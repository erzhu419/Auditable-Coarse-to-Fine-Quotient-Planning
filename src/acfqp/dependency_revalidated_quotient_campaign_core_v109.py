"""Matched dependency-revalidated/no-cache quotient campaign V109."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v109 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_complete_anonymous_action_catalogue_receipt_v107 import (
    build_complete_anonymous_action_catalogue_receipt_v107,
    verify_complete_anonymous_action_catalogue_receipt_v107,
)
from acfqp.generic_dependency_revalidated_quotient_sequence_v109 import (
    run_dependency_revalidated_quotient_sequence_v109,
)
from acfqp.generic_persistent_legality_conditioned_quotient_sequence_v106 import (
    run_persistent_legality_conditioned_quotient_sequence_v106,
)
from acfqp.generic_persistent_multi_residual_sequence_v96 import (
    run_strict_cold_direct_sequence_v96,
)


_LOCAL_LEGALITY_SOURCES = {
    "CERTIFICATE_LOCAL_LEGALITY_AFTER_FAILURE",
    "CERTIFICATE_LOCAL_LEGALITY_FROM_TRANSITION_AFTER_FAILURE",
}


def _utilization(sequence: Mapping[str, Any]) -> dict[str, Any]:
    receipts = sequence["all_actual_legality_conditioned_execution_receipts"]
    steps = len(receipts)
    admitted = sum(
        row["quotient_proposal_admitted_to_real_action_order"] for row in receipts
    )
    matches = sum(
        row["chosen_action_matches_admitted_quotient_proposal"] for row in receipts
    )
    local = sum(
        row["legality_support_source"] in _LOCAL_LEGALITY_SOURCES
        for row in receipts
    )
    return {
        "schema": "acfqp.dependency_revalidated_quotient_utilization.v109",
        "execution_receipt_count": steps,
        "execution_step_count": steps,
        "quotient_proposal_admitted_execution_count": admitted,
        "chosen_action_matches_admitted_quotient_proposal_count": matches,
        "certificate_local_legality_plan_count": local,
        "quotient_proposal_admitted_fraction_numerator": admitted,
        "quotient_proposal_admitted_fraction_denominator": steps,
        "chosen_action_match_fraction_numerator": matches,
        "chosen_action_match_fraction_denominator": steps,
        "quotient_actually_orders_strict_majority_of_execution": 2 * admitted > steps,
        "quotient_actually_orders_at_least_three_quarters_of_execution": 4
        * admitted
        >= 3 * steps,
        "chosen_action_matches_quotient_strict_majority": 2 * matches > steps,
        "every_action_independently_receipted": True,
        "receipt_replay_uses_no_producer_summary_count": True,
        "ordering_is_engine_input_not_posthoc_policy_match": True,
        "certified_legality_is_boundary_condition_not_transition_model": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }


def build_dependency_revalidated_quotient_occurrence_v109(
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
    reused = run_dependency_revalidated_quotient_sequence_v109(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        **common,
    )
    no_cache = run_persistent_legality_conditioned_quotient_sequence_v106(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        **common,
    )
    direct = run_strict_cold_direct_sequence_v96(
        adapter,
        acquisition["candidate"],
        episode_indices=episode_indices,
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    utilization = _utilization(reused)
    same_actions = [row["action_keys"] for row in reused["episodes"]] == [
        row["action_keys"] for row in no_cache["episodes"]
    ]
    same_base_receipts = [
        row["abstract_execution_receipts"] for row in reused["episodes"]
    ] == [row["abstract_execution_receipts"] for row in no_cache["episodes"]]
    same_labels = reused["lifetime_target_ground_support_labels"] == no_cache[
        "lifetime_target_ground_support_labels"
    ]
    same_steps = reused["execution_step_count"] == no_cache["execution_step_count"]
    actual_compute = reused["actual_new_abstract_planning_compute_events"]
    baseline_compute = sum(
        row["abstract_planning_compute_events"] for row in no_cache["episodes"]
    )
    quotient_labels = reused["lifetime_target_ground_support_labels"]
    direct_labels = direct["lifetime_target_ground_support_labels"]
    later_zero_label_reuse = any(
        row["episode_index"] != episode_indices[0]
        and row["new_certificate_labels_charged_this_episode"] == 0
        and row["quotient_proposal_admitted_execution_count"] > 0
        for row in reused["episodes"]
    )
    gate = {
        "revalidated_and_no_cache_action_sequences_exactly_match": same_actions,
        "revalidated_and_no_cache_base_execution_receipts_exactly_match": same_base_receipts,
        "revalidated_and_no_cache_target_labels_exactly_match": same_labels,
        "revalidated_and_no_cache_execution_steps_exactly_match": same_steps,
        "actual_new_planning_compute_strictly_below_no_cache": actual_compute
        < baseline_compute,
        "dependency_revalidated_hit_observed": reused[
            "dependency_revalidated_cache_hit_count"
        ]
        > 0,
        "quotient_model_orders_at_least_three_quarters": utilization[
            "quotient_actually_orders_at_least_three_quarters_of_execution"
        ],
        "chosen_action_matches_quotient_strict_majority": utilization[
            "chosen_action_matches_quotient_strict_majority"
        ],
        "certificate_failure_only_query_discipline_clean": reused[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "later_zero_label_quotient_reuse_observed": later_zero_label_reuse,
        "quotient_lifetime_labels_strictly_below_cold_direct": quotient_labels
        < direct_labels,
    }
    gate["passed"] = all(gate.values())
    accounting = {
        "initial_acquisition_labels": reused[
            "initial_acquisition_ground_support_labels_paid_once"
        ],
        "certificate_local_labels": reused[
            "certificate_ground_support_labels_paid_once"
        ],
        "dependency_revalidated_quotient_lifetime_target_labels": quotient_labels,
        "matched_no_cache_quotient_lifetime_target_labels": no_cache[
            "lifetime_target_ground_support_labels"
        ],
        "cold_direct_lifetime_target_labels": direct_labels,
        "target_label_reduction_against_cold_direct": direct_labels
        - quotient_labels,
        "execution_steps": utilization["execution_step_count"],
        "actual_new_abstract_planning_compute_events": actual_compute,
        "matched_no_cache_planning_compute_events": baseline_compute,
        "planning_compute_events_avoided": baseline_compute - actual_compute,
        "dependency_validation_checks": reused["dependency_validation_checks"],
        "sample_labels_execution_steps_planning_and_validation_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.dependency_revalidated_quotient_occurrence.v109",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "complete_anonymous_action_catalogue_receipt": catalogue_receipt,
        "partial_acquisition": acquisition["document"],
        "persistent_dependency_revalidated_quotient_sequence": reused,
        "matched_no_cache_legality_quotient_sequence": no_cache,
        "strict_cold_direct_sequence": direct,
        "legality_conditioned_quotient_utilization": utilization,
        "accounting": accounting,
        "registered_gate": gate,
        "dependency_revalidated_ordering_preserves_actions_labels_and_steps": gate[
            "passed"
        ],
        "local_ground_distinctions_only_after_certificate_failure_verified": gate[
            "passed"
        ],
        "cached_heuristic_used_as_safety_authority": False,
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
        "occurrence_id": domains.extension_content_id_v109(
            domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_OCCURRENCE_V109_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_dependency_revalidated_quotient_occurrence_v109(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        factor_library=args[4],
    )


def build_dependency_revalidated_quotient_campaign_document_v109(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v108_campaign_id: str,
    v108_verification_id: str,
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
    with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
        occurrences = list(executor.map(_target, args))
    total_keys = (
        "initial_acquisition_labels",
        "certificate_local_labels",
        "dependency_revalidated_quotient_lifetime_target_labels",
        "matched_no_cache_quotient_lifetime_target_labels",
        "cold_direct_lifetime_target_labels",
        "target_label_reduction_against_cold_direct",
        "execution_steps",
        "actual_new_abstract_planning_compute_events",
        "matched_no_cache_planning_compute_events",
        "planning_compute_events_avoided",
        "dependency_validation_checks",
    )
    totals = {
        key: sum(row["accounting"][key] for row in occurrences)
        for key in total_keys
    }
    ood = incompatible_schema_no_transfer_control_v99()
    passed = (
        all(row["registered_gate"]["passed"] for row in occurrences)
        and totals["actual_new_abstract_planning_compute_events"]
        < totals["matched_no_cache_planning_compute_events"]
        and totals["dependency_revalidated_quotient_lifetime_target_labels"]
        < totals["cold_direct_lifetime_target_labels"]
        and ood["strict_ood_no_transfer"] is True
    )
    gate = {
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in occurrences
        ),
        "every_occurrence_actions_base_receipts_labels_and_steps_equal_no_cache": all(
            row["registered_gate"][
                "revalidated_and_no_cache_action_sequences_exactly_match"
            ]
            and row["registered_gate"][
                "revalidated_and_no_cache_base_execution_receipts_exactly_match"
            ]
            and row["registered_gate"][
                "revalidated_and_no_cache_target_labels_exactly_match"
            ]
            and row["registered_gate"][
                "revalidated_and_no_cache_execution_steps_exactly_match"
            ]
            for row in occurrences
        ),
        "every_occurrence_planning_compute_strictly_reduced": all(
            row["registered_gate"][
                "actual_new_planning_compute_strictly_below_no_cache"
            ]
            for row in occurrences
        ),
        "aggregate_sample_labels_unchanged_by_reuse": totals[
            "dependency_revalidated_quotient_lifetime_target_labels"
        ]
        == totals["matched_no_cache_quotient_lifetime_target_labels"],
        "aggregate_quotient_labels_strictly_below_cold_direct": totals[
            "dependency_revalidated_quotient_lifetime_target_labels"
        ]
        < totals["cold_direct_lifetime_target_labels"],
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    payload = {
        "schema": "acfqp.dependency_revalidated_quotient_campaign.v109",
        "preregistration_id": preregistration_id,
        "v108_failed_campaign_id": v108_campaign_id,
        "v108_failed_verification_id": v108_verification_id,
        "target_occurrences": occurrences,
        "incompatible_schema_no_transfer_control": ood,
        "accounting": {
            **totals,
            "offline_source_labels_not_recharged": True,
            "sample_labels_execution_steps_planning_and_validation_compute_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": gate,
        "registered_dependency_revalidated_quotient_reuse_verified": passed,
        "ground_distinctions_acquired_only_after_certificate_failure_verified": passed,
        "cached_heuristic_used_as_safety_authority": False,
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
        "campaign_id": domains.extension_content_id_v109(
            domains.CONSTRUCTION_K7_DEPENDENCY_REVALIDATED_QUOTIENT_CAMPAIGN_V109_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_dependency_revalidated_quotient_campaign_document_v109",
    "build_dependency_revalidated_quotient_occurrence_v109",
)
