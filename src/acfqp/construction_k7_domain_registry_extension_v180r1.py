"""Fresh additive domains for the V180 shared-terminal finalizer slice."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v180r1"
    for key, tag in (
        ("terminal_observation", "construction-k7-all-path-terminal-observation"),
        ("terminal_measurement", "construction-k7-all-path-terminal-measurement"),
        ("terminal_bundle", "construction-k7-all-path-terminal-accounting-bundle"),
        ("campaign_bundle", "construction-k7-all-path-fixture-campaign-bundle"),
        ("verification", "construction-k7-all-path-finalizer-verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R1: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V180R1 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V180R1_DOMAIN"] = _domain


def extension_content_id_v180r1(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V180R1
    ):
        raise ValueError("domain tag is absent from V180r1")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R1",
    "K7_DOMAIN_TAG_EXTENSION_V180R1",
    "extension_content_id_v180r1",
)
