"""V134 source-unseen domain transfer using the verified opaque dictionary."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v134 as domains
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_packet_batching_adapter_v134 import (
    FAMILY,
    build_packet_batching_adapter_v134,
)
from acfqp.opaque_archive_factor_acquisition_v133 import (
    acquire_matched_opaque_archive_factor_arms_v133,
)
from acfqp.standalone_generic_owned_sequence_v126 import (
    run_standalone_generic_owned_sequence_v126,
)


def build_packet_batching_transfer_occurrence_v134(
    config: Mapping[str, Any],
    *,
    seed: int,
    episode_indices: tuple[int, ...],
    dictionary: Mapping[str, Any],
    dictionary_verification: Mapping[str, Any],
) -> dict[str, Any]:
    adapter = build_packet_batching_adapter_v134(seed, config)
    arms = acquire_matched_opaque_archive_factor_arms_v133(
        adapter, dictionary, dictionary_verification, config
    )
    prior = arms["OPAQUE_ARCHIVE_FACTOR_PRIOR_ON"]
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
    prior_sequence = sequences["OPAQUE_ARCHIVE_FACTOR_PRIOR_ON"]
    strict_sequence = sequences["STRICT_NO_PRIOR"]
    common = min(len(prior["batches"]), len(strict["batches"]))
    common_prefix_equal = tuple(
        row for batch in prior["batches"][:common] for row in batch
    ) == tuple(row for batch in strict["batches"][:common] for row in batch)
    reduction = strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    accounting = {
        "opaque_archive_prior_acquisition_labels": prior_doc["ground_support_labels"],
        "strict_no_prior_acquisition_labels": strict_doc["ground_support_labels"],
        "acquisition_labels_avoided_by_opaque_archive_prior": reduction,
        "opaque_archive_prior_certificate_local_labels": prior_sequence[
            "certificate_ground_support_labels_paid_once"
        ],
        "strict_no_prior_certificate_local_labels": strict_sequence[
            "certificate_ground_support_labels_paid_once"
        ],
        "opaque_archive_prior_lifetime_target_labels": prior_sequence[
            "lifetime_target_ground_support_labels"
        ],
        "strict_no_prior_lifetime_target_labels": strict_sequence[
            "lifetime_target_ground_support_labels"
        ],
        "opaque_archive_prior_execution_steps": prior_sequence["execution_step_count"],
        "strict_no_prior_execution_steps": strict_sequence["execution_step_count"],
        "opaque_archive_prior_derivation_compute_events": prior_doc[
            "derivation_compute_events"
        ],
        "strict_no_prior_derivation_compute_events": strict_doc[
            "derivation_compute_events"
        ],
        "opaque_archive_prior_planning_compute_events": prior_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "strict_no_prior_planning_compute_events": strict_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "source_unseen_domain_identity_present": adapter.family == FAMILY,
        "opaque_archive_prior_stops_before_strict_no_prior": reduction > 0,
        "same_raw_transition_prefix_through_common_label": common_prefix_equal,
        "only_arm_switch_is_normalized_factor_prior": True,
        "verified_v132_receipt_consumed": all(
            arm["document"][
                "verified_dictionary_receipt_consumed_before_target_outcomes"
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
    payload = {
        "schema": "acfqp.packet_batching_source_unseen_transfer_occurrence.v134",
        "target_family": FAMILY,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "v132_dictionary_id": dictionary["dictionary_id"],
        "v132_independent_verification_id": dictionary_verification["verification_id"],
        "v132_dictionary_predates_packet_batching_domain_implementation": True,
        "opaque_archive_factor_prior_acquisition": prior_doc,
        "strict_no_prior_acquisition": strict_doc,
        "opaque_archive_factor_prior_owned_sequence": prior_sequence,
        "strict_no_prior_owned_sequence": strict_sequence,
        "accounting": accounting,
        "registered_gate": gate,
        "registered_source_unseen_domain_sample_efficiency_improvement_observed": gate[
            "passed"
        ],
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
        "occurrence_id": domains.extension_content_id_v134(
            domains.CONSTRUCTION_K7_PACKET_BATCHING_TRANSFER_OCCURRENCE_V134_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_packet_batching_transfer_occurrence_v134(
        args[0],
        seed=args[1],
        episode_indices=args[2],
        dictionary=args[3],
        dictionary_verification=args[4],
    )


def build_packet_batching_transfer_campaign_document_v134(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    dictionary: Mapping[str, Any],
    dictionary_verification: Mapping[str, Any],
) -> dict[str, Any]:
    args = [
        (
            config,
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
            row["accounting"]["acquisition_labels_avoided_by_opaque_archive_prior"]
            > 0
            for row in rows
        ),
        "source_unseen_domain_verified_everywhere": all(
            row["registered_gate"]["source_unseen_domain_identity_present"]
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
        "schema": "acfqp.packet_batching_source_unseen_transfer_campaign.v134",
        "preregistration_id": preregistration_id,
        "v132_dictionary_id": dictionary["dictionary_id"],
        "v132_independent_verification_id": dictionary_verification["verification_id"],
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": ood,
        "accounting": accounting,
        "registered_gate": gate,
        "registered_source_unseen_domain_sample_efficiency_improvement_observed": gate[
            "passed"
        ],
        "sample_efficiency_improvement_claim_scope": (
            "ONLY_THE_PREREGISTERED_V134_PACKET_BATCHING_WORKLOAD"
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
        "campaign_id": domains.extension_content_id_v134(
            domains.CONSTRUCTION_K7_PACKET_BATCHING_TRANSFER_CAMPAIGN_V134_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_packet_batching_transfer_campaign_document_v134",
    "build_packet_batching_transfer_occurrence_v134",
)
