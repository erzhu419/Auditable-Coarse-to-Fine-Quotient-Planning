"""Domains for the fourth-family inventory transfer V118."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-fourth-family-inventory-{suffix}:v118"
    for key, suffix in (
        ("construction_k7_fourth_family_inventory_preregistration_v118", "preregistration"),
        ("construction_k7_fourth_family_inventory_occurrence_v118", "occurrence"),
        ("construction_k7_fourth_family_inventory_campaign_v118", "campaign"),
        ("construction_k7_fourth_family_inventory_verification_v118", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V118: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V118 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v118(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V118:
        raise ValueError("domain tag is absent from V118")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V118",
            "K7_DOMAIN_TAG_EXTENSION_V118",
            "extension_content_id_v118",
        )
    )
)
