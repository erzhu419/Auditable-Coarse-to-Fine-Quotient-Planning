"""Fresh domains for identity-bound quotient-plan memoization V108."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-memoized-catalogue-quotient-{suffix}:v108"
    for key, suffix in (
        ("construction_k7_memoized_catalogue_quotient_preregistration_v108", "preregistration"),
        ("construction_k7_memoized_catalogue_quotient_sequence_v108", "sequence"),
        ("construction_k7_memoized_catalogue_quotient_occurrence_v108", "occurrence"),
        ("construction_k7_memoized_catalogue_quotient_campaign_v108", "campaign"),
        ("construction_k7_memoized_catalogue_quotient_verification_v108", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V108: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V108 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v108(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V108:
        raise ValueError("domain tag is absent from V108")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V108",
            "K7_DOMAIN_TAG_EXTENSION_V108",
            "extension_content_id_v108",
        )
    )
)
