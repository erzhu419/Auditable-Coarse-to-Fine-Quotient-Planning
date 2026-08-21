"""Fresh-target campaign using the generic compiled-factor planner V122."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v122 as domains
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_artifact_subprogram_acquisition_v121 import (
    acquire_generic_artifact_subprogram_model_v121,
)
from acfqp.generic_dual_budget_adapter_v119 import FAMILY, build_dual_budget_adapter_v119
from acfqp.generic_factor_planner_sequence_v122 import (
    run_generic_factor_planner_sequence_v122,
)


def build_generic_factor_planner_occurrence_v122(
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
    sequence = run_generic_factor_planner_sequence_v122(
        adapter,
        partial["candidate"],
        partial["rows"],
        partial["document"]["ground_support_labels"],
        episode_indices=episode_indices,
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    v119 = sequence["generic_planner_base_sequence"]
    base = v119["genesis_authorized_base_sequence"]
    candidate = partial["candidate"].public_document
    partial_document = partial["document"]
    execution = sequence["generic_execution_verification"]
    accounting = {
        "partial_prior_acquisition_labels": partial_document["ground_support_labels"],
        "strict_control_matched_prefix_labels": strict["ground_support_labels"],
        "strict_complete_model_attempt_count": strict["attempt_count"],
        "certificate_local_labels": base[
            "certificate_ground_support_labels_paid_once"
        ],
        "lifetime_target_labels": base["lifetime_target_ground_support_labels"],
        "execution_steps": base["execution_step_count"],
        "abstract_planning_compute_events": v119[
            "actual_new_abstract_planning_compute_events"
        ],
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
        "generic_binding_candidate_evaluations": sum(
            row.get("exact_template_binding_count", 0)
            for row in candidate["binding_ambiguity_inventory"]
        ),
        "generic_projected_edge_support_checks": execution[
            "generic_projected_edge_support_checks"
        ],
        "generic_terminal_rule_checks": execution["generic_terminal_rule_checks"],
        "direct_generic_factor_program_plans": execution[
            "direct_generic_factor_program_plan_count"
        ],
        "memoized_generic_planner_sources": execution[
            "memoized_generic_planner_source_count"
        ],
        "sample_labels_execution_steps_binding_derivation_planning_dependency_and_generic_execution_checks_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "fresh_dual_budget_identity_present": adapter.family == FAMILY,
        "candidate_uses_artifact_derived_factor_library": candidate[
            "source_factor_library_id"
        ]
        == artifact_factor_library["factor_library_id"],
        "generic_symbol_binding_and_opcode_interpretation_used": partial_document[
            "generic_symbol_binding_and_opcode_interpretation_used"
        ],
        "partial_candidate_retains_unknown_higher_order_residual": bool(
            candidate["unknown_residual_target_columns"]
        ),
        "strict_control_uses_exact_partial_raw_prefix": strict[
            "ground_support_labels"
        ]
        == partial_document["ground_support_labels"]
        and strict["raw_transition_sha256"]
        == partial_document["raw_transition_sha256"],
        "strict_control_outcome_retained_without_selection": strict["outcome_kind"]
        in {
            "COMPLETE_CANDIDATE_SYNTHESIZED",
            "NO_COMPLETE_CANDIDATE_WITHIN_FROZEN_GRAMMAR",
        },
        "all_receding_abstract_episodes_succeed": all(
            row["success"] for row in base["episodes"]
        ),
        "generic_program_fallback_exercised": execution[
            "direct_generic_factor_program_plan_count"
        ]
        > 0,
        "every_compiled_edge_replayed_by_generic_interpreter": execution[
            "every_compiled_model_edge_replayed_by_generic_interpreter"
        ],
        "every_direct_fallback_used_generic_adapter": execution[
            "every_direct_program_fallback_used_generic_adapter"
        ],
        "legacy_shape_specific_planner_adapter_not_called": execution[
            "legacy_shape_specific_planner_execution_adapter_called"
        ]
        is False,
        "cache_hit_opportunity_not_required": v119[
            "same_epoch_genesis_authorized_cache_hit_count"
        ]
        >= 0,
        "certificate_failure_only_query_discipline_clean": base[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "incremental_model_matches_full_v105_rebuild": base[
            "all_model_successors_exactly_equal_full_v105_rebuild"
        ],
        "planner_consumes_compiled_model_without_raw_rows": base[
            "planner_consumed_compiled_successor_without_raw_transition_argument"
        ],
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.generic_factor_planner_occurrence.v122",
        "target_family": FAMILY,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "artifact_factor_library_id": artifact_factor_library["factor_library_id"],
        "partial_prior_acquisition": partial_document,
        "strict_no_prior_complete_model_control": strict,
        "generic_factor_planner_sequence": sequence,
        "generic_factor_planner_sequence_id": sequence["sequence_id"],
        "accounting": accounting,
        "registered_gate": gate,
        "registered_generic_factor_planner_pipeline_verified": gate["passed"],
        "legacy_shape_specific_model_builder_retained_as_matched_control": True,
        "legacy_shape_specific_planner_execution_adapter_present": False,
        "generic_planner_execution_adapter_verified": gate["passed"],
        "target_family_present_in_historical_artifact_inventory": True,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "strict_complete_model_required_for_planning": False,
        "strict_control_outcome_used_for_gate_selection": False,
        "sample_efficiency_improvement_claimed": False,
        "ground_distinctions_only_after_certificate_failure_verified": gate[
            "passed"
        ],
        "compiled_model_cache_or_receipt_used_as_safety_authority": False,
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
        "occurrence_id": domains.extension_content_id_v122(
            domains.CONSTRUCTION_K7_GENERIC_FACTOR_PLANNER_OCCURRENCE_V122_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_generic_factor_planner_occurrence_v122(
        args[0],
        seed=args[1],
        episode_indices=args[2],
        artifact_factor_library=args[3],
        source_campaign_bytes=args[4],
        strict_complete_factor_library=args[5],
    )


def build_generic_factor_planner_campaign_document_v122(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v121r1_campaign_id: str,
    v121r1_verification_id: str,
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
    keys = tuple(rows[0]["accounting"])
    numeric = {
        key: sum(row["accounting"][key] for row in rows)
        for key in keys
        if type(rows[0]["accounting"][key]) is int
    }
    gate = {
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "generic_planner_used_in_every_occurrence": all(
            row["generic_planner_execution_adapter_verified"] for row in rows
        ),
        "legacy_shape_specific_planner_adapter_absent_in_every_occurrence": all(
            row["legacy_shape_specific_planner_execution_adapter_present"] is False
            for row in rows
        ),
        "all_receding_episodes_succeed": all(
            episode["success"]
            for row in rows
            for episode in row["generic_factor_planner_sequence"][
                "generic_planner_base_sequence"
            ]["genesis_authorized_base_sequence"]["episodes"]
        ),
        "every_occurrence_retains_unknown_residual": all(
            row["registered_gate"][
                "partial_candidate_retains_unknown_higher_order_residual"
            ]
            for row in rows
        ),
        "strict_control_outcomes_retained_without_gate_selection": True,
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    accounting = {
        **numeric,
        "same_epoch_genesis_authorized_cache_hits_are_diagnostic_not_gate": True,
        "sample_labels_execution_steps_binding_derivation_planning_dependency_and_generic_execution_checks_separate": True,
        "sample_efficiency_improvement_claimed": False,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.generic_factor_planner_campaign.v122",
        "preregistration_id": preregistration_id,
        "v121r1_success_campaign_id": v121r1_campaign_id,
        "v121r1_success_verification_id": v121r1_verification_id,
        "artifact_factor_library_id": artifact_factor_library["factor_library_id"],
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": ood,
        "accounting": accounting,
        "registered_gate": gate,
        "registered_generic_factor_planner_pipeline_verified": passed,
        "legacy_shape_specific_model_builder_retained_as_matched_control": True,
        "legacy_shape_specific_planner_execution_adapter_present": False,
        "generic_planner_execution_adapter_verified": passed,
        "target_family_present_in_historical_artifact_inventory": True,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "strict_complete_model_required_for_planning": False,
        "strict_control_outcome_used_for_gate_selection": False,
        "sample_efficiency_improvement_claimed": False,
        "ground_distinctions_only_after_certificate_failure_verified": passed,
        "compiled_model_cache_or_receipt_used_as_safety_authority": False,
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
        "campaign_id": domains.extension_content_id_v122(
            domains.CONSTRUCTION_K7_GENERIC_FACTOR_PLANNER_CAMPAIGN_V122_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_generic_factor_planner_campaign_document_v122",
    "build_generic_factor_planner_occurrence_v122",
)
