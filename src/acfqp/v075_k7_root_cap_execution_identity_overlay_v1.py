"""V0-075 execution identity for the construction-only K7 root-cap fixture.

The operation-boundary V3 manifest was frozen against a historical V0-072
context key.  Its operation boundaries may be reused as accounting semantics,
but that historical identity is not the identity of the V0-075 occurrence.
This overlay binds the reusable boundary manifest to the exact public V0-075
K7 construction context and fails closed before accounting or cache activity.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from acfqp.phase3e_ids import (
    V075_K7_ROOT_CAP_EXECUTION_IDENTITY_PROFILE_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as boundary_v3


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v075_k7_root_cap_execution_identity_overlay_v1"
EXECUTION_PROFILE_DOMAIN = (
    V075_K7_ROOT_CAP_EXECUTION_IDENTITY_PROFILE_V1_DOMAIN
)

REGISTERED_ARM = "NO_PRIOR"
REGISTERED_ROUTE = "ADAPTIVE_QUOTIENT"
REGISTERED_TERMINAL_STATUS = "CHILD_ACTION_ROW_CAP_EXCEEDED"
REGISTERED_CONTEXT_KEY = "heldout_graph_k7_production_replication_v075_1"
REGISTERED_CONTEXT_ID = (
    "e8f5b54c9b31814d3a971f7223d3eeadc5dd8063b96faa0c1780f306869c255a"
)
REGISTERED_TOPOLOGY_ID = (
    "c4ad4934340b4fe0854a7f85d778a6ebec9a52337da6577426d5585a155a7b21"
)
BOUNDARY_IDENTITY_DISPOSITION = (
    "BOUNDARY_SEMANTICS_REUSED_ONLY_HISTORICAL_EXECUTION_IDENTITY_FORBIDDEN"
)

_PROFILE_ISSUER = object()


class V075K7RootCapExecutionIdentityV1Error(ValueError):
    """The construction fixture was crossed with another execution identity."""


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075K7RootCapExecutionIdentityV1Error(
            f"{field_name} must be one exact content ID"
        ) from error


def _exact_k7_context() -> public.V075PublicReplicateContextV1:
    family = public.freeze_v075_public_family_generation_v1()
    matches = tuple(
        context
        for context in family.replicate_contexts
        if context.context_key == REGISTERED_CONTEXT_KEY
    )
    if (
        len(matches) != 1
        or matches[0].topology != public.K7_TOPOLOGY
        or matches[0].context_id != REGISTERED_CONTEXT_ID
        or matches[0].topology.topology_id != REGISTERED_TOPOLOGY_ID
    ):
        raise V075K7RootCapExecutionIdentityV1Error(
            "exact V0-075 public K7 construction context changed"
        )
    return matches[0]


@dataclass(frozen=True, slots=True)
class V075K7RootCapExecutionIdentityProfileV1:
    """Content-addressed identity overlay for one construction fixture."""

    _issuer: InitVar[object]
    boundary_manifest_id: str
    boundary_manifest_context_key: str
    execution_context_key: str
    execution_context_id: str
    execution_topology_id: str
    arm: str
    route: str
    terminal_status: str

    def __post_init__(self, _issuer: object) -> None:
        manifest = (
            boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
        )
        context = _exact_k7_context()
        _cid(self.boundary_manifest_id, "V3 boundary manifest")
        _cid(self.execution_context_id, "V0-075 execution context")
        _cid(self.execution_topology_id, "V0-075 execution topology")
        if (
            _issuer is not _PROFILE_ISSUER
            or self.boundary_manifest_id != manifest.manifest_id
            or self.boundary_manifest_context_key
            != boundary_v3.REGISTERED_CONTEXT_KEY
            or self.execution_context_key != context.context_key
            or self.execution_context_id != context.context_id
            or self.execution_topology_id != context.topology.topology_id
            or self.arm != REGISTERED_ARM
            or self.route != REGISTERED_ROUTE
            or self.terminal_status != REGISTERED_TERMINAL_STATUS
            or self.execution_context_key
            == self.boundary_manifest_context_key
        ):
            raise V075K7RootCapExecutionIdentityV1Error(
                "V0-075 K7 execution identity overlay changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_k7_root_cap_execution_identity_profile.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "boundary_manifest_id": self.boundary_manifest_id,
            "boundary_manifest_context_key": (
                self.boundary_manifest_context_key
            ),
            "boundary_identity_disposition": BOUNDARY_IDENTITY_DISPOSITION,
            "boundary_semantics_reused": True,
            "boundary_execution_identity_reused": False,
            "execution_context_key": self.execution_context_key,
            "execution_context_id": self.execution_context_id,
            "execution_topology_id": self.execution_topology_id,
            "arm": self.arm,
            "route": self.route,
            "terminal_status": self.terminal_status,
            "construction_fixture_only": True,
            "scientific_endpoint_credit_allowed": False,
            "target_observation_reuse_allowed": False,
            "prior_target_observation_ids": [],
            "prior_target_observation_count": 0,
            "official_execution_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def profile_id(self) -> str:
        return content_id(EXECUTION_PROFILE_DOMAIN, self._payload())

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "execution_profile_id": self.profile_id}


@lru_cache(maxsize=1)
def official_v075_k7_root_cap_execution_identity_profile_v1(
) -> V075K7RootCapExecutionIdentityProfileV1:
    manifest = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    context = _exact_k7_context()
    return V075K7RootCapExecutionIdentityProfileV1(
        _PROFILE_ISSUER,
        manifest.manifest_id,
        boundary_v3.REGISTERED_CONTEXT_KEY,
        context.context_key,
        context.context_id,
        context.topology.topology_id,
        REGISTERED_ARM,
        REGISTERED_ROUTE,
        REGISTERED_TERMINAL_STATUS,
    )


def validate_v075_k7_root_cap_execution_identity_v1(
    *,
    profile: V075K7RootCapExecutionIdentityProfileV1,
    repository_root: str | Path,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    schedule_verification: acquisition.V075InitialAcquisitionVerificationV2,
) -> V075K7RootCapExecutionIdentityProfileV1:
    """Reject a crossed context/arm/route before owned execution activates."""

    exact_profile = official_v075_k7_root_cap_execution_identity_profile_v1()
    if (
        type(profile) is not V075K7RootCapExecutionIdentityProfileV1
        or profile != exact_profile
        or profile.profile_id != exact_profile.profile_id
        or not isinstance(repository_root, (str, Path))
        or type(namespace) is not namespace_v2.V075PublicTargetTapeNamespaceV2
        or type(schedule) is not acquisition.V075InitialAcquisitionScheduleV2
        or type(schedule_verification)
        is not acquisition.V075InitialAcquisitionVerificationV2
    ):
        raise V075K7RootCapExecutionIdentityV1Error(
            "execution identity inputs are untyped or caller-minted"
        )

    context = _exact_k7_context()
    occurrence = schedule.occurrence
    try:
        registered_contexts = tuple(namespace.family.replicate_contexts)
        matched = tuple(
            item
            for item in registered_contexts
            if item.context_id == occurrence.context_id
        )
        registration = schedule.profile.registration_for(occurrence.arm)
        slot = schedule.profile.occurrence_slot_for(
            context_id=occurrence.context_id,
            arm=occurrence.arm,
        )
        occurrence_document = occurrence.to_document()
        schedule_document = schedule.to_document()
        verification_document = schedule_verification.to_document()
    except Exception as error:
        raise V075K7RootCapExecutionIdentityV1Error(
            "execution schedule identity could not be resolved"
        ) from error

    if (
        namespace.family
        != public.freeze_v075_public_family_generation_v1()
        or len(matched) != 1
        or matched[0] != context
        or matched[0].context_key != profile.execution_context_key
        or matched[0].context_id != profile.execution_context_id
        or matched[0].topology.topology_id
        != profile.execution_topology_id
        or occurrence.context_id != profile.execution_context_id
        or occurrence.arm is not worker.V075WorkerArmV1.NO_PRIOR
        or occurrence.arm.value != profile.arm
        or occurrence.occurrence_ordinal
        != acquisition.ARM_ORDER.index(worker.V075WorkerArmV1.NO_PRIOR)
        or occurrence.target_tape_namespace_id
        != namespace.target_tape_namespace_id
        or schedule.profile.namespace.target_tape_namespace_id
        != namespace.target_tape_namespace_id
        or registration.route
        is not acquisition.V075AcquisitionRouteV2.ADAPTIVE_QUOTIENT
        or registration.route.value != profile.route
        or schedule_document.get("context_id") != profile.execution_context_id
        or schedule_document.get("arm") != profile.arm
        or schedule_document.get("route") != profile.route
        or schedule_verification.schedule.schedule_id != schedule.schedule_id
        or schedule_verification.schedule.canonical_bytes
        != schedule.canonical_bytes
        or schedule_verification.expected_slot != slot
        or verification_document.get("schedule_id") != schedule.schedule_id
        or verification_document.get("arm") != profile.arm
        or occurrence_document.get("target_accessed") is not False
        or occurrence_document.get("batch_count_at_freeze") != 0
        or occurrence_document.get("observer_calls") != 0
        or occurrence_document.get("kernel_calls") != 0
        or schedule_document.get("target_accessed") is not False
        or verification_document.get("target_accessed") is not False
    ):
        raise V075K7RootCapExecutionIdentityV1Error(
            "schedule, occurrence, arm, or route is outside the exact V0-075 "
            "K7 construction execution profile"
        )
    return profile


__all__ = [
    "BOUNDARY_IDENTITY_DISPOSITION",
    "EXECUTION_PROFILE_DOMAIN",
    "PROFILE_KEY",
    "REGISTERED_ARM",
    "REGISTERED_CONTEXT_ID",
    "REGISTERED_CONTEXT_KEY",
    "REGISTERED_ROUTE",
    "REGISTERED_TERMINAL_STATUS",
    "REGISTERED_TOPOLOGY_ID",
    "SCHEMA_VERSION",
    "V075K7RootCapExecutionIdentityProfileV1",
    "V075K7RootCapExecutionIdentityV1Error",
    "official_v075_k7_root_cap_execution_identity_profile_v1",
    "validate_v075_k7_root_cap_execution_identity_v1",
]
