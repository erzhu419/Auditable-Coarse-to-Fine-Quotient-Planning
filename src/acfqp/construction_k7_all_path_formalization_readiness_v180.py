"""Frozen current-readiness audit for the V180 all-path campaign.

This audit is intentionally outcome-free.  It inventories the strongest
terminal-specific accounting implementation that exists before any V180
terminal occurrence is run, and keeps implementation capability, retained
portable evidence, and fresh V180 evidence as three separate facts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_all_path_formalization_contract_v180 as contract_v180
from acfqp import construction_k7_domain_registry_extension_v180 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


SCHEMA_VERSION = "1.0.0"
EXPECTED_AUDIT_ID = (
    "3abd33da19d79a8daf2c69fc757bcfed0ffba6a2a1515a5f9991e106b887a8af"
)
EXPECTED_CANONICAL_BYTE_COUNT = 9_577
EXPECTED_CANONICAL_SHA256 = (
    "ccefeba25d2930f11c476716602bd622bf129411c389ec8035619d3ac8554e55"
)


@dataclass(frozen=True, slots=True)
class _ImplementationSpecV180:
    terminal_code: TerminalCode
    accounting_registry_version: str | None
    implementation_state: str
    producer_module: str
    verifier_module: str | None
    production_site_bound: bool
    complete_formal_chain_implemented: bool
    blocker_code: str | None


_SPECS = (
    _ImplementationSpecV180(
        TerminalCode.ABSTRACT_CERTIFIED,
        "9.0.0",
        "PRIOR_PROFILE_NATIVE_CHAIN_IMPLEMENTED",
        "construction_k7_standard_2048_expression_full_accounted_campaign_v34.py",
        "construction_k7_standard_2048_expression_full_accounted_independent_verifier_v34.py",
        True,
        True,
        None,
    ),
    _ImplementationSpecV180(
        TerminalCode.LOCAL_GROUND_RECOVERY,
        "9.0.0",
        "PRIOR_PROFILE_NATIVE_CHAIN_IMPLEMENTED",
        "construction_k7_standard_2048_adaptive_accounted_campaign_v36.py",
        "construction_k7_standard_2048_adaptive_accounted_independent_verifier_v36.py",
        True,
        True,
        None,
    ),
    _ImplementationSpecV180(
        TerminalCode.FULL_GROUND_FALLBACK,
        "6.0.0",
        "PRIOR_PROFILE_NATIVE_CHAIN_IMPLEMENTED_REQUIRES_V9_LIFT",
        "construction_k7_recovery_eligible_occurrence_accounting_v1.py",
        "construction_k7_recovery_eligible_campaign_independent_verifier_v1.py",
        True,
        True,
        "V9_TERMINAL_SPECIFIC_SUCCESSOR_REQUIRED",
    ),
    _ImplementationSpecV180(
        TerminalCode.CACHED_EXACT_INFEASIBLE,
        None,
        "TERMINAL_SPECIFIC_CHAIN_MISSING",
        "construction_k7_all_path_accounting_profile_v1.py",
        None,
        False,
        False,
        "CACHED_EXACT_INFEASIBLE_V9_CHAIN_REQUIRED",
    ),
    _ImplementationSpecV180(
        TerminalCode.FULL_GROUND_EXACT_INFEASIBLE,
        None,
        "READINESS_BLOCKER_ONLY",
        "construction_k7_direct_fallback_exact_infeasibility_readiness_v1.py",
        None,
        False,
        False,
        "LEGACY_42_ROW_VECTOR_CANNOT_BE_LIFTED_TO_V9",
    ),
    _ImplementationSpecV180(
        TerminalCode.INTEGRITY_FAILURE,
        "6.0.0",
        "PRIOR_PROFILE_NATIVE_CHAIN_IMPLEMENTED_REQUIRES_V9_LIFT",
        "construction_k7_integrity_failure_authority_v1.py",
        "construction_k7_integrity_failure_authority_v1.py",
        True,
        True,
        "V9_TERMINAL_SPECIFIC_FAILURE_SUCCESSOR_REQUIRED",
    ),
    _ImplementationSpecV180(
        TerminalCode.PROTOCOL_FAILURE,
        "6.0.0",
        "NEGATIVE_CONTROL_CHAIN_ONLY_REQUIRES_PRODUCTION_BINDING_AND_V9_LIFT",
        "construction_k7_protocol_failure_authority_v1.py",
        "construction_k7_protocol_failure_authority_v1.py",
        False,
        True,
        "PRODUCTION_SITE_AND_V9_SUCCESSOR_REQUIRED",
    ),
    _ImplementationSpecV180(
        TerminalCode.REBUILD_REQUIRED,
        None,
        "TERMINAL_SPECIFIC_CHAIN_MISSING",
        "construction_k7_all_path_accounting_profile_v1.py",
        None,
        False,
        False,
        "REBUILD_REQUIRED_V9_CHAIN_REQUIRED",
    ),
    _ImplementationSpecV180(
        TerminalCode.FALLBACK_CAP_EXHAUSTED,
        None,
        "TERMINAL_SPECIFIC_CHAIN_MISSING",
        "construction_k7_all_path_accounting_profile_v1.py",
        None,
        False,
        False,
        "FALLBACK_CAP_EXHAUSTED_V9_CHAIN_REQUIRED",
    ),
    _ImplementationSpecV180(
        TerminalCode.ATTEMPT_BUDGET_EXHAUSTED,
        "6.0.0",
        "PRIOR_PROFILE_NATIVE_CHAIN_IMPLEMENTED_REQUIRES_V9_LIFT",
        "construction_k7_root_cap_terminal_authority_v1.py",
        "construction_k7_production_complete_bundle_independent_verifier_v1.py",
        True,
        True,
        "V9_TERMINAL_SPECIFIC_FAILURE_SUCCESSOR_REQUIRED",
    ),
)


def _source_fact(filename: str) -> dict[str, Any]:
    path = Path(__file__).resolve().parent / filename
    raw = path.read_bytes()
    return {
        "filename": filename,
        "source_byte_count": len(raw),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_all_path_formalization_readiness_v180() -> dict[str, Any]:
    contract = contract_v180.freeze_all_path_formalization_contract_v180()
    source_facts = {
        filename: _source_fact(filename)
        for filename in sorted(
            {
                item.producer_module
                for item in _SPECS
            }
            | {
                item.verifier_module
                for item in _SPECS
                if item.verifier_module is not None
            }
        )
    }
    rows = [
        {
            "terminal_code": item.terminal_code.value,
            "accounting_registry_version": item.accounting_registry_version,
            "implementation_state": item.implementation_state,
            "producer_source": source_facts[item.producer_module],
            "verifier_source": (
                source_facts[item.verifier_module]
                if item.verifier_module is not None
                else None
            ),
            "complete_counter_record_work_vector_comparison_vector_chain_implemented": (
                item.complete_formal_chain_implemented
            ),
            "terminal_specific_independent_verifier_implemented": (
                item.verifier_module is not None
            ),
            "production_site_bound": item.production_site_bound,
            "retained_portable_occurrence_bytes_in_v180": False,
            "fresh_v180_observed_occurrence_present": False,
            "v180_output_fixed_point_replayed": False,
            "blocker_code": item.blocker_code,
        }
        for item in _SPECS
    ]
    v9_implemented = sum(
        row["accounting_registry_version"] == "9.0.0"
        and row[
            "complete_counter_record_work_vector_comparison_vector_chain_implemented"
        ]
        for row in rows
    )
    formal_implemented = sum(
        row[
            "complete_counter_record_work_vector_comparison_vector_chain_implemented"
        ]
        for row in rows
    )
    payload = {
        "schema": "acfqp.all_path_formalization_readiness.v180",
        "schema_version": SCHEMA_VERSION,
        "formalization_contract_id": contract.formalization_contract_id,
        "audit_timing": "AFTER_V180_CONTRACT_BEFORE_ANY_V180_OUTCOME",
        "terminal_rows": rows,
        "terminal_code_count": len(rows),
        "prior_profile_formal_chain_implementation_count": formal_implemented,
        "current_v9_formal_chain_implementation_count": v9_implemented,
        "fresh_v180_observed_occurrence_count": 0,
        "fresh_v180_missing_occurrence_count": len(rows),
        "retained_v180_portable_occurrence_count": 0,
        "historical_summary_promoted_to_v180_evidence": False,
        "next_required_actions": [
            "IMPLEMENT_ONE_V9_TERMINAL_FINALIZER_SHARED_BY_ALL_TEN_CODES",
            "BIND_PROTOCOL_FAILURE_TO_A_REAL_PRODUCTION_SITE",
            "RUN_FRESH_PREREGISTERED_OCCURRENCE_FOR_EACH_TERMINAL_CODE",
            "REPLAY_EVERY_COUNTER_AND_OUTPUT_FIXED_POINT_WITHOUT_PRODUCER_IMPORT",
            "CLOSE_ORDERED_ALL_PATH_CAMPAIGN_DENOMINATOR",
        ],
        "claim_locks": {
            "all_path_native_accounting_complete": False,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        },
    }
    return {
        **payload,
        "formalization_readiness_audit_id": domains.extension_content_id_v180(
            domains.CONSTRUCTION_K7_READINESS_AUDIT_V180_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AllPathFormalizationReadinessV180:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    audit_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_all_path_formalization_readiness_v180() -> AllPathFormalizationReadinessV180:
    document = build_all_path_formalization_readiness_v180()
    raw = canonical_json_bytes(document)
    if EXPECTED_AUDIT_ID != "0" * 64 and not (
        document["formalization_readiness_audit_id"] == EXPECTED_AUDIT_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180 frozen readiness audit changed")
    return AllPathFormalizationReadinessV180(
        _ISSUER,
        raw,
        document["formalization_readiness_audit_id"],
    )


__all__ = (
    "EXPECTED_AUDIT_ID",
    "freeze_all_path_formalization_readiness_v180",
)
