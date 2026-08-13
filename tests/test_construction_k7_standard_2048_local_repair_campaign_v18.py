from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_local_repair_campaign_v18 as campaign
from acfqp import construction_k7_standard_2048_local_repair_preregistration_v18 as pre
from acfqp.phase3e_ids import canonical_json_bytes, content_id


@pytest.fixture(scope="module")
def result():
    value = campaign.run_standard_2048_local_repair_campaign_v18()
    assert campaign.verify_standard_2048_local_repair_campaign_v18(value) is value
    return value


def test_certificate_failure_precedes_two_targeted_queries(result) -> None:
    document = result.to_document()
    first = document["episodes"][0]["decisions"][0]
    failure = first["base_failure"]
    assert failure["status"] == "FAILED_BASE_MODEL_APPLICABILITY_CERTIFICATE"
    assert failure["ground_probability_query_count_before_failure"] == 0
    assert failure["target_transition_accessed_before_failure"] is False
    assert first["structural_frontier_empty_counts"] == [1, 2, 3, 4, 5]
    queries = first["local_acquisitions"]
    assert [row["queried_empty_count"] for row in queries] == [5, 4]
    assert [row["candidate_count_after"] for row in queries] == [13, 1]
    assert all(row["query_context_was_in_failed_frontier"] for row in queries)
    assert [row["sequence"] for row in first["route_events"]] == list(range(5))


def test_local_overlay_is_selected_and_reused(result) -> None:
    document = result.to_document()
    overlay = document["persistent_local_repair_overlay"]
    assert overlay["selected_candidate_key"] == "EMPTY_COUNT_LE_4__RANK_TWO_1_OVER_5"
    assert overlay["candidate_version_space_count"] == 1
    assert overlay["ground_distinction_query_count"] == 2
    assert overlay["full_state_action_table_materialized"] is False
    decisions = [row for episode in document["episodes"] for row in episode["decisions"]]
    assert len(decisions) == 12
    assert sum(row["base_failure"] is not None for row in decisions) == 1
    assert all(row["local_repair_overlay_id"] == overlay["local_repair_overlay_id"] for row in decisions)
    assert all(row["certificate"]["ground_probability_query_count_during_planning"] == 0 for row in decisions)


def test_repaired_abstract_plans_exactly_match_cold_target_ground(result) -> None:
    document = result.to_document()
    decisions = [row for episode in document["episodes"] for row in episode["decisions"]]
    assert document["repaired_abstract_model_certificate_count"] == 12
    assert document["operational_ground_state_action_row_count"] == 0
    assert document["all_root_action_values_and_selected_actions_match_cold_target_ground"] is True
    assert all(row["all_root_action_values_exactly_equal"] for row in decisions)
    assert all(row["selected_action_exact_value_and_loss_equivalent"] for row in decisions)
    assert all(row["certificate_frozen_before_target_transition"] for row in decisions)
    assert all(row["matched_cold_target_ground_control"]["lane"] == "STANDALONE_EVALUATION_ONLY" for row in decisions)


def test_registered_program_prior_reduces_only_the_scoped_query_axis(result) -> None:
    document = result.to_document()
    assert document["ground_distinction_query_count"] == 2
    assert document["matched_no_prior_first_failure_frontier_query_count"] == 5
    assert document["program_prior_ground_query_difference"] == 3
    assert document["program_prior_ground_query_fraction"].numerator == 2
    assert document["program_prior_ground_query_fraction"].denominator == 5
    assert document["v16_registered_observation_difference"] == 7040
    assert document["broad_or_physical_iid_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False


def test_claims_and_official_gates_remain_locked(result) -> None:
    document = result.to_document()
    assert document["full_standard_2048_game_completed"] is False
    assert document["tile_2048_reached"] is False
    assert document["broad_world_model_synthesis_completed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_fully_resigned_route_tamper_and_caller_mint_are_rejected(result) -> None:
    document = copy.deepcopy(result.to_document())
    document["episodes"][0]["decisions"][0]["route"] = "GROUND_BEFORE_FAILURE"
    payload = {
        key: value for key, value in document.items() if key != "local_repair_campaign_id"
    }
    forged_id = content_id(pre.FUTURE_DOMAINS["campaign"], payload)
    document["local_repair_campaign_id"] = forged_id
    forged = copy.copy(result)
    object.__setattr__(forged, "canonical_bytes", canonical_json_bytes(document))
    object.__setattr__(forged, "campaign_id", forged_id)
    with pytest.raises(campaign.ConstructionK7Standard2048LocalRepairCampaignV18Error):
        campaign.verify_standard_2048_local_repair_campaign_v18(forged)
    with pytest.raises(campaign.ConstructionK7Standard2048LocalRepairCampaignV18Error):
        campaign.Standard2048LocalRepairCampaignV18(
            object(), result.canonical_bytes, result.campaign_id
        )
