#!/usr/bin/env python3
"""Write retained V181r3 preimages after the commitment commit."""

from pathlib import Path

from acfqp import construction_k7_open_world_manifest_reveals_v181r3 as reveals


def main() -> None:
    value = reveals.freeze_open_world_manifest_reveals_v181r3()
    path = (
        Path(__file__).resolve().parents[1]
        / ".tmp"
        / "exact-freeze"
        / "v181r3_open_world_manifest_reveals.json"
    )
    with path.open("xb") as stream:
        if stream.write(value.canonical_bytes) != len(value.canonical_bytes):
            raise RuntimeError("V181r3 reveal short write")


if __name__ == "__main__":
    main()
