"""Additive domains for the fresh ten-terminal aggregation V180r12r2."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v180r12r2"
    for key, tag in (
        (
            "aggregation_protocol",
            "construction-k7-ten-terminal-aggregation-protocol",
        ),
        (
            "execution_authorization",
            "construction-k7-ten-terminal-aggregation-execution-authorization",
        ),
        (
            "aggregation_execution_slot",
            "construction-k7-ten-terminal-aggregation-execution-slot",
        ),
        (
            "authorization_evidence",
            "construction-k7-ten-terminal-aggregation-authorization-evidence",
        ),
        (
            "stale_predecessor",
            "construction-k7-ten-terminal-aggregation-stale-predecessor",
        ),
        (
            "terminal_bundle",
            "construction-k7-ten-terminal-aggregation-terminal-bundle",
        ),
        (
            "verification",
            "construction-k7-ten-terminal-aggregation-verification",
        ),
        ("failure", "construction-k7-ten-terminal-aggregation-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R2: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V180R12R2 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V180R12R2_DOMAIN"] = _domain


def extension_content_id_v180r12r2(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V180R12R2
    ):
        raise ValueError("domain tag is absent from V180r12r2")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R2",
    "K7_DOMAIN_TAG_EXTENSION_V180R12R2",
    "extension_content_id_v180r12r2",
)
