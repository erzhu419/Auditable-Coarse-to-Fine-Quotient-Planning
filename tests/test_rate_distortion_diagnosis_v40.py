"""Analytic discounted-chain identities, including terminal leakage and masking."""

import numpy as np
import pytest

from acfqp.science.rate_distortion_diagnosis_v40 import diagnose_roundtrip


def chain():
    transitions = np.zeros((3, 1, 3))
    transitions[0, 0, 1] = transitions[1, 0, 2] = transitions[2, 0, 2] = 1.
    return transitions, np.asarray([[0.], [1.], [0.]]), .5, np.ones((3, 1), dtype=bool), [2, 1, -1]


def test_soft_terminal_leak_gives_nonzero_root_bias_and_signed_resolvent_sources():
    P, r, gamma, legal, layers = chain()
    E = np.asarray([[1., 0.], [0., 1.], [.5, .5]])
    result = diagnose_roundtrip(P, r, gamma, E, [0, 1], [.8, 1.6], legal, layers, [0])
    np.testing.assert_allclose(result['abstract_residual'], [0., 0.], atol=1e-14)
    np.testing.assert_allclose(result['predicted_state_values'], [.8, 1.6, 1.2], atol=1e-14)
    np.testing.assert_allclose(result['actual_policy_values'], [.5, 1., 0.], atol=1e-14)
    np.testing.assert_allclose(result['root_bias'], [.3], atol=1e-14)
    assert result['terminal_predicted_values'] == pytest.approx([1.2])
    assert result['full_q_bellman_residual_inf'] == pytest.approx(.6)
    assert result['full_q_error_bound_inf'] == pytest.approx(1.2)
    assert result['source_layer_root_contributions']['H2'] == pytest.approx([0.])
    assert result['source_layer_root_contributions']['H1'] == pytest.approx([0.])
    assert result['source_layer_root_contributions']['TERMINAL'] == pytest.approx([.3])
    assert result['roundtrip_decoder_layer_root_contributions']['H2'] == pytest.approx([.05])
    assert result['roundtrip_decoder_layer_root_contributions']['H1'] == pytest.approx([.25])
    assert result['roundtrip_decoder_layer_root_contributions']['TERMINAL'] == pytest.approx([0.])
    assert result['decoder_layer_mixing_mass']['legal_rows'] == pytest.approx([0., 0., 1.])
    # This K is already a projection: idempotence alone does not certify value.
    assert result['roundtrip_kernel_idempotence_inf'] == 0
    assert result['identities']['all_passed']


def test_identity_encoder_has_no_reconstruction_bias_at_the_exact_fixed_point():
    P, r, gamma, legal, layers = chain()
    result = diagnose_roundtrip(P, r, gamma, np.eye(3), [0, 1, 2], [.5, 1., 0.], legal, layers, [0, 1])
    assert result['root_predicted_values'] == result['root_actual_values'] == [.5, 1.]
    assert result['root_bias'] == result['legal_roundtrip_term'][:2] == [0., 0.]
    assert result['full_q_bellman_residual_inf'] == result['full_q_error_bound_inf'] == 0
    assert result['decoder_layer_mixing_mass']['maximum_legal_row'] == 0
    assert result['roundtrip_kernel_idempotence_inf'] == 0


def test_nonconverged_iterate_keeps_iteration_term_and_signed_source_cancellation():
    P, r, gamma, legal, layers = chain()
    result = diagnose_roundtrip(P, r, gamma, np.eye(3), [0, 1, 2], [0., 0., 1.], legal, layers, [0])
    assert result['legal_roundtrip_term'] == [0., 0., 0.]
    assert result['abstract_residual'] == result['legal_iteration_term'] == [0., -1.5, .5]
    assert result['iteration_root_contribution'] == result['root_bias'] == [-.5]
    assert result['source_layer_root_contributions']['H1'] == [-.75]
    assert result['source_layer_root_contributions']['TERMINAL'] == [.25]
    assert result['full_q_bellman_residual_inf'] == 1.5
    assert result['full_q_error_bound_inf'] == 3.
    assert all(value == [0.] for value in result['roundtrip_decoder_layer_root_contributions'].values())


def test_masked_greedy_and_duplicate_decoder_kernel_norm_use_only_legal_rows():
    P, r, gamma, _, layers = chain()
    P, r = np.repeat(P, 2, axis=1), np.repeat(r, 2, axis=1)
    legal = np.asarray([[True, False], [False, True], [True, False]])
    legal_rows = np.flatnonzero(legal.reshape(-1))
    E = np.asarray([[.8, .1, .1], [0., 0., 1.], [0., 0., 1.], [.2, .3, .5], [.4, .4, .2], [0., 0., 1.]])
    decoder = np.asarray([0, 0, 3])
    original = E.copy()
    result = diagnose_roundtrip(P, r, gamma, E, decoder, [0., 0., 10.], legal, layers, [0])
    assert result['policy'] == [0, 1, 0]
    assert result['legal_row_indices'] == legal_rows.tolist()
    # Explicit K only in this tiny fixture verifies duplicate-column aggregation.
    L = np.zeros((3, 6)); L[np.arange(3), decoder] = 1.
    K = E @ L
    expected = np.max(np.abs(K @ K - K)[legal_rows].sum(axis=1))
    assert result['roundtrip_kernel_idempotence_inf'] == pytest.approx(expected)
    assert result['full_q_bellman_residual_inf'] == pytest.approx(max(abs(value) for value in result['legal_q_residual']))
    np.testing.assert_array_equal(E, original)


def test_nonstochastic_encoder_is_rejected_before_reporting_a_false_layer_identity():
    P, r, gamma, legal, layers = chain()
    E = np.eye(3); E[0, 0] = .9
    with pytest.raises(ValueError, match='probability distributions'):
        diagnose_roundtrip(P, r, gamma, E, [0, 1, 2], [.5, 1., 0.], legal, layers, [0])
