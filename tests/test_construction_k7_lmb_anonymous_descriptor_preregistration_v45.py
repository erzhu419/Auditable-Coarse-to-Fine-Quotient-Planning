from __future__ import annotations

import hashlib

from acfqp import construction_k7_lmb_anonymous_descriptor_preregistration_v45 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_v45_is_outcome_free_anonymous_and_has_no_named_projection() -> None:
    frozen = pre.freeze_lmb_anonymous_descriptor_preregistration_v45()
    document = frozen.to_document()
    adapter = document["anonymous_adapter_protocol"]
    grammar = document["typed_relation_grammar"]
    source = document["source_projection_acquisition"]
    assert document["outcome_fields_present"] is False
    assert document["campaign_executed"] is False
    assert document["named_action_class_scaffold_present"] is False
    assert b"ACTION_PUBLIC_CLASS" not in frozen.canonical_bytes
    assert adapter["descriptor_field_semantic_names_exposed_to_synthesizer"] is False
    assert adapter["descriptor_values_permuted_by_occurrence"] is True
    assert adapter["coordinate_order_permuted_by_occurrence"] is True
    assert grammar["named_action_class_atom_present"] is False
    assert grammar["predeclared_projection_field"] is None
    assert source["action_policy"] == "MIN_LEGAL_ACTION_ID"
    assert source["action_policy_reads_descriptor_fields"] is False
    assert source["source_generation_witness_access_allowed"] is False


def test_v45_dependency_signature_is_not_hand_written() -> None:
    document = pre.freeze_lmb_anonymous_descriptor_preregistration_v45().to_document()
    minimization = document["dependency_minimization"]
    protocol = document["planning_and_recovery_protocol"]
    assert minimization["support_signature_fields_predeclared"] == []
    assert minimization["expected_support_signature_predeclared"] is False
    assert protocol["derived_support_signature_required"] is True
    assert protocol["hand_written_structural_support_key_present"] is False
    assert protocol["ground_distinction_requires_prior_failed_certificate"] is True
    assert protocol["successful_certificate_forbids_ground_acquisition"] is True


def test_v45_identity_fresh_permuted_target_and_claim_locks() -> None:
    frozen = pre.freeze_lmb_anonymous_descriptor_preregistration_v45()
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert len(set(pre.FUTURE_DOMAINS.values())) == len(pre.FUTURE_DOMAINS)
    assert set(pre.FUTURE_DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    document = frozen.to_document()
    target = document["heldout_target"]
    assert target["target_outcome_observed_before_registration"] is False
    assert target["descriptor_values_and_coordinate_order_changed"] is True
    assert target["tile_count_changed"] is True
    assert target["type_count_changed"] is True
    assert target["capacity_changed"] is True
    assert target["layer_depth_changed"] is True
    assert document["open_ended_descriptor_or_grammar_invention_claimed"] is False
    assert document["broad_iid_or_cross_domain_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
