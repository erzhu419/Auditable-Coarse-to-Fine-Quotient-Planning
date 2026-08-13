from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_program_preregistration_v14 as p
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_program_preregistration_is_outcome_free_and_target_blind() -> None:
    value = p.freeze_standard_2048_program_preregistration_v14()
    assert p.verify_standard_2048_program_preregistration_v14(value) is value
    document = value.to_document()
    assert value.preregistration_id == p.PREREGISTRATION_ID
    assert document["outcome_fields_present"] is False
    assert document["v13_target_transition_or_route_outcomes_read_before_freeze"] is False
    assert document["program_selected"] is False
    assert document["exhaustive_line_proof_run"] is False
    assert document["target_execution_performed"] is False
    assert document["sample_tax_reduction_claimed"] is False


def test_program_proposal_and_proof_roles_are_separated() -> None:
    document = p.freeze_standard_2048_program_preregistration_v14().to_document()
    assert len(document["program_candidates"]) == 4
    selection = document["program_selection_rule"]
    assert selection["proposal_has_certificate_authority"] is False
    proof = document["exhaustive_deterministic_proof"]
    assert proof["exhaustive_line_input_count"] == 160000
    assert proof["proof_evaluations_are_compute_not_transition_observation_samples"] is True
    model = document["factored_world_model_contract"]
    assert model["verified_component"] == "DETERMINISTIC_WHOLE_BOARD_SWIPE"
    assert model["unverified_component"] == "STOCHASTIC_SPAWN_SUPPORT_AND_PROBABILITY"
    assert model["program_proof_alone_can_issue_sound_plan_certificate"] is False
    assert model["exact_local_obligation_closure_still_required"] is True


def test_sample_tax_axes_and_local_recovery_are_frozen() -> None:
    document = p.freeze_standard_2048_program_preregistration_v14().to_document()
    sample = document["sample_tax_comparison"]
    assert sample["program_arm_offline_transition_observation_count"] == 768
    assert sample["matched_fixed_control_offline_transition_observation_count"] == 8192
    assert sample["registered_offline_observation_difference"] == 7424
    assert sample["positive_sample_tax_claim_requires_target_action_equivalence"] is True
    assert sample["total_operational_work_saving_claimed"] is False
    recovery = document["local_recovery_contract"]
    assert recovery["only_after_certificate_failure"] is True
    assert recovery["maximum_exact_rows_per_decision"] == 4
    assert recovery["maximum_exact_rows_campaign"] == 256


def test_domains_gate_locks_and_issuer_are_exact() -> None:
    assert len(set(p.FUTURE_DOMAINS.values())) == len(p.FUTURE_DOMAINS)
    assert set(p.FUTURE_DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    value = p.freeze_standard_2048_program_preregistration_v14()
    document = value.to_document()
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    forged = copy.copy(value)
    object.__setattr__(forged, "preregistration_id", "f" * 64)
    with pytest.raises(p.ConstructionK7Standard2048ProgramPreregistrationV14Error):
        p.verify_standard_2048_program_preregistration_v14(forged)
    with pytest.raises(p.ConstructionK7Standard2048ProgramPreregistrationV14Error):
        p.Standard2048ProgramPreregistrationV14(
            object(), value.canonical_bytes, value.preregistration_id
        )
