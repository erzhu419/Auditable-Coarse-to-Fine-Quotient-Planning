from acfqp import construction_k7_multi_residual_planning_preregistration_v67 as previous
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.persistent_multi_residual_campaign_core_v96 import (
    build_persistent_multi_residual_occurrence_v96,
)


def test_v96_development_gate_persists_joint_residual_successor_and_exact_overlay():
    config = previous.campaign_config_v67()
    config.update(worker_count=1)
    factor_library = previous.previous.previous.previous.previous.FACTOR_LIBRARY
    residual_library = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    ).to_document()["compiled_library"]
    document = build_persistent_multi_residual_occurrence_v96(
        config,
        family="COUPLED_EXCHANGE",
        seed=682_101,
        episode_indices=(0, 1, 2),
        factor_library=factor_library,
        residual_library=residual_library,
    )
    assert document["registered_gate"]["passed"] is True
    assert document["meta_prior_persistent_sequence"][
        "retained_joint_proposal_count"
    ] >= 2
    assert document["meta_prior_persistent_sequence"][
        "later_joint_abstract_plan_receipt_count"
    ] > 0
    assert document["meta_prior_persistent_sequence"][
        "later_query_ground_support_labels"
    ] == 0
    assert document["no_prior_persistent_sequence"][
        "later_query_ground_support_labels"
    ] == 0
    assert document["accounting"]["meta_prior_lifetime_target_labels"] <= document[
        "accounting"
    ]["no_prior_lifetime_target_labels"]
    assert document["accounting"]["meta_prior_lifetime_target_labels"] < document[
        "accounting"
    ]["strict_cold_direct_lifetime_target_labels"]
    assert document["accounting"]["meta_prior_lifetime_target_labels"] == 36
    assert document["accounting"]["no_prior_lifetime_target_labels"] == 36
    assert document["accounting"]["strict_cold_direct_lifetime_target_labels"] == 57
    assert document["meta_prior_persistent_sequence"][
        "later_joint_abstract_plan_receipt_count"
    ] == 16
    assert document["complete_world_model_synthesized"] is False
    assert document["official_execution_allowed"] is False
