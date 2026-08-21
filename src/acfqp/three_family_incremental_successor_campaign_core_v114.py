"""Fresh three-family transfer wrapper around the unchanged V113 compiler."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v114 as domains
from acfqp import incremental_abstract_successor_campaign_core_v113 as previous
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)


def build_three_family_incremental_successor_occurrence_v114(
    config: Mapping[str, Any],
    *,
    family: str,
    seed: int,
    episode_indices: tuple[int, ...],
    factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    raw = previous.build_incremental_abstract_successor_occurrence_v113(
        config,
        family=family,
        seed=seed,
        episode_indices=episode_indices,
        factor_library=factor_library,
    )
    accounting = copy.deepcopy(raw["accounting"])
    gate = {
        "unchanged_v113_incremental_successor_gate_passed": raw[
            "registered_gate"
        ]["passed"],
        "incremental_execution_exactly_matches_full_rebuild": raw[
            "registered_gate"
        ][
            "incremental_and_full_rebuild_actions_plans_receipts_labels_steps_equal"
        ],
        "incremental_model_exactly_matches_full_v105_rebuild": raw[
            "registered_gate"
        ]["every_incremental_model_exactly_matches_full_v105_rebuild"],
        "planner_consumes_compiled_model_without_raw_rows": raw[
            "registered_gate"
        ]["planner_consumes_compiled_model_without_raw_transition_argument"],
        "incremental_compilation_strictly_below_full_rebuild": accounting[
            "incremental_model_update_compilation_events"
        ]
        < accounting["matched_full_rebuild_update_compilation_events"],
        "certificate_failure_only_query_discipline_clean": raw[
            "registered_gate"
        ]["certificate_failure_only_query_discipline_clean"],
        "quotient_labels_strictly_below_cold_direct": accounting[
            "incremental_quotient_lifetime_target_labels"
        ]
        < accounting["cold_direct_lifetime_target_labels"],
    }
    gate["passed"] = all(gate.values())
    payload = {
        "schema": "acfqp.three_family_incremental_successor_occurrence.v114",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "v113_incremental_successor_occurrence": raw,
        "v113_incremental_successor_occurrence_id": raw["occurrence_id"],
        "accounting": accounting,
        "registered_gate": gate,
        "unchanged_incremental_compiler_and_planner_verified_on_target_family": gate[
            "passed"
        ],
        "compiled_model_used_as_safety_authority": False,
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
        "occurrence_id": domains.extension_content_id_v114(
            domains.CONSTRUCTION_K7_THREE_FAMILY_INCREMENTAL_SUCCESSOR_OCCURRENCE_V114_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_three_family_incremental_successor_occurrence_v114(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        factor_library=args[4],
    )


def build_three_family_incremental_successor_campaign_document_v114(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v113_campaign_id: str,
    v113_verification_id: str,
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
        and set(family_counts) == set(config["required_target_families"])
        and all(count > 0 for count in family_counts.values())
        and numeric["incremental_model_update_compilation_events"]
        < numeric["matched_full_rebuild_update_compilation_events"]
        and numeric["incremental_quotient_lifetime_target_labels"]
        < numeric["cold_direct_lifetime_target_labels"]
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
        "all_three_registered_structural_families_present": set(family_counts)
        == set(config["required_target_families"])
        and all(count > 0 for count in family_counts.values()),
        "every_occurrence_unchanged_v113_gate_passed": all(
            row["registered_gate"][
                "unchanged_v113_incremental_successor_gate_passed"
            ]
            for row in occurrences
        ),
        "every_occurrence_exactly_matches_full_rebuild": all(
            row["registered_gate"][
                "incremental_execution_exactly_matches_full_rebuild"
            ]
            for row in occurrences
        ),
        "every_occurrence_incremental_compilation_below_full_rebuild": all(
            row["registered_gate"][
                "incremental_compilation_strictly_below_full_rebuild"
            ]
            for row in occurrences
        ),
        "aggregate_incremental_compilation_below_full_rebuild": numeric[
            "incremental_model_update_compilation_events"
        ]
        < numeric["matched_full_rebuild_update_compilation_events"],
        "aggregate_quotient_labels_below_cold_direct": numeric[
            "incremental_quotient_lifetime_target_labels"
        ]
        < numeric["cold_direct_lifetime_target_labels"],
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    payload = {
        "schema": "acfqp.three_family_incremental_successor_campaign.v114",
        "preregistration_id": preregistration_id,
        "v113_success_campaign_id": v113_campaign_id,
        "v113_success_verification_id": v113_verification_id,
        "target_occurrences": occurrences,
        "incompatible_schema_no_transfer_control": ood,
        "accounting": {
            **numeric,
            "offline_source_labels_not_recharged": True,
            "sample_labels_execution_steps_derivation_planning_dependency_and_model_compilation_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": gate,
        "registered_three_family_incremental_successor_transfer_verified": passed,
        "ground_distinctions_acquired_only_after_certificate_failure_verified": passed,
        "algorithm_changed_from_v113": False,
        "compiled_model_used_as_safety_authority": False,
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
        "campaign_id": domains.extension_content_id_v114(
            domains.CONSTRUCTION_K7_THREE_FAMILY_INCREMENTAL_SUCCESSOR_CAMPAIGN_V114_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_three_family_incremental_successor_campaign_document_v114",
    "build_three_family_incremental_successor_occurrence_v114",
)
