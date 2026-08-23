"""Producer-free verification of the V179 finite-objective completion audit."""

from __future__ import annotations

import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v179 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CONTRACT_ID = "6823041e61671aa9cefd45903522451c605735d937cab8e356c9035087f2fd66"
CONTRACT_BYTE_COUNT = 3_991
CONTRACT_SHA256 = "040beafcb23d342701eabfcc570f6f1932211f65bc9a8e55b5f9bdf371684c66"
V178R1_CAMPAIGN_ID = "0" * 64
V178R1_CAMPAIGN_BYTE_COUNT = 0
V178R1_CAMPAIGN_SHA256 = "0" * 64
V178R1_VERIFICATION_ID = "0" * 64
V178R1_VERIFICATION_BYTE_COUNT = 0
V178R1_VERIFICATION_SHA256 = "0" * 64
AUDIT_ID = "0" * 64
AUDIT_BYTE_COUNT = 0
AUDIT_SHA256 = "0" * 64
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


_FIXED_FACTS = (
    (
        "v41_standard_2048_complete_episode_campaign.json",
        1_400_748,
        "81400665c11f9efe70d6e0223898597cf45c3b4d27b1a8bd15ad50b3e6390c2f",
        "adaptive_checkpoint_campaign_id",
        "1a576e0c8b34f52050f77366ec7ac39dab58bddd53ec91180ed9d6c092072732",
    ),
    (
        "v41_standard_2048_complete_episode_verification.json",
        1_602,
        "9e9808e081c5b2d0d65534e4d0a99618329060608e59bad48c5e856f923c4395",
        "adaptive_checkpoint_verification_id",
        "a05a6b795a15a8dda596b148efe52b374cc687f125b1c14731466f83aa791396",
    ),
    (
        "v124_cross_family_generic_compiler_campaign.json",
        1_830_635,
        "b1a1f7e40747275077ce32e3147a48bef2235de23bc3b983e86b79d36a32eb49",
        "campaign_id",
        "d2da5c1f3271b362a584156fa7febe4d0cf2e715e14d9d4d453eeef471aa1d26",
    ),
    (
        "v124_cross_family_generic_compiler_verification.json",
        3_636,
        "5dac5d7a7f147759e82c7384d13a3ee4148285ca852057077ba5ad8fddbf7f7b",
        "verification_id",
        "f58ab2a74d21907b019da2461b26b33c6d988416eb4050cb7545370b5ff24ea1",
    ),
    (
        "v159_third_dynamics_campaign.json",
        22_440_110,
        "10befc870c0ef542b32dc401e8f6d81bc99314c5ec6cc972ad56d161dad23748",
        "campaign_id",
        "76561d796084acf486f92e55feeca59a2b671cfacd03ddd2eb17230a8503bc55",
    ),
    (
        "v159_third_dynamics_verification.json",
        14_492,
        "cae733f19abf841dc37bfeb6d4cb038a4a1cd480fe452cf25d069ac262d0faae",
        "verification_id",
        "43714af046dc9ec04a3d35fddec08c6e803867afbde154f8a2cbae3e9cf5bebb",
    ),
    (
        "v168_fifth_family_total_plan_receipt_set_campaign.json",
        25_586_483,
        "e0cd4d36fb72bf79519878e1a368aeecf128cd91c4571bf0071d68af2760dfa5",
        "campaign_id",
        "447f04fb450a9b76083993593a66ef717431f0b814212927ff2adfa1e27e4dce",
    ),
    (
        "v168_fifth_family_total_plan_receipt_set_verification.json",
        10_215,
        "ecf1c0d10fc9cedc508353425cbf2c93533a52cbd2b07af2076eb5b9161cbc09",
        "verification_id",
        "11378538ea1d8340647b9e172f34c7e6f427a1d177a045074e596329c2cb8908",
    ),
)


class ConstructionK7FiniteObjectiveCompletionIndependentVerifierV179Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FiniteObjectiveCompletionIndependentVerifierV179Error(
        message
    )


def _document(raw, fact):
    name, count, digest, identity_key, identity = fact
    document = loads_canonical_json(raw)
    if not (
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(identity_key) == identity
    ):
        _fail(f"V179 independent input changed: {name}")
    return document


def _claim_locks(document):
    economics = document.get(
        "WORKLOAD_ECONOMICS_GATE",
        document.get("workload_economics_gate_status"),
    )
    counters = document.get(
        "COUNTER_COMPLETENESS_GATE",
        document.get("counter_completeness_gate_status"),
    )
    return (
        document.get("official_execution_allowed") is False
        and document.get("official_scalar_cost") is None
        and document.get("official_N_break_even") is None
        and economics == "NOT_RUN"
        and counters == "NOT_RUN"
    )


def verify_finite_objective_completion_audit_v179(
    contract_raw: bytes,
    audit_raw: bytes,
    v41_campaign_raw: bytes,
    v41_verification_raw: bytes,
    v124_campaign_raw: bytes,
    v124_verification_raw: bytes,
    v159_campaign_raw: bytes,
    v159_verification_raw: bytes,
    v168_campaign_raw: bytes,
    v168_verification_raw: bytes,
    v178r1_campaign_raw: bytes,
    v178r1_verification_raw: bytes,
) -> dict[str, Any]:
    contract = loads_canonical_json(contract_raw)
    if not (
        canonical_json_bytes(contract) == contract_raw
        and len(contract_raw) == CONTRACT_BYTE_COUNT
        and hashlib.sha256(contract_raw).hexdigest() == CONTRACT_SHA256
        and contract.get("completion_contract_id") == CONTRACT_ID
        and contract.get("completion_rule", {}).get(
            "registered_finite_central_objective_may_be_marked_complete"
        )
        is True
        and contract.get("target_outcomes_accessed") is False
    ):
        _fail("V179 independent completion contract changed")
    if "0" * 64 in {
        V178R1_CAMPAIGN_ID,
        V178R1_VERIFICATION_ID,
        AUDIT_ID,
    }:
        _fail("V179 independent terminal identities are not frozen")
    raws = (
        v41_campaign_raw,
        v41_verification_raw,
        v124_campaign_raw,
        v124_verification_raw,
        v159_campaign_raw,
        v159_verification_raw,
        v168_campaign_raw,
        v168_verification_raw,
        v178r1_campaign_raw,
        v178r1_verification_raw,
    )
    facts = _FIXED_FACTS + (
        (
            "v178r1_indexed_lazy_invalidation_campaign.json",
            V178R1_CAMPAIGN_BYTE_COUNT,
            V178R1_CAMPAIGN_SHA256,
            "campaign_id",
            V178R1_CAMPAIGN_ID,
        ),
        (
            "v178r1_indexed_lazy_invalidation_verification.json",
            V178R1_VERIFICATION_BYTE_COUNT,
            V178R1_VERIFICATION_SHA256,
            "verification_id",
            V178R1_VERIFICATION_ID,
        ),
    )
    documents = [_document(raw, fact) for raw, fact in zip(raws, facts)]
    (
        v41_campaign,
        v41_verification,
        v124_campaign,
        v124_verification,
        v159_campaign,
        v159_verification,
        v168_campaign,
        v168_verification,
        v178_campaign,
        v178_verification,
    ) = documents
    if not (
        v41_campaign["adaptive_checkpoint_campaign_id"]
        == v41_verification["adaptive_checkpoint_campaign_id"]
        and v41_campaign["full_standard_2048_game_completed"] is True
        and v41_campaign["tile_2048_reached"] is True
        and v41_campaign["all_segment_planning_performed_in_expression_world_model"]
        is True
        and v41_campaign["operational_ground_state_action_row_count_in_segment"]
        == 0
        and v41_verification["producer_module_imported"] is False
        and v41_verification["retained_campaign_bytes_replayed"] is True
        and v41_verification["full_game_completion_verified"] is True
        and v41_verification["tile_2048_reached_verified"] is True
        and v124_verification["campaign_id"] == v124_campaign["campaign_id"]
        and v124_campaign["registered_gate"]["passed"] is True
        and v124_campaign["incompatible_schema_no_transfer_control"][
            "strict_ood_no_transfer"
        ]
        is True
        and v124_campaign["incompatible_schema_no_transfer_control"][
            "learned_structure_prior_delivered"
        ]
        is False
        and v124_verification[
            "producer_free_raw_transition_model_epoch_reconstruction"
        ]
        is True
        and v124_verification[
            "producer_free_recursive_expression_successor_reconstruction"
        ]
        is True
        and v124_verification[
            "producer_free_terminal_rule_and_plan_reconstruction"
        ]
        is True
        and v159_verification["campaign_id"] == v159_campaign["campaign_id"]
        and v159_campaign["registered_gate"]["passed"] is True
        and v159_campaign["registered_gate"][
            "certificate_failure_local_recovery_exercised"
        ]
        is True
        and v159_verification[
            "producer_free_abstract_planning_plan_receipt_and_certificate_reconstruction"
        ]
        is True
        and v159_verification["factor_prior_sample_reduction_within_joint_policy"]
        > 0
        and v168_verification["campaign_id"] == v168_campaign["campaign_id"]
        and v168_campaign["registered_gate"]["passed"] is True
        and v168_campaign["registered_gate"][
            "fresh_packet_certificate_failure_only_local_ground_distinctions"
        ]
        is True
        and v168_verification[
            "producer_free_acquisition_candidate_sequence_and_v109_reconstruction"
        ]
        is True
        and v168_verification[
            "fifth_family_factor_prior_sample_tax_transfer_independently_verified"
        ]
        is True
        and v178_verification["campaign_id"] == v178_campaign["campaign_id"]
        and v178_campaign["registered_gate"]["passed"] is True
        and v178_campaign["indexed_lazy_invalidation_observed"] is True
        and v178_verification["producer_free_target_outcome_reexecution"] is True
        and v178_verification[
            "producer_free_dependency_reverse_index_reconstruction"
        ]
        is True
        and v178_verification[
            "producer_free_issuance_reverse_index_reconstruction"
        ]
        is True
        and v178_verification["producer_free_lazy_authorization_reconstruction"]
        is True
        and all(_claim_locks(document) for document in documents)
    ):
        _fail("V179 independent evidence semantics changed")
    accounting = v178_campaign["accounting"]
    if not (
        accounting["production_full_graph_diff_checks"] == 0
        and accounting["production_live_dependency_projection_scan_count"] == 0
        and accounting["production_prior_receipt_event_scan_count"] == 0
        and accounting["retained_authorization_metadata_updates"] == 0
        and accounting["lazy_authorization_metadata_updates"]
        == accounting["lazy_authorization_receipts"]
        == accounting["lazy_authorization_issuance_joins"]
        > 0
        and v178_verification[
            "zero_production_prior_receipt_event_scan_independently_verified"
        ]
        is True
        and v178_verification[
            "zero_eager_retained_authorization_update_independently_verified"
        ]
        is True
    ):
        _fail("V179 independent indexed-lazy tax removal changed")
    evidence = [
        {
            "name": fact[0],
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            fact[3]: fact[4],
        }
        for raw, fact in zip(raws, facts)
    ]
    expected_payload = {
        "schema": "acfqp.finite_objective_completion_audit.v179",
        "completion_contract_id": CONTRACT_ID,
        "evidence_facts": evidence,
        "registered_finite_central_objective_completed": True,
        "actual_full_episode_2048_and_tile_2048_verified": True,
        "observation_derived_generic_abstract_world_model_compiler_verified": True,
        "multi_step_planning_primarily_in_reusable_abstract_models_verified": True,
        "certificate_failure_only_local_ground_recovery_verified": True,
        "strict_incompatible_schema_ood_no_transfer_verified": True,
        "matched_factor_prior_sample_tax_reduction_verified": True,
        "complete_typed_plan_receipt_lifecycle_verified": True,
        "indexed_lazy_minimal_invalidation_verified": True,
        "production_prior_receipt_event_scan_count": 0,
        "production_eager_retained_authorization_update_count": 0,
        "producer_free_verification_present_for_every_required_evidence_role": True,
        "sample_labels_execution_steps_derivation_planning_certificate_and_maintenance_compute_separate": True,
        "completion_scope": "FINITE_COVERAGE_BOUNDED_REGISTERED_SYMBOLIC_FAMILIES",
        "complete_ground_world_model_synthesized": False,
        "open_ended_world_model_invention_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "broad_iid_sample_efficiency_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "new_target_outcomes_accessed_by_completion_audit": False,
    }
    expected_audit = {
        **expected_payload,
        "completion_audit_id": domains.extension_content_id_v179(
            domains.CONSTRUCTION_K7_COMPLETION_AUDIT_V179_DOMAIN,
            expected_payload,
        ),
    }
    audit = loads_canonical_json(audit_raw)
    if not (
        canonical_json_bytes(audit) == audit_raw
        and len(audit_raw) == AUDIT_BYTE_COUNT
        and hashlib.sha256(audit_raw).hexdigest() == AUDIT_SHA256
        and audit.get("completion_audit_id") == AUDIT_ID
        and canonical_json_bytes(audit) == canonical_json_bytes(expected_audit)
    ):
        _fail("V179 independent completion audit reconstruction changed")
    verification_payload = {
        "schema": "acfqp.finite_objective_completion_verification.v179",
        "completion_contract_id": CONTRACT_ID,
        "completion_audit_id": AUDIT_ID,
        "verified_evidence_facts": evidence,
        "registered_finite_central_objective_completion_independently_verified": True,
        "full_episode_2048_and_tile_2048_independently_verified": True,
        "generic_compiler_and_ood_no_transfer_independently_verified": True,
        "multi_family_partial_stochastic_transfer_independently_verified": True,
        "certificate_failure_only_local_ground_recovery_independently_verified": True,
        "matched_sample_tax_reduction_independently_verified": True,
        "indexed_lazy_scan_and_eager_update_tax_removal_independently_verified": True,
        "completion_scope": "FINITE_COVERAGE_BOUNDED_REGISTERED_SYMBOLIC_FAMILIES",
        "complete_ground_world_model_claimed": False,
        "open_ended_world_model_invention_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "broad_iid_sample_efficiency_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **verification_payload,
        "verification_id": domains.extension_content_id_v179(
            domains.CONSTRUCTION_K7_VERIFICATION_V179_DOMAIN,
            verification_payload,
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == VERIFICATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V179 frozen independent completion verification changed")
    return document


__all__ = (
    "VERIFICATION_ID",
    "verify_finite_objective_completion_audit_v179",
)
