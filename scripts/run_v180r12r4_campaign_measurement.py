#!/usr/bin/env python3
"""Trusted one-shot outer observer for V180r12r4 measurement.

This process is deliberately outside the measured cgroup.  It is the sole
owner of the attempt lock, canonical event files, ACKs, retained cgroup
control-file descriptions, timeout, cleanup, and typed failure artifact.
Children receive only authenticated IPC and explicitly inherited data/control
descriptors; they never receive an EVENTS directory descriptor.

The public helpers are dependency-injected so tests cannot accidentally touch
the host cgroup tree or launch a process.  ``LinuxRuntimeAdapter`` retains the
real cgroup-v2, clone3(CLONE_PIDFD|CLONE_INTO_CGROUP), pidfd, and renameat2
implementation used by an authorized launch.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import errno
import fcntl
import hashlib
import hmac
import json
import marshal
import os
from pathlib import Path, PurePosixPath
import resource
import select
import signal
import socket
import stat
import struct
import sys
import time
import types
from typing import Any, Callable, Iterable, Mapping, NoReturn, Protocol, Sequence

from acfqp import construction_k7_domain_registry_extension_v180r12r4 as identity_domains
from acfqp import construction_k7_domain_registry_extension_v180r12r4e as evidence_domains
from acfqp import construction_k7_campaign_measurement_execution_authorization_v180r12r4 as authorization
from acfqp import construction_k7_campaign_measurement_authorization_evidence_freeze_v180r12r4 as authorization_evidence
from acfqp import construction_k7_campaign_measurement_finalizer_v180r12r4 as finalizer
from acfqp import construction_k7_campaign_measurement_ledger_v180r12r4 as ledger
from acfqp import construction_k7_campaign_measurement_protocol_v180r12r4 as protocol
from acfqp import construction_k7_campaign_measurement_supervisor_v180r12r4 as runtime
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


PROFILE_KEY = "run_v180r12r4_campaign_measurement"
ATTEMPT_RELATIVE_PATH = protocol.ATTEMPT_RELATIVE_PATH
OUTPUT_ROOT_RELATIVE_PATH = protocol.OUTPUT_ROOT_RELATIVE_PATH
EVENTS_RELATIVE_PATH = protocol.EVENTS_RELATIVE_PATH
FAILURE_RELATIVE_PATH = protocol.FAILURE_RELATIVE_PATH
SUBJECT_TEMP_RELATIVE_PATH = protocol.SUBJECT_TEMP_RELATIVE_PATH
SUBJECT_RESULT_RELATIVE_PATH = protocol.SUBJECT_RESULT_RELATIVE_PATH
EVIDENCE_INVENTORY_RELATIVE_PATH = protocol.EVIDENCE_INVENTORY_RELATIVE_PATH
EXECUTION_CLOSURE_RELATIVE_PATH = protocol.EXECUTION_CLOSURE_RELATIVE_PATH
OS_RECEIPT_RELATIVE_PATH = protocol.OS_RECEIPT_RELATIVE_PATH
LEDGER_CLOSURE_RELATIVE_PATH = protocol.LEDGER_CLOSURE_RELATIVE_PATH
TERMINAL_RELATIVE_PATH = protocol.TERMINAL_RELATIVE_PATH
RUNTIME_CAS_ROOT_RELATIVE_PATH = protocol.RUNTIME_CAS_ROOT_RELATIVE_PATH
VERIFICATION_RELATIVE_PATH = protocol.VERIFICATION_RELATIVE_PATH
VERIFICATION_FAILURE_RELATIVE_PATH = protocol.VERIFICATION_FAILURE_RELATIVE_PATH
RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH = (
    protocol.RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH
)
SUCCESS_EVENT_COUNT = 625
MAX_EVENT_COUNT = protocol.MAX_EVENT_COUNT
MAX_EVENT_BYTES = 64 * 1024
MAX_LEDGER_BYTES = 64 * 1024 * 1024
MEMORY_MAX_BYTES = 16 * 1024 * 1024 * 1024
PIDS_MAX = 2
WALL_TIMEOUT_SECONDS = 14_400
CAMPAIGN_CLEANUP_GRACE_SECONDS = 600
NANOSECONDS_PER_SECOND = 1_000_000_000
HARD_DEADLINE_DURATION_NS = WALL_TIMEOUT_SECONDS * NANOSECONDS_PER_SECOND
CAMPAIGN_CLEANUP_GRACE_NS = (
    CAMPAIGN_CLEANUP_GRACE_SECONDS * NANOSECONDS_PER_SECOND
)
FAILURE_RESERVE_BYTES = protocol.FAILURE_EMERGENCY_RESERVE_BYTES
FAILURE_ARTIFACT_ROW_CAP = 4_112
FAILURE_DIRECTORY_ENTRY_CAP = runtime.supervisor_contract_v180r12r4()[
    "failure_directory_entry_cap"
]
FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP = (
    runtime.supervisor_contract_v180r12r4()[
        "failure_directory_entry_name_total_byte_cap"
    ]
)
FAILURE_ARTIFACT_HASH_BYTE_CAP = (
    runtime.supervisor_contract_v180r12r4()["failure_artifact_stream_hash_byte_cap"]
)
FRAME_BYTE_CAP = 1024 * 1024
SOCK_SEQPACKET_BUFFER_REQUEST_BYTES = FRAME_BYTE_CAP
SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES = 2 * FRAME_BYTE_CAP
SNAPSHOT_BYTES_TRANSPORT_SCHEMA = (
    "acfqp.v180r12r4_snapshot_bytes_transport.v1"
)
SNAPSHOT_BYTES_TRANSPORT_BYTE_CAP = 512 * 1024
SNAPSHOT_BYTES_TRANSPORT_FIELDS = (
    "schema", "snapshot_receipt_id", "role", "byte_count", "sha256",
    "canonical_bytes_hex",
)
FRAME_HEADER = struct.Struct("!I")
CLONE_PIDFD = 0x00001000
CLONE_INTO_CGROUP = 0x200000000
RENAME_NOREPLACE = 1
CGROUP2_SUPER_MAGIC = 0x63677270
INTERNAL_BOOTSTRAP_ARGV_PREFIX = (
    "/usr/bin/python3", "-I", "-S", "-B", "-X",
    "pycache_prefix=/dev/null/v180r12r4",
)
INTERNAL_INITIAL_ENV_KEYS = frozenset(
    {"ACFQP_V180R12R4_LAUNCH_MANIFEST_SHA256", "LC_CTYPE"}
)
INTERNAL_FD_TARGETS = {
    "SUPERVISOR": (240, 241, 242, 243, 244, 245),
    "WORKER": (240, 241, 242, 243, 246, 247, 248),
}
PRECOMPILED_SOURCE_BUNDLE_FD = 240
INTERNAL_IPC_FD = 241
INTERNAL_MAC_KEY_FD = 242
INTERNAL_CONTEXT_FD = 243
SUPERVISOR_REPOSITORY_ROOT_FD = 244
SUPERVISOR_WORKER_CGROUP_FD = 245
REQUIRED_MEMFD_SEAL_MASK = sum(
    (
        fcntl.F_SEAL_SEAL,
        fcntl.F_SEAL_SHRINK,
        fcntl.F_SEAL_GROW,
        fcntl.F_SEAL_WRITE,
    )
)
PRECOMPILED_SOURCE_BUNDLE_SCHEMA = (
    "acfqp.v180r12r4_precompiled_source_bundle.v1"
)
MEASURED_TARGETS = ("measurement", "supervisor", "worker")
EXTERNAL_CONTEXT_FD = 249
DELEGATED_CGROUP_PARENT_FD = 250
CGROUP2_MOUNT_FD = 251
SOURCE_SYSTEMD_SERVICE_FD = 252
EXTERNAL_LAUNCH_CONTEXT_SCHEMA = (
    "acfqp.v180r12r4_external_launch_context.v1"
)
VERIFIED_EXTERNAL_LAUNCH_CONTEXT_SCHEMA = (
    "acfqp.v180r12r4_verified_external_launch_context.v1"
)
REVALIDATED_EXTERNAL_MEASUREMENT_CONTEXT_SCHEMA = (
    protocol.REVALIDATED_EXTERNAL_MEASUREMENT_CONTEXT_SCHEMA
)
PRE_ATTEMPT_HOST_CONFORMANCE_SCHEMA = (
    protocol.PRE_ATTEMPT_HOST_CONFORMANCE_SCHEMA
)
PRE_ATTEMPT_HOST_CONFORMANCE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_pre_attempt_host_conformance.json"
)
PRE_ATTEMPT_HOST_CONFORMANCE_BYTE_CAP = (
    protocol.PRE_ATTEMPT_HOST_CONFORMANCE_BYTE_CAP
)
SOCKET_BUFFER_CAPABILITY_FACT_SCHEMA = (
    protocol.SOCKET_BUFFER_CAPABILITY_FACT_SCHEMA
)
SOCKET_BUFFER_CAPABILITY_FACT_FIELDS = (
    protocol.SOCKET_BUFFER_CAPABILITY_FACT_FIELDS
)
SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS = (
    protocol.SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS
)
SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS = (
    protocol.SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS
)
SOCKET_BUFFER_CAPABILITY_EXPECTED_EXACT_PROPERTIES = (
    protocol.SOCKET_BUFFER_CAPABILITY_EXPECTED_EXACT_PROPERTIES
)
SOCKET_BUFFER_CAPABILITY_EXPECTED_MINIMUM_PROPERTIES = (
    protocol.SOCKET_BUFFER_CAPABILITY_EXPECTED_MINIMUM_PROPERTIES
)
SOCKET_BUFFER_CAPABILITY_MISMATCH_SCOPE = (
    protocol.SOCKET_BUFFER_CAPABILITY_MISMATCH_SCOPE
)
SOCKET_BUFFER_CAPABILITY_INSUFFICIENT_CAUSE = (
    protocol.SOCKET_BUFFER_CAPABILITY_INSUFFICIENT_CAUSE
)
PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA = (
    protocol.PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA
)
PRODUCTION_RUNTIME_PLACEMENT_T2_SCHEMA = (
    protocol.PRODUCTION_RUNTIME_PLACEMENT_T2_SCHEMA
)
PRODUCTION_RUNTIME_PLACEMENT_T3_SCHEMA = (
    protocol.PRODUCTION_RUNTIME_PLACEMENT_T3_SCHEMA
)
TYPED_LAUNCH_FAILURE_SUBSTAGES = protocol.TYPED_LAUNCH_FAILURE_SUBSTAGES
PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN = (
    "acfqp:construction-k7-production-transient-service-token:v180r12r4"
)
PRODUCTION_TRANSIENT_SERVICE_ROWS = {
    "measurement": (
        "1ba5304a7d653a3805fdca4754eeb7ff2feaa63794c6b866f47adda85160668d",
        "acfqp-v180r12r4-measurement-"
        "1ba5304a7d653a3805fdca4754eeb7ff2feaa63794c6b866f47adda85160668d.service",
    ),
    "verification": (
        "14e3fead4dab312dd06026196922d455600e970d5de64624e3d47b66525c0221",
        "acfqp-v180r12r4-verification-"
        "14e3fead4dab312dd06026196922d455600e970d5de64624e3d47b66525c0221.service",
    ),
}
EXTERNAL_LAUNCH_CONTEXT_FIELDS = (
    "schema",
    "target",
    "actor_role",
    "repository_root",
    "c_pre_root",
    "prereg_commit_id",
    "prelaunch_materialization_terminal_id",
    "prelaunch_materialization_terminal_byte_count",
    "prelaunch_materialization_terminal_sha256",
    "prelaunch_launch_manifest_sha256",
    "prelaunch_launch_rule_id",
    "current_launch_attempt_id",
    "current_launch_attempt_byte_count",
    "current_launch_attempt_sha256",
    "measurement_launch_attempt_id",
    "measurement_launch_attempt_byte_count",
    "measurement_launch_attempt_sha256",
    "protocol_id",
    "protocol_byte_count",
    "protocol_sha256",
    "authorization_id",
    "authorization_byte_count",
    "authorization_sha256",
    "authorization_evidence_id",
    "authorization_evidence_byte_count",
    "authorization_evidence_sha256",
    "campaign_measurement_execution_slot_id",
    "logical_occurrence_id",
    "execution_nonce",
    "campaign_attempt_id",
    "monotonic_origin_ns",
    "hard_deadline_ns",
    "campaign_deadline_ns",
    "cgroup_parent_fact",
    "runtime_capability_fact",
    "production_systemd_service_invocation",
    "production_runtime_placement_t1",
    "inherited_fd_roles",
    "target_payload",
    "one_shot",
)
VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS = (
    *EXTERNAL_LAUNCH_CONTEXT_FIELDS,
    "precompiled_source_bundle_sha256",
    "native_zero_precompiled_source_rows",
    "external_launch_context_sha256",
    "context_consumed_once",
)
REVALIDATED_EXTERNAL_MEASUREMENT_CONTEXT_FIELDS = (
    *VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS,
    "production_runtime_placement_t2",
)
if (
    REVALIDATED_EXTERNAL_MEASUREMENT_CONTEXT_FIELDS
    != protocol.REVALIDATED_EXTERNAL_MEASUREMENT_CONTEXT_FIELDS
):
    raise RuntimeError("revalidated external context protocol mirror changed")
EXTERNAL_FD_CONTRACT_ROWS = {
    "measurement": (
        (
            EXTERNAL_CONTEXT_FD,
            "EXTERNAL_LAUNCH_CONTEXT_MEMFD",
            "SEALED_MEMFD",
            "READ_ONLY",
            "0400",
            True,
            True,
            False,
        ),
        (
            DELEGATED_CGROUP_PARENT_FD,
            "DELEGATED_CGROUP_PARENT_DIRECTORY",
            "DIRECTORY",
            "READ_ONLY",
            None,
            True,
            False,
            True,
        ),
        (
            CGROUP2_MOUNT_FD,
            "CGROUP2_MOUNT_DIRECTORY",
            "DIRECTORY",
            "O_PATH",
            None,
            True,
            False,
            True,
        ),
        (
            SOURCE_SYSTEMD_SERVICE_FD,
            "SOURCE_SYSTEMD_SERVICE_DIRECTORY",
            "DIRECTORY",
            "READ_ONLY",
            None,
            True,
            False,
            True,
        ),
    ),
    "verification": (
        (
            EXTERNAL_CONTEXT_FD,
            "EXTERNAL_LAUNCH_CONTEXT_MEMFD",
            "SEALED_MEMFD",
            "READ_ONLY",
            "0400",
            True,
            True,
            False,
        ),
    ),
}
EXTERNAL_FD_ROLE_ROWS = {
    target: tuple((row[0], row[1]) for row in rows)
    for target, rows in EXTERNAL_FD_CONTRACT_ROWS.items()
}
EXTERNAL_TARGET_PAYLOADS = {
    "measurement": {
        "delegated_cgroup_parent_fd": DELEGATED_CGROUP_PARENT_FD,
        "cgroup2_mount_fd": CGROUP2_MOUNT_FD,
        "source_systemd_service_fd": SOURCE_SYSTEMD_SERVICE_FD,
    },
    "verification": {},
}
FAILURE_ARTIFACT_FIXED_PATH_KINDS = (
    (ATTEMPT_RELATIVE_PATH, "FILE"),
    (OUTPUT_ROOT_RELATIVE_PATH, "DIRECTORY"),
    (EVENTS_RELATIVE_PATH, "DIRECTORY"),
    (FAILURE_RELATIVE_PATH, "FILE"),
    (SUBJECT_TEMP_RELATIVE_PATH, "FILE"),
    (SUBJECT_RESULT_RELATIVE_PATH, "FILE"),
    (EVIDENCE_INVENTORY_RELATIVE_PATH, "FILE"),
    (EXECUTION_CLOSURE_RELATIVE_PATH, "FILE"),
    (OS_RECEIPT_RELATIVE_PATH, "FILE"),
    (LEDGER_CLOSURE_RELATIVE_PATH, "FILE"),
    (TERMINAL_RELATIVE_PATH, "FILE"),
    (RUNTIME_CAS_ROOT_RELATIVE_PATH, "DIRECTORY"),
    (VERIFICATION_RELATIVE_PATH, "FILE"),
    (VERIFICATION_FAILURE_RELATIVE_PATH, "FILE"),
    (RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH, "FILE"),
)
if tuple(sorted(FAILURE_ARTIFACT_FIXED_PATH_KINDS)) != (
    runtime.FAILURE_ARTIFACT_FIXED_PATH_KIND_ROWS
):
    raise RuntimeError("runtime failure fixed-path inventory changed")
SUCCESS_ARTIFACT_RELATIVE_PATH_BY_KEY = {
    "evidence_inventory": EVIDENCE_INVENTORY_RELATIVE_PATH,
    "execution_closure": EXECUTION_CLOSURE_RELATIVE_PATH,
    "os_receipt": OS_RECEIPT_RELATIVE_PATH,
    "ledger_closure": LEDGER_CLOSURE_RELATIVE_PATH,
}
SUCCESS_ARTIFACT_BYTE_CAP_BY_KEY = {
    "evidence_inventory": protocol.EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP,
    "execution_closure": protocol.EXECUTION_CLOSURE_BYTE_CAP,
    "os_receipt": protocol.OS_RECEIPT_BUNDLE_BYTE_CAP,
    "ledger_closure": protocol.LEDGER_CLOSURE_BYTE_CAP,
}
if tuple(SUCCESS_ARTIFACT_RELATIVE_PATH_BY_KEY) != finalizer.SUCCESS_ARTIFACT_ORDER:
    raise RuntimeError("runtime/finalizer success artifact order changed")
if tuple(SUCCESS_ARTIFACT_BYTE_CAP_BY_KEY) != finalizer.SUCCESS_ARTIFACT_ORDER:
    raise RuntimeError("runtime/finalizer success artifact cap order changed")


class V180R12R4RuntimeError(RuntimeError):
    """The one-shot runtime cannot preserve the frozen execution contract."""


class V180R12R4ReplayForbidden(V180R12R4RuntimeError):
    """The durable attempt identity or one of its progress paths already exists."""


class V180R12R4RuntimeTimeout(V180R12R4RuntimeError):
    """The frozen monotonic wall deadline expired."""


class V180R12R4CapViolation(V180R12R4RuntimeError):
    """A preregistered byte, count, memory, PID, or time cap was exceeded."""


class V180R12R4DurableWriteFailure(V180R12R4RuntimeError):
    """A write-once path failed, possibly after its directory entry existed."""

    def __init__(self, relative_path: str, path_created: bool) -> None:
        super().__init__("durable write-once operation failed")
        self.relative_path = relative_path
        self.path_created = path_created


class V180R12R4OwnedAttemptFailure(V180R12R4RuntimeError):
    """This process created ATTEMPT, so it must now freeze typed failure."""

    def __init__(self, failure_reserve: bytearray) -> None:
        super().__init__("owned ATTEMPT write failed after O_EXCL creation")
        self.failure_reserve = failure_reserve


def _validate_shared_deadlines_v180r12r4(
    context: Mapping[str, Any],
    *,
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
) -> tuple[int, int, int]:
    """Validate the launcher's one shared monotonic time axis.

    The campaign deadline deliberately precedes the outer hard deadline by ten
    minutes.  The observer never derives a fresh relative timeout after this
    gate; the remaining interval may only shrink.
    """

    origin_ns = context.get("monotonic_origin_ns")
    hard_deadline_ns = context.get("hard_deadline_ns")
    campaign_deadline_ns = context.get("campaign_deadline_ns")
    if not (
        type(origin_ns) is int
        and type(hard_deadline_ns) is int
        and type(campaign_deadline_ns) is int
        and 0 < origin_ns < campaign_deadline_ns < hard_deadline_ns
        and hard_deadline_ns - origin_ns == HARD_DEADLINE_DURATION_NS
        and hard_deadline_ns - campaign_deadline_ns
        == CAMPAIGN_CLEANUP_GRACE_NS
        and callable(monotonic_ns)
    ):
        _fail("shared monotonic deadline contract changed")
    now_ns = monotonic_ns()
    if type(now_ns) is not int or now_ns >= campaign_deadline_ns:
        raise V180R12R4RuntimeTimeout(
            "campaign deadline expired before ATTEMPT ownership"
        )
    return origin_ns, hard_deadline_ns, campaign_deadline_ns


def _check_campaign_deadline_v180r12r4(
    campaign_deadline_ns: int,
    *,
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
    boundary: str = "measurement lifecycle",
) -> None:
    if type(campaign_deadline_ns) is not int or campaign_deadline_ns <= 0:
        _fail("campaign deadline is not one positive monotonic timestamp")
    now_ns = monotonic_ns()
    if type(now_ns) is not int or now_ns >= campaign_deadline_ns:
        raise V180R12R4RuntimeTimeout(
            "campaign deadline expired at " + boundary
        )


class CampaignDeadlineWatchdogV180R12R4:
    """Fail-safe SIGALRM guard for blocking syscalls on the campaign axis."""

    __slots__ = (
        "campaign_deadline_ns",
        "_monotonic_ns",
        "_previous_handler",
        "armed",
        "cancel_attempted",
        "cancel_succeeded",
        "ignore_attempted",
        "ignore_succeeded",
        "restore_attempted",
        "restore_succeeded",
        "_cleanup_error_0",
        "_cleanup_error_1",
        "_cleanup_error_2",
        "deadline_expired_during_exception",
        "_exception_path_timeout",
    )

    def __init__(
        self,
        campaign_deadline_ns: int,
        *,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if (
            type(campaign_deadline_ns) is not int
            or campaign_deadline_ns <= 0
            or not callable(monotonic_ns)
        ):
            _fail("campaign watchdog construction changed")
        self.campaign_deadline_ns = campaign_deadline_ns
        self._monotonic_ns = monotonic_ns
        self._previous_handler: Any = None
        self.armed = False
        self.cancel_attempted = False
        self.cancel_succeeded = False
        self.ignore_attempted = False
        self.ignore_succeeded = False
        self.restore_attempted = False
        self.restore_succeeded = False
        # Preallocate all secondary-error slots before the 4 MiB emergency
        # reserve.  Neutralization stores references only; it never formats or
        # grows a container while memory may still be exhausted.
        self._cleanup_error_0: BaseException | None = None
        self._cleanup_error_1: BaseException | None = None
        self._cleanup_error_2: BaseException | None = None
        self.deadline_expired_during_exception = False
        self._exception_path_timeout = V180R12R4RuntimeTimeout(
            "campaign deadline expired while another primary was active"
        )

    def _expired(self, _signum: int, _frame: Any) -> None:
        # Python 3.10 has no ``sys.exception``.  ``sys.exc_info`` is nevertheless
        # sufficient here: if delivery lands anywhere in exception unwinding or
        # its handler prologue, raising a second exception would replace the
        # owned scientific/runtime primary before typed FAILURE can be emitted.
        # Store one preallocated flag instead; the next neutralization/teardown
        # consumes it as secondary evidence.  Outside an active exception the
        # alarm still interrupts blocking syscalls immediately.
        if sys.exc_info()[0] is not None:
            self.deadline_expired_during_exception = True
            return
        raise V180R12R4RuntimeTimeout(
            "campaign measurement exceeded its shared monotonic deadline"
        )

    def _remember_cleanup_error(self, error: BaseException) -> None:
        if self._cleanup_error_0 is None:
            self._cleanup_error_0 = error
        elif self._cleanup_error_1 is None:
            self._cleanup_error_1 = error
        elif self._cleanup_error_2 is None:
            self._cleanup_error_2 = error

    def arm(self) -> None:
        if self.armed or self._previous_handler is not None:
            _fail("campaign watchdog lifecycle was reused")
        if signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
            _fail("measurement inherited an active real-time interval timer")
        _check_campaign_deadline_v180r12r4(
            self.campaign_deadline_ns,
            monotonic_ns=self._monotonic_ns,
            boundary="watchdog arm",
        )
        remaining_ns = self.campaign_deadline_ns - self._monotonic_ns()
        if remaining_ns <= 0:
            raise V180R12R4RuntimeTimeout(
                "campaign deadline expired during watchdog arm"
            )
        self._previous_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, self._expired)
        signal.setitimer(
            signal.ITIMER_REAL, remaining_ns / NANOSECONDS_PER_SECOND
        )
        self.armed = True

    def neutralize(self) -> None:
        """Cancel and ignore SIGALRM before reserve release or formatting."""

        if self._previous_handler is None and not self.armed:
            # ``arm`` may fail closed on an inherited timer before touching
            # process signal state.  Do not cancel or replace state we never
            # owned.
            self.cancel_attempted = True
            self.cancel_succeeded = True
            self.ignore_attempted = True
            self.ignore_succeeded = True
            return
        if not self.cancel_succeeded:
            self.cancel_attempted = True
            try:
                signal.setitimer(signal.ITIMER_REAL, 0.0)
                self.cancel_succeeded = True
            except BaseException as error:
                self._remember_cleanup_error(error)
        if not self.ignore_succeeded:
            self.ignore_attempted = True
            try:
                signal.signal(signal.SIGALRM, signal.SIG_IGN)
                self.ignore_succeeded = True
            except BaseException as error:
                self._remember_cleanup_error(error)
        self.armed = False
        if self.deadline_expired_during_exception:
            self._remember_cleanup_error(self._exception_path_timeout)

    def neutralize_preserving_primary(self) -> None:
        """Catch the one-shot alarm even if it fires inside exception cleanup."""

        try:
            self.neutralize()
            return
        except BaseException as error:
            self._remember_cleanup_error(error)
        # ITIMER_REAL is one-shot.  After its handler interrupted the first
        # attempt, retry cancellation/ignore while preserving the original
        # scientific/runtime primary held by the caller.
        try:
            self.neutralize()
        except BaseException as error:
            self._remember_cleanup_error(error)

    def restore(self) -> None:
        if not self.cancel_attempted or not self.ignore_attempted:
            self.neutralize()
        if not self.restore_attempted:
            self.restore_attempted = True
            try:
                # If cancellation failed, keep SIGALRM ignored until process
                # exit.  Restoring an earlier handler while a live timer may
                # still fire would destroy typed failure liveness.
                if self.cancel_succeeded and self._previous_handler is not None:
                    signal.signal(signal.SIGALRM, self._previous_handler)
                self.restore_succeeded = self.cancel_succeeded
            except BaseException as error:
                self._remember_cleanup_error(error)

    def first_cleanup_error(self) -> BaseException | None:
        if self._cleanup_error_0 is not None:
            return self._cleanup_error_0
        if self._cleanup_error_1 is not None:
            return self._cleanup_error_1
        return self._cleanup_error_2

    def teardown(self) -> None:
        self.neutralize()
        self.restore()
        error = self.first_cleanup_error()
        if error is not None:
            raise V180R12R4RuntimeError(
                "campaign deadline watchdog teardown failed"
            ) from error


def _fail(message: str) -> NoReturn:
    raise V180R12R4RuntimeError(message)


def _annotate_launch_primary_v180r12r4(
    primary: BaseException,
    substage: str,
    *,
    child_created: bool = False,
    pidfd_acquired: bool = False,
    exec_observed: bool = False,
) -> None:
    """Attach typed launch facts to the original primary without replacing it."""

    if (
        substage not in TYPED_LAUNCH_FAILURE_SUBSTAGES
        or type(child_created) is not bool
        or type(pidfd_acquired) is not bool
        or type(exec_observed) is not bool
        or pidfd_acquired and not child_created
        or exec_observed and not pidfd_acquired
    ):
        _fail("typed launch primary annotation changed")
    try:
        existing = BaseException.__getattribute__(primary, "launch_substage")
    except BaseException:
        existing = None
    if existing in TYPED_LAUNCH_FAILURE_SUBSTAGES:
        # A signal can be delivered after clone3 has filled the caller-owned
        # pidfd cell but before ctypes returns its result to Python.  The
        # boundary annotation then already exists, while the subsequently
        # recovered ownership facts are strictly stronger.  Promote those
        # booleans monotonically without changing the original substage or
        # errno primary.
        try:
            existing_child_created = BaseException.__getattribute__(
                primary, "launch_child_created"
            )
            existing_pidfd_acquired = BaseException.__getattribute__(
                primary, "launch_pidfd_acquired"
            )
            existing_exec_observed = BaseException.__getattribute__(
                primary, "launch_exec_observed"
            )
        except BaseException:
            return
        if all(
            type(value) is bool
            for value in (
                existing_child_created,
                existing_pidfd_acquired,
                existing_exec_observed,
            )
        ):
            BaseException.__setattr__(
                primary,
                "launch_child_created",
                existing_child_created or child_created,
            )
            BaseException.__setattr__(
                primary,
                "launch_pidfd_acquired",
                existing_pidfd_acquired or pidfd_acquired,
            )
            BaseException.__setattr__(
                primary,
                "launch_exec_observed",
                existing_exec_observed or exec_observed,
            )
        return
    try:
        supplied_errno = BaseException.__getattribute__(primary, "errno")
    except BaseException:
        supplied_errno = None
    launch_errno = (
        supplied_errno
        if type(supplied_errno) is int and supplied_errno > 0
        else None
    )
    for name, value in (
        ("launch_substage", substage),
        ("launch_errno", launch_errno),
        ("launch_child_created", child_created),
        ("launch_pidfd_acquired", pidfd_acquired),
        ("launch_exec_observed", exec_observed),
    ):
        BaseException.__setattr__(primary, name, value)


def _launch_boundary_v180r12r4(
    substage: str,
    operation: Callable[[], Any],
    *,
    fault_injector: Callable[[str], None] | None = None,
    child_created: bool = False,
    pidfd_acquired: bool = False,
    exec_observed: bool = False,
) -> Any:
    """Run one launch boundary and preserve its exact original primary."""

    try:
        if fault_injector is not None:
            fault_injector(substage)
        return operation()
    except BaseException as primary:
        _annotate_launch_primary_v180r12r4(
            primary,
            substage,
            child_created=child_created,
            pidfd_acquired=pidfd_acquired,
            exec_observed=exec_observed,
        )
        raise


def configure_seqpacket_pair_v180r12r4(
    parent: socket.socket, child: socket.socket
) -> tuple[tuple[int, int], tuple[int, int]]:
    """Provision both authenticated IPC endpoints before clone or send.

    Linux reports twice the requested SO_SNDBUF/SO_RCVBUF value.  The frozen
    request therefore has an exact effective minimum of two maximum frames on
    every endpoint.  A host that cannot provide it fails before child creation
    or campaign progression.
    """

    if (
        type(parent) is not socket.socket
        or type(child) is not socket.socket
        or parent.type & socket.SOCK_SEQPACKET != socket.SOCK_SEQPACKET
        or child.type & socket.SOCK_SEQPACKET != socket.SOCK_SEQPACKET
    ):
        _fail("runtime IPC buffer provisioning requires one seqpacket pair")
    observations: list[tuple[int, int]] = []
    for endpoint in (parent, child):
        endpoint.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_SNDBUF,
            SOCK_SEQPACKET_BUFFER_REQUEST_BYTES,
        )
        endpoint.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_RCVBUF,
            SOCK_SEQPACKET_BUFFER_REQUEST_BYTES,
        )
        observed = (
            endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF),
            endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF),
        )
        if (
            any(type(value) is not int for value in observed)
            or min(observed) < SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
        ):
            _fail("runtime IPC seqpacket buffers do not cover the frame cap")
        observations.append(observed)
    return observations[0], observations[1]


def _canonical(value: Any) -> bytes:
    return canonical_json_bytes(value)


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty exact bytes")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V180R12R4RuntimeError(f"{label} is not canonical JSON") from error
    if type(value) is not dict or _canonical(value) != raw:
        _fail(f"{label} must be one canonical JSON object")
    return value


def _thaw_json_value(value: Any) -> Any:
    """Copy one immutable bootstrap value into canonical-JSON primitives."""

    if isinstance(value, Mapping):
        return {key: _thaw_json_value(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw_json_value(item) for item in value]
    if type(value) is list:
        return [_thaw_json_value(item) for item in value]
    return value


def _require_content_id(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{label} must be one lowercase SHA-256 identity")
    return value


def _validate_native_zero_precompiled_rows_v180r12r4(
    value: Any,
) -> tuple[dict[str, Any], ...]:
    if type(value) not in {tuple, list} or not value:
        _fail("native-zero precompiled source rows are not one exact sequence")
    fields = {
        "source_kind", "name", "source_path", "is_package",
        "marshal_byte_count", "marshal_sha256",
    }
    expected_targets = dict(ledger.PRECOMPILED_TARGET_SOURCE_PATHS)
    rows: list[dict[str, Any]] = []
    coordinates: list[tuple[str, str]] = []
    for supplied in value:
        row = _thaw_json_value(supplied)
        if type(row) is not dict or set(row) != fields:
            _fail("native-zero precompiled source row field set changed")
        kind = row["source_kind"]
        name = row["name"]
        path = row["source_path"]
        if (
            kind not in {"MODULE", "TARGET"}
            or type(name) is not str
            or not name
            or type(path) is not str
            or not path
            or path.startswith("/")
            or "//" in path
            or any(part in {"", ".", ".."} for part in path.split("/"))
            or type(row["marshal_byte_count"]) is not int
            or row["marshal_byte_count"] <= 0
        ):
            _fail("native-zero precompiled source row value changed")
        _require_content_id(
            row["marshal_sha256"], "native-zero precompiled marshal SHA-256"
        )
        if kind == "MODULE":
            if (
                type(row["is_package"]) is not bool
                or (name != "acfqp" and not name.startswith("acfqp."))
                or any(not part.isidentifier() for part in name.split("."))
            ):
                _fail("native-zero application module row changed")
        elif not (
            row["is_package"] is False
            and expected_targets.get(name) == path
        ):
            _fail("native-zero measured target row changed")
        coordinates.append((kind, name))
        rows.append(row)
    if (
        coordinates != sorted(set(coordinates))
        or {name for kind, name in coordinates if kind == "TARGET"}
        != set(MEASURED_TARGETS)
        or not any(kind == "MODULE" for kind, _name in coordinates)
    ):
        _fail("native-zero precompiled source rows are incomplete or reordered")
    return tuple(rows)


EXTERNAL_REPLAY_DOCUMENT_ROWS = (
    (
        "protocol",
        "protocol_id",
        "protocol_byte_count",
        "protocol_sha256",
        "campaign_measurement_protocol_id",
    ),
    (
        "authorization",
        "authorization_id",
        "authorization_byte_count",
        "authorization_sha256",
        "execution_authorization_id",
    ),
    (
        "authorization_evidence",
        "authorization_evidence_id",
        "authorization_evidence_byte_count",
        "authorization_evidence_sha256",
        "authorization_evidence_id",
    ),
    (
        "prelaunch_materialization_terminal",
        "prelaunch_materialization_terminal_id",
        "prelaunch_materialization_terminal_byte_count",
        "prelaunch_materialization_terminal_sha256",
        "materialization_terminal_id",
    ),
    (
        "current_launch_attempt",
        "current_launch_attempt_id",
        "current_launch_attempt_byte_count",
        "current_launch_attempt_sha256",
        "launch_attempt_id",
    ),
    (
        "measurement_launch_attempt",
        "measurement_launch_attempt_id",
        "measurement_launch_attempt_byte_count",
        "measurement_launch_attempt_sha256",
        "launch_attempt_id",
    ),
)


def validate_verified_external_launch_context_v180r12r4(
    value: Mapping[str, Any],
    *,
    replayed_documents: Mapping[str, bytes],
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
) -> types.MappingProxyType:
    """Validate the source-bound external context before campaign ATTEMPT.

    The context SHA is only an integrity join to FD249.  Authorization comes
    from independently replaying the three frozen authority documents and the
    two prelaunch transport documents supplied in ``replayed_documents``.
    """

    if (
        type(value) is not types.MappingProxyType
        or tuple(value) != VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS
        or set(replayed_documents) != {
            row[0] for row in EXTERNAL_REPLAY_DOCUMENT_ROWS
        }
    ):
        _fail("external launch context or replay population field set changed")
    context = dict(value)
    target = context["target"]
    expected_actor = {"measurement": "OBSERVER", "verification": "VERIFIER"}
    if target not in expected_actor:
        _fail("external launch context target changed")
    raw_document = {
        key: _thaw_json_value(context[key]) for key in EXTERNAL_LAUNCH_CONTEXT_FIELDS
    }
    raw_document["schema"] = EXTERNAL_LAUNCH_CONTEXT_SCHEMA
    raw_sha256 = hashlib.sha256(_canonical(raw_document)).hexdigest()
    id_fields = (
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256",
        "prelaunch_launch_rule_id",
        "current_launch_attempt_id",
        "current_launch_attempt_sha256",
        "measurement_launch_attempt_id",
        "measurement_launch_attempt_sha256",
        "protocol_id",
        "protocol_sha256",
        "authorization_id",
        "authorization_sha256",
        "authorization_evidence_id",
        "authorization_evidence_sha256",
        "campaign_measurement_execution_slot_id",
        "logical_occurrence_id",
        "execution_nonce",
        "campaign_attempt_id",
        "precompiled_source_bundle_sha256",
        "external_launch_context_sha256",
    )
    for field_name in id_fields:
        _require_content_id(context[field_name], "external context " + field_name)
    if (
        type(context["prereg_commit_id"]) is not str
        or len(context["prereg_commit_id"]) != 40
        or any(
            character not in "0123456789abcdef"
            for character in context["prereg_commit_id"]
        )
    ):
        _fail("external context preregistration commit must be lowercase 40-hex")
    for field_name in (
        "prelaunch_materialization_terminal_byte_count",
        "current_launch_attempt_byte_count",
        "measurement_launch_attempt_byte_count",
        "protocol_byte_count",
        "authorization_byte_count",
        "authorization_evidence_byte_count",
    ):
        if type(context[field_name]) is not int or context[field_name] <= 0:
            _fail("external context byte count changed")
    _validate_shared_deadlines_v180r12r4(
        context, monotonic_ns=monotonic_ns
    )
    repository_root = PurePosixPath(context["repository_root"])
    c_pre_root = PurePosixPath(context["c_pre_root"])
    inherited = tuple(context["inherited_fd_roles"])
    target_payload = _thaw_json_value(context["target_payload"])
    production_invocation = _thaw_json_value(
        context["production_systemd_service_invocation"]
    )
    placement_t1 = _thaw_json_value(context["production_runtime_placement_t1"])
    expected_token, expected_unit = PRODUCTION_TRANSIENT_SERVICE_ROWS[target]
    if not (
        context["schema"] == VERIFIED_EXTERNAL_LAUNCH_CONTEXT_SCHEMA
        and context["actor_role"] == expected_actor[target]
        and repository_root.is_absolute()
        and repository_root.as_posix() == context["repository_root"]
        and c_pre_root.is_absolute()
        and c_pre_root.as_posix() == context["c_pre_root"]
        and context["one_shot"] is True
        and context["context_consumed_once"] is True
        and context["external_launch_context_sha256"] == raw_sha256
        and inherited == EXTERNAL_FD_ROLE_ROWS[target]
        and target_payload == EXTERNAL_TARGET_PAYLOADS[target]
        and type(production_invocation) is dict
        and set(production_invocation)
        == set(protocol.PRODUCTION_SYSTEMD_SERVICE_INVOCATION_FIELDS)
        and production_invocation.get("schema")
        == "acfqp.v180r12r4_production_systemd_service_invocation.v1"
        and production_invocation.get("target") == target
        and production_invocation.get("token_domain")
        == PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN
        and production_invocation.get("token") == expected_token
        and production_invocation.get("unit_name") == expected_unit
        and production_invocation.get("unit_kind") == "SERVICE_NOT_SCOPE"
        and production_invocation.get("slice") == "app.slice"
        and production_invocation.get("service_type") == "exec"
        and production_invocation.get("delegate") is True
        and type(placement_t1) is dict
        and set(placement_t1) == set(protocol.PRODUCTION_RUNTIME_PLACEMENT_T1_FIELDS)
        and placement_t1.get("schema") == PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA
        and placement_t1.get("target") == target
        and placement_t1.get("token") == expected_token
        and placement_t1.get("unit_name") == expected_unit
        and placement_t1.get("slice") == "app.slice"
        and placement_t1.get("self_pid_in_source_cgroup_procs") is True
        and placement_t1.get("nearest_common_ancestor_is_app_slice") is True
        and placement_t1.get("parent_cgroup_procs_o_wronly_openable") is True
        and placement_t1.get("planned_measurement_root_absent") is True
        and placement_t1.get("t1_complete_before_child_popen") is True
        and (
            target != "measurement"
            or context["current_launch_attempt_id"]
            == context["measurement_launch_attempt_id"]
        )
    ):
        _fail("external launch context role, transport, or integrity join changed")
    expected_attempt_id = identity_domains.derive_campaign_measurement_attempt_id_v180r12r4(
        protocol_id=context["protocol_id"],
        authorization_id=context["authorization_id"],
        authorization_evidence_id=context["authorization_evidence_id"],
        campaign_measurement_execution_slot_id=context[
            "campaign_measurement_execution_slot_id"
        ],
        logical_occurrence_id=context["logical_occurrence_id"],
        execution_nonce=context["execution_nonce"],
    )
    if context["campaign_attempt_id"] != expected_attempt_id:
        _fail("external context campaign attempt differs from six-input authority")
    supplied_cgroup_fact = _thaw_json_value(context["cgroup_parent_fact"])
    supplied_capability_fact = _thaw_json_value(
        context["runtime_capability_fact"]
    )
    cgroup_fact = protocol.validate_cgroup_parent_fact_v180r12r4(
        supplied_cgroup_fact
    )
    capability_fact = protocol.validate_runtime_capability_fact_v180r12r4(
        supplied_capability_fact
    )
    if (
        supplied_cgroup_fact != cgroup_fact
        or supplied_capability_fact != capability_fact
    ):
        _fail("external context capability facts are not exact canonical mappings")
    _validate_native_zero_precompiled_rows_v180r12r4(
        context["native_zero_precompiled_source_rows"]
    )

    replayed: dict[str, dict[str, Any]] = {}
    for key, id_key, count_key, sha_key, identity_field in (
        EXTERNAL_REPLAY_DOCUMENT_ROWS
    ):
        raw = replayed_documents[key]
        if (
            type(raw) is not bytes
            or len(raw) != context[count_key]
            or hashlib.sha256(raw).hexdigest() != context[sha_key]
        ):
            _fail("external replay document byte join changed")
        document = _canonical_object(raw, "external replay " + key)
        if document.get(identity_field) != context[id_key]:
            _fail("external replay document identity join changed")
        replayed[key] = document
    protocol_document = replayed["protocol"]
    authorization_document = replayed["authorization"]
    evidence_document = replayed["authorization_evidence"]
    materialization_document = replayed["prelaunch_materialization_terminal"]
    launch_attempt_document = replayed["current_launch_attempt"]
    measurement_launch_attempt_document = replayed["measurement_launch_attempt"]
    if not (
        protocol_document.get("cgroup_parent_fact") == cgroup_fact
        and protocol_document.get("runtime_capability_fact") == capability_fact
        and authorization_document.get("campaign_measurement_protocol_id")
        == context["protocol_id"]
        and authorization_document.get("campaign_measurement_execution_slot_id")
        == context["campaign_measurement_execution_slot_id"]
        and authorization_document.get("logical_occurrence_id")
        == context["logical_occurrence_id"]
        and authorization_document.get("execution_nonce")
        == context["execution_nonce"]
        and evidence_document.get("campaign_measurement_protocol_id")
        == context["protocol_id"]
        and evidence_document.get("execution_authorization_id")
        == context["authorization_id"]
        and evidence_document.get("campaign_measurement_execution_slot_id")
        == context["campaign_measurement_execution_slot_id"]
        and type(materialization_document.get("launch_manifest")) is dict
        and materialization_document["launch_manifest"].get("sha256")
        == context["prelaunch_launch_manifest_sha256"]
        and launch_attempt_document.get("target") == target
        and launch_attempt_document.get("materialization_terminal_id")
        == context["prelaunch_materialization_terminal_id"]
        and launch_attempt_document.get("launch_manifest_sha256")
        == context["prelaunch_launch_manifest_sha256"]
        and launch_attempt_document.get("launch_rule_id")
        == context["prelaunch_launch_rule_id"]
        and launch_attempt_document.get("production_systemd_service_invocation")
        == production_invocation
        and measurement_launch_attempt_document.get("target") == "measurement"
        and measurement_launch_attempt_document.get("materialization_terminal_id")
        == context["prelaunch_materialization_terminal_id"]
        and measurement_launch_attempt_document.get("launch_manifest_sha256")
        == context["prelaunch_launch_manifest_sha256"]
        and measurement_launch_attempt_document.get("launch_rule_id")
        == context["prelaunch_launch_rule_id"]
        and type(
            measurement_launch_attempt_document.get(
                "production_systemd_service_invocation"
            )
        ) is dict
        and measurement_launch_attempt_document[
            "production_systemd_service_invocation"
        ].get("target") == "measurement"
        and measurement_launch_attempt_document[
            "production_systemd_service_invocation"
        ].get("token") == PRODUCTION_TRANSIENT_SERVICE_ROWS["measurement"][0]
        and measurement_launch_attempt_document[
            "production_systemd_service_invocation"
        ].get("unit_name") == PRODUCTION_TRANSIENT_SERVICE_ROWS["measurement"][1]
        and (
            target != "measurement"
            or replayed_documents["measurement_launch_attempt"]
            == replayed_documents["current_launch_attempt"]
        )
    ):
        _fail("external authority or prelaunch causal join changed")
    return value


def _bounded_proc_read(relative_path: str, byte_cap: int = 1024 * 1024) -> str:
    descriptor = os.open(
        relative_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(64 * 1024, byte_cap + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > byte_cap:
                _fail("bounded pre-attempt proc observation exceeded its cap")
            chunks.append(chunk)
        return b"".join(chunks).decode("ascii")
    finally:
        os.close(descriptor)


def _fd_canonical_path(descriptor: int, label: str) -> str:
    value = os.readlink(f"/proc/self/fd/{descriptor}")
    path = PurePosixPath(value)
    if (
        not path.is_absolute()
        or path.as_posix() != value
        or "//" in value
        or value.endswith(" (deleted)")
        or any(part in {"", ".", ".."} for part in path.parts[1:])
    ):
        _fail(f"{label} descriptor no longer names one canonical directory")
    return value


def _mountinfo_cgroup2_row(mount_point: str) -> tuple[str, ...]:
    matched: tuple[str, ...] | None = None
    for line in _bounded_proc_read("/proc/self/mountinfo").splitlines():
        left, separator, right = line.partition(" - ")
        left_fields = left.split()
        right_fields = right.split()
        if (
            separator
            and len(left_fields) >= 6
            and len(right_fields) >= 3
            and left_fields[4] == mount_point
            and right_fields[0] == "cgroup2"
        ):
            values = {
                *left_fields[5].split(","),
                *right_fields[2].split(","),
            }
            matched = tuple(sorted(value for value in values if value))
            break
    if matched is None:
        _fail("preopened cgroup2 mount is absent from bounded mountinfo")
    return matched


def reobserve_cgroup_parent_fact_from_inherited_fds_v180r12r4(
    parent_fd: int = DELEGATED_CGROUP_PARENT_FD,
    mount_fd: int = CGROUP2_MOUNT_FD,
) -> dict[str, Any]:
    """Read-only replay of the bound cgroup parent fact from original OFDs."""

    if parent_fd != DELEGATED_CGROUP_PARENT_FD or mount_fd != CGROUP2_MOUNT_FD:
        _fail("external cgroup descriptor numbers differ from the frozen map")
    parent_flags = fcntl.fcntl(parent_fd, fcntl.F_GETFL)
    mount_flags = fcntl.fcntl(mount_fd, fcntl.F_GETFL)
    parent_metadata = os.fstat(parent_fd)
    mount_metadata = os.fstat(mount_fd)
    if (
        not stat.S_ISDIR(parent_metadata.st_mode)
        or not stat.S_ISDIR(mount_metadata.st_mode)
        or parent_flags & os.O_ACCMODE != os.O_RDONLY
        or mount_flags & os.O_PATH != os.O_PATH
        or os.get_inheritable(parent_fd)
        or os.get_inheritable(mount_fd)
        or LinuxCgroupV2V180R12R4._fstatfs_type(parent_fd)
        != CGROUP2_SUPER_MAGIC
        or LinuxCgroupV2V180R12R4._fstatfs_type(mount_fd)
        != CGROUP2_SUPER_MAGIC
    ):
        _fail("preopened external cgroup descriptors changed before ATTEMPT")
    mount_point = _fd_canonical_path(mount_fd, "cgroup2 mount")
    parent_path = _fd_canonical_path(parent_fd, "delegated cgroup parent")
    try:
        PurePosixPath(parent_path).relative_to(PurePosixPath(mount_point))
    except ValueError as error:
        raise V180R12R4RuntimeError(
            "delegated parent descriptor is outside its cgroup2 mount"
        ) from error

    def read_control(name: str) -> str:
        return LinuxCgroupV2V180R12R4._read_at(parent_fd, name)

    def present(name: str) -> bool:
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        return stat.S_ISREG(metadata.st_mode)

    document = {
        "schema": "acfqp.v180r12r4_cgroup_parent_fact.v1",
        "mount_point": mount_point,
        "mount_fstype": "cgroup2",
        "mount_device": mount_metadata.st_dev,
        "mount_inode": mount_metadata.st_ino,
        "mount_options": list(_mountinfo_cgroup2_row(mount_point)),
        "parent_path": parent_path,
        "parent_device": parent_metadata.st_dev,
        "parent_inode": parent_metadata.st_ino,
        "owner_uid": parent_metadata.st_uid,
        "owner_gid": parent_metadata.st_gid,
        "mode": stat.S_IMODE(parent_metadata.st_mode),
        "controllers": sorted(read_control("cgroup.controllers").split()),
        "subtree_control": sorted(read_control("cgroup.subtree_control").split()),
        "cgroup_type": read_control("cgroup.type").strip(),
        "cgroup_namespace_inode": os.stat("/proc/self/ns/cgroup").st_ino,
        "cgroup_events_present": present("cgroup.events"),
        "memory_events_present": present("memory.events"),
        "pids_events_present": present("pids.events"),
        # cgroup.kill is write-only on normal delegated cgroup2 trees.  Its
        # lstat presence is authoritative; no read is attempted.
        "cgroup_kill_present": present("cgroup.kill"),
        "cgroup_procs_present": present("cgroup.procs"),
        "memory_peak_present": present("memory.peak"),
        "pids_peak_present": present("pids.peak"),
        "self_membership": _proc_cgroup(os.getpid()),
    }
    return protocol.validate_cgroup_parent_fact_v180r12r4(document)


def _probe_linux_syscall_errno(number: int, *arguments: Any) -> int:
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    ctypes.set_errno(0)
    result = libc.syscall(number, *arguments)
    if result >= 0:
        # These probes are deliberately invalid and must never create a child,
        # signal a process, or replace the image.
        _fail("read-only invalid syscall probe unexpectedly succeeded")
    return ctypes.get_errno()


def reobserve_runtime_capability_fact_v180r12r4() -> dict[str, Any]:
    """Repeat the frozen no-child/no-output Linux capability probes."""

    machine = os.uname().machine
    if machine != "x86_64":
        _fail("V180r12r4 syscall probe numbers freeze only x86_64")
    clone3_errno = _probe_linux_syscall_errno(435, ctypes.c_void_p(), 0)
    pidfd_signal_errno = _probe_linux_syscall_errno(424, -1, 0, 0, 0)
    argv = (ctypes.c_char_p * 1)(None)
    envp = (ctypes.c_char_p * 1)(None)
    execveat_errno = _probe_linux_syscall_errno(
        322, -1, ctypes.c_char_p(b""), argv, envp, 0x1000
    )
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    ctypes.set_errno(0)
    landlock_abi = int(libc.syscall(444, ctypes.c_void_p(), 0, 1))
    if landlock_abi <= 0:
        _fail("Landlock ABI observation failed")
    cap_eff: int | None = None
    for line in _bounded_proc_read("/proc/self/status").splitlines():
        if line.startswith("CapEff:"):
            cap_eff = int(line.split(":", 1)[1].strip(), 16)
            break
    if cap_eff is None:
        _fail("effective capability mask is absent")
    document = {
        "schema": "acfqp.v180r12r4_runtime_capability_fact.v1",
        "machine_architecture": machine,
        "single_threaded": _single_threaded(),
        "clone3_probe_errno": clone3_errno,
        "clone3_syscall_recognized": clone3_errno != errno.ENOSYS,
        "pidfd_send_signal_probe_errno": pidfd_signal_errno,
        "pidfd_send_signal_recognized": pidfd_signal_errno != errno.ENOSYS,
        "execveat_probe_errno": execveat_errno,
        "execveat_recognized": execveat_errno != errno.ENOSYS,
        "pidfd_wait_present": hasattr(os, "P_PIDFD") and hasattr(os, "waitid"),
        "landlock_abi": landlock_abi,
        "uid": os.getuid(),
        "gid": os.getgid(),
        "effective_capability_mask": cap_eff,
        "admitted": (
            clone3_errno != errno.ENOSYS
            and pidfd_signal_errno != errno.ENOSYS
            and execveat_errno != errno.ENOSYS
            and hasattr(os, "P_PIDFD")
            and hasattr(os, "waitid")
            and landlock_abi > 0
            and cap_eff == 0
            and _single_threaded()
        ),
    }
    return protocol.validate_runtime_capability_fact_v180r12r4(document)


def _validate_socket_buffer_capability_fact_v180r12r4(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one complete 13-field socket-capability observation."""

    document = _thaw_json_value(value)
    if (
        type(document) is not dict
        or set(document) != set(SOCKET_BUFFER_CAPABILITY_FACT_FIELDS)
    ):
        _fail("socket-buffer capability fact field set changed")
    string_fields = (
        "schema", "probe_boundary", "socket_family", "socket_type",
    )
    numeric_fields = (
        "endpoint_count", "buffer_request_bytes", "effective_min_bytes",
        *SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS,
    )
    if (
        any(
            type(document.get(field)) is not str or not document[field]
            for field in string_fields
        )
        or any(
            type(document.get(field)) is not int or document[field] <= 0
            for field in numeric_fields
        )
    ):
        _fail("socket-buffer capability fact types or values changed")
    return {
        field: document[field]
        for field in SOCKET_BUFFER_CAPABILITY_FACT_FIELDS
    }


def expected_socket_buffer_capability_fact_v180r12r4() -> dict[str, Any]:
    """Return the complete preregistered exact/minimum socket fact."""

    return _validate_socket_buffer_capability_fact_v180r12r4(
        {
            **SOCKET_BUFFER_CAPABILITY_EXPECTED_EXACT_PROPERTIES,
            **SOCKET_BUFFER_CAPABILITY_EXPECTED_MINIMUM_PROPERTIES,
        }
    )


def _read_positive_socket_sysctl_v180r12r4(path: str) -> int:
    raw = _bounded_proc_read(path, byte_cap=64)
    rendered = raw.strip()
    if not rendered.isdecimal():
        _fail("socket-buffer sysctl observation is not one positive integer")
    value = int(rendered, 10)
    if type(value) is not int or value <= 0:
        _fail("socket-buffer sysctl observation is not one positive integer")
    return value


def reobserve_socket_buffer_capability_fact_v180r12r4() -> dict[str, Any]:
    """Probe seqpacket capacity without retaining sockets or campaign effects."""

    wmem_max = _read_positive_socket_sysctl_v180r12r4(
        "/proc/sys/net/core/wmem_max"
    )
    rmem_max = _read_positive_socket_sysctl_v180r12r4(
        "/proc/sys/net/core/rmem_max"
    )
    endpoint_0, endpoint_1 = socket.socketpair(
        socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC
    )
    try:
        observations: list[tuple[int, int]] = []
        for endpoint in (endpoint_0, endpoint_1):
            endpoint.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_SNDBUF,
                SOCK_SEQPACKET_BUFFER_REQUEST_BYTES,
            )
            endpoint.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_RCVBUF,
                SOCK_SEQPACKET_BUFFER_REQUEST_BYTES,
            )
            observations.append(
                (
                    endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF),
                    endpoint.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF),
                )
            )
        document = {
            **SOCKET_BUFFER_CAPABILITY_EXPECTED_EXACT_PROPERTIES,
            "net_core_wmem_max_bytes": wmem_max,
            "net_core_rmem_max_bytes": rmem_max,
            "endpoint_0_so_sndbuf_bytes": observations[0][0],
            "endpoint_0_so_rcvbuf_bytes": observations[0][1],
            "endpoint_1_so_sndbuf_bytes": observations[1][0],
            "endpoint_1_so_rcvbuf_bytes": observations[1][1],
        }
        return _validate_socket_buffer_capability_fact_v180r12r4(document)
    finally:
        try:
            endpoint_0.close()
        finally:
            endpoint_1.close()


def _read_cgroup_control_from_fd_v180r12r4(
    directory_fd: int, name: str
) -> str:
    if name not in {"cgroup.procs", "cgroup.events"}:
        _fail("production placement cgroup control name changed")
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
        dir_fd=directory_fd,
    )
    try:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(4096, 64 * 1024 + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > 64 * 1024:
                _fail("production placement cgroup control exceeded its cap")
        return b"".join(chunks).decode("ascii")
    finally:
        os.close(descriptor)


def _production_direct_child_pid_evidence_v180r12r4(
    placement_t1: Mapping[str, Any],
    source_cgroup_pids: tuple[int, ...],
    *,
    self_pid: int,
    parent_pid: int,
) -> dict[str, Any]:
    """Bind the bootstrap child directly to its live service-entry parent."""

    t1_pid = placement_t1.get("self_pid")
    if not (
        type(t1_pid) is int
        and t1_pid > 0
        and placement_t1.get("self_pid_in_source_cgroup_procs") is True
        and type(self_pid) is int
        and self_pid > 0
        and type(parent_pid) is int
        and parent_pid > 0
        and self_pid != t1_pid
        and parent_pid == t1_pid
        and self_pid in source_cgroup_pids
        and parent_pid in source_cgroup_pids
    ):
        _fail("T1 service-entry/T2 bootstrap direct-child PID relation changed")
    return {
        "self_pid": self_pid,
        "self_pid_in_source_cgroup_procs": True,
        "parent_pid": parent_pid,
        "parent_pid_in_source_cgroup_procs": True,
    }


def _revalidate_production_source_placement_v180r12r4(
    context: Mapping[str, Any],
    *,
    schema: str,
    boundary: str,
    require_progress_absent: bool,
) -> dict[str, Any]:
    """Revalidate the original service OFD and app.slice delegation without writes."""

    if context.get("target") != "measurement":
        _fail("production source placement revalidation target changed")
    token, unit_name = PRODUCTION_TRANSIENT_SERVICE_ROWS["measurement"]
    t1 = _thaw_json_value(context["production_runtime_placement_t1"])
    cgroup_fact = _thaw_json_value(context["cgroup_parent_fact"])
    parent_metadata = os.fstat(DELEGATED_CGROUP_PARENT_FD)
    mount_metadata = os.fstat(CGROUP2_MOUNT_FD)
    service_metadata = os.fstat(SOURCE_SYSTEMD_SERVICE_FD)
    parent_flags = fcntl.fcntl(DELEGATED_CGROUP_PARENT_FD, fcntl.F_GETFL)
    mount_flags = fcntl.fcntl(CGROUP2_MOUNT_FD, fcntl.F_GETFL)
    service_flags = fcntl.fcntl(SOURCE_SYSTEMD_SERVICE_FD, fcntl.F_GETFL)
    parent_path = _fd_canonical_path(
        DELEGATED_CGROUP_PARENT_FD, "delegated cgroup parent"
    )
    mount_path = _fd_canonical_path(CGROUP2_MOUNT_FD, "cgroup2 mount")
    service_path = _fd_canonical_path(
        SOURCE_SYSTEMD_SERVICE_FD, "source systemd service"
    )
    expected_service_path = str(PurePosixPath(parent_path) / unit_name)
    parent_relative = PurePosixPath(parent_path).relative_to(
        PurePosixPath(mount_path)
    )
    expected_membership = "0::/" + (parent_relative / unit_name).as_posix()
    self_pid = os.getpid()
    parent_pid = os.getppid()
    membership = _proc_cgroup(self_pid)
    pids = tuple(
        int(row)
        for row in _read_cgroup_control_from_fd_v180r12r4(
            SOURCE_SYSTEMD_SERVICE_FD, "cgroup.procs"
        ).splitlines()
        if row
    )
    pid_evidence = _production_direct_child_pid_evidence_v180r12r4(
        t1,
        pids,
        self_pid=self_pid,
        parent_pid=parent_pid,
    )
    writable = os.open(
        "cgroup.procs",
        os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
        dir_fd=DELEGATED_CGROUP_PARENT_FD,
    )
    try:
        writable_metadata = os.fstat(writable)
        writable_flags = fcntl.fcntl(writable, fcntl.F_GETFL)
        parent_writable = (
            stat.S_ISREG(writable_metadata.st_mode)
            and writable_flags & os.O_ACCMODE == os.O_WRONLY
        )
    finally:
        os.close(writable)
    root_name = "v180r12r4-" + context["campaign_attempt_id"]
    try:
        root_metadata = os.stat(
            root_name,
            dir_fd=DELEGATED_CGROUP_PARENT_FD,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        root_state = "ABSENT"
    else:
        root_state = (
            "PRESENT" if stat.S_ISDIR(root_metadata.st_mode) else "LINKED_OR_NONDIR"
        )
    progress_present = tuple(
        path
        for path, _kind in FAILURE_ARTIFACT_FIXED_PATH_KINDS
        if os.path.lexists(Path(context["repository_root"]) / path)
    )
    t1_service = t1.get("source_service_fd_fact")
    if not (
        schema
        in {
            PRODUCTION_RUNTIME_PLACEMENT_T2_SCHEMA,
            PRODUCTION_RUNTIME_PLACEMENT_T3_SCHEMA,
        }
        and boundary
        in {
            "T2_BEFORE_SCIENTIFIC_ATTEMPT_O_EXCL",
            "T3_BEFORE_GETRANDOM",
            "T3_IMMEDIATELY_BEFORE_CLONE3",
        }
        and type(t1_service) is dict
        and token == t1.get("token")
        and unit_name == t1.get("unit_name")
        and parent_path == cgroup_fact["parent_path"]
        and mount_path == cgroup_fact["mount_point"]
        and service_path == expected_service_path
        and PurePosixPath(parent_path).name == "app.slice"
        and membership == expected_membership
        and parent_flags & os.O_ACCMODE == os.O_RDONLY
        and mount_flags & os.O_PATH == os.O_PATH
        and service_flags & os.O_ACCMODE == os.O_RDONLY
        and not os.get_inheritable(DELEGATED_CGROUP_PARENT_FD)
        and not os.get_inheritable(CGROUP2_MOUNT_FD)
        and not os.get_inheritable(SOURCE_SYSTEMD_SERVICE_FD)
        and stat.S_ISDIR(parent_metadata.st_mode)
        and stat.S_ISDIR(mount_metadata.st_mode)
        and stat.S_ISDIR(service_metadata.st_mode)
        and parent_metadata.st_dev == cgroup_fact["parent_device"]
        and parent_metadata.st_ino == cgroup_fact["parent_inode"]
        and mount_metadata.st_dev == cgroup_fact["mount_device"]
        and mount_metadata.st_ino == cgroup_fact["mount_inode"]
        and service_metadata.st_dev == t1_service.get("device")
        and service_metadata.st_ino == t1_service.get("inode")
        and LinuxCgroupV2V180R12R4._fstatfs_type(DELEGATED_CGROUP_PARENT_FD)
        == CGROUP2_SUPER_MAGIC
        and LinuxCgroupV2V180R12R4._fstatfs_type(CGROUP2_MOUNT_FD)
        == CGROUP2_SUPER_MAGIC
        and LinuxCgroupV2V180R12R4._fstatfs_type(SOURCE_SYSTEMD_SERVICE_FD)
        == CGROUP2_SUPER_MAGIC
        and os.stat("/proc/self/ns/cgroup").st_ino
        == t1.get("cgroup_namespace_inode")
        and parent_writable
        and (not require_progress_absent or not progress_present)
        and (
            not require_progress_absent
            or root_state == "ABSENT"
        )
    ):
        _fail(f"{boundary} production source placement changed")
    document = {
        "schema": schema,
        "boundary": boundary,
        "target": "measurement",
        "token": token,
        "unit_name": unit_name,
        "source_membership": membership,
        "expected_source_membership": expected_membership,
        **pid_evidence,
        "source_service_fd": SOURCE_SYSTEMD_SERVICE_FD,
        "source_service_device": service_metadata.st_dev,
        "source_service_inode": service_metadata.st_ino,
        "cgroup_namespace_inode": os.stat("/proc/self/ns/cgroup").st_ino,
        "nearest_common_ancestor_path": parent_path,
        "nearest_common_ancestor_is_app_slice": True,
        "parent_cgroup_procs_o_wronly_openable": parent_writable,
        "planned_measurement_root_state": root_state,
        "scientific_progress_present_paths": list(progress_present),
        "scientific_progress_absent": not progress_present,
    }
    if (
        schema == PRODUCTION_RUNTIME_PLACEMENT_T2_SCHEMA
        and tuple(document) != protocol.PRODUCTION_RUNTIME_PLACEMENT_T2_FIELDS
    ):
        _fail(f"{boundary} production placement field order changed")
    return document


def _production_runtime_placement_t3_checkpoint_v180r12r4(
    context: Mapping[str, Any],
    tree: "CgroupTreeV180R12R4",
    *,
    boundary: str,
    fault_injector: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Revalidate source service plus exact empty destination topology."""

    if boundary not in {
        "T3_BEFORE_GETRANDOM",
        "T3_IMMEDIATELY_BEFORE_CLONE3",
    }:
        _fail("T3 checkpoint boundary changed")

    def observe() -> dict[str, Any]:
        source = _revalidate_production_source_placement_v180r12r4(
            context,
            schema=PRODUCTION_RUNTIME_PLACEMENT_T3_SCHEMA,
            boundary=boundary,
            require_progress_absent=False,
        )
        if not (
            type(tree) is CgroupTreeV180R12R4
            and tree.parent_fd == DELEGATED_CGROUP_PARENT_FD
            and tree.mount_fd == CGROUP2_MOUNT_FD
            and tree.source_service_fd == SOURCE_SYSTEMD_SERVICE_FD
        ):
            _fail("T3 cgroup tree external-FD ownership changed")
        topology = tree.topology_receipt
        node_rows = (
            (topology.measurement_root, tree.root_fd),
            (topology.supervisor_leaf, tree.supervisor_fd),
            (topology.worker_leaf, tree.worker_fd),
        )
        for node, descriptor in node_rows:
            metadata = os.fstat(descriptor)
            if not (
                metadata.st_dev == node.device
                and metadata.st_ino == node.inode
                and stat.S_ISDIR(metadata.st_mode)
                and not os.get_inheritable(descriptor)
                and LinuxCgroupV2V180R12R4._fstatfs_type(descriptor)
                == CGROUP2_SUPER_MAGIC
            ):
                _fail("T3 destination cgroup OFD identity changed")
        LinuxCgroupV2V180R12R4._validate_programmed_limits(
            tree.root_fd, tree.supervisor_fd, tree.worker_fd
        )

        def empty(descriptor: int) -> bool:
            events = dict(
                line.split(" ", 1)
                for line in LinuxCgroupV2V180R12R4._read_at(
                    descriptor, "cgroup.events"
                ).splitlines()
                if line
            )
            return (
                events.get("populated") == "0"
                and LinuxCgroupV2V180R12R4._read_at(
                    descriptor, "cgroup.procs"
                )
                == ""
            )

        root_empty = empty(tree.root_fd)
        supervisor_empty = empty(tree.supervisor_fd)
        worker_empty = empty(tree.worker_fd)
        target_metadata = os.fstat(tree.supervisor_fd)
        if not (root_empty and supervisor_empty and worker_empty):
            _fail("T3 destination topology is not empty before supervisor birth")
        document = {
            **source,
            "measurement_root_device": topology.measurement_root.device,
            "measurement_root_inode": topology.measurement_root.inode,
            "supervisor_leaf_device": topology.supervisor_leaf.device,
            "supervisor_leaf_inode": topology.supervisor_leaf.inode,
            "worker_leaf_device": topology.worker_leaf.device,
            "worker_leaf_inode": topology.worker_leaf.inode,
            "target_cgroup_role": "SUPERVISOR",
            "target_cgroup_fd": tree.supervisor_fd,
            "target_cgroup_device": target_metadata.st_dev,
            "target_cgroup_inode": target_metadata.st_ino,
            "target_cgroup_path": topology.supervisor_leaf.path,
            "target_membership_path": topology.supervisor_leaf.membership_path,
            "root_empty_before_birth": root_empty,
            "supervisor_leaf_empty_before_birth": supervisor_empty,
            "worker_leaf_empty_before_birth": worker_empty,
            "programmed_limits_revalidated": True,
        }
        if tuple(document) != protocol.PRODUCTION_RUNTIME_PLACEMENT_T3_CHECKPOINT_FIELDS:
            _fail("T3 checkpoint field order changed")
        return document

    return _launch_boundary_v180r12r4(
        boundary,
        observe,
        fault_injector=fault_injector,
    )


def _complete_t3_checkpoint_conformance_v180r12r4(
    topology_receipt: runtime.MeasurementCgroupTopologyReceiptV180R12R4,
    *,
    before_getrandom: Mapping[str, Any],
    immediately_before_clone3: Mapping[str, Any],
) -> dict[str, Any]:
    """Return one conformant outer T3 receipt or block before clone3."""

    diagnostic = (
        runtime.build_t3_checkpoint_conformance_diagnostic_v180r12r4r4(
            placement_t1=topology_receipt.production_runtime_placement_t1,
            placement_t2=topology_receipt.production_runtime_placement_t2,
            parent_snapshot=topology_receipt.cgroup_parent_fact,
            measurement_snapshot=topology_receipt.to_document(),
            before_getrandom=before_getrandom,
            immediately_before_clone3=immediately_before_clone3,
        )
    )
    if diagnostic["full_conformance"] is not True:
        primary = runtime.CgroupTopologyConformanceErrorV180R12R4R4(
            diagnostic
        )
        _annotate_launch_primary_v180r12r4(
            primary, "T3_IMMEDIATELY_BEFORE_CLONE3"
        )
        raise primary
    snapshot = diagnostic["property_snapshots"][
        "production_runtime_placement_t3"
    ]
    placement = {
        name: snapshot[name]
        for name in protocol.PRODUCTION_RUNTIME_PLACEMENT_T3_FIELDS
    }
    if tuple(placement) != protocol.PRODUCTION_RUNTIME_PLACEMENT_T3_FIELDS:
        _fail("T3 placement receipt field order changed")
    return placement


def reobserve_precompiled_source_bundle_v180r12r4(
    context: Mapping[str, Any],
    descriptor: int = PRECOMPILED_SOURCE_BUNDLE_FD,
) -> tuple[str, tuple[dict[str, Any], ...]]:
    """Rebuild the native-zero summary from the original sealed FD240 bytes."""

    if descriptor != PRECOMPILED_SOURCE_BUNDLE_FD:
        _fail("precompiled bundle descriptor number changed")
    metadata = os.fstat(descriptor)
    flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 0
        or metadata.st_size <= 0
        or metadata.st_size > 128 * 1024 * 1024
        or stat.S_IMODE(metadata.st_mode) != 0o400
        or flags & os.O_ACCMODE != os.O_RDONLY
        or fcntl.fcntl(descriptor, fcntl.F_GET_SEALS)
        != REQUIRED_MEMFD_SEAL_MASK
        or os.get_inheritable(descriptor)
    ):
        _fail("precompiled source bundle FD changed before campaign ATTEMPT")
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    remaining = metadata.st_size
    while remaining:
        chunk = os.read(descriptor, min(1024 * 1024, remaining))
        if not chunk:
            _fail("precompiled source bundle ended before its exact size")
        chunks.append(chunk)
        remaining -= len(chunk)
    if os.read(descriptor, 1):
        _fail("precompiled source bundle grew during replay")
    after = os.fstat(descriptor)
    os.lseek(descriptor, 0, os.SEEK_SET)
    if any(
        getattr(metadata, name) != getattr(after, name)
        for name in ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size")
    ):
        _fail("precompiled source bundle identity drifted during replay")
    raw = b"".join(chunks)
    digest = hashlib.sha256(raw).hexdigest()
    bundle = _canonical_object(raw, "precompiled source bundle")
    if set(bundle) != {
        "schema", "manifest_sha256", "c_pre_commit_id", "repository_root",
        "c_pre_root", "manifest_path", "measured_target_contract",
        "source_records", "target_records",
    }:
        _fail("precompiled source bundle field set changed")
    if not (
        bundle["schema"] == PRECOMPILED_SOURCE_BUNDLE_SCHEMA
        and bundle["manifest_sha256"]
        == context["prelaunch_launch_manifest_sha256"]
        and bundle["c_pre_commit_id"] == context["prereg_commit_id"]
        and bundle["repository_root"] == context["repository_root"]
        and bundle["c_pre_root"] == context["c_pre_root"]
        and bundle["manifest_path"]
        == f"{context['c_pre_root']}/launch_manifest.json"
        and bundle["measured_target_contract"] == list(MEASURED_TARGETS)
        and type(bundle["source_records"]) is list
        and type(bundle["target_records"]) is list
    ):
        _fail("precompiled source bundle provenance changed")

    source_fields = {
        "module", "source_path", "is_package", "marshal_byte_count",
        "marshal_sha256", "marshal_hex",
    }
    target_fields = {
        "target", "source_path", "marshal_byte_count", "marshal_sha256",
        "marshal_hex",
    }

    def validate_marshaled(row: Mapping[str, Any], label: str) -> None:
        count = row.get("marshal_byte_count")
        supplied_digest = row.get("marshal_sha256")
        encoded = row.get("marshal_hex")
        if (
            type(count) is not int
            or count <= 0
            or type(encoded) is not str
            or encoded != encoded.lower()
        ):
            _fail(label + " marshal fields changed")
        _require_content_id(supplied_digest, label + " marshal SHA-256")
        try:
            marshalled = bytes.fromhex(encoded)
            code = marshal.loads(marshalled)
        except (ValueError, TypeError, EOFError) as error:
            raise V180R12R4RuntimeError(label + " marshal bytes changed") from error
        if (
            len(marshalled) != count
            or hashlib.sha256(marshalled).hexdigest() != supplied_digest
            or not isinstance(code, types.CodeType)
        ):
            _fail(label + " marshal identity changed")

    repository_root = Path(context["repository_root"])
    application_rows: list[dict[str, Any]] = []
    source_names: list[str] = []
    for index, row in enumerate(bundle["source_records"]):
        if type(row) is not dict or set(row) != source_fields:
            _fail("precompiled source record field set changed")
        validate_marshaled(row, f"precompiled source {index}")
        module = row["module"]
        source_path = Path(row["source_path"])
        if (
            type(module) is not str
            or not module
            or any(not part.isidentifier() for part in module.split("."))
            or type(row["is_package"]) is not bool
            or not source_path.is_absolute()
        ):
            _fail("precompiled source module binding changed")
        source_names.append(module)
        if module == "acfqp" or module.startswith("acfqp."):
            try:
                relative = source_path.relative_to(repository_root).as_posix()
            except ValueError as error:
                raise V180R12R4RuntimeError(
                    "precompiled application source escaped repository root"
                ) from error
            if str(repository_root / relative) != str(source_path):
                _fail("precompiled application source normalization changed")
            application_rows.append(
                {
                    "source_kind": "MODULE",
                    "name": module,
                    "source_path": relative,
                    "is_package": row["is_package"],
                    "marshal_byte_count": row["marshal_byte_count"],
                    "marshal_sha256": row["marshal_sha256"],
                }
            )
    if source_names != sorted(set(source_names)):
        _fail("precompiled source module order or uniqueness changed")

    target_names: list[str] = []
    for index, row in enumerate(bundle["target_records"]):
        if type(row) is not dict or set(row) != target_fields:
            _fail("precompiled target record field set changed")
        validate_marshaled(row, f"precompiled target {index}")
        name = row["target"]
        relative = dict(ledger.PRECOMPILED_TARGET_SOURCE_PATHS).get(name)
        if relative is None or row["source_path"] != str(repository_root / relative):
            _fail("precompiled measured target source binding changed")
        target_names.append(name)
        application_rows.append(
            {
                "source_kind": "TARGET",
                "name": name,
                "source_path": relative,
                "is_package": False,
                "marshal_byte_count": row["marshal_byte_count"],
                "marshal_sha256": row["marshal_sha256"],
            }
        )
    if tuple(target_names) != MEASURED_TARGETS:
        _fail("precompiled measured target order changed")
    application_rows.sort(key=lambda row: (row["source_kind"], row["name"]))
    rows = _validate_native_zero_precompiled_rows_v180r12r4(application_rows)
    if (
        digest != context["precompiled_source_bundle_sha256"]
        or list(rows)
        != _thaw_json_value(context["native_zero_precompiled_source_rows"])
    ):
        _fail("precompiled source bundle digest or normalized row join changed")
    return digest, rows


def pre_attempt_host_conformance_mismatch_rows_v180r12r4(
    *,
    expected_cgroup_parent_fact: Mapping[str, Any],
    observed_cgroup_parent_fact: Mapping[str, Any],
    expected_runtime_capability_fact: Mapping[str, Any],
    observed_runtime_capability_fact: Mapping[str, Any],
    expected_socket_buffer_capability: Mapping[str, Any],
    observed_socket_buffer_capability: Mapping[str, Any],
) -> tuple[tuple[str, str, Any, Any], ...]:
    """Compare complete host facts under exact and minimum predicates."""

    expected_parent = protocol.validate_cgroup_parent_fact_v180r12r4(
        _thaw_json_value(expected_cgroup_parent_fact)
    )
    observed_parent = protocol.validate_cgroup_parent_fact_v180r12r4(
        _thaw_json_value(observed_cgroup_parent_fact)
    )
    expected_runtime = protocol.validate_runtime_capability_fact_v180r12r4(
        _thaw_json_value(expected_runtime_capability_fact)
    )
    observed_runtime = protocol.validate_runtime_capability_fact_v180r12r4(
        _thaw_json_value(observed_runtime_capability_fact)
    )
    expected_socket = _validate_socket_buffer_capability_fact_v180r12r4(
        expected_socket_buffer_capability
    )
    observed_socket = _validate_socket_buffer_capability_fact_v180r12r4(
        observed_socket_buffer_capability
    )
    rows = [
        ("cgroup_parent_fact", field, expected_parent[field], observed_parent[field])
        for field in protocol.CGROUP_PARENT_FACT_FIELDS
        if field != "self_membership"
        and _canonical(expected_parent[field]) != _canonical(observed_parent[field])
    ]
    rows.extend(
        (
            "runtime_capability_fact",
            field,
            expected_runtime[field],
            observed_runtime[field],
        )
        for field in protocol.RUNTIME_CAPABILITY_FACT_FIELDS
        if _canonical(expected_runtime[field]) != _canonical(observed_runtime[field])
    )
    rows.extend(
        (
            SOCKET_BUFFER_CAPABILITY_MISMATCH_SCOPE,
            field,
            expected_socket[field],
            observed_socket[field],
        )
        for field in SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS
        if _canonical(expected_socket[field]) != _canonical(observed_socket[field])
    )
    rows.extend(
        (
            SOCKET_BUFFER_CAPABILITY_MISMATCH_SCOPE,
            field,
            expected_socket[field],
            observed_socket[field],
        )
        for field in SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS
        if observed_socket[field] < expected_socket[field]
    )
    return tuple(sorted(rows, key=lambda row: (row[0], row[1])))


def _pre_attempt_host_conformance_cause_v180r12r4(
    mismatches: Sequence[tuple[str, str, Any, Any]],
) -> str | None:
    fact_kinds = {row[0] for row in mismatches}
    cgroup_drift = "cgroup_parent_fact" in fact_kinds
    runtime_drift = "runtime_capability_fact" in fact_kinds
    socket_insufficient = SOCKET_BUFFER_CAPABILITY_MISMATCH_SCOPE in fact_kinds
    if not (cgroup_drift or runtime_drift or socket_insufficient):
        return None
    if cgroup_drift and runtime_drift:
        cause = "CGROUP_PARENT_AND_RUNTIME_CAPABILITY_FACT_DRIFT"
    elif cgroup_drift:
        cause = "CGROUP_PARENT_FACT_DRIFT"
    elif runtime_drift:
        cause = "RUNTIME_CAPABILITY_FACT_DRIFT"
    else:
        cause = ""
    if socket_insufficient:
        return (
            cause + "_AND_" if cause else ""
        ) + SOCKET_BUFFER_CAPABILITY_INSUFFICIENT_CAUSE
    return cause


def write_pre_attempt_host_conformance_v180r12r4(
    store: "DurableStoreV180R12R4",
    *,
    campaign_attempt_id: str,
    expected_cgroup_parent_fact: Mapping[str, Any],
    observed_cgroup_parent_fact: Mapping[str, Any],
    expected_runtime_capability_fact: Mapping[str, Any],
    observed_runtime_capability_fact: Mapping[str, Any],
    expected_socket_buffer_capability: Mapping[str, Any],
    observed_socket_buffer_capability: Mapping[str, Any],
) -> dict[str, Any]:
    """Durably retain the complete pre-ATTEMPT host comparison once."""

    if type(store) is not DurableStoreV180R12R4:
        _fail("pre-attempt host conformance requires the durable repository store")
    _require_content_id(campaign_attempt_id, "campaign attempt ID")
    expected_parent = protocol.validate_cgroup_parent_fact_v180r12r4(
        _thaw_json_value(expected_cgroup_parent_fact)
    )
    observed_parent = protocol.validate_cgroup_parent_fact_v180r12r4(
        _thaw_json_value(observed_cgroup_parent_fact)
    )
    expected_runtime = protocol.validate_runtime_capability_fact_v180r12r4(
        _thaw_json_value(expected_runtime_capability_fact)
    )
    observed_runtime = protocol.validate_runtime_capability_fact_v180r12r4(
        _thaw_json_value(observed_runtime_capability_fact)
    )
    expected_socket = _validate_socket_buffer_capability_fact_v180r12r4(
        expected_socket_buffer_capability
    )
    observed_socket = _validate_socket_buffer_capability_fact_v180r12r4(
        observed_socket_buffer_capability
    )
    mismatches = pre_attempt_host_conformance_mismatch_rows_v180r12r4(
        expected_cgroup_parent_fact=expected_parent,
        observed_cgroup_parent_fact=observed_parent,
        expected_runtime_capability_fact=expected_runtime,
        observed_runtime_capability_fact=observed_runtime,
        expected_socket_buffer_capability=expected_socket,
        observed_socket_buffer_capability=observed_socket,
    )
    cause = _pre_attempt_host_conformance_cause_v180r12r4(mismatches)
    document = {
        "schema": PRE_ATTEMPT_HOST_CONFORMANCE_SCHEMA,
        "phase": "PRE_CAMPAIGN_ATTEMPT_HOST_CONFORMANCE",
        "campaign_attempt_id": campaign_attempt_id,
        "expected": {
            "cgroup_parent_fact": expected_parent,
            "runtime_capability_fact": expected_runtime,
            "socket_buffer_capability": expected_socket,
        },
        "observed": {
            "cgroup_parent_fact": observed_parent,
            "runtime_capability_fact": observed_runtime,
            "socket_buffer_capability": observed_socket,
        },
        "cgroup_parent_compared_fields": [
            field
            for field in protocol.CGROUP_PARENT_FACT_FIELDS
            if field != "self_membership"
        ],
        "cgroup_parent_excluded_fields": ["self_membership"],
        "runtime_capability_compared_fields": list(
            protocol.RUNTIME_CAPABILITY_FACT_FIELDS
        ),
        "socket_buffer_capability_exact_fields": list(
            SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS
        ),
        "socket_buffer_capability_at_least_fields": list(
            SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS
        ),
        "mismatch_rows": [list(row) for row in mismatches],
        "mismatch_count": len(mismatches),
        "cause": cause,
        "full_host_conformance": not mismatches,
        "working_tree_source_conformance_joined": False,
        "production_unit_ownership_t1_joined": False,
        "campaign_event_or_counter_record_issued": False,
        "campaign_attempt_created": False,
    }
    raw = _canonical(document)
    store.write_once_verified(
        PRE_ATTEMPT_HOST_CONFORMANCE_RELATIVE_PATH,
        raw,
        byte_cap=PRE_ATTEMPT_HOST_CONFORMANCE_BYTE_CAP,
        mode=0o400,
    )
    return document


def revalidate_external_measurement_pre_attempt_v180r12r4(
    context: Mapping[str, Any],
    *,
    replayed_documents: Mapping[str, bytes],
    store: "DurableStoreV180R12R4",
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
) -> types.MappingProxyType:
    """Final gate; retain host conformance before any campaign ATTEMPT."""

    verified = validate_verified_external_launch_context_v180r12r4(
        context,
        replayed_documents=replayed_documents,
        monotonic_ns=monotonic_ns,
    )
    if verified["target"] != "measurement":
        _fail("measurement pre-attempt gate received a verification context")
    reobserve_precompiled_source_bundle_v180r12r4(verified)
    reobserved_parent = reobserve_cgroup_parent_fact_from_inherited_fds_v180r12r4()
    frozen_parent = _thaw_json_value(verified["cgroup_parent_fact"])
    reobserved_runtime = reobserve_runtime_capability_fact_v180r12r4()
    frozen_runtime = _thaw_json_value(verified["runtime_capability_fact"])
    expected_socket = expected_socket_buffer_capability_fact_v180r12r4()
    reobserved_socket = reobserve_socket_buffer_capability_fact_v180r12r4()
    host_conformance = write_pre_attempt_host_conformance_v180r12r4(
        store,
        campaign_attempt_id=verified["campaign_attempt_id"],
        expected_cgroup_parent_fact=frozen_parent,
        observed_cgroup_parent_fact=reobserved_parent,
        expected_runtime_capability_fact=frozen_runtime,
        observed_runtime_capability_fact=reobserved_runtime,
        expected_socket_buffer_capability=expected_socket,
        observed_socket_buffer_capability=reobserved_socket,
    )
    if host_conformance["full_host_conformance"] is not True:
        _fail(
            "pre-attempt host conformance failed: "
            + host_conformance["cause"]
        )
    placement_t2 = _revalidate_production_source_placement_v180r12r4(
        verified,
        schema=PRODUCTION_RUNTIME_PLACEMENT_T2_SCHEMA,
        boundary="T2_BEFORE_SCIENTIFIC_ATTEMPT_O_EXCL",
        require_progress_absent=True,
    )
    _check_campaign_deadline_v180r12r4(
        verified["campaign_deadline_ns"],
        monotonic_ns=monotonic_ns,
        boundary="pre-ATTEMPT authority replay",
    )
    values = dict(verified)
    values["schema"] = REVALIDATED_EXTERNAL_MEASUREMENT_CONTEXT_SCHEMA
    values["production_runtime_placement_t2"] = types.MappingProxyType(
        placement_t2
    )
    if tuple(values) != REVALIDATED_EXTERNAL_MEASUREMENT_CONTEXT_FIELDS:
        _fail("T2 revalidated measurement context field order changed")
    return types.MappingProxyType(values)


def _relative_parts(relative_path: str) -> tuple[str, ...]:
    if type(relative_path) is not str:
        _fail("runtime path must be one relative string")
    path = PurePosixPath(relative_path)
    if path.is_absolute() or not path.parts or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        _fail("runtime path escaped its repository root")
    return path.parts


class DurableStoreV180R12R4:
    """Symlink-free, write-once, fsyncing repository-relative storage."""

    def __init__(self, repository_root: Path) -> None:
        root = Path(repository_root)
        metadata = os.lstat(root)
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            _fail("repository root is linked or non-directory")
        self.repository_root = root
        self.root_fd = os.open(
            root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        )

    def close(self) -> None:
        if self.root_fd >= 0:
            os.close(self.root_fd)
            self.root_fd = -1

    def _open_parent(
        self, relative_path: str, *, create: bool
    ) -> tuple[int, str]:
        parts = _relative_parts(relative_path)
        current = os.dup(self.root_fd)
        try:
            for part in parts[:-1]:
                created = False
                if create:
                    try:
                        os.mkdir(part, 0o700, dir_fd=current)
                        created = True
                        os.chmod(
                            part,
                            0o700,
                            dir_fd=current,
                            follow_symlinks=False,
                        )
                        os.fsync(current)
                    except FileExistsError:
                        pass
                successor = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=current,
                )
                metadata = os.fstat(successor)
                if not stat.S_ISDIR(metadata.st_mode):
                    os.close(successor)
                    _fail("durable campaign parent directory identity or mode changed")
                os.close(current)
                current = successor
            return current, parts[-1]
        except BaseException:
            os.close(current)
            raise

    def exists(self, relative_path: str) -> bool:
        try:
            parent_fd, name = self._open_parent(relative_path, create=False)
        except FileNotFoundError:
            return False
        try:
            try:
                os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                return False
            return True
        finally:
            os.close(parent_fd)

    def mkdir_once(self, relative_path: str, mode: int = 0o700) -> None:
        if type(mode) is not int or mode != 0o700:
            _fail("durable campaign directory mode changed")
        parent_fd, name = self._open_parent(relative_path, create=True)
        descriptor = -1
        try:
            os.mkdir(name, mode, dir_fd=parent_fd)
            os.chmod(name, mode, dir_fd=parent_fd, follow_symlinks=False)
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=parent_fd,
            )
            os.fchmod(descriptor, mode)
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISDIR(metadata.st_mode)
                or stat.S_IMODE(metadata.st_mode) != mode
                or metadata.st_nlink < 2
            ):
                _fail("durable campaign directory identity or mode changed")
            os.fsync(descriptor)
            os.fsync(parent_fd)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            os.close(parent_fd)

    def write_once(
        self, relative_path: str, raw: bytes, *, mode: int = 0o400
    ) -> None:
        if type(raw) is not bytes:
            _fail("durable write requires exact bytes")
        parent_fd, name = self._open_parent(relative_path, create=True)
        descriptor = -1
        path_created = False
        try:
            descriptor = os.open(
                name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_NOFOLLOW
                | os.O_CLOEXEC,
                mode,
                dir_fd=parent_fd,
            )
            path_created = True
            remaining = memoryview(raw)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    _fail("durable write made no progress")
                remaining = remaining[written:]
            os.fchmod(descriptor, mode)
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = -1
            os.fsync(parent_fd)
        except FileExistsError:
            raise
        except BaseException as error:
            raise V180R12R4DurableWriteFailure(
                relative_path, path_created
            ) from error
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            os.close(parent_fd)

    def read_exact(
        self,
        relative_path: str,
        byte_cap: int,
        *,
        expected_mode: int | None = None,
    ) -> bytes:
        parent_fd, name = self._open_parent(relative_path, create=False)
        descriptor = -1
        try:
            descriptor = os.open(
                name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd
            )
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_size <= 0
                or before.st_size > byte_cap
                or expected_mode is not None
                and stat.S_IMODE(before.st_mode) != expected_mode
            ):
                _fail("durable input is not one bounded single-link regular file")
            chunks: list[bytes] = []
            remaining = before.st_size
            while remaining:
                chunk = os.read(descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    _fail("durable input ended before its exact size")
                chunks.append(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                _fail("durable input grew while observed")
            after = os.fstat(descriptor)
            compared = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size")
            if any(getattr(before, field) != getattr(after, field) for field in compared):
                _fail("durable input identity changed during read")
            return b"".join(chunks)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            os.close(parent_fd)

    def write_once_verified(
        self,
        relative_path: str,
        raw: bytes,
        *,
        byte_cap: int,
        mode: int = 0o400,
    ) -> bytes:
        """O_EXCL-write one bounded artifact, then byte-for-byte read it back."""

        if (
            type(raw) is not bytes
            or not raw
            or type(byte_cap) is not int
            or byte_cap <= 0
            or len(raw) > byte_cap
            or mode != 0o400
        ):
            raise V180R12R4CapViolation(
                "success artifact exceeds its exact preregistered byte cap"
            )
        # ``write_once`` performs O_EXCL, fchmod(0400), file fsync, and parent
        # directory fsync.  The second open is intentionally separate: an
        # exit-zero result is forbidden unless the durable namespace bytes are
        # the exact bytes returned by the pure finalizer.
        self.write_once(relative_path, raw, mode=mode)
        readback = self.read_exact(relative_path, byte_cap)
        if readback != raw:
            _fail("success artifact stable readback differs byte-for-byte")
        parent_fd, name = self._open_parent(relative_path, create=False)
        try:
            metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or stat.S_IMODE(metadata.st_mode) != mode
                or metadata.st_size != len(raw)
            ):
                _fail("success artifact durable mode or identity changed")
        finally:
            os.close(parent_fd)
        return readback

    def observe_failure_artifact(
        self, relative_path: str, *, kind: str
    ) -> runtime.FailureArtifactObservationV180R12R4:
        """Stream-observe one owned path without following links or joining bytes."""

        if kind not in {"FILE", "DIRECTORY"}:
            _fail("failure artifact kind is malformed")

        def row(
            state: str,
            *,
            mode: int | None = None,
            nlink: int | None = None,
            byte_count: int | None = None,
            digest: str | None = None,
            entries: tuple[str, ...] | None = None,
            error: BaseException | None = None,
        ) -> runtime.FailureArtifactObservationV180R12R4:
            error_text = None if error is None else _bounded_exception_text(error)
            error_type = None
            if error is not None:
                try:
                    error_type = type.__getattribute__(
                        type(error), "__name__"
                    ).encode(
                        "utf-8", "replace"
                    )[:512].decode("utf-8", "replace") or "BaseException"
                except BaseException:
                    error_type = "BaseException"
            return runtime.FailureArtifactObservationV180R12R4(
                relative_path,
                kind,
                state,
                mode,
                nlink,
                byte_count,
                digest,
                entries,
                error_type,
                None if error_text is None else error_text[:512],
            )

        try:
            parent_fd, name = self._open_parent(relative_path, create=False)
        except FileNotFoundError:
            return row("ABSENT")
        except BaseException as error:
            return row("READ_ERROR", error=error)
        descriptor = -1
        try:
            try:
                metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                return row("ABSENT")
            expected = (
                stat.S_ISREG(metadata.st_mode)
                if kind == "FILE"
                else stat.S_ISDIR(metadata.st_mode)
            )
            if not expected or stat.S_ISLNK(metadata.st_mode) or (
                kind == "FILE" and metadata.st_nlink != 1
            ):
                return row(
                    "LINKED_OR_NONREGULAR",
                    mode=metadata.st_mode,
                    nlink=metadata.st_nlink,
                    byte_count=(metadata.st_size if kind == "FILE" else None),
                )
            if kind == "DIRECTORY":
                descriptor = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=parent_fd,
                )
                bounded_entries: list[str] = []
                entry_name_bytes = 0
                with os.scandir(descriptor) as iterator:
                    for entry in iterator:
                        name = entry.name
                        if type(name) is not str or name in {"", ".", ".."}:
                            _fail("failure directory entry name is malformed")
                        entry_name_bytes += len(name.encode("utf-8", "strict"))
                        if (
                            len(bounded_entries) >= FAILURE_DIRECTORY_ENTRY_CAP
                            or entry_name_bytes
                            > FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP
                        ):
                            raise V180R12R4CapViolation(
                                "failure directory observation exceeds its exact "
                                "entry or name-byte cap"
                            )
                        bounded_entries.append(name)
                entries = tuple(sorted(bounded_entries))
                after = os.fstat(descriptor)
                if (
                    after.st_dev != metadata.st_dev
                    or after.st_ino != metadata.st_ino
                    or after.st_mode != metadata.st_mode
                    or after.st_nlink != metadata.st_nlink
                ):
                    _fail("failure directory identity changed during observation")
                return row(
                    "PRESENT",
                    mode=after.st_mode,
                    nlink=after.st_nlink,
                    entries=entries,
                )
            descriptor = os.open(
                name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd
            )
            before = os.fstat(descriptor)
            if before.st_size > FAILURE_ARTIFACT_HASH_BYTE_CAP:
                raise V180R12R4CapViolation(
                    "failure artifact exceeds bounded streaming hash cap"
                )
            digest_state = hashlib.sha256()
            observed = 0
            while observed < before.st_size:
                chunk = os.read(descriptor, min(64 * 1024, before.st_size - observed))
                if not chunk:
                    _fail("failure artifact ended before its observed size")
                digest_state.update(chunk)
                observed += len(chunk)
            if os.read(descriptor, 1):
                _fail("failure artifact grew while hashed")
            after = os.fstat(descriptor)
            if any(
                getattr(before, field) != getattr(after, field)
                for field in ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size")
            ):
                _fail("failure artifact identity changed while hashed")
            return row(
                "PRESENT",
                mode=after.st_mode,
                nlink=after.st_nlink,
                byte_count=observed,
                digest=digest_state.hexdigest(),
            )
        except BaseException as error:
            metadata = locals().get("metadata")
            return row(
                "READ_ERROR",
                mode=None if metadata is None else metadata.st_mode,
                nlink=None if metadata is None else metadata.st_nlink,
                byte_count=(
                    None
                    if metadata is None or kind == "DIRECTORY"
                    else metadata.st_size
                ),
                error=error,
            )
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            os.close(parent_fd)

    def observe_failure_progress(
        self,
    ) -> tuple[runtime.FailureArtifactObservationV180R12R4, ...]:
        """Observe fixed progress paths and every bounded EVENTS entry."""

        kinds = dict(FAILURE_ARTIFACT_FIXED_PATH_KINDS)
        events = self.observe_failure_artifact(
            EVENTS_RELATIVE_PATH, kind="DIRECTORY"
        )
        observations = [
            self.observe_failure_artifact(path, kind=kind)
            for path, kind in kinds.items()
            if path != EVENTS_RELATIVE_PATH
        ]
        observations.append(events)
        if events.state == "PRESENT" and events.directory_entries is not None:
            for name in events.directory_entries:
                observations.append(
                    self.observe_failure_artifact(
                        f"{EVENTS_RELATIVE_PATH}/{name}", kind="FILE"
                    )
                )
        observations.sort(key=lambda item: item.relative_path)
        if (
            len(observations) > FAILURE_ARTIFACT_ROW_CAP
            or len({item.relative_path for item in observations}) != len(observations)
        ):
            raise V180R12R4CapViolation(
                "failure artifact observations exceed exact row cap"
            )
        return tuple(observations)

    def reserve_failure_space(
        self, byte_count: int = FAILURE_RESERVE_BYTES
    ) -> bytearray:
        """Pre-cap heap reserve released before any terminal formatting."""

        if type(byte_count) is not int or byte_count != FAILURE_RESERVE_BYTES:
            _fail("failure reserve differs from its frozen exact byte count")
        reserve = bytearray(byte_count)
        # Touch every page so this is committed memory, not merely virtual
        # address space that could fail only inside the terminal path.
        for offset in range(0, byte_count, 4096):
            reserve[offset] = 1
        return reserve


def replay_external_authority_documents_v180r12r4(
    context: Mapping[str, Any],
    *,
    store: DurableStoreV180R12R4,
) -> dict[str, bytes]:
    """Independently rebuild frozen authority and stable-read transport bytes."""

    if (
        type(context) is not types.MappingProxyType
        or tuple(context) != VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS
        or type(store) is not DurableStoreV180R12R4
    ):
        _fail("external authority replay requires exact bootstrap/store inputs")
    cgroup_fact = _thaw_json_value(context["cgroup_parent_fact"])
    capability_fact = _thaw_json_value(context["runtime_capability_fact"])
    frozen_protocol = protocol.freeze_campaign_measurement_protocol_v180r12r4(
        cgroup_parent_fact=cgroup_fact,
        runtime_capability_fact=capability_fact,
    )
    source_facts = authorization.replay_authorization_source_facts_v180r12r4()
    frozen_authorization = (
        authorization.freeze_campaign_measurement_execution_authorization_v180r12r4(
            cgroup_parent_fact=cgroup_fact,
            runtime_capability_fact=capability_fact,
            source_facts=source_facts,
        )
    )
    frozen_evidence = (
        authorization_evidence.freeze_campaign_measurement_authorization_evidence_v180r12r4(
            context["prereg_commit_id"],
            cgroup_parent_fact=cgroup_fact,
            runtime_capability_fact=capability_fact,
        )
    )
    current_attempt_path = (
        protocol.PRELAUNCH_MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH
        if context["target"] == "measurement"
        else protocol.PRELAUNCH_VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH
    )
    materialization_raw = store.read_exact(
        protocol.PRELAUNCH_MATERIALIZATION_TERMINAL_RELATIVE_PATH,
        64 * 1024 * 1024,
        expected_mode=0o400,
    )
    current_attempt_raw = store.read_exact(
        current_attempt_path, 16 * 1024 * 1024, expected_mode=0o400
    )
    measurement_attempt_raw = store.read_exact(
        protocol.PRELAUNCH_MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH,
        16 * 1024 * 1024,
        expected_mode=0o400,
    )
    return {
        "protocol": frozen_protocol.canonical_bytes,
        "authorization": frozen_authorization.canonical_bytes,
        "authorization_evidence": frozen_evidence.canonical_bytes,
        "prelaunch_materialization_terminal": materialization_raw,
        "current_launch_attempt": current_attempt_raw,
        "measurement_launch_attempt": measurement_attempt_raw,
    }


CAMPAIGN_ATTEMPT_AUTHORITY_FIELDS = (
    "protocol_id",
    "authorization_id",
    "authorization_evidence_id",
    "campaign_measurement_execution_slot_id",
    "logical_occurrence_id",
    "execution_nonce",
    "prelaunch_materialization_terminal_id",
    "prelaunch_launch_manifest_sha256",
    "prelaunch_launch_rule_id",
    "measurement_launch_attempt_id",
)


@dataclass(frozen=True, slots=True)
class CampaignAttemptAuthorityV180R12R4:
    protocol_id: str
    authorization_id: str
    authorization_evidence_id: str
    campaign_measurement_execution_slot_id: str
    logical_occurrence_id: str
    execution_nonce: str
    prelaunch_materialization_terminal_id: str
    prelaunch_launch_manifest_sha256: str
    prelaunch_launch_rule_id: str
    measurement_launch_attempt_id: str

    def __post_init__(self) -> None:
        if tuple(field for field in self.__dataclass_fields__) != (
            CAMPAIGN_ATTEMPT_AUTHORITY_FIELDS
        ):
            _fail("campaign attempt authority field order changed")
        for field_name in CAMPAIGN_ATTEMPT_AUTHORITY_FIELDS:
            _require_content_id(
                getattr(self, field_name), "campaign attempt " + field_name
            )

    @property
    def attempt_id(self) -> str:
        return identity_domains.derive_campaign_measurement_attempt_id_v180r12r4(
            protocol_id=self.protocol_id,
            authorization_id=self.authorization_id,
            authorization_evidence_id=self.authorization_evidence_id,
            campaign_measurement_execution_slot_id=(
                self.campaign_measurement_execution_slot_id
            ),
            logical_occurrence_id=self.logical_occurrence_id,
            execution_nonce=self.execution_nonce,
        )

    @classmethod
    def from_external_context(
        cls, context: Mapping[str, Any]
    ) -> "CampaignAttemptAuthorityV180R12R4":
        if type(context) is not types.MappingProxyType:
            _fail("campaign attempt authority requires verified external context")
        return cls(*(context[field] for field in CAMPAIGN_ATTEMPT_AUTHORITY_FIELDS))


def build_campaign_attempt_record_v180r12r4(
    authority: CampaignAttemptAuthorityV180R12R4,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Issue event-0 evidence solely from the six-input attempt authority."""

    if type(authority) is not CampaignAttemptAuthorityV180R12R4:
        _fail("campaign attempt record authority is mistyped")
    operation_manifest = ledger.campaign_operation_manifest_v180r12r4(
        authority.attempt_id
    )
    operation_manifest_id = _require_content_id(
        operation_manifest.get("campaign_operation_manifest_id"),
        "campaign operation manifest ID",
    )
    event_zero = ledger.build_campaign_success_event_schedule_v180r12r4(
        authority.attempt_id
    )[0]
    if (
        event_zero.event_kind != "ATTEMPT_OPEN"
        or event_zero.actor_role != "OBSERVER"
        or event_zero.phase != "ATTEMPT"
    ):
        _fail("campaign success schedule event zero changed")
    record = ledger.issue_campaign_attempt_record_v180r12r4(
        protocol_id=authority.protocol_id,
        authorization_id=authority.authorization_id,
        authorization_evidence_id=authority.authorization_evidence_id,
        campaign_measurement_execution_slot_id=(
            authority.campaign_measurement_execution_slot_id
        ),
        logical_occurrence_id=authority.logical_occurrence_id,
        execution_nonce=authority.execution_nonce,
        prelaunch_materialization_terminal_id=(
            authority.prelaunch_materialization_terminal_id
        ),
        prelaunch_launch_manifest_sha256=(
            authority.prelaunch_launch_manifest_sha256
        ),
        prelaunch_launch_rule_id=authority.prelaunch_launch_rule_id,
        measurement_launch_attempt_id=authority.measurement_launch_attempt_id,
        attempt_id=authority.attempt_id,
        operation_id=event_zero.operation_id,
        operation_manifest_id=operation_manifest_id,
    )
    return record, operation_manifest


def validate_campaign_attempt_record_v180r12r4(
    attempt_document: Mapping[str, Any],
    *,
    authority: CampaignAttemptAuthorityV180R12R4,
) -> dict[str, Any]:
    """Reject a foreign/re-signed event-0 document before O_EXCL."""

    if not isinstance(attempt_document, Mapping):
        _fail("attempt record must be one mapping")
    expected, _manifest = build_campaign_attempt_record_v180r12r4(authority)
    actual = _thaw_json_value(attempt_document)
    if type(actual) is not dict or actual != expected:
        _fail("campaign ATTEMPT document is not its exact six-input issuance")
    return actual


@dataclass(frozen=True, slots=True)
class AttemptClaimV180R12R4:
    attempt_document: Mapping[str, Any]
    failure_reserve: bytearray


@dataclass(slots=True)
class AttemptOwnershipTokenV180R12R4:
    """Preallocated bridge across the claim-return async-signal gap."""

    owned: bool = False
    failure_reserve: bytearray | None = None


def claim_attempt_before_effects_v180r12r4(
    store: DurableStoreV180R12R4,
    attempt_document: Mapping[str, Any],
    *,
    authority: CampaignAttemptAuthorityV180R12R4,
    forbidden_progress_paths: Sequence[str],
    ownership_token: AttemptOwnershipTokenV180R12R4 | None = None,
) -> AttemptClaimV180R12R4:
    """Create the O_EXCL replay lock before any measured read/cgroup effect."""

    token = (
        AttemptOwnershipTokenV180R12R4()
        if ownership_token is None
        else ownership_token
    )
    if (
        type(token) is not AttemptOwnershipTokenV180R12R4
        or token.owned
        or token.failure_reserve is not None
    ):
        _fail("attempt ownership token was reused or mistyped")
    validated_attempt = validate_campaign_attempt_record_v180r12r4(
        attempt_document, authority=authority
    )
    # Commit the exact heap reserve before consuming the one-shot identity.
    # Clearing it is the first terminal action, before hostile formatting or
    # any bounded artifact observation allocates replacement memory.
    reserve = store.reserve_failure_space()
    token.failure_reserve = reserve
    try:
        if any(store.exists(path) for path in forbidden_progress_paths):
            raise V180R12R4ReplayForbidden(
                "attempt or output progress already exists; same identity cannot rerun"
            )
        try:
            store.write_once(ATTEMPT_RELATIVE_PATH, _canonical(validated_attempt))
            token.owned = True
        except FileExistsError as error:
            raise V180R12R4ReplayForbidden(
                "attempt O_EXCL lost; same identity cannot rerun"
            ) from error
        except V180R12R4DurableWriteFailure as error:
            # Preabsence was established above and FileExistsError is the sole
            # loser signal.  Any other ATTEMPT write failure consumes this
            # launch identity, even when interruption occurred between the
            # kernel's successful O_EXCL open and Python's path-created flag.
            token.owned = True
            raise V180R12R4OwnedAttemptFailure(reserve) from error
        except BaseException as error:
            token.owned = True
            raise V180R12R4OwnedAttemptFailure(reserve) from error
    except BaseException as error:
        if token.owned:
            if isinstance(error, V180R12R4OwnedAttemptFailure):
                raise
            raise V180R12R4OwnedAttemptFailure(reserve) from error
        reserve.clear()
        token.failure_reserve = None
        raise
    return AttemptClaimV180R12R4(validated_attempt, reserve)


class CanonicalEventJournalV180R12R4:
    """Sole durable owner for the exact 625 canonical event files."""

    def __init__(
        self,
        store: DurableStoreV180R12R4,
        *,
        protocol_id: str,
        authorization_id: str,
        attempt_id: str,
    ) -> None:
        self.store = store
        self.protocol_id = protocol_id
        self.authorization_id = authorization_id
        self.attempt_id = attempt_id
        self.schedule = ledger.build_campaign_success_event_schedule_v180r12r4(
            attempt_id
        )
        if len(self.schedule) != SUCCESS_EVENT_COUNT:
            _fail("kernel event schedule is not exactly 625 positions")
        store.mkdir_once(OUTPUT_ROOT_RELATIVE_PATH)
        store.mkdir_once(EVENTS_RELATIVE_PATH)
        self.next_sequence = 0
        self.previous_event_id: str | None = None
        self.total_event_bytes = 0

    def append(self, event_document: Mapping[str, Any] | bytes) -> dict[str, Any]:
        if self.next_sequence >= SUCCESS_EVENT_COUNT:
            raise V180R12R4CapViolation(
                "event journal exceeded its exact 625-position schedule"
            )
        event = ledger.CampaignLedgerEventV180R12R4.from_document(event_document)
        expected = self.schedule[self.next_sequence]
        if (
            event.protocol_id != self.protocol_id
            or event.authorization_id != self.authorization_id
            or event.attempt_id != self.attempt_id
            or event.sequence != self.next_sequence
            or event.previous_event_id != self.previous_event_id
            or (event.event_kind, event.actor_role, event.phase, event.operation_id)
            != (
                expected.event_kind,
                expected.actor_role,
                expected.phase,
                expected.operation_id,
            )
        ):
            _fail("event is not the next exact observer-owned schedule position")
        raw = _canonical(event.to_document())
        if len(raw) > MAX_EVENT_BYTES:
            raise V180R12R4CapViolation("canonical event exceeds the 64KiB cap")
        if self.total_event_bytes + len(raw) > MAX_LEDGER_BYTES:
            raise V180R12R4CapViolation(
                "canonical event ledger exceeds the 64MiB cap"
            )
        sequence = self.next_sequence
        successor_total_event_bytes = self.total_event_bytes + len(raw)
        successor_next_sequence = sequence + 1
        successor_previous_event_id = event.event_id
        relative_path = f"{EVENTS_RELATIVE_PATH}/{sequence:06d}.json"
        ack = {
            "schema": "acfqp.v180r12r4_observer_event_ack.v1",
            "sequence": sequence,
            "event_id": event.event_id,
            "event_file_sha256": hashlib.sha256(raw).hexdigest(),
            "durable_file_and_directory_fsync_complete": True,
        }
        try:
            self.store.write_once(relative_path, raw)
            self.total_event_bytes = successor_total_event_bytes
            self.next_sequence = successor_next_sequence
            self.previous_event_id = successor_previous_event_id
        except BaseException:
            # SIGALRM can arrive after file+directory fsync but before the
            # in-memory successor advances.  Promote only an exact stable file;
            # a partial next path remains visible solely in failure evidence.
            try:
                durable = self.store.read_exact(relative_path, MAX_EVENT_BYTES)
            except BaseException:
                durable = None
            if durable == raw:
                self.total_event_bytes = successor_total_event_bytes
                self.next_sequence = successor_next_sequence
                self.previous_event_id = successor_previous_event_id
            raise
        return ack

    def assert_complete(self) -> None:
        if self.next_sequence != SUCCESS_EVENT_COUNT:
            _fail("observer journal is an incomplete preserved event prefix")

    def read_complete_event_documents(self) -> tuple[bytes, ...]:
        """Return the exact durable 625-file population in sequence order."""

        self.assert_complete()
        rows: list[bytes] = []
        total = 0
        previous_event_id: str | None = None
        for sequence in range(SUCCESS_EVENT_COUNT):
            raw = self.store.read_exact(
                f"{EVENTS_RELATIVE_PATH}/{sequence:06d}.json", MAX_EVENT_BYTES
            )
            event = ledger.CampaignLedgerEventV180R12R4.from_document(raw)
            if (
                event.sequence != sequence
                or event.previous_event_id != previous_event_id
            ):
                _fail("durable event population is not its exact canonical chain")
            total += len(raw)
            if total > MAX_LEDGER_BYTES:
                raise V180R12R4CapViolation(
                    "durable event population exceeds the 64MiB cap"
                )
            rows.append(raw)
            previous_event_id = event.event_id
        if previous_event_id != self.previous_event_id or total != self.total_event_bytes:
            _fail("durable event population differs from observer journal state")
        return tuple(rows)


class AuthenticatedFrameChannelV180R12R4:
    """Directional, role-bound, sequence-exact canonical SOCK_SEQPACKET."""

    _ROLE_FRAME_TYPES = {
        ("OBSERVER", "SUPERVISOR"): {
            "PARENT_TO_CHILD": frozenset({"SUPERVISOR_START", "EVENT_ACK"}),
            "CHILD_TO_PARENT": frozenset({"EVENT_PROPOSAL"}),
        },
        ("SUPERVISOR", "WORKER"): {
            "PARENT_TO_CHILD": frozenset({"WORKER_HANDOFF", "EVENT_ACK"}),
            "CHILD_TO_PARENT": frozenset({"EVENT_PROPOSAL"}),
        },
    }
    _FIRST_PARENT_FRAME = {
        ("OBSERVER", "SUPERVISOR"): "SUPERVISOR_START",
        ("SUPERVISOR", "WORKER"): "WORKER_HANDOFF",
    }

    def __init__(
        self,
        channel: socket.socket,
        secret: bytes,
        *,
        channel_id: str,
        protocol_id: str,
        authorization_id: str,
        authorization_evidence_id: str,
        attempt_id: str,
        parent_actor_role: str,
        child_actor_role: str,
        local_actor_role: str,
    ) -> None:
        role_pair = (parent_actor_role, child_actor_role)
        if type(secret) is not bytes or len(secret) != 32:
            _fail("IPC secret must be exactly 32 unpredictable bytes")
        if channel.type & socket.SOCK_SEQPACKET != socket.SOCK_SEQPACKET:
            _fail("observer IPC must use SOCK_SEQPACKET")
        for value, label in (
            (channel_id, "channel ID"),
            (protocol_id, "channel protocol ID"),
            (authorization_id, "channel authorization ID"),
            (authorization_evidence_id, "channel authorization-evidence ID"),
            (attempt_id, "channel attempt ID"),
        ):
            _require_content_id(value, label)
        if (
            role_pair not in self._ROLE_FRAME_TYPES
            or local_actor_role not in role_pair
        ):
            _fail("IPC parent/child/local role tuple changed")
        expected_birth_role = role_pair[1]
        expected_channel_ids = {
            row.operation_id
            for row in ledger.build_campaign_success_event_schedule_v180r12r4(
                attempt_id
            )
            if row.event_kind == "PROCESS_BIRTH_INTENT"
            and row.actor_role == role_pair[0]
            and (
                expected_birth_role == "SUPERVISOR" and row.phase == "STAGE"
                or expected_birth_role == "WORKER" and row.phase == "WORKER"
            )
        }
        if expected_channel_ids != {channel_id}:
            _fail("IPC channel ID is not the exact child birth operation ID")
        self.channel = channel
        self.channel_id = channel_id
        self.protocol_id = protocol_id
        self.authorization_id = authorization_id
        self.authorization_evidence_id = authorization_evidence_id
        self.attempt_id = attempt_id
        self.parent_actor_role = parent_actor_role
        self.child_actor_role = child_actor_role
        self.local_actor_role = local_actor_role
        self.remote_actor_role = (
            child_actor_role
            if local_actor_role == parent_actor_role
            else parent_actor_role
        )
        self.is_parent = local_actor_role == parent_actor_role
        self.send_direction = (
            "PARENT_TO_CHILD" if self.is_parent else "CHILD_TO_PARENT"
        )
        self.receive_direction = (
            "CHILD_TO_PARENT" if self.is_parent else "PARENT_TO_CHILD"
        )
        self.send_key = self._direction_key(secret, self.send_direction)
        self.receive_key = self._direction_key(secret, self.receive_direction)
        self.next_send_sequence = 0
        self.next_receive_sequence = 0

    def _direction_key(self, parent_secret: bytes, direction: str) -> bytes:
        context = {
            "schema": "acfqp.v180r12r4_runtime_channel_key_context.v1",
            "channel_id": self.channel_id,
            "protocol_id": self.protocol_id,
            "authorization_id": self.authorization_id,
            "authorization_evidence_id": self.authorization_evidence_id,
            "attempt_id": self.attempt_id,
            "parent_actor_role": self.parent_actor_role,
            "child_actor_role": self.child_actor_role,
            "direction": direction,
        }
        return hashlib.blake2s(
            _canonical(context), key=parent_secret, digest_size=32
        ).digest()

    def _validate_frame_type(self, frame_type: str, direction: str) -> None:
        allowed = self._ROLE_FRAME_TYPES[
            (self.parent_actor_role, self.child_actor_role)
        ][direction]
        if frame_type not in allowed:
            _fail("authenticated IPC frame type crossed its role/direction")
        if direction == "PARENT_TO_CHILD":
            sequence = (
                self.next_send_sequence
                if direction == self.send_direction
                else self.next_receive_sequence
            )
            first = self._FIRST_PARENT_FRAME[
                (self.parent_actor_role, self.child_actor_role)
            ]
            if (
                sequence == 0 and frame_type != first
                or sequence >= 1 and frame_type != "EVENT_ACK"
            ):
                _fail("authenticated IPC parent frame transition changed")
        elif frame_type != "EVENT_PROPOSAL":
            _fail("authenticated IPC child direction accepts proposals only")

    def send(self, frame_type: str, sequence: int, body: Mapping[str, Any]) -> None:
        if type(sequence) is not int or sequence != self.next_send_sequence:
            _fail("authenticated IPC send sequence replayed or skipped")
        self._validate_frame_type(frame_type, self.send_direction)
        validated_body = _validate_runtime_frame_body_v180r12r4(
            frame_type,
            body,
            protocol_id=self.protocol_id,
            authorization_id=self.authorization_id,
            authorization_evidence_id=self.authorization_evidence_id,
            attempt_id=self.attempt_id,
        )
        unsigned = {
            "schema": "acfqp.v180r12r4_runtime_ipc_frame.v1",
            "channel_id": self.channel_id,
            "direction": self.send_direction,
            "sender_actor_role": self.local_actor_role,
            "recipient_actor_role": self.remote_actor_role,
            "frame_type": frame_type,
            "sequence": sequence,
            "body": validated_body,
        }
        mac = hashlib.blake2s(
            _canonical(unsigned), key=self.send_key, digest_size=32
        ).hexdigest()
        raw = _canonical({**unsigned, "mac": mac})
        if len(raw) > FRAME_BYTE_CAP:
            raise V180R12R4CapViolation(
                "authenticated IPC frame exceeds its byte cap"
            )
        written = self.channel.send(raw)
        if written != len(raw):
            _fail("authenticated IPC frame made a partial seqpacket write")
        self.next_send_sequence = sequence + 1

    def receive(
        self, *, allow_eof: bool = False
    ) -> tuple[str, int, dict[str, Any]] | None:
        raw, ancillary, flags, address = self.channel.recvmsg(FRAME_BYTE_CAP + 1)
        if not raw and not ancillary and flags == 0 and address in (None, "", b""):
            if allow_eof:
                return None
            raise V180R12R4CapViolation(
                "authenticated IPC channel ended before its exact boundary"
            )
        if (
            flags != 0
            or ancillary
            or address not in (None, "", b"")
            or not raw
            or len(raw) > FRAME_BYTE_CAP
        ):
            raise V180R12R4CapViolation(
                "authenticated IPC frame carried flags, ancillary data, an "
                "address, truncation, or excess bytes"
            )
        frame = _canonical_object(raw, "authenticated IPC frame")
        unsigned_fields = (
            "schema", "channel_id", "direction", "sender_actor_role",
            "recipient_actor_role", "frame_type", "sequence", "body",
        )
        if set(frame) != {*unsigned_fields, "mac"}:
            _fail("authenticated IPC frame field set changed")
        unsigned = {key: frame[key] for key in unsigned_fields}
        expected = hashlib.blake2s(
            _canonical(unsigned), key=self.receive_key, digest_size=32
        ).hexdigest()
        if (
            frame["schema"] != "acfqp.v180r12r4_runtime_ipc_frame.v1"
            or frame["channel_id"] != self.channel_id
            or frame["direction"] != self.receive_direction
            or frame["sender_actor_role"] != self.remote_actor_role
            or frame["recipient_actor_role"] != self.local_actor_role
            or type(frame["frame_type"]) is not str
            or type(frame["sequence"]) is not int
            or type(frame["body"]) is not dict
            or not hmac.compare_digest(frame.get("mac", ""), expected)
        ):
            _fail("authenticated IPC frame failed canonical MAC validation")
        if frame["sequence"] != self.next_receive_sequence:
            _fail("authenticated IPC receive sequence replayed or skipped")
        self._validate_frame_type(frame["frame_type"], self.receive_direction)
        validated_body = _validate_runtime_frame_body_v180r12r4(
            frame["frame_type"],
            frame["body"],
            protocol_id=self.protocol_id,
            authorization_id=self.authorization_id,
            authorization_evidence_id=self.authorization_evidence_id,
            attempt_id=self.attempt_id,
        )
        self.next_receive_sequence = frame["sequence"] + 1
        return frame["frame_type"], frame["sequence"], validated_body


EVENT_PROPOSAL_BODY_SCHEMA = "acfqp.v180r12r4_event_proposal.v1"
EVENT_ACK_BODY_SCHEMA = "acfqp.v180r12r4_event_ack.v1"
EVENT_PROPOSAL_BODY_FIELDS = (
    "schema",
    "protocol_id",
    "authorization_id",
    "authorization_evidence_id",
    "attempt_id",
    "campaign_event_sequence",
    "phase",
    "actor_role",
    "event_kind",
    "operation_id",
    "payload",
    "evidence_documents",
)
EVENT_ACK_BODY_FIELDS = (
    "schema",
    "protocol_id",
    "authorization_id",
    "authorization_evidence_id",
    "attempt_id",
    "campaign_event_sequence",
    "event_id",
    "event_file_sha256",
    "durable_file_and_directory_fsync_complete",
)
OBSERVER_SUPERVISOR_START_SCHEMA = (
    "acfqp.v180r12r4_observer_supervisor_start.v1"
)
OBSERVER_SUPERVISOR_START_FIELDS = (
    "schema",
    "protocol_id",
    "authorization_id",
    "authorization_evidence_id",
    "attempt_id",
    "campaign_measurement_execution_slot_id",
    "logical_occurrence_id",
    "execution_nonce",
    "campaign_attempt_record_id",
    "campaign_operation_manifest_id",
    "native_zero_source_manifest_id",
    "native_zero_import_inventory_id",
    "prelaunch_materialization_terminal_id",
    "prelaunch_launch_manifest_sha256",
    "prelaunch_launch_rule_id",
    "measurement_launch_attempt_id",
    "cgroup_topology_receipt_id",
    "cgroup_topology_document",
    "supervisor_birth_operation_id",
    "supervisor_birth_receipt_id",
    "supervisor_birth_document",
    "supervisor_birth_event_id",
    "supervisor_birth_event_sequence",
    "next_campaign_event_sequence",
    "one_shot_start",
)
SUPERVISOR_WORKER_HANDOFF_SCHEMA = (
    "acfqp.v180r12r4_supervisor_worker_handoff.v1"
)
SUPERVISOR_WORKER_HANDOFF_FIELDS = (
    "schema",
    "protocol_id",
    "authorization_id",
    "authorization_evidence_id",
    "attempt_id",
    "campaign_attempt_record_id",
    "execution_slot_id",
    "execution_nonce",
    "logical_occurrence_id",
    "prelaunch_materialization_terminal_id",
    "prelaunch_launch_manifest_sha256",
    "prelaunch_launch_rule_id",
    "measurement_launch_attempt_id",
    "operation_manifest_id",
    "native_zero_source_manifest_id",
    "native_zero_import_inventory_id",
    "terminal_snapshot_document",
    "verification_snapshot_document",
    "terminal_memfd_stage_document",
    "verification_memfd_stage_document",
    "terminal_open_visibility_document",
    "verification_open_visibility_document",
    "stage_semantic_receipt_documents",
    "terminal_stage_binding",
    "verification_stage_binding",
    "subject_output_binding",
    "worker_birth_operation_id",
    "worker_birth_receipt_id",
    "worker_birth_document",
    "worker_birth_event_id",
    "worker_birth_event_sequence",
    "next_campaign_event_sequence",
    "one_shot_handoff",
)


def _validate_registered_evidence_document_v180r12r4(
    value: Mapping[str, Any], *, expected_schema: str
) -> tuple[dict[str, Any], str]:
    rows = {
        schema: (domain, identity_field)
        for _kind, schema, domain, identity_field in (
            *runtime.EVIDENCE_DOCUMENT_CONTRACT_ROWS,
            *runtime.worker.EVIDENCE_DOCUMENT_CONTRACT_ROWS,
        )
    }
    keysets = {
        schema: keyset
        for _kind, schema, _identity_field, keyset in (
            *ledger.EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS,
            *runtime.EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS,
            *runtime.worker.EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS,
        )
    }
    if expected_schema not in rows:
        _fail("runtime evidence schema is not registered")
    domain, identity_field = rows[expected_schema]
    document = _thaw_json_value(value)
    if (
        type(document) is not dict
        or document.get("schema") != expected_schema
        or expected_schema not in keysets
        or set(document) != keysets[expected_schema]
    ):
        _fail("runtime evidence document schema changed")
    payload = dict(document)
    identity = payload.pop(identity_field, None)
    expected = evidence_domains.extension_content_id_v180r12r4e(domain, payload)
    if identity != expected:
        _fail("runtime evidence document content identity changed")
    return document, identity


def build_observer_supervisor_start_body_v180r12r4(
    *,
    authority: CampaignAttemptAuthorityV180R12R4,
    attempt_document: Mapping[str, Any],
    operation_manifest_document: Mapping[str, Any],
    native_zero_source_manifest_id: str,
    native_zero_import_inventory_id: str,
    cgroup_topology_document: Mapping[str, Any],
    supervisor_birth_document: Mapping[str, Any],
    supervisor_birth_event_id: str,
    supervisor_birth_event_sequence: int,
    next_campaign_event_sequence: int,
) -> dict[str, Any]:
    attempt, attempt_id = _validate_registered_evidence_document_v180r12r4(
        attempt_document,
        expected_schema="acfqp.campaign_attempt_record.v180r12r4",
    )
    topology, topology_id = _validate_registered_evidence_document_v180r12r4(
        cgroup_topology_document,
        expected_schema="acfqp.campaign_cgroup_topology_receipt.v180r12r4",
    )
    birth, birth_id = _validate_registered_evidence_document_v180r12r4(
        supervisor_birth_document,
        expected_schema="acfqp.campaign_pidfd_birth_receipt.v180r12r4",
    )
    operation_manifest = _thaw_json_value(operation_manifest_document)
    operation_manifest_id = operation_manifest.get(
        "campaign_operation_manifest_id"
    )
    expected_birth_operation_id = (
        ledger.build_campaign_success_event_schedule_v180r12r4(
            authority.attempt_id
        )[1].operation_id
    )
    if operation_manifest != ledger.campaign_operation_manifest_v180r12r4(
        authority.attempt_id
    ):
        _fail("START operation manifest differs from exact campaign authority")
    for value, label in (
        (native_zero_source_manifest_id, "START source manifest ID"),
        (native_zero_import_inventory_id, "START import inventory ID"),
        (supervisor_birth_event_id, "START birth event ID"),
    ):
        _require_content_id(value, label)
    if not (
        attempt == build_campaign_attempt_record_v180r12r4(authority)[0]
        and attempt_id == attempt["campaign_attempt_record_id"]
        and operation_manifest_id == attempt["operation_manifest_id"]
        and birth.get("attempt_id") == authority.attempt_id
        and birth.get("operation_id") == expected_birth_operation_id
        and birth.get("process_role") == "SUPERVISOR"
        and birth.get("cgroup_topology_receipt_id") == topology_id
        and type(supervisor_birth_event_sequence) is int
        and supervisor_birth_event_sequence == 2
        and type(next_campaign_event_sequence) is int
        and next_campaign_event_sequence == 3
    ):
        _fail("START causal topology/birth/attempt join changed")
    document = {
        "schema": OBSERVER_SUPERVISOR_START_SCHEMA,
        "protocol_id": authority.protocol_id,
        "authorization_id": authority.authorization_id,
        "authorization_evidence_id": authority.authorization_evidence_id,
        "attempt_id": authority.attempt_id,
        "campaign_measurement_execution_slot_id": (
            authority.campaign_measurement_execution_slot_id
        ),
        "logical_occurrence_id": authority.logical_occurrence_id,
        "execution_nonce": authority.execution_nonce,
        "campaign_attempt_record_id": attempt_id,
        "campaign_operation_manifest_id": operation_manifest_id,
        "native_zero_source_manifest_id": native_zero_source_manifest_id,
        "native_zero_import_inventory_id": native_zero_import_inventory_id,
        "prelaunch_materialization_terminal_id": (
            authority.prelaunch_materialization_terminal_id
        ),
        "prelaunch_launch_manifest_sha256": (
            authority.prelaunch_launch_manifest_sha256
        ),
        "prelaunch_launch_rule_id": authority.prelaunch_launch_rule_id,
        "measurement_launch_attempt_id": authority.measurement_launch_attempt_id,
        "cgroup_topology_receipt_id": topology_id,
        "cgroup_topology_document": topology,
        "supervisor_birth_operation_id": birth["operation_id"],
        "supervisor_birth_receipt_id": birth_id,
        "supervisor_birth_document": birth,
        "supervisor_birth_event_id": supervisor_birth_event_id,
        "supervisor_birth_event_sequence": supervisor_birth_event_sequence,
        "next_campaign_event_sequence": next_campaign_event_sequence,
        "one_shot_start": True,
    }
    if tuple(document) != OBSERVER_SUPERVISOR_START_FIELDS:
        raise AssertionError("START body construction field order changed")
    return document


def validate_event_proposal_body_v180r12r4(
    body: Mapping[str, Any],
    *,
    protocol_id: str,
    authorization_id: str,
    authorization_evidence_id: str,
    attempt_id: str,
) -> dict[str, Any]:
    document = _thaw_json_value(body)
    if type(document) is not dict or tuple(document) != EVENT_PROPOSAL_BODY_FIELDS:
        # In-memory MappingProxy preserves the frozen constructor order.  A
        # decoded canonical frame is alphabetical, so accept the same keyset.
        if type(document) is not dict or set(document) != set(EVENT_PROPOSAL_BODY_FIELDS):
            _fail("event proposal body field set changed")
    payload = document.get("payload")
    evidence = document.get("evidence_documents")
    if not (
        document.get("schema") == EVENT_PROPOSAL_BODY_SCHEMA
        and document.get("protocol_id") == protocol_id
        and document.get("authorization_id") == authorization_id
        and document.get("authorization_evidence_id")
        == authorization_evidence_id
        and document.get("attempt_id") == attempt_id
        and type(document.get("campaign_event_sequence")) is int
        and document["campaign_event_sequence"] >= 0
        and type(document.get("phase")) is str
        and type(document.get("actor_role")) is str
        and type(document.get("event_kind")) is str
        and type(document.get("operation_id")) is str
        and type(payload) is dict
        and set(payload)
        == {"evidence_id", "outcome_code", "measured_value", "auxiliary_values"}
        and payload.get("auxiliary_values") == []
        and type(evidence) is list
        and all(type(row) is dict for row in evidence)
    ):
        _fail("event proposal body context or payload changed")
    _require_content_id(document["operation_id"], "proposal operation ID")
    if payload["evidence_id"] is not None:
        _require_content_id(payload["evidence_id"], "proposal evidence ID")
    return document


def build_event_ack_body_v180r12r4(
    *,
    protocol_id: str,
    authorization_id: str,
    authorization_evidence_id: str,
    attempt_id: str,
    journal_ack: Mapping[str, Any],
) -> dict[str, Any]:
    ack = dict(journal_ack)
    if set(ack) != {
        "schema", "sequence", "event_id", "event_file_sha256",
        "durable_file_and_directory_fsync_complete",
    }:
        _fail("journal ACK field set changed before IPC wrapping")
    document = {
        "schema": EVENT_ACK_BODY_SCHEMA,
        "protocol_id": _require_content_id(protocol_id, "ACK protocol ID"),
        "authorization_id": _require_content_id(
            authorization_id, "ACK authorization ID"
        ),
        "authorization_evidence_id": _require_content_id(
            authorization_evidence_id, "ACK authorization-evidence ID"
        ),
        "attempt_id": _require_content_id(attempt_id, "ACK attempt ID"),
        "campaign_event_sequence": ack["sequence"],
        "event_id": _require_content_id(ack["event_id"], "ACK event ID"),
        "event_file_sha256": _require_content_id(
            ack["event_file_sha256"], "ACK event file SHA-256"
        ),
        "durable_file_and_directory_fsync_complete": ack[
            "durable_file_and_directory_fsync_complete"
        ],
    }
    if (
        type(document["campaign_event_sequence"]) is not int
        or document["campaign_event_sequence"] < 0
        or document["durable_file_and_directory_fsync_complete"] is not True
    ):
        _fail("event ACK is not one durable exact sequence")
    return document


def _validate_runtime_frame_body_v180r12r4(
    frame_type: str,
    body: Mapping[str, Any],
    *,
    protocol_id: str,
    authorization_id: str,
    authorization_evidence_id: str,
    attempt_id: str,
) -> dict[str, Any]:
    """Validate every authenticated frame body before send and after receive.

    Completion and failure-notice frames are deliberately absent.  The child
    closes its channel only at its preregistered event boundary; the parent
    then authenticates the exact event prefix and pidfd exit status.  This
    avoids a second caller-supplied PASS/failure authority.
    """

    if frame_type == "EVENT_PROPOSAL":
        return validate_event_proposal_body_v180r12r4(
            body,
            protocol_id=protocol_id,
            authorization_id=authorization_id,
            authorization_evidence_id=authorization_evidence_id,
            attempt_id=attempt_id,
        )
    document = _thaw_json_value(body)
    common = (
        type(document) is dict
        and document.get("protocol_id") == protocol_id
        and document.get("authorization_id") == authorization_id
        and document.get("authorization_evidence_id")
        == authorization_evidence_id
        and document.get("attempt_id") == attempt_id
    )
    if frame_type == "EVENT_ACK":
        if not (
            common
            and set(document) == set(EVENT_ACK_BODY_FIELDS)
            and document.get("schema") == EVENT_ACK_BODY_SCHEMA
            and type(document.get("campaign_event_sequence")) is int
            and document["campaign_event_sequence"] >= 0
            and document.get("durable_file_and_directory_fsync_complete") is True
        ):
            _fail("event ACK body schema, keyset, or context changed")
        _require_content_id(document.get("event_id"), "ACK event ID")
        _require_content_id(
            document.get("event_file_sha256"), "ACK event file SHA-256"
        )
        return document
    if frame_type == "SUPERVISOR_START":
        if not (
            common
            and set(document) == set(OBSERVER_SUPERVISOR_START_FIELDS)
            and document.get("schema") == OBSERVER_SUPERVISOR_START_SCHEMA
            and document.get("supervisor_birth_event_sequence") == 2
            and document.get("next_campaign_event_sequence") == 3
            and document.get("one_shot_start") is True
        ):
            _fail("SUPERVISOR_START body schema, keyset, or context changed")
        return document
    if frame_type == "WORKER_HANDOFF":
        if not (
            common
            and set(document) == set(SUPERVISOR_WORKER_HANDOFF_FIELDS)
            and document.get("schema") == SUPERVISOR_WORKER_HANDOFF_SCHEMA
            and type(document.get("worker_birth_event_sequence")) is int
            and document.get("next_campaign_event_sequence")
            == document["worker_birth_event_sequence"] + 1
            and document.get("one_shot_handoff") is True
        ):
            _fail("WORKER_HANDOFF body schema, keyset, or context changed")
        return document
    _fail("authenticated IPC frame type has no exact body contract")


@dataclass(frozen=True, slots=True)
class ProcessHandleV180R12R4:
    role: str
    pid: int
    pidfd: int
    pidfd_device: int
    pidfd_inode: int
    proc_starttime_ticks: int
    fdinfo_pid: int
    fdinfo_nspid: tuple[int, ...]
    cgroup_membership_line: str
    target_cgroup_fd: int
    target_cgroup_device: int
    target_cgroup_inode: int


class _CloneArgs(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_uint64),
        ("pidfd", ctypes.c_uint64),
        ("child_tid", ctypes.c_uint64),
        ("parent_tid", ctypes.c_uint64),
        ("exit_signal", ctypes.c_uint64),
        ("stack", ctypes.c_uint64),
        ("stack_size", ctypes.c_uint64),
        ("tls", ctypes.c_uint64),
        ("set_tid", ctypes.c_uint64),
        ("set_tid_size", ctypes.c_uint64),
        ("cgroup", ctypes.c_uint64),
    ]


def _single_threaded() -> bool:
    try:
        return len(os.listdir("/proc/self/task")) == 1
    except OSError:
        return False


def _proc_starttime(pid: int) -> int:
    raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    close = raw.rfind(")")
    fields = raw[close + 2 :].split()
    if close <= 0 or len(fields) < 20 or not fields[19].isdigit():
        _fail("/proc child stat did not expose one starttime")
    return int(fields[19])


def _pidfd_info(pidfd: int) -> tuple[int, tuple[int, ...]]:
    values: dict[str, str] = {}
    for line in Path(f"/proc/self/fdinfo/{pidfd}").read_text(encoding="ascii").splitlines():
        if ":" in line:
            name, value = line.split(":", 1)
            values[name] = value.strip()
    if not values.get("Pid", "").isdigit():
        _fail("pidfd fdinfo lacks one PID")
    nspid = tuple(int(value) for value in values.get("NSpid", "").split())
    if not nspid:
        _fail("pidfd fdinfo lacks one NSpid chain")
    return int(values["Pid"]), nspid


def _proc_cgroup(pid: int) -> str:
    rows = Path(f"/proc/{pid}/cgroup").read_text(encoding="ascii").splitlines()
    if len(rows) != 1 or not rows[0].startswith("0::/"):
        _fail("child cgroup namespace membership is not one cgroup-v2 row")
    return rows[0]


def _observe_child_exec_status_v180r12r4(status_read: int) -> None:
    """EOF proves execve closed CLOEXEC; four bytes preserve pre-exec errno."""

    received = bytearray()
    while len(received) < 4:
        chunk = os.read(status_read, 4 - len(received))
        if not chunk:
            break
        received.extend(chunk)
    if not received:
        return
    if len(received) != 4:
        raise OSError(errno.EIO, "child pre-exec status was truncated")
    child_errno = struct.unpack("!I", received)[0]
    if child_errno <= 0:
        child_errno = errno.EIO
    raise OSError(child_errno, os.strerror(child_errno))


class LinuxClone3V180R12R4:
    """Real atomic clone3+pidfd launcher; never used by focused tests."""

    clone3_number = 435
    pidfd_send_signal_number = 424

    def __init__(
        self, fault_injector: Callable[[str], None] | None = None
    ) -> None:
        if os.uname().machine != "x86_64" or not _single_threaded():
            _fail("real clone3 launch requires x86_64 and one observer thread")
        if fault_injector is not None and not callable(fault_injector):
            _fail("clone3 launch fault injector changed")
        self.libc = ctypes.CDLL(None, use_errno=True)
        self.libc.syscall.restype = ctypes.c_long
        self.fault_injector = fault_injector

    @staticmethod
    def validate_internal_exec_contract(
        *,
        role: str,
        argv: Sequence[str],
        env: Mapping[str, str],
        inherited_fd_map: Mapping[int, int],
    ) -> None:
        expected_target = role.lower() if role in INTERNAL_FD_TARGETS else None
        if (
            expected_target is None
            or type(argv) not in {tuple, list}
            or len(argv) != 11
            or tuple(argv[:6]) != INTERNAL_BOOTSTRAP_ARGV_PREFIX
            or argv[7] != expected_target
            or any(
                type(value) is not str
                or not value
                or "\x00" in value
                for value in argv
            )
            or any(not Path(argv[index]).is_absolute() for index in (6, 8, 9, 10))
            or set(env) != INTERNAL_INITIAL_ENV_KEYS
            or env.get("LC_CTYPE") != "C.UTF-8"
            or type(env.get("ACFQP_V180R12R4_LAUNCH_MANIFEST_SHA256")) is not str
            or len(env["ACFQP_V180R12R4_LAUNCH_MANIFEST_SHA256"]) != 64
            or any(
                char not in "0123456789abcdef"
                for char in env["ACFQP_V180R12R4_LAUNCH_MANIFEST_SHA256"]
            )
            or type(inherited_fd_map) is not dict
            or tuple(sorted(inherited_fd_map)) != INTERNAL_FD_TARGETS[role]
            or any(type(source) is not int or source < 3 for source in inherited_fd_map.values())
        ):
            _fail("internal clone3 exec argv/env/fixed-FD contract changed")

    def _cleanup_unreturned_child_v180r12r4(
        self, *, pid: int | None, pidfd: int
    ) -> None:
        """Best-effort kill/reap/close after birth but before handle return.

        A valid pidfd is sufficient ownership even when asynchronous delivery
        prevented ctypes from publishing clone3's positive PID result.  Every
        cleanup error is secondary to the launch primary held by the caller.
        """

        if pidfd >= 0:
            signal_result = -1
            try:
                signal_result = self.libc.syscall(
                    self.pidfd_send_signal_number,
                    pidfd,
                    signal.SIGKILL,
                    0,
                    0,
                )
            except BaseException:
                pass
            if signal_result != 0:
                fallback_pid = pid
                if fallback_pid is None:
                    try:
                        fallback_pid, _nspid = _pidfd_info(pidfd)
                    except BaseException:
                        fallback_pid = None
                if fallback_pid is not None:
                    try:
                        os.kill(fallback_pid, signal.SIGKILL)
                    except BaseException:
                        pass
            try:
                os.waitid(os.P_PIDFD, pidfd, os.WEXITED)
            except BaseException:
                if pid is not None:
                    try:
                        os.waitpid(pid, 0)
                    except BaseException:
                        pass
            try:
                os.close(pidfd)
            except BaseException:
                pass
            return
        if pid is not None:
            try:
                os.kill(pid, signal.SIGKILL)
            except BaseException:
                pass
            try:
                os.waitpid(pid, 0)
            except BaseException:
                pass

    def launch_exec(
        self,
        *,
        role: str,
        target_cgroup_fd: int,
        expected_cgroup_membership_line: str,
        argv: Sequence[str],
        env: Mapping[str, str],
        inherited_fd_map: Mapping[int, int],
        pre_clone_revalidate: Callable[[], None],
        address_space_cap_bytes: int = MEMORY_MAX_BYTES,
    ) -> ProcessHandleV180R12R4:
        self.validate_internal_exec_contract(
            role=role, argv=argv, env=env, inherited_fd_map=inherited_fd_map
        )
        if (
            type(expected_cgroup_membership_line) is not str
            or not expected_cgroup_membership_line.startswith("0::/")
            or not callable(pre_clone_revalidate)
        ):
            _fail("clone3 launch role or argv changed")
        fault_injector = getattr(self, "fault_injector", None)
        target_stat = _launch_boundary_v180r12r4(
            "TARGET_CGROUP_FSTAT",
            lambda: os.fstat(target_cgroup_fd),
            fault_injector=fault_injector,
        )
        status_read, status_write = _launch_boundary_v180r12r4(
            "EXEC_STATUS_PIPE",
            lambda: os.pipe2(os.O_CLOEXEC),
            fault_injector=fault_injector,
        )
        pidfd_cell = ctypes.c_int(-1)
        args = _CloneArgs()
        args.flags = CLONE_PIDFD | CLONE_INTO_CGROUP
        args.pidfd = ctypes.addressof(pidfd_cell)
        args.exit_signal = signal.SIGCHLD
        args.cgroup = target_cgroup_fd
        result: int | None = None
        pid: int | None = None
        pidfd = -1
        previous_alarm_mask: set[signal.Signals] | None = None
        alarm_mask_active = False
        try:
            # Keep the watchdog live through every pre-birth OS operation.
            # Only the final T3->clone3->ownership-publication window masks
            # SIGALRM in this one observer thread.  The callback remains the
            # last OS boundary before clone3.
            try:
                previous_alarm_mask = signal.pthread_sigmask(
                    signal.SIG_BLOCK, {signal.SIGALRM}
                )
                alarm_mask_active = True
            except BaseException as primary:
                _annotate_launch_primary_v180r12r4(
                    primary, "T3_IMMEDIATELY_BEFORE_CLONE3"
                )
                raise
            pre_clone_revalidate()
            result = _launch_boundary_v180r12r4(
                "CLONE3",
                lambda: self.libc.syscall(
                    self.clone3_number, ctypes.byref(args), ctypes.sizeof(args)
                ),
                fault_injector=fault_injector,
            )
            # No Python signal handler can run before all ownership facts have
            # crossed from ctypes memory into ordinary Python locals.
            clone_errno = ctypes.get_errno()
            pidfd = int(pidfd_cell.value)
            if result < 0:
                primary = OSError(clone_errno, os.strerror(clone_errno))
                _annotate_launch_primary_v180r12r4(primary, "CLONE3")
                raise primary
            if result == 0:
                # clone3 copied the blocked mask into the child.  Restore it
                # before even closing the unused pipe end or applying rlimits.
                try:
                    signal.pthread_sigmask(
                        signal.SIG_SETMASK, previous_alarm_mask
                    )
                    alarm_mask_active = False
                    os.close(status_read)
                    status_read = -1
                    resource.setrlimit(
                        resource.RLIMIT_AS,
                        (address_space_cap_bytes, address_space_cap_bytes),
                    )
                    temporary: dict[int, int] = {}
                    floor = max(
                        (*inherited_fd_map, *inherited_fd_map.values(), 255)
                    ) + 1
                    for target, source in inherited_fd_map.items():
                        temporary[target] = fcntl.fcntl(
                            source, fcntl.F_DUPFD_CLOEXEC, floor
                        )
                        floor = max(floor, temporary[target] + 1)
                    for target, source in temporary.items():
                        os.dup2(source, target, inheritable=True)
                    for descriptor in temporary.values():
                        os.close(descriptor)
                    os.execve(argv[0], list(argv), dict(env))
                except BaseException as child_error:
                    try:
                        child_errno = BaseException.__getattribute__(
                            child_error, "errno"
                        )
                    except BaseException:
                        child_errno = None
                    if type(child_errno) is not int or child_errno <= 0:
                        child_errno = errno.EIO
                    try:
                        os.write(status_write, struct.pack("!I", child_errno))
                    except BaseException:
                        pass
                    os._exit(127)
            pid = int(result)
            # The parent now owns both the positive child PID and any pidfd
            # written by clone3.  A pending SIGALRM may raise during this
            # restore, but the enclosing exception path can no longer lose
            # either ownership fact.
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_alarm_mask)
            alarm_mask_active = False
        except BaseException as primary:
            observed_pidfd = (
                pidfd if pidfd >= 0 else int(pidfd_cell.value)
            )
            observed_pid = pid
            child_created = observed_pid is not None or observed_pidfd >= 0
            pidfd_acquired = observed_pidfd >= 0
            _annotate_launch_primary_v180r12r4(
                primary,
                "CLONE3",
                child_created=child_created,
                pidfd_acquired=pidfd_acquired,
            )
            # Restore while ``primary`` is active so the watchdog records a
            # pending alarm as secondary instead of replacing it.
            if alarm_mask_active and previous_alarm_mask is not None:
                try:
                    signal.pthread_sigmask(
                        signal.SIG_SETMASK, previous_alarm_mask
                    )
                    alarm_mask_active = False
                except BaseException:
                    pass
            if child_created:
                self._cleanup_unreturned_child_v180r12r4(
                    pid=observed_pid, pidfd=observed_pidfd
                )
            for descriptor in (status_read, status_write):
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except BaseException:
                        pass
            raise
        os.close(status_write)
        status_write = -1
        try:
            if pidfd < 0:
                try:
                    os.kill(pid, signal.SIGKILL)
                finally:
                    os.waitpid(pid, 0)
                primary = V180R12R4RuntimeError(
                    "clone3 returned a PID without its required pidfd"
                )
                _annotate_launch_primary_v180r12r4(
                    primary, "PIDFD_ACQUISITION", child_created=True
                )
                raise primary

            def acquire_pidfd() -> os.stat_result:
                fcntl.fcntl(pidfd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)
                return os.fstat(pidfd)

            pidfd_stat = _launch_boundary_v180r12r4(
                "PIDFD_ACQUISITION",
                acquire_pidfd,
                fault_injector=fault_injector,
                child_created=True,
                pidfd_acquired=True,
            )

            _launch_boundary_v180r12r4(
                "CHILD_PREEXEC",
                lambda: _observe_child_exec_status_v180r12r4(status_read),
                fault_injector=fault_injector,
                child_created=True,
                pidfd_acquired=True,
            )
            os.close(status_read)
            status_read = -1

            def observe_child_identity() -> tuple[
                int, tuple[int, ...], int, str
            ]:
                observed_pid, observed_nspid = _pidfd_info(pidfd)
                return (
                    observed_pid,
                    observed_nspid,
                    _proc_starttime(pid),
                    _proc_cgroup(pid),
                )

            fdinfo_pid, nspid, starttime, membership = (
                _launch_boundary_v180r12r4(
                    "PROC_CHILD_IDENTITY_OBSERVATION",
                    observe_child_identity,
                    fault_injector=fault_injector,
                    child_created=True,
                    pidfd_acquired=True,
                    exec_observed=True,
                )
            )
            if fdinfo_pid != pid or nspid[0] != pid:
                _fail("clone3 pidfd anti-reuse identity disagrees with child PID")
            if membership != expected_cgroup_membership_line:
                _fail("clone3 child membership crossed its exact target leaf")
            return ProcessHandleV180R12R4(
                role,
                pid,
                pidfd,
                pidfd_stat.st_dev,
                pidfd_stat.st_ino,
                starttime,
                fdinfo_pid,
                nspid,
                membership,
                target_cgroup_fd,
                target_stat.st_dev,
                target_stat.st_ino,
            )
        except BaseException:
            # Once clone3 succeeds this launcher owns a live direct child even
            # when an anti-reuse observation fails.  Never lose that child
            # merely because a typed ProcessHandle could not be constructed.
            if pidfd >= 0:
                signal_result = -1
                try:
                    signal_result = self.libc.syscall(
                        self.pidfd_send_signal_number, pidfd, signal.SIGKILL, 0, 0
                    )
                    if signal_result != 0:
                        os.kill(pid, signal.SIGKILL)
                except BaseException:
                    pass
                try:
                    if signal_result == 0:
                        os.waitid(os.P_PIDFD, pidfd, os.WEXITED)
                    else:
                        os.waitpid(pid, 0)
                except BaseException:
                    pass
                try:
                    os.close(pidfd)
                except BaseException:
                    pass
            if status_read >= 0:
                try:
                    os.close(status_read)
                except BaseException:
                    pass
            raise

    def signal(self, handle: ProcessHandleV180R12R4, sig: int) -> None:
        result = self.libc.syscall(
            self.pidfd_send_signal_number, handle.pidfd, sig, 0, 0
        )
        if result != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))

    def reap(
        self,
        handle: ProcessHandleV180R12R4,
        *,
        deadline_ns: int,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> os.waitid_result:
        if (
            os.fstat(handle.pidfd).st_dev != handle.pidfd_device
            or os.fstat(handle.pidfd).st_ino != handle.pidfd_inode
            or _proc_starttime(handle.pid) != handle.proc_starttime_ticks
        ):
            _fail("pidfd/starttime identity changed before reap")
        poller = select.poll()
        poller.register(handle.pidfd, select.POLLIN | select.POLLHUP | select.POLLERR)
        while True:
            _check_campaign_deadline_v180r12r4(
                deadline_ns,
                monotonic_ns=monotonic_ns,
                boundary="pidfd wait",
            )
            remaining_ns = deadline_ns - monotonic_ns()
            timeout_ms = max(
                1, min(1_000, (remaining_ns + 999_999) // 1_000_000)
            )
            if not poller.poll(timeout_ms):
                continue
            result = os.waitid(
                os.P_PIDFD, handle.pidfd, os.WEXITED | os.WNOHANG
            )
            if result is None:
                continue
            if result.si_pid != handle.pid:
                _fail("waitid(P_PIDFD) did not reap the exact direct child")
            return result


def pidfd_birth_receipt_v180r12r4(
    *,
    topology: runtime.MeasurementCgroupTopologyReceiptV180R12R4,
    attempt_id: str,
    operation_id: str,
    handle: ProcessHandleV180R12R4,
    production_runtime_placement_t3: Mapping[str, Any] | None = None,
) -> runtime.PidfdBirthReceiptV180R12R4:
    """Turn independently observed clone3 facts into the exact typed receipt."""

    if type(handle) is not ProcessHandleV180R12R4:
        _fail("pidfd birth handle is mistyped")
    role = runtime.ProcessRoleV180R12R4(handle.role)
    target = (
        topology.supervisor_leaf
        if role is runtime.ProcessRoleV180R12R4.SUPERVISOR
        else topology.worker_leaf
    )
    if (
        handle.target_cgroup_fd != target.directory_fd
        or handle.target_cgroup_device != target.device
        or handle.target_cgroup_inode != target.inode
        or handle.cgroup_membership_line != f"0::{target.membership_path}"
    ):
        _fail("pidfd birth handle crossed its typed topology leaf")
    return runtime.PidfdBirthReceiptV180R12R4(
        topology,
        attempt_id,
        operation_id,
        role,
        handle.pid,
        handle.pidfd,
        handle.pidfd_device,
        handle.pidfd_inode,
        ("CLONE_INTO_CGROUP", "CLONE_PIDFD"),
        handle.target_cgroup_fd,
        handle.target_cgroup_device,
        handle.target_cgroup_inode,
        target.path,
        handle.proc_starttime_ticks,
        handle.fdinfo_pid,
        handle.fdinfo_nspid,
        handle.cgroup_membership_line,
        True,
        bool(fcntl.fcntl(handle.pidfd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC),
        _thaw_json_value(production_runtime_placement_t3),
    )


def pidfd_reap_receipt_v180r12r4(
    *,
    launcher: LinuxClone3V180R12R4,
    handle: ProcessHandleV180R12R4,
    birth_receipt: runtime.PidfdBirthReceiptV180R12R4,
    leaf_directory_fd: int,
    deadline_ns: int,
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
) -> runtime.PidfdReapReceiptV180R12R4:
    """waitid(P_PIDFD), then prove the exact target leaf is empty."""

    result = launcher.reap(
        handle, deadline_ns=deadline_ns, monotonic_ns=monotonic_ns
    )
    _check_campaign_deadline_v180r12r4(
        deadline_ns,
        monotonic_ns=monotonic_ns,
        boundary="pidfd reap receipt observation",
    )
    poller = select.poll()
    poller.register(handle.pidfd, select.POLLIN)
    readable = bool(poller.poll(0))
    events = LinuxCgroupV2V180R12R4._read_at(
        leaf_directory_fd, "cgroup.events"
    )
    populated_rows = dict(
        line.split(" ", 1) for line in events.splitlines() if line
    )
    processes = LinuxCgroupV2V180R12R4._read_at(
        leaf_directory_fd, "cgroup.procs"
    )
    process_count = len([line for line in processes.splitlines() if line])
    code = "CLD_EXITED" if result.si_code == os.CLD_EXITED else str(result.si_code)
    return runtime.PidfdReapReceiptV180R12R4(
        birth_receipt,
        birth_receipt.operation_id,
        handle.pidfd_device,
        handle.pidfd_inode,
        handle.proc_starttime_ticks,
        "P_PIDFD",
        handle.pidfd,
        code,
        result.si_status,
        readable,
        populated_rows.get("populated") == "1",
        process_count,
    )


def close_reaped_pidfd_v180r12r4(handle: ProcessHandleV180R12R4) -> None:
    """Close one reaped child's original pidfd after its receipt event ACK.

    Receipt construction deliberately leaves the descriptor live so the
    observer can durably ACK the anti-reuse evidence first.  This helper is the
    sole success-path close point and validates the same OFD immediately before
    closing it.
    """

    if type(handle) is not ProcessHandleV180R12R4:
        _fail("reaped pidfd close requires one exact process handle")
    metadata = os.fstat(handle.pidfd)
    if (
        metadata.st_dev != handle.pidfd_device
        or metadata.st_ino != handle.pidfd_inode
    ):
        _fail("reaped pidfd identity changed before its exact close")
    os.close(handle.pidfd)


@dataclass(frozen=True, slots=True)
class CgroupTreeV180R12R4:
    parent_path: Path
    root_path: Path
    supervisor_path: Path
    worker_path: Path
    root_fd: int
    supervisor_fd: int
    worker_fd: int
    parent_fd: int
    mount_fd: int
    source_service_fd: int
    retained_control_fds: tuple[tuple[str, str, int, int, int], ...]
    topology_receipt: runtime.MeasurementCgroupTopologyReceiptV180R12R4


class V180R12R4PartialCgroupCreateFailure(V180R12R4RuntimeError):
    """An owned partial tree could not be fully removed during create failure."""

    def __init__(
        self,
        cleanup_errors: Sequence[str],
        node_observations: Sequence[Mapping[str, Any]],
    ) -> None:
        super().__init__("partial cgroup create cleanup failed")
        self.cleanup_errors = tuple(cleanup_errors)
        self.node_observations = tuple(dict(row) for row in node_observations)


class LinuxCgroupV2V180R12R4:
    """Real fresh empty-root/sibling-leaf cgroup-v2 controller."""

    retained_names = (
        ("MEASUREMENT_ROOT", "cgroup.events"),
        ("MEASUREMENT_ROOT", "cgroup.procs"),
        ("MEASUREMENT_ROOT", "memory.events"),
        ("MEASUREMENT_ROOT", "memory.max"),
        ("MEASUREMENT_ROOT", "memory.peak"),
        ("MEASUREMENT_ROOT", "pids.events"),
        ("MEASUREMENT_ROOT", "pids.max"),
        ("MEASUREMENT_ROOT", "pids.peak"),
        ("SUPERVISOR", "cgroup.events"),
        ("SUPERVISOR", "cgroup.procs"),
        ("SUPERVISOR", "pids.max"),
        ("WORKER", "cgroup.events"),
        ("WORKER", "cgroup.procs"),
        ("WORKER", "pids.max"),
    )

    def __init__(self, fault_injector: Callable[[str], None] | None = None) -> None:
        if fault_injector is not None and not callable(fault_injector):
            _fail("cgroup fault injector must be callable")
        self.fault_injector = fault_injector

    def _checkpoint(self, name: str) -> None:
        if self.fault_injector is not None:
            self.fault_injector(name)

    @staticmethod
    def _open_absolute_directory(path_text: str) -> int:
        path = PurePosixPath(path_text)
        if (
            not path.is_absolute()
            or path.as_posix() != path_text
            or "//" in path_text
            or any(part in {"", ".", ".."} for part in path.parts[1:])
        ):
            _fail("cgroup directory path is not canonical absolute POSIX")
        current = os.open(
            "/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        try:
            for part in path.parts[1:]:
                successor = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=current,
                )
                os.close(current)
                current = successor
            return current
        except BaseException:
            os.close(current)
            raise

    @staticmethod
    def _membership_for_filesystem_path(
        mount_point: str, filesystem_path: str
    ) -> str:
        """Translate one cgroup2 mount path into its namespace membership path.

        The observer may live outside the delegated parent, so its own
        ``/proc/self/cgroup`` line is not an authority for this translation.
        """

        mount = PurePosixPath(mount_point)
        path = PurePosixPath(filesystem_path)
        if (
            not mount.is_absolute()
            or not path.is_absolute()
            or mount.as_posix() != mount_point
            or path.as_posix() != filesystem_path
        ):
            _fail("cgroup mount or delegated path is non-canonical")
        try:
            relative = path.relative_to(mount)
        except ValueError as error:
            raise V180R12R4RuntimeError(
                "delegated cgroup parent is outside its bound cgroup2 mount"
            ) from error
        return "/" if not relative.parts else "/" + relative.as_posix()

    @staticmethod
    def _fstatfs_type(descriptor: int) -> int:
        libc = ctypes.CDLL(None, use_errno=True)
        buffer = ctypes.create_string_buffer(256)
        if libc.fstatfs(descriptor, ctypes.byref(buffer)) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
        return ctypes.c_long.from_buffer(buffer).value

    @staticmethod
    def _open_file(directory_fd: int, name: str, flags: int = os.O_RDONLY) -> int:
        if "/" in name or name in {"", ".", ".."}:
            _fail("cgroup control basename is malformed")
        return os.open(
            name, flags | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory_fd
        )

    @classmethod
    def _read_at(cls, directory_fd: int, name: str, byte_cap: int = 1024 * 1024) -> str:
        descriptor = cls._open_file(directory_fd, name)
        try:
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = os.read(descriptor, min(64 * 1024, byte_cap + 1 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > byte_cap:
                    _fail(f"cgroup {name} exceeded its bounded read cap")
            return b"".join(chunks).decode("ascii")
        finally:
            os.close(descriptor)

    @classmethod
    def _write_at(cls, directory_fd: int, name: str, value: str) -> None:
        descriptor = cls._open_file(directory_fd, name, os.O_WRONLY)
        try:
            raw = value.encode("ascii")
            if os.write(descriptor, raw) != len(raw):
                _fail(f"cgroup control write made partial progress: {name}")
        finally:
            os.close(descriptor)

    @staticmethod
    def _node(
        role: str,
        path: str,
        parent_path: str | None,
        membership_path: str,
        parent_membership_path: str | None,
        descriptor: int,
    ) -> runtime.CgroupNodeIdentityV180R12R4:
        metadata = os.fstat(descriptor)
        return runtime.CgroupNodeIdentityV180R12R4(
            role,
            path,
            parent_path,
            membership_path,
            parent_membership_path,
            descriptor,
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_mode,
            metadata.st_nlink,
            bool(fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC),
            True,
        )

    @staticmethod
    def _read_fd(descriptor: int) -> str:
        os.lseek(descriptor, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
            if sum(map(len, chunks)) > 1024 * 1024:
                _fail("cgroup retained control read exceeded 1MiB")
        return b"".join(chunks).decode("ascii")

    @classmethod
    def _observe_programmed_limits(
        cls, root_fd: int, supervisor_fd: int, worker_fd: int
    ) -> dict[str, Any]:
        raw = {
            "controllers": sorted(
                cls._read_at(root_fd, "cgroup.controllers").split()
            ),
            "subtree_control": sorted(
                cls._read_at(root_fd, "cgroup.subtree_control").split()
            ),
            "root_memory_max": cls._read_at(root_fd, "memory.max").strip(),
            "root_pids_max": cls._read_at(root_fd, "pids.max").strip(),
            "supervisor_pids_max": cls._read_at(
                supervisor_fd, "pids.max"
            ).strip(),
            "worker_pids_max": cls._read_at(worker_fd, "pids.max").strip(),
        }
        if (
            not raw["controllers"]
            or len(raw["controllers"]) != len(set(raw["controllers"]))
            or len(raw["subtree_control"]) != len(set(raw["subtree_control"]))
            or any(
                type(value) is not str or not value
                for value in (*raw["controllers"], *raw["subtree_control"])
            )
            or any(
                type(raw[name]) is not str or not raw[name].isdigit()
                for name in (
                    "root_memory_max", "root_pids_max",
                    "supervisor_pids_max", "worker_pids_max",
                )
            )
        ):
            _fail("cgroup-v2 programmed property framing changed")
        return {
            "controllers": raw["controllers"],
            "subtree_control": raw["subtree_control"],
            "root_memory_max_bytes": int(raw["root_memory_max"]),
            "root_pids_max": int(raw["root_pids_max"]),
            "supervisor_leaf_pids_max": int(raw["supervisor_pids_max"]),
            "worker_leaf_pids_max": int(raw["worker_pids_max"]),
        }

    @classmethod
    def _validate_programmed_limits(
        cls, root_fd: int, supervisor_fd: int, worker_fd: int
    ) -> None:
        observed = cls._observe_programmed_limits(
            root_fd, supervisor_fd, worker_fd
        )
        if (
            not {"memory", "pids"}.issubset(observed["controllers"])
            or observed["subtree_control"] != ["memory", "pids"]
            or observed["root_memory_max_bytes"] != MEMORY_MAX_BYTES
            or observed["root_pids_max"] != PIDS_MAX
            or observed["supervisor_leaf_pids_max"] != 1
            or observed["worker_leaf_pids_max"] != 1
        ):
            _fail("cgroup-v2 caps/controllers drifted before process birth")

    @staticmethod
    def _safe_error_parts(error: BaseException) -> tuple[str, str]:
        try:
            error_type = type.__getattribute__(type(error), "__name__")
        except BaseException:
            error_type = "BaseException"
        return error_type, _bounded_exception_text(error)[:512]

    @classmethod
    def _partial_node_row(
        cls,
        *,
        role: str,
        path: str,
        parent_fd: int,
        basename: str,
    ) -> dict[str, Any]:
        """Observe one cleanup-time cgroup path without following aliases."""

        try:
            metadata = os.stat(basename, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return runtime.FailureCgroupNodeObservationV180R12R4(
                role, path, "ABSENT", None, None, None, None, None, None,
                None, None,
            ).to_document()
        except BaseException as error:
            error_type, message = cls._safe_error_parts(error)
            return runtime.FailureCgroupNodeObservationV180R12R4(
                role, path, "READ_ERROR", None, None, None, None, None, None,
                error_type, message,
            ).to_document()
        if not stat.S_ISDIR(metadata.st_mode):
            return runtime.FailureCgroupNodeObservationV180R12R4(
                role, path, "LINKED_OR_NONDIR", metadata.st_mode,
                metadata.st_nlink, metadata.st_dev, metadata.st_ino, None,
                None, None, None,
            ).to_document()
        descriptor = -1
        try:
            descriptor = os.open(
                basename,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=parent_fd,
            )
            reopened = os.fstat(descriptor)
            if (
                reopened.st_mode != metadata.st_mode
                or reopened.st_nlink != metadata.st_nlink
                or reopened.st_dev != metadata.st_dev
                or reopened.st_ino != metadata.st_ino
            ):
                _fail("partial cgroup path changed while it was observed")
            events = dict(
                line.split(" ", 1)
                for line in cls._read_at(
                    descriptor, "cgroup.events", byte_cap=64 * 1024
                ).splitlines()
                if line
            )
            process_lines = tuple(
                line
                for line in cls._read_at(
                    descriptor, "cgroup.procs", byte_cap=64 * 1024
                ).splitlines()
                if line
            )
            if events.get("populated") not in {"0", "1"}:
                _fail("partial cgroup populated observation is malformed")
            return runtime.FailureCgroupNodeObservationV180R12R4(
                role, path, "PRESENT", reopened.st_mode, reopened.st_nlink,
                reopened.st_dev, reopened.st_ino,
                int(events["populated"]), len(process_lines), None, None,
            ).to_document()
        except BaseException as error:
            error_type, message = cls._safe_error_parts(error)
            return runtime.FailureCgroupNodeObservationV180R12R4(
                role, path, "READ_ERROR", metadata.st_mode,
                metadata.st_nlink, metadata.st_dev, metadata.st_ino, None,
                None, error_type, message,
            ).to_document()
        finally:
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass

    @classmethod
    def _observe_partial_tree_after_cleanup(
        cls,
        *,
        parent_fd: int,
        root_name: str,
        root_path: str,
        supervisor_path: str,
        worker_path: str,
    ) -> tuple[dict[str, Any], ...]:
        root = cls._partial_node_row(
            role="MEASUREMENT_ROOT",
            path=root_path,
            parent_fd=parent_fd,
            basename=root_name,
        )
        if root["state"] == "ABSENT":
            leaves = tuple(
                runtime.FailureCgroupNodeObservationV180R12R4(
                    role, path, "ABSENT", None, None, None, None, None, None,
                    None, None,
                ).to_document()
                for role, path in (
                    ("SUPERVISOR", supervisor_path),
                    ("WORKER", worker_path),
                )
            )
            return (root, *leaves)
        root_descriptor = -1
        try:
            root_descriptor = os.open(
                root_name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=parent_fd,
            )
        except BaseException as error:
            error_type, message = cls._safe_error_parts(error)
            leaves = tuple(
                runtime.FailureCgroupNodeObservationV180R12R4(
                    role, path, "READ_ERROR", None, None, None, None, None,
                    None, error_type, message,
                ).to_document()
                for role, path in (
                    ("SUPERVISOR", supervisor_path),
                    ("WORKER", worker_path),
                )
            )
            return (root, *leaves)
        try:
            supervisor = cls._partial_node_row(
                role="SUPERVISOR",
                path=supervisor_path,
                parent_fd=root_descriptor,
                basename="SUPERVISOR",
            )
            worker = cls._partial_node_row(
                role="WORKER",
                path=worker_path,
                parent_fd=root_descriptor,
                basename="WORKER",
            )
            return (root, supervisor, worker)
        finally:
            os.close(root_descriptor)

    def create(
        self,
        cgroup_parent_fact: Mapping[str, Any],
        attempt_id: str,
        *,
        parent_fd: int = DELEGATED_CGROUP_PARENT_FD,
        mount_fd: int = CGROUP2_MOUNT_FD,
        source_service_fd: int = SOURCE_SYSTEMD_SERVICE_FD,
        production_runtime_placement_t1: Mapping[str, Any] | None = None,
        production_runtime_placement_t2: Mapping[str, Any] | None = None,
    ) -> CgroupTreeV180R12R4:
        if len(attempt_id) != 64 or any(char not in "0123456789abcdef" for char in attempt_id):
            _fail("cgroup attempt ID is malformed")
        parent_fact = protocol.validate_cgroup_parent_fact_v180r12r4(
            cgroup_parent_fact
        )
        if (
            parent_fd != DELEGATED_CGROUP_PARENT_FD
            or mount_fd != CGROUP2_MOUNT_FD
            or source_service_fd != SOURCE_SYSTEMD_SERVICE_FD
        ):
            _fail("cgroup create requires exact inherited external OFD numbers")
        parent_path = parent_fact["parent_path"]
        root_name = f"v180r12r4-{attempt_id}"
        root_path = f"{parent_path}/{root_name}"
        supervisor_path = f"{root_path}/SUPERVISOR"
        worker_path = f"{root_path}/WORKER"
        parent_membership = self._membership_for_filesystem_path(
            parent_fact["mount_point"], parent_path
        )
        root_membership = (
            f"/{root_name}" if parent_membership == "/" else f"{parent_membership}/{root_name}"
        )
        supervisor_membership = f"{root_membership}/SUPERVISOR"
        worker_membership = f"{root_membership}/WORKER"
        root_fd = supervisor_fd = worker_fd = -1
        retained: list[tuple[str, str, int, int, int]] = []
        root_created = supervisor_created = worker_created = False
        try:
            mount_stat = os.fstat(mount_fd)
            parent_stat = os.fstat(parent_fd)
            if (
                self._fstatfs_type(mount_fd) != CGROUP2_SUPER_MAGIC
                or self._fstatfs_type(parent_fd) != CGROUP2_SUPER_MAGIC
                or mount_stat.st_dev != parent_fact["mount_device"]
                or mount_stat.st_ino != parent_fact["mount_inode"]
                or parent_stat.st_dev != parent_fact["parent_device"]
                or parent_stat.st_ino != parent_fact["parent_inode"]
                or parent_stat.st_uid != parent_fact["owner_uid"]
                or parent_stat.st_gid != parent_fact["owner_gid"]
                or stat.S_IMODE(parent_stat.st_mode) != parent_fact["mode"]
                or sorted(self._read_at(parent_fd, "cgroup.controllers").split())
                != parent_fact["controllers"]
                or sorted(self._read_at(parent_fd, "cgroup.subtree_control").split())
                != parent_fact["subtree_control"]
                or self._read_at(parent_fd, "cgroup.type").strip()
                != parent_fact["cgroup_type"]
                or os.stat("/proc/self/ns/cgroup").st_ino
                != parent_fact["cgroup_namespace_inode"]
                or _fd_canonical_path(mount_fd, "cgroup2 mount")
                != parent_fact["mount_point"]
                or _fd_canonical_path(parent_fd, "delegated cgroup parent")
                != parent_path
            ):
                _fail("delegated cgroup parent drifted before fresh mkdir")
            for name in (
                "cgroup.events", "memory.events", "pids.events", "cgroup.kill",
                "cgroup.procs", "memory.peak", "pids.peak",
            ):
                metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                if not stat.S_ISREG(metadata.st_mode):
                    _fail(f"delegated cgroup parent surface is non-regular: {name}")
            self._checkpoint("PARENT_VERIFIED")

            os.mkdir(root_name, 0o700, dir_fd=parent_fd)
            root_created = True
            root_fd = os.open(
                root_name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=parent_fd,
            )
            self._checkpoint("ROOT_OPENED")
            if self._read_at(root_fd, "cgroup.procs") != "":
                _fail("fresh measurement root is not empty")
            self._write_at(root_fd, "memory.max", str(MEMORY_MAX_BYTES))
            self._write_at(root_fd, "pids.max", str(PIDS_MAX))
            self._write_at(root_fd, "cgroup.subtree_control", "+memory +pids")
            os.mkdir("SUPERVISOR", 0o700, dir_fd=root_fd)
            supervisor_created = True
            os.mkdir("WORKER", 0o700, dir_fd=root_fd)
            worker_created = True
            supervisor_fd = os.open(
                "SUPERVISOR",
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=root_fd,
            )
            worker_fd = os.open(
                "WORKER",
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=root_fd,
            )
            if worker_fd != 245:
                os.dup2(worker_fd, 245, inheritable=False)
                os.close(worker_fd)
                worker_fd = 245
            self._write_at(supervisor_fd, "pids.max", "1")
            self._write_at(worker_fd, "pids.max", "1")
            programmed = self._observe_programmed_limits(
                root_fd, supervisor_fd, worker_fd
            )
            populated_values: list[int] = []
            process_counts: list[int] = []
            for descriptor in (root_fd, supervisor_fd, worker_fd):
                events = dict(
                    line.split(" ", 1)
                    for line in self._read_at(descriptor, "cgroup.events").splitlines()
                    if line
                )
                populated = events.get("populated")
                processes = tuple(
                    row
                    for row in self._read_at(
                        descriptor, "cgroup.procs"
                    ).splitlines()
                    if row
                )
                if populated not in {"0", "1"} or any(
                    not row.isdigit() for row in processes
                ):
                    _fail("fresh cgroup population property framing changed")
                populated_values.append(int(populated))
                process_counts.append(len(processes))
            self._checkpoint("LEAVES_OPENED")

            nodes = {
                "DELEGATED_PARENT": self._node(
                    "DELEGATED_PARENT",
                    parent_path,
                    parent_fact["mount_point"],
                    parent_membership,
                    parent_membership.rsplit("/", 1)[0] or "/",
                    parent_fd,
                ),
                "MEASUREMENT_ROOT": self._node(
                    "MEASUREMENT_ROOT", root_path, parent_path,
                    root_membership, parent_membership, root_fd,
                ),
                "SUPERVISOR": self._node(
                    "SUPERVISOR", supervisor_path, root_path,
                    supervisor_membership, root_membership, supervisor_fd,
                ),
                "WORKER": self._node(
                    "WORKER", worker_path, root_path,
                    worker_membership, root_membership, worker_fd,
                ),
            }
            by_role = {
                "MEASUREMENT_ROOT": root_fd,
                "SUPERVISOR": supervisor_fd,
                "WORKER": worker_fd,
            }
            control_receipts: list[runtime.CgroupControlFileOFDV180R12R4] = []
            for role, name in self.retained_names:
                descriptor = self._open_file(by_role[role], name)
                metadata = os.fstat(descriptor)
                retained.append((role, name, descriptor, metadata.st_dev, metadata.st_ino))
                control_receipts.append(
                    runtime.CgroupControlFileOFDV180R12R4(
                        role, name, descriptor, metadata.st_dev, metadata.st_ino,
                        metadata.st_mode, metadata.st_nlink,
                        bool(fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC),
                        True, True,
                    )
                )
            topology = runtime.MeasurementCgroupTopologyReceiptV180R12R4(
                parent_fact,
                nodes["DELEGATED_PARENT"],
                nodes["MEASUREMENT_ROOT"],
                nodes["SUPERVISOR"],
                nodes["WORKER"],
                "cgroup2",
                tuple(programmed["controllers"]),
                tuple(programmed["subtree_control"]),
                programmed["root_memory_max_bytes"],
                programmed["root_pids_max"],
                programmed["supervisor_leaf_pids_max"],
                programmed["worker_leaf_pids_max"],
                bool(populated_values[0]),
                process_counts[0],
                tuple(process_counts[1:]),
                tuple(control_receipts),
                _thaw_json_value(production_runtime_placement_t1),
                _thaw_json_value(production_runtime_placement_t2),
            )
            self._checkpoint("TOPOLOGY_FROZEN")
            return CgroupTreeV180R12R4(
                Path(parent_path), Path(root_path), Path(supervisor_path), Path(worker_path),
                root_fd, supervisor_fd, worker_fd, parent_fd, mount_fd,
                source_service_fd, tuple(retained), topology,
            )
        except BaseException as primary:
            cleanup_errors: list[str] = []
            for _role, _name, descriptor, _device, _inode in reversed(retained):
                try:
                    os.close(descriptor)
                except OSError as error:
                    cleanup_errors.append(_bounded_exception_text(error))
            for descriptor in (worker_fd, supervisor_fd):
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except OSError as error:
                        cleanup_errors.append(_bounded_exception_text(error))
            if root_fd >= 0:
                if worker_created:
                    try:
                        os.rmdir("WORKER", dir_fd=root_fd)
                    except OSError as error:
                        cleanup_errors.append(_bounded_exception_text(error))
                if supervisor_created:
                    try:
                        os.rmdir("SUPERVISOR", dir_fd=root_fd)
                    except OSError as error:
                        cleanup_errors.append(_bounded_exception_text(error))
                try:
                    os.close(root_fd)
                except OSError as error:
                    cleanup_errors.append(_bounded_exception_text(error))
            if root_created:
                try:
                    os.rmdir(root_name, dir_fd=parent_fd)
                except OSError as error:
                    cleanup_errors.append(_bounded_exception_text(error))
            if cleanup_errors:
                node_observations = self._observe_partial_tree_after_cleanup(
                    parent_fd=parent_fd,
                    root_name=root_name,
                    root_path=root_path,
                    supervisor_path=supervisor_path,
                    worker_path=worker_path,
                )
                for descriptor in (
                    source_service_fd,
                    mount_fd,
                    parent_fd,
                ):
                    try:
                        os.close(descriptor)
                    except OSError as error:
                        cleanup_errors.append(_bounded_exception_text(error))
                raise V180R12R4PartialCgroupCreateFailure(
                    cleanup_errors, node_observations
                ) from primary
            for descriptor in (source_service_fd, mount_fd, parent_fd):
                try:
                    os.close(descriptor)
                except OSError as error:
                    try:
                        inherited = BaseException.__getattribute__(
                            primary, "cleanup_errors"
                        )
                    except BaseException:
                        inherited = ()
                    if type(inherited) is not tuple:
                        inherited = ()
                    try:
                        BaseException.__setattr__(
                            primary,
                            "cleanup_errors",
                            (*inherited, _bounded_exception_text(error)),
                        )
                    except BaseException:
                        pass
            raise

    def observe(self, tree: CgroupTreeV180R12R4) -> dict[str, str]:
        observations: dict[str, str] = {}
        for role, name, descriptor, device, inode in tree.retained_control_fds:
            metadata = os.fstat(descriptor)
            if metadata.st_dev != device or metadata.st_ino != inode:
                _fail("retained cgroup control OFD identity changed")
            observations[f"{role}:{name}"] = self._read_fd(descriptor)
        return observations

    def observe_receipt(
        self,
        tree: CgroupTreeV180R12R4,
        *,
        supervisor_reap_receipt: runtime.PidfdReapReceiptV180R12R4,
        worker_reap_receipt: runtime.PidfdReapReceiptV180R12R4,
        operation_id: str,
    ) -> runtime.CgroupV2ObservationReceiptV180R12R4:
        """Read every retained OFD once and construct the exact success receipt."""

        values = self.observe(tree)

        def counter_rows(raw: str) -> tuple[tuple[str, int], ...]:
            rows: list[tuple[str, int]] = []
            for line in raw.splitlines():
                parts = line.split(" ")
                if len(parts) != 2 or not parts[0] or not parts[1].isdigit():
                    _fail("retained cgroup counter file is malformed")
                rows.append((parts[0], int(parts[1])))
            result = tuple(sorted(rows))
            if len({name for name, _value in result}) != len(result):
                _fail("retained cgroup counter names repeat")
            return result

        control_by_key = {
            (row.node_role, row.name): row
            for row in tree.topology_receipt.control_files
        }
        readbacks = tuple(
            runtime.CgroupControlFileReadbackV180R12R4(
                control_by_key[(role, name)],
                values[f"{role}:{name}"],
                True,
                True,
                True,
            )
            for role, name in self.retained_names
        )
        populated: list[tuple[str, int]] = []
        process_counts: list[tuple[str, int]] = []
        for role in ("MEASUREMENT_ROOT", "SUPERVISOR", "WORKER"):
            events = dict(
                line.split(" ", 1)
                for line in values[f"{role}:cgroup.events"].splitlines()
                if line
            )
            if events.get("populated") not in {"0", "1"}:
                _fail("retained cgroup populated state is malformed")
            populated.append((role, int(events["populated"])))
            process_counts.append(
                (
                    role,
                    len(
                        [
                            row
                            for row in values[f"{role}:cgroup.procs"].splitlines()
                            if row
                        ]
                    ),
                )
            )
        memory_peak = values["MEASUREMENT_ROOT:memory.peak"].strip()
        pids_peak = values["MEASUREMENT_ROOT:pids.peak"].strip()
        if not memory_peak.isdigit() or not pids_peak.isdigit():
            _fail("retained cgroup peak value is malformed")
        return runtime.CgroupV2ObservationReceiptV180R12R4(
            tree.topology_receipt,
            supervisor_reap_receipt,
            worker_reap_receipt,
            operation_id,
            int(memory_peak),
            int(pids_peak),
            counter_rows(values["MEASUREMENT_ROOT:memory.events"]),
            counter_rows(values["MEASUREMENT_ROOT:pids.events"]),
            tuple(populated),
            tuple(process_counts),
            readbacks,
            True,
        )

    def observe_failure(self, tree: CgroupTreeV180R12R4) -> dict[str, Any]:
        """Best-effort bounded raw observation; never a success receipt."""

        raw: dict[str, Any] = {
            "root_populated": None,
            "supervisor_leaf_populated": None,
            "worker_leaf_populated": None,
            "root_process_count": None,
            "supervisor_leaf_process_count": None,
            "worker_leaf_process_count": None,
            "memory_peak_bytes": None,
            "pids_peak": None,
            "memory_events": None,
            "pids_events": None,
            "observation_errors": [],
        }
        try:
            values = self.observe(tree)
        except BaseException as error:
            raw["observation_errors"].append(_bounded_exception_text(error)[:512])
            return raw

        def parse_events(value: str) -> tuple[tuple[str, int], ...]:
            rows: list[tuple[str, int]] = []
            for line in value.splitlines():
                parts = line.split(" ")
                if len(parts) != 2 or not parts[0] or not parts[1].isdigit():
                    _fail("failure cgroup counter row is malformed")
                rows.append((parts[0], int(parts[1])))
            result = tuple(sorted(rows))
            if len({name for name, _count in result}) != len(result):
                _fail("failure cgroup counter name repeats")
            return result

        roles = ("MEASUREMENT_ROOT", "SUPERVISOR", "WORKER")
        populated_keys = (
            "root_populated", "supervisor_leaf_populated", "worker_leaf_populated"
        )
        process_keys = (
            "root_process_count", "supervisor_leaf_process_count",
            "worker_leaf_process_count",
        )
        for role, populated_key, process_key in zip(
            roles, populated_keys, process_keys
        ):
            try:
                events = dict(
                    line.split(" ", 1)
                    for line in values[f"{role}:cgroup.events"].splitlines()
                    if line
                )
                populated = events.get("populated")
                if populated not in {"0", "1"}:
                    _fail("failure cgroup populated counter is malformed")
                raw[populated_key] = int(populated)
                raw[process_key] = len(
                    [
                        line
                        for line in values[f"{role}:cgroup.procs"].splitlines()
                        if line
                    ]
                )
            except BaseException as error:
                raw["observation_errors"].append(
                    f"{role}:" + _bounded_exception_text(error)[:400]
                )
        for destination, source in (
            ("memory_peak_bytes", "MEASUREMENT_ROOT:memory.peak"),
            ("pids_peak", "MEASUREMENT_ROOT:pids.peak"),
        ):
            try:
                value = values[source].strip()
                if not value.isdigit():
                    _fail("failure cgroup peak is malformed")
                raw[destination] = int(value)
            except BaseException as error:
                raw["observation_errors"].append(
                    f"{source}:" + _bounded_exception_text(error)[:400]
                )
        for destination, source in (
            ("memory_events", "MEASUREMENT_ROOT:memory.events"),
            ("pids_events", "MEASUREMENT_ROOT:pids.events"),
        ):
            try:
                raw[destination] = parse_events(values[source])
            except BaseException as error:
                raw["observation_errors"].append(
                    f"{source}:" + _bounded_exception_text(error)[:400]
                )
        raw["observation_errors"] = raw["observation_errors"][:32]
        return raw

    def kill(self, tree: CgroupTreeV180R12R4) -> None:
        self._write_at(tree.root_fd, "cgroup.kill", "1")

    def close(self, tree: CgroupTreeV180R12R4) -> None:
        primary: BaseException | None = None
        primary_traceback = None
        secondary: list[str] = []

        def attempt(label: str, operation: Callable[[], None]) -> None:
            nonlocal primary, primary_traceback
            try:
                operation()
            except BaseException as error:
                if primary is None:
                    primary = error
                    primary_traceback = error.__traceback__
                else:
                    secondary.append(label + ":" + _bounded_exception_text(error))

        for role, name, descriptor, _device, _inode in tree.retained_control_fds:
            attempt(
                f"retained:{role}:{name}",
                lambda descriptor=descriptor: os.close(descriptor),
            )
        attempt("supervisor_fd", lambda: os.close(tree.supervisor_fd))
        attempt("worker_fd", lambda: os.close(tree.worker_fd))
        attempt(
            "supervisor_rmdir",
            lambda: os.rmdir("SUPERVISOR", dir_fd=tree.root_fd),
        )
        attempt(
            "worker_rmdir",
            lambda: os.rmdir("WORKER", dir_fd=tree.root_fd),
        )
        attempt("root_fd", lambda: os.close(tree.root_fd))
        attempt(
            "root_rmdir",
            lambda: os.rmdir(tree.root_path.name, dir_fd=tree.parent_fd),
        )
        attempt("source_service_fd", lambda: os.close(tree.source_service_fd))
        attempt("mount_fd", lambda: os.close(tree.mount_fd))
        attempt("parent_fd", lambda: os.close(tree.parent_fd))
        if primary is not None:
            if secondary:
                try:
                    BaseException.__setattr__(
                        primary, "cleanup_errors", tuple(secondary[:32])
                    )
                except BaseException:
                    pass
            raise primary.with_traceback(primary_traceback)


class TypedWireEvidenceRegistryV180R12R4:
    """Rehydrate authenticated wire evidence into its exact native type.

    Runtime-owned receipts deliberately cannot be registered as generic JSON.
    This registry reconstructs them through their normal validating
    constructors, using only causally earlier registered dependencies, and then
    requires an exact canonical-byte round trip.  Hidden input/subject bytes are
    independently retained by the observer and are never accepted from a child
    receipt as authority.
    """

    def __init__(
        self,
    ) -> None:
        self.objects_by_id: dict[str, Any] = {}
        self.documents_by_id: dict[str, dict[str, Any]] = {}
        self._snapshot_bytes_by_id: dict[str, bytes] = {}
        self._consumed_snapshot_transport_ids: set[str] = set()
        self._consumed_snapshot_transport_roles: set[str] = set()

    def register_existing(self, value: Any) -> str:
        to_document = getattr(value, "to_document", None)
        supplied = to_document() if callable(to_document) else value
        if type(supplied) is not dict:
            _fail("typed wire existing evidence is not one exact document")
        schema = supplied.get("schema")
        if type(schema) is not str:
            _fail("typed wire existing evidence schema is missing")
        document, identity = _validate_registered_evidence_document_v180r12r4(
            supplied, expected_schema=schema
        )
        prior = self.documents_by_id.get(identity)
        if prior is not None and prior != document:
            _fail("typed wire evidence identity aliases two documents")
        self.documents_by_id[identity] = document
        self.objects_by_id[identity] = value
        return identity

    def _dependency(self, identity: Any, expected_type: type, label: str) -> Any:
        value = self.objects_by_id.get(_require_content_id(identity, label))
        if type(value) is not expected_type:
            _fail("typed wire evidence lacks its exact earlier " + label)
        return value

    @staticmethod
    def _topology(document: Mapping[str, Any]) -> Any:
        def node(row: Mapping[str, Any]) -> Any:
            return runtime.CgroupNodeIdentityV180R12R4(
                row["role"], row["path"], row["parent_path"],
                row["membership_path"], row["parent_membership_path"],
                row["directory_fd"], row["device"], row["inode"], row["mode"],
                row["link_count"], row["cloexec"], row["symlink_free_resolution"],
            )

        controls = tuple(
            runtime.CgroupControlFileOFDV180R12R4(
                row["node_role"], row["name"], row["fd"], row["device"],
                row["inode"], row["mode"], row["link_count"], row["cloexec"],
                row["opened_before_supervisor_birth"],
                row["retained_through_os_observe"],
            )
            for row in document["control_files"]
        )
        return runtime.MeasurementCgroupTopologyReceiptV180R12R4(
            document["cgroup_parent_fact"],
            node(document["delegated_parent"]),
            node(document["measurement_root"]),
            node(document["supervisor_leaf"]),
            node(document["worker_leaf"]),
            document["filesystem_type"], tuple(document["controllers"]),
            tuple(document["subtree_control"]),
            document["root_memory_max_bytes"], document["root_pids_max"],
            document["supervisor_leaf_pids_max"],
            document["worker_leaf_pids_max"],
            document["root_populated_before_birth"],
            document["root_process_count_before_birth"],
            tuple(document["leaf_process_counts_before_birth"]), controls,
        )

    def _rehydrate(self, document: dict[str, Any]) -> Any:
        worker = runtime.worker
        schema = document["schema"]
        if schema == "acfqp.campaign_stable_input_snapshot.v180r12r4":
            facts = {
                fact.fact_id: fact
                for fact in worker.frozen_campaign_input_facts_v180r12r4()
            }
            fact = facts.get(document["stable_input_fact_id"])
            if fact is None or fact.role.value != document["role"]:
                _fail("typed wire snapshot crossed its frozen input fact")
            raw = self._snapshot_bytes_by_id.pop(
                document["stable_input_snapshot_id"], None
            )
            if type(raw) is not bytes:
                _fail("typed wire snapshot lacks its authenticated source-read bytes")
            return worker.StableInputSnapshotReceiptV180R12R4(fact, raw)
        if schema == "acfqp.campaign_memfd_stage_receipt.v180r12r4":
            return worker.MemfdStageReceiptV180R12R4(
                document["input_snapshot_id"],
                worker.CampaignInputRoleV180R12R4(document["role"]),
                document["supervisor_fd"], document["worker_fd"],
                document["device"], document["inode"], document["byte_count"],
                document["sha256"], tuple(document["observed_seals"]),
                document["supervisor_cloexec"], document["worker_read_only"],
                document["anonymous_inode"], document["link_count"],
                document["write_probe_errno"],
            )
        if schema == "acfqp.campaign_fd_visibility_receipt.v180r12r4":
            return worker.FDVisibilityReceiptV180R12R4(
                document["attempt_id"], document["operation_id"],
                document["stage_receipt_id"],
                document["holder_process_birth_receipt_id"],
                document["holder_role"],
                worker.CampaignInputRoleV180R12R4(document["role"]),
                worker.VisibilityStateV180R12R4(document["state"]),
                document["designated_worker_fd"], document["expected_device"],
                document["expected_inode"], document["observed_device"],
                document["observed_inode"], document["visible"],
                document["read_only"], tuple(document["unexpected_stage_fds"]),
            )
        if schema == "acfqp.campaign_semantic_operation_receipt.v180r12r4":
            auxiliary = tuple(
                (row["name"], row["value"])
                for row in document["auxiliary_values"]
            )
            return worker.SemanticOperationReceiptV180R12R4(
                document["attempt_id"], document["operation_id"],
                worker.SemanticOperationKindV180R12R4(document["kind"]),
                document["label"], document["family"],
                document["family_ordinal"], document["ordinal"],
                document["operation_manifest_id"],
                document["native_zero_source_manifest_id"],
                document["native_zero_import_inventory_id"],
                document["evidence_subject_id"], document["outcome_code"],
                document["measured_value"], auxiliary,
            )
        if schema == "acfqp.campaign_measurement_subject_result.v180r12r4":
            return document
        if schema == "acfqp.campaign_replay_subject_receipt.v180r12r4":
            subject_document = self.documents_by_id.get(document["subject_result_id"])
            if (
                type(subject_document) is not dict
                or subject_document.get("schema")
                != "acfqp.campaign_measurement_subject_result.v180r12r4"
            ):
                _fail("typed wire replay subject lacks its earlier subject bytes")
            semantic = tuple(
                self._dependency(
                    identity,
                    worker.SemanticOperationReceiptV180R12R4,
                    "semantic operation receipt",
                )
                for identity in document["semantic_operation_receipt_ids"]
            )
            return worker.ProducerFreeReplaySubjectReceiptV180R12R4(
                document["subject_result_id"],
                document["campaign_attempt_record_id"],
                document["operation_manifest_id"],
                document["native_zero_source_manifest_id"],
                document["native_zero_import_inventory_id"],
                document["terminal_snapshot_id"],
                document["verification_snapshot_id"],
                tuple(document["open_visibility_receipt_ids"]), semantic,
                _canonical(subject_document),
                document["producer_module_imported"],
                document["producer_entrypoint_called"],
                document["exact_v180r12r2_verification_replayed"],
                document["route_component_counter_closure_status"],
            )
        if schema == "acfqp.campaign_cgroup_topology_receipt.v180r12r4":
            return self._topology(document)
        if schema == "acfqp.campaign_pidfd_birth_receipt.v180r12r4":
            topology = self._dependency(
                document["cgroup_topology_receipt_id"],
                runtime.MeasurementCgroupTopologyReceiptV180R12R4,
                "cgroup topology receipt",
            )
            return runtime.PidfdBirthReceiptV180R12R4(
                topology, document["attempt_id"], document["operation_id"],
                runtime.ProcessRoleV180R12R4(document["process_role"]),
                document["pid"], document["pidfd"], document["pidfd_device"],
                document["pidfd_inode"], tuple(document["clone3_flags"]),
                document["target_cgroup_fd"], document["target_cgroup_device"],
                document["target_cgroup_inode"], document["target_cgroup_path"],
                document["proc_starttime_ticks"], document["pidfd_fdinfo_pid"],
                tuple(document["pidfd_fdinfo_nspid"]),
                document["cgroup_membership_line"],
                document["membership_observed_before_work"],
                document["pidfd_cloexec"],
                document["production_runtime_placement_t3"],
            )
        if schema == "acfqp.campaign_pidfd_reap_receipt.v180r12r4":
            birth = self._dependency(
                document["pidfd_birth_receipt_id"],
                runtime.PidfdBirthReceiptV180R12R4,
                "pidfd birth receipt",
            )
            return runtime.PidfdReapReceiptV180R12R4(
                birth, document["operation_id"], document["pidfd_device"],
                document["pidfd_inode"], document["proc_starttime_ticks"],
                document["waitid_idtype"], document["waitid_pidfd"],
                document["waitid_code"], document["waitid_status"],
                document["pidfd_readable"],
                document["leaf_populated_after_reap"],
                document["leaf_process_count_after_reap"],
            )
        if schema == "acfqp.campaign_cgroup_observation_receipt.v180r12r4":
            topology = self._dependency(
                document["cgroup_topology_receipt_id"],
                runtime.MeasurementCgroupTopologyReceiptV180R12R4,
                "cgroup topology receipt",
            )
            supervisor_reap = self._dependency(
                document["supervisor_reap_receipt_id"],
                runtime.PidfdReapReceiptV180R12R4,
                "supervisor reap receipt",
            )
            worker_reap = self._dependency(
                document["worker_reap_receipt_id"],
                runtime.PidfdReapReceiptV180R12R4,
                "worker reap receipt",
            )
            controls = {
                row.control_file_fact_id: row for row in topology.control_files
            }
            readbacks = tuple(
                runtime.CgroupControlFileReadbackV180R12R4(
                    controls[row["control_file_fact_id"]], row["raw_value"],
                    row["same_open_file_description"],
                    row["read_after_both_reaps"],
                    row["read_before_cgroup_remove"],
                )
                for row in document["control_file_readbacks"]
            )
            pairs = lambda rows, key: tuple(
                (row[key], row["value"]) for row in rows
            )
            return runtime.CgroupV2ObservationReceiptV180R12R4(
                topology, supervisor_reap, worker_reap, document["operation_id"],
                document["memory_peak_bytes"], document["pids_peak"],
                pairs(document["memory_events"], "name"),
                pairs(document["pids_events"], "name"),
                pairs(document["populated_by_role"], "role"),
                pairs(document["process_count_by_role"], "role"),
                readbacks, document["observed_after_window_close"],
            )
        return document

    def _accept_snapshot_transport(
        self, supplied: Mapping[str, Any], *, expected_role: str
    ) -> str:
        document = _thaw_json_value(supplied)
        if (
            type(document) is not dict
            or set(document) != set(SNAPSHOT_BYTES_TRANSPORT_FIELDS)
            or document.get("schema") != SNAPSHOT_BYTES_TRANSPORT_SCHEMA
            or document.get("role") != expected_role
            or type(document.get("byte_count")) is not int
            or document["byte_count"] <= 0
            or document["byte_count"] > 1024 * 1024
            or type(document.get("canonical_bytes_hex")) is not str
            or len(document["canonical_bytes_hex"]) != 2 * document["byte_count"]
            or len(_canonical(document)) > SNAPSHOT_BYTES_TRANSPORT_BYTE_CAP
        ):
            _fail("snapshot bytes transport schema, keyset, or cap changed")
        identity = _require_content_id(
            document["snapshot_receipt_id"], "snapshot transport receipt ID"
        )
        supplied_sha = _require_content_id(
            document["sha256"], "snapshot transport SHA-256"
        )
        try:
            raw = bytes.fromhex(document["canonical_bytes_hex"])
        except ValueError as error:
            raise V180R12R4RuntimeError(
                "snapshot bytes transport is not lowercase hexadecimal"
            ) from error
        if (
            document["canonical_bytes_hex"] != raw.hex()
            or len(raw) != document["byte_count"]
            or hashlib.sha256(raw).hexdigest() != supplied_sha
            or identity in self._snapshot_bytes_by_id
            or identity in self._consumed_snapshot_transport_ids
            or expected_role in self._consumed_snapshot_transport_roles
        ):
            _fail("snapshot bytes transport identity, digest, or one-shot join changed")
        self._snapshot_bytes_by_id[identity] = raw
        self._consumed_snapshot_transport_ids.add(identity)
        self._consumed_snapshot_transport_roles.add(expected_role)
        return identity

    def decode_batch(
        self,
        supplied_rows: Sequence[Mapping[str, Any]],
        *,
        campaign_event_sequence: int,
        phase: str,
        actor_role: str,
        event_kind: str,
    ) -> tuple[Any, ...]:
        if type(supplied_rows) not in {tuple, list}:
            _fail("typed wire evidence batch is mistyped")
        transports = [
            row for row in supplied_rows
            if type(row) is dict and row.get("schema") == SNAPSHOT_BYTES_TRANSPORT_SCHEMA
        ]
        ordinary = [row for row in supplied_rows if row not in transports]
        if transports:
            expected_role = {4: "TERMINAL", 6: "VERIFICATION"}.get(
                campaign_event_sequence
            )
            if (
                len(transports) != 1
                or expected_role is None
                or phase != "STAGE"
                or actor_role != "SUPERVISOR"
                or event_kind != "INPUT_READ_OUTCOME"
            ):
                _fail("snapshot proposal must carry exactly one transport attachment")
            transport_id = self._accept_snapshot_transport(
                transports[0], expected_role=expected_role
            )
            snapshots = [
                row for row in ordinary
                if type(row) is dict
                and row.get("schema")
                == "acfqp.campaign_stable_input_snapshot.v180r12r4"
            ]
            if (
                len(snapshots) != 1
                or snapshots[0].get("stable_input_snapshot_id") != transport_id
                or snapshots[0].get("role") != expected_role
            ):
                self._snapshot_bytes_by_id.pop(transport_id, None)
                _fail("snapshot transport is missing or crossed its receipt document")
        values = tuple(self.decode(row) for row in ordinary)
        if self._snapshot_bytes_by_id:
            _fail("authenticated snapshot transport was not consumed exactly once")
        return values

    def assert_snapshot_transports_complete(self) -> None:
        if (
            self._snapshot_bytes_by_id
            or self._consumed_snapshot_transport_roles
            != {"TERMINAL", "VERIFICATION"}
            or len(self._consumed_snapshot_transport_ids) != 2
        ):
            _fail("authenticated snapshot transports are not the exact seq4/seq6 pair")

    def decode(self, supplied: Mapping[str, Any]) -> Any:
        if type(supplied) is not dict or type(supplied.get("schema")) is not str:
            _fail("typed wire evidence is not one exact schema document")
        document, identity = _validate_registered_evidence_document_v180r12r4(
            supplied, expected_schema=supplied["schema"]
        )
        value = self._rehydrate(document)
        to_document = getattr(value, "to_document", None)
        round_trip = to_document() if callable(to_document) else value
        if (
            type(round_trip) is not dict
            or _canonical(round_trip) != _canonical(document)
        ):
            _fail("typed wire evidence failed exact native canonical round trip")
        prior = self.documents_by_id.get(identity)
        if prior is not None and prior != document:
            _fail("typed wire evidence identity aliases two documents")
        self.documents_by_id[identity] = document
        self.objects_by_id[identity] = value
        return value


@dataclass(frozen=True, slots=True)
class ObserverEventProposalV180R12R4:
    """One child report after the adapter reconstructs its typed evidence."""

    campaign_event_sequence: int
    phase: str
    actor_role: str
    event_kind: str
    operation_id: str
    payload: Mapping[str, Any]
    evidence_document: Any | None
    supporting_evidence_documents: tuple[Any, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.campaign_event_sequence) is not int
            or self.campaign_event_sequence < 0
            or type(self.phase) is not str
            or type(self.actor_role) is not str
            or type(self.event_kind) is not str
            or type(self.operation_id) is not str
            or type(self.payload) is not dict
            or type(self.supporting_evidence_documents) is not tuple
        ):
            _fail("observer event proposal is malformed")

    @property
    def measured_value(self) -> int | None:
        return self.payload["measured_value"]

    @classmethod
    def from_signed_body_v180r12r4(
        cls,
        body: Mapping[str, Any],
        *,
        protocol_id: str,
        authorization_id: str,
        authorization_evidence_id: str,
        attempt_id: str,
        evidence_registry: TypedWireEvidenceRegistryV180R12R4 | None = None,
    ) -> "ObserverEventProposalV180R12R4":
        document = validate_event_proposal_body_v180r12r4(
            body,
            protocol_id=protocol_id,
            authorization_id=authorization_id,
            authorization_evidence_id=authorization_evidence_id,
            attempt_id=attempt_id,
        )
        supplied_rows = document["evidence_documents"]
        decoded_values = (
            None
            if evidence_registry is None
            else evidence_registry.decode_batch(
                supplied_rows,
                campaign_event_sequence=document["campaign_event_sequence"],
                phase=document["phase"],
                actor_role=document["actor_role"],
                event_kind=document["event_kind"],
            )
        )
        ordinary_rows = [
            row for row in supplied_rows
            if row.get("schema") != SNAPSHOT_BYTES_TRANSPORT_SCHEMA
        ]
        evidence_rows: list[tuple[Any, str]] = []
        for index, supplied in enumerate(ordinary_rows):
            schema = supplied.get("schema")
            if type(schema) is not str:
                _fail("proposal evidence schema is missing")
            validated, identity = _validate_registered_evidence_document_v180r12r4(
                supplied, expected_schema=schema
            )
            value = validated if decoded_values is None else decoded_values[index]
            evidence_rows.append((value, identity))
        evidence_ids = [identity for _row, identity in evidence_rows]
        if len(evidence_ids) != len(set(evidence_ids)):
            _fail("proposal evidence documents are identity-duplicated")
        direct_id = document["payload"]["evidence_id"]
        if direct_id is None:
            if evidence_rows:
                _fail("evidence-null proposal carried unregistered support bytes")
            direct = None
            supporting: tuple[Any, ...] = ()
        else:
            matches = [index for index, value in enumerate(evidence_ids) if value == direct_id]
            if matches != [0]:
                _fail("proposal direct evidence is not the first exact document")
            direct = evidence_rows[0][0]
            supporting = tuple(row for row, _identity in evidence_rows[1:])
        expected_payload = runtime.campaign_event_payload_v180r12r4(
            event_kind=document["event_kind"],
            evidence_id=direct_id,
            measured_value=document["payload"]["measured_value"],
            auxiliary_values=(),
        )
        if document["payload"] != expected_payload:
            _fail("signed proposal payload differs from exact campaign event payload")
        return cls(
            document["campaign_event_sequence"],
            document["phase"],
            document["actor_role"],
            document["event_kind"],
            document["operation_id"],
            document["payload"],
            direct,
            supporting,
        )


FINALIZE_SUCCESS_INPUT_FIELDS = (
    "event_documents",
    "evidence_documents",
    "os_receipt_documents",
    "expected_protocol_id",
    "expected_authorization_id",
    "expected_authorization_evidence_id",
    "expected_attempt_id",
    "expected_prelaunch_materialization_terminal_id",
    "expected_prelaunch_launch_manifest_sha256",
    "expected_precompiled_source_bundle_sha256",
    "expected_prelaunch_launch_rule_id",
    "expected_measurement_launch_attempt_id",
    "expected_subject_id",
    "expected_native_zero_source_manifest_id",
    "expected_native_zero_import_inventory_id",
    "max_event_count",
    "max_event_byte_count",
    "max_ledger_byte_count",
)


def _content_id(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{label} must be one lowercase SHA-256 identity")
    return value


@dataclass(frozen=True, slots=True)
class FinalizeSuccessInputsV180R12R4:
    """Exact observer-retained population accepted by the pure finalizer."""

    event_documents: tuple[bytes, ...]
    evidence_documents: tuple[bytes, ...]
    os_receipt_documents: tuple[bytes, ...]
    expected_protocol_id: str
    expected_authorization_id: str
    expected_authorization_evidence_id: str
    expected_attempt_id: str
    expected_prelaunch_materialization_terminal_id: str
    expected_prelaunch_launch_manifest_sha256: str
    expected_precompiled_source_bundle_sha256: str
    expected_prelaunch_launch_rule_id: str
    expected_measurement_launch_attempt_id: str
    expected_subject_id: str
    expected_native_zero_source_manifest_id: str
    expected_native_zero_import_inventory_id: str
    max_event_count: int
    max_event_byte_count: int
    max_ledger_byte_count: int

    def __post_init__(self) -> None:
        for rows, count, label in (
            (self.event_documents, SUCCESS_EVENT_COUNT, "success events"),
            (
                self.evidence_documents,
                finalizer.SUCCESS_EVIDENCE_DOCUMENT_COUNT,
                "success evidence",
            ),
            (
                self.os_receipt_documents,
                finalizer.OS_EVIDENCE_DOCUMENT_COUNT,
                "success OS receipts",
            ),
        ):
            if (
                type(rows) is not tuple
                or len(rows) != count
                or any(type(raw) is not bytes or not raw for raw in rows)
            ):
                _fail(f"{label} are not the exact observer-retained byte tuple")
        for value, label in (
            (self.expected_protocol_id, "finalizer protocol ID"),
            (self.expected_authorization_id, "finalizer authorization ID"),
            (
                self.expected_authorization_evidence_id,
                "finalizer authorization-evidence ID",
            ),
            (self.expected_attempt_id, "finalizer attempt ID"),
            (
                self.expected_prelaunch_materialization_terminal_id,
                "finalizer prelaunch materialization-terminal ID",
            ),
            (
                self.expected_prelaunch_launch_manifest_sha256,
                "finalizer prelaunch launch-manifest SHA-256",
            ),
            (
                self.expected_precompiled_source_bundle_sha256,
                "finalizer precompiled source-bundle SHA-256",
            ),
            (
                self.expected_prelaunch_launch_rule_id,
                "finalizer prelaunch launch-rule ID",
            ),
            (
                self.expected_measurement_launch_attempt_id,
                "finalizer measurement launch-attempt ID",
            ),
            (self.expected_subject_id, "finalizer subject ID"),
            (
                self.expected_native_zero_source_manifest_id,
                "finalizer native-zero source manifest ID",
            ),
            (
                self.expected_native_zero_import_inventory_id,
                "finalizer native-zero import inventory ID",
            ),
        ):
            _content_id(value, label)
        if (
            self.max_event_count != protocol.MAX_EVENT_COUNT
            or self.max_event_byte_count != protocol.MAX_EVENT_BYTE_COUNT
            or self.max_ledger_byte_count != protocol.MAX_LEDGER_BYTE_COUNT
        ):
            _fail("finalizer input caps differ from the preregistered exact caps")
        # This constructor validates all 328 registered identities and their
        # sorted unique byte population.  The pure finalizer independently
        # replays it again; this early check prevents any output file creation
        # for a malformed population.
        inventory = ledger.CampaignEvidenceInventoryV180R12R4.from_documents(
            self.evidence_documents
        )
        if tuple(raw for _identity, raw in inventory.rows) != self.evidence_documents:
            _fail("finalizer evidence bytes are not in registered identity order")
        # Do not trust caller-supplied OS flags: the twelve bytes must be the
        # exact sorted subset already present in the registered inventory.
        os_schemas = set(finalizer.OS_EVIDENCE_SCHEMA_COUNTS)
        expected_os = tuple(
            raw
            for _identity, raw in inventory.rows
            if _canonical_object(raw, "registered OS evidence").get("schema")
            in os_schemas
        )
        if self.os_receipt_documents != expected_os:
            _fail("finalizer OS receipts are not the exact inventory subset")

    def to_kwargs(self) -> dict[str, Any]:
        values = {
            field: getattr(self, field) for field in FINALIZE_SUCCESS_INPUT_FIELDS
        }
        if tuple(values) != FINALIZE_SUCCESS_INPUT_FIELDS:
            _fail("finalizer success input field order changed")
        return values


def _inventory_one(
    inventory: ledger.CampaignEvidenceInventoryV180R12R4,
    schema: str,
    identity_field: str,
) -> tuple[str, dict[str, Any]]:
    document = inventory.one(schema)
    return _content_id(document.get(identity_field), schema + " identity"), document


def build_finalize_success_inputs_v180r12r4(
    *,
    campaign: runtime.CampaignMeasurementSupervisorV180R12R4,
    journal: CanonicalEventJournalV180R12R4,
) -> FinalizeSuccessInputsV180R12R4:
    """Freeze finalizer inputs only from observer-owned retained state."""

    campaign.assert_success_schedule_complete()
    event_documents = journal.read_complete_event_documents()
    in_memory_events = tuple(
        _canonical(event.to_document()) for event in campaign.ledger_state.events
    )
    if event_documents != in_memory_events:
        _fail("durable event bytes differ from the observer ledger state")
    inventory = campaign.validate_registered_evidence_bundle()
    evidence_documents = tuple(raw for _identity, raw in inventory.rows)
    _attempt_record_id, attempt_record = _inventory_one(
        inventory,
        "acfqp.campaign_attempt_record.v180r12r4",
        "campaign_attempt_record_id",
    )
    if (
        attempt_record.get("protocol_id") != campaign.protocol_id
        or attempt_record.get("authorization_id") != campaign.authorization_id
        or attempt_record.get("attempt_id") != campaign.attempt_id
    ):
        _fail("registered attempt record differs from observer campaign context")
    subject_id, _subject = _inventory_one(
        inventory,
        "acfqp.campaign_measurement_subject_result.v180r12r4",
        "subject_result_id",
    )
    source_manifest_id, _source_manifest = _inventory_one(
        inventory,
        "acfqp.campaign_native_zero_source_manifest.v180r12r4",
        "native_zero_source_manifest_id",
    )
    import_inventory_id, _import_inventory = _inventory_one(
        inventory,
        "acfqp.campaign_native_zero_import_inventory.v180r12r4",
        "native_zero_import_inventory_id",
    )
    os_schemas = set(finalizer.OS_EVIDENCE_SCHEMA_COUNTS)
    os_receipts = tuple(
        raw
        for _identity, raw in inventory.rows
        if _canonical_object(raw, "registered evidence document").get("schema")
        in os_schemas
    )
    return FinalizeSuccessInputsV180R12R4(
        event_documents,
        evidence_documents,
        os_receipts,
        campaign.protocol_id,
        campaign.authorization_id,
        attempt_record["authorization_evidence_id"],
        campaign.attempt_id,
        attempt_record["prelaunch_materialization_terminal_id"],
        attempt_record["prelaunch_launch_manifest_sha256"],
        _source_manifest["precompiled_source_bundle_sha256"],
        attempt_record["prelaunch_launch_rule_id"],
        attempt_record["measurement_launch_attempt_id"],
        subject_id,
        source_manifest_id,
        import_inventory_id,
        protocol.MAX_EVENT_COUNT,
        protocol.MAX_EVENT_BYTE_COUNT,
        protocol.MAX_LEDGER_BYTE_COUNT,
    )


@dataclass(slots=True)
class TerminalPublicationTokenV180R12R4:
    """Marks TERMINAL_PUBLICATION_ATTEMPT_ENTRY before fallible path work."""

    started: bool = False


def finalize_and_materialize_success_v180r12r4(
    *,
    store: DurableStoreV180R12R4,
    inputs: FinalizeSuccessInputsV180R12R4,
    campaign_deadline_ns: int,
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
    publication_token: TerminalPublicationTokenV180R12R4 | None = None,
) -> finalizer.PendingCampaignMeasurementTerminalV180R12R4:
    """Call the pure finalizer once, commit four artifacts, then TERMINAL."""

    token = (
        TerminalPublicationTokenV180R12R4()
        if publication_token is None
        else publication_token
    )
    if (
        type(inputs) is not FinalizeSuccessInputsV180R12R4
        or type(token) is not TerminalPublicationTokenV180R12R4
        or token.started
    ):
        _fail("success finalization requires its exact retained-input type")
    _check_campaign_deadline_v180r12r4(
        campaign_deadline_ns,
        monotonic_ns=monotonic_ns,
        boundary="pure finalizer entry",
    )
    result = finalizer.finalize_campaign_measurement_terminal_v180r12r4(
        **inputs.to_kwargs()
    )
    _check_campaign_deadline_v180r12r4(
        campaign_deadline_ns,
        monotonic_ns=monotonic_ns,
        boundary="pure finalizer return",
    )
    if type(result) is not finalizer.PendingCampaignMeasurementTerminalV180R12R4:
        _fail("pure finalizer returned a mistyped pending terminal")
    artifacts = result.success_artifact_bytes
    if tuple(artifacts) != finalizer.SUCCESS_ARTIFACT_ORDER:
        _fail("pure finalizer success artifact order changed")

    # Validate all caps and schema/identity/terminal joins before creating the
    # first durable artifact.  This keeps a cap violation outcome-free while
    # preserving the consumed attempt and closed event prefix via FAILURE.
    terminal = result.document
    for key, schema, identity_field, terminal_prefix in (
        finalizer.SUCCESS_ARTIFACT_SCHEMA_ROWS
    ):
        raw = artifacts.get(key)
        cap = SUCCESS_ARTIFACT_BYTE_CAP_BY_KEY[key]
        if type(raw) is not bytes or not raw or len(raw) > cap:
            raise V180R12R4CapViolation(
                f"{key} exceeds its exact preregistered byte cap"
            )
        document = _canonical_object(raw, key + " success artifact")
        if (
            document.get("schema") != schema
            or _content_id(document.get(identity_field), identity_field)
            != terminal.get(identity_field)
            or terminal.get(terminal_prefix + "_byte_count") != len(raw)
            or terminal.get(terminal_prefix + "_sha256")
            != hashlib.sha256(raw).hexdigest()
        ):
            _fail("success artifact does not join its exact pending terminal")
    terminal_raw = result.canonical_bytes
    if (
        len(terminal_raw) > protocol.TERMINAL_BYTE_CAP
        or _canonical_object(terminal_raw, "pending campaign terminal") != terminal
        or terminal.get("V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS")
        != finalizer.TERMINAL_COUNTER_STATUS
        or terminal.get("COUNTER_COMPLETENESS_GATE")
        != finalizer.TERMINAL_COUNTER_GATE
        or terminal.get("independent_verification_present") is not False
    ):
        raise V180R12R4CapViolation(
            "pending terminal exceeds its cap or escaped its pending boundary"
        )

    for key in finalizer.SUCCESS_ARTIFACT_ORDER:
        _check_campaign_deadline_v180r12r4(
            campaign_deadline_ns,
            monotonic_ns=monotonic_ns,
            boundary=key + " durable write entry",
        )
        store.write_once_verified(
            SUCCESS_ARTIFACT_RELATIVE_PATH_BY_KEY[key],
            artifacts[key],
            byte_cap=SUCCESS_ARTIFACT_BYTE_CAP_BY_KEY[key],
        )
        _check_campaign_deadline_v180r12r4(
            campaign_deadline_ns,
            monotonic_ns=monotonic_ns,
            boundary=key + " durable readback",
        )
    # TERMINAL is deliberately the only final namespace mutation.  A verifier
    # can therefore treat its presence as proof that all four inputs survived
    # their own stable readback first.
    _check_campaign_deadline_v180r12r4(
        campaign_deadline_ns,
        monotonic_ns=monotonic_ns,
        boundary="pending TERMINAL durable write entry",
    )
    # From TERMINAL_PUBLICATION_ATTEMPT_ENTRY onward, an inner campaign FAILURE
    # is forbidden even if parent-open/O_EXCL/fsync/readback or watchdog
    # teardown fails.  The retained launcher observes absent, partial, or exact
    # TERMINAL state; the two campaign terminal namespaces never coexist.
    token.started = True
    store.write_once_verified(
        TERMINAL_RELATIVE_PATH,
        terminal_raw,
        byte_cap=protocol.TERMINAL_BYTE_CAP,
    )
    _check_campaign_deadline_v180r12r4(
        campaign_deadline_ns,
        monotonic_ns=monotonic_ns,
        boundary="pending TERMINAL durable readback",
    )
    return result


class OuterEffectAdapterV180R12R4(Protocol):
    """Effects beneath the observer; every child starts blocked on an ACK."""

    def create_cgroup(self, attempt_id: str) -> tuple[Any, Any]: ...
    def launch_supervisor(
        self, cgroup: Any, operation_id: str, deadline_ns: int
    ) -> tuple[Any, Any]: ...
    def acknowledge_event(self, child: Any, ack_document: Mapping[str, Any]) -> None: ...
    def receive_event_proposals(
        self, child: Any, deadline_ns: int
    ) -> Iterable[ObserverEventProposalV180R12R4]: ...
    def reap_supervisor(
        self, child: Any, operation_id: str, deadline_ns: int
    ) -> Any: ...
    def close_supervisor_pidfd_after_reap_ack(
        self, child: Any, supervisor_reap_receipt: Any
    ) -> None: ...
    def observe_cgroup(
        self, cgroup: Any, supervisor_reap_receipt: Any, operation_id: str
    ) -> Any: ...
    def kill_cgroup(self, cgroup: Any) -> None: ...
    def terminate_and_reap(self, child: Any) -> None: ...
    def observe_cgroup_failure(self, cgroup: Any) -> Mapping[str, Any]: ...
    def close_cgroup(self, cgroup: Any) -> None: ...


def _sealed_read_only_runtime_memfd_v180r12r4(name: str, raw: bytes) -> int:
    if type(name) is not str or not name or type(raw) is not bytes or not raw:
        _fail("runtime sealed memfd arguments changed")
    writable = os.memfd_create(
        name, os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING
    )
    read_only = -1
    try:
        remaining = memoryview(raw)
        while remaining:
            written = os.write(writable, remaining)
            if written <= 0:
                _fail("runtime sealed memfd write made no progress")
            remaining = remaining[written:]
        os.fchmod(writable, 0o400)
        fcntl.fcntl(writable, fcntl.F_ADD_SEALS, REQUIRED_MEMFD_SEAL_MASK)
        read_only = os.open(
            f"/proc/self/fd/{writable}", os.O_RDONLY | os.O_CLOEXEC
        )
        metadata = os.fstat(read_only)
        if (
            metadata.st_size != len(raw)
            or metadata.st_nlink != 0
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or fcntl.fcntl(read_only, fcntl.F_GETFL) & os.O_ACCMODE
            != os.O_RDONLY
            or fcntl.fcntl(read_only, fcntl.F_GET_SEALS)
            != REQUIRED_MEMFD_SEAL_MASK
        ):
            _fail("runtime sealed memfd identity changed")
        return read_only
    except BaseException:
        if read_only >= 0:
            os.close(read_only)
        raise
    finally:
        os.close(writable)


@dataclass(slots=True)
class LinuxSupervisorChildV180R12R4:
    process: ProcessHandleV180R12R4
    birth_receipt: runtime.PidfdBirthReceiptV180R12R4
    channel: AuthenticatedFrameChannelV180R12R4
    expected_campaign_sequence: int = 3
    awaiting_campaign_sequence: int | None = None
    start_sent: bool = False
    stream_closed: bool = False
    reaped: bool = False
    pidfd_closed: bool = False


class LinuxOuterEffectAdapterV180R12R4:
    """Concrete observer effects behind the injectable one-shot interface."""

    def __init__(
        self,
        *,
        context: types.MappingProxyType,
        authority: CampaignAttemptAuthorityV180R12R4,
        attempt_document: Mapping[str, Any],
        operation_manifest_document: Mapping[str, Any],
        native_zero_source_manifest_document: Mapping[str, Any],
        native_zero_import_inventory_document: Mapping[str, Any],
        repository_root_fd: int,
        launcher: LinuxClone3V180R12R4 | None = None,
        cgroup_manager: LinuxCgroupV2V180R12R4 | None = None,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
        launch_fault_injector: Callable[[str], None] | None = None,
    ) -> None:
        if (
            type(context) is not types.MappingProxyType
            or type(authority) is not CampaignAttemptAuthorityV180R12R4
            or context["target"] != "measurement"
            or context["campaign_attempt_id"] != authority.attempt_id
            or type(repository_root_fd) is not int
            or repository_root_fd < 3
            or not callable(monotonic_ns)
            or launch_fault_injector is not None
            and not callable(launch_fault_injector)
        ):
            _fail("Linux outer adapter authority or repository FD changed")
        repository_metadata = os.fstat(repository_root_fd)
        if (
            not stat.S_ISDIR(repository_metadata.st_mode)
            or fcntl.fcntl(repository_root_fd, fcntl.F_GETFL) & os.O_PATH
            != os.O_PATH
            or os.get_inheritable(repository_root_fd)
            or _fd_canonical_path(repository_root_fd, "repository root")
            != context["repository_root"]
        ):
            _fail("Linux outer adapter repository root OFD changed")
        expected_attempt, expected_manifest = build_campaign_attempt_record_v180r12r4(
            authority
        )
        if (
            _thaw_json_value(attempt_document) != expected_attempt
            or _thaw_json_value(operation_manifest_document) != expected_manifest
        ):
            _fail("Linux outer adapter attempt/operation authority changed")
        source, source_id = _validate_registered_evidence_document_v180r12r4(
            native_zero_source_manifest_document,
            expected_schema="acfqp.campaign_native_zero_source_manifest.v180r12r4",
        )
        imports, import_id = _validate_registered_evidence_document_v180r12r4(
            native_zero_import_inventory_document,
            expected_schema="acfqp.campaign_native_zero_import_inventory.v180r12r4",
        )
        if not (
            source["protocol_id"] == authority.protocol_id
            and source["authorization_id"] == authority.authorization_id
            and source["attempt_id"] == authority.attempt_id
            and source["operation_manifest_id"]
            == expected_manifest["campaign_operation_manifest_id"]
            and source["precompiled_source_bundle_sha256"]
            == context["precompiled_source_bundle_sha256"]
            and imports["protocol_id"] == authority.protocol_id
            and imports["authorization_id"] == authority.authorization_id
            and imports["attempt_id"] == authority.attempt_id
            and imports["source_manifest_id"] == source_id
        ):
            _fail("Linux outer adapter native-zero manifest join changed")
        self.context = context
        self.authority = authority
        self.attempt_document = expected_attempt
        self.operation_manifest_document = expected_manifest
        self.native_zero_source_manifest_document = source
        self.native_zero_import_inventory_document = imports
        self.native_zero_source_manifest_id = source_id
        self.native_zero_import_inventory_id = import_id
        self.repository_root_fd = repository_root_fd
        self.launcher = LinuxClone3V180R12R4() if launcher is None else launcher
        self.cgroup_manager = (
            LinuxCgroupV2V180R12R4()
            if cgroup_manager is None
            else cgroup_manager
        )
        self.monotonic_ns = monotonic_ns
        self.launch_fault_injector = launch_fault_injector
        self.evidence_registry = TypedWireEvidenceRegistryV180R12R4()
        for document in (
            expected_attempt,
            expected_manifest,
            source,
            imports,
        ):
            self.evidence_registry.register_existing(document)

    def create_cgroup(
        self, attempt_id: str
    ) -> tuple[CgroupTreeV180R12R4, runtime.MeasurementCgroupTopologyReceiptV180R12R4]:
        if attempt_id != self.authority.attempt_id:
            _fail("Linux outer adapter cgroup attempt changed")
        tree = self.cgroup_manager.create(
            _thaw_json_value(self.context["cgroup_parent_fact"]),
            attempt_id,
            production_runtime_placement_t1=_thaw_json_value(
                self.context["production_runtime_placement_t1"]
            ),
            production_runtime_placement_t2=_thaw_json_value(
                self.context["production_runtime_placement_t2"]
            ),
        )
        self.evidence_registry.register_existing(tree.topology_receipt)
        return tree, tree.topology_receipt

    def _supervisor_exec_argv(self) -> tuple[str, ...]:
        c_pre_root = PurePosixPath(self.context["c_pre_root"])
        repository_root = PurePosixPath(self.context["repository_root"])
        bootstrap = c_pre_root / "bootstrap.py"
        manifest = c_pre_root / "launch_manifest.json"
        if not (
            c_pre_root.is_absolute()
            and repository_root.is_absolute()
            and bootstrap.is_absolute()
            and manifest.is_absolute()
        ):
            _fail("Linux outer adapter retained bootstrap paths changed")
        return (
            *INTERNAL_BOOTSTRAP_ARGV_PREFIX,
            bootstrap.as_posix(),
            "supervisor",
            repository_root.as_posix(),
            c_pre_root.as_posix(),
            manifest.as_posix(),
        )

    def launch_supervisor(
        self,
        cgroup: CgroupTreeV180R12R4,
        operation_id: str,
        deadline_ns: int,
    ) -> tuple[LinuxSupervisorChildV180R12R4, runtime.PidfdBirthReceiptV180R12R4]:
        if (
            type(cgroup) is not CgroupTreeV180R12R4
            or operation_id
            != ledger.build_campaign_success_event_schedule_v180r12r4(
                self.authority.attempt_id
            )[1].operation_id
            or type(deadline_ns) is not int
            or self.monotonic_ns() >= deadline_ns
            or cgroup.worker_fd != SUPERVISOR_WORKER_CGROUP_FD
        ):
            _fail("Linux outer adapter supervisor launch boundary changed")
        t3_before_getrandom = (
            _production_runtime_placement_t3_checkpoint_v180r12r4(
                self.context,
                cgroup,
                boundary="T3_BEFORE_GETRANDOM",
                fault_injector=self.launch_fault_injector,
            )
        )
        secret = _launch_boundary_v180r12r4(
            "GETRANDOM",
            lambda: os.getrandom(32),
            fault_injector=self.launch_fault_injector,
        )
        if type(secret) is not bytes or len(secret) != 32:
            primary = V180R12R4RuntimeError(
                "observer getrandom returned a short supervisor channel key"
            )
            _annotate_launch_primary_v180r12r4(primary, "GETRANDOM")
            raise primary
        parent_channel, child_channel = _launch_boundary_v180r12r4(
            "SOCKETPAIR",
            lambda: socket.socketpair(
                socket.AF_UNIX, socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC
            ),
            fault_injector=self.launch_fault_injector,
        )
        try:
            _launch_boundary_v180r12r4(
                "SOCKET_BUFFER_CONFIGURATION",
                lambda: configure_seqpacket_pair_v180r12r4(
                    parent_channel, child_channel
                ),
                fault_injector=self.launch_fault_injector,
            )
        except BaseException:
            parent_channel.close()
            child_channel.close()
            raise
        key_fd = context_fd = -1
        process: ProcessHandleV180R12R4 | None = None
        try:
            argv = _launch_boundary_v180r12r4(
                "SUPERVISOR_ARGV_AND_CONTEXT_BUILD",
                self._supervisor_exec_argv,
                fault_injector=self.launch_fault_injector,
            )
            inherited_roles = [
                {"fd": descriptor, "role": role}
                for descriptor, role in (
                    (240, "PRECOMPILED_SOURCE_BUNDLE_MEMFD"),
                    (241, "OBSERVER_SUPERVISOR_SOCK_SEQPACKET"),
                    (242, "PARENT_TO_CHILD_MAC_KEY_MEMFD"),
                    (243, "INTERNAL_LAUNCH_CONTEXT_MEMFD"),
                    (244, "REPOSITORY_ROOT_O_PATH_DIRECTORY"),
                    (245, "WORKER_CGROUP_DIRECTORY"),
                )
            ]
            payload = {
                "schema": "acfqp.v180r12r4_internal_launch_context.v1",
                "target": "supervisor",
                "actor_role": "SUPERVISOR",
                "parent_actor_role": "OBSERVER",
                "protocol_id": self.authority.protocol_id,
                "authorization_id": self.authority.authorization_id,
                "authorization_evidence_id": self.authority.authorization_evidence_id,
                "attempt_id": self.authority.attempt_id,
                "campaign_measurement_execution_slot_id": (
                    self.authority.campaign_measurement_execution_slot_id
                ),
                "logical_occurrence_id": self.authority.logical_occurrence_id,
                "execution_nonce": self.authority.execution_nonce,
                "prelaunch_materialization_terminal_id": (
                    self.authority.prelaunch_materialization_terminal_id
                ),
                "prelaunch_launch_rule_id": self.authority.prelaunch_launch_rule_id,
                "measurement_launch_attempt_id": (
                    self.authority.measurement_launch_attempt_id
                ),
                "launch_operation_id": operation_id,
                "repository_root": self.context["repository_root"],
                "c_pre_root": self.context["c_pre_root"],
                "manifest_path": argv[10],
                "launch_manifest_sha256": (
                    self.authority.prelaunch_launch_manifest_sha256
                ),
                "c_pre_commit_id": self.context["prereg_commit_id"],
                "precompiled_source_bundle_sha256": self.context[
                    "precompiled_source_bundle_sha256"
                ],
                "runner_relative_path": (
                    "scripts/supervise_v180r12r4_campaign_measurement.py"
                ),
                "inherited_fd_roles": inherited_roles,
                "target_payload": {
                    "repository_root_fd": SUPERVISOR_REPOSITORY_ROOT_FD,
                    "worker_cgroup_fd": SUPERVISOR_WORKER_CGROUP_FD,
                },
                "one_shot": True,
                "context_mac_algorithm": "BLAKE2S_KEYED_256",
                "context_mac_direction": "PARENT_TO_CHILD_ONLY",
            }
            context_mac = hashlib.blake2s(
                _canonical(payload), key=secret, digest_size=32
            ).hexdigest()
            key_fd = _launch_boundary_v180r12r4(
                "KEY_MEMFD_CREATE",
                lambda: _sealed_read_only_runtime_memfd_v180r12r4(
                    "v180r12r4-supervisor-key", secret
                ),
                fault_injector=self.launch_fault_injector,
            )
            context_fd = _launch_boundary_v180r12r4(
                "CONTEXT_MEMFD_CREATE",
                lambda: _sealed_read_only_runtime_memfd_v180r12r4(
                    "v180r12r4-supervisor-context",
                    _canonical({**payload, "context_mac": context_mac}),
                ),
                fault_injector=self.launch_fault_injector,
            )
            inherited = {
                PRECOMPILED_SOURCE_BUNDLE_FD: PRECOMPILED_SOURCE_BUNDLE_FD,
                INTERNAL_IPC_FD: child_channel.fileno(),
                INTERNAL_MAC_KEY_FD: key_fd,
                INTERNAL_CONTEXT_FD: context_fd,
                SUPERVISOR_REPOSITORY_ROOT_FD: self.repository_root_fd,
                SUPERVISOR_WORKER_CGROUP_FD: cgroup.worker_fd,
            }
            env = {
                "ACFQP_V180R12R4_LAUNCH_MANIFEST_SHA256": (
                    self.authority.prelaunch_launch_manifest_sha256
                ),
                "LC_CTYPE": "C.UTF-8",
            }
            placement_t3_holder: list[dict[str, Any]] = []

            def revalidate_t3_immediately_before_clone3() -> None:
                if placement_t3_holder:
                    _fail("T3 immediately-before-clone3 callback was repeated")
                observed = _production_runtime_placement_t3_checkpoint_v180r12r4(
                    self.context,
                    cgroup,
                    boundary="T3_IMMEDIATELY_BEFORE_CLONE3",
                    fault_injector=self.launch_fault_injector,
                )
                placement = _complete_t3_checkpoint_conformance_v180r12r4(
                    cgroup.topology_receipt,
                    before_getrandom=t3_before_getrandom,
                    immediately_before_clone3=observed,
                )
                placement_t3_holder.append(placement)

            try:
                process = self.launcher.launch_exec(
                    role="SUPERVISOR",
                    target_cgroup_fd=cgroup.supervisor_fd,
                    expected_cgroup_membership_line=(
                        "0::"
                        + cgroup.topology_receipt.supervisor_leaf.membership_path
                    ),
                    argv=argv,
                    env=env,
                    inherited_fd_map=inherited,
                    pre_clone_revalidate=(
                        revalidate_t3_immediately_before_clone3
                    ),
                )
            except BaseException as primary:
                # The exact launcher annotates every internal boundary itself;
                # this fallback only types a substituted launcher's untyped
                # primary and never replaces an existing T3/OS annotation.
                _annotate_launch_primary_v180r12r4(primary, "CLONE3")
                raise
            if len(placement_t3_holder) != 1:
                primary = V180R12R4RuntimeError(
                    "launcher returned without its adjacent T3 revalidation"
                )
                _annotate_launch_primary_v180r12r4(
                    primary,
                    "T3_IMMEDIATELY_BEFORE_CLONE3",
                    child_created=True,
                    pidfd_acquired=True,
                    exec_observed=True,
                )
                raise primary
            placement_t3 = placement_t3_holder[0]
            birth = _launch_boundary_v180r12r4(
                "BIRTH_RECEIPT_CONSTRUCTION",
                lambda: pidfd_birth_receipt_v180r12r4(
                    topology=cgroup.topology_receipt,
                    attempt_id=self.authority.attempt_id,
                    operation_id=operation_id,
                    handle=process,
                    production_runtime_placement_t3=placement_t3,
                ),
                fault_injector=self.launch_fault_injector,
                child_created=True,
                pidfd_acquired=True,
                exec_observed=True,
            )
            authenticated = _launch_boundary_v180r12r4(
                "AUTHENTICATED_CHANNEL_CONSTRUCTION",
                lambda: AuthenticatedFrameChannelV180R12R4(
                    parent_channel,
                    secret,
                    channel_id=operation_id,
                    protocol_id=self.authority.protocol_id,
                    authorization_id=self.authority.authorization_id,
                    authorization_evidence_id=(
                        self.authority.authorization_evidence_id
                    ),
                    attempt_id=self.authority.attempt_id,
                    parent_actor_role="OBSERVER",
                    child_actor_role="SUPERVISOR",
                    local_actor_role="OBSERVER",
                ),
                fault_injector=self.launch_fault_injector,
                child_created=True,
                pidfd_acquired=True,
                exec_observed=True,
            )
            child = LinuxSupervisorChildV180R12R4(process, birth, authenticated)
            self.evidence_registry.register_existing(birth)
            child_channel.close()
            os.close(key_fd)
            key_fd = -1
            os.close(context_fd)
            context_fd = -1
            return child, birth
        except BaseException:
            parent_channel.close()
            child_channel.close()
            if process is not None:
                try:
                    self.launcher.signal(process, signal.SIGKILL)
                except BaseException:
                    pass
                try:
                    self.launcher.reap(
                        process,
                        deadline_ns=self.context["hard_deadline_ns"],
                        monotonic_ns=self.monotonic_ns,
                    )
                except BaseException:
                    pass
                try:
                    os.close(process.pidfd)
                except BaseException:
                    pass
            raise
        finally:
            if key_fd >= 0:
                os.close(key_fd)
            if context_fd >= 0:
                os.close(context_fd)

    def acknowledge_event(
        self,
        child: LinuxSupervisorChildV180R12R4,
        ack_document: Mapping[str, Any],
    ) -> None:
        if type(child) is not LinuxSupervisorChildV180R12R4:
            _fail("Linux outer adapter child handle is mistyped")
        ack = dict(ack_document)
        if not child.start_sent:
            if ack.get("sequence") != 2 or child.awaiting_campaign_sequence is not None:
                _fail("supervisor START did not follow exact birth ACK")
            start = build_observer_supervisor_start_body_v180r12r4(
                authority=self.authority,
                attempt_document=self.attempt_document,
                operation_manifest_document=self.operation_manifest_document,
                native_zero_source_manifest_id=self.native_zero_source_manifest_id,
                native_zero_import_inventory_id=self.native_zero_import_inventory_id,
                cgroup_topology_document=(
                    child.birth_receipt.topology_receipt.to_document()
                ),
                supervisor_birth_document=child.birth_receipt.to_document(),
                supervisor_birth_event_id=ack["event_id"],
                supervisor_birth_event_sequence=2,
                next_campaign_event_sequence=3,
            )
            child.channel.send(
                "SUPERVISOR_START", child.channel.next_send_sequence, start
            )
            child.start_sent = True
            return
        if child.awaiting_campaign_sequence is None:
            _fail("observer attempted to ACK without one authenticated proposal")
        if ack.get("sequence") != child.awaiting_campaign_sequence:
            _fail("observer ACK crossed its exact proposal sequence")
        wrapped = build_event_ack_body_v180r12r4(
            protocol_id=self.authority.protocol_id,
            authorization_id=self.authority.authorization_id,
            authorization_evidence_id=self.authority.authorization_evidence_id,
            attempt_id=self.authority.attempt_id,
            journal_ack=ack,
        )
        child.channel.send(
            "EVENT_ACK", child.channel.next_send_sequence, wrapped
        )
        child.expected_campaign_sequence += 1
        child.awaiting_campaign_sequence = None

    def _poll_child(
        self, child: LinuxSupervisorChildV180R12R4, deadline_ns: int
    ) -> None:
        remaining_ns = deadline_ns - self.monotonic_ns()
        if remaining_ns <= 0:
            raise V180R12R4RuntimeTimeout("measurement wall deadline expired")
        poller = select.poll()
        poller.register(
            child.channel.channel.fileno(),
            select.POLLIN | select.POLLHUP | select.POLLERR,
        )
        timeout_ms = max(1, min(60_000, (remaining_ns + 999_999) // 1_000_000))
        if not poller.poll(timeout_ms):
            if self.monotonic_ns() >= deadline_ns:
                raise V180R12R4RuntimeTimeout(
                    "measurement wall deadline expired"
                )
            return self._poll_child(child, deadline_ns)

    def receive_event_proposals(
        self, child: LinuxSupervisorChildV180R12R4, deadline_ns: int
    ) -> Iterable[ObserverEventProposalV180R12R4]:
        if type(child) is not LinuxSupervisorChildV180R12R4 or not child.start_sent:
            _fail("supervisor proposal stream began before authenticated START")
        while True:
            if child.awaiting_campaign_sequence is not None:
                _fail("supervisor emitted or awaited a proposal without durable ACK")
            self._poll_child(child, deadline_ns)
            received = child.channel.receive(allow_eof=True)
            if received is None:
                if not (
                    child.expected_campaign_sequence == 622
                    and child.awaiting_campaign_sequence is None
                    and child.channel.next_receive_sequence == 619
                    and child.channel.next_send_sequence == 620
                ):
                    _fail("supervisor EOF occurred outside exact WINDOW_CLOSED boundary")
                self.evidence_registry.assert_snapshot_transports_complete()
                child.stream_closed = True
                return
            frame_type, _frame_sequence, body = received
            if frame_type != "EVENT_PROPOSAL":
                _fail("supervisor child sent a non-proposal frame")
            proposal = ObserverEventProposalV180R12R4.from_signed_body_v180r12r4(
                body,
                protocol_id=self.authority.protocol_id,
                authorization_id=self.authority.authorization_id,
                authorization_evidence_id=self.authority.authorization_evidence_id,
                attempt_id=self.authority.attempt_id,
                evidence_registry=self.evidence_registry,
            )
            if proposal.campaign_event_sequence != child.expected_campaign_sequence:
                _fail("supervisor proposal sequence skipped or replayed")
            child.awaiting_campaign_sequence = proposal.campaign_event_sequence
            yield proposal
            if child.awaiting_campaign_sequence is not None:
                _fail("supervisor proposal was not durably ACKed by observer")

    def reap_supervisor(
        self,
        child: LinuxSupervisorChildV180R12R4,
        operation_id: str,
        deadline_ns: int,
    ) -> runtime.PidfdReapReceiptV180R12R4:
        if not (
            type(child) is LinuxSupervisorChildV180R12R4
            and child.stream_closed
            and not child.reaped
            and operation_id == child.birth_receipt.operation_id
        ):
            _fail("supervisor reap occurred outside exact stream closure")
        receipt = pidfd_reap_receipt_v180r12r4(
            launcher=self.launcher,
            handle=child.process,
            birth_receipt=child.birth_receipt,
            leaf_directory_fd=child.process.target_cgroup_fd,
            deadline_ns=deadline_ns,
            monotonic_ns=self.monotonic_ns,
        )
        child.reaped = True
        self.evidence_registry.register_existing(receipt)
        return receipt

    def close_supervisor_pidfd_after_reap_ack(
        self,
        child: LinuxSupervisorChildV180R12R4,
        supervisor_reap_receipt: runtime.PidfdReapReceiptV180R12R4,
    ) -> None:
        if not (
            type(child) is LinuxSupervisorChildV180R12R4
            and type(supervisor_reap_receipt)
            is runtime.PidfdReapReceiptV180R12R4
            and child.reaped
            and not child.pidfd_closed
            and supervisor_reap_receipt.birth_receipt is child.birth_receipt
        ):
            _fail("supervisor pidfd close crossed its reap ACK")
        close_reaped_pidfd_v180r12r4(child.process)
        child.channel.channel.close()
        child.pidfd_closed = True

    def observe_cgroup(
        self,
        cgroup: CgroupTreeV180R12R4,
        supervisor_reap_receipt: runtime.PidfdReapReceiptV180R12R4,
        operation_id: str,
    ) -> runtime.CgroupV2ObservationReceiptV180R12R4:
        worker_reaps = [
            value
            for value in self.evidence_registry.objects_by_id.values()
            if type(value) is runtime.PidfdReapReceiptV180R12R4
            and value.birth_receipt.process_role
            is runtime.ProcessRoleV180R12R4.WORKER
        ]
        if len(worker_reaps) != 1:
            _fail("cgroup observation lacks its exact worker reap receipt")
        receipt = self.cgroup_manager.observe_receipt(
            cgroup,
            supervisor_reap_receipt=supervisor_reap_receipt,
            worker_reap_receipt=worker_reaps[0],
            operation_id=operation_id,
        )
        self.evidence_registry.register_existing(receipt)
        return receipt

    def kill_cgroup(self, cgroup: CgroupTreeV180R12R4) -> None:
        self.cgroup_manager.kill(cgroup)

    def terminate_and_reap(self, child: LinuxSupervisorChildV180R12R4) -> None:
        if child.pidfd_closed:
            return
        primary: BaseException | None = None
        if not child.reaped:
            try:
                self.launcher.signal(child.process, signal.SIGKILL)
            except BaseException as error:
                primary = error
            try:
                self.launcher.reap(
                    child.process,
                    deadline_ns=self.context["hard_deadline_ns"],
                    monotonic_ns=self.monotonic_ns,
                )
                child.reaped = True
            except BaseException as error:
                if primary is None:
                    primary = error
        try:
            close_reaped_pidfd_v180r12r4(child.process)
            child.pidfd_closed = True
        except BaseException as error:
            if primary is None:
                primary = error
        try:
            child.channel.channel.close()
        except BaseException as error:
            if primary is None:
                primary = error
        if primary is not None:
            raise primary

    def observe_cgroup_failure(
        self, cgroup: CgroupTreeV180R12R4
    ) -> Mapping[str, Any]:
        return self.cgroup_manager.observe_failure(cgroup)

    def close_cgroup(self, cgroup: CgroupTreeV180R12R4) -> None:
        self.cgroup_manager.close(cgroup)


def _bounded_text_v180r12r4(
    value: Any,
    *,
    byte_cap: int,
    fallback: str,
) -> str:
    """Render one hostile value with base primitives under one byte cap.

    Failure handling must not dispatch to an attacker-controlled ``__str__``
    after the emergency heap reserve has been released.  ``BaseException``
    values use the base implementation directly; exact strings are already
    inert.  Other values are intentionally reduced to their exact type name.
    Encoding, truncation, and decoding remain inside the same guarded block.
    """

    try:
        if type(value) is str:
            rendered = value
        elif isinstance(value, BaseException):
            kind = type.__getattribute__(type(value), "__name__")
            rendered = kind + ": " + BaseException.__str__(value)
        else:
            kind = type.__getattribute__(type(value), "__name__")
            rendered = "<" + kind + ">"
        raw = str.encode(rendered, "utf-8", "replace")[:byte_cap]
        bounded = bytes.decode(raw, "utf-8", "replace")
        if bounded:
            return bounded
    except BaseException:
        pass
    return fallback


def _bounded_exception_text(error: BaseException) -> str:
    """Format hostile exceptions without allowing their __str__ to mask failure."""

    return _bounded_text_v180r12r4(
        error,
        byte_cap=4096,
        fallback="BaseException: <unprintable exception>",
    )


def _append_next_event_v180r12r4(
    campaign: runtime.CampaignMeasurementSupervisorV180R12R4,
    journal: CanonicalEventJournalV180R12R4,
    *,
    monotonic_ns: Callable[[], int],
    evidence_document: Any | None = None,
    measured_value: int | None = None,
) -> dict[str, Any]:
    if campaign.event_count >= len(campaign.success_event_plan):
        _fail("observer attempted to append past the exact 625-position plan")
    planned = campaign.success_event_plan[campaign.event_count]
    event = campaign.append_event(
        phase=planned.phase,
        actor_role=planned.actor_role,
        operation_id=planned.operation_id,
        event_kind=planned.event_kind,
        monotonic_ns=monotonic_ns(),
        evidence_document=evidence_document,
        measured_value=measured_value,
    )
    return journal.append(event.to_document())


def register_campaign_execution_closure_v180r12r4(
    *,
    campaign: runtime.CampaignMeasurementSupervisorV180R12R4,
    protocol_id: str,
    authorization_id: str,
    attempt_id: str,
    preregistered_by_schema: Mapping[str, Mapping[str, Any]],
    subject_result_document: Mapping[str, Any] | None,
    window_closure_document: Mapping[str, Any] | None,
    window_closed_ack: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Register the acyclic execution closure at its sole lifecycle point."""

    operation_manifest_document = preregistered_by_schema.get(
        "acfqp.campaign_operation_manifest.v180r12r4"
    )
    source_manifest_document = preregistered_by_schema.get(
        "acfqp.campaign_native_zero_source_manifest.v180r12r4"
    )
    import_inventory_document = preregistered_by_schema.get(
        "acfqp.campaign_native_zero_import_inventory.v180r12r4"
    )
    if (
        subject_result_document is None
        or window_closure_document is None
        or window_closed_ack is None
        or operation_manifest_document is None
        or source_manifest_document is None
        or import_inventory_document is None
    ):
        _fail("execution closure lacks one exact registered predecessor")
    execution_closure_document = ledger.issue_campaign_execution_closure_v180r12r4(
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        attempt_id=attempt_id,
        subject_id=_content_id(
            subject_result_document.get("subject_result_id"),
            "execution-closure subject ID",
        ),
        window_closed_event_id=_content_id(
            window_closed_ack.get("event_id"),
            "execution-closure window event ID",
        ),
        window_closure_receipt_id=_content_id(
            window_closure_document.get("window_closure_receipt_id"),
            "execution-closure window receipt ID",
        ),
        operation_manifest_id=_content_id(
            operation_manifest_document.get("campaign_operation_manifest_id"),
            "execution-closure operation manifest ID",
        ),
        source_manifest_id=_content_id(
            source_manifest_document.get("native_zero_source_manifest_id"),
            "execution-closure source manifest ID",
        ),
        import_inventory_id=_content_id(
            import_inventory_document.get("native_zero_import_inventory_id"),
            "execution-closure import inventory ID",
        ),
        precompiled_source_bundle_sha256=_content_id(
            source_manifest_document.get("precompiled_source_bundle_sha256"),
            "execution-closure source-bundle SHA256",
        ),
    )
    campaign.register_evidence_document(execution_closure_document)
    return execution_closure_document


def _topology_conformance_diagnostic_v180r12r4(
    error: BaseException,
) -> dict[str, Any] | None:
    """Retain the exact topology cause across partial-create cleanup wrapping."""

    candidates: tuple[BaseException, ...] = (error,)
    if isinstance(error, V180R12R4PartialCgroupCreateFailure):
        cause = BaseException.__getattribute__(error, "__cause__")
        if isinstance(cause, BaseException):
            candidates = (*candidates, cause)
    for candidate in candidates:
        if isinstance(
            candidate,
            runtime.CgroupTopologyConformanceErrorV180R12R4R3,
        ):
            return runtime.validate_topology_conformance_diagnostic_v180r12r4r3(
                candidate.conformance_diagnostic
            )
        if isinstance(
            candidate,
            runtime.CgroupTopologyConformanceErrorV180R12R4R4,
        ):
            return runtime.validate_topology_conformance_diagnostic_v180r12r4r4(
                candidate.conformance_diagnostic
            )
    return None


def _failure_document(
    *,
    protocol_id: str,
    authorization_id: str,
    attempt_id: str,
    journal: CanonicalEventJournalV180R12R4 | None,
    error: BaseException,
    cleanup_errors: Sequence[str],
    partial_artifact_observations: tuple[
        runtime.FailureArtifactObservationV180R12R4, ...
    ],
    cgroup_failure_observation: runtime.FailureCgroupObservationV180R12R4 | None,
    cgroup_topology_conformance_diagnostic: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        launch_substage = BaseException.__getattribute__(
            error, "launch_substage"
        )
        launch_errno = BaseException.__getattribute__(error, "launch_errno")
        launch_child_created = BaseException.__getattribute__(
            error, "launch_child_created"
        )
        launch_pidfd_acquired = BaseException.__getattribute__(
            error, "launch_pidfd_acquired"
        )
        launch_exec_observed = BaseException.__getattribute__(
            error, "launch_exec_observed"
        )
    except BaseException:
        launch_substage = launch_errno = None
        launch_child_created = launch_pidfd_acquired = False
        launch_exec_observed = False
    if not (
        launch_substage in TYPED_LAUNCH_FAILURE_SUBSTAGES
        and (launch_errno is None or type(launch_errno) is int and launch_errno > 0)
        and type(launch_child_created) is bool
        and type(launch_pidfd_acquired) is bool
        and type(launch_exec_observed) is bool
        and (not launch_pidfd_acquired or launch_child_created)
        and (not launch_exec_observed or launch_pidfd_acquired)
    ):
        launch_substage = launch_errno = None
        launch_child_created = launch_pidfd_acquired = False
        launch_exec_observed = False
    detail = _bounded_exception_text(error)
    if cleanup_errors:
        bounded_cleanup = tuple(
            _bounded_text_v180r12r4(
                value,
                byte_cap=512,
                fallback="<unprintable cleanup observation>",
            )
            for value in cleanup_errors[:32]
        )
        detail += "; cleanup=" + " | ".join(bounded_cleanup)
    message = _bounded_text_v180r12r4(
        detail,
        byte_cap=4096,
        fallback="BaseException: <unprintable failure>",
    )
    sequence = 0 if journal is None else journal.next_sequence
    if journal is None or sequence == 0:
        phase = runtime.CampaignPhaseV180R12R4.ATTEMPT
        operation_id = None
    else:
        position = min(sequence, len(journal.schedule) - 1)
        scheduled = journal.schedule[position]
        phase = runtime.CampaignPhaseV180R12R4(scheduled.phase)
        operation_id = scheduled.operation_id
    if cgroup_topology_conformance_diagnostic is not None:
        failure_code = (
            runtime.FailureCodeV180R12R4.CGROUP_TOPOLOGY_CONFORMANCE_FAILURE
        )
    elif isinstance(
        error, (V180R12R4RuntimeTimeout, V180R12R4CapViolation, MemoryError)
    ):
        failure_code = runtime.FailureCodeV180R12R4.CAP_VIOLATION
    elif journal is None or sequence == 0:
        failure_code = runtime.FailureCodeV180R12R4.PROTOCOL_FAILURE
    else:
        kind = journal.schedule[min(sequence, len(journal.schedule) - 1)].event_kind
        if kind == "INPUT_READ_INTENT" or kind == "INPUT_READ_OUTCOME":
            failure_code = runtime.FailureCodeV180R12R4.INPUT_DRIFT
        elif kind.startswith("STAGE_WRITE"):
            failure_code = runtime.FailureCodeV180R12R4.STAGE_FAILURE
        elif kind.startswith("MOUNT_VISIBILITY"):
            failure_code = runtime.FailureCodeV180R12R4.FD_VISIBILITY_FAILURE
        elif kind.startswith("PROCESS_BIRTH"):
            failure_code = (
                runtime.FailureCodeV180R12R4.SUPERVISOR_BIRTH_FAILURE
                if phase is runtime.CampaignPhaseV180R12R4.STAGE
                else runtime.FailureCodeV180R12R4.WORKER_BIRTH_FAILURE
            )
        elif kind == "PROCESS_REAP":
            failure_code = runtime.FailureCodeV180R12R4.PROCESS_REAP_FAILURE
        elif kind.startswith("SUBJECT_WRITE"):
            failure_code = runtime.FailureCodeV180R12R4.SUBJECT_WRITE_FAILURE
        elif kind == "SUBJECT_COMMIT" or phase is runtime.CampaignPhaseV180R12R4.COMMIT:
            failure_code = runtime.FailureCodeV180R12R4.SUBJECT_COMMIT_FAILURE
        elif kind == "WINDOW_CLOSED" or phase is runtime.CampaignPhaseV180R12R4.WINDOW_CLOSE:
            failure_code = runtime.FailureCodeV180R12R4.WINDOW_CLOSE_FAILURE
        elif kind == "CGROUP_OBSERVED":
            failure_code = runtime.FailureCodeV180R12R4.CGROUP_OBSERVATION_FAILURE
        elif kind == "LEDGER_CLOSED":
            failure_code = runtime.FailureCodeV180R12R4.LEDGER_FAILURE
        elif phase is runtime.CampaignPhaseV180R12R4.WORKER:
            failure_code = runtime.FailureCodeV180R12R4.WORKER_REPLAY_FAILURE
        elif phase is runtime.CampaignPhaseV180R12R4.STAGE:
            failure_code = runtime.FailureCodeV180R12R4.STAGE_FAILURE
        else:
            failure_code = runtime.FailureCodeV180R12R4.PROTOCOL_FAILURE
    process_may_remain = bool(cleanup_errors) or (
        cgroup_failure_observation is not None
        and (
            cgroup_failure_observation.kill_outcome.startswith("ERROR:")
            or cgroup_failure_observation.reap_outcome.startswith("ERROR:")
            or 1
            in {
                cgroup_failure_observation.root_populated,
                cgroup_failure_observation.supervisor_leaf_populated,
                cgroup_failure_observation.worker_leaf_populated,
            }
        )
    )
    output_may_exist = any(
        row.state != "ABSENT" for row in partial_artifact_observations
    )
    return runtime.CampaignFailureStateV180R12R4(
        protocol_id,
        authorization_id,
        attempt_id,
        failure_code,
        phase,
        operation_id,
        None if journal is None else journal.previous_event_id,
        sequence,
        message,
        process_may_remain,
        output_may_exist,
        partial_artifact_observations,
        cgroup_failure_observation,
        cgroup_topology_conformance_diagnostic=(
            cgroup_topology_conformance_diagnostic
        ),
        launch_substage=launch_substage,
        launch_errno=launch_errno,
        launch_child_created=launch_child_created,
        launch_pidfd_acquired=launch_pidfd_acquired,
        launch_exec_observed=launch_exec_observed,
    ).to_document()


def _failure_cgroup_observation_v180r12r4(
    raw: Mapping[str, Any] | None,
    *,
    kill_outcome: str,
    reap_outcome: str,
    close_outcome: str,
    observation_errors: Sequence[str] = (),
) -> runtime.FailureCgroupObservationV180R12R4:
    raw = {} if raw is None else dict(raw)
    combined = [
        *raw.get("observation_errors", ()),
        *observation_errors,
    ]
    fallback_nodes = tuple(
        {
            "role": role,
            "path": None,
            "state": "READ_ERROR",
            "mode": None,
            "nlink": None,
            "device": None,
            "inode": None,
            "populated": None,
            "process_count": None,
            "read_error_type": "RuntimeBoundary",
            "read_error_message": (
                "exact partial cgroup node observation unavailable"
            ),
        }
        for role in ("MEASUREMENT_ROOT", "SUPERVISOR", "WORKER")
    )
    supplied_nodes = raw.get("node_observations")
    if not (
        type(supplied_nodes) in {tuple, list}
        and len(supplied_nodes) == 3
        and all(type(row) is dict for row in supplied_nodes)
        and all(
            set(row) == runtime.FAILURE_CGROUP_NODE_OBSERVATION_KEYS
            for row in supplied_nodes
        )
        and tuple(row["role"] for row in supplied_nodes)
        == ("MEASUREMENT_ROOT", "SUPERVISOR", "WORKER")
    ):
        supplied_nodes = fallback_nodes
    try:
        node_observations = tuple(
            runtime.FailureCgroupNodeObservationV180R12R4(
                row["role"], row["path"], row["state"], row["mode"],
                row["nlink"], row["device"], row["inode"], row["populated"],
                row["process_count"], row["read_error_type"],
                row["read_error_message"],
            )
            for row in supplied_nodes
        )
    except BaseException:
        node_observations = tuple(
            runtime.FailureCgroupNodeObservationV180R12R4(
                row["role"], row["path"], row["state"], row["mode"],
                row["nlink"], row["device"], row["inode"], row["populated"],
                row["process_count"], row["read_error_type"],
                row["read_error_message"],
            )
            for row in fallback_nodes
        )
    return runtime.FailureCgroupObservationV180R12R4(
        raw.get("root_populated"),
        raw.get("supervisor_leaf_populated"),
        raw.get("worker_leaf_populated"),
        raw.get("root_process_count"),
        raw.get("supervisor_leaf_process_count"),
        raw.get("worker_leaf_process_count"),
        raw.get("memory_peak_bytes"),
        raw.get("pids_peak"),
        raw.get("memory_events"),
        raw.get("pids_events"),
        kill_outcome,
        reap_outcome,
        close_outcome,
        tuple(
            _bounded_text_v180r12r4(
                value,
                byte_cap=512,
                fallback="unprintable observation error",
            )
            for value in combined[:32]
        ),
        node_observations,
    )


def run_one_shot_outer_v180r12r4(
    *,
    store: DurableStoreV180R12R4,
    adapter: OuterEffectAdapterV180R12R4,
    attempt_document: Mapping[str, Any],
    attempt_authority: CampaignAttemptAuthorityV180R12R4,
    protocol_id: str,
    authorization_id: str,
    attempt_id: str,
    campaign_deadline_ns: int,
    forbidden_progress_paths: Sequence[str],
    preregistered_evidence_documents: Sequence[Any] = (),
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
    pre_attempt_revalidate: Callable[[], None] | None = None,
) -> CanonicalEventJournalV180R12R4:
    """Run one injected lifecycle with observer-owned event 0 and final three."""

    if (
        type(attempt_authority) is not CampaignAttemptAuthorityV180R12R4
        or protocol_id != attempt_authority.protocol_id
        or authorization_id != attempt_authority.authorization_id
        or attempt_id != attempt_authority.attempt_id
    ):
        _fail("outer lifecycle IDs differ from exact campaign attempt authority")
    _check_campaign_deadline_v180r12r4(
        campaign_deadline_ns,
        monotonic_ns=monotonic_ns,
        boundary="one-shot entry",
    )

    campaign = runtime.CampaignMeasurementSupervisorV180R12R4(
        protocol_id=protocol_id,
        authorization_id=authorization_id,
        attempt_id=attempt_id,
    )
    cgroup: Any = None
    child: Any = None
    journal: CanonicalEventJournalV180R12R4 | None = None
    failure_reserve: bytearray | None = None
    owned_attempt = False
    ownership_token = AttemptOwnershipTokenV180R12R4()
    terminal_publication_token = TerminalPublicationTokenV180R12R4()
    watchdog = CampaignDeadlineWatchdogV180R12R4(
        campaign_deadline_ns, monotonic_ns=monotonic_ns
    )
    try:
        watchdog.arm()
        if pre_attempt_revalidate is not None:
            if not callable(pre_attempt_revalidate):
                _fail("pre-ATTEMPT T2 revalidation hook changed")
            pre_attempt_revalidate()
        claim = claim_attempt_before_effects_v180r12r4(
            store,
            attempt_document,
            authority=attempt_authority,
            forbidden_progress_paths=forbidden_progress_paths,
            ownership_token=ownership_token,
        )
        failure_reserve = claim.failure_reserve
        owned_attempt = True
        journal = CanonicalEventJournalV180R12R4(
            store,
            protocol_id=protocol_id,
            authorization_id=authorization_id,
            attempt_id=attempt_id,
        )
        allowed_preregistered_schemas = {
            "acfqp.campaign_operation_manifest.v180r12r4",
            "acfqp.campaign_native_zero_source_manifest.v180r12r4",
            "acfqp.campaign_native_zero_import_inventory.v180r12r4",
        }
        supplied_preregistered_schemas: list[str] = []
        preregistered_by_schema: dict[str, dict[str, Any]] = {}
        for document in preregistered_evidence_documents:
            supplied = (
                document.to_document()
                if callable(getattr(document, "to_document", None))
                else document
            )
            schema = supplied.get("schema") if type(supplied) is dict else None
            if schema not in allowed_preregistered_schemas:
                _fail(
                    "outer preregistration included a runtime-owned or foreign "
                    "evidence schema"
                )
            supplied_preregistered_schemas.append(schema)
            preregistered_by_schema[schema] = supplied
            campaign.register_evidence_document(document)
        if len(supplied_preregistered_schemas) != len(
            set(supplied_preregistered_schemas)
        ):
            _fail("outer preregistration repeated an evidence schema")
        _append_next_event_v180r12r4(
            campaign,
            journal,
            monotonic_ns=monotonic_ns,
            evidence_document=attempt_document,
        )
        _check_campaign_deadline_v180r12r4(
            campaign_deadline_ns,
            monotonic_ns=monotonic_ns,
            boundary="durable ATTEMPT_OPEN",
        )
        if campaign.success_event_plan[campaign.event_count].event_kind != (
            "PROCESS_BIRTH_INTENT"
        ):
            _fail("observer event 0 did not advance to supervisor birth intent")

        # Event 0 is durably fsynced above.  No input or cgroup effect may
        # precede it.  create_cgroup must clean any partial tree internally if
        # it cannot return its typed topology receipt.
        cgroup, topology_receipt = adapter.create_cgroup(attempt_id)
        _check_campaign_deadline_v180r12r4(
            campaign_deadline_ns,
            monotonic_ns=monotonic_ns,
            boundary="cgroup creation",
        )
        campaign.register_evidence_document(topology_receipt)
        _append_next_event_v180r12r4(
            campaign, journal, monotonic_ns=monotonic_ns
        )
        birth_plan = campaign.success_event_plan[campaign.event_count]
        child, supervisor_birth_receipt = adapter.launch_supervisor(
            cgroup, birth_plan.operation_id, campaign_deadline_ns
        )
        birth_ack = _append_next_event_v180r12r4(
            campaign,
            journal,
            monotonic_ns=monotonic_ns,
            evidence_document=supervisor_birth_receipt,
            measured_value=1,
        )
        adapter.acknowledge_event(child, birth_ack)

        subject_result_document: dict[str, Any] | None = None
        window_closure_document: dict[str, Any] | None = None
        window_closed_ack: dict[str, Any] | None = None
        for proposal in adapter.receive_event_proposals(
            child, campaign_deadline_ns
        ):
            _check_campaign_deadline_v180r12r4(
                campaign_deadline_ns,
                monotonic_ns=monotonic_ns,
                boundary="authenticated proposal receive",
            )
            if type(proposal) is not ObserverEventProposalV180R12R4:
                _fail("child stream yielded an untyped observer proposal")
            planned = campaign.success_event_plan[campaign.event_count]
            direct_evidence_id = None
            if proposal.evidence_document is not None:
                direct_value = proposal.evidence_document
                direct_document = direct_value
                schema = getattr(direct_value, "get", lambda *_: None)("schema")
                if type(schema) is not str:
                    to_document = getattr(direct_value, "to_document", None)
                    if callable(to_document):
                        direct_document = to_document()
                        schema = direct_document.get("schema")
                _direct_document, direct_evidence_id = (
                    _validate_registered_evidence_document_v180r12r4(
                        direct_document, expected_schema=schema
                    )
                )
                if schema == "acfqp.campaign_window_closure_receipt.v180r12r4":
                    if (
                        window_closure_document is not None
                        and window_closure_document != direct_document
                    ):
                        _fail("child stream supplied two window-closure documents")
                    window_closure_document = direct_document
            expected_signed_payload = runtime.campaign_event_payload_v180r12r4(
                event_kind=planned.event_kind,
                evidence_id=direct_evidence_id,
                measured_value=proposal.measured_value,
                auxiliary_values=(),
            )
            if (
                proposal.campaign_event_sequence != campaign.event_count
                or proposal.phase != planned.phase
                or proposal.actor_role != planned.actor_role
                or proposal.event_kind != planned.event_kind
                or proposal.operation_id != planned.operation_id
                or proposal.payload != expected_signed_payload
                or planned.event_kind
                in {"PROCESS_REAP", "CGROUP_OBSERVED", "LEDGER_CLOSED"}
                and planned.actor_role == "OBSERVER"
            ):
                _fail("child proposed a foreign or observer-owned event")
            for document in proposal.supporting_evidence_documents:
                supporting_document = (
                    document.to_document()
                    if callable(getattr(document, "to_document", None))
                    else document
                )
                if (
                    type(supporting_document) is dict
                    and supporting_document.get("schema")
                    == "acfqp.campaign_measurement_subject_result.v180r12r4"
                ):
                    if (
                        subject_result_document is not None
                        and subject_result_document != supporting_document
                    ):
                        _fail("child stream supplied two subject-result documents")
                    subject_result_document = supporting_document
                campaign.register_evidence_document(document)
            ack = _append_next_event_v180r12r4(
                campaign,
                journal,
                monotonic_ns=monotonic_ns,
                evidence_document=proposal.evidence_document,
                measured_value=proposal.measured_value,
            )
            adapter.acknowledge_event(child, ack)
            if planned.event_kind == "WINDOW_CLOSED":
                if window_closed_ack is not None:
                    _fail("child stream repeated the WINDOW_CLOSED event")
                window_closed_ack = ack
        if (
            campaign.event_count != SUCCESS_EVENT_COUNT - 3
            or campaign.success_event_plan[campaign.event_count].event_kind
            != "PROCESS_REAP"
            or campaign.success_event_plan[campaign.event_count].actor_role
            != "OBSERVER"
        ):
            _fail("child stream did not end exactly after WINDOW_CLOSED")

        # The execution closure is not an event receipt.  Its first acyclic
        # construction point is after the exact WINDOW_CLOSED event is durable
        # (so its event ID exists) and before LEDGER_CLOSED prevents further
        # evidence registration.  Build it solely from already registered
        # authority and child-produced evidence; the finalizer must receive the
        # resulting exact 328-document inventory rather than synthesize it.
        register_campaign_execution_closure_v180r12r4(
            campaign=campaign,
            protocol_id=protocol_id,
            authorization_id=authorization_id,
            attempt_id=attempt_id,
            preregistered_by_schema=preregistered_by_schema,
            subject_result_document=subject_result_document,
            window_closure_document=window_closure_document,
            window_closed_ack=window_closed_ack,
        )

        reap_plan = campaign.success_event_plan[campaign.event_count]
        _check_campaign_deadline_v180r12r4(
            campaign_deadline_ns,
            monotonic_ns=monotonic_ns,
            boundary="supervisor reap entry",
        )
        supervisor_reap_receipt = adapter.reap_supervisor(
            child, reap_plan.operation_id, campaign_deadline_ns
        )
        _check_campaign_deadline_v180r12r4(
            campaign_deadline_ns,
            monotonic_ns=monotonic_ns,
            boundary="supervisor reap observation",
        )
        _append_next_event_v180r12r4(
            campaign,
            journal,
            monotonic_ns=monotonic_ns,
            evidence_document=supervisor_reap_receipt,
        )
        adapter.close_supervisor_pidfd_after_reap_ack(
            child, supervisor_reap_receipt
        )
        _check_campaign_deadline_v180r12r4(
            campaign_deadline_ns,
            monotonic_ns=monotonic_ns,
            boundary="supervisor pidfd close",
        )
        child = None
        cgroup_plan = campaign.success_event_plan[campaign.event_count]
        observation_receipt = adapter.observe_cgroup(
            cgroup, supervisor_reap_receipt, cgroup_plan.operation_id
        )
        _check_campaign_deadline_v180r12r4(
            campaign_deadline_ns,
            monotonic_ns=monotonic_ns,
            boundary="retained cgroup observation",
        )
        _append_next_event_v180r12r4(
            campaign,
            journal,
            monotonic_ns=monotonic_ns,
            evidence_document=observation_receipt,
            measured_value=observation_receipt.memory_peak_bytes,
        )
        _check_campaign_deadline_v180r12r4(
            campaign_deadline_ns,
            monotonic_ns=monotonic_ns,
            boundary="durable CGROUP_OBSERVED",
        )
        _append_next_event_v180r12r4(
            campaign, journal, monotonic_ns=monotonic_ns
        )
        _check_campaign_deadline_v180r12r4(
            campaign_deadline_ns,
            monotonic_ns=monotonic_ns,
            boundary="durable LEDGER_CLOSED",
        )
        journal.assert_complete()
        campaign.assert_success_schedule_complete()
        adapter.close_cgroup(cgroup)
        _check_campaign_deadline_v180r12r4(
            campaign_deadline_ns,
            monotonic_ns=monotonic_ns,
            boundary="cgroup descriptor and namespace close",
        )
        cgroup = None
        _check_campaign_deadline_v180r12r4(
            campaign_deadline_ns,
            monotonic_ns=monotonic_ns,
            boundary="finalizer retained-input construction entry",
        )
        finalizer_inputs = build_finalize_success_inputs_v180r12r4(
            campaign=campaign,
            journal=journal,
        )
        _check_campaign_deadline_v180r12r4(
            campaign_deadline_ns,
            monotonic_ns=monotonic_ns,
            boundary="finalizer retained-input construction return",
        )
        finalize_and_materialize_success_v180r12r4(
            store=store,
            inputs=finalizer_inputs,
            campaign_deadline_ns=campaign_deadline_ns,
            monotonic_ns=monotonic_ns,
            publication_token=terminal_publication_token,
        )
        watchdog.teardown()
        failure_reserve.clear()
        failure_reserve = None
        return journal
    except BaseException as primary:
        # Neutralize SIGALRM before examining the exception, releasing the
        # reserve, allocating cleanup containers, or formatting any failure.
        # A one-shot SIGALRM can be delivered after this ``except`` suite has
        # begun but before the callee's first protected bytecode.  Guard the
        # call site as well as the helper body so that an owned ATTEMPT always
        # reaches its typed failure closure with the original primary intact.
        try:
            watchdog.neutralize_preserving_primary()
        except BaseException as neutralization_error:
            watchdog._remember_cleanup_error(neutralization_error)
            try:
                watchdog.neutralize_preserving_primary()
            except BaseException as retry_error:
                watchdog._remember_cleanup_error(retry_error)
        if ownership_token.owned:
            failure_reserve = ownership_token.failure_reserve
            owned_attempt = True
        if isinstance(primary, V180R12R4OwnedAttemptFailure):
            failure_reserve = primary.failure_reserve
            owned_attempt = True
            primary = primary.__cause__ or primary
        if terminal_publication_token.started:
            # TERMINAL is the final campaign namespace mutation.  Any failure
            # after TERMINAL_PUBLICATION_ATTEMPT_ENTRY belongs to the retained
            # outer launch attempt, which can observe absent, partial, or exact
            # TERMINAL state.
            # Writing CAMPAIGN_FAILURE here would violate the frozen mutual-
            # exclusion contract.
            if failure_reserve is not None:
                failure_reserve.clear()
                failure_reserve = None
            watchdog.restore()
            watchdog_cleanup_error = watchdog.first_cleanup_error()
            if watchdog_cleanup_error is not None:
                rendered_watchdog_cleanup = _bounded_exception_text(
                    watchdog_cleanup_error
                )
                try:
                    inherited_cleanup = BaseException.__getattribute__(
                        primary, "cleanup_errors"
                    )
                except BaseException:
                    inherited_cleanup = ()
                if type(inherited_cleanup) is not tuple:
                    inherited_cleanup = ()
                try:
                    BaseException.__setattr__(
                        primary,
                        "cleanup_errors",
                        (
                            *inherited_cleanup[:31],
                            "post_terminal_campaign_watchdog:"
                            + rendered_watchdog_cleanup,
                        ),
                    )
                    if BaseException.__getattribute__(primary, "__cause__") is None:
                        BaseException.__setattr__(
                            primary,
                            "__cause__",
                            V180R12R4RuntimeError(
                                "post-terminal watchdog cleanup failed: "
                                + rendered_watchdog_cleanup
                            ),
                        )
                except BaseException:
                    pass
            try:
                BaseException.__setattr__(primary, "__traceback__", None)
            except BaseException:
                pass
            raise primary
        if isinstance(primary, V180R12R4ReplayForbidden) or not owned_attempt:
            watchdog.restore()
            raise
        # This must be the first allocating-path action after ownership is
        # known.  In particular, detach/format/list construction happens only
        # after the exact 4MiB committed heap reserve has been surrendered.
        if failure_reserve is not None:
            failure_reserve.clear()
            failure_reserve = None
        watchdog.restore()
        try:
            BaseException.__setattr__(primary, "__traceback__", None)
        except BaseException:
            pass
        cgroup_topology_conformance_diagnostic = (
            _topology_conformance_diagnostic_v180r12r4(primary)
        )
        cleanup_errors: list[str] = []
        watchdog_cleanup_error = watchdog.first_cleanup_error()
        if watchdog_cleanup_error is not None:
            cleanup_errors.append(
                "campaign_watchdog:"
                + _bounded_exception_text(watchdog_cleanup_error)
            )
        try:
            inherited_cleanup = BaseException.__getattribute__(
                primary, "cleanup_errors"
            )
        except BaseException:
            inherited_cleanup = ()
        if type(inherited_cleanup) is tuple:
            cleanup_errors.extend(
                "partial_cgroup_create:"
                + _bounded_text_v180r12r4(
                    value,
                    byte_cap=512,
                    fallback="<unprintable cleanup observation>",
                )
                for value in inherited_cleanup[:32]
            )
        try:
            inherited_partial_nodes = BaseException.__getattribute__(
                primary, "node_observations"
            )
        except BaseException:
            inherited_partial_nodes = ()
        kill_outcome = "NOT_ATTEMPTED"
        reap_outcome = "NOT_ATTEMPTED"
        close_outcome = "NOT_ATTEMPTED"
        cgroup_failure_raw: Mapping[str, Any] | None = None
        cgroup_observation_errors: list[str] = []
        if type(inherited_partial_nodes) is tuple and len(inherited_partial_nodes) == 3:
            cgroup_failure_raw = {"node_observations": inherited_partial_nodes}
            kill_outcome = "NOT_AVAILABLE_PARTIAL_CREATE"
            reap_outcome = "NO_CHILD_HANDLE"
            close_outcome = "INTERNAL_CLEANUP_INCOMPLETE"
        if cgroup is not None:
            try:
                adapter.kill_cgroup(cgroup)
                kill_outcome = "SUCCESS"
            except BaseException as error:
                rendered = _bounded_exception_text(error)
                kill_outcome = "ERROR:" + rendered[:500]
                cleanup_errors.append("cgroup.kill:" + rendered)
        if child is not None:
            try:
                adapter.terminate_and_reap(child)
                reap_outcome = "SUCCESS"
            except BaseException as error:
                rendered = _bounded_exception_text(error)
                reap_outcome = "ERROR:" + rendered[:500]
                cleanup_errors.append("pidfd_reap:" + rendered)
        elif cgroup is not None:
            reap_outcome = "NO_CHILD_HANDLE"
        if cgroup is not None:
            observe_failure = getattr(adapter, "observe_cgroup_failure", None)
            if callable(observe_failure):
                try:
                    cgroup_failure_raw = observe_failure(cgroup)
                except BaseException as error:
                    cgroup_observation_errors.append(
                        _bounded_exception_text(error)[:512]
                    )
            else:
                cgroup_observation_errors.append(
                    "adapter lacks bounded failure cgroup observation"
                )
        if cgroup is not None:
            try:
                adapter.close_cgroup(cgroup)
                close_outcome = "SUCCESS"
            except BaseException as error:
                rendered = _bounded_exception_text(error)
                close_outcome = "ERROR:" + rendered[:500]
                cleanup_errors.append("cgroup_close:" + rendered)
        try:
            artifact_observations = store.observe_failure_progress()
        except BaseException as error:
            rendered_observation_error = _bounded_exception_text(error)[:512]
            artifact_observations = tuple(
                runtime.FailureArtifactObservationV180R12R4(
                    relative_path,
                    kind,
                    "READ_ERROR",
                    None,
                    None,
                    None,
                    None,
                    None,
                    "BaseException",
                    rendered_observation_error,
                )
                for relative_path, kind in (
                    runtime.FAILURE_ARTIFACT_FIXED_PATH_KIND_ROWS
                )
            )
        cgroup_failure_observation = (
            None
            if cgroup is None and cgroup_failure_raw is None
            else _failure_cgroup_observation_v180r12r4(
                cgroup_failure_raw,
                kill_outcome=kill_outcome,
                reap_outcome=reap_outcome,
                close_outcome=close_outcome,
                observation_errors=cgroup_observation_errors,
            )
        )
        failure = _failure_document(
            protocol_id=protocol_id,
            authorization_id=authorization_id,
            attempt_id=attempt_id,
            journal=journal,
            error=primary,
            cleanup_errors=cleanup_errors,
            partial_artifact_observations=artifact_observations,
            cgroup_failure_observation=cgroup_failure_observation,
            cgroup_topology_conformance_diagnostic=(
                cgroup_topology_conformance_diagnostic
            ),
        )
        try:
            store.write_once(FAILURE_RELATIVE_PATH, _canonical(failure))
        except BaseException as failure_write_error:
            raise V180R12R4RuntimeError(
                "primary failure preserved ("
                + _bounded_exception_text(primary)
                + "); failure artifact write also failed: "
                + _bounded_exception_text(failure_write_error)
            ) from primary
        raise primary


def bootstrap_entrypoint_v180r12r4(
    verified_context: Mapping[str, Any],
) -> None:
    """Consume the retained bootstrap's verified measurement context once."""

    if (
        type(verified_context) is not types.MappingProxyType
        or tuple(verified_context) != VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS
        or verified_context.get("target") != "measurement"
    ):
        _fail("measurement bootstrap entrypoint context shape changed")
    store = DurableStoreV180R12R4(Path(verified_context["repository_root"]))
    repository_root_fd = -1
    try:
        replayed = replay_external_authority_documents_v180r12r4(
            verified_context, store=store
        )
        context = revalidate_external_measurement_pre_attempt_v180r12r4(
            verified_context, replayed_documents=replayed, store=store
        )
        authority = CampaignAttemptAuthorityV180R12R4.from_external_context(
            context
        )
        attempt_document, operation_manifest = (
            build_campaign_attempt_record_v180r12r4(authority)
        )
        normalized_rows = _validate_native_zero_precompiled_rows_v180r12r4(
            context["native_zero_precompiled_source_rows"]
        )
        source_manifest = ledger.issue_native_zero_source_manifest_v180r12r4(
            protocol_id=authority.protocol_id,
            authorization_id=authority.authorization_id,
            attempt_id=authority.attempt_id,
            operation_manifest_id=operation_manifest[
                "campaign_operation_manifest_id"
            ],
            prelaunch_launch_manifest_sha256=(
                authority.prelaunch_launch_manifest_sha256
            ),
            precompiled_source_bundle_sha256=context[
                "precompiled_source_bundle_sha256"
            ],
            precompiled_source_rows=normalized_rows,
        )
        import_inventory = ledger.issue_native_zero_import_inventory_v180r12r4(
            protocol_id=authority.protocol_id,
            authorization_id=authority.authorization_id,
            attempt_id=authority.attempt_id,
            source_manifest=source_manifest,
        )
        repository_root_fd = os.open(
            context["repository_root"],
            os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        adapter = LinuxOuterEffectAdapterV180R12R4(
            context=context,
            authority=authority,
            attempt_document=attempt_document,
            operation_manifest_document=operation_manifest,
            native_zero_source_manifest_document=source_manifest,
            native_zero_import_inventory_document=import_inventory,
            repository_root_fd=repository_root_fd,
        )

        frozen_t2 = _thaw_json_value(
            context["production_runtime_placement_t2"]
        )

        def revalidate_t2_immediately_before_attempt_o_excl() -> None:
            observed = _revalidate_production_source_placement_v180r12r4(
                context,
                schema=PRODUCTION_RUNTIME_PLACEMENT_T2_SCHEMA,
                boundary="T2_BEFORE_SCIENTIFIC_ATTEMPT_O_EXCL",
                require_progress_absent=True,
            )
            if observed != frozen_t2:
                _fail("final T2 observation changed before scientific ATTEMPT")

        run_one_shot_outer_v180r12r4(
            store=store,
            adapter=adapter,
            attempt_document=attempt_document,
            attempt_authority=authority,
            protocol_id=authority.protocol_id,
            authorization_id=authority.authorization_id,
            attempt_id=authority.attempt_id,
            campaign_deadline_ns=context["campaign_deadline_ns"],
            forbidden_progress_paths=tuple(
                path for path, _kind in FAILURE_ARTIFACT_FIXED_PATH_KINDS
            ),
            preregistered_evidence_documents=(
                operation_manifest,
                source_manifest,
                import_inventory,
            ),
            pre_attempt_revalidate=(
                revalidate_t2_immediately_before_attempt_o_excl
            ),
        )
    finally:
        if repository_root_fd >= 0:
            os.close(repository_root_fd)
        store.close()


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    raise V180R12R4RuntimeError(
        "direct invocation is forbidden; use the frozen prelaunch launcher with "
        "an exact authorization-bound runtime adapter"
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        raise
