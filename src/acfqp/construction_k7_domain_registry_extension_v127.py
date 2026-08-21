"""Domains for V127 cross-family reuse of the V126 owned sequence."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-owned-sequence-cross-family-{suffix}:v127"
    for key, suffix in (
        ("construction_k7_owned_sequence_cross_family_preregistration_v127", "preregistration"),
        ("construction_k7_owned_sequence_cross_family_occurrence_v127", "occurrence"),
        ("construction_k7_owned_sequence_cross_family_campaign_v127", "campaign"),
        ("construction_k7_owned_sequence_cross_family_verification_v127", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V127: Mapping[str, str] = MappingProxyType(_DOMAIN_BY_KEY)
K7_DOMAIN_TAG_EXTENSION_V127 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v127(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V127:
        raise ValueError("domain tag is absent from V127")
    return hashlib.sha256(domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V127",
            "K7_DOMAIN_TAG_EXTENSION_V127",
            "extension_content_id_v127",
        )
    )
)
