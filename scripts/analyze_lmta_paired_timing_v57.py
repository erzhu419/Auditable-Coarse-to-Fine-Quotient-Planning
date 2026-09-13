"""Paired cold-query timing ledgers; no dynamic-programming revalidation."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import statistics
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
FULL, ANALYTIC = 'LOOKAHEAD_FULL', 'LOOKAHEAD_FULL_ANALYTIC'
METHODS = [FULL, ANALYTIC]
PANELS = [dict(nodes=7, stratum='sparse', expected_degree=1.5, p=.25, seeds=list(range(550000, 550016))),
          dict(nodes=7, stratum='dense', expected_degree=4.5, p=.75, seeds=list(range(550100, 550116))),
          dict(nodes=9, stratum='sparse', expected_degree=1.5, p=.1875, seeds=list(range(550200, 550216))),
          dict(nodes=9, stratum='dense', expected_degree=4.5, p=.5625, seeds=list(range(550300, 550316)))]
LIMITS = dict(max_planner_action_values=2000000, max_policy_states=100000, max_wall_seconds=60.)
PROTOCOL = dict(budget=2, horizon=3, methods=METHODS, repetitions=6, panels=PANELS,
    warmup=dict(graph_id=550000, repetitions=5, query='root'),
    order=dict(graphs='ascending_on_even_repetition_descending_on_odd',
               first_method='control_if_repetition_plus_canonical_graph_index_even'),
    gc_policy='default_enabled_collect_before_and_after_each_block', limits=LIMITS)
SOURCE_DIRS = dict(control='reports/lmta_tie_refinement_v55', analytic='reports/lmta_analytic_terminal_v56')


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def close(a, b):
    return finite(a) and finite(b) and math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10)


def state_key(row):
    return tuple(row['statuses']), row['remaining_budget'], row['remaining_days']


def identity(row):
    return tuple(row.get(name) for name in ('phase', 'repetition', 'graph_id', 'method', 'position'))


def expected_order():
    result = []
    ids = sorted(seed for panel in PANELS for seed in panel['seeds'])
    for repetition in range(5):
        order = METHODS if repetition % 2 == 0 else METHODS[::-1]
        result.extend(('warmup', repetition, 550000, method, position) for position, method in enumerate(order))
    canonical = {graph: index for index, graph in enumerate(ids)}
    for repetition in range(6):
        for graph in ids if repetition % 2 == 0 else ids[::-1]:
            order = METHODS if (repetition + canonical[graph]) % 2 == 0 else METHODS[::-1]
            result.extend(('measured', repetition, graph, method, position) for position, method in enumerate(order))
    return result


def verify_case(case, source_rows, reach, limits=LIMITS):
    errors = Counter()

    def check(name, passed):
        if not passed:
            errors[name] += 1

    complete = case.get('status') == 'complete'
    check('terminal_status', case.get('status') in ('complete', 'resource_limit'))
    count = case.get('query_count')
    durations = case.get('query_seconds', [])
    check('query_coverage', isinstance(count, int) and 1 <= count <= len(source_rows)
          and case.get('source_state_records') == len(source_rows) and len(durations) == count
          and (not complete or count == len(source_rows)))
    check('query_times', all(finite(number) and number >= 0 for number in durations))
    prefix = source_rows[:count] if isinstance(count, int) else []
    expected_work = Counter()
    for row in prefix:
        expected_work.update(row['decision_work'])
    check('source_prefix_work', Counter(case.get('decision_work', {})) == expected_work
          and case.get('decision_work', {}).get('planner_calls') == count)
    check('direct_output_comparison', case.get('output_mismatches') == [])
    fields = ('prepare_gc_seconds', 'loop_seconds', 'decision_seconds', 'cleanup_seconds', 'decision_total_seconds',
              'bookkeeping_seconds', 'block_seconds', 'last_limit_check_seconds')
    check('nonnegative_costs', all(finite(case.get(name)) and case[name] >= 0 for name in fields))
    if all(finite(case.get(name)) for name in fields) and all(finite(number) for number in durations):
        check('decision_time_sum', close(case['decision_seconds'], math.fsum(durations)))
        check('loop_partition', close(case['loop_seconds'], case['decision_seconds'] + case['bookkeeping_seconds']))
        check('primary_includes_cleanup', close(case['decision_total_seconds'], case['decision_seconds'] + case['cleanup_seconds']))
        check('block_partition', close(case['block_seconds'], case['loop_seconds'] + case['cleanup_seconds']))
        check('limit_clock_boundary', case['last_limit_check_seconds'] <= case['loop_seconds'] + 1e-10)
    observed = dict(max_planner_action_values=case.get('decision_work', {}).get('action_value_evaluations', 0),
                    max_policy_states=count, max_wall_seconds=case.get('last_limit_check_seconds'))
    triggered = [name for name in LIMITS if finite(observed[name]) and observed[name] >= limits[name]]
    check('postdecision_limit_reason', (not triggered and case.get('stop_reason') is None) if complete else
          (bool(triggered) and case.get('stop_reason') == triggered[0]))
    if complete:
        weighted = math.fsum(seconds * probability for seconds, probability in zip(durations, reach))
        check('source_weighted_planning', len(reach) == len(source_rows)
              and close(case.get('source_weighted_planning_seconds'), weighted))
    else:
        check('partial_weighted_time', case.get('source_weighted_planning_seconds') is None)
    return dict(passed=not errors, errors=dict(errors), query_count=count,
                output_mismatch_count=len(case.get('output_mismatches') or []), complete=complete)


def accounting(cases):
    work = Counter()
    for case in cases:
        work.update(case.get('decision_work', {}))
    fields = ('prepare_gc_seconds', 'loop_seconds', 'decision_seconds', 'cleanup_seconds', 'decision_total_seconds',
              'bookkeeping_seconds', 'block_seconds')
    return dict(case_records=len(cases), query_records=sum(len(case.get('query_seconds', [])) for case in cases),
        declared_queries=sum(case.get('query_count', 0) for case in cases), decision_work=dict(work),
        complete_cases=sum(case.get('status') == 'complete' for case in cases),
        resource_limited_cases=sum(case.get('status') == 'resource_limit' for case in cases),
        output_mismatch_records=sum(len(case.get('output_mismatches') or []) for case in cases),
        **{name: math.fsum(case[name] for case in cases if finite(case.get(name))) for name in fields})


def paired_round(pairs):
    totals = {method: {name: math.fsum(pair[method][name] for pair in pairs) for name in
        ('decision_total_seconds', 'block_seconds', 'source_weighted_planning_seconds')} for method in METHODS}
    def ratio(name):
        denominator = totals[FULL][name]
        return totals[ANALYTIC][name] / denominator if denominator > 0 else None
    return dict(graph_pairs=len(pairs), full=totals[FULL], analytic=totals[ANALYTIC],
        primary_ratio=ratio('decision_total_seconds'),
        absolute_saved_seconds=totals[FULL]['decision_total_seconds'] - totals[ANALYTIC]['decision_total_seconds'],
        block_ratio=ratio('block_seconds'), source_weighted_planning_ratio=ratio('source_weighted_planning_seconds'))


def round_statistics(rounds):
    result = {}
    for field in ('primary_ratio', 'absolute_saved_seconds', 'block_ratio', 'source_weighted_planning_ratio'):
        values = [row[field] for row in rounds if row[field] is not None]
        result[field] = dict(rounds=len(rounds), available_rounds=len(values), median=statistics.median(values) if values else None,
                             minimum=min(values) if values else None, maximum=max(values) if values else None)
    return result


def stratum_summary(panel, cases, valid):
    expected = Counter((repetition, graph, method) for repetition in range(6) for graph in panel['seeds'] for method in METHODS)
    complete = valid and Counter((row['repetition'], row['graph_id'], row['method']) for row in cases) == expected
    complete = complete and all(row['status'] == 'complete' and row['output_mismatches'] == [] for row in cases)
    result = dict(nodes=panel['nodes'], stratum=panel['stratum'], p=panel['p'], complete_performance_evidence=complete,
        costs_by_method={method: accounting([row for row in cases if row['method'] == method]) for method in METHODS},
        repetitions=None, six_round_summary=None, order_effects=None)
    if complete:
        lookup = {(row['repetition'], row['graph_id'], row['method']): row for row in cases}
        rounds = []
        order_rounds = {'FULL_then_ANALYTIC': [], 'ANALYTIC_then_FULL': []}
        for repetition in range(6):
            pairs = [{method: lookup[repetition, graph, method] for method in METHODS} for graph in panel['seeds']]
            rounds.append(dict(repetition=repetition, **paired_round(pairs)))
            for name, position in (('FULL_then_ANALYTIC', 0), ('ANALYTIC_then_FULL', 1)):
                selected = [pair for pair in pairs if pair[FULL]['position'] == position]
                order_rounds[name].append(dict(repetition=repetition, **paired_round(selected)))
        result.update(repetitions=rounds, six_round_summary=round_statistics(rounds),
            order_effects={name: dict(repetitions=values, six_round_summary=round_statistics(values)) for name, values in order_rounds.items()})
    return result


def summarize(manifest, cases, control_manifest, control_analysis, control_states,
              analytic_manifest, analytic_analysis, analytic_states):
    started = perf_counter()
    errors = Counter()

    def check(name, passed):
        if not passed:
            errors[name] += 1

    ids = sorted(seed for panel in PANELS for seed in panel['seeds'])
    check('frozen_protocol', manifest.get('schema') == 'acfqp.lmta_paired_timing.v57'
          and manifest.get('status') == 'complete' and manifest.get('protocol') == PROTOCOL
          and manifest.get('source_directories') == SOURCE_DIRS and manifest.get('cold_decisions') is True
          and manifest.get('runtime', {}).get('gc_enabled') is True)
    check('source_certificates', control_manifest.get('schema') == 'acfqp.lmta_tie_refinement.v55'
          and analytic_manifest.get('schema') == 'acfqp.lmta_analytic_terminal.v56'
          and control_manifest.get('status') == analytic_manifest.get('status') == 'complete'
          and control_analysis.get('integrity', {}).get('passed') is True
          and control_analysis.get('fresh_complete_quality_evidence') is True
          and analytic_analysis.get('integrity', {}).get('passed') is True
          and analytic_analysis.get('policy_value_preserved_all') is True)
    expected_graphs = sorted((row for row in control_manifest.get('graphs', []) if row['graph_id'] in ids),
                             key=lambda row: row['graph_id'])
    check('source_graph_binding', [row['graph_id'] for row in expected_graphs] == ids
          and all(row.get('panel') == 'fresh' for row in expected_graphs)
          and manifest.get('graphs') == analytic_manifest.get('graphs') == expected_graphs)
    metadata = {row['graph_id']: row for row in expected_graphs}
    for panel in PANELS:
        check('frozen_graph_panel', all(graph in metadata and all(metadata[graph].get(key) == panel[key]
              for key in ('nodes', 'stratum', 'p')) for graph in panel['seeds']))
    source = {method: defaultdict(list) for method in METHODS}
    for method, rows in ((FULL, control_states), (ANALYTIC, analytic_states)):
        for row in rows:
            if row['graph_id'] in ids and row['method'] == method:
                source[method][row['graph_id']].append(row)
    for graph in ids:
        left, right = source[FULL][graph], source[ANALYTIC][graph]
        keys = [state_key(row) for row in left]
        check('source_query_order', bool(left) and keys == [state_key(row) for row in right]
              and len(set(keys)) == len(keys))
        check('source_reach_values', all(finite(row.get('reach_probability'))
              and 0 <= row['reach_probability'] <= 1 + 1e-10 for row in left))
    source_count = sum(map(len, source[FULL].values()))
    check('source_query_count', source_count == 20112 and manifest.get('source_state_records') == source_count
          and analytic_manifest.get('source_full_state_records') == source_count)
    order = [identity(row) for row in cases]
    check('exact_paired_sequence', order == expected_order())
    check('unique_blocks', len(set(order)) == len(order))
    first_counts = Counter((row['graph_id'], row['method']) for row in cases
                           if row['phase'] == 'measured' and row['position'] == 0)
    check('three_first_blocks_per_method_graph', first_counts == Counter({(graph, method): 3 for graph in ids for method in METHODS}))
    check('manifest_counts', manifest.get('completed_blocks') == len(cases) == 778
          and manifest.get('completed_measured_blocks') == sum(row['phase'] == 'measured' for row in cases) == 768
          and manifest.get('completed_warmup_blocks') == sum(row['phase'] == 'warmup' for row in cases) == 10
          and manifest.get('successful_blocks') == sum(row['status'] == 'complete' for row in cases)
          and manifest.get('resource_limited_blocks') == sum(row['status'] == 'resource_limit' for row in cases)
          and manifest.get('total_query_count') == sum(row['query_count'] for row in cases))
    zero_fields = ('new_graphs', 'new_environment_samples', 'new_environment_calls', 'new_RL_updates',
                   'new_MCTS_calls', 'new_full_policy_evaluations', 'new_independent_DP_checks')
    check('no_new_quality_or_environment_computation', all(manifest.get(key) == 0 for key in zero_fields))
    manifest_times = ('source_read_seconds', 'graph_reconstruction_seconds', 'data_output_seconds',
                      'whole_runner_seconds', 'runner_cpu_seconds')
    check('manifest_costs', all(finite(manifest.get(key)) and manifest[key] >= 0 for key in manifest_times))
    source_and_schedule_valid = not errors
    validations = []
    case_valid = []
    for row in cases:
        graph, method = row['graph_id'], row['method']
        references = source.get(method, {}).get(graph, [])
        base = source[FULL].get(graph, [])
        if row['phase'] == 'warmup':
            references = [ref for ref in references if state_key(ref) == ((0,) * row['nodes'], 2, 3)]
            base = [ref for ref in base if state_key(ref) == ((0,) * row['nodes'], 2, 3)]
        result = verify_case(row, references, [ref['reach_probability'] for ref in base])
        if graph not in metadata or any(row.get(key) != metadata[graph].get(key) for key in ('nodes', 'stratum', 'p')) \
                or row.get('budget') != 2 or row.get('horizon') != 3:
            result['errors']['case_metadata'] = 1
            result['passed'] = False
        errors.update(result['errors'])
        case_valid.append(result['passed'])
        validations.append(dict(phase=row['phase'], repetition=row['repetition'], graph_id=graph,
                                method=method, position=row['position'], **result))
    warmup_valid = all(ok for row, ok in zip(cases, case_valid) if row['phase'] == 'warmup')
    strata = []
    for panel in PANELS:
        selected = [(row, ok) for row, ok in zip(cases, case_valid)
                    if row['phase'] == 'measured' and row['graph_id'] in panel['seeds']]
        strata.append(stratum_summary(panel, [row for row, _ in selected],
                      source_and_schedule_valid and warmup_valid and all(ok for _, ok in selected)))
    fees = dict(all_blocks=accounting(cases),
        warmup=accounting([row for row in cases if row['phase'] == 'warmup']),
        measured=accounting([row for row in cases if row['phase'] == 'measured']),
        runner={key: manifest.get(key) for key in (*manifest_times, 'process_peak_rss_bytes', 'data_bytes')},
        new_environment_samples=0, new_RL_updates=0, new_MCTS_calls=0,
        analysis_independent_DP_checks=0, analysis_full_policy_evaluations=0,
        partition_note='warmup and measured partition all_blocks; timing component views are not additive totals')
    fees['analysis_seconds'] = perf_counter() - started
    return dict(schema='acfqp.lmta_paired_timing_analysis.v57',
        integrity=dict(passed=not errors, errors=dict(errors)),
        complete_performance_evidence=all(row['complete_performance_evidence'] for row in strata),
        scope=dict(primary='fixed-query batch planning plus cleanup',
                   block='planning, in-loop record checking, and cleanup',
                   secondary='source-reach-weighted planning only; excludes batch cleanup',
                   repeats='six timing repetitions of fixed graphs and queries; no independent-query CI',
                   quality='V55/V56 policy certificate reused; no new quality evaluation',
                   source_bytes='frozen source bytes compared by runner before timing'),
        strata=strata, block_validation=validations, accounting=fees,
        retained_source_accounting=dict(control=control_analysis.get('accounting'),
                                        analytic=analytic_analysis.get('accounting')),
        historical_cost_scope='source ledgers retained separately; never added to new costs or refunded')


def read_jsonl(path, method=None):
    rows = []
    with path.open() as handle:
        for line in handle:
            row = json.loads(line)
            if method is None or row['method'] == method:
                rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_paired_timing_v57')
    parser.add_argument('--control-dir', type=Path, default=ROOT / SOURCE_DIRS['control'])
    parser.add_argument('--analytic-dir', type=Path, default=ROOT / SOURCE_DIRS['analytic'])
    args = parser.parse_args()
    started = perf_counter()
    result = summarize(json.loads((args.output_dir / 'manifest.json').read_text()),
        read_jsonl(args.output_dir / 'cases.jsonl'),
        json.loads((args.control_dir / 'manifest.json').read_text()),
        json.loads((args.control_dir / 'analysis.json').read_text()),
        read_jsonl(args.control_dir / 'states.jsonl', FULL),
        json.loads((args.analytic_dir / 'manifest.json').read_text()),
        json.loads((args.analytic_dir / 'analysis.json').read_text()),
        read_jsonl(args.analytic_dir / 'states.jsonl', ANALYTIC))
    result['accounting']['analysis_cli_seconds_including_reads'] = perf_counter() - started
    (args.output_dir / 'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(integrity=result['integrity'], complete_performance_evidence=result['complete_performance_evidence'])))


if __name__ == '__main__':
    main()
