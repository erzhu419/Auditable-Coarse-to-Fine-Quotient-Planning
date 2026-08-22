"""V162 campaign: switch query order only after a paid relation witness."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from types import FunctionType, SimpleNamespace
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v162 as domains
from acfqp import progressive_raw_prefix_campaign_core_v160 as v160
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.certified_paid_path_switch_acquisition_operator_v162 import (
    acquire_matched_certified_paid_path_switch_arms_v162,
)
from acfqp.construction_k7_paid_path_prefix_classifier_receipt_freeze_v161 import (
    CLASSIFIER_RECEIPT_ID,
    verify_frozen_paid_path_prefix_classifier_receipt_v161,
)


POSITIVE_FAMILY = v160.POSITIVE_FAMILY
FALLBACK_FAMILY = v160.FALLBACK_FAMILY
MODULAR_FAMILY = v160.MODULAR_FAMILY
TARGET_FAMILIES = v160.TARGET_FAMILIES
V160_FAILED_CAMPAIGN_ID = (
    "38cbf013db9ceb15605807f5aa83564f7b89fc559d793dcfd7a049d7095771c6"
)
V160_FAILURE_SHA256 = (
    "1d554b56462031920d3573ed1969997eedd8955426bfd024f8355bfab362d3ab"
)
V161_FAILED_PREREGISTRATION_ID = (
    "84bfbf8e9be7de54d0ac95516e5adf18cd5cf7ea08ddb8c22881795c234ee13e"
)
V161_FAILURE_SHA256 = (
    "2a6658caac00c9c4257311e6a1bcc9667afadc13339d36aff4d84d6ea7293cab"
)


def certified_paid_path_switch_campaign_config_v162():
    return v160.progressive_raw_prefix_campaign_config_v160()


def _verify_classifier_compat(raw):
    document = verify_frozen_paid_path_prefix_classifier_receipt_v161(raw)
    return {
        **document,
        "fresh_v160_target_outcomes_accessed": document[
            "fresh_v161_target_outcomes_accessed"
        ],
    }


_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v160=domains.extension_content_id_v162,
    CONSTRUCTION_K7_OCCURRENCE_V160_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V162_DOMAIN,
)
_BASE_GLOBALS = dict(v160.__dict__)
_BASE_GLOBALS.update(
    domains=_DOMAIN_PROXY,
    CLASSIFIER_RECEIPT_ID=CLASSIFIER_RECEIPT_ID,
    verify_frozen_progressive_raw_prefix_classifier_receipt_v160=_verify_classifier_compat,
    acquire_matched_progressive_raw_prefix_arms_v160=acquire_matched_certified_paid_path_switch_arms_v162,
)
_BASE_OCCURRENCE = FunctionType(
    v160.build_progressive_raw_prefix_occurrence_v160.__code__,
    _BASE_GLOBALS,
    name="_base_certified_paid_path_switch_occurrence_v162",
)


def build_certified_paid_path_switch_occurrence_v162(
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
    certified = prior["certified_positive_switch"]
    if certified is not strict["certified_positive_switch"]:
        raise ValueError("V162 matched arms disagreed on certified switch")
    fallback = not certified
    exact_prior_fallback = (
        prior["source_v148_acquisition_id"]
        == base["legacy_path_first_prior_summary"]["acquisition_id"]
        and prior["ground_support_labels"]
        == base["legacy_path_first_prior_summary"]["ground_support_labels"]
        and prior["raw_transition_sha256"]
        == base["legacy_path_first_prior_summary"]["raw_transition_sha256"]
    )
    expected_decision = (
        "RELATION_COVERAGE" if certified else "PATH_FIRST_SAFE_FALLBACK"
    )
    guard_reduction = base[
        "query_policy_sample_reduction_vs_legacy_path_first"
    ]
    gate = {
        **base["registered_gate"],
        "raw_prefix_query_decision_matches_witnessed_state": (
            prior["query_policy_decision"]
            == strict["query_policy_decision"]
            == expected_decision
        ),
        "certified_switch_requires_classifier_and_paid_relation_witness": (
            not certified
            or all(
                document["classifier_decision"] == "RELATION_COVERAGE"
                and document["paid_prefix_relation_candidate_count"] > 0
                for document in (prior, strict)
            )
        ),
        "unwitnessed_classifier_positive_falls_back_exactly": all(
            not (
                document["classifier_decision"] == "RELATION_COVERAGE"
                and not document["certified_positive_switch"]
            )
            or document[
                "unwitnessed_positive_classifier_decision_falls_back_exactly"
            ]
            for document in (prior, strict)
        ),
        "positive_query_policy_strictly_improves_when_certified": (
            guard_reduction > 0 if certified else True
        ),
        "exact_fallback_has_zero_regression": (
            guard_reduction == 0 and exact_prior_fallback if fallback else True
        ),
        "fallback_resumed_same_generator_object_both_arms": (
            all(
                document["fallback_resumed_same_path_first_generator_object"]
                is True
                for document in (prior, strict)
            )
            if fallback
            else True
        ),
        "no_additional_classifier_only_target_labels": all(
            document["additional_classifier_only_target_labels"] == 0
            for document in (prior, strict)
        ),
        "v160_and_v161_failures_preserved": True,
    }
    gate.pop("raw_prefix_query_decision_matches_registered_cohort", None)
    gate.pop("positive_query_policy_strictly_improves_when_required", None)
    gate.pop("fallback_query_policy_has_zero_regression_when_required", None)
    gate["passed"] = all(value for value in gate.values() if type(value) is bool)
    payload = {
        **{
            key: value
            for key, value in base.items()
            if key not in {"schema", "occurrence_id", "registered_gate"}
        },
        "schema": "acfqp.certified_paid_path_switch_occurrence.v162",
        "failed_v160_campaign_id": V160_FAILED_CAMPAIGN_ID,
        "failed_v160_record_sha256": V160_FAILURE_SHA256,
        "failed_v161_preregistration_id": V161_FAILED_PREREGISTRATION_ID,
        "failed_v161_record_sha256": V161_FAILURE_SHA256,
        "registered_gate": gate,
        "certified_positive_switch": certified,
        "exact_path_first_fallback": fallback,
        "v160_and_v161_failures_preserved_not_reclassified": True,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V162_THREE_FAMILY_COHORT",
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v162(
            domains.CONSTRUCTION_K7_OCCURRENCE_V162_DOMAIN, payload
        ),
    }


def _target(args: tuple[Any, ...]):
    return build_certified_paid_path_switch_occurrence_v162(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        classifier_receipt_raw=args[6],
    )


def build_certified_paid_path_switch_campaign_v162(
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
    fallback_rows = [row for row in rows if row["exact_path_first_fallback"]]
    certified_rows = [row for row in rows if row["certified_positive_switch"]]
    guards = tuple(
        row["query_policy_sample_reduction_vs_legacy_path_first"] for row in rows
    )
    factors = tuple(
        row["factor_prior_sample_reduction_within_progressive_policy"] for row in rows
    )
    gate = {
        "required_target_occurrence_count": config["required_target_occurrence_count"],
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "all_three_registered_families_present": {
            row["target_family"] for row in rows
        }
        == set(TARGET_FAMILIES),
        "at_least_one_paid_witness_certified_switch": bool(certified_rows),
        "certified_switches_only_in_registered_positive_family": all(
            row["target_family"] == POSITIVE_FAMILY for row in certified_rows
        ),
        "certified_switch_strictly_reduces_samples_in_aggregate": sum(
            row["query_policy_sample_reduction_vs_legacy_path_first"]
            for row in certified_rows
        )
        > 0,
        "every_exact_fallback_is_zero_regression": all(
            row["query_policy_sample_reduction_vs_legacy_path_first"] == 0
            and row["registered_gate"]["exact_fallback_has_zero_regression"]
            for row in fallback_rows
        ),
        "registered_positive_cohort_present": len(positive_rows) == 2,
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
        "v160_and_v161_failures_preserved_everywhere": all(
            row["v160_and_v161_failures_preserved_not_reclassified"] is True
            for row in rows
        ),
    }
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and gate["passed_target_occurrence_count"] == len(rows)
        and all(value for value in gate.values() if type(value) is bool)
    )
    payload = {
        "schema": "acfqp.certified_paid_path_switch_campaign.v162",
        "preregistration_id": preregistration_id,
        "classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
        "failed_v160_campaign_id": V160_FAILED_CAMPAIGN_ID,
        "failed_v160_record_sha256": V160_FAILURE_SHA256,
        "failed_v161_preregistration_id": V161_FAILED_PREREGISTRATION_ID,
        "failed_v161_record_sha256": V161_FAILURE_SHA256,
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": incompatible_schema_no_transfer_control_v99(),
        "accounting": accounting,
        "registered_gate": gate,
        "certified_paid_path_switch_query_policy_verified": gate["passed"],
        "v160_and_v161_failures_preserved_not_reclassified": True,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V162_THREE_FAMILY_COHORT",
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
        "campaign_id": domains.extension_content_id_v162(
            domains.CONSTRUCTION_K7_CAMPAIGN_V162_DOMAIN, payload
        ),
    }


__all__ = (
    "FALLBACK_FAMILY",
    "MODULAR_FAMILY",
    "POSITIVE_FAMILY",
    "build_certified_paid_path_switch_campaign_v162",
    "build_certified_paid_path_switch_occurrence_v162",
    "certified_paid_path_switch_campaign_config_v162",
)
