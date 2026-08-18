from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as campaign
from acfqp.generic_persistent_certificate_overlay_planner_v17 import (
    run_persistent_certificate_overlay_episodes_v17,
)


def test_v17_occurrence_overlay_is_certificate_first_and_reused_by_later_episodes():
    config = pre.campaign_config_v59()
    adapter = campaign.predecessor.predecessor.prior_ground._adapter(
        "MAINTENANCE_CASCADE", 590_401, config
    )
    acquisitions = campaign.acquire_matched_true_bit_models_v59(
        adapter, pre.previous.previous.FACTOR_LIBRARY, config
    )
    prior = acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"]
    result = run_persistent_certificate_overlay_episodes_v17(
        adapter,
        prior["candidate"],
        prior["rows"],
        episode_indices=(0, 1, 2),
        maximum_abstract_depth=12,
        maximum_execution_steps=96,
    )
    assert result["success"] is True
    assert result["total_local_ground_support_labels"] > 0
    assert result["amortized_query_label_reduction"] > 0
    assert result["later_episode_ground_query_count"] == 0
    assert result["episodes"][0]["new_local_ground_support_labels"] > 0
    assert all(
        row["new_local_ground_support_labels"] == 0
        for row in result["episodes"][1:]
    )
    assert all(
        failure["ground_query_performed_before_failure"] is False
        for failure in result["failed_certificates"]
    )
    assert all(
        distinction["query_after_failed_certificate"] is True
        for distinction in result["local_distinctions"]
    )
    assert result["occurrence_identity_bound"] is True
    assert result["cross_occurrence_ground_fact_reuse_allowed"] is False
    assert result["complete_residual_world_model_synthesized"] is False
