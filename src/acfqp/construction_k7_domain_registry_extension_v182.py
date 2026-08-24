"""Domain-separated identities for the V182 universal-machine successor."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAINS = {
    key: f"acfqp:{role}:v182"
    for key, role in (
        ("raw_observation", "open-world-universal-machine-raw-observation"),
        ("machine_program", "open-world-universal-machine-program"),
        ("compiled_model", "open-world-universal-machine-compiled-model"),
        ("certificate", "open-world-universal-machine-certificate"),
        ("preregistration", "open-world-universal-machine-preregistration"),
        ("campaign", "open-world-universal-machine-campaign"),
        ("verification", "open-world-universal-machine-verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V182: Mapping[str, str] = MappingProxyType(
    _DOMAINS
)
K7_DOMAIN_TAG_EXTENSION_V182 = frozenset(_DOMAINS.values())
for _key, _domain in _DOMAINS.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V182_DOMAIN"] = _domain


def extension_content_id_v182(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V182:
        raise ValueError("domain tag is absent from V182")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V182",
    "K7_DOMAIN_TAG_EXTENSION_V182",
    "extension_content_id_v182",
)
