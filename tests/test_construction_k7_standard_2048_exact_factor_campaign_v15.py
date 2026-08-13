from __future__ import annotations

import copy
import hashlib

import pytest

from acfqp import construction_k7_standard_2048_exact_factor_campaign_v15 as campaign_v15
from acfqp import construction_k7_standard_2048_exact_factor_preregistration_v15 as pre
from acfqp.domains.standard_2048 import state_from_board_v1


@pytest.fixture(scope="module")
def campaign() -> campaign_v15.Standard2048ExactFactorCampaignV15:
    return campaign_v15.run_standard_2048_exact_factor_campaign_v15()


def test_source_closure_binds_synthesized_swipe_and_exact_spawn(campaign) -> None:
    document = campaign.to_document()
    assert campaign.campaign_id == campaign_v15.EXPECTED_CAMPAIGN_ID
    closure = document["exact_factor_source_closure"]
    source_bytes = bytes.fromhex(closure["source_bytes_hex"])
    assert len(source_bytes) == pre.STANDARD_2048_SOURCE_BYTE_COUNT
    assert hashlib.sha256(source_bytes).hexdigest() == pre.STANDARD_2048_SOURCE_SHA256
    assert closure["v14_program_line_proof_id"] == pre.V14_PROGRAM_LINE_PROOF_ID
    assert closure["v14_factored_world_model_id"] == pre.V14_FACTORED_WORLD_MODEL_ID
    assert closure["spawn_cell_law"] == "UNIFORM_OVER_ALL_POST_SWIPE_EMPTY_CELLS"
    assert closure["target_identity_or_transition_bytes_present"] is False


def test_all_registered_multistep_plans_are_model_certified_and_exact(campaign) -> None:
    assert campaign_v15.verify_standard_2048_exact_factor_campaign_v15(campaign) is campaign
    document = campaign.to_document()
    assert document["episode_count"] == 4
    assert document["decision_count"] == 64
    assert document["exact_factored_certificate_count"] == 64
    assert document["local_ground_recovery_count"] == 0
    assert document["cold_direct_operational_fallback_count"] == 0
    assert document["factored_action_row_evaluation_count"] == 319506
    assert document["factored_support_outcome_evaluation_count"] == 7007978
    assert document["evaluation_cold_direct_ground_state_action_row_count"] == 319506
    assert document["evaluation_cold_direct_ground_outcome_count"] == 7007978
    assert document["all_planning_performed_in_exact_factored_model"] is True
    assert document["ground_step_v1_used_by_operational_planner"] is False
    assert document["all_root_action_values_exactly_equal"] is True
    assert document["all_selected_actions_exact_value_and_loss_equivalent"] is True
    assert all(episode["decision_count"] == 16 for episode in document["episodes"])


def test_each_certificate_precedes_execution_and_direct_is_evaluation_only(campaign) -> None:
    for episode in campaign.to_document()["episodes"]:
        for decision in episode["decisions"]:
            certificate = decision["certificate"]
            assert certificate["status"] == (
                "CERTIFIED_EXACT_FACTORED_H3_BELLMAN_OPTIMALITY"
            )
            assert certificate["planning_horizon"] == 3
            assert certificate["ground_step_v1_accessed_by_certificate"] is False
            assert certificate["matched_direct_accessed_by_certificate"] is False
            assert certificate["target_transition_accessed_before_certificate_freeze"] is False
            assert decision["certificate_frozen_before_target_transition"] is True
            assert decision["route"] == "EXACT_FACTORED_MODEL_CERTIFIED"
            assert decision["operational_ground_state_action_row_count"] == 0
            assert decision["matched_cold_direct"]["lane"] == "STANDALONE_EVALUATION_ONLY"
            assert decision["matched_cold_direct"]["route_or_certificate_authority"] is False
            assert decision["all_root_action_values_exactly_equal"] is True


def test_factored_certificate_does_not_call_ground_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = state_from_board_v1(tuple(pre.v13.TARGET_INITIAL_BOARDS[0]))
    planner = campaign_v15._FactoredPlanner()

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("operational factored certificate called step_v1")

    monkeypatch.setattr(campaign_v15, "step_v1", forbidden)
    certificate, values = campaign_v15._certificate_document(
        episode_index=0,
        decision_index=0,
        state=state,
        source_closure_id="a" * 64,
        planner=planner,
    )
    assert certificate["selected_action"] is not None
    assert len(values) == 3


def test_registered_sample_tax_reduction_is_scoped_and_axis_separated(campaign) -> None:
    document = campaign.to_document()
    assert document["program_arm_offline_transition_observation_count"] == 768
    assert document["matched_fixed_observation_control_count"] == 8192
    assert document["offline_transition_observation_saving"] == 7424
    assert document["online_target_transition_observation_count"] == 64
    assert document["program_proof_compute_evaluation_count"] == 160000
    assert document["observation_compute_ground_and_target_axes_reported_separately"] is True
    assert document["registered_sample_tax_outcome"] == (
        "POSITIVE_CONDITIONAL_SOURCE_CLOSED_SAMPLE_TAX_RESULT"
    )
    assert document["sample_tax_reduced_on_registered_offline_observation_axis"] is True
    assert document["conditional_on_source_closed_standard_2048_family"] is True
    assert document["total_operational_work_saving_claimed"] is False
    assert document["broad_domain_or_physical_iid_sample_efficiency_claimed"] is False


def test_full_game_and_official_gate_claims_remain_locked(campaign) -> None:
    document = campaign.to_document()
    assert document["full_standard_2048_game_completed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    forged = copy.copy(campaign)
    object.__setattr__(forged, "campaign_id", "f" * 64)
    with pytest.raises(campaign_v15.ConstructionK7Standard2048ExactFactorCampaignV15Error):
        campaign_v15.verify_standard_2048_exact_factor_campaign_v15(forged)
    with pytest.raises(campaign_v15.ConstructionK7Standard2048ExactFactorCampaignV15Error):
        campaign_v15.Standard2048ExactFactorCampaignV15(
            object(), campaign.canonical_bytes, campaign.campaign_id
        )
