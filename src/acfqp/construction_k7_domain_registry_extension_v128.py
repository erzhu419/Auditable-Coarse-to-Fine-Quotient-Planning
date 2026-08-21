"""Domains for V128 third-family reuse of the V126 owned sequence."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-third-family-owned-sequence-{suffix}:v128"
    for key, suffix in (
        ("construction_k7_third_family_owned_sequence_preregistration_v128", "preregistration"),
        ("construction_k7_third_family_owned_sequence_occurrence_v128", "occurrence"),
        ("construction_k7_third_family_owned_sequence_campaign_v128", "campaign"),
        ("construction_k7_third_family_owned_sequence_verification_v128", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V128: Mapping[str, str] = MappingProxyType(_DOMAIN_BY_KEY)
K7_DOMAIN_TAG_EXTENSION_V128 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v128(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V128:
        raise ValueError("domain tag is absent from V128")
    return hashlib.sha256(domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V128",
            "K7_DOMAIN_TAG_EXTENSION_V128",
            "extension_content_id_v128",
        )
    )
)
