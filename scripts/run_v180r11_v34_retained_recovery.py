#!/usr/bin/env python3
"""Execute the V180r11 retained V34 finish-forward exactly once."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from acfqp import construction_k7_domain_registry_extension_v180r11 as domains
from acfqp import construction_k7_v34_retained_recovery_authorization_v180r11 as authorization
from acfqp import construction_k7_v34_retained_recovery_independent_verifier_v180r11 as verifier
from acfqp import construction_k7_v34_retained_recovery_terminal_v180r11 as producer
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
EXACT_ROOT = ROOT / ".tmp" / "exact-freeze"
SOURCE_ROOT = EXACT_ROOT / "v180r5_v34_production_output"
TERMINAL_PATH = EXACT_ROOT / "v180r11_v34_retained_terminal.json"
VERIFICATION_PATH = EXACT_ROOT / "v180r11_v34_retained_verification.json"
FAILURE_PATH = EXACT_ROOT / "v180r11_v34_retained_failure.json"


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
                raise OSError("V180r11 output short write")
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
    frozen = authorization.freeze_v34_retained_recovery_authorization_v180r11()
    if any(path.exists() for path in (TERMINAL_PATH, VERIFICATION_PATH, FAILURE_PATH)):
        raise RuntimeError("V180r11 authorization already has progress or terminal")
    try:
        terminal = producer.finish_forward_retained_v34_occurrence_v180r11(
            SOURCE_ROOT,
            recovery_authorization_id=frozen.authorization_id,
        )
        _write_once(TERMINAL_PATH, terminal.canonical_bytes)
        verification = verifier.verify_v34_retained_recovery_bytes_independently_v180r11(
            terminal.canonical_bytes,
            SOURCE_ROOT,
            recovery_authorization_id=frozen.authorization_id,
        )
        verification_bytes = canonical_json_bytes(verification)
        _write_once(VERIFICATION_PATH, verification_bytes)
    except BaseException as error:
        if not FAILURE_PATH.exists():
            payload = {
                "schema": "acfqp.v34_retained_recovery_failure.v180r11",
                "v34_retained_recovery_authorization_id": frozen.authorization_id,
                "terminal_output_present": TERMINAL_PATH.is_file(),
                "verification_output_present": VERIFICATION_PATH.is_file(),
                "failure_type": type(error).__name__,
                "failure_message": str(error),
                "same_identity_rerun_forbidden": True,
                "scientific_success_claimed": False,
                "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
                "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
                "official_execution_allowed": False,
            }
            failure = {
                **payload,
                "failure_id": domains.extension_content_id_v180r11(
                    domains.CONSTRUCTION_K7_V34_RETAINED_FAILURE_V180R11_DOMAIN,
                    payload,
                ),
            }
            _write_once(FAILURE_PATH, canonical_json_bytes(failure))
        raise
    print(
        canonical_json_bytes(
            {
                "v34_retained_recovery_authorization_id": frozen.authorization_id,
                "v34_retained_terminal_id": terminal.terminal_id,
                "terminal_byte_count": len(terminal.canonical_bytes),
                "terminal_sha256": hashlib.sha256(
                    terminal.canonical_bytes
                ).hexdigest(),
                "verification_id": verification["verification_id"],
                "verification_byte_count": len(verification_bytes),
                "verification_sha256": hashlib.sha256(
                    verification_bytes
                ).hexdigest(),
                "scientific_occurrence_rerun": False,
            }
        ).decode("utf-8")
    )


if __name__ == "__main__":
    main()
