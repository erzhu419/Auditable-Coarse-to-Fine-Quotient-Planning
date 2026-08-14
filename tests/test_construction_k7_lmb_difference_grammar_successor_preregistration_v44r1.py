from __future__ import annotations

import hashlib

from acfqp import construction_k7_lmb_difference_grammar_successor_preregistration_v44r1 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_v44r1_preserves_failure_and_registers_fresh_model_derived_confirmation() -> None:
    frozen = pre.freeze_lmb_difference_grammar_successor_preregistration_v44r1()
    document = frozen.to_document()
    predecessors = document["frozen_predecessors"]
    source = document["source_successor_protocol"]
    assert predecessors["v44_failure_id"] == pre.V44_FAILURE_ID
    assert predecessors["failed_predecessor_preserved_without_relabeling"] is True
    assert source["inherited_offline_source_transition_labels"] == 42
    assert source["fresh_confirmation_seed"] == 440301
    assert source["confirmation_policy"] == (
        "DERIVE_PARTIAL_PROGRAM_THEN_MODEL_PLAN_FULL_REMOVAL"
    )
    assert source["full_removal_is_planning_goal_not_assumed_terminal_status"] is True
    assert source["terminal_success_rule_requires_fresh_observation"] is True
    assert source["kernel_step_during_source_planning_allowed"] is False
    assert source["source_generation_witness_access_allowed"] is False
    assert source["reuse_failed_v44_seed_under_new_identity"] is False
    assert document["numeric_program_grid_present"] is False
    assert document["outcome_fields_present"] is False
    assert document["campaign_executed"] is False


def test_v44r1_identity_domains_and_locked_claims() -> None:
    frozen = pre.freeze_lmb_difference_grammar_successor_preregistration_v44r1()
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert len(set(pre.FUTURE_DOMAINS.values())) == len(pre.FUTURE_DOMAINS)
    assert set(pre.FUTURE_DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    document = frozen.to_document()
    assert document["heldout_target"]["target_outcome_observed_before_registration"] is False
    assert all(document["heldout_target"]["different_from_source"].values())
    assert document["open_ended_grammar_invention_claimed"] is False
    assert document["broad_iid_or_cross_domain_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
