"""Corrected fresh successor of the preserved V72 aggregation failure.

The frozen V72 occurrence constructor had completed all worker results before
its campaign accounting read an absent V39 field.  V72r1 reuses that exact
source/arm constructor on disjoint fresh seeds, rebinds each result to a fresh
occurrence domain, and independently derives the schedule work from retained
relation-signature rows.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v72r1 as domains
from acfqp import successor_version_space_campaign_core_v72 as frozen_v72
from acfqp.construction_k7_successor_version_space_failure_v72 import FAILURE_ID


class SuccessorVersionSpaceCampaignCoreV72R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise SuccessorVersionSpaceCampaignCoreV72R1Error(message)


def _run_occurrence(args: tuple[Any, ...]) -> dict[str, Any]:
    predecessor = frozen_v72._run_occurrence(args)  # noqa: SLF001
    payload = {
        **{
            key: value
            for key, value in predecessor.items()
            if key not in {"schema", "occurrence_id"}
        },
        "schema": "acfqp.successor_version_space_occurrence.v72r1",
        "preserved_v72_failure_id": FAILURE_ID,
        "frozen_v72_occurrence_constructor_reused_without_semantic_change": True,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v72r1(
            domains.CONSTRUCTION_K7_SUCCESSOR_VERSION_SPACE_OCCURRENCE_V72R1_DOMAIN,
            payload,
        ),
    }


def _consumed(acquisition: Mapping[str, Any]) -> int:
    value = acquisition.get("stopped_physical_ground_support_labels")
    if value is None:
        value = acquisition.get("full_query_stream_ground_support_labels")
    if type(value) is not int:
        _fail("V72r1 consumed-label accounting changed")
    return value


def _terminal_compute(acquisition: Mapping[str, Any]) -> int:
    total = 0
    for row in acquisition.get("proposal_attempts", []):
        value = row.get("candidate_constructor_compute", 0)
        if type(value) is not int:
            _fail("V72r1 terminal constructor compute changed")
        total += value
    return total


def _schedule_compute(schedule: Mapping[str, Any]) -> int:
    rows = schedule.get("schedule")
    if type(rows) is not list:
        _fail("V72r1 retained schedule rows changed")
    total = 0
    for row in rows:
        signature = row.get("relation_signature") if type(row) is dict else None
        state = (
            signature.get("modeled_pre_coordinate_relations")
            if type(signature) is dict
            else None
        )
        action = (
            signature.get("anonymous_action_field_relations")
            if type(signature) is dict
            else None
        )
        if type(state) is not list or type(action) is not list:
            _fail("V72r1 relation signature accounting changed")
        total += len(state) + len(action)
    return total


def build_successor_version_space_campaign_document_v72r1(
    config: Mapping[str, Any],
    preregistration_id: str,
    v71_campaign_id: str,
    v71_verification_id: str,
    template_library_artifact_id: str,
    factor_library: Mapping[str, Any],
    residual_library: Mapping[str, Any],
    template_library: Mapping[str, Any],
    offline_template_source_labels: int,
) -> dict[str, Any]:
    arguments = [
        (family, seed, factor_library, residual_library, template_library, config)
        for family, seeds in config["target_seeds"].items()
        for seed in seeds
    ]
    if config["worker_count"] == 1:
        occurrences = [_run_occurrence(row) for row in arguments]
    else:
        with ProcessPoolExecutor(max_workers=config["worker_count"]) as executor:
            occurrences = list(executor.map(_run_occurrence, arguments))
    if len(occurrences) != config["target_occurrence_count"]:
        _fail("V72r1 occurrence inventory changed")
    arm_names = (
        "ROLE_FREE_FACTOR_PRIOR_ON",
        "STRICT_NO_ROLE_FREE_FACTOR_PRIOR",
    )
    summaries = {}
    for name in arm_names:
        rows = [row["acquisition_arms"][name] for row in occurrences]
        summaries[name] = {
            "heldout_validated_occurrence_count": sum(
                row["status"] == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
                for row in rows
            ),
            "heldout_failed_noncertificate_occurrence_count": sum(
                row["status"]
                == "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE"
                for row in rows
            ),
            "abstained_occurrence_count": sum(
                row["status"].startswith("ABSTAINED") for row in rows
            ),
            "counterfactual_acquisition_consumed_labels": sum(
                _consumed(row) for row in rows
            ),
            "post_stop_heldout_audit_labels": sum(
                row["heldout_ground_query_count"] for row in rows
            ),
            "terminal_constructor_compute_events": sum(
                _terminal_compute(row) for row in rows
            ),
            "successor_model_derivation_compute_events": sum(
                row["successor_model_derivation_compute_events"] for row in rows
            ),
            "retired_failed_proposal_count": sum(
                row["retired_failed_proposal_count"] for row in rows
            ),
        }
    comparable = [
        row
        for row in occurrences
        if all(
            row["acquisition_arms"][name]["status"]
            == "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
            for name in arm_names
        )
    ]
    prior_labels = sum(
        _consumed(row["acquisition_arms"][arm_names[0]]) for row in comparable
    )
    strict_labels = sum(
        _consumed(row["acquisition_arms"][arm_names[1]]) for row in comparable
    )
    ood_rejections = sum(
        row["incompatible_schema_ood_control"]["status"]
        == "INCOMPATIBLE_SCHEMA_REJECTED"
        for row in occurrences
    )
    zero_failed = all(
        summaries[name]["heldout_failed_noncertificate_occurrence_count"] == 0
        for name in arm_names
    )
    gate_passed = (
        zero_failed
        and all(
            summaries[name]["heldout_validated_occurrence_count"] > 0
            for name in arm_names
        )
        and bool(comparable)
        and ood_rejections == len(occurrences)
        and all(
            row["shared_outcome_blind_query_schedule"][
                "terminal_acceptance_label_accessed"
            ]
            is False
            for row in occurrences
        )
    )
    episodes = [
        row["target_source_complete_episode"]["predecessor_v30_episode"]
        for row in occurrences
    ]
    accounting = {
        "offline_template_source_labels": offline_template_source_labels,
        "offline_residual_library_labels": config["offline_library_labels"],
        "underlying_target_common_partial_labels": sum(
            row["common_partial_ground_support_labels"] for row in occurrences
        ),
        "underlying_target_certificate_local_labels": sum(
            row["local_ground_support_labels"] for row in episodes
        ),
        "underlying_target_execution_steps": sum(
            row["execution_steps"] for row in episodes
        ),
        "underlying_target_partial_planning_compute_events": sum(
            row["partial_planning_compute_events"] for row in episodes
        ),
        "underlying_target_relational_planning_compute_events": sum(
            row["relational_abstract_support_branch_evaluations"] for row in episodes
        ),
        "shared_schedule_relation_evaluations": sum(
            _schedule_compute(row["shared_outcome_blind_query_schedule"])
            for row in occurrences
        ),
        "arm_accounting": summaries,
        "all_axes_separate": True,
        "counterfactual_acquisition_labels_not_subtracted_from_actual_source_generation": True,
    }
    sample_tax = {
        "jointly_heldout_validated_occurrence_count": len(comparable),
        "prior_consumed_labels_on_comparable_occurrences": prior_labels,
        "strict_consumed_labels_on_comparable_occurrences": strict_labels,
        "prior_minus_strict_labels": prior_labels - strict_labels,
        "fresh_prior_label_reduction_observed": bool(comparable)
        and prior_labels < strict_labels,
        "sample_reduction_required_by_registered_gate": False,
        "online_actual_sample_reduction_claimed": False,
        "economics_claimed": False,
    }
    payload = {
        "schema": "acfqp.successor_version_space_campaign.v72r1",
        "preregistration_id": preregistration_id,
        "preserved_v72_failure_id": FAILURE_ID,
        "v71_campaign_id": v71_campaign_id,
        "v71_verification_id": v71_verification_id,
        "template_library_artifact_id": template_library_artifact_id,
        "occurrences": occurrences,
        "accounting": accounting,
        "sample_tax_comparison": sample_tax,
        "registered_gate": {
            "zero_heldout_failed_proposals_in_both_arms": zero_failed,
            "prior_heldout_validated_occurrence_count": summaries[arm_names[0]][
                "heldout_validated_occurrence_count"
            ],
            "strict_heldout_validated_occurrence_count": summaries[arm_names[1]][
                "heldout_validated_occurrence_count"
            ],
            "jointly_comparable_occurrence_count": len(comparable),
            "incompatible_schema_ood_rejection_count": ood_rejections,
            "required_ood_rejection_count": len(occurrences),
            "sample_reduction_required": False,
            "passed": gate_passed,
        },
        "same_target_query_pool_in_both_arms": True,
        "same_query_schedule_in_both_arms": True,
        "same_v41_version_space_and_stop_engine_in_both_arms": True,
        "heldout_rows_accessed_before_stop": False,
        "all_ground_queries_followed_failed_certificates": True,
        "query_local_exact_overlay_exclusively_used_for_safety": True,
        "producer_free_verification_present": False,
        "online_adaptive_acquisition_integrated": False,
        "complete_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v72r1(
            domains.CONSTRUCTION_K7_SUCCESSOR_VERSION_SPACE_CAMPAIGN_V72R1_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "SuccessorVersionSpaceCampaignCoreV72R1Error",
    "build_successor_version_space_campaign_document_v72r1",
)
