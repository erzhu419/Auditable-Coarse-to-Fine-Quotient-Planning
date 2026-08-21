"""Matched persistent joint-residual construction Gate."""

from __future__ import annotations

from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v96 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_persistent_multi_residual_sequence_v96 import (
    run_persistent_multi_residual_arm_v96,
    run_strict_cold_direct_sequence_v96,
)


def build_persistent_multi_residual_occurrence_v96(
    config: Mapping[str, Any],
    *,
    family: str,
    seed: int,
    episode_indices: tuple[int, ...],
    factor_library: Mapping[str, Any],
    residual_library: Mapping[str, Any],
) -> dict[str, Any]:
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        family, seed, config
    )
    acquisitions = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )
    meta_partial = acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"]
    # Keep the already-paid partial acquisition exact and common.  V96's sole
    # switch is the residual-factor meta-prior, matching the frozen V67 Gate.
    no_prior_partial = meta_partial
    common = dict(
        episode_indices=episode_indices,
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        confidence_denominator=config["residual_confidence_denominator"],
        maximum_joint_support_branch_evaluations=config[
            "maximum_joint_support_branch_evaluations"
        ],
        joint_support_feasible_beam_width=config[
            "joint_support_feasible_beam_width"
        ],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    meta = run_persistent_multi_residual_arm_v96(
        adapter,
        meta_partial["candidate"],
        meta_partial["rows"],
        meta_partial["document"]["ground_support_labels"],
        residual_prior_library=residual_library,
        **common,
    )
    no_prior = run_persistent_multi_residual_arm_v96(
        adapter,
        no_prior_partial["candidate"],
        no_prior_partial["rows"],
        no_prior_partial["document"]["ground_support_labels"],
        residual_prior_library=None,
        **common,
    )
    strict = run_strict_cold_direct_sequence_v96(
        adapter,
        meta_partial["candidate"],
        episode_indices=episode_indices,
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    gate = {
        "meta_retained_joint_proposal_count_at_least_two": (
            meta["retained_joint_proposal_count"] >= 2
        ),
        "meta_later_joint_abstract_plan_used": (
            meta["later_joint_abstract_plan_receipt_count"] > 0
        ),
        "meta_later_executed_action_matched_abstract_proposal": (
            meta[
                "later_execution_action_matches_any_abstract_proposal_count"
            ]
            > 0
        ),
        "all_later_queries_ground_label_free_after_overlay_closure": (
            meta["later_query_ground_support_labels"] == 0
            and no_prior["later_query_ground_support_labels"] == 0
        ),
        "meta_lifetime_labels_noninferior_to_no_residual_prior": (
            meta["lifetime_target_ground_support_labels"]
            <= no_prior["lifetime_target_ground_support_labels"]
        ),
        "meta_lifetime_labels_strictly_below_cold_direct": (
            meta["lifetime_target_ground_support_labels"]
            < strict["lifetime_target_ground_support_labels"]
        ),
        "certificate_failure_only_query_discipline_clean": (
            meta["every_new_ground_query_followed_a_failed_certificate"]
            and no_prior["every_new_ground_query_followed_a_failed_certificate"]
        ),
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.persistent_multi_residual_occurrence.v96",
        "family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "meta_prior_partial_acquisition": meta_partial["document"],
        "no_prior_partial_acquisition": no_prior_partial["document"],
        "same_partial_candidate_and_observations_between_residual_prior_arms": True,
        "only_switched_variable": (
            "FROZEN_RESIDUAL_FACTOR_EXPRESSION_PRIOR_CODE_LENGTH"
        ),
        "meta_prior_persistent_sequence": meta,
        "no_prior_persistent_sequence": no_prior,
        "strict_cold_direct_sequence": strict,
        "accounting": {
            "meta_prior_lifetime_target_labels": meta[
                "lifetime_target_ground_support_labels"
            ],
            "no_prior_lifetime_target_labels": no_prior[
                "lifetime_target_ground_support_labels"
            ],
            "strict_cold_direct_lifetime_target_labels": strict[
                "lifetime_target_ground_support_labels"
            ],
            "meta_prior_execution_steps": sum(
                episode["execution_steps"]
                for episode in [
                    meta["first_online_multi_residual_episode"],
                    *meta["later_persistent_episodes"],
                ]
            ),
            "no_prior_execution_steps": sum(
                episode["execution_steps"]
                for episode in [
                    no_prior["first_online_multi_residual_episode"],
                    *no_prior["later_persistent_episodes"],
                ]
            ),
            "strict_execution_steps": sum(
                episode["execution_steps"] for episode in strict["episodes"]
            ),
            "sample_labels_execution_steps_synthesis_and_planning_compute_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": gate,
        "persistent_joint_model_used_only_as_fallible_action_ordering_heuristic": True,
        "persistent_exact_overlay_exclusively_used_for_safety": True,
        "complete_world_model_synthesized": False,
        "sample_tax_reduction_generalized_beyond_two_registered_domain_families": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v96(
            domains.CONSTRUCTION_K7_PERSISTENT_MULTI_RESIDUAL_OCCURRENCE_V96_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_persistent_multi_residual_occurrence_v96",)
