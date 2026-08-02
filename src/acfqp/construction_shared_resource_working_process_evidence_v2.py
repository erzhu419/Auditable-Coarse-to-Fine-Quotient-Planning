"""Raw V2 evidence for working-set peak and production process launches.

The recorder owns one retained ``memory.peak`` open-file description and an
attempt-local lifecycle journal.  It derives values only from bytes read by
the recorder and from positive native clone edges joined to live pidfds,
kernel-authenticated broker frames, direct ``P_PIDFD`` reaps, and post-exec
no-spawn observations.  Callers cannot submit a peak, launch total, sequence,
or cutoff.

This module is deliberately raw-only.  Component and event IDs use centrally
registered role-separated content domains.  The resulting components match
the exact schemas registered by
``construction_shared_resource_resolution_v2`` but do not install either
semantic replayer and cannot authorize a CounterRecord or formal value.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import fcntl
import hashlib
import os
import re
import stat
import threading
from typing import Any, Mapping, NoReturn

from acfqp import construction_shared_resource_resolution_v2 as resolution_v2
from acfqp import v075_k7_authenticated_broker_channel_v2 as channel_v2
from acfqp import v075_k7_outer_attempt_broker_ipc_v1 as ipc_v1
from acfqp import v075_k7_production_role_manifest_v2 as manifest_v2
from acfqp import v075_k7_production_role_sandbox_v2 as sandbox_v2
from acfqp.phase3e_ids import (
    CONSTRUCTION_SHARED_RESOURCE_WORKING_PROCESS_EVENT_V2_DOMAIN,
    V075_K7_CGROUP_EMPTY_ATTESTATION_V2_DOMAIN,
    V075_K7_MEMORY_PEAK_POST_READ_V2_DOMAIN,
    V075_K7_MEMORY_PEAK_PRE_READ_V2_DOMAIN,
    V075_K7_NO_SPAWN_ATTESTATION_V2_DOMAIN,
    V075_K7_OPERATIONAL_CUTOFF_ATTESTATION_V2_DOMAIN,
    V075_K7_PIDFD_REAP_ATTESTATION_V2_DOMAIN,
    V075_K7_PROCESS_LIFECYCLE_JOURNAL_V2_DOMAIN,
    V075_K7_SAME_OFD_ATTESTATION_V2_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.17"
PROFILE_KEY = "construction_shared_resource_working_process_evidence_v2"

MEMORY_PATH = "memory.working_bytes_peak"
PROCESS_PATH = "process.launches"
SUPPORTED_PATHS = (MEMORY_PATH, PROCESS_PATH)
EXPECTED_ROLES = ("WORKER", "BUSINESS")

CUTOFF_SCHEMA_ID = "acfqp.v075_k7_operational_cutoff_attestation.v2"
CGROUP_EMPTY_SCHEMA_ID = "acfqp.v075_k7_cgroup_empty_attestation.v2"
MEMORY_POST_SCHEMA_ID = "acfqp.v075_k7_memory_peak_post_read.v2"
MEMORY_PRE_SCHEMA_ID = "acfqp.v075_k7_memory_peak_pre_read.v2"
SAME_OFD_SCHEMA_ID = "acfqp.v075_k7_same_ofd_attestation.v2"
NO_SPAWN_SCHEMA_ID = "acfqp.v075_k7_no_spawn_attestation.v2"
PIDFD_REAP_SCHEMA_ID = "acfqp.v075_k7_pidfd_reap_attestation.v2"
PROCESS_JOURNAL_SCHEMA_ID = "acfqp.v075_k7_process_lifecycle_journal.v2"

WORKING_PROCESS_EVENT_V2_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_WORKING_PROCESS_EVENT_V2_DOMAIN
)
_COMPONENT_DOMAIN = {
    CUTOFF_SCHEMA_ID: V075_K7_OPERATIONAL_CUTOFF_ATTESTATION_V2_DOMAIN,
    CGROUP_EMPTY_SCHEMA_ID: V075_K7_CGROUP_EMPTY_ATTESTATION_V2_DOMAIN,
    MEMORY_POST_SCHEMA_ID: V075_K7_MEMORY_PEAK_POST_READ_V2_DOMAIN,
    MEMORY_PRE_SCHEMA_ID: V075_K7_MEMORY_PEAK_PRE_READ_V2_DOMAIN,
    SAME_OFD_SCHEMA_ID: V075_K7_SAME_OFD_ATTESTATION_V2_DOMAIN,
    NO_SPAWN_SCHEMA_ID: V075_K7_NO_SPAWN_ATTESTATION_V2_DOMAIN,
    PIDFD_REAP_SCHEMA_ID: V075_K7_PIDFD_REAP_ATTESTATION_V2_DOMAIN,
    PROCESS_JOURNAL_SCHEMA_ID: V075_K7_PROCESS_LIFECYCLE_JOURNAL_V2_DOMAIN,
}
REQUESTED_PHASE3E_DOMAIN_TAGS = tuple(
    sorted({WORKING_PROCESS_EVENT_V2_DOMAIN, *_COMPONENT_DOMAIN.values()})
)

MAX_CONTROL_BYTES = 4096
_ASCII_UINT = re.compile(rb"(?:0|[1-9][0-9]*)\n?\Z")

_BUNDLE_ISSUER = object()
_REPLAY_ISSUER = object()


class ConstructionSharedResourceWorkingProcessEvidenceV2Error(RuntimeError):
    """The retained OFD, lifecycle journal, or raw replay failed closed."""


class WorkingProcessSessionStateV2(str, Enum):
    OPEN = "OPEN"
    CLOSED_EXACT = "CLOSED_EXACT"
    CLOSED_FAILURE_PREFIX = "CLOSED_FAILURE_PREFIX"


class WorkingProcessClosureKindV2(str, Enum):
    EXACT = "EXACT"
    FAILURE_PREFIX = "FAILURE_PREFIX"


class LifecycleEventKindV2(str, Enum):
    MEMORY_PEAK_RESET_AND_PRE_READ = "MEMORY_PEAK_RESET_AND_PRE_READ"
    NATIVE_POSITIVE_CLONE_WRITE_AHEAD = "NATIVE_POSITIVE_CLONE_WRITE_AHEAD"
    POSTEXEC_NO_SPAWN = "POSTEXEC_NO_SPAWN"
    AUTHENTICATED_SCM_FRAME = "AUTHENTICATED_SCM_FRAME"
    OUTPUT_COMMITTED = "OUTPUT_COMMITTED"
    DIRECT_PIDFD_REAP = "DIRECT_PIDFD_REAP"
    DESCENDANT_FREE_POST_READ = "DESCENDANT_FREE_POST_READ"


def _fail(message: str) -> NoReturn:
    raise ConstructionSharedResourceWorkingProcessEvidenceV2Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceWorkingProcessEvidenceV2Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be one positive exact integer")
    return value


def _domain_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in REQUESTED_PHASE3E_DOMAIN_TAGS:
        _fail("working/process evidence used an undeclared central domain")
    return content_id(domain, dict(payload))


def _identity_fields(
    *,
    live_envelope_id: str,
    occurrence_id: str,
    route_attempt_id: str,
    decision_point_id: str,
    measurement_window_id: str,
) -> dict[str, str]:
    return {
        "live_envelope_id": live_envelope_id,
        "occurrence_id": occurrence_id,
        "route_attempt_id": route_attempt_id,
        "decision_point_id": decision_point_id,
        "measurement_window_id": measurement_window_id,
    }


_IDENTITY_KEYS = frozenset(
    {
        "live_envelope_id",
        "occurrence_id",
        "route_attempt_id",
        "decision_point_id",
        "measurement_window_id",
    }
)


def _component_document(
    schema_id: str,
    body: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": schema_id,
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        **dict(body),
        "raw_evidence_only": True,
        "domain_separated_content_id": True,
        "semantic_source_verified": False,
        "counter_record_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "formal_value_authorized": False,
    }


def _component(
    component_key: str,
    schema_id: str,
    body: Mapping[str, Any],
) -> resolution_v2.SharedResourceEvidenceComponentV2:
    raw = canonical_json_bytes(_component_document(schema_id, body))
    digest = hashlib.sha256(raw).hexdigest()
    try:
        domain = _COMPONENT_DOMAIN[schema_id]
    except KeyError as error:
        raise ConstructionSharedResourceWorkingProcessEvidenceV2Error(
            "working/process component used an unregistered schema"
        ) from error
    return resolution_v2.SharedResourceEvidenceComponentV2(
        component_key=component_key,
        source_schema_id=schema_id,
        source_artifact_id=_domain_id(
            domain,
            _canonical_object(raw, schema_id),
        ),
        source_bytes_sha256=digest,
        raw_bytes=raw,
    )


def _canonical_object(raw: bytes, schema_id: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{schema_id} bytes are empty or mistyped")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceWorkingProcessEvidenceV2Error(
            f"{schema_id} is not canonical JSON"
        ) from error
    if type(value) is not dict or value.get("schema") != schema_id:
        _fail("raw working/process component crossed its exact schema")
    fixed = {
        "schema": schema_id,
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "raw_evidence_only": True,
        "domain_separated_content_id": True,
        "semantic_source_verified": False,
        "counter_record_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "formal_value_authorized": False,
    }
    if any(value.get(key) != expected for key, expected in fixed.items()):
        _fail("raw working/process component changed its authority boundary")
    return value


def _descriptor_identity(descriptor: int) -> tuple[int, ...]:
    try:
        status = os.fstat(descriptor)
    except OSError as error:
        raise ConstructionSharedResourceWorkingProcessEvidenceV2Error(
            "working/process descriptor is closed or unavailable"
        ) from error
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_uid,
        status.st_gid,
        status.st_rdev,
    )


def _identity_document(identity: tuple[int, ...]) -> dict[str, int]:
    return {
        "device": identity[0],
        "inode": identity[1],
        "mode": identity[2],
        "owner_uid": identity[3],
        "owner_gid": identity[4],
        "rdev": identity[5],
    }


def _duplicate_cloexec(descriptor: int) -> int:
    try:
        duplicate = fcntl.fcntl(descriptor, fcntl.F_DUPFD_CLOEXEC, 3)
        os.set_inheritable(duplicate, False)
        return duplicate
    except OSError as error:
        raise ConstructionSharedResourceWorkingProcessEvidenceV2Error(
            "working/process descriptor could not be retained"
        ) from error


def _same_open_file_description(descriptor: int, witness: int) -> bool:
    """Probe one shared OFD via its file-status flags, then restore it."""

    try:
        descriptor_flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
        witness_flags = fcntl.fcntl(witness, fcntl.F_GETFL)
        if descriptor_flags != witness_flags:
            return False
        probe_flags = descriptor_flags ^ os.O_NONBLOCK
        fcntl.fcntl(descriptor, fcntl.F_SETFL, probe_flags)
        observed_probe = fcntl.fcntl(witness, fcntl.F_GETFL)
        fcntl.fcntl(descriptor, fcntl.F_SETFL, descriptor_flags)
        observed_restore = fcntl.fcntl(witness, fcntl.F_GETFL)
    except OSError as error:
        raise ConstructionSharedResourceWorkingProcessEvidenceV2Error(
            "retained memory.peak same-OFD probe failed"
        ) from error
    return observed_probe == probe_flags and observed_restore == descriptor_flags


def _read_retained(descriptor: int, label: str) -> bytes:
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(
                descriptor,
                min(1024, MAX_CONTROL_BYTES + 1 - total),
            )
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_CONTROL_BYTES:
                _fail(f"{label} exceeds its raw byte cap")
        return b"".join(chunks)
    except OSError as error:
        raise ConstructionSharedResourceWorkingProcessEvidenceV2Error(
            f"{label} retained-OFD read failed"
        ) from error


def _parse_peak(raw: bytes, label: str) -> int:
    if type(raw) is not bytes or _ASCII_UINT.fullmatch(raw) is None:
        _fail(f"{label} is not one canonical nonnegative decimal control value")
    return int(raw.rstrip(b"\n"))


def _read_named(directory_fd: int, name: str) -> bytes:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
        return _read_retained(descriptor, name)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _parse_cgroup_stat(raw: bytes) -> dict[str, int]:
    try:
        text = raw.decode("ascii", errors="strict")
    except UnicodeError as error:
        raise ConstructionSharedResourceWorkingProcessEvidenceV2Error(
            "cgroup.stat is not strict ASCII"
        ) from error
    rows: dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 2 or not parts[1].isdigit() or parts[0] in rows:
            _fail("cgroup.stat row is malformed or duplicated")
        rows[parts[0]] = int(parts[1])
    if not {"nr_descendants", "nr_dying_descendants"} <= set(rows):
        _fail("cgroup.stat lacks descendant closure fields")
    return rows


def _parse_cgroup_procs(raw: bytes) -> tuple[int, ...]:
    try:
        lines = raw.decode("ascii", errors="strict").splitlines()
    except UnicodeError as error:
        raise ConstructionSharedResourceWorkingProcessEvidenceV2Error(
            "cgroup.procs is not strict ASCII"
        ) from error
    if any(not line.isdigit() or int(line) <= 0 for line in lines):
        _fail("cgroup.procs contains a malformed PID")
    result = tuple(int(line) for line in lines)
    if len(set(result)) != len(result):
        _fail("cgroup.procs repeats a PID")
    return result


def _cgroup_snapshot(directory_fd: int) -> tuple[tuple[int, ...], dict[str, int]]:
    return (
        _parse_cgroup_procs(_read_named(directory_fd, "cgroup.procs")),
        _parse_cgroup_stat(_read_named(directory_fd, "cgroup.stat")),
    )


def _named_peak_identity(directory_fd: int) -> tuple[int, ...]:
    try:
        status = os.stat(
            "memory.peak",
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
    except OSError as error:
        raise ConstructionSharedResourceWorkingProcessEvidenceV2Error(
            "named memory.peak is unavailable"
        ) from error
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_uid,
        status.st_gid,
        status.st_rdev,
    )


def _pidfd_pid(pidfd: int) -> int:
    try:
        return channel_v2._pid_from_pidfdinfo(pidfd)  # noqa: SLF001
    except Exception as error:
        raise ConstructionSharedResourceWorkingProcessEvidenceV2Error(
            "pidfd does not retain one live expected PID"
        ) from error


def _author_role(frame_role: ipc_v1.K7OuterAttemptBrokerFrameRoleV1) -> str:
    matches = tuple(
        author
        for role, author in manifest_v2.FRAME_AUTHOR_VECTOR
        if role == frame_role.value
    )
    if len(matches) != 1:
        _fail("authenticated frame role lacks one registered author")
    return matches[0]


def _postexec_filter_sha256() -> str:
    return hashlib.sha256(
        canonical_json_bytes(
            [list(row) for row in sandbox_v2.postexec_seccomp_filter_rows_v2()]
        )
    ).hexdigest()


def _event_document(
    *, sequence: int, kind: LifecycleEventKindV2, body: Mapping[str, Any]
) -> dict[str, Any]:
    payload = {
        "sequence": sequence,
        "kind": kind.value,
        **dict(body),
    }
    return {
        **payload,
        "raw_event_id": _domain_id(WORKING_PROCESS_EVENT_V2_DOMAIN, payload),
    }


@dataclass(frozen=True, slots=True)
class WorkingProcessRawReplayV2:
    _issuer: InitVar[object]
    closure_kind: WorkingProcessClosureKindV2
    operational_cutoff_sequence: int
    memory_peak_max_bytes: int | None
    process_launches_sum: int | None
    process_launches_lower_bound: int
    roles_with_positive_clone_edge: tuple[str, ...]
    exact_memory_window_complete: bool
    exact_process_window_complete: bool
    semantic_source_verified: bool = False
    counter_record_issuance_authorized: bool = False

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REPLAY_ISSUER:
            _fail("working/process raw replay is caller-minted")
        closure = WorkingProcessClosureKindV2(self.closure_kind)
        object.__setattr__(self, "closure_kind", closure)
        _nonnegative(self.operational_cutoff_sequence, "raw replay cutoff")
        _nonnegative(
            self.process_launches_lower_bound,
            "raw process launch lower bound",
        )
        if (
            type(self.roles_with_positive_clone_edge) is not tuple
            or len(set(self.roles_with_positive_clone_edge))
            != len(self.roles_with_positive_clone_edge)
            or any(role not in EXPECTED_ROLES for role in self.roles_with_positive_clone_edge)
            or type(self.exact_memory_window_complete) is not bool
            or type(self.exact_process_window_complete) is not bool
            or self.semantic_source_verified is not False
            or self.counter_record_issuance_authorized is not False
        ):
            _fail("working/process raw replay flags or roles are malformed")
        if self.process_launches_lower_bound != len(
            self.roles_with_positive_clone_edge
        ):
            _fail("raw launch lower bound differs from positive native edges")
        if closure is WorkingProcessClosureKindV2.EXACT:
            if (
                type(self.memory_peak_max_bytes) is not int
                or self.memory_peak_max_bytes < 0
                or self.process_launches_sum != 2
                or self.process_launches_lower_bound != 2
                or self.roles_with_positive_clone_edge != EXPECTED_ROLES
                or not self.exact_memory_window_complete
                or not self.exact_process_window_complete
            ):
                _fail("exact raw replay lacks the complete two-role window")
        elif (
            self.memory_peak_max_bytes is not None
            or self.process_launches_sum is not None
            or self.exact_memory_window_complete
            or self.exact_process_window_complete
        ):
            _fail("failure-prefix raw replay forged an exact value")


@dataclass(frozen=True, slots=True)
class WorkingProcessRawEvidenceBundleV2:
    _issuer: InitVar[object]
    live_envelope_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    operational_cutoff_id: str
    measurement_start_sequence: int
    operational_cutoff_sequence: int
    closure_kind: WorkingProcessClosureKindV2
    cgroup_empty_component: resolution_v2.SharedResourceEvidenceComponentV2
    memory_post_component: resolution_v2.SharedResourceEvidenceComponentV2
    memory_pre_component: resolution_v2.SharedResourceEvidenceComponentV2
    same_ofd_component: resolution_v2.SharedResourceEvidenceComponentV2
    cutoff_component: resolution_v2.SharedResourceEvidenceComponentV2
    no_spawn_component: resolution_v2.SharedResourceEvidenceComponentV2
    pidfd_reap_component: resolution_v2.SharedResourceEvidenceComponentV2
    process_journal_component: resolution_v2.SharedResourceEvidenceComponentV2
    raw_replay: WorkingProcessRawReplayV2

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BUNDLE_ISSUER:
            _fail("working/process raw evidence bundle is caller-minted")
        for value, label in (
            (self.live_envelope_id, "bundle live envelope"),
            (self.occurrence_id, "bundle occurrence"),
            (self.route_attempt_id, "bundle route attempt"),
            (self.decision_point_id, "bundle decision point"),
            (self.measurement_window_id, "bundle measurement window"),
            (self.operational_cutoff_id, "bundle operational cutoff"),
        ):
            _cid(value, label)
        _nonnegative(self.measurement_start_sequence, "bundle start sequence")
        _nonnegative(self.operational_cutoff_sequence, "bundle cutoff sequence")
        closure = WorkingProcessClosureKindV2(self.closure_kind)
        object.__setattr__(self, "closure_kind", closure)
        components = self._all_components()
        if any(
            type(item) is not resolution_v2.SharedResourceEvidenceComponentV2
            for item in components
        ) or type(self.raw_replay) is not WorkingProcessRawReplayV2:
            _fail("working/process raw bundle contains a mistyped component")
        if self.raw_replay.closure_kind is not closure:
            _fail("working/process raw bundle crossed its replay closure kind")

    def _all_components(
        self,
    ) -> tuple[resolution_v2.SharedResourceEvidenceComponentV2, ...]:
        return (
            self.cgroup_empty_component,
            self.memory_post_component,
            self.memory_pre_component,
            self.same_ofd_component,
            self.cutoff_component,
            self.no_spawn_component,
            self.pidfd_reap_component,
            self.process_journal_component,
        )

    @property
    def exact_values_eligible_for_semantic_replay(self) -> bool:
        return self.closure_kind is WorkingProcessClosureKindV2.EXACT

    def components_for_path(
        self, path: str
    ) -> tuple[resolution_v2.SharedResourceEvidenceComponentV2, ...]:
        if path == MEMORY_PATH:
            return (
                self.cgroup_empty_component,
                self.memory_post_component,
                self.memory_pre_component,
                self.same_ofd_component,
            )
        if path == PROCESS_PATH:
            return (
                self.cutoff_component,
                self.no_spawn_component,
                self.pidfd_reap_component,
                self.process_journal_component,
            )
        _fail("working/process bundle requested an unsupported path")

    def live_sources_v2(self) -> tuple[resolution_v2.SharedResourceLiveSourceV2, ...]:
        contracts = {
            row.path: row
            for row in resolution_v2.official_shared_resource_resolution_catalogue_v2()
        }
        result = []
        for path in SUPPORTED_PATHS:
            contract = contracts[path]
            components = self.components_for_path(path)
            if tuple(
                (item.component_key, item.source_schema_id) for item in components
            ) != tuple(
                (item.component_key, item.source_schema_id)
                for item in contract.required_components
            ):
                _fail("working/process components differ from the exact catalogue")
            result.append(
                resolution_v2.SharedResourceLiveSourceV2(
                    self.live_envelope_id,
                    self.occurrence_id,
                    self.route_attempt_id,
                    self.decision_point_id,
                    self.measurement_window_id,
                    self.operational_cutoff_id,
                    path,
                    contract.exact_source_kind,
                    contract.required_provenance,
                    self.measurement_start_sequence,
                    self.operational_cutoff_sequence,
                    components,
                )
            )
        return tuple(result)

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_working_process_raw_bundle.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            **_identity_fields(
                live_envelope_id=self.live_envelope_id,
                occurrence_id=self.occurrence_id,
                route_attempt_id=self.route_attempt_id,
                decision_point_id=self.decision_point_id,
                measurement_window_id=self.measurement_window_id,
            ),
            "operational_cutoff_id": self.operational_cutoff_id,
            "measurement_start_sequence": self.measurement_start_sequence,
            "operational_cutoff_sequence": self.operational_cutoff_sequence,
            "closure_kind": self.closure_kind.value,
            "component_artifact_ids": [
                item.source_artifact_id for item in self._all_components()
            ],
            "raw_memory_peak_max_bytes": self.raw_replay.memory_peak_max_bytes,
            "raw_process_launches_sum": self.raw_replay.process_launches_sum,
            "raw_process_launches_lower_bound": (
                self.raw_replay.process_launches_lower_bound
            ),
            "exact_values_eligible_for_semantic_replay": (
                self.exact_values_eligible_for_semantic_replay
            ),
            "raw_evidence_only": True,
            "semantic_source_verified": False,
            "counter_record_issued": False,
            "formal_value_authorized": False,
        }


class WorkingProcessEvidenceSessionV2:
    """Process-local append authority for one retained peak/lifecycle window."""

    def __init__(
        self,
        *,
        live_envelope_id: str,
        occurrence_id: str,
        route_attempt_id: str,
        decision_point_id: str,
        measurement_window_id: str,
        measurement_start_sequence: int,
        memory_peak_fd: int,
        cgroup_directory_fd: int,
    ) -> None:
        for value, label in (
            (live_envelope_id, "session live envelope"),
            (occurrence_id, "session occurrence"),
            (route_attempt_id, "session route attempt"),
            (decision_point_id, "session decision point"),
            (measurement_window_id, "session measurement window"),
        ):
            _cid(value, label)
        _nonnegative(measurement_start_sequence, "measurement start sequence")
        if (
            type(memory_peak_fd) is not int
            or memory_peak_fd < 3
            or type(cgroup_directory_fd) is not int
            or cgroup_directory_fd < 3
            or memory_peak_fd == cgroup_directory_fd
        ):
            _fail("retained memory.peak/cgroup descriptors are invalid")
        peak_identity = _descriptor_identity(memory_peak_fd)
        directory_identity = _descriptor_identity(cgroup_directory_fd)
        try:
            peak_flags = fcntl.fcntl(memory_peak_fd, fcntl.F_GETFL)
            directory_flags = fcntl.fcntl(cgroup_directory_fd, fcntl.F_GETFL)
        except OSError as error:
            raise ConstructionSharedResourceWorkingProcessEvidenceV2Error(
                "retained memory/cgroup descriptor flags are unavailable"
            ) from error
        if (
            not stat.S_ISREG(peak_identity[2])
            or not stat.S_ISDIR(directory_identity[2])
            or peak_flags & os.O_ACCMODE != os.O_RDWR
            or peak_flags & getattr(os, "O_PATH", 0)
            or directory_flags & os.O_ACCMODE != os.O_RDONLY
            or directory_flags & getattr(os, "O_PATH", 0)
            or os.get_inheritable(memory_peak_fd)
            or os.get_inheritable(cgroup_directory_fd)
            or not fcntl.fcntl(memory_peak_fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC
            or not fcntl.fcntl(cgroup_directory_fd, fcntl.F_GETFD)
            & fcntl.FD_CLOEXEC
            or peak_identity != _named_peak_identity(cgroup_directory_fd)
        ):
            _fail("retained memory.peak/cgroup FD identity or access is invalid")
        peak_owned = -1
        peak_witness = -1
        directory_owned = -1
        try:
            peak_owned = _duplicate_cloexec(memory_peak_fd)
            peak_witness = _duplicate_cloexec(peak_owned)
            if not _same_open_file_description(peak_owned, peak_witness):
                _fail("memory.peak duplicates do not retain one open-file description")
            directory_owned = _duplicate_cloexec(cgroup_directory_fd)
            pre_procs, pre_stats = _cgroup_snapshot(directory_owned)
            if (
                pre_procs
                or pre_stats["nr_descendants"] != 0
                or pre_stats["nr_dying_descendants"] != 0
            ):
                _fail("measurement reset requires an empty descendant-free cgroup")
            os.lseek(peak_owned, 0, os.SEEK_SET)
            if os.write(peak_owned, b"0") != 1:
                _fail("memory.peak reset made partial progress")
            pre_raw = _read_retained(peak_owned, "memory.peak pre-read")
            pre_value = _parse_peak(pre_raw, "memory.peak pre-read")
            if pre_value != 0:
                _fail("memory.peak retained OFD did not replay a zero reset")
        except BaseException:
            for descriptor in (peak_owned, peak_witness, directory_owned):
                if descriptor >= 0:
                    os.close(descriptor)
            raise
        self._live_envelope_id = live_envelope_id
        self._occurrence_id = occurrence_id
        self._route_attempt_id = route_attempt_id
        self._decision_point_id = decision_point_id
        self._measurement_window_id = measurement_window_id
        self._measurement_start_sequence = measurement_start_sequence
        self._next_sequence_value = measurement_start_sequence
        self._peak_fd = peak_owned
        self._peak_witness_fd = peak_witness
        self._cgroup_fd = directory_owned
        self._peak_identity = peak_identity
        self._cgroup_identity = directory_identity
        self._named_peak_initial_identity = _named_peak_identity(directory_owned)
        self._pre_procs = pre_procs
        self._pre_stats = pre_stats
        self._pre_raw = pre_raw
        self._pre_value = pre_value
        self._roles: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []
        self._seen_authenticated_frames: set[str] = set()
        self._output_commit_id: str | None = None
        self._state = WorkingProcessSessionStateV2.OPEN
        self._bundle: WorkingProcessRawEvidenceBundleV2 | None = None
        self._owner_pid = os.getpid()
        self._lock = threading.RLock()
        self._append_event(
            LifecycleEventKindV2.MEMORY_PEAK_RESET_AND_PRE_READ,
            {
                "role": None,
                "retained_memory_peak_ofd_identity": _identity_document(
                    peak_identity
                ),
                "reset_write_ascii": "0",
                "pre_read_ascii": pre_raw.decode("ascii"),
                "parsed_pre_peak_bytes": pre_value,
            },
        )

    @property
    def state(self) -> WorkingProcessSessionStateV2:
        self._check_owner()
        return self._state

    def _check_owner(self) -> None:
        if os.getpid() != self._owner_pid:
            _fail("working/process evidence session crossed a process")

    def _require_open(self) -> None:
        self._check_owner()
        if self._state is not WorkingProcessSessionStateV2.OPEN:
            _fail("closed working/process evidence session cannot be reused")

    def _append_event(
        self, kind: LifecycleEventKindV2, body: Mapping[str, Any]
    ) -> dict[str, Any]:
        sequence = self._next_sequence_value
        self._next_sequence_value += 1
        event = _event_document(sequence=sequence, kind=kind, body=body)
        self._events.append(event)
        return event

    def _role(self, role: str) -> dict[str, Any]:
        if role not in EXPECTED_ROLES or role not in self._roles:
            _fail("process lifecycle requested an absent or unknown role")
        return self._roles[role]

    def _assert_retained_descriptors(self) -> None:
        if (
            _descriptor_identity(self._peak_fd) != self._peak_identity
            or _descriptor_identity(self._peak_witness_fd) != self._peak_identity
            or not _same_open_file_description(
                self._peak_fd,
                self._peak_witness_fd,
            )
            or _descriptor_identity(self._cgroup_fd) != self._cgroup_identity
            or _named_peak_identity(self._cgroup_fd) != self._peak_identity
        ):
            _fail("retained memory.peak OFD or cgroup identity was replaced")

    def record_native_positive_clone_v2(
        self,
        *,
        role: str,
        expected_pid: int,
        pidfd: int,
        native_clone_result: int,
        native_write_ahead_edge: int,
    ) -> None:
        """Record one positive parent-branch clone edge before fallible work."""

        with self._lock:
            self._require_open()
            self._assert_retained_descriptors()
            if role not in EXPECTED_ROLES or role in self._roles:
                _fail("native clone role is unknown or duplicated")
            _positive(expected_pid, "native expected PID")
            if (
                type(native_clone_result) is not int
                or native_clone_result != expected_pid
                or native_write_ahead_edge != 1
                or type(pidfd) is not int
                or pidfd < 3
                or _pidfd_pid(pidfd) != expected_pid
            ):
                _fail("native clone lacks one positive write-ahead PID/pidfd edge")
            pidfd_identity = _descriptor_identity(pidfd)
            cgroup_procs, _stats = _cgroup_snapshot(self._cgroup_fd)
            if expected_pid not in cgroup_procs:
                _fail("positive native child is absent from the attempt cgroup")
            event = self._append_event(
                LifecycleEventKindV2.NATIVE_POSITIVE_CLONE_WRITE_AHEAD,
                {
                    "role": role,
                    "pid": expected_pid,
                    "pidfd_identity": _identity_document(pidfd_identity),
                    "native_clone_result": native_clone_result,
                    "native_write_ahead_edge": 1,
                    "cgroup_membership_observed": True,
                },
            )
            self._roles[role] = {
                "role": role,
                "pid": expected_pid,
                "pidfd": pidfd,
                "pidfd_identity": pidfd_identity,
                "clone_sequence": event["sequence"],
                "authenticated_frames": [],
                "no_spawn": None,
                "reap": None,
            }

    def record_postexec_no_spawn_v2(
        self,
        *,
        role: str,
        attestation_source_id: str,
        attested_pid: int,
        attested_pidfd: int,
        postexec_filter_sha256: str,
        clone_fork_vfork_denied: bool,
        execve_execveat_denied: bool,
        seccomp_tsync_completed: bool,
    ) -> None:
        with self._lock:
            self._require_open()
            row = self._role(role)
            _cid(attestation_source_id, "postexec no-spawn source")
            if row["no_spawn"] is not None:
                _fail("postexec no-spawn role was duplicated")
            if (
                attested_pid != row["pid"]
                or attested_pidfd != row["pidfd"]
                or _descriptor_identity(attested_pidfd)
                != row["pidfd_identity"]
                or _pidfd_pid(attested_pidfd) != attested_pid
                or postexec_filter_sha256 != _postexec_filter_sha256()
                or clone_fork_vfork_denied is not True
                or execve_execveat_denied is not True
                or seccomp_tsync_completed is not True
            ):
                _fail("postexec no-spawn attestation is forged or crossed")
            event = self._append_event(
                LifecycleEventKindV2.POSTEXEC_NO_SPAWN,
                {
                    "role": role,
                    "pid": attested_pid,
                    "pidfd_identity": _identity_document(row["pidfd_identity"]),
                    "attestation_source_id": attestation_source_id,
                    "postexec_filter_sha256": postexec_filter_sha256,
                    "clone_fork_vfork_denied": True,
                    "execve_execveat_denied": True,
                    "seccomp_tsync_completed": True,
                },
            )
            row["no_spawn"] = event

    def record_authenticated_frame_v2(
        self,
        observation: channel_v2.K7AuthenticatedBrokerFrameV2,
    ) -> None:
        with self._lock:
            self._require_open()
            if type(observation) is not channel_v2.K7AuthenticatedBrokerFrameV2:
                _fail("process journal requires one exact authenticated frame")
            role = _author_role(observation.frame.role)
            row = self._role(role)
            if observation.observation_id in self._seen_authenticated_frames:
                _fail("authenticated frame observation was duplicated")
            if (
                observation.sender_pid != row["pid"]
                or observation.pidfd_identity != row["pidfd_identity"]
                or _descriptor_identity(row["pidfd"]) != row["pidfd_identity"]
                or _pidfd_pid(row["pidfd"]) != row["pid"]
            ):
                _fail("authenticated SCM sender PID/pidfd crossed its native edge")
            event = self._append_event(
                LifecycleEventKindV2.AUTHENTICATED_SCM_FRAME,
                {
                    "role": role,
                    "pid": row["pid"],
                    "pidfd_identity": _identity_document(row["pidfd_identity"]),
                    "authenticated_broker_frame_id": observation.observation_id,
                    "frame_role": observation.frame.role.value,
                    "frame_sequence": observation.frame.sequence,
                    "scm_sender_pid": observation.sender_pid,
                },
            )
            row["authenticated_frames"].append(event)
            self._seen_authenticated_frames.add(observation.observation_id)

    def record_output_committed_v2(self, *, output_commit_id: str) -> None:
        with self._lock:
            self._require_open()
            _cid(output_commit_id, "output commit")
            if self._output_commit_id is not None:
                _fail("output commit was duplicated")
            if tuple(self._roles) != EXPECTED_ROLES or any(
                not self._roles[role]["authenticated_frames"]
                or self._roles[role]["no_spawn"] is None
                for role in EXPECTED_ROLES
            ):
                _fail("output commit precedes authenticated/no-spawn role closure")
            self._append_event(
                LifecycleEventKindV2.OUTPUT_COMMITTED,
                {"role": None, "output_commit_id": output_commit_id},
            )
            self._output_commit_id = output_commit_id

    def reap_direct_child_v2(self, *, role: str) -> None:
        """Perform the sole exact direct-child reap through its retained pidfd."""

        with self._lock:
            self._require_open()
            row = self._role(role)
            if self._output_commit_id is None:
                _fail("direct child reap must occur after output commit")
            if row["reap"] is not None:
                _fail("direct child role was reaped twice")
            pidfd = row["pidfd"]
            if (
                _descriptor_identity(pidfd) != row["pidfd_identity"]
                or _pidfd_pid(pidfd) != row["pid"]
            ):
                _fail("direct reap PID/pidfd identity crossed before wait")
            try:
                waited = os.waitid(os.P_PIDFD, pidfd, os.WEXITED)
            except (ChildProcessError, OSError) as error:
                raise ConstructionSharedResourceWorkingProcessEvidenceV2Error(
                    "direct P_PIDFD reap failed"
                ) from error
            if waited is None or waited.si_pid != row["pid"]:
                _fail("direct P_PIDFD reap returned a foreign child")
            event = self._append_event(
                LifecycleEventKindV2.DIRECT_PIDFD_REAP,
                {
                    "role": role,
                    "pid": row["pid"],
                    "pidfd_identity": _identity_document(row["pidfd_identity"]),
                    "wait_idtype": "P_PIDFD",
                    "wait_options": "WEXITED",
                    "wait_si_pid": waited.si_pid,
                    "wait_si_uid": waited.si_uid,
                    "wait_si_signo": waited.si_signo,
                    "wait_si_status": waited.si_status,
                    "wait_si_code": waited.si_code,
                    "direct_child_reaped": True,
                },
            )
            row["reap"] = event

    def _identity(self) -> dict[str, str]:
        return _identity_fields(
            live_envelope_id=self._live_envelope_id,
            occurrence_id=self._occurrence_id,
            route_attempt_id=self._route_attempt_id,
            decision_point_id=self._decision_point_id,
            measurement_window_id=self._measurement_window_id,
        )

    def _close(
        self,
        *,
        closure_kind: WorkingProcessClosureKindV2,
        failure_reason: str | None,
    ) -> WorkingProcessRawEvidenceBundleV2:
        with self._lock:
            self._require_open()
            exact = closure_kind is WorkingProcessClosureKindV2.EXACT
            if exact:
                if (
                    failure_reason is not None
                    or tuple(self._roles) != EXPECTED_ROLES
                    or self._output_commit_id is None
                    or any(
                        not self._roles[role]["authenticated_frames"]
                        or self._roles[role]["no_spawn"] is None
                        or self._roles[role]["reap"] is None
                        for role in EXPECTED_ROLES
                    )
                ):
                    _fail("exact working/process close lacks the complete two-role lifecycle")
            elif type(failure_reason) is not str or not failure_reason:
                _fail("failure-prefix close requires one nonempty reason")
            self._assert_retained_descriptors()
            post_raw: bytes | None = None
            post_value: int | None = None
            post_procs: tuple[int, ...] | None = None
            post_stats: dict[str, int] | None = None
            post_event: dict[str, Any] | None = None
            if exact:
                post_procs, post_stats = _cgroup_snapshot(self._cgroup_fd)
                if (
                    post_procs
                    or post_stats["nr_descendants"] != 0
                    or post_stats["nr_dying_descendants"] != 0
                ):
                    _fail("post-reap cgroup is not empty and descendant-free")
                post_raw = _read_retained(self._peak_fd, "memory.peak post-read")
                post_value = _parse_peak(post_raw, "memory.peak post-read")
                if post_value < self._pre_value:
                    _fail("retained memory.peak regressed after its zero reset")
                post_event = self._append_event(
                    LifecycleEventKindV2.DESCENDANT_FREE_POST_READ,
                    {
                        "role": None,
                        "retained_memory_peak_ofd_identity": _identity_document(
                            self._peak_identity
                        ),
                        "post_read_ascii": post_raw.decode("ascii"),
                        "parsed_post_peak_bytes": post_value,
                        "post_cgroup_procs": [],
                        "post_nr_descendants": 0,
                        "post_nr_dying_descendants": 0,
                    },
                )
            cutoff_sequence = self._next_sequence_value
            cutoff_payload = {
                **self._identity(),
                "measurement_start_sequence": self._measurement_start_sequence,
                "operational_cutoff_sequence": cutoff_sequence,
                "last_included_event_sequence": cutoff_sequence - 1,
                "included_event_count": len(self._events),
                "closure_kind": closure_kind.value,
                "failure_reason": failure_reason,
            }
            cutoff_id = _domain_id(
                _COMPONENT_DOMAIN[CUTOFF_SCHEMA_ID],
                {
                    "schema": CUTOFF_SCHEMA_ID,
                    "schema_version": SCHEMA_VERSION,
                    **cutoff_payload,
                }
            )
            common = {
                **self._identity(),
                "operational_cutoff_id": cutoff_id,
                "measurement_start_sequence": self._measurement_start_sequence,
                "operational_cutoff_sequence": cutoff_sequence,
                "closure_kind": closure_kind.value,
                "failure_reason": failure_reason,
            }
            role_rows = [self._roles[role] for role in EXPECTED_ROLES if role in self._roles]
            exact_peak = (
                max(self._pre_value, post_value)
                if exact and post_value is not None
                else None
            )
            memory_pre = _component(
                "memory_peak_pre_read",
                MEMORY_PRE_SCHEMA_ID,
                {
                    **common,
                    "read_ordinal": 1,
                    "read_sequence": self._measurement_start_sequence,
                    "reset_write_ascii": "0",
                    "raw_read_ascii": self._pre_raw.decode("ascii"),
                    "parsed_peak_bytes": self._pre_value,
                    "retained_memory_peak_ofd_identity": _identity_document(
                        self._peak_identity
                    ),
                    "no_baseline_subtraction": True,
                },
            )
            memory_post = _component(
                "memory_peak_post_read",
                MEMORY_POST_SCHEMA_ID,
                {
                    **common,
                    "read_ordinal": 2,
                    "read_performed": exact,
                    "read_sequence": None if post_event is None else post_event["sequence"],
                    "raw_read_ascii": None if post_raw is None else post_raw.decode("ascii"),
                    "parsed_peak_bytes": post_value,
                    "raw_derived_max_bytes": exact_peak,
                    "after_output_commit": exact,
                    "after_direct_pidfd_reap_roles": (
                        list(EXPECTED_ROLES) if exact else []
                    ),
                    "after_descendant_free_scan": exact,
                    "no_baseline_subtraction": True,
                },
            )
            same_ofd = _component(
                "same_ofd_attestation",
                SAME_OFD_SCHEMA_ID,
                {
                    **common,
                    "retained_memory_peak_ofd_identity": _identity_document(
                        self._peak_identity
                    ),
                    "named_memory_peak_initial_identity": _identity_document(
                        self._named_peak_initial_identity
                    ),
                    "named_memory_peak_final_identity": _identity_document(
                        _named_peak_identity(self._cgroup_fd)
                    ),
                    "reset_pre_post_same_retained_fd": True,
                    "pre_read_sequence": self._measurement_start_sequence,
                    "post_read_sequence": (
                        None if post_event is None else post_event["sequence"]
                    ),
                    "ofd_replacement_detected": False,
                },
            )
            cgroup_empty = _component(
                "cgroup_empty_attestation",
                CGROUP_EMPTY_SCHEMA_ID,
                {
                    **common,
                    "cgroup_directory_identity": _identity_document(
                        self._cgroup_identity
                    ),
                    "pre_reset_cgroup_procs": list(self._pre_procs),
                    "pre_reset_nr_descendants": self._pre_stats[
                        "nr_descendants"
                    ],
                    "pre_reset_nr_dying_descendants": self._pre_stats[
                        "nr_dying_descendants"
                    ],
                    "post_reap_scan_performed": exact,
                    "post_reap_cgroup_procs": (
                        None if post_procs is None else list(post_procs)
                    ),
                    "post_reap_nr_descendants": (
                        None if post_stats is None else post_stats["nr_descendants"]
                    ),
                    "post_reap_nr_dying_descendants": (
                        None
                        if post_stats is None
                        else post_stats["nr_dying_descendants"]
                    ),
                    "direct_reaped_roles": [
                        row["role"] for row in role_rows if row["reap"] is not None
                    ],
                },
            )
            cutoff = _component(
                "cutoff_attestation",
                CUTOFF_SCHEMA_ID,
                {
                    **common,
                    "last_included_event_sequence": cutoff_sequence - 1,
                    "included_event_count": len(self._events),
                    "closed_inclusive": True,
                    "cutoff_auto_assigned": True,
                    "post_cutoff_append_allowed": False,
                },
            )
            no_spawn_rows = [
                {
                    key: value
                    for key, value in row["no_spawn"].items()
                    if key != "raw_event_id"
                }
                for row in role_rows
                if row["no_spawn"] is not None
            ]
            no_spawn = _component(
                "no_spawn_attestation",
                NO_SPAWN_SCHEMA_ID,
                {
                    **common,
                    "expected_roles": list(EXPECTED_ROLES),
                    "role_attestations": no_spawn_rows,
                    "complete_role_coverage": exact,
                    "postexec_filter_sha256": _postexec_filter_sha256(),
                },
            )
            reap_rows = []
            for row in role_rows:
                if row["reap"] is None:
                    continue
                authenticated = row["authenticated_frames"]
                reap_rows.append(
                    {
                        **{
                            key: value
                            for key, value in row["reap"].items()
                            if key != "raw_event_id"
                        },
                        "native_clone_sequence": row["clone_sequence"],
                        "authenticated_frame_ids": [
                            event["authenticated_broker_frame_id"]
                            for event in authenticated
                        ],
                        "authenticated_scm_sender_pid": row["pid"],
                    }
                )
            pidfd_reap = _component(
                "pidfd_reap_attestation",
                PIDFD_REAP_SCHEMA_ID,
                {
                    **common,
                    "expected_roles": list(EXPECTED_ROLES),
                    "direct_reaps": reap_rows,
                    "complete_role_coverage": exact,
                    "waitid_idtype": "P_PIDFD",
                    "waitid_options": "WEXITED",
                },
            )
            journal = _component(
                "process_lifecycle_journal",
                PROCESS_JOURNAL_SCHEMA_ID,
                {
                    **common,
                    "expected_roles": list(EXPECTED_ROLES),
                    "events": list(self._events),
                    "event_count": len(self._events),
                    "last_event_sequence": cutoff_sequence - 1,
                    "raw_derived_process_launches_lower_bound": len(role_rows),
                    "raw_derived_process_launches_sum": 2 if exact else None,
                    "positive_clone_roles": [row["role"] for row in role_rows],
                    "output_commit_id": self._output_commit_id,
                    "failure_prefix_cannot_be_exact": not exact,
                },
            )
            replay = WorkingProcessRawReplayV2(
                _REPLAY_ISSUER,
                closure_kind,
                cutoff_sequence,
                exact_peak,
                2 if exact else None,
                len(role_rows),
                tuple(row["role"] for row in role_rows),
                exact,
                exact,
                False,
                False,
            )
            bundle = WorkingProcessRawEvidenceBundleV2(
                _BUNDLE_ISSUER,
                self._live_envelope_id,
                self._occurrence_id,
                self._route_attempt_id,
                self._decision_point_id,
                self._measurement_window_id,
                cutoff_id,
                self._measurement_start_sequence,
                cutoff_sequence,
                closure_kind,
                cgroup_empty,
                memory_post,
                memory_pre,
                same_ofd,
                cutoff,
                no_spawn,
                pidfd_reap,
                journal,
                replay,
            )
            self._bundle = bundle
            self._state = (
                WorkingProcessSessionStateV2.CLOSED_EXACT
                if exact
                else WorkingProcessSessionStateV2.CLOSED_FAILURE_PREFIX
            )
            self._close_descriptors()
            return bundle

    def close_exact_v2(self) -> WorkingProcessRawEvidenceBundleV2:
        return self._close(
            closure_kind=WorkingProcessClosureKindV2.EXACT,
            failure_reason=None,
        )

    def close_failure_prefix_v2(
        self, *, failure_reason: str
    ) -> WorkingProcessRawEvidenceBundleV2:
        return self._close(
            closure_kind=WorkingProcessClosureKindV2.FAILURE_PREFIX,
            failure_reason=failure_reason,
        )

    def _close_descriptors(self) -> None:
        for name in ("_peak_fd", "_peak_witness_fd", "_cgroup_fd"):
            descriptor = getattr(self, name, -1)
            if descriptor >= 0:
                os.close(descriptor)
                setattr(self, name, -1)

    def close(self) -> None:
        with self._lock:
            self._check_owner()
            self._close_descriptors()

    def __reduce__(self) -> NoReturn:
        raise TypeError("working/process evidence session is process-local")

    def __reduce_ex__(self, _protocol: int) -> NoReturn:
        raise TypeError("working/process evidence session is process-local")


def _exact_fields(document: Mapping[str, Any], expected: set[str], label: str) -> None:
    try:
        require_exact_fields(document, expected, context=label)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceWorkingProcessEvidenceV2Error(
            f"{label} fields are incomplete or unknown"
        ) from error


_BASE_COMPONENT_KEYS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    *_IDENTITY_KEYS,
    "operational_cutoff_id",
    "measurement_start_sequence",
    "operational_cutoff_sequence",
    "closure_kind",
    "failure_reason",
    "raw_evidence_only",
    "domain_separated_content_id",
    "semantic_source_verified",
    "counter_record_issued",
    "work_vector_issued",
    "comparison_vector_issued",
    "formal_value_authorized",
}


_SCHEMA_BODY_KEYS = {
    MEMORY_PRE_SCHEMA_ID: {
        "read_ordinal",
        "read_sequence",
        "reset_write_ascii",
        "raw_read_ascii",
        "parsed_peak_bytes",
        "retained_memory_peak_ofd_identity",
        "no_baseline_subtraction",
    },
    MEMORY_POST_SCHEMA_ID: {
        "read_ordinal",
        "read_performed",
        "read_sequence",
        "raw_read_ascii",
        "parsed_peak_bytes",
        "raw_derived_max_bytes",
        "after_output_commit",
        "after_direct_pidfd_reap_roles",
        "after_descendant_free_scan",
        "no_baseline_subtraction",
    },
    SAME_OFD_SCHEMA_ID: {
        "retained_memory_peak_ofd_identity",
        "named_memory_peak_initial_identity",
        "named_memory_peak_final_identity",
        "reset_pre_post_same_retained_fd",
        "pre_read_sequence",
        "post_read_sequence",
        "ofd_replacement_detected",
    },
    CGROUP_EMPTY_SCHEMA_ID: {
        "cgroup_directory_identity",
        "pre_reset_cgroup_procs",
        "pre_reset_nr_descendants",
        "pre_reset_nr_dying_descendants",
        "post_reap_scan_performed",
        "post_reap_cgroup_procs",
        "post_reap_nr_descendants",
        "post_reap_nr_dying_descendants",
        "direct_reaped_roles",
    },
    CUTOFF_SCHEMA_ID: {
        "last_included_event_sequence",
        "included_event_count",
        "closed_inclusive",
        "cutoff_auto_assigned",
        "post_cutoff_append_allowed",
    },
    NO_SPAWN_SCHEMA_ID: {
        "expected_roles",
        "role_attestations",
        "complete_role_coverage",
        "postexec_filter_sha256",
    },
    PIDFD_REAP_SCHEMA_ID: {
        "expected_roles",
        "direct_reaps",
        "complete_role_coverage",
        "waitid_idtype",
        "waitid_options",
    },
    PROCESS_JOURNAL_SCHEMA_ID: {
        "expected_roles",
        "events",
        "event_count",
        "last_event_sequence",
        "raw_derived_process_launches_lower_bound",
        "raw_derived_process_launches_sum",
        "positive_clone_roles",
        "output_commit_id",
        "failure_prefix_cannot_be_exact",
    },
}


def _replay_documents(raw_by_schema: Mapping[str, bytes]) -> dict[str, dict[str, Any]]:
    if set(raw_by_schema) != set(_SCHEMA_BODY_KEYS):
        _fail("working/process raw replay lacks an exact component schema")
    documents = {
        schema: _canonical_object(raw_by_schema[schema], schema)
        for schema in _SCHEMA_BODY_KEYS
    }
    for schema, document in documents.items():
        _exact_fields(
            document,
            _BASE_COMPONENT_KEYS | _SCHEMA_BODY_KEYS[schema],
            schema,
        )
    first = documents[MEMORY_PRE_SCHEMA_ID]
    common_keys = (
        *_IDENTITY_KEYS,
        "operational_cutoff_id",
        "measurement_start_sequence",
        "operational_cutoff_sequence",
        "closure_kind",
        "failure_reason",
    )
    for document in documents.values():
        if any(document[key] != first[key] for key in common_keys):
            _fail("working/process components crossed identity or cutoff")
    return documents


def replay_working_process_raw_evidence_v2(
    *,
    cgroup_empty_bytes: bytes,
    memory_peak_post_read_bytes: bytes,
    memory_peak_pre_read_bytes: bytes,
    same_ofd_attestation_bytes: bytes,
    cutoff_attestation_bytes: bytes,
    no_spawn_attestation_bytes: bytes,
    pidfd_reap_attestation_bytes: bytes,
    process_lifecycle_journal_bytes: bytes,
) -> WorkingProcessRawReplayV2:
    """Replay raw arithmetic and joins without granting semantic authority."""

    documents = _replay_documents(
        {
            CGROUP_EMPTY_SCHEMA_ID: cgroup_empty_bytes,
            MEMORY_POST_SCHEMA_ID: memory_peak_post_read_bytes,
            MEMORY_PRE_SCHEMA_ID: memory_peak_pre_read_bytes,
            SAME_OFD_SCHEMA_ID: same_ofd_attestation_bytes,
            CUTOFF_SCHEMA_ID: cutoff_attestation_bytes,
            NO_SPAWN_SCHEMA_ID: no_spawn_attestation_bytes,
            PIDFD_REAP_SCHEMA_ID: pidfd_reap_attestation_bytes,
            PROCESS_JOURNAL_SCHEMA_ID: process_lifecycle_journal_bytes,
        }
    )
    pre = documents[MEMORY_PRE_SCHEMA_ID]
    post = documents[MEMORY_POST_SCHEMA_ID]
    same = documents[SAME_OFD_SCHEMA_ID]
    empty = documents[CGROUP_EMPTY_SCHEMA_ID]
    cutoff = documents[CUTOFF_SCHEMA_ID]
    no_spawn = documents[NO_SPAWN_SCHEMA_ID]
    reaps = documents[PIDFD_REAP_SCHEMA_ID]
    journal = documents[PROCESS_JOURNAL_SCHEMA_ID]
    try:
        closure = WorkingProcessClosureKindV2(pre["closure_kind"])
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceWorkingProcessEvidenceV2Error(
            "working/process closure kind is unknown"
        ) from error
    start = _nonnegative(pre["measurement_start_sequence"], "replay start")
    cutoff_sequence = _nonnegative(
        pre["operational_cutoff_sequence"], "replay cutoff"
    )
    events = journal["events"]
    if type(events) is not list or any(type(row) is not dict for row in events):
        _fail("process lifecycle events are not one raw object list")
    sequences = tuple(row.get("sequence") for row in events)
    if (
        sequences != tuple(range(start, start + len(events)))
        or journal["event_count"] != len(events)
        or journal["last_event_sequence"] != cutoff_sequence - 1
        or cutoff["last_included_event_sequence"] != cutoff_sequence - 1
        or cutoff["included_event_count"] != len(events)
        or cutoff_sequence != start + len(events)
        or cutoff["closed_inclusive"] is not True
        or cutoff["cutoff_auto_assigned"] is not True
        or cutoff["post_cutoff_append_allowed"] is not False
    ):
        _fail("operational cutoff hides, skips, or duplicates a lifecycle event")
    expected_cutoff_id = _domain_id(
        _COMPONENT_DOMAIN[CUTOFF_SCHEMA_ID],
        {
            "schema": CUTOFF_SCHEMA_ID,
            "schema_version": SCHEMA_VERSION,
            **{key: pre[key] for key in _IDENTITY_KEYS},
            "measurement_start_sequence": start,
            "operational_cutoff_sequence": cutoff_sequence,
            "last_included_event_sequence": cutoff_sequence - 1,
            "included_event_count": len(events),
            "closure_kind": pre["closure_kind"],
            "failure_reason": pre["failure_reason"],
        }
    )
    if pre["operational_cutoff_id"] != expected_cutoff_id:
        _fail("operational cutoff identity does not replay from its closed window")
    event_kinds = {item.value for item in LifecycleEventKindV2}
    for event in events:
        payload = dict(event)
        event_id = payload.pop("raw_event_id", None)
        if (
            event.get("kind") not in event_kinds
            or event_id
            != _domain_id(WORKING_PROCESS_EVENT_V2_DOMAIN, payload)
        ):
            _fail("process lifecycle raw event ID does not replay")
    clone_events = [
        row
        for row in events
        if row["kind"]
        == LifecycleEventKindV2.NATIVE_POSITIVE_CLONE_WRITE_AHEAD.value
    ]
    clone_roles = tuple(row.get("role") for row in clone_events)
    if (
        any(role not in EXPECTED_ROLES for role in clone_roles)
        or len(set(clone_roles)) != len(clone_roles)
        or any(
            type(row.get("pid")) is not int
            or row["pid"] <= 0
            or row.get("native_clone_result") != row["pid"]
            or row.get("native_write_ahead_edge") != 1
            or row.get("cgroup_membership_observed") is not True
            for row in clone_events
        )
        or journal["positive_clone_roles"] != list(clone_roles)
        or journal["raw_derived_process_launches_lower_bound"]
        != len(clone_events)
    ):
        _fail("process launch lower bound differs from positive native edges")
    edge_by_role = {row["role"]: row for row in clone_events}
    auth_by_role: dict[str, list[dict[str, Any]]] = {
        role: [] for role in clone_roles
    }
    frame_author_by_role = dict(manifest_v2.FRAME_AUTHOR_VECTOR)
    authenticated_frame_ids: set[str] = set()
    for row in events:
        if row["kind"] != LifecycleEventKindV2.AUTHENTICATED_SCM_FRAME.value:
            continue
        role = row.get("role")
        edge = edge_by_role.get(role)
        frame_id = row.get("authenticated_broker_frame_id")
        if (
            edge is None
            or row.get("pid") != edge["pid"]
            or row.get("scm_sender_pid") != edge["pid"]
            or row.get("pidfd_identity") != edge["pidfd_identity"]
            or row.get("sequence") <= edge["sequence"]
            or frame_author_by_role.get(row.get("frame_role")) != role
            or type(row.get("frame_sequence")) is not int
            or type(frame_id) is not str
            or frame_id in authenticated_frame_ids
        ):
            _fail("authenticated SCM frame crossed its PID/pidfd native edge")
        _cid(frame_id, "replayed authenticated broker frame")
        auth_by_role[role].append(row)
        authenticated_frame_ids.add(frame_id)
    no_spawn_rows = no_spawn["role_attestations"]
    if type(no_spawn_rows) is not list:
        _fail("no-spawn role attestations are not a list")
    journal_no_spawn_rows = [
        row
        for row in events
        if row["kind"] == LifecycleEventKindV2.POSTEXEC_NO_SPAWN.value
    ]
    no_spawn_by_role: dict[str, dict[str, Any]] = {}
    for row in no_spawn_rows:
        if type(row) is not dict or row.get("role") in no_spawn_by_role:
            _fail("no-spawn role is malformed or duplicated")
        role = row.get("role")
        edge = edge_by_role.get(role)
        matching_journal_rows = [
            event
            for event in journal_no_spawn_rows
            if event.get("role") == role
        ]
        if (
            edge is None
            or len(matching_journal_rows) != 1
            or {
                key: value
                for key, value in matching_journal_rows[0].items()
                if key != "raw_event_id"
            }
            != row
            or row.get("kind") != LifecycleEventKindV2.POSTEXEC_NO_SPAWN.value
            or row.get("pid") != edge["pid"]
            or row.get("pidfd_identity") != edge["pidfd_identity"]
            or row.get("sequence") <= edge["sequence"]
            or row.get("postexec_filter_sha256") != _postexec_filter_sha256()
            or row.get("clone_fork_vfork_denied") is not True
            or row.get("execve_execveat_denied") is not True
            or row.get("seccomp_tsync_completed") is not True
        ):
            _fail("postexec no-spawn replay is forged or crossed")
        _cid(row.get("attestation_source_id"), "replayed no-spawn source")
        no_spawn_by_role[role] = row
    if (
        len(journal_no_spawn_rows) != len(no_spawn_rows)
        or no_spawn["postexec_filter_sha256"] != _postexec_filter_sha256()
    ):
        _fail("no-spawn component crossed the fixed postexec filter")
    reap_rows = reaps["direct_reaps"]
    if type(reap_rows) is not list:
        _fail("pidfd direct reaps are not a list")
    journal_reap_rows = [
        row
        for row in events
        if row["kind"] == LifecycleEventKindV2.DIRECT_PIDFD_REAP.value
    ]
    reap_by_role: dict[str, dict[str, Any]] = {}
    for row in reap_rows:
        if type(row) is not dict or row.get("role") in reap_by_role:
            _fail("pidfd direct-reap role is malformed or duplicated")
        role = row.get("role")
        edge = edge_by_role.get(role)
        expected_auth = auth_by_role.get(role, [])
        matching_journal_rows = [
            event for event in journal_reap_rows if event.get("role") == role
        ]
        journal_projection = (
            {}
            if len(matching_journal_rows) != 1
            else {
                key: value
                for key, value in matching_journal_rows[0].items()
                if key != "raw_event_id"
            }
        )
        if (
            edge is None
            or not expected_auth
            or len(matching_journal_rows) != 1
            or any(row.get(key) != value for key, value in journal_projection.items())
            or row.get("pid") != edge["pid"]
            or row.get("wait_si_pid") != edge["pid"]
            or row.get("authenticated_scm_sender_pid") != edge["pid"]
            or row.get("pidfd_identity") != edge["pidfd_identity"]
            or row.get("wait_idtype") != "P_PIDFD"
            or row.get("wait_options") != "WEXITED"
            or row.get("direct_child_reaped") is not True
            or row.get("authenticated_frame_ids")
            != [item["authenticated_broker_frame_id"] for item in expected_auth]
        ):
            _fail("direct PIDfd reap crossed PID, pidfd, SCM, or wait identity")
        reap_by_role[role] = row
    if len(journal_reap_rows) != len(reap_rows):
        _fail("direct PIDfd reap component omitted or duplicated a journal event")
    output_events = [
        row
        for row in events
        if row["kind"] == LifecycleEventKindV2.OUTPUT_COMMITTED.value
    ]
    output_commit_id = journal["output_commit_id"]
    if output_commit_id is None:
        if output_events:
            _fail("output-commit journal event lacks its bound identity")
    elif (
        len(output_events) != 1
        or output_events[0].get("role") is not None
        or output_events[0].get("output_commit_id") != output_commit_id
    ):
        _fail("output-commit identity differs from its lifecycle event")
    else:
        _cid(output_commit_id, "replayed output commit")
    exact = closure is WorkingProcessClosureKindV2.EXACT
    if exact:
        if (
            clone_roles != EXPECTED_ROLES
            or set(auth_by_role) != set(EXPECTED_ROLES)
            or any(not auth_by_role[role] for role in EXPECTED_ROLES)
            or tuple(no_spawn_by_role) != EXPECTED_ROLES
            or tuple(reap_by_role) != EXPECTED_ROLES
            or no_spawn["expected_roles"] != list(EXPECTED_ROLES)
            or reaps["expected_roles"] != list(EXPECTED_ROLES)
            or journal["expected_roles"] != list(EXPECTED_ROLES)
            or no_spawn["complete_role_coverage"] is not True
            or reaps["complete_role_coverage"] is not True
            or journal["raw_derived_process_launches_sum"] != 2
            or journal["failure_prefix_cannot_be_exact"] is not False
            or journal["output_commit_id"] is None
            or any(
                output_events[0]["sequence"] >= reap_by_role[role]["sequence"]
                for role in EXPECTED_ROLES
            )
        ):
            _fail("exact process replay lacks two complete distinct roles")
    elif (
        journal["raw_derived_process_launches_sum"] is not None
        or journal["failure_prefix_cannot_be_exact"] is not True
        or no_spawn["complete_role_coverage"] is not False
        or reaps["complete_role_coverage"] is not False
    ):
        _fail("failure prefix attempted to become an exact process value")
    retained_identity = pre["retained_memory_peak_ofd_identity"]
    pre_events = [
        row
        for row in events
        if row["kind"]
        == LifecycleEventKindV2.MEMORY_PEAK_RESET_AND_PRE_READ.value
    ]
    if (
        len(pre_events) != 1
        or pre_events[0].get("sequence") != start
        or pre_events[0].get("role") is not None
        or pre_events[0].get("retained_memory_peak_ofd_identity")
        != retained_identity
        or pre_events[0].get("reset_write_ascii") != "0"
        or pre_events[0].get("pre_read_ascii") != pre["raw_read_ascii"]
        or pre_events[0].get("parsed_pre_peak_bytes")
        != pre["parsed_peak_bytes"]
        or pre["read_ordinal"] != 1
        or pre["read_sequence"] != start
        or pre["reset_write_ascii"] != "0"
        or _parse_peak(pre["raw_read_ascii"].encode("ascii"), "replayed pre peak")
        != pre["parsed_peak_bytes"]
        or pre["parsed_peak_bytes"] != 0
        or pre["no_baseline_subtraction"] is not True
        or same["retained_memory_peak_ofd_identity"] != retained_identity
        or same["named_memory_peak_initial_identity"] != retained_identity
        or same["named_memory_peak_final_identity"] != retained_identity
        or same["reset_pre_post_same_retained_fd"] is not True
        or same["pre_read_sequence"] != start
        or same["ofd_replacement_detected"] is not False
    ):
        _fail("memory pre-read or same-OFD evidence does not replay")
    exact_peak: int | None = None
    if exact:
        post_events = [
            row
            for row in events
            if row["kind"]
            == LifecycleEventKindV2.DESCENDANT_FREE_POST_READ.value
        ]
        if (
            len(post_events) != 1
            or post_events[0].get("sequence") != cutoff_sequence - 1
            or post_events[0].get("sequence") != post["read_sequence"]
            or post_events[0].get("role") is not None
            or post_events[0].get("retained_memory_peak_ofd_identity")
            != retained_identity
            or post_events[0].get("post_read_ascii") != post["raw_read_ascii"]
            or post_events[0].get("parsed_post_peak_bytes")
            != post["parsed_peak_bytes"]
            or post_events[0].get("post_cgroup_procs") != []
            or post_events[0].get("post_nr_descendants") != 0
            or post_events[0].get("post_nr_dying_descendants") != 0
            or post["read_ordinal"] != 2
            or post["read_performed"] is not True
            or type(post["raw_read_ascii"]) is not str
            or _parse_peak(
                post["raw_read_ascii"].encode("ascii"),
                "replayed post peak",
            )
            != post["parsed_peak_bytes"]
            or post["parsed_peak_bytes"] < pre["parsed_peak_bytes"]
            or post["raw_derived_max_bytes"]
            != max(pre["parsed_peak_bytes"], post["parsed_peak_bytes"])
            or post["after_output_commit"] is not True
            or post["after_direct_pidfd_reap_roles"] != list(EXPECTED_ROLES)
            or post["after_descendant_free_scan"] is not True
            or post["no_baseline_subtraction"] is not True
            or same["post_read_sequence"] != post["read_sequence"]
            or empty["pre_reset_cgroup_procs"] != []
            or empty["pre_reset_nr_descendants"] != 0
            or empty["pre_reset_nr_dying_descendants"] != 0
            or empty["post_reap_scan_performed"] is not True
            or empty["post_reap_cgroup_procs"] != []
            or empty["post_reap_nr_descendants"] != 0
            or empty["post_reap_nr_dying_descendants"] != 0
            or empty["direct_reaped_roles"] != list(EXPECTED_ROLES)
        ):
            _fail("exact memory MAX lacks same-OFD descendant-free post-read")
        exact_peak = post["raw_derived_max_bytes"]
    elif (
        post["read_performed"] is not False
        or post["raw_read_ascii"] is not None
        or post["parsed_peak_bytes"] is not None
        or post["raw_derived_max_bytes"] is not None
        or empty["post_reap_scan_performed"] is not False
    ):
        _fail("failure prefix attempted to become an exact memory MAX")
    return WorkingProcessRawReplayV2(
        _REPLAY_ISSUER,
        closure,
        cutoff_sequence,
        exact_peak,
        2 if exact else None,
        len(clone_events),
        clone_roles,
        exact,
        exact,
        False,
        False,
    )


def open_working_process_evidence_session_v2(
    *,
    live_envelope_id: str,
    occurrence_id: str,
    route_attempt_id: str,
    decision_point_id: str,
    measurement_window_id: str,
    measurement_start_sequence: int,
    memory_peak_fd: int,
    cgroup_directory_fd: int,
) -> WorkingProcessEvidenceSessionV2:
    return WorkingProcessEvidenceSessionV2(
        live_envelope_id=live_envelope_id,
        occurrence_id=occurrence_id,
        route_attempt_id=route_attempt_id,
        decision_point_id=decision_point_id,
        measurement_window_id=measurement_window_id,
        measurement_start_sequence=measurement_start_sequence,
        memory_peak_fd=memory_peak_fd,
        cgroup_directory_fd=cgroup_directory_fd,
    )


__all__ = (
    "CGROUP_EMPTY_SCHEMA_ID",
    "CUTOFF_SCHEMA_ID",
    "ConstructionSharedResourceWorkingProcessEvidenceV2Error",
    "EXPECTED_ROLES",
    "LifecycleEventKindV2",
    "MEMORY_PATH",
    "MEMORY_POST_SCHEMA_ID",
    "MEMORY_PRE_SCHEMA_ID",
    "NO_SPAWN_SCHEMA_ID",
    "PIDFD_REAP_SCHEMA_ID",
    "PROCESS_JOURNAL_SCHEMA_ID",
    "PROCESS_PATH",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SAME_OFD_SCHEMA_ID",
    "SCHEMA_VERSION",
    "SUPPORTED_PATHS",
    "WorkingProcessClosureKindV2",
    "WorkingProcessEvidenceSessionV2",
    "WorkingProcessRawEvidenceBundleV2",
    "WorkingProcessRawReplayV2",
    "WorkingProcessSessionStateV2",
    "open_working_process_evidence_session_v2",
    "replay_working_process_raw_evidence_v2",
)
