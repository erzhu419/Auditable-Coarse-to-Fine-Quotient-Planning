from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_synthesized_plan_campaign_v17 as campaign_v17
from acfqp import construction_k7_standard_2048_synthesized_plan_preregistration_v17 as pre
from acfqp.domains.standard_2048 import state_from_board_v1


@pytest.fixture(scope="module")
def campaign() -> campaign_v17.Standard2048SynthesizedPlanCampaignV17:
    return campaign_v17.run_standard_2048_synthesized_plan_campaign_v17()


def test_all_fresh_decisions_are_certified_in_synthesized_model(campaign) -> None:
    assert campaign_v17.verify_standard_2048_synthesized_plan_campaign_v17(campaign) is campaign
    assert campaign.campaign_id == campaign_v17.EXPECTED_CAMPAIGN_ID
    document = campaign.to_document()
    assert document["episode_count"] == 4
    assert document["decision_count"] == 128
    assert document["synthesized_model_certificate_count"] == 128
    assert document["local_ground_recovery_count"] == 0
    assert document["cold_direct_operational_fallback_count"] == 0
    assert document["all_planning_performed_in_synthesized_factored_model"] is True
    assert document["ground_step_v1_used_by_operational_planner"] is False


def test_model_values_and_selected_actions_match_cold_ground(campaign) -> None:
    document = campaign.to_document()
    assert document["all_root_action_values_exactly_equal"] is True
    assert document["all_selected_actions_exact_value_and_loss_equivalent"] is True
    for episode in document["episodes"]:
        assert episode["decision_count"] == 32
        for decision in episode["decisions"]:
            certificate = decision["certificate"]
            assert certificate["status"] == (
                "CERTIFIED_EXACT_SYNTHESIZED_FACTORED_H3_BELLMAN_OPTIMALITY"
            )
            assert certificate["ground_step_v1_accessed_by_certificate"] is False
            assert certificate["matched_direct_accessed_by_certificate"] is False
            assert decision["certificate_frozen_before_target_transition"] is True
            assert decision["matched_cold_direct"]["lane"] == (
                "STANDALONE_EVALUATION_ONLY"
            )


def test_sample_tax_reduction_survives_target_planning(campaign) -> None:
    document = campaign.to_document()
    assert document["joint_model_synthesis_transition_observation_count"] == 1152
    assert document["additional_model_acquisition_observation_count"] == 0
    assert document["matched_fixed_observation_control_count"] == 8192
    assert document["registered_offline_observation_difference"] == 7040
    assert document["registered_observation_axis_reduction_retained"] is True
    assert document["total_operational_work_saving_claimed"] is False
    assert document["broad_or_physical_iid_sample_efficiency_claimed"] is False


def test_synthesized_certificate_cannot_call_ground_step(monkeypatch) -> None:
    state = state_from_board_v1(pre.TARGET_INITIAL_BOARDS[0])
    planner = campaign_v17._SynthesizedPlanner()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("synthesized certificate called ground step")

    monkeypatch.setattr(campaign_v17, "step_v1", forbidden)
    certificate, values = campaign_v17._certificate(0, 0, state, planner)
    assert certificate["selected_action"] is not None
    assert certificate["ground_step_v1_accessed_by_certificate"] is False
    assert values


def test_full_game_and_official_claims_remain_locked(campaign) -> None:
    document = campaign.to_document()
    assert document["full_standard_2048_game_completed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    forged = copy.copy(campaign)
    object.__setattr__(forged, "campaign_id", "f" * 64)
    with pytest.raises(
        campaign_v17.ConstructionK7Standard2048SynthesizedPlanCampaignV17Error
    ):
        campaign_v17.verify_standard_2048_synthesized_plan_campaign_v17(forged)
