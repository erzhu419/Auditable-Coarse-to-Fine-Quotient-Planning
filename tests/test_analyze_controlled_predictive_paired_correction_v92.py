"""Residual correction is evaluated against an independent terminal batch."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("paired_correction_analysis_v92",
    ROOT / "scripts/analyze_controlled_predictive_paired_correction_v92.py")
ANALYZER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYZER)


def rebuild_gates(stage):
    gates = {}
    for left, right in ANALYZER._gate_pairs(tuple(stage["methods"])):
        changes = []
        for new, old in zip(stage["methods"][left]["games"], stage["methods"][right]["games"]):
            before, after = old["selected_option"], new["selected_option"]
            category = ("both_h2" if before in (None, "H2") and after in (None, "H2") else
                "enabled" if before in (None, "H2") else "disabled" if after in (None, "H2") else
                "same_fragment" if before == after else "changed_fragment")
            changes.append(dict(seed=new["seed"], replica=new["replica"], query=new["query"],
                category=category, old_option=before, new_option=after))
        gates[f"{left}_minus_{right}"] = changes
    stage["gate_changes"] = gates


def natural_fixture(query="reward"):
    methods = {"6": ["H2_ONLY", "MC", "V91_DECOMPOSED", "PAIR_ONLY", "CORRECTED"],
        "12": ["H2_ONLY", "MC", "V91_DECOMPOSED", "PAIR_ONLY", "CORRECTED", "CORRECTED_FROZEN_6"]}
    settings = dict(lifecycles=[0, 1], checkpoints=[6, 12], methods_by_checkpoint=methods,
        queries={query: ANALYZER.QUERIES[query]}, evaluation_replicas=2)
    options = {"H2_ONLY": None, "MC": "SPACE_4", "V91_DECOMPOSED": "SPACE_1",
        "PAIR_ONLY": "SNAKE_4", "CORRECTED": "H2", "CORRECTED_FROZEN_6": "SNAKE_1"}
    scores = {"H2_ONLY": 100, "MC": 90, "V91_DECOMPOSED": 95,
        "PAIR_ONLY": 80, "CORRECTED": 100, "CORRECTED_FROZEN_6": 70}
    lives = []
    for life in settings["lifecycles"]:
        stages = []
        for checkpoint in settings["checkpoints"]:
            records = {}
            for method in methods[str(checkpoint)]:
                selected = options[method]
                duration = int(selected.split("_")[1]) if selected not in (None, "H2") else 0
                records[method] = dict(costs={"evaluation_seconds": .02}, games=[dict(
                    seed=100000 + checkpoint * 1000 + life * 100 + replica, replica=replica,
                    query=query, score=scores[method],
                    utility=ANALYZER._utility([scores[method] / 2048, 1., 0.], ANALYZER.QUERIES[query]),
                    status="LOST", steps=10, max_rank=5, seconds=.01, selected_option=selected,
                    duration_budget=duration, fragment_actions=duration,
                    environment_counts={"sampled_transitions": 10}, planning_counts={"model_uniform_draws": 40})
                    for replica in range(2)])
            stage = dict(episodes=checkpoint, methods=records, wiring={name: True for name in ANALYZER.WIRING})
            rebuild_gates(stage)
            stages.append(stage)
        lives.append(dict(id=life, checkpoints=stages))
    return dict(status="complete", settings=settings, lifecycles=lives)


def test_natural_contrasts_keep_disabled_recovery_separate():
    result = ANALYZER.analyze_natural(natural_fixture())
    assert all(result["checks"].values())
    stage = result["checkpoints"]["12"]
    assert stage["comparisons"]["CORRECTED_minus_MC"]["reward"]["mean_score_delta"] == 10
    assert stage["comparisons"]["CORRECTED_minus_PAIR_ONLY"]["reward"]["mean_score_delta"] == 20
    assert stage["comparisons"]["CORRECTED_minus_V91_DECOMPOSED"]["reward"]["mean_score_delta"] == 5
    assert stage["comparisons"]["CORRECTED_minus_CORRECTED_FROZEN_6"]["reward"]["mean_score_delta"] == 30
    attribution = stage["gate_decomposition"]["CORRECTED_minus_MC"]["reward"]["primary_attribution"]
    assert attribution["score"]["cancelled_intervention_recovery_contribution"] == 10
    assert attribution["score"]["new_or_changed_intervention_h2_contribution"] == 0
    assert attribution["utility"]["cancelled_intervention_recovery_contribution"] == 10 / 2048
    assert set(stage["gate_decomposition"]) == {"CORRECTED_minus_MC", "CORRECTED_minus_PAIR_ONLY",
        "CORRECTED_minus_V91_DECOMPOSED", "CORRECTED_minus_H2_ONLY", "PAIR_ONLY_minus_MC",
        "CORRECTED_minus_CORRECTED_FROZEN_6"}
    assert stage["gate_decomposition"]["CORRECTED_minus_V91_DECOMPOSED"]["reward"]["primary_attribution"]["score"]["cancelled_intervention_recovery_contribution"] == 5
    assert stage["gate_decomposition"]["CORRECTED_minus_H2_ONLY"]["reward"]["available_common_terminal"]["categories"]["both_h2"]["pairs"] == 4
    assert stage["gate_decomposition"]["PAIR_ONLY_minus_MC"]["reward"]["available_common_terminal"]["categories"]["changed_fragment"]["old"]["mean_score_contribution"] == -10
    assert result["work"]["ground_work"]["sampled_transitions"] == 440


def test_natural_cutoff_retains_cost_and_equal_life_descriptive_weight():
    run = natural_fixture()
    run["lifecycles"][0]["checkpoints"][1]["methods"]["MC"]["games"][1]["status"] = "CUTOFF"
    for game in run["lifecycles"][1]["checkpoints"][1]["methods"]["MC"]["games"]:
        game.update(score=100, utility=100 / 2048)
    result = ANALYZER.analyze_natural(run)
    comparison = result["checkpoints"]["12"]["comparisons"]["CORRECTED_minus_MC"]["reward"]
    assert comparison["mean_score_delta"] is None
    assert comparison["available_common_terminal"]["mean_score_delta"] == 5
    assert [row["pairs"] for row in comparison["available_common_terminal"]["lifecycles"]] == [1, 2]
    assert result["work"]["ground_work"]["sampled_transitions"] == 440
    assert result["work"]["outcomes"]["CUTOFF"] == 1


def test_new_risk_intervention_utility_includes_terminal_goal_difference():
    run = natural_fixture("risk_goal")
    for life in run["lifecycles"]:
        stage = life["checkpoints"][1]
        for game in stage["methods"]["MC"]["games"]:
            game.update(selected_option="H2", duration_budget=0, fragment_actions=0,
                score=100, utility=100 / 2048 - 4)
        game = stage["methods"]["CORRECTED"]["games"][0]
        game.update(selected_option="SPACE_1", duration_budget=1, fragment_actions=1,
            status="WON", utility=100 / 2048 + 4)
        rebuild_gates(stage)
    result = ANALYZER.analyze_natural(run)
    contribution = result["checkpoints"]["12"]["gate_decomposition"]["CORRECTED_minus_MC"]["risk_goal"]["primary_attribution"]
    assert contribution["score"]["new_or_changed_intervention_h2_contribution"] == 0
    assert contribution["utility"]["new_or_changed_intervention_h2_contribution"] == 4


def vectors(values):
    return [[value, 0., 0.] for value in values]


def test_correction_includes_prefix_and_terminal_residual_variance():
    result = ANALYZER.compare_estimators(vectors([2, 6]), vectors([1, 3]),
        vectors([3, 5, 3, 5]), vectors([8, 10]), "reward")
    estimate = result["estimates"]
    assert estimate["MC"]["mean_utility"] == 4
    assert estimate["PAIR_ONLY"]["mean_utility"] == 4
    assert estimate["CORRECTED"]["mean_utility"] == 6
    assert estimate["MC"]["conditional_variance_of_mean"] == 4
    assert estimate["CORRECTED"]["conditional_variance_of_mean"] == pytest.approx(4 / 3)
    assert result["corrected_variance_components"] == pytest.approx(
        {"prefix_mean_variance": 1 / 3, "terminal_residual_mean_variance": 1})
    assert result["corrected_to_mc_conditional_variance_ratio"] == pytest.approx(1 / 3)
    assert estimate["MC"]["reference_squared_utility_error"] == 25
    assert estimate["CORRECTED"]["reference_squared_utility_error"] == 9


def test_reference_batch_never_enters_any_estimator():
    inputs = (vectors([2, 6]), vectors([1, 3]), vectors([3, 5, 3, 5]))
    first = ANALYZER.compare_estimators(*inputs, vectors([8, 10]), "reward")
    second = ANALYZER.compare_estimators(*inputs, vectors([100, 102]), "reward")
    for name in ("MC", "PAIR_ONLY", "CORRECTED"):
        for field in ("mean_rfs", "mean_utility", "conditional_variance_of_mean"):
            assert first["estimates"][name][field] == second["estimates"][name][field]
        assert first["estimates"][name]["reference_squared_utility_error"] != second["estimates"][name]["reference_squared_utility_error"]


def test_risk_variance_preserves_reward_failure_success_covariance():
    result = ANALYZER.compare_estimators([[0., 1., 0.], [2., 0., 1.]], vectors([0, 0]),
        vectors([0, 0, 0, 0]), vectors([0, 0]), "risk_goal")
    assert result["full_terminal_estimation_batch"]["utility_sample_variance"] == 50
    assert result["estimates"]["MC"]["conditional_variance_of_mean"] == 25
    assert result["estimates"]["CORRECTED"]["conditional_variance_of_mean"] == 25


def test_same_prefix_algebra_cancels_to_mc_showing_why_independence_matters():
    full = vectors([2, 6])
    predictions = vectors([1, 3])
    result = ANALYZER.compare_estimators(full, predictions, predictions, vectors([8, 10]), "reward")
    assert result["estimates"]["CORRECTED"]["mean_rfs"] == result["estimates"]["MC"]["mean_rfs"]


def prefix_log(replicas=4):
    trajectories, transitions = replicas * 5, replicas * 5 * 4
    return dict(requested_replicas=replicas, trajectories=trajectories,
        ground_work={"sampled_transitions": transitions, "environment_random_draws": 2 * transitions},
        planning_counts={"model_uniform_draws": 4 * transitions}, outcomes={"ACTIVE": trajectories},
        wiring={name: True for name in ANALYZER.PREFIX_WIRING}, seconds=.1)


def full_fixture():
    run = natural_fixture()
    run["settings"].update(prefix_replicas=4, validation_estimation_replicas=2,
        validation_reference_replicas=2, validation_prefix_replicas=4,
        validation_roots_per_query=2, workers=2)
    run["actual_wall_seconds"] = 3.
    for life in run["lifecycles"]:
        life["inherited"] = dict(source_work={"sampled_transitions": 20},
            branch_work={"sampled_transitions": 200}, v91_fitting={"tree_fits": 20})
        for stage in life["checkpoints"]:
            checkpoint = stage["episodes"]
            episodes = [episode for episode in range(checkpoint) if episode % 5 != 4]
            n = len(episodes)
            head = dict(counts={"tree_fits": 1, "fit_roots": n, "fit_output_vectors": 4 * n}, seconds=.1)
            fits = {}
            for name, fold in (("full", None), ("fold_0", 0), ("fold_1", 1)):
                fits[name] = dict(checkpoint=checkpoint, excluded_fold=fold,
                    counts={"tree_fits": 1, "paired_continuation_tree_fits": 1},
                    queries={"reward": {"training_episodes": [episode for episode in episodes
                        if fold is None or episode % 2 != fold]}})
            stage.update(dataset=dict(roots=checkpoint, training_roots=n, heldout_roots=checkpoint - n,
                    records=checkpoint * 4), input_preparation_seconds=.2,
                updates=dict(paired_models=dict(fits=fits, counts={"tree_fits": 3}, seconds=.15),
                    selectors=dict(head_fits={name: deepcopy(head) for name in ANALYZER.ESTIMATORS},
                        root_estimates=[dict(episode=episode, complete=True) for episode in range(checkpoint)],
                        counts={"tree_fits": 3}, oof_episode_isolation=True, label_seconds=.03, seconds=.33)))
            stage["acquisition"] = dict(roots=[dict(root={"episode": checkpoint - 6 + i}, log=prefix_log()) for i in range(6)],
                ground_work={"sampled_transitions": 480}, planning_counts={"model_uniform_draws": 1920},
                outcomes={"ACTIVE": 120}, trajectories=120, seconds=.6)
            if checkpoint != 12:
                continue
            records = []
            for episode in range(2):
                detail = dict(full_targets=vectors([2, 6]), full_predictions=vectors([1, 3]),
                    short_predictions=vectors([3, 5, 3, 5]), paired_residuals=vectors([1, 3]),
                    full_replicas=[0, 1], short_replicas=list(range(4)),
                    mc_variance_of_mean=4., corrected_variance_of_mean=4 / 3)
                estimates = {method: {option: [value, 0., 0.] for option in ANALYZER.OPTIONS[1:]}
                    for method, value in (("MC", 4.), ("PAIR_ONLY", 4.), ("CORRECTED", 6.))}
                head_predictions = {method: dict(option="SPACE_1", predictions={option: dict(target=[value, 0., 0.])
                    for option in ANALYZER.OPTIONS[1:]}) for method, value in (
                        ("MC", 4.), ("V91_DECOMPOSED", 8.), ("PAIR_ONLY", 4.), ("CORRECTED", 6.), ("CORRECTED_FROZEN_6", 3.))}
                records.append(dict(root=dict(life=life["id"], query="reward", episode=episode,
                        board=[1, 0] * 8, source_seed=1000 + life["id"] * 100 + episode, step=5),
                    terminal_log=dict(censored_root=False, pair_deltas={}, trajectories=20,
                        ground_work={"sampled_transitions": 100}, planning_counts={"model_uniform_draws": 400},
                        outcomes={"LOST": 20}), prefix_log=prefix_log(),
                    estimates=dict(complete=True, estimates=estimates,
                        details={option: deepcopy(detail) for option in ANALYZER.OPTIONS[1:]}),
                    head_predictions=head_predictions, reference={option: vectors([8, 10]) for option in ANALYZER.OPTIONS[1:]},
                    reference_complete=True))
            stage["validation"] = dict(roots=records, missing_roots=[],
                prediction_work={"paired_continuation_predictions": 16}, seconds=.5)
    return run


def test_full_cost_fit_and_independent_reference_accounting():
    result = ANALYZER.analyze_run(full_fixture())
    assert result["complete"] and result["primary_complete"]
    assert result["actual_executed_work"]["actual_tree_fits"] == 24
    assert result["actual_executed_work"]["new_pair_tree_fits"] == 12
    assert result["actual_executed_work"]["new_head_tree_fits"] == 12
    assert result["actual_executed_work"]["new_v91_baseline_fits"] == 0
    assert result["actual_executed_work"]["new_training_prefix_transitions"] == 1920
    assert result["actual_executed_work"]["new_training_terminal_transitions"] == 0
    assert result["actual_executed_work"]["newly_sampled_transitions"] == 3080
    assert result["construction"]["acquisition"]["outcomes"] == {"ACTIVE": 480}
    assert result["validation"]["work"]["prediction_work"]["paired_continuation_predictions"] == 32
    validation = result["validation"]["estimators"]
    assert validation["MC"]["reward"]["primary"]["mean_utility_mse"] == 25
    assert validation["CORRECTED"]["reward"]["primary"]["mean_utility_mse"] == 9
    assert validation["CORRECTED"]["reward"]["primary"]["mean_conditional_variance_of_mean"] == pytest.approx(4 / 3)
    assert result["validation"]["heads"]["MC"]["reward"]["primary"]["mean_utility_mse"] == 25


@pytest.mark.parametrize("part", ["estimation", "reference"])
def test_each_terminal_batch_cutoff_preserves_cost_and_blocks_primary(part):
    run = full_fixture()
    record = run["lifecycles"][0]["checkpoints"][1]["validation"]["roots"][0]
    record["terminal_log"].update(censored_root=True, outcomes={"LOST": 19, "CUTOFF": 1})
    if part == "estimation":
        record["estimates"] = dict(complete=False, estimates={}, details={})
    else:
        record.update(reference_complete=False, reference={})
    result = ANALYZER.analyze_run(run)
    assert result["complete"] and not result["primary_complete"]
    assert result["validation"]["estimators"]["MC"]["reward"]["primary"] is None
    assert result["actual_executed_work"]["newly_sampled_transitions"] == 3080
    assert result["validation"]["work"]["trajectories"]["terminal"] == 80
    assert result["validation"]["work"]["terminal"]["outcomes"]["CUTOFF"] == 1


def test_oof_and_stored_correction_variance_mismatches_are_detected():
    run = full_fixture()
    run["lifecycles"][0]["checkpoints"][0]["updates"]["paired_models"]["fits"]["fold_0"]["queries"]["reward"]["training_episodes"].append(0)
    result = ANALYZER.analyze_run(run)
    assert not result["complete"]
    assert not result["checks"]["fitting_accounting_complete"]
    run = full_fixture()
    detail = run["lifecycles"][0]["checkpoints"][1]["validation"]["roots"][0]["estimates"]["details"][ANALYZER.OPTIONS[1]]
    detail["corrected_variance_of_mean"] = 1.
    result = ANALYZER.analyze_run(run)
    assert not result["complete"]
    assert not result["checks"]["stored_estimator_values_match"]
