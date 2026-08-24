"""Domains for the fresh V180r8 durable cached-infeasibility path."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v180r8"
    for key, tag in (
        (
            "cached_execution_authorization",
            "construction-k7-cached-exact-infeasibility-execution-authorization",
        ),
        (
            "cached_execution_failure",
            "construction-k7-cached-exact-infeasibility-execution-failure",
        ),
        (
            "cached_source_receipt",
            "construction-k7-cached-exact-infeasibility-source-receipt",
        ),
        (
            "cached_shared_resource_receipt_set",
            "construction-k7-cached-exact-shared-resource-receipt-set",
        ),
        (
            "cached_execution_terminal",
            "construction-k7-cached-exact-infeasibility-execution-terminal",
        ),
        (
            "cached_execution_verification",
            "construction-k7-cached-exact-infeasibility-execution-verification",
        ),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R8: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V180R8 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V180R8_DOMAIN"] = _domain


def extension_content_id_v180r8(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V180R8:
        raise ValueError("domain tag is absent from V180r8")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R8",
    "K7_DOMAIN_TAG_EXTENSION_V180R8",
    "extension_content_id_v180r8",
)
