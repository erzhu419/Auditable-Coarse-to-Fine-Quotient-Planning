"""Additive domains for the V150 certified-abstention successor."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v150"
    for key, tag in (
        ("sequence", "construction-k7-certified-planner-abstention-sequence"),
        ("occurrence", "construction-k7-cross-domain-relational-bank-occurrence"),
        ("campaign", "construction-k7-cross-domain-relational-bank-campaign"),
        ("preregistration", "construction-k7-cross-domain-relational-bank-preregistration"),
        ("verification", "construction-k7-cross-domain-relational-bank-verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V150: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V150 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V150_DOMAIN"] = _domain


def extension_content_id_v150(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V150:
        raise ValueError("domain tag is absent from V150")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V150",
    "K7_DOMAIN_TAG_EXTENSION_V150",
    "extension_content_id_v150",
)
