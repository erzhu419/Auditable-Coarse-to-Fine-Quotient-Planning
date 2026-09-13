"""Learn a raw-board encoder into a source-only, frozen finite world model.

Both RAW and QUOTIENT classify source model cells with the same network inputs
and training schedule. Only the teacher state partition changes. No target
transitions, legality masks, value labels, or target model fitting are used.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
from time import perf_counter

import torch
from torch import nn
from torch.nn import functional as F

from .controlled_predictive_quotient_v1 import (
    Cell, CompiledModel, FiniteModel, Outcome, build_quotient, compile_full_state,
)


NEIGHBORS = tuple((cell, neighbor) for cell in range(16) for neighbor in range(16)
    if abs(cell//4-neighbor//4)+abs(cell%4-neighbor%4) == 1)
FEATURE_DIMENSION = 16*12 + len(NEIGHBORS)


@dataclass(frozen=True)
class SourceAssembly:
    model: FiniteModel
    boards: dict[int, tuple[int, ...]]
    counts: dict[str, int]
    elapsed_seconds: float


def assemble_sources(builds) -> SourceAssembly:
    """Unify exact source kernels by concrete active key and terminal status."""
    started, work = perf_counter(), Counter()
    index, layers, statuses, boards, rows, roots = {}, {}, {}, {}, {}, []
    for build in builds:
        work['source_builds'] += 1
        mapping = {}
        for state, h in build.model.layers.items():
            status = build.model.terminal[state]
            key = (h, tuple(build.boards[state])) if status == 'ACTIVE' else (h, status)
            work['input_source_states'] += 1
            if key not in index:
                target = len(index); index[key] = target
                layers[target], statuses[target] = h, status
                if status == 'ACTIVE': boards[target] = key[1]
            else:
                work['unified_source_states'] += 1
            mapping[state] = index[key]
        roots.extend(mapping[root] for root in build.model.roots)
        for (state, action), outcomes in build.model.rows.items():
            work['input_source_rows'] += 1
            work['input_source_outcomes'] += len(outcomes)
            key = mapping[state], action
            if key in rows:
                work['unified_source_rows'] += 1
            else:
                rows[key] = tuple(Outcome(o.probability, mapping[o.next_state], o.reward) for o in outcomes)
    model = FiniteModel(layers, statuses, rows, tuple(roots))
    work.update(source_states=len(layers), source_active_states=len(boards), source_rows=len(rows),
        source_outcomes=sum(map(len, rows.values())))
    return SourceAssembly(model, boards, dict(work), perf_counter()-started)


def board_features(boards):
    """Raw rank one-hot and directed adjacent nonempty rank equalities."""
    ranks = torch.as_tensor(boards, dtype=torch.long)
    onehot = F.one_hot(ranks.clamp(max=11), num_classes=12).reshape(len(boards), -1).float()
    left = ranks[:, [a for a, _ in NEIGHBORS]]
    right = ranks[:, [b for _, b in NEIGHBORS]]
    return torch.cat((onehot, ((left == right) & (left > 0)).float()), dim=1)


class BoardEncoder(nn.Module):
    def __init__(self, cells_by_horizon):
        super().__init__()
        self.body = nn.Sequential(nn.Linear(FEATURE_DIMENSION, 128), nn.ReLU(),
                                  nn.Linear(128, 128), nn.ReLU())
        self.heads = nn.ModuleDict({str(h): nn.Linear(128, len(cells))
                                   for h, cells in sorted(cells_by_horizon.items())})

    def forward(self, features, horizon):
        return self.heads[str(horizon)](self.body(features))


class LearnedModel:
    def __init__(self, network, compiled, cells_by_horizon, variant, training_report):
        self.network, self.compiled = network.eval(), compiled
        self.cells_by_horizon = cells_by_horizon
        self.variant, self.training_report = variant, training_report
        self.inference_counts = Counter()
        self.inference_seconds = 0.

    def batch_encode(self, boards, horizons):
        started = perf_counter()
        output = [None]*len(boards)
        self.inference_counts['batch_calls'] += 1
        for h in sorted(set(horizons)):
            indices = [i for i, value in enumerate(horizons) if value == h]
            if h not in self.cells_by_horizon:
                self.inference_counts['unsupported_horizon_boards'] += len(indices)
                continue
            cells = self.cells_by_horizon[h]
            with torch.no_grad():
                for start in range(0, len(indices), 512):
                    chunk = indices[start:start+512]
                    inputs = board_features([boards[i] for i in chunk])
                    labels = self.network(inputs, h).argmax(dim=1).tolist()
                    for i, label in zip(chunk, labels): output[i] = cells[label]
                    self.inference_counts['network_batches'] += 1
            self.inference_counts['encoded_boards'] += len(indices)
            self.inference_counts['feature_entries'] += len(indices)*FEATURE_DIMENSION
            self.inference_counts['classification_logits'] += len(indices)*len(cells)
        self.inference_seconds += perf_counter()-started
        return output

    def encode(self, board, horizon):
        return self.batch_encode([board], [horizon])[0]


def train_model(source, variant, *, steps=1500, batch_size=128, seed=6801):
    """Fit source quotient-code labels, with a fixed horizon-balanced schedule."""
    started = perf_counter()
    if variant not in {'RAW', 'QUOTIENT'}:
        raise ValueError('variant must be RAW or QUOTIENT')
    tick = perf_counter()
    compiled = compile_full_state(source.model) if variant == 'RAW' else build_quotient(source.model)
    compilation_seconds = perf_counter()-tick
    cells_by_horizon = {}
    for cell, descriptor in compiled.cells.items():
        if descriptor.terminal == 'ACTIVE': cells_by_horizon.setdefault(descriptor.layer, []).append(cell)
    if not cells_by_horizon:
        raise ValueError('source contains no active training states')
    class_index = {h:{cell:index for index,cell in enumerate(cells)} for h,cells in cells_by_horizon.items()}
    data = {}
    tick = perf_counter()
    for h in sorted(cells_by_horizon):
        states = sorted(state for state in source.boards if source.model.layers[state] == h)
        features = board_features([source.boards[state] for state in states])
        labels = torch.tensor([class_index[h][compiled.state_to_cell[state]] for state in states], dtype=torch.long)
        data[h] = features, labels
    feature_seconds = perf_counter()-tick
    torch.set_num_threads(1)
    torch.manual_seed(seed)
    network = BoardEncoder(cells_by_horizon)
    optimizer = torch.optim.Adam(network.parameters(), lr=1e-3)
    # A separate generator gives both variants the identical observed source
    # minibatches even though their output-head parameter counts differ.
    sampler = torch.Generator().manual_seed(seed)
    horizons = sorted(data)
    work = Counter()
    tick = perf_counter()
    last_loss = None
    for _ in range(steps):
        h = horizons[int(torch.randint(len(horizons), (1,), generator=sampler))]
        features, labels = data[h]
        selection = torch.randint(len(labels), (batch_size,), generator=sampler)
        optimizer.zero_grad(set_to_none=True)
        loss = F.cross_entropy(network(features[selection], h), labels[selection])
        loss.backward(); optimizer.step()
        last_loss = float(loss.detach())
        work['optimizer_steps'] += 1
        work['training_examples'] += batch_size
        work['training_logits'] += batch_size*len(cells_by_horizon[h])
        work[f'h{h}_steps'] += 1
        if work['optimizer_steps'] % 250 == 0:
            print(json.dumps(dict(variant=variant, training_step=work['optimizer_steps'],
                final_batch_loss=last_loss)), flush=True)
    training_seconds = perf_counter()-tick
    source_accuracy = {}
    tick = perf_counter()
    network.eval()
    with torch.no_grad():
        for h, (features, labels) in data.items():
            correct = 0
            for start in range(0, len(labels), 512):
                prediction = network(features[start:start+512], h).argmax(dim=1)
                correct += int((prediction == labels[start:start+512]).sum())
                work['training_diagnostic_examples'] += len(prediction)
                work['training_diagnostic_logits'] += len(prediction)*len(cells_by_horizon[h])
            source_accuracy[str(h)] = dict(correct=correct, examples=len(labels), accuracy=correct/len(labels))
    report = dict(variant=variant, seed=seed, steps=steps, batch_size=batch_size, optimizer='Adam', learning_rate=1e-3,
        schedule='Uniform horizon, then uniform source states with replacement; no validation/target selection',
        architecture=[FEATURE_DIMENSION,128,128], features='16x12 raw ranks plus 48 directed adjacent equalities',
        classes_by_horizon={str(h):len(cells) for h,cells in cells_by_horizon.items()},
        source_active_states=len(source.boards), teacher_active_cells=sum(map(len,cells_by_horizon.values())),
        source_classification=source_accuracy, final_training_batch_loss=last_loss,
        parameters=sum(p.numel() for p in network.parameters()), device='cpu', torch_threads=torch.get_num_threads(),
        teacher_compilation_seconds=compilation_seconds, feature_seconds=feature_seconds,
        training_seconds=training_seconds, source_diagnostic_seconds=perf_counter()-tick,
        total_seconds=perf_counter()-started, counts=dict(work), target_model_updates=0)
    return LearnedModel(network, compiled, cells_by_horizon, variant, report)


def save_model(model, directory):
    """Save the actual encoder and frozen dynamics, without training board maps."""
    started = perf_counter(); directory = Path(directory); directory.mkdir(parents=True, exist_ok=False)
    compiled = model.compiled
    payload = dict(schema='acfqp.source_frozen_neural_model.v68', variant=model.variant,
        cells_by_horizon={str(h):cells for h,cells in model.cells_by_horizon.items()},
        cells=[[cell,row.layer,row.terminal] for cell,row in sorted(compiled.cells.items())],
        rows=[[cell,action,[[o.probability,o.next_state,o.reward] for o in outcomes]]
              for (cell,action),outcomes in sorted(compiled.rows.items())], roots=list(compiled.roots),
        training_report=model.training_report)
    (directory/'kernel.json').write_text(json.dumps(payload, separators=(',', ':'), allow_nan=False)+'\n')
    torch.save(model.network.state_dict(), directory/'encoder.pt')
    return dict(kernel_bytes=(directory/'kernel.json').stat().st_size,
                weight_bytes=(directory/'encoder.pt').stat().st_size, elapsed_seconds=perf_counter()-started)


def load_model(directory):
    directory = Path(directory)
    payload = json.loads((directory/'kernel.json').read_text())
    if payload['schema'] != 'acfqp.source_frozen_neural_model.v68':
        raise ValueError('expected V68 source-frozen model')
    cells = {cell:Cell(h,status,()) for cell,h,status in payload['cells']}
    rows = {(cell,action):tuple(Outcome(p,target,reward) for p,target,reward in outcomes)
            for cell,action,outcomes in payload['rows']}
    compiled = CompiledModel(cells,rows,tuple(payload['roots']),{}, {})
    cells_by_horizon = {int(h):values for h,values in payload['cells_by_horizon'].items()}
    network = BoardEncoder(cells_by_horizon)
    network.load_state_dict(torch.load(directory/'encoder.pt', map_location='cpu', weights_only=True))
    return LearnedModel(network,compiled,cells_by_horizon,payload['variant'],payload['training_report'])
