"""Campaign using the standalone V125 model-epoch carrier."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v125 as domains
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import incompatible_schema_no_transfer_control_v99
from acfqp.generic_artifact_subprogram_acquisition_v121 import acquire_generic_artifact_subprogram_model_v121
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY, build_inventory_assembly_adapter_v118
from acfqp.standalone_generic_model_sequence_v125 import run_standalone_generic_model_sequence_v125


def build_standalone_generic_model_occurrence_v125(
    config: Mapping[str, Any],
    *,
    seed: int,
    episode_indices: tuple[int, ...],
    artifact_factor_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
    strict_complete_factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    adapter = build_inventory_assembly_adapter_v118(seed, config)
    acquired = acquire_generic_artifact_subprogram_model_v121(
        adapter, artifact_factor_library, source_campaign_bytes, strict_complete_factor_library, config
    )
    partial, strict = acquired["partial"], acquired["strict_control"]["document"]
    sequence = run_standalone_generic_model_sequence_v125(
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
    acquisition = partial["document"]
    reconstruction = sequence["standalone_generic_model_reconstruction"]
    accounting = {
        "partial_prior_acquisition_labels": acquisition["ground_support_labels"],
        "strict_control_matched_prefix_labels": strict["ground_support_labels"],
        "strict_complete_model_attempt_count": strict["attempt_count"],
        "certificate_local_labels": base["certificate_ground_support_labels_paid_once"],
        "lifetime_target_labels": base["lifetime_target_ground_support_labels"],
        "execution_steps": base["execution_step_count"],
        "abstract_planning_compute_events": v119["actual_new_abstract_planning_compute_events"],
        "matched_uncached_planning_compute_events": v119["matched_uncached_abstract_planning_compute_events"],
        "planning_compute_events_avoided_against_uncached": v119["planning_compute_events_avoided_against_uncached"],
        "dependency_derivation_compute_events": v119["dependency_derivation_compute_events"],
        "standalone_model_epoch_reconstructions": reconstruction["generic_model_epoch_reconstruction_count"],
        "generic_model_program_support_checks": reconstruction["generic_model_program_support_checks"],
        "direct_generic_factor_program_plans": sequence["direct_generic_factor_program_plan_count"],
        "sample_labels_execution_steps_derivation_planning_and_model_checks_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "fresh_inventory_identity_present": adapter.family == FAMILY,
        "candidate_uses_artifact_derived_factor_library": partial["candidate"].public_document["source_factor_library_id"] == artifact_factor_library["factor_library_id"],
        "partial_candidate_retains_unknown_residual": bool(partial["candidate"].public_document["unknown_residual_target_columns"]),
        "strict_control_uses_exact_partial_raw_prefix": strict["ground_support_labels"] == acquisition["ground_support_labels"] and strict["raw_transition_sha256"] == acquisition["raw_transition_sha256"],
        "all_receding_episodes_succeed": all(row["success"] for row in base["episodes"]),
        "standalone_v125_state_carrier_verified": sequence["standalone_v125_state_carrier_verified"],
        "retained_v113_state_carrier_absent": sequence["retained_v113_state_carrier_present"] is False,
        "all_state_and_update_receipts_use_v125_domains": reconstruction["all_state_and_update_receipts_use_v125_domains"],
        "legacy_model_builder_not_called": sequence["legacy_shape_specific_model_builder_called"] is False,
        "generic_program_fallback_exercised": sequence["direct_generic_factor_program_plan_count"] > 0,
        "certificate_failure_only_query_discipline_clean": base["every_new_ground_query_followed_a_failed_certificate"],
        "planner_consumes_compiled_model_without_raw_rows": base["planner_consumed_compiled_successor_without_raw_transition_argument"],
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.standalone_generic_model_occurrence.v125",
        "target_family": FAMILY,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "artifact_factor_library_id": artifact_factor_library["factor_library_id"],
        "partial_prior_acquisition": acquisition,
        "strict_no_prior_complete_model_control": strict,
        "standalone_generic_model_sequence": sequence,
        "standalone_generic_model_sequence_id": sequence["sequence_id"],
        "accounting": accounting,
        "registered_gate": gate,
        "registered_standalone_generic_model_verified": gate["passed"],
        "retained_v113_state_carrier_present": False,
        "retained_v113_sequence_orchestration_present": True,
        "legacy_shape_specific_model_builder_called": False,
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
    return {**payload, "occurrence_id": domains.extension_content_id_v125(domains.CONSTRUCTION_K7_STANDALONE_GENERIC_MODEL_OCCURRENCE_V125_DOMAIN, payload)}


def _target(args):
    return build_standalone_generic_model_occurrence_v125(args[0], seed=args[1], episode_indices=args[2], artifact_factor_library=args[3], source_campaign_bytes=args[4], strict_complete_factor_library=args[5])


def build_standalone_generic_model_campaign_document_v125(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v124_campaign_id: str,
    v124_verification_id: str,
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
        "standalone_v125_state_carrier_used_in_every_occurrence": all(row["registered_standalone_generic_model_verified"] for row in rows),
        "retained_v113_state_carrier_absent_in_every_occurrence": all(row["retained_v113_state_carrier_present"] is False for row in rows),
        "all_receding_episodes_succeed": all(ep["success"] for row in rows for ep in row["standalone_generic_model_sequence"]["generic_compiler_base_sequence"]["genesis_authorized_base_sequence"]["episodes"]),
        "strict_incompatible_schema_no_transfer_verified": ood["strict_ood_no_transfer"],
        "passed": passed,
    }
    payload = {
        "schema": "acfqp.standalone_generic_model_campaign.v125",
        "preregistration_id": preregistration_id,
        "v124_success_campaign_id": v124_campaign_id,
        "v124_success_verification_id": v124_verification_id,
        "artifact_factor_library_id": artifact_factor_library["factor_library_id"],
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": ood,
        "accounting": accounting,
        "registered_gate": gate,
        "registered_standalone_generic_model_verified": passed,
        "retained_v113_state_carrier_present": False,
        "retained_v113_sequence_orchestration_present": True,
        "legacy_shape_specific_model_builder_called": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "sample_efficiency_improvement_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {**payload, "campaign_id": domains.extension_content_id_v125(domains.CONSTRUCTION_K7_STANDALONE_GENERIC_MODEL_CAMPAIGN_V125_DOMAIN, payload)}


__all__ = ("build_standalone_generic_model_campaign_document_v125", "build_standalone_generic_model_occurrence_v125")
