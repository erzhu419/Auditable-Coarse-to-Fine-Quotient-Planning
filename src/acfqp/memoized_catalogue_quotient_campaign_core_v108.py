"""Matched memoized/no-cache quotient planning-compute campaign V108."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v108 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_complete_anonymous_action_catalogue_receipt_v107 import (
    build_complete_anonymous_action_catalogue_receipt_v107,
    verify_complete_anonymous_action_catalogue_receipt_v107,
)
from acfqp.generic_persistent_legality_conditioned_quotient_sequence_v106 import (
    run_persistent_legality_conditioned_quotient_sequence_v106,
)
from acfqp.generic_persistent_memoized_catalogue_quotient_sequence_v108 import (
    run_persistent_memoized_catalogue_quotient_sequence_v108,
)
from acfqp.generic_persistent_multi_residual_sequence_v96 import (
    run_strict_cold_direct_sequence_v96,
)
from acfqp.legality_conditioned_quotient_campaign_core_v106 import (
    derive_legality_conditioned_utilization_v106,
)


def build_memoized_catalogue_quotient_occurrence_v108(
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
    memoized = run_persistent_memoized_catalogue_quotient_sequence_v108(
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
    utilization = derive_legality_conditioned_utilization_v106(memoized)
    same_actions = [row["action_keys"] for row in memoized["episodes"]] == [
        row["action_keys"] for row in no_cache["episodes"]
    ]
    same_receipts = memoized[
        "all_actual_legality_conditioned_execution_receipts"
    ] == no_cache["all_actual_legality_conditioned_execution_receipts"]
    same_labels = memoized["lifetime_target_ground_support_labels"] == no_cache[
        "lifetime_target_ground_support_labels"
    ]
    actual_compute = memoized["actual_new_abstract_planning_compute_events"]
    baseline_compute = sum(
        row["abstract_planning_compute_events"] for row in no_cache["episodes"]
    )
    quotient_labels = memoized["lifetime_target_ground_support_labels"]
    direct_labels = direct["lifetime_target_ground_support_labels"]
    later_zero_label_reuse = any(
        row["episode_index"] != episode_indices[0]
        and row["new_certificate_labels_charged_this_episode"] == 0
        and row["quotient_proposal_admitted_execution_count"] > 0
        for row in memoized["episodes"]
    )
    gate = {
        "memoized_and_no_cache_action_sequences_exactly_match": same_actions,
        "memoized_and_no_cache_per_action_receipts_exactly_match": same_receipts,
        "memoized_and_no_cache_target_labels_exactly_match": same_labels,
        "memoized_actual_planning_compute_strictly_below_no_cache": actual_compute
        < baseline_compute,
        "memoized_cache_hit_observed": memoized["memoized_plan_cache_hit_count"]
        > 0,
        "quotient_model_orders_at_least_three_quarters": utilization[
            "quotient_actually_orders_at_least_three_quarters_of_execution"
        ],
        "chosen_action_matches_quotient_strict_majority": utilization[
            "chosen_action_matches_quotient_strict_majority"
        ],
        "certificate_failure_only_query_discipline_clean": memoized[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "later_zero_label_quotient_reuse_observed": later_zero_label_reuse,
        "quotient_lifetime_labels_strictly_below_cold_direct": quotient_labels
        < direct_labels,
    }
    gate["passed"] = all(gate.values())
    accounting = {
        "initial_acquisition_labels": memoized[
            "initial_acquisition_ground_support_labels_paid_once"
        ],
        "certificate_local_labels": memoized[
            "certificate_ground_support_labels_paid_once"
        ],
        "memoized_quotient_lifetime_target_labels": quotient_labels,
        "matched_no_cache_quotient_lifetime_target_labels": no_cache[
            "lifetime_target_ground_support_labels"
        ],
        "cold_direct_lifetime_target_labels": direct_labels,
        "target_label_reduction_against_cold_direct": direct_labels
        - quotient_labels,
        "execution_steps": utilization["execution_step_count"],
        "memoized_actual_new_planning_compute_events": actual_compute,
        "matched_no_cache_planning_compute_events": baseline_compute,
        "planning_compute_events_avoided": baseline_compute - actual_compute,
        "sample_labels_execution_steps_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.memoized_catalogue_quotient_occurrence.v108",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "complete_anonymous_action_catalogue_receipt": catalogue_receipt,
        "partial_acquisition": acquisition["document"],
        "persistent_memoized_catalogue_quotient_sequence": memoized,
        "matched_no_cache_legality_quotient_sequence": no_cache,
        "strict_cold_direct_sequence": direct,
        "legality_conditioned_quotient_utilization": utilization,
        "accounting": accounting,
        "registered_gate": gate,
        "identity_bound_memoization_preserves_actions_and_labels": gate["passed"],
        "local_ground_distinctions_only_after_certificate_failure_verified": gate[
            "passed"
        ],
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
        "occurrence_id": domains.extension_content_id_v108(
            domains.CONSTRUCTION_K7_MEMOIZED_CATALOGUE_QUOTIENT_OCCURRENCE_V108_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_memoized_catalogue_quotient_occurrence_v108(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        factor_library=args[4],
    )


def build_memoized_catalogue_quotient_campaign_document_v108(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v107_campaign_id: str,
    v107_verification_id: str,
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
    totals = {
        key: sum(row["accounting"][key] for row in occurrences)
        for key in (
            "initial_acquisition_labels",
            "certificate_local_labels",
            "memoized_quotient_lifetime_target_labels",
            "matched_no_cache_quotient_lifetime_target_labels",
            "cold_direct_lifetime_target_labels",
            "target_label_reduction_against_cold_direct",
            "execution_steps",
            "memoized_actual_new_planning_compute_events",
            "matched_no_cache_planning_compute_events",
            "planning_compute_events_avoided",
        )
    }
    ood = incompatible_schema_no_transfer_control_v99()
    passed = (
        all(row["registered_gate"]["passed"] for row in occurrences)
        and totals["memoized_actual_new_planning_compute_events"]
        < totals["matched_no_cache_planning_compute_events"]
        and totals["memoized_quotient_lifetime_target_labels"]
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
        "every_occurrence_action_and_receipt_equivalent_to_no_cache": all(
            row["registered_gate"][
                "memoized_and_no_cache_action_sequences_exactly_match"
            ]
            and row["registered_gate"][
                "memoized_and_no_cache_per_action_receipts_exactly_match"
            ]
            for row in occurrences
        ),
        "every_occurrence_planning_compute_strictly_reduced": all(
            row["registered_gate"][
                "memoized_actual_planning_compute_strictly_below_no_cache"
            ]
            for row in occurrences
        ),
        "aggregate_sample_labels_unchanged_by_memoization": totals[
            "memoized_quotient_lifetime_target_labels"
        ]
        == totals["matched_no_cache_quotient_lifetime_target_labels"],
        "aggregate_quotient_labels_strictly_below_cold_direct": totals[
            "memoized_quotient_lifetime_target_labels"
        ]
        < totals["cold_direct_lifetime_target_labels"],
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    payload = {
        "schema": "acfqp.memoized_catalogue_quotient_campaign.v108",
        "preregistration_id": preregistration_id,
        "v107_campaign_id": v107_campaign_id,
        "v107_verification_id": v107_verification_id,
        "target_occurrences": occurrences,
        "incompatible_schema_no_transfer_control": ood,
        "accounting": {
            **totals,
            "offline_source_labels_not_recharged": True,
            "sample_labels_execution_steps_and_planning_compute_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": gate,
        "registered_identity_bound_quotient_memoization_verified": passed,
        "ground_distinctions_acquired_only_after_certificate_failure_verified": passed,
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
        "campaign_id": domains.extension_content_id_v108(
            domains.CONSTRUCTION_K7_MEMOIZED_CATALOGUE_QUOTIENT_CAMPAIGN_V108_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_memoized_catalogue_quotient_campaign_document_v108",
    "build_memoized_catalogue_quotient_occurrence_v108",
)
