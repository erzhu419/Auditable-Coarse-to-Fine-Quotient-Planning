"""Fresh domains for identity-short-circuited epoch invalidation V111."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-identity-short-circuited-epoch-{suffix}:v111"
    for key, suffix in (
        ("construction_k7_identity_short_circuited_epoch_preregistration_v111", "preregistration"),
        ("construction_k7_identity_short_circuited_epoch_transition_v111", "transition"),
        ("construction_k7_identity_short_circuited_epoch_sequence_v111", "sequence"),
        ("construction_k7_identity_short_circuited_epoch_occurrence_v111", "occurrence"),
        ("construction_k7_identity_short_circuited_epoch_campaign_v111", "campaign"),
        ("construction_k7_identity_short_circuited_epoch_verification_v111", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V111: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V111 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v111(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V111:
        raise ValueError("domain tag is absent from V111")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V111",
            "K7_DOMAIN_TAG_EXTENSION_V111",
            "extension_content_id_v111",
        )
    )
)
