"""Additive domains for V173 branch-complete online receipt evidence."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v173"
    for key, tag in (
        ("occurrence", "construction-k7-branch-complete-online-receipt-occurrence"),
        ("campaign", "construction-k7-branch-complete-online-receipt-campaign"),
        ("target_preregistration", "construction-k7-branch-complete-online-receipt-preregistration"),
        ("verification", "construction-k7-branch-complete-online-receipt-verification"),
        ("failure", "construction-k7-branch-complete-online-receipt-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V173: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V173 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V173_DOMAIN"] = _domain


def extension_content_id_v173(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V173:
        raise ValueError("domain tag is absent from V173")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V173",
    "K7_DOMAIN_TAG_EXTENSION_V173",
    "extension_content_id_v173",
)
