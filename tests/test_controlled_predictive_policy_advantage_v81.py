"""Synthetic fitting and policy composition, with no real environment sampling."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path
import random

import numpy as np
import pytest

from acfqp.science import controlled_predictive_policy_advantage_v81 as module
from acfqp.science.controlled_predictive_relational_dynamics_v69 import (
    LearnedDynamics, RewriteProgram,
)


ROOT = Path(__file__).resolve().parents[1]
LEDGER = Counter()
BOARD = (1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3)
RULE = LearnedDynamics(RewriteProgram(True, "equal", 1, "once", "output_value"),
    ((1, Fraction(9, 10)), (2, Fraction(1, 10))), "uniform")


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_policy_advantage_v81.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic paired targets and known-rule policy calls; no environment transitions.",
        ground_calls=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def leaf(value):
    return dict(left=[-1], right=[-1], feature=[-2], threshold=[-2.0],
                values=[value], samples=[16])


def fake_h2(board, query, knowledge, rule, rng, depth=2, work=None):
    for _ in range(4):
        rng.random()
    work["model_uniform_draws"] += 4
    return dict(action="LEFT", value=3.0, metrics=dict(reward=3.0, failure=0.0, success=0.0))


def test_features_use_observed_state_deterministic_afterstates_and_action_binding():
    counts = Counter()
    vector = module.action_features(BOARD, "RIGHT", "LEFT", RULE, counts)
    right, right_score, _ = RULE.swipe(BOARD, "RIGHT")
    left, left_score, _ = RULE.swipe(BOARD, "LEFT")
    assert len(vector) == len(module.FEATURE_NAMES) == 81
    assert vector[:36] == module.features(BOARD, 30)[:-1]
    np.testing.assert_array_equal(vector[36:72], np.asarray(module.features(right, 30)[:-1])
                                  - np.asarray(module.features(left, 30)[:-1]))
    assert vector[72] == (right_score - left_score) / 2048
    assert vector[73:] == (0, 0, 1, 0, 0, 1, 0, 0)
    assert counts["learned_swipe_calls"] == 2 and "model_uniform_draws" not in counts
    LEDGER.update(counts)


def test_zero_reference_strict_tie_and_complete_vector_query_selection(monkeypatch):
    monkeypatch.setattr(module.planner, "choose", fake_h2)
    base = module.Policy.base()
    zero = module.Policy(base, {query: leaf([0, 0, 0]) for query in module.QUERIES}, 1)
    result = zero.choose(BOARD, "reward", RULE, random.Random(1))
    LEDGER.update(result["counts"])
    assert result["action"] == result["reference_action"] == "LEFT"
    assert result["action_advantages"]["LEFT"] == dict(target=[0.0, 0.0, 0.0], value=0.0)
    policy = module.Policy(base, {query: leaf([1, 0.2, -0.2]) for query in module.QUERIES}, 1)
    reward = policy.choose(BOARD, "reward", RULE, random.Random(1))
    risk = policy.choose(BOARD, "risk_goal", RULE, random.Random(1))
    LEDGER.update(reward["counts"])
    LEDGER.update(risk["counts"])
    assert reward["action"] == "DOWN" and reward["advantage"] == [1, 0.2, -0.2]
    assert risk["action"] == "LEFT" and risk["advantage"] == [0, 0, 0]
    assert risk["action_advantages"]["DOWN"]["value"] == pytest.approx(-0.6)
    assert risk["counts"]["model_uniform_draws"] == 4


def training_rows(iteration, target):
    rows = []
    for episode in range(5):
        for query in module.QUERIES:
            for _ in range(16):
                value = [1000, 1000, 1000] if episode == 4 else target
                rows.append(dict(board=list(BOARD), query=query, episode=episode,
                    action="RIGHT", reference_action="LEFT", target=value, iteration=iteration))
    return rows


@pytest.fixture(scope="module")
def fitted():
    base = module.Policy.base()
    parent_before = base.to_payload()
    records = training_rows(1, [1, 0.2, -0.2])
    records += training_rows(2, [900, 0, 0])
    records.append(dict(board=list(BOARD), query="reward", episode=0,
        action="LEFT", reference_action="LEFT", target=[900, 0, 0], iteration=1))
    seen = []
    real_fit = module._fit

    def capture(x, y, counts):
        seen.append((x.copy(), y.copy()))
        return real_fit(x, y, counts)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module, "_fit", capture)
        first, first_log = module.improve(base, records, 1, RULE)
        first_before = first.to_payload()
        second, second_log = module.improve(first, training_rows(2, [-1, 0, 0]), 2, RULE)
    LEDGER.update(first_log["counts"])
    LEDGER.update(second_log["counts"])
    assert base.to_payload() == parent_before
    assert first.to_payload() == first_before
    return first, second, first_log, second_log, seen


def test_fit_excludes_holdout_other_iterations_and_exact_reference_rows(fitted):
    first, second, first_log, second_log, seen = fitted
    assert first_log["other_iteration_records_excluded"] == 160
    assert first_log["reference_records_excluded"] == 1
    assert first_log["training_records"] == second_log["training_records"] == 128
    assert first_log["heldout_records"] == second_log["heldout_records"] == 32
    assert first_log["counts"]["tree_fits"] == second_log["counts"]["tree_fits"] == 2
    assert len(seen) == 4
    for index, (x, y) in enumerate(seen):
        assert x.shape == (64, 81)
        np.testing.assert_allclose(y, np.tile([1, 0.2, -0.2] if index < 2 else [-1, 0, 0], (64, 1)))
    for query in module.QUERIES:
        np.testing.assert_allclose(first_log["queries"][query]["heldout_mse_components"],
                                   [(1000 - value) ** 2 for value in (1, 0.2, -0.2)])
    assert second.parent.to_payload() == first.to_payload()
    assert second.parent is not first and second.parent.trees is not first.trees


def test_two_layer_roundtrip_preserves_actions_and_only_base_consumes_rng(fitted):
    _, policy, _, _, _ = fitted
    payload = json.loads(json.dumps(policy.to_payload()))
    restored = module.Policy.from_payload(payload)
    for query in module.QUERIES:
        expected_rng, original_rng, restored_rng = (random.Random(81) for _ in range(3))
        for _ in range(4):
            expected_rng.random()
        counts = Counter()
        original = policy.choose(BOARD, query, RULE, original_rng, counts)
        replica = restored.choose(BOARD, query, RULE, restored_rng)
        LEDGER.update(counts)
        LEDGER.update(replica["counts"])
        assert original == replica
        assert counts == Counter(original["counts"])
        assert counts["model_uniform_draws"] == 4
        assert original_rng.getstate() == restored_rng.getstate() == expected_rng.getstate()
        assert policy.to_payload() == restored.to_payload() == payload
        assert counts["learned_policy_decisions"] == 2
    terminal_rng = random.Random(82)
    before = terminal_rng.getstate()
    terminal = restored.choose((11,) + (0,) * 15, "reward", RULE, terminal_rng)
    LEDGER.update(terminal["counts"])
    assert terminal["action"] is None and terminal["action_advantages"] == {}
    assert terminal_rng.getstate() == before
