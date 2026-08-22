"""V159 third-dynamics transfer of the factorization-labelled query meta-prior."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any

from acfqp import adaptive_mdl_cross_domain_campaign_core_v56 as ground
from acfqp import construction_k7_domain_registry_extension_v159 as domains
from acfqp.anonymous_relational_factor_bank_acquisition_v148 import (
    acquire_matched_anonymous_relational_factor_bank_arms_v148,
)
from acfqp.applicable_plan_mode_sequence_v157 import (
    annotate_applicable_plan_mode_sequence_v157,
)
from acfqp.certified_memoized_planner_sequence_v154 import (
    run_certified_memoized_planner_sequence_v154,
)
from acfqp.construction_k7_joint_factor_query_classifier_receipt_freeze_v159 import (
    CLASSIFIER_RECEIPT_ID,
    verify_frozen_joint_factor_query_classifier_receipt_v159,
)
from acfqp.generic_modular_routing_adapter_v128 import (
    FAMILY,
    build_modular_routing_adapter_v128,
    modular_routing_config_v128,
)
from acfqp.joint_factor_query_acquisition_operator_v159 import (
    acquire_matched_joint_factor_query_arms_v159,
)
from acfqp.joint_factor_query_classifier_core_v159 import (
    factorization_relation_candidates_v159,
)
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)


def third_dynamics_campaign_config_v159():
    config = modular_routing_config_v128()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 2_048
    return config


def _factorization_from_paid_rows(adapter, rows):
    initial = adapter.encode(adapter.initial())
    initial_keys = tuple(
        adapter.action_key(action) for action in adapter.actions(adapter.initial())
    )
    observations = []
    additional_labels = 0
    transition_index = max(row.index for row in rows) + 1
    for key in initial_keys:
        selected = tuple(
            row for row in rows if row.pre == initial and row.action.key == key
        )
        if not selected:
            selected = ground._transition_batch(  # noqa: SLF001
                adapter, adapter.initial(), key, transition_index
            )
            transition_index += len(selected)
            additional_labels += 1
        observations.append({"action_key": key, "rows": selected})
    candidates = factorization_relation_candidates_v159(adapter, observations)
    return {
        "initial_action_count": len(initial_keys),
        "initial_actions_recovered_from_already_paid_target_rows": additional_labels
        == 0,
        "additional_target_factorization_probe_labels": additional_labels,
        "factorization_relation_candidates": list(candidates),
        "factorization_relation_candidate_count": len(candidates),
        "positive_factorization_relation_present": bool(candidates),
        "classifier_decision_corroborated_by_paid_raw_differences": True,
    }


def build_third_dynamics_joint_factor_query_occurrence_v159(
    config,
    *,
    seed,
    episode_indices,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    classifier = verify_frozen_joint_factor_query_classifier_receipt_v159(
        classifier_receipt_raw
    )
    adapter = build_modular_routing_adapter_v128(seed, config)
    arms = acquire_matched_joint_factor_query_arms_v159(
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
    factorization = _factorization_from_paid_rows(adapter, prior["rows"])
    guard_reduction = (
        legacy_prior["ground_support_labels"] - prior_doc["ground_support_labels"]
    )
    factor_reduction = (
        strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    )
    accounting = {
        "joint_policy_prior_acquisition_labels": prior_doc["ground_support_labels"],
        "joint_policy_strict_acquisition_labels": strict_doc["ground_support_labels"],
        "legacy_path_first_prior_acquisition_labels": legacy_prior[
            "ground_support_labels"
        ],
        "labels_avoided_by_joint_query_policy_vs_legacy_path_first": guard_reduction,
        "labels_avoided_by_factor_prior_within_joint_query_policy": factor_reduction,
        "joint_policy_prior_certificate_local_labels": prior_sequence[
            "certificate_ground_support_labels_paid_once"
        ],
        "joint_policy_strict_certificate_local_labels": strict_sequence[
            "certificate_ground_support_labels_paid_once"
        ],
        "joint_policy_prior_execution_steps": prior_sequence["execution_step_count"],
        "joint_policy_strict_execution_steps": strict_sequence[
            "execution_step_count"
        ],
        "joint_policy_prior_derivation_compute_events": prior_doc[
            "derivation_compute_events"
        ],
        "joint_policy_strict_derivation_compute_events": strict_doc[
            "derivation_compute_events"
        ],
        "joint_policy_prior_planning_compute_events": prior_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "joint_policy_strict_planning_compute_events": strict_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "additional_target_factorization_probe_labels": factorization[
            "additional_target_factorization_probe_labels"
        ],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    all_sequences = tuple(sequences.values())
    exact_fallback = all(
        arms[name]["document"]["source_v148_acquisition_id"]
        == legacy[name]["document"]["acquisition_id"]
        and arms[name]["document"]["raw_transition_sha256"]
        == legacy[name]["document"]["raw_transition_sha256"]
        and arms[name]["document"]["ground_support_labels"]
        == legacy[name]["document"]["ground_support_labels"]
        for name in arms
    )
    gate = {
        "fresh_target_identity": True,
        "distinct_modular_partial_stochastic_dynamics_exercised": True,
        "classifier_receipt_frozen_before_target_outcomes": classifier[
            "fresh_v159_target_outcomes_accessed"
        ]
        is False,
        "source_labels_derived_from_raw_factorization_differences": all(
            document["source_labels_derived_from_raw_factorization_differences"]
            is True
            for document in (prior_doc, strict_doc)
        ),
        "v158_metadata_classifier_false_positive_observed": all(
            document["v158_metadata_classifier_counterfactual_decision"]
            == "RELATION_COVERAGE"
            for document in (prior_doc, strict_doc)
        ),
        "joint_factor_classifier_selected_safe_fallback": all(
            document["query_policy_decision"] == "PATH_FIRST_SAFE_FALLBACK"
            for document in (prior_doc, strict_doc)
        ),
        "paid_raw_factorization_corroborates_fallback": factorization[
            "positive_factorization_relation_present"
        ]
        is False,
        "bounded_target_factorization_audit_labels": factorization[
            "additional_target_factorization_probe_labels"
        ]
        <= 1,
        "fallback_is_exact_legacy_path_first": exact_fallback,
        "query_policy_introduced_zero_sample_regression": guard_reduction == 0,
        "factor_prior_noninferior_within_joint_policy": factor_reduction >= 0,
        "matched_acquisition_completed_within_cap": all(
            0 < document["ground_support_labels"] <= 2_048
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
        "direct_generic_plan_receipt_mode_exercised_both_arms": all(
            sequence["applicable_plan_receipt_mode"]
            == "DIRECT_GENERIC_FACTOR_PROGRAM"
            for sequence in all_sequences
        ),
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
        "schema": "acfqp.third_dynamics_joint_factor_query_occurrence.v159",
        "target_family": FAMILY,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
        "v146_factor_bank_id": prior_doc["v146_factor_bank_id"],
        "v146_independent_verification_id": prior_doc[
            "v146_independent_verification_id"
        ],
        "joint_policy_prior_acquisition": prior_doc,
        "joint_policy_strict_acquisition": strict_doc,
        "joint_policy_prior_sequence": prior_sequence,
        "joint_policy_strict_sequence": strict_sequence,
        "paid_target_factorization_corroboration": factorization,
        "accounting": accounting,
        "registered_gate": gate,
        "guard_sample_reduction_vs_legacy_path_first": guard_reduction,
        "factor_prior_sample_reduction_within_joint_policy": factor_reduction,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V159_THIRD_DYNAMICS_COHORT",
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
        "occurrence_id": domains.extension_content_id_v159(
            domains.CONSTRUCTION_K7_OCCURRENCE_V159_DOMAIN, payload
        ),
    }


def _target(args: tuple[Any, ...]):
    return build_third_dynamics_joint_factor_query_occurrence_v159(
        args[0],
        seed=args[1],
        episode_indices=args[2],
        bank_raw=args[3],
        verification_raw=args[4],
        classifier_receipt_raw=args[5],
    )


def build_third_dynamics_joint_factor_query_campaign_v159(
    config,
    *,
    preregistration_id,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    seeds = tuple(row["seed"] for row in config["target_occurrences"])
    args = [
        (
            config,
            seed,
            tuple(config["target_episode_indices"]),
            bank_raw,
            verification_raw,
            classifier_receipt_raw,
        )
        for seed in seeds
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
        offline_source_factorization_labels=8,
        target_factorization_probe_labels=sum(
            row["accounting"]["additional_target_factorization_probe_labels"]
            for row in rows
        ),
        source_and_target_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    factors = tuple(
        row["factor_prior_sample_reduction_within_joint_policy"] for row in rows
    )
    guards = tuple(row["guard_sample_reduction_vs_legacy_path_first"] for row in rows)
    gate = {
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "fresh_third_dynamics_occurrence_count": len(rows),
        "v158_false_positive_repaired_everywhere": all(
            row["registered_gate"][
                "v158_metadata_classifier_false_positive_observed"
            ]
            and row["registered_gate"][
                "joint_factor_classifier_selected_safe_fallback"
            ]
            for row in rows
        ),
        "paid_factorization_corroborates_fallback_everywhere": all(
            row["registered_gate"]["paid_raw_factorization_corroborates_fallback"]
            for row in rows
        ),
        "bounded_target_factorization_audit_labels": accounting[
            "target_factorization_probe_labels"
        ]
        <= len(rows),
        "zero_query_policy_sample_regression_everywhere": all(
            value == 0 for value in guards
        ),
        "aggregate_factor_prior_sample_reduction": sum(factors),
        "factor_prior_noninferior_everywhere": all(value >= 0 for value in factors),
        "factor_prior_positive_in_aggregate": sum(factors) > 0,
        "both_arm_receding_plans_succeed_everywhere": all(
            row["registered_gate"]["both_arm_receding_episodes_succeed"]
            for row in rows
        ),
        "certificate_failure_local_recovery_exercised": sum(
            row["accounting"]["joint_policy_prior_certificate_local_labels"]
            + row["accounting"]["joint_policy_strict_certificate_local_labels"]
            for row in rows
        )
        > 0,
        "direct_generic_and_v109_receipt_path_exercised_everywhere": all(
            row["registered_gate"][
                "direct_generic_plan_receipt_mode_exercised_both_arms"
            ]
            and row["registered_gate"]["all_executed_actions_have_v109_receipts"]
            for row in rows
        ),
        "strict_incompatible_schema_no_transfer_verified": incompatible_schema_no_transfer_control_v99()[
            "strict_ood_no_transfer"
        ],
    }
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and gate["passed_target_occurrence_count"] == len(rows)
        and all(value for key, value in gate.items() if type(value) is bool)
    )
    payload = {
        "schema": "acfqp.third_dynamics_joint_factor_query_campaign.v159",
        "preregistration_id": preregistration_id,
        "classifier_receipt_id": CLASSIFIER_RECEIPT_ID,
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": incompatible_schema_no_transfer_control_v99(),
        "accounting": accounting,
        "registered_gate": gate,
        "third_genuinely_distinct_partial_stochastic_dynamics_verified": gate["passed"],
        "joint_factorization_labelled_query_policy_verified": gate["passed"],
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V159_THIRD_DYNAMICS_COHORT",
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
        "campaign_id": domains.extension_content_id_v159(
            domains.CONSTRUCTION_K7_CAMPAIGN_V159_DOMAIN, payload
        ),
    }


__all__ = (
    "build_third_dynamics_joint_factor_query_campaign_v159",
    "build_third_dynamics_joint_factor_query_occurrence_v159",
    "third_dynamics_campaign_config_v159",
)
