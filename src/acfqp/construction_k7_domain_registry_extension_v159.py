"""Additive domains for V159 joint factorization/query-policy transfer."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v159"
    for key, tag in (
        ("source_preregistration", "construction-k7-joint-factor-query-source-preregistration"),
        ("classifier_receipt", "construction-k7-joint-factor-query-classifier-receipt"),
        ("acquisition", "construction-k7-joint-factor-query-acquisition"),
        ("occurrence", "construction-k7-third-dynamics-occurrence"),
        ("campaign", "construction-k7-third-dynamics-campaign"),
        ("target_preregistration", "construction-k7-third-dynamics-preregistration"),
        ("verification", "construction-k7-third-dynamics-verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V159: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V159 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V159_DOMAIN"] = _domain


def extension_content_id_v159(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V159:
        raise ValueError("domain tag is absent from V159")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V159",
    "K7_DOMAIN_TAG_EXTENSION_V159",
    "extension_content_id_v159",
)
