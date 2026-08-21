"""Additive content domains for V89 permutation-matched sample-tax evidence."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-permutation-matched-sample-tax-{suffix}:v89"
    for key, suffix in (
        ("construction_k7_permutation_matched_preregistration_v89", "preregistration"),
        ("construction_k7_permutation_matched_occurrence_v89", "occurrence"),
        ("construction_k7_permutation_matched_campaign_v89", "campaign"),
        ("construction_k7_permutation_matched_verification_v89", "verification"),
        ("construction_k7_permutation_matched_attack_v89", "attack"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V89: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V89 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v89(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V89:
        raise ValueError("domain tag is absent from V89")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V89",
            "K7_DOMAIN_TAG_EXTENSION_V89",
            "extension_content_id_v89",
        )
    )
)
