"""V12 partial target acquisition roster copied from the fixed V11 inputs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR, V7Case

V11_ROSTER = "controlled_predictive_cohort_roster_v11.json"


def cases_v12(*, reports_dir: str | Path | None = None) -> tuple[V7Case, ...]:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    source = json.loads((directory / V11_ROSTER).read_text(encoding="utf-8"))
    return tuple(V7Case(**(record["case"] | {"board": tuple(record["case"]["board"])}))
                 for record in source["cases"])


def build_cohort_roster_v12(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    source = json.loads((directory / V11_ROSTER).read_text(encoding="utf-8"))
    return {
        "schema": "controlled_predictive_cohort_roster_v12",
        "status": "REGISTERED_BEFORE_V12_SOURCE_FITS_PARTIAL_ACQUISITION_AND_OUTCOMES",
        "v12_source_fits_partial_acquisition_or_outcomes_evaluated": False,
        "source_roster": V11_ROSTER,
        "case_count": source["case_count"], "cases": source["cases"],
        "scenario_count": source["scenario_count"],
        "scenario_case_evaluation_count": source["scenario_case_evaluation_count"],
        "scenarios": source["scenarios"],
        "historical_exposure": source["historical_exposure"],
        "split_label_scope": source["split_label_scope"],
        "source_fit_roles_and_scenarios_unchanged": True,
        "evaluation_target_data_adaptation_permitted": True,
        "samples_per_acquired_row": 256,
        "sample_seeds": source["sample_seeds"],
        "row_budgets": [8, 32, 128], "budgets_are_nested": True,
        "queries": source["queries"],
        "query_roles": {name: "CONSTRUCTION_AND_EVALUATION" for name in source["queries"]},
        "probe_or_query_holdout_roles": [],
        "partial_arms": ["bfs", "query_interval", "source_priority", "shuffled_source_priority"],
        "full_row_benchmark_arms": ["full_state_empirical", "exact_empirical_quotient"],
        "source_priority_scope": (
            "Source empirical Q values only break exact ties in upper-bound actions or "
            "reach-times-gap frontier priority. They never fill target transition rows or values. "
            "The shuffled source control rotates each code's sorted-action Q vector once."
        ),
        "all_sixteen_declared_cases_retained_in_primary": True,
        "new_board_discovery_performed": False,
        "boards_or_symmetries_changed": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "scope": (
            "All roots, horizons, source assignments and scenario evaluation assignments remain "
            "unchanged. All ten numeric queries now participate in construction; historical query "
            "names are retained as identifiers and no query has a probe role. The three nested "
            "budgets count acquired target action rows, each with 256 observations. Source fitting "
            "uses only declared source data; source and fallback work are separate charged costs."
        ),
    }


def freeze_cohort_roster_v12(path: str | Path, *, reports_dir: str | Path | None = None) -> dict[str, Any]:
    payload = build_cohort_roster_v12(reports_dir=reports_dir)
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return payload
