#!/usr/bin/env python3
"""Execute the preregistered V180r10 resource successor exactly once."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from acfqp import construction_k7_all_path_v36_resource_successor_authorization_v180r10 as authorization
from acfqp import construction_k7_domain_registry_extension_v180r10 as domains
from acfqp import construction_k7_v36_local_recovery_production_terminal_finalizer_v180r6 as finalizer
from acfqp import construction_k7_v36_local_recovery_resource_successor_independent_verifier_v180r10 as verifier
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".tmp" / "exact-freeze"
OUTPUT_ROOT = BASE / "v180r10_v36_resource_successor_output"
TERMINAL = BASE / "v180r10_v36_resource_successor_terminal.json"
VERIFICATION = BASE / "v180r10_v36_resource_successor_verification.json"
FAILURE = BASE / "v180r10_v36_resource_successor_failure.json"


def _write_once(path: Path, raw: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o400)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V180r10 output short write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _write_failure(error: BaseException, authorization_id: str) -> None:
    payload = {
        "schema": "acfqp.v36_resource_successor_failure.v180r10",
        "v36_resource_successor_authorization_id": authorization_id,
        "failure_type": type(error).__name__,
        "failure_message": str(error),
        "output_root_created": OUTPUT_ROOT.exists(),
        "retained_output_file_count": (
            sum(path.is_file() for path in OUTPUT_ROOT.rglob("*"))
            if OUTPUT_ROOT.exists()
            else 0
        ),
        "terminal_output_present": TERMINAL.is_file(),
        "verification_output_present": VERIFICATION.is_file(),
        "same_authorization_rerun_forbidden": True,
        "success_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    document = {
        **payload,
        "failure_id": domains.extension_content_id_v180r10(
            domains.CONSTRUCTION_K7_V36_RESOURCE_SUCCESSOR_FAILURE_V180R10_DOMAIN,
            payload,
        ),
    }
    _write_once(FAILURE, canonical_json_bytes(document))


def main() -> None:
    if any(path.exists() for path in (OUTPUT_ROOT, TERMINAL, VERIFICATION, FAILURE)):
        raise RuntimeError("V180r10 resource-successor authorization already has progress")
    frozen = authorization.freeze_v36_resource_successor_authorization_v180r10()
    try:
        terminal = finalizer.run_v36_local_ground_recovery_production_occurrence_v180r6(
            OUTPUT_ROOT
        )
        _write_once(TERMINAL, terminal.canonical_bytes)
        verification = verifier.verify_v36_resource_successor_independently_v180r10(
            terminal.canonical_bytes,
            OUTPUT_ROOT,
        )
        verification_bytes = canonical_json_bytes(verification)
        _write_once(VERIFICATION, verification_bytes)
    except BaseException as error:
        if not FAILURE.exists():
            _write_failure(error, frozen.authorization_id)
        raise
    print(
        canonical_json_bytes(
            {
                "authorization_id": frozen.authorization_id,
                "terminal_bundle_id": terminal.production_terminal_bundle_id,
                "terminal_byte_count": len(terminal.canonical_bytes),
                "terminal_sha256": hashlib.sha256(terminal.canonical_bytes).hexdigest(),
                "verification_id": verification["verification_id"],
                "verification_byte_count": len(verification_bytes),
                "verification_sha256": hashlib.sha256(verification_bytes).hexdigest(),
            }
        ).decode("utf-8"),
        flush=True,
    )


if __name__ == "__main__":
    main()
