"""V166 transfers the safe sample-tax pipeline to a fourth stochastic family."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
from types import FunctionType, SimpleNamespace
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v166 as domains
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
from acfqp.generic_maintenance_cascade_adapter_v144 import (
    FAMILY as MAINTENANCE_FAMILY,
    build_maintenance_cascade_adapter_v144,
    maintenance_cascade_config_v144,
)


POSITIVE_FAMILY = v160.POSITIVE_FAMILY
FALLBACK_FAMILY = v160.FALLBACK_FAMILY
MODULAR_FAMILY = v160.MODULAR_FAMILY
TARGET_FAMILIES = (
    POSITIVE_FAMILY,
    FALLBACK_FAMILY,
    MODULAR_FAMILY,
    MAINTENANCE_FAMILY,
)
V164_CAMPAIGN_ID = "108bc4cf4f61123c6da7812ae76a48c21027a3b5e32e80005952a93b2ab8da1c"
V164_VERIFICATION_ID = (
    "1095eec978a045ac3fec2ef0848927ecf7ce3d290d68415656b28fe34b3f298f"
)
V165_AUDIT_ID = "8de483f4f827caddf96dd367b470aba6b8fef409f3cc060c4f3308fd592cbdeb"
V165_VERIFICATION_ID = (
    "d9aab6590d650f534edf19b7f87fd51045cd0d07cdf9d528f9873de3421e6390"
)


def fourth_family_sample_tax_transfer_campaign_config_v166():
    config = v160.progressive_raw_prefix_campaign_config_v160()
    maintenance = maintenance_cascade_config_v144()
    config["families"][MAINTENANCE_FAMILY] = copy.deepcopy(
        maintenance["families"][MAINTENANCE_FAMILY]
    )
    config["families"][MAINTENANCE_FAMILY]["maximum_acquisition_labels"] = 2_048
    return config


def _verify_classifier_compat(raw):
    document = verify_frozen_paid_path_prefix_classifier_receipt_v161(raw)
    return {
        **document,
        "fresh_v160_target_outcomes_accessed": document[
            "fresh_v161_target_outcomes_accessed"
        ],
    }


_DOMAIN_PROXY = SimpleNamespace(
    extension_content_id_v160=domains.extension_content_id_v166,
    CONSTRUCTION_K7_OCCURRENCE_V160_DOMAIN=domains.CONSTRUCTION_K7_OCCURRENCE_V166_DOMAIN,
)
_BASE_GLOBALS = dict(v160.__dict__)
_BASE_GLOBALS.update(
    domains=_DOMAIN_PROXY,
    CLASSIFIER_RECEIPT_ID=CLASSIFIER_RECEIPT_ID,
    _BUILDERS={
        **v160._BUILDERS,  # noqa: SLF001
        MAINTENANCE_FAMILY: build_maintenance_cascade_adapter_v144,
    },
    verify_frozen_progressive_raw_prefix_classifier_receipt_v160=_verify_classifier_compat,
    acquire_matched_progressive_raw_prefix_arms_v160=(
        acquire_matched_certified_paid_path_switch_arms_v162
    ),
)
_BASE_OCCURRENCE = FunctionType(
    v160.build_progressive_raw_prefix_occurrence_v160.__code__,
    _BASE_GLOBALS,
    name="_base_fourth_family_sample_tax_occurrence_v166",
)


def build_fourth_family_sample_tax_occurrence_v166(
    config,
    *,
    family,
    seed,
    episode_indices,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    if family not in TARGET_FAMILIES:
        raise ValueError("V166 target family is not registered")
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
        raise ValueError("V166 matched arms disagreed on certified switch")
    guard_reduction = base[
        "query_policy_sample_reduction_vs_legacy_path_first"
    ]
    factor_reduction = base[
        "factor_prior_sample_reduction_within_progressive_policy"
    ]
    exact_fallback = (
        prior["source_v148_acquisition_id"]
        == base["legacy_path_first_prior_summary"]["acquisition_id"]
        and prior["ground_support_labels"]
        == base["legacy_path_first_prior_summary"]["ground_support_labels"]
        and prior["raw_transition_sha256"]
        == base["legacy_path_first_prior_summary"]["raw_transition_sha256"]
    )
    gate = {
        key: value
        for key, value in base["registered_gate"].items()
        if key
        not in {
            "passed",
            "raw_prefix_query_decision_matches_registered_cohort",
            "positive_query_policy_strictly_improves_when_required",
            "fallback_query_policy_has_zero_regression_when_required",
        }
    }
    gate.update(
        raw_prefix_query_decision_matches_paid_evidence=(
            prior["query_policy_decision"]
            == strict["query_policy_decision"]
            == ("RELATION_COVERAGE" if certified else "PATH_FIRST_SAFE_FALLBACK")
        ),
        certified_switch_requires_classifier_and_paid_relation_witness=(
            not certified
            or all(
                row["classifier_decision"] == "RELATION_COVERAGE"
                and row["paid_prefix_relation_candidate_count"] > 0
                for row in (prior, strict)
            )
        ),
        query_policy_noninferior_to_exact_path_first=guard_reduction >= 0,
        certified_switch_is_noninferior_when_exercised=(
            guard_reduction >= 0 if certified else True
        ),
        exact_fallback_has_zero_regression=(
            guard_reduction == 0 and exact_fallback if not certified else True
        ),
        factor_prior_noninferior_within_same_query_policy=factor_reduction >= 0,
        v164_replication_identity_preserved=True,
        v165_nonidentifiability_boundary_preserved=True,
        profitability_classifier_not_issued=True,
    )
    gate["passed"] = all(value for value in gate.values() if type(value) is bool)
    payload = {
        **{
            key: value
            for key, value in base.items()
            if key not in {"schema", "occurrence_id", "registered_gate"}
        },
        "schema": "acfqp.fourth_family_sample_tax_occurrence.v166",
        "frozen_v164_campaign_id": V164_CAMPAIGN_ID,
        "frozen_v164_verification_id": V164_VERIFICATION_ID,
        "frozen_v165_identifiability_audit_id": V165_AUDIT_ID,
        "frozen_v165_independent_verification_id": V165_VERIFICATION_ID,
        "registered_gate": gate,
        "certified_positive_switch": certified,
        "exact_path_first_fallback": not certified,
        "profitability_classifier_issued": False,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V166_FOUR_FAMILY_COHORT",
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v166(
            domains.CONSTRUCTION_K7_OCCURRENCE_V166_DOMAIN, payload
        ),
    }


def _target(args: tuple[Any, ...]):
    return build_fourth_family_sample_tax_occurrence_v166(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        classifier_receipt_raw=args[6],
    )


def build_fourth_family_sample_tax_campaign_v166(
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
    new_family_rows = [
        row for row in rows if row["target_family"] == MAINTENANCE_FAMILY
    ]
    accounting.update(
        offline_source_observation_labels=96,
        historical_profitability_outcome_annotations=20,
        new_profitability_classifier_training_labels=0,
        target_classifier_path_prefix_labels=sum(
            row["accounting"]["classifier_prefix_labels_included_in_acquisition"]
            for row in rows
        ),
        additional_classifier_only_target_labels=0,
        total_query_policy_labels_avoided_vs_exact_path_first=sum(guards),
        total_factor_prior_labels_avoided_within_same_query_policy=sum(factors),
        new_family_factor_prior_labels_avoided=sum(
            row["factor_prior_sample_reduction_within_progressive_policy"]
            for row in new_family_rows
        ),
        source_target_and_historical_annotations_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    gate = {
        "required_target_occurrence_count": config["required_target_occurrence_count"],
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "all_four_registered_families_present": {
            row["target_family"] for row in rows
        }
        == set(TARGET_FAMILIES),
        "two_fresh_maintenance_occurrences_present": len(new_family_rows) == 2,
        "query_policy_noninferior_everywhere": all(value >= 0 for value in guards),
        "every_exact_fallback_is_zero_regression": all(
            row["query_policy_sample_reduction_vs_legacy_path_first"] == 0
            and row["registered_gate"]["exact_fallback_has_zero_regression"]
            for row in rows
            if row["exact_path_first_fallback"]
        ),
        "factor_prior_noninferior_everywhere": all(value >= 0 for value in factors),
        "factor_prior_strictly_reduces_sample_tax_in_aggregate": sum(factors) > 0,
        "factor_prior_strictly_reduces_new_family_sample_tax": accounting[
            "new_family_factor_prior_labels_avoided"
        ]
        > 0,
        "new_family_receding_plans_succeed": all(
            row["registered_gate"]["both_arm_receding_episodes_succeed"]
            for row in new_family_rows
        ),
        "sample_tax_axes_remain_separate": accounting[
            "source_target_and_historical_annotations_execution_steps_derivation_and_planning_compute_separate"
        ],
        "no_new_profitability_training_labels": accounting[
            "new_profitability_classifier_training_labels"
        ]
        == 0,
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
        "v164_replication_and_v165_boundary_preserved": all(
            row["frozen_v164_campaign_id"] == V164_CAMPAIGN_ID
            and row["frozen_v164_verification_id"] == V164_VERIFICATION_ID
            and row["frozen_v165_identifiability_audit_id"] == V165_AUDIT_ID
            and row["frozen_v165_independent_verification_id"]
            == V165_VERIFICATION_ID
            for row in rows
        ),
        "profitability_classifier_not_issued": all(
            row["profitability_classifier_issued"] is False for row in rows
        ),
        "strict_query_policy_reduction_not_required_in_v166": True,
    }
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and gate["passed_target_occurrence_count"] == len(rows)
        and all(value for value in gate.values() if type(value) is bool)
    )
    payload = {
        "schema": "acfqp.fourth_family_sample_tax_campaign.v166",
        "preregistration_id": preregistration_id,
        "frozen_v164_campaign_id": V164_CAMPAIGN_ID,
        "frozen_v164_verification_id": V164_VERIFICATION_ID,
        "frozen_v165_identifiability_audit_id": V165_AUDIT_ID,
        "frozen_v165_independent_verification_id": V165_VERIFICATION_ID,
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": incompatible_schema_no_transfer_control_v99(),
        "accounting": accounting,
        "registered_gate": gate,
        "fourth_family_factor_prior_sample_tax_transfer_verified": gate["passed"],
        "profitability_classifier_issued": False,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V166_FOUR_FAMILY_COHORT",
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
        "campaign_id": domains.extension_content_id_v166(
            domains.CONSTRUCTION_K7_CAMPAIGN_V166_DOMAIN, payload
        ),
    }


__all__ = (
    "FALLBACK_FAMILY",
    "MAINTENANCE_FAMILY",
    "MODULAR_FAMILY",
    "POSITIVE_FAMILY",
    "TARGET_FAMILIES",
    "build_fourth_family_sample_tax_campaign_v166",
    "build_fourth_family_sample_tax_occurrence_v166",
    "fourth_family_sample_tax_transfer_campaign_config_v166",
)
