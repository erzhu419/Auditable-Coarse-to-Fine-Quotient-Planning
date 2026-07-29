#!/usr/bin/env python3
"""Deterministically write or check the two V0-072 environment specs."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile

from acfqp import v072_execution_environment_authority_v1 as authority


def _replace_regular_file(path: Path, data: bytes) -> None:
    if path.is_symlink():
        raise SystemExit(f"refusing to replace symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _expected(root: Path) -> tuple[tuple[Path, bytes], ...]:
    return (
        (
            root / authority.TEST_COMMAND_SPEC_PATH,
            authority.render_expected_confirmatory_test_command_spec_v1(
                root
            ),
        ),
        (
            root / authority.RUNTIME_LOCK_SPEC_PATH,
            authority.render_expected_runtime_dependency_lock_spec_v1(
                root
            ),
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write",
        action="store_true",
        help="atomically replace both specs with current deterministic bytes",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="fail unless both checked-in specs equal current derived bytes",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    expected = _expected(root)
    if args.write:
        for path, data in expected:
            _replace_regular_file(path, data)
        print("V0-072 execution-environment specs regenerated")
        return 0

    stale = [
        path.relative_to(root).as_posix()
        for path, data in expected
        if path.is_symlink()
        or not path.is_file()
        or path.read_bytes() != data
    ]
    if stale:
        print("stale V0-072 execution-environment specs:")
        for path in stale:
            print(path)
        return 1
    print("V0-072 execution-environment specs match current tree/runtime")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
