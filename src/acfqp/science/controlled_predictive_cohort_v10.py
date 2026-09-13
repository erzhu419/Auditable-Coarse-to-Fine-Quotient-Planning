"""V10 paired runtime comparison over the unchanged V9 adaptation cohort."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from .controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR, V7Case
from .controlled_predictive_comparison_v3 import COMPARISON_QUERIES, PROBE_QUERIES


V9_ROSTER = "controlled_predictive_cohort_roster_v9.json"


def cases_v10(*, reports_dir: str | Path | None = None) -> tuple[V7Case, ...]:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    source = json.loads((directory / V9_ROSTER).read_text(encoding="utf-8"))
    return tuple(V7Case(**(record["case"] | {"board": tuple(record["case"]["board"])}))
                 for record in source["cases"])


def build_cohort_roster_v10(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    source = json.loads((directory / V9_ROSTER).read_text(encoding="utf-8"))
    return {
        "schema": "controlled_predictive_cohort_roster_v10",
        "status": "REGISTERED_BEFORE_V10_RUNTIME_COMPARISON_AND_OUTCOMES",
        "v10_runtime_comparison_or_outcomes_evaluated": False,
        "source_roster": V9_ROSTER,
        "case_count": source["case_count"],
        "cases": source["cases"],
        "scenario_count": source["scenario_count"],
        "scenario_case_evaluation_count": source["scenario_case_evaluation_count"],
        "scenarios": source["scenarios"],
        "historical_exposure": source["historical_exposure"],
        "source_fit_roles_and_scenarios_unchanged": True,
        "evaluation_target_data_adaptation_permitted": True,
        "split_label_scope": source["split_label_scope"],
        "comparison_scope": "RUNTIME_OPTIMIZATION_ONLY",
        "paired_runtime_implementations": ["V9_EAGER", "V10_LAZY"],
        "samples_per_action_row": 256,
        "sample_seeds": [832101, 832102, 832103],
        "queries": {name: asdict(query) for name, query in {**COMPARISON_QUERIES, **PROBE_QUERIES}.items()},
        "queries_changed": False,
        "all_sixteen_declared_cases_retained_in_primary": True,
        "new_board_discovery_performed": False,
        "boards_or_symmetries_changed": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "target_empirical_kernels_used_for_model_compilation": True,
        "scope": (
            "V10 pairs the V9 eager implementation and V10 lazy runtime over the same frozen "
            "sixteen roots, four source-fit scenarios and thirty-four scenario-case evaluations. "
            "The 256 observations per action row, three sampling seeds and ten numeric queries "
            "are unchanged. Existing labels describe source encoder fit only; current target "
            "data remain available for adaptation. This roster adds runtime comparison metadata "
            "without changing boards, orientations, horizons, source assignments or historical exposure."
        ),
    }


def freeze_cohort_roster_v10(path: str | Path, *, reports_dir: str | Path | None = None) -> dict[str, Any]:
    payload = build_cohort_roster_v10(reports_dir=reports_dir)
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return payload
