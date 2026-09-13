"""Frozen common-snapshot allocation intervention on all22 V20 diagnostic identities."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from .controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR

V20_ROSTER = "controlled_predictive_cohort_roster_v20.json"
V20_ANALYSIS = "controlled_predictive_variance_analysis_v20.json"
METHODS = ("CACHED", "VARIANCE")


def build_cohort_roster_v21(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    source = json.loads((directory / V20_ROSTER).read_text(encoding="utf-8"))
    analysis = json.loads((directory / V20_ANALYSIS).read_text(encoding="utf-8"))
    changed = analysis["pairs"]["VARIANCE_versus_CACHED"]["nonzero_component_contexts"]
    changed_index = {(row["case"], row["seed"], row["query"]): row for row in changed}
    old = source["source_witnesses"]
    old_index = {(row["case"], row["seed"], row["query"]): row for row in old}
    identities = set(changed_index) | set(old_index)
    contexts = []
    selected_cases = []
    for case_record in source["cases"]:
        case = case_record["case"]
        for seed in source["sample_seeds"]:
            for query_name in source["initial_query_order"]:
                identity = case["name"], seed, query_name
                if identity not in identities:
                    continue
                changed_row, old_row = changed_index.get(identity), old_index.get(identity)
                delta = changed_row["candidate_minus_comparator"]["value"] if changed_row else 0.0
                group = ("improvement" if delta > 0 else "regression") if changed_row else "old_witness_only"
                contexts.append({"context_index": len(contexts), "case_name": case["name"], "case": case,
                    "sample_seed": seed, "query_name": query_name, "query": source["queries"][query_name],
                    "group": group, "source_v20_changed": changed_row is not None,
                    "source_old_witness": old_row is not None,
                    "source_old_group": old_row["group"] if old_row else None,
                    "v20_value_difference": delta})
        if any(context["case_name"] == case["name"] for context in contexts):
            selected_cases.append(case_record)
    return {
        "schema": "controlled_predictive_cohort_roster_v21",
        "status": "REGISTERED_BEFORE_V21_COMMON_SNAPSHOT_EXTRACTION_LOCAL_ACQUISITION_AND_TRUTH",
        "common_snapshot_extraction_or_local_acquisition_evaluated": False,
        "input_roster": V20_ROSTER, "input_analysis": V20_ANALYSIS,
        "input_histories": "controlled_predictive_variance_v20.json.gz",
        "source_v20_changed_contexts": changed, "source_witnesses": old,
        "source_v20_changed_count": len(changed), "source_old_witness_count": len(old),
        "contexts": contexts, "context_count": len(contexts),
        "group_counts": dict(Counter(row["group"] for row in contexts)),
        "all_source_changed_and_old_witness_identities_included": True,
        "case_count": len(selected_cases), "cases": selected_cases,
        "sample_seeds": source["sample_seeds"], "queries": source["queries"],
        "initial_query_order": source["initial_query_order"], "query_roles": source["query_roles"],
        "historical_exposure": source["historical_exposure"],
        "methods": list(METHODS),
        "method_implementations": {"CACHED": "Unchanged V18 CachedGapPlannerState",
            "VARIANCE": "Unchanged V20 VarianceGapPlannerState"},
        "declared_common_snapshot_count": len(contexts), "declared_local_arm_count": 2 * len(contexts),
        "common_snapshot": {
            "search": "Breadth-first, preserving original retained child order. Follow only histories whose earlier requests, observations, actions and true-history edges agree exactly.",
            "request_identity": ["row_key", "batch_index", "kind"],
            "boundary": "Freeze immediately before the first differing acquisition request. Equal requests must have equal retained observations.",
            "state": "Preserve all observed rows, profiles, integer counts, accumulated batch counts, empirical policies and intervals. Do not convert a resampled state with from_warm or use post-divergence data.",
            "unavailable": "Keep every identity with a status and reason when no request difference exists or reconstruction fails; do not choose a substitute snapshot.",
            "persistence": "Persist every extracted common snapshot before starting any local intervention.",
        },
        "local_intervention": {
            "quota": "(128 - node.batches_before) // target_horizon",
            "common_batches_at_decision": "j = zero-based index of the first differing request",
            "snapshot_spent_batches": "node.batches_before + j",
            "fixed_batches_per_arm": "K = node.quota - j",
            "budget_scope": "Derive K only from the common pre-divergence record. Both arms have the same K; starting spent_batches plus K is at most128. Do not recompute a full decision quota at the snapshot or select K from later stopping/results.",
            "execution": "Clone the same snapshot independently for each original allocation class; remain at its target state for K acquisitions. Rotate arm order by context-index parity.",
            "stopping": "Record and charge every original gap assessment but jointly ignore its early-stop signal in this local intervention. Keep structural select_row priority and each original resampling selector, including zero-variance fallback.",
            "no_candidate": "Retain actual batches and the original no-candidate reason. Mark fixed-sample matching incomplete and exclude only from the complete-pair primary comparison, while retaining the identity and both arm records.",
            "samples_per_batch": 256, "total_path_batch_cap": 128,
            "source_reproduction": "The first actual request must match the corresponding recorded differing request. Validate subsequent retained requests while available; mark acquisition beyond recorded stopping as the local intervention.",
            "endpoint_persistence": "Persist both final observed models for all arms before constructing the exact evaluator.",
        },
        "fixed_state_panel": {
            "selection": "Starting at the target, traverse every already observed action row in the common snapshot; retain reachable known ACTIVE states including the target. Stop at unknown rows and sort by original state key.",
            "evaluation_points": ["COMMON_START", "CACHED_ENDPOINT", "VARIANCE_ENDPOINT"],
            "endpoint_new_states_expand_panel": False,
            "metrics": ["selected_action", "selected_action_observed", "empirical_interval_closed", "local_regret", "optimal_action"],
            "scope": "The common observed state panel is fixed before local acquisition and truth evaluation; states are not independent samples or a complete-policy evaluation.",
        },
        "target_evaluation": {
            "horizons": [1, 2, 3], "actions": "Every legal target action",
            "q_hat": "Current empirical lower-bound action value",
            "q_star": "Exact action value under optimal continuation",
            "A": "E_Phat[r+Vstar] - Qstar",
            "D": "E_Phat[Vhat-Vstar]",
            "identity": "Qhat-Qstar = A+D",
            "action_pairs": "All fixed alphabetical pairs of legal actions; retain empirical/true margins and A/D differences.",
            "unobserved_action": "Keep original lower/upper bounds and unobserved status; do not invent empirical transitions or A/D terms.",
            "regret": "Vstar(target)-Qstar(snapshot_selected_action)",
            "scope": "Current-action optimal-continuation benchmark only. No multi-step Vpi or claimed frozen/online complete-policy value.",
        },
        "warm_replay": {
            "planner": "Unchanged MASS_BOUND32 with the original ten queries and order",
            "sample_seeds": source["sample_seeds"], "trajectory_count": 3,
            "batch_cap_per_trajectory": 32, "physical_replayed_batches": 96,
            "physical_replayed_draws": 24576, "samples_per_batch": 256,
            "stream": source["row_stream"],
            "scope": "Rebuild one original batch-zero warm per seed and share its immutable results. Count actual regeneration as paid replay, not new independent evidence. Shared suffix prefixes replay retained aggregates without provider calls.",
        },
        "local_sampling": {
            "stream": source["row_stream"], "retain_accumulated_batch_indices": True,
            "physical_draws": "256 * actual_local_batch_requests, counted for every arm",
            "scope": "Use the same fixed row/batch streams and original seeds; every local provider call is physical work, including repeated rows. This is a posthoc allocation intervention, not an independent confirmation cohort.",
        },
        "reporting": "Retain all22 identities and7/13/2 groups, common-snapshot statuses, completed equal-K pairs, actual batches, target and fixed-panel choices/errors, stage costs and physical work. Do not condition selection on local outcomes.",
        "source_fits": 0, "source_setup_seconds": 0.0,
        "scientific_gate": "NOT_A_FORMAL_GATE", "u006_assurance_started": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "scope": "Posthoc local fixed-observation and fixed-batch intervention on exposed V20 contexts. The formal V18 stopping/execution rules remain unchanged and V20 remains a negative complete-policy comparison.",
    }


def freeze_cohort_roster_v21(path: str | Path, *, reports_dir: str | Path | None = None) -> dict[str, Any]:
    payload = build_cohort_roster_v21(reports_dir=reports_dir)
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return payload
