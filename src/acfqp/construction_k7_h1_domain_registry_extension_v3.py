"""Third additive domain registry for phase-aware H1 normal-prefix artifacts.

Earlier extension modules are already members of frozen semantic closures.  New
59E-C artifacts therefore receive disjoint domains here instead of mutating an
older registry and silently changing its meaning.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_NORMAL_PREFIX_SPEC_V1_DOMAIN = (
    "acfqp:construction-k7-h1-normal-prefix-spec:v1"
)
CONSTRUCTION_K7_H1_NORMAL_PREFIX_ALLOCATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-normal-prefix-allocation:v1"
)
CONSTRUCTION_K7_H1_NORMAL_SITE_INTENT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-normal-site-intent:v1"
)
CONSTRUCTION_K7_H1_NORMAL_SITE_CALLBACK_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-normal-site-callback-result:v1"
)
CONSTRUCTION_K7_H1_NORMAL_SITE_EVENT_COMMIT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-normal-site-event-commit:v1"
)
CONSTRUCTION_K7_H1_NORMAL_PREFIX_CURSOR_RECORD_V1_DOMAIN = (
    "acfqp:construction-k7-h1-normal-prefix-cursor-record:v1"
)
CONSTRUCTION_K7_H1_NORMAL_PREFIX_SNAPSHOT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-normal-prefix-snapshot:v1"
)
CONSTRUCTION_K7_H1_NORMAL_PREFIX_SEMANTIC_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-normal-prefix-semantic-closure:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V3: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_normal_prefix_spec_v1": (
            CONSTRUCTION_K7_H1_NORMAL_PREFIX_SPEC_V1_DOMAIN
        ),
        "construction_k7_h1_normal_prefix_allocation_v1": (
            CONSTRUCTION_K7_H1_NORMAL_PREFIX_ALLOCATION_V1_DOMAIN
        ),
        "construction_k7_h1_normal_site_intent_v1": (
            CONSTRUCTION_K7_H1_NORMAL_SITE_INTENT_V1_DOMAIN
        ),
        "construction_k7_h1_normal_site_callback_result_v1": (
            CONSTRUCTION_K7_H1_NORMAL_SITE_CALLBACK_RESULT_V1_DOMAIN
        ),
        "construction_k7_h1_normal_site_event_commit_v1": (
            CONSTRUCTION_K7_H1_NORMAL_SITE_EVENT_COMMIT_V1_DOMAIN
        ),
        "construction_k7_h1_normal_prefix_cursor_record_v1": (
            CONSTRUCTION_K7_H1_NORMAL_PREFIX_CURSOR_RECORD_V1_DOMAIN
        ),
        "construction_k7_h1_normal_prefix_snapshot_v1": (
            CONSTRUCTION_K7_H1_NORMAL_PREFIX_SNAPSHOT_V1_DOMAIN
        ),
        "construction_k7_h1_normal_prefix_semantic_closure_v1": (
            CONSTRUCTION_K7_H1_NORMAL_PREFIX_SEMANTIC_CLOSURE_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V3 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V3.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V3) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V3
):  # pragma: no cover - module invariant
    raise RuntimeError("K7 H1 domain extension V3 contains a duplicate domain")


def extension_content_id_v3(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V3
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V3 registry")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = (
    "CONSTRUCTION_K7_H1_NORMAL_PREFIX_ALLOCATION_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NORMAL_PREFIX_CURSOR_RECORD_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NORMAL_PREFIX_SNAPSHOT_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NORMAL_PREFIX_SEMANTIC_CLOSURE_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NORMAL_PREFIX_SPEC_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NORMAL_SITE_CALLBACK_RESULT_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NORMAL_SITE_EVENT_COMMIT_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_NORMAL_SITE_INTENT_V1_DOMAIN",
    "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V3",
    "K7_H1_DOMAIN_TAG_EXTENSION_V3",
    "extension_content_id_v3",
)
