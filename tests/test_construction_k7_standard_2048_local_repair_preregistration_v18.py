from __future__ import annotations

import copy
from fractions import Fraction

import pytest

from acfqp import construction_k7_standard_2048_local_dynamics_kernel_v18 as kernel
from acfqp import construction_k7_standard_2048_local_repair_preregistration_v18 as pre
from acfqp.domains.standard_2048 import Swipe2048Action, state_from_board_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_target_kernel_is_exact_and_content_bound() -> None:
    assert kernel.verify_target_kernel_identity_v18() == kernel.TARGET_KERNEL_ID
    assert kernel.query_rank_two_probability_v18(4) == Fraction(1, 5)
    assert kernel.query_rank_two_probability_v18(5) == Fraction(1, 10)
    state = state_from_board_v1(pre.TARGET_INITIAL_BOARDS[0])
    outcomes = kernel.target_outcomes_v18(state, Swipe2048Action.LEFT)
    assert sum((row.probability for row in outcomes), Fraction()) == 1


def test_preregistration_is_outcome_free() -> None:
    value = pre.freeze_standard_2048_local_repair_preregistration_v18()
    assert pre.verify_standard_2048_local_repair_preregistration_v18(value) is value
    document = value.to_document()
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert document["outcome_fields_present"] is False
    assert document["target_execution_performed"] is False
    assert document["certificate_failure_count"] == 0
    assert document["ground_distinction_query_count"] == 0
    assert document["overlay_program_selected"] is False


def test_frozen_program_prior_and_recovery_order() -> None:
    document = pre.freeze_standard_2048_local_repair_preregistration_v18().to_document()
    assert document["candidate_program_count"] == 25
    assert len(document["candidate_programs"]) == 25
    protocol = document["recovery_protocol"]
    assert protocol["ground_probability_query_before_failed_audit"] is False
    assert protocol["queries_restricted_to_failed_certificate_frontier"] is True
    assert protocol["persistent_version_space_reused_across_decisions_and_episodes"] is True
    assert protocol["maximum_ground_distinction_queries"] == 8


def test_base_model_and_target_workload_are_frozen() -> None:
    document = pre.freeze_standard_2048_local_repair_preregistration_v18().to_document()
    base = document["frozen_base_model"]
    assert base["v16_synthesized_world_model_id"] == pre.V16_WORLD_MODEL_ID
    assert base["v17_independent_verification_id"] == pre.V17_INDEPENDENT_VERIFICATION_ID
    assert document["target_environment_binding"]["target_kernel_id"] == kernel.TARGET_KERNEL_ID
    assert document["target_workload"]["episode_count"] == 3
    assert document["target_workload"]["maximum_decisions_per_episode"] == 4


def test_domains_and_claim_locks_remain_scoped() -> None:
    document = pre.freeze_standard_2048_local_repair_preregistration_v18().to_document()
    assert len(pre.FUTURE_DOMAINS) == 9
    assert len(set(pre.FUTURE_DOMAINS.values())) == 9
    assert set(pre.FUTURE_DOMAINS.values()).issubset(PHASE3E_DOMAIN_TAGS)
    assert document["sample_tax_scope"]["broad_or_physical_iid_sample_efficiency_claimed"] is False
    assert document["sample_tax_scope"]["total_operational_work_saving_claimed"] is False
    assert document["broad_world_model_synthesis_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_tamper_and_caller_mint_are_rejected() -> None:
    value = pre.freeze_standard_2048_local_repair_preregistration_v18()
    tampered = copy.copy(value)
    object.__setattr__(tampered, "preregistration_id", "f" * 64)
    with pytest.raises(pre.ConstructionK7Standard2048LocalRepairPreregistrationV18Error):
        pre.verify_standard_2048_local_repair_preregistration_v18(tampered)
    with pytest.raises(pre.ConstructionK7Standard2048LocalRepairPreregistrationV18Error):
        pre.Standard2048LocalRepairPreregistrationV18(
            object(), value.canonical_bytes, value.preregistration_id
        )
