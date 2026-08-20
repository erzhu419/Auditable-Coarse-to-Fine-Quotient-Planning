"""Fresh matched V67 campaign for jointly compiled residual successors."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v67 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_multi_residual_certificate_planner_v26 import (
    run_multi_residual_certificate_episode_v26,
)


class MultiResidualPlanningCampaignCoreV67Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise MultiResidualPlanningCampaignCoreV67Error(message)


def _run_occurrence(args: tuple[Any, ...]) -> dict[str, Any]:
    family, seed, factor_library, residual_library, config = args
    adapter = base.predecessor.predecessor.prior_ground._adapter(family, seed, config)
    partial = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    episodes = {}
    for arm, library in (
        ("RESIDUAL_FACTOR_PRIOR_ON", residual_library),
        ("STRICT_NO_RESIDUAL_FACTOR_PRIOR", None),
    ):
        episodes[arm] = run_multi_residual_certificate_episode_v26(
            adapter,
            partial["candidate"],
            partial["rows"],
            residual_prior_library=library,
            episode_index=0,
            maximum_abstract_depth=config["maximum_abstract_depth"],
            maximum_execution_steps=config["maximum_execution_steps"],
            confidence_denominator=config["residual_confidence_denominator"],
            maximum_joint_support_branch_evaluations=config[
                "maximum_joint_support_branch_evaluations"
            ],
            joint_support_feasible_beam_width=config[
                "joint_support_feasible_beam_width"
            ],
        )
    prior = episodes["RESIDUAL_FACTOR_PRIOR_ON"]
    strict = episodes["STRICT_NO_RESIDUAL_FACTOR_PRIOR"]
    for episode in episodes.values():
        if (
            episode["success"] is not True
            or episode["all_ground_queries_followed_failed_certificates"] is not True
            or episode["query_local_exact_overlay_exclusively_used_for_safety"]
            is not True
            or episode["joint_abstract_plan_used_as_safety_authority"] is not False
            or episode["complete_residual_world_model_synthesized"] is not False
        ):
            _fail("V67 safety boundary changed")
    if prior["partial_candidate_id"] != strict["partial_candidate_id"]:
        _fail("V67 matched partial candidate changed")
    payload = {
        "schema": "acfqp.multi_residual_planning_occurrence.v67",
        "family": family,
        "seed": seed,
        "common_partial_acquisition_id": partial["document"]["acquisition_id"],
        "common_partial_ground_support_labels": partial["document"][
            "ground_support_labels"
        ],
        "prior_episode": prior,
        "strict_episode": strict,
        "matched_environment_seed_episode_partial_candidate_and_observations": True,
        "only_switched_variable": "FROZEN_RESIDUAL_FACTOR_EXPRESSION_PRIOR_CODE_LENGTH",
        "shared_physical_query_pool_not_multiplied_by_residual_target_count": True,
        "joint_residual_model_never_discharges_certificate": True,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v67(
            domains.CONSTRUCTION_K7_MULTI_RESIDUAL_PLANNING_OCCURRENCE_V67_DOMAIN,
            payload,
        ),
    }


def build_multi_residual_planning_campaign_document_v67(
    config: Mapping[str, Any],
    preregistration_id: str,
    v66_campaign_id: str,
    v66_verification_id: str,
    factor_library: Mapping[str, Any],
    residual_library: Mapping[str, Any],
) -> dict[str, Any]:
    arguments = [
        (family, seed, factor_library, residual_library, config)
        for family, seeds in config["target_seeds"].items()
        for seed in seeds
    ]
    if config["worker_count"] == 1:
        occurrences = [_run_occurrence(row) for row in arguments]
    else:
        with ProcessPoolExecutor(max_workers=config["worker_count"]) as executor:
            occurrences = list(executor.map(_run_occurrence, arguments))
    if len(occurrences) != config["target_occurrence_count"]:
        _fail("V67 occurrence inventory changed")
    prior = [row["prior_episode"] for row in occurrences]
    strict = [row["strict_episode"] for row in occurrences]
    prior_joint = sum(row["joint_abstract_plan_success_count"] for row in prior)
    strict_joint = sum(row["joint_abstract_plan_success_count"] for row in strict)
    prior_multi_occurrences = sum(
        row["maximum_simultaneously_compilable_residual_proposal_count"] >= 2
        for row in prior
    )
    strict_multi_occurrences = sum(
        row["maximum_simultaneously_compilable_residual_proposal_count"] >= 2
        for row in strict
    )
    gate_passed = prior_joint > 0 and prior_multi_occurrences > 0
    family_projections = {}
    for family in config["target_seeds"]:
        selected = [row for row in occurrences if row["family"] == family]
        family_projections[family] = {
            "occurrence_count": len(selected),
            "prior_joint_abstract_plan_success_count": sum(
                row["prior_episode"]["joint_abstract_plan_success_count"]
                for row in selected
            ),
            "strict_joint_abstract_plan_success_count": sum(
                row["strict_episode"]["joint_abstract_plan_success_count"]
                for row in selected
            ),
            "prior_multi_proposal_occurrence_count": sum(
                row["prior_episode"][
                    "maximum_simultaneously_compilable_residual_proposal_count"
                ]
                >= 2
                for row in selected
            ),
            "strict_multi_proposal_occurrence_count": sum(
                row["strict_episode"][
                    "maximum_simultaneously_compilable_residual_proposal_count"
                ]
                >= 2
                for row in selected
            ),
            "prior_certificate_local_labels": sum(
                row["prior_episode"]["local_ground_support_labels"]
                for row in selected
            ),
            "strict_certificate_local_labels": sum(
                row["strict_episode"]["local_ground_support_labels"]
                for row in selected
            ),
        }
    accounting = {
        "offline_residual_library_labels": config["offline_library_labels"],
        "common_partial_acquisition_labels": sum(
            row["common_partial_ground_support_labels"] for row in occurrences
        ),
        "prior_certificate_local_labels": sum(
            row["local_ground_support_labels"] for row in prior
        ),
        "strict_certificate_local_labels": sum(
            row["local_ground_support_labels"] for row in strict
        ),
        "prior_execution_steps": sum(row["execution_steps"] for row in prior),
        "strict_execution_steps": sum(row["execution_steps"] for row in strict),
        "prior_partial_planning_compute_events": sum(
            row["partial_planning_compute_events"] for row in prior
        ),
        "strict_partial_planning_compute_events": sum(
            row["partial_planning_compute_events"] for row in strict
        ),
        "prior_joint_abstract_support_branch_evaluations": sum(
            row["joint_abstract_support_branch_evaluations"] for row in prior
        ),
        "strict_joint_abstract_support_branch_evaluations": sum(
            row["joint_abstract_support_branch_evaluations"] for row in strict
        ),
        "prior_multi_residual_synthesis_attempts": sum(
            row["multi_residual_synthesis_attempt_count"] for row in prior
        ),
        "strict_multi_residual_synthesis_attempts": sum(
            row["multi_residual_synthesis_attempt_count"] for row in strict
        ),
        "all_axes_separate": True,
    }
    payload = {
        "schema": "acfqp.multi_residual_planning_campaign.v67",
        "preregistration_id": preregistration_id,
        "v66_campaign_id": v66_campaign_id,
        "v66_verification_id": v66_verification_id,
        "occurrences": occurrences,
        "accounting": accounting,
        "family_projections": family_projections,
        "registered_joint_planning_gate": {
            "prior_joint_abstract_plan_success_count": prior_joint,
            "strict_joint_abstract_plan_success_count": strict_joint,
            "prior_multi_proposal_occurrence_count": prior_multi_occurrences,
            "strict_multi_proposal_occurrence_count": strict_multi_occurrences,
            "required_relation": "PRIOR_JOINT_GT_ZERO_AND_PRIOR_MULTI_OCCURRENCES_GT_ZERO",
            "passed": gate_passed,
            "prior_vs_strict_improvement_required": False,
            "certificate_local_label_reduction_required": False,
        },
        "multiple_residual_proposals_jointly_compiled_when_available": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "joint_abstract_plan_used_as_safety_authority": False,
        "producer_free_verification_present": False,
        "complete_residual_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "campaign_id": domains.extension_content_id_v67(
            domains.CONSTRUCTION_K7_MULTI_RESIDUAL_PLANNING_CAMPAIGN_V67_DOMAIN,
            payload,
        ),
    }
    if not gate_passed:
        _fail(
            "V67 registered joint-planning Gate failed: "
            f"prior_joint={prior_joint} prior_multi={prior_multi_occurrences} "
            f"failed_campaign_id={document['campaign_id']}"
        )
    return document


__all__ = (
    "MultiResidualPlanningCampaignCoreV67Error",
    "build_multi_residual_planning_campaign_document_v67",
)
