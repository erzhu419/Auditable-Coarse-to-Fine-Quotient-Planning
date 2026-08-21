"""Matched cross-epoch versus per-epoch program-branch reuse core V116."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v116 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_cross_epoch_program_branch_sequence_v116 import (
    run_cross_epoch_program_branch_sequence_v116,
)
from acfqp.generic_projected_program_memo_sequence_v115 import (
    run_projected_program_memo_sequence_v115,
)


def build_cross_epoch_program_branch_occurrence_v116(
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
    cross = run_cross_epoch_program_branch_sequence_v116(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        **common,
    )
    cross_base = cross["cross_epoch_program_branch_base_sequence"]
    matched = run_projected_program_memo_sequence_v115(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        **common,
    )
    matched_base = matched["program_memoized_base_sequence"]
    exact_keys = (
        "all_failed_certificates",
        "all_local_distinctions",
        "persistent_exact_overlay_rows",
        "persistent_exact_overlay_sha256",
        "quotient_models_before_each_episode",
        "quotient_models_after_each_episode",
        "incremental_successor_update_receipts",
        "full_rebuild_match_receipts",
        "model_epoch_transition_receipts",
        "lifetime_target_ground_support_labels",
        "execution_step_count",
    )
    episode_exact_keys = (
        "action_keys",
        "abstract_execution_receipts",
        "raw_incremental_transition_rows",
        "failed_certificates",
        "local_distinctions",
        "incremental_certificate_local_ground_support_labels",
        "execution_steps",
        "success",
    )
    exact = all(cross_base[key] == matched_base[key] for key in exact_keys) and all(
        all(left[key] == right[key] for key in episode_exact_keys)
        for left, right in zip(
            cross_base["episodes"], matched_base["episodes"], strict=True
        )
    )
    cross_compute = cross["actual_new_abstract_planning_compute_events"]
    matched_compute = matched["actual_new_abstract_planning_compute_events"]
    accounting = {
        "initial_acquisition_labels": cross_base[
            "initial_acquisition_ground_support_labels_paid_once"
        ],
        "certificate_local_labels": cross_base[
            "certificate_ground_support_labels_paid_once"
        ],
        "cross_epoch_lifetime_target_labels": cross_base[
            "lifetime_target_ground_support_labels"
        ],
        "matched_v115_lifetime_target_labels": matched_base[
            "lifetime_target_ground_support_labels"
        ],
        "execution_steps": cross_base["execution_step_count"],
        "cross_epoch_planning_compute_events": cross_compute,
        "matched_v115_planning_compute_events": matched_compute,
        "matched_uncached_v113_planning_compute_events": cross[
            "matched_uncached_abstract_planning_compute_events"
        ],
        "planning_compute_events_avoided_against_v115": matched_compute
        - cross_compute,
        "planning_compute_events_avoided_against_uncached_v113": cross[
            "planning_compute_events_avoided_against_uncached"
        ],
        "cross_epoch_program_branch_cache_hits": cross[
            "cross_epoch_program_branch_cache_hit_count"
        ],
        "matched_v115_program_branch_cache_hits": matched[
            "projected_program_branch_cache_hit_count"
        ],
        "additional_cross_epoch_program_branch_cache_hits": cross[
            "cross_epoch_program_branch_cache_hit_count"
        ]
        - matched["projected_program_branch_cache_hit_count"],
        "model_epoch_identity_checks": cross_base["model_epoch_identity_checks"],
        "full_model_epoch_diff_checks": cross_base[
            "full_model_epoch_diff_checks"
        ],
        "reverse_dependency_index_lookups": cross_base[
            "reverse_dependency_index_lookups"
        ],
        "dependency_maintenance_events": cross_base[
            "dependency_maintenance_events"
        ],
        "incremental_model_update_compilation_events": cross_base[
            "incremental_model_update_compilation_events"
        ],
        "matched_full_rebuild_update_compilation_events": cross_base[
            "matched_full_rebuild_update_compilation_events"
        ],
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "cross_epoch_and_v115_actions_certificates_overlays_models_and_execution_equal": exact,
        "cross_epoch_and_v115_target_labels_equal": accounting[
            "cross_epoch_lifetime_target_labels"
        ]
        == accounting["matched_v115_lifetime_target_labels"],
        "cross_epoch_uncached_compute_reconstructs_v115_uncached_compute": cross[
            "matched_uncached_abstract_planning_compute_events"
        ]
        == matched["matched_uncached_abstract_planning_compute_events"],
        "additional_cross_epoch_branch_reuse_observed": accounting[
            "additional_cross_epoch_program_branch_cache_hits"
        ]
        > 0,
        "cross_epoch_planning_compute_not_above_v115": cross_compute
        <= matched_compute,
        "certificate_failure_only_query_discipline_clean": cross_base[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "incremental_model_still_matches_full_v105_rebuild": cross_base[
            "all_model_successors_exactly_equal_full_v105_rebuild"
        ],
        "planner_still_consumes_compiled_model_without_raw_rows": cross_base[
            "planner_consumed_compiled_successor_without_raw_transition_argument"
        ],
    }
    gate["passed"] = all(
        value
        for key, value in gate.items()
        if key != "additional_cross_epoch_branch_reuse_observed"
    )
    payload = {
        "schema": "acfqp.cross_epoch_program_branch_occurrence.v116",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "partial_acquisition": acquisition["document"],
        "cross_epoch_program_branch_sequence": cross,
        "cross_epoch_program_branch_sequence_id": cross["sequence_id"],
        "matched_v115_program_memo_sequence": matched,
        "matched_v115_program_memo_sequence_id": matched["sequence_id"],
        "accounting": accounting,
        "registered_gate": gate,
        "cross_epoch_program_branch_reuse_verified": gate["passed"],
        "ground_distinctions_only_after_certificate_failure_verified": gate[
            "passed"
        ],
        "compiled_model_or_cache_used_as_safety_authority": False,
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
        "occurrence_id": domains.extension_content_id_v116(
            domains.CONSTRUCTION_K7_CROSS_EPOCH_PROGRAM_BRANCH_OCCURRENCE_V116_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_cross_epoch_program_branch_occurrence_v116(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        factor_library=args[4],
    )


def build_cross_epoch_program_branch_campaign_document_v116(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v115_campaign_id: str,
    v115_verification_id: str,
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
        and numeric["additional_cross_epoch_program_branch_cache_hits"] > 0
        and numeric["cross_epoch_planning_compute_events"]
        < numeric["matched_v115_planning_compute_events"]
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
        "every_occurrence_matches_v115_actions_certificates_models_and_execution": all(
            row["registered_gate"][
                "cross_epoch_and_v115_actions_certificates_overlays_models_and_execution_equal"
            ]
            for row in occurrences
        ),
        "at_least_one_occurrence_observes_additional_cross_epoch_branch_reuse": any(
            row["registered_gate"][
                "additional_cross_epoch_branch_reuse_observed"
            ]
            for row in occurrences
        ),
        "every_occurrence_planning_compute_not_above_v115": all(
            row["registered_gate"][
                "cross_epoch_planning_compute_not_above_v115"
            ]
            for row in occurrences
        ),
        "aggregate_planning_compute_below_v115": numeric[
            "cross_epoch_planning_compute_events"
        ]
        < numeric["matched_v115_planning_compute_events"],
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    payload = {
        "schema": "acfqp.cross_epoch_program_branch_campaign.v116",
        "preregistration_id": preregistration_id,
        "v115_success_campaign_id": v115_campaign_id,
        "v115_success_verification_id": v115_verification_id,
        "target_occurrences": occurrences,
        "incompatible_schema_no_transfer_control": ood,
        "accounting": {
            **numeric,
            "offline_source_labels_not_recharged": True,
            "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": gate,
        "registered_cross_epoch_program_branch_reuse_verified": passed,
        "ground_distinctions_only_after_certificate_failure_verified": passed,
        "compiled_model_or_cache_used_as_safety_authority": False,
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
        "campaign_id": domains.extension_content_id_v116(
            domains.CONSTRUCTION_K7_CROSS_EPOCH_PROGRAM_BRANCH_CAMPAIGN_V116_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_cross_epoch_program_branch_campaign_document_v116",
    "build_cross_epoch_program_branch_occurrence_v116",
)
