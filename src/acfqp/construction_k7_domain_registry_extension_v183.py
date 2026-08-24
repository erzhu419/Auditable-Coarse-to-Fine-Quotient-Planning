"""Additive domains for proof-carrying unbounded-input machine models."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAINS = {
    key: f"acfqp:{role}:v183"
    for key, role in (
        ("termination_certificate", "ranked-machine-termination-certificate"),
        ("program", "ranked-machine-program"),
        ("compiled_model", "ranked-machine-compiled-world-model"),
        ("plan_certificate", "ranked-machine-plan-certificate"),
        ("protocol", "ranked-machine-campaign-protocol"),
        ("manifest_reveal", "ranked-machine-manifest-reveal"),
        ("execution_preregistration", "ranked-machine-execution-preregistration"),
        ("campaign", "ranked-machine-campaign"),
        ("verification", "ranked-machine-independent-verification"),
        ("failure", "ranked-machine-campaign-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V183: Mapping[str, str] = MappingProxyType(_DOMAINS)
K7_DOMAIN_TAG_EXTENSION_V183 = frozenset(_DOMAINS.values())
for _key, _domain in _DOMAINS.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V183_DOMAIN"] = _domain


def extension_content_id_v183(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V183:
        raise ValueError("domain tag is absent from V183")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V183",
    "K7_DOMAIN_TAG_EXTENSION_V183",
    "extension_content_id_v183",
)
