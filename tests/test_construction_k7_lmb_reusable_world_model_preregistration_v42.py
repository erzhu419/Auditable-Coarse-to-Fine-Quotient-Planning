from __future__ import annotations

import copy
import hashlib

import pytest

from acfqp import construction_k7_lmb_reusable_world_model_preregistration_v42 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


@pytest.fixture(scope="module")
def frozen():
    return pre.freeze_lmb_reusable_world_model_preregistration_v42()


def test_v42_is_outcome_free_and_preserves_v41(frozen) -> None:
    document = frozen.to_document()
    predecessor = document["frozen_predecessor"]
    assert predecessor == {
        "v41_preregistration_id": pre.V41_PREREGISTRATION_ID,
        "v41_complete_episode_campaign_id": pre.V41_CAMPAIGN_ID,
        "v41_producer_free_verification_id": pre.V41_VERIFICATION_ID,
        "v41_identities_preserved_without_rewrite": True,
    }
    workload = document["outcome_free_workload"]
    assert workload["target_kernel_transition_observed_before_registration"] is False
    assert workload["target_outcome_or_policy_present"] is False
    assert workload["generation_witness_available_to_planner"] is False
    assert document["outcome_fields_present"] is False
    assert document["target_campaign_executed"] is False


def test_v42_freezes_generic_program_and_matched_acquisition(frozen) -> None:
    document = frozen.to_document()
    program = document["observation_derived_program_space"]
    assert program["source_relations"] == list(pre.GENERIC_SOURCE_RELATIONS)
    assert program["meta_operators"] == list(pre.GENERIC_META_OPERATORS)
    assert program["registered_shared_primitive_compatibility_names"] == list(
        pre.REGISTERED_SHARED_PRIMITIVES
    )
    assert program["domain_name_or_reward_query_is_program_input"] is False
    matched = document["matched_acquisition_protocol"]
    assert matched["arms"] == list(pre.ACQUISITION_ARMS)
    assert matched["same_heldout_instances_and_episode_order"] is True
    assert matched["prior_is_proposal_order_not_acceptance_authority"] is True
    assert matched["target_row_may_be_acquired_only_after_certificate_failure"] is True


def test_v42_separates_labels_execution_and_planning_compute(frozen) -> None:
    document = frozen.to_document()
    axes = document["accounting_axes"]
    assert axes["labels_must_not_be_summed_with_compute_events"] is True
    assert axes["execution_steps_must_not_be_relabelled_as_model_labels"] is True
    protocol = document["planning_and_certificate_protocol"]
    assert protocol["kernel_step_during_planning_forbidden"] is True
    assert protocol["failed_certificate_precedes_every_local_ground_distinction"] is True
    assert protocol["successful_certificate_forbids_local_ground_acquisition"] is True


def test_v42_domains_identity_and_claim_locks(frozen) -> None:
    assert set(pre.FUTURE_DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    assert len(set(pre.FUTURE_DOMAINS.values())) == len(pre.FUTURE_DOMAINS)
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == (
        pre.EXPECTED_CANONICAL_SHA256
    )
    document = frozen.to_document()
    assert document["cross_domain_general_sample_efficiency_claimed"] is False
    assert document["broad_iid_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    forged = copy.copy(frozen)
    object.__setattr__(forged, "preregistration_id", "f" * 64)
    with pytest.raises(
        pre.ConstructionK7LMBReusableWorldModelPreregistrationV42Error
    ):
        pre.verify_lmb_reusable_world_model_preregistration_v42(forged)
