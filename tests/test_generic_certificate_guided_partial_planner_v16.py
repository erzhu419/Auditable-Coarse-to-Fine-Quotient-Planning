from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as campaign
from acfqp.generic_certificate_guided_partial_planner_v16 import (
    run_certificate_guided_partial_episode_v16,
)


def test_v16_queries_only_after_certificates_and_builds_robust_local_overlay():
    config = pre.campaign_config_v59()
    cases = (
        ("BALANCED_BATCH_REFINEMENT", 590_101),
        ("COUPLED_EXCHANGE", 590_201),
        ("MAINTENANCE_CASCADE", 590_301),
    )
    for family, seed in cases:
        adapter = campaign.predecessor.predecessor.prior_ground._adapter(
            family, seed, config
        )
        acquisitions = campaign.acquire_matched_true_bit_models_v59(
            adapter, pre.previous.previous.FACTOR_LIBRARY, config
        )
        prior = acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"]
        episode = run_certificate_guided_partial_episode_v16(
            adapter,
            prior["candidate"],
            prior["rows"],
            episode_index=0,
            maximum_abstract_depth=12,
            maximum_execution_steps=96,
        )
        assert episode["success"] is True
        assert episode["all_ground_queries_followed_failed_certificates"] is True
        assert episode["stream_prefix_residual_recovery_consumed"] is False
        assert episode["complete_residual_world_model_synthesized"] is False
        assert episode["local_ground_support_labels"] == len(
            episode["local_distinctions"]
        )
