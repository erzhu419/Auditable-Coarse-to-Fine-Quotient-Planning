"""Fresh domains for legality-conditioned quotient utilization V106."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-legality-conditioned-quotient-{suffix}:v106"
    for key, suffix in (
        ("construction_k7_legality_conditioned_quotient_preregistration_v106", "preregistration"),
        ("construction_k7_legality_conditioned_quotient_occurrence_v106", "occurrence"),
        ("construction_k7_legality_conditioned_quotient_campaign_v106", "campaign"),
        ("construction_k7_legality_conditioned_quotient_verification_v106", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V106: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V106 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v106(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V106:
        raise ValueError("domain tag is absent from V106")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V106",
            "K7_DOMAIN_TAG_EXTENSION_V106",
            "extension_content_id_v106",
        )
    )
)
