"""Additive domains for the V148 anonymous-relational prior ablation."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v148"
    for key, tag in (
        ("candidate", "construction-k7-anonymous-relational-prior-candidate"),
        ("calibration", "construction-k7-anonymous-relational-prior-calibration"),
        ("acquisition", "construction-k7-anonymous-relational-prior-acquisition"),
        ("occurrence", "construction-k7-anonymous-relational-prior-occurrence"),
        ("campaign", "construction-k7-anonymous-relational-prior-campaign"),
        ("preregistration", "construction-k7-anonymous-relational-prior-preregistration"),
        ("verification", "construction-k7-anonymous-relational-prior-verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V148: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V148 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_{_key.upper()}_V148_DOMAIN"] = _domain


def extension_content_id_v148(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V148:
        raise ValueError("domain tag is absent from V148")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V148",
    "K7_DOMAIN_TAG_EXTENSION_V148",
    "extension_content_id_v148",
)
