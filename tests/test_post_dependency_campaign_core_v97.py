from pathlib import Path

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as pre
from acfqp.construction_k7_post_dependency_source_library_v97 import (
    freeze_post_dependency_source_library_v97,
)
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.post_dependency_campaign_core_v97 import (
    build_post_dependency_occurrence_v97,
)


def test_v97_development_gate_compiles_post_dependency_into_persistent_successor():
    config = pre.campaign_config_v96()
    config.update(target_worker_count=1)
    source = freeze_post_dependency_source_library_v97(
        Path(".tmp/exact-freeze/v96_persistent_multi_residual_campaign.json").read_bytes(),
        Path(".tmp/exact-freeze/v96_persistent_multi_residual_verification.json").read_bytes(),
    ).to_document()
    residual = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    ).to_document()["compiled_library"]
    document = build_post_dependency_occurrence_v97(
        config,
        family="COUPLED_EXCHANGE",
        # The preserved V96 failure is now a development source, never a fresh
        # V97 target identity.
        seed=997_101,
        episode_indices=(21, 22, 23),
        factor_library=pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
        residual_library=residual,
        structural_prior_library=source["compiled_structure_library"],
    )
    assert document["registered_gate"]["passed"] is True
    assert document["meta_prior_persistent_sequence"][
        "retained_post_dependency_candidate_count"
    ] >= 1
    assert document["meta_prior_persistent_sequence"][
        "retained_joint_residual_candidate_count"
    ] >= 2
    assert document["meta_prior_persistent_sequence"][
        "later_post_dependency_abstract_plan_receipt_count"
    ] > 0
    assert document["meta_prior_persistent_sequence"][
        "later_query_ground_support_labels"
    ] == 0
    assert document["accounting"]["meta_prior_lifetime_target_labels"] <= document[
        "accounting"
    ]["no_structure_prior_lifetime_target_labels"]
    assert document["accounting"]["meta_prior_lifetime_target_labels"] < document[
        "accounting"
    ]["strict_cold_direct_lifetime_target_labels"]
    assert document["source_structure_prior_supplied_target_bindings"] is False
    assert document["complete_world_model_synthesized"] is False
    assert document["official_execution_allowed"] is False
