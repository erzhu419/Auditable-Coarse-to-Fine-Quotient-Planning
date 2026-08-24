#!/usr/bin/env python3
"""Execute and independently verify the V180r12r1 aggregation once."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import resource

from acfqp import construction_k7_domain_registry_extension_v180r12r1 as domains
from acfqp import construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r1 as authorization
from acfqp import construction_k7_ten_terminal_aggregation_finalizer_v180r12r1 as finalizer
from acfqp import construction_k7_ten_terminal_aggregation_independent_verifier_v180r12r1 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / ".tmp/exact-freeze/v180r12r1_ten_terminal_aggregation"
TERMINAL = OUTPUT_ROOT / "TERMINAL.json"
VERIFICATION = OUTPUT_ROOT / "VERIFICATION.json"
FAILURE = OUTPUT_ROOT / "FAILURE.json"


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
                raise OSError("V180r12r1 output short write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _failure(error: BaseException, authorization_id: str) -> None:
    payload = {
        "schema": "acfqp.ten_terminal_aggregation_failure.v180r12r1",
        "execution_authorization_id": authorization_id,
        "failure_type": type(error).__name__,
        "failure_message": str(error),
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
        "failure_id": domains.extension_content_id_v180r12r1(
            domains.CONSTRUCTION_K7_FAILURE_V180R12R1_DOMAIN,
            payload,
        ),
    }
    _write_once(FAILURE, canonical_json_bytes(document))


def main() -> None:
    if OUTPUT_ROOT.exists():
        raise RuntimeError("V180r12r1 aggregation already has progress")
    frozen = authorization.freeze_ten_terminal_aggregation_execution_authorization_v180r12r1()
    OUTPUT_ROOT.mkdir(mode=0o700, parents=False, exist_ok=False)
    old_soft, old_hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = authorization.WORKING_BYTES_HARD_CAP
    if old_hard != resource.RLIM_INFINITY and old_hard < cap:
        raise RuntimeError("V180r12r1 address-space hard limit is below the frozen cap")
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    try:
        terminal = finalizer.freeze_ten_terminal_aggregation_v180r12r1(ROOT)
        _write_once(TERMINAL, terminal.canonical_bytes)
        verification = verifier.verify_ten_terminal_aggregation_independently_v180r12r1(
            terminal.canonical_bytes,
            ROOT,
        )
        verification_bytes = canonical_json_bytes(verification)
        _write_once(VERIFICATION, verification_bytes)
    except BaseException as error:
        if not FAILURE.exists():
            _failure(error, frozen.authorization_id)
        raise
    document = loads_canonical_json(terminal.canonical_bytes)
    print(
        canonical_json_bytes(
            {
                "execution_authorization_id": frozen.authorization_id,
                "production_aggregation_bundle_id": document[
                    "production_aggregation_bundle_id"
                ],
                "terminal_byte_count": len(terminal.canonical_bytes),
                "terminal_sha256": hashlib.sha256(
                    terminal.canonical_bytes
                ).hexdigest(),
                "verification_id": verification["verification_id"],
                "verification_byte_count": len(verification_bytes),
                "verification_sha256": hashlib.sha256(
                    verification_bytes
                ).hexdigest(),
            }
        ).decode("utf-8"),
        flush=True,
    )


if __name__ == "__main__":
    main()
