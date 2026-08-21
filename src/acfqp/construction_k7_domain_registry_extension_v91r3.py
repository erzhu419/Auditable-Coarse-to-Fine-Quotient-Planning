"""Fresh domains for corrected V91r3 source-model acceptance."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-source-model-acceptance-{suffix}:v91r3"
    for key, suffix in (
        (
            "construction_k7_source_model_acceptance_preregistration_v91r3",
            "preregistration",
        ),
        (
            "construction_k7_source_model_acceptance_result_v91r3",
            "result",
        ),
        (
            "construction_k7_source_model_acceptance_verification_v91r3",
            "verification",
        ),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V91R3: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V91R3 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V91R3) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V91r3 domain extension contains a duplicate domain")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v91r3(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V91R3
    ):
        raise ValueError("domain tag is absent from the V91r3 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V91R3",
            "K7_DOMAIN_TAG_EXTENSION_V91R3",
            "extension_content_id_v91r3",
        )
    )
)
