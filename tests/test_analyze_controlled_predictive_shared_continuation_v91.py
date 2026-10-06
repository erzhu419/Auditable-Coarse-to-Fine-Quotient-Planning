"""Independent finite references and matched natural cohorts for V91."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("shared_continuation_analysis_v91",
    ROOT / "scripts/analyze_controlled_predictive_shared_continuation_v91.py")
ANALYZER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYZER)


def fixture():
    methods = {"6": ["H2_ONLY", "MC", "DECOMPOSED"],
        "12": ["H2_ONLY", "MC", "DECOMPOSED", "MC_FROZEN_6", "DECOMPOSED_FROZEN_6"]}
    settings = dict(lifecycles=[0, 1], checkpoints=[6, 12], methods_by_checkpoint=methods,
        queries={"reward": ANALYZER.QUERIES["reward"]}, evaluation_replicas=2,
        validation_replicas=2, validation_roots_per_query=2, workers=2)
    lives = []
    options = {"H2_ONLY": None, "MC": "SPACE_4", "DECOMPOSED": "H2",
        "MC_FROZEN_6": "SNAKE_4", "DECOMPOSED_FROZEN_6": "SNAKE_1"}
    scores = {"H2_ONLY": 100, "MC": 90, "DECOMPOSED": 100,
        "MC_FROZEN_6": 80, "DECOMPOSED_FROZEN_6": 95}
    for life in settings["lifecycles"]:
        stages = []
        for checkpoint in settings["checkpoints"]:
            method_records = {}
            for method in methods[str(checkpoint)]:
                games = []
                for replica in range(2):
                    selected = options[method]
                    duration = int(selected.split("_")[1]) if selected not in (None, "H2") else 0
                    games.append(dict(seed=100000 + checkpoint * 1000 + life * 100 + replica,
                        replica=replica, query="reward", score=scores[method], utility=scores[method] / 2048,
                        status="LOST", steps=10, max_rank=5, seconds=.01,
                        selected_option=selected, duration_budget=duration, fragment_actions=duration,
                        environment_counts={"sampled_transitions": 10}, planning_counts={"model_uniform_draws": 40}))
                method_records[method] = dict(games=games, costs={"evaluation_seconds": .02})
            gates = {}
            for left, right in ANALYZER._gate_pairs(methods[str(checkpoint)]):
                rows = []
                for new, old in zip(method_records[left]["games"], method_records[right]["games"]):
                    before, after = old["selected_option"], new["selected_option"]
                    category = ("both_h2" if before in (None, "H2") and after in (None, "H2") else
                        "enabled" if before in (None, "H2") else "disabled" if after in (None, "H2") else
                        "same_fragment" if before == after else "changed_fragment")
                    rows.append(dict(seed=new["seed"], query="reward", replica=new["replica"],
                        category=category, old_option=before, new_option=after))
                gates[f"{left}_minus_{right}"] = rows
            episodes = [episode for episode in range(checkpoint) if episode % 5 != 4]
            n = len(episodes)
            head = dict(counts={"tree_fits": 1, "fit_roots": n, "fit_output_vectors": 4 * n}, seconds=.1)
            tails = {}
            for name, fold in (("full", None), ("fold_0", 0), ("fold_1", 1)):
                tails[name] = dict(checkpoint=checkpoint, excluded_fold=fold,
                    counts={"tree_fits": 1, "continuation_tree_fits": 1}, seconds=.05,
                    queries={"reward": {"training_episodes": [episode for episode in episodes
                        if fold is None or episode % 2 != fold]}})
            decomp = dict(head_fit=deepcopy(head), tail_fits=tails, oof_episode_isolation=True,
                label_seconds=.03, seconds=.28, label_variance=[])
            stage = dict(episodes=checkpoint, methods=method_records, gate_changes=gates,
                wiring={name: True for name in ANALYZER.WIRING}, dataset=dict(roots=checkpoint,
                    training_roots=n, heldout_roots=checkpoint - n, records=checkpoint * 4),
                updates={"MC": deepcopy(head), "DECOMPOSED": decomp}, input_preparation_seconds=.2)
            if checkpoint == 12:
                records = []
                for episode in range(2):
                    root = dict(life=life, query="reward", episode=episode, board=[1, 0] * 8,
                        source_seed=100000 + checkpoint * 1000 + life * 100 + episode, step=5)
                    paired = {option: [[0., 0., 0.], [2., 0., 0.]] for option in ANALYZER.OPTIONS[1:]}
                    predictions = {}
                    for method in methods["12"][1:]:
                        reward = {"MC": 3., "DECOMPOSED": 1., "MC_FROZEN_6": 2., "DECOMPOSED_FROZEN_6": 0.}[method]
                        predictions[method] = dict(option=options[method], predictions={option:
                            dict(target=[reward, 0., 0.], value=reward) for option in ANALYZER.OPTIONS[1:]})
                    reconstruction = {option: dict(paired_targets=[[.5, 0., 0.], [1.5, 0., 0.]],
                        paired_residuals=[[.5, 0., 0.], [-.5, 0., 0.]]) for option in ANALYZER.OPTIONS[1:]}
                    log = dict(pair_deltas=paired, censored_root=False, trajectories=10,
                        ground_work={"sampled_transitions": 100}, planning_counts={"model_uniform_draws": 400},
                        outcomes={"LOST": 10})
                    records.append(dict(root=root, log=log, predictions=predictions, reconstruction=reconstruction))
                stage["validation"] = dict(roots=records, missing_roots=[], seconds=.5,
                    prediction_work={"continuation_predictions": 16})
            stages.append(stage)
        lives.append(dict(id=life, checkpoints=stages, actual_wall_seconds=1.,
            inherited=dict(source_work={"sampled_transitions": 20}, branch_work={"sampled_transitions": 200},
                source_games=12, branch_trajectories=40)))
    return dict(status="complete", settings=settings, lifecycles=lives, actual_wall_seconds=2.)


def test_complete_accounting_and_disabled_recovery_is_separate():
    result = ANALYZER.analyze_run(fixture())
    assert result["complete"] and result["primary_complete"]
    assert result["fitting"]["actual_tree_fits"] == 20
    assert result["actual_executed_work"]["head_tree_fits"] == 8
    assert result["actual_executed_work"]["continuation_tree_fits"] == 12
    assert result["actual_executed_work"]["new_evaluation_transitions"] == 320
    assert result["actual_executed_work"]["new_validation_transitions"] == 400
    assert result["actual_executed_work"]["new_training_transitions"] == 0
    assert result["validation"]["work"]["prediction_work"]["continuation_predictions"] == 32
    assert result["inherited"]["branch_work"]["sampled_transitions"] == 400
    stage = result["natural"]["checkpoints"]["12"]
    assert stage["comparisons"]["DECOMPOSED_minus_MC"]["reward"]["mean_score_delta"] == 10
    attribution = stage["gate_decomposition"]["DECOMPOSED_minus_MC"]["reward"]["primary_attribution"]
    assert attribution["cancelled_intervention_recovery_score_contribution"] == 10
    assert attribution["new_or_changed_intervention_h2_score_contribution"] == 0


def test_cutoff_keeps_actual_cost_and_equal_life_descriptive_weight():
    run = fixture()
    run["lifecycles"][0]["checkpoints"][1]["methods"]["MC"]["games"][1]["status"] = "CUTOFF"
    for game in run["lifecycles"][1]["checkpoints"][1]["methods"]["MC"]["games"]:
        game.update(score=100, utility=100 / 2048)
    result = ANALYZER.analyze_run(run)
    assert result["complete"] and not result["primary_complete"]
    comparison = result["natural"]["checkpoints"]["12"]["comparisons"]["DECOMPOSED_minus_MC"]["reward"]
    assert comparison["mean_score_delta"] is None
    assert comparison["available_common_terminal"]["mean_score_delta"] == 5
    assert [row["pairs"] for row in comparison["available_common_terminal"]["lifecycles"]] == [1, 2]
    assert result["actual_executed_work"]["newly_sampled_transitions"] == 720
    assert result["natural"]["work"]["outcomes"]["CUTOFF"] == 1


def test_finite_reference_error_and_paired_reconstruction_are_distinct():
    result = ANALYZER.analyze_run(fixture())
    validation = result["validation"]
    assert validation["heads"]["MC"]["reward"]["primary"]["mean_utility_bias"] == 2
    assert validation["heads"]["MC"]["reward"]["primary"]["mean_utility_mse"] == 4
    assert validation["heads"]["DECOMPOSED"]["reward"]["primary"]["mean_utility_mse"] == 0
    assert validation["heads"]["MC"]["reward"]["primary"]["selected_empirical_utility"] == 1
    assert validation["heads"]["DECOMPOSED"]["reward"]["primary"]["selected_empirical_utility"] == 0
    row = validation["reconstruction_root_options"][0]
    assert row["conditional_variance_ratio"] == pytest.approx(.25)
    assert row["paired_residual"]["mean_utility"] == 0
    assert row["paired_residual"]["standard_error"] == pytest.approx(.5)
    assert row["paired_residual"]["two_se_lower"] == -1
    assert "finite_terminal_reference" in validation["head_root_errors"][0]["candidates"][0]
    assert "not oracle values" in validation["reference_scope"]
    assert "exclude continuation-model fitting uncertainty" in validation["reference_scope"]


def test_censored_validation_root_does_not_silently_drop_from_primary():
    run = fixture()
    record = run["lifecycles"][0]["checkpoints"][1]["validation"]["roots"][0]
    record["log"].update(censored_root=True, pair_deltas={}, outcomes={"LOST": 9, "CUTOFF": 1})
    record["reconstruction"] = {}
    result = ANALYZER.analyze_run(run)
    assert result["complete"] and not result["primary_complete"]
    assert result["validation"]["heads"]["MC"]["reward"]["primary"] is None
    assert result["validation"]["work"]["trajectories"] == 40
    assert result["validation"]["work"]["ground_work"]["sampled_transitions"] == 400
    assert result["validation"]["work"]["outcomes"]["CUTOFF"] == 1


def test_missing_trigger_retains_real_life_field_and_fails_full_roster():
    run = fixture()
    validation = run["lifecycles"][0]["checkpoints"][1]["validation"]
    validation["roots"].pop()
    validation["missing_roots"].append(dict(life=0, query="reward", episode=1))
    result = ANALYZER.analyze_run(run)
    assert not result["complete"] and not result["primary_complete"]
    assert result["validation"]["missing_roots"] == [dict(life=0, query="reward", episode=1)]
    assert result["validation"]["work"]["trajectories"] == 30


def test_oof_episode_contamination_and_unpaired_residuals_are_detected():
    run = fixture()
    run["lifecycles"][0]["checkpoints"][0]["updates"]["DECOMPOSED"]["tail_fits"]["fold_0"]["queries"]["reward"]["training_episodes"].append(0)
    result = ANALYZER.analyze_run(run)
    assert not result["complete"]
    assert not result["checks"]["fitting_accounting_complete"]
    run = fixture()
    record = run["lifecycles"][0]["checkpoints"][1]["validation"]["roots"][0]
    record["reconstruction"][ANALYZER.OPTIONS[1]]["paired_residuals"][0][0] += 1
    result = ANALYZER.analyze_run(run)
    assert not result["complete"]
    assert not result["checks"]["validation_reconstruction_pairs_match"]
