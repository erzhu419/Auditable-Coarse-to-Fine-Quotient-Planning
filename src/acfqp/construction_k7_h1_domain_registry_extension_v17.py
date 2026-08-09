"""One additive domain for the consumed B2-B cleanup barrier.

The existing V15 native-cleanup barrier describes revocation before any
permit consumption.  A durable barrier after an observed birth, exact reap,
and bounded V16 peak is a different role and must not reuse that domain.
Registration alone grants no launch, cleanup, accounting, or official
authority.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_CONSUMED_CLEANUP_BARRIER_V1_DOMAIN = (
    "acfqp:construction-k7-h1-guardian-runtime-consumed-cleanup-barrier:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V17: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_guardian_runtime_consumed_cleanup_barrier_v1": (
            CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_CONSUMED_CLEANUP_BARRIER_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V17 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V17.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V17) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V17
):  # pragma: no cover - import-time invariant
    raise RuntimeError("K7 H1 domain extension V17 contains a duplicate domain")


def extension_content_id_v17(domain_tag: str, payload: Any) -> str:
    """Hash only the registered V17 consumed-cleanup payload."""

    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V17
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V17 registry")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = (
    "CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_CONSUMED_CLEANUP_BARRIER_V1_DOMAIN",
    "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V17",
    "K7_H1_DOMAIN_TAG_EXTENSION_V17",
    "extension_content_id_v17",
)
