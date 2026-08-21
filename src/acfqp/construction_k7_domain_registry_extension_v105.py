"""Fresh domains for actual quotient-model ordering evidence V105."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-actual-quotient-utilization-{suffix}:v105"
    for key, suffix in (
        ("construction_k7_quotient_utilization_preregistration_v105", "preregistration"),
        ("construction_k7_quotient_utilization_occurrence_v105", "occurrence"),
        ("construction_k7_quotient_utilization_campaign_v105", "campaign"),
        ("construction_k7_quotient_utilization_verification_v105", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V105: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V105 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v105(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V105:
        raise ValueError("domain tag is absent from V105")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V105",
            "K7_DOMAIN_TAG_EXTENSION_V105",
            "extension_content_id_v105",
        )
    )
)
