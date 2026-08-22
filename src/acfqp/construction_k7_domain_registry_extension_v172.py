"""Additive domains for V172 online typed plan-receipt issuance."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v172"
    for key, tag in (
        ("online_plan_issuance", "construction-k7-online-typed-plan-issuance"),
        ("online_execution_join", "construction-k7-online-typed-plan-execution-join"),
        ("sequence", "construction-k7-online-typed-plan-sequence"),
        ("occurrence", "construction-k7-online-typed-plan-occurrence"),
        ("campaign", "construction-k7-online-typed-plan-campaign"),
        ("target_preregistration", "construction-k7-online-typed-plan-preregistration"),
        ("verification", "construction-k7-online-typed-plan-verification"),
        ("failure", "construction-k7-online-typed-plan-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V172: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V172 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V172_DOMAIN"] = _domain


def extension_content_id_v172(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V172:
        raise ValueError("domain tag is absent from V172")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V172",
    "K7_DOMAIN_TAG_EXTENSION_V172",
    "extension_content_id_v172",
)
