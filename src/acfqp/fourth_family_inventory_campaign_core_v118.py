"""Fourth-family inventory transfer through the V117 abstract pipeline."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v118 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as acquisition
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_cross_epoch_program_branch_sequence_v116 import (
    run_cross_epoch_program_branch_sequence_v116,
)
from acfqp.generic_dependency_derived_program_branch_sequence_v117 import (
    run_dependency_derived_program_branch_sequence_v117,
)
from acfqp.generic_inventory_assembly_adapter_v118 import (
    FAMILY,
    build_inventory_assembly_adapter_v118,
)


def build_fourth_family_inventory_occurrence_v118(
    config: Mapping[str, Any],
    *,
    seed: int,
    episode_indices: tuple[int, ...],
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    adapter = build_inventory_assembly_adapter_v118(seed, config)
    acquired = acquisition.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )
    prior = acquired["ANONYMOUS_FACTOR_PRIOR_ON"]
    no_prior = acquired["STRICT_NO_PRIOR"]
    common = {
        "episode_indices": episode_indices,
        "maximum_abstract_depth": config["maximum_abstract_depth"],
        "maximum_execution_steps": config["maximum_execution_steps"],
        "maximum_incremental_certificate_ground_support_labels": 100_000,
    }
    derived = run_dependency_derived_program_branch_sequence_v117(
        adapter,
        prior["candidate"],
        prior["rows"],
        prior["document"]["ground_support_labels"],
        **common,
    )
    matched = run_cross_epoch_program_branch_sequence_v116(
        adapter,
        prior["candidate"],
        prior["rows"],
        prior["document"]["ground_support_labels"],
        **common,
    )
    derived_base = derived["dependency_derived_program_branch_base_sequence"]
    matched_base = matched["cross_epoch_program_branch_base_sequence"]
    prior_labels = prior["document"]["ground_support_labels"]
    no_prior_labels = no_prior["document"]["ground_support_labels"]
    common_batch_count = min(len(prior["batches"]), len(no_prior["batches"]))
    prior_common_prefix = tuple(
        row
        for batch in prior["batches"][:common_batch_count]
        for row in batch
    )
    no_prior_common_prefix = tuple(
        row
        for batch in no_prior["batches"][:common_batch_count]
        for row in batch
    )
    accounting = {
        "prior_on_acquisition_labels": prior_labels,
        "strict_no_prior_acquisition_labels": no_prior_labels,
        "prior_minus_no_prior_acquisition_labels": prior_labels - no_prior_labels,
        "certificate_local_labels": derived_base[
            "certificate_ground_support_labels_paid_once"
        ],
        "lifetime_target_labels": derived_base[
            "lifetime_target_ground_support_labels"
        ],
        "execution_steps": derived_base["execution_step_count"],
        "abstract_planning_compute_events": derived[
            "actual_new_abstract_planning_compute_events"
        ],
        "matched_uncached_planning_compute_events": derived[
            "matched_uncached_abstract_planning_compute_events"
        ],
        "planning_compute_events_avoided_against_uncached": derived[
            "planning_compute_events_avoided_against_uncached"
        ],
        "dependency_derivation_compute_events": derived[
            "dependency_derivation_compute_events"
        ],
        "program_branch_cache_hits": derived["program_branch_cache_hit_count"],
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "fresh_inventory_family_not_in_v117_three_family_campaign": FAMILY
        not in {
            "BALANCED_BATCH_REFINEMENT",
            "COUPLED_EXCHANGE",
            "MAINTENANCE_CASCADE",
        },
        "matched_prior_and_no_prior_use_identical_witness_blind_prefix": (
            prior_common_prefix == no_prior_common_prefix
        ),
        "both_acquisition_arms_terminate_with_candidates": prior["candidate"]
        is not None
        and no_prior["candidate"] is not None,
        "dependency_derived_and_v116_sequences_byte_exact": derived_base
        == matched_base,
        "all_receding_abstract_episodes_succeed": all(
            row["success"] for row in derived_base["episodes"]
        ),
        "certificate_failure_only_query_discipline_clean": derived_base[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "incremental_model_matches_full_v105_rebuild": derived_base[
            "all_model_successors_exactly_equal_full_v105_rebuild"
        ],
        "planner_consumes_compiled_model_without_raw_rows": derived_base[
            "planner_consumed_compiled_successor_without_raw_transition_argument"
        ],
        "sample_tax_sign_excluded_from_construction_gate": True,
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.fourth_family_inventory_occurrence.v118",
        "target_family": FAMILY,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "prior_on_partial_acquisition": prior["document"],
        "strict_no_prior_acquisition": no_prior["document"],
        "dependency_derived_program_branch_sequence": derived,
        "dependency_derived_program_branch_sequence_id": derived["sequence_id"],
        "matched_v116_cross_epoch_sequence": matched,
        "matched_v116_cross_epoch_sequence_id": matched["sequence_id"],
        "accounting": accounting,
        "registered_gate": gate,
        "fourth_family_abstract_world_model_pipeline_verified": gate["passed"],
        "sample_efficiency_improvement_claimed": False,
        "factor_library_contains_historical_related_schema_sources": True,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "ground_distinctions_only_after_certificate_failure_verified": gate[
            "passed"
        ],
        "compiled_model_cache_or_receipt_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v118(
            domains.CONSTRUCTION_K7_FOURTH_FAMILY_INVENTORY_OCCURRENCE_V118_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_fourth_family_inventory_occurrence_v118(
        args[0],
        seed=args[1],
        episode_indices=args[2],
        factor_library=args[3],
    )


def build_fourth_family_inventory_campaign_document_v118(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v117_campaign_id: str,
    v117_verification_id: str,
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    args = [
        (
            config,
            row["seed"],
            tuple(config["target_episode_indices"]),
            factor_library,
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
        "fresh_inventory_family_present": all(
            row["target_family"] == FAMILY for row in rows
        ),
        "every_occurrence_completes_receding_abstract_planning": all(
            row["registered_gate"]["all_receding_abstract_episodes_succeed"]
            for row in rows
        ),
        "every_occurrence_matches_dependency_guarded_and_v116_sequences": all(
            row["registered_gate"][
                "dependency_derived_and_v116_sequences_byte_exact"
            ]
            for row in rows
        ),
        "sample_tax_sign_excluded_and_reported_without_selection": True,
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    accounting = {
        **numeric,
        "offline_factor_library_labels_not_recharged": True,
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "sample_efficiency_improvement_claimed": False,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.fourth_family_inventory_campaign.v118",
        "preregistration_id": preregistration_id,
        "v117_success_campaign_id": v117_campaign_id,
        "v117_success_verification_id": v117_verification_id,
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "incompatible_schema_no_transfer_control": ood,
        "accounting": accounting,
        "registered_gate": gate,
        "registered_fourth_family_abstract_world_model_pipeline_verified": passed,
        "factor_library_contains_historical_related_schema_sources": True,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "ground_distinctions_only_after_certificate_failure_verified": passed,
        "compiled_model_cache_or_receipt_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v118(
            domains.CONSTRUCTION_K7_FOURTH_FAMILY_INVENTORY_CAMPAIGN_V118_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_fourth_family_inventory_campaign_document_v118",
    "build_fourth_family_inventory_occurrence_v118",
)
