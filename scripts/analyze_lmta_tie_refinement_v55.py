"""Independent exact-tie refinement checks, fresh-panel results and paid work."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import importlib.util
import itertools
import json
import math
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('scale_certificate_v54', Path(__file__).with_name('analyze_lmta_scale_v54.py'))
v54 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v54)
v53, v52, TOL = v54.v53, v54.v52, 1e-10
CANDIDATE = 'LOOKAHEAD_2_TIE3'
METHODS = ['LOOKAHEAD_1', 'LOOKAHEAD_2', CANDIDATE, 'LOOKAHEAD_FULL']
LIMITS = v54.LIMITS
PANELS = [dict(nodes=7, stratum='sparse', expected_degree=1.5, p=.25, seeds=list(range(550000, 550016))),
          dict(nodes=7, stratum='dense', expected_degree=4.5, p=.75, seeds=list(range(550100, 550116))),
          dict(nodes=9, stratum='sparse', expected_degree=1.5, p=.1875, seeds=list(range(550200, 550216))),
          dict(nodes=9, stratum='dense', expected_degree=4.5, p=.5625, seeds=list(range(550300, 550316)))]
REGRESSION = dict(graph_id=540009, source_directory='reports/lmta_scale_v54', methods=[CANDIDATE], role='known_regression_only')
PROTOCOL = dict(budget=2, horizon=3, methods=METHODS, panels=PANELS, limits=LIMITS, regression=REGRESSION)


def verify_stage_work(case, rows):
    errors = Counter()
    for stage in ('prefix_work', 'refinement_work'):
        actual, expected = Counter(), Counter()
        for row in rows:
            actual.update(row.get(stage, {}))
            if case['status'] == 'complete' and v52.finite(row.get('reach_probability')):
                expected.update({name: count * row['reach_probability'] for name, count in row.get(stage, {}).items()})
        if Counter(case.get(stage, {})) != actual:
            errors[stage + '_sum'] += 1
        reported = case.get('expected_' + stage)
        if case['status'] == 'complete':
            if not isinstance(reported, dict) or set(reported) != set(expected) or not all(
                    v53.close(reported[name], number) for name, number in expected.items()):
                errors['expected_' + stage + '_sum'] += 1
        elif reported is not None:
            errors['partial_expected_' + stage] += 1
    return errors


def refinement_values(statuses, budget, days, roots, edges, nodes):
    """Only the tied root subset is refined; future nodes use all legal actions."""
    _, outcomes = v52.independent_model(edges, nodes)

    @lru_cache(maxsize=None)
    def value(state, b, h, d):
        if h == 0 or d == 0:
            return 0.
        return max(q(state, b, h, d, action) for action in v53.actions(state, b, h))

    def q(state, b, h, d, action):
        return math.fsum(p * (reward + value(after, b - len(action), h - 1, d - 1))
                         for p, after, reward in outcomes(state, action))

    return {action: q(tuple(statuses), budget, days, 3, action) for action in roots}


def verify_candidate_decision(row, edges, nodes):
    errors = Counter()

    def check(name, passed):
        if not passed:
            errors[name] += 1

    statuses, budget, days = v52.state_key(row)
    choices = v53.actions(statuses, budget, days)
    expected = v53.independent_plan(statuses, budget, days, min(2, days), edges, nodes)
    prefix_selected, selected = tuple(row['prefix_selected']), tuple(row['selected'])
    reported = row.get('root_action_values', [])
    refined = row.get('refinement_action_values', [])
    check('selected_legal_allocation', prefix_selected in choices and selected in choices)
    tied, trigger = [], False
    if len(choices) == 1:
        check('forced_prefix', row.get('planned_value') is None and reported == []
              and prefix_selected == selected == choices[0])
    else:
        check('prefix_action_roster', Counter(tuple(action['selected']) for action in reported) == Counter(choices))
        values = {tuple(action['selected']): action['value'] for action in expected['root_action_values']}
        numeric = all(tuple(action['selected']) in values and v52.finite(action.get('value')) for action in reported)
        check('prefix_action_values', numeric and all(abs(action['value'] - values[tuple(action['selected'])]) <= TOL
                                                     for action in reported))
        if numeric and reported:
            recorded_values = {tuple(action['selected']): action['value'] for action in reported}
            maximum = max(recorded_values.values())
            tied = sorted(action for action, number in recorded_values.items() if number == maximum)
            check('prefix_strict_choice', prefix_selected == tied[0] and row.get('planned_value') == maximum)
            trigger = days > 2 and len(tied) > 1
    if trigger:
        check('refinement_root_set', Counter(tuple(action['selected']) for action in refined) == Counter(tied))
        expected_refinement = refinement_values(statuses, budget, days, tied, edges, nodes)
        numeric = all(tuple(action['selected']) in expected_refinement and v52.finite(action.get('value')) for action in refined)
        check('refinement_values', numeric and all(abs(action['value'] - expected_refinement[tuple(action['selected'])]) <= TOL
                                                   for action in refined))
        if numeric and refined:
            recorded_refinement = {tuple(action['selected']): action['value'] for action in refined}
            maximum = max(recorded_refinement.values())
            best = min(action for action, number in recorded_refinement.items() if number == maximum)
            check('refinement_strict_choice', selected == best)
    else:
        check('no_untriggered_refinement', refined == [] and selected == prefix_selected)
    prefix_work, refinement_work = row.get('prefix_work', {}), row.get('refinement_work', {})
    special = ('planner_calls', 'refinement_calls', 'refined_root_actions')
    check('stage_work', all(isinstance(number, int) and number >= 0 for stage in (prefix_work, refinement_work)
                           for number in stage.values()) and not any(name in stage for stage in (prefix_work, refinement_work) for name in special))
    if not trigger:
        check('no_untriggered_work', all(number == 0 for number in refinement_work.values()))
    else:
        check('triggered_refinement_work', refinement_work.get('action_value_evaluations', 0) >= len(tied)
              and refinement_work.get('kernel_builds', 0) >= len(tied) and refinement_work.get('dp_states', 0) > 0
              and refinement_work.get('bellman_expectation_terms', 0) > 0 and refinement_work.get('transition_outcomes', 0) > 0)
    expected_work = Counter(prefix_work)
    expected_work.update(refinement_work)
    expected_work.update(planner_calls=1, refinement_calls=int(trigger), refined_root_actions=len(tied) if trigger else 0)
    check('two_stage_work_sum', Counter(row.get('decision_work', {})) == expected_work)
    check('forced_work', expected_work.get('forced_choice') == int(len(choices) == 1))
    return dict(passed=not errors, errors=dict(errors), triggered=trigger, prefix_tie_count=len(tied),
                forced=len(choices) == 1, refinement_root_actions=len(tied) if trigger else 0)


def verify_candidate_case(case, rows, edges, nodes, limits=LIMITS):
    """Verify a fresh policy certificate, or account for its explicit interruption."""
    errors = Counter()

    def check(name, passed):
        if not passed:
            errors[name] += 1

    complete = case.get('status') == 'complete'
    check('terminal_status', case.get('status') in ('complete', 'resource_limit'))
    check('new_value_source', case.get('value_source') == 'V55_full_policy_evaluation'
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
        decision = verify_candidate_decision(row, edges, nodes)
        errors.update(decision['errors'])
        forced += decision['forced']
        planned += not decision['forced']
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
    errors.update(verify_stage_work(case, rows))
    return dict(passed=not errors, errors=dict(errors), status=case.get('status'), state_records=len(rows),
        quality_verified=complete and not errors, planned_roots=planned, forced_roots=forced,
        full_policy_equations=equations, maximum_bellman_residual=maximum_residual if complete else None)


def ratio(numerator, denominator):
    return numerator / denominator if v52.finite(numerator) and v52.finite(denominator) and denominator > 0 else None


def candidate_costs(cases):
    result = v54.case_accounting(cases)
    all_complete = bool(cases) and all(case['status'] == 'complete' for case in cases)
    for stage in ('prefix_work', 'refinement_work'):
        actual, expected = Counter(), Counter()
        for case in cases:
            actual.update(case.get(stage, {}))
            if all_complete:
                expected.update(case.get('expected_' + stage, {}))
        result[stage] = dict(actual)
        result['expected_' + stage] = dict(expected) if all_complete else None
    triggered = sum(case.get('decision_work', {}).get('refinement_calls', 0) for case in cases)
    expected = result.get('expected_decision_work') or {}
    result['triggering_roots'] = triggered
    result['root_trigger_rate'] = ratio(triggered, len(cases))
    result['expected_refinement_calls_per_trajectory'] = ratio(expected.get('refinement_calls'), len(cases))
    result['reach_weighted_trigger_fraction_of_decisions'] = ratio(expected.get('refinement_calls'), expected.get('planner_calls'))
    return result


def graph_comparison(cases):
    lookup = {case['method']: case for case in cases}
    one, two, candidate, full = (lookup[method]['root_value'] for method in METHODS)
    headroom = full - one
    quality = dict(values={method: lookup[method]['root_value'] for method in METHODS},
        candidate_minus_two=candidate - two, candidate_minus_myopic=candidate - one, full_minus_candidate=full - candidate,
        full_minus_myopic=headroom, headroom_fraction=(candidate - one) / headroom if headroom > TOL else None,
        new_degradation=two >= one - TOL and candidate < one - TOL,
        repaired_degradation=two < one - TOL and candidate >= one - TOL,
        root_action_changed_vs_two=lookup[CANDIDATE]['root_selected'] != lookup['LOOKAHEAD_2']['root_selected'])
    ratios = {}
    for control in ('LOOKAHEAD_1', 'LOOKAHEAD_2', 'LOOKAHEAD_FULL'):
        ratios[control] = dict(
            expected_action_values=ratio(lookup[CANDIDATE]['expected_decision_work'].get('action_value_evaluations', 0),
                lookup[control]['expected_decision_work'].get('action_value_evaluations', 0)),
            expected_decision_seconds=ratio(lookup[CANDIDATE]['expected_decision_seconds'], lookup[control]['expected_decision_seconds']))
    return dict(**quality, candidate_over_control_cost_ratios=ratios)


def stratum_summary(panel, cases, valid):
    expected = Counter(itertools.product(panel['seeds'], METHODS))
    complete = valid and Counter((case['graph_id'], case['method']) for case in cases) == expected
    complete = complete and all(case['status'] == 'complete' for case in cases)
    result = dict(nodes=panel['nodes'], stratum=panel['stratum'], p=panel['p'], quality_complete=complete,
        expected_graphs=len(panel['seeds']), terminal_cases=len(cases),
        resource_limited_cases=sum(case['status'] == 'resource_limit' for case in cases),
        costs_by_method={method: (candidate_costs if method == CANDIDATE else v54.case_accounting)(
            [case for case in cases if case['method'] == method]) for method in METHODS},
        values=None, contrasts=None, per_graph=None, sum_gain_over_sum_headroom=None, new_degradations=None,
        repaired_degradations=None, root_actions_changed_vs_two=None,
        candidate_over_control_cost_ratios=None, ratio_of_summed_expected_action_values=None)
    if complete:
        rows = [dict(graph_id=graph, **graph_comparison([case for case in cases if case['graph_id'] == graph])) for graph in panel['seeds']]
        headroom = math.fsum(row['full_minus_myopic'] for row in rows)
        result.update(per_graph=rows, values={method: v53.descriptive([row['values'][method] for row in rows]) for method in METHODS},
            contrasts={name: v53.descriptive([row[name] for row in rows]) for name in
                ('candidate_minus_two', 'candidate_minus_myopic', 'full_minus_candidate', 'full_minus_myopic', 'headroom_fraction')},
            sum_gain_over_sum_headroom=math.fsum(row['candidate_minus_myopic'] for row in rows) / headroom if headroom > TOL else None,
            new_degradations=sum(row['new_degradation'] for row in rows), repaired_degradations=sum(row['repaired_degradation'] for row in rows),
            root_actions_changed_vs_two=sum(row['root_action_changed_vs_two'] for row in rows),
            ratio_of_summed_expected_action_values={control: ratio(
                result['costs_by_method'][CANDIDATE]['expected_decision_work'].get('action_value_evaluations', 0),
                result['costs_by_method'][control]['expected_decision_work'].get('action_value_evaluations', 0))
                for control in ('LOOKAHEAD_1', 'LOOKAHEAD_2', 'LOOKAHEAD_FULL')},
            candidate_over_control_cost_ratios={control: {name: v53.descriptive([
                row['candidate_over_control_cost_ratios'][control][name] for row in rows])
                for name in ('expected_action_values', 'expected_decision_seconds')}
                for control in ('LOOKAHEAD_1', 'LOOKAHEAD_2', 'LOOKAHEAD_FULL')})
    return result


def summarize(manifest, cases, states, source_analysis, source_cases):
    started, errors = perf_counter(), Counter()
    bindings = {seed: dict(panel, panel='fresh') for panel in PANELS for seed in panel['seeds']}
    bindings[540009] = dict(nodes=7, stratum='sparse', p=.25, expected_degree=1.5, panel='regression')
    expected = Counter((graph, 3, method) for graph in bindings for method in (METHODS if graph != 540009 else [CANDIDATE]))
    if (manifest.get('schema') != 'acfqp.lmta_tie_refinement.v55' or manifest.get('status') != 'complete'
            or manifest.get('protocol') != PROTOCOL or manifest.get('source_directory') != 'reports/lmta_scale_v54'
            or manifest.get('cold_decisions') is not True):
        errors['manifest_protocol'] += 1
    if source_analysis.get('integrity', {}).get('passed') is not True or source_analysis.get('complete_quality_evidence') is not True:
        errors['source_V54_not_valid'] += 1
    controls = [case for case in source_cases if case.get('graph_id') == 540009]
    if (Counter(case['method'] for case in controls) != Counter(['LOOKAHEAD_1', 'LOOKAHEAD_2', 'LOOKAHEAD_FULL'])
            or manifest.get('regression_controls') != controls):
        errors['regression_control_binding'] += 1
    if any(manifest.get(name) != 0 for name in ('new_environment_samples', 'new_environment_calls', 'new_RL_updates', 'new_MCTS_calls')):
        errors['environment_or_training_work'] += 1
    counts = Counter(v52.identity(case) for case in cases)
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
        if panel is None or any(graph.get(name) != panel[name] for name in ('nodes', 'stratum', 'p', 'expected_degree', 'panel')):
            errors['graph_binding'] += 1
            continue
        edges, nodes = graph['edges'], graph['nodes']
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
        grouped[v52.identity(row)].append(row)
    if grouped.keys() - expected.keys():
        errors['unbound_state_case'] += 1
    validations = []
    for case in cases:
        key = v52.identity(case)
        panel = bindings.get(case.get('graph_id'))
        if (key not in expected or case['graph_id'] not in valid_graphs or case.get('budget') != 2
                or panel is None or any(case.get(name) != panel[name] for name in ('nodes', 'stratum', 'p'))):
            errors['case_binding'] += 1
            continue
        graph = valid_graphs[case['graph_id']]
        checker = verify_candidate_case if case['method'] == CANDIDATE else v54.verify_case
        checked = checker(case, grouped[key], graph['edges'], graph['nodes'])
        validations.append(dict(graph_id=key[0], horizon=key[1], method=key[2], **checked))
        if not checked['passed']:
            errors['invalid_case_certificate_or_cost'] += 1
    for graph in bindings:
        rows = [case for case in cases if case['graph_id'] == graph] + (controls if graph == 540009 else [])
        lookup = {case['method']: case for case in rows}
        if set(lookup) == set(METHODS) and all(row['status'] == 'complete' and v52.finite(row['root_value']) for row in rows):
            if lookup[CANDIDATE]['root_value'] < lookup['LOOKAHEAD_2']['root_value'] - TOL:
                errors['T3_candidate_dominates_two_consistency'] += 1
            if max(lookup[method]['root_value'] for method in METHODS[:-1]) > lookup['LOOKAHEAD_FULL']['root_value'] + TOL:
                errors['full_horizon_upper_bound'] += 1
    fresh = [case for case in cases if case['graph_id'] in bindings and bindings[case['graph_id']]['panel'] == 'fresh']
    regression = [case for case in cases if case['graph_id'] == 540009]
    strata = [stratum_summary(panel, [case for case in fresh if case['nodes'] == panel['nodes']
                and case['stratum'] == panel['stratum']], not errors) for panel in PANELS]
    regression_complete = not errors and len(regression) == 1 and all(case['status'] == 'complete' for case in regression + controls)
    return dict(schema='acfqp.lmta_tie_refinement_analysis.v55', protocol=PROTOCOL,
        integrity=dict(passed=not errors, errors=dict(errors), terminal_execution_complete=terminal,
            expected_case_records=257, case_records=len(cases), state_records=len(states), successful_cases=successful,
            resource_limited_cases=limited, case_validations=validations),
        fresh_complete_quality_evidence=not errors and len(fresh) == 256 and all(case['status'] == 'complete' for case in fresh),
        strata=strata, root_values=cases,
        regression=dict(graph_id=540009, role='known_regression_only', quality_complete=regression_complete,
            comparison=graph_comparison(regression + controls) if regression_complete else None,
            new_candidate_costs=candidate_costs(regression), retained_control_cases=controls),
        accounting=dict(new_cases=v54.case_accounting(cases), fresh_cases=v54.case_accounting(fresh),
            regression_new_candidate=candidate_costs(regression),
            **{name: manifest.get(name) for name in ('source_read_seconds', 'graph_generation_seconds', 'whole_runner_seconds',
                'runner_cpu_seconds', 'process_peak_rss_bytes', 'data_bytes', 'new_environment_samples', 'new_environment_calls',
                'new_RL_updates', 'new_MCTS_calls')}, retained_V54=source_analysis.get('accounting'),
            analysis_wall_seconds_before_serialization=perf_counter() - started,
            scope='The fresh and regression ledgers partition all new work and are not added a second time. '
                  'Total candidate work includes both prefix and refinement; reach-weighted work is a separate trajectory expectation. '
                  'All interrupted work remains charged. V54 regression controls are historical, not new evaluations.'),
        inference_scope='Only exactly equal retained prefix Q values trigger refinement; independent numerical checks use absolute 1e-10. '
            'Fresh strata include all 16 graphs or have null quality summaries. The known regression is excluded from every fresh mean '
            'and trigger rate. Under T3, candidate>=two is an implementation consistency condition, not evidence of candidate>=myopic. '
            'Negative gains versus myopic remain reported; zero-headroom ratios are null. No confidence interval or adoption Gate is created.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_tie_refinement_v55')
    parser.add_argument('--control-dir', type=Path, default=ROOT / 'reports/lmta_scale_v54')
    args = parser.parse_args()
    started = perf_counter()

    def read(directory, name):
        text = (directory / name).read_text()
        return [json.loads(line) for line in text.splitlines()] if name.endswith('.jsonl') else json.loads(text)

    report = summarize(read(args.output_dir, 'manifest.json'), read(args.output_dir, 'cases.jsonl'), read(args.output_dir, 'states.jsonl'),
                       read(args.control_dir, 'analysis.json'), read(args.control_dir, 'cases.jsonl'))
    report['accounting']['analysis_wall_seconds_including_reads'] = perf_counter() - started
    (args.output_dir / 'analysis.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(integrity_passed=report['integrity']['passed'], strata=report['strata'], regression=report['regression']), indent=2))


if __name__ == '__main__':
    main()
