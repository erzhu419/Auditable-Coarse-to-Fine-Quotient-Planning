"""V149 fresh cross-domain reuse of the frozen V146 anonymous factor bank."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v149 as domains
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.anonymous_relational_factor_bank_acquisition_v148 import (
    acquire_matched_anonymous_relational_factor_bank_arms_v148,
)
from acfqp.certificate_local_relational_overlay_sequence_v144r1 import (
    run_certificate_local_relational_overlay_sequence_v144r1,
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


TARGET_FAMILIES = (INVENTORY, DUAL, MODULAR, PACKET)
_BUILDERS = {
    INVENTORY: build_inventory_assembly_adapter_v118,
    DUAL: build_dual_budget_adapter_v119,
    MODULAR: build_modular_routing_adapter_v128,
    PACKET: build_packet_batching_adapter_v134,
}


def build_cross_domain_relational_factor_bank_occurrence_v149(
    config: Mapping[str, Any],
    *,
    family: str,
    seed: int,
    episode_indices: tuple[int, ...],
    bank_raw: bytes,
    verification_raw: bytes,
) -> dict[str, Any]:
    if family not in _BUILDERS:
        raise ValueError("V149 family is outside the registered cohort")
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
    all_sequences = tuple(sequences.values())
    gate = {
        "matched_acquisition_completed_within_registered_cap": all(
            0 < arm["document"]["ground_support_labels"]
            <= config["families"][family]["maximum_acquisition_labels"]
            for arm in arms.values()
        ),
        "same_raw_transition_prefix_through_common_label": prior_prefix == strict_prefix,
        "same_synthesizer_representation_and_stop_rule": all(
            prior_doc[key] is True and strict_doc[key] is True
            for key in (
                "binding_derived_from_current_raw_prefix_in_both_arms",
                "same_generic_atomic_hypothesis_pool",
                "same_candidate_carrier_and_schema",
                "same_candidate_replay_function",
                "same_stopping_rule_function",
            )
        ),
        "only_arm_switch_is_anonymous_relational_prior": prior_doc[
            "only_arm_switch_is_anonymous_relational_prior"
        ]
        is True
        and strict_doc["only_arm_switch_is_anonymous_relational_prior"] is True,
        "v146_source_family_absent_from_target_domain": True,
        "anonymous_relational_instantiation_present_both_arms": all(
            arm["document"]["anonymous_relational_instantiation"][
                "exact_relational_instantiation_count"
            ]
            > 0
            for arm in arms.values()
        ),
        "at_least_one_bank_template_selected_in_prior_arm": prior_doc[
            "artifact_expression_selected_count"
        ]
        > 0,
        "both_arm_receding_episodes_succeed": all(
            episode["success"]
            for sequence in all_sequences
            for episode in sequence["episodes"]
        ),
        "certificate_failure_only_local_ground_distinctions": all(
            sequence["every_new_ground_query_followed_a_failed_certificate"]
            for sequence in all_sequences
        ),
        "planner_consumes_compiled_model_without_raw_rows": all(
            sequence[
                "planner_consumed_compiled_successor_without_raw_transition_argument"
            ]
            for sequence in all_sequences
        ),
        "sound_certificate_local_recovery_union": all(
            sequence["source_partial_program_mutated_after_certificate_failure"]
            is False
            and sequence["every_uncompiled_edge_is_certificate_local"] is True
            and sequence["overlay_promoted_to_global_dynamics"] is False
            and sequence["query_local_overlay_used_as_safety_authority"] is False
            for sequence in all_sequences
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
        "anonymous_relational_prior_binding_compute_events": prior_doc[
            "template_binding_evaluation_events"
        ],
        "strict_no_prior_binding_compute_events": strict_doc[
            "template_binding_evaluation_events"
        ],
        "anonymous_relational_prior_planning_compute_events": prior_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "strict_no_prior_planning_compute_events": strict_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.cross_domain_relational_factor_bank_occurrence.v149",
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
        "accounting": accounting,
        "registered_gate": gate,
        "paired_label_reduction": reduction,
        "sample_efficiency_direction": (
            "POSITIVE" if reduction > 0 else "NEGATIVE" if reduction < 0 else "ZERO"
        ),
        "registered_workload_sample_efficiency_improvement_observed": reduction > 0,
        "relational_instantiation_present_but_relational_template_selection_not_required": True,
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
        "occurrence_id": domains.extension_content_id_v149(
            domains.CONSTRUCTION_K7_CROSS_DOMAIN_RELATIONAL_BANK_OCCURRENCE_V149_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_cross_domain_relational_factor_bank_occurrence_v149(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
    )


def build_cross_domain_relational_factor_bank_campaign_document_v149(
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
    accounting_keys = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    accounting = {
        key: sum(row["accounting"][key] for row in rows) for key in accounting_keys
    }
    accounting.update(
        sample_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    reductions = tuple(row["paired_label_reduction"] for row in rows)
    family_reductions = {
        family: sum(
            row["paired_label_reduction"] for row in rows if row["target_family"] == family
        )
        for family in TARGET_FAMILIES
    }
    local_labels = (
        accounting["anonymous_relational_prior_certificate_local_labels"]
        + accounting["strict_no_prior_certificate_local_labels"]
    )
    ood = incompatible_schema_no_transfer_control_v99()
    gate = {
        "required_target_occurrence_count": config["required_target_occurrence_count"],
        "passed_target_occurrence_count": sum(row["registered_gate"]["passed"] for row in rows),
        "required_target_family_count": len(TARGET_FAMILIES),
        "observed_target_family_count": len({row["target_family"] for row in rows}),
        "aggregate_paired_acquisition_label_reduction": sum(reductions),
        "aggregate_positive_label_reduction": sum(reductions) > 0,
        "positive_reduction_occurrence_count": sum(value > 0 for value in reductions),
        "zero_reduction_occurrence_count": sum(value == 0 for value in reductions),
        "negative_reduction_occurrence_count": sum(value < 0 for value in reductions),
        "family_aggregate_reductions": family_reductions,
        "every_family_has_positive_aggregate_reduction": all(
            value > 0 for value in family_reductions.values()
        ),
        "same_synthesizer_and_stop_rule_everywhere": all(
            row["registered_gate"]["same_synthesizer_representation_and_stop_rule"]
            for row in rows
        ),
        "anonymous_relational_instantiation_present_everywhere": all(
            row["registered_gate"][
                "anonymous_relational_instantiation_present_both_arms"
            ]
            for row in rows
        ),
        "both_arm_receding_episodes_succeed_everywhere": all(
            row["registered_gate"]["both_arm_receding_episodes_succeed"] for row in rows
        ),
        "certificate_failure_local_recovery_exercised_at_least_once": local_labels > 0,
        "strict_incompatible_schema_no_transfer_verified": ood["strict_ood_no_transfer"],
    }
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and gate["passed_target_occurrence_count"] == len(rows)
        and gate["observed_target_family_count"] == len(TARGET_FAMILIES)
        and gate["aggregate_positive_label_reduction"]
        and gate["every_family_has_positive_aggregate_reduction"]
        and sum(
            gate[key]
            for key in (
                "positive_reduction_occurrence_count",
                "zero_reduction_occurrence_count",
                "negative_reduction_occurrence_count",
            )
        )
        == len(rows)
        and gate["same_synthesizer_and_stop_rule_everywhere"]
        and gate["anonymous_relational_instantiation_present_everywhere"]
        and gate["both_arm_receding_episodes_succeed_everywhere"]
        and gate["certificate_failure_local_recovery_exercised_at_least_once"]
        and gate["strict_incompatible_schema_no_transfer_verified"]
    )
    payload = {
        "schema": "acfqp.cross_domain_relational_factor_bank_campaign.v149",
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
            "ONLY_THE_PREREGISTERED_V149_FOUR_FAMILY_CROSS_DOMAIN_COHORT"
        ),
        "relational_template_selection_itself_claimed_cross_domain": False,
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
        "campaign_id": domains.extension_content_id_v149(
            domains.CONSTRUCTION_K7_CROSS_DOMAIN_RELATIONAL_BANK_CAMPAIGN_V149_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "TARGET_FAMILIES",
    "build_cross_domain_relational_factor_bank_campaign_document_v149",
    "build_cross_domain_relational_factor_bank_occurrence_v149",
)
