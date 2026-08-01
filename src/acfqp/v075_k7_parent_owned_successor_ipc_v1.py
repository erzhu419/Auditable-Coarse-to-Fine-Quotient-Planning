"""Parent-owned successor IPC admission schema for the V0-075 K7 route.

This revision deliberately stops before launch.  It binds the existing K7
accounted-sealed route, the public signer registry, scientific/Phase-3E
occurrence identity, and the read-only OS-supervisor admission result. When
the host is not admitted it emits a structural prelaunch blocker with no
attempt-terminal authority. It never manufactures the future
child-business or parent-accounting-suffix frames.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import json
from typing import Any, Mapping, NoReturn

from acfqp import v075_k7_os_supervisor_admission_v1 as os_admission
from acfqp import v075_k7_root_cap_accounted_sealed_ipc_v1 as accounted
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_PARENT_OWNED_PRELAUNCH_BLOCKED_RESULT_V1_DOMAIN,
    V075_K7_PARENT_OWNED_SUCCESSOR_PROFILE_V1_DOMAIN,
    V075_K7_PARENT_OWNED_SUCCESSOR_REQUEST_V1_DOMAIN,
    V075_K7_SCIENTIFIC_PHASE3E_OCCURRENCE_MAPPING_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.95.0"
PROFILE_KEY = "v075_k7_parent_owned_successor_ipc_v1"
FUTURE_LAUNCHED_OUTPUT_ROLES = (
    "CHILD_OWNED_K7_BUSINESS",
    "PARENT_OWNED_ACCOUNTING_SUFFIX",
)
BOOTSTRAP_SOURCE_PATH = "acfqp/v075_k7_parent_owned_successor_ipc_v1.py"
REQUESTED_PHASE3E_DOMAIN_CONSTANTS = (
    "V075_K7_PARENT_OWNED_SUCCESSOR_PROFILE_V1_DOMAIN",
    "V075_K7_SCIENTIFIC_PHASE3E_OCCURRENCE_MAPPING_V1_DOMAIN",
    "V075_K7_PARENT_OWNED_SUCCESSOR_REQUEST_V1_DOMAIN",
    "V075_K7_PARENT_OWNED_PRELAUNCH_BLOCKED_RESULT_V1_DOMAIN",
)
LOCAL_DOMAIN_TAGS = frozenset(
    {
        V075_K7_PARENT_OWNED_SUCCESSOR_PROFILE_V1_DOMAIN,
        V075_K7_SCIENTIFIC_PHASE3E_OCCURRENCE_MAPPING_V1_DOMAIN,
        V075_K7_PARENT_OWNED_SUCCESSOR_REQUEST_V1_DOMAIN,
        V075_K7_PARENT_OWNED_PRELAUNCH_BLOCKED_RESULT_V1_DOMAIN,
    }
)
if not LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("parent-owned successor IPC domains are unregistered")

_PROFILE_ISSUER = object()
_MAPPING_ISSUER = object()
_REQUEST_ISSUER = object()
_BLOCKED_RESULT_ISSUER = object()


class V075K7ParentOwnedSuccessorIPCV1Error(ValueError):
    """The structural successor IPC identity graph is invalid."""


def _fail(message: str) -> NoReturn:
    raise V075K7ParentOwnedSuccessorIPCV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075K7ParentOwnedSuccessorIPCV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        _fail("successor IPC used an undeclared content domain")
    return content_id(domain, dict(payload))


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} bytes are empty or mistyped")
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: _fail(
                f"{label} contains non-finite {token}"
            ),
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        if isinstance(error, V075K7ParentOwnedSuccessorIPCV1Error):
            raise
        raise V075K7ParentOwnedSuccessorIPCV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON document")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("successor IPC JSON contains a duplicate key")
        result[key] = value
    return result


def _locks() -> dict[str, bool]:
    return {
        "semantic_source_evidence_verified": False,
        "shared_resource_semantics_verified": False,
        "counter_records_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "actual_projection_proof_issued": False,
        "formal_vector_authorized": False,
        "official_execution_allowed": False,
        "plan_certificate": False,
        "infeasibility_certificate": False,
    }


@dataclass(frozen=True, slots=True)
class V075K7ParentOwnedSuccessorIPCProfileV1:
    """Exact old-profile and OS-admission binding for the successor path."""

    _issuer: InitVar[object]
    accounted_profile: accounted.V075K7RootCapAccountedSealedIPCProfileV1 = field(
        repr=False, compare=False
    )
    admission_profile: os_admission.K7OSSupervisorAdmissionProfileV1 = field(
        repr=False, compare=False
    )
    _validated_refs: tuple[object, object] = field(init=False, repr=False)
    _validated_ids: tuple[str, str] = field(init=False, repr=False)
    _bootstrap_sha256: str = field(init=False, repr=False)
    _bootstrap_byte_count: int = field(init=False, repr=False)
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PROFILE_ISSUER
            or type(self.accounted_profile)
            is not accounted.V075K7RootCapAccountedSealedIPCProfileV1
            or type(self.admission_profile)
            is not os_admission.K7OSSupervisorAdmissionProfileV1
        ):
            _fail("successor profile is caller-minted or crossed")
        self.accounted_profile._assert_current()  # noqa: SLF001
        entries = tuple(
            (digest, size)
            for path, digest, size in self.accounted_profile.transport_profile.source_entries
            if path == BOOTSTRAP_SOURCE_PATH
        )
        if (
            len(entries) != 1
            or type(entries[0][0]) is not str
            or len(entries[0][0]) != 64
            or type(entries[0][1]) is not int
            or entries[0][1] <= 0
        ):
            _fail("sealed source snapshot lacks the exact successor bootstrap")
        refs = (self.accounted_profile, self.admission_profile)
        ids = (
            self.accounted_profile.profile_id,
            self.admission_profile.profile_id,
        )
        object.__setattr__(self, "_validated_refs", refs)
        object.__setattr__(self, "_validated_ids", ids)
        object.__setattr__(
            self,
            "_bootstrap_sha256",
            entries[0][0],
        )
        object.__setattr__(
            self, "_bootstrap_byte_count", entries[0][1]
        )
        object.__setattr__(
            self,
            "_profile_id",
            _hash(
                V075_K7_PARENT_OWNED_SUCCESSOR_PROFILE_V1_DOMAIN,
                self._payload(),
            ),
        )
        self._assert_current()

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_parent_owned_successor_ipc_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "accounted_sealed_profile_id": self._validated_ids[0],
            "accounted_sealed_profile": self.accounted_profile.to_document(),
            "os_supervisor_admission_profile_id": self._validated_ids[1],
            "os_supervisor_admission_profile": self.admission_profile.to_document(),
            "bootstrap_source_entry": {
                "path": BOOTSTRAP_SOURCE_PATH,
                "sha256": self._bootstrap_sha256,
                "byte_count": self._bootstrap_byte_count,
                "derived_from_sealed_source_snapshot": True,
            },
            "future_launched_output_frame_count": 2,
            "future_launched_output_frame_roles": list(
                FUTURE_LAUNCHED_OUTPUT_ROLES
            ),
            "child_business_precedes_parent_suffix": True,
            "parent_owned_suffix": True,
            "prelaunch_blocked_result_frame_count": 0,
            "attempt_terminal_authority_implemented": False,
            **_locks(),
        }

    def _assert_current(self) -> None:
        if (
            self.accounted_profile is not self._validated_refs[0]
            or self.admission_profile is not self._validated_refs[1]
        ):
            _fail("successor profile authority object was replaced")
        self.accounted_profile._assert_current()  # noqa: SLF001
        if (
            self.accounted_profile.profile_id,
            self.admission_profile.profile_id,
        ) != self._validated_ids:
            _fail("successor profile authority identity is stale")
        entries = tuple(
            (digest, size)
            for path, digest, size in self.accounted_profile.transport_profile.source_entries
            if path == BOOTSTRAP_SOURCE_PATH
        )
        if (
            entries != ((self._bootstrap_sha256, self._bootstrap_byte_count),)
            or _hash(
                V075_K7_PARENT_OWNED_SUCCESSOR_PROFILE_V1_DOMAIN,
                self._payload(),
            )
            != self._profile_id
        ):
            _fail("successor profile content changed after freeze")

    @property
    def profile_id(self) -> str:
        self._assert_current()
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "successor_profile_id": self._profile_id}


def freeze_v075_k7_parent_owned_successor_ipc_profile_v1(
    *,
    accounted_profile: accounted.V075K7RootCapAccountedSealedIPCProfileV1,
    admission_profile: os_admission.K7OSSupervisorAdmissionProfileV1 | None = None,
) -> V075K7ParentOwnedSuccessorIPCProfileV1:
    return V075K7ParentOwnedSuccessorIPCProfileV1(
        _PROFILE_ISSUER,
        accounted_profile,
        (
            os_admission.official_v075_k7_os_supervisor_admission_profile_v1()
            if admission_profile is None
            else admission_profile
        ),
    )


@dataclass(frozen=True, slots=True)
class V075K7ScientificPhase3EOccurrenceMappingV1:
    _issuer: InitVar[object]
    scientific_occurrence_id: str
    scientific_schedule_id: str
    phase3e_logical_occurrence_id: str

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _MAPPING_ISSUER:
            _fail("scientific occurrence mapping is caller-minted")
        _cid(self.scientific_occurrence_id, "scientific K7 occurrence")
        _cid(self.scientific_schedule_id, "scientific K7 schedule")
        _cid(self.phase3e_logical_occurrence_id, "Phase-3E logical occurrence")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_scientific_phase3e_occurrence_mapping.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "scientific_occurrence_id": self.scientific_occurrence_id,
            "scientific_schedule_id": self.scientific_schedule_id,
            "phase3e_logical_occurrence_id": self.phase3e_logical_occurrence_id,
            "mapping_cardinality": "ONE_TO_ONE_FOR_THIS_REQUEST",
        }

    @property
    def mapping_id(self) -> str:
        return _hash(
            V075_K7_SCIENTIFIC_PHASE3E_OCCURRENCE_MAPPING_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_mapping_id": self.mapping_id}


def _freeze_mapping(
    *,
    scientific_occurrence_id: str,
    scientific_schedule_id: str,
    phase3e_logical_occurrence_id: str,
) -> V075K7ScientificPhase3EOccurrenceMappingV1:
    return V075K7ScientificPhase3EOccurrenceMappingV1(
        _MAPPING_ISSUER,
        scientific_occurrence_id,
        scientific_schedule_id,
        phase3e_logical_occurrence_id,
    )


@dataclass(frozen=True, slots=True)
class V075K7ParentOwnedSuccessorRequestV1:
    _issuer: InitVar[object]
    profile: V075K7ParentOwnedSuccessorIPCProfileV1 = field(
        repr=False, compare=False
    )
    route_identity: accounted.V075K7RootCapAccountedSealedRouteIdentityV1 = field(
        repr=False, compare=False
    )
    signer_registry: public_authority.V075TrustedSignerRegistryV1 = field(
        repr=False, compare=False
    )
    opaque_environment_commitment_id: str
    sealed_secret_commitment_id: str
    session_external_id: str
    request_nonce: str
    scientific_occurrence_id: str
    schedule_id: str
    occurrence_mapping: V075K7ScientificPhase3EOccurrenceMappingV1 = field(
        repr=False, compare=False
    )
    _validated_refs: tuple[object, ...] = field(init=False, repr=False)
    _validated_registry_bytes: bytes = field(init=False, repr=False)
    _request_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _REQUEST_ISSUER
            or type(self.profile) is not V075K7ParentOwnedSuccessorIPCProfileV1
            or type(self.route_identity)
            is not accounted.V075K7RootCapAccountedSealedRouteIdentityV1
            or type(self.signer_registry)
            is not public_authority.V075TrustedSignerRegistryV1
            or type(self.occurrence_mapping)
            is not V075K7ScientificPhase3EOccurrenceMappingV1
        ):
            _fail("successor request is caller-minted or has a foreign authority")
        self.profile._assert_current()
        self.route_identity._assert_current()
        for value, label in (
            (self.opaque_environment_commitment_id, "opaque commitment"),
            (self.sealed_secret_commitment_id, "sealed secret commitment"),
            (self.session_external_id, "session external identity"),
            (self.request_nonce, "successor request nonce"),
            (self.scientific_occurrence_id, "scientific K7 occurrence"),
            (self.schedule_id, "scientific schedule"),
        ):
            _cid(value, label)
        if (
            self.route_identity.profile is not self.profile.accounted_profile
            or self.occurrence_mapping.scientific_occurrence_id
            != self.scientific_occurrence_id
            or self.occurrence_mapping.scientific_schedule_id
            != self.schedule_id
            or self.occurrence_mapping.phase3e_logical_occurrence_id
            != self.route_identity.logical_occurrence.logical_occurrence_id
        ):
            _fail("successor request occurrence/route identity graph is crossed")
        registry_bytes = canonical_json_bytes(self.signer_registry.to_document())
        object.__setattr__(
            self,
            "_validated_refs",
            (
                self.profile,
                self.route_identity,
                self.signer_registry,
                self.occurrence_mapping,
            ),
        )
        object.__setattr__(self, "_validated_registry_bytes", registry_bytes)
        object.__setattr__(
            self,
            "_request_id",
            _hash(
                V075_K7_PARENT_OWNED_SUCCESSOR_REQUEST_V1_DOMAIN,
                self._payload(),
            ),
        )
        self._assert_current()

    def _assert_current(self) -> None:
        refs = (
            self.profile,
            self.route_identity,
            self.signer_registry,
            self.occurrence_mapping,
        )
        if any(a is not b for a, b in zip(refs, self._validated_refs)):
            _fail("successor request authority object was replaced")
        self.profile._assert_current()
        self.route_identity._assert_current()
        if (
            self.route_identity.profile is not self.profile.accounted_profile
            or canonical_json_bytes(self.signer_registry.to_document())
            != self._validated_registry_bytes
            or self.occurrence_mapping.scientific_occurrence_id
            != self.scientific_occurrence_id
            or self.occurrence_mapping.scientific_schedule_id
            != self.schedule_id
            or self.occurrence_mapping.phase3e_logical_occurrence_id
            != self.route_identity.logical_occurrence.logical_occurrence_id
        ):
            _fail("successor request authority content is stale")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_parent_owned_successor_request.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "successor_profile_id": self.profile.profile_id,
            "route_identity_id": self.route_identity.route_identity_id,
            "route_identity": self.route_identity.to_document(),
            "signer_registry_id": self.signer_registry.registry_id,
            "signer_registry": self.signer_registry.to_document(),
            "opaque_environment_commitment_id": (
                self.opaque_environment_commitment_id
            ),
            "sealed_secret_commitment_id": self.sealed_secret_commitment_id,
            "session_external_id": self.session_external_id,
            "request_nonce": self.request_nonce,
            "scientific_occurrence_id": self.scientific_occurrence_id,
            "schedule_id": self.schedule_id,
            "occurrence_mapping_id": self.occurrence_mapping.mapping_id,
            "occurrence_mapping": self.occurrence_mapping.to_document(),
            "phase3e_logical_occurrence_id": (
                self.occurrence_mapping.phase3e_logical_occurrence_id
            ),
            "caller_supplied_signer": False,
            "caller_supplied_private_result": False,
            "caller_supplied_cutoff": False,
            "expected_launched_output_frame_count": 2,
            "expected_launched_output_frame_roles": list(
                FUTURE_LAUNCHED_OUTPUT_ROLES
            ),
            **_locks(),
        }

    @property
    def request_id(self) -> str:
        self._assert_current()
        current = _hash(
            V075_K7_PARENT_OWNED_SUCCESSOR_REQUEST_V1_DOMAIN,
            self._payload(),
        )
        if current != self._request_id:
            _fail("successor request changed after freeze")
        return self._request_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "request_id": self.request_id}


def freeze_v075_k7_parent_owned_successor_request_v1(
    *,
    profile: V075K7ParentOwnedSuccessorIPCProfileV1,
    route_identity: accounted.V075K7RootCapAccountedSealedRouteIdentityV1,
    signer_registry: public_authority.V075TrustedSignerRegistryV1,
    opaque_environment_commitment_id: str,
    sealed_secret_commitment_id: str,
    session_external_id: str,
    request_nonce: str,
    scientific_occurrence_id: str,
    schedule_id: str,
) -> V075K7ParentOwnedSuccessorRequestV1:
    mapping = _freeze_mapping(
        scientific_occurrence_id=scientific_occurrence_id,
        scientific_schedule_id=schedule_id,
        phase3e_logical_occurrence_id=(
            route_identity.logical_occurrence.logical_occurrence_id
        ),
    )
    return V075K7ParentOwnedSuccessorRequestV1(
        _REQUEST_ISSUER,
        profile,
        route_identity,
        signer_registry,
        opaque_environment_commitment_id,
        sealed_secret_commitment_id,
        session_external_id,
        request_nonce,
        scientific_occurrence_id,
        schedule_id,
        mapping,
    )


def verify_v075_k7_parent_owned_successor_request_bytes_v1(
    *, raw: bytes, expected: V075K7ParentOwnedSuccessorRequestV1
) -> V075K7ParentOwnedSuccessorRequestV1:
    if type(expected) is not V075K7ParentOwnedSuccessorRequestV1:
        _fail("request replay requires the exact expected request authority")
    document = _canonical_document(raw, "successor request")
    expected_document = expected.to_document()
    if canonical_json_bytes(document) != canonical_json_bytes(expected_document):
        _fail("successor request bytes/document binding changed")
    return expected


@dataclass(frozen=True, slots=True)
class V075K7ParentOwnedPrelaunchBlockedResultV1:
    """Structural blocker; a future executor must issue any attempt terminal."""

    _issuer: InitVar[object]
    request: V075K7ParentOwnedSuccessorRequestV1 = field(
        repr=False, compare=False
    )
    admission_result: os_admission.K7OSSupervisorAdmissionResultV1 = field(
        repr=False, compare=False
    )
    _validated_refs: tuple[object, object] = field(init=False, repr=False)
    _validated_ids: tuple[str, str] = field(init=False, repr=False)
    _blocked_result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BLOCKED_RESULT_ISSUER
            or type(self.request) is not V075K7ParentOwnedSuccessorRequestV1
            or type(self.admission_result)
            is not os_admission.K7OSSupervisorAdmissionResultV1
        ):
            _fail("prelaunch blocked result is caller-minted or foreign")
        self.request._assert_current()
        os_admission.verify_v075_k7_os_supervisor_admission_v1(
            self.admission_result
        )
        if (
            self.admission_result.profile is not self.request.profile.admission_profile
            or self.admission_result.status
            is not os_admission.K7OSSupervisorAdmissionStatusV1.NOT_AVAILABLE
            or self.admission_result.to_document()["child_launch_attempted"]
            is not False
        ):
            _fail("prelaunch blocked result crossed or admitted execution")
        object.__setattr__(
            self, "_validated_refs", (self.request, self.admission_result)
        )
        object.__setattr__(
            self,
            "_validated_ids",
            (self.request.request_id, self.admission_result.result_id),
        )
        object.__setattr__(
            self,
            "_blocked_result_id",
            _hash(
                V075_K7_PARENT_OWNED_PRELAUNCH_BLOCKED_RESULT_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _assert_current(self) -> None:
        if (
            self.request is not self._validated_refs[0]
            or self.admission_result is not self._validated_refs[1]
        ):
            _fail("prelaunch blocked-result authority object was replaced")
        self.request._assert_current()
        os_admission.verify_v075_k7_os_supervisor_admission_v1(
            self.admission_result
        )
        if (
            self.request.request_id,
            self.admission_result.result_id,
        ) != self._validated_ids:
            _fail("prelaunch blocked-result identity changed after issuance")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_parent_owned_prelaunch_blocked_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "successor_profile_id": self.request.profile.profile_id,
            "request_id": self.request.request_id,
            "route_identity_id": self.request.route_identity.route_identity_id,
            "scientific_occurrence_id": self.request.scientific_occurrence_id,
            "phase3e_logical_occurrence_id": (
                self.request.occurrence_mapping.phase3e_logical_occurrence_id
            ),
            "route_attempt_id": (
                self.request.route_identity.route_attempt.route_attempt_id
            ),
            "decision_point_id": (
                self.request.route_identity.decision_point.decision_point_id
            ),
            "transaction_id": (
                self.request.route_identity.transaction.transaction_id
            ),
            "os_supervisor_admission_profile_id": (
                self.admission_result.profile.profile_id
            ),
            "os_supervisor_admission_result_id": self.admission_result.result_id,
            "os_supervisor_admission_result": (
                self.admission_result.to_document()
            ),
            "blocked_scope": "STRUCTURAL_PRELAUNCH_ADMISSION",
            "attempt_terminal_issued": False,
            "noncertificate_closure_issued": False,
            "successor_executor_process_launches": 0,
            "child_output_frame_count": 0,
            "parent_output_frame_count": 0,
            "total_output_frame_count": 0,
            "child_business_frame_issued": False,
            "parent_accounting_suffix_frame_issued": False,
            "parent_owned_suffix_required_on_launched_path": True,
            "nine_shared_resource_paths_issued": False,
            **_locks(),
        }

    @property
    def blocked_result_id(self) -> str:
        self._assert_current()
        current = _hash(
            V075_K7_PARENT_OWNED_PRELAUNCH_BLOCKED_RESULT_V1_DOMAIN,
            self._payload(),
        )
        if current != self._blocked_result_id:
            _fail("prelaunch blocked result changed after issuance")
        return self._blocked_result_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "prelaunch_blocked_result_id": self.blocked_result_id,
        }


def block_v075_k7_parent_owned_prelaunch_v1(
    *,
    request: V075K7ParentOwnedSuccessorRequestV1,
    admission_result: os_admission.K7OSSupervisorAdmissionResultV1,
) -> V075K7ParentOwnedPrelaunchBlockedResultV1:
    return V075K7ParentOwnedPrelaunchBlockedResultV1(
        _BLOCKED_RESULT_ISSUER, request, admission_result
    )


__all__ = [
    "BOOTSTRAP_SOURCE_PATH",
    "FUTURE_LAUNCHED_OUTPUT_ROLES",
    "LOCAL_DOMAIN_TAGS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_CONSTANTS",
    "SCHEMA_VERSION",
    "V075K7ParentOwnedPrelaunchBlockedResultV1",
    "V075K7ParentOwnedSuccessorIPCProfileV1",
    "V075K7ParentOwnedSuccessorIPCV1Error",
    "V075K7ParentOwnedSuccessorRequestV1",
    "V075K7ScientificPhase3EOccurrenceMappingV1",
    "block_v075_k7_parent_owned_prelaunch_v1",
    "freeze_v075_k7_parent_owned_successor_ipc_profile_v1",
    "freeze_v075_k7_parent_owned_successor_request_v1",
    "verify_v075_k7_parent_owned_successor_request_bytes_v1",
]
