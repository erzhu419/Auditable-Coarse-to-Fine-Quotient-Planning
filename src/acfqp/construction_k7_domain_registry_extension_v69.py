"""Fresh domains for V69 source-complete relational world models."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-source-complete-relational-{suffix}:v69"
    for key, suffix in (
        ("construction_k7_source_complete_relational_preregistration_v69", "preregistration"),
        ("construction_k7_source_complete_relational_occurrence_v69", "occurrence"),
        ("construction_k7_source_complete_relational_campaign_v69", "campaign"),
        ("construction_k7_source_complete_relational_failure_v69", "failure"),
        ("construction_k7_source_complete_relational_verification_v69", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V69: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V69 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V69) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V69 domain extension contains duplicate tags")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v69(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V69:
        raise ValueError("domain tag is absent from V69")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V69",
            "K7_DOMAIN_TAG_EXTENSION_V69",
            "extension_content_id_v69",
        )
    )
)
