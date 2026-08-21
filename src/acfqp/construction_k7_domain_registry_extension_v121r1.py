"""Domains for opportunity-independent generic subprogram Gate V121r1."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-generic-subprogram-opportunity-independent-{suffix}:v121r1"
    for key, suffix in (
        ("construction_k7_generic_subprogram_preregistration_v121r1", "preregistration"),
        ("construction_k7_generic_subprogram_occurrence_v121r1", "occurrence"),
        ("construction_k7_generic_subprogram_campaign_v121r1", "campaign"),
        ("construction_k7_generic_subprogram_verification_v121r1", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V121R1: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V121R1 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v121r1(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V121R1:
        raise ValueError("domain tag is absent from V121r1")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V121R1",
            "K7_DOMAIN_TAG_EXTENSION_V121R1",
            "extension_content_id_v121r1",
        )
    )
)
