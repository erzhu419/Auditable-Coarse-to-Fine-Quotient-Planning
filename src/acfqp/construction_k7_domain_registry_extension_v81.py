"""Additive content domains for the V81 retained-version-space source Gate."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-retained-version-space-source-{suffix}:v81"
    for key, suffix in (
        ("construction_k7_retained_space_preregistration_v81", "preregistration"),
        ("construction_k7_retained_space_member_v81", "member"),
        ("construction_k7_retained_space_campaign_v81", "campaign"),
        ("construction_k7_retained_space_verification_v81", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V81: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V81 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v81(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V81:
        raise ValueError("domain tag is absent from V81")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V81",
            "K7_DOMAIN_TAG_EXTENSION_V81",
            "extension_content_id_v81",
        )
    )
)
