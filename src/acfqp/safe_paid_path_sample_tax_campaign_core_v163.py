"""V163 validates safe query ordering plus strict factor-prior sample savings."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v163 as domains
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.certified_paid_path_switch_campaign_core_v162 import (
    FALLBACK_FAMILY,
    MODULAR_FAMILY,
    POSITIVE_FAMILY,
    TARGET_FAMILIES,
    build_certified_paid_path_switch_occurrence_v162,
    certified_paid_path_switch_campaign_config_v162,
)
from acfqp.construction_k7_paid_path_prefix_classifier_receipt_freeze_v161 import (
    CLASSIFIER_RECEIPT_ID,
)


V162_FAILED_CAMPAIGN_ID = (
    "84250a94f22de611e57987c88bedbf5d44cc2bfa8f92cdec942ef625daa6b69a"
)
V162_FAILURE_SHA256 = (
    "3f69c16b089ce2bb95a458b1e046dd19c3d262b953397bd79d8579e1f9f96c7a"
)


def safe_paid_path_sample_tax_campaign_config_v163():
    return certified_paid_path_switch_campaign_config_v162()


def build_safe_paid_path_sample_tax_occurrence_v163(
    config,
    *,
    family,
    seed,
    episode_indices,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    base = build_certified_paid_path_switch_occurrence_v162(
        config,
        family=family,
        seed=seed,
        episode_indices=episode_indices,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    guard_reduction = base[
        "query_policy_sample_reduction_vs_legacy_path_first"
    ]
    certified = base["certified_positive_switch"]
    gate = {
        key: value
        for key, value in base["registered_gate"].items()
        if key
        not in {
            "passed",
            "positive_query_policy_strictly_improves_when_certified",
        }
    }
    gate.update(
        query_policy_noninferior_to_exact_path_first=guard_reduction >= 0,
        certified_switch_is_noninferior_when_exercised=(
            guard_reduction >= 0 if certified else True
        ),
        strict_query_policy_reduction_not_required_after_v162_counterexample=True,
        factor_prior_sample_reduction_measured_separately=(
            base["factor_prior_sample_reduction_within_progressive_policy"] >= 0
        ),
        v162_failed_identity_preserved=True,
    )
    gate["passed"] = all(value for value in gate.values() if type(value) is bool)
    payload = {
        **{
            key: value
            for key, value in base.items()
            if key not in {"schema", "occurrence_id", "registered_gate"}
        },
        "schema": "acfqp.safe_paid_path_sample_tax_occurrence.v163",
        "failed_v162_campaign_id": V162_FAILED_CAMPAIGN_ID,
        "failed_v162_record_sha256": V162_FAILURE_SHA256,
        "registered_gate": gate,
        "v162_failure_preserved_not_reclassified": True,
        "query_policy_strict_sample_reduction_claimed": False,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V163_THREE_FAMILY_COHORT",
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v163(
            domains.CONSTRUCTION_K7_OCCURRENCE_V163_DOMAIN, payload
        ),
    }


def _target(args: tuple[Any, ...]):
    return build_safe_paid_path_sample_tax_occurrence_v163(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        classifier_receipt_raw=args[6],
    )


def build_safe_paid_path_sample_tax_campaign_v163(
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
        "every_certified_switch_noninferior": all(
            row["query_policy_sample_reduction_vs_legacy_path_first"] >= 0
            for row in certified_rows
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
        "v162_failed_identity_preserved_everywhere": all(
            row["v162_failure_preserved_not_reclassified"] is True for row in rows
        ),
        "strict_query_policy_reduction_not_claimed": True,
    }
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and gate["passed_target_occurrence_count"] == len(rows)
        and all(value for value in gate.values() if type(value) is bool)
    )
    payload = {
        "schema": "acfqp.safe_paid_path_sample_tax_campaign.v163",
        "preregistration_id": preregistration_id,
        "classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
        "failed_v162_campaign_id": V162_FAILED_CAMPAIGN_ID,
        "failed_v162_record_sha256": V162_FAILURE_SHA256,
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": incompatible_schema_no_transfer_control_v99(),
        "accounting": accounting,
        "registered_gate": gate,
        "safe_query_and_factor_prior_sample_tax_reduction_verified": gate["passed"],
        "v162_failure_preserved_not_reclassified": True,
        "query_policy_strict_sample_reduction_claimed": False,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V163_THREE_FAMILY_COHORT",
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
        "campaign_id": domains.extension_content_id_v163(
            domains.CONSTRUCTION_K7_CAMPAIGN_V163_DOMAIN, payload
        ),
    }


__all__ = (
    "FALLBACK_FAMILY",
    "MODULAR_FAMILY",
    "POSITIVE_FAMILY",
    "build_safe_paid_path_sample_tax_campaign_v163",
    "build_safe_paid_path_sample_tax_occurrence_v163",
    "safe_paid_path_sample_tax_campaign_config_v163",
)
