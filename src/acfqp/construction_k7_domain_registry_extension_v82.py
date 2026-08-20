"""Additive content domains for the V82 bounded multi-source Gate."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-bounded-multi-source-{suffix}:v82"
    for key, suffix in (
        ("construction_k7_bounded_source_preregistration_v82", "preregistration"),
        ("construction_k7_bounded_source_member_v82", "member"),
        ("construction_k7_bounded_source_campaign_v82", "campaign"),
        ("construction_k7_bounded_source_verification_v82", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V82: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V82 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v82(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V82:
        raise ValueError("domain tag is absent from V82")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V82",
            "K7_DOMAIN_TAG_EXTENSION_V82",
            "extension_content_id_v82",
        )
    )
)
