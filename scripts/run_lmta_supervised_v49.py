"""Fixed teacher data and a bounded, goal-free NodeQ supervised fit."""
from __future__ import annotations

import argparse
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
from acfqp.science.lmta_structure_v45 import weighted_adjacency
from acfqp.science.lmta_supervised_v49 import collect_episode, features_from_state, ranking_metrics

PROTOCOL = dict(train_graph_ids=list(range(440000, 440016)),
    heldout_graph_ids=list(range(490900, 490908)),
    train_environment_seeds=list(range(491000, 491016)),
    heldout_environment_seeds=list(range(492000, 492008)),
    nodes=500, p=.01, budget=70, horizon=10, runs=3,
    initialization_seeds=[493001, 493002, 493003], batch_seeds=[494001, 494002, 494003],
    steps=2000, batch_size=4, checkpoints=[0, 2000], learning_rate=.001,
    weight_decay=.00001, gradient_clip=5., target_tie_tolerance=1e-9,
    max_mean_relative_regret=.01, min_optimal_rate=.95,
    loss='state_mean_legal_node_mse', state_policy='AVERAGE_SCORE',
    operator='IC_SUM', dtype='float32')
SOURCES = ['src/acfqp/science/' + name for name in ('lmta_aim_v43.py',
    'lmta_models_v43.py', 'lmta_structure_v45.py', 'lmta_supervised_v49.py')]
SOURCES += ['scripts/run_lmta_supervised_v49.py', 'scripts/analyze_lmta_supervised_v49.py']


def synchronize(device):
    if str(device).startswith('cuda'):
        torch.cuda.synchronize()


def supervised_loss(predictions, targets, legal):
    return (((predictions - targets).square() * legal).sum(-1) / legal.sum(-1)).mean()


def run(output_dir, device):
    torch.set_num_threads(1)
    runtime = dict(python=platform.python_version(), numpy=np.__version__, networkx=nx.__version__,
        torch=torch.__version__, device=device, torch_threads=torch.get_num_threads(),
        gpu=torch.cuda.get_device_name() if str(device).startswith('cuda') else None)
    previous = ROOT / 'reports/lmta_components_v48'
    if runtime != json.loads((previous / 'manifest.json').read_text())['runtime']:
        raise ValueError('V49 must use the retained V48 runtime')
    # These are the unchanged environment, operator and NodeQ definitions.
    for name in SOURCES[:3]:
        if (ROOT / name).read_bytes() != (previous / 'source' / name).read_bytes():
            raise ValueError(f'Retained dependency differs: {name}')
    output_dir.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    for name in SOURCES:
        target = output_dir / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    shutil.copyfile(ROOT / 'specs/LMTA_SUPERVISED_V49.md', output_dir / 'protocol.md')
    (output_dir / 'models').mkdir()
    manifest = dict(schema='acfqp.lmta_supervised.v49', status='running', protocol=PROTOCOL,
        runtime=runtime, graphs=[], runs=[], retained_history='reports/lmta_components_v48/analysis.json')

    def save_manifest():
        (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')

    def emit(log, row):
        log.write(json.dumps(row, allow_nan=False) + '\n')

    save_manifest()
    tick = perf_counter()
    graphs = {}
    for split in ('train', 'heldout'):
        for graph_id in PROTOCOL[split + '_graph_ids']:
            graph = generate_graph(500, graph_id, .01)
            graph.graph['replay_id'] = graph_id
            graphs[graph_id] = graph
            manifest['graphs'].append(dict(graph_id=graph_id, split=split,
                nodes=len(graph), edges=graph.number_of_edges()))
    manifest['graph_generation_seconds'] = perf_counter() - tick
    save_manifest()
    samples = []
    with (output_dir / 'collection.jsonl').open('x') as log:
        for split in ('train', 'heldout'):
            for graph_id, seed in zip(PROTOCOL[split + '_graph_ids'], PROTOCOL[split + '_environment_seeds']):
                batch, event = collect_episode(graphs[graph_id], graph_id, seed)
                emit(log, dict(split=split, **event))
                log.flush()
                if len(batch) != 70:
                    manifest.update(status='incomplete_teacher_episode', wall_seconds=perf_counter() - started)
                    save_manifest()
                    raise AssertionError('Teacher did not supply the frozen 70 pre-selection states')
                for sample in batch:
                    samples.append(dict(state_id=len(samples), graph_id=graph_id, split=split, **sample))
    print(json.dumps(dict(collected_episodes=24, states=len(samples))), flush=True)
    tick = perf_counter()
    statuses = np.stack([row['statuses'] for row in samples])
    targets = np.stack([row['targets'] for row in samples])
    np.savez_compressed(output_dir / 'dataset.npz', statuses=statuses, targets=targets,
        day=np.asarray([row['day'] for row in samples], dtype=np.int8),
        remaining_budget=np.asarray([row['remaining_budget'] for row in samples], dtype=np.int16),
        graph_id=np.asarray([row['graph_id'] for row in samples], dtype=np.int32),
        heldout=np.asarray([row['split'] == 'heldout' for row in samples], dtype=bool))
    manifest['dataset_serialization_seconds'] = perf_counter() - tick
    manifest['dataset_bytes'] = (output_dir / 'dataset.npz').stat().st_size
    tick = perf_counter()
    x = torch.as_tensor(np.stack([features_from_state(row['statuses'], 10 - row['day'],
        row['remaining_budget']) for row in samples]), device=device)
    y = torch.as_tensor(targets, dtype=torch.float32, device=device)
    legal = torch.as_tensor(statuses == 0, device=device)
    graph_ids = list(graphs)
    adjacencies = torch.stack([weighted_adjacency(graphs[key], device, torch.float32) for key in graph_ids])
    state_graph_indices = torch.tensor([graph_ids.index(row['graph_id']) for row in samples], device=device)
    synchronize(device)
    manifest['tensor_preparation_seconds'] = perf_counter() - tick
    save_manifest()
    with (output_dir / 'metrics.jsonl').open('x') as metrics, (output_dir / 'training.jsonl').open('x') as training:
        def evaluate(model, run_id, checkpoint):
            synchronize(device)
            tick = perf_counter()
            model.eval()
            with torch.no_grad():
                for begin in range(0, len(samples), 16):
                    end = min(begin + 16, len(samples))
                    q = model(x[begin:end], adjacencies[state_graph_indices[begin:end]]).cpu().numpy()
                    for offset, state_id in enumerate(range(begin, end)):
                        row = samples[state_id]
                        mask = statuses[state_id] == 0
                        measured = ranking_metrics(q[offset], targets[state_id], mask)
                        emit(metrics, dict(run_id=run_id, checkpoint=checkpoint,
                            split=row['split'], graph_id=row['graph_id'], state_id=state_id,
                            day=row['day'], remaining_budget=row['remaining_budget'],
                            legal_nodes=int(mask.sum()), **measured,
                            mse=float(np.mean((q[offset][mask] - targets[state_id][mask]) ** 2)),
                            predicted_q=float(q[offset][measured['predicted_node']]),
                            teacher_q=float(q[offset][measured['teacher_node']])))
            metrics.flush()
            synchronize(device)
            return dict(checkpoint=checkpoint, states=len(samples), wall_seconds=perf_counter() - tick)

        for run_id in range(3):
            tick = perf_counter()
            torch.manual_seed(PROTOCOL['initialization_seeds'][run_id])
            model = NodeQ().to(device)
            optimizer = torch.optim.Adam(model.parameters(), lr=.001, weight_decay=.00001)
            rng = np.random.default_rng(PROTOCOL['batch_seeds'][run_id])
            synchronize(device)
            record = dict(run_id=run_id, initialization_seed=PROTOCOL['initialization_seeds'][run_id],
                batch_seed=PROTOCOL['batch_seeds'][run_id], initialization_seconds=perf_counter() - tick,
                gradient_steps=0, training_state_presentations=0, evaluations=[])
            manifest['runs'].append(record)
            record['evaluations'].append(evaluate(model, run_id, 0))
            save_manifest()
            model.train()
            synchronize(device)
            tick = perf_counter()
            for step in range(1, PROTOCOL['steps'] + 1):
                indices = rng.choice(1120, PROTOCOL['batch_size'], replace=False)
                ids = torch.as_tensor(indices, device=device)
                predictions = model(x[ids], adjacencies[state_graph_indices[ids]])
                loss = supervised_loss(predictions, y[ids], legal[ids])
                if not torch.isfinite(loss):
                    raise AssertionError('Nonfinite supervised loss')
                optimizer_step(optimizer, loss, model.parameters())
                record['gradient_steps'] += 1
                record['training_state_presentations'] += len(indices)
                emit(training, dict(run_id=run_id, step=step, batch_state_ids=indices.tolist(), loss=float(loss.detach())))
                if step % 500 == 0:
                    training.flush()
                    print(json.dumps(dict(run_id=run_id, step=step)), flush=True)
            synchronize(device)
            record['training_seconds'] = perf_counter() - tick
            record['evaluations'].append(evaluate(model, run_id, 2000))
            tick = perf_counter()
            model_path = f'models/run{run_id}.pt'
            torch.save(dict(schema='acfqp.nodeq_supervised.v49', run_id=run_id, checkpoint=2000,
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
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_supervised_v49')
    parser.add_argument('--device', default='cuda' if torch.cuda.is_available() else 'cpu')
    args = parser.parse_args()
    run(args.output_dir, args.device)
