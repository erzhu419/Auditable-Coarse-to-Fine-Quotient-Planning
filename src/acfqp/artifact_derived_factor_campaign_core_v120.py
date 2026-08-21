"""Fresh-target campaign using an artifact-derived anonymous factor library."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v120 as domains
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.artifact_derived_partial_acquisition_v120 import (
    acquire_artifact_derived_partial_model_v120,
)
from acfqp.generic_dual_budget_adapter_v119 import FAMILY, build_dual_budget_adapter_v119
from acfqp.generic_genesis_authorized_program_branch_sequence_v119 import (
    run_genesis_authorized_program_branch_sequence_v119,
)


def build_artifact_derived_factor_occurrence_v120(
    config: Mapping[str, Any],
    *,
    seed: int,
    episode_indices: tuple[int, ...],
    artifact_factor_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
    strict_complete_factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    adapter = build_dual_budget_adapter_v119(seed, config)
    acquired = acquire_artifact_derived_partial_model_v120(
        adapter,
        artifact_factor_library,
        source_campaign_bytes,
        strict_complete_factor_library,
        config,
    )
    partial = acquired["partial"]
    strict = acquired["strict_control"]["document"]
    sequence = run_genesis_authorized_program_branch_sequence_v119(
        adapter,
        partial["candidate"],
        partial["rows"],
        partial["document"]["ground_support_labels"],
        episode_indices=episode_indices,
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    base = sequence["genesis_authorized_base_sequence"]
    candidate = partial["candidate"].public_document
    partial_document = partial["document"]
    accounting = {
        "partial_prior_acquisition_labels": partial_document[
            "ground_support_labels"
        ],
        "strict_control_matched_prefix_labels": strict["ground_support_labels"],
        "strict_complete_model_attempt_count": strict["attempt_count"],
        "certificate_local_labels": base[
            "certificate_ground_support_labels_paid_once"
        ],
        "lifetime_target_labels": base["lifetime_target_ground_support_labels"],
        "execution_steps": base["execution_step_count"],
        "abstract_planning_compute_events": sequence[
            "actual_new_abstract_planning_compute_events"
        ],
        "matched_uncached_planning_compute_events": sequence[
            "matched_uncached_abstract_planning_compute_events"
        ],
        "planning_compute_events_avoided_against_uncached": sequence[
            "planning_compute_events_avoided_against_uncached"
        ],
        "dependency_derivation_compute_events": sequence[
            "dependency_derivation_compute_events"
        ],
        "same_epoch_genesis_authorized_cache_hits": sequence[
            "same_epoch_genesis_authorized_cache_hit_count"
        ],
        "program_branch_cache_hits": sequence["program_branch_cache_hit_count"],
        "artifact_library_derivation_candidate_documents": artifact_factor_library[
            "candidate_document_count"
        ],
        "sample_labels_execution_steps_derivation_planning_dependency_and_library_derivation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "fresh_dual_budget_identity_present": adapter.family == FAMILY,
        "candidate_uses_artifact_derived_factor_library": candidate[
            "source_factor_library_id"
        ]
        == artifact_factor_library["factor_library_id"],
        "hand_written_factor_template_count_zero": artifact_factor_library[
            "hand_written_factor_template_count"
        ]
        == 0,
        "three_cross_schema_subprograms_derived": len(
            artifact_factor_library["derived_subprograms"]
        )
        == 3,
        "factor_library_reconstructed_from_frozen_candidate_artifacts": artifact_factor_library[
            "projection_derived_only_from_frozen_candidate_artifacts"
        ],
        "partial_candidate_retains_unknown_higher_order_residual": bool(
            candidate["unknown_residual_target_columns"]
        ),
        "minimum_reusable_factor_count_derived": len(
            candidate["compiled_factor_assignments"]
        )
        >= config["minimum_reusable_factor_count"],
        "strict_control_uses_exact_partial_raw_prefix": strict[
            "ground_support_labels"
        ]
        == partial_document["ground_support_labels"]
        and strict["raw_transition_sha256"]
        == partial_document["raw_transition_sha256"],
        "strict_control_outcome_retained_without_selection": strict[
            "outcome_kind"
        ]
        in {
            "COMPLETE_CANDIDATE_SYNTHESIZED",
            "NO_COMPLETE_CANDIDATE_WITHIN_FROZEN_GRAMMAR",
        },
        "same_epoch_genesis_authorization_observed": sequence[
            "same_epoch_genesis_authorized_cache_hit_count"
        ]
        > 0,
        "all_receding_abstract_episodes_succeed": all(
            row["success"] for row in base["episodes"]
        ),
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
        "schema": "acfqp.artifact_derived_factor_occurrence.v120",
        "target_family": FAMILY,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "artifact_factor_library": artifact_factor_library,
        "artifact_factor_library_id": artifact_factor_library["factor_library_id"],
        "partial_prior_acquisition": partial_document,
        "strict_no_prior_complete_model_control": strict,
        "genesis_authorized_program_branch_sequence": sequence,
        "genesis_authorized_program_branch_sequence_id": sequence["sequence_id"],
        "accounting": accounting,
        "registered_gate": gate,
        "artifact_derived_partial_world_model_pipeline_verified": gate["passed"],
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
        "occurrence_id": domains.extension_content_id_v120(
            domains.CONSTRUCTION_K7_ARTIFACT_DERIVED_FACTOR_OCCURRENCE_V120_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_artifact_derived_factor_occurrence_v120(
        args[0],
        seed=args[1],
        episode_indices=args[2],
        artifact_factor_library=args[3],
        source_campaign_bytes=args[4],
        strict_complete_factor_library=args[5],
    )


def build_artifact_derived_factor_campaign_document_v120(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v119_campaign_id: str,
    v119_verification_id: str,
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
        with ProcessPoolExecutor(
            max_workers=config["target_worker_count"]
        ) as executor:
            rows = list(executor.map(_target, args))
    keys = tuple(rows[0]["accounting"])
    numeric = {
        key: sum(row["accounting"][key] for row in rows)
        for key in keys
        if type(rows[0]["accounting"][key]) is int
    }
    ood = incompatible_schema_no_transfer_control_v99()
    passed = (
        len(rows) == config["required_target_occurrence_count"]
        and all(row["registered_gate"]["passed"] for row in rows)
        and ood["strict_ood_no_transfer"] is True
    )
    gate = {
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in rows
        ),
        "artifact_factor_library_shared_exactly_across_occurrences": len(
            {row["artifact_factor_library_id"] for row in rows}
        )
        == 1,
        "hand_written_factor_template_count_zero": all(
            row["registered_gate"]["hand_written_factor_template_count_zero"]
            for row in rows
        ),
        "every_occurrence_retains_unknown_residual_and_completes_planning": all(
            row["registered_gate"][
                "partial_candidate_retains_unknown_higher_order_residual"
            ]
            and row["registered_gate"]["all_receding_abstract_episodes_succeed"]
            for row in rows
        ),
        "same_epoch_genesis_authorization_verified": all(
            row["registered_gate"]["same_epoch_genesis_authorization_observed"]
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
        "historical_artifact_labels_not_recharged_to_target": True,
        "sample_labels_execution_steps_derivation_planning_dependency_and_library_derivation_separate": True,
        "sample_efficiency_improvement_claimed": False,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.artifact_derived_factor_campaign.v120",
        "preregistration_id": preregistration_id,
        "v119_success_campaign_id": v119_campaign_id,
        "v119_success_verification_id": v119_verification_id,
        "artifact_factor_library_id": artifact_factor_library["factor_library_id"],
        "artifact_factor_library": artifact_factor_library,
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": ood,
        "accounting": accounting,
        "registered_gate": gate,
        "registered_artifact_derived_partial_world_model_pipeline_verified": passed,
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
        "campaign_id": domains.extension_content_id_v120(
            domains.CONSTRUCTION_K7_ARTIFACT_DERIVED_FACTOR_CAMPAIGN_V120_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_artifact_derived_factor_campaign_document_v120",
    "build_artifact_derived_factor_occurrence_v120",
)
