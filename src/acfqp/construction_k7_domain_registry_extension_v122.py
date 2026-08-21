"""Domains for the generic compiled-factor planner adapter V122."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-generic-factor-planner-{suffix}:v122"
    for key, suffix in (
        ("construction_k7_generic_factor_planner_preregistration_v122", "preregistration"),
        ("construction_k7_generic_factor_planner_sequence_v122", "sequence"),
        ("construction_k7_generic_factor_planner_occurrence_v122", "occurrence"),
        ("construction_k7_generic_factor_planner_campaign_v122", "campaign"),
        ("construction_k7_generic_factor_planner_verification_v122", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V122: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V122 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v122(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V122:
        raise ValueError("domain tag is absent from V122")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V122",
            "K7_DOMAIN_TAG_EXTENSION_V122",
            "extension_content_id_v122",
        )
    )
)
