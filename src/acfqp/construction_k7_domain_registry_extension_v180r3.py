"""Fresh domains for the V180r3 all-path production execution protocol."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v180r3"
    for key, tag in (
        ("production_execution_protocol", "construction-k7-all-path-production-execution-protocol"),
        ("production_execution_slot", "construction-k7-all-path-production-execution-slot"),
        ("production_occurrence_receipt", "construction-k7-all-path-production-occurrence-receipt"),
        ("production_terminal_bundle", "construction-k7-all-path-production-terminal-bundle"),
        ("production_campaign", "construction-k7-all-path-production-campaign"),
        ("production_verification", "construction-k7-all-path-production-verification"),
        ("counter_completeness_gate", "construction-k7-counter-completeness-gate"),
        ("workload_economics", "construction-k7-workload-economics"),
        ("scalar_calibration", "construction-k7-scalar-calibration"),
        ("official_execution", "construction-k7-official-execution"),
        ("failure", "construction-k7-all-path-production-execution-failure"),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R3: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V180R3 = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V180R3_DOMAIN"] = _domain


def extension_content_id_v180r3(domain_tag: str, payload: Any) -> str:
    if type(domain_tag) is not str or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V180R3:
        raise ValueError("domain tag is absent from V180r3")
    return hashlib.sha256(
        domain_tag.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R3",
    "K7_DOMAIN_TAG_EXTENSION_V180R3",
    "extension_content_id_v180r3",
)
