"""One-shot launch records for the K7 production broker roles.

This construction-only authority joins one exact v2 role manifest and launch
context to its issuer-owned resource-session capability bundle, immutable
public inputs, role-private lifecycle-secret capability, and the current
interpreter image.  It fixes the complete archive bootstrap ``argv`` and
environment but does not launch a process or issue an operational receipt.

The two content domains remain local so this slice can be merged without
editing the central registry concurrently.  An integrating change must
register the exact tags in :mod:`acfqp.phase3e_ids` before promotion.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import fcntl
import hashlib
import os
from pathlib import Path
import socket
import stat
import sys
from threading import Lock
from types import MappingProxyType
from typing import Any, Mapping, NoReturn, TypeAlias

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime_v1
from acfqp import v075_k7_broker_resource_session_v2 as resource_v2
from acfqp import v075_k7_production_role_bootstrap_v2 as bootstrap_v2
from acfqp import v075_k7_production_role_manifest_v2 as manifest_v2
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_PRODUCTION_ROLE_LAUNCH_AUTHORITY_PROFILE_V2_DOMAIN,
    V075_K7_PRODUCTION_ROLE_LAUNCH_AUTHORITY_V2_DOMAIN,
    canonical_json_bytes,
    content_id,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.12"
PROFILE_KEY = "v075_k7_production_role_launch_authority_v2"

PROFILE_DOMAIN = V075_K7_PRODUCTION_ROLE_LAUNCH_AUTHORITY_PROFILE_V2_DOMAIN
AUTHORITY_DOMAIN = V075_K7_PRODUCTION_ROLE_LAUNCH_AUTHORITY_V2_DOMAIN
REQUESTED_PHASE3E_DOMAIN_TAGS = (PROFILE_DOMAIN, AUTHORITY_DOMAIN)
if not frozenset(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS:
    raise RuntimeError("production role launch-authority domains are unregistered")

MAX_PUBLIC_INPUT_BYTES = runtime_v1.MAX_SEALED_INPUT_BYTES
MAX_INTERPRETER_BYTES = runtime_v1.MAX_EXECUTABLE_BYTES

K7ProductionRoleNativeLaunchRecordV2: TypeAlias = tuple[
    int,
    tuple[int, ...],
    tuple[int, ...],
    tuple[str, ...],
    tuple[tuple[str, str], ...],
]

_PROFILE_ISSUER = object()
_AUTHORITY_ISSUER = object()
_ISSUANCE_LOCK = Lock()
_ISSUED_BINDINGS: set[tuple[int, str, str]] = set()


class V075K7ProductionRoleLaunchAuthorityV2Error(RuntimeError):
    """A launch authority input, descriptor, or retained identity is invalid."""


def _fail(message: str) -> NoReturn:
    raise V075K7ProductionRoleLaunchAuthorityV2Error(message)


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in REQUESTED_PHASE3E_DOMAIN_TAGS:
        _fail("production role launch authority used an undeclared domain")
    return content_id(domain, dict(payload))


def _formal_locks() -> dict[str, bool]:
    return {
        "native_role_launcher_executed": False,
        "role_sandbox_installed": False,
        "role_cgroup_joined_from_birth": False,
        "live_sender_credentials_verified": False,
        "complete_five_frame_protocol_verified": False,
        "post_reap_supervisor_envelope_issued": False,
        "shared_resource_receipts_issued": False,
        "counter_records_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "official_execution_allowed": False,
    }


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _descriptor_identity(descriptor: int) -> tuple[int, ...]:
    try:
        status = os.fstat(descriptor)
    except OSError as error:
        raise V075K7ProductionRoleLaunchAuthorityV2Error(
            "launch descriptor is closed or unavailable"
        ) from error
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_uid,
        status.st_gid,
        status.st_rdev,
        status.st_size,
    )


def _identity_document(identity: tuple[int, ...]) -> dict[str, int]:
    return {
        "device": identity[0],
        "inode": identity[1],
        "mode": identity[2],
        "owner_uid": identity[3],
        "owner_gid": identity[4],
        "rdev": identity[5],
        "byte_count": identity[6],
    }


def _fd_flags(descriptor: int) -> int:
    try:
        return fcntl.fcntl(descriptor, fcntl.F_GETFL)
    except OSError as error:
        raise V075K7ProductionRoleLaunchAuthorityV2Error(
            "launch descriptor flags are unavailable"
        ) from error


def _is_cloexec(descriptor: int) -> bool:
    try:
        return bool(fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC)
    except OSError as error:
        raise V075K7ProductionRoleLaunchAuthorityV2Error(
            "launch descriptor inheritance state is unavailable"
        ) from error


def _read_exact_descriptor(
    descriptor: int,
    *,
    byte_cap: int,
    label: str,
) -> tuple[bytes, tuple[int, ...]]:
    identity = _descriptor_identity(descriptor)
    size = identity[6]
    if not stat.S_ISREG(identity[2]) or not 0 < size <= byte_cap:
        _fail(f"{label} is not one bounded nonempty regular descriptor")
    chunks: list[bytes] = []
    offset = 0
    while offset < size:
        try:
            chunk = os.pread(descriptor, min(1024 * 1024, size - offset), offset)
        except OSError as error:
            raise V075K7ProductionRoleLaunchAuthorityV2Error(
                f"{label} descriptor read failed"
            ) from error
        if not chunk:
            _fail(f"{label} descriptor ended before its frozen size")
        chunks.append(chunk)
        offset += len(chunk)
    raw = b"".join(chunks)
    if _descriptor_identity(descriptor) != identity:
        _fail(f"{label} descriptor identity changed while read")
    return raw, identity


def _inspect_interpreter(
    descriptor: int,
    *,
    expected_identity: tuple[int, ...] | None,
    expected_sha256: str,
    expected_byte_count: int,
) -> tuple[int, ...]:
    if type(descriptor) is not int or descriptor < 3:
        _fail("interpreter FD is invalid or uses a standard descriptor")
    raw, identity = _read_exact_descriptor(
        descriptor,
        byte_cap=MAX_INTERPRETER_BYTES,
        label="interpreter",
    )
    live_fd = -1
    try:
        live_fd = os.open(
            Path(sys.executable).resolve(strict=True),
            os.O_RDONLY | os.O_CLOEXEC,
        )
        live_identity = _descriptor_identity(live_fd)
    finally:
        if live_fd >= 0:
            os.close(live_fd)
    if (
        identity != live_identity
        or (expected_identity is not None and identity != expected_identity)
        or identity[6] != expected_byte_count
        or _sha256(raw) != expected_sha256
        or _fd_flags(descriptor) & os.O_ACCMODE != os.O_RDONLY
        or _fd_flags(descriptor) & getattr(os, "O_PATH", 0)
        or not stat.S_IMODE(identity[2]) & 0o111
        or not _is_cloexec(descriptor)
        or os.get_inheritable(descriptor)
    ):
        _fail("interpreter FD identity, digest, access, or inheritance changed")
    return identity


def _inspect_sealed_input(
    descriptor: int,
    *,
    label: str,
    expected_identity: tuple[int, ...] | None,
    expected_raw: bytes | None,
) -> tuple[tuple[int, ...], str | None, int]:
    if type(descriptor) is not int or descriptor < 3:
        _fail(f"{label} FD is invalid or uses a standard descriptor")
    identity = _descriptor_identity(descriptor)
    if expected_raw is None:
        if (
            not stat.S_ISREG(identity[2])
            or not 0 < identity[6] <= MAX_PUBLIC_INPUT_BYTES
        ):
            _fail(f"{label} is not one bounded nonempty sealed input")
        digest = None
    else:
        raw, replayed_identity = _read_exact_descriptor(
            descriptor,
            byte_cap=MAX_PUBLIC_INPUT_BYTES,
            label=label,
        )
        if raw != expected_raw:
            _fail(f"{label} content differs from its exact public authority")
        identity = replayed_identity
        digest = _sha256(raw)
    try:
        seals = fcntl.fcntl(descriptor, runtime_v1.F_GET_SEALS)
    except OSError as error:
        raise V075K7ProductionRoleLaunchAuthorityV2Error(
            f"{label} lacks inspectable immutable seals"
        ) from error
    if (
        (expected_identity is not None and identity != expected_identity)
        or _fd_flags(descriptor) & os.O_ACCMODE != os.O_RDONLY
        or _fd_flags(descriptor) & (os.O_APPEND | getattr(os, "O_PATH", 0))
        or seals != runtime_v1.REQUIRED_MEMFD_SEALS
        or not _is_cloexec(descriptor)
        or os.get_inheritable(descriptor)
    ):
        _fail(f"{label} identity, read-only access, seals, or inheritance changed")
    return identity, digest, seals


def _socket_is_empty(descriptor: int) -> None:
    duplicate = -1
    endpoint: socket.socket | None = None
    try:
        duplicate = fcntl.fcntl(descriptor, fcntl.F_DUPFD_CLOEXEC, 3)
        endpoint = socket.socket(fileno=duplicate)
        duplicate = -1
        endpoint.getpeername()
        if (
            endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_DOMAIN)
            != socket.AF_UNIX
            or endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
            != socket.SOCK_SEQPACKET
            or endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED) != 0
            or endpoint.getblocking() is not True
        ):
            _fail("role broker channel lost its fixed child-end semantics")
        try:
            queued = endpoint.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT)
        except BlockingIOError:
            queued = None
        if queued is not None:
            _fail("role broker channel is closed or already carries a packet")
    except OSError as error:
        raise V075K7ProductionRoleLaunchAuthorityV2Error(
            "role broker channel cannot be inspected"
        ) from error
    finally:
        if endpoint is not None:
            endpoint.close()
        elif duplicate >= 0:
            os.close(duplicate)


def _inspect_capabilities(
    bundle: resource_v2.K7BrokerRoleCapabilityBundleV2,
    *,
    expected_rows: tuple[tuple[str, tuple[int, ...], str, int | None], ...]
    | None,
) -> tuple[
    tuple[int, ...],
    tuple[tuple[str, tuple[int, ...], str, int | None], ...],
]:
    roles = bundle.descriptor_roles
    expected_roles = (
        bootstrap_v2.WORKER_CAPABILITY_ROLES
        if bundle.role is manifest_v2.K7ProductionBrokerRoleV2.WORKER
        else bootstrap_v2.BUSINESS_CAPABILITY_ROLES
    )
    if roles != expected_roles:
        _fail("resource capability roles differ from the fixed bootstrap")
    descriptors = tuple(bundle.descriptor(role) for role in roles)
    if len(set(descriptors)) != len(descriptors) or any(fd < 3 for fd in descriptors):
        _fail("resource capability FD lanes overlap or use standard descriptors")
    rows: list[tuple[str, tuple[int, ...], str, int | None]] = []
    for role, descriptor in zip(roles, descriptors):
        identity = _descriptor_identity(descriptor)
        if not _is_cloexec(descriptor) or os.get_inheritable(descriptor):
            _fail("resource capability FD is not parent-side CLOEXEC")
        if role == "BROKER_CHANNEL":
            _socket_is_empty(descriptor)
            semantics = "BLOCKING_AF_UNIX_SOCK_SEQPACKET_CHILD_END"
            seals: int | None = None
        elif role in {"BUSINESS_RESULT_READONLY", "BUSINESS_RESULT_WRITABLE"}:
            try:
                seals = fcntl.fcntl(descriptor, runtime_v1.F_GET_SEALS)
            except OSError as error:
                raise V075K7ProductionRoleLaunchAuthorityV2Error(
                    "business-result capability is not a sealable memfd"
                ) from error
            expected_access = (
                os.O_RDONLY
                if role == "BUSINESS_RESULT_READONLY"
                else os.O_RDWR
            )
            if (
                not stat.S_ISREG(identity[2])
                or identity[6] != 0
                or _fd_flags(descriptor) & os.O_ACCMODE != expected_access
                or seals != 0
            ):
                _fail("business-result capability access or seal state changed")
            semantics = (
                "EMPTY_UNSEALED_READONLY_MEMFD"
                if expected_access == os.O_RDONLY
                else "EMPTY_UNSEALED_READWRITE_MEMFD"
            )
        elif role == "OUTPUT_DIRECTORY":
            try:
                entries = os.listdir(descriptor)
            except OSError as error:
                raise V075K7ProductionRoleLaunchAuthorityV2Error(
                    "worker output-directory capability cannot be inspected"
                ) from error
            if (
                not stat.S_ISDIR(identity[2])
                or entries
                or _fd_flags(descriptor) & os.O_ACCMODE != os.O_RDONLY
                or _fd_flags(descriptor) & getattr(os, "O_PATH", 0)
            ):
                _fail("worker output-directory capability changed")
            semantics = "EMPTY_READONLY_DIRECTORY_VIEW"
            seals = None
        else:  # pragma: no cover - exact bundle rejects this first
            _fail("resource capability role is unknown")
        rows.append((role, identity, semantics, seals))
    result = tuple(rows)
    if expected_rows is not None and result != expected_rows:
        _fail("resource capability identity or kernel semantics changed")
    return descriptors, result


def _path_identity(path: Path, *, directory: bool) -> tuple[int, ...]:
    try:
        resolved = path.resolve(strict=True)
        status = os.stat(resolved, follow_symlinks=False)
    except OSError as error:
        raise V075K7ProductionRoleLaunchAuthorityV2Error(
            "production launch path is unavailable"
        ) from error
    if not path.is_absolute() or path != resolved:
        _fail("production launch paths must be absolute and canonical")
    if directory != stat.S_ISDIR(status.st_mode):
        _fail("production launch path has the wrong kind")
    if not directory and not stat.S_ISREG(status.st_mode):
        _fail("production launch key path is not a regular file")
    return (
        status.st_dev,
        status.st_ino,
        stat.S_IMODE(status.st_mode),
        status.st_uid,
        status.st_gid,
        status.st_size,
    )


def derive_v075_k7_production_role_public_input_bytes_v2(
    *,
    manifest: manifest_v2.K7ProductionRoleManifestV2,
    launch_context: manifest_v2.K7ProductionRoleLaunchContextV2,
) -> Mapping[str, bytes]:
    """Derive the seven public payloads in their frozen bootstrap role order."""

    if (
        type(manifest) is not manifest_v2.K7ProductionRoleManifestV2
        or type(launch_context)
        is not manifest_v2.K7ProductionRoleLaunchContextV2
        or launch_context.manifest is not manifest
    ):
        _fail("public role input derivation crossed its manifest/context")
    manifest.assert_current()
    _ = launch_context.context_id
    request = manifest.request
    accounted = request.profile.accounted_profile
    transport = accounted.transport_profile
    lifecycle = accounted.private_replay_profile
    rows = {
        "SOURCE_ARCHIVE": transport._archive_bytes,  # noqa: SLF001
        "TRANSPORT_PROFILE": canonical_json_bytes(transport.to_document()),
        "LIFECYCLE_PROFILE": canonical_json_bytes(lifecycle.to_document()),
        "SUCCESSOR_PROFILE": canonical_json_bytes(request.profile.to_document()),
        "SUCCESSOR_REQUEST": request.canonical_bytes,
        "ROLE_MANIFEST_V2": manifest.canonical_bytes,
        "ROLE_LAUNCH_CONTEXT_V2": launch_context.canonical_bytes,
    }
    if tuple(rows) != bootstrap_v2.COMMON_SEALED_INPUT_ROLES:
        _fail("derived public role input ordering changed")
    if (
        _sha256(rows["SOURCE_ARCHIVE"]) != manifest.source_archive_sha256
        or len(rows["SOURCE_ARCHIVE"]) != manifest.source_archive_byte_count
    ):
        _fail("derived source archive differs from its manifest")
    return MappingProxyType(rows)


def _fixed_argv(
    *,
    role: manifest_v2.K7ProductionBrokerRoleV2,
    manifest: manifest_v2.K7ProductionRoleManifestV2,
    launch_context: manifest_v2.K7ProductionRoleLaunchContextV2,
    repository_root: Path,
    signer_private_root: Path | None,
    signer_private_key_path: Path | None,
) -> tuple[str, ...]:
    worker = role is manifest_v2.K7ProductionBrokerRoleV2.WORKER
    role_spec = manifest.role_spec(role)
    role_document = role_spec.to_document()
    source = bootstrap_v2.bootstrap_source_for_role_v2(role.value)
    if (
        _sha256(source.encode("utf-8")) != role_document["bootstrap_sha256"]
        or len(source.encode("utf-8")) != role_document["bootstrap_byte_count"]
    ):
        _fail("fixed role bootstrap source differs from the manifest")
    return (
        os.fspath(Path(sys.executable).resolve(strict=True)),
        "-I",
        "-S",
        "-B",
        "-c",
        source,
        manifest.source_archive_sha256,
        str(manifest.source_archive_byte_count),
        manifest.interpreter_sha256,
        str(manifest.interpreter_byte_count),
        os.fspath(repository_root),
        "NOT_APPLICABLE" if worker else os.fspath(signer_private_root),
        "NOT_APPLICABLE" if worker else os.fspath(signer_private_key_path),
        manifest.manifest_id,
        role_spec.role_spec_id,
        launch_context.context_id,
    )


def _fixed_environment(
    *,
    role: manifest_v2.K7ProductionBrokerRoleV2,
    sealed_fds: tuple[int, ...],
    capability_roles: tuple[str, ...],
    capability_fds: tuple[int, ...],
) -> tuple[tuple[str, str], ...]:
    capabilities = dict(zip(capability_roles, capability_fds))
    environment = {
        **bootstrap_v2.BASE_ENVIRONMENT,
        bootstrap_v2.ROLE_ENV: role.value,
        bootstrap_v2.SEALED_FD_ENV: ",".join(str(fd) for fd in sealed_fds),
        bootstrap_v2.CHANNEL_FD_ENV: str(capabilities["BROKER_CHANNEL"]),
        bootstrap_v2.RESULT_FD_ENV: str(
            capabilities[
                "BUSINESS_RESULT_READONLY"
                if role is manifest_v2.K7ProductionBrokerRoleV2.WORKER
                else "BUSINESS_RESULT_WRITABLE"
            ]
        ),
    }
    if role is manifest_v2.K7ProductionBrokerRoleV2.WORKER:
        environment[bootstrap_v2.OUTPUT_DIRECTORY_FD_ENV] = str(
            capabilities["OUTPUT_DIRECTORY"]
        )
    fixed_fields = manifest_v2._role_fixed_fields(role)  # noqa: SLF001
    expected_keys = set(fixed_fields["runtime_environment_keys"])
    if set(environment) != expected_keys:
        _fail("fixed launch environment differs from the role manifest")
    return tuple(sorted(environment.items()))


@dataclass(frozen=True, slots=True)
class K7ProductionRoleLaunchAuthorityProfileV2:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("production role launch-authority profile is issuer-owned")
        object.__setattr__(self, "_profile_id", _content_id(PROFILE_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_production_role_launch_authority_profile.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "role_order": list(bootstrap_v2.ROLE_ORDER),
            "public_sealed_input_roles": list(
                bootstrap_v2.COMMON_SEALED_INPUT_ROLES
            ),
            "business_private_sealed_role": "LIFECYCLE_SECRET",
            "sealed_input_access": "READ_ONLY",
            "complete_seal_mask": runtime_v1.REQUIRED_MEMFD_SEALS,
            "resource_capability_bundle_required": True,
            "sealed_and_capability_fd_numbers_and_inodes_disjoint": True,
            "fixed_bootstrap_argv_and_environment": True,
            "private_locator_serialized": False,
            "process_local": True,
            "single_use": True,
            "construction_only": True,
            "central_domain_registration_pending_merge": False,
            "formal_locks": _formal_locks(),
        }

    @property
    def profile_id(self) -> str:
        if _content_id(PROFILE_DOMAIN, self._payload()) != self._profile_id:
            _fail("production role launch-authority profile changed")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "production_role_launch_authority_profile_id": self.profile_id,
        }


_OFFICIAL_PROFILE = K7ProductionRoleLaunchAuthorityProfileV2(_PROFILE_ISSUER)


def official_v075_k7_production_role_launch_authority_profile_v2(
) -> K7ProductionRoleLaunchAuthorityProfileV2:
    return _OFFICIAL_PROFILE


class K7ProductionRoleLaunchAuthorityV2:
    """Issuer-owned prelaunch descriptor graph transferred exactly once."""

    __slots__ = (
        "_argv",
        "_authority_id",
        "_capability_bundle",
        "_capability_fds",
        "_capability_rows",
        "_consumed",
        "_environment",
        "_executable_fd",
        "_executable_identity",
        "_input_digests",
        "_input_identities",
        "_launch_context",
        "_lock",
        "_manifest",
        "_owner_pid",
        "_private_key_identity",
        "_private_root_identity",
        "_public_expected",
        "_repository_identity",
        "_repository_root",
        "_role",
        "_sealed_fds",
        "_signer_private_key_path",
        "_signer_private_root",
    )

    def __init__(
        self,
        issuer: object,
        *,
        manifest: manifest_v2.K7ProductionRoleManifestV2,
        launch_context: manifest_v2.K7ProductionRoleLaunchContextV2,
        capability_bundle: resource_v2.K7BrokerRoleCapabilityBundleV2,
        executable_fd: int,
        executable_identity: tuple[int, ...],
        sealed_fds: tuple[int, ...],
        input_identities: tuple[tuple[int, ...], ...],
        input_digests: tuple[str | None, ...],
        public_expected: tuple[tuple[str, bytes], ...],
        capability_fds: tuple[int, ...],
        capability_rows: tuple[
            tuple[str, tuple[int, ...], str, int | None], ...
        ],
        repository_root: Path,
        repository_identity: tuple[int, ...],
        signer_private_root: Path | None,
        private_root_identity: tuple[int, ...] | None,
        signer_private_key_path: Path | None,
        private_key_identity: tuple[int, ...] | None,
        argv: tuple[str, ...],
        environment: tuple[tuple[str, str], ...],
    ) -> None:
        if issuer is not _AUTHORITY_ISSUER:
            _fail("production role launch authority is caller-minted")
        self._manifest = manifest
        self._launch_context = launch_context
        self._capability_bundle = capability_bundle
        self._role = launch_context.role
        self._executable_fd = executable_fd
        self._executable_identity = executable_identity
        self._sealed_fds = sealed_fds
        self._input_identities = input_identities
        self._input_digests = input_digests
        self._public_expected = public_expected
        self._capability_fds = capability_fds
        self._capability_rows = capability_rows
        self._repository_root = repository_root
        self._repository_identity = repository_identity
        self._signer_private_root = signer_private_root
        self._private_root_identity = private_root_identity
        self._signer_private_key_path = signer_private_key_path
        self._private_key_identity = private_key_identity
        self._argv = argv
        self._environment = environment
        self._owner_pid = os.getpid()
        self._consumed = False
        self._lock = Lock()
        self._authority_id = _content_id(AUTHORITY_DOMAIN, self._payload())

    def _check_owner(self) -> None:
        if os.getpid() != self._owner_pid:
            _fail("production role launch authority crossed a process boundary")

    @property
    def role(self) -> manifest_v2.K7ProductionBrokerRoleV2:
        return self._role

    def _assert_current_locked(self) -> None:
        self._check_owner()
        if self._consumed:
            _fail("production role launch authority was already consumed")
        manifest = self._manifest
        context = self._launch_context
        bundle = self._capability_bundle
        manifest.assert_current()
        if (
            context.manifest is not manifest
            or context.role is not self.role
            or bundle.role is not self.role
            or bundle.manifest_id != manifest.manifest_id
            or bundle.launch_context_id != context.context_id
            or bundle.request_id != context.binding.request_id
            or bundle.route_identity_id != context.binding.route_identity_id
            or bundle.broker_execution_spec_id
            != context.binding.broker_execution_spec_id
            or bundle.session_nonce != context.binding.session_nonce
        ):
            _fail("production launch manifest/context/resource graph crossed")
        _inspect_interpreter(
            self._executable_fd,
            expected_identity=self._executable_identity,
            expected_sha256=manifest.interpreter_sha256,
            expected_byte_count=manifest.interpreter_byte_count,
        )
        expected_rows = dict(self._public_expected)
        sealed_roles = (
            bootstrap_v2.WORKER_SEALED_INPUT_ROLES
            if self.role is manifest_v2.K7ProductionBrokerRoleV2.WORKER
            else bootstrap_v2.BUSINESS_SEALED_INPUT_ROLES
        )
        for index, (role, descriptor) in enumerate(
            zip(sealed_roles, self._sealed_fds)
        ):
            expected_raw = expected_rows.get(role)
            identity, digest, _seals = _inspect_sealed_input(
                descriptor,
                label=role.lower(),
                expected_identity=self._input_identities[index],
                expected_raw=expected_raw,
            )
            if identity != self._input_identities[index] or digest != self._input_digests[index]:
                _fail("production launch sealed input digest or identity changed")
        capability_fds, capability_rows = _inspect_capabilities(
            bundle,
            expected_rows=self._capability_rows,
        )
        if capability_fds != self._capability_fds:
            _fail("production launch capability FD vector changed")
        all_fds = (self._executable_fd, *self._sealed_fds, *capability_fds)
        all_identities = (
            self._executable_identity,
            *self._input_identities,
            *(row[1] for row in capability_rows),
        )
        if (
            len(set(all_fds)) != len(all_fds)
            or len({identity[:2] for identity in all_identities})
            != len(all_identities)
        ):
            _fail("executable, sealed, and capability FD lanes overlap")
        if _path_identity(self._repository_root, directory=True) != self._repository_identity:
            _fail("production repository locator identity changed")
        worker = self.role is manifest_v2.K7ProductionBrokerRoleV2.WORKER
        if worker:
            if (
                self._signer_private_root is not None
                or self._signer_private_key_path is not None
                or self._private_root_identity is not None
                or self._private_key_identity is not None
            ):
                _fail("worker production launch gained private signer locators")
        else:
            if (
                self._signer_private_root is None
                or self._signer_private_key_path is None
                or _path_identity(self._signer_private_root, directory=True)
                != self._private_root_identity
                or _path_identity(self._signer_private_key_path, directory=False)
                != self._private_key_identity
            ):
                _fail("business private signer locator identity changed")
        if self._argv != _fixed_argv(
            role=self.role,
            manifest=manifest,
            launch_context=context,
            repository_root=self._repository_root,
            signer_private_root=self._signer_private_root,
            signer_private_key_path=self._signer_private_key_path,
        ) or self._environment != _fixed_environment(
            role=self.role,
            sealed_fds=self._sealed_fds,
            capability_roles=bundle.descriptor_roles,
            capability_fds=capability_fds,
        ):
            _fail("production launch argv or environment changed")
        if _content_id(AUTHORITY_DOMAIN, self._payload()) != self._authority_id:
            _fail("production role launch authority content identity changed")

    def assert_current(self) -> None:
        with self._lock:
            self._assert_current_locked()

    @property
    def consumed(self) -> bool:
        self._check_owner()
        return self._consumed

    @property
    def authority_id(self) -> str:
        self._check_owner()
        if _content_id(AUTHORITY_DOMAIN, self._payload()) != self._authority_id:
            _fail("production role launch authority content identity changed")
        return self._authority_id

    @property
    def sealed_input_roles(self) -> tuple[str, ...]:
        return (
            bootstrap_v2.WORKER_SEALED_INPUT_ROLES
            if self.role is manifest_v2.K7ProductionBrokerRoleV2.WORKER
            else bootstrap_v2.BUSINESS_SEALED_INPUT_ROLES
        )

    @property
    def capability_roles(self) -> tuple[str, ...]:
        return self._capability_bundle.descriptor_roles

    def _payload(self) -> dict[str, Any]:
        manifest = self._manifest
        role_spec = manifest.role_spec(self.role)
        role_document = role_spec.to_document()
        input_rows = []
        for index, role in enumerate(self.sealed_input_roles):
            secret = role == "LIFECYCLE_SECRET"
            input_rows.append(
                {
                    "role": role,
                    "descriptor_identity": _identity_document(
                        self._input_identities[index]
                    ),
                    "sha256": None if secret else self._input_digests[index],
                    "byte_count": self._input_identities[index][6],
                    "access": "READ_ONLY",
                    "seal_mask": runtime_v1.REQUIRED_MEMFD_SEALS,
                    "content_read_by_authority": False if secret else True,
                }
            )
        capability_rows = [
            {
                "role": role,
                "descriptor_identity": _identity_document(identity),
                "semantics": semantics,
                "seal_mask": seals,
            }
            for role, identity, semantics, seals in self._capability_rows
        ]
        return {
            "schema": "acfqp.v075_k7_production_role_launch_authority.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "production_role_launch_authority_profile_id": _OFFICIAL_PROFILE.profile_id,
            "production_role_manifest_id": manifest.manifest_id,
            "production_role_spec_id": role_spec.role_spec_id,
            "production_role_launch_context_id": self._launch_context.context_id,
            "broker_role_capability_bundle_id": self._capability_bundle.bundle_id,
            "request_id": manifest.request_id,
            "route_identity_id": manifest.route_identity_id,
            "role": self.role.value,
            "bootstrap_sha256": role_document["bootstrap_sha256"],
            "bootstrap_byte_count": role_document["bootstrap_byte_count"],
            "interpreter_sha256": manifest.interpreter_sha256,
            "interpreter_byte_count": manifest.interpreter_byte_count,
            "interpreter_descriptor_identity": _identity_document(
                self._executable_identity
            ),
            "interpreter_access": "READ_ONLY",
            "public_source_archive_sha256": manifest.source_archive_sha256,
            "public_source_archive_byte_count": manifest.source_archive_byte_count,
            "sealed_inputs": input_rows,
            "capabilities": capability_rows,
            "sealed_fd_count": len(self._sealed_fds),
            "capability_fd_count": len(self._capability_fds),
            "sealed_and_capability_fd_numbers_and_inodes_disjoint": True,
            "repository_root_path_sha256": manifest.repository_root_path_sha256,
            "private_locator_required": self.role is manifest_v2.K7ProductionBrokerRoleV2.BUSINESS,
            "private_locator_serialized": False,
            "raw_descriptor_numbers_serialized": False,
            "argv_values_serialized": False,
            "environment_values_serialized": False,
            "environment_keys": [key for key, _value in self._environment],
            "lifecycle_secret_commitment_id": (
                manifest.request.sealed_secret_commitment_id
                if self.role is manifest_v2.K7ProductionBrokerRoleV2.BUSINESS
                else None
            ),
            "lifecycle_secret_content_verification_deferred_to_business_core": (
                self.role is manifest_v2.K7ProductionBrokerRoleV2.BUSINESS
            ),
            "consume_transfers_no_launch_claim": True,
            "processes_launched": 0,
            "construction_only": True,
            "central_domain_registration_pending_merge": False,
            "formal_locks": _formal_locks(),
        }

    def to_document(self) -> dict[str, Any]:
        self._check_owner()
        return {
            **self._payload(),
            "production_role_launch_authority_id": self.authority_id,
        }

    def consume(self) -> K7ProductionRoleNativeLaunchRecordV2:
        """Transfer the exact retained launch record to one native launcher."""

        with self._lock:
            self._assert_current_locked()
            self._consumed = True
            return (
                self._executable_fd,
                self._sealed_fds,
                self._capability_fds,
                self._argv,
                self._environment,
            )

    def __reduce__(self) -> NoReturn:
        raise TypeError("production role launch authority is process-local")

    def __reduce_ex__(self, _protocol: int) -> NoReturn:
        raise TypeError("production role launch authority is process-local")


def freeze_v075_k7_production_role_launch_authority_v2(
    *,
    manifest: manifest_v2.K7ProductionRoleManifestV2,
    launch_context: manifest_v2.K7ProductionRoleLaunchContextV2,
    capability_bundle: resource_v2.K7BrokerRoleCapabilityBundleV2,
    public_sealed_input_fds: Mapping[str, int],
    interpreter_fd: int,
    repository_root: Path,
    lifecycle_secret_fd: int | None = None,
    signer_private_root: Path | None = None,
    signer_private_key_path: Path | None = None,
) -> K7ProductionRoleLaunchAuthorityV2:
    """Freeze one exact unlaunched native role record."""

    if (
        type(manifest) is not manifest_v2.K7ProductionRoleManifestV2
        or type(launch_context)
        is not manifest_v2.K7ProductionRoleLaunchContextV2
        or type(capability_bundle)
        is not resource_v2.K7BrokerRoleCapabilityBundleV2
        or not isinstance(public_sealed_input_fds, Mapping)
        or not isinstance(repository_root, Path)
    ):
        _fail("production launch-authority factory received mistyped authorities")
    manifest.assert_current()
    role = launch_context.role
    worker = role is manifest_v2.K7ProductionBrokerRoleV2.WORKER
    if (
        launch_context.manifest is not manifest
        or capability_bundle.role is not role
        or capability_bundle.manifest_id != manifest.manifest_id
        or capability_bundle.launch_context_id != launch_context.context_id
        or capability_bundle.request_id != launch_context.binding.request_id
        or capability_bundle.route_identity_id
        != launch_context.binding.route_identity_id
        or capability_bundle.broker_execution_spec_id
        != launch_context.binding.broker_execution_spec_id
        or capability_bundle.session_nonce != launch_context.binding.session_nonce
    ):
        _fail("production launch manifest/context/resource bundle crossed")
    expected_public = derive_v075_k7_production_role_public_input_bytes_v2(
        manifest=manifest,
        launch_context=launch_context,
    )
    if (
        set(public_sealed_input_fds) != set(bootstrap_v2.COMMON_SEALED_INPUT_ROLES)
        or any(
            type(name) is not str or type(descriptor) is not int
            for name, descriptor in public_sealed_input_fds.items()
        )
    ):
        _fail("public sealed input roles are incomplete, unknown, or mistyped")
    public_fds = tuple(
        public_sealed_input_fds[role_name]
        for role_name in bootstrap_v2.COMMON_SEALED_INPUT_ROLES
    )
    if worker:
        if (
            lifecycle_secret_fd is not None
            or signer_private_root is not None
            or signer_private_key_path is not None
        ):
            _fail("worker launch may not receive business private capabilities")
        sealed_fds = public_fds
        private_root_identity = None
        private_key_identity = None
    else:
        if (
            type(lifecycle_secret_fd) is not int
            or lifecycle_secret_fd < 3
            or not isinstance(signer_private_root, Path)
            or not isinstance(signer_private_key_path, Path)
        ):
            _fail("business launch requires its secret and private signer locators")
        sealed_fds = (*public_fds, lifecycle_secret_fd)
        private_root_identity = _path_identity(
            signer_private_root, directory=True
        )
        private_key_identity = _path_identity(
            signer_private_key_path, directory=False
        )
        if (
            private_root_identity != manifest.private_root_identity
            or private_key_identity != manifest.private_key_identity
        ):
            _fail("business private signer locators crossed the role manifest")
    if len(set((interpreter_fd, *sealed_fds))) != 1 + len(sealed_fds):
        _fail("interpreter and sealed input FD numbers overlap")
    executable_identity = _inspect_interpreter(
        interpreter_fd,
        expected_identity=None,
        expected_sha256=manifest.interpreter_sha256,
        expected_byte_count=manifest.interpreter_byte_count,
    )
    input_identities: list[tuple[int, ...]] = []
    input_digests: list[str | None] = []
    sealed_roles = (
        bootstrap_v2.WORKER_SEALED_INPUT_ROLES
        if worker
        else bootstrap_v2.BUSINESS_SEALED_INPUT_ROLES
    )
    for role_name, descriptor in zip(sealed_roles, sealed_fds):
        identity, digest, _seals = _inspect_sealed_input(
            descriptor,
            label=role_name.lower(),
            expected_identity=None,
            expected_raw=expected_public.get(role_name),
        )
        input_identities.append(identity)
        input_digests.append(digest)
    capability_fds, capability_rows = _inspect_capabilities(
        capability_bundle,
        expected_rows=None,
    )
    all_fds = (interpreter_fd, *sealed_fds, *capability_fds)
    all_identities = (
        executable_identity,
        *input_identities,
        *(row[1] for row in capability_rows),
    )
    if (
        len(set(all_fds)) != len(all_fds)
        or len({identity[:2] for identity in all_identities})
        != len(all_identities)
    ):
        _fail("capability FDs cannot masquerade as sealed or executable inputs")
    repository_identity = _path_identity(repository_root, directory=True)
    if (
        hashlib.sha256(os.fsencode(repository_root)).hexdigest()
        != manifest.repository_root_path_sha256
    ):
        _fail("production repository locator crossed the role manifest")
    argv = _fixed_argv(
        role=role,
        manifest=manifest,
        launch_context=launch_context,
        repository_root=repository_root,
        signer_private_root=signer_private_root,
        signer_private_key_path=signer_private_key_path,
    )
    environment = _fixed_environment(
        role=role,
        sealed_fds=sealed_fds,
        capability_roles=capability_bundle.descriptor_roles,
        capability_fds=capability_fds,
    )
    authority = K7ProductionRoleLaunchAuthorityV2(
        _AUTHORITY_ISSUER,
        manifest=manifest,
        launch_context=launch_context,
        capability_bundle=capability_bundle,
        executable_fd=interpreter_fd,
        executable_identity=executable_identity,
        sealed_fds=sealed_fds,
        input_identities=tuple(input_identities),
        input_digests=tuple(input_digests),
        public_expected=tuple(expected_public.items()),
        capability_fds=capability_fds,
        capability_rows=capability_rows,
        repository_root=repository_root,
        repository_identity=repository_identity,
        signer_private_root=signer_private_root,
        private_root_identity=private_root_identity,
        signer_private_key_path=signer_private_key_path,
        private_key_identity=private_key_identity,
        argv=argv,
        environment=environment,
    )
    authority.assert_current()
    issuance_key = (os.getpid(), launch_context.context_id, capability_bundle.bundle_id)
    with _ISSUANCE_LOCK:
        if issuance_key in _ISSUED_BINDINGS:
            _fail("production role launch binding already has one authority")
        _ISSUED_BINDINGS.add(issuance_key)
    return authority


__all__ = (
    "AUTHORITY_DOMAIN",
    "K7ProductionRoleLaunchAuthorityProfileV2",
    "K7ProductionRoleLaunchAuthorityV2",
    "K7ProductionRoleNativeLaunchRecordV2",
    "MAX_INTERPRETER_BYTES",
    "MAX_PUBLIC_INPUT_BYTES",
    "PROFILE_DOMAIN",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SCHEMA_VERSION",
    "V075K7ProductionRoleLaunchAuthorityV2Error",
    "derive_v075_k7_production_role_public_input_bytes_v2",
    "freeze_v075_k7_production_role_launch_authority_v2",
    "official_v075_k7_production_role_launch_authority_profile_v2",
)
