"""Fresh domains for reverse-index-only invalidation V177."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v177"
    for key, tag in (
        ("certificate_delta", "certificate-local-model-delta"),
        ("epoch_transition", "reverse-index-model-epoch-transition"),
        ("delta_transition_join", "certificate-delta-transition-join"),
        ("sequence", "reverse-index-incremental-revalidation-sequence"),
        ("target_preregistration", "construction-k7-reverse-index-preregistration"),
        ("occurrence", "construction-k7-reverse-index-occurrence"),
        ("campaign", "construction-k7-reverse-index-campaign"),
        ("verification", "construction-k7-reverse-index-verification"),
        ("failure", "construction-k7-reverse-index-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V177: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V177 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V177_DOMAIN"] = _domain


def extension_content_id_v177(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V177:
        raise ValueError("domain tag is absent from V177")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V177",
    "K7_DOMAIN_TAG_EXTENSION_V177",
    "extension_content_id_v177",
)
