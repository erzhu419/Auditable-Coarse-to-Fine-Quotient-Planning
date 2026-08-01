"""Production-bound K7 authority for atomic shared-resource raw facts.

This successor does not upgrade the older structural receipt schemas.  It
joins one authentic V0-108 parent result to the exact K7 route identity, V6
registry, sealed parent/runtime source entries, and runtime-issued lifecycle
evidence.  V1 verifies ``memory.working_bytes_peak`` for the successful atomic
child-runtime window and ``process.launches`` for the native runtime launch
site.  Neither observation is an attempt-scope resolution: the measurement
window does not include all parent bootstrap, prelaunch, replay, publication,
and close work.  The other seven paths remain explicitly ``NOT_CONNECTED``.

No object in this module is a CounterRecord, WorkVector, ComparisonVector,
projection proof, terminal, certificate, or official-execution authority.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_receipts_v1 as shared_v1
from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime_v1
from acfqp import v075_k7_parent_atomic_executor_v1 as parent_v1
from acfqp import v075_k7_parent_owned_successor_ipc_v1 as successor_v1
from acfqp import v075_k7_root_cap_shared_resource_identity_v1 as identity_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_ATOMIC_SHARED_RESOURCE_REGISTRY_V1_DOMAIN,
    V075_K7_ATOMIC_SHARED_RESOURCE_RESOLUTION_V1_DOMAIN,
    V075_K7_ATOMIC_SHARED_RESOURCE_VERIFICATION_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.1"
PROFILE_KEY = "v075_k7_atomic_shared_resource_authority_v1"
RUNTIME_SOURCE_PATH = "acfqp/v075_k7_atomic_pidfd_runtime_v1.py"

LOCAL_DOMAINS = frozenset(
    {
        V075_K7_ATOMIC_SHARED_RESOURCE_REGISTRY_V1_DOMAIN,
        V075_K7_ATOMIC_SHARED_RESOURCE_RESOLUTION_V1_DOMAIN,
        V075_K7_ATOMIC_SHARED_RESOURCE_VERIFICATION_V1_DOMAIN,
    }
)
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("atomic shared-resource authority domains are unregistered")

MEMORY_PATH = "memory.working_bytes_peak"
PROCESS_PATH = "process.launches"
EXACT_CONNECTED_PATHS: tuple[str, ...] = ()
CHILD_RUNTIME_WINDOW_PATHS = (MEMORY_PATH,)
RUNTIME_LOCAL_PATHS = (PROCESS_PATH,)
NOT_CONNECTED_PATHS = tuple(
    path
    for path in shared_v1.SHARED_RESOURCE_PATHS
    if path not in {
        *EXACT_CONNECTED_PATHS,
        *CHILD_RUNTIME_WINDOW_PATHS,
        *RUNTIME_LOCAL_PATHS,
    }
)

_REGISTRY_ISSUER = object()
_RESOLUTION_ISSUER = object()
_VERIFICATION_ISSUER = object()


class V075K7AtomicSharedResourceAuthorityV1Error(ValueError):
    """The production registry, runtime evidence, or route join is invalid."""


class ProductionConnectionStatusV1(str, Enum):
    VERIFIED_CHILD_RUNTIME_WINDOW_SCOPE_INCOMPLETE = (
        "VERIFIED_CHILD_RUNTIME_WINDOW_SCOPE_INCOMPLETE"
    )
    VERIFIED_RUNTIME_LOCAL_SCOPE_INCOMPLETE = (
        "VERIFIED_RUNTIME_LOCAL_SCOPE_INCOMPLETE"
    )
    NOT_CONNECTED = "NOT_CONNECTED"


def _fail(message: str) -> NoReturn:
    raise V075K7AtomicSharedResourceAuthorityV1Error(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAINS:
        _fail("atomic shared-resource authority used an undeclared domain")
    return content_id(domain, dict(payload))


def _frozen_document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V075K7AtomicSharedResourceAuthorityV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} must be one canonical JSON object")
    return value


def _validated_request_id(
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
) -> str:
    try:
        current = request.request_id
    except Exception as error:
        raise V075K7AtomicSharedResourceAuthorityV1Error(
            "successor request failed complete identity replay"
        ) from error
    if current != request._request_id:  # noqa: SLF001
        _fail("successor request identity changed before authority freeze")
    return current


def _validated_spec_id(
    spec: parent_v1.V075K7AtomicParentExecutionSpecV1,
) -> str:
    try:
        current = spec.spec_id
    except Exception as error:
        raise V075K7AtomicSharedResourceAuthorityV1Error(
            "atomic execution spec failed canonical snapshot replay"
        ) from error
    if current != spec._spec_id:  # noqa: SLF001
        _fail("atomic execution spec identity changed before authority freeze")
    return current


def _locks() -> dict[str, bool]:
    return {
        "all_nine_shared_resource_paths_verified": False,
        "counter_records_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "actual_projection_proof_issued": False,
        "formal_vector_authorized": False,
        "attempt_terminal_issued": False,
        "plan_certificate_issued": False,
        "infeasibility_certificate_issued": False,
        "official_execution_allowed": False,
    }


def _source_entry(request: Any, path: str) -> tuple[str, int]:
    transport = request.profile.accounted_profile.transport_profile
    matches = tuple(
        (digest, size)
        for source_path, digest, size in transport.source_entries
        if source_path == path
    )
    if len(matches) != 1:
        _fail(f"sealed source snapshot lacks exact entry {path}")
    digest, size = matches[0]
    if (
        type(digest) is not str
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        or type(size) is not int
        or size <= 0
    ):
        _fail("sealed source entry is malformed")
    return digest, size


def _live_source_matches(path: Path, digest: str, size: int) -> bool:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise V075K7AtomicSharedResourceAuthorityV1Error(
            "registered live source cannot be read"
        ) from error
    return len(raw) == size and hashlib.sha256(raw).hexdigest() == digest


def _connection_status(path: str) -> ProductionConnectionStatusV1:
    if path == MEMORY_PATH:
        return (
            ProductionConnectionStatusV1
            .VERIFIED_CHILD_RUNTIME_WINDOW_SCOPE_INCOMPLETE
        )
    if path == PROCESS_PATH:
        return (
            ProductionConnectionStatusV1
            .VERIFIED_RUNTIME_LOCAL_SCOPE_INCOMPLETE
        )
    if path in NOT_CONNECTED_PATHS:
        return ProductionConnectionStatusV1.NOT_CONNECTED
    _fail("unknown shared-resource path")


def _method_key(path: str) -> str:
    if path == MEMORY_PATH:
        return "CGROUP_V2_FINAL_MEMORY_PEAK_AFTER_DESCENDANT_SCAN"
    if path == PROCESS_PATH:
        return "NATIVE_CLONE3_PIDFD_RUNTIME_LOCAL_LAUNCH"
    return "NOT_CONNECTED"


@dataclass(frozen=True, slots=True)
class V075K7ProductionSharedResourceRegistryV1:
    """Exact nine-row connection registry derived from one execution spec."""

    _issuer: InitVar[object]
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1 = field(
        repr=False, compare=False
    )
    spec: parent_v1.V075K7AtomicParentExecutionSpecV1 = field(
        repr=False, compare=False
    )
    identity_derivation: (
        identity_v1.V075K7RootCapSharedResourceIdentityDerivationV1
    ) = field(repr=False, compare=False)
    identity_verification: (
        identity_v1.V075K7RootCapSharedResourceIdentityVerificationV1
    ) = field(repr=False, compare=False)
    runtime_source_sha256: str
    runtime_source_byte_count: int
    _validated_request: successor_v1.V075K7ParentOwnedSuccessorRequestV1 = field(
        init=False, repr=False, compare=False
    )
    _validated_spec: parent_v1.V075K7AtomicParentExecutionSpecV1 = field(
        init=False, repr=False, compare=False
    )
    _validated_derivation: (
        identity_v1.V075K7RootCapSharedResourceIdentityDerivationV1
    ) = field(init=False, repr=False, compare=False)
    _validated_identity_verification: (
        identity_v1.V075K7RootCapSharedResourceIdentityVerificationV1
    ) = field(init=False, repr=False, compare=False)
    _identity_binding: shared_v1.SharedResourceIdentityBindingV1 = field(
        init=False, repr=False, compare=False
    )
    _request_id: str = field(init=False, repr=False)
    _route_identity_id: str = field(init=False, repr=False)
    _spec_id: str = field(init=False, repr=False)
    _identity_binding_id: str = field(init=False, repr=False)
    _identity_derivation_id: str = field(init=False, repr=False)
    _identity_verification_id: str = field(init=False, repr=False)
    _frozen_payload_bytes: bytes = field(init=False, repr=False)
    _registry_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _REGISTRY_ISSUER
            or type(self.request)
            is not successor_v1.V075K7ParentOwnedSuccessorRequestV1
            or type(self.spec)
            is not parent_v1.V075K7AtomicParentExecutionSpecV1
            or type(self.identity_derivation)
            is not identity_v1.V075K7RootCapSharedResourceIdentityDerivationV1
            or type(self.identity_verification)
            is not identity_v1.V075K7RootCapSharedResourceIdentityVerificationV1
        ):
            _fail("production shared-resource registry is caller-minted")
        # Perform the complete upstream checks once at the authority boundary.
        # The issued artifact below is a canonical snapshot; no later payload
        # calculation mixes cached identifiers with mutable live fields.
        request_id = _validated_request_id(self.request)
        _validated_spec_id(self.spec)
        if self.spec._request_id != request_id:  # noqa: SLF001
            _fail("atomic execution spec crossed its successor request")
        self.identity_derivation._assert_current()  # noqa: SLF001
        self.identity_verification._assert_current()  # noqa: SLF001
        binding = self.identity_derivation._identity_binding  # noqa: SLF001
        if (
            self.spec.request is not self.request
            or self.identity_derivation.route_identity
            is not self.request.route_identity
            or self.identity_verification.derivation
            is not self.identity_derivation
            or type(binding) is not shared_v1.SharedResourceIdentityBindingV1
        ):
            _fail("production shared-resource registry dependencies crossed")
        object.__setattr__(self, "_validated_request", self.request)
        object.__setattr__(self, "_validated_spec", self.spec)
        object.__setattr__(
            self, "_validated_derivation", self.identity_derivation
        )
        object.__setattr__(
            self,
            "_validated_identity_verification",
            self.identity_verification,
        )
        object.__setattr__(self, "_identity_binding", binding)
        object.__setattr__(
            self, "_request_id", self.request._request_id  # noqa: SLF001
        )
        object.__setattr__(
            self,
            "_route_identity_id",
            self.identity_derivation._route_identity_id,  # noqa: SLF001
        )
        object.__setattr__(self, "_spec_id", self.spec._spec_id)  # noqa: SLF001
        object.__setattr__(
            self,
            "_identity_binding_id",
            self.identity_derivation._identity_binding_id,  # noqa: SLF001
        )
        object.__setattr__(
            self,
            "_identity_derivation_id",
            self.identity_verification._derivation_id,  # noqa: SLF001
        )
        object.__setattr__(
            self,
            "_identity_verification_id",
            self.identity_verification.verification_id,
        )
        self._assert_dependencies()
        snapshot = self._snapshot_payload()
        object.__setattr__(
            self, "_frozen_payload_bytes", canonical_json_bytes(snapshot)
        )
        object.__setattr__(
            self,
            "_registry_id",
            _hash(
                V075_K7_ATOMIC_SHARED_RESOURCE_REGISTRY_V1_DOMAIN,
                snapshot,
            ),
        )

    def _assert_dependencies(self) -> None:
        if (
            self.request is not self._validated_request
            or self.spec is not self._validated_spec
            or self.identity_derivation is not self._validated_derivation
            or self.identity_verification
            is not self._validated_identity_verification
            or self.spec.request is not self.request
            or self.request._request_id != self._request_id  # noqa: SLF001
            or self.spec._spec_id != self._spec_id  # noqa: SLF001
            or self.identity_derivation._route_identity_id  # noqa: SLF001
            != self._route_identity_id
            or self.identity_derivation._identity_binding_id  # noqa: SLF001
            != self._identity_binding_id
            or self.identity_derivation.route_identity
            is not self.request.route_identity
            or self.identity_verification.derivation
            is not self.identity_derivation
            or self.runtime_source_byte_count <= 0
            or not _live_source_matches(
                Path(runtime_v1.__file__),
                self.runtime_source_sha256,
                self.runtime_source_byte_count,
            )
        ):
            _fail("production shared-resource registry dependencies crossed")
        binding = self._identity_binding
        official = registry_v6.official_counter_registry_v6()
        stage = registry_v6.official_stage_profile_v6(official)
        if (
            binding.counter_registry_id != official.registry_id
            or binding.stage_profile_id != stage.stage_profile_id
            or self.request.route_identity.profile.counter_registry_id
            != official.registry_id
        ):
            _fail("production registry differs from exact V6 route metadata")
        for path in shared_v1.SHARED_RESOURCE_PATHS:
            leaf = official.by_path[path]
            expected_reducer = (
                ReducerEnum.SUM
                if path in shared_v1.SUM_SHARED_RESOURCE_PATHS
                else ReducerEnum.MAX
            )
            if (
                not leaf.required
                or leaf.lane.value != "operational"
                or leaf.reducer is not expected_reducer
            ):
                _fail("production registry path differs from V6")

    def _rows(self) -> list[dict[str, Any]]:
        official = registry_v6.official_counter_registry_v6()
        return [
            {
                "path": path,
                "reducer": official.by_path[path].reducer.value,
                "semantics_id": official.by_path[path].semantics_id,
                "owner": official.by_path[path].owner,
                "connection_status": _connection_status(path).value,
                "measurement_method": _method_key(path),
                "numeric_value_present": False,
            }
            for path in shared_v1.SHARED_RESOURCE_PATHS
        ]

    def _snapshot_payload(self) -> dict[str, Any]:
        binding = self._identity_binding
        spec_document = self.spec.to_document()
        parent_source_entry = spec_document["parent_source_entry"]
        return {
            "schema": "acfqp.v075_k7_production_shared_resource_registry.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "request_id": self._request_id,
            "route_identity_id": self._route_identity_id,
            "atomic_parent_execution_spec_id": self._spec_id,
            "identity_derivation_id": self._identity_derivation_id,
            "identity_verification_id": self._identity_verification_id,
            "shared_resource_identity_binding_id": self._identity_binding_id,
            "counter_registry_id": binding.counter_registry_id,
            "stage_profile_id": binding.stage_profile_id,
            "execution_profile_id": binding.execution_profile_id,
            "parent_source_sha256": parent_source_entry["sha256"],
            "parent_source_byte_count": parent_source_entry["byte_count"],
            "runtime_source_sha256": self.runtime_source_sha256,
            "runtime_source_byte_count": self.runtime_source_byte_count,
            "native_trampoline_sha256": runtime_v1.X86_64_TRAMPOLINE_SHA256,
            "rows": self._rows(),
            "row_count": len(shared_v1.SHARED_RESOURCE_PATHS),
            "exact_connected_paths": list(EXACT_CONNECTED_PATHS),
            "child_runtime_window_scope_incomplete_paths": list(
                CHILD_RUNTIME_WINDOW_PATHS
            ),
            "runtime_local_scope_incomplete_paths": list(RUNTIME_LOCAL_PATHS),
            "not_connected_paths": list(NOT_CONNECTED_PATHS),
            "caller_numeric_totals_accepted": False,
            **_locks(),
        }

    def _payload(self) -> dict[str, Any]:
        return _frozen_document(
            self._frozen_payload_bytes,
            "frozen production shared-resource registry payload",
        )

    @property
    def registry_id(self) -> str:
        if _hash(
            V075_K7_ATOMIC_SHARED_RESOURCE_REGISTRY_V1_DOMAIN,
            self._payload(),
        ) != self._registry_id:
            _fail("production shared-resource registry changed after freeze")
        return self._registry_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "production_shared_resource_registry_id": self.registry_id,
        }


@dataclass(frozen=True, slots=True)
class V075K7VerifiedSharedResourceResolutionV1:
    """One value rederived from the runtime issuer evidence, never supplied."""

    _issuer: InitVar[object]
    registry: V075K7ProductionSharedResourceRegistryV1 = field(
        repr=False, compare=False
    )
    parent_result: parent_v1.V075K7ParentAtomicExecutionResultV1 = field(
        repr=False, compare=False
    )
    path: str
    value: int
    _frozen_payload_bytes: bytes = field(init=False, repr=False)
    _resolution_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _RESOLUTION_ISSUER
            or type(self.registry)
            is not V075K7ProductionSharedResourceRegistryV1
            or type(self.parent_result)
            is not parent_v1.V075K7ParentAtomicExecutionResultV1
            or self.parent_result.request is not self.registry.request
            or self.parent_result.spec is not self.registry.spec
            or self.path not in {MEMORY_PATH, PROCESS_PATH}
        ):
            _fail("verified shared-resource resolution is caller-minted")
        _ = self.registry.registry_id
        if _validated_request_id(self.registry.request) != self.registry._request_id:  # noqa: SLF001
            _fail("successor request changed before resolution issuance")
        if self.parent_result.result_id != self.parent_result._result_id:  # noqa: SLF001
            _fail("atomic parent result changed before resolution issuance")
        evidence = self.parent_result.runtime_result.supervisor_resource_evidence
        expected = (
            evidence.memory_peak_bytes
            if self.path == MEMORY_PATH
            else evidence.process_launches
        )
        if type(self.value) is not int or self.value != expected:
            _fail("verified shared-resource value differs from runtime evidence")
        snapshot = self._snapshot_payload()
        object.__setattr__(
            self, "_frozen_payload_bytes", canonical_json_bytes(snapshot)
        )
        object.__setattr__(
            self,
            "_resolution_id",
            _hash(
                V075_K7_ATOMIC_SHARED_RESOURCE_RESOLUTION_V1_DOMAIN,
                snapshot,
            ),
        )

    def _snapshot_payload(self) -> dict[str, Any]:
        evidence = self.parent_result.runtime_result.supervisor_resource_evidence
        leaf = registry_v6.official_counter_registry_v6().by_path[self.path]
        child_runtime_window = self.path == MEMORY_PATH
        return {
            "schema": "acfqp.v075_k7_verified_shared_resource_resolution.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "production_shared_resource_registry_id": self.registry.registry_id,
            "request_id": self.registry._request_id,  # noqa: SLF001
            "route_identity_id": self.registry._route_identity_id,  # noqa: SLF001
            "atomic_parent_execution_spec_id": self.registry._spec_id,  # noqa: SLF001
            "atomic_parent_execution_result_id": (
                self.parent_result._result_id  # noqa: SLF001
            ),
            "atomic_supervisor_resource_evidence_id": evidence.evidence_id,
            "lease_id": evidence.lease_id,
            "path": self.path,
            "reducer": leaf.reducer.value,
            "semantics_id": leaf.semantics_id,
            "value": self.value,
            "connection_status": _connection_status(self.path).value,
            "measurement_method": _method_key(self.path),
            "source_role": (
                "FINAL_CGROUP_MEMORY_PEAK"
                if child_runtime_window
                else "NATIVE_RUNTIME_PROCESS_LAUNCH"
            ),
            "source_semantics_verified_for_declared_window": True,
            "attempt_scope_complete": False,
            "eligible_as_shared_resource_resolution": False,
            "counter_record_issued": False,
            **_locks(),
        }

    def _payload(self) -> dict[str, Any]:
        return _frozen_document(
            self._frozen_payload_bytes,
            "frozen verified shared-resource resolution payload",
        )

    @property
    def resolution_id(self) -> str:
        if _hash(
            V075_K7_ATOMIC_SHARED_RESOURCE_RESOLUTION_V1_DOMAIN,
            self._payload(),
        ) != self._resolution_id:
            _fail("verified shared-resource resolution changed after issuance")
        return self._resolution_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verified_shared_resource_resolution_id": self.resolution_id,
        }


@dataclass(frozen=True, slots=True)
class V075K7AtomicSharedResourceVerificationV1:
    """Issuer-owned result of the production route/source semantic replay."""

    _issuer: InitVar[object]
    registry: V075K7ProductionSharedResourceRegistryV1 = field(
        repr=False, compare=False
    )
    parent_result: parent_v1.V075K7ParentAtomicExecutionResultV1 = field(
        repr=False, compare=False
    )
    resolutions: tuple[V075K7VerifiedSharedResourceResolutionV1, ...] = field(
        repr=False
    )
    _frozen_payload_bytes: bytes = field(init=False, repr=False)
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _VERIFICATION_ISSUER
            or type(self.registry)
            is not V075K7ProductionSharedResourceRegistryV1
            or type(self.parent_result)
            is not parent_v1.V075K7ParentAtomicExecutionResultV1
            or type(self.resolutions) is not tuple
            or tuple(row.path for row in self.resolutions)
            != (MEMORY_PATH, PROCESS_PATH)
            or any(
                type(row) is not V075K7VerifiedSharedResourceResolutionV1
                or row.registry is not self.registry
                or row.parent_result is not self.parent_result
                for row in self.resolutions
            )
        ):
            _fail("atomic shared-resource verification is caller-minted")
        snapshot = self._snapshot_payload()
        object.__setattr__(
            self, "_frozen_payload_bytes", canonical_json_bytes(snapshot)
        )
        object.__setattr__(
            self,
            "_verification_id",
            _hash(
                V075_K7_ATOMIC_SHARED_RESOURCE_VERIFICATION_V1_DOMAIN,
                snapshot,
            ),
        )

    def _snapshot_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_atomic_shared_resource_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "production_shared_resource_registry_id": self.registry.registry_id,
            "atomic_parent_execution_result_id": (
                self.parent_result._result_id  # noqa: SLF001
            ),
            "atomic_supervisor_resource_evidence_id": (
                self.parent_result.runtime_result
                .supervisor_resource_evidence.evidence_id
            ),
            "resolution_ids": [row.resolution_id for row in self.resolutions],
            "exact_connected_paths": list(EXACT_CONNECTED_PATHS),
            "child_runtime_window_scope_incomplete_paths": list(
                CHILD_RUNTIME_WINDOW_PATHS
            ),
            "runtime_local_scope_incomplete_paths": list(RUNTIME_LOCAL_PATHS),
            "not_connected_paths": list(NOT_CONNECTED_PATHS),
            "successful_atomic_result_semantically_replayed": True,
            "same_process_runtime_issuer_verified": True,
            "standalone_bytes_only_os_replay_completed": False,
            "all_nine_shared_resource_paths_verified": False,
            **_locks(),
        }

    def _payload(self) -> dict[str, Any]:
        return _frozen_document(
            self._frozen_payload_bytes,
            "frozen atomic shared-resource verification payload",
        )

    @property
    def verification_id(self) -> str:
        if _hash(
            V075_K7_ATOMIC_SHARED_RESOURCE_VERIFICATION_V1_DOMAIN,
            self._payload(),
        ) != self._verification_id:
            _fail("atomic shared-resource verification changed after issuance")
        return self._verification_id

    @property
    def child_runtime_resolution(
        self,
    ) -> V075K7VerifiedSharedResourceResolutionV1:
        return self.resolutions[0]

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "atomic_shared_resource_verification_id": self.verification_id,
        }


def freeze_v075_k7_production_shared_resource_registry_v1(
    *,
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
    spec: parent_v1.V075K7AtomicParentExecutionSpecV1,
) -> V075K7ProductionSharedResourceRegistryV1:
    """Derive all identities and source entries; accepts no path/value rows."""

    if (
        type(request) is not successor_v1.V075K7ParentOwnedSuccessorRequestV1
        or type(spec) is not parent_v1.V075K7AtomicParentExecutionSpecV1
        or spec.request is not request
    ):
        _fail("production registry requires exact request/spec authorities")
    request_id = _validated_request_id(request)
    _validated_spec_id(spec)
    if spec._request_id != request_id:  # noqa: SLF001
        _fail("atomic execution spec crossed its successor request")
    derivation = identity_v1.derive_v075_k7_root_cap_shared_resource_identity_v1(
        request.route_identity
    )
    verification = identity_v1.verify_v075_k7_root_cap_shared_resource_identity_v1(
        derivation
    )
    runtime_digest, runtime_size = _source_entry(request, RUNTIME_SOURCE_PATH)
    return V075K7ProductionSharedResourceRegistryV1(
        _REGISTRY_ISSUER,
        request,
        spec,
        derivation,
        verification,
        runtime_digest,
        runtime_size,
    )


def verify_v075_k7_atomic_shared_resource_evidence_v1(
    *,
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
    parent_result: parent_v1.V075K7ParentAtomicExecutionResultV1,
) -> V075K7AtomicSharedResourceVerificationV1:
    """Replay the authentic result and rederive the only two numeric facts."""

    if (
        type(request) is not successor_v1.V075K7ParentOwnedSuccessorRequestV1
        or type(parent_result)
        is not parent_v1.V075K7ParentAtomicExecutionResultV1
        or parent_result.request is not request
    ):
        _fail("atomic shared-resource verification crossed request/result")
    _validated_request_id(request)
    registry = freeze_v075_k7_production_shared_resource_registry_v1(
        request=request,
        spec=parent_result.spec,
    )
    try:
        parent_v1.verify_v075_k7_parent_atomic_two_frame_output_v1(
            raw=parent_result.two_frame_output,
            request=request,
            spec=parent_result.spec,
            runtime_result=parent_result.runtime_result,
        )
    except Exception as error:
        raise V075K7AtomicSharedResourceAuthorityV1Error(
            "atomic parent result failed exact semantic replay"
        ) from error
    evidence = parent_result.runtime_result.supervisor_resource_evidence
    expected_roles = [
        row["role"] for row in evidence.to_document()["lifecycle_sequence"]
    ]
    if expected_roles != [
        "PROCESS_LAUNCH",
        "OUTPUT_EOF",
        "PROCESS_REAP",
        "CGROUP_EMPTY",
        "DESCENDANT_SCAN",
        "FINAL_MEMORY_PEAK",
        "MEMORY_CONTROLS_VERIFIED",
    ]:
        _fail("successful atomic supervisor lifecycle order changed")
    memory = V075K7VerifiedSharedResourceResolutionV1(
        _RESOLUTION_ISSUER,
        registry,
        parent_result,
        MEMORY_PATH,
        evidence.memory_peak_bytes,
    )
    process = V075K7VerifiedSharedResourceResolutionV1(
        _RESOLUTION_ISSUER,
        registry,
        parent_result,
        PROCESS_PATH,
        evidence.process_launches,
    )
    return V075K7AtomicSharedResourceVerificationV1(
        _VERIFICATION_ISSUER,
        registry,
        parent_result,
        (memory, process),
    )


__all__ = [
    "CHILD_RUNTIME_WINDOW_PATHS",
    "EXACT_CONNECTED_PATHS",
    "MEMORY_PATH",
    "NOT_CONNECTED_PATHS",
    "PROCESS_PATH",
    "PROFILE_KEY",
    "ProductionConnectionStatusV1",
    "RUNTIME_LOCAL_PATHS",
    "V075K7AtomicSharedResourceAuthorityV1Error",
    "V075K7AtomicSharedResourceVerificationV1",
    "V075K7ProductionSharedResourceRegistryV1",
    "V075K7VerifiedSharedResourceResolutionV1",
    "freeze_v075_k7_production_shared_resource_registry_v1",
    "verify_v075_k7_atomic_shared_resource_evidence_v1",
]
