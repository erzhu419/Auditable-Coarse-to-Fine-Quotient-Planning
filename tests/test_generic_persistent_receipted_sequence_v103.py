from pathlib import Path

from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as pre
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.construction_k7_post_dependency_source_library_v97 import (
    freeze_post_dependency_source_library_v97,
)
from acfqp.construction_k7_residual_factor_library_v62 import (
    freeze_residual_factor_library_v62,
    verify_residual_factor_library_v62,
)
from acfqp.generic_persistent_receipted_sequence_v103 import (
    run_persistent_receipted_arm_v103,
)
from acfqp.generic_abstract_execution_receipt_v103 import verify_abstract_execution_receipt_v103


def test_v103_persistent_sequence_receipts_cover_every_execution():
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
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        "MAINTENANCE_CASCADE", 590_543, config
    )
    partial = base.acquire_matched_true_bit_models_v59(
        adapter,
        pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
        config,
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    common = dict(
        residual_prior_library=residual,
        episode_indices=(0, 1),
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        confidence_denominator=config["residual_confidence_denominator"],
        maximum_support_branch_evaluations=config[
            "maximum_joint_support_branch_evaluations"
        ],
        support_feasible_beam_width=config["joint_support_feasible_beam_width"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    meta = run_persistent_receipted_arm_v103(
        adapter,
        partial["candidate"],
        partial["rows"],
        partial["document"]["ground_support_labels"],
        structural_prior_library=source,
        **common,
    )
    no_prior = run_persistent_receipted_arm_v103(
        adapter,
        partial["candidate"],
        partial["rows"],
        partial["document"]["ground_support_labels"],
        structural_prior_library=None,
        **common,
    )

    assert meta[
        "target_model_activation_ground_support_labels_with_right_censoring"
    ] < no_prior[
        "target_model_activation_ground_support_labels_with_right_censoring"
    ]
    assert meta["lifetime_target_ground_support_labels"] == no_prior[
        "lifetime_target_ground_support_labels"
    ]
    assert meta["later_agreement_shield_accept_receipt_count"] > 0
    assert meta["first_agreement_shielded_online_episode"][
        "agreement_shield_disagreement_abstention_count"
    ] > 0
    assert meta["later_post_dependency_abstract_plan_receipt_count"] > 0
    assert meta["abstract_proposal_can_precede_partial_without_agreement"] is False
    assert meta["every_new_ground_query_followed_a_failed_certificate"] is True
    assert meta["complete_world_model_synthesized"] is False
    assert meta["every_execution_action_has_content_addressed_receipt"] is True
    assert meta["abstract_execution_receipt_count"] == sum(
        [meta["first_agreement_shielded_online_episode"]["execution_steps"]]
        + [row["execution_steps"] for row in meta["later_persistent_episodes"]]
    )
    assert all(
        verify_abstract_execution_receipt_v103(row) == row
        for row in meta["all_abstract_execution_receipts"]
    )
