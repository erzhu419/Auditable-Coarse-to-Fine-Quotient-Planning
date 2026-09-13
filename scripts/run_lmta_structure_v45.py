"""Frozen, zero-environment-sample V45 initial-structure comparison."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

import networkx as nx
import numpy as np
import torch
from torch.nn import functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.lmta_aim_v43 import generate_graph
from acfqp.science.lmta_models_v43 import NodeQ
from acfqp.science.lmta_structure_v45 import (
    exact_one_step_score, initial_features, mean_adjacency, one_step_readout,
    spread_summary, weighted_adjacency,
)

V44 = ROOT / 'reports/lmta_learnability_v44'
OPERATORS = {'MEAN': mean_adjacency, 'IC_SUM': weighted_adjacency}
VISIBLE_TOLERANCE = 1e-10


def load_policies(manifest):
    policies = []
    for row in manifest['completed_runs']:
        payload = torch.load(V44 / row['model_path'], map_location='cpu', weights_only=True)
        name = row['method']
        network = NodeQ(goal_size=128 if name == 'LMTA_RI' else 0, wait=name == 'FLAT_DQN')
        network.load_state_dict(payload['weights']['low' if name == 'LMTA_RI' else 'll'], strict=True)
        network.double().eval()
        goals = F.normalize(payload['weights']['model']['goals.weight'].double(), dim=-1) if name == 'LMTA_RI' else None
        policies.append(dict(method=name, run_id=row['run_id'], network=network, goals=goals,
                             model_path=row['model_path']))
    return policies


def conditional_q(network, nodes, goals=None):
    """Reuse node embeddings across goals; END_DAY is not a seed score."""
    if goals is None:
        q = network.head(nodes).squeeze(-1).unsqueeze(0)
    else:
        inputs = torch.cat((nodes.unsqueeze(0).expand(len(goals), -1, -1),
                            goals.unsqueeze(1).expand(-1, len(nodes), -1)), dim=-1)
        q = network.head(inputs).squeeze(-1)
    wait_q = float(network.wait_head(nodes.mean(dim=0)).squeeze()) if network.wait_head is not None else None
    return q, wait_q


def describe_q(q, analytic_score, wait_q=None):
    greedy_seed = int(q.argmax())
    seed_value = float(q[greedy_seed])
    # Seed IDs precede END_DAY in the published V43/V44 argmax convention.
    selects_wait = wait_q is not None and wait_q > seed_value
    return {**spread_summary(q), 'seed_q_min': float(q.min()), 'seed_q_max': float(q.max()),
            'conditional_greedy_seed': greedy_seed,
            'conditional_seed_one_step_score': float(analytic_score[greedy_seed]),
            'conditional_seed_one_step_regret': float(max(analytic_score) - analytic_score[greedy_seed]),
            'end_day_q': wait_q, 'flat_actual_choice_is_end_day': selects_wait if wait_q is not None else None}


def aggregate_diagnostics(rows, field):
    groups = defaultdict(list)
    for row in rows:
        groups[(row['operator'], row['method'])].append(row[field])
    return [dict(operator=op, method=method, conditions=len(values),
                 visible_conditions=sum(value > VISIBLE_TOLERANCE for value in values),
                 min_scaled_spread=min(values), median_scaled_spread=float(np.median(values)),
                 max_scaled_spread=max(values)) for (op, method), values in groups.items()]


@torch.inference_mode()
def run(output_dir):
    output_dir.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    start = perf_counter()
    manifest = json.loads((V44 / 'manifest.json').read_text())
    if manifest['status'] != 'complete' or nx.__version__ != manifest['runtime']['networkx']:
        raise ValueError('V44 input completion or graph generator version differs')
    tick = perf_counter()
    policies = load_policies(manifest)
    timings = Counter(checkpoint_loading_seconds=perf_counter() - tick)
    counts = Counter(checkpoint_files_loaded=len(policies))
    graph_rows, encoder_rows, q_rows = [], [], []
    with (output_dir / 'graphs.jsonl').open('x') as graph_log, \
         (output_dir / 'encoders.jsonl').open('x') as encoder_log, \
         (output_dir / 'readouts.jsonl').open('x') as q_log:
        for identity in manifest['graphs']:
            tick = perf_counter()
            graph_id = identity['graph_id']
            graph = generate_graph(identity['nodes'], graph_id, manifest['protocol']['p'])
            if graph.number_of_edges() != identity['edges']:
                raise ValueError('Regenerated graph differs from retained metadata')
            timings['graph_generation_seconds'] += perf_counter() - tick
            counts['graph_generation_calls'] += 1
            tick = perf_counter()
            score = exact_one_step_score(graph)
            x = initial_features(len(graph))
            timings['analytic_score_seconds'] += perf_counter() - tick
            for operator, build in OPERATORS.items():
                tick = perf_counter()
                a = build(graph)
                timings[operator + '_operator_seconds'] += perf_counter() - tick
                counts['operator_constructions'] += 1
                tick = perf_counter()
                first_message = a @ x
                counts['first_message_products'] += 1
                g = dict(graph_id=graph_id, operator=operator, nodes=len(graph), edges=identity['edges'],
                         operator_numeric_bytes=a.numel() * a.element_size(),
                         analytic_score_range=float(np.ptp(score)),
                         message_spread=spread_summary(first_message),
                         constant_message_error=float((first_message - x).abs().max()),
                         analytic_readout_error=float(np.max(np.abs(one_step_readout(first_message).numpy() - score))))
                graph_log.write(json.dumps(g, allow_nan=False) + '\n')
                graph_rows.append(g)
                timings['message_diagnostic_seconds'] += perf_counter() - tick
                for policy in policies:
                    identity_fields = {k: policy[k] for k in ('method', 'run_id')}
                    identity_fields.update(graph_id=graph_id, operator=operator)
                    tick = perf_counter()
                    nodes = policy['network'].encoder.nodes(x, a)
                    timings[operator + '_encoder_seconds'] += perf_counter() - tick
                    counts['encoder_node_calls'] += 1
                    enc = dict(**identity_fields, **spread_summary(nodes))
                    encoder_rows.append(enc)
                    encoder_log.write(json.dumps(enc, allow_nan=False) + '\n')
                    tick = perf_counter()
                    q, wait_q = conditional_q(policy['network'], nodes, policy['goals'])
                    timings[operator + '_head_seconds'] += perf_counter() - tick
                    counts['conditional_head_batches'] += 1
                    counts['conditional_q_vectors'] += len(q)
                    counts['flat_end_day_head_calls'] += int(wait_q is not None)
                    if not torch.isfinite(nodes).all() or not torch.isfinite(q).all():
                        raise AssertionError('Nonfinite fixed-network readout')
                    tick = perf_counter()
                    for goal, values in enumerate(q):
                        row = dict(**identity_fields, goal=goal if policy['goals'] is not None else None,
                                   **describe_q(values, score, wait_q))
                        q_rows.append(row)
                        q_log.write(json.dumps(row, allow_nan=False) + '\n')
                    timings['readout_summary_seconds'] += perf_counter() - tick
                del a
            if counts['graph_generation_calls'] % 10 == 0:
                print(json.dumps(dict(completed_graphs=counts['graph_generation_calls'], total_graphs=58)), flush=True)
    mean = [r for r in graph_rows if r['operator'] == 'MEAN']
    weighted = [r for r in graph_rows if r['operator'] == 'IC_SUM']
    conditions = dict(all_graphs_covered=len(mean) == len(weighted) == 58,
                      mean_constant=all(r['constant_message_error'] <= 1e-12 for r in mean),
                      exact_initial_score_recoverable=all(r['analytic_readout_error'] <= 1e-12 for r in weighted),
                      score_variation_preserved=all(r['message_spread']['scaled_row_range'] > VISIBLE_TOLERANCE
                                                   for r in weighted if r['analytic_score_range'] > 1e-12))
    coverage = dict(expected_encoder_conditions=1044, actual_encoder_conditions=len(encoder_rows),
                    expected_q_conditions=11832, actual_q_conditions=len(q_rows))
    if len(encoder_rows) != 1044 or len(q_rows) != 11832:
        raise AssertionError('Incomplete fixed-policy/graph/goal coverage')
    storage = dict(retained_input_file_bytes=sum(r['model_bytes'] for r in manifest['completed_runs']),
                   loaded_parameter_bytes=sum(p.numel() * p.element_size() for model in policies for p in model['network'].parameters()),
                   loaded_goal_bytes=sum(p['goals'].numel() * p['goals'].element_size() for p in policies if p['goals'] is not None),
                   per_operator_bytes=500 * 500 * 8, all_graph_operators_cached=False)
    summary = dict(schema='acfqp.lmta_structure.v45', status='complete',
                   runtime=dict(device='cpu', dtype='float64', torch_threads=torch.get_num_threads(),
                                torch=torch.__version__, numpy=np.__version__, networkx=nx.__version__),
                   counts=dict(counts), coverage=coverage, structural_conditions=conditions,
                   initial_structural_information_restored=all(conditions.values()),
                   max_mean_constant_error=max(r['constant_message_error'] for r in mean),
                   max_weighted_readout_error=max(r['analytic_readout_error'] for r in weighted),
                   encoder_diagnostics=aggregate_diagnostics(encoder_rows, 'scaled_row_range'),
                   q_diagnostics=aggregate_diagnostics(q_rows, 'scaled_row_range'),
                   cost=dict(timing_seconds=dict(timings), storage=storage),
                   environment_samples=0, environment_calls=0, gradient_updates=0, mcts_simulations=0,
                   training_benefit_tested=False, fixed_weights_adopted=False,
                   interpretation='Initial structural information only. Existing weights face a changed input distribution. '
                   'Seed-conditional one-step scores are analytical descriptions, not policy returns. '
                   'MEAN64 is a precision-controlled formula comparison, not a V44 float32 action replay.')
    (output_dir / 'source').mkdir()
    for name in ('scripts/run_lmta_structure_v45.py', 'src/acfqp/science/lmta_structure_v45.py',
                 'src/acfqp/science/lmta_models_v43.py', 'src/acfqp/science/lmta_aim_v43.py'):
        shutil.copyfile(ROOT / name, output_dir / 'source' / Path(name).name)
    shutil.copyfile(ROOT / 'specs/LMTA_STRUCTURE_V45.md', output_dir / 'protocol.md')
    summary['wall_seconds_before_summary_serialization'] = perf_counter() - start
    (output_dir / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(structural_conditions=conditions, coverage=coverage, wall_seconds=summary['wall_seconds_before_summary_serialization'])), flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_structure_v45')
    args = parser.parse_args()
    run(args.output_dir)
