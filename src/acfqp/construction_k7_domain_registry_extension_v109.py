"""Fresh domains for dependency-revalidated quotient heuristics V109."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-dependency-revalidated-quotient-{suffix}:v109"
    for key, suffix in (
        ("construction_k7_dependency_revalidated_quotient_preregistration_v109", "preregistration"),
        ("construction_k7_dependency_revalidated_quotient_dependency_v109", "dependency"),
        ("construction_k7_dependency_revalidated_quotient_plan_v109", "plan"),
        ("construction_k7_dependency_revalidated_quotient_execution_receipt_v109", "execution-receipt"),
        ("construction_k7_dependency_revalidated_quotient_sequence_v109", "sequence"),
        ("construction_k7_dependency_revalidated_quotient_occurrence_v109", "occurrence"),
        ("construction_k7_dependency_revalidated_quotient_campaign_v109", "campaign"),
        ("construction_k7_dependency_revalidated_quotient_verification_v109", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V109: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V109 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v109(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V109:
        raise ValueError("domain tag is absent from V109")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V109",
            "K7_DOMAIN_TAG_EXTENSION_V109",
            "extension_content_id_v109",
        )
    )
)
