"""Fresh domains for V68 relational residual world-model planning."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-relational-world-model-{suffix}:v68"
    for key, suffix in (
        ("construction_k7_relational_world_model_preregistration_v68", "preregistration"),
        ("construction_k7_relational_world_model_occurrence_v68", "occurrence"),
        ("construction_k7_relational_world_model_campaign_v68", "campaign"),
        ("construction_k7_relational_world_model_failure_v68", "failure"),
        ("construction_k7_relational_world_model_verification_v68", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V68: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V68 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V68) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V68 domain extension contains duplicate tags")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v68(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V68:
        raise ValueError("domain tag is absent from V68")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V68",
            "K7_DOMAIN_TAG_EXTENSION_V68",
            "extension_content_id_v68",
        )
    )
)
