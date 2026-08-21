"""Domains for auto-calibrated archive planning campaign V136."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "construction_k7_auto_calibrated_archive_acquisition_v136": (
        "acfqp:construction-k7-auto-calibrated-archive-acquisition:v136"
    ),
    "construction_k7_auto_calibrated_archive_occurrence_v136": (
        "acfqp:construction-k7-auto-calibrated-archive-occurrence:v136"
    ),
    "construction_k7_auto_calibrated_archive_campaign_v136": (
        "acfqp:construction-k7-auto-calibrated-archive-campaign:v136"
    ),
    "construction_k7_auto_calibrated_archive_preregistration_v136": (
        "acfqp:construction-k7-auto-calibrated-archive-preregistration:v136"
    ),
    "construction_k7_auto_calibrated_archive_verification_v136": (
        "acfqp:construction-k7-auto-calibrated-archive-verification:v136"
    ),
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V136: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V136 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v136(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V136:
        raise ValueError("domain tag is absent from V136")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V136",
            "K7_DOMAIN_TAG_EXTENSION_V136",
            "extension_content_id_v136",
        )
    )
)
