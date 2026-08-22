"""Additive domains for the V165 paid-prefix identifiability audit."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v165"
    for key, tag in (
        (
            "profitability_signature",
            "construction-k7-paid-prefix-profitability-signature",
        ),
        (
            "identifiability_audit",
            "construction-k7-paid-prefix-profitability-identifiability-audit",
        ),
        (
            "verification",
            "construction-k7-paid-prefix-profitability-identifiability-verification",
        ),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V165: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V165 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V165_DOMAIN"] = _domain


def extension_content_id_v165(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V165:
        raise ValueError("domain tag is absent from V165")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V165",
    "K7_DOMAIN_TAG_EXTENSION_V165",
    "extension_content_id_v165",
)
