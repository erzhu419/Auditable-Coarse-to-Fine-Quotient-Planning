"""Domains for the V126 owned generic-model episode loop."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-standalone-generic-owned-{suffix}:v126"
    for key, suffix in (
        ("construction_k7_standalone_generic_owned_preregistration_v126", "preregistration"),
        ("construction_k7_standalone_generic_owned_sequence_v126", "sequence"),
        ("construction_k7_standalone_generic_owned_occurrence_v126", "occurrence"),
        ("construction_k7_standalone_generic_owned_campaign_v126", "campaign"),
        ("construction_k7_standalone_generic_owned_verification_v126", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V126: Mapping[str, str] = MappingProxyType(_DOMAIN_BY_KEY)
K7_DOMAIN_TAG_EXTENSION_V126 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v126(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V126:
        raise ValueError("domain tag is absent from V126")
    return hashlib.sha256(domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V126",
            "K7_DOMAIN_TAG_EXTENSION_V126",
            "extension_content_id_v126",
        )
    )
)
