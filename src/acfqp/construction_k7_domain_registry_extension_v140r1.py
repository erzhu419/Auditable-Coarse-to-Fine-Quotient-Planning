"""Domains for occurrence-factor-bank planning campaign V140r1."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "construction_k7_occurrence_factor_bank_acquisition_v140r1": (
        "acfqp:construction-k7-occurrence-factor-bank-acquisition:v140r1"
    ),
    "construction_k7_occurrence_factor_bank_occurrence_v140r1": (
        "acfqp:construction-k7-occurrence-factor-bank-occurrence:v140r1"
    ),
    "construction_k7_occurrence_factor_bank_campaign_v140r1": (
        "acfqp:construction-k7-occurrence-factor-bank-campaign:v140r1"
    ),
    "construction_k7_occurrence_factor_bank_preregistration_v140r1": (
        "acfqp:construction-k7-occurrence-factor-bank-preregistration:v140r1"
    ),
    "construction_k7_occurrence_factor_bank_verification_v140r1": (
        "acfqp:construction-k7-occurrence-factor-bank-verification:v140r1"
    ),
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V140r1: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V140r1 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v140r1(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V140r1:
        raise ValueError("domain tag is absent from V140r1")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V140r1",
            "K7_DOMAIN_TAG_EXTENSION_V140r1",
            "extension_content_id_v140r1",
        )
    )
)
