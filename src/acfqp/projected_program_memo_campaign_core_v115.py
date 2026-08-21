"""Matched projected-program memoization campaign core V115."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v115 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_incremental_abstract_successor_sequence_v113 import (
    run_incremental_abstract_successor_sequence_v113,
)
from acfqp.generic_projected_program_memo_sequence_v115 import (
    run_projected_program_memo_sequence_v115,
)


def build_projected_program_memo_occurrence_v115(
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
    memo = run_projected_program_memo_sequence_v115(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        **common,
    )
    sequence = memo["program_memoized_base_sequence"]
    matched = run_incremental_abstract_successor_sequence_v113(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        **common,
    )
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
    exact = all(sequence[key] == matched[key] for key in exact_keys) and all(
        all(left[key] == right[key] for key in episode_exact_keys)
        for left, right in zip(
            sequence["episodes"], matched["episodes"], strict=True
        )
    )
    memo_compute = memo["actual_new_abstract_planning_compute_events"]
    baseline_compute = matched["actual_new_abstract_planning_compute_events"]
    accounting = {
        "initial_acquisition_labels": sequence[
            "initial_acquisition_ground_support_labels_paid_once"
        ],
        "certificate_local_labels": sequence[
            "certificate_ground_support_labels_paid_once"
        ],
        "projected_program_memo_lifetime_target_labels": sequence[
            "lifetime_target_ground_support_labels"
        ],
        "matched_v113_lifetime_target_labels": matched[
            "lifetime_target_ground_support_labels"
        ],
        "execution_steps": sequence["execution_step_count"],
        "projected_program_memo_planning_compute_events": memo_compute,
        "matched_v113_planning_compute_events": baseline_compute,
        "matched_uncached_abstract_planning_compute_events": memo[
            "matched_uncached_abstract_planning_compute_events"
        ],
        "planning_compute_events_avoided_by_program_memo": baseline_compute
        - memo_compute,
        "projected_program_whole_plan_memo_hits": memo[
            "projected_program_memo_hit_count"
        ],
        "projected_program_branch_cache_hits": memo[
            "projected_program_branch_cache_hit_count"
        ],
        "model_epoch_identity_checks": sequence[
            "model_epoch_identity_checks"
        ],
        "full_model_epoch_diff_checks": sequence[
            "full_model_epoch_diff_checks"
        ],
        "reverse_dependency_index_lookups": sequence[
            "reverse_dependency_index_lookups"
        ],
        "dependency_maintenance_events": sequence[
            "dependency_maintenance_events"
        ],
        "incremental_model_update_compilation_events": sequence[
            "incremental_model_update_compilation_events"
        ],
        "matched_full_rebuild_update_compilation_events": sequence[
            "matched_full_rebuild_update_compilation_events"
        ],
        "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "memo_and_v113_actions_certificates_overlays_models_and_execution_equal": exact,
        "memo_and_v113_target_labels_equal": accounting[
            "projected_program_memo_lifetime_target_labels"
        ]
        == accounting["matched_v113_lifetime_target_labels"],
        "memo_uncached_compute_reconstructs_v113_compute": accounting[
            "matched_uncached_abstract_planning_compute_events"
        ]
        == baseline_compute,
        "projected_program_branch_cache_hit_observed": accounting[
            "projected_program_branch_cache_hits"
        ]
        > 0,
        "projected_program_memo_planning_compute_strictly_below_v113": memo_compute
        < baseline_compute,
        "certificate_failure_only_query_discipline_clean": sequence[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "incremental_model_still_matches_full_v105_rebuild": sequence[
            "all_model_successors_exactly_equal_full_v105_rebuild"
        ],
        "planner_still_consumes_compiled_model_without_raw_rows": sequence[
            "planner_consumed_compiled_successor_without_raw_transition_argument"
        ],
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.projected_program_memo_occurrence.v115",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "partial_acquisition": acquisition["document"],
        "projected_program_memo_sequence": memo,
        "projected_program_memo_sequence_id": memo["sequence_id"],
        "matched_v113_incremental_sequence": matched,
        "matched_v113_incremental_sequence_id": matched["sequence_id"],
        "accounting": accounting,
        "registered_gate": gate,
        "projected_program_memoization_verified": gate["passed"],
        "ground_distinctions_only_after_certificate_failure_verified": gate[
            "passed"
        ],
        "compiled_model_or_memo_used_as_safety_authority": False,
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
        "occurrence_id": domains.extension_content_id_v115(
            domains.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_OCCURRENCE_V115_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_projected_program_memo_occurrence_v115(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        factor_library=args[4],
    )


def build_projected_program_memo_campaign_document_v115(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v114_campaign_id: str,
    v114_verification_id: str,
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
        and numeric["projected_program_branch_cache_hits"] > 0
        and numeric["projected_program_memo_planning_compute_events"]
        < numeric["matched_v113_planning_compute_events"]
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
        "every_occurrence_matches_v113_actions_certificates_models_and_execution": all(
            row["registered_gate"][
                "memo_and_v113_actions_certificates_overlays_models_and_execution_equal"
            ]
            for row in occurrences
        ),
        "every_occurrence_observes_program_branch_reuse": all(
            row["registered_gate"][
                "projected_program_branch_cache_hit_observed"
            ]
            for row in occurrences
        ),
        "every_occurrence_planning_compute_below_v113": all(
            row["registered_gate"][
                "projected_program_memo_planning_compute_strictly_below_v113"
            ]
            for row in occurrences
        ),
        "aggregate_planning_compute_below_v113": numeric[
            "projected_program_memo_planning_compute_events"
        ]
        < numeric["matched_v113_planning_compute_events"],
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    payload = {
        "schema": "acfqp.projected_program_memo_campaign.v115",
        "preregistration_id": preregistration_id,
        "v114_success_campaign_id": v114_campaign_id,
        "v114_success_verification_id": v114_verification_id,
        "target_occurrences": occurrences,
        "incompatible_schema_no_transfer_control": ood,
        "accounting": {
            **numeric,
            "offline_source_labels_not_recharged": True,
            "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": gate,
        "registered_projected_program_memoization_verified": passed,
        "ground_distinctions_only_after_certificate_failure_verified": passed,
        "compiled_model_or_memo_used_as_safety_authority": False,
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
        "campaign_id": domains.extension_content_id_v115(
            domains.CONSTRUCTION_K7_PROJECTED_PROGRAM_MEMO_CAMPAIGN_V115_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_projected_program_memo_campaign_document_v115",
    "build_projected_program_memo_occurrence_v115",
)
