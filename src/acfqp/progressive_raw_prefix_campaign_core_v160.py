"""Fresh three-family V160 transfer of a raw-prefix query meta-prior."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v160 as domains
from acfqp.anonymous_relational_factor_bank_acquisition_v148 import (
    acquire_matched_anonymous_relational_factor_bank_arms_v148,
)
from acfqp.applicable_plan_mode_sequence_v157 import (
    annotate_applicable_plan_mode_sequence_v157,
)
from acfqp.certified_memoized_planner_sequence_v154 import (
    run_certified_memoized_planner_sequence_v154,
)
from acfqp.construction_k7_progressive_raw_prefix_classifier_receipt_freeze_v160 import (
    CLASSIFIER_RECEIPT_ID,
    verify_frozen_progressive_raw_prefix_classifier_receipt_v160,
)
from acfqp.generic_modular_routing_adapter_v128 import (
    FAMILY as MODULAR_FAMILY,
    build_modular_routing_adapter_v128,
    modular_routing_config_v128,
)
from acfqp.generic_novel_signature_adapters_v158 import (
    FALLBACK_FAMILY,
    POSITIVE_FAMILY,
    build_novel_fallback_signature_adapter_v158,
    build_novel_positive_signature_adapter_v158,
)
from acfqp.novel_signature_campaign_core_v158 import (
    novel_signature_campaign_config_v158,
)
from acfqp.progressive_raw_prefix_acquisition_operator_v160 import (
    acquire_matched_progressive_raw_prefix_arms_v160,
)
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)


TARGET_FAMILIES = (POSITIVE_FAMILY, FALLBACK_FAMILY, MODULAR_FAMILY)
_BUILDERS = {
    POSITIVE_FAMILY: build_novel_positive_signature_adapter_v158,
    FALLBACK_FAMILY: build_novel_fallback_signature_adapter_v158,
    MODULAR_FAMILY: build_modular_routing_adapter_v128,
}


def progressive_raw_prefix_campaign_config_v160():
    config = novel_signature_campaign_config_v158()
    modular = modular_routing_config_v128()
    config["families"][MODULAR_FAMILY] = copy.deepcopy(
        modular["families"][MODULAR_FAMILY]
    )
    config["families"][POSITIVE_FAMILY]["maximum_acquisition_labels"] = 1_536
    config["families"][FALLBACK_FAMILY]["maximum_acquisition_labels"] = 1_536
    config["families"][MODULAR_FAMILY]["maximum_acquisition_labels"] = 2_048
    return config


def build_progressive_raw_prefix_occurrence_v160(
    config,
    *,
    family,
    seed,
    episode_indices,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    classifier = verify_frozen_progressive_raw_prefix_classifier_receipt_v160(
        classifier_receipt_raw
    )
    if family not in _BUILDERS:
        raise ValueError("V160 target family is not registered")
    adapter = _BUILDERS[family](seed, config)
    arms = acquire_matched_progressive_raw_prefix_arms_v160(
        adapter, bank_raw, verification_raw, classifier_receipt_raw, config
    )
    legacy = acquire_matched_anonymous_relational_factor_bank_arms_v148(
        adapter, bank_raw, verification_raw, config
    )
    sequences = {
        name: annotate_applicable_plan_mode_sequence_v157(
            run_certified_memoized_planner_sequence_v154(
                adapter,
                arm["candidate"],
                arm["rows"],
                arm["document"]["ground_support_labels"],
                episode_indices=episode_indices,
                maximum_abstract_depth=config["maximum_abstract_depth"],
                maximum_execution_steps=config["maximum_execution_steps"],
                maximum_incremental_certificate_ground_support_labels=100_000,
            )
        )
        for name, arm in arms.items()
    }
    prior = arms["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]
    strict = arms["STRICT_NO_PRIOR"]
    prior_doc = prior["document"]
    strict_doc = strict["document"]
    prior_sequence = sequences["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]
    strict_sequence = sequences["STRICT_NO_PRIOR"]
    legacy_prior = legacy["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]["document"]
    guard_reduction = (
        legacy_prior["ground_support_labels"] - prior_doc["ground_support_labels"]
    )
    factor_reduction = (
        strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    )
    expected_positive = family == POSITIVE_FAMILY
    expected_decision = (
        "RELATION_COVERAGE" if expected_positive else "PATH_FIRST_SAFE_FALLBACK"
    )
    plan_modes = {
        prior_sequence["applicable_plan_receipt_mode"],
        strict_sequence["applicable_plan_receipt_mode"],
    }
    accounting = {
        "progressive_prior_acquisition_labels": prior_doc["ground_support_labels"],
        "progressive_strict_acquisition_labels": strict_doc[
            "ground_support_labels"
        ],
        "legacy_path_first_prior_acquisition_labels": legacy_prior[
            "ground_support_labels"
        ],
        "classifier_prefix_labels_included_in_acquisition": prior_doc[
            "classifier_prefix_observation_labels"
        ],
        "additional_classifier_only_target_labels": 0,
        "labels_avoided_by_progressive_query_policy_vs_legacy_path_first": guard_reduction,
        "labels_avoided_by_factor_prior_within_progressive_policy": factor_reduction,
        "progressive_prior_certificate_local_labels": prior_sequence[
            "certificate_ground_support_labels_paid_once"
        ],
        "progressive_strict_certificate_local_labels": strict_sequence[
            "certificate_ground_support_labels_paid_once"
        ],
        "progressive_prior_execution_steps": prior_sequence[
            "execution_step_count"
        ],
        "progressive_strict_execution_steps": strict_sequence[
            "execution_step_count"
        ],
        "progressive_prior_derivation_compute_events": prior_doc[
            "derivation_compute_events"
        ],
        "progressive_strict_derivation_compute_events": strict_doc[
            "derivation_compute_events"
        ],
        "classifier_derivation_compute_events": classifier[
            "classifier_derivation_compute_events"
        ],
        "progressive_prior_planning_compute_events": prior_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "progressive_strict_planning_compute_events": strict_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    all_sequences = tuple(sequences.values())
    gate = {
        "fresh_target_identity": True,
        "classifier_receipt_frozen_before_target_outcomes": classifier[
            "fresh_v160_target_outcomes_accessed"
        ]
        is False,
        "raw_prefix_query_decision_matches_registered_cohort": prior_doc[
            "query_policy_decision"
        ]
        == strict_doc["query_policy_decision"]
        == expected_decision,
        "no_named_initial_or_catalogue_support_primitive": all(
            document["no_named_initial_or_catalogue_support_primitive"] is True
            for document in (prior_doc, strict_doc)
        ),
        "decision_before_full_initial_action_frontier": all(
            document["full_initial_action_frontier_required_for_decision"] is False
            for document in (prior_doc, strict_doc)
        ),
        "classifier_uses_only_paid_target_raw_prefix": all(
            document["classifier_accessed_only_its_paid_target_raw_prefix"] is True
            and document[
                "classifier_prefix_labels_are_included_in_ground_support_labels"
            ]
            is True
            for document in (prior_doc, strict_doc)
        ),
        "query_policy_noninferior_to_legacy_path_first": guard_reduction >= 0,
        "positive_query_policy_strictly_improves_when_required": (
            guard_reduction > 0 if expected_positive else True
        ),
        "fallback_query_policy_has_zero_regression_when_required": (
            guard_reduction == 0 if not expected_positive else True
        ),
        "factor_prior_noninferior_within_same_progressive_policy": factor_reduction
        >= 0,
        "matched_acquisition_completed_within_cap": all(
            0
            < document["ground_support_labels"]
            <= config["families"][family]["maximum_acquisition_labels"]
            for document in (prior_doc, strict_doc)
        ),
        "both_arms_use_same_synthesizer_and_stop_rule": all(
            prior_doc[key] is True and strict_doc[key] is True
            for key in (
                "same_generic_atomic_hypothesis_pool",
                "same_candidate_carrier_and_schema",
                "same_candidate_replay_function",
                "same_stopping_rule_function",
            )
        ),
        "both_arm_receding_episodes_succeed": all(
            episode["success"]
            for sequence in all_sequences
            for episode in sequence["episodes"]
        ),
        "planner_consumes_compiled_model_without_raw_rows": all(
            sequence[
                "planner_consumed_compiled_successor_without_raw_transition_argument"
            ]
            for sequence in all_sequences
        ),
        "certificate_failure_only_local_ground_distinctions": all(
            sequence["every_new_ground_query_followed_a_failed_certificate"]
            for sequence in all_sequences
        ),
        "query_local_overlay_not_promoted_to_global_dynamics": all(
            sequence["source_partial_program_mutated_after_certificate_failure"]
            is False
            and sequence["overlay_promoted_to_global_dynamics"] is False
            and sequence["query_local_overlay_used_as_safety_authority"] is False
            for sequence in all_sequences
        ),
        "applicable_plan_receipt_mode_agrees_between_arms": len(plan_modes) == 1,
        "all_executed_actions_have_v109_receipts": all(
            sequence["all_executed_actions_have_v109_receipts"]
            for sequence in all_sequences
        ),
        "exact_signature_registry_not_consulted": all(
            document["exact_signature_registry_consulted"] is False
            for document in (prior_doc, strict_doc)
        ),
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.progressive_raw_prefix_occurrence.v160",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
        "v146_factor_bank_id": prior_doc["v146_factor_bank_id"],
        "v146_independent_verification_id": prior_doc[
            "v146_independent_verification_id"
        ],
        "progressive_prior_acquisition": prior_doc,
        "progressive_strict_acquisition": strict_doc,
        "progressive_prior_sequence": prior_sequence,
        "progressive_strict_sequence": strict_sequence,
        "legacy_path_first_prior_summary": {
            key: legacy_prior[key]
            for key in (
                "acquisition_id",
                "ground_support_labels",
                "raw_transition_sha256",
                "first_accepting_observation_label",
            )
        },
        "applicable_plan_receipt_mode": next(iter(plan_modes)),
        "accounting": accounting,
        "registered_gate": gate,
        "query_policy_sample_reduction_vs_legacy_path_first": guard_reduction,
        "factor_prior_sample_reduction_within_progressive_policy": factor_reduction,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V160_THREE_FAMILY_COHORT",
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
        "occurrence_id": domains.extension_content_id_v160(
            domains.CONSTRUCTION_K7_OCCURRENCE_V160_DOMAIN, payload
        ),
    }


def _target(args: tuple[Any, ...]):
    return build_progressive_raw_prefix_occurrence_v160(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        classifier_receipt_raw=args[6],
    )


def build_progressive_raw_prefix_campaign_v160(
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
        offline_source_observation_labels=40,
        target_classifier_prefix_labels=sum(
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
        "positive_raw_prefix_policy_strictly_reduces_samples_in_aggregate": sum(
            row["query_policy_sample_reduction_vs_legacy_path_first"]
            for row in positive_rows
        )
        > 0,
        "fallback_and_modular_raw_prefix_policy_zero_regression_everywhere": all(
            row["query_policy_sample_reduction_vs_legacy_path_first"] == 0
            for row in fallback_rows + modular_rows
        ),
        "query_policy_noninferior_everywhere": all(value >= 0 for value in guards),
        "factor_prior_noninferior_everywhere": all(value >= 0 for value in factors),
        "factor_prior_positive_in_aggregate": sum(factors) > 0,
        "no_additional_classifier_only_target_labels": accounting[
            "additional_classifier_only_target_labels"
        ]
        == 0,
        "decision_before_full_initial_action_frontier_everywhere": all(
            row["registered_gate"]["decision_before_full_initial_action_frontier"]
            for row in rows
        ),
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
    }
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and gate["passed_target_occurrence_count"] == len(rows)
        and all(value for value in gate.values() if type(value) is bool)
    )
    payload = {
        "schema": "acfqp.progressive_raw_prefix_campaign.v160",
        "preregistration_id": preregistration_id,
        "classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": incompatible_schema_no_transfer_control_v99(),
        "accounting": accounting,
        "registered_gate": gate,
        "progressive_raw_prefix_query_policy_verified": gate["passed"],
        "named_initial_catalogue_support_scaffold_removed": gate["passed"],
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V160_THREE_FAMILY_COHORT",
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
        "campaign_id": domains.extension_content_id_v160(
            domains.CONSTRUCTION_K7_CAMPAIGN_V160_DOMAIN, payload
        ),
    }


__all__ = (
    "FALLBACK_FAMILY",
    "MODULAR_FAMILY",
    "POSITIVE_FAMILY",
    "build_progressive_raw_prefix_campaign_v160",
    "build_progressive_raw_prefix_occurrence_v160",
    "progressive_raw_prefix_campaign_config_v160",
)
