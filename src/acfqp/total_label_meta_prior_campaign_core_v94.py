"""Fresh V94 total-target-label meta-prior/no-prior/cold-direct campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v94 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_low_label_residual_applicability_v73 import (
    acquire_low_label_residual_applicability_v73,
)
from acfqp.generic_total_label_residual_transfer_ablation_v75 import (
    run_total_label_residual_transfer_ablation_v75,
)


class TotalLabelMetaPriorCampaignCoreV94Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise TotalLabelMetaPriorCampaignCoreV94Error(message)


def _acquire_and_run(
    seed: int,
    model: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    source_meta_prior_odds: int,
    acquisition_domain: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        config["target_family"], seed, config
    )
    acquisition = acquire_low_label_residual_applicability_v73(
        adapter,
        model,
        maximum_ground_support_labels=config[
            "maximum_applicability_ground_support_labels"
        ],
        confidence_denominator=config["confidence_denominator"],
        source_meta_prior_odds=source_meta_prior_odds,
        layout_domain=config["generic_domains"]["layout"],
        applicability_domain=acquisition_domain,
        content_id=domains.extension_content_id_v94,
    )
    ablation = run_total_label_residual_transfer_ablation_v75(
        acquisition["projected_adapter"],
        acquisition["candidate"],
        acquisition["aligned_rows"],
        acquisition["document"]["ground_support_labels"],
        model,
        episode_index=config["target_episode_index"],
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=config[
            "maximum_incremental_certificate_ground_support_labels"
        ],
        maximum_robust_state_depth_evaluations=config[
            "maximum_robust_state_depth_evaluations"
        ],
        maximum_abstract_support_branch_evaluations=config[
            "maximum_abstract_support_branch_evaluations"
        ],
        abstract_support_feasible_beam_width=config[
            "abstract_support_feasible_beam_width"
        ],
    )
    return acquisition["document"], ablation


def _ood_control(seed: int, model: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    forged = copy.deepcopy(dict(model))
    forged["state_width"] += 1
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        config["target_family"], seed, config
    )
    try:
        acquire_low_label_residual_applicability_v73(
            adapter,
            forged,
            maximum_ground_support_labels=config[
                "maximum_applicability_ground_support_labels"
            ],
            confidence_denominator=config["confidence_denominator"],
            source_meta_prior_odds=config["source_meta_prior_odds"],
            layout_domain=config["generic_domains"]["layout"],
            applicability_domain=(
                domains.CONSTRUCTION_K7_TOTAL_LABEL_META_PRIOR_ON_ACQUISITION_V94_DOMAIN
            ),
            content_id=domains.extension_content_id_v94,
        )
    except Exception as error:
        if not error.__class__.__module__.startswith("acfqp.generic_"):
            raise
        return {
            "status": "INCOMPATIBLE_MODEL_REJECTED_BEFORE_TARGET_OBSERVATION",
            "reason": str(error),
            "target_ground_support_labels_consumed": 0,
            "target_episode_executed": False,
        }
    _fail("V94 incompatible source model received target observations")


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    seed, model, config = args
    meta = None
    no_prior = None
    ood = None
    status = "TARGET_FAILED_BEFORE_MATCHED_ACQUISITIONS_NONCERTIFICATE"
    reason = None
    try:
        meta = _acquire_and_run(
            seed,
            model,
            config,
            source_meta_prior_odds=config["source_meta_prior_odds"],
            acquisition_domain=(
                domains.CONSTRUCTION_K7_TOTAL_LABEL_META_PRIOR_ON_ACQUISITION_V94_DOMAIN
            ),
        )
        no_prior = _acquire_and_run(
            seed,
            model,
            config,
            source_meta_prior_odds=1,
            acquisition_domain=(
                domains.CONSTRUCTION_K7_TOTAL_LABEL_META_PRIOR_OFF_ACQUISITION_V94_DOMAIN
            ),
        )
        meta_strict = meta[1]["arms"]["STRICT_COLD_DIRECT_GROUND"]
        no_prior_strict = no_prior[1]["arms"]["STRICT_COLD_DIRECT_GROUND"]
        if {
            key: value
            for key, value in meta_strict.items()
            if key not in {"episode_id", "target_candidate_id"}
        } != {
            key: value
            for key, value in no_prior_strict.items()
            if key not in {"episode_id", "target_candidate_id"}
        }:
            _fail("V94 repeated cold-direct control changed across matched runs")
        ood = _ood_control(seed, model, config)
    except Exception as error:
        if not error.__class__.__module__.startswith("acfqp.generic_"):
            raise
        status = "TARGET_ACQUISITION_OR_EPISODE_FAILED_NONCERTIFICATE"
        reason = str(error)
    else:
        status = "TARGET_META_PRIOR_NO_PRIOR_AND_DIRECT_EPISODES_COMPLETED"
    payload = {
        "schema": "acfqp.total_label_meta_prior_occurrence.v94",
        "family": config["target_family"],
        "target_seed": seed,
        "target_episode_index": config["target_episode_index"],
        "source_model_id": model["joint_successor_version_space_model_id"],
        "meta_prior_acquisition": None if meta is None else meta[0],
        "meta_prior_total_label_ablation": None if meta is None else meta[1],
        "no_prior_acquisition": None if no_prior is None else no_prior[0],
        "no_prior_total_label_ablation": None if no_prior is None else no_prior[1],
        "strict_incompatible_model_ood_control": ood,
        "status": status,
        "failure_reason": reason,
        "same_synthesizer_stop_rule_target_kernel_seed_episode_and_exact_engine": (
            meta is not None and no_prior is not None
        ),
        "only_source_meta_prior_odds_differs_between_acquisition_arms": True,
        "source_meta_prior_strength_used_as_safety_authority": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v94(
            domains.CONSTRUCTION_K7_TOTAL_LABEL_META_PRIOR_OCCURRENCE_V94_DOMAIN,
            payload,
        ),
    }


def build_total_label_meta_prior_campaign_document_v94(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    source_acceptance_id: str,
    source_acceptance_verification_id: str,
    source_campaign_id: str,
    source_campaign_verification_id: str,
    v93_failed_campaign_id: str,
    v93_failed_verification_id: str,
    source_accounting: Mapping[str, Any],
    model: Mapping[str, Any],
) -> dict[str, Any]:
    arguments = [(seed, model, config) for seed in config["target_seeds"]]
    if config["target_worker_count"] == 1:
        occurrences = [_target(row) for row in arguments]
    else:
        with ProcessPoolExecutor(
            max_workers=config["target_worker_count"]
        ) as executor:
            occurrences = list(executor.map(_target, arguments))
    completed = [
        row
        for row in occurrences
        if row["status"]
        == "TARGET_META_PRIOR_NO_PRIOR_AND_DIRECT_EPISODES_COMPLETED"
    ]
    meta_acquisitions = [row["meta_prior_acquisition"] for row in completed]
    no_prior_acquisitions = [row["no_prior_acquisition"] for row in completed]
    meta_ablations = [row["meta_prior_total_label_ablation"] for row in completed]
    no_prior_ablations = [
        row["no_prior_total_label_ablation"] for row in completed
    ]
    meta_episodes = [
        row["arms"]["LOW_LABEL_RESIDUAL_TRANSFER"] for row in meta_ablations
    ]
    no_prior_episodes = [
        row["arms"]["LOW_LABEL_RESIDUAL_TRANSFER"]
        for row in no_prior_ablations
    ]
    strict_episodes = [
        row["arms"]["STRICT_COLD_DIRECT_GROUND"] for row in meta_ablations
    ]
    matched_acquisition_clean = bool(completed) and all(
        meta["source_meta_prior_odds"] == config["source_meta_prior_odds"]
        and meta["source_meta_prior_enabled"] is True
        and no_prior["source_meta_prior_odds"] == 1
        and no_prior["source_meta_prior_enabled"] is False
        and meta["fixed_label_floor_used"] is False
        and no_prior["fixed_label_floor_used"] is False
        and meta["fixed_confirmation_block_used"] is False
        and no_prior["fixed_confirmation_block_used"] is False
        and meta["target_episode_outcomes_used"] is False
        and no_prior["target_episode_outcomes_used"] is False
        for meta, no_prior in zip(
            meta_acquisitions, no_prior_acquisitions, strict=True
        )
    )
    certificate_clean = bool(completed) and all(
        episode["all_incremental_ground_queries_followed_failed_certificates"]
        is True
        and episode["query_local_exact_overlay_exclusively_used_for_safety"]
        is True
        and episode["model_or_alignment_used_as_safety_authority"] is False
        for episode in (*meta_episodes, *no_prior_episodes, *strict_episodes)
    )
    multi_step_abstract_primary = bool(meta_episodes) and all(
        row["execution_steps"] >= 2
        and row["abstract_plan_success_count"] > 0
        and row["execution_action_matches_abstract_proposal_count"] >= 2
        and 2 * row["execution_action_matches_abstract_proposal_count"]
        >= row["execution_steps"]
        for row in meta_episodes
    )
    candidates_propagated = bool(meta_ablations) and all(
        row[
            "all_actual_source_residual_and_terminal_candidates_propagated_as_heuristics"
        ]
        is True
        for row in meta_ablations
    )
    ood_clean = bool(completed) and all(
        row["strict_incompatible_model_ood_control"]["status"]
        == "INCOMPATIBLE_MODEL_REJECTED_BEFORE_TARGET_OBSERVATION"
        and row["strict_incompatible_model_ood_control"][
            "target_ground_support_labels_consumed"
        ]
        == 0
        for row in completed
    )
    meta_totals = [row["total_target_ground_support_labels"] for row in meta_episodes]
    no_prior_totals = [
        row["total_target_ground_support_labels"] for row in no_prior_episodes
    ]
    strict_totals = [
        row["total_target_ground_support_labels"] for row in strict_episodes
    ]
    meta_noninferior_to_direct = bool(meta_totals) and all(
        left <= right for left, right in zip(meta_totals, strict_totals, strict=True)
    )
    meta_beats_direct = (
        meta_noninferior_to_direct and sum(meta_totals) < sum(strict_totals)
    )
    meta_beats_no_prior = bool(meta_totals) and all(
        left < right
        for left, right in zip(meta_totals, no_prior_totals, strict=True)
    ) and sum(meta_totals) < sum(no_prior_totals)
    passed = (
        len(completed) == config["required_target_occurrence_count"]
        and matched_acquisition_clean
        and certificate_clean
        and multi_step_abstract_primary
        and candidates_propagated
        and ood_clean
        and meta_beats_direct
        and meta_beats_no_prior
    )
    accounting = {
        "inherited_source_accounting": copy.deepcopy(dict(source_accounting)),
        "meta_prior_target_acquisition_labels": sum(
            row["ground_support_labels"] for row in meta_acquisitions
        ),
        "no_prior_target_acquisition_labels": sum(
            row["ground_support_labels"] for row in no_prior_acquisitions
        ),
        "meta_prior_incremental_certificate_labels": sum(
            row["incremental_certificate_local_ground_support_labels"]
            for row in meta_episodes
        ),
        "no_prior_incremental_certificate_labels": sum(
            row["incremental_certificate_local_ground_support_labels"]
            for row in no_prior_episodes
        ),
        "strict_cold_direct_labels": sum(strict_totals),
        "meta_prior_total_target_labels": sum(meta_totals),
        "no_prior_total_target_labels": sum(no_prior_totals),
        "strict_minus_meta_prior_total_target_labels": (
            sum(strict_totals) - sum(meta_totals)
        ),
        "no_prior_minus_meta_prior_total_target_labels": (
            sum(no_prior_totals) - sum(meta_totals)
        ),
        "meta_prior_execution_steps": sum(
            row["execution_steps"] for row in meta_episodes
        ),
        "no_prior_execution_steps": sum(
            row["execution_steps"] for row in no_prior_episodes
        ),
        "strict_execution_steps": sum(
            row["execution_steps"] for row in strict_episodes
        ),
        "meta_prior_applicability_derivation_events": sum(
            row["partial_and_residual_replay_compute_events"]
            for row in meta_acquisitions
        ),
        "no_prior_applicability_derivation_events": sum(
            row["partial_and_residual_replay_compute_events"]
            for row in no_prior_acquisitions
        ),
        "meta_prior_abstract_planning_compute_events": sum(
            row["abstract_planning_compute_events"] for row in meta_episodes
        ),
        "no_prior_abstract_planning_compute_events": sum(
            row["abstract_planning_compute_events"] for row in no_prior_episodes
        ),
        "strict_abstract_planning_compute_events": sum(
            row["abstract_planning_compute_events"] for row in strict_episodes
        ),
        "source_target_labels_execution_derivation_certificate_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.total_label_meta_prior_campaign.v94",
        "preregistration_id": preregistration_id,
        "source_acceptance_id": source_acceptance_id,
        "source_acceptance_verification_id": source_acceptance_verification_id,
        "source_campaign_id": source_campaign_id,
        "source_campaign_verification_id": source_campaign_verification_id,
        "preserved_v93_failed_campaign_id": v93_failed_campaign_id,
        "preserved_v93_failed_verification_id": v93_failed_verification_id,
        "source_model_id": model["joint_successor_version_space_model_id"],
        "source_meta_prior_odds": config["source_meta_prior_odds"],
        "target_occurrences": occurrences,
        "accounting": accounting,
        "registered_gate": {
            "required_target_occurrence_count": config[
                "required_target_occurrence_count"
            ],
            "completed_target_occurrence_count": len(completed),
            "matched_same_synthesizer_prior_on_off_acquisition_clean": (
                matched_acquisition_clean
            ),
            "certificate_failure_only_ground_discipline_clean": certificate_clean,
            "multi_step_abstract_proposal_primary_on_every_target": (
                multi_step_abstract_primary
            ),
            "all_source_version_space_candidates_propagated_as_heuristics": (
                candidates_propagated
            ),
            "strict_incompatible_model_no_transfer_clean": ood_clean,
            "meta_prior_total_labels_noninferior_to_direct_on_every_target": (
                meta_noninferior_to_direct
            ),
            "meta_prior_total_labels_strictly_better_than_direct_in_aggregate": (
                meta_beats_direct
            ),
            "meta_prior_total_labels_strictly_better_than_no_prior_on_every_target_and_aggregate": (
                meta_beats_no_prior
            ),
            "passed": passed,
        },
        "fresh_target_identities_executed_without_selection": True,
        "v93_failure_preserved_without_rerun": True,
        "sample_tax_reduction_verified_on_registered_target_workload": passed,
        "sample_tax_reduction_generalized_beyond_registered_workload": False,
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
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v94(
            domains.CONSTRUCTION_K7_TOTAL_LABEL_META_PRIOR_CAMPAIGN_V94_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_total_label_meta_prior_campaign_document_v94",)
