from __future__ import annotations

from acfqp import construction_k7_standard_2048_expression_checkpoint_campaign_v29 as campaign


def test_fourth_checkpoint_source_binding_keeps_zero_additional_labels() -> None:
    binding = campaign._source_binding()
    assert binding["expression_world_model_id"] == campaign.pre.WORLD_MODEL_ID
    assert binding["empty_cache_at_checkpoint_start"] is True
    assert binding["persistent_cache_within_segment"] is True
    assert binding["target_probability_query_count_in_segment"] == 0


def test_fourth_checkpoint_campaign_runs_exact_segment() -> None:
    result = campaign.run_standard_2048_expression_checkpoint_campaign_v29()
    document = result.to_document()
    assert document["episode_count"] == 4
    assert document["segment_decision_count"] == 256
    assert document["cumulative_decision_count_across_episodes"] == 768
    assert document["model_certificate_count"] == 256
    assert document["additional_model_acquisition_label_count"] == 0
    assert document["cold_evaluation_checkpoint_count"] == 12
    assert document["all_checkpoint_root_values_and_actions_exactly_equal"] is True
    assert document["cumulative_certified_decisions_per_acquired_target_label"] == 192
    assert document["official_execution_allowed"] is False
