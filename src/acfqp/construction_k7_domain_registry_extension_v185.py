"""Additive domains for observation-derived composite operators in V185."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v185"
    for key, tag in (
        ("macro_definition", "construction-k7-composite-macro-definition"),
        ("macro_library", "construction-k7-composite-macro-library"),
        ("synthesized_program", "construction-k7-composite-macro-synthesized-program"),
        ("compiled_model", "construction-k7-composite-macro-compiled-model"),
        ("plan_certificate", "construction-k7-composite-macro-plan-certificate"),
        ("protocol", "construction-k7-composite-macro-protocol"),
        ("manifest_reveal", "construction-k7-composite-macro-manifest-reveal"),
        ("execution_preregistration", "construction-k7-composite-macro-execution-preregistration"),
        ("campaign", "construction-k7-composite-macro-campaign"),
        ("verification", "construction-k7-composite-macro-verification"),
        ("failure", "construction-k7-composite-macro-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V185: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V185 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V185_DOMAIN"] = _domain


def extension_content_id_v185(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V185:
        raise ValueError("domain tag is absent from V185")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V185",
    "K7_DOMAIN_TAG_EXTENSION_V185",
    "extension_content_id_v185",
)
