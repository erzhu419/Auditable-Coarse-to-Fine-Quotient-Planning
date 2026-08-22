"""Additive domains for the V171 sixth-family typed-receipt campaign."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v171"
    for key, tag in (
        ("sequence", "construction-k7-complete-typed-plan-receipt-sequence"),
        ("typed_plan_receipt", "construction-k7-typed-abstract-plan-receipt"),
        ("execution_join_receipt", "construction-k7-typed-plan-execution-join"),
        ("occurrence", "construction-k7-sixth-family-typed-receipt-occurrence"),
        ("campaign", "construction-k7-sixth-family-typed-receipt-campaign"),
        ("target_preregistration", "construction-k7-sixth-family-typed-receipt-preregistration"),
        ("verification", "construction-k7-sixth-family-typed-receipt-verification"),
        ("failure", "construction-k7-sixth-family-typed-receipt-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V171: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V171 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V171_DOMAIN"] = _domain


def extension_content_id_v171(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V171:
        raise ValueError("domain tag is absent from V171")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V171",
    "K7_DOMAIN_TAG_EXTENSION_V171",
    "extension_content_id_v171",
)
