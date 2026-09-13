"""V9 target-adaptation scope over the unchanged frozen V8 inputs and splits."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR, V7Case


V8_ROSTER = "controlled_predictive_cohort_roster_v8.json"


def cases_v9(*, reports_dir: str | Path | None = None) -> tuple[V7Case, ...]:
    """Read the fixed source roster, excluding all experiment outcome reports."""
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    source = json.loads((directory / V8_ROSTER).read_text(encoding="utf-8"))
    return tuple(V7Case(**(record["case"] | {"board": tuple(record["case"]["board"])}))
                 for record in source["cases"])


def build_cohort_roster_v9(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    source = json.loads((directory / V8_ROSTER).read_text(encoding="utf-8"))
    return {
        "schema": "controlled_predictive_cohort_roster_v9",
        "status": "REGISTERED_BEFORE_V9_SOURCE_FITS_TARGET_ADAPTATION_AND_OUTCOMES",
        "v9_source_fits_target_adaptation_or_outcomes_evaluated": False,
        "source_roster": V8_ROSTER,
        "case_count": source["case_count"],
        "cases": source["cases"],
        "scenario_count": source["scenario_count"],
        "scenario_case_evaluation_count": source["scenario_case_evaluation_count"],
        "scenarios": source["scenarios"],
        "historical_exposure": source["historical_exposure"],
        "source_fit_roles_and_scenarios_unchanged": True,
        "evaluation_target_data_adaptation_permitted": True,
        "split_label_scope": (
            "TRAIN, VALIDATION_DIAGNOSTIC, FIT_HELD_OUT_DEVELOPMENT, EXPOSED_REGRESSION "
            "and FAMILY_HELD_OUT retain their V8 source encoder fit meanings. Evaluation "
            "target data may be used by the declared V9 adaptation procedure; these labels "
            "do not indicate that target data are excluded from adaptation."
        ),
        "all_sixteen_declared_cases_retained_in_primary": True,
        "new_board_discovery_performed": False,
        "boards_or_symmetries_changed": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "target_empirical_kernels_used_for_model_compilation": True,
        "scope": (
            "All sixteen boards, horizons, metadata records, source assignments and evaluation "
            "assignments are copied from the frozen V8 roster. PRIMARY retains sixteen cases "
            "and three sources; each of the three LOFO scenarios retains six evaluation cases "
            "and two sources. Every root and family was already exposed during research. "
            "V9 permits target-data adaptation while preserving the source-fit split; it does "
            "not create unseen research roots, new mechanism families or a source-only transfer claim."
        ),
    }


def freeze_cohort_roster_v9(path: str | Path, *, reports_dir: str | Path | None = None) -> dict[str, Any]:
    payload = build_cohort_roster_v9(reports_dir=reports_dir)
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return payload
