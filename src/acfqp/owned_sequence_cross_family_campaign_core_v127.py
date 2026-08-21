"""Run the unchanged V126 owned sequence on the dual-budget family."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v127 as domains
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import incompatible_schema_no_transfer_control_v99
from acfqp.generic_artifact_subprogram_acquisition_v121 import acquire_generic_artifact_subprogram_model_v121
from acfqp.generic_dual_budget_adapter_v119 import FAMILY, build_dual_budget_adapter_v119
from acfqp.standalone_generic_owned_sequence_v126 import run_standalone_generic_owned_sequence_v126


def build_owned_sequence_cross_family_occurrence_v127(
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
    partial, strict = acquired["partial"], acquired["strict_control"]["document"]
    acquisition = partial["document"]
    sequence = run_standalone_generic_owned_sequence_v126(
        adapter,
        partial["candidate"],
        partial["rows"],
        acquisition["ground_support_labels"],
        episode_indices=episode_indices,
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    models = [*sequence["quotient_models_before_each_episode"], *sequence["quotient_models_after_each_episode"]]
    accounting = {
        "partial_prior_acquisition_labels": acquisition["ground_support_labels"],
        "strict_control_matched_prefix_labels": strict["ground_support_labels"],
        "strict_complete_model_attempt_count": strict["attempt_count"],
        "certificate_local_labels": sequence["certificate_ground_support_labels_paid_once"],
        "lifetime_target_labels": sequence["lifetime_target_ground_support_labels"],
        "execution_steps": sequence["execution_step_count"],
        "abstract_planning_compute_events": sequence["actual_new_abstract_planning_compute_events"],
        "matched_uncached_planning_compute_events": sequence["matched_uncached_abstract_planning_compute_events"],
        "planning_compute_events_avoided_against_uncached": sequence["planning_compute_events_avoided_against_uncached"],
        "dependency_derivation_compute_events": sequence["dependency_derivation_compute_events"],
        "standalone_model_epoch_reconstructions": len(models),
        "generic_model_program_support_checks": sum(model["source_projected_edge_program_checks"] for model in models),
        "direct_generic_factor_program_plans": sequence["direct_generic_factor_program_plan_count"],
        "sample_labels_execution_steps_derivation_planning_and_model_checks_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "fresh_dual_budget_identity_present": adapter.family == FAMILY,
        "candidate_uses_artifact_derived_factor_library": partial["candidate"].public_document["source_factor_library_id"] == artifact_factor_library["factor_library_id"],
        "partial_candidate_retains_unknown_residual": bool(partial["candidate"].public_document["unknown_residual_target_columns"]),
        "strict_control_uses_exact_partial_raw_prefix": strict["ground_support_labels"] == acquisition["ground_support_labels"] and strict["raw_transition_sha256"] == acquisition["raw_transition_sha256"],
        "all_receding_episodes_succeed": all(row["success"] for row in sequence["episodes"]),
        "unchanged_v126_owned_sequence_reused": sequence["owned_episode_loop_implementation_present"],
        "retained_v113_sequence_orchestration_absent": sequence["retained_v113_sequence_orchestration_present"] is False,
        "retained_v119_sequence_orchestration_absent": sequence["retained_v119_sequence_orchestration_present"] is False,
        "generic_program_fallback_exercised": sequence["direct_generic_factor_program_plan_count"] > 0,
        "certificate_failure_only_query_discipline_clean": sequence["every_new_ground_query_followed_a_failed_certificate"],
        "planner_consumes_compiled_model_without_raw_rows": sequence["planner_consumed_compiled_successor_without_raw_transition_argument"],
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.owned_sequence_cross_family_occurrence.v127",
        "target_family": FAMILY,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "artifact_factor_library_id": artifact_factor_library["factor_library_id"],
        "partial_prior_acquisition": acquisition,
        "strict_no_prior_complete_model_control": strict,
        "standalone_generic_owned_sequence": sequence,
        "standalone_generic_owned_sequence_id": sequence["sequence_id"],
        "accounting": accounting,
        "registered_gate": gate,
        "same_v126_owned_sequence_reused_without_family_dispatch": True,
        "retained_v113_state_carrier_present": False,
        "retained_v113_sequence_orchestration_present": False,
        "retained_v119_sequence_orchestration_present": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "sample_efficiency_improvement_claimed": False,
        "ground_distinctions_only_after_certificate_failure_verified": gate["passed"],
        "compiled_model_or_receipt_used_as_safety_authority": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v127(
            domains.CONSTRUCTION_K7_OWNED_SEQUENCE_CROSS_FAMILY_OCCURRENCE_V127_DOMAIN,
            payload,
        ),
    }


def _target(args):
    return build_owned_sequence_cross_family_occurrence_v127(
        args[0],
        seed=args[1],
        episode_indices=args[2],
        artifact_factor_library=args[3],
        source_campaign_bytes=args[4],
        strict_complete_factor_library=args[5],
    )


def build_owned_sequence_cross_family_campaign_document_v127(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v126_campaign_id: str,
    v126_verification_id: str,
    artifact_factor_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
    strict_complete_factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    args = [
        (config, row["seed"], tuple(config["target_episode_indices"]), artifact_factor_library, source_campaign_bytes, strict_complete_factor_library)
        for row in config["target_occurrences"]
    ]
    if config["target_worker_count"] == 1:
        rows = [_target(row) for row in args]
    else:
        with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
            rows = list(executor.map(_target, args))
    ood = incompatible_schema_no_transfer_control_v99()
    passed = len(rows) == config["required_target_occurrence_count"] and all(row["registered_gate"]["passed"] for row in rows) and ood["strict_ood_no_transfer"] is True
    numeric = [key for key, value in rows[0]["accounting"].items() if type(value) is int]
    accounting = {key: sum(row["accounting"][key] for row in rows) for key in numeric}
    accounting.update(sample_labels_execution_steps_derivation_planning_and_model_checks_separate=True, sample_efficiency_improvement_claimed=False, scalar_cost_aggregation_performed=False)
    gate = {
        "required_target_occurrence_count": config["required_target_occurrence_count"],
        "passed_target_occurrence_count": sum(row["registered_gate"]["passed"] for row in rows),
        "unchanged_v126_owned_sequence_reused_in_every_occurrence": all(row["same_v126_owned_sequence_reused_without_family_dispatch"] for row in rows),
        "retained_v113_sequence_orchestration_absent_in_every_occurrence": all(row["retained_v113_sequence_orchestration_present"] is False for row in rows),
        "retained_v119_sequence_orchestration_absent_in_every_occurrence": all(row["retained_v119_sequence_orchestration_present"] is False for row in rows),
        "all_receding_episodes_succeed": all(ep["success"] for row in rows for ep in row["standalone_generic_owned_sequence"]["episodes"]),
        "strict_incompatible_schema_no_transfer_verified": ood["strict_ood_no_transfer"],
        "passed": passed,
    }
    payload = {
        "schema": "acfqp.owned_sequence_cross_family_campaign.v127",
        "preregistration_id": preregistration_id,
        "v126_success_campaign_id": v126_campaign_id,
        "v126_success_verification_id": v126_verification_id,
        "artifact_factor_library_id": artifact_factor_library["factor_library_id"],
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": ood,
        "accounting": accounting,
        "registered_gate": gate,
        "same_v126_owned_sequence_reused_without_family_dispatch": passed,
        "retained_v113_state_carrier_present": False,
        "retained_v113_sequence_orchestration_present": False,
        "retained_v119_sequence_orchestration_present": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "sample_efficiency_improvement_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v127(
            domains.CONSTRUCTION_K7_OWNED_SEQUENCE_CROSS_FAMILY_CAMPAIGN_V127_DOMAIN,
            payload,
        ),
    }


__all__ = ("build_owned_sequence_cross_family_campaign_document_v127", "build_owned_sequence_cross_family_occurrence_v127")
