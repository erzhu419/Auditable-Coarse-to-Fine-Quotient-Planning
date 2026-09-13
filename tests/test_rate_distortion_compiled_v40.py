"""Compiled decoder backups preserve the author operator without model reads."""
from dataclasses import fields, replace
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

AUTHOR_CODE = Path(__file__).resolve().parents[2] / "acfqp-rate-distortion-reference-v39-source" / "code"
if not AUTHOR_CODE.is_dir():
    pytest.skip("V40 equivalence tests require the retained author reference checkout", allow_module_level=True)
sys.path.insert(0, str(AUTHOR_CODE))
from core import abstraction as AB, planning as PL

from acfqp.science.rate_distortion_2048_v39 import build_exact_2048_adapter, embed_author_abstraction
from acfqp.science.rate_distortion_compiled_v40 import CompiledOperator, compile_operator
import acfqp.science.rate_distortion_compiled_v40 as compiled_module


def abstraction(encoder, decoder):
    encoder, decoder = np.asarray(encoder, dtype=float), np.asarray(decoder, dtype=int)
    return AB.StateActionAbstraction(1., encoder, encoder / encoder.shape[0], decoder, encoder, decoder)


@pytest.mark.parametrize("case", ["last_pair_spawn_risk", "dense_merge_choice", "adjacent_1024_goal"])
def test_public_models_match_author_for_signed_random_iterates_and_reward_units(case):
    adapter = build_exact_2048_adapter(case, AB)
    rng = np.random.default_rng(40)
    encoder = rng.dirichlet(np.ones(4), adapter.num_valid_pairs)
    legal = abstraction(encoder, [0, 0, adapter.num_valid_pairs - 2, adapter.num_valid_pairs - 1])
    embedded = embed_author_abstraction(adapter, legal, AB)
    for scale in (1., 13.7):
        operator = compile_operator(adapter, legal, reward_scale=scale)
        mdp = replace(adapter.mdp, rewards=adapter.mdp.rewards * scale)
        candidates = [np.zeros(4), np.full(4, -3.), *rng.normal(size=(10, 4))]
        for u in candidates:
            expected = PL.abstract_state_action_bellman_update(mdp, embedded, u)
            assert np.max(np.abs(operator.backup(u) - expected)) <= 1e-12
        # Error accumulation is checked on a fixed small sequence, not just one backup.
        reference, compiled = np.zeros(4), np.zeros(4)
        for _ in range(20):
            reference = PL.abstract_state_action_bellman_update(mdp, embedded, reference)
            compiled = operator.backup(compiled)
        np.testing.assert_allclose(compiled, reference, rtol=0., atol=1e-12)
        assert operator.inventory()["duplicate_decoder_outputs"] == 1
        assert all(isinstance(getattr(operator, field.name), np.ndarray) for field in fields(operator))


def synthetic_adapter(repeated_sets=False):
    # One root, two (or three) H1 states, and the shared absorber.
    child_count = 3 if repeated_sets else 2
    states, actions = child_count + 2, 5
    terminal = states - 1
    mask = np.zeros((states, actions), dtype=bool)
    mask[0, 0] = True
    mask[1:terminal, :2] = True
    mask[terminal, -1] = True
    transitions = np.zeros((states, actions, states))
    transitions[0, :, 1:terminal] = ([.25, .25, .5] if repeated_sets else [.5, .5])
    transitions[1:, :, terminal] = 1.
    mdp = AB.TabularMDP(transitions, np.zeros((states, actions)), .95, list(range(states)), ["DOWN", "LEFT", "RIGHT", "UP", "TERMINAL"])
    valid = np.flatnonzero(mask.reshape(-1))
    lookup = {int(pair): i for i, pair in enumerate(valid)}
    mapping = []
    for state in range(states):
        first = np.flatnonzero(mask[state])[0]
        mapping.extend(lookup[state * actions + (action if mask[state, action] else first)] for action in range(actions))
    adapter = SimpleNamespace(mdp=mdp, legal_mask=mask, valid_pair_indices=valid, rect_to_valid_pair=np.asarray(mapping), num_valid_pairs=valid.size)
    basis = np.eye(4)
    if repeated_sets:
        almost = basis[1].copy()
        almost[0], almost[1] = 1e-14, 1. - 1e-14
        encoder = [basis[3], basis[0], basis[1], basis[1], basis[0], basis[0], almost, basis[3]]
        decoder = [0, 0, valid.size - 1, valid.size - 1]
    else:
        encoder = [basis[3], basis[0], basis[1], basis[1], basis[2], basis[3]]
        decoder = [0, 1, 3, valid.size - 1]
    return adapter, abstraction(encoder, decoder)


def test_each_successor_max_precedes_expectation_and_absorber_is_not_clamped():
    adapter, legal = synthetic_adapter()
    operator = compile_operator(adapter, legal)
    u = np.asarray([4., 0., 2., 7.])
    result = operator.backup(u)
    # The two successor states choose different legal actions: E[max] = 3.
    assert result[0] == pytest.approx(.95 * (.5 * 4. + .5 * 2.))
    assert result[0] != pytest.approx(.95 * max(.5 * 4. + .5 * 0., .5 * 0. + .5 * 2.))
    assert result[0] != pytest.approx(.95 * np.mean([4., 0., 0., 2.]))
    # Abstractly grounded terminal value is 7 during this iterate, not zero.
    np.testing.assert_allclose(result[1:], .95 * 7., atol=1e-14)
    expected = PL.abstract_state_action_bellman_update(adapter.mdp, embed_author_abstraction(adapter, legal, AB), u)
    np.testing.assert_allclose(result, expected, rtol=0., atol=1e-12)


def test_exact_set_dedup_merges_permutations_but_preserves_nearby_rows():
    adapter, legal = synthetic_adapter(repeated_sets=True)
    operator = compile_operator(adapter, legal)
    inventory = operator.inventory()
    assert inventory["unique_decoder_representatives"] == 2
    assert inventory["duplicate_decoder_outputs"] == 2
    assert inventory["supported_source_states"] == 4
    assert inventory["successor_choice_sets"] == 3
    assert inventory["choice_encoder_rows"] == 5
    assert np.max(operator.transition_weights[0]) == .5
    u = np.asarray([0., 1., -2., 3.])
    result = operator.backup(u)
    assert result[0] == result[1]
    assert result[2] == result[3]
    expected = PL.abstract_state_action_bellman_update(adapter.mdp, embed_author_abstraction(adapter, legal, AB), u)
    np.testing.assert_allclose(result, expected, rtol=0., atol=1e-12)


def test_saved_operator_runs_in_new_process_without_author_or_2048_imports(tmp_path):
    adapter, legal = synthetic_adapter(repeated_sets=True)
    operator = compile_operator(adapter, legal, reward_scale=2.)
    saved = tmp_path / "operator.npz"
    operator.save(saved)
    loaded = CompiledOperator.load(saved)
    assert loaded.inventory() == operator.inventory()
    u = np.asarray([-2., 3., -4., 5.])
    script = """
import json, runpy, sys
module = runpy.run_path(sys.argv[1])
operator = module['CompiledOperator'].load(sys.argv[2])
result = operator.backup([-2., 3., -4., 5.])
assert not any(name == 'core' or name.startswith('core.') or name == 'acfqp' or name.startswith('acfqp.') for name in sys.modules)
print(json.dumps(result.tolist()))
"""
    env = {**os.environ, "PYTHONPATH": ""}
    run = subprocess.run([sys.executable, "-c", script, compiled_module.__file__, str(saved)], cwd=tmp_path, env=env, capture_output=True, text=True, check=True)
    np.testing.assert_array_equal(json.loads(run.stdout), operator.backup(u))
    with np.load(saved, allow_pickle=False) as arrays:
        assert set(arrays.files) == {field.name for field in fields(operator)}
        assert all(arrays[name].dtype != object for name in arrays.files)
