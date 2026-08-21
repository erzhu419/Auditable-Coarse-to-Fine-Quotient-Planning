"""Domains for automatic minimal factor dictionary V131R1."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-automatic-dictionary-factor-prior-{suffix}:v131r1"
    for key, suffix in (
        ("construction_k7_automatic_dictionary_factor_prior_preregistration_v131r1", "preregistration"),
        ("construction_k7_automatic_dictionary_factor_occurrence_v131r1", "occurrence"),
        ("construction_k7_automatic_dictionary_factor_campaign_v131r1", "campaign"),
        ("construction_k7_automatic_dictionary_factor_verification_v131r1", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V131R1: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V131R1 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v131r1(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V131R1:
        raise ValueError("domain tag is absent from V131R1")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V131R1",
            "K7_DOMAIN_TAG_EXTENSION_V131R1",
            "extension_content_id_v131r1",
        )
    )
)
