"""Detect false fragment gains from mismatched pairs or counted-again source work."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("fragment_analysis_v83", ROOT /
    "scripts/analyze_controlled_predictive_fragments_v83.py")
ANALYSIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYSIS)
CALLS = []


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_fragments_v83.analysis_checks.json"
    ledger = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    ledger["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        synthetic_analysis_calls=len(CALLS), main_campaign_calls=0, ground_calls=0))
    path.write_text(json.dumps(ledger, indent=2) + "\n")


def _run():
    methods = ["H2_ONLY", "ONE_STEP", "FRAGMENT", "FROZEN_6", "FIXED_SPACE4"]
    run = dict(status="complete", settings=dict(lifecycles=[0, 1, 2], checkpoints=[6, 12], methods=methods,
        queries={"reward": {}, "risk_goal": {}}, evaluation_replicas=2, source_episodes_per_query=12, workers=3),
        lifecycles=[], actual_wall_seconds=10)
    for life in range(3):
        checkpoints = []
        for checkpoint in (6, 12):
            per_method = {}
            for method in methods:
                delta = [-2, 1, 10][life] if method == "FRAGMENT" and checkpoint == 12 else 0
                length = 0 if method == "H2_ONLY" else 1 if method == "ONE_STEP" else 4
                selector = 6 if method == "FROZEN_6" else checkpoint if method in ("ONE_STEP", "FRAGMENT") else None
                games = [dict(seed=life * 100 + replica, replica=replica, query=query,
                    score=2048 * (100 + delta), utility=100 + delta - (4 if query == "risk_goal" else 0),
                    status="LOST", steps=10, max_rank=8, seconds=0.1,
                    environment_counts={"sampled_transitions": 10}, planning_counts={"model_uniform_draws": 40},
                    selected_option=f"SPACE_{length}" if length else None,
                    initiation_step=2 if length else None, fragment_actions=length,
                    controller_events=1 if length else 0, duration_budget=length, selector_checkpoint=selector)
                    for query in ("reward", "risk_goal") for replica in range(2)]
                costs = dict(source_seconds=checkpoint * 2 if selector else 0, branch_seconds=checkpoint * 40 if selector else 0,
                    fitting_seconds=1 if selector else 0, export_seconds=0, evaluation_seconds=0.4, total_seconds=checkpoint * 42 + 1.4)
                if method == "FROZEN_6":
                    costs["source_seconds"], costs["branch_seconds"] = 12, 240
                per_method[method] = dict(games=games, costs=costs)
            records, training, heldout = checkpoint * 8, checkpoint // 6 * 40, checkpoint // 6 * 8
            checkpoints.append(dict(episodes=checkpoint, methods=per_method,
                source=dict(games=12, roots=12, outcomes={"LOST": 12}, work={"sampled_transitions": 24},
                    planning_counts={"model_uniform_draws": 96}, seconds=1),
                branches=dict(roots=12, trajectories=480, censored_roots=0, outcomes={"LOST": 480},
                    work={"sampled_transitions": 960}, planning_counts={"model_uniform_draws": 3840}, seconds=2),
                dataset=dict(records=records, training_records=training, heldout_records=heldout),
                update=dict(checkpoint=checkpoint, input_records=records, training_records=training,
                    heldout_records=heldout, counts={"fit_rows": training, "tree_fits": 2}),
                wiring={name: True for name in ANALYSIS.WIRING}, phase_seconds=5,
                query_response={method: dict(pairs=2, identical_trajectory_pairs=2) for method in methods}))
        run["lifecycles"].append(dict(id=life, checkpoints=checkpoints))
    return run


def _analyze(run, name):
    CALLS.append(name)
    return ANALYSIS.analyze_run(run)


def test_paired_lifecycle_effects_choice_counts_and_actual_batch_work():
    result = _analyze(_run(), "correct_bounded_learning")
    assert result["complete"]
    effect = result["final_comparisons"]["FRAGMENT_minus_H2_ONLY"]["reward"]
    assert [row["mean_utility_delta"] for row in effect["lifecycles"]] == [-2, 1, 10]
    assert effect["mean_utility_delta"] == 3
    assert effect["mean_score_delta"] == 6144
    assert effect["positive_lifecycles"] == 2
    assert effect["negative_lifecycles"] == 1
    assert result["first_to_last_checkpoint_change"]["FRAGMENT"]["reward"]["mean_utility_delta"] == 3
    methods = result["checkpoints"][-1]["methods"]
    assert methods["ONE_STEP"]["queries"]["reward"]["pooled"]["selected_options"] == {"SPACE_1": 6}
    assert methods["FRAGMENT"]["queries"]["risk_goal"]["pooled"]["fragment_actions"] == 24
    assert methods["FROZEN_6"]["cumulative_cost_attribution"]["totals"]["source_seconds"] == 36
    work = result["actual_executed_work"]
    assert work["source_games"] == 72
    assert work["trajectories"] == 2880
    assert work["newly_sampled_transitions"] == 7104
    assert work["actual_wall_seconds"] == 10
    assert sum(row["seconds"] for row in work["lifecycle_phase_seconds"]) == 30
    assert result["learning_sources"]["unique_final_labels"]["records"] == work["new_labels"] == 288
    assert result["learning_sources"]["cumulative_fit_work"]["fit_rows"] == 360


def test_any_method_cutoff_uses_the_same_remaining_cohort_for_all_contrasts():
    run = _run()
    methods = run["lifecycles"][0]["checkpoints"][-1]["methods"]
    methods["ONE_STEP"]["games"][0]["status"] = "CUTOFF"
    # This attractive FRAGMENT outcome must leave every contrast with that replica.
    methods["FRAGMENT"]["games"][0]["score"] += 2048 * 1000
    methods["FRAGMENT"]["games"][0]["utility"] += 1000
    result = _analyze(run, "common_terminal_cohort")
    assert result["complete"]
    assert not result["cohort"]["all_evaluation_games_terminal"]
    for comparison in result["final_comparisons"].values():
        assert comparison["reward"]["lifecycles"][0]["pairs"] == 1
        assert comparison["reward"]["mean_utility_delta"] == 3
    assert result["actual_executed_work"]["newly_sampled_transitions"] == 7104


def test_pair_model_lineage_and_training_work_errors_are_visible():
    for name in ("pair", "frozen", "selector", "fitting", "wiring"):
        run = deepcopy(_run())
        checkpoint = run["lifecycles"][0]["checkpoints"][-1]
        if name == "pair":
            checkpoint["methods"]["FRAGMENT"]["games"][0]["seed"] += 1
        elif name == "frozen":
            checkpoint["methods"]["FROZEN_6"]["games"][0]["score"] += 4
        elif name == "selector":
            checkpoint["methods"]["ONE_STEP"]["games"][0]["selector_checkpoint"] = 6
        elif name == "fitting":
            checkpoint["update"]["counts"]["fit_rows"] += checkpoint["dataset"]["heldout_records"]
        else:
            checkpoint["wiring"]["committed_lengths_match"] = False
        result = _analyze(run, name)
        assert not result["complete"]
        if name == "pair":
            assert result["final_comparisons"]["FRAGMENT_minus_H2_ONLY"]["reward"]["mean_utility_delta"] is None
