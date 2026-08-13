from __future__ import annotations

from acfqp import construction_k7_standard_2048_expression_accounted_campaign_v24 as campaign


def test_instrumented_model_synthesis_uses_four_actual_label_queries() -> None:
    trace, acquisition, proof = campaign._instrumented_model_synthesis("OPERATIONAL")
    assert trace["structural_pool"]["blind_structural_pool_id"] == campaign.EXPECTED_STRUCTURAL_POOL_ID
    assert trace["proposal"]["blind_expression_proposal_id"] == campaign.EXPECTED_PROPOSAL_ID
    assert trace["proof"]["blind_expression_proof_id"] == campaign.EXPECTED_PROOF_ID
    assert trace["world_model"]["blind_expression_world_model_id"] == campaign.EXPECTED_WORLD_MODEL_ID
    assert trace["unique_target_probability_labels"] == 4
    assert trace["actual_target_probability_query_invocations"] == 4
    assert trace["duplicate_label_query_for_artifact_recording"] is False
    assert acquisition["model.structural_expression_value_evaluations"] == 224
    assert acquisition["model.expression_candidates_materialized"] == 80
    assert acquisition["model.candidate_label_consistency_checks"] == 142
    assert acquisition["model.active_query_partition_evaluations"] == 399
    assert proof["model.exact_program_proof_rows_evaluated"] == 17
    assert proof["model.world_model_freezes"] == 1


def test_independent_model_replay_is_evaluation_only() -> None:
    trace, evaluation, empty = campaign._instrumented_model_synthesis("EVALUATION")
    assert trace["actual_target_probability_query_invocations"] == 4
    assert evaluation["evaluation.target_probability_labels_acquired"] == 4
    assert evaluation["evaluation.structural_expression_value_evaluations"] == 224
    assert evaluation["evaluation.exact_program_proof_rows_evaluated"] == 17
    assert evaluation["evaluation.world_model_freezes"] == 1
    assert all(value == 0 for path, value in evaluation.items() if path.startswith("model."))
    assert all(value == 0 for value in empty.values())
