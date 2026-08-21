"""Matched incremental-successor and full-rebuild campaign core V113."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v113 as domains
from acfqp import identity_short_circuited_epoch_campaign_core_v111 as previous
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_complete_anonymous_action_catalogue_receipt_v107 import (
    build_complete_anonymous_action_catalogue_receipt_v107,
    verify_complete_anonymous_action_catalogue_receipt_v107,
)
from acfqp.generic_incremental_abstract_successor_sequence_v113 import (
    run_incremental_abstract_successor_sequence_v113,
)


def build_incremental_abstract_successor_occurrence_v113(
    config: Mapping[str, Any],
    *,
    family: str,
    seed: int,
    episode_indices: tuple[int, ...],
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        family, seed, config
    )
    catalogue_receipt = verify_complete_anonymous_action_catalogue_receipt_v107(
        build_complete_anonymous_action_catalogue_receipt_v107(
            adapter.catalogue, family=family, seed=seed
        )
    )
    acquisition = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    common = {
        "episode_indices": episode_indices,
        "maximum_abstract_depth": config["maximum_abstract_depth"],
        "maximum_execution_steps": config["maximum_execution_steps"],
        "maximum_incremental_certificate_ground_support_labels": 100_000,
    }
    incremental = run_incremental_abstract_successor_sequence_v113(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        **common,
    )
    matched = previous.build_identity_short_circuited_epoch_occurrence_v111(
        config,
        family=family,
        seed=seed,
        episode_indices=episode_indices,
        factor_library=factor_library,
    )
    full_sequence = matched[
        "persistent_identity_short_circuited_epoch_sequence"
    ]
    exact_execution = (
        [row["action_keys"] for row in incremental["episodes"]]
        == [row["action_keys"] for row in full_sequence["episodes"]]
        and [row["abstract_plan_receipts"] for row in incremental["episodes"]]
        == [row["abstract_plan_receipts"] for row in full_sequence["episodes"]]
        and [
            row["abstract_execution_receipts"] for row in incremental["episodes"]
        ]
        == [
            row["abstract_execution_receipts"] for row in full_sequence["episodes"]
        ]
        and incremental["quotient_models_before_each_episode"]
        == full_sequence["quotient_models_before_each_episode"]
        and incremental["lifetime_target_ground_support_labels"]
        == full_sequence["lifetime_target_ground_support_labels"]
        and incremental["execution_step_count"]
        == full_sequence["execution_step_count"]
        and incremental["actual_new_abstract_planning_compute_events"]
        == full_sequence["actual_new_abstract_planning_compute_events"]
    )
    incremental_maintenance = incremental["dependency_maintenance_events"]
    matched_maintenance = matched["accounting"][
        "identity_short_dependency_maintenance_events"
    ]
    update_events = incremental["incremental_model_update_compilation_events"]
    rebuild_events = incremental[
        "matched_full_rebuild_update_compilation_events"
    ]
    labels = incremental["lifetime_target_ground_support_labels"]
    direct_labels = matched["accounting"]["cold_direct_lifetime_target_labels"]
    gate = {
        "incremental_and_full_rebuild_actions_plans_receipts_labels_steps_equal": exact_execution,
        "incremental_and_full_rebuild_dependency_maintenance_equal": incremental_maintenance
        == matched_maintenance,
        "every_incremental_model_exactly_matches_full_v105_rebuild": incremental[
            "all_model_successors_exactly_equal_full_v105_rebuild"
        ],
        "planner_consumes_compiled_model_without_raw_transition_argument": incremental[
            "planner_consumed_compiled_successor_without_raw_transition_argument"
        ],
        "incremental_update_compilation_strictly_below_full_rebuild": update_events
        < rebuild_events,
        "at_least_one_model_compilation_event_avoided": incremental[
            "model_compilation_events_avoided_against_full_rebuild"
        ]
        > 0,
        "epoch_authorized_cache_hit_observed": incremental[
            "epoch_authorized_cache_hit_count"
        ]
        > 0,
        "certificate_failure_only_query_discipline_clean": incremental[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "quotient_lifetime_labels_strictly_below_cold_direct": labels
        < direct_labels,
    }
    gate["passed"] = all(gate.values())
    accounting = {
        "initial_acquisition_labels": incremental[
            "initial_acquisition_ground_support_labels_paid_once"
        ],
        "certificate_local_labels": incremental[
            "certificate_ground_support_labels_paid_once"
        ],
        "incremental_quotient_lifetime_target_labels": labels,
        "matched_full_rebuild_quotient_lifetime_target_labels": full_sequence[
            "lifetime_target_ground_support_labels"
        ],
        "cold_direct_lifetime_target_labels": direct_labels,
        "target_label_reduction_against_cold_direct": direct_labels - labels,
        "execution_steps": incremental["execution_step_count"],
        "incremental_new_planning_compute_events": incremental[
            "actual_new_abstract_planning_compute_events"
        ],
        "matched_full_rebuild_new_planning_compute_events": full_sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "model_epoch_identity_checks": incremental[
            "model_epoch_identity_checks"
        ],
        "full_model_epoch_diff_checks": incremental[
            "full_model_epoch_diff_checks"
        ],
        "reverse_dependency_index_lookups": incremental[
            "reverse_dependency_index_lookups"
        ],
        "incremental_dependency_maintenance_events": incremental_maintenance,
        "matched_full_rebuild_dependency_maintenance_events": matched_maintenance,
        "bootstrap_model_compilation_events": incremental[
            "bootstrap_compilation_events_separate"
        ],
        "incremental_model_update_compilation_events": update_events,
        "matched_full_rebuild_update_compilation_events": rebuild_events,
        "model_compilation_events_avoided_against_full_rebuild": rebuild_events
        - update_events,
        "identity_short_circuit_count": incremental[
            "identity_short_circuit_count"
        ],
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "matched_control_compilation_not_charged_to_incremental_arm": True,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.incremental_abstract_successor_occurrence.v113",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "complete_anonymous_action_catalogue_receipt": catalogue_receipt,
        "partial_acquisition": acquisition["document"],
        "incremental_abstract_successor_sequence": incremental,
        "matched_full_rebuild_v111_occurrence": matched,
        "matched_full_rebuild_v111_occurrence_id": matched["occurrence_id"],
        "accounting": accounting,
        "registered_gate": gate,
        "incremental_world_model_successor_verified": gate["passed"],
        "local_ground_distinctions_only_after_certificate_failure_verified": gate[
            "passed"
        ],
        "compiled_model_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v113(
            domains.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_OCCURRENCE_V113_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_incremental_abstract_successor_occurrence_v113(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        factor_library=args[4],
    )


def build_incremental_abstract_successor_campaign_document_v113(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v112_campaign_id: str,
    v112_verification_id: str,
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    args = [
        (
            config,
            row["family"],
            row["seed"],
            tuple(config["target_episode_indices"]),
            factor_library,
        )
        for row in config["target_occurrences"]
    ]
    if config["target_worker_count"] == 1:
        occurrences = [_target(row) for row in args]
    else:
        with ProcessPoolExecutor(
            max_workers=config["target_worker_count"]
        ) as executor:
            occurrences = list(executor.map(_target, args))
    numeric_keys = tuple(occurrences[0]["accounting"])
    numeric = {
        key: sum(row["accounting"][key] for row in occurrences)
        for key in numeric_keys
        if type(occurrences[0]["accounting"][key]) is int
    }
    ood = incompatible_schema_no_transfer_control_v99()
    passed = (
        all(row["registered_gate"]["passed"] for row in occurrences)
        and numeric["incremental_model_update_compilation_events"]
        < numeric["matched_full_rebuild_update_compilation_events"]
        and numeric["model_compilation_events_avoided_against_full_rebuild"] > 0
        and numeric["incremental_quotient_lifetime_target_labels"]
        < numeric["cold_direct_lifetime_target_labels"]
        and ood["strict_ood_no_transfer"] is True
    )
    gate = {
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in occurrences
        ),
        "every_occurrence_exactly_matches_full_rebuild_execution": all(
            row["registered_gate"][
                "incremental_and_full_rebuild_actions_plans_receipts_labels_steps_equal"
            ]
            for row in occurrences
        ),
        "every_occurrence_incremental_model_equals_full_v105_rebuild": all(
            row["registered_gate"][
                "every_incremental_model_exactly_matches_full_v105_rebuild"
            ]
            for row in occurrences
        ),
        "every_occurrence_planner_uses_compiled_model_without_raw_rows": all(
            row["registered_gate"][
                "planner_consumes_compiled_model_without_raw_transition_argument"
            ]
            for row in occurrences
        ),
        "every_occurrence_incremental_compilation_below_full_rebuild": all(
            row["registered_gate"][
                "incremental_update_compilation_strictly_below_full_rebuild"
            ]
            for row in occurrences
        ),
        "aggregate_incremental_compilation_below_full_rebuild": numeric[
            "incremental_model_update_compilation_events"
        ]
        < numeric["matched_full_rebuild_update_compilation_events"],
        "aggregate_quotient_labels_below_cold_direct": numeric[
            "incremental_quotient_lifetime_target_labels"
        ]
        < numeric["cold_direct_lifetime_target_labels"],
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    payload = {
        "schema": "acfqp.incremental_abstract_successor_campaign.v113",
        "preregistration_id": preregistration_id,
        "v112_success_campaign_id": v112_campaign_id,
        "v112_success_verification_id": v112_verification_id,
        "target_occurrences": occurrences,
        "incompatible_schema_no_transfer_control": ood,
        "accounting": {
            **numeric,
            "offline_source_labels_not_recharged": True,
            "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": gate,
        "registered_incremental_abstract_successor_verified": passed,
        "ground_distinctions_acquired_only_after_certificate_failure_verified": passed,
        "compiled_model_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v113(
            domains.CONSTRUCTION_K7_INCREMENTAL_ABSTRACT_SUCCESSOR_CAMPAIGN_V113_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_incremental_abstract_successor_campaign_document_v113",
    "build_incremental_abstract_successor_occurrence_v113",
)
