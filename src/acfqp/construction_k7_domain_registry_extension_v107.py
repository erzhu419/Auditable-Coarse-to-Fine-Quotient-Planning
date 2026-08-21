"""Fresh domains for catalogue-closed legality-conditioned quotient V107."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-catalogue-closed-legality-quotient-{suffix}:v107"
    for key, suffix in (
        ("construction_k7_catalogue_closed_legality_quotient_preregistration_v107", "preregistration"),
        ("construction_k7_complete_anonymous_action_catalogue_receipt_v107", "catalogue-receipt"),
        ("construction_k7_catalogue_closed_legality_quotient_occurrence_v107", "occurrence"),
        ("construction_k7_catalogue_closed_legality_quotient_campaign_v107", "campaign"),
        ("construction_k7_catalogue_closed_legality_quotient_verification_v107", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V107: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V107 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v107(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V107:
        raise ValueError("domain tag is absent from V107")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V107",
            "K7_DOMAIN_TAG_EXTENSION_V107",
            "extension_content_id_v107",
        )
    )
)
