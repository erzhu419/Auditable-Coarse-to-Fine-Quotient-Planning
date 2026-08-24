#!/usr/bin/env python3
"""Run the preregistered V180r9 six-terminal occurrence once."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from acfqp import construction_k7_domain_registry_extension_v180r9 as domains
from acfqp import construction_k7_remaining_terminal_execution_authorization_v180r9 as authorization
from acfqp import construction_k7_remaining_terminal_independent_verifier_v180r9 as verifier
from acfqp import construction_k7_remaining_terminal_production_v180r9 as producer
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / ".tmp" / "exact-freeze" / "v180r9_remaining_terminal_production"
TERMINAL_PATH = OUTPUT_ROOT / "TERMINAL.json"
VERIFICATION_PATH = OUTPUT_ROOT / "VERIFICATION.json"
FAILURE_PATH = OUTPUT_ROOT / "FAILURE.json"


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
                raise OSError("V180r9 output short write")
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
    frozen = authorization.freeze_remaining_terminal_execution_authorization_v180r9()
    if OUTPUT_ROOT.exists():
        raise RuntimeError("V180r9 output root exists; same-identity rerun forbidden")
    OUTPUT_ROOT.mkdir(mode=0o700, parents=False, exist_ok=False)
    manifests = authorization.event_manifests_v180r9()
    try:
        terminal_bytes = producer.run_remaining_terminal_production_campaign_v180r9(
            manifests,
            execution_authorization_id=frozen.authorization_id,
        )
        _write_once(TERMINAL_PATH, terminal_bytes)
        verification = verifier.verify_remaining_terminal_campaign_independently_v180r9(
            terminal_bytes,
            execution_authorization_id=frozen.authorization_id,
            event_manifests=manifests,
        )
        verification_bytes = canonical_json_bytes(verification)
        _write_once(VERIFICATION_PATH, verification_bytes)
    except BaseException as error:
        if not FAILURE_PATH.exists():
            payload = {
                "schema": "acfqp.remaining_terminal_campaign_failure.v180r9",
                "execution_authorization_id": frozen.authorization_id,
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
                "failure_id": domains.extension_content_id_v180r9(
                    domains.CONSTRUCTION_K7_FAILURE_V180R9_DOMAIN,
                    payload,
                ),
            }
            _write_once(FAILURE_PATH, canonical_json_bytes(failure))
        raise
    print(
        canonical_json_bytes(
            {
                "execution_authorization_id": frozen.authorization_id,
                "production_campaign_bundle_id": (
                    loads_canonical_json(terminal_bytes)["production_campaign_bundle_id"]
                ),
                "terminal_byte_count": len(terminal_bytes),
                "terminal_sha256": hashlib.sha256(terminal_bytes).hexdigest(),
                "verification_id": verification["verification_id"],
                "verification_byte_count": len(verification_bytes),
                "verification_sha256": hashlib.sha256(verification_bytes).hexdigest(),
            }
        ).decode("utf-8")
    )


if __name__ == "__main__":
    main()
