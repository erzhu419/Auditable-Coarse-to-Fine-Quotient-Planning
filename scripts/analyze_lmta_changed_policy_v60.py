"""Evaluate the one changed policy and reuse the other certified depth results."""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
import math
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

v54 = load('changed_certificate_v54', 'analyze_lmta_scale_v54.py')
v59 = load('changed_summary_v59', 'analyze_lmta_analytic_short_v59.py')
v53, v52 = v54.v53, v54.v52
METHOD, SOURCE_METHOD, GRAPH = 'LOOKAHEAD_1_ANALYTIC', 'LOOKAHEAD_1', 580109
LIMITS = dict(max_planner_action_values=2000000, max_policy_states=100000, max_wall_seconds=60.)
CHANGED_STATE = dict(statuses=[0,0,2,0,1,0,1,1,0], remaining_budget=1, remaining_days=2)
PROTOCOL = dict(graph_id=GRAPH, method=METHOD, budget=2, horizon=3, limits=LIMITS, changed_state=CHANGED_STATE)
SOURCE_DIRS = dict(policies='reports/lmta_analytic_scale_v58', replay='reports/lmta_analytic_short_v59')


def verify_case(case, rows, edges, nodes, limits=LIMITS):
    errors = Counter()
    if (case.get('method') != METHOD or case.get('graph_id') != GRAPH
            or case.get('value_source') != 'V60_full_policy_evaluation' or case.get('control_method') is not None
            or any(row.get('method') != METHOD for row in rows)):
        errors['V60_identity_and_value_source'] += 1
    checked = v54.verify_case(dict(case, method=SOURCE_METHOD, value_source='V54_full_policy_evaluation'),
        [dict(row, method=SOURCE_METHOD) for row in rows], edges, nodes, limits)
    errors.update(checked['errors'])
    for row in rows:
        choices = v53.actions(*v52.state_key(row))
        work = row['decision_work']
        forced = len(choices) == 1
        if (work.get('action_value_evaluations') != (0 if forced else len(choices))
                or work.get('analytic_expectation_calls') != work.get('action_value_evaluations')
                or work.get('analytic_probability_terms') != (0 if forced else sum(row['statuses'].count(0)-len(action) for action in choices))
                or work.get('target_probability_evaluations') != work.get('analytic_probability_terms')
                or any(work.get(name, 0) != 0 for name in
                       ('kernel_builds', 'kernel_cache_hits', 'transition_outcomes', 'bellman_expectation_terms'))):
            errors['single_window_analytic_work'] += 1
        q = row.get('root_action_values', [])
        if q and all(v52.finite(action.get('value')) for action in q):
            maximum = max(action['value'] for action in q)
            selected = min(tuple(action['selected']) for action in q if action['value'] == maximum)
            if tuple(row['selected']) != selected or row.get('planned_value') != maximum:
                errors['reported_strict_choice'] += 1
    if (not all(v52.finite(case.get(name)) and case[name] >= 0 for name in
                ('prepare_gc_seconds', 'cleanup_seconds', 'decision_total_seconds', 'block_seconds'))
            or not v53.close(case.get('decision_total_seconds'), case['decision_seconds']+case.get('cleanup_seconds', 0))
            or not v53.close(case.get('block_seconds'), case['wall_seconds']+case.get('cleanup_seconds', 0))):
        errors['gc_cost_views'] += 1
    return dict(checked, passed=not errors, errors=dict(errors), quality_verified=case.get('status')=='complete' and not errors)


def costs(case):
    result = v54.case_accounting([case])
    result.update({name: case.get(name) for name in ('prepare_gc_seconds', 'cleanup_seconds', 'decision_total_seconds', 'block_seconds')})
    return result


def policy_change(case, rows, old_case, old_rows):
    old, new = ({v52.state_key(row): row for row in values} for values in (old_rows, rows))
    key = v52.state_key(CHANGED_STATE)
    left, right = old.get(key), new.get(key)
    return dict(old_root_value=old_case['root_value'], new_root_value=case['root_value'],
        root_value_difference=case['root_value']-old_case['root_value'],
        reachable_state_sets=dict(old_count=len(old), new_count=len(new), shared_count=len(old.keys() & new.keys()),
            newly_reachable_count=len(new.keys()-old.keys()), no_longer_reachable_count=len(old.keys()-new.keys())),
        known_changed_state=dict(**CHANGED_STATE, old_reachable=left is not None, new_reachable=right is not None,
            old_full_value=left['value'] if left else None, new_full_value=right['value'] if right else None,
            full_value_difference=right['value']-left['value'] if left and right else None,
            old_reach_probability=left['reach_probability'] if left else 0.,
            new_reach_probability=right['reach_probability'] if right else 0.,
            reach_probability_difference=(right['reach_probability'] if right else 0.)-(left['reach_probability'] if left else 0.)))


def unified_strata(case, source58_cases, source59_cases, certificates):
    old = {v59.identity(row): row for row in source58_cases}
    checks = [dict(row) for row in certificates]
    fresh_values = [row for row in checks if v59.identity(row) != (GRAPH, METHOD)]
    fresh_values.append(dict(graph_id=GRAPH, method=METHOD, candidate_policy_value=case['root_value']))
    replay = [row for row in source59_cases if v59.identity(row) != (GRAPH, METHOD)]
    replay.append(dict(case, source_weighted_decision_work=case['expected_decision_work'],
        source_weighted_decision_seconds=case['expected_decision_seconds']))
    result = []
    for panel in v59.PANELS:
        summary = v59.three_depth_summary(panel,
            [row for row in replay if row['graph_id'] in panel['seeds']],
            [old[graph, v59.FULL] for graph in panel['seeds']],
            [row for row in fresh_values if row['graph_id'] in panel['seeds']])
        for point in summary['per_graph']:
            point['provenance'] = {method: 'V60_fresh_full_policy_evaluation' if (point['graph_id'], method)==(GRAPH,METHOD)
                else 'V59_preserved_policy_reuse' for method in v59.METHODS}
            point['provenance'][v59.FULL] = 'V58_full_policy_reuse'
        summary['provenance'] = dict(target='V60 fresh evaluation; action preservation is not asserted',
            other_short_policies='127 V59 action-preservation certificates', full='64 retained V58 full-policy evaluations')
        summary['scope'] = 'Expected work uses each certified policy occupancy. Different-run times are descriptive, not paired speedup evidence.'
        result.append(dict(nodes=panel['nodes'], stratum=panel['stratum'], p=panel['p'], **summary))
    return result


def summarize(manifest, case, states, source58_manifest, source58_analysis, source58_cases,
              source58_target_rows, source59_analysis, source59_cases):
    started, errors = perf_counter(), Counter()
    ids = {seed for panel in v59.PANELS for seed in panel['seeds']}
    source = {v59.identity(row): row for row in source58_cases}
    if (manifest.get('schema') != 'acfqp.lmta_changed_policy.v60' or manifest.get('status') != 'complete'
            or manifest.get('protocol') != PROTOCOL or manifest.get('source_directories') != SOURCE_DIRS
            or manifest.get('cold_decisions') is not True or manifest.get('runtime', {}).get('gc_enabled') is not True):
        errors['manifest_protocol'] += 1
    graphs = {row['graph_id']: row for row in source58_manifest.get('graphs', [])}
    graph = graphs.get(GRAPH)
    if manifest.get('graph') != graph or graph is None:
        errors['graph_binding'] += 1
    if (source58_manifest.get('schema') != 'acfqp.lmta_analytic_scale.v58' or source58_manifest.get('status') != 'complete'
            or source58_analysis.get('integrity', {}).get('passed') is not True
            or source58_analysis.get('complete_quality_evidence') is not True
            or source59_analysis.get('integrity', {}).get('passed') is not True
            or source59_analysis.get('integrity', {}).get('terminal_execution_complete') is not True):
        errors['source_certificates'] += 1
    expected_old = Counter((graph_id, method) for graph_id in ids for method in v59.SOURCE_METHODS+[v59.FULL])
    expected_replay = Counter((graph_id, method) for graph_id in ids for method in v59.METHODS)
    if (Counter(v59.identity(row) for row in source58_cases) != expected_old
            or any(row.get('status') != 'complete' for row in source58_cases)
            or Counter(v59.identity(row) for row in source59_cases) != expected_replay
            or any(row.get('status') != 'complete' for row in source59_cases)):
        errors['source_case_rosters'] += 1
    certificates = source59_analysis.get('integrity', {}).get('case_validations', [])
    source_127 = Counter(v59.identity(row) for row in certificates) == expected_replay
    for row in certificates:
        key = v59.identity(row)
        old = source.get((key[0], v59.SOURCES.get(key[1])))
        is_target = key == (GRAPH, METHOD)
        expected_value = old['root_value'] if old else None
        correct = (row.get('passed') is True and row.get('value_agreement') is True and old is not None
            and row.get('source_policy_value') == expected_value
            and row.get('policy_value_preserved') is (not is_target)
            and row.get('action_preserved') is (not is_target)
            and row.get('candidate_policy_value') == (None if is_target else expected_value))
        source_127 = source_127 and correct
    if not source_127:
        errors['exact_127_preserved_and_one_target_changed'] += 1
    target_old = source.get((GRAPH, SOURCE_METHOD))
    if (target_old is None or target_old.get('state_records') != len(source58_target_rows)
            or any(row.get('graph_id') != GRAPH or row.get('method') != SOURCE_METHOD for row in source58_target_rows)
            or v52.state_key(CHANGED_STATE) not in {v52.state_key(row) for row in source58_target_rows}):
        errors['retained_target_state_binding'] += 1
    if (manifest.get('completed_cases') != 1 or manifest.get('successful_cases') != int(case.get('status')=='complete')
            or manifest.get('resource_limited_cases') != int(case.get('status')=='resource_limit')
            or manifest.get('total_state_records') != len(states)):
        errors['new_case_counts'] += 1
    zero_fields = ('new_graphs', 'new_environment_samples', 'new_environment_calls', 'new_RL_updates', 'new_MCTS_calls')
    if any(manifest.get(name) != 0 for name in zero_fields) or manifest.get('new_full_policy_evaluations') != 1:
        errors['new_work_scope'] += 1
    cost_fields = ('source_read_seconds', 'graph_reconstruction_seconds', 'data_output_seconds', 'whole_runner_seconds',
                   'runner_cpu_seconds', 'process_peak_rss_bytes')
    if any(not v52.finite(manifest.get(name)) or manifest[name] < 0 for name in cost_fields):
        errors['manifest_costs'] += 1
    checked = dict(passed=False, errors={'unbound_graph':1}, quality_verified=False)
    if graph:
        if any(case.get(name) != graph.get(name) for name in ('graph_id', 'nodes', 'stratum', 'p')) or case.get('budget') != 2 or case.get('horizon') != 3:
            errors['case_graph_binding'] += 1
        checked = verify_case(case, states, graph['edges'], graph['nodes'])
        errors.update(checked['errors'])
    complete = not errors and checked['quality_verified']
    return dict(schema='acfqp.lmta_changed_policy_analysis.v60', protocol=PROTOCOL,
        integrity=dict(passed=not errors, errors=dict(errors), case_validation=checked),
        complete_unified_policy_evidence=complete, target_action_preservation_claim=False,
        target_policy_comparison=policy_change(case, states, target_old, source58_target_rows) if complete else None,
        unified_three_depth_strata=unified_strata(case, source58_cases, source59_cases, certificates) if complete else None,
        new_case=case, preserved_reuse_count=127 if source_127 else None,
        accounting=dict(new_case=costs(case), **{name:manifest.get(name) for name in (*cost_fields, 'data_bytes', *zero_fields, 'new_full_policy_evaluations')},
            retained_V58=source58_analysis.get('accounting'), retained_V59=source59_analysis.get('accounting'),
            analysis_independent_query_checks=checked.get('planned_roots',0)+checked.get('forced_roots',0),
            analysis_full_policy_equations=checked.get('full_policy_equations',0),
            analysis_wall_seconds_before_serialization=perf_counter()-started,
            scope='Only the target policy is freshly evaluated. All prior costs are retained, not recharged or refunded. '
                  'GC and serialization views overlap; source histories are not additive new costs.'),
        scope='The target may have a different valid policy value. Its actual new reachable states and occupancy are evaluated. '
              'The other 127 short policies and all FULL results are reused with explicit provenance. V59 failure flags remain unchanged. '
              'No same-policy claim, paired-time speedup, or adoption Gate is created.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'reports/lmta_changed_policy_v60')
    parser.add_argument('--policies-dir', type=Path, default=ROOT/SOURCE_DIRS['policies'])
    parser.add_argument('--replay-dir', type=Path, default=ROOT/SOURCE_DIRS['replay'])
    args = parser.parse_args()
    started = perf_counter()
    def document(directory, filename):
        return json.loads((directory/filename).read_text())
    def rows(directory, filename, target_only=False):
        result = []
        with (directory/filename).open() as handle:
            for line in handle:
                row = json.loads(line)
                if target_only and row['graph_id'] > GRAPH:
                    break
                if not target_only or (row.get('graph_id'),row.get('method')) == (GRAPH,SOURCE_METHOD):
                    result.append(row)
        return result
    result = summarize(document(args.output_dir,'manifest.json'), document(args.output_dir,'case.json'),
        rows(args.output_dir,'states.jsonl'), document(args.policies_dir,'manifest.json'), document(args.policies_dir,'analysis.json'),
        rows(args.policies_dir,'cases.jsonl'), rows(args.policies_dir,'states.jsonl',True),
        document(args.replay_dir,'analysis.json'), rows(args.replay_dir,'cases.jsonl'))
    result['accounting']['analysis_wall_seconds_including_reads'] = perf_counter()-started
    (args.output_dir/'analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(integrity=result['integrity']['passed'], complete_unified_policy_evidence=result['complete_unified_policy_evidence'])))


if __name__ == '__main__':
    main()
