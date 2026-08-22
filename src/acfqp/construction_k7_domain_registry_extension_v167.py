"""Additive domains for the failed V166 attempt and its V167 successor."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v167"
    for key, tag in (
        ("v166_failure", "construction-k7-v166-fourth-family-failure"),
        ("sequence", "construction-k7-plan-mode-set-sequence"),
        ("occurrence", "construction-k7-plan-mode-set-fourth-family-occurrence"),
        ("campaign", "construction-k7-plan-mode-set-fourth-family-campaign"),
        (
            "target_preregistration",
            "construction-k7-plan-mode-set-fourth-family-preregistration",
        ),
        ("verification", "construction-k7-plan-mode-set-fourth-family-verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V167: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V167 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V167_DOMAIN"] = _domain


def extension_content_id_v167(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V167:
        raise ValueError("domain tag is absent from V167")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V167",
    "K7_DOMAIN_TAG_EXTENSION_V167",
    "extension_content_id_v167",
)
