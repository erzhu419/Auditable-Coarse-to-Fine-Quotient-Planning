"""Sixth additive domain registry for H1 native-resource receipts.

The earlier H1 registries are inputs to frozen semantic closures.  Native
resource slot declarations, durable callback cells, typed resolutions, and an
exact cleanup-transition cutoff therefore receive disjoint domains here.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_NATIVE_RECEIPT_SPEC_V1_DOMAIN = (
    "acfqp:construction-k7-h1-native-receipt-spec:v1"
)
CONSTRUCTION_K7_H1_NATIVE_SLOT_DECLARATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-native-slot-declaration:v1"
)
CONSTRUCTION_K7_H1_NATIVE_RECEIPT_ALLOCATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-native-receipt-allocation:v1"
)
CONSTRUCTION_K7_H1_NATIVE_CALLBACK_START_V1_DOMAIN = (
    "acfqp:construction-k7-h1-native-callback-start:v1"
)
CONSTRUCTION_K7_H1_NATIVE_CALLBACK_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-native-callback-result:v1"
)
CONSTRUCTION_K7_H1_NATIVE_RESOURCE_RECEIPT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-native-resource-receipt:v1"
)
CONSTRUCTION_K7_H1_NATIVE_ABSENCE_RESOLUTION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-native-absence-resolution:v1"
)
CONSTRUCTION_K7_H1_NATIVE_RECEIPT_CURSOR_V1_DOMAIN = (
    "acfqp:construction-k7-h1-native-receipt-cursor:v1"
)
CONSTRUCTION_K7_H1_NATIVE_CUTOFF_SNAPSHOT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-native-cutoff-snapshot:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V6: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_native_receipt_spec_v1": (
            CONSTRUCTION_K7_H1_NATIVE_RECEIPT_SPEC_V1_DOMAIN
        ),
        "construction_k7_h1_native_slot_declaration_v1": (
            CONSTRUCTION_K7_H1_NATIVE_SLOT_DECLARATION_V1_DOMAIN
        ),
        "construction_k7_h1_native_receipt_allocation_v1": (
            CONSTRUCTION_K7_H1_NATIVE_RECEIPT_ALLOCATION_V1_DOMAIN
        ),
        "construction_k7_h1_native_callback_start_v1": (
            CONSTRUCTION_K7_H1_NATIVE_CALLBACK_START_V1_DOMAIN
        ),
        "construction_k7_h1_native_callback_result_v1": (
            CONSTRUCTION_K7_H1_NATIVE_CALLBACK_RESULT_V1_DOMAIN
        ),
        "construction_k7_h1_native_resource_receipt_v1": (
            CONSTRUCTION_K7_H1_NATIVE_RESOURCE_RECEIPT_V1_DOMAIN
        ),
        "construction_k7_h1_native_absence_resolution_v1": (
            CONSTRUCTION_K7_H1_NATIVE_ABSENCE_RESOLUTION_V1_DOMAIN
        ),
        "construction_k7_h1_native_receipt_cursor_v1": (
            CONSTRUCTION_K7_H1_NATIVE_RECEIPT_CURSOR_V1_DOMAIN
        ),
        "construction_k7_h1_native_cutoff_snapshot_v1": (
            CONSTRUCTION_K7_H1_NATIVE_CUTOFF_SNAPSHOT_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V6 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V6.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V6) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V6
):  # pragma: no cover - module invariant
    raise RuntimeError("K7 H1 domain extension V6 contains a duplicate domain")


def extension_content_id_v6(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V6
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V6 registry")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = (
    "CONSTRUCTION_K7_H1_NATIVE_ABSENCE_RESOLUTION_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NATIVE_CALLBACK_RESULT_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NATIVE_CALLBACK_START_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NATIVE_CUTOFF_SNAPSHOT_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NATIVE_RECEIPT_ALLOCATION_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NATIVE_RECEIPT_CURSOR_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NATIVE_RECEIPT_SPEC_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NATIVE_RESOURCE_RECEIPT_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NATIVE_SLOT_DECLARATION_V1_DOMAIN",
    "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V6",
    "K7_H1_DOMAIN_TAG_EXTENSION_V6",
    "extension_content_id_v6",
)
