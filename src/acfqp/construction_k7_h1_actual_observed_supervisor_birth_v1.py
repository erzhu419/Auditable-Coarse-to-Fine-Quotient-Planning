"""Bounded H1 B2-C guardian-created SUPERVISOR birth fixture.

The first public phase freezes a sealed, process-local source/RX prebinding
while the exact B2-A runtime is still ``PREPARED_SUCCESSOR``.  A later phase
consumes that live temporal authority together with the exact B2-B RUNNING
session and its one-shot permit.  This module never imports a compiler,
assembler, subprocess launcher, or helper runtime.

Only the registered one-child inert vertical slice is in scope.  Five-birth
E3 V2 completion, E4 V2, production accounting, current-access, V7, and every
official/economics claim remain locked.
"""

from __future__ import annotations

from array import array
import ctypes
from dataclasses import dataclass, field
import errno
import fcntl
import hashlib
import mmap
import os
from pathlib import Path
import select
import signal
import socket
import stat
import struct
import threading
import time
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_h1_domain_registry_extension_v12 as domains_v12
from acfqp import construction_k7_h1_domain_registry_extension_v15 as domains_v15
from acfqp import construction_k7_h1_domain_registry_extension_v16 as domains_v16
from acfqp import construction_k7_h1_domain_registry_extension_v17 as domains_v17
from acfqp import construction_k7_h1_e5a_runtime_lease_successor_v1 as b2a_v1
from acfqp import construction_k7_h1_guardian_runtime_genesis_v1 as b2b_v1
from acfqp import construction_k7_h1_route_wide_working_set_cgroup_v1 as e5a_v1
from acfqp import construction_k7_h1_supervisor_birth_native_v1 as native_v1
from acfqp import phase3e_ids as ids_v1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-E5B-B2-C"
PROFILE_KEY = "construction_k7_h1_actual_observed_supervisor_birth_v1"
READINESS = "BOUNDED_SINGLE_SUPERVISOR_BIRTH_SLICE"

PRE_RUNNING_SEALED_SOURCE_PREBINDING_PRESENT = True
EXACT_B2B_COMPANION_TAKEOVER_PRESENT = True
ONE_SHOT_SUPERVISOR_PERMIT_CONSUMPTION_PRESENT = True
SHARED_PID_CELL_GUARDIAN_SEAL_PRESENT = True
GUARDIAN_CREATOR_PIDFD_SELF_ESCROW_PRESENT = True
EXACT_SINGLE_INERT_SUPERVISOR_BIRTH_PRESENT = True
CONTROL_MEMBERSHIP_TWO_SNAPSHOTS_PRESENT = True
DURABLE_ACK_BEFORE_RELEASE_PRESENT = True
WNOWAIT_AND_DIRECT_REAP_PRESENT = True
SINGLE_CONTENT_ADDRESSED_PEAK_OBSERVATION_PRESENT = True
CONSUMED_B2B_HANDOFF_PRESENT = True
ACTUAL_OBSERVED_E3_V2_IMPLEMENTATION_SLICE1_PRESENT = True

PRODUCTION_FULL_EXECUTION_SOURCE_CLOSURE_PRESENT = False
EXTERNAL_PREREGISTRATION_ANCHOR_PRESENT = False
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
P_PIDFD = getattr(os, "P_PIDFD", 3)
PID_CELL_BYTES = mmap.PAGESIZE
PID_CELL_PID_OFFSET = 0
MAX_PROTOCOL_FRAME_BYTES = 64
MAX_JOURNAL_RECORD_BYTES = 4 * 1024 * 1024
PROTOCOL_TIMEOUT_SECONDS = 10.0
REAP_TIMEOUT_SECONDS = 10.0

_EXPECTED_SOURCE_SHA256 = MappingProxyType(
    {
        "native_module": "a6079a3c8d3a720881d16481af33e71831cdd359cec02ae938e2438d7e9e521a",
        "native_source": native_v1.SOURCE_SHA256,
        "v12": "4506d17182c91cdf68b4449b1026833faecc99cf9585e09db75d8b7c9c483586",
        "b2b": "c3641be8cd43b6a56208d7ed99bd2f687b00a6f3961d0fa0641230497ab4b3cf",
        "b2a": "c4340e95901ba41c9ba686b56a2f81a39958f4bd2003e736524285723cf9d3c4",
        "e5a": "70a32237ba72bf33aa924b65e8b45ee285090dd800ed049e66636e882d969287",
        "v15": "a54493f6431e0a5fa57afdc18bd185802f434ef88d88299285d0e1f40e0e0469",
        "v16": "76c35a2b2967598f303b14c13d531dbe1ef086fbc8ef653fe949e56282035a50",
        "v17": "2541a41749962461cd5bf0e4d545df81cdf7a31740966c37cbd131ad5b1d02c9",
        "phase3e_ids": "3eb435bfec4692961d61b4edf6e067cc128810509b5e35ec1d7348079288c4c2",
    }
)
_SELF_SOURCE_PATH = Path(__file__).resolve(strict=True)
_SELF_IMPORT_STATUS = _SELF_SOURCE_PATH.stat()
_SELF_IMPORT_FACT = MappingProxyType(
    {
        "sha256": hashlib.sha256(_SELF_SOURCE_PATH.read_bytes()).hexdigest(),
        "device": _SELF_IMPORT_STATUS.st_dev,
        "inode": _SELF_IMPORT_STATUS.st_ino,
        "mode": _SELF_IMPORT_STATUS.st_mode,
        "size": _SELF_IMPORT_STATUS.st_size,
    }
)
_SOURCE_PATHS = MappingProxyType(
    {
        "b2c": _SELF_SOURCE_PATH,
        "native_module": Path(native_v1.__file__).resolve(strict=True),
        "native_source": native_v1._SOURCE_PATH,  # noqa: SLF001
        "v12": Path(domains_v12.__file__).resolve(strict=True),
        "b2b": Path(b2b_v1.__file__).resolve(strict=True),
        "b2a": Path(b2a_v1.__file__).resolve(strict=True),
        "e5a": Path(e5a_v1.__file__).resolve(strict=True),
        "v15": Path(domains_v15.__file__).resolve(strict=True),
        "v16": Path(domains_v16.__file__).resolve(strict=True),
        "v17": Path(domains_v17.__file__).resolve(strict=True),
        "phase3e_ids": Path(ids_v1.__file__).resolve(strict=True),
    }
)

_PREBIND_ISSUER = object()
_TAKEOVER_ISSUER = object()
_RESULT_ISSUER = object()
_NATIVE_PREFIX_ISSUER = object()
_B2C_LOCK = threading.RLock()
_LIVE_PREBINDINGS: dict[int, "H1SupervisorBirthSourcePrebindingV1"] = {}
_CONSUMED_PREBINDINGS: dict[int, "H1SupervisorBirthSourcePrebindingV1"] = {}
_LIVE_TAKEOVERS: dict[int, "_H1SupervisorBirthTakeoverV1"] = {}
_QUARANTINED_TAKEOVERS: dict[int, "_H1SupervisorBirthTakeoverV1"] = {}
_RAW_OS_CLOSE = os.close
_RAW_OS_WRITE = os.write
_FCNTL_FCNTL = fcntl.fcntl
_SELF_CALLABLES: Mapping[str, tuple[Any, Any]] = MappingProxyType({})
_SELF_METHODS: Mapping[tuple[type[Any], str], tuple[Any, Any]] = MappingProxyType({})
_SELF_GLOBALS: Mapping[str, Any] = MappingProxyType({})
_TEST_ONLY_JOURNAL_FAULT_EVENT: str | None = None
_TEST_ONLY_JOURNAL_FAULT_PHASE: str | None = None
_TEST_ONLY_TAKEOVER_COMMIT_FAULT_AFTER_STEP: int | None = None
_TEST_ONLY_CONSUME_COMMIT_FAULT_AFTER_STEP: int | None = None
_TEST_ONLY_PEAK_FINISH_FAULT_STAGE: str | None = None

_UPSTREAM_CALLABLES = MappingProxyType(
    {
        ("native", "verify_supervisor_birth_native_image_v1"): (
            native_v1.verify_supervisor_birth_native_image_v1,
            native_v1.verify_supervisor_birth_native_image_v1.__code__,
        ),
        ("b2b", "_verify_running_under_locks"): (
            b2b_v1._verify_running_under_locks,  # noqa: SLF001
            b2b_v1._verify_running_under_locks.__code__,  # noqa: SLF001
        ),
        ("b2b", "_persist_record"): (
            b2b_v1._persist_record,  # noqa: SLF001
            b2b_v1._persist_record.__code__,  # noqa: SLF001
        ),
        ("b2b", "_same_owner"): (
            b2b_v1._same_owner,  # noqa: SLF001
            b2b_v1._same_owner.__code__,  # noqa: SLF001
        ),
        ("b2b", "_single_thread_identity"): (
            b2b_v1._single_thread_identity,  # noqa: SLF001
            b2b_v1._single_thread_identity.__code__,  # noqa: SLF001
        ),
        ("b2b", "_require_pristine_b2a_grants"): (
            b2b_v1._require_pristine_b2a_grants,  # noqa: SLF001
            b2b_v1._require_pristine_b2a_grants.__code__,  # noqa: SLF001
        ),
        ("b2b", "_verify_retained_sources_and_records"): (
            b2b_v1._verify_retained_sources_and_records,  # noqa: SLF001
            b2b_v1._verify_retained_sources_and_records.__code__,  # noqa: SLF001
        ),
        ("b2b", "_verify_managed_fd"): (
            b2b_v1._verify_managed_fd,  # noqa: SLF001
            b2b_v1._verify_managed_fd.__code__,  # noqa: SLF001
        ),
        ("b2b", "start_h1_guardian_runtime_genesis_v1"): (
            b2b_v1.start_h1_guardian_runtime_genesis_v1,
            b2b_v1.start_h1_guardian_runtime_genesis_v1.__code__,
        ),
        ("b2b", "close_h1_guardian_runtime_genesis_v1"): (
            b2b_v1.close_h1_guardian_runtime_genesis_v1,
            b2b_v1.close_h1_guardian_runtime_genesis_v1.__code__,
        ),
        ("b2b", "close_h1_guardian_runtime_after_rejected_consumption_v1"): (
            b2b_v1.close_h1_guardian_runtime_after_rejected_consumption_v1,
            b2b_v1.close_h1_guardian_runtime_after_rejected_consumption_v1.__code__,
        ),
        ("b2b", "close_h1_guardian_runtime_postrun_v1"): (
            b2b_v1.close_h1_guardian_runtime_postrun_v1,
            b2b_v1.close_h1_guardian_runtime_postrun_v1.__code__,
        ),
        ("b2b", "close_h1_guardian_runtime_after_failed_birth_v1"): (
            b2b_v1.close_h1_guardian_runtime_after_failed_birth_v1,
            b2b_v1.close_h1_guardian_runtime_after_failed_birth_v1.__code__,
        ),
        ("b2b", "close_h1_guardian_runtime_companion_unconsumed_v1"): (
            b2b_v1.close_h1_guardian_runtime_companion_unconsumed_v1,
            b2b_v1.close_h1_guardian_runtime_companion_unconsumed_v1.__code__,
        ),
        ("b2a", "_validate_e5a_bridge"): (
            b2a_v1._validate_e5a_bridge,  # noqa: SLF001
            b2a_v1._validate_e5a_bridge.__code__,  # noqa: SLF001
        ),
        ("b2a", "_verify_source_lease_retired"): (
            b2a_v1._verify_source_lease_retired,  # noqa: SLF001
            b2a_v1._verify_source_lease_retired.__code__,  # noqa: SLF001
        ),
        ("b2a", "_verify_runtime_fd_registry_unlocked"): (
            b2a_v1._verify_runtime_fd_registry_unlocked,  # noqa: SLF001
            b2a_v1._verify_runtime_fd_registry_unlocked.__code__,  # noqa: SLF001
        ),
        ("b2a", "_same_owner_context"): (
            b2a_v1._same_owner_context,  # noqa: SLF001
            b2a_v1._same_owner_context.__code__,  # noqa: SLF001
        ),
        ("e5a", "_verify_live_hierarchy"): (
            e5a_v1._verify_live_hierarchy,  # noqa: SLF001
            e5a_v1._verify_live_hierarchy.__code__,  # noqa: SLF001
        ),
        ("e5a", "_same_open_file_description_for_close"): (
            e5a_v1._same_open_file_description_for_close,  # noqa: SLF001
            e5a_v1._same_open_file_description_for_close.__code__,  # noqa: SLF001
        ),
        ("e5a", "_registry_fd_identity"): (
            e5a_v1._registry_fd_identity,  # noqa: SLF001
            e5a_v1._registry_fd_identity.__code__,  # noqa: SLF001
        ),
        ("e5a", "_block_fd_publication_signals"): (
            e5a_v1._block_fd_publication_signals,  # noqa: SLF001
            e5a_v1._block_fd_publication_signals.__code__,  # noqa: SLF001
        ),
        ("e5a", "_restore_fd_publication_signals"): (
            e5a_v1._restore_fd_publication_signals,  # noqa: SLF001
            e5a_v1._restore_fd_publication_signals.__code__,  # noqa: SLF001
        ),
        ("ids", "canonical_json_bytes"): (
            ids_v1.canonical_json_bytes,
            ids_v1.canonical_json_bytes.__code__,
        ),
        ("ids", "loads_canonical_json"): (
            ids_v1.loads_canonical_json,
            ids_v1.loads_canonical_json.__code__,
        ),
        ("v15", "extension_content_id_v15"): (
            domains_v15.extension_content_id_v15,
            domains_v15.extension_content_id_v15.__code__,
        ),
        ("v12", "extension_content_id_v12"): (
            domains_v12.extension_content_id_v12,
            domains_v12.extension_content_id_v12.__code__,
        ),
        ("v16", "extension_content_id_v16"): (
            domains_v16.extension_content_id_v16,
            domains_v16.extension_content_id_v16.__code__,
        ),
        ("v17", "extension_content_id_v17"): (
            domains_v17.extension_content_id_v17,
            domains_v17.extension_content_id_v17.__code__,
        ),
    }
)
_UPSTREAM_GLOBALS = MappingProxyType(
    {
        ("native", "X86_64_TEXT_BYTES"): native_v1.X86_64_TEXT_BYTES,
        ("native", "NativeLaunchArgsV1"): native_v1.NativeLaunchArgsV1,
        ("native", "NativeParentEdgeV1"): native_v1.NativeParentEdgeV1,
        ("native", "CloneArgsV1"): native_v1.CloneArgsV1,
        ("native", "_LIBC"): native_v1._LIBC,  # noqa: SLF001
        ("b2b", "_B2B_LOCK"): b2b_v1._B2B_LOCK,  # noqa: SLF001
        ("b2b", "_LIVE_SESSIONS"): b2b_v1._LIVE_SESSIONS,  # noqa: SLF001
        ("b2b", "_QUARANTINED_SESSIONS"): b2b_v1._QUARANTINED_SESSIONS,  # noqa: SLF001
        ("b2b", "_RUNTIME_RESERVATIONS"): b2b_v1._RUNTIME_RESERVATIONS,  # noqa: SLF001
        ("b2b", "_PERMIT_ISSUER"): b2b_v1._PERMIT_ISSUER,  # noqa: SLF001
        ("b2b", "_MANAGED_FDS"): b2b_v1._MANAGED_FDS,  # noqa: SLF001
        ("b2a", "_ADAPTER_LOCK"): b2a_v1._ADAPTER_LOCK,  # noqa: SLF001
        ("b2a", "_LIVE_RUNTIME_LEASES"): b2a_v1._LIVE_RUNTIME_LEASES,  # noqa: SLF001
        ("e5a", "_FD_OWNERSHIP_LOCK"): e5a_v1._FD_OWNERSHIP_LOCK,  # noqa: SLF001
        ("e5a", "_OWNED_FDS"): e5a_v1._OWNED_FDS,  # noqa: SLF001
        (
            "v16",
            "CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_COMPANION_TAKEOVER_V1_DOMAIN",
        ): domains_v16.CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_COMPANION_TAKEOVER_V1_DOMAIN,
        (
            "v16",
            "CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_PERMIT_CONSUMPTION_V1_DOMAIN",
        ): domains_v16.CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_PERMIT_CONSUMPTION_V1_DOMAIN,
        (
            "v16",
            "CONSTRUCTION_K7_H1_BOUNDED_SUPERVISOR_BIRTH_PEAK_OBSERVATION_V1_DOMAIN",
        ): domains_v16.CONSTRUCTION_K7_H1_BOUNDED_SUPERVISOR_BIRTH_PEAK_OBSERVATION_V1_DOMAIN,
        (
            "v16",
            "CONSTRUCTION_K7_H1_BOUNDED_SUPERVISOR_BIRTH_SLICE_RESULT_V1_DOMAIN",
        ): domains_v16.CONSTRUCTION_K7_H1_BOUNDED_SUPERVISOR_BIRTH_SLICE_RESULT_V1_DOMAIN,
        (
            "v16",
            "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V16",
        ): domains_v16.K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V16,
        (
            "v16",
            "K7_H1_DOMAIN_TAG_EXTENSION_V16",
        ): domains_v16.K7_H1_DOMAIN_TAG_EXTENSION_V16,
        (
            "v12",
            "K7_H1_DOMAIN_TAG_EXTENSION_V12",
        ): domains_v12.K7_H1_DOMAIN_TAG_EXTENSION_V12,
        (
            "v15",
            "K7_H1_DOMAIN_TAG_EXTENSION_V15",
        ): domains_v15.K7_H1_DOMAIN_TAG_EXTENSION_V15,
        (
            "v17",
            "CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_CONSUMED_CLEANUP_BARRIER_V1_DOMAIN",
        ): domains_v17.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_CONSUMED_CLEANUP_BARRIER_V1_DOMAIN,
        (
            "v17",
            "K7_H1_DOMAIN_TAG_EXTENSION_V17",
        ): domains_v17.K7_H1_DOMAIN_TAG_EXTENSION_V17,
    }
)


class ConstructionK7H1ActualObservedSupervisorBirthV1Error(ValueError):
    """The bounded B2-C source, identity, protocol, or cleanup changed."""

    def __init__(
        self,
        message: str,
        *,
        cleanup_document: Mapping[str, Any] | None = None,
        cleanup_handle: Any = None,
    ):
        super().__init__(message)
        self.cleanup_document = (
            dict(cleanup_document) if cleanup_document is not None else None
        )
        self.cleanup_handle = cleanup_handle


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(message)


def _domain_id(domain: str, payload: Any) -> str:
    if domain in domains_v12.K7_H1_DOMAIN_TAG_EXTENSION_V12:
        return domains_v12.extension_content_id_v12(domain, payload)
    if domain in domains_v15.K7_H1_DOMAIN_TAG_EXTENSION_V15:
        return domains_v15.extension_content_id_v15(domain, payload)
    if domain in domains_v16.K7_H1_DOMAIN_TAG_EXTENSION_V16:
        return domains_v16.extension_content_id_v16(domain, payload)
    if domain in domains_v17.K7_H1_DOMAIN_TAG_EXTENSION_V17:
        return domains_v17.extension_content_id_v17(domain, payload)
    _fail("B2-C domain tag is absent from the frozen V15/V16/V17 registries")


def _verify_birth_record(
    record: "_BirthJournalRecordV1",
    *,
    domain: str,
    id_field: str,
) -> dict[str, Any]:
    if type(record) is not _BirthJournalRecordV1:
        _fail("B2-C durable record type changed")
    document = ids_v1.loads_canonical_json(record.canonical_bytes)
    payload = dict(document)
    supplied = payload.pop(id_field, None)
    if (
        supplied != record.record_id
        or type(supplied) is not str
        or _domain_id(domain, payload) != supplied
    ):
        _fail("B2-C durable record content ID changed")
    return document


def _locked_claims() -> dict[str, Any]:
    return {
        "production_full_execution_source_closure_present": False,
        "external_preregistration_anchor_present": False,
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


def _validate_live_code_closure() -> None:
    modules = {
        "native": native_v1,
        "b2b": b2b_v1,
        "b2a": b2a_v1,
        "e5a": e5a_v1,
        "ids": ids_v1,
        "v12": domains_v12,
        "v15": domains_v15,
        "v16": domains_v16,
        "v17": domains_v17,
    }
    for (module_name, name), (expected, expected_code) in _UPSTREAM_CALLABLES.items():
        live = getattr(modules[module_name], name, None)
        if (
            live is not expected
            or getattr(live, "__globals__", None) is not modules[module_name].__dict__
            or getattr(live, "__code__", None) is not expected_code
        ):
            _fail(f"B2-C live callable identity changed: {module_name}.{name}")
    for name, (expected, expected_code) in _SELF_CALLABLES.items():
        live = globals().get(name)
        if (
            live is not expected
            or getattr(live, "__globals__", None) is not globals()
            or getattr(live, "__code__", None) is not expected_code
        ):
            _fail(f"B2-C live callable identity changed: b2c.{name}")
    for (owner, name), (expected, expected_code) in _SELF_METHODS.items():
        live = getattr(owner, name, None)
        if live is not expected or getattr(live, "__code__", None) is not expected_code:
            _fail(f"B2-C live method identity changed: {owner.__name__}.{name}")
    for name, expected in _SELF_GLOBALS.items():
        if globals().get(name) is not expected:
            _fail(f"B2-C prebound global identity changed: {name}")
    for (module_name, name), expected in _UPSTREAM_GLOBALS.items():
        if getattr(modules[module_name], name, None) is not expected:
            _fail(f"B2-C live global identity changed: {module_name}.{name}")
    for label, expected_digest in _EXPECTED_SOURCE_SHA256.items():
        try:
            observed = hashlib.sha256(_SOURCE_PATHS[label].read_bytes()).hexdigest()
        except OSError as error:
            raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
                "B2-C source closure cannot be replayed"
            ) from error
        if observed != expected_digest:
            _fail(f"B2-C expected source changed: {label}")
    status = os.stat(_SELF_SOURCE_PATH, follow_symlinks=False)
    if (
        hashlib.sha256(_SELF_SOURCE_PATH.read_bytes()).hexdigest()
        != _SELF_IMPORT_FACT["sha256"]
        or (status.st_dev, status.st_ino, status.st_mode, status.st_size)
        != (
            _SELF_IMPORT_FACT["device"],
            _SELF_IMPORT_FACT["inode"],
            _SELF_IMPORT_FACT["mode"],
            _SELF_IMPORT_FACT["size"],
        )
    ):
        _fail("B2-C self source changed after import")
    native_v1.verify_supervisor_birth_native_image_v1()


def _write_all(descriptor: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        written = os.write(descriptor, raw[offset:])
        if written <= 0:
            _fail("B2-C durable write made no progress")
        offset += written


def _new_sealed_document_memfd(raw: bytes, name: str) -> tuple[int, int]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_JOURNAL_RECORD_BYTES:
        _fail("B2-C sealed document bytes are invalid")
    if not callable(getattr(os, "memfd_create", None)):
        _fail("B2-C requires memfd_create")
    descriptor = os.memfd_create(name, MFD_CLOEXEC | MFD_ALLOW_SEALING)
    witness = -1
    try:
        _write_all(descriptor, raw)
        os.fsync(descriptor)
        fcntl.fcntl(descriptor, F_ADD_SEALS, REQUIRED_SEALS)
        if fcntl.fcntl(descriptor, F_GET_SEALS) != REQUIRED_SEALS:
            _fail("B2-C sealed document has incomplete seals")
        if os.pread(descriptor, len(raw) + 1, 0) != raw:
            _fail("B2-C sealed document replay changed")
        witness = fcntl.fcntl(descriptor, fcntl.F_DUPFD_CLOEXEC, 3)
        if not e5a_v1._same_open_file_description_for_close(  # noqa: SLF001
            descriptor, witness
        ):
            _fail("B2-C sealed document witness is not the same OFD")
        return descriptor, witness
    except BaseException:
        if witness >= 0:
            os.close(witness)
        os.close(descriptor)
        raise


def _open_retained_source_fds() -> tuple[
    dict[str, tuple[int, int]], dict[str, dict[str, Any]]
]:
    descriptors: dict[str, tuple[int, int]] = {}
    facts: dict[str, dict[str, Any]] = {}
    try:
        for label, path in _SOURCE_PATHS.items():
            canonical = os.open(
                path,
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            )
            witness = -1
            try:
                witness = fcntl.fcntl(canonical, fcntl.F_DUPFD_CLOEXEC, 3)
                if not e5a_v1._same_open_file_description_for_close(  # noqa: SLF001
                    canonical, witness
                ):
                    _fail("B2-C retained source witness is not the same OFD")
                status = os.fstat(canonical)
                named = os.stat(path, follow_symlinks=False)
                raw = os.pread(canonical, MAX_JOURNAL_RECORD_BYTES + 1, 0)
                if (
                    not stat.S_ISREG(status.st_mode)
                    or len(raw) > MAX_JOURNAL_RECORD_BYTES
                    or (status.st_dev, status.st_ino, status.st_mode, status.st_size)
                    != (named.st_dev, named.st_ino, named.st_mode, named.st_size)
                    or len(raw) != status.st_size
                ):
                    _fail("B2-C retained source identity or extent changed")
                descriptors[label] = (canonical, witness)
                facts[label] = {
                    "label": label,
                    "resolved_path": str(path),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "byte_count": len(raw),
                    "device": status.st_dev,
                    "inode": status.st_ino,
                    "mode": status.st_mode,
                    "size": status.st_size,
                    "canonical_fd_cloexec": True,
                    "same_ofd_witness_retained": True,
                }
            except BaseException:
                if witness >= 0:
                    os.close(witness)
                os.close(canonical)
                raise
        return descriptors, facts
    except BaseException:
        for canonical, witness in descriptors.values():
            os.close(witness)
            os.close(canonical)
        raise


def _new_sealed_code_rx() -> tuple[int, int, int, Any, dict[str, Any]]:
    raw = native_v1.X86_64_TEXT_BYTES
    descriptor, witness = _new_sealed_document_memfd(
        raw, "acfqp-h1-b2c-supervisor-code"
    )
    libc = native_v1._LIBC  # noqa: SLF001
    libc.mmap.argtypes = (
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_long,
    )
    libc.mmap.restype = ctypes.c_void_p
    address_value = libc.mmap(
        None,
        len(raw),
        mmap.PROT_READ | mmap.PROT_EXEC,
        mmap.MAP_PRIVATE,
        descriptor,
        0,
    )
    address = int(address_value) if address_value is not None else 0
    if address == 0 or address == ctypes.c_void_p(-1).value:
        os.close(witness)
        os.close(descriptor)
        _fail("B2-C sealed code could not map direct RX")
    try:
        function_type = ctypes.PYFUNCTYPE(
            ctypes.c_long,
            ctypes.POINTER(native_v1.NativeLaunchArgsV1),
        )
        function = function_type(address)
        status = os.fstat(descriptor)
        fact = {
            "text_sha256": hashlib.sha256(raw).hexdigest(),
            "text_byte_count": len(raw),
            "memfd_device": status.st_dev,
            "memfd_inode": status.st_ino,
            "memfd_mode": status.st_mode,
            "memfd_size": status.st_size,
            "memfd_seals": fcntl.fcntl(descriptor, F_GET_SEALS),
            "canonical_fd_cloexec": True,
            "witness_fd_cloexec": True,
            "same_ofd_witness_retained": True,
            "mapping_offset": 0,
            "mapping_extent_bytes": len(raw),
            "mapping_protection": "PROT_READ|PROT_EXEC",
            "mapping_flags": "MAP_PRIVATE",
            "writable_code_mapping_ever_created": False,
            "pyfunctype_gil_retaining_entry": True,
        }
        return descriptor, witness, address, function, fact
    except BaseException:
        libc.munmap(ctypes.c_void_p(address), len(raw))
        os.close(witness)
        os.close(descriptor)
        raise


@dataclass(slots=True)
class H1SupervisorBirthSourcePrebindingV1:
    """Uncopyable pre-RUNNING temporal authority with a sealed manifest."""

    _owner_pid: int = field(repr=False)
    _owner_thread: threading.Thread = field(repr=False)
    _owner_thread_id: int = field(repr=False)
    _runtime: b2a_v1.H1E5ARuntimeLeaseSuccessorV1 = field(repr=False)
    _canonical_bytes: bytes = field(repr=False)
    _manifest_id: str
    _manifest_fd: int = field(repr=False)
    _manifest_witness_fd: int = field(repr=False)
    _manifest_fact: dict[str, Any] = field(repr=False)
    _source_fds: dict[str, tuple[int, int]] = field(repr=False)
    _source_facts: dict[str, dict[str, Any]] = field(repr=False)
    _code_fd: int = field(repr=False)
    _code_witness_fd: int = field(repr=False)
    _code_rx_address: int = field(repr=False)
    _code_rx_function: Any = field(repr=False)
    _code_fact: dict[str, Any] = field(repr=False)
    _state: str
    _issuer: object = field(repr=False)

    def __post_init__(self) -> None:
        if self._issuer is not _PREBIND_ISSUER:
            _fail("B2-C source prebinding is caller-minted")

    @property
    def prebinding_id(self) -> str:
        return self._manifest_id

    @property
    def state(self) -> str:
        return self._state

    def to_document(self) -> dict[str, Any]:
        return ids_v1.loads_canonical_json(self._canonical_bytes)

    def __copy__(self) -> NoReturn:
        _fail("B2-C source prebinding cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("B2-C source prebinding cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("B2-C source prebinding cannot be copied or pickled")


def _same_owner(prebinding: H1SupervisorBirthSourcePrebindingV1) -> bool:
    return (
        prebinding._owner_pid == os.getpid()
        and prebinding._owner_thread_id == threading.get_ident()
        and prebinding._owner_thread is threading.current_thread()
    )


def _require_exact_prepared_runtime(
    runtime: b2a_v1.H1E5ARuntimeLeaseSuccessorV1,
) -> None:
    if (
        type(runtime) is not b2a_v1.H1E5ARuntimeLeaseSuccessorV1
        or not b2a_v1._same_owner_context(runtime)  # noqa: SLF001
        or runtime._state != "PREPARED_SUCCESSOR"  # noqa: SLF001
        or b2a_v1._LIVE_RUNTIME_LEASES.get(id(runtime)) is not runtime  # noqa: SLF001
        or id(runtime) in b2b_v1._RUNTIME_RESERVATIONS  # noqa: SLF001
        or id(runtime) in _LIVE_PREBINDINGS
        or id(runtime) in _CONSUMED_PREBINDINGS
    ):
        _fail("B2-C prebinding requires one unreserved exact PREPARED runtime")
    b2a_v1._validate_e5a_bridge()  # noqa: SLF001
    b2a_v1._verify_source_lease_retired(runtime)  # noqa: SLF001
    b2a_v1._verify_runtime_fd_registry_unlocked(runtime)  # noqa: SLF001
    b2b_v1._require_pristine_b2a_grants(runtime)  # noqa: SLF001
    e5a_v1._verify_live_hierarchy(runtime)  # noqa: SLF001


def prebind_h1_actual_observed_supervisor_birth_v1(
    runtime: b2a_v1.H1E5ARuntimeLeaseSuccessorV1,
) -> H1SupervisorBirthSourcePrebindingV1:
    """Freeze final B2-C source/RX identity before B2-B enters RUNNING."""

    _validate_live_code_closure()
    guardian = b2b_v1._single_thread_identity()  # noqa: SLF001
    original_mask = e5a_v1._block_fd_publication_signals()  # noqa: SLF001
    source_fds: dict[str, tuple[int, int]] = {}
    code_fd = -1
    code_witness = -1
    code_address = 0
    manifest_descriptor = -1
    manifest_witness = -1
    try:
        with _B2C_LOCK:
            with b2b_v1._B2B_LOCK:  # noqa: SLF001
                with b2a_v1._ADAPTER_LOCK:  # noqa: SLF001
                    source = runtime._source_lease  # noqa: SLF001
                    with source._lock:  # noqa: SLF001
                        with runtime._lock:  # noqa: SLF001
                            with e5a_v1._FD_OWNERSHIP_LOCK:  # noqa: SLF001
                                _require_exact_prepared_runtime(runtime)
                                source_fds, source_facts = _open_retained_source_fds()
                                (
                                    code_fd,
                                    code_witness,
                                    code_address,
                                    code_function,
                                    code_fact,
                                ) = _new_sealed_code_rx()
                                payload = {
                                    "schema": "acfqp.k7_h1_supervisor_birth_source_prebinding.v1",
                                    "schema_version": SCHEMA_VERSION,
                                    "profile_key": PROFILE_KEY,
                                    "runtime_successor_id": runtime.successor_id,
                                    "runtime_state_at_freeze": "PREPARED_SUCCESSOR",
                                    "b2b_runtime_reservation_absent_at_freeze": True,
                                    "guardian_identity": guardian,
                                    "retained_source_files": [
                                        source_facts[label]
                                        for label in sorted(source_facts)
                                    ],
                                    "native_image": native_v1.verify_supervisor_birth_native_image_v1(),
                                    "sealed_code_memfd_and_direct_rx": code_fact,
                                    "rx_callable_frozen_before_running": True,
                                    "native_anonymous_development_mapping_used": False,
                                    "prebinding_is_process_local_temporal_authority": True,
                                    "prebinding_is_externally_anchored": False,
                                    **_locked_claims(),
                                }
                                manifest_id = _domain_id(
                                    domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN,
                                    payload,
                                )
                                document = dict(payload)
                                document["supervisor_birth_source_prebinding_id"] = manifest_id
                                raw = ids_v1.canonical_json_bytes(document)
                                (
                                    manifest_descriptor,
                                    manifest_witness,
                                ) = _new_sealed_document_memfd(
                                    raw, "acfqp-h1-b2c-source-prebinding"
                                )
                                manifest_status = os.fstat(manifest_descriptor)
                                manifest_fact = {
                                    "device": manifest_status.st_dev,
                                    "inode": manifest_status.st_ino,
                                    "mode": manifest_status.st_mode,
                                    "size": manifest_status.st_size,
                                    "canonical_fd_cloexec": True,
                                    "witness_fd_cloexec": True,
                                }
                                result = H1SupervisorBirthSourcePrebindingV1(
                                    os.getpid(),
                                    threading.current_thread(),
                                    threading.get_ident(),
                                    runtime,
                                    raw,
                                    manifest_id,
                                    manifest_descriptor,
                                    manifest_witness,
                                    manifest_fact,
                                    source_fds,
                                    source_facts,
                                    code_fd,
                                    code_witness,
                                    code_address,
                                    code_function,
                                    code_fact,
                                    "LIVE_PRE_RUNNING",
                                    _PREBIND_ISSUER,
                                )
                                _LIVE_PREBINDINGS[id(runtime)] = result
                                return result
    except BaseException:
        libc = native_v1._LIBC  # noqa: SLF001
        if code_address:
            libc.munmap(ctypes.c_void_p(code_address), len(native_v1.X86_64_TEXT_BYTES))
        for descriptor in (code_witness, code_fd):
            if descriptor >= 0:
                os.close(descriptor)
        for descriptor in (manifest_witness, manifest_descriptor):
            if descriptor >= 0:
                os.close(descriptor)
        for canonical, witness in source_fds.values():
            os.close(witness)
            os.close(canonical)
        raise
    finally:
        e5a_v1._restore_fd_publication_signals(original_mask)  # noqa: SLF001


def verify_h1_supervisor_birth_source_prebinding_v1(
    prebinding: H1SupervisorBirthSourcePrebindingV1,
) -> dict[str, Any]:
    _validate_live_code_closure()
    if type(prebinding) is not H1SupervisorBirthSourcePrebindingV1:
        _fail("B2-C source prebinding type changed")
    runtime = prebinding._runtime
    source = runtime._source_lease  # noqa: SLF001
    original_mask = e5a_v1._block_fd_publication_signals()  # noqa: SLF001
    try:
        if takeover.state in {
            "UNCONSUMED_CLOSE_PENDING",
            "UNCONSUMED_B2C_RESOURCES_CLOSED_JOURNAL_OPEN",
            "CLOSED_UNCONSUMED_CANCELLED",
        }:
            _close_unconsumed_takeover_v1(takeover)
        with _B2C_LOCK:
            with b2b_v1._B2B_LOCK:  # noqa: SLF001
                with b2a_v1._ADAPTER_LOCK:  # noqa: SLF001
                    with source._lock:  # noqa: SLF001
                        with runtime._lock:  # noqa: SLF001
                            with e5a_v1._FD_OWNERSHIP_LOCK:  # noqa: SLF001
                                if (
                                    not _same_owner(prebinding)
                                    or prebinding._state != "LIVE_PRE_RUNNING"
                                    or _LIVE_PREBINDINGS.get(id(runtime))
                                    is not prebinding
                                ):
                                    _fail(
                                        "B2-C source prebinding is not exact and live"
                                    )
                                return _verify_prebinding_bytes(
                                    prebinding,
                                    allowed_states={"LIVE_PRE_RUNNING"},
                                )
    finally:
        e5a_v1._restore_fd_publication_signals(original_mask)  # noqa: SLF001


def _close_h1_supervisor_birth_source_prebinding_under_locks_v1(
    prebinding: H1SupervisorBirthSourcePrebindingV1,
) -> None:
    """Close an unused prebinding; consumed prebindings close via B2-C."""

    if type(prebinding) is not H1SupervisorBirthSourcePrebindingV1 or not _same_owner(
        prebinding
    ):
        _fail("B2-C prebinding close requires one exact owner")
    with _B2C_LOCK:
        if prebinding._state == "CLOSED_UNUSED":
            return
        if (
            prebinding._state != "LIVE_PRE_RUNNING"
            or _LIVE_PREBINDINGS.get(id(prebinding._runtime)) is not prebinding
        ):
            _fail("B2-C consumed prebinding cannot use unused close")
        libc = native_v1._LIBC  # noqa: SLF001
        libc.munmap.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
        libc.munmap.restype = ctypes.c_int
        if libc.munmap(
            ctypes.c_void_p(prebinding._code_rx_address),
            len(native_v1.X86_64_TEXT_BYTES),
        ) != 0:
            _fail("B2-C unused prebinding RX unmap failed")
        for canonical, witness in prebinding._source_fds.values():
            os.close(witness)
            os.close(canonical)
        for descriptor in (
            prebinding._code_witness_fd,
            prebinding._code_fd,
            prebinding._manifest_witness_fd,
            prebinding._manifest_fd,
        ):
            os.close(descriptor)
        prebinding._manifest_fd = -1
        prebinding._manifest_witness_fd = -1
        prebinding._source_fds.clear()
        prebinding._code_fd = -1
        prebinding._code_witness_fd = -1
        prebinding._code_rx_address = 0
        prebinding._code_rx_function = None
        prebinding._state = "CLOSED_UNUSED"
        _LIVE_PREBINDINGS.pop(id(prebinding._runtime), None)


def close_h1_supervisor_birth_source_prebinding_v1(
    prebinding: H1SupervisorBirthSourcePrebindingV1,
) -> None:
    """Signal/fork-shielded close for one unused pre-RUNNING prebinding."""

    if type(prebinding) is not H1SupervisorBirthSourcePrebindingV1:
        _fail("B2-C prebinding close type changed")
    runtime = prebinding._runtime
    source = runtime._source_lease  # noqa: SLF001
    original_mask = e5a_v1._block_fd_publication_signals()  # noqa: SLF001
    try:
        with _B2C_LOCK:
            with b2b_v1._B2B_LOCK:  # noqa: SLF001
                with b2a_v1._ADAPTER_LOCK:  # noqa: SLF001
                    with source._lock:  # noqa: SLF001
                        with runtime._lock:  # noqa: SLF001
                            with e5a_v1._FD_OWNERSHIP_LOCK:  # noqa: SLF001
                                _close_h1_supervisor_birth_source_prebinding_under_locks_v1(
                                    prebinding
                                )
    finally:
        e5a_v1._restore_fd_publication_signals(original_mask)  # noqa: SLF001


@dataclass(slots=True)
class _BirthJournalRecordV1:
    canonical_bytes: bytes = field(repr=False)
    record_id: str
    filename: str
    descriptor: int = field(repr=False)

    def to_document(self) -> dict[str, Any]:
        return ids_v1.loads_canonical_json(self.canonical_bytes)


@dataclass(slots=True)
class _PendingBirthJournalRecordV1:
    domain: str
    id_field: str
    event: str
    raw: bytes = field(repr=False)
    record: _BirthJournalRecordV1 = field(repr=False)
    index: int
    filename: str
    descriptor: int = -1
    injected_fault_phase: str | None = None


class _BirthJournalV1:
    __slots__ = (
        "_owner_pid",
        "_owner_thread_id",
        "_path",
        "_directory_fd",
        "_records",
        "_names",
        "_pending",
        "_state",
    )

    def __init__(self, path: Path) -> None:
        self._owner_pid = os.getpid()
        self._owner_thread_id = threading.get_ident()
        self._path = path
        self._directory_fd = os.open(
            path,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        self._records: list[_BirthJournalRecordV1] = []
        self._names: set[str] = set()
        self._pending: _PendingBirthJournalRecordV1 | None = None
        self._state = "OPEN"
        status = os.fstat(self._directory_fd)
        if (
            not stat.S_ISDIR(status.st_mode)
            or status.st_uid != os.geteuid()
            or stat.S_IMODE(status.st_mode) & 0o077
            or os.listdir(self._directory_fd)
        ):
            os.close(self._directory_fd)
            self._directory_fd = -1
            _fail("B2-C journal directory must be private and empty")

    def append(
        self,
        *,
        domain: str,
        id_field: str,
        event: str,
        payload: Mapping[str, Any],
    ) -> _BirthJournalRecordV1:
        if (
            self._state != "OPEN"
            or self._owner_pid != os.getpid()
            or self._owner_thread_id != threading.get_ident()
            or self._directory_fd < 0
        ):
            _fail("B2-C journal is not exact and open")
        document = dict(payload)
        record_id = _domain_id(domain, document)
        document[id_field] = record_id
        raw = ids_v1.canonical_json_bytes(document)
        if not raw or len(raw) > MAX_JOURNAL_RECORD_BYTES:
            _fail("B2-C journal record exceeds its exact bound")
        pending = self._pending
        if pending is not None:
            if (
                pending.domain == domain
                and pending.id_field == id_field
                and pending.event == event
                and pending.raw == raw
            ):
                return self._resume_pending()
            self._resume_pending()
        index = len(self._records)
        filename = f"{index:04d}_{event}_{record_id}.json"
        record = _BirthJournalRecordV1(raw, record_id, filename, -1)
        self._pending = _PendingBirthJournalRecordV1(
            domain=domain,
            id_field=id_field,
            event=event,
            raw=raw,
            record=record,
            index=index,
            filename=filename,
        )
        try:
            return self._resume_pending()
        except BaseException as first_error:
            try:
                return self._resume_pending()
            except BaseException as retry_error:
                raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
                    "B2-C journal retained a retryable exact transaction",
                    cleanup_handle=self,
                ) from retry_error

    def _inject_fault(self, pending: _PendingBirthJournalRecordV1, phase: str) -> None:
        if (
            _TEST_ONLY_JOURNAL_FAULT_EVENT == pending.event
            and _TEST_ONLY_JOURNAL_FAULT_PHASE == phase
            and pending.injected_fault_phase is None
        ):
            pending.injected_fault_phase = phase
            raise RuntimeError(f"injected B2-C journal fault {phase}")

    def _finish_pending(
        self,
        pending: _PendingBirthJournalRecordV1,
    ) -> _BirthJournalRecordV1:
        record = pending.record
        record.descriptor = pending.descriptor
        self._names.add(pending.filename)
        if len(self._records) == pending.index:
            self._records.append(record)
        elif (
            len(self._records) <= pending.index
            or self._records[pending.index] is not record
        ):
            _fail("B2-C journal finish-forward order changed")
        self._pending = None
        return record

    def _resume_pending(self) -> _BirthJournalRecordV1:
        pending = self._pending
        if pending is None:
            _fail("B2-C journal has no pending transaction")
        if pending.descriptor < 0:
            pending.descriptor = os.open(
                pending.filename,
                os.O_RDWR
                | os.O_CREAT
                | os.O_EXCL
                | os.O_CLOEXEC
                | os.O_NOFOLLOW,
                0o400,
                dir_fd=self._directory_fd,
            )
            self._inject_fault(pending, "AFTER_OPEN")
        descriptor = pending.descriptor
        os.ftruncate(descriptor, 0)
        os.lseek(descriptor, 0, os.SEEK_SET)
        if (
            _TEST_ONLY_JOURNAL_FAULT_EVENT == pending.event
            and _TEST_ONLY_JOURNAL_FAULT_PHASE == "AFTER_PARTIAL_WRITE"
            and pending.injected_fault_phase is None
        ):
            _write_all(descriptor, pending.raw[: max(1, len(pending.raw) // 2)])
            self._inject_fault(pending, "AFTER_PARTIAL_WRITE")
        _write_all(descriptor, pending.raw)
        self._inject_fault(pending, "AFTER_FULL_WRITE")
        os.fsync(descriptor)
        self._inject_fault(pending, "AFTER_FILE_FSYNC")
        os.fsync(self._directory_fd)
        self._inject_fault(pending, "AFTER_DIRECTORY_FSYNC")
        status = os.fstat(descriptor)
        named = os.stat(
            pending.filename,
            dir_fd=self._directory_fd,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(status.st_mode)
            or stat.S_IMODE(status.st_mode) != 0o400
            or status.st_nlink != 1
            or status.st_size != len(pending.raw)
            or (status.st_dev, status.st_ino) != (named.st_dev, named.st_ino)
            or os.pread(descriptor, len(pending.raw) + 1, 0) != pending.raw
        ):
            _fail("B2-C durable journal record changed")
        return self._finish_pending(pending)

    def verify(self) -> None:
        if (
            self._state != "OPEN"
            or self._pending is not None
            or set(os.listdir(self._directory_fd)) != self._names
        ):
            _fail("B2-C journal inventory changed")
        for record in self._records:
            status = os.fstat(record.descriptor)
            named = os.stat(
                record.filename,
                dir_fd=self._directory_fd,
                follow_symlinks=False,
            )
            if (
                fcntl.fcntl(record.descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
                == 0
                or (status.st_dev, status.st_ino) != (named.st_dev, named.st_ino)
                or status.st_size != len(record.canonical_bytes)
                or os.pread(
                    record.descriptor, len(record.canonical_bytes) + 1, 0
                )
                != record.canonical_bytes
            ):
                _fail("B2-C retained journal record changed")

    def close(self) -> None:
        if self._state == "CLOSED":
            return
        if self._state not in {"OPEN", "CLOSE_PENDING"}:
            _fail("B2-C journal cannot close from its current state")
        self._state = "CLOSE_PENDING"
        first: OSError | None = None
        if self._pending is not None and self._pending.descriptor >= 0:
            descriptor = self._pending.descriptor
            try:
                os.close(descriptor)
            except OSError as error:
                try:
                    fcntl.fcntl(descriptor, fcntl.F_GETFD)
                except OSError as probe:
                    if probe.errno == errno.EBADF:
                        self._pending.descriptor = -1
                    elif first is None:
                        first = error
                else:
                    if first is None:
                        first = error
            else:
                self._pending.descriptor = -1
        for record in reversed(self._records):
            if record.descriptor < 0:
                continue
            descriptor = record.descriptor
            try:
                os.close(descriptor)
            except OSError as error:
                try:
                    fcntl.fcntl(descriptor, fcntl.F_GETFD)
                except OSError as probe:
                    if probe.errno == errno.EBADF:
                        record.descriptor = -1
                    elif first is None:
                        first = error
                else:
                    if first is None:
                        first = error
            else:
                record.descriptor = -1
        if self._directory_fd >= 0:
            descriptor = self._directory_fd
            try:
                os.close(descriptor)
            except OSError as error:
                try:
                    fcntl.fcntl(descriptor, fcntl.F_GETFD)
                except OSError as probe:
                    if probe.errno == errno.EBADF:
                        self._directory_fd = -1
                    elif first is None:
                        first = error
                else:
                    if first is None:
                        first = error
            else:
                self._directory_fd = -1
        outstanding = (
            (self._pending is not None and self._pending.descriptor >= 0)
            or any(record.descriptor >= 0 for record in self._records)
            or self._directory_fd >= 0
        )
        if first is not None:
            raise first
        if outstanding:
            raise RuntimeError("B2-C journal close retained a descriptor")
        self._state = "CLOSED"

    def poison_after_fork_child(self) -> None:
        if self._pending is not None and self._pending.descriptor >= 0:
            try:
                os.close(self._pending.descriptor)
            except OSError:
                pass
            self._pending.descriptor = -1
        for record in self._records:
            if record.descriptor >= 0:
                try:
                    os.close(record.descriptor)
                except OSError:
                    pass
                record.descriptor = -1
        if self._directory_fd >= 0:
            try:
                os.close(self._directory_fd)
            except OSError:
                pass
            self._directory_fd = -1
        self._state = "FORK_POISONED"


@dataclass(slots=True)
class _H1SupervisorBirthTakeoverV1:
    session: b2b_v1.H1GuardianRuntimeGenesisV1 = field(repr=False)
    prebinding: H1SupervisorBirthSourcePrebindingV1 = field(repr=False)
    permit: b2b_v1.H1SupervisorBirthPermitV1 = field(repr=False)
    permit_record: b2b_v1.H1GuardianRuntimeRecordV1 = field(repr=False)
    journal: _BirthJournalV1 = field(repr=False)
    takeover_record: _BirthJournalRecordV1 = field(repr=False)
    owner_pid: int
    owner_thread: threading.Thread = field(repr=False)
    owner_thread_id: int
    state: str
    child_pid: int = -1
    pidfd: int = -1
    cgroup_kill_written: bool = False
    consume_record: _BirthJournalRecordV1 | None = field(default=None, repr=False)
    native_prefix: "_H1SupervisorNativeLaunchPrefixV1 | None" = field(
        default=None, repr=False
    )
    consumed_barrier: b2b_v1.H1GuardianRuntimeRecordV1 | None = field(
        default=None, repr=False
    )
    protocol_failure_record: _BirthJournalRecordV1 | None = field(
        default=None, repr=False
    )
    closure: b2a_v1.H1E5ARuntimeLeaseClosureV1 | None = field(
        default=None, repr=False
    )
    _issuer: object = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self._issuer is not _TAKEOVER_ISSUER:
            _fail("B2-C takeover is caller-minted")

    def __copy__(self) -> NoReturn:
        _fail("B2-C takeover cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("B2-C takeover cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("B2-C takeover cannot be copied or pickled")

    def poison_after_fork_child(self) -> None:
        self.journal.poison_after_fork_child()
        self.session._poison_after_fork_child()  # noqa: SLF001
        self.state = "FORK_POISONED"
        self.child_pid = -1
        self.pidfd = -1


@dataclass(slots=True)
class _H1SupervisorNativeLaunchPrefixV1:
    """Live post-consumption edge; later protocol code must close every FD."""

    takeover: _H1SupervisorBirthTakeoverV1 = field(repr=False)
    consume_record: _BirthJournalRecordV1 | None = field(repr=False)
    clone_args: native_v1.CloneArgsV1 = field(repr=False)
    launch_args: native_v1.NativeLaunchArgsV1 = field(repr=False)
    parent_edge: native_v1.NativeParentEdgeV1 = field(repr=False)
    pidfd_cell: ctypes.c_int = field(repr=False)
    cell_withdrawn_buffer: Any = field(repr=False)
    gate_ready_buffer: Any = field(repr=False)
    release_buffer: Any = field(repr=False)
    launch_args_pointer: Any = field(repr=False)
    release_frame: bytes = field(repr=False)
    parent_gate_fd: int
    child_gate_source_fd: int
    pid_cell_sealer_fd: int
    pid_cell_witness_fd: int
    pid_cell_reader_fd: int
    guardian_pid_cell_read_mapping: int
    creator_pid_cell_fd: int
    creator_pid_cell_mapping: int
    creator_cgroup_grant_fd: int
    escrow_receiver_fd: int
    escrow_sender_fd: int
    creator_pidfd_fd: int
    escrowed_pidfd_fd: int
    native_return: int | None
    child_gate_source_close_errno: int | None
    protocol_records: dict[str, _BirthJournalRecordV1] = field(repr=False)
    protocol_facts: dict[str, Any] = field(repr=False)
    state: str
    _issuer: object = field(repr=False)

    def __post_init__(self) -> None:
        if self._issuer is not _NATIVE_PREFIX_ISSUER:
            _fail("B2-C native launch prefix is caller-minted")

    def __copy__(self) -> NoReturn:
        _fail("B2-C native launch prefix cannot be copied")

    def __deepcopy__(self, _memo: object) -> NoReturn:
        _fail("B2-C native launch prefix cannot be copied")

    def __reduce__(self) -> NoReturn:
        _fail("B2-C native launch prefix cannot be copied or pickled")


@dataclass(frozen=True, slots=True)
class H1ActualObservedSupervisorBirthResultV1:
    """Portable content-addressed result of the bounded one-birth slice."""

    canonical_bytes: bytes = field(repr=False)
    result_id: str = field(init=False)
    _issuer: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer is not _RESULT_ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("B2-C bounded slice result is caller-minted")
        document = ids_v1.loads_canonical_json(self.canonical_bytes)
        payload = dict(document)
        supplied = payload.pop("bounded_supervisor_birth_slice_result_id", None)
        if (
            type(supplied) is not str
            or _domain_id(
                domains_v16.CONSTRUCTION_K7_H1_BOUNDED_SUPERVISOR_BIRTH_SLICE_RESULT_V1_DOMAIN,
                payload,
            )
            != supplied
        ):
            _fail("B2-C bounded slice result content ID changed")
        object.__setattr__(self, "result_id", supplied)

    def to_document(self) -> dict[str, Any]:
        return ids_v1.loads_canonical_json(self.canonical_bytes)


def _finish_takeover_commit(takeover: _H1SupervisorBirthTakeoverV1) -> None:
    """Idempotently finish the durable takeover toward companion ownership."""

    session = takeover.session
    runtime = session._runtime  # noqa: SLF001

    def apply(*, inject_fault: bool) -> None:
        step = 0

        def boundary() -> None:
            nonlocal step
            step += 1
            if inject_fault and _TEST_ONLY_TAKEOVER_COMMIT_FAULT_AFTER_STEP == step:
                raise RuntimeError(
                    f"injected B2-C takeover commit fault after step {step}"
                )

        takeover.prebinding._state = "TAKEN_OVER_UNCONSUMED"
        boundary()
        _LIVE_PREBINDINGS.pop(id(runtime), None)
        _CONSUMED_PREBINDINGS[id(runtime)] = takeover.prebinding
        boundary()
        if session._permit not in {takeover.permit, None}:  # noqa: SLF001
            _fail("B2-C takeover permit changed during finish-forward")
        session._permit = None  # noqa: SLF001
        boundary()
        session._state = "COMPANION_ESCROW_UNCONSUMED"  # noqa: SLF001
        boundary()
        b2b_v1._LIVE_SESSIONS.pop(id(session), None)  # noqa: SLF001
        b2b_v1._QUARANTINED_SESSIONS[id(session)] = session  # noqa: SLF001
        boundary()
        _LIVE_TAKEOVERS[id(session)] = takeover

    try:
        apply(inject_fault=True)
    except BaseException:
        apply(inject_fault=False)


def _finish_consume_commit(
    takeover: _H1SupervisorBirthTakeoverV1,
    prefix: _H1SupervisorNativeLaunchPrefixV1,
    consume_record: _BirthJournalRecordV1,
) -> None:
    """Idempotently publish the irreversible permit-consumption edge."""

    session = takeover.session

    def apply(*, inject_fault: bool) -> None:
        step = 0

        def boundary() -> None:
            nonlocal step
            step += 1
            if inject_fault and _TEST_ONLY_CONSUME_COMMIT_FAULT_AFTER_STEP == step:
                raise RuntimeError(
                    f"injected B2-C consume commit fault after step {step}"
                )

        prefix.consume_record = consume_record
        takeover.consume_record = consume_record
        boundary()
        takeover.native_prefix = prefix
        boundary()
        takeover.state = "CONSUME_COMMITTED"
        takeover.prebinding._state = "CONSUME_COMMITTED"
        boundary()
        session._state = "COMPANION_CONSUME_COMMITTED"  # noqa: SLF001
        prefix.state = "CONSUME_COMMITTED"

    try:
        apply(inject_fault=True)
    except BaseException:
        apply(inject_fault=False)


def _verify_prebinding_bytes(
    prebinding: H1SupervisorBirthSourcePrebindingV1,
    *,
    allowed_states: set[str],
) -> dict[str, Any]:
    if (
        type(prebinding) is not H1SupervisorBirthSourcePrebindingV1
        or not _same_owner(prebinding)
        or prebinding._state not in allowed_states
        or prebinding._manifest_fd < 0
        or prebinding._manifest_witness_fd < 0
    ):
        _fail("B2-C source prebinding is not live in the required state")
    raw = prebinding._canonical_bytes
    manifest_status = os.fstat(prebinding._manifest_fd)
    manifest_witness_status = os.fstat(prebinding._manifest_witness_fd)
    manifest_fact = prebinding._manifest_fact
    if (
        fcntl.fcntl(prebinding._manifest_fd, F_GET_SEALS) != REQUIRED_SEALS
        or fcntl.fcntl(prebinding._manifest_witness_fd, F_GET_SEALS)
        != REQUIRED_SEALS
        or not e5a_v1._same_open_file_description_for_close(  # noqa: SLF001
            prebinding._manifest_fd, prebinding._manifest_witness_fd
        )
        or os.pread(prebinding._manifest_fd, len(raw) + 1, 0) != raw
        or fcntl.fcntl(prebinding._manifest_fd, fcntl.F_GETFD)
        & fcntl.FD_CLOEXEC
        == 0
        or fcntl.fcntl(prebinding._manifest_witness_fd, fcntl.F_GETFD)
        & fcntl.FD_CLOEXEC
        == 0
        or (
            manifest_status.st_dev,
            manifest_status.st_ino,
            manifest_status.st_mode,
            manifest_status.st_size,
        )
        != (
            manifest_fact.get("device"),
            manifest_fact.get("inode"),
            manifest_fact.get("mode"),
            manifest_fact.get("size"),
        )
        or (
            manifest_witness_status.st_dev,
            manifest_witness_status.st_ino,
            manifest_witness_status.st_mode,
            manifest_witness_status.st_size,
        )
        != (
            manifest_fact.get("device"),
            manifest_fact.get("inode"),
            manifest_fact.get("mode"),
            manifest_fact.get("size"),
        )
    ):
        _fail("B2-C sealed source prebinding changed")
    if set(prebinding._source_fds) != set(_SOURCE_PATHS) or set(
        prebinding._source_facts
    ) != set(_SOURCE_PATHS):
        _fail("B2-C retained source inventory changed")
    for label, path in _SOURCE_PATHS.items():
        canonical, witness = prebinding._source_fds[label]
        fact = prebinding._source_facts[label]
        status = os.fstat(canonical)
        named = os.stat(path, follow_symlinks=False)
        source = os.pread(canonical, MAX_JOURNAL_RECORD_BYTES + 1, 0)
        if (
            not e5a_v1._same_open_file_description_for_close(  # noqa: SLF001
                canonical, witness
            )
            or fcntl.fcntl(canonical, fcntl.F_GETFD) & fcntl.FD_CLOEXEC == 0
            or fcntl.fcntl(witness, fcntl.F_GETFD) & fcntl.FD_CLOEXEC == 0
            or (status.st_dev, status.st_ino, status.st_mode, status.st_size)
            != (named.st_dev, named.st_ino, named.st_mode, named.st_size)
            or len(source) != status.st_size
            or hashlib.sha256(source).hexdigest() != fact.get("sha256")
            or fact.get("device") != status.st_dev
            or fact.get("inode") != status.st_ino
            or fact.get("mode") != status.st_mode
            or fact.get("size") != status.st_size
        ):
            _fail("B2-C retained source FD/OFD replay changed")
    code_raw = native_v1.X86_64_TEXT_BYTES
    code_status = os.fstat(prebinding._code_fd)
    code_witness_status = os.fstat(prebinding._code_witness_fd)
    if (
        prebinding._code_fd < 0
        or prebinding._code_witness_fd < 0
        or prebinding._code_rx_address <= 0
        or fcntl.fcntl(prebinding._code_fd, F_GET_SEALS) != REQUIRED_SEALS
        or fcntl.fcntl(prebinding._code_witness_fd, F_GET_SEALS) != REQUIRED_SEALS
        or not e5a_v1._same_open_file_description_for_close(  # noqa: SLF001
            prebinding._code_fd, prebinding._code_witness_fd
        )
        or os.pread(prebinding._code_fd, len(code_raw) + 1, 0) != code_raw
        or ctypes.string_at(prebinding._code_rx_address, len(code_raw)) != code_raw
        or ctypes.cast(
            prebinding._code_rx_function, ctypes.c_void_p
        ).value
        != prebinding._code_rx_address
        or prebinding._code_fact.get("memfd_seals") != REQUIRED_SEALS
        or fcntl.fcntl(prebinding._code_fd, fcntl.F_GETFD)
        & fcntl.FD_CLOEXEC
        == 0
        or fcntl.fcntl(prebinding._code_witness_fd, fcntl.F_GETFD)
        & fcntl.FD_CLOEXEC
        == 0
        or (
            code_status.st_dev,
            code_status.st_ino,
            code_status.st_mode,
            code_status.st_size,
        )
        != (
            prebinding._code_fact.get("memfd_device"),
            prebinding._code_fact.get("memfd_inode"),
            prebinding._code_fact.get("memfd_mode"),
            prebinding._code_fact.get("memfd_size"),
        )
        or (
            code_witness_status.st_dev,
            code_witness_status.st_ino,
            code_witness_status.st_mode,
            code_witness_status.st_size,
        )
        != (
            prebinding._code_fact.get("memfd_device"),
            prebinding._code_fact.get("memfd_inode"),
            prebinding._code_fact.get("memfd_mode"),
            prebinding._code_fact.get("memfd_size"),
        )
        or prebinding._code_fact.get("writable_code_mapping_ever_created")
        is not False
    ):
        _fail("B2-C sealed code memfd or direct RX mapping changed")
    mapping_match = False
    for row in Path("/proc/self/maps").read_text(encoding="ascii").splitlines():
        columns = row.split()
        if len(columns) < 5 or "-" not in columns[0] or ":" not in columns[3]:
            continue
        start_text, end_text = columns[0].split("-", 1)
        start, end = int(start_text, 16), int(end_text, 16)
        major_text, minor_text = columns[3].split(":", 1)
        if (
            start == prebinding._code_rx_address
            and end >= prebinding._code_rx_address + len(code_raw)
            and columns[1].startswith("r-x")
            and "w" not in columns[1]
            and int(columns[2], 16) == 0
            and int(major_text, 16) == os.major(code_status.st_dev)
            and int(minor_text, 16) == os.minor(code_status.st_dev)
            and int(columns[4]) == code_status.st_ino
        ):
            mapping_match = True
            break
    if not mapping_match:
        _fail("B2-C code mapping is not the exact sealed-memfd direct RX extent")
    document = ids_v1.loads_canonical_json(raw)
    payload = dict(document)
    supplied = payload.pop("supervisor_birth_source_prebinding_id", None)
    if (
        supplied != prebinding._manifest_id
        or _domain_id(
            domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN,
            payload,
        )
        != supplied
        or payload.get("runtime_successor_id") != prebinding._runtime.successor_id
        or payload.get("retained_source_files")
        != [
            prebinding._source_facts[label]
            for label in sorted(prebinding._source_facts)
        ]
        or payload.get("sealed_code_memfd_and_direct_rx")
        != prebinding._code_fact
        or payload.get("native_anonymous_development_mapping_used") is not False
    ):
        _fail("B2-C source prebinding content changed")
    return document


def _take_over_b2b_session(
    session: b2b_v1.H1GuardianRuntimeGenesisV1,
    permit: b2b_v1.H1SupervisorBirthPermitV1,
    prebinding: H1SupervisorBirthSourcePrebindingV1,
    *,
    journal_directory: Path | str,
) -> _H1SupervisorBirthTakeoverV1:
    """Atomically consume the B2-B live session; never call B2-B verify later."""

    _validate_live_code_closure()
    path = Path(os.path.abspath(os.fspath(journal_directory)))
    if path == session._journal_path:  # noqa: SLF001
        _fail("B2-C birth journal must be distinct from the B2-B journal")
    journal: _BirthJournalV1 | None = None
    original_mask = e5a_v1._block_fd_publication_signals()  # noqa: SLF001
    try:
        with _B2C_LOCK:
            with b2b_v1._B2B_LOCK:  # noqa: SLF001
                runtime = session._runtime  # noqa: SLF001
                source = runtime._source_lease  # noqa: SLF001
                with b2a_v1._ADAPTER_LOCK:  # noqa: SLF001
                    with source._lock:  # noqa: SLF001
                        with runtime._lock:  # noqa: SLF001
                            with e5a_v1._FD_OWNERSHIP_LOCK:  # noqa: SLF001
                                if (
                                    type(session)
                                    is not b2b_v1.H1GuardianRuntimeGenesisV1
                                    or not b2b_v1._same_owner(session)  # noqa: SLF001
                                    or type(permit)
                                    is not b2b_v1.H1SupervisorBirthPermitV1
                                    or session._permit is not permit  # noqa: SLF001
                                    or permit._issuer is not b2b_v1._PERMIT_ISSUER  # noqa: SLF001
                                    or permit._session_id != id(session)  # noqa: SLF001
                                    or session._permit_record is None  # noqa: SLF001
                                    or permit._canonical_bytes  # noqa: SLF001
                                    != session._permit_record.canonical_bytes  # noqa: SLF001
                                    or session._state != "RUNNING"  # noqa: SLF001
                                    or b2b_v1._LIVE_SESSIONS.get(id(session))  # noqa: SLF001
                                    is not session
                                    or b2b_v1._RUNTIME_RESERVATIONS.get(id(runtime))  # noqa: SLF001
                                    is not session
                                    or prebinding._runtime is not runtime
                                    or _LIVE_PREBINDINGS.get(id(runtime))
                                    is not prebinding
                                    or id(session) in _LIVE_TAKEOVERS
                                    or id(session) in _QUARANTINED_TAKEOVERS
                                ):
                                    _fail("B2-C takeover inputs are not exact and live")
                                b2b_document = b2b_v1._verify_running_under_locks(  # noqa: SLF001
                                    session
                                )
                                prebind_document = _verify_prebinding_bytes(
                                    prebinding,
                                    allowed_states={"LIVE_PRE_RUNNING"},
                                )
                                permit_document = ids_v1.loads_canonical_json(
                                    permit._canonical_bytes  # noqa: SLF001
                                )
                                permit_payload = dict(permit_document)
                                permit_id = permit_payload.pop(
                                    "actual_process_birth_permit_id", None
                                )
                                if (
                                    prebind_document["runtime_successor_id"]
                                    != runtime.successor_id
                                    or prebind_document["guardian_identity"]
                                    != session._preregistration.to_document()[  # noqa: SLF001
                                        "expected_guardian_identity"
                                    ]
                                    or permit_id != session._permit_record.record_id  # noqa: SLF001
                                    or domains_v15.extension_content_id_v15(
                                        domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_PERMIT_V1_DOMAIN,
                                        permit_payload,
                                    )
                                    != permit_id
                                    or permit_document.get("permit_state")
                                    != "ISSUED_UNCONSUMED"
                                    or permit_document.get(
                                        "actual_process_birth_intent_id"
                                    )
                                    != session._intent.record_id  # noqa: SLF001
                                ):
                                    _fail("B2-C prebinding/session/permit identity join changed")
                                journal = _BirthJournalV1(path)
                                takeover_payload = {
                                    "schema": "acfqp.k7_h1_supervisor_birth_companion_takeover.v1",
                                    "schema_version": SCHEMA_VERSION,
                                    "profile_key": PROFILE_KEY,
                                    "supervisor_birth_source_prebinding_id": prebinding.prebinding_id,
                                    "guardian_session_genesis_id": session.session_id,
                                    "actual_process_birth_intent_id": session._intent.record_id,  # noqa: SLF001
                                    "actual_process_birth_permit_id": session._permit_record.record_id,  # noqa: SLF001
                                    "runtime_successor_id": runtime.successor_id,
                                    "b2b_state_before": "RUNNING",
                                    "permit_state_before": "ISSUED_UNCONSUMED",
                                    "companion_state_after": "TAKEN_OVER_UNCONSUMED",
                                    "b2b_live_registry_removed_atomically": True,
                                    "b2b_quarantine_is_fd_and_atfork_escrow": True,
                                    "permit_consumed_by_takeover": False,
                                    "b2b_verify_forbidden_after_takeover": True,
                                    "native_image": native_v1.verify_supervisor_birth_native_image_v1(),
                                    "b2b_genesis_readiness": b2b_document["readiness"],
                                    **_locked_claims(),
                                }
                                record = journal.append(
                                    domain=domains_v16.CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_COMPANION_TAKEOVER_V1_DOMAIN,
                                    id_field="supervisor_birth_companion_takeover_id",
                                    event="COMPANION_TAKEOVER",
                                    payload=takeover_payload,
                                )
                                takeover = _H1SupervisorBirthTakeoverV1(
                                    session,
                                    prebinding,
                                    permit,
                                    session._permit_record,  # noqa: SLF001
                                    journal,
                                    record,
                                    os.getpid(),
                                    threading.current_thread(),
                                    threading.get_ident(),
                                    "TAKEN_OVER_UNCONSUMED",
                                    _issuer=_TAKEOVER_ISSUER,
                                )
                                _finish_takeover_commit(takeover)
                                return takeover
    except BaseException as error:
        if journal is not None and getattr(error, "cleanup_handle", None) is not journal:
            journal.close()
        raise
    finally:
        e5a_v1._restore_fd_publication_signals(original_mask)  # noqa: SLF001


def _prepare_h1_actual_observed_supervisor_birth_v1(
    runtime: b2a_v1.H1E5ARuntimeLeaseSuccessorV1,
    *,
    b2b_preregistration: b2b_v1.H1GuardianRuntimeGenesisPreregistrationV1,
    b2b_journal_directory: Path | str,
    birth_journal_directory: Path | str,
) -> _H1SupervisorBirthTakeoverV1:
    """Freeze source, start B2-B, and take over its permit without a gap.

    The outer lock/signal window is intentional.  No caller can receive the
    process-local prebinding or the transient B2-B ``RUNNING`` session before
    the companion has removed the old live authority and installed its own
    ``TAKEN_OVER_UNCONSUMED`` state.
    """

    _validate_live_code_closure()
    original_mask = e5a_v1._block_fd_publication_signals()  # noqa: SLF001
    prebinding: H1SupervisorBirthSourcePrebindingV1 | None = None
    session: b2b_v1.H1GuardianRuntimeGenesisV1 | None = None
    result: _H1SupervisorBirthTakeoverV1 | None = None
    try:
        with _B2C_LOCK:
            with b2b_v1._B2B_LOCK:  # noqa: SLF001
                source = runtime._source_lease  # noqa: SLF001
                with b2a_v1._ADAPTER_LOCK:  # noqa: SLF001
                    with source._lock:  # noqa: SLF001
                        with runtime._lock:  # noqa: SLF001
                            with e5a_v1._FD_OWNERSHIP_LOCK:  # noqa: SLF001
                                _require_exact_prepared_runtime(runtime)
                                prebinding = prebind_h1_actual_observed_supervisor_birth_v1(
                                    runtime
                                )
                                session = b2b_v1.start_h1_guardian_runtime_genesis_v1(
                                    runtime,
                                    preregistration=b2b_preregistration,
                                    journal_directory=b2b_journal_directory,
                                )
                                result = _take_over_b2b_session(
                                    session,
                                    session.permit,
                                    prebinding,
                                    journal_directory=birth_journal_directory,
                                )
                                return result
    except BaseException:
        # A completed takeover is never rolled back.  Before takeover, the
        # original B2-B close remains the exact unconsumed cleanup path.
        if result is None and session is not None:
            if session._state == "RUNNING":  # noqa: SLF001
                b2b_v1.close_h1_guardian_runtime_genesis_v1(session)
            elif session._state not in {"CLOSED", "ABORTED_PRECOMMIT"}:  # noqa: SLF001
                _fail("B2-C prepare failed after an ambiguous B2-B transition")
        if (
            result is None
            and prebinding is not None
            and prebinding._state == "LIVE_PRE_RUNNING"
        ):
            close_h1_supervisor_birth_source_prebinding_v1(prebinding)
        raise
    finally:
        e5a_v1._restore_fd_publication_signals(original_mask)  # noqa: SLF001


def _verify_current_takeover(
    takeover: _H1SupervisorBirthTakeoverV1,
    *,
    allowed_states: set[str],
) -> None:
    """B2-C current verifier; intentionally never calls B2-B verification."""

    _validate_live_code_closure()
    session = takeover.session
    runtime = session._runtime  # noqa: SLF001
    if (
        type(takeover) is not _H1SupervisorBirthTakeoverV1
        or takeover._issuer is not _TAKEOVER_ISSUER
        or takeover.owner_pid != os.getpid()
        or takeover.owner_thread_id != threading.get_ident()
        or takeover.owner_thread is not threading.current_thread()
        or takeover.state not in allowed_states
        or _LIVE_TAKEOVERS.get(id(session)) is not takeover
        or session._state != "COMPANION_ESCROW_UNCONSUMED"  # noqa: SLF001
        or b2b_v1._LIVE_SESSIONS.get(id(session)) is not None  # noqa: SLF001
        or b2b_v1._QUARANTINED_SESSIONS.get(id(session)) is not session  # noqa: SLF001
        or b2b_v1._RUNTIME_RESERVATIONS.get(id(runtime)) is not session  # noqa: SLF001
        or runtime._state != "RUNNING"  # noqa: SLF001
        or b2a_v1._LIVE_RUNTIME_LEASES.get(id(runtime)) is not runtime  # noqa: SLF001
        or takeover.prebinding._state != "TAKEN_OVER_UNCONSUMED"
        or _CONSUMED_PREBINDINGS.get(id(runtime)) is not takeover.prebinding
        or takeover.permit._issuer is not b2b_v1._PERMIT_ISSUER  # noqa: SLF001
        or takeover.permit._session_id != id(session)  # noqa: SLF001
        or takeover.permit._canonical_bytes  # noqa: SLF001
        != takeover.permit_record.canonical_bytes
        or session._permit_record is not takeover.permit_record  # noqa: SLF001
    ):
        _fail("B2-C current takeover identity or one-way state changed")
    _verify_prebinding_bytes(
        takeover.prebinding,
        allowed_states={"TAKEN_OVER_UNCONSUMED"},
    )
    permit_document = ids_v1.loads_canonical_json(
        takeover.permit._canonical_bytes  # noqa: SLF001
    )
    permit_payload = dict(permit_document)
    permit_id = permit_payload.pop("actual_process_birth_permit_id", None)
    if (
        permit_id != takeover.permit_record.record_id
        or domains_v15.extension_content_id_v15(
            domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_PERMIT_V1_DOMAIN,
            permit_payload,
        )
        != permit_id
    ):
        _fail("B2-C current permit content ID changed")
    b2a_v1._validate_e5a_bridge()  # noqa: SLF001
    b2a_v1._verify_source_lease_retired(runtime)  # noqa: SLF001
    b2a_v1._verify_runtime_fd_registry_unlocked(runtime)  # noqa: SLF001
    b2b_v1._verify_retained_sources_and_records(session)  # noqa: SLF001
    for slot in ("cgroup:kill", "grant:SUPERVISOR:CONTROL"):
        b2b_v1._verify_managed_fd(session, slot)  # noqa: SLF001
    takeover.journal.verify()
    takeover_document = _verify_birth_record(
        takeover.takeover_record,
        domain=domains_v16.CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_COMPANION_TAKEOVER_V1_DOMAIN,
        id_field="supervisor_birth_companion_takeover_id",
    )
    if (
        takeover_document.get("guardian_session_genesis_id") != session.session_id
        or takeover_document.get("actual_process_birth_permit_id")
        != takeover.permit_record.record_id
        or takeover_document.get("supervisor_birth_source_prebinding_id")
        != takeover.prebinding.prebinding_id
    ):
        _fail("B2-C current takeover record identity join changed")


def _new_seqpacket_pair(*, receiver_passcred: bool) -> tuple[int, int]:
    first: socket.socket | None = None
    second: socket.socket | None = None
    try:
        first, second = socket.socketpair(
            socket.AF_UNIX,
            socket.SOCK_SEQPACKET | getattr(socket, "SOCK_CLOEXEC", 0),
        )
        first.set_inheritable(False)
        second.set_inheritable(False)
        first.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_PASSCRED,
            1 if receiver_passcred else 0,
        )
        second.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 0)
        if (
            first.family != socket.AF_UNIX
            or second.family != socket.AF_UNIX
            or first.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
            != socket.SOCK_SEQPACKET
            or second.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
            != socket.SOCK_SEQPACKET
            or not first.getblocking()
            or not second.getblocking()
            or first.get_inheritable()
            or second.get_inheritable()
            or first.getsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED)
            != int(receiver_passcred)
            or second.getsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED) != 0
        ):
            _fail("B2-C seqpacket credential endpoint grammar changed")
        return first.detach(), second.detach()
    except BaseException:
        if second is not None:
            second.close()
        if first is not None:
            first.close()
        raise


def _fd_at_least(descriptor: int, minimum: int) -> int:
    if descriptor >= minimum:
        return descriptor
    replacement = int(_FCNTL_FCNTL(descriptor, fcntl.F_DUPFD_CLOEXEC, minimum))
    _RAW_OS_CLOSE(descriptor)
    return replacement


def _close_unconsumed_native_prefix(
    prefix: _H1SupervisorNativeLaunchPrefixV1,
) -> None:
    """Close setup-only resources; never use after the native entry begins."""

    if prefix.state not in {"PREPARED_UNCONSUMED", "SETUP_FAILED"}:
        _fail("B2-C cannot roll back a consumed native prefix")
    if prefix.creator_pid_cell_mapping > 0:
        native_v1._LIBC.munmap(  # noqa: SLF001
            ctypes.c_void_p(prefix.creator_pid_cell_mapping), PID_CELL_BYTES
        )
        prefix.creator_pid_cell_mapping = 0
    if prefix.guardian_pid_cell_read_mapping > 0:
        native_v1._LIBC.munmap(  # noqa: SLF001
            ctypes.c_void_p(prefix.guardian_pid_cell_read_mapping), PID_CELL_BYTES
        )
        prefix.guardian_pid_cell_read_mapping = 0
    for field_name in (
        "child_gate_source_fd",
        "parent_gate_fd",
        "creator_pid_cell_fd",
        "creator_cgroup_grant_fd",
        "pid_cell_reader_fd",
        "pid_cell_witness_fd",
        "pid_cell_sealer_fd",
        "escrow_sender_fd",
        "escrow_receiver_fd",
    ):
        descriptor = int(getattr(prefix, field_name))
        if descriptor >= 0:
            try:
                _RAW_OS_CLOSE(descriptor)
            except OSError:
                pass
            setattr(prefix, field_name, -1)
    prefix.state = "CLOSED_UNCONSUMED"


def _prepare_native_launch_prefix_under_locks(
    takeover: _H1SupervisorBirthTakeoverV1,
) -> _H1SupervisorNativeLaunchPrefixV1:
    """Allocate every fallible input before the irreversible permit record."""

    _verify_current_takeover(takeover, allowed_states={"TAKEN_OVER_UNCONSUMED"})
    if signal.getsignal(signal.SIGCHLD) is not signal.SIG_DFL:
        _fail("B2-C requires the default SIGCHLD disposition")
    b2b_v1._single_thread_identity()  # noqa: SLF001
    for descriptor in (0, 1, 2):
        try:
            os.fstat(descriptor)
            _FCNTL_FCNTL(descriptor, fcntl.F_GETFD)
        except OSError as error:
            raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
                "B2-C requires valid inherited standard descriptors"
            ) from error
    session = takeover.session
    grant_fd = b2b_v1._verify_managed_fd(  # noqa: SLF001
        session, "grant:SUPERVISOR:CONTROL"
    )

    parent_gate_fd = -1
    child_gate_fd = -1
    escrow_receiver_fd = -1
    escrow_sender_fd = -1
    pid_cell_fd = -1
    pid_cell_witness_fd = -1
    pid_cell_reader_fd = -1
    creator_pid_cell_fd = -1
    creator_cgroup_grant_fd = -1
    creator_mapping = 0
    guardian_read_mapping = 0
    prefix: _H1SupervisorNativeLaunchPrefixV1 | None = None
    try:
        parent_gate_fd, child_gate_fd = _new_seqpacket_pair(receiver_passcred=True)
        child_gate_fd = _fd_at_least(
            child_gate_fd, native_v1.FUTURE_WRAPPER_CHILD_GATE_SOURCE_FD_MINIMUM
        )
        escrow_receiver_fd, escrow_sender_fd = _new_seqpacket_pair(
            receiver_passcred=True
        )

        pid_cell_fd = os.memfd_create(
            "acfqp-h1-b2c-shared-pid-cell", MFD_CLOEXEC | MFD_ALLOW_SEALING
        )
        os.ftruncate(pid_cell_fd, PID_CELL_BYTES)
        pid_cell_witness_fd = int(
            _FCNTL_FCNTL(pid_cell_fd, fcntl.F_DUPFD_CLOEXEC, 3)
        )
        pid_cell_reader_fd = os.open(
            f"/proc/self/fd/{pid_cell_fd}", os.O_RDONLY | os.O_CLOEXEC
        )
        creator_pid_cell_fd = int(
            _FCNTL_FCNTL(pid_cell_fd, fcntl.F_DUPFD_CLOEXEC, 3)
        )
        if not e5a_v1._same_open_file_description_for_close(  # noqa: SLF001
            pid_cell_fd, pid_cell_witness_fd
        ) or not e5a_v1._same_open_file_description_for_close(  # noqa: SLF001
            pid_cell_fd, creator_pid_cell_fd
        ):
            _fail("B2-C shared PID-cell descriptors are not one OFD")
        reader_status = os.fstat(pid_cell_reader_fd)
        sealer_status = os.fstat(pid_cell_fd)
        if (
            _FCNTL_FCNTL(pid_cell_reader_fd, fcntl.F_GETFL) & os.O_ACCMODE
            != os.O_RDONLY
            or (reader_status.st_dev, reader_status.st_ino)
            != (sealer_status.st_dev, sealer_status.st_ino)
            or e5a_v1._same_open_file_description_for_close(  # noqa: SLF001
                pid_cell_fd, pid_cell_reader_fd
            )
        ):
            _fail("B2-C guardian PID-cell reader is not an independent read OFD")
        creator_cgroup_grant_fd = int(
            _FCNTL_FCNTL(grant_fd, fcntl.F_DUPFD_CLOEXEC, 3)
        )
        if not e5a_v1._same_open_file_description_for_close(  # noqa: SLF001
            grant_fd, creator_cgroup_grant_fd
        ):
            _fail("B2-C creator cgroup grant is not a one-shot same-OFD duplicate")
        sensitive = {
            parent_gate_fd,
            child_gate_fd,
            escrow_receiver_fd,
            escrow_sender_fd,
            pid_cell_fd,
            pid_cell_witness_fd,
            pid_cell_reader_fd,
            creator_pid_cell_fd,
            creator_cgroup_grant_fd,
        }
        if (
            len(sensitive) != 9
            or min(sensitive) < 3
            or child_gate_fd
            < native_v1.FUTURE_WRAPPER_CHILD_GATE_SOURCE_FD_MINIMUM
            or any(
                _FCNTL_FCNTL(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC == 0
                for descriptor in sensitive
            )
        ):
            _fail("B2-C launch descriptors overlap or lost CLOEXEC")

        libc = native_v1._LIBC  # noqa: SLF001
        libc.mmap.argtypes = (
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_long,
        )
        libc.mmap.restype = ctypes.c_void_p
        mapped = libc.mmap(
            None,
            PID_CELL_BYTES,
            mmap.PROT_READ | mmap.PROT_WRITE,
            mmap.MAP_SHARED,
            creator_pid_cell_fd,
            0,
        )
        creator_mapping = int(mapped) if mapped is not None else 0
        if creator_mapping in {0, ctypes.c_void_p(-1).value}:
            _fail("B2-C shared PID-cell creator mapping failed")
        read_mapped = libc.mmap(
            None,
            PID_CELL_BYTES,
            mmap.PROT_READ,
            mmap.MAP_SHARED,
            pid_cell_reader_fd,
            0,
        )
        guardian_read_mapping = int(read_mapped) if read_mapped is not None else 0
        if guardian_read_mapping in {0, ctypes.c_void_p(-1).value}:
            _fail("B2-C guardian PID-cell read mapping failed")

        pidfd_cell = ctypes.c_int(-1)
        clone_args = native_v1.CloneArgsV1(
            flags=native_v1.REQUIRED_CLONE_FLAGS,
            pidfd=ctypes.addressof(pidfd_cell),
            child_tid=0,
            parent_tid=creator_mapping + PID_CELL_PID_OFFSET,
            exit_signal=int(signal.SIGCHLD),
            stack=0,
            stack_size=0,
            tls=0,
            set_tid=0,
            set_tid_size=0,
            cgroup=creator_cgroup_grant_fd,
        )
        parent_edge = native_v1.NativeParentEdgeV1(0, 0, 0, 0)
        nonce = (
            os.getrandom(16)
            if callable(getattr(os, "getrandom", None))
            else os.urandom(16)
        )
        nonce_ascii = nonce.hex().encode("ascii")
        cell_withdrawn_frame = b"ACFQP:CELL_WITHDRAWN:v1:" + nonce_ascii
        gate_ready_frame = b"ACFQP:CHILD_GATE_READY:v1:" + nonce_ascii
        release_frame = b"ACFQP:SUPERVISOR_RELEASE:v1:" + nonce_ascii
        if any(
            not 0 < len(frame) <= MAX_PROTOCOL_FRAME_BYTES
            for frame in (cell_withdrawn_frame, gate_ready_frame, release_frame)
        ):
            _fail("B2-C nonce-bound frame exceeds the native grammar")
        cell_buffer = ctypes.create_string_buffer(
            cell_withdrawn_frame, len(cell_withdrawn_frame)
        )
        ready_buffer = ctypes.create_string_buffer(
            gate_ready_frame, len(gate_ready_frame)
        )
        release_buffer = ctypes.create_string_buffer(release_frame, len(release_frame))
        launch_args = native_v1.NativeLaunchArgsV1(
            clone_args=ctypes.addressof(clone_args),
            creator_pid_cell_mapping=creator_mapping,
            pid_cell_mapping_bytes=PID_CELL_BYTES,
            creator_pid_cell_fd=creator_pid_cell_fd,
            one_shot_cgroup_grant_fd=creator_cgroup_grant_fd,
            child_gate_fd=child_gate_fd,
            parent_edge=ctypes.addressof(parent_edge),
            cell_withdrawn_frame=ctypes.addressof(cell_buffer),
            cell_withdrawn_frame_bytes=len(cell_withdrawn_frame),
            gate_ready_frame=ctypes.addressof(ready_buffer),
            gate_ready_frame_bytes=len(gate_ready_frame),
            release_frame=ctypes.addressof(release_buffer),
            release_frame_bytes=len(release_frame),
        )
        launch_args_pointer = ctypes.pointer(launch_args)
        prefix = _H1SupervisorNativeLaunchPrefixV1(
            takeover=takeover,
            consume_record=None,
            clone_args=clone_args,
            launch_args=launch_args,
            parent_edge=parent_edge,
            pidfd_cell=pidfd_cell,
            cell_withdrawn_buffer=cell_buffer,
            gate_ready_buffer=ready_buffer,
            release_buffer=release_buffer,
            launch_args_pointer=launch_args_pointer,
            release_frame=release_frame,
            parent_gate_fd=parent_gate_fd,
            child_gate_source_fd=child_gate_fd,
            pid_cell_sealer_fd=pid_cell_fd,
            pid_cell_witness_fd=pid_cell_witness_fd,
            pid_cell_reader_fd=pid_cell_reader_fd,
            guardian_pid_cell_read_mapping=guardian_read_mapping,
            creator_pid_cell_fd=creator_pid_cell_fd,
            creator_pid_cell_mapping=creator_mapping,
            creator_cgroup_grant_fd=creator_cgroup_grant_fd,
            escrow_receiver_fd=escrow_receiver_fd,
            escrow_sender_fd=escrow_sender_fd,
            creator_pidfd_fd=-1,
            escrowed_pidfd_fd=-1,
            native_return=None,
            child_gate_source_close_errno=None,
            protocol_records={},
            protocol_facts={},
            state="PREPARED_UNCONSUMED",
            _issuer=_NATIVE_PREFIX_ISSUER,
        )
        return prefix
    except BaseException:
        if prefix is not None:
            prefix.state = "SETUP_FAILED"
            _close_unconsumed_native_prefix(prefix)
        else:
            if creator_mapping not in {0, ctypes.c_void_p(-1).value}:
                native_v1._LIBC.munmap(  # noqa: SLF001
                    ctypes.c_void_p(creator_mapping), PID_CELL_BYTES
                )
            if guardian_read_mapping not in {0, ctypes.c_void_p(-1).value}:
                native_v1._LIBC.munmap(  # noqa: SLF001
                    ctypes.c_void_p(guardian_read_mapping), PID_CELL_BYTES
                )
            for descriptor in (
                creator_pid_cell_fd,
                creator_cgroup_grant_fd,
                pid_cell_reader_fd,
                pid_cell_witness_fd,
                pid_cell_fd,
                escrow_sender_fd,
                escrow_receiver_fd,
                child_gate_fd,
                parent_gate_fd,
            ):
                if descriptor >= 0:
                    try:
                        _RAW_OS_CLOSE(descriptor)
                    except OSError:
                        pass
        raise


def _recv_exact_seqpacket(
    descriptor: int,
    *,
    expected_frame: bytes,
    expected_credentials: tuple[int, int, int],
    expected_rights_count: int,
) -> tuple[dict[str, Any], list[int]]:
    if descriptor < 0 or not 0 < len(expected_frame) <= MAX_PROTOCOL_FRAME_BYTES:
        _fail("B2-C exact seqpacket receive inputs changed")
    poller = select.poll()
    poller.register(descriptor, select.POLLIN)
    events = poller.poll(int(PROTOCOL_TIMEOUT_SECONDS * 1000))
    if (
        len(events) != 1
        or events[0][0] != descriptor
        or events[0][1] & select.POLLIN == 0
        or events[0][1] & (select.POLLERR | select.POLLNVAL)
        or events[0][1] & ~(select.POLLIN | select.POLLHUP)
    ):
        _fail("B2-C exact seqpacket receive did not become solely readable")
    wrapper = socket.socket(fileno=descriptor)
    rights: list[int] = []
    try:
        try:
            data, ancillary, flags, address = wrapper.recvmsg(
                len(expected_frame) + 1,
                socket.CMSG_SPACE(struct.calcsize("=iii"))
                + socket.CMSG_SPACE(struct.calcsize("=i") * max(1, expected_rights_count)),
                getattr(socket, "MSG_CMSG_CLOEXEC", 0),
            )
            credentials: list[tuple[int, int, int]] = []
            unknown = False
            for level, kind, raw in ancillary:
                if level != socket.SOL_SOCKET:
                    unknown = True
                elif kind == socket.SCM_CREDENTIALS:
                    if len(raw) != struct.calcsize("=iii"):
                        unknown = True
                    else:
                        credentials.append(struct.unpack("=iii", raw))
                elif kind == socket.SCM_RIGHTS:
                    if len(raw) == 0 or len(raw) % struct.calcsize("=i"):
                        unknown = True
                    else:
                        installed = array("i")
                        installed.frombytes(raw)
                        rights.extend(int(item) for item in installed)
                else:
                    unknown = True
            allowed_flags = getattr(socket, "MSG_EOR", 0) | getattr(
                socket, "MSG_CMSG_CLOEXEC", 0
            )
            invalid = (
                data != expected_frame
                or address is not None
                or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC)
                or flags & ~allowed_flags
                or unknown
                or credentials != [expected_credentials]
                or len(rights) != expected_rights_count
                or len(ancillary) != 1 + int(expected_rights_count > 0)
            )
            if invalid:
                for installed_fd in rights:
                    try:
                        _RAW_OS_CLOSE(installed_fd)
                    except OSError:
                        pass
                _fail("B2-C seqpacket payload, credential, rights, or flag grammar changed")
            for installed_fd in rights:
                if _FCNTL_FCNTL(installed_fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC == 0:
                    for cleanup_fd in rights:
                        try:
                            _RAW_OS_CLOSE(cleanup_fd)
                        except OSError:
                            pass
                    _fail("B2-C received descriptor is not CLOEXEC")
            return (
                {
                    "frame_sha256": hashlib.sha256(data).hexdigest(),
                    "frame_bytes": len(data),
                    "credential_pid": credentials[0][0],
                    "credential_uid": credentials[0][1],
                    "credential_gid": credentials[0][2],
                    "rights_count": len(rights),
                    "message_flags": flags,
                    "source_address_absent": True,
                    "truncation_absent": True,
                },
                rights,
            )
        finally:
            wrapper.detach()
    except BaseException:
        raise


def _read_process_start_ticks(pid: int) -> int:
    try:
        raw = Path(f"/proc/{pid}/stat").read_bytes()
    except OSError as error:
        raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
            "B2-C child process identity disappeared"
        ) from error
    close = raw.rfind(b")")
    fields = raw[close + 2 :].split() if close >= 0 else []
    if len(fields) < 20 or not fields[19].isdigit():
        _fail("B2-C child process start ticks are unavailable")
    return int(fields[19])


def _pidfd_fact(descriptor: int) -> dict[str, Any]:
    if descriptor < 0:
        _fail("B2-C creator pidfd is absent")
    try:
        rows = Path(f"/proc/self/fdinfo/{descriptor}").read_text(
            encoding="ascii"
        ).splitlines()
    except OSError as error:
        raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
            "B2-C pidfd fdinfo is unavailable"
        ) from error
    parsed: dict[str, str] = {}
    for row in rows:
        key, separator, value = row.partition(":")
        if separator:
            parsed[key] = value.strip()
    pid_text = parsed.get("Pid")
    nspid_text = parsed.get("NSpid")
    if (
        pid_text is None
        or not pid_text.isdigit()
        or nspid_text is None
        or any(not item.isdigit() for item in nspid_text.split())
    ):
        _fail("B2-C pidfd identity fields changed")
    status = os.fstat(descriptor)
    return {
        "pid": int(pid_text),
        "namespace_pids": [int(item) for item in nspid_text.split()],
        "device": status.st_dev,
        "inode": status.st_ino,
        "mode": status.st_mode,
        "cloexec": bool(
            _FCNTL_FCNTL(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
        ),
    }


def _require_pidfd_child_live(descriptor: int) -> None:
    poller = select.poll()
    poller.register(descriptor, select.POLLIN)
    if poller.poll(0):
        _fail("B2-C supervisor exited before guardian release")


def _read_small_control(directory_fd: int, name: str) -> bytes:
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
        dir_fd=directory_fd,
    )
    try:
        raw = os.pread(descriptor, 65537, 0)
        if len(raw) > 65536:
            _fail("B2-C cgroup control exceeded its exact cap")
        return raw
    finally:
        _RAW_OS_CLOSE(descriptor)


def _parse_single_nonnegative(raw: bytes, label: str) -> int:
    stripped = raw.strip()
    if not stripped.isdigit():
        _fail(f"B2-C {label} is not one nonnegative integer")
    return int(stripped)


def _parse_events(raw: bytes) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in raw.splitlines():
        fields = row.split()
        if len(fields) != 2 or not fields[1].isdigit():
            _fail("B2-C cgroup.events grammar changed")
        key = fields[0].decode("ascii")
        if key in result:
            _fail("B2-C cgroup.events contains a duplicate key")
        result[key] = int(fields[1])
    if "populated" not in result:
        _fail("B2-C cgroup.events omitted populated")
    return result


def _live_cgroup_snapshot(
    runtime: b2a_v1.H1E5ARuntimeLeaseSuccessorV1,
    *,
    child_pid: int,
    sequence: int,
) -> dict[str, Any]:
    b2a_v1._verify_runtime_fd_registry_unlocked(runtime)  # noqa: SLF001
    entries: list[dict[str, Any]] = []
    expected = {
        "CONTROL": ([child_pid], 1, 1),
        "WORKER": ([], 0, 0),
        "BUSINESS": ([], 0, 0),
    }
    for role in ("CONTROL", "WORKER", "BUSINESS"):
        directory_fd = runtime._role_fds[role]  # noqa: SLF001
        raw_procs = _read_small_control(directory_fd, "cgroup.procs")
        try:
            procs = [int(row) for row in raw_procs.splitlines() if row]
        except ValueError as error:
            raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
                "B2-C cgroup.procs grammar changed"
            ) from error
        if len(procs) != len(set(procs)):
            _fail("B2-C cgroup.procs contains a duplicate PID")
        pids_current = _parse_single_nonnegative(
            _read_small_control(directory_fd, "pids.current"),
            f"{role} pids.current",
        )
        events = _parse_events(_read_small_control(directory_fd, "cgroup.events"))
        expected_procs, expected_current, expected_populated = expected[role]
        if (
            sorted(procs) != expected_procs
            or pids_current != expected_current
            or events["populated"] != expected_populated
        ):
            _fail("B2-C live cgroup membership is not the registered singleton")
        entries.append(
            {
                "role": role,
                "directory_identity": list(
                    e5a_v1._registry_fd_identity(directory_fd)  # noqa: SLF001
                ),
                "cgroup_procs": sorted(procs),
                "pids_current": pids_current,
                "populated": events["populated"],
            }
        )
    outer_fd = runtime._outer_fd  # noqa: SLF001
    outer_procs_raw = _read_small_control(outer_fd, "cgroup.procs")
    if outer_procs_raw.strip():
        _fail("B2-C outer cgroup acquired a direct task")
    outer_current = _parse_single_nonnegative(
        _read_small_control(outer_fd, "pids.current"), "outer pids.current"
    )
    outer_events = _parse_events(_read_small_control(outer_fd, "cgroup.events"))
    if outer_current != 1 or outer_events["populated"] != 1:
        _fail("B2-C outer cgroup did not contain exactly one descendant task")
    return {
        "schema": "acfqp.k7_h1_live_cgroup_snapshot.v1",
        "sequence": sequence,
        "child_pid": child_pid,
        "runtime_successor_id": runtime.successor_id,
        "outer_directory_identity": list(
            e5a_v1._registry_fd_identity(outer_fd)  # noqa: SLF001
        ),
        "outer_direct_procs": [],
        "outer_pids_current": outer_current,
        "outer_populated": outer_events["populated"],
        "role_entries": entries,
    }


def _empty_cgroup_snapshot(
    runtime: b2a_v1.H1E5ARuntimeLeaseSuccessorV1,
    *,
    sequence: int,
) -> dict[str, Any]:
    """Read one exact post-reap empty hierarchy snapshot without peak access."""

    b2a_v1._verify_runtime_fd_registry_unlocked(runtime)  # noqa: SLF001
    entries: list[dict[str, Any]] = []
    for role in ("CONTROL", "WORKER", "BUSINESS"):
        directory_fd = runtime._role_fds[role]  # noqa: SLF001
        raw_procs = _read_small_control(directory_fd, "cgroup.procs")
        current = _parse_single_nonnegative(
            _read_small_control(directory_fd, "pids.current"),
            f"{role} pids.current",
        )
        events = _parse_events(_read_small_control(directory_fd, "cgroup.events"))
        memory_current = _parse_single_nonnegative(
            _read_small_control(directory_fd, "memory.current"),
            f"{role} memory.current",
        )
        if raw_procs.strip() or current != 0 or events["populated"] != 0:
            _fail("B2-C post-reap leaf cgroup is not empty")
        entries.append(
            {
                "role": role,
                "directory_identity": list(
                    e5a_v1._registry_fd_identity(directory_fd)  # noqa: SLF001
                ),
                "cgroup_procs": [],
                "pids_current": 0,
                "populated": 0,
                "memory_current_bytes": memory_current,
            }
        )
    outer_fd = runtime._outer_fd  # noqa: SLF001
    outer_procs = _read_small_control(outer_fd, "cgroup.procs")
    outer_current = _parse_single_nonnegative(
        _read_small_control(outer_fd, "pids.current"), "outer pids.current"
    )
    outer_events = _parse_events(_read_small_control(outer_fd, "cgroup.events"))
    outer_memory_current = _parse_single_nonnegative(
        _read_small_control(outer_fd, "memory.current"), "outer memory.current"
    )
    if outer_procs.strip() or outer_current != 0 or outer_events["populated"] != 0:
        _fail("B2-C post-reap outer cgroup is not empty")
    return {
        "schema": "acfqp.k7_h1_empty_cgroup_snapshot.v1",
        "sequence": sequence,
        "runtime_successor_id": runtime.successor_id,
        "outer_directory_identity": list(
            e5a_v1._registry_fd_identity(outer_fd)  # noqa: SLF001
        ),
        "outer_direct_procs": [],
        "outer_pids_current": 0,
        "outer_populated": 0,
        "outer_memory_current_bytes": outer_memory_current,
        "role_entries": entries,
    }


def _wait_for_empty_cgroup_snapshot(
    runtime: b2a_v1.H1E5ARuntimeLeaseSuccessorV1,
    *,
    sequence: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + REAP_TIMEOUT_SECONDS
    last_error: BaseException | None = None
    while time.monotonic() < deadline:
        try:
            return _empty_cgroup_snapshot(runtime, sequence=sequence)
        except ConstructionK7H1ActualObservedSupervisorBirthV1Error as error:
            last_error = error
            time.sleep(0.001)
    raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
        "B2-C hierarchy did not reach exact post-reap emptiness"
    ) from last_error


def _waitid_fact(info: Any) -> dict[str, int]:
    return {
        "si_pid": int(info.si_pid),
        "si_uid": int(info.si_uid),
        "si_signo": int(info.si_signo),
        "si_status": int(info.si_status),
        "si_code": int(info.si_code),
    }


def _require_clean_child_exit(info: Any, child_pid: int) -> dict[str, int]:
    fact = _waitid_fact(info)
    if (
        fact["si_pid"] != child_pid
        or fact["si_uid"] != os.geteuid()
        or fact["si_signo"] != int(signal.SIGCHLD)
        or fact["si_code"] != int(getattr(os, "CLD_EXITED", 1))
        or fact["si_status"] != 0
    ):
        _fail("B2-C child did not expose the exact clean wait status")
    return fact


def _observe_child_and_persist_ack_under_locks(
    prefix: _H1SupervisorNativeLaunchPrefixV1,
) -> None:
    takeover = prefix.takeover
    session = takeover.session
    runtime = session._runtime  # noqa: SLF001
    child_pid = takeover.child_pid
    edge = prefix.parent_edge
    if (
        takeover.native_prefix is not prefix
        or prefix.state != "NATIVE_PARENT_RETURNED_CHILD_LIVE"
        or takeover.state != "NATIVE_PARENT_RETURNED_CHILD_LIVE"
        or session._state != "COMPANION_CONSUME_COMMITTED"  # noqa: SLF001
        or prefix.consume_record is None
        or takeover.consume_record is not prefix.consume_record
        or edge.clone_result != child_pid
        or child_pid <= 0
        or edge.status_bits != native_v1.PARENT_EDGE_REQUIRED_SUCCESS_BITS
        or edge.first_cleanup_error != 0
        or edge.reserved_zero != 0
        or prefix.native_return != child_pid
        or prefix.child_gate_source_close_errno != 0
        or prefix.creator_pidfd_fd < 0
        or prefix.pidfd_cell.value != prefix.creator_pidfd_fd
        or prefix.creator_pid_cell_fd != -1
        or prefix.creator_pid_cell_mapping != 0
        or prefix.creator_cgroup_grant_fd != -1
    ):
        _fail("B2-C native parent edge is not the exact successful withdrawal edge")
    _verify_prebinding_bytes(
        takeover.prebinding, allowed_states={"CONSUME_COMMITTED"}
    )
    b2b_v1._verify_retained_sources_and_records(session)  # noqa: SLF001
    for slot in ("cgroup:kill", "grant:SUPERVISOR:CONTROL"):
        b2b_v1._verify_managed_fd(session, slot)  # noqa: SLF001
    takeover.journal.verify()

    child_credentials = (child_pid, os.geteuid(), os.getegid())
    cell_fact, cell_rights = _recv_exact_seqpacket(
        prefix.parent_gate_fd,
        expected_frame=bytes(prefix.cell_withdrawn_buffer),
        expected_credentials=child_credentials,
        expected_rights_count=0,
    )
    if cell_rights:
        _fail("B2-C CELL_WITHDRAWN unexpectedly installed rights")
    ready_fact, ready_rights = _recv_exact_seqpacket(
        prefix.parent_gate_fd,
        expected_frame=bytes(prefix.gate_ready_buffer),
        expected_credentials=child_credentials,
        expected_rights_count=0,
    )
    if ready_rights:
        _fail("B2-C CHILD_GATE_READY unexpectedly installed rights")

    _FCNTL_FCNTL(prefix.pid_cell_sealer_fd, F_ADD_SEALS, REQUIRED_SEALS)
    if any(
        _FCNTL_FCNTL(descriptor, F_GET_SEALS) != REQUIRED_SEALS
        for descriptor in (
            prefix.pid_cell_sealer_fd,
            prefix.pid_cell_witness_fd,
            prefix.pid_cell_reader_fd,
        )
    ):
        _fail("B2-C shared PID cell did not acquire final seals")
    pid_page_fd = os.pread(prefix.pid_cell_reader_fd, PID_CELL_BYTES + 1, 0)
    pid_page_mapping = ctypes.string_at(
        prefix.guardian_pid_cell_read_mapping, PID_CELL_BYTES
    )
    if (
        len(pid_page_fd) != PID_CELL_BYTES
        or pid_page_mapping != pid_page_fd
        or any(pid_page_fd[struct.calcsize("=i") :])
    ):
        _fail("B2-C sealed PID-cell bytes changed outside the PID slot")
    cell_pid = struct.unpack_from("=i", pid_page_fd, PID_CELL_PID_OFFSET)[0]
    creator_pidfd_fact = _pidfd_fact(prefix.creator_pidfd_fd)
    child_start_ticks = _read_process_start_ticks(child_pid)
    try:
        child_cgroup_raw = Path(f"/proc/{child_pid}/cgroup").read_bytes()
    except OSError as error:
        raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
            "B2-C child cgroup membership disappeared"
        ) from error
    hierarchy = runtime._hierarchy_document  # noqa: SLF001
    control_name = next(
        row["name"] for row in hierarchy["leaves"] if row["role"] == "CONTROL"
    )
    expected_cgroup_suffix = (
        "/" + hierarchy["outer"]["name"] + "/" + control_name
    ).encode("ascii")
    child_cgroup_rows = child_cgroup_raw.splitlines()
    if (
        len(child_cgroup_rows) != 1
        or not child_cgroup_rows[0].startswith(b"0::/")
        or not child_cgroup_rows[0].endswith(expected_cgroup_suffix)
    ):
        _fail("B2-C /proc child cgroup path does not bind the CONTROL leaf")
    _require_pidfd_child_live(prefix.creator_pidfd_fd)
    if (
        cell_pid != child_pid
        or creator_pidfd_fact["pid"] != child_pid
        or not creator_pidfd_fact["cloexec"]
        or cell_fact["credential_pid"] != child_pid
        or ready_fact["credential_pid"] != child_pid
    ):
        _fail("B2-C PID cell, pidfd, SCM credentials, and clone result do not join")
    pid_cell_record = takeover.journal.append(
        domain=domains_v15.CONSTRUCTION_K7_H1_SHARED_PID_CELL_BINDING_V1_DOMAIN,
        id_field="shared_pid_cell_binding_id",
        event="SHARED_PID_CELL_BOUND",
        payload={
            "schema": "acfqp.k7_h1_shared_pid_cell_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "actual_process_birth_permit_consumption_id": prefix.consume_record.record_id,
            "child_pid": child_pid,
            "clone_result": int(edge.clone_result),
            "pidfd_pid": creator_pidfd_fact["pid"],
            "cell_withdrawn_credentials": cell_fact,
            "child_gate_ready_credentials": ready_fact,
            "final_seals": REQUIRED_SEALS,
            "guardian_reader_is_independent_read_ofd": True,
            "pid_cell_tail_zero": True,
            "child_process_start_ticks": child_start_ticks,
            "child_proc_cgroup_sha256": hashlib.sha256(child_cgroup_raw).hexdigest(),
            "child_proc_cgroup_expected_suffix": expected_cgroup_suffix.decode(
                "ascii"
            ),
            **_locked_claims(),
        },
    )
    prefix.protocol_records["pid_cell_binding"] = pid_cell_record

    escrow_frame = (
        b"ACFQP:CREATOR_PIDFD:v1:"
        + prefix.consume_record.record_id[:24].encode("ascii")
    )
    sender = socket.socket(fileno=prefix.escrow_sender_fd)
    try:
        sent = sender.sendmsg(
            [escrow_frame],
            [
                (
                    socket.SOL_SOCKET,
                    socket.SCM_RIGHTS,
                    array("i", [prefix.creator_pidfd_fd]).tobytes(),
                )
            ],
            getattr(socket, "MSG_NOSIGNAL", 0),
        )
    finally:
        sender.detach()
    if sent != len(escrow_frame):
        _fail("B2-C guardian creator pidfd self-escrow send was short")
    escrow_fact, escrow_rights = _recv_exact_seqpacket(
        prefix.escrow_receiver_fd,
        expected_frame=escrow_frame,
        expected_credentials=(os.getpid(), os.geteuid(), os.getegid()),
        expected_rights_count=1,
    )
    escrowed_pidfd = escrow_rights[0]
    prefix.escrowed_pidfd_fd = escrowed_pidfd
    escrowed_fact = _pidfd_fact(escrowed_pidfd)
    if (
        not e5a_v1._same_open_file_description_for_close(  # noqa: SLF001
            prefix.creator_pidfd_fd, escrowed_pidfd
        )
        or escrowed_fact["pid"] != child_pid
        or not escrowed_fact["cloexec"]
    ):
        _fail("B2-C guardian creator pidfd escrow changed OFD or PID identity")
    escrow_record = takeover.journal.append(
        domain=domains_v15.CONSTRUCTION_K7_H1_PIDFD_ESCROW_RECEIPT_V2_DOMAIN,
        id_field="pidfd_escrow_receipt_id",
        event="CREATOR_PIDFD_SELF_ESCROWED",
        payload={
            "schema": "acfqp.k7_h1_pidfd_escrow_receipt.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "shared_pid_cell_binding_id": pid_cell_record.record_id,
            "actual_process_birth_permit_consumption_id": prefix.consume_record.record_id,
            "child_pid": child_pid,
            "creator_is_guardian_pid": os.getpid(),
            "creator_sent_clone3_pidfd": True,
            "child_sent_pidfd": False,
            "same_open_file_description": True,
            "escrow_frame": escrow_fact,
            "escrowed_pidfd": escrowed_fact,
            **_locked_claims(),
        },
    )
    prefix.protocol_records["pidfd_escrow"] = escrow_record
    _RAW_OS_CLOSE(prefix.creator_pidfd_fd)
    prefix.creator_pidfd_fd = -1
    takeover.pidfd = escrowed_pidfd
    for field_name in ("escrow_sender_fd", "escrow_receiver_fd"):
        _RAW_OS_CLOSE(int(getattr(prefix, field_name)))
        setattr(prefix, field_name, -1)

    _require_pidfd_child_live(escrowed_pidfd)
    if _pidfd_fact(escrowed_pidfd) != escrowed_fact:
        _fail("B2-C escrowed pidfd changed before first cgroup snapshot")
    snapshot_one = _live_cgroup_snapshot(runtime, child_pid=child_pid, sequence=1)
    snapshot_one_record = takeover.journal.append(
        domain=domains_v15.CONSTRUCTION_K7_H1_CGROUP_MEMBERSHIP_OBSERVATION_V1_DOMAIN,
        id_field="cgroup_membership_observation_id",
        event="LIVE_CGROUP_SNAPSHOT_1",
        payload={
            **snapshot_one,
            "pidfd_escrow_receipt_id": escrow_record.record_id,
            **_locked_claims(),
        },
    )
    prefix.protocol_records["live_cgroup_snapshot_1"] = snapshot_one_record
    birth_record = takeover.journal.append(
        domain=domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_OBSERVATION_V1_DOMAIN,
        id_field="actual_process_birth_observation_id",
        event="ACTUAL_SUPERVISOR_BIRTH_OBSERVED",
        payload={
            "schema": "acfqp.k7_h1_actual_process_birth_observation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "actual_process_birth_permit_consumption_id": prefix.consume_record.record_id,
            "shared_pid_cell_binding_id": pid_cell_record.record_id,
            "pidfd_escrow_receipt_id": escrow_record.record_id,
            "cgroup_membership_observation_id": snapshot_one_record.record_id,
            "child_pid": child_pid,
            "child_process_start_ticks": child_start_ticks,
            "native_parent_edge": {
                "clone_result": int(edge.clone_result),
                "status_bits": int(edge.status_bits),
                "first_cleanup_error": int(edge.first_cleanup_error),
                "reserved_zero": int(edge.reserved_zero),
                "native_return": prefix.native_return,
            },
            "child_is_inert_and_blocked_before_release": True,
            **_locked_claims(),
        },
    )
    prefix.protocol_records["birth_observation"] = birth_record

    _require_pidfd_child_live(escrowed_pidfd)
    if (
        _read_process_start_ticks(child_pid) != child_start_ticks
        or _pidfd_fact(escrowed_pidfd) != escrowed_fact
    ):
        _fail("B2-C child process start-tick identity changed")
    snapshot_two = _live_cgroup_snapshot(runtime, child_pid=child_pid, sequence=2)
    snapshot_two_record = takeover.journal.append(
        domain=domains_v15.CONSTRUCTION_K7_H1_CGROUP_MEMBERSHIP_OBSERVATION_V1_DOMAIN,
        id_field="cgroup_membership_observation_id",
        event="LIVE_CGROUP_SNAPSHOT_2",
        payload={
            **snapshot_two,
            "actual_process_birth_observation_id": birth_record.record_id,
            **_locked_claims(),
        },
    )
    prefix.protocol_records["live_cgroup_snapshot_2"] = snapshot_two_record
    ack_record = takeover.journal.append(
        domain=domains_v15.CONSTRUCTION_K7_H1_GUARDIAN_BIRTH_ACK_V1_DOMAIN,
        id_field="guardian_birth_ack_id",
        event="GUARDIAN_BIRTH_ACK_DURABLE",
        payload={
            "schema": "acfqp.k7_h1_guardian_birth_ack.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "actual_process_birth_observation_id": birth_record.record_id,
            "first_cgroup_membership_observation_id": snapshot_one_record.record_id,
            "second_cgroup_membership_observation_id": snapshot_two_record.record_id,
            "release_frame_sha256": hashlib.sha256(prefix.release_frame).hexdigest(),
            "release_frame_bytes": len(prefix.release_frame),
            "ack_file_and_directory_fsync_complete": True,
            "release_sent": False,
            **_locked_claims(),
        },
    )
    prefix.protocol_records["guardian_birth_ack"] = ack_record
    prefix.protocol_facts.update(
        {
            "cell_withdrawn": cell_fact,
            "child_gate_ready": ready_fact,
            "cell_pid": cell_pid,
            "child_start_ticks": child_start_ticks,
            "pidfd": escrowed_fact,
            "live_cgroup_snapshots": [snapshot_one, snapshot_two],
        }
    )
    takeover.journal.verify()
    prefix.state = "ACK_DURABLE_RELEASE_NOT_SENT"
    takeover.state = "ACK_DURABLE_RELEASE_NOT_SENT"


def _consume_permit_and_launch_native_prefix_v1(
    takeover: _H1SupervisorBirthTakeoverV1,
) -> _H1SupervisorNativeLaunchPrefixV1:
    """Irreversibly consume once, enter the prebound native image, and return."""

    original_mask = e5a_v1._block_fd_publication_signals()  # noqa: SLF001
    prefix: _H1SupervisorNativeLaunchPrefixV1 | None = None
    try:
        with _B2C_LOCK:
            with b2b_v1._B2B_LOCK:  # noqa: SLF001
                session = takeover.session
                runtime = session._runtime  # noqa: SLF001
                source = runtime._source_lease  # noqa: SLF001
                with b2a_v1._ADAPTER_LOCK:  # noqa: SLF001
                    with source._lock:  # noqa: SLF001
                        with runtime._lock:  # noqa: SLF001
                            with e5a_v1._FD_OWNERSHIP_LOCK:  # noqa: SLF001
                                prefix = _prepare_native_launch_prefix_under_locks(
                                    takeover
                                )
                                takeover.native_prefix = prefix
                                pid_cell_status = os.fstat(prefix.pid_cell_sealer_fd)
                                pid_cell_reader_status = os.fstat(
                                    prefix.pid_cell_reader_fd
                                )
                                zero_page = bytes(PID_CELL_BYTES)
                                if (
                                    os.pread(
                                        prefix.pid_cell_reader_fd,
                                        PID_CELL_BYTES + 1,
                                        0,
                                    )
                                    != zero_page
                                    or ctypes.string_at(
                                        prefix.guardian_pid_cell_read_mapping,
                                        PID_CELL_BYTES,
                                    )
                                    != zero_page
                                ):
                                    _fail("B2-C shared PID cell was not pristine zero")
                                canonical_grant_fd = b2b_v1._verify_managed_fd(  # noqa: SLF001
                                    session, "grant:SUPERVISOR:CONTROL"
                                )
                                creator_grant_fd = int(prefix.clone_args.cgroup)
                                consume_payload = {
                                    "schema": "acfqp.k7_h1_supervisor_birth_permit_consumption.v1",
                                    "schema_version": SCHEMA_VERSION,
                                    "profile_key": PROFILE_KEY,
                                    "supervisor_birth_companion_takeover_id": takeover.takeover_record.record_id,
                                    "guardian_session_genesis_id": session.session_id,
                                    "actual_process_birth_intent_id": session._intent.record_id,  # noqa: SLF001
                                    "actual_process_birth_permit_id": takeover.permit_record.record_id,
                                    "supervisor_birth_source_prebinding_id": takeover.prebinding.prebinding_id,
                                    "runtime_successor_id": runtime.successor_id,
                                    "permit_state_before": "TAKEN_OVER_UNCONSUMED",
                                    "permit_state_after": "CONSUME_COMMITTED",
                                    "target_role": "SUPERVISOR",
                                    "target_leaf": "CONTROL",
                                    "clone_flags": native_v1.REQUIRED_CLONE_FLAGS,
                                    "exit_signal": int(signal.SIGCHLD),
                                    "cgroup_grant_identity": list(
                                        e5a_v1._registry_fd_identity(  # noqa: SLF001
                                            canonical_grant_fd
                                        )
                                    ),
                                    "creator_grant_is_one_shot_same_ofd_duplicate": True,
                                    "guardian_canonical_grant_retained": True,
                                    "shared_pid_cell_identity": {
                                        "device": pid_cell_status.st_dev,
                                        "inode": pid_cell_status.st_ino,
                                        "size": pid_cell_status.st_size,
                                        "guardian_reader_device": pid_cell_reader_status.st_dev,
                                        "guardian_reader_inode": pid_cell_reader_status.st_ino,
                                        "guardian_reader_access": "O_RDONLY",
                                        "guardian_reader_independent_ofd": True,
                                        "guardian_read_mapping": "PROT_READ|MAP_SHARED",
                                        "entire_page_zero_before_commit": True,
                                    },
                                    "cell_withdrawn_frame_sha256": hashlib.sha256(
                                        bytes(prefix.cell_withdrawn_buffer)
                                    ).hexdigest(),
                                    "gate_ready_frame_sha256": hashlib.sha256(
                                        bytes(prefix.gate_ready_buffer)
                                    ).hexdigest(),
                                    "release_frame_sha256": hashlib.sha256(
                                        prefix.release_frame
                                    ).hexdigest(),
                                    "all_fallible_launch_setup_completed_before_commit": True,
                                    "durable_fsync_precedes_native_entry": True,
                                    "native_entry_is_prebound_direct_rx": True,
                                    **_locked_claims(),
                                }
                                # This append is the final fallible preparation.
                                # Once it returns, the permit can never be revoked as
                                # unconsumed, even if clone3 rejects the request.
                                consume_record = takeover.journal.append(
                                    domain=domains_v16.CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_PERMIT_CONSUMPTION_V1_DOMAIN,
                                    id_field="actual_process_birth_permit_consumption_id",
                                    event="SUPERVISOR_PERMIT_CONSUMED",
                                    payload=consume_payload,
                                )
                                _finish_consume_commit(
                                    takeover,
                                    prefix,
                                    consume_record,
                                )
                                try:
                                    prefix.native_return = int(
                                        takeover.prebinding._code_rx_function(
                                            prefix.launch_args_pointer
                                        )
                                    )
                                finally:
                                    try:
                                        _RAW_OS_CLOSE(prefix.child_gate_source_fd)
                                    except OSError as error:
                                        prefix.child_gate_source_close_errno = error.errno
                                    else:
                                        prefix.child_gate_source_close_errno = 0
                                    prefix.child_gate_source_fd = -1

                                edge = prefix.parent_edge
                                if edge.status_bits & native_v1.PARENT_EDGE_CREATOR_MAPPING_WITHDRAWN:
                                    prefix.creator_pid_cell_mapping = 0
                                if edge.status_bits & native_v1.PARENT_EDGE_CREATOR_FD_CLOSED:
                                    prefix.creator_pid_cell_fd = -1
                                if edge.status_bits & native_v1.PARENT_EDGE_CGROUP_GRANT_FD_CLOSED:
                                    try:
                                        _FCNTL_FCNTL(
                                            creator_grant_fd, fcntl.F_GETFD
                                        )
                                    except OSError as error:
                                        if error.errno != errno.EBADF:
                                            raise
                                    else:
                                        _fail(
                                            "B2-C native edge claimed an open creator cgroup grant closed"
                                        )
                                    prefix.creator_cgroup_grant_fd = -1
                                    b2b_v1._verify_managed_fd(  # noqa: SLF001
                                        session, "grant:SUPERVISOR:CONTROL"
                                    )
                                if edge.clone_result > 0:
                                    prefix.creator_pidfd_fd = int(prefix.pidfd_cell.value)
                                    takeover.child_pid = int(edge.clone_result)
                                    takeover.pidfd = prefix.creator_pidfd_fd
                                    prefix.state = "NATIVE_PARENT_RETURNED_CHILD_LIVE"
                                    takeover.state = "NATIVE_PARENT_RETURNED_CHILD_LIVE"
                                    _observe_child_and_persist_ack_under_locks(prefix)
                                else:
                                    prefix.state = "NATIVE_PARENT_RETURNED_CLONE_REJECTED"
                                    takeover.state = "NATIVE_PARENT_RETURNED_CLONE_REJECTED"
                                return prefix
    except BaseException:
        if prefix is not None and prefix.state == "PREPARED_UNCONSUMED":
            prefix.state = "SETUP_FAILED"
            _close_unconsumed_native_prefix(prefix)
            if takeover.native_prefix is prefix:
                takeover.native_prefix = None
        raise
    finally:
        e5a_v1._restore_fd_publication_signals(original_mask)  # noqa: SLF001


def _release_reap_and_observe_peak_under_locks(
    prefix: _H1SupervisorNativeLaunchPrefixV1,
) -> _BirthJournalRecordV1:
    takeover = prefix.takeover
    session = takeover.session
    runtime = session._runtime  # noqa: SLF001
    child_pid = takeover.child_pid
    pidfd = prefix.escrowed_pidfd_fd
    ack = prefix.protocol_records.get("guardian_birth_ack")
    if (
        takeover.native_prefix is not prefix
        or prefix.state != "ACK_DURABLE_RELEASE_NOT_SENT"
        or takeover.state != "ACK_DURABLE_RELEASE_NOT_SENT"
        or session._state != "COMPANION_CONSUME_COMMITTED"  # noqa: SLF001
        or type(ack) is not _BirthJournalRecordV1
        or pidfd < 0
        or takeover.pidfd != pidfd
        or _pidfd_fact(pidfd)["pid"] != child_pid
    ):
        _fail("B2-C release requires the exact durable-ACK live-child edge")
    takeover.journal.verify()
    _require_pidfd_child_live(pidfd)

    wrapper = socket.socket(fileno=prefix.parent_gate_fd)
    try:
        sent = wrapper.sendmsg(
            [prefix.release_frame],
            [],
            getattr(socket, "MSG_NOSIGNAL", 0),
        )
    finally:
        wrapper.detach()
    if sent != len(prefix.release_frame):
        _fail("B2-C guardian release frame was short")
    prefix.state = "RELEASE_SENT"
    takeover.state = "RELEASE_SENT"
    echo_fact, echo_rights = _recv_exact_seqpacket(
        prefix.parent_gate_fd,
        expected_frame=prefix.release_frame,
        expected_credentials=(child_pid, os.geteuid(), os.getegid()),
        expected_rights_count=0,
    )
    if echo_rights:
        _fail("B2-C child release echo unexpectedly installed rights")
    _RAW_OS_CLOSE(prefix.parent_gate_fd)
    prefix.parent_gate_fd = -1
    release_record = takeover.journal.append(
        domain=domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_CREATOR_RELEASE_V1_DOMAIN,
        id_field="actual_process_creator_release_id",
        event="SUPERVISOR_RELEASE_ECHO_OBSERVED",
        payload={
            "schema": "acfqp.k7_h1_actual_process_creator_release.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "guardian_birth_ack_id": ack.record_id,
            "actual_process_birth_observation_id": prefix.protocol_records[
                "birth_observation"
            ].record_id,
            "child_pid": child_pid,
            "release_frame_sha256": hashlib.sha256(prefix.release_frame).hexdigest(),
            "release_frame_bytes": len(prefix.release_frame),
            "release_was_sent_after_durable_ack": True,
            "child_exact_echo": echo_fact,
            **_locked_claims(),
        },
    )
    prefix.protocol_records["creator_release"] = release_record
    prefix.protocol_facts["release_echo"] = echo_fact

    poller = select.poll()
    poller.register(pidfd, select.POLLIN)
    events = poller.poll(int(REAP_TIMEOUT_SECONDS * 1000))
    if (
        len(events) != 1
        or events[0][0] != pidfd
        or events[0][1] & select.POLLIN == 0
        or events[0][1] & (select.POLLERR | select.POLLNVAL)
        or events[0][1] & ~(select.POLLIN | select.POLLHUP)
    ):
        _fail("B2-C child pidfd did not reach an exact readable death edge")
    if not callable(getattr(os, "waitid", None)):
        _fail("B2-C requires waitid")
    observed = os.waitid(P_PIDFD, pidfd, os.WEXITED | os.WNOWAIT)
    observed_fact = _require_clean_child_exit(observed, child_pid)
    death_record = takeover.journal.append(
        domain=domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_DEATH_OBSERVATION_V1_DOMAIN,
        id_field="actual_process_death_observation_id",
        event="SUPERVISOR_DEATH_OBSERVED_WNOWAIT",
        payload={
            "schema": "acfqp.k7_h1_actual_process_death_observation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "actual_process_creator_release_id": release_record.record_id,
            "pidfd_escrow_receipt_id": prefix.protocol_records[
                "pidfd_escrow"
            ].record_id,
            "child_pid": child_pid,
            "waitid_idtype": "P_PIDFD",
            "waitid_options": ["WEXITED", "WNOWAIT"],
            "wait_status": observed_fact,
            "creator_reap_not_yet_consumed": True,
            **_locked_claims(),
        },
    )
    prefix.protocol_records["death_observation"] = death_record

    consumed = os.waitid(P_PIDFD, pidfd, os.WEXITED)
    consumed_fact = _require_clean_child_exit(consumed, child_pid)
    if consumed_fact != observed_fact:
        _fail("B2-C consuming wait changed the WNOWAIT status")
    prefix.protocol_facts["creator_reap_consumed"] = {
        "observed_wnowait_status": observed_fact,
        "consuming_wait_status": consumed_fact,
    }
    try:
        os.waitid(P_PIDFD, pidfd, os.WEXITED | os.WNOHANG)
    except ChildProcessError:
        third_wait_errno = errno.ECHILD
    except OSError as error:
        if error.errno != errno.ECHILD:
            raise
        third_wait_errno = error.errno
    else:
        _fail("B2-C child remained waitable after the consuming reap")
    prefix.protocol_facts["creator_reap_completed"] = {
        "observed_wnowait_status": observed_fact,
        "consuming_wait_status": consumed_fact,
        "third_wait_errno": third_wait_errno,
    }
    reap_record = takeover.journal.append(
        domain=domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_CREATOR_REAP_ATTESTATION_V1_DOMAIN,
        id_field="actual_process_creator_reap_attestation_id",
        event="SUPERVISOR_CREATOR_REAP_COMPLETE",
        payload={
            "schema": "acfqp.k7_h1_actual_process_creator_reap_attestation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "actual_process_death_observation_id": death_record.record_id,
            "actual_process_birth_observation_id": prefix.protocol_records[
                "birth_observation"
            ].record_id,
            "child_pid": child_pid,
            "observed_wnowait_status": observed_fact,
            "consuming_wait_status": consumed_fact,
            "third_wait_errno": third_wait_errno,
            "creator_is_guardian_pid": os.getpid(),
            "creator_reap_exactly_once": True,
            **_locked_claims(),
        },
    )
    prefix.protocol_records["creator_reap"] = reap_record
    _RAW_OS_CLOSE(pidfd)
    prefix.escrowed_pidfd_fd = -1
    takeover.pidfd = -1

    empty_one = _wait_for_empty_cgroup_snapshot(runtime, sequence=1)
    empty_one_record = takeover.journal.append(
        domain=domains_v15.CONSTRUCTION_K7_H1_CGROUP_MEMBERSHIP_OBSERVATION_V1_DOMAIN,
        id_field="cgroup_membership_observation_id",
        event="EMPTY_CGROUP_SNAPSHOT_1",
        payload={
            **empty_one,
            "actual_process_creator_reap_attestation_id": reap_record.record_id,
            **_locked_claims(),
        },
    )
    empty_two = _wait_for_empty_cgroup_snapshot(runtime, sequence=2)
    empty_two_record = takeover.journal.append(
        domain=domains_v15.CONSTRUCTION_K7_H1_CGROUP_MEMBERSHIP_OBSERVATION_V1_DOMAIN,
        id_field="cgroup_membership_observation_id",
        event="EMPTY_CGROUP_SNAPSHOT_2",
        payload={
            **empty_two,
            "first_empty_cgroup_membership_observation_id": empty_one_record.record_id,
            **_locked_claims(),
        },
    )
    prefix.protocol_records["empty_cgroup_snapshot_1"] = empty_one_record
    prefix.protocol_records["empty_cgroup_snapshot_2"] = empty_two_record

    b2a_v1._verify_runtime_fd_registry_unlocked(runtime)  # noqa: SLF001
    primary = runtime._memory_peak_fd  # noqa: SLF001
    witness = runtime._memory_peak_witness_fd  # noqa: SLF001
    if not e5a_v1._same_open_file_description_for_close(primary, witness):  # noqa: SLF001
        _fail("B2-C retained memory.peak pair changed OFD")
    primary_status = os.fstat(primary)
    witness_status = os.fstat(witness)
    frozen_peak = runtime._hierarchy_document["outer_memory_peak"]  # noqa: SLF001
    if (
        (primary_status.st_dev, primary_status.st_ino)
        != (witness_status.st_dev, witness_status.st_ino)
        or {
            "device": primary_status.st_dev,
            "inode": primary_status.st_ino,
        }
        != {
            "device": frozen_peak["identity"]["device"],
            "inode": frozen_peak["identity"]["inode"],
        }
    ):
        _fail("B2-C retained memory.peak identity changed")
    prefix.protocol_facts["peak_read_started"] = True
    primary_raw = os.pread(primary, 65537, 0)
    prefix.protocol_facts["peak_read_returned"] = True
    prefix.protocol_facts["peak_primary_raw"] = primary_raw
    prefix.state = "PEAK_READ_RETURNED_UNPERSISTED"
    takeover.state = "PEAK_READ_RETURNED_UNPERSISTED"
    if (
        _TEST_ONLY_PEAK_FINISH_FAULT_STAGE == "AFTER_READ_RETURNED"
        and prefix.protocol_facts.get("peak_finish_fault_injected") is not True
    ):
        prefix.protocol_facts["peak_finish_fault_injected"] = True
        raise RuntimeError("injected B2-C peak finish fault after returned read")
    return _finish_peak_observation_from_returned_read_under_locks(prefix)


def _finish_peak_observation_from_returned_read_under_locks(
    prefix: _H1SupervisorNativeLaunchPrefixV1,
) -> _BirthJournalRecordV1:
    """Finish one already-returned primary peak read without reading again."""

    takeover = prefix.takeover
    session = takeover.session
    runtime = session._runtime  # noqa: SLF001
    if (
        takeover.native_prefix is not prefix
        or prefix.state != "PEAK_READ_RETURNED_UNPERSISTED"
        or takeover.state != "PEAK_READ_RETURNED_UNPERSISTED"
        or session._state != "COMPANION_CONSUME_COMMITTED"  # noqa: SLF001
        or prefix.protocol_facts.get("peak_read_started") is not True
        or prefix.protocol_facts.get("peak_read_returned") is not True
        or type(prefix.protocol_facts.get("peak_primary_raw")) is not bytes
    ):
        _fail("B2-C peak finish-forward state changed")
    _recover_durable_protocol_records(prefix)
    required = {
        "creator_reap",
        "empty_cgroup_snapshot_1",
        "empty_cgroup_snapshot_2",
    }
    if not required.issubset(prefix.protocol_records):
        _fail("B2-C peak finish-forward lost its post-reap records")

    primary_raw = prefix.protocol_facts["peak_primary_raw"]
    if len(primary_raw) > 65536:
        _fail("B2-C retained memory.peak read exceeded its exact cap")
    peak_bytes = _parse_single_nonnegative(primary_raw, "outer memory.peak")
    hierarchy = runtime._hierarchy_document  # noqa: SLF001
    frozen_peak = hierarchy["outer_memory_peak"]
    primary = runtime._memory_peak_fd  # noqa: SLF001
    witness = runtime._memory_peak_witness_fd  # noqa: SLF001
    b2a_v1._verify_runtime_fd_registry_unlocked(runtime)  # noqa: SLF001
    if not e5a_v1._same_open_file_description_for_close(primary, witness):  # noqa: SLF001
        _fail("B2-C retained memory.peak pair changed during finish-forward")
    primary_status = os.fstat(primary)
    witness_status = os.fstat(witness)
    if (
        (primary_status.st_dev, primary_status.st_ino)
        != (witness_status.st_dev, witness_status.st_ino)
        or {
            "device": primary_status.st_dev,
            "inode": primary_status.st_ino,
        }
        != {
            "device": frozen_peak["identity"]["device"],
            "inode": frozen_peak["identity"]["inode"],
        }
    ):
        _fail("B2-C retained memory.peak identity changed during finish-forward")
    allowed_cap = min(
        int(hierarchy["registered_hard_cap_bytes"]),
        int(hierarchy["outer"]["memory_max_bytes"]),
    )
    baseline = int(frozen_peak["baseline_peak_bytes"])
    empty_one_record = prefix.protocol_records["empty_cgroup_snapshot_1"]
    empty_two_record = prefix.protocol_records["empty_cgroup_snapshot_2"]
    reap_record = prefix.protocol_records["creator_reap"]
    empty_one = empty_one_record.to_document()
    empty_two = empty_two_record.to_document()
    if (
        peak_bytes < baseline
        or peak_bytes < empty_two["outer_memory_current_bytes"]
        or peak_bytes > allowed_cap
    ):
        _fail("B2-C actual memory.peak crossed its frozen envelope")
    peak_payload = {
        "schema": "acfqp.k7_h1_bounded_supervisor_birth_peak_observation.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "actual_process_creator_reap_attestation_id": reap_record.record_id,
        "first_empty_cgroup_membership_observation_id": empty_one_record.record_id,
        "second_empty_cgroup_membership_observation_id": empty_two_record.record_id,
        "runtime_successor_id": runtime.successor_id,
        "retained_memory_peak_identity": frozen_peak["identity"],
        "primary_and_witness_same_open_file_description": True,
        "primary_read_count": 1,
        "witness_read_count": 0,
        "raw_sha256": hashlib.sha256(primary_raw).hexdigest(),
        "memory_peak_bytes": peak_bytes,
        "final_outer_memory_current_bytes": empty_two[
            "outer_memory_current_bytes"
        ],
        "baseline_peak_bytes": baseline,
        "allowed_cap_bytes": allowed_cap,
        "observation_after_exact_reap_and_two_empty_snapshots": True,
        **_locked_claims(),
    }
    peak_record = prefix.protocol_records.get("peak_observation")
    if peak_record is None:
        peak_record = takeover.journal.append(
            domain=domains_v16.CONSTRUCTION_K7_H1_BOUNDED_SUPERVISOR_BIRTH_PEAK_OBSERVATION_V1_DOMAIN,
            id_field="bounded_supervisor_birth_peak_observation_id",
            event="BOUNDED_SUPERVISOR_BIRTH_PEAK_OBSERVED",
            payload=peak_payload,
        )
    else:
        peak_document = _verify_birth_record(
            peak_record,
            domain=domains_v16.CONSTRUCTION_K7_H1_BOUNDED_SUPERVISOR_BIRTH_PEAK_OBSERVATION_V1_DOMAIN,
            id_field="bounded_supervisor_birth_peak_observation_id",
        )
        expected = dict(peak_payload)
        expected["bounded_supervisor_birth_peak_observation_id"] = _domain_id(
            domains_v16.CONSTRUCTION_K7_H1_BOUNDED_SUPERVISOR_BIRTH_PEAK_OBSERVATION_V1_DOMAIN,
            peak_payload,
        )
        if peak_document != expected:
            _fail("B2-C durable peak record changed during finish-forward")
    prefix.protocol_records["peak_observation"] = peak_record
    if (
        _TEST_ONLY_PEAK_FINISH_FAULT_STAGE == "AFTER_PEAK_RECORD_DURABLE"
        and prefix.protocol_facts.get("peak_record_fault_injected") is not True
    ):
        prefix.protocol_facts["peak_record_fault_injected"] = True
        raise RuntimeError("injected B2-C peak finish fault after durable record")
    prefix.protocol_facts.update(
        {
            "death_waitid": reap_record.to_document()[
                "observed_wnowait_status"
            ],
            "empty_cgroup_snapshots": [empty_one, empty_two],
            "memory_peak_bytes": peak_bytes,
        }
    )
    takeover.journal.verify()
    runtime._state = "PEAK_READ"  # noqa: SLF001
    prefix.state = "PEAK_OBSERVED_POST_REAP"
    takeover.state = "PEAK_OBSERVED_POST_REAP"
    return peak_record


def _close_postrun_b2c_resources_under_locks(
    takeover: _H1SupervisorBirthTakeoverV1,
) -> None:
    """Close only B2-C-owned resources after the upstream hierarchy is closed."""

    prefix = takeover.native_prefix
    prebinding = takeover.prebinding
    if (
        prefix is None
        or prefix.takeover is not takeover
        or takeover.closure is None
        or takeover.session._state != "CLOSED"  # noqa: SLF001
    ):
        _fail("B2-C postrun resource close requires the closed upstream handback")
    takeover.state = "B2C_CLOSE_PENDING"
    prefix.state = "B2C_CLOSE_PENDING"
    prebinding._state = "B2C_CLOSE_PENDING"
    first_error: BaseException | None = None

    libc = native_v1._LIBC  # noqa: SLF001
    libc.munmap.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
    libc.munmap.restype = ctypes.c_int
    for owner, field_name, byte_count in (
        (prefix, "creator_pid_cell_mapping", PID_CELL_BYTES),
        (prefix, "guardian_pid_cell_read_mapping", PID_CELL_BYTES),
        (prebinding, "_code_rx_address", len(native_v1.X86_64_TEXT_BYTES)),
    ):
        address = int(getattr(owner, field_name))
        if address <= 0:
            continue
        if libc.munmap(ctypes.c_void_p(address), byte_count) != 0:
            if first_error is None:
                code = ctypes.get_errno()
                first_error = OSError(code, os.strerror(code))
            continue
        setattr(owner, field_name, 0)

    for label in sorted(tuple(prebinding._source_fds)):
        canonical, witness = prebinding._source_fds[label]
        updated = [canonical, witness]
        for index in (1, 0):
            descriptor = updated[index]
            if descriptor < 0:
                continue
            try:
                _RAW_OS_CLOSE(descriptor)
            except OSError as error:
                if first_error is None:
                    first_error = error
            else:
                updated[index] = -1
        if updated == [-1, -1]:
            prebinding._source_fds.pop(label)
        else:
            prebinding._source_fds[label] = (updated[0], updated[1])

    for owner, field_name in (
        (prefix, "parent_gate_fd"),
        (prefix, "child_gate_source_fd"),
        (prefix, "creator_pid_cell_fd"),
        (prefix, "creator_cgroup_grant_fd"),
        (prefix, "escrow_receiver_fd"),
        (prefix, "escrow_sender_fd"),
        (prefix, "creator_pidfd_fd"),
        (prefix, "escrowed_pidfd_fd"),
        (prefix, "pid_cell_reader_fd"),
        (prefix, "pid_cell_witness_fd"),
        (prefix, "pid_cell_sealer_fd"),
        (prebinding, "_code_witness_fd"),
        (prebinding, "_code_fd"),
        (prebinding, "_manifest_witness_fd"),
        (prebinding, "_manifest_fd"),
    ):
        descriptor = int(getattr(owner, field_name))
        if descriptor < 0:
            continue
        try:
            _RAW_OS_CLOSE(descriptor)
        except OSError as error:
            try:
                _FCNTL_FCNTL(descriptor, fcntl.F_GETFD)
            except OSError as probe:
                if probe.errno == errno.EBADF:
                    setattr(owner, field_name, -1)
                elif first_error is None:
                    first_error = error
            else:
                if first_error is None:
                    first_error = error
        else:
            setattr(owner, field_name, -1)

    leaked_prefix_fields = {
        field_name: int(getattr(prefix, field_name))
        for field_name in (
            "parent_gate_fd",
            "child_gate_source_fd",
            "creator_pid_cell_fd",
            "creator_cgroup_grant_fd",
            "escrow_receiver_fd",
            "escrow_sender_fd",
            "creator_pidfd_fd",
            "escrowed_pidfd_fd",
            "pid_cell_reader_fd",
            "pid_cell_witness_fd",
            "pid_cell_sealer_fd",
        )
        if int(getattr(prefix, field_name)) >= 0
    }
    if (
        first_error is not None
        or leaked_prefix_fields
        or prebinding._source_fds
        or prebinding._code_rx_address != 0
        or prefix.guardian_pid_cell_read_mapping != 0
        or any(
            descriptor >= 0
            for descriptor in (
                prebinding._code_witness_fd,
                prebinding._code_fd,
                prebinding._manifest_witness_fd,
                prebinding._manifest_fd,
            )
        )
    ):
        _QUARANTINED_TAKEOVERS[id(takeover.session)] = takeover
        _LIVE_TAKEOVERS.pop(id(takeover.session), None)
        raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
            "B2-C postrun close retained retryable resources",
            cleanup_document={"live_prefix_fields": leaked_prefix_fields},
            cleanup_handle=takeover,
        ) from first_error
    prebinding._code_rx_function = None
    prebinding._state = "CLOSED_CONSUMED"
    prefix.state = "B2C_RESOURCES_CLOSED_JOURNAL_OPEN"
    takeover.state = "B2C_RESOURCES_CLOSED_JOURNAL_OPEN"
    _CONSUMED_PREBINDINGS.pop(id(takeover.session._runtime), None)  # noqa: SLF001
    _LIVE_TAKEOVERS.pop(id(takeover.session), None)
    _QUARANTINED_TAKEOVERS[id(takeover.session)] = takeover


def _close_birth_journal_and_finish_v1(
    takeover: _H1SupervisorBirthTakeoverV1,
) -> None:
    prefix = takeover.native_prefix
    if (
        prefix is None
        or takeover.state != "B2C_RESOURCES_CLOSED_JOURNAL_OPEN"
        or prefix.state != "B2C_RESOURCES_CLOSED_JOURNAL_OPEN"
        or _QUARANTINED_TAKEOVERS.get(id(takeover.session)) is not takeover
    ):
        _fail("B2-C journal finish requires closed process resources")
    if takeover.journal._state == "OPEN":  # noqa: SLF001
        takeover.journal.verify()
    try:
        takeover.journal.close()
    except BaseException as error:
        raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
            "B2-C journal close retained retryable descriptors",
            cleanup_handle=takeover,
        ) from error
    prefix.state = "CLOSED"
    takeover.state = "CLOSED"
    _QUARANTINED_TAKEOVERS.pop(id(takeover.session), None)


def _close_taken_over_prebinding_under_locks(
    takeover: _H1SupervisorBirthTakeoverV1,
) -> None:
    prebinding = takeover.prebinding
    runtime = takeover.session._runtime  # noqa: SLF001
    if (
        takeover.session._state != "CLOSED"  # noqa: SLF001
        or takeover.consume_record is not None
        or takeover.native_prefix is not None
        or prebinding._state
        not in {"TAKEN_OVER_UNCONSUMED", "UNCONSUMED_CLOSE_PENDING"}
        or _CONSUMED_PREBINDINGS.get(id(runtime)) is not prebinding
    ):
        _fail("B2-C unconsumed close state changed")
    prebinding._state = "UNCONSUMED_CLOSE_PENDING"
    takeover.state = "UNCONSUMED_CLOSE_PENDING"
    first: BaseException | None = None
    if prebinding._code_rx_address > 0:
        libc = native_v1._LIBC  # noqa: SLF001
        libc.munmap.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
        libc.munmap.restype = ctypes.c_int
        if libc.munmap(
            ctypes.c_void_p(prebinding._code_rx_address),
            len(native_v1.X86_64_TEXT_BYTES),
        ) != 0:
            code = ctypes.get_errno()
            first = OSError(code, os.strerror(code))
        else:
            prebinding._code_rx_address = 0
    for label in sorted(tuple(prebinding._source_fds)):
        descriptors = list(prebinding._source_fds[label])
        for index in (1, 0):
            descriptor = descriptors[index]
            if descriptor < 0:
                continue
            try:
                _RAW_OS_CLOSE(descriptor)
            except OSError as error:
                try:
                    _FCNTL_FCNTL(descriptor, fcntl.F_GETFD)
                except OSError as probe:
                    if probe.errno == errno.EBADF:
                        descriptors[index] = -1
                    elif first is None:
                        first = error
                else:
                    if first is None:
                        first = error
            else:
                descriptors[index] = -1
        if descriptors == [-1, -1]:
            prebinding._source_fds.pop(label)
        else:
            prebinding._source_fds[label] = (descriptors[0], descriptors[1])
    for field_name in (
        "_code_witness_fd",
        "_code_fd",
        "_manifest_witness_fd",
        "_manifest_fd",
    ):
        descriptor = int(getattr(prebinding, field_name))
        if descriptor < 0:
            continue
        try:
            _RAW_OS_CLOSE(descriptor)
        except OSError as error:
            try:
                _FCNTL_FCNTL(descriptor, fcntl.F_GETFD)
            except OSError as probe:
                if probe.errno == errno.EBADF:
                    setattr(prebinding, field_name, -1)
                elif first is None:
                    first = error
            else:
                if first is None:
                    first = error
        else:
            setattr(prebinding, field_name, -1)
    if (
        first is not None
        or prebinding._code_rx_address != 0
        or prebinding._source_fds
        or any(
            int(getattr(prebinding, field_name)) >= 0
            for field_name in (
                "_code_witness_fd",
                "_code_fd",
                "_manifest_witness_fd",
                "_manifest_fd",
            )
        )
    ):
        _QUARANTINED_TAKEOVERS[id(takeover.session)] = takeover
        _LIVE_TAKEOVERS.pop(id(takeover.session), None)
        raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
            "B2-C unconsumed prebinding close retained resources",
            cleanup_handle=takeover,
        ) from first
    prebinding._code_rx_function = None
    prebinding._state = "CLOSED_UNUSED_AFTER_TAKEOVER"
    takeover.state = "UNCONSUMED_B2C_RESOURCES_CLOSED_JOURNAL_OPEN"
    _CONSUMED_PREBINDINGS.pop(id(runtime), None)
    _LIVE_TAKEOVERS.pop(id(takeover.session), None)
    _QUARANTINED_TAKEOVERS[id(takeover.session)] = takeover


def _close_unconsumed_takeover_v1(
    takeover: _H1SupervisorBirthTakeoverV1,
) -> NoReturn:
    if takeover.consume_record is not None or takeover.native_prefix is not None:
        _fail("B2-C unconsumed cleanup crossed durable consumption")
    if takeover.state == "CLOSED_UNCONSUMED_CANCELLED":
        cleanup_document = {
            "schema": "acfqp.k7_h1_unconsumed_supervisor_birth_cleanup.v1",
            "schema_version": SCHEMA_VERSION,
            "supervisor_birth_companion_takeover_id": (
                takeover.takeover_record.record_id
            ),
            "h1_route_wide_runtime_lease_closure_id": takeover.closure.closure_id,
            "permit_consumed": False,
            "actual_process_birth_present": False,
            "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "terminal_code": "PROTOCOL_FAILURE",
            **_locked_claims(),
        }
        raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
            "B2-C unconsumed lifecycle already closed",
            cleanup_document=cleanup_document,
            cleanup_handle=None,
        )
    closure = b2b_v1.close_h1_guardian_runtime_companion_unconsumed_v1(
        takeover.session
    )
    takeover.closure = closure
    runtime = takeover.session._runtime  # noqa: SLF001
    source = runtime._source_lease  # noqa: SLF001
    if takeover.state != "UNCONSUMED_B2C_RESOURCES_CLOSED_JOURNAL_OPEN":
        with _B2C_LOCK:
            with b2b_v1._B2B_LOCK:  # noqa: SLF001
                with b2a_v1._ADAPTER_LOCK:  # noqa: SLF001
                    with source._lock:  # noqa: SLF001
                        with runtime._lock:  # noqa: SLF001
                            with e5a_v1._FD_OWNERSHIP_LOCK:  # noqa: SLF001
                                _close_taken_over_prebinding_under_locks(takeover)
    if takeover.journal._state == "OPEN":  # noqa: SLF001
        takeover.journal.verify()
    try:
        takeover.journal.close()
    except BaseException as error:
        raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
            "B2-C unconsumed journal close retained resources",
            cleanup_handle=takeover,
        ) from error
    takeover.state = "CLOSED_UNCONSUMED_CANCELLED"
    _QUARANTINED_TAKEOVERS.pop(id(takeover.session), None)
    cleanup_document = {
        "schema": "acfqp.k7_h1_unconsumed_supervisor_birth_cleanup.v1",
        "schema_version": SCHEMA_VERSION,
        "supervisor_birth_companion_takeover_id": takeover.takeover_record.record_id,
        "h1_route_wide_runtime_lease_closure_id": closure.closure_id,
        "permit_consumed": False,
        "actual_process_birth_present": False,
        "all_process_and_cgroup_resources_closed": True,
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": "PROTOCOL_FAILURE",
        **_locked_claims(),
    }
    raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
        "B2-C closed an unconsumed SUPERVISOR setup failure",
        cleanup_document=cleanup_document,
        cleanup_handle=None,
    )


def _close_postrun_b2c_resources_v1(
    takeover: _H1SupervisorBirthTakeoverV1,
) -> None:
    """Apply the full inherited lock order around the B2-C-only close."""

    session = takeover.session
    runtime = session._runtime  # noqa: SLF001
    source = runtime._source_lease  # noqa: SLF001
    original_mask = e5a_v1._block_fd_publication_signals()  # noqa: SLF001
    try:
        with _B2C_LOCK:
            with b2b_v1._B2B_LOCK:  # noqa: SLF001
                with b2a_v1._ADAPTER_LOCK:  # noqa: SLF001
                    with source._lock:  # noqa: SLF001
                        with runtime._lock:  # noqa: SLF001
                            with e5a_v1._FD_OWNERSHIP_LOCK:  # noqa: SLF001
                                _close_postrun_b2c_resources_under_locks(takeover)
    finally:
        e5a_v1._restore_fd_publication_signals(original_mask)  # noqa: SLF001


def _validate_exact_clone_rejection(
    prefix: _H1SupervisorNativeLaunchPrefixV1,
) -> dict[str, int]:
    """Accept only the frozen no-child native rejection edge."""

    edge = prefix.parent_edge
    fact = {
        "clone_result": int(edge.clone_result),
        "status_bits": int(edge.status_bits),
        "first_cleanup_error": int(edge.first_cleanup_error),
        "reserved_zero": int(edge.reserved_zero),
        "native_return": int(prefix.native_return)
        if type(prefix.native_return) is int
        else 0,
        "child_gate_source_close_errno": int(prefix.child_gate_source_close_errno)
        if type(prefix.child_gate_source_close_errno) is int
        else -1,
        "rejected_pidfd_cell_value": int(prefix.pidfd_cell.value),
    }
    rejected_pidfd_cell_is_closed = False
    if fact["rejected_pidfd_cell_value"] >= 0:
        try:
            _FCNTL_FCNTL(fact["rejected_pidfd_cell_value"], fcntl.F_GETFD)
        except OSError as error:
            rejected_pidfd_cell_is_closed = error.errno == errno.EBADF
    else:
        rejected_pidfd_cell_is_closed = True
    fact["rejected_pidfd_cell_is_closed"] = int(rejected_pidfd_cell_is_closed)
    if (
        prefix.state != "NATIVE_PARENT_RETURNED_CLONE_REJECTED"
        or prefix.takeover.state != "NATIVE_PARENT_RETURNED_CLONE_REJECTED"
        or prefix.consume_record is None
        or prefix.takeover.consume_record is not prefix.consume_record
        or not -4095 <= fact["clone_result"] <= -1
        or fact["native_return"] != fact["clone_result"]
        or fact["status_bits"] != native_v1.PARENT_EDGE_REQUIRED_REJECTION_BITS
        or fact["first_cleanup_error"] != 0
        or fact["reserved_zero"] != 0
        or fact["child_gate_source_close_errno"] != 0
        or not rejected_pidfd_cell_is_closed
        or prefix.creator_pidfd_fd != -1
        or prefix.escrowed_pidfd_fd != -1
        or prefix.creator_pid_cell_fd != -1
        or prefix.creator_pid_cell_mapping != 0
        or prefix.creator_cgroup_grant_fd != -1
        or prefix.takeover.child_pid != -1
        or prefix.takeover.pidfd != -1
    ):
        _fail("B2-C native rejection was not the exact no-child withdrawal edge")
    return fact


def _persist_clone_rejection_failure_closure(
    takeover: _H1SupervisorBirthTakeoverV1,
    *,
    native_edge: Mapping[str, int],
) -> _BirthJournalRecordV1:
    prefix = takeover.native_prefix
    if prefix is None or takeover.consume_record is None:
        _fail("B2-C clone-rejection closure lacks its consumed launch edge")
    return takeover.journal.append(
        domain=(
            domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN
        ),
        id_field="actual_observed_e3_v2_protocol_failure_closure_id",
        event="SUPERVISOR_CLONE_REJECTED_PROTOCOL_FAILURE_CLOSURE",
        payload={
            "schema": "acfqp.k7_h1_actual_observed_e3_v2_protocol_failure_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "supervisor_birth_companion_takeover_id": takeover.takeover_record.record_id,
            "actual_process_birth_permit_consumption_id": (
                takeover.consume_record.record_id
            ),
            "guardian_session_genesis_id": takeover.session.session_id,
            "runtime_successor_id": takeover.session._runtime.successor_id,  # noqa: SLF001
            "native_parent_edge": dict(native_edge),
            "failure_reason": "CLONE3_REJECTED_AFTER_DURABLE_PERMIT_CONSUMPTION",
            "permit_was_consumed": True,
            "clone_syscall_performed": True,
            "actual_process_birth_present": False,
            "pidfd_issued": False,
            "process_death_or_reap_present": False,
            "peak_read_present": False,
            "unconsumed_revoke_forbidden": True,
            "terminal_scope": "ROUTE_ATTEMPT",
            "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "terminal_code": "PROTOCOL_FAILURE",
            **_locked_claims(),
        },
    )


def _close_exact_clone_rejection_v1(
    takeover: _H1SupervisorBirthTakeoverV1,
    prefix: _H1SupervisorNativeLaunchPrefixV1,
) -> NoReturn:
    """Truthfully close a consumed permit for which clone3 made no child."""

    native_edge = _validate_exact_clone_rejection(prefix)
    failure_record = _persist_clone_rejection_failure_closure(
        takeover,
        native_edge=native_edge,
    )
    takeover.protocol_failure_record = failure_record
    takeover.journal.verify()
    closure = b2b_v1.close_h1_guardian_runtime_after_rejected_consumption_v1(
        takeover.session,
        permit_consumption_record=takeover.consume_record,
        rejection_attestation=failure_record,
    )
    barrier = takeover.session._consumed_barrier  # noqa: SLF001
    if (
        type(barrier) is not b2b_v1.H1GuardianRuntimeRecordV1
        or takeover.session._state != "CLOSED"  # noqa: SLF001
        or takeover.session._runtime._state != "CLOSED"  # noqa: SLF001
    ):
        _fail("B2-C clone-rejection handback did not close exactly")
    barrier_document = barrier.to_document()
    closure_document = closure.to_document()
    if (
        barrier_document.get("cleanup_outcome") != "CLONE_REJECTED_NO_BIRTH"
        or barrier_document.get("actual_process_birth_present") is not False
        or barrier_document.get("actual_peak_issued") is not False
        or closure_document.get("actual_process_birth_present") is not False
        or closure_document.get("actual_peak_issued") is not False
    ):
        _fail("B2-C clone-rejection cleanup semantics changed")
    takeover.consumed_barrier = barrier
    takeover.closure = closure
    _close_postrun_b2c_resources_v1(takeover)
    cleanup_document = _clone_rejection_cleanup_document(takeover)
    _close_birth_journal_and_finish_v1(takeover)
    raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
        "B2-C clone3 rejected the consumed SUPERVISOR birth attempt",
        cleanup_document=cleanup_document,
        cleanup_handle=None,
    )


def _clone_rejection_cleanup_document(
    takeover: _H1SupervisorBirthTakeoverV1,
) -> dict[str, Any]:
    failure_record = takeover.protocol_failure_record
    barrier = takeover.consumed_barrier
    closure = takeover.closure
    if (
        type(failure_record) is not _BirthJournalRecordV1
        or type(barrier) is not b2b_v1.H1GuardianRuntimeRecordV1
        or type(closure) is not b2a_v1.H1E5ARuntimeLeaseClosureV1
    ):
        _fail("B2-C clone-rejection cleanup artifacts are incomplete")
    return {
        "schema": "acfqp.k7_h1_bounded_supervisor_birth_clone_rejection_cleanup.v1",
        "schema_version": SCHEMA_VERSION,
        "actual_observed_e3_v2_protocol_failure_closure_id": (
            failure_record.record_id
        ),
        "guardian_runtime_consumed_cleanup_barrier_id": barrier.record_id,
        "h1_route_wide_runtime_lease_closure_id": closure.closure_id,
        "terminal_scope": "ROUTE_ATTEMPT",
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": "PROTOCOL_FAILURE",
        "all_process_and_cgroup_resources_closed": True,
        **_locked_claims(),
    }


def _release_reap_peak_v1(
    takeover: _H1SupervisorBirthTakeoverV1,
    prefix: _H1SupervisorNativeLaunchPrefixV1,
) -> _BirthJournalRecordV1:
    """Run the release/reap/peak edge under the complete inherited lock order."""

    session = takeover.session
    runtime = session._runtime  # noqa: SLF001
    source = runtime._source_lease  # noqa: SLF001
    original_mask = e5a_v1._block_fd_publication_signals()  # noqa: SLF001
    try:
        with _B2C_LOCK:
            with b2b_v1._B2B_LOCK:  # noqa: SLF001
                with b2a_v1._ADAPTER_LOCK:  # noqa: SLF001
                    with source._lock:  # noqa: SLF001
                        with runtime._lock:  # noqa: SLF001
                            with e5a_v1._FD_OWNERSHIP_LOCK:  # noqa: SLF001
                                return _release_reap_and_observe_peak_under_locks(
                                    prefix
                                )
    finally:
        e5a_v1._restore_fd_publication_signals(original_mask)  # noqa: SLF001


def _finish_peak_observation_from_returned_read_v1(
    takeover: _H1SupervisorBirthTakeoverV1,
    prefix: _H1SupervisorNativeLaunchPrefixV1,
) -> _BirthJournalRecordV1:
    """Resume only the post-read peak transaction under the inherited locks."""

    session = takeover.session
    runtime = session._runtime  # noqa: SLF001
    source = runtime._source_lease  # noqa: SLF001
    original_mask = e5a_v1._block_fd_publication_signals()  # noqa: SLF001
    try:
        with _B2C_LOCK:
            with b2b_v1._B2B_LOCK:  # noqa: SLF001
                with b2a_v1._ADAPTER_LOCK:  # noqa: SLF001
                    with source._lock:  # noqa: SLF001
                        with runtime._lock:  # noqa: SLF001
                            with e5a_v1._FD_OWNERSHIP_LOCK:  # noqa: SLF001
                                return _finish_peak_observation_from_returned_read_under_locks(
                                    prefix
                                )
    finally:
        e5a_v1._restore_fd_publication_signals(original_mask)  # noqa: SLF001


def _recover_durable_protocol_records(
    prefix: _H1SupervisorNativeLaunchPrefixV1,
) -> None:
    """Reattach records whose append completed before a raised boundary."""

    journal = prefix.takeover.journal
    if journal._pending is not None:  # noqa: SLF001
        journal._resume_pending()  # noqa: SLF001
    event_to_key = {
        "SHARED_PID_CELL_BOUND": "pid_cell_binding",
        "CREATOR_PIDFD_SELF_ESCROWED": "pidfd_escrow",
        "LIVE_CGROUP_SNAPSHOT_1": "live_cgroup_snapshot_1",
        "ACTUAL_SUPERVISOR_BIRTH_OBSERVED": "birth_observation",
        "LIVE_CGROUP_SNAPSHOT_2": "live_cgroup_snapshot_2",
        "GUARDIAN_BIRTH_ACK_DURABLE": "guardian_birth_ack",
        "SUPERVISOR_RELEASE_ECHO_OBSERVED": "creator_release",
        "SUPERVISOR_DEATH_OBSERVED_WNOWAIT": "death_observation",
        "SUPERVISOR_CREATOR_REAP_COMPLETE": "creator_reap",
        "EMPTY_CGROUP_SNAPSHOT_1": "empty_cgroup_snapshot_1",
        "EMPTY_CGROUP_SNAPSHOT_2": "empty_cgroup_snapshot_2",
        "BOUNDED_SUPERVISOR_BIRTH_PEAK_OBSERVED": "peak_observation",
    }
    for record in journal._records:  # noqa: SLF001
        for event, key in event_to_key.items():
            if f"_{event}_" in record.filename:
                retained = prefix.protocol_records.get(key)
                if retained is not None and retained is not record:
                    _fail("B2-C durable protocol record identity forked")
                prefix.protocol_records[key] = record
                break
    journal.verify()


def _terminated_wait_fact(info: Any, child_pid: int) -> dict[str, int]:
    fact = _waitid_fact(info)
    allowed_codes = {
        int(getattr(os, "CLD_EXITED", 1)),
        int(getattr(os, "CLD_KILLED", 2)),
        int(getattr(os, "CLD_DUMPED", 3)),
    }
    if (
        fact["si_pid"] != child_pid
        or fact["si_signo"] != int(signal.SIGCHLD)
        or fact["si_code"] not in allowed_codes
        or fact["si_status"] < 0
    ):
        _fail("B2-C failure cleanup observed a different child wait status")
    return fact


def _failure_pidfd(
    prefix: _H1SupervisorNativeLaunchPrefixV1,
    child_pid: int,
) -> int:
    candidates = (
        prefix.escrowed_pidfd_fd,
        prefix.creator_pidfd_fd,
        prefix.takeover.pidfd,
    )
    seen: set[int] = set()
    for descriptor in candidates:
        if descriptor < 0 or descriptor in seen:
            continue
        seen.add(descriptor)
        try:
            fact = _pidfd_fact(descriptor)
        except (OSError, ConstructionK7H1ActualObservedSupervisorBirthV1Error):
            continue
        if fact["pid"] == child_pid and fact["cloexec"]:
            return descriptor
    return -1


def _kill_reap_empty_failure_under_locks(
    takeover: _H1SupervisorBirthTakeoverV1,
    prefix: _H1SupervisorNativeLaunchPrefixV1,
    *,
    primary_failure_stage: str,
) -> _BirthJournalRecordV1:
    """Turn a post-birth Python failure into one truthful no-peak closure."""

    session = takeover.session
    runtime = session._runtime  # noqa: SLF001
    edge = prefix.parent_edge
    child_pid = int(edge.clone_result)
    if (
        child_pid <= 0
        or takeover.child_pid != child_pid
        or int(edge.status_bits) != native_v1.PARENT_EDGE_REQUIRED_SUCCESS_BITS
        or int(edge.first_cleanup_error) != 0
        or int(edge.reserved_zero) != 0
        or prefix.native_return != child_pid
        or prefix.protocol_facts.get("peak_read_started") is True
        or "peak_observation" in prefix.protocol_records
    ):
        _fail("B2-C failure cleanup is outside the no-peak born-child profile")
    _recover_durable_protocol_records(prefix)

    kill_fd = b2b_v1._verify_managed_fd(session, "cgroup:kill")  # noqa: SLF001
    if not takeover.cgroup_kill_written:
        written = _RAW_OS_WRITE(kill_fd, b"1")
        if written != 1:
            _fail("B2-C cgroup.kill failure cleanup write was short")
        takeover.cgroup_kill_written = True
    prefix.state = "FAILURE_KILL_DURABLE_EFFECT"
    takeover.state = "FAILURE_KILL_DURABLE_EFFECT"

    reap_record = prefix.protocol_records.get("creator_reap")
    reap_fact = prefix.protocol_facts.get("creator_reap_completed")
    if reap_record is not None:
        reap_document = reap_record.to_document()
        reap_fact = {
            "observed_wnowait_status": reap_document["observed_wnowait_status"],
            "consuming_wait_status": reap_document["consuming_wait_status"],
            "third_wait_errno": reap_document["third_wait_errno"],
        }
    consumed_reap = prefix.protocol_facts.get("creator_reap_consumed")
    if reap_fact is None and consumed_reap is not None:
        if (
            type(consumed_reap) is not dict
            or consumed_reap.get("observed_wnowait_status")
            != consumed_reap.get("consuming_wait_status")
        ):
            _fail("B2-C failure cleanup retained an invalid consumed reap")
        pidfd = _failure_pidfd(prefix, child_pid)
        if pidfd < 0:
            _fail("B2-C failure cleanup lost the consumed child's pidfd")
        try:
            os.waitid(P_PIDFD, pidfd, os.WEXITED | os.WNOHANG)
        except ChildProcessError:
            third_wait_errno = errno.ECHILD
        except OSError as error:
            if error.errno != errno.ECHILD:
                raise
            third_wait_errno = error.errno
        else:
            _fail("B2-C consumed child unexpectedly became waitable again")
        reap_fact = {
            **consumed_reap,
            "third_wait_errno": third_wait_errno,
        }
        prefix.protocol_facts["creator_reap_completed"] = reap_fact
    if reap_fact is None:
        pidfd = _failure_pidfd(prefix, child_pid)
        if pidfd < 0:
            _fail("B2-C failure cleanup lost the child pidfd before reap")
        try:
            signal.pidfd_send_signal(pidfd, signal.SIGKILL)
        except ProcessLookupError:
            pass
        poller = select.poll()
        poller.register(pidfd, select.POLLIN)
        events = poller.poll(int(REAP_TIMEOUT_SECONDS * 1000))
        if (
            len(events) != 1
            or events[0][0] != pidfd
            or events[0][1] & select.POLLIN == 0
            or events[0][1] & (select.POLLERR | select.POLLNVAL)
        ):
            _fail("B2-C failure-cleanup pidfd did not become waitable")
        observed = os.waitid(P_PIDFD, pidfd, os.WEXITED | os.WNOWAIT)
        observed_fact = _terminated_wait_fact(observed, child_pid)
        consumed = os.waitid(P_PIDFD, pidfd, os.WEXITED)
        consumed_fact = _terminated_wait_fact(consumed, child_pid)
        if consumed_fact != observed_fact:
            _fail("B2-C failure cleanup consuming wait changed status")
        try:
            os.waitid(P_PIDFD, pidfd, os.WEXITED | os.WNOHANG)
        except ChildProcessError:
            third_wait_errno = errno.ECHILD
        except OSError as error:
            if error.errno != errno.ECHILD:
                raise
            third_wait_errno = error.errno
        else:
            _fail("B2-C failure-cleanup child remained waitable")
        reap_fact = {
            "observed_wnowait_status": observed_fact,
            "consuming_wait_status": consumed_fact,
            "third_wait_errno": third_wait_errno,
        }
        prefix.protocol_facts["creator_reap_completed"] = reap_fact
    if (
        type(reap_fact) is not dict
        or reap_fact.get("observed_wnowait_status")
        != reap_fact.get("consuming_wait_status")
        or reap_fact.get("third_wait_errno") != errno.ECHILD
    ):
        _fail("B2-C failure cleanup lacks exact one-time reap evidence")

    empty_one = _wait_for_empty_cgroup_snapshot(runtime, sequence=1)
    empty_two = _wait_for_empty_cgroup_snapshot(runtime, sequence=2)
    failure_record = takeover.journal.append(
        domain=(
            domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN
        ),
        id_field="actual_observed_e3_v2_protocol_failure_closure_id",
        event="POST_CONSUMPTION_BIRTH_PROTOCOL_FAILURE_CLOSURE",
        payload={
            "schema": "acfqp.k7_h1_actual_observed_e3_v2_protocol_failure_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "supervisor_birth_companion_takeover_id": takeover.takeover_record.record_id,
            "actual_process_birth_permit_consumption_id": takeover.consume_record.record_id,
            "guardian_session_genesis_id": session.session_id,
            "runtime_successor_id": runtime.successor_id,
            "failure_reason": "POST_CONSUMPTION_BIRTH_PROTOCOL_FAILURE",
            "primary_failure_stage": primary_failure_stage,
            "permit_was_consumed": True,
            "clone_syscall_performed": True,
            "actual_process_birth_present": True,
            "child_pid": child_pid,
            "cgroup_kill_written": True,
            "process_death_or_reap_present": True,
            "creator_reap_completed": True,
            "creator_is_guardian_pid": os.getpid(),
            "creator_reap_exactly_once": True,
            "creator_reap_wait_status": reap_fact["consuming_wait_status"],
            "third_wait_errno": reap_fact["third_wait_errno"],
            "empty_cgroup_snapshots": [empty_one, empty_two],
            "peak_read_started": False,
            "peak_read_present": False,
            "primary_peak_read_count": 0,
            "witness_peak_read_count": 0,
            "actual_peak_issued": False,
            "unconsumed_revoke_forbidden": True,
            "terminal_scope": "ROUTE_ATTEMPT",
            "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "terminal_code": "PROTOCOL_FAILURE",
            **_locked_claims(),
        },
    )
    takeover.protocol_failure_record = failure_record
    takeover.state = "BIRTH_FAILURE_REAP_EMPTY_DURABLE"
    prefix.state = "BIRTH_FAILURE_REAP_EMPTY_DURABLE"
    takeover.journal.verify()
    return failure_record


def _kill_reap_empty_failure_v1(
    takeover: _H1SupervisorBirthTakeoverV1,
    prefix: _H1SupervisorNativeLaunchPrefixV1,
    *,
    primary_failure_stage: str,
) -> _BirthJournalRecordV1:
    session = takeover.session
    runtime = session._runtime  # noqa: SLF001
    source = runtime._source_lease  # noqa: SLF001
    with _B2C_LOCK:
        with b2b_v1._B2B_LOCK:  # noqa: SLF001
            with b2a_v1._ADAPTER_LOCK:  # noqa: SLF001
                with source._lock:  # noqa: SLF001
                    with runtime._lock:  # noqa: SLF001
                        with e5a_v1._FD_OWNERSHIP_LOCK:  # noqa: SLF001
                            return _kill_reap_empty_failure_under_locks(
                                takeover,
                                prefix,
                                primary_failure_stage=primary_failure_stage,
                            )


_RESULT_PROTOCOL_RECORD_ORDER = (
    "pid_cell_binding",
    "pidfd_escrow",
    "live_cgroup_snapshot_1",
    "birth_observation",
    "live_cgroup_snapshot_2",
    "guardian_birth_ack",
    "creator_release",
    "death_observation",
    "creator_reap",
    "empty_cgroup_snapshot_1",
    "empty_cgroup_snapshot_2",
    "peak_observation",
)


def _build_bounded_birth_result(
    takeover: _H1SupervisorBirthTakeoverV1,
    prefix: _H1SupervisorNativeLaunchPrefixV1,
) -> H1ActualObservedSupervisorBirthResultV1:
    if (
        takeover.state != "CLOSED"
        or prefix.state != "CLOSED"
        or takeover.consumed_barrier is None
        or takeover.closure is None
        or takeover.journal._state != "CLOSED"  # noqa: SLF001
    ):
        _fail("B2-C bounded result requires one exactly closed lifecycle")
    records = prefix.protocol_records
    if tuple(records) != _RESULT_PROTOCOL_RECORD_ORDER:
        _fail("B2-C bounded result protocol record order changed")
    closure_document = takeover.closure.to_document()
    barrier_document = takeover.consumed_barrier.to_document()
    peak_document = records["peak_observation"].to_document()
    session = takeover.session
    runtime = session._runtime  # noqa: SLF001
    source_closure = runtime._source_lease._closure  # noqa: SLF001
    if (
        source_closure is None
        or session._genesis is None  # noqa: SLF001
        or session._source_closure is None  # noqa: SLF001
        or session._intent is None  # noqa: SLF001
        or session._permit_record is None  # noqa: SLF001
    ):
        _fail("B2-C bounded result lost an upstream artifact")
    artifact_documents = {
        "hierarchy": runtime._hierarchy_document,  # noqa: SLF001
        "runtime_successor": runtime.to_document(),
        "source_prebinding": takeover.prebinding.to_document(),
        "guardian_preregistration": session._preregistration.to_document(),  # noqa: SLF001
        "guardian_source_closure": session._source_closure.to_document(),  # noqa: SLF001
        "guardian_genesis": session._genesis.to_document(),  # noqa: SLF001
        "birth_intent": session._intent.to_document(),  # noqa: SLF001
        "birth_permit": session._permit_record.to_document(),  # noqa: SLF001
        "companion_takeover": takeover.takeover_record.to_document(),
        "permit_consumption": takeover.consume_record.to_document(),
        "protocol_records": {
            name: records[name].to_document()
            for name in _RESULT_PROTOCOL_RECORD_ORDER
        },
        "consumed_cleanup_barrier": barrier_document,
        "source_cgroup_closure": source_closure.to_document(),
        "runtime_closure": closure_document,
    }
    payload = {
        "schema": "acfqp.k7_h1_bounded_supervisor_birth_slice_result.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "readiness": READINESS,
        "supervisor_birth_companion_takeover_id": takeover.takeover_record.record_id,
        "actual_process_birth_permit_consumption_id": takeover.consume_record.record_id,
        "protocol_record_ids": {
            name: records[name].record_id for name in _RESULT_PROTOCOL_RECORD_ORDER
        },
        "guardian_runtime_consumed_cleanup_barrier_id": (
            takeover.consumed_barrier.record_id
        ),
        "h1_route_wide_runtime_lease_closure_id": takeover.closure.closure_id,
        "source_e5a_cleanup_closure_id": closure_document[
            "source_e5a_cleanup_closure_id"
        ],
        "guardian_session_genesis_id": takeover.session.session_id,
        "runtime_successor_id": takeover.session._runtime.successor_id,  # noqa: SLF001
        "child_pid": takeover.child_pid,
        "bounded_actual_peak_bytes": peak_document["memory_peak_bytes"],
        "actual_process_birth_present": True,
        "creator_reap_exactly_once": True,
        "memory_peak_primary_read_count": 1,
        "memory_peak_witness_read_count": 0,
        "birth_journal_closed": True,
        "all_b2c_owned_resources_closed": True,
        "all_upstream_cgroups_and_descriptors_closed": True,
        "consumed_cleanup_outcome": barrier_document["cleanup_outcome"],
        "actual_peak_issued": True,
        "artifact_documents": artifact_documents,
        **_locked_claims(),
    }
    result_id = _domain_id(
        domains_v16.CONSTRUCTION_K7_H1_BOUNDED_SUPERVISOR_BIRTH_SLICE_RESULT_V1_DOMAIN,
        payload,
    )
    document = dict(payload)
    document["bounded_supervisor_birth_slice_result_id"] = result_id
    return H1ActualObservedSupervisorBirthResultV1(
        ids_v1.canonical_json_bytes(document),
        _issuer=_RESULT_ISSUER,
    )


def _finish_positive_postrun_v1(
    takeover: _H1SupervisorBirthTakeoverV1,
    prefix: _H1SupervisorNativeLaunchPrefixV1,
) -> H1ActualObservedSupervisorBirthResultV1:
    peak_record = prefix.protocol_records.get("peak_observation")
    if (
        type(peak_record) is not _BirthJournalRecordV1
        or takeover.state != "PEAK_OBSERVED_POST_REAP"
        or prefix.state != "PEAK_OBSERVED_POST_REAP"
    ):
        _fail("B2-C positive handback lacks the exact peak edge")
    closure = b2b_v1.close_h1_guardian_runtime_postrun_v1(
        takeover.session,
        permit_consumption_record=takeover.consume_record,
        birth_observation=prefix.protocol_records["birth_observation"],
        creator_reap_attestation=prefix.protocol_records["creator_reap"],
        bounded_peak_observation=peak_record,
    )
    barrier = takeover.session._consumed_barrier  # noqa: SLF001
    if type(barrier) is not b2b_v1.H1GuardianRuntimeRecordV1:
        _fail("B2-C postrun handback lost its consumed cleanup barrier")
    barrier_document = barrier.to_document()
    closure_document = closure.to_document()
    if (
        barrier_document.get("cleanup_outcome") != "BIRTH_REAP_PEAK_COMPLETE"
        or barrier_document.get("actual_process_birth_present") is not True
        or barrier_document.get("actual_peak_issued") is not True
        or barrier_document.get("bounded_supervisor_birth_peak_observation_id")
        != peak_record.record_id
        or closure_document.get("actual_process_birth_present") is not True
        or closure_document.get("actual_peak_issued") is not True
        or closure_document.get("bounded_supervisor_birth_peak_observation_id")
        != peak_record.record_id
    ):
        _fail("B2-C postrun upstream closure semantics changed")
    takeover.consumed_barrier = barrier
    takeover.closure = closure
    _close_postrun_b2c_resources_v1(takeover)
    _close_birth_journal_and_finish_v1(takeover)
    return _build_bounded_birth_result(takeover, prefix)


def _birth_failure_cleanup_document(
    takeover: _H1SupervisorBirthTakeoverV1,
) -> dict[str, Any]:
    failure_record = takeover.protocol_failure_record
    barrier = takeover.consumed_barrier
    closure = takeover.closure
    if (
        type(failure_record) is not _BirthJournalRecordV1
        or type(barrier) is not b2b_v1.H1GuardianRuntimeRecordV1
        or type(closure) is not b2a_v1.H1E5ARuntimeLeaseClosureV1
    ):
        _fail("B2-C failed-birth cleanup artifacts are incomplete")
    return {
        "schema": "acfqp.k7_h1_bounded_supervisor_birth_failure_cleanup.v1",
        "schema_version": SCHEMA_VERSION,
        "actual_observed_e3_v2_protocol_failure_closure_id": (
            failure_record.record_id
        ),
        "guardian_runtime_consumed_cleanup_barrier_id": barrier.record_id,
        "h1_route_wide_runtime_lease_closure_id": closure.closure_id,
        "child_pid": takeover.child_pid,
        "terminal_scope": "ROUTE_ATTEMPT",
        "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
        "terminal_code": "PROTOCOL_FAILURE",
        "all_process_and_cgroup_resources_closed": True,
        **_locked_claims(),
    }


def _finish_birth_failure_postrun_v1(
    takeover: _H1SupervisorBirthTakeoverV1,
    prefix: _H1SupervisorNativeLaunchPrefixV1,
) -> NoReturn:
    failure_record = takeover.protocol_failure_record
    if (
        type(failure_record) is not _BirthJournalRecordV1
        or takeover.state != "BIRTH_FAILURE_REAP_EMPTY_DURABLE"
        or prefix.state != "BIRTH_FAILURE_REAP_EMPTY_DURABLE"
    ):
        _fail("B2-C failed-birth handback lacks its durable cleanup record")
    closure = b2b_v1.close_h1_guardian_runtime_after_failed_birth_v1(
        takeover.session,
        permit_consumption_record=takeover.consume_record,
        failure_attestation=failure_record,
    )
    barrier = takeover.session._consumed_barrier  # noqa: SLF001
    if type(barrier) is not b2b_v1.H1GuardianRuntimeRecordV1:
        _fail("B2-C failed-birth handback lost its consumed barrier")
    barrier_document = barrier.to_document()
    closure_document = closure.to_document()
    if (
        barrier_document.get("cleanup_outcome")
        != "BIRTH_FAILURE_KILL_REAP_NO_PEAK"
        or barrier_document.get("actual_process_birth_present") is not True
        or barrier_document.get("process_death_or_reap_present") is not True
        or barrier_document.get("actual_peak_issued") is not False
        or closure_document.get("actual_process_birth_present") is not True
        or closure_document.get("process_death_or_reap_present") is not True
        or closure_document.get("actual_peak_issued") is not False
    ):
        _fail("B2-C failed-birth upstream closure semantics changed")
    takeover.consumed_barrier = barrier
    takeover.closure = closure
    _close_postrun_b2c_resources_v1(takeover)
    cleanup_document = _birth_failure_cleanup_document(takeover)
    _close_birth_journal_and_finish_v1(takeover)
    raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
        "B2-C closed a post-consumption SUPERVISOR birth protocol failure",
        cleanup_document=cleanup_document,
        cleanup_handle=None,
    )


def _verify_embedded_content_document(
    document: Any,
    *,
    domain: str,
    id_field: str,
    label: str,
) -> str:
    if type(document) is not dict:
        _fail(f"B2-C embedded {label} is not one object")
    payload = dict(document)
    supplied = payload.pop(id_field, None)
    if type(supplied) is not str or _domain_id(domain, payload) != supplied:
        _fail(f"B2-C embedded {label} content ID changed")
    return supplied


def _verify_bounded_result_artifact_graph(document: Mapping[str, Any]) -> None:
    artifacts = document.get("artifact_documents")
    if type(artifacts) is not dict or set(artifacts) != {
        "hierarchy",
        "runtime_successor",
        "source_prebinding",
        "guardian_preregistration",
        "guardian_source_closure",
        "guardian_genesis",
        "birth_intent",
        "birth_permit",
        "companion_takeover",
        "permit_consumption",
        "protocol_records",
        "consumed_cleanup_barrier",
        "source_cgroup_closure",
        "runtime_closure",
    }:
        _fail("B2-C bounded result artifact inventory changed")
    hierarchy = artifacts["hierarchy"]
    successor = artifacts["runtime_successor"]
    prebinding = artifacts["source_prebinding"]
    preregistration = artifacts["guardian_preregistration"]
    guardian_source = artifacts["guardian_source_closure"]
    genesis = artifacts["guardian_genesis"]
    intent = artifacts["birth_intent"]
    permit = artifacts["birth_permit"]
    takeover = artifacts["companion_takeover"]
    consumption = artifacts["permit_consumption"]
    protocol = artifacts["protocol_records"]
    barrier = artifacts["consumed_cleanup_barrier"]
    source_closure = artifacts["source_cgroup_closure"]
    runtime_closure = artifacts["runtime_closure"]
    if type(protocol) is not dict or set(protocol) != set(
        _RESULT_PROTOCOL_RECORD_ORDER
    ):
        _fail("B2-C bounded result protocol artifact inventory changed")

    hierarchy_id = _verify_embedded_content_document(
        hierarchy,
        domain=domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_HIERARCHY_V1_DOMAIN,
        id_field="h1_route_wide_cgroup_hierarchy_id",
        label="hierarchy",
    )
    successor_id = _verify_embedded_content_document(
        successor,
        domain=domains_v15.CONSTRUCTION_K7_H1_ROUTE_WIDE_RUNTIME_LEASE_SUCCESSOR_V1_DOMAIN,
        id_field="h1_e5a_runtime_lease_successor_id",
        label="runtime successor",
    )
    prebinding_id = _verify_embedded_content_document(
        prebinding,
        domain=domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN,
        id_field="supervisor_birth_source_prebinding_id",
        label="source prebinding",
    )
    preregistration_id = _verify_embedded_content_document(
        preregistration,
        domain=domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_STAGE_PLAN_V1_DOMAIN,
        id_field="guardian_runtime_genesis_preregistration_id",
        label="guardian preregistration",
    )
    guardian_source_id = _verify_embedded_content_document(
        guardian_source,
        domain=domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN,
        id_field="execution_source_closure_id",
        label="guardian source closure",
    )
    genesis_id = _verify_embedded_content_document(
        genesis,
        domain=domains_v15.CONSTRUCTION_K7_H1_ACTUAL_OBSERVED_E3_V2_GUARDIAN_SESSION_GENESIS_V1_DOMAIN,
        id_field="guardian_session_genesis_id",
        label="guardian genesis",
    )
    intent_id = _verify_embedded_content_document(
        intent,
        domain=domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_INTENT_V1_DOMAIN,
        id_field="actual_process_birth_intent_id",
        label="birth intent",
    )
    permit_id = _verify_embedded_content_document(
        permit,
        domain=domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_PERMIT_V1_DOMAIN,
        id_field="actual_process_birth_permit_id",
        label="birth permit",
    )
    takeover_id = _verify_embedded_content_document(
        takeover,
        domain=domains_v16.CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_COMPANION_TAKEOVER_V1_DOMAIN,
        id_field="supervisor_birth_companion_takeover_id",
        label="companion takeover",
    )
    consumption_id = _verify_embedded_content_document(
        consumption,
        domain=domains_v16.CONSTRUCTION_K7_H1_SUPERVISOR_BIRTH_PERMIT_CONSUMPTION_V1_DOMAIN,
        id_field="actual_process_birth_permit_consumption_id",
        label="permit consumption",
    )
    barrier_id = _verify_embedded_content_document(
        barrier,
        domain=(
            domains_v17.CONSTRUCTION_K7_H1_GUARDIAN_RUNTIME_CONSUMED_CLEANUP_BARRIER_V1_DOMAIN
        ),
        id_field="guardian_runtime_consumed_cleanup_barrier_id",
        label="consumed cleanup barrier",
    )
    source_closure_id = _verify_embedded_content_document(
        source_closure,
        domain=domains_v12.CONSTRUCTION_K7_H1_ROUTE_WIDE_CGROUP_CLEANUP_CLOSURE_V1_DOMAIN,
        id_field="h1_route_wide_cgroup_cleanup_closure_id",
        label="source cgroup closure",
    )
    runtime_closure_id = _verify_embedded_content_document(
        runtime_closure,
        domain=domains_v15.CONSTRUCTION_K7_H1_ROUTE_WIDE_RUNTIME_LEASE_CLOSURE_V1_DOMAIN,
        id_field="h1_route_wide_runtime_lease_closure_id",
        label="runtime closure",
    )
    protocol_specs = {
        "pid_cell_binding": (
            domains_v15.CONSTRUCTION_K7_H1_SHARED_PID_CELL_BINDING_V1_DOMAIN,
            "shared_pid_cell_binding_id",
        ),
        "pidfd_escrow": (
            domains_v15.CONSTRUCTION_K7_H1_PIDFD_ESCROW_RECEIPT_V2_DOMAIN,
            "pidfd_escrow_receipt_id",
        ),
        "live_cgroup_snapshot_1": (
            domains_v15.CONSTRUCTION_K7_H1_CGROUP_MEMBERSHIP_OBSERVATION_V1_DOMAIN,
            "cgroup_membership_observation_id",
        ),
        "birth_observation": (
            domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_BIRTH_OBSERVATION_V1_DOMAIN,
            "actual_process_birth_observation_id",
        ),
        "live_cgroup_snapshot_2": (
            domains_v15.CONSTRUCTION_K7_H1_CGROUP_MEMBERSHIP_OBSERVATION_V1_DOMAIN,
            "cgroup_membership_observation_id",
        ),
        "guardian_birth_ack": (
            domains_v15.CONSTRUCTION_K7_H1_GUARDIAN_BIRTH_ACK_V1_DOMAIN,
            "guardian_birth_ack_id",
        ),
        "creator_release": (
            domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_CREATOR_RELEASE_V1_DOMAIN,
            "actual_process_creator_release_id",
        ),
        "death_observation": (
            domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_DEATH_OBSERVATION_V1_DOMAIN,
            "actual_process_death_observation_id",
        ),
        "creator_reap": (
            domains_v15.CONSTRUCTION_K7_H1_ACTUAL_PROCESS_CREATOR_REAP_ATTESTATION_V1_DOMAIN,
            "actual_process_creator_reap_attestation_id",
        ),
        "empty_cgroup_snapshot_1": (
            domains_v15.CONSTRUCTION_K7_H1_CGROUP_MEMBERSHIP_OBSERVATION_V1_DOMAIN,
            "cgroup_membership_observation_id",
        ),
        "empty_cgroup_snapshot_2": (
            domains_v15.CONSTRUCTION_K7_H1_CGROUP_MEMBERSHIP_OBSERVATION_V1_DOMAIN,
            "cgroup_membership_observation_id",
        ),
        "peak_observation": (
            domains_v16.CONSTRUCTION_K7_H1_BOUNDED_SUPERVISOR_BIRTH_PEAK_OBSERVATION_V1_DOMAIN,
            "bounded_supervisor_birth_peak_observation_id",
        ),
    }
    protocol_ids = {
        name: _verify_embedded_content_document(
            protocol[name],
            domain=protocol_specs[name][0],
            id_field=protocol_specs[name][1],
            label=name,
        )
        for name in _RESULT_PROTOCOL_RECORD_ORDER
    }
    child_pid = protocol["birth_observation"].get("child_pid")
    occurrence_fields = (
        "logical_occurrence_id",
        "route_attempt_id",
        "decision_point_id",
        "BuildEpoch_id",
    )
    if (
        successor.get("h1_route_wide_cgroup_hierarchy_id") != hierarchy_id
        or prebinding.get("runtime_successor_id") != successor_id
        or guardian_source.get("preregistration_id") != preregistration_id
        or genesis.get("h1_e5a_runtime_lease_successor_id") != successor_id
        or genesis.get("preregistration_id") != preregistration_id
        or genesis.get("execution_source_closure_id") != guardian_source_id
        or intent.get("execution_source_closure_id") != guardian_source_id
        or intent.get("guardian_session_genesis_id") != genesis_id
        or permit.get("guardian_session_genesis_id") != genesis_id
        or permit.get("execution_source_closure_id") != guardian_source_id
        or permit.get("actual_process_birth_intent_id") != intent_id
        or takeover.get("supervisor_birth_source_prebinding_id") != prebinding_id
        or takeover.get("guardian_session_genesis_id") != genesis_id
        or takeover.get("actual_process_birth_intent_id") != intent_id
        or takeover.get("actual_process_birth_permit_id") != permit_id
        or takeover.get("runtime_successor_id") != successor_id
        or consumption.get("supervisor_birth_companion_takeover_id") != takeover_id
        or consumption.get("guardian_session_genesis_id") != genesis_id
        or consumption.get("actual_process_birth_intent_id") != intent_id
        or consumption.get("actual_process_birth_permit_id") != permit_id
        or consumption.get("supervisor_birth_source_prebinding_id") != prebinding_id
        or consumption.get("runtime_successor_id") != successor_id
        or protocol["pid_cell_binding"].get(
            "actual_process_birth_permit_consumption_id"
        )
        != consumption_id
        or protocol["pidfd_escrow"].get("shared_pid_cell_binding_id")
        != protocol_ids["pid_cell_binding"]
        or protocol["pidfd_escrow"].get(
            "actual_process_birth_permit_consumption_id"
        )
        != consumption_id
        or protocol["live_cgroup_snapshot_1"].get("pidfd_escrow_receipt_id")
        != protocol_ids["pidfd_escrow"]
        or protocol["birth_observation"].get(
            "actual_process_birth_permit_consumption_id"
        )
        != consumption_id
        or protocol["birth_observation"].get("shared_pid_cell_binding_id")
        != protocol_ids["pid_cell_binding"]
        or protocol["birth_observation"].get("pidfd_escrow_receipt_id")
        != protocol_ids["pidfd_escrow"]
        or protocol["birth_observation"].get("cgroup_membership_observation_id")
        != protocol_ids["live_cgroup_snapshot_1"]
        or protocol["live_cgroup_snapshot_2"].get(
            "actual_process_birth_observation_id"
        )
        != protocol_ids["birth_observation"]
        or protocol["guardian_birth_ack"].get(
            "actual_process_birth_observation_id"
        )
        != protocol_ids["birth_observation"]
        or protocol["guardian_birth_ack"].get(
            "first_cgroup_membership_observation_id"
        )
        != protocol_ids["live_cgroup_snapshot_1"]
        or protocol["guardian_birth_ack"].get(
            "second_cgroup_membership_observation_id"
        )
        != protocol_ids["live_cgroup_snapshot_2"]
        or protocol["creator_release"].get("guardian_birth_ack_id")
        != protocol_ids["guardian_birth_ack"]
        or protocol["creator_release"].get(
            "actual_process_birth_observation_id"
        )
        != protocol_ids["birth_observation"]
        or protocol["death_observation"].get(
            "actual_process_creator_release_id"
        )
        != protocol_ids["creator_release"]
        or protocol["death_observation"].get("pidfd_escrow_receipt_id")
        != protocol_ids["pidfd_escrow"]
        or protocol["creator_reap"].get(
            "actual_process_death_observation_id"
        )
        != protocol_ids["death_observation"]
        or protocol["creator_reap"].get("actual_process_birth_observation_id")
        != protocol_ids["birth_observation"]
        or protocol["empty_cgroup_snapshot_1"].get(
            "actual_process_creator_reap_attestation_id"
        )
        != protocol_ids["creator_reap"]
        or protocol["empty_cgroup_snapshot_2"].get(
            "first_empty_cgroup_membership_observation_id"
        )
        != protocol_ids["empty_cgroup_snapshot_1"]
        or protocol["peak_observation"].get(
            "actual_process_creator_reap_attestation_id"
        )
        != protocol_ids["creator_reap"]
        or protocol["peak_observation"].get(
            "first_empty_cgroup_membership_observation_id"
        )
        != protocol_ids["empty_cgroup_snapshot_1"]
        or protocol["peak_observation"].get(
            "second_empty_cgroup_membership_observation_id"
        )
        != protocol_ids["empty_cgroup_snapshot_2"]
        or protocol["peak_observation"].get("runtime_successor_id") != successor_id
        or any(protocol[name].get("child_pid") != child_pid for name in (
            "pid_cell_binding",
            "pidfd_escrow",
            "live_cgroup_snapshot_1",
            "birth_observation",
            "live_cgroup_snapshot_2",
            "death_observation",
            "creator_reap",
        ))
        or barrier.get("actual_process_birth_permit_consumption_id")
        != consumption_id
        or barrier.get("actual_process_birth_observation_id")
        != protocol_ids["birth_observation"]
        or barrier.get("actual_process_creator_reap_attestation_id")
        != protocol_ids["creator_reap"]
        or barrier.get("bounded_supervisor_birth_peak_observation_id")
        != protocol_ids["peak_observation"]
        or barrier.get("runtime_successor_id") != successor_id
        or runtime_closure.get("h1_e5a_runtime_lease_successor_id") != successor_id
        or runtime_closure.get("h1_route_wide_cgroup_hierarchy_id") != hierarchy_id
        or runtime_closure.get("source_e5a_cleanup_closure_id") != source_closure_id
        or runtime_closure.get("actual_process_birth_observation_id")
        != protocol_ids["birth_observation"]
        or runtime_closure.get("actual_process_creator_reap_attestation_id")
        != protocol_ids["creator_reap"]
        or runtime_closure.get("bounded_supervisor_birth_peak_observation_id")
        != protocol_ids["peak_observation"]
        or source_closure.get("h1_route_wide_cgroup_hierarchy_id") != hierarchy_id
        or source_closure.get("actual_process_birth_observation_id")
        != protocol_ids["birth_observation"]
        or source_closure.get("actual_process_creator_reap_attestation_id")
        != protocol_ids["creator_reap"]
        or source_closure.get("bounded_supervisor_birth_peak_observation_id")
        != protocol_ids["peak_observation"]
        or any(
            successor.get(field) != hierarchy.get(field)
            or runtime_closure.get(field) != hierarchy.get(field)
            or source_closure.get(field) != hierarchy.get(field)
            for field in occurrence_fields
        )
        or document.get("supervisor_birth_companion_takeover_id") != takeover_id
        or document.get("actual_process_birth_permit_consumption_id")
        != consumption_id
        or document.get("guardian_runtime_consumed_cleanup_barrier_id")
        != barrier_id
        or document.get("h1_route_wide_runtime_lease_closure_id")
        != runtime_closure_id
        or document.get("source_e5a_cleanup_closure_id") != source_closure_id
        or document.get("guardian_session_genesis_id") != genesis_id
        or document.get("runtime_successor_id") != successor_id
        or document.get("child_pid") != child_pid
        or document.get("bounded_actual_peak_bytes")
        != protocol["peak_observation"].get("memory_peak_bytes")
        or document.get("protocol_record_ids") != protocol_ids
    ):
        _fail("B2-C bounded result artifact dependency graph changed")


def verify_h1_actual_observed_supervisor_birth_result_v1(
    result: H1ActualObservedSupervisorBirthResultV1,
) -> dict[str, Any]:
    """Replay the portable bounded result without consulting live resources."""

    if type(result) is not H1ActualObservedSupervisorBirthResultV1:
        _fail("B2-C bounded result type changed")
    document = result.to_document()
    protocol = document.get("protocol_record_ids")
    if (
        document.get("schema")
        != "acfqp.k7_h1_bounded_supervisor_birth_slice_result.v1"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("profile_key") != PROFILE_KEY
        or document.get("readiness") != READINESS
        or type(protocol) is not dict
        or len(protocol) != len(_RESULT_PROTOCOL_RECORD_ORDER)
        or set(protocol) != set(_RESULT_PROTOCOL_RECORD_ORDER)
        or document.get("actual_process_birth_present") is not True
        or document.get("creator_reap_exactly_once") is not True
        or document.get("memory_peak_primary_read_count") != 1
        or document.get("memory_peak_witness_read_count") != 0
        or document.get("birth_journal_closed") is not True
        or document.get("all_b2c_owned_resources_closed") is not True
        or document.get("all_upstream_cgroups_and_descriptors_closed") is not True
        or document.get("consumed_cleanup_outcome")
        != "BIRTH_REAP_PEAK_COMPLETE"
        or document.get("actual_peak_issued") is not True
        or type(document.get("child_pid")) is not int
        or document["child_pid"] <= 0
        or type(document.get("bounded_actual_peak_bytes")) is not int
        or document["bounded_actual_peak_bytes"] < 0
        or any(document.get(key) != value for key, value in _locked_claims().items())
    ):
        _fail("B2-C bounded result semantics changed")
    _verify_bounded_result_artifact_graph(document)
    return document


def verify_h1_actual_observed_supervisor_birth_result_bytes_v1(
    raw: bytes,
) -> dict[str, Any]:
    """Independent portable replay from canonical bytes only."""

    if type(raw) is not bytes:
        _fail("B2-C bounded result bytes type changed")
    try:
        document = ids_v1.loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
            "B2-C bounded result is not canonical JSON"
        ) from error
    if type(document) is not dict or ids_v1.canonical_json_bytes(document) != raw:
        _fail("B2-C bounded result is not one canonical object")
    replay = H1ActualObservedSupervisorBirthResultV1(
        raw,
        _issuer=_RESULT_ISSUER,
    )
    return verify_h1_actual_observed_supervisor_birth_result_v1(replay)


def complete_h1_actual_observed_supervisor_birth_v1(
    takeover: _H1SupervisorBirthTakeoverV1,
) -> H1ActualObservedSupervisorBirthResultV1:
    """Consume once and close either the exact success or rejection lifecycle."""

    prefix: _H1SupervisorNativeLaunchPrefixV1 | None = None
    _validate_live_code_closure()
    original_mask = e5a_v1._block_fd_publication_signals()  # noqa: SLF001
    try:
        if takeover.state == "CLOSED":
            prefix = takeover.native_prefix
            if prefix is None:
                _fail("B2-C closed lifecycle lost its native prefix")
            if takeover.protocol_failure_record is not None:
                failure = takeover.protocol_failure_record.to_document()
                cleanup_document = (
                    _clone_rejection_cleanup_document(takeover)
                    if failure.get("failure_reason")
                    == "CLONE3_REJECTED_AFTER_DURABLE_PERMIT_CONSUMPTION"
                    else _birth_failure_cleanup_document(takeover)
                )
                raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
                    "B2-C lifecycle already closed as a noncertificate",
                    cleanup_document=cleanup_document,
                    cleanup_handle=None,
                )
            result = _build_bounded_birth_result(takeover, prefix)
            verify_h1_actual_observed_supervisor_birth_result_v1(result)
            return result
        if takeover.state == "B2C_RESOURCES_CLOSED_JOURNAL_OPEN":
            prefix = takeover.native_prefix
            if prefix is None:
                _fail("B2-C journal retry lost its native prefix")
            _close_birth_journal_and_finish_v1(takeover)
            return complete_h1_actual_observed_supervisor_birth_v1(takeover)
        if takeover.state == "B2C_CLOSE_PENDING":
            prefix = takeover.native_prefix
            if prefix is None:
                _fail("B2-C close retry lost its native prefix")
            _close_postrun_b2c_resources_v1(takeover)
            _close_birth_journal_and_finish_v1(takeover)
            return complete_h1_actual_observed_supervisor_birth_v1(takeover)
        if takeover.state == "BIRTH_FAILURE_REAP_EMPTY_DURABLE":
            prefix = takeover.native_prefix
            if prefix is None:
                _fail("B2-C failure retry lost its native prefix")
            _finish_birth_failure_postrun_v1(takeover, prefix)
        if takeover.state == "PEAK_READ_RETURNED_UNPERSISTED":
            prefix = takeover.native_prefix
            if prefix is None:
                _fail("B2-C peak retry lost its native prefix")
            _finish_peak_observation_from_returned_read_v1(takeover, prefix)
        if takeover.state == "PEAK_OBSERVED_POST_REAP":
            prefix = takeover.native_prefix
            if prefix is None:
                _fail("B2-C positive retry lost its native prefix")
            result = _finish_positive_postrun_v1(takeover, prefix)
            verify_h1_actual_observed_supervisor_birth_result_v1(result)
            return result
        prefix = _consume_permit_and_launch_native_prefix_v1(takeover)
        if prefix.state == "NATIVE_PARENT_RETURNED_CLONE_REJECTED":
            _close_exact_clone_rejection_v1(takeover, prefix)
        if prefix.state != "ACK_DURABLE_RELEASE_NOT_SENT":
            _fail("B2-C native launch did not reach one registered parent edge")
        _release_reap_peak_v1(takeover, prefix)
        result = _finish_positive_postrun_v1(takeover, prefix)
        verify_h1_actual_observed_supervisor_birth_result_v1(result)
        return result
    except BaseException as error:
        if takeover.state in {"CLOSED", "CLOSED_UNCONSUMED_CANCELLED"}:
            raise
        if takeover.consume_record is None and takeover.native_prefix is None:
            try:
                _close_unconsumed_takeover_v1(takeover)
            except ConstructionK7H1ActualObservedSupervisorBirthV1Error as cleanup:
                if cleanup.cleanup_handle is None:
                    raise cleanup from error
        prefix = takeover.native_prefix if prefix is None else prefix
        if (
            prefix is not None
            and int(prefix.parent_edge.clone_result) > 0
            and prefix.protocol_facts.get("peak_read_started") is not True
            and takeover.protocol_failure_record is None
        ):
            primary_stage = takeover.state
            try:
                _kill_reap_empty_failure_v1(
                    takeover,
                    prefix,
                    primary_failure_stage=primary_stage,
                )
                _finish_birth_failure_postrun_v1(takeover, prefix)
            except ConstructionK7H1ActualObservedSupervisorBirthV1Error as cleanup:
                if cleanup.cleanup_handle is None and takeover.state == "CLOSED":
                    raise cleanup from error
        _QUARANTINED_TAKEOVERS[id(takeover.session)] = takeover
        _LIVE_TAKEOVERS.pop(id(takeover.session), None)
        raise ConstructionK7H1ActualObservedSupervisorBirthV1Error(
            "B2-C lifecycle retained an explicit cleanup quarantine",
            cleanup_handle=takeover,
        ) from error
    finally:
        e5a_v1._restore_fd_publication_signals(original_mask)  # noqa: SLF001


def run_h1_actual_observed_supervisor_birth_v1(
    runtime: b2a_v1.H1E5ARuntimeLeaseSuccessorV1,
    *,
    b2b_preregistration: b2b_v1.H1GuardianRuntimeGenesisPreregistrationV1,
    b2b_journal_directory: Path | str,
    birth_journal_directory: Path | str,
) -> H1ActualObservedSupervisorBirthResultV1:
    """One-call bounded construction runner; never exposes a live child."""

    _validate_live_code_closure()
    takeover = _prepare_h1_actual_observed_supervisor_birth_v1(
        runtime,
        b2b_preregistration=b2b_preregistration,
        b2b_journal_directory=b2b_journal_directory,
        birth_journal_directory=birth_journal_directory,
    )
    return complete_h1_actual_observed_supervisor_birth_v1(takeover)


def _poison_prebinding_after_fork_child(
    prebinding: H1SupervisorBirthSourcePrebindingV1,
) -> None:
    if prebinding._code_rx_address > 0:
        try:
            result = native_v1._LIBC.munmap(  # noqa: SLF001
                ctypes.c_void_p(prebinding._code_rx_address),
                len(native_v1.X86_64_TEXT_BYTES),
            )
        except BaseException:
            os._exit(127)
        if result != 0:
            os._exit(127)
    descriptors: list[int] = []
    for canonical, witness in prebinding._source_fds.values():
        descriptors.extend((witness, canonical))
    descriptors.extend(
        (
            prebinding._code_witness_fd,
            prebinding._code_fd,
            prebinding._manifest_witness_fd,
            prebinding._manifest_fd,
        )
    )
    for descriptor in descriptors:
        if descriptor < 0:
            continue
        try:
            os.close(descriptor)
        except OSError:
            pass
    prebinding._source_fds.clear()
    prebinding._code_witness_fd = -1
    prebinding._code_fd = -1
    prebinding._manifest_witness_fd = -1
    prebinding._manifest_fd = -1
    prebinding._code_rx_address = 0
    prebinding._code_rx_function = None
    prebinding._state = "FORK_POISONED"


def _poison_native_prefix_after_fork_child(
    prefix: _H1SupervisorNativeLaunchPrefixV1,
) -> None:
    if prefix.creator_pid_cell_mapping > 0:
        try:
            result = native_v1._LIBC.munmap(  # noqa: SLF001
                ctypes.c_void_p(prefix.creator_pid_cell_mapping), PID_CELL_BYTES
            )
        except BaseException:
            os._exit(127)
        if result != 0:
            os._exit(127)
        prefix.creator_pid_cell_mapping = 0
    if prefix.guardian_pid_cell_read_mapping > 0:
        try:
            result = native_v1._LIBC.munmap(  # noqa: SLF001
                ctypes.c_void_p(prefix.guardian_pid_cell_read_mapping),
                PID_CELL_BYTES,
            )
        except BaseException:
            os._exit(127)
        if result != 0:
            os._exit(127)
        prefix.guardian_pid_cell_read_mapping = 0
    seen: set[int] = set()
    for field_name in (
        "child_gate_source_fd",
        "parent_gate_fd",
        "creator_pidfd_fd",
        "escrowed_pidfd_fd",
        "creator_pid_cell_fd",
        "creator_cgroup_grant_fd",
        "pid_cell_reader_fd",
        "pid_cell_witness_fd",
        "pid_cell_sealer_fd",
        "escrow_sender_fd",
        "escrow_receiver_fd",
    ):
        descriptor = int(getattr(prefix, field_name))
        if descriptor >= 0 and descriptor not in seen:
            seen.add(descriptor)
            try:
                _RAW_OS_CLOSE(descriptor)
            except OSError:
                pass
        setattr(prefix, field_name, -1)
    prefix.state = "FORK_POISONED"


def _before_fork() -> None:
    # Registered after B2-B, so Python's reverse before-order is
    # B2-C -> B2-B -> B2-A -> E5A.
    _B2C_LOCK.acquire()


def _after_fork_parent() -> None:
    _B2C_LOCK.release()


def _after_fork_child() -> None:
    # Parent/child callbacks run in registration order.  B2-B has therefore
    # already poisoned its escrow before this B2-C-specific authority closes.
    global _B2C_LOCK
    prebindings = {
        id(item): item
        for item in (*_LIVE_PREBINDINGS.values(), *_CONSUMED_PREBINDINGS.values())
    }
    for prebinding in prebindings.values():
        _poison_prebinding_after_fork_child(prebinding)
    for takeover in tuple(
        {**_LIVE_TAKEOVERS, **_QUARANTINED_TAKEOVERS}.values()
    ):
        if takeover.native_prefix is not None:
            _poison_native_prefix_after_fork_child(takeover.native_prefix)
            takeover.pidfd = -1
        elif takeover.pidfd >= 0:
            try:
                _RAW_OS_CLOSE(takeover.pidfd)
            except OSError:
                pass
            takeover.pidfd = -1
        takeover.journal.poison_after_fork_child()
        takeover.state = "FORK_POISONED"
        takeover.child_pid = -1
    _LIVE_PREBINDINGS.clear()
    _CONSUMED_PREBINDINGS.clear()
    _LIVE_TAKEOVERS.clear()
    _QUARANTINED_TAKEOVERS.clear()
    _B2C_LOCK = threading.RLock()


_SELF_CALLABLES = MappingProxyType(
    {
        name: (globals()[name], globals()[name].__code__)
        for name in (
            "_domain_id",
            "_verify_birth_record",
            "_validate_live_code_closure",
            "_write_all",
            "_new_sealed_document_memfd",
            "_open_retained_source_fds",
            "_new_sealed_code_rx",
            "prebind_h1_actual_observed_supervisor_birth_v1",
            "_close_h1_supervisor_birth_source_prebinding_under_locks_v1",
            "close_h1_supervisor_birth_source_prebinding_v1",
            "verify_h1_supervisor_birth_source_prebinding_v1",
            "_finish_takeover_commit",
            "_finish_consume_commit",
            "_verify_prebinding_bytes",
            "_take_over_b2b_session",
            "_prepare_h1_actual_observed_supervisor_birth_v1",
            "_verify_current_takeover",
            "_new_seqpacket_pair",
            "_fd_at_least",
            "_close_unconsumed_native_prefix",
            "_prepare_native_launch_prefix_under_locks",
            "_recv_exact_seqpacket",
            "_read_process_start_ticks",
            "_pidfd_fact",
            "_require_pidfd_child_live",
            "_read_small_control",
            "_parse_single_nonnegative",
            "_parse_events",
            "_live_cgroup_snapshot",
            "_empty_cgroup_snapshot",
            "_wait_for_empty_cgroup_snapshot",
            "_waitid_fact",
            "_require_clean_child_exit",
            "_observe_child_and_persist_ack_under_locks",
            "_consume_permit_and_launch_native_prefix_v1",
            "_release_reap_and_observe_peak_under_locks",
            "_finish_peak_observation_from_returned_read_under_locks",
            "_close_postrun_b2c_resources_under_locks",
            "_close_birth_journal_and_finish_v1",
            "_close_taken_over_prebinding_under_locks",
            "_close_unconsumed_takeover_v1",
            "_close_postrun_b2c_resources_v1",
            "_validate_exact_clone_rejection",
            "_persist_clone_rejection_failure_closure",
            "_close_exact_clone_rejection_v1",
            "_clone_rejection_cleanup_document",
            "_release_reap_peak_v1",
            "_finish_peak_observation_from_returned_read_v1",
            "_recover_durable_protocol_records",
            "_terminated_wait_fact",
            "_failure_pidfd",
            "_kill_reap_empty_failure_under_locks",
            "_kill_reap_empty_failure_v1",
            "_build_bounded_birth_result",
            "_finish_positive_postrun_v1",
            "_birth_failure_cleanup_document",
            "_finish_birth_failure_postrun_v1",
            "_verify_embedded_content_document",
            "_verify_bounded_result_artifact_graph",
            "verify_h1_actual_observed_supervisor_birth_result_v1",
            "verify_h1_actual_observed_supervisor_birth_result_bytes_v1",
            "complete_h1_actual_observed_supervisor_birth_v1",
            "run_h1_actual_observed_supervisor_birth_v1",
        )
    }
)

_SELF_METHODS = MappingProxyType(
    {
        (owner, name): (getattr(owner, name), getattr(owner, name).__code__)
        for owner, names in (
            (
                H1SupervisorBirthSourcePrebindingV1,
                ("__post_init__", "to_document", "__reduce__"),
            ),
            (
                _BirthJournalRecordV1,
                ("to_document",),
            ),
            (
                _BirthJournalV1,
                (
                    "append",
                    "_finish_pending",
                    "_resume_pending",
                    "verify",
                    "close",
                    "poison_after_fork_child",
                ),
            ),
            (
                _H1SupervisorBirthTakeoverV1,
                ("__post_init__", "__reduce__", "poison_after_fork_child"),
            ),
            (
                _H1SupervisorNativeLaunchPrefixV1,
                ("__post_init__", "__reduce__"),
            ),
            (
                H1ActualObservedSupervisorBirthResultV1,
                ("__post_init__", "to_document"),
            ),
        )
        for name in names
    }
)

_SELF_GLOBALS = MappingProxyType(
    {
        "_RAW_OS_CLOSE": _RAW_OS_CLOSE,
        "_RAW_OS_WRITE": _RAW_OS_WRITE,
        "_FCNTL_FCNTL": _FCNTL_FCNTL,
        "_PREBIND_ISSUER": _PREBIND_ISSUER,
        "_TAKEOVER_ISSUER": _TAKEOVER_ISSUER,
        "_RESULT_ISSUER": _RESULT_ISSUER,
        "_NATIVE_PREFIX_ISSUER": _NATIVE_PREFIX_ISSUER,
        "_B2C_LOCK": _B2C_LOCK,
        "_LIVE_PREBINDINGS": _LIVE_PREBINDINGS,
        "_CONSUMED_PREBINDINGS": _CONSUMED_PREBINDINGS,
        "_LIVE_TAKEOVERS": _LIVE_TAKEOVERS,
        "_QUARANTINED_TAKEOVERS": _QUARANTINED_TAKEOVERS,
    }
)


os.register_at_fork(
    before=_before_fork,
    after_in_parent=_after_fork_parent,
    after_in_child=_after_fork_child,
)


__all__ = tuple(
    sorted(
        name
        for name in globals()
        if (
            name.isupper()
            or name.startswith("H1")
            or name.startswith("ConstructionK7")
            or name
            in {
                "run_h1_actual_observed_supervisor_birth_v1",
                "verify_h1_actual_observed_supervisor_birth_result_v1",
                "verify_h1_actual_observed_supervisor_birth_result_bytes_v1",
            }
        )
        and not name.startswith("_")
    )
)
