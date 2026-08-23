"""Fresh domains for indexed receipt lookup and lazy epoch authorization V178."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v178"
    for key, tag in (
        ("certificate_delta", "certificate-local-model-delta"),
        ("epoch_transition", "indexed-lazy-model-epoch-transition"),
        ("lazy_authorization", "lazy-epoch-authorization"),
        ("lazy_authorization_join", "lazy-authorization-issuance-join"),
        ("program_invalidation", "indexed-program-cache-invalidation"),
        ("delta_transition_join", "certificate-delta-transition-join"),
        ("sequence", "indexed-lazy-invalidation-sequence"),
        ("target_preregistration", "construction-k7-indexed-lazy-preregistration"),
        ("occurrence", "construction-k7-indexed-lazy-occurrence"),
        ("campaign", "construction-k7-indexed-lazy-campaign"),
        ("verification", "construction-k7-indexed-lazy-verification"),
        ("failure", "construction-k7-indexed-lazy-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V178: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V178 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V178_DOMAIN"] = _domain


def extension_content_id_v178(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V178:
        raise ValueError("domain tag is absent from V178")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V178",
    "K7_DOMAIN_TAG_EXTENSION_V178",
    "extension_content_id_v178",
)
