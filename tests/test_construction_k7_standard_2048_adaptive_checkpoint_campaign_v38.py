from __future__ import annotations

from acfqp import construction_k7_standard_2048_adaptive_checkpoint_campaign_v38 as campaign


def test_checkpoint_source_binding_keeps_zero_additional_labels() -> None:
    binding = campaign._source_binding()
    assert binding["adaptive_expression_overlay_id"] == (
        campaign.pre.ADAPTIVE_EXPRESSION_OVERLAY_ID
    )
    assert binding["adaptive_expression_proof_id"] == (
        campaign.pre.ADAPTIVE_EXPRESSION_PROOF_ID
    )
    assert binding["empty_cache_at_checkpoint_start"] is True
    assert binding["persistent_cache_within_segment"] is True
    assert binding["target_probability_query_count_in_segment"] == 0


def test_checkpoint_campaign_runs_exact_segment() -> None:
    result = campaign.run_standard_2048_adaptive_checkpoint_campaign_v38()
    document = result.to_document()
    assert document["episode_count"] == 4
    assert 0 < document["segment_decision_count"] <= 1024
    assert document["cumulative_decision_count_across_episodes"] == (
        1024 + document["segment_decision_count"]
    )
    assert document["model_certificate_count"] == document["segment_decision_count"]
    assert document["additional_model_acquisition_label_count"] == 0
    assert 4 <= document["cold_evaluation_checkpoint_count"] <= 12
    assert document["all_checkpoint_root_values_and_actions_exactly_equal"] is True
    assert document["inherited_target_probability_label_count"] == 6
    assert document["strict_no_prior_context_label_count"] == 2400
    assert document["all_segment_planning_bound_to_v35_proof_and_overlay"] is True
    assert document["official_execution_allowed"] is False
