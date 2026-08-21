"""Domains for cross-epoch program-branch reuse V116."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-cross-epoch-program-branch-{suffix}:v116"
    for key, suffix in (
        ("construction_k7_cross_epoch_program_branch_preregistration_v116", "preregistration"),
        ("construction_k7_cross_epoch_program_branch_sequence_v116", "sequence"),
        ("construction_k7_cross_epoch_program_branch_occurrence_v116", "occurrence"),
        ("construction_k7_cross_epoch_program_branch_campaign_v116", "campaign"),
        ("construction_k7_cross_epoch_program_branch_verification_v116", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V116: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V116 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v116(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V116:
        raise ValueError("domain tag is absent from V116")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V116",
            "K7_DOMAIN_TAG_EXTENSION_V116",
            "extension_content_id_v116",
        )
    )
)
