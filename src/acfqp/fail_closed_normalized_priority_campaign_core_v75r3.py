"""Fail-closed V75r3 wrapper that retains every target-arm outcome."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v75r3 as domains
from acfqp import normalized_portable_priority_campaign_core_v75r2 as predecessor


DERIVED_ARM = "NORMALIZED_PORTABLE_PRIORITY_AND_REUSABLE_MODEL"
STRICT_ARM = "STRICT_NORMALIZED_NO_REUSABLE_ARTIFACTS"


def _successful(row: Mapping[str, Any], arm: str) -> bool:
    return row["target_arms"][arm].get("success") is True


def build_fail_closed_normalized_priority_campaign_document_v75r3(
    config: Mapping[str, Any],
    preregistration_id: str,
    v75_failure_id: str,
    v75r1_failure_id: str,
    v75r2_failure_id: str,
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
        sources = list(executor.map(predecessor._source, source_args))  # noqa: SLF001
    usable = [row for row in sources if row["portable_query_priority"] is not None]
    source_by_family = {row["family"]: row for row in usable}
    target_args = [
        (source_by_family[family], seed, factor_library, config)
        for family, seeds in config["fresh_target_seeds"].items()
        for seed in seeds
        if family in source_by_family
    ]
    with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
        targets = list(executor.map(predecessor._target, target_args))  # noqa: SLF001
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
        row["target_arms"][DERIVED_ARM][
            "target_certificate_local_ground_support_labels"
        ]
        for row in completed
    )
    strict_labels = sum(
        row["target_arms"][STRICT_ARM]["target_certificate_local_ground_support_labels"]
        for row in completed
    )
    reduced_count = sum(
        row["target_arms"][DERIVED_ARM][
            "target_certificate_local_ground_support_labels"
        ]
        < row["target_arms"][STRICT_ARM]["target_certificate_local_ground_support_labels"]
        for row in completed
    )
    priority_used = sum(
        row["target_arms"][DERIVED_ARM]["portable_priority_ordering_accepted_count"]
        > 0
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
    gate_passed = (
        len(usable) == config["required_usable_source_count"]
        and len(targets) == config["fresh_target_occurrence_count"]
        and not failures
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
        "schema": "acfqp.fail_closed_normalized_priority_campaign.v75r3",
        "preregistration_id": preregistration_id,
        "preserved_failure_ids": [v75_failure_id, v75r1_failure_id, v75r2_failure_id],
        "template_library_artifact_id": template_library_artifact_id,
        "sources": sources,
        "targets": targets,
        "typed_target_arm_failures": failures,
        "sample_tax_comparison": {
            "fresh_cross_occurrence_target_count": len(targets),
            "completed_matched_target_count": len(completed),
            "derived_target_certificate_local_labels": derived_labels,
            "strict_target_certificate_local_labels": strict_labels,
            "derived_minus_strict_target_labels": derived_labels - strict_labels,
            "reduced_target_occurrence_count": reduced_count,
            "target_occurrences_using_portable_priority_count": priority_used,
            "normalized_portable_priority_reduction_observed": (
                bool(completed) and not failures and derived_labels < strict_labels
            ),
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
            "usable_source_count": len(usable),
            "fresh_target_occurrence_count": len(targets),
            "target_arm_failure_count": len(failures),
            "certificate_discipline_clean": certificate_clean,
            "portable_priority_used_target_count": priority_used,
            "incompatible_schema_ood_rejection_count": ood_rejections,
            "actual_reduced_target_occurrence_count": reduced_count,
            "aggregate_cross_occurrence_target_reduction_observed": (
                bool(completed) and not failures and derived_labels < strict_labels
            ),
            "passed": gate_passed,
        },
        "failed_target_arms_retained_before_aggregation": True,
        "source_artifacts_frozen_before_targets": True,
        "target_outcomes_used_to_refit_source_artifacts": False,
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
        "campaign_id": domains.extension_content_id_v75r3(
            domains.CONSTRUCTION_K7_FAIL_CLOSED_PRIORITY_CAMPAIGN_V75R3_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_fail_closed_normalized_priority_campaign_document_v75r3",)
