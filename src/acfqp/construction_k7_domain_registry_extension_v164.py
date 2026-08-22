"""Additive domains for the V164 sample-tax replication."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v164"
    for key, tag in (
        ("occurrence", "construction-k7-sample-tax-replication-occurrence"),
        ("campaign", "construction-k7-sample-tax-replication-campaign"),
        ("target_preregistration", "construction-k7-sample-tax-replication-preregistration"),
        ("verification", "construction-k7-sample-tax-replication-verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V164: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V164 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V164_DOMAIN"] = _domain


def extension_content_id_v164(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V164:
        raise ValueError("domain tag is absent from V164")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V164",
    "K7_DOMAIN_TAG_EXTENSION_V164",
    "extension_content_id_v164",
)
