"""Independent terminal references and descriptive predictive Bellman comparisons."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("bellman_analysis_v94",
    ROOT / "scripts/analyze_controlled_predictive_bellman_v94.py")
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
    methods = {"6": ["H2_ONLY", "MC", "V91_DECOMPOSED", "V92_CORRECTED", "FQE", "MC_EXTRA", "MC_TAIL"],
        "12": ["H2_ONLY", "MC", "V91_DECOMPOSED", "V92_CORRECTED", "FQE", "MC_EXTRA", "MC_TAIL", "FQE_FROZEN_6", "MC_TAIL_FROZEN_6"]}
    settings = dict(lifecycles=[3, 8], checkpoints=[6, 12], methods_by_checkpoint=methods,
        queries={query: ANALYZER.QUERIES[query]}, evaluation_replicas=2)
    options = {"H2_ONLY": None, "MC": "SPACE_4", "V91_DECOMPOSED": "SPACE_1",
        "V92_CORRECTED": "SNAKE_4", "FQE": "H2", "FQE_FROZEN_6": "SNAKE_1", "MC_EXTRA": "SPACE_4", "MC_TAIL": "SNAKE_4", "MC_TAIL_FROZEN_6": "SNAKE_4"}
    scores = {"H2_ONLY": 100, "MC": 90, "V91_DECOMPOSED": 95,
        "V92_CORRECTED": 80, "FQE": 100, "FQE_FROZEN_6": 70, "MC_EXTRA": 95, "MC_TAIL": 85, "MC_TAIL_FROZEN_6": 75}
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



def test_all_primary_contrasts_and_cancelled_recovery_remain_separate():
    result = ANALYZER.analyze_natural(natural_fixture())
    assert all(result["checks"].values())
    stage = result["checkpoints"]["12"]
    assert set(stage["gate_decomposition"]) == {"FQE_minus_" + name for name in
        ("MC_TAIL", "MC", "MC_EXTRA", "H2_ONLY", "V91_DECOMPOSED", "V92_CORRECTED", "FQE_FROZEN_6")} | {
        "MC_TAIL_minus_V91_DECOMPOSED", "MC_TAIL_minus_H2_ONLY", "MC_TAIL_minus_MC_TAIL_FROZEN_6"}
    assert stage["comparisons"]["FQE_minus_MC_TAIL"]["reward"]["mean_score_delta"] == 15
    assert stage["comparisons"]["FQE_minus_FQE_FROZEN_6"]["reward"]["mean_score_delta"] == 30
    attribution = stage["gate_decomposition"]["FQE_minus_MC_TAIL"]["reward"]["primary_attribution"]
    assert attribution["score"]["cancelled_intervention_recovery_contribution"] == 15
    assert attribution["score"]["new_or_changed_intervention_h2_contribution"] == 0
    assert result["work"]["ground_work"]["sampled_transitions"] == 640


def test_history_uncertainty_and_natural_cutoff_preserve_cost():
    run = natural_fixture()
    for life, score in zip(run["lifecycles"], (100, 80)):
        for game in life["checkpoints"][1]["methods"]["MC_TAIL"]["games"]:
            game.update(score=score, utility=score / 2048)
    comparison = ANALYZER.analyze_natural(run)["checkpoints"]["12"]["comparisons"]["FQE_minus_MC_TAIL"]["reward"]
    assert comparison["mean_score_delta"] == 10
    assert comparison["descriptive_lifecycle_uncertainty"]["score"]["standard_error"] == pytest.approx(10)
    run["lifecycles"][0]["checkpoints"][1]["methods"]["MC_TAIL"]["games"][0]["status"] = "CUTOFF"
    result = ANALYZER.analyze_natural(run)
    comparison = result["checkpoints"]["12"]["comparisons"]["FQE_minus_MC_TAIL"]["reward"]
    assert comparison["mean_score_delta"] is None
    assert comparison["descriptive_lifecycle_uncertainty"] is None
    assert comparison["available_common_terminal"]["mean_score_delta"] == 10
    assert result["work"]["ground_work"]["sampled_transitions"] == 640


def test_risk_effect_uses_terminal_outcomes_not_score_alone():
    run = natural_fixture("risk_goal")
    for life in run["lifecycles"]:
        stage = life["checkpoints"][1]
        for game in stage["methods"]["MC_TAIL"]["games"]:
            game.update(score=100, utility=100 / 2048 - 4, selected_option="H2",
                duration_budget=0, fragment_actions=0)
        game = stage["methods"]["FQE"]["games"][0]
        game.update(selected_option="SPACE_1", duration_budget=1, fragment_actions=1,
            status="WON", utility=100 / 2048 + 4)
        rebuild_gates(stage)
    attribution = ANALYZER.analyze_natural(run)["checkpoints"]["12"]["gate_decomposition"]["FQE_minus_MC_TAIL"]["risk_goal"]["primary_attribution"]
    assert attribution["score"]["new_or_changed_intervention_h2_contribution"] == 0
    assert attribution["utility"]["new_or_changed_intervention_h2_contribution"] == 4

def full_fixture():
    run = natural_fixture()
    run["settings"].update(fqe_iterations=2, reference_replicas=2, validation_roots_per_query=2,
        n_step=16, stride=16, branch_replicas=8)
    run.update(actual_wall_seconds=3., inherited_data="retained_v93")
    for life in run["lifecycles"]:
        for stage in life["checkpoints"]:
            cp = stage["episodes"]
            train = [episode for episode in range(cp) if episode % 5 != 4]
            folds = {}
            for name, excluded in (("full", None), ("fold_0", 0), ("fold_1", 1)):
                episodes = [episode for episode in train if excluded is None or episode % 2 != excluded]
                diag = dict(mean_prediction_rfs=[4., .8, .2], mean_failure_plus_success=1.,
                    mean_target_rfs=[4., .8, .2], fit_target_mse_rfs=[2., .1, .1],
                    counts={"tree_fits": 1}, seconds=.01)
                folds[name] = dict(excluded_fold=excluded, training_episodes={"reward": episodes},
                    queries={"reward": dict(training_episodes=episodes, training_rows=10 * len(episodes),
                        bootstrap_rows=8 * len(episodes), terminal_anchor_rows=2 * len(episodes))},
                    cache_counts={"feature_cache_builds": 1}, cache_seconds=.01,
                    MC_TAIL=dict(counts={"tree_fits": 1, "mc_tail_tree_fits": 1}, queries={"reward": deepcopy(diag)}, seconds=.01),
                    FQE=dict(counts={"tree_fits": 2, "fqe_tree_fits": 2}, initialization="MC_TAIL", seconds=.02,
                        iterations=[dict(iteration=iteration, queries={"reward": deepcopy(diag)}) for iteration in (1, 2)]))
            head = dict(counts={"tree_fits": 1, "fit_roots": len(train), "fit_output_vectors": 4 * len(train)}, seconds=.01)
            source = dict(sampled_transitions=100)
            branches = dict(sampled_transitions=1000)
            basecost = dict(source_transitions=100 * (cp // 6), base_branch_transitions=1000 * (cp // 6),
                prefix_transitions=0, extra_terminal_transitions=0, total_training_transitions=1100 * (cp // 6))
            costs = {name: deepcopy(basecost) for name in stage["methods"]}
            if cp == 12:
                for method in ANALYZER.VALUE_METHODS:
                    costs[method + "_FROZEN_6"] = dict(source_transitions=100, base_branch_transitions=1000,
                        prefix_transitions=0, extra_terminal_transitions=0, total_training_transitions=1100)
            stage.update(dataset=dict(roots=cp, training_roots=len(train), heldout_roots=cp - len(train), records=4 * cp, bellman_rows=10 * cp),
                input=dict(counts=dict(eligible_roots=6, training_eligible_roots=5, heldout_eligible_roots=1,
                    bellman_rows=60, roots=6, censored_roots=0, new_environment_transitions=0, tree_fits=0),
                    complete_root_execution_contract_matches=True, retained_means_match=True,
                    n_step=16, stride=16, row_weight=1., inherited_environment_work=deepcopy(branches), seconds=.02),
                inherited_acquisition=dict(source=source, branches=branches),
                inherited_v93_baselines=dict(original_stage_tree_fits=11, paths={}),
                new_training_environment_transitions=0, method_acquisition=costs,
                updates=dict(value=dict(checkpoint=cp, iterations=2, folds=folds, counts={"tree_fits": 9}, seconds=.15),
                    heads=dict(checkpoint=cp, head_fits={name: deepcopy(head) for name in ANALYZER.VALUE_METHODS},
                        counts={"tree_fits": 2, "continuation_predictions": 100}, input_roots=cp,
                        censored_roots_excluded=0, future_roots_excluded=0, oof_episode_isolation=True, seconds=.1)))
            if cp != 12:
                continue
            records = []
            for episode in range(2):
                predictions = {name: dict(option="SPACE_1", predictions={option: dict(target=
                    [0., 0., 0.] if option == "H2" else [3. if name == "FQE" else 1., .1, -.1])
                    for option in ANALYZER.OPTIONS}) for name in stage["methods"] if name != "H2_ONLY"}
                reference = {option: [[2., 0., 0.], [6., 0., 0.]] for option in ANALYZER.OPTIONS[1:]}
                boundaries = [dict(replica=replica, option=option, terminal=True,
                    predictions=dict(MC_TAIL=[10., .5, .5], FQE=[12., .5, .5]),
                    remaining_target=[10., 1., 0.] if replica == 0 else [14., 0., 1.])
                    for option in ANALYZER.OPTIONS for replica in range(2)]
                reconstruction = [dict(replica=replica, option=option, Y=reference[option][replica],
                    Z=dict(MC_TAIL=[1., 0., 0.], FQE=[3., 0., 0.]))
                    for option in ANALYZER.OPTIONS[1:] for replica in range(2)]
                records.append(dict(root=dict(life=life["id"], query="reward", episode=episode, board=[1] * 16),
                    head_predictions=predictions, reference_complete=True, paired_reference=reference,
                    active_boundaries=10, value_records=boundaries, reconstruction=reconstruction,
                    terminal_log=dict(censored_root=False, trajectories=10, outcomes={"LOST": 5, "WON": 5},
                        ground_work={"sampled_transitions": 100}, planning_counts={"model_uniform_draws": 400})))
            stage["validation"] = dict(roots=records, missing_roots=[],
                prediction_work={"continuation_predictions": 40}, seconds=.4)
    return run


def test_complete_accounting_counts_warm_start_once_and_inherited_data_separately():
    result = ANALYZER.analyze_run(full_fixture())
    assert result["complete"] and result["primary_complete"]
    assert all(result["checks"].values())
    cost = result["actual_executed_work"]
    assert cost["actual_tree_fits"] == 44
    assert (cost["new_mc_tail_tree_fits"], cost["new_fqe_tree_fits"], cost["new_head_tree_fits"]) == (12, 24, 8)
    assert cost["new_training_environment_transitions"] == 0
    assert cost["newly_sampled_transitions"] == 1040
    assert result["construction"]["inherited_acquisition"]["branches"]["sampled_transitions"] == 4000
    assert result["validation"]["work"]["prediction_work"]["continuation_predictions"] == 80


def test_head_reference_is_independent_and_predictive_error_is_not_mc_self_comparison():
    validation = ANALYZER.analyze_validation(full_fixture())
    assert validation["heads"]["MC"]["reward"]["primary"]["mean_utility_mse"] == 9
    assert validation["heads"]["FQE"]["reward"]["primary"]["mean_utility_mse"] == 1
    assert validation["heads"]["FQE"]["reward"]["primary"]["selected_empirical_utility"] == 4
    assert validation["heads"]["FQE"]["reward"]["primary"]["predicted_delta_terminal_mass"] == 0
    assert validation["heads"]["FQE"]["reward"]["primary"]["implied_candidate_terminal_mass"] == 1
    assert validation["values"]["MC_TAIL"]["reward"]["primary"]["mean_utility_mse"] == 8
    assert validation["values"]["FQE"]["reward"]["primary"]["mean_utility_mse"] == 4
    assert validation["reconstruction"]["MC_TAIL"]["reward"]["primary"]["mean_utility_mse"] == 13
    assert validation["reconstruction"]["FQE"]["reward"]["primary"]["mean_utility_mse"] == 5
    assert validation["roots"][0]["paired_reference"]["SPACE_1"]["standard_error"] == 2
    assert all(row["observations"] == 10 for row in validation["value_roots"])


def test_risk_predictive_error_keeps_joint_rfs_covariance():
    result = ANALYZER.predictive_error([[1., .25, .75], [3., .75, .25]],
        [[2., 1., 0.], [4., 0., 1.]], "risk_goal")
    assert result["mean_utility_bias"] == -1
    assert result["mean_utility_mse"] == 37
    assert result["paired_error"]["standard_error"] == 6
    assert result["predicted_terminal_mass"] == result["observed_terminal_mass"] == 1


def test_reference_cutoff_preserves_cost_but_never_becomes_a_terminal_target():
    run = full_fixture()
    record = run["lifecycles"][0]["checkpoints"][1]["validation"]["roots"][0]
    record["terminal_log"].update(censored_root=True, outcomes={"LOST": 4, "WON": 5, "CUTOFF": 1})
    record.update(reference_complete=False, paired_reference={}, reconstruction=[])
    record["value_records"].pop()
    result = ANALYZER.analyze_run(run)
    assert result["complete"] and not result["primary_complete"]
    assert result["validation"]["heads"]["FQE"]["reward"]["primary"] is None
    assert result["validation"]["values"]["FQE"]["reward"]["primary"] is None
    assert result["actual_executed_work"]["newly_sampled_transitions"] == 1040
    assert result["validation"]["work"]["outcomes"]["CUTOFF"] == 1


@pytest.mark.parametrize("failure", ["fold", "rounds", "boundary", "reconstruction", "heads"])
def test_reachable_protocol_mismatches_are_detected(failure):
    run = full_fixture()
    stage = run["lifecycles"][0]["checkpoints"][1]
    if failure == "fold":
        stage["updates"]["value"]["folds"]["fold_0"]["training_episodes"]["reward"].append(0)
        key = "checkpoint_and_episode_fold_isolation"
    elif failure == "rounds":
        stage["updates"]["value"]["folds"]["full"]["FQE"]["iterations"].pop()
        key = "warm_start_and_fixed_rounds_match"
    elif failure == "boundary":
        stage["validation"]["roots"][0]["value_records"].pop()
        key = "boundary_prediction_rosters_complete"
    elif failure == "reconstruction":
        stage["validation"]["roots"][0]["reconstruction"][0]["Y"] = [100., 0., 0.]
        key = "reconstruction_rosters_complete"
    else:
        stage["validation"]["roots"][0]["head_predictions"]["FQE"]["predictions"].pop("H2")
        key = "head_prediction_rosters_complete"
    result = ANALYZER.analyze_run(run)
    assert not result["complete"] and not result["checks"][key]
