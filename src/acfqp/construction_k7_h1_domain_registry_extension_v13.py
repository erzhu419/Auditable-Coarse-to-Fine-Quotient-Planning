"""Additive content domains for the E5B-A E4 authority attestation."""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_E4_IN_SUPERVISOR_ATTESTATION_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e4-in-supervisor-attestation-profile:v1"
)
CONSTRUCTION_K7_H1_E4_IN_SUPERVISOR_AUTHORITATIVE_ATTESTATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e4-in-supervisor-authoritative-attestation:v1"
)
CONSTRUCTION_K7_H1_E4_GUARDIAN_PERSISTED_REPLAY_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e4-guardian-persisted-replay:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V13: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_e4_in_supervisor_attestation_profile_v1": (
            CONSTRUCTION_K7_H1_E4_IN_SUPERVISOR_ATTESTATION_PROFILE_V1_DOMAIN
        ),
        "construction_k7_h1_e4_in_supervisor_authoritative_attestation_v1": (
            CONSTRUCTION_K7_H1_E4_IN_SUPERVISOR_AUTHORITATIVE_ATTESTATION_V1_DOMAIN
        ),
        "construction_k7_h1_e4_guardian_persisted_replay_v1": (
            CONSTRUCTION_K7_H1_E4_GUARDIAN_PERSISTED_REPLAY_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V13 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V13.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V13) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V13
):  # pragma: no cover - import-time invariant
    raise RuntimeError("K7 H1 domain extension V13 contains a duplicate domain")


def extension_content_id_v13(domain_tag: str, payload: Any) -> str:
    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V13
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V13 registry")
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
            "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V13",
            "K7_H1_DOMAIN_TAG_EXTENSION_V13",
            "extension_content_id_v13",
        )
    )
)
