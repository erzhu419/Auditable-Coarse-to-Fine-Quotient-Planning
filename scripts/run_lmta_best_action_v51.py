"""One best-action-set objective on the unchanged V49 NodeQ and recorded batches."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter

import networkx as nx
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.lmta_aim_v43 import generate_graph
from acfqp.science.lmta_models_v43 import NodeQ, optimizer_step
from acfqp.science.lmta_best_action_v51 import teacher_best_mask, best_action_loss, objective_metrics
from acfqp.science.lmta_structure_v45 import weighted_adjacency
from acfqp.science.lmta_supervised_v49 import features_from_state, ranking_metrics
from run_lmta_supervised_v49 import PROTOCOL as BASE_PROTOCOL, SOURCES as BASE_SOURCES, synchronize

CONTROL = ROOT / 'reports/lmta_supervised_v49'
PROTOCOL = dict(BASE_PROTOCOL, loss='negative_log_best_set_mass', temperature=1.,
    architecture='NodeQ', batch_source='V49_recorded_batches',
    target_set_rule='float64_legal_within_1e-9_of_best', output_semantics='ranking_logits')
SOURCES = BASE_SOURCES + ['src/acfqp/science/lmta_best_action_v51.py',
    'scripts/run_lmta_best_action_v51.py', 'scripts/analyze_lmta_best_action_v51.py',
    'scripts/analyze_lmta_learnability_v44.py']
def run(output_dir, device):
    started = perf_counter()
    torch.set_num_threads(1)
    tick = perf_counter()
    control = json.loads((CONTROL / 'manifest.json').read_text())
    if control['status'] != 'complete' or control['protocol'] != BASE_PROTOCOL:
        raise ValueError('V49 control is not the frozen completed experiment')
    if not json.loads((CONTROL / 'analysis.json').read_text())['integrity']['passed']:
        raise ValueError('V49 control is incomplete')
    runtime = dict(python=platform.python_version(), numpy=np.__version__, networkx=nx.__version__,
        torch=torch.__version__, device=device, torch_threads=torch.get_num_threads(),
        gpu=torch.cuda.get_device_name() if str(device).startswith('cuda') else None)
    if runtime != control['runtime']:
        raise ValueError('Runtime differs from the retained control')
    for name in BASE_SOURCES:
        if (ROOT / name).read_bytes() != (CONTROL / 'source' / name).read_bytes():
            raise ValueError(f'Retained V49 source changed: {name}')
    with np.load(CONTROL / 'dataset.npz') as loaded:
        data = {name: loaded[name] for name in loaded.files}
    old_metrics = [json.loads(line) for line in (CONTROL / 'metrics.jsonl').read_text().splitlines()]
    old_training = [json.loads(line) for line in (CONTROL / 'training.jsonl').read_text().splitlines()]
    source_seconds = perf_counter() - tick
    output_dir.mkdir(parents=True, exist_ok=False)
    for name in SOURCES:
        target = output_dir / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    shutil.copyfile(ROOT / 'specs/LMTA_BEST_ACTION_V51.md', output_dir / 'protocol.md')
    (output_dir / 'models').mkdir()
    manifest = dict(schema='acfqp.lmta_best_action.v51', status='running', protocol=PROTOCOL,
        runtime=runtime, source_directory='reports/lmta_supervised_v49',
        dataset_path='reports/lmta_supervised_v49/dataset.npz',
        dataset_bytes=(CONTROL / 'dataset.npz').stat().st_size, source_read_seconds=source_seconds,
        graphs=[], runs=[], initial_anchors_complete=False,
        new_environment_calls=0, new_RL_training_updates=0, new_MCTS_calls=0)

    def save_manifest():
        (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')

    def emit(log, row):
        log.write(json.dumps(row, allow_nan=False) + '\n')

    save_manifest()
    tick = perf_counter()
    graphs = {}
    for row in control['graphs']:
        graph_id = row['graph_id']
        graph = generate_graph(500, graph_id, .01)
        graph.graph['replay_id'] = graph_id
        graphs[graph_id] = graph
        manifest['graphs'].append(dict(graph_id=graph_id, split=row['split'], nodes=len(graph), edges=graph.number_of_edges()))
    if manifest['graphs'] != control['graphs']:
        raise AssertionError('Regenerated graphs differ')
    manifest['graph_generation_seconds'] = perf_counter() - tick
    graph_ids = list(graphs)
    if (data['statuses'].shape != (1680, 500) or data['targets'].dtype != np.float64
            or not np.array_equal(data['graph_id'], np.repeat(graph_ids, 70))
            or not np.array_equal(data['heldout'], np.arange(1680) >= 1120)):
        raise AssertionError('Retained dataset shape or split differs')
    tick = perf_counter()
    x = torch.as_tensor(np.stack([features_from_state(data['statuses'][i], 10 - int(data['day'][i]),
        int(data['remaining_budget'][i])) for i in range(1680)]), device=device)
    legal_array = data['statuses'] == 0
    legal = torch.as_tensor(legal_array, device=device)
    adjacencies = torch.stack([weighted_adjacency(graphs[key], device, torch.float32) for key in graph_ids])
    state_graph_indices = torch.tensor(np.repeat(np.arange(24), 70), device=device)
    synchronize(device)
    manifest['tensor_preparation_seconds'] = perf_counter() - tick
    tick = perf_counter()
    best_array = teacher_best_mask(data['targets'], legal_array)
    best = torch.as_tensor(best_array, device=device)
    sizes = best_array.sum(-1)
    synchronize(device)
    supervision = dict(states=1680, legal_nodes=int(legal_array.sum()),
        teacher_best_members=int(sizes.sum()),
        best_set_size_counts={str(int(size)): count for size, count in sorted(Counter(sizes).items())},
        tolerance=1e-9, target_dtype=str(data['targets'].dtype),
        all_sets_nonempty=bool((sizes > 0).all()), all_sets_legal=bool(not (best_array & ~legal_array).any()),
        wall_seconds=perf_counter() - tick)
    (output_dir / 'supervision.json').write_text(json.dumps(supervision, indent=2) + '\n')
    manifest['supervision_preparation_seconds'] = supervision['wall_seconds']
    if not supervision['all_sets_nonempty'] or not supervision['all_sets_legal']:
        manifest.update(status='invalid_supervision', wall_seconds=perf_counter() - started)
        save_manifest()
        raise AssertionError('Teacher best sets must be nonempty and legal')
    print(json.dumps(dict(supervision_states=1680, best_set_size_counts=supervision['best_set_size_counts'])), flush=True)
    save_manifest()
    references = {(row['run_id'], row['checkpoint'], row['state_id']): row for row in old_metrics}
    batch_records = {(row['run_id'], row['step']): row for row in old_training}
    models, optimizers = {}, {}
    for run_id in range(3):
        tick = perf_counter()
        torch.manual_seed(PROTOCOL['initialization_seeds'][run_id])
        model = NodeQ().to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=.001, weight_decay=.00001)
        synchronize(device)
        total = sum(p.numel() for p in model.parameters())
        record = dict(run_id=run_id, initialization_seed=PROTOCOL['initialization_seeds'][run_id],
            batch_seed=PROTOCOL['batch_seeds'][run_id], initialization_seconds=perf_counter() - tick,
            base_parameters=total, candidate_parameters=total,
            gradient_steps=0, training_state_presentations=0, evaluations=[])
        models[run_id], optimizers[run_id] = model, optimizer
        manifest['runs'].append(record)
    with (output_dir / 'metrics.jsonl').open('x') as metrics, (output_dir / 'training.jsonl').open('x') as training:
        def evaluate(model, run_id, checkpoint):
            synchronize(device)
            tick = perf_counter()
            model.eval()
            mismatch_count = 0
            with torch.no_grad():
                for begin in range(0, 1680, 16):
                    end = min(begin + 16, 1680)
                    q = model(x[begin:end], adjacencies[state_graph_indices[begin:end]]).cpu().numpy()
                    for offset, state_id in enumerate(range(begin, end)):
                        mask, targets = legal_array[state_id], data['targets'][state_id]
                        measured = ranking_metrics(q[offset], targets, mask)
                        original_fields = dict(run_id=run_id, checkpoint=checkpoint,
                            split='heldout' if data['heldout'][state_id] else 'train',
                            graph_id=int(data['graph_id'][state_id]), state_id=state_id,
                            day=int(data['day'][state_id]), remaining_budget=int(data['remaining_budget'][state_id]),
                            legal_nodes=int(mask.sum()), **measured,
                            mse=float(np.mean((q[offset][mask] - targets[mask]) ** 2)),
                            predicted_q=float(q[offset][measured['predicted_node']]),
                            teacher_q=float(q[offset][measured['teacher_node']]))
                        emit(metrics, dict(**original_fields, **objective_metrics(q[offset], best_array[state_id], mask)))
                        if checkpoint == 0 and original_fields != references[run_id, checkpoint, state_id]:
                            mismatch_count += 1
            metrics.flush()
            synchronize(device)
            return dict(checkpoint=checkpoint, states=1680, wall_seconds=perf_counter() - tick,
                initial_mismatch_count=mismatch_count)

        for record in manifest['runs']:
            run_id = record['run_id']
            anchor = evaluate(models[run_id], run_id, 0)
            record['evaluations'].append(anchor)
            if anchor['initial_mismatch_count']:
                manifest.update(status='initial_mismatch', wall_seconds=perf_counter() - started)
                save_manifest()
                raise AssertionError('Unchanged NodeQ initial evaluation differs from V49')
        manifest['initial_anchors_complete'] = True
        save_manifest()
        print(json.dumps(dict(initial_anchor_states=5040, exact=True)), flush=True)
        for record in manifest['runs']:
            run_id = record['run_id']
            model, optimizer = models[run_id], optimizers[run_id]
            model.train()
            synchronize(device)
            tick = perf_counter()
            for step in range(1, 2001):
                indices = batch_records[run_id, step]['batch_state_ids']
                if len(indices) != 4 or len(set(indices)) != 4 or not all(0 <= i < 1120 for i in indices):
                    raise AssertionError('Retained batch is not four distinct training states')
                ids = torch.tensor(indices, device=device)
                loss = best_action_loss(model(x[ids], adjacencies[state_graph_indices[ids]]), best[ids], legal[ids])
                if not torch.isfinite(loss):
                    raise AssertionError('Nonfinite best-set loss')
                optimizer_step(optimizer, loss, model.parameters())
                record['gradient_steps'] += 1
                record['training_state_presentations'] += 4
                emit(training, dict(run_id=run_id, step=step, batch_state_ids=indices, loss=float(loss.detach())))
                if step % 500 == 0:
                    training.flush()
                    print(json.dumps(dict(run_id=run_id, step=step)), flush=True)
            synchronize(device)
            record['training_seconds'] = perf_counter() - tick
            record['evaluations'].append(evaluate(model, run_id, 2000))
            tick = perf_counter()
            model_path = f'models/run{run_id}.pt'
            torch.save(dict(schema='acfqp.nodeq_best_action.v51', run_id=run_id, checkpoint=2000,
                output_semantics='ranking_logits',
                weights={name: value.detach().cpu() for name, value in model.state_dict().items()}),
                output_dir / model_path)
            record.update(model_path=model_path, model_bytes=(output_dir / model_path).stat().st_size,
                model_serialization_seconds=perf_counter() - tick)
            save_manifest()
            print(json.dumps(dict(run_id=run_id, complete=True)), flush=True)
    manifest.update(status='complete', wall_seconds=perf_counter() - started)
    save_manifest()
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_best_action_v51')
    parser.add_argument('--device', default='cuda' if torch.cuda.is_available() else 'cpu')
    args = parser.parse_args()
    run(args.output_dir, args.device)
