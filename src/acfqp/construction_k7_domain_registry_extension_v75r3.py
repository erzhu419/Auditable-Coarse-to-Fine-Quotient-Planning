"""Additive domains for the V75r3 fail-closed target campaign."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-fail-closed-normalized-priority-{suffix}:v75r3"
    for key, suffix in (
        ("construction_k7_fail_closed_priority_preregistration_v75r3", "preregistration"),
        ("construction_k7_fail_closed_priority_campaign_v75r3", "campaign"),
        ("construction_k7_fail_closed_priority_verification_v75r3", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75R3: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V75R3 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V75R3) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V75r3 domain extension contains duplicate tags")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v75r3(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V75R3:
        raise ValueError("domain tag is absent from V75r3")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75R3",
            "K7_DOMAIN_TAG_EXTENSION_V75R3",
            "extension_content_id_v75r3",
        )
    )
)
