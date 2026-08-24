"""Outcome-free ten-terminal production-occurrence denominator for V180r2."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_all_path_accounting_profile_v1 as profile_v1
from acfqp import construction_k7_all_path_formalization_contract_v180 as contract_v180
from acfqp import construction_k7_all_path_terminal_finalizer_fixture_freeze_v180r1 as fixture_v180r1
from acfqp import construction_k7_domain_registry_extension_v180r2 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


EXPECTED_PREREGISTRATION_ID = (
    "f9e0a1021ef0ce7a7f3082bb6b97a951987b7bb1c766381ba5391b40428561e5"
)
EXPECTED_CANONICAL_BYTE_COUNT = 22_796
EXPECTED_CANONICAL_SHA256 = (
    "57f5036e0879de7451e0f63044b11f923261cf193bd28c89d3af83db90b78a0b"
)


_SITE_BY_CODE = {
    TerminalCode.ABSTRACT_CERTIFIED: "construction_k7_standard_2048_expression_full_accounted_campaign_v34.py",
    TerminalCode.LOCAL_GROUND_RECOVERY: "construction_k7_standard_2048_adaptive_accounted_campaign_v36.py",
    TerminalCode.FULL_GROUND_FALLBACK: "construction_k7_recovery_eligible_occurrence_accounting_v1.py",
    TerminalCode.CACHED_EXACT_INFEASIBLE: "phase3e_occurrence_runner_v1.py",
    TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: "phase3e_occurrence_runner_v1.py",
    TerminalCode.INTEGRITY_FAILURE: "construction_k7_integrity_failure_authority_v1.py",
    TerminalCode.PROTOCOL_FAILURE: "phase3e_occurrence_runner_v1.py",
    TerminalCode.REBUILD_REQUIRED: "phase3e_occurrence_runner_v1.py",
    TerminalCode.FALLBACK_CAP_EXHAUSTED: "phase3e_occurrence_runner_v1.py",
    TerminalCode.ATTEMPT_BUDGET_EXHAUSTED: "construction_k7_root_cap_terminal_authority_v1.py",
}


def _source_fact(filename: str) -> dict[str, Any]:
    raw = (Path(__file__).resolve().parent / filename).read_bytes()
    return {
        "filename": filename,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_all_path_production_preregistration_v180r2() -> dict[str, Any]:
    contract = contract_v180.freeze_all_path_formalization_contract_v180()
    fixture = fixture_v180r1.load_frozen_fixture_graph_v180r1()
    profile = profile_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    rule_by_code = profile.terminal_path_rule_by_code
    source_facts = {
        filename: _source_fact(filename)
        for filename in sorted(
            {
                *_SITE_BY_CODE.values(),
                "construction_k7_all_path_terminal_finalizer_v180r1.py",
                "construction_k7_all_path_terminal_finalizer_independent_verifier_v180r1.py",
                "construction_k7_all_path_terminal_finalizer_fixture_freeze_v180r1.py",
                "construction_k7_all_path_accounting_profile_v1.py",
                "construction_k7_all_path_formalization_contract_v180.py",
                "construction_k7_domain_registry_extension_v180r2.py",
                "construction_accounting_registry_v9.py",
            }
        )
    }
    slots = []
    for ordinal, code in enumerate(TerminalCode):
        rule = rule_by_code[code]
        slot_payload = {
            "schema": "acfqp.all_path_production_occurrence_slot.v180r2",
            "formalization_contract_id": contract.formalization_contract_id,
            "ordinal": ordinal,
            "terminal_code": code.value,
            "permitted_route_kinds": [
                row.value for row in rule.route_kinds_permitted_in_attempt
            ],
            "required_evidence_roles": [
                row.to_document() for row in rule.required_evidence_roles
            ],
            "production_site_source": source_facts[_SITE_BY_CODE[code]],
            "fresh_occurrence_required": True,
            "historical_or_fixture_evidence_forbidden": True,
            "counter_registry_version_required": "9.0.0",
            "counter_record_work_vector_comparison_vector_required": True,
            "output_fixed_point_required": True,
            "outcome_accessed": False,
        }
        slots.append(
            {
                **slot_payload,
                "occurrence_slot_id": domains.extension_content_id_v180r2(
                    domains.CONSTRUCTION_K7_OCCURRENCE_SLOT_V180R2_DOMAIN,
                    slot_payload,
                ),
            }
        )
    payload = {
        "schema": "acfqp.all_path_production_preregistration.v180r2",
        "formalization_contract_id": contract.formalization_contract_id,
        "v180r1_fixture_campaign_id": fixture.campaign_id,
        "v180r1_fixture_verification_id": fixture.verification_id,
        "all_path_accounting_profile_id": profile.profile_id,
        "terminal_occurrence_slots": slots,
        "ordered_terminal_codes": [code.value for code in TerminalCode],
        "ordered_denominator": len(slots),
        "one_fresh_occurrence_per_terminal_code": True,
        "source_facts": [source_facts[key] for key in sorted(source_facts)],
        "production_outcomes_accessed": False,
        "fresh_production_occurrence_count": 0,
        "protocol_failure_real_runner_site_preregistered": True,
        "shared_v9_finalizer_must_be_reimplemented_as_additive_production_boundary": True,
        "fixture_finalizer_source_mutated": False,
        "same_identity_rerun_after_terminal_forbidden": True,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "production_preregistration_id": domains.extension_content_id_v180r2(
            domains.CONSTRUCTION_K7_PRODUCTION_PREREGISTRATION_V180R2_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AllPathProductionPreregistrationV180r2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    production_preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


@lru_cache(maxsize=1)
def freeze_all_path_production_preregistration_v180r2() -> AllPathProductionPreregistrationV180r2:
    document = build_all_path_production_preregistration_v180r2()
    raw = canonical_json_bytes(document)
    if EXPECTED_PREREGISTRATION_ID != "0" * 64 and not (
        document["production_preregistration_id"] == EXPECTED_PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r2 frozen production preregistration changed")
    return AllPathProductionPreregistrationV180r2(
        _ISSUER,
        raw,
        document["production_preregistration_id"],
    )


__all__ = (
    "EXPECTED_PREREGISTRATION_ID",
    "freeze_all_path_production_preregistration_v180r2",
)
