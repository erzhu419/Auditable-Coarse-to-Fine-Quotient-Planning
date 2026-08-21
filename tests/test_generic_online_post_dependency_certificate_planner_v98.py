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
from acfqp.generic_online_post_dependency_certificate_planner_v98 import (
    run_online_post_dependency_certificate_episode_v98,
)


def _development_inputs():
    config = pre.campaign_config_v96()
    source_library = freeze_post_dependency_source_library_v97(
        Path(".tmp/exact-freeze/v96_persistent_multi_residual_campaign.json").read_bytes(),
        Path(
            ".tmp/exact-freeze/v96_persistent_multi_residual_verification.json"
        ).read_bytes(),
    ).to_document()["compiled_structure_library"]
    residual_library = verify_residual_factor_library_v62(
        freeze_residual_factor_library_v62()
    ).to_document()["compiled_library"]
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        "COUPLED_EXCHANGE", 997_101, config
    )
    partial = base.acquire_matched_true_bit_models_v59(
        adapter,
        pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY,
        config,
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    return config, source_library, residual_library, adapter, partial


def test_v98_online_prior_reduces_labels_until_reusable_model_activation():
    config, source, residual, adapter, partial = _development_inputs()
    common = dict(
        residual_prior_library=residual,
        episode_index=21,
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        confidence_denominator=config["residual_confidence_denominator"],
        maximum_support_branch_evaluations=config[
            "maximum_joint_support_branch_evaluations"
        ],
        support_feasible_beam_width=config["joint_support_feasible_beam_width"],
    )
    meta = run_online_post_dependency_certificate_episode_v98(
        adapter,
        partial["candidate"],
        partial["rows"],
        structural_prior_library=source,
        **common,
    )
    no_prior = run_online_post_dependency_certificate_episode_v98(
        adapter,
        partial["candidate"],
        partial["rows"],
        structural_prior_library=None,
        **common,
    )

    assert meta["candidate_activated_at_ground_support_label"] is not None
    assert (
        no_prior["candidate_activated_at_ground_support_label"] is None
        or meta["candidate_activated_at_ground_support_label"]
        < no_prior["candidate_activated_at_ground_support_label"]
    )
    assert meta["required_post_dependency_model_evidence_labels"] < no_prior[
        "required_post_dependency_model_evidence_labels"
    ]
    assert meta["local_ground_support_labels"] <= no_prior[
        "local_ground_support_labels"
    ]
    assert meta["active_post_dependency_acquisition"] is not None
    assert meta["joint_abstract_plan_success_count"] > 0
    assert meta["same_synthesizer_and_stopping_rule_between_prior_arms"] is True
    assert (
        meta["activation_is_fallible_mdl_proposal_not_exact_dynamics_authority"]
        is True
    )
    assert meta["all_ground_queries_followed_failed_certificates"] is True
    assert meta["query_local_exact_overlay_exclusively_used_for_safety"] is True
    assert meta["complete_world_model_synthesized"] is False
