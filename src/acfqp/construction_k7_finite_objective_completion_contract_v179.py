"""Outcome-free contract for the finite registered central-objective audit."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v179 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CENTRAL_OBJECTIVE = (
    "compile a coverage-bounded ground process once into a reusable abstract "
    "planning model, perform repeated multi-step contingent planning primarily "
    "in that model, and recover ground distinctions locally only when an "
    "independent value/risk certificate cannot certify the current plan"
)
V178R1_PREREGISTRATION_ID = (
    "a4ffe67949d0cad7f392f678b5b8c9c4d6631ebea5d9e49c95f61367f2b40064"
)
EXPECTED_CONTRACT_ID = "6823041e61671aa9cefd45903522451c605735d937cab8e356c9035087f2fd66"
EXPECTED_CANONICAL_BYTE_COUNT = 3_991
EXPECTED_CANONICAL_SHA256 = "040beafcb23d342701eabfcc570f6f1932211f65bc9a8e55b5f9bdf371684c66"


def build_finite_objective_completion_contract_v179() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.finite_objective_completion_contract.v179",
        "central_objective": CENTRAL_OBJECTIVE,
        "completion_scope": {
            "finite_state": True,
            "finite_horizon": True,
            "fully_observable_symbolic_kernels": True,
            "coverage_bounded_registered_families_only": True,
            "open_ended_world_model_invention_required": False,
            "arbitrary_unseen_domain_transfer_required": False,
            "official_execution_or_economics_required": False,
        },
        "required_evidence": [
            {
                "role": "FULL_EPISODE_REAL_TASK_DEMONSTRATION",
                "version": "V41",
                "campaign_id": "1a576e0c8b34f52050f77366ec7ac39dab58bddd53ec91180ed9d6c092072732",
                "campaign_byte_count": 1_400_748,
                "campaign_sha256": "81400665c11f9efe70d6e0223898597cf45c3b4d27b1a8bd15ad50b3e6390c2f",
                "verification_id": "a05a6b795a15a8dda596b148efe52b374cc687f125b1c14731466f83aa791396",
                "verification_byte_count": 1_602,
                "verification_sha256": "9e9808e081c5b2d0d65534e4d0a99618329060608e59bad48c5e856f923c4395",
                "required_claims": [
                    "full_game_completion_verified",
                    "tile_2048_reached_verified",
                    "producer_free_exact_replay",
                ],
            },
            {
                "role": "OBSERVATION_DERIVED_GENERIC_COMPILER_AND_OOD_CONTROL",
                "version": "V124",
                "campaign_id": "d2da5c1f3271b362a584156fa7febe4d0cf2e715e14d9d4d453eeef471aa1d26",
                "verification_id": "f58ab2a74d21907b019da2461b26b33c6d988416eb4050cb7545370b5ff24ea1",
                "required_claims": [
                    "producer_free_raw_transition_model_epoch_reconstruction",
                    "producer_free_recursive_expression_successor_reconstruction",
                    "producer_free_terminal_rule_and_plan_reconstruction",
                    "incompatible_schema_no_transfer_control",
                ],
            },
            {
                "role": "THIRD_DYNAMICS_AND_MATCHED_SAMPLE_TAX",
                "version": "V159",
                "campaign_id": "76561d796084acf486f92e55feeca59a2b671cfacd03ddd2eb17230a8503bc55",
                "verification_id": "43714af046dc9ec04a3d35fddec08c6e803867afbde154f8a2cbae3e9cf5bebb",
                "required_claims": [
                    "producer_free_abstract_planning_plan_receipt_and_certificate_reconstruction",
                    "positive_factor_prior_sample_reduction",
                ],
            },
            {
                "role": "FIFTH_FAMILY_TOTAL_PLAN_RECEIPT_SET",
                "version": "V168",
                "campaign_id": "447f04fb450a9b76083993593a66ef717431f0b814212927ff2adfa1e27e4dce",
                "verification_id": "11378538ea1d8340647b9e172f34c7e6f427a1d177a045074e596329c2cb8908",
                "required_claims": [
                    "producer_free_acquisition_candidate_sequence_and_v109_reconstruction",
                    "fifth_family_factor_prior_sample_tax_transfer_independently_verified",
                ],
            },
            {
                "role": "INDEXED_LAZY_CERTIFICATE_FAILURE_RECOVERY_LIFECYCLE",
                "version": "V178R1",
                "preregistration_id": V178R1_PREREGISTRATION_ID,
                "fresh_campaign_and_verification_identity_required": True,
                "required_claims": [
                    "producer_free_target_outcome_reexecution",
                    "producer_free_dependency_reverse_index_reconstruction",
                    "producer_free_issuance_reverse_index_reconstruction",
                    "producer_free_lazy_authorization_reconstruction",
                    "zero_production_prior_receipt_event_scan_independently_verified",
                    "zero_eager_retained_authorization_update_independently_verified",
                ],
            },
        ],
        "completion_rule": {
            "all_required_evidence_content_addressed": True,
            "all_required_producer_free_verifications_pass": True,
            "multi_step_planning_primarily_in_reusable_abstract_model": True,
            "ground_distinctions_only_after_certificate_failure": True,
            "sample_labels_execution_planning_derivation_certificate_and_maintenance_compute_separate": True,
            "registered_finite_central_objective_may_be_marked_complete": True,
        },
        "claim_locks": {
            "complete_ground_world_model_synthesized": False,
            "open_ended_world_model_invention_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "broad_iid_sample_efficiency_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "target_outcomes_accessed": False,
    }
    return {
        **payload,
        "completion_contract_id": domains.extension_content_id_v179(
            domains.CONSTRUCTION_K7_COMPLETION_CONTRACT_V179_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FiniteObjectiveCompletionContractV179:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    completion_contract_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_finite_objective_completion_contract_v179():
    document = build_finite_objective_completion_contract_v179()
    raw = canonical_json_bytes(document)
    if EXPECTED_CONTRACT_ID != "0" * 64 and not (
        document["completion_contract_id"] == EXPECTED_CONTRACT_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V179 frozen completion contract changed")
    return FiniteObjectiveCompletionContractV179(
        _ISSUER, raw, document["completion_contract_id"]
    )


__all__ = (
    "EXPECTED_CONTRACT_ID",
    "freeze_finite_objective_completion_contract_v179",
)
