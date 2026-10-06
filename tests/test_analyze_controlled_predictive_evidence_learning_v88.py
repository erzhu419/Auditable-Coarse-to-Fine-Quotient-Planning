"""Check intervention attribution and shared terminal cohorts with known paired effects."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("evidence_learning_analysis_v88", ROOT /
    "scripts/analyze_controlled_predictive_evidence_learning_v88.py")
ANALYSIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYSIS)


def _changes(evaluation):
    result = {}
    for left, right in ANALYSIS.GATE_CONTRASTS:
        old = {ANALYSIS._key(game): game for game in evaluation["methods"][right]["games"]}
        result[f"{left}_minus_{right}"] = [dict(seed=game["seed"], query=game["query"], replica=game["replica"],
            old_option=old[ANALYSIS._key(game)]["selected_option"], new_option=game["selected_option"],
            category=ANALYSIS._gate_category(old[ANALYSIS._key(game)]["selected_option"], game["selected_option"]))
            for game in evaluation["methods"][left]["games"]]
    return result


def _run():
    methods = ["H2_ONLY"] + [f"{arm}_{kind}" for arm in ANALYSIS.ARMS for kind in ("OLD", "POINT", "SUPPORTED")]
    queries = {"reward": {}, "risk_goal": {}}
    run = dict(status="complete", settings=dict(lifecycles=[0, 1, 2], methods=methods, queries=queries,
        evaluation_replicas=5, workers=3), lifecycles=[], actual_wall_seconds=10)
    for life in range(3):
        updates, allocation = {}, {}
        for arm in ANALYSIS.ARMS:
            training = 26 if arm == "COVERAGE" else 20
            updates[arm] = dict(dataset=dict(roots=training + 4, training_roots=training, heldout_roots=4,
                records=4 * (training + 4)), update=dict(counts=dict(tree_fits=2, fit_roots=training,
                fit_candidate_labels=4 * training)), preparation_seconds=0.1, fitting_seconds=1, export_seconds=0.01)
            allocation[arm] = dict(source_work={"sampled_transitions": 100 if arm == "COVERAGE" else 0},
                branch_work={"sampled_transitions": 1900 if arm == "COVERAGE" else 2000},
                fit_counts={"fit_roots": training, "tree_fits": 2}, construction_seconds=3)
        d = [-2, 1, 10][life]
        methods_payload = {}
        for method in methods:
            games = []
            for query in queries:
                for replica, category in enumerate(ANALYSIS.CATEGORIES):
                    old = "H2" if category in ("enabled", "both_h2") else "SPACE_4"
                    new = "H2" if category in ("disabled", "both_h2") else (
                        "SNAKE_4" if category == "changed_fragment" else "SPACE_4")
                    if method == "H2_ONLY":
                        option, extra = None, 0
                    elif method.endswith("_SUPPORTED"):
                        option = new
                        extra = 5 * d if category in ("enabled", "changed_fragment") else 10 * d if category == "same_fragment" else 0
                    else:
                        option = old
                        extra = -5 * d if category in ("disabled", "changed_fragment") else 10 * d if category == "same_fragment" else 0
                    length = 4 if option in ("SPACE_4", "SNAKE_4") else 0
                    games.append(dict(seed=life * 100 + replica, replica=replica, query=query,
                        score=2048 * (100 + extra), utility=100 + extra - (4 if query == "risk_goal" else 0),
                        status="LOST", steps=10, max_rank=8, seconds=0.1,
                        environment_counts={"sampled_transitions": 10}, planning_counts={"model_uniform_draws": 40},
                        selected_option=option, initiation_step=2 if method != "H2_ONLY" else None,
                        fragment_actions=length, duration_budget=length, controller_events=int(method != "H2_ONLY"),
                        selector_checkpoint=12 if method != "H2_ONLY" else None, committed_length_matches=True))
            methods_payload[method] = dict(games=games, costs=dict(evaluation_seconds=1,
                inherited_construction_seconds=0 if method == "H2_ONLY" else 100,
                inherited_v86_base_load_seconds=0 if method == "H2_ONLY" else 0.1,
                new_fitting_seconds=1 if method.endswith(("_POINT", "_SUPPORTED")) else 0))
        evaluation = dict(methods=methods_payload, wiring={name: True for name in ANALYSIS.WIRING},
            pairwise_histories={method: dict(pairs=10, identical_to_h2=10 if method == "H2_ONLY" else 4) for method in methods},
            query_response={method: dict(pairs=5, identical_trajectory_pairs=5) for method in methods})
        evaluation["gate_changes"] = _changes(evaluation)
        run["lifecycles"].append(dict(id=life, updates=updates,
            inherited=dict(source_work={"sampled_transitions": 10000}, branch_work={"sampled_transitions": 20000},
                joint_fit_counts={"tree_fits": 4, "fit_roots": 30}, residual_fit_counts={"tree_fits": 4, "fit_roots": 30},
                allocation=allocation, construction_seconds=100, v86_base_load_seconds=0.1), evaluation=evaluation))
    return run


def test_changed_fragment_and_h2_recovery_are_separate_additive_contributions():
    result = ANALYSIS.analyze_run(_run())
    assert result["complete"]
    for left, right in ANALYSIS.GATE_CONTRASTS:
        contrast = f"{left}_minus_{right}"
        effect = result["final_comparisons"][contrast]["reward"]
        assert [row["mean_utility_delta"] for row in effect["lifecycles"]] == [-8, 4, 40]
        assert effect["mean_utility_delta"] == 12
        decomposition = result["gate_decomposition"][contrast]["reward"]
        categories = decomposition["categories"]
        assert categories["enabled"]["old"]["mean_utility_contribution"] == 3
        assert categories["disabled"]["old"]["mean_utility_contribution"] == 3
        assert categories["changed_fragment"]["old"]["mean_utility_contribution"] == 6
        assert categories["changed_fragment"]["old"]["conditional_mean_utility_delta"] == 30
        assert categories["same_fragment"]["old"]["mean_utility_contribution"] == 0
        assert categories["disabled"]["h2"]["mean_utility_contribution"] == 0
        assert decomposition["summed_contributions"]["old"]["utility"] == 12
        assert decomposition["summed_contributions"]["h2"]["utility"] == 12


def test_cutoff_is_dropped_jointly_from_seven_methods_but_cost_is_retained():
    run = _run()
    run["lifecycles"][0]["evaluation"]["methods"]["REPEAT_OLD"]["games"][0]["status"] = "CUTOFF"
    result = ANALYSIS.analyze_run(run)
    assert result["complete"] and not result["cohort"]["all_evaluation_games_terminal"]
    for left, right in ANALYSIS.GATE_CONTRASTS:
        contrast = f"{left}_minus_{right}"
        effect = result["final_comparisons"][contrast]["reward"]
        assert effect["mean_utility_delta"] == pytest.approx(73 / 6)
        decomposition = result["gate_decomposition"][contrast]["reward"]
        enabled = decomposition["categories"]["enabled"]
        assert enabled["raw_cases"] == 3 and enabled["pairs"] == 2
        assert enabled["old"]["mean_utility_contribution"] == pytest.approx(11 / 3)
        assert decomposition["summed_contributions"]["old"]["utility"] == pytest.approx(effect["mean_utility_delta"])
    assert result["actual_executed_work"]["newly_sampled_transitions"] == 2100
    assert result["actual_executed_work"]["new_fit_counts"]["COVERAGE"]["fit_candidate_labels"] == 312
    assert result["inherited"]["allocation"]["REPEAT"]["branch_work"]["sampled_transitions"] == 6000
    assert result["inherited"]["source_work"]["sampled_transitions"] == 30000
    assert result["methods"]["REPEAT_OLD"]["cumulative_cost_attribution"]["totals"]["evaluation_seconds"] == 3


def test_h2_fallback_benefit_does_not_become_new_intervention_success():
    run = _run()
    for life in run["lifecycles"]:
        evaluation = life["evaluation"]
        for arm in ANALYSIS.ARMS:
            for game in evaluation["methods"][arm + "_SUPPORTED"]["games"]:
                game.update(selected_option="H2", score=204800, utility=100 if game["query"] == "reward" else 96,
                    fragment_actions=0, duration_budget=0)
        evaluation["gate_changes"] = _changes(evaluation)
    result = ANALYSIS.analyze_run(run)
    assert result["complete"]
    data = result["gate_decomposition"]["COVERAGE_SUPPORTED_minus_COVERAGE_POINT"]["reward"]
    assert data["categories"]["enabled"]["pairs"] == data["categories"]["changed_fragment"]["pairs"] == 0
    assert data["categories"]["disabled"]["pairs"] == 9
    assert data["categories"]["disabled"]["h2"]["mean_utility_contribution"] == 0


def test_empty_terminal_lifecycle_is_unestimable_not_zero_effect():
    run = _run()
    for game in run["lifecycles"][0]["evaluation"]["methods"]["REPEAT_OLD"]["games"]:
        if game["query"] == "reward":
            game["status"] = "CUTOFF"
    result = ANALYSIS.analyze_run(run)
    effect = result["final_comparisons"]["COVERAGE_SUPPORTED_minus_COVERAGE_POINT"]["reward"]
    assert effect["mean_utility_delta"] is None
    data = result["gate_decomposition"]["COVERAGE_SUPPORTED_minus_COVERAGE_POINT"]["reward"]
    assert not data["all_lifecycles_estimable"]
    assert data["summed_contributions"]["old"]["utility"] is None
    assert result["actual_executed_work"]["newly_sampled_transitions"] == 2100


def test_incomplete_or_mislabeled_records_do_not_pass():
    for defect in ("missing_game", "candidate_label_units", "extra_fits", "gate_label", "changed_option", "wiring"):
        run = deepcopy(_run())
        life = run["lifecycles"][0]
        if defect == "missing_game":
            life["evaluation"]["methods"]["COVERAGE_SUPPORTED"]["games"].pop()
        elif defect == "candidate_label_units":
            life["updates"]["COVERAGE"]["update"]["counts"]["fit_candidate_labels"] //= 4
        elif defect == "extra_fits":
            life["updates"]["COVERAGE"]["update"]["counts"]["tree_fits"] = 4
        elif defect == "gate_label":
            life["evaluation"]["gate_changes"]["COVERAGE_SUPPORTED_minus_COVERAGE_POINT"][0]["category"] = "disabled"
        elif defect == "changed_option":
            life["evaluation"]["methods"]["COVERAGE_SUPPORTED"]["games"][3]["selected_option"] = "SNAKE_4"
        else:
            life["evaluation"]["wiring"]["point_supported_predictions_match"] = False
        assert not ANALYSIS.analyze_run(run)["complete"], defect
