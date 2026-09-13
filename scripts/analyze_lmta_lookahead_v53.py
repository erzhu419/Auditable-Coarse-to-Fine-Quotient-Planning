"""Independent receding-lookahead certificates and retained V52 controls."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import importlib.util
import itertools
import json
import math
from pathlib import Path
import statistics
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('exact_certificate_v52', Path(__file__).with_name('analyze_lmta_exact_v52.py'))
v52 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v52)
METHODS = ['LOOKAHEAD_1', 'LOOKAHEAD_2', 'LOOKAHEAD_FULL']
CONTROLS = {'LOOKAHEAD_1': 'AVERAGE_MYOPIC', 'LOOKAHEAD_FULL': 'AVERAGE_OPTIMAL'}
PROTOCOL = dict(v52.PROTOCOL, methods=METHODS)
TOL = 1e-10


def close(a, b):
    return v52.finite(a) and v52.finite(b) and math.isclose(a, b, rel_tol=TOL, abs_tol=TOL)


def actions(statuses, budget, days):
    legal = [node for node, status in enumerate(statuses) if status == 0]
    cap = min(budget, len(legal))
    allocation = cap if days == 1 else min(cap, (budget + days - 1) // days)
    return list(itertools.combinations(legal, allocation))


def independent_plan(statuses, budget, days, depth, edges, nodes):
    """Cold truncated dynamic program; real days determine every allocation."""
    choices = actions(statuses, budget, days)
    if len(choices) == 1:
        return dict(selected=choices[0], planned_value=None, root_action_values=[])
    _, outcomes = v52.independent_model(edges, nodes)

    @lru_cache(maxsize=None)
    def value(state, b, h, d):
        if d == 0 or h == 0:
            return 0.
        return max(q(state, b, h, d, action) for action in actions(state, b, h))

    def q(state, b, h, d, action):
        return math.fsum(p * (reward + value(after, b - len(action), h - 1, d - 1))
                         for p, after, reward in outcomes(state, action))

    measured = [(action, q(tuple(statuses), budget, days, depth, action)) for action in choices]
    selected, best = max(measured, key=lambda item: item[1])
    return dict(selected=selected, planned_value=best,
                root_action_values=[dict(selected=action, value=number) for action, number in measured])


def verify_case(case, rows, edges, nodes, source_rows=None, source_case=None):
    errors = Counter()

    def check(name, passed):
        if not passed:
            errors[name] += 1

    table = {}
    for row in rows:
        bound = (v52.identity(row) == v52.identity(case) and len(row['statuses']) == nodes
                 and all(status in (0, 1, 2) for status in row['statuses'])
                 and isinstance(row['remaining_budget'], int) and 0 <= row['remaining_budget'] <= case['budget']
                 and isinstance(row['remaining_days'], int) and 1 <= row['remaining_days'] <= case['horizon']
                 and v52.finite(row['value']) and -TOL <= row['value'] <= row['statuses'].count(0) + TOL
                 and v52.finite(row['reach_probability']) and 0 < row['reach_probability'] <= 1 + TOL)
        check('state_binding_or_value', bound)
        if not bound:
            continue
        key = v52.state_key(row)
        check('duplicate_state', key not in table)
        table[key] = row
    source = {v52.state_key(row): row for row in (source_rows or [])}
    method = case['method']
    if method in CONTROLS:
        check('control_source', case.get('value_source') == 'V52_retained'
              and case.get('control_method') == CONTROLS[method] and source_case is not None
              and case['root_value'] == source_case['root_value'] and case['root_selected'] == source_case['root_selected'])
    else:
        check('candidate_value_source', case.get('value_source') == 'V53_full_policy_evaluation'
              and case.get('control_method') is None)
    planned, forced, equations, max_residual = 0, 0, 0, 0.
    _, outcomes = v52.independent_model(edges, nodes)
    root_key = ((0,) * nodes, case['budget'], case['horizon'])
    reach = defaultdict(float, {root_key: 1.})
    work, expected_work = Counter(), Counter()
    decision_seconds, expected_seconds = [], []
    occupancy_terms = 0
    for key, row in sorted(table.items(), key=lambda item: -item[0][2]):
        statuses, budget, days = key
        selected = tuple(sorted(row['selected']))
        choices = actions(statuses, budget, days)
        check('selected_legal_allocation', selected in choices)
        check('state_reach', close(row['reach_probability'], reach[key]))
        if method in CONTROLS:
            old = source.get(key)
            check('control_state_exact', old is not None and row['value'] == old['value'] and row['selected'] == old['selected'])
        if selected not in choices:
            continue
        depth = 1 if method == 'LOOKAHEAD_1' else min(2, days) if method == 'LOOKAHEAD_2' else days
        expected = independent_plan(statuses, budget, days, depth, edges, nodes)
        if len(choices) == 1:
            forced += 1
            check('forced_root_shortcut', row.get('planned_value') is None and row.get('root_action_values') == [])
        else:
            planned += 1
            reported = row.get('root_action_values', [])
            check('root_action_roster', Counter(tuple(sorted(action['selected'])) for action in reported) == Counter(choices))
            values = {tuple(action['selected']): action['value'] for action in expected['root_action_values']}
            check('truncated_action_values', all(tuple(sorted(action['selected'])) in values
                  and v52.finite(action.get('value'))
                  and abs(action['value'] - values[tuple(sorted(action['selected']))]) <= TOL for action in reported))
            check('truncated_choice_and_value', v52.finite(row.get('planned_value'))
                  and abs(row['planned_value'] - values[selected]) <= TOL
                  and values[selected] >= expected['planned_value'] - TOL)
        terms, successors_present = [], True
        for probability, after, reward in outcomes(statuses, selected):
            future = 0.
            if days > 1:
                occupancy_terms += 1
                successor_key = (after, budget - len(selected), days - 1)
                successor = table.get(successor_key)
                check('missing_policy_successor', successor is not None)
                if successor is None:
                    successors_present = False
                    continue
                future = successor['value']
                reach[successor_key] += reach[key] * probability
            terms.append(probability * (reward + future))
        if successors_present:
            residual = abs(row['value'] - math.fsum(terms))
            max_residual = max(max_residual, residual)
            equations += 1
            check('full_policy_bellman', residual <= TOL)
        counts = row.get('decision_work', {})
        check('decision_work_nonnegative', all(isinstance(number, int) and number >= 0 for number in counts.values()))
        check('planner_call_and_forced_counts', counts.get('planner_calls') == 1
              and counts.get('forced_choice') == (1 if len(choices) == 1 else 0))
        check('decision_seconds_nonnegative', v52.finite(row.get('decision_seconds')) and row['decision_seconds'] >= 0)
        work.update(counts)
        expected_work.update({name: number * row['reach_probability'] for name, number in counts.items()})
        decision_seconds.append(row['decision_seconds'])
        expected_seconds.append(row['decision_seconds'] * row['reach_probability'])
    root = table.get(root_key)
    check('root_record', root is not None and root['value'] == case['root_value'] and root['selected'] == case['root_selected']
          and close(root['reach_probability'], 1.))
    for days in range(1, case['horizon'] + 1):
        check('daily_probability_mass', close(math.fsum(row['reach_probability'] for key, row in table.items() if key[2] == days), 1.))
    check('state_record_count', case.get('state_records') == len(rows))
    check('decision_work_sum', Counter(case.get('decision_work', {})) == work)
    recorded_expected = case.get('expected_decision_work', {})
    check('expected_decision_work_sum', set(recorded_expected) == set(expected_work)
          and all(close(recorded_expected[name], number) for name, number in expected_work.items()))
    check('expected_planner_calls', close(recorded_expected.get('planner_calls'), case['horizon']))
    check('decision_time_sum', close(case.get('decision_seconds'), math.fsum(decision_seconds))
          and close(case.get('expected_decision_seconds'), math.fsum(expected_seconds)))
    check('wall_time_partition', close(case.get('wall_seconds'), case.get('decision_seconds', 0) + case.get('evaluation_seconds', 0))
          and all(v52.finite(case.get(field)) and case[field] >= 0 for field in ('wall_seconds', 'evaluation_seconds', 'serialization_seconds')))
    evaluation = case.get('evaluation_work', {})
    check('evaluation_work', all(isinstance(number, int) and number >= 0 for number in evaluation.values())
          and evaluation.get('new_full_policy_backups') == (len(rows) if method == 'LOOKAHEAD_2' else 0)
          and evaluation.get('retained_value_reads') == (0 if method == 'LOOKAHEAD_2' else len(rows))
          and evaluation.get('occupancy_probability_terms') == occupancy_terms)
    return dict(passed=not errors, errors=dict(errors), state_records=len(rows), planned_roots=planned, forced_roots=forced,
                full_policy_equations=equations, maximum_bellman_residual=max_residual)


def descriptive(values):
    available = [value for value in values if value is not None]
    return dict(count=len(values), available_count=len(available), null_count=len(values) - len(available),
        mean=statistics.mean(available) if available else None, minimum=min(available) if available else None,
        maximum=max(available) if available else None, positive_count=sum(value > TOL for value in available),
        negative_count=sum(value < -TOL for value in available), tie_count=sum(abs(value) <= TOL for value in available))


def case_accounting(cases):
    work = {name: Counter() for name in ('decision_work', 'expected_decision_work', 'evaluation_work')}
    for case in cases:
        for name in work:
            work[name].update(case.get(name, {}))
    return dict(case_records=len(cases), **{name: dict(value) for name, value in work.items()},
        expected_nonforced_planner_calls=work['expected_decision_work'].get('planner_calls', 0)
                                        - work['expected_decision_work'].get('forced_choice', 0),
        **{name: math.fsum(case[name] for case in cases if v52.finite(case.get(name))) for name in
           ('wall_seconds', 'decision_seconds', 'evaluation_seconds', 'serialization_seconds', 'expected_decision_seconds')})


def summarize(manifest, cases, states, source_manifest, source_analysis, source_cases, source_states):
    started, errors = perf_counter(), Counter()
    bindings = {seed: panel['p'] for panel in PROTOCOL['panels'] for seed in panel['seeds']}
    expected = Counter(itertools.product(bindings, PROTOCOL['horizons'], METHODS))
    source_ok = (source_manifest.get('status') == 'complete' and source_manifest.get('protocol') == v52.PROTOCOL
                 and source_analysis.get('integrity', {}).get('passed') is True)
    if not source_ok:
        errors['source_V52_not_valid'] += 1
    if (manifest.get('schema') != 'acfqp.lmta_lookahead.v53' or manifest.get('status') != 'complete'
            or manifest.get('protocol') != PROTOCOL or manifest.get('source_directory') != 'reports/lmta_exact_v52'
            or manifest.get('graphs') != source_manifest.get('graphs') or manifest.get('cold_decisions') is not True):
        errors['manifest_or_source_binding'] += 1
    if any(manifest.get(name) != 0 for name in ('new_environment_samples', 'new_environment_calls', 'new_RL_updates', 'new_MCTS_calls')):
        errors['new_environment_or_training_work'] += 1
    counts = Counter(v52.identity(case) for case in cases)
    if counts != expected or manifest.get('completed_cases') != len(cases) or manifest.get('total_state_records') != len(states):
        errors['case_or_manifest_record_roster'] += 1
    graphs = {graph['graph_id']: graph for graph in manifest.get('graphs', [])}
    if Counter(graph['graph_id'] for graph in manifest.get('graphs', [])) != Counter(bindings.keys()):
        errors['graph_roster'] += 1
    for name in ('source_read_seconds', 'graph_reconstruction_seconds', 'whole_runner_seconds', 'runner_cpu_seconds', 'process_peak_rss_bytes'):
        if not v52.finite(manifest.get(name)) or manifest[name] < 0:
            errors['manifest_costs'] += 1
    grouped, old_grouped = defaultdict(list), defaultdict(list)
    for row in states:
        grouped[v52.identity(row)].append(row)
    for row in source_states:
        old_grouped[v52.identity(row)].append(row)
    if grouped.keys() - expected.keys():
        errors['unbound_state_case'] += 1
    old_cases = {v52.identity(case): case for case in source_cases}
    validations = []
    for case in cases:
        identity = v52.identity(case)
        graph, horizon, method = identity
        if identity not in expected or graph not in graphs or case.get('p') != bindings[graph] or case.get('budget') != 2:
            errors['case_binding'] += 1
            continue
        source_identity = (graph, horizon, CONTROLS.get(method))
        checked = verify_case(case, grouped[identity], graphs[graph]['edges'], 7,
                              old_grouped[source_identity], old_cases.get(source_identity))
        validations.append(dict(graph_id=graph, horizon=horizon, method=method, **checked))
        if not checked['passed']:
            errors['invalid_certificate_cases'] += 1
    lookup = {v52.identity(case): case['root_value'] for case in cases if v52.finite(case.get('root_value'))}
    if counts == expected and len(lookup) == len(expected):
        for graph, horizon in itertools.product(bindings, PROTOCOL['horizons']):
            values = [lookup[graph, horizon, method] for method in METHODS]
            if max(values[:2]) > values[2] + TOL:
                errors['full_horizon_upper_bound'] += 1
            if horizon == 1 and max(values) - min(values) > TOL:
                errors['one_day_equality'] += 1
    per_graph, strata = None, None
    if not errors:
        per_graph = []
        for graph, horizon in itertools.product(bindings, PROTOCOL['horizons']):
            myopic, candidate, full = (lookup[graph, horizon, method] for method in METHODS)
            headroom, gain = full - myopic, candidate - myopic
            per_graph.append(dict(graph_id=graph, p=bindings[graph], horizon=horizon,
                values=dict(zip(METHODS, (myopic, candidate, full))), candidate_minus_myopic=gain,
                full_minus_candidate=full - candidate, full_minus_myopic=headroom,
                headroom_fraction=gain / headroom if headroom > TOL else None))
        strata = []
        for panel, horizon in itertools.product(PROTOCOL['panels'], PROTOCOL['horizons']):
            rows = [row for row in per_graph if row['p'] == panel['p'] and row['horizon'] == horizon]
            headroom = math.fsum(row['full_minus_myopic'] for row in rows)
            gain = math.fsum(row['candidate_minus_myopic'] for row in rows)
            strata.append(dict(p=panel['p'], horizon=horizon,
                values={method: descriptive([row['values'][method] for row in rows]) for method in METHODS},
                contrasts={name: descriptive([row[name] for row in rows]) for name in
                    ('candidate_minus_myopic', 'full_minus_candidate', 'full_minus_myopic', 'headroom_fraction')},
                sum_gain_over_sum_headroom=gain / headroom if headroom > TOL else None,
                costs_by_method={method: case_accounting([case for case in cases if case['p'] == panel['p']
                    and case['horizon'] == horizon and case['method'] == method]) for method in METHODS}))
    return dict(schema='acfqp.lmta_lookahead_analysis.v53', protocol=PROTOCOL,
        integrity=dict(passed=not errors, errors=dict(errors), expected_case_records=192, case_records=len(cases),
                       state_records=len(states), case_validations=validations),
        strata=strata, per_graph=per_graph, root_values=cases,
        accounting=dict(new_cases=case_accounting(cases),
            **{name: manifest.get(name) for name in ('source_read_seconds', 'graph_reconstruction_seconds',
               'whole_runner_seconds', 'runner_cpu_seconds', 'process_peak_rss_bytes', 'data_bytes',
               'new_environment_samples', 'new_environment_calls', 'new_RL_updates', 'new_MCTS_calls')},
            retained_V52=source_analysis.get('accounting'), analysis_wall_seconds_before_serialization=perf_counter() - started,
            scope='Every cold decision and policy traversal is charged once. Reach-weighted decision work estimates '
                  'one executed policy trajectory and is not added to exhaustive case work. Serialization is separate. '
                  'V52 costs are retained as historical work, without refund or inclusion in new work.'),
        inference_scope='All graphs and negative candidate gains are retained. Per-graph fractions are null when full-minus-myopic '
            'headroom is at most 1e-10; the ratio of summed gains to summed headroom is a separately labelled aggregate, '
            'not the unweighted mean of graph fractions. Real remaining days determine allocations even in truncated planning. '
            'No confidence interval, adoption Gate, or original-size learnability claim is created.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_lookahead_v53')
    parser.add_argument('--control-dir', type=Path, default=ROOT / 'reports/lmta_exact_v52')
    args = parser.parse_args()
    started = perf_counter()

    def read(directory, name):
        path = directory / name
        return [json.loads(line) for line in path.read_text().splitlines()] if name.endswith('.jsonl') else json.loads(path.read_text())

    report = summarize(read(args.output_dir, 'manifest.json'), read(args.output_dir, 'cases.jsonl'), read(args.output_dir, 'states.jsonl'),
        read(args.control_dir, 'manifest.json'), read(args.control_dir, 'analysis.json'),
        read(args.control_dir, 'cases.jsonl'), read(args.control_dir, 'states.jsonl'))
    report['accounting']['analysis_wall_seconds_including_reads'] = perf_counter() - started
    (args.output_dir / 'analysis.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(integrity_passed=report['integrity']['passed'], strata=report['strata']), indent=2))


if __name__ == '__main__':
    main()
