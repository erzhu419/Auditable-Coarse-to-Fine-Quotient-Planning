"""Additive content domains for the V78 pooled-source diagnostic."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-canonical-pooled-source-{suffix}:v78"
    for key, suffix in (
        ("construction_k7_pooled_source_preregistration_v78", "preregistration"),
        ("construction_k7_pooled_source_member_v78", "member"),
        ("construction_k7_pooled_source_campaign_v78", "campaign"),
        ("construction_k7_pooled_source_verification_v78", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V78: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V78 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v78(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V78:
        raise ValueError("domain tag is absent from V78")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V78",
            "K7_DOMAIN_TAG_EXTENSION_V78",
            "extension_content_id_v78",
        )
    )
)
