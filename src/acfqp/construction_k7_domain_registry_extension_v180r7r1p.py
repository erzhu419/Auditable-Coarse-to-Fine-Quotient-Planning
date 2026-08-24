"""Fresh protocol and slot domains for the V180r7r1 occurrence."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v180r7r1p"
    for key, tag in (
        (
            "fallback_execution_protocol",
            "construction-k7-full-ground-fallback-execution-protocol",
        ),
        (
            "fallback_production_execution_slot",
            "construction-k7-full-ground-fallback-production-execution-slot",
        ),
        (
            "fallback_execution_authorization_evidence",
            (
                "construction-k7-full-ground-fallback-execution-"
                "authorization-evidence"
            ),
        ),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R7R1P: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V180R7R1P = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V180R7R1P_DOMAIN"] = _domain


def extension_content_id_v180r7r1p(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V180R7R1P
    ):
        raise ValueError("domain tag is absent from V180r7r1p")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R7R1P",
    "K7_DOMAIN_TAG_EXTENSION_V180R7R1P",
    "extension_content_id_v180r7r1p",
)
