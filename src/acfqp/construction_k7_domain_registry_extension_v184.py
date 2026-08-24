"""Additive domains for fair unbounded expression synthesis in V184."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v184"
    for key, tag in (
        ("fair_search_trace", "construction-k7-fair-expression-search-trace"),
        ("synthesized_program", "construction-k7-fair-expression-synthesized-program"),
        ("compiled_model", "construction-k7-fair-expression-compiled-model"),
        ("plan_certificate", "construction-k7-fair-expression-plan-certificate"),
        ("protocol", "construction-k7-fair-expression-protocol"),
        ("manifest_reveal", "construction-k7-fair-expression-manifest-reveal"),
        ("execution_preregistration", "construction-k7-fair-expression-execution-preregistration"),
        ("campaign", "construction-k7-fair-expression-campaign"),
        ("verification", "construction-k7-fair-expression-verification"),
        ("failure", "construction-k7-fair-expression-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V184: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V184 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V184_DOMAIN"] = _domain


def extension_content_id_v184(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V184:
        raise ValueError("domain tag is absent from V184")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V184",
    "K7_DOMAIN_TAG_EXTENSION_V184",
    "extension_content_id_v184",
)
