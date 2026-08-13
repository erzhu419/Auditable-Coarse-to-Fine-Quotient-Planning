from __future__ import annotations

from fractions import Fraction

from acfqp import construction_k7_standard_2048_expression_checkpoint_campaign_v33 as campaign


def test_eighth_checkpoint_source_binding_keeps_zero_additional_labels() -> None:
    binding = campaign._source_binding()
    assert binding["expression_world_model_id"] == campaign.pre.WORLD_MODEL_ID
    assert binding["empty_cache_at_checkpoint_start"] is True
    assert binding["persistent_cache_within_segment"] is True
    assert binding["target_probability_query_count_in_segment"] == 0


def test_eighth_checkpoint_campaign_preserves_all_occurrences() -> None:
    result = campaign.run_standard_2048_expression_checkpoint_campaign_v33()
    document = result.to_document()
    assert document["episode_count"] == 4
    assert document["source_terminal_occurrence_count"] == 2
    assert 0 < document["segment_decision_count"] <= 512
    assert document["cumulative_decision_count_across_episodes"] == (
        sum(campaign.pre.SOURCE_DECISION_COUNTS) + document["segment_decision_count"]
    )
    assert document["model_certificate_count"] == document["segment_decision_count"]
    assert document["additional_model_acquisition_label_count"] == 0
    assert 2 <= document["cold_evaluation_checkpoint_count"] <= 6
    assert document["all_checkpoint_root_values_and_actions_exactly_equal"] is True
    assert document["cumulative_certified_decisions_per_acquired_target_label"] == Fraction(
        document["cumulative_decision_count_across_episodes"], 4
    )
    assert document["episodes"][1]["segment_decision_count"] == 0
    assert document["episodes"][1]["closure_reason"] == "TERMINAL_STATE"
    assert document["episodes"][2]["segment_decision_count"] == 0
    assert document["episodes"][2]["closure_reason"] == "TERMINAL_STATE"
    assert document["episodes"][0]["final_state"]["status"] == "WON"
    assert document["episodes"][3]["final_state"]["status"] == "WON"
    assert document["tile_2048_reached"] is True
    assert document["full_standard_2048_game_completed"] is True
    assert document["official_execution_allowed"] is False
