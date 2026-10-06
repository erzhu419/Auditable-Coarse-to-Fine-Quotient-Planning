"""Behavioral replication uses equal history weights and retains partial-budget costs."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("replication_analysis_v93",
    ROOT / "scripts/analyze_controlled_predictive_replication_v93.py")
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
    methods = {"6": ["H2_ONLY", "MC", "V91_DECOMPOSED", "PAIR_ONLY", "CORRECTED", "MC_EXTRA"],
        "12": ["H2_ONLY", "MC", "V91_DECOMPOSED", "PAIR_ONLY", "CORRECTED", "MC_EXTRA", "CORRECTED_FROZEN_6", "MC_EXTRA_FROZEN_6"]}
    settings = dict(lifecycles=[3, 8], checkpoints=[6, 12], methods_by_checkpoint=methods,
        queries={query: ANALYZER.QUERIES[query]}, evaluation_replicas=2)
    options = {"H2_ONLY": None, "MC": "SPACE_4", "V91_DECOMPOSED": "SPACE_1",
        "PAIR_ONLY": "SNAKE_4", "CORRECTED": "H2", "CORRECTED_FROZEN_6": "SNAKE_1", "MC_EXTRA": "SPACE_4", "MC_EXTRA_FROZEN_6": "SNAKE_4"}
    scores = {"H2_ONLY": 100, "MC": 90, "V91_DECOMPOSED": 95,
        "PAIR_ONLY": 80, "CORRECTED": 100, "CORRECTED_FROZEN_6": 70, "MC_EXTRA": 95, "MC_EXTRA_FROZEN_6": 75}
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
        "CORRECTED_minus_CORRECTED_FROZEN_6", "CORRECTED_minus_MC_EXTRA", "MC_EXTRA_minus_MC",
        "MC_EXTRA_minus_H2_ONLY", "MC_EXTRA_minus_MC_EXTRA_FROZEN_6"}
    assert stage["gate_decomposition"]["CORRECTED_minus_V91_DECOMPOSED"]["reward"]["primary_attribution"]["score"]["cancelled_intervention_recovery_contribution"] == 5
    assert stage["gate_decomposition"]["CORRECTED_minus_H2_ONLY"]["reward"]["available_common_terminal"]["categories"]["both_h2"]["pairs"] == 4
    assert stage["gate_decomposition"]["PAIR_ONLY_minus_MC"]["reward"]["available_common_terminal"]["categories"]["changed_fragment"]["old"]["mean_score_contribution"] == -10
    assert stage["comparisons"]["CORRECTED_minus_MC_EXTRA"]["reward"]["mean_score_delta"] == 5
    assert stage["comparisons"]["MC_EXTRA_minus_MC_EXTRA_FROZEN_6"]["reward"]["mean_score_delta"] == 20
    assert [row["id"] for row in stage["comparisons"]["CORRECTED_minus_MC"]["reward"]["available_common_terminal"]["lifecycles"]] == [3, 8]
    assert result["work"]["ground_work"]["sampled_transitions"] == 560


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
    assert result["work"]["ground_work"]["sampled_transitions"] == 560
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



def test_training_variance_uses_equal_histories_and_excludes_heldout():
    run = natural_fixture()
    for index, life in enumerate(run["lifecycles"]):
        for stage in life["checkpoints"]:
            rows = []
            for episode in list(range(index + 1)) + [4]:
                value = (1. if index == 0 else 9.) if episode != 4 else 1000.
                detail = dict(mc_sample_variance=8 * value, short_sample_variance=0.,
                    residual_sample_variance=8 * value, mc_variance_of_mean=value,
                    corrected_variance_of_mean=value)
                rows.append(dict(query="reward", episode=episode, complete=True,
                    details={option: deepcopy(detail) for option in ANALYZER.OPTIONS[1:]}))
            stage["updates"] = dict(paired_selectors=dict(root_estimates=rows))
    result = ANALYZER.analyze_training_variance(run)
    stage = result["checkpoints"]["12"]["reward"]
    assert stage["equal_lifecycle_means"]["mc_variance_of_mean"] == 5
    assert stage["ratio_of_equal_lifecycle_mean_variances"] == 1
    assert [row["complete_roots"] for row in stage["lifecycles"]] == [1, 2]
    assert "not independent validation errors" in result["scope"]

def full_fixture():
    run = natural_fixture()
    run["settings"].update(prefix_replicas=4, branch_replicas=8)
    run.update(actual_wall_seconds=3., inherited_dynamics="fixed_supplied_dynamics.json")
    for life in run["lifecycles"]:
        cumulative_extras = {}
        frozen_charges = None
        for stage in life["checkpoints"]:
            cp = stage["episodes"]
            episodes = list(range(cp))
            train = [episode for episode in episodes if episode % 5 != 4]
            roots = [dict(query="reward", episode=episode, board=[episode + 1] + [0] * 15)
                for episode in range(cp - 6, cp)]
            roster = sorted([root for root in roots if root["episode"] % 5 != 4], key=ANALYZER._root_key)
            rotation = (life["id"] + cp) % len(roster)
            roster = roster[rotation:] + roster[:rotation]
            cumulative_extras[roster[0]["episode"]] = 1
            blocks = [dict(root=root, attempt=index, complete_block=index == 0,
                ground_work={"sampled_transitions": cost}, trajectories=trajectories)
                for index, (root, cost, trajectories) in enumerate(zip(roster, (200, 280), (5, 3)))]
            extra = dict(checkpoint=cp, budget=480, used_transitions=480, unused_budget=0,
                roster=roster, roster_rotation=rotation, root_statistics=[],
                blocks=blocks, attempted_blocks=2, complete_blocks=1, incomplete_blocks=1,
                budget_truncated_blocks=1, budget_cutoff_trajectories=1, max_step_cutoff_trajectories=0,
                ground_work={"sampled_transitions": 480}, planning_counts={"model_uniform_draws": 1920},
                incorporated_ground_work={"sampled_transitions": 200},
                unincorporated_ground_work={"sampled_transitions": 280},
                outcomes={"LOST": 7, "CUTOFF": 1}, trajectories=8, seconds=.2)
            prefix_one = dict(requested_replicas=4, trajectories=20,
                ground_work={"sampled_transitions": 80}, planning_counts={"model_uniform_draws": 320},
                outcomes={"ACTIVE": 20}, wiring={name: True for name in ANALYZER.PREFIX_WIRING})
            fits = {}
            for name, fold in (("full", None), ("fold_0", 0), ("fold_1", 1)):
                fits[name] = dict(checkpoint=cp, excluded_fold=fold,
                    counts={"tree_fits": 1, "paired_continuation_tree_fits": 1, "continuation_tree_fits": 1},
                    queries={"reward": {"training_episodes": [episode for episode in train
                        if fold is None or episode % 2 != fold]}}, seconds=.01)
            head = dict(counts={"tree_fits": 1, "fit_roots": len(train), "fit_output_vectors": 4 * len(train)}, seconds=.01)
            detail = dict(mc_sample_variance=8., short_sample_variance=.4, residual_sample_variance=4.,
                mc_variance_of_mean=1., corrected_variance_of_mean=.6)
            estimates = [dict(query="reward", episode=episode, complete=True,
                continuation_model="full" if episode % 5 == 4 else f"fold_{episode % 2}",
                details={option: deepcopy(detail) for option in ANALYZER.OPTIONS[1:]}) for episode in episodes]
            stage.update(source_sampling_lifecycle=9300 + life["id"],
                source=dict(games=6, roots=6, outcomes={"LOST": 6}, work={"sampled_transitions": 100},
                    planning_counts={"model_uniform_draws": 400}, seconds=.1),
                branches=dict(roots=6, trajectories=240, censored_roots=0, outcomes={"LOST": 240},
                    work={"sampled_transitions": 1000}, planning_counts={"model_uniform_draws": 4000}, seconds=.4),
                dataset=dict(roots=cp, training_roots=len(train), heldout_roots=cp - len(train), records=4 * cp),
                input=dict(agreement={"root_cohorts_identical": True}), input_preparation_seconds=.02,
                acquisition_prefix=dict(roots=[dict(root=root, log=deepcopy(prefix_one)) for root in roots],
                    ground_work={"sampled_transitions": 480}, planning_counts={"model_uniform_draws": 1920},
                    outcomes={"ACTIVE": 120}, trajectories=120, seconds=.2),
                acquisition_extra=extra,
                extra_merge=dict(complete_extra_blocks=len(cumulative_extras), root_statistics=[dict(
                    root=dict(query="reward", episode=episode, board=[episode + 1] + [0] * 15),
                    base_replicas=8, extra_replicas=cumulative_extras.get(episode, 0),
                    total_replicas=8 + cumulative_extras.get(episode, 0)) for episode in episodes]),
                updates=dict(paired_models={"fits": deepcopy(fits)},
                    paired_selectors=dict(head_fits={name: deepcopy(head) for name in ("MC", "PAIR_ONLY", "CORRECTED")},
                        root_estimates=estimates, oof_episode_isolation=True, label_seconds=.03),
                    v91_decomposed=dict(tail_fits=deepcopy(fits), head_fit=deepcopy(head),
                        oof_episode_isolation=True, label_seconds=.02), mc_extra=deepcopy(head), counts={"tree_fits": 10}))
            charges = {}
            for method in stage["methods"]:
                if method.endswith("_FROZEN_6"):
                    charges[method] = deepcopy(frozen_charges[method.removesuffix("_FROZEN_6")])
                    continue
                base = 0 if method == "H2_ONLY" else cp // 6
                prefix = 480 * base if method in ("PAIR_ONLY", "CORRECTED") else 0
                extra_cost = 480 * base if method == "MC_EXTRA" else 0
                charges[method] = dict(source_transitions=100 * base, base_branch_transitions=1000 * base,
                    prefix_transitions=prefix, extra_terminal_transitions=extra_cost,
                    total_training_transitions=1100 * base + prefix + extra_cost)
            stage["method_acquisition"] = charges
            if cp == 6:
                frozen_charges = deepcopy(charges)
    return run


def test_exact_budget_partial_blocks_keep_behavior_primary_and_all_costs():
    result = ANALYZER.analyze_run(full_fixture())
    assert result["complete"] and result["primary_complete"]
    assert all(result["checks"].values())
    work = result["actual_executed_work"]
    assert work["actual_tree_fits"] == 44
    assert (work["new_pair_tree_fits"], work["new_v91_continuation_tree_fits"], work["new_head_tree_fits"]) == (12, 12, 20)
    assert work["prefix_transitions"] == work["extra_terminal_transitions"] == 1920
    assert work["newly_sampled_transitions"] == 8800
    extra = result["construction"]["extra_allocation_totals"]
    assert extra["incorporated_transitions"] == 800
    assert extra["unincorporated_transitions"] == 1120
    assert extra["budget_truncated_blocks"] == 4
    assert result["construction"]["work"]["extra_terminal"]["outcomes"]["CUTOFF"] == 4


def test_natural_terminal_missing_still_blocks_primary_with_extra_partial_budget():
    run = full_fixture()
    run["lifecycles"][0]["checkpoints"][1]["methods"]["MC_EXTRA"]["games"][0]["status"] = "CUTOFF"
    result = ANALYZER.analyze_run(run)
    assert result["complete"] and not result["primary_complete"]
    assert result["actual_executed_work"]["newly_sampled_transitions"] == 8800


@pytest.mark.parametrize("failure", ["budget", "partial_label", "heldout_fold", "frozen_charge", "old_batch"])
def test_material_allocation_and_fit_errors_invalidate_protocol(failure):
    run = full_fixture()
    stage = run["lifecycles"][0]["checkpoints"][1]
    if failure == "budget":
        stage["acquisition_extra"]["budget"] += 1
        key = "extra_environment_budget_matched"
    elif failure == "partial_label":
        stage["extra_merge"]["complete_extra_blocks"] += 1
        key = "extra_labels_use_complete_blocks"
    elif failure == "heldout_fold":
        stage["updates"]["v91_decomposed"]["tail_fits"]["full"]["queries"]["reward"]["training_episodes"].append(4)
        key = "fitting_accounting_complete"
    elif failure == "frozen_charge":
        stage["method_acquisition"]["MC_EXTRA_FROZEN_6"]["extra_terminal_transitions"] += 480
        key = "method_training_charges_match"
    else:
        stage["acquisition_extra"]["roster"][0]["episode"] = 0
        key = "extra_new_batch_round_robin_valid"
    result = ANALYZER.analyze_run(run)
    assert not result["complete"] and not result["primary_complete"]
    assert not result["checks"][key]

def test_uncertainty_uses_history_means_not_individual_game_count():
    run = natural_fixture()
    for life, score in zip(run["lifecycles"], (100, 80)):
        for game in life["checkpoints"][1]["methods"]["MC"]["games"]:
            game.update(score=score, utility=score / 2048)
    comparison = ANALYZER.analyze_natural(run)["checkpoints"]["12"]["comparisons"]["CORRECTED_minus_MC"]["reward"]
    uncertainty = comparison["descriptive_lifecycle_uncertainty"]
    assert comparison["mean_score_delta"] == 10
    assert uncertainty["score"] == pytest.approx(dict(lifecycles=2, standard_error=10, two_se_lower=-10, two_se_upper=30))
    assert uncertainty["utility"]["standard_error"] == pytest.approx(10 / 2048)
    assert "not a calibrated 95%" in uncertainty["scope"]
    run["lifecycles"][0]["checkpoints"][1]["methods"]["MC"]["games"][0]["status"] = "CUTOFF"
    comparison = ANALYZER.analyze_natural(run)["checkpoints"]["12"]["comparisons"]["CORRECTED_minus_MC"]["reward"]
    assert comparison["descriptive_lifecycle_uncertainty"] is None
