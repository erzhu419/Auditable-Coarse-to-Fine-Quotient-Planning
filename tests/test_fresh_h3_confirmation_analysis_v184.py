"""Small deterministic integration cases; no real fresh seeds or compiler calls."""
from copy import deepcopy
from fractions import Fraction

import pytest
from scripts import analyze_controlled_predictive_fresh_h3_confirmation_v184 as audit


def test_h1_goal_and_loss_precede_cutoff_and_first_reward_is_counted_once():
    won = (10, 10, 0, 0)+tuple([0]*12)
    teacher = [dict(board=list(won), horizon=1, action='LEFT')]
    evaluator = audit.FrozenTeacherEvaluator(teacher)
    label = evaluator.root_label(won, 1)
    assert label['action_component_fractions']['LEFT'] == [[1, 1], [0, 1], [1, 1]]
    assert evaluator.value((11,)+tuple([0]*15), 0) == (0, 0, 1)
    lost = tuple([1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1])
    assert evaluator.value(lost, 0) == (0, 1, 0)
    assert evaluator.value((1,)+tuple([0]*15), 0) == (0, 0, 0)
    small = (1, 1, 0, 0)+tuple([0]*12)
    tiny = audit.FrozenTeacherEvaluator([dict(board=list(small), horizon=1, action='LEFT')])
    assert tiny.action_value(small, 1, 'LEFT') == (Fraction(1, 512), 0, 0)


def test_h2_saved_teacher_exact_spawn_probabilities_and_missing_binding():
    board = (1, 1, 0, 0)+tuple([0]*12)
    policy = {(board, 2): 'LEFT'}
    mechanics = audit.FrozenTeacherEvaluator([])
    for after, _ in mechanics.classify(board)[1].values():
        for cell, value in enumerate(after):
            if value != 0:
                continue
            for rank in (1, 2):
                child = list(after); child[cell] = rank; child = tuple(child)
                status, legal = mechanics.classify(child)
                if status == 'ACTIVE':
                    # The continuation is fixed, not selected using future values.
                    policy[child, 1] = 'LEFT' if 'LEFT' in legal else 'DOWN' if 'DOWN' in legal else next(iter(legal))
    rows = [dict(board=list(state), horizon=h, action=action) for (state, h), action in policy.items()]
    evaluator = audit.FrozenTeacherEvaluator(rows)
    assert evaluator.action_value(board, 2, 'LEFT') == (Fraction(27, 12800), 0, 0)
    assert evaluator.root_label(board, 2)['continuation_components'][0] == float(Fraction(27, 12800))
    damaged = deepcopy(rows)
    needed = list(audit.swipe(board, 'LEFT')[0]); needed[1] = 1
    damaged = [row for row in damaged if not (row['horizon'] == 1 and row['board'] == needed)]
    with pytest.raises(ValueError, match='continuation observation is missing'):
        audit.FrozenTeacherEvaluator(damaged).action_value(board, 2, 'LEFT')
    with pytest.raises(ValueError, match='Duplicate'):
        audit.FrozenTeacherEvaluator(rows+[rows[0]])
    with pytest.raises(ValueError, match='legal and ACTIVE'):
        audit.FrozenTeacherEvaluator([dict(board=list(board), horizon=2, action='UP')]).value(board, 2)


def test_replica_effect_full_vector_regret_and_gain_concentration_are_independent():
    roots, labels = [], []
    choices = {name: [] for name in (*audit.MODEL_NAMES, 'FALLBACK')}
    for index, (replica, gain) in enumerate(((0, 4.), (0, -1.), (1, -1.))):
        identity = f'synthetic:{index}'
        roots.append(dict(root_id=identity, replica=replica, stratum=index, legal_actions=['DOWN', 'LEFT']))
        labels.append(dict(root_id=identity, action_components=dict(DOWN=[1., 1., 0.], LEFT=[gain-.5, 0., .5])))
        for name, rows in choices.items():
            rows.append(dict(root_id=identity, canonical_action='LEFT' if name == 'RIDGE' else 'DOWN', fallback=False,
                decision=dict(coverage={'LEFT': dict(total_tokens=40, known_tokens=39, unknown_tokens=1)})))
    result = audit.summarize(roots, labels, choices)
    contrast = result['comparisons']['RIDGE_MINUS_ONE']
    assert contrast['utility'] == pytest.approx(2/3)
    assert contrast['components'] == pytest.approx([-5/6, -1., .5])
    assert (contrast['resolved_error_roots'], contrast['new_error_roots']) == (1, 2)
    assert (contrast['positive_gain_sum'], contrast['negative_gain_sum']) == (4., -2.)
    assert contrast['largest_gain_share_of_positive'] == 1.
    assert result['whole_cohort_positive_vs_one_and_shared']
    assert not result['all_replicas_positive_vs_one_and_shared']
    assert [row['comparisons']['RIDGE_MINUS_ONE']['utility'] for row in result['replicas']] == [1.5, -1.]
    assert result['feature_coverage'] == dict(total_tokens=120, known_tokens=117, unknown_tokens=3)
