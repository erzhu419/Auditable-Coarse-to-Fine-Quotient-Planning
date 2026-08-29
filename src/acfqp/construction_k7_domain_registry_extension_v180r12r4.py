"""Fresh domains for the V180r12r4 actual campaign-measurement ledger."""

from __future__ import annotations

import hashlib
import re
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v180r12r4"
    for key, tag in (
        (
            "campaign_measurement_protocol",
            "construction-k7-campaign-measurement-protocol",
        ),
        (
            "execution_authorization",
            "construction-k7-campaign-measurement-execution-authorization",
        ),
        (
            "campaign_measurement_execution_slot",
            "construction-k7-campaign-measurement-execution-slot",
        ),
        (
            "campaign_measurement_attempt",
            "construction-k7-campaign-measurement-attempt",
        ),
        (
            "authorization_evidence",
            "construction-k7-campaign-measurement-authorization-evidence",
        ),
        (
            "prelaunch_external_root",
            "construction-k7-campaign-measurement-prelaunch-external-root",
        ),
        (
            "prelaunch_manifest",
            "construction-k7-campaign-measurement-prelaunch-manifest",
        ),
        (
            "prelaunch_materialization_terminal",
            "construction-k7-campaign-measurement-prelaunch-materialization-terminal",
        ),
        (
            "prelaunch_materialization_failure",
            "construction-k7-campaign-measurement-prelaunch-materialization-failure",
        ),
        ("launch_attempt", "construction-k7-campaign-measurement-launch-attempt"),
        ("launch_receipt", "construction-k7-campaign-measurement-launch-receipt"),
        ("launch_failure", "construction-k7-campaign-measurement-launch-failure"),
        (
            "terminal_bundle",
            "construction-k7-campaign-measurement-terminal-bundle",
        ),
        (
            "campaign_evidence_inventory_bundle",
            "construction-k7-campaign-evidence-inventory-bundle",
        ),
        (
            "campaign_os_receipt_bundle",
            "construction-k7-campaign-os-receipt-bundle",
        ),
        (
            "verification",
            "construction-k7-campaign-measurement-verification",
        ),
        ("failure", "construction-k7-campaign-measurement-failure"),
        (
            "production_evidence",
            "construction-k7-campaign-measurement-production-evidence",
        ),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R4: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V180R12R4 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V180R12R4_DOMAIN"] = _domain


CAMPAIGN_MEASUREMENT_ATTEMPT_SCHEMA = (
    "acfqp.campaign_measurement_attempt.v180r12r4"
)
_CONTENT_ID = re.compile(r"^[0-9a-f]{64}$")


def extension_content_id_v180r12r4(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V180R12R4
    ):
        raise ValueError("domain tag is absent from V180r12r4")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def derive_campaign_measurement_attempt_id_v180r12r4(
    *,
    protocol_id: str,
    authorization_id: str,
    authorization_evidence_id: str,
    campaign_measurement_execution_slot_id: str,
    logical_occurrence_id: str,
    execution_nonce: str,
) -> str:
    """Derive the one exact campaign occurrence identity without issuing it."""

    values = (
        (protocol_id, "protocol_id"),
        (authorization_id, "authorization_id"),
        (authorization_evidence_id, "authorization_evidence_id"),
        (
            campaign_measurement_execution_slot_id,
            "campaign_measurement_execution_slot_id",
        ),
        (logical_occurrence_id, "logical_occurrence_id"),
        (execution_nonce, "execution_nonce"),
    )
    for value, label in values:
        if type(value) is not str or _CONTENT_ID.fullmatch(value) is None:
            raise ValueError(f"{label} must be one lowercase 64-hex identity")
    payload = {
        "schema": CAMPAIGN_MEASUREMENT_ATTEMPT_SCHEMA,
        "protocol_id": protocol_id,
        "authorization_id": authorization_id,
        "authorization_evidence_id": authorization_evidence_id,
        "campaign_measurement_execution_slot_id": (
            campaign_measurement_execution_slot_id
        ),
        "logical_occurrence_id": logical_occurrence_id,
        "execution_nonce": execution_nonce,
    }
    if set(payload) != {
        "schema",
        "protocol_id",
        "authorization_id",
        "authorization_evidence_id",
        "campaign_measurement_execution_slot_id",
        "logical_occurrence_id",
        "execution_nonce",
    }:  # pragma: no cover - literal exact-keyset guard
        raise AssertionError("campaign-measurement attempt payload changed")
    return extension_content_id_v180r12r4(
        CONSTRUCTION_K7_CAMPAIGN_MEASUREMENT_ATTEMPT_V180R12R4_DOMAIN,
        payload,
    )


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "CAMPAIGN_MEASUREMENT_ATTEMPT_SCHEMA",
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R4",
    "K7_DOMAIN_TAG_EXTENSION_V180R12R4",
    "derive_campaign_measurement_attempt_id_v180r12r4",
    "extension_content_id_v180r12r4",
)
