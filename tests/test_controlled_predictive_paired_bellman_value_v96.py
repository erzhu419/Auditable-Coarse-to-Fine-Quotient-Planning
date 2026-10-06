"""One antisymmetric operator for prediction, bootstrap, and training diagnostics."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import controlled_predictive_paired_bellman_value_v96 as module
from acfqp.science.controlled_predictive_paired_direct_v96 import PairedDirectSelector
from acfqp.science.controlled_predictive_direct_value_v95 import DirectSelector
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = [1] * 10 + [0] * 6
CANDIDATE = [2] + REFERENCE[1:]
LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_paired_bellman_value_v96.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic paired Bellman trees and model-only direct prefixes; no environment data extraction.",
        ground_sampled_transitions=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def asymmetric_tree():
    return dict(left=[1, -1, -1], right=[2, -1, -1], feature=[36, -2, -2], threshold=[0, -2, -2],
                values=[[0, 0, 0], [-6, -.2, .2], [10, .4, -.4]], samples=[32, 16, 16])


def test_deployed_projection_is_not_the_raw_tree_and_preserves_exact_zero():
    tree = asymmetric_tree()
    value = module.PairedBellmanValue({query: deepcopy(tree) for query in module.QUERIES}, 6,
        {query: [0, 1, 2, 3] for query in module.QUERIES}, "PAIR_MC", 0)
    counts = Counter()
    forward = value.predict_pair(CANDIDATE, REFERENCE, True, True, "reward", counts)
    backward = value.predict_pair(REFERENCE, CANDIDATE, True, True, "reward", counts)
    assert forward == pytest.approx([8, .3, -.3])
    assert backward == pytest.approx([-x for x in forward])
    assert counts["tree_apply_rows"] == 4
    before = counts["tree_apply_rows"]
    assert value.predict_pair(CANDIDATE, CANDIDATE, True, True, "reward", counts) == [0, 0, 0]
    assert value.predict_pair(CANDIDATE, REFERENCE, False, False, "reward", counts) == [0, 0, 0]
    assert counts["tree_apply_rows"] == before and counts["paired_exact_zero_predictions"] == 2
    LEDGER.update(counts)


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
                        target=[10 * (episode + 1), 0, 0], weight=1.0))
    return rows


def test_cached_bootstrap_and_diagnostics_use_the_identical_projected_operator():
    counts = Counter()
    cache = module._cache(data()[:32], counts)
    tree = asymmetric_tree()
    bootstrap = module._prediction(tree, cache["next_x"], cache["next_mirrored"], cache["next_zero"], counts)
    np.testing.assert_allclose(bootstrap[:16], np.tile([8, .3, -.3], (16, 1)))
    np.testing.assert_array_equal(bootstrap[16:], np.zeros((16, 3)))
    target = cache["direct"] + bootstrap
    cache["active_mass"] = np.asarray([1] * 16 + [-1] * 16)
    diagnostics = module._diagnostics(tree, cache, target, counts)
    assert diagnostics["mean_prediction_rfs"] == pytest.approx([8, .3, -.3])
    assert diagnostics["mean_target_rfs"] == pytest.approx([5.5, .15, -.15])
    assert diagnostics["mean_terminal_mass_gap"] == 0
    assert diagnostics["mean_absolute_terminal_mass_gap"] == 1
    assert counts["board_feature_rows"] == 2 * (32 + 16)
    assert counts["tree_apply_rows"] == 2 * (16 + 32)
    LEDGER.update(counts)


@pytest.fixture(scope="module")
def fitted():
    rows = data()
    before = deepcopy(rows)
    models, log = module.fit_models(rows, checkpoint=6, iterations=2)
    LEDGER.update(log["counts"])
    assert rows == before
    changed = deepcopy(rows)
    for row in changed:
        if row["episode"] in (4, 6):
            row.update(target=[1e6, -1e6, 1e6], n_target=[1e6, 1e6, -1e6],
                       next_candidate_active=False, next_reference_active=False)
    other, other_log = module.fit_models(changed, checkpoint=6, iterations=2)
    LEDGER.update(other_log["counts"])
    return models, log, other, other_log


def test_pair_mc_warm_start_is_saved_unchanged_and_bellman_targets_absorb(fitted):
    models, log, _, _ = fitted
    counts = Counter()
    for query in module.QUERIES:
        assert models["PAIR_MC"].predict_pair(CANDIDATE, REFERENCE, True, True, query, counts) == [25, 0, 0]
        assert models["PAIR_FQE"].predict_pair(CANDIDATE, REFERENCE, True, True, query, counts) == [8.5, 0, 0]
        iterations = log["PAIR_FQE"]["iterations"]
        assert iterations[0]["queries"][query]["mean_target_rfs"] == [14, 0, 0]
        assert iterations[1]["queries"][query]["mean_target_rfs"] == [8.5, 0, 0]
        assert iterations[-1]["queries"][query]["mean_terminal_mass_gap"] == 0
        assert iterations[-1]["queries"][query]["mean_absolute_terminal_mass_gap"] == 0
    LEDGER.update(counts)
    assert models["PAIR_MC"].iterations == 0 and models["PAIR_FQE"].iterations == 2
    assert log["counts"]["tree_fits"] == 6
    assert log["PAIR_MC"]["counts"]["tree_fits"] == 2
    assert log["PAIR_FQE"]["counts"]["tree_fits"] == 4
    assert log["cache_counts"]["feature_cache_builds"] == 2
    assert log["cache_counts"]["board_feature_rows"] == 2 * (256 + 128)


def test_heldout_and_future_labels_never_enter_initial_or_indirect_bootstrap(fitted):
    models, log, other, other_log = fitted
    assert log["training_episodes"] == {query: [0, 1, 2, 3] for query in module.QUERIES}
    counts = Counter()
    for family in ("PAIR_MC", "PAIR_FQE"):
        payload = json.loads(json.dumps(models[family].to_payload(), allow_nan=False))
        assert payload == other[family].to_payload()
        restored = module.PairedBellmanValue.from_payload(payload)
        assert restored.to_payload() == payload
        assert restored.predict_pair(CANDIDATE, REFERENCE, True, True, "reward", counts) == (
            models[family].predict_pair(CANDIDATE, REFERENCE, True, True, "reward", counts))
    LEDGER.update(counts)
    assert log["heldout"]["counts"].get("tree_fits", 0) == 0
    assert log["heldout"]["counts"]["board_feature_rows"] == 128
    assert log["heldout"]["counts"]["tree_apply_rows"] == 256
    for query in module.QUERIES:
        diagnostic = log["heldout"]["queries"][query]
        assert diagnostic["episodes"] == [4] and diagnostic["rows"] == 32
        assert diagnostic["PAIR_MC"]["fit_target_mse_rfs"] == [625, 0, 0]
        assert diagnostic["PAIR_FQE"]["fit_target_mse_rfs"] == [1722.25, 0, 0]
        assert diagnostic["PAIR_MC"]["utility_mse"] == pytest.approx(
            625 * module.QUERIES[query]["reward_weight"] ** 2)
        assert diagnostic["PAIR_MC"]["mean_absolute_terminal_mass_gap"] == 0
        assert diagnostic != other_log["heldout"]["queries"][query]


def test_paired_direct_reuses_unary_physical_paths_and_only_predicts_paired_values(fitted, monkeypatch):
    from acfqp.domains import standard_2048 as ground
    def forbidden(*args, **kwargs):
        raise AssertionError("paired direct planning must not call the ground environment")
    monkeypatch.setattr(ground, "swipe_board_v1", forbidden)
    rule = LearnedDynamics(RewriteProgram(True, "equal", 1, "once", "output_value"),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), "uniform")
    class Unary:
        checkpoint = 6
        def predict(self, board, query, work=None):
            if work is not None:
                work["synthetic_unary_predictions"] += 1
            return [2, .9, .1]
    seed = 396_990_000_000
    unary = DirectSelector(Unary(), rule, seed, replicas=1)
    paired = PairedDirectSelector(fitted[0]["PAIR_FQE"], rule, seed, replicas=1)
    unary.select(REFERENCE, "reward")
    work = Counter(model_uniform_draws=11)
    decision = paired.select(REFERENCE, "reward", work=work)
    for selector in (unary, paired):
        for group in ("model_work", "planning_counts", "value_counts"):
            LEDGER.update({"direct_" + group + "_" + key: value for key, value in selector.last_log[group].items()})
    physical = ("option", "replica", "spawn_seed", "planning_seed", "steps", "status", "controller")
    assert [{key: row[key] for key in physical} for row in unary.last_prefixes] == [
        {key: row[key] for key in physical} for row in paired.last_prefixes]
    assert all(paired.last_log["wiring"].values())
    assert paired.last_log["value_counts"]["paired_continuation_predictions"] == 4
    assert "synthetic_unary_predictions" not in paired.last_log["value_counts"]
    assert work["model_uniform_draws"] == 11 and work["candidate_model_uniform_draws"] == 80
    assert decision["predictions"]["H2"] == dict(target=[0, 0, 0], value=0)
    for prefix in paired.last_prefixes:
        assert prefix["paired_completed"] == [a + b for a, b in zip(prefix["paired_direct"], prefix["paired_tail"])]
        assert "tail" not in prefix and "completed" not in prefix
