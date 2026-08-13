from __future__ import annotations

import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_adaptive_expression_preregistration_v35 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_preregistration_is_outcome_free_and_commit_only() -> None:
    value = pre.freeze_standard_2048_adaptive_expression_preregistration_v35()
    assert pre.verify_standard_2048_adaptive_expression_preregistration_v35(value) is value
    document = value.to_document()
    assert document["outcome_fields_present"] is False
    assert document["target_revealed"] is False
    assert document["target_execution_performed"] is False
    assert document["target_probability_label_count"] == 0
    assert document["certificate_failure_count"] == 0
    assert document["overlay_program_count"] == 0
    assert document["certificate_count"] == 0
    target = document["target_commitment"]
    assert target["target_kernel_commitment_id"] == pre.TARGET_KERNEL_COMMITMENT_ID
    assert target["target_semantics_document_present"] is False
    assert target["target_source_present"] is False
    assert target["target_probability_table_present"] is False
    predecessors = document["frozen_predecessors"]
    assert predecessors["v34_accounted_campaign_id"]["kind"] == (
        "PENDING_PREEXECUTION_BINDING"
    )
    assert predecessors["v34_accounting_verification_id"]["kind"] == (
        "PENDING_PREEXECUTION_BINDING"
    )
    assert predecessors[
        "v34_full_accounting_must_verify_before_target_execution"
    ] is True


def test_target_semantics_are_not_revealed_in_preregistration_source() -> None:
    source = Path(pre.__file__).read_text(encoding="utf-8")
    assert "override_expression_ast" not in source
    assert "override_rank_two_probability" not in source
    assert "override_threshold" not in source
    assert "rank_one_probability_is_exact_complement" not in source


def test_fresh_registered_long_segment_and_domains() -> None:
    document = pre.freeze_standard_2048_adaptive_expression_preregistration_v35().to_document()
    workload = document["fresh_long_segment"]
    assert workload["episode_count"] == 4
    assert workload["maximum_decision_count"] == 512
    assert all(sum(rank != 0 for rank in board) == 2 for board in pre.INITIAL_BOARDS)
    freshness = workload["freshness_evidence"]
    assert freshness["target_orbits_pairwise_distinct"] is True
    assert freshness["target_orbits_disjoint_from_predecessors"] is True
    assert len(pre.FUTURE_DOMAINS) == 12
    assert len(set(pre.FUTURE_DOMAINS.values())) == 12
    assert set(pre.FUTURE_DOMAINS.values()).issubset(PHASE3E_DOMAIN_TAGS)


def test_only_failed_frontier_can_trigger_target_acquisition() -> None:
    document = pre.freeze_standard_2048_adaptive_expression_preregistration_v35().to_document()
    recovery = document["certificate_triggered_recovery"]
    assert recovery["h3_raw_frontier_frozen_before_any_target_probability_query"] is True
    assert recovery["failure_artifact_required_before_acquisition"] is True
    assert recovery["query_context_must_belong_to_failed_certificate_frontier"] is True
    assert recovery["candidate_universe_frozen_at_first_failed_frontier"] is True
    assert recovery["later_frontiers_may_filter_but_not_expand_candidate_universe"] is True
    assert recovery["global_unique_program_required"] is False
    assert recovery["persistent_overlay_reused_across_decisions_and_episodes"] is True
    assert recovery["global_target_table_read_allowed"] is False
    assert recovery["maximum_target_probability_labels"] == 12


def test_generic_observation_grammar_and_matched_controls_are_frozen() -> None:
    document = pre.freeze_standard_2048_adaptive_expression_preregistration_v35().to_document()
    prior = document["observation_derived_structural_prior"]
    assert prior["support_program_and_position_law_reused_without_target_labels"] is True
    assert prior["expression_composition_depth"] == 1
    assert prior["constants_generated_only_from_frozen_raw_context_values"] is True
    assert prior["nonbase_probabilities_generated_only_from_acquired_labels"] is True
    assert prior["named_target_feature_supplied"] is False
    assert prior["target_specific_program_candidate_supplied"] is False
    controls = document["matched_controls"]
    assert controls[
        "no_prior_ground_table_queries_every_distinct_first_failed_h3_context"
    ] is True
    assert controls["control_target_labels_never_feed_operational_overlay"] is True
    assert controls["control_and_cold_ground_are_evaluation_lane_only"] is True
    proof = document["postproposal_reveal_and_proof"]
    assert proof["preproposal_target_access_limited_to_black_box_probability_labels"] is True
    assert proof[
        "target_semantics_document_or_formula_read_before_first_overlay_proposal_freeze"
    ] is False
    assert proof["target_commitment_recomputed_before_semantic_proof"] is True
    assert proof["proof_failure_prevents_world_model_authority"] is True
    assert proof["proved_world_model_reused_without_further_target_table_reads"] is True


def test_sample_tax_accounting_and_claim_locks_are_exact() -> None:
    document = pre.freeze_standard_2048_adaptive_expression_preregistration_v35().to_document()
    sample = document["sample_tax_contract"]
    assert sample["adaptive_target_probability_label_cap"] == 12
    assert sample["model_labels_execution_transitions_and_planning_compute_separate"] is True
    assert sample["meta_prior_may_not_supply_target_program_or_certificate"] is True
    accounting = document["native_accounting_contract"]
    assert accounting["counter_record_to_work_vector_to_comparison_vector_required"] is True
    assert accounting["nine_shared_resource_paths_measured"] is True
    assert accounting["evaluation_lane_excluded_from_operational_comparison"] is True
    assert document["full_standard_2048_game_claimed"] is False
    assert document["automatic_reusable_world_model_goal_completed"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_tamper_and_caller_mint_are_rejected() -> None:
    value = pre.freeze_standard_2048_adaptive_expression_preregistration_v35()
    tampered = copy.copy(value)
    object.__setattr__(tampered, "preregistration_id", "f" * 64)
    with pytest.raises(
        pre.ConstructionK7Standard2048AdaptiveExpressionPreregistrationV35Error
    ):
        pre.verify_standard_2048_adaptive_expression_preregistration_v35(tampered)
    with pytest.raises(
        pre.ConstructionK7Standard2048AdaptiveExpressionPreregistrationV35Error
    ):
        pre.Standard2048AdaptiveExpressionPreregistrationV35(
            object(), value.canonical_bytes, value.preregistration_id
        )
