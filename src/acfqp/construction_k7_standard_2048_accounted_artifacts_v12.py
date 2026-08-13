"""Exact V8 vector artifacts and output-byte closure for standard 2048.

Operational business work is frozen before this module starts.  The renderer
then solves the self-referential ``io.output_bytes`` value in memory, writes
the exact eight registered role files once, and fsyncs both files and their
directory.  Hashes used only to construct accounting provenance are excluded
from the business hash counter, as preregistered, so the accounting graph does
not recursively charge its own content IDs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import stat
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import RouteKindEnum, WorkVectorV1
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp import construction_accounting_registry_v8 as registry_v8
from acfqp import construction_k7_standard_2048_accounted_preregistration_v12 as pre
from acfqp import construction_k7_standard_2048_instrumented_runtime_v12 as runtime
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp.phase3e_ids import (
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = "construction_k7_standard_2048_accounted_artifacts_v12"
DOMAINS = pre.FUTURE_DOMAINS
SHARED_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)


class ConstructionK7Standard2048AccountedArtifactsV12Error(RuntimeError):
    """A measurement, fixed point, vector, or durable write changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048AccountedArtifactsV12Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048AccountedArtifactsV12Error(
            f"{label} is not one exact content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} is not one nonnegative exact integer")
    return value


def _exact_document(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{label} must be one exact mapping")
    raw = canonical_json_bytes(dict(value))
    replayed = loads_canonical_json(raw)
    if type(replayed) is not dict:
        raise AssertionError("canonical object replay changed")
    return replayed


@dataclass(frozen=True, slots=True)
class Standard2048AccountingMeasurementV12:
    subject_id: str
    window_role: str
    shared_values: tuple[tuple[str, int], ...]
    allocation_profile: str

    def __post_init__(self) -> None:
        _cid(self.subject_id, "measurement subject")
        if (
            type(self.window_role) is not str
            or not self.window_role
            or type(self.allocation_profile) is not str
            or not self.allocation_profile
            or type(self.shared_values) is not tuple
            or tuple(path for path, _ in self.shared_values) != SHARED_PATHS
        ):
            _fail("measurement window shape changed")
        for path, value in self.shared_values:
            if path not in SHARED_PATHS:
                _fail("measurement contains an unknown shared path")
            _nonnegative(value, f"measurement {path}")

    def _payload(self) -> dict[str, Any]:
        registry = registry_v8.official_counter_registry_v8()
        return {
            "schema": "acfqp.standard_2048_accounting_measurement.v12",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "accounted_preregistration_id": pre.PREREGISTRATION_ID,
            "subject_id": self.subject_id,
            "measurement_window_role": self.window_role,
            "allocation_profile": self.allocation_profile,
            "shared_resource_rows": [
                {
                    "path": path,
                    "value": value,
                    "reducer": registry.by_path[path].reducer.value,
                    "value_kind": "EXACT_OR_PREREGISTERED_VERIFIED_UPPER",
                }
                for path, value in self.shared_values
            ],
            "all_nine_shared_paths_present": True,
            "native_zero_observed_not_inferred": True,
            "accounting_provenance_hashes_excluded": True,
            "complete_window_closed": True,
            "official_execution_allowed": False,
        }

    @property
    def measurement_id(self) -> str:
        return content_id(DOMAINS["measurement"], self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "accounting_measurement_id": self.measurement_id}


@dataclass(frozen=True, slots=True)
class Standard2048OutputCommitV12:
    subject_id: str
    output_key: str
    fixed_point_result_id: str | None
    role_rows: tuple[tuple[str, int, str], ...]
    evaluation_only: bool

    def __post_init__(self) -> None:
        _cid(self.subject_id, "output-commit subject")
        if self.fixed_point_result_id is not None:
            _cid(self.fixed_point_result_id, "output fixed point")
        if (
            type(self.output_key) is not str
            or not self.output_key
            or type(self.role_rows) is not tuple
            or not self.role_rows
            or len({row[0] for row in self.role_rows}) != len(self.role_rows)
            or type(self.evaluation_only) is not bool
        ):
            _fail("output commit shape changed")
        for role, byte_count, digest in self.role_rows:
            if type(role) is not str or not role:
                _fail("output commit role changed")
            if type(byte_count) is not int or byte_count <= 0:
                _fail("output commit contains an empty artifact")
            _cid(digest, "output artifact digest")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.standard_2048_output_commit.v12",
            "schema_version": SCHEMA_VERSION,
            "subject_id": self.subject_id,
            "output_key": self.output_key,
            "output_bytes_fixed_point_result_id": self.fixed_point_result_id,
            "role_rows": [
                {
                    "artifact_role": role,
                    "byte_count": byte_count,
                    "bytes_sha256": digest,
                }
                for role, byte_count, digest in self.role_rows
            ],
            "evaluation_only": self.evaluation_only,
            "file_fsync_complete": True,
            "directory_fsync_complete": True,
            "committed_once": True,
            "path_independent_identity": True,
        }

    @property
    def output_commit_id(self) -> str:
        return content_id(DOMAINS["output_commit"], self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "output_commit_id": self.output_commit_id}


@dataclass(frozen=True, slots=True)
class MaterializedOperationalSegmentV12:
    subject_id: str
    segment_role: str
    measurement: Standard2048AccountingMeasurementV12
    fixed_point: fixed_v1.OutputBytesFixedPointResultV1 = field(
        repr=False, compare=False
    )
    accounting_chain: runtime.OperationalAccountingChainV12 = field(
        repr=False, compare=False
    )
    output_commit: Standard2048OutputCommitV12

    def __post_init__(self) -> None:
        if (
            self.subject_id != self.measurement.subject_id
            or self.accounting_chain.work_vector.subject_id != self.subject_id
            or self.accounting_chain.work_vector.value("io.output_bytes")
            != self.fixed_point.output_bytes
            or self.output_commit.subject_id != self.subject_id
            or self.output_commit.fixed_point_result_id != self.fixed_point.result_id
            or self.output_commit.evaluation_only
        ):
            _fail("operational segment materialization changed")

    def to_document(self) -> dict[str, Any]:
        payload = {
            "schema": "acfqp.standard_2048_operational_counter_bundle.v12",
            "schema_version": SCHEMA_VERSION,
            "subject_id": self.subject_id,
            "segment_role": self.segment_role,
            "accounting_measurement": self.measurement.to_document(),
            "work_vector": self.accounting_chain.work_vector.to_dict(),
            "comparison_vector": self.accounting_chain.comparison_vector.to_dict(),
            "actual_projection_proof": self.accounting_chain.projection_proof.to_dict(),
            "output_bytes_fixed_point_result": self.fixed_point.to_document(),
            "output_commit": self.output_commit.to_document(),
            "counter_record_count": len(self.accounting_chain.work_vector.records),
            "counter_record_to_work_vector_to_comparison_vector_complete": True,
            "official_execution_allowed": False,
        }
        return {
            **payload,
            "accounted_counter_bundle_id": content_id(
                DOMAINS["counter_bundle"], payload
            ),
        }


@dataclass(frozen=True, slots=True)
class MaterializedEvaluationV12:
    subject_id: str
    measurement: Mapping[str, Any]
    work_vector: WorkVectorV1 = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False, compare=False)
    transport_output_bytes: int
    output_commit: Standard2048OutputCommitV12

    def __post_init__(self) -> None:
        if (
            self.work_vector.subject_id != self.subject_id
            or self.work_vector.value("evaluation.io_output_bytes")
            != self.transport_output_bytes + len(self.canonical_bytes)
            or self.output_commit.subject_id != self.subject_id
            or not self.output_commit.evaluation_only
        ):
            _fail("evaluation materialization changed")

    def to_document(self) -> dict[str, Any]:
        payload = {
            "schema": "acfqp.standard_2048_evaluation_counter_bundle.v12",
            "schema_version": SCHEMA_VERSION,
            "subject_id": self.subject_id,
            "accounting_measurement": dict(self.measurement),
            "work_vector_id": self.work_vector.work_vector_id,
            "output_commit": self.output_commit.to_document(),
            "canonical_byte_count": len(self.canonical_bytes),
            "transport_output_byte_count": self.transport_output_bytes,
            "total_evaluation_output_byte_count": (
                self.transport_output_bytes + len(self.canonical_bytes)
            ),
            "canonical_bytes_sha256": hashlib.sha256(self.canonical_bytes).hexdigest(),
            "evaluation_lane_excluded_from_operational_comparison": True,
            "comparison_vector_issued": False,
            "official_execution_allowed": False,
        }
        return {
            **payload,
            "accounted_counter_bundle_id": content_id(
                DOMAINS["counter_bundle"], payload
            ),
        }


def _with_output_candidate(
    base_values: Mapping[str, int],
    candidate: int,
    *,
    allocation_profile: str,
) -> dict[str, int]:
    registry = registry_v8.official_counter_registry_v8()
    if set(base_values) != set(registry.by_path):
        _fail("base values do not cover the full V8 registry")
    values = dict(base_values)
    values["io.output_bytes"] = _nonnegative(candidate, "output candidate")
    if allocation_profile == "CAMPAIGN_GLOBAL_MOUNT_PEAK_PLUS_OWN_OUTPUT":
        values["io.mounted_bytes_peak"] += candidate
    else:
        values["io.mounted_bytes_peak"] = max(
            values["io.mounted_bytes_peak"], candidate
        )
    return values


def _measurement(
    subject_id: str,
    segment_role: str,
    values: Mapping[str, int],
    *,
    allocation_profile: str,
) -> Standard2048AccountingMeasurementV12:
    return Standard2048AccountingMeasurementV12(
        subject_id,
        segment_role,
        tuple((path, values[path]) for path in SHARED_PATHS),
        allocation_profile,
    )


def _static_roles(
    *,
    subject_id: str,
    segment_role: str,
    business_document: Mapping[str, Any],
    trace_document: Mapping[str, Any],
    terminal_document: Mapping[str, Any],
) -> Mapping[str, bytes]:
    business = _exact_document(business_document, "business document")
    trace = _exact_document(trace_document, "trace document")
    terminal = _exact_document(terminal_document, "terminal document")
    return MappingProxyType(
        {
            "BUSINESS_RESULT": canonical_json_bytes(
                {
                    "artifact_role": "BUSINESS_RESULT",
                    "schema": "acfqp.standard_2048_business_result.v12",
                    "subject_id": subject_id,
                    "segment_role": segment_role,
                    "business_result": business,
                }
            ),
            "OPERATIONAL_TRACE": canonical_json_bytes(
                {
                    "artifact_role": "OPERATIONAL_TRACE",
                    "schema": "acfqp.standard_2048_operational_trace.v12",
                    "subject_id": subject_id,
                    "segment_role": segment_role,
                    "operational_trace": trace,
                    "accounting_provenance_hashes_excluded": True,
                }
            ),
            "TERMINAL_ARTIFACT": canonical_json_bytes(
                {
                    "artifact_role": "TERMINAL_ARTIFACT",
                    "schema": "acfqp.standard_2048_segment_terminal.v12",
                    "subject_id": subject_id,
                    "segment_role": segment_role,
                    "terminal": terminal,
                }
            ),
        }
    )


def _render_operational(
    *,
    subject_id: str,
    segment_role: str,
    route_kind: RouteKindEnum,
    work_scope: ActualWorkScope,
    base_values: Mapping[str, int],
    profile: fixed_v1.OutputBytesFixedPointProfileV1,
    candidate: int,
    static_roles: Mapping[str, bytes],
    allocation_profile: str,
) -> tuple[
    Standard2048AccountingMeasurementV12,
    runtime.OperationalAccountingChainV12,
    Mapping[str, bytes],
]:
    values = _with_output_candidate(
        base_values,
        candidate,
        allocation_profile=allocation_profile,
    )
    measurement = _measurement(
        subject_id,
        segment_role,
        values,
        allocation_profile=allocation_profile,
    )
    recorders = {path: measurement.measurement_id for path in SHARED_PATHS}
    chain = runtime.build_operational_accounting_chain_v12(
        subject_id=subject_id,
        route_kind=route_kind,
        work_scope=work_scope,
        values=values,
        recorder_id=subject_id,
        recorder_ids_by_path=recorders,
    )
    roles = dict(static_roles)
    roles["COUNTER_RECORD_SET"] = canonical_json_bytes(
        {
            "artifact_role": "COUNTER_RECORD_SET",
            "schema": "acfqp.standard_2048_counter_record_set.v12",
            "subject_id": subject_id,
            "segment_role": segment_role,
            "io.output_bytes": candidate,
            "accounting_measurement": measurement.to_document(),
            "counter_records": [row.to_dict() for row in chain.work_vector.records],
            "counter_record_count": len(chain.work_vector.records),
        }
    )
    roles["WORK_VECTOR"] = canonical_json_bytes(
        {
            "artifact_role": "WORK_VECTOR",
            "schema": "acfqp.standard_2048_work_vector_artifact.v12",
            "io.output_bytes": candidate,
            "work_vector": chain.work_vector.to_dict(),
        }
    )
    roles["COMPARISON_VECTOR"] = canonical_json_bytes(
        {
            "artifact_role": "COMPARISON_VECTOR",
            "schema": "acfqp.standard_2048_comparison_vector_artifact.v12",
            "io.output_bytes": candidate,
            "comparison_vector": chain.comparison_vector.to_dict(),
            "route_choice_authority": False,
        }
    )
    roles["ACTUAL_PROJECTION_PROOF"] = canonical_json_bytes(
        {
            "artifact_role": "ACTUAL_PROJECTION_PROOF",
            "schema": "acfqp.standard_2048_projection_artifact.v12",
            "io.output_bytes": candidate,
            "actual_projection_proof": chain.projection_proof.to_dict(),
            "all_operational_leaves_projected_exactly_once": True,
        }
    )
    preceding = [
        {
            "artifact_role": role,
            "byte_count": len(raw),
            "bytes_sha256": hashlib.sha256(raw).hexdigest(),
        }
        for role, raw in roles.items()
    ]
    roles["OUTPUT_MANIFEST"] = canonical_json_bytes(
        {
            "artifact_role": "OUTPUT_MANIFEST",
            "schema": "acfqp.standard_2048_output_manifest.v12",
            "subject_id": subject_id,
            "segment_role": segment_role,
            "output_bytes_fixed_point_profile_id": profile.profile_id,
            "io.output_bytes": candidate,
            "ordered_preceding_roles": preceding,
            "required_role_order": list(
                fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
            ),
        }
    )
    if tuple(roles) != fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES:
        _fail("operational output role order changed")
    return measurement, chain, MappingProxyType(roles)


def _write_roles(
    *, output_directory: Path, role_bytes: Mapping[str, bytes]
) -> tuple[tuple[str, int, str], ...]:
    if output_directory.exists():
        _fail("output directory must be absent")
    output_directory.mkdir(mode=0o700, parents=False)
    directory_fd = os.open(
        output_directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    )
    rows: list[tuple[str, int, str]] = []
    try:
        for role, raw in role_bytes.items():
            filename = f"{role}.json"
            fd = os.open(
                filename,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
                0o400,
                dir_fd=directory_fd,
            )
            try:
                view = memoryview(raw)
                while view:
                    written = os.write(fd, view)
                    if written <= 0:
                        _fail("output write made no progress")
                    view = view[written:]
                os.fsync(fd)
            finally:
                os.close(fd)
            observed = os.stat(
                filename, dir_fd=directory_fd, follow_symlinks=False
            )
            if not stat.S_ISREG(observed.st_mode) or observed.st_size != len(raw):
                _fail("output file readback changed")
            rows.append((role, len(raw), hashlib.sha256(raw).hexdigest()))
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return tuple(rows)


def materialize_operational_segment_v12(
    *,
    subject_id: str,
    segment_role: str,
    route_kind: RouteKindEnum,
    work_scope: ActualWorkScope,
    base_values: Mapping[str, int],
    business_document: Mapping[str, Any],
    trace_document: Mapping[str, Any],
    terminal_document: Mapping[str, Any],
    output_directory: str | Path,
    output_key: str,
    allocation_profile: str,
) -> MaterializedOperationalSegmentV12:
    _cid(subject_id, "operational segment subject")
    static_roles = _static_roles(
        subject_id=subject_id,
        segment_role=segment_role,
        business_document=business_document,
        trace_document=trace_document,
        terminal_document=terminal_document,
    )
    renderer_id = content_id(
        DOMAINS["output_renderer"],
        {
            "subject_id": subject_id,
            "segment_role": segment_role,
            "required_roles": list(fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES),
            "renderer_semantics": "STANDARD_2048_V12_OPERATIONAL_VECTOR_RENDERER",
        },
    )
    profile = fixed_v1.freeze_output_bytes_fixed_point_profile_v1(
        renderer_id=renderer_id,
        execution_identity_id=subject_id,
        max_total_bytes=64 * 1024 * 1024,
        max_iterations=32,
    )
    cache: dict[
        int,
        tuple[
            Standard2048AccountingMeasurementV12,
            runtime.OperationalAccountingChainV12,
            Mapping[str, bytes],
        ],
    ] = {}

    def render(candidate: int) -> dict[str, bytes]:
        value = cache.get(candidate)
        if value is None:
            value = _render_operational(
                subject_id=subject_id,
                segment_role=segment_role,
                route_kind=route_kind,
                work_scope=work_scope,
                base_values=base_values,
                profile=profile,
                candidate=candidate,
                static_roles=static_roles,
                allocation_profile=allocation_profile,
            )
            cache[candidate] = value
        return dict(value[2])

    fixed_point = fixed_v1.solve_output_bytes_fixed_point_v1(
        profile=profile, renderer=render
    )
    fixed_v1.replay_output_bytes_fixed_point_v1(
        result=fixed_point, renderer=render
    )
    measurement, chain, role_bytes = _render_operational(
        subject_id=subject_id,
        segment_role=segment_role,
        route_kind=route_kind,
        work_scope=work_scope,
        base_values=base_values,
        profile=profile,
        candidate=fixed_point.output_bytes,
        static_roles=static_roles,
        allocation_profile=allocation_profile,
    )
    if dict(role_bytes) != fixed_point.artifact_bytes_by_role:
        _fail("terminal render differs from the fixed-point role bytes")
    rows = _write_roles(
        output_directory=Path(output_directory), role_bytes=role_bytes
    )
    commit = Standard2048OutputCommitV12(
        subject_id,
        output_key,
        fixed_point.result_id,
        rows,
        False,
    )
    return MaterializedOperationalSegmentV12(
        subject_id,
        segment_role,
        measurement,
        fixed_point,
        chain,
        commit,
    )


def _evaluation_candidate(
    *,
    subject_id: str,
    transport_document: Mapping[str, Any],
    exact_document: Mapping[str, Any],
    forced_document: Mapping[str, Any] | None,
    base_values: Mapping[str, int],
    candidate: int,
    working_bytes_peak: int,
) -> tuple[dict[str, Any], WorkVectorV1, bytes]:
    values = dict(base_values)
    registry = registry_v8.official_counter_registry_v8()
    if set(values) != set(registry.by_path):
        _fail("evaluation values do not cover V8")
    values["evaluation.io_output_bytes"] = candidate
    values["evaluation.io_mounted_bytes_peak"] = max(
        values["evaluation.io_mounted_bytes_peak"], candidate
    )
    values["evaluation.memory_working_bytes_peak"] = max(
        values["evaluation.memory_working_bytes_peak"], working_bytes_peak
    )
    measurement_payload = {
        "schema": "acfqp.standard_2048_evaluation_measurement.v12",
        "schema_version": SCHEMA_VERSION,
        "subject_id": subject_id,
        "evaluation_lane_values": {
            leaf.path: values[leaf.path] for leaf in registry.evaluation_leaves
        },
        "evaluation_diagnostic_values": {
            leaf.path: values[leaf.path]
            for leaf in registry.leaves
            if leaf.path.startswith("evaluation.")
            and leaf not in registry.evaluation_leaves
        },
        "operational_route_values_zero": True,
        "accounting_provenance_hashes_excluded": True,
    }
    measurement = {
        **measurement_payload,
        "accounting_measurement_id": content_id(
            DOMAINS["measurement"], measurement_payload
        ),
    }
    recorders = {
        path: measurement["accounting_measurement_id"]
        for path in values
        if path.startswith("evaluation.")
    }
    vector = runtime.build_evaluation_work_vector_v12(
        subject_id=subject_id,
        values=values,
        recorder_id=subject_id,
        recorder_ids_by_path=recorders,
    )
    document = {
        "artifact_role": "EVALUATION_WORK_VECTOR",
        "schema": "acfqp.standard_2048_evaluation_artifact.v12",
        "schema_version": SCHEMA_VERSION,
        "subject_id": subject_id,
        "evaluation.io_output_bytes": candidate,
        "evaluation_transport": _exact_document(
            transport_document, "evaluation transport"
        ),
        "accounting_measurement": measurement,
        "exact_plan": _exact_document(exact_document, "evaluation exact plan"),
        "forced_selected_action_exact_evaluation": (
            None
            if forced_document is None
            else _exact_document(forced_document, "evaluation forced plan")
        ),
        "work_vector": vector.to_dict(),
        "comparison_vector_issued": False,
        "evaluation_lane_excluded_from_operational_route_vector": True,
    }
    return measurement, vector, canonical_json_bytes(document)


def materialize_evaluation_v12(
    *,
    subject_id: str,
    transport_document: Mapping[str, Any],
    exact_document: Mapping[str, Any],
    forced_document: Mapping[str, Any] | None,
    base_values: Mapping[str, int],
    transport_output_bytes: int = 0,
    working_bytes_peak: int,
    output_directory: str | Path,
    output_key: str,
) -> MaterializedEvaluationV12:
    _cid(subject_id, "evaluation subject")
    transport_output_bytes = _nonnegative(
        transport_output_bytes, "evaluation transport output bytes"
    )
    candidate = transport_output_bytes
    final: tuple[dict[str, Any], WorkVectorV1, bytes] | None = None
    for _ in range(32):
        current = _evaluation_candidate(
            subject_id=subject_id,
            transport_document=transport_document,
            exact_document=exact_document,
            forced_document=forced_document,
            base_values=base_values,
            candidate=candidate,
            working_bytes_peak=_nonnegative(
                working_bytes_peak, "evaluation working peak"
            ),
        )
        rendered = transport_output_bytes + len(current[2])
        if rendered < candidate:
            _fail("evaluation output-byte fixed point decreased")
        if rendered == candidate:
            final = current
            break
        candidate = rendered
    if final is None:
        _fail("evaluation output-byte fixed point did not converge")
    replayed = _evaluation_candidate(
        subject_id=subject_id,
        transport_document=transport_document,
        exact_document=exact_document,
        forced_document=forced_document,
        base_values=base_values,
        candidate=candidate,
        working_bytes_peak=working_bytes_peak,
    )
    if replayed[2] != final[2] or replayed[1] != final[1]:
        _fail("evaluation fixed-point replay changed")
    rows = _write_roles(
        output_directory=Path(output_directory),
        role_bytes={"EVALUATION_WORK_VECTOR": final[2]},
    )
    commit = Standard2048OutputCommitV12(
        subject_id,
        output_key,
        None,
        rows,
        True,
    )
    return MaterializedEvaluationV12(
        subject_id,
        MappingProxyType(final[0]),
        final[1],
        final[2],
        transport_output_bytes,
        commit,
    )


__all__ = (
    "ConstructionK7Standard2048AccountedArtifactsV12Error",
    "MaterializedEvaluationV12",
    "MaterializedOperationalSegmentV12",
    "SHARED_PATHS",
    "Standard2048AccountingMeasurementV12",
    "Standard2048OutputCommitV12",
    "materialize_evaluation_v12",
    "materialize_operational_segment_v12",
)
