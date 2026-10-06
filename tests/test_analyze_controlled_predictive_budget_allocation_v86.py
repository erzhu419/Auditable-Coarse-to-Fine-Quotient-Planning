"""Detect unequal actual budgets, arm-specific censoring and reused-work inflation."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("allocation_analysis_v86", ROOT /
    "scripts/analyze_controlled_predictive_budget_allocation_v86.py")
ANALYSIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYSIS)
CALLS = []


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_budget_allocation_v86.analysis_checks.json"
    ledger = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    ledger["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        synthetic_analysis_calls=len(CALLS), main_campaign_calls=0, ground_calls=0))
    path.write_text(json.dumps(ledger, indent=2) + "\n")


def _run():
    methods = ["H2_ONLY", "FROZEN_V85", "COVERAGE", "REPEAT"]
    queries = {"reward": {}, "risk_goal": {}}
    run = dict(status="complete", settings=dict(lifecycles=[0, 1, 2], methods=methods, queries=queries,
        budget_per_query=1000, branch_replicas=8, validation_roots_per_query=4,
        validation_replicas=16, evaluation_replicas=2, workers=3), lifecycles=[], actual_wall_seconds=10)
    for life in range(3):
        allocation = {}
        for arm in ("COVERAGE", "REPEAT"):
            added = 3 if arm == "COVERAGE" else 0
            training = 20 + 2 * added
            allocation[arm] = dict(queries={query: dict(budget=1000, used_transitions=1000,
                source_work={"sampled_transitions": 100 if arm == "COVERAGE" else 0},
                branch_work={"sampled_transitions": 900 if arm == "COVERAGE" else 1000},
                source_games=4 if arm == "COVERAGE" else 0, branch_trajectories=123 if arm == "COVERAGE" else 163,
                completed_blocks=3 if arm == "COVERAGE" else 4, incomplete_blocks=1,
                training_roots_added=added, seconds=1) for query in queries},
                dataset=dict(roots=training + 4, training_roots=training, heldout_roots=4, records=4 * (training + 4)),
                update=dict(counts=dict(tree_fits=2, fit_roots=training, fit_output_vectors=4 * training)), construction_seconds=3)
        methods_payload = {}
        for method in methods:
            delta = [-2, 1, 10][life] if method == "COVERAGE" else 0
            length = 0 if method == "H2_ONLY" else 4
            games = [dict(seed=life * 100 + replica, replica=replica, query=query,
                score=2048 * (100 + delta), utility=100 + delta - (4 if query == "risk_goal" else 0),
                status="LOST", steps=10, max_rank=8, seconds=0.1,
                environment_counts={"sampled_transitions": 10}, planning_counts={"model_uniform_draws": 40},
                selected_option="SPACE_4" if length else None, initiation_step=2 if length else None,
                fragment_actions=length, duration_budget=length, controller_events=1 if length else 0,
                selector_checkpoint=12 if length else None, committed_length_matches=True)
                for query in queries for replica in range(2)]
            methods_payload[method] = dict(games=games, costs=dict(evaluation_seconds=0.4,
                inherited_construction_seconds=0 if method == "H2_ONLY" else 100,
                new_construction_seconds=3 if method in ("COVERAGE", "REPEAT") else 0))
        run["lifecycles"].append(dict(id=life, allocation=allocation,
            validation=dict(source_work={"sampled_transitions": 10}, branch_work={"sampled_transitions": 1000},
                source_games=8, roots=8, complete_roots=8, incomplete_roots=0, branch_trajectories=640, seconds=2),
            evaluation=dict(methods=methods_payload, wiring={name: True for name in ANALYSIS.WIRING},
                pairwise_histories={method: dict(pairs=4, identical_to_h2=4 if method == "H2_ONLY" else 0) for method in methods},
                query_response={method: dict(pairs=2, identical_trajectory_pairs=2) for method in methods}),
            inherited=dict(source_work={"sampled_transitions": 10000}, branch_work={"sampled_transitions": 20000},
                joint_fit_counts={"tree_fits": 4, "fit_roots": 30}, residual_fit_counts={"tree_fits": 4, "fit_roots": 30},
                construction_seconds=100)))
    return run


def _analyze(run, name):
    CALLS.append(name)
    return ANALYSIS.analyze_run(run)


def test_budget_allocation_counts_incomplete_blocks_but_keeps_validation_separate():
    result = _analyze(_run(), "matched_actual_acquisition")
    assert result["complete"]
    effect = result["final_comparisons"]["COVERAGE_minus_REPEAT"]["reward"]
    assert [row["mean_utility_delta"] for row in effect["lifecycles"]] == [-2, 1, 10]
    assert effect["mean_utility_delta"] == 3
    assert effect["negative_lifecycles"] == 1
    work = result["actual_executed_work"]
    assert work["new_acquisition_transitions"] == 12000
    assert work["new_validation_transitions"] == 3030
    assert work["new_evaluation_transitions"] == 480
    assert work["newly_sampled_transitions"] == 15510
    assert work["acquisition"]["COVERAGE"]["counts"]["incomplete_blocks"] == 6
    assert work["acquisition"]["COVERAGE"]["counts"]["training_roots_added"] == 18
    assert work["acquisition"]["COVERAGE"]["fit_counts"]["fit_roots"] == 78
    assert work["acquisition"]["REPEAT"]["fit_counts"]["fit_roots"] == 60
    assert result["inherited"]["source_work"]["sampled_transitions"] == 30000
    assert result["inherited"]["branch_work"]["sampled_transitions"] == 60000
    assert result["inherited"]["residual_fit_counts"]["tree_fits"] == 12


def test_any_arm_cutoff_removes_the_replica_from_all_comparisons_and_retains_cost():
    run = _run()
    methods = run["lifecycles"][0]["evaluation"]["methods"]
    methods["FROZEN_V85"]["games"][0]["status"] = "CUTOFF"
    methods["COVERAGE"]["games"][0]["score"] += 2048000
    methods["COVERAGE"]["games"][0]["utility"] += 1000
    result = _analyze(run, "common_four_method_cohort")
    assert result["complete"]
    assert not result["cohort"]["all_evaluation_games_terminal"]
    for name, comparison in result["final_comparisons"].items():
        assert comparison["reward"]["lifecycles"][0]["pairs"] == 1
        assert comparison["reward"]["mean_utility_delta"] == (3 if name.startswith("COVERAGE") else 0)
    assert result["actual_executed_work"]["newly_sampled_transitions"] == 15510


def test_nominal_budget_matching_missing_pairs_and_bad_training_units_fail_completeness():
    for name in ("actual_budget", "missing_game", "duplicate_game", "fit_roots", "validation", "wiring"):
        run = deepcopy(_run())
        life = run["lifecycles"][0]
        if name == "actual_budget":
            life["allocation"]["REPEAT"]["queries"]["reward"]["branch_work"]["sampled_transitions"] -= 1
        elif name == "missing_game":
            life["evaluation"]["methods"]["COVERAGE"]["games"].pop()
        elif name == "duplicate_game":
            games = life["evaluation"]["methods"]["COVERAGE"]["games"]
            games[0] = deepcopy(games[1])
        elif name == "fit_roots":
            life["allocation"]["COVERAGE"]["update"]["counts"]["fit_roots"] += 1
        elif name == "validation":
            life["validation"]["roots"] -= 1
        else:
            life["evaluation"]["wiring"]["single_initiations"] = False
        assert not _analyze(run, name)["complete"]


def test_validation_source_without_trigger_retains_cost_without_requiring_branches():
    run = _run()
    validation = run["lifecycles"][0]["validation"]
    validation.update(complete_roots=7, incomplete_roots=1, branch_trajectories=560)
    validation["branch_work"]["sampled_transitions"] = 900
    result = _analyze(run, "validation_source_missing_trigger")
    assert result["complete"]
    assert result["validation"]["counts"]["source_games"] == 24
    assert result["validation"]["counts"]["complete_roots"] == 23
    assert result["validation"]["counts"]["incomplete_roots"] == 1
    assert result["validation"]["counts"]["branch_trajectories"] == 1840
    assert result["actual_executed_work"]["new_validation_transitions"] == 2930
    assert result["actual_executed_work"]["newly_sampled_transitions"] == 15410
    for comparison in result["final_comparisons"].values():
        assert comparison["reward"]["lifecycles"][0]["pairs"] == 2
