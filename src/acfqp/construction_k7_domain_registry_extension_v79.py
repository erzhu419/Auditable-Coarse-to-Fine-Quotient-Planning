"""Additive content domains for the V79 successor-projected source Gate."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-successor-projected-pooled-source-{suffix}:v79"
    for key, suffix in (
        (
            "construction_k7_successor_projected_preregistration_v79",
            "preregistration",
        ),
        ("construction_k7_successor_projected_member_v79", "member"),
        ("construction_k7_successor_projected_campaign_v79", "campaign"),
        ("construction_k7_successor_projected_verification_v79", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V79: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V79 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v79(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V79:
        raise ValueError("domain tag is absent from V79")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V79",
            "K7_DOMAIN_TAG_EXTENSION_V79",
            "extension_content_id_v79",
        )
    )
)
