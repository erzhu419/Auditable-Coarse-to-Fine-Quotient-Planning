"""Family-wide shield opportunity coverage with per-occurrence utilization."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v102 as domains
from acfqp.abstract_execution_utilization_campaign_core_v101 import (
    build_abstract_execution_utilization_occurrence_v101,
)
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)


def build_family_wide_utilization_occurrence_v102(
    config: Mapping[str, Any],
    *, family: str, seed: int, episode_indices: tuple[int, ...],
    factor_library: Mapping[str, Any], residual_library: Mapping[str, Any],
    structural_prior_library: Mapping[str, Any],
) -> dict[str, Any]:
    observation = build_abstract_execution_utilization_occurrence_v101(
        config, family=family, seed=seed, episode_indices=episode_indices,
        factor_library=factor_library, residual_library=residual_library,
        structural_prior_library=structural_prior_library,
    )
    predecessor = observation["frozen_v100_sequence_wide_observation"]
    algorithm = predecessor["frozen_v99_algorithm_observation"]
    meta = algorithm["meta_prior_persistent_sequence"]
    no_prior = algorithm["no_structure_prior_persistent_sequence"]
    utilization = observation["meta_prior_abstract_execution_utilization"]
    no_utilization = observation["no_prior_abstract_execution_utilization"]
    coverage = predecessor["sequence_wide_path_coverage"]
    gate = {
        "abstract_ordering_matches_strict_majority_of_executed_actions": utilization["strict_majority_of_executed_actions_match_abstract_proposal"],
        "abstract_execution_match_rate_noninferior_to_no_prior": utilization["abstract_execution_match_fraction_numerator"] * no_utilization["abstract_execution_match_fraction_denominator"] >= no_utilization["abstract_execution_match_fraction_numerator"] * utilization["abstract_execution_match_fraction_denominator"],
        "abstract_accept_path_observed": coverage["accept_path_observed_somewhere_in_persistent_sequence"],
        "certificate_failure_only_query_discipline_clean": meta["every_new_ground_query_followed_a_failed_certificate"] and no_prior["every_new_ground_query_followed_a_failed_certificate"],
        "exact_overlay_exclusively_discharges_safety": meta["persistent_exact_overlay_exclusively_discharges_safety"] and no_prior["persistent_exact_overlay_exclusively_discharges_safety"],
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.family_wide_abstract_utilization_occurrence.v102",
        "target_family": family, "seed": seed, "episode_indices": list(episode_indices),
        "frozen_v101_measurement_observation": observation,
        "registered_gate": gate,
        "disagreement_path_required_per_occurrence": False,
        "disagreement_path_count_for_family_aggregation": coverage["persistent_sequence_disagreement_abstention_count"],
        "accept_path_count_for_family_aggregation": coverage["persistent_sequence_accept_count"],
        "algorithm_changed_from_v101": False,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False, "official_scalar_cost": None,
        "official_N_break_even": None, "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {**payload, "occurrence_id": domains.extension_content_id_v102(domains.CONSTRUCTION_K7_FAMILY_WIDE_UTILIZATION_OCCURRENCE_V102_DOMAIN, payload)}


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_family_wide_utilization_occurrence_v102(
        args[0], family=args[1], seed=args[2], episode_indices=args[3],
        factor_library=args[4], residual_library=args[5], structural_prior_library=args[6]
    )


def build_family_wide_utilization_campaign_document_v102(
    config: Mapping[str, Any], *, preregistration_id: str,
    v101_campaign_id: str, v101_verification_id: str,
    source_library_artifact_id: str, factor_library: Mapping[str, Any],
    residual_library: Mapping[str, Any], structural_prior_library: Mapping[str, Any],
) -> dict[str, Any]:
    args = [(config, row["family"], row["seed"], tuple(config["target_episode_indices"]), factor_library, residual_library, structural_prior_library) for row in config["target_occurrences"]]
    if config["target_worker_count"] == 1:
        occurrences = [_target(row) for row in args]
    else:
        with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
            occurrences = list(executor.map(_target, args))
    algorithms = [row["frozen_v101_measurement_observation"]["frozen_v100_sequence_wide_observation"]["frozen_v99_algorithm_observation"] for row in occurrences]
    totals = {key: sum(row["accounting"][field] for row in algorithms) for key, field in (
        ("meta_activation", "meta_model_activation_target_labels_with_right_censoring"),
        ("no_prior_activation", "no_prior_model_activation_target_labels_with_right_censoring"),
        ("meta_labels", "meta_lifetime_target_labels"), ("no_prior_labels", "no_prior_lifetime_target_labels"),
        ("direct_labels", "strict_cold_direct_lifetime_target_labels"),
    )}
    family_coverage = []
    for family in sorted(config["required_target_families"]):
        rows = [row for row in occurrences if row["target_family"] == family]
        accepts = sum(row["accept_path_count_for_family_aggregation"] for row in rows)
        disagreements = sum(row["disagreement_path_count_for_family_aggregation"] for row in rows)
        family_coverage.append({"target_family": family, "occurrence_count": len(rows), "accept_count": accepts, "disagreement_abstention_count": disagreements, "both_shield_paths_observed_across_family": accepts > 0 and disagreements > 0})
    matches = sum(row["frozen_v101_measurement_observation"]["meta_prior_abstract_execution_utilization"]["persistent_sequence_abstract_execution_match_count"] for row in occurrences)
    steps = sum(row["frozen_v101_measurement_observation"]["meta_prior_abstract_execution_utilization"]["persistent_sequence_execution_step_count"] for row in occurrences)
    ood = incompatible_schema_no_transfer_control_v99()
    passed = len(occurrences) == config["required_target_occurrence_count"] and all(row["registered_gate"]["passed"] for row in occurrences) and all(row["both_shield_paths_observed_across_family"] for row in family_coverage) and totals["meta_activation"] < totals["no_prior_activation"] and totals["meta_labels"] <= totals["no_prior_labels"] and totals["meta_labels"] < totals["direct_labels"] and 2 * matches > steps and ood["strict_ood_no_transfer"] is True
    payload = {
        "schema": "acfqp.family_wide_abstract_utilization_campaign.v102",
        "preregistration_id": preregistration_id, "v101_failed_campaign_id": v101_campaign_id,
        "v101_failure_verification_id": v101_verification_id, "source_library_artifact_id": source_library_artifact_id,
        "target_occurrences": occurrences, "family_wide_shield_path_coverage": family_coverage,
        "incompatible_schema_no_transfer_control": ood,
        "accounting": {**totals, "meta_abstract_execution_match_count": matches, "meta_execution_step_count": steps, "offline_source_labels_not_recharged": True, "sample_labels_execution_steps_derivation_shield_and_planning_compute_separate": True, "scalar_cost_aggregation_performed": False},
        "registered_gate": {"required_target_occurrence_count": config["required_target_occurrence_count"], "passed_target_occurrence_count": sum(row["registered_gate"]["passed"] is True for row in occurrences), "every_occurrence_abstract_orders_strict_majority_of_executed_actions": all(row["registered_gate"]["abstract_ordering_matches_strict_majority_of_executed_actions"] for row in occurrences), "every_target_family_exercises_both_shield_paths": all(row["both_shield_paths_observed_across_family"] for row in family_coverage), "aggregate_model_activation_sample_tax_strictly_reduced": totals["meta_activation"] < totals["no_prior_activation"], "aggregate_negative_transfer_absent": totals["meta_labels"] <= totals["no_prior_labels"], "aggregate_meta_labels_strictly_below_cold_direct": totals["meta_labels"] < totals["direct_labels"], "strict_incompatible_schema_no_transfer_verified": ood["strict_ood_no_transfer"], "passed": passed},
        "registered_multistep_execution_primarily_abstract_ordered_verified": passed,
        "ground_distinctions_acquired_only_after_certificate_failure_verified": passed,
        "complete_world_model_synthesized": False, "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False, "official_execution_allowed": False,
        "official_scalar_cost": None, "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN", "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {**payload, "campaign_id": domains.extension_content_id_v102(domains.CONSTRUCTION_K7_FAMILY_WIDE_UTILIZATION_CAMPAIGN_V102_DOMAIN, payload)}


__all__ = ("build_family_wide_utilization_campaign_document_v102", "build_family_wide_utilization_occurrence_v102")
