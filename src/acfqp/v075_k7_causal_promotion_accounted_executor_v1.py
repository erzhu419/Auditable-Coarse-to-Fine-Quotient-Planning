"""Trusted supervisor for the K7 causal-promotion construction occurrence.

The preparation phase derives an exact recursive ACFQP source closure and
snapshots it into the existing immutable runtime CAS.  One invocation then
launches exactly one fresh ``python -I`` worker, observes its terminal status
and peak through ``wait4``, meters parent/child business SHA-256 constructors,
replays every portable stage event chain, and retains owner-correct evidence
for the eight pre-output shared-resource paths.

``io.output_bytes`` and the final mounted peak remain pending until the eight
operational artifact roles reach their deterministic fixed point and are
committed by the occurrence finalizer.  This module issues no occurrence
CounterRecord or official/campaign authority by itself.
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
from acfqp import construction_accounting_owned_runtime_v2 as owned_v2
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import v075_k7_causal_promotion_terminal_authority_v1 as terminal_v1
from acfqp.phase3e_ids import (
    V075_K7_CAUSAL_PROMOTION_OPERATIONAL_TRACE_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_RUNTIME_PREPARATION_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_SHARED_MEASUREMENT_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_SUPERVISED_REQUEST_V1_DOMAIN,
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
TRACE_SCHEMA_VERSION = "2.0.0"
PROFILE_KEY = "v075_k7_causal_promotion_accounted_executor_v1"
RUNTIME_ROOT_MODULES = (
    "acfqp.v075_k7_causal_promotion_accounted_runtime_v1",
)
RUNTIME_ENTRYPOINT = "acfqp/v075_k7_causal_promotion_accounted_runtime_v1.py"
RUNTIME_IMPORT_READ_PASSES_UPPER = 2
DEFAULT_TIMEOUT_SECONDS = 3_600
MAX_TRACE_BYTES = 64 * 1024 * 1024

PREPARATION_DOMAIN = (
    V075_K7_CAUSAL_PROMOTION_RUNTIME_PREPARATION_V1_DOMAIN
)
REQUEST_DOMAIN = V075_K7_CAUSAL_PROMOTION_SUPERVISED_REQUEST_V1_DOMAIN
TRACE_DOMAIN = V075_K7_CAUSAL_PROMOTION_OPERATIONAL_TRACE_V1_DOMAIN
MEASUREMENT_DOMAIN = V075_K7_CAUSAL_PROMOTION_SHARED_MEASUREMENT_V1_DOMAIN

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
    "runtime-cas-resolved",
    "private-runtime-lease-replayed",
    "child-completion-observed",
    "trace-canonical-and-content-id-replayed",
    "twelve-stage-event-chains-replayed",
    "science-summary-identity-chain-replayed",
    "resource-formulas-reconciled",
)
PARENT_PROTOCOL_OBLIGATIONS = (
    "request-identity-frozen-before-launch",
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
            "terminal-identity-chain-replayed",
            "budget-closure-semantic-verification-consumed",
            "twelve-stage-inventory-replayed",
            "science-summary-derived-from-live-result",
            *(
                f"stage-{index:02d}-event-to-vector-replay"
                for index in range(1, 13)
            ),
        )
    )
)
EXPECTED_CHILD_PROTOCOL_OBLIGATIONS = tuple(
    sorted(
        (
            "request-construction-only-profile-bound",
            "budget-exhaustion-route-outcome-replayed",
            "construction-terminal-mapping-prerequisites-frozen",
            "route-and-solver-reconciliation-derived",
            *(
                f"stage-{index:02d}-owner-and-sequence-binding"
                for index in range(1, 13)
            ),
        )
    )
)

_PREPARATION_ISSUER = object()
_EXECUTION_ISSUER = object()
_PARENT_HASH_LOCK = threading.Lock()


class V075K7CausalPromotionAccountedExecutorV1Error(RuntimeError):
    """The source closure, worker, resource evidence, or replay failed."""


def _fail(message: str) -> NoReturn:
    raise V075K7CausalPromotionAccountedExecutorV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075K7CausalPromotionAccountedExecutorV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _source_inventory(
    source_root: Path,
) -> tuple[dict[str, bytes], dict[str, str]]:
    package = source_root / "src" / "acfqp"
    if package.is_symlink() or not package.is_dir():
        _fail("causal-promotion source package is absent or linked")
    sources: dict[str, bytes] = {}
    paths: dict[str, str] = {}
    for path in sorted(package.rglob("*.py")):
        if path.is_symlink() or not path.is_file():
            _fail("causal-promotion source inventory contains a linked/nonfile path")
        relative = path.relative_to(source_root / "src")
        parts = list(relative.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        module_name = ".".join(parts)
        raw = path.read_bytes()
        if not raw or module_name in sources:
            _fail("causal-promotion source inventory is empty or duplicated")
        sources[module_name] = raw
        paths[module_name] = str(path)
    return sources, paths


@dataclass(frozen=True, slots=True)
class CausalPromotionRuntimePreparationV1:
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
            or self.source_closure.root_modules != RUNTIME_ROOT_MODULES
            or tuple(row.relative_path for row in self.manifest.entries)
            != tuple(row.relative_path for row in self.source_closure.modules)
        ):
            _fail("causal-promotion runtime preparation changed")
        object.__setattr__(
            self,
            "_preparation_id",
            content_id(PREPARATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_causal_promotion_runtime_preparation.v1",
            "schema_version": SCHEMA_VERSION,
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
        expected = content_id(PREPARATION_DOMAIN, self._payload())
        if expected != self._preparation_id:
            _fail("causal-promotion runtime preparation changed after issuance")
        return self._preparation_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "causal_promotion_runtime_preparation_id": self.preparation_id,
        }


def prepare_v075_k7_causal_promotion_accounted_runtime_v1(
    *,
    repository_root: str | Path,
    runtime_cas_root: str | Path,
) -> CausalPromotionRuntimePreparationV1:
    """Derive and snapshot the exact recursive worker source closure."""

    source_root = Path(repository_root).resolve(strict=True)
    sources, paths = _source_inventory(source_root)
    closure = source_runtime.build_construction_source_closure_v2(
        root_modules=RUNTIME_ROOT_MODULES,
        module_sources=sources,
        module_paths=paths,
    )
    cas = RuntimeTreeCASV1(Path(runtime_cas_root).resolve())
    with tempfile.TemporaryDirectory(
        prefix="acfqp-k7-causal-promotion-runtime-build-"
    ) as temporary:
        build = Path(temporary)
        for row in closure.modules:
            target = build / row.relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            source = Path(paths[row.module_name])
            shutil.copyfile(source, target)
            target.chmod(0o444)
        manifest = cas.snapshot_build_tree(build)
    resolved = cas.resolve(
        manifest.runtime_tree_id,
        cap_profile=OFFICIAL_RUNTIME_MANIFEST_CAP_PROFILE,
    )
    if resolved.manifest != manifest:
        _fail("causal-promotion runtime CAS replay changed")
    return CausalPromotionRuntimePreparationV1(
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
            _fail("another parent causal-promotion hash window is active")
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
            _fail("parent causal-promotion hash meter binding changed")


@dataclass(slots=True)
class _NamedParentObligationsV1:
    integrity: list[str] = field(default_factory=list)
    protocol: list[str] = field(default_factory=list)

    def checked_integrity(self, name: str) -> None:
        if name not in PARENT_INTEGRITY_OBLIGATIONS or name in self.integrity:
            _fail("parent integrity obligation is invalid or duplicated")
        self.integrity.append(name)

    def checked_protocol(self, name: str) -> None:
        if name not in PARENT_PROTOCOL_OBLIGATIONS or name in self.protocol:
            _fail("parent protocol obligation is invalid or duplicated")
        self.protocol.append(name)

    def close(self) -> None:
        if (
            tuple(self.integrity) != PARENT_INTEGRITY_OBLIGATIONS
            or tuple(self.protocol) != PARENT_PROTOCOL_OBLIGATIONS
        ):
            _fail("parent obligation window did not close exactly")


@dataclass(frozen=True, slots=True)
class _ChildWait4ObservationV1:
    returncode: int
    peak_working_bytes: int

    def __post_init__(self) -> None:
        if (
            type(self.returncode) is not int
            or self.returncode != 0
            or type(self.peak_working_bytes) is not int
            or self.peak_working_bytes <= 0
        ):
            _fail("causal-promotion child did not exit successfully with a peak")


def _wait4_child(
    process: subprocess.Popen[bytes],
    *,
    timeout_seconds: int,
) -> _ChildWait4ObservationV1:
    if not sys.platform.startswith("linux") or not hasattr(os, "wait4"):
        _fail("causal-promotion supervisor requires Linux wait4")
    deadline = time.monotonic() + timeout_seconds
    while True:
        waited_pid, status, usage = os.wait4(process.pid, os.WNOHANG)
        if waited_pid == process.pid:
            break
        if time.monotonic() >= deadline:
            process.send_signal(signal.SIGKILL)
            os.wait4(process.pid, 0)
            process.returncode = -signal.SIGKILL
            _fail("causal-promotion worker timed out")
        time.sleep(0.01)
    returncode = os.waitstatus_to_exitcode(status)
    process.returncode = returncode
    return _ChildWait4ObservationV1(
        returncode,
        int(usage.ru_maxrss) * 1024,
    )


SCIENCE_SUMMARY_KEYS = {
    "occurrence_id",
    "accounted_occurrence_id",
    "owned_accounting_result_id",
    "schedule_id",
    "schedule_verification_id",
    "root_execution_id",
    "root_model_epoch_id",
    "causal_child_authorization_id",
    "causal_child_execution_bundle_id",
    "causal_promotion_bundle_id",
    "budget_closure_id",
    "budget_closure_verification_id",
    "budget_replay_attestation_id",
    "terminal_class",
    "terminal_code",
    "route_attempts",
    "route_successes",
    "route_failures",
    "solver_attempts",
    "solver_successes",
    "solver_failures",
    "observer_closed_and_exactly_reconciled",
    "stage_instance_count",
    "stage_local_counter_record_count",
}


@dataclass(frozen=True, slots=True)
class CausalPromotionPreOutputMeasurementV1:
    preparation_id: str
    runtime_tree_id: str
    source_closure_id: str
    request_id: str
    operational_trace_id: str
    occurrence_id: str
    accounted_occurrence_id: str
    owned_accounting_result_id: str
    runtime_file_count: int
    runtime_total_bytes: int
    runtime_manifest_document_bytes: int
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
            (self.accounted_occurrence_id, "accounted occurrence"),
            (self.owned_accounting_result_id, "owned accounting result"),
        ):
            _cid(value, label)
        numeric = (
            self.runtime_file_count,
            self.runtime_total_bytes,
            self.runtime_manifest_document_bytes,
            self.request_bytes,
            self.operational_trace_bytes,
            self.child_wait4_peak_bytes,
            self.parent_hash_invocations,
            self.child_hash_invocations,
        )
        if any(type(value) is not int or value <= 0 for value in numeric):
            _fail("pre-output measurement numeric evidence must be positive")
        if (
            self.parent_integrity_obligations != PARENT_INTEGRITY_OBLIGATIONS
            or self.child_integrity_obligations
            != EXPECTED_CHILD_INTEGRITY_OBLIGATIONS
            or self.parent_protocol_obligations != PARENT_PROTOCOL_OBLIGATIONS
            or self.child_protocol_obligations
            != EXPECTED_CHILD_PROTOCOL_OBLIGATIONS
        ):
            _fail("pre-output named-obligation inventory changed")
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
                    + self.operational_trace_bytes
                ),
                "io.staged_bytes": self.runtime_total_bytes + self.request_bytes,
                "memory.working_bytes_peak": self.child_wait4_peak_bytes,
                "process.launches": 1,
            }
        )

    @property
    def pre_output_mounted_bytes_peak(self) -> int:
        return (
            self.runtime_total_bytes
            + self.request_bytes
            + self.operational_trace_bytes
        )

    def mounted_bytes_peak(self, output_bytes: int) -> int:
        if type(output_bytes) is not int or output_bytes < 0:
            _fail("output candidate for mounted peak is invalid")
        return max(self.pre_output_mounted_bytes_peak, output_bytes)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_causal_promotion_shared_measurement.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "runtime_preparation_id": self.preparation_id,
            "runtime_tree_id": self.runtime_tree_id,
            "source_closure_id": self.source_closure_id,
            "supervised_request_id": self.request_id,
            "operational_trace_id": self.operational_trace_id,
            "occurrence_id": self.occurrence_id,
            "accounted_occurrence_id": self.accounted_occurrence_id,
            "owned_accounting_result_id": self.owned_accounting_result_id,
            "runtime_file_count": self.runtime_file_count,
            "runtime_total_bytes": self.runtime_total_bytes,
            "runtime_manifest_document_bytes": self.runtime_manifest_document_bytes,
            "request_bytes": self.request_bytes,
            "operational_trace_bytes": self.operational_trace_bytes,
            "child_wait4_peak_bytes": self.child_wait4_peak_bytes,
            "parent_hash_invocations": self.parent_hash_invocations,
            "child_hash_invocations": self.child_hash_invocations,
            "parent_integrity_obligations": list(
                self.parent_integrity_obligations
            ),
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
            "read_value_kind": "VERIFIED_UPPER_BOUND_SEALED_RUNTIME_AND_TRACE",
            "staged_value_kind": "EXACT_PRIVATE_LEASE_AND_REQUEST_BYTES",
            "working_value_kind": "TRUSTED_PARENT_WAIT4_PEAK",
            "construction_only": True,
            "formal_counter_records_issued_here": False,
            "official_execution_allowed": False,
        }

    @property
    def measurement_id(self) -> str:
        expected = content_id(MEASUREMENT_DOMAIN, self._payload())
        if expected != self._measurement_id:
            _fail("pre-output measurement changed after issuance")
        return self._measurement_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "shared_measurement_id": self.measurement_id,
        }


@dataclass(frozen=True, slots=True)
class SupervisedCausalPromotionExecutionV1:
    _issuer: InitVar[object]
    preparation: CausalPromotionRuntimePreparationV1 = field(
        repr=False, compare=False
    )
    request_document: Mapping[str, Any] = field(repr=False, compare=False)
    trace_raw: bytes = field(repr=False, compare=False)
    trace_document: Mapping[str, Any] = field(repr=False, compare=False)
    science_summary: Mapping[str, Any] = field(repr=False, compare=False)
    recorded_stages: tuple[live_v3.RecordedStageWorkV3, ...] = field(
        repr=False, compare=False
    )
    measurement: CausalPromotionPreOutputMeasurementV1

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _EXECUTION_ISSUER
            or type(self.preparation) is not CausalPromotionRuntimePreparationV1
            or type(self.request_document) is not MappingProxyType
            or type(self.trace_raw) is not bytes
            or type(self.trace_document) is not MappingProxyType
            or type(self.science_summary) is not MappingProxyType
            or type(self.recorded_stages) is not tuple
            or len(self.recorded_stages) != 12
            or type(self.measurement) is not CausalPromotionPreOutputMeasurementV1
        ):
            _fail("supervised causal-promotion execution is caller-minted")
        if (
            canonical_json_bytes(dict(self.trace_document)) != self.trace_raw
            or self.request_document["supervised_request_id"]
            != self.measurement.request_id
            or self.trace_document["operational_trace_id"]
            != self.measurement.operational_trace_id
            or self.science_summary["occurrence_id"]
            != self.measurement.occurrence_id
        ):
            _fail("supervised causal-promotion execution identities crossed")

    @property
    def execution_id(self) -> str:
        return self.measurement.measurement_id

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_causal_promotion_supervised_execution.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "runtime_preparation_id": self.preparation.preparation_id,
            "supervised_request_id": self.measurement.request_id,
            "operational_trace_id": self.measurement.operational_trace_id,
            "shared_measurement": self.measurement.to_document(),
            "occurrence_id": self.measurement.occurrence_id,
            "accounted_occurrence_id": self.measurement.accounted_occurrence_id,
            "owned_accounting_result_id": (
                self.measurement.owned_accounting_result_id
            ),
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


def _request_document(
    preparation: CausalPromotionRuntimePreparationV1,
    *,
    marker: str,
) -> dict[str, Any]:
    if type(marker) is not str or not marker or len(marker.encode("utf-8")) > 128:
        _fail("causal-promotion construction marker is invalid")
    payload = {
        "schema": "acfqp.v075_k7_causal_promotion_supervised_request.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "runtime_preparation_id": preparation.preparation_id,
        "runtime_tree_id": preparation.manifest.runtime_tree_id,
        "construction_fixture_marker": marker,
        "construction_only": True,
        "fresh_heldout_accessed": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "supervised_request_id": content_id(REQUEST_DOMAIN, payload),
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
    "budget_replay_attestation",
    "recorded_stages",
    "business_hash_invocations",
    "child_integrity_obligations",
    "child_protocol_obligations",
    "child_self_peak_working_bytes_diagnostic",
    "hash_measurement_window_start",
    "hash_measurement_window_end",
    "accounting_provenance_hashes_excluded",
    "global_hashlib_sha256_constructor_hook_present",
    "construction_only",
    "fresh_heldout_accessed",
    "formal_counter_record_issued_by_worker",
    "occurrence_vector_issued_by_worker",
    "official_execution_allowed",
    "operational_trace_id",
}


def execute_v075_k7_causal_promotion_accounted_v1(
    preparation: CausalPromotionRuntimePreparationV1,
    *,
    trace_output_path: str | Path,
    construction_fixture_marker: str = "nonfresh-k7-causal-promotion",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> SupervisedCausalPromotionExecutionV1:
    """Execute, supervise, and replay one sealed construction occurrence."""

    if type(preparation) is not CausalPromotionRuntimePreparationV1:
        _fail("causal-promotion execution requires exact preparation")
    preparation.__post_init__(_PREPARATION_ISSUER)
    if type(timeout_seconds) is not int or not (0 < timeout_seconds <= 7_200):
        _fail("causal-promotion timeout is outside its finite profile")
    trace_path = Path(trace_output_path).resolve()
    if trace_path.exists() or trace_path.parent.is_symlink() or not trace_path.parent.is_dir():
        _fail("operational trace target must be absent under one real directory")

    obligations = _NamedParentObligationsV1()
    parent_meter = _ParentHashMeterV1()
    with parent_meter:
        preparation.__post_init__(_PREPARATION_ISSUER)
        obligations.checked_integrity("runtime-preparation-replayed")
        request_document = _request_document(
            preparation,
            marker=construction_fixture_marker,
        )
        request_raw = canonical_json_bytes(request_document)
        obligations.checked_protocol("request-identity-frozen-before-launch")
        resolved = preparation.runtime_cas.resolve(
            preparation.manifest.runtime_tree_id,
            cap_profile=preparation.cap_profile,
        )
        if resolved.manifest != preparation.manifest:
            _fail("runtime CAS resolved another causal-promotion manifest")
        obligations.checked_integrity("runtime-cas-resolved")

        with resolved.open_private_lease() as lease:
            obligations.checked_integrity("private-runtime-lease-replayed")
            entrypoint = lease.root / RUNTIME_ENTRYPOINT
            if entrypoint.is_symlink() or not entrypoint.is_file():
                _fail("causal-promotion worker entrypoint is absent")
            with tempfile.TemporaryDirectory(
                prefix="acfqp-k7-causal-promotion-execution-"
            ) as temporary:
                sandbox = Path(temporary)
                request_path = sandbox / "request.json"
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
                    "--trace-output",
                    str(trace_path),
                )
                obligations.checked_protocol("fresh-python-I-argv-executed")
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
                    obligations.checked_protocol("single-process-launch-observed")
                    wait = _wait4_child(
                        process,
                        timeout_seconds=timeout_seconds,
                    )
                obligations.checked_integrity("child-completion-observed")
                if (
                    stdout_path.read_bytes()
                    or stderr_path.read_bytes()
                    or not trace_path.is_file()
                    or trace_path.is_symlink()
                ):
                    _fail("causal-promotion worker was noisy or omitted its trace")
                obligations.checked_protocol("quiet-stdout-stderr-enforced")
                trace_raw = trace_path.read_bytes()
                if not trace_raw or len(trace_raw) > MAX_TRACE_BYTES:
                    _fail("causal-promotion operational trace is empty or oversized")
                trace_document = loads_canonical_json(trace_raw)
                if type(trace_document) is not dict or canonical_json_bytes(trace_document) != trace_raw:
                    _fail("causal-promotion trace is not canonical")
                require_exact_fields(
                    trace_document,
                    TRACE_KEYS,
                    context="causal-promotion operational trace",
                )
                if (
                    trace_document["artifact_role"] != "OPERATIONAL_TRACE"
                    or
                    trace_document["schema"]
                    != "acfqp.v075_k7_causal_promotion_operational_trace.v2"
                    or trace_document["schema_version"] != TRACE_SCHEMA_VERSION
                    or trace_document["profile_key"]
                    != "v075_k7_causal_promotion_accounted_runtime_v1"
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
                    or trace_document["construction_only"] is not True
                    or trace_document["fresh_heldout_accessed"] is not False
                    or trace_document["formal_counter_record_issued_by_worker"] is not False
                    or trace_document["occurrence_vector_issued_by_worker"] is not False
                    or trace_document["official_execution_allowed"] is not False
                ):
                    _fail("causal-promotion operational trace contract changed")
                trace_payload = dict(trace_document)
                observed_trace_id = trace_payload.pop("operational_trace_id")
                if observed_trace_id != content_id(TRACE_DOMAIN, trace_payload):
                    _fail("causal-promotion operational trace ID mismatch")
                obligations.checked_integrity("trace-canonical-and-content-id-replayed")
                obligations.checked_protocol("worker-trace-schema-enforced")

                if (
                    trace_document["child_integrity_obligations"]
                    != list(EXPECTED_CHILD_INTEGRITY_OBLIGATIONS)
                    or trace_document["child_protocol_obligations"]
                    != list(EXPECTED_CHILD_PROTOCOL_OBLIGATIONS)
                    or type(trace_document["business_hash_invocations"]) is not int
                    or trace_document["business_hash_invocations"] <= 0
                    or type(trace_document["recorded_stages"]) is not list
                    or len(trace_document["recorded_stages"]) != 12
                ):
                    _fail("causal-promotion child evidence inventory changed")

                budget_attestation = (
                    terminal_v1
                    .verify_v075_k7_causal_promotion_budget_replay_attestation_document_v1(
                        trace_document["budget_replay_attestation"]
                    )
                )

                registry = registry_v6.official_counter_registry_v6()
                stage_profile = registry_v6.official_stage_profile_v6(registry)
                comparison = registry_v6.official_comparison_profile_v6(registry)
                actual = registry_v6.official_actual_projection_profile_v6(
                    registry,
                    comparison,
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
                ) != owned_v2.CANONICAL_CAUSAL_PROMOTION_STAGE_PLAN_V2:
                    _fail("portable causal-promotion stage order changed")
                obligations.checked_integrity("twelve-stage-event-chains-replayed")
                obligations.checked_protocol("stage-order-and-owner-chain-enforced")

                science = trace_document["science_summary"]
                if type(science) is not dict or set(science) != SCIENCE_SUMMARY_KEYS:
                    _fail("causal-promotion science summary field set changed")
                for key in (
                    "occurrence_id",
                    "accounted_occurrence_id",
                    "owned_accounting_result_id",
                    "schedule_id",
                    "schedule_verification_id",
                    "root_execution_id",
                    "root_model_epoch_id",
                    "causal_child_authorization_id",
                    "causal_child_execution_bundle_id",
                    "causal_promotion_bundle_id",
                    "budget_closure_id",
                    "budget_closure_verification_id",
                    "budget_replay_attestation_id",
                ):
                    _cid(science[key], f"science summary {key}")
                if (
                    science["terminal_class"]
                    != "ATTEMPT_CLOSURE_NONCERTIFICATE"
                    or science["terminal_code"] != "ATTEMPT_BUDGET_EXHAUSTED"
                    or science["route_attempts"] != 1
                    or science["route_successes"] != 0
                    or science["route_failures"] != 1
                    or science["solver_attempts"] != 0
                    or science["solver_successes"] != 0
                    or science["solver_failures"] != 0
                    or science["observer_closed_and_exactly_reconciled"] is not True
                    or science["stage_instance_count"] != 12
                    or science["stage_local_counter_record_count"] != 2_424
                    or science["budget_replay_attestation_id"]
                    != budget_attestation["budget_replay_attestation_id"]
                    or science["budget_closure_id"]
                    != budget_attestation["budget_closure_id"]
                    or science["budget_closure_verification_id"]
                    != budget_attestation["budget_closure_verification_id"]
                ):
                    _fail("causal-promotion science or derived route facts changed")
                obligations.checked_integrity("science-summary-identity-chain-replayed")
                obligations.checked_protocol("terminal-route-reconciliation-enforced")
                obligations.checked_integrity("resource-formulas-reconciled")
                obligations.checked_protocol(
                    "operational-cutoff-precedes-accounting-provenance"
                )
                obligations.close()

    if parent_meter.count <= 0:
        _fail("parent causal-promotion hash window produced no observation")
    measurement = CausalPromotionPreOutputMeasurementV1(
        preparation.preparation_id,
        preparation.manifest.runtime_tree_id,
        preparation.source_closure.closure_id,
        request_document["supervised_request_id"],
        trace_document["operational_trace_id"],
        science["occurrence_id"],
        science["accounted_occurrence_id"],
        science["owned_accounting_result_id"],
        preparation.manifest.file_count,
        preparation.manifest.total_bytes,
        preparation.manifest.manifest_document_bytes,
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
    return SupervisedCausalPromotionExecutionV1(
        _EXECUTION_ISSUER,
        preparation,
        MappingProxyType(dict(request_document)),
        trace_raw,
        MappingProxyType(dict(trace_document)),
        MappingProxyType(dict(science)),
        recorded_stages,
        measurement,
    )


__all__ = (
    "CausalPromotionPreOutputMeasurementV1",
    "CausalPromotionRuntimePreparationV1",
    "DEFAULT_TIMEOUT_SECONDS",
    "PRE_OUTPUT_SHARED_PATHS",
    "SupervisedCausalPromotionExecutionV1",
    "V075K7CausalPromotionAccountedExecutorV1Error",
    "execute_v075_k7_causal_promotion_accounted_v1",
    "prepare_v075_k7_causal_promotion_accounted_runtime_v1",
)
