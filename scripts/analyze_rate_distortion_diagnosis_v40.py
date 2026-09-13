"""Summarize retained V40 outcomes without refitting or rerunning models."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "reports/rate_distortion_v40"
summary = json.loads((ROOT / "summary.json").read_text())
rows = []
acquisition = {"rows": 0, "outcomes": 0, "construction_seconds": 0., "metric_seconds": 0., "exact_solve_seconds": 0.}
for filename in summary["case_files"]:
    case = json.loads((ROOT / filename).read_text())
    acquisition["rows"] += case["closure_counts"]["exact_transition_row_calls"]
    acquisition["outcomes"] += case["closure_counts"]["exact_outcomes_enumerated"]
    for key, value in case["costs"].items():
        acquisition[key] += value
    for condition, result in case["conditions"].items():
        fixed = result["converged"]
        diagnostic = fixed["diagnosis"]
        clamp = result["terminal_clamp"]
        comparison = result["snapshot_comparison"]
        events = comparison["action_disagreement_events"]
        inv = result["operator_inventory"]
        bias = fixed["predicted_root_value"] - fixed["root_value"]
        clamped_bias = clamp["predicted_root_value"] - clamp["root_value"]
        times = result["timing"]
        rows.append({
            "case": case["case"], "units": condition, "actual_root_value": fixed["root_value"],
            "optimal_root_value": case["exact_root_value"],
            "frozen_predicted_root_value": result["frozen_snapshot"]["predicted_root_value"],
            "converged_predicted_root_value": fixed["predicted_root_value"],
            "converged_bias": bias, "clamped_predicted_root_value": clamp["predicted_root_value"],
            "clamped_bias": clamped_bias, "clamp_improves_absolute_bias": abs(clamped_bias) < abs(bias),
            "clamp_changed_states": clamp["comparison_to_original_converged"]["disagreeing_states"],
            "remaining_iteration_error_bound": diagnostic["remaining_abstract_iteration_error_bound"],
            "terminal_source_root_contribution": diagnostic["source_layer_root_contributions"]["TERMINAL"],
            "snapshots_compared": comparison["snapshots"], "action_disagreement_events": len(events),
            "max_snapshot_root_value_difference": max((abs(e["root_value_difference"]) for e in events), default=0.),
            "max_snapshot_update_error": comparison["max_operator_error"],
            "max_identity_error": max(diagnostic["identities"]["maximum_absolute_residual"], result["frozen_diagnosis"]["identities"]["maximum_absolute_residual"]),
            "operator_array_bytes": inv["array_bytes"],
            "operator_plus_readout_array_bytes": inv["operator_plus_legal_readout_array_bytes"],
            "ground_model_array_bytes": inv["full_ground_model_array_bytes"],
            "median_backup_time_reduction_percent": 100 * (1 - times["compiled"]["median_seconds"] / times["author"]["median_seconds"]),
            "costs": result["costs"],
        })
analysis = {
    "rows": rows, "reconstruction_acquisition": acquisition,
    "total_compared_snapshots": sum(row["snapshots_compared"] for row in rows),
    "total_action_disagreement_events": sum(row["action_disagreement_events"] for row in rows),
    "clamp_improves_absolute_bias_conditions": sum(row["clamp_improves_absolute_bias"] for row in rows),
    "operator_plus_readout_exceeds_ground_bytes_conditions": sum(row["operator_plus_readout_array_bytes"] > row["ground_model_array_bytes"] for row in rows),
    "interpretation": "Arithmetic/operator agreement within tolerance does not establish identical actions. Terminal clamp changes the operator and is diagnostic only. Counts summarize the fixed six conditions, not a population sample.",
}
(ROOT / "analysis.json").write_text(json.dumps(analysis, indent=2, allow_nan=False) + "\n")
print(json.dumps({key: value for key, value in analysis.items() if key != "rows"}, indent=2))
