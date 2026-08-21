"""Fresh domains for persistent jointly compiled residual planning."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-persistent-multi-residual-{suffix}:v96"
    for key, suffix in (
        ("construction_k7_persistent_multi_residual_preregistration_v96", "preregistration"),
        ("construction_k7_persistent_multi_residual_occurrence_v96", "occurrence"),
        ("construction_k7_persistent_multi_residual_campaign_v96", "campaign"),
        ("construction_k7_persistent_multi_residual_verification_v96", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V96: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V96 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V96) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V96 domain extension contains a duplicate domain")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v96(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V96:
        raise ValueError("domain tag is absent from the V96 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V96",
            "K7_DOMAIN_TAG_EXTENSION_V96",
            "extension_content_id_v96",
        )
    )
)
