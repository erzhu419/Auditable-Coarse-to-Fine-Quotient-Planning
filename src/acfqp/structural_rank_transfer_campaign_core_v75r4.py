"""V75r4 cross-occurrence reuse with target-local structural-rank priorities."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v75r4 as domains
from acfqp import normalized_portable_priority_campaign_core_v75r2 as v75r2
from acfqp import portable_priority_cross_occurrence_campaign_core_v75r1 as v75r1
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_flat_action_adapter_v45 import normalize_flat_action_adapter_v45
from acfqp.generic_structural_rank_query_prior_v46 import (
    compile_structural_rank_query_prior_v46,
    translate_structural_rank_prior_to_initial_v44_priority_v46,
)


DERIVED_ARM = "STRUCTURAL_RANK_PRIORITY_AND_REUSABLE_MODEL"
STRICT_ARM = "STRICT_NORMALIZED_NO_REUSABLE_ARTIFACTS"


def _source(args: tuple[Any, ...]) -> dict[str, Any]:
    family, seed, factor_library, residual_library, template_library, config = args
    predecessor = v75r1._build_priority_source(args)  # noqa: SLF001
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        family, seed, config
    )
    model = predecessor["predecessor_v75_source"][
        "reusable_joint_successor_version_space_model"
    ]
    prior = compile_structural_rank_query_prior_v46(
        predecessor["priority_source_episode"],
        model["source_layout"],
        adapter.catalogue,
    )
    payload = {
        "schema": "acfqp.structural_rank_transfer_source.v75r4",
        "family": family,
        "source_seed": seed,
        "predecessor_v75r1_source": predecessor,
        "reusable_joint_successor_version_space_model": model,
        "structural_rank_query_prior": prior,
        "source_query_outcomes_only_used_to_fit_rank_prior": True,
        "fresh_target_transition_outcomes_used_to_fit_source_artifacts": False,
        "rank_prior_is_ordering_only": True,
        "safety_authority_present": False,
    }
    return {
        **payload,
        "source_id": domains.extension_content_id_v75r4(
            domains.CONSTRUCTION_K7_STRUCTURAL_RANK_SOURCE_V75R4_DOMAIN,
            payload,
        ),
    }


def _successful(row: Mapping[str, Any], arm: str) -> bool:
    return row["target_arms"][arm].get("success") is True


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    source, target_seed, factor_library, config = args
    original = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        source["family"], target_seed, config
    )
    partial = base.acquire_matched_true_bit_models_v59(
        original, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    adapter = normalize_flat_action_adapter_v45(original)
    translated = translate_structural_rank_prior_to_initial_v44_priority_v46(
        source["structural_rank_query_prior"], partial["candidate"], adapter
    )
    model = source["reusable_joint_successor_version_space_model"]
    priority = translated["portable_priority"]
    arms = {
        DERIVED_ARM: v75r2._arm(  # noqa: SLF001
            adapter, partial["candidate"], partial["rows"], model, priority, config
        ),
        STRICT_ARM: v75r2._arm(  # noqa: SLF001
            adapter, partial["candidate"], partial["rows"], None, None, config
        ),
    }
    payload = {
        "schema": "acfqp.structural_rank_transfer_target.v75r4",
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
        "structural_rank_query_prior_id": source["structural_rank_query_prior"][
            "structural_rank_query_prior_id"
        ],
        "target_local_priority_translation": translated["translation_receipt"],
        "target_local_portable_priority_id": priority["portable_query_priority_id"],
        "target_arms": arms,
        "incompatible_schema_ood_control": v75r2._ood(  # noqa: SLF001
            adapter, partial["candidate"], model, priority, config
        ),
        "target_transition_outcomes_used_to_translate_priority": False,
        "same_target_adapter_kernel_seed_episode_in_both_arms": True,
        "only_reusable_ordering_artifacts_differ_between_target_arms": True,
        "query_local_overlay_only_safety_authority": True,
    }
    return {
        **payload,
        "target_id": domains.extension_content_id_v75r4(
            domains.CONSTRUCTION_K7_STRUCTURAL_RANK_TARGET_V75R4_DOMAIN,
            payload,
        ),
    }


def build_structural_rank_transfer_campaign_document_v75r4(
    config: Mapping[str, Any],
    preregistration_id: str,
    preserved_failure_ids: tuple[str, ...],
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
    source_by_family = {row["family"]: row for row in sources}
    target_args = [
        (source_by_family[family], seed, factor_library, config)
        for family, seeds in config["fresh_target_seeds"].items()
        for seed in seeds
    ]
    with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
        targets = list(executor.map(_target, target_args))
    completed = [
        row for row in targets if _successful(row, DERIVED_ARM) and _successful(row, STRICT_ARM)
    ]
    failures = [
        {
            "family": row["family"],
            "target_seed": row["target_seed"],
            "arm": arm,
            "status": row["target_arms"][arm].get("status"),
            "reason": row["target_arms"][arm].get("reason"),
        }
        for row in targets
        for arm in (DERIVED_ARM, STRICT_ARM)
        if not _successful(row, arm)
    ]
    derived_labels = sum(
        row["target_arms"][DERIVED_ARM]["target_certificate_local_ground_support_labels"]
        for row in completed
    )
    strict_labels = sum(
        row["target_arms"][STRICT_ARM]["target_certificate_local_ground_support_labels"]
        for row in completed
    )
    reduced_count = sum(
        row["target_arms"][DERIVED_ARM]["target_certificate_local_ground_support_labels"]
        < row["target_arms"][STRICT_ARM]["target_certificate_local_ground_support_labels"]
        for row in completed
    )
    priority_used = sum(
        row["target_arms"][DERIVED_ARM]["portable_priority_ordering_accepted_count"] > 0
        for row in completed
    )
    certificate_clean = all(
        arm["all_ground_queries_followed_failed_certificates"] is True
        and arm["query_local_exact_overlay_exclusively_used_for_safety"] is True
        and arm["reusable_artifacts_used_as_safety_authority"] is False
        for row in completed
        for arm in row["target_arms"].values()
    )
    ood_rejections = sum(
        row["incompatible_schema_ood_control"]["status"]
        == "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_GROUND_QUERY"
        for row in targets
    )
    passed = (
        len(sources) == config["required_usable_source_count"]
        and len(targets) == config["fresh_target_occurrence_count"]
        and not failures
        and certificate_clean
        and priority_used == len(targets)
        and ood_rejections == len(targets)
        and derived_labels < strict_labels
        and reduced_count >= config["minimum_reduced_target_occurrence_count"]
    )
    payload = {
        "schema": "acfqp.structural_rank_transfer_campaign.v75r4",
        "preregistration_id": preregistration_id,
        "preserved_failure_ids": list(preserved_failure_ids),
        "template_library_artifact_id": template_library_artifact_id,
        "sources": sources,
        "targets": targets,
        "typed_target_arm_failures": failures,
        "sample_tax_comparison": {
            "fresh_target_count": len(targets),
            "completed_matched_target_count": len(completed),
            "derived_target_certificate_local_labels": derived_labels,
            "strict_target_certificate_local_labels": strict_labels,
            "derived_minus_strict_target_labels": derived_labels - strict_labels,
            "reduced_target_occurrence_count": reduced_count,
            "target_occurrences_using_structural_rank_priority_count": priority_used,
            "cross_occurrence_reduction_observed": (
                bool(completed) and not failures and derived_labels < strict_labels
            ),
            "official_economics_claimed": False,
        },
        "accounting": {
            "offline_template_source_labels": offline_template_source_labels,
            "offline_residual_library_labels": config["offline_library_labels"],
            "source_labels": sum(
                row["predecessor_v75r1_source"]["predecessor_v75_source"][
                    "source_complete_episode"
                ]["predecessor_v30_episode"]["local_ground_support_labels"]
                for row in sources
            ),
            "priority_source_labels": sum(
                row["predecessor_v75r1_source"]["priority_source_episode"][
                    "target_certificate_local_ground_support_labels"
                ]
                for row in sources
            ),
            "target_common_partial_labels": sum(
                row["target_common_partial_ground_support_labels"] for row in targets
            ),
            "target_derived_certificate_local_labels": derived_labels,
            "target_strict_certificate_local_labels": strict_labels,
            "execution_steps_by_arm": {
                DERIVED_ARM: sum(row["target_arms"][DERIVED_ARM]["execution_steps"] for row in completed),
                STRICT_ARM: sum(row["target_arms"][STRICT_ARM]["execution_steps"] for row in completed),
            },
            "planning_compute_by_arm": {
                DERIVED_ARM: sum(row["target_arms"][DERIVED_ARM]["abstract_planning_compute_events"] for row in completed),
                STRICT_ARM: sum(row["target_arms"][STRICT_ARM]["abstract_planning_compute_events"] for row in completed),
            },
            "all_axes_separate": True,
        },
        "registered_gate": {
            "usable_source_count": len(sources),
            "fresh_target_occurrence_count": len(targets),
            "target_arm_failure_count": len(failures),
            "certificate_discipline_clean": certificate_clean,
            "structural_rank_priority_used_target_count": priority_used,
            "incompatible_schema_ood_rejection_count": ood_rejections,
            "actual_reduced_target_occurrence_count": reduced_count,
            "aggregate_cross_occurrence_target_reduction_observed": (
                bool(completed) and not failures and derived_labels < strict_labels
            ),
            "passed": passed,
        },
        "target_transition_outcomes_used_to_translate_priority": False,
        "source_artifacts_frozen_before_targets": True,
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
        "campaign_id": domains.extension_content_id_v75r4(
            domains.CONSTRUCTION_K7_STRUCTURAL_RANK_CAMPAIGN_V75R4_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_structural_rank_transfer_campaign_document_v75r4",)
