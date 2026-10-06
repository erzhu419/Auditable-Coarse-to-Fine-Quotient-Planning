"""Mean-only fitting, original candidate order and whole-root data separation."""
from collections import Counter
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_mean_fragments_v87 as module
from acfqp.science.controlled_predictive_joint_fragments_v84 import JointSelector


ROOT = Path(__file__).resolve().parents[1]
BOARD = (1, 1, 2, 3, 4, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0)
LEDGER = Counter()
VECTORS = np.asarray([[2, 0.5, 0], [1, 0, 0.5], [4, 1, 0], [0, -0.5, 1]])


def leaf(values):
    return dict(left=[-1], right=[-1], feature=[-2], threshold=[-2.0],
                values=[np.asarray(values).reshape(-1).tolist()], samples=[2])


def source_model(vectors=VECTORS):
    vectors = np.asarray(vectors)
    mean = vectors.mean(axis=0)
    anchor = JointSelector({query: leaf(np.tile(mean, (4, 1))) for query in module.QUERIES}, 12)
    return module.CenteredSelector({query: leaf(vectors - mean) for query in module.QUERIES}, 12, anchor)


def with_mean(source, mean):
    return module.MeanSelector({query: leaf(mean) for query in module.QUERIES}, 12, source)


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_mean_fragments_v87.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic mean-tree fits and saved-selector interpretation; no RNG or environment calls.",
        ground_calls=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


@pytest.fixture(scope="module")
def fitted():
    source = source_model()
    before = source.to_payload()
    rows = [dict(board=list(BOARD), query=query, episode=episode, option=option,
                 target=[999, 999, 999] if episode == 4 else (VECTORS[i] + [episode, 0, 0]).tolist())
            for query in module.QUERIES for episode in range(5)
            for i, option in enumerate(module.OPTIONS[1:])]
    captured = []
    actual_fit = module._fit

    def capture(x, y, counts):
        captured.append((x.copy(), y.copy()))
        return actual_fit(x, y, counts)

    def forbidden(*args, **kwargs):
        raise AssertionError("The saved source and anchor must never be refitted")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module, "_fit", capture)
        patch.setattr(module.CenteredSelector, "fit", forbidden)
        patch.setattr(JointSelector, "fit", forbidden)
        selector, log = module.MeanSelector.fit(list(reversed(rows)), 12, source)
    assert source.to_payload() == before
    LEDGER.update(log["counts"])
    return selector, log, captured, before


def test_fit_uses_one_mean_vector_per_root_and_excludes_holdout_without_source_fit(fitted):
    selector, log, captured, before = fitted
    assert log["input_records"] == 40 and log["input_roots"] == 10
    assert log["training_records"] == 32 and log["training_roots"] == 8
    assert log["heldout_records"] == 8 and log["heldout_roots"] == 2
    assert log["counts"]["fit_rows"] == log["counts"]["fit_roots"] == log["counts"]["fit_output_vectors"] == 8
    assert log["counts"]["tree_fits"] == log["counts"]["mean_tree_fits"] == 2
    assert log["source_tree_fits"] == 0 and selector.source.to_payload() == before
    expected = np.asarray([VECTORS.mean(axis=0) + [episode, 0, 0] for episode in range(4)])
    for x, y in captured:
        assert x.shape == (4, 36) and y.shape == (4, 3)
        np.testing.assert_array_equal(y, expected)
    for query in module.QUERIES:
        assert selector.mean_trees[query]["samples"] == [4]
        np.testing.assert_allclose(log["queries"][query]["heldout_mse_components"],
                                  (expected.mean(axis=0) - 999) ** 2)


def test_mean_can_enable_or_disable_intervention_without_changing_non_h2_winner():
    counts = Counter()
    negative = source_model([[-4, 0, 0], [-2, 0, 0], [-1, 0, 0], [-3, 0, 0]])
    assert negative.select(BOARD, "reward", work=counts)["option"] == "H2"
    enabled = with_mean(negative, [1.5, 0, 0]).select(BOARD, "reward", work=counts)
    assert enabled["option"] == "SPACE_4" and enabled["value"] == 3
    positive = source_model([[6, 0, 0], [8, 0, 0], [9, 0, 0], [7, 0, 0]])
    assert positive.select(BOARD, "reward", work=counts)["option"] == "SPACE_4"
    disabled = with_mean(positive, [-10, 0, 0]).select(BOARD, "reward", work=counts)
    assert disabled["option"] == "H2" and disabled["value"] == 0
    for result in (enabled, disabled):
        winner = max(module.OPTIONS[1:], key=lambda option: result["predictions"][option]["ranking_value"])
        assert winner == "SPACE_4"
    LEDGER.update(counts)


def test_shared_shift_preserves_vector_differences_and_full_four_mean_before_restriction():
    source = source_model()
    model = with_mean(source, [4, 0.75, -0.25])
    counts = Counter()
    for query in module.QUERIES:
        old = source.select(BOARD, query, work=counts)
        full = model.select(BOARD, query, work=counts)
        one = model.select(BOARD, query, tuple(reversed(module.ONE_STEP_OPTIONS)), counts)
        old_values = np.asarray([old["predictions"][option]["target"] for option in module.OPTIONS[1:]])
        new_values = np.asarray([full["predictions"][option]["target"] for option in module.OPTIONS[1:]])
        np.testing.assert_array_equal(new_values.mean(axis=0), [4, 0.75, -0.25])
        np.testing.assert_array_equal(new_values - old_values,
                                     np.tile(np.asarray([4, 0.75, -0.25]) - old_values.mean(axis=0), (4, 1)))
        np.testing.assert_array_equal(new_values[:, None, :] - new_values[None, :, :],
                                     old_values[:, None, :] - old_values[None, :, :])
        for option in module.ONE_STEP_OPTIONS:
            assert one["predictions"][option] == full["predictions"][option]
        for option in module.OPTIONS[1:]:
            assert full["predictions"][option]["ranking_value"] == old["predictions"][option]["value"]
        if full["option"] != "H2":
            assert full["option"] == max(module.OPTIONS[1:], key=lambda option: old["predictions"][option]["value"])
    assert counts["mean_prediction_roots"] == 4 and counts["mean_tree_apply_rows"] == 4
    assert counts["tree_apply_rows"] == 16  # Four three-tree calls and two two-tree source calls.
    assert "model_uniform_draws" not in counts
    LEDGER.update(counts)


def test_original_ties_keep_stable_order_and_shifted_float_ties_do_not_replace_source_winner():
    counts = Counter()
    tied = source_model([[1, 0, 0], [1, 0, 0], [0, 0, 0], [0, 0, 0]])
    selected = with_mean(tied, [2, 0, 0]).select(BOARD, "reward", tuple(reversed(module.OPTIONS)), counts)
    assert selected["option"] == "SPACE_1"
    # These adjacent representable source utilities become tied after the common shift.
    near = source_model([[0.1, 0, 0], [np.nextafter(0.1, 1), 0, 0], [-0.1, 0, 0], [-0.1, 0, 0]])
    original = near.select(BOARD, "reward", work=counts)
    assert original["predictions"]["SNAKE_1"]["value"] > original["predictions"]["SPACE_1"]["value"]
    shifted = with_mean(near, [1, 0, 0]).select(BOARD, "reward", work=counts)
    assert shifted["predictions"]["SNAKE_1"]["value"] == shifted["predictions"]["SPACE_1"]["value"]
    assert shifted["option"] == "SNAKE_1"
    LEDGER.update(counts)


def test_serialization_is_self_contained_and_leaves_source_immutable(fitted):
    model, _, _, _ = fitted
    payload = json.loads(json.dumps(model.to_payload()))
    restored = module.MeanSelector.from_payload(payload)
    counts = Counter()
    for query in module.QUERIES:
        for allowed in (None, module.ONE_STEP_OPTIONS):
            assert model.select(BOARD, query, allowed, counts) == restored.select(BOARD, query, allowed, counts)
    assert model.to_payload() == restored.to_payload() == payload
    assert restored.source is not model.source
    assert restored.source.trees is not model.source.trees
    assert restored.source.anchor.trees is not model.source.anchor.trees
    assert counts["tree_apply_rows"] == 24 and counts["mean_tree_apply_rows"] == 8
    assert "model_uniform_draws" not in counts
    LEDGER.update(counts)
