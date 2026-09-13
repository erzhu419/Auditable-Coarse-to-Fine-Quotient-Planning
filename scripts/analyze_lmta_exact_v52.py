"""Independent finite-state Bellman certificates for the frozen small AIM panel."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import itertools
import json
import math
from pathlib import Path
import statistics
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
TOLERANCE = 1e-10
METHODS = ['AVERAGE_SCORE', 'AVERAGE_MYOPIC', 'AVERAGE_OPTIMAL', 'SCORE_OPTIMAL_BUDGET', 'JOINT_OPTIMAL']
PROTOCOL = dict(nodes=7, budget=2, horizons=[1, 3], panels=[
    dict(p=.25, seeds=list(range(520000, 520016))),
    dict(p=.75, seeds=list(range(520100, 520116)))], methods=METHODS)
GAPS = {'joint_minus_score': ('JOINT_OPTIMAL', 'AVERAGE_SCORE'),
        'average_optimal_minus_score': ('AVERAGE_OPTIMAL', 'AVERAGE_SCORE'),
        'budget_optimal_minus_score': ('SCORE_OPTIMAL_BUDGET', 'AVERAGE_SCORE'),
        'average_optimal_minus_myopic': ('AVERAGE_OPTIMAL', 'AVERAGE_MYOPIC')}


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def identity(row):
    return row.get('graph_id'), row.get('horizon'), row.get('method')


def state_key(row):
    return tuple(row['statuses']), row['remaining_budget'], row['remaining_days']


def independent_model(edges, nodes):
    """Build a checker-local transition kernel; no solver or environment imports."""
    parents = [tuple(u for u, v in edges if v == target) for target in range(nodes)]
    children = [tuple(v for u, v in edges if u == source) for source in range(nodes)]

    def score_subset(statuses, size):
        inactive = {node for node, status in enumerate(statuses) if status == 0}
        chosen = []
        for _ in range(size):
            node = max(sorted(inactive), key=lambda u: math.fsum(
                1. / len(parents[v]) for v in children[u] if v in inactive))
            chosen.append(node)
            inactive.remove(node)
        return tuple(sorted(chosen))

    @lru_cache(maxsize=None)
    def outcomes(statuses, selected):
        sources = {i for i, status in enumerate(statuses) if status == 1} | set(selected)
        targets = [i for i, status in enumerate(statuses) if status == 0 and i not in sources]
        probabilities = []
        for target in targets:
            failure = math.prod(1. - 1. / len(parents[target])
                                for parent in parents[target] if parent in sources)
            probabilities.append(1. - failure)
        certain = {node for node, p in zip(targets, probabilities) if p == 1.}
        uncertain = [(node, p) for node, p in zip(targets, probabilities) if 0. < p < 1.]
        result = []
        for bits in itertools.product((False, True), repeat=len(uncertain)):
            probability = math.prod(p if active else 1. - p for (_, p), active in zip(uncertain, bits))
            activated = certain | {node for (node, _), active in zip(uncertain, bits) if active}
            after = tuple(2 if node in sources else 1 if node in activated else status
                          for node, status in enumerate(statuses))
            result.append((probability, after, len(selected) + len(activated)))
        return tuple(result)

    return score_subset, outcomes


def verify_case(case, state_rows, edges, nodes):
    """Check every retained state using independently enumerated legal actions."""
    errors = Counter()
    table = {}
    for row in state_rows:
        valid = (identity(row) == identity(case) and len(row['statuses']) == nodes
                 and all(status in (0, 1, 2) for status in row['statuses'])
                 and isinstance(row['remaining_budget'], int) and 0 <= row['remaining_budget'] <= case['budget']
                 and isinstance(row['remaining_days'], int) and 1 <= row['remaining_days'] <= case['horizon']
                 and finite(row['value']) and -TOLERANCE <= row['value'] <= row['statuses'].count(0) + TOLERANCE)
        if not valid:
            errors['state_binding_or_value'] += 1
            continue
        key = state_key(row)
        if key in table:
            errors['duplicate_state'] += 1
        table[key] = row
    score_subset, outcomes = independent_model(edges, nodes)
    equations, comparisons, max_residual = 0, 0, 0.
    for (statuses, budget, days), row in table.items():
        legal = tuple(i for i, status in enumerate(statuses) if status == 0)
        cap = min(budget, len(legal))
        selected = tuple(sorted(row['selected']))
        if len(set(selected)) != len(selected) or not set(selected) <= set(legal) or len(selected) > cap:
            errors['illegal_selected'] += 1
            continue
        size = cap if days == 1 else min(cap, (budget + days - 1) // days)
        method = case['method']
        if method == 'AVERAGE_SCORE':
            actions = [score_subset(statuses, size)]
        elif method in ('AVERAGE_MYOPIC', 'AVERAGE_OPTIMAL'):
            actions = list(itertools.combinations(legal, size))
        elif method == 'SCORE_OPTIMAL_BUDGET':
            actions = [score_subset(statuses, k) for k in ([cap] if days == 1 else range(cap + 1))]
        else:
            actions = [a for k in ([cap] if days == 1 else range(cap + 1)) for a in itertools.combinations(legal, k)]
        if selected not in actions:
            errors['selected_outside_policy_actions'] += 1
            continue

        def q_value(action, continuation=True):
            terms = []
            for probability, after, reward in outcomes(statuses, action):
                future = 0.
                if continuation and days > 1:
                    successor = table.get((after, budget - len(action), days - 1))
                    if successor is None:
                        errors['missing_successor'] += 1
                        return None
                    future = successor['value']
                terms.append(probability * (reward + future))
            return math.fsum(terms)

        chosen_value = q_value(selected)
        if chosen_value is not None:
            residual = abs(row['value'] - chosen_value)
            max_residual = max(max_residual, residual)
            equations += 1
            if residual > TOLERANCE:
                errors['bellman_equation'] += 1
        action_values = [q_value(action, method != 'AVERAGE_MYOPIC') for action in actions]
        if all(value is not None for value in action_values):
            comparisons += 1
            if action_values[actions.index(selected)] < max(action_values) - TOLERANCE:
                errors['action_optimality'] += 1
    root = table.get(((0,) * nodes, case['budget'], case['horizon']))
    if (root is None or not finite(case.get('root_value')) or abs(root['value'] - case['root_value']) > TOLERANCE
            or sorted(root['selected']) != sorted(case['root_selected'])):
        errors['root_record_binding'] += 1
    if case.get('certificate_records') != len(state_rows):
        errors['certificate_record_count'] += 1
    if case.get('counters', {}).get('dp_states') != len(state_rows):
        errors['dp_state_count'] += 1
    return dict(passed=not errors, errors=dict(errors), states=len(state_rows), bellman_equations=equations,
                action_comparisons=comparisons, maximum_bellman_residual=max_residual,
                independent_kernel_builds=outcomes.cache_info().currsize)


def descriptive(values):
    return dict(count=len(values), mean=statistics.mean(values), minimum=min(values), maximum=max(values),
                positive_count=sum(value > TOLERANCE for value in values))


def summarize(manifest, cases, states):
    started = perf_counter()
    errors = Counter()
    bindings = {seed: panel['p'] for panel in PROTOCOL['panels'] for seed in panel['seeds']}
    graphs = manifest.get('graphs', [])
    if manifest.get('schema') != 'acfqp.lmta_exact.v52' or manifest.get('status') != 'complete' or manifest.get('protocol') != PROTOCOL:
        errors['manifest_protocol_or_status'] += 1
    if not manifest.get('cold_cache') or any(manifest.get(field) != 0 for field in
            ('new_environment_samples', 'new_environment_calls', 'new_RL_updates', 'new_MCTS_calls')):
        errors['cold_cache_and_zero_sampling'] += 1
    if manifest.get('completed_cases') != len(cases) or manifest.get('total_state_records') != len(states):
        errors['manifest_record_counts'] += 1
    if not all(finite(manifest.get(field)) and manifest[field] >= 0 for field in
               ('graph_generation_seconds', 'whole_runner_seconds', 'runner_cpu_seconds', 'process_peak_rss_bytes')):
        errors['manifest_accounting'] += 1
    graph_counts = Counter(graph.get('graph_id') for graph in graphs)
    if graph_counts != Counter(bindings.keys()):
        errors['graph_roster'] += 1
    valid_graphs = {}
    for graph in graphs:
        edges = graph['edges']
        if (graph.get('p') != bindings.get(graph.get('graph_id')) or graph.get('nodes') != 7
                or len({tuple(edge) for edge in edges}) != len(edges)
                or not all(len(edge) == 2 and all(isinstance(node, int) and 0 <= node < 7 for node in edge)
                           and edge[0] != edge[1] for edge in edges)):
            errors['graph_binding_or_edges'] += 1
        else:
            valid_graphs[graph['graph_id']] = graph
    expected = Counter(itertools.product(bindings, PROTOCOL['horizons'], METHODS))
    case_counts = Counter(identity(case) for case in cases)
    if case_counts != expected:
        errors['case_roster'] += 1
    grouped = defaultdict(list)
    for row in states:
        grouped[identity(row)].append(row)
    if grouped.keys() - expected.keys():
        errors['unbound_state_cases'] += 1
    validations = []
    for case in cases:
        key = identity(case)
        if (key not in expected or case.get('budget') != 2 or case.get('p') != bindings.get(case.get('graph_id'))
                or case.get('graph_id') not in valid_graphs):
            errors['case_binding'] += 1
            continue
        checked = verify_case(case, grouped[key], valid_graphs[case['graph_id']]['edges'], 7)
        validations.append(dict(graph_id=key[0], horizon=key[1], method=key[2], **checked))
        if not checked['passed']:
            errors['invalid_certificate_cases'] += 1
        if (not all(finite(case.get(field)) and case[field] >= 0 for field in ('wall_seconds', 'certificate_serialization_seconds'))
                or not all(isinstance(value, int) and value >= 0 for value in case.get('counters', {}).values())):
            errors['case_accounting'] += 1
    lookup = {identity(case): case['root_value'] for case in cases if finite(case.get('root_value'))}
    if case_counts == expected and len(lookup) == len(expected):
        for graph, horizon in itertools.product(bindings, PROTOCOL['horizons']):
            values = {method: lookup[graph, horizon, method] for method in METHODS}
            relations = [('AVERAGE_SCORE', 'AVERAGE_OPTIMAL'), ('AVERAGE_OPTIMAL', 'JOINT_OPTIMAL'),
                         ('AVERAGE_SCORE', 'SCORE_OPTIMAL_BUDGET'), ('SCORE_OPTIMAL_BUDGET', 'JOINT_OPTIMAL'),
                         ('AVERAGE_MYOPIC', 'AVERAGE_OPTIMAL')]
            if any(values[a] > values[b] + TOLERANCE for a, b in relations):
                errors['policy_inclusion'] += 1
            if horizon == 1 and (max(values[m] for m in ('JOINT_OPTIMAL', 'AVERAGE_OPTIMAL', 'AVERAGE_MYOPIC'))
                    - min(values[m] for m in ('JOINT_OPTIMAL', 'AVERAGE_OPTIMAL', 'AVERAGE_MYOPIC')) > TOLERANCE
                    or abs(values['SCORE_OPTIMAL_BUDGET'] - values['AVERAGE_SCORE']) > TOLERANCE):
                errors['one_day_control'] += 1
    strata = None
    if not errors:
        strata = [dict(p=panel['p'], horizon=horizon,
            values={method: descriptive([lookup[seed, horizon, method] for seed in panel['seeds']]) for method in METHODS},
            gaps={name: descriptive([lookup[seed, horizon, a] - lookup[seed, horizon, b] for seed in panel['seeds']])
                  for name, (a, b) in GAPS.items()}) for panel in PROTOCOL['panels'] for horizon in PROTOCOL['horizons']]
    totals = Counter()
    for case in cases:
        totals.update({name: value for name, value in case.get('counters', {}).items() if finite(value)})
    return dict(schema='acfqp.lmta_exact_analysis.v52', protocol=PROTOCOL,
        integrity=dict(passed=not errors, errors=dict(errors), case_records=len(cases), expected_case_records=320,
            state_records=len(states), case_validations=validations), strata=strata, root_values=cases,
        accounting=dict(new_environment_samples=manifest.get('new_environment_samples'),
            new_environment_calls=manifest.get('new_environment_calls'),
            new_RL_updates=manifest.get('new_RL_updates'), new_MCTS_calls=manifest.get('new_MCTS_calls'),
            cold_case_solve_seconds=math.fsum(case['wall_seconds'] for case in cases if finite(case.get('wall_seconds'))),
            certificate_serialization_seconds=math.fsum(case['certificate_serialization_seconds'] for case in cases
                                                       if finite(case.get('certificate_serialization_seconds'))),
            summed_case_counters=dict(totals), graph_generation_seconds=manifest.get('graph_generation_seconds'),
            whole_runner_seconds=manifest.get('whole_runner_seconds'), runner_cpu_seconds=manifest.get('runner_cpu_seconds'),
            process_peak_rss_bytes=manifest.get('process_peak_rss_bytes'), data_bytes=manifest.get('data_bytes'),
            retained_prior_runs=manifest.get('retained_prior_runs'),
            analysis_wall_seconds_before_serialization=perf_counter() - started,
            scope='All case costs are retained, including invalid or incomplete certificates. Old environment and supervised '
                  'training costs remain in their original reports; none is refunded or charged again here.'),
        inference_scope='Exact means full finite-model enumeration in floating point. Strata retain all fixed graphs, including '
            'zero gaps; positive counts use tolerance 1e-10. No confidence intervals or adoption Gate are created. '
            'These small-graph value bounds do not establish learnability or performance on the original 500-node task.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_exact_v52')
    args = parser.parse_args()
    started = perf_counter()
    manifest = json.loads((args.output_dir / 'manifest.json').read_text())
    cases = [json.loads(line) for line in (args.output_dir / 'cases.jsonl').read_text().splitlines()]
    states = [json.loads(line) for line in (args.output_dir / 'states.jsonl').read_text().splitlines()]
    report = summarize(manifest, cases, states)
    report['accounting']['analysis_wall_seconds_including_reads'] = perf_counter() - started
    (args.output_dir / 'analysis.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(integrity_passed=report['integrity']['passed'], strata=report['strata']), indent=2))


if __name__ == '__main__':
    main()
