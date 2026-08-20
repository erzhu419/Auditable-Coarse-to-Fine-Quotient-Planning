"""Additive domains for the V75r1 portable-priority successor."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-portable-priority-cross-occurrence-{suffix}:v75r1"
    for key, suffix in (
        ("construction_k7_portable_priority_preregistration_v75r1", "preregistration"),
        ("construction_k7_portable_priority_source_v75r1", "source"),
        ("construction_k7_portable_priority_target_v75r1", "target"),
        ("construction_k7_portable_priority_campaign_v75r1", "campaign"),
        ("construction_k7_portable_priority_verification_v75r1", "verification"),
        ("construction_k7_portable_priority_failure_v75r1", "failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75R1: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V75R1 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V75R1) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V75r1 domain extension contains duplicate tags")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v75r1(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V75R1:
        raise ValueError("domain tag is absent from V75r1")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75R1",
            "K7_DOMAIN_TAG_EXTENSION_V75R1",
            "extension_content_id_v75r1",
        )
    )
)
