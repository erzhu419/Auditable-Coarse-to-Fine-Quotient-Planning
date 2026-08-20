"""Fresh matched V68 campaign for relational residual world models."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v68 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_relational_world_model_certificate_planner_v30 import (
    run_relational_world_model_certificate_episode_v30,
)


class RelationalWorldModelCampaignCoreV68Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise RelationalWorldModelCampaignCoreV68Error(message)


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
        episodes[arm] = run_relational_world_model_certificate_episode_v30(
            adapter,
            partial["candidate"],
            partial["rows"],
            residual_prior_library=library,
            episode_index=0,
            maximum_abstract_depth=config["maximum_abstract_depth"],
            maximum_execution_steps=config["maximum_execution_steps"],
            confidence_denominator=config["residual_confidence_denominator"],
            maximum_terminal_program_candidates_to_try=config[
                "maximum_terminal_program_candidates_to_try"
            ],
            maximum_relational_support_branch_evaluations=config[
                "maximum_relational_support_branch_evaluations"
            ],
            relational_support_feasible_beam_width=config[
                "relational_support_feasible_beam_width"
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
            or episode["relational_abstract_plan_used_as_safety_authority"] is not False
            or episode["complete_world_model_synthesized"] is not False
        ):
            _fail("V68 safety boundary changed")
    payload = {
        "schema": "acfqp.relational_world_model_occurrence.v68",
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
        "terminal_and_transition_programs_jointly_selected": True,
        "query_local_overlay_only_safety_authority": True,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v68(
            domains.CONSTRUCTION_K7_RELATIONAL_WORLD_MODEL_OCCURRENCE_V68_DOMAIN,
            payload,
        ),
    }


def build_relational_world_model_campaign_document_v68(
    config: Mapping[str, Any],
    preregistration_id: str,
    v67_campaign_id: str,
    v67_verification_id: str,
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
        _fail("V68 occurrence inventory changed")
    prior = [row["prior_episode"] for row in occurrences]
    strict = [row["strict_episode"] for row in occurrences]
    prior_successes = sum(
        row["relational_abstract_plan_success_count"] for row in prior
    )
    strict_successes = sum(
        row["relational_abstract_plan_success_count"] for row in strict
    )
    prior_active = sum(bool(row["relational_world_model_activations"]) for row in prior)
    strict_active = sum(bool(row["relational_world_model_activations"]) for row in strict)
    prior_rejections = sum(
        row["terminal_program_candidate_rejection_count"] for row in prior
    )
    gate_passed = prior_successes > 0 and prior_active > 0 and prior_rejections > 0
    family_projections = {}
    for family in config["target_seeds"]:
        selected = [row for row in occurrences if row["family"] == family]
        family_projections[family] = {
            "occurrence_count": len(selected),
            "prior_relational_plan_success_count": sum(
                row["prior_episode"]["relational_abstract_plan_success_count"]
                for row in selected
            ),
            "strict_relational_plan_success_count": sum(
                row["strict_episode"]["relational_abstract_plan_success_count"]
                for row in selected
            ),
            "prior_active_world_model_occurrence_count": sum(
                bool(row["prior_episode"]["relational_world_model_activations"])
                for row in selected
            ),
            "strict_active_world_model_occurrence_count": sum(
                bool(row["strict_episode"]["relational_world_model_activations"])
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
        "prior_relational_abstract_support_branch_evaluations": sum(
            row["relational_abstract_support_branch_evaluations"] for row in prior
        ),
        "strict_relational_abstract_support_branch_evaluations": sum(
            row["relational_abstract_support_branch_evaluations"] for row in strict
        ),
        "prior_relational_world_model_synthesis_attempts": sum(
            row["relational_world_model_synthesis_attempt_count"] for row in prior
        ),
        "strict_relational_world_model_synthesis_attempts": sum(
            row["relational_world_model_synthesis_attempt_count"] for row in strict
        ),
        "prior_terminal_program_candidate_attempts": sum(
            row["terminal_program_candidate_attempt_count"] for row in prior
        ),
        "strict_terminal_program_candidate_attempts": sum(
            row["terminal_program_candidate_attempt_count"] for row in strict
        ),
        "all_axes_separate": True,
    }
    payload = {
        "schema": "acfqp.relational_world_model_campaign.v68",
        "preregistration_id": preregistration_id,
        "v67_campaign_id": v67_campaign_id,
        "v67_verification_id": v67_verification_id,
        "occurrences": occurrences,
        "accounting": accounting,
        "family_projections": family_projections,
        "registered_relational_world_model_gate": {
            "prior_relational_plan_success_count": prior_successes,
            "strict_relational_plan_success_count": strict_successes,
            "prior_active_world_model_occurrence_count": prior_active,
            "strict_active_world_model_occurrence_count": strict_active,
            "prior_terminal_candidate_rejection_count": prior_rejections,
            "required_relation": "PRIOR_PLAN_GT_ZERO_AND_ACTIVE_GT_ZERO_AND_REJECTION_GT_ZERO",
            "passed": gate_passed,
            "prior_vs_strict_improvement_required": False,
            "certificate_local_label_reduction_required": False,
        },
        "terminal_and_transition_programs_jointly_selected_for_abstract_planning": True,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "relational_abstract_plan_used_as_safety_authority": False,
        "producer_free_verification_present": False,
        "complete_world_model_synthesized": False,
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
        "campaign_id": domains.extension_content_id_v68(
            domains.CONSTRUCTION_K7_RELATIONAL_WORLD_MODEL_CAMPAIGN_V68_DOMAIN,
            payload,
        ),
    }
    if not gate_passed:
        _fail(
            "V68 registered Gate failed: "
            f"success={prior_successes} active={prior_active} reject={prior_rejections} "
            f"failed_campaign_id={document['campaign_id']}"
        )
    return document


__all__ = (
    "RelationalWorldModelCampaignCoreV68Error",
    "build_relational_world_model_campaign_document_v68",
)
