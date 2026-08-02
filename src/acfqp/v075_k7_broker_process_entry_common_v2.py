"""Shared fresh-exec input reconstruction for the K7 broker role entries."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import fcntl
import hashlib
import os
from pathlib import Path
import socket
import stat
from typing import Any, NoReturn

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime_v1
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp import v075_k7_production_role_bootstrap_v2 as bootstrap_v2
from acfqp import v075_k7_production_role_manifest_v2 as manifest_v2
from acfqp import v075_k7_successor_portable_replay_v1 as replay_v1


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.8"
PROFILE_KEY = "v075_k7_broker_process_entry_common_v2"
MAX_PUBLIC_INPUT_BYTES = runtime_v1.MAX_SEALED_INPUT_BYTES

_INPUTS_ISSUER = object()


class V075K7BrokerProcessEntryCommonV2Error(RuntimeError):
    """The fresh-exec descriptor or portable authority graph is invalid."""


def _fail(message: str) -> NoReturn:
    raise V075K7BrokerProcessEntryCommonV2Error(message)


def _inspect_sealed(
    descriptor: int, label: str
) -> tuple[os.stat_result, int]:
    try:
        status = os.fstat(descriptor)
        seals = fcntl.fcntl(descriptor, runtime_v1.F_GET_SEALS)
    except OSError as error:
        raise V075K7BrokerProcessEntryCommonV2Error(
            f"{label} descriptor cannot be inspected"
        ) from error
    if (
        not stat.S_ISREG(status.st_mode)
        or not 0 < status.st_size <= MAX_PUBLIC_INPUT_BYTES
        or seals & runtime_v1.REQUIRED_MEMFD_SEALS
        != runtime_v1.REQUIRED_MEMFD_SEALS
    ):
        _fail(f"{label} descriptor is not one bounded sealed regular input")
    return status, seals


def _read_sealed(descriptor: int, label: str) -> bytes:
    status, seals = _inspect_sealed(descriptor, label)
    chunks: list[bytes] = []
    offset = 0
    while offset < status.st_size:
        try:
            chunk = os.pread(
                descriptor,
                min(1024 * 1024, status.st_size - offset),
                offset,
            )
        except OSError as error:
            raise V075K7BrokerProcessEntryCommonV2Error(
                f"{label} descriptor read failed"
            ) from error
        if not chunk:
            _fail(f"{label} descriptor ended early")
        chunks.append(chunk)
        offset += len(chunk)
    raw = b"".join(chunks)
    after = os.fstat(descriptor)
    if (
        (after.st_dev, after.st_ino, after.st_size)
        != (status.st_dev, status.st_ino, status.st_size)
        or fcntl.fcntl(descriptor, runtime_v1.F_GET_SEALS)
        != seals
    ):
        _fail(f"{label} descriptor changed while being read")
    return raw


def _fd_list(value: str, expected_count: int) -> tuple[int, ...]:
    try:
        result = tuple(int(item) for item in value.split(","))
    except (TypeError, ValueError) as error:
        raise V075K7BrokerProcessEntryCommonV2Error(
            "sealed input descriptor vector is malformed"
        ) from error
    if (
        len(result) != expected_count
        or any(descriptor < 3 for descriptor in result)
        or len(set(result)) != len(result)
    ):
        _fail("sealed input descriptor vector has the wrong cardinality")
    return result


def _single_fd(name: str) -> int:
    try:
        value = int(os.environ[name])
    except (KeyError, TypeError, ValueError) as error:
        raise V075K7BrokerProcessEntryCommonV2Error(
            f"runtime descriptor variable {name} is invalid"
        ) from error
    if value < 3:
        _fail(f"runtime descriptor variable {name} uses a standard FD")
    return value


def _path_identity(path: Path, *, directory: bool) -> tuple[int, ...]:
    try:
        resolved = path.resolve(strict=True)
        status = os.stat(resolved, follow_symlinks=False)
    except OSError as error:
        raise V075K7BrokerProcessEntryCommonV2Error(
            "fresh-exec runtime locator is unavailable"
        ) from error
    if not path.is_absolute() or resolved != path:
        _fail("fresh-exec runtime locator is not absolute and canonical")
    if directory != stat.S_ISDIR(status.st_mode):
        _fail("fresh-exec runtime locator has the wrong kind")
    if not directory and not stat.S_ISREG(status.st_mode):
        _fail("fresh-exec private key locator is not a regular file")
    return (
        status.st_dev,
        status.st_ino,
        stat.S_IMODE(status.st_mode),
        status.st_uid,
        status.st_gid,
        status.st_size,
    )


def _set_cloexec(descriptors: tuple[int, ...]) -> None:
    for descriptor in descriptors:
        try:
            flags = fcntl.fcntl(descriptor, fcntl.F_GETFD)
            fcntl.fcntl(descriptor, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
        except OSError as error:
            raise V075K7BrokerProcessEntryCommonV2Error(
                "fresh-exec descriptor could not be made close-on-exec"
            ) from error
        if not fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC:
            _fail("fresh-exec descriptor did not retain close-on-exec")


@dataclass(frozen=True, slots=True)
class K7BrokerProcessInputsV2:
    _issuer: InitVar[object]
    role: manifest_v2.K7ProductionBrokerRoleV2
    request_replay: replay_v1.V075K7SuccessorPortableRequestReplayV1 = field(
        repr=False, compare=False
    )
    manifest_replay: manifest_v2.K7ProductionRoleManifestPublicReplayV2 = field(
        repr=False, compare=False
    )
    binding: ipc_v1.K7OuterAttemptBrokerIPCBindingV1
    source_archive_fd: int
    sealed_secret_fd: int | None
    endpoint: socket.socket = field(repr=False, compare=False)
    result_fd: int
    output_directory_fd: int | None
    repository_root: Path
    signer_private_root: Path | None = field(repr=False)
    signer_private_key_path: Path | None = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _INPUTS_ISSUER
            or type(self.request_replay)
            is not replay_v1.V075K7SuccessorPortableRequestReplayV1
            or type(self.manifest_replay)
            is not manifest_v2.K7ProductionRoleManifestPublicReplayV2
            or type(self.binding) is not ipc_v1.K7OuterAttemptBrokerIPCBindingV1
            or type(self.endpoint) is not socket.socket
        ):
            _fail("broker process inputs are caller-minted")

    def close_endpoint(self) -> None:
        self.endpoint.close()

    def __reduce__(self) -> NoReturn:
        raise TypeError("broker process inputs are process-local")

    def __reduce_ex__(self, _protocol: int) -> NoReturn:
        raise TypeError("broker process inputs are process-local")


def load_v075_k7_broker_process_inputs_v2(
    *, role: manifest_v2.K7ProductionBrokerRoleV2
) -> K7BrokerProcessInputsV2:
    """Reconstruct the fixed portable graph from inherited role descriptors."""

    exact_role = manifest_v2.K7ProductionBrokerRoleV2(role)
    worker = exact_role is manifest_v2.K7ProductionBrokerRoleV2.WORKER
    if len(os.sys.argv) != 7:
        _fail("broker process entry argv has the wrong fixed shape")
    (
        _label,
        repository_raw,
        private_root_raw,
        private_key_raw,
        expected_manifest_id,
        expected_role_spec_id,
        expected_context_id,
    ) = os.sys.argv
    expected_role_name = exact_role.value
    if os.environ.get(bootstrap_v2.ROLE_ENV) != expected_role_name:
        _fail("broker process entry role environment crossed its entry")
    sealed_roles = (
        bootstrap_v2.WORKER_SEALED_INPUT_ROLES
        if worker
        else bootstrap_v2.BUSINESS_SEALED_INPUT_ROLES
    )
    try:
        sealed_raw = os.environ[bootstrap_v2.SEALED_FD_ENV]
    except KeyError as error:
        raise V075K7BrokerProcessEntryCommonV2Error(
            "broker process entry lacks its sealed descriptor vector"
        ) from error
    sealed_fds = _fd_list(sealed_raw, len(sealed_roles))
    endpoint_fd = _single_fd(bootstrap_v2.CHANNEL_FD_ENV)
    result_fd = _single_fd(bootstrap_v2.RESULT_FD_ENV)
    output_fd = (
        _single_fd(bootstrap_v2.OUTPUT_DIRECTORY_FD_ENV) if worker else None
    )
    capability_fds = (
        (endpoint_fd, result_fd, output_fd)
        if worker
        else (endpoint_fd, result_fd)
    )
    if (
        any(value is None for value in capability_fds)
        or len(set((*sealed_fds, *capability_fds)))
        != len(sealed_fds) + len(capability_fds)
    ):
        _fail("broker process sealed and capability FD lanes overlap")
    exact_capabilities = tuple(int(value) for value in capability_fds)
    # Restore close-on-exec before importing or invoking any role business
    # code.  The descriptors remain usable but cannot escape a later exec.
    _set_cloexec((*sealed_fds, *exact_capabilities))

    if not worker:
        # The secret is a private descriptor capability, not a public replay
        # payload.  Inspect its immutable metadata here, but leave the sole
        # byte read to the business core that verifies its commitment.
        _inspect_sealed(sealed_fds[-1], "lifecycle_secret")
    rows = {
        name: _read_sealed(descriptor, name.lower())
        for name, descriptor in zip(sealed_roles, sealed_fds)
        if name != "LIFECYCLE_SECRET"
    }
    closure = replay_v1.reconstruct_v075_k7_successor_portable_profile_closure_v1(
        source_archive_raw=rows["SOURCE_ARCHIVE"],
        transport_profile_raw=rows["TRANSPORT_PROFILE"],
        lifecycle_profile_raw=rows["LIFECYCLE_PROFILE"],
        successor_profile_raw=rows["SUCCESSOR_PROFILE"],
    )
    request_replay = replay_v1.replay_v075_k7_successor_request_bytes_portable_v1(
        raw=rows["SUCCESSOR_REQUEST"],
        profile_closure=closure,
    )
    manifest_replay = (
        manifest_v2.verify_v075_k7_production_role_manifest_public_bytes_v2(
            raw=rows["ROLE_MANIFEST_V2"],
            expected_request_replay=request_replay,
        )
    )
    if manifest_replay.manifest_id != expected_manifest_id:
        _fail("broker process manifest argument crossed its sealed manifest")
    role_document = manifest_replay.role_document(exact_role)
    if role_document.get("production_role_spec_id") != expected_role_spec_id:
        _fail("broker process role-spec argument crossed its sealed manifest")
    binding = (
        manifest_v2
        .verify_v075_k7_production_role_launch_context_public_bytes_v2(
            raw=rows["ROLE_LAUNCH_CONTEXT_V2"],
            expected_manifest=manifest_replay,
            expected_role=exact_role,
        )
    )
    context_document = manifest_v2._canonical_document(  # noqa: SLF001
        rows["ROLE_LAUNCH_CONTEXT_V2"], "role launch context v2"
    )
    if context_document.get("production_role_launch_context_id") != expected_context_id:
        _fail("broker process launch-context argument crossed its sealed context")

    repository_root = Path(repository_raw)
    _path_identity(repository_root, directory=True)
    manifest_document = manifest_replay.document
    if hashlib.sha256(os.fsencode(repository_root)).hexdigest() != manifest_document.get(
        "repository_root_path_sha256"
    ):
        _fail("broker process repository locator crossed its manifest digest")
    private_root: Path | None = None
    private_key: Path | None = None
    secret_fd: int | None = None
    if worker:
        if private_root_raw != "NOT_APPLICABLE" or private_key_raw != "NOT_APPLICABLE":
            _fail("worker received private signer locators")
    else:
        private_root = Path(private_root_raw)
        private_key = Path(private_key_raw)
        if list(_path_identity(private_root, directory=True)) != manifest_document.get(
            "private_root_inode_identity"
        ) or list(_path_identity(private_key, directory=False)) != manifest_document.get(
            "private_key_inode_identity"
        ):
            _fail("business private locators crossed their manifest identities")
        secret_fd = sealed_fds[-1]

    endpoint = socket.socket(fileno=endpoint_fd)
    try:
        if (
            endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_DOMAIN)
            != socket.AF_UNIX
            or endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
            != socket.SOCK_SEQPACKET
            or endpoint.getblocking() is not True
        ):
            _fail("broker process endpoint lost its fixed kernel contract")
        result = K7BrokerProcessInputsV2(
            _INPUTS_ISSUER,
            exact_role,
            request_replay,
            manifest_replay,
            binding,
            sealed_fds[0],
            secret_fd,
            endpoint,
            result_fd,
            output_fd,
            repository_root,
            private_root,
            private_key,
        )
        endpoint = None  # type: ignore[assignment]
        return result
    finally:
        if endpoint is not None:
            endpoint.close()


__all__ = (
    "K7BrokerProcessInputsV2",
    "MAX_PUBLIC_INPUT_BYTES",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V075K7BrokerProcessEntryCommonV2Error",
    "load_v075_k7_broker_process_inputs_v2",
)
