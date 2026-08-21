"""Fresh domains for the V91r2 prior-only source-acquisition successor."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-prior-only-occurrence-source-{suffix}:v91r2"
    for key, suffix in (
        (
            "construction_k7_prior_only_occurrence_source_preregistration_v91r2",
            "preregistration",
        ),
        (
            "construction_k7_prior_only_occurrence_source_partial_acquisition_v91r2",
            "partial-acquisition",
        ),
        (
            "construction_k7_prior_only_occurrence_source_member_v91r2",
            "member",
        ),
        (
            "construction_k7_prior_only_occurrence_source_campaign_v91r2",
            "campaign",
        ),
        (
            "construction_k7_prior_only_occurrence_source_verification_v91r2",
            "verification",
        ),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V91R2: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V91R2 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V91R2) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V91r2 domain extension contains a duplicate domain")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v91r2(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V91R2
    ):
        raise ValueError("domain tag is absent from the V91r2 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V91R2",
            "K7_DOMAIN_TAG_EXTENSION_V91R2",
            "extension_content_id_v91r2",
        )
    )
)
