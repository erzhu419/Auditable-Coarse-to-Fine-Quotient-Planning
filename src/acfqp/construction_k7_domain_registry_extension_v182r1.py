"""Additive runtime domains for the preregistered V182 campaign."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAINS = {
    key: f"acfqp:{role}:v182r1"
    for key, role in (
        ("manifest_reveal", "open-world-universal-machine-manifest-reveal"),
        ("execution_preregistration", "open-world-universal-machine-execution-preregistration"),
        ("progress_checkpoint", "open-world-universal-machine-progress-checkpoint"),
        ("failure", "open-world-universal-machine-campaign-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V182R1: Mapping[str, str] = MappingProxyType(
    _DOMAINS
)
K7_DOMAIN_TAG_EXTENSION_V182R1 = frozenset(_DOMAINS.values())
for _key, _domain in _DOMAINS.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V182R1_DOMAIN"] = _domain


def extension_content_id_v182r1(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V182R1:
        raise ValueError("domain tag is absent from V182r1")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V182R1",
    "K7_DOMAIN_TAG_EXTENSION_V182R1",
    "extension_content_id_v182r1",
)
