"""Fresh domains for post-coordinate dependency residual synthesis."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-post-dependency-{suffix}:v97"
    for key, suffix in (
        ("construction_k7_post_dependency_source_library_v97", "source-library"),
        ("construction_k7_post_dependency_preregistration_v97", "preregistration"),
        ("construction_k7_post_dependency_occurrence_v97", "occurrence"),
        ("construction_k7_post_dependency_campaign_v97", "campaign"),
        ("construction_k7_post_dependency_verification_v97", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V97: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V97 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V97) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V97 domain extension contains a duplicate domain")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v97(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V97:
        raise ValueError("domain tag is absent from the V97 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V97",
            "K7_DOMAIN_TAG_EXTENSION_V97",
            "extension_content_id_v97",
        )
    )
)
