#!/usr/bin/env python3
"""Write the V181r3 outcome-free successor before any reveal query."""

from pathlib import Path

from acfqp import construction_k7_open_world_protocol_successor_v181r3 as protocol


def main() -> None:
    value = protocol.freeze_open_world_protocol_successor_v181r3()
    path = (
        Path(__file__).resolve().parents[1]
        / ".tmp"
        / "exact-freeze"
        / "v181r3_open_world_protocol_successor.json"
    )
    with path.open("xb") as stream:
        if stream.write(value.canonical_bytes) != len(value.canonical_bytes):
            raise RuntimeError("V181r3 successor short write")


if __name__ == "__main__":
    main()
