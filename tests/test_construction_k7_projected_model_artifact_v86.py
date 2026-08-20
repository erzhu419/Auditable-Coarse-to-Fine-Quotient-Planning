from acfqp.construction_k7_projected_model_artifact_v86 import (
    MODEL_ARTIFACT_ID,
    MODEL_ID,
    load_projected_model_artifact_v86,
)


def test_v86_model_artifact_is_source_frozen_and_negative_authority():
    document = load_projected_model_artifact_v86()
    assert document["model_artifact_id"] == MODEL_ARTIFACT_ID
    assert document["projected_disagreement_successor_model_id"] == MODEL_ID
    assert document["source_member_count"] == 4
    assert document["model_frozen_before_any_v86_target_outcome"] is True
    assert document["target_outcomes_used_to_select_or_refit_model"] is False
    assert document["abstract_plan_safety_authority_present"] is False
    assert document["official_execution_allowed"] is False
