"""Parent-owned atomic executor joining V0-105, V0-106, and V0-107.

This construction milestone owns the exact bootstrap specification, nonce and
cgroup-lease lifecycle, sealed input ordering, atomic pidfd runtime, public
child-frame replay, and an immutable two-frame result.  Frame one remains the
child-owned K7 business payload; frame two is created only by the parent after
EOF-before-reap, reap, descendant, and final-peak facts have been observed.

The suffix exposes raw nonformal facts for three of the nine shared resources.
It does not promote them to semantic receipts or emit CounterRecords, a
WorkVector, a ComparisonVector, a terminal, or a certificate.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import os
from pathlib import Path
import stat
import sys
from typing import Any, Mapping, NoReturn

from acfqp import construction_shared_resource_receipts_v1 as shared_v1
from acfqp import v075_k7_atomic_child_entry_v1 as child_v1
from acfqp import v075_k7_atomic_pidfd_runtime_v1 as runtime_v1
from acfqp import v075_k7_cgroup_lease_v1 as lease_v1
from acfqp import v075_k7_os_supervisor_admission_v1 as admission_v1
from acfqp import v075_k7_parent_owned_successor_ipc_v1 as successor_v1
from acfqp import v075_k7_successor_portable_replay_v1 as portable_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_ATOMIC_PARENT_ACCOUNTING_SUFFIX_V1_DOMAIN,
    V075_K7_ATOMIC_PARENT_EXECUTION_FAILURE_V1_DOMAIN,
    V075_K7_ATOMIC_PARENT_EXECUTION_RESULT_V1_DOMAIN,
    V075_K7_ATOMIC_PARENT_EXECUTION_SPEC_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.0"
PROFILE_KEY = "v075_k7_parent_atomic_executor_v1"
FRAME_WIDTH = 8
MAX_FRAME_BYTES = 64 * 1024 * 1024
MAX_TWO_FRAME_BYTES = 2 * MAX_FRAME_BYTES + 2 * FRAME_WIDTH
MAX_FIXED_POINT_ITERATIONS = 32
FIXED_DEADLINE_MILLISECONDS = runtime_v1.MAX_DEADLINE_MILLISECONDS
FIXED_MEMORY_MAX_BYTES = 2 * 1024 * 1024 * 1024
FIXED_CHILD_OUTPUT_CAP_BYTES = runtime_v1.MAX_CHILD_OUTPUT_BYTES
INPUT_ROLES = (
    "SOURCE_ARCHIVE",
    "TRANSPORT_PROFILE",
    "LIFECYCLE_PROFILE",
    "SUCCESSOR_PROFILE",
    "SUCCESSOR_REQUEST",
    "LIFECYCLE_SECRET",
)
PARENT_FRAME_ROLE = "PARENT_OWNED_ACCOUNTING_SUFFIX"
PARENT_MODULE = "acfqp.v075_k7_parent_atomic_executor_v1"
PARENT_SOURCE_PATH = "acfqp/v075_k7_parent_atomic_executor_v1.py"
CHILD_SOURCE_PATH = "acfqp/v075_k7_atomic_child_entry_v1.py"

LOCAL_DOMAINS = frozenset(
    {
        V075_K7_ATOMIC_PARENT_EXECUTION_SPEC_V1_DOMAIN,
        V075_K7_ATOMIC_PARENT_ACCOUNTING_SUFFIX_V1_DOMAIN,
        V075_K7_ATOMIC_PARENT_EXECUTION_RESULT_V1_DOMAIN,
        V075_K7_ATOMIC_PARENT_EXECUTION_FAILURE_V1_DOMAIN,
    }
)
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:
    raise RuntimeError("atomic parent-executor domains are unregistered")

_SPEC_ISSUER = object()
_RESULT_ISSUER = object()
_FAILURE_ISSUER = object()


class V075K7ParentAtomicExecutorV1Error(RuntimeError):
    """The parent execution identity, lifecycle, or two-frame output failed."""


def _fail(message: str) -> NoReturn:
    raise V075K7ParentAtomicExecutorV1Error(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAINS:
        _fail("parent executor used an undeclared content domain")
    return content_id(domain, dict(payload))


def _locks() -> dict[str, bool]:
    return {
        "shared_resource_semantics_verified": False,
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


_BOOTSTRAP_SOURCE = r'''
import fcntl
import hashlib
import os
import stat
import sys
import traceback

failure_code = 70
channel_fd = None
try:
    if any(name == "acfqp" or name.startswith("acfqp.") for name in sys.modules):
        os._exit(81)
    if (
        len(sys.argv) != 11
        or sys.flags.isolated != 1
        or sys.flags.no_site != 1
        or sys.flags.ignore_environment != 1
        or sys.flags.dont_write_bytecode != 1
    ):
        os._exit(81)
    if set(os.environ) != {
        "LANG", "LC_ALL", "TZ", "ACFQP_K7_SEALED_INPUT_FDS",
        "ACFQP_K7_PARENT_CHANNEL_FD",
    } or any(os.environ[key] != value for key, value in {
        "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
    }.items()):
        os._exit(81)
    input_fds = tuple(int(value) for value in os.environ["ACFQP_K7_SEALED_INPUT_FDS"].split(","))
    channel_fd = int(os.environ["ACFQP_K7_PARENT_CHANNEL_FD"])
    if len(input_fds) != 6 or len(set((*input_fds, channel_fd))) != 7:
        os._exit(82)
    archive_fd = input_fds[0]
    expected_archive_sha256 = sys.argv[1]
    expected_archive_size = int(sys.argv[2])
    expected_executable_sha256 = sys.argv[3]
    expected_executable_size = int(sys.argv[4])
    repository_root = sys.argv[5]
    signer_private_root = sys.argv[6]
    signer_private_key_path = sys.argv[7]
    atomic_parent_execution_spec_id = sys.argv[8]
    failure_code = 71
    expected_private_root_identity = tuple(int(value) for value in sys.argv[9].split(","))
    expected_private_key_identity = tuple(int(value) for value in sys.argv[10].split(","))
    if (
        len(atomic_parent_execution_spec_id) != 64
        or any(character not in "0123456789abcdef" for character in atomic_parent_execution_spec_id)
    ):
        os._exit(81)
    failure_code = 72
    def path_identity(path, directory):
        status = os.stat(path, follow_symlinks=False)
        if directory != stat.S_ISDIR(status.st_mode):
            os._exit(81)
        if not directory and not stat.S_ISREG(status.st_mode):
            os._exit(81)
        return (
            status.st_dev, status.st_ino, stat.S_IMODE(status.st_mode),
            status.st_uid, status.st_gid, status.st_size,
        )
    if (
        len(expected_private_root_identity) != 6
        or len(expected_private_key_identity) != 6
        or path_identity(signer_private_root, True) != expected_private_root_identity
        or path_identity(signer_private_key_path, False) != expected_private_key_identity
    ):
        os._exit(81)
    required_seals = 0x0008 | 0x0004 | 0x0002 | 0x0001
    failure_code = 73
    for descriptor in input_fds:
        descriptor_status = os.fstat(descriptor)
        if (
            not stat.S_ISREG(descriptor_status.st_mode)
            or descriptor_status.st_size <= 0
            or fcntl.fcntl(descriptor, 1034) & required_seals != required_seals
        ):
            os._exit(83)
    if not stat.S_ISSOCK(os.fstat(channel_fd).st_mode):
        os._exit(83)
    executable_status = os.stat("/proc/self/exe")
    visible = []
    for name in os.listdir("/proc/self/fd"):
        try:
            descriptor = int(name)
            status = os.fstat(descriptor)
        except (OSError, ValueError):
            continue
        visible.append((descriptor, status.st_dev, status.st_ino))
    fixed = {0, 1, 2, *input_fds, channel_fd}
    executable_fds = [
        descriptor
        for descriptor, device, inode in visible
        if descriptor not in fixed
        and (device, inode) == (executable_status.st_dev, executable_status.st_ino)
    ]
    if len(executable_fds) != 1 or {row[0] for row in visible} != fixed | set(executable_fds):
        os._exit(83)
    if fcntl.fcntl(archive_fd, 1034) & required_seals != required_seals:
        os._exit(83)
    archive_status = os.fstat(archive_fd)
    if archive_status.st_size != expected_archive_size:
        os._exit(84)
    digest = hashlib.sha256()
    offset = 0
    while offset < archive_status.st_size:
        chunk = os.pread(archive_fd, min(1024 * 1024, archive_status.st_size - offset), offset)
        if not chunk:
            os._exit(85)
        digest.update(chunk)
        offset += len(chunk)
    if digest.hexdigest() != expected_archive_sha256:
        os._exit(86)
    if executable_status.st_size != expected_executable_size:
        os._exit(87)
    executable_digest = hashlib.sha256()
    with open("/proc/self/exe", "rb", buffering=0) as executable_stream:
        while True:
            chunk = executable_stream.read(1024 * 1024)
            if not chunk:
                break
            executable_digest.update(chunk)
    if executable_digest.hexdigest() != expected_executable_sha256:
        os._exit(88)
    os.close(executable_fds[0])
    failure_code = 76
    archive_path = "/proc/self/fd/" + str(archive_fd)
    if any(path == repository_root or path.startswith(repository_root + "/") for path in sys.path):
        os._exit(89)
    sys.path.insert(0, archive_path)
    failure_code = 77
    from acfqp import v075_k7_atomic_child_entry_v1 as entry
    failure_code = 78
    code = entry.run_v075_k7_atomic_child_entry_v1(
        archive_fd=input_fds[0],
        transport_profile_fd=input_fds[1],
        lifecycle_profile_fd=input_fds[2],
        successor_profile_fd=input_fds[3],
        request_fd=input_fds[4],
        sealed_secret_fd=input_fds[5],
        channel_fd=channel_fd,
        repository_root=repository_root,
        signer_private_root=signer_private_root,
        signer_private_key_path=signer_private_key_path,
        atomic_parent_execution_spec_id=atomic_parent_execution_spec_id,
    )
except BaseException as error:
    try:
        if channel_fd is None:
            socket_descriptors = []
            for name in os.listdir("/proc/self/fd"):
                try:
                    descriptor = int(name)
                    if descriptor > 2 and stat.S_ISSOCK(os.fstat(descriptor).st_mode):
                        socket_descriptors.append(descriptor)
                except (OSError, ValueError):
                    continue
            if len(socket_descriptors) == 1:
                channel_fd = socket_descriptors[0]
        detail = "BOOTSTRAP_EXCEPTION_TYPE:" + type(error).__name__
        if failure_code in {70, 77}:
            detail += ":MODULE=" + str(getattr(error, "name", None))
            detail += ":FILENAME=" + str(getattr(error, "filename", None))
            detail += ":TRACE=" + "|".join(
                str(frame.lineno) + "@" + frame.name
                for frame in traceback.extract_tb(error.__traceback__)
            )
        if channel_fd is not None:
            os.write(channel_fd, detail.encode("utf-8", errors="backslashreplace"))
    except BaseException:
        pass
    os._exit(failure_code)
os._exit(code)
'''.strip()
BOOTSTRAP_SHA256 = hashlib.sha256(_BOOTSTRAP_SOURCE.encode("utf-8")).hexdigest()


def _canonical_document(raw: bytes, label: str, *, cap: int = MAX_FRAME_BYTES) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > cap:
        _fail(f"{label} bytes are empty, mistyped, or over cap")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V075K7ParentAtomicExecutorV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} must be one canonical JSON object")
    return value


def _source_entry(transport: Any, path: str) -> tuple[str, int]:
    matches = tuple(
        (digest, size)
        for source_path, digest, size in transport.source_entries
        if source_path == path
    )
    if len(matches) != 1:
        _fail(f"sealed source snapshot lacks exact entry {path}")
    return matches[0]


def _read_interpreter() -> tuple[bytes, str]:
    executable = Path(sys.executable).resolve(strict=True)
    raw = executable.read_bytes()
    if not raw or len(raw) > runtime_v1.MAX_EXECUTABLE_BYTES:
        _fail("registered interpreter bytes are unavailable or over cap")
    return raw, hashlib.sha256(raw).hexdigest()


def _secret_size(fd: int) -> int:
    if type(fd) is not int or fd < 0:
        _fail("sealed lifecycle-secret descriptor is invalid")
    try:
        status = os.fstat(fd)
    except OSError as error:
        raise V075K7ParentAtomicExecutorV1Error(
            "sealed lifecycle-secret descriptor is unavailable"
        ) from error
    if (
        not stat.S_ISREG(status.st_mode)
        or status.st_size <= 0
        or status.st_size > runtime_v1.MAX_SEALED_INPUT_BYTES
    ):
        _fail("sealed lifecycle-secret descriptor is invalid")
    return status.st_size


def _path_identity(path: Path, *, directory: bool) -> tuple[int, int, int, int, int, int]:
    try:
        status = os.stat(path, follow_symlinks=False)
    except OSError as error:
        raise V075K7ParentAtomicExecutorV1Error(
            "parent execution path identity is unavailable"
        ) from error
    if (directory and not stat.S_ISDIR(status.st_mode)) or (
        not directory and not stat.S_ISREG(status.st_mode)
    ):
        _fail("parent execution path has the wrong inode type")
    return (
        status.st_dev,
        status.st_ino,
        stat.S_IMODE(status.st_mode),
        status.st_uid,
        status.st_gid,
        status.st_size,
    )


@dataclass(frozen=True, slots=True)
class V075K7AtomicParentExecutionSpecV1:
    """Issuer-owned exact bootstrap, input-role, runtime, and cap identity."""

    _issuer: InitVar[object]
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1 = field(
        repr=False, compare=False
    )
    input_manifest_rows: tuple[bytes, ...] = field(repr=False)
    interpreter_sha256: str
    interpreter_byte_count: int
    parent_source_sha256: str
    parent_source_byte_count: int
    child_source_sha256: str
    child_source_byte_count: int
    repository_root_sha256: str
    signer_private_root_identity: tuple[int, int, int, int, int, int]
    signer_private_key_identity: tuple[int, int, int, int, int, int]
    _spec_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _SPEC_ISSUER
            or type(self.request) is not successor_v1.V075K7ParentOwnedSuccessorRequestV1
        ):
            _fail("atomic parent execution spec is caller-minted or crossed")
        self.request._assert_current()  # noqa: SLF001
        if (
            type(self.input_manifest_rows) is not tuple
            or any(type(row) is not bytes for row in self.input_manifest_rows)
            or any(
                type(identity) is not tuple
                or len(identity) != 6
                or any(type(value) is not int or value < 0 for value in identity)
                for identity in (
                    self.signer_private_root_identity,
                    self.signer_private_key_identity,
                )
            )
            or child_v1.MAX_EXECUTED_BUSINESS_BUNDLE_BYTES
            + child_v1.MAX_CHILD_FRAME_NONBUSINESS_OVERHEAD_BYTES
            > FIXED_CHILD_OUTPUT_CAP_BYTES
        ):
            _fail("atomic parent execution input manifest is malformed")
        rows = tuple(
            _canonical_document(raw, "atomic parent input manifest row", cap=4096)
            for raw in self.input_manifest_rows
        )
        if tuple(row.get("role") for row in rows) != INPUT_ROLES:
            _fail("atomic parent execution input role order changed")
        for index, row in enumerate(rows):
            expected_fields = (
                {"role", "byte_count", "sha256", "content_digest_serialized"}
                if index < len(INPUT_ROLES) - 1
                else {"role", "byte_count", "commitment_id", "content_digest_serialized"}
            )
            if (
                set(row) != expected_fields
                or type(row["byte_count"]) is not int
                or row["byte_count"] <= 0
                or row["content_digest_serialized"] is not (index < len(INPUT_ROLES) - 1)
            ):
                _fail("atomic parent execution input row is malformed")
        object.__setattr__(
            self,
            "_spec_id",
            _hash(V075_K7_ATOMIC_PARENT_EXECUTION_SPEC_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        request = self.request
        transport = request.profile.accounted_profile.transport_profile
        return {
            "schema": "acfqp.v075_k7_atomic_parent_execution_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "successor_profile_id": request.profile.profile_id,
            "request_id": request.request_id,
            "route_identity_id": request.route_identity.route_identity_id,
            "source_snapshot_id": transport.source_snapshot_id,
            "source_archive_sha256": transport.source_archive_sha256,
            "source_archive_byte_count": transport.source_archive_byte_count,
            "bootstrap_sha256": BOOTSTRAP_SHA256,
            "bootstrap_byte_count": len(_BOOTSTRAP_SOURCE.encode("utf-8")),
            "entry_module": child_v1.ENTRY_MODULE,
            "entry_symbol": child_v1.ENTRY_SYMBOL,
            "parent_source_entry": {
                "path": PARENT_SOURCE_PATH,
                "sha256": self.parent_source_sha256,
                "byte_count": self.parent_source_byte_count,
            },
            "child_source_entry": {
                "path": CHILD_SOURCE_PATH,
                "sha256": self.child_source_sha256,
                "byte_count": self.child_source_byte_count,
            },
            "sealed_interpreter_sha256": self.interpreter_sha256,
            "sealed_interpreter_byte_count": self.interpreter_byte_count,
            "python_flags": ["-I", "-S", "-B", "-c"],
            "argv_schema": [
                "SEALED_INTERPRETER", "-I", "-S", "-B", "-c",
                "BOUND_BOOTSTRAP_BYTES", "SOURCE_ARCHIVE_SHA256",
                "SOURCE_ARCHIVE_BYTE_COUNT", "INTERPRETER_SHA256",
                "INTERPRETER_BYTE_COUNT", "REPOSITORY_ROOT",
                "CHILD_PRIVATE_ROOT", "CHILD_PRIVATE_KEY_PATH",
                "ATOMIC_PARENT_EXECUTION_SPEC_ID",
                "CHILD_PRIVATE_ROOT_INODE_IDENTITY",
                "CHILD_PRIVATE_KEY_INODE_IDENTITY",
            ],
            "base_environment": {
                "LANG": "C",
                "LC_ALL": "C",
                "TZ": "UTC",
            },
            "python_hash_seed_fixed": False,
            "runtime_owned_fd_environment": [
                runtime_v1.CHANNEL_ENV_KEY,
                runtime_v1.INPUT_FDS_ENV_KEY,
            ],
            "input_roles": list(INPUT_ROLES),
            "input_manifest": [
                _canonical_document(raw, "retained atomic parent input row", cap=4096)
                for raw in self.input_manifest_rows
            ],
            "repository_root_path_sha256": self.repository_root_sha256,
            "signer_private_root_inode_identity": list(self.signer_private_root_identity),
            "signer_private_key_inode_identity": list(self.signer_private_key_identity),
            "private_locator_path_or_digest_serialized": False,
            "private_locator_semantics_bound_by_child_loader": False,
            "private_locator_child_bootstrap_inode_recheck": True,
            "private_locator_toctou_free": False,
            "signer_registry_id": request.signer_registry.registry_id,
            "observer_evidence_key_id": request.signer_registry.observer_evidence_key.key_id,
            "deadline_milliseconds": FIXED_DEADLINE_MILLISECONDS,
            "memory_max_bytes": FIXED_MEMORY_MAX_BYTES,
            "child_output_cap_bytes": FIXED_CHILD_OUTPUT_CAP_BYTES,
            "max_executed_business_bundle_bytes": child_v1.MAX_EXECUTED_BUSINESS_BUNDLE_BYTES,
            "max_child_frame_nonbusiness_overhead_bytes": child_v1.MAX_CHILD_FRAME_NONBUSINESS_OVERHEAD_BYTES,
            "worst_case_child_frame_bytes": (
                child_v1.MAX_EXECUTED_BUSINESS_BUNDLE_BYTES
                + child_v1.MAX_CHILD_FRAME_NONBUSINESS_OVERHEAD_BYTES
            ),
            "worst_case_child_frame_within_runtime_output_cap": (
                child_v1.MAX_EXECUTED_BUSINESS_BUNDLE_BYTES
                + child_v1.MAX_CHILD_FRAME_NONBUSINESS_OVERHEAD_BYTES
                <= FIXED_CHILD_OUTPUT_CAP_BYTES
            ),
            "required_clone_flags": runtime_v1.REQUIRED_CLONE_FLAGS,
            "native_trampoline_sha256": runtime_v1.X86_64_TRAMPOLINE_SHA256,
            "child_channel_protocol": "ONE_EOF_DELIMITED_CANONICAL_JSON_DOCUMENT",
            "published_frame_width_bytes": FRAME_WIDTH,
            "published_frame_count": 2,
            "published_frame_roles": [child_v1.FRAME_ROLE, PARENT_FRAME_ROLE],
            "parent_frames_child_bytes_without_reconstruction": True,
            "complete_parent_verifier_code_graph_verified": False,
            "caller_cap_override_allowed": False,
            "caller_bootstrap_authority_allowed": False,
            "v075_103_bootstrap_metadata_used_as_execution_authority": False,
            **_locks(),
        }

    @property
    def spec_id(self) -> str:
        if _hash(V075_K7_ATOMIC_PARENT_EXECUTION_SPEC_V1_DOMAIN, self._payload()) != self._spec_id:
            _fail("atomic parent execution spec changed after freeze")
        return self._spec_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atomic_parent_execution_spec_id": self.spec_id}


def _freeze_execution_spec(
    *,
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
    sealed_secret_fd: int,
    repository_root: Path,
    signer_private_root: Path,
    signer_private_key_path: Path,
    public_inputs: tuple[tuple[str, bytes], ...],
    interpreter_sha256: str,
    interpreter_byte_count: int,
) -> V075K7AtomicParentExecutionSpecV1:
    transport = request.profile.accounted_profile.transport_profile
    parent_digest, parent_size = _source_entry(transport, PARENT_SOURCE_PATH)
    child_digest, child_size = _source_entry(transport, CHILD_SOURCE_PATH)
    live_parent_raw = Path(__file__).read_bytes()
    live_child_raw = Path(child_v1.__file__).read_bytes()
    if (
        hashlib.sha256(live_parent_raw).hexdigest() != parent_digest
        or len(live_parent_raw) != parent_size
        or hashlib.sha256(live_child_raw).hexdigest() != child_digest
        or len(live_child_raw) != child_size
    ):
        _fail("live parent/child executor differs from the sealed source snapshot")
    manifest = [
        {
            "role": role,
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "content_digest_serialized": True,
        }
        for role, raw in public_inputs
    ]
    manifest.append(
        {
            "role": "LIFECYCLE_SECRET",
            "byte_count": _secret_size(sealed_secret_fd),
            "commitment_id": request.sealed_secret_commitment_id,
            "content_digest_serialized": False,
        }
    )
    return V075K7AtomicParentExecutionSpecV1(
        _SPEC_ISSUER,
        request,
        tuple(canonical_json_bytes(row) for row in manifest),
        interpreter_sha256,
        interpreter_byte_count,
        parent_digest,
        parent_size,
        child_digest,
        child_size,
        hashlib.sha256(os.fsencode(repository_root)).hexdigest(),
        _path_identity(signer_private_root, directory=True),
        _path_identity(signer_private_key_path, directory=False),
    )


def _frame(raw: bytes) -> bytes:
    if type(raw) is not bytes or not raw or len(raw) > MAX_FRAME_BYTES:
        _fail("two-frame payload is empty, mistyped, or over cap")
    return f"{len(raw):0{FRAME_WIDTH}x}".encode("ascii") + raw


def _split_two_frames(raw: bytes) -> tuple[bytes, bytes]:
    if type(raw) is not bytes or len(raw) > MAX_TWO_FRAME_BYTES:
        _fail("parent two-frame output is mistyped or over cap")
    parts: list[bytes] = []
    offset = 0
    for _ in range(2):
        end = offset + FRAME_WIDTH
        if end > len(raw):
            _fail("parent two-frame output is truncated")
        header = raw[offset:end]
        try:
            size = int(header, 16)
        except ValueError as error:
            raise V075K7ParentAtomicExecutorV1Error(
                "parent two-frame header is noncanonical"
            ) from error
        if header != f"{size:0{FRAME_WIDTH}x}".encode("ascii") or not 0 < size <= MAX_FRAME_BYTES:
            _fail("parent two-frame header is noncanonical or over cap")
        payload_end = end + size
        if payload_end > len(raw):
            _fail("parent two-frame payload is truncated")
        parts.append(raw[end:payload_end])
        offset = payload_end
    if offset != len(raw):
        _fail("parent two-frame output has trailing bytes or an extra frame")
    return parts[0], parts[1]


def _resource_rows(
    *, runtime_result: runtime_v1.K7AtomicPidfdRunResultV1, output_bytes: int
) -> list[dict[str, Any]]:
    observed = {
        "io.output_bytes": output_bytes,
        "memory.working_bytes_peak": runtime_result.memory_peak_bytes,
        "process.launches": runtime_result.counters.process_launches,
    }
    return [
        {
            "path": path,
            "measurement": (
                {
                    "kind": (
                        "DERIVED_IN_MEMORY_NONFORMAL_FACT"
                        if path == "io.output_bytes"
                        else "OBSERVED_NONFORMAL_RUNTIME_FACT"
                    ),
                    "value": observed[path],
                    "formal_semantic_authority": False,
                }
                if path in observed
                else {
                    "kind": "NOT_AVAILABLE",
                    "reason": "PRODUCTION_SEMANTIC_SOURCE_NOT_CONNECTED",
                }
            ),
        }
        for path in shared_v1.SHARED_RESOURCE_PATHS
    ]


def _suffix_payload(
    *,
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
    spec: V075K7AtomicParentExecutionSpecV1,
    child_document: Mapping[str, Any],
    runtime_result: runtime_v1.K7AtomicPidfdRunResultV1,
    output_bytes: int,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_k7_atomic_parent_accounting_suffix.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frame_index": 2,
        "frame_role": PARENT_FRAME_ROLE,
        "atomic_parent_execution_spec_id": spec.spec_id,
        "successor_profile_id": request.profile.profile_id,
        "request_id": request.request_id,
        "route_identity_id": request.route_identity.route_identity_id,
        "logical_occurrence_id": request.occurrence_mapping.phase3e_logical_occurrence_id,
        "atomic_child_business_frame_id": child_document["atomic_child_business_frame_id"],
        "child_business_bundle_id": child_document["child_business_bundle_id"],
        "runtime_result": runtime_result.to_document(),
        "business_output_eof_before_reap": runtime_result.output_eof_before_reap,
        "child_reaped_before_suffix": True,
        "descendant_scan_before_final_peak": True,
        "final_cgroup_empty_verified": runtime_result.cgroup_empty_verified,
        "final_no_descendants_verified": runtime_result.no_descendants_verified,
        "final_memory_peak_bytes": runtime_result.memory_peak_bytes,
        "shared_resource_paths": _resource_rows(
            runtime_result=runtime_result, output_bytes=output_bytes
        ),
        "shared_resource_path_count": len(shared_v1.SHARED_RESOURCE_PATHS),
        "wrapper_complete_two_frame_output_bytes": output_bytes,
        "wrapper_complete_output_fixed_point_verified": True,
        "parent_suffix_frozen_after_child_validation": True,
        "parent_suffix_frozen_after_runtime_finalization": True,
        "public_replay_used_only_eof_frozen_child_bytes": True,
        "public_replay_after_reap_is_not_business_work": True,
        "loaded_acfqp_graph_completeness_source_authority": (
            "SEALED_CHILD_PROGRAM_SELF_CHECK"
        ),
        "loaded_acfqp_graph_independently_replayed_by_parent": False,
        "private_taint_independently_replayed_by_parent": False,
        "raw_runtime_facts_are_not_counter_records": True,
        **_locks(),
    }


def _render_suffix(
    *,
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
    spec: V075K7AtomicParentExecutionSpecV1,
    child_document: Mapping[str, Any],
    runtime_result: runtime_v1.K7AtomicPidfdRunResultV1,
    output_bytes: int,
) -> bytes:
    payload = _suffix_payload(
        request=request,
        spec=spec,
        child_document=child_document,
        runtime_result=runtime_result,
        output_bytes=output_bytes,
    )
    return canonical_json_bytes(
        {
            **payload,
            "atomic_parent_accounting_suffix_id": _hash(
                V075_K7_ATOMIC_PARENT_ACCOUNTING_SUFFIX_V1_DOMAIN, payload
            ),
        }
    )


def _solve_two_frame_fixed_point(
    *,
    child_raw: bytes,
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
    spec: V075K7AtomicParentExecutionSpecV1,
    child_document: Mapping[str, Any],
    runtime_result: runtime_v1.K7AtomicPidfdRunResultV1,
) -> tuple[bytes, bytes]:
    candidate = 0
    seen: set[int] = set()
    for _ in range(MAX_FIXED_POINT_ITERATIONS):
        if candidate in seen:
            _fail("parent two-frame output fixed point cycled")
        seen.add(candidate)
        suffix = _render_suffix(
            request=request,
            spec=spec,
            child_document=child_document,
            runtime_result=runtime_result,
            output_bytes=candidate,
        )
        output = _frame(child_raw) + _frame(suffix)
        actual = len(output)
        if actual == candidate:
            replayed = _render_suffix(
                request=request,
                spec=spec,
                child_document=child_document,
                runtime_result=runtime_result,
                output_bytes=candidate,
            )
            if replayed != suffix or len(output) > MAX_TWO_FRAME_BYTES:
                _fail("parent two-frame fixed point changed on replay")
            return suffix, output
        candidate = actual
    _fail("parent two-frame output fixed point did not converge")


@dataclass(frozen=True, slots=True)
class V075K7ParentAtomicExecutionResultV1:
    _issuer: InitVar[object]
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1 = field(
        repr=False, compare=False
    )
    spec: V075K7AtomicParentExecutionSpecV1 = field(repr=False, compare=False)
    runtime_result: runtime_v1.K7AtomicPidfdRunResultV1 = field(
        repr=False, compare=False
    )
    child_frame_bytes: bytes = field(repr=False, compare=False)
    suffix_frame_bytes: bytes = field(repr=False, compare=False)
    two_frame_output: bytes = field(repr=False, compare=False)
    _validated_frame_ids: tuple[str, str] = field(init=False, repr=False)
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("atomic parent execution result is caller-minted")
        child_document, suffix_document = verify_v075_k7_parent_atomic_two_frame_output_v1(
            raw=self.two_frame_output,
            request=self.request,
            spec=self.spec,
            runtime_result=self.runtime_result,
        )
        first_raw, second_raw = _split_two_frames(self.two_frame_output)
        if (
            type(self.child_frame_bytes) is not bytes
            or type(self.suffix_frame_bytes) is not bytes
            or self.child_frame_bytes != first_raw
            or self.suffix_frame_bytes != second_raw
        ):
            _fail("atomic parent result frame bytes differ from published output")
        object.__setattr__(
            self,
            "_validated_frame_ids",
            (
                child_document["atomic_child_business_frame_id"],
                suffix_document["atomic_parent_accounting_suffix_id"],
            ),
        )
        object.__setattr__(
            self,
            "_result_id",
            _hash(V075_K7_ATOMIC_PARENT_EXECUTION_RESULT_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_atomic_parent_execution_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "atomic_parent_execution_spec_id": self.spec.spec_id,
            "request_id": self.request.request_id,
            "route_identity_id": self.request.route_identity.route_identity_id,
            "atomic_child_business_frame_id": self._validated_frame_ids[0],
            "atomic_parent_accounting_suffix_id": self._validated_frame_ids[1],
            "two_frame_output_sha256": hashlib.sha256(self.two_frame_output).hexdigest(),
            "two_frame_output_byte_count": len(self.two_frame_output),
            "two_frame_output_in_memory_atomic": True,
            "durable_artifact_commit_claimed": False,
            **_locks(),
        }

    @property
    def result_id(self) -> str:
        if _hash(V075_K7_ATOMIC_PARENT_EXECUTION_RESULT_V1_DOMAIN, self._payload()) != self._result_id:
            _fail("atomic parent execution result changed after issuance")
        return self._result_id

    @property
    def child_frame(self) -> dict[str, Any]:
        return _canonical_document(self.child_frame_bytes, "retained child frame")

    @property
    def suffix_frame(self) -> dict[str, Any]:
        return _canonical_document(self.suffix_frame_bytes, "retained parent suffix")

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atomic_parent_execution_result_id": self.result_id}


@dataclass(frozen=True, slots=True)
class V075K7ParentAtomicFailureV1:
    _issuer: InitVar[object]
    request_id: str
    execution_spec_id: str
    failure_stage: str
    underlying_result_bytes: bytes = field(repr=False)
    raw_child_output: bytes = field(repr=False)
    _failure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _FAILURE_ISSUER or self.failure_stage not in {
            "ADMISSION", "LEASE_ACQUIRE", "CGROUP_LEASE", "PREPARE",
            "ATOMIC_RUNTIME_PREFLIGHT", "ATOMIC_RUNTIME_EXCEPTION",
            "CHILD_EXECUTION", "CHILD_REPLAY", "PARENT_FINALIZATION",
        }:
            _fail("atomic parent failure is caller-minted or has an unknown stage")
        if not (
            type(self.execution_spec_id) is str
            and (
                (
                    len(self.execution_spec_id) == 64
                    and all(character in "0123456789abcdef" for character in self.execution_spec_id)
                )
                or self.execution_spec_id in {
                    "NOT_APPLICABLE_LEASE_NOT_ACQUIRED",
                    "NOT_APPLICABLE_SPEC_NOT_FROZEN",
                }
            )
        ):
            _fail("atomic parent failure has an invalid execution-spec reference")
        if (
            (self.failure_stage == "CGROUP_LEASE")
            != (self.execution_spec_id == "NOT_APPLICABLE_LEASE_NOT_ACQUIRED")
            or (self.failure_stage in {"ADMISSION", "LEASE_ACQUIRE", "PREPARE"})
            != (self.execution_spec_id == "NOT_APPLICABLE_SPEC_NOT_FROZEN")
        ):
            _fail("atomic parent failure crossed its execution-spec applicability")
        _canonical_document(
            self.underlying_result_bytes,
            "atomic parent underlying failure result",
        )
        if type(self.raw_child_output) is not bytes:
            _fail("atomic parent failure raw output is mistyped")
        if self.failure_stage in {
            "ADMISSION", "LEASE_ACQUIRE", "CGROUP_LEASE", "PREPARE",
            "ATOMIC_RUNTIME_PREFLIGHT", "ATOMIC_RUNTIME_EXCEPTION",
        } and self.raw_child_output:
            _fail("prelaunch atomic parent failure cannot retain child output")
        object.__setattr__(
            self,
            "_failure_id",
            _hash(V075_K7_ATOMIC_PARENT_EXECUTION_FAILURE_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_atomic_parent_execution_failure.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "request_id": self.request_id,
            "atomic_parent_execution_spec_id": (
                {
                    "kind": "NOT_APPLICABLE",
                    "reason": (
                        "LEASE_NOT_ACQUIRED"
                        if self.execution_spec_id == "NOT_APPLICABLE_LEASE_NOT_ACQUIRED"
                        else "SPEC_NOT_FROZEN"
                    ),
                }
                if self.execution_spec_id.startswith("NOT_APPLICABLE_")
                else self.execution_spec_id
            ),
            "failure_stage": self.failure_stage,
            "underlying_result": _canonical_document(
                self.underlying_result_bytes,
                "retained atomic parent underlying failure result",
            ),
            "raw_child_output_sha256": hashlib.sha256(self.raw_child_output).hexdigest(),
            "raw_child_output_byte_count": len(self.raw_child_output),
            "raw_child_output_retained_privately": bool(self.raw_child_output),
            "two_frame_output_issued": False,
            "business_cutoff_completed": False,
            "aborted_cutoff_before_reap_verified": False,
            "failure_path_accounting_complete": False,
            "noncertificate_closure_issued": False,
            **_locks(),
        }

    @property
    def failure_id(self) -> str:
        if _hash(V075_K7_ATOMIC_PARENT_EXECUTION_FAILURE_V1_DOMAIN, self._payload()) != self._failure_id:
            _fail("atomic parent failure changed after issuance")
        return self._failure_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atomic_parent_execution_failure_id": self.failure_id}


def _portable_replay(
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
) -> portable_v1.V075K7SuccessorPortableRequestReplayV1:
    old = request.profile.accounted_profile
    transport = old.transport_profile
    lifecycle = old.private_replay_profile
    closure = portable_v1.reconstruct_v075_k7_successor_portable_profile_closure_v1(
        source_archive_raw=transport._archive_bytes,  # noqa: SLF001
        transport_profile_raw=canonical_json_bytes(transport.to_document()),
        lifecycle_profile_raw=canonical_json_bytes(lifecycle.to_document()),
        successor_profile_raw=canonical_json_bytes(request.profile.to_document()),
    )
    return portable_v1.replay_v075_k7_successor_request_bytes_portable_v1(
        raw=request.canonical_bytes,
        profile_closure=closure,
    )


def _internal_failure_detail(stage: str) -> bytes:
    return canonical_json_bytes(
        {
            "schema": "acfqp.v075_k7_parent_internal_failure_detail.v1",
            "schema_version": SCHEMA_VERSION,
            "failure_stage": stage,
            "exception_text_or_private_locator_serialized": False,
            "failure_path_accounting_complete": False,
        }
    )


def _require_success_runtime_result(
    result: runtime_v1.K7AtomicPidfdRunResultV1,
) -> None:
    counters = result.counters
    if (
        result.outcome is not runtime_v1.K7AtomicPidfdOutcomeV1.EXITED
        or result.exit_code != 0
        or result.terminating_signal is not None
        or not result.setup_succeeded
        or result.setup_failure_stage is not None
        or result.setup_errno is not None
        or result.output_truncated
        or not result.output_eof_before_reap
        or result.deadline_milliseconds != FIXED_DEADLINE_MILLISECONDS
        or result.output_cap_bytes != FIXED_CHILD_OUTPUT_CAP_BYTES
        or result.memory_max_bytes != FIXED_MEMORY_MAX_BYTES
        or not result.cgroup_empty_verified
        or not result.no_descendants_verified
        or result.memory_peak_bytes > result.memory_max_bytes
        or counters.process_launches != 1
        or counters.child_output_bytes != len(result.output)
        or counters.captured_output_bytes != len(result.output)
    ):
        _fail("retained atomic runtime result is not one complete success")


def verify_v075_k7_parent_atomic_two_frame_output_v1(
    *,
    raw: bytes,
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
    spec: V075K7AtomicParentExecutionSpecV1,
    runtime_result: runtime_v1.K7AtomicPidfdRunResultV1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Strictly replay the exact two frames against retained parent facts."""

    if (
        type(request) is not successor_v1.V075K7ParentOwnedSuccessorRequestV1
        or type(spec) is not V075K7AtomicParentExecutionSpecV1
        or type(runtime_result) is not runtime_v1.K7AtomicPidfdRunResultV1
        or spec.request is not request
    ):
        _fail("parent two-frame replay requires exact retained authorities")
    _require_success_runtime_result(runtime_result)
    child_raw, suffix_raw = _split_two_frames(raw)
    if child_raw != runtime_result.output:
        _fail("published child frame differs from EOF-frozen runtime bytes")
    replay = _portable_replay(request)
    child_document = child_v1.verify_v075_k7_atomic_child_business_frame_bytes_v1(
        raw=child_raw,
        expected_request_replay=replay,
        expected_atomic_parent_execution_spec_id=spec.spec_id,
    )
    suffix_document = _canonical_document(suffix_raw, "atomic parent suffix")
    expected_suffix = _render_suffix(
        request=request,
        spec=spec,
        child_document=child_document,
        runtime_result=runtime_result,
        output_bytes=len(raw),
    )
    if suffix_raw != expected_suffix:
        _fail("atomic parent suffix differs from retained runtime facts")
    return child_document, suffix_document


def _prepare_bootstrap(
    *,
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
    sealed_secret_fd: int,
    repository_root: Path,
    signer_private_root: Path,
    signer_private_key_path: Path,
) -> tuple[V075K7AtomicParentExecutionSpecV1, runtime_v1.K7SealedBootstrapExecV1]:
    old = request.profile.accounted_profile
    transport = old.transport_profile
    lifecycle = old.private_replay_profile
    public_inputs = (
        ("SOURCE_ARCHIVE", transport._archive_bytes),  # noqa: SLF001
        ("TRANSPORT_PROFILE", canonical_json_bytes(transport.to_document())),
        ("LIFECYCLE_PROFILE", canonical_json_bytes(lifecycle.to_document())),
        ("SUCCESSOR_PROFILE", canonical_json_bytes(request.profile.to_document())),
        ("SUCCESSOR_REQUEST", request.canonical_bytes),
    )
    interpreter_raw, interpreter_sha256 = _read_interpreter()
    if any(
        not path.is_absolute() or path.resolve(strict=True) != path
        for path in (repository_root, signer_private_root, signer_private_key_path)
    ):
        _fail("atomic parent execution paths must be absolute canonical paths")
    runtime_document = transport.runtime_document
    if (
        interpreter_sha256 != runtime_document["executable_sha256"]
        or len(interpreter_raw) != runtime_document["executable_byte_count"]
    ):
        _fail("live interpreter differs from the frozen runtime profile")
    spec = _freeze_execution_spec(
        request=request,
        sealed_secret_fd=sealed_secret_fd,
        repository_root=repository_root,
        signer_private_root=signer_private_root,
        signer_private_key_path=signer_private_key_path,
        public_inputs=public_inputs,
        interpreter_sha256=interpreter_sha256,
        interpreter_byte_count=len(interpreter_raw),
    )
    executable_fd = runtime_v1.create_v075_k7_sealed_memfd_from_bytes_v1(
        raw=interpreter_raw, name="acfqp-k7-parent-interpreter"
    )
    staged_fds: list[int] = []
    try:
        for role, raw in public_inputs:
            staged_fds.append(
                runtime_v1.create_v075_k7_sealed_memfd_from_bytes_v1(
                    raw=raw, name="acfqp-k7-input-" + role.lower()
                )
            )
        bootstrap = runtime_v1.freeze_v075_k7_sealed_bootstrap_exec_v1(
            executable_fd=executable_fd,
            executable_sha256=interpreter_sha256,
            argv=(
                os.fspath(Path(sys.executable).resolve(strict=True)),
                "-I", "-S", "-B", "-c", _BOOTSTRAP_SOURCE,
                transport.source_archive_sha256,
                str(transport.source_archive_byte_count),
                interpreter_sha256,
                str(len(interpreter_raw)),
                os.fspath(repository_root),
                os.fspath(signer_private_root),
                os.fspath(signer_private_key_path),
                spec.spec_id,
                ",".join(str(value) for value in spec.signer_private_root_identity),
                ",".join(str(value) for value in spec.signer_private_key_identity),
            ),
            environment={
                "LANG": "C", "LC_ALL": "C", "TZ": "UTC"
            },
            sealed_input_fds=(*staged_fds, sealed_secret_fd),
        )
        return spec, bootstrap
    finally:
        os.close(executable_fd)
        for fd in staged_fds:
            os.close(fd)


def execute_v075_k7_parent_atomic_attempt_v1(
    *,
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
    delegated_parent_fd: int,
    sealed_lifecycle_secret_fd: int,
    repository_root: Path,
    signer_private_root: Path,
    signer_private_key_path: Path,
) -> (
    V075K7ParentAtomicExecutionResultV1
    | V075K7ParentAtomicFailureV1
):
    """Execute one fixed-cap atomic attempt; callers cannot override its TCB."""

    if (
        type(request) is not successor_v1.V075K7ParentOwnedSuccessorRequestV1
        or not isinstance(repository_root, Path)
        or not isinstance(signer_private_root, Path)
        or not isinstance(signer_private_key_path, Path)
    ):
        _fail("atomic parent attempt received mistyped authorities or paths")
    request._assert_current()  # noqa: SLF001
    lease: lease_v1.K7CgroupAttemptLeaseV1 | None = None
    bootstrap: runtime_v1.K7SealedBootstrapExecV1 | None = None
    spec: V075K7AtomicParentExecutionSpecV1 | None = None
    try:
        try:
            admission_result = admission_v1.probe_v075_k7_os_supervisor_admission_v1(
                delegated_parent_fd=delegated_parent_fd
            )
        except Exception:
            return V075K7ParentAtomicFailureV1(
                _FAILURE_ISSUER,
                request.request_id,
                "NOT_APPLICABLE_SPEC_NOT_FROZEN",
                "ADMISSION",
                _internal_failure_detail("ADMISSION"),
                b"",
            )
        try:
            nonce = lease_v1.official_v075_k7_cgroup_lease_nonce_service_v1().issue(
                request=request,
                admission_result=admission_result,
                delegated_parent_fd=delegated_parent_fd,
            )
            acquired = lease_v1.acquire_v075_k7_cgroup_attempt_lease_v1(
                request=request,
                admission_result=admission_result,
                delegated_parent_fd=delegated_parent_fd,
                nonce_token=nonce,
            )
        except lease_v1.V075K7CgroupLeaseCleanupV1Error:
            raise
        except Exception:
            return V075K7ParentAtomicFailureV1(
                _FAILURE_ISSUER,
                request.request_id,
                "NOT_APPLICABLE_SPEC_NOT_FROZEN",
                "LEASE_ACQUIRE",
                _internal_failure_detail("LEASE_ACQUIRE"),
                b"",
            )
        if type(acquired) is lease_v1.K7CgroupLeasePrelaunchBlockedResultV1:
            return V075K7ParentAtomicFailureV1(
                _FAILURE_ISSUER,
                request.request_id,
                "NOT_APPLICABLE_LEASE_NOT_ACQUIRED",
                "CGROUP_LEASE",
                canonical_json_bytes(acquired.to_document()),
                b"",
            )
        if type(acquired) is not lease_v1.K7CgroupAttemptLeaseV1:
            _fail("cgroup lease acquisition returned an unknown authority")
        lease = acquired
        try:
            spec, bootstrap = _prepare_bootstrap(
                request=request,
                sealed_secret_fd=sealed_lifecycle_secret_fd,
                repository_root=repository_root,
                signer_private_root=signer_private_root,
                signer_private_key_path=signer_private_key_path,
            )
        except (
            runtime_v1.V075K7AtomicPidfdCleanupV1Error,
            lease_v1.V075K7CgroupLeaseCleanupV1Error,
        ):
            raise
        except Exception:
            return V075K7ParentAtomicFailureV1(
                _FAILURE_ISSUER,
                request.request_id,
                "NOT_APPLICABLE_SPEC_NOT_FROZEN",
                "PREPARE",
                _internal_failure_detail("PREPARE"),
                b"",
            )
        try:
            observed = runtime_v1.run_v075_k7_atomic_pidfd_runtime_v1(
                lease=lease,
                bootstrap=bootstrap,
                deadline_milliseconds=FIXED_DEADLINE_MILLISECONDS,
                memory_max_bytes=FIXED_MEMORY_MAX_BYTES,
                output_cap_bytes=FIXED_CHILD_OUTPUT_CAP_BYTES,
            )
        except (
            runtime_v1.V075K7AtomicPidfdCleanupV1Error,
            lease_v1.V075K7CgroupLeaseCleanupV1Error,
        ):
            raise
        except Exception:
            return V075K7ParentAtomicFailureV1(
                _FAILURE_ISSUER,
                request.request_id,
                spec.spec_id,
                "ATOMIC_RUNTIME_EXCEPTION",
                _internal_failure_detail("ATOMIC_RUNTIME_EXCEPTION"),
                b"",
            )
        if type(observed) is runtime_v1.K7AtomicPidfdBlockedResultV1:
            if not lease.closed:
                lease.close()
            if bootstrap is not None and not bootstrap.closed:
                bootstrap.close()
            return V075K7ParentAtomicFailureV1(
                _FAILURE_ISSUER,
                request.request_id,
                spec.spec_id,
                "ATOMIC_RUNTIME_PREFLIGHT",
                canonical_json_bytes(observed.to_document()),
                b"",
            )
        if type(observed) is not runtime_v1.K7AtomicPidfdRunResultV1:
            _fail("atomic runtime returned an unknown result")
        if (
            observed.outcome is not runtime_v1.K7AtomicPidfdOutcomeV1.EXITED
            or observed.exit_code != 0
            or not observed.setup_succeeded
            or observed.output_truncated
            or not observed.output_eof_before_reap
        ):
            return V075K7ParentAtomicFailureV1(
                _FAILURE_ISSUER,
                request.request_id,
                spec.spec_id,
                "CHILD_EXECUTION",
                canonical_json_bytes(observed.to_document()),
                observed.output,
            )
        try:
            replay = _portable_replay(request)
            child_document = child_v1.verify_v075_k7_atomic_child_business_frame_bytes_v1(
                raw=observed.output,
                expected_request_replay=replay,
                expected_atomic_parent_execution_spec_id=spec.spec_id,
            )
        except Exception:
            return V075K7ParentAtomicFailureV1(
                _FAILURE_ISSUER,
                request.request_id,
                spec.spec_id,
                "CHILD_REPLAY",
                canonical_json_bytes(observed.to_document()),
                observed.output,
            )
        try:
            suffix_raw, two_frame = _solve_two_frame_fixed_point(
                child_raw=observed.output,
                request=request,
                spec=spec,
                child_document=child_document,
                runtime_result=observed,
            )
            _canonical_document(suffix_raw, "atomic parent suffix")
            return V075K7ParentAtomicExecutionResultV1(
                _RESULT_ISSUER,
                request,
                spec,
                observed,
                observed.output,
                suffix_raw,
                two_frame,
            )
        except Exception:
            return V075K7ParentAtomicFailureV1(
                _FAILURE_ISSUER,
                request.request_id,
                spec.spec_id,
                "PARENT_FINALIZATION",
                canonical_json_bytes(observed.to_document()),
                observed.output,
            )
    finally:
        if lease is not None and not lease.closed:
            lease.close()
        if bootstrap is not None and not bootstrap.closed:
            bootstrap.close()


__all__ = [
    "BOOTSTRAP_SHA256",
    "FIXED_CHILD_OUTPUT_CAP_BYTES",
    "FIXED_DEADLINE_MILLISECONDS",
    "FIXED_MEMORY_MAX_BYTES",
    "INPUT_ROLES",
    "MAX_FRAME_BYTES",
    "PARENT_FRAME_ROLE",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V075K7AtomicParentExecutionSpecV1",
    "V075K7ParentAtomicExecutionResultV1",
    "V075K7ParentAtomicExecutorV1Error",
    "V075K7ParentAtomicFailureV1",
    "execute_v075_k7_parent_atomic_attempt_v1",
    "verify_v075_k7_parent_atomic_two_frame_output_v1",
]
