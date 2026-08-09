"""Tenth additive domains for the H1 exclusive native-resource broker.

V10 is deliberately disjoint from the V8 process-local Guardian and the V9
cleanup-action journal.  In particular, no V8 ``PRESENT_LIVE`` document can
be re-labelled as the V10 ``BROKER_EXCLUSIVE_PRESENT`` authority.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-exclusive-broker-profile:v1"
)
CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_SOURCE_MANIFEST_V1_DOMAIN = (
    "acfqp:construction-k7-h1-exclusive-broker-source-manifest:v1"
)
CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_SESSION_GENESIS_V1_DOMAIN = (
    "acfqp:construction-k7-h1-exclusive-broker-session-genesis:v1"
)
CONSTRUCTION_K7_H1_EXCLUSIVE_PAYLOAD_CREATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-exclusive-payload-creation:v1"
)
CONSTRUCTION_K7_H1_EXCLUSIVE_ROLE_LAUNCH_EDGE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-exclusive-role-launch-edge:v1"
)
CONSTRUCTION_K7_H1_EXCLUSIVE_CHILD_CREDENTIAL_V1_DOMAIN = (
    "acfqp:construction-k7-h1-exclusive-child-credential:v1"
)
CONSTRUCTION_K7_H1_EXCLUSIVE_ROLE_REAP_V1_DOMAIN = (
    "acfqp:construction-k7-h1-exclusive-role-reap:v1"
)
CONSTRUCTION_K7_H1_LAST_LEGAL_REFERENCE_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-last-legal-reference-closure:v1"
)
CONSTRUCTION_K7_H1_NATIVE_CLEANUP_BARRIER_V1_DOMAIN = (
    "acfqp:construction-k7-h1-native-cleanup-barrier:v1"
)
CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_COMPLETION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-exclusive-broker-completion:v1"
)
CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_CRASH_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-exclusive-broker-crash-closure:v1"
)
CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_UNAVAILABLE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-exclusive-broker-unavailable:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V10: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_exclusive_broker_profile_v1": (
            CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_PROFILE_V1_DOMAIN
        ),
        "construction_k7_h1_exclusive_broker_source_manifest_v1": (
            CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_SOURCE_MANIFEST_V1_DOMAIN
        ),
        "construction_k7_h1_exclusive_broker_session_genesis_v1": (
            CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_SESSION_GENESIS_V1_DOMAIN
        ),
        "construction_k7_h1_exclusive_payload_creation_v1": (
            CONSTRUCTION_K7_H1_EXCLUSIVE_PAYLOAD_CREATION_V1_DOMAIN
        ),
        "construction_k7_h1_exclusive_role_launch_edge_v1": (
            CONSTRUCTION_K7_H1_EXCLUSIVE_ROLE_LAUNCH_EDGE_V1_DOMAIN
        ),
        "construction_k7_h1_exclusive_child_credential_v1": (
            CONSTRUCTION_K7_H1_EXCLUSIVE_CHILD_CREDENTIAL_V1_DOMAIN
        ),
        "construction_k7_h1_exclusive_role_reap_v1": (
            CONSTRUCTION_K7_H1_EXCLUSIVE_ROLE_REAP_V1_DOMAIN
        ),
        "construction_k7_h1_last_legal_reference_closure_v1": (
            CONSTRUCTION_K7_H1_LAST_LEGAL_REFERENCE_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_h1_native_cleanup_barrier_v1": (
            CONSTRUCTION_K7_H1_NATIVE_CLEANUP_BARRIER_V1_DOMAIN
        ),
        "construction_k7_h1_exclusive_broker_completion_v1": (
            CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_COMPLETION_V1_DOMAIN
        ),
        "construction_k7_h1_exclusive_broker_crash_closure_v1": (
            CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_CRASH_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_h1_exclusive_broker_unavailable_v1": (
            CONSTRUCTION_K7_H1_EXCLUSIVE_BROKER_UNAVAILABLE_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V10 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V10.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V10) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V10
):  # pragma: no cover - module invariant
    raise RuntimeError("K7 H1 domain extension V10 contains a duplicate domain")


def extension_content_id_v10(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V10
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V10 registry")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(
                name
                for name in globals()
                if name.startswith("CONSTRUCTION_K7_H1_")
                and name.endswith("_DOMAIN")
            ),
            "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V10",
            "K7_H1_DOMAIN_TAG_EXTENSION_V10",
            "extension_content_id_v10",
        )
    )
)
