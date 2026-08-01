"""Fresh-exec reconstruction of the complete V0-103 K7 request authority.

The V0-103 byte verifier intentionally required the parent's live request
object.  That is useful against in-process transplantation but unusable in a
sealed fresh child.  This module reconstructs the complete issuer-protected
profile chain from canonical documents and the exact sealed source archive,
then replays the request without accepting any live parent authority object.

This remains a pre-business construction boundary.  The returned authorities
are process-local and unpickleable; actual isolated-runtime flags are checked
by the sealed bootstrap, not inferred by this profile replay.  No child,
accounting, terminal, certificate, or official authority is issued here.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import v075_k7_os_supervisor_admission_v1 as admission
from acfqp import v075_k7_parent_owned_successor_ipc_v1 as successor
from acfqp import v075_k7_root_cap_accounted_sealed_ipc_v1 as accounted
from acfqp import v075_k7_root_cap_execution_identity_overlay_v1 as execution
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as boundary
from acfqp import v075_signer_owning_complete_observer_lifecycle_ipc_v1 as lifecycle
from acfqp import v075_signer_owning_sealed_observer_ipc_v1 as transport
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_SUCCESSOR_PORTABLE_PROFILE_CLOSURE_V1_DOMAIN,
    V075_K7_SUCCESSOR_PORTABLE_REQUEST_REPLAY_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.97.0"
PROFILE_KEY = "v075_k7_successor_portable_replay_v1"
MAX_PROFILE_DOCUMENT_BYTES = 16 * 1024 * 1024
MAX_REQUEST_BYTES = transport.MAX_REQUEST_BYTES

LOCAL_DOMAIN_TAGS = frozenset(
    {
        V075_K7_SUCCESSOR_PORTABLE_PROFILE_CLOSURE_V1_DOMAIN,
        V075_K7_SUCCESSOR_PORTABLE_REQUEST_REPLAY_V1_DOMAIN,
    }
)
if not LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("K7 portable replay domains are unregistered")

_PROFILE_CLOSURE_ISSUER = object()
_REQUEST_REPLAY_ISSUER = object()


class V075K7SuccessorPortableReplayV1Error(ValueError):
    """The profile closure, source archive, or request failed exact replay."""


def _fail(message: str) -> NoReturn:
    raise V075K7SuccessorPortableReplayV1Error(message)


def _canonical_document(raw: bytes, label: str, *, cap: int) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > cap:
        _fail(f"{label} bytes are empty, mistyped, or over cap")
    try:
        value = loads_canonical_json(raw)
    except Exception as error:
        raise V075K7SuccessorPortableReplayV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON document")
    return value


def _same_document(actual: Mapping[str, Any], expected: Mapping[str, Any], label: str) -> None:
    if canonical_json_bytes(actual) != canonical_json_bytes(expected):
        _fail(f"{label} differs from fresh issuer reconstruction")


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        _fail("portable replay used an undeclared domain")
    return content_id(domain, dict(payload))


def _locks() -> dict[str, bool]:
    return {
        "actual_isolated_runtime_verified": False,
        "child_launch_authorized": False,
        "business_execution_authorized": False,
        "counter_record_authorized": False,
        "work_vector_authorized": False,
        "comparison_vector_authorized": False,
        "actual_projection_proof_authorized": False,
        "attempt_terminal_authorized": False,
        "official_execution_allowed": False,
    }


def _reconstruct_accounted_profile(
    *,
    transport_profile: transport.V075SignerOwningSealedObserverServiceProfileV1,
    lifecycle_profile: lifecycle.V075CompleteObserverLifecycleProfileV1,
) -> accounted.V075K7RootCapAccountedSealedIPCProfileV1:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    projection = registry_v6.official_actual_projection_profile_v6(
        registry, comparison
    )
    boundary_profile = boundary.official_k7_root_cap_operation_boundary_manifest_v3()
    execution_profile = execution.official_v075_k7_root_cap_execution_identity_profile_v1()
    snapshot = accounted._V075K7AccountedAuthoritySnapshotV1(  # noqa: SLF001
        accounted._AUTHORITY_SNAPSHOT_ISSUER,  # noqa: SLF001
        registry,
        stage,
        comparison,
        projection,
        boundary_profile,
        execution_profile,
    )
    return accounted.V075K7RootCapAccountedSealedIPCProfileV1(
        accounted._PROFILE_ISSUER,  # noqa: SLF001
        transport_profile,
        lifecycle_profile,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        projection.actual_projection_profile_id,
        boundary_profile.manifest_id,
        execution_profile.profile_id,
        snapshot,
    )


@dataclass(frozen=True, slots=True)
class V075K7SuccessorPortableProfileClosureV1:
    """Process-local fresh reconstruction of all profiles used by V0-103."""

    _issuer: InitVar[object]
    successor_profile: successor.V075K7ParentOwnedSuccessorIPCProfileV1 = field(
        repr=False, compare=False
    )
    accounted_profile: accounted.V075K7RootCapAccountedSealedIPCProfileV1 = field(
        repr=False, compare=False
    )
    transport_profile: transport.V075SignerOwningSealedObserverServiceProfileV1 = field(
        repr=False, compare=False
    )
    lifecycle_profile: lifecycle.V075CompleteObserverLifecycleProfileV1 = field(
        repr=False, compare=False
    )
    source_archive_sha256: str
    source_archive_byte_count: int
    transport_profile_document_sha256: str
    lifecycle_profile_document_sha256: str
    successor_profile_document_sha256: str
    _validated_refs: tuple[object, ...] = field(init=False, repr=False)
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PROFILE_CLOSURE_ISSUER
            or type(self.successor_profile)
            is not successor.V075K7ParentOwnedSuccessorIPCProfileV1
            or type(self.accounted_profile)
            is not accounted.V075K7RootCapAccountedSealedIPCProfileV1
            or type(self.transport_profile)
            is not transport.V075SignerOwningSealedObserverServiceProfileV1
            or type(self.lifecycle_profile)
            is not lifecycle.V075CompleteObserverLifecycleProfileV1
            or self.successor_profile.accounted_profile is not self.accounted_profile
            or self.accounted_profile.transport_profile is not self.transport_profile
            or self.accounted_profile.private_replay_profile is not self.lifecycle_profile
        ):
            _fail("portable profile closure is caller-minted or crossed")
        self.successor_profile._assert_current()  # noqa: SLF001
        self.accounted_profile._assert_current()  # noqa: SLF001
        self.transport_profile._assert_current()  # noqa: SLF001
        self.lifecycle_profile._assert_current()  # noqa: SLF001
        if (
            self.source_archive_sha256 != self.transport_profile.source_archive_sha256
            or self.source_archive_byte_count
            != self.transport_profile.source_archive_byte_count
        ):
            _fail("portable profile closure source facts changed")
        refs = (
            self.successor_profile,
            self.accounted_profile,
            self.transport_profile,
            self.lifecycle_profile,
        )
        object.__setattr__(self, "_validated_refs", refs)
        object.__setattr__(
            self,
            "_closure_id",
            _hash(
                V075_K7_SUCCESSOR_PORTABLE_PROFILE_CLOSURE_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_successor_portable_profile_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "successor_profile_id": self.successor_profile.profile_id,
            "accounted_profile_id": self.accounted_profile.profile_id,
            "sealed_transport_profile_id": self.transport_profile.profile_id,
            "complete_lifecycle_profile_id": self.lifecycle_profile.profile_id,
            "source_snapshot_id": self.transport_profile.source_snapshot_id,
            "runtime_id": self.transport_profile.runtime_id,
            "source_archive_sha256": self.source_archive_sha256,
            "source_archive_byte_count": self.source_archive_byte_count,
            "transport_profile_document_sha256": (
                self.transport_profile_document_sha256
            ),
            "lifecycle_profile_document_sha256": (
                self.lifecycle_profile_document_sha256
            ),
            "successor_profile_document_sha256": (
                self.successor_profile_document_sha256
            ),
            "fresh_profile_authorities_reconstructed": True,
            "live_parent_profile_object_accepted": False,
            **_locks(),
        }

    def _assert_current(self) -> None:
        refs = (
            self.successor_profile,
            self.accounted_profile,
            self.transport_profile,
            self.lifecycle_profile,
        )
        if any(current is not frozen for current, frozen in zip(refs, self._validated_refs)):
            _fail("portable profile closure authority was replaced")
        self.successor_profile._assert_current()  # noqa: SLF001
        if _hash(
            V075_K7_SUCCESSOR_PORTABLE_PROFILE_CLOSURE_V1_DOMAIN,
            self._payload(),
        ) != self._closure_id:
            _fail("portable profile closure changed after issuance")

    @property
    def closure_id(self) -> str:
        self._assert_current()
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "portable_profile_closure_id": self.closure_id}

    def __reduce__(self):
        raise TypeError("portable profile closure is process-local")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("portable profile closure is process-local")


def reconstruct_v075_k7_successor_portable_profile_closure_v1(
    *,
    source_archive_raw: bytes,
    transport_profile_raw: bytes,
    lifecycle_profile_raw: bytes,
    successor_profile_raw: bytes,
) -> V075K7SuccessorPortableProfileClosureV1:
    """Reconstruct the complete V0-103 profile chain without live parent refs."""

    transport_document = _canonical_document(
        transport_profile_raw,
        "sealed transport profile",
        cap=MAX_PROFILE_DOCUMENT_BYTES,
    )
    lifecycle_document = _canonical_document(
        lifecycle_profile_raw,
        "complete lifecycle profile",
        cap=MAX_PROFILE_DOCUMENT_BYTES,
    )
    successor_document = _canonical_document(
        successor_profile_raw,
        "successor profile",
        cap=MAX_PROFILE_DOCUMENT_BYTES,
    )
    if (
        type(source_archive_raw) is not bytes
        or not source_archive_raw
        or len(source_archive_raw) > transport.MAX_SOURCE_ARCHIVE_BYTES
    ):
        _fail("sealed source archive is empty, mistyped, or over cap")
    try:
        entries = transport._archive_entries(source_archive_raw)  # noqa: SLF001
        runtime_document = dict(transport_document["runtime"])
        runtime_document.pop("runtime_id")
        rebuilt_transport = transport.V075SignerOwningSealedObserverServiceProfileV1(
            hashlib.sha256(source_archive_raw).hexdigest(),
            len(source_archive_raw),
            entries,
            runtime_document,
            transport_document["timeout_milliseconds"],
            source_archive_raw,
        )
        _same_document(
            transport_document,
            rebuilt_transport.to_document(),
            "sealed transport profile",
        )
        rebuilt_lifecycle = lifecycle.V075CompleteObserverLifecycleProfileV1(
            rebuilt_transport
        )
        _same_document(
            lifecycle_document,
            rebuilt_lifecycle.to_document(),
            "complete lifecycle profile",
        )
        rebuilt_accounted = _reconstruct_accounted_profile(
            transport_profile=rebuilt_transport,
            lifecycle_profile=rebuilt_lifecycle,
        )
        nested_accounted = successor_document["accounted_sealed_profile"]
        _same_document(
            nested_accounted,
            rebuilt_accounted.to_document(),
            "accounted profile nested in successor",
        )
        rebuilt_successor = successor.freeze_v075_k7_parent_owned_successor_ipc_profile_v1(
            accounted_profile=rebuilt_accounted,
            admission_profile=(
                admission.official_v075_k7_os_supervisor_admission_profile_v1()
            ),
        )
        _same_document(
            successor_document,
            rebuilt_successor.to_document(),
            "successor profile",
        )
    except V075K7SuccessorPortableReplayV1Error:
        raise
    except Exception as error:
        raise V075K7SuccessorPortableReplayV1Error(
            "fresh profile authority reconstruction failed"
        ) from error
    return V075K7SuccessorPortableProfileClosureV1(
        _PROFILE_CLOSURE_ISSUER,
        rebuilt_successor,
        rebuilt_accounted,
        rebuilt_transport,
        rebuilt_lifecycle,
        rebuilt_transport.source_archive_sha256,
        rebuilt_transport.source_archive_byte_count,
        hashlib.sha256(transport_profile_raw).hexdigest(),
        hashlib.sha256(lifecycle_profile_raw).hexdigest(),
        hashlib.sha256(successor_profile_raw).hexdigest(),
    )


@dataclass(frozen=True, slots=True)
class V075K7SuccessorPortableRequestReplayV1:
    """Fresh child-owned replay result retaining its exact reconstructed request."""

    _issuer: InitVar[object]
    profile_closure: V075K7SuccessorPortableProfileClosureV1 = field(
        repr=False, compare=False
    )
    request: successor.V075K7ParentOwnedSuccessorRequestV1 = field(
        repr=False, compare=False
    )
    request_document_sha256: str
    _replay_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _REQUEST_REPLAY_ISSUER
            or type(self.profile_closure)
            is not V075K7SuccessorPortableProfileClosureV1
            or type(self.request)
            is not successor.V075K7ParentOwnedSuccessorRequestV1
            or self.request.profile is not self.profile_closure.successor_profile
            or hashlib.sha256(self.request.canonical_bytes).hexdigest()
            != self.request_document_sha256
        ):
            _fail("portable request replay is caller-minted or crossed")
        self.profile_closure._assert_current()  # noqa: SLF001
        self.request._assert_current()  # noqa: SLF001
        object.__setattr__(
            self,
            "_replay_id",
            _hash(
                V075_K7_SUCCESSOR_PORTABLE_REQUEST_REPLAY_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_successor_portable_request_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_profile_closure_id": self.profile_closure.closure_id,
            "successor_profile_id": self.request.profile.profile_id,
            "request_id": self.request.request_id,
            "request_document_sha256": self.request_document_sha256,
            "route_identity_id": self.request.route_identity.route_identity_id,
            "scientific_occurrence_id": self.request.scientific_occurrence_id,
            "schedule_id": self.request.schedule_id,
            "phase3e_logical_occurrence_id": (
                self.request.occurrence_mapping.phase3e_logical_occurrence_id
            ),
            "signer_registry_id": self.request.signer_registry.registry_id,
            "fresh_request_authority_reconstructed": True,
            "live_parent_request_object_accepted": False,
            **_locks(),
        }

    @property
    def replay_id(self) -> str:
        self.profile_closure._assert_current()  # noqa: SLF001
        self.request._assert_current()  # noqa: SLF001
        if _hash(
            V075_K7_SUCCESSOR_PORTABLE_REQUEST_REPLAY_V1_DOMAIN,
            self._payload(),
        ) != self._replay_id:
            _fail("portable request replay changed after issuance")
        return self._replay_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "portable_request_replay_id": self.replay_id}

    def __reduce__(self):
        raise TypeError("portable request replay is process-local")

    def __reduce_ex__(self, _protocol: int):
        raise TypeError("portable request replay is process-local")


def replay_v075_k7_successor_request_bytes_portable_v1(
    *,
    raw: bytes,
    profile_closure: V075K7SuccessorPortableProfileClosureV1,
) -> V075K7SuccessorPortableRequestReplayV1:
    """Reconstruct one exact V0-103 request without a parent request object."""

    if type(profile_closure) is not V075K7SuccessorPortableProfileClosureV1:
        _fail("portable request replay requires one exact profile closure")
    profile_closure._assert_current()  # noqa: SLF001
    document = _canonical_document(raw, "successor request", cap=MAX_REQUEST_BYTES)
    try:
        route = accounted.V075K7RootCapAccountedSealedRouteIdentityV1.from_document(
            document["route_identity"],
            profile=profile_closure.accounted_profile,
        )
        signer_registry = transport._registry_from_document(  # noqa: SLF001
            document["signer_registry"]
        )
        rebuilt = successor.freeze_v075_k7_parent_owned_successor_request_v1(
            profile=profile_closure.successor_profile,
            route_identity=route,
            signer_registry=signer_registry,
            opaque_environment_commitment_id=(
                document["opaque_environment_commitment_id"]
            ),
            sealed_secret_commitment_id=document["sealed_secret_commitment_id"],
            session_external_id=document["session_external_id"],
            request_nonce=document["request_nonce"],
            scientific_occurrence_id=document["scientific_occurrence_id"],
            schedule_id=document["schedule_id"],
        )
        _same_document(document, rebuilt.to_document(), "successor request")
    except V075K7SuccessorPortableReplayV1Error:
        raise
    except Exception as error:
        raise V075K7SuccessorPortableReplayV1Error(
            "fresh successor request reconstruction failed"
        ) from error
    return V075K7SuccessorPortableRequestReplayV1(
        _REQUEST_REPLAY_ISSUER,
        profile_closure,
        rebuilt,
        hashlib.sha256(raw).hexdigest(),
    )


__all__ = [
    "LOCAL_DOMAIN_TAGS",
    "MAX_PROFILE_DOCUMENT_BYTES",
    "MAX_REQUEST_BYTES",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V075K7SuccessorPortableProfileClosureV1",
    "V075K7SuccessorPortableReplayV1Error",
    "V075K7SuccessorPortableRequestReplayV1",
    "reconstruct_v075_k7_successor_portable_profile_closure_v1",
    "replay_v075_k7_successor_request_bytes_portable_v1",
]
