"""Domains for the fresh long-horizon relational-overlay successor V144R2."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v144r2"
    for key, tag in (
        (
            "construction_k7_fifth_family_factor_bank_transfer_occurrence_v144r2",
            "construction-k7-fifth-family-factor-bank-transfer-occurrence",
        ),
        (
            "construction_k7_fifth_family_factor_bank_transfer_campaign_v144r2",
            "construction-k7-fifth-family-factor-bank-transfer-campaign",
        ),
        (
            "construction_k7_fifth_family_factor_bank_transfer_preregistration_v144r2",
            "construction-k7-fifth-family-factor-bank-transfer-preregistration",
        ),
        (
            "construction_k7_fifth_family_factor_bank_transfer_verification_v144r2",
            "construction-k7-fifth-family-factor-bank-transfer-verification",
        ),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V144R2: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V144R2 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v144r2(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V144R2:
        raise ValueError("domain tag is absent from V144R2")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V144R2",
            "K7_DOMAIN_TAG_EXTENSION_V144R2",
            "extension_content_id_v144r2",
        )
    )
)
