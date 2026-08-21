"""Matched dependency-derived versus unconditional cross-epoch reuse V117."""

from __future__ import annotations

import copy
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v117 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_cross_epoch_program_branch_sequence_v116 import (
    run_cross_epoch_program_branch_sequence_v116,
)
from acfqp.generic_dependency_derived_program_branch_sequence_v117 import (
    program_branch_cache_retention_decision_v117,
    run_dependency_derived_program_branch_sequence_v117,
)


def _dependency_change_control(receipt: Mapping[str, Any]) -> dict[str, Any]:
    changed = copy.deepcopy(dict(receipt))
    payload = {
        key: value for key, value in changed.items() if key != "dependency_receipt_id"
    }
    payload["canonical_action_catalogue"][0]["canonical_anonymous_fields"][0] += 1
    changed = {
        **payload,
        "dependency_receipt_id": domains.extension_content_id_v117(
            domains.CONSTRUCTION_K7_PROGRAM_BRANCH_DEPENDENCY_RECEIPT_V117_DOMAIN,
            payload,
        ),
    }
    decision = program_branch_cache_retention_decision_v117(receipt, changed)
    return {
        "schema": "acfqp.program_branch_dependency_change_control.v117",
        "changed_dependency_receipt_id": changed["dependency_receipt_id"],
        "different_from_observed_receipt": changed["dependency_receipt_id"]
        != receipt["dependency_receipt_id"],
        "cache_retention_authorized": decision["retain_program_branch_cache"],
        "cache_invalidation_required": decision["invalidate_program_branch_cache"],
        "ground_outcome_executed_for_negative_control": False,
    }


def build_dependency_derived_program_branch_occurrence_v117(
    config: Mapping[str, Any],
    *,
    family: str,
    seed: int,
    episode_indices: tuple[int, ...],
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    adapter = base.predecessor.predecessor.prior_ground._adapter(  # noqa: SLF001
        family, seed, config
    )
    acquisition = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    common = {
        "episode_indices": episode_indices,
        "maximum_abstract_depth": config["maximum_abstract_depth"],
        "maximum_execution_steps": config["maximum_execution_steps"],
        "maximum_incremental_certificate_ground_support_labels": 100_000,
    }
    dependency = run_dependency_derived_program_branch_sequence_v117(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        **common,
    )
    dependency_base = dependency["dependency_derived_program_branch_base_sequence"]
    matched = run_cross_epoch_program_branch_sequence_v116(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        **common,
    )
    matched_base = matched["cross_epoch_program_branch_base_sequence"]
    exact = dependency_base == matched_base
    control = _dependency_change_control(
        dependency["program_branch_dependency_receipt"]
    )
    accounting = {
        "initial_acquisition_labels": dependency_base[
            "initial_acquisition_ground_support_labels_paid_once"
        ],
        "certificate_local_labels": dependency_base[
            "certificate_ground_support_labels_paid_once"
        ],
        "dependency_derived_lifetime_target_labels": dependency_base[
            "lifetime_target_ground_support_labels"
        ],
        "matched_v116_lifetime_target_labels": matched_base[
            "lifetime_target_ground_support_labels"
        ],
        "execution_steps": dependency_base["execution_step_count"],
        "dependency_derived_planning_compute_events": dependency[
            "actual_new_abstract_planning_compute_events"
        ],
        "matched_v116_planning_compute_events": matched[
            "actual_new_abstract_planning_compute_events"
        ],
        "matched_uncached_v113_planning_compute_events": dependency[
            "matched_uncached_abstract_planning_compute_events"
        ],
        "planning_compute_events_avoided_against_uncached_v113": dependency[
            "planning_compute_events_avoided_against_uncached"
        ],
        "dependency_derived_program_branch_cache_hits": dependency[
            "program_branch_cache_hit_count"
        ],
        "matched_v116_program_branch_cache_hits": matched[
            "cross_epoch_program_branch_cache_hit_count"
        ],
        "dependency_receipt_rederivation_count": dependency[
            "dependency_receipt_rederivation_count"
        ],
        "dependency_derivation_compute_events": dependency[
            "dependency_derivation_compute_events"
        ],
        "model_epoch_transition_count": dependency[
            "model_epoch_transition_count"
        ],
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "dependency_derived_and_v116_sequences_byte_exact": exact,
        "dependency_derived_and_v116_target_labels_equal": accounting[
            "dependency_derived_lifetime_target_labels"
        ]
        == accounting["matched_v116_lifetime_target_labels"],
        "dependency_derived_and_v116_planning_compute_equal": accounting[
            "dependency_derived_planning_compute_events"
        ]
        == accounting["matched_v116_planning_compute_events"],
        "dependency_receipt_rederived_at_every_episode": accounting[
            "dependency_receipt_rederivation_count"
        ]
        == len(episode_indices),
        "dependency_receipt_stable_across_model_epochs": dependency[
            "dependency_receipt_stable_across_model_epochs"
        ],
        "changed_dependency_forces_cache_invalidation_without_outcome_execution": control[
            "different_from_observed_receipt"
        ]
        and control["cache_retention_authorized"] is False
        and control["cache_invalidation_required"] is True
        and control["ground_outcome_executed_for_negative_control"] is False,
        "certificate_failure_only_query_discipline_clean": dependency_base[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "incremental_model_still_matches_full_v105_rebuild": dependency_base[
            "all_model_successors_exactly_equal_full_v105_rebuild"
        ],
        "planner_still_consumes_compiled_model_without_raw_rows": dependency_base[
            "planner_consumed_compiled_successor_without_raw_transition_argument"
        ],
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.dependency_derived_program_branch_occurrence.v117",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "partial_acquisition": acquisition["document"],
        "dependency_derived_program_branch_sequence": dependency,
        "dependency_derived_program_branch_sequence_id": dependency["sequence_id"],
        "matched_v116_cross_epoch_sequence": matched,
        "matched_v116_cross_epoch_sequence_id": matched["sequence_id"],
        "dependency_change_no_outcome_control": control,
        "accounting": accounting,
        "registered_gate": gate,
        "dependency_derived_branch_retention_verified": gate["passed"],
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
        "occurrence_id": domains.extension_content_id_v117(
            domains.CONSTRUCTION_K7_DEPENDENCY_DERIVED_BRANCH_OCCURRENCE_V117_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_dependency_derived_program_branch_occurrence_v117(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        factor_library=args[4],
    )


def build_dependency_derived_program_branch_campaign_document_v117(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v116_campaign_id: str,
    v116_verification_id: str,
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    args = [
        (
            config,
            row["family"],
            row["seed"],
            tuple(config["target_episode_indices"]),
            factor_library,
        )
        for row in config["target_occurrences"]
    ]
    if config["target_worker_count"] == 1:
        occurrences = [_target(row) for row in args]
    else:
        with ProcessPoolExecutor(
            max_workers=config["target_worker_count"]
        ) as executor:
            occurrences = list(executor.map(_target, args))
    keys = tuple(occurrences[0]["accounting"])
    numeric = {
        key: sum(row["accounting"][key] for row in occurrences)
        for key in keys
        if type(occurrences[0]["accounting"][key]) is int
    }
    family_counts = {
        family: sum(row["target_family"] == family for row in occurrences)
        for family in config["required_target_families"]
    }
    ood = incompatible_schema_no_transfer_control_v99()
    passed = (
        all(row["registered_gate"]["passed"] for row in occurrences)
        and all(family_counts.values())
        and numeric["dependency_derived_planning_compute_events"]
        == numeric["matched_v116_planning_compute_events"]
        and ood["strict_ood_no_transfer"] is True
    )
    gate = {
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] for row in occurrences
        ),
        "required_target_family_counts": family_counts,
        "all_three_registered_structural_families_present": all(
            family_counts.values()
        ),
        "every_occurrence_matches_v116_sequence_bytes_and_compute": all(
            row["registered_gate"][
                "dependency_derived_and_v116_sequences_byte_exact"
            ]
            and row["registered_gate"][
                "dependency_derived_and_v116_planning_compute_equal"
            ]
            for row in occurrences
        ),
        "every_occurrence_rederives_exact_dependency_and_rejects_changed_dependency": all(
            row["registered_gate"]["dependency_receipt_rederived_at_every_episode"]
            and row["registered_gate"][
                "changed_dependency_forces_cache_invalidation_without_outcome_execution"
            ]
            for row in occurrences
        ),
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    accounting = {
        **numeric,
        "offline_source_labels_not_recharged": True,
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.dependency_derived_program_branch_campaign.v117",
        "preregistration_id": preregistration_id,
        "v116_success_campaign_id": v116_campaign_id,
        "v116_success_verification_id": v116_verification_id,
        "target_occurrences": occurrences,
        "target_occurrence_ids": [row["occurrence_id"] for row in occurrences],
        "incompatible_schema_no_transfer_control": ood,
        "accounting": accounting,
        "registered_gate": gate,
        "registered_dependency_derived_branch_retention_verified": passed,
        "ground_distinctions_only_after_certificate_failure_verified": passed,
        "compiled_model_cache_or_receipt_used_as_safety_authority": False,
        "global_lumpability_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v117(
            domains.CONSTRUCTION_K7_DEPENDENCY_DERIVED_BRANCH_CAMPAIGN_V117_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_dependency_derived_program_branch_campaign_document_v117",
    "build_dependency_derived_program_branch_occurrence_v117",
)
