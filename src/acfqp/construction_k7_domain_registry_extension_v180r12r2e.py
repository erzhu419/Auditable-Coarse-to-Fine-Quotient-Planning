"""Sub-record domains for the V180r12r2 production aggregation."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    key: f"acfqp:{tag}:v180r12r2e"
    for key, tag in (
        ("source_receipt", "construction-k7-ten-terminal-source-verification-receipt"),
        (
            "route_component_chain_receipt",
            "construction-k7-route-component-chain-receipt",
        ),
        ("terminal_receipt", "construction-k7-ten-terminal-chain-receipt"),
        (
            "terminal_shared_receipt",
            "construction-k7-terminal-shared-resource-receipt",
        ),
        (
            "terminal_receipt_set",
            "construction-k7-terminal-shared-resource-receipt-set",
        ),
        (
            "v180r7r1_construction_axis_receipt",
            "construction-k7-v180r7r1-construction-axis-receipt",
        ),
        (
            "campaign_counter_record",
            "construction-k7-campaign-scope-counter-record-receipt",
        ),
        (
            "campaign_receipt_set",
            "construction-k7-campaign-scope-shared-resource-receipt-set",
        ),
        ("campaign_work_vector", "construction-k7-campaign-scope-work-vector"),
        (
            "campaign_comparison_vector",
            "construction-k7-campaign-scope-comparison-vector",
        ),
        (
            "campaign_projection_proof",
            "construction-k7-campaign-scope-projection-proof",
        ),
        (
            "campaign_native_zero_attestation",
            "construction-k7-campaign-scope-native-zero-attestation",
        ),
        (
            "campaign_accounting_chain",
            "construction-k7-campaign-scope-accounting-chain",
        ),
        (
            "campaign_structural_boundary",
            "construction-k7-campaign-scope-structural-boundary",
        ),
    )
}
K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R2E: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_DOMAIN_TAG_EXTENSION_V180R12R2E = frozenset(_DOMAIN_BY_KEY.values())
for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"CONSTRUCTION_K7_{_key.upper()}_V180R12R2E_DOMAIN"] = _domain


def extension_content_id_v180r12r2e(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_DOMAIN_TAG_EXTENSION_V180R12R2E
    ):
        raise ValueError("domain tag is absent from V180r12r2e")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("_DOMAIN")) + (
    "K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R2E",
    "K7_DOMAIN_TAG_EXTENSION_V180R12R2E",
    "extension_content_id_v180r12r2e",
)
