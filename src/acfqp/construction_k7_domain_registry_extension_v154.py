"""Additive domains for V154 cross-structure operator validation."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v154"
    for key, tag in (
        ("application_receipt", "construction-k7-relation-coverage-cross-structure-application-receipt"),
        ("sequence", "construction-k7-certified-memoized-planner-sequence"),
        ("ood_control", "construction-k7-nonrelational-ood-control"),
        ("occurrence", "construction-k7-relation-coverage-cross-structure-occurrence"),
        ("campaign", "construction-k7-relation-coverage-cross-structure-campaign"),
        ("preregistration", "construction-k7-relation-coverage-cross-structure-preregistration"),
        ("verification", "construction-k7-relation-coverage-cross-structure-verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V154: Mapping[str, str] = MappingProxyType(_DOMAIN_BY_KEY)
K7_DOMAIN_TAG_EXTENSION_V154 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V154_DOMAIN"] = _domain


def extension_content_id_v154(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V154:
        raise ValueError("domain tag is absent from V154")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V154",
    "K7_DOMAIN_TAG_EXTENSION_V154",
    "extension_content_id_v154",
)
