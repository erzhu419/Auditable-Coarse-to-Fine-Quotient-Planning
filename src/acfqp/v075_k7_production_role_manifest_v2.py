"""Executable source/role manifest for the K7 two-role broker successor.

Unlike the historical v1 template, this version requires both fresh-exec role
entries to be present in the exact retained source archive and binds the real
archive-loading bootstrap bytes.  It remains a construction authority: the
live v2 session, native launcher, sender credentials and accounting receipts
are deliberately outside this module.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import os
from pathlib import Path
import stat
import sys
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp import v075_k7_parent_owned_successor_ipc_v1 as successor_v1
from acfqp import v075_k7_production_role_bootstrap_v2 as bootstrap_v2
from acfqp import v075_k7_successor_portable_replay_v1 as replay_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_PRODUCTION_ROLE_LAUNCH_CONTEXT_V2_DOMAIN,
    V075_K7_PRODUCTION_ROLE_MANIFEST_PROFILE_V2_DOMAIN,
    V075_K7_PRODUCTION_ROLE_MANIFEST_V2_DOMAIN,
    V075_K7_PRODUCTION_ROLE_SPEC_V2_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.8"
PROFILE_KEY = "v075_k7_production_role_manifest_v2"

WORKER_ENTRY_SOURCE_PATH = (
    "acfqp/v075_k7_broker_worker_process_entry_v2.py"
)
BUSINESS_ENTRY_SOURCE_PATH = (
    "acfqp/v075_k7_broker_business_process_entry_v2.py"
)
COMMON_ENTRY_SOURCE_PATH = "acfqp/v075_k7_broker_process_entry_common_v2.py"
BOOTSTRAP_SOURCE_PATH = "acfqp/v075_k7_production_role_bootstrap_v2.py"
SUPPORT_SOURCE_PATHS = (COMMON_ENTRY_SOURCE_PATH, BOOTSTRAP_SOURCE_PATH)

ROLE_ORDER = bootstrap_v2.ROLE_ORDER
FRAME_AUTHOR_VECTOR = (
    (ipc_v1.K7OuterAttemptBrokerFrameRoleV1.WORKER_READY.value, "WORKER"),
    (ipc_v1.K7OuterAttemptBrokerFrameRoleV1.BUSINESS_REQUEST.value, "WORKER"),
    (ipc_v1.K7OuterAttemptBrokerFrameRoleV1.BUSINESS_RESULT.value, "BUSINESS"),
    (ipc_v1.K7OuterAttemptBrokerFrameRoleV1.PARENT_OUTPUT.value, "WORKER"),
    (ipc_v1.K7OuterAttemptBrokerFrameRoleV1.WORKER_EOF.value, "WORKER"),
)

LOCAL_DOMAIN_TAGS = frozenset(
    {
        V075_K7_PRODUCTION_ROLE_MANIFEST_PROFILE_V2_DOMAIN,
        V075_K7_PRODUCTION_ROLE_SPEC_V2_DOMAIN,
        V075_K7_PRODUCTION_ROLE_MANIFEST_V2_DOMAIN,
        V075_K7_PRODUCTION_ROLE_LAUNCH_CONTEXT_V2_DOMAIN,
    }
)
if not LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("production role-manifest v2 domains are unregistered")

_PROFILE_ISSUER = object()
_ROLE_ISSUER = object()
_MANIFEST_ISSUER = object()
_PUBLIC_REPLAY_ISSUER = object()
_CONTEXT_ISSUER = object()


class V075K7ProductionRoleManifestV2Error(ValueError):
    """The fresh source, role manifest or launch overlay is invalid."""


class K7ProductionBrokerRoleV2(str, Enum):
    WORKER = "WORKER"
    BUSINESS = "BUSINESS"


def _fail(message: str) -> NoReturn:
    raise V075K7ProductionRoleManifestV2Error(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        _fail("production role-manifest v2 used an undeclared domain")
    return content_id(domain, dict(payload))


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075K7ProductionRoleManifestV2Error(
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


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} bytes are empty or mistyped")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V075K7ProductionRoleManifestV2Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} must be one canonical JSON object")
    return value


def _path_identity(path: Path, *, directory: bool) -> tuple[int, ...]:
    try:
        resolved = path.resolve(strict=True)
        status = os.stat(resolved, follow_symlinks=False)
    except OSError as error:
        raise V075K7ProductionRoleManifestV2Error(
            "production role private/runtime path is unavailable"
        ) from error
    if not path.is_absolute() or resolved != path:
        _fail("production role paths must be absolute canonical paths")
    if directory != stat.S_ISDIR(status.st_mode):
        _fail("production role path has the wrong directory kind")
    if not directory and not stat.S_ISREG(status.st_mode):
        _fail("production role private key is not a regular file")
    return (
        status.st_dev,
        status.st_ino,
        stat.S_IMODE(status.st_mode),
        status.st_uid,
        status.st_gid,
        status.st_size,
    )


def _archive_source_entry(transport: Any, path: str) -> tuple[str, int]:
    rows = tuple(
        (digest, byte_count)
        for source_path, digest, byte_count in transport.source_entries
        if source_path == path
    )
    if len(rows) != 1:
        _fail(f"fresh sealed source archive lacks exact entry {path}")
    digest, byte_count = rows[0]
    _sha256(digest, f"{path} source")
    if type(byte_count) is not int or byte_count <= 0:
        _fail(f"{path} source byte count is invalid")
    return digest, byte_count


def _checked_live_source_entry(transport: Any, path: str) -> tuple[str, int]:
    digest, byte_count = _archive_source_entry(transport, path)
    live_path = Path(__file__).resolve().parents[1] / path
    try:
        raw = live_path.read_bytes()
    except OSError as error:
        raise V075K7ProductionRoleManifestV2Error(
            f"live source entry {path} cannot be read"
        ) from error
    if len(raw) != byte_count or hashlib.sha256(raw).hexdigest() != digest:
        _fail(f"live source entry {path} differs from the fresh archive")
    return digest, byte_count


def _source_row(path: str, digest: str, byte_count: int) -> dict[str, Any]:
    return {"path": path, "sha256": digest, "byte_count": byte_count}


def _formal_locks() -> dict[str, bool]:
    return {
        "v2_prepared_session_joined": False,
        "native_role_launcher_implemented": False,
        "role_specific_seccomp_implemented": False,
        "role_specific_landlock_implemented": False,
        "live_sender_credentials_verified": False,
        "complete_five_frame_protocol_verified": False,
        "shared_resource_receipts_issued": False,
        "counter_records_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "official_execution_allowed": False,
    }


ROLE_DOCUMENT_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "role",
        "ordinal",
        "cgroup_name",
        "entry_module",
        "entry_symbol",
        "entry_source_path",
        "bootstrap_sha256",
        "bootstrap_byte_count",
        "sealed_input_roles",
        "capability_fd_roles",
        "authored_frame_roles",
        "runtime_environment_keys",
        "entry_source_sha256",
        "entry_source_byte_count",
        "entry_source_present",
        "python_flags",
        "argv_value_source",
        "raw_private_locator_serialized",
        "formal_locks",
        "production_role_spec_id",
    }
)
MANIFEST_DOCUMENT_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "production_role_manifest_profile_id",
        "production_role_bootstrap_profile_id",
        "request_id",
        "route_identity_id",
        "source_snapshot_id",
        "source_archive_sha256",
        "source_archive_byte_count",
        "runtime_id",
        "interpreter_sha256",
        "interpreter_byte_count",
        "worker_role",
        "business_role",
        "support_source_entries",
        "repository_root_path_sha256",
        "private_root_inode_identity",
        "private_key_inode_identity",
        "private_locator_serialized",
        "fresh_archive_required",
        "historical_manifest_v1_relabelled",
        "live_session_binding_deferred_to_launch_context",
        "formal_locks",
        "production_role_manifest_id",
    }
)
LAUNCH_CONTEXT_DOCUMENT_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "production_role_manifest_id",
        "production_role_spec_id",
        "role",
        "request_id",
        "route_identity_id",
        "broker_execution_spec_id",
        "session_nonce",
        "source_snapshot_id",
        "source_archive_sha256",
        "runtime_id",
        "live_v2_session_authority_joined",
        "kernel_sender_authority_joined",
        "caller_minted_binding_is_launch_authority",
        "construction_only",
        "formal_locks",
        "production_role_launch_context_id",
    }
)


@dataclass(frozen=True, slots=True)
class K7ProductionRoleManifestProfileV2:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("production role-manifest v2 profile is issuer-owned")
        object.__setattr__(
            self,
            "_profile_id",
            _hash(
                V075_K7_PRODUCTION_ROLE_MANIFEST_PROFILE_V2_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_production_role_manifest_profile.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "bootstrap_profile_id": (
                bootstrap_v2
                .official_v075_k7_production_role_bootstrap_profile_v2()
                .profile_id
            ),
            "role_order": list(ROLE_ORDER),
            "cgroup_names": ["worker", "business"],
            "frame_author_vector": [
                {"frame_role": frame, "author_role": author}
                for frame, author in FRAME_AUTHOR_VECTOR
            ],
            "present_entry_source_required": True,
            "entry_and_dispatch_digests_distinct": True,
            "fresh_request_source_snapshot_required": True,
            "sealed_and_capability_fd_lanes_distinct": True,
            "caller_program_selection_allowed": False,
            "caller_fd_role_selection_allowed": False,
            "private_locator_serialized": False,
            "construction_only": True,
            "formal_locks": _formal_locks(),
        }

    @property
    def profile_id(self) -> str:
        if _hash(
            V075_K7_PRODUCTION_ROLE_MANIFEST_PROFILE_V2_DOMAIN,
            self._payload(),
        ) != self._profile_id:
            _fail("production role-manifest v2 profile changed")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "production_role_manifest_profile_id": self.profile_id,
        }


_OFFICIAL_PROFILE = K7ProductionRoleManifestProfileV2(_PROFILE_ISSUER)


def official_v075_k7_production_role_manifest_profile_v2(
) -> K7ProductionRoleManifestProfileV2:
    return _OFFICIAL_PROFILE


def _role_fixed_fields(role: K7ProductionBrokerRoleV2) -> dict[str, Any]:
    worker = role is K7ProductionBrokerRoleV2.WORKER
    return {
        "ordinal": 0 if worker else 1,
        "cgroup_name": "worker" if worker else "business",
        "entry_module": (
            bootstrap_v2.WORKER_ENTRY_MODULE
            if worker
            else bootstrap_v2.BUSINESS_ENTRY_MODULE
        ),
        "entry_symbol": (
            bootstrap_v2.WORKER_ENTRY_SYMBOL
            if worker
            else bootstrap_v2.BUSINESS_ENTRY_SYMBOL
        ),
        "entry_source_path": (
            WORKER_ENTRY_SOURCE_PATH if worker else BUSINESS_ENTRY_SOURCE_PATH
        ),
        "bootstrap_sha256": (
            bootstrap_v2.WORKER_BOOTSTRAP_SHA256
            if worker
            else bootstrap_v2.BUSINESS_BOOTSTRAP_SHA256
        ),
        "bootstrap_byte_count": len(
            bootstrap_v2.bootstrap_source_for_role_v2(role.value).encode("utf-8")
        ),
        "sealed_input_roles": (
            bootstrap_v2.WORKER_SEALED_INPUT_ROLES
            if worker
            else bootstrap_v2.BUSINESS_SEALED_INPUT_ROLES
        ),
        "capability_fd_roles": (
            bootstrap_v2.WORKER_CAPABILITY_ROLES
            if worker
            else bootstrap_v2.BUSINESS_CAPABILITY_ROLES
        ),
        "authored_frame_roles": tuple(
            frame for frame, author in FRAME_AUTHOR_VECTOR if author == role.value
        ),
        "runtime_environment_keys": tuple(
            sorted(
                {
                    *bootstrap_v2.BASE_ENVIRONMENT,
                    bootstrap_v2.ROLE_ENV,
                    bootstrap_v2.SEALED_FD_ENV,
                    bootstrap_v2.CHANNEL_FD_ENV,
                    bootstrap_v2.RESULT_FD_ENV,
                    *(
                        {bootstrap_v2.OUTPUT_DIRECTORY_FD_ENV}
                        if worker
                        else set()
                    ),
                }
            )
        ),
    }


@dataclass(frozen=True, slots=True)
class K7ProductionRoleSpecV2:
    _issuer: InitVar[object]
    role: K7ProductionBrokerRoleV2
    entry_source_sha256: str
    entry_source_byte_count: int
    _role_spec_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROLE_ISSUER:
            _fail("production role spec v2 is issuer-owned")
        try:
            exact_role = K7ProductionBrokerRoleV2(self.role)
        except (TypeError, ValueError) as error:
            raise V075K7ProductionRoleManifestV2Error(
                "production role spec v2 has an unknown role"
            ) from error
        object.__setattr__(self, "role", exact_role)
        _sha256(self.entry_source_sha256, "role entry source")
        if type(self.entry_source_byte_count) is not int or self.entry_source_byte_count <= 0:
            _fail("role entry source byte count is invalid")
        object.__setattr__(
            self,
            "_role_spec_id",
            _hash(V075_K7_PRODUCTION_ROLE_SPEC_V2_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        fields = _role_fixed_fields(self.role)
        return {
            "schema": "acfqp.v075_k7_production_role_spec.v2",
            "schema_version": SCHEMA_VERSION,
            "role": self.role.value,
            **{
                key: list(value) if isinstance(value, tuple) else value
                for key, value in fields.items()
            },
            "entry_source_sha256": self.entry_source_sha256,
            "entry_source_byte_count": self.entry_source_byte_count,
            "entry_source_present": True,
            "python_flags": ["-I", "-S", "-B", "-c"],
            "argv_value_source": "MANIFEST_DERIVED_RUNTIME_LOCATORS",
            "raw_private_locator_serialized": False,
            "formal_locks": _formal_locks(),
        }

    @property
    def role_spec_id(self) -> str:
        if _hash(V075_K7_PRODUCTION_ROLE_SPEC_V2_DOMAIN, self._payload()) != self._role_spec_id:
            _fail("production role spec v2 changed")
        return self._role_spec_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "production_role_spec_id": self.role_spec_id}


@dataclass(frozen=True, slots=True)
class K7ProductionRoleManifestV2:
    _issuer: InitVar[object]
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1 = field(
        repr=False, compare=False
    )
    worker_role: K7ProductionRoleSpecV2
    business_role: K7ProductionRoleSpecV2
    support_source_entries: tuple[tuple[str, str, int], ...]
    source_snapshot_id: str
    source_archive_sha256: str
    source_archive_byte_count: int
    runtime_id: str
    interpreter_sha256: str
    interpreter_byte_count: int
    repository_root_path_sha256: str
    private_root_identity: tuple[int, ...]
    private_key_identity: tuple[int, ...]
    _request_id: str = field(init=False, repr=False)
    _route_identity_id: str = field(init=False, repr=False)
    _frozen_payload_bytes: bytes = field(init=False, repr=False)
    _manifest_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _MANIFEST_ISSUER
            or type(self.request)
            is not successor_v1.V075K7ParentOwnedSuccessorRequestV1
            or type(self.worker_role) is not K7ProductionRoleSpecV2
            or type(self.business_role) is not K7ProductionRoleSpecV2
        ):
            _fail("production role manifest v2 is caller-minted")
        self.request._assert_current()  # noqa: SLF001
        if (
            self.worker_role.role is not K7ProductionBrokerRoleV2.WORKER
            or self.business_role.role is not K7ProductionBrokerRoleV2.BUSINESS
            or type(self.support_source_entries) is not tuple
            or tuple(row[0] for row in self.support_source_entries)
            != SUPPORT_SOURCE_PATHS
        ):
            _fail("production role manifest v2 role/support ordering changed")
        for path, digest, byte_count in self.support_source_entries:
            if type(path) is not str or not path:
                _fail("production role support source path is invalid")
            _sha256(digest, "support source")
            if type(byte_count) is not int or byte_count <= 0:
                _fail("support source byte count is invalid")
        for value, label in (
            (self.source_snapshot_id, "source snapshot"),
            (self.runtime_id, "runtime"),
        ):
            _cid(value, label)
        for value, label in (
            (self.source_archive_sha256, "source archive"),
            (self.interpreter_sha256, "interpreter"),
            (self.repository_root_path_sha256, "repository path"),
        ):
            _sha256(value, label)
        if (
            type(self.source_archive_byte_count) is not int
            or self.source_archive_byte_count <= 0
            or type(self.interpreter_byte_count) is not int
            or self.interpreter_byte_count <= 0
            or len(self.private_root_identity) != 6
            or len(self.private_key_identity) != 6
            or any(type(value) is not int or value < 0 for value in (*self.private_root_identity, *self.private_key_identity))
        ):
            _fail("production role manifest v2 sizes/path identities are invalid")
        object.__setattr__(self, "_request_id", self.request.request_id)
        object.__setattr__(
            self,
            "_route_identity_id",
            self.request.route_identity.route_identity_id,
        )
        raw = canonical_json_bytes(self._snapshot_payload())
        object.__setattr__(self, "_frozen_payload_bytes", raw)
        object.__setattr__(
            self,
            "_manifest_id",
            _hash(
                V075_K7_PRODUCTION_ROLE_MANIFEST_V2_DOMAIN,
                _canonical_document(raw, "role manifest v2 snapshot"),
            ),
        )

    def _snapshot_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_production_role_manifest.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "production_role_manifest_profile_id": _OFFICIAL_PROFILE.profile_id,
            "production_role_bootstrap_profile_id": (
                bootstrap_v2
                .official_v075_k7_production_role_bootstrap_profile_v2()
                .profile_id
            ),
            "request_id": self._request_id,
            "route_identity_id": self._route_identity_id,
            "source_snapshot_id": self.source_snapshot_id,
            "source_archive_sha256": self.source_archive_sha256,
            "source_archive_byte_count": self.source_archive_byte_count,
            "runtime_id": self.runtime_id,
            "interpreter_sha256": self.interpreter_sha256,
            "interpreter_byte_count": self.interpreter_byte_count,
            "worker_role": self.worker_role.to_document(),
            "business_role": self.business_role.to_document(),
            "support_source_entries": [
                _source_row(path, digest, byte_count)
                for path, digest, byte_count in self.support_source_entries
            ],
            "repository_root_path_sha256": self.repository_root_path_sha256,
            "private_root_inode_identity": list(self.private_root_identity),
            "private_key_inode_identity": list(self.private_key_identity),
            "private_locator_serialized": False,
            "fresh_archive_required": True,
            "historical_manifest_v1_relabelled": False,
            "live_session_binding_deferred_to_launch_context": True,
            "formal_locks": _formal_locks(),
        }

    def _payload(self) -> dict[str, Any]:
        return _canonical_document(
            self._frozen_payload_bytes,
            "frozen role manifest v2 payload",
        )

    @property
    def request_id(self) -> str:
        return self._request_id

    @property
    def route_identity_id(self) -> str:
        return self._route_identity_id

    @property
    def manifest_id(self) -> str:
        if _hash(V075_K7_PRODUCTION_ROLE_MANIFEST_V2_DOMAIN, self._payload()) != self._manifest_id:
            _fail("production role manifest v2 changed")
        return self._manifest_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "production_role_manifest_id": self.manifest_id}

    def role_spec(self, role: K7ProductionBrokerRoleV2 | str) -> K7ProductionRoleSpecV2:
        try:
            exact = K7ProductionBrokerRoleV2(role)
        except (TypeError, ValueError) as error:
            raise V075K7ProductionRoleManifestV2Error(
                "production role manifest v2 received an unknown role"
            ) from error
        return self.worker_role if exact is K7ProductionBrokerRoleV2.WORKER else self.business_role

    def assert_current(self) -> None:
        try:
            self.request._assert_current()  # noqa: SLF001
        except Exception as error:
            raise V075K7ProductionRoleManifestV2Error(
                "production role manifest v2 request/source authority is stale"
            ) from error
        transport = self.request.profile.accounted_profile.transport_profile
        if (
            self.request.request_id != self._request_id
            or self.request.route_identity.route_identity_id != self._route_identity_id
            or transport.source_snapshot_id != self.source_snapshot_id
            or transport.source_archive_sha256 != self.source_archive_sha256
            or transport.source_archive_byte_count != self.source_archive_byte_count
            or transport.runtime_id != self.runtime_id
        ):
            _fail("production role manifest v2 crossed its retained request")
        expected = {
            path: _checked_live_source_entry(transport, path)
            for path in (
                WORKER_ENTRY_SOURCE_PATH,
                BUSINESS_ENTRY_SOURCE_PATH,
                *SUPPORT_SOURCE_PATHS,
            )
        }
        if (
            expected[WORKER_ENTRY_SOURCE_PATH]
            != (self.worker_role.entry_source_sha256, self.worker_role.entry_source_byte_count)
            or expected[BUSINESS_ENTRY_SOURCE_PATH]
            != (self.business_role.entry_source_sha256, self.business_role.entry_source_byte_count)
            or tuple(
                (path, *expected[path]) for path in SUPPORT_SOURCE_PATHS
            )
            != self.support_source_entries
        ):
            _fail("production role manifest v2 source binding changed")
        _ = self.manifest_id


def freeze_v075_k7_production_role_manifest_v2(
    *,
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
    repository_root: Path,
    signer_private_root: Path,
    signer_private_key_path: Path,
) -> K7ProductionRoleManifestV2:
    if (
        type(request) is not successor_v1.V075K7ParentOwnedSuccessorRequestV1
        or not isinstance(repository_root, Path)
        or not isinstance(signer_private_root, Path)
        or not isinstance(signer_private_key_path, Path)
    ):
        _fail("production role manifest v2 received mistyped authorities or paths")
    request._assert_current()  # noqa: SLF001
    repository_identity = _path_identity(repository_root, directory=True)
    del repository_identity  # only the canonical path digest is public
    private_root_identity = _path_identity(signer_private_root, directory=True)
    private_key_identity = _path_identity(signer_private_key_path, directory=False)
    transport = request.profile.accounted_profile.transport_profile
    worker_digest, worker_size = _checked_live_source_entry(transport, WORKER_ENTRY_SOURCE_PATH)
    business_digest, business_size = _checked_live_source_entry(
        transport, BUSINESS_ENTRY_SOURCE_PATH
    )
    support = tuple(
        (path, *_checked_live_source_entry(transport, path)) for path in SUPPORT_SOURCE_PATHS
    )
    runtime = transport.runtime_document
    if type(runtime) is not dict:
        _fail("production role manifest v2 lacks a frozen runtime document")
    try:
        interpreter = Path(sys.executable).resolve(strict=True).read_bytes()
    except OSError as error:
        raise V075K7ProductionRoleManifestV2Error(
            "production interpreter cannot be read"
        ) from error
    if (
        hashlib.sha256(interpreter).hexdigest() != runtime.get("executable_sha256")
        or len(interpreter) != runtime.get("executable_byte_count")
    ):
        _fail("live interpreter differs from the request runtime")
    return K7ProductionRoleManifestV2(
        _MANIFEST_ISSUER,
        request,
        K7ProductionRoleSpecV2(
            _ROLE_ISSUER,
            K7ProductionBrokerRoleV2.WORKER,
            worker_digest,
            worker_size,
        ),
        K7ProductionRoleSpecV2(
            _ROLE_ISSUER,
            K7ProductionBrokerRoleV2.BUSINESS,
            business_digest,
            business_size,
        ),
        support,
        transport.source_snapshot_id,
        transport.source_archive_sha256,
        transport.source_archive_byte_count,
        transport.runtime_id,
        runtime["executable_sha256"],
        runtime["executable_byte_count"],
        hashlib.sha256(os.fsencode(repository_root)).hexdigest(),
        private_root_identity,
        private_key_identity,
    )


@dataclass(frozen=True, slots=True)
class K7ProductionRoleManifestPublicReplayV2:
    _issuer: InitVar[object]
    _raw: bytes = field(repr=False)
    request_replay: replay_v1.V075K7SuccessorPortableRequestReplayV1 = field(
        repr=False, compare=False
    )
    _manifest_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PUBLIC_REPLAY_ISSUER
            or type(self._raw) is not bytes
            or type(self.request_replay)
            is not replay_v1.V075K7SuccessorPortableRequestReplayV1
        ):
            _fail("production role manifest public replay is caller-minted")
        document = _canonical_document(self._raw, "retained public role manifest v2")
        object.__setattr__(
            self,
            "_manifest_id",
            _cid(document["production_role_manifest_id"], "role manifest"),
        )

    @property
    def document(self) -> dict[str, Any]:
        return _canonical_document(
            self._raw, "retained public role manifest v2"
        )

    @property
    def manifest_id(self) -> str:
        document = self.document
        payload = dict(document)
        payload.pop("production_role_manifest_id")
        if (
            _hash(V075_K7_PRODUCTION_ROLE_MANIFEST_V2_DOMAIN, payload)
            != self._manifest_id
        ):
            _fail("retained public role manifest v2 changed")
        return self._manifest_id

    def role_document(self, role: K7ProductionBrokerRoleV2 | str) -> Mapping[str, Any]:
        exact = K7ProductionBrokerRoleV2(role)
        key = "worker_role" if exact is K7ProductionBrokerRoleV2.WORKER else "business_role"
        value = self.document[key]
        if type(value) is not dict:
            _fail("public role document changed")
        return MappingProxyType(dict(value))


def _verify_role_document(
    *, document: Any, role: K7ProductionBrokerRoleV2, transport: Any
) -> None:
    if type(document) is not dict or set(document) != ROLE_DOCUMENT_KEYS:
        _fail("public role spec is not an object")
    role_id = _cid(document.get("production_role_spec_id"), "role spec")
    payload = dict(document)
    payload.pop("production_role_spec_id", None)
    if _hash(V075_K7_PRODUCTION_ROLE_SPEC_V2_DOMAIN, payload) != role_id:
        _fail("public role spec content ID is invalid")
    fixed = _role_fixed_fields(role)
    for key, expected in fixed.items():
        actual = document.get(key)
        if isinstance(expected, tuple):
            expected = list(expected)
        if actual != expected:
            _fail(f"public {role.value.lower()} role field {key} changed")
    if (
        document.get("schema") != "acfqp.v075_k7_production_role_spec.v2"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("role") != role.value
        or document.get("entry_source_present") is not True
        or document.get("python_flags") != ["-I", "-S", "-B", "-c"]
        or document.get("argv_value_source")
        != "MANIFEST_DERIVED_RUNTIME_LOCATORS"
        or document.get("raw_private_locator_serialized") is not False
        or document.get("formal_locks") != _formal_locks()
    ):
        _fail("public role spec fixed semantics changed")
    path = fixed["entry_source_path"]
    if _archive_source_entry(transport, path) != (
        document.get("entry_source_sha256"),
        document.get("entry_source_byte_count"),
    ):
        _fail("public role spec crossed its archive source entry")


def verify_v075_k7_production_role_manifest_public_bytes_v2(
    *,
    raw: bytes,
    expected_request_replay: replay_v1.V075K7SuccessorPortableRequestReplayV1,
) -> K7ProductionRoleManifestPublicReplayV2:
    if type(expected_request_replay) is not replay_v1.V075K7SuccessorPortableRequestReplayV1:
        _fail("public role-manifest replay requires the exact request replay")
    expected_request_replay.profile_closure._assert_current()  # noqa: SLF001
    document = _canonical_document(raw, "public production role manifest v2")
    if set(document) != MANIFEST_DOCUMENT_KEYS:
        _fail("public role manifest v2 fields are incomplete or unknown")
    manifest_id = _cid(document.get("production_role_manifest_id"), "role manifest")
    payload = dict(document)
    payload.pop("production_role_manifest_id", None)
    if _hash(V075_K7_PRODUCTION_ROLE_MANIFEST_V2_DOMAIN, payload) != manifest_id:
        _fail("public role manifest v2 content ID is invalid")
    request = expected_request_replay.request
    transport = expected_request_replay.profile_closure.transport_profile
    if (
        document.get("schema") != "acfqp.v075_k7_production_role_manifest.v2"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("proposed_contract_version") != PROPOSED_CONTRACT_VERSION
        or document.get("profile_key") != PROFILE_KEY
        or document.get("production_role_manifest_profile_id") != _OFFICIAL_PROFILE.profile_id
        or document.get("production_role_bootstrap_profile_id")
        != bootstrap_v2.official_v075_k7_production_role_bootstrap_profile_v2().profile_id
        or document.get("request_id") != request.request_id
        or document.get("route_identity_id") != request.route_identity.route_identity_id
        or document.get("source_snapshot_id") != transport.source_snapshot_id
        or document.get("source_archive_sha256") != transport.source_archive_sha256
        or document.get("source_archive_byte_count") != transport.source_archive_byte_count
        or document.get("runtime_id") != transport.runtime_id
        or document.get("formal_locks") != _formal_locks()
        or document.get("private_locator_serialized") is not False
        or document.get("fresh_archive_required") is not True
        or document.get("historical_manifest_v1_relabelled") is not False
        or document.get("live_session_binding_deferred_to_launch_context") is not True
    ):
        _fail("public role manifest v2 crossed its fresh request/source")
    runtime = transport.runtime_document
    if (
        document.get("interpreter_sha256") != runtime.get("executable_sha256")
        or document.get("interpreter_byte_count") != runtime.get("executable_byte_count")
    ):
        _fail("public role manifest v2 crossed its interpreter")
    _verify_role_document(
        document=document.get("worker_role"),
        role=K7ProductionBrokerRoleV2.WORKER,
        transport=transport,
    )
    _verify_role_document(
        document=document.get("business_role"),
        role=K7ProductionBrokerRoleV2.BUSINESS,
        transport=transport,
    )
    expected_support = [
        _source_row(path, *_archive_source_entry(transport, path))
        for path in SUPPORT_SOURCE_PATHS
    ]
    if document.get("support_source_entries") != expected_support:
        _fail("public role manifest v2 support source entries changed")
    for key in (
        "repository_root_path_sha256",
    ):
        _sha256(document.get(key), key)
    for key in ("private_root_inode_identity", "private_key_inode_identity"):
        identity = document.get(key)
        if type(identity) is not list or len(identity) != 6 or any(type(value) is not int or value < 0 for value in identity):
            _fail("public role manifest v2 path identity is malformed")
    return K7ProductionRoleManifestPublicReplayV2(
        _PUBLIC_REPLAY_ISSUER,
        raw,
        expected_request_replay,
    )


@dataclass(frozen=True, slots=True)
class K7ProductionRoleLaunchContextV2:
    _issuer: InitVar[object]
    manifest: K7ProductionRoleManifestV2 = field(repr=False, compare=False)
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1 = field(repr=False)
    role: K7ProductionBrokerRoleV2
    _context_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CONTEXT_ISSUER
            or type(self.manifest) is not K7ProductionRoleManifestV2
            or type(self.binding) is not ipc_v1.K7OuterAttemptBrokerIPCBindingV1
        ):
            _fail("production role launch context v2 is caller-minted")
        self.manifest.assert_current()
        exact = K7ProductionBrokerRoleV2(self.role)
        object.__setattr__(self, "role", exact)
        if (
            self.binding.request_id != self.manifest.request_id
            or self.binding.route_identity_id != self.manifest.route_identity_id
        ):
            _fail("production role launch context crossed request/route binding")
        object.__setattr__(
            self,
            "_context_id",
            _hash(V075_K7_PRODUCTION_ROLE_LAUNCH_CONTEXT_V2_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        role_spec = self.manifest.role_spec(self.role)
        return {
            "schema": "acfqp.v075_k7_production_role_launch_context.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "production_role_manifest_id": self.manifest.manifest_id,
            "production_role_spec_id": role_spec.role_spec_id,
            "role": self.role.value,
            **self.binding.to_document(),
            "source_snapshot_id": self.manifest.source_snapshot_id,
            "source_archive_sha256": self.manifest.source_archive_sha256,
            "runtime_id": self.manifest.runtime_id,
            "live_v2_session_authority_joined": False,
            "kernel_sender_authority_joined": False,
            "caller_minted_binding_is_launch_authority": False,
            "construction_only": True,
            "formal_locks": _formal_locks(),
        }

    @property
    def context_id(self) -> str:
        if _hash(V075_K7_PRODUCTION_ROLE_LAUNCH_CONTEXT_V2_DOMAIN, self._payload()) != self._context_id:
            _fail("production role launch context v2 changed")
        return self._context_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "production_role_launch_context_id": self.context_id}


def freeze_v075_k7_production_role_launch_context_v2(
    *,
    manifest: K7ProductionRoleManifestV2,
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1,
    role: K7ProductionBrokerRoleV2,
) -> K7ProductionRoleLaunchContextV2:
    return K7ProductionRoleLaunchContextV2(
        _CONTEXT_ISSUER, manifest, binding, role
    )


def verify_v075_k7_production_role_launch_context_public_bytes_v2(
    *,
    raw: bytes,
    expected_manifest: K7ProductionRoleManifestPublicReplayV2,
    expected_role: K7ProductionBrokerRoleV2,
) -> ipc_v1.K7OuterAttemptBrokerIPCBindingV1:
    if type(expected_manifest) is not K7ProductionRoleManifestPublicReplayV2:
        _fail("role launch-context replay requires one public manifest replay")
    role = K7ProductionBrokerRoleV2(expected_role)
    document = _canonical_document(raw, "public role launch context v2")
    if set(document) != LAUNCH_CONTEXT_DOCUMENT_KEYS:
        _fail("public role launch context v2 fields are incomplete or unknown")
    context_id = _cid(
        document.get("production_role_launch_context_id"), "role launch context"
    )
    payload = dict(document)
    payload.pop("production_role_launch_context_id", None)
    if _hash(V075_K7_PRODUCTION_ROLE_LAUNCH_CONTEXT_V2_DOMAIN, payload) != context_id:
        _fail("public role launch context v2 content ID is invalid")
    role_document = expected_manifest.role_document(role)
    request = expected_manifest.request_replay.request
    source = expected_manifest.document
    if (
        document.get("schema") != "acfqp.v075_k7_production_role_launch_context.v2"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("proposed_contract_version") != PROPOSED_CONTRACT_VERSION
        or document.get("profile_key") != PROFILE_KEY
        or document.get("production_role_manifest_id") != expected_manifest.manifest_id
        or document.get("production_role_spec_id") != role_document.get("production_role_spec_id")
        or document.get("role") != role.value
        or document.get("request_id") != request.request_id
        or document.get("route_identity_id") != request.route_identity.route_identity_id
        or document.get("source_snapshot_id") != source.get("source_snapshot_id")
        or document.get("source_archive_sha256") != source.get("source_archive_sha256")
        or document.get("runtime_id") != source.get("runtime_id")
        or document.get("live_v2_session_authority_joined") is not False
        or document.get("kernel_sender_authority_joined") is not False
        or document.get("caller_minted_binding_is_launch_authority") is not False
        or document.get("construction_only") is not True
        or document.get("formal_locks") != _formal_locks()
    ):
        _fail("public role launch context v2 crossed its manifest/request")
    binding = ipc_v1.K7OuterAttemptBrokerIPCBindingV1(
        document.get("request_id"),
        document.get("route_identity_id"),
        document.get("broker_execution_spec_id"),
        document.get("session_nonce"),
    )
    if any(
        document.get(key) != value
        for key, value in binding.to_document().items()
    ):
        _fail("public role launch context v2 binding fields changed")
    return binding


__all__ = (
    "BOOTSTRAP_SOURCE_PATH",
    "BUSINESS_ENTRY_SOURCE_PATH",
    "COMMON_ENTRY_SOURCE_PATH",
    "FRAME_AUTHOR_VECTOR",
    "K7ProductionBrokerRoleV2",
    "K7ProductionRoleLaunchContextV2",
    "K7ProductionRoleManifestProfileV2",
    "K7ProductionRoleManifestPublicReplayV2",
    "K7ProductionRoleManifestV2",
    "K7ProductionRoleSpecV2",
    "LOCAL_DOMAIN_TAGS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "ROLE_ORDER",
    "SCHEMA_VERSION",
    "SUPPORT_SOURCE_PATHS",
    "V075K7ProductionRoleManifestV2Error",
    "WORKER_ENTRY_SOURCE_PATH",
    "freeze_v075_k7_production_role_launch_context_v2",
    "freeze_v075_k7_production_role_manifest_v2",
    "official_v075_k7_production_role_manifest_profile_v2",
    "verify_v075_k7_production_role_launch_context_public_bytes_v2",
    "verify_v075_k7_production_role_manifest_public_bytes_v2",
)
