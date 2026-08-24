#!/usr/bin/env python3
"""Execute the preregistered V180r8 cached-exact occurrence once."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
from typing import Any

from acfqp import construction_k7_all_path_cached_execution_authorization_v180r8 as authorization
from acfqp import construction_k7_cached_exact_infeasibility_production_terminal_finalizer_v180r8 as finalizer
from acfqp import construction_k7_domain_registry_extension_v180r8 as domains
from acfqp import phase3e_exact_infeasibility_durable_proof_v1 as durable
from acfqp.phase3e_ids import canonical_json_bytes


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROOF_SOURCE_ROOT = REPOSITORY_ROOT / "artifacts" / "phase05" / "g2048"
OUTPUT_ROOT = REPOSITORY_ROOT / ".tmp" / "v180r8-cached-exact-production"
PROOF_PATH = OUTPUT_ROOT / "DURABLE_EXACT_PROOF.json"
TERMINAL_PATH = OUTPUT_ROOT / "TERMINAL.json"
FAILURE_PATH = OUTPUT_ROOT / "FAILURE.json"


def _write_once(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o400,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V180r8 exact write made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _failure_document(
    *, authorization_id: str, error: BaseException, proof_present: bool
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.cached_exact_infeasibility_execution_failure.v180r8",
        "cached_execution_authorization_id": authorization_id,
        "logical_occurrence_id": authorization.LOGICAL_OCCURRENCE_ID,
        "candidate_terminal_code": "CACHED_EXACT_INFEASIBLE",
        "failure_class": "TYPED_PROTOCOL_FAILURE_NONCERTIFICATE",
        "exception_type": type(error).__name__,
        "exception_message": str(error),
        "durable_proof_output_present": proof_present,
        "production_terminal_present": TERMINAL_PATH.exists(),
        "same_authorization_rerun_forbidden": True,
        "scientific_terminal_issued": False,
        "all_ten_paths_verified": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "cached_execution_failure_id": domains.extension_content_id_v180r8(
            domains.CONSTRUCTION_K7_CACHED_EXECUTION_FAILURE_V180R8_DOMAIN,
            payload,
        ),
    }


def main() -> None:
    frozen = authorization.freeze_cached_execution_authorization_v180r8()
    if OUTPUT_ROOT.exists():
        raise SystemExit(
            "V180r8 output root already exists; same-authorization rerun is forbidden"
        )
    OUTPUT_ROOT.mkdir(mode=0o700, parents=False, exist_ok=False)
    try:
        proof_bytes = durable.issue_phase3e_exact_infeasibility_durable_proof_v1(
            PROOF_SOURCE_ROOT
        )
        if not (
            len(proof_bytes) == authorization.EXPECTED_DURABLE_PROOF_BYTE_COUNT
            and hashlib.sha256(proof_bytes).hexdigest()
            == authorization.EXPECTED_DURABLE_PROOF_SHA256
        ):
            raise RuntimeError("V180r8 pre-window durable proof bytes changed")
        _write_once(PROOF_PATH, proof_bytes)
        terminal = finalizer.run_cached_exact_infeasibility_production_occurrence_v180r8(
            PROOF_PATH
        )
        _write_once(TERMINAL_PATH, terminal.canonical_bytes)
    except BaseException as error:
        if not TERMINAL_PATH.exists() and not FAILURE_PATH.exists():
            failure = _failure_document(
                authorization_id=frozen.authorization_id,
                error=error,
                proof_present=PROOF_PATH.exists(),
            )
            _write_once(FAILURE_PATH, canonical_json_bytes(failure))
        raise
    print(
        canonical_json_bytes(
            {
                "authorization_id": frozen.authorization_id,
                "terminal_id": terminal.production_terminal_bundle_id,
                "terminal_byte_count": len(terminal.canonical_bytes),
                "terminal_sha256": hashlib.sha256(terminal.canonical_bytes).hexdigest(),
            }
        ).decode("utf-8")
    )


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        print(f"V180r8 failed: {type(error).__name__}: {error}", file=sys.stderr)
        raise
