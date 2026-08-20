"""Additive domains for the V73 reusable-model certificate campaign."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-reusable-version-space-{suffix}:v73"
    for key, suffix in (
        ("construction_k7_reusable_version_space_preregistration_v73", "preregistration"),
        ("construction_k7_reusable_version_space_occurrence_v73", "occurrence"),
        ("construction_k7_reusable_version_space_campaign_v73", "campaign"),
        ("construction_k7_reusable_version_space_verification_v73", "verification"),
        ("construction_k7_reusable_version_space_failure_v73", "failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V73: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V73 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V73) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V73 domain extension contains duplicate tags")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v73(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V73:
        raise ValueError("domain tag is absent from V73")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V73",
            "K7_DOMAIN_TAG_EXTENSION_V73",
            "extension_content_id_v73",
        )
    )
)
