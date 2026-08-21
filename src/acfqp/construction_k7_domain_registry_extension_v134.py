"""Domains for V134 source-unseen packet-batching transfer."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "construction_k7_packet_batching_transfer_preregistration_v134": (
        "acfqp:construction-k7-packet-batching-transfer-preregistration:v134"
    ),
    "construction_k7_packet_batching_transfer_occurrence_v134": (
        "acfqp:construction-k7-packet-batching-transfer-occurrence:v134"
    ),
    "construction_k7_packet_batching_transfer_campaign_v134": (
        "acfqp:construction-k7-packet-batching-transfer-campaign:v134"
    ),
    "construction_k7_packet_batching_transfer_verification_v134": (
        "acfqp:construction-k7-packet-batching-transfer-verification:v134"
    ),
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V134: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V134 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v134(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V134:
        raise ValueError("domain tag is absent from V134")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V134",
            "K7_DOMAIN_TAG_EXTENSION_V134",
            "extension_content_id_v134",
        )
    )
)
