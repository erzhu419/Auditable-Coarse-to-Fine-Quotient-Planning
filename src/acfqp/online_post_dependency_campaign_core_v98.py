"""Matched campaign for online post-dependency activation sample tax."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v98 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_persistent_multi_residual_sequence_v96 import (
    run_strict_cold_direct_sequence_v96,
)
from acfqp.generic_persistent_online_post_dependency_sequence_v98 import (
    run_persistent_online_post_dependency_arm_v98,
)


def build_online_post_dependency_occurrence_v98(
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
    meta = run_persistent_online_post_dependency_arm_v98(
        adapter,
        partial["candidate"],
        partial["rows"],
        partial["document"]["ground_support_labels"],
        structural_prior_library=structural_prior_library,
        **common,
    )
    no_prior = run_persistent_online_post_dependency_arm_v98(
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
    acquisition = meta["retained_active_post_dependency_acquisition"]
    dependency_count = (
        0
        if acquisition is None
        else len(acquisition["retrospective_post_dependency_candidates"])
    )
    meta_activation = meta[
        "target_model_activation_ground_support_labels_with_right_censoring"
    ]
    no_prior_activation = no_prior[
        "target_model_activation_ground_support_labels_with_right_censoring"
    ]
    dependency_advantage = dependency_count > 0 and meta_activation < no_prior_activation
    gate = {
        "online_model_activated_in_meta_arm": meta[
            "post_dependency_model_activation_observed"
        ],
        "retained_model_covers_every_residual_target": (
            acquisition is not None
            and acquisition["all_residual_targets_have_compilable_proposals"]
            is True
        ),
        "later_persistent_abstract_planning_used": (
            meta["later_online_model_abstract_plan_receipt_count"] > 0
        ),
        "meta_activation_not_later_than_no_prior": (
            meta_activation <= no_prior_activation
        ),
        "dependency_occurrence_has_strict_activation_advantage": (
            dependency_advantage if dependency_count > 0 else True
        ),
        "meta_lifetime_labels_noninferior_to_no_prior": (
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
        "schema": "acfqp.online_post_dependency_occurrence.v98",
        "family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "common_partial_acquisition": partial["document"],
        "same_partial_candidate_rows_residual_prior_and_outcome_schedule_between_arms": True,
        "same_synthesizer_and_mdl_confidence_stopping_rule_between_arms": True,
        "only_switched_variable": "POST_DEPENDENCY_STRUCTURE_DESCRIPTION_CODE_UNITS",
        "meta_prior_persistent_sequence": meta,
        "no_structure_prior_persistent_sequence": no_prior,
        "strict_cold_direct_sequence": strict,
        "post_dependency_candidate_count": dependency_count,
        "dependency_occurrence_has_strict_activation_advantage": dependency_advantage,
        "accounting": {
            "meta_model_activation_target_labels_with_right_censoring": meta_activation,
            "no_prior_model_activation_target_labels_with_right_censoring": (
                no_prior_activation
            ),
            "meta_lifetime_target_labels": meta[
                "lifetime_target_ground_support_labels"
            ],
            "no_prior_lifetime_target_labels": no_prior[
                "lifetime_target_ground_support_labels"
            ],
            "strict_cold_direct_lifetime_target_labels": strict[
                "lifetime_target_ground_support_labels"
            ],
            "meta_post_dependency_synthesis_attempts": meta[
                "first_online_post_dependency_episode"
            ]["post_dependency_synthesis_attempt_count"],
            "no_prior_post_dependency_synthesis_attempts": no_prior[
                "first_online_post_dependency_episode"
            ]["post_dependency_synthesis_attempt_count"],
            "meta_joint_abstract_support_branch_evaluations": meta[
                "first_online_post_dependency_episode"
            ]["joint_abstract_support_branch_evaluations"],
            "no_prior_joint_abstract_support_branch_evaluations": no_prior[
                "first_online_post_dependency_episode"
            ]["joint_abstract_support_branch_evaluations"],
            "meta_execution_steps": sum(
                row["execution_steps"]
                for row in [
                    meta["first_online_post_dependency_episode"],
                    *meta["later_persistent_episodes"],
                ]
            ),
            "no_prior_execution_steps": sum(
                row["execution_steps"]
                for row in [
                    no_prior["first_online_post_dependency_episode"],
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
        "model_activation_is_fallible_proposal_not_safety_authority": True,
        "persistent_exact_overlay_exclusively_used_for_safety": True,
        "source_structure_prior_supplied_target_bindings": False,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v98(
            domains.CONSTRUCTION_K7_ONLINE_POST_DEPENDENCY_OCCURRENCE_V98_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_online_post_dependency_occurrence_v98(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        factor_library=args[4],
        residual_library=args[5],
        structural_prior_library=args[6],
    )


def build_online_post_dependency_campaign_document_v98(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v97_campaign_id: str,
    v97_verification_id: str,
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
    meta_activation = sum(
        row["accounting"][
            "meta_model_activation_target_labels_with_right_censoring"
        ]
        for row in occurrences
    )
    no_prior_activation = sum(
        row["accounting"][
            "no_prior_model_activation_target_labels_with_right_censoring"
        ]
        for row in occurrences
    )
    meta = sum(
        row["accounting"]["meta_lifetime_target_labels"] for row in occurrences
    )
    no_prior = sum(
        row["accounting"]["no_prior_lifetime_target_labels"]
        for row in occurrences
    )
    direct = sum(
        row["accounting"]["strict_cold_direct_lifetime_target_labels"]
        for row in occurrences
    )
    dependency_rows = [
        row for row in occurrences if row["post_dependency_candidate_count"] > 0
    ]
    passed = (
        len(occurrences) == config["required_target_occurrence_count"]
        and all(row["registered_gate"]["passed"] for row in occurrences)
        and bool(dependency_rows)
        and all(
            row["dependency_occurrence_has_strict_activation_advantage"]
            is True
            for row in dependency_rows
        )
        and meta_activation < no_prior_activation
        and meta <= no_prior
        and meta < direct
        and sum(
            row["meta_prior_persistent_sequence"][
                "later_post_dependency_abstract_plan_receipt_count"
            ]
            for row in occurrences
        )
        > 0
    )
    payload = {
        "schema": "acfqp.online_post_dependency_campaign.v98",
        "preregistration_id": preregistration_id,
        "v97_campaign_id": v97_campaign_id,
        "v97_verification_id": v97_verification_id,
        "source_library_artifact_id": source_library_artifact_id,
        "target_occurrences": occurrences,
        "accounting": {
            "meta_model_activation_target_labels_with_right_censoring": meta_activation,
            "no_prior_model_activation_target_labels_with_right_censoring": (
                no_prior_activation
            ),
            "meta_lifetime_target_labels": meta,
            "no_prior_lifetime_target_labels": no_prior,
            "strict_cold_direct_lifetime_target_labels": direct,
            "offline_source_labels_in_predecessor_artifacts_not_recharged": True,
            "target_labels_execution_steps_synthesis_and_planning_compute_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": {
            "required_target_occurrence_count": config[
                "required_target_occurrence_count"
            ],
            "passed_target_occurrence_count": sum(
                row["registered_gate"]["passed"] is True for row in occurrences
            ),
            "post_dependency_occurrence_count": len(dependency_rows),
            "aggregate_model_activation_sample_tax_strictly_reduced": (
                meta_activation < no_prior_activation
            ),
            "all_dependency_occurrences_strictly_reduce_activation_labels": all(
                row["dependency_occurrence_has_strict_activation_advantage"]
                is True
                for row in dependency_rows
            ),
            "meta_lifetime_task_labels_noninferior_to_no_prior": meta <= no_prior,
            "meta_lifetime_task_labels_strictly_below_cold_direct": meta < direct,
            "passed": passed,
        },
        "same_synthesizer_stopping_rule_partial_rows_and_outcome_schedule_matched": True,
        "only_structure_description_code_units_switched": True,
        "structural_prior_model_activation_sample_tax_advantage_verified": passed,
        "structural_prior_total_task_label_advantage_over_same_synthesizer_verified": (
            passed and meta < no_prior
        ),
        "persistent_abstract_planning_with_certificate_failure_only_local_recovery_verified": passed,
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
        "campaign_id": domains.extension_content_id_v98(
            domains.CONSTRUCTION_K7_ONLINE_POST_DEPENDENCY_CAMPAIGN_V98_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_online_post_dependency_campaign_document_v98",
    "build_online_post_dependency_occurrence_v98",
)
