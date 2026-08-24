"""Outcome-free V36 successor authorization after the frozen V180r6 failure."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_all_path_v36_execution_authorization_v180r6 as predecessor_authorization
from acfqp import construction_k7_all_path_v36_failure_freeze_v180r6 as failed
from acfqp import construction_k7_domain_registry_extension_v180r10 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_AUTHORIZATION_ID = "3fbf12ce574fff0038cf8cd1190a08c9831314a47f8fd02f0aa04c5e9429e95f"
EXPECTED_CANONICAL_BYTE_COUNT = 7_402
EXPECTED_CANONICAL_SHA256 = "784f2b77f4dfa740a69bf8ebaeb665fd1abfe88a79ce3d9395a910aea7718269"

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v180r10.py",
    "src/acfqp/construction_k7_all_path_v36_execution_authorization_v180r6.py",
    "src/acfqp/construction_k7_all_path_v36_failure_freeze_v180r6.py",
    "src/acfqp/construction_k7_v36_local_recovery_production_terminal_finalizer_v180r6.py",
    "src/acfqp/construction_k7_v36_local_recovery_production_terminal_independent_verifier_v180r6.py",
    "src/acfqp/construction_k7_v36_local_recovery_resource_successor_independent_verifier_v180r10.py",
    "src/acfqp/construction_k7_all_path_production_execution_protocol_v180r3.py",
    "src/acfqp/construction_k7_standard_2048_adaptive_accounting_preregistration_v36.py",
    "src/acfqp/construction_accounting_registry_v9.py",
    "src/acfqp/phase3e_ids.py",
    "scripts/run_v180r10_v36_resource_successor_occurrence.py",
)


def _fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = (root / relative_path).read_bytes()
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_v36_resource_successor_authorization_v180r10() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    protocol_document = protocol.freeze_all_path_production_execution_protocol_v180r3().to_document()
    predecessor = predecessor_authorization.freeze_v36_execution_authorization_v180r6()
    frozen_failure = failed.load_frozen_v36_failure_v180r6()
    slots = [
        row
        for row in protocol_document["production_execution_slots"]
        if row["terminal_code"] == "LOCAL_GROUND_RECOVERY"
    ]
    if len(slots) != 1:
        raise ValueError("V180r10 local-recovery slot changed")
    payload = {
        "schema": "acfqp.v36_resource_successor_authorization.v180r10",
        "production_execution_protocol_id": protocol_document[
            "production_execution_protocol_id"
        ],
        "production_execution_slot": slots[0],
        "failed_predecessor_authorization_id": predecessor.authorization_id,
        "preserved_v180r6_failure_id": frozen_failure.failure_id,
        "preserved_v180r6_failure_sha256": failed.EXPECTED_CANONICAL_SHA256,
        "preserved_partial_output_facts": list(frozen_failure.partial_output_facts),
        "same_failed_authorization_rerun": False,
        "successor_reason": "BROKEN_PROCESS_POOL_AFTER_MODEL_STAGE",
        "scientific_contract_changed": False,
        "algorithm_changed": False,
        "worker_resource_schedule_changed": False,
        "maximum_worker_processes": 2,
        "maximum_tasks_per_worker_process": 1,
        "no_other_registered_full_campaign_may_run_concurrently": True,
        "source_facts": [_fact(root, path) for path in _SOURCE_PATHS],
        "entrypoint": (
            "acfqp.construction_k7_v36_local_recovery_production_terminal_finalizer_v180r6:"
            "run_v36_local_ground_recovery_production_occurrence_v180r6"
        ),
        "runner_relative_path": "scripts/run_v180r10_v36_resource_successor_occurrence.py",
        "output_root_relative_path": (
            ".tmp/exact-freeze/v180r10_v36_resource_successor_output"
        ),
        "terminal_output_relative_path": (
            ".tmp/exact-freeze/v180r10_v36_resource_successor_terminal.json"
        ),
        "verification_output_relative_path": (
            ".tmp/exact-freeze/v180r10_v36_resource_successor_verification.json"
        ),
        "failure_output_relative_path": (
            ".tmp/exact-freeze/v180r10_v36_resource_successor_failure.json"
        ),
        "all_output_paths_must_be_absent": True,
        "same_authorization_rerun_after_any_progress_forbidden": True,
        "fresh_successor_execution_started": False,
        "production_outcome_accessed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "v36_resource_successor_authorization_id": domains.extension_content_id_v180r10(
            domains.CONSTRUCTION_K7_V36_RESOURCE_SUCCESSOR_AUTHORIZATION_V180R10_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V36ResourceSuccessorAuthorizationV180r10:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    authorization_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V180r10 authorization is not canonical")
        return document


@lru_cache(maxsize=1)
def freeze_v36_resource_successor_authorization_v180r10() -> V36ResourceSuccessorAuthorizationV180r10:
    document = build_v36_resource_successor_authorization_v180r10()
    raw = canonical_json_bytes(document)
    if EXPECTED_AUTHORIZATION_ID != "0" * 64 and not (
        document["v36_resource_successor_authorization_id"]
        == EXPECTED_AUTHORIZATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r10 resource-successor authorization changed")
    return V36ResourceSuccessorAuthorizationV180r10(
        _ISSUER,
        raw,
        document["v36_resource_successor_authorization_id"],
    )


__all__ = (
    "EXPECTED_AUTHORIZATION_ID",
    "build_v36_resource_successor_authorization_v180r10",
    "freeze_v36_resource_successor_authorization_v180r10",
)
