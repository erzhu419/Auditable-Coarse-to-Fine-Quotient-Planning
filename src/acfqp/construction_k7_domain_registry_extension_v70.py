"""Fresh domains for V70 role-free relational transfer."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-role-free-relational-{suffix}:v70"
    for key, suffix in (
        ("construction_k7_role_free_relational_library_v70", "library"),
        ("construction_k7_role_free_relational_preregistration_v70", "preregistration"),
        ("construction_k7_role_free_relational_occurrence_v70", "occurrence"),
        ("construction_k7_role_free_relational_campaign_v70", "campaign"),
        ("construction_k7_role_free_relational_failure_v70", "failure"),
        ("construction_k7_role_free_relational_verification_v70", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V70: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V70 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V70) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V70 domain extension contains duplicate tags")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v70(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V70:
        raise ValueError("domain tag is absent from V70")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V70",
            "K7_DOMAIN_TAG_EXTENSION_V70",
            "extension_content_id_v70",
        )
    )
)
