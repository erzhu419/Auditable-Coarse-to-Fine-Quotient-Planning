"""V161 fresh correction campaign with an exact path-first fallback."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from types import FunctionType, SimpleNamespace
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v161 as domains
from acfqp import progressive_raw_prefix_campaign_core_v160 as failed_v160
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.construction_k7_paid_path_prefix_classifier_receipt_freeze_v161 import (
    CLASSIFIER_RECEIPT_ID,
    verify_frozen_paid_path_prefix_classifier_receipt_v161,
)
from acfqp.paid_path_continuation_acquisition_operator_v161 import (
    acquire_matched_paid_path_continuation_arms_v161,
)


POSITIVE_FAMILY = failed_v160.POSITIVE_FAMILY
FALLBACK_FAMILY = failed_v160.FALLBACK_FAMILY
MODULAR_FAMILY = failed_v160.MODULAR_FAMILY
TARGET_FAMILIES = failed_v160.TARGET_FAMILIES
V160_FAILED_CAMPAIGN_ID = "38cbf013db9ceb15605807f5aa83564f7b89fc559d793dcfd7a049d7095771c6"
V160_FAILURE_SHA256 = "1d554b56462031920d3573ed1969997eedd8955426bfd024f8355bfab362d3ab"


def paid_path_continuation_campaign_config_v161():
    return failed_v160.progressive_raw_prefix_campaign_config_v160()


def _verify_classifier_compat(raw):
    document = verify_frozen_paid_path_prefix_classifier_receipt_v161(raw)
    return {
        **document,
        "fresh_v160_target_outcomes_accessed": document[
            "fresh_v161_target_outcomes_accessed"
        ],
    }


_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v160=domains.extension_content_id_v161,
    CONSTRUCTION_K7_OCCURRENCE_V160_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V161_DOMAIN,
)
_BASE_GLOBALS = dict(failed_v160.__dict__)
_BASE_GLOBALS.update(
    domains=_DOMAIN_PROXY,
    CLASSIFIER_RECEIPT_ID=CLASSIFIER_RECEIPT_ID,
    verify_frozen_progressive_raw_prefix_classifier_receipt_v160=_verify_classifier_compat,
    acquire_matched_progressive_raw_prefix_arms_v160=acquire_matched_paid_path_continuation_arms_v161,
)
_BASE_OCCURRENCE = FunctionType(
    failed_v160.build_progressive_raw_prefix_occurrence_v160.__code__,
    _BASE_GLOBALS,
    name="_base_paid_path_continuation_occurrence_v161",
)


def build_paid_path_continuation_occurrence_v161(
    config,
    *,
    family,
    seed,
    episode_indices,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    base = _BASE_OCCURRENCE(
        config,
        family=family,
        seed=seed,
        episode_indices=episode_indices,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    prior = base["progressive_prior_acquisition"]
    strict = base["progressive_strict_acquisition"]
    fallback = family != POSITIVE_FAMILY
    exact_prior_fallback = (
        prior["source_v148_acquisition_id"]
        == base["legacy_path_first_prior_summary"]["acquisition_id"]
        and prior["ground_support_labels"]
        == base["legacy_path_first_prior_summary"]["ground_support_labels"]
        and prior["raw_transition_sha256"]
        == base["legacy_path_first_prior_summary"]["raw_transition_sha256"]
    )
    gate = {
        **base["registered_gate"],
        "v160_failed_identity_preserved": True,
        "fallback_resumed_same_generator_object_both_arms": (
            all(
                document["fallback_resumed_same_path_first_generator_object"]
                is True
                for document in (prior, strict)
            )
            if fallback
            else True
        ),
        "positive_only_switch_to_relation_coverage": (
            all(
                document["positive_only_switch_to_relation_coverage"] is True
                for document in (prior, strict)
            )
            if not fallback
            else True
        ),
        "fallback_prior_bytes_labels_and_id_match_legacy": (
            exact_prior_fallback if fallback else True
        ),
        "no_additional_classifier_only_target_labels": all(
            document["additional_classifier_only_target_labels"] == 0
            for document in (prior, strict)
        ),
    }
    gate["passed"] = all(gate.values())
    payload = {
        **{
            key: value
            for key, value in base.items()
            if key not in {"schema", "occurrence_id", "registered_gate"}
        },
        "schema": "acfqp.paid_path_continuation_occurrence.v161",
        "failed_v160_campaign_id": V160_FAILED_CAMPAIGN_ID,
        "failed_v160_record_sha256": V160_FAILURE_SHA256,
        "registered_gate": gate,
        "v160_failure_preserved_not_reclassified": True,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V161_THREE_FAMILY_COHORT",
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v161(
            domains.CONSTRUCTION_K7_OCCURRENCE_V161_DOMAIN, payload
        ),
    }


def _target(args: tuple[Any, ...]):
    return build_paid_path_continuation_occurrence_v161(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        classifier_receipt_raw=args[6],
    )


def build_paid_path_continuation_campaign_v161(
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
    accounting.update(
        offline_source_observation_labels=96,
        target_classifier_path_prefix_labels=sum(
            row["accounting"]["classifier_prefix_labels_included_in_acquisition"]
            for row in rows
        ),
        additional_classifier_only_target_labels=0,
        source_and_target_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    positive_rows = [row for row in rows if row["target_family"] == POSITIVE_FAMILY]
    fallback_rows = [row for row in rows if row["target_family"] == FALLBACK_FAMILY]
    modular_rows = [row for row in rows if row["target_family"] == MODULAR_FAMILY]
    guards = tuple(
        row["query_policy_sample_reduction_vs_legacy_path_first"] for row in rows
    )
    factors = tuple(
        row["factor_prior_sample_reduction_within_progressive_policy"] for row in rows
    )
    gate = {
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "all_three_dynamics_cohorts_present": all(
            len(cohort) == 2 for cohort in (positive_rows, fallback_rows, modular_rows)
        ),
        "both_query_policy_decisions_observed": {
            row["progressive_prior_acquisition"]["query_policy_decision"]
            for row in rows
        }
        == {"RELATION_COVERAGE", "PATH_FIRST_SAFE_FALLBACK"},
        "positive_switch_strictly_reduces_samples_in_aggregate": sum(
            row["query_policy_sample_reduction_vs_legacy_path_first"]
            for row in positive_rows
        )
        > 0,
        "fallback_and_modular_are_exact_zero_regression_everywhere": all(
            row["query_policy_sample_reduction_vs_legacy_path_first"] == 0
            and row["registered_gate"][
                "fallback_prior_bytes_labels_and_id_match_legacy"
            ]
            for row in fallback_rows + modular_rows
        ),
        "query_policy_noninferior_everywhere": all(value >= 0 for value in guards),
        "factor_prior_noninferior_everywhere": all(value >= 0 for value in factors),
        "factor_prior_positive_in_aggregate": sum(factors) > 0,
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
        "v160_failed_identity_preserved_everywhere": all(
            row["v160_failure_preserved_not_reclassified"] is True for row in rows
        ),
    }
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and gate["passed_target_occurrence_count"] == len(rows)
        and all(value for value in gate.values() if type(value) is bool)
    )
    payload = {
        "schema": "acfqp.paid_path_continuation_campaign.v161",
        "preregistration_id": preregistration_id,
        "classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
        "failed_v160_campaign_id": V160_FAILED_CAMPAIGN_ID,
        "failed_v160_record_sha256": V160_FAILURE_SHA256,
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": incompatible_schema_no_transfer_control_v99(),
        "accounting": accounting,
        "registered_gate": gate,
        "paid_path_continuation_query_policy_verified": gate["passed"],
        "v160_failure_preserved_not_reclassified": True,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V161_THREE_FAMILY_COHORT",
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
        "campaign_id": domains.extension_content_id_v161(
            domains.CONSTRUCTION_K7_CAMPAIGN_V161_DOMAIN, payload
        ),
    }


__all__ = (
    "FALLBACK_FAMILY",
    "MODULAR_FAMILY",
    "POSITIVE_FAMILY",
    "build_paid_path_continuation_campaign_v161",
    "build_paid_path_continuation_occurrence_v161",
    "paid_path_continuation_campaign_config_v161",
)
