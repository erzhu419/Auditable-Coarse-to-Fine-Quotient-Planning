"""Cold terminal-expectation replay: numeric validity and action preservation."""
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
v52, TOL = v53.v52, 1e-10
METHOD, SOURCE_METHOD = 'LOOKAHEAD_FULL_ANALYTIC', 'LOOKAHEAD_FULL'
LIMITS = dict(max_planner_action_values=2000000, max_policy_states=100000, max_wall_seconds=60.)
PANELS = [dict(nodes=7, stratum='sparse', expected_degree=1.5, p=.25, seeds=list(range(550000, 550016))),
          dict(nodes=7, stratum='dense', expected_degree=4.5, p=.75, seeds=list(range(550100, 550116))),
          dict(nodes=9, stratum='sparse', expected_degree=1.5, p=.1875, seeds=list(range(550200, 550216))),
          dict(nodes=9, stratum='dense', expected_degree=4.5, p=.5625, seeds=list(range(550300, 550316)))]
PROTOCOL = dict(budget=2, horizon=3, method=METHOD, source_method=SOURCE_METHOD, panels=PANELS, limits=LIMITS)


def verify_row(row, source, edges, nodes):
    errors = Counter()

    def check(name, passed):
        if not passed:
            errors[name] += 1

    check('source_state_binding', row.get('method') == METHOD and row.get('source_method') == SOURCE_METHOD
          and all(row.get(name) == source.get(name) for name in ('graph_id', 'nodes', 'stratum', 'p', 'budget', 'horizon',
                                                              'statuses', 'remaining_budget', 'remaining_days')))
    statuses, budget, days = v52.state_key(source)
    choices = v53.actions(statuses, budget, days)
    selected = tuple(row['selected'])
    check('selected_legal_allocation', selected in choices)
    expected = v53.independent_plan(statuses, budget, days, days, edges, nodes)
    independent_difference = source_difference = source_value_difference = None
    value_agreement = True
    if len(choices) == 1:
        check('forced_shortcut', row.get('planned_value') is None and row.get('root_action_values') == [] and selected == choices[0])
    else:
        reported = row.get('root_action_values', [])
        roster = Counter(tuple(action['selected']) for action in reported)
        check('action_roster', roster == Counter(choices))
        expected_q = {tuple(action['selected']): action['value'] for action in expected['root_action_values']}
        source_q = {tuple(action['selected']): action['value'] for action in source['root_action_values']}
        numeric = all(tuple(action['selected']) in expected_q and tuple(action['selected']) in source_q
                      and v52.finite(action.get('value')) for action in reported)
        if numeric and reported:
            values = {tuple(action['selected']): action['value'] for action in reported}
            maximum = max(values.values())
            best = min(action for action, value in values.items() if value == maximum)
            check('reported_strict_choice', selected == best and row.get('planned_value') == maximum)
            independent_difference = max(abs(action['value'] - expected_q[tuple(action['selected'])]) for action in reported)
            source_difference = max(abs(action['value'] - source_q[tuple(action['selected'])]) for action in reported)
            source_value_difference = abs(maximum - source['value'])
            value_agreement = max(independent_difference, source_difference, source_value_difference) <= TOL
        else:
            value_agreement = False
        check('Q_and_source_value_tolerance', value_agreement)
    counts = row.get('decision_work', {})
    check('decision_work', all(isinstance(number, int) and number >= 0 for number in counts.values())
          and counts.get('planner_calls') == 1 and counts.get('forced_choice') == int(len(choices) == 1)
          and isinstance(counts.get('analytic_expectation_calls'), int) and isinstance(counts.get('analytic_probability_terms'), int)
          and counts.get('target_probability_evaluations', -1) >= counts.get('analytic_probability_terms', 0))
    check('action_value_work_partition', counts.get('action_value_evaluations') ==
          counts.get('kernel_builds', 0) + counts.get('kernel_cache_hits', 0) + counts.get('analytic_expectation_calls', 0))
    check('unchanged_search_scope', all(counts.get(name) == source['decision_work'].get(name)
                                      for name in ('dp_states', 'action_value_evaluations')))
    if len(choices) == 1:
        check('forced_work', all(number == 0 for name, number in counts.items() if name not in ('planner_calls', 'forced_choice')))
    else:
        check('analytic_work_present', counts.get('analytic_expectation_calls', 0) > 0
              and counts.get('action_value_evaluations', 0) >= counts.get('analytic_expectation_calls', 0))
        if days == 1:
            check('terminal_analytic_work', counts.get('analytic_expectation_calls') == len(choices)
                  and counts.get('analytic_probability_terms') == sum(len(statuses) - len(action) - sum(s != 0 for s in statuses) for action in choices)
                  and all(counts.get(name, 0) == 0 for name in ('kernel_builds', 'transition_outcomes', 'bellman_expectation_terms')))
    check('decision_seconds', v52.finite(row.get('decision_seconds')) and row['decision_seconds'] >= 0)
    return dict(passed=not errors, errors=dict(errors), action_preserved=row['selected'] == source['selected'],
        value_agreement=value_agreement, maximum_abs_independent_Q_difference=independent_difference,
        maximum_abs_source_Q_difference=source_difference, source_value_difference=source_value_difference)


def verify_case(case, rows, source_case, source_rows, edges, nodes, limits=LIMITS):
    errors = Counter()
    complete = case.get('status') == 'complete'
    if case.get('status') not in ('complete', 'resource_limit'):
        errors['terminal_status'] += 1
    if case.get('method') != METHOD or case.get('source_method') != SOURCE_METHOD or any(case.get(name) != source_case.get(name)
            for name in ('graph_id', 'nodes', 'stratum', 'p', 'budget', 'horizon')):
        errors['source_case_binding'] += 1
    source = {v52.state_key(row): row for row in source_rows}
    keys = [v52.state_key(row) for row in rows]
    expected_keys = [v52.state_key(row) for row in source_rows]
    if keys != expected_keys[:len(rows)] or (complete and len(rows) != len(source_rows)):
        errors['replay_source_order_and_coverage'] += 1
    work, weighted = Counter(), Counter()
    seconds, weighted_seconds, checked = [], [], []
    root_changes = nonroot_changes = 0
    root_key = ((0,) * nodes, case['budget'], case['horizon'])
    for row in rows:
        old = source.get(v52.state_key(row))
        if old is None:
            errors['unknown_source_state'] += 1
            continue
        result = verify_row(row, old, edges, nodes)
        errors.update(result['errors'])
        checked.append(result)
        if not result['action_preserved']:
            root_changes += v52.state_key(row) == root_key
            nonroot_changes += v52.state_key(row) != root_key
        work.update(row['decision_work'])
        weighted.update({name: number * old['reach_probability'] for name, number in row['decision_work'].items()})
        seconds.append(row['decision_seconds'])
        weighted_seconds.append(row['decision_seconds'] * old['reach_probability'])
    if (case.get('state_records') != len(rows) or case.get('source_state_records') != len(source_rows)
            or Counter(case.get('decision_work', {})) != work or work.get('planner_calls') != len(rows)):
        errors['case_work_or_record_counts'] += 1
    if not v53.close(case.get('decision_seconds'), math.fsum(seconds)):
        errors['decision_time_sum'] += 1
    if (not all(v52.finite(case.get(name)) and case[name] >= 0 for name in
                ('replay_seconds', 'decision_seconds', 'replay_overhead_seconds', 'serialization_seconds', 'last_limit_check_seconds'))
            or not v53.close(case.get('replay_seconds'), case.get('decision_seconds', 0) + case.get('replay_overhead_seconds', 0))
            or case.get('last_limit_check_seconds', 0) > case.get('replay_seconds', 0) + TOL):
        errors['case_time_partition'] += 1
    observed = dict(max_planner_action_values=work.get('action_value_evaluations', 0), max_policy_states=len(rows),
                    max_wall_seconds=case.get('last_limit_check_seconds'))
    triggered = [name for name in LIMITS if v52.finite(observed[name]) and observed[name] >= limits[name]]
    if ((complete and (triggered or case.get('stop_reason') is not None)) or
            (not complete and (not triggered or case.get('stop_reason') != triggered[0]))):
        errors['limit_boundary'] += 1
    if complete:
        reported = case.get('source_weighted_decision_work') or {}
        if set(reported) != set(weighted) or not all(v53.close(reported[name], number) for name, number in weighted.items()):
            errors['source_weighted_work'] += 1
        if not v53.close(case.get('source_weighted_decision_seconds'), math.fsum(weighted_seconds)):
            errors['source_weighted_time'] += 1
    elif case.get('source_weighted_decision_work') is not None or case.get('source_weighted_decision_seconds') is not None:
        errors['partial_weighted_interpretation'] += 1
    action_preserved = complete and len(checked) == len(source_rows) and root_changes == nonroot_changes == 0
    value_agreement = complete and all(row['value_agreement'] for row in checked)
    preserved = not errors and action_preserved and value_agreement
    return dict(passed=not errors, errors=dict(errors), status=case.get('status'), state_records=len(rows), source_state_records=len(source_rows),
        exact_action_matches=sum(row['action_preserved'] for row in checked), root_action_changes=root_changes,
        nonroot_action_changes=nonroot_changes, action_preserved=action_preserved, value_agreement=value_agreement,
        policy_value_preserved=preserved, source_policy_value=source_case['root_value'],
        candidate_policy_value=source_case['root_value'] if preserved else None,
        maximum_abs_source_Q_difference=max((row['maximum_abs_source_Q_difference'] for row in checked
                                            if row['maximum_abs_source_Q_difference'] is not None), default=None))


def ratio(numerator, denominator):
    return numerator / denominator if v52.finite(numerator) and v52.finite(denominator) and denominator > 0 else None


def costs(cases):
    work, weighted = Counter(), Counter()
    complete = bool(cases) and all(case['status'] == 'complete' for case in cases)
    for case in cases:
        work.update(case.get('decision_work', {}))
        if complete:
            weighted.update(case.get('source_weighted_decision_work') or {})
    return dict(case_records=len(cases), state_records=sum(case.get('state_records', 0) for case in cases),
        decision_work=dict(work), source_weighted_decision_work=dict(weighted) if complete else None,
        **{name: math.fsum(case[name] for case in cases if v52.finite(case.get(name))) for name in
            ('decision_seconds', 'replay_seconds', 'replay_overhead_seconds', 'serialization_seconds')},
        source_weighted_decision_seconds=math.fsum(case['source_weighted_decision_seconds'] for case in cases
            if v52.finite(case.get('source_weighted_decision_seconds'))) if complete else None)


def workload_ratios(cases, old_cases):
    fresh = costs(cases)
    old, old_weighted = Counter(), Counter()
    for case in old_cases:
        old.update(case['decision_work'])
        old_weighted.update(case['expected_decision_work'])
    fields = ('action_value_evaluations', 'kernel_builds', 'kernel_cache_hits', 'transition_outcomes', 'target_probability_evaluations')
    return dict(actual_work={name: ratio(fresh['decision_work'].get(name, 0), old.get(name, 0)) for name in fields},
        source_weighted_work={name: ratio(fresh['source_weighted_decision_work'].get(name, 0), old_weighted.get(name, 0)) for name in fields},
        decision_seconds=ratio(fresh['decision_seconds'], math.fsum(case['decision_seconds'] for case in old_cases)),
        source_weighted_decision_seconds=ratio(fresh['source_weighted_decision_seconds'],
                                              math.fsum(case['expected_decision_seconds'] for case in old_cases)))


def stratum_summary(panel, cases, old_cases, validations, valid):
    complete = valid and Counter(case['graph_id'] for case in cases) == Counter(panel['seeds'])
    complete = complete and all(case['status'] == 'complete' for case in cases)
    preserved = complete and all(row['policy_value_preserved'] for row in validations)
    fixed = workload_ratios(cases, old_cases) if complete else None
    return dict(nodes=panel['nodes'], stratum=panel['stratum'], p=panel['p'], expected_graphs=len(panel['seeds']),
        complete_fixed_query_workload=complete, policy_value_preserved=preserved,
        changed_root_actions=sum(row['root_action_changes'] for row in validations),
        changed_nonroot_actions=sum(row['nonroot_action_changes'] for row in validations),
        exact_action_matches=sum(row['exact_action_matches'] for row in validations),
        fixed_query_workload_ratios=fixed,
        preserved_policy_decision_cost_ratios=dict(work=fixed['source_weighted_work'],
            seconds=fixed['source_weighted_decision_seconds']) if preserved else None,
        new_costs=costs(cases), retained_full_decision_seconds=math.fsum(case['decision_seconds'] for case in old_cases),
        case_preservation=validations)


def summarize(manifest, cases, states, source_manifest, source_analysis, source_cases, source_states):
    started, errors = perf_counter(), Counter()
    ids = {seed for panel in PANELS for seed in panel['seeds']}
    if (manifest.get('schema') != 'acfqp.lmta_analytic_terminal.v56' or manifest.get('status') != 'complete'
            or manifest.get('protocol') != PROTOCOL or manifest.get('source_directory') != 'reports/lmta_tie_refinement_v55'
            or manifest.get('cold_decisions') is not True):
        errors['manifest_protocol'] += 1
    if (source_manifest.get('status') != 'complete' or source_analysis.get('integrity', {}).get('passed') is not True
            or source_analysis.get('fresh_complete_quality_evidence') is not True):
        errors['source_certificate_not_valid'] += 1
    old_graphs = [graph for graph in source_manifest.get('graphs', []) if graph.get('panel') == 'fresh' and graph.get('graph_id') in ids]
    if (manifest.get('graphs') != old_graphs or Counter(graph['graph_id'] for graph in old_graphs) != Counter(ids)):
        errors['retained_fresh_graph_binding'] += 1
    zero_fields = ('new_graphs', 'new_full_policy_evaluations', 'new_environment_samples', 'new_environment_calls', 'new_RL_updates', 'new_MCTS_calls')
    if any(manifest.get(name) != 0 for name in zero_fields):
        errors['unexpected_new_environment_or_evaluation_work'] += 1
    counts = Counter(case.get('graph_id') for case in cases)
    terminal = counts == Counter(ids) and all(case.get('status') in ('complete', 'resource_limit') for case in cases)
    successful = sum(case.get('status') == 'complete' for case in cases)
    limited = sum(case.get('status') == 'resource_limit' for case in cases)
    if (not terminal or manifest.get('completed_cases') != len(cases) or manifest.get('successful_cases') != successful
            or manifest.get('resource_limited_cases') != limited or manifest.get('total_state_records') != len(states)):
        errors['case_roster_and_manifest_counts'] += 1
    for name in ('source_read_seconds', 'whole_runner_seconds', 'runner_cpu_seconds', 'process_peak_rss_bytes'):
        if not v52.finite(manifest.get(name)) or manifest[name] < 0:
            errors['manifest_costs'] += 1
    previous = [case for case in source_cases if case.get('graph_id') in ids and case.get('method') == SOURCE_METHOD]
    if Counter(case['graph_id'] for case in previous) != Counter(ids) or any(case.get('status') != 'complete' for case in previous):
        errors['source_full_case_roster'] += 1
    old_cases = {case['graph_id']: case for case in previous}
    old_rows, grouped = defaultdict(list), defaultdict(list)
    for row in source_states:
        if row.get('graph_id') in ids and row.get('method') == SOURCE_METHOD:
            old_rows[row['graph_id']].append(row)
    for row in states:
        grouped[row['graph_id']].append(row)
    if grouped.keys() - ids or manifest.get('source_full_state_records') != sum(map(len, old_rows.values())):
        errors['source_and_replay_state_counts'] += 1
    if any(len(old_rows[graph]) != case['state_records'] for graph, case in old_cases.items()):
        errors['retained_full_state_coverage'] += 1
    graphs = {graph['graph_id']: graph for graph in old_graphs}
    validations = []
    for case in cases:
        graph = case.get('graph_id')
        if graph not in graphs or graph not in old_cases:
            errors['unbound_case'] += 1
            continue
        checked = verify_case(case, grouped[graph], old_cases[graph], old_rows[graph], graphs[graph]['edges'], graphs[graph]['nodes'])
        validations.append(dict(graph_id=graph, **checked))
        if not checked['passed']:
            errors['invalid_replay_certificate_or_cost'] += 1
    strata = [stratum_summary(panel, [case for case in cases if case['graph_id'] in panel['seeds']],
        [case for case in previous if case['graph_id'] in panel['seeds']],
        [row for row in validations if row['graph_id'] in panel['seeds']], not errors) for panel in PANELS]
    all_complete = terminal and successful == 64
    return dict(schema='acfqp.lmta_analytic_terminal_analysis.v56', protocol=PROTOCOL,
        integrity=dict(passed=not errors, errors=dict(errors), terminal_execution_complete=terminal,
            expected_case_records=64, case_records=len(cases), source_full_state_records=sum(map(len, old_rows.values())),
            state_records=len(states), case_validations=validations),
        action_preservation_all=all_complete and len(validations) == 64 and all(row['action_preserved'] for row in validations),
        value_agreement_all=all_complete and len(validations) == 64 and all(row['value_agreement'] for row in validations),
        policy_value_preserved_all=not errors and all_complete and all(row['policy_value_preserved'] for row in validations),
        strata=strata, replay_cases=cases,
        accounting=dict(new_replay=costs(cases),
            **{name: manifest.get(name) for name in ('source_read_seconds', 'whole_runner_seconds', 'runner_cpu_seconds',
                'process_peak_rss_bytes', 'data_bytes', *zero_fields)}, retained_V55=source_analysis.get('accounting'),
            analysis_wall_seconds_before_serialization=perf_counter() - started,
            scope='All complete and interrupted cold decisions remain charged. No new outer policy evaluation or environmental sample '
                  'is used. Old full-policy work is retained, not recharged. Source-weighted work describes the old occupancy distribution '
                  'and supports actual policy-decision cost interpretation only when every action and value certificate is preserved.'),
        inference_scope='Numerical validation and exact action preservation are separate. A strictly selected action can change under '
            'a Q perturbation smaller than 1e-10; that replay remains numerically valid but has no certified candidate policy value. '
            'Fixed-query workload ratios do not require action preservation. Incomplete strata have no ratios; any action change '
            'suppresses preserved-policy cost interpretation for the full stratum. Ratios compare summed work or time, not means of '
            'per-graph ratios. No new policy-quality experiment or adoption Gate is created.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_analytic_terminal_v56')
    parser.add_argument('--control-dir', type=Path, default=ROOT / 'reports/lmta_tie_refinement_v55')
    args = parser.parse_args()
    started = perf_counter()

    def document(directory, name):
        return json.loads((directory / name).read_text())

    def rows(directory, name, source=False):
        result = []
        with (directory / name).open() as handle:
            for line in handle:
                row = json.loads(line)
                if not source or (row.get('method') == SOURCE_METHOD and any(row.get('graph_id') in panel['seeds'] for panel in PANELS)):
                    result.append(row)
        return result

    report = summarize(document(args.output_dir, 'manifest.json'), rows(args.output_dir, 'cases.jsonl'), rows(args.output_dir, 'states.jsonl'),
        document(args.control_dir, 'manifest.json'), document(args.control_dir, 'analysis.json'),
        rows(args.control_dir, 'cases.jsonl', True), rows(args.control_dir, 'states.jsonl', True))
    elapsed = perf_counter() - started
    report['accounting']['analysis_wall_seconds_including_reads'] = elapsed
    report['accounting']['new_runner_plus_analysis_seconds_before_serialization'] = report['accounting']['whole_runner_seconds'] + elapsed
    (args.output_dir / 'analysis.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(integrity_passed=report['integrity']['passed'], action_preservation_all=report['action_preservation_all'],
                         policy_value_preserved_all=report['policy_value_preserved_all'], strata=report['strata']), indent=2))


if __name__ == '__main__':
    main()
