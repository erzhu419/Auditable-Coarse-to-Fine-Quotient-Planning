"""Fifth additive domain registry for Owner-cleanup sidecar artifacts.

The V3/V4 Owner journals and the V2 cleanup-transition registry are frozen
inputs.  Conservative cleanup continuations therefore use a separate domain
set and never add a record kind to either historical Owner journal.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_OWNER_CLEANUP_SIDECAR_SPEC_V1_DOMAIN = (
    "acfqp:construction-k7-h1-owner-cleanup-sidecar-spec:v1"
)
CONSTRUCTION_K7_H1_OWNER_CLEANUP_SIDECAR_ALLOCATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-owner-cleanup-sidecar-allocation:v1"
)
CONSTRUCTION_K7_H1_OWNER_CLEANUP_RELEASE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-owner-cleanup-release:v1"
)
CONSTRUCTION_K7_H1_OWNER_CLEANUP_CURSOR_RECORD_V1_DOMAIN = (
    "acfqp:construction-k7-h1-owner-cleanup-cursor-record:v1"
)
CONSTRUCTION_K7_H1_OWNER_CLEANUP_COMBINED_STATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-owner-cleanup-combined-state:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V5: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_owner_cleanup_sidecar_spec_v1": (
            CONSTRUCTION_K7_H1_OWNER_CLEANUP_SIDECAR_SPEC_V1_DOMAIN
        ),
        "construction_k7_h1_owner_cleanup_sidecar_allocation_v1": (
            CONSTRUCTION_K7_H1_OWNER_CLEANUP_SIDECAR_ALLOCATION_V1_DOMAIN
        ),
        "construction_k7_h1_owner_cleanup_release_v1": (
            CONSTRUCTION_K7_H1_OWNER_CLEANUP_RELEASE_V1_DOMAIN
        ),
        "construction_k7_h1_owner_cleanup_cursor_record_v1": (
            CONSTRUCTION_K7_H1_OWNER_CLEANUP_CURSOR_RECORD_V1_DOMAIN
        ),
        "construction_k7_h1_owner_cleanup_combined_state_v1": (
            CONSTRUCTION_K7_H1_OWNER_CLEANUP_COMBINED_STATE_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V5 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V5.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V5) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V5
):  # pragma: no cover - module invariant
    raise RuntimeError("K7 H1 domain extension V5 contains a duplicate domain")


def extension_content_id_v5(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V5
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V5 registry")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = (
    "CONSTRUCTION_K7_H1_OWNER_CLEANUP_COMBINED_STATE_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_OWNER_CLEANUP_CURSOR_RECORD_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_OWNER_CLEANUP_RELEASE_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_OWNER_CLEANUP_SIDECAR_ALLOCATION_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_OWNER_CLEANUP_SIDECAR_SPEC_V1_DOMAIN",
    "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V5",
    "K7_H1_DOMAIN_TAG_EXTENSION_V5",
    "extension_content_id_v5",
)
