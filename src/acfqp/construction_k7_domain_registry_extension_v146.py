"""Domains for the anonymous relational factor bank V146."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "bank": "acfqp:construction-k7-anonymous-relational-factor-bank:v146",
    "verification": "acfqp:construction-k7-anonymous-relational-factor-bank-verification:v146",
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V146: Mapping[str, str] = MappingProxyType(_DOMAIN_BY_KEY)
K7_DOMAIN_TAG_EXTENSION_V146 = frozenset(_DOMAIN_BY_KEY.values())
CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_FACTOR_BANK_V146_DOMAIN = _DOMAIN_BY_KEY["bank"]
CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_FACTOR_BANK_VERIFICATION_V146_DOMAIN = _DOMAIN_BY_KEY["verification"]


def extension_content_id_v146(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V146:
        raise ValueError("domain tag is absent from V146")
    return hashlib.sha256(domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


__all__ = (
    "CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_FACTOR_BANK_V146_DOMAIN",
    "CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_FACTOR_BANK_VERIFICATION_V146_DOMAIN",
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V146",
    "K7_DOMAIN_TAG_EXTENSION_V146",
    "extension_content_id_v146",
)
