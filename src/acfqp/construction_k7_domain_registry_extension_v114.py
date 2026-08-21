"""Fresh domains for three-family incremental successor transfer V114."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-three-family-incremental-successor-{suffix}:v114"
    for key, suffix in (
        ("construction_k7_three_family_incremental_successor_preregistration_v114", "preregistration"),
        ("construction_k7_three_family_incremental_successor_occurrence_v114", "occurrence"),
        ("construction_k7_three_family_incremental_successor_campaign_v114", "campaign"),
        ("construction_k7_three_family_incremental_successor_verification_v114", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V114: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V114 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v114(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V114:
        raise ValueError("domain tag is absent from V114")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V114",
            "K7_DOMAIN_TAG_EXTENSION_V114",
            "extension_content_id_v114",
        )
    )
)
