"""V75r2 successor with an explicit domain-to-flat action adapter."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v75r2 as domains
from acfqp import portable_priority_cross_occurrence_campaign_core_v75r1 as v75r1
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_flat_action_adapter_v45 import normalize_flat_action_adapter_v45
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_portable_certificate_query_priority_v44 import (
    GenericPortableCertificateQueryPriorityV44Error,
    run_portable_priority_certificate_episode_v44,
)


class NormalizedPortablePriorityCampaignCoreV75R2Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise NormalizedPortablePriorityCampaignCoreV75R2Error(message)


def _source(args: tuple[Any, ...]) -> dict[str, Any]:
    row = v75r1._build_priority_source(args)  # noqa: SLF001
    payload = {
        "schema": "acfqp.normalized_portable_priority_source.v75r2",
        "v75r1_source": row,
        "family": row["family"],
        "source_seed": row["source_seed"],
        "portable_query_priority": row["portable_query_priority"],
        "reusable_joint_successor_version_space_model": row[
            "predecessor_v75_source"
        ]["reusable_joint_successor_version_space_model"],
        "flat_action_adapter_needed_only_at_target_receipt_boundary": True,
        "fresh_target_outcomes_used_to_fit_source_artifacts": False,
    }
    return {
        **payload,
        "source_id": domains.extension_content_id_v75r2(
            domains.CONSTRUCTION_K7_NORMALIZED_PRIORITY_SOURCE_V75R2_DOMAIN,
            payload,
        ),
    }


def _arm(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    rows: tuple[Any, ...],
    model: Mapping[str, Any] | None,
    priority: Mapping[str, Any] | None,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        return run_portable_priority_certificate_episode_v44(
            adapter,
            candidate,
            rows,
            reusable_model=model,
            portable_query_priority=priority,
            model_source_episode_index=config["source_episode_index"],
            episode_index=config["target_episode_index"],
            maximum_abstract_depth=config["maximum_abstract_depth"],
            maximum_execution_steps=config["maximum_execution_steps"],
            maximum_target_ground_support_labels=config[
                "maximum_target_ground_support_labels"
            ],
            maximum_abstract_support_branch_evaluations=config[
                "maximum_relational_support_branch_evaluations"
            ],
            abstract_support_feasible_beam_width=config[
                "relational_support_feasible_beam_width"
            ],
        )
    except GenericPortableCertificateQueryPriorityV44Error as error:
        return {
            "schema": "acfqp.generic_portable_priority_certificate_failure.v44",
            "status": "TARGET_CERTIFICATE_EPISODE_FAILED_NONCERTIFICATE",
            "reason": str(error),
            "portable_priority_present": priority is not None,
            "official_execution_allowed": False,
        }


def _ood(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    model: Mapping[str, Any],
    priority: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    foreign_document = copy.deepcopy(candidate.public_document)
    foreign_document["state_width"] += 1
    foreign_document["unknown_residual_target_columns"] = sorted(
        [
            *foreign_document["unknown_residual_target_columns"],
            foreign_document["state_width"] - 1,
        ]
    )
    foreign_document["layout"]["state_canonical_to_raw"].append(
        foreign_document["state_width"] - 1
    )
    foreign_document["layout"]["state_structural_colors"].append(
        "V75R2_STRICT_INCOMPATIBLE_EXTRA_COORDINATE"
    )
    foreign = PartialFactorCandidateV15(
        foreign_document,
        candidate.layout,
        candidate.assignments,
        candidate.issuance_rows,
    )
    try:
        run_portable_priority_certificate_episode_v44(
            adapter,
            foreign,
            (),
            reusable_model=model,
            portable_query_priority=priority,
            model_source_episode_index=config["source_episode_index"],
            episode_index=config["target_episode_index"],
            maximum_abstract_depth=config["maximum_abstract_depth"],
            maximum_execution_steps=config["maximum_execution_steps"],
        )
    except GenericPortableCertificateQueryPriorityV44Error as error:
        return {
            "status": "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_GROUND_QUERY",
            "reason": str(error),
            "ground_transition_accessed": False,
        }
    _fail("V75r2 incompatible schema escaped normalized priority guard")


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    source, target_seed, factor_library, config = args
    original = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        source["family"], target_seed, config
    )
    partial = base.acquire_matched_true_bit_models_v59(
        original, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    adapter = normalize_flat_action_adapter_v45(original)
    model = source["reusable_joint_successor_version_space_model"]
    priority = source["portable_query_priority"]
    arms = {
        "NORMALIZED_PORTABLE_PRIORITY_AND_REUSABLE_MODEL": _arm(
            adapter, partial["candidate"], partial["rows"], model, priority, config
        ),
        "STRICT_NORMALIZED_NO_REUSABLE_ARTIFACTS": _arm(
            adapter, partial["candidate"], partial["rows"], None, None, config
        ),
    }
    payload = {
        "schema": "acfqp.normalized_portable_priority_target.v75r2",
        "family": source["family"],
        "source_id": source["source_id"],
        "source_seed": source["source_seed"],
        "target_seed": target_seed,
        "source_and_target_seed_identities_disjoint": source["source_seed"] != target_seed,
        "target_common_partial_acquisition_id": partial["document"]["acquisition_id"],
        "target_common_partial_ground_support_labels": partial["document"][
            "ground_support_labels"
        ],
        "source_model_id": model["joint_successor_version_space_model_id"],
        "portable_query_priority_id": priority["portable_query_priority_id"],
        "flat_action_adapter_applied_before_both_target_arms": True,
        "target_arms": arms,
        "incompatible_schema_ood_control": _ood(
            adapter, partial["candidate"], model, priority, config
        ),
        "source_artifacts_frozen_before_target_occurrence": True,
        "target_outcomes_used_to_refit_source_artifacts": False,
        "same_target_adapter_kernel_seed_episode_in_both_arms": True,
        "same_exact_query_local_certificate_engine_in_both_arms": True,
        "only_reusable_ordering_artifacts_differ_between_target_arms": True,
        "query_local_overlay_only_safety_authority": True,
    }
    return {
        **payload,
        "target_id": domains.extension_content_id_v75r2(
            domains.CONSTRUCTION_K7_NORMALIZED_PRIORITY_TARGET_V75R2_DOMAIN,
            payload,
        ),
    }


def build_normalized_portable_priority_campaign_document_v75r2(
    config: Mapping[str, Any],
    preregistration_id: str,
    v75_failure_id: str,
    v75r1_failure_id: str,
    v74_campaign_id: str,
    v74_verification_id: str,
    template_library_artifact_id: str,
    factor_library: Mapping[str, Any],
    residual_library: Mapping[str, Any],
    template_library: Mapping[str, Any],
    offline_template_source_labels: int,
) -> dict[str, Any]:
    source_args = [
        (family, seed, factor_library, residual_library, template_library, config)
        for family, seed in config["source_seed_by_family"].items()
    ]
    with ProcessPoolExecutor(max_workers=config["source_worker_count"]) as executor:
        sources = list(executor.map(_source, source_args))
    usable = [row for row in sources if row["portable_query_priority"] is not None]
    source_by_family = {row["family"]: row for row in usable}
    target_args = [
        (source_by_family[family], seed, factor_library, config)
        for family, seeds in config["fresh_target_seeds"].items()
        for seed in seeds
        if family in source_by_family
    ]
    with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
        targets = list(executor.map(_target, target_args))
    target_failures = sum(
        arm.get("success") is not True
        for row in targets
        for arm in row["target_arms"].values()
    )
    certificate_clean = all(
        arm["all_ground_queries_followed_failed_certificates"] is True
        and arm["query_local_exact_overlay_exclusively_used_for_safety"] is True
        and arm["reusable_artifacts_used_as_safety_authority"] is False
        for row in targets
        for arm in row["target_arms"].values()
        if arm.get("success") is True
    )
    derived_labels = sum(
        row["target_arms"]["NORMALIZED_PORTABLE_PRIORITY_AND_REUSABLE_MODEL"][
            "target_certificate_local_ground_support_labels"
        ]
        for row in targets
        if all(arm.get("success") is True for arm in row["target_arms"].values())
    )
    strict_labels = sum(
        row["target_arms"]["STRICT_NORMALIZED_NO_REUSABLE_ARTIFACTS"][
            "target_certificate_local_ground_support_labels"
        ]
        for row in targets
        if all(arm.get("success") is True for arm in row["target_arms"].values())
    )
    reduced_count = sum(
        row["target_arms"]["NORMALIZED_PORTABLE_PRIORITY_AND_REUSABLE_MODEL"][
            "target_certificate_local_ground_support_labels"
        ]
        < row["target_arms"]["STRICT_NORMALIZED_NO_REUSABLE_ARTIFACTS"][
            "target_certificate_local_ground_support_labels"
        ]
        for row in targets
        if all(arm.get("success") is True for arm in row["target_arms"].values())
    )
    priority_used = sum(
        row["target_arms"]["NORMALIZED_PORTABLE_PRIORITY_AND_REUSABLE_MODEL"][
            "portable_priority_ordering_accepted_count"
        ]
        > 0
        for row in targets
    )
    ood_rejections = sum(
        row["incompatible_schema_ood_control"]["status"]
        == "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_GROUND_QUERY"
        for row in targets
    )
    gate_passed = (
        len(usable) == config["required_usable_source_count"]
        and len(targets) == config["fresh_target_occurrence_count"]
        and target_failures == 0
        and certificate_clean
        and priority_used == len(targets)
        and ood_rejections == len(targets)
        and derived_labels < strict_labels
        and reduced_count >= config["minimum_reduced_target_occurrence_count"]
    )
    source_episodes = [
        row["v75r1_source"]["predecessor_v75_source"]["source_complete_episode"][
            "predecessor_v30_episode"
        ]
        for row in sources
    ]
    priority_episodes = [row["v75r1_source"]["priority_source_episode"] for row in usable]
    payload = {
        "schema": "acfqp.normalized_portable_priority_campaign.v75r2",
        "preregistration_id": preregistration_id,
        "v75_failure_id": v75_failure_id,
        "v75r1_failure_id": v75r1_failure_id,
        "v74_campaign_id": v74_campaign_id,
        "v74_verification_id": v74_verification_id,
        "template_library_artifact_id": template_library_artifact_id,
        "sources": sources,
        "targets": targets,
        "sample_tax_comparison": {
            "fresh_cross_occurrence_target_count": len(targets),
            "derived_target_certificate_local_labels": derived_labels,
            "strict_target_certificate_local_labels": strict_labels,
            "derived_minus_strict_target_labels": derived_labels - strict_labels,
            "reduced_target_occurrence_count": reduced_count,
            "target_occurrences_using_portable_priority_count": priority_used,
            "normalized_portable_priority_reduction_observed": (
                bool(targets) and derived_labels < strict_labels
            ),
            "v75_zero_reduction_failure_preserved": True,
            "v75r1_adapter_failure_preserved": True,
            "official_economics_claimed": False,
        },
        "accounting": {
            "offline_template_source_labels": offline_template_source_labels,
            "offline_residual_library_labels": config["offline_library_labels"],
            "source_certificate_local_labels": sum(
                row["local_ground_support_labels"] for row in source_episodes
            ),
            "priority_source_certificate_local_labels": sum(
                row["target_certificate_local_ground_support_labels"]
                for row in priority_episodes
            ),
            "target_common_partial_labels": sum(
                row["target_common_partial_ground_support_labels"] for row in targets
            ),
            "target_derived_certificate_local_labels": derived_labels,
            "target_strict_certificate_local_labels": strict_labels,
            "target_derived_execution_steps": sum(
                row["target_arms"]["NORMALIZED_PORTABLE_PRIORITY_AND_REUSABLE_MODEL"][
                    "execution_steps"
                ]
                for row in targets
            ),
            "target_strict_execution_steps": sum(
                row["target_arms"]["STRICT_NORMALIZED_NO_REUSABLE_ARTIFACTS"][
                    "execution_steps"
                ]
                for row in targets
            ),
            "target_derived_priority_lookup_count": sum(
                row["target_arms"]["NORMALIZED_PORTABLE_PRIORITY_AND_REUSABLE_MODEL"][
                    "portable_priority_lookup_count"
                ]
                for row in targets
            ),
            "target_derived_abstract_planning_compute_events": sum(
                row["target_arms"]["NORMALIZED_PORTABLE_PRIORITY_AND_REUSABLE_MODEL"][
                    "abstract_planning_compute_events"
                ]
                for row in targets
            ),
            "target_strict_abstract_planning_compute_events": 0,
            "all_axes_separate": True,
        },
        "registered_gate": {
            "usable_source_count": len(usable),
            "required_usable_source_count": config["required_usable_source_count"],
            "fresh_target_occurrence_count": len(targets),
            "required_fresh_target_occurrence_count": config[
                "fresh_target_occurrence_count"
            ],
            "target_arm_failure_count": target_failures,
            "certificate_discipline_clean": certificate_clean,
            "portable_priority_used_target_count": priority_used,
            "required_portable_priority_used_target_count": len(targets),
            "incompatible_schema_ood_rejection_count": ood_rejections,
            "required_incompatible_schema_ood_rejection_count": len(targets),
            "aggregate_cross_occurrence_target_reduction_required": True,
            "aggregate_cross_occurrence_target_reduction_observed": (
                bool(targets) and derived_labels < strict_labels
            ),
            "minimum_reduced_target_occurrence_count": config[
                "minimum_reduced_target_occurrence_count"
            ],
            "actual_reduced_target_occurrence_count": reduced_count,
            "passed": gate_passed,
        },
        "v75_and_v75r1_failures_preserved": True,
        "flat_action_adapter_applied_before_both_target_arms": True,
        "source_artifacts_frozen_before_targets": True,
        "source_and_target_seed_identities_disjoint": all(
            row["source_and_target_seed_identities_disjoint"] is True for row in targets
        ),
        "target_outcomes_used_to_refit_source_artifacts": False,
        "all_ground_queries_followed_failed_certificates": certificate_clean,
        "query_local_exact_overlay_exclusively_used_for_safety": certificate_clean,
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
        "campaign_id": domains.extension_content_id_v75r2(
            domains.CONSTRUCTION_K7_NORMALIZED_PRIORITY_CAMPAIGN_V75R2_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "NormalizedPortablePriorityCampaignCoreV75R2Error",
    "build_normalized_portable_priority_campaign_document_v75r2",
)
