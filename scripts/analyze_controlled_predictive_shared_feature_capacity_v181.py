"""Verify arbitrary shared-feature potentials with exact incidence certificates."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from scripts import analyze_controlled_predictive_ranking_capacity_v180 as previous

OUTPUT = PROJECT/'reports/controlled_predictive_shared_feature_capacity_v181'
ACTIONS, EPS = previous.ACTIONS, previous.EPS
rational, _equal = previous.rational, previous._equal


def lift_problem(problem):
    features = sorted({tuple(row['features']) for root in problem['roots'] for row in root['classes']})
    ids = {values: index for index, values in enumerate(features)}; lifted = deepcopy(problem); work = Counter()
    for root in lifted['roots']:
        for row in root['classes']:
            row['vertex_id'] = ids[tuple(row['features'])]
            work.update(lift_class_records=1, lift_feature_values_read=6, lift_terminal_components_copied=3, lift_vertex_assignments=1)
        work['lift_roots_copied'] += 1
    work['lift_distinct_vertices'] = len(features)
    lifted.update(schema='acfqp.shared_feature_capacity.v181.problem',
                  vertices=[dict(vertex_id=index, features=list(values)) for index, values in enumerate(features)],
                  inherited_problem_work=deepcopy(problem['work']), work=dict(work))
    return lifted


def evaluate_potentials(problem, potentials):
    potentials = list(map(rational, potentials)); records, gaps = [], []
    for root in problem['roots']:
        classes = {row['representative']: row for row in root['classes']}
        scores = {action: rational(row['immediate_reward_fraction'])+potentials[row['vertex_id']] for action, row in classes.items()}
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
    return dict(potentials=list(map(str, potentials)), root_records=records, minimum_gap=None if not gaps else str(min(gaps)),
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
            bound = rational(good['immediate_reward_fraction'])-rational(bad['immediate_reward_fraction'])
            result.append(dict(kind='ranking', root_id=root['root_id'], best_action=action, bad_action=alternative,
                               best_vertex=good['vertex_id'], bad_vertex=bad['vertex_id'], b=str(bound)))
    result.append(dict(kind='margin_cap', root_id=None, best_action=None, bad_action=None, best_vertex=None, bad_vertex=None, b='1'))
    return result


def verify_dual(problem, constraints, dual):
    flow, margin, bound, seen = [Fraction()]*len(problem['vertices']), Fraction(), Fraction(), set()
    for atom in dual['support']:
        index, weight = atom['constraint_index'], rational(atom['weight'])
        if index in seen or not 0 <= index < len(constraints) or weight < 0:
            return False
        seen.add(index); row = constraints[index]
        if row['kind'] == 'ranking':
            flow[row['bad_vertex']] += weight; flow[row['best_vertex']] -= weight
        margin += weight; bound += weight*rational(row['b'])
    return not any(flow) and margin == 1 and bound == rational(dual['upper_bound'])


def verify_recorded_costs(problem, capacity, work, check):
    nodes, costs = capacity['nodes'], capacity['costs']; count = len(nodes); vertices = len(problem['vertices'])
    rows = sum(len(node['constraints']) for node in nodes)
    entries = sum(3 if row['kind'] == 'ranking' else 1 for node in nodes for row in node['constraints'])
    expected = dict(lp_solves=count, lp_constraint_rows=rows, lp_variables=count*(vertices+1), lp_incidence_entries=entries,
                    symbolic_balance_solves=count, dual_balance_vertices_checked=count*vertices, potential_evaluations=count,
                    potential_root_records=count*len(problem['roots']), potential_rational_conversions=count*vertices)
    check('recorded_sparse_LP_and_symbolic_work', all(costs[key] == value for key, value in expected.items()) and
          costs['dual_support_rows'] >= work['dual_support_rows_verified'] and
          costs['dual_margin_weight_accumulations'] == costs['dual_support_rows'] and
          work['dual_vertex_flow_additions'] <= costs.get('dual_vertex_flow_accumulations', 0) <= 2*costs['dual_support_rows'] and
          costs['lp_seconds'] >= 0 and costs['symbolic_balance_seconds'] >= 0)


def verify_capacity(problem, capacity):
    checks, work = [], Counter()
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    nodes = capacity['nodes']; by_id = {node['node_id']: node for node in nodes}
    check('node_ids', [node['node_id'] for node in nodes] == list(range(len(nodes))))
    visited, bounds, strict_nodes, weak = [], [], [], []
    roots = {row['root_id']: row for row in problem['roots']}
    strict_result = capacity['status'] == 'strict_feasible'
    def visit(node_id, parent, assigned):
        if node_id not in by_id or node_id in visited:
            check(f'node{node_id}:unique_reachable_child', False); return False
        node = by_id[node_id]; visited.append(node_id); prefix = f'node{node_id}:'
        check(prefix+'parent_and_optimal_assignment', node['parent_id'] == parent and node['assigned'] == assigned)
        constraints = constraints_for(problem, assigned)
        check(prefix+'independent_incidence_constraints', node['constraints'] == constraints)
        check(prefix+'exact_nonnegative_vertex_balance_and_bound', verify_dual(problem, constraints, node['dual']))
        work.update(nodes_verified=1, incidence_constraints_rebuilt=len(constraints),
                    dual_support_rows_verified=len(node['dual']['support']),
                    dual_vertex_flow_additions=2*sum(constraints[row['constraint_index']]['kind'] == 'ranking' for row in node['dual']['support']))
        native, primal = node['native_lp'], node['primal']
        potentials = [str(rational(value)) for value in native['potentials']]
        evaluation = evaluate_potentials(problem, potentials)
        check(prefix+'native_success_and_exact_binary_potentials', native['success'] and native['status'] == 0 and
              len(potentials) == len(problem['vertices']) and primal['potentials'] == potentials and primal['evaluation'] == evaluation)
        work.update(potential_evaluations=1, potential_root_records=len(problem['roots']),
                    potential_rational_conversions=len(problem['vertices']))
        if evaluation['all_weak']:
            weak.append(dict(node_id=node_id, potentials=potentials, evaluation=evaluation))
        bound = rational(node['dual']['upper_bound'])
        minimum = Fraction(1) if evaluation['minimum_gap'] is None else rational(evaluation['minimum_gap'])
        disposition = 'pruned_negative' if bound < 0 else 'pruned_zero' if bound == 0 else 'strict_witness' if minimum > rational(EPS) else 'branch'
        check(prefix+'disposition', node['disposition'] == disposition)
        if disposition != 'branch':
            check(prefix+'terminal_has_no_branches', node['branch_root_id'] is None and not node['branch_actions'] and not node['children'] and not node['unexplored_actions'])
            if bound <= 0:
                bounds.append(bound); return False
            check(prefix+'strict_whole_scope_margin_and_actual_choice', minimum > rational(EPS) and evaluation['all_optimal'])
            strict_nodes.append(dict(node_id=node_id, potentials=potentials, margin=str(min(Fraction(1), minimum)), evaluation=evaluation))
            return True
        assigned_ids = {row['root_id'] for row in assigned}
        violated = [roots[row['root_id']] for row in evaluation['root_records'] if row['optimal_vs_bad_gap'] is not None and
                    rational(row['optimal_vs_bad_gap']) <= rational(EPS) and len(roots[row['root_id']]['optimal_actions']) > 1 and row['root_id'] not in assigned_ids]
        branch = violated[0] if violated else None
        check(prefix+'first_violating_unassigned_optimal_disjunction', branch is not None and node['branch_root_id'] == branch['root_id'] and node['branch_actions'] == branch['optimal_actions'])
        if branch is None:
            return False
        actions = branch['optimal_actions']; count = len(node['children'])
        check(prefix+'all_visited_or_recorded_unexplored_alternatives', 0 < count <= len(actions) and node['unexplored_actions'] == actions[count:] and (strict_result or count == len(actions)))
        success = False
        for ordinal, child in enumerate(node['children']):
            if ordinal >= len(actions):
                check(prefix+'no_extra_optimal_alternative', False); break
            child_success = visit(child, node_id, assigned+[dict(root_id=branch['root_id'], best_action=actions[ordinal])])
            check(prefix+f'child{ordinal}:DFS_stops_only_after_verified_witness', not success and (not child_success or ordinal == count-1))
            success = success or child_success
        check(prefix+'unexplored_only_after_verified_witness', not node['unexplored_actions'] or success)
        return success
    success = visit(0, None, []) if nodes else False
    check('all_nodes_in_DFS_order', visited == list(range(len(nodes))))
    check('weak_witness_has_exact_nonnegative_gaps', capacity['weak_witness'] == (weak[0] if weak else None))
    if strict_nodes:
        check('strict_result_verified_witness_and_root_upper_bound', success and len(strict_nodes) == 1 and
              capacity['status'] == 'strict_feasible' and capacity['witness'] == strict_nodes[0] and
              rational(capacity['upper_bound']) == rational(nodes[0]['dual']['upper_bound']))
    else:
        upper = max(bounds) if bounds else None
        status = 'weak_infeasible' if upper is not None and upper < 0 else 'no_positive_margin'
        check('exhaustive_nonpositive_subtree_bounds', not success and bool(bounds) and capacity['witness'] is None and
              capacity['status'] == status and rational(capacity['upper_bound']) == upper and not any(node['unexplored_actions'] for node in nodes))
    verify_recorded_costs(problem, capacity, work, check)
    return checks, dict(work)


def feature_coverage(problems):
    source = {tuple(row['features']) for row in problems['SOURCE']['vertices']}
    target = {tuple(row['features']) for row in problems['TARGET']['vertices']}
    records, work = [], Counter(vertex_feature_value_reads=6*(len(source)+len(target)))
    for root in problems['TARGET']['roots']:
        features = sorted({tuple(row['features']) for row in root['classes']})
        unseen = [list(values) for values in features if values not in source]
        records.append(dict(root_id=root['root_id'], distinct_tuples=len(features), unseen_tuples=unseen, all_tuples_seen=not unseen))
        work.update(target_class_feature_value_reads=6*len(features), source_membership_tests=len(features))
    return dict(source_vertices=len(source), target_vertices=len(target), common_vertices=len(source & target),
                target_only_tuples=[list(values) for values in sorted(target-source)],
                target_roots_all_tuples_seen=sum(row['all_tuples_seen'] for row in records), target_root_records=records, work=dict(work))


def summarize(problems, capacities, coverage, inherited):
    return dict(schema='acfqp.shared_feature_capacity.v181.summary', complete=True,
                scopes={name: dict(roots=len(problems[name]['roots']), vertices=len(problems[name]['vertices']),
                    capacity_status=capacities[name]['status'], upper_bound=capacities[name]['upper_bound'],
                    witness=capacities[name]['witness'], weak_witness=capacities[name]['weak_witness'], costs=capacities[name]['costs'])
                    for name in ('SOURCE', 'TARGET', 'JOINT')},
                feature_coverage=coverage, inherited_V180=deepcopy(inherited),
                new_environment_samples=0, new_source_games=0, new_native_weight_updates=0, new_predictors_fitted=0)


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, work = [], Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); work.update(json_read_operations=1, input_bytes_read=len(raw))
        return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = ['stage_checks.json', 'run.json', 'problems.json', 'summary.json']
    check('fixed_four_inherited_inputs', [(row['saved_ref'], row['phase']) for row in inputs] ==
          [(f'inputs/inherited/{name}', 'preparing') for name in names])
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        work.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input_bytes:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    check('input_costs', run['costs']['input_counts'] == dict(json_read_operations=4, input_bytes_read=sum(row['bytes'] for row in inputs)))
    stage, inherited_run = read('inputs/inherited/stage_checks.json'), read('inputs/inherited/run.json')
    check('inherited_V180_settled_complete', stage['valid'] and inherited_run['status'] == 'complete')
    inherited_problems, inherited_summary = read('inputs/inherited/problems.json'), read('inputs/inherited/summary.json')
    problems = {name: lift_problem(inherited_problems[name]) for name in ('SOURCE', 'TARGET', 'JOINT')}
    saved_problems = read('problems.json')
    for name in ('SOURCE', 'TARGET', 'JOINT'):
        check(name+':shared_vertices_and_unchanged_audited_classes', saved_problems[name] == problems[name])
        check(name+':lift_work', run['costs']['lift_work'][name] == problems[name]['work'])
    coverage = feature_coverage(problems)
    check('independent_SOURCE_TARGET_feature_coverage', read('feature_coverage.json') == coverage)
    check('feature_coverage_work', run['costs']['coverage_work'] == coverage['work'])
    capacities = read('capacities.json'); certificate_work = Counter()
    for name in ('SOURCE', 'TARGET', 'JOINT'):
        detail, counters = verify_capacity(problems[name], capacities[name]); certificate_work.update(counters)
        for item in detail:
            check(name+':'+item['name'], item['passed'])
        check(name+':retained_solver_costs', run['costs'][name]['counts'] == capacities[name]['costs'])
    expected = summarize(problems, capacities, coverage, inherited_summary)
    check('independent_capacity_summary_and_inherited_V180', read('summary.json') == expected)
    check('frozen_lift_then_three_capacity_phases', [row['phase'] for row in run['phase_history']] ==
          ['problems_frozen', 'source_capacity', 'target_capacity', 'joint_capacity', 'complete'] and
          all(row['input_reads'] == 4 for row in run['phase_history']))
    check('no_new_predictor_samples_or_native_updates', all(run[key] == 0 for key in
          ('new_environment_samples', 'new_source_games', 'new_native_weight_updates', 'new_predictors_fitted')))
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and expected['complete']
    return dict(schema='acfqp.shared_feature_capacity.v181.analysis', valid=valid, complete=complete, primary_complete=complete,
                checks=checks, passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=expected,
                costs=dict(new_environment_samples=0, physical_branches_replayed=0, old_kernels_reevaluated=0,
                    old_models_refitted=0, features_recomputed=0, independent_lp_solves=0,
                    inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], original_run_costs=run['costs'],
                    independent_input_counts=dict(work), independent_certificate_counts=dict(certificate_work),
                    reconstructed_production_lift_counts={name: problem['work'] for name, problem in problems.items()},
                    reconstructed_feature_coverage_counts=coverage['work'], seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(); result = analyze(args.directory)
    target = args.output or args.directory/'analysis.json'
    target.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], checks=len(result['checks']))))


if __name__ == '__main__':
    main()
