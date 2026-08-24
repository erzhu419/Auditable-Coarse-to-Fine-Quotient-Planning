#!/usr/bin/env python3
"""Write the final V181r3 runner freeze before target outcome execution."""

from pathlib import Path

from acfqp import construction_k7_open_world_execution_preregistration_v181r3 as prereg


def main() -> None:
    value = prereg.freeze_open_world_execution_preregistration_v181r3()
    path = (
        Path(__file__).resolve().parents[1]
        / ".tmp"
        / "exact-freeze"
        / "v181r3_open_world_execution_preregistration.json"
    )
    with path.open("xb") as stream:
        if stream.write(value.canonical_bytes) != len(value.canonical_bytes):
            raise RuntimeError("V181r3 execution preregistration short write")


if __name__ == "__main__":
    main()
