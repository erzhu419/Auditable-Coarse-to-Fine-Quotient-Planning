import copy
import importlib.util
from pathlib import Path


path = Path(__file__).resolve().parents[1] / "scripts/analyze_controlled_predictive_local_v21.py"
spec = importlib.util.spec_from_file_location("local_analysis_v21", path)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def fixture():
    key = [3, [2] * 16]
    choice = {"key": key, "selected_action": "LEFT", "selected_action_observed": True,
              "interval_closed": False, "local_regret": 0.0,
              "selected_action_in_true_optimal_set": True}
    target = {**choice, "target_key": key, "identities_pass": True,
              "maximum_absolute_identity_residual": 0.0,
              "actions": {"LEFT": {"observed": True, "q_hat": 0.2, "q_star": 0.3,
                  "A_transition_error": -0.025, "D_continuation_error": -0.075, "total_error": -0.1},
                  "RIGHT": {"observed": False, "q_hat": None, "A_transition_error": None,
                            "D_continuation_error": None, "total_error": None}}}
    evaluation = {"target": target, "panel": {"states": [choice], "state_count": 1,
        "selected_optimal_count": 1, "positive_regret_count": 0,
        "sum_local_regret": 0.0, "maximum_local_regret": 0.0}}
    local = {"requested_batch_count": 30, "completed_batches": 30,
        "initial_batches": 34, "final_batches": 64, "actual_draws": 7680,
        "completed_fixed_budget": True, "stop_reason": "FIXED_BATCH_BUDGET_COMPLETE",
        "first_original_stop_index": 2,
        "provider_counts": {"row_requests": 30, "physical_draws": 7680,
                            "first_batch_requests": 1, "repeat_batch_requests": 29},
        "accounting": {"seconds_by_stage": {"gap_assessment": 0.1},
                       "work_counts": {"gap_state_visits": 3}, "whole_run_seconds": 1.0}}
    contexts, identities = [], []
    for index in range(22):
        identity = {"context_index": index, "case_name": "case", "sample_seed": 832101,
                    "query_name": f"query_{index}", "group": "improvement" if index < 7 else "regression" if index < 20 else "old_witness_only",
                    "source_v20_changed": index < 20, "source_old_witness": index >= 12,
                    "source_old_group": "old" if index >= 12 else None}
        identities.append(identity)
        contexts.append({"identity": identity, "status": "LOCAL_COMPLETE", "target_key": key,
            "panel": [key], "requested_batch_count": 30, "initial_batches": 34, "request_index": 2,
            "run_order": list(analysis.ARMS if index % 2 == 0 else reversed(analysis.ARMS)),
            "paired_complete": True, "initial_evaluation": copy.deepcopy(evaluation),
            "arms": {arm: {"local": copy.deepcopy(local), "evaluation": copy.deepcopy(evaluation),
                           "source_validation": {"passed": True, "checks": {}}} for arm in analysis.ARMS}})
    return {"status": "DIAGNOSTIC_COMPLETE", "contexts": contexts,
            "cohort_roster": {"contexts": identities, "context_count": 22},
            "paired_complete_count": 22, "elapsed_seconds_before_report_serialization": 50,
            "common_snapshots_persisted_before_local_acquisition": True,
            "all_endpoints_persisted_before_oracle": True,
            "accounting": {"warm_prefix_count": 3, "warm_conversion_count": 3,
                "warm_physical_batches": 96, "warm_physical_draws": 24576,
                "retained_suffix_provider_calls": 0, "local_physical_batches": 1320,
                "local_physical_draws": 337920,
                "total_physical_draws_including_warm_regeneration": 362496,
                "local_allocation_wall_seconds": 44},
            "reconstruction_validation": {"warm_prefixes": [{"passed": True}] * 3}}


def test_incomplete_pair_retained_and_charged_but_excluded_from_primary():
    payload = fixture()
    context = payload["contexts"][0]
    local = context["arms"]["VARIANCE"]["local"]
    context.update(status="FIXED_BUDGET_INCOMPLETE", paired_complete=False)
    local.update(completed_batches=29, final_batches=63, actual_draws=7424,
                 completed_fixed_budget=False, stop_reason="NO_ELIGIBLE_CANDIDATE")
    local["provider_counts"].update(row_requests=29, physical_draws=7424, repeat_batch_requests=28)
    payload["paired_complete_count"] -= 1
    payload["accounting"]["local_physical_batches"] -= 1
    payload["accounting"]["local_physical_draws"] -= 256
    payload["accounting"]["total_physical_draws_including_warm_regeneration"] -= 256
    result = analysis.summarize(payload)
    assert result["all_analysis_checks_passed"]
    assert result["context_count"] == 22 and result["complete_pair_count"] == 21
    assert result["groups"]["improvement"]["complete_pair_count"] == 6
    assert result["requested_K"]["maximum"] == 30
    assert result["all_local_arms"]["VARIANCE"]["provider_counts"]["row_requests"] == 22 * 30 - 1
    assert result["all_local_arms"]["VARIANCE"]["whole_run_seconds"] == 22


def test_panel_expansion_and_invented_unknown_terms_are_reported():
    payload = fixture()
    evaluation = payload["contexts"][0]["arms"]["VARIANCE"]["evaluation"]
    evaluation["panel"]["states"].append({**evaluation["panel"]["states"][0], "key": [2, [2] * 16]})
    evaluation["panel"]["state_count"] = 2
    evaluation["target"]["actions"]["RIGHT"]["q_hat"] = 0.0
    result = analysis.summarize(payload)
    assert not result["all_analysis_checks_passed"]
    assert result["checks"]["fixed_panel"]["failed"] == 1
    assert result["checks"]["unknown_action_terms"]["failed"] == 1
