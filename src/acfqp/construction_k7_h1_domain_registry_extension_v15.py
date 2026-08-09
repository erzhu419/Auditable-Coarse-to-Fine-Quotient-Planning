"""Reserved domains for the staged actual-observed E3 V2 contract.

V15 is a specification-only additive registry.  Registering these domains
does not implement the first runtime slice, upgrade V10 E3 or V14 journal
objects, or issue any process, peak, accounting, current-access, V7, or
official authority.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-actual-observed-e3-v2-profile:v1"
)
CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_STAGE_PLAN_V1_DOMAIN = (
    "acfqp:construction-k7-h1-actual-observed-e3-v2-stage-plan:v1"
)
CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-actual-observed-e3-v2-execution-source-closure:v1"
)
CONSTRUCTION_K7_H1_ROUTE_WIDE_RUNTIME_LEASE_SUCCESSOR_V1_DOMAIN = (
    "acfqp:construction-k7-h1-route-wide-runtime-lease-successor:v1"
)
CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_GUARDIAN_SESSION_GENESIS_V1_DOMAIN = (
    "acfqp:construction-k7-h1-actual-observed-e3-v2-guardian-session-genesis:v1"
)
CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_INTENT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-actual-process-birth-intent:v1"
)
CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_PERMIT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-actual-process-birth-permit:v1"
)
CONSTRUCTION_K7_H1_SHARED_PID_CELL_BINDING_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-pid-cell-binding:v1"
)
CONSTRUCTION_K7_H1_PIDFD_ESCROW_RECEIPT_V2_DOMAIN = (
    "acfqp:construction-k7-h1-pidfd-escrow-receipt:v2"
)
CONSTRUCTION_K7_H1_CGROUP_MEMBERSHIP_OBSERVATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-cgroup-membership-observation:v1"
)
CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_OBSERVATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-actual-process-birth-observation:v1"
)
CONSTRUCTION_K7_H1_GUARDIAN_BIRTH_ACK_V1_DOMAIN = (
    "acfqp:construction-k7-h1-guardian-birth-ack:v1"
)
CONSTRUCTION_K7_H1_ACTUAL_PROCESS_CREATOR_RELEASE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-actual-process-creator-release:v1"
)
CONSTRUCTION_K7_H1_ACTUAL_PROCESS_DEATH_OBSERVATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-actual-process-death-observation:v1"
)
CONSTRUCTION_K7_H1_ACTUAL_PROCESS_CREATOR_REAP_ATTESTATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-actual-process-creator-reap-attestation:v1"
)
CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_NATIVE_CLEANUP_BARRIER_V1_DOMAIN = (
    "acfqp:construction-k7-h1-actual-observed-e3-v2-native-cleanup-barrier:v1"
)
CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_COMPLETION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-actual-observed-e3-v2-completion:v1"
)
CONSTRUCTION_K7_H1_E4_V2_LIVE_SUPERVISOR_CONTEXT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e4-v2-live-supervisor-context:v1"
)
CONSTRUCTION_K7_H1_E4_V2_IN_SUPERVISOR_COMPLETION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-e4-v2-in-supervisor-completion:v1"
)
CONSTRUCTION_K7_H1_ROUTE_WIDE_ACTUAL_PEAK_OBSERVATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-route-wide-actual-peak-observation:v1"
)
CONSTRUCTION_K7_H1_ROUTE_WIDE_RUNTIME_LEASE_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-route-wide-runtime-lease-closure:v1"
)
CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-actual-observed-e3-v2-protocol-failure-closure:v1"
)


K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V15: Mapping[str, str] = MappingProxyType(
    {
        "construction_k7_h1_actual_observed_e3_v2_profile_v1": (
            CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_PROFILE_V1_DOMAIN
        ),
        "construction_k7_h1_actual_observed_e3_v2_stage_plan_v1": (
            CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_STAGE_PLAN_V1_DOMAIN
        ),
        "construction_k7_h1_actual_observed_e3_v2_execution_source_closure_v1": (
            CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_h1_route_wide_runtime_lease_successor_v1": (
            CONSTRUCTION_K7_H1_ROUTE_WIDE_RUNTIME_LEASE_SUCCESSOR_V1_DOMAIN
        ),
        "construction_k7_h1_actual_observed_e3_v2_guardian_session_genesis_v1": (
            CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_GUARDIAN_SESSION_GENESIS_V1_DOMAIN
        ),
        "construction_k7_h1_actual_process_birth_intent_v1": (
            CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_INTENT_V1_DOMAIN
        ),
        "construction_k7_h1_actual_process_birth_permit_v1": (
            CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_PERMIT_V1_DOMAIN
        ),
        "construction_k7_h1_shared_pid_cell_binding_v1": (
            CONSTRUCTION_K7_H1_SHARED_PID_CELL_BINDING_V1_DOMAIN
        ),
        "construction_k7_h1_pidfd_escrow_receipt_v2": (
            CONSTRUCTION_K7_H1_PIDFD_ESCROW_RECEIPT_V2_DOMAIN
        ),
        "construction_k7_h1_cgroup_membership_observation_v1": (
            CONSTRUCTION_K7_H1_CGROUP_MEMBERSHIP_OBSERVATION_V1_DOMAIN
        ),
        "construction_k7_h1_actual_process_birth_observation_v1": (
            CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_OBSERVATION_V1_DOMAIN
        ),
        "construction_k7_h1_guardian_birth_ack_v1": (
            CONSTRUCTION_K7_H1_GUARDIAN_BIRTH_ACK_V1_DOMAIN
        ),
        "construction_k7_h1_actual_process_creator_release_v1": (
            CONSTRUCTION_K7_H1_ACTUAL_PROCESS_CREATOR_RELEASE_V1_DOMAIN
        ),
        "construction_k7_h1_actual_process_death_observation_v1": (
            CONSTRUCTION_K7_H1_ACTUAL_PROCESS_DEATH_OBSERVATION_V1_DOMAIN
        ),
        "construction_k7_h1_actual_process_creator_reap_attestation_v1": (
            CONSTRUCTION_K7_H1_ACTUAL_PROCESS_CREATOR_REAP_ATTESTATION_V1_DOMAIN
        ),
        "construction_k7_h1_actual_observed_e3_v2_native_cleanup_barrier_v1": (
            CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_NATIVE_CLEANUP_BARRIER_V1_DOMAIN
        ),
        "construction_k7_h1_actual_observed_e3_v2_completion_v1": (
            CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_COMPLETION_V1_DOMAIN
        ),
        "construction_k7_h1_e4_v2_live_supervisor_context_v1": (
            CONSTRUCTION_K7_H1_E4_V2_LIVE_SUPERVISOR_CONTEXT_V1_DOMAIN
        ),
        "construction_k7_h1_e4_v2_in_supervisor_completion_v1": (
            CONSTRUCTION_K7_H1_E4_V2_IN_SUPERVISOR_COMPLETION_V1_DOMAIN
        ),
        "construction_k7_h1_route_wide_actual_peak_observation_v1": (
            CONSTRUCTION_K7_H1_ROUTE_WIDE_ACTUAL_PEAK_OBSERVATION_V1_DOMAIN
        ),
        "construction_k7_h1_route_wide_runtime_lease_closure_v1": (
            CONSTRUCTION_K7_H1_ROUTE_WIDE_RUNTIME_LEASE_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_h1_actual_observed_e3_v2_protocol_failure_closure_v1": (
            CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN
        ),
    }
)
K7_H1_DOMAIN_TAG_EXTENSION_V15 = frozenset(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V15.values()
)
if len(K7_H1_DOMAIN_TAG_EXTENSION_V15) != len(
    K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V15
):  # pragma: no cover - import-time invariant
    raise RuntimeError("K7 H1 domain extension V15 contains a duplicate domain")


def extension_content_id_v15(domain_tag: str, payload: Any) -> str:
    """Hash only one pre-registered V15 construction payload."""

    if (
        type(domain_tag) is not str
        or domain_tag not in K7_H1_DOMAIN_TAG_EXTENSION_V15
        or "\x00" in domain_tag
    ):
        raise ValueError("domain tag is absent from the K7 H1 V15 registry")
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
            "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V15",
            "K7_H1_DOMAIN_TAG_EXTENSION_V15",
            "extension_content_id_v15",
        )
    )
)
