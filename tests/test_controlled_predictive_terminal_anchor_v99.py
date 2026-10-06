"""Persistent terminal targets, projected bootstrap, and episode isolation."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_terminal_anchor_v99 as module
from acfqp.science import controlled_predictive_paired_bellman_value_v96 as old


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = [1] * 10 + [0] * 6
CANDIDATE = [2] + REFERENCE[1:]
LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_terminal_anchor_v99.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic terminal-anchored paired trees only; no source extraction or environment calls.",
        ground_sampled_transitions=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def data():
    rows = []
    for query in module.QUERIES:
        for episode in (0, 1, 2, 3, 4, 6):
            for active in (True, False):
                for _ in range(16):
                    rows.append(dict(query=query, episode=episode, candidate_board=list(CANDIDATE),
                        reference_board=list(REFERENCE), candidate_active=True, reference_active=True,
                        next_candidate_board=list(CANDIDATE), next_reference_board=list(REFERENCE),
                        next_candidate_active=active, next_reference_active=active,
                        n_target=[1, 0, 0] if active else [2, 0, 0],
                        target=[10 * (episode + 1), 0, 0] if active else [2, 0, 0], weight=1 / 32))
    return rows


@pytest.fixture(scope="module")
def fitted():
    rows = data()
    before = deepcopy(rows)
    captured = []
    original_fit = module._fit_tree
    def recording_fit(cache, target, counts, family):
        captured.append(dict(family=family, target=target.copy()))
        return original_fit(cache, target, counts, family)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module, "_fit_tree", recording_fit)
        patch.setattr(old, "fit_models", lambda *args, **kwargs: pytest.fail("must not fit an unused pure-FQE arm"))
        models, log = module.fit_models(rows, checkpoint=6, iterations=2)
    LEDGER.update(log["counts"])
    assert rows == before
    changed = deepcopy(rows)
    for row in changed:
        if row["episode"] in (4, 6):
            row.update(target=[1e8, -1e8, 1e8], n_target=[1e8, 1e8, -1e8],
                       next_candidate_active=False, next_reference_active=False)
    other, other_log = module.fit_models(changed, checkpoint=6, iterations=2)
    LEDGER.update(other_log["counts"])
    return models, log, other, other_log, captured


def test_each_update_keeps_half_terminal_target_and_absorbed_next_has_no_bootstrap(fitted):
    models, log, _, _, captured = fitted
    assert module.ANCHOR_WEIGHT == log["anchor_weight"] == .5
    assert [row["family"] for row in captured] == ["PAIR_MC"] * 2 + ["ANCHORED_FQE"] * 4
    counts = Counter()
    for query in module.QUERIES:
        iterations = log["ANCHORED_FQE"]["iterations"]
        first, second = [row["queries"][query] for row in iterations]
        assert first["mean_complete_target_rfs"] == second["mean_complete_target_rfs"] == [13.5, 0, 0]
        assert first["mean_bellman_target_rfs"] == [8.25, 0, 0]
        assert first["mean_target_rfs"] == [10.875, 0, 0]
        assert second["mean_bellman_target_rfs"] == [6.9375, 0, 0]
        assert second["mean_target_rfs"] == [10.21875, 0, 0]
        assert models["PAIR_MC"].predict_pair(CANDIDATE, REFERENCE, True, True, query, counts) == [13.5, 0, 0]
        assert models["ANCHORED_FQE"].predict_pair(CANDIDATE, REFERENCE, True, True, query, counts) == [10.21875, 0, 0]
    LEDGER.update(counts)
    np.testing.assert_array_equal(captured[2]["target"][0], [12.25, 0, 0])
    np.testing.assert_array_equal(captured[4]["target"][0], [10.9375, 0, 0])
    for index in (2, 3, 4, 5):
        # A terminal segment equals its full remaining return: the event enters once.
        np.testing.assert_array_equal(captured[index]["target"][16], [2, 0, 0])


def test_saved_initializer_is_unchanged_and_counts_include_only_executed_fits(fitted):
    models, log, _, _, _ = fitted
    assert models["PAIR_MC"].family == "PAIR_MC" and models["PAIR_MC"].iterations == 0
    assert models["ANCHORED_FQE"].family == "ANCHORED_FQE" and models["ANCHORED_FQE"].iterations == 2
    assert log["counts"]["tree_fits"] == 6
    assert log["counts"]["pair_mc_tree_fits"] == 2
    assert log["counts"]["pair_fqe_tree_fits"] == log["counts"]["anchored_fqe_tree_fits"] == 4
    assert log["cache_counts"]["board_feature_rows"] == 768
    assert log["cache_counts"]["feature_cache_builds"] == 2
    assert log["heldout"]["counts"]["tree_apply_rows"] == 256
    total = Counter(log["cache_counts"])
    for name in ("PAIR_MC", "ANCHORED_FQE", "heldout"):
        total.update(log[name]["counts"])
    assert dict(total) == log["counts"]


def test_heldout_and_future_terminal_targets_never_enter_anchored_updates(fitted):
    models, log, other, other_log, _ = fitted
    assert log["training_episodes"] == {query: [0, 1, 2, 3] for query in module.QUERIES}
    for family in models:
        assert models[family].to_payload() == other[family].to_payload()
    for query in module.QUERIES:
        diagnostic = log["heldout"]["queries"][query]
        assert diagnostic["episodes"] == [4]
        expected_mse = ((50 - 10.21875) ** 2 + (2 - 10.21875) ** 2) / 2
        assert diagnostic["ANCHORED_FQE"]["fit_target_mse_rfs"] == [expected_mse, 0, 0]
        assert diagnostic["ANCHORED_FQE"]["utility_mse"] != (
            other_log["heldout"]["queries"][query]["ANCHORED_FQE"]["utility_mse"])


def test_anchored_prediction_keeps_swap_absorption_diagonal_and_json_contract(fitted):
    models = fitted[0]
    counts = Counter()
    for family, value in models.items():
        payload = json.loads(json.dumps(value.to_payload(), allow_nan=False))
        restored = old.PairedBellmanValue.from_payload(payload)
        assert restored.to_payload() == payload
        forward = value.predict_pair(CANDIDATE, REFERENCE, True, True, "reward", counts)
        assert restored.predict_pair(REFERENCE, CANDIDATE, True, True, "reward", counts) == [-x for x in forward]
        before = counts["tree_apply_rows"]
        assert value.predict_pair(CANDIDATE, CANDIDATE, True, True, "reward", counts) == [0, 0, 0]
        assert value.predict_pair(CANDIDATE, REFERENCE, False, False, "reward", counts) == [0, 0, 0]
        assert counts["tree_apply_rows"] == before
    LEDGER.update(counts)
