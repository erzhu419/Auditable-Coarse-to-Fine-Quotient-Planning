"""Domains for heterogeneous source-archive cohort selection V137."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "construction_k7_heterogeneous_archive_dictionary_v137": (
        "acfqp:construction-k7-heterogeneous-archive-dictionary:v137"
    ),
    "construction_k7_heterogeneous_archive_verification_v137": (
        "acfqp:construction-k7-heterogeneous-archive-verification:v137"
    ),
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V137: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V137 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v137(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V137:
        raise ValueError("domain tag is absent from V137")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V137",
            "K7_DOMAIN_TAG_EXTENSION_V137",
            "extension_content_id_v137",
        )
    )
)
