"""Additive content domains for V91 reference-aligned source synthesis."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-reference-aligned-source-{suffix}:v91"
    for key, suffix in (
        ("construction_k7_reference_aligned_preregistration_v91", "preregistration"),
        ("construction_k7_reference_aligned_member_v91", "member"),
        ("construction_k7_reference_aligned_campaign_v91", "campaign"),
        ("construction_k7_reference_aligned_verification_v91", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V91: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V91 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v91(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V91:
        raise ValueError("domain tag is absent from V91")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V91",
            "K7_DOMAIN_TAG_EXTENSION_V91",
            "extension_content_id_v91",
        )
    )
)
