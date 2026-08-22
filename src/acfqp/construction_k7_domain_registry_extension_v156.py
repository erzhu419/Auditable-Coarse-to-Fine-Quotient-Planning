"""Additive domains for the V156 anonymous structural-margin guard."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v156"
    for key, tag in (
        ("guard_receipt", "construction-k7-structural-margin-query-guard-receipt"),
        ("acquisition", "construction-k7-structural-margin-guarded-acquisition"),
        ("occurrence", "construction-k7-structural-margin-guarded-occurrence"),
        ("campaign", "construction-k7-structural-margin-guarded-campaign"),
        ("preregistration", "construction-k7-structural-margin-guarded-preregistration"),
        ("verification", "construction-k7-structural-margin-guarded-verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V156: Mapping[str, str] = MappingProxyType(_DOMAIN_BY_KEY)
K7_DOMAIN_TAG_EXTENSION_V156 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V156_DOMAIN"] = _domain


def extension_content_id_v156(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V156:
        raise ValueError("domain tag is absent from V156")
    return hashlib.sha256(domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V156",
    "K7_DOMAIN_TAG_EXTENSION_V156",
    "extension_content_id_v156",
)
