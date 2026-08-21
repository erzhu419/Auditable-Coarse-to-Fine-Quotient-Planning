"""Matched persistent post-dependency construction Gate."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v97 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_persistent_multi_residual_sequence_v96 import (
    run_strict_cold_direct_sequence_v96,
)
from acfqp.generic_persistent_post_dependency_sequence_v97 import (
    run_persistent_post_dependency_arm_v97,
)


def build_post_dependency_occurrence_v97(
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
    acquisitions = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )
    partial = acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"]
    common = dict(
        residual_prior_library=residual_library,
        episode_indices=episode_indices,
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        confidence_denominator=config["residual_confidence_denominator"],
        maximum_support_branch_evaluations=config[
            "maximum_joint_support_branch_evaluations"
        ],
        support_feasible_beam_width=config[
            "joint_support_feasible_beam_width"
        ],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    meta = run_persistent_post_dependency_arm_v97(
        adapter,
        partial["candidate"],
        partial["rows"],
        partial["document"]["ground_support_labels"],
        structural_prior_library=structural_prior_library,
        **common,
    )
    no_prior = run_persistent_post_dependency_arm_v97(
        adapter,
        partial["candidate"],
        partial["rows"],
        partial["document"]["ground_support_labels"],
        structural_prior_library=None,
        **common,
    )
    strict = run_strict_cold_direct_sequence_v96(
        adapter,
        partial["candidate"],
        episode_indices=episode_indices,
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    gate = {
        "meta_post_dependency_candidate_discovered_in_this_occurrence": (
            meta["retained_post_dependency_candidate_count"] >= 1
        ),
        "meta_joint_successor_represents_every_residual_target": (
            meta["retained_joint_residual_candidate_count"]
            == len(partial["candidate"].public_document[
                "unknown_residual_target_columns"
            ])
        ),
        "meta_later_joint_abstract_plan_used": (
            meta["later_joint_abstract_plan_receipt_count"] > 0
        ),
        "meta_later_executed_action_matched_abstract_proposal": (
            meta["later_execution_action_matches_any_abstract_proposal_count"]
            > 0
        ),
        "meta_lifetime_labels_noninferior_to_no_structure_prior": (
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
    gate["passed"] = all(
        value
        for key, value in gate.items()
        if key != "meta_post_dependency_candidate_discovered_in_this_occurrence"
    )
    payload = {
        "schema": "acfqp.post_dependency_occurrence.v97",
        "family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "common_partial_acquisition": partial["document"],
        "same_partial_candidate_rows_residual_prior_and_first_episode_between_structure_arms": (
            meta["first_online_multi_residual_episode"]
            == no_prior["first_online_multi_residual_episode"]
        ),
        "only_switched_variable": "POST_DEPENDENCY_STRUCTURE_PRIOR_CODE_LENGTH",
        "meta_prior_persistent_sequence": meta,
        "no_structure_prior_persistent_sequence": no_prior,
        "strict_cold_direct_sequence": strict,
        "accounting": {
            "meta_prior_lifetime_target_labels": meta[
                "lifetime_target_ground_support_labels"
            ],
            "no_structure_prior_lifetime_target_labels": no_prior[
                "lifetime_target_ground_support_labels"
            ],
            "strict_cold_direct_lifetime_target_labels": strict[
                "lifetime_target_ground_support_labels"
            ],
            "meta_post_dependency_binding_evaluations": meta[
                "retained_post_dependency_acquisition"
            ]["post_dependency_candidate_binding_evaluation_count"],
            "no_prior_post_dependency_binding_evaluations": no_prior[
                "retained_post_dependency_acquisition"
            ]["post_dependency_candidate_binding_evaluation_count"],
            "meta_execution_steps": sum(
                row["execution_steps"]
                for row in [
                    meta["first_online_multi_residual_episode"],
                    *meta["later_persistent_episodes"],
                ]
            ),
            "no_prior_execution_steps": sum(
                row["execution_steps"]
                for row in [
                    no_prior["first_online_multi_residual_episode"],
                    *no_prior["later_persistent_episodes"],
                ]
            ),
            "strict_execution_steps": sum(
                row["execution_steps"] for row in strict["episodes"]
            ),
            "sample_labels_execution_steps_synthesis_and_planning_compute_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": gate,
        "source_structure_prior_supplied_target_bindings": False,
        "post_dependency_program_used_only_as_fallible_action_ordering_heuristic": True,
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
        "occurrence_id": domains.extension_content_id_v97(
            domains.CONSTRUCTION_K7_POST_DEPENDENCY_OCCURRENCE_V97_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_post_dependency_occurrence_v97(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        factor_library=args[4],
        residual_library=args[5],
        structural_prior_library=args[6],
    )


def build_post_dependency_campaign_document_v97(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v96_campaign_id: str,
    v96_verification_id: str,
    source_library_artifact_id: str,
    factor_library: Mapping[str, Any],
    residual_library: Mapping[str, Any],
    structural_prior_library: Mapping[str, Any],
) -> dict[str, Any]:
    arguments = [
        (
            config,
            config["target_family"],
            seed,
            tuple(config["target_episode_indices"]),
            factor_library,
            residual_library,
            structural_prior_library,
        )
        for seed in config["target_seeds"]
    ]
    if config["target_worker_count"] == 1:
        occurrences = [_target(row) for row in arguments]
    else:
        with ProcessPoolExecutor(
            max_workers=config["target_worker_count"]
        ) as executor:
            occurrences = list(executor.map(_target, arguments))
    meta = sum(
        row["accounting"]["meta_prior_lifetime_target_labels"]
        for row in occurrences
    )
    no_prior = sum(
        row["accounting"]["no_structure_prior_lifetime_target_labels"]
        for row in occurrences
    )
    direct = sum(
        row["accounting"]["strict_cold_direct_lifetime_target_labels"]
        for row in occurrences
    )
    passed_rows = [row for row in occurrences if row["registered_gate"]["passed"]]
    receipts = sum(
        row["meta_prior_persistent_sequence"][
            "later_post_dependency_abstract_plan_receipt_count"
        ]
        for row in occurrences
    )
    joint_receipts = sum(
        row["meta_prior_persistent_sequence"][
            "later_joint_abstract_plan_receipt_count"
        ]
        for row in occurrences
    )
    dependency_occurrences = sum(
        row["registered_gate"][
            "meta_post_dependency_candidate_discovered_in_this_occurrence"
        ]
        is True
        for row in occurrences
    )
    passed = (
        len(passed_rows) == config["required_target_occurrence_count"]
        and meta <= no_prior
        and meta < direct
        and dependency_occurrences > 0
        and receipts > 0
        and joint_receipts > 0
    )
    payload = {
        "schema": "acfqp.post_dependency_campaign.v97",
        "preregistration_id": preregistration_id,
        "v96_campaign_id": v96_campaign_id,
        "v96_verification_id": v96_verification_id,
        "source_library_artifact_id": source_library_artifact_id,
        "target_occurrences": occurrences,
        "accounting": {
            "meta_prior_lifetime_target_labels": meta,
            "no_structure_prior_lifetime_target_labels": no_prior,
            "strict_cold_direct_lifetime_target_labels": direct,
            "strict_minus_meta_prior_lifetime_target_labels": direct - meta,
            "later_post_dependency_abstract_plan_receipt_count": receipts,
            "later_joint_abstract_plan_receipt_count": joint_receipts,
            "source_labels_target_labels_execution_steps_derivation_and_planning_compute_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": {
            "required_target_occurrence_count": config[
                "required_target_occurrence_count"
            ],
            "completed_passing_target_occurrence_count": len(passed_rows),
            "every_target_discovered_post_dependency_program": all(
                row["registered_gate"][
                    "meta_post_dependency_candidate_discovered_in_this_occurrence"
                ]
                for row in occurrences
            ),
            "at_least_one_fresh_target_discovered_post_dependency_program": (
                dependency_occurrences > 0
            ),
            "at_least_one_fresh_target_used_post_dependency_abstract_plan": (
                receipts > 0
            ),
            "every_target_used_joint_abstract_plan": all(
                row["registered_gate"][
                    "meta_later_joint_abstract_plan_used"
                ]
                for row in occurrences
            ),
            "aggregate_meta_labels_noninferior_to_no_structure_prior": meta
            <= no_prior,
            "aggregate_meta_labels_strictly_below_cold_direct": meta < direct,
            "passed": passed,
        },
        "fresh_target_identities_executed_without_selection": True,
        "successor_coordinate_dependency_synthesized_and_jointly_compiled": passed,
        "persistent_exact_overlay_reduced_repeated_query_sample_tax": passed,
        "structural_prior_sample_tax_advantage_over_same_synthesizer_verified": False,
        "producer_free_verification_present": False,
        "sample_tax_reduction_generalized_beyond_two_registered_domain_families": False,
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
        "campaign_id": domains.extension_content_id_v97(
            domains.CONSTRUCTION_K7_POST_DEPENDENCY_CAMPAIGN_V97_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_post_dependency_campaign_document_v97",
    "build_post_dependency_occurrence_v97",
)
