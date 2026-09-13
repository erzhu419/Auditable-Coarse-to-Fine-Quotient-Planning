"""Frozen V15 repeated-observation comparison on the unchanged V14 inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR, V7Case


V14_ROSTER = "controlled_predictive_cohort_roster_v14.json"
METHODS = ("full_state_empirical", "exact_empirical_quotient", "online_mass_bound",
           "online_balanced_resampling", "online_directed_resampling")
ONLINE_METHODS = METHODS[2:]
CANDIDATE_METHODS = METHODS[3:]


def _source(reports_dir: str | Path | None) -> dict:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    return json.loads((directory / V14_ROSTER).read_text(encoding="utf-8"))


def cases_v15(*, reports_dir: str | Path | None = None) -> tuple[V7Case, ...]:
    return tuple(V7Case(**(record["case"] | {"board": tuple(record["case"]["board"])}))
                 for record in _source(reports_dir)["cases"])


def build_cohort_roster_v15(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    source = _source(reports_dir)
    query_order = source["initial_query_order"]
    return {
        "schema": "controlled_predictive_cohort_roster_v15",
        "status": "REGISTERED_BEFORE_V15_TARGET_ACQUISITION_EXECUTION_AND_OUTCOMES",
        "v15_target_acquisition_execution_or_outcomes_evaluated": False,
        "input_roster": V14_ROSTER,
        "case_count": source["case_count"], "cases": source["cases"],
        "sample_seeds": source["sample_seeds"], "case_seed_count": source["case_seed_count"],
        "queries": source["queries"], "initial_query_order": query_order,
        "query_roles": source["query_roles"], "probe_or_query_holdout_roles": [],
        "query_execution_context_count": source["query_execution_context_count"],
        "query_execution_count_scope": "Each of five methods is evaluated on 16 original cases x 3 seeds x 10 queries; the three ONLINE methods produce 1440 adaptive history trees.",
        "historical_exposure": source["historical_exposure"],
        "scenario_count": 1, "scenario_case_evaluation_count": source["case_count"],
        "scenarios": source["scenarios"],
        "historical_primary_case_splits": source["historical_primary_case_splits"],
        "root_mass_groups": source["root_mass_groups"],
        "split_label_scope": "Original PRIMARY splits, families and mass groups remain historical development metadata; no source representation is fitted in V15.",
        "lofo_scenarios_reexecuted": False,
        "source_fitting_enabled": False, "source_priority_enabled": False, "source_fees": 0,
        "methods": list(METHODS), "online_methods": list(ONLINE_METHODS),
        "candidate_methods": list(CANDIDATE_METHODS),
        "samples_per_batch": 256,
        "initial_shared_row_cap": 32, "initial_shared_batch_cap": 32,
        "total_episode_batch_cap": 128, "maximum_episode_physical_draws": 32768,
        "batch_budget_scope": "Every first or repeated 256-sample acquisition consumes one batch. The total includes the paid warm prefix and every subsequent batch on the episode history; unique row count is not the repeated-observation budget.",
        "online_per_decision_quota": "(128 - spent_batches) // remaining_horizon",
        "online_quota_scope": "Fix this additional-batch quota when an ACTIVE decision is reached. Unused quota carries forward; terminal states take no decisions.",
        "single_active_query_for_online": True,
        "mass_bound": source["mass_bound"],
        "row_stream": {
            "batch_zero_version": "V12_V14_UNCHANGED",
            "key": "(remaining_horizon, tuple(board_ranks))",
            "action_order": source["row_stream"]["action_order"],
            "base_seeds": source["sample_seeds"],
            "batch_index_range": [0, 127],
            "batch_index_source": "The number of previous batches of this row on the current planner history.",
            "batch_seed_stride": 1000000,
            "integer_seed": "row_seed(base_seed + 1000000 * batch_index, key, action)",
            "sampling": "One current-row support enumeration and random.Random(integer_seed).choices(support, weights, k=256) per actual call.",
            "mutable_random_cursor": False, "discard_old_prefix_to_position_stream": False,
            "complete_support_returned_to_planner": False,
            "repeated_identical_batch_requests": "Physically enumerate and sample again; every such call is charged even when it belongs to an alternative counterfactual history.",
            "sharing_scope": "Only the explicitly shared paid warm prefix is reused across methods. Every post-warm method/query provider and every history-local row batch count is independent.",
        },
        "warm_preparation": {
            "planner": "Unchanged V14 MASS_BOUND incremental planner",
            "acquisition_mode": "query_interval", "query_order": query_order,
            "row_and_batch_cap": 32, "only_batch_zero": True,
            "physical_trajectory_count": source["case_seed_count"],
            "shared_by_methods": list(ONLINE_METHODS),
            "scope": "Build one paid first-batch prefix per case/seed from the original root; share its frozen 32-cap snapshot, with actual warm count allowed below32. No128 prefix is acquired for prewarming.",
            "integer_count_conversion": {
                "performed_once_per_warm_prefix": True,
                "shared_by_methods": list(CANDIDATE_METHODS),
                "conversion": "Convert each 256-sample aggregate row to integer outcome counts and initialize that row's batch count to1; pool later batches by summed counts.",
                "physical_cost_counted_once": True,
                "attribution": "Both candidate methods include the same conversion cost. Full warm preparation is charged to a standalone query or divided by ten for a declared batch; BASE does not pay candidate-only conversion.",
            },
        },
        "acquisition_methods": {
            "online_mass_bound": {
                "label": "BASE", "repeat_observations": False,
                "rule": "Use the unchanged V14 structural select_row, max-L action and ONLINE quota; stop acquisition at empirical closure or exhausted quota/budget.",
            },
            "online_balanced_resampling": {
                "label": "BALANCED", "repeat_observations": True,
                "rule": "Prefer the current-query structural select_row when available. Otherwise compute the shared score-policy reachable candidate set and choose the known positive-radius row with fewest batches, then key/action.",
            },
            "online_directed_resampling": {
                "label": "DIRECTED", "repeat_observations": True,
                "rule": "Prefer the current-query structural select_row when available. Otherwise compute the same candidate set and choose maximal empirical reach times radius, then key/action.",
            },
        },
        "resampling_score": {
            "terminal": "The original terminal query value.",
            "unknown_action": "The V14 physical mass-bound Q upper bound.",
            "known_action": "sum(empirical_probability * (reward_weight * reward + successor_S)) + radius",
            "radius": "(V14 physical Q_upper - V14 physical Q_lower) / sqrt(256 * row_batch_count)",
            "physical_width_scope": "The V14 unknown-action completion width evaluated from this board/horizon/query, not the current empirical Q interval width.",
            "state_score": "Maximum legal action score, with alphabetical action ties.",
            "candidate_set": "Known rows with radius >0 and positive reach under the score-maximizing policy; propagate reach only through their observed empirical transitions.",
            "clipping": False, "statistical_confidence_interval": False,
            "scope": "This deterministic acquisition priority is a sampling-uncertainty proxy, not a probabilistic guarantee or an execution-policy replacement.",
        },
        "candidate_stopping": ["total_batch_cap", "current_decision_quota", "terminal_state", "no_eligible_row"],
        "candidate_empirical_closure_stops_all_acquisition": False,
        "execution_action_rule": "Original maximal empirical lower-bound action with alphabetical ties; acquisition scores never replace the executed max-L policy.",
        "history_evaluation": {
            "execution_tree_count": source["query_execution_context_count"] * len(ONLINE_METHODS),
            "branch_history": source["stage_b"]["branch_history"],
            "true_dynamics_scope": "Evaluator-only selected-action transitions and final policy consequences; never returned to the planner as unsampled dynamics.",
            "deployment_cost": "Expected and maximum path batch requests and256draws include warm, first and repeated batches. Charge query-start state copying, profile, acquisition, count pooling, score/interval/frontier updates and decisions.",
            "physical_cost": "Count the shared warm acquisition/conversion once, every real post-warm batch call across all counterfactual histories, and one shared full-row benchmark acquisition. Sibling-history cloning is audit work, not deployment work.",
            "full_benchmarks": "The two complete empirical methods share a paid all-row batch0 acquisition per case/seed and remain larger-budget quality/cost benchmarks.",
        },
        "history_policy_examples": [example | {"method": "online_directed_resampling"}
                                    for example in source["history_policy_examples"]],
        "legacy_v14_comparison": {
            "input_result": "controlled_predictive_mass_bound_v14.json",
            "stage_a_mass_bound_warm_prefix_count": 48,
            "online_mass_bound_query_tree_count": 480,
            "scope": "BASE physically uses the newly paid shared V15 warm data and its own execution batches. Read the old V14 MASS_BOUND32 prefixes and ONLINE trees only after current trees freeze; the comparison issues no new acquisition or execution calls and compares semantics, not wall-clock equality.",
        },
        "all_sixteen_declared_cases_retained": True,
        "new_board_discovery_performed": False, "boards_or_symmetries_changed": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "u006_assurance_started": False,
        "scope": "Previously exposed development inputs only. V15 tests paid repeated observations and allocation on complete history-dependent policies; it does not change inputs, frozen structural bounds or the original scientific FAIL.",
    }


def freeze_cohort_roster_v15(path: str | Path, *, reports_dir: str | Path | None = None) -> dict[str, Any]:
    payload = build_cohort_roster_v15(reports_dir=reports_dir)
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return payload
