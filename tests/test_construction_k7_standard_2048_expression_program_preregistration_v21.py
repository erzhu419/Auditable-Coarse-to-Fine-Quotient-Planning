from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_expression_program_preregistration_v21 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_expression_gate_is_outcome_free() -> None:
    value = pre.freeze_standard_2048_expression_program_preregistration_v21()
    assert pre.verify_standard_2048_expression_program_preregistration_v21(value) is value
    document = value.to_document()
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert document["outcome_fields_present"] is False
    assert document["context_pool_materialized"] is False
    assert document["target_probability_query_count"] == 0
    assert document["expression_candidate_count"] == 0
    assert document["expression_or_program_selected"] is False
    assert document["exact_proof_executed"] is False
    assert document["heldout_planning_executed"] is False


def test_only_raw_contexts_and_generic_expression_grammar_are_supplied() -> None:
    document = pre.freeze_standard_2048_expression_program_preregistration_v21().to_document()
    pool = document["raw_context_pool_protocol"]
    assert pool["context_count"] == 8
    assert all(set(row) == {"pool_ordinal", "pre_state_board_ranks", "action"} for row in pool["contexts"])
    assert pool["all_structural_expression_values_frozen_before_first_probability_query"] is True
    grammar = document["expression_grammar"]
    assert grammar["named_empty_count_feature_supplied"] is False
    assert grammar["named_v20_feature_basis_supplied"] is False
    assert grammar["count_eq_constants_generated_from_observed_raw_cell_values"] is True
    assert grammar["expression_composition_depth"] == 1
    assert grammar["open_ended_expression_language_claimed"] is False


def test_active_query_budget_and_fresh_workload_are_frozen() -> None:
    document = pre.freeze_standard_2048_expression_program_preregistration_v21().to_document()
    protocol = document["program_and_active_acquisition_protocol"]
    assert protocol["first_query_pool_ordinal"] == 0
    assert protocol["maximum_target_probability_queries"] == 4
    assert protocol["after_first_query_rule"] == (
        "MINIMIZE_MAXIMUM_REMAINING_VERSION_BUCKET_THEN_POOL_ORDINAL"
    )
    assert protocol["stop_rule"] == "UNIQUE_ZERO_MISMATCH_EXPRESSION_PROGRAM"
    workload = document["heldout_planning_workload"]
    assert workload["episode_count"] == 3
    assert workload["maximum_decisions_per_episode"] == 4
    assert workload["planning_horizon"] == 3
    assert workload["heldout_transitions_unread_before_preregistration"] is True


def test_domains_sample_contract_and_claim_locks() -> None:
    document = pre.freeze_standard_2048_expression_program_preregistration_v21().to_document()
    assert len(pre.FUTURE_DOMAINS) == 11
    assert len(set(pre.FUTURE_DOMAINS.values())) == 11
    assert set(pre.FUTURE_DOMAINS.values()).issubset(PHASE3E_DOMAIN_TAGS)
    sample = document["sample_tax_contract"]
    assert sample["v21_probability_query_budget"] == 4
    assert sample["v19_actual_strict_no_prior_query_count"] == 10
    assert sample["scalar_sum_present"] is False
    assert document["open_ended_coordinate_invention_claimed"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["full_standard_2048_game_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_tamper_and_caller_mint_are_rejected() -> None:
    value = pre.freeze_standard_2048_expression_program_preregistration_v21()
    tampered = copy.copy(value)
    object.__setattr__(tampered, "preregistration_id", "f" * 64)
    with pytest.raises(pre.ConstructionK7Standard2048ExpressionProgramPreregistrationV21Error):
        pre.verify_standard_2048_expression_program_preregistration_v21(tampered)
    with pytest.raises(pre.ConstructionK7Standard2048ExpressionProgramPreregistrationV21Error):
        pre.Standard2048ExpressionProgramPreregistrationV21(
            object(), value.canonical_bytes, value.preregistration_id
        )
