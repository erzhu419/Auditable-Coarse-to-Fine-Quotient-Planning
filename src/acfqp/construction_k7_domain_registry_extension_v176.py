"""Fresh domains for verifier-deferred delta invalidation V176."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v176"
    for key, tag in (
        ("certificate_delta", "certificate-local-model-delta"),
        ("epoch_transition", "delta-only-model-epoch-transition"),
        ("delta_transition_join", "certificate-delta-transition-join"),
        ("sequence", "delta-only-incremental-revalidation-sequence"),
        ("target_preregistration", "construction-k7-delta-only-preregistration"),
        ("occurrence", "construction-k7-delta-only-occurrence"),
        ("campaign", "construction-k7-delta-only-campaign"),
        ("verification", "construction-k7-delta-only-verification"),
        ("failure", "construction-k7-delta-only-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V176: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V176 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V176_DOMAIN"] = _domain


def extension_content_id_v176(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V176:
        raise ValueError("domain tag is absent from V176")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V176",
    "K7_DOMAIN_TAG_EXTENSION_V176",
    "extension_content_id_v176",
)
