"""Domains for projected program-plan memoization V115."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-projected-program-memo-{suffix}:v115"
    for key, suffix in (
        ("construction_k7_projected_program_memo_preregistration_v115", "preregistration"),
        ("construction_k7_projected_program_memo_plan_v115", "plan"),
        ("construction_k7_projected_program_memo_sequence_v115", "sequence"),
        ("construction_k7_projected_program_memo_occurrence_v115", "occurrence"),
        ("construction_k7_projected_program_memo_campaign_v115", "campaign"),
        ("construction_k7_projected_program_memo_verification_v115", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V115: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V115 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v115(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V115:
        raise ValueError("domain tag is absent from V115")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V115",
            "K7_DOMAIN_TAG_EXTENSION_V115",
            "extension_content_id_v115",
        )
    )
)
