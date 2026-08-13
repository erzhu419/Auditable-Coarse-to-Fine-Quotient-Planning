from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_context_program_preregistration_v20 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_context_program_gate_is_outcome_free() -> None:
    value = pre.freeze_standard_2048_context_program_preregistration_v20()
    assert pre.verify_standard_2048_context_program_preregistration_v20(value) is value
    document = value.to_document()
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert document["outcome_fields_present"] is False
    assert document["observation_archive_materialized"] is False
    assert document["feature_or_program_selected"] is False
    assert document["exact_postproposal_proof_executed"] is False
    assert document["world_model_issued"] is False
    assert document["heldout_planning_executed"] is False


def test_raw_contexts_and_feature_basis_are_frozen_before_queries() -> None:
    document = pre.freeze_standard_2048_context_program_preregistration_v20().to_document()
    protocol = document["source_context_protocol"]
    assert protocol["source_observation_count"] == 4
    assert protocol["witnesses_frozen_before_target_probability_queries"] is True
    assert protocol["post_swipe_board_and_features_computed_before_probability_query"] is True
    assert protocol["target_probability_or_kernel_rule_available_to_proposer"] is False
    assert [row["structurally_expected_post_swipe_empty_count"] for row in protocol["witnesses"]] == [
        2,
        5,
        3,
        4,
    ]
    assert document["feature_basis"] == list(pre.FEATURE_BASIS)
    assert document["feature_basis_kind"] == "FINITE_STRUCTURAL_PRIMITIVE_BASIS"


def test_candidates_are_generated_after_observation_and_proof_is_postproposal() -> None:
    document = pre.freeze_standard_2048_context_program_preregistration_v20().to_document()
    proposal = document["program_proposal_protocol"]
    assert proposal["preenumerated_feature_threshold_program_candidates"] is False
    assert proposal["override_values_generated_from_observed_nonbase_values"] is True
    assert proposal["threshold_values_generated_from_observed_feature_values"] is True
    assert proposal["normalized_program_schema"] == (
        "IF_FEATURE_LE_THRESHOLD_THEN_OVERRIDE_ELSE_BASE"
    )
    assert proposal["required_result"] == "UNIQUE_ZERO_MISMATCH_PROGRAM"
    proof = document["postproposal_exact_proof"]
    assert proof["target_source_access_before_proposal_freeze"] is False
    assert proof["registered_post_swipe_empty_count_domain"] == list(range(1, 17))
    assert proof["required_exact_formula_row_count"] == 16


def test_fresh_h3_workload_domains_and_claim_locks() -> None:
    document = pre.freeze_standard_2048_context_program_preregistration_v20().to_document()
    workload = document["heldout_planning_workload"]
    assert workload["episode_count"] == 3
    assert workload["maximum_decisions_per_episode"] == 4
    assert workload["planning_horizon"] == 3
    assert workload["heldout_target_transitions_unread_before_preregistration"] is True
    assert len(pre.FUTURE_DOMAINS) == 10
    assert len(set(pre.FUTURE_DOMAINS.values())) == 10
    assert set(pre.FUTURE_DOMAINS.values()).issubset(PHASE3E_DOMAIN_TAGS)
    assert document["open_ended_coordinate_invention_claimed"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["full_standard_2048_game_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_tamper_and_caller_mint_are_rejected() -> None:
    value = pre.freeze_standard_2048_context_program_preregistration_v20()
    tampered = copy.copy(value)
    object.__setattr__(tampered, "preregistration_id", "f" * 64)
    with pytest.raises(pre.ConstructionK7Standard2048ContextProgramPreregistrationV20Error):
        pre.verify_standard_2048_context_program_preregistration_v20(tampered)
    with pytest.raises(pre.ConstructionK7Standard2048ContextProgramPreregistrationV20Error):
        pre.Standard2048ContextProgramPreregistrationV20(
            object(), value.canonical_bytes, value.preregistration_id
        )
