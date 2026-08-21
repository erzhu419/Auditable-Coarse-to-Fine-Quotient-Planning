"""Domains for V133 opaque-archive dictionary planning integration."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "construction_k7_opaque_archive_planning_preregistration_v133": (
        "acfqp:construction-k7-opaque-archive-planning-preregistration:v133"
    ),
    "construction_k7_opaque_archive_factor_acquisition_v133": (
        "acfqp:construction-k7-opaque-archive-factor-acquisition:v133"
    ),
    "construction_k7_opaque_archive_planning_occurrence_v133": (
        "acfqp:construction-k7-opaque-archive-planning-occurrence:v133"
    ),
    "construction_k7_opaque_archive_planning_campaign_v133": (
        "acfqp:construction-k7-opaque-archive-planning-campaign:v133"
    ),
    "construction_k7_opaque_archive_planning_verification_v133": (
        "acfqp:construction-k7-opaque-archive-planning-verification:v133"
    ),
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V133: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V133 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v133(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V133:
        raise ValueError("domain tag is absent from V133")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V133",
            "K7_DOMAIN_TAG_EXTENSION_V133",
            "extension_content_id_v133",
        )
    )
)
