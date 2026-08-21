"""Domains for the standalone generic model-epoch carrier V125."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-standalone-generic-model-{suffix}:v125"
    for key, suffix in (
        ("construction_k7_standalone_generic_model_preregistration_v125", "preregistration"),
        ("construction_k7_standalone_generic_model_state_v125", "state"),
        ("construction_k7_standalone_generic_model_bootstrap_v125", "bootstrap"),
        ("construction_k7_standalone_generic_model_update_v125", "update"),
        ("construction_k7_standalone_generic_model_match_v125", "match"),
        ("construction_k7_standalone_generic_model_sequence_v125", "sequence"),
        ("construction_k7_standalone_generic_model_occurrence_v125", "occurrence"),
        ("construction_k7_standalone_generic_model_campaign_v125", "campaign"),
        ("construction_k7_standalone_generic_model_verification_v125", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V125: Mapping[str, str] = MappingProxyType(_DOMAIN_BY_KEY)
K7_DOMAIN_TAG_EXTENSION_V125 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v125(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V125:
        raise ValueError("domain tag is absent from V125")
    return hashlib.sha256(domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V125",
            "K7_DOMAIN_TAG_EXTENSION_V125",
            "extension_content_id_v125",
        )
    )
)
