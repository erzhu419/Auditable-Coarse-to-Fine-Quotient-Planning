"""Domains for the fresh V180r6 V36 local-recovery production path."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v180r6"
    for key, tag in (
        (
            "v36_execution_authorization",
            "construction-k7-v36-production-execution-authorization",
        ),
        (
            "v36_execution_failure",
            "construction-k7-v36-production-execution-failure",
        ),
        (
            "v36_execution_terminal",
            "construction-k7-v36-production-execution-terminal",
        ),
        (
            "v36_occurrence_receipt",
            "construction-k7-v36-production-occurrence-receipt",
        ),
        (
            "v36_execution_verification",
            "construction-k7-v36-production-execution-verification",
        ),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R6: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V180R6 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V180R6_DOMAIN"] = _domain


def extension_content_id_v180r6(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V180R6:
        raise ValueError("domain tag is absent from V180r6")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R6",
    "K7_DOMAIN_TAG_EXTENSION_V180R6",
    "extension_content_id_v180r6",
)
