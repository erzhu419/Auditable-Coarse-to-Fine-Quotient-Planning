"""Additive domains for six fresh controlled V180 terminal occurrences."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAINS = {
    key: f"acfqp:{role}:v180r9"
    for key, role in (
        ("execution_authorization", "remaining-terminal-execution-authorization"),
        ("event_evidence", "remaining-terminal-event-evidence"),
        ("shared_receipt", "remaining-terminal-shared-resource-receipt"),
        ("receipt_set", "remaining-terminal-shared-resource-receipt-set"),
        ("terminal_bundle", "remaining-terminal-accounting-bundle"),
        ("campaign_bundle", "remaining-terminal-campaign-bundle"),
        ("verification", "remaining-terminal-independent-verification"),
        ("failure", "remaining-terminal-campaign-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R9: Mapping[str, str] = MappingProxyType(
    _DOMAINS
)
K7_DOMAIN_TAG_EXTENSION_V180R9 = frozenset(_DOMAINS.values())
for _key, _domain in _DOMAINS.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V180R9_DOMAIN"] = _domain


def extension_content_id_v180r9(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V180R9:
        raise ValueError("domain tag is absent from V180r9")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R9",
    "K7_DOMAIN_TAG_EXTENSION_V180R9",
    "extension_content_id_v180r9",
)
