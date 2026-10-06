"""Actual deployed predictions, isolated model work, and fixed-cohort reference errors."""
from collections import Counter
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("direct_value_analysis_v95",
    ROOT / "scripts/analyze_controlled_predictive_direct_value_v95.py")
ANALYZER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYZER)


def fixture():
    choices = dict(H2_ONLY=None, MC_TAIL="SPACE_1", FQE="SPACE_4", MC_TAIL_DIRECT="SNAKE_1", FQE_DIRECT="H2",
        MC_TAIL_FROZEN_6="SPACE_1", FQE_FROZEN_6="SNAKE_4", MC_TAIL_DIRECT_FROZEN_6="SNAKE_1", FQE_DIRECT_FROZEN_6="SPACE_4")
    scores = {None: 100, "H2": 100, "SPACE_1": 90, "SPACE_4": 80, "SNAKE_1": 110, "SNAKE_4": 70}
    settings = dict(lifecycles=[3, 8], checkpoints=[12], methods_by_checkpoint={"12": list(choices)},
        queries={"reward": ANALYZER.QUERIES["reward"]}, evaluation_replicas=2, prefix_replicas=2,
        reference_replicas=2, validation_roots_per_query=2, horizon=4,
        contrasts=[list(pair) for pair in ANALYZER.CONTRASTS])
    run = dict(status="complete", settings=settings, lifecycles=[], inherited_data="retained_v94", actual_wall_seconds=2.)
    for life in settings["lifecycles"]:
        methods, inherited = {}, {}
        for method, option in choices.items():
            checkpoint = 6 if method.endswith("_FROZEN_6") else 12
            duration = int(option.split("_")[1]) if option not in (None, "H2") else 0
            games = []
            for replica in range(2):
                log = None
                planning = dict(model_uniform_draws=40)
                if "_DIRECT" in method:
                    log = dict(replicas=2, trajectories=10,
                        model_work=dict(synthetic_transitions=40, spawn_uniform_draws=80, model_spawn_samples=40),
                        planning_counts=dict(model_uniform_draws=160, model_spawn_samples=3),
                        value_counts=dict(continuation_predictions=10), outcomes={"ACTIVE": 10},
                        wiring={name: True for name in ANALYZER.SIMULATION_WIRING}, seconds=.01)
                    combined = Counter()
                    for name in ("model_work", "planning_counts", "value_counts"):
                        combined.update(log[name])
                    planning.update({"candidate_" + name: value for name, value in combined.items()})
                    planning.update(candidate_selector_decisions=1, candidate_trajectories=10)
                games.append(dict(seed=9710000 + life * 100 + replica, query="reward", replica=replica,
                    score=scores[option], utility=scores[option] / 2048, status="LOST", steps=10,
                    max_rank=5, seconds=.01, selected_option=option, duration_budget=duration,
                    fragment_actions=duration, initiation_step=5 if method != "H2_ONLY" else None,
                    selector_checkpoint=checkpoint if method != "H2_ONLY" else None,
                    environment_counts={"sampled_transitions": 10}, planning_counts=planning, candidate_evaluation=log))
            methods[method] = dict(games=games, costs={"evaluation_seconds": .02})
            if method != "H2_ONLY":
                source, branches = (100, 1000) if checkpoint == 12 else (50, 500)
                inherited[method] = dict(checkpoint=checkpoint, paths={"value" if "_DIRECT" in method else "head": "saved.json"},
                    training_acquisition=dict(source_transitions=source, base_branch_transitions=branches,
                        prefix_transitions=0, extra_terminal_transitions=0, total_training_transitions=source + branches))
        gates = {}
        for left, right in ANALYZER.CONTRASTS:
            records = []
            for new, old in zip(methods[left]["games"], methods[right]["games"]):
                before, after = old["selected_option"] or "H2", new["selected_option"] or "H2"
                category = ("both_h2" if before == after == "H2" else "enabled" if before == "H2" else
                    "disabled" if after == "H2" else "same_fragment" if before == after else "changed_fragment")
                records.append(dict(seed=new["seed"], query="reward", replica=new["replica"],
                    category=category, old_option=before, new_option=after))
            gates[left + "_minus_" + right] = records
        references = []
        for episode in range(2):
            root = dict(life=life, query="reward", episode=episode, source_seed=9710000 + life * 100 + episode,
                step=5, board=[1, 0] * 8)
            predictions = {}
            for method, option in choices.items():
                if method == "H2_ONLY":
                    continue
                values = {}
                for candidate in ANALYZER.OPTIONS:
                    target = 0. if candidate == "H2" else -1. if option == "H2" else (
                        (5. if candidate == option else 3.) if "_DIRECT" in method else (2. if candidate == option else 1.))
                    values[candidate] = dict(target=[target, 0., 0.], value=target)
                predictions[method] = dict(board=root["board"], step=5, option=option, predictions=values)
            references.append(dict(root=root, predictions=predictions, reference_complete=True,
                paired_reference={option: [[2., 0., 0.], [6., 0., 0.]] for option in ANALYZER.OPTIONS[1:]},
                terminal_log=dict(censored_root=False, trajectories=10, outcomes={"LOST": 10},
                    ground_work={"sampled_transitions": 100}, planning_counts={"model_uniform_draws": 400})))
        stage = dict(episodes=12, methods=methods, wiring={name: True for name in ANALYZER.WIRING}, gate_changes=gates,
            validation=dict(roots=references, missing_roots=[], seconds=.1, new_selector_calls=0, new_model_transitions=0),
            new_tree_fits=0, new_training_environment_transitions=0, inherited_models=inherited,
            inherited_training=dict(source={"sampled_transitions": 100}, branches={"sampled_transitions": 1000}),
            historical_v94_tree_fits=1556)
        run["lifecycles"].append(dict(id=life, checkpoints=[stage]))
    return run


def test_all_primary_contrasts_history_se_and_cancelled_recovery():
    run = fixture()
    for life, score in zip(run["lifecycles"], (100, 80)):
        for method in ("MC_TAIL", "MC_TAIL_FROZEN_6"):
            for game in life["checkpoints"][0]["methods"][method]["games"]:
                game.update(score=score, utility=score / 2048)
    result = ANALYZER.analyze_natural(run)
    assert all(result["checks"].values())
    stage = result["checkpoints"]["12"]
    assert len(stage["gate_decomposition"]) == 12
    difference = stage["comparisons"]["MC_TAIL_DIRECT_minus_MC_TAIL"]["reward"]
    assert difference["mean_score_delta"] == 20
    assert difference["descriptive_lifecycle_uncertainty"]["score"]["standard_error"] == 10
    attribution = stage["gate_decomposition"]["FQE_DIRECT_minus_FQE"]["reward"]["primary_attribution"]["score"]
    assert attribution["cancelled_intervention_recovery_contribution"] == 20
    assert attribution["new_or_changed_intervention_h2_contribution"] == 0


def test_executed_work_counts_simulation_once_and_keeps_ground_separate():
    result = ANALYZER.analyze_run(fixture())
    assert result["complete"] and result["primary_complete"]
    assert all(result["checks"].values())
    cost = result["actual_executed_work"]
    assert cost["newly_sampled_environment_transitions"] == 760
    assert cost["new_simulated_transitions"] == 640
    assert cost["simulated_selector_calls"] == 16
    assert cost["new_tree_fits"] == cost["new_training_environment_transitions"] == 0
    assert result["natural"]["work"]["planning_counts"]["candidate_synthetic_transitions"] == 640
    assert cost["simulated_model_work"]["model_spawn_samples"] == 640
    assert result["inherited"]["historical_v94_tree_fits"] == 3112


def test_original_deployed_predictions_use_independent_reference():
    result = ANALYZER.analyze_validation(fixture())
    assert result["methods"]["MC_TAIL"]["reward"]["primary"]["mean_utility_mse"] == 7.75
    assert result["methods"]["MC_TAIL_DIRECT"]["reward"]["primary"]["mean_utility_mse"] == 1
    assert result["methods"]["MC_TAIL_DIRECT"]["reward"]["primary"]["selected_reference_utility"] == 4
    assert result["methods"]["FQE_DIRECT"]["reward"]["primary"]["selected_reference_utility"] == 0
    assert result["roots"][0]["paired_reference"]["SPACE_1"]["standard_error"] == 2


def test_reference_cutoff_keeps_all_ground_and_model_costs_without_replacement():
    run = fixture()
    record = run["lifecycles"][0]["checkpoints"][0]["validation"]["roots"][0]
    record.update(reference_complete=False, paired_reference={})
    record["terminal_log"].update(censored_root=True, outcomes={"LOST": 9, "CUTOFF": 1})
    result = ANALYZER.analyze_run(run)
    assert result["complete"] and not result["primary_complete"]
    assert result["validation"]["methods"]["FQE_DIRECT"]["reward"]["primary"] is None
    assert result["actual_executed_work"]["newly_sampled_environment_transitions"] == 760
    assert result["actual_executed_work"]["new_simulated_transitions"] == 640


def test_no_trigger_means_no_simulation_and_preserves_other_costs():
    run = fixture()
    for method in run["lifecycles"][0]["checkpoints"][0]["methods"].values():
        game = method["games"][1]
        game.update(selected_option=None, initiation_step=None, candidate_evaluation=None)
        game["planning_counts"] = {key: value for key, value in game["planning_counts"].items() if not key.startswith("candidate_")}
    result = ANALYZER.analyze_simulation(run)
    assert all(result["checks"].values())
    assert result["decisions"] == 12
    assert result["model_work"]["synthetic_transitions"] == 480


def test_actor_rng_contamination_and_duplicate_counter_mismatch_are_detected():
    run = fixture()
    game = run["lifecycles"][0]["checkpoints"][0]["methods"]["FQE_DIRECT"]["games"][0]
    game["planning_counts"]["model_uniform_draws"] += 160
    game["planning_counts"]["candidate_synthetic_transitions"] += 40
    result = ANALYZER.analyze_simulation(run)
    assert not result["checks"]["simulated_actor_rng_separate"]
    assert not result["checks"]["simulated_work_accounted"]


def test_reference_selection_must_match_the_original_deployed_action():
    run = fixture()
    record = run["lifecycles"][0]["checkpoints"][0]["validation"]["roots"][0]
    record["predictions"]["FQE_DIRECT"]["option"] = "SPACE_1"
    result = ANALYZER.analyze_validation(run)
    assert not result["checks"]["deployed_prediction_rosters_complete"]
    assert result["methods"]["FQE_DIRECT"]["reward"]["primary"] is None


def test_inherited_checkpoint_and_zero_new_fit_requirements_are_checked():
    run = fixture()
    stage = run["lifecycles"][0]["checkpoints"][0]
    stage["inherited_models"]["FQE_DIRECT"]["checkpoint"] = 6
    stage["new_tree_fits"] = 1
    result = ANALYZER.analyze_inheritance(run)
    assert not result["checks"]["inherited_model_rosters_match"]
    assert not result["checks"]["no_new_training_or_fitting"]
