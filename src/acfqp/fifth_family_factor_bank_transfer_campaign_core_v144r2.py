"""Fresh long-horizon V144R2 campaign over the unchanged V144R1 mechanism."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v144r2 as domains
from acfqp.fifth_family_factor_bank_transfer_campaign_core_v144r1 import (
    build_fifth_family_factor_bank_transfer_campaign_document_v144r1,
)


def reidentify_fifth_family_factor_bank_transfer_campaign_v144r2(
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
            schema="acfqp.fifth_family_factor_bank_transfer_occurrence.v144r2",
            v144r1_occurrence_semantics_reused_unchanged=True,
            source_v144r1_occurrence_id=source_occurrence_id,
        )
        row["occurrence_id"] = domains.extension_content_id_v144r2(
            domains.CONSTRUCTION_K7_FIFTH_FAMILY_FACTOR_BANK_TRANSFER_OCCURRENCE_V144R2_DOMAIN,
            row,
        )
        rows.append(row)
    document.update(
        schema="acfqp.fifth_family_factor_bank_transfer_campaign.v144r2",
        preregistration_id=preregistration_id,
        target_occurrences=rows,
        target_occurrence_ids=[row["occurrence_id"] for row in rows],
        source_v144r1_campaign_semantics_id=source_campaign_id,
        v144r1_algorithm_reused_without_outcome_adaptive_change=True,
        fresh_longer_receding_stress_successor=True,
    )
    document["registered_gate"][
        "v144r1_algorithm_reused_without_outcome_adaptive_change"
    ] = True
    document["registered_gate"]["fresh_longer_receding_stress_executed"] = True
    document["registered_gate"]["passed"] = (
        document["registered_gate"]["passed"]
        and document["registered_gate"][
            "v144r1_algorithm_reused_without_outcome_adaptive_change"
        ]
        and document["registered_gate"]["fresh_longer_receding_stress_executed"]
    )
    return {
        **document,
        "campaign_id": domains.extension_content_id_v144r2(
            domains.CONSTRUCTION_K7_FIFTH_FAMILY_FACTOR_BANK_TRANSFER_CAMPAIGN_V144R2_DOMAIN,
            document,
        ),
    }


def build_fifth_family_factor_bank_transfer_campaign_document_v144r2(
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
    return reidentify_fifth_family_factor_bank_transfer_campaign_v144r2(
        source, preregistration_id=preregistration_id
    )


__all__ = (
    "build_fifth_family_factor_bank_transfer_campaign_document_v144r2",
    "reidentify_fifth_family_factor_bank_transfer_campaign_v144r2",
)
