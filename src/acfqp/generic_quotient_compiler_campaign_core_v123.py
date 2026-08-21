"""Fresh-target campaign for the generic quotient-model compiler V123."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v123 as domains
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_artifact_subprogram_acquisition_v121 import (
    acquire_generic_artifact_subprogram_model_v121,
)
from acfqp.generic_dual_budget_adapter_v119 import FAMILY, build_dual_budget_adapter_v119
from acfqp.generic_quotient_compiler_sequence_v123 import (
    run_generic_quotient_compiler_sequence_v123,
)


def build_generic_quotient_compiler_occurrence_v123(
    config: Mapping[str, Any],
    *,
    seed: int,
    episode_indices: tuple[int, ...],
    artifact_factor_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
    strict_complete_factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    adapter = build_dual_budget_adapter_v119(seed, config)
    acquired = acquire_generic_artifact_subprogram_model_v121(
        adapter,
        artifact_factor_library,
        source_campaign_bytes,
        strict_complete_factor_library,
        config,
    )
    partial = acquired["partial"]
    strict = acquired["strict_control"]["document"]
    sequence = run_generic_quotient_compiler_sequence_v123(
        adapter,
        partial["candidate"],
        partial["rows"],
        partial["document"]["ground_support_labels"],
        episode_indices=episode_indices,
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    v119 = sequence["generic_compiler_base_sequence"]
    base = v119["genesis_authorized_base_sequence"]
    candidate = partial["candidate"].public_document
    acquisition = partial["document"]
    comparison = sequence["generic_compiler_matched_control"]
    accounting = {
        "partial_prior_acquisition_labels": acquisition["ground_support_labels"],
        "strict_control_matched_prefix_labels": strict["ground_support_labels"],
        "strict_complete_model_attempt_count": strict["attempt_count"],
        "certificate_local_labels": base["certificate_ground_support_labels_paid_once"],
        "lifetime_target_labels": base["lifetime_target_ground_support_labels"],
        "execution_steps": base["execution_step_count"],
        "abstract_planning_compute_events": v119["actual_new_abstract_planning_compute_events"],
        "matched_uncached_planning_compute_events": v119[
            "matched_uncached_abstract_planning_compute_events"
        ],
        "planning_compute_events_avoided_against_uncached": v119[
            "planning_compute_events_avoided_against_uncached"
        ],
        "dependency_derivation_compute_events": v119[
            "dependency_derivation_compute_events"
        ],
        "same_epoch_genesis_authorized_cache_hits": v119[
            "same_epoch_genesis_authorized_cache_hit_count"
        ],
        "program_branch_cache_hits": v119["program_branch_cache_hit_count"],
        "generic_model_compiler_comparisons": comparison[
            "matched_model_comparison_count"
        ],
        "generic_model_program_support_checks": comparison[
            "generic_model_program_support_checks"
        ],
        "legacy_matched_control_program_support_checks": comparison[
            "legacy_matched_control_program_support_checks"
        ],
        "direct_generic_factor_program_plans": sequence[
            "direct_generic_factor_program_plan_count"
        ],
        "sample_labels_execution_steps_derivation_planning_and_model_checks_separate": True,
        "legacy_matched_control_compute_charged_to_generic_arm": False,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "fresh_dual_budget_identity_present": adapter.family == FAMILY,
        "candidate_uses_artifact_derived_factor_library": candidate[
            "source_factor_library_id"
        ]
        == artifact_factor_library["factor_library_id"],
        "partial_candidate_retains_unknown_higher_order_residual": bool(
            candidate["unknown_residual_target_columns"]
        ),
        "strict_control_uses_exact_partial_raw_prefix": strict[
            "ground_support_labels"
        ]
        == acquisition["ground_support_labels"]
        and strict["raw_transition_sha256"] == acquisition["raw_transition_sha256"],
        "strict_control_outcome_retained_without_selection": strict["outcome_kind"]
        in {
            "COMPLETE_CANDIDATE_SYNTHESIZED",
            "NO_COMPLETE_CANDIDATE_WITHIN_FROZEN_GRAMMAR",
        },
        "all_receding_abstract_episodes_succeed": all(
            row["success"] for row in base["episodes"]
        ),
        "generic_quotient_model_compiler_verified": sequence[
            "generic_quotient_model_compiler_verified"
        ],
        "generic_planner_execution_adapter_verified": sequence[
            "generic_planner_execution_adapter_verified"
        ],
        "generic_model_equal_to_retained_matched_control": comparison[
            "all_generic_models_equal_retained_v113_matched_control"
        ],
        "legacy_shape_specific_model_builder_not_planning_input": comparison[
            "legacy_shape_specific_model_builder_used_as_planning_input"
        ]
        is False,
        "legacy_shape_specific_planner_adapter_absent": sequence[
            "legacy_shape_specific_planner_execution_adapter_present"
        ]
        is False,
        "generic_program_fallback_exercised": sequence[
            "direct_generic_factor_program_plan_count"
        ]
        > 0,
        "certificate_failure_only_query_discipline_clean": base[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "incremental_generic_model_matches_full_generic_rebuild": base[
            "all_model_successors_exactly_equal_full_v105_rebuild"
        ],
        "planner_consumes_compiled_model_without_raw_rows": base[
            "planner_consumed_compiled_successor_without_raw_transition_argument"
        ],
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.generic_quotient_compiler_occurrence.v123",
        "target_family": FAMILY,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "artifact_factor_library_id": artifact_factor_library["factor_library_id"],
        "partial_prior_acquisition": acquisition,
        "strict_no_prior_complete_model_control": strict,
        "generic_quotient_compiler_sequence": sequence,
        "generic_quotient_compiler_sequence_id": sequence["sequence_id"],
        "accounting": accounting,
        "registered_gate": gate,
        "registered_generic_quotient_compiler_pipeline_verified": gate["passed"],
        "legacy_shape_specific_model_builder_retained_as_matched_control": True,
        "legacy_shape_specific_model_builder_used_as_planning_input": False,
        "legacy_shape_specific_planner_execution_adapter_present": False,
        "strict_complete_model_required_for_planning": False,
        "strict_control_outcome_used_for_gate_selection": False,
        "sample_efficiency_improvement_claimed": False,
        "ground_distinctions_only_after_certificate_failure_verified": gate["passed"],
        "compiled_model_or_receipt_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v123(
            domains.CONSTRUCTION_K7_GENERIC_QUOTIENT_COMPILER_OCCURRENCE_V123_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_generic_quotient_compiler_occurrence_v123(
        args[0],
        seed=args[1],
        episode_indices=args[2],
        artifact_factor_library=args[3],
        source_campaign_bytes=args[4],
        strict_complete_factor_library=args[5],
    )


def build_generic_quotient_compiler_campaign_document_v123(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v122_campaign_id: str,
    v122_verification_id: str,
    artifact_factor_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
    strict_complete_factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    args = [
        (
            config,
            row["seed"],
            tuple(config["target_episode_indices"]),
            artifact_factor_library,
            source_campaign_bytes,
            strict_complete_factor_library,
        )
        for row in config["target_occurrences"]
    ]
    if config["target_worker_count"] == 1:
        rows = [_target(row) for row in args]
    else:
        with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
            rows = list(executor.map(_target, args))
    ood = incompatible_schema_no_transfer_control_v99()
    passed = (
        len(rows) == config["required_target_occurrence_count"]
        and all(row["registered_gate"]["passed"] for row in rows)
        and ood["strict_ood_no_transfer"] is True
    )
    numeric_keys = tuple(rows[0]["accounting"])
    numeric = {
        key: sum(row["accounting"][key] for row in rows)
        for key in numeric_keys
        if type(rows[0]["accounting"][key]) is int
    }
    gate = {
        "required_target_occurrence_count": config["required_target_occurrence_count"],
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "generic_model_compiler_used_in_every_occurrence": all(
            row["registered_generic_quotient_compiler_pipeline_verified"] for row in rows
        ),
        "legacy_model_builder_not_planning_input_in_every_occurrence": all(
            row["legacy_shape_specific_model_builder_used_as_planning_input"] is False
            for row in rows
        ),
        "legacy_planner_adapter_absent_in_every_occurrence": all(
            row["legacy_shape_specific_planner_execution_adapter_present"] is False
            for row in rows
        ),
        "all_receding_episodes_succeed": all(
            episode["success"]
            for row in rows
            for episode in row["generic_quotient_compiler_sequence"][
                "generic_compiler_base_sequence"
            ]["genesis_authorized_base_sequence"]["episodes"]
        ),
        "every_occurrence_retains_unknown_residual": all(
            row["registered_gate"][
                "partial_candidate_retains_unknown_higher_order_residual"
            ]
            for row in rows
        ),
        "strict_control_outcomes_retained_without_gate_selection": True,
        "strict_incompatible_schema_no_transfer_verified": ood["strict_ood_no_transfer"],
        "passed": passed,
    }
    payload = {
        "schema": "acfqp.generic_quotient_compiler_campaign.v123",
        "preregistration_id": preregistration_id,
        "v122_success_campaign_id": v122_campaign_id,
        "v122_success_verification_id": v122_verification_id,
        "artifact_factor_library_id": artifact_factor_library["factor_library_id"],
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": ood,
        "accounting": {
            **numeric,
            "sample_labels_execution_steps_derivation_planning_and_model_checks_separate": True,
            "legacy_matched_control_compute_charged_to_generic_arm": False,
            "sample_efficiency_improvement_claimed": False,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": gate,
        "registered_generic_quotient_compiler_pipeline_verified": passed,
        "legacy_shape_specific_model_builder_retained_as_matched_control": True,
        "legacy_shape_specific_model_builder_used_as_planning_input": False,
        "legacy_shape_specific_planner_execution_adapter_present": False,
        "strict_complete_model_required_for_planning": False,
        "strict_control_outcome_used_for_gate_selection": False,
        "sample_efficiency_improvement_claimed": False,
        "ground_distinctions_only_after_certificate_failure_verified": passed,
        "compiled_model_or_receipt_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v123(
            domains.CONSTRUCTION_K7_GENERIC_QUOTIENT_COMPILER_CAMPAIGN_V123_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_generic_quotient_compiler_campaign_document_v123",
    "build_generic_quotient_compiler_occurrence_v123",
)
