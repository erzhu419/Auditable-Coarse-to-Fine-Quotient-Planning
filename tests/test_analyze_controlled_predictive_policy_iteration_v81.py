"""Detect false improvement from incomplete pairing and repeated source counts."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("v81_analysis", ROOT /
    "scripts/analyze_controlled_predictive_policy_iteration_v81.py")
ANALYSIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYSIS)
CALLS = []


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_policy_iteration_v81.analysis_checks.json"
    ledger = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    ledger["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        synthetic_analysis_calls=len(CALLS), main_campaign_calls=0, ground_calls=0))
    path.write_text(json.dumps(ledger, indent=2) + "\n")


def _run():
    methods = ["H2_ONLY", "CURRENT", "FROZEN_1", "SHORT_REF", "TERMINAL_REF"]
    run = dict(status="complete", settings=dict(lifecycles=[0, 1, 2], iterations=[1, 2],
        queries={"reward": {}, "risk_goal": {}}, methods=methods, evaluation_replicas=2),
        lifecycles=[], actual_wall_seconds=20)
    for life in range(3):
        rounds = []
        for iteration in (1, 2):
            per_method = {}
            for method in methods:
                value = [-2, 1, 10][life] if method == "CURRENT" and iteration == 2 else 0
                games = [dict(seed=100 * life + replica, replica=replica, query=query,
                    status="LOST", score=2048 * (value + 3), utility=value + 3 - (4 if query == "risk_goal" else 0),
                    steps=2, max_rank=1, seconds=0.1, decisions=2, top_layer_overrides=1 if method == "CURRENT" else 0,
                    environment_counts={"sampled_transitions": 2},
                    planning_counts={"model_spawn_samples": 4}, prediction_counts={})
                    for query in ("reward", "risk_goal") for replica in range(2)]
                per_method[method] = dict(games=games, costs=dict(total_seconds=iteration))
            rounds.append(dict(iteration=iteration, methods=per_method,
                behavior=dict(policy_iteration=iteration - 1, games=24, outcomes={"LOST": 24},
                    work={"sampled_transitions": 48}, planning_counts={"model_spawn_samples": 96},
                    state_coverage=dict(unique_observations=24, new_vs_prior=24, root_observations=12)),
                branches=dict(continuation_iteration=iteration - 1, roots=2, trajectories=4, censored_roots=1,
                    outcomes={"LOST": 3, "CUTOFF": 1}, work={"sampled_transitions": 20},
                    continuation_work={"model_spawn_samples": 40}, known_model_counts={"learned_swipe_calls": 4}),
                dataset=dict(records=10, training_records=8, heldout_records=2,
                    queries={query: dict(training_records=4, heldout_records=1,
                        nonzero_failure_deltas=0, nonzero_success_deltas=0) for query in ("reward", "risk_goal")},
                    replica_noise=dict(pairs=10, mean_abs_component_difference=[2, 0, 0], reward_sign_reversals=3),
                    root_state_coverage=dict(unique=2, new_vs_prior=2)),
                update=dict(iteration=iteration, parent_iteration=iteration - 1, input_records=10,
                    training_records=8, heldout_records=2, queries={}, counts={"tree_fits": 2}),
                query_response={method: dict(pairs=2, identical_trajectory_pairs=2) for method in methods}))
        run["lifecycles"].append(dict(id=life, rounds=rounds))
    return run


def _analyze(run, label):
    CALLS.append(label)
    return ANALYSIS.analyze_run(run)


def test_lifecycle_counterexample_and_distinct_sampling_sources():
    run = _run()
    run["lifecycles"][0]["rounds"][-1]["methods"]["CURRENT"]["games"][0]["status"] = "CUTOFF"
    result = _analyze(run, "complete_with_cutoff")
    assert result["complete"]
    assert result["cohort"]["games"] == result["cohort"]["expected_games"] == 120
    assert result["cohort"]["cutoff_games"] == 1
    assert not result["cohort"]["all_evaluation_games_terminal"]
    comparison = result["final_comparisons"]["CURRENT_minus_H2_ONLY"]["reward"]
    assert comparison["lifecycle_mean_deltas"] == [-2, 1, 10]
    assert comparison["mean_delta"] == 3
    assert comparison["mean_score_delta"] == 6144
    assert comparison["positive_lifecycles"] == 2
    assert comparison["negative_lifecycles"] == 1
    assert result["first_to_last_iteration_utility_change"]["CURRENT"]["reward"]["mean_delta"] == 3
    assert result["iterations"][-1]["methods"]["CURRENT"]["cumulative_costs"]["totals"]["total_seconds"] == 6
    assert result["paired_query_trajectories"]["pairs"] == 60
    assert result["iterations"][-1]["methods"]["CURRENT"]["queries"]["reward"]["pooled"]["top_layer_override_rate"] == 0.5
    work = result["actual_executed_work"]
    assert work["new_behavior_counts"]["sampled_transitions"] == 288
    assert work["new_branch_counts"]["sampled_transitions"] == 120
    assert work["newly_sampled_transitions"] == 648
    assert work["new_model_fit_counts"]["tree_fits"] == 12
    assert work["branch_outcomes"]["CUTOFF"] == 6
    assert result["learning_sources"]["totals"]["replica_noise"]["mean_abs_component_difference"] == [2, 0, 0]
    assert result["learning_sources"]["totals"]["replica_noise"]["reward_sign_reversal_fraction"] == 0.3


def test_missing_duplicate_control_drift_and_wrong_parent_are_not_complete():
    original = _run()
    missing = deepcopy(original)
    missing["lifecycles"][0]["rounds"].pop()
    result = _analyze(missing, "missing_round")
    assert not result["complete"]
    assert not result["cohort"]["lifecycle_roster_complete"]
    assert result["final_comparisons"]["CURRENT_minus_H2_ONLY"]["reward"]["mean_delta"] is None
    duplicate = deepcopy(original)
    games = duplicate["lifecycles"][1]["rounds"][0]["methods"]["CURRENT"]["games"]
    games[1] = deepcopy(games[0])
    assert not _analyze(duplicate, "duplicate_game")["complete"]
    drift = deepcopy(original)
    drift["lifecycles"][0]["rounds"][-1]["methods"]["FROZEN_1"]["games"][0]["score"] += 4
    result = _analyze(drift, "control_drift")
    assert not result["complete"]
    assert not result["cohort"]["fixed_controls_unchanged"]
    initial_drift = deepcopy(original)
    initial_drift["lifecycles"][0]["rounds"][0]["methods"]["CURRENT"]["games"][0]["score"] += 4
    assert not _analyze(initial_drift, "first_round_drift")["cohort"]["first_round_current_matches_frozen"]
    wrong_parent = deepcopy(original)
    wrong_parent["lifecycles"][0]["rounds"][-1]["branches"]["continuation_iteration"] = 0
    result = _analyze(wrong_parent, "wrong_parent")
    assert not result["complete"]
    assert not result["cohort"]["parent_lineage_complete"]
