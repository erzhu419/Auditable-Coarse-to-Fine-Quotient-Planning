"""Pure capacity witnesses, tied optima and exact contradiction certificates."""
from fractions import Fraction
from types import SimpleNamespace

import pytest

from acfqp.science import controlled_predictive_ranking_capacity_v180 as core


ZERO = [0]*6
VACANCY = [0, 1, 0, 0, 0, 0]
ROW_PAIR = [0, 0, 1, 0, 0, 0]


def case(name, features, utilities, rewards=None):
    legal = [action for action in core.ACTIONS if action in features]
    root = dict(root_id=name, cohort='SOURCE', life=0, source_id='DESIGN_SOURCE:00',
                legal_actions=legal, action_features=features,
                immediate_rewards={action: (rewards or {}).get(action, 0.) for action in legal})
    label = dict(root_id=name, action_components={action: [utilities[action], 0., 0.] for action in legal})
    return root, label


def problem(*cases):
    return core.build_problem([row[0] for row in cases], [row[1] for row in cases])


def assert_dual(node):
    weights = [(entry['constraint_index'], Fraction(entry['weight'])) for entry in node['dual']['support']]
    assert all(weight >= 0 for _, weight in weights)
    assert [sum(weight*Fraction(node['constraints'][index]['a'][column]) for index, weight in weights)
            for column in range(7)] == [0]*6+[1]
    assert sum(weight*Fraction(node['constraints'][index]['b']) for index, weight in weights) == Fraction(node['dual']['upper_bound'])


def test_alias_representatives_use_observable_reward_and_keep_all_true_optimal_representatives():
    data = problem(case('alias', dict(DOWN=VACANCY, LEFT=VACANCY, RIGHT=ZERO),
                        dict(DOWN=9., LEFT=1., RIGHT=1.), dict(LEFT=1/2048)))
    row = data['roots'][0]
    assert [group['representative'] for group in row['classes']] == ['LEFT', 'RIGHT']
    assert row['classes'][0]['actions'] == ['DOWN', 'LEFT']
    assert row['classes'][0]['immediate_reward_fraction'] == '1/2048'
    assert row['optimal_actions'] == ['LEFT', 'RIGHT'] and row['suboptimal_actions'] == []
    result = core.solve_capacity(data)
    assert result['status'] == 'strict_feasible' and result['witness']['margin'] == '1'
    assert result['costs']['lp_solves'] == 1


def test_beta_is_unbounded_and_exact_witness_beats_the_known_first_reward_offset():
    data = problem(case('large_beta', dict(DOWN=VACANCY, LEFT=ZERO), dict(DOWN=10., LEFT=8.), dict(LEFT=8.)))
    result = core.solve_capacity(data)
    assert result['status'] == 'strict_feasible'
    assert Fraction(result['witness']['beta'][1]) >= 9
    assert result['witness']['evaluation']['root_records'][0]['chosen'] == 'DOWN'
    assert Fraction(result['witness']['margin']) > Fraction(core.EPSILON)
    assert_dual(result['nodes'][0])


def test_multiple_optimal_alternatives_avoid_false_canonical_infeasibility():
    data = problem(
        case('a_unique', dict(DOWN=VACANCY, LEFT=ZERO), dict(DOWN=2., LEFT=1.), dict(LEFT=1.)),
        case('b_multiple', dict(DOWN=ZERO, LEFT=[0, 2, 0, 0, 0, 0], RIGHT=VACANCY),
             dict(DOWN=2., LEFT=2., RIGHT=1.)))
    result = core.solve_capacity(data)
    assert result['status'] == 'strict_feasible' and result['costs']['lp_solves'] == 1
    assert result['witness']['evaluation']['root_records'][1]['chosen'] == 'LEFT'
    assert data['roots'][1]['optimal_actions'] == ['DOWN', 'LEFT']
    assert not any(row['root_id'] == 'b_multiple' for row in result['nodes'][0]['constraints'])


def test_first_violated_disjunction_branches_in_actions_order_and_stops_after_positive_certificate():
    data = problem(case('ambiguous', dict(DOWN=[0, 2, 0, 0, 0, 0], LEFT=ZERO, RIGHT=VACANCY),
                        dict(DOWN=2., LEFT=2., RIGHT=1.)))
    result = core.solve_capacity(data)
    parent, child = result['nodes']
    assert result['status'] == 'strict_feasible' and result['costs']['lp_solves'] == 2
    assert parent['branch_root_id'] == 'ambiguous' and parent['branch_actions'] == ['DOWN', 'LEFT']
    assert parent['children'] == [1] and parent['unexplored_actions'] == ['LEFT']
    assert child['assigned'] == [dict(root_id='ambiguous', best_action='DOWN')]
    assert child['disposition'] == 'strict_witness'
    for node in result['nodes']:
        assert_dual(node)


def test_negative_conclusion_covers_both_optimal_branches_with_small_exact_duals():
    data = problem(
        case('a', dict(DOWN=VACANCY, LEFT=ZERO), dict(DOWN=2., LEFT=1.), dict(LEFT=1.)),
        case('b', dict(DOWN=ROW_PAIR, LEFT=ZERO), dict(DOWN=2., LEFT=1.), dict(LEFT=1.)),
        case('z', dict(DOWN=ROW_PAIR, LEFT=VACANCY, RIGHT=[0, 1, 1, 0, 0, 0]),
             dict(DOWN=2., LEFT=2., RIGHT=0.)))
    result = core.solve_capacity(data)
    assert result['status'] == 'weak_infeasible' and result['upper_bound'] == '-1/2'
    assert result['witness'] is None and result['weak_witness'] is None
    assert result['costs']['lp_solves'] == result['costs']['symbolic_balance_solves'] == 3
    assert result['nodes'][0]['children'] == [1, 2] and result['nodes'][0]['unexplored_actions'] == []
    assert [node['assigned'][-1]['best_action'] for node in result['nodes'][1:]] == ['DOWN', 'LEFT']
    for node in result['nodes'][1:]:
        assert node['disposition'] == 'pruned_negative'
        assert len(node['dual']['support']) == 2
        assert_dual(node)


def test_zero_margin_does_not_claim_impossibility_or_attainable_exact_tied_policy():
    data = problem(
        case('a', dict(DOWN=VACANCY, LEFT=ZERO), dict(DOWN=1., LEFT=0.)),
        case('b', dict(DOWN=VACANCY, LEFT=ZERO), dict(DOWN=0., LEFT=1.)))
    result = core.solve_capacity(data)
    assert result['status'] == 'no_positive_margin' and result['upper_bound'] == '0'
    assert result['weak_witness']['evaluation']['all_weak']
    assert not result['weak_witness']['evaluation']['all_optimal']
    assert result['weak_witness']['evaluation']['root_records'][1]['chosen'] == 'DOWN'
    assert_dual(result['nodes'][0])


def test_zero_boundary_can_have_an_actual_optimal_lexical_policy():
    data = problem(
        case('a', dict(DOWN=VACANCY, LEFT=ZERO), dict(DOWN=1., LEFT=0.)),
        case('b', dict(DOWN=ZERO, LEFT=VACANCY), dict(DOWN=1., LEFT=0.)))
    result = core.solve_capacity(data)
    assert result['status'] == 'no_positive_margin'
    assert result['weak_witness']['evaluation']['all_optimal']
    assert result['weak_witness']['evaluation']['all_weak']


def test_zero_relaxation_bound_with_violated_unassigned_root_does_not_invent_a_weak_witness():
    data = problem(
        case('a', dict(DOWN=VACANCY, LEFT=ZERO), dict(DOWN=1., LEFT=0.)),
        case('b', dict(DOWN=ZERO, LEFT=VACANCY), dict(DOWN=1., LEFT=0.)),
        case('z', dict(DOWN=VACANCY, LEFT=[0, 2, 0, 0, 0, 0], RIGHT=ZERO),
             dict(DOWN=2., LEFT=2., RIGHT=1.), dict(RIGHT=1.)))
    result = core.solve_capacity(data)
    assert result['status'] == 'no_positive_margin' and result['weak_witness'] is None
    assert result['costs']['lp_solves'] == 1 and result['nodes'][0]['disposition'] == 'pruned_zero'


def test_evaluation_keeps_complete_vector_and_exact_score_gap_without_deploying_beta():
    root, label = case('vector', dict(DOWN=VACANCY, LEFT=ZERO), dict(DOWN=1., LEFT=0.))
    label['action_components'] = dict(DOWN=[.5, .25, .75], LEFT=[.5, .5, .5])
    data = problem((root, label))
    evaluation = core.evaluate_beta(data, ['0', '1/2048', '0', '0', '0', '0'])
    row = evaluation['root_records'][0]
    assert row['chosen'] == 'DOWN' and row['chosen_components'] == [.5, .25, .75]
    assert row['chosen_utility'] == 1. and row['optimal_vs_bad_gap'] == '1/2048'
    assert evaluation['all_optimal'] and evaluation['all_weak']


def test_native_solver_failure_is_engineering_error_with_paid_attempt_not_negative_capacity(monkeypatch):
    data = problem(case('source', dict(DOWN=VACANCY, LEFT=ZERO), dict(DOWN=1., LEFT=0.)))
    monkeypatch.setattr(core, 'linprog', lambda *args, **kwargs:
        SimpleNamespace(success=False, status=2, message='synthetic native failure', nit=0))
    with pytest.raises(core.CapacityExecutionError) as caught:
        core.solve_capacity(data)
    record = caught.value.record
    assert record['status'] == 'execution_error' and record['costs']['lp_solves'] == 1
    assert record['witness'] is None and record['upper_bound'] is None
    assert record['nodes'][0]['native_lp']['status'] == 2
