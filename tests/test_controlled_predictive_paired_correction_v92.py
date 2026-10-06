"""Paired residual correction, independent mean variance, and prefix execution."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_paired_correction_v92 as module
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram


ROOT = Path(__file__).resolve().parents[1]
BOARD = [1] * 10 + [0] * 6
LEDGER = Counter()


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_paired_correction_v92.core_checks.json"
    payload = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    payload["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        scope="Synthetic estimators/heads and one real 40-transition prefix sample; no campaign calls.",
        main_campaign_calls=0, **LEDGER))
    path.write_text(json.dumps(payload, indent=2) + "\n")


class Model:
    def __init__(self, factor=1, fold=None):
        self.factor, self.excluded_fold, self.checkpoint = factor, fold, 5
        self.training_episodes = {query: [episode for episode in range(4)
            if fold is None or episode % 2 != fold] for query in module.QUERIES}

    def predict_pair(self, cboard, rboard, cactive, ractive, query, work=None):
        if work is not None:
            work["synthetic_pair_predictions"] += 1
        return [self.factor * (cboard[0] * cactive - rboard[0] * ractive), 0, 0]


def prefixes(values, terminal_values=None):
    result = {option: [] for option in module.OPTIONS}
    for option in module.OPTIONS:
        for replica, value in enumerate(values):
            reference = option == "H2"
            result[option].append(dict(replica=replica, option=option, direct=[0, 0, 0],
                boundary_board=[0 if reference else value] + BOARD[1:], status="ACTIVE",
                full_target=(None if terminal_values is None else
                             [0 if reference else terminal_values[replica], 0, 0])))
    return result


def root(query="reward", episode=0):
    return dict(board=list(BOARD), query=query, episode=episode, censored=False,
                prefixes=prefixes([1, 3], [10, 14]), mc_rows=[])


def test_correction_uses_two_distinct_means_and_both_variance_terms():
    sample, short = root(), prefixes([5, 9])
    before = deepcopy((sample, short))
    result = module.estimate_root(sample, short, Model())
    assert result["complete"] and (sample, short) == before
    for option in module.OPTIONS[1:]:
        assert result["estimates"]["MC"][option] == [12, 0, 0]
        assert result["estimates"]["PAIR_ONLY"][option] == [7, 0, 0]
        assert result["estimates"]["CORRECTED"][option] == [17, 0, 0]
        detail = result["details"][option]
        assert detail["paired_residuals"] == [[9, 0, 0], [11, 0, 0]]
        assert detail["mc_variance_of_mean"] == 4
        assert detail["corrected_variance_of_mean"] == 5  # short 4 + residual 1


def test_reused_prefixes_recover_mc_point_estimate_algebra_only():
    sample = root()
    result = module.estimate_root(sample, sample["prefixes"], Model())
    assert result["estimates"]["MC"] == result["estimates"]["CORRECTED"]
    # The reported two-independent-mean variance is not asserted for this reused-sample identity fixture.


def test_censoring_and_requested_terminal_replica_subset():
    sample = root()
    censored = dict(sample, censored=True)
    assert not module.estimate_root(censored, prefixes([5, 9]), Model())["complete"]
    sample["prefixes"]["SPACE_1"][1]["full_target"] = None
    assert not module.estimate_root(sample, prefixes([5, 9]), Model())["complete"]
    subset = module.estimate_root(sample, prefixes([5, 9]), Model(), full_replicas=1)
    assert subset["complete"] and subset["estimates"]["MC"]["SPACE_1"] == [10, 0, 0]
    assert subset["details"]["SPACE_1"]["corrected_variance_of_mean"] is None


def test_absorbing_boundaries_do_not_add_terminal_outcomes_twice():
    candidate = dict(direct=[2, 0, 1], boundary_board=[10] * 16, status="WON")
    reference = dict(direct=[1, 1, 0], boundary_board=[1] * 16, status="LOST")
    assert module.compose_pair(candidate, reference, None, "reward") == [1, -1, 1]
    active = dict(direct=[1, 0, 0], boundary_board=[3] + BOARD[1:], status="ACTIVE")
    assert module.compose_pair(candidate, active, Model(), "reward") == [-2, 0, 1]
    assert module.compose_pair(active, candidate, Model(), "reward") == [2, 0, -1]
    with pytest.raises(ValueError, match="incomplete prefix"):
        module.compose_pair(dict(active, status="CUTOFF"), candidate, Model(), "reward")


def test_real_four_action_prefixes_keep_active_boundaries_and_aligned_draws():
    rule = LearnedDynamics(RewriteProgram(True, "equal", 1, "once", "output_value"),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), "uniform")
    sample = root()
    before = deepcopy(sample)
    seed = 112_990_000_000
    observed, raw, log = module.collect_prefixes(sample, rule, seed, replicas=2)
    LEDGER.update({"ground_" + key: value for key, value in log["ground_work"].items()})
    LEDGER.update({"planning_" + key: value for key, value in log["planning_counts"].items()})
    assert sample == before and log["ground_work"]["sampled_transitions"] == 40
    assert log["outcomes"] == {"ACTIVE": 10} and all(log["wiring"].values())
    for item in raw:
        assert item["env_seed"] == seed + item["replica"]
        assert item["model_seed"] == item["env_seed"] + 1_000_000_000_000
        assert item["game"]["status"] == "CUTOFF" and item["game"]["steps_count"] == 4
        assert item["game"]["work"]["environment_random_draws"] == 8
        assert item["planning_counts"]["model_uniform_draws"] == 16
        prefix = observed[item["option"]][item["replica"]]
        assert prefix["status"] == "ACTIVE" and prefix["full_target"] is None
        assert prefix["direct"][1:] == [0, 0]
        duration = 0 if item["option"] == "H2" else int(item["option"].split("_")[1])
        assert item["action_paths"] == ["fragment"] * duration + ["H2"] * (4 - duration)


@pytest.fixture(scope="module")
def fitted():
    roots = [dict(root(query, episode), censored=episode == 3)
             for query in module.QUERIES for episode in range(6)]
    independent = {module._key(row): prefixes([5, 9]) for row in roots}
    models = {"full": Model(10), "fold_0": Model(2, 0), "fold_1": Model(3, 1)}
    before = deepcopy((roots, independent))
    result = module.fit_selectors(roots, independent, models, checkpoint=5)
    assert (roots, independent) == before
    LEDGER.update(result[-1]["counts"])
    return result


def test_three_identical_capacity_heads_use_oof_labels_and_roundtrip_json(fitted):
    selectors, rows, log = fitted
    assert log["counts"]["tree_fits"] == 6 and log["oof_episode_isolation"]
    assert log["future_roots_excluded"] == log["censored_roots_excluded"] == 2
    for method in module.METHODS:
        assert len(rows[method]) == 32
        assert log["head_fits"][method]["training_roots"] == 6
        assert log["head_fits"][method]["heldout_roots"] == 2
        selector = selectors[method]
        restored = module.JointSelector.from_payload(json.loads(json.dumps(selector.to_payload())))
        assert restored.select(BOARD, "reward") == selector.select(BOARD, "reward")
    for row in rows["CORRECTED"]:
        factor = 10 if row["episode"] == 4 else 2 if row["episode"] % 2 == 0 else 3
        assert row["target"] == [12 + factor * 5, 0, 0]


def test_source_episode_or_future_tail_leak_is_rejected_before_head_fit(monkeypatch):
    models = {"full": Model(), "fold_0": Model(fold=0), "fold_1": Model(fold=1)}
    models["fold_0"].training_episodes["risk_goal"].append(0)
    def forbidden(*args, **kwargs):
        raise AssertionError("leaked model must not reach selector fitting")
    monkeypatch.setattr(module.JointSelector, "fit", forbidden)
    with pytest.raises(ValueError, match="isolation"):
        module.fit_selectors([root()], {}, models, 5)
