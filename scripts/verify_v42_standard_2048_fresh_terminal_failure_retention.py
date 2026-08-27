#!/usr/bin/env python3
"""Fresh isolated bootstrap for the producer-free V42r1 verifier."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from acfqp.construction_k7_standard_2048_fresh_terminal_failure_retention_independent_verifier_v42r1 import (  # noqa: E402
    verify_v42_ordinal1_failure_retention_independently,
)
from acfqp.phase3e_ids import canonical_json_bytes  # noqa: E402


DEFAULT_RETENTION_ROOT = (
    ROOT / "retained_evidence/v42_standard_2048_fresh_terminal_ordinal1_failure"
)
_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | _O_DIRECTORY | _O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_once(path: Path, raw: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_CLOEXEC | _O_NOFOLLOW,
        0o400,
    )
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V42r1 verification publication made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_directory(path.parent)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=str(ROOT))
    parser.add_argument("--retention-root", default=str(DEFAULT_RETENTION_ROOT))
    parser.add_argument("--publish", action="store_true")
    arguments = parser.parse_args()
    repository_root = Path(arguments.repository_root).resolve()
    retention_root = Path(arguments.retention_root).resolve()
    verification = verify_v42_ordinal1_failure_retention_independently(
        repository_root=repository_root,
        retention_root=retention_root,
    )
    raw = canonical_json_bytes(verification)
    verification_path = retention_root / "INDEPENDENT_VERIFICATION.json"
    if arguments.publish and not verification_path.exists():
        _publish_once(verification_path, raw)
        verification = verify_v42_ordinal1_failure_retention_independently(
            repository_root=repository_root,
            retention_root=retention_root,
        )
        raw = canonical_json_bytes(verification)
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
