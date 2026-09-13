"""V11 fixed-feature-block runtime comparison on the unchanged V10 cohort."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR, V7Case


V10_ROSTER = "controlled_predictive_cohort_roster_v10.json"


def cases_v11(*, reports_dir: str | Path | None = None) -> tuple[V7Case, ...]:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    source = json.loads((directory / V10_ROSTER).read_text(encoding="utf-8"))
    return tuple(V7Case(**(record["case"] | {"board": tuple(record["case"]["board"])}))
                 for record in source["cases"])


def build_cohort_roster_v11(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    source = json.loads((directory / V10_ROSTER).read_text(encoding="utf-8"))
    return {
        "schema": "controlled_predictive_cohort_roster_v11",
        "status": "REGISTERED_BEFORE_V11_RUNTIME_COMPARISON_AND_OUTCOMES",
        "v11_runtime_comparison_or_outcomes_evaluated": False,
        "source_roster": V10_ROSTER,
        "case_count": source["case_count"], "cases": source["cases"],
        "scenario_count": source["scenario_count"],
        "scenario_case_evaluation_count": source["scenario_case_evaluation_count"],
        "scenarios": source["scenarios"],
        "historical_exposure": source["historical_exposure"],
        "source_fit_roles_and_scenarios_unchanged": True,
        "evaluation_target_data_adaptation_permitted": True,
        "split_label_scope": source["split_label_scope"],
        "comparison_scope": "RUNTIME_OPTIMIZATION_ONLY",
        "paired_runtime_implementations": ["V9_EAGER", "V11_FIXED_FEATURE_BLOCKS"],
        "feature_block_sizes": [7, 6, 6, 6, 6],
        "intermediate_storage_scope": "ACTIVE_STATE_ONLY_PER_STATE",
        "all_state_board_cache": False,
        "cross_state_cache": False,
        "global_cache": False,
        "samples_per_action_row": source["samples_per_action_row"],
        "sample_seeds": source["sample_seeds"],
        "queries": source["queries"], "queries_changed": False,
        "all_sixteen_declared_cases_retained_in_primary": True,
        "new_board_discovery_performed": False,
        "boards_or_symmetries_changed": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "target_empirical_kernels_used_for_model_compilation": True,
        "scope": (
            "The frozen V10 roots, horizons, source roles, evaluation assignments, observation "
            "budget, sampling seeds and ten queries are unchanged. V11 pairs the V9 eager "
            "implementation with fixed feature blocks: seven board features and six features "
            "for each of four actions. Intermediate feature and swipe results belong only to "
            "their active state; there is no all-state board inventory cache, cross-state cache "
            "or global cache. Source-fit labels still permit current target-data adaptation."
        ),
    }


def freeze_cohort_roster_v11(path: str | Path, *, reports_dir: str | Path | None = None) -> dict[str, Any]:
    payload = build_cohort_roster_v11(reports_dir=reports_dir)
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return payload
