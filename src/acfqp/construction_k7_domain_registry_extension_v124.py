"""Domains for cross-family generic quotient compilation V124."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-cross-family-generic-compiler-{suffix}:v124"
    for key, suffix in (
        ("construction_k7_cross_family_generic_compiler_preregistration_v124", "preregistration"),
        ("construction_k7_cross_family_generic_compiler_sequence_v124", "sequence"),
        ("construction_k7_cross_family_generic_compiler_occurrence_v124", "occurrence"),
        ("construction_k7_cross_family_generic_compiler_campaign_v124", "campaign"),
        ("construction_k7_cross_family_generic_compiler_verification_v124", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V124: Mapping[str, str] = MappingProxyType(_DOMAIN_BY_KEY)
K7_DOMAIN_TAG_EXTENSION_V124 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v124(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V124:
        raise ValueError("domain tag is absent from V124")
    return hashlib.sha256(domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V124",
            "K7_DOMAIN_TAG_EXTENSION_V124",
            "extension_content_id_v124",
        )
    )
)
