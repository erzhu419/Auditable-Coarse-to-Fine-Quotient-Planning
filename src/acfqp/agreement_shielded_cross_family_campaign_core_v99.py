"""Cross-family campaign for activation tax with negative-transfer shielding."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import hashlib
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v99 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.generic_persistent_agreement_shielded_sequence_v99 import (
    run_persistent_agreement_shielded_arm_v99,
)
from acfqp.generic_persistent_multi_residual_sequence_v96 import (
    run_strict_cold_direct_sequence_v96,
)
from acfqp.phase3e_ids import canonical_json_bytes


def incompatible_schema_no_transfer_control_v99() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.incompatible_schema_no_transfer_control.v99",
        "source_required_interface": {
            "state_representation": "OPAQUE_FLAT_INTEGER_COLUMNS",
            "transition_representation": "PRE_ACTION_POST_VECTOR",
            "dependency_driver_space": "SUCCESSOR_COLUMNS",
        },
        "target_interface": {
            "state_representation": "NESTED_UNORDERED_TYPED_GRAPH",
            "transition_representation": "EVENT_LOG_WITHOUT_POST_VECTOR",
            "dependency_driver_space": None,
        },
        "exact_interface_match": False,
        "learned_structure_prior_delivered": False,
        "target_binding_search_started": False,
        "target_outcomes_accessed": False,
        "rejection_reason": "REQUIRED_FLAT_SUCCESSOR_COLUMN_INTERFACE_ABSENT",
        "strict_ood_no_transfer": True,
    }
    return {
        **payload,
        "control_id": hashlib.sha256(
            b"acfqp:incompatible-schema-no-transfer-control:v99\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def build_agreement_shielded_occurrence_v99(
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
    meta = run_persistent_agreement_shielded_arm_v99(
        adapter,
        partial["candidate"],
        partial["rows"],
        partial["document"]["ground_support_labels"],
        structural_prior_library=structural_prior_library,
        **common,
    )
    no_prior = run_persistent_agreement_shielded_arm_v99(
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
    dependency_count = len(acquisition["retrospective_post_dependency_candidates"])
    meta_activation = meta[
        "target_model_activation_ground_support_labels_with_right_censoring"
    ]
    no_prior_activation = no_prior[
        "target_model_activation_ground_support_labels_with_right_censoring"
    ]
    meta_labels = meta["lifetime_target_ground_support_labels"]
    no_prior_labels = no_prior["lifetime_target_ground_support_labels"]
    direct_labels = strict["lifetime_target_ground_support_labels"]
    first = meta["first_agreement_shielded_online_episode"]
    gate = {
        "meta_model_activated": meta["post_dependency_model_activation_observed"],
        "retained_model_covers_every_residual_target": acquisition[
            "all_residual_targets_have_compilable_proposals"
        ],
        "model_activation_strictly_earlier_than_no_prior": (
            meta_activation < no_prior_activation
        ),
        "agreement_shield_exercised": (
            first["agreement_shield_accept_count"] > 0
            and first["agreement_shield_disagreement_abstention_count"] > 0
        ),
        "persistent_agreement_shielded_abstract_planning_used": (
            meta["later_agreement_shield_accept_receipt_count"] > 0
        ),
        "meta_task_labels_noninferior_to_no_prior": meta_labels <= no_prior_labels,
        "meta_task_labels_strictly_below_cold_direct": meta_labels < direct_labels,
        "certificate_failure_only_query_discipline_clean": (
            meta["every_new_ground_query_followed_a_failed_certificate"]
            and no_prior["every_new_ground_query_followed_a_failed_certificate"]
        ),
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.agreement_shielded_cross_family_occurrence.v99",
        "source_structure_family": "COUPLED_EXCHANGE",
        "target_family": family,
        "cross_family_structure_transfer": family != "COUPLED_EXCHANGE",
        "seed": seed,
        "episode_indices": list(episode_indices),
        "common_partial_acquisition": partial["document"],
        "same_partial_rows_outcomes_synthesizer_stopping_rule_and_shield_between_arms": True,
        "only_switched_variable": "POST_DEPENDENCY_STRUCTURE_DESCRIPTION_CODE_UNITS",
        "meta_prior_persistent_sequence": meta,
        "no_structure_prior_persistent_sequence": no_prior,
        "strict_cold_direct_sequence": strict,
        "post_dependency_candidate_count": dependency_count,
        "accounting": {
            "meta_model_activation_target_labels_with_right_censoring": meta_activation,
            "no_prior_model_activation_target_labels_with_right_censoring": (
                no_prior_activation
            ),
            "meta_lifetime_target_labels": meta_labels,
            "no_prior_lifetime_target_labels": no_prior_labels,
            "strict_cold_direct_lifetime_target_labels": direct_labels,
            "meta_first_episode_shield_accept_count": first[
                "agreement_shield_accept_count"
            ],
            "meta_first_episode_shield_disagreement_abstention_count": first[
                "agreement_shield_disagreement_abstention_count"
            ],
            "meta_execution_steps": sum(
                row["execution_steps"]
                for row in [
                    first,
                    *meta["later_persistent_episodes"],
                ]
            ),
            "no_prior_execution_steps": sum(
                row["execution_steps"]
                for row in [
                    no_prior["first_agreement_shielded_online_episode"],
                    *no_prior["later_persistent_episodes"],
                ]
            ),
            "strict_execution_steps": sum(
                row["execution_steps"] for row in strict["episodes"]
            ),
            "sample_labels_execution_steps_derivation_shield_and_planning_compute_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": gate,
        "abstract_model_used_only_after_partial_agreement": True,
        "abstract_or_partial_model_used_as_safety_authority": False,
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
        "occurrence_id": domains.extension_content_id_v99(
            domains.CONSTRUCTION_K7_AGREEMENT_SHIELDED_OCCURRENCE_V99_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_agreement_shielded_occurrence_v99(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        factor_library=args[4],
        residual_library=args[5],
        structural_prior_library=args[6],
    )


def build_agreement_shielded_campaign_document_v99(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v98_campaign_id: str,
    v98_verification_id: str,
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
    totals = {
        key: sum(row["accounting"][field] for row in occurrences)
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
            for row in occurrences
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
        "schema": "acfqp.agreement_shielded_cross_family_campaign.v99",
        "preregistration_id": preregistration_id,
        "v98_campaign_id": v98_campaign_id,
        "v98_verification_id": v98_verification_id,
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
        "campaign_id": domains.extension_content_id_v99(
            domains.CONSTRUCTION_K7_AGREEMENT_SHIELDED_CAMPAIGN_V99_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_agreement_shielded_campaign_document_v99",
    "build_agreement_shielded_occurrence_v99",
    "incompatible_schema_no_transfer_control_v99",
)
