"""V145 accepts either sound local-recovery representation after certificate failure."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v145 as domains
from acfqp.fifth_family_factor_bank_transfer_campaign_core_v144r1 import (
    build_fifth_family_factor_bank_transfer_campaign_document_v144r1,
)


def reidentify_certificate_local_recovery_union_campaign_v145(
    source: Mapping[str, Any],
    *,
    preregistration_id: str,
) -> dict[str, Any]:
    document = deepcopy(dict(source))
    source_campaign_id = document.pop("campaign_id")
    rows: list[dict[str, Any]] = []
    for source_row in document["target_occurrences"]:
        row = deepcopy(source_row)
        source_occurrence_id = row.pop("occurrence_id")
        row.update(
            schema="acfqp.certificate_local_recovery_union_occurrence.v145",
            source_v144r1_occurrence_semantics_id=source_occurrence_id,
            certificate_local_recovery_union_semantics=True,
        )
        row["occurrence_id"] = domains.extension_content_id_v145(
            domains.CONSTRUCTION_K7_CERTIFICATE_LOCAL_RECOVERY_UNION_OCCURRENCE_V145_DOMAIN,
            row,
        )
        rows.append(row)
    accounting = document["accounting"]
    local_labels = (
        accounting["occurrence_factor_bank_update_prior_certificate_local_labels"]
        + accounting["strict_no_prior_certificate_local_labels"]
    )
    overlay_edges = (
        accounting["occurrence_factor_bank_update_prior_query_local_overlay_edges"]
        + accounting["strict_no_prior_query_local_overlay_edges"]
    )
    gate = document["registered_gate"]
    gate.update(
        certificate_failure_local_recovery_exercised_at_least_once=local_labels > 0,
        program_compatible_refinement_or_exact_overlay_admissible=True,
        exact_overlay_branch_exercise_required=False,
        exact_overlay_branch_exercised=overlay_edges > 0,
        observed_certificate_local_ground_label_count=local_labels,
        observed_query_local_exact_overlay_edge_count=overlay_edges,
    )
    gate["passed"] = (
        gate["passed_target_occurrence_count"] == gate["required_target_occurrence_count"]
        and gate["aggregate_positive_label_reduction"]
        and gate["verified_v141_factor_bank_receipt_consumed_everywhere"]
        and gate["target_family_absent_from_v141_source_occurrence_archive_everywhere"]
        and gate["same_synthesizer_representation_and_stop_rule_everywhere"]
        and gate["both_arm_receding_episodes_succeed_everywhere"]
        and gate["strict_incompatible_schema_no_transfer_verified"]
        and gate["certificate_local_relational_overlay_pipeline_verified_everywhere"]
        and gate["certificate_failure_local_recovery_exercised_at_least_once"]
        and gate["program_compatible_refinement_or_exact_overlay_admissible"]
    )
    document.update(
        schema="acfqp.certificate_local_recovery_union_campaign.v145",
        preregistration_id=preregistration_id,
        target_occurrences=rows,
        target_occurrence_ids=[row["occurrence_id"] for row in rows],
        source_v144r1_campaign_semantics_id=source_campaign_id,
        registered_gate=gate,
        registered_workload_sample_efficiency_improvement_observed=gate["passed"],
        sample_efficiency_improvement_claim_scope=(
            "ONLY_THE_PREREGISTERED_V145_SIX_OCCURRENCE_CERTIFICATE_LOCAL_RECOVERY_UNION_WORKLOAD"
        ),
        certificate_local_recovery_representation=(
            "PROGRAM_COMPATIBLE_INCREMENTAL_REFINEMENT_OR_QUERY_LOCAL_EXACT_OVERLAY"
        ),
        exact_overlay_branch_required_for_positive_claim=False,
    )
    return {
        **document,
        "campaign_id": domains.extension_content_id_v145(
            domains.CONSTRUCTION_K7_CERTIFICATE_LOCAL_RECOVERY_UNION_CAMPAIGN_V145_DOMAIN,
            document,
        ),
    }


def build_certificate_local_recovery_union_campaign_document_v145(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    dictionary: Mapping[str, Any],
    dictionary_verification: Mapping[str, Any],
) -> dict[str, Any]:
    source = build_fifth_family_factor_bank_transfer_campaign_document_v144r1(
        config,
        preregistration_id=preregistration_id,
        dictionary=dictionary,
        dictionary_verification=dictionary_verification,
    )
    return reidentify_certificate_local_recovery_union_campaign_v145(
        source, preregistration_id=preregistration_id
    )


__all__ = (
    "build_certificate_local_recovery_union_campaign_document_v145",
    "reidentify_certificate_local_recovery_union_campaign_v145",
)
