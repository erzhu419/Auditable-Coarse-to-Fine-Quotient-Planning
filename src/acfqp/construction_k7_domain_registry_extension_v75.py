"""Additive domains for V75 cross-occurrence reusable-model transfer."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-cross-occurrence-reuse-{suffix}:v75"
    for key, suffix in (
        ("construction_k7_cross_occurrence_reuse_preregistration_v75", "preregistration"),
        ("construction_k7_cross_occurrence_reuse_source_v75", "source"),
        ("construction_k7_cross_occurrence_reuse_target_v75", "target"),
        ("construction_k7_cross_occurrence_reuse_campaign_v75", "campaign"),
        ("construction_k7_cross_occurrence_reuse_verification_v75", "verification"),
        ("construction_k7_cross_occurrence_reuse_failure_v75", "failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V75 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V75) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V75 domain extension contains duplicate tags")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v75(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V75:
        raise ValueError("domain tag is absent from V75")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75",
            "K7_DOMAIN_TAG_EXTENSION_V75",
            "extension_content_id_v75",
        )
    )
)
