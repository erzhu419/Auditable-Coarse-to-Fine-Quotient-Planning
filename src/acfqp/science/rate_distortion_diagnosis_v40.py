"""Array-only signed diagnosis of a soft encoder/decoder Bellman round trip.

The fixed-policy resolvent attributes prediction bias exactly. Layer mixing
mass is descriptive; its magnitude alone is not a causal attribution.
"""
from __future__ import annotations

import numpy as np


TOLERANCE = 1e-10
LAYER_GROUPS = (('H2', 2), ('H1', 1), ('TERMINAL', -1))


def _maximum_absolute(values: np.ndarray) -> float:
    return float(np.max(np.abs(values), initial=0.))


def diagnose_roundtrip(P, r, gamma, E, decoder, u, legal_mask, state_layers, root_states) -> dict:
    """Decompose legal-Q residuals and the grounded greedy policy's value bias.

    Rows of E and entries of decoder use flattened rectangular (state,action)
    indices. Rectangular alias construction is the caller's responsibility.
    Absorbing states have layer -1 and retain a legal self-loop action. Exact
    argmax selects the lowest legal action index on a numerical tie.
    """
    P, r, E, u = (np.asarray(value, dtype=float) for value in (P, r, E, u))
    legal = np.asarray(legal_mask, dtype=bool)
    decoder = np.asarray(decoder)
    layers, roots = np.asarray(state_layers), np.asarray(root_states)
    if r.ndim != 2:
        raise ValueError('r must have shape (states, actions)')
    states, actions = r.shape
    rows = states * actions
    if (P.shape != (states, actions, states) or legal.shape != r.shape or
            E.ndim != 2 or E.shape[0] != rows or u.shape != (E.shape[1],) or
            decoder.shape != u.shape or layers.shape != (states,) or roots.ndim != 1):
        raise ValueError('inconsistent model, encoder, mask or root dimensions')
    if (not np.issubdtype(decoder.dtype, np.integer) or not np.issubdtype(roots.dtype, np.integer) or
            np.any((decoder < 0) | (decoder >= rows)) or np.any((roots < 0) | (roots >= states))):
        raise ValueError('decoder and roots must contain valid integer indices')
    if (not 0. <= gamma < 1. or not np.all(legal.any(axis=1)) or
            not np.all(np.isin(layers, [-1, 1, 2]))):
        raise ValueError('diagnosis requires discount below one, legal state actions and H2/H1/terminal layers')
    legal_rows = np.flatnonzero(legal.reshape(-1))
    if not np.all(legal.reshape(-1)[decoder]):
        raise ValueError('decoder representatives must be legal rows')
    if (not all(np.isfinite(value).all() for value in (P[legal], r[legal], E[legal_rows], u)) or
            np.any(P[legal] < 0.) or np.any(E[legal_rows] < 0.) or
            _maximum_absolute(P[legal].sum(axis=1) - 1.) > TOLERANCE or
            _maximum_absolute(E[legal_rows].sum(axis=1) - 1.) > TOLERANCE):
        raise ValueError('legal transition and encoder rows must be finite probability distributions')

    q = E @ u
    q_rectangle = q.reshape(states, actions)
    policy = np.argmax(np.where(legal, q_rectangle, -np.inf), axis=1)
    indices = np.arange(states)
    chosen_rows = indices * actions + policy
    y = q[chosen_rows]
    Fq = (r + gamma * np.einsum('sak,k->sa', P, y)).reshape(-1)
    delta = u - Fq[decoder]
    iteration = E @ delta
    roundtrip = E @ Fq[decoder] - Fq
    residual = q - Fq

    source_row_layers = np.repeat(layers, actions)
    decoder_layers = source_row_layers[decoder]
    roundtrip_by_decoder = np.column_stack([
        np.sum(E[:, decoder_layers == layer] * (Fq[decoder[decoder_layers == layer]][None, :] - Fq[:, None]), axis=1)
        for _, layer in LAYER_GROUPS])
    policy_transition = P[indices, policy]
    policy_reward = r[indices, policy]
    d = y - policy_reward - gamma * policy_transition @ y
    source_layer_residuals = np.column_stack([d * (layers == layer) for _, layer in LAYER_GROUPS])
    # One factorization carries the actual policy value and every signed source.
    system = np.eye(states) - gamma * policy_transition
    rhs = np.column_stack((policy_reward, d, source_layer_residuals, iteration[chosen_rows], roundtrip_by_decoder[chosen_rows]))
    propagated = np.linalg.solve(system, rhs)
    actual = propagated[:, 0]
    bias = y - actual
    source_contributions = propagated[:, 2:5]
    iteration_contribution = propagated[:, 5]
    roundtrip_contributions = propagated[:, 6:9]

    # K=EL can have duplicate destination columns. Group those columns before
    # taking its infinity norm; ||E E_decoder-E|| alone would overcount them.
    kernel_difference_by_code = E @ E[decoder] - E
    unique_decoder, inverse = np.unique(decoder, return_inverse=True)
    kernel_difference = np.zeros((rows, unique_decoder.size))
    for code, destination in enumerate(inverse):
        kernel_difference[:, destination] += kernel_difference_by_code[:, code]
    idempotence = float(np.max(np.sum(np.abs(kernel_difference[legal_rows]), axis=1), initial=0.))

    identity_errors = {
        'q_residual_iteration_plus_roundtrip': _maximum_absolute((residual - iteration - roundtrip)[legal_rows]),
        'roundtrip_decoder_layer_sum': _maximum_absolute((roundtrip - roundtrip_by_decoder.sum(axis=1))[legal_rows]),
        'policy_residual_matches_selected_q': _maximum_absolute(d - residual[chosen_rows]),
        'actual_policy_bellman_equation': _maximum_absolute(actual - policy_reward - gamma * policy_transition @ actual),
        'resolvent_bias': _maximum_absolute(bias - propagated[:, 1]),
        'source_layer_bias_sum': _maximum_absolute(bias - source_contributions.sum(axis=1)),
        'iteration_and_decoder_layer_bias_sum': _maximum_absolute(bias - iteration_contribution - roundtrip_contributions.sum(axis=1)),
    }
    if any(not np.isfinite(value) or value > TOLERANCE for value in identity_errors.values()):
        failed = ', '.join(name for name, value in identity_errors.items() if not np.isfinite(value) or value > TOLERANCE)
        raise ValueError('roundtrip diagnosis numerical identity exceeds 1e-10: ' + failed)

    mixing = np.sum(E * (source_row_layers[:, None] != decoder_layers[None, :]), axis=1)
    mass_by_decoder = {name: np.sum(E[:, decoder_layers == layer], axis=1) for name, layer in LAYER_GROUPS}
    terminal = np.flatnonzero(layers == -1)
    residual_inf = _maximum_absolute(residual[legal_rows])
    terminal_rows = legal_rows[source_row_layers[legal_rows] == -1]
    return {
        'policy': policy.tolist(), 'legal_row_indices': legal_rows.tolist(),
        'legal_q': q[legal_rows].tolist(), 'legal_bellman_q': Fq[legal_rows].tolist(),
        'legal_q_residual': residual[legal_rows].tolist(), 'abstract_residual': delta.tolist(),
        'abstract_residual_inf': _maximum_absolute(delta),
        'legal_iteration_term': iteration[legal_rows].tolist(), 'legal_roundtrip_term': roundtrip[legal_rows].tolist(),
        'full_q_bellman_residual_inf': residual_inf, 'full_q_error_bound_inf': residual_inf / (1. - gamma),
        'roundtrip_kernel_idempotence_inf': idempotence,
        'predicted_state_values': y.tolist(), 'actual_policy_values': actual.tolist(), 'state_bias': bias.tolist(),
        'policy_bellman_residual': d.tolist(),
        'terminal_states': terminal.tolist(), 'terminal_predicted_values': y[terminal].tolist(),
        'terminal_legal_row_indices': terminal_rows.tolist(), 'terminal_legal_q': q[terminal_rows].tolist(),
        'root_states': roots.tolist(), 'root_predicted_values': y[roots].tolist(),
        'root_actual_values': actual[roots].tolist(), 'root_bias': bias[roots].tolist(),
        'source_layer_root_contributions': {name: source_contributions[roots, index].tolist() for index, (name, _) in enumerate(LAYER_GROUPS)},
        'iteration_root_contribution': iteration_contribution[roots].tolist(),
        'roundtrip_decoder_layer_root_contributions': {name: roundtrip_contributions[roots, index].tolist() for index, (name, _) in enumerate(LAYER_GROUPS)},
        'legal_roundtrip_by_decoder_layer': {name: roundtrip_by_decoder[legal_rows, index].tolist() for index, (name, _) in enumerate(LAYER_GROUPS)},
        'decoder_layer_mixing_mass': {
            'legal_rows': mixing[legal_rows].tolist(), 'mean_legal_row': float(np.mean(mixing[legal_rows])),
            'maximum_legal_row': float(np.max(mixing[legal_rows])),
            'selected_policy_states': mixing[chosen_rows].tolist(), 'selected_roots': mixing[chosen_rows][roots].tolist(),
            'by_source_layer': {name: {'legal_row_count': int(np.sum(source_row_layers[legal_rows] == layer)),
                'mean_cross_layer_mass': float(np.mean(mixing[legal_rows[source_row_layers[legal_rows] == layer]])) if np.any(source_row_layers[legal_rows] == layer) else None}
                for name, layer in LAYER_GROUPS},
            'by_decoder_layer_legal_rows': {name: value[legal_rows].tolist() for name, value in mass_by_decoder.items()}},
        'identities': {'all_passed': True, 'maximum_absolute_residual': max(identity_errors.values()), **identity_errors},
        'scope': 'Legal-row Bellman residual bounds full Q error by contraction. Signed fixed-policy resolvent terms explain grounded selected-value minus actual policy-value bias. Source-state layers and decoder-representative layers are different decompositions; decoder-layer contributions sum to roundtrip bias, and the iteration contribution is retained separately. Cross-layer mixing mass is descriptive and does not by itself establish a causal mechanism.',
    }
