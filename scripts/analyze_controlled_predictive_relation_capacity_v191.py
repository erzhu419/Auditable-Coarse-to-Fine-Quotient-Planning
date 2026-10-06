"""Independent exact certificates for the retained 98-coordinate ranking class."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT/'src'))
from scripts import analyze_controlled_predictive_merge_relations_v190 as relation

ACTIONS, EPS = relation.ACTIONS, relation.EPS
COLUMNS = 98
SCHEMA = 'acfqp.relation_capacity.v191'
OUTPUT = PROJECT/'reports/controlled_predictive_relation_capacity_v191'


def rational(value):
    return value if isinstance(value, Fraction) else Fraction(value)


def utility(vector):
    return vector[0]-vector[1]+vector[2]


def build_problem(roots, labels):
    by_id = {row['root_id']: row['action_components'] for row in labels}
    records, work = [], Counter()
    for root in sorted(roots, key=lambda row: row['root_id']):
        actions = []
        for action in ACTIONS:
            if action not in root['legal_actions']:
                continue
            features = list(map(float, root['relation_features'][action]))
            if len(features) != COLUMNS:
                raise ValueError('the frozen relation basis has 98 coordinates')
            reward = float(root['immediate_rewards'][action]); vector = list(map(float, by_id[root['root_id']][action]))
            actions.append(dict(action=action, features=features,
                feature_fractions=[str(Fraction(float(value))) for value in features],
                immediate_reward=reward, immediate_reward_fraction=str(Fraction(reward)),
                components=vector, utility=utility(vector)))
            work.update(problem_feature_values_read=COLUMNS, problem_feature_fraction_conversions=COLUMNS,
                problem_immediate_rewards_read=1, problem_reward_fraction_conversions=1,
                problem_terminal_components_read=3, problem_action_utility_evaluations=1,
                problem_action_records=1)
        maximum = max(row['utility'] for row in actions)
        optimal = [row['action'] for row in actions if row['utility'] >= maximum-EPS]
        records.append(dict(root_id=root['root_id'], cohort=root['cohort'], life=root['life'],
            source_id=root['source_id'], actions=actions, optimal_actions=optimal,
            suboptimal_actions=[row['action'] for row in actions if row['action'] not in optimal],
            best_utility=maximum))
        work['problem_root_records'] += 1
    if not records or len({row['root_id'] for row in records}) != len(records):
        raise ValueError('capacity scopes require distinct retained roots')
    return dict(schema=SCHEMA+'.problem', columns=COLUMNS, epsilon=EPS, roots=records, work=dict(work))


def constraints_for(problem, assigned):
    selected = {row['root_id']: row['best_action'] for row in assigned}; constraints = []
    for root in problem['roots']:
        if not root['suboptimal_actions']:
            continue
        action = selected.get(root['root_id'])
        if action is None and len(root['optimal_actions']) == 1:
            action = root['optimal_actions'][0]
        if action is None:
            continue
        records = {row['action']: row for row in root['actions']}; good = records[action]
        for alternative in root['suboptimal_actions']:
            bad = records[alternative]
            # Convert both actual binary floats before subtraction. No rounding.
            coefficients = [str(rational(b)-rational(g)) for b, g in
                zip(bad['feature_fractions'], good['feature_fractions'], strict=True)]+['1']
            bound = rational(good['immediate_reward_fraction'])-rational(bad['immediate_reward_fraction'])
            constraints.append(dict(kind='ranking', root_id=root['root_id'], best_action=action,
                bad_action=alternative, a=coefficients, b=str(bound)))
    constraints.append(dict(kind='margin_cap', root_id=None, best_action=None, bad_action=None,
        a=['0']*COLUMNS+['1'], b='1'))
    return constraints


def evaluate_beta(problem, beta):
    exact = list(map(rational, beta)); actual = list(map(float, exact)); records, gaps = [], []
    work = Counter(beta_rational_conversions=COLUMNS, beta_float_conversions=COLUMNS)
    for root in problem['roots']:
        by_action = {row['action']: row for row in root['actions']}
        scores = {action: rational(row['immediate_reward_fraction'])+sum(
            (rational(value)*weight for value, weight in zip(row['feature_fractions'], exact, strict=True)), Fraction())
            for action, row in by_action.items()}
        float_scores = {action: row['immediate_reward']+sum(
            float(value)*weight for value, weight in zip(row['features'], actual, strict=True))
            for action, row in by_action.items()}
        chosen = next(action for action in ACTIONS if action in scores); actual_chosen = chosen
        for action in ACTIONS:
            if action in scores and scores[action] > scores[chosen]+rational(EPS):
                chosen = action
            if action in float_scores and float_scores[action] > float_scores[actual_chosen]+EPS:
                actual_chosen = action
        good = max(scores[action] for action in root['optimal_actions'])
        bad = max((scores[action] for action in root['suboptimal_actions']), default=None)
        gap = None if bad is None else good-bad
        if gap is not None:
            gaps.append(gap)
        row = by_action[actual_chosen]
        records.append(dict(root_id=root['root_id'], chosen=chosen, chosen_optimal=chosen in root['optimal_actions'],
            action_scores={action: str(value) for action, value in scores.items()},
            actual_action_scores=float_scores, actual_chosen=actual_chosen,
            actual_chosen_optimal=actual_chosen in root['optimal_actions'], optimal_score=str(good),
            suboptimal_score=None if bad is None else str(bad), optimal_vs_bad_gap=None if gap is None else str(gap),
            chosen_components=list(row['components']), chosen_utility=row['utility'], regret=root['best_utility']-row['utility']))
        work.update(beta_root_records=1, beta_action_records=len(by_action),
            beta_feature_fraction_reads=COLUMNS*len(by_action), beta_rational_scalar_products=COLUMNS*len(by_action),
            beta_float_feature_reads=COLUMNS*len(by_action), beta_float_scalar_products=COLUMNS*len(by_action),
            beta_exact_score_evaluations=len(by_action), beta_float_score_evaluations=len(by_action),
            beta_exact_choice_comparisons=len(by_action), beta_float_choice_comparisons=len(by_action),
            beta_gap_subtractions=int(gap is not None))
    return dict(beta=list(map(str, exact)), root_records=records,
        minimum_gap=None if not gaps else str(min(gaps)),
        all_optimal=all(row['actual_chosen_optimal'] for row in records),
        rational_all_optimal=all(row['chosen_optimal'] for row in records),
        all_weak=all(gap >= 0 for gap in gaps), work=dict(work))


def verify_dual(constraints, dual):
    if dual is None:
        return False
    weights, seen = {}, set()
    for atom in dual['support']:
        index, weight = atom['constraint_index'], rational(atom['weight'])
        if index in seen or not 0 <= index < len(constraints) or weight < 0:
            return False
        seen.add(index); weights[index] = weight
    balance = [sum((weight*rational(constraints[index]['a'][j]) for index, weight in weights.items()), Fraction())
        for j in range(COLUMNS+1)]
    bound = sum((weight*rational(constraints[index]['b']) for index, weight in weights.items()), Fraction())
    return balance == [Fraction()]*COLUMNS+[Fraction(1)] and bound == rational(dual['upper_bound'])


def verify_capacity(problem, capacity):
    checks, work = [], Counter()
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    nodes = capacity['nodes']; by_id = {node['node_id']: node for node in nodes}
    check('node_ids', [node['node_id'] for node in nodes] == list(range(len(nodes))))
    if capacity['status'] == 'execution_error':
        check('retained_HOLD_has_no_capacity_claim', capacity['witness'] is None and
            capacity['upper_bound'] is None and bool(capacity.get('failure')))
        check('capacity_certificate_complete', False)
        return checks, dict(work)
    visited, bounds, strict_nodes, weak = [], [], [], []
    rows = {row['root_id']: row for row in problem['roots']}
    strict_result = capacity['status'] == 'strict_feasible'
    def visit(node_id, parent, assigned):
        if node_id not in by_id or node_id in visited:
            check(f'node{node_id}:unique_reachable_child', False); return False
        node = by_id[node_id]; visited.append(node_id); prefix = f'node{node_id}:'
        check(prefix+'parent_and_optimal_assignment', node['parent_id'] == parent and node['assigned'] == assigned)
        constraints = constraints_for(problem, assigned)
        check(prefix+'exact_binary_feature_constraints', node['constraints'] == constraints)
        check(prefix+'exact_nonnegative_99_coordinate_dual_and_bound', verify_dual(constraints, node['dual']))
        work.update(nodes_verified=1, ranking_constraints_rebuilt=len(constraints),
            dual_support_rows_verified=len(node['dual']['support']),
            dual_balance_scalar_products=(COLUMNS+1)*len(node['dual']['support']))
        native, primal = node['native_lp'], node['primal']
        beta = [str(Fraction(float(value))) for value in native['beta']]
        evaluation = evaluate_beta(problem, beta)
        check(prefix+'native_success_exact_beta_and_actual_float_choice', native['success'] and native['status'] == 0 and
            primal['beta'] == beta and primal['evaluation'] == evaluation)
        work.update(beta_evaluations=1, **evaluation['work'])
        if evaluation['all_weak']:
            weak.append(dict(node_id=node_id, beta=beta, evaluation=evaluation))
        bound = rational(node['dual']['upper_bound'])
        minimum = Fraction(1) if evaluation['minimum_gap'] is None else rational(evaluation['minimum_gap'])
        strict = minimum > rational(EPS) and evaluation['all_optimal'] and evaluation['rational_all_optimal']
        expected = 'strict_witness' if strict else 'pruned_negative' if bound < 0 else 'pruned_zero' if bound == 0 else 'branch'
        check(prefix+'verified_primal_before_exact_bound_disposition', node['disposition'] == expected)
        if expected != 'branch':
            check(prefix+'terminal_has_no_branches', node['branch_root_id'] is None and not node['branch_actions'] and
                not node['children'] and not node['unexplored_actions'])
            if strict:
                check(prefix+'strict_rational_gap_and_actual_float_optima', minimum > rational(EPS) and
                    evaluation['rational_all_optimal'] and evaluation['all_optimal'])
                check(prefix+'strict_cap_bound_needs_no_symbolic_balance', node['dual']['method'] == 'trivial_margin_cap' and
                    node['dual']['support'] == [dict(constraint_index=len(constraints)-1, weight='1')] and bound == 1)
                strict_nodes.append(dict(node_id=node_id, beta=beta, margin=str(min(Fraction(1), minimum)), evaluation=evaluation))
                return True
            check(prefix+'nonpositive_bound_is_exact_native_support', node['dual']['method'] == 'exact_native_support')
            bounds.append(bound); return False
        selected = {row['root_id'] for row in assigned}
        check(prefix+'branch_bound_is_exact_native_support', node['dual']['method'] == 'exact_native_support')
        violated = [rows[row['root_id']] for row in evaluation['root_records'] if
            row['optimal_vs_bad_gap'] is not None and rational(row['optimal_vs_bad_gap']) <= rational(EPS) and
            len(rows[row['root_id']]['optimal_actions']) > 1 and row['root_id'] not in selected]
        branch = violated[0] if violated else None
        check(prefix+'first_unassigned_optimal_disjunction', branch is not None and
            node['branch_root_id'] == branch['root_id'] and node['branch_actions'] == branch['optimal_actions'])
        if branch is None:
            return False
        actions = branch['optimal_actions']; count = len(node['children'])
        check(prefix+'all_visited_or_recorded_unexplored_alternatives', 0 < count <= len(actions) and
            node['unexplored_actions'] == actions[count:] and (strict_result or count == len(actions)))
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
    check('retained_weak_witness_requires_exact_nonnegative_gap', capacity['weak_witness'] == (weak[0] if weak else None))
    if strict_nodes:
        check('strict_result_matches_verified_whole_scope_primal', success and len(strict_nodes) == 1 and
            capacity['status'] == 'strict_feasible' and capacity['witness'] == strict_nodes[0] and
            rational(capacity['upper_bound']) == rational(nodes[0]['dual']['upper_bound']))
    else:
        upper = max(bounds) if bounds else None
        status = 'weak_infeasible' if upper is not None and upper < 0 else 'no_positive_margin'
        check('exhaustive_nonpositive_subtree_bounds', not success and bool(bounds) and capacity['witness'] is None and
            capacity['status'] == status and rational(capacity['upper_bound']) == upper and
            not any(node['unexplored_actions'] for node in nodes))
    constraint_rows = sum(len(node['constraints']) for node in nodes)
    costs = capacity['costs']; symbolic = sum(node['dual']['method'] == 'exact_native_support' for node in nodes)
    trivial = len(nodes)-symbolic
    expected_costs = dict(lp_solves=len(nodes), lp_constraint_rows=constraint_rows,
        lp_matrix_cells=(COLUMNS+1)*constraint_rows, symbolic_balance_solves=symbolic,
        beta_evaluations=len(nodes), beta_root_records=len(nodes)*len(problem['roots']),
        beta_rational_conversions=COLUMNS*len(nodes), trivial_margin_cap_certificates=trivial,
        constraint_exact_feature_subtractions=COLUMNS*(constraint_rows-len(nodes)),
        constraint_exact_reward_subtractions=constraint_rows-len(nodes))
    check('recorded_solver_and_symbolic_work', all(costs.get(key, 0) == value for key, value in expected_costs.items()) and
        all(costs.get(key, 0) == value for key, value in work.items() if key.startswith('beta_')) and
        costs.get('dual_support_rows', 0) >= sum(len(node['dual']['support']) for node in nodes) and
        costs.get('dual_balance_scalar_products', 0) == (COLUMNS+1)*costs.get('dual_support_rows', 0) and
        costs.get('symbolic_balance_matrix_cells', 0) == (COLUMNS+1)*(costs.get('dual_support_rows', 0)-trivial) and
        costs['lp_seconds'] >= 0 and costs.get('symbolic_balance_seconds', 0.) >= 0)
    return checks, dict(work)


def source_diagnostics(roots, model):
    records, work = [], Counter()
    for root in sorted(roots, key=lambda row: row['root_id']):
        decision = relation.choose_action(model, relation.observable(root), work)
        legal = [action for action in ACTIONS if action in root['legal_actions']]
        vectors = root['action_components']; values = {action: utility(vectors[action]) for action in legal}
        maximum = max(values.values()); oracle = next(action for action in legal if values[action] >= maximum-EPS)
        action = decision['canonical_action']; regret = maximum-values[action]
        records.append(dict(root_id=root['root_id'], source_id=root['source_id'], decision=decision,
            action=action, components=list(vectors[action]), utility=values[action], oracle_action=oracle,
            oracle_components=list(vectors[oracle]), oracle_utility=maximum, regret=regret, positive_regret=regret > EPS))
        work.update(source_observable_root_preparations=1, source_complete_component_reads=3*len(legal),
            source_action_utility_evaluations=len(legal), source_selected_component_reads=3,
            source_oracle_component_reads=3, source_regret_subtractions=1,
            source_oracle_action_comparisons=legal.index(oracle)+1, source_diagnostic_root_records=1)
    n = len(records)
    metrics = dict(roots=n, components=[math.fsum(row['components'][i] for row in records)/n for i in range(3)],
        utility=math.fsum(row['utility'] for row in records)/n,
        oracle_components=[math.fsum(row['oracle_components'][i] for row in records)/n for i in range(3)],
        oracle_utility=math.fsum(row['oracle_utility'] for row in records)/n,
        regret_mean=math.fsum(row['regret'] for row in records)/n,
        positive_regret_roots=sum(row['positive_regret'] for row in records),
        fallback_roots=sum(row['decision']['fallback'] for row in records))
    work.update(source_summary_component_reads=6*n, source_summary_scalar_reads=3*n, source_summary_flag_reads=2*n)
    return dict(root_records=records, metrics=metrics, work=dict(work))


def retained_target_metrics(roots, choices, summary, labels):
    decisions = {row['root_id']: row for row in choices['RELATION']}
    old_records = {row['root_id']: row for row in summary['root_records']}
    vectors = {row['root_id']: row['action_components'] for row in labels}
    ids = {root['root_id'] for root in roots}; records, checks, work = [], [], Counter()
    checks.append(dict(name='complete_retained_TARGET_choice_summary_label_binding', passed=
        len(ids) == len(roots) == len(decisions) == len(old_records) == len(vectors) and
        ids == set(decisions) == set(old_records) == set(vectors)))
    for root in roots:
        by_action = vectors[root['root_id']]; choice = decisions[root['root_id']]
        action = choice['canonical_action']; oracle = root['legal_actions'][0]
        for alternative in root['legal_actions'][1:]:
            if utility(by_action[alternative]) > utility(by_action[oracle])+EPS:
                oracle = alternative
        vector, oracle_vector = list(by_action[action]), list(by_action[oracle])
        record = dict(action=action, components=vector, utility=utility(vector),
            regret=utility(oracle_vector)-utility(vector), fallback=choice['fallback'])
        expected_oracle = dict(action=oracle, components=oracle_vector, utility=utility(oracle_vector),
            regret=0., fallback=False)
        saved = old_records[root['root_id']]['models']
        checks.append(dict(name='settled_target_choice_RFS_binding:'+root['root_id'], passed=
            action in root['legal_actions'] and saved['RELATION'] == record and saved['ORACLE'] == expected_oracle))
        records.append(dict(selected=record, oracle=expected_oracle))
        work.update(independent_retained_target_root_bindings=1,
            independent_retained_target_complete_component_reads=3*len(root['legal_actions']),
            independent_retained_target_selected_components_read=3, independent_retained_target_oracle_components_read=3)
    n = len(roots)
    components = [math.fsum(row['selected']['components'][i] for row in records)/n for i in range(3)]
    oracle_components = [math.fsum(row['oracle']['components'][i] for row in records)/n for i in range(3)]
    selected = dict(components=components, utility=utility(components),
        positive_regret_roots=sum(row['selected']['regret'] > EPS for row in records),
        fallback_roots=sum(row['selected']['fallback'] for row in records))
    oracle = dict(components=oracle_components, utility=utility(oracle_components), positive_regret_roots=0, fallback_roots=0)
    checks.append(dict(name='settled_target_aggregate_RFS_binding', passed=
        relation.same(summary['models']['RELATION'], selected) and relation.same(summary['models']['ORACLE'], oracle)))
    metrics = dict(roots=n, **selected, oracle_components=oracle_components, oracle_utility=oracle['utility'],
        regret_mean=oracle['utility']-selected['utility'])
    binding = dict(retained_target_root_bindings=n, retained_target_choice_bindings=n,
        retained_target_summary_root_bindings=n, retained_target_aggregate_reads=12)
    return metrics, binding, checks, dict(work)


def summarize(problems, capacities, source, target):
    learned = dict(SOURCE=source['metrics'], TARGET=target); total = source['metrics']['roots']+target['roots']
    joint = dict(roots=total)
    for key in ('components', 'oracle_components'):
        joint[key] = [math.fsum(row['roots']*row[key][i] for row in learned.values())/total for i in range(3)]
    for key in ('utility', 'oracle_utility', 'regret_mean'):
        joint[key] = math.fsum(row['roots']*row[key] for row in learned.values())/total
    for key in ('positive_regret_roots', 'fallback_roots'):
        joint[key] = sum(row[key] for row in learned.values())
    learned['JOINT'] = joint; scopes = {}
    for name in ('SOURCE', 'TARGET', 'JOINT'):
        capacity = capacities[name]; weak, witness = capacity['weak_witness'], capacity['witness']
        attained = weak is not None and weak['evaluation']['all_optimal']
        interpretation = 'attained_by_retained_strict_witness' if capacity['status'] == 'strict_feasible' else (
            'impossible_on_retained_roots' if capacity['status'] == 'weak_infeasible' else
            'attained_by_retained_weak_witness' if attained else 'unknown')
        scopes[name] = dict(roots=len(problems[name]['roots']), status=capacity['status'], upper_bound=capacity['upper_bound'],
            strict_witness_margin=None if witness is None else witness['margin'], solver_nodes=len(capacity['nodes']),
            lp_solves=capacity['costs'].get('lp_solves', 0),
            native_lp_status_counts=dict(Counter(str(node['native_lp']['status']) for node in capacity['nodes'])),
            strict_witness_actual_all_optimal=None if witness is None else witness['evaluation']['all_optimal'],
            strict_witness_rational_all_optimal=None if witness is None else witness['evaluation']['rational_all_optimal'],
            actual_tie_policy_attainability=interpretation,
            weak_witness_all_optimal=None if weak is None else weak['evaluation']['all_optimal'], learned=learned[name])
    return dict(schema=SCHEMA+'.summary', complete=all(capacities[name]['status'] in
        ('strict_feasible', 'weak_infeasible', 'no_positive_margin') for name in ('SOURCE', 'TARGET', 'JOINT')),
        scopes=scopes, new_environment_samples=0, new_fits=0, new_labels=0, new_capacity_scopes=len(capacities),
        work=dict(summary_scope_records=3, summary_learned_weighted_component_products=12,
            summary_learned_weighted_scalar_products=6, summary_learned_count_reads=4))


def analyze(directory):
    begun = perf_counter(); directory = Path(directory); checks, io = [], Counter()
    def read(relative):
        raw = (directory/relative).read_bytes(); io.update(json_read_operations=1, input_bytes_read=len(raw)); return json.loads(raw)
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
    run, inputs = read('run.json'), read('input_manifest.json')
    names = ('v190_stage_checks.json', 'v190_metadata_amendment.json', 'v190_run.json', 'v190_roots.json',
        'v190_labels.json', 'v190_model.json', 'v190_choices.json', 'v190_summary.json')
    check('eight_protocol_frozen_retained_inputs', [(row['saved_ref'], row['phase']) for row in inputs] ==
        [(f'inputs/inherited/{name}', 'protocol_frozen') for name in names])
    for row in inputs:
        saved, original = (directory/row['saved_ref']).read_bytes(), Path(row['path']).read_bytes()
        io.update(input_byte_comparisons=1, input_comparison_bytes_read=len(saved)+len(original))
        check('retained_input:'+row['saved_ref'], saved == original and len(saved) == row['bytes'])
    stage, amendment, prior = [read('inputs/inherited/'+name) for name in names[:3]]
    check('settled_amended_V190_original_negative_audit_preserved', not stage['valid'] and
        stage['frozen_source_same'] and stage['frozen_inputs_same'] and amendment['corrected_valid'] and
        not amendment['original_valid'] and prior['status'] == 'complete')
    inherited = read('inputs/inherited/v190_roots.json'); labels = read('inputs/inherited/v190_labels.json')
    model = read('inputs/inherited/v190_model.json'); choices = read('inputs/inherited/v190_choices.json')
    old_summary = read('inputs/inherited/v190_summary.json')
    source, target = deepcopy(inherited['SOURCE']), inherited['TARGET']
    check('fixed_SOURCE143_36groups_retained_TARGET96', len(source) == 143 and
        len({row['source_id'] for row in source}) == 36 and len(target) == len(labels) == 96)
    cache_counts = relation.cache_roots(source)
    check('one_new_SOURCE_projection_and_no_TARGET_recomputation', read('roots.json') == dict(SOURCE=source, TARGET=target) and
        run['costs']['source_cache']['counts'] == cache_counts)
    source_labels = [dict(root_id=root['root_id'], action_components=root['action_components']) for root in source]
    problems = dict(SOURCE=build_problem(source, source_labels), TARGET=build_problem(target, labels),
        JOINT=build_problem(source+target, source_labels+labels))
    saved_problems = read('problems.json')
    for name, problem in problems.items():
        check(name+':independent_98_binary_coordinates_all_legal_actions_and_optimal_sets', saved_problems[name] == problem)
        check(name+':all_paid_problem_construction', run['costs']['problem_'+name]['counts'] == problem['work'])
    source_result = source_diagnostics(source, model)
    check('SOURCE_actual_frozen_full_RFS_choices_and_regrets', read('learned_source_diagnostics.json') == source_result)
    check('SOURCE_actual_frozen_choice_paid_work', run['costs']['source_evaluation']['counts'] == source_result['work'])
    target_metrics, bindings, target_checks, target_work = retained_target_metrics(target, choices, old_summary, labels)
    checks.extend(target_checks)
    check('settled_TARGET_only_binding_paid_work', run['costs']['retained_target_bindings']['counts'] == bindings)
    capacities = read('capacities.json'); certificate_work = Counter()
    for name, problem in problems.items():
        detail, counters = verify_capacity(problem, capacities[name]); certificate_work.update(counters)
        for item in detail:
            check(name+':'+item['name'], item['passed'])
        check(name+':once_retained_solver_costs', run['costs']['capacity_'+name]['counts'] == capacities[name]['costs'])
    summary = summarize(problems, capacities, source_result, target_metrics)
    check('certified_capacity_and_actual_learned_loss_summary', relation.same(read('summary.json'), summary))
    check('all_paid_summary_work', run['costs']['summary']['counts'] == summary['work'])
    phases = [('protocol_frozen', 0), ('problems_frozen', 8), ('capacity_SOURCE', 8), ('capacity_TARGET', 8),
        ('capacity_JOINT', 8), ('complete', 8)]
    check('fixed_problems_before_three_capacity_scopes', [(row['phase'], row['input_reads']) for row in run['phase_history']] == phases)
    check('all_paid_retained_input_counts', run['costs']['input_counts'] == dict(json_read_operations=8,
        input_bytes_read=sum(row['bytes'] for row in inputs), input_bytes_retained=sum(row['bytes'] for row in inputs)))
    zero = ('new_environment_samples', 'new_source_games', 'new_native_weight_updates', 'new_predictors_fitted',
        'new_reference_kernels', 'new_exact_label_roots', 'new_boards_generated')
    check('three_scopes_no_new_boards_labels_fits_or_samples', all(run[key] == 0 for key in zero) and
        run['new_capacity_attempts'] == run['new_capacity_scopes'] == 3 and
        run['new_lp_solves'] == sum(row['costs']['lp_solves'] for row in capacities.values()))
    valid = all(row['passed'] for row in checks); complete = valid and run['status'] == 'complete' and summary['complete']
    return dict(schema=SCHEMA+'.analysis', valid=valid, complete=complete, primary_complete=complete, checks=checks,
        passed_checks=sum(row['passed'] for row in checks), total_checks=len(checks), summary=summary,
        costs=dict(independent_lp_solves=0, independent_svd_solves=0, old_models_refitted=0,
            new_kernels_reintegrated=0, new_environment_samples=0, physical_branches_replayed=0,
            independent_input_counts=dict(io), independent_source_cache_counts=cache_counts,
            independent_source_evaluation_counts=source_result['work'], independent_target_binding_counts=target_work,
            independent_certificate_counts=dict(certificate_work), original_run_costs=run['costs'],
            inherited_cost_refs=run['inherited_cost_refs'], test_refs=run['test_refs'], seconds=perf_counter()-begun))


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, default=OUTPUT)
    args = parser.parse_args(); result = analyze(args.directory)
    (args.directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(valid=result['valid'], complete=result['complete'], passed=result['passed_checks'], total=result['total_checks'])))


if __name__ == '__main__':
    main()
