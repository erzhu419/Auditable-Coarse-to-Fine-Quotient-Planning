"""Actual deployed predictions, isolated model work, and fixed-cohort reference errors."""
from collections import Counter
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("boundary_learning_analysis_v97",
    ROOT / "scripts/analyze_controlled_predictive_boundary_learning_v97.py")
ANALYZER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYZER)


def weighting(checkpoint):
    summary = dict(groups=2, singletons=1, rows=4, prior_total_mass=.125, new_total_mass=.125,
        prior_boundary_mass=.0625, new_boundary_mass=.078125, prior_tail_mass=.0625,
        new_tail_mass=.046875, singleton_boundary_mass=.03125,
        prior_boundary_share=.5, new_boundary_share=.625, max_pair_mass_error=0.)
    return dict(checkpoint=checkpoint, target_boundary_share=.5, eligible_episodes={"reward": [0, 1]},
        queries={"reward": deepcopy(summary)}, totals=summary,
        counts={"training_rows": 4, "groups": 2, "new_environment_transitions": 0, "tree_fits": 0}, seconds=.001)


def boundary_diagnostics(checkpoint):
    models = ("PAIR_MC", "PAIR_FQE", "BOUNDARY_MC", "BOUNDARY_FQE")
    strata = {}
    for name, size, error in (("all", 2, 2.), ("boundary", 1, 3.), ("tail", 1, 1.)):
        strata[name] = dict(rows=size, episodes=[4], weight_sum=size / 32,
            models={model: dict(mse_rfs=[error, 0., 0.], utility_mse=error,
                bias_rfs=[.1, 0., 0.], utility_bias=.1, mean_prediction_rfs=[1., 0., 0.],
                mean_target_rfs=[1., 0., 0.], mean_terminal_mass_gap=.1,
                mean_absolute_terminal_mass_gap=.2) for model in models})
    return dict(checkpoint=checkpoint, scoring_weight=1 / 32,
        queries={"reward": dict(rows=2, episodes=[4], strata=strata)},
        feature_counts={"board_feature_rows": 4},
        model_counts={model: {"paired_continuation_predictions": 2} for model in models},
        counts={"board_feature_rows": 4, "paired_continuation_predictions": 8}, seconds=.004)


def construction(checkpoint):
    diagnostic = dict(mean_prediction_rfs=[1., .2, -.1], mean_target_rfs=[1., 0., 0.],
        fit_target_mse_rfs=[.2, .1, .1], mean_terminal_mass_gap=.1,
        mean_absolute_terminal_mass_gap=.3, utility_mse=.2, counts={"tree_fits": 1}, seconds=.01)
    return dict(checkpoint=checkpoint, weighting=weighting(checkpoint), diagnostics=boundary_diagnostics(checkpoint),
        data=dict(counts=dict(roots=12, eligible_roots=11, censored_roots=1,
                new_environment_transitions=0, tree_fits=0),
            inherited_environment_work={"sampled_transitions": 1000},
            inherited_planning_work={"model_uniform_draws": 4000},
            paired_crn_contract_matches=True, retained_means_match=True, seconds=.02),
        fit_log=dict(checkpoint=checkpoint, iterations=2, training_episodes={"reward": [0, 1]},
            queries={"reward": dict(training_episode_count=2, training_rows=4)},
            cache_counts={"feature_cache_builds": 1}, cache_seconds=.005,
            PAIR_MC=dict(counts={"tree_fits": 1, "pair_mc_tree_fits": 1},
                queries={"reward": deepcopy(diagnostic)}, seconds=.01),
            PAIR_FQE=dict(counts={"tree_fits": 2, "pair_fqe_tree_fits": 2},
                queries={"reward": {"counts": {"tree_fits": 2}, "seconds": .02}},
                initialization="PAIR_MC", seconds=.02,
                iterations=[dict(iteration=i, queries={"reward": deepcopy(diagnostic)}) for i in (1, 2)]),
            heldout=dict(counts={"paired_continuation_predictions": 4}, seconds=.003,
                queries={"reward": dict(episodes=[4], rows=2, weight_sum=2.,
                    **{family: {key: value for key, value in diagnostic.items() if key not in ("counts", "seconds")}
                        for family in ("PAIR_MC", "PAIR_FQE")})}),
            counts={"tree_fits": 3, "pair_mc_tree_fits": 1, "pair_fqe_tree_fits": 2,
                "paired_continuation_predictions": 4}, seconds=.04))


def fixture():
    choices = dict(H2_ONLY=None, PAIR_MC_DIRECT="SPACE_1", PAIR_FQE_DIRECT="SPACE_4", BOUNDARY_MC_DIRECT="SNAKE_1", BOUNDARY_FQE_DIRECT="H2",
        PAIR_MC_DIRECT_FROZEN_6="SPACE_1", PAIR_FQE_DIRECT_FROZEN_6="SNAKE_4", BOUNDARY_MC_DIRECT_FROZEN_6="SNAKE_1", BOUNDARY_FQE_DIRECT_FROZEN_6="SPACE_4")
    scores = {None: 100, "H2": 100, "SPACE_1": 90, "SPACE_4": 80, "SNAKE_1": 110, "SNAKE_4": 70}
    settings = dict(lifecycles=[3, 8], checkpoints=[12], methods_by_checkpoint={"12": list(choices)},
        queries={"reward": ANALYZER.QUERIES["reward"]}, evaluation_replicas=2, prefix_replicas=2,
        reference_replicas=2, validation_roots_per_query=2, horizon=4, iterations=2, model_checkpoints=[6, 12],
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
                        value_counts={"paired_continuation_predictions": 8}, outcomes={"ACTIVE": 10},
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
                        (5. if candidate == option else 3.) if method.startswith("BOUNDARY_") else (2. if candidate == option else 1.))
                    values[candidate] = dict(target=[target, 0., 0.], value=target)
                predictions[method] = dict(board=root["board"], step=5, option=option, predictions=values)
            references.append(dict(root=root, predictions=predictions, reference_complete=True,
                paired_reference={option: [[2., 0., 0.], [6., 0., 0.]] for option in ANALYZER.OPTIONS[1:]},
                terminal_log=dict(censored_root=False, trajectories=10, outcomes={"LOST": 10},
                    ground_work={"sampled_transitions": 100}, planning_counts={"model_uniform_draws": 400})))
        stage = dict(episodes=12, methods=methods, wiring={name: True for name in ANALYZER.WIRING}, gate_changes=gates,
            validation=dict(roots=references, missing_roots=[], seconds=.1, new_selector_calls=0, new_model_transitions=0),
            new_tree_fits=6, new_training_environment_transitions=0, construction=[construction(cp) for cp in (6, 12)], inherited_models={name: value for name, value in inherited.items() if name.startswith("PAIR_")},
            inherited_training=dict(source={"sampled_transitions": 100}, branches={"sampled_transitions": 1000}),
            historical_v94_tree_fits=1556, historical_v96_tree_fits=516)
        run["lifecycles"].append(dict(id=life, checkpoints=[stage]))
    return run


def test_primary_contrasts_equal_history_se_and_cancelled_gain():
    run = fixture()
    for life, score in zip(run["lifecycles"], (100, 80)):
        for game in life["checkpoints"][0]["methods"]["PAIR_MC_DIRECT"]["games"]:
            game.update(score=score, utility=score / 2048)
    result = ANALYZER.analyze_natural(run)
    assert all(result["checks"].values())
    stage = result["checkpoints"]["12"]
    assert len(stage["gate_decomposition"]) == 12
    difference = stage["comparisons"]["BOUNDARY_MC_DIRECT_minus_PAIR_MC_DIRECT"]["reward"]
    assert difference["mean_score_delta"] == 20
    assert difference["descriptive_lifecycle_uncertainty"]["score"]["standard_error"] == 10
    attribution = stage["gate_decomposition"]["BOUNDARY_FQE_DIRECT_minus_PAIR_FQE_DIRECT"]["reward"]["primary_attribution"]["score"]
    assert attribution["cancelled_intervention_recovery_contribution"] == 20
    assert attribution["new_or_changed_intervention_h2_contribution"] == 0


def test_actual_full_only_fits_and_all_eight_direct_costs_counted_once():
    result = ANALYZER.analyze_run(fixture())
    assert result["complete"] and result["primary_complete"]
    assert all(result["checks"].values())
    cost = result["actual_executed_work"]
    assert cost["new_tree_fits"] == 12
    assert cost["new_boundary_mc_fits"] == 4 and cost["new_boundary_fqe_fits"] == 8
    assert cost["new_training_environment_transitions"] == 0
    assert cost["newly_sampled_environment_transitions"] == 760
    assert cost["new_simulated_transitions"] == 1280
    assert cost["simulated_selector_calls"] == 32
    assert cost["simulated_value_counts"].get("continuation_predictions", 0) == 0
    assert cost["simulated_value_counts"]["paired_continuation_predictions"] == 256
    assert cost["construction_seconds"]["fitting_total"] == pytest.approx(.16)
    assert cost["construction_seconds"]["heldout_evaluation"] == pytest.approx(.012)
    assert result["construction"]["counts"]["paired_continuation_predictions"] == 48
    assert result["construction"]["heldout_diagnostics"][0]["PAIR_FQE"]["utility_mse"] == .2
    assert result["inherited"]["acquisition"]["branches"]["sampled_transitions"] == 2000
    assert result["inherited"]["historical_v94_tree_fits"] == 3112
    assert result["inherited"]["historical_v96_tree_fits"] == 1032
    assert cost["construction_seconds"]["boundary_diagnostics"] == pytest.approx(.016)
    assert result["construction"]["boundary_diagnostic_counts"]["paired_continuation_predictions"] == 32
    layer = result["construction"]["boundary_diagnostics"][0]["queries"]["reward"]["strata"]
    assert layer["boundary"]["models"]["BOUNDARY_FQE"]["utility_mse"] == 3
    assert layer["tail"]["models"]["PAIR_MC"]["utility_mse"] == 1


def test_deployed_predictions_have_independent_reference_and_no_oracle_baseline():
    result = ANALYZER.analyze_validation(fixture())
    assert result["methods"]["PAIR_MC_DIRECT"]["reward"]["primary"]["mean_utility_mse"] == 7.75
    assert result["methods"]["BOUNDARY_MC_DIRECT"]["reward"]["primary"]["mean_utility_mse"] == 1
    assert result["methods"]["BOUNDARY_MC_DIRECT"]["reward"]["primary"]["selected_reference_utility"] == 4
    assert result["methods"]["BOUNDARY_FQE_DIRECT"]["reward"]["primary"]["selected_reference_utility"] == 0
    assert result["roots"][0]["paired_reference"]["SPACE_1"]["standard_error"] == 2


def test_cutoff_preserves_training_ground_and_simulation_costs():
    run = fixture()
    record = run["lifecycles"][0]["checkpoints"][0]["validation"]["roots"][0]
    record.update(reference_complete=False, paired_reference={})
    record["terminal_log"].update(censored_root=True, outcomes={"LOST": 9, "CUTOFF": 1})
    result = ANALYZER.analyze_run(run)
    assert result["complete"] and not result["primary_complete"]
    assert result["validation"]["methods"]["BOUNDARY_FQE_DIRECT"]["reward"]["primary"] is None
    assert result["actual_executed_work"]["new_tree_fits"] == 12
    assert result["actual_executed_work"]["newly_sampled_environment_transitions"] == 760
    assert result["actual_executed_work"]["new_simulated_transitions"] == 1280


def test_pair_prediction_roster_and_actor_rng_contamination_are_checked():
    run = fixture()
    game = run["lifecycles"][0]["checkpoints"][0]["methods"]["BOUNDARY_FQE_DIRECT"]["games"][0]
    game["candidate_evaluation"]["value_counts"]["paired_continuation_predictions"] = 10
    game["planning_counts"]["model_uniform_draws"] += 160
    result = ANALYZER.analyze_simulation(run)
    assert not result["checks"]["simulated_work_accounted"]
    assert not result["checks"]["simulated_actor_rng_separate"]


def test_mass_error_is_diagnostic_and_uses_existing_predictions():
    run = fixture()
    for life in run["lifecycles"]:
        for record in life["checkpoints"][0]["validation"]["roots"]:
            for event in record["predictions"].values():
                for option, gap in zip(ANALYZER.OPTIONS[1:], (-.4, .4, -.4, .4)):
                    event["predictions"][option]["target"][1] = gap
    result = ANALYZER.analyze_run(run)
    assert result["primary_complete"]
    diagnostic = result["prediction_mass"]["methods"]["BOUNDARY_FQE_DIRECT"]["reward"]["primary"]
    assert diagnostic["mean_terminal_mass_gap"] == 0
    assert diagnostic["mean_absolute_terminal_mass_gap"] == pytest.approx(.4)
    assert result["construction"]["final_training_diagnostics"][0]["mean_absolute_terminal_mass_gap"] == .3


def test_whole_episode_exclusion_and_fit_accounting_detect_actual_contract_breaks():
    run = fixture()
    stage = run["lifecycles"][0]["checkpoints"][0]
    fit = stage["construction"][0]["fit_log"]
    fit["training_episodes"]["reward"] = [0, 4]
    stage["new_tree_fits"] += 1
    result = ANALYZER.analyze_construction(run)
    assert not result["checks"]["whole_episode_isolation"]
    assert not result["checks"]["new_fitting_accounted"]


def test_singletons_mass_preservation_and_uniform_scoring_are_checked_separately():
    record = construction(12)
    assert all(ANALYZER.weighting_checks(record["weighting"]).values())
    record["weighting"]["totals"]["max_pair_mass_error"] = .01
    record["weighting"]["totals"]["new_boundary_share"] = .5
    checks = ANALYZER.weighting_checks(record["weighting"])
    assert not checks["boundary_pair_mass_preserved"]
    assert not checks["boundary_weight_share_matches"]
    record["diagnostics"]["queries"]["reward"]["strata"]["boundary"]["weight_sum"] = .5
    checks = ANALYZER.boundary_diagnostic_checks(record["diagnostics"], fixture()["settings"])
    assert not checks["heldout_scoring_unchanged"]
