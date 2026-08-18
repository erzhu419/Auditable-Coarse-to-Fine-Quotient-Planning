"""Content domains for the retrospective V62 residual-factor library."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-residual-factor-{suffix}:v62"
    for key, suffix in (
        ("construction_k7_residual_factor_source_v62", "source"),
        ("construction_k7_residual_factor_library_v62", "library"),
        ("construction_k7_residual_factor_verification_v62", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V62: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V62 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_DOMAIN_TAG_EXTENSION_V62) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("V62 domain extension contains a duplicate domain")
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v62(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V62:
        raise ValueError("domain tag is absent from the V62 extension")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V62",
            "K7_DOMAIN_TAG_EXTENSION_V62",
            "extension_content_id_v62",
        )
    )
)
