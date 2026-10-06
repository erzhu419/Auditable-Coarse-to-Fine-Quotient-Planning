"""Synthetic exact-array capacity and actual-float policy checks."""
from fractions import Fraction
from types import SimpleNamespace

import numpy as np
import pytest

from acfqp.science import controlled_predictive_relation_capacity_v191 as core


def feature(*values):
    return list(values)+[0.]*(core.COLUMNS-len(values))


def case(name, features, utilities, rewards=None):
    legal = [action for action in core.ACTIONS if action in features]
    root = dict(root_id=name, cohort='SOURCE', life=0, source_id='DESIGN_SOURCE:00',
        legal_actions=legal, relation_features=features,
        immediate_rewards={action: (rewards or {}).get(action, 0.) for action in legal})
    label = dict(root_id=name, action_components={action: [utilities[action], 0., 0.] for action in legal})
    return root, label


def problem(*cases):
    return core.build_problem([row[0] for row in cases], [row[1] for row in cases])


def assert_dual(node):
    weights = [(row['constraint_index'], Fraction(row['weight'])) for row in node['dual']['support']]
    assert all(weight >= 0 for _, weight in weights)
    balance = [sum(weight*Fraction(node['constraints'][index]['a'][column]) for index, weight in weights)
               for column in range(core.COLUMNS+1)]
    assert balance == [0]*core.COLUMNS+[1]
    assert sum(weight*Fraction(node['constraints'][index]['b']) for index, weight in weights) == Fraction(node['dual']['upper_bound'])


def test_identical_features_keep_all_actual_actions_and_do_not_replace_true_optimum():
    data = problem(case('same', dict(DOWN=feature(0), LEFT=feature(0)),
        dict(DOWN=0., LEFT=1.), dict(DOWN=1.)))
    root = data['roots'][0]
    assert [row['action'] for row in root['actions']] == ['DOWN', 'LEFT']
    assert root['optimal_actions'] == ['LEFT'] and root['suboptimal_actions'] == ['DOWN']
    assert data['work']['problem_feature_fraction_conversions'] == 2*98
    result = core.solve_capacity(data)
    assert result['status'] == 'weak_infeasible' and result['upper_bound'] == '-1'
    assert result['costs']['lp_solves'] == result['costs']['symbolic_balance_solves'] == 1
    assert_dual(result['nodes'][0])


def test_unbounded_coefficient_strict_witness_needs_no_symbolic_solve():
    data = problem(case('large', dict(DOWN=feature(1), LEFT=feature(0)),
        dict(DOWN=10., LEFT=8.), dict(LEFT=8.)))
    result = core.solve_capacity(data)
    assert result['status'] == 'strict_feasible'
    assert Fraction(result['witness']['beta'][0]) >= 9
    evaluation = result['witness']['evaluation']
    assert evaluation['all_optimal'] and evaluation['rational_all_optimal']
    assert evaluation['root_records'][0]['actual_chosen'] == 'DOWN'
    assert result['nodes'][0]['dual']['method'] == 'trivial_margin_cap'
    assert result['costs'].get('symbolic_balance_solves', 0) == 0
    assert result['costs']['beta_float_scalar_products'] == 196
    assert_dual(result['nodes'][0])


def test_all_tied_optimum_disjunctions_are_covered_before_negative_claim():
    data = problem(
        case('a', dict(DOWN=feature(1, 0), LEFT=feature(0, 0)), dict(DOWN=2., LEFT=1.), dict(LEFT=1.)),
        case('b', dict(DOWN=feature(0, 1), LEFT=feature(0, 0)), dict(DOWN=2., LEFT=1.), dict(LEFT=1.)),
        case('z', dict(DOWN=feature(0, 1), LEFT=feature(1, 0), RIGHT=feature(1, 1)),
             dict(DOWN=2., LEFT=2., RIGHT=0.)))
    result = core.solve_capacity(data)
    assert result['status'] == 'weak_infeasible' and result['upper_bound'] == '-1/2'
    assert data['roots'][2]['optimal_actions'] == ['DOWN', 'LEFT']
    assert result['costs']['lp_solves'] == result['costs']['symbolic_balance_solves'] == 3
    assert result['nodes'][0]['children'] == [1, 2]
    assert result['nodes'][0]['unexplored_actions'] == []
    assert [row['assigned'][-1]['best_action'] for row in result['nodes'][1:]] == ['DOWN', 'LEFT']
    for node in result['nodes']:
        assert_dual(node)


def test_zero_margin_retains_actual_tie_failure_without_claiming_impossibility():
    data = problem(
        case('a', dict(DOWN=feature(1), LEFT=feature(0)), dict(DOWN=1., LEFT=0.)),
        case('b', dict(DOWN=feature(1), LEFT=feature(0)), dict(DOWN=0., LEFT=1.)))
    result = core.solve_capacity(data)
    assert result['status'] == 'no_positive_margin' and result['upper_bound'] == '0'
    assert result['weak_witness']['evaluation']['all_weak']
    assert not result['weak_witness']['evaluation']['all_optimal']
    assert result['weak_witness']['evaluation']['root_records'][1]['actual_chosen'] == 'DOWN'
    assert_dual(result['nodes'][0])


def test_actual_binary_coordinates_are_subtracted_before_float_lp_conversion():
    data = problem(case('binary', dict(DOWN=feature(1.), LEFT=feature(.1)), dict(DOWN=1., LEFT=0.)))
    actual = data['roots'][0]['actions'][1]
    assert actual['features'][0] == .1
    assert actual['feature_fractions'][0] == str(Fraction(.1))
    coefficient = Fraction(core._constraints(data, [])[0]['a'][0])
    assert coefficient == Fraction(.1)-Fraction(1.)
    assert coefficient != Fraction(.1-1.)
    with pytest.raises(ValueError, match='distinct retained roots'):
        core.build_problem([case('dup', dict(DOWN=feature(0)), dict(DOWN=1.))[0]]*2,
                           [case('dup', dict(DOWN=feature(0)), dict(DOWN=1.))[1]]*2)


def test_large_weights_cannot_turn_rational_only_success_into_actual_policy_claim(monkeypatch):
    data = problem(case('cancellation', dict(DOWN=feature(1., 0., 1.), LEFT=feature(1., 1., 1.)),
                        dict(DOWN=0., LEFT=1.)))
    beta = feature(1e16, 1., -1e16)
    evaluation = core.evaluate_beta(data, beta)
    row = evaluation['root_records'][0]
    assert row['optimal_vs_bad_gap'] == '1'
    assert row['chosen'] == 'LEFT' and row['actual_chosen'] == 'DOWN'
    assert evaluation['rational_all_optimal'] and not evaluation['all_optimal']
    monkeypatch.setattr(core, 'linprog', lambda *args, **kwargs: SimpleNamespace(
        success=True, status=0, message='synthetic cancellation candidate', nit=0,
        x=np.asarray(beta+[1.]), ineqlin=SimpleNamespace(marginals=np.asarray([0., -1.]))))
    with pytest.raises(core.CapacityExecutionError) as caught:
        core.solve_capacity(data)
    record = caught.value.record
    assert record['status'] == 'execution_error' and record['witness'] is None
    assert record['costs']['beta_evaluations'] == record['costs']['symbolic_balance_solves'] == 1
    assert record['nodes'][0]['primal']['evaluation']['minimum_gap'] == '1'


def test_paid_native_or_exact_support_failure_never_becomes_negative_capacity(monkeypatch):
    data = problem(case('failed', dict(DOWN=feature(1.), LEFT=feature(0.)), dict(DOWN=1., LEFT=0.)))
    monkeypatch.setattr(core, 'linprog', lambda *args, **kwargs: SimpleNamespace(
        success=False, status=2, message='synthetic solver failure', nit=0))
    with pytest.raises(core.CapacityExecutionError) as caught:
        core.solve_capacity(data)
    record = caught.value.record
    assert record['status'] == 'execution_error' and record['costs']['lp_solves'] == 1
    assert record['witness'] is None and record['upper_bound'] is None
    monkeypatch.setattr(core, 'linprog', lambda *args, **kwargs: SimpleNamespace(
        success=True, status=0, message='synthetic unbalanced support', nit=0,
        x=np.asarray(feature(0.)+[0.]), ineqlin=SimpleNamespace(marginals=np.asarray([-1., 0.]))))
    with pytest.raises(core.CapacityExecutionError) as caught:
        core.solve_capacity(data)
    record = caught.value.record
    assert record['status'] == 'execution_error' and record['costs']['lp_solves'] == 1
    assert record['costs']['symbolic_balance_solves'] == 1
    assert record['costs']['symbolic_balance_matrix_cells'] == 99
    assert 'cannot balance' in record['failure']['message']
    assert record['nodes'][0]['dual'] is None and record['upper_bound'] is None
