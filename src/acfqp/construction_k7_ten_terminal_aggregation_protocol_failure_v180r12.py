"""Frozen non-execution failure for the misregistered V180r12 protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_cached_exact_infeasibility_production_terminal_independent_verifier_v180r8 as cached_verifier
from acfqp import construction_k7_domain_registry_extension_v180r12 as domains
from acfqp import construction_k7_ten_terminal_aggregation_protocol_v180r12 as predecessor
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_FAILURE_ID = "b8348c51c19db9238281a9a59e66bba911c9c9756e80c04a9cb3111e8515a604"
EXPECTED_CANONICAL_BYTE_COUNT = 2_465
EXPECTED_CANONICAL_SHA256 = "7c74af102aa1d111a99ad43d3a8dd73192b059f2bc685bceeeac194ff8a2bbe5"

V180R8_EVIDENCE_COMMIT = "6c884113eee1adbd90d0348140a50bca0b3b0f72"
V180R8_EVIDENCE_COMMIT_TIME = "2026-08-24T16:21:47+08:00"
V180R12_PROTOCOL_COMMIT = "9875392a7e7818505fbc0a19ef3336e8f1579f5d"
V180R12_PROTOCOL_COMMIT_TIME = "2026-08-24T19:38:11+08:00"


def build_ten_terminal_aggregation_protocol_failure_v180r12() -> dict[str, Any]:
    protocol = predecessor.freeze_ten_terminal_aggregation_protocol_v180r12()
    protocol_document = protocol.to_document()
    cached_row = next(
        row
        for row in protocol_document["terminal_sources"]
        if row["terminal_code"] == "CACHED_EXACT_INFEASIBLE"
    )
    payload = {
        "schema": "acfqp.ten_terminal_aggregation_protocol_failure.v180r12",
        "predecessor_protocol_id": protocol.aggregation_protocol_id,
        "predecessor_protocol_byte_count": len(protocol.canonical_bytes),
        "predecessor_protocol_sha256": hashlib.sha256(
            protocol.canonical_bytes
        ).hexdigest(),
        "failure_kind": "HISTORICAL_COMPLETION_STATUS_MISREGISTERED",
        "incorrect_terminal_code": "CACHED_EXACT_INFEASIBLE",
        "incorrect_source_row": cached_row,
        "recorded_status": "AUTHORIZED_NOT_STARTED",
        "correct_status": "COMPLETED_AND_INDEPENDENTLY_VERIFIED_BEFORE_PROTOCOL_FREEZE",
        "directory_checked_during_faulty_inventory": ".tmp/exact-freeze",
        "actual_terminal_relative_path": (
            ".tmp/v180r8-cached-exact-production/TERMINAL.json"
        ),
        "actual_verification_relative_path": (
            ".tmp/v180r8-cached-exact-verification/VERIFICATION.json"
        ),
        "retained_v180r8_evidence": {
            "terminal_bundle_id": cached_verifier.EXPECTED_TERMINAL_BUNDLE_ID,
            "terminal_byte_count": cached_verifier.EXPECTED_TERMINAL_BYTE_COUNT,
            "terminal_sha256": cached_verifier.EXPECTED_TERMINAL_SHA256,
            "verification_id": cached_verifier.EXPECTED_VERIFICATION_ID,
            "verification_byte_count": cached_verifier.EXPECTED_VERIFICATION_BYTE_COUNT,
            "verification_sha256": cached_verifier.EXPECTED_VERIFICATION_SHA256,
            "producer_free_replay_matches_retained_verification_bytes": True,
        },
        "chronology": {
            "v180r8_evidence_commit": V180R8_EVIDENCE_COMMIT,
            "v180r8_evidence_commit_time": V180R8_EVIDENCE_COMMIT_TIME,
            "v180r12_protocol_commit": V180R12_PROTOCOL_COMMIT,
            "v180r12_protocol_commit_time": V180R12_PROTOCOL_COMMIT_TIME,
            "v180r8_evidence_precedes_v180r12_protocol": True,
        },
        "predecessor_protocol_executed": False,
        "predecessor_execution_authorization_issued": False,
        "scientific_output_generated_under_predecessor_protocol": False,
        "predecessor_retained_without_relabeling": True,
        "fresh_successor_required": True,
        "all_ten_paths_verified": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "failure_id": domains.extension_content_id_v180r12(
            domains.CONSTRUCTION_K7_FAILURE_V180R12_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TenTerminalAggregationProtocolFailureV180R12:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    failure_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V180r12 failure is not canonical")
        return document


def freeze_ten_terminal_aggregation_protocol_failure_v180r12() -> (
    TenTerminalAggregationProtocolFailureV180R12
):
    document = build_ten_terminal_aggregation_protocol_failure_v180r12()
    raw = canonical_json_bytes(document)
    if EXPECTED_FAILURE_ID != "0" * 64 and not (
        document["failure_id"] == EXPECTED_FAILURE_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r12 frozen protocol failure changed")
    return TenTerminalAggregationProtocolFailureV180R12(
        _ISSUER,
        raw,
        document["failure_id"],
    )


__all__ = (
    "EXPECTED_FAILURE_ID",
    "build_ten_terminal_aggregation_protocol_failure_v180r12",
    "freeze_ten_terminal_aggregation_protocol_failure_v180r12",
)
