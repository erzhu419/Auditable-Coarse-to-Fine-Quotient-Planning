"""Legal-pair integration with the unmodified external reference implementation."""

from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
import pytest

AUTHOR_CODE = Path(__file__).resolve().parents[2] / "acfqp-rate-distortion-reference-v39-source" / "code"
if not AUTHOR_CODE.is_dir():
    pytest.skip("V39 requires the retained author reference checkout", allow_module_level=True)
sys.path.insert(0, str(AUTHOR_CODE))
from core import abstraction as AB, planning as PL, analysis as AN
from exp4_sysadmin import sysadmin_mdp as METRIC

from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome
from acfqp.science.rate_distortion_2048_v39 import (
    ACTION_LABELS, adapter_from_closure, build_exact_2048_adapter,
    author_bellman_update, author_fixed_point_distortion, embed_author_abstraction,
    evaluate_original_policy, exact_original_solution, fit_author_abstraction,
    greedy_legal_policy,
)


@pytest.mark.parametrize("case,original,states,pairs", [
    ("last_pair_spawn_risk", 9, 3, 5),
    ("dense_merge_choice", 202, 18, 65),
    ("adjacent_1024_goal", 43, 4, 8),
])
def test_complete_public_models_preserve_legal_rows_and_terminal_policy_values(case, original, states, pairs):
    adapter = build_exact_2048_adapter(case, AB)
    assert len(adapter.closure.model.layers) == original
    assert adapter.mdp.num_states == states
    assert adapter.num_valid_pairs == pairs == len(adapter.closure.model.rows) + 1
    np.testing.assert_allclose(adapter.mdp.transitions.sum(axis=2), 1., atol=1e-14)
    assert not adapter.legal_mask[:-1, -1].any()
    assert adapter.legal_mask[-1].tolist() == [False, False, False, False, True]
    for (source, action), outcomes in adapter.closure.model.rows.items():
        s, a = adapter.source_to_state[source], ACTION_LABELS.index(action)
        assert adapter.legal_mask[s, a]
        assert adapter.mdp.rewards[s, a] == pytest.approx(sum(o.probability * o.reward for o in outcomes))
        for target in range(states):
            expected = sum(o.probability for o in outcomes if adapter.source_to_state[o.next_state] == target)
            assert adapter.mdp.transitions[s, a, target] == pytest.approx(expected)
    for s in range(states):
        first = np.flatnonzero(adapter.legal_mask[s])[0]
        for a in range(adapter.mdp.num_actions):
            representative = a if adapter.legal_mask[s, a] else first
            assert adapter.rectangular_alias_indices[s * 5 + a] == s * 5 + representative
    exact = exact_original_solution(adapter)
    np.testing.assert_allclose(PL.solve_optimal_values(adapter.mdp), exact["tabular_state_values"], atol=1e-13)
    assert AN.evaluate_policy_value_exact(adapter.mdp, exact["policy"]) == pytest.approx(exact["mean_tabular_state_value"])
    assert evaluate_original_policy(adapter, exact["policy"])["root_values"] == exact["root_values"]
    # Scaling the planning units leaves the original unscaled evaluation intact.
    scaled = replace(adapter.mdp, rewards=adapter.mdp.rewards * 3.7)
    assert AN.evaluate_policy_value_exact(scaled, exact["policy"]) / 3.7 == pytest.approx(exact["mean_tabular_state_value"])


def test_illegal_slots_cannot_win_readout_or_execute_even_when_tied():
    adapter = build_exact_2048_adapter("last_pair_spawn_risk", AB)
    values = np.zeros_like(adapter.mdp.rewards)
    values[~adapter.legal_mask] = 1e6
    chosen = greedy_legal_policy(adapter, values)
    assert chosen.tolist() == [int(np.flatnonzero(row)[0]) for row in adapter.legal_mask]
    invalid = chosen.copy()
    invalid[0] = len(ACTION_LABELS) - 1
    with pytest.raises(ValueError, match="illegal computation slot"):
        evaluate_original_policy(adapter, invalid)


def test_alias_bellman_and_identity_embedding_preserve_arbitrary_negative_legal_q():
    adapter = build_exact_2048_adapter("last_pair_spawn_risk", AB)
    legal_q = np.linspace(-7., -1., adapter.num_valid_pairs)
    by_state = np.full(adapter.legal_mask.shape, -np.inf)
    by_state.reshape(-1)[adapter.valid_pair_indices] = legal_q
    expected = adapter.mdp.rewards + adapter.mdp.gamma * np.einsum("sak,k->sa", adapter.mdp.transitions, by_state.max(axis=1))
    np.testing.assert_allclose(author_bellman_update(adapter, legal_q, PL), expected.reshape(-1)[adapter.valid_pair_indices])
    identity = np.eye(adapter.num_valid_pairs)
    direct = AB.StateActionAbstraction(1., identity, identity, np.arange(adapter.num_valid_pairs), identity, np.arange(adapter.num_valid_pairs))
    embedded = embed_author_abstraction(adapter, direct, AB)
    assert not embedded.posterior[~adapter.legal_mask.reshape(-1)].any()
    np.testing.assert_array_equal(embedded.decoder, adapter.valid_pair_indices)
    np.testing.assert_allclose(PL.abstract_state_action_bellman_update(adapter.mdp, embedded, legal_q), author_bellman_update(adapter, legal_q, PL))
    np.testing.assert_allclose(PL.solve_optimal_abstract_q(adapter.mdp, embedded), exact_original_solution(adapter)["legal_q"], atol=1e-13)


def test_original_ba_uses_legal_prior_and_only_legal_decoder_support():
    adapter = build_exact_2048_adapter("last_pair_spawn_risk", AB)
    distance = np.abs(np.arange(adapter.num_valid_pairs)[:, None] - np.arange(adapter.num_valid_pairs)[None, :]).astype(float)
    fitted = fit_author_abstraction(adapter, distance, AB, beta=1., num_abstract=3, max_outer=2, max_inner=3)
    reference = AB.fit_soft_abstraction(distance, adapter.uniform_legal_prior, beta=1., num_abstract=3, max_outer=2, max_inner=3, tolerance=1e-6, solver_kind="flat")
    np.testing.assert_array_equal(fitted.encoder, reference.encoder)
    np.testing.assert_array_equal(fitted.decoder, reference.decoder)
    assert fitted.encoder.shape[0] == adapter.num_valid_pairs
    embedded = embed_author_abstraction(adapter, fitted, AB)
    assert set(embedded.decoder).issubset(set(adapter.valid_pair_indices))
    np.testing.assert_allclose(embedded.encoder, fitted.encoder[adapter.rect_to_valid_pair])
    values = np.arange(fitted.num_abstract, dtype=float) - 5.
    legal_grounded = AB.ground_state_action_abstract_q(fitted, values)
    expected = author_bellman_update(adapter, legal_grounded, PL)[fitted.decoder]
    np.testing.assert_allclose(PL.abstract_state_action_bellman_update(adapter.mdp, embedded, values), expected)


def test_author_wasserstein_preserves_stochastic_probability_difference():
    model = FiniteModel(layers={0: 2, 1: 1, 2: 1, 3: 0}, terminal={0: "ACTIVE", 1: "ACTIVE", 2: "LOST", 3: "CUTOFF"}, roots=(0,), rows={
        (0, "DOWN"): (Outcome(.75, 1, 0.), Outcome(.25, 2, 0.)),
        (0, "LEFT"): (Outcome(.25, 1, 0.), Outcome(.75, 2, 0.)),
        (1, "UP"): (Outcome(1., 3, 1.),),
    })
    closure = DevelopmentClosure(model, {s: (s,) * 16 for s in model.layers}, ("stochastic",), {}, 0.)
    adapter = adapter_from_closure(closure, AB)
    distance = author_fixed_point_distortion(adapter, METRIC)
    assert distance.shape == (4, 4)
    # Child vs terminal value distance is exactly 1; transport only half its mass.
    # Replacing either row by its modal successor would incorrectly produce .95.
    assert distance[0, 1] == pytest.approx(.95 * .5, abs=1e-12)
    np.testing.assert_allclose(distance, distance.T, atol=1e-13)
    np.testing.assert_array_equal(np.diag(distance), 0.)
