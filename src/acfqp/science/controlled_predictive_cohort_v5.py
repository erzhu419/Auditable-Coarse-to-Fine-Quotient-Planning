"""Fixed V5 starting boards and a pre-outcome, raw-board exposure audit.

This inventory reads only historical root metadata. It neither reconstructs
closures nor inspects optimal actions, rewards, sampled kernels, or arm results.
The deferred V2 candidate roster is not an exposed source and is not loaded.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, replace
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .controlled_predictive_2048_challenges_v2 import FAMILIES, _source_board
from .controlled_predictive_comparison_v3 import RefinementCase


DEVELOPMENT_SEEDS_V5 = (838101, 838201, 838301, 838401)
HISTORICAL_REPORTS = (
    "controlled_predictive_development_v1.json",
    "challenge_generator_discovery_v2.json",
    "controlled_predictive_refinement_v3.json",
    "controlled_predictive_comparison_v4.json",
    "controlled_predictive_sampling_diagnosis_v4.json",
)
DEFAULT_REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"


def historical_report_roots(name: str, payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Extract the five existing report schemas' root fields, not witness boards."""
    groups: list[tuple[str, list[Mapping[str, Any]]]]
    if name == "controlled_predictive_development_v1.json":
        groups = [("public_development_boards_rank_encoding", [
            {"name": case_name, "board": board}
            for case_name, board in payload["public_development_boards_rank_encoding"].items()
        ])]
    elif name == "challenge_generator_discovery_v2.json":
        groups = [("records", payload["records"]), ("round2.records", payload["round2"]["records"])]
    elif name in ("controlled_predictive_refinement_v3.json", "controlled_predictive_comparison_v4.json"):
        groups = [("cases", [record["case"] for record in payload["cases"]])]
    elif name == "controlled_predictive_sampling_diagnosis_v4.json":
        groups = [
            (f"{section}.cases", [record["case"] for record in payload[section]["cases"]])
            for section in ("original_exposed_diagnosis", "nested_sampling_curve")
        ]
    else:
        raise ValueError(f"unsupported historical root report: {name}")
    return [{
        "source_report": name, "source_section": section,
        "case_name": record["name"], "board": tuple(record["board"]),
    } for section, records in groups for record in records]


def exposed_root_registry(reports_dir: str | Path | None = None) -> tuple[dict[str, Any], ...]:
    directory = Path(reports_dir) if reports_dir is not None else DEFAULT_REPORTS_DIR
    return tuple(root for name in HISTORICAL_REPORTS
                 for root in historical_report_roots(name, json.loads((directory / name).read_text())))


def declared_cases_v5() -> tuple[RefinementCase, ...]:
    """Generate all 14 declared inputs without outcome-dependent replacements."""
    exposed = tuple(RefinementCase(
        f"v3_{family}_{seed}", f"v3_{family}_{seed}", "EXPOSED_V4_ERROR_ROOT",
        _source_board(family, seed), family, seed, 3,
    ) for family, seed in (("cross_axis_pairs", 835401), ("gradient_bottleneck", 835402)))
    candidates = tuple(RefinementCase(
        f"v5_{family}_{seed + index}", f"v5_{family}_{seed + index}",
        "NEW_ROOT_DEVELOPMENT_V5", _source_board(family, seed + index), family, seed + index, 3,
    ) for index, family in enumerate(FAMILIES) for seed in DEVELOPMENT_SEEDS_V5)
    return (*exposed, *candidates)


def audit_roster_v5(cases: Sequence[RefinementCase], history: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Retain repeated generation units and identify their actual root exposure."""
    by_board: dict[tuple[int, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for record in history:
        by_board[tuple(record["board"])].append(record)
    within: dict[tuple[int, ...], list[str]] = defaultdict(list)
    for case in cases:
        within[tuple(case.board)].append(case.name)
    registered = []
    for case in cases:
        matches = by_board.get(tuple(case.board), [])
        split = ("EXPOSED_ROOT_REUSE" if matches and case.split == "NEW_ROOT_DEVELOPMENT_V5"
                 else case.split)
        registered.append({
            "case": asdict(replace(case, split=split)),
            "declared_split": case.split,
            "historical_root_matches": [{key: value for key, value in match.items() if key != "board"}
                                        for match in matches],
            "within_roster_other_case_names": [name for name in within[tuple(case.board)] if name != case.name],
        })
    new_cases = [case for case in cases if case.split == "NEW_ROOT_DEVELOPMENT_V5"]
    repeated = [{"board": list(board), "case_names": names}
                for board, names in within.items() if len(names) > 1]
    return {
        "schema": "controlled_predictive_cohort_roster_v5",
        "status": "REGISTERED_BEFORE_V5_QUERY_AND_SAMPLE_OUTCOMES",
        "v5_query_and_sample_outcomes_evaluated": False,
        "historical_sources": list(dict.fromkeys(record["source_report"] for record in history)),
        "historical_root_record_count": len(history),
        "historical_unique_root_board_count": len(by_board),
        "historical_root_records_by_source": dict(Counter(record["source_report"] for record in history)),
        "declared_case_count": len(cases), "unique_root_board_count": len(within),
        "new_seed_case_count": len(new_cases),
        "new_seed_cases_reusing_exposed_roots": sum(tuple(case.board) in by_board for case in new_cases),
        "unique_new_roots_absent_from_historical_root_inventory": len({tuple(case.board) for case in new_cases} - by_board.keys()),
        "registered_split_counts": dict(Counter(record["case"]["split"] for record in registered)),
        "duplicate_root_groups": repeated, "cases": registered,
        "all_declared_cases_retained": True,
        "original_deferred_24_case_cohort_executed": False,
        "scope": "Raw starting-board equality, excluding horizon, against the five enumerated historical development reports. This does not audit descendant-state overlap, establish unseen states, or establish independent samples. Repeated generator outputs stay in the declared denominator.",
    }


def build_cohort_roster_v5(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    return audit_roster_v5(declared_cases_v5(), exposed_root_registry(reports_dir))


def cases_v5(*, reports_dir: str | Path | None = None) -> tuple[RefinementCase, ...]:
    roster = build_cohort_roster_v5(reports_dir=reports_dir)
    return tuple(RefinementCase(**{**record["case"], "board": tuple(record["case"]["board"])})
                 for record in roster["cases"])
