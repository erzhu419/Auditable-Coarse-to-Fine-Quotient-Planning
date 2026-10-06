"""Independent rational certificates for fixed shared linear action rankings."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT/'reports/controlled_predictive_ranking_capacity_v180'
ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')
EPS = 1e-12


def _equal(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(key in actual and _equal(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(_equal(a, b) for a, b in zip(actual, expected))
    if isinstance(expected, float):
        return isinstance(actual, (float, int)) and math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10)
    return actual == expected


def rational(value):
    return value if isinstance(value, Fraction) else Fraction(value)


def utility(vector):
    return vector[0]-vector[1]+vector[2]


def build_problem(roots, labels):
    by_id = {row['root_id']: row['action_components'] for row in labels}; result, work = [], Counter()
    for root in sorted(roots, key=lambda row: row['root_id']):
        groups = {}
        for action in ACTIONS:
            if action not in root['legal_actions']:
                continue
            groups.setdefault(tuple(root['action_features'][action]), []).append(action)
            work.update(problem_feature_values_read=6, problem_action_alias_classifications=1)
        classes = []
        for features, actions in groups.items():
            representative = actions[0]
            for action in actions[1:]:
                if root['immediate_rewards'][action] > root['immediate_rewards'][representative]+EPS:
                    representative = action
                work.update(problem_alias_reward_comparisons=1, problem_immediate_rewards_read=2)
            vector = list(by_id[root['root_id']][representative])
            reward = root['immediate_rewards'][representative]
            classes.append(dict(class_id=len(classes), features=list(features), actions=actions,
                representative=representative, immediate_reward=reward,
                immediate_reward_fraction=str(rational(reward)),
                components=vector, utility=utility(vector)))
            work.update(problem_terminal_components_read=3, problem_immediate_rewards_read=1)
        maximum = max(row['utility'] for row in classes)
        optimal = [action for action in ACTIONS if any(row['representative'] == action and row['utility'] >= maximum-EPS for row in classes)]
        others = [action for action in ACTIONS if any(row['representative'] == action for row in classes) and action not in optimal]
        result.append(dict(root_id=root['root_id'], cohort=root['cohort'], life=root['life'], source_id=root['source_id'],
                           classes=classes, optimal_actions=optimal, suboptimal_actions=others, best_utility=maximum))
        work.update(problem_root_records=1, problem_representative_utility_evaluations=len(classes))
    if not result or len({row['root_id'] for row in result}) != len(result):
        raise ValueError('capacity scope requires distinct retained roots')
    return dict(schema='acfqp.ranking_capacity.v180.problem', roots=result, epsilon=EPS, work=dict(work))


def evaluate_beta(problem, beta):
    beta = list(map(rational, beta)); records, gaps = [], []
    for root in problem['roots']:
        classes = {row['representative']: row for row in root['classes']}
        scores = {action: rational(row['immediate_reward_fraction'])+
                  sum((rational(value)*coefficient for value, coefficient in zip(row['features'], beta)), Fraction())
                  for action, row in classes.items()}
        chosen = next(action for action in ACTIONS if action in scores)
        for action in ACTIONS:
            if action in scores and scores[action] > scores[chosen]+rational(EPS):
                chosen = action
        good = max(scores[action] for action in root['optimal_actions'])
        bad = max((scores[action] for action in root['suboptimal_actions']), default=None)
        gap = None if bad is None else good-bad
        if gap is not None:
            gaps.append(gap)
        row = classes[chosen]
        records.append(dict(root_id=root['root_id'], chosen=chosen, chosen_optimal=chosen in root['optimal_actions'],
            action_scores={action: str(value) for action, value in scores.items()}, optimal_score=str(good),
            suboptimal_score=None if bad is None else str(bad), optimal_vs_bad_gap=None if gap is None else str(gap),
            chosen_components=list(row['components']), chosen_utility=row['utility'], regret=root['best_utility']-row['utility']))
    return dict(beta=list(map(str, beta)), root_records=records, minimum_gap=None if not gaps else str(min(gaps)),
                all_optimal=all(row['chosen_optimal'] for row in records), all_weak=all(gap >= 0 for gap in gaps))


def constraints_for(problem, assigned):
    selected = {row['root_id']: row['best_action'] for row in assigned}; result = []
    for root in problem['roots']:
        if not root['suboptimal_actions']:
            continue
        action = selected.get(root['root_id'])
        if action is None and len(root['optimal_actions']) == 1:
            action = root['optimal_actions'][0]
        if action is None:
            continue
        classes = {row['representative']: row for row in root['classes']}; good = classes[action]
        for alternative in root['suboptimal_actions']:
            bad = classes[alternative]
            coefficients = [str(rational(b)-rational(g)) for b, g in zip(bad['features'], good['features'])]+['1']
            bound = rational(good['immediate_reward_fraction'])-rational(bad['immediate_reward_fraction'])
            result.append(dict(kind='ranking', root_id=root['root_id'], best_action=action, bad_action=alternative, a=coefficients, b=str(bound)))
    result.append(dict(kind='margin_cap', root_id=None, best_action=None, bad_action=None, a=['0']*6+['1'], b='1'))
    return result


def terminal_identities(roots, labels):
    records, work = [], Counter()
    for cohort in ('SOURCE', 'TARGET'):
        by_id = {row['root_id']: row for row in labels[cohort]}
        for root in roots[cohort]:
            for action in root['legal_actions']:
                work['cached_goal_feature_reads'] += 1
                if root['action_features'][action][0]:
                    actual = by_id[root['root_id']]['action_components'][action]
                    expected = [root['immediate_rewards'][action], 0., 1.]
                    records.append(dict(root_id=root['root_id'], cohort=cohort, action=action,
                                        components=actual, expected=expected,
                                        consistent=all(abs(a-b) <= EPS for a, b in zip(actual, expected))))
                    work.update(goal_component_reads=3, goal_identity_comparisons=3)
    return dict(consistent=all(row['consistent'] for row in records), actions=len(records), records=records, work=dict(work))


def verify_dual(constraints, dual):
    """An exact upper bound is valid without re-solving the unbounded-beta LP."""
    weights, seen = {}, set()
    for atom in dual['support']:
        index, weight = atom['constraint_index'], rational(atom['weight'])
        if index in seen or not 0 <= index < len(constraints) or weight < 0:
            return False
        seen.add(index); weights[index] = weight
    balance = [sum((weight*rational(constraints[index]['a'][j]) for index, weight in weights.items()), Fraction()) for j in range(7)]
    bound = sum((weight*rational(constraints[index]['b']) for index, weight in weights.items()), Fraction())
    return balance == [Fraction()]*6+[Fraction(1)] and bound == rational(dual['upper_bound'])


def verify_capacity(problem, capacity):
    checks, work = [], Counter()
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    nodes = capacity['nodes']; by_id = {node['node_id']: node for node in nodes}
    check('node_ids', [node['node_id'] for node in nodes] == list(range(len(nodes))))
    visited, bounds, strict_nodes, weak = [], [], [], []
    rows = {row['root_id']: row for row in problem['roots']}
    strict_result = capacity['status'] == 'strict_feasible'
    def visit(node_id, parent, assigned):
        if node_id not in by_id or node_id in visited:
            check(f'node{node_id}:unique_reachable_child', False); return False
        node = by_id[node_id]; visited.append(node_id); prefix = f'node{node_id}:'
        check(prefix+'parent_and_optimal_assignment', node['parent_id'] == parent and node['assigned'] == assigned)
        constraints = constraints_for(problem, assigned)
        check(prefix+'independent_constraints', node['constraints'] == constraints)
        check(prefix+'exact_nonnegative_dual_balance_and_bound', verify_dual(constraints, node['dual']))
        work.update(nodes_verified=1, ranking_constraints_rebuilt=len(constraints),
                    dual_support_rows_verified=len(node['dual']['support']),
                    dual_balance_scalar_products=7*len(node['dual']['support']))
        native, primal = node['native_lp'], node['primal']
        native_beta = [str(rational(value)) for value in native['beta']]
        evaluation = evaluate_beta(problem, native_beta)
        check(prefix+'native_success_and_exact_binary_primal', native['success'] and native['status'] == 0 and
              primal['beta'] == native_beta and primal['evaluation'] == evaluation)
        work.update(beta_evaluations=1, beta_root_records=len(problem['roots']), beta_rational_conversions=6)
        if evaluation['all_weak']:
            weak.append(dict(node_id=node_id, beta=native_beta, evaluation=evaluation))
        bound = rational(node['dual']['upper_bound'])
        minimum = Fraction(1) if evaluation['minimum_gap'] is None else rational(evaluation['minimum_gap'])
        expected_disposition = 'pruned_negative' if bound < 0 else 'pruned_zero' if bound == 0 else 'strict_witness' if minimum > rational(EPS) else 'branch'
        check(prefix+'disposition', node['disposition'] == expected_disposition)
        if expected_disposition != 'branch':
            check(prefix+'terminal_has_no_branches', node['branch_root_id'] is None and not node['branch_actions'] and not node['children'] and not node['unexplored_actions'])
            if bound <= 0:
                bounds.append(bound); return False
            check(prefix+'strict_whole_scope_margin_and_actual_choice', minimum > rational(EPS) and evaluation['all_optimal'])
            strict_nodes.append(dict(node_id=node_id, beta=native_beta, margin=str(min(Fraction(1), minimum)), evaluation=evaluation))
            return True
        selected = {row['root_id'] for row in assigned}
        violated = [rows[row['root_id']] for row in evaluation['root_records'] if row['optimal_vs_bad_gap'] is not None and
                    rational(row['optimal_vs_bad_gap']) <= rational(EPS) and len(rows[row['root_id']]['optimal_actions']) > 1 and row['root_id'] not in selected]
        branch = violated[0] if violated else None
        check(prefix+'first_violating_unassigned_optimal_disjunction', branch is not None and node['branch_root_id'] == branch['root_id'] and node['branch_actions'] == branch['optimal_actions'])
        if branch is None:
            return False
        actions = branch['optimal_actions']; count = len(node['children'])
        check(prefix+'all_visited_or_recorded_unexplored_alternatives', 0 < count <= len(actions) and node['unexplored_actions'] == actions[count:] and (strict_result or count == len(actions)))
        success = False
        for index, child in enumerate(node['children']):
            if index >= len(actions):
                check(prefix+'no_extra_optimal_alternative', False); break
            child_success = visit(child, node_id, assigned+[dict(root_id=branch['root_id'], best_action=actions[index])])
            check(prefix+f'child{index}:DFS_stops_only_after_verified_witness', not success and (not child_success or index == count-1))
            success = success or child_success
        check(prefix+'unexplored_only_after_verified_witness', not node['unexplored_actions'] or success)
        return success
    success = visit(0, None, []) if nodes else False
    check('all_nodes_in_DFS_order', visited == list(range(len(nodes))))
    expected_weak = weak[0] if weak else None
    check('weak_witness_is_exact_nonnegative_gap_only', capacity['weak_witness'] == expected_weak)
    if strict_nodes:
        check('strict_result_verified_witness_and_root_upper_bound', success and len(strict_nodes) == 1 and
              capacity['status'] == 'strict_feasible' and capacity['witness'] == strict_nodes[0] and
              rational(capacity['upper_bound']) == rational(nodes[0]['dual']['upper_bound']))
    else:
        expected_bound = max(bounds) if bounds else None
        expected_status = 'weak_infeasible' if expected_bound is not None and expected_bound < 0 else 'no_positive_margin'
        check('exhaustive_nonpositive_subtree_bounds', not success and bool(bounds) and
              capacity['witness'] is None and capacity['status'] == expected_status and
              rational(capacity['upper_bound']) == expected_bound and not any(node['unexplored_actions'] for node in nodes))
    costs = capacity['costs']; count = len(nodes); constraint_rows = sum(len(node['constraints']) for node in nodes)
    expected_counts = dict(lp_solves=count, lp_constraint_rows=constraint_rows, lp_matrix_cells=7*constraint_rows,
                           symbolic_balance_solves=count, beta_evaluations=count, beta_root_records=count*len(problem['roots']), beta_rational_conversions=6*count)
    check('recorded_solver_and_symbolic_work', all(costs[key] == value for key, value in expected_counts.items()) and
          costs['dual_support_rows'] >= work['dual_support_rows_verified'] and
          costs['dual_balance_scalar_products'] == 7*costs['dual_support_rows'] and costs['lp_seconds'] >= 0 and costs['symbolic_balance_seconds'] >= 0)
    return checks, dict(work)


def interpret_certificates(problems, capacities):
    scopes, work = {}, Counter()
    for name, capacity in capacities.items():
        roots = {row['root_id']: row for row in problems[name]['roots']}; nodes = []
        for node in capacity['nodes']:
            flow = {}
            for atom in node['dual']['support']:
                work['certificate_support_rows_inspected'] += 1
                constraint = node['constraints'][atom['constraint_index']]
                if constraint['kind'] == 'margin_cap':
                    continue
                classes = {row['representative']: tuple(row['features']) for row in roots[constraint['root_id']]['classes']}
                for action, sign in ((constraint['bad_action'], 1), (constraint['best_action'], -1)):
                    features = classes[action]
                    flow[features] = flow.get(features, Fraction())+sign*rational(atom['weight'])
                    work['feature_flow_additions'] += 1
            residual = [dict(features=list(features), weight=str(value)) for features, value in sorted(flow.items()) if value]
            nodes.append(dict(node_id=node['node_id'], feature_flow=residual, bounds_any_shared_feature_function=not residual))
        terminal = {node['node_id'] for node in capacity['nodes'] if node['disposition'] in ('pruned_negative', 'pruned_zero')}
        scopes[name] = dict(nodes=nodes, all_terminal_bounds_apply_to_any_shared_function=None if capacity['status'] == 'strict_feasible'
                            else all(node['bounds_any_shared_feature_function'] for node in nodes if node['node_id'] in terminal))
    return dict(scopes=scopes, work=dict(work))


def summarize(problems, capacities, fitted, terminal, inherited, interpretation):
    return dict(schema='acfqp.ranking_capacity.v180.summary', complete=True,
                scopes={name: dict(roots=len(problems[name]['roots']), capacity_status=capacities[name]['status'],
                    upper_bound=capacities[name]['upper_bound'], witness=capacities[name]['witness'],
                    weak_witness=capacities[name]['weak_witness'], costs=capacities[name]['costs'], fitted=fitted[name])
                    for name in ('SOURCE', 'TARGET', 'JOINT')},
                terminal_identities=terminal,
                certificate_interpretation=interpretation,
                inherited_V179={cohort: deepcopy(inherited['SHARED']['cohorts'][cohort]) for cohort in ('SOURCE', 'TARGET')},
                new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=0)


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, work = [], Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); work.update(json_read_operations=1, input_bytes_read=len(raw))
        return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = ['stage_checks.json', 'run.json', 'roots.json', 'labels.json', 'models.json', 'summary.json']
    check('fixed_six_inherited_inputs', [(row['saved_ref'], row['phase']) for row in inputs] ==
          [(f'inputs/inherited/{name}', 'preparing') for name in names])
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        work.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input_bytes:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    check('input_costs', run['costs']['input_counts'] == dict(json_read_operations=6, input_bytes_read=sum(row['bytes'] for row in inputs)))
    stage, inherited_run = read('inputs/inherited/stage_checks.json'), read('inputs/inherited/run.json')
    check('inherited_V179_settled_complete', stage['valid'] and inherited_run['status'] == 'complete')
    roots, labels = read('inputs/inherited/roots.json'), read('inputs/inherited/labels.json')
    models, inherited = read('inputs/inherited/models.json'), read('inputs/inherited/summary.json')
    check('fixed47_SOURCE24_TARGET', len(roots['SOURCE']) == 47 and len(roots['TARGET']) == 24)
    terminal = terminal_identities(roots, labels)
    check('cached_absorbing_goal_identities', _equal(read('terminal_identities.json'), terminal) and terminal['consistent'])
    check('terminal_identity_work', run['costs']['terminal_work'] == terminal['work'])
    problems = {name: build_problem(roots[name], labels[name]) for name in ('SOURCE', 'TARGET')}
    problems['JOINT'] = build_problem(roots['SOURCE']+roots['TARGET'], labels['SOURCE']+labels['TARGET'])
    saved_problems = read('problems.json')
    for name in ('SOURCE', 'TARGET', 'JOINT'):
        check(name+':independent_class_representatives_optimal_sets', _equal(saved_problems[name], problems[name]) and _equal(problems[name], saved_problems[name]))
        check(name+':problem_work', run['costs']['problem_work'][name] == problems[name]['work'])
    beta = [row[0]-row[1]+row[2] for row in models['SHARED']['coefficients']]
    fitted = {name: evaluate_beta(problem, beta) for name, problem in problems.items()}
    saved_fitted = read('fitted_diagnostics.json')
    check('inherited_beta_rational_evaluation', _equal(saved_fitted, fitted) and _equal(fitted, saved_fitted))
    for cohort in ('SOURCE', 'TARGET'):
        old = {row['root_id']: row['modes']['TREE'] for row in inherited['SHARED']['cohorts'][cohort]['root_records']}
        check(cohort+':old_fitted_actions_and_true_values', all(row['chosen'] == old[row['root_id']]['action'] and
              _equal(row['chosen_components'], old[row['root_id']]['components']) and _equal(row['chosen_utility'], old[row['root_id']]['utility'])
              for row in fitted[cohort]['root_records']))
    capacities = read('capacities.json'); certificate_work = Counter()
    for name in ('SOURCE', 'TARGET', 'JOINT'):
        detail, counters = verify_capacity(problems[name], capacities[name])
        certificate_work.update(counters)
        for item in detail:
            check(name+':'+item['name'], item['passed'])
        check(name+':retained_solver_costs', run['costs'][name]['counts'] == capacities[name]['costs'])
    interpretation = interpret_certificates(problems, capacities)
    check('independent_feature_tuple_flow_cancellation', read('certificate_interpretation.json') == interpretation)
    check('certificate_interpretation_work', run['costs']['certificate_interpretation_work'] == interpretation['work'])
    expected = summarize(problems, capacities, fitted, terminal, inherited, interpretation); saved_summary = read('summary.json')
    check('independent_capacity_summary', _equal(saved_summary, expected) and _equal(expected, saved_summary))
    check('frozen_problem_then_three_capacity_phases', [row['phase'] for row in run['phase_history']] ==
          ['problems_frozen', 'source_capacity', 'target_capacity', 'joint_capacity', 'complete'] and
          all(row['input_reads'] == 6 for row in run['phase_history']))
    check('no_new_predictor_samples_or_native_updates', all(run[key] == 0 for key in
          ('new_environment_samples', 'new_source_games', 'new_native_weight_updates', 'new_predictors_fitted')))
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and expected['complete']
    return dict(schema='acfqp.ranking_capacity.v180.analysis', valid=valid, complete=complete, primary_complete=complete,
                checks=checks, passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=expected,
                costs=dict(new_environment_samples=0, physical_branches_replayed=0, old_kernels_reevaluated=0,
                    old_models_refitted=0, features_recomputed=0, independent_lp_solves=0,
                    inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], original_run_costs=run['costs'],
                    independent_input_counts=dict(work), independent_certificate_counts=dict(certificate_work),
                    independent_certificate_interpretation_counts=interpretation['work'],
                    seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(); result = analyze(args.directory)
    target = args.output or args.directory/'analysis.json'
    target.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], checks=len(result['checks']))))


if __name__ == '__main__':
    main()
