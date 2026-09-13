"""The observed H1 mask, terminal values, signed identities and fixed rankings."""

from copy import deepcopy

import pytest

from acfqp.science.controlled_predictive_continuation_sources_v37 import evaluate_continuation_sources, margin
from acfqp.science.controlled_predictive_decomposition_v19 import ExactOracle
from acfqp.science.controlled_predictive_score_cache_v18 import CachedGapPlannerState
from acfqp.science.controlled_predictive_quotient_v1 import Query
from test_controlled_predictive_decomposition_v19 import ROOT, A, B, END, analytic_fixture

ACTIONS = ('DOWN', 'LEFT', 'RIGHT', 'UP')
LOST = (1, tuple(1 + (i + i // 4) % 2 for i in range(16)))
WON = (1, (11,) + (0,) * 15)
LOST0, WON0 = (0, LOST[1]), (0, WON[1])


def test_all_observed_has_zero_coverage_and_state_is_unchanged(monkeypatch):
    state, oracle = analytic_fixture()
    state.observe_batch(ROOT, 'DOWN', ((1., A, 0.),))
    state.observe_batch(ROOT, 'UP', ((1., A, 0.),))
    before = deepcopy(state.__dict__)
    def forbidden(*args, **kwargs):
        pytest.fail('a diagnostic changed the retained observation mask')
    monkeypatch.setattr(type(state), 'observe_batch', forbidden)
    result = evaluate_continuation_sources(state, 'q', ROOT, oracle)
    assert state.__dict__ == before
    diag = result['diagnostic']
    assert all(row['C_coverage_error'] == 0 for row in diag['actions'].values())
    assert diag['actions']['LEFT']['E_estimation_error'] == 2.
    assert diag['actions']['RIGHT']['E_estimation_error'] == 0.
    assert diag['actions']['LEFT']['E_estimation_error'] == diag['actions']['LEFT']['D_continuation_error']
    assert diag['modes']['REMOVE_E']['selected_action'] == 'RIGHT'
    assert diag['modes']['REMOVE_C']['selected_action'] == diag['modes']['RAW']['selected_action']
    assert diag['validation']['all_passed']
    assert diag['mask_counts']['mask_observed_exact_action_values'] == 8
    assert margin('LEFT', 'LEFT', diag['actions'])['E_estimation_error_difference'] == 0


def test_all_unknown_h1_keeps_structural_bounds_and_zero_estimation():
    _, oracle = analytic_fixture()
    state = CachedGapPlannerState(ROOT, {'q': Query(1., 1., 0.)})
    for action in ACTIONS:
        state.observe_batch(ROOT, action, ((1., A, 0.),))
    diag = evaluate_continuation_sources(state, 'q', ROOT, oracle)['diagnostic']
    assert diag['mask_counts']['mask_unobserved_structural_action_values'] == 4
    for row in diag['actions'].values():
        assert row['E_estimation_error'] == 0
        assert row['q_mask'] == row['q_hat'] == -1
        assert row['C_coverage_error'] == row['D_continuation_error'] == -3
    assert diag['modes']['REMOVE_E']['selected_action'] == 'DOWN'


def test_observed_h1_true_terminal_support_is_used_without_revealing_unknown_actions():
    state = CachedGapPlannerState(ROOT, {'q': Query(0., 2., 4.)})
    state.observe_batch(A, 'DOWN', ((1., WON0, 0.),))
    for action in ACTIONS:
        state.observe_batch(ROOT, action, ((1., A, 0.),))
    truth_rows = {(ROOT, action): ((1., A, 0.),) for action in ACTIONS}
    truth_rows.update({(A, action): ((1., WON0, 0.),) for action in ACTIONS})
    truth_rows[A, 'DOWN'] = ((.5, WON0, 0.), (.5, LOST0, 0.))
    oracle = ExactOracle({ROOT: 'ACTIVE', A: 'ACTIVE', WON0: 'WON', LOST0: 'LOST'}, truth_rows)
    original = deepcopy(state.__dict__)
    diag = evaluate_continuation_sources(state, 'q', ROOT, oracle)['diagnostic']
    assert state.__dict__ == original and LOST0 not in state.profiles
    for row in diag['actions'].values():
        assert row['q_hat'] == 4 and row['q_mask'] == 1 and row['q_star'] == 4
        assert row['E_estimation_error'] == 3 and row['C_coverage_error'] == -3
        assert row['D_continuation_error'] == 0
        assert row['mode_values']['REMOVE_E'] == 1
        assert row['mode_values']['REMOVE_C'] == row['q_hat_exact_continuation'] + 3 == 7
    assert diag['mask_counts']['mask_observed_exact_action_values'] == 1
    assert diag['mask_counts']['mask_unobserved_structural_action_values'] == 3


def test_all_terminal_children_keep_won_lost_cutoff_and_zero_e_c():
    cutoff = (1, END[1])
    # END's board is active at H1, so an actual terminal cutoff uses horizon 0
    # only in H1 rows; at the H2 root WON/LOST are the reachable terminal types.
    state = CachedGapPlannerState(ROOT, {'q': Query(2., 3., 5.)})
    rows = {}
    for action in ACTIONS:
        rows[ROOT, action] = ((.75, LOST, 1.), (.25, WON, 2.))
        state.observe_batch(ROOT, action, rows[ROOT, action])
    oracle = ExactOracle({ROOT: 'ACTIVE', LOST: 'LOST', WON: 'WON'}, rows)
    result = evaluate_continuation_sources(state, 'q', ROOT, oracle)['diagnostic']
    assert result['mask_counts']['mask_terminal_values'] == 2
    assert all(row['E_estimation_error'] == row['C_coverage_error'] == 0 for row in result['actions'].values())
    assert all(row['q_mask'] == row['q_hat'] == 1.5 for row in result['actions'].values())


def test_risk_zero_has_no_h1_estimation_or_coverage_error_with_deterministic_rewards():
    state = CachedGapPlannerState(ROOT, {'q': Query(1., 0., 0.)})
    state.observe_state(A)
    exact_rows = {}
    for action in ACTIONS:
        reward = state.profiles[A].reward(action)
        exact_rows[A, action] = ((.25, END, reward), (.75, WON0, reward))
        if action in ('DOWN', 'LEFT'):
            state.observe_batch(A, action, ((1., END, reward),))
        exact_rows[ROOT, action] = ((1., A, 0.),)
        state.observe_batch(ROOT, action, ((1., A, 0.),))
    oracle = ExactOracle({ROOT: 'ACTIVE', A: 'ACTIVE', END: 'CUTOFF', WON0: 'WON'}, exact_rows)
    diag = evaluate_continuation_sources(state, 'q', ROOT, oracle)['diagnostic']
    assert all(row['E_estimation_error'] == row['C_coverage_error'] == 0 for row in diag['actions'].values())


def test_unknown_root_disables_all_corrected_rankings_and_keeps_null_terms():
    state, oracle = analytic_fixture()
    diag = evaluate_continuation_sources(state, 'q', ROOT, oracle)['diagnostic']
    assert diag['modes']['RAW']['available']
    for mode in ('REMOVE_E', 'REMOVE_C'):
        assert not diag['modes'][mode]['available'] and diag['modes'][mode]['selected_action'] is None
    assert diag['actions']['UP']['E_estimation_error'] is diag['actions']['UP']['C_coverage_error'] is None
    assert len(diag['actions']) == 4 and len(diag['pair_margins']) == 6


def test_near_tie_modes_use_exact_values_while_correctness_keeps_original_tolerance():
    state = CachedGapPlannerState(ROOT, {'q': Query(1., 0., 0.)})
    rows = {(A, action): ((1., END, 1.),) for action in ACTIONS}
    for action in ACTIONS:
        state.observe_batch(A, action, rows[A, action])
        rows[ROOT, action] = ((1., A, 5e-11 if action == 'UP' else 0.),)
        state.observe_batch(ROOT, action, rows[ROOT, action])
    oracle = ExactOracle({ROOT: 'ACTIVE', A: 'ACTIVE', END: 'CUTOFF'}, rows)
    diag = evaluate_continuation_sources(state, 'q', ROOT, oracle)['diagnostic']
    assert diag['true_optimal_actions'] == list(ACTIONS) and diag['exact_reference_action'] == 'UP'
    assert all(row['selected_action'] == 'UP' and not row['wrong'] for row in diag['modes'].values())
