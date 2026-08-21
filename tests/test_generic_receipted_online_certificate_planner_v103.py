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
from acfqp.generic_receipted_online_certificate_planner_v103 import (
    run_receipted_online_certificate_episode_v103,
)
from acfqp.generic_abstract_execution_receipt_v103 import verify_abstract_execution_receipt_v103


def test_v103_first_episode_emits_exact_execution_receipts():
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
        episode_index=0,
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        confidence_denominator=config["residual_confidence_denominator"],
        maximum_support_branch_evaluations=config[
            "maximum_joint_support_branch_evaluations"
        ],
        support_feasible_beam_width=config["joint_support_feasible_beam_width"],
    )
    meta = run_receipted_online_certificate_episode_v103(
        adapter,
        partial["candidate"],
        partial["rows"],
        structural_prior_library=source,
        **common,
    )
    no_prior = run_receipted_online_certificate_episode_v103(
        adapter,
        partial["candidate"],
        partial["rows"],
        structural_prior_library=None,
        **common,
    )

    assert meta["candidate_activated_at_ground_support_label"] < no_prior[
        "candidate_activated_at_ground_support_label"
    ]
    assert meta["local_ground_support_labels"] == no_prior[
        "local_ground_support_labels"
    ]
    assert meta["agreement_shield_accept_count"] > 0
    assert meta["agreement_shield_disagreement_abstention_count"] > 0
    assert meta["abstract_proposal_can_precede_partial_without_agreement"] is False
    assert meta["all_ground_queries_followed_failed_certificates"] is True
    assert meta["query_local_exact_overlay_exclusively_used_for_safety"] is True
    assert meta["complete_world_model_synthesized"] is False
    assert meta["every_execution_action_has_content_addressed_receipt"] is True
    assert len(meta["abstract_execution_receipts"]) == meta["execution_steps"]
    assert all(
        verify_abstract_execution_receipt_v103(row) == row
        for row in meta["abstract_execution_receipts"]
    )
    assert sum(
        row["chosen_action_matches_admitted_abstract_proposal"]
        for row in meta["abstract_execution_receipts"]
    ) == meta["shielded_joint_execution_action_match_count"]
