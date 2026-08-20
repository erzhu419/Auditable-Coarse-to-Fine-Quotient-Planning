"""Additive domains for the fail-closed V77 three-family successor."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-fail-closed-three-family-{suffix}:v77"
    for key, suffix in (
        ("construction_k7_three_family_source_v77", "source"),
        ("construction_k7_three_family_target_v77", "target"),
        ("construction_k7_three_family_preregistration_v77", "preregistration"),
        ("construction_k7_three_family_campaign_v77", "campaign"),
        ("construction_k7_three_family_verification_v77", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V77: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V77 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v77(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V77:
        raise ValueError("domain tag is absent from V77")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V77",
            "K7_DOMAIN_TAG_EXTENSION_V77",
            "extension_content_id_v77",
        )
    )
)
