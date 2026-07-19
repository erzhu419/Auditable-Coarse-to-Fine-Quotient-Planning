#!/usr/bin/env python3
"""Validate the frozen Laplace-semi-MDP Bellman-Kron regression artifact."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


INTEGER_FIELDS = {
    "n_states": 81,
    "n_boundary": 32,
    "n_interior": 49,
    "n_edges": 128,
    "signature_merge_group_count": 32,
}

DISCRETE_CSV_FIELDS = ("boundary_pos", "state", "coord", "char", "best_option")
NUMERIC_CSV_FIELDS = ("smdp_value", "primitive_value", "abs_gap")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _close(actual: float, expected: float, atol: float) -> bool:
    return math.isfinite(actual) and math.isclose(actual, expected, rel_tol=0.0, abs_tol=atol)


def validate(expected_dir: Path, actual_dir: Path) -> list[str]:
    failures: list[str] = []
    expected = _load_json(expected_dir / "summary.json")
    actual = _load_json(actual_dir / "summary.json")

    for field, required in INTEGER_FIELDS.items():
        if actual.get(field) != required:
            failures.append(f"{field}: expected {required!r}, got {actual.get(field)!r}")

    for field, required in (("gamma", 0.97), ("slip", 0.0)):
        try:
            observed = float(actual[field])
        except (KeyError, TypeError, ValueError):
            failures.append(f"{field}: missing or non-numeric")
        else:
            if not _close(observed, required, 1e-15):
                failures.append(f"{field}: expected {required}, got {observed}")

    errors = actual.get("bellman_preservation_max_error_by_option")
    if not isinstance(errors, dict) or set(errors) != {"N", "S", "W", "E"}:
        failures.append("bellman_preservation_max_error_by_option: expected N/S/W/E")
    else:
        for option, value in errors.items():
            try:
                observed = float(value)
            except (TypeError, ValueError):
                failures.append(f"Bellman error for {option}: non-numeric")
                continue
            if not math.isfinite(observed) or observed >= 1e-12:
                failures.append(f"Bellman error for {option}: {observed} is not < 1e-12")

    try:
        value_gap = float(actual["smdp_vs_primitive_value_max_abs_gap_on_boundaries"])
    except (KeyError, TypeError, ValueError):
        failures.append("smdp_vs_primitive_value_max_abs_gap_on_boundaries: missing or non-numeric")
    else:
        if not math.isfinite(value_gap) or value_gap >= 1e-10:
            failures.append(f"SMDP/primitive boundary value gap {value_gap} is not < 1e-10")

    for field in ("smdp_value_at_start_boundary_if_boundary", "primitive_value_at_start"):
        try:
            observed = float(actual[field])
            reference = float(expected[field])
        except (KeyError, TypeError, ValueError):
            failures.append(f"{field}: missing or non-numeric")
        else:
            if not _close(observed, reference, 1e-10):
                failures.append(f"{field}: expected {reference}, got {observed}")

    expected_rows = _load_csv(expected_dir / "boundary_values.csv")
    actual_rows = _load_csv(actual_dir / "boundary_values.csv")
    if len(actual_rows) != 32:
        failures.append(f"boundary_values.csv: expected 32 rows, got {len(actual_rows)}")
    if len(actual_rows) != len(expected_rows):
        return failures

    for row_index, (expected_row, actual_row) in enumerate(zip(expected_rows, actual_rows, strict=True)):
        for field in DISCRETE_CSV_FIELDS:
            if actual_row.get(field) != expected_row.get(field):
                failures.append(
                    f"boundary row {row_index} field {field}: "
                    f"expected {expected_row.get(field)!r}, got {actual_row.get(field)!r}"
                )
        for field in NUMERIC_CSV_FIELDS:
            try:
                observed = float(actual_row[field])
                reference = float(expected_row[field])
            except (KeyError, TypeError, ValueError):
                failures.append(f"boundary row {row_index} field {field}: missing or non-numeric")
                continue
            if not _close(observed, reference, 1e-10):
                failures.append(
                    f"boundary row {row_index} field {field}: expected {reference}, got {observed}"
                )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-dir",
        type=Path,
        default=Path("third_party/laplace_smdp_940598d/experiments/fixtures"),
    )
    parser.add_argument("--actual-dir", type=Path, required=True)
    args = parser.parse_args()

    failures = validate(args.expected_dir, args.actual_dir)
    if failures:
        print(json.dumps({"status": "FAIL", "failures": failures}, indent=2))
        return 1
    print(json.dumps({"status": "PASS", "actual_dir": str(args.actual_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
