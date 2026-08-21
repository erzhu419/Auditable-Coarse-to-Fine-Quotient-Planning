"""Fresh domains for hierarchical abstract-ordering evidence V104."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes

_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-hierarchical-abstract-utilization-{suffix}:v104"
    for key, suffix in (
        ("construction_k7_hierarchical_utilization_preregistration_v104", "preregistration"),
        ("construction_k7_hierarchical_utilization_occurrence_v104", "occurrence"),
        ("construction_k7_hierarchical_utilization_campaign_v104", "campaign"),
        ("construction_k7_hierarchical_utilization_verification_v104", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V104: Mapping[str, str] = MappingProxyType(_DOMAIN_BY_KEY)
K7_DOMAIN_TAG_EXTENSION_V104 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v104(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V104:
        raise ValueError("domain tag is absent from V104")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V104",
            "K7_DOMAIN_TAG_EXTENSION_V104",
            "extension_content_id_v104",
        )
    )
)
