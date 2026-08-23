"""Fresh domains for receipt-driven minimal dependency invalidation V174."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v174"
    for key, tag in (
        ("dependency_projection", "online-plan-dependency-projection"),
        ("online_plan_issuance", "online-dependent-plan-issuance"),
        ("online_execution_join", "online-dependent-plan-execution-join"),
        ("epoch_transition", "receipt-driven-model-epoch-transition"),
        ("program_invalidation", "receipt-driven-program-cache-invalidation"),
        ("sequence", "receipt-driven-incremental-revalidation-sequence"),
        ("target_preregistration", "construction-k7-receipt-invalidation-preregistration"),
        ("occurrence", "construction-k7-receipt-invalidation-occurrence"),
        ("campaign", "construction-k7-receipt-invalidation-campaign"),
        ("verification", "construction-k7-receipt-invalidation-verification"),
        ("failure", "construction-k7-receipt-invalidation-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V174: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V174 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V174_DOMAIN"] = _domain


def extension_content_id_v174(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V174:
        raise ValueError("domain tag is absent from V174")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V174",
    "K7_DOMAIN_TAG_EXTENSION_V174",
    "extension_content_id_v174",
)
