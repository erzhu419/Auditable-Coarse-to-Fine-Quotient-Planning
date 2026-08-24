"""Corrected outcome-free protocol for aggregating the ten V180 paths."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_all_path_cached_execution_authorization_v180r8 as cached
from acfqp import construction_k7_all_path_fallback_execution_authorization_v180r7 as fallback
from acfqp import construction_k7_all_path_formalization_contract_v180 as contract
from acfqp import construction_k7_all_path_v36_resource_successor_authorization_v180r10 as local
from acfqp import construction_k7_cached_exact_infeasibility_production_terminal_independent_verifier_v180r8 as cached_verifier
from acfqp import construction_k7_domain_registry_extension_v180r12r1 as domains
from acfqp import construction_k7_remaining_terminal_evidence_freeze_v180r9 as remaining
from acfqp import construction_k7_ten_terminal_aggregation_protocol_failure_v180r12 as predecessor_failure
from acfqp import construction_k7_v34_retained_recovery_authorization_v180r11 as abstract
from acfqp.accounting_v1 import RouteKindEnum
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


EXPECTED_PROTOCOL_ID = "54816ae5405c50eba7294d59da21c4b70e7486ccdf89956f3c5b9fcf4c6219fe"
EXPECTED_CANONICAL_BYTE_COUNT = 6_262
EXPECTED_CANONICAL_SHA256 = "414fc1100a6c6c04dc458f62b273cb870cd2099063eb2204ce8e496b69833bcc"

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v180r12r1.py",
    "src/acfqp/construction_k7_ten_terminal_aggregation_protocol_failure_v180r12.py",
    "src/acfqp/construction_k7_all_path_formalization_contract_v180.py",
    "src/acfqp/construction_k7_cached_exact_infeasibility_production_terminal_independent_verifier_v180r8.py",
    "src/acfqp/construction_accounting_registry_v9.py",
    "src/acfqp/accounting_v1.py",
    "src/acfqp/routing_v1.py",
    "src/acfqp/phase3e_ids.py",
)


def _fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = (root / relative_path).read_bytes()
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_ten_terminal_aggregation_protocol_v180r12r1() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    failure = (
        predecessor_failure.freeze_ten_terminal_aggregation_protocol_failure_v180r12()
    )
    terminal_sources = [
        {
            "terminal_code": TerminalCode.ABSTRACT_CERTIFIED.value,
            "source_kind": "V180R11_RETAINED_V34_FINISH_FORWARD",
            "source_authorization_id": abstract.EXPECTED_AUTHORIZATION_ID,
            "terminal_relative_path": ".tmp/exact-freeze/v180r11_v34_retained_terminal.json",
            "verification_relative_path": ".tmp/exact-freeze/v180r11_v34_retained_verification.json",
            "status_at_successor_freeze": "COMPLETED",
        },
        {
            "terminal_code": TerminalCode.LOCAL_GROUND_RECOVERY.value,
            "source_kind": "V180R10_FRESH_V36_RESOURCE_SUCCESSOR",
            "source_authorization_id": local.EXPECTED_AUTHORIZATION_ID,
            "terminal_relative_path": ".tmp/exact-freeze/v180r10_v36_resource_successor_terminal.json",
            "verification_relative_path": ".tmp/exact-freeze/v180r10_v36_resource_successor_verification.json",
            "status_at_successor_freeze": "AUTHORIZED_ACTIVE_NOT_CONSUMED",
        },
        {
            "terminal_code": TerminalCode.FULL_GROUND_FALLBACK.value,
            "source_kind": "V180R7_FRESH_FULL_GROUND_FALLBACK",
            "source_authorization_id": fallback.EXPECTED_AUTHORIZATION_ID,
            "terminal_relative_path": ".tmp/exact-freeze/v180r7_full_ground_fallback_terminal_bundle.json",
            "verification_relative_path": None,
            "status_at_successor_freeze": "AUTHORIZED_NOT_STARTED",
        },
        {
            "terminal_code": TerminalCode.CACHED_EXACT_INFEASIBLE.value,
            "source_kind": "V180R8_FRESH_CACHED_EXACT",
            "source_authorization_id": cached.EXPECTED_AUTHORIZATION_ID,
            "terminal_relative_path": ".tmp/v180r8-cached-exact-production/TERMINAL.json",
            "verification_relative_path": ".tmp/v180r8-cached-exact-verification/VERIFICATION.json",
            "terminal_bundle_id": cached_verifier.EXPECTED_TERMINAL_BUNDLE_ID,
            "terminal_byte_count": cached_verifier.EXPECTED_TERMINAL_BYTE_COUNT,
            "terminal_sha256": cached_verifier.EXPECTED_TERMINAL_SHA256,
            "verification_id": cached_verifier.EXPECTED_VERIFICATION_ID,
            "verification_byte_count": cached_verifier.EXPECTED_VERIFICATION_BYTE_COUNT,
            "verification_sha256": cached_verifier.EXPECTED_VERIFICATION_SHA256,
            "status_at_successor_freeze": "COMPLETED_AND_INDEPENDENTLY_VERIFIED",
        },
        {
            "terminal_code": "REMAINING_SIX_TERMINAL_CODES",
            "covered_terminal_codes": [
                TerminalCode.FULL_GROUND_EXACT_INFEASIBLE.value,
                TerminalCode.INTEGRITY_FAILURE.value,
                TerminalCode.PROTOCOL_FAILURE.value,
                TerminalCode.REBUILD_REQUIRED.value,
                TerminalCode.FALLBACK_CAP_EXHAUSTED.value,
                TerminalCode.ATTEMPT_BUDGET_EXHAUSTED.value,
            ],
            "source_kind": "V180R9_FRESH_SIX_TERMINAL_CAMPAIGN",
            "source_authorization_id": remaining.EXPECTED_EXECUTION_AUTHORIZATION_ID,
            "terminal_relative_path": ".tmp/exact-freeze/v180r9_remaining_terminal_production/TERMINAL.json",
            "verification_relative_path": ".tmp/exact-freeze/v180r9_remaining_terminal_production/VERIFICATION.json",
            "status_at_successor_freeze": "COMPLETED",
        },
    ]
    payload = {
        "schema": "acfqp.ten_terminal_aggregation_protocol.v180r12r1",
        "formalization_contract_id": contract.EXPECTED_CONTRACT_ID,
        "formalization_contract_exact_frozen_identity_used": True,
        "failed_v180r12_protocol_id": failure.to_document()[
            "predecessor_protocol_id"
        ],
        "preserved_v180r12_failure_id": failure.failure_id,
        "failed_predecessor_preserved_without_relabeling": True,
        "terminal_sources": terminal_sources,
        "ordered_terminal_codes": [row.value for row in TerminalCode],
        "terminal_code_count": len(TerminalCode),
        "ordered_route_kinds": [row.value for row in RouteKindEnum],
        "route_kind_count": len(RouteKindEnum),
        "completed_terminal_code_count_bound_at_successor_freeze": 8,
        "pending_terminal_codes_at_successor_freeze": [
            TerminalCode.LOCAL_GROUND_RECOVERY.value,
            TerminalCode.FULL_GROUND_FALLBACK.value,
        ],
        "completed_predecessor_outcome_bytes_accessed": True,
        "pending_outcome_bytes_accessed": False,
        "source_facts": [_fact(root, path) for path in _SOURCE_PATHS],
        "exact_terminal_and_verification_bytes_required": True,
        "every_source_independent_verifier_must_pass": True,
        "terminal_code_identity_must_be_unique_and_complete": True,
        "every_terminal_requires_counter_record_work_vector_comparison_vector": True,
        "every_terminal_requires_nine_shared_resource_receipts": True,
        "campaign_orchestration_vector_required": True,
        "output_bytes_exact_fixed_point_required": True,
        "producer_free_ten_source_reconstruction_required": True,
        "historical_summary_translation_forbidden": True,
        "failure_prefix_work_must_be_retained": True,
        "weight_agnostic_componentwise_economics_required_after_counter_completeness": True,
        "scalarization_in_this_protocol": False,
        "reference_machine_profile_present": False,
        "separate_fresh_calibration_successor_required_for_scalar_and_break_even": True,
        "execution_authorization_issued": False,
        "all_ten_paths_verified": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "aggregation_protocol_id": domains.extension_content_id_v180r12r1(
            domains.CONSTRUCTION_K7_AGGREGATION_PROTOCOL_V180R12R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TenTerminalAggregationProtocolV180R12R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    aggregation_protocol_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V180r12r1 protocol is not canonical")
        return document


@lru_cache(maxsize=1)
def freeze_ten_terminal_aggregation_protocol_v180r12r1() -> (
    TenTerminalAggregationProtocolV180R12R1
):
    document = build_ten_terminal_aggregation_protocol_v180r12r1()
    raw = canonical_json_bytes(document)
    if EXPECTED_PROTOCOL_ID != "0" * 64 and not (
        document["aggregation_protocol_id"] == EXPECTED_PROTOCOL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r12r1 protocol changed")
    return TenTerminalAggregationProtocolV180R12R1(
        _ISSUER,
        raw,
        document["aggregation_protocol_id"],
    )


__all__ = (
    "EXPECTED_PROTOCOL_ID",
    "build_ten_terminal_aggregation_protocol_v180r12r1",
    "freeze_ten_terminal_aggregation_protocol_v180r12r1",
)
