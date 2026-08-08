"""Second additive domain registry for post-59E H1 construction artifacts.

The V1 extension is part of Contract 2.0.59-E-A's runtime semantic closure.
Later contracts therefore add domains here instead of changing those loaded
bytes and silently relabelling an already-audited closure.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_ATTEMPT_EXECUTION_PHASE_SPEC_V1_DOMAIN = (
    "acfqp:construction-k7-h1-attempt-execution-phase-spec:v1"
)
CONSTRUCTION_K7_H1_ATTEMPT_CLEANUP_TRANSITION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-attempt-cleanup-transition:v1"
)
CONSTRUCTION_K7_H1_ATTEMPT_PHASE_ALLOCATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-attempt-phase-allocation:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V2: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_attempt_execution_phase_spec_v1": (
            CONSTRUCTION_K7_H1_ATTEMPT_EXECUTION_PHASE_SPEC_V1_DOMAIN
        ),
        "construction_k7_h1_attempt_cleanup_transition_v1": (
            CONSTRUCTION_K7_H1_ATTEMPT_CLEANUP_TRANSITION_V1_DOMAIN
        ),
        "construction_k7_h1_attempt_phase_allocation_v1": (
            CONSTRUCTION_K7_H1_ATTEMPT_PHASE_ALLOCATION_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V2 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V2.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V2) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V2
):  # pragma: no cover - module invariant
    raise RuntimeError("K7 H1 domain extension V2 contains a duplicate domain")


def extension_content_id_v2(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V2
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V2 registry")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = (
    "CONSTRUCTION_K7_H1_ATTEMPT_CLEANUP_TRANSITION_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_ATTEMPT_EXECUTION_PHASE_SPEC_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_ATTEMPT_PHASE_ALLOCATION_V1_DOMAIN",
    "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V2",
    "K7_H1_DOMAIN_TAG_EXTENSION_V2",
    "extension_content_id_v2",
)
