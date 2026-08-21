"""Domains for the source-unseen higher-order residual construction V119."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-source-unseen-residual-{suffix}:v119"
    for key, suffix in (
        ("construction_k7_source_unseen_residual_preregistration_v119", "preregistration"),
        ("construction_k7_source_unseen_partial_acquisition_v119", "partial-acquisition"),
        ("construction_k7_source_unseen_strict_control_v119", "strict-control"),
        ("construction_k7_genesis_authorized_branch_sequence_v119", "genesis-authorized-branch-sequence"),
        ("construction_k7_source_unseen_residual_occurrence_v119", "occurrence"),
        ("construction_k7_source_unseen_residual_campaign_v119", "campaign"),
        ("construction_k7_source_unseen_residual_verification_v119", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V119: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V119 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v119(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V119:
        raise ValueError("domain tag is absent from V119")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V119",
            "K7_DOMAIN_TAG_EXTENSION_V119",
            "extension_content_id_v119",
        )
    )
)
