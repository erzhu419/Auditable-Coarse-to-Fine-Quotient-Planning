from acfqp import construction_k7_domain_registry_extension_v91r2 as domains
from acfqp import construction_k7_occurrence_balanced_source_preregistration_v91r1 as old
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as v59
from acfqp.generic_prior_only_partial_acquisition_v67 import (
    acquire_prior_only_partial_candidate_v67,
)


def test_v67_prior_only_closes_the_preserved_v91r1_upstream_blocker():
    config = old.campaign_config_v91r1()
    adapter = v59.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        "COUPLED_EXCHANGE", 931101, config
    )
    result = acquire_prior_only_partial_candidate_v67(
        adapter,
        maximum_ground_support_labels=160,
        global_alpha_denominator=config["global_alpha_denominator"],
        minimum_factor_assignment_count=config["minimum_reusable_factor_count"],
        layout_domain=config["generic_domains"]["layout"],
        acquisition_domain=(
            domains.CONSTRUCTION_K7_PRIOR_ONLY_OCCURRENCE_SOURCE_PARTIAL_ACQUISITION_V91R2_DOMAIN
        ),
        content_id=domains.extension_content_id_v91r2,
    )
    document = result["document"]
    assert document["ground_support_labels"] <= 160
    assert document["strict_no_prior_arm_executed"] is False
    assert document["matched_sample_tax_comparison_claimed"] is False
    assert document["complete_world_model_claimed"] is False
    assert document["proposal_used_as_safety_authority"] is False
