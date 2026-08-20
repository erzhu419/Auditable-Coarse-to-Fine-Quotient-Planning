"""Additive content domains for the V83 all-frontier multi-source Gate."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-all-frontier-multi-source-{suffix}:v83"
    for key, suffix in (
        ("construction_k7_all_frontier_preregistration_v83", "preregistration"),
        ("construction_k7_all_frontier_member_v83", "member"),
        ("construction_k7_all_frontier_campaign_v83", "campaign"),
        ("construction_k7_all_frontier_verification_v83", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V83: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V83 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v83(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V83:
        raise ValueError("domain tag is absent from V83")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V83",
            "K7_DOMAIN_TAG_EXTENSION_V83",
            "extension_content_id_v83",
        )
    )
)
