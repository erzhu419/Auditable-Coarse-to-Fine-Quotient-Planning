"""Fresh matched campaign for V23 combined-model certificate planning."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v66 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_combined_model_certificate_planner_v23 import (
    run_combined_model_certificate_episode_v23,
)


class CombinedModelPlanningCampaignCoreV66Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise CombinedModelPlanningCampaignCoreV66Error(message)


def _run_occurrence(args: tuple[Any, ...]) -> dict[str, Any]:
    family, seed, factor_library, residual_library, config = args
    adapter = base.predecessor.predecessor.prior_ground._adapter(
        family, seed, config
    )
    partial = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    episodes = {}
    for arm, library in (
        ("RESIDUAL_FACTOR_PRIOR_ON", residual_library),
        ("STRICT_NO_RESIDUAL_FACTOR_PRIOR", None),
    ):
        episodes[arm] = run_combined_model_certificate_episode_v23(
            adapter,
            partial["candidate"],
            partial["rows"],
            residual_prior_library=library,
            episode_index=0,
            maximum_abstract_depth=config["maximum_abstract_depth"],
            maximum_execution_steps=config["maximum_execution_steps"],
            confidence_denominator=config["residual_confidence_denominator"],
            maximum_combined_support_branch_evaluations=config[
                "maximum_combined_support_branch_evaluations"
            ],
            combined_support_feasible_beam_width=config[
                "combined_support_feasible_beam_width"
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
            or episode["combined_abstract_plan_used_as_safety_authority"] is not False
        ):
            _fail("V66 safety boundary changed")
    if prior["partial_candidate_id"] != strict["partial_candidate_id"]:
        _fail("V66 matched partial candidate changed")
    payload = {
        "schema": "acfqp.combined_model_planning_occurrence.v66",
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
        "action_trajectories_required_to_match": False,
        "combined_model_never_discharges_certificate": True,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v66(
            domains.CONSTRUCTION_K7_COMBINED_MODEL_PLANNING_OCCURRENCE_V66_DOMAIN,
            payload,
        ),
    }


def build_combined_model_planning_campaign_document_v66(
    config: Mapping[str, Any],
    preregistration_id: str,
    v65_campaign_id: str,
    v65_verification_id: str,
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
        _fail("V66 occurrence inventory changed")
    prior_episodes = [row["prior_episode"] for row in occurrences]
    strict_episodes = [row["strict_episode"] for row in occurrences]
    prior_combined = sum(
        row["combined_abstract_plan_success_count"] for row in prior_episodes
    )
    strict_combined = sum(
        row["combined_abstract_plan_success_count"] for row in strict_episodes
    )
    gate_passed = prior_combined > 0 and prior_combined >= strict_combined
    family_projections = {}
    for family in config["target_seeds"]:
        selected = [row for row in occurrences if row["family"] == family]
        family_projections[family] = {
            "occurrence_count": len(selected),
            "prior_combined_abstract_plan_success_count": sum(
                row["prior_episode"]["combined_abstract_plan_success_count"]
                for row in selected
            ),
            "strict_combined_abstract_plan_success_count": sum(
                row["strict_episode"]["combined_abstract_plan_success_count"]
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
    payload = {
        "schema": "acfqp.combined_model_planning_campaign.v66",
        "preregistration_id": preregistration_id,
        "v65_campaign_id": v65_campaign_id,
        "v65_verification_id": v65_verification_id,
        "occurrences": occurrences,
        "accounting": {
            "offline_residual_library_labels": config["offline_library_labels"],
            "common_partial_acquisition_labels": sum(
                row["common_partial_ground_support_labels"] for row in occurrences
            ),
            "prior_certificate_local_labels": sum(
                row["local_ground_support_labels"] for row in prior_episodes
            ),
            "strict_certificate_local_labels": sum(
                row["local_ground_support_labels"] for row in strict_episodes
            ),
            "prior_execution_steps": sum(
                row["execution_steps"] for row in prior_episodes
            ),
            "strict_execution_steps": sum(
                row["execution_steps"] for row in strict_episodes
            ),
            "prior_partial_planning_compute_events": sum(
                row["partial_planning_compute_events"] for row in prior_episodes
            ),
            "strict_partial_planning_compute_events": sum(
                row["partial_planning_compute_events"] for row in strict_episodes
            ),
            "prior_combined_abstract_support_branch_evaluations": sum(
                row["combined_abstract_support_branch_evaluations"]
                for row in prior_episodes
            ),
            "strict_combined_abstract_support_branch_evaluations": sum(
                row["combined_abstract_support_branch_evaluations"]
                for row in strict_episodes
            ),
            "prior_residual_synthesis_attempts": sum(
                row["residual_synthesis_attempt_count"] for row in prior_episodes
            ),
            "strict_residual_synthesis_attempts": sum(
                row["residual_synthesis_attempt_count"] for row in strict_episodes
            ),
            "all_axes_separate": True,
        },
        "family_projections": family_projections,
        "registered_combined_planning_gate": {
            "prior_combined_abstract_plan_success_count": prior_combined,
            "strict_combined_abstract_plan_success_count": strict_combined,
            "required_relation": "PRIOR_GT_ZERO_AND_PRIOR_GE_STRICT",
            "passed": gate_passed,
            "certificate_local_label_reduction_required": False,
        },
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "combined_abstract_plan_used_as_safety_authority": False,
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
        "campaign_id": domains.extension_content_id_v66(
            domains.CONSTRUCTION_K7_COMBINED_MODEL_PLANNING_CAMPAIGN_V66_DOMAIN,
            payload,
        ),
    }
    if not gate_passed:
        _fail(
            "V66 registered combined-planning Gate failed: "
            f"prior={prior_combined} strict={strict_combined} "
            f"failed_campaign_id={document['campaign_id']}"
        )
    return document


__all__ = (
    "CombinedModelPlanningCampaignCoreV66Error",
    "build_combined_model_planning_campaign_document_v66",
)
