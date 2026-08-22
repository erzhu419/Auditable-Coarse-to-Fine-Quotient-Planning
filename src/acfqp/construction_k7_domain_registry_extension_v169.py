"""Additive domains for the V169 episode-scoped receipt-set audit."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "episode_receipt_set": "acfqp:construction-k7-episode-plan-receipt-set:v169",
    "audit": "acfqp:construction-k7-episode-plan-receipt-set-audit:v169",
    "verification": "acfqp:construction-k7-episode-plan-receipt-set-verification:v169",
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V169: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V169 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V169_DOMAIN"] = _domain


def extension_content_id_v169(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V169:
        raise ValueError("domain tag is absent from V169")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V169",
    "K7_DOMAIN_TAG_EXTENSION_V169",
    "extension_content_id_v169",
)
