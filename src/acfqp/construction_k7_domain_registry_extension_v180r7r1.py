"""Domains for the additive V180r7r1 fallback repair successor."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v180r7r1"
    for key, tag in (
        (
            "fallback_source_inventory_preregistration",
            "construction-k7-full-ground-fallback-source-inventory-preregistration",
        ),
        (
            "fallback_source_closure_repair",
            "construction-k7-full-ground-fallback-source-closure-repair",
        ),
        (
            "fallback_execution_authorization",
            "construction-k7-full-ground-fallback-execution-authorization",
        ),
        (
            "fallback_execution_failure",
            "construction-k7-full-ground-fallback-execution-failure",
        ),
        (
            "fallback_occurrence_receipt",
            "construction-k7-full-ground-fallback-occurrence-receipt",
        ),
        (
            "fallback_v9_lift_lineage",
            "construction-k7-full-ground-fallback-v9-lift-lineage",
        ),
        (
            "fallback_execution_terminal",
            "construction-k7-full-ground-fallback-execution-terminal",
        ),
        (
            "fallback_execution_verification",
            "construction-k7-full-ground-fallback-execution-verification",
        ),
        (
            "fallback_verification_failure",
            "construction-k7-full-ground-fallback-verification-failure",
        ),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R7R1: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V180R7R1 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V180R7R1_DOMAIN"] = _domain


def extension_content_id_v180r7r1(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V180R7R1
    ):
        raise ValueError("domain tag is absent from V180r7r1")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R7R1",
    "K7_DOMAIN_TAG_EXTENSION_V180R7R1",
    "extension_content_id_v180r7r1",
)
