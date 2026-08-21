from pathlib import Path

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as pre
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    build_agreement_shielded_occurrence_v99,
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.construction_k7_post_dependency_source_library_v97 import (
    freeze_post_dependency_source_library_v97,
)
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)


def test_v99_incompatible_schema_is_rejected_without_target_outcomes():
    control = incompatible_schema_no_transfer_control_v99()
    assert control["exact_interface_match"] is False
    assert control["learned_structure_prior_delivered"] is False
    assert control["target_binding_search_started"] is False
    assert control["target_outcomes_accessed"] is False
    assert control["strict_ood_no_transfer"] is True


def test_v99_development_occurrence_shields_cross_family_negative_transfer():
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
    document = build_agreement_shielded_occurrence_v99(
        config,
        family="MAINTENANCE_CASCADE",
        seed=590_543,
        episode_indices=(0, 1),
        factor_library=pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
        residual_library=residual,
        structural_prior_library=source,
    )

    assert document["registered_gate"]["passed"] is True
    assert document["cross_family_structure_transfer"] is True
    assert document["post_dependency_candidate_count"] > 0
    assert document["registered_gate"][
        "model_activation_strictly_earlier_than_no_prior"
    ] is True
    assert document["accounting"]["meta_lifetime_target_labels"] <= document[
        "accounting"
    ]["no_prior_lifetime_target_labels"]
    assert document["registered_gate"]["agreement_shield_exercised"] is True
    assert document["abstract_model_used_only_after_partial_agreement"] is True
    assert document["abstract_or_partial_model_used_as_safety_authority"] is False
    assert document["complete_world_model_synthesized"] is False
