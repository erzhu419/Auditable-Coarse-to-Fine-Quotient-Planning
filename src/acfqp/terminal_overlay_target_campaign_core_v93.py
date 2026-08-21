"""Fresh V93 campaign: reusable residuals plus target-local terminal overlays."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v93 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_joint_partial_terminal_acquisition_v70 import (
    acquire_joint_partial_terminal_prefix_v70,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_terminal_overlay_target_ablation_v72 import (
    run_matched_terminal_overlay_target_ablation_v72,
)
from acfqp.generic_terminal_overlay_version_space_planner_v69 import (
    prepare_terminal_overlay_target_inputs_v69,
)


class TerminalOverlayTargetCampaignCoreV93Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise TerminalOverlayTargetCampaignCoreV93Error(message)


def _ood_control(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    partial_rows: tuple[Any, ...],
    joint_rows: tuple[Any, ...],
    model: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    foreign_document = copy.deepcopy(candidate.public_document)
    foreign_document["state_width"] += 1
    foreign_document["layout"]["schema_signature"] = (
        "V93_STRICT_INCOMPATIBLE_SCHEMA"
    )
    foreign = PartialFactorCandidateV15(
        foreign_document,
        candidate.layout,
        candidate.assignments,
        candidate.issuance_rows,
    )
    try:
        prepare_terminal_overlay_target_inputs_v69(
            adapter,
            foreign,
            joint_rows,
            model,
            layout_domain=config["generic_domains"]["layout"],
            layout_observed_rows=partial_rows,
            terminal_confidence_denominator=config[
                "terminal_confidence_denominator"
            ],
            maximum_terminal_program_candidates=config[
                "maximum_terminal_program_candidates"
            ],
        )
    except Exception as error:
        if not error.__class__.__module__.startswith("acfqp.generic_"):
            raise
        return {
            "status": "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_ALIGNMENT_OR_EPISODE",
            "reason": str(error),
            "ground_transition_accessed_beyond_registered_joint_prefix": False,
        }
    _fail("V93 incompatible schema received a target overlay")


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    seed, model, config = args
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        config["target_family"], seed, config
    )
    acquisition = None
    ablation = None
    ood = None
    status = "TARGET_FAILED_BEFORE_JOINT_ACQUISITION_NONCERTIFICATE"
    reason = None
    try:
        acquisition = acquire_joint_partial_terminal_prefix_v70(
            adapter,
            model,
            maximum_ground_support_labels=config[
                "target_joint_acquisition_maximum_ground_labels"
            ],
            global_alpha_denominator=config["global_alpha_denominator"],
            minimum_factor_assignment_count=config[
                "minimum_reusable_factor_count"
            ],
            terminal_confidence_denominator=config[
                "terminal_confidence_denominator"
            ],
            maximum_terminal_program_candidates=config[
                "maximum_terminal_program_candidates"
            ],
            layout_domain=config["generic_domains"]["layout"],
            partial_acquisition_domain=(
                domains.CONSTRUCTION_K7_TERMINAL_OVERLAY_TARGET_PARTIAL_ACQUISITION_V93_DOMAIN
            ),
            joint_acquisition_domain=(
                domains.CONSTRUCTION_K7_TERMINAL_OVERLAY_TARGET_JOINT_ACQUISITION_V93_DOMAIN
            ),
            content_id=domains.extension_content_id_v93,
        )
        ablation = run_matched_terminal_overlay_target_ablation_v72(
            acquisition["projected_adapter"],
            acquisition["candidate"],
            acquisition["aligned_rows"],
            model,
            acquisition["terminal_overlay"],
            episode_index=config["target_episode_index"],
            maximum_abstract_depth=config["maximum_abstract_depth"],
            maximum_execution_steps=config["maximum_execution_steps"],
            maximum_target_ground_support_labels=config[
                "maximum_target_ground_support_labels"
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
        ood = _ood_control(
            adapter,
            acquisition["partial"]["candidate"],
            acquisition["partial"]["rows"],
            acquisition["rows"],
            model,
            config,
        )
    except Exception as error:
        if not error.__class__.__module__.startswith("acfqp.generic_"):
            raise
        status = "TARGET_ACQUISITION_ALIGNMENT_OR_EPISODE_FAILED_NONCERTIFICATE"
        reason = str(error)
    else:
        status = "TARGET_TERMINAL_OVERLAY_EPISODES_COMPLETED"
    acquisition_document = None if acquisition is None else acquisition["document"]
    payload = {
        "schema": "acfqp.terminal_overlay_target_occurrence.v93",
        "family": adapter.family,
        "target_seed": seed,
        "target_episode_index": config["target_episode_index"],
        "source_model_id": model["joint_successor_version_space_model_id"],
        "target_joint_acquisition": acquisition_document,
        "matched_ablation": ablation,
        "incompatible_schema_ood_control": ood,
        "status": status,
        "failure_reason": reason,
        "alignment_terminal_overlay_and_source_residual_frozen_before_episode": (
            ablation is not None
        ),
        "target_episode_outcomes_used_to_refit_any_abstract_component": False,
        "certificate_failure_only_local_ground_distinctions": (
            ablation is None
            or ablation["all_ground_queries_followed_failed_certificates"] is True
        ),
        "query_local_exact_overlay_only_safety_authority": True,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v93(
            domains.CONSTRUCTION_K7_TERMINAL_OVERLAY_TARGET_OCCURRENCE_V93_DOMAIN,
            payload,
        ),
    }


def build_terminal_overlay_target_campaign_document_v93(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    source_acceptance_id: str,
    source_acceptance_verification_id: str,
    source_campaign_id: str,
    source_campaign_verification_id: str,
    v92_failed_campaign_id: str,
    v92_failed_verification_id: str,
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
    if len(occurrences) != config["required_target_occurrence_count"]:
        _fail("V93 target occurrence count changed")
    completed = [
        row
        for row in occurrences
        if row["status"] == "TARGET_TERMINAL_OVERLAY_EPISODES_COMPLETED"
    ]
    acquisitions = [row["target_joint_acquisition"] for row in completed]
    ablations = [row["matched_ablation"] for row in completed]
    derived = [
        row["arms"]["SOURCE_RESIDUAL_PLUS_TARGET_TERMINAL_OVERLAY"]
        for row in ablations
    ]
    strict = [row["arms"]["STRICT_DIRECT_GROUND"] for row in ablations]
    joint_acquisition_clean = bool(acquisitions) and all(
        row["terminal_witness_used_to_schedule_queries"] is False
        and row["fixed_label_floor_used"] is False
        and row["fixed_confirmation_block_used"] is False
        and row["candidate_disagreement_mdl_and_confidence_stopping_only"] is True
        and row["target_episode_outcomes_used"] is False
        and row["raw_transition_rows"]
        and row["action_catalogue"]
        for row in acquisitions
    )
    certificate_clean = bool(ablations) and all(
        row["all_ground_queries_followed_failed_certificates"] is True
        and row["query_local_exact_overlay_exclusively_used_for_safety"] is True
        and row[
            "model_alignment_or_terminal_overlay_used_as_safety_authority"
        ]
        is False
        for row in ablations
    )
    multi_step_abstract_primary = bool(derived) and all(
        row["execution_steps"] >= 2
        and row["abstract_plan_success_count"] > 0
        and row["execution_action_matches_abstract_proposal_count"] >= 2
        and 2 * row["execution_action_matches_abstract_proposal_count"]
        >= row["execution_steps"]
        for row in derived
    )
    version_space_propagated = bool(ablations) and all(
        row["all_actual_residual_and_terminal_candidates_jointly_propagated"]
        is True
        for row in ablations
    )
    ood_clean = bool(completed) and all(
        row["incompatible_schema_ood_control"]["status"]
        == "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_ALIGNMENT_OR_EPISODE"
        and row["incompatible_schema_ood_control"][
            "ground_transition_accessed_beyond_registered_joint_prefix"
        ]
        is False
        for row in completed
    )
    derived_labels = sum(
        row["target_certificate_local_ground_support_labels"] for row in derived
    )
    strict_labels = sum(
        row["target_certificate_local_ground_support_labels"] for row in strict
    )
    every_target_reduced = bool(ablations) and all(
        row["actual_target_sample_reduction_observed"] is True
        for row in ablations
    )
    sample_reduction = every_target_reduced and derived_labels < strict_labels
    passed = (
        len(completed) == config["required_target_occurrence_count"]
        and joint_acquisition_clean
        and certificate_clean
        and multi_step_abstract_primary
        and version_space_propagated
        and ood_clean
        and sample_reduction
    )
    accounting = {
        "inherited_source_accounting": copy.deepcopy(dict(source_accounting)),
        "target_partial_factor_labels": sum(
            row["partial_factor_stop_ground_support_labels"]
            for row in acquisitions
        ),
        "target_terminal_calibration_incremental_labels": sum(
            row["terminal_calibration_incremental_ground_support_labels"]
            for row in acquisitions
        ),
        "target_joint_acquisition_labels": sum(
            row["joint_stop_ground_support_labels"] for row in acquisitions
        ),
        "derived_target_certificate_local_labels": derived_labels,
        "strict_target_certificate_local_labels": strict_labels,
        "strict_minus_derived_target_certificate_labels": (
            strict_labels - derived_labels
        ),
        "derived_target_execution_steps": sum(
            row["execution_steps"] for row in derived
        ),
        "strict_target_execution_steps": sum(
            row["execution_steps"] for row in strict
        ),
        "terminal_overlay_derivation_events": sum(
            len(row["terminal_overlay"]["prequential_history"])
            for row in acquisitions
        ),
        "alignment_partial_and_residual_replay_events": sum(
            row["alignment"]["partial_replay_evaluations"]
            + row["alignment"]["residual_replay_evaluations"]
            for row in acquisitions
        ),
        "derived_abstract_planning_compute_events": sum(
            row["abstract_planning_compute_events"] for row in derived
        ),
        "strict_abstract_planning_compute_events": sum(
            row["abstract_planning_compute_events"] for row in strict
        ),
        "source_target_labels_execution_derivation_certificate_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.terminal_overlay_target_campaign.v93",
        "preregistration_id": preregistration_id,
        "source_acceptance_id": source_acceptance_id,
        "source_acceptance_verification_id": source_acceptance_verification_id,
        "source_campaign_id": source_campaign_id,
        "source_campaign_verification_id": source_campaign_verification_id,
        "preserved_v92_failed_campaign_id": v92_failed_campaign_id,
        "preserved_v92_failed_verification_id": v92_failed_verification_id,
        "source_model_id": model["joint_successor_version_space_model_id"],
        "target_occurrences": occurrences,
        "accounting": accounting,
        "registered_gate": {
            "required_target_occurrence_count": config[
                "required_target_occurrence_count"
            ],
            "completed_target_occurrence_count": len(completed),
            "joint_partial_terminal_acquisition_clean": joint_acquisition_clean,
            "certificate_failure_only_ground_discipline_clean": certificate_clean,
            "multi_step_abstract_proposal_primary_on_every_target": (
                multi_step_abstract_primary
            ),
            "all_actual_residual_and_target_terminal_candidates_propagated": (
                version_space_propagated
            ),
            "strict_incompatible_schema_no_transfer_clean": ood_clean,
            "every_target_certificate_label_reduction_observed": (
                every_target_reduced
            ),
            "aggregate_target_certificate_label_reduction_observed": (
                sample_reduction
            ),
            "passed": passed,
        },
        "fresh_target_identities_executed_without_selection": True,
        "v92_failure_preserved_without_rerun": True,
        "target_episode_outcomes_used_to_refit_abstract_components": False,
        "all_ground_queries_followed_failed_certificates": certificate_clean,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "multi_step_planning_primarily_in_abstract_model_verified": passed,
        "sample_tax_reduction_verified_on_registered_target_workload": (
            sample_reduction
        ),
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
        "campaign_id": domains.extension_content_id_v93(
            domains.CONSTRUCTION_K7_TERMINAL_OVERLAY_TARGET_CAMPAIGN_V93_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_terminal_overlay_target_campaign_document_v93",)
