#!/usr/bin/env python3
"""Independently replay and freeze the one-shot V180r7 occurrence."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from acfqp import construction_k7_full_ground_fallback_production_terminal_independent_verifier_v180r7 as verifier
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".tmp" / "exact-freeze"
OUTPUT_ROOT = BASE / "v180r7_full_ground_fallback_output"
TERMINAL = BASE / "v180r7_full_ground_fallback_terminal_bundle.json"
VERIFICATION = BASE / "v180r7_full_ground_fallback_verification.json"
FAILURE = BASE / "v180r7_full_ground_fallback_failure.json"


def _write_once(path: Path, raw: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o400,
    )
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V180r7 verification short write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main() -> None:
    if FAILURE.exists():
        raise RuntimeError("V180r7 occurrence failed; verification is forbidden")
    if not TERMINAL.is_file() or not OUTPUT_ROOT.is_dir():
        raise RuntimeError("V180r7 successful occurrence is incomplete")
    if VERIFICATION.exists():
        raise RuntimeError("V180r7 verification already exists")
    terminal_bytes = TERMINAL.read_bytes()
    frozen = verifier.freeze_full_ground_fallback_verification_v180r7(
        terminal_bytes,
        OUTPUT_ROOT,
    )
    _write_once(VERIFICATION, frozen.canonical_bytes)
    print(
        canonical_json_bytes(
            {
                "terminal_bundle_id": frozen.to_document()[
                    "production_terminal_bundle_id"
                ],
                "terminal_byte_count": len(terminal_bytes),
                "terminal_sha256": hashlib.sha256(terminal_bytes).hexdigest(),
                "verification_id": frozen.verification_id,
                "verification_byte_count": len(frozen.canonical_bytes),
                "verification_sha256": hashlib.sha256(
                    frozen.canonical_bytes
                ).hexdigest(),
            }
        ).decode("utf-8"),
        flush=True,
    )


if __name__ == "__main__":
    main()
