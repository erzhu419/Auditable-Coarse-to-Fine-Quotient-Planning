#!/usr/bin/env python3
"""Independently replay and freeze the one-shot V180r7r1 occurrence."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat

from acfqp import (
    construction_k7_domain_registry_extension_v180r7r1 as domains,
    construction_k7_full_ground_fallback_execution_authorization_evidence_freeze_v180r7r1
    as authorization_evidence,
    construction_k7_full_ground_fallback_production_terminal_independent_verifier_v180r7r1
    as verifier,
)
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".tmp" / "exact-freeze"
OUTPUT_ROOT = BASE / "v180r7r1_full_ground_fallback_output"
TERMINAL = BASE / "v180r7r1_full_ground_fallback_terminal_bundle.json"
VERIFICATION = BASE / "v180r7r1_full_ground_fallback_verification.json"
FAILURE = BASE / "v180r7r1_full_ground_fallback_failure.json"
VERIFICATION_FAILURE = (
    BASE / "v180r7r1_full_ground_fallback_verification_failure.json"
)


def _freeze_authorization_boundary() -> None:
    freeze_evidence = getattr(
        authorization_evidence,
        (
            "freeze_full_ground_fallback_execution_authorization_"
            "evidence_v180r7r1"
        ),
    )
    frozen = freeze_evidence()
    document = frozen.to_document()
    if not (
        frozen.authorization_evidence_id
        == authorization_evidence.EXPECTED_AUTHORIZATION_EVIDENCE_ID
        and frozen.authorization_id
        == authorization_evidence.EXPECTED_AUTHORIZATION_ID
        and document.get("production_outcome_accessed") is False
        and document.get("fresh_production_occurrence_count") == 0
        and document.get("outcome_free") is True
        and document.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and document.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and document.get("SCALAR_CALIBRATION_GATE") == "NOT_RUN"
        and document.get("BREAK_EVEN_GATE") == "NOT_RUN"
        and document.get("official_scalar_cost") is None
        and document.get("official_N_break_even") is None
        and document.get("official_execution_allowed") is False
    ):
        raise RuntimeError("V180r7r1 authorization evidence boundary changed")


def _write_once(path: Path, raw: bytes) -> None:
    directory = _open_directory_symlink_free(path.parent)
    try:
        descriptor = os.open(
            path.name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_CLOEXEC
            | getattr(os, "O_NOFOLLOW", 0),
            0o400,
            dir_fd=directory,
        )
        try:
            view = memoryview(raw)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("V180r7r1 verification short write")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.fsync(directory)
    finally:
        os.close(directory)


def _open_directory_symlink_free(path: Path) -> int:
    absolute = Path(os.path.abspath(os.fspath(path)))
    flags = (
        os.O_RDONLY
        | os.O_CLOEXEC
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open("/", flags)
    try:
        for part in absolute.parts[1:]:
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise RuntimeError(
                "V180r7r1 path contains a symlink or nondirectory"
            )
        return descriptor
    except (OSError, ValueError) as error:
        os.close(descriptor)
        raise RuntimeError(
            "V180r7r1 path contains a symlink or nondirectory"
        ) from error


def _read_symlink_free(path: Path) -> bytes:
    absolute = Path(os.path.abspath(os.fspath(path)))
    directory = _open_directory_symlink_free(absolute.parent)
    try:
        descriptor = os.open(
            absolute.name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory,
        )
    except OSError as error:
        os.close(directory)
        raise RuntimeError(
            "V180r7r1 retained terminal path contains a symlink"
        ) from error
    finally:
        if "descriptor" in locals():
            os.close(directory)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError("V180r7r1 retained terminal is not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        if (
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
             before.st_ctime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                after.st_ctime_ns)
            or len(raw) != after.st_size
        ):
            raise RuntimeError(
                "V180r7r1 retained terminal changed during stable read"
            )
        return raw
    finally:
        os.close(descriptor)


def _write_verification_failure(
    error: BaseException, terminal_bytes: bytes | None
) -> None:
    from acfqp import (  # noqa: PLC0415
        construction_k7_full_ground_fallback_execution_authorization_v180r7r1
        as authorization,
    )

    payload = {
        "schema": "acfqp.full_ground_fallback_verification_failure.v180r7r1",
        "fallback_execution_authorization_id": (
            authorization.EXPECTED_AUTHORIZATION_ID
        ),
        "production_terminal_byte_count": (
            len(terminal_bytes) if terminal_bytes is not None else None
        ),
        "production_terminal_sha256": (
            hashlib.sha256(terminal_bytes).hexdigest()
            if terminal_bytes is not None
            else None
        ),
        "failure_type": type(error).__name__,
        "failure_message": str(error)[-4_096:],
        "verification_output_created": os.path.lexists(VERIFICATION),
        "same_verification_identity_rerun_forbidden": True,
        "success_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    document = {
        **payload,
        "verification_failure_id": domains.extension_content_id_v180r7r1(
            domains.CONSTRUCTION_K7_FALLBACK_VERIFICATION_FAILURE_V180R7R1_DOMAIN,
            payload,
        ),
    }
    _write_once(VERIFICATION_FAILURE, canonical_json_bytes(document))


def main() -> None:
    _freeze_authorization_boundary()
    if os.path.lexists(FAILURE):
        raise RuntimeError("V180r7r1 occurrence failed; verification is forbidden")
    if os.path.lexists(VERIFICATION_FAILURE):
        raise RuntimeError("V180r7r1 verification already failed; rerun is forbidden")
    if not os.path.lexists(TERMINAL) or not os.path.lexists(OUTPUT_ROOT):
        raise RuntimeError("V180r7r1 successful occurrence is incomplete")
    if os.path.lexists(VERIFICATION):
        raise RuntimeError("V180r7r1 verification already exists")
    terminal_bytes: bytes | None = None
    try:
        terminal_bytes = _read_symlink_free(TERMINAL)
        frozen = verifier.freeze_full_ground_fallback_verification_v180r7r1(
            terminal_bytes,
            OUTPUT_ROOT,
        )
        _write_once(VERIFICATION, frozen.canonical_bytes)
    except BaseException as error:
        _write_verification_failure(error, terminal_bytes)
        raise
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
