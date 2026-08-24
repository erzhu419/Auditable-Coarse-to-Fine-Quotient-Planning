"""Outcome-free V180r3 execution protocol for ten fresh terminal paths.

The protocol fixes one successor occurrence identity for every V180r2 slot.
It deliberately issues no occurrence, reads no terminal outcome, and leaves
all accounting, economics, scalar, and official-execution gates locked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_all_path_formalization_contract_v180 as contract
from acfqp import construction_k7_all_path_production_preregistration_v180r2 as predecessor
from acfqp import construction_k7_domain_registry_extension_v180r3 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


EXPECTED_PROTOCOL_ID = (
    "ea8aa0a457d09b7056f19f73ca606262fb806f445d0c868708b617244d396e01"
)
EXPECTED_CANONICAL_BYTE_COUNT = 26_522
EXPECTED_CANONICAL_SHA256 = (
    "069fa76eaa79ea5694f8783c57e06184b9c458f7ef27c05e98f18492c41867a3"
)


_EXECUTION_NONCE_BY_CODE = {
    code: hashlib.sha256(
        b"acfqp:v180r3:fresh-production-execution-nonce\x00"
        + code.value.encode()
    ).hexdigest()
    for code in TerminalCode
}


def _source_fact(filename: str) -> dict[str, Any]:
    raw = (Path(__file__).resolve().parent / filename).read_bytes()
    return {
        "filename": filename,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_all_path_production_execution_protocol_v180r3() -> dict[str, Any]:
    formal = contract.freeze_all_path_formalization_contract_v180()
    prior = predecessor.freeze_all_path_production_preregistration_v180r2()
    prior_document = prior.to_document()
    source_names = {
        row["production_site_source"]["filename"]
        for row in prior_document["terminal_occurrence_slots"]
    } | {
        "construction_k7_all_path_terminal_finalizer_v180r1.py",
        "construction_k7_all_path_terminal_finalizer_independent_verifier_v180r1.py",
        "construction_k7_all_path_production_preregistration_v180r2.py",
        "construction_k7_domain_registry_extension_v180r3.py",
        "construction_accounting_registry_v9.py",
    }
    source_facts = {
        filename: _source_fact(filename) for filename in sorted(source_names)
    }
    slots = []
    for prior_slot in prior_document["terminal_occurrence_slots"]:
        code = TerminalCode(prior_slot["terminal_code"])
        payload = {
            "schema": "acfqp.all_path_production_execution_slot.v180r3",
            "formalization_contract_id": formal.formalization_contract_id,
            "production_preregistration_id": prior.production_preregistration_id,
            "predecessor_occurrence_slot_id": prior_slot["occurrence_slot_id"],
            "ordinal": prior_slot["ordinal"],
            "terminal_code": code.value,
            "execution_nonce": _EXECUTION_NONCE_BY_CODE[code],
            "production_site_source": source_facts[
                prior_slot["production_site_source"]["filename"]
            ],
            "required_evidence_roles": prior_slot["required_evidence_roles"],
            "counter_registry_version": "9.0.0",
            "native_counter_record_source_required": True,
            "historical_summary_to_counter_translation_forbidden": True,
            "development_fixture_evidence_forbidden": True,
            "fresh_process_or_occurrence_boundary_required": True,
            "counter_record_work_vector_comparison_vector_required": True,
            "output_fixed_point_required": True,
            "producer_free_replay_required": True,
            "same_identity_rerun_after_terminal_forbidden": True,
            "outcome_accessed": False,
        }
        slots.append(
            {
                **payload,
                "production_execution_slot_id": domains.extension_content_id_v180r3(
                    domains.CONSTRUCTION_K7_PRODUCTION_EXECUTION_SLOT_V180R3_DOMAIN,
                    payload,
                ),
            }
        )
    payload = {
        "schema": "acfqp.all_path_production_execution_protocol.v180r3",
        "formalization_contract_id": formal.formalization_contract_id,
        "production_preregistration_id": prior.production_preregistration_id,
        "ordered_terminal_codes": [code.value for code in TerminalCode],
        "production_execution_slots": slots,
        "ordered_denominator": len(slots),
        "source_facts": [source_facts[key] for key in sorted(source_facts)],
        "protocol_frozen_before_any_v180r3_outcome": True,
        "production_outcomes_accessed": False,
        "fresh_production_occurrence_count": 0,
        "all_ten_terminal_codes_must_reach_one_terminal_exactly_once": True,
        "partial_campaign_cannot_unlock_any_gate": True,
        "failed_identity_must_be_preserved_without_rerun": True,
        "counter_completeness_precedes_economics": True,
        "weight_agnostic_economics_precedes_scalar_calibration": True,
        "scalar_calibration_precedes_official_execution": True,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "production_execution_protocol_id": domains.extension_content_id_v180r3(
            domains.CONSTRUCTION_K7_PRODUCTION_EXECUTION_PROTOCOL_V180R3_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AllPathProductionExecutionProtocolV180r3:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    production_execution_protocol_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


@lru_cache(maxsize=1)
def freeze_all_path_production_execution_protocol_v180r3() -> AllPathProductionExecutionProtocolV180r3:
    document = build_all_path_production_execution_protocol_v180r3()
    raw = canonical_json_bytes(document)
    if EXPECTED_PROTOCOL_ID != "0" * 64 and not (
        document["production_execution_protocol_id"] == EXPECTED_PROTOCOL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r3 frozen production execution protocol changed")
    return AllPathProductionExecutionProtocolV180r3(
        _ISSUER,
        raw,
        document["production_execution_protocol_id"],
    )


__all__ = (
    "EXPECTED_PROTOCOL_ID",
    "freeze_all_path_production_execution_protocol_v180r3",
)
