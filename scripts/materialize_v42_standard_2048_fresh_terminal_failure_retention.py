#!/usr/bin/env python3
"""Copy the fixed V42 ordinal-1 failure into its additive V42r1 retention."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from acfqp.construction_k7_standard_2048_fresh_terminal_failure_retention_v42r1 import (  # noqa: E402
    DEFAULT_RETENTION_ROOT_RELATIVE,
    materialize_v42_ordinal1_failure_retention,
)
from acfqp.phase3e_ids import canonical_json_bytes  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=str(ROOT))
    parser.add_argument(
        "--retention-root",
        default=str(ROOT / DEFAULT_RETENTION_ROOT_RELATIVE),
    )
    arguments = parser.parse_args()
    manifest = materialize_v42_ordinal1_failure_retention(
        repository_root=Path(arguments.repository_root).resolve(),
        retention_root=Path(arguments.retention_root).resolve(),
    )
    sys.stdout.buffer.write(canonical_json_bytes(manifest))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
