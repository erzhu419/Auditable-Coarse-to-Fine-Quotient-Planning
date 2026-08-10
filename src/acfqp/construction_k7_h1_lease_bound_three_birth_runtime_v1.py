"""Lease-bound V19 preparation for the first real three-birth prefix.

This module is deliberately additive.  It consumes no B2-C private API and it
does not reinterpret the historical V15--V18 domains.  The implemented slice
freezes the exact Guardian-V2 handoff, SUPERVISOR-V2/BROKER-V2 images, PID
cells and independent SOCK_SEQPACKET channels before a launch is permitted.

The actual clone path is fail-closed behind the public Guardian-V2 atomic
takeover seam.  Until that seam returns a source-pinned consumed lease and the
full SUPERVISOR -> PIDFD_PROBE -> BROKER observation graph is independently
verified, every three-birth and accounting authority remains false.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import fcntl
import hashlib
import os
from pathlib import Path
import socket
import stat
import threading
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_h1_domain_registry_extension_v19 as domains_v19
from acfqp import construction_k7_h1_guardian_runtime_genesis_v2 as guardian_v2
from acfqp import construction_k7_h1_nested_creator_broker_native_v2 as broker_v2
from acfqp import construction_k7_h1_nested_creator_probe_native_v1 as probe_v1
from acfqp import construction_k7_h1_nested_creator_supervisor_native_v2 as supervisor_v2
from acfqp import phase3e_ids as ids_v1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.62-E-C-E5B-B2-D-V19-THREE-BIRTH"
PROFILE_KEY = "construction_k7_h1_lease_bound_three_birth_runtime_v1"
READINESS = "SOURCE_CLOSED_PRELAUNCH_PREPARATION_PUBLIC_SEAM_REQUIRED"

EXACT_B2A_PREPARED_THROUGH_GUARDIAN_V2_REQUIRED = True
GUARDIAN_V2_PUBLIC_HANDOFF_REQUIRED = True
SOURCE_PINNED_CONSUMER_PREPARATION_PRESENT = True
DURABLE_PRELAUNCH_GRAPH_PRESENT = True
SUPERVISOR_V2_AND_BROKER_V2_IMAGES_FROZEN = True
PID_CELLS_AND_INDEPENDENT_CHANNELS_FROZEN = True
NO_B2C_PRIVATE_API_IMPORTED = True

PUBLIC_ATOMIC_TAKEOVER_SEAM_AVAILABLE = False
PERMIT_CONSUMPTION_PATH_PRESENT = False
CLONE_SYSCALL_PERFORMED = False
ACTUAL_SUPERVISOR_BIRTH_OBSERVED = False
ACTUAL_NESTED_PIDFD_PROBE_BIRTH_OBSERVED = False
ACTUAL_BROKER_BIRTH_OBSERVED = False
CONTROL_SB_SINGLETON_OBSERVED = False
PEAK_READ_PRESENT = False
THREE_BIRTH_PREFIX_AUTHORITY_PRESENT = False
FIVE_BIRTH_PROCESS_AUTHORITY_PRESENT = False
ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT = False
E4_V2_COMPLETION_PRESENT = False
PRODUCTION_SHARED_RESOURCE_RECEIPTS_PRESENT = False
FQ11_COUNTER_COMPLETENESS_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED = False
CURRENT_ACCESS_AUTHORITY_PRESENT = False
FORMAL_V7_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
COUNTER_COMPLETENESS_GATE = "NOT_RUN"
WORKLOAD_ECONOMICS_GATE = "NOT_RUN"

MFD_CLOEXEC = getattr(os, "MFD_CLOEXEC", 0x0001)
MFD_ALLOW_SEALING = getattr(os, "MFD_ALLOW_SEALING", 0x0002)
F_ADD_SEALS = getattr(fcntl, "F_ADD_SEALS", 1033)
F_GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
F_SEAL_SEAL = getattr(fcntl, "F_SEAL_SEAL", 0x0001)
F_SEAL_SHRINK = getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
F_SEAL_GROW = getattr(fcntl, "F_SEAL_GROW", 0x0004)
F_SEAL_WRITE = getattr(fcntl, "F_SEAL_WRITE", 0x0008)
REQUIRED_SEALS = F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE
PID_CELL_BYTES = 4096

# The consumer never guesses or reaches through a private registry.  The
# preparation seam is already public.  The atomic consumption/terminal seam
# remains intentionally absent and is checked separately before any clone.
REQUIRED_GUARDIAN_PREPARATION_SEAM = (
    "register_h1_guardian_runtime_consumer_adapter_v2",
    "prepare_h1_guardian_runtime_consumer_takeover_v2",
    "cancel_h1_guardian_runtime_prepared_takeover_v2",
)
REQUIRED_GUARDIAN_ACTIVATION_SEAM = (
    "consume_h1_guardian_runtime_prepared_takeover_v2",
    "verify_h1_guardian_runtime_consumed_lease_v2",
    "close_h1_guardian_runtime_consumed_lease_v2",
    "fail_h1_guardian_runtime_consumed_lease_v2",
)

_ISSUER = object()
_LOCK = threading.RLock()
_LIVE: dict[int, "_PreparationRecordV1"] = {}
_SOURCE_PATHS = MappingProxyType(
    {
        "three_birth_runtime_v1": Path(__file__).resolve(strict=True),
        "guardian_runtime_v2": Path(guardian_v2.__file__).resolve(strict=True),
        "domain_registry_v19": Path(domains_v19.__file__).resolve(strict=True),
        "supervisor_native_v2": Path(supervisor_v2.__file__).resolve(strict=True),
        "supervisor_native_source_v2": supervisor_v2.SOURCE_PATH,
        "broker_native_v2": Path(broker_v2.__file__).resolve(strict=True),
        "broker_native_source_v2": broker_v2.SOURCE_PATH,
        "probe_native_v1": Path(probe_v1.__file__).resolve(strict=True),
        "phase3e_ids": Path(ids_v1.__file__).resolve(strict=True),
    }
)
_IMPORT_SOURCE_FACTS = MappingProxyType(
    {
        label: (
            path.stat().st_dev,
            path.stat().st_ino,
            path.stat().st_mode,
            path.stat().st_size,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for label, path in _SOURCE_PATHS.items()
    }
)
_EXPECTED_DOMAIN_GLOBALS = MappingProxyType(
    {
        name: getattr(domains_v19, name)
        for name in dir(domains_v19)
        if name.endswith("_DOMAIN")
        or name
        in {
            "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V19",
            "K7_H1_DOMAIN_TAG_EXTENSION_V19",
        }
    }
)
_EXPECTED_ROLE_IMAGES = MappingProxyType(
    {
        "supervisor_role": (
            bytes(supervisor_v2.ROLE_ELF_BYTES),
            supervisor_v2.ELF_BYTE_COUNT,
            supervisor_v2.ELF_SHA256,
        ),
        "broker_role": (
            bytes(broker_v2.ROLE_ELF_BYTES),
            broker_v2.ELF_BYTE_COUNT,
            broker_v2.ELF_SHA256,
        ),
    }
)
_LOCAL_CALLABLES: Mapping[str, tuple[Any, Any, Any, Any]] = MappingProxyType({})
_UPSTREAM_CALLABLES = MappingProxyType(
    {
        ("domains", "extension_content_id_v19"): (
            domains_v19.extension_content_id_v19,
            domains_v19.extension_content_id_v19.__code__,
        ),
        ("ids", "canonical_json_bytes"): (
            ids_v1.canonical_json_bytes,
            ids_v1.canonical_json_bytes.__code__,
        ),
        ("ids", "loads_canonical_json"): (
            ids_v1.loads_canonical_json,
            ids_v1.loads_canonical_json.__code__,
        ),
        ("guardian", "verify_h1_guardian_runtime_permit_handoff_v2"): (
            guardian_v2.verify_h1_guardian_runtime_permit_handoff_v2,
            guardian_v2.verify_h1_guardian_runtime_permit_handoff_v2.__code__,
        ),
        ("guardian", "register_h1_guardian_runtime_consumer_adapter_v2"): (
            guardian_v2.register_h1_guardian_runtime_consumer_adapter_v2,
            guardian_v2.register_h1_guardian_runtime_consumer_adapter_v2.__code__,
        ),
        ("guardian", "prepare_h1_guardian_runtime_consumer_takeover_v2"): (
            guardian_v2.prepare_h1_guardian_runtime_consumer_takeover_v2,
            guardian_v2.prepare_h1_guardian_runtime_consumer_takeover_v2.__code__,
        ),
        ("guardian", "cancel_h1_guardian_runtime_prepared_takeover_v2"): (
            guardian_v2.cancel_h1_guardian_runtime_prepared_takeover_v2,
            guardian_v2.cancel_h1_guardian_runtime_prepared_takeover_v2.__code__,
        ),
        ("guardian", "cancel_h1_guardian_runtime_permit_handoff_v2"): (
            guardian_v2.cancel_h1_guardian_runtime_permit_handoff_v2,
            guardian_v2.cancel_h1_guardian_runtime_permit_handoff_v2.__code__,
        ),
        ("guardian", "verify_h1_guardian_runtime_cancellation_v2"): (
            guardian_v2.verify_h1_guardian_runtime_cancellation_v2,
            guardian_v2.verify_h1_guardian_runtime_cancellation_v2.__code__,
        ),
        ("supervisor", "verify_nested_creator_supervisor_native_image_v2"): (
            supervisor_v2.verify_nested_creator_supervisor_native_image_v2,
            supervisor_v2.verify_nested_creator_supervisor_native_image_v2.__code__,
        ),
        ("supervisor", "create_sealed_nested_creator_supervisor_memfd_v2"): (
            supervisor_v2.create_sealed_nested_creator_supervisor_memfd_v2,
            supervisor_v2.create_sealed_nested_creator_supervisor_memfd_v2.__code__,
        ),
        ("broker", "verify_nested_creator_broker_native_image_v2"): (
            broker_v2.verify_nested_creator_broker_native_image_v2,
            broker_v2.verify_nested_creator_broker_native_image_v2.__code__,
        ),
        ("broker", "create_sealed_nested_creator_broker_memfd_v2"): (
            broker_v2.create_sealed_nested_creator_broker_memfd_v2,
            broker_v2.create_sealed_nested_creator_broker_memfd_v2.__code__,
        ),
    }
)

_DESCRIPTOR_ROLES = (
    "supervisor_role",
    "broker_role",
    "supervisor_pid_cell",
    "broker_pid_cell",
    "supervisor_guardian_channel",
    "supervisor_child_channel",
    "broker_guardian_channel",
    "broker_child_channel",
)
_CHANNEL_PAIRS = (
    ("supervisor_guardian_channel", "supervisor_child_channel"),
    ("broker_guardian_channel", "broker_child_channel"),
)


class ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error(RuntimeError):
    """The V19 prelaunch identity, ordering, owner, or cleanup was crossed."""

    def __init__(
        self,
        message: str,
        *,
        cleanup_handle: "LeaseBoundThreeBirthPreparationV1 | None" = None,
    ) -> None:
        super().__init__(message)
        self.cleanup_handle = cleanup_handle


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error(message)


def _claims() -> dict[str, Any]:
    return {
        "public_atomic_takeover_seam_available": False,
        "permit_consumption_path_present": False,
        "clone_syscall_performed": False,
        "actual_supervisor_birth_observed": False,
        "actual_nested_pidfd_probe_birth_observed": False,
        "actual_broker_birth_observed": False,
        "control_sb_singleton_observed": False,
        "peak_read_present": False,
        "memory_peak_read_count": 0,
        "three_birth_prefix_authority_present": False,
        "five_birth_process_authority_present": False,
        "actual_observed_e3_v2_completion_present": False,
        "e4_v2_completion_present": False,
        "production_shared_resource_receipts_present": False,
        "fq11_counter_completeness_present": False,
        "formal_counter_records_issued": False,
        "formal_work_vector_issued": False,
        "formal_comparison_vector_issued": False,
        "formal_actual_projection_proof_issued": False,
        "current_access_authority_present": False,
        "formal_v7_authority_present": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
    }


def _with_id(
    payload: Mapping[str, Any], *, domain: str, id_field: str
) -> dict[str, Any]:
    result = dict(payload)
    result[id_field] = domains_v19.extension_content_id_v19(domain, payload)
    return result


def _verify_id(
    document: Mapping[str, Any], *, domain: str, id_field: str, label: str
) -> str:
    if type(document) is not dict:
        _fail(f"{label} is not one exact object")
    payload = dict(document)
    supplied = payload.pop(id_field, None)
    if (
        type(supplied) is not str
        or domains_v19.extension_content_id_v19(domain, payload) != supplied
    ):
        _fail(f"{label} content ID changed")
    return supplied


def _source_rows() -> list[dict[str, Any]]:
    rows = []
    for label, path in sorted(_SOURCE_PATHS.items()):
        status = path.stat()
        raw = path.read_bytes()
        observed = (
            status.st_dev,
            status.st_ino,
            status.st_mode,
            status.st_size,
            hashlib.sha256(raw).hexdigest(),
        )
        if observed != _IMPORT_SOURCE_FACTS[label]:
            _fail(f"V19 three-birth source changed after import: {label}")
        rows.append(
            {
                "label": label,
                "sha256": observed[-1],
                "byte_count": observed[3],
            }
        )
    return rows


def _deep_canonical_copy(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = ids_v1.loads_canonical_json(ids_v1.canonical_json_bytes(value))
    if type(copied) is not dict:
        _fail("V19 canonical document copy changed its exact type")
    return copied


def _validate_local_code_closure() -> None:
    """Reject runtime rebinding even when source bytes on disk are unchanged."""

    _source_rows()
    if any(
        getattr(domains_v19, name, None) != expected
        for name, expected in _EXPECTED_DOMAIN_GLOBALS.items()
    ):
        _fail("V19 domain registry globals changed after import")
    upstream_modules = {
        "domains": domains_v19,
        "ids": ids_v1,
        "guardian": guardian_v2,
        "supervisor": supervisor_v2,
        "broker": broker_v2,
    }
    for (module_name, name), (function, code) in _UPSTREAM_CALLABLES.items():
        current = getattr(upstream_modules[module_name], name, None)
        if current is not function or getattr(current, "__code__", None) is not code:
            _fail(f"V19 upstream callable changed after import: {module_name}.{name}")
    for name, (function, code, defaults, kwdefaults) in _LOCAL_CALLABLES.items():
        current = globals().get(name)
        if (
            current is not function
            or getattr(current, "__code__", None) is not code
            or getattr(current, "__defaults__", None) != defaults
            or getattr(current, "__kwdefaults__", None) != kwdefaults
            or getattr(current, "__globals__", None) is not globals()
        ):
            _fail(f"V19 local callable changed after import: {name}")
    for role, (expected_bytes, expected_size, expected_sha256) in (
        _EXPECTED_ROLE_IMAGES.items()
    ):
        module = supervisor_v2 if role == "supervisor_role" else broker_v2
        if (
            type(module.ROLE_ELF_BYTES) is not bytes
            or module.ROLE_ELF_BYTES != expected_bytes
            or module.ELF_BYTE_COUNT != expected_size
            or module.ELF_SHA256 != expected_sha256
        ):
            _fail(f"V19 expected role image globals changed: {role}")


def _public_seam_rows(names: tuple[str, ...]) -> list[dict[str, Any]]:
    exports = set(getattr(guardian_v2, "__all__", ()))
    rows = []
    for name in names:
        value = getattr(guardian_v2, name, None)
        rows.append(
            {
                "name": name,
                "exported": name in exports,
                "callable": callable(value),
                "owned_by_guardian_v2": (
                    callable(value)
                    and getattr(value, "__globals__", None) is guardian_v2.__dict__
                ),
            }
        )
    return rows


def guardian_public_consumer_seam_status_v1() -> dict[str, Any]:
    """Report only exact public-callable availability; never call a private API."""

    _validate_local_code_closure()
    preparation_rows = _public_seam_rows(REQUIRED_GUARDIAN_PREPARATION_SEAM)
    activation_rows = _public_seam_rows(REQUIRED_GUARDIAN_ACTIVATION_SEAM)
    return {
        "schema": "acfqp.k7_h1_guardian_runtime_v2_public_seam_status.v1",
        "required_preparation_names": list(REQUIRED_GUARDIAN_PREPARATION_SEAM),
        "required_activation_names": list(REQUIRED_GUARDIAN_ACTIVATION_SEAM),
        "preparation_rows": preparation_rows,
        "activation_rows": activation_rows,
        "preparation_complete": all(
            row["exported"] and row["callable"] and row["owned_by_guardian_v2"]
            for row in preparation_rows
        ),
        "activation_complete": all(
            row["exported"] and row["callable"] and row["owned_by_guardian_v2"]
            for row in activation_rows
        ),
        "b2c_private_api_imported_or_used": False,
    }


def verify_lease_bound_three_birth_runtime_surface_v1() -> dict[str, Any]:
    """Verify the additive sources, role images, domains and locked boundary."""

    _validate_local_code_closure()
    supervisor = supervisor_v2.verify_nested_creator_supervisor_native_image_v2()
    broker = broker_v2.verify_nested_creator_broker_native_image_v2()
    source_rows = _source_rows()
    if (
        REQUIRED_SEALS != 15
        or PID_CELL_BYTES != supervisor_v2.PID_CELL_BYTES
        or PID_CELL_BYTES != broker_v2.PID_CELL_BYTES
        or supervisor.get("actual_broker_birth_observed") is not False
        or broker.get("broker_created_by_supervisor_observed") is not False
        or any(_claims()[key] != value for key, value in _claims().items())
    ):
        _fail("V19 three-birth registered constants or claim locks changed")
    return {
        "schema": "acfqp.k7_h1_lease_bound_three_birth_runtime_surface.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "readiness": READINESS,
        "source_digests": source_rows,
        "supervisor_v2_elf_sha256": supervisor_v2.ELF_SHA256,
        "broker_v2_elf_sha256": broker_v2.ELF_SHA256,
        "guardian_public_seam": guardian_public_consumer_seam_status_v1(),
        "b2b_v1_imported_or_started": False,
        "b2c_private_api_imported_or_used": False,
        **_claims(),
    }


def _new_pid_cell(name: str) -> int:
    descriptor = os.memfd_create(name, MFD_CLOEXEC | MFD_ALLOW_SEALING)
    try:
        os.ftruncate(descriptor, PID_CELL_BYTES)
        if os.pread(descriptor, PID_CELL_BYTES + 1, 0) != bytes(PID_CELL_BYTES):
            _fail("V19 PID cell is not pristine and exact-width")
        if fcntl.fcntl(descriptor, F_GET_SEALS) != 0:
            _fail("V19 writable PID cell unexpectedly acquired a seal")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _new_seqpacket_pair() -> tuple[int, int]:
    left, right = socket.socketpair(
        socket.AF_UNIX,
        socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC,
    )
    left.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    right.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    return left.detach(), right.detach()


def _fd_fact(descriptor: int, *, role: str) -> dict[str, Any]:
    status = os.fstat(descriptor)
    fact = {
        "role": role,
        "device": status.st_dev,
        "inode": status.st_ino,
        "mode": status.st_mode,
        "byte_count": status.st_size,
        "cloexec": bool(fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC),
    }
    if role in {pair_role for pair in _CHANNEL_PAIRS for pair_role in pair}:
        with socket.socket(fileno=os.dup(descriptor)) as endpoint:
            fact.update(
                {
                    "fd_kind": "AF_UNIX_SOCK_SEQPACKET",
                    "socket_type": endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE),
                    "passcred": endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED),
                }
            )
            if hasattr(socket, "SO_DOMAIN"):
                fact["socket_domain"] = endpoint.getsockopt(
                    socket.SOL_SOCKET, socket.SO_DOMAIN
                )
    elif role in _EXPECTED_ROLE_IMAGES:
        raw = os.pread(descriptor, status.st_size + 1, 0)
        fact.update(
            {
                "fd_kind": "SEALED_ROLE_MEMFD",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "seals": fcntl.fcntl(descriptor, F_GET_SEALS),
            }
        )
    else:
        fact.update(
            {
                "fd_kind": "WRITABLE_PID_CELL_MEMFD",
                "seals": fcntl.fcntl(descriptor, F_GET_SEALS),
                "access_mode": fcntl.fcntl(descriptor, fcntl.F_GETFL)
                & os.O_ACCMODE,
            }
        )
    return fact


def _socket_has_no_queued_bytes(endpoint: socket.socket) -> bool:
    try:
        endpoint.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT)
    except BlockingIOError:
        return True
    return False


def _verify_socket_pair(left_fd: int, right_fd: int, *, label: str) -> None:
    with socket.socket(fileno=os.dup(left_fd)) as left, socket.socket(
        fileno=os.dup(right_fd)
    ) as right:
        for endpoint in (left, right):
            if (
                endpoint.family != socket.AF_UNIX
                or endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
                != socket.SOCK_SEQPACKET
                or endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED) != 1
                or not _socket_has_no_queued_bytes(endpoint)
            ):
                _fail(f"V19 {label} socket properties or queue changed")
        left_marker = b"acfqp-v19-peer-left"
        right_marker = b"acfqp-v19-peer-right"
        try:
            left_received = (
                left.send(left_marker) == len(left_marker)
                and right.recv(64, socket.MSG_DONTWAIT) == left_marker
            )
        except BlockingIOError:
            left_received = False
        if not left_received:
            _fail(f"V19 {label} left-to-right peer identity changed")
        try:
            right_received = (
                right.send(right_marker) == len(right_marker)
                and left.recv(64, socket.MSG_DONTWAIT) == right_marker
            )
        except BlockingIOError:
            right_received = False
        if not right_received:
            _fail(f"V19 {label} right-to-left peer identity changed")
        if not all(_socket_has_no_queued_bytes(endpoint) for endpoint in (left, right)):
            _fail(f"V19 {label} peer proof did not leave an empty channel")


def _verify_prepared_descriptors(descriptors: Mapping[str, int]) -> list[dict[str, Any]]:
    if type(descriptors) is not dict or tuple(descriptors) != _DESCRIPTOR_ROLES:
        _fail("V19 exact eight-role descriptor inventory changed")
    if len(set(descriptors.values())) != len(_DESCRIPTOR_ROLES):
        _fail("V19 prepared descriptor numbers overlap")
    identities = []
    for role in _DESCRIPTOR_ROLES:
        descriptor = descriptors[role]
        status = os.fstat(descriptor)
        identity = (status.st_dev, status.st_ino)
        identities.append(identity)
        if not (fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC):
            _fail(f"V19 prepared descriptor lost CLOEXEC: {role}")
        if role in _EXPECTED_ROLE_IMAGES:
            expected_bytes, expected_size, expected_sha256 = _EXPECTED_ROLE_IMAGES[role]
            raw = os.pread(descriptor, expected_size + 1, 0)
            try:
                link = os.readlink(f"/proc/self/fd/{descriptor}")
            except OSError as error:
                raise ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error(
                    f"V19 cannot identify role memfd: {role}"
                ) from error
            if (
                not stat.S_ISREG(status.st_mode)
                or not link.startswith("/memfd:")
                or status.st_size != expected_size
                or raw != expected_bytes
                or hashlib.sha256(raw).hexdigest() != expected_sha256
                or fcntl.fcntl(descriptor, F_GET_SEALS) != REQUIRED_SEALS
            ):
                _fail(f"V19 exact sealed role image changed: {role}")
        elif role.endswith("_pid_cell"):
            try:
                link = os.readlink(f"/proc/self/fd/{descriptor}")
            except OSError as error:
                raise ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error(
                    f"V19 cannot identify PID-cell memfd: {role}"
                ) from error
            if (
                not stat.S_ISREG(status.st_mode)
                or not link.startswith("/memfd:")
                or status.st_size != PID_CELL_BYTES
                or os.pread(descriptor, PID_CELL_BYTES + 1, 0)
                != bytes(PID_CELL_BYTES)
                or fcntl.fcntl(descriptor, F_GET_SEALS) != 0
                or (fcntl.fcntl(descriptor, fcntl.F_GETFL) & os.O_ACCMODE)
                != os.O_RDWR
            ):
                _fail(f"V19 exact writable pristine PID cell changed: {role}")
        elif not stat.S_ISSOCK(status.st_mode):
            _fail(f"V19 channel descriptor is not a socket: {role}")
    if len(set(identities)) != len(_DESCRIPTOR_ROLES):
        _fail("V19 prepared descriptors do not have eight unique identities")
    for left_role, right_role in _CHANNEL_PAIRS:
        _verify_socket_pair(
            descriptors[left_role],
            descriptors[right_role],
            label=f"{left_role}/{right_role}",
        )
    return [_fd_fact(descriptors[role], role=role) for role in _DESCRIPTOR_ROLES]


def _append_exclusive(
    directory_fd: int,
    *,
    filename: str,
    document: Mapping[str, Any],
) -> bytes:
    raw = ids_v1.canonical_json_bytes(document)
    descriptor = os.open(
        filename,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o600,
        dir_fd=directory_fd,
    )
    try:
        offset = 0
        while offset < len(raw):
            count = os.write(descriptor, raw[offset:])
            if count <= 0:
                _fail("V19 three-birth journal write made no progress")
            offset += count
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.fsync(directory_fd)
    return raw


_TEST_ONLY_JOURNAL_FAULT_AFTER_DURABLE: str | None = None


def _append_or_verify_exclusive(
    directory_fd: int,
    *,
    filename: str,
    document: Mapping[str, Any],
) -> bytes:
    """Create once, or finish forward from the exact durable bytes."""

    expected = ids_v1.canonical_json_bytes(document)
    try:
        raw = _append_exclusive(
            directory_fd, filename=filename, document=document
        )
        if _TEST_ONLY_JOURNAL_FAULT_AFTER_DURABLE == filename:
            raise RuntimeError(f"injected V19 post-durable journal fault: {filename}")
        return raw
    except FileExistsError:
        descriptor = os.open(
            filename,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=directory_fd,
        )
        try:
            status = os.fstat(descriptor)
            raw = os.read(descriptor, status.st_size + 1)
        finally:
            os.close(descriptor)
        if not stat.S_ISREG(status.st_mode) or raw != expected:
            _fail(f"V19 existing journal boundary is not the exact durable record: {filename}")
        return raw


@dataclass(slots=True)
class _PreparationRecordV1:
    handle: "LeaseBoundThreeBirthPreparationV1"
    guardian_handoff: guardian_v2.H1GuardianRuntimePermitHandoffV2
    journal_path: Path
    directory_fd: int
    directory_identity: tuple[int, int]
    owner_pid: int
    owner_thread: threading.Thread
    owner_thread_id: int
    state: str
    documents: dict[str, dict[str, Any]]
    descriptors: dict[str, int]
    descriptor_facts: tuple[dict[str, Any], ...] = ()
    expected_close_rows: tuple[dict[str, Any], ...] = ()
    closed_roles: set[str] = field(default_factory=set)
    adapter: Any = None
    takeover: Any = None
    cancellation_document: dict[str, Any] | None = None
    close_facts: dict[str, Any] | None = None


class LeaseBoundThreeBirthPreparationV1:
    """Issuer-only owner-bound prepared resources; it is not a birth permit."""

    __slots__ = ("_owner_pid", "_owner_thread", "_owner_thread_id", "_issuer")

    def __init__(self, issuer: object) -> None:
        if issuer is not _ISSUER:
            _fail("V19 three-birth preparation is caller-minted")
        self._owner_pid = os.getpid()
        self._owner_thread = threading.current_thread()
        self._owner_thread_id = threading.get_ident()
        self._issuer = issuer

    @property
    def state(self) -> str:
        record = _LIVE.get(id(self))
        if record is not None and record.handle is self:
            return record.state
        return "CLOSED_OR_FORK_POISONED"

    def to_document(self) -> dict[str, Any]:
        record = _require(self)
        return _deep_canonical_copy(record.documents["launch_preparation"])

    def artifact_graph(self) -> dict[str, dict[str, Any]]:
        record = _require(self)
        return {
            key: _deep_canonical_copy(value)
            for key, value in sorted(record.documents.items())
        }

    def __copy__(self) -> NoReturn:
        _fail("V19 three-birth preparation cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("V19 three-birth preparation cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("V19 three-birth preparation cannot be copied or pickled")


def _require(handle: LeaseBoundThreeBirthPreparationV1) -> _PreparationRecordV1:
    if (
        type(handle) is not LeaseBoundThreeBirthPreparationV1
        or handle._issuer is not _ISSUER
        or handle._owner_pid != os.getpid()
        or handle._owner_thread is not threading.current_thread()
        or handle._owner_thread_id != threading.get_ident()
    ):
        _fail("V19 three-birth preparation crossed its exact owner")
    record = _LIVE.get(id(handle))
    if (
        record is None
        or record.handle is not handle
        or record.owner_pid != handle._owner_pid
        or record.owner_thread is not handle._owner_thread
        or record.owner_thread_id != handle._owner_thread_id
        or record.owner_pid != os.getpid()
        or record.owner_thread is not threading.current_thread()
        or record.owner_thread_id != threading.get_ident()
    ):
        _fail("V19 three-birth preparation is not live")
    return record


def prepare_lease_bound_three_birth_v1(
    guardian_handoff: guardian_v2.H1GuardianRuntimePermitHandoffV2,
    *,
    journal_path: str | os.PathLike[str],
) -> LeaseBoundThreeBirthPreparationV1:
    """Freeze all non-cgroup resources and three durable pre-clone records."""

    _validate_local_code_closure()
    verify_lease_bound_three_birth_runtime_surface_v1()
    handoff = guardian_v2.verify_h1_guardian_runtime_permit_handoff_v2(
        guardian_handoff
    )
    if handoff.get("handoff_state") != "HANDOFF_ESCROWED_UNCONSUMED":
        _fail("V19 requires the exact Guardian-V2 unconsumed handoff")
    path = Path(journal_path).resolve()
    status = path.stat()
    if not stat.S_ISDIR(status.st_mode):
        _fail("V19 three-birth journal is not one directory")
    directory_fd = os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    try:
        directory_entries = os.listdir(directory_fd)
        directory_status = os.fstat(directory_fd)
    except BaseException:
        os.close(directory_fd)
        raise
    if directory_entries:
        os.close(directory_fd)
        _fail("V19 three-birth runner journal must be a dedicated empty directory")
    handle = LeaseBoundThreeBirthPreparationV1(_ISSUER)
    record = _PreparationRecordV1(
        handle=handle,
        guardian_handoff=guardian_handoff,
        journal_path=path,
        directory_fd=directory_fd,
        directory_identity=(directory_status.st_dev, directory_status.st_ino),
        owner_pid=os.getpid(),
        owner_thread=threading.current_thread(),
        owner_thread_id=threading.get_ident(),
        state="PREPARING_NO_CLONE",
        documents={},
        descriptors={},
    )
    try:
        with _LOCK:
            if _LIVE:
                _fail("V19 three-birth runtime already owns one preparation")
            _LIVE[id(handle)] = record
        record.descriptors["supervisor_role"] = (
            supervisor_v2.create_sealed_nested_creator_supervisor_memfd_v2()
        )
        record.descriptors["broker_role"] = (
            broker_v2.create_sealed_nested_creator_broker_memfd_v2()
        )
        record.descriptors["supervisor_pid_cell"] = _new_pid_cell(
            "acfqp-v19-supervisor-pid-cell"
        )
        record.descriptors["broker_pid_cell"] = _new_pid_cell(
            "acfqp-v19-broker-pid-cell"
        )
        supervisor_guardian, supervisor_child = _new_seqpacket_pair()
        record.descriptors["supervisor_guardian_channel"] = supervisor_guardian
        record.descriptors["supervisor_child_channel"] = supervisor_child
        broker_guardian, broker_child = _new_seqpacket_pair()
        record.descriptors["broker_guardian_channel"] = broker_guardian
        record.descriptors["broker_child_channel"] = broker_child
        descriptor_facts = _verify_prepared_descriptors(record.descriptors)
        record.descriptor_facts = tuple(
            _deep_canonical_copy(fact) for fact in descriptor_facts
        )
        record.expected_close_rows = tuple(
            {"role": role, "closed": True} for role in reversed(_DESCRIPTOR_ROLES)
        )
        seam = guardian_public_consumer_seam_status_v1()
        if seam["preparation_complete"] is not True:
            _fail("Guardian V2 public preparation seam is incomplete")
        record.adapter = guardian_v2.register_h1_guardian_runtime_consumer_adapter_v2(
            consumer_key=PROFILE_KEY,
            consumer_source_path=Path(__file__).resolve(strict=True),
            consumer_callable=prepare_lease_bound_three_birth_v1,
        )
        source_closure = record.adapter.to_document()
        adapter_id = _verify_id(
            source_closure,
            domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_CONSUMER_ADAPTER_V1_DOMAIN,
            id_field="guardian_runtime_v2_consumer_adapter_id",
            label="Guardian V2 issued consumer adapter",
        )
        launch = _with_id(
            {
                "schema": "acfqp.k7_h1_supervisor_v2_launch_preparation.v1",
                "schema_version": SCHEMA_VERSION,
                "profile_key": PROFILE_KEY,
                "guardian_runtime_v2_public_handoff_id": handoff[
                    "guardian_runtime_v2_public_handoff_id"
                ],
                "guardian_runtime_v2_consumer_adapter_id": adapter_id,
                "supervisor_v2_elf_sha256": supervisor_v2.ELF_SHA256,
                "broker_v2_elf_sha256": broker_v2.ELF_SHA256,
                "descriptor_facts_without_fd_numbers": descriptor_facts,
                "supervisor_pid_cell_pristine": True,
                "broker_pid_cell_pristine": True,
                "all_eight_descriptor_identities_distinct": True,
                "supervisor_and_broker_channels_independent": True,
                "launch_preparation_state": "DURABLE_NO_CLONE",
                "next_legal_action": "PUBLIC_ATOMIC_PERMIT_CONSUMPTION",
                **_claims(),
            },
            domain=domains_v19.CONSTRUCTION_K7_H1_SUPERVISOR_V2_LAUNCH_PREPARATION_V1_DOMAIN,
            id_field="supervisor_v2_launch_preparation_id",
        )
        for index, (name, document) in enumerate(
            (("consumer_adapter", source_closure), ("launch_preparation", launch)),
            start=1,
        ):
            _append_or_verify_exclusive(
                directory_fd,
                filename=f"{index:04d}_{name.upper()}.json",
                document=document,
            )
            record.documents[name] = document
        record.takeover = guardian_v2.prepare_h1_guardian_runtime_consumer_takeover_v2(
            guardian_handoff,
            adapter=record.adapter,
            consumer_preparation_id=adapter_id,
            launch_preparation_id=launch["supervisor_v2_launch_preparation_id"],
        )
        takeover = record.takeover.to_document()
        _append_or_verify_exclusive(
            directory_fd,
            filename="0003_TAKEOVER_PREPARATION.json",
            document=takeover,
        )
        record.documents["takeover_preparation"] = takeover
        record.state = "DURABLE_PREPARED_AWAITING_PUBLIC_ATOMIC_TAKEOVER"
        verify_lease_bound_three_birth_preparation_v1(handle)
        return handle
    except BaseException:
        try:
            abort_lease_bound_three_birth_preparation_v1(handle)
        except BaseException as cleanup_error:
            raise ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error(
                "V19 preparation failed with retryable cleanup",
                cleanup_handle=handle,
            ) from cleanup_error
        raise


def verify_lease_bound_three_birth_preparation_v1(
    handle: LeaseBoundThreeBirthPreparationV1,
) -> dict[str, Any]:
    _validate_local_code_closure()
    record = _require(handle)
    if record.state != "DURABLE_PREPARED_AWAITING_PUBLIC_ATOMIC_TAKEOVER":
        _fail("V19 three-birth preparation is not at the exact pre-clone cut")
    handoff = guardian_v2.verify_h1_guardian_runtime_permit_handoff_v2(
        record.guardian_handoff
    )
    if set(record.documents) != {
        "consumer_adapter",
        "takeover_preparation",
        "launch_preparation",
    } or len(record.descriptors) != 8:
        _fail("V19 prepared artifact or descriptor inventory changed")
    expected_files = {
        "0001_CONSUMER_ADAPTER.json": "consumer_adapter",
        "0002_LAUNCH_PREPARATION.json": "launch_preparation",
        "0003_TAKEOVER_PREPARATION.json": "takeover_preparation",
    }
    directory_status = os.fstat(record.directory_fd)
    if (directory_status.st_dev, directory_status.st_ino) != record.directory_identity:
        _fail("V19 prepared journal directory identity changed")
    observed_files = set(os.listdir(record.directory_fd))
    if observed_files != set(expected_files):
        _fail("V19 prepared journal inventory changed")
    for filename, key in expected_files.items():
        descriptor = os.open(
            filename,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=record.directory_fd,
        )
        try:
            status = os.fstat(descriptor)
            raw = os.read(descriptor, status.st_size + 1)
        finally:
            os.close(descriptor)
        if raw != ids_v1.canonical_json_bytes(record.documents[key]):
            _fail(f"V19 durable journal bytes changed: {filename}")
    ids = {
        "consumer_adapter": _verify_id(
            record.documents["consumer_adapter"],
            domain=domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_CONSUMER_ADAPTER_V1_DOMAIN,
            id_field="guardian_runtime_v2_consumer_adapter_id",
            label="V19 consumer adapter",
        ),
        "takeover_preparation": _verify_id(
            record.documents["takeover_preparation"],
            domain=(
                domains_v19.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_V2_TAKEOVER_PREPARATION_V1_DOMAIN
            ),
            id_field="guardian_runtime_v2_takeover_preparation_id",
            label="V19 takeover preparation",
        ),
        "launch_preparation": _verify_id(
            record.documents["launch_preparation"],
            domain=domains_v19.CONSTRUCTION_K7_H1_SUPERVISOR_V2_LAUNCH_PREPARATION_V1_DOMAIN,
            id_field="supervisor_v2_launch_preparation_id",
            label="V19 launch preparation",
        ),
    }
    launch = record.documents["launch_preparation"]
    if (
        record.documents["takeover_preparation"].get(
            "guardian_runtime_v2_consumer_adapter_id"
        )
        != ids["consumer_adapter"]
        or record.documents["takeover_preparation"].get(
            "launch_preparation_id"
        )
        != ids["launch_preparation"]
        or record.documents["takeover_preparation"].get(
            "guardian_runtime_v2_consumer_adapter_id"
        )
        != ids["consumer_adapter"]
        or launch.get("guardian_runtime_v2_public_handoff_id")
        != handoff.get("guardian_runtime_v2_public_handoff_id")
        or any(launch.get(key) != value for key, value in _claims().items())
    ):
        _fail("V19 prepared identity joins or locked claims changed")
    descriptor_facts = _verify_prepared_descriptors(record.descriptors)
    if (
        descriptor_facts != list(record.descriptor_facts)
        or descriptor_facts != launch.get("descriptor_facts_without_fd_numbers")
        or launch.get("all_eight_descriptor_identities_distinct") is not True
        or launch.get("supervisor_and_broker_channels_independent") is not True
    ):
        _fail("V19 exact eight-descriptor facts changed")
    return {
        "schema": "acfqp.k7_h1_lease_bound_three_birth_preparation_verification.v1",
        "state": record.state,
        "artifact_ids": ids,
        "guardian_runtime_v2_public_handoff_id": handoff[
            "guardian_runtime_v2_public_handoff_id"
        ],
        "descriptor_count": len(record.descriptors),
        "clone_syscall_performed": False,
        "memory_peak_read_count": 0,
        "b2c_private_api_imported_or_used": False,
        **_claims(),
    }


def begin_lease_bound_three_birth_v1(
    handle: LeaseBoundThreeBirthPreparationV1,
) -> NoReturn:
    """Fail closed until the exact public Guardian-V2 seam is installed.

    The function intentionally performs its seam check before reading or
    exporting any retained descriptor.  A later slice replaces this terminal
    guard with public preparation/consume calls and the real three-birth
    protocol; it must not reach through Guardian-V2 internals.
    """

    _validate_local_code_closure()
    verify_lease_bound_three_birth_preparation_v1(handle)
    seam = guardian_public_consumer_seam_status_v1()
    if seam["activation_complete"] is not True:
        raise ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error(
            "Guardian V2 public atomic takeover seam is not installed; no clone occurred",
            cleanup_handle=handle,
        )
    _fail("Guardian V2 public seam exists but the V19 activation adapter is not yet frozen")


def abort_lease_bound_three_birth_preparation_v1(
    handle: LeaseBoundThreeBirthPreparationV1,
) -> dict[str, Any]:
    """Close every prepared FD and cancel the still-unconsumed Guardian handoff."""

    _validate_local_code_closure()
    record = _require(handle)
    record.state = "PRELAUNCH_ABORT_PENDING"
    if not record.expected_close_rows:
        record.expected_close_rows = tuple(
            {"role": role, "closed": True}
            for role in reversed(tuple(record.descriptors))
        )
    for role in reversed(tuple(record.descriptors)):
        descriptor = record.descriptors.pop(role)
        os.close(descriptor)
        record.closed_roles.add(role)
    expected_closed_roles = {
        row["role"] for row in record.expected_close_rows
    }
    if record.closed_roles != expected_closed_roles or record.descriptors:
        _fail("V19 prepared descriptor closure inventory changed")
    if record.cancellation_document is None:
        if record.takeover is not None:
            cancellation = guardian_v2.cancel_h1_guardian_runtime_prepared_takeover_v2(
                record.takeover
            )
        else:
            cancellation = guardian_v2.cancel_h1_guardian_runtime_permit_handoff_v2(
                record.guardian_handoff
            )
        cancel_document = guardian_v2.verify_h1_guardian_runtime_cancellation_v2(
            cancellation
        )
        if (
            type(cancel_document) is not dict
            or type(cancel_document.get("guardian_runtime_v2_cancellation_id"))
            is not str
            or cancel_document.get("terminal_code")
            != "UNCONSUMED_HANDOFF_CANCELLED"
            or cancel_document.get("process_birth_count") != 0
        ):
            _fail("V19 Guardian cancellation verifier returned changed semantics")
        record.cancellation_document = _deep_canonical_copy(cancel_document)
    cancel_document = record.cancellation_document
    if cancel_document is None:
        _fail("V19 typed Guardian cancellation was not retained")
    payload = {
        "schema": "acfqp.k7_h1_three_birth_protocol_failure_closure.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "guardian_runtime_v2_public_handoff_id": record.documents.get(
            "launch_preparation", {}
        ).get(
            "guardian_runtime_v2_public_handoff_id",
            {"kind": "NOT_APPLICABLE", "reason": "PREPARATION_NOT_DURABLE"},
        ),
        "supervisor_v2_launch_preparation_id": record.documents.get(
            "launch_preparation", {}
        ).get(
            "supervisor_v2_launch_preparation_id",
            {"kind": "NOT_APPLICABLE", "reason": "PREPARATION_NOT_DURABLE"},
        ),
        "guardian_runtime_v2_cancellation_id": cancel_document[
            "guardian_runtime_v2_cancellation_id"
        ],
        "guardian_runtime_v2_typed_cancellation": cancel_document,
        "failure_stage": "BEFORE_PUBLIC_ATOMIC_PERMIT_CONSUMPTION",
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": "PROTOCOL_FAILURE",
        "prepared_descriptor_closures": list(record.expected_close_rows),
        "all_prepared_descriptors_closed": len(record.descriptors) == 0,
        "guardian_handoff_cancelled_unconsumed": True,
        "process_birth_count": 0,
        "b2c_private_api_imported_or_used": False,
        **_claims(),
    }
    closure = _with_id(
        payload,
        domain=domains_v19.CONSTRUCTION_K7_H1_THREE_BIRTH_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN,
        id_field="three_birth_protocol_failure_closure_id",
    )
    if record.directory_fd >= 0:
        _append_or_verify_exclusive(
            record.directory_fd,
            filename="0004_PROTOCOL_FAILURE_CLOSURE.json",
            document=closure,
        )
        os.close(record.directory_fd)
        record.directory_fd = -1
    record.close_facts = closure
    record.state = "CLOSED_PRELAUNCH_NONCERTIFICATE"
    with _LOCK:
        _LIVE.pop(id(handle), None)
    return _deep_canonical_copy(closure)


def _after_fork_child() -> None:
    global _LOCK
    for record in tuple(_LIVE.values()):
        for descriptor in tuple(record.descriptors.values()):
            try:
                os.close(descriptor)
            except OSError:
                pass
        record.descriptors.clear()
        if record.directory_fd >= 0:
            try:
                os.close(record.directory_fd)
            except OSError:
                pass
            record.directory_fd = -1
        record.state = "FORK_POISONED"
    _LIVE.clear()
    _LOCK = threading.RLock()


def _freeze_local_callable_closure() -> None:
    global _LOCAL_CALLABLES
    names = (
        "_fail",
        "_claims",
        "_with_id",
        "_verify_id",
        "_source_rows",
        "_deep_canonical_copy",
        "_validate_local_code_closure",
        "_public_seam_rows",
        "guardian_public_consumer_seam_status_v1",
        "verify_lease_bound_three_birth_runtime_surface_v1",
        "_new_pid_cell",
        "_new_seqpacket_pair",
        "_fd_fact",
        "_socket_has_no_queued_bytes",
        "_verify_socket_pair",
        "_verify_prepared_descriptors",
        "_append_exclusive",
        "_append_or_verify_exclusive",
        "_require",
        "prepare_lease_bound_three_birth_v1",
        "verify_lease_bound_three_birth_preparation_v1",
        "begin_lease_bound_three_birth_v1",
        "abort_lease_bound_three_birth_preparation_v1",
        "_after_fork_child",
    )
    _LOCAL_CALLABLES = MappingProxyType(
        {
            name: (
                globals()[name],
                globals()[name].__code__,
                globals()[name].__defaults__,
                (
                    dict(globals()[name].__kwdefaults__)
                    if globals()[name].__kwdefaults__
                    else None
                ),
            )
            for name in names
        }
    )


_freeze_local_callable_closure()


os.register_at_fork(after_in_child=_after_fork_child)


__all__ = tuple(
    sorted(
        name
        for name in globals()
        if (
            name.isupper()
            or name.startswith("LeaseBound")
            or name.startswith("ConstructionK7")
            or name
            in {
                "guardian_public_consumer_seam_status_v1",
                "verify_lease_bound_three_birth_runtime_surface_v1",
                "prepare_lease_bound_three_birth_v1",
                "verify_lease_bound_three_birth_preparation_v1",
                "begin_lease_bound_three_birth_v1",
                "abort_lease_bound_three_birth_preparation_v1",
            }
        )
        and not name.startswith("_")
    )
)
