"""Domains for the retained-output V180r10r1 finish-forward successor."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v180r10r1"
    for key, tag in (
        ("v36_retained_recovery_authorization", "construction-k7-v36-retained-recovery-authorization"),
        ("v36_retained_occurrence_receipt", "construction-k7-v36-retained-occurrence-receipt"),
        ("v36_retained_terminal", "construction-k7-v36-retained-terminal"),
        ("v36_retained_verification", "construction-k7-v36-retained-verification"),
        ("v36_retained_failure", "construction-k7-v36-retained-recovery-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R10R1: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V180R10R1 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V180R10R1_DOMAIN"] = _domain


def extension_content_id_v180r10r1(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V180R10R1
    ):
        raise ValueError("domain tag is absent from V180r10r1")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R10R1",
    "K7_DOMAIN_TAG_EXTENSION_V180R10R1",
    "extension_content_id_v180r10r1",
)
