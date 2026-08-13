from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_synthesized_plan_preregistration_v17 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_preregistration_binds_independently_verified_synthesized_model() -> None:
    value = pre.freeze_standard_2048_synthesized_plan_preregistration_v17()
    assert pre.verify_standard_2048_synthesized_plan_preregistration_v17(value) is value
    document = value.to_document()
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert document["v16_synthesized_world_model_id"] == (
        "492750c86baf5d53f68b7f470a8d5e3f74a7b088dc5767329a5945a90f01f389"
    )
    assert document["v16_independent_verification_id"] == (
        "a6fa6e31d8ee765e4a6c352384baed87ef7a38bba58af7590b85b666e94a8198"
    )
    assert document["v17_target_or_route_outcomes_read_before_freeze"] is False


def test_primary_planner_is_composed_model_only_before_failure() -> None:
    document = pre.freeze_standard_2048_synthesized_plan_preregistration_v17().to_document()
    model = document["model_contract"]
    assert model["swipe_component"].startswith("OBSERVATION_PROPOSED")
    assert model["spawn_component"].startswith("OBSERVATION_PROPOSED")
    assert model["full_state_action_table_present"] is False
    assert model["factored_successor_generation"] is True
    assert model["ground_kernel_access_before_certificate_failure"] is False
    protocol = document["certificate_protocol"]
    assert protocol["planning_horizon"] == 3
    assert protocol["source_closed_ground_step_used_by_certificate"] is False
    assert protocol["local_ground_recovery_only_after_certificate_failure"] is True


def test_fresh_multiepisode_workload_and_matched_control_are_frozen() -> None:
    document = pre.freeze_standard_2048_synthesized_plan_preregistration_v17().to_document()
    target = document["target_workload"]
    assert target["all_target_orbits_distinct"] is True
    assert target["episode_count"] == 4
    assert target["maximum_decisions_per_episode"] == 32
    assert target["maximum_decision_count"] == 128
    control = document["matched_direct_control"]
    assert control["cold_exact_ground_h3_at_every_decision"] is True
    assert control["standalone_evaluation_lane_only"] is True
    assert control["route_or_certificate_authority"] is False


def test_sample_axes_and_gate_locks_are_explicit() -> None:
    document = pre.freeze_standard_2048_synthesized_plan_preregistration_v17().to_document()
    accounting = document["sample_tax_accounting"]
    assert accounting["joint_model_synthesis_transition_observation_count"] == 1152
    assert accounting["additional_model_acquisition_observation_budget"] == 0
    assert accounting["registered_offline_observation_difference"] == 7040
    assert accounting["broad_or_physical_iid_sample_efficiency_claimed"] is False
    assert accounting["total_operational_work_saving_claimed"] is False
    assert document["outcome_fields_present"] is False
    assert document["target_execution_performed"] is False
    assert document["full_standard_2048_game_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_domains_are_registered_and_caller_mint_is_rejected() -> None:
    values = tuple(pre.FUTURE_DOMAINS.values())
    assert len(values) == 5
    assert len(set(values)) == 5
    assert set(values).issubset(PHASE3E_DOMAIN_TAGS)
    value = pre.freeze_standard_2048_synthesized_plan_preregistration_v17()
    forged = copy.copy(value)
    object.__setattr__(forged, "preregistration_id", "f" * 64)
    with pytest.raises(
        pre.ConstructionK7Standard2048SynthesizedPlanPreregistrationV17Error
    ):
        pre.verify_standard_2048_synthesized_plan_preregistration_v17(forged)
    with pytest.raises(
        pre.ConstructionK7Standard2048SynthesizedPlanPreregistrationV17Error
    ):
        pre.Standard2048SynthesizedPlanPreregistrationV17(
            object(), value.canonical_bytes, value.preregistration_id
        )
