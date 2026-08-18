"""Matched online use of residual proposals under certificate-local safety."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v65 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_online_residual_guided_planner_v21 import (
    run_online_residual_guided_episode_v21,
)


class OnlineResidualPlanningCampaignCoreV65Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OnlineResidualPlanningCampaignCoreV65Error(message)


def _identifier(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v65(
            domains.CONSTRUCTION_K7_ONLINE_RESIDUAL_PLANNING_OCCURRENCE_V65_DOMAIN,
            payload,
        ),
    }


def _label_breakdown(episode: Mapping[str, Any]) -> dict[str, int]:
    legality = sum(
        row["ground_support_labels"]
        for row in episode["local_distinctions"]
        if row["distinction_kind"] == "QUERY_LOCAL_LEGAL_ACTION_SET"
    )
    transition = sum(
        row["ground_support_labels"]
        for row in episode["local_distinctions"]
        if row["distinction_kind"] == "QUERY_LOCAL_EXACT_RESIDUAL_SUPPORT"
    )
    if legality + transition != episode["local_ground_support_labels"]:
        _fail("V65 local-label decomposition changed")
    return {"legality_labels": legality, "transition_labels": transition}


def _run_occurrence(args: tuple[Any, ...]) -> dict[str, Any]:
    family, seed, factor_library, residual_library, config = args
    adapter = base.predecessor.predecessor.prior_ground._adapter(
        family, seed, config
    )
    partial = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    shared = {
        "candidate": partial["candidate"],
        "rows": partial["rows"],
    }
    prior = run_online_residual_guided_episode_v21(
        adapter,
        shared["candidate"],
        shared["rows"],
        residual_prior_library=residual_library,
        episode_index=0,
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        confidence_denominator=config["residual_confidence_denominator"],
    )
    strict = run_online_residual_guided_episode_v21(
        adapter,
        shared["candidate"],
        shared["rows"],
        residual_prior_library=None,
        episode_index=0,
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        confidence_denominator=config["residual_confidence_denominator"],
    )
    if not (prior["success"] and strict["success"]):
        _fail("V65 matched online episode failed")
    if prior["partial_candidate_id"] != strict["partial_candidate_id"]:
        _fail("V65 matched partial candidate changed")
    for episode in (prior, strict):
        if (
            episode["all_ground_queries_followed_failed_certificates"] is not True
            or episode["query_local_exact_overlay_used_for_safety"] is not True
            or episode["residual_proposal_used_as_safety_authority"] is not False
            or episode[
                "only_action_conditioned_zero_excess_residual_proposals_guided_ordering"
            ]
            is not True
        ):
            _fail("V65 certificate-local safety boundary changed")
    payload = {
        "schema": "acfqp.online_residual_planning_occurrence.v65",
        "family": family,
        "seed": seed,
        "episode_index": 0,
        "common_partial_acquisition_id": partial["document"]["acquisition_id"],
        "common_partial_ground_support_labels": partial["document"][
            "ground_support_labels"
        ],
        "prior_episode": prior,
        "strict_episode": strict,
        "prior_label_breakdown": _label_breakdown(prior),
        "strict_label_breakdown": _label_breakdown(strict),
        "matched_environment_seed_and_episode": True,
        "same_partial_candidate_and_observations": True,
        "only_switched_variable": "FROZEN_RESIDUAL_FACTOR_EXPRESSION_PRIOR_CODE_LENGTH",
        "action_trajectories_required_to_match": False,
        "proposal_never_discharges_certificate": True,
    }
    return _identifier(payload)


def build_online_residual_planning_campaign_document_v65(
    config: Mapping[str, Any],
    preregistration_id: str,
    v64_campaign_id: str,
    v64_verification_id: str,
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
        _fail("V65 occurrence inventory changed")
    prior_labels = sum(
        row["prior_episode"]["local_ground_support_labels"] for row in occurrences
    )
    strict_labels = sum(
        row["strict_episode"]["local_ground_support_labels"] for row in occurrences
    )
    family_projection = {}
    for family in config["target_seeds"]:
        selected = [row for row in occurrences if row["family"] == family]
        prior_family = sum(
            row["prior_episode"]["local_ground_support_labels"] for row in selected
        )
        strict_family = sum(
            row["strict_episode"]["local_ground_support_labels"] for row in selected
        )
        family_projection[family] = {
            "occurrence_count": len(selected),
            "prior_certificate_local_labels": prior_family,
            "strict_certificate_local_labels": strict_family,
            "observed_label_difference_strict_minus_prior": strict_family
            - prior_family,
        }
    sample_gate_passed = prior_labels <= strict_labels
    payload = {
        "schema": "acfqp.online_residual_planning_campaign.v65",
        "preregistration_id": preregistration_id,
        "v64_campaign_id": v64_campaign_id,
        "v64_verification_id": v64_verification_id,
        "occurrences": occurrences,
        "accounting": {
            "offline_residual_library_labels": config["offline_library_labels"],
            "common_partial_acquisition_labels": sum(
                row["common_partial_ground_support_labels"] for row in occurrences
            ),
            "prior_certificate_local_labels": prior_labels,
            "strict_certificate_local_labels": strict_labels,
            "observed_online_label_difference_strict_minus_prior": strict_labels
            - prior_labels,
            "prior_execution_steps": sum(
                row["prior_episode"]["execution_steps"] for row in occurrences
            ),
            "strict_execution_steps": sum(
                row["strict_episode"]["execution_steps"] for row in occurrences
            ),
            "prior_partial_planning_compute_events": sum(
                row["prior_episode"]["abstract_planning_compute_events"]
                for row in occurrences
            ),
            "strict_partial_planning_compute_events": sum(
                row["strict_episode"]["abstract_planning_compute_events"]
                for row in occurrences
            ),
            "prior_residual_synthesis_attempts": sum(
                row["prior_episode"]["residual_synthesis_attempt_count"]
                for row in occurrences
            ),
            "strict_residual_synthesis_attempts": sum(
                row["strict_episode"]["residual_synthesis_attempt_count"]
                for row in occurrences
            ),
            "all_axes_separate": True,
        },
        "family_projections": family_projection,
        "registered_noninferiority_gate": {
            "relation": "PRIOR_CERTIFICATE_LOCAL_LABELS_LE_STRICT_CERTIFICATE_LOCAL_LABELS",
            "passed": sample_gate_passed,
            "positive_reduction_required": False,
        },
        "all_ground_queries_followed_failed_certificates": True,
        "residual_proposals_used_only_for_abstract_action_order": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
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
        "campaign_id": domains.extension_content_id_v65(
            domains.CONSTRUCTION_K7_ONLINE_RESIDUAL_PLANNING_CAMPAIGN_V65_DOMAIN,
            payload,
        ),
    }
    if not sample_gate_passed:
        _fail(
            "V65 registered online label noninferiority Gate failed: "
            f"prior={prior_labels} strict={strict_labels} "
            f"failed_campaign_id={document['campaign_id']}"
        )
    return document


__all__ = (
    "OnlineResidualPlanningCampaignCoreV65Error",
    "build_online_residual_planning_campaign_document_v65",
)
