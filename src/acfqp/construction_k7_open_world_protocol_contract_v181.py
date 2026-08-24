"""Outcome-free protocol for the post-V179 open-world research successor.

The contract removes a finite candidate-program table and named target-family
registry.  It replaces them with length-ordered enumeration in a self-delimiting
universal expression language.  Every concrete run is still resource bounded;
therefore this contract does not itself claim unrestricted open-ended invention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v181 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


V179_COMPLETION_AUDIT_ID = (
    "373e67b24f19b130f556fbf5249b5661c27430a2f1ff15bc12dadb38d7238561"
)
V179_COMPLETION_VERIFICATION_ID = (
    "56fb4630b23cdfa0e28effaccaaabe30ddf8c9e18a40575ec30049fcabe9a3c9"
)
V180_FORMALIZATION_CONTRACT_ID = (
    "f392e9178e8c9c69150567ce210ad146ab96d61aa5925c34b133415fa86737fd"
)
V180_READINESS_AUDIT_ID = (
    "3abd33da19d79a8daf2c69fc757bcfed0ffba6a2a1515a5f9991e106b887a8af"
)
MANIFEST_COMMITMENTS = (
    "8f1e1a6b5b4ba54a4d4091079fcd17c6f6f31c214a4c0c665f57f195e2f8096f",
    "84a7bcdb91d96d71af644b304a9b8d775ba3836f37aad9a80b78f1a161ef2a92",
    "0893d1ef4a391c4412a9997ba1618b1cfd670954c6f1619635712f8c37aa1af4",
)
EXPECTED_CONTRACT_ID = (
    "7623fee75f20ba17dc9f66c9029a4d73cd0338ce49bab5b2d1118f36719f1377"
)
EXPECTED_CANONICAL_BYTE_COUNT = 4_042
EXPECTED_CANONICAL_SHA256 = (
    "aac9815334adf405a12854d06d9395bc93eccabcfdfcaa5fb12c7d4ea37cf42f"
)


def build_open_world_protocol_contract_v181() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.open_world_protocol_contract.v181",
        "predecessors": {
            "v179_completion_audit_id": V179_COMPLETION_AUDIT_ID,
            "v179_completion_verification_id": V179_COMPLETION_VERIFICATION_ID,
            "v180_formalization_contract_id": V180_FORMALIZATION_CONTRACT_ID,
            "v180_readiness_audit_id": V180_READINESS_AUDIT_ID,
            "predecessor_bytes_or_claims_mutated": False,
        },
        "representation_invention_protocol": {
            "named_target_family_registry_present": False,
            "finite_candidate_program_catalog_present": False,
            "whole_program_templates_present": False,
            "domain_specific_discovery_patterns_present": False,
            "source_generation_witness_available_to_synthesizer": False,
            "inputs": [
                "OPAQUE_INTEGER_STATE_VECTOR",
                "OPAQUE_INTEGER_ACTION_VECTOR",
                "RAW_SUCCESSOR_VECTOR",
                "RAW_TERMINAL_BIT",
            ],
            "language": "SELF_DELIMITING_LENGTH_ORDERED_TYPED_PREFIX_PROGRAMS",
            "instruction_vocabulary": [
                "LOAD_STATE",
                "LOAD_ACTION",
                "LOAD_SUPPORT_SYMBOL",
                "INTEGER_LITERAL",
                "ADD",
                "SUB",
                "MOD",
                "MIN",
                "MAX",
                "XOR",
                "EQ",
                "LT",
                "AND",
                "SELECT",
            ],
            "program_length_semantic_bound": None,
            "enumeration_order": "PREFIX_TOKEN_LENGTH_THEN_CANONICAL_BYTES",
            "observational_equivalence_deduplication_required": True,
            "exact_mdl_tie_break_required": True,
            "run_compute_budget_is_a_stop_condition_not_a_candidate_catalog": True,
            "resource_exhaustion_must_emit_typed_failure": True,
        },
        "hidden_target_protocol": {
            "manifest_commitment_domain": "acfqp:v181:manifest-commitment",
            "manifest_commitments": list(MANIFEST_COMMITMENTS),
            "manifest_count": len(MANIFEST_COMMITMENTS),
            "commitments_frozen_before_reveal_or_outcome_access": True,
            "salted_reveals_required": True,
            "synthesizer_may_not_read_manifest_programs": True,
            "oracle_exposes_only_raw_transition_queries": True,
            "named_family_labels_exposed": False,
        },
        "scientific_protocol": {
            "minimum_horizon": 5,
            "honest_partial_dynamics_support_required": True,
            "minimum_iid_distribution_count": 3,
            "iid_occurrences_per_distribution": 12,
            "matched_arms": [
                "REUSED_SUBPROGRAM_PRIOR",
                "EMPTY_ARCHIVE_NO_PRIOR",
            ],
            "same_synthesizer_search_and_stop_rule_across_arms": True,
            "receding_abstract_planning_required": True,
            "planner_consumes_compiled_program_not_raw_transition_rows": True,
            "ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_ood_no_transfer_required": True,
            "all_failed_predecessors_and_unfavourable_rows_retained": True,
        },
        "accounting_protocol": {
            "offline_source_labels_separate": True,
            "target_ground_labels_separate": True,
            "execution_steps_separate": True,
            "program_enumeration_compute_separate": True,
            "planning_compute_separate": True,
            "certificate_compute_separate": True,
            "producer_free_reconstruction_required": True,
            "weight_agnostic_total_work_vector_required": True,
            "outcome_selected_scalar_weights_forbidden": True,
        },
        "resource_schedule": {
            "maximum_simultaneous_worker_count": 2,
            "maximum_source_labels_per_distribution_and_arm": 512,
            "maximum_target_ground_labels_per_occurrence": 32,
            "maximum_program_enumeration_events_per_distribution_and_arm": 2_000_000,
            "maximum_receding_decisions_per_occurrence": 64,
        },
        "next_freeze_sequence": [
            "IMPLEMENT_DEVELOPMENT_ONLY_UNIVERSAL_SYNTHESIZER",
            "FREEZE_IMPLEMENTATION_SOURCE_BYTES",
            "ISSUE_FINAL_V181_PREREGISTRATION_BEFORE_MANIFEST_REVEAL",
            "REVEAL_AND_RUN_FRESH_TARGETS",
            "PRODUCER_FREE_RECONSTRUCTION",
        ],
        "claim_locks": {
            "v181_manifest_reveals_accessed": False,
            "v181_target_outcomes_accessed": False,
            "implementation_source_frozen": False,
            "open_ended_world_model_invention_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "broad_iid_sample_efficiency_claimed": False,
            "total_work_dominance_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "open_world_protocol_contract_id": domains.extension_content_id_v181(
            domains.CONSTRUCTION_K7_PROTOCOL_CONTRACT_V181_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldProtocolContractV181:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    contract_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_protocol_contract_v181() -> OpenWorldProtocolContractV181:
    document = build_open_world_protocol_contract_v181()
    raw = canonical_json_bytes(document)
    if EXPECTED_CONTRACT_ID != "0" * 64 and not (
        document["open_world_protocol_contract_id"] == EXPECTED_CONTRACT_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V181 frozen open-world protocol contract changed")
    return OpenWorldProtocolContractV181(
        _ISSUER,
        raw,
        document["open_world_protocol_contract_id"],
    )


__all__ = (
    "EXPECTED_CONTRACT_ID",
    "MANIFEST_COMMITMENTS",
    "freeze_open_world_protocol_contract_v181",
)
