"""Additive domains for the V170 complete abstract-plan receipt taxonomy."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "taxonomy_contract": "acfqp:construction-k7-abstract-plan-receipt-taxonomy-contract:v170",
    "typed_plan_receipt": "acfqp:construction-k7-typed-abstract-plan-receipt:v170",
    "execution_join_receipt": "acfqp:construction-k7-typed-plan-execution-join:v170",
    "audit": "acfqp:construction-k7-complete-abstract-plan-receipt-audit:v170",
    "verification": "acfqp:construction-k7-complete-abstract-plan-receipt-verification:v170",
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V170: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V170 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V170_DOMAIN"] = _domain


def extension_content_id_v170(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V170:
        raise ValueError("domain tag is absent from V170")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V170",
    "K7_DOMAIN_TAG_EXTENSION_V170",
    "extension_content_id_v170",
)
