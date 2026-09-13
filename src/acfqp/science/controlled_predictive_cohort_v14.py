"""Frozen V14 inputs and mass groups for one structural upper-bound comparison."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from acfqp.domains.standard_2048 import GOAL_RANK
from .controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR, V7Case


V13_ROSTER = "controlled_predictive_cohort_roster_v13.json"
VARIANTS = ("LEGACY", "MASS_BOUND")
EXECUTION_ARMS = ("upfront_legacy", "upfront_mass_bound", "online_legacy", "online_mass_bound")
REFERENCE_ARMS = ("frozen32_legacy", "frozen32_mass_bound", "full_state_empirical", "exact_empirical_quotient")
GOAL_QUERY_PAIRS = (("goal_1_risk_1", "risk_1"), ("probe_goal_2_risk_0_5", "probe_risk_0_5"))


def _source(reports_dir: str | Path | None) -> dict:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    return json.loads((directory / V13_ROSTER).read_text(encoding="utf-8"))


def cases_v14(*, reports_dir: str | Path | None = None) -> tuple[V7Case, ...]:
    return tuple(V7Case(**(record["case"] | {"board": tuple(record["case"]["board"])}))
                 for record in _source(reports_dir)["cases"])


def build_cohort_roster_v14(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    source = _source(reports_dir)
    query_order = source["initial_query_order"]
    records = []
    for record in source["cases"]:
        case = record["case"]
        mass = sum(1 << rank for rank in case["board"] if rank)
        upper_mass = mass + 4 * case["horizon"]
        records.append(record | {"total_tile_mass": mass, "mass_plus_4h": upper_mass,
                                 "goal_mass_excluded": upper_mass < 1 << GOAL_RANK})
    groups = {
        "goal_mass_excluded": [record["case"]["name"] for record in records if record["goal_mass_excluded"]],
        "goal_mass_not_excluded": [record["case"]["name"] for record in records if not record["goal_mass_excluded"]],
    }
    four_queries = {query for pair in GOAL_QUERY_PAIRS for query in pair}
    return {
        "schema": "controlled_predictive_cohort_roster_v14",
        "status": "REGISTERED_BEFORE_V14_TARGET_ACQUISITION_EXECUTION_AND_OUTCOMES",
        "v14_target_acquisition_execution_or_outcomes_evaluated": False,
        "input_roster": V13_ROSTER,
        "case_count": source["case_count"], "cases": records,
        "sample_seeds": source["sample_seeds"], "case_seed_count": source["case_seed_count"],
        "queries": source["queries"], "initial_query_order": query_order,
        "query_roles": source["query_roles"], "probe_or_query_holdout_roles": [],
        "query_execution_context_count": source["query_execution_context_count"],
        "query_execution_count_scope": "Each of eight methods is evaluated on 16 original cases x 3 seeds x 10 declared queries; four acquisition methods produce 1920 execution trees.",
        "historical_exposure": source["historical_exposure"],
        "scenario_count": 1, "scenario_case_evaluation_count": source["case_count"],
        "scenarios": source["scenarios"],
        "historical_primary_case_splits": source["historical_primary_case_splits"],
        "split_label_scope": "Original PRIMARY splits and families remain historical metadata; no source representation is fitted or used in V14.",
        "lofo_scenarios_reexecuted": False,
        "source_fitting_enabled": False, "source_priority_enabled": False, "source_fees": 0,
        "samples_per_acquired_row": source["samples_per_acquired_row"],
        "row_stream": source["row_stream"],
        "initial_shared_row_cap": 32, "total_episode_row_cap": 128,
        "initial_acquisition_mode": "query_interval",
        "single_active_query_for_upfront_and_online": True,
        "online_per_decision_quota": source["online_per_decision_quota"],
        "online_quota_scope": source["online_quota_scope"],
        "variants": list(VARIANTS),
        "variant_scope": {
            "LEGACY": "Unchanged V13 incremental interval planner.",
            "MASS_BOUND": "Same incremental planner; only the goal-bonus upper-bound term of an unobserved ACTIVE action becomes zero when mass + 4*h < 2048.",
            "unchanged": ["lower_bounds", "reward_upper_bounds", "failure_bounds", "empirical_rows", "terminal_values", "quota", "tie_order", "stopping_tolerance", "row_stream"],
        },
        "mass_bound": {
            "goal_rank": GOAL_RANK, "goal_tile_value": 1 << GOAL_RANK,
            "maximum_spawn_value_per_step": 4,
            "predicate": "ACTIVE and total_tile_mass + 4 * remaining_horizon < 2048",
            "equality_behavior": "At equality retain the legacy goal-bonus upper bound.",
            "won_behavior": "Already WON states retain terminal goal_bonus before ACTIVE unknown-action bounds are considered.",
        },
        "root_mass_groups": groups,
        "mechanism_query_pairs": [{"goal_query": goal, "no_goal_query": no_goal}
                                  for goal, no_goal in GOAL_QUERY_PAIRS],
        "mechanism_comparison": {
            "case_names": groups["goal_mass_excluded"],
            "variants": list(VARIANTS), "execution_modes": ["upfront", "online"],
            "comparison_fields": ["complete_trace", "root_metrics"],
            "scope": "Within each variant, compare the already declared goal and no-goal query trees on roots excluded by the frozen mass predicate. No extra roots, seeds, queries, or provider calls.",
            "mass_bound_expected_equal": True,
            "legacy_expected_equal": False,
            "legacy_expectation_scope": "LEGACY equality is measured, not required to pass or fail.",
        },
        "stage_a": {
            "variants": list(VARIANTS), "update_modes": ["incremental"],
            "acquisition_mode": "query_interval", "row_checkpoints": [32, 128],
            "query_order": query_order, "independent_trajectories": True,
            "trajectory_count": source["case_seed_count"] * len(VARIANTS),
            "scope": "Each variant independently starts from the root and preserves its own 32/128 multi-query prefixes. Cross-variant observations may differ as part of the method's effect.",
        },
        "stage_b": {
            "execution_arms": list(EXECUTION_ARMS), "reference_arms": list(REFERENCE_ARMS),
            "execution_tree_count": source["query_execution_context_count"] * len(EXECUTION_ARMS),
            "upfront_acquisition": source["stage_b"]["upfront_acquisition"],
            "online_acquisition": source["stage_b"]["online_acquisition"],
            "branch_history": source["stage_b"]["branch_history"],
            "prefix_accounting": "Each variant shares only its own paid Stage A 32-row snapshot within that variant. Initial preparation is attributed fully for a standalone query and divided by ten for a batch. Query-start cloning is deployment work; sibling-history clones are audit work.",
            "cross_variant_warm_states_required_equal": False,
            "provider_scope": "Each execution arm and query has an independent provider. Already observed rows are not resampled within a history; actual repeated acquisition across alternative histories is physically counted.",
        },
        "history_policy_examples": [
            {"name": "spawn_all_queries", "case_name": "v6_spawn_edge_rescue_2", "sample_seed": 832101,
             "method": "online_mass_bound", "query_names": query_order},
            {"name": "crossing_risk_5", "case_name": "v6_crossing_rescue_pair_3", "sample_seed": 832102,
             "method": "online_mass_bound", "query_names": ["risk_5"]},
            {"name": "crossing_goal_pairs", "case_name": "v6_crossing_rescue_pair_2", "sample_seed": 832102,
             "method": "online_mass_bound", "query_names": [query for query in query_order if query in four_queries]},
        ],
        "legacy_v13_comparison": {
            "input_result": "controlled_predictive_execution_acquisition_v13.json",
            "stage_a_incremental_prefix_count": 96,
            "stage_b_incremental_query_tree_count": 960,
            "scope": "Read-only comparison with retained V13 records after all current V14 trees freeze; LEGACY is physically rebuilt and paid within V14; the posthoc comparison itself issues no sampling or execution calls. No timing equality is expected.",
        },
        "all_sixteen_declared_cases_retained": True,
        "new_board_discovery_performed": False, "boards_or_symmetries_changed": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "u006_assurance_started": False,
        "scope": "Previously exposed development inputs only. V14 tests one structural goal-unreachability bound, not new data, representation transfer, statistical confidence, or a formal scientific gate.",
    }


def freeze_cohort_roster_v14(path: str | Path, *, reports_dir: str | Path | None = None) -> dict[str, Any]:
    payload = build_cohort_roster_v14(reports_dir=reports_dir)
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return payload
