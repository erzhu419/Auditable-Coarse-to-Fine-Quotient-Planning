"""Aggregation must retain lifecycle counterexamples and incomplete cohorts."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("v78_analysis", ROOT /
    "scripts/analyze_controlled_predictive_decision_v78.py")
ANALYSIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYSIS)
CALLS = []


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_decision_v78.analysis_checks.json"
    ledger = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    ledger["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        synthetic_analysis_calls=len(CALLS), main_campaign_calls=0, ground_calls=0))
    path.write_text(json.dumps(ledger, indent=2) + "\n")


def _run():
    methods = ["H2_ONLY", "FROZEN_PLAN", "FIXED_PLAN", "MSE_PLAN", "DECISION_PLAN"]
    run = dict(status="complete", settings=dict(lifecycles=[0, 1, 2], checkpoints=[39, 75],
        queries={"reward": {}, "risk_goal": {}}, methods=methods, evaluation_replicas=2),
        lifecycles=[], actual_wall_seconds=20)
    for life in range(3):
        stages = []
        for episodes in (39, 75):
            per_method = {}
            for method in methods:
                value = [-2, 1, 10][life] if method == "DECISION_PLAN" else 0
                games = [dict(seed=100 * life + replica, replica=replica, query=query,
                    status="LOST", score=2048 * value, utility=value, steps=2, max_rank=1,
                    seconds=0.1, environment_counts={"sampled_transitions": 2},
                    planning_counts={"model_spawn_samples": 4}, prediction_counts={})
                    for query in ("reward", "risk_goal") for replica in range(2)]
                per_method[method] = dict(games=games, costs=dict(total_seconds=1 if episodes == 39 else 3))
            stages.append(dict(episodes=episodes, source_summary=dict(episodes=episodes,
                work={"sampled_transitions": 2 * episodes}), methods=per_method,
                training_branches={"work": {"sampled_transitions": 10}},
                acceptance_rollouts={"work": {"sampled_transitions": 20}},
                mse_acceptance={"accepted": life != 0}, decision_acceptance={"accepted": life == 2}))
        run["lifecycles"].append(dict(id=life, stages=stages))
    return run


def _analyze(run, label):
    CALLS.append(label)
    return ANALYSIS.analyze_run(run)


def test_aggregation_retains_lifecycle_counterexample_and_separates_work():
    run = _run()
    run["lifecycles"][0]["stages"][-1]["methods"]["DECISION_PLAN"]["games"][0]["status"] = "CUTOFF"
    result = _analyze(run, "complete_with_cutoff")
    assert result["complete"]
    assert result["cohort"]["games"] == result["cohort"]["expected_games"] == 120
    assert result["cohort"]["cutoff_games"] == 1
    assert not result["cohort"]["all_evaluation_games_terminal"]
    comparison = result["final_decision_plan_minus_comparator"]["MSE_PLAN"]["reward"]
    assert comparison["lifecycle_mean_deltas"] == [-2, 1, 10]
    assert comparison["mean_delta"] == 3
    assert comparison["mean_score_delta"] == 6144
    assert comparison["positive_lifecycles"] == 2
    assert comparison["negative_lifecycles"] == 1
    assert result["acceptance"]["mse"]["accepted"] == 4
    assert result["acceptance"]["decision"]["accepted"] == 2
    work = result["actual_executed_work"]
    assert work["inherited_source_once_counts"]["sampled_transitions"] == 450
    assert work["new_training_branch_counts"]["sampled_transitions"] == 60
    assert work["new_acceptance_rollout_counts"]["sampled_transitions"] == 120
    assert sum(v["environment"]["sampled_transitions"] for v in work["evaluation"].values()) == 240
    costs = result["checkpoints"][-1]["methods"]["DECISION_PLAN"]["cumulative_costs"]
    assert costs["totals"]["total_seconds"] == 9


def test_missing_stage_duplicate_game_and_control_drift_are_incomplete():
    original = _run()
    missing = deepcopy(original)
    missing["lifecycles"][0]["stages"].pop()
    result = _analyze(missing, "missing_stage")
    assert not result["complete"]
    assert not result["cohort"]["lifecycle_roster_complete"]
    assert result["final_decision_plan_minus_comparator"]["MSE_PLAN"]["reward"]["mean_delta"] is None
    duplicate = deepcopy(original)
    games = duplicate["lifecycles"][1]["stages"][0]["methods"]["FIXED_PLAN"]["games"]
    games[1] = deepcopy(games[0])
    assert not _analyze(duplicate, "duplicate_game")["complete"]
    drift = deepcopy(original)
    drift["lifecycles"][0]["stages"][-1]["methods"]["FROZEN_PLAN"]["games"][0]["score"] += 4
    result = _analyze(drift, "control_drift")
    assert not result["complete"]
    assert not result["cohort"]["fixed_controls_unchanged"]
