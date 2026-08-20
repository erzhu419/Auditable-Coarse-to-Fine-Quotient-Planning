"""V77 three-family successor with typed source abstention."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v77 as domains
from acfqp import portable_priority_cross_occurrence_campaign_core_v75r1 as v75r1
from acfqp import three_family_cross_occurrence_campaign_core_v76 as v76
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_structural_rank_query_prior_v46 import (
    compile_structural_rank_query_prior_v46,
)


FILTERED = v76.FILTERED
MODEL_ONLY = v76.MODEL_ONLY
STRICT = v76.STRICT
ARMS = v76.ARMS


def _source(args: tuple[Any, ...]) -> dict[str, Any]:
    family, seed, _factor, _residual, _template, config = args
    predecessor = v75r1._build_priority_source(args)  # noqa: SLF001
    model = predecessor["predecessor_v75_source"][
        "reusable_joint_successor_version_space_model"
    ]
    prior = None
    status = "SOURCE_MODEL_ABSTAINED_NONCERTIFICATE"
    if model is not None and predecessor["priority_source_episode"] is not None:
        adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
            family, seed, config
        )
        prior = compile_structural_rank_query_prior_v46(
            predecessor["priority_source_episode"],
            model["source_layout"],
            adapter.catalogue,
        )
        status = "SOURCE_MODEL_AND_RANK_PRIOR_AVAILABLE"
    payload = {
        "schema": "acfqp.fail_closed_three_family_source.v77",
        "family": family,
        "source_seed": seed,
        "predecessor_v75r1_source": predecessor,
        "reusable_joint_successor_version_space_model": model,
        "structural_rank_query_prior": prior,
        "source_status": status,
        "source_abstention_retained_as_typed_noncertificate": model is None,
        "fresh_target_outcomes_used_to_fit_source_artifacts": False,
    }
    return {
        **payload,
        "source_id": domains.extension_content_id_v77(
            domains.CONSTRUCTION_K7_THREE_FAMILY_SOURCE_V77_DOMAIN, payload
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    predecessor = v76._target(args)  # noqa: SLF001
    payload = {
        "schema": "acfqp.fail_closed_three_family_target.v77",
        "predecessor_v76_target": predecessor,
        "family": predecessor["family"],
        "source_id": predecessor["source_id"],
        "source_seed": predecessor["source_seed"],
        "target_seed": predecessor["target_seed"],
        "target_common_partial_acquisition_id": predecessor[
            "target_common_partial_acquisition_id"
        ],
        "target_common_partial_ground_support_labels": predecessor[
            "target_common_partial_ground_support_labels"
        ],
        "source_model_id": predecessor["source_model_id"],
        "abstract_agreement_filter": predecessor["abstract_agreement_filter"],
        "target_arms": predecessor["target_arms"],
        "incompatible_schema_ood_control": predecessor[
            "incompatible_schema_ood_control"
        ],
        "target_transition_outcomes_used_to_filter_priority": False,
        "query_local_overlay_only_safety_authority": True,
    }
    return {
        **payload,
        "target_id": domains.extension_content_id_v77(
            domains.CONSTRUCTION_K7_THREE_FAMILY_TARGET_V77_DOMAIN, payload
        ),
    }


def _success(row: Mapping[str, Any], arm: str) -> bool:
    return row["target_arms"][arm].get("success") is True


def build_fail_closed_three_family_campaign_document_v77(
    config: Mapping[str, Any],
    preregistration_id: str,
    v76_failure_id: str,
    v75r5_campaign_id: str,
    v75r5_verification_id: str,
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
    usable = [
        row for row in sources
        if row["reusable_joint_successor_version_space_model"] is not None
        and row["structural_rank_query_prior"] is not None
    ]
    source_by_family = {row["family"]: row for row in usable}
    target_args = [
        (source_by_family[family], seed, factor_library, config)
        for family, seeds in config["fresh_target_seeds"].items()
        for seed in seeds
        if family in source_by_family
    ]
    with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
        targets = list(executor.map(_target, target_args))
    completed = [row for row in targets if all(_success(row, arm) for arm in ARMS)]
    failures = [
        {
            "family": row["family"],
            "target_seed": row["target_seed"],
            "arm": arm,
            "reason": row["target_arms"][arm].get("reason"),
        }
        for row in targets for arm in ARMS if not _success(row, arm)
    ]
    labels = {
        arm: sum(
            row["target_arms"][arm]["target_certificate_local_ground_support_labels"]
            for row in completed
        )
        for arm in ARMS
    }
    matched = all(
        row["target_arms"][FILTERED]["action_keys"]
        == row["target_arms"][MODEL_ONLY]["action_keys"]
        and row["target_arms"][FILTERED]["target_certificate_local_ground_support_labels"]
        == row["target_arms"][MODEL_ONLY]["target_certificate_local_ground_support_labels"]
        for row in completed
    )
    reduced = sum(
        row["target_arms"][FILTERED]["target_certificate_local_ground_support_labels"]
        < row["target_arms"][STRICT]["target_certificate_local_ground_support_labels"]
        for row in completed
    )
    certificate_clean = all(
        arm["all_ground_queries_followed_failed_certificates"] is True
        and arm["query_local_exact_overlay_exclusively_used_for_safety"] is True
        and arm["reusable_artifacts_used_as_safety_authority"] is False
        for row in completed for arm in row["target_arms"].values()
    )
    ood = sum(
        row["incompatible_schema_ood_control"]["status"]
        == "INCOMPATIBLE_SCHEMA_REJECTED_BEFORE_GROUND_QUERY"
        for row in targets
    )
    passed = (
        len(usable) == 3
        and len(targets) == 6
        and not failures
        and matched
        and certificate_clean
        and ood == 6
        and labels[FILTERED] <= labels[STRICT]
        and reduced >= config["minimum_reduced_target_occurrence_count"]
    )
    payload = {
        "schema": "acfqp.fail_closed_three_family_campaign.v77",
        "preregistration_id": preregistration_id,
        "v76_failure_id": v76_failure_id,
        "v75r5_campaign_id": v75r5_campaign_id,
        "v75r5_verification_id": v75r5_verification_id,
        "template_library_artifact_id": template_library_artifact_id,
        "sources": sources,
        "usable_source_ids": [row["source_id"] for row in usable],
        "targets": targets,
        "typed_source_abstention_count": len(sources) - len(usable),
        "typed_target_arm_failures": failures,
        "sample_tax_comparison": {
            "labels_by_arm": labels,
            "filtered_minus_strict_labels": labels[FILTERED] - labels[STRICT],
            "filtered_matches_model_only_per_target": matched,
            "reduced_target_occurrence_count": reduced,
            "three_family_cross_occurrence_noninferiority_observed": (
                len(usable) == 3 and bool(completed) and labels[FILTERED] <= labels[STRICT]
            ),
            "official_economics_claimed": False,
        },
        "accounting": {
            "offline_template_source_labels": offline_template_source_labels,
            "offline_residual_library_labels": config["offline_library_labels"],
            "target_common_partial_labels": sum(
                row["target_common_partial_ground_support_labels"] for row in targets
            ),
            "target_certificate_labels_by_arm": labels,
            "execution_steps_by_arm": {
                arm: sum(row["target_arms"][arm]["execution_steps"] for row in completed)
                for arm in ARMS
            },
            "planning_compute_by_arm": {
                arm: sum(row["target_arms"][arm]["abstract_planning_compute_events"] for row in completed)
                for arm in ARMS
            },
            "all_axes_separate": True,
        },
        "registered_gate": {
            "source_family_count": len(sources),
            "usable_source_family_count": len(usable),
            "fresh_target_occurrence_count": len(targets),
            "target_arm_failure_count": len(failures),
            "filtered_matches_model_only_per_target": matched,
            "certificate_discipline_clean": certificate_clean,
            "incompatible_schema_ood_rejection_count": ood,
            "filtered_not_worse_than_strict": labels[FILTERED] <= labels[STRICT],
            "actual_reduced_target_occurrence_count": reduced,
            "passed": passed,
        },
        "source_abstentions_retained_before_target_execution": True,
        "target_transition_outcomes_used_to_filter_priority": False,
        "all_ground_queries_followed_failed_certificates": certificate_clean,
        "query_local_exact_overlay_exclusively_used_for_safety": certificate_clean,
        "producer_free_verification_present": False,
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "cross_family_model_transfer_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v77(
            domains.CONSTRUCTION_K7_THREE_FAMILY_CAMPAIGN_V77_DOMAIN, payload
        ),
    }


__all__ = ("build_fail_closed_three_family_campaign_document_v77",)
