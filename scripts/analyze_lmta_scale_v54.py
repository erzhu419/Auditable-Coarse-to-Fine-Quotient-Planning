"""Independent bounded-scale lookahead certificates and unconditional costs."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import importlib.util
import itertools
import json
import math
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('lookahead_certificate_v53', Path(__file__).with_name('analyze_lmta_lookahead_v53.py'))
v53 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v53)
v52, METHODS, TOL = v53.v52, v53.METHODS, 1e-10
LIMITS = dict(max_planner_action_values=2000000, max_policy_states=100000, max_wall_seconds=60.)
PANELS = [dict(nodes=7, stratum='sparse', expected_degree=1.5, p=.25, seeds=list(range(540000, 540016))),
          dict(nodes=7, stratum='dense', expected_degree=4.5, p=.75, seeds=list(range(540100, 540116))),
          dict(nodes=9, stratum='sparse', expected_degree=1.5, p=.1875, seeds=list(range(540200, 540216))),
          dict(nodes=9, stratum='dense', expected_degree=4.5, p=.5625, seeds=list(range(540300, 540316)))]
PROTOCOL = dict(budget=2, horizon=3, methods=METHODS, panels=PANELS, limits=LIMITS)


def identity(row):
    return row.get('graph_id'), row.get('horizon'), row.get('method')


def verify_case(case, rows, edges, nodes, limits=LIMITS):
    """Verify a fresh policy certificate, or account for its explicit interruption."""
    errors = Counter()

    def check(name, passed):
        if not passed:
            errors[name] += 1

    complete = case.get('status') == 'complete'
    check('terminal_status', case.get('status') in ('complete', 'resource_limit'))
    check('new_value_source', case.get('value_source') == 'V54_full_policy_evaluation'
          and case.get('control_method') is None)
    table, work = {}, Counter()
    decision_seconds = []
    planned, forced = 0, 0
    for row in rows:
        bound = (all(row.get(name) == case.get(name) for name in
                    ('graph_id', 'horizon', 'method', 'nodes', 'stratum', 'p', 'budget'))
                 and len(row['statuses']) == nodes and all(status in (0, 1, 2) for status in row['statuses'])
                 and isinstance(row['remaining_budget'], int) and 0 <= row['remaining_budget'] <= case['budget']
                 and isinstance(row['remaining_days'], int) and 1 <= row['remaining_days'] <= case['horizon'])
        check('state_binding', bound)
        if not bound:
            continue
        key = v52.state_key(row)
        check('duplicate_state', key not in table)
        table[key] = row
        available = v53.actions(key[0], key[1], key[2])
        check('selected_legal_allocation', tuple(sorted(row['selected'])) in available)
        check('state_value', (row['value'] is None and not complete) or
              (v52.finite(row['value']) and -TOL <= row['value'] <= row['statuses'].count(0) + TOL))
        check('state_probability', (row.get('reach_probability') is None and not complete) or
              (complete and v52.finite(row.get('reach_probability')) and 0 < row['reach_probability'] <= 1 + TOL))
        counts = row.get('decision_work', {})
        check('decision_work', all(isinstance(number, int) and number >= 0 for number in counts.values())
              and counts.get('planner_calls') == 1 and counts.get('forced_choice') == int(len(available) == 1))
        check('decision_time', v52.finite(row.get('decision_seconds')) and row['decision_seconds'] >= 0)
        work.update(counts)
        decision_seconds.append(row['decision_seconds'])
        statuses, budget, days = key
        selected = tuple(sorted(row['selected']))
        if selected not in available:
            continue
        depth = 1 if case['method'] == 'LOOKAHEAD_1' else min(2, days) if case['method'] == 'LOOKAHEAD_2' else days
        expected = v53.independent_plan(statuses, budget, days, depth, edges, nodes)
        if len(available) == 1:
            forced += 1
            check('forced_root_shortcut', row.get('planned_value') is None and row.get('root_action_values') == [])
        else:
            planned += 1
            reported = row.get('root_action_values', [])
            values = {tuple(action['selected']): action['value'] for action in expected['root_action_values']}
            check('root_action_roster', Counter(tuple(sorted(action['selected'])) for action in reported) == Counter(available))
            check('truncated_action_values', all(tuple(sorted(action['selected'])) in values
                  and v52.finite(action.get('value')) and abs(action['value'] - values[tuple(sorted(action['selected']))]) <= TOL
                  for action in reported))
            check('truncated_choice', v52.finite(row.get('planned_value'))
                  and abs(row['planned_value'] - values[selected]) <= TOL and values[selected] >= expected['planned_value'] - TOL)
    check('state_count_and_decision_work', case.get('state_records') == len(rows)
          and Counter(case.get('decision_work', {})) == work and work.get('planner_calls') == len(rows))
    check('decision_time_sum', v53.close(case.get('decision_seconds'), math.fsum(decision_seconds)))
    check('case_time_partition', all(v52.finite(case.get(name)) and case[name] >= 0 for name in
          ('wall_seconds', 'decision_seconds', 'evaluation_seconds', 'serialization_seconds'))
          and v53.close(case.get('wall_seconds'), case.get('decision_seconds', 0) + case.get('evaluation_seconds', 0)))
    check_time = case.get('last_limit_check_seconds')
    check('last_limit_check_time', v52.finite(check_time) and 0 <= check_time <= case.get('wall_seconds', -1) + TOL)
    observed = dict(max_planner_action_values=work.get('action_value_evaluations', 0),
                    max_policy_states=len(rows), max_wall_seconds=check_time)
    triggered = [name for name in LIMITS if v52.finite(observed[name]) and observed[name] >= limits[name]]
    check('limit_boundary_and_reason', (not triggered and case.get('stop_reason') is None) if complete else
          (bool(triggered) and case.get('stop_reason') == triggered[0]))
    evaluation = case.get('evaluation_work', {})
    check('evaluation_work', all(isinstance(number, int) and number >= 0 for number in evaluation.values())
          and evaluation.get('retained_value_reads') == 0
          and evaluation.get('new_full_policy_backups') == sum(row['value'] is not None for row in rows))
    equations, maximum_residual = 0, 0.
    check('initial_state_recorded', ((0,) * nodes, case['budget'], case['horizon']) in table)
    if complete and not errors:
        check('complete_reason', case.get('stop_reason') is None)
        root_key = ((0,) * nodes, case['budget'], case['horizon'])
        root = table.get(root_key)
        check('root_binding', root is not None and case.get('root_value') == root['value']
              and case.get('root_selected') == root['selected'])
        _, outcomes = v52.independent_model(edges, nodes)
        reach, expected_work = defaultdict(float, {root_key: 1.}), Counter()
        expected_seconds, occupancy_terms = [], 0
        for key, row in sorted(table.items(), key=lambda item: -item[0][2]):
            statuses, budget, days = key
            selected = tuple(sorted(row['selected']))
            choices = v53.actions(statuses, budget, days)
            check('state_reach', v53.close(row['reach_probability'], reach[key]))
            if selected not in choices:
                continue
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
            if successors_present and v52.finite(row['value']):
                residual = abs(row['value'] - math.fsum(terms))
                equations += 1
                maximum_residual = max(maximum_residual, residual)
                check('full_policy_bellman', residual <= TOL)
            expected_work.update({name: number * row['reach_probability'] for name, number in row['decision_work'].items()})
            expected_seconds.append(row['decision_seconds'] * row['reach_probability'])
        for days in range(1, case['horizon'] + 1):
            check('daily_probability_mass', v53.close(math.fsum(row['reach_probability'] for key, row in table.items() if key[2] == days), 1.))
        recorded = case.get('expected_decision_work') or {}
        check('expected_work', set(recorded) == set(expected_work)
              and all(v53.close(recorded[name], value) for name, value in expected_work.items())
              and v53.close(recorded.get('planner_calls'), case['horizon']))
        check('expected_time', v53.close(case.get('expected_decision_seconds'), math.fsum(expected_seconds)))
        check('occupancy_work', evaluation.get('occupancy_probability_terms') == occupancy_terms)
    elif not complete:
        check('resource_limit_no_quality', case.get('root_value') is None and case.get('root_selected') is None
              and case.get('expected_decision_work') is None and case.get('expected_decision_seconds') is None
              and evaluation.get('occupancy_probability_terms') == 0)
    return dict(passed=not errors, errors=dict(errors), status=case.get('status'), state_records=len(rows),
        quality_verified=complete and not errors, planned_roots=planned, forced_roots=forced,
        full_policy_equations=equations, maximum_bellman_residual=maximum_residual if complete else None)


def case_accounting(cases):
    work = {name: Counter() for name in ('decision_work', 'evaluation_work')}
    for case in cases:
        for name in work:
            work[name].update(case.get(name, {}))
    all_complete = bool(cases) and all(case.get('status') == 'complete' for case in cases)
    expected = Counter()
    if all_complete:
        for case in cases:
            expected.update(case.get('expected_decision_work') or {})
    return dict(case_records=len(cases), complete_cases=sum(case.get('status') == 'complete' for case in cases),
        resource_limited_cases=sum(case.get('status') == 'resource_limit' for case in cases),
        state_records=sum(case.get('state_records', 0) for case in cases),
        **{name: dict(value) for name, value in work.items()},
        **{name: math.fsum(case[name] for case in cases if v52.finite(case.get(name))) for name in
           ('wall_seconds', 'decision_seconds', 'evaluation_seconds', 'serialization_seconds')},
        expected_decision_work=dict(expected) if all_complete else None,
        expected_decision_seconds=math.fsum(case['expected_decision_seconds'] for case in cases
            if v52.finite(case.get('expected_decision_seconds'))) if all_complete else None,
        expected_nonforced_planner_calls=expected.get('planner_calls', 0) - expected.get('forced_choice', 0) if all_complete else None)


def stratum_summary(panel, cases, integrity_passed):
    """An incomplete stratum has costs and coverage, but no filtered quality mean."""
    expected = Counter(itertools.product(panel['seeds'], METHODS))
    roster = Counter((case['graph_id'], case['method']) for case in cases)
    complete = integrity_passed and roster == expected and all(case['status'] == 'complete' for case in cases)
    result = dict(nodes=panel['nodes'], stratum=panel['stratum'], expected_degree=panel['expected_degree'], p=panel['p'],
        quality_complete=complete, expected_graphs=len(panel['seeds']),
        terminal_cases=len(cases), complete_cases=sum(case['status'] == 'complete' for case in cases),
        resource_limited_cases=sum(case['status'] == 'resource_limit' for case in cases),
        costs_by_method={method: case_accounting([case for case in cases if case['method'] == method]) for method in METHODS},
        values=None, contrasts=None, per_graph=None, sum_gain_over_sum_headroom=None)
    if complete:
        lookup = {(case['graph_id'], case['method']): case['root_value'] for case in cases}
        rows = []
        for graph in panel['seeds']:
            myopic, candidate, full = (lookup[graph, method] for method in METHODS)
            gain, headroom = candidate - myopic, full - myopic
            rows.append(dict(graph_id=graph, values=dict(zip(METHODS, (myopic, candidate, full))),
                candidate_minus_myopic=gain, full_minus_candidate=full - candidate, full_minus_myopic=headroom,
                headroom_fraction=gain / headroom if headroom > TOL else None))
        headroom = math.fsum(row['full_minus_myopic'] for row in rows)
        result.update(values={method: v53.descriptive([row['values'][method] for row in rows]) for method in METHODS},
            contrasts={name: v53.descriptive([row[name] for row in rows]) for name in
                ('candidate_minus_myopic', 'full_minus_candidate', 'full_minus_myopic', 'headroom_fraction')},
            per_graph=rows, sum_gain_over_sum_headroom=math.fsum(row['candidate_minus_myopic'] for row in rows) / headroom
                if headroom > TOL else None)
    return result


def summarize(manifest, cases, states, source_analysis):
    started, errors = perf_counter(), Counter()
    bindings = {seed: panel for panel in PANELS for seed in panel['seeds']}
    expected = Counter(itertools.product(bindings, [3], METHODS))
    if (manifest.get('schema') != 'acfqp.lmta_scale.v54' or manifest.get('status') != 'complete'
            or manifest.get('protocol') != PROTOCOL or manifest.get('source_directory') != 'reports/lmta_lookahead_v53'
            or manifest.get('cold_decisions') is not True):
        errors['manifest_protocol'] += 1
    if source_analysis.get('integrity', {}).get('passed') is not True:
        errors['source_V53_not_valid'] += 1
    if any(manifest.get(name) != 0 for name in ('new_environment_samples', 'new_environment_calls', 'new_RL_updates', 'new_MCTS_calls')):
        errors['unexpected_environment_or_training_work'] += 1
    counts = Counter(identity(case) for case in cases)
    terminal = counts == expected and all(case.get('status') in ('complete', 'resource_limit') for case in cases)
    successful = sum(case.get('status') == 'complete' for case in cases)
    limited = sum(case.get('status') == 'resource_limit' for case in cases)
    if (not terminal or manifest.get('completed_cases') != len(cases) or manifest.get('successful_cases') != successful
            or manifest.get('resource_limited_cases') != limited or manifest.get('total_state_records') != len(states)):
        errors['case_roster_or_manifest_counts'] += 1
    graphs = manifest.get('graphs', [])
    if Counter(graph.get('graph_id') for graph in graphs) != Counter(bindings.keys()):
        errors['graph_roster'] += 1
    valid_graphs = {}
    for graph in graphs:
        panel = bindings.get(graph.get('graph_id'))
        if panel is None or any(graph.get(name) != panel[name] for name in ('nodes', 'stratum', 'expected_degree', 'p')):
            errors['graph_binding'] += 1
            continue
        edges, nodes = graph['edges'], panel['nodes']
        if (len({tuple(edge) for edge in edges}) != len(edges) or not all(len(edge) == 2 and edge[0] != edge[1]
                and all(isinstance(node, int) and 0 <= node < nodes for node in edge) for edge in edges)):
            errors['graph_edges'] += 1
        else:
            valid_graphs[graph['graph_id']] = graph
    for name in ('source_read_seconds', 'graph_generation_seconds', 'whole_runner_seconds', 'runner_cpu_seconds', 'process_peak_rss_bytes'):
        if not v52.finite(manifest.get(name)) or manifest[name] < 0:
            errors['manifest_costs'] += 1
    grouped = defaultdict(list)
    for row in states:
        grouped[identity(row)].append(row)
    if grouped.keys() - expected.keys():
        errors['unbound_state_case'] += 1
    validations = []
    for case in cases:
        key = identity(case)
        panel = bindings.get(case.get('graph_id'))
        if (key not in expected or case['graph_id'] not in valid_graphs or case.get('budget') != 2
                or panel is None or any(case.get(name) != panel[name] for name in ('nodes', 'stratum', 'p'))):
            errors['case_binding'] += 1
            continue
        graph = valid_graphs[case['graph_id']]
        checked = verify_case(case, grouped[key], graph['edges'], graph['nodes'])
        validations.append(dict(graph_id=key[0], horizon=key[1], method=key[2], **checked))
        if not checked['passed']:
            errors['invalid_case_certificate_or_costs'] += 1
    lookup = {identity(case): case for case in cases}
    if counts == expected:
        for graph in bindings:
            rows = [lookup[graph, 3, method] for method in METHODS]
            if all(row['status'] == 'complete' and v52.finite(row['root_value']) for row in rows):
                if max(row['root_value'] for row in rows[:2]) > rows[2]['root_value'] + TOL:
                    errors['full_horizon_upper_bound'] += 1
    strata = [stratum_summary(panel, [case for case in cases if case.get('nodes') == panel['nodes']
               and case.get('stratum') == panel['stratum']], not errors) for panel in PANELS]
    return dict(schema='acfqp.lmta_scale_analysis.v54', protocol=PROTOCOL,
        integrity=dict(passed=not errors, errors=dict(errors), terminal_execution_complete=terminal,
            expected_case_records=192, case_records=len(cases), state_records=len(states), successful_cases=successful,
            resource_limited_cases=limited, case_validations=validations),
        complete_quality_evidence=not errors and successful == 192, strata=strata, root_values=cases,
        accounting=dict(new_cases=case_accounting(cases),
            **{name: manifest.get(name) for name in ('source_read_seconds', 'graph_generation_seconds', 'whole_runner_seconds',
               'runner_cpu_seconds', 'process_peak_rss_bytes', 'data_bytes', 'new_environment_samples', 'new_environment_calls',
               'new_RL_updates', 'new_MCTS_calls')}, retained_V53=source_analysis.get('accounting'),
            analysis_wall_seconds_before_serialization=perf_counter() - started,
            scope='All interrupted and completed decisions, policy evaluations and serializations remain charged. '
                  'Limits are checked after a paid cold decision, so an overshooting decision is included in full. '
                  'Reach-weighted work is a separate expected trajectory quantity, not an extra cost. V53 remains historical work.'),
        inference_scope='The 64 new graphs have fixed expected degrees at N=7 and N=9. Any incomplete stratum has null '
            'quality means, contrasts and retention summaries; completed graphs are not selected into a replacement cohort. '
            'Negative gains are retained and zero-headroom ratios are null. Ratios of total gain to total headroom are '
            'labelled separately from per-graph fractions. Terminal execution and complete quality evidence are distinct. '
            'No confidence interval, adoption Gate, or original-size learnability claim is created.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_scale_v54')
    parser.add_argument('--control-dir', type=Path, default=ROOT / 'reports/lmta_lookahead_v53')
    args = parser.parse_args()
    started = perf_counter()
    manifest = json.loads((args.output_dir / 'manifest.json').read_text())
    cases = [json.loads(line) for line in (args.output_dir / 'cases.jsonl').read_text().splitlines()]
    states = [json.loads(line) for line in (args.output_dir / 'states.jsonl').read_text().splitlines()]
    old = json.loads((args.control_dir / 'analysis.json').read_text())
    report = summarize(manifest, cases, states, old)
    report['accounting']['analysis_wall_seconds_including_reads'] = perf_counter() - started
    (args.output_dir / 'analysis.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(integrity_passed=report['integrity']['passed'], complete_quality_evidence=report['complete_quality_evidence'],
                         strata=report['strata']), indent=2))


if __name__ == '__main__':
    main()
