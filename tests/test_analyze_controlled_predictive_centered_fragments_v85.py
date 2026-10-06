"""Separate candidate differentiation, paired benefit and inherited acquisition."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("centered_analysis_v85", ROOT /
    "scripts/analyze_controlled_predictive_centered_fragments_v85.py")
ANALYSIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYSIS)
CALLS = []


@pytest.fixture(scope="module", autouse=True)
def retain_work(request):
    yield
    path = ROOT / "reports/controlled_predictive_centered_fragments_v85.analysis_checks.json"
    ledger = json.loads(path.read_text()) if path.exists() else {"attempts": []}
    ledger["attempts"].append(dict(test_module=__file__, session_failures=request.session.testsfailed,
        synthetic_analysis_calls=len(CALLS), main_campaign_calls=0, ground_calls=0))
    path.write_text(json.dumps(ledger, indent=2) + "\n")


def _run():
    methods = ["H2_ONLY", "CENTERED", "CENTERED_ONE_STEP", "CENTERED_FROZEN6", "JOINT", "FIXED_SPACE4"]
    run = dict(status="complete", settings=dict(lifecycles=[0, 1, 2], checkpoints=[6, 12], methods=methods,
        queries={"reward": {}, "risk_goal": {}}, evaluation_replicas=2, workers=3),
        lifecycles=[], actual_wall_seconds=10)
    for life in range(3):
        checkpoints = []
        for checkpoint in (6, 12):
            per_method = {}
            for method in methods:
                delta = [-2, 1, 10][life] if method == "CENTERED" and checkpoint == 12 else 0
                length = 0 if method == "H2_ONLY" else 1 if method in ("CENTERED_ONE_STEP", "JOINT") else 4
                selector = 6 if method == "CENTERED_FROZEN6" else checkpoint if method in ("CENTERED", "CENTERED_ONE_STEP", "JOINT") else None
                games = [dict(seed=life * 100 + replica, replica=replica, query=query,
                    score=2048 * (100 + delta), utility=100 + delta - (4 if query == "risk_goal" else 0),
                    status="LOST", steps=10, max_rank=8, seconds=0.1,
                    environment_counts={"sampled_transitions": 10}, planning_counts={"model_uniform_draws": 40},
                    selected_option=f"SPACE_{length}" if length else None,
                    initiation_step=2 if length else None, fragment_actions=length,
                    controller_events=1 if length else 0, duration_budget=length,
                    selector_checkpoint=selector, committed_length_matches=True)
                    for query in ("reward", "risk_goal") for replica in range(2)]
                costs = dict(evaluation_seconds=0.4)
                construction = 6 if method == "CENTERED_FROZEN6" else checkpoint
                if selector:
                    costs.update(inherited_source_seconds=construction, inherited_branch_seconds=construction * 100,
                        inherited_joint_preparation_seconds=construction / 12,
                        inherited_joint_fitting_seconds=construction / 6, inherited_joint_export_seconds=0)
                    if method == "JOINT":
                        costs["anchor_load_seconds"] = 0.01
                    else:
                        costs.update(preparation_seconds=construction / 6, fitting_seconds=construction / 6,
                            export_seconds=0)
                costs["total_seconds"] = sum(costs.values())
                per_method[method] = dict(games=games, costs=costs)
            records, roots = checkpoint * 8, checkpoint * 2
            training_roots, heldout_roots = checkpoint // 6 * 10, checkpoint // 6 * 2
            checkpoints.append(dict(episodes=checkpoint, methods=per_method,
                dataset=dict(records=records, roots=roots, training_roots=training_roots,
                    heldout_roots=heldout_roots, training_records=training_roots * 4, heldout_records=heldout_roots * 4),
                update=dict(counts={"fit_roots": training_roots, "fit_output_vectors": training_roots * 4, "tree_fits": 2}),
                input_preparation_seconds=1, new_fitting_seconds=1,
                inherited=dict(source_work={"sampled_transitions": checkpoint * 2},
                    branch_work={"sampled_transitions": checkpoint * 80}, source_games=checkpoint * 2,
                    branch_trajectories=checkpoint * 80, acquisition_costs=dict(source_seconds=checkpoint, branch_seconds=checkpoint * 100),
                    joint_costs=dict(preparation_seconds=checkpoint / 12, fitting_seconds=checkpoint / 6, export_seconds=0),
                    joint_fit_counts=dict(tree_fits=checkpoint // 3, fit_roots=10 if checkpoint == 6 else 30,
                        fit_output_vectors=40 if checkpoint == 6 else 120)),
                wiring={name: True for name in ANALYSIS.WIRING}, phase_seconds=5,
                pairwise_histories={method: dict(pairs=4, identical_to_h2=4 if method == "H2_ONLY" else 0) for method in methods},
                query_response={method: dict(pairs=2, identical_trajectory_pairs=2) for method in methods}))
        run["lifecycles"].append(dict(id=life, checkpoints=checkpoints))
    return run


def _analyze(run, name):
    CALLS.append(name)
    return ANALYSIS.analyze_run(run)


def test_four_step_use_does_not_erase_a_negative_lifecycle_or_add_old_samples():
    result = _analyze(_run(), "centered_output_accounting")
    assert result["complete"]
    effect = result["final_comparisons"]["CENTERED_minus_H2_ONLY"]["reward"]
    assert [row["mean_utility_delta"] for row in effect["lifecycles"]] == [-2, 1, 10]
    assert effect["mean_utility_delta"] == 3
    assert effect["positive_lifecycles"] == 2 and effect["negative_lifecycles"] == 1
    joint = result["checkpoints"][-1]["methods"]["CENTERED"]
    assert joint["queries"]["reward"]["pooled"]["four_step_selections"] == 6
    assert joint["queries"]["risk_goal"]["pooled"]["completed_four_step_fragments"] == 6
    assert joint["paired_histories"] == {"pairs": 12, "identical_to_h2": 0}
    assert result["first_to_last_checkpoint_change"]["CENTERED"]["reward"]["mean_utility_delta"] == 3
    assert result["actual_executed_work"]["newly_sampled_transitions"] == 1440
    assert result["actual_executed_work"]["new_source_games"] == 0
    assert result["actual_executed_work"]["new_branch_trajectories"] == 0
    assert result["inherited_acquisition"]["source_games"] == 72
    assert result["inherited_acquisition"]["source_work"]["sampled_transitions"] == 72
    assert result["inherited_acquisition"]["branch_work"]["sampled_transitions"] == 2880
    assert result["fitting"]["unique_reused_dataset"]["roots"] == 72
    assert result["fitting"]["new_fit_counts"]["fit_roots"] == 90
    assert result["fitting"]["new_fit_counts"]["fit_output_vectors"] == 360
    # Saved V84 counts are already cumulative, and must neither be summed across
    # checkpoints nor counted among the new centered fits.
    anchor = result["inherited_anchor_construction"]
    assert anchor["cumulative_costs"]["fitting_seconds"] == 6
    assert anchor["cumulative_fit_counts"]["tree_fits"] == 12
    assert anchor["cumulative_fit_counts"]["fit_roots"] == 90
    assert result["actual_executed_work"]["new_fit_counts"]["tree_fits"] == 12


def test_cutoff_in_any_arm_removes_its_replica_from_all_five_contrasts():
    run = _run()
    methods = run["lifecycles"][0]["checkpoints"][-1]["methods"]
    methods["JOINT"]["games"][0]["status"] = "CUTOFF"
    methods["CENTERED"]["games"][0]["score"] += 2048 * 1000
    methods["CENTERED"]["games"][0]["utility"] += 1000
    result = _analyze(run, "common_six_arm_cohort")
    assert result["complete"]
    assert not result["cohort"]["all_evaluation_games_terminal"]
    for comparison in result["final_comparisons"].values():
        assert comparison["reward"]["lifecycles"][0]["pairs"] == 1
        assert comparison["reward"]["mean_utility_delta"] == 3
    assert result["actual_executed_work"]["newly_sampled_transitions"] == 1440


def test_bad_pairing_frozen_model_or_root_units_are_reported():
    for name in ("pair", "frozen", "selector", "root_units", "wiring", "histories"):
        run = deepcopy(_run())
        checkpoint = run["lifecycles"][0]["checkpoints"][-1]
        if name == "pair":
            checkpoint["methods"]["CENTERED"]["games"][0]["seed"] += 1
        elif name == "frozen":
            checkpoint["methods"]["CENTERED_FROZEN6"]["games"][0]["score"] += 4
        elif name == "selector":
            checkpoint["methods"]["CENTERED_ONE_STEP"]["games"][0]["selector_checkpoint"] = 6
        elif name == "root_units":
            checkpoint["update"]["counts"]["fit_roots"] *= 4
        elif name == "wiring":
            checkpoint["wiring"]["committed_lengths_match"] = False
        else:
            checkpoint["pairwise_histories"]["CENTERED"]["pairs"] -= 1
        result = _analyze(run, name)
        assert not result["complete"]
        if name == "pair":
            assert result["final_comparisons"]["CENTERED_minus_H2_ONLY"]["reward"]["mean_utility_delta"] is None
