"""Fresh domains for V66 combined-model online planning evidence."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-combined-model-planning-{suffix}:v66"
    for key, suffix in (
        ("construction_k7_combined_model_planning_preregistration_v66", "preregistration"),
        ("construction_k7_combined_model_planning_occurrence_v66", "occurrence"),
        ("construction_k7_combined_model_planning_campaign_v66", "campaign"),
        ("construction_k7_combined_model_planning_failure_v66", "failure"),
        ("construction_k7_combined_model_planning_verification_v66", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V66: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V66 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V66) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V66 domain extension contains duplicate tags")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v66(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V66:
        raise ValueError("domain tag is absent from V66")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V66",
            "K7_DOMAIN_TAG_EXTENSION_V66",
            "extension_content_id_v66",
        )
    )
)
