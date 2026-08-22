"""Additive domains for the V168 total receipt-set fifth-family successor."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v168"
    for key, tag in (
        ("sequence", "construction-k7-total-plan-receipt-set-sequence"),
        ("occurrence", "construction-k7-total-plan-receipt-set-fifth-family-occurrence"),
        ("campaign", "construction-k7-total-plan-receipt-set-fifth-family-campaign"),
        (
            "target_preregistration",
            "construction-k7-total-plan-receipt-set-fifth-family-preregistration",
        ),
        ("verification", "construction-k7-total-plan-receipt-set-fifth-family-verification"),
        ("failure", "construction-k7-total-plan-receipt-set-fifth-family-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V168: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V168 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V168_DOMAIN"] = _domain


def extension_content_id_v168(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V168:
        raise ValueError("domain tag is absent from V168")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V168",
    "K7_DOMAIN_TAG_EXTENSION_V168",
    "extension_content_id_v168",
)
