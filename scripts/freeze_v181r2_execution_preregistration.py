#!/usr/bin/env python3
"""Write the final V181r2 runner/source freeze before target queries."""

from __future__ import annotations

from pathlib import Path

from acfqp import construction_k7_open_world_execution_preregistration_v181r2 as prereg


def main() -> None:
    value = prereg.freeze_open_world_execution_preregistration_v181r2()
    path = (
        Path(__file__).resolve().parents[1]
        / ".tmp"
        / "exact-freeze"
        / "v181r2_open_world_execution_preregistration.json"
    )
    with path.open("xb") as stream:
        if stream.write(value.canonical_bytes) != len(value.canonical_bytes):
            raise RuntimeError("V181r2 execution preregistration short write")


if __name__ == "__main__":
    main()
