"""Domains for the V180r7r1 reachable-source materialization successor."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v180r7r1m1"
    for key, tag in (
        (
            "materialized_source_tree",
            "construction-k7-full-ground-fallback-materialized-source-tree",
        ),
        (
            "materialized_source_tree_manifest",
            "construction-k7-full-ground-fallback-materialized-source-tree-manifest",
        ),
        (
            "materialized_source_tree_failure",
            "construction-k7-full-ground-fallback-materialized-source-tree-failure",
        ),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R7R1M1: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V180R7R1M1 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V180R7R1M1_DOMAIN"] = _domain


def extension_content_id_v180r7r1m1(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V180R7R1M1
    ):
        raise ValueError("domain tag is absent from V180r7r1m1")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R7R1M1",
    "K7_DOMAIN_TAG_EXTENSION_V180R7R1M1",
    "extension_content_id_v180r7r1m1",
)
