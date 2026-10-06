"""Five synthetic certificate checks without solvers, physics or real inputs."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction

from scripts import analyze_controlled_predictive_relation_capacity_v191 as audit


def root(name, features, rewards, values):
    row = dict(root_id=name, cohort='SOURCE', life=0, source_id='synthetic',
        legal_actions=list(features), relation_features={action: [float(value)]+[0.]*97 for action, value in features.items()},
        immediate_rewards=rewards)
    labels = dict(root_id=name, action_components={action: [float(value), 0., 0.] for action, value in values.items()})
    return row, labels


def fixture(data, nodes_spec, status, upper):
    problem = audit.build_problem([row for row, _ in data], [label for _, label in data])
    nodes, costs = [], Counter(lp_seconds=0., symbolic_balance_seconds=0.)
    weak, witness = None, None
    for index, action, beta_value, support, bound, disposition in nodes_spec:
        assigned = [] if action is None else [dict(root_id='multi', best_action=action)]
        beta = [float(beta_value)]+[0.]*97; evaluation = audit.evaluate_beta(problem, beta)
        constraints = audit.constraints_for(problem, assigned)
        strict = disposition == 'strict_witness'
        dual = dict(method='trivial_margin_cap' if strict else 'exact_native_support',
            support=[dict(constraint_index=i, weight='1' if strict else '1/2') for i in support], upper_bound=bound)
        nodes.append(dict(node_id=index, parent_id=None if index == 0 else 0, assigned=assigned,
            constraints=constraints, native_lp=dict(success=True, status=0, message='fixture', iterations=0,
                beta=beta, delta=float(Fraction(bound))), primal=dict(beta=evaluation['beta'], evaluation=evaluation),
            dual=dual, disposition=disposition, branch_root_id='multi' if disposition == 'branch' else None,
            branch_actions=['DOWN', 'LEFT'] if disposition == 'branch' else [],
            children=[1, 2] if disposition == 'branch' else [], unexplored_actions=[]))
        if evaluation['all_weak'] and weak is None:
            weak = dict(node_id=index, beta=evaluation['beta'], evaluation=evaluation)
        if strict:
            margin = min(Fraction(1), Fraction(evaluation['minimum_gap']))
            witness = dict(node_id=index, beta=evaluation['beta'], margin=str(margin), evaluation=evaluation)
        costs.update(lp_solves=1, lp_constraint_rows=len(constraints), lp_matrix_cells=99*len(constraints),
            symbolic_balance_solves=int(not strict), trivial_margin_cap_certificates=int(strict),
            symbolic_balance_matrix_cells=0 if strict else 99*len(support), dual_support_rows=len(support),
            dual_balance_scalar_products=99*len(support), beta_evaluations=1,
            constraint_exact_feature_subtractions=98*(len(constraints)-1),
            constraint_exact_reward_subtractions=len(constraints)-1)
        costs.update(evaluation['work'])
    capacity = dict(schema=audit.SCHEMA+'.capacity', status=status, nodes=nodes,
        witness=witness, weak_witness=weak, upper_bound=upper, costs=dict(costs))
    return problem, capacity


def test_all_legal_actions_survive_and_binary_coordinates_are_not_rounded():
    row, labels = root('r', {'DOWN': .1+.2, 'LEFT': .3, 'UP': .1+.2},
        {'DOWN': 0., 'LEFT': 0., 'UP': 0.}, {'DOWN': 0., 'LEFT': 1., 'UP': 2.})
    problem = audit.build_problem([row], [labels]); saved = problem['roots'][0]
    assert [record['action'] for record in saved['actions']] == ['DOWN', 'LEFT', 'UP']
    assert saved['optimal_actions'] == ['UP']
    constraint = audit.constraints_for(problem, [])[0]
    assert Fraction(constraint['a'][0]) == 0  # DOWN and UP kept separately.
    other = audit.constraints_for(problem, [])[1]
    assert Fraction(other['a'][0]) == Fraction(.3)-Fraction(.1+.2)
    assert Fraction(other['a'][0]) != 0


def test_strict_witness_has_exact_margin_and_actual_float_choice_without_symbolic_solve():
    data = [root('r', {'DOWN': 1, 'LEFT': 0}, {'DOWN': 0., 'LEFT': 0.}, {'DOWN': 1., 'LEFT': 0.})]
    problem, capacity = fixture(data, [(0, None, 2., [1], '1', 'strict_witness')], 'strict_feasible', '1')
    checks, _ = audit.verify_capacity(problem, capacity)
    assert all(row['passed'] for row in checks)
    assert capacity['costs']['symbolic_balance_solves'] == 0
    assert capacity['witness']['evaluation']['all_optimal']
    changed = deepcopy(capacity); changed['nodes'][0]['primal']['evaluation']['root_records'][0]['actual_chosen'] = 'LEFT'
    assert not all(row['passed'] for row in audit.verify_capacity(problem, changed)[0])


def test_exact_dual_rejects_stationarity_error_negative_weight_and_wrong_bound():
    constraints = [dict(a=['0']*98+['1'], b='1')]
    certificate = dict(support=[dict(constraint_index=0, weight='1')], upper_bound='1')
    assert audit.verify_dual(constraints, certificate)
    changed = deepcopy(constraints); changed[0]['a'][83] = '1/1000000000000000000000000'
    assert not audit.verify_dual(changed, certificate)
    changed = deepcopy(certificate); changed['support'][0]['weight'] = '-1'
    assert not audit.verify_dual(constraints, changed)
    changed = deepcopy(certificate); changed['upper_bound'] = '0'
    assert not audit.verify_dual(constraints, changed)


def test_negative_bound_requires_full_coverage_of_tied_optimal_disjunction():
    data = [root('multi', {'DOWN': 0, 'LEFT': 2, 'RIGHT': 1},
            {'DOWN': 0., 'LEFT': 0., 'RIGHT': 2.}, {'DOWN': 2., 'LEFT': 2., 'RIGHT': 1.}),
        root('unique1', {'DOWN': 0, 'LEFT': 1}, {'DOWN': 0., 'LEFT': 0.}, {'DOWN': 1., 'LEFT': 0.}),
        root('unique2', {'DOWN': 1, 'LEFT': 0}, {'DOWN': 1., 'LEFT': 0.}, {'DOWN': 1., 'LEFT': 0.})]
    problem, capacity = fixture(data, [(0, None, -.5, [0, 1], '1/2', 'branch'),
        (1, 'DOWN', -1.5, [0, 2], '-1/2', 'pruned_negative'),
        (2, 'LEFT', -1., [0, 1], '-1', 'pruned_negative')], 'weak_infeasible', '-1/2')
    assert all(row['passed'] for row in audit.verify_capacity(problem, capacity)[0])
    changed = deepcopy(capacity); changed['nodes'][0]['children'] = [1]; changed['nodes'][0]['unexplored_actions'] = ['LEFT']
    checks, _ = audit.verify_capacity(problem, changed)
    assert any(not row['passed'] and 'alternatives' in row['name'] for row in checks)


def test_certificate_failure_is_hold_and_cannot_support_negative_capacity_claim():
    row, labels = root('r', {'DOWN': 0}, {'DOWN': 0.}, {'DOWN': 1.})
    problem = audit.build_problem([row], [labels])
    capacity = dict(status='execution_error', nodes=[], witness=None, upper_bound=None,
        failure=dict(type='ValueError', message='native support cannot balance exactly'))
    checks, _ = audit.verify_capacity(problem, capacity)
    assert any(row['name'] == 'retained_HOLD_has_no_capacity_claim' and row['passed'] for row in checks)
    assert not all(row['passed'] for row in checks)
    changed = deepcopy(capacity); changed['upper_bound'] = '-1'
    assert any(row['name'] == 'retained_HOLD_has_no_capacity_claim' and not row['passed']
        for row in audit.verify_capacity(problem, changed)[0])
