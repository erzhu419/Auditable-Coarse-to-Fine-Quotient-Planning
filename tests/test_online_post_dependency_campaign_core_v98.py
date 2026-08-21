from pathlib import Path

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as pre
from acfqp.construction_k7_post_dependency_source_library_v97 import (
    freeze_post_dependency_source_library_v97,
)
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.online_post_dependency_campaign_core_v98 import (
    build_online_post_dependency_occurrence_v98,
)


def test_v98_development_occurrence_reduces_model_activation_sample_tax():
    config = pre.campaign_config_v96()
    source = freeze_post_dependency_source_library_v97(
        Path(".tmp/exact-freeze/v96_persistent_multi_residual_campaign.json").read_bytes(),
        Path(
            ".tmp/exact-freeze/v96_persistent_multi_residual_verification.json"
        ).read_bytes(),
    ).to_document()["compiled_structure_library"]
    residual = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    ).to_document()["compiled_library"]
    document = build_online_post_dependency_occurrence_v98(
        config,
        family="COUPLED_EXCHANGE",
        seed=997_101,
        episode_indices=(21, 22),
        factor_library=pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
        residual_library=residual,
        structural_prior_library=source,
    )

    assert document["registered_gate"]["passed"] is True
    assert document["post_dependency_candidate_count"] > 0
    assert document[
        "dependency_occurrence_has_strict_activation_advantage"
    ] is True
    assert document["accounting"][
        "meta_model_activation_target_labels_with_right_censoring"
    ] < document["accounting"][
        "no_prior_model_activation_target_labels_with_right_censoring"
    ]
    assert document["meta_prior_persistent_sequence"][
        "later_post_dependency_abstract_plan_receipt_count"
    ] > 0
    assert document["persistent_exact_overlay_exclusively_used_for_safety"] is True
    assert document["complete_world_model_synthesized"] is False
    assert document["official_execution_allowed"] is False
