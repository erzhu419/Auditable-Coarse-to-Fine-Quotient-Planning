"""Fixed V7 fitting roles for the already exposed V6 roots and H2 regression."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from .controlled_predictive_comparison_v3 import refinement_cases


DEFAULT_REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"
V6_ROSTER = "controlled_predictive_cohort_roster_v6.json"


@dataclass(frozen=True)
class V7Case:
    name: str
    group: str
    family: str
    variant: str
    board: tuple[int, ...]
    horizon: int
    role: str
    split: str
    source: str


def cases_v7(*, reports_dir: str | Path | None = None) -> tuple[V7Case, ...]:
    """Read frozen input metadata; fit roles depend only on declared variant index."""
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    v6 = json.loads((directory / V6_ROSTER).read_text(encoding="utf-8"))
    cases = []
    for record in v6["cases"]:
        source = record["case"]
        if source["role"] == "EXPOSED_PUBLIC_CONTROL":
            role = "EXPOSED_REGRESSION"
        else:
            index = int(source["name"].rsplit("_", 1)[1])
            role = ("TRAIN" if index == 0 else "VALIDATION_DIAGNOSTIC" if index == 1
                    else "FIT_HELD_OUT_DEVELOPMENT")
        cases.append(V7Case(
            name=source["name"], group=source["group"], family=source["family"],
            variant=source["variant"], board=tuple(source["board"]),
            horizon=source["horizon"], role=role, split=role, source=V6_ROSTER,
        ))
    h2 = refinement_cases()[0]
    cases.append(V7Case(
        name=h2.name, group=h2.group, family=h2.family, variant="exposed_h2_decision_point",
        board=h2.board, horizon=h2.horizon, role="EXPOSED_REGRESSION",
        split="EXPOSED_REGRESSION", source="controlled_predictive_comparison_v3.refinement_cases()[0]",
    ))
    return tuple(cases)


def build_cohort_roster_v7(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    cases = cases_v7(reports_dir=reports_dir)
    return {
        "schema": "controlled_predictive_cohort_roster_v7",
        "status": "REGISTERED_BEFORE_V7_ENCODER_FIT_AND_OUTCOMES",
        "encoder_fitted_or_v7_outcomes_evaluated": False,
        "declared_case_count": len(cases),
        "unique_raw_root_board_count": len({case.board for case in cases}),
        "role_counts": dict(Counter(case.role for case in cases)),
        "historical_exposure": "ALL_ROOTS_PREVIOUSLY_EXPOSED_IN_DEVELOPMENT",
        "fit_split_rule": (
            "Each of the three fixed V6 mechanism families uses variant index 0 for TRAIN, "
            "index 1 for VALIDATION_DIAGNOSTIC, and indices 2 and 3 for FIT_HELD_OUT_DEVELOPMENT. "
            "The three V1 public controls and the existing H2 decision point are EXPOSED_REGRESSION."
        ),
        "validation_used_for_model_selection": False,
        "cases": [{"case": asdict(case), "historical_exposure": "PREVIOUSLY_EXPOSED"}
                  for case in cases],
        "all_declared_cases_retained": True,
        "new_board_discovery_performed": False,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "scope": (
            "Fitting roles describe this encoder fit only. Every root and its previous result "
            "were already exposed during research. Family variants are not independent mechanism "
            "sources; root separation does not establish descendant-state separation."
        ),
    }


def freeze_cohort_roster_v7(path: str | Path, *, reports_dir: str | Path | None = None) -> dict[str, Any]:
    payload = build_cohort_roster_v7(reports_dir=reports_dir)
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return payload
