"""Small source-binding and exclusive-output helpers for science execution."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess


class ScienceExecutionIOV1Error(RuntimeError):
    """A source checkout or output path is not eligible for execution."""


def require_path_outside_repository_v1(
    *, repository: Path, path: Path, label: str
) -> Path:
    repository = repository.resolve()
    resolved = path.resolve()
    if resolved == repository or repository in resolved.parents:
        raise ScienceExecutionIOV1Error(f"{label} must be outside the source checkout")
    return resolved


def bound_clean_source_commit_v1(repository: Path) -> str:
    """Return the actual commit only when the whole checkout is clean."""

    repository = repository.resolve()
    head = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--verify", "HEAD^{commit}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if len(head) != 40 or any(character not in "0123456789abcdef" for character in head):
        raise ScienceExecutionIOV1Error(
            "current source HEAD is not one lowercase full Git object ID"
        )
    if status:
        raise ScienceExecutionIOV1Error("science source checkout is not clean")
    return head


def write_exclusive_bytes_v1(path: Path, raw: bytes) -> None:
    if not isinstance(path, Path) or type(raw) is not bytes:
        raise ScienceExecutionIOV1Error("exclusive output input changed")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


__all__ = (
    "ScienceExecutionIOV1Error",
    "bound_clean_source_commit_v1",
    "require_path_outside_repository_v1",
    "write_exclusive_bytes_v1",
)
