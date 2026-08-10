"""Additive domains for the B2-B V2 handoff and later B2-D V19 run.

This registry is deliberately disjoint from the frozen V15--V18 roles.  The
first bounded consumer uses only the guardian-V2 preregistration, source,
genesis, intent, permit, handoff, revoke, cancellation, and failure roles.
The remaining tags are reserved now so a later three-birth runner does not
reinterpret an already-issued guardian artifact.  Registration alone issues
no process, topology, accounting, current-access, or official authority.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_DOMAIN_BY_KEY = {
    "construction_k7_h1_guardian_runtime_v2_preregistration_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-preregistration:v1"
    ),
    "construction_k7_h1_guardian_runtime_v2_source_closure_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-source-closure:v1"
    ),
    "construction_k7_h1_guardian_runtime_v2_genesis_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-genesis:v1"
    ),
    "construction_k7_h1_guardian_runtime_v2_birth_intent_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-birth-intent:v1"
    ),
    "construction_k7_h1_guardian_runtime_v2_birth_permit_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-birth-permit:v1"
    ),
    "construction_k7_h1_guardian_runtime_v2_public_handoff_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-public-handoff:v1"
    ),
    "construction_k7_h1_guardian_runtime_v2_unconsumed_revoke_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-unconsumed-revoke:v1"
    ),
    "construction_k7_h1_guardian_runtime_v2_cancellation_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-cancellation:v1"
    ),
    "construction_k7_h1_guardian_runtime_v2_failure_closure_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-failure-closure:v1"
    ),
    "construction_k7_h1_guardian_runtime_v2_consumer_adapter_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-consumer-adapter:v1"
    ),
    "construction_k7_h1_guardian_runtime_v2_takeover_preparation_v1": (
        "acfqp:construction-k7-h1-guardian-runtime-v2-takeover-preparation:v1"
    ),
    "construction_k7_h1_supervisor_v2_launch_preparation_v1": (
        "acfqp:construction-k7-h1-supervisor-v2-launch-preparation:v1"
    ),
    "construction_k7_h1_supervisor_v2_permit_consumption_v1": (
        "acfqp:construction-k7-h1-supervisor-v2-permit-consumption:v1"
    ),
    "construction_k7_h1_supervisor_v2_probe_reap_bundle_v1": (
        "acfqp:construction-k7-h1-supervisor-v2-probe-reap-bundle:v1"
    ),
    "construction_k7_h1_broker_command_consumption_v1": (
        "acfqp:construction-k7-h1-broker-command-consumption:v1"
    ),
    "construction_k7_h1_broker_live_observation_bundle_v1": (
        "acfqp:construction-k7-h1-broker-live-observation-bundle:v1"
    ),
    "construction_k7_h1_lease_bound_three_birth_checkpoint_v1": (
        "acfqp:construction-k7-h1-lease-bound-three-birth-checkpoint:v1"
    ),
    "construction_k7_h1_three_birth_protocol_failure_closure_v1": (
        "acfqp:construction-k7-h1-three-birth-protocol-failure-closure:v1"
    ),
    "construction_k7_h1_three_birth_lifecycle_closure_v1": (
        "acfqp:construction-k7-h1-three-birth-lifecycle-closure:v1"
    ),
}

K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V19: Mapping[str, str] = MappingProxyType(
    _DOMAIN_BY_KEY
)
K7_H1_DOMAIN_TAG_EXTENSION_V19 = frozenset(_DOMAIN_BY_KEY.values())
if len(K7_H1_DOMAIN_TAG_EXTENSION_V19) != len(_DOMAIN_BY_KEY):  # pragma: no cover
    raise RuntimeError("K7 H1 domain extension V19 contains a duplicate domain")

for _key, _domain in _DOMAIN_BY_KEY.items():
    globals()[f"{_key.upper()}_DOMAIN"] = _domain


def extension_content_id_v19(domain_tag: str, payload: Any) -> str:
    """Hash exactly one registered V19 role with its domain separator."""

    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V19
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V19 registry")
    return hashlib.sha256(
        domain_tag.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


__all__ = tuple(
    sorted(
        (
            *(name for name in globals() if name.endswith("_DOMAIN")),
            "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V19",
            "K7_H1_DOMAIN_TAG_EXTENSION_V19",
            "extension_content_id_v19",
        )
    )
)
