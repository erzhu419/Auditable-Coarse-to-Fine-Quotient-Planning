"""Sealed, resource-accounted abstract model execution.

This additive executor keeps the historical V1 path intact.  It snapshots the
exact model-only Python closure into the existing immutable runtime CAS, opens
one invocation-private lease, launches one fresh ``python -I`` worker, and
retains independently replayable measurements for eight of the nine shared
resource paths.  ``io.output_bytes`` is deliberately absent: the formal value
must be solved together with the final CounterRecord/WorkVector/Comparison
artifact set.

The child globally meters business SHA-256 constructors between an explicit
window start and the accounting/provenance cutoff.  The parent meters its own
business SHA-256 constructors, observes the child through ``waitid(WNOWAIT)``
and ``wait4``, evaluates a preregistered runtime-read upper formula, and
derives exact staging/mount traffic from the immutable lease and sandbox
files.  No ground, local-recovery, fallback, or host planner is invoked.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import InitVar, dataclass, field
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Iterator, Mapping, NoReturn
import weakref

from acfqp.accounting_v1 import (
    RouteKindEnum,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.native_recorder_v1 import NativeCounterRecorderV1, verify_recorded_work_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_MEASUREMENT_WINDOW_V2_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_RUNTIME_PREPARATION_V2_DOMAIN,
    CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_WORKER_OUTPUT_V2_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
)
from acfqp.phase3e_model_only_executor_v1 import (
    MODEL_ONLY_NATIVE_RECORDER_ID,
    ModelOnlyQueryExecutionArtifactV1,
    ModelOnlyQueryExecutionV1,
    ModelOnlyNativeEventTraceV1,
    _mint_model_only_query_execution_v1,
    _parse_worker_output_v1,
    model_only_execution_request_v1,
)
from acfqp.phase3e_model_only_v1 import ModelOnlyOutcome
from acfqp.phase3e_rapm_consumer_v1 import (
    ModelOnlyRAPMSourceV1,
    require_model_only_source_authority_v1,
)
from acfqp.phase3e_sealed_executor_v1 import (
    OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE,
    RUNTIME_FACTORY_TREE_PASSES,
    RuntimeManifestCapProfileV1,
    RuntimeTreeCASV1,
    RuntimeTreeManifestV1,
)


SCHEMA_VERSION = "2.0.0"
PROFILE_KEY = "phase3e_model_only_accounted_executor_v2"
WORKER_SCHEMA = "acfqp.phase3e_model_only_accounted_worker_output.v2"
RUNTIME_ENTRYPOINT = "acfqp/phase3e_model_only_accounted_runtime_v2.py"
ISOLATION_PROFILE_ID = "sealed_runtime_tree_fresh_python_I_wait4_v2"
MEASUREMENT_STATUS = "EIGHT_SHARED_PATHS_EXACT_OUTPUT_FIXED_POINT_PENDING"

PREPARATION_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_RUNTIME_PREPARATION_V2_DOMAIN
)
WORKER_OUTPUT_DOMAIN = CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_WORKER_OUTPUT_V2_DOMAIN
MEASUREMENT_DOMAIN = (
    CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_MEASUREMENT_WINDOW_V2_DOMAIN
)
LOCAL_DOMAINS = frozenset(
    {PREPARATION_DOMAIN, WORKER_OUTPUT_DOMAIN, MEASUREMENT_DOMAIN}
)
if len(LOCAL_DOMAINS) != 3 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("accounted model-only domains are not central and unique")

FORMAL_SHARED_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)
PENDING_SHARED_PATH = "io.output_bytes"
RUNTIME_IMPORT_READ_PASSES_UPPER = 2

PARENT_INTEGRITY_OBLIGATIONS = (
    "source_authority_replayed",
    "runtime_preparation_replayed",
    "runtime_cas_resolved",
    "private_runtime_lease_replayed",
    "child_completion_observed",
    "worker_wrapper_replayed",
    "nested_result_replayed",
    "resource_observation_reconciled",
)
PARENT_PROTOCOL_OBLIGATIONS = (
    "prelaunch_identity_joined",
    "exact_fresh_process_argv_used",
    "quiet_stdout_stderr_required",
    "worker_wrapper_exact_schema_required",
    "request_result_identity_joined",
    "operational_cutoff_closed_before_evidence_ids",
)

# Static modulefinder closure of the historical model-only runtime plus this
# additive entrypoint.  Forbidden modules may be present as inert bytes; the
# worker import deny-list still proves that none is imported operationally.
ACCOUNTED_RUNTIME_SOURCE_PATHS = (
    "acfqp/__init__.py",
    "acfqp/_runtime_authority_v1.py",
    "acfqp/abstraction/__init__.py",
    "acfqp/abstraction/partition.py",
    "acfqp/abstraction/quotient.py",
    "acfqp/access_protocol_v1.py",
    "acfqp/accounting_v1.py",
    "acfqp/actual_accounting_v1.py",
    "acfqp/aliased_safe_chain.py",
    "acfqp/artifacts.py",
    "acfqp/build_coverage.py",
    "acfqp/campaign_v1.py",
    "acfqp/core.py",
    "acfqp/domains/__init__.py",
    "acfqp/domains/g2048.py",
    "acfqp/domains/matching_buffer.py",
    "acfqp/domains/semantic.py",
    "acfqp/enumeration.py",
    "acfqp/frozen_phase3c.py",
    "acfqp/general_local_recovery.py",
    "acfqp/general_local_solver.py",
    "acfqp/local_recovery.py",
    "acfqp/local_solver.py",
    "acfqp/marginal_accounting_v1.py",
    "acfqp/native_recorder_v1.py",
    "acfqp/phase05.py",
    "acfqp/phase3c.py",
    "acfqp/phase3d.py",
    "acfqp/phase3e_exact_cache_v1.py",
    "acfqp/phase3e_failure_continuation_v1.py",
    "acfqp/phase3e_fallback_v1.py",
    "acfqp/phase3e_ground_handoff_v1.py",
    "acfqp/phase3e_ids.py",
    "acfqp/phase3e_local_preselection_v1.py",
    "acfqp/phase3e_local_semantics_v1.py",
    "acfqp/phase3e_model_only_accounted_runtime_v2.py",
    "acfqp/phase3e_model_only_executor_v1.py",
    "acfqp/phase3e_model_only_runtime_v1.py",
    "acfqp/phase3e_model_only_v1.py",
    "acfqp/phase3e_occurrence_accounting_v1.py",
    "acfqp/phase3e_occurrence_runner_v1.py",
    "acfqp/phase3e_rapm_consumer_v1.py",
    "acfqp/phase3e_runner_v1.py",
    "acfqp/phase3e_sealed_executor_v1.py",
    "acfqp/phase3e_threshold_v1.py",
    "acfqp/phase3e_transactions_v1.py",
    "acfqp/phase3e_two_stage_accounting_v1.py",
    "acfqp/planning/__init__.py",
    "acfqp/planning/audit.py",
    "acfqp/planning/common.py",
    "acfqp/planning/ground.py",
    "acfqp/planning/lift.py",
    "acfqp/planning/nominal.py",
    "acfqp/planning/policy.py",
    "acfqp/planning/production.py",
    "acfqp/portable.py",
    "acfqp/portable_planner.py",
    "acfqp/portable_sound_audit_v1.py",
    "acfqp/refinement/__init__.py",
    "acfqp/refinement/cegar.py",
    "acfqp/refinement/predicates.py",
    "acfqp/refinement/split.py",
    "acfqp/route_upper_formula_v1.py",
    "acfqp/routing_v1.py",
    "acfqp/semantic_verification_v1.py",
    "acfqp/sparse_capability.py",
)
if tuple(sorted(ACCOUNTED_RUNTIME_SOURCE_PATHS)) != ACCOUNTED_RUNTIME_SOURCE_PATHS:
    raise RuntimeError("accounted runtime source paths are not canonical")

_PREPARATION_ISSUER = object()
_EXECUTION_AUTHORITY = object()
_PARENT_HASH_LOCK = threading.Lock()


class Phase3EModelOnlyAccountedExecutorV2Error(ValueError):
    """The sealed runtime, process, measurement, or identity join failed."""


def _fail(message: str) -> NoReturn:
    raise Phase3EModelOnlyAccountedExecutorV2Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise Phase3EModelOnlyAccountedExecutorV2Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class AccountedRuntimePreparationV2:
    _issuer: InitVar[object]
    runtime_cas: RuntimeTreeCASV1 = field(repr=False, compare=False)
    manifest: RuntimeTreeManifestV1
    cap_profile: RuntimeManifestCapProfileV1
    source_paths: tuple[str, ...]
    _preparation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PREPARATION_ISSUER:
            _fail("accounted runtime preparation is caller-minted")
        if (
            type(self.runtime_cas) is not RuntimeTreeCASV1
            or type(self.manifest) is not RuntimeTreeManifestV1
            or type(self.cap_profile) is not RuntimeManifestCapProfileV1
            or self.cap_profile != OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE
            or self.source_paths != ACCOUNTED_RUNTIME_SOURCE_PATHS
            or tuple(row.relative_path for row in self.manifest.entries)
            != self.source_paths
        ):
            _fail("accounted runtime preparation changed")
        object.__setattr__(
            self,
            "_preparation_id",
            content_id(PREPARATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.phase3e_model_only_accounted_runtime_preparation.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "runtime_manifest": self.manifest.to_dict(),
            "runtime_manifest_cap_profile": self.cap_profile.to_dict(),
            "source_paths": list(self.source_paths),
            "runtime_entrypoint": RUNTIME_ENTRYPOINT,
            "private_runtime_lease_required": True,
            "runtime_tree_build_charged_to_occurrence": False,
            "official_execution_allowed": False,
        }

    @property
    def preparation_id(self) -> str:
        expected = content_id(PREPARATION_DOMAIN, self._payload())
        if expected != self._preparation_id:
            _fail("accounted runtime preparation changed after issuance")
        return self._preparation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "accounted_runtime_preparation_id": self.preparation_id}


def prepare_model_only_accounted_runtime_v2(
    *,
    source_root: str | Path,
    runtime_cas_root: str | Path,
) -> AccountedRuntimePreparationV2:
    """Build/reuse one exact model-only runtime CAS object before execution."""

    source = Path(source_root).resolve(strict=True)
    cas = RuntimeTreeCASV1(Path(runtime_cas_root).resolve())
    with tempfile.TemporaryDirectory(prefix="acfqp-accounted-runtime-build-") as temporary:
        build = Path(temporary)
        for relative in ACCOUNTED_RUNTIME_SOURCE_PATHS:
            origin = source / relative
            if origin.is_symlink() or not origin.is_file():
                _fail(f"accounted runtime source is missing: {relative}")
            target = build / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin, target)
            target.chmod(0o444)
        manifest = cas.snapshot_build_tree(build)
    resolved = cas.resolve(
        manifest.runtime_tree_id,
        cap_profile=OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE,
    )
    if resolved.manifest != manifest:
        _fail("accounted runtime CAS replay changed after preparation")
    return AccountedRuntimePreparationV2(
        _PREPARATION_ISSUER,
        cas,
        manifest,
        OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE,
        ACCOUNTED_RUNTIME_SOURCE_PATHS,
    )


class _ParentHashMeterV2:
    def __init__(self) -> None:
        self.count = 0
        self._original: Any = None
        self._installed: Any = None

    def __enter__(self) -> "_ParentHashMeterV2":
        if not _PARENT_HASH_LOCK.acquire(blocking=False):
            _fail("another parent business hash window is active")
        self._original = hashlib.sha256

        def metered_sha256(*args: Any, **kwargs: Any) -> Any:
            self.count += 1
            return self._original(*args, **kwargs)

        self._installed = metered_sha256
        hashlib.sha256 = metered_sha256  # type: ignore[assignment]
        return self

    def __exit__(self, _kind: object, _value: object, _traceback: object) -> None:
        changed = hashlib.sha256 is not self._installed
        hashlib.sha256 = self._original  # type: ignore[assignment]
        _PARENT_HASH_LOCK.release()
        if changed:
            _fail("parent business hash meter binding changed")


@dataclass(slots=True)
class _ParentObligationMeterV2:
    integrity_rows: list[str] = field(default_factory=list)
    protocol_rows: list[str] = field(default_factory=list)

    def integrity(self, name: str) -> None:
        if name not in PARENT_INTEGRITY_OBLIGATIONS or name in self.integrity_rows:
            _fail("parent integrity obligation is unknown or duplicated")
        self.integrity_rows.append(name)

    def protocol(self, name: str) -> None:
        if name not in PARENT_PROTOCOL_OBLIGATIONS or name in self.protocol_rows:
            _fail("parent protocol obligation is unknown or duplicated")
        self.protocol_rows.append(name)

    def close(self) -> None:
        if (
            tuple(self.integrity_rows) != PARENT_INTEGRITY_OBLIGATIONS
            or tuple(self.protocol_rows) != PARENT_PROTOCOL_OBLIGATIONS
        ):
            _fail("parent obligation window did not close exactly")


@dataclass(frozen=True, slots=True)
class _ChildResourceObservationV2:
    returncode: int
    wait4_peak_bytes: int

    def __post_init__(self) -> None:
        for name in (
            "returncode",
            "wait4_peak_bytes",
        ):
            value = getattr(self, name)
            if type(value) is not int or (name != "returncode" and value < 0):
                _fail(f"child resource field {name} is invalid")
        if self.returncode != 0 or self.wait4_peak_bytes <= 0:
            _fail("child resource observation is not a successful bounded run")


def _wait_and_observe_child_v2(
    process: subprocess.Popen[bytes], *, timeout_seconds: int
) -> _ChildResourceObservationV2:
    if not sys.platform.startswith("linux") or not hasattr(os, "wait4"):
        _fail("accounted model-only execution requires Linux wait4")
    deadline = time.monotonic() + timeout_seconds
    while True:
        waited_pid, status, usage = os.wait4(process.pid, os.WNOHANG)
        if waited_pid == process.pid:
            break
        if time.monotonic() >= deadline:
            process.send_signal(signal.SIGKILL)
            os.wait4(process.pid, 0)
            process.returncode = -signal.SIGKILL
            _fail("accounted model-only worker timed out")
        time.sleep(0.01)
    returncode = os.waitstatus_to_exitcode(status)
    process.returncode = returncode
    wait4_peak = int(usage.ru_maxrss) * 1024
    return _ChildResourceObservationV2(
        returncode,
        wait4_peak,
    )


@dataclass(frozen=True, slots=True)
class AccountedMeasurementWindowV2:
    preparation_id: str
    runtime_tree_id: str
    request_id: str
    worker_output_id: str
    accounted_worker_output_id: str
    result_id: str
    operational_execution_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    route_decision_context_id: str
    runtime_file_count: int
    runtime_total_bytes: int
    runtime_manifest_document_bytes: int
    request_bytes: int
    nested_worker_output_bytes: int
    accounted_worker_output_bytes: int
    child_wait4_peak_bytes: int
    parent_hash_invocations: int
    child_hash_invocations: int
    parent_integrity_obligations: tuple[str, ...]
    parent_protocol_obligations: tuple[str, ...]
    shared_values: tuple[tuple[str, int], ...]
    _measurement_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.preparation_id, "preparation"),
            (self.runtime_tree_id, "runtime tree"),
            (self.request_id, "request"),
            (self.worker_output_id, "worker output"),
            (self.accounted_worker_output_id, "accounted worker output"),
            (self.result_id, "result"),
            (self.operational_execution_id, "operational execution"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.route_decision_context_id, "route context"),
        ):
            _cid(value, label)
        numeric = (
            self.runtime_file_count,
            self.runtime_total_bytes,
            self.runtime_manifest_document_bytes,
            self.request_bytes,
            self.nested_worker_output_bytes,
            self.accounted_worker_output_bytes,
            self.child_wait4_peak_bytes,
            self.parent_hash_invocations,
            self.child_hash_invocations,
        )
        if any(type(value) is not int or value <= 0 for value in numeric):
            _fail("accounted measurement numeric evidence must be positive")
        if (
            self.parent_integrity_obligations != PARENT_INTEGRITY_OBLIGATIONS
            or self.parent_protocol_obligations != PARENT_PROTOCOL_OBLIGATIONS
            or tuple(path for path, _value in self.shared_values) != FORMAL_SHARED_PATHS
            or any(type(value) is not int or value <= 0 for _path, value in self.shared_values)
        ):
            _fail("accounted measurement shared-resource inventory changed")
        values = dict(self.shared_values)
        expected = {
            "common.hash_invocations": (
                self.parent_hash_invocations + self.child_hash_invocations
            ),
            "common.integrity_checks": len(self.parent_integrity_obligations),
            "common.protocol_checks": len(self.parent_protocol_obligations),
            "io.mounted_bytes_peak": (
                self.runtime_total_bytes
                + self.request_bytes
                + self.accounted_worker_output_bytes
            ),
            "io.read_bytes": (
                self.runtime_manifest_document_bytes
                + (
                    RUNTIME_FACTORY_TREE_PASSES
                    + RUNTIME_IMPORT_READ_PASSES_UPPER
                )
                * self.runtime_total_bytes
                + self.request_bytes
                + self.accounted_worker_output_bytes
            ),
            "io.staged_bytes": self.runtime_total_bytes + self.request_bytes,
            "memory.working_bytes_peak": self.child_wait4_peak_bytes,
            "process.launches": 1,
        }
        # Child integrity/protocol values are added by the issuer after the
        # historical event trace is replayed; exact totals are checked there.
        if any(values[path] != expected[path] for path in expected if path not in {
            "common.integrity_checks", "common.protocol_checks"
        }):
            _fail("accounted measurement formula changed")
        if (
            values["common.integrity_checks"] <= expected["common.integrity_checks"]
            or values["common.protocol_checks"] <= expected["common.protocol_checks"]
        ):
            _fail("child named obligations are missing from shared totals")
        object.__setattr__(
            self, "_measurement_id", content_id(MEASUREMENT_DOMAIN, self._payload())
        )

    @property
    def values(self) -> dict[str, int]:
        return dict(self.shared_values)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.phase3e_model_only_accounted_measurement_window.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "preparation_id": self.preparation_id,
            "runtime_tree_id": self.runtime_tree_id,
            "request_id": self.request_id,
            "worker_output_id": self.worker_output_id,
            "accounted_worker_output_id": self.accounted_worker_output_id,
            "result_id": self.result_id,
            "operational_execution_id": self.operational_execution_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "route_decision_context_id": self.route_decision_context_id,
            "runtime_file_count": self.runtime_file_count,
            "runtime_total_bytes": self.runtime_total_bytes,
            "runtime_manifest_document_bytes": self.runtime_manifest_document_bytes,
            "request_bytes": self.request_bytes,
            "nested_worker_output_bytes": self.nested_worker_output_bytes,
            "accounted_worker_output_bytes": self.accounted_worker_output_bytes,
            "child_wait4_peak_bytes": self.child_wait4_peak_bytes,
            "runtime_import_read_passes_upper": RUNTIME_IMPORT_READ_PASSES_UPPER,
            "parent_hash_invocations": self.parent_hash_invocations,
            "child_hash_invocations": self.child_hash_invocations,
            "parent_integrity_obligations": list(self.parent_integrity_obligations),
            "parent_protocol_obligations": list(self.parent_protocol_obligations),
            "shared_values": [
                {"path": path, "value": value}
                for path, value in self.shared_values
            ],
            "measurement_window_start": "BEFORE_REQUEST_AND_RUNTIME_CAS_RESOLUTION",
            "measurement_window_end": "AFTER_RESULT_AND_RESOURCE_REPLAY_BEFORE_EVIDENCE_IDS",
            "hash_accounting_provenance_excluded": True,
            "read_value_kind": "VERIFIED_UPPER_BOUND_SEALED_RUNTIME_AND_TRANSFERS",
            "staged_value_kind": "EXACT_PRIVATE_LEASE_AND_REQUEST_BYTES",
            "mounted_value_kind": "EXACT_SIMULTANEOUS_SANDBOX_PAYLOAD",
            "working_value_kind": "PARENT_WAIT4_AND_WAITABLE_PROC_PEAK_MAX",
            "output_counter_record_pending_fixed_point": True,
            "formal_shared_path_count": len(FORMAL_SHARED_PATHS),
            "formal_counter_records_issued_here": False,
            "official_execution_allowed": False,
        }

    @property
    def measurement_id(self) -> str:
        expected = content_id(MEASUREMENT_DOMAIN, self._payload())
        if expected != self._measurement_id:
            _fail("accounted measurement changed after issuance")
        return self._measurement_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "accounted_measurement_window_id": self.measurement_id}


class AccountedModelOnlyExecutionV2:
    __slots__ = (
        "_execution",
        "_measurement",
        "_preparation",
        "_authority",
        "_token",
        "__weakref__",
    )

    def __init__(
        self,
        execution: ModelOnlyQueryExecutionV1,
        measurement: AccountedMeasurementWindowV2,
        preparation: AccountedRuntimePreparationV2,
        authority: object,
    ) -> None:
        if authority is not _EXECUTION_AUTHORITY:
            _fail("accounted model-only execution is caller-minted")
        self._execution = execution
        self._measurement = measurement
        self._preparation = preparation
        self._authority = authority
        self._token = object()
        identity = id(self)

        def discard(reference: weakref.ReferenceType[AccountedModelOnlyExecutionV2]) -> None:
            current = _LIVE_EXECUTIONS.get(identity)
            if current is not None and current[0] is reference:
                _LIVE_EXECUTIONS.pop(identity, None)

        reference = weakref.ref(self, discard)
        _LIVE_EXECUTIONS[identity] = (reference, self._token)

    def __setattr__(self, name: str, value: object) -> None:
        if hasattr(self, name):
            raise AttributeError("AccountedModelOnlyExecutionV2 is immutable")
        object.__setattr__(self, name, value)

    @property
    def execution(self) -> ModelOnlyQueryExecutionV1:
        return self._execution

    @property
    def measurement(self) -> AccountedMeasurementWindowV2:
        return self._measurement

    @property
    def preparation(self) -> AccountedRuntimePreparationV2:
        return self._preparation

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.phase3e_model_only_accounted_execution.v2",
            "schema_version": SCHEMA_VERSION,
            "preparation": self.preparation.to_document(),
            "measurement": self.measurement.to_document(),
            "legacy_transport_projection": self.execution.to_dict(),
            "measurement_status": MEASUREMENT_STATUS,
            "formal_output_fixed_point_present": False,
            "official_execution_allowed": False,
        }


_LIVE_EXECUTIONS: dict[
    int, tuple[weakref.ReferenceType[AccountedModelOnlyExecutionV2], object]
] = {}


def require_accounted_model_only_execution_v2(
    value: object,
) -> AccountedModelOnlyExecutionV2:
    if type(value) is not AccountedModelOnlyExecutionV2:
        _fail("exact accounted model-only execution authority is required")
    current = _LIVE_EXECUTIONS.get(id(value))
    if (
        current is None
        or current[0]() is not value
        or current[1] is not value._token
        or value._authority is not _EXECUTION_AUTHORITY
    ):
        _fail("accounted model-only execution authority is not live")
    value.measurement.__post_init__()
    value.preparation.__post_init__(_PREPARATION_ISSUER)
    if (
        value.measurement.preparation_id != value.preparation.preparation_id
        or value.measurement.operational_execution_id
        != value.execution.operational_execution_id
    ):
        _fail("accounted model-only execution roots crossed")
    return value


def _parse_accounted_worker_output_v2(
    raw: bytes,
    *,
    request: Any,
    source: ModelOnlyRAPMSourceV1,
) -> tuple[str, str, Any, ModelOnlyNativeEventTraceV1, int, int, int]:
    loads_canonical_json(raw)
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Phase3EModelOnlyAccountedExecutorV2Error(
            "accounted worker output is not canonical UTF-8 JSON"
        ) from error
    if type(document) is not dict:
        _fail("accounted worker output root must be an object")
    require_exact_fields(
        document,
        {
            "schema",
            "schema_version",
            "request_id",
            "nested_worker_output",
            "business_hash_invocations",
            "hash_measurement_window_start",
            "hash_measurement_window_end",
            "accounting_provenance_hashes_excluded",
            "global_hashlib_sha256_constructor_hook_present",
            "formal_counter_record_issued_by_worker",
            "accounted_worker_output_id",
        },
        context="accounted model-only worker output",
    )
    if (
        document["schema"] != WORKER_SCHEMA
        or document["schema_version"] != SCHEMA_VERSION
        or document["request_id"] != request.request_id
        or type(document["nested_worker_output"]) is not dict
        or type(document["business_hash_invocations"]) is not int
        or document["business_hash_invocations"] <= 0
        or document["hash_measurement_window_start"]
        != "AFTER_RUNTIME_INFRASTRUCTURE_IMPORTS"
        or document["hash_measurement_window_end"]
        != "BEFORE_ACCOUNTING_AND_PROVENANCE_SERIALIZATION"
        or document["accounting_provenance_hashes_excluded"] is not True
        or document["global_hashlib_sha256_constructor_hook_present"] is not True
        or document["formal_counter_record_issued_by_worker"] is not False
    ):
        _fail("accounted worker output contract changed")
    payload = dict(document)
    observed_id = payload.pop("accounted_worker_output_id")
    expected_id = content_id(WORKER_OUTPUT_DOMAIN, payload)
    if observed_id != expected_id:
        _fail("accounted worker output ID mismatch")
    nested = document["nested_worker_output"]
    output_id, result, trace, self_peak = _parse_worker_output_v1(
        nested,
        request=request,
        source=source,
    )
    return (
        observed_id,
        output_id,
        result,
        trace,
        self_peak,
        document["business_hash_invocations"],
        len(canonical_json_bytes(nested)),
    )


def execute_model_only_accounted_query_v2(
    source: ModelOnlyRAPMSourceV1,
    preparation: AccountedRuntimePreparationV2,
    *,
    regret_tolerance: Fraction | int = Fraction(1, 20),
    timeout_seconds: int = 120,
) -> AccountedModelOnlyExecutionV2:
    """Run one sealed abstract query and retain eight shared measurements."""

    if type(preparation) is not AccountedRuntimePreparationV2:
        _fail("execution requires exact accounted runtime preparation")
    preparation.__post_init__(_PREPARATION_ISSUER)
    try:
        require_model_only_source_authority_v1(source)
    except ValueError as error:
        raise Phase3EModelOnlyAccountedExecutorV2Error(
            f"execution requires live source authority: {error}"
        ) from error
    if type(timeout_seconds) is not int or timeout_seconds <= 0:
        _fail("timeout_seconds must be positive")

    obligations = _ParentObligationMeterV2()
    parent_meter = _ParentHashMeterV2()
    with parent_meter:
        obligations.integrity("source_authority_replayed")
        request = model_only_execution_request_v1(
            source, regret_tolerance=regret_tolerance
        )
        request_raw = canonical_json_bytes(request.to_dict())
        obligations.protocol("prelaunch_identity_joined")
        preparation.__post_init__(_PREPARATION_ISSUER)
        obligations.integrity("runtime_preparation_replayed")
        verified = preparation.runtime_cas.resolve(
            preparation.manifest.runtime_tree_id,
            cap_profile=preparation.cap_profile,
        )
        if verified.manifest != preparation.manifest:
            _fail("runtime CAS resolved another manifest")
        obligations.integrity("runtime_cas_resolved")

        with verified.open_private_lease() as lease:
            obligations.integrity("private_runtime_lease_replayed")
            entrypoint = lease.root / RUNTIME_ENTRYPOINT
            if entrypoint.is_symlink() or not entrypoint.is_file():
                _fail("accounted worker entrypoint is absent from the private lease")
            obligations.protocol("exact_fresh_process_argv_used")
            with tempfile.TemporaryDirectory(prefix="acfqp-accounted-model-only-") as temporary:
                sandbox = Path(temporary)
                request_path = sandbox / "request.json"
                output_path = sandbox / "output.json"
                stdout_path = sandbox / "stdout.bin"
                stderr_path = sandbox / "stderr.bin"
                request_path.write_bytes(request_raw)
                argv = (
                    sys.executable,
                    "-I",
                    "-B",
                    str(entrypoint),
                    "--runtime-source",
                    str(lease.root),
                    "--request",
                    str(request_path),
                    "--output",
                    str(output_path),
                )
                with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
                    process = subprocess.Popen(
                        argv,
                        cwd=sandbox,
                        env={
                            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                            "LANG": "C.UTF-8",
                            "PYTHONHASHSEED": "0",
                            "PYTHONDONTWRITEBYTECODE": "1",
                        },
                        stdin=subprocess.DEVNULL,
                        stdout=stdout,
                        stderr=stderr,
                        close_fds=True,
                    )
                    resources = _wait_and_observe_child_v2(
                        process, timeout_seconds=timeout_seconds
                    )
                obligations.integrity("child_completion_observed")
                stdout_raw = stdout_path.read_bytes()
                stderr_raw = stderr_path.read_bytes()
                if stdout_raw or stderr_raw or not output_path.is_file():
                    _fail("accounted worker was noisy or omitted its output")
                obligations.protocol("quiet_stdout_stderr_required")
                wrapper_raw = output_path.read_bytes()
                (
                    accounted_output_id,
                    worker_output_id,
                    result,
                    trace,
                    self_peak,
                    child_hashes,
                    nested_output_bytes,
                ) = _parse_accounted_worker_output_v2(
                    wrapper_raw,
                    request=request,
                    source=source,
                )
                obligations.protocol("worker_wrapper_exact_schema_required")
                obligations.integrity("worker_wrapper_replayed")
                if (
                    result.outcome is not ModelOnlyOutcome.PASS
                    or result.ground_binding_required
                    or result.route_attempt.route_attempt_id
                    != result.route_context.route_attempt_id
                ):
                    _fail("accounted abstract execution did not produce one strict PASS")
                obligations.integrity("nested_result_replayed")
                obligations.protocol("request_result_identity_joined")
                obligations.integrity("resource_observation_reconciled")
                obligations.protocol(
                    "operational_cutoff_closed_before_evidence_ids"
                )
                obligations.close()

    if parent_meter.count <= 0:
        _fail("parent business hash window produced no observation")

    # Historical V1 transport remains a compatibility projection only.  The
    # V2 formal authority consumes the independent measurement below and does
    # not relabel these legacy values.
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    recorder = NativeCounterRecorderV1(
        subject_id=result.route_attempt.route_attempt_id,
        route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=comparison,
        recorder_id=MODEL_ONLY_NATIVE_RECORDER_ID,
    )
    for path, amount in trace.totals.items():
        if amount:
            recorder.add(path, amount)
    recorder.add("common.integrity_checks", 6)
    recorder.add("common.protocol_checks", 5)
    recorder.add("common.hash_invocations", 2)
    recorder.add("io.read_bytes", len(request_raw) + nested_output_bytes)
    recorder.add("io.staged_bytes", len(request_raw))
    recorder.add("io.output_bytes", nested_output_bytes)
    recorder.observe_peak("memory.working_bytes_peak", self_peak)
    recorder.record_process_completion(success=True)
    recorder.record_solver_completion(success=True)
    recorder.record_route_completion(success=True)
    legacy_work = recorder.seal()
    verify_recorded_work_v1(
        legacy_work,
        expected_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=comparison,
    )
    artifact = ModelOnlyQueryExecutionArtifactV1(
        request.request_id,
        worker_output_id,
        result,
        trace,
        legacy_work,
    )
    execution = _mint_model_only_query_execution_v1(artifact)

    shared = {
        "common.hash_invocations": parent_meter.count + child_hashes,
        "common.integrity_checks": (
            trace.totals["common.integrity_checks"]
            + len(obligations.integrity_rows)
        ),
        "common.protocol_checks": (
            trace.totals["common.protocol_checks"]
            + len(obligations.protocol_rows)
        ),
        "io.mounted_bytes_peak": (
            preparation.manifest.total_bytes + len(request_raw) + len(wrapper_raw)
        ),
        "io.read_bytes": (
            preparation.manifest.manifest_document_bytes
            + (
                RUNTIME_FACTORY_TREE_PASSES
                + RUNTIME_IMPORT_READ_PASSES_UPPER
            )
            * preparation.manifest.total_bytes
            + len(request_raw)
            + len(wrapper_raw)
        ),
        "io.staged_bytes": preparation.manifest.total_bytes + len(request_raw),
        "memory.working_bytes_peak": resources.wait4_peak_bytes,
        "process.launches": 1,
    }
    measurement = AccountedMeasurementWindowV2(
        preparation.preparation_id,
        preparation.manifest.runtime_tree_id,
        request.request_id,
        worker_output_id,
        accounted_output_id,
        result.result_id,
        execution.operational_execution_id,
        result.logical_occurrence.logical_occurrence_id,
        result.route_attempt.route_attempt_id,
        result.route_context.route_decision_context_id,
        preparation.manifest.file_count,
        preparation.manifest.total_bytes,
        preparation.manifest.manifest_document_bytes,
        len(request_raw),
        nested_output_bytes,
        len(wrapper_raw),
        resources.wait4_peak_bytes,
        parent_meter.count,
        child_hashes,
        tuple(obligations.integrity_rows),
        tuple(obligations.protocol_rows),
        tuple((path, shared[path]) for path in FORMAL_SHARED_PATHS),
    )
    return AccountedModelOnlyExecutionV2(
        execution, measurement, preparation, _EXECUTION_AUTHORITY
    )


__all__ = (
    "ACCOUNTED_RUNTIME_SOURCE_PATHS",
    "AccountedMeasurementWindowV2",
    "AccountedModelOnlyExecutionV2",
    "AccountedRuntimePreparationV2",
    "FORMAL_SHARED_PATHS",
    "MEASUREMENT_STATUS",
    "PENDING_SHARED_PATH",
    "Phase3EModelOnlyAccountedExecutorV2Error",
    "execute_model_only_accounted_query_v2",
    "prepare_model_only_accounted_runtime_v2",
    "require_accounted_model_only_execution_v2",
)
