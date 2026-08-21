"""Fresh V123r1 successor retaining the exact failed V123 predecessor."""

from __future__ import annotations

from typing import Any, Mapping

from acfqp import construction_k7_domain_registry_extension_v123r1 as domains
from acfqp.generic_quotient_compiler_campaign_core_v123 import (
    build_generic_quotient_compiler_campaign_document_v123,
    build_generic_quotient_compiler_occurrence_v123,
)


FAILED_V123_PREREGISTRATION_ID = (
    "abf11379f9075d225b0a0233d3f8d7fea7d57e26c7c2eaf0b9b0a8a1686d505d"
)
FAILED_V123_RECORD_SHA256 = (
    "84f32d6ed71ac0b4496d457662d5f750dacb9e77e37a51a17d6db6b6939b778e"
)


def _successor_occurrence(document: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        **{key: value for key, value in document.items() if key != "occurrence_id"},
        "schema": "acfqp.generic_quotient_compiler_occurrence.v123r1",
        "frozen_failed_v123_preregistration_id": FAILED_V123_PREREGISTRATION_ID,
        "frozen_failed_v123_record_sha256": FAILED_V123_RECORD_SHA256,
        "same_failed_v123_identity_rerun": False,
    }
    return {
        **payload,
        "occurrence_id": domains.extension_content_id_v123r1(
            domains.CONSTRUCTION_K7_GENERIC_QUOTIENT_COMPILER_OCCURRENCE_V123R1_DOMAIN,
            payload,
        ),
    }


def build_generic_quotient_compiler_occurrence_v123r1(
    config: Mapping[str, Any],
    *,
    seed: int,
    episode_indices: tuple[int, ...],
    artifact_factor_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
    strict_complete_factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    return _successor_occurrence(
        build_generic_quotient_compiler_occurrence_v123(
            config,
            seed=seed,
            episode_indices=episode_indices,
            artifact_factor_library=artifact_factor_library,
            source_campaign_bytes=source_campaign_bytes,
            strict_complete_factor_library=strict_complete_factor_library,
        )
    )


def build_generic_quotient_compiler_campaign_document_v123r1(
    config: Mapping[str, Any],
    *,
    preregistration_id: str,
    v122_campaign_id: str,
    v122_verification_id: str,
    artifact_factor_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
    strict_complete_factor_library: Mapping[str, Any],
) -> dict[str, Any]:
    base = build_generic_quotient_compiler_campaign_document_v123(
        config,
        preregistration_id=preregistration_id,
        v122_campaign_id=v122_campaign_id,
        v122_verification_id=v122_verification_id,
        artifact_factor_library=artifact_factor_library,
        source_campaign_bytes=source_campaign_bytes,
        strict_complete_factor_library=strict_complete_factor_library,
    )
    rows = [_successor_occurrence(row) for row in base["target_occurrences"]]
    payload = {
        **{key: value for key, value in base.items() if key != "campaign_id"},
        "schema": "acfqp.generic_quotient_compiler_campaign.v123r1",
        "target_occurrences": rows,
        "target_occurrence_ids": [row["occurrence_id"] for row in rows],
        "frozen_failed_v123_preregistration_id": FAILED_V123_PREREGISTRATION_ID,
        "frozen_failed_v123_record_sha256": FAILED_V123_RECORD_SHA256,
        "same_failed_v123_identity_rerun": False,
        "fresh_resource_successor": True,
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v123r1(
            domains.CONSTRUCTION_K7_GENERIC_QUOTIENT_COMPILER_CAMPAIGN_V123R1_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "build_generic_quotient_compiler_campaign_document_v123r1",
    "build_generic_quotient_compiler_occurrence_v123r1",
)
