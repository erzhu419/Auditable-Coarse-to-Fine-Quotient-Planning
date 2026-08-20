"""Additive domains for V74 multi-episode sample amortization."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-reusable-amortization-{suffix}:v74"
    for key, suffix in (
        ("construction_k7_reusable_amortization_preregistration_v74", "preregistration"),
        ("construction_k7_reusable_amortization_occurrence_v74", "occurrence"),
        ("construction_k7_reusable_amortization_campaign_v74", "campaign"),
        ("construction_k7_reusable_amortization_verification_v74", "verification"),
        ("construction_k7_reusable_amortization_failure_v74", "failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V74: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V74 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V74) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V74 domain extension contains duplicate tags")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v74(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V74:
        raise ValueError("domain tag is absent from V74")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V74",
            "K7_DOMAIN_TAG_EXTENSION_V74",
            "extension_content_id_v74",
        )
    )
)
