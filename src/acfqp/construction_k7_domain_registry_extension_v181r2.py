"""Fresh domains for the post-resource-failure V181r2 successor."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v181r2"
    for key, tag in (
        ("protocol_successor", "construction-k7-open-world-protocol-successor"),
        ("manifest_reveal", "construction-k7-open-world-manifest-reveal"),
        ("execution_preregistration", "construction-k7-open-world-execution-preregistration"),
        ("compiled_program", "construction-k7-open-world-compiled-program"),
        ("certificate", "construction-k7-open-world-abstract-plan-certificate"),
        ("progress_checkpoint", "construction-k7-open-world-progress-checkpoint"),
        ("campaign", "construction-k7-open-world-campaign"),
        ("verification", "construction-k7-open-world-verification"),
        ("failure", "construction-k7-open-world-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V181R2: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V181R2 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V181R2_DOMAIN"] = _domain


def extension_content_id_v181r2(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V181R2:
        raise ValueError("domain tag is absent from V181r2")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V181R2",
    "K7_DOMAIN_TAG_EXTENSION_V181R2",
    "extension_content_id_v181r2",
)
