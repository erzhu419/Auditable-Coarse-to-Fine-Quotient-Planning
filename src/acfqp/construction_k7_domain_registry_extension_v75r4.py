"""Additive domains for V75r4 structural-rank transfer."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-structural-rank-transfer-{suffix}:v75r4"
    for key, suffix in (
        ("construction_k7_structural_rank_source_v75r4", "source"),
        ("construction_k7_structural_rank_target_v75r4", "target"),
        ("construction_k7_structural_rank_preregistration_v75r4", "preregistration"),
        ("construction_k7_structural_rank_campaign_v75r4", "campaign"),
        ("construction_k7_structural_rank_verification_v75r4", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75R4: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V75R4 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V75R4) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V75r4 domain extension contains duplicate tags")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v75r4(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V75R4:
        raise ValueError("domain tag is absent from V75r4")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V75R4",
            "K7_DOMAIN_TAG_EXTENSION_V75R4",
            "extension_content_id_v75r4",
        )
    )
)
