"""Fresh N9/N11 policy certificates and analytic-planner cost accounting."""
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
SPEC = importlib.util.spec_from_file_location('scale_certificate_v54', Path(__file__).with_name('analyze_lmta_scale_v54.py'))
v54 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v54)
v53, v52, TOL = v54.v53, v54.v52, 1e-10
METHODS = ['LOOKAHEAD_1', 'LOOKAHEAD_2', 'LOOKAHEAD_FULL_ANALYTIC']
ANALYTIC = METHODS[2]
LIMITS = dict(max_planner_action_values=2000000, max_policy_states=100000, max_wall_seconds=60.)
PANELS = [dict(nodes=9, stratum='sparse', expected_degree=1.5, p=1.5/8, seeds=list(range(580000, 580016))),
          dict(nodes=9, stratum='dense', expected_degree=4.5, p=4.5/8, seeds=list(range(580100, 580116))),
          dict(nodes=11, stratum='sparse', expected_degree=1.5, p=1.5/10, seeds=list(range(580200, 580216))),
          dict(nodes=11, stratum='dense', expected_degree=4.5, p=4.5/10, seeds=list(range(580300, 580316)))]
PROTOCOL = dict(budget=2, horizon=3, methods=METHODS, panels=PANELS, limits=LIMITS)
identity = v54.identity


def verify_case(case, rows, edges, nodes, limits=LIMITS):
    """Check actual V58 identities before a non-mutating FULL certificate view."""
    errors = Counter()
    if (case.get('method') not in METHODS or case.get('value_source') != 'V58_full_policy_evaluation'
            or case.get('control_method') is not None or any(row.get('method') != case['method'] for row in rows)):
        errors['actual_V58_method_and_value_source'] += 1
    if case.get('method') not in METHODS:
        return dict(passed=False, errors=dict(errors), quality_verified=False, state_records=len(rows))
    method = 'LOOKAHEAD_FULL' if case['method'] == ANALYTIC else case['method']
    view = dict(case, method=method, value_source='V54_full_policy_evaluation')
    checked = v54.verify_case(view, [dict(row, method=method) for row in rows], edges, nodes, limits)
    errors.update(checked['errors'])
    for row in rows:
        reported = row.get('root_action_values', [])
        if reported and all(v52.finite(action.get('value')) for action in reported):
            best = max(action['value'] for action in reported)
            selected = min(tuple(sorted(action['selected'])) for action in reported if action['value'] == best)
            if tuple(row['selected']) != selected or row.get('planned_value') != best:
                errors['reported_strict_argmax_and_lex_tie'] += 1
        if case['method'] == ANALYTIC:
            work = row.get('decision_work', {})
            if (not all(isinstance(work.get(name), int) and work[name] >= 0 for name in
                    ('analytic_expectation_calls', 'analytic_probability_terms'))
                    or work.get('action_value_evaluations') != work.get('kernel_builds', 0)
                    + work.get('kernel_cache_hits', 0) + work.get('analytic_expectation_calls', 0)
                    or work.get('target_probability_evaluations', 0) < work.get('analytic_probability_terms', 0)):
                errors['analytic_work_partition'] += 1
    fields = ('prepare_gc_seconds', 'cleanup_seconds', 'decision_total_seconds', 'block_seconds')
    if not all(v52.finite(case.get(name)) and case[name] >= 0 for name in fields):
        errors['gc_costs'] += 1
    else:
        if not v53.close(case['decision_total_seconds'], case['decision_seconds'] + case['cleanup_seconds']):
            errors['decision_total_includes_cleanup'] += 1
        if not v53.close(case['block_seconds'], case['wall_seconds'] + case['cleanup_seconds']):
            errors['block_includes_evaluation_and_cleanup'] += 1
    return dict(checked, passed=not errors, errors=dict(errors),
                quality_verified=case.get('status') == 'complete' and not errors)


def case_accounting(cases):
    fees = v54.case_accounting(cases)
    fees.update({name: math.fsum(case[name] for case in cases if v52.finite(case.get(name))) for name in
                 ('prepare_gc_seconds', 'cleanup_seconds', 'decision_total_seconds', 'block_seconds')})
    return fees


def work_ratios(costs):
    """Ratios of sums across each method's own full reachable-policy workload."""
    result = {}
    for numerator, denominator in ((METHODS[1], METHODS[0]), (ANALYTIC, METHODS[1]), (ANALYTIC, METHODS[0])):
        values = {}
        for group in ('decision_work', 'evaluation_work', 'expected_decision_work'):
            a, b = costs[numerator].get(group) or {}, costs[denominator].get(group) or {}
            values[group] = {name: a.get(name, 0) / number if number > 0 else None for name, number in b.items()}
        for name in ('decision_seconds', 'decision_total_seconds', 'wall_seconds', 'block_seconds', 'expected_decision_seconds'):
            a, b = costs[numerator][name], costs[denominator][name]
            values[name] = a / b if v52.finite(a) and v52.finite(b) and b > 0 else None
        result[numerator + '_over_' + denominator] = values
    return result


def stratum_summary(panel, cases, integrity_passed):
    expected = Counter(itertools.product(panel['seeds'], METHODS))
    complete = (integrity_passed and Counter((row['graph_id'], row['method']) for row in cases) == expected
                and all(row['status'] == 'complete' for row in cases))
    costs = {method: case_accounting([row for row in cases if row['method'] == method]) for method in METHODS}
    result = dict(nodes=panel['nodes'], stratum=panel['stratum'], expected_degree=panel['expected_degree'], p=panel['p'],
        quality_complete=complete, expected_graphs=len(panel['seeds']), terminal_cases=len(cases),
        complete_cases=sum(row['status'] == 'complete' for row in cases),
        resource_limited_cases=sum(row['status'] == 'resource_limit' for row in cases),
        costs_by_method=costs, values=None, contrasts=None, per_graph=None,
        sum_gain_over_sum_headroom=None, ratios_of_total_work_and_cost=None)
    if complete:
        lookup = {(row['graph_id'], row['method']): row['root_value'] for row in cases}
        points = []
        for graph in panel['seeds']:
            myopic, two, full = (lookup[graph, method] for method in METHODS)
            points.append(dict(graph_id=graph, values=dict(zip(METHODS, (myopic, two, full))),
                two_minus_myopic=two-myopic, full_minus_two=full-two, full_minus_myopic=full-myopic,
                headroom_fraction=(two-myopic)/(full-myopic) if full-myopic > TOL else None))
        headroom = math.fsum(point['full_minus_myopic'] for point in points)
        result.update(values={method: v53.descriptive([point['values'][method] for point in points]) for method in METHODS},
            contrasts={name: v53.descriptive([point[name] for point in points]) for name in
                       ('two_minus_myopic', 'full_minus_two', 'full_minus_myopic', 'headroom_fraction')},
            per_graph=points, sum_gain_over_sum_headroom=math.fsum(point['two_minus_myopic'] for point in points)/headroom
                if headroom > TOL else None, ratios_of_total_work_and_cost=work_ratios(costs))
    return result


def scale_comparisons(strata):
    result = []
    for name in ('sparse', 'dense'):
        small, large = (next(row for row in strata if row['stratum'] == name and row['nodes'] == n) for n in (9, 11))
        comparisons = None
        if small['quality_complete'] and large['quality_complete']:
            comparisons = {}
            for method in METHODS:
                a, b = large['costs_by_method'][method], small['costs_by_method'][method]
                ratios = {}
                for group in ('expected_decision_work', 'decision_work', 'evaluation_work'):
                    ratios[group] = {key: (a[group].get(key, 0)/a['case_records']) / (value/b['case_records'])
                                     if value > 0 else None for key, value in b[group].items()}
                comparisons[method] = ratios
        result.append(dict(stratum=name, nodes_numerator=11, nodes_denominator=9,
            ratios_of_per_graph_mean_work=comparisons,
            scope='descriptive independent graph groups, fixed K=2; no paired timing interpretation'))
    return result


def summarize(manifest, cases, states, source_analysis):
    started, errors = perf_counter(), Counter()
    bindings = {seed: panel for panel in PANELS for seed in panel['seeds']}
    expected = Counter(itertools.product(bindings, [3], METHODS))
    if (manifest.get('schema') != 'acfqp.lmta_analytic_scale.v58' or manifest.get('status') != 'complete'
            or manifest.get('protocol') != PROTOCOL or manifest.get('source_directory') != 'reports/lmta_paired_timing_v57'
            or manifest.get('cold_decisions') is not True or manifest.get('runtime', {}).get('gc_enabled') is not True):
        errors['manifest_protocol'] += 1
    if (source_analysis.get('integrity', {}).get('passed') is not True
            or source_analysis.get('complete_performance_evidence') is not True):
        errors['source_V57_not_complete_and_valid'] += 1
    if (manifest.get('new_graphs') != 64 or any(manifest.get(name) != 0 for name in
            ('new_environment_samples', 'new_environment_calls', 'new_RL_updates', 'new_MCTS_calls'))):
        errors['graph_or_environment_work'] += 1
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
    cost_names = ('source_read_seconds', 'graph_generation_seconds', 'data_output_seconds', 'whole_runner_seconds', 'runner_cpu_seconds',
                  'process_peak_rss_bytes')
    if any(not v52.finite(manifest.get(name)) or manifest[name] < 0 for name in cost_names):
        errors['manifest_costs'] += 1
    grouped = defaultdict(list)
    for row in states:
        grouped[identity(row)].append(row)
    if grouped.keys() - expected.keys():
        errors['unbound_state_case'] += 1
    validations = []
    for case in cases:
        key, panel = identity(case), bindings.get(case.get('graph_id'))
        if (key not in expected or case['graph_id'] not in valid_graphs or case.get('budget') != 2 or panel is None
                or any(case.get(name) != panel[name] for name in ('nodes', 'stratum', 'p'))):
            errors['case_binding'] += 1
            continue
        graph = valid_graphs[case['graph_id']]
        checked = verify_case(case, grouped[key], graph['edges'], graph['nodes'])
        validations.append(dict(graph_id=key[0], horizon=key[1], method=key[2], **checked))
        if not checked['passed']:
            errors['invalid_case_certificate_or_costs'] += 1
    if counts == expected:
        lookup = {identity(case): case for case in cases}
        for graph in bindings:
            rows = [lookup[graph, 3, method] for method in METHODS]
            if all(row['status'] == 'complete' and v52.finite(row['root_value']) for row in rows):
                if max(row['root_value'] for row in rows[:2]) > rows[2]['root_value'] + TOL:
                    errors['full_horizon_upper_bound'] += 1
    strata = [stratum_summary(panel, [case for case in cases if case.get('nodes') == panel['nodes']
               and case.get('stratum') == panel['stratum']], not errors) for panel in PANELS]
    return dict(schema='acfqp.lmta_analytic_scale_analysis.v58', protocol=PROTOCOL,
        integrity=dict(passed=not errors, errors=dict(errors), terminal_execution_complete=terminal,
            expected_case_records=192, case_records=len(cases), state_records=len(states), successful_cases=successful,
            resource_limited_cases=limited, case_validations=validations),
        complete_quality_evidence=not errors and successful == 192, strata=strata,
        descriptive_scale_comparisons=scale_comparisons(strata), root_values=cases,
        accounting=dict(new_cases=case_accounting(cases),
            **{name: manifest.get(name) for name in (*cost_names, 'data_bytes', 'new_graphs', 'new_environment_samples',
               'new_environment_calls', 'new_RL_updates', 'new_MCTS_calls')}, retained_V57=source_analysis.get('accounting'),
            analysis_wall_seconds_before_serialization=perf_counter()-started,
            analysis_independent_query_checks=sum(row.get('planned_roots', 0)+row.get('forced_roots', 0) for row in validations),
            analysis_full_policy_equations=sum(row.get('full_policy_equations', 0) for row in validations),
            scope='Every complete or interrupted decision, evaluation, cleanup and serialization is charged. '
                  'GC preparation is separate; timing component views overlap and are not additive. '
                  'Cleanup includes outer policy evaluation objects. Reach-weighted work is the main scale measure; '
                  'weighted planning time is secondary and excludes batch cleanup. Prior V57 remains historical.'),
        inference_scope='Fresh fixed-degree N9/N11 panel. Incomplete strata have null quality means and no replacement '
            'cohort. Each method is evaluated under its own policy; neither exact action identity with historical FULL '
            'nor equal policy-dependent workloads is assumed. Work ratios compare sums for these full evaluations. '
            'Negative gains remain and zero-headroom ratios are null. No independent-sample CI or adoption Gate.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_analytic_scale_v58')
    parser.add_argument('--control-dir', type=Path, default=ROOT / 'reports/lmta_paired_timing_v57')
    args = parser.parse_args()
    started = perf_counter()
    manifest = json.loads((args.output_dir / 'manifest.json').read_text())
    cases = [json.loads(line) for line in (args.output_dir / 'cases.jsonl').read_text().splitlines()]
    states = [json.loads(line) for line in (args.output_dir / 'states.jsonl').read_text().splitlines()]
    source = json.loads((args.control_dir / 'analysis.json').read_text())
    result = summarize(manifest, cases, states, source)
    result['accounting']['analysis_wall_seconds_including_reads'] = perf_counter()-started
    (args.output_dir / 'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(integrity=result['integrity'], complete_quality_evidence=result['complete_quality_evidence'])))


if __name__ == '__main__':
    main()
