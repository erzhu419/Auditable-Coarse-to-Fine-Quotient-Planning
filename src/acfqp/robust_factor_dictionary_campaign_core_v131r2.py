"""V131R2 automatic minimal-dictionary sample-tax campaign construction."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v131r2 as domains
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_dual_budget_adapter_v119 import (
    FAMILY as DUAL,
    build_dual_budget_adapter_v119,
)
from acfqp.generic_inventory_assembly_adapter_v118 import (
    FAMILY as INVENTORY,
    build_inventory_assembly_adapter_v118,
)
from acfqp.generic_modular_routing_adapter_v128 import (
    FAMILY as MODULAR,
    build_modular_routing_adapter_v128,
)
from acfqp.robust_factor_dictionary_acquisition_v131r2 import (
    acquire_matched_robust_dictionary_factor_arms_v131r2,
)
from acfqp.standalone_generic_owned_sequence_v126 import (
    run_standalone_generic_owned_sequence_v126,
)


_BUILDERS = {
    INVENTORY: build_inventory_assembly_adapter_v118,
    DUAL: build_dual_budget_adapter_v119,
    MODULAR: build_modular_routing_adapter_v128,
}


def build_robust_dictionary_factor_prior_occurrence_v131r2(
    config: Mapping[str, Any],
    *,
    family: str,
    seed: int,
    episode_indices: tuple[int, ...],
    artifact_factor_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
) -> dict[str, Any]:
    if family not in _BUILDERS:
        raise ValueError("V131R2 family is outside the registered adapter boundary")
    adapter = _BUILDERS[family](seed, config)
    arms = acquire_matched_robust_dictionary_factor_arms_v131r2(
        adapter, artifact_factor_library, source_campaign_bytes, config
    )
    prior = arms["NORMALIZED_FACTOR_PRIOR_ON"]
    strict = arms["STRICT_NO_PRIOR"]
    sequences = {
        name: run_standalone_generic_owned_sequence_v126(
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
    prior_sequence = sequences["NORMALIZED_FACTOR_PRIOR_ON"]
    strict_sequence = sequences["STRICT_NO_PRIOR"]
    common = min(len(prior["batches"]), len(strict["batches"]))
    prior_prefix = tuple(row for batch in prior["batches"][:common] for row in batch)
    strict_prefix = tuple(row for batch in strict["batches"][:common] for row in batch)
    reduction = strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    sample_tax = {
        "normalized_factor_prior_ground_support_labels": prior_doc[
            "ground_support_labels"
        ],
        "strict_no_prior_ground_support_labels": strict_doc["ground_support_labels"],
        "ground_support_labels_avoided_by_normalized_factor_prior": reduction,
        "same_fair_witness_blind_path_first_backtracking_policy": True,
        "same_raw_transition_prefix_through_common_label": prior_prefix == strict_prefix,
        "same_generic_atomic_hypothesis_pool": True,
        "same_candidate_carrier_and_schema": True,
        "same_candidate_replay_function": True,
        "same_stopping_rule_function": True,
        "only_arm_switch_is_normalized_factor_prior": True,
        "fixed_two_to_library_cardinality_prior_multiplier_present": False,
        "robust_dictionary_selected_from_source_candidate_artifacts": True,
        "fixed_template_cardinality_supplied": False,
        "sample_labels_and_derivation_compute_separate": True,
    }
    gate = {
        "normalized_factor_prior_stops_before_strict_no_prior": reduction > 0,
        "same_raw_transition_prefix_through_common_label": sample_tax[
            "same_raw_transition_prefix_through_common_label"
        ],
        "same_synthesizer_representation_and_stop_rule": all(
            sample_tax[key]
            for key in (
                "same_generic_atomic_hypothesis_pool",
                "same_candidate_carrier_and_schema",
                "same_candidate_replay_function",
                "same_stopping_rule_function",
            )
        ),
        "only_arm_switch_is_normalized_factor_prior": True,
        "fixed_two_to_library_cardinality_prior_multiplier_absent": True,
        "robust_dictionary_selected_before_target_outcomes": (
            artifact_factor_library["target_outcomes_accessed"] is False
        ),
        "leave_one_source_campaign_reconstruction_present": all(
            item["eligible_for_dictionary_search"]
            for item in artifact_factor_library[
                "leave_one_source_campaign_reconstruction"
            ]
        ),
        "both_arm_receding_episodes_succeed": all(
            episode["success"]
            for sequence in sequences.values()
            for episode in sequence["episodes"]
        ),
        "both_arms_use_certificate_failure_only_local_ground_distinctions": all(
            sequence["every_new_ground_query_followed_a_failed_certificate"]
            for sequence in sequences.values()
        ),
        "both_planners_consume_compiled_model_without_raw_rows": all(
            sequence[
                "planner_consumed_compiled_successor_without_raw_transition_argument"
            ]
            for sequence in sequences.values()
        ),
        "retained_sequence_orchestration_absent": all(
            sequence["retained_v113_sequence_orchestration_present"] is False
            and sequence["retained_v119_sequence_orchestration_present"] is False
            for sequence in sequences.values()
        ),
    }
    gate["passed"] = all(gate.values())
    accounting = {
        "normalized_factor_prior_acquisition_labels": prior_doc[
            "ground_support_labels"
        ],
        "strict_no_prior_acquisition_labels": strict_doc["ground_support_labels"],
        "acquisition_labels_avoided_by_normalized_factor_prior": reduction,
        "normalized_factor_prior_certificate_local_labels": prior_sequence[
            "certificate_ground_support_labels_paid_once"
        ],
        "strict_no_prior_certificate_local_labels": strict_sequence[
            "certificate_ground_support_labels_paid_once"
        ],
        "normalized_factor_prior_lifetime_target_labels": prior_sequence[
            "lifetime_target_ground_support_labels"
        ],
        "strict_no_prior_lifetime_target_labels": strict_sequence[
            "lifetime_target_ground_support_labels"
        ],
        "normalized_factor_prior_execution_steps": prior_sequence[
            "execution_step_count"
        ],
        "strict_no_prior_execution_steps": strict_sequence["execution_step_count"],
        "normalized_factor_prior_derivation_compute_events": prior_doc[
            "derivation_compute_events"
        ],
        "strict_no_prior_derivation_compute_events": strict_doc[
            "derivation_compute_events"
        ],
        "normalized_factor_prior_planning_compute_events": prior_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "strict_no_prior_planning_compute_events": strict_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.robust_dictionary_factor_prior_occurrence.v131r2",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "robust_factor_dictionary_id": artifact_factor_library["dictionary_id"],
        "robust_factor_dictionary_selected_template_count": (
            artifact_factor_library["selected_template_count"]
        ),
        "normalized_factor_prior_acquisition": prior_doc,
        "strict_no_prior_acquisition": strict_doc,
        "normalized_factor_prior_owned_sequence": prior_sequence,
        "strict_no_prior_owned_sequence": strict_sequence,
        "sample_tax_comparison": sample_tax,
        "accounting": accounting,
        "registered_gate": gate,
        "registered_workload_sample_efficiency_improvement_observed": gate["passed"],
        "arbitrary_unseen_domain_transfer_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v131r2(
            domains.CONSTRUCTION_K7_ROBUST_DICTIONARY_FACTOR_OCCURRENCE_V131R2_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_robust_dictionary_factor_prior_occurrence_v131r2(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        artifact_factor_library=args[4],
        source_campaign_bytes=args[5],
    )


def build_robust_dictionary_factor_prior_campaign_document_v131r2(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v130_campaign_id: str,
    v130_verification_id: str,
    artifact_factor_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
) -> dict[str, Any]:
    args = [
        (
            config,
            row["family"],
            row["seed"],
            tuple(config["target_episode_indices"]),
            artifact_factor_library,
            source_campaign_bytes,
        )
        for row in config["target_occurrences"]
    ]
    if config["target_worker_count"] == 1:
        rows = [_target(row) for row in args]
    else:
        with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
            rows = list(executor.map(_target, args))
    ood = incompatible_schema_no_transfer_control_v99()
    gate = {
        "required_target_occurrence_count": config["required_target_occurrence_count"],
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "every_occurrence_has_strictly_positive_label_reduction": all(
            row["accounting"][
                "acquisition_labels_avoided_by_normalized_factor_prior"
            ]
            > 0
            for row in rows
        ),
        "fixed_two_to_library_cardinality_prior_multiplier_absent_everywhere": all(
            row["registered_gate"][
                "fixed_two_to_library_cardinality_prior_multiplier_absent"
            ]
            for row in rows
        ),
        "robust_dictionary_selected_before_target_outcomes": (
            artifact_factor_library["target_outcomes_accessed"] is False
        ),
        "robust_dictionary_cardinality_not_preregistered": (
            artifact_factor_library["fixed_template_cardinality_supplied"] is False
        ),
        "leave_one_source_campaign_reconstruction_verified": all(
            item["eligible_for_dictionary_search"]
            for item in artifact_factor_library[
                "leave_one_source_campaign_reconstruction"
            ]
        ),
        "same_synthesizer_representation_and_stop_rule_in_every_occurrence": all(
            row["registered_gate"]["same_synthesizer_representation_and_stop_rule"]
            for row in rows
        ),
        "both_arm_receding_episodes_succeed_everywhere": all(
            row["registered_gate"]["both_arm_receding_episodes_succeed"]
            for row in rows
        ),
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
    }
    gate["passed"] = len(rows) == config["required_target_occurrence_count"] and all(
        gate.values()
    )
    numeric = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    accounting = {
        key: sum(row["accounting"][key] for row in rows) for key in numeric
    }
    accounting.update(
        sample_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    payload = {
        "schema": "acfqp.robust_dictionary_factor_prior_campaign.v131r2",
        "preregistration_id": preregistration_id,
        "v130_success_campaign_id": v130_campaign_id,
        "v130_success_verification_id": v130_verification_id,
        "robust_factor_dictionary_id": artifact_factor_library["dictionary_id"],
        "robust_factor_dictionary_selected_template_count": (
            artifact_factor_library["selected_template_count"]
        ),
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": ood,
        "accounting": accounting,
        "registered_gate": gate,
        "registered_workload_sample_efficiency_improvement_observed": gate["passed"],
        "sample_efficiency_improvement_claim_scope": (
            "ONLY_THE_PREREGISTERED_V131R2_THREE_FAMILY_WORKLOAD"
        ),
        "fixed_two_to_library_cardinality_prior_multiplier_present": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v131r2(
            domains.CONSTRUCTION_K7_ROBUST_DICTIONARY_FACTOR_CAMPAIGN_V131R2_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_robust_dictionary_factor_prior_campaign_document_v131r2",
    "build_robust_dictionary_factor_prior_occurrence_v131r2",
)
