"""Domains for the anonymous relational template instantiator V147."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "instantiation": "acfqp:construction-k7-anonymous-relational-instantiation:v147",
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V147: Mapping[str, str] = MappingProxyType(_DOMAIN_BY_KEY)
K7_DOMAIN_TAG_EXTENSION_V147 = frozenset(_DOMAIN_BY_KEY.values())
CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_INSTANTIATION_V147_DOMAIN = _DOMAIN_BY_KEY["instantiation"]


def extension_content_id_v147(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V147:
        raise ValueError("domain tag is absent from V147")
    return hashlib.sha256(domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


__all__ = (
    "CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_INSTANTIATION_V147_DOMAIN",
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V147",
    "K7_DOMAIN_TAG_EXTENSION_V147",
    "extension_content_id_v147",
)
