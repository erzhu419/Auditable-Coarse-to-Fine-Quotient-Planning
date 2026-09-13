"""Frozen V13 roster: unchanged V12 inputs, source-free execution experiments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR, V7Case


V12_ROSTER = "controlled_predictive_cohort_roster_v12.json"


def cases_v13(*, reports_dir: str | Path | None = None) -> tuple[V7Case, ...]:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    source = json.loads((directory / V12_ROSTER).read_text(encoding="utf-8"))
    return tuple(V7Case(**(record["case"] | {"board": tuple(record["case"]["board"])}))
                 for record in source["cases"])


def build_cohort_roster_v13(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    source = json.loads((directory / V12_ROSTER).read_text(encoding="utf-8"))
    primary = next(scenario for scenario in source["scenarios"] if scenario["name"] == "PRIMARY_V7_SPLIT")
    query_order = list(source["queries"])
    case_seed_count = source["case_count"] * len(source["sample_seeds"])
    return {
        "schema": "controlled_predictive_cohort_roster_v13",
        "status": "REGISTERED_BEFORE_V13_TARGET_ACQUISITION_EXECUTION_AND_OUTCOMES",
        "v13_target_acquisition_execution_or_outcomes_evaluated": False,
        "input_roster": V12_ROSTER,
        "case_count": source["case_count"], "cases": source["cases"],
        "sample_seeds": source["sample_seeds"],
        "case_seed_count": case_seed_count,
        "queries": source["queries"], "initial_query_order": query_order,
        "query_execution_context_count": case_seed_count * len(query_order),
        "query_execution_count_scope": "Each execution arm is evaluated on all 16 cases x 3 seeds x 10 query contexts.",
        "query_roles": {name: "CONSTRUCTION_AND_EVALUATION" for name in query_order},
        "probe_or_query_holdout_roles": [],
        "historical_exposure": source["historical_exposure"],
        "scenario_count": 1,
        "scenario_case_evaluation_count": source["case_count"],
        "scenarios": [primary | {"source_case_names": []}],
        "historical_primary_case_splits": primary["case_splits"],
        "split_label_scope": "Original PRIMARY split and family labels are retained as historical metadata; no source representation is fitted or used in V13.",
        "lofo_scenarios_reexecuted": False,
        "source_fitting_enabled": False, "source_priority_enabled": False,
        "source_fees": 0,
        "samples_per_acquired_row": 256,
        "row_stream": {
            "version": "V12_UNCHANGED",
            "key": "(remaining_horizon, tuple(board_ranks))",
            "action_order": ["DOWN", "LEFT", "RIGHT", "UP"],
            "integer_seed": "seed*(12**16*16)+(h*4+action_index)*12**16+sum(rank*12**i)",
            "sampling": "random.Random(integer_seed).choices(requested_row_support, weights, k=256)",
            "cross_method_prewarming": False,
        },
        "initial_shared_row_cap": 32,
        "total_episode_row_cap": 128,
        "initial_acquisition_mode": "query_interval",
        "single_active_query_for_upfront_and_online": True,
        "online_per_decision_quota": "(128 - observed_rows) // remaining_horizon",
        "online_quota_scope": "At each ACTIVE decision; stop acquiring earlier when the current query interval closes. Terminal states require no decision quota.",
        "stage_a": {
            "scope": "Separate V12-equivalent multi-query interval update comparison.",
            "acquisition_mode": "query_interval",
            "update_modes": ["full_recompute", "incremental"],
            "row_checkpoints": [32, 128],
            "query_order": query_order,
            "exact_equivalence_fields": ["requested_row_order", "observed_rows", "profiles", "L", "U", "QL", "QU", "all_declared_query_policies"],
        },
        "stage_b": {
            "execution_arms": ["upfront_full", "upfront_incremental", "online_full", "online_incremental"],
            "reference_arms": ["frozen32", "full_state_empirical", "exact_empirical_quotient"],
            "upfront_acquisition": "After the initial multi-query prefix, the active query alone may acquire until its root interval closes or the total row cap is reached.",
            "online_acquisition": "After the initial multi-query prefix, the active query acquires at each actual decision under the declared per-decision quota and remaining episode row cap.",
            "branch_history": "Each true successor branch has an independent cloned planner, observation history and remaining budget; probabilities combine audit outcomes only.",
            "prefix_accounting": "Initial prefixes are physically rebuilt and charged; Stage A does not provide free prewarming for Stage B. Any actual prefix sharing and amortization are reported explicitly.",
        },
        "all_sixteen_declared_cases_retained": True,
        "new_board_discovery_performed": False,
        "boards_or_symmetries_changed": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "u006_assurance_started": False,
        "scope": "Previously exposed development inputs only. V13 changes update scheduling and execution-time acquisition; it does not change roots, horizons, query coefficients, row streams, or the original failed scientific gate.",
    }


def freeze_cohort_roster_v13(path: str | Path, *, reports_dir: str | Path | None = None) -> dict[str, Any]:
    payload = build_cohort_roster_v13(reports_dir=reports_dir)
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return payload
