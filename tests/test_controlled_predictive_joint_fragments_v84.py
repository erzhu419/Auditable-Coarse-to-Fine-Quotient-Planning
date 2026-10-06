"""Candidate-output binding and whole-root fitting, without environment calls."""
from collections import Counter
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_joint_fragments_v84 as module


ROOT = Path(__file__).resolve().parents[1]
BOARD = (1, 1, 2, 3, 4, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0)
TARGETS = {"SPACE_1": [1, 0.2, 0], "SNAKE_1": [0.5, 0, 0],
           "SPACE_4": [2, 1, 0.1], "SNAKE_4": [0.25, -0.2, 0.2]}
LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_joint_fragments_v84.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic joint-output trees and root grouping; no RNG or environment sampling.",
        ground_calls=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def records():
    return [dict(board=list(BOARD), query=query, episode=episode, option=option,
                 target=[999, 999, 999] if episode == 4 else TARGETS[option])
            for query in module.QUERIES for episode in range(5)
            for option in reversed(module.OPTIONS[1:])]


@pytest.fixture(scope="module")
def fitted():
    rows = records()
    rows.append(dict(board=list(BOARD), query="reward", episode=0, option="H2", target=[999] * 3))
    observed = []
    actual_fit = module._fit

    def capture(x, y, counts):
        observed.append((x.copy(), y.copy()))
        return actual_fit(x, y, counts)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module, "_fit", capture)
        selector, log = module.JointSelector.fit(rows, checkpoint=5)
    LEDGER.update(log["counts"])
    return selector, log, observed


def test_grouping_preserves_option_binding_under_reordered_records():
    rows = records()
    roots = module._pack_roots(rows)
    assert roots == module._pack_roots(list(reversed(rows)))
    assert len(roots) == 10
    expected = [value for option in module.OPTIONS[1:] for value in TARGETS[option]]
    for root in roots:
        assert root["target"] == ([999] * 12 if root["episode"] == 4 else expected)
    # A root is an indivisible joint target, including every option's output.
    with pytest.raises(ValueError, match="all four"):
        module._pack_roots(rows[:-1])


def test_fit_excludes_whole_heldout_roots_and_counts_leaf_samples_as_roots(fitted):
    selector, log, observed = fitted
    assert log["input_records"] == 41 and log["reference_records_excluded"] == 1
    assert log["input_roots"] == 10 and log["training_roots"] == 8 and log["heldout_roots"] == 2
    assert log["training_records"] == 32 and log["heldout_records"] == 8
    assert log["counts"]["fit_roots"] == log["counts"]["fit_rows"] == 8
    assert log["counts"]["fit_output_vectors"] == 32 and log["counts"]["tree_fits"] == 2
    assert module.TREE_PARAMETERS["min_samples_leaf"] == 2 and log["min_samples_leaf_unit"] == "roots"
    expected = [value for option in module.OPTIONS[1:] for value in TARGETS[option]]
    for x, y in observed:
        assert x.shape == (4, 36) and y.shape == (4, 12)
        np.testing.assert_allclose(x, np.tile(module.features(BOARD, 30)[:-1], (4, 1)), rtol=1e-6)
        np.testing.assert_array_equal(y, np.tile(expected, (4, 1)))
    for query in module.QUERIES:
        assert selector.trees[query]["left"] == [-1] and selector.trees[query]["samples"] == [4]
        np.testing.assert_allclose(log["queries"][query]["heldout_mse_components"],
                                  ((np.asarray(expected) - 999) ** 2).reshape((4, 3)))


def test_same_leaf_keeps_distinct_options_and_can_select_four_steps(fitted):
    selector, _, _ = fitted
    counts = Counter()
    reward = selector.select(BOARD, "reward", work=counts)
    risk = selector.select(BOARD, "risk_goal", work=counts)
    assert reward["option"] == "SPACE_4" and risk["option"] == "SNAKE_4"
    assert reward["predicted_advantage"] == TARGETS["SPACE_4"]
    assert risk["predicted_advantage"] == TARGETS["SNAKE_4"]
    assert risk["value"] == pytest.approx(1.85)
    for option in module.OPTIONS[1:]:
        assert reward["predictions"][option]["target"] == TARGETS[option]
    assert counts["board_feature_rows"] == counts["joint_prediction_roots"] == 2
    assert counts["predicted_output_vectors"] == 8
    assert "model_uniform_draws" not in counts
    LEDGER.update(counts)


def test_serialization_and_one_step_restriction_preserve_output_identity(fitted):
    selector, _, _ = fitted
    payload = json.loads(json.dumps(selector.to_payload()))
    restored = module.JointSelector.from_payload(payload)
    counts = Counter()
    for query, expected in (("reward", "SPACE_1"), ("risk_goal", "SNAKE_1")):
        one = restored.select(BOARD, query, tuple(reversed(module.ONE_STEP_OPTIONS)), counts)
        assert one["option"] == expected
        assert tuple(one["predictions"]) == module.ONE_STEP_OPTIONS
        assert selector.select(BOARD, query, work=counts) == restored.select(BOARD, query, work=counts)
    assert selector.to_payload() == restored.to_payload() == payload
    assert len(payload["feature_names"]) == 36 and len(payload["output_names"]) == 12
    assert payload["min_samples_leaf_unit"] == "roots"
    LEDGER.update(counts)


def test_exact_h2_zero_and_stable_strict_positive_ties():
    counts = Counter()
    for target, expected in (([0, 0, 0], "H2"), ([1, 0, 0], "SPACE_1"), ([-1, 0, 0], "H2")):
        leaf = dict(left=[-1], right=[-1], feature=[-2], threshold=[-2.0],
                    values=[target * 4], samples=[2])
        selector = module.JointSelector({query: leaf for query in module.QUERIES}, 0)
        result = selector.select(BOARD, "reward", tuple(reversed(module.OPTIONS)), counts)
        assert result["option"] == expected
        assert result["predictions"]["H2"] == dict(target=[0, 0, 0], value=0)
    LEDGER.update(counts)
