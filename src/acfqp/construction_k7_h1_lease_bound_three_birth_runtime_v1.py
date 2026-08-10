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
import errno
import fcntl
import hashlib
import os
from pathlib import Path
import signal
import socket
import stat
import sys
import threading
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_h1_domain_registry_extension_v19 as domains_v19
from acfqp import construction_k7_h1_guardian_runtime_genesis_v2 as guardian_v2
from acfqp import construction_k7_h1_nested_creator_broker_native_v2 as broker_v2
from acfqp import construction_k7_h1_nested_creator_probe_native_v1 as probe_v1
from acfqp import construction_k7_h1_nested_creator_supervisor_native_v2 as supervisor_v2
from acfqp import construction_k7_h1_supervisor_v2_prebound_clone_v1 as prebound_v20
from acfqp import phase3e_ids as ids_v1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.62-E-C-E5B-B2-D-V19-THREE-BIRTH"
PROFILE_KEY = "construction_k7_h1_lease_bound_three_birth_runtime_v1"
READINESS = "SOURCE_CLOSED_PREBOUND_CAPSULE_BINDING_NO_CONSUMPTION"

EXACT_B2A_PREPARED_THROUGH_GUARDIAN_V2_REQUIRED = True
GUARDIAN_V2_PUBLIC_HANDOFF_REQUIRED = True
SOURCE_PINNED_CONSUMER_PREPARATION_PRESENT = True
DURABLE_PRELAUNCH_GRAPH_PRESENT = True
SUPERVISOR_V2_AND_BROKER_V2_IMAGES_FROZEN = True
PID_CELLS_AND_INDEPENDENT_CHANNELS_FROZEN = True
NO_B2C_PRIVATE_API_IMPORTED = True
PUBLIC_PREBOUND_CAPSULE_BINDING_SEAM_PRESENT = True
PREBOUND_CAPSULE_DUPLICATE_OWNS_INPUTS = True
PREBOUND_CAPSULE_SOURCE_DESCRIPTORS_RETAINED = True
RAW_DESCRIPTOR_ACCESSOR_PRESENT = False
PREBOUND_BINDING_IS_OWNER_LOCAL_LIVE_TYPED_PROOF_ONLY = True
PREBOUND_BINDING_DURABLE_ARTIFACT_PRESENT = False

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
_PREBOUND_BINDING_ISSUER = object()
_PREBOUND_TERMINAL_ORIGIN_TOKENS = MappingProxyType(
    {
        "LIVE_DUPLICATE_OWNED_PREBOUND_CAPSULE": object(),
        "PREBOUND_CAPSULE_PREPARING": object(),
        "PREBOUND_CAPSULE_CLEANUP_REQUIRED": object(),
    }
)
_LOCK = threading.RLock()
_LIVE: dict[int, "_PreparationRecordV1"] = {}
_RAW_OS_GETRANDOM = os.getrandom
_RAW_PTHREAD_SIGMASK = signal.pthread_sigmask
_RAW_SYS_GETFRAME = sys._getframe  # noqa: SLF001
_EXPECTED_PREBOUND_CAPSULE_TYPE = prebound_v20.H1SupervisorV2PreboundNativeCloneV1
_EXPECTED_PREBOUND_MAX_FRAME_BYTES = prebound_v20.MAX_FRAME_BYTES
_BLOCKABLE_SIGNALS = frozenset(signal.valid_signals()) - {
    signal.SIGKILL,
    signal.SIGSTOP,
}
_STATIC_IDENTITY_GLOBALS = MappingProxyType(
    {
        "_ISSUER": _ISSUER,
        "_PREBOUND_BINDING_ISSUER": _PREBOUND_BINDING_ISSUER,
        "_PREBOUND_TERMINAL_ORIGIN_TOKENS": _PREBOUND_TERMINAL_ORIGIN_TOKENS,
        "_RAW_OS_GETRANDOM": _RAW_OS_GETRANDOM,
        "_RAW_PTHREAD_SIGMASK": _RAW_PTHREAD_SIGMASK,
        "_RAW_SYS_GETFRAME": _RAW_SYS_GETFRAME,
        "_EXPECTED_PREBOUND_CAPSULE_TYPE": _EXPECTED_PREBOUND_CAPSULE_TYPE,
        "_BLOCKABLE_SIGNALS": _BLOCKABLE_SIGNALS,
    }
)
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
        "supervisor_v2_prebound_clone_v1": Path(prebound_v20.__file__).resolve(
            strict=True
        ),
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
        ("prebound", "prepare_h1_supervisor_v2_prebound_native_clone_v1"): (
            prebound_v20.prepare_h1_supervisor_v2_prebound_native_clone_v1,
            prebound_v20.prepare_h1_supervisor_v2_prebound_native_clone_v1.__code__,
        ),
        ("prebound", "verify_h1_supervisor_v2_prebound_native_clone_v1"): (
            prebound_v20.verify_h1_supervisor_v2_prebound_native_clone_v1,
            prebound_v20.verify_h1_supervisor_v2_prebound_native_clone_v1.__code__,
        ),
        ("prebound", "cancel_h1_supervisor_v2_prebound_native_clone_v1"): (
            prebound_v20.cancel_h1_supervisor_v2_prebound_native_clone_v1,
            prebound_v20.cancel_h1_supervisor_v2_prebound_native_clone_v1.__code__,
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


def _restore_signal_mask_finish_forward_v1(
    expected_mask: set[signal.Signals],
) -> None:
    """Restore/read back the mask, then re-raise any deferred interruption."""

    deferred_error: BaseException | None = None
    mismatch_error: BaseException | None = None
    for _attempt in range(3):
        try:
            _RAW_PTHREAD_SIGMASK(signal.SIG_SETMASK, expected_mask)
            observed = _RAW_PTHREAD_SIGMASK(signal.SIG_BLOCK, frozenset())
            if observed == expected_mask:
                if deferred_error is not None:
                    raise deferred_error
                return
            mismatch_error = RuntimeError("signal mask read-back did not match")
        except BaseException as error:  # includes one-shot async interruption
            if error is deferred_error:
                raise
            if deferred_error is None:
                deferred_error = error
    raise ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error(
        "V19 could not prove restoration of the caller signal mask"
    ) from (deferred_error or mismatch_error)


def _close_prepared_descriptors_finish_forward_v1(
    record: "_PreparationRecordV1",
) -> None:
    """Close each source FD through replayable pending ownership state.

    The pending row is installed before the descriptor is removed from the
    active inventory.  Therefore an opcode-level interruption cannot strand a
    closed numeric FD in ``record.descriptors``.  On replay, EBADF or a
    different kernel identity proves that the original authority is already
    gone; a replacement descriptor is deliberately left open.
    """

    old_mask = _RAW_PTHREAD_SIGMASK(signal.SIG_BLOCK, frozenset())
    restore_pending = True
    _RAW_PTHREAD_SIGMASK(signal.SIG_BLOCK, _BLOCKABLE_SIGNALS)
    try:
        roles = tuple(row["role"] for row in record.expected_close_rows)
        for role in roles:
            if role in record.closed_roles:
                record.closing_descriptors.pop(role, None)
                record.descriptors.pop(role, None)
                continue
            pending = record.closing_descriptors.get(role)
            if pending is None:
                descriptor = record.descriptors.get(role)
                if type(descriptor) is not int:
                    _fail(f"V19 source descriptor ownership was lost: {role}")
                status = os.fstat(descriptor)
                pending = (
                    descriptor,
                    status.st_dev,
                    status.st_ino,
                    status.st_mode,
                )
                record.closing_descriptors[role] = pending
            descriptor, device, inode, mode = pending
            active_descriptor = record.descriptors.get(role)
            if active_descriptor is not None:
                if active_descriptor != descriptor:
                    _fail(f"V19 source descriptor number changed: {role}")
                record.descriptors.pop(role)
            try:
                status = os.fstat(descriptor)
            except OSError as error:
                if error.errno != errno.EBADF:
                    raise
            else:
                if (
                    status.st_dev,
                    status.st_ino,
                    status.st_mode,
                ) == (device, inode, mode):
                    try:
                        os.close(descriptor)
                    except OSError as error:
                        if error.errno != errno.EBADF:
                            raise
            record.closed_roles.add(role)
            record.closing_descriptors.pop(role)
    finally:
        try:
            _restore_signal_mask_finish_forward_v1(old_mask)
            restore_pending = False
        finally:
            if restore_pending:
                _restore_signal_mask_finish_forward_v1(old_mask)


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
        "prebound": prebound_v20,
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
    if (
        _RAW_OS_GETRANDOM is not os.getrandom
        or _RAW_PTHREAD_SIGMASK is not signal.pthread_sigmask
        or _RAW_SYS_GETFRAME is not sys._getframe  # noqa: SLF001
        or any(
            globals().get(name) is not expected
            for name, expected in _STATIC_IDENTITY_GLOBALS.items()
        )
        or prebound_v20.H1SupervisorV2PreboundNativeCloneV1
        is not _EXPECTED_PREBOUND_CAPSULE_TYPE
        or prebound_v20.MAX_FRAME_BYTES != _EXPECTED_PREBOUND_MAX_FRAME_BYTES
        or prebound_v20.CLONE_SYSCALL_PERFORMED is not False
        or prebound_v20.NATIVE_ENTRY_INVOKED is not False
    ):
        _fail("V19 prebound-capsule dependency or entropy source changed")


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
        "public_prebound_capsule_binding_seam_present": True,
        "prebound_capsule_duplicate_owns_inputs": True,
        "prebound_capsule_source_descriptors_retained": True,
        "raw_descriptor_accessor_present": False,
        "prebound_binding_is_owner_local_live_typed_proof_only": True,
        "prebound_binding_durable_artifact_present": False,
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
_TEST_ONLY_FAIL_AFTER_PREBOUND_PREPARE = False
_TEST_ONLY_FAIL_DURING_PREBOUND_COMMIT = False


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


@dataclass(frozen=True, slots=True)
class _PreboundLifecycleV1:
    issuer: object | None = None
    state: str = "ABSENT"
    launch_id: str | None = None
    capsule_id: str | None = None
    capsule: Any = None
    binding_bytes: bytes | None = None
    terminal_capsule: Any = None
    cancellation_bytes: bytes | None = None
    terminal_state_before: str | None = None
    terminal_origin_token: object | None = None
    capsule_was_crossed: bool | None = None


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
    owner_native_thread_id: int
    state: str
    documents: dict[str, dict[str, Any]]
    descriptors: dict[str, int]
    descriptor_facts: tuple[dict[str, Any], ...] = ()
    expected_close_rows: tuple[dict[str, Any], ...] = ()
    closed_roles: set[str] = field(default_factory=set)
    closing_descriptors: dict[str, tuple[int, int, int, int]] = field(
        default_factory=dict
    )
    adapter: Any = None
    takeover: Any = None
    cancellation_document: dict[str, Any] | None = None
    close_facts: dict[str, Any] | None = None
    prebound: _PreboundLifecycleV1 = field(default_factory=_PreboundLifecycleV1)


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
        or record.owner_native_thread_id != threading.get_native_id()
        or record.owner_pid != os.getpid()
        or record.owner_thread is not threading.current_thread()
        or record.owner_thread_id != threading.get_ident()
    ):
        _fail("V19 three-birth preparation is not live")
    return record


def _prebound_document_from_bytes_v1(
    raw: bytes | None,
    *,
    label: str,
) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"V19 {label} canonical bytes are absent")
    document = ids_v1.loads_canonical_json(raw)
    if (
        type(document) is not dict
        or ids_v1.canonical_json_bytes(document) != raw
    ):
        _fail(f"V19 {label} canonical bytes changed")
    return document


def _prebound_operation_active_on_ancestor_stack_v1() -> str | None:
    """Return a live ancestor operation without mutable enter/leave flags."""

    frame = _RAW_SYS_GETFRAME(3)
    targets = {
        prepare_lease_bound_three_birth_prebound_clone_v1.__code__: "prepare",
        cancel_lease_bound_three_birth_prebound_clone_v1.__code__: "cancel",
        abort_lease_bound_three_birth_preparation_v1.__code__: "abort",
    }
    try:
        while frame is not None:
            operation = targets.get(frame.f_code)
            if operation is not None and frame.f_globals is globals():
                return operation
            frame = frame.f_back
        return None
    finally:
        del frame


def _reject_reentrant_prebound_operation_v1(
    handle: "LeaseBoundThreeBirthPreparationV1",
) -> None:
    active = _prebound_operation_active_on_ancestor_stack_v1()
    if active is None:
        return
    if active == "prepare":
        message = "V19 prebound operation is forbidden before prebound prepare returns"
    else:
        message = f"V19 prebound operation cannot reenter active {active}"
    raise ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error(
        message,
        cleanup_handle=handle,
    )


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
        owner_native_thread_id=threading.get_native_id(),
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


def _new_outer_nonce_v1() -> bytes:
    nonce = bytearray()
    while len(nonce) < 16:
        chunk = _RAW_OS_GETRANDOM(16 - len(nonce))
        if type(chunk) is not bytes or not chunk:
            _fail("V19 outer-frame nonce source made no exact progress")
        nonce.extend(chunk)
    result = bytes(nonce)
    if len(result) != 16:
        _fail("V19 outer-frame nonce width changed")
    return result


def _outer_frames_v1(nonce: bytes) -> tuple[bytes, bytes, bytes]:
    if type(nonce) is not bytes or len(nonce) != 16:
        _fail("V19 outer-frame nonce is not one exact 128-bit value")
    suffix = nonce.hex().encode("ascii")
    frames = (
        b"ACFQP:EXEC_CELL_WITHDRAWN:v1:" + suffix,
        b"ACFQP:EXEC_GATE_READY:v1:" + suffix,
        b"ACFQP:EXEC_RELEASE:v1:" + suffix,
    )
    if len(set(frames)) != 3 or any(
        not 0 < len(frame) <= prebound_v20.MAX_FRAME_BYTES for frame in frames
    ):
        _fail("V19 exact outer-frame grammar changed")
    return frames


def _prebound_descriptor_join_v1(
    record: _PreparationRecordV1,
    capsule: Mapping[str, Any],
) -> list[dict[str, Any]]:
    launch_facts = record.documents.get("launch_preparation", {}).get(
        "descriptor_facts_without_fd_numbers"
    )
    source_facts = capsule.get("source_fd_facts")
    duplicate_facts = capsule.get("fd_facts")
    if (
        type(launch_facts) is not list
        or type(source_facts) is not list
        or duplicate_facts != source_facts
    ):
        _fail("V19/V20 prebound descriptor fact inventories changed")
    launch_by_role = {
        row.get("role"): row for row in launch_facts if type(row) is dict
    }
    capsule_by_role = {
        row.get("role"): row for row in source_facts if type(row) is dict
    }
    if len(launch_by_role) != 8 or set(capsule_by_role) != {
        "creator_pid_cell_fd",
        "child_gate_fd",
        "child_gate_peer_fd",
        "supervisor_executable_fd",
    }:
        _fail("V19/V20 prebound descriptor roles changed")
    role_join = (
        ("supervisor_pid_cell", "creator_pid_cell_fd"),
        ("supervisor_child_channel", "child_gate_fd"),
        ("supervisor_guardian_channel", "child_gate_peer_fd"),
        ("supervisor_role", "supervisor_executable_fd"),
    )
    rows: list[dict[str, Any]] = []
    for launch_role, capsule_role in role_join:
        launch_fact = launch_by_role.get(launch_role)
        capsule_fact = capsule_by_role.get(capsule_role)
        if type(launch_fact) is not dict or type(capsule_fact) is not dict:
            _fail(f"V19/V20 prebound role join is absent: {launch_role}")
        device = launch_fact.get("device")
        inode = launch_fact.get("inode")
        if (
            type(device) is not int
            or type(inode) is not int
            or capsule_fact.get("device") != device
            or capsule_fact.get("inode") != inode
        ):
            _fail(f"V19/V20 prebound kernel identity crossed: {launch_role}")
        rows.append(
            {
                "launch_role": launch_role,
                "capsule_role": capsule_role,
                "device": device,
                "inode": inode,
            }
        )
    return rows


def _prebound_binding_document_v1(
    record: _PreparationRecordV1,
    capsule: Mapping[str, Any],
    *,
    nonce: bytes,
) -> dict[str, Any]:
    launch = record.documents.get("launch_preparation")
    if type(launch) is not dict:
        _fail("V19 launch preparation is absent from the prebound join")
    launch_id = launch.get("supervisor_v2_launch_preparation_id")
    capsule_id = capsule.get("prebound_native_edge_capsule_id")
    source_id = capsule.get("prebound_native_edge_source_closure_id")
    if not all(type(value) is str and len(value) == 64 for value in (
        launch_id,
        capsule_id,
        source_id,
    )):
        _fail("V19/V20 prebound content identities are absent")
    frames = _outer_frames_v1(nonce)
    expected_frame_facts = [
        {
            "role": role,
            "byte_count": len(frame),
            "sha256": hashlib.sha256(frame).hexdigest(),
        }
        for role, frame in zip(
            (
                "cell_withdrawn_frame",
                "gate_ready_frame",
                "release_frame",
            ),
            frames,
            strict=True,
        )
    ]
    if (
        capsule.get("state") != "PREBOUND_NO_ACTIVATION"
        or capsule.get("frame_facts") != expected_frame_facts
        or capsule.get("supervisor_v2_elf_sha256")
        != launch.get("supervisor_v2_elf_sha256")
        or capsule.get("input_ownership")
        != {
            "caller_retains_original_descriptors": 4,
            "capsule_owns_f_dupfd_cloexec_duplicates": True,
            "duplicates_preserve_kernel_identity": True,
        }
        or capsule.get("raw_descriptor_accessor_present") is not False
        or capsule.get("raw_native_callable_accessor_present") is not False
        or capsule.get("permit_consumption_path_present") is not False
        or capsule.get("native_entry_invoked") is not False
        or capsule.get("clone_syscall_performed") is not False
    ):
        _fail("V19/V20 prebound state, frames, ownership, or claim locks changed")
    return {
        "schema": "acfqp.k7_h1_lease_bound_three_birth_prebound_clone_live_proof.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "content_id": {
            "kind": "NOT_APPLICABLE",
            "reason": "OWNER_LOCAL_LIVE_TYPED_PROOF_NOT_DURABLE_ARTIFACT",
        },
        "owner_local_live_typed_proof_only": True,
        "durable_artifact_present": False,
        "live_launch_and_capsule_handles_required_for_replay": True,
        "binding_state": "LIVE_DUPLICATE_OWNED_PREBOUND_CAPSULE",
        "binding_issuer": PROFILE_KEY,
        "owner_identity": {
            "pid": record.owner_pid,
            "thread_id": record.owner_thread_id,
            "native_thread_id": record.owner_native_thread_id,
        },
        "supervisor_v2_launch_preparation_id": launch_id,
        "prebound_native_edge_source_closure_id": source_id,
        "prebound_native_edge_capsule_id": capsule_id,
        "outer_nonce_hex": nonce.hex(),
        "outer_frame_facts": expected_frame_facts,
        "descriptor_identity_joins": _prebound_descriptor_join_v1(record, capsule),
        "source_descriptors_retained_by_v19": True,
        "capsule_descriptors_are_owned_duplicates": True,
        "duplicate_descriptors_preserve_kernel_identity": True,
        "raw_descriptor_exposed": False,
        "permit_consumed": False,
        "native_entry_invoked": False,
        "clone_syscall_performed": False,
        **_claims(),
    }


def prepare_lease_bound_three_birth_prebound_clone_v1(
    handle: LeaseBoundThreeBirthPreparationV1,
) -> prebound_v20.H1SupervisorV2PreboundNativeCloneV1:
    """Bind V19 originals to a V20 duplicate-owned opaque capsule."""

    _reject_reentrant_prebound_operation_v1(handle)
    _validate_local_code_closure()
    verify_lease_bound_three_birth_preparation_v1(handle)
    with _LOCK:
        record = _require(handle)
        lifecycle = record.prebound
        if lifecycle.state == "LIVE_DUPLICATE_OWNED_PREBOUND_CAPSULE":
            capsule = lifecycle.capsule
            if type(capsule) is not _EXPECTED_PREBOUND_CAPSULE_TYPE:
                _fail("V19 retained prebound capsule type changed")
            verify_lease_bound_three_birth_prebound_clone_binding_v1(
                handle, prebound_capsule=capsule
            )
            return capsule
        if (
            lifecycle.state != "ABSENT"
            or lifecycle.issuer is not None
            or lifecycle.capsule is not None
            or lifecycle.binding_bytes is not None
            or lifecycle.terminal_capsule is not None
            or lifecycle.cancellation_bytes is not None
        ):
            _fail("V19 prebound capsule binding is terminal and cannot be reissued")
        nonce = _new_outer_nonce_v1()
        cell_frame, gate_frame, release_frame = _outer_frames_v1(nonce)
        launch_id = record.documents["launch_preparation"][
            "supervisor_v2_launch_preparation_id"
        ]
        capsule: Any = None
        binding_bytes: bytes | None = None
        old_signal_mask: set[signal.Signals] | None = None
        signal_mask_restore_pending = False
        try:
            record.prebound = _PreboundLifecycleV1(
                issuer=_PREBOUND_BINDING_ISSUER,
                state="PREBOUND_PREPARE_CALL_IN_PROGRESS",
                launch_id=launch_id,
            )
            old_signal_mask = _RAW_PTHREAD_SIGMASK(signal.SIG_BLOCK, frozenset())
            signal_mask_restore_pending = True
            _RAW_PTHREAD_SIGMASK(signal.SIG_BLOCK, _BLOCKABLE_SIGNALS)
            try:
                capsule = (
                    prebound_v20.prepare_h1_supervisor_v2_prebound_native_clone_v1(
                        creator_pid_cell_fd=record.descriptors[
                            "supervisor_pid_cell"
                        ],
                        child_gate_fd=record.descriptors[
                            "supervisor_child_channel"
                        ],
                        child_gate_peer_fd=record.descriptors[
                            "supervisor_guardian_channel"
                        ],
                        supervisor_executable_fd=record.descriptors[
                            "supervisor_role"
                        ],
                        cell_withdrawn_frame=cell_frame,
                        gate_ready_frame=gate_frame,
                        release_frame=release_frame,
                    )
                )
                record.prebound = _PreboundLifecycleV1(
                    issuer=_PREBOUND_BINDING_ISSUER,
                    state="PREBOUND_CAPSULE_PREPARING",
                    launch_id=launch_id,
                    capsule=capsule,
                )
                if _TEST_ONLY_FAIL_AFTER_PREBOUND_PREPARE:
                    raise RuntimeError("injected V19 post-prebound-prepare fault")
                capsule_document = (
                    prebound_v20.verify_h1_supervisor_v2_prebound_native_clone_v1(
                        capsule
                    )
                )
                binding = _prebound_binding_document_v1(
                    record, capsule_document, nonce=nonce
                )
                binding_bytes = ids_v1.canonical_json_bytes(binding)
                capsule_id = binding["prebound_native_edge_capsule_id"]
                if _TEST_ONLY_FAIL_DURING_PREBOUND_COMMIT:
                    raise RuntimeError("injected V19 prebound binding commit fault")
            finally:
                _restore_signal_mask_finish_forward_v1(old_signal_mask)
                signal_mask_restore_pending = False
            record.prebound = _PreboundLifecycleV1(
                issuer=_PREBOUND_BINDING_ISSUER,
                state="LIVE_DUPLICATE_OWNED_PREBOUND_CAPSULE",
                launch_id=launch_id,
                capsule_id=capsule_id,
                capsule=capsule,
                binding_bytes=binding_bytes,
            )
            return capsule
        except BaseException as primary:
            restoration_error: BaseException | None = None
            if signal_mask_restore_pending and old_signal_mask is not None:
                for _restore_attempt in range(2):
                    try:
                        _restore_signal_mask_finish_forward_v1(old_signal_mask)
                    except BaseException as error:
                        restoration_error = error
                    else:
                        signal_mask_restore_pending = False
                        restoration_error = None
                        break
            if type(capsule) is _EXPECTED_PREBOUND_CAPSULE_TYPE:
                cleanup_primary: BaseException | None = None
                try:
                    capsule_cancellation = (
                        prebound_v20.cancel_h1_supervisor_v2_prebound_native_clone_v1(
                            capsule
                        )
                    )
                except prebound_v20.ConstructionK7H1SupervisorV2PreboundCloneV1Error as cleanup_error:
                    cleanup_primary = cleanup_error
                    capsule_cancellation = cleanup_error.cleanup_document
                except BaseException as cleanup_error:  # pragma: no cover - fatal dependency edge
                    cleanup_primary = cleanup_error
                    capsule_cancellation = None
                capsule_id = (
                    capsule_cancellation.get("prebound_native_edge_capsule_id")
                    if type(capsule_cancellation) is dict
                    else None
                )
                if _exact_capsule_cancellation_v1(
                    capsule_cancellation, capsule_id=capsule_id
                ):
                    state_before = record.prebound.state
                    if state_before not in {
                        "PREBOUND_CAPSULE_PREPARING",
                        "LIVE_DUPLICATE_OWNED_PREBOUND_CAPSULE",
                    }:
                        state_before = "PREBOUND_CAPSULE_PREPARING"
                    capsule_was_crossed = (
                        capsule_cancellation.get(
                            "input_integrity_valid_before_cleanup"
                        )
                        is False
                    )
                    tombstone = _prebound_tombstone_v1(
                        launch_id=launch_id,
                        capsule_id=capsule_id,
                        capsule_cancellation=capsule_cancellation,
                        state_before=state_before,
                        capsule_was_crossed=capsule_was_crossed,
                    )
                    record.prebound = _PreboundLifecycleV1(
                        issuer=_PREBOUND_BINDING_ISSUER,
                        state="CANCELLED_DUPLICATES_CLOSED_TOMBSTONED",
                        launch_id=launch_id,
                        capsule_id=capsule_id,
                        binding_bytes=binding_bytes,
                        terminal_capsule=capsule,
                        cancellation_bytes=ids_v1.canonical_json_bytes(tombstone),
                        terminal_state_before=state_before,
                        terminal_origin_token=(
                            _PREBOUND_TERMINAL_ORIGIN_TOKENS[state_before]
                        ),
                        capsule_was_crossed=capsule_was_crossed,
                    )
                else:
                    record.prebound = _PreboundLifecycleV1(
                        issuer=_PREBOUND_BINDING_ISSUER,
                        state="PREBOUND_CAPSULE_CLEANUP_REQUIRED",
                        launch_id=launch_id,
                        capsule=capsule,
                        binding_bytes=binding_bytes,
                    )
            else:
                record.prebound = _PreboundLifecycleV1()
            raise ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error(
                (
                    "V19 failed to establish the duplicate-owned prebound capsule"
                    if not signal_mask_restore_pending
                    else "V19 prebound failure cleanup could not prove signal-mask restoration"
                ),
                cleanup_handle=handle,
            ) from (restoration_error or primary)


def verify_lease_bound_three_birth_prebound_clone_binding_v1(
    handle: LeaseBoundThreeBirthPreparationV1,
    *,
    prebound_capsule: prebound_v20.H1SupervisorV2PreboundNativeCloneV1,
) -> dict[str, Any]:
    """Replay the owner, launch/capsule IDs, frames, and four FD joins."""

    _validate_local_code_closure()
    verify_lease_bound_three_birth_preparation_v1(handle)
    with _LOCK:
        record = _require(handle)
        lifecycle = record.prebound
        if (
            type(prebound_capsule) is not _EXPECTED_PREBOUND_CAPSULE_TYPE
            or lifecycle.issuer is not _PREBOUND_BINDING_ISSUER
            or lifecycle.state
            != "LIVE_DUPLICATE_OWNED_PREBOUND_CAPSULE"
            or lifecycle.capsule is not prebound_capsule
            or lifecycle.terminal_capsule is not None
            or lifecycle.cancellation_bytes is not None
        ):
            _fail("V19 prebound capsule is not live under its exact binding")
        binding_document = _prebound_document_from_bytes_v1(
            lifecycle.binding_bytes,
            label="live prebound binding",
        )
        capsule = prebound_v20.verify_h1_supervisor_v2_prebound_native_clone_v1(
            prebound_capsule
        )
        nonce_hex = binding_document.get("outer_nonce_hex")
        if type(nonce_hex) is not str or len(nonce_hex) != 32:
            _fail("V19 retained outer nonce changed")
        try:
            nonce = bytes.fromhex(nonce_hex)
        except ValueError as error:
            raise ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error(
                "V19 retained outer nonce is not hexadecimal"
            ) from error
        expected = _prebound_binding_document_v1(record, capsule, nonce=nonce)
        if ids_v1.canonical_json_bytes(expected) != lifecycle.binding_bytes:
            _fail("V19 live prebound binding document changed")
        return _deep_canonical_copy(expected)


def _exact_capsule_cancellation_v1(
    cancellation: Any,
    *,
    capsule_id: str,
) -> bool:
    return (
        type(cancellation) is dict
        and type(capsule_id) is str
        and len(capsule_id) == 64
        and cancellation.get("prebound_native_edge_capsule_id") == capsule_id
        and cancellation.get("all_capsule_owned_resources_closed") is True
        and cancellation.get("permit_consumed") is False
        and cancellation.get("native_entry_invoked") is False
        and cancellation.get("clone_syscall_performed") is False
        and cancellation.get("actual_process_birth_present") is False
        and type(cancellation.get("input_integrity_valid_before_cleanup")) is bool
    )


def _prebound_tombstone_v1(
    *,
    launch_id: str,
    capsule_id: str,
    capsule_cancellation: Mapping[str, Any],
    state_before: str,
    capsule_was_crossed: bool,
) -> dict[str, Any]:
    if (
        type(launch_id) is not str
        or len(launch_id) != 64
        or type(state_before) is not str
        or type(capsule_was_crossed) is not bool
        or capsule_was_crossed
        is not (
            capsule_cancellation.get("input_integrity_valid_before_cleanup")
            is False
        )
        or not _exact_capsule_cancellation_v1(
            capsule_cancellation, capsule_id=capsule_id
        )
    ):
        _fail("V19 cannot issue a prebound tombstone without exact closure")
    return {
        "schema": "acfqp.k7_h1_lease_bound_three_birth_prebound_clone_live_tombstone.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "content_id": {
            "kind": "NOT_APPLICABLE",
            "reason": "OWNER_LOCAL_LIVE_TYPED_WRAPPER_AROUND_V20_CANCELLATION",
        },
        "owner_local_live_typed_proof_only": True,
        "durable_artifact_present": False,
        "binding_state_before": state_before,
        "binding_state_after": "CANCELLED_DUPLICATES_CLOSED_TOMBSTONED",
        "supervisor_v2_launch_preparation_id": launch_id,
        "prebound_native_edge_capsule_id": capsule_id,
        "prebound_native_edge_cancellation": dict(capsule_cancellation),
        "capsule_duplicates_closed_before_v19_source_release": True,
        "capsule_was_crossed_before_cancellation": capsule_was_crossed,
        "source_descriptors_retained_by_v19": True,
        "permit_consumed": False,
        "native_entry_invoked": False,
        "clone_syscall_performed": False,
        **_claims(),
    }


def _authoritative_launch_preparation_v1(
    record: _PreparationRecordV1,
) -> tuple[dict[str, Any], str]:
    """Rejoin terminal live state to the durable V19 launch record."""

    launch = record.documents.get("launch_preparation")
    if type(launch) is not dict or record.directory_fd < 0:
        _fail("V19 authoritative launch preparation is unavailable")
    launch_id = _verify_id(
        launch,
        domain=(
            domains_v19.CONSTRUCTION_K7_H1_SUPERVISOR_V2_LAUNCH_PREPARATION_V1_DOMAIN
        ),
        id_field="supervisor_v2_launch_preparation_id",
        label="V19 authoritative launch preparation",
    )
    descriptor = os.open(
        "0002_LAUNCH_PREPARATION.json",
        os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
        dir_fd=record.directory_fd,
    )
    try:
        status = os.fstat(descriptor)
        raw = os.read(descriptor, status.st_size + 1)
    finally:
        os.close(descriptor)
    if (
        not stat.S_ISREG(status.st_mode)
        or raw != ids_v1.canonical_json_bytes(launch)
    ):
        _fail("V19 authoritative launch preparation bytes changed")
    return launch, launch_id


def _verify_terminal_prebound_binding_v1(
    record: _PreparationRecordV1,
    lifecycle: _PreboundLifecycleV1,
) -> None:
    """Replay the exact live-binding schema retained by a terminal state."""

    state_before = lifecycle.terminal_state_before
    if lifecycle.binding_bytes is None:
        if state_before == "LIVE_DUPLICATE_OWNED_PREBOUND_CAPSULE":
            _fail("V19 terminal live binding bytes are absent")
        return
    binding = _prebound_document_from_bytes_v1(
        lifecycle.binding_bytes,
        label="terminal retained prebound binding",
    )
    nonce_hex = binding.get("outer_nonce_hex")
    source_id = binding.get("prebound_native_edge_source_closure_id")
    if (
        type(nonce_hex) is not str
        or len(nonce_hex) != 32
        or type(source_id) is not str
        or len(source_id) != 64
        or any(character not in "0123456789abcdef" for character in source_id)
    ):
        _fail("V19 terminal retained binding identities changed")
    try:
        nonce = bytes.fromhex(nonce_hex)
    except ValueError as error:
        raise ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error(
            "V19 terminal retained nonce is not hexadecimal"
        ) from error
    if len(nonce) != 16:
        _fail("V19 terminal retained nonce width changed")
    launch, _launch_id = _authoritative_launch_preparation_v1(record)
    launch_facts = launch.get("descriptor_facts_without_fd_numbers")
    if type(launch_facts) is not list:
        _fail("V19 terminal retained descriptor facts are absent")
    launch_by_role = {
        row.get("role"): row for row in launch_facts if type(row) is dict
    }
    role_join = (
        ("supervisor_pid_cell", "creator_pid_cell_fd"),
        ("supervisor_child_channel", "child_gate_fd"),
        ("supervisor_guardian_channel", "child_gate_peer_fd"),
        ("supervisor_role", "supervisor_executable_fd"),
    )
    source_facts: list[dict[str, Any]] = []
    for launch_role, capsule_role in role_join:
        row = launch_by_role.get(launch_role)
        if (
            type(row) is not dict
            or type(row.get("device")) is not int
            or type(row.get("inode")) is not int
        ):
            _fail(f"V19 terminal retained role join changed: {launch_role}")
        source_facts.append(
            {
                "role": capsule_role,
                "device": row["device"],
                "inode": row["inode"],
            }
        )
    frames = _outer_frames_v1(nonce)
    frame_facts = [
        {
            "role": role,
            "byte_count": len(frame),
            "sha256": hashlib.sha256(frame).hexdigest(),
        }
        for role, frame in zip(
            ("cell_withdrawn_frame", "gate_ready_frame", "release_frame"),
            frames,
            strict=True,
        )
    ]
    capsule_projection = {
        "state": "PREBOUND_NO_ACTIVATION",
        "prebound_native_edge_capsule_id": lifecycle.capsule_id,
        "prebound_native_edge_source_closure_id": source_id,
        "frame_facts": frame_facts,
        "supervisor_v2_elf_sha256": launch.get("supervisor_v2_elf_sha256"),
        "input_ownership": {
            "caller_retains_original_descriptors": 4,
            "capsule_owns_f_dupfd_cloexec_duplicates": True,
            "duplicates_preserve_kernel_identity": True,
        },
        "source_fd_facts": source_facts,
        "fd_facts": source_facts,
        "raw_descriptor_accessor_present": False,
        "raw_native_callable_accessor_present": False,
        "permit_consumption_path_present": False,
        "native_entry_invoked": False,
        "clone_syscall_performed": False,
    }
    expected = _prebound_binding_document_v1(
        record,
        capsule_projection,
        nonce=nonce,
    )
    if ids_v1.canonical_json_bytes(expected) != lifecycle.binding_bytes:
        _fail("V19 terminal retained live-binding schema changed")


def _verify_prebound_tombstone_v1(
    record: _PreparationRecordV1,
    prebound_capsule: prebound_v20.H1SupervisorV2PreboundNativeCloneV1,
) -> dict[str, Any]:
    lifecycle = record.prebound
    if (
        lifecycle.issuer is not _PREBOUND_BINDING_ISSUER
        or lifecycle.state
        != "CANCELLED_DUPLICATES_CLOSED_TOMBSTONED"
        or lifecycle.terminal_capsule is not prebound_capsule
        or lifecycle.capsule is not None
    ):
        _fail("V19 prebound tombstone ownership changed")
    document = _prebound_document_from_bytes_v1(
        lifecycle.cancellation_bytes,
        label="prebound terminal tombstone",
    )
    nested = document.get("prebound_native_edge_cancellation")
    capsule_id = document.get("prebound_native_edge_capsule_id")
    replayed = prebound_v20.cancel_h1_supervisor_v2_prebound_native_clone_v1(
        prebound_capsule
    )
    state_before = lifecycle.terminal_state_before
    capsule_was_crossed = lifecycle.capsule_was_crossed
    _launch, authoritative_launch_id = _authoritative_launch_preparation_v1(record)
    if (
        type(lifecycle.launch_id) is not str
        or lifecycle.launch_id != authoritative_launch_id
        or type(lifecycle.capsule_id) is not str
        or lifecycle.capsule_id != capsule_id
        or type(state_before) is not str
        or state_before
        not in {
            "LIVE_DUPLICATE_OWNED_PREBOUND_CAPSULE",
            "PREBOUND_CAPSULE_PREPARING",
            "PREBOUND_CAPSULE_CLEANUP_REQUIRED",
        }
        or type(capsule_was_crossed) is not bool
        or lifecycle.terminal_origin_token
        is not _PREBOUND_TERMINAL_ORIGIN_TOKENS.get(state_before)
        or document.get("binding_state_before") != state_before
        or document.get("capsule_was_crossed_before_cancellation")
        is not capsule_was_crossed
        or ids_v1.canonical_json_bytes(replayed)
        != ids_v1.canonical_json_bytes(nested)
        or not _exact_capsule_cancellation_v1(nested, capsule_id=capsule_id)
    ):
        _fail("V19 prebound tombstone semantics changed")
    _verify_terminal_prebound_binding_v1(record, lifecycle)
    expected = _prebound_tombstone_v1(
        launch_id=lifecycle.launch_id,
        capsule_id=lifecycle.capsule_id,
        capsule_cancellation=replayed,
        state_before=state_before,
        capsule_was_crossed=capsule_was_crossed,
    )
    if ids_v1.canonical_json_bytes(expected) != lifecycle.cancellation_bytes:
        _fail("V19 prebound tombstone contains unknown or changed fields")
    return expected


def _cancel_prebound_clone_v1(
    record: _PreparationRecordV1,
    prebound_capsule: prebound_v20.H1SupervisorV2PreboundNativeCloneV1,
) -> tuple[dict[str, Any], BaseException | None]:
    lifecycle = record.prebound
    if (
        lifecycle.state == "CANCELLED_DUPLICATES_CLOSED_TOMBSTONED"
        and lifecycle.terminal_capsule is prebound_capsule
        and lifecycle.cancellation_bytes is not None
    ):
        return _verify_prebound_tombstone_v1(record, prebound_capsule), None
    if (
        type(prebound_capsule) is not _EXPECTED_PREBOUND_CAPSULE_TYPE
        or lifecycle.issuer is not _PREBOUND_BINDING_ISSUER
        or lifecycle.state
        != "LIVE_DUPLICATE_OWNED_PREBOUND_CAPSULE"
        or lifecycle.capsule is not prebound_capsule
        or type(lifecycle.launch_id) is not str
        or type(lifecycle.capsule_id) is not str
    ):
        _fail("V19 cannot cancel a capsule outside its exact live binding")
    _verify_terminal_prebound_binding_v1(record, lifecycle)
    binding = _prebound_document_from_bytes_v1(
        lifecycle.binding_bytes,
        label="prebound binding before cancellation",
    )
    if (
        binding.get("supervisor_v2_launch_preparation_id") != lifecycle.launch_id
        or binding.get("prebound_native_edge_capsule_id") != lifecycle.capsule_id
    ):
        _fail("V19 prebound cancellation identity join changed")
    primary: BaseException | None = None
    try:
        capsule_cancellation = (
            prebound_v20.cancel_h1_supervisor_v2_prebound_native_clone_v1(
                prebound_capsule
            )
        )
    except prebound_v20.ConstructionK7H1SupervisorV2PreboundCloneV1Error as error:
        primary = error
        capsule_cancellation = error.cleanup_document
    capsule_id = lifecycle.capsule_id
    if not _exact_capsule_cancellation_v1(
        capsule_cancellation, capsule_id=capsule_id
    ):
        if primary is not None:
            raise ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error(
                "V19 prebound capsule cancellation did not prove duplicate closure",
            ) from primary
        _fail("V19 prebound capsule cancellation semantics changed")
    document = _prebound_tombstone_v1(
        launch_id=lifecycle.launch_id,
        capsule_id=capsule_id,
        capsule_cancellation=capsule_cancellation,
        state_before="LIVE_DUPLICATE_OWNED_PREBOUND_CAPSULE",
        capsule_was_crossed=(
            capsule_cancellation.get("input_integrity_valid_before_cleanup")
            is False
        ),
    )
    record.prebound = _PreboundLifecycleV1(
        issuer=_PREBOUND_BINDING_ISSUER,
        state="CANCELLED_DUPLICATES_CLOSED_TOMBSTONED",
        launch_id=lifecycle.launch_id,
        capsule_id=lifecycle.capsule_id,
        binding_bytes=lifecycle.binding_bytes,
        terminal_capsule=prebound_capsule,
        cancellation_bytes=ids_v1.canonical_json_bytes(document),
        terminal_state_before="LIVE_DUPLICATE_OWNED_PREBOUND_CAPSULE",
        terminal_origin_token=_PREBOUND_TERMINAL_ORIGIN_TOKENS[
            "LIVE_DUPLICATE_OWNED_PREBOUND_CAPSULE"
        ],
        capsule_was_crossed=(
            capsule_cancellation.get("input_integrity_valid_before_cleanup")
            is False
        ),
    )
    return document, primary


def _cancel_partial_prebound_clone_v1(
    record: _PreparationRecordV1,
) -> tuple[dict[str, Any], BaseException | None]:
    lifecycle = record.prebound
    capsule = lifecycle.capsule
    if (
        lifecycle.issuer is not _PREBOUND_BINDING_ISSUER
        or lifecycle.state != "PREBOUND_CAPSULE_CLEANUP_REQUIRED"
        or type(capsule) is not _EXPECTED_PREBOUND_CAPSULE_TYPE
        or type(lifecycle.launch_id) is not str
        or lifecycle.terminal_capsule is not None
    ):
        _fail("V19 partial prebound cleanup ownership changed")
    primary: BaseException | None = None
    try:
        cancellation = prebound_v20.cancel_h1_supervisor_v2_prebound_native_clone_v1(
            capsule
        )
    except prebound_v20.ConstructionK7H1SupervisorV2PreboundCloneV1Error as error:
        primary = error
        cancellation = error.cleanup_document
    capsule_id = (
        cancellation.get("prebound_native_edge_capsule_id")
        if type(cancellation) is dict
        else None
    )
    if not _exact_capsule_cancellation_v1(
        cancellation, capsule_id=capsule_id
    ):
        raise ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error(
            "V19 partial prebound capsule cleanup remains unproven"
        ) from primary
    document = _prebound_tombstone_v1(
        launch_id=lifecycle.launch_id,
        capsule_id=capsule_id,
        capsule_cancellation=cancellation,
        state_before="PREBOUND_CAPSULE_CLEANUP_REQUIRED",
        capsule_was_crossed=(
            cancellation.get("input_integrity_valid_before_cleanup") is False
        ),
    )
    record.prebound = _PreboundLifecycleV1(
        issuer=_PREBOUND_BINDING_ISSUER,
        state="CANCELLED_DUPLICATES_CLOSED_TOMBSTONED",
        launch_id=lifecycle.launch_id,
        capsule_id=capsule_id,
        binding_bytes=lifecycle.binding_bytes,
        terminal_capsule=capsule,
        cancellation_bytes=ids_v1.canonical_json_bytes(document),
        terminal_state_before="PREBOUND_CAPSULE_CLEANUP_REQUIRED",
        terminal_origin_token=_PREBOUND_TERMINAL_ORIGIN_TOKENS[
            "PREBOUND_CAPSULE_CLEANUP_REQUIRED"
        ],
        capsule_was_crossed=(
            cancellation.get("input_integrity_valid_before_cleanup") is False
        ),
    )
    return document, primary


def cancel_lease_bound_three_birth_prebound_clone_v1(
    handle: LeaseBoundThreeBirthPreparationV1,
    *,
    prebound_capsule: prebound_v20.H1SupervisorV2PreboundNativeCloneV1,
) -> dict[str, Any]:
    """Close capsule duplicates first; retain every V19 source for abort."""

    _reject_reentrant_prebound_operation_v1(handle)
    _validate_local_code_closure()
    with _LOCK:
        record = _require(handle)
        document, primary = _cancel_prebound_clone_v1(record, prebound_capsule)
    if primary is not None:
        raise ConstructionK7H1LeaseBoundThreeBirthRuntimeV1Error(
            "V19 crossed prebound capsule was tombstoned after duplicate closure",
            cleanup_handle=handle,
        ) from primary
    return document


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

    _reject_reentrant_prebound_operation_v1(handle)
    _validate_local_code_closure()
    record = _require(handle)
    lifecycle = record.prebound
    if lifecycle.state == "PREBOUND_PREPARE_CALL_IN_PROGRESS":
        if lifecycle.capsule is not None:
            _fail("V19 in-progress prebound state unexpectedly owns a capsule")
        record.prebound = _PreboundLifecycleV1()
        lifecycle = record.prebound
    if lifecycle.state == "PREBOUND_CAPSULE_PREPARING":
        if type(lifecycle.capsule) is not _EXPECTED_PREBOUND_CAPSULE_TYPE:
            _fail("V19 preparing prebound state lost its capsule")
        record.prebound = _PreboundLifecycleV1(
            issuer=lifecycle.issuer,
            state="PREBOUND_CAPSULE_CLEANUP_REQUIRED",
            launch_id=lifecycle.launch_id,
            capsule_id=lifecycle.capsule_id,
            capsule=lifecycle.capsule,
            binding_bytes=lifecycle.binding_bytes,
        )
        lifecycle = record.prebound
    if lifecycle.state == "PREBOUND_CAPSULE_CLEANUP_REQUIRED":
        _cancel_partial_prebound_clone_v1(record)
        lifecycle = record.prebound
    if lifecycle.state == "LIVE_DUPLICATE_OWNED_PREBOUND_CAPSULE":
        capsule = lifecycle.capsule
        if type(capsule) is not _EXPECTED_PREBOUND_CAPSULE_TYPE:
            _fail("V19 live prebound capsule type changed before abort")
        _cancel_prebound_clone_v1(record, capsule)
        lifecycle = record.prebound
    if lifecycle.state == "CANCELLED_DUPLICATES_CLOSED_TOMBSTONED":
        terminal_capsule = lifecycle.terminal_capsule
        if type(terminal_capsule) is not _EXPECTED_PREBOUND_CAPSULE_TYPE:
            _fail("V19 prebound terminal capsule type changed before abort")
        _verify_prebound_tombstone_v1(record, terminal_capsule)
    elif lifecycle.state != "ABSENT":
        _fail("V19 prebound binding did not reach a safe abort cut")
    record.state = "PRELAUNCH_ABORT_PENDING"
    if not record.expected_close_rows:
        record.expected_close_rows = tuple(
            {"role": role, "closed": True}
            for role in reversed(tuple(record.descriptors))
        )
    _close_prepared_descriptors_finish_forward_v1(record)
    expected_closed_roles = {
        row["role"] for row in record.expected_close_rows
    }
    if (
        record.closed_roles != expected_closed_roles
        or record.descriptors
        or record.closing_descriptors
    ):
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
        descriptors = set(record.descriptors.values()) | {
            pending[0] for pending in record.closing_descriptors.values()
        }
        for descriptor in descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass
        record.descriptors.clear()
        record.closing_descriptors.clear()
        record.prebound = _PreboundLifecycleV1(state="FORK_POISONED")
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
        "_restore_signal_mask_finish_forward_v1",
        "_close_prepared_descriptors_finish_forward_v1",
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
        "_prebound_document_from_bytes_v1",
        "_prebound_operation_active_on_ancestor_stack_v1",
        "_reject_reentrant_prebound_operation_v1",
        "prepare_lease_bound_three_birth_v1",
        "verify_lease_bound_three_birth_preparation_v1",
        "_new_outer_nonce_v1",
        "_outer_frames_v1",
        "_prebound_descriptor_join_v1",
        "_prebound_binding_document_v1",
        "_exact_capsule_cancellation_v1",
        "_prebound_tombstone_v1",
        "_authoritative_launch_preparation_v1",
        "_verify_terminal_prebound_binding_v1",
        "_verify_prebound_tombstone_v1",
        "prepare_lease_bound_three_birth_prebound_clone_v1",
        "verify_lease_bound_three_birth_prebound_clone_binding_v1",
        "_cancel_prebound_clone_v1",
        "_cancel_partial_prebound_clone_v1",
        "cancel_lease_bound_three_birth_prebound_clone_v1",
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
                "prepare_lease_bound_three_birth_prebound_clone_v1",
                "verify_lease_bound_three_birth_prebound_clone_binding_v1",
                "cancel_lease_bound_three_birth_prebound_clone_v1",
                "begin_lease_bound_three_birth_v1",
                "abort_lease_bound_three_birth_preparation_v1",
            }
        )
        and not name.startswith("_")
    )
)
