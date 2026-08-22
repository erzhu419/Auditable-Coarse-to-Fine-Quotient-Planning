"""Additive domains for V160 progressive raw-prefix query synthesis."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v160"
    for key, tag in (
        (
            "source_preregistration",
            "construction-k7-progressive-raw-prefix-source-preregistration",
        ),
        (
            "classifier_receipt",
            "construction-k7-progressive-raw-prefix-classifier-receipt",
        ),
        ("acquisition", "construction-k7-progressive-raw-prefix-acquisition"),
        ("occurrence", "construction-k7-progressive-raw-prefix-occurrence"),
        ("campaign", "construction-k7-progressive-raw-prefix-campaign"),
        (
            "target_preregistration",
            "construction-k7-progressive-raw-prefix-preregistration",
        ),
        ("verification", "construction-k7-progressive-raw-prefix-verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V160: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V160 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V160_DOMAIN"] = _domain


def extension_content_id_v160(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V160:
        raise ValueError("domain tag is absent from V160")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V160",
    "K7_DOMAIN_TAG_EXTENSION_V160",
    "extension_content_id_v160",
)
