from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_coordinate_preregistration_v13 as p
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_coordinate_preregistration_is_outcome_free_and_frozen() -> None:
    value = p.freeze_standard_2048_coordinate_preregistration_v13()
    assert p.verify_standard_2048_coordinate_preregistration_v13(value) is value
    document = value.to_document()
    assert value.preregistration_id == p.PREREGISTRATION_ID
    assert document["outcome_fields_present"] is False
    assert document["coordinate_basis_selected"] is False
    assert document["target_execution_performed"] is False
    assert document["sample_tax_reduction_claimed"] is False
    assert document["counter_completeness_gate_status"] == "NOT_RUN"


def test_coordinate_grammar_and_selection_are_frozen_before_target() -> None:
    document = p.freeze_standard_2048_coordinate_preregistration_v13().to_document()
    assert len(document["coordinate_candidates"]) == 9
    assert document["coordinate_candidates"][-1]["candidate_key"] == (
        "exact_d4_board_fallback_coordinate"
    )
    selection = document["coordinate_selection_rule"]
    assert selection["query_reward_value_or_policy_access_allowed"] is False
    assert selection["target_episode_access_allowed"] is False
    assert selection["exact_d4_coordinate_forced_into_initial_basis"] is False
    assert document["v171_outcome_or_route_counts_read_before_freeze"] is False


def test_statistical_proposal_cannot_masquerade_as_sound_certificate() -> None:
    document = p.freeze_standard_2048_coordinate_preregistration_v13().to_document()
    dynamics = document["partial_dynamics_contract"]
    assert dynamics["unobserved_successor_mass_retained_as_unknown"] is True
    assert dynamics["statistical_interval_alone_can_issue_sound_plan_certificate"] is False
    assert dynamics["sound_plan_certificate_requires_exact_local_obligation_closure"] is True
    refinement = document["local_refinement_protocol"]
    assert refinement["refinement_only_after_certificate_failure"] is True
    assert refinement["maximum_exact_local_rows_per_decision"] == 4
    assert refinement["maximum_exact_local_rows_campaign"] == 256
    assert refinement["fallback_not_classified_as_infeasible"] is True


def test_fresh_target_and_sample_tax_controls_are_precommitted() -> None:
    document = p.freeze_standard_2048_coordinate_preregistration_v13().to_document()
    target = document["target_workload"]
    assert target["fresh_and_d4_disjoint_from_v169_and_v171"] is True
    assert target["episode_count"] == 4
    assert target["maximum_decision_count"] == 64
    assert len(set(target["episode_seeds"])) == 4
    controls = document["sample_tax_controls"]
    assert controls["coordinate_source_and_validation_count"] == 768
    assert controls["matched_fixed_control_total_observation_count"] == 8192
    assert controls["historical_147456_observation_control_is_diagnostic_only"] is True
    assert controls["strict_no_prior_control_required"] is True
    assert controls["sample_count_not_combined_with_compute_or_bytes_as_scalar"] is True


def test_domains_and_issuer_boundary_reject_tampering() -> None:
    assert len(set(p.FUTURE_DOMAINS.values())) == len(p.FUTURE_DOMAINS)
    assert set(p.FUTURE_DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    value = p.freeze_standard_2048_coordinate_preregistration_v13()
    forged = copy.copy(value)
    object.__setattr__(forged, "preregistration_id", "f" * 64)
    with pytest.raises(
        p.ConstructionK7Standard2048CoordinatePreregistrationV13Error
    ):
        p.verify_standard_2048_coordinate_preregistration_v13(forged)
    with pytest.raises(
        p.ConstructionK7Standard2048CoordinatePreregistrationV13Error
    ):
        p.Standard2048CoordinatePreregistrationV13(
            object(), value.canonical_bytes, value.preregistration_id
        )
