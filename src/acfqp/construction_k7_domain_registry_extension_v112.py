"""Fresh domains for symmetrically accounted identity validation V112."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:construction-k7-symmetric-epoch-accounting-{suffix}:v112"
    for key, suffix in (
        ("construction_k7_symmetric_epoch_accounting_preregistration_v112", "preregistration"),
        ("construction_k7_symmetric_epoch_accounting_occurrence_v112", "occurrence"),
        ("construction_k7_symmetric_epoch_accounting_campaign_v112", "campaign"),
        ("construction_k7_symmetric_epoch_accounting_verification_v112", "verification"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V112: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V112 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v112(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V112:
        raise ValueError("domain tag is absent from V112")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V112",
            "K7_DOMAIN_TAG_EXTENSION_V112",
            "extension_content_id_v112",
        )
    )
)
