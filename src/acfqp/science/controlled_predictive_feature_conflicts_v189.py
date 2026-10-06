"""Retained-board alias loss, SOURCE coverage and shared-feature conflicts.

The capacity target is the best attainable within-root representative, not an
oracle action discarded by the fixed first-reward/ACTIONS alias rule.
"""
from collections import Counter
from fractions import Fraction
from itertools import permutations
from math import fsum

from . import controlled_predictive_ranking_capacity_v180 as ranking
from . import controlled_predictive_shared_feature_capacity_v181 as capacity_backend

SCHEMA = 'acfqp.feature_conflicts.v189'
ACTIONS, EPSILON = ranking.ACTIONS, ranking.EPSILON
solve_capacity = capacity_backend.solve_capacity
evaluate_potentials = capacity_backend.evaluate_potentials
CapacityExecutionError = capacity_backend.CapacityExecutionError


def _utility(vector):
    return vector[0]-vector[1]+vector[2]


def _optimum(actions, components, work):
    utilities = {a: _utility(components[a]) for a in actions}
    best = max(utilities.values())
    optimal = [a for a in ACTIONS if a in utilities and utilities[a] >= best-EPSILON]
    work['alias_action_utility_evaluations'] += len(actions)
    return dict(actions=optimal, reference_action=optimal[0], utility=best,
                components_by_action={a: list(components[a]) for a in optimal})


def _features(root, work, prefix):
    legal = [a for a in ACTIONS if a in root['legal_actions']]
    result = {a: tuple(root['action_features'][a]) for a in legal}
    work[prefix+'_feature_values_read'] += 6*len(legal)
    work[prefix+'_legal_actions'] += len(legal)
    return legal, result


def _coverage(source, target, alias, work):
    tuples, contrasts, thresholds = {}, {}, {}
    def record(index, key, root):
        roots, groups = index.setdefault(key, (set(), set()))
        roots.add(root['root_id']); groups.add(root['source_id'])
    for root in source:
        legal, features = _features(root, work, 'coverage_source')
        rewards = {a: Fraction(root['immediate_rewards'][a]) for a in legal}
        for action in legal:
            record(tuples, features[action], root)
        for first, second in permutations(legal, 2):
            key = (features[first], features[second])
            threshold = str(rewards[first]-rewards[second])
            record(contrasts, key, root); record(thresholds, (*key, threshold), root)
            work.update(coverage_source_ordered_pairs=1, coverage_source_reward_difference_subtractions=1)
        work.update(coverage_source_roots=1, coverage_source_reward_fraction_conversions=len(legal))

    def counts(index, key):
        roots, groups = index.get(key, (set(), set()))
        return len(roots), len(groups)

    rows = []
    alias_index = {row['root_id']: row for row in alias}
    for root in target:
        legal, features = _features(root, work, 'coverage_target')
        rewards = {a: Fraction(root['immediate_rewards'][a]) for a in legal}
        feature_rows = []
        for action in legal:
            roots, groups = counts(tuples, features[action])
            feature_rows.append(dict(action=action, features=list(features[action]), seen=roots > 0,
                                     source_root_count=roots, source_group_count=groups))
            work['coverage_target_tuple_lookups'] += 1
        comparisons = []
        for first, second in permutations(legal, 2):
            key = (features[first], features[second])
            threshold = str(rewards[first]-rewards[second])
            roots, groups = counts(contrasts, key)
            threshold_roots, threshold_groups = counts(thresholds, (*key, threshold))
            comparisons.append(dict(first_action=first, second_action=second, first_features=list(features[first]),
                second_features=list(features[second]), reward_difference_fraction=threshold,
                structure_seen=roots > 0, reward_threshold_seen=threshold_roots > 0,
                source_root_count=roots, source_group_count=groups,
                reward_threshold_source_root_count=threshold_roots, reward_threshold_source_group_count=threshold_groups))
            work.update(coverage_target_ordered_pairs=1, coverage_target_structure_lookups=1,
                        coverage_target_reward_threshold_lookups=1, coverage_target_reward_difference_subtractions=1)
        paired = {(row['first_action'], row['second_action']): row for row in comparisons}
        item = alias_index[root['root_id']]
        optimal_vs_linear = []
        for action in item['alias']['actions']:
            linear = item['linear']['action']
            if action == linear:
                optimal_vs_linear.append(dict(first_action=action, second_action=linear, same_action=True,
                    requires_change=False, structure_seen=None, reward_threshold_seen=None))
            else:
                optimal_vs_linear.append(dict(paired[action, linear], same_action=False, requires_change=True))
            work['coverage_alias_optimal_linear_records'] += 1
        rows.append(dict(root_id=root['root_id'], tuples=feature_rows, ordered_contrasts=comparisons,
            all_tuples_seen=all(row['seen'] for row in feature_rows),
            all_contrast_structures_seen=all(row['structure_seen'] for row in comparisons),
            all_reward_thresholds_seen=all(row['reward_threshold_seen'] for row in comparisons),
            alias_optimal_vs_linear=optimal_vs_linear))
        work.update(coverage_target_roots=1, coverage_target_reward_fraction_conversions=len(legal))
    return dict(source_roots=len(source), source_groups=len({row['source_id'] for row in source}),
        distinct_tuples=len(tuples), distinct_contrast_structures=len(contrasts), distinct_reward_thresholds=len(thresholds),
        pair_definition='ALL_ORDERED_DISTINCT_LEGAL_ACTIONS', threshold_definition='EXACT_FIRST_REWARD_DIFFERENCE',
        root_records=rows)


def build_diagnostics(roots, labels, summary):
    """Reconstruct the frozen TARGET problem; SOURCE is used only for coverage."""
    target, source = roots['TARGET'], roots['SOURCE']
    target_ids = [row['root_id'] for row in target]
    label_index = {row['root_id']: row for row in labels}
    chosen = {row['root_id']: row['models']['LINEAR']['action'] for row in summary['root_records']}
    if (len(set(target_ids)) != len(target_ids) or len(label_index) != len(labels)
            or len(chosen) != len(summary['root_records']) or set(target_ids) != set(label_index) or set(target_ids) != set(chosen)):
        raise ValueError('frozen TARGET roots, labels and LINEAR decisions must bind once each')
    problem = ranking.build_problem(target, labels)
    lifted = capacity_backend.lift_problem(problem)
    work = Counter(problem['work'])+Counter(lifted['work'])
    work.update(diagnostic_label_root_bindings=len(labels), diagnostic_summary_root_bindings=len(chosen))
    problem_index = {row['root_id']: row for row in lifted['roots']}
    rows = []
    for root in sorted(target, key=lambda row: row['root_id']):
        legal = [a for a in ACTIONS if a in root['legal_actions']]
        components = label_index[root['root_id']]['action_components']
        linear_action = chosen[root['root_id']]
        if linear_action not in legal:
            raise ValueError('retained LINEAR action is not legal at its bound root')
        classes = problem_index[root['root_id']]['classes']
        representatives = [row['representative'] for row in classes]
        oracle = _optimum(legal, components, work)
        alias = _optimum(representatives, components, work)
        linear_components = list(components[linear_action])
        linear_utility = _utility(linear_components)
        regret = oracle['utility']-linear_utility
        within, remaining = oracle['utility']-alias['utility'], alias['utility']-linear_utility
        rows.append(dict(root_id=root['root_id'], oracle=oracle, alias=alias,
            linear=dict(action=linear_action, components=linear_components, utility=linear_utility, regret=regret),
            within_root_regret=within, remaining_regret=remaining, linear_error=regret > EPSILON,
            alias_loss=within > EPSILON, linear_is_class_representative=linear_action in representatives))
        work.update(alias_root_records=1, alias_original_terminal_component_reads=3*len(legal),
                    alias_linear_component_reads=3, alias_regret_subtractions=3, alias_linear_utility_evaluations=1)
    coverage = _coverage(source, target, rows, work)
    return dict(schema=SCHEMA+'.diagnostics', problem=lifted, alias=dict(root_records=rows),
                coverage=coverage, costs=dict(work))


def _dual_explanations(problem, capacity, work):
    indexed = {row['root_id']: {item['representative']: item for item in row['classes']} for row in problem['roots']}
    vertices = {row['vertex_id']: row['features'] for row in problem['vertices']}
    explanations = []
    for node in capacity['nodes']:
        if node['disposition'] not in ('pruned_negative', 'pruned_zero'):
            continue
        flow, edges, cap_support = Counter(), [], []
        delta, rhs = Fraction(0), Fraction(0)
        for entry in node['dual']['support']:
            constraint = node['constraints'][entry['constraint_index']]
            weight, reward = Fraction(entry['weight']), Fraction(constraint['b'])
            delta += weight; rhs += weight*reward
            work.update(explanation_constraint_records_read=1, explanation_exact_weight_conversions=1,
                        explanation_reward_fraction_conversions=1, explanation_weighted_reward_products=1)
            if constraint['kind'] == 'margin_cap':
                cap_support.append(dict(constraint_index=entry['constraint_index'], weight=str(weight), b=str(reward)))
                continue
            good = indexed[constraint['root_id']][constraint['best_action']]
            bad = indexed[constraint['root_id']][constraint['bad_action']]
            flow[bad['vertex_id']] += weight; flow[good['vertex_id']] -= weight
            def details(row):
                return dict(action=row['representative'], vertex_id=row['vertex_id'], features=list(row['features']),
                    immediate_reward_fraction=row['immediate_reward_fraction'], components=list(row['components']), utility=row['utility'])
            edges.append(dict(constraint_index=entry['constraint_index'], root_id=constraint['root_id'], weight=str(weight),
                best=details(good), bad=details(bad), reward_difference_fraction=str(reward),
                weighted_reward_difference_fraction=str(weight*reward)))
            work.update(explanation_vertex_flow_accumulations=2, explanation_feature_values_copied=12,
                        explanation_terminal_component_reads=6)
        explanations.append(dict(node_id=node['node_id'], disposition=node['disposition'], assigned=list(node['assigned']),
            upper_bound=node['dual']['upper_bound'], weighted_reward_difference_sum=str(rhs),
            margin_weight_sum=str(delta), margin_cap_support=cap_support, edges=edges,
            vertex_flows=[dict(vertex_id=vertex, features=list(vertices[vertex]), net_flow=str(flow[vertex])) for vertex in sorted(flow)],
            balanced_vertex_flow=all(value == 0 for value in flow.values())))
        work.update(explanation_dual_nodes=1, explanation_vertex_balances_read=len(flow))
    return explanations


def summarize(diagnostics, capacity):
    """Report separate alias loss, remaining errors and exact local certificates."""
    work = Counter()
    rows = diagnostics['alias']['root_records']
    n = len(rows)
    coverage = {row['root_id']: row for row in diagnostics['coverage']['root_records']}
    def aggregate(which):
        vectors = [row[which]['components'] if which == 'linear' else
                   row[which]['components_by_action'][row[which]['reference_action']] for row in rows]
        return dict(reference_components=[fsum(vector[i] for vector in vectors)/n for i in range(3)],
                    utility=fsum(row[which]['utility'] for row in rows)/n)
    errors = [row for row in rows if row['linear_error']]
    loss = [row for row in rows if row['alias_loss']]
    alias = dict(oracle=aggregate('oracle'), alias=aggregate('alias'), linear=aggregate('linear'),
        linear_error_roots=len(errors), within_root_loss_roots=len(loss),
        linear_errors_affected_by_alias=sum(row['alias_loss'] for row in errors),
        within_root_regret_mean=fsum(row['within_root_regret'] for row in rows)/n,
        remaining_regret_mean=fsum(row['remaining_regret'] for row in rows)/n,
        linear_regret_mean=fsum(row['linear']['regret'] for row in rows)/n,
        within_root_loss_root_ids=[row['root_id'] for row in loss],
        linear_error_root_ids=[row['root_id'] for row in errors])
    def covered(selected):
        return dict(roots=len(selected), all_tuples_seen=sum(coverage[row['root_id']]['all_tuples_seen'] for row in selected),
            all_contrast_structures_seen=sum(coverage[row['root_id']]['all_contrast_structures_seen'] for row in selected),
            all_reward_thresholds_seen=sum(coverage[row['root_id']]['all_reward_thresholds_seen'] for row in selected))
    work.update(summary_alias_root_records=n, summary_reference_component_reads=9*n,
                summary_regret_scalar_reads=3*n, summary_coverage_flags_read=3*(n+len(errors)))
    weak = capacity.get('weak_witness')
    weak_actual = weak is not None and weak['evaluation']['all_optimal']
    tie_attainability = ('attained_by_retained_weak_witness' if weak_actual else 'unknown')
    status = capacity['status']
    if status == 'strict_feasible':
        interpretation = 'strict_alias_optimal_witness_on_retained_TARGET'
    elif status == 'weak_infeasible':
        interpretation = 'incompatible_alias_rankings_on_retained_TARGET'
    else:
        interpretation = ('no_positive_margin_actual_tie_policy_attained' if weak_actual else
                          'no_positive_margin_actual_tie_policy_not_settled')
    result = dict(schema=SCHEMA+'.summary', complete=status in ('strict_feasible', 'weak_infeasible', 'no_positive_margin'),
        roots=n, alias=alias, coverage=dict(source_roots=diagnostics['coverage']['source_roots'],
            source_groups=diagnostics['coverage']['source_groups'], all_roots=covered(rows), linear_errors=covered(errors)),
        capacity=dict(status=status, upper_bound=capacity['upper_bound'], vertices=len(diagnostics['problem']['vertices']),
            solver_nodes=len(capacity['nodes']), lp_solves=capacity['costs'].get('lp_solves', 0), interpretation=interpretation,
            actual_tie_policy_attainability=tie_attainability,
            weak_witness_all_optimal=None if weak is None else weak['evaluation']['all_optimal']),
        dual_explanations=_dual_explanations(diagnostics['problem'], capacity, work),
        new_environment_samples=0, new_fits=0, new_labels=0)
    result['work'] = dict(work)
    return result
