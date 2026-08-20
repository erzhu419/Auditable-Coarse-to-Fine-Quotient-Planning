"""V76 three-family cross-occurrence abstract-model validation."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import agreement_filtered_priority_campaign_core_v75r5 as predecessor
from acfqp import construction_k7_domain_registry_extension_v76 as domains
from acfqp import normalized_portable_priority_campaign_core_v75r2 as v75r2
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_abstract_agreement_query_filter_v47 import (
    apply_abstract_agreement_query_filter_v47,
)
from acfqp.generic_flat_action_adapter_v45 import normalize_flat_action_adapter_v45
from acfqp.generic_structural_rank_query_prior_v46 import (
    translate_structural_rank_prior_to_initial_v44_priority_v46,
)


FILTERED = "AGREEMENT_FILTERED_MODEL"
MODEL_ONLY = "MODEL_ONLY_MATCHED_ENGINE"
STRICT = "STRICT_NO_MODEL_OR_PRIORITY"
ARMS = (FILTERED, MODEL_ONLY, STRICT)


def _source(args: tuple[Any, ...]) -> dict[str, Any]:
    row = predecessor._source(args)  # noqa: SLF001
    payload = {
        "schema": "acfqp.three_family_cross_occurrence_source.v76",
        "family": row["family"],
        "source_seed": row["source_seed"],
        "predecessor_v75r5_source": row,
        "reusable_joint_successor_version_space_model": row[
            "reusable_joint_successor_version_space_model"
        ],
        "structural_rank_query_prior": row["structural_rank_query_prior"],
        "fresh_target_outcomes_used_to_fit_source_artifacts": False,
    }
    return {
        **payload,
        "source_id": domains.extension_content_id_v76(
            domains.CONSTRUCTION_K7_THREE_FAMILY_SOURCE_V76_DOMAIN, payload
        ),
    }


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
    filtered = apply_abstract_agreement_query_filter_v47(
        model,
        partial["candidate"],
        adapter,
        translated,
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_support_branch_evaluations=config[
            "maximum_relational_support_branch_evaluations"
        ],
        support_feasible_beam_width=config["relational_support_feasible_beam_width"],
    )
    arms = {
        FILTERED: v75r2._arm(  # noqa: SLF001
            adapter,
            partial["candidate"],
            partial["rows"],
            model,
            filtered["filtered_priority"],
            config,
        ),
        MODEL_ONLY: v75r2._arm(  # noqa: SLF001
            adapter,
            partial["candidate"],
            partial["rows"],
            model,
            filtered["model_only_inert_priority"],
            config,
        ),
        STRICT: v75r2._arm(  # noqa: SLF001
            adapter, partial["candidate"], partial["rows"], None, None, config
        ),
    }
    payload = {
        "schema": "acfqp.three_family_cross_occurrence_target.v76",
        "family": source["family"],
        "source_id": source["source_id"],
        "source_seed": source["source_seed"],
        "target_seed": target_seed,
        "target_common_partial_acquisition_id": partial["document"]["acquisition_id"],
        "target_common_partial_ground_support_labels": partial["document"][
            "ground_support_labels"
        ],
        "source_model_id": model["joint_successor_version_space_model_id"],
        "structural_rank_query_translation": translated["translation_receipt"],
        "abstract_agreement_filter": filtered["agreement_filter_receipt"],
        "target_arms": arms,
        "incompatible_schema_ood_control": v75r2._ood(  # noqa: SLF001
            adapter,
            partial["candidate"],
            model,
            filtered["filtered_priority"],
            config,
        ),
        "source_and_target_seed_identities_disjoint": source["source_seed"] != target_seed,
        "target_transition_outcomes_used_to_filter_priority": False,
        "query_local_overlay_only_safety_authority": True,
    }
    return {
        **payload,
        "target_id": domains.extension_content_id_v76(
            domains.CONSTRUCTION_K7_THREE_FAMILY_TARGET_V76_DOMAIN, payload
        ),
    }


def _success(row: Mapping[str, Any], arm: str) -> bool:
    return row["target_arms"][arm].get("success") is True


def build_three_family_cross_occurrence_campaign_document_v76(
    config: Mapping[str, Any],
    preregistration_id: str,
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
    by_family = {row["family"]: row for row in sources}
    target_args = [
        (by_family[family], seed, factor_library, config)
        for family, seeds in config["fresh_target_seeds"].items()
        for seed in seeds
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
        for row in targets
        for arm in ARMS
        if not _success(row, arm)
    ]
    labels = {
        arm: sum(
            row["target_arms"][arm]["target_certificate_local_ground_support_labels"]
            for row in completed
        )
        for arm in ARMS
    }
    per_family = {
        family: {
            "filtered_labels": sum(
                row["target_arms"][FILTERED]["target_certificate_local_ground_support_labels"]
                for row in completed if row["family"] == family
            ),
            "strict_labels": sum(
                row["target_arms"][STRICT]["target_certificate_local_ground_support_labels"]
                for row in completed if row["family"] == family
            ),
        }
        for family in config["source_seed_by_family"]
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
        len(sources) == 3
        and len(targets) == 6
        and not failures
        and matched
        and certificate_clean
        and ood == 6
        and labels[FILTERED] <= labels[STRICT]
        and reduced >= config["minimum_reduced_target_occurrence_count"]
    )
    payload = {
        "schema": "acfqp.three_family_cross_occurrence_campaign.v76",
        "preregistration_id": preregistration_id,
        "v75r5_campaign_id": v75r5_campaign_id,
        "v75r5_verification_id": v75r5_verification_id,
        "template_library_artifact_id": template_library_artifact_id,
        "sources": sources,
        "targets": targets,
        "typed_target_arm_failures": failures,
        "sample_tax_comparison": {
            "labels_by_arm": labels,
            "per_family_labels": per_family,
            "filtered_minus_strict_labels": labels[FILTERED] - labels[STRICT],
            "filtered_matches_model_only_per_target": matched,
            "reduced_target_occurrence_count": reduced,
            "three_family_cross_occurrence_noninferiority_observed": (
                bool(completed) and labels[FILTERED] <= labels[STRICT]
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
            "fresh_target_occurrence_count": len(targets),
            "target_arm_failure_count": len(failures),
            "filtered_matches_model_only_per_target": matched,
            "certificate_discipline_clean": certificate_clean,
            "incompatible_schema_ood_rejection_count": ood,
            "filtered_not_worse_than_strict": labels[FILTERED] <= labels[STRICT],
            "actual_reduced_target_occurrence_count": reduced,
            "passed": passed,
        },
        "target_transition_outcomes_used_to_filter_priority": False,
        "source_artifacts_frozen_before_targets": True,
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
        "campaign_id": domains.extension_content_id_v76(
            domains.CONSTRUCTION_K7_THREE_FAMILY_CAMPAIGN_V76_DOMAIN, payload
        ),
    }


__all__ = ("build_three_family_cross_occurrence_campaign_document_v76",)
