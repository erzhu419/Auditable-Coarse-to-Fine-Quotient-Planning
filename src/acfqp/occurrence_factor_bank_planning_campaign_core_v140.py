"""V140 campaign: verified occurrence-factor-bank archive into planning."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v140 as domains
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
from acfqp.generic_packet_batching_adapter_v134 import (
    FAMILY as PACKET,
    build_packet_batching_adapter_v134,
)
from acfqp.occurrence_factor_bank_acquisition_v140 import (
    acquire_matched_occurrence_factor_bank_factor_arms_v140,
)
from acfqp.standalone_generic_owned_sequence_v126 import (
    run_standalone_generic_owned_sequence_v126,
)


_BUILDERS = {
    INVENTORY: build_inventory_assembly_adapter_v118,
    DUAL: build_dual_budget_adapter_v119,
    MODULAR: build_modular_routing_adapter_v128,
    PACKET: build_packet_batching_adapter_v134,
}


def build_occurrence_factor_bank_planning_occurrence_v140(
    config: Mapping[str, Any],
    *,
    family: str,
    seed: int,
    episode_indices: tuple[int, ...],
    dictionary: Mapping[str, Any],
    dictionary_verification: Mapping[str, Any],
) -> dict[str, Any]:
    if family not in _BUILDERS:
        raise ValueError("V140 family is outside the registered adapter boundary")
    adapter = _BUILDERS[family](seed, config)
    arms = acquire_matched_occurrence_factor_bank_factor_arms_v140(
        adapter, dictionary, dictionary_verification, config
    )
    prior = arms["OCCURRENCE_FACTOR_BANK_FACTOR_PRIOR_ON"]
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
    prior_sequence = sequences["OCCURRENCE_FACTOR_BANK_FACTOR_PRIOR_ON"]
    strict_sequence = sequences["STRICT_NO_PRIOR"]
    common = min(len(prior["batches"]), len(strict["batches"]))
    prior_prefix = tuple(row for batch in prior["batches"][:common] for row in batch)
    strict_prefix = tuple(row for batch in strict["batches"][:common] for row in batch)
    reduction = strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    sample_tax = {
        "occurrence_factor_bank_factor_prior_ground_support_labels": prior_doc[
            "ground_support_labels"
        ],
        "strict_no_prior_ground_support_labels": strict_doc["ground_support_labels"],
        "ground_support_labels_avoided_by_occurrence_factor_bank_prior": reduction,
        "same_fair_witness_blind_path_first_backtracking_policy": True,
        "same_raw_transition_prefix_through_common_label": prior_prefix == strict_prefix,
        "same_generic_atomic_hypothesis_pool": True,
        "same_candidate_carrier_and_schema": True,
        "same_candidate_replay_function": True,
        "same_stopping_rule_function": True,
        "only_arm_switch_is_normalized_factor_prior": True,
        "verified_v139_factor_bank_is_the_only_structural_prior_input": True,
        "fixed_source_inventory_reintroduced": False,
        "sample_labels_and_derivation_compute_separate": True,
    }
    gate = {
        "occurrence_factor_bank_prior_stops_before_strict_no_prior": reduction > 0,
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
        "verified_v139_factor_bank_receipt_consumed": all(
            arm["document"][
                "verified_factor_bank_receipt_consumed_before_target_outcomes"
            ]
            for arm in arms.values()
        ),
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
    }
    gate["passed"] = all(gate.values())
    accounting = {
        "occurrence_factor_bank_prior_acquisition_labels": prior_doc[
            "ground_support_labels"
        ],
        "strict_no_prior_acquisition_labels": strict_doc["ground_support_labels"],
        "acquisition_labels_avoided_by_occurrence_factor_bank_prior": reduction,
        "occurrence_factor_bank_prior_certificate_local_labels": prior_sequence[
            "certificate_ground_support_labels_paid_once"
        ],
        "strict_no_prior_certificate_local_labels": strict_sequence[
            "certificate_ground_support_labels_paid_once"
        ],
        "occurrence_factor_bank_prior_lifetime_target_labels": prior_sequence[
            "lifetime_target_ground_support_labels"
        ],
        "strict_no_prior_lifetime_target_labels": strict_sequence[
            "lifetime_target_ground_support_labels"
        ],
        "occurrence_factor_bank_prior_execution_steps": prior_sequence[
            "execution_step_count"
        ],
        "strict_no_prior_execution_steps": strict_sequence["execution_step_count"],
        "occurrence_factor_bank_prior_derivation_compute_events": prior_doc[
            "derivation_compute_events"
        ],
        "strict_no_prior_derivation_compute_events": strict_doc[
            "derivation_compute_events"
        ],
        "occurrence_factor_bank_prior_planning_compute_events": prior_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "strict_no_prior_planning_compute_events": strict_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.occurrence_factor_bank_planning_occurrence.v140",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "v139_factor_bank_id": dictionary["bank_id"],
        "v139_independent_verification_id": dictionary_verification["verification_id"],
        "occurrence_factor_bank_factor_prior_acquisition": prior_doc,
        "strict_no_prior_acquisition": strict_doc,
        "occurrence_factor_bank_factor_prior_owned_sequence": prior_sequence,
        "strict_no_prior_owned_sequence": strict_sequence,
        "sample_tax_comparison": sample_tax,
        "accounting": accounting,
        "registered_gate": gate,
        "registered_workload_sample_efficiency_improvement_observed": gate["passed"],
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
        "occurrence_id": domains.extension_content_id_v140(
            domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_OCCURRENCE_V140_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_occurrence_factor_bank_planning_occurrence_v140(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        dictionary=args[4],
        dictionary_verification=args[5],
    )


def build_occurrence_factor_bank_planning_campaign_document_v140(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    dictionary: Mapping[str, Any],
    dictionary_verification: Mapping[str, Any],
) -> dict[str, Any]:
    args = [
        (
            config,
            row["family"],
            row["seed"],
            tuple(config["target_episode_indices"]),
            dictionary,
            dictionary_verification,
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
            row["accounting"]["acquisition_labels_avoided_by_occurrence_factor_bank_prior"]
            > 0
            for row in rows
        ),
        "verified_v139_factor_bank_receipt_consumed_everywhere": all(
            row["registered_gate"]["verified_v139_factor_bank_receipt_consumed"]
            for row in rows
        ),
        "same_synthesizer_representation_and_stop_rule_everywhere": all(
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
        "schema": "acfqp.occurrence_factor_bank_planning_campaign.v140",
        "preregistration_id": preregistration_id,
        "v139_factor_bank_id": dictionary["bank_id"],
        "v139_independent_verification_id": dictionary_verification["verification_id"],
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": ood,
        "accounting": accounting,
        "registered_gate": gate,
        "registered_workload_sample_efficiency_improvement_observed": gate["passed"],
        "sample_efficiency_improvement_claim_scope": (
            "ONLY_THE_PREREGISTERED_V140_FOUR_FAMILY_WORKLOAD"
        ),
        "fixed_source_campaign_inventory_reintroduced": False,
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
        "campaign_id": domains.extension_content_id_v140(
            domains.CONSTRUCTION_K7_OCCURRENCE_FACTOR_BANK_CAMPAIGN_V140_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_occurrence_factor_bank_planning_campaign_document_v140",
    "build_occurrence_factor_bank_planning_occurrence_v140",
)
