"""Campaign whose utilization evidence is rebuilt from per-action receipts."""

from __future__ import annotations
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping
from acfqp import construction_k7_domain_registry_extension_v103 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import incompatible_schema_no_transfer_control_v99
from acfqp.generic_abstract_execution_receipt_v103 import verify_abstract_execution_receipt_v103
from acfqp.generic_persistent_receipted_sequence_v103 import run_persistent_receipted_arm_v103
from acfqp.generic_persistent_multi_residual_sequence_v96 import run_strict_cold_direct_sequence_v96


def derive_receipted_utilization_v103(sequence: Mapping[str, Any]) -> dict[str, Any]:
    receipts = sequence["all_abstract_execution_receipts"]
    verified = [verify_abstract_execution_receipt_v103(row) for row in receipts]
    indices = [row["decision_index"] for row in verified]
    episode_lengths = [sequence["first_agreement_shielded_online_episode"]["execution_steps"], *[row["execution_steps"] for row in sequence["later_persistent_episodes"]]]
    expected_indices = [index for length in episode_lengths for index in range(length)]
    matches = sum(row["chosen_action_matches_admitted_abstract_proposal"] for row in verified)
    if indices != expected_indices or len(verified) != sum(episode_lengths): raise ValueError("V103 execution receipt coverage changed")
    return {
        "schema": "acfqp.receipted_abstract_execution_utilization.v103",
        "execution_receipt_count": len(verified),
        "execution_step_count": sum(episode_lengths),
        "admitted_abstract_execution_match_count": matches,
        "abstract_execution_match_fraction_numerator": matches,
        "abstract_execution_match_fraction_denominator": len(verified),
        "strict_majority_of_executed_actions_match_admitted_abstract_proposal": 2 * matches > len(verified),
        "every_execution_action_independently_receipted": True,
        "receipt_replay_uses_no_producer_summary_count": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }


def build_receipted_utilization_occurrence_v103(config: Mapping[str, Any], *, family: str, seed: int, episode_indices: tuple[int, ...], factor_library: Mapping[str, Any], residual_library: Mapping[str, Any], structural_prior_library: Mapping[str, Any]) -> dict[str, Any]:
    adapter = base.predecessor.predecessor.prior_ground._adapter(family, seed, config)  # noqa: SLF001
    partial = base.acquire_matched_true_bit_models_v59(adapter, factor_library, config)["ANONYMOUS_FACTOR_PRIOR_ON"]
    common = dict(residual_prior_library=residual_library, episode_indices=episode_indices, maximum_abstract_depth=config["maximum_abstract_depth"], maximum_execution_steps=config["maximum_execution_steps"], confidence_denominator=config["residual_confidence_denominator"], maximum_support_branch_evaluations=config["maximum_joint_support_branch_evaluations"], support_feasible_beam_width=config["joint_support_feasible_beam_width"], maximum_incremental_certificate_ground_support_labels=100_000)
    meta = run_persistent_receipted_arm_v103(adapter, partial["candidate"], partial["rows"], partial["document"]["ground_support_labels"], structural_prior_library=structural_prior_library, **common)
    no_prior = run_persistent_receipted_arm_v103(adapter, partial["candidate"], partial["rows"], partial["document"]["ground_support_labels"], structural_prior_library=None, **common)
    direct = run_strict_cold_direct_sequence_v96(adapter, partial["candidate"], episode_indices=episode_indices, maximum_execution_steps=config["maximum_execution_steps"], maximum_incremental_certificate_ground_support_labels=100_000)
    meta_u = derive_receipted_utilization_v103(meta); no_u = derive_receipted_utilization_v103(no_prior)
    accepts = meta["first_agreement_shielded_online_episode"]["agreement_shield_accept_count"] + meta["later_agreement_shield_accept_receipt_count"]
    disagreements = meta["first_agreement_shielded_online_episode"]["agreement_shield_disagreement_abstention_count"] + meta["later_agreement_shield_disagreement_abstention_count"]
    meta_activation = meta["target_model_activation_ground_support_labels_with_right_censoring"]; no_activation = no_prior["target_model_activation_ground_support_labels_with_right_censoring"]
    gate = {"every_execution_action_independently_receipted": meta_u["every_execution_action_independently_receipted"], "abstract_ordering_matches_strict_majority_of_executed_actions": meta_u["strict_majority_of_executed_actions_match_admitted_abstract_proposal"], "abstract_execution_match_rate_noninferior_to_no_prior": meta_u["abstract_execution_match_fraction_numerator"] * no_u["abstract_execution_match_fraction_denominator"] >= no_u["abstract_execution_match_fraction_numerator"] * meta_u["abstract_execution_match_fraction_denominator"], "abstract_accept_path_observed": accepts > 0, "model_activation_strictly_earlier_than_no_prior": meta_activation < no_activation, "meta_task_labels_noninferior_to_no_prior": meta["lifetime_target_ground_support_labels"] <= no_prior["lifetime_target_ground_support_labels"], "meta_task_labels_strictly_below_cold_direct": meta["lifetime_target_ground_support_labels"] < direct["lifetime_target_ground_support_labels"], "certificate_failure_only_query_discipline_clean": meta["every_new_ground_query_followed_a_failed_certificate"] and no_prior["every_new_ground_query_followed_a_failed_certificate"]}; gate["passed"] = all(gate.values())
    payload = {"schema": "acfqp.receipted_abstract_utilization_occurrence.v103", "target_family": family, "seed": seed, "episode_indices": list(episode_indices), "common_partial_acquisition": partial["document"], "meta_prior_persistent_receipted_sequence": meta, "no_prior_persistent_receipted_sequence": no_prior, "strict_cold_direct_sequence": direct, "meta_prior_receipted_utilization": meta_u, "no_prior_receipted_utilization": no_u, "accept_count_for_family_aggregation": accepts, "disagreement_count_for_family_aggregation": disagreements, "accounting": {"meta_activation_labels": meta_activation, "no_prior_activation_labels": no_activation, "meta_target_labels": meta["lifetime_target_ground_support_labels"], "no_prior_target_labels": no_prior["lifetime_target_ground_support_labels"], "direct_target_labels": direct["lifetime_target_ground_support_labels"], "sample_labels_execution_steps_derivation_shield_and_planning_compute_separate": True, "scalar_cost_aggregation_performed": False}, "registered_gate": gate, "complete_world_model_synthesized": False, "official_execution_allowed": False, "official_scalar_cost": None, "official_N_break_even": None, "WORKLOAD_ECONOMICS_GATE": "NOT_RUN", "COUNTER_COMPLETENESS_GATE": "NOT_RUN"}
    return {**payload, "occurrence_id": domains.extension_content_id_v103(domains.CONSTRUCTION_K7_RECEIPTED_UTILIZATION_OCCURRENCE_V103_DOMAIN, payload)}


def _target(args: tuple[Any, ...]) -> dict[str, Any]: return build_receipted_utilization_occurrence_v103(args[0], family=args[1], seed=args[2], episode_indices=args[3], factor_library=args[4], residual_library=args[5], structural_prior_library=args[6])


def build_receipted_utilization_campaign_document_v103(config: Mapping[str, Any], *, preregistration_id: str, v102_campaign_id: str, v102_verification_id: str, source_library_artifact_id: str, factor_library: Mapping[str, Any], residual_library: Mapping[str, Any], structural_prior_library: Mapping[str, Any]) -> dict[str, Any]:
    args = [(config, row["family"], row["seed"], tuple(config["target_episode_indices"]), factor_library, residual_library, structural_prior_library) for row in config["target_occurrences"]]
    with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor: occurrences = list(executor.map(_target, args))
    totals = {key: sum(row["accounting"][field] for row in occurrences) for key, field in (("meta_activation", "meta_activation_labels"), ("no_prior_activation", "no_prior_activation_labels"), ("meta_labels", "meta_target_labels"), ("no_prior_labels", "no_prior_target_labels"), ("direct_labels", "direct_target_labels"))}
    matches = sum(row["meta_prior_receipted_utilization"]["admitted_abstract_execution_match_count"] for row in occurrences); steps = sum(row["meta_prior_receipted_utilization"]["execution_step_count"] for row in occurrences)
    family_coverage = []
    for family in sorted(config["required_target_families"]):
        rows = [row for row in occurrences if row["target_family"] == family]; a = sum(row["accept_count_for_family_aggregation"] for row in rows); d = sum(row["disagreement_count_for_family_aggregation"] for row in rows); family_coverage.append({"target_family": family, "occurrence_count": len(rows), "accept_count": a, "disagreement_abstention_count": d, "both_shield_paths_observed_across_family": a > 0 and d > 0})
    ood = incompatible_schema_no_transfer_control_v99(); passed = all(row["registered_gate"]["passed"] for row in occurrences) and all(row["both_shield_paths_observed_across_family"] for row in family_coverage) and 2 * matches > steps and totals["meta_activation"] < totals["no_prior_activation"] and totals["meta_labels"] <= totals["no_prior_labels"] and totals["meta_labels"] < totals["direct_labels"] and ood["strict_ood_no_transfer"] is True
    payload = {"schema": "acfqp.receipted_abstract_utilization_campaign.v103", "preregistration_id": preregistration_id, "v102_campaign_id": v102_campaign_id, "v102_verification_id": v102_verification_id, "source_library_artifact_id": source_library_artifact_id, "target_occurrences": occurrences, "family_wide_shield_path_coverage": family_coverage, "incompatible_schema_no_transfer_control": ood, "accounting": {**totals, "meta_receipted_abstract_execution_match_count": matches, "meta_execution_step_count": steps, "offline_source_labels_not_recharged": True, "sample_labels_execution_steps_derivation_shield_and_planning_compute_separate": True, "scalar_cost_aggregation_performed": False}, "registered_gate": {"required_target_occurrence_count": config["required_target_occurrence_count"], "passed_target_occurrence_count": sum(row["registered_gate"]["passed"] is True for row in occurrences), "every_occurrence_abstract_orders_strict_majority_of_executed_actions_from_receipts": all(row["registered_gate"]["abstract_ordering_matches_strict_majority_of_executed_actions"] for row in occurrences), "every_target_family_exercises_both_shield_paths": all(row["both_shield_paths_observed_across_family"] for row in family_coverage), "aggregate_activation_sample_tax_strictly_reduced": totals["meta_activation"] < totals["no_prior_activation"], "aggregate_negative_transfer_absent": totals["meta_labels"] <= totals["no_prior_labels"], "aggregate_meta_labels_strictly_below_cold_direct": totals["meta_labels"] < totals["direct_labels"], "strict_incompatible_schema_no_transfer_verified": ood["strict_ood_no_transfer"], "passed": passed}, "registered_multistep_execution_primarily_abstract_ordered_verified": passed, "ground_distinctions_acquired_only_after_certificate_failure_verified": passed, "complete_world_model_synthesized": False, "global_exact_dynamics_claimed": False, "arbitrary_domain_transfer_claimed": False, "official_execution_allowed": False, "official_scalar_cost": None, "official_N_break_even": None, "WORKLOAD_ECONOMICS_GATE": "NOT_RUN", "COUNTER_COMPLETENESS_GATE": "NOT_RUN"}
    return {**payload, "campaign_id": domains.extension_content_id_v103(domains.CONSTRUCTION_K7_RECEIPTED_UTILIZATION_CAMPAIGN_V103_DOMAIN, payload)}


__all__ = ("build_receipted_utilization_campaign_document_v103", "build_receipted_utilization_occurrence_v103", "derive_receipted_utilization_v103")
