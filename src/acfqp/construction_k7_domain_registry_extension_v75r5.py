"""Additive domains for V75r5 agreement-filtered query ordering."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-agreement-filtered-priority-{suffix}:v75r5"
    for key, suffix in (
        ("construction_k7_agreement_filtered_source_v75r5", "source"),
        ("construction_k7_agreement_filtered_target_v75r5", "target"),
        ("construction_k7_agreement_filtered_preregistration_v75r5", "preregistration"),
        ("construction_k7_agreement_filtered_campaign_v75r5", "campaign"),
        ("construction_k7_agreement_filtered_verification_v75r5", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75R5: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V75R5 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v75r5(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V75R5:
        raise ValueError("domain tag is absent from V75r5")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75R5",
            "K7_DOMAIN_TAG_EXTENSION_V75R5",
            "extension_content_id_v75r5",
        )
    )
)
