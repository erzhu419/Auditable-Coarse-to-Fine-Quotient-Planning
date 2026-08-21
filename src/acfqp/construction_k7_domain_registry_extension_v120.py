"""Domains for artifact-derived anonymous factor invention V120."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-artifact-derived-factor-{suffix}:v120"
    for key, suffix in (
        ("construction_k7_artifact_derived_factor_library_v120", "library"),
        ("construction_k7_artifact_derived_factor_preregistration_v120", "preregistration"),
        ("construction_k7_artifact_derived_factor_acquisition_v120", "partial-acquisition"),
        ("construction_k7_artifact_derived_factor_strict_control_v120", "strict-control"),
        ("construction_k7_artifact_derived_factor_occurrence_v120", "occurrence"),
        ("construction_k7_artifact_derived_factor_campaign_v120", "campaign"),
        ("construction_k7_artifact_derived_factor_verification_v120", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V120: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V120 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v120(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V120:
        raise ValueError("domain tag is absent from V120")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V120",
            "K7_DOMAIN_TAG_EXTENSION_V120",
            "extension_content_id_v120",
        )
    )
)
