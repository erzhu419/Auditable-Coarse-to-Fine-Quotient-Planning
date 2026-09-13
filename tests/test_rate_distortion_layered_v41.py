"""Small synthetic checks for layer isolation and reward-unit policy readout."""
from dataclasses import replace
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

AUTHOR_CODE = Path(__file__).resolve().parents[2] / "acfqp-rate-distortion-reference-v39-source" / "code"
if not AUTHOR_CODE.is_dir():
    pytest.skip("V41 requires the retained author reference checkout", allow_module_level=True)
sys.path.insert(0, str(AUTHOR_CODE))
from core import abstraction as AB, planning as PL

from acfqp.science.controlled_predictive_2048_v1 import DevelopmentClosure
from acfqp.science.controlled_predictive_quotient_v1 import FiniteModel, Outcome
from acfqp.science.rate_distortion_2048_v39 import adapter_from_closure, embed_author_abstraction
from acfqp.science.rate_distortion_compiled_v40 import compile_operator
from acfqp.science.rate_distortion_layered_v41 import fit_layered_abstraction, layer_inventory, stable_legal_policy


def fixture():
    model = FiniteModel(
        layers={0: 2, 1: 1, 2: 1, 3: 0},
        terminal={0: "ACTIVE", 1: "ACTIVE", 2: "ACTIVE", 3: "CUTOFF"},
        roots=(0,), rows={
            (0, "DOWN"): (Outcome(.75, 1, .2), Outcome(.25, 2, .2)),
            (0, "LEFT"): (Outcome(.25, 1, .3), Outcome(.75, 2, .3)),
            (1, "DOWN"): (Outcome(1., 3, .1),),
            (1, "UP"): (Outcome(1., 3, .2),),
            (2, "LEFT"): (Outcome(1., 3, .4),),
            (2, "RIGHT"): (Outcome(1., 3, 0.),),
        },
    )
    closure = DevelopmentClosure(model, {s: (s,) * 16 for s in model.layers}, ("synthetic",), {}, 0.)
    adapter = adapter_from_closure(closure, AB)
    distance = np.abs(np.arange(7)[:, None] - np.arange(7)[None, :]).astype(float)
    return adapter, distance


def test_original_ba_calls_use_layer_prior_global_pruning_and_correct_active_full_mappings():
    adapter, distance = fixture()
    calls = []

    def fit(**kwargs):
        calls.append(kwargs)
        n = kwargs["num_abstract"]
        # Different active/full widths expose indexing mistakes hidden by no pruning.
        return AB.StateActionAbstraction(
            kwargs["beta"], np.ones((n, 1)), np.full((n, 1), 1. / n),
            np.asarray([n - 1]), np.eye(n), np.arange(n - 1, -1, -1),
        )

    author = SimpleNamespace(fit_soft_abstraction=fit, StateActionAbstraction=AB.StateActionAbstraction)
    result = fit_layered_abstraction(adapter, distance, author, beta=8.)
    groups = [np.asarray([2, 3, 4, 5]), np.asarray([0, 1])]
    assert len(calls) == 2
    assert sum(call["num_abstract"] for call in calls) + 1 == adapter.num_valid_pairs
    for call, group in zip(calls, groups, strict=True):
        np.testing.assert_array_equal(call["distortion"], distance[np.ix_(group, group)])
        np.testing.assert_array_equal(call["mu"], np.full(group.size, 1. / group.size))
        assert call["prune_mass_threshold"] == pytest.approx(1e-4 * 7 / group.size)
        assert call["beta"] == 8. and call["max_outer"] == 200 and call["max_inner"] == 50
        assert call["tolerance"] == 1e-6 and call["solver_kind"] == "flat"
        assert "encoder_init" not in call and "decoder_init" not in call
    np.testing.assert_array_equal(result.decoder, [5, 1, 6])
    np.testing.assert_array_equal(result.full_decoder, [5, 4, 3, 2, 1, 0, 6])
    expected_encoder = np.zeros((7, 3))
    expected_encoder[[2, 3, 4, 5], 0] = 1.
    expected_encoder[[0, 1], 1] = 1.
    expected_encoder[6, 2] = 1.
    np.testing.assert_array_equal(result.encoder, expected_encoder)
    expected_full = np.zeros((7, 7))
    expected_full[[2, 3, 4, 5, 0, 1, 6], np.arange(7)] = 1.
    np.testing.assert_array_equal(result.full_encoder, expected_full)
    np.testing.assert_allclose(result.posterior.sum(axis=0), 1.)
    inventory = layer_inventory(adapter, result)
    assert inventory["layers"] == [1, 2, -1]
    assert inventory["pair_count_by_layer"] == {"1": 4, "2": 2, "-1": 1}
    assert inventory["code_count_by_layer"] == {"1": 1, "2": 1, "-1": 1}
    assert inventory["full_code_count_by_layer"] == {"1": 4, "2": 2, "-1": 1}
    assert inventory["cross_layer_mass_max"] == inventory["full_cross_layer_mass_max"] == inventory["posterior_block_mass_max"] == 0.
    assert inventory["terminal_row_pure"] and inventory["terminal_code_unique"] and inventory["decoder_layer_consistent"]
    damaged = result.encoder.copy()
    damaged[0] = [1., 0., 0.]
    assert layer_inventory(adapter, replace(result, encoder=damaged))["cross_layer_mass_max"] == 1.


def test_actual_author_layered_fit_keeps_terminal_zero_and_h2_stable_after_two_backups():
    adapter, distance = fixture()
    result = fit_layered_abstraction(adapter, distance, AB, beta=1.3)
    inventory = layer_inventory(adapter, result)
    assert inventory["cross_layer_mass_max"] == inventory["posterior_block_mass_max"] == 0.
    assert inventory["terminal_row_pure"] and inventory["terminal_code_unique"]
    assert result.solver_kind == "flat"
    # Conditional posteriors equal the global uniform-pair posterior after embedding.
    prior = adapter.uniform_legal_prior
    expected_posterior = prior[:, None] * result.encoder / (prior @ result.encoder)[None, :]
    np.testing.assert_allclose(result.posterior, expected_posterior, rtol=0., atol=1e-13)
    embedded = embed_author_abstraction(adapter, result, AB)
    operator = compile_operator(adapter, result)
    states = [np.zeros(result.num_abstract)]
    for _ in range(3):
        states.append(operator.backup(states[-1]))
        expected = PL.abstract_state_action_bellman_update(adapter.mdp, embedded, states[-2])
        np.testing.assert_allclose(states[-1], expected, rtol=0., atol=1e-13)
    terminal_code = inventory["terminal_code_index"]
    assert [float(u[terminal_code]) for u in states] == [0., 0., 0., 0.]
    np.testing.assert_array_equal(states[2], states[3])
    assert np.any(states[1] != states[2])


@pytest.mark.parametrize("scale", [1., .001, 137.])
def test_stable_readout_has_original_unit_tolerance_and_never_selects_illegal_action(scale):
    adapter, _ = fixture()
    values = np.zeros_like(adapter.mdp.rewards)
    values[0, 1] = .75e-12
    values[1, 3] = .75e-12
    values[2, 2] = 1.25e-12
    values[~adapter.legal_mask] = 1e6
    before = values.copy()
    policy = stable_legal_policy(adapter, values * scale, reward_scale=scale)
    np.testing.assert_array_equal(policy, [0, 0, 2, 4])
    np.testing.assert_array_equal(values, before)
    strict = stable_legal_policy(adapter, values * scale, reward_scale=scale, tie_tolerance=0.)
    np.testing.assert_array_equal(strict, [1, 3, 2, 4])
    # The author operator continues to use the exact max, not this readout tolerance.
    backed_up = PL.bellman_update(adapter.mdp, np.where(adapter.legal_mask, values, 0.).reshape(-1))
    assert backed_up[0] == .2 + .95 * (.75 * .75e-12 + .25 * 1.25e-12)
