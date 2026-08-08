"""Explicit post-anchor domain registry for K7 H1 construction successors.

The original :mod:`acfqp.phase3e_ids` bytes are part of the caller-pinned 59A
component boundary and therefore cannot be edited without invalidating that
historical anchor.  This additive registry gives later construction schemas
their own non-overlapping domains while reusing the exact canonical JSON value
language and SHA-256 framing.  A later source-authority revision must bind this
extension as an additional component; it does not rewrite the historical
registry or claim that the old component set was transitive.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V4_WAL_BINDING_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-owner-v4-wal-binding:v1"
)
CONSTRUCTION_K7_H1_PREFIX_VERIFIER_SEMANTIC_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-prefix-verifier-semantic-closure:v1"
)
CONSTRUCTION_K7_H1_TAIL_BOUND_PREFIX_ATTESTATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-tail-bound-prefix-attestation:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V1: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_shared_cap_owner_v4_wal_binding_v1": (
            CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V4_WAL_BINDING_V1_DOMAIN
        ),
        "construction_k7_h1_prefix_verifier_semantic_closure_v1": (
            CONSTRUCTION_K7_H1_PREFIX_VERIFIER_SEMANTIC_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_h1_tail_bound_prefix_attestation_v1": (
            CONSTRUCTION_K7_H1_TAIL_BOUND_PREFIX_ATTESTATION_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V1 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V1.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V1) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V1
):  # pragma: no cover - module invariant
    raise RuntimeError("K7 H1 domain extension contains a duplicate domain")


def extension_content_id_v1(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V1
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 extension registry")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = (
    "CONSTRUCTION_K7_H1_PREFIX_VERIFIER_SEMANTIC_CLOSURE_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V4_WAL_BINDING_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_TAIL_BOUND_PREFIX_ATTESTATION_V1_DOMAIN",
    "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V1",
    "K7_H1_DOMAIN_TAG_EXTENSION_V1",
    "extension_content_id_v1",
)
