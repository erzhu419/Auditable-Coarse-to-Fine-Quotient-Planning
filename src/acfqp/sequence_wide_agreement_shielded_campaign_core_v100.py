"""Fresh campaign with sequence-wide agreement-shield path coverage.

The planning, synthesis, acquisition, stopping, and shield implementations are
the frozen V99 implementation.  V100 changes only the prospective registered
path-coverage predicate: both shield paths must be observed somewhere in the
complete persistent sequence rather than both being forced into episode one.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v100 as domains
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    build_agreement_shielded_occurrence_v99,
    incompatible_schema_no_transfer_control_v99,
)


def build_sequence_wide_path_coverage_v100(
    algorithm_observation: Mapping[str, Any],
) -> dict[str, Any]:
    meta = algorithm_observation["meta_prior_persistent_sequence"]
    first = meta["first_agreement_shielded_online_episode"]
    first_accept = first["agreement_shield_accept_count"]
    first_disagreement = first["agreement_shield_disagreement_abstention_count"]
    later_accept = meta["later_agreement_shield_accept_receipt_count"]
    later_disagreement = meta[
        "later_agreement_shield_disagreement_abstention_count"
    ]
    total_accept = first_accept + later_accept
    total_disagreement = first_disagreement + later_disagreement
    return {
        "schema": "acfqp.sequence_wide_agreement_shield_path_coverage.v100",
        "first_episode_accept_count": first_accept,
        "first_episode_disagreement_abstention_count": first_disagreement,
        "later_episode_accept_count": later_accept,
        "later_episode_disagreement_abstention_count": later_disagreement,
        "persistent_sequence_accept_count": total_accept,
        "persistent_sequence_disagreement_abstention_count": total_disagreement,
        "accept_path_observed_somewhere_in_persistent_sequence": total_accept > 0,
        "disagreement_path_observed_somewhere_in_persistent_sequence": (
            total_disagreement > 0
        ),
        "both_paths_observed_somewhere_in_persistent_sequence": (
            total_accept > 0 and total_disagreement > 0
        ),
        "both_paths_required_in_first_episode": False,
        "path_coverage_window_fixed_before_v100_outcomes": True,
    }


def build_sequence_wide_agreement_shielded_occurrence_v100(
    config: Mapping[str, Any],
    *,
    family: str,
    seed: int,
    episode_indices: tuple[int, ...],
    factor_library: Mapping[str, Any],
    residual_library: Mapping[str, Any],
    structural_prior_library: Mapping[str, Any],
) -> dict[str, Any]:
    observation = build_agreement_shielded_occurrence_v99(
        config,
        family=family,
        seed=seed,
        episode_indices=episode_indices,
        factor_library=factor_library,
        residual_library=residual_library,
        structural_prior_library=structural_prior_library,
    )
    coverage = build_sequence_wide_path_coverage_v100(observation)
    old_gate = observation["registered_gate"]
    gate = {
        "meta_model_activated": old_gate["meta_model_activated"],
        "retained_model_covers_every_residual_target": old_gate[
            "retained_model_covers_every_residual_target"
        ],
        "model_activation_strictly_earlier_than_no_prior": old_gate[
            "model_activation_strictly_earlier_than_no_prior"
        ],
        "agreement_and_disagreement_paths_exercised_across_persistent_sequence": (
            coverage["both_paths_observed_somewhere_in_persistent_sequence"]
        ),
        "persistent_agreement_shielded_abstract_planning_used": old_gate[
            "persistent_agreement_shielded_abstract_planning_used"
        ],
        "meta_task_labels_noninferior_to_no_prior": old_gate[
            "meta_task_labels_noninferior_to_no_prior"
        ],
        "meta_task_labels_strictly_below_cold_direct": old_gate[
            "meta_task_labels_strictly_below_cold_direct"
        ],
        "certificate_failure_only_query_discipline_clean": old_gate[
            "certificate_failure_only_query_discipline_clean"
        ],
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.sequence_wide_agreement_shielded_occurrence.v100",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "frozen_v99_algorithm_observation": observation,
        "sequence_wide_path_coverage": coverage,
        "registered_gate": gate,
        "algorithm_changed_from_v99": False,
        "registered_path_coverage_window_changed_from_v99": True,
        "registered_path_coverage_window": "COMPLETE_PERSISTENT_SEQUENCE",
        "first_episode_path_coverage_required": False,
        "sample_labels_execution_steps_derivation_shield_and_planning_compute_separate": True,
        "complete_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v100(
            domains.CONSTRUCTION_K7_SEQUENCE_WIDE_AGREEMENT_SHIELDED_OCCURRENCE_V100_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_sequence_wide_agreement_shielded_occurrence_v100(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        factor_library=args[4],
        residual_library=args[5],
        structural_prior_library=args[6],
    )


def build_sequence_wide_agreement_shielded_campaign_document_v100(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v99_campaign_id: str,
    v99_verification_id: str,
    source_library_artifact_id: str,
    factor_library: Mapping[str, Any],
    residual_library: Mapping[str, Any],
    structural_prior_library: Mapping[str, Any],
) -> dict[str, Any]:
    arguments = [
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
    if config["target_worker_count"] == 1:
        occurrences = [_target(row) for row in arguments]
    else:
        with ProcessPoolExecutor(
            max_workers=config["target_worker_count"]
        ) as executor:
            occurrences = list(executor.map(_target, arguments))
    observations = [row["frozen_v99_algorithm_observation"] for row in occurrences]
    totals = {
        key: sum(row["accounting"][field] for row in observations)
        for key, field in (
            ("meta_activation", "meta_model_activation_target_labels_with_right_censoring"),
            ("no_prior_activation", "no_prior_model_activation_target_labels_with_right_censoring"),
            ("meta_labels", "meta_lifetime_target_labels"),
            ("no_prior_labels", "no_prior_lifetime_target_labels"),
            ("direct_labels", "strict_cold_direct_lifetime_target_labels"),
        )
    }
    families = sorted({row["target_family"] for row in occurrences})
    dependency_families = sorted(
        {
            row["target_family"]
            for row in observations
            if row["post_dependency_candidate_count"] > 0
        }
    )
    ood = incompatible_schema_no_transfer_control_v99()
    passed = (
        len(occurrences) == config["required_target_occurrence_count"]
        and all(row["registered_gate"]["passed"] for row in occurrences)
        and families == sorted(config["required_target_families"])
        and dependency_families == families
        and totals["meta_activation"] < totals["no_prior_activation"]
        and totals["meta_labels"] <= totals["no_prior_labels"]
        and totals["meta_labels"] < totals["direct_labels"]
        and ood["strict_ood_no_transfer"] is True
    )
    payload = {
        "schema": "acfqp.sequence_wide_agreement_shielded_campaign.v100",
        "preregistration_id": preregistration_id,
        "v99_failed_campaign_id": v99_campaign_id,
        "v99_failure_verification_id": v99_verification_id,
        "source_library_artifact_id": source_library_artifact_id,
        "target_occurrences": occurrences,
        "incompatible_schema_no_transfer_control": ood,
        "accounting": {
            **totals,
            "offline_source_labels_not_recharged": True,
            "sample_labels_execution_steps_derivation_shield_and_planning_compute_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": {
            "required_target_occurrence_count": config[
                "required_target_occurrence_count"
            ],
            "passed_target_occurrence_count": sum(
                row["registered_gate"]["passed"] is True for row in occurrences
            ),
            "target_families": families,
            "dependency_candidate_target_families": dependency_families,
            "aggregate_model_activation_sample_tax_strictly_reduced": (
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
        },
        "v99_registered_failure_preserved": True,
        "v99_algorithm_reused_without_change": True,
        "sequence_wide_shield_path_coverage_verified": passed,
        "cross_family_structure_transfer_with_target_bindings_rederived": passed,
        "agreement_shield_prevented_observed_aggregate_negative_transfer": passed,
        "structural_prior_model_activation_sample_tax_advantage_verified": passed,
        "structural_prior_total_task_label_advantage_verified": (
            passed and totals["meta_labels"] < totals["no_prior_labels"]
        ),
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
        "campaign_id": domains.extension_content_id_v100(
            domains.CONSTRUCTION_K7_SEQUENCE_WIDE_AGREEMENT_SHIELDED_CAMPAIGN_V100_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_sequence_wide_agreement_shielded_campaign_document_v100",
    "build_sequence_wide_agreement_shielded_occurrence_v100",
    "build_sequence_wide_path_coverage_v100",
)
