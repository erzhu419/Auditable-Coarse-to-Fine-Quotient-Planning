"""Fresh domains for the finite registered central-objective completion audit."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v179"
    for key, tag in (
        ("completion_contract", "construction-k7-finite-objective-completion-contract"),
        ("completion_audit", "construction-k7-finite-objective-completion-audit"),
        ("verification", "construction-k7-finite-objective-completion-verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V179: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V179 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V179_DOMAIN"] = _domain


def extension_content_id_v179(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V179:
        raise ValueError("domain tag is absent from V179")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V179",
    "K7_DOMAIN_TAG_EXTENSION_V179",
    "extension_content_id_v179",
)
