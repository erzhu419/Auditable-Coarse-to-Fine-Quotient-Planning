from __future__ import annotations

import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_blind_expression_preregistration_v22 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_commit_only_gate_is_outcome_free_and_unrevealed() -> None:
    value = pre.freeze_standard_2048_blind_expression_preregistration_v22()
    assert pre.verify_standard_2048_blind_expression_preregistration_v22(value) is value
    document = value.to_document()
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert document["outcome_fields_present"] is False
    assert document["target_revealed"] is False
    assert document["target_probability_query_count"] == 0
    assert document["expression_candidates_generated"] is False
    assert document["expression_program_selected"] is False
    assert document["exact_proof_executed"] is False
    assert document["heldout_planning_executed"] is False


def test_only_target_commitment_not_semantics_is_frozen() -> None:
    document = pre.freeze_standard_2048_blind_expression_preregistration_v22().to_document()
    commitment = document["target_commitment"]
    assert commitment["target_kernel_commitment_id"] == pre.TARGET_KERNEL_COMMITMENT_ID
    assert commitment["target_semantics_document_present"] is False
    assert commitment["target_kernel_source_present"] is False
    assert commitment["commitment_frozen_before_reveal_commit"] is True
    assert commitment["reveal_must_recompute_exact_committed_content_id"] is True
    assert commitment["experimenter_cognitive_blinding_claimed"] is False
    assert commitment["git_ordered_commit_reveal_protocol_claimed"] is True
    source = Path(pre.__file__).read_text(encoding="utf-8")
    assert "override_expression_ast" not in source
    assert "override_probability" not in source


def test_v21_protocol_is_transferred_without_target_specific_feature() -> None:
    document = pre.freeze_standard_2048_blind_expression_preregistration_v22().to_document()
    grammar = document["transferred_expression_grammar"]
    assert grammar["expression_composition_depth"] == 1
    assert grammar["named_feature_or_target_specific_expression_supplied"] is False
    assert grammar["override_generated_from_first_observed_nonbase_value"] is True
    assert document["raw_context_count"] == 8
    active = document["active_acquisition"]
    assert active["first_query_pool_ordinal"] == 0
    assert active["maximum_target_probability_queries"] == 4
    assert active["later_query_rule"] == (
        "MINIMIZE_MAXIMUM_REMAINING_VERSION_BUCKET_THEN_POOL_ORDINAL"
    )


def test_fresh_workload_domains_and_claim_locks() -> None:
    document = pre.freeze_standard_2048_blind_expression_preregistration_v22().to_document()
    workload = document["heldout_planning_workload"]
    assert workload["episode_count"] == 3
    assert workload["maximum_decisions_per_episode"] == 4
    assert workload["planning_horizon"] == 3
    assert len(pre.FUTURE_DOMAINS) == 12
    assert len(set(pre.FUTURE_DOMAINS.values())) == 12
    assert set(pre.FUTURE_DOMAINS.values()).issubset(PHASE3E_DOMAIN_TAGS)
    assert document["blind_protocol_transfer_claimed"] is False
    assert document["open_ended_expression_invention_claimed"] is False
    assert document["broad_sample_efficiency_claimed"] is False
    assert document["full_standard_2048_game_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_tamper_and_caller_mint_are_rejected() -> None:
    value = pre.freeze_standard_2048_blind_expression_preregistration_v22()
    tampered = copy.copy(value)
    object.__setattr__(tampered, "preregistration_id", "f" * 64)
    with pytest.raises(pre.ConstructionK7Standard2048BlindExpressionPreregistrationV22Error):
        pre.verify_standard_2048_blind_expression_preregistration_v22(tampered)
    with pytest.raises(pre.ConstructionK7Standard2048BlindExpressionPreregistrationV22Error):
        pre.Standard2048BlindExpressionPreregistrationV22(
            object(), value.canonical_bytes, value.preregistration_id
        )
