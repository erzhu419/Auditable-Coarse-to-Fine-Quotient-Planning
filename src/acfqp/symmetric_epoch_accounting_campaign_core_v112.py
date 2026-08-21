"""Symmetric identity-check accounting over the unchanged V111 algorithm."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v112 as domains
from acfqp import identity_short_circuited_epoch_campaign_core_v111 as previous
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)


def build_symmetric_epoch_accounting_occurrence_v112(
    config: Mapping[str, Any],
    *,
    family: str,
    seed: int,
    episode_indices: tuple[int, ...],
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    raw = previous.build_identity_short_circuited_epoch_occurrence_v111(
        config,
        family=family,
        seed=seed,
        episode_indices=episode_indices,
        factor_library=factor_library,
    )
    accounting = copy.deepcopy(raw["accounting"])
    symmetric_full_diff = (
        accounting["full_diff_dependency_maintenance_events"]
        + accounting["model_epoch_identity_checks"]
    )
    accounting.update(
        fully_accounted_full_diff_identity_checks=accounting[
            "model_epoch_identity_checks"
        ],
        fully_accounted_full_diff_dependency_maintenance_events=symmetric_full_diff,
        maintenance_events_avoided_against_fully_accounted_full_diff=(
            symmetric_full_diff
            - accounting["identity_short_dependency_maintenance_events"]
        ),
        v110_full_diff_baseline_omitted_identity_checks=True,
        symmetric_matched_accounting_applied=True,
    )
    old_gate = raw["registered_gate"]
    gate = {
        "identity_short_full_diff_per_hit_and_no_cache_execution_equal": old_gate[
            "identity_short_full_diff_per_hit_and_no_cache_execution_equal"
        ],
        "all_reuse_arms_new_planning_compute_equal": old_gate[
            "all_reuse_arms_new_planning_compute_equal"
        ],
        "identity_short_new_planning_compute_strictly_below_no_cache": old_gate[
            "identity_short_new_planning_compute_strictly_below_no_cache"
        ],
        "identity_short_dependency_maintenance_strictly_below_per_hit_validation": old_gate[
            "identity_short_dependency_maintenance_strictly_below_per_hit_validation"
        ],
        "identity_short_dependency_maintenance_not_above_symmetrically_accounted_full_diff": accounting[
            "identity_short_dependency_maintenance_events"
        ]
        <= symmetric_full_diff,
        "epoch_authorized_cache_hit_observed": old_gate[
            "epoch_authorized_cache_hit_observed"
        ],
        "per_hit_dependency_rescan_count_is_zero": old_gate[
            "per_hit_dependency_rescan_count_is_zero"
        ],
        "quotient_model_orders_at_least_three_quarters": old_gate[
            "quotient_model_orders_at_least_three_quarters"
        ],
        "chosen_action_matches_quotient_strict_majority": old_gate[
            "chosen_action_matches_quotient_strict_majority"
        ],
        "certificate_failure_only_query_discipline_clean": old_gate[
            "certificate_failure_only_query_discipline_clean"
        ],
        "later_zero_label_quotient_reuse_observed": old_gate[
            "later_zero_label_quotient_reuse_observed"
        ],
        "quotient_lifetime_labels_strictly_below_cold_direct": old_gate[
            "quotient_lifetime_labels_strictly_below_cold_direct"
        ],
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.symmetric_epoch_accounting_occurrence.v112",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "v111_raw_occurrence": raw,
        "v111_raw_occurrence_id": raw["occurrence_id"],
        "accounting": accounting,
        "registered_gate": gate,
        "symmetric_accounting_preserves_actions_labels_steps_and_algorithm": gate[
            "passed"
        ],
        "local_ground_distinctions_only_after_certificate_failure_verified": gate[
            "passed"
        ],
        "algorithm_or_outcome_changed_from_embedded_v111_occurrence": False,
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
        "occurrence_id": domains.extension_content_id_v112(
            domains.CONSTRUCTION_K7_SYMMETRIC_EPOCH_ACCOUNTING_OCCURRENCE_V112_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_symmetric_epoch_accounting_occurrence_v112(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        factor_library=args[4],
    )


def build_symmetric_epoch_accounting_campaign_document_v112(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v111_campaign_id: str,
    v111_verification_id: str,
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
        and numeric["identity_short_dependency_maintenance_events"]
        < numeric["fully_accounted_full_diff_dependency_maintenance_events"]
        and numeric["identity_short_dependency_maintenance_events"]
        < numeric["per_hit_dependency_validation_checks"]
        and numeric["identity_short_circuit_count"] > 0
        and numeric["identity_short_quotient_lifetime_target_labels"]
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
        "every_occurrence_exactly_matches_all_baselines": all(
            row["registered_gate"][
                "identity_short_full_diff_per_hit_and_no_cache_execution_equal"
            ]
            for row in occurrences
        ),
        "every_occurrence_maintenance_below_per_hit_validation": all(
            row["registered_gate"][
                "identity_short_dependency_maintenance_strictly_below_per_hit_validation"
            ]
            for row in occurrences
        ),
        "every_occurrence_not_above_symmetrically_accounted_full_diff": all(
            row["registered_gate"][
                "identity_short_dependency_maintenance_not_above_symmetrically_accounted_full_diff"
            ]
            for row in occurrences
        ),
        "aggregate_maintenance_strictly_below_symmetrically_accounted_full_diff": numeric[
            "identity_short_dependency_maintenance_events"
        ]
        < numeric["fully_accounted_full_diff_dependency_maintenance_events"],
        "identity_short_circuit_observed": numeric["identity_short_circuit_count"]
        > 0,
        "aggregate_quotient_labels_strictly_below_cold_direct": numeric[
            "identity_short_quotient_lifetime_target_labels"
        ]
        < numeric["cold_direct_lifetime_target_labels"],
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    payload = {
        "schema": "acfqp.symmetric_epoch_accounting_campaign.v112",
        "preregistration_id": preregistration_id,
        "v111_failed_campaign_id": v111_campaign_id,
        "v111_failed_verification_id": v111_verification_id,
        "target_occurrences": occurrences,
        "incompatible_schema_no_transfer_control": ood,
        "accounting": {
            **numeric,
            "offline_source_labels_not_recharged": True,
            "sample_labels_execution_steps_planning_and_all_maintenance_axes_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": gate,
        "registered_symmetric_epoch_accounting_verified": passed,
        "ground_distinctions_acquired_only_after_certificate_failure_verified": passed,
        "algorithm_or_outcome_changed_by_v112_accounting_successor": False,
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
        "campaign_id": domains.extension_content_id_v112(
            domains.CONSTRUCTION_K7_SYMMETRIC_EPOCH_ACCOUNTING_CAMPAIGN_V112_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_symmetric_epoch_accounting_campaign_document_v112",
    "build_symmetric_epoch_accounting_occurrence_v112",
)
