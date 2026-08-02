"""Frozen archive-loading bootstraps for the K7 broker roles.

The two sources in this module are complete ``python -I -S -B -c`` programs.
They validate the exact descriptor namespace, sealed source archive and
interpreter before importing a fixed role entry from the archive.  This module
does not launch a process and does not authorize a live broker or accounting
artifact.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_PRODUCTION_ROLE_BOOTSTRAP_PROFILE_V2_DOMAIN,
    content_id,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.8"
PROFILE_KEY = "v075_k7_production_role_bootstrap_v2"

WORKER_ROLE = "WORKER"
BUSINESS_ROLE = "BUSINESS"
ROLE_ORDER = (WORKER_ROLE, BUSINESS_ROLE)

SEALED_FD_ENV = "ACFQP_K7_SEALED_INPUT_FDS"
ROLE_ENV = "ACFQP_K7_ROLE"
CHANNEL_FD_ENV = "ACFQP_K7_BROKER_CHANNEL_FD"
RESULT_FD_ENV = "ACFQP_K7_BUSINESS_RESULT_FD"
OUTPUT_DIRECTORY_FD_ENV = "ACFQP_K7_OUTPUT_DIRECTORY_FD"
BASE_ENVIRONMENT = {"LANG": "C", "LC_ALL": "C", "TZ": "UTC"}

WORKER_ENTRY_MODULE = "acfqp.v075_k7_broker_worker_process_entry_v2"
WORKER_ENTRY_SYMBOL = "run_v075_k7_broker_worker_process_entry_v2"
BUSINESS_ENTRY_MODULE = "acfqp.v075_k7_broker_business_process_entry_v2"
BUSINESS_ENTRY_SYMBOL = "run_v075_k7_broker_business_process_entry_v2"

COMMON_SEALED_INPUT_ROLES = (
    "SOURCE_ARCHIVE",
    "TRANSPORT_PROFILE",
    "LIFECYCLE_PROFILE",
    "SUCCESSOR_PROFILE",
    "SUCCESSOR_REQUEST",
    "ROLE_MANIFEST_V2",
    "ROLE_LAUNCH_CONTEXT_V2",
)
WORKER_SEALED_INPUT_ROLES = COMMON_SEALED_INPUT_ROLES
BUSINESS_SEALED_INPUT_ROLES = (*COMMON_SEALED_INPUT_ROLES, "LIFECYCLE_SECRET")
WORKER_CAPABILITY_ROLES = (
    "BROKER_CHANNEL",
    "BUSINESS_RESULT_READONLY",
    "OUTPUT_DIRECTORY",
)
BUSINESS_CAPABILITY_ROLES = (
    "BROKER_CHANNEL",
    "BUSINESS_RESULT_WRITABLE",
)

LOCAL_DOMAIN_TAGS = frozenset(
    {V075_K7_PRODUCTION_ROLE_BOOTSTRAP_PROFILE_V2_DOMAIN}
)
if not LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("production role-bootstrap domain is unregistered")

_PROFILE_ISSUER = object()


class V075K7ProductionRoleBootstrapV2Error(ValueError):
    """The static bootstrap profile or requested role is invalid."""


def _fail(message: str) -> NoReturn:
    raise V075K7ProductionRoleBootstrapV2Error(message)


def _hash(payload: Mapping[str, Any]) -> str:
    return content_id(
        V075_K7_PRODUCTION_ROLE_BOOTSTRAP_PROFILE_V2_DOMAIN,
        dict(payload),
    )


def _bootstrap_source(
    *,
    role: str,
    entry_module: str,
    entry_symbol: str,
    sealed_count: int,
    has_output_directory: bool,
) -> str:
    """Render a standalone bootstrap without importing project code first."""

    required_env = sorted(
        {
            *BASE_ENVIRONMENT,
            ROLE_ENV,
            SEALED_FD_ENV,
            CHANNEL_FD_ENV,
            RESULT_FD_ENV,
            *({OUTPUT_DIRECTORY_FD_ENV} if has_output_directory else set()),
        }
    )
    capability_names = [CHANNEL_FD_ENV, RESULT_FD_ENV]
    if has_output_directory:
        capability_names.append(OUTPUT_DIRECTORY_FD_ENV)
    # repr() is used only on frozen ASCII constants and makes the generated
    # bytes reviewable and independent of indentation in this module.
    return f'''import fcntl
import hashlib
import importlib
import os
import socket
import stat
import sys

def die(code):
    os._exit(code)

try:
    failure_code = 95
    if any(name == "acfqp" or name.startswith("acfqp.") for name in sys.modules):
        die(81)
    if len(sys.argv) != 11 or not (
        sys.flags.isolated == 1 and sys.flags.no_site == 1
        and sys.flags.ignore_environment == 1
        and sys.flags.dont_write_bytecode == 1
    ):
        die(81)
    expected_env = {required_env!r}
    if sorted(os.environ) != expected_env or any(
        os.environ.get(key) != value for key, value in {BASE_ENVIRONMENT!r}.items()
    ) or os.environ.get({ROLE_ENV!r}) != {role!r}:
        die(82)
    sealed = tuple(int(value) for value in os.environ[{SEALED_FD_ENV!r}].split(","))
    capabilities = tuple(int(os.environ[name]) for name in {capability_names!r})
    if len(sealed) != {sealed_count} or min((*sealed, *capabilities), default=-1) < 3:
        die(83)
    if len(set((*sealed, *capabilities))) != len(sealed) + len(capabilities):
        die(83)
    archive_fd = sealed[0]
    archive_sha = sys.argv[1]
    archive_size = int(sys.argv[2])
    interpreter_sha = sys.argv[3]
    interpreter_size = int(sys.argv[4])
    repository_root = sys.argv[5]
    private_root = sys.argv[6]
    private_key = sys.argv[7]
    manifest_id = sys.argv[8]
    role_spec_id = sys.argv[9]
    launch_context_id = sys.argv[10]
    for identity in (manifest_id, role_spec_id, launch_context_id):
        if len(identity) != 64 or any(c not in "0123456789abcdef" for c in identity):
            die(84)
    required_seals = 0x0008 | 0x0004 | 0x0002 | 0x0001
    for descriptor in sealed:
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode) or status.st_size <= 0:
            die(85)
        if fcntl.fcntl(descriptor, 1034) & required_seals != required_seals:
            die(85)
        if fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC:
            die(85)
    channel_fd = capabilities[0]
    result_fd = capabilities[1]
    channel = socket.socket(fileno=os.dup(channel_fd))
    try:
        if channel.getsockopt(socket.SOL_SOCKET, socket.SO_DOMAIN) != socket.AF_UNIX:
            die(86)
        if channel.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) != socket.SOCK_SEQPACKET:
            die(86)
        if channel.getpeername() in (None,):
            die(86)
    finally:
        channel.close()
    result_status = os.fstat(result_fd)
    result_access = fcntl.fcntl(result_fd, fcntl.F_GETFL) & os.O_ACCMODE
    if not stat.S_ISREG(result_status.st_mode) or result_status.st_size != 0:
        die(87)
    if result_access != ({'os.O_RDONLY' if role == WORKER_ROLE else 'os.O_RDWR'}):
        die(87)
    if fcntl.fcntl(result_fd, 1034) != 0:
        die(87)
    if fcntl.fcntl(channel_fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC:
        die(88)
    if fcntl.fcntl(result_fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC:
        die(88)
    if {has_output_directory!r}:
        output_fd = capabilities[2]
        if not stat.S_ISDIR(os.fstat(output_fd).st_mode):
            die(89)
        if fcntl.fcntl(output_fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC:
            die(89)
    executable_status = os.stat("/proc/self/exe")
    visible = []
    for name in os.listdir("/proc/self/fd"):
        try:
            descriptor = int(name)
            status = os.fstat(descriptor)
        except (OSError, ValueError):
            continue
        visible.append((descriptor, status.st_dev, status.st_ino))
    fixed = {{0, 1, 2, *sealed, *capabilities}}
    extras = [row for row in visible if row[0] not in fixed]
    executable_fds = [
        descriptor for descriptor, device, inode in extras
        if (device, inode) == (executable_status.st_dev, executable_status.st_ino)
    ]
    if len(extras) != 1 or len(executable_fds) != 1:
        die(90)
    for descriptor in (*sealed, *capabilities):
        flags = fcntl.fcntl(descriptor, fcntl.F_GETFD)
        fcntl.fcntl(descriptor, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
        if not fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC:
            die(90)
    if executable_status.st_size != interpreter_size:
        die(91)
    digest = hashlib.sha256()
    with open("/proc/self/exe", "rb", buffering=0) as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    if digest.hexdigest() != interpreter_sha:
        die(91)
    os.close(executable_fds[0])
    archive_status = os.fstat(archive_fd)
    if archive_status.st_size != archive_size:
        die(92)
    digest = hashlib.sha256()
    offset = 0
    while offset < archive_status.st_size:
        chunk = os.pread(archive_fd, min(1024 * 1024, archive_status.st_size - offset), offset)
        if not chunk:
            die(92)
        digest.update(chunk)
        offset += len(chunk)
    if digest.hexdigest() != archive_sha:
        die(92)
    if any(path == repository_root or path.startswith(repository_root + "/") for path in sys.path):
        die(93)
    archive_path = "/proc/self/fd/" + str(archive_fd)
    sys.path.insert(0, archive_path)
    failure_code = 96
    module = importlib.import_module({entry_module!r})
    origin = getattr(getattr(module, "__spec__", None), "origin", None)
    if not isinstance(origin, str) or not origin.startswith(archive_path + "/"):
        die(94)
    entry = getattr(module, {entry_symbol!r}, None)
    if not callable(entry):
        die(94)
    sys.argv = [
        "acfqp-k7-{role.lower()}-v2", repository_root, private_root,
        private_key, manifest_id, role_spec_id, launch_context_id,
    ]
    failure_code = 97
    raise SystemExit(entry())
except SystemExit:
    raise
except BaseException:
    die(failure_code)
'''.strip()


WORKER_BOOTSTRAP_SOURCE = _bootstrap_source(
    role=WORKER_ROLE,
    entry_module=WORKER_ENTRY_MODULE,
    entry_symbol=WORKER_ENTRY_SYMBOL,
    sealed_count=len(WORKER_SEALED_INPUT_ROLES),
    has_output_directory=True,
)
BUSINESS_BOOTSTRAP_SOURCE = _bootstrap_source(
    role=BUSINESS_ROLE,
    entry_module=BUSINESS_ENTRY_MODULE,
    entry_symbol=BUSINESS_ENTRY_SYMBOL,
    sealed_count=len(BUSINESS_SEALED_INPUT_ROLES),
    has_output_directory=False,
)
WORKER_BOOTSTRAP_SHA256 = hashlib.sha256(
    WORKER_BOOTSTRAP_SOURCE.encode("utf-8")
).hexdigest()
BUSINESS_BOOTSTRAP_SHA256 = hashlib.sha256(
    BUSINESS_BOOTSTRAP_SOURCE.encode("utf-8")
).hexdigest()


def bootstrap_source_for_role_v2(role: str) -> str:
    if role == WORKER_ROLE:
        return WORKER_BOOTSTRAP_SOURCE
    if role == BUSINESS_ROLE:
        return BUSINESS_BOOTSTRAP_SOURCE
    _fail("production bootstrap requested an unknown role")


def bootstrap_sha256_for_role_v2(role: str) -> str:
    return hashlib.sha256(
        bootstrap_source_for_role_v2(role).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class K7ProductionRoleBootstrapProfileV2:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("production role-bootstrap profile is issuer-owned")
        object.__setattr__(self, "_profile_id", _hash(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_production_role_bootstrap_profile.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "role_order": list(ROLE_ORDER),
            "python_flags": ["-I", "-S", "-B", "-c"],
            "worker_bootstrap_sha256": WORKER_BOOTSTRAP_SHA256,
            "worker_bootstrap_byte_count": len(
                WORKER_BOOTSTRAP_SOURCE.encode("utf-8")
            ),
            "business_bootstrap_sha256": BUSINESS_BOOTSTRAP_SHA256,
            "business_bootstrap_byte_count": len(
                BUSINESS_BOOTSTRAP_SOURCE.encode("utf-8")
            ),
            "source_archive_loaded_from_proc_fd": True,
            "live_workspace_import_allowed": False,
            "exact_descriptor_namespace_required": True,
            "sealed_and_capability_fd_lanes_distinct": True,
            "private_locator_serialized": False,
            "process_launcher_implemented": False,
            "role_specific_seccomp_implemented": False,
            "role_specific_landlock_implemented": False,
            "live_broker_execution_authorized": False,
            "formal_accounting_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def profile_id(self) -> str:
        if _hash(self._payload()) != self._profile_id:
            _fail("production role-bootstrap profile changed after issuance")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "production_role_bootstrap_profile_id": self.profile_id,
        }


_OFFICIAL_PROFILE = K7ProductionRoleBootstrapProfileV2(_PROFILE_ISSUER)


def official_v075_k7_production_role_bootstrap_profile_v2(
) -> K7ProductionRoleBootstrapProfileV2:
    return _OFFICIAL_PROFILE


__all__ = (
    "BASE_ENVIRONMENT",
    "BUSINESS_BOOTSTRAP_SHA256",
    "BUSINESS_BOOTSTRAP_SOURCE",
    "BUSINESS_CAPABILITY_ROLES",
    "BUSINESS_ENTRY_MODULE",
    "BUSINESS_ENTRY_SYMBOL",
    "BUSINESS_ROLE",
    "BUSINESS_SEALED_INPUT_ROLES",
    "CHANNEL_FD_ENV",
    "COMMON_SEALED_INPUT_ROLES",
    "K7ProductionRoleBootstrapProfileV2",
    "OUTPUT_DIRECTORY_FD_ENV",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "RESULT_FD_ENV",
    "ROLE_ENV",
    "ROLE_ORDER",
    "SCHEMA_VERSION",
    "SEALED_FD_ENV",
    "V075K7ProductionRoleBootstrapV2Error",
    "WORKER_BOOTSTRAP_SHA256",
    "WORKER_BOOTSTRAP_SOURCE",
    "WORKER_CAPABILITY_ROLES",
    "WORKER_ENTRY_MODULE",
    "WORKER_ENTRY_SYMBOL",
    "WORKER_ROLE",
    "WORKER_SEALED_INPUT_ROLES",
    "bootstrap_sha256_for_role_v2",
    "bootstrap_source_for_role_v2",
    "official_v075_k7_production_role_bootstrap_profile_v2",
)
