"""Trusted fresh-process supervisor for the recovery-eligible K7 loop.

Three preregistered cache artifacts and the fresh query identity are frozen
before one isolated worker launch.  The parent then replays the portable
three-stage chain and closes eight pre-output shared-resource measurements.
``io.output_bytes`` and the final mounted peak remain pending until the
occurrence output fixed point is solved.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import _v075_construction_source_runtime_v2 as source_runtime
from acfqp import construction_accounting_live_v3 as live_v3
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_recovery_eligible_stage_accounting_v1 as stage_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OPERATIONAL_TRACE_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_RUNTIME_PREPARATION_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_MEASUREMENT_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SUPERVISED_REQUEST_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
)
from acfqp.phase3e_sealed_executor_v1 import (
    OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE,
    RUNTIME_FACTORY_TREE_PASSES,
    RuntimeManifestCapProfileV1,
    RuntimeTreeCASV1,
    RuntimeTreeManifestV1,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.115"
PROFILE_KEY = "construction_k7_recovery_eligible_supervised_executor_v1"
PRIMARY_RUNTIME_ROOT_MODULES = (
    "acfqp.construction_k7_recovery_eligible_accounted_runtime_v1",
)
RUNTIME_DYNAMIC_ROOT_PREFIX = "acfqp.v075_"
RUNTIME_ENTRYPOINT = (
    "acfqp/construction_k7_recovery_eligible_accounted_runtime_v1.py"
)
RUNTIME_IMPORT_READ_PASSES_UPPER = 2
DEFAULT_TIMEOUT_SECONDS = 3_600
MAX_TRACE_BYTES = 128 * 1024 * 1024

PREPARATION_DOMAIN = (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_RUNTIME_PREPARATION_V1_DOMAIN
)
REQUEST_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SUPERVISED_REQUEST_V1_DOMAIN
TRACE_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OPERATIONAL_TRACE_V1_DOMAIN
MEASUREMENT_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_MEASUREMENT_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {PREPARATION_DOMAIN, REQUEST_DOMAIN, TRACE_DOMAIN, MEASUREMENT_DOMAIN}
)
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("recovery supervisor domains are not central")

INPUT_ROLES = (
    ("SOURCE_BUNDLE_BINDING", "source_bundle_binding.json"),
    ("REUSABLE_RAPM_SNAPSHOT", "reusable_rapm_snapshot.json"),
    ("PROOF_DEPENDENCY_TRANSITION", "proof_dependency_transition.json"),
)
PRE_OUTPUT_SHARED_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)

PARENT_INTEGRITY_OBLIGATIONS = (
    "runtime-preparation-replayed",
    "three-input-canonical-digests-replayed",
    "runtime-cas-resolved",
    "private-runtime-lease-replayed",
    "child-completion-observed",
    "trace-canonical-and-content-id-replayed",
    "three-stage-event-chains-replayed",
    "science-summary-identity-chain-replayed",
    "resource-formulas-reconciled",
)
PARENT_PROTOCOL_OBLIGATIONS = (
    "fresh-query-frozen-before-launch",
    "checkpoint-before-ground-enforced",
    "fresh-python-I-argv-executed",
    "single-process-launch-observed",
    "quiet-stdout-stderr-enforced",
    "worker-trace-schema-enforced",
    "stage-order-and-owner-chain-enforced",
    "terminal-route-reconciliation-enforced",
    "operational-cutoff-precedes-accounting-provenance",
)
EXPECTED_CHILD_INTEGRITY_OBLIGATIONS = tuple(
    sorted(
        (
            "request-canonical-and-content-id-replayed",
            "input-source_bundle_binding-digest-replayed",
            "input-reusable_rapm_snapshot-digest-replayed",
            "input-proof_dependency_transition-digest-replayed",
            "persistent-cache-and-checkpoint-replayed",
            "native-accounting-identity-replayed",
            "three-stage-inventory-replayed",
            "science-summary-derived-from-live-result",
            *(f"stage-{index:02d}-event-to-vector-replay" for index in range(1, 4)),
        )
    )
)
EXPECTED_CHILD_PROTOCOL_OBLIGATIONS = tuple(
    sorted(
        (
            "request-and-fresh-query-frozen-before-launch",
            "three-cache-inputs-read-before-ground-access",
            "cached-failure-precedes-local-ground-recovery",
            "local-recovery-exhaustion-precedes-fallback",
            "route-and-solver-reconciliation-derived",
            *(f"stage-{index:02d}-owner-and-sequence-binding" for index in range(1, 4)),
        )
    )
)

SCIENCE_SUMMARY_KEYS = {
    "occurrence_id",
    "persistent_proof_cache_id",
    "recovery_eligible_checkpoint_id",
    "recovery_request_id",
    "native_accounting_id",
    "stage_accounting_result_id",
    "ground_transaction_id",
    "world_model_loop_id",
    "direct_ground_fallback_id",
    "terminal_class",
    "terminal_code",
    "route_attempts",
    "route_successes",
    "route_failures",
    "solver_attempts",
    "solver_successes",
    "solver_failures",
    "stage_instance_count",
    "stage_local_counter_record_count",
    "proof_node_reuse_count",
    "requested_frontier_row_count",
    "local_ground_draw_count",
    "changed_abstract_row_count",
    "fallback_states_expanded",
    "fallback_actions_evaluated",
    "fallback_ground_steps",
    "fallback_outcome_rows",
    "fallback_bellman_backups",
}
TRACE_KEYS = {
    "artifact_role",
    "schema",
    "schema_version",
    "profile_key",
    "supervised_request_id",
    "runtime_preparation_id",
    "runtime_tree_id",
    "science_summary",
    "recorded_stages",
    "business_hash_invocations",
    "child_integrity_obligations",
    "child_protocol_obligations",
    "child_self_peak_working_bytes_diagnostic",
    "hash_measurement_window_start",
    "hash_measurement_window_end",
    "accounting_provenance_hashes_excluded",
    "global_hashlib_sha256_constructor_hook_present",
    "full_planner_replayed_for_operational_validation",
    "standalone_verifier_work_included",
    "formal_occurrence_counter_records_issued_by_worker",
    "construction_only",
    "official_execution_allowed",
    "operational_trace_id",
}

_PREPARATION_ISSUER = object()
_EXECUTION_ISSUER = object()
_PARENT_HASH_LOCK = threading.Lock()


class ConstructionK7RecoveryEligibleSupervisedExecutorV1Error(RuntimeError):
    """The source closure, worker trace, or shared measurement diverged."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RecoveryEligibleSupervisedExecutorV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligibleSupervisedExecutorV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _source_inventory(source_root: Path) -> tuple[dict[str, bytes], dict[str, str]]:
    package = source_root / "src" / "acfqp"
    if package.is_symlink() or not package.is_dir():
        _fail("recovery source package is absent or linked")
    sources: dict[str, bytes] = {}
    paths: dict[str, str] = {}
    for path in sorted(package.rglob("*.py")):
        if path.is_symlink() or not path.is_file():
            _fail("recovery source inventory contains a linked/nonfile path")
        relative = path.relative_to(source_root / "src")
        parts = list(relative.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        module_name = ".".join(parts)
        raw = path.read_bytes()
        if not raw or module_name in sources:
            _fail("recovery source inventory is empty or duplicated")
        sources[module_name] = raw
        paths[module_name] = str(path)
    return sources, paths


@dataclass(frozen=True, slots=True)
class RecoveryEligibleRuntimePreparationV1:
    _issuer: InitVar[object]
    runtime_cas: RuntimeTreeCASV1 = field(repr=False, compare=False)
    manifest: RuntimeTreeManifestV1
    cap_profile: RuntimeManifestCapProfileV1
    source_closure: source_runtime.ConstructionSourceClosureV2
    _preparation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PREPARATION_ISSUER
            or type(self.runtime_cas) is not RuntimeTreeCASV1
            or type(self.manifest) is not RuntimeTreeManifestV1
            or type(self.cap_profile) is not RuntimeManifestCapProfileV1
            or self.cap_profile != OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE
            or type(self.source_closure)
            is not source_runtime.ConstructionSourceClosureV2
            or not set(PRIMARY_RUNTIME_ROOT_MODULES)
            <= set(self.source_closure.root_modules)
            or any(
                value not in PRIMARY_RUNTIME_ROOT_MODULES
                and not value.startswith(RUNTIME_DYNAMIC_ROOT_PREFIX)
                for value in self.source_closure.root_modules
            )
            or not any(
                value.startswith(RUNTIME_DYNAMIC_ROOT_PREFIX)
                for value in self.source_closure.root_modules
            )
            or tuple(row.relative_path for row in self.manifest.entries)
            != tuple(row.relative_path for row in self.source_closure.modules)
        ):
            _fail("recovery runtime preparation changed")
        object.__setattr__(
            self,
            "_preparation_id",
            content_id(PREPARATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_runtime_preparation.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_closure": self.source_closure.to_document(),
            "runtime_manifest": self.manifest.to_dict(),
            "runtime_manifest_cap_profile": self.cap_profile.to_dict(),
            "runtime_entrypoint": RUNTIME_ENTRYPOINT,
            "private_runtime_lease_required": True,
            "runtime_tree_build_charged_to_occurrence": False,
            "construction_only": True,
            "official_execution_allowed": False,
        }

    @property
    def preparation_id(self) -> str:
        current = content_id(PREPARATION_DOMAIN, self._payload())
        if current != self._preparation_id:
            _fail("recovery runtime preparation changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "recovery_eligible_runtime_preparation_id": self.preparation_id,
        }


def prepare_recovery_eligible_accounted_runtime_v1(
    *, repository_root: str | Path, runtime_cas_root: str | Path
) -> RecoveryEligibleRuntimePreparationV1:
    source_root = Path(repository_root).resolve(strict=True)
    sources, paths = _source_inventory(source_root)
    dynamic_roots = tuple(
        sorted(name for name in sources if name.startswith(RUNTIME_DYNAMIC_ROOT_PREFIX))
    )
    roots = tuple(sorted((*PRIMARY_RUNTIME_ROOT_MODULES, *dynamic_roots)))
    closure = source_runtime.build_construction_source_closure_v2(
        root_modules=roots,
        module_sources=sources,
        module_paths=paths,
    )
    cas = RuntimeTreeCASV1(Path(runtime_cas_root).resolve())
    with tempfile.TemporaryDirectory(prefix="acfqp-k7-recovery-runtime-build-") as temporary:
        build = Path(temporary)
        for row in closure.modules:
            target = build / row.relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(paths[row.module_name]), target)
            target.chmod(0o444)
        manifest = cas.snapshot_build_tree(build)
    resolved = cas.resolve(
        manifest.runtime_tree_id,
        cap_profile=OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE,
    )
    if resolved.manifest != manifest:
        _fail("recovery runtime CAS replay changed")
    return RecoveryEligibleRuntimePreparationV1(
        _PREPARATION_ISSUER,
        cas,
        manifest,
        OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE,
        closure,
    )


class _ParentHashMeterV1:
    def __init__(self) -> None:
        self.count = 0
        self._original: Any = None
        self._installed: Any = None

    def __enter__(self) -> "_ParentHashMeterV1":
        if not _PARENT_HASH_LOCK.acquire(blocking=False):
            _fail("another recovery parent hash window is active")
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
            _fail("recovery parent hash meter binding changed")


@dataclass(slots=True)
class _NamedParentObligationsV1:
    integrity: list[str] = field(default_factory=list)
    protocol: list[str] = field(default_factory=list)

    def integrity_checked(self, name: str) -> None:
        if name not in PARENT_INTEGRITY_OBLIGATIONS or name in self.integrity:
            _fail("parent integrity obligation is invalid or duplicated")
        self.integrity.append(name)

    def protocol_checked(self, name: str) -> None:
        if name not in PARENT_PROTOCOL_OBLIGATIONS or name in self.protocol:
            _fail("parent protocol obligation is invalid or duplicated")
        self.protocol.append(name)

    def close(self) -> None:
        if (
            tuple(self.integrity) != PARENT_INTEGRITY_OBLIGATIONS
            or tuple(self.protocol) != PARENT_PROTOCOL_OBLIGATIONS
        ):
            _fail("recovery parent obligation window did not close exactly")


@dataclass(frozen=True, slots=True)
class _ChildWait4ObservationV1:
    returncode: int
    peak_working_bytes: int

    def __post_init__(self) -> None:
        if (
            type(self.returncode) is not int
            or type(self.peak_working_bytes) is not int
            or self.peak_working_bytes <= 0
        ):
            _fail("recovery child wait observation is malformed")


def _wait4_child(
    process: subprocess.Popen[bytes], *, timeout_seconds: int
) -> _ChildWait4ObservationV1:
    if not sys.platform.startswith("linux") or not hasattr(os, "wait4"):
        _fail("recovery supervisor requires Linux wait4")
    deadline = time.monotonic() + timeout_seconds
    while True:
        waited_pid, status, usage = os.wait4(process.pid, os.WNOHANG)
        if waited_pid == process.pid:
            break
        if time.monotonic() >= deadline:
            process.send_signal(signal.SIGKILL)
            os.wait4(process.pid, 0)
            process.returncode = -signal.SIGKILL
            _fail("recovery worker timed out")
        time.sleep(0.01)
    returncode = os.waitstatus_to_exitcode(status)
    process.returncode = returncode
    return _ChildWait4ObservationV1(returncode, int(usage.ru_maxrss) * 1024)


@dataclass(frozen=True, slots=True)
class RecoveryEligiblePreOutputMeasurementV1:
    preparation_id: str
    runtime_tree_id: str
    source_closure_id: str
    request_id: str
    operational_trace_id: str
    occurrence_id: str
    native_accounting_id: str
    stage_accounting_result_id: str
    runtime_file_count: int
    runtime_total_bytes: int
    runtime_manifest_document_bytes: int
    input_file_count: int
    input_total_bytes: int
    request_bytes: int
    operational_trace_bytes: int
    child_wait4_peak_bytes: int
    parent_hash_invocations: int
    child_hash_invocations: int
    parent_integrity_obligations: tuple[str, ...]
    child_integrity_obligations: tuple[str, ...]
    parent_protocol_obligations: tuple[str, ...]
    child_protocol_obligations: tuple[str, ...]
    _measurement_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.preparation_id, "preparation"),
            (self.runtime_tree_id, "runtime tree"),
            (self.source_closure_id, "source closure"),
            (self.request_id, "request"),
            (self.operational_trace_id, "operational trace"),
            (self.occurrence_id, "occurrence"),
            (self.native_accounting_id, "native accounting"),
            (self.stage_accounting_result_id, "stage accounting"),
        ):
            _cid(value, label)
        numeric = (
            self.runtime_file_count,
            self.runtime_total_bytes,
            self.runtime_manifest_document_bytes,
            self.input_file_count,
            self.input_total_bytes,
            self.request_bytes,
            self.operational_trace_bytes,
            self.child_wait4_peak_bytes,
            self.parent_hash_invocations,
            self.child_hash_invocations,
        )
        if any(type(value) is not int or value <= 0 for value in numeric):
            _fail("recovery pre-output evidence must be positive")
        if (
            self.input_file_count != len(INPUT_ROLES)
            or self.parent_integrity_obligations != PARENT_INTEGRITY_OBLIGATIONS
            or self.child_integrity_obligations != EXPECTED_CHILD_INTEGRITY_OBLIGATIONS
            or self.parent_protocol_obligations != PARENT_PROTOCOL_OBLIGATIONS
            or self.child_protocol_obligations != EXPECTED_CHILD_PROTOCOL_OBLIGATIONS
        ):
            _fail("recovery named-obligation inventory changed")
        object.__setattr__(
            self,
            "_measurement_id",
            content_id(MEASUREMENT_DOMAIN, self._payload()),
        )

    @property
    def fixed_values(self) -> Mapping[str, int]:
        return MappingProxyType(
            {
                "common.hash_invocations": (
                    self.parent_hash_invocations + self.child_hash_invocations
                ),
                "common.integrity_checks": (
                    len(self.parent_integrity_obligations)
                    + len(self.child_integrity_obligations)
                ),
                "common.protocol_checks": (
                    len(self.parent_protocol_obligations)
                    + len(self.child_protocol_obligations)
                ),
                "io.read_bytes": (
                    self.runtime_manifest_document_bytes
                    + (
                        RUNTIME_FACTORY_TREE_PASSES
                        + RUNTIME_IMPORT_READ_PASSES_UPPER
                    )
                    * self.runtime_total_bytes
                    + self.request_bytes
                    + self.input_total_bytes
                    + self.operational_trace_bytes
                ),
                "io.staged_bytes": (
                    self.runtime_total_bytes
                    + self.request_bytes
                    + self.input_total_bytes
                ),
                "memory.working_bytes_peak": self.child_wait4_peak_bytes,
                "process.launches": 1,
            }
        )

    @property
    def pre_output_mounted_bytes_peak(self) -> int:
        return (
            self.runtime_total_bytes
            + self.request_bytes
            + self.input_total_bytes
            + self.operational_trace_bytes
        )

    def mounted_bytes_peak(self, output_bytes: int) -> int:
        if type(output_bytes) is not int or output_bytes < 0:
            _fail("recovery output candidate is invalid")
        return max(self.pre_output_mounted_bytes_peak, output_bytes)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_shared_measurement.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "runtime_preparation_id": self.preparation_id,
            "runtime_tree_id": self.runtime_tree_id,
            "source_closure_id": self.source_closure_id,
            "supervised_request_id": self.request_id,
            "operational_trace_id": self.operational_trace_id,
            "occurrence_id": self.occurrence_id,
            "native_accounting_id": self.native_accounting_id,
            "stage_accounting_result_id": self.stage_accounting_result_id,
            "runtime_file_count": self.runtime_file_count,
            "runtime_total_bytes": self.runtime_total_bytes,
            "runtime_manifest_document_bytes": self.runtime_manifest_document_bytes,
            "input_file_count": self.input_file_count,
            "input_total_bytes": self.input_total_bytes,
            "request_bytes": self.request_bytes,
            "operational_trace_bytes": self.operational_trace_bytes,
            "child_wait4_peak_bytes": self.child_wait4_peak_bytes,
            "parent_hash_invocations": self.parent_hash_invocations,
            "child_hash_invocations": self.child_hash_invocations,
            "parent_integrity_obligations": list(self.parent_integrity_obligations),
            "child_integrity_obligations": list(self.child_integrity_obligations),
            "parent_protocol_obligations": list(self.parent_protocol_obligations),
            "child_protocol_obligations": list(self.child_protocol_obligations),
            "fixed_pre_output_values": [
                {"path": path, "value": value}
                for path, value in sorted(self.fixed_values.items())
            ],
            "pre_output_mounted_bytes_peak": self.pre_output_mounted_bytes_peak,
            "mounted_peak_final_formula": "max(pre_output_peak,io.output_bytes)",
            "output_counter_record_pending_fixed_point_and_commit": True,
            "process_exit_successes": 1,
            "process_exit_failures": 0,
            "read_value_kind": "VERIFIED_UPPER_BOUND_SEALED_RUNTIME_INPUTS_AND_TRACE",
            "staged_value_kind": "EXACT_PRIVATE_LEASE_REQUEST_AND_INPUT_BYTES",
            "working_value_kind": "TRUSTED_PARENT_WAIT4_PEAK",
            "construction_only": True,
            "formal_counter_records_issued_here": False,
            "official_execution_allowed": False,
        }

    @property
    def measurement_id(self) -> str:
        current = content_id(MEASUREMENT_DOMAIN, self._payload())
        if current != self._measurement_id:
            _fail("recovery pre-output measurement changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "shared_measurement_id": self.measurement_id}


@dataclass(frozen=True, slots=True)
class SupervisedRecoveryEligibleExecutionV1:
    _issuer: InitVar[object]
    preparation: RecoveryEligibleRuntimePreparationV1 = field(
        repr=False, compare=False
    )
    request_document: Mapping[str, Any] = field(repr=False, compare=False)
    trace_raw: bytes = field(repr=False, compare=False)
    trace_document: Mapping[str, Any] = field(repr=False, compare=False)
    science_summary: Mapping[str, Any] = field(repr=False, compare=False)
    recorded_stages: tuple[live_v3.RecordedStageWorkV3, ...] = field(
        repr=False, compare=False
    )
    measurement: RecoveryEligiblePreOutputMeasurementV1

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _EXECUTION_ISSUER
            or type(self.preparation) is not RecoveryEligibleRuntimePreparationV1
            or type(self.request_document) is not MappingProxyType
            or type(self.trace_raw) is not bytes
            or type(self.trace_document) is not MappingProxyType
            or type(self.science_summary) is not MappingProxyType
            or type(self.recorded_stages) is not tuple
            or len(self.recorded_stages) != 3
            or type(self.measurement) is not RecoveryEligiblePreOutputMeasurementV1
            or canonical_json_bytes(dict(self.trace_document)) != self.trace_raw
            or self.request_document["supervised_request_id"]
            != self.measurement.request_id
            or self.trace_document["operational_trace_id"]
            != self.measurement.operational_trace_id
            or self.science_summary["occurrence_id"] != self.measurement.occurrence_id
        ):
            _fail("supervised recovery execution is caller-minted or crossed")

    @property
    def execution_id(self) -> str:
        return self.measurement.measurement_id

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_supervised_execution.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "runtime_preparation_id": self.preparation.preparation_id,
            "supervised_request_id": self.measurement.request_id,
            "operational_trace_id": self.measurement.operational_trace_id,
            "shared_measurement": self.measurement.to_document(),
            "occurrence_id": self.measurement.occurrence_id,
            "native_accounting_id": self.measurement.native_accounting_id,
            "stage_accounting_result_id": self.measurement.stage_accounting_result_id,
            "stage_instance_count": len(self.recorded_stages),
            "stage_local_counter_record_count": sum(
                len(row.work_vector.records) for row in self.recorded_stages
            ),
            "eight_pre_output_shared_paths_owner_correct": True,
            "io_output_bytes_pending_fixed_point_and_commit": True,
            "occurrence_work_vector_issued": False,
            "construction_only": True,
            "official_execution_allowed": False,
            "supervised_execution_id": self.execution_id,
        }


def _input_inventory(input_bytes: Mapping[str, bytes]) -> list[dict[str, Any]]:
    if set(input_bytes) != {role for role, _filename in INPUT_ROLES}:
        _fail("recovery input role set changed")
    rows = []
    for role, filename in INPUT_ROLES:
        raw = input_bytes[role]
        if type(raw) is not bytes or not raw:
            _fail("recovery input bytes are absent")
        document = loads_canonical_json(raw)
        if type(document) is not dict or canonical_json_bytes(document) != raw:
            _fail("recovery input is not canonical JSON")
        rows.append(
            {
                "role": role,
                "filename": filename,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return rows


def _request_document(
    preparation: RecoveryEligibleRuntimePreparationV1,
    *,
    input_bytes: Mapping[str, bytes],
    logical_occurrence_id: str,
    query_ordinal: int,
) -> dict[str, Any]:
    occurrence = _cid(logical_occurrence_id, "fresh logical occurrence")
    if type(query_ordinal) is not int or query_ordinal <= 1:
        _fail("recovery query ordinal must be greater than one")
    payload = {
        "schema": "acfqp.construction_k7_recovery_eligible_supervised_request.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "runtime_preparation_id": preparation.preparation_id,
        "runtime_tree_id": preparation.manifest.runtime_tree_id,
        "input_inventory": _input_inventory(input_bytes),
        "logical_occurrence_id": occurrence,
        "query_ordinal": query_ordinal,
        "checkpoint_replayed_before_ground_access": True,
        "construction_only": True,
        "official_execution_allowed": False,
    }
    return {**payload, "supervised_request_id": content_id(REQUEST_DOMAIN, payload)}


def execute_recovery_eligible_accounted_v1(
    preparation: RecoveryEligibleRuntimePreparationV1,
    *,
    binding_bytes: bytes,
    snapshot_bytes: bytes,
    transition_bytes: bytes,
    logical_occurrence_id: str,
    query_ordinal: int,
    trace_output_path: str | Path,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> SupervisedRecoveryEligibleExecutionV1:
    if type(preparation) is not RecoveryEligibleRuntimePreparationV1:
        _fail("recovery execution requires exact preparation")
    preparation.__post_init__(_PREPARATION_ISSUER)
    if type(timeout_seconds) is not int or not (0 < timeout_seconds <= 7_200):
        _fail("recovery timeout is outside its finite profile")
    trace_path = Path(trace_output_path).resolve()
    if trace_path.exists() or trace_path.parent.is_symlink() or not trace_path.parent.is_dir():
        _fail("recovery trace target must be absent under one real directory")
    input_bytes = MappingProxyType(
        {
            "SOURCE_BUNDLE_BINDING": binding_bytes,
            "REUSABLE_RAPM_SNAPSHOT": snapshot_bytes,
            "PROOF_DEPENDENCY_TRANSITION": transition_bytes,
        }
    )

    obligations = _NamedParentObligationsV1()
    parent_meter = _ParentHashMeterV1()
    with parent_meter:
        preparation.__post_init__(_PREPARATION_ISSUER)
        obligations.integrity_checked("runtime-preparation-replayed")
        request_document = _request_document(
            preparation,
            input_bytes=input_bytes,
            logical_occurrence_id=logical_occurrence_id,
            query_ordinal=query_ordinal,
        )
        request_raw = canonical_json_bytes(request_document)
        obligations.protocol_checked("fresh-query-frozen-before-launch")
        obligations.integrity_checked("three-input-canonical-digests-replayed")
        obligations.protocol_checked("checkpoint-before-ground-enforced")
        resolved = preparation.runtime_cas.resolve(
            preparation.manifest.runtime_tree_id,
            cap_profile=preparation.cap_profile,
        )
        if resolved.manifest != preparation.manifest:
            _fail("runtime CAS resolved another recovery manifest")
        obligations.integrity_checked("runtime-cas-resolved")

        with resolved.open_private_lease() as lease:
            obligations.integrity_checked("private-runtime-lease-replayed")
            entrypoint = lease.root / RUNTIME_ENTRYPOINT
            if entrypoint.is_symlink() or not entrypoint.is_file():
                _fail("recovery worker entrypoint is absent")
            with tempfile.TemporaryDirectory(prefix="acfqp-k7-recovery-execution-") as temporary:
                sandbox = Path(temporary)
                inputs_root = sandbox / "inputs"
                inputs_root.mkdir(mode=0o700)
                request_path = sandbox / "request.json"
                stdout_path = sandbox / "stdout.bin"
                stderr_path = sandbox / "stderr.bin"
                request_path.write_bytes(request_raw)
                for role, filename in INPUT_ROLES:
                    (inputs_root / filename).write_bytes(input_bytes[role])
                argv = (
                    sys.executable,
                    "-I",
                    "-B",
                    str(entrypoint),
                    "--runtime-source",
                    str(lease.root),
                    "--request",
                    str(request_path),
                    "--inputs-root",
                    str(inputs_root),
                    "--trace-output",
                    str(trace_path),
                )
                obligations.protocol_checked("fresh-python-I-argv-executed")
                with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
                    process = subprocess.Popen(
                        argv,
                        cwd=sandbox,
                        env={
                            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                            "LANG": "C.UTF-8",
                            "LC_ALL": "C.UTF-8",
                            "PYTHONHASHSEED": "0",
                            "PYTHONDONTWRITEBYTECODE": "1",
                            "TZ": "UTC",
                        },
                        stdin=subprocess.DEVNULL,
                        stdout=stdout,
                        stderr=stderr,
                        close_fds=True,
                    )
                    obligations.protocol_checked("single-process-launch-observed")
                    wait = _wait4_child(process, timeout_seconds=timeout_seconds)
                obligations.integrity_checked("child-completion-observed")
                if wait.returncode != 0:
                    diagnostic = stderr_path.read_bytes()[-8_192:].decode(
                        "utf-8", errors="replace"
                    )
                    _fail(
                        "recovery child exited nonzero: "
                        f"{wait.returncode}: {diagnostic}"
                    )
                if (
                    stdout_path.read_bytes()
                    or stderr_path.read_bytes()
                    or not trace_path.is_file()
                    or trace_path.is_symlink()
                ):
                    _fail("recovery worker was noisy or omitted its trace")
                obligations.protocol_checked("quiet-stdout-stderr-enforced")
                trace_raw = trace_path.read_bytes()
                if not trace_raw or len(trace_raw) > MAX_TRACE_BYTES:
                    _fail("recovery operational trace is empty or oversized")
                trace_document = loads_canonical_json(trace_raw)
                if type(trace_document) is not dict or canonical_json_bytes(trace_document) != trace_raw:
                    _fail("recovery trace is not canonical")
                require_exact_fields(
                    trace_document,
                    TRACE_KEYS,
                    context="recovery operational trace",
                )
                if (
                    trace_document["artifact_role"] != "OPERATIONAL_TRACE"
                    or trace_document["schema"]
                    != "acfqp.construction_k7_recovery_eligible_operational_trace.v1"
                    or trace_document["schema_version"] != SCHEMA_VERSION
                    or trace_document["profile_key"]
                    != "construction_k7_recovery_eligible_accounted_runtime_v1"
                    or trace_document["supervised_request_id"]
                    != request_document["supervised_request_id"]
                    or trace_document["runtime_preparation_id"]
                    != preparation.preparation_id
                    or trace_document["runtime_tree_id"]
                    != preparation.manifest.runtime_tree_id
                    or trace_document["hash_measurement_window_start"]
                    != "AFTER_RUNTIME_INFRASTRUCTURE_IMPORTS"
                    or trace_document["hash_measurement_window_end"]
                    != "AFTER_STAGE_AND_TERMINAL_REPLAY_BEFORE_TRACE_PROVENANCE"
                    or trace_document["accounting_provenance_hashes_excluded"] is not True
                    or trace_document["global_hashlib_sha256_constructor_hook_present"] is not True
                    or trace_document["full_planner_replayed_for_operational_validation"] is not False
                    or trace_document["standalone_verifier_work_included"] is not False
                    or trace_document["formal_occurrence_counter_records_issued_by_worker"] is not False
                    or trace_document["construction_only"] is not True
                    or trace_document["official_execution_allowed"] is not False
                ):
                    _fail("recovery operational trace contract changed")
                trace_payload = dict(trace_document)
                trace_id = trace_payload.pop("operational_trace_id")
                if trace_id != content_id(TRACE_DOMAIN, trace_payload):
                    _fail("recovery operational trace ID mismatch")
                obligations.integrity_checked("trace-canonical-and-content-id-replayed")
                obligations.protocol_checked("worker-trace-schema-enforced")

                if (
                    trace_document["child_integrity_obligations"]
                    != list(EXPECTED_CHILD_INTEGRITY_OBLIGATIONS)
                    or trace_document["child_protocol_obligations"]
                    != list(EXPECTED_CHILD_PROTOCOL_OBLIGATIONS)
                    or type(trace_document["business_hash_invocations"]) is not int
                    or trace_document["business_hash_invocations"] <= 0
                    or type(trace_document["recorded_stages"]) is not list
                    or len(trace_document["recorded_stages"]) != 3
                ):
                    _fail("recovery child evidence inventory changed")

                registry = registry_v6.official_counter_registry_v6()
                stage_profile = registry_v6.official_stage_profile_v6(registry)
                comparison = registry_v6.official_comparison_profile_v6(registry)
                actual = registry_v6.official_actual_projection_profile_v6(
                    registry, comparison
                )
                recorded_stages = tuple(
                    live_v3.RecordedStageWorkV3.from_document(
                        document,
                        registry,
                        stage_profile,
                        comparison,
                        actual,
                    )
                    for document in trace_document["recorded_stages"]
                )
                if tuple(
                    registry_v6.ConstructionStageKindV6(
                        row.stage_start.stage_kind.value
                    )
                    for row in recorded_stages
                ) != stage_v1.CANONICAL_STAGE_PLAN_V1:
                    _fail("portable recovery stage order changed")
                obligations.integrity_checked("three-stage-event-chains-replayed")
                obligations.protocol_checked("stage-order-and-owner-chain-enforced")

                science = trace_document["science_summary"]
                if type(science) is not dict or set(science) != SCIENCE_SUMMARY_KEYS:
                    _fail("recovery science summary field set changed")
                for key in (
                    "occurrence_id",
                    "persistent_proof_cache_id",
                    "recovery_eligible_checkpoint_id",
                    "recovery_request_id",
                    "native_accounting_id",
                    "stage_accounting_result_id",
                    "ground_transaction_id",
                    "world_model_loop_id",
                    "direct_ground_fallback_id",
                ):
                    _cid(science[key], f"science summary {key}")
                if (
                    science["occurrence_id"] != logical_occurrence_id
                    or science["terminal_class"] != "PLAN_CERTIFICATE"
                    or science["terminal_code"] != "FULL_GROUND_FALLBACK"
                    or (
                        science["route_attempts"],
                        science["route_successes"],
                        science["route_failures"],
                    )
                    != (1, 1, 0)
                    or (
                        science["solver_attempts"],
                        science["solver_successes"],
                        science["solver_failures"],
                    )
                    != (1, 1, 0)
                    or science["stage_instance_count"] != 3
                    or science["stage_local_counter_record_count"] != 606
                    or science["proof_node_reuse_count"] != 41
                    or science["requested_frontier_row_count"] != 6
                    or science["local_ground_draw_count"] != 12_672
                    or science["changed_abstract_row_count"] != 6
                    or (
                        science["fallback_states_expanded"],
                        science["fallback_actions_evaluated"],
                        science["fallback_ground_steps"],
                        science["fallback_outcome_rows"],
                        science["fallback_bellman_backups"],
                    )
                    != (30, 96, 96, 1_440, 102)
                ):
                    _fail("recovery science or route facts changed")
                obligations.integrity_checked("science-summary-identity-chain-replayed")
                obligations.protocol_checked("terminal-route-reconciliation-enforced")
                obligations.integrity_checked("resource-formulas-reconciled")
                obligations.protocol_checked("operational-cutoff-precedes-accounting-provenance")
                obligations.close()

    if parent_meter.count <= 0:
        _fail("recovery parent hash window produced no observation")
    measurement = RecoveryEligiblePreOutputMeasurementV1(
        preparation.preparation_id,
        preparation.manifest.runtime_tree_id,
        preparation.source_closure.closure_id,
        request_document["supervised_request_id"],
        trace_document["operational_trace_id"],
        science["occurrence_id"],
        science["native_accounting_id"],
        science["stage_accounting_result_id"],
        preparation.manifest.file_count,
        preparation.manifest.total_bytes,
        preparation.manifest.manifest_document_bytes,
        len(INPUT_ROLES),
        sum(len(raw) for raw in input_bytes.values()),
        len(request_raw),
        len(trace_raw),
        wait.peak_working_bytes,
        parent_meter.count,
        trace_document["business_hash_invocations"],
        tuple(obligations.integrity),
        tuple(trace_document["child_integrity_obligations"]),
        tuple(obligations.protocol),
        tuple(trace_document["child_protocol_obligations"]),
    )
    return SupervisedRecoveryEligibleExecutionV1(
        _EXECUTION_ISSUER,
        preparation,
        MappingProxyType(dict(request_document)),
        trace_raw,
        MappingProxyType(dict(trace_document)),
        MappingProxyType(dict(science)),
        recorded_stages,
        measurement,
    )


def require_supervised_recovery_eligible_execution_v1(
    claimed: SupervisedRecoveryEligibleExecutionV1,
) -> SupervisedRecoveryEligibleExecutionV1:
    if type(claimed) is not SupervisedRecoveryEligibleExecutionV1:
        _fail("supervised recovery execution has a foreign type")
    claimed.__post_init__(_EXECUTION_ISSUER)
    return claimed


__all__ = (
    "ConstructionK7RecoveryEligibleSupervisedExecutorV1Error",
    "DEFAULT_TIMEOUT_SECONDS",
    "EXPECTED_CHILD_INTEGRITY_OBLIGATIONS",
    "EXPECTED_CHILD_PROTOCOL_OBLIGATIONS",
    "INPUT_ROLES",
    "LOCAL_DOMAINS",
    "PARENT_INTEGRITY_OBLIGATIONS",
    "PARENT_PROTOCOL_OBLIGATIONS",
    "PRE_OUTPUT_SHARED_PATHS",
    "RecoveryEligiblePreOutputMeasurementV1",
    "RecoveryEligibleRuntimePreparationV1",
    "SupervisedRecoveryEligibleExecutionV1",
    "execute_recovery_eligible_accounted_v1",
    "prepare_recovery_eligible_accounted_runtime_v1",
    "require_supervised_recovery_eligible_execution_v1",
)
