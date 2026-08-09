"""Ninth additive domain registry for the H1 cleanup-action journal.

The registry is deliberately disjoint from the V2 cleanup transition, V6
native-receipt journal, V7 cleanup-budget admission and V8 process-local
guardian.  V9 joins those objects without relabelling any of them.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_CLEANUP_CUTOFF_JOIN_V1_DOMAIN = (
    "acfqp:construction-k7-h1-cleanup-cutoff-join:v1"
)
CONSTRUCTION_K7_H1_CLEANUP_ACTION_MANIFEST_V1_DOMAIN = (
    "acfqp:construction-k7-h1-cleanup-action-manifest:v1"
)
CONSTRUCTION_K7_H1_CLEANUP_ACTION_DEFINITION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-cleanup-action-definition:v1"
)
CONSTRUCTION_K7_H1_CLEANUP_JOURNAL_ALLOCATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-cleanup-journal-allocation:v1"
)
CONSTRUCTION_K7_H1_CLEANUP_ACTION_INTENT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-cleanup-action-intent:v1"
)
CONSTRUCTION_K7_H1_CLEANUP_PIDFD_PREOBSERVATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-cleanup-pidfd-preobservation:v1"
)
CONSTRUCTION_K7_H1_CLEANUP_ACTION_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-cleanup-action-result:v1"
)
CONSTRUCTION_K7_H1_CLEANUP_JOURNAL_CURSOR_V1_DOMAIN = (
    "acfqp:construction-k7-h1-cleanup-journal-cursor:v1"
)
CONSTRUCTION_K7_H1_CLEANUP_DRAIN_SNAPSHOT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-cleanup-drain-snapshot:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V9: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_cleanup_cutoff_join_v1": (
            CONSTRUCTION_K7_H1_CLEANUP_CUTOFF_JOIN_V1_DOMAIN
        ),
        "construction_k7_h1_cleanup_action_manifest_v1": (
            CONSTRUCTION_K7_H1_CLEANUP_ACTION_MANIFEST_V1_DOMAIN
        ),
        "construction_k7_h1_cleanup_action_definition_v1": (
            CONSTRUCTION_K7_H1_CLEANUP_ACTION_DEFINITION_V1_DOMAIN
        ),
        "construction_k7_h1_cleanup_journal_allocation_v1": (
            CONSTRUCTION_K7_H1_CLEANUP_JOURNAL_ALLOCATION_V1_DOMAIN
        ),
        "construction_k7_h1_cleanup_action_intent_v1": (
            CONSTRUCTION_K7_H1_CLEANUP_ACTION_INTENT_V1_DOMAIN
        ),
        "construction_k7_h1_cleanup_pidfd_preobservation_v1": (
            CONSTRUCTION_K7_H1_CLEANUP_PIDFD_PREOBSERVATION_V1_DOMAIN
        ),
        "construction_k7_h1_cleanup_action_result_v1": (
            CONSTRUCTION_K7_H1_CLEANUP_ACTION_RESULT_V1_DOMAIN
        ),
        "construction_k7_h1_cleanup_journal_cursor_v1": (
            CONSTRUCTION_K7_H1_CLEANUP_JOURNAL_CURSOR_V1_DOMAIN
        ),
        "construction_k7_h1_cleanup_drain_snapshot_v1": (
            CONSTRUCTION_K7_H1_CLEANUP_DRAIN_SNAPSHOT_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V9 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V9.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V9) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V9
):  # pragma: no cover - module invariant
    raise RuntimeError("K7 H1 domain extension V9 contains a duplicate domain")


def extension_content_id_v9(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V9
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V9 registry")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = (
    "CONSTRUCTION_K7_H1_CLEANUP_ACTION_DEFINITION_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_CLEANUP_ACTION_INTENT_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_CLEANUP_ACTION_MANIFEST_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_CLEANUP_ACTION_RESULT_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_CLEANUP_CUTOFF_JOIN_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_CLEANUP_DRAIN_SNAPSHOT_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_CLEANUP_JOURNAL_ALLOCATION_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_CLEANUP_JOURNAL_CURSOR_V1_DOMAIN",
    "CONSTRUCTION_K7_H1_CLEANUP_PIDFD_PREOBSERVATION_V1_DOMAIN",
    "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V9",
    "K7_H1_DOMAIN_TAG_EXTENSION_V9",
    "extension_content_id_v9",
)
