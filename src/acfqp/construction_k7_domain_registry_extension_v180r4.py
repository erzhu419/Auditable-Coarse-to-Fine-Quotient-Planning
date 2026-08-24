"""Domains for the source-pinned V180r4 first production occurrence."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v180r4"
    for key, tag in (
        ("v34_execution_authorization", "construction-k7-v34-production-execution-authorization"),
        ("v34_execution_failure", "construction-k7-v34-production-execution-failure"),
        ("v34_execution_terminal", "construction-k7-v34-production-execution-terminal"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R4: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V180R4 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V180R4_DOMAIN"] = _domain


def extension_content_id_v180r4(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V180R4:
        raise ValueError("domain tag is absent from V180r4")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R4",
    "K7_DOMAIN_TAG_EXTENSION_V180R4",
    "extension_content_id_v180r4",
)
