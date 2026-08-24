"""Outcome-free protocol for aggregating the ten V180 terminal paths."""

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
from acfqp import construction_k7_domain_registry_extension_v180r12 as domains
from acfqp import construction_k7_remaining_terminal_evidence_freeze_v180r9 as remaining
from acfqp import construction_k7_v34_retained_recovery_authorization_v180r11 as abstract
from acfqp.accounting_v1 import RouteKindEnum
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


EXPECTED_PROTOCOL_ID = "f0b5f52205b6f4eeb671bb86c5d048f72df14100bbabee7b22ce4619c66ccd15"
EXPECTED_CANONICAL_BYTE_COUNT = 5_033
EXPECTED_CANONICAL_SHA256 = "2c58ead754839c26631cb04b835ac496e774c11f14078e81edf687050fc09f2f"

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v180r12.py",
    "src/acfqp/construction_k7_all_path_formalization_contract_v180.py",
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


def build_ten_terminal_aggregation_protocol_v180r12() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    terminal_sources = [
        {
            "terminal_code": TerminalCode.ABSTRACT_CERTIFIED.value,
            "source_kind": "V180R11_RETAINED_V34_FINISH_FORWARD",
            "source_authorization_id": abstract.EXPECTED_AUTHORIZATION_ID,
            "terminal_relative_path": ".tmp/exact-freeze/v180r11_v34_retained_terminal.json",
            "verification_relative_path": ".tmp/exact-freeze/v180r11_v34_retained_verification.json",
            "status_at_protocol_freeze": "COMPLETED",
        },
        {
            "terminal_code": TerminalCode.LOCAL_GROUND_RECOVERY.value,
            "source_kind": "V180R10_FRESH_V36_RESOURCE_SUCCESSOR",
            "source_authorization_id": local.EXPECTED_AUTHORIZATION_ID,
            "terminal_relative_path": ".tmp/exact-freeze/v180r10_v36_resource_successor_terminal.json",
            "verification_relative_path": ".tmp/exact-freeze/v180r10_v36_resource_successor_verification.json",
            "status_at_protocol_freeze": "AUTHORIZED_RUNNING",
        },
        {
            "terminal_code": TerminalCode.FULL_GROUND_FALLBACK.value,
            "source_kind": "V180R7_FRESH_FULL_GROUND_FALLBACK",
            "source_authorization_id": fallback.EXPECTED_AUTHORIZATION_ID,
            "terminal_relative_path": ".tmp/exact-freeze/v180r7_full_ground_fallback_terminal_bundle.json",
            "verification_relative_path": None,
            "status_at_protocol_freeze": "AUTHORIZED_NOT_STARTED",
        },
        {
            "terminal_code": TerminalCode.CACHED_EXACT_INFEASIBLE.value,
            "source_kind": "V180R8_FRESH_CACHED_EXACT",
            "source_authorization_id": cached.EXPECTED_AUTHORIZATION_ID,
            "terminal_relative_path": ".tmp/v180r8-cached-exact-production/TERMINAL.json",
            "verification_relative_path": None,
            "status_at_protocol_freeze": "AUTHORIZED_NOT_STARTED",
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
            "status_at_protocol_freeze": "COMPLETED",
        },
    ]
    payload = {
        "schema": "acfqp.ten_terminal_aggregation_protocol.v180r12",
        "formalization_contract_id": contract.EXPECTED_CONTRACT_ID,
        "formalization_contract_exact_frozen_identity_used": True,
        "terminal_sources": terminal_sources,
        "ordered_terminal_codes": [row.value for row in TerminalCode],
        "terminal_code_count": len(TerminalCode),
        "ordered_route_kinds": [row.value for row in RouteKindEnum],
        "route_kind_count": len(RouteKindEnum),
        "completed_terminal_code_count_at_protocol_freeze": 7,
        "pending_terminal_codes_at_protocol_freeze": [
            TerminalCode.LOCAL_GROUND_RECOVERY.value,
            TerminalCode.FULL_GROUND_FALLBACK.value,
            TerminalCode.CACHED_EXACT_INFEASIBLE.value,
        ],
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
        "all_ten_paths_verified": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "aggregation_protocol_id": domains.extension_content_id_v180r12(
            domains.CONSTRUCTION_K7_AGGREGATION_PROTOCOL_V180R12_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TenTerminalAggregationProtocolV180R12:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    aggregation_protocol_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V180r12 protocol is not canonical")
        return document


@lru_cache(maxsize=1)
def freeze_ten_terminal_aggregation_protocol_v180r12() -> TenTerminalAggregationProtocolV180R12:
    document = build_ten_terminal_aggregation_protocol_v180r12()
    raw = canonical_json_bytes(document)
    if EXPECTED_PROTOCOL_ID != "0" * 64 and not (
        document["aggregation_protocol_id"] == EXPECTED_PROTOCOL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r12 protocol changed")
    return TenTerminalAggregationProtocolV180R12(
        _ISSUER,
        raw,
        document["aggregation_protocol_id"],
    )


__all__ = (
    "EXPECTED_PROTOCOL_ID",
    "build_ten_terminal_aggregation_protocol_v180r12",
    "freeze_ten_terminal_aggregation_protocol_v180r12",
)
