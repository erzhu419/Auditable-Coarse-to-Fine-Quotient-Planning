"""Additive content domains for the V80 structurally routed source Gate."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-structurally-routed-source-{suffix}:v80"
    for key, suffix in (
        ("construction_k7_structural_route_preregistration_v80", "preregistration"),
        ("construction_k7_structural_route_member_v80", "member"),
        ("construction_k7_structural_route_campaign_v80", "campaign"),
        ("construction_k7_structural_route_verification_v80", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V80: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V80 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v80(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V80:
        raise ValueError("domain tag is absent from V80")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V80",
            "K7_DOMAIN_TAG_EXTENSION_V80",
            "extension_content_id_v80",
        )
    )
)
