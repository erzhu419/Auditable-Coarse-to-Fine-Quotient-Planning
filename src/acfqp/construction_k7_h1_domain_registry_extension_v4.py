"""Fourth additive domain registry for pre-admitted H1 cleanup artifacts.

The V1 phase owner and the 59E-C-A normal-prefix journal already participate in
frozen semantic closures.  Their registries therefore remain immutable; the
pre-admitted cleanup envelope and tagged V2 transition receive disjoint domains
here.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_PREADMITTED_CLEANUP_ENVELOPE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-preadmitted-cleanup-envelope:v1"
)
CONSTRUCTION_K7_H1_ATTEMPT_CLEANUP_TRANSITION_V2_DOMAIN = (
    "acfqp:construction-k7-h1-attempt-cleanup-transition:v2"
)

K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V4: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_preadmitted_cleanup_envelope_v1": (
            CONSTRUCTION_K7_H1_PREADMITTED_CLEANUP_ENVELOPE_V1_DOMAIN
        ),
        "construction_k7_h1_attempt_cleanup_transition_v2": (
            CONSTRUCTION_K7_H1_ATTEMPT_CLEANUP_TRANSITION_V2_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V4 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V4.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V4) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V4
):  # pragma: no cover - module invariant
    raise RuntimeError("K7 H1 domain extension V4 contains a duplicate domain")


def extension_content_id_v4(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V4
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V4 registry")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = (
    "CONSTRUCTION_K7_H1_ATTEMPT_CLEANUP_TRANSITION_V2_DOMAIN",
    "CONSTRUCTION_K7_H1_PREADMITTED_CLEANUP_ENVELOPE_V1_DOMAIN",
    "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V4",
    "K7_H1_DOMAIN_TAG_EXTENSION_V4",
    "extension_content_id_v4",
)
