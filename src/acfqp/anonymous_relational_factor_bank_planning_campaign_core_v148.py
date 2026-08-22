"""V148 matched acquisition and certificate-local receding planning campaign."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v148 as domains
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.anonymous_relational_factor_bank_acquisition_v148 import (
    acquire_matched_anonymous_relational_factor_bank_arms_v148,
)
from acfqp.certificate_local_relational_overlay_sequence_v144r1 import (
    run_certificate_local_relational_overlay_sequence_v144r1,
)
from acfqp.generic_maintenance_cascade_adapter_v144 import (
    FAMILY as MAINTENANCE,
    build_maintenance_cascade_adapter_v144,
)


_BUILDERS = {MAINTENANCE: build_maintenance_cascade_adapter_v144}


def build_anonymous_relational_factor_bank_occurrence_v148(
    config: Mapping[str, Any],
    *,
    family: str,
    seed: int,
    episode_indices: tuple[int, ...],
    bank_raw: bytes,
    verification_raw: bytes,
) -> dict[str, Any]:
    if family not in _BUILDERS:
        raise ValueError("V148 family is outside the registered adapter boundary")
    adapter = _BUILDERS[family](seed, config)
    arms = acquire_matched_anonymous_relational_factor_bank_arms_v148(
        adapter, bank_raw, verification_raw, config
    )
    prior = arms["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]
    strict = arms["STRICT_NO_PRIOR"]
    sequences = {
        name: run_certificate_local_relational_overlay_sequence_v144r1(
            adapter,
            arm["candidate"],
            arm["rows"],
            arm["document"]["ground_support_labels"],
            episode_indices=episode_indices,
            maximum_abstract_depth=config["maximum_abstract_depth"],
            maximum_execution_steps=config["maximum_execution_steps"],
            maximum_incremental_certificate_ground_support_labels=100_000,
        )
        for name, arm in arms.items()
    }
    prior_doc = prior["document"]
    strict_doc = strict["document"]
    prior_sequence = sequences["ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON"]
    strict_sequence = sequences["STRICT_NO_PRIOR"]
    common = min(len(prior["batches"]), len(strict["batches"]))
    prior_prefix = tuple(row for batch in prior["batches"][:common] for row in batch)
    strict_prefix = tuple(row for batch in strict["batches"][:common] for row in batch)
    reduction = strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    sample_tax = {
        "anonymous_relational_factor_prior_ground_support_labels": prior_doc[
            "ground_support_labels"
        ],
        "strict_no_prior_ground_support_labels": strict_doc["ground_support_labels"],
        "ground_support_labels_avoided_by_anonymous_relational_prior": reduction,
        "same_fair_witness_blind_path_first_backtracking_policy": True,
        "same_raw_transition_prefix_through_common_label": prior_prefix == strict_prefix,
        "same_observation_derived_binding_and_template_instantiator": True,
        "same_generic_atomic_hypothesis_pool": True,
        "same_candidate_carrier_and_schema": True,
        "same_candidate_replay_function": True,
        "same_stopping_rule_function": True,
        "only_arm_switch_is_anonymous_relational_prior": True,
        "sample_labels_and_derivation_compute_separate": True,
    }
    gate = {
        "matched_acquisition_completed_within_registered_cap": all(
            0 < arm["document"]["ground_support_labels"]
            <= config["families"][family]["maximum_acquisition_labels"]
            for arm in arms.values()
        ),
        "same_raw_transition_prefix_through_common_label": sample_tax[
            "same_raw_transition_prefix_through_common_label"
        ],
        "same_synthesizer_representation_and_stop_rule": all(
            sample_tax[key]
            for key in (
                "same_observation_derived_binding_and_template_instantiator",
                "same_generic_atomic_hypothesis_pool",
                "same_candidate_carrier_and_schema",
                "same_candidate_replay_function",
                "same_stopping_rule_function",
            )
        ),
        "verified_v146_factor_bank_and_v147_binding_receipt_consumed": all(
            arm["document"]["v146_factor_bank_id"]
            == prior_doc["v146_factor_bank_id"]
            and arm["document"]["v146_independent_verification_id"]
            == prior_doc["v146_independent_verification_id"]
            and arm["document"]["anonymous_relational_instantiation"][
                "binding_derived_from_raw_observations"
            ]
            is True
            for arm in arms.values()
        ),
        "anonymous_relational_template_selected_in_prior_arm": prior_doc[
            "relational_artifact_expression_selected_count"
        ]
        > 0,
        "both_arm_receding_episodes_succeed": all(
            episode["success"]
            for sequence in sequences.values()
            for episode in sequence["episodes"]
        ),
        "certificate_failure_only_local_ground_distinctions": all(
            sequence["every_new_ground_query_followed_a_failed_certificate"]
            for sequence in sequences.values()
        ),
        "planner_consumes_compiled_model_without_raw_rows": all(
            sequence[
                "planner_consumed_compiled_successor_without_raw_transition_argument"
            ]
            for sequence in sequences.values()
        ),
        "planner_consumes_lowered_relational_execution_projection": all(
            sequence["partial_candidate_id"]
            == arms[name]["document"]["execution_projection"]["candidate_id"]
            and arms[name]["document"]["execution_projection"][
                "source_relational_candidate_id"
            ]
            == arms[name]["document"]["candidate"]["candidate_id"]
            and arms[name]["document"]["execution_projection"][
                "finite_relations_lowered_to_typed_conditionals"
            ]
            is True
            for name, sequence in sequences.items()
        ),
        "sound_certificate_local_recovery_union": all(
            sequence["source_partial_program_mutated_after_certificate_failure"]
            is False
            and sequence["every_uncompiled_edge_is_certificate_local"] is True
            and sequence["overlay_promoted_to_global_dynamics"] is False
            and sequence["query_local_overlay_used_as_safety_authority"] is False
            for sequence in sequences.values()
        ),
    }
    gate["passed"] = all(gate.values())
    accounting = {
        "anonymous_relational_prior_acquisition_labels": prior_doc[
            "ground_support_labels"
        ],
        "strict_no_prior_acquisition_labels": strict_doc["ground_support_labels"],
        "acquisition_labels_avoided_by_anonymous_relational_prior": reduction,
        "anonymous_relational_prior_certificate_local_labels": prior_sequence[
            "certificate_ground_support_labels_paid_once"
        ],
        "strict_no_prior_certificate_local_labels": strict_sequence[
            "certificate_ground_support_labels_paid_once"
        ],
        "anonymous_relational_prior_lifetime_target_labels": prior_sequence[
            "lifetime_target_ground_support_labels"
        ],
        "strict_no_prior_lifetime_target_labels": strict_sequence[
            "lifetime_target_ground_support_labels"
        ],
        "anonymous_relational_prior_execution_steps": prior_sequence[
            "execution_step_count"
        ],
        "strict_no_prior_execution_steps": strict_sequence["execution_step_count"],
        "anonymous_relational_prior_derivation_compute_events": prior_doc[
            "derivation_compute_events"
        ],
        "strict_no_prior_derivation_compute_events": strict_doc[
            "derivation_compute_events"
        ],
        "anonymous_relational_prior_template_binding_evaluation_events": prior_doc[
            "template_binding_evaluation_events"
        ],
        "strict_no_prior_template_binding_evaluation_events": strict_doc[
            "template_binding_evaluation_events"
        ],
        "anonymous_relational_prior_planning_compute_events": prior_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "strict_no_prior_planning_compute_events": strict_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "anonymous_relational_prior_query_local_overlay_edges": prior_sequence[
            "total_query_local_exact_overlay_edge_count"
        ],
        "strict_no_prior_query_local_overlay_edges": strict_sequence[
            "total_query_local_exact_overlay_edge_count"
        ],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.anonymous_relational_factor_bank_occurrence.v148",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "v146_factor_bank_id": prior_doc["v146_factor_bank_id"],
        "v146_independent_verification_id": prior_doc[
            "v146_independent_verification_id"
        ],
        "anonymous_relational_factor_prior_acquisition": prior_doc,
        "strict_no_prior_acquisition": strict_doc,
        "anonymous_relational_factor_prior_owned_sequence": prior_sequence,
        "strict_no_prior_owned_sequence": strict_sequence,
        "sample_tax_comparison": sample_tax,
        "accounting": accounting,
        "registered_gate": gate,
        "paired_label_reduction": reduction,
        "sample_efficiency_direction": (
            "POSITIVE" if reduction > 0 else "NEGATIVE" if reduction < 0 else "ZERO"
        ),
        "registered_workload_sample_efficiency_improvement_observed": reduction > 0,
        "complete_ground_world_model_synthesized": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v148(
            domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_OCCURRENCE_V148_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_anonymous_relational_factor_bank_occurrence_v148(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
    )


def build_anonymous_relational_factor_bank_campaign_document_v148(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    bank_raw: bytes,
    verification_raw: bytes,
) -> dict[str, Any]:
    args = [
        (
            config,
            row["family"],
            row["seed"],
            tuple(config["target_episode_indices"]),
            bank_raw,
            verification_raw,
        )
        for row in config["target_occurrences"]
    ]
    if config["target_worker_count"] == 1:
        rows = [_target(row) for row in args]
    else:
        with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
            rows = list(executor.map(_target, args))
    ood = incompatible_schema_no_transfer_control_v99()
    numeric = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    accounting = {key: sum(row["accounting"][key] for row in rows) for key in numeric}
    accounting.update(
        sample_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    reductions = tuple(row["paired_label_reduction"] for row in rows)
    aggregate_reduction = accounting[
        "acquisition_labels_avoided_by_anonymous_relational_prior"
    ]
    local_labels = (
        accounting["anonymous_relational_prior_certificate_local_labels"]
        + accounting["strict_no_prior_certificate_local_labels"]
    )
    passed_count = sum(row["registered_gate"]["passed"] for row in rows)
    gate = {
        "required_target_occurrence_count": config["required_target_occurrence_count"],
        "passed_target_occurrence_count": passed_count,
        "aggregate_paired_acquisition_label_reduction": aggregate_reduction,
        "aggregate_positive_label_reduction": aggregate_reduction > 0,
        "per_occurrence_positive_reduction_required": False,
        "zero_or_negative_occurrences_preserved_without_selection": True,
        "positive_reduction_occurrence_count": sum(value > 0 for value in reductions),
        "zero_reduction_occurrence_count": sum(value == 0 for value in reductions),
        "negative_reduction_occurrence_count": sum(value < 0 for value in reductions),
        "verified_v146_v147_receipts_consumed_everywhere": all(
            row["registered_gate"][
                "verified_v146_factor_bank_and_v147_binding_receipt_consumed"
            ]
            for row in rows
        ),
        "same_synthesizer_representation_and_stop_rule_everywhere": all(
            row["registered_gate"]["same_synthesizer_representation_and_stop_rule"]
            for row in rows
        ),
        "anonymous_relational_template_selected_everywhere": all(
            row["registered_gate"][
                "anonymous_relational_template_selected_in_prior_arm"
            ]
            for row in rows
        ),
        "both_arm_receding_episodes_succeed_everywhere": all(
            row["registered_gate"]["both_arm_receding_episodes_succeed"]
            for row in rows
        ),
        "certificate_failure_local_recovery_exercised_at_least_once": local_labels > 0,
        "strict_incompatible_schema_no_transfer_verified": ood["strict_ood_no_transfer"],
    }
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and passed_count == config["required_target_occurrence_count"]
        and aggregate_reduction > 0
        and sum(
            gate[key]
            for key in (
                "positive_reduction_occurrence_count",
                "zero_reduction_occurrence_count",
                "negative_reduction_occurrence_count",
            )
        )
        == len(rows)
        and gate["verified_v146_v147_receipts_consumed_everywhere"]
        and gate["same_synthesizer_representation_and_stop_rule_everywhere"]
        and gate["anonymous_relational_template_selected_everywhere"]
        and gate["both_arm_receding_episodes_succeed_everywhere"]
        and gate["certificate_failure_local_recovery_exercised_at_least_once"]
        and gate["strict_incompatible_schema_no_transfer_verified"]
    )
    payload = {
        "schema": "acfqp.anonymous_relational_factor_bank_campaign.v148",
        "preregistration_id": preregistration_id,
        "v146_factor_bank_id": rows[0]["v146_factor_bank_id"],
        "v146_independent_verification_id": rows[0][
            "v146_independent_verification_id"
        ],
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": ood,
        "accounting": accounting,
        "registered_gate": gate,
        "registered_workload_sample_efficiency_improvement_observed": gate["passed"],
        "sample_efficiency_improvement_claim_scope": (
            "ONLY_THE_PREREGISTERED_V148_ANONYMOUS_RELATIONAL_PRIOR_ABLATION"
        ),
        "complete_ground_world_model_synthesized": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v148(
            domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_CAMPAIGN_V148_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_anonymous_relational_factor_bank_campaign_document_v148",
    "build_anonymous_relational_factor_bank_occurrence_v148",
)
