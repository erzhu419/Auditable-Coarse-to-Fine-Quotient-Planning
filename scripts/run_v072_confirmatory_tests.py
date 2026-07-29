#!/usr/bin/env python3
"""Run the exact V0-072 pytest command in a private temporary directory."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Mapping


PARALLEL_WORKERS = 32
INNER_TEST_ARGV = (
    sys.executable,
    "scripts/run_pytest_parallel.py",
    "-j",
    str(PARALLEL_WORKERS),
    "--fresh-ids",
    "--no-timing-cache",
    "tests",
)
DETERMINISTIC_SETTINGS = (
    ("LC_ALL", "C.UTF-8"),
    ("PYTHONDONTWRITEBYTECODE", "1"),
    ("PYTHONHASHSEED", "0"),
)
TEMPORARY_VARIABLES = (
    "TMPDIR",
    "TMP",
    "TEMP",
    "ACFQP_PARALLEL_TEMP_ROOT",
)


def build_confirmatory_environment_v1(
    inherited: Mapping[str, str],
    private_temp_root: str | os.PathLike[str],
) -> dict[str, str]:
    """Overwrite host temp variables; the random path is runtime-only."""

    if not isinstance(inherited, Mapping) or any(
        type(key) is not str or type(value) is not str
        for key, value in inherited.items()
    ):
        raise ValueError("inherited environment is not string-to-string")
    private = Path(private_temp_root)
    try:
        canonical_private = private.resolve(strict=True)
    except FileNotFoundError as error:
        raise ValueError(
            "private temp root is not an absolute real directory"
        ) from error
    if (
        not private.is_absolute()
        or not private.is_dir()
        or private.is_symlink()
        or canonical_private != private
    ):
        raise ValueError("private temp root is not an absolute real directory")
    environment = dict(inherited)
    environment.update(DETERMINISTIC_SETTINGS)
    for name in TEMPORARY_VARIABLES:
        environment[name] = str(private)
    return environment


def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    base = repository_root / ".tmp" / "v072-confirmatory-pytest"
    if base.is_symlink():
        raise SystemExit("private pytest temp base must not be a symlink")
    base.mkdir(parents=True, exist_ok=True)
    resolved_base = base.resolve(strict=True)
    if resolved_base != base or resolved_base.parent.parent != repository_root:
        raise SystemExit("private pytest temp base escaped the repository")
    private = Path(
        tempfile.mkdtemp(
            prefix="execution-",
            dir=resolved_base,
        )
    ).resolve(strict=True)
    if private.parent != resolved_base or private.is_symlink():
        raise SystemExit("private pytest temp root escaped its frozen base")
    try:
        environment = build_confirmatory_environment_v1(
            os.environ,
            private,
        )
        completed = subprocess.run(
            INNER_TEST_ARGV,
            cwd=repository_root,
            env=environment,
            check=False,
        )
        return completed.returncode
    finally:
        shutil.rmtree(private)


if __name__ == "__main__":
    raise SystemExit(main())
