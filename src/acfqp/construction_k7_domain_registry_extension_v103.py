"""Fresh domains for receipt-verified abstract utilization."""

from __future__ import annotations
import hashlib
from types import MappingProxyType
from typing import Any, Mapping
from acfqp.phase3e_ids import canonical_json_bytes

_DOMAIN_BY_KEY = {key: f"acfqp:construction-k7-receipted-utilization-{suffix}:v103" for key, suffix in (
    ("construction_k7_receipted_utilization_preregistration_v103", "preregistration"),
    ("construction_k7_receipted_utilization_occurrence_v103", "occurrence"),
    ("construction_k7_receipted_utilization_campaign_v103", "campaign"),
    ("construction_k7_receipted_utilization_verification_v103", "verification"),
)}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V103: Mapping[str, str] = MappingProxyType(_DOMAIN_BY_KEY)
K7_DOMAIN_TAG_EXTENSION_V103 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items(): globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v103(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V103: raise ValueError("domain tag is absent from V103")
    return hashlib.sha256(domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)).hexdigest()


__all__ = tuple(sorted((*(name for name in globals() if name.endswith("_DOMAIN")), "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V103", "K7_DOMAIN_TAG_EXTENSION_V103", "extension_content_id_v103")))
