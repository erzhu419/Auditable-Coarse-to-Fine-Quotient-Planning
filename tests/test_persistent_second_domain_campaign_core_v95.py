from acfqp import construction_k7_domain_registry_extension_v94 as v94_domains
from acfqp import construction_k7_domain_registry_extension_v95 as domains
from acfqp import construction_k7_permutation_matched_sample_tax_preregistration_v89 as previous
from acfqp.construction_k7_action_applicability_model_v87 import (
    load_action_applicability_model_v87,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    load_projected_model_artifact_v86,
)
from acfqp.persistent_second_domain_campaign_core_v95 import (
    build_persistent_second_domain_campaign_document_v95,
)


def test_v95_domains_are_fresh_and_disjoint_from_v94():
    assert len(domains.K7_DOMAIN_TAG_EXTENSION_V95) == 6
    assert domains.K7_DOMAIN_TAG_EXTENSION_V95.isdisjoint(
        v94_domains.K7_DOMAIN_TAG_EXTENSION_V94
    )


def test_v95_development_gate_closes_only_after_persistent_reuse():
    config = previous.campaign_config_v89()
    config.update(
        target_seeds=(929_101,),
        target_worker_count=1,
        required_target_occurrence_count=1,
        source_meta_prior_odds=16,
        confidence_denominator=4,
        maximum_applicability_ground_support_labels=40,
        maximum_incremental_certificate_ground_support_labels=100_000,
        target_episode_indices=(13, 14),
    )
    projected = load_projected_model_artifact_v86()
    applicability = load_action_applicability_model_v87()
    document = build_persistent_second_domain_campaign_document_v95(
        config,
        preregistration_id="1" * 64,
        v94_campaign_id="2" * 64,
        v94_verification_id="3" * 64,
        projected_model_artifact_id="4" * 64,
        applicability_model_artifact_id="5" * 64,
        model=projected["projected_disagreement_successor_model"],
        applicability=applicability["action_applicability_program"],
    )
    assert document["registered_gate"]["passed"] is True
    assert document["accounting"]["meta_prior_lifetime_unique_target_labels"] == 50
    assert document["accounting"]["no_prior_lifetime_unique_target_labels"] == 58
    assert document["accounting"]["strict_cold_direct_lifetime_target_labels"] == 146
    assert document["target_occurrences"][0]["meta_prior_persistent_sequence"][
        "transfer_episodes"
    ][1]["new_certificate_labels_charged_this_episode"] == 0
    assert document[
        "sample_tax_reduction_replicated_in_second_registered_domain"
    ] is True
    assert document[
        "sample_tax_reduction_generalized_beyond_two_registered_domain_families"
    ] is False
    assert document["complete_world_model_synthesized"] is False
    assert document["official_execution_allowed"] is False
