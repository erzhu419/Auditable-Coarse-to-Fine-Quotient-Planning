from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_matched_repair_campaign_v19 as campaign
from acfqp import construction_k7_standard_2048_matched_repair_preregistration_v19 as pre
from acfqp.phase3e_ids import canonical_json_bytes, content_id


@pytest.fixture(scope="module")
def result():
    value = campaign.run_standard_2048_matched_repair_campaign_v19()
    assert campaign.verify_standard_2048_matched_repair_campaign_v19(value) is value
    return value


def _decisions(document):
    return [row for episode in document["episodes"] for row in episode["decisions"]]


def test_both_arms_actually_run_and_share_targets(result) -> None:
    document = result.to_document()
    decisions = _decisions(document)
    assert len(decisions) == 12
    assert document["all_12_program_prior_plans_exact"] is True
    assert document["all_12_no_prior_table_plans_exact"] is True
    assert document["all_12_arm_actions_identical"] is True
    assert document["all_12_target_transitions_shared"] is True
    assert all(row["both_arms_exactly_match_cold_target_ground"] for row in decisions)
    assert all(row["certificate_frozen_before_target_transition"] for row in decisions)


def test_program_prior_active_queries_are_minimax_and_persistent(result) -> None:
    document = result.to_document()
    decisions = _decisions(document)
    queries = [
        query
        for row in decisions
        for query in row["program_prior_arm"]["acquisitions"]
    ]
    assert [row["queried_empty_count"] for row in queries] == [2, 5, 3, 4]
    assert [row["candidate_count_after"] for row in queries] == [7, 3, 2, 1]
    assert document["program_prior_failure_count"] == 1
    assert document["program_prior_selected_candidate_key"] == (
        "EMPTY_COUNT_LE_4__RANK_TWO_1_OVER_5"
    )
    assert sum(row["program_prior_arm"]["failure"] is not None for row in decisions) == 1


def test_no_prior_table_actually_queries_every_new_context(result) -> None:
    document = result.to_document()
    decisions = _decisions(document)
    queries = [
        query
        for row in decisions
        for query in row["no_prior_table_arm"]["acquisitions"]
    ]
    assert [row["queried_empty_count"] for row in queries] == list(range(1, 11))
    assert all(row["candidate_count_before"] is None for row in queries)
    assert all(row["candidate_count_after"] is None for row in queries)
    assert document["no_prior_failure_count"] == 3
    assert document["no_prior_final_context_count"] == 10


def test_strict_matched_sample_reduction_is_observed(result) -> None:
    document = result.to_document()
    assert document["program_prior_unique_ground_distinction_query_count"] == 4
    assert document["no_prior_unique_ground_distinction_query_count"] == 10
    assert document["strict_ground_distinction_query_reduction"] == 6
    assert document["program_prior_query_fraction_of_no_prior"].numerator == 2
    assert document["program_prior_query_fraction_of_no_prior"].denominator == 5
    assert document["strict_reduction_observed"] is True
    assert document["matched_active_program_prior_sample_result"] == (
        "POSITIVE_STRICT_GROUND_DISTINCTION_QUERY_REDUCTION"
    )


def test_ground_access_order_quality_and_lane_are_preserved(result) -> None:
    decisions = _decisions(result.to_document())
    for decision in decisions:
        for arm in (decision["program_prior_arm"], decision["no_prior_table_arm"]):
            failure = arm["failure"]
            if failure is not None:
                assert failure["ground_query_count_before_failure"] == 0
                assert failure["target_transition_accessed_before_failure"] is False
                assert all(row["query_after_failure_freeze"] for row in arm["acquisitions"])
            assert arm["certificate"]["ground_query_count_during_planning"] == 0
            assert arm["certificate"]["ground_state_action_row_count"] == 0
            assert arm["all_root_values_exactly_match_cold_target_ground"] is True
            assert arm["selected_action_matches_cold_target_ground"] is True
        control = decision["cold_target_ground_control"]
        assert control["lane"] == "STANDALONE_EVALUATION_ONLY"
        assert control["route_or_certificate_authority"] is False


def test_claims_and_official_gates_remain_locked(result) -> None:
    document = result.to_document()
    assert document["conditional_on_v18_candidate_grammar_and_target_kernel"] is True
    assert document["broad_or_physical_iid_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["full_standard_2048_game_completed"] is False
    assert document["tile_2048_reached"] is False
    assert document["broad_world_model_synthesis_completed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_fully_resigned_arm_tamper_and_caller_mint_are_rejected(result) -> None:
    document = copy.deepcopy(result.to_document())
    document["episodes"][0]["decisions"][0]["program_prior_arm"]["acquisitions"][0][
        "queried_empty_count"
    ] = 1
    payload = {
        key: value for key, value in document.items() if key != "matched_repair_campaign_id"
    }
    forged_id = content_id(pre.FUTURE_DOMAINS["campaign"], payload)
    document["matched_repair_campaign_id"] = forged_id
    forged = copy.copy(result)
    object.__setattr__(forged, "canonical_bytes", canonical_json_bytes(document))
    object.__setattr__(forged, "campaign_id", forged_id)
    with pytest.raises(campaign.ConstructionK7Standard2048MatchedRepairCampaignV19Error):
        campaign.verify_standard_2048_matched_repair_campaign_v19(forged)
    with pytest.raises(campaign.ConstructionK7Standard2048MatchedRepairCampaignV19Error):
        campaign.Standard2048MatchedRepairCampaignV19(
            object(), result.canonical_bytes, result.campaign_id
        )
