"""Fresh corrected Gate over the frozen V178 indexed-lazy construction."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor

from acfqp import construction_k7_domain_registry_extension_v178r1 as domains
from acfqp import indexed_lazy_invalidation_campaign_core_v178 as previous
from acfqp.online_typed_plan_receipt_sequence_v172 import TAXONOMY


PACKET_FAMILY = previous.PACKET_FAMILY
RESERVOIR_FAMILY = previous.RESERVOIR_FAMILY
TARGET_FAMILIES = previous.TARGET_FAMILIES
V178_FAILURE_ID = "1c749090356db31c10a22d58bd88bb620c097e9ec730ef746c06800f50effa49"


def indexed_lazy_invalidation_campaign_config_v178r1():
    return previous.indexed_lazy_invalidation_campaign_config_v178()


def _correct_gate(base):
    metrics = base["indexed_lazy_invalidation_metrics"]
    gate = {
        key: value
        for key, value in base["registered_gate"].items()
        if key not in {"passed", "receipt_reverse_indices_are_live"}
    }
    invalidation_count = (
        metrics["graph_invalidations"] + metrics["program_invalidations"]
    )
    lookup_count = metrics["receipt_reverse_index_lookups"]
    gate.update(
        receipt_reverse_indices_constructed=metrics[
            "receipt_reverse_index_updates"
        ]
        > 0,
        receipt_reverse_index_lookup_matches_invalidation_demand=(
            lookup_count > 0 if invalidation_count > 0 else lookup_count == 0
        ),
        zero_invalidation_requires_zero_receipt_lookup=(
            invalidation_count != 0 or lookup_count == 0
        ),
    )
    gate["passed"] = all(value for value in gate.values() if type(value) is bool)
    return gate


def build_indexed_lazy_invalidation_occurrence_v178r1(
    config,
    *,
    family,
    seed,
    episode_indices,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
):
    if family not in (PACKET_FAMILY, RESERVOIR_FAMILY):
        raise ValueError("V178r1 target family is not registered")
    base = previous.build_indexed_lazy_invalidation_occurrence_v178(
        config,
        family=family,
        seed=seed,
        episode_indices=episode_indices,
        bank_raw=bank_raw,
        verification_raw=verification_raw,
        classifier_receipt_raw=classifier_receipt_raw,
    )
    gate = _correct_gate(base)
    payload = {
        **{
            key: value
            for key, value in base.items()
            if key
            not in {
                "schema",
                "occurrence_id",
                "registered_gate",
                "sample_tax_claim_scope",
            }
        },
        "schema": "acfqp.indexed_lazy_invalidation_occurrence.v178r1",
        "source_v178_occurrence_id": base["occurrence_id"],
        "preserved_v178_failure_id": V178_FAILURE_ID,
        "registered_gate": gate,
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V178R1_CROSS_FAMILY_COHORT",
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v178r1(
            domains.CONSTRUCTION_K7_OCCURRENCE_V178R1_DOMAIN, payload
        ),
    }


def _target(args):
    return build_indexed_lazy_invalidation_occurrence_v178r1(
        args[0],
        family=args[1],
        seed=args[2],
        episode_indices=args[3],
        bank_raw=args[4],
        verification_raw=args[5],
        classifier_receipt_raw=args[6],
    )


def build_indexed_lazy_invalidation_campaign_v178r1(
    config,
    *,
    preregistration_id,
    bank_raw,
    verification_raw,
    classifier_receipt_raw,
    v177_campaign_id,
    v177_verification_id,
):
    args = [
        (
            config,
            row["family"],
            row["seed"],
            tuple(config["target_episode_indices"]),
            bank_raw,
            verification_raw,
            classifier_receipt_raw,
        )
        for row in config["target_occurrences"]
    ]
    if config["target_worker_count"] == 1:
        rows = [_target(row) for row in args]
    else:
        with ProcessPoolExecutor(max_workers=config["target_worker_count"]) as executor:
            rows = list(executor.map(_target, args))
    histogram = {
        source: sum(row["online_typed_plan_source_histogram"][source] for row in rows)
        for source in TAXONOMY.values()
    }
    metrics = {
        key: sum(row["indexed_lazy_invalidation_metrics"][key] for row in rows)
        for key in rows[0]["indexed_lazy_invalidation_metrics"]
    }
    accounting = {
        "online_plan_issuance_receipt_count": sum(
            row["online_plan_issuance_receipt_count"] for row in rows
        ),
        "online_execution_join_receipt_count": sum(
            row["online_execution_join_receipt_count"] for row in rows
        ),
        **metrics,
        "factor_prior_labels_avoided": sum(
            row["factor_prior_sample_reduction_within_progressive_policy"]
            for row in rows
        ),
        "query_policy_labels_avoided": sum(
            row["query_policy_sample_reduction_vs_legacy_path_first"] for row in rows
        ),
        "sample_labels_execution_steps_derivation_planning_receipt_delta_index_and_lazy_maintenance_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    roles = {row["registered_indexed_lazy_role"] for row in rows}
    gate = {
        "required_occurrence_count": config["required_target_occurrence_count"],
        "passed_occurrence_count": sum(row["registered_gate"]["passed"] for row in rows),
        "packet_and_reservoir_indexed_lazy_roles_both_present": roles
        == {
            "INDEXED_INVALIDATION_AND_LAZY_PROGRAM_AUTHORIZATION",
            "INDEXED_RETENTION_AND_LAZY_GRAPH_AUTHORIZATION",
        },
        "all_four_online_plan_sources_observed": all(
            histogram[source] > 0 for source in TAXONOMY.values()
        ),
        "positive_selective_graph_invalidation_observed": metrics[
            "graph_invalidations"
        ]
        > 0,
        "positive_unaffected_graph_retention_observed": metrics["graph_retentions"] > 0,
        "positive_exact_state_program_invalidation_observed": metrics[
            "program_invalidations"
        ]
        > 0,
        "positive_incremental_revalidation_observed": metrics[
            "incremental_revalidations"
        ]
        > 0,
        "zero_production_full_graph_diff_control": metrics[
            "production_full_graph_diff_checks"
        ]
        == 0,
        "zero_production_live_dependency_projection_scan": metrics[
            "production_live_dependency_projection_scan_count"
        ]
        == 0,
        "zero_production_prior_receipt_event_scan": metrics[
            "production_prior_receipt_event_scan_count"
        ]
        == 0,
        "zero_eager_retained_authorization_update": metrics[
            "retained_authorization_metadata_updates"
        ]
        == 0,
        "lazy_authorization_join_is_total": metrics[
            "lazy_authorization_metadata_updates"
        ]
        == metrics["lazy_authorization_receipts"]
        == metrics["lazy_authorization_issuance_joins"]
        > 0,
        "receipt_reverse_indices_constructed_each_occurrence": all(
            row["registered_gate"]["receipt_reverse_indices_constructed"] is True
            for row in rows
        ),
        "receipt_reverse_index_lookup_matches_each_occurrence_demand": all(
            row["registered_gate"][
                "receipt_reverse_index_lookup_matches_invalidation_demand"
            ]
            is True
            for row in rows
        ),
        "positive_receipt_reverse_index_lookup_observed_campaign_wide": metrics[
            "receipt_reverse_index_lookups"
        ]
        > 0,
        "producer_free_dependency_and_full_graph_controls_required_each_occurrence": all(
            row["producer_free_dependency_and_full_graph_controls_required"] is True
            for row in rows
        ),
        "factor_prior_strictly_reduces_labels_each_occurrence": all(
            row["factor_prior_sample_reduction_within_progressive_policy"] > 0
            for row in rows
        ),
        "query_policy_noninferior_each_occurrence": all(
            row["query_policy_sample_reduction_vs_legacy_path_first"] >= 0
            for row in rows
        ),
        "certificate_failure_only_local_ground_distinctions": all(
            row["registered_gate"]["certificate_failure_only_local_ground_distinctions"]
            for row in rows
        ),
        "indexed_lazy_lifecycle_not_safety_authority": all(
            row["indexed_lazy_invalidation_is_model_or_safety_authority"] is False
            for row in rows
        ),
    }
    gate["passed"] = (
        len(rows) == config["required_target_occurrence_count"]
        and gate["passed_occurrence_count"] == len(rows)
        and all(value for value in gate.values() if type(value) is bool)
    )
    payload = {
        "schema": "acfqp.indexed_lazy_invalidation_campaign.v178r1",
        "preregistration_id": preregistration_id,
        "preserved_v178_failure_id": V178_FAILURE_ID,
        "frozen_v177_campaign_id": v177_campaign_id,
        "frozen_v177_verification_id": v177_verification_id,
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "online_typed_plan_source_histogram": histogram,
        "accounting": accounting,
        "registered_gate": gate,
        "indexed_lazy_invalidation_observed": gate["passed"],
        "factor_prior_sample_tax_reduction_observed": gate[
            "factor_prior_strictly_reduces_labels_each_occurrence"
        ],
        "sample_tax_claim_scope": "ONLY_THIS_PREREGISTERED_V178R1_CROSS_FAMILY_COHORT",
        "production_full_graph_diff_control_present": False,
        "production_live_dependency_projection_scan_present": False,
        "production_prior_receipt_event_scan_present": False,
        "eager_retained_authorization_update_present": False,
        "producer_free_dependency_and_full_graph_controls_required": True,
        "indexed_lazy_invalidation_changes_selected_action_order": False,
        "indexed_lazy_invalidation_is_model_or_safety_authority": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_world_model_synthesized": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v178r1(
            domains.CONSTRUCTION_K7_CAMPAIGN_V178R1_DOMAIN, payload
        ),
    }


__all__ = (
    "PACKET_FAMILY",
    "RESERVOIR_FAMILY",
    "V178_FAILURE_ID",
    "build_indexed_lazy_invalidation_campaign_v178r1",
    "build_indexed_lazy_invalidation_occurrence_v178r1",
    "indexed_lazy_invalidation_campaign_config_v178r1",
)
