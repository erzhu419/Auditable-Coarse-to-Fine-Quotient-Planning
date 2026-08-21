"""Fresh V92 target campaign using the accepted V91r3 source model."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v92 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_prior_only_partial_acquisition_v67 import (
    acquire_prior_only_partial_candidate_v67,
)
from acfqp.generic_version_space_target_planner_v68 import (
    align_version_space_target_inputs_v68,
    run_matched_version_space_target_ablation_v68,
)


class VersionSpaceTargetCampaignCoreV92Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise VersionSpaceTargetCampaignCoreV92Error(message)


def _ood_control(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    rows: tuple[Any, ...],
    model: Mapping[str, Any],
    layout_domain: str,
) -> dict[str, Any]:
    foreign_document = copy.deepcopy(candidate.public_document)
    foreign_document["state_width"] += 1
    foreign_document["layout"]["schema_signature"] = (
        "V92_STRICT_INCOMPATIBLE_SCHEMA"
    )
    foreign = PartialFactorCandidateV15(
        foreign_document,
        candidate.layout,
        candidate.assignments,
        candidate.issuance_rows,
    )
    try:
        align_version_space_target_inputs_v68(
            adapter,
            foreign,
            rows,
            model,
            layout_domain=layout_domain,
        )
    except Exception as error:
        if not error.__class__.__module__.startswith("acfqp.generic_"):
            raise
        return {
            "status": "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_ALIGNMENT_OR_EPISODE",
            "reason": str(error),
            "ground_transition_accessed_beyond_common_partial_prefix": False,
        }
    _fail("V92 incompatible schema received a target alignment")


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    seed, model, config = args
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        config["target_family"], seed, config
    )
    partial = None
    ablation = None
    ood = None
    status = "TARGET_FAILED_BEFORE_COMMON_PARTIAL_PREFIX_NONCERTIFICATE"
    reason = None
    try:
        partial = acquire_prior_only_partial_candidate_v67(
            adapter,
            maximum_ground_support_labels=config[
                "target_partial_acquisition_maximum_ground_labels"
            ],
            global_alpha_denominator=config["global_alpha_denominator"],
            minimum_factor_assignment_count=config[
                "minimum_reusable_factor_count"
            ],
            layout_domain=config["generic_domains"]["layout"],
            acquisition_domain=(
                domains.CONSTRUCTION_K7_VERSION_SPACE_TARGET_PARTIAL_ACQUISITION_V92_DOMAIN
            ),
            content_id=domains.extension_content_id_v92,
        )
        ablation = run_matched_version_space_target_ablation_v68(
            adapter,
            partial["candidate"],
            partial["rows"],
            model,
            layout_domain=config["generic_domains"]["layout"],
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
            partial["candidate"],
            partial["rows"],
            model,
            config["generic_domains"]["layout"],
        )
    except Exception as error:
        if not error.__class__.__module__.startswith("acfqp.generic_"):
            raise
        status = "TARGET_ALIGNMENT_OR_EPISODE_FAILED_NONCERTIFICATE"
        reason = str(error)
    else:
        status = "TARGET_MATCHED_VERSION_SPACE_EPISODES_COMPLETED"
    partial_document = None if partial is None else partial["document"]
    payload = {
        "schema": "acfqp.version_space_target_occurrence.v92",
        "family": adapter.family,
        "target_seed": seed,
        "target_episode_index": config["target_episode_index"],
        "source_model_id": model["joint_successor_version_space_model_id"],
        "target_common_partial_acquisition": partial_document,
        "target_common_partial_ground_support_labels": (
            0
            if partial_document is None
            else partial_document["ground_support_labels"]
        ),
        "matched_ablation": ablation,
        "incompatible_schema_ood_control": ood,
        "status": status,
        "failure_reason": reason,
        "alignment_and_source_model_frozen_before_target_episode": (
            ablation is not None
        ),
        "target_episode_outcomes_used_to_select_alignment_or_refit_model": False,
        "certificate_failure_only_local_ground_distinctions": (
            ablation is None
            or ablation["all_ground_queries_followed_failed_certificates"] is True
        ),
        "query_local_exact_overlay_only_safety_authority": True,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v92(
            domains.CONSTRUCTION_K7_VERSION_SPACE_TARGET_OCCURRENCE_V92_DOMAIN,
            payload,
        ),
    }


def build_version_space_target_campaign_document_v92(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    source_acceptance_id: str,
    source_acceptance_verification_id: str,
    source_campaign_id: str,
    source_campaign_verification_id: str,
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
        _fail("V92 target occurrence count changed")
    completed = [
        row
        for row in occurrences
        if row["status"]
        == "TARGET_MATCHED_VERSION_SPACE_EPISODES_COMPLETED"
    ]
    ablations = [row["matched_ablation"] for row in completed]
    derived = [row["arms"]["JOINT_VERSION_SPACE_WORLD_MODEL"] for row in ablations]
    strict = [row["arms"]["STRICT_DIRECT_GROUND"] for row in ablations]
    certificate_clean = bool(ablations) and all(
        row["all_ground_queries_followed_failed_certificates"] is True
        and row["query_local_exact_overlay_exclusively_used_for_safety"] is True
        and row["model_or_alignment_used_as_safety_authority"] is False
        for row in ablations
    )
    multi_step_abstract_primary = bool(derived) and all(
        row["execution_steps"] >= 3
        and row["abstract_plan_success_count"] > 0
        and row["execution_action_matches_abstract_proposal_count"] >= 2
        and 2 * row["execution_action_matches_abstract_proposal_count"]
        >= row["execution_steps"]
        for row in derived
    )
    version_space_propagated = bool(derived) and all(
        row["abstract_plan_receipts"]
        and all(
            receipt["abstract_plan"][
                "all_residual_version_spaces_jointly_propagated"
            ]
            is True
            and receipt["abstract_plan"][
                "all_mdl_minimal_terminal_trees_jointly_propagated"
            ]
            is True
            for receipt in row["abstract_plan_receipts"]
        )
        for row in derived
    )
    ood_clean = bool(completed) and all(
        row["incompatible_schema_ood_control"]["status"]
        == "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_ALIGNMENT_OR_EPISODE"
        and row["incompatible_schema_ood_control"][
            "ground_transition_accessed_beyond_common_partial_prefix"
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
    sample_reduction = bool(completed) and derived_labels < strict_labels
    passed = (
        len(completed) == config["required_target_occurrence_count"]
        and certificate_clean
        and multi_step_abstract_primary
        and version_space_propagated
        and ood_clean
        and sample_reduction
    )
    accounting = {
        "inherited_source_accounting": copy.deepcopy(dict(source_accounting)),
        "target_common_partial_labels": sum(
            row["target_common_partial_ground_support_labels"]
            for row in occurrences
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
        "derived_abstract_planning_compute_events": sum(
            row["abstract_planning_compute_events"] for row in derived
        ),
        "strict_abstract_planning_compute_events": sum(
            row["abstract_planning_compute_events"] for row in strict
        ),
        "target_alignment_replay_compute_events": sum(
            row["matched_ablation"]["alignment"][
                "target_prefix_model_replay_evaluations"
            ]
            for row in completed
        ),
        "source_labels_target_labels_execution_steps_alignment_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.version_space_target_campaign.v92",
        "preregistration_id": preregistration_id,
        "source_acceptance_id": source_acceptance_id,
        "source_acceptance_verification_id": source_acceptance_verification_id,
        "source_campaign_id": source_campaign_id,
        "source_campaign_verification_id": source_campaign_verification_id,
        "source_model_id": model["joint_successor_version_space_model_id"],
        "target_occurrences": occurrences,
        "accounting": accounting,
        "registered_gate": {
            "required_target_occurrence_count": config[
                "required_target_occurrence_count"
            ],
            "completed_target_occurrence_count": len(completed),
            "certificate_failure_only_ground_discipline_clean": certificate_clean,
            "multi_step_abstract_proposal_primary_on_every_target": (
                multi_step_abstract_primary
            ),
            "complete_actual_version_space_jointly_propagated": (
                version_space_propagated
            ),
            "strict_incompatible_schema_no_transfer_clean": ood_clean,
            "aggregate_target_certificate_label_reduction_observed": (
                sample_reduction
            ),
            "passed": passed,
        },
        "fresh_target_identities_executed_without_selection": True,
        "target_outcomes_used_to_refit_source_model_or_alignment": False,
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
        "campaign_id": domains.extension_content_id_v92(
            domains.CONSTRUCTION_K7_VERSION_SPACE_TARGET_CAMPAIGN_V92_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_version_space_target_campaign_document_v92",)
