"""Producer-free binding of a fresh V36 terminal to the V180r10 successor."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_all_path_v36_failure_freeze_v180r6 as failed
from acfqp import construction_k7_all_path_v36_resource_successor_authorization_v180r10 as authorization
from acfqp import construction_k7_domain_registry_extension_v180r10 as domains
from acfqp import construction_k7_v36_local_recovery_production_terminal_independent_verifier_v180r6 as underlying
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


class ConstructionK7V36ResourceSuccessorIndependentVerifierV180r10Error(
    RuntimeError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7V36ResourceSuccessorIndependentVerifierV180r10Error(
        message
    )


def verify_v36_resource_successor_independently_v180r10(
    terminal_bytes: bytes,
    output_root: Path,
) -> dict[str, Any]:
    if type(terminal_bytes) is not bytes:
        _fail("V180r10 terminal input is not exact bytes")
    terminal = loads_canonical_json(terminal_bytes)
    if type(terminal) is not dict or canonical_json_bytes(terminal) != terminal_bytes:
        _fail("V180r10 terminal input is not one canonical object")
    frozen_authorization = (
        authorization.freeze_v36_resource_successor_authorization_v180r10()
    )
    authorization_document = frozen_authorization.to_document()
    root = Path(__file__).resolve().parents[2]
    for fact in authorization_document["source_facts"]:
        raw = (root / fact["relative_path"]).read_bytes()
        if fact != {
            "relative_path": fact["relative_path"],
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }:
            _fail("V180r10 authorized source bytes changed")
    frozen_failure = failed.load_frozen_v36_failure_v180r6()
    replayed = underlying.verify_v36_production_terminal_independently_v180r6(
        terminal_bytes,
        output_root,
    )
    payload = {
        "schema": "acfqp.v36_resource_successor_verification.v180r10",
        "v36_resource_successor_authorization_id": frozen_authorization.authorization_id,
        "preserved_v180r6_failure_id": frozen_failure.failure_id,
        "same_failed_authorization_rerun": False,
        "production_terminal_bundle_id": terminal["production_terminal_bundle_id"],
        "production_terminal_byte_count": len(terminal_bytes),
        "production_terminal_sha256": hashlib.sha256(terminal_bytes).hexdigest(),
        "underlying_producer_free_verification": replayed,
        "fresh_resource_successor_execution_verified": True,
        "scientific_contract_changed": False,
        "algorithm_changed": False,
        "worker_resource_schedule_changed": False,
        "failed_predecessor_and_partial_outputs_preserved": True,
        "terminal_work_vector_reconstructed": replayed[
            "terminal_work_vector_reconstructed"
        ],
        "terminal_comparison_vector_rederived": replayed[
            "terminal_comparison_vector_rederived"
        ],
        "certificate_failure_then_local_recovery_verified": replayed[
            "certificate_failure_then_local_recovery_verified"
        ],
        "all_ten_paths_verified": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "verification_id": domains.extension_content_id_v180r10(
            domains.CONSTRUCTION_K7_V36_RESOURCE_SUCCESSOR_VERIFICATION_V180R10_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "ConstructionK7V36ResourceSuccessorIndependentVerifierV180r10Error",
    "verify_v36_resource_successor_independently_v180r10",
)
