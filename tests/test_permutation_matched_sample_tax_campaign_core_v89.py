from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70
from acfqp.construction_k7_action_applicability_model_v87 import (
    load_action_applicability_model_v87,
)
from acfqp.construction_k7_coordinate_aligned_target_preregistration_v87r1 import (
    campaign_config_v87r1,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    load_projected_model_artifact_v86,
)
from acfqp.permutation_matched_sample_tax_campaign_core_v89 import (
    build_permutation_matched_sample_tax_campaign_document_v89,
)


def test_v89_fixture_reduces_certificate_labels_with_matched_execution():
    config = campaign_config_v87r1()
    config.update(
        target_seeds=(888_887, 888_888),
        target_episode_index=12,
        target_worker_count=2,
        required_target_occurrence_count=2,
        minimum_completed_target_count_v89=2,
        minimum_reduced_target_occurrence_count_v89=2,
        v87r1_campaign_id="33e9d49933e8b2d94169911170732b178095ce55fe52258c6ccfb9d425990739",
        v87r1_verification_id="9a5fdb135fcebe2e4a31077e7a542d9af2338ecb1c2d76eda1e3f4f72eedd29d",
        v88_campaign_id="041f758ee32cb6fdef0b1218a23bdbfe47a115781ef1fc8f9c557a79a7b065b2",
        v88_verification_id="e176b3b775511c2c98e650e99fdb183555833ca5c4638bc7fc5d4b6f998be327",
    )
    projected = load_projected_model_artifact_v86()
    applicability = load_action_applicability_model_v87()
    factor_library = (
        v70.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    )
    result = build_permutation_matched_sample_tax_campaign_document_v89(
        config,
        "fixture-preregistration",
        projected["model_artifact_id"],
        applicability["model_artifact_id"],
        projected["projected_disagreement_successor_model"],
        applicability["action_applicability_program"],
        factor_library,
    )
    assert result["registered_gate"]["passed"] is True
    assert result["registered_gate"]["matched_ground_execution_identical"] is True
    assert result["registered_gate"]["actual_reduced_target_occurrence_count"] == 2
    assert result["sample_tax_reduction_verified"] is True
    assert result["sample_tax_measurement"]["target_labels_avoided"] > 0
    assert result["official_scalar_cost"] is None
