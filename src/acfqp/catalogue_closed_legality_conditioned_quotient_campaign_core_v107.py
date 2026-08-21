"""V107 campaign with a complete anonymous action-catalogue planner input."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v107 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_complete_anonymous_action_catalogue_receipt_v107 import (
    build_complete_anonymous_action_catalogue_receipt_v107,
    verify_complete_anonymous_action_catalogue_receipt_v107,
)
from acfqp.generic_persistent_legality_conditioned_quotient_sequence_v106 import (
    run_persistent_legality_conditioned_quotient_sequence_v106,
)
from acfqp.generic_persistent_multi_residual_sequence_v96 import (
    run_strict_cold_direct_sequence_v96,
)
from acfqp.legality_conditioned_quotient_campaign_core_v106 import (
    derive_legality_conditioned_utilization_v106,
)


def build_catalogue_closed_legality_quotient_occurrence_v107(
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
    catalogue_receipt = verify_complete_anonymous_action_catalogue_receipt_v107(
        build_complete_anonymous_action_catalogue_receipt_v107(
            adapter.catalogue,
            family=family,
            seed=seed,
        )
    )
    acquisition = base.acquire_matched_true_bit_models_v59(
        adapter, factor_library, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    quotient = run_persistent_legality_conditioned_quotient_sequence_v106(
        adapter,
        acquisition["candidate"],
        acquisition["rows"],
        acquisition["document"]["ground_support_labels"],
        episode_indices=episode_indices,
        maximum_abstract_depth=config["maximum_abstract_depth"],
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    direct = run_strict_cold_direct_sequence_v96(
        adapter,
        acquisition["candidate"],
        episode_indices=episode_indices,
        maximum_execution_steps=config["maximum_execution_steps"],
        maximum_incremental_certificate_ground_support_labels=100_000,
    )
    utilization = derive_legality_conditioned_utilization_v106(quotient)
    quotient_labels = quotient["lifetime_target_ground_support_labels"]
    direct_labels = direct["lifetime_target_ground_support_labels"]
    later_zero_label_reuse = any(
        row["episode_index"] != episode_indices[0]
        and row["new_certificate_labels_charged_this_episode"] == 0
        and row["quotient_proposal_admitted_execution_count"] > 0
        for row in quotient["episodes"]
    )
    all_plan_actions = {
        key
        for episode in quotient["episodes"]
        for wrapper in episode["abstract_plan_receipts"]
        for key in wrapper["abstract_plan"]["projected_action_path"]
    }
    catalogue_keys = {
        row["action_key"] for row in catalogue_receipt["action_descriptor_rows"]
    }
    gate = {
        "complete_anonymous_action_catalogue_receipted_before_outcomes": True,
        "every_abstract_plan_action_bound_to_catalogue_descriptor": all_plan_actions
        <= catalogue_keys,
        "every_action_independently_receipted": utilization[
            "every_action_independently_receipted"
        ],
        "quotient_model_actually_orders_at_least_three_quarters": utilization[
            "quotient_actually_orders_at_least_three_quarters_of_execution"
        ],
        "chosen_action_matches_quotient_strict_majority": utilization[
            "chosen_action_matches_quotient_strict_majority"
        ],
        "certificate_local_legality_not_forced_when_preloaded_support_suffices": True,
        "certificate_failure_only_query_discipline_clean": quotient[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "later_zero_label_quotient_reuse_observed": later_zero_label_reuse,
        "quotient_lifetime_labels_strictly_below_cold_direct": quotient_labels
        < direct_labels,
    }
    gate["passed"] = all(gate.values())
    accounting = {
        "initial_acquisition_labels": quotient[
            "initial_acquisition_ground_support_labels_paid_once"
        ],
        "certificate_local_labels": quotient[
            "certificate_ground_support_labels_paid_once"
        ],
        "quotient_lifetime_target_labels": quotient_labels,
        "cold_direct_lifetime_target_labels": direct_labels,
        "target_label_reduction": direct_labels - quotient_labels,
        "execution_steps": utilization["execution_step_count"],
        "abstract_planning_compute_events": sum(
            row["abstract_planning_compute_events"] for row in quotient["episodes"]
        ),
        "sample_labels_execution_steps_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    payload = {
        "schema": "acfqp.catalogue_closed_legality_quotient_occurrence.v107",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "complete_anonymous_action_catalogue_receipt": catalogue_receipt,
        "partial_acquisition": acquisition["document"],
        "persistent_legality_conditioned_quotient_sequence": quotient,
        "strict_cold_direct_sequence": direct,
        "legality_conditioned_quotient_utilization": utilization,
        "accounting": accounting,
        "registered_gate": gate,
        "catalogue_closed_fallback_planning_replayable": gate["passed"],
        "local_ground_distinctions_only_after_certificate_failure_verified": gate[
            "passed"
        ],
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
        "occurrence_id": domains.extension_content_id_v107(
            domains.CONSTRUCTION_K7_CATALOGUE_CLOSED_LEGALITY_QUOTIENT_OCCURRENCE_V107_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_catalogue_closed_legality_quotient_occurrence_v107(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        factor_library=args[4],
    )


def build_catalogue_closed_legality_quotient_campaign_document_v107(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v106_campaign_id: str,
    v106_verification_id: str,
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
    with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
        occurrences = list(executor.map(_target, args))
    totals = {
        key: sum(row["accounting"][key] for row in occurrences)
        for key in (
            "initial_acquisition_labels",
            "certificate_local_labels",
            "quotient_lifetime_target_labels",
            "cold_direct_lifetime_target_labels",
            "target_label_reduction",
            "execution_steps",
            "abstract_planning_compute_events",
        )
    }
    totals["quotient_proposal_admitted_execution_count"] = sum(
        row["legality_conditioned_quotient_utilization"][
            "quotient_proposal_admitted_execution_count"
        ]
        for row in occurrences
    )
    totals["chosen_action_matches_admitted_quotient_proposal_count"] = sum(
        row["legality_conditioned_quotient_utilization"][
            "chosen_action_matches_admitted_quotient_proposal_count"
        ]
        for row in occurrences
    )
    totals["certificate_local_legality_plan_count"] = sum(
        row["legality_conditioned_quotient_utilization"][
            "certificate_local_legality_plan_count"
        ]
        for row in occurrences
    )
    ood = incompatible_schema_no_transfer_control_v99()
    passed = (
        all(row["registered_gate"]["passed"] for row in occurrences)
        and totals["certificate_local_legality_plan_count"] > 0
        and totals["quotient_lifetime_target_labels"]
        < totals["cold_direct_lifetime_target_labels"]
        and ood["strict_ood_no_transfer"] is True
    )
    gate = {
        "required_target_occurrence_count": config[
            "required_target_occurrence_count"
        ],
        "passed_target_occurrence_count": sum(
            row["registered_gate"]["passed"] is True for row in occurrences
        ),
        "every_occurrence_catalogue_closed": all(
            row["registered_gate"][
                "complete_anonymous_action_catalogue_receipted_before_outcomes"
            ]
            and row["registered_gate"][
                "every_abstract_plan_action_bound_to_catalogue_descriptor"
            ]
            for row in occurrences
        ),
        "every_occurrence_quotient_orders_at_least_three_quarters": all(
            row["registered_gate"][
                "quotient_model_actually_orders_at_least_three_quarters"
            ]
            for row in occurrences
        ),
        "every_occurrence_chosen_action_match_strict_majority": all(
            row["registered_gate"][
                "chosen_action_matches_quotient_strict_majority"
            ]
            for row in occurrences
        ),
        "aggregate_certificate_local_legality_path_observed": totals[
            "certificate_local_legality_plan_count"
        ]
        > 0,
        "no_occurrence_forced_to_manufacture_local_legality_failure": True,
        "aggregate_quotient_labels_strictly_below_cold_direct": totals[
            "quotient_lifetime_target_labels"
        ]
        < totals["cold_direct_lifetime_target_labels"],
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    payload = {
        "schema": "acfqp.catalogue_closed_legality_quotient_campaign.v107",
        "preregistration_id": preregistration_id,
        "v106_failed_campaign_id": v106_campaign_id,
        "v106_failed_verification_id": v106_verification_id,
        "target_occurrences": occurrences,
        "incompatible_schema_no_transfer_control": ood,
        "accounting": {
            **totals,
            "offline_source_labels_not_recharged": True,
            "sample_labels_execution_steps_and_planning_compute_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": gate,
        "registered_catalogue_closed_legality_conditioned_quotient_verified": passed,
        "ground_distinctions_acquired_only_after_certificate_failure_verified": passed,
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
        "campaign_id": domains.extension_content_id_v107(
            domains.CONSTRUCTION_K7_CATALOGUE_CLOSED_LEGALITY_QUOTIENT_CAMPAIGN_V107_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_catalogue_closed_legality_quotient_campaign_document_v107",
    "build_catalogue_closed_legality_quotient_occurrence_v107",
)
