"""Additive content domains for the guardian-owned external process journal.

V14 is a construction-only registry extension.  It does not relabel the V10
exclusive broker, V11 output continuation, V12 cgroup admission, or V13 E4
attestation objects.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_JOURNAL_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-external-process-journal-profile:v1"
)
CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_JOURNAL_GENESIS_V1_DOMAIN = (
    "acfqp:construction-k7-h1-external-process-journal-genesis:v1"
)
CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_CREATOR_CHANNEL_V1_DOMAIN = (
    "acfqp:construction-k7-h1-external-process-creator-channel:v1"
)
CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_INTENT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-external-process-intent:v1"
)
CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_PERMIT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-external-process-permit:v1"
)
CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_ESCROW_RECEIPT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-external-process-escrow-receipt:v1"
)
CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_ESCROW_ACK_V1_DOMAIN = (
    "acfqp:construction-k7-h1-external-process-escrow-ack:v1"
)
CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_RELEASE_PREPARATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-external-process-release-preparation:v1"
)
CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_RELEASE_AUTHORIZATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-external-process-release-authorization:v1"
)
CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_TERMINAL_OBSERVATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-external-process-terminal-observation:v1"
)
CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_DIRECT_REAP_V1_DOMAIN = (
    "acfqp:construction-k7-h1-external-process-direct-reap:v1"
)
CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_CRASH_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-external-process-crash-closure:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V14: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_external_process_journal_profile_v1": (
            CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_JOURNAL_PROFILE_V1_DOMAIN
        ),
        "construction_k7_h1_external_process_journal_genesis_v1": (
            CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_JOURNAL_GENESIS_V1_DOMAIN
        ),
        "construction_k7_h1_external_process_creator_channel_v1": (
            CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_CREATOR_CHANNEL_V1_DOMAIN
        ),
        "construction_k7_h1_external_process_intent_v1": (
            CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_INTENT_V1_DOMAIN
        ),
        "construction_k7_h1_external_process_permit_v1": (
            CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_PERMIT_V1_DOMAIN
        ),
        "construction_k7_h1_external_process_escrow_receipt_v1": (
            CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_ESCROW_RECEIPT_V1_DOMAIN
        ),
        "construction_k7_h1_external_process_escrow_ack_v1": (
            CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_ESCROW_ACK_V1_DOMAIN
        ),
        "construction_k7_h1_external_process_release_preparation_v1": (
            CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_RELEASE_PREPARATION_V1_DOMAIN
        ),
        "construction_k7_h1_external_process_release_authorization_v1": (
            CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_RELEASE_AUTHORIZATION_V1_DOMAIN
        ),
        "construction_k7_h1_external_process_terminal_observation_v1": (
            CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_TERMINAL_OBSERVATION_V1_DOMAIN
        ),
        "construction_k7_h1_external_process_direct_reap_v1": (
            CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_DIRECT_REAP_V1_DOMAIN
        ),
        "construction_k7_h1_external_process_crash_closure_v1": (
            CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_CRASH_CLOSURE_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V14 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V14.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V14) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V14
):  # pragma: no cover - import-time invariant
    raise RuntimeError("K7 H1 domain extension V14 contains a duplicate domain")


def extension_content_id_v14(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V14
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V14 registry")
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
            "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V14",
            "K7_H1_DOMAIN_TAG_EXTENSION_V14",
            "extension_content_id_v14",
        )
    )
)
