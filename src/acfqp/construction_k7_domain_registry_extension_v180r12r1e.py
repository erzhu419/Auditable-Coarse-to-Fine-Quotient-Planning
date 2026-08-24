"""Sub-record domains for the V180r12r1 production aggregation execution."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v180r12r1e"
    for key, tag in (
        ("source_receipt", "construction-k7-ten-terminal-source-verification-receipt"),
        ("terminal_receipt", "construction-k7-ten-terminal-chain-receipt"),
        ("shared_receipt", "construction-k7-ten-terminal-shared-resource-receipt"),
        ("receipt_set", "construction-k7-ten-terminal-shared-resource-receipt-set"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R1E: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V180R12R1E = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V180R12R1E_DOMAIN"] = _domain


def extension_content_id_v180r12r1e(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V180R12R1E
    ):
        raise ValueError("domain tag is absent from V180r12r1e")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R1E",
    "K7_DOMAIN_TAG_EXTENSION_V180R12R1E",
    "extension_content_id_v180r12r1e",
)
