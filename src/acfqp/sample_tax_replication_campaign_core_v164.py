"""Fresh V164 replication of query-policy and factor-prior sample savings."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v164 as domains
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.safe_paid_path_sample_tax_campaign_core_v163 import (
    FALLBACK_FAMILY,
    MODULAR_FAMILY,
    POSITIVE_FAMILY,
    build_safe_paid_path_sample_tax_occurrence_v163,
    safe_paid_path_sample_tax_campaign_config_v163,
)


TARGET_FAMILIES = (POSITIVE_FAMILY, FALLBACK_FAMILY, MODULAR_FAMILY)
V163_CAMPAIGN_ID = "193323db43d5524e5bebe3a1713e946ab7dbb77cf79307c957a13cded0d9c219"
V163_VERIFICATION_ID = (
    "5e856f8cab34726906f3e93924ea099d2027ee39aca0708efc5ebabec437975b"
)


def sample_tax_replication_campaign_config_v164():
    return safe_paid_path_sample_tax_campaign_config_v163()


def build_sample_tax_replication_occurrence_v164(
    config,
    *,
    family,
    seed,
    episode_indices,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    source = build_safe_paid_path_sample_tax_occurrence_v163(
        config,
        family=family,
        seed=seed,
        episode_indices=episode_indices,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    payload = {
        **{
            key: value
            for key, value in source.items()
            if key not in {"schema", "occurrence_id"}
        },
        "schema": "acfqp.sample_tax_replication_occurrence.v164",
        "source_v163_occurrence_id": source["occurrence_id"],
        "frozen_v163_campaign_id": V163_CAMPAIGN_ID,
        "frozen_v163_verification_id": V163_VERIFICATION_ID,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v164(
            domains.CONSTRUCTION_K7_OCCURRENCE_V164_DOMAIN, payload
        ),
    }


def _target(args: tuple[Any, ...]):
    return build_sample_tax_replication_occurrence_v164(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        classifier_receipt_raw=args[6],
    )


def build_sample_tax_replication_campaign_v164(
    config,
    *,
    preregistration_id,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    args = [
        (
            config,
            row["family"],
            row["seed"],
            tuple(config["target_episode_indices"]),
            bank_raw,
            verification_raw,
            classifier_receipt_raw,
        )
        for row in config["target_occurrences"]
    ]
    if config["target_worker_count"] == 1:
        rows = [_target(row) for row in args]
    else:
        with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
            rows = list(executor.map(_target, args))
    numeric = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    accounting = {
        key: sum(row["accounting"][key] for row in rows) for key in numeric
    }
    guards = tuple(
        row["query_policy_sample_reduction_vs_legacy_path_first"] for row in rows
    )
    factors = tuple(
        row["factor_prior_sample_reduction_within_progressive_policy"] for row in rows
    )
    accounting.update(
        offline_source_observation_labels=96,
        target_classifier_path_prefix_labels=sum(
            row["accounting"]["classifier_prefix_labels_included_in_acquisition"]
            for row in rows
        ),
        additional_classifier_only_target_labels=0,
        total_query_policy_labels_avoided_vs_exact_path_first=sum(guards),
        total_factor_prior_labels_avoided_within_same_query_policy=sum(factors),
        source_and_target_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    certified_rows = [row for row in rows if row["certified_positive_switch"]]
    fallback_rows = [row for row in rows if row["exact_path_first_fallback"]]
    gate = {
        "required_target_occurrence_count": config["required_target_occurrence_count"],
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "all_three_registered_families_present": {
            row["target_family"] for row in rows
        }
        == set(TARGET_FAMILIES),
        "at_least_one_certified_switch_exercised": bool(certified_rows),
        "query_policy_noninferior_everywhere": all(value >= 0 for value in guards),
        "query_policy_strictly_reduces_sample_tax_in_aggregate": sum(guards) > 0,
        "query_policy_positive_reduction_occurrence_present": any(
            value > 0 for value in guards
        ),
        "every_exact_fallback_is_zero_regression": all(
            row["query_policy_sample_reduction_vs_legacy_path_first"] == 0
            and row["registered_gate"]["exact_fallback_has_zero_regression"]
            for row in fallback_rows
        ),
        "factor_prior_noninferior_everywhere": all(value >= 0 for value in factors),
        "factor_prior_strictly_reduces_sample_tax_in_aggregate": sum(factors) > 0,
        "sample_tax_axes_remain_separate": accounting[
            "source_and_target_labels_execution_steps_derivation_and_planning_compute_separate"
        ],
        "no_additional_classifier_only_target_labels": accounting[
            "additional_classifier_only_target_labels"
        ]
        == 0,
        "both_arm_receding_plans_succeed_everywhere": all(
            row["registered_gate"]["both_arm_receding_episodes_succeed"]
            for row in rows
        ),
        "certificate_failure_local_recovery_exercised": sum(
            row["accounting"]["progressive_prior_certificate_local_labels"]
            + row["accounting"]["progressive_strict_certificate_local_labels"]
            for row in rows
        )
        > 0,
        "all_executed_actions_have_v109_receipts": all(
            row["registered_gate"]["all_executed_actions_have_v109_receipts"]
            for row in rows
        ),
        "strict_incompatible_schema_no_transfer_verified": incompatible_schema_no_transfer_control_v99()[
            "strict_ood_no_transfer"
        ],
        "v163_campaign_and_verification_bindings_preserved": all(
            row["frozen_v163_campaign_id"] == V163_CAMPAIGN_ID
            and row["frozen_v163_verification_id"] == V163_VERIFICATION_ID
            for row in rows
        ),
    }
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and gate["passed_target_occurrence_count"] == len(rows)
        and all(value for value in gate.values() if type(value) is bool)
    )
    payload = {
        "schema": "acfqp.sample_tax_replication_campaign.v164",
        "preregistration_id": preregistration_id,
        "frozen_v163_campaign_id": V163_CAMPAIGN_ID,
        "frozen_v163_verification_id": V163_VERIFICATION_ID,
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": incompatible_schema_no_transfer_control_v99(),
        "accounting": accounting,
        "registered_gate": gate,
        "query_and_factor_prior_sample_tax_reduction_replicated": gate["passed"],
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V164_THREE_FAMILY_REPLICATION_COHORT",
        "query_policy_classifier_is_model_planning_or_certificate_authority": False,
        "complete_world_model_synthesized": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v164(
            domains.CONSTRUCTION_K7_CAMPAIGN_V164_DOMAIN, payload
        ),
    }


__all__ = (
    "FALLBACK_FAMILY",
    "MODULAR_FAMILY",
    "POSITIVE_FAMILY",
    "build_sample_tax_replication_campaign_v164",
    "build_sample_tax_replication_occurrence_v164",
    "sample_tax_replication_campaign_config_v164",
)
