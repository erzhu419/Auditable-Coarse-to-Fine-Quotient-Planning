"""Fresh domains for V71 outcome-blind sample-tax calibration."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-role-free-prequential-{suffix}:v71"
    for key, suffix in (
        ("construction_k7_role_free_prequential_preregistration_v71", "preregistration"),
        ("construction_k7_role_free_prequential_occurrence_v71", "occurrence"),
        ("construction_k7_role_free_prequential_campaign_v71", "campaign"),
        ("construction_k7_role_free_prequential_failure_v71", "failure"),
        ("construction_k7_role_free_prequential_verification_v71", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V71: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V71 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V71) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V71 domain extension contains duplicate tags")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v71(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V71:
        raise ValueError("domain tag is absent from V71")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V71",
            "K7_DOMAIN_TAG_EXTENSION_V71",
            "extension_content_id_v71",
        )
    )
)
