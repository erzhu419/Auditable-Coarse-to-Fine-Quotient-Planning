"""Additive domains for V163 safe sample-tax noninferiority."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v163"
    for key, tag in (
        ("occurrence", "construction-k7-safe-paid-path-occurrence"),
        ("campaign", "construction-k7-safe-paid-path-campaign"),
        ("target_preregistration", "construction-k7-safe-paid-path-preregistration"),
        ("verification", "construction-k7-safe-paid-path-verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V163: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V163 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V163_DOMAIN"] = _domain


def extension_content_id_v163(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V163:
        raise ValueError("domain tag is absent from V163")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V163",
    "K7_DOMAIN_TAG_EXTENSION_V163",
    "extension_content_id_v163",
)
