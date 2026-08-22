"""Additive domains for V157 plan-mode-corrected margin evidence."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v157"
    for key, tag in (
        ("correction_receipt", "construction-k7-plan-mode-correction-receipt"),
        ("sequence", "construction-k7-applicable-plan-mode-sequence"),
        ("occurrence", "construction-k7-plan-mode-margin-occurrence"),
        ("campaign", "construction-k7-plan-mode-margin-campaign"),
        ("preregistration", "construction-k7-plan-mode-margin-preregistration"),
        ("verification", "construction-k7-plan-mode-margin-verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V157: Mapping[str, str] = MappingProxyType(_DOMAIN_BY_KEY)
K7_DOMAIN_TAG_EXTENSION_V157 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V157_DOMAIN"] = _domain


def extension_content_id_v157(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V157:
        raise ValueError("domain tag is absent from V157")
    return hashlib.sha256(domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V157",
    "K7_DOMAIN_TAG_EXTENSION_V157",
    "extension_content_id_v157",
)
