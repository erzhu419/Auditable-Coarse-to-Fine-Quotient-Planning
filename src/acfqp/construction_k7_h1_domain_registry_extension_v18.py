"""Additive domains for a future live two-birth construction prefix.

The V18 roles separate execution-source closure, nested credential evidence,
the live checkpoint, and protocol-failure closure.  They do not relabel any
V12 cgroup, V15 E3 V2, V16 supervisor-birth, or V17 consumed-cleanup object.
Registration alone grants no runtime, accounting, current-access, or official
authority.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_TWO_BIRTH_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-two-birth-execution-source-closure:v1"
)
CONSTRUCTION_K7_H1_NESTED_PROBE_CREDENTIAL_OBSERVATION_BUNDLE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-nested-probe-credential-observation-bundle:v1"
)
CONSTRUCTION_K7_H1_LIVE_TWO_BIRTH_PREFIX_CHECKPOINT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-live-two-birth-prefix-checkpoint:v1"
)
CONSTRUCTION_K7_H1_TWO_BIRTH_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-two-birth-protocol-failure-closure:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V18: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_two_birth_execution_source_closure_v1": (
            CONSTRUCTION_K7_H1_TWO_BIRTH_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_h1_nested_probe_credential_observation_bundle_v1": (
            CONSTRUCTION_K7_H1_NESTED_PROBE_CREDENTIAL_OBSERVATION_BUNDLE_V1_DOMAIN
        ),
        "construction_k7_h1_live_two_birth_prefix_checkpoint_v1": (
            CONSTRUCTION_K7_H1_LIVE_TWO_BIRTH_PREFIX_CHECKPOINT_V1_DOMAIN
        ),
        "construction_k7_h1_two_birth_protocol_failure_closure_v1": (
            CONSTRUCTION_K7_H1_TWO_BIRTH_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V18 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V18.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V18) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V18
):  # pragma: no cover - import-time invariant
    raise RuntimeError("K7 H1 domain extension V18 contains a duplicate domain")


def extension_content_id_v18(domain_tag: str, payload: Any) -> str:
    """Hash only one pre-registered V18 two-birth payload."""

    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V18
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V18 registry")
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
            "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V18",
            "K7_H1_DOMAIN_TAG_EXTENSION_V18",
            "extension_content_id_v18",
        )
    )
)
