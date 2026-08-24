"""Outcome-free authorization for retained V180r10 V36 finish-forward."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as protocol
from acfqp import construction_k7_all_path_v36_resource_successor_authorization_v180r10 as predecessor_authorization
from acfqp import construction_k7_all_path_v36_resource_successor_failure_freeze_v180r10 as predecessor_failure
from acfqp import construction_k7_domain_registry_extension_v180r10r1 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_AUTHORIZATION_ID = "e53492926bc900ccd64ed27456eca45e1c5b087c7995a122d47b80e432064ad3"
EXPECTED_CANONICAL_BYTE_COUNT = 10_595
EXPECTED_CANONICAL_SHA256 = "ef650c4097b27b60dc2fe389c1d8cf0b7aed424976a7b6c4673d34191eaaced8"
MAXIMUM_RETAINED_REPLAY_PROCESSES = 1
MAXIMUM_RETAINED_REPLAY_WORKING_BYTES = 24 * 1024 * 1024 * 1024

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v180r10r1.py",
    "src/acfqp/construction_k7_all_path_v36_resource_successor_failure_freeze_v180r10.py",
    "src/acfqp/construction_k7_v36_retained_campaign_reconstructor_v180r10r1.py",
    "src/acfqp/construction_k7_v36_retained_recovery_terminal_v180r10r1.py",
    "src/acfqp/construction_k7_v36_retained_recovery_independent_verifier_v180r10r1.py",
    "src/acfqp/construction_k7_all_path_production_execution_protocol_v180r3.py",
    "src/acfqp/construction_k7_standard_2048_adaptive_expression_preregistration_v35.py",
    "src/acfqp/construction_k7_standard_2048_adaptive_expression_independent_verifier_v35.py",
    "src/acfqp/construction_k7_standard_2048_adaptive_accounting_preregistration_v36.py",
    "src/acfqp/construction_k7_standard_2048_adaptive_accounted_independent_verifier_v36.py",
    "src/acfqp/construction_accounting_registry_v9.py",
    "src/acfqp/accounting_v1.py",
    "src/acfqp/actual_accounting_v1.py",
    "src/acfqp/phase3e_ids.py",
    "scripts/run_v180r10r1_v36_retained_recovery.py",
)


def _fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = (root / relative_path).read_bytes()
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_v36_retained_recovery_authorization_v180r10r1() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    frozen_failure = predecessor_failure.load_frozen_v36_resource_successor_failure_v180r10()
    slots = [
        row
        for row in protocol.freeze_all_path_production_execution_protocol_v180r3()
        .to_document()["production_execution_slots"]
        if row["terminal_code"] == "LOCAL_GROUND_RECOVERY"
    ]
    if len(slots) != 1:
        raise ValueError("V180r10r1 local-recovery slot changed")
    payload = {
        "schema": "acfqp.v36_retained_recovery_authorization.v180r10r1",
        "production_execution_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
        "production_execution_slot": slots[0],
        "original_v180r10_execution_authorization_id": predecessor_authorization.EXPECTED_AUTHORIZATION_ID,
        "preserved_v180r10_failure_id": frozen_failure.failure_id,
        "preserved_v180r10_failure_sha256": predecessor_failure.EXPECTED_CANONICAL_SHA256,
        "preserved_complete_output_facts": list(frozen_failure.output_facts),
        "same_failed_authorization_rerun": False,
        "scientific_occurrence_rerun_forbidden": True,
        "retained_actual_occurrence_finish_forward_only": True,
        "successor_reason": "V36_TERMINAL_LIFT_FIELD_AND_LANE_PROJECTION_MISMATCH",
        "source_field": "operational_target_probability_label_query_count",
        "repaired_terminal_predicate": "positive_local_ground_distinction_count",
        "retained_operational_lane_literal": "OPERATIONAL",
        "scientific_contract_changed": False,
        "algorithm_changed": False,
        "worker_resource_schedule_changed": False,
        "retained_source_output_root_relative_path": ".tmp/exact-freeze/v180r10_v36_resource_successor_output",
        "source_facts": [_fact(root, path) for path in _SOURCE_PATHS],
        "entrypoint": (
            "acfqp.construction_k7_v36_retained_recovery_terminal_v180r10r1:"
            "finish_forward_retained_v36_occurrence_v180r10r1"
        ),
        "runner_relative_path": "scripts/run_v180r10r1_v36_retained_recovery.py",
        "terminal_output_relative_path": ".tmp/exact-freeze/v180r10r1_v36_retained_terminal.json",
        "verification_output_relative_path": ".tmp/exact-freeze/v180r10r1_v36_retained_verification.json",
        "failure_output_relative_path": ".tmp/exact-freeze/v180r10r1_v36_retained_failure.json",
        "all_successor_output_paths_must_be_absent": True,
        "same_authorization_rerun_after_any_progress_forbidden": True,
        "recovery_execution_started": False,
        "new_scientific_outcome_accessed": False,
        "actual_worker_process_count": 0,
        "maximum_retained_replay_processes": MAXIMUM_RETAINED_REPLAY_PROCESSES,
        "maximum_retained_replay_working_bytes": MAXIMUM_RETAINED_REPLAY_WORKING_BYTES,
        "producer_free_replay_required": True,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "v36_retained_recovery_authorization_id": domains.extension_content_id_v180r10r1(
            domains.CONSTRUCTION_K7_V36_RETAINED_RECOVERY_AUTHORIZATION_V180R10R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V36RetainedRecoveryAuthorizationV180r10r1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    authorization_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V180r10r1 authorization is not canonical")
        return document


@lru_cache(maxsize=1)
def freeze_v36_retained_recovery_authorization_v180r10r1() -> V36RetainedRecoveryAuthorizationV180r10r1:
    document = build_v36_retained_recovery_authorization_v180r10r1()
    raw = canonical_json_bytes(document)
    if EXPECTED_AUTHORIZATION_ID != "0" * 64 and not (
        document["v36_retained_recovery_authorization_id"] == EXPECTED_AUTHORIZATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r10r1 recovery authorization changed")
    return V36RetainedRecoveryAuthorizationV180r10r1(
        _ISSUER,
        raw,
        document["v36_retained_recovery_authorization_id"],
    )


__all__ = (
    "EXPECTED_AUTHORIZATION_ID",
    "build_v36_retained_recovery_authorization_v180r10r1",
    "freeze_v36_retained_recovery_authorization_v180r10r1",
)
