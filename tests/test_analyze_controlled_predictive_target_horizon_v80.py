"""Lifecycle counterexamples, paired labels and nonduplicated sample accounting."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("v80_analysis", ROOT /
    "scripts/analyze_controlled_predictive_target_horizon_v80.py")
ANALYSIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYSIS)
CALLS = []


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_target_horizon_v80.analysis_checks.json"
    ledger = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    ledger["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        synthetic_analysis_calls=len(CALLS), main_campaign_calls=0, ground_calls=0))
    path.write_text(json.dumps(ledger, indent=2) + "\n")


def _run():
    methods = ["H2_ONLY", "SHORT_PLAN", "TERMINAL_PLAN", "SHORT_FROZEN", "TERMINAL_FROZEN"]
    run = dict(status="complete", settings=dict(lifecycles=[0, 1, 2], checkpoints=[15, 39, 75],
        queries={"reward": {}, "risk_goal": {}}, methods=methods, evaluation_replicas=2),
        lifecycles=[], actual_wall_seconds=20)
    for life in range(3):
        stages = []
        for episodes in (15, 39, 75):
            per_method = {}
            for method in methods:
                value = [-2, 1, 10][life] if method == "TERMINAL_PLAN" else 0
                games = [dict(seed=100 * life + replica, replica=replica, query=query,
                    status="LOST", score=2048 * (value + 3), utility=value + 3 - (4 if query == "risk_goal" else 0),
                    steps=2, max_rank=1, seconds=0.1,
                    environment_counts={"sampled_transitions": 2},
                    planning_counts={"model_spawn_samples": 4}, prediction_counts={})
                    for query in ("reward", "risk_goal") for replica in range(2)]
                per_method[method] = dict(games=games, costs=dict(total_seconds=episodes / 15))
            fit = dict(checkpoint=episodes, input_records=10, prefix_records=10,
                future_records_excluded=0, training_records=8, heldout_records=2,
                feature_context_horizon=30, policies={policy: dict(training_rows=8,
                    heldout_rows=2, training_target_mean=[1, 1, 0])
                    for policy in ("GREEDY", "SPACE", "SNAKE")}, counts={"tree_fits": 3})
            stages.append(dict(episodes=episodes, source_summary=dict(episodes=episodes,
                work={"sampled_transitions": 2 * episodes}), methods=per_method,
                dataset=dict(paired_records=10, discarded_records=2),
                models={scope: dict(fit_log=dict(target_scope=scope, **deepcopy(fit)))
                        for scope in ("SHORT", "TERMINAL")},
                branch_completion=dict(prefix_work={"sampled_transitions": 10},
                    new_work={"sampled_transitions": 20}, trajectories=2,
                    outcomes={"LOST": 1, "CUTOFF": 1})))
        run["lifecycles"].append(dict(id=life, stages=stages))
    return run


def _analyze(run, label):
    CALLS.append(label)
    return ANALYSIS.analyze_run(run)


def test_counterexample_and_distinct_inherited_and_new_sample_budgets():
    run = _run()
    run["lifecycles"][0]["stages"][-1]["methods"]["TERMINAL_PLAN"]["games"][0]["status"] = "CUTOFF"
    result = _analyze(run, "complete_with_cutoff")
    assert result["complete"]
    assert result["cohort"]["games"] == result["cohort"]["expected_games"] == 180
    assert result["cohort"]["cutoff_games"] == 1
    assert not result["cohort"]["all_evaluation_games_terminal"]
    comparison = result["final_comparisons"]["TERMINAL_PLAN_minus_SHORT_PLAN"]["reward"]
    assert comparison["lifecycle_mean_deltas"] == [-2, 1, 10]
    assert comparison["mean_delta"] == 3
    assert comparison["mean_score_delta"] == 6144
    assert comparison["positive_lifecycles"] == 2
    assert comparison["negative_lifecycles"] == 1
    work = result["actual_executed_work"]
    assert work["inherited_natural_source_once_counts"]["sampled_transitions"] == 450
    assert work["inherited_training_branch_prefix_counts"]["sampled_transitions"] == 90
    assert work["new_training_branch_suffix_counts"]["sampled_transitions"] == 180
    assert work["newly_sampled_transitions"] == 540
    assert work["branch_completion"]["outcomes"]["CUTOFF"] == 9
    assert work["model_fit_counts"]["tree_fits"] == 54
    assert all(row["terminal_training_failure_is_constant_one"] for row in result["labels"])
    assert all(row["terminal_training_success_is_constant_zero"] for row in result["labels"])
    outcomes = result["paired_query_outcomes"]
    assert outcomes["pairs"] == 90
    assert outcomes["identical_outcomes"] == 89
    costs = result["checkpoints"][-1]["methods"]["TERMINAL_PLAN"]["cumulative_costs"]
    assert costs["totals"]["total_seconds"] == 15


def test_missing_duplicate_control_drift_and_unmatched_fit_rows_remain_visible():
    original = _run()
    missing = deepcopy(original)
    missing["lifecycles"][0]["stages"].pop()
    result = _analyze(missing, "missing_stage")
    assert not result["complete"]
    assert not result["cohort"]["lifecycle_roster_complete"]
    assert result["final_comparisons"]["TERMINAL_PLAN_minus_SHORT_PLAN"]["reward"]["mean_delta"] is None
    duplicate = deepcopy(original)
    games = duplicate["lifecycles"][1]["stages"][0]["methods"]["SHORT_PLAN"]["games"]
    games[1] = deepcopy(games[0])
    assert not _analyze(duplicate, "duplicate_game")["complete"]
    drift = deepcopy(original)
    drift["lifecycles"][0]["stages"][-1]["methods"]["TERMINAL_FROZEN"]["games"][0]["score"] += 4
    result = _analyze(drift, "control_drift")
    assert not result["complete"]
    assert not result["cohort"]["fixed_controls_unchanged"]
    unmatched = deepcopy(original)
    unmatched["lifecycles"][0]["stages"][-1]["models"]["TERMINAL"]["fit_log"]["training_records"] += 1
    result = _analyze(unmatched, "unmatched_fit")
    assert not result["complete"]
    assert not result["cohort"]["matched_training_rows"]
