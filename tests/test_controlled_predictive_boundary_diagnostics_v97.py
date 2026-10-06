"""Uniform boundary evaluation without new fits or environment calls."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_boundary_diagnostics_v97 as module
from acfqp.science.controlled_predictive_paired_bellman_value_v96 import PairedBellmanValue


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = [1] * 10 + [0] * 6
CANDIDATE = [2] + REFERENCE[1:]
LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_boundary_diagnostics_v97.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic retained-state diagnostics with handcrafted trees.",
        tree_fits=0, ground_sampled_transitions=0, main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


def models():
    result = {}
    for scale, name in enumerate(module.MODEL_NAMES, 1):
        tree = dict(left=[1, -1, -1], right=[2, -1, -1], feature=[36, -2, -2], threshold=[0, -2, -2],
            values=[[0, 0, 0], [-6 * scale, -.2 * scale, .2 * scale],
                    [10 * scale, .4 * scale, -.4 * scale]], samples=[32, 16, 16])
        result[name] = PairedBellmanValue({q: deepcopy(tree) for q in module.QUERIES}, 6,
            {q: [0, 1, 2, 3] for q in module.QUERIES}, name, 0)
    return result


def rows():
    result = []
    for query in module.QUERIES:
        base = dict(query=query, episode=4, candidate_board=list(CANDIDATE),
            reference_board=list(REFERENCE), candidate_active=True, reference_active=True,
            weight=1 / 32, step=4, target=[2, .2, -.2])
        result.extend([base,
            dict(base, step=20, candidate_board=list(REFERENCE), reference_board=list(CANDIDATE),
                 target=[-4, -.1, .1]),
            dict(base, candidate_board=list(REFERENCE), target=[0, 0, 0]),
            dict(base, step=36, candidate_active=False, reference_active=False, target=[0, 0, 0]),
            dict(base, episode=0, target=[1e6, -1e6, 1e6]),
            dict(base, episode=9, target=[-1e6, 1e6, -1e6])])
    return result


def evaluate(data, fitted=None):
    log = module.evaluate_boundaries(data, fitted or models(), checkpoint=6)
    LEDGER.update(log["counts"])
    return log


def test_fixed_scoring_weights_and_one_prediction_cache_feed_all_strata():
    data = rows()
    original = deepcopy(data)
    log = evaluate(data)
    assert data == original
    modified = deepcopy(data)
    for index, row in enumerate(modified):
        row["weight"] = 1e9 if index % 2 else 0
    other = evaluate(modified)
    assert {k: v for k, v in log.items() if k != "seconds"} == {
        k: v for k, v in other.items() if k != "seconds"}
    assert log["scoring_weight"] == 1 / 32
    assert log["feature_counts"]["feature_cache_builds"] == 2
    assert log["feature_counts"]["board_feature_rows"] == 16
    for counts in log["model_counts"].values():
        assert counts["paired_continuation_predictions"] == 8
        assert counts["paired_exact_zero_predictions"] == 4
        assert counts["tree_apply_rows"] == 8
    combined = Counter(log["feature_counts"])
    for counts in log["model_counts"].values():
        combined.update(counts)
    assert dict(combined) == log["counts"] and combined.get("tree_fits", 0) == 0


def test_boundary_and_tail_errors_remain_distinct_with_exact_episode_isolation():
    data = rows()
    log = evaluate(data)
    other = evaluate([row for row in data if row["episode"] == 4])
    assert log["queries"] == other["queries"]
    for query in module.QUERIES:
        summary = log["queries"][query]
        assert summary["rows"] == 4 and summary["episodes"] == [4]
        strata = summary["strata"]
        assert strata["all"]["weight_sum"] == 4 / 32
        for name in ("boundary", "tail"):
            assert strata[name]["rows"] == 2 and strata[name]["episodes"] == [4]
        assert strata["all"]["models"]["PAIR_MC"]["mse_rfs"] == pytest.approx([13, .0125, .0125])
        assert strata["boundary"]["models"]["PAIR_MC"]["mse_rfs"] == pytest.approx([18, .005, .005])
        assert strata["tail"]["models"]["PAIR_MC"]["mse_rfs"] == pytest.approx([8, .02, .02])
        assert strata["all"]["models"]["PAIR_MC"]["bias_rfs"] == pytest.approx([.5, -.025, .025])
    risk = log["queries"]["risk_goal"]["strata"]
    assert risk["all"]["models"]["PAIR_MC"]["utility_mse"] == pytest.approx(8.2)
    assert risk["boundary"]["models"]["PAIR_MC"]["utility_mse"] == pytest.approx(13.52)
    assert risk["tail"]["models"]["PAIR_MC"]["utility_mse"] == pytest.approx(2.88)


def test_cached_diagnostics_equal_deployed_antisymmetric_and_exact_zero_operator():
    data, fitted = rows(), models()
    log = evaluate(data, fitted)
    reference_counts = Counter()
    for query in module.QUERIES:
        for name, value in fitted.items():
            predictions = [value.predict_pair(row["candidate_board"], row["reference_board"],
                row["candidate_active"], row["reference_active"], query, reference_counts)
                for row in data if row["query"] == query and row["episode"] == 4]
            assert predictions[2:] == [[0, 0, 0], [0, 0, 0]]
            assert predictions[0] == pytest.approx([-x for x in predictions[1]])
            diag = log["queries"][query]["strata"]["boundary"]["models"][name]
            assert diag["mean_prediction_rfs"] == pytest.approx([x / 2 for x in predictions[0]])
    LEDGER.update({"reference_" + key: value for key, value in reference_counts.items()})


def test_terminal_mass_uses_active_difference_and_empty_strata_are_json_safe():
    row = dict(rows()[0], reference_active=False, target=[2, 1, 0])
    row.pop("weight")  # Diagnostic scoring does not need the training weight.
    log = evaluate([row])
    assert json.loads(json.dumps(log, allow_nan=False)) == log
    reward = log["queries"]["reward"]["strata"]
    for name in module.MODEL_NAMES:
        assert reward["boundary"]["models"][name]["mean_terminal_mass_gap"] == -1
        assert reward["boundary"]["models"][name]["mean_absolute_terminal_mass_gap"] == 1
        assert all(value is None for value in reward["tail"]["models"][name].values())
    assert reward["tail"]["rows"] == 0
    assert log["queries"]["risk_goal"]["rows"] == 0
    assert log["feature_counts"]["feature_cache_builds"] == 1
