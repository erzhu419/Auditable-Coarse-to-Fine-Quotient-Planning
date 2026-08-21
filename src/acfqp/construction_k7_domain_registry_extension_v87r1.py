"""Additive content domains for V87r1 coordinate-aligned transfer."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-coordinate-aligned-{suffix}:v87r1"
    for key, suffix in (
        ("construction_k7_coordinate_alignment_v87r1", "alignment"),
        ("construction_k7_coordinate_aligned_preregistration_v87r1", "preregistration"),
        ("construction_k7_coordinate_aligned_occurrence_v87r1", "occurrence"),
        ("construction_k7_coordinate_aligned_campaign_v87r1", "campaign"),
        ("construction_k7_coordinate_aligned_verification_v87r1", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V87R1: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V87R1 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v87r1(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V87R1:
        raise ValueError("domain tag is absent from V87r1")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V87R1",
            "K7_DOMAIN_TAG_EXTENSION_V87R1",
            "extension_content_id_v87r1",
        )
    )
)
