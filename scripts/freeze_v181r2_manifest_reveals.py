#!/usr/bin/env python3
"""Write retained V181r2 preimages after the commitment commit."""

from __future__ import annotations

from pathlib import Path

from acfqp import construction_k7_open_world_manifest_reveals_v181r2 as reveals


def main() -> None:
    value = reveals.freeze_open_world_manifest_reveals_v181r2()
    path = (
        Path(__file__).resolve().parents[1]
        / ".tmp"
        / "exact-freeze"
        / "v181r2_open_world_manifest_reveals.json"
    )
    with path.open("xb") as stream:
        if stream.write(value.canonical_bytes) != len(value.canonical_bytes):
            raise RuntimeError("V181r2 reveal short write")


if __name__ == "__main__":
    main()
