from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_spawn_program_preregistration_v16 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_spawn_program_preregistration_is_outcome_free() -> None:
    value = pre.freeze_standard_2048_spawn_program_preregistration_v16()
    assert pre.verify_standard_2048_spawn_program_preregistration_v16(value) is value
    document = value.to_document()
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert document["v15_independent_verification_id"] == (
        "33777be770b7ae8eb45c4d22b2a8c5226dde4a443f2381ea402afd09826f7180"
    )
    assert document["outcome_fields_present"] is False
    assert document["observation_archives_materialized"] is False
    assert document["program_selection_executed"] is False
    assert document["exact_support_proof_executed"] is False
    assert document["target_planning_or_execution_performed"] is False


def test_candidate_grammar_and_fresh_streams_are_frozen() -> None:
    document = pre.freeze_standard_2048_spawn_program_preregistration_v16().to_document()
    assert len(document["spawn_program_candidates"]) == 25
    assert document["spawn_program_candidates"][12]["candidate_key"] == (
        "LAST_EMPTY_CELL_ONLY__RANK_TWO_1_OVER_10"
    )
    protocol = document["fresh_observation_protocol"]
    assert protocol["source_observation_count"] == 256
    assert protocol["validation_observation_count"] == 128
    assert protocol["streams_are_content_addressed_and_disjoint"] is True
    assert protocol["spawn_probability_or_source_rule_available_to_learner"] is False


def test_exact_proof_and_sample_axes_are_separate() -> None:
    document = pre.freeze_standard_2048_spawn_program_preregistration_v16().to_document()
    proof = document["exact_postselection_proof"]
    assert proof["source_access_allowed_only_after_proposal_freeze"] is True
    assert proof["nonempty_proper_empty_cell_subsets"] == 65534
    assert proof["proof_compute_is_not_counted_as_transition_observation"] is True
    gate = document["sample_tax_gate"]
    assert gate["joint_swipe_and_spawn_observation_count"] == 1152
    assert gate["matched_fixed_observation_control_count"] == 8192
    assert gate["registered_observation_difference"] == 7040
    assert gate["broad_or_physical_iid_sample_efficiency_claimed"] is False
    assert gate["total_operational_work_saving_claimed"] is False


def test_future_domains_are_registered_and_distinct() -> None:
    values = tuple(pre.FUTURE_DOMAINS.values())
    assert len(values) == 8
    assert len(set(values)) == len(values)
    assert set(values).issubset(PHASE3E_DOMAIN_TAGS)


def test_claims_and_official_gates_remain_locked() -> None:
    document = pre.freeze_standard_2048_spawn_program_preregistration_v16().to_document()
    assert document["sample_tax_reduction_claimed"] is False
    assert document["full_standard_2048_game_claimed"] is False
    assert document["tile_2048_reached"] is False
    assert document["broad_world_model_synthesis_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_tamper_and_caller_mint_are_rejected() -> None:
    value = pre.freeze_standard_2048_spawn_program_preregistration_v16()
    tampered = copy.copy(value)
    object.__setattr__(tampered, "preregistration_id", "f" * 64)
    with pytest.raises(
        pre.ConstructionK7Standard2048SpawnProgramPreregistrationV16Error
    ):
        pre.verify_standard_2048_spawn_program_preregistration_v16(tampered)
    with pytest.raises(
        pre.ConstructionK7Standard2048SpawnProgramPreregistrationV16Error
    ):
        pre.Standard2048SpawnProgramPreregistrationV16(
            object(), value.canonical_bytes, value.preregistration_id
        )
