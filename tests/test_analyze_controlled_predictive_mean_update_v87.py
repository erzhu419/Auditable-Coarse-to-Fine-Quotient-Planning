"""Keep H2 recovery separate from enabled fragments and count one mean per root."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("mean_update_analysis_v87", ROOT /
    "scripts/analyze_controlled_predictive_mean_update_v87.py")
ANALYSIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYSIS)
CALLS = []


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_mean_update_v87.analysis_checks.json"
    ledger = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    ledger["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        synthetic_analysis_calls=len(CALLS), main_campaign_calls=0, ground_calls=0))
    path.write_text(json.dumps(ledger, indent=2) + "\n")


def _run():
    methods = ["H2_ONLY", "COVERAGE_OLD", "COVERAGE_MEAN", "REPEAT_OLD", "REPEAT_MEAN"]
    queries = {"reward": {}, "risk_goal": {}}
    run = dict(status="complete", settings=dict(lifecycles=[0, 1, 2], methods=methods, queries=queries,
        evaluation_replicas=4, workers=3), lifecycles=[], actual_wall_seconds=10)
    for life in range(3):
        updates, allocation = {}, {}
        for arm in ANALYSIS.ARMS:
            training = 26 if arm == "COVERAGE" else 20
            updates[arm] = dict(dataset=dict(roots=training + 4, training_roots=training, heldout_roots=4,
                records=4 * (training + 4)), update=dict(counts=dict(tree_fits=2, fit_roots=training,
                fit_output_vectors=training)), preparation_seconds=0.1, fitting_seconds=1, export_seconds=0.01)
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
                    new = "H2" if category in ("disabled", "both_h2") else "SPACE_4"
                    if method == "H2_ONLY":
                        option, extra = None, 0
                    elif method.endswith("_OLD"):
                        option = old
                        extra = -4 * d if category == "disabled" else 8 * d if category == "same_fragment" else 0
                    else:
                        option = new
                        extra = 4 * d if category == "enabled" else 8 * d if category == "same_fragment" else 0
                    length = 4 if option == "SPACE_4" else 0
                    games.append(dict(seed=life * 100 + replica, replica=replica, query=query,
                        score=2048 * (100 + extra), utility=100 + extra - (4 if query == "risk_goal" else 0),
                        status="LOST", steps=10, max_rank=8, seconds=0.1,
                        environment_counts={"sampled_transitions": 10}, planning_counts={"model_uniform_draws": 40},
                        selected_option=option, initiation_step=2 if method != "H2_ONLY" else None,
                        fragment_actions=length, duration_budget=length, controller_events=int(method != "H2_ONLY"),
                        selector_checkpoint=12 if method != "H2_ONLY" else None, committed_length_matches=True))
            methods_payload[method] = dict(games=games, costs=dict(evaluation_seconds=0.8,
                inherited_construction_seconds=0 if method == "H2_ONLY" else 100,
                new_fitting_seconds=1 if method.endswith("_MEAN") else 0))
        changes = {arm: [dict(seed=life * 100 + replica, replica=replica, query=query, category=category,
            old_option="H2" if category in ("enabled", "both_h2") else "SPACE_4",
            new_option="H2" if category in ("disabled", "both_h2") else "SPACE_4")
            for query in queries for replica, category in enumerate(ANALYSIS.CATEGORIES)] for arm in ANALYSIS.ARMS}
        run["lifecycles"].append(dict(id=life, updates=updates,
            inherited=dict(source_work={"sampled_transitions": 10000}, branch_work={"sampled_transitions": 20000},
                joint_fit_counts={"tree_fits": 4, "fit_roots": 30}, residual_fit_counts={"tree_fits": 4, "fit_roots": 30},
                allocation=allocation, construction_seconds=100),
            evaluation=dict(methods=methods_payload, wiring={name: True for name in ANALYSIS.WIRING},
                pairwise_histories={method: dict(pairs=8, identical_to_h2=8 if method == "H2_ONLY" else 4) for method in methods},
                query_response={method: dict(pairs=4, identical_trajectory_pairs=4) for method in methods}, gate_changes=changes)))
    return run


def _analyze(run, name):
    CALLS.append(name)
    return ANALYSIS.analyze_run(run)


def test_category_contributions_reconstruct_effect_without_inherited_work_inflation():
    result = _analyze(_run(), "mean_update_categories")
    assert result["complete"]
    effect = result["final_comparisons"]["COVERAGE_MEAN_minus_COVERAGE_OLD"]["reward"]
    assert [row["mean_utility_delta"] for row in effect["lifecycles"]] == [-4, 2, 20]
    assert effect["mean_utility_delta"] == 6
    decomposition = result["gate_decomposition"]["COVERAGE"]["reward"]
    assert decomposition["categories"]["enabled"]["old"]["conditional_mean_utility_delta"] == 12
    assert decomposition["categories"]["enabled"]["old"]["mean_utility_contribution"] == 3
    assert decomposition["categories"]["disabled"]["old"]["mean_utility_contribution"] == 3
    assert decomposition["categories"]["same_fragment"]["old"]["mean_utility_contribution"] == 0
    assert decomposition["summed_contributions"]["old"]["utility"] == 6
    assert decomposition["summed_contributions"]["h2"]["utility"] == 9
    assert result["actual_executed_work"]["newly_sampled_transitions"] == 1200
    assert result["actual_executed_work"]["new_fit_counts"]["COVERAGE"]["fit_output_vectors"] == 78
    assert result["inherited"]["allocation"]["REPEAT"]["branch_work"]["sampled_transitions"] == 6000
    assert result["inherited"]["source_work"]["sampled_transitions"] == 30000


def test_censoring_uses_common_denominator_before_equal_life_averaging():
    run = _run()
    games = run["lifecycles"][0]["evaluation"]["methods"]["REPEAT_OLD"]["games"]
    games[0]["status"] = "CUTOFF"
    result = _analyze(run, "unequal_terminal_denominators")
    assert result["complete"]
    assert not result["cohort"]["all_evaluation_games_terminal"]
    for arm in ANALYSIS.ARMS:
        effect = result["final_comparisons"][f"{arm}_MEAN_minus_{arm}_OLD"]["reward"]
        assert effect["mean_utility_delta"] == pytest.approx(58 / 9)
        decomposition = result["gate_decomposition"][arm]["reward"]
        enabled = decomposition["categories"]["enabled"]
        assert enabled["raw_cases"] == 3 and enabled["pairs"] == 2
        assert enabled["old"]["mean_utility_contribution"] == pytest.approx(11 / 3)
        assert decomposition["summed_contributions"]["old"]["utility"] == pytest.approx(effect["mean_utility_delta"])
    assert result["actual_executed_work"]["newly_sampled_transitions"] == 1200


def test_missing_cohort_wrong_mean_vector_units_and_mislabeled_change_are_detected():
    for name in ("missing_game", "mean_vectors", "gate_label", "different_fragment", "wiring"):
        run = deepcopy(_run())
        life = run["lifecycles"][0]
        if name == "missing_game":
            life["evaluation"]["methods"]["COVERAGE_MEAN"]["games"].pop()
        elif name == "mean_vectors":
            life["updates"]["COVERAGE"]["update"]["counts"]["fit_output_vectors"] *= 4
        elif name == "gate_label":
            life["evaluation"]["gate_changes"]["COVERAGE"][0]["category"] = "disabled"
        elif name == "different_fragment":
            life["evaluation"]["methods"]["COVERAGE_MEAN"]["games"][3]["selected_option"] = "SNAKE_4"
        else:
            life["evaluation"]["wiring"]["mean_update_choices_preserved"] = False
        assert not _analyze(run, name)["complete"]
