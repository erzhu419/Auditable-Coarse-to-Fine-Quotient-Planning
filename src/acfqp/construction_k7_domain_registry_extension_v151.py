"""Additive domains for the V151 relational-template utilization campaign."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v151"
    for key, tag in (
        ("occurrence", "construction-k7-relation-keyed-bank-occurrence"),
        ("campaign", "construction-k7-relation-keyed-bank-campaign"),
        ("preregistration", "construction-k7-relation-keyed-bank-preregistration"),
        ("verification", "construction-k7-relation-keyed-bank-verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V151: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V151 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V151_DOMAIN"] = _domain


def extension_content_id_v151(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V151:
        raise ValueError("domain tag is absent from V151")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V151",
    "K7_DOMAIN_TAG_EXTENSION_V151",
    "extension_content_id_v151",
)
