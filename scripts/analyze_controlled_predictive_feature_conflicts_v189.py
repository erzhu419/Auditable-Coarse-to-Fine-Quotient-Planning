"""Independent alias regret, observed feature coverage and TARGET certificates."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from itertools import combinations
import json
import math
from pathlib import Path
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT/'src'))
from scripts import analyze_controlled_predictive_shared_feature_capacity_v181 as capacity_audit

old = capacity_audit.previous
ACTIONS, EPS, rational = old.ACTIONS, old.EPS, old.rational
SCHEMA = 'acfqp.feature_conflicts.v189'
OUTPUT = PROJECT/'reports/controlled_predictive_feature_conflicts_v189'


def same(actual, expected):
    return old._equal(actual, expected) and old._equal(expected, actual)


def mean_vectors(vectors):
    return [math.fsum(vector[k] for vector in vectors)/len(vectors) for k in range(3)]


def optimal_actions(actions, vectors):
    values = {action: old.utility(vectors[action]) for action in actions}; maximum = max(values.values())
    return [action for action in ACTIONS if action in values and values[action] >= maximum-EPS], maximum


def optimum(actions, vectors, work):
    actions, maximum = optimal_actions(actions, vectors)
    return dict(actions=actions, reference_action=actions[0], utility=maximum,
                components_by_action={action: list(vectors[action]) for action in actions})


def features_from_root(root, work, prefix):
    legal = [action for action in ACTIONS if action in root['legal_actions']]
    features = {action: tuple(root['action_features'][action]) for action in legal}
    work[prefix+'_feature_values_read'] += 6*len(legal); work[prefix+'_legal_actions'] += len(legal)
    return legal, features


def coverage(source, target, alias, work):
    tuples, structures, thresholds = {}, {}, {}
    def add(index, key, root):
        root_ids, group_ids = index.setdefault(key, (set(), set()))
        root_ids.add(root['root_id']); group_ids.add(root['source_id'])
    def support(index, key):
        root_ids, group_ids = index.get(key, (set(), set()))
        return len(root_ids), len(group_ids)
    for root in source:
        legal, features = features_from_root(root, work, 'coverage_source'); rewards = {action: rational(root['immediate_rewards'][action]) for action in legal}
        for action in legal:
            add(tuples, features[action], root)
        for first in legal:
            for second in legal:
                if first == second:
                    continue
                key = (features[first], features[second]); gap = str(rewards[first]-rewards[second])
                add(structures, key, root); add(thresholds, (*key, gap), root)
                work.update(coverage_source_ordered_pairs=1, coverage_source_reward_difference_subtractions=1)
        work.update(coverage_source_roots=1, coverage_source_reward_fraction_conversions=len(legal))
    by_id = {row['root_id']: row for row in alias}; records = []
    for root in target:
        legal, features = features_from_root(root, work, 'coverage_target'); rewards = {action: rational(root['immediate_rewards'][action]) for action in legal}
        feature_rows, comparisons = [], []
        for action in legal:
            roots, groups = support(tuples, features[action])
            feature_rows.append(dict(action=action, features=list(features[action]), seen=roots > 0, source_root_count=roots, source_group_count=groups))
            work['coverage_target_tuple_lookups'] += 1
        for first in legal:
            for second in legal:
                if first == second:
                    continue
                key = (features[first], features[second]); gap = str(rewards[first]-rewards[second])
                roots, groups = support(structures, key); threshold_roots, threshold_groups = support(thresholds, (*key, gap))
                comparisons.append(dict(first_action=first, second_action=second, first_features=list(features[first]), second_features=list(features[second]),
                    reward_difference_fraction=gap, structure_seen=roots > 0, reward_threshold_seen=threshold_roots > 0,
                    source_root_count=roots, source_group_count=groups, reward_threshold_source_root_count=threshold_roots, reward_threshold_source_group_count=threshold_groups))
                work.update(coverage_target_ordered_pairs=1, coverage_target_structure_lookups=1, coverage_target_reward_threshold_lookups=1, coverage_target_reward_difference_subtractions=1)
        pairs = {(row['first_action'], row['second_action']): row for row in comparisons}; item = by_id[root['root_id']]; changed = []
        for action in item['alias']['actions']:
            linear = item['linear']['action']
            if action == linear:
                changed.append(dict(first_action=action, second_action=linear, same_action=True, requires_change=False, structure_seen=None, reward_threshold_seen=None))
            else:
                changed.append(dict(pairs[action, linear], same_action=False, requires_change=True))
            work['coverage_alias_optimal_linear_records'] += 1
        records.append(dict(root_id=root['root_id'], tuples=feature_rows, ordered_contrasts=comparisons,
            all_tuples_seen=all(row['seen'] for row in feature_rows), all_contrast_structures_seen=all(row['structure_seen'] for row in comparisons),
            all_reward_thresholds_seen=all(row['reward_threshold_seen'] for row in comparisons), alias_optimal_vs_linear=changed))
        work.update(coverage_target_roots=1, coverage_target_reward_fraction_conversions=len(legal))
    return dict(source_roots=len(source), source_groups=len({row['source_id'] for row in source}), distinct_tuples=len(tuples),
        distinct_contrast_structures=len(structures), distinct_reward_thresholds=len(thresholds), pair_definition='ALL_ORDERED_DISTINCT_LEGAL_ACTIONS',
        threshold_definition='EXACT_FIRST_REWARD_DIFFERENCE', root_records=records)


def build_diagnostics(roots, labels, summary):
    target = roots['TARGET']; indexed_labels = {row['root_id']: row for row in labels}
    actions = {row['root_id']: row['models']['LINEAR']['action'] for row in summary['root_records']}
    original_problem = old.build_problem(target, labels); problem = capacity_audit.lift_problem(original_problem)
    work = Counter(original_problem['work'])+Counter(problem['work'])
    work.update(diagnostic_label_root_bindings=len(labels), diagnostic_summary_root_bindings=len(actions))
    indexed_problem = {row['root_id']: row for row in problem['roots']}; rows = []
    for root in sorted(target, key=lambda row: row['root_id']):
        legal = [action for action in ACTIONS if action in root['legal_actions']]; vectors = indexed_labels[root['root_id']]['action_components']
        representatives = [row['representative'] for row in indexed_problem[root['root_id']]['classes']]
        oracle = optimum(legal, vectors, work); alias = optimum(representatives, vectors, work)
        action = actions[root['root_id']]; vector = list(vectors[action]); value = old.utility(vector)
        regret = oracle['utility']-value; within = oracle['utility']-alias['utility']; remaining = alias['utility']-value
        rows.append(dict(root_id=root['root_id'], oracle=oracle, alias=alias, linear=dict(action=action, components=vector, utility=value, regret=regret),
            within_root_regret=within, remaining_regret=remaining, linear_error=regret > EPS, alias_loss=within > EPS, linear_is_class_representative=action in representatives))
        work.update(alias_action_utility_evaluations=len(legal)+len(representatives), alias_root_records=1, alias_original_terminal_component_reads=3*len(legal),
                    alias_linear_component_reads=3, alias_regret_subtractions=3, alias_linear_utility_evaluations=1)
    observed = coverage(roots['SOURCE'], target, rows, work)
    return dict(schema=SCHEMA+'.diagnostics', problem=problem, alias=dict(root_records=rows), coverage=observed, costs=dict(work))


def dual_explanations(problem, capacity, work):
    roots = {root['root_id']: {row['representative']: row for row in root['classes']} for root in problem['roots']}
    vertices = {row['vertex_id']: row['features'] for row in problem['vertices']}; records = []
    for node in capacity['nodes']:
        if node['disposition'] not in ('pruned_negative', 'pruned_zero'):
            continue
        flow, edges, cap_support = Counter(), [], []; total_weight, bound = Fraction(), Fraction()
        for atom in node['dual']['support']:
            constraint = node['constraints'][atom['constraint_index']]; weight, reward = rational(atom['weight']), rational(constraint['b'])
            total_weight += weight; bound += weight*reward
            work.update(explanation_constraint_records_read=1, explanation_exact_weight_conversions=1, explanation_reward_fraction_conversions=1, explanation_weighted_reward_products=1)
            if constraint['kind'] == 'margin_cap':
                cap_support.append(dict(constraint_index=atom['constraint_index'], weight=str(weight), b=str(reward))); continue
            best, bad = roots[constraint['root_id']][constraint['best_action']], roots[constraint['root_id']][constraint['bad_action']]
            flow[bad['vertex_id']] += weight; flow[best['vertex_id']] -= weight
            def details(row):
                return dict(action=row['representative'], vertex_id=row['vertex_id'], features=list(row['features']),
                            immediate_reward_fraction=row['immediate_reward_fraction'], components=list(row['components']), utility=row['utility'])
            edges.append(dict(constraint_index=atom['constraint_index'], root_id=constraint['root_id'], weight=str(weight), best=details(best), bad=details(bad),
                              reward_difference_fraction=str(reward), weighted_reward_difference_fraction=str(weight*reward)))
            work.update(explanation_vertex_flow_accumulations=2, explanation_feature_values_copied=12, explanation_terminal_component_reads=6)
        records.append(dict(node_id=node['node_id'], disposition=node['disposition'], assigned=list(node['assigned']), upper_bound=node['dual']['upper_bound'],
            weighted_reward_difference_sum=str(bound), margin_weight_sum=str(total_weight), margin_cap_support=cap_support, edges=edges,
            vertex_flows=[dict(vertex_id=vertex, features=list(vertices[vertex]), net_flow=str(flow[vertex])) for vertex in sorted(flow)],
            balanced_vertex_flow=not any(flow.values())))
        work.update(explanation_dual_nodes=1, explanation_vertex_balances_read=len(flow))
    return records


def summarize(diagnostics, capacity):
    work = Counter(); rows = diagnostics['alias']['root_records']; n = len(rows)
    indexed_coverage = {row['root_id']: row for row in diagnostics['coverage']['root_records']}
    def aggregate(name):
        vectors = [row[name]['components'] if name == 'linear' else row[name]['components_by_action'][row[name]['reference_action']] for row in rows]
        return dict(reference_components=mean_vectors(vectors), utility=math.fsum(row[name]['utility'] for row in rows)/n)
    errors = [row for row in rows if row['linear_error']]; loss = [row for row in rows if row['alias_loss']]
    alias = dict(oracle=aggregate('oracle'), alias=aggregate('alias'), linear=aggregate('linear'), linear_error_roots=len(errors), within_root_loss_roots=len(loss),
        linear_errors_affected_by_alias=sum(row['alias_loss'] for row in errors), within_root_regret_mean=math.fsum(row['within_root_regret'] for row in rows)/n,
        remaining_regret_mean=math.fsum(row['remaining_regret'] for row in rows)/n, linear_regret_mean=math.fsum(row['linear']['regret'] for row in rows)/n,
        within_root_loss_root_ids=[row['root_id'] for row in loss], linear_error_root_ids=[row['root_id'] for row in errors])
    def observed(selected):
        return dict(roots=len(selected), all_tuples_seen=sum(indexed_coverage[row['root_id']]['all_tuples_seen'] for row in selected),
            all_contrast_structures_seen=sum(indexed_coverage[row['root_id']]['all_contrast_structures_seen'] for row in selected),
            all_reward_thresholds_seen=sum(indexed_coverage[row['root_id']]['all_reward_thresholds_seen'] for row in selected))
    work.update(summary_alias_root_records=n, summary_reference_component_reads=9*n, summary_regret_scalar_reads=3*n, summary_coverage_flags_read=3*(n+len(errors)))
    weak = capacity.get('weak_witness'); tie_attained = weak is not None and weak['evaluation']['all_optimal']; status = capacity['status']
    interpretation = {'strict_feasible': 'strict_alias_optimal_witness_on_retained_TARGET', 'weak_infeasible': 'incompatible_alias_rankings_on_retained_TARGET',
                      'no_positive_margin': 'no_positive_margin_actual_tie_policy_not_settled'}[status]
    if status == 'no_positive_margin' and tie_attained:
        interpretation = 'no_positive_margin_actual_tie_policy_attained'
    result = dict(schema=SCHEMA+'.summary', complete=status in ('strict_feasible', 'weak_infeasible', 'no_positive_margin'), roots=n, alias=alias,
        coverage=dict(source_roots=diagnostics['coverage']['source_roots'], source_groups=diagnostics['coverage']['source_groups'], all_roots=observed(rows), linear_errors=observed(errors)),
        capacity=dict(status=status, upper_bound=capacity['upper_bound'], vertices=len(diagnostics['problem']['vertices']), solver_nodes=len(capacity['nodes']),
            lp_solves=capacity['costs'].get('lp_solves', 0), interpretation=interpretation,
            actual_tie_policy_attainability='attained_by_retained_weak_witness' if tie_attained else 'unknown',
            weak_witness_all_optimal=None if weak is None else weak['evaluation']['all_optimal']),
        dual_explanations=dual_explanations(diagnostics['problem'], capacity, work), new_environment_samples=0, new_fits=0, new_labels=0)
    result['work'] = dict(work)
    return result


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, io = [], Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); io.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = ('stage_checks.json', 'run.json', 'roots.json', 'labels.json', 'summary.json')
    expected_inputs = [(f'inputs/inherited/{name}', 'protocol_frozen') for name in names]
    check('five_protocol_frozen_retained_inputs', [(row['saved_ref'], row['phase']) for row in inputs] == expected_inputs)
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        io.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    stage, inherited_run = read('inputs/inherited/stage_checks.json'), read('inputs/inherited/run.json')
    check('settled_V188_complete', stage['valid'] and inherited_run['status'] == 'complete')
    roots, labels, retained_summary = read('inputs/inherited/roots.json'), read('inputs/inherited/labels.json'), read('inputs/inherited/summary.json')
    check('fixed_SOURCE143_36_groups_and_TARGET96', len(roots['SOURCE']) == 143 and len({row['source_id'] for row in roots['SOURCE']}) == 36 and len(roots['TARGET']) == len(labels) == 96)
    diagnostics = build_diagnostics(roots, labels, retained_summary)
    check('independent_alias_regret_directed_coverage_and_TARGET_problem', same(read('diagnostics.json'), diagnostics))
    check('all_paid_diagnostics_work', run['costs']['diagnostics']['counts'] == diagnostics['costs'])
    capacity = read('capacity.json'); certificate_checks, certificate_work = capacity_audit.verify_capacity(diagnostics['problem'], capacity)
    for row in certificate_checks:
        check('TARGET:'+row['name'], row['passed'])
    check('one_retained_TARGET_capacity_cost', run['costs']['target_capacity']['counts'] == capacity['costs'] and run['new_lp_solves'] == capacity['costs']['lp_solves'])
    expected = summarize(diagnostics, capacity)
    check('alias_coverage_and_verified_capacity_claim_summary', same(read('summary.json'), expected))
    check('paid_summary_and_exact_dual_explanation_work', run['costs']['summary']['counts'] == expected['work'])
    phases = [('protocol_frozen', 0), ('retained_inputs', 5), ('diagnostics_frozen', 5), ('target_capacity', 5), ('complete', 5)]
    check('retained_inputs_and_TARGET_only_capacity_freeze', [(row['phase'], row['input_reads']) for row in run['phase_history']] == phases)
    input_counts = dict(json_read_operations=5, input_bytes_read=sum(row['bytes'] for row in inputs), input_bytes_retained=sum(row['bytes'] for row in inputs))
    check('all_paid_retained_input_counts', run['costs']['input_counts'] == input_counts)
    zero = ('new_predictors_fitted', 'new_environment_samples', 'new_source_games', 'new_native_weight_updates', 'new_reference_kernels', 'new_exact_label_roots')
    check('one_new_capacity_scope_no_fits_labels_or_samples', all(run[key] == 0 for key in zero) and run['new_capacity_attempts'] == run['new_capacity_scopes'] == 1)
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and expected['complete']
    return dict(schema=SCHEMA+'.analysis', valid=valid, complete=complete, primary_complete=complete, checks=checks,
        passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=expected,
        costs=dict(new_environment_samples=0, physical_branches_replayed=0, old_kernels_reevaluated=0, old_models_refitted=0,
            features_recomputed=0, independent_lp_solves=0, independent_input_counts=dict(io), independent_certificate_counts=certificate_work,
            independent_diagnostics_counts=diagnostics['costs'], independent_summary_counts=expected['work'], original_run_costs=run['costs'],
            inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'], new_environment_samples=0)))


if __name__ == '__main__':
    main()
