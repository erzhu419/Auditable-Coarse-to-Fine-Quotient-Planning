"""Domains for V141-source-unseen fifth-family transfer campaign V144."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "construction_k7_relational_factor_execution_projection_v144": (
        "acfqp:construction-k7-relational-factor-execution-projection:v144"
    ),
    "construction_k7_fifth_family_factor_bank_transfer_acquisition_v144": (
        "acfqp:construction-k7-fifth-family-factor-bank-transfer-acquisition:v144"
    ),
    "construction_k7_fifth_family_factor_bank_transfer_occurrence_v144": (
        "acfqp:construction-k7-fifth-family-factor-bank-transfer-occurrence:v144"
    ),
    "construction_k7_fifth_family_factor_bank_transfer_campaign_v144": (
        "acfqp:construction-k7-fifth-family-factor-bank-transfer-campaign:v144"
    ),
    "construction_k7_fifth_family_factor_bank_transfer_preregistration_v144": (
        "acfqp:construction-k7-fifth-family-factor-bank-transfer-preregistration:v144"
    ),
    "construction_k7_fifth_family_factor_bank_transfer_verification_v144": (
        "acfqp:construction-k7-fifth-family-factor-bank-transfer-verification:v144"
    ),
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V144: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V144 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v144(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V144:
        raise ValueError("domain tag is absent from V144")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V144",
            "K7_DOMAIN_TAG_EXTENSION_V144",
            "extension_content_id_v144",
        )
    )
)
