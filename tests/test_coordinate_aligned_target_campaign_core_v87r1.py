from acfqp import construction_k7_applicability_target_preregistration_v87 as previous
from acfqp import construction_k7_role_free_relational_transfer_preregistration_v70 as v70
from acfqp.construction_k7_action_applicability_model_v87 import (
    load_action_applicability_model_v87,
)
from acfqp.construction_k7_projected_model_artifact_v86 import (
    load_projected_model_artifact_v86,
)
from acfqp.coordinate_aligned_target_campaign_core_v87r1 import (
    build_coordinate_aligned_target_campaign_document_v87r1,
)


def test_v87r1_core_completes_coordinate_permuted_fixture():
    config = previous.campaign_config_v87()
    config.update(
        target_seeds=(888_881,),
        target_worker_count=1,
        required_target_occurrence_count=1,
        minimum_aligned_completed_target_count=1,
        v87_failed_campaign_id=(
            "e5432505db2bf911324d3d719986493bfa81aa131439ee31367da9329cc2b0d8"
        ),
        v87_failure_verification_id=(
            "d8af2766c723c1b42895f9c4b5d85e2557c366af2ab6473f19516c9b54fe19d5"
        ),
    )
    projected = load_projected_model_artifact_v86()
    applicability = load_action_applicability_model_v87()
    factor_library = v70.previous.previous.previous.previous.previous.previous.previous.FACTOR_LIBRARY
    result = build_coordinate_aligned_target_campaign_document_v87r1(
        config,
        "fixture-preregistration",
        projected["model_artifact_id"],
        applicability["model_artifact_id"],
        projected["projected_disagreement_successor_model"],
        applicability["action_applicability_program"],
        factor_library,
    )
    assert result["registered_gate"]["passed"] is True
    assert result["registered_gate"][
        "actual_coordinate_aligned_completed_target_count"
    ] == 1
    occurrence = result["target_occurrences"][0]
    assert occurrence["coordinate_alignment"]["exact_full_model_projection_count"] == 1
    assert occurrence["incompatible_schema_ood_control"]["status"] == (
        "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_ALIGNMENT_OR_SEARCH"
    )
    assert result["query_local_exact_overlay_only_safety_authority"] is True
    assert result["multi_step_planning_primarily_in_abstract_model_claimed"] is False
    assert result["official_scalar_cost"] is None
