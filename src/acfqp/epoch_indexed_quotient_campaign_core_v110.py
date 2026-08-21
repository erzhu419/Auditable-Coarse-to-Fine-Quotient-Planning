"""Matched epoch-indexed, per-hit V109, and no-cache campaign V110."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v110 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp import dependency_revalidated_quotient_campaign_core_v109 as v109_core
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
from acfqp.generic_epoch_indexed_quotient_sequence_v110 import (
    run_epoch_indexed_quotient_sequence_v110,
)
from acfqp.generic_persistent_legality_conditioned_quotient_sequence_v106 import (
    run_persistent_legality_conditioned_quotient_sequence_v106,
)
from acfqp.generic_persistent_multi_residual_sequence_v96 import (
    run_strict_cold_direct_sequence_v96,
)


def build_epoch_indexed_quotient_occurrence_v110(
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
    indexed = run_epoch_indexed_quotient_sequence_v110(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        **common,
    )
    per_hit = run_dependency_revalidated_quotient_sequence_v109(
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
    utilization = v109_core._utilization(indexed)  # noqa: SLF001
    actions = [row["action_keys"] for row in indexed["episodes"]]
    bases = [row["abstract_execution_receipts"] for row in indexed["episodes"]]
    exact_equivalence = (
        actions == [row["action_keys"] for row in per_hit["episodes"]]
        == [row["action_keys"] for row in no_cache["episodes"]]
        and bases
        == [row["abstract_execution_receipts"] for row in per_hit["episodes"]]
        == [row["abstract_execution_receipts"] for row in no_cache["episodes"]]
        and indexed["lifetime_target_ground_support_labels"]
        == per_hit["lifetime_target_ground_support_labels"]
        == no_cache["lifetime_target_ground_support_labels"]
        and indexed["execution_step_count"]
        == per_hit["execution_step_count"]
        == no_cache["execution_step_count"]
    )
    indexed_compute = indexed["actual_new_abstract_planning_compute_events"]
    per_hit_compute = per_hit["actual_new_abstract_planning_compute_events"]
    no_cache_compute = sum(
        row["abstract_planning_compute_events"] for row in no_cache["episodes"]
    )
    indexed_maintenance = (
        indexed["model_epoch_diff_checks"]
        + indexed["reverse_dependency_index_lookups"]
    )
    per_hit_validation = per_hit["dependency_validation_checks"]
    quotient_labels = indexed["lifetime_target_ground_support_labels"]
    direct_labels = direct["lifetime_target_ground_support_labels"]
    later_zero = any(
        row["episode_index"] != episode_indices[0]
        and row["new_certificate_labels_charged_this_episode"] == 0
        and row["quotient_proposal_admitted_execution_count"] > 0
        for row in indexed["episodes"]
    )
    gate = {
        "indexed_per_hit_and_no_cache_actions_base_receipts_labels_and_steps_equal": exact_equivalence,
        "indexed_and_per_hit_new_planning_compute_equal": indexed_compute
        == per_hit_compute,
        "indexed_new_planning_compute_strictly_below_no_cache": indexed_compute
        < no_cache_compute,
        "epoch_indexed_dependency_maintenance_strictly_below_per_hit_validation": indexed_maintenance
        < per_hit_validation,
        "epoch_authorized_cache_hit_observed": indexed[
            "epoch_authorized_cache_hit_count"
        ]
        > 0,
        "per_hit_dependency_rescan_count_is_zero": indexed[
            "per_hit_dependency_validation_checks"
        ]
        == 0,
        "quotient_model_orders_at_least_three_quarters": utilization[
            "quotient_actually_orders_at_least_three_quarters_of_execution"
        ],
        "chosen_action_matches_quotient_strict_majority": utilization[
            "chosen_action_matches_quotient_strict_majority"
        ],
        "certificate_failure_only_query_discipline_clean": indexed[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "later_zero_label_quotient_reuse_observed": later_zero,
        "quotient_lifetime_labels_strictly_below_cold_direct": quotient_labels
        < direct_labels,
    }
    gate["passed"] = all(gate.values())
    accounting = {
        "initial_acquisition_labels": indexed[
            "initial_acquisition_ground_support_labels_paid_once"
        ],
        "certificate_local_labels": indexed[
            "certificate_ground_support_labels_paid_once"
        ],
        "epoch_indexed_quotient_lifetime_target_labels": quotient_labels,
        "per_hit_quotient_lifetime_target_labels": per_hit[
            "lifetime_target_ground_support_labels"
        ],
        "no_cache_quotient_lifetime_target_labels": no_cache[
            "lifetime_target_ground_support_labels"
        ],
        "cold_direct_lifetime_target_labels": direct_labels,
        "target_label_reduction_against_cold_direct": direct_labels - quotient_labels,
        "execution_steps": indexed["execution_step_count"],
        "epoch_indexed_new_planning_compute_events": indexed_compute,
        "per_hit_new_planning_compute_events": per_hit_compute,
        "no_cache_planning_compute_events": no_cache_compute,
        "planning_compute_events_avoided_against_no_cache": no_cache_compute
        - indexed_compute,
        "model_epoch_diff_checks": indexed["model_epoch_diff_checks"],
        "reverse_dependency_index_lookups": indexed[
            "reverse_dependency_index_lookups"
        ],
        "epoch_indexed_dependency_maintenance_events": indexed_maintenance,
        "per_hit_dependency_validation_checks": per_hit_validation,
        "dependency_maintenance_events_avoided": per_hit_validation
        - indexed_maintenance,
        "sample_labels_execution_steps_planning_and_both_validation_axes_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.epoch_indexed_quotient_occurrence.v110",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "complete_anonymous_action_catalogue_receipt": catalogue_receipt,
        "partial_acquisition": acquisition["document"],
        "persistent_epoch_indexed_quotient_sequence": indexed,
        "matched_per_hit_dependency_revalidated_sequence": per_hit,
        "matched_no_cache_legality_quotient_sequence": no_cache,
        "strict_cold_direct_sequence": direct,
        "legality_conditioned_quotient_utilization": utilization,
        "accounting": accounting,
        "registered_gate": gate,
        "epoch_indexed_invalidation_preserves_actions_labels_and_steps": gate[
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
        "occurrence_id": domains.extension_content_id_v110(
            domains.CONSTRUCTION_K7_EPOCH_INDEXED_QUOTIENT_OCCURRENCE_V110_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_epoch_indexed_quotient_occurrence_v110(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        factor_library=args[4],
    )


def build_epoch_indexed_quotient_campaign_document_v110(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v109_campaign_id: str,
    v109_verification_id: str,
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
    keys = tuple(occurrences[0]["accounting"])
    numeric = {
        key: sum(row["accounting"][key] for row in occurrences)
        for key in keys
        if type(occurrences[0]["accounting"][key]) is int
    }
    ood = incompatible_schema_no_transfer_control_v99()
    passed = (
        all(row["registered_gate"]["passed"] for row in occurrences)
        and numeric["epoch_indexed_dependency_maintenance_events"]
        < numeric["per_hit_dependency_validation_checks"]
        and numeric["epoch_indexed_quotient_lifetime_target_labels"]
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
        "every_occurrence_exactly_matches_per_hit_and_no_cache_execution": all(
            row["registered_gate"][
                "indexed_per_hit_and_no_cache_actions_base_receipts_labels_and_steps_equal"
            ]
            for row in occurrences
        ),
        "every_occurrence_dependency_maintenance_strictly_reduced": all(
            row["registered_gate"][
                "epoch_indexed_dependency_maintenance_strictly_below_per_hit_validation"
            ]
            for row in occurrences
        ),
        "aggregate_quotient_labels_strictly_below_cold_direct": numeric[
            "epoch_indexed_quotient_lifetime_target_labels"
        ]
        < numeric["cold_direct_lifetime_target_labels"],
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    payload = {
        "schema": "acfqp.epoch_indexed_quotient_campaign.v110",
        "preregistration_id": preregistration_id,
        "v109_campaign_id": v109_campaign_id,
        "v109_verification_id": v109_verification_id,
        "target_occurrences": occurrences,
        "incompatible_schema_no_transfer_control": ood,
        "accounting": {
            **numeric,
            "offline_source_labels_not_recharged": True,
            "sample_labels_execution_steps_planning_and_both_validation_axes_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": gate,
        "registered_epoch_indexed_dependency_invalidation_verified": passed,
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
        "campaign_id": domains.extension_content_id_v110(
            domains.CONSTRUCTION_K7_EPOCH_INDEXED_QUOTIENT_CAMPAIGN_V110_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_epoch_indexed_quotient_campaign_document_v110",
    "build_epoch_indexed_quotient_occurrence_v110",
)
