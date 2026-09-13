"""Frozen V8 encoder-fit scenarios over the unchanged, exposed V7 cohort."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from .controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR, V7Case


V7_ROSTER = "controlled_predictive_cohort_roster_v7.json"


def cases_v8(*, reports_dir: str | Path | None = None) -> tuple[V7Case, ...]:
    """Read all sixteen frozen V7 input records without outcomes or replacements."""
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    roster = json.loads((directory / V7_ROSTER).read_text(encoding="utf-8"))
    return tuple(V7Case(**(record["case"] | {"board": tuple(record["case"]["board"])}))
                 for record in roster["cases"])


def build_cohort_roster_v8(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    cases = cases_v8(reports_dir=reports_dir)
    sources = [case for case in cases if case.role == "TRAIN"]
    scenarios = [{
        "name": "PRIMARY_V7_SPLIT",
        "source_case_names": [case.name for case in sources],
        "evaluation_case_names": [case.name for case in cases],
        "target_family": None,
        "case_splits": {case.name: case.split for case in cases},
    }]
    for family in dict.fromkeys(case.family for case in sources):
        source_cases = [case for case in sources if case.family != family]
        target_cases = [case for case in cases if case.family == family]
        scenarios.append({
            "name": f"LOFO_{family}",
            "source_case_names": [case.name for case in source_cases],
            "evaluation_case_names": [case.name for case in (*source_cases, *target_cases)],
            "target_family": family,
            "case_splits": ({case.name: "TRAIN" for case in source_cases}
                            | {case.name: "FAMILY_HELD_OUT" for case in target_cases}),
        })
    return {
        "schema": "controlled_predictive_cohort_roster_v8",
        "status": "REGISTERED_BEFORE_V8_ENCODER_FITS_AND_OUTCOMES",
        "v8_encoders_fitted_or_outcomes_evaluated": False,
        "source_roster": V7_ROSTER,
        "case_count": len(cases),
        "cases": [{"case": asdict(case)} for case in cases],
        "scenario_count": len(scenarios),
        "scenario_case_evaluation_count": sum(len(item["evaluation_case_names"]) for item in scenarios),
        "scenarios": scenarios,
        "historical_exposure": "ALL_ROOTS_AND_FAMILIES_PREVIOUSLY_EXPOSED_IN_DEVELOPMENT",
        "all_sixteen_declared_cases_retained_in_primary": True,
        "all_three_mechanism_families_evaluated_as_encoder_fit_holdouts": True,
        "new_board_discovery_performed": False,
        "boards_or_symmetries_changed": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "target_empirical_kernels_used_for_model_compilation": True,
        "scope": (
            "PRIMARY_V7_SPLIT retains the original V7 fit roles. Each LOFO scenario fits only "
            "variant 0 of the other two mechanism families and evaluates those two sources plus "
            "all four variants of the withheld family. FAMILY_HELD_OUT denotes absence from this "
            "encoder fit; the roots and families were already exposed during research, and target "
            "empirical kernels remain available for compiled dynamics. All boards, orientations, "
            "horizons and source metadata are unchanged. No held-out outcome selects the roster."
        ),
    }


def freeze_cohort_roster_v8(path: str | Path, *, reports_dir: str | Path | None = None) -> dict[str, Any]:
    payload = build_cohort_roster_v8(reports_dir=reports_dir)
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return payload
