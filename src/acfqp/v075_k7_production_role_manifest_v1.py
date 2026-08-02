"""Issuer-owned worker/business role manifest for the live K7 broker.

This additive construction object closes the static launch-plan degrees of
freedom left by the V0-110B-2C probe.  It derives its request, route, prepared
session, source archive and interpreter identities from retained authorities;
callers cannot choose a program, cgroup, argument, environment or descriptor
role.  It does not execute either role and therefore authorizes no live frame,
resource value, formal accounting object or terminal.

All identities use the central Phase-3E domain registry.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp import v075_k7_outer_attempt_broker_preparation_v1 as preparation_v1
from acfqp import v075_k7_parent_owned_successor_ipc_v1 as successor_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_PRODUCTION_ROLE_MANIFEST_PROFILE_V1_DOMAIN,
    V075_K7_PRODUCTION_ROLE_MANIFEST_V1_DOMAIN,
    V075_K7_PRODUCTION_ROLE_SPEC_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.7"
PROFILE_KEY = "v075_k7_production_role_manifest_v1"

REQUESTED_PHASE3E_DOMAIN_CONSTANTS = (
    "V075_K7_PRODUCTION_ROLE_MANIFEST_PROFILE_V1_DOMAIN",
    "V075_K7_PRODUCTION_ROLE_SPEC_V1_DOMAIN",
    "V075_K7_PRODUCTION_ROLE_MANIFEST_V1_DOMAIN",
)
LOCAL_DOMAIN_TAGS = frozenset(
    {
        V075_K7_PRODUCTION_ROLE_MANIFEST_PROFILE_V1_DOMAIN,
        V075_K7_PRODUCTION_ROLE_SPEC_V1_DOMAIN,
        V075_K7_PRODUCTION_ROLE_MANIFEST_V1_DOMAIN,
    }
)
if not LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS:
    raise RuntimeError("production role-manifest domains are unregistered")

ROLE_ORDER = ("WORKER", "BUSINESS")
FRAME_AUTHOR_VECTOR = (
    (ipc_v1.K7OuterAttemptBrokerFrameRoleV1.WORKER_READY.value, "WORKER"),
    (ipc_v1.K7OuterAttemptBrokerFrameRoleV1.BUSINESS_REQUEST.value, "WORKER"),
    (ipc_v1.K7OuterAttemptBrokerFrameRoleV1.BUSINESS_RESULT.value, "BUSINESS"),
    (ipc_v1.K7OuterAttemptBrokerFrameRoleV1.PARENT_OUTPUT.value, "WORKER"),
    (ipc_v1.K7OuterAttemptBrokerFrameRoleV1.WORKER_EOF.value, "WORKER"),
)

BASE_ENVIRONMENT = (
    ("LANG", "C"),
    ("LC_ALL", "C"),
    ("TZ", "UTC"),
)
WORKER_RUNTIME_ENVIRONMENT = (
    ("ACFQP_K7_BROKER_CHANNEL_FD", "BROKER_CHANNEL"),
    ("ACFQP_K7_BUSINESS_RESULT_FD", "BUSINESS_RESULT_READONLY"),
    ("ACFQP_K7_OUTPUT_DIRECTORY_FD", "OUTPUT_DIRECTORY"),
    ("ACFQP_K7_ROLE", "WORKER"),
    ("ACFQP_K7_SEALED_INPUT_FDS", "ORDERED_SEALED_INPUTS"),
)
BUSINESS_RUNTIME_ENVIRONMENT = (
    ("ACFQP_K7_BROKER_CHANNEL_FD", "BROKER_CHANNEL"),
    ("ACFQP_K7_BUSINESS_RESULT_FD", "BUSINESS_RESULT_WRITABLE"),
    ("ACFQP_K7_ROLE", "BUSINESS"),
    ("ACFQP_K7_SEALED_INPUT_FDS", "ORDERED_SEALED_INPUTS"),
)

WORKER_SEALED_INPUT_ROLES = (
    "SOURCE_ARCHIVE",
    "TRANSPORT_PROFILE",
    "LIFECYCLE_PROFILE",
    "SUCCESSOR_PROFILE",
    "SUCCESSOR_REQUEST",
)
BUSINESS_SEALED_INPUT_ROLES = (*WORKER_SEALED_INPUT_ROLES, "LIFECYCLE_SECRET")
WORKER_INHERITED_FD_ROLES = (
    "EXECUTABLE",
    *WORKER_SEALED_INPUT_ROLES,
    "BROKER_CHANNEL",
    "BUSINESS_RESULT_READONLY",
    "OUTPUT_DIRECTORY",
)
BUSINESS_INHERITED_FD_ROLES = (
    "EXECUTABLE",
    *BUSINESS_SEALED_INPUT_ROLES,
    "BROKER_CHANNEL",
    "BUSINESS_RESULT_WRITABLE",
)
FORBIDDEN_EXEC_IMAGE_FD_ROLES = (
    "DELEGATED_PARENT",
    "ATTEMPT_ANCESTOR",
    "WORKER_CGROUP",
    "BUSINESS_CGROUP",
    "CGROUP_KILL",
    "MEMORY_PEAK",
    "OTHER_ROLE_CHANNEL",
    "OTHER_ROLE_PIDFD",
    "BROKER_LAUNCH_AUTHORITY",
)

WORKER_ENTRY_MODULE = "acfqp.v075_k7_broker_worker_process_entry_v1"
WORKER_ENTRY_SYMBOL = "run_v075_k7_broker_worker_entry_v1"
BUSINESS_ENTRY_MODULE = "acfqp.v075_k7_broker_business_process_entry_v1"
BUSINESS_ENTRY_SYMBOL = "run_v075_k7_broker_business_entry_v1"
WORKER_ENTRY_SOURCE_PATH = "acfqp/v075_k7_broker_worker_process_entry_v1.py"
BUSINESS_ENTRY_SOURCE_PATH = "acfqp/v075_k7_broker_business_process_entry_v1.py"
ENTRY_SOURCE_STATUS = "NOT_PRESENT_IN_SEALED_SOURCE_ARCHIVE"

# These are exact future ``python -c`` dispatch programs, not an assertion
# that the entry modules have already been implemented in the current archive.
WORKER_ENTRY_SOURCE = (
    "from acfqp.v075_k7_broker_worker_process_entry_v1 import "
    "run_v075_k7_broker_worker_entry_v1 as _run;"
    "raise SystemExit(_run())"
)
BUSINESS_ENTRY_SOURCE = (
    "from acfqp.v075_k7_broker_business_process_entry_v1 import "
    "run_v075_k7_broker_business_entry_v1 as _run;"
    "raise SystemExit(_run())"
)
WORKER_DISPATCH_SHA256 = hashlib.sha256(
    WORKER_ENTRY_SOURCE.encode("utf-8")
).hexdigest()
BUSINESS_DISPATCH_SHA256 = hashlib.sha256(
    BUSINESS_ENTRY_SOURCE.encode("utf-8")
).hexdigest()
WORKER_ARGV = (
    "acfqp-k7-broker-worker-v1",
    "-I",
    "-S",
    "-B",
    "-c",
    WORKER_ENTRY_SOURCE,
)
BUSINESS_ARGV = (
    "acfqp-k7-broker-business-v1",
    "-I",
    "-S",
    "-B",
    "-c",
    BUSINESS_ENTRY_SOURCE,
)

_PROFILE_ISSUER = object()
_ROLE_ISSUER = object()
_MANIFEST_ISSUER = object()


class V075K7ProductionRoleManifestV1Error(ValueError):
    """A production role plan is caller-selected, stale, or crossed."""


class K7ProductionBrokerRoleV1(str, Enum):
    WORKER = "WORKER"
    BUSINESS = "BUSINESS"


def _fail(message: str) -> NoReturn:
    raise V075K7ProductionRoleManifestV1Error(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        _fail("production role manifest used an undeclared content domain")
    return content_id(domain, dict(payload))


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075K7ProductionRoleManifestV1Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{label} must be one lowercase SHA-256 digest")
    return value


def _descriptor(value: Mapping[str, Any], label: str) -> Mapping[str, int]:
    if type(value) not in {dict, MappingProxyType}:
        _fail(f"{label} descriptor identity has the wrong mapping type")
    expected = {"device", "inode", "mode", "owner_uid", "owner_gid"}
    if set(value) != expected or any(type(value[key]) is not int for key in expected):
        _fail(f"{label} descriptor identity is incomplete or mistyped")
    if any(value[key] < 0 for key in expected):
        _fail(f"{label} descriptor identity contains a negative value")
    return MappingProxyType({key: value[key] for key in sorted(expected)})


def _formal_locks() -> dict[str, bool]:
    return {
        "role_entry_implementation_present": False,
        "role_bootstraps_materialized": False,
        "live_broker_execution_authorized": False,
        "live_frame_sender_provenance_verified": False,
        "operational_output_committed": False,
        "shared_resource_semantics_verified": False,
        "counter_record_authorized": False,
        "work_vector_authorized": False,
        "comparison_vector_authorized": False,
        "attempt_terminal_authorized": False,
        "official_execution_allowed": False,
    }


@dataclass(frozen=True, slots=True)
class K7ProductionRoleManifestProfileV1:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("production role-manifest profile is issuer-owned")
        object.__setattr__(
            self,
            "_profile_id",
            _hash(
                V075_K7_PRODUCTION_ROLE_MANIFEST_PROFILE_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_production_role_manifest_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "role_order": list(ROLE_ORDER),
            "cgroup_names": ["worker", "business"],
            "frame_author_vector": [
                {"frame_role": frame, "author_role": author}
                for frame, author in FRAME_AUTHOR_VECTOR
            ],
            "caller_program_selection_allowed": False,
            "caller_argv_selection_allowed": False,
            "caller_environment_selection_allowed": False,
            "caller_fd_role_selection_allowed": False,
            "caller_cgroup_selection_allowed": False,
            "source_and_interpreter_derived_from_request": True,
            "prepared_session_exact_object_binding_required": True,
            "live_prepared_guardian_replay_required": True,
            "same_address_space_private_sentinels_are_security_capabilities": False,
            "construction_only": True,
            "formal_locks": _formal_locks(),
        }

    @property
    def profile_id(self) -> str:
        current = _hash(
            V075_K7_PRODUCTION_ROLE_MANIFEST_PROFILE_V1_DOMAIN,
            self._payload(),
        )
        if current != self._profile_id:
            _fail("production role-manifest profile changed after issuance")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "production_role_manifest_profile_id": self.profile_id}


_OFFICIAL_PROFILE = K7ProductionRoleManifestProfileV1(_PROFILE_ISSUER)


def official_v075_k7_production_role_manifest_profile_v1(
) -> K7ProductionRoleManifestProfileV1:
    return _OFFICIAL_PROFILE


@dataclass(frozen=True, slots=True)
class K7ProductionRoleSpecV1:
    _issuer: InitVar[object]
    role: K7ProductionBrokerRoleV1
    ordinal: int
    cgroup_name: str
    cgroup_descriptor_identity: Mapping[str, int]
    entry_module: str
    entry_symbol: str
    dispatch_sha256: str
    entry_source_path: str
    entry_source_sha256: None
    entry_source_byte_count: None
    entry_source_present: bool
    argv: tuple[str, ...]
    base_environment: Mapping[str, str]
    runtime_environment_contract: Mapping[str, str]
    sealed_input_roles: tuple[str, ...]
    inherited_fd_roles: tuple[str, ...]
    writable_fd_roles: tuple[str, ...]
    authored_frame_roles: tuple[str, ...]
    _role_spec_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROLE_ISSUER:
            _fail("production broker role spec is issuer-owned")
        try:
            exact_role = K7ProductionBrokerRoleV1(self.role)
        except (TypeError, ValueError) as error:
            raise V075K7ProductionRoleManifestV1Error(
                "production broker role is unknown"
            ) from error
        expected = _expected_role_fields(exact_role)
        actual = {
            "ordinal": self.ordinal,
            "cgroup_name": self.cgroup_name,
            "entry_module": self.entry_module,
            "entry_symbol": self.entry_symbol,
            "dispatch_sha256": self.dispatch_sha256,
            "entry_source_path": self.entry_source_path,
            "entry_source_sha256": self.entry_source_sha256,
            "entry_source_byte_count": self.entry_source_byte_count,
            "entry_source_present": self.entry_source_present,
            "argv": self.argv,
            "base_environment": dict(self.base_environment),
            "runtime_environment_contract": dict(self.runtime_environment_contract),
            "sealed_input_roles": self.sealed_input_roles,
            "inherited_fd_roles": self.inherited_fd_roles,
            "writable_fd_roles": self.writable_fd_roles,
            "authored_frame_roles": self.authored_frame_roles,
        }
        if actual != expected:
            _fail("production broker role fields differ from the fixed contract")
        object.__setattr__(self, "role", exact_role)
        object.__setattr__(
            self,
            "cgroup_descriptor_identity",
            _descriptor(self.cgroup_descriptor_identity, exact_role.value.lower()),
        )
        object.__setattr__(
            self, "base_environment", MappingProxyType(dict(self.base_environment))
        )
        object.__setattr__(
            self,
            "runtime_environment_contract",
            MappingProxyType(dict(self.runtime_environment_contract)),
        )
        object.__setattr__(
            self,
            "_role_spec_id",
            _hash(V075_K7_PRODUCTION_ROLE_SPEC_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_production_role_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "production_role_manifest_profile_id": _OFFICIAL_PROFILE.profile_id,
            "role": self.role.value,
            "ordinal": self.ordinal,
            "cgroup_name": self.cgroup_name,
            "cgroup_descriptor_identity": dict(self.cgroup_descriptor_identity),
            "entry_module": self.entry_module,
            "entry_symbol": self.entry_symbol,
            "dispatch_sha256": self.dispatch_sha256,
            "entry_source_path": self.entry_source_path,
            "entry_source_sha256": self.entry_source_sha256,
            "entry_source_byte_count": self.entry_source_byte_count,
            "entry_source_present": self.entry_source_present,
            "entry_source_status": ENTRY_SOURCE_STATUS,
            "dispatch_digest_is_not_entry_source_digest": True,
            "argv": list(self.argv),
            "base_environment": dict(self.base_environment),
            "runtime_environment_contract": dict(self.runtime_environment_contract),
            "sealed_input_roles": list(self.sealed_input_roles),
            "inherited_fd_roles": list(self.inherited_fd_roles),
            "writable_fd_roles": list(self.writable_fd_roles),
            "forbidden_exec_image_fd_roles": list(FORBIDDEN_EXEC_IMAGE_FD_ROLES),
            "authored_frame_roles": list(self.authored_frame_roles),
            "no_unregistered_inherited_fd_allowed": True,
            "caller_mutation_allowed": False,
            "formal_locks": _formal_locks(),
        }

    @property
    def role_spec_id(self) -> str:
        current = _hash(
            V075_K7_PRODUCTION_ROLE_SPEC_V1_DOMAIN, self._payload()
        )
        if current != self._role_spec_id:
            _fail("production broker role spec changed after issuance")
        return self._role_spec_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "production_role_spec_id": self.role_spec_id}


def _expected_role_fields(role: K7ProductionBrokerRoleV1) -> dict[str, Any]:
    worker = role is K7ProductionBrokerRoleV1.WORKER
    return {
        "ordinal": 0 if worker else 1,
        "cgroup_name": "worker" if worker else "business",
        "entry_module": WORKER_ENTRY_MODULE if worker else BUSINESS_ENTRY_MODULE,
        "entry_symbol": WORKER_ENTRY_SYMBOL if worker else BUSINESS_ENTRY_SYMBOL,
        "dispatch_sha256": (
            WORKER_DISPATCH_SHA256 if worker else BUSINESS_DISPATCH_SHA256
        ),
        "entry_source_path": (
            WORKER_ENTRY_SOURCE_PATH if worker else BUSINESS_ENTRY_SOURCE_PATH
        ),
        "entry_source_sha256": None,
        "entry_source_byte_count": None,
        "entry_source_present": False,
        "argv": WORKER_ARGV if worker else BUSINESS_ARGV,
        "base_environment": dict(BASE_ENVIRONMENT),
        "runtime_environment_contract": dict(
            WORKER_RUNTIME_ENVIRONMENT if worker else BUSINESS_RUNTIME_ENVIRONMENT
        ),
        "sealed_input_roles": (
            WORKER_SEALED_INPUT_ROLES if worker else BUSINESS_SEALED_INPUT_ROLES
        ),
        "inherited_fd_roles": (
            WORKER_INHERITED_FD_ROLES if worker else BUSINESS_INHERITED_FD_ROLES
        ),
        "writable_fd_roles": (
            ("OUTPUT_DIRECTORY",)
            if worker
            else ("BUSINESS_RESULT_WRITABLE",)
        ),
        "authored_frame_roles": tuple(
            frame for frame, author in FRAME_AUTHOR_VECTOR if author == role.value
        ),
    }


def _freeze_role(
    role: K7ProductionBrokerRoleV1,
    descriptor_identity: Mapping[str, int],
) -> K7ProductionRoleSpecV1:
    values = _expected_role_fields(role)
    return K7ProductionRoleSpecV1(
        _ROLE_ISSUER,
        role,
        values["ordinal"],
        values["cgroup_name"],
        descriptor_identity,
        values["entry_module"],
        values["entry_symbol"],
        values["dispatch_sha256"],
        values["entry_source_path"],
        values["entry_source_sha256"],
        values["entry_source_byte_count"],
        values["entry_source_present"],
        values["argv"],
        values["base_environment"],
        values["runtime_environment_contract"],
        values["sealed_input_roles"],
        values["inherited_fd_roles"],
        values["writable_fd_roles"],
        values["authored_frame_roles"],
    )


@dataclass(frozen=True, slots=True)
class K7ProductionRoleManifestV1:
    _issuer: InitVar[object]
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1 = field(
        repr=False, compare=False
    )
    prepared_session: preparation_v1.K7OuterAttemptPreparedBrokerSessionV1 = field(
        repr=False, compare=False
    )
    worker_role: K7ProductionRoleSpecV1
    business_role: K7ProductionRoleSpecV1
    source_snapshot_id: str
    source_archive_sha256: str
    source_archive_byte_count: int
    transport_profile_id: str
    runtime_id: str
    interpreter_sha256: str
    interpreter_byte_count: int
    _validated_refs: tuple[object, object, object] = field(init=False, repr=False)
    _validated_ids: tuple[str, str, str] = field(init=False, repr=False)
    _validated_route_identity_id: str = field(init=False, repr=False)
    _manifest_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _MANIFEST_ISSUER
            or type(self.request)
            is not successor_v1.V075K7ParentOwnedSuccessorRequestV1
            or type(self.prepared_session)
            is not preparation_v1.K7OuterAttemptPreparedBrokerSessionV1
            or type(self.worker_role) is not K7ProductionRoleSpecV1
            or type(self.business_role) is not K7ProductionRoleSpecV1
        ):
            _fail("production role manifest is caller-minted or mistyped")
        if (
            self.worker_role.role is not K7ProductionBrokerRoleV1.WORKER
            or self.business_role.role is not K7ProductionBrokerRoleV1.BUSINESS
        ):
            _fail("production role manifest crossed worker/business roles")
        _cid(self.source_snapshot_id, "source snapshot")
        _sha256(self.source_archive_sha256, "source archive")
        _cid(self.transport_profile_id, "transport profile")
        _cid(self.runtime_id, "runtime")
        _sha256(self.interpreter_sha256, "interpreter")
        if (
            type(self.source_archive_byte_count) is not int
            or self.source_archive_byte_count <= 0
            or type(self.interpreter_byte_count) is not int
            or self.interpreter_byte_count <= 0
        ):
            _fail("production source/interpreter byte counts must be positive integers")
        object.__setattr__(
            self,
            "_validated_refs",
            (self.request, self.prepared_session, self.request.route_identity),
        )
        object.__setattr__(
            self,
            "_validated_ids",
            (
                self.request.request_id,
                self.prepared_session.session_id,
                self.prepared_session.execution_spec.spec_id,
            ),
        )
        object.__setattr__(
            self,
            "_validated_route_identity_id",
            self.request.route_identity.route_identity_id,
        )
        self._assert_static_binding()
        object.__setattr__(
            self,
            "_manifest_id",
            _hash(
                V075_K7_PRODUCTION_ROLE_MANIFEST_V1_DOMAIN, self._payload()
            ),
        )

    @property
    def request_id(self) -> str:
        return self._validated_ids[0]

    @property
    def prepared_session_id(self) -> str:
        return self._validated_ids[1]

    @property
    def broker_execution_spec_id(self) -> str:
        return self._validated_ids[2]

    @property
    def worker_dispatch_sha256(self) -> str:
        return self.worker_role.dispatch_sha256

    @property
    def business_dispatch_sha256(self) -> str:
        return self.business_role.dispatch_sha256

    def _assert_static_binding(self) -> None:
        request = self.request
        session = self.prepared_session
        try:
            request._assert_current()  # noqa: SLF001 - retained authority replay
            session.assert_prepared_current()
        except V075K7ProductionRoleManifestV1Error:
            raise
        except Exception as error:
            raise V075K7ProductionRoleManifestV1Error(
                "production role manifest retained authority is stale"
            ) from error
        if (
            session.binding.request_id != request.request_id
            or session.binding.route_identity_id
            != request.route_identity.route_identity_id
            or session.binding.broker_execution_spec_id
            != session.execution_spec.spec_id
            or session.execution_spec.request_id != request.request_id
            or session.execution_spec.route_identity_id
            != request.route_identity.route_identity_id
            or session.execution_spec.session_nonce != session.binding.session_nonce
        ):
            _fail("production role manifest crossed request/session/route binding")
        transport = request.profile.accounted_profile.transport_profile
        runtime = transport.runtime_document
        if (
            self.source_snapshot_id != transport.source_snapshot_id
            or self.source_archive_sha256 != transport.source_archive_sha256
            or self.source_archive_byte_count != transport.source_archive_byte_count
            or self.transport_profile_id != transport.profile_id
            or self.runtime_id != transport.runtime_id
            or type(runtime) is not dict
            or self.interpreter_sha256 != runtime.get("executable_sha256")
            or self.interpreter_byte_count != runtime.get("executable_byte_count")
            or self.worker_role.cgroup_name != "worker"
            or dict(self.worker_role.cgroup_descriptor_identity)
            != dict(session.execution_spec.worker_identity)
            or self.business_role.cgroup_name != "business"
            or dict(self.business_role.cgroup_descriptor_identity)
            != dict(session.execution_spec.business_identity)
        ):
            _fail("production role manifest source/interpreter/cgroup binding changed")
        archived_paths = tuple(
            path for path, _digest, _size in transport.source_entries
        )
        if (
            self.worker_role.entry_source_path in archived_paths
            or self.business_role.entry_source_path in archived_paths
        ):
            _fail(
                "construction manifest cannot advertise an unbound role entry source"
            )

    def _assert_cached_binding(self) -> None:
        """Cheap exact-object/cache check for repeated role-core assertions.

        Full nested source replay is deliberately confined to
        :meth:`assert_current`; otherwise rendering one immutable manifest
        would repeatedly hash the multi-megabyte sealed archive.  These cached
        IDs are private fields of the same retained issuer-owned objects and
        are still checked together with exact object identity.
        """

        if (
            self.request is not self._validated_refs[0]
            or self.prepared_session is not self._validated_refs[1]
            or self.request.route_identity is not self._validated_refs[2]
        ):
            _fail("production role manifest retained authority object was replaced")
        if (
            getattr(self.request, "_request_id", None),
            getattr(self.prepared_session, "_session_id", None),
            getattr(self.prepared_session.execution_spec, "_spec_id", None),
        ) != self._validated_ids:
            _fail("production role manifest retained cached identity changed")

    def assert_current(
        self,
        *,
        request: successor_v1.V075K7ParentOwnedSuccessorRequestV1 | None = None,
        prepared_session: preparation_v1.K7OuterAttemptPreparedBrokerSessionV1
        | None = None,
    ) -> None:
        """Replay the retained authority chain and optional exact object join."""

        if request is not None and request is not self._validated_refs[0]:
            _fail("production role manifest received a foreign request object")
        if prepared_session is not None and prepared_session is not self._validated_refs[1]:
            _fail("production role manifest received a foreign prepared session object")
        self._assert_cached_binding()
        self._assert_static_binding()
        current_ids = (
            self.request.request_id,
            self.prepared_session.session_id,
            self.prepared_session.execution_spec.spec_id,
        )
        if current_ids != self._validated_ids:
            _fail("production role manifest retained identity changed")
        if (
            self.request.route_identity.route_identity_id
            != self._validated_route_identity_id
            or self.worker_role.role_spec_id
            != _hash(
                V075_K7_PRODUCTION_ROLE_SPEC_V1_DOMAIN,
                self.worker_role._payload(),  # noqa: SLF001
            )
            or self.business_role.role_spec_id
            != _hash(
                V075_K7_PRODUCTION_ROLE_SPEC_V1_DOMAIN,
                self.business_role._payload(),  # noqa: SLF001
            )
        ):
            _fail("production role manifest role identity changed")
        if (
            _hash(V075_K7_PRODUCTION_ROLE_MANIFEST_V1_DOMAIN, self._payload())
            != self._manifest_id
        ):
            _fail("production role manifest changed after issuance")

    def assert_role_binding(
        self,
        role: K7ProductionBrokerRoleV1,
        *,
        request_id: str,
        prepared_session_id: str,
        broker_execution_spec_id: str,
        source_archive_sha256: str,
        interpreter_sha256: str,
        dispatch_sha256: str,
    ) -> K7ProductionRoleSpecV1:
        """Bind a worker/business core to all immutable launch identities."""

        # A static content ID is insufficient here: role binding replays the
        # complete request/source authority and the still-live PREPARED
        # guardian on every call.
        self.assert_current()
        try:
            exact_role = K7ProductionBrokerRoleV1(role)
        except (TypeError, ValueError) as error:
            raise V075K7ProductionRoleManifestV1Error(
                "production role core requested an unknown role"
            ) from error
        selected = self.worker_role if exact_role is K7ProductionBrokerRoleV1.WORKER else self.business_role
        if (
            _cid(request_id, "role-core request") != self.request_id
            or _cid(prepared_session_id, "role-core prepared session")
            != self.prepared_session_id
            or _cid(broker_execution_spec_id, "role-core broker execution spec")
            != self.broker_execution_spec_id
            or _sha256(source_archive_sha256, "role-core source archive")
            != self.source_archive_sha256
            or _sha256(interpreter_sha256, "role-core interpreter")
            != self.interpreter_sha256
            or _sha256(dispatch_sha256, "role-core dispatch")
            != selected.dispatch_sha256
            or selected.entry_source_present is not False
            or selected.entry_source_sha256 is not None
            or selected.entry_source_byte_count is not None
        ):
            _fail("production role core crossed its manifest binding")
        return selected

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_production_role_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "production_role_manifest_profile_id": _OFFICIAL_PROFILE.profile_id,
            "request_id": self.request_id,
            "route_identity_id": self._validated_route_identity_id,
            "prepared_broker_session_id": self.prepared_session_id,
            "broker_execution_spec_id": self.broker_execution_spec_id,
            "source_snapshot_id": self.source_snapshot_id,
            "source_archive_sha256": self.source_archive_sha256,
            "source_archive_byte_count": self.source_archive_byte_count,
            "transport_profile_id": self.transport_profile_id,
            "runtime_id": self.runtime_id,
            "interpreter_sha256": self.interpreter_sha256,
            "interpreter_byte_count": self.interpreter_byte_count,
            "role_order": list(ROLE_ORDER),
            "role_spec_ids": [
                self.worker_role.role_spec_id,
                self.business_role.role_spec_id,
            ],
            "worker_role": self.worker_role.to_document(),
            "business_role": self.business_role.to_document(),
            "frame_author_vector": [
                {"frame_role": frame, "author_role": author}
                for frame, author in FRAME_AUTHOR_VECTOR
            ],
            "business_request_ordinal": 0,
            "role_programs_derived_not_caller_supplied": True,
            "role_cgroups_derived_not_caller_supplied": True,
            "role_argv_environment_derived_not_caller_supplied": True,
            "role_fd_contract_derived_not_caller_supplied": True,
            "entry_sources_expected_but_not_yet_present": True,
            "dispatch_digests_are_not_entry_source_digests": True,
            "same_address_space_private_sentinels_are_security_capabilities": False,
            "construction_only": True,
            "formal_locks": _formal_locks(),
        }

    @property
    def manifest_id(self) -> str:
        self._assert_cached_binding()
        current = _hash(
            V075_K7_PRODUCTION_ROLE_MANIFEST_V1_DOMAIN, self._payload()
        )
        if current != self._manifest_id:
            _fail("production role manifest changed after issuance")
        return self._manifest_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "production_role_manifest_id": self.manifest_id}


def freeze_v075_k7_production_role_manifest_v1(
    *,
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
    prepared_session: preparation_v1.K7OuterAttemptPreparedBrokerSessionV1,
) -> K7ProductionRoleManifestV1:
    """Derive the exact two-role launch contract from retained authorities."""

    if (
        type(request) is not successor_v1.V075K7ParentOwnedSuccessorRequestV1
        or type(prepared_session)
        is not preparation_v1.K7OuterAttemptPreparedBrokerSessionV1
    ):
        _fail("production role-manifest factory requires exact request/session types")
    transport = request.profile.accounted_profile.transport_profile
    runtime = transport.runtime_document
    if type(runtime) is not dict:
        _fail("production role manifest lacks one exact interpreter document")
    worker = _freeze_role(
        K7ProductionBrokerRoleV1.WORKER,
        prepared_session.execution_spec.worker_identity,
    )
    business = _freeze_role(
        K7ProductionBrokerRoleV1.BUSINESS,
        prepared_session.execution_spec.business_identity,
    )
    return K7ProductionRoleManifestV1(
        _MANIFEST_ISSUER,
        request,
        prepared_session,
        worker,
        business,
        transport.source_snapshot_id,
        transport.source_archive_sha256,
        transport.source_archive_byte_count,
        transport.profile_id,
        transport.runtime_id,
        runtime.get("executable_sha256"),
        runtime.get("executable_byte_count"),
    )


def verify_v075_k7_production_role_manifest_bytes_v1(
    *,
    raw: bytes,
    expected: K7ProductionRoleManifestV1,
) -> K7ProductionRoleManifestV1:
    """Strictly replay canonical bytes against one retained live manifest."""

    if type(expected) is not K7ProductionRoleManifestV1:
        _fail("production role-manifest replay requires one exact expected manifest")
    expected.assert_current()
    if type(raw) is not bytes or not raw:
        _fail("production role-manifest bytes are empty or mistyped")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V075K7ProductionRoleManifestV1Error(
            "production role-manifest bytes are not canonical JSON"
        ) from error
    if type(document) is not dict or raw != expected.canonical_bytes:
        _fail("production role-manifest bytes crossed or changed")
    return expected


__all__ = (
    "BASE_ENVIRONMENT",
    "BUSINESS_DISPATCH_SHA256",
    "BUSINESS_ENTRY_MODULE",
    "BUSINESS_ENTRY_SOURCE_PATH",
    "BUSINESS_ENTRY_SYMBOL",
    "BUSINESS_INHERITED_FD_ROLES",
    "BUSINESS_RUNTIME_ENVIRONMENT",
    "BUSINESS_SEALED_INPUT_ROLES",
    "FORBIDDEN_EXEC_IMAGE_FD_ROLES",
    "FRAME_AUTHOR_VECTOR",
    "K7ProductionBrokerRoleV1",
    "K7ProductionRoleManifestProfileV1",
    "K7ProductionRoleManifestV1",
    "K7ProductionRoleSpecV1",
    "LOCAL_DOMAIN_TAGS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_CONSTANTS",
    "ROLE_ORDER",
    "SCHEMA_VERSION",
    "ENTRY_SOURCE_STATUS",
    "V075K7ProductionRoleManifestV1Error",
    "V075_K7_PRODUCTION_ROLE_MANIFEST_PROFILE_V1_DOMAIN",
    "V075_K7_PRODUCTION_ROLE_MANIFEST_V1_DOMAIN",
    "V075_K7_PRODUCTION_ROLE_SPEC_V1_DOMAIN",
    "WORKER_DISPATCH_SHA256",
    "WORKER_ENTRY_MODULE",
    "WORKER_ENTRY_SOURCE_PATH",
    "WORKER_ENTRY_SYMBOL",
    "WORKER_INHERITED_FD_ROLES",
    "WORKER_RUNTIME_ENVIRONMENT",
    "WORKER_SEALED_INPUT_ROLES",
    "freeze_v075_k7_production_role_manifest_v1",
    "official_v075_k7_production_role_manifest_profile_v1",
    "verify_v075_k7_production_role_manifest_bytes_v1",
)
