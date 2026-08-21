"""Domains for heterogeneous-cohort planning campaign V138."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "construction_k7_heterogeneous_cohort_acquisition_v138": (
        "acfqp:construction-k7-heterogeneous-cohort-acquisition:v138"
    ),
    "construction_k7_heterogeneous_cohort_occurrence_v138": (
        "acfqp:construction-k7-heterogeneous-cohort-occurrence:v138"
    ),
    "construction_k7_heterogeneous_cohort_campaign_v138": (
        "acfqp:construction-k7-heterogeneous-cohort-campaign:v138"
    ),
    "construction_k7_heterogeneous_cohort_preregistration_v138": (
        "acfqp:construction-k7-heterogeneous-cohort-preregistration:v138"
    ),
    "construction_k7_heterogeneous_cohort_verification_v138": (
        "acfqp:construction-k7-heterogeneous-cohort-verification:v138"
    ),
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V138: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V138 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v138(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V138:
        raise ValueError("domain tag is absent from V138")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V138",
            "K7_DOMAIN_TAG_EXTENSION_V138",
            "extension_content_id_v138",
        )
    )
)
