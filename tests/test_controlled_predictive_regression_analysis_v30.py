from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_controlled_predictive_regression_v30 as analysis


def margin(qhat, observed=True):
    return {"observed_both": observed, "q_hat_difference": qhat if observed else None,
        "q_star_difference": -.1, "A_transition_error_difference": .05 if observed else None,
        "D_continuation_error_difference": qhat + .05 if observed else None, "identity_residual": 0. if observed else None}


def boundary(index, wrong=False, policy_wrong=False):
    action, qhat, regret = ("UP", 1.2, .1) if wrong else ("DOWN", .9, 0.)
    local = {"selected_action": action, "local_regret": regret, "identities_pass": True,
        "actions": {"DOWN": {"observed": True, "q_hat": 1., "q_star": 1., "A_transition_error": 0., "D_continuation_error": 0., "batch_count": 8},
            "UP": {"observed": True, "q_hat": qhat, "q_star": .9, "A_transition_error": .05, "D_continuation_error": qhat - .95, "batch_count": 8}}}
    total = max(regret, .2 if policy_wrong else 0.)
    policy = {"initial_action": action, "policy_evaluable": True, "total_regret": total,
        "first_action_regret": regret, "continuation_regret": total-regret, "v_pi": 1.-total,
        "identities_pass": True, "reach_probability_pass": True, "terminal_probability": 1., "missing_probability": 0.}
    selected = margin(.2) if wrong else {"observed_both": True, **{key: 0. for key in (*analysis.MARGIN_COMPONENTS, "identity_residual")}}
    return {"boundary_index": index, "spent_batches": 32+index, "local_evaluation": local,
        "policy_evaluation": policy, "selected_vs_reference": selected}


def fixture():
    identity = {"context_index": 69, "board_index": 6, "case_name": "selected", "query_name": "query"}
    plan = {"context": identity, "replicates": [{"replicate_index": index, "base_seed": 10+index} for index in range(2)],
        "arms": ["CACHED", "VARIANCE"], "expected_trajectories": 4, "expected_boundaries_per_trajectory": 6,
        "source_historical_physical_batches": 100, "source_historical_physical_draws": 25600,
        "selected_suffix_historical_batches": 20, "selected_suffix_historical_draws": 5120}
    rows = []
    for rep in plan["replicates"]:
        for arm in plan["arms"]:
            boundaries = [boundary(i, wrong=i in (2, 3, 5), policy_wrong=i in (1, 2, 3, 5)) for i in range(6)]
            root_events = [{"from_boundary_index": 1, "to_boundary_index": 2, "kind": "CORRECT_TO_WRONG"},
                {"from_boundary_index": 3, "to_boundary_index": 4, "kind": "WRONG_TO_CORRECT"},
                {"from_boundary_index": 4, "to_boundary_index": 5, "kind": "CORRECT_TO_WRONG"}]
            trigger = {"after_boundary_index": 2, "request": {"kind": "FIRST_OBSERVATION"}, "update_location": "DOWNSTREAM",
                "previous_action": "DOWN", "new_action": "UP", "reference_action": "DOWN",
                "before_margin": margin(-.1), "after_margin": margin(.2),
                "before_local": boundaries[1]["local_evaluation"], "after_local": boundaries[2]["local_evaluation"]}
            rows.append({**rep, "arm": arm, "identity": identity, "status": "REPLAY_COMPLETE",
                **{key: {"passed": True} for key in analysis.VALIDATIONS}, "boundaries": boundaries,
                "transitions": root_events, "first_harmful_update": trigger,
                "original_costs": {"independent_query_seconds": 2., "local_whole_run_seconds": 1.},
                "original_local_accounting": {"physical_draws": 1280}, "accounting": {"replay_seconds": .5}})
    return {"plan": plan, "trajectories": rows, "plan_binding_validation": {"passed": True},
        "all_histories_bound_before_oracle": True, "oracle_used_for_replay_selection": False,
        "original_source_accounting": {"total_physical_batches": 100, "total_physical_draws": 25600},
        "accounting": {"new_provider_calls": 0, "new_sampling_calls": 0, "new_physical_draws": 0,
            "retained_batches_replayed": 20, "retained_draws_replayed": 5120,
            "historical_physical_batches": 100, "historical_physical_draws": 25600}}


def test_root_trigger_is_one_based_and_distinct_from_policy_harm_repairs_and_reentry():
    result = analysis.summarize(fixture())
    assert result["all_analysis_checks_passed"]
    row = result["trajectory_statuses"][0]
    assert row["first_root_harmful_batch"] == 2
    assert row["first_policy_harmful_batch"] == row["first_positive_policy_regret_boundary"] == 1
    assert row["root_repair_count"] == row["root_reentry_count"] == 1
    assert row["first_harmful_update"]["signed_margin_change"]["q_hat_difference"] == pytest.approx(.3)
    assert row["first_harmful_update"]["signed_margin_change"]["A_transition_error_difference"] == 0.
    assert row["first_harmful_update"]["signed_margin_change"]["D_continuation_error_difference"] == pytest.approx(.3)
    assert result["representative"]["replicate_index"] == 0 and result["representative"]["arm"] == "CACHED"
    assert result["by_arm"]["CACHED"]["trigger_row_locations"] == {"DOWNSTREAM": 2}
    assert "confidence_interval" not in str(result) and "boundaries" not in row
    wrong_index = fixture()
    wrong_index["trajectories"][0]["first_harmful_update"]["after_boundary_index"] = 1
    assert not analysis.summarize(wrong_index)["checks"]["first_root_harmful_batch_is_adjacent_update"]["passed"]


def test_unobserved_decomposition_remains_null_and_unknown_policy_does_not_create_transition():
    unknown = margin(None, observed=False)
    assert analysis.margin_valid(unknown)
    delta = analysis.signed_change(unknown, margin(.2))
    assert delta["q_hat_difference"] is delta["A_transition_error_difference"] is delta["D_continuation_error_difference"] is delta["identity_residual"] is None
    fabricated = deepcopy(unknown)
    fabricated["D_continuation_error_difference"] = 0.
    assert not analysis.margin_valid(fabricated)
    bounds = [boundary(0), boundary(1), boundary(2, wrong=True)]
    bounds[1]["policy_evaluation"].update(policy_evaluable=False, total_regret=None, continuation_regret=None, v_pi=None)
    assert analysis.transitions(bounds, policy=True) == []
    assert analysis.correctness(bounds[1], policy=True) is None


def test_failed_trajectory_remains_visible_and_keeps_all_original_costs():
    payload = fixture()
    failed = payload["trajectories"][0]
    failed.update(status="REPLAY_MISMATCH", boundaries=[], transitions=[], first_harmful_update=None)
    for key in analysis.VALIDATIONS:
        failed[key]["passed"] = False
    result = analysis.summarize(payload)
    assert not result["all_analysis_checks_passed"]
    assert result["trajectory_count"] == 4 and result["complete_trajectory_count"] == 3
    assert result["trajectory_statuses"][0]["status"] == "REPLAY_MISMATCH"
    assert result["representative"]["status"] == "REPLAY_MISMATCH"  # no convenient replacement
    assert result["selected_original_costs_including_failures"]["CACHED"]["attributed_cost_totals"]["independent_query_seconds"] == 4.
    assert result["original_source_accounting"] == payload["original_source_accounting"]
    assert result["accounting"]["historical_physical_draws"] == 25600
    payload["accounting"]["new_physical_draws"] = 256
    assert not analysis.summarize(payload)["checks"]["no_new_acquisition"]["passed"]


def test_all_failed_binding_records_remain_analyzable_without_replay_counter_entries():
    payload = fixture()
    payload["plan_binding_validation"]["passed"] = False
    payload["accounting"].pop("retained_batches_replayed")
    payload["accounting"].pop("retained_draws_replayed")
    for row in payload["trajectories"]:
        row.update(status="REPLAY_MISMATCH", boundaries=[], transitions=[], first_harmful_update=None)
        for key in analysis.VALIDATIONS:
            row[key]["passed"] = False
    result = analysis.summarize(payload)
    assert result["complete_trajectory_count"] == 0 and result["trajectory_count"] == 4
    assert not result["checks"]["plan_binding_and_oracle_separation"]["passed"]
    assert not result["checks"]["selected_retained_samples_replayed"]["passed"]
    assert result["selected_original_costs_including_failures"]["CACHED"]["attributed_cost_totals"]["independent_query_seconds"] == 4.
    assert result["checks"]["historical_physical_costs_retained"]["passed"]
