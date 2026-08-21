"""Campaign for full-or-explicit-partial abstract execution utilization."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v104 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_hierarchical_abstract_execution_receipt_v104 import (
    verify_hierarchical_abstract_execution_receipt_v104,
)
from acfqp.generic_persistent_hierarchical_receipted_sequence_v104 import (
    run_persistent_hierarchical_receipted_arm_v104,
)
from acfqp.generic_persistent_multi_residual_sequence_v96 import (
    run_strict_cold_direct_sequence_v96,
)


def derive_hierarchical_utilization_v104(
    sequence: Mapping[str, Any],
) -> dict[str, Any]:
    predecessor = sequence["v103_receipted_sequence"]
    episodes = [
        predecessor["first_agreement_shielded_online_episode"],
        *predecessor["later_persistent_episodes"],
    ]
    verified = [
        verify_hierarchical_abstract_execution_receipt_v104(row)
        for row in sequence["hierarchical_abstract_execution_receipts"]
    ]
    expected_pairs = [
        (episode["episode_index"], decision)
        for episode in episodes
        for decision in range(episode["execution_steps"])
    ]
    observed_pairs = [
        (row["episode_index"], row["decision_index"]) for row in verified
    ]
    if observed_pairs != expected_pairs or len(verified) != sum(
        episode["execution_steps"] for episode in episodes
    ):
        raise ValueError("V104 hierarchical receipt coverage changed")
    full = sum(
        row["abstract_ordering_source"] == "FULL_POST_DEPENDENCY_WORLD_MODEL"
        for row in verified
    )
    partial = sum(
        row["abstract_ordering_source"]
        == "COMPILED_PARTIAL_WORLD_MODEL_FALLBACK"
        for row in verified
    )
    exact = sum(
        row["abstract_ordering_source"] == "EXACT_CERTIFICATE_POLICY_ONLY"
        for row in verified
    )
    steps = len(verified)
    if (
        sequence["full_post_dependency_world_model_match_count"] != full
        or sequence["compiled_partial_world_model_fallback_match_count"] != partial
        or sequence["exact_certificate_policy_only_count"] != exact
        or sequence["abstract_model_ordered_execution_count"] != full + partial
        or full + partial + exact != steps
    ):
        raise ValueError("V104 hierarchical source accounting changed")
    return {
        "schema": "acfqp.hierarchical_abstract_execution_utilization.v104",
        "execution_receipt_count": steps,
        "execution_step_count": steps,
        "full_post_dependency_world_model_match_count": full,
        "compiled_partial_world_model_fallback_match_count": partial,
        "exact_certificate_policy_only_count": exact,
        "abstract_model_ordered_execution_count": full + partial,
        "abstract_model_ordered_fraction_numerator": full + partial,
        "abstract_model_ordered_fraction_denominator": steps,
        "strict_majority_of_executed_actions_ordered_by_full_or_explicit_partial_world_model": 2 * (full + partial) > steps,
        "full_world_model_match_is_not_inferred_from_partial_fallback": True,
        "partial_world_model_incompleteness_is_explicit": True,
        "every_execution_action_independently_receipted": True,
        "receipt_replay_uses_no_producer_summary_count": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }


def build_hierarchical_utilization_occurrence_v104(
    config: Mapping[str, Any],
    *,
    family: str,
    seed: int,
    episode_indices: tuple[int, ...],
    factor_library: Mapping[str, Any],
    residual_library: Mapping[str, Any],
    structural_prior_library: Mapping[str, Any],
) -> dict[str, Any]:
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        family, seed, config
    )
    partial = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    common = dict(
        residual_prior_library=residual_library,
        episode_indices=episode_indices,
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        confidence_denominator=config["residual_confidence_denominator"],
        maximum_support_branch_evaluations=config[
            "maximum_joint_support_branch_evaluations"
        ],
        support_feasible_beam_width=config["joint_support_feasible_beam_width"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    meta = run_persistent_hierarchical_receipted_arm_v104(
        adapter,
        partial["candidate"],
        partial["rows"],
        partial["document"]["ground_support_labels"],
        structural_prior_library=structural_prior_library,
        **common,
    )
    no_prior = run_persistent_hierarchical_receipted_arm_v104(
        adapter,
        partial["candidate"],
        partial["rows"],
        partial["document"]["ground_support_labels"],
        structural_prior_library=None,
        **common,
    )
    direct = run_strict_cold_direct_sequence_v96(
        adapter,
        partial["candidate"],
        episode_indices=episode_indices,
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    meta_u = derive_hierarchical_utilization_v104(meta)
    no_u = derive_hierarchical_utilization_v104(no_prior)
    meta_v103 = meta["v103_receipted_sequence"]
    no_v103 = no_prior["v103_receipted_sequence"]
    accepts = (
        meta_v103["first_agreement_shielded_online_episode"][
            "agreement_shield_accept_count"
        ]
        + meta_v103["later_agreement_shield_accept_receipt_count"]
    )
    disagreements = (
        meta_v103["first_agreement_shielded_online_episode"][
            "agreement_shield_disagreement_abstention_count"
        ]
        + meta_v103["later_agreement_shield_disagreement_abstention_count"]
    )
    meta_activation = meta_v103[
        "target_model_activation_ground_support_labels_with_right_censoring"
    ]
    no_activation = no_v103[
        "target_model_activation_ground_support_labels_with_right_censoring"
    ]
    meta_labels = meta_v103["lifetime_target_ground_support_labels"]
    no_labels = no_v103["lifetime_target_ground_support_labels"]
    direct_labels = direct["lifetime_target_ground_support_labels"]
    gate = {
        "every_execution_action_independently_receipted": meta_u[
            "every_execution_action_independently_receipted"
        ],
        "abstract_model_orders_strict_majority_of_executed_actions": meta_u[
            "strict_majority_of_executed_actions_ordered_by_full_or_explicit_partial_world_model"
        ],
        "abstract_ordering_rate_noninferior_to_no_prior": meta_u[
            "abstract_model_ordered_fraction_numerator"
        ]
        * no_u["abstract_model_ordered_fraction_denominator"]
        >= no_u["abstract_model_ordered_fraction_numerator"]
        * meta_u["abstract_model_ordered_fraction_denominator"],
        "full_and_partial_model_matches_kept_separate": meta_u[
            "full_world_model_match_is_not_inferred_from_partial_fallback"
        ],
        "partial_world_model_incompleteness_explicit": meta_u[
            "partial_world_model_incompleteness_is_explicit"
        ],
        "abstract_accept_path_observed": accepts > 0,
        "model_activation_strictly_earlier_than_no_prior": (
            meta_activation < no_activation
        ),
        "meta_task_labels_noninferior_to_no_prior": meta_labels <= no_labels,
        "meta_task_labels_strictly_below_cold_direct": meta_labels < direct_labels,
        "certificate_failure_only_query_discipline_clean": (
            meta_v103["every_new_ground_query_followed_a_failed_certificate"]
            and no_v103["every_new_ground_query_followed_a_failed_certificate"]
        ),
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.hierarchical_abstract_utilization_occurrence.v104",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "common_partial_acquisition": partial["document"],
        "meta_prior_hierarchical_sequence": meta,
        "no_prior_hierarchical_sequence": no_prior,
        "strict_cold_direct_sequence": direct,
        "meta_prior_hierarchical_utilization": meta_u,
        "no_prior_hierarchical_utilization": no_u,
        "accept_count_for_family_aggregation": accepts,
        "disagreement_count_for_family_aggregation": disagreements,
        "accounting": {
            "meta_activation_labels": meta_activation,
            "no_prior_activation_labels": no_activation,
            "meta_target_labels": meta_labels,
            "no_prior_target_labels": no_labels,
            "direct_target_labels": direct_labels,
            "sample_labels_execution_steps_derivation_shield_and_planning_compute_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": gate,
        "full_post_dependency_world_model_primary_ordering_verified": False,
        "partial_world_model_is_honest_incomplete_abstraction": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v104(
            domains.CONSTRUCTION_K7_HIERARCHICAL_UTILIZATION_OCCURRENCE_V104_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_hierarchical_utilization_occurrence_v104(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        factor_library=args[4],
        residual_library=args[5],
        structural_prior_library=args[6],
    )


def build_hierarchical_utilization_campaign_document_v104(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v103_campaign_id: str,
    v103_verification_id: str,
    source_library_artifact_id: str,
    factor_library: Mapping[str, Any],
    residual_library: Mapping[str, Any],
    structural_prior_library: Mapping[str, Any],
) -> dict[str, Any]:
    args = [
        (
            config,
            row["family"],
            row["seed"],
            tuple(config["target_episode_indices"]),
            factor_library,
            residual_library,
            structural_prior_library,
        )
        for row in config["target_occurrences"]
    ]
    with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
        occurrences = list(executor.map(_target, args))
    totals = {
        key: sum(row["accounting"][field] for row in occurrences)
        for key, field in (
            ("meta_activation", "meta_activation_labels"),
            ("no_prior_activation", "no_prior_activation_labels"),
            ("meta_labels", "meta_target_labels"),
            ("no_prior_labels", "no_prior_target_labels"),
            ("direct_labels", "direct_target_labels"),
        )
    }
    for key in (
        "full_post_dependency_world_model_match_count",
        "compiled_partial_world_model_fallback_match_count",
        "exact_certificate_policy_only_count",
        "abstract_model_ordered_execution_count",
        "execution_step_count",
    ):
        totals[f"meta_{key}"] = sum(
            row["meta_prior_hierarchical_utilization"][key]
            for row in occurrences
        )
    coverage = []
    for family in sorted(config["required_target_families"]):
        rows = [row for row in occurrences if row["target_family"] == family]
        accepts = sum(row["accept_count_for_family_aggregation"] for row in rows)
        disagreements = sum(
            row["disagreement_count_for_family_aggregation"] for row in rows
        )
        coverage.append(
            {
                "target_family": family,
                "occurrence_count": len(rows),
                "accept_count": accepts,
                "disagreement_abstention_count": disagreements,
                "both_shield_paths_observed_across_family": (
                    accepts > 0 and disagreements > 0
                ),
            }
        )
    ood = incompatible_schema_no_transfer_control_v99()
    passed = (
        all(row["registered_gate"]["passed"] for row in occurrences)
        and all(row["both_shield_paths_observed_across_family"] for row in coverage)
        and 2 * totals["meta_abstract_model_ordered_execution_count"]
        > totals["meta_execution_step_count"]
        and totals["meta_activation"] < totals["no_prior_activation"]
        and totals["meta_labels"] <= totals["no_prior_labels"]
        and totals["meta_labels"] < totals["direct_labels"]
        and ood["strict_ood_no_transfer"] is True
    )
    accounting = {
        **totals,
        "offline_source_labels_not_recharged": True,
        "sample_labels_execution_steps_derivation_shield_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] is True for row in occurrences
        ),
        "every_occurrence_abstract_model_orders_strict_majority": all(
            row["registered_gate"][
                "abstract_model_orders_strict_majority_of_executed_actions"
            ]
            for row in occurrences
        ),
        "every_target_family_exercises_both_shield_paths": all(
            row["both_shield_paths_observed_across_family"] for row in coverage
        ),
        "aggregate_activation_sample_tax_strictly_reduced": (
            totals["meta_activation"] < totals["no_prior_activation"]
        ),
        "aggregate_negative_transfer_absent": (
            totals["meta_labels"] <= totals["no_prior_labels"]
        ),
        "aggregate_meta_labels_strictly_below_cold_direct": (
            totals["meta_labels"] < totals["direct_labels"]
        ),
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    payload = {
        "schema": "acfqp.hierarchical_abstract_utilization_campaign.v104",
        "preregistration_id": preregistration_id,
        "v103_failed_campaign_id": v103_campaign_id,
        "v103_failure_verification_id": v103_verification_id,
        "source_library_artifact_id": source_library_artifact_id,
        "target_occurrences": occurrences,
        "family_wide_shield_path_coverage": coverage,
        "incompatible_schema_no_transfer_control": ood,
        "accounting": accounting,
        "registered_gate": gate,
        "registered_multistep_execution_primarily_abstract_ordered_verified": passed,
        "ground_distinctions_acquired_only_after_certificate_failure_verified": passed,
        "full_post_dependency_world_model_primary_ordering_verified": False,
        "partial_world_model_primary_ordering_verified": passed,
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v104(
            domains.CONSTRUCTION_K7_HIERARCHICAL_UTILIZATION_CAMPAIGN_V104_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_hierarchical_utilization_campaign_document_v104",
    "build_hierarchical_utilization_occurrence_v104",
    "derive_hierarchical_utilization_v104",
)
