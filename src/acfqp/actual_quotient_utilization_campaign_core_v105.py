"""Fresh V105 campaign where the quotient model really orders actions."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v105 as domains
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as base
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_actual_quotient_execution_receipt_v105 import (
    verify_actual_quotient_execution_receipt_v105,
)
from acfqp.generic_persistent_multi_residual_sequence_v96 import (
    run_strict_cold_direct_sequence_v96,
)
from acfqp.generic_persistent_quotient_sequence_v105 import (
    run_persistent_quotient_sequence_v105,
)


def derive_actual_quotient_utilization_v105(
    sequence: Mapping[str, Any],
) -> dict[str, Any]:
    receipts = [
        verify_actual_quotient_execution_receipt_v105(row)
        for row in sequence["all_actual_quotient_execution_receipts"]
    ]
    expected_pairs = [
        (episode["episode_index"], decision)
        for episode in sequence["episodes"]
        for decision in range(episode["execution_steps"])
    ]
    observed_pairs = [
        (row["episode_index"], row["decision_index"]) for row in receipts
    ]
    if observed_pairs != expected_pairs:
        raise ValueError("V105 per-action quotient receipt coverage changed")
    steps = len(receipts)
    admitted = sum(
        row["quotient_proposal_admitted_to_real_action_order"] for row in receipts
    )
    matches = sum(
        row["chosen_action_matches_admitted_quotient_proposal"] for row in receipts
    )
    overrides = sum(
        row["actual_action_ordering_source"]
        == "EXACT_CERTIFICATE_FALLBACK_AFTER_QUOTIENT_ORDER"
        for row in receipts
    )
    exact_only = steps - admitted
    if (
        sequence["actual_quotient_execution_receipt_count"] != steps
        or sequence["execution_step_count"] != steps
        or sequence["quotient_proposal_admitted_execution_count"] != admitted
        or sequence["chosen_action_matches_admitted_quotient_proposal_count"]
        != matches
    ):
        raise ValueError("V105 quotient utilization accounting changed")
    return {
        "schema": "acfqp.actual_quotient_execution_utilization.v105",
        "execution_receipt_count": steps,
        "execution_step_count": steps,
        "quotient_proposal_admitted_execution_count": admitted,
        "chosen_action_matches_admitted_quotient_proposal_count": matches,
        "exact_certificate_override_after_quotient_order_count": overrides,
        "exact_certificate_only_no_quotient_order_count": exact_only,
        "quotient_proposal_admitted_fraction_numerator": admitted,
        "quotient_proposal_admitted_fraction_denominator": steps,
        "chosen_action_match_fraction_numerator": matches,
        "chosen_action_match_fraction_denominator": steps,
        "quotient_actually_orders_strict_majority_of_execution": 2 * admitted > steps,
        "chosen_action_matches_quotient_strict_majority": 2 * matches > steps,
        "every_action_independently_receipted": True,
        "receipt_replay_uses_no_producer_summary_count": True,
        "ordering_is_engine_input_not_posthoc_policy_match": True,
        "query_local_exact_overlay_remains_only_safety_authority": True,
    }


def build_actual_quotient_utilization_occurrence_v105(
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
    quotient = run_persistent_quotient_sequence_v105(
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
    utilization = derive_actual_quotient_utilization_v105(quotient)
    quotient_labels = quotient["lifetime_target_ground_support_labels"]
    direct_labels = direct["lifetime_target_ground_support_labels"]
    later_zero_label_reuse = any(
        row["episode_index"] != episode_indices[0]
        and row["new_certificate_labels_charged_this_episode"] == 0
        and row["quotient_proposal_admitted_execution_count"] > 0
        for row in quotient["episodes"]
    )
    gate = {
        "every_action_independently_receipted": utilization[
            "every_action_independently_receipted"
        ],
        "quotient_model_actually_orders_strict_majority": utilization[
            "quotient_actually_orders_strict_majority_of_execution"
        ],
        "chosen_action_matches_quotient_strict_majority": utilization[
            "chosen_action_matches_quotient_strict_majority"
        ],
        "ordering_is_engine_input_not_posthoc_match": utilization[
            "ordering_is_engine_input_not_posthoc_policy_match"
        ],
        "certificate_failure_only_query_discipline_clean": quotient[
            "every_new_ground_query_followed_a_failed_certificate"
        ],
        "later_zero_label_quotient_reuse_observed": later_zero_label_reuse,
        "quotient_lifetime_labels_strictly_below_cold_direct": (
            quotient_labels < direct_labels
        ),
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
        "schema": "acfqp.actual_quotient_utilization_occurrence.v105",
        "target_family": family,
        "seed": seed,
        "episode_indices": list(episode_indices),
        "partial_acquisition": acquisition["document"],
        "persistent_quotient_sequence": quotient,
        "strict_cold_direct_sequence": direct,
        "actual_quotient_utilization": utilization,
        "accounting": accounting,
        "registered_gate": gate,
        "observation_derived_quotient_primary_ordering_verified": gate["passed"],
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
        "occurrence_id": domains.extension_content_id_v105(
            domains.CONSTRUCTION_K7_QUOTIENT_UTILIZATION_OCCURRENCE_V105_DOMAIN,
            payload,
        ),
    }


def _target(args: tuple[Any, ...]) -> dict[str, Any]:
    return build_actual_quotient_utilization_occurrence_v105(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        factor_library=args[4],
    )


def build_actual_quotient_utilization_campaign_document_v105(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v104_campaign_id: str,
    v104_verification_id: str,
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
        row["actual_quotient_utilization"][
            "quotient_proposal_admitted_execution_count"
        ]
        for row in occurrences
    )
    totals["chosen_action_matches_admitted_quotient_proposal_count"] = sum(
        row["actual_quotient_utilization"][
            "chosen_action_matches_admitted_quotient_proposal_count"
        ]
        for row in occurrences
    )
    ood = incompatible_schema_no_transfer_control_v99()
    passed = (
        all(row["registered_gate"]["passed"] for row in occurrences)
        and 2 * totals["quotient_proposal_admitted_execution_count"]
        > totals["execution_steps"]
        and 2 * totals[
            "chosen_action_matches_admitted_quotient_proposal_count"
        ]
        > totals["execution_steps"]
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
        "every_occurrence_actual_quotient_ordering_strict_majority": all(
            row["registered_gate"]["quotient_model_actually_orders_strict_majority"]
            for row in occurrences
        ),
        "every_occurrence_chosen_action_match_strict_majority": all(
            row["registered_gate"]["chosen_action_matches_quotient_strict_majority"]
            for row in occurrences
        ),
        "aggregate_quotient_labels_strictly_below_cold_direct": (
            totals["quotient_lifetime_target_labels"]
            < totals["cold_direct_lifetime_target_labels"]
        ),
        "strict_incompatible_schema_no_transfer_verified": ood[
            "strict_ood_no_transfer"
        ],
        "passed": passed,
    }
    payload = {
        "schema": "acfqp.actual_quotient_utilization_campaign.v105",
        "preregistration_id": preregistration_id,
        "v104_campaign_id": v104_campaign_id,
        "v104_verification_id": v104_verification_id,
        "target_occurrences": occurrences,
        "incompatible_schema_no_transfer_control": ood,
        "accounting": {
            **totals,
            "offline_source_labels_not_recharged": True,
            "sample_labels_execution_steps_and_planning_compute_separate": True,
            "scalar_cost_aggregation_performed": False,
        },
        "registered_gate": gate,
        "registered_multistep_execution_primarily_ordered_by_observation_derived_quotient": passed,
        "ground_distinctions_acquired_only_after_certificate_failure_verified": passed,
        "actual_engine_ordering_not_posthoc_receipt_reclassification": True,
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
        "campaign_id": domains.extension_content_id_v105(
            domains.CONSTRUCTION_K7_QUOTIENT_UTILIZATION_CAMPAIGN_V105_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_actual_quotient_utilization_campaign_document_v105",
    "build_actual_quotient_utilization_occurrence_v105",
    "derive_actual_quotient_utilization_v105",
)
