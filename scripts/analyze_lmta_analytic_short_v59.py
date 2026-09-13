"""Short-lookahead analytic replay: fixed-query accounting and policy preservation."""
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
METHODS = ['LOOKAHEAD_1_ANALYTIC', 'LOOKAHEAD_2_ANALYTIC']
SOURCE_METHODS = ['LOOKAHEAD_1', 'LOOKAHEAD_2']
SOURCES = dict(zip(METHODS, SOURCE_METHODS))
FULL = 'LOOKAHEAD_FULL_ANALYTIC'
LIMITS = dict(max_planner_action_values=2000000, max_policy_states=100000, max_wall_seconds=60.)
PANELS = [dict(nodes=9, stratum='sparse', expected_degree=1.5, p=1.5/8, seeds=list(range(580000, 580016))),
          dict(nodes=9, stratum='dense', expected_degree=4.5, p=4.5/8, seeds=list(range(580100, 580116))),
          dict(nodes=11, stratum='sparse', expected_degree=1.5, p=1.5/10, seeds=list(range(580200, 580216))),
          dict(nodes=11, stratum='dense', expected_degree=4.5, p=4.5/10, seeds=list(range(580300, 580316)))]
PROTOCOL = dict(budget=2, horizon=3, methods=METHODS, source_methods=SOURCE_METHODS, panels=PANELS, limits=LIMITS)


def identity(row):
    return row.get('graph_id'), row.get('method')


def verify_row(row, source, edges, nodes):
    errors = Counter()

    def check(name, passed):
        if not passed:
            errors[name] += 1

    check('source_state_binding', row.get('method') in METHODS and row.get('source_method') == SOURCES.get(row.get('method'))
          and source.get('method') == row.get('source_method')
          and all(row.get(name) == source.get(name) for name in ('graph_id', 'nodes', 'stratum', 'p', 'budget', 'horizon',
                                                              'statuses', 'remaining_budget', 'remaining_days')))
    statuses, budget, days = v52.state_key(source)
    choices = v53.actions(statuses, budget, days)
    selected = tuple(row['selected'])
    check('selected_legal_allocation', selected in choices)
    depth = min(int(source['method'][-1]), days)
    expected = v53.independent_plan(statuses, budget, days, depth, edges, nodes)
    independent_difference = source_difference = source_planned_value_difference = None
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
            source_planned_value_difference = abs(maximum - source['planned_value'])
            value_agreement = max(independent_difference, source_difference, source_planned_value_difference) <= TOL
        else:
            value_agreement = False
        check('Q_and_source_short_planned_value_tolerance', value_agreement)
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
        if depth == 1:
            check('terminal_analytic_work', counts.get('analytic_expectation_calls') == len(choices)
                  and counts.get('analytic_probability_terms') == sum(len(statuses) - len(action) - sum(s != 0 for s in statuses) for action in choices)
                  and all(counts.get(name, 0) == 0 for name in ('kernel_builds', 'transition_outcomes', 'bellman_expectation_terms')))
    check('decision_seconds', v52.finite(row.get('decision_seconds')) and row['decision_seconds'] >= 0)
    return dict(passed=not errors, errors=dict(errors), action_preserved=row['selected'] == source['selected'],
        value_agreement=value_agreement, maximum_abs_independent_Q_difference=independent_difference,
        maximum_abs_source_Q_difference=source_difference, source_planned_value_difference=source_planned_value_difference)


def verify_case(case, rows, source_case, source_rows, edges, nodes, limits=LIMITS):
    errors = Counter()
    complete = case.get('status') == 'complete'
    if case.get('status') not in ('complete', 'resource_limit'):
        errors['terminal_status'] += 1
    if (case.get('method') not in METHODS or case.get('source_method') != SOURCES.get(case.get('method'))
            or source_case.get('method') != case.get('source_method') or any(case.get(name) != source_case.get(name)
            for name in ('graph_id', 'nodes', 'stratum', 'p', 'budget', 'horizon'))):
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
    if (not all(v52.finite(case.get(name)) and case[name] >= 0 for name in
                ('prepare_gc_seconds', 'cleanup_seconds', 'decision_total_seconds', 'block_seconds'))
            or not v53.close(case.get('decision_total_seconds'), case.get('decision_seconds', 0)+case.get('cleanup_seconds', 0))
            or not v53.close(case.get('block_seconds'), case.get('replay_seconds', 0)+case.get('cleanup_seconds', 0))):
        errors['gc_cost_views'] += 1
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
        independent_query_checks=len(checked),
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
            ('decision_seconds', 'replay_seconds', 'replay_overhead_seconds', 'serialization_seconds',
             'prepare_gc_seconds', 'cleanup_seconds', 'decision_total_seconds', 'block_seconds')},
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




def method_summary(panel, method, cases, old_cases, validations, valid):
    complete = (valid and Counter(case['graph_id'] for case in cases) == Counter(panel['seeds'])
                and len(validations) == len(panel['seeds']) and all(case['status'] == 'complete' for case in cases))
    preserved = complete and all(row['policy_value_preserved'] for row in validations)
    fixed = workload_ratios(cases, old_cases) if complete else None
    return dict(method=method, source_method=SOURCES[method], complete_fixed_query_workload=complete,
        policy_value_preserved=preserved, root_action_changes=sum(row['root_action_changes'] for row in validations),
        preserved_graphs=sum(row['policy_value_preserved'] for row in validations),
        maximum_abs_source_Q_difference=max((row['maximum_abs_source_Q_difference'] for row in validations
                                            if row['maximum_abs_source_Q_difference'] is not None), default=None),
        nonroot_action_changes=sum(row['nonroot_action_changes'] for row in validations),
        exact_action_matches=sum(row['exact_action_matches'] for row in validations),
        fixed_query_workload_ratios=fixed,
        preserved_policy_decision_cost_ratios=dict(work=fixed['source_weighted_work'],
            seconds_descriptive=fixed['source_weighted_decision_seconds']) if preserved else None,
        source_policy_values=v53.descriptive([row['root_value'] for row in old_cases]),
        candidate_policy_values=v53.descriptive([row['candidate_policy_value'] for row in validations]) if preserved else None,
        new_costs=costs(cases))


def three_depth_summary(panel, cases, full_cases, validations):
    """Called only when both short policies and the source full policy are certified."""
    lookup = {identity(row): row for row in validations}
    full = {row['graph_id']: row for row in full_cases}
    points = []
    for graph in panel['seeds']:
        one, two = (lookup[graph, method]['candidate_policy_value'] for method in METHODS)
        exact = full[graph]['root_value']
        points.append(dict(graph_id=graph, values=dict(zip(METHODS+[FULL], (one, two, exact))),
                           two_minus_one=two-one, full_minus_two=exact-two, full_minus_one=exact-one))
    work, seconds = {}, {}
    for method in METHODS:
        account = costs([row for row in cases if row['method'] == method])
        work[method] = account['source_weighted_decision_work']
        seconds[method] = account['source_weighted_decision_seconds']
    retained_work = Counter()
    for row in full_cases:
        retained_work.update(row['expected_decision_work'])
    work[FULL] = dict(retained_work)
    seconds[FULL] = math.fsum(row['expected_decision_seconds'] for row in full_cases)
    ratios = {}
    for numerator, denominator in ((METHODS[1], METHODS[0]), (FULL, METHODS[1]), (FULL, METHODS[0])):
        ratios[numerator+'_over_'+denominator] = {name: ratio(work[numerator].get(name, 0), number)
                                                 for name, number in work[denominator].items()}
    return dict(values={method: v53.descriptive([row['values'][method] for row in points]) for method in METHODS+[FULL]},
        contrasts={name: v53.descriptive([row[name] for row in points]) for name in ('two_minus_one', 'full_minus_two', 'full_minus_one')},
        per_graph=points, expected_work_sums=work, ratios_of_expected_work_sums=ratios,
        expected_planning_seconds_descriptive=seconds,
        provenance={METHODS[0]: 'V59 replay with action-preservation certificate',
                    METHODS[1]: 'V59 replay with action-preservation certificate', FULL: 'V58 retained; no rerun'},
        scope='Work uses each preserved policy occupancy. Wall times are from different runs and are not paired speedup evidence.')


EXPECTED_SOURCE_STATES = 188499


def summarize(manifest, cases, states, source_manifest, source_analysis, source_cases, source_states):
    started, errors = perf_counter(), Counter()
    bindings = {seed: panel for panel in PANELS for seed in panel['seeds']}
    ids = set(bindings)
    expected = Counter(itertools.product(ids, METHODS))
    if (manifest.get('schema') != 'acfqp.lmta_analytic_short.v59' or manifest.get('status') != 'complete'
            or manifest.get('protocol') != PROTOCOL or manifest.get('source_directory') != 'reports/lmta_analytic_scale_v58'
            or manifest.get('cold_decisions') is not True or manifest.get('runtime', {}).get('gc_enabled') is not True):
        errors['manifest_protocol'] += 1
    if (source_manifest.get('schema') != 'acfqp.lmta_analytic_scale.v58' or source_manifest.get('status') != 'complete'
            or source_analysis.get('integrity', {}).get('passed') is not True
            or source_analysis.get('complete_quality_evidence') is not True):
        errors['source_certificate_not_valid'] += 1
    old_graphs = source_manifest.get('graphs', [])
    if (manifest.get('graphs') != old_graphs or Counter(graph['graph_id'] for graph in old_graphs) != Counter(ids)
            or any(graph['graph_id'] not in bindings or any(graph.get(key) != bindings[graph['graph_id']][key]
                   for key in ('nodes', 'stratum', 'p', 'expected_degree')) for graph in old_graphs)):
        errors['retained_graph_binding'] += 1
    zero_fields = ('new_graphs', 'new_full_policy_evaluations', 'new_environment_samples', 'new_environment_calls', 'new_RL_updates', 'new_MCTS_calls')
    if any(manifest.get(name) != 0 for name in zero_fields):
        errors['unexpected_new_environment_or_evaluation_work'] += 1
    counts = Counter(identity(case) for case in cases)
    terminal = counts == expected and all(case.get('status') in ('complete', 'resource_limit') for case in cases)
    successful = sum(case.get('status') == 'complete' for case in cases)
    limited = sum(case.get('status') == 'resource_limit' for case in cases)
    if (not terminal or manifest.get('completed_cases') != len(cases) or manifest.get('successful_cases') != successful
            or manifest.get('resource_limited_cases') != limited or manifest.get('total_state_records') != len(states)):
        errors['case_roster_and_manifest_counts'] += 1
    cost_fields = ('source_read_seconds', 'graph_reconstruction_seconds', 'data_output_seconds', 'whole_runner_seconds',
                   'runner_cpu_seconds', 'process_peak_rss_bytes')
    if any(not v52.finite(manifest.get(name)) or manifest[name] < 0 for name in cost_fields):
        errors['manifest_costs'] += 1
    previous = [case for case in source_cases if case.get('graph_id') in ids and case.get('method') in SOURCE_METHODS+[FULL]]
    if (Counter(identity(case) for case in previous) != Counter(itertools.product(ids, SOURCE_METHODS+[FULL]))
            or any(case.get('status') != 'complete' or case.get('horizon') != 3 or case.get('budget') != 2 for case in previous)):
        errors['source_three_depth_case_roster'] += 1
    old_cases = {identity(case): case for case in previous}
    old_rows, grouped = defaultdict(list), defaultdict(list)
    for row in source_states:
        if row.get('graph_id') in ids and row.get('method') in SOURCE_METHODS:
            old_rows[identity(row)].append(row)
    for row in states:
        grouped[identity(row)].append(row)
    source_count = sum(map(len, old_rows.values()))
    if grouped.keys() - expected.keys() or manifest.get('source_state_records') != source_count or source_count != EXPECTED_SOURCE_STATES:
        errors['source_and_replay_state_counts'] += 1
    if any(len(old_rows[key]) != case['state_records'] for key, case in old_cases.items() if key[1] in SOURCE_METHODS):
        errors['retained_short_state_coverage'] += 1
    structural_valid = not errors
    graphs = {graph['graph_id']: graph for graph in old_graphs}
    validations = []
    for case in cases:
        graph, method = identity(case)
        old_key = (graph, SOURCES.get(method))
        if graph not in graphs or old_key not in old_cases:
            errors['unbound_case'] += 1
            continue
        checked = verify_case(case, grouped[graph, method], old_cases[old_key], old_rows[old_key],
                              graphs[graph]['edges'], graphs[graph]['nodes'])
        validations.append(dict(graph_id=graph, method=method, **checked))
        if not checked['passed']:
            errors['invalid_replay_certificate_or_cost'] += 1
    strata = []
    for panel in PANELS:
        selected = [case for case in cases if case['graph_id'] in panel['seeds']]
        checks = [row for row in validations if row['graph_id'] in panel['seeds']]
        methods = {}
        for method in METHODS:
            method_checks = [row for row in checks if row['method'] == method]
            methods[method] = method_summary(panel, method, [row for row in selected if row['method'] == method],
                [row for row in previous if row['graph_id'] in panel['seeds'] and row['method'] == SOURCES[method]],
                method_checks, structural_valid and all(row['passed'] for row in method_checks))
        unified = all(row['policy_value_preserved'] for row in methods.values())
        strata.append(dict(nodes=panel['nodes'], stratum=panel['stratum'], p=panel['p'], expected_graphs=len(panel['seeds']),
            methods=methods, unified_three_depth_policy_and_work=three_depth_summary(panel, selected,
                [row for row in previous if row['graph_id'] in panel['seeds'] and row['method'] == FULL], checks) if unified else None))
    all_complete = terminal and successful == 128 and len(validations) == 128
    return dict(schema='acfqp.lmta_analytic_short_analysis.v59', protocol=PROTOCOL,
        integrity=dict(passed=not errors, errors=dict(errors), terminal_execution_complete=terminal,
            expected_case_records=128, case_records=len(cases), source_state_records=source_count,
            state_records=len(states), case_validations=validations),
        action_preservation_all=all_complete and all(row['action_preserved'] for row in validations),
        value_agreement_all=all_complete and all(row['value_agreement'] for row in validations),
        policy_value_preserved_all=not errors and all_complete and all(row['policy_value_preserved'] for row in validations),
        strata=strata, replay_cases=cases,
        accounting=dict(new_replay=costs(cases), **{name: manifest.get(name) for name in (*cost_fields, 'data_bytes', *zero_fields)},
            retained_V58=source_analysis.get('accounting'), analysis_wall_seconds_before_serialization=perf_counter()-started,
            analysis_independent_query_checks=sum(row.get('independent_query_checks', 0) for row in validations),
            analysis_new_full_policy_evaluations=0,
            scope='All completed or interrupted replay decisions, GC and serialization remain charged. '
                  'Cost views overlap; data_output_seconds contains state serialization_seconds. '
                  'V58 full-policy evaluations and FULL planning remain historical, not rerun or refunded.'),
        inference_scope='Short planned Q is compared with short planned Q, not with full-policy continuation value. '
            'Numerically valid exact-action changes suppress policy-value reuse. Complete fixed-query work remains descriptive. '
            'Source-weighted work has a policy-cost interpretation only if all actions in the method/stratum are preserved. '
            'The unified three-depth view requires both short policies preserved; its FULL work is retained V58 work. '
            'Different-run times are not paired acceleration evidence. No policy reevaluation, CI, or adoption Gate is added.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_analytic_short_v59')
    parser.add_argument('--control-dir', type=Path, default=ROOT / 'reports/lmta_analytic_scale_v58')
    args = parser.parse_args()
    started = perf_counter()
    def document(directory, name):
        return json.loads((directory/name).read_text())
    def rows(directory, name, short_only=False):
        result = []
        with (directory/name).open() as handle:
            for line in handle:
                row = json.loads(line)
                if not short_only or row.get('method') in SOURCE_METHODS:
                    result.append(row)
        return result
    result = summarize(document(args.output_dir, 'manifest.json'), rows(args.output_dir, 'cases.jsonl'),
        rows(args.output_dir, 'states.jsonl'), document(args.control_dir, 'manifest.json'),
        document(args.control_dir, 'analysis.json'), rows(args.control_dir, 'cases.jsonl'),
        rows(args.control_dir, 'states.jsonl', True))
    result['accounting']['analysis_wall_seconds_including_reads'] = perf_counter()-started
    (args.output_dir/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(integrity=result['integrity']['passed'],
                          policy_value_preserved_all=result['policy_value_preserved_all'])))


if __name__ == '__main__':
    main()
