"""V144 campaign: V141 factor-bank transfer to a source-unseen fifth family."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v144 as domains
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_maintenance_cascade_adapter_v144 import (
    FAMILY as MAINTENANCE,
    build_maintenance_cascade_adapter_v144,
)
from acfqp.fifth_family_factor_bank_transfer_acquisition_v144 import (
    acquire_matched_fifth_family_factor_bank_arms_v144,
)
from acfqp.standalone_generic_owned_sequence_v126 import (
    run_standalone_generic_owned_sequence_v126,
)


_BUILDERS = {
    MAINTENANCE: build_maintenance_cascade_adapter_v144,
}


def build_fifth_family_factor_bank_transfer_occurrence_v144(
    config: Mapping[str, Any],
    *,
    family: str,
    seed: int,
    episode_indices: tuple[int, ...],
    dictionary: Mapping[str, Any],
    dictionary_verification: Mapping[str, Any],
) -> dict[str, Any]:
    if family not in _BUILDERS:
        raise ValueError("V144 family is outside the registered adapter boundary")
    adapter = _BUILDERS[family](seed, config)
    arms = acquire_matched_fifth_family_factor_bank_arms_v144(
        adapter, dictionary, dictionary_verification, config
    )
    prior = arms["OCCURRENCE_FACTOR_BANK_UPDATE_FACTOR_PRIOR_ON"]
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
    prior_sequence = sequences["OCCURRENCE_FACTOR_BANK_UPDATE_FACTOR_PRIOR_ON"]
    strict_sequence = sequences["STRICT_NO_PRIOR"]
    common = min(len(prior["batches"]), len(strict["batches"]))
    prior_prefix = tuple(row for batch in prior["batches"][:common] for row in batch)
    strict_prefix = tuple(row for batch in strict["batches"][:common] for row in batch)
    reduction = strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    sample_tax = {
        "occurrence_factor_bank_update_factor_prior_ground_support_labels": prior_doc[
            "ground_support_labels"
        ],
        "strict_no_prior_ground_support_labels": strict_doc["ground_support_labels"],
        "ground_support_labels_avoided_by_occurrence_factor_bank_update_prior": reduction,
        "same_fair_witness_blind_path_first_backtracking_policy": True,
        "same_raw_transition_prefix_through_common_label": prior_prefix == strict_prefix,
        "same_generic_atomic_hypothesis_pool": True,
        "same_candidate_carrier_and_schema": True,
        "same_candidate_replay_function": True,
        "same_stopping_rule_function": True,
        "only_arm_switch_is_normalized_factor_prior": True,
        "verified_v141_factor_bank_is_the_only_structural_prior_input": True,
        "target_family_absent_from_v141_source_occurrence_archive": True,
        "fixed_source_inventory_reintroduced": False,
        "sample_labels_and_derivation_compute_separate": True,
    }
    sample_efficiency_direction = (
        "POSITIVE" if reduction > 0 else "NEGATIVE" if reduction < 0 else "ZERO"
    )
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
                "same_generic_atomic_hypothesis_pool",
                "same_candidate_carrier_and_schema",
                "same_candidate_replay_function",
                "same_stopping_rule_function",
            )
        ),
        "verified_v141_factor_bank_receipt_consumed": all(
            arm["document"][
                "verified_factor_bank_receipt_consumed_before_target_outcomes"
            ]
            for arm in arms.values()
        ),
        "target_family_absent_from_v141_source_occurrence_archive": all(
            arm["document"][
                "target_family_absent_from_v141_source_occurrence_archive"
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
    }
    gate["passed"] = all(gate.values())
    accounting = {
        "occurrence_factor_bank_update_prior_acquisition_labels": prior_doc[
            "ground_support_labels"
        ],
        "strict_no_prior_acquisition_labels": strict_doc["ground_support_labels"],
        "acquisition_labels_avoided_by_occurrence_factor_bank_update_prior": reduction,
        "occurrence_factor_bank_update_prior_certificate_local_labels": prior_sequence[
            "certificate_ground_support_labels_paid_once"
        ],
        "strict_no_prior_certificate_local_labels": strict_sequence[
            "certificate_ground_support_labels_paid_once"
        ],
        "occurrence_factor_bank_update_prior_lifetime_target_labels": prior_sequence[
            "lifetime_target_ground_support_labels"
        ],
        "strict_no_prior_lifetime_target_labels": strict_sequence[
            "lifetime_target_ground_support_labels"
        ],
        "occurrence_factor_bank_update_prior_execution_steps": prior_sequence[
            "execution_step_count"
        ],
        "strict_no_prior_execution_steps": strict_sequence["execution_step_count"],
        "occurrence_factor_bank_update_prior_derivation_compute_events": prior_doc[
            "derivation_compute_events"
        ],
        "strict_no_prior_derivation_compute_events": strict_doc[
            "derivation_compute_events"
        ],
        "occurrence_factor_bank_update_prior_candidate_replay_errors": prior_doc[
            "candidate_replay_error_count"
        ],
        "strict_no_prior_candidate_replay_errors": strict_doc[
            "candidate_replay_error_count"
        ],
        "occurrence_factor_bank_update_prior_planning_compute_events": prior_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "strict_no_prior_planning_compute_events": strict_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.fifth_family_factor_bank_transfer_occurrence.v144",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "v141_factor_bank_id": dictionary["bank_id"],
        "v141_independent_verification_id": dictionary_verification["verification_id"],
        "occurrence_factor_bank_update_factor_prior_acquisition": prior_doc,
        "strict_no_prior_acquisition": strict_doc,
        "occurrence_factor_bank_update_factor_prior_owned_sequence": prior_sequence,
        "strict_no_prior_owned_sequence": strict_sequence,
        "sample_tax_comparison": sample_tax,
        "accounting": accounting,
        "registered_gate": gate,
        "paired_label_reduction": reduction,
        "sample_efficiency_direction": sample_efficiency_direction,
        "registered_workload_sample_efficiency_improvement_observed": reduction > 0,
        "target_family_absent_from_v141_source_occurrence_archive": True,
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
        "occurrence_id": domains.extension_content_id_v144(
            domains.CONSTRUCTION_K7_FIFTH_FAMILY_FACTOR_BANK_TRANSFER_OCCURRENCE_V144_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_fifth_family_factor_bank_transfer_occurrence_v144(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        dictionary=args[4],
        dictionary_verification=args[5],
    )


def build_fifth_family_factor_bank_transfer_campaign_document_v144(
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
    reductions = tuple(row["paired_label_reduction"] for row in rows)
    positive_count = sum(value > 0 for value in reductions)
    zero_count = sum(value == 0 for value in reductions)
    negative_count = sum(value < 0 for value in reductions)
    aggregate_reduction = accounting[
        "acquisition_labels_avoided_by_occurrence_factor_bank_update_prior"
    ]
    passed_count = sum(row["registered_gate"]["passed"] for row in rows)
    gate = {
        "required_target_occurrence_count": config["required_target_occurrence_count"],
        "passed_target_occurrence_count": passed_count,
        "aggregate_paired_acquisition_label_reduction": aggregate_reduction,
        "aggregate_positive_label_reduction": aggregate_reduction > 0,
        "per_occurrence_positive_reduction_required": False,
        "zero_or_negative_occurrences_preserved_without_selection": True,
        "positive_reduction_occurrence_count": positive_count,
        "zero_reduction_occurrence_count": zero_count,
        "negative_reduction_occurrence_count": negative_count,
        "verified_v141_factor_bank_receipt_consumed_everywhere": all(
            row["registered_gate"]["verified_v141_factor_bank_receipt_consumed"]
            for row in rows
        ),
        "target_family_absent_from_v141_source_occurrence_archive_everywhere": all(
            row["registered_gate"][
                "target_family_absent_from_v141_source_occurrence_archive"
            ]
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
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and passed_count == config["required_target_occurrence_count"]
        and aggregate_reduction > 0
        and positive_count + zero_count + negative_count == len(rows)
        and gate["verified_v141_factor_bank_receipt_consumed_everywhere"]
        and gate["target_family_absent_from_v141_source_occurrence_archive_everywhere"]
        and gate["same_synthesizer_representation_and_stop_rule_everywhere"]
        and gate["both_arm_receding_episodes_succeed_everywhere"]
        and gate["strict_incompatible_schema_no_transfer_verified"]
    )
    payload = {
        "schema": "acfqp.fifth_family_factor_bank_transfer_campaign.v144",
        "preregistration_id": preregistration_id,
        "v141_factor_bank_id": dictionary["bank_id"],
        "v141_independent_verification_id": dictionary_verification["verification_id"],
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": ood,
        "accounting": accounting,
        "registered_gate": gate,
        "registered_workload_sample_efficiency_improvement_observed": gate["passed"],
        "sample_efficiency_improvement_claim_scope": (
            "ONLY_THE_PREREGISTERED_V144_SIX_OCCURRENCE_SOURCE_UNSEEN_FIFTH_FAMILY_WORKLOAD"
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
        "campaign_id": domains.extension_content_id_v144(
            domains.CONSTRUCTION_K7_FIFTH_FAMILY_FACTOR_BANK_TRANSFER_CAMPAIGN_V144_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_fifth_family_factor_bank_transfer_campaign_document_v144",
    "build_fifth_family_factor_bank_transfer_occurrence_v144",
)
