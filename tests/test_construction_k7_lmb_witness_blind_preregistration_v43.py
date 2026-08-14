from __future__ import annotations

import copy
import hashlib

import pytest

from acfqp import construction_k7_lmb_witness_blind_preregistration_v43 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_v43_is_outcome_free_witness_blind_and_cross_cardinality() -> None:
    frozen = pre.freeze_lmb_witness_blind_preregistration_v43()
    document = frozen.to_document()
    source = document["source_exploration"]
    target = document["cross_cardinality_target"]
    assert source["source_generation_witness_access_allowed"] is False
    assert source["source_hidden_solution_sequence_access_allowed"] is False
    assert source["action_selection_uses_only_public_state_legal_actions_and_candidates"] is True
    assert target["heldout_generation_witness_access_allowed"] is False
    assert target["target_transition_observed_before_registration"] is False
    assert target["source_to_target_tile_count_changed"] is True
    assert target["source_to_target_type_count_changed"] is True
    assert target["source_to_target_layer_depth_changed"] is True
    assert document["outcome_fields_present"] is False
    assert document["campaign_executed"] is False


def test_v43_identity_protocol_axes_and_claim_locks() -> None:
    frozen = pre.freeze_lmb_witness_blind_preregistration_v43()
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert len(set(pre.FUTURE_DOMAINS.values())) == len(pre.FUTURE_DOMAINS)
    assert set(pre.FUTURE_DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    document = frozen.to_document()
    protocol = document["world_model_protocol"]
    assert protocol["kernel_step_during_planning_allowed"] is False
    assert protocol["ground_distinction_requires_prior_failed_certificate"] is True
    assert protocol["successful_certificate_forbids_ground_acquisition"] is True
    assert document["accounting_axes"]["labels_steps_and_compute_may_not_be_collapsed"] is True
    assert document["broad_iid_or_cross_domain_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    forged = copy.copy(frozen)
    object.__setattr__(forged, "preregistration_id", "f" * 64)
    with pytest.raises(pre.ConstructionK7LMBWitnessBlindPreregistrationV43Error):
        pre.verify_lmb_witness_blind_preregistration_v43(forged)
