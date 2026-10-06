"""Centered output invariants and root-isolated fitting; no sampled episodes."""
from collections import Counter
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_centered_fragments_v85 as module


ROOT = Path(__file__).resolve().parents[1]
BOARD = (1, 1, 2, 3, 4, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0)
LEDGER = Counter()
TARGETS = np.asarray([[0.5, 0.25, 0], [-0.5, 0, 0.25], [1, 0.5, 0], [-1, -0.25, 0.5]])


def leaf(vectors):
    return dict(left=[-1], right=[-1], feature=[-2], threshold=[-2.0],
                values=[np.asarray(vectors).reshape(12).tolist()], samples=[2])


def anchor_model(checkpoint=6):
    vectors = [[2, 0.5, 0], [3, 0, 0.5], [1, -0.5, 0], [2, 0, 0.5]]
    return module.JointSelector({query: leaf(vectors) for query in module.QUERIES}, checkpoint)


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_centered_fragments_v85.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic centered targets and JSON tree interpretation; no RNG or environment calls.",
        ground_calls=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def records(shifted=False):
    rows = []
    for query_index, query in enumerate(module.QUERIES):
        for episode in range(6):
            board = (1 + episode % 2,) + BOARD[1:]
            targets = TARGETS * (1 + episode % 2)
            if episode == 4:
                targets = np.asarray([[100 + i, -80 + 2 * i, 64 - 3 * i] for i in range(4)])
            if shifted:
                targets = targets + [16 * episode + query_index, 8 * (episode + 1), -4 * episode]
            for option, target in zip(module.OPTIONS[1:], targets):
                rows.append(dict(board=list(board), query=query, episode=episode,
                                 option=option, target=target.tolist()))
    return rows


@pytest.fixture(scope="module")
def fitted():
    anchor = anchor_model()
    before = anchor.to_payload()
    captured = []
    actual_fit = module._fit

    def capture(x, y, counts):
        captured.append((x.copy(), y.copy()))
        return actual_fit(x, y, counts)

    def forbidden_anchor_fit(*args, **kwargs):
        raise AssertionError("The retained anchor must never be fitted")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module, "_fit", capture)
        patch.setattr(module.JointSelector, "fit", forbidden_anchor_fit)
        original, original_log = module.CenteredSelector.fit(records(), 6, anchor)
        shifted, shifted_log = module.CenteredSelector.fit(list(reversed(records(True))), 6, anchor)
    assert anchor.to_payload() == before
    LEDGER.update(original_log["counts"])
    LEDGER.update(shifted_log["counts"])
    return original, shifted, original_log, shifted_log, captured, before


def test_root_common_vector_shifts_cancel_from_residual_targets_and_tree(fitted):
    original, shifted, _, _, captured, _ = fitted
    assert original.trees == shifted.trees
    for index in range(2):
        np.testing.assert_array_equal(captured[index][0], captured[index + 2][0])
        np.testing.assert_array_equal(captured[index][1], captured[index + 2][1])
        np.testing.assert_array_equal(captured[index][1].reshape((-1, 4, 3)).mean(axis=1), np.zeros((5, 3)))


def test_holdout_excluded_as_whole_roots_and_only_residual_fits_counted(fitted):
    original, _, log, shifted_log, captured, anchor = fitted
    for current in (log, shifted_log):
        assert current["input_records"] == 48 and current["input_roots"] == 12
        assert current["training_records"] == 40 and current["training_roots"] == 10
        assert current["heldout_records"] == 8 and current["heldout_roots"] == 2
        assert current["counts"]["tree_fits"] == 2 and current["anchor_tree_fits"] == 0
        assert current["counts"]["fit_roots"] == current["counts"]["fit_rows"] == 10
        assert current["counts"]["fit_output_vectors"] == 40
        assert current["min_samples_leaf_unit"] == "roots"
        for query in module.QUERIES:
            assert np.shape(current["queries"][query]["heldout_mse_components"]) == (4, 3)
            assert np.shape(current["queries"][query]["heldout_residual_mse_components"]) == (4, 3)
    assert original.anchor.to_payload() == anchor
    expected = [module._center((TARGETS * (1 + episode % 2))[None])[0].reshape(12)
                for episode in (0, 1, 2, 3, 5)]
    for x, y in captured:
        assert x.shape == (5, 36) and y.shape == (5, 12)
        np.testing.assert_array_equal(y, expected)


def test_inference_preserves_anchor_mean_and_centers_full_four_before_restriction():
    # Intentionally nonzero residual mean detects omission of inference centering.
    residual = [[11, 2, 0], [9, 0, 2], [14, 6, 0], [6, 0, 2]]
    anchor = anchor_model()
    model = module.CenteredSelector({query: leaf(residual) for query in module.QUERIES}, 6, anchor)
    counts = Counter()
    for query in module.QUERIES:
        full = model.select(BOARD, query, work=counts)
        restricted = model.select(BOARD, query, tuple(reversed(module.ONE_STEP_OPTIONS)), counts)
        anchor_prediction = anchor.select(BOARD, query, work=counts)
        actual = np.asarray([full["predictions"][option]["target"] for option in module.OPTIONS[1:]])
        base = np.asarray([anchor_prediction["predictions"][option]["target"] for option in module.OPTIONS[1:]])
        np.testing.assert_array_equal(actual.mean(axis=0), base.mean(axis=0))
        np.testing.assert_array_equal(actual, base.mean(axis=0) + np.asarray(residual) - np.mean(residual, axis=0))
        for option in module.ONE_STEP_OPTIONS:
            assert restricted["predictions"][option] == full["predictions"][option]
        assert tuple(restricted["predictions"]) == module.ONE_STEP_OPTIONS
        assert full["predictions"]["H2"] == dict(target=[0, 0, 0], value=0)
    assert model.select(BOARD, "reward", work=counts)["option"] == "SPACE_4"
    assert counts["anchor_prediction_roots"] == counts["residual_prediction_roots"] == 5
    assert counts["anchor_tree_apply_rows"] == counts["residual_tree_apply_rows"] == 5
    assert counts["tree_apply_rows"] == 12  # Five two-tree calls plus two direct anchor calls.
    assert "model_uniform_draws" not in counts
    LEDGER.update(counts)


def test_self_contained_roundtrip_preserves_choices_and_anchor_without_mutation(fitted):
    model, _, _, _, _, _ = fitted
    payload = json.loads(json.dumps(model.to_payload()))
    restored = module.CenteredSelector.from_payload(payload)
    counts = Counter()
    for query in module.QUERIES:
        for allowed in (None, module.ONE_STEP_OPTIONS):
            assert model.select(BOARD, query, allowed, counts) == restored.select(BOARD, query, allowed, counts)
    assert restored.to_payload() == model.to_payload() == payload
    assert restored.anchor is not model.anchor and restored.anchor.trees is not model.anchor.trees
    assert counts["tree_apply_rows"] == 16
    assert counts["anchor_tree_apply_rows"] == counts["residual_tree_apply_rows"] == 8
    assert "model_uniform_draws" not in counts
    LEDGER.update(counts)


def test_zero_reference_and_stable_ties_remain_exact_after_reconstruction():
    counts = Counter()
    for mean, expected in ((0, "H2"), (1, "SPACE_1"), (-1, "H2")):
        anchor = module.JointSelector({query: leaf([[mean, 0, 0]] * 4) for query in module.QUERIES}, 6)
        model = module.CenteredSelector({query: leaf([[7, 3, -2]] * 4) for query in module.QUERIES}, 6, anchor)
        result = model.select(BOARD, "reward", tuple(reversed(module.OPTIONS)), counts)
        assert result["option"] == expected
        assert result["predictions"]["H2"]["target"] == [0, 0, 0]
    LEDGER.update(counts)
