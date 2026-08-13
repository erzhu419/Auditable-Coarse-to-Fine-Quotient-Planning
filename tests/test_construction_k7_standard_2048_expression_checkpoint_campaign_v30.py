from __future__ import annotations

from fractions import Fraction

from acfqp import construction_k7_standard_2048_expression_checkpoint_campaign_v30 as campaign


def test_fifth_checkpoint_source_binding_keeps_zero_additional_labels() -> None:
    binding = campaign._source_binding()
    assert binding["expression_world_model_id"] == campaign.pre.WORLD_MODEL_ID
    assert binding["empty_cache_at_checkpoint_start"] is True
    assert binding["persistent_cache_within_segment"] is True
    assert binding["target_probability_query_count_in_segment"] == 0


def test_fifth_checkpoint_campaign_runs_exact_segment() -> None:
    result = campaign.run_standard_2048_expression_checkpoint_campaign_v30()
    document = result.to_document()
    assert document["episode_count"] == 4
    assert 0 < document["segment_decision_count"] <= 512
    assert document["cumulative_decision_count_across_episodes"] == (
        768 + document["segment_decision_count"]
    )
    assert document["model_certificate_count"] == document["segment_decision_count"]
    assert document["additional_model_acquisition_label_count"] == 0
    assert 4 <= document["cold_evaluation_checkpoint_count"] <= 12
    assert document["all_checkpoint_root_values_and_actions_exactly_equal"] is True
    assert document["cumulative_certified_decisions_per_acquired_target_label"] == (
        Fraction(document["cumulative_decision_count_across_episodes"], 4)
    )
    assert document["official_execution_allowed"] is False
