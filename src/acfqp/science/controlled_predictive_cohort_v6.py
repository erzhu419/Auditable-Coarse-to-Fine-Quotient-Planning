"""Pre-outcome V6 root exposure and mechanism-family inventory.

Only declared starting boards and historical report root fields are inspected.
No closure is reconstructed and no action, value, or sample outcome is used.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .controlled_predictive_challenges_v6 import V6Case, declared_cases_v6
from .controlled_predictive_cohort_v5 import DEFAULT_REPORTS_DIR, exposed_root_registry


V5_REPORT = "controlled_predictive_comparison_v5.json"


def board_symmetries(board: Sequence[int]) -> dict[str, tuple[int, ...]]:
    """Return the eight square-board symmetries, including the unchanged board."""
    original = tuple(board)
    if len(original) != 16:
        raise ValueError("V6 exposure inventory requires 4 by 4 starting boards")

    def rotate(value: tuple[int, ...]) -> tuple[int, ...]:
        return tuple(value[(3 - column) * 4 + row] for row in range(4) for column in range(4))

    result = {"identity": original}
    current = original
    for degrees in (90, 180, 270):
        current = rotate(current)
        result[f"rotate_{degrees}"] = current
    current = tuple(original[row * 4 + 3 - column] for row in range(4) for column in range(4))
    result["reflect_vertical"] = current
    for degrees in (90, 180, 270):
        current = rotate(current)
        result[f"reflect_vertical_rotate_{degrees}"] = current
    return result


def v5_report_roots(payload: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Read only V5's declared root metadata, excluding witnesses and results."""
    return tuple({
        "source_report": V5_REPORT,
        "source_section": "cases",
        "case_name": record["case"]["name"],
        "board": tuple(record["case"]["board"]),
    } for record in payload["cases"])


def exposed_root_registry_v6(reports_dir: str | Path | None = None) -> tuple[dict[str, Any], ...]:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    return (*exposed_root_registry(directory),
            *v5_report_roots(json.loads((directory / V5_REPORT).read_text())))


def _unique_boards(boards: Sequence[tuple[int, ...]], *, up_to_symmetry: bool = False) -> list[tuple[int, ...]]:
    representatives: list[tuple[int, ...]] = []
    for board in boards:
        equivalent = tuple(board_symmetries(board).values()) if up_to_symmetry else (board,)
        if not any(previous in equivalent for previous in representatives):
            representatives.append(board)
    return representatives


def audit_roster_v6(cases: Sequence[V6Case], history: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Label all declared cases without replacing repeated or exposed boards."""
    historical_boards = [tuple(record["board"]) for record in history]
    current_boards = [tuple(case.board) for case in cases]
    registered = []
    for case in cases:
        transformations = board_symmetries(case.board)
        raw_matches = []
        symmetry_matches = []
        for record in history:
            target = tuple(record["board"])
            matches = [name for name, board in transformations.items() if board == target]
            if not matches:
                continue
            match = {key: value for key, value in record.items() if key != "board"}
            match["transforms_of_current_board_matching_historical_board"] = matches
            (raw_matches if target == tuple(case.board) else symmetry_matches).append(match)
        exposure = ("EXPOSED_ROOT_REUSE" if raw_matches else
                    "EXPOSED_SYMMETRY_REUSE" if symmetry_matches else
                    "NEW_ROOT_DEVELOPMENT_V6")
        within_raw = []
        within_symmetry = []
        for other in cases:
            if other.name == case.name:
                continue
            matches = [name for name, board in transformations.items() if board == tuple(other.board)]
            if matches:
                match = {"case_name": other.name, "group": other.group,
                         "transforms_of_current_board_matching_other_board": matches}
                (within_raw if tuple(other.board) == tuple(case.board) else within_symmetry).append(match)
        registered.append({
            "case": asdict(case), "exposure": exposure,
            "historical_raw_root_matches": raw_matches,
            "historical_symmetry_root_matches": symmetry_matches,
            "within_roster_raw_root_matches": within_raw,
            "within_roster_symmetry_root_matches": within_symmetry,
        })
    family_groups = [{
        "family": family,
        "generation_groups": list(dict.fromkeys(case.group for case in cases if case.family == family)),
        "case_names": [case.name for case in cases if case.family == family],
        "variants": [case.variant for case in cases if case.family == family],
        "roles": list(dict.fromkeys(case.role for case in cases if case.family == family)),
        "variants_are_independent_replicates": False,
    } for family in dict.fromkeys(case.family for case in cases)]
    new_boards = [tuple(record["case"]["board"]) for record in registered
                  if record["exposure"] == "NEW_ROOT_DEVELOPMENT_V6"]
    return {
        "schema": "controlled_predictive_cohort_roster_v6",
        "status": "REGISTERED_BEFORE_V6_CHARACTERIZATION_AND_SAMPLE_OUTCOMES",
        "v6_characterization_and_sample_outcomes_evaluated": False,
        "historical_sources": list(dict.fromkeys(record["source_report"] for record in history)),
        "historical_root_record_count": len(history),
        "historical_unique_raw_root_board_count": len(_unique_boards(historical_boards)),
        "historical_unique_root_symmetry_orbit_count": len(_unique_boards(historical_boards, up_to_symmetry=True)),
        "historical_root_records_by_source": dict(Counter(record["source_report"] for record in history)),
        "declared_case_count": len(cases),
        "unique_raw_root_board_count": len(_unique_boards(current_boards)),
        "unique_root_symmetry_orbit_count": len(_unique_boards(current_boards, up_to_symmetry=True)),
        "unique_new_root_symmetry_orbit_count": len(_unique_boards(new_boards, up_to_symmetry=True)),
        "registered_exposure_counts": dict(Counter(record["exposure"] for record in registered)),
        "role_counts": dict(Counter(case.role for case in cases)),
        "generation_group_count": len(dict.fromkeys(case.group for case in cases)),
        "family_group_count": len(family_groups),
        "family_groups": family_groups,
        "cases": registered,
        "all_declared_cases_retained": True,
        "original_deferred_24_case_cohort_loaded_or_executed": False,
        "scope": (
            "Starting-board equality, excluding horizon, and all eight rotations/reflections against the six "
            "enumerated historical development reports and within the declared V6 roster. Mechanism variants "
            "within a family and symmetric roots are not independent replicates. This root-only inventory "
            "does not audit descendant-state overlap or establish unseen states. All declared cases remain "
            "in the roster regardless of exposure or later outcomes."
        ),
    }


def build_cohort_roster_v6(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    return audit_roster_v6(declared_cases_v6(), exposed_root_registry_v6(reports_dir))


def cases_v6() -> tuple[V6Case, ...]:
    """Return the declared inputs; exposure labels are separate roster metadata."""
    return declared_cases_v6()
