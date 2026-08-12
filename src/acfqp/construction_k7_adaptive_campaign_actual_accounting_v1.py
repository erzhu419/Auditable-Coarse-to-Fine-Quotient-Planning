"""Formal V7 actual accounting for the adaptive W5/K6 campaign.

The native campaign supplies owner-bound non-shared CounterRecords and the
same-window shared events.  This module closes each logical occurrence with
nine typed shared-resource receipts, reducer-exact path aggregation, one
CounterRecord -> WorkVector -> ComparisonVector chain, and an exact
eight-role output-byte fixed point.  Construct, reuse, and unsupported paths
remain distinct route kinds.

This is still construction evidence.  A separate bytes-only verifier is
required before the Counter Completeness gate may run; scalar economics and
official execution remain locked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import stat
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import (
    ComparisonVectorV1,
    CounterRecordV1,
    LaneEnum,
    ReducerEnum,
    RouteKindEnum,
    SHARED_AXES,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import ActualProjectionProofV1, ActualWorkScope
from acfqp import construction_accounting_registry_v7 as registry_v7
from acfqp import construction_k7_adaptive_campaign_native_accounting_v1 as native_v1
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ADAPTIVE_CAMPAIGN_ACCOUNTING_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_OCCURRENCE_ACCOUNTING_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_OUTPUT_COMMIT_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_OUTPUT_RENDERER_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_PATH_AGGREGATION_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_SHARED_MEASUREMENT_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_SHARED_RECEIPT_SET_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_SHARED_RECEIPT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.148"
PROFILE_KEY = "construction_k7_adaptive_campaign_actual_accounting_v1"
SHARED_PATHS = native_v1.SHARED_RESOURCE_PATHS
EXPECTED_REQUIRED_PATH_COUNT = registry_v7.EXPECTED_V7_REQUIRED_LEAF_COUNT
EXPECTED_OPERATIONAL_PATH_COUNT = registry_v7.EXPECTED_V7_OPERATIONAL_LEAF_COUNT

MEASUREMENT_DOMAIN = CONSTRUCTION_K7_ADAPTIVE_SHARED_MEASUREMENT_V1_DOMAIN
RECEIPT_DOMAIN = CONSTRUCTION_K7_ADAPTIVE_SHARED_RECEIPT_V1_DOMAIN
RECEIPT_SET_DOMAIN = CONSTRUCTION_K7_ADAPTIVE_SHARED_RECEIPT_SET_V1_DOMAIN
AGGREGATION_DOMAIN = CONSTRUCTION_K7_ADAPTIVE_PATH_AGGREGATION_V1_DOMAIN
OCCURRENCE_DOMAIN = CONSTRUCTION_K7_ADAPTIVE_OCCURRENCE_ACCOUNTING_V1_DOMAIN
CAMPAIGN_DOMAIN = CONSTRUCTION_K7_ADAPTIVE_CAMPAIGN_ACCOUNTING_V1_DOMAIN
RENDERER_DOMAIN = CONSTRUCTION_K7_ADAPTIVE_OUTPUT_RENDERER_V1_DOMAIN
OUTPUT_COMMIT_DOMAIN = CONSTRUCTION_K7_ADAPTIVE_OUTPUT_COMMIT_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {
        MEASUREMENT_DOMAIN,
        RECEIPT_DOMAIN,
        RECEIPT_SET_DOMAIN,
        AGGREGATION_DOMAIN,
        OCCURRENCE_DOMAIN,
        CAMPAIGN_DOMAIN,
        RENDERER_DOMAIN,
        OUTPUT_COMMIT_DOMAIN,
    }
)
if LOCAL_DOMAINS - PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("adaptive actual-accounting domains are not central")


class ConstructionK7AdaptiveCampaignActualAccountingV1Error(RuntimeError):
    """One native join, receipt, projection, fixed point, or commit failed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AdaptiveCampaignActualAccountingV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AdaptiveCampaignActualAccountingV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _route_kind(outcome: str) -> RouteKindEnum:
    if outcome == "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED":
        return RouteKindEnum.LOCAL_ATTEMPT
    if outcome == "EXISTING_MODEL_REUSED":
        return RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
    if outcome == "NO_CERTIFIABLE_CONSTRUCTOR":
        return RouteKindEnum.ABSTRACT_FAILED_PREFIX
    _fail("adaptive result outcome has no registered route kind")


def _work_scope(route: RouteKindEnum) -> ActualWorkScope:
    return (
        ActualWorkScope.MARGINAL_ROUTE_AGGREGATE
        if route is RouteKindEnum.LOCAL_ATTEMPT
        else ActualWorkScope.COMMON_PREFIX
    )


@dataclass(frozen=True, slots=True)
class AdaptiveSharedMeasurementV1:
    occurrence_id: str
    native_occurrence_id: str
    route_input_sha256: str
    route_input_bytes: int
    hash_invocations: int
    integrity_checks: int
    protocol_checks: int
    staged_bytes: int
    process_launches: int
    working_bytes_peak_upper: int
    native_event_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "measurement occurrence"),
            (self.native_occurrence_id, "measurement native occurrence"),
            (self.route_input_sha256, "measurement input digest"),
        ):
            _cid(value, label)
        for value, label in (
            (self.route_input_bytes, "read bytes"),
            (self.hash_invocations, "hash invocations"),
            (self.integrity_checks, "integrity checks"),
            (self.protocol_checks, "protocol checks"),
            (self.staged_bytes, "staged bytes"),
            (self.process_launches, "process launches"),
            (self.working_bytes_peak_upper, "working bytes peak"),
        ):
            _nonnegative(value, label)
        if (
            self.occurrence_id != self.native_occurrence_id
            or self.route_input_bytes <= 0
            or self.hash_invocations <= 0
            or self.integrity_checks <= 0
            or self.protocol_checks <= 0
            or self.working_bytes_peak_upper <= 0
            or type(self.native_event_ids) is not tuple
            or tuple(sorted(set(self.native_event_ids))) != self.native_event_ids
        ):
            _fail("adaptive shared measurement is incomplete")
        for value in self.native_event_ids:
            _cid(value, "measurement native event")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_adaptive_shared_measurement.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "adaptive_native_occurrence_id": self.native_occurrence_id,
            "route_input_bytes_sha256": self.route_input_sha256,
            "io.read_bytes": self.route_input_bytes,
            "common.hash_invocations": self.hash_invocations,
            "common.integrity_checks": self.integrity_checks,
            "common.protocol_checks": self.protocol_checks,
            "io.staged_bytes": self.staged_bytes,
            "process.launches": self.process_launches,
            "memory.working_bytes_peak": self.working_bytes_peak_upper,
            "native_shared_event_ids": list(self.native_event_ids),
            "read_bytes_kind": "EXACT_CANONICAL_ROUTE_INPUT_ENVELOPE",
            "working_bytes_kind": "VERIFIED_CONSERVATIVE_UPPER_BOUND",
            "same_process_zero_staging_explicit_when_no_worker": True,
            "complete_window_closed": True,
            "official_execution_allowed": False,
        }

    @property
    def measurement_id(self) -> str:
        return content_id(MEASUREMENT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "shared_measurement_id": self.measurement_id}


@dataclass(frozen=True, slots=True)
class AdaptiveSharedReceiptV1:
    occurrence_id: str
    measurement_id: str
    path: str
    reducer: ReducerEnum
    value: int
    source_kind: str
    source_evidence_id: str
    native_event_ids: tuple[str, ...]
    fixed_point_profile_id: str | None = None

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "receipt occurrence")
        _cid(self.measurement_id, "receipt measurement")
        _cid(self.source_evidence_id, "receipt source")
        object.__setattr__(self, "reducer", ReducerEnum(self.reducer))
        _nonnegative(self.value, "receipt value")
        if (
            self.path not in SHARED_PATHS
            or type(self.native_event_ids) is not tuple
            or tuple(sorted(set(self.native_event_ids))) != self.native_event_ids
            or self.source_kind
            not in {
                "NATIVE_EVENT_REDUCTION",
                "COMPLETE_WINDOW_ZERO_ATTESTATION",
                "DERIVED_MOUNTED_BYTES_UPPER",
                "OUTPUT_FIXED_POINT",
            }
        ):
            _fail("adaptive shared receipt shape changed")
        is_output = self.path == "io.output_bytes"
        if (self.fixed_point_profile_id is not None) != is_output:
            _fail("adaptive output receipt lost its fixed-point binding")
        if self.fixed_point_profile_id is not None:
            _cid(self.fixed_point_profile_id, "receipt fixed point")
        for value in self.native_event_ids:
            _cid(value, "receipt native event")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_adaptive_shared_receipt.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "shared_measurement_id": self.measurement_id,
            "path": self.path,
            "reducer": self.reducer.value,
            "value": self.value,
            "source_kind": self.source_kind,
            "source_evidence_id": self.source_evidence_id,
            "native_event_ids": list(self.native_event_ids),
            "output_fixed_point_profile_id": self.fixed_point_profile_id,
            "one_occurrence_charge": True,
            "official_execution_allowed": False,
        }

    @property
    def receipt_id(self) -> str:
        return content_id(RECEIPT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "shared_resource_receipt_id": self.receipt_id}


@dataclass(frozen=True, slots=True)
class AdaptiveSharedReceiptSetV1:
    occurrence_id: str
    measurement_id: str
    receipts: tuple[AdaptiveSharedReceiptV1, ...]

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "receipt-set occurrence")
        _cid(self.measurement_id, "receipt-set measurement")
        if (
            type(self.receipts) is not tuple
            or tuple(row.path for row in self.receipts) != SHARED_PATHS
            or any(
                type(row) is not AdaptiveSharedReceiptV1
                or row.occurrence_id != self.occurrence_id
                or row.measurement_id != self.measurement_id
                for row in self.receipts
            )
        ):
            _fail("adaptive receipt set does not cover nine paths exactly")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_adaptive_shared_receipt_set.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "shared_measurement_id": self.measurement_id,
            "shared_resource_paths": list(SHARED_PATHS),
            "shared_resource_receipt_ids": [row.receipt_id for row in self.receipts],
            "receipt_count": len(self.receipts),
            "all_nine_shared_paths_present": True,
            "official_execution_allowed": False,
        }

    @property
    def receipt_set_id(self) -> str:
        return content_id(RECEIPT_SET_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "shared_resource_receipt_set_id": self.receipt_set_id}


@dataclass(frozen=True, slots=True)
class AdaptivePathAggregationV1:
    occurrence_id: str
    path: str
    reducer: ReducerEnum
    value: int
    component_record_ids: tuple[str, ...]
    source_kind: str
    source_evidence_id: str

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "aggregation occurrence")
        _cid(self.source_evidence_id, "aggregation source")
        object.__setattr__(self, "reducer", ReducerEnum(self.reducer))
        _nonnegative(self.value, "aggregation value")
        if (
            type(self.path) is not str
            or not self.path
            or type(self.component_record_ids) is not tuple
            or self.source_kind
            not in {
                "COMPONENT_SUM",
                "COMPONENT_MAX",
                "SHARED_RESOURCE_RECEIPT",
                "SEMANTIC_DERIVED_RECONCILIATION",
            }
        ):
            _fail("adaptive path aggregation shape changed")
        for value in self.component_record_ids:
            _cid(value, "aggregation component record")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_adaptive_path_aggregation.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "path": self.path,
            "reducer": self.reducer.value,
            "value": self.value,
            "component_record_ids": list(self.component_record_ids),
            "source_kind": self.source_kind,
            "source_evidence_id": self.source_evidence_id,
            "all_component_instances_retained": True,
        }

    @property
    def aggregation_id(self) -> str:
        return content_id(AGGREGATION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "path_aggregation_id": self.aggregation_id}


@dataclass(frozen=True, slots=True)
class AdaptiveOutputCommitV1:
    occurrence_id: str
    fixed_point_result_id: str
    output_directory: str
    role_rows: tuple[tuple[str, int, str], ...]

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "output commit occurrence")
        _cid(self.fixed_point_result_id, "output fixed point")
        if (
            type(self.output_directory) is not str
            or not self.output_directory
            or tuple(row[0] for row in self.role_rows)
            != fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
        ):
            _fail("adaptive output commit shape changed")
        for _role, size, digest in self.role_rows:
            if type(size) is not int or size <= 0:
                _fail("adaptive output commit contains an empty role")
            _cid(digest, "output role digest")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_adaptive_output_commit.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "output_bytes_fixed_point_result_id": self.fixed_point_result_id,
            "output_directory": self.output_directory,
            "role_rows": [
                {"artifact_role": role, "byte_count": size, "bytes_sha256": digest}
                for role, size, digest in self.role_rows
            ],
            "file_fsync_complete": True,
            "directory_fsync_complete": True,
            "committed_once": True,
        }

    @property
    def output_commit_id(self) -> str:
        return content_id(OUTPUT_COMMIT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "output_commit_id": self.output_commit_id}


@dataclass(frozen=True, slots=True)
class _MaterializedV1:
    receipt_set: AdaptiveSharedReceiptSetV1
    aggregations: tuple[AdaptivePathAggregationV1, ...]
    work_vector: WorkVectorV1
    comparison_vector: ComparisonVectorV1
    projection_proof: ActualProjectionProofV1


def _event_reduction(
    occurrence: native_v1.AdaptiveOccurrenceNativeAccountingV1,
) -> tuple[dict[str, int], dict[str, tuple[str, ...]]]:
    registry = registry_v7.official_counter_registry_v7()
    values = {path: 0 for path in SHARED_PATHS}
    ids: dict[str, list[str]] = {path: [] for path in SHARED_PATHS}
    for event in occurrence.shared_events:
        leaf = registry.by_path[event.target_path]
        ids[event.target_path].append(event.event_id)
        if leaf.reducer is ReducerEnum.SUM:
            values[event.target_path] += event.value
        else:
            values[event.target_path] = max(
                values[event.target_path], event.value
            )
    return values, {
        path: tuple(sorted(rows)) for path, rows in ids.items()
    }


def _measurement(
    occurrence: native_v1.AdaptiveOccurrenceNativeAccountingV1,
) -> AdaptiveSharedMeasurementV1:
    values, ids = _event_reduction(occurrence)
    result = AdaptiveSharedMeasurementV1(
        occurrence.occurrence_id,
        occurrence.occurrence_id,
        occurrence.route_input_sha256,
        values["io.read_bytes"],
        values["common.hash_invocations"],
        values["common.integrity_checks"],
        values["common.protocol_checks"],
        values["io.staged_bytes"],
        values["process.launches"],
        values["memory.working_bytes_peak"],
        tuple(sorted(event.event_id for event in occurrence.shared_events)),
    )
    if result.route_input_bytes != len(occurrence.route_input_bytes):
        _fail("adaptive read-byte event differs from the frozen route input")
    constructed = occurrence.result_outcome == "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED"
    if constructed != (result.process_launches > 0 and result.staged_bytes > 0):
        _fail("adaptive worker launch/staging semantics changed")
    if any(ids[path] for path in ("io.output_bytes", "io.mounted_bytes_peak")):
        _fail("output or mounted receipt was emitted before fixed-point closure")
    return result


def _shared_values(
    measurement: AdaptiveSharedMeasurementV1,
    output_candidate: int,
) -> dict[str, int]:
    mounted = (
        measurement.route_input_bytes
        + measurement.staged_bytes
        + _nonnegative(output_candidate, "output candidate")
    )
    return {
        "common.hash_invocations": measurement.hash_invocations,
        "common.integrity_checks": measurement.integrity_checks,
        "common.protocol_checks": measurement.protocol_checks,
        "io.mounted_bytes_peak": mounted,
        "io.output_bytes": output_candidate,
        "io.read_bytes": measurement.route_input_bytes,
        "io.staged_bytes": measurement.staged_bytes,
        "memory.working_bytes_peak": max(
            measurement.working_bytes_peak_upper,
            mounted,
        ),
        "process.launches": measurement.process_launches,
    }


def _derived_values(
    occurrence: native_v1.AdaptiveOccurrenceNativeAccountingV1,
    process_launches: int,
) -> dict[str, int]:
    certified = occurrence.result_outcome != "NO_CERTIFIABLE_CONSTRUCTOR"
    return {
        "process.exit_failures": 0,
        "process.exit_successes": process_launches,
        "route.attempts": 1,
        "route.failures": 0 if certified else 1,
        "route.successes": 1 if certified else 0,
        "solver.attempts": 1 if certified else 0,
        "solver.failures": 0,
        "solver.successes": 1 if certified else 0,
    }


def _project_v7(
    vector: WorkVectorV1,
    comparison: registry_v7.ComparisonProfileV7,
) -> ComparisonVectorV1:
    axes = {axis: 0 for axis in SHARED_AXES}
    for term in comparison.terms:
        contribution = vector.values[term.source_leaf] * term.coefficient
        if term.reducer is ReducerEnum.SUM:
            axes[term.target_axis] += contribution
        else:
            axes[term.target_axis] = max(axes[term.target_axis], contribution)
    return ComparisonVectorV1(
        comparison.comparison_profile_id,
        vector.work_vector_id,
        vector.subject_id,
        vector.route_kind,
        tuple(sorted(axes.items())),
    )


def _materialize(
    occurrence: native_v1.AdaptiveOccurrenceNativeAccountingV1,
    measurement: AdaptiveSharedMeasurementV1,
    fixed_profile: fixed_v1.OutputBytesFixedPointProfileV1,
    output_candidate: int,
) -> _MaterializedV1:
    registry = registry_v7.official_counter_registry_v7()
    comparison = registry_v7.official_comparison_profile_v7(registry)
    actual = registry_v7.official_actual_projection_profile_v7(
        registry, comparison
    )
    shared_values = _shared_values(measurement, output_candidate)
    _native_values, event_ids = _event_reduction(occurrence)
    receipts: list[AdaptiveSharedReceiptV1] = []
    for path in SHARED_PATHS:
        native_ids = event_ids[path]
        if path == "io.output_bytes":
            kind = "OUTPUT_FIXED_POINT"
            source = fixed_profile.profile_id
        elif path == "io.mounted_bytes_peak":
            kind = "DERIVED_MOUNTED_BYTES_UPPER"
            source = measurement.measurement_id
        elif not native_ids and shared_values[path] == 0:
            kind = "COMPLETE_WINDOW_ZERO_ATTESTATION"
            source = measurement.measurement_id
        else:
            kind = "NATIVE_EVENT_REDUCTION"
            source = measurement.measurement_id
        receipts.append(
            AdaptiveSharedReceiptV1(
                occurrence.occurrence_id,
                measurement.measurement_id,
                path,
                registry.by_path[path].reducer,
                shared_values[path],
                kind,
                source,
                native_ids,
                fixed_profile.profile_id if path == "io.output_bytes" else None,
            )
        )
    receipt_set = AdaptiveSharedReceiptSetV1(
        occurrence.occurrence_id,
        measurement.measurement_id,
        tuple(receipts),
    )
    receipt_by_path = {row.path: row for row in receipts}
    component_by_path = tuple(
        {row.path: row for row in component.records}
        for component in occurrence.components
    )
    derived = _derived_values(occurrence, measurement.process_launches)
    aggregations: list[AdaptivePathAggregationV1] = []
    for path in registry.required_paths:
        leaf = registry.by_path[path]
        component_rows = tuple(
            rows[path] for rows in component_by_path if path in rows
        )
        if path in receipt_by_path:
            value = receipt_by_path[path].value
            kind = "SHARED_RESOURCE_RECEIPT"
            source = receipt_by_path[path].receipt_id
        elif path in derived:
            value = derived[path]
            kind = "SEMANTIC_DERIVED_RECONCILIATION"
            source = occurrence.occurrence_id
        elif leaf.reducer is ReducerEnum.SUM:
            value = sum(row.value for row in component_rows)
            kind = "COMPONENT_SUM"
            source = occurrence.occurrence_id
        else:
            value = max((row.value for row in component_rows), default=0)
            kind = "COMPONENT_MAX"
            source = occurrence.occurrence_id
        aggregations.append(
            AdaptivePathAggregationV1(
                occurrence.occurrence_id,
                path,
                leaf.reducer,
                value,
                tuple(row.record_id for row in component_rows),
                kind,
                source,
            )
        )
    aggregation_rows = tuple(aggregations)
    records = tuple(
        CounterRecordV1.observe(
            registry,
            row.path,
            row.value,
            recorder_id=row.aggregation_id,
        )
        for row in aggregation_rows
    )
    route = _route_kind(occurrence.result_outcome)
    vector = WorkVectorV1(
        registry.registry_id,
        occurrence.occurrence_id,
        route,
        records,
    )
    registry.validate_vector(vector)
    projected = _project_v7(vector, comparison)
    proof = ActualProjectionProofV1(
        actual.actual_projection_profile_id,
        registry.registry_id,
        comparison.comparison_profile_id,
        vector.work_vector_id,
        projected.comparison_vector_id,
        LaneEnum.OPERATIONAL,
        _work_scope(route),
        len(actual.terms),
    )
    return _MaterializedV1(
        receipt_set,
        aggregation_rows,
        vector,
        projected,
        proof,
    )


def _render(
    occurrence: native_v1.AdaptiveOccurrenceNativeAccountingV1,
    measurement: AdaptiveSharedMeasurementV1,
    fixed_profile: fixed_v1.OutputBytesFixedPointProfileV1,
    output_candidate: int,
) -> tuple[_MaterializedV1, Mapping[str, bytes]]:
    materialized = _materialize(
        occurrence,
        measurement,
        fixed_profile,
        output_candidate,
    )
    vector = materialized.work_vector
    comparison = materialized.comparison_vector
    proof = materialized.projection_proof
    certified = occurrence.result_outcome != "NO_CERTIFIABLE_CONSTRUCTOR"
    terminal_class = "PLAN_CERTIFICATE" if certified else "ATTEMPT_CLOSURE_NONCERTIFICATE"
    terminal_code = (
        "LOCAL_GROUND_RECOVERY"
        if vector.route_kind is RouteKindEnum.LOCAL_ATTEMPT
        else "ABSTRACT_CERTIFIED"
        if vector.route_kind is RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
        else "NO_CERTIFIABLE_CONSTRUCTOR"
    )
    roles: dict[str, bytes] = {}
    roles["BUSINESS_RESULT"] = canonical_json_bytes(
        {
            "artifact_role": "BUSINESS_RESULT",
            "schema": "acfqp.construction_k7_adaptive_business_result.v1",
            "adaptive_native_occurrence_id": occurrence.occurrence_id,
            "synthesis_result_id": occurrence.synthesis_result_id,
            "result_outcome": occurrence.result_outcome,
            "context_id": occurrence.context_id,
            "catalogue_id_before": occurrence.catalogue_id_before,
            "catalogue_id_after": occurrence.catalogue_id_after,
            "route_kind": vector.route_kind.value,
            "io.output_bytes": output_candidate,
        }
    )
    roles["OPERATIONAL_TRACE"] = canonical_json_bytes(
        {
            "artifact_role": "OPERATIONAL_TRACE",
            "schema": "acfqp.construction_k7_adaptive_operational_trace.v1",
            "native_component_ids": [row.component_id for row in occurrence.components],
            "native_shared_event_ids": [row.event_id for row in occurrence.shared_events],
            "shared_measurement": measurement.to_document(),
            "evaluation_replay_included": False,
        }
    )
    roles["TERMINAL_ARTIFACT"] = canonical_json_bytes(
        {
            "artifact_role": "TERMINAL_ARTIFACT",
            "schema": "acfqp.construction_k7_adaptive_terminal_artifact.v1",
            "occurrence_id": occurrence.occurrence_id,
            "terminal_scope": "LOGICAL_OCCURRENCE_CONSTRUCTION",
            "terminal_class": terminal_class,
            "terminal_code": terminal_code,
            "plan_certificate_present": certified,
            "work_vector_id": vector.work_vector_id,
            "comparison_vector_id": comparison.comparison_vector_id,
            "official_execution_allowed": False,
        }
    )
    roles["COUNTER_RECORD_SET"] = canonical_json_bytes(
        {
            "artifact_role": "COUNTER_RECORD_SET",
            "schema": "acfqp.construction_k7_adaptive_counter_record_set.v1",
            "io.output_bytes": output_candidate,
            "shared_resource_receipt_set": materialized.receipt_set.to_document(),
            "shared_resource_receipts": [
                row.to_document() for row in materialized.receipt_set.receipts
            ],
            "path_aggregation_ids": [
                row.aggregation_id for row in materialized.aggregations
            ],
            "counter_record_ids": [row.record_id for row in vector.records],
            "counter_record_count": len(vector.records),
        }
    )
    roles["WORK_VECTOR"] = canonical_json_bytes(
        {
            "artifact_role": "WORK_VECTOR",
            "schema": "acfqp.construction_k7_adaptive_work_vector_artifact.v1",
            "io.output_bytes": output_candidate,
            "work_vector": vector.to_dict(),
        }
    )
    roles["COMPARISON_VECTOR"] = canonical_json_bytes(
        {
            "artifact_role": "COMPARISON_VECTOR",
            "schema": "acfqp.construction_k7_adaptive_comparison_vector_artifact.v1",
            "io.output_bytes": output_candidate,
            "comparison_vector": comparison.to_dict(),
            "route_choice_authority": False,
        }
    )
    roles["ACTUAL_PROJECTION_PROOF"] = canonical_json_bytes(
        {
            "artifact_role": "ACTUAL_PROJECTION_PROOF",
            "schema": "acfqp.construction_k7_adaptive_projection_artifact.v1",
            "io.output_bytes": output_candidate,
            "actual_projection_proof": proof.to_dict(),
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
            "schema": "acfqp.construction_k7_adaptive_output_manifest.v1",
            "occurrence_id": occurrence.occurrence_id,
            "output_bytes_fixed_point_profile_id": fixed_profile.profile_id,
            "io.output_bytes": output_candidate,
            "ordered_preceding_roles": preceding,
            "required_role_order": list(
                fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
            ),
        }
    )
    if tuple(roles) != fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES:
        _fail("adaptive output role order changed")
    return materialized, MappingProxyType(roles)


def _fixed_profile(
    occurrence: native_v1.AdaptiveOccurrenceNativeAccountingV1,
    measurement: AdaptiveSharedMeasurementV1,
) -> fixed_v1.OutputBytesFixedPointProfileV1:
    renderer_id = content_id(
        RENDERER_DOMAIN,
        {
            "occurrence_id": occurrence.occurrence_id,
            "shared_measurement_id": measurement.measurement_id,
            "required_roles": list(fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES),
        },
    )
    return fixed_v1.freeze_output_bytes_fixed_point_profile_v1(
        renderer_id=renderer_id,
        execution_identity_id=occurrence.occurrence_id,
        max_total_bytes=512 * 1024 * 1024,
        role_byte_caps={
            role: 256 * 1024 * 1024
            for role in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
        },
        max_iterations=32,
    )


def _commit(
    occurrence_id: str,
    fixed_point: fixed_v1.OutputBytesFixedPointResultV1,
    output: Path,
) -> AdaptiveOutputCommitV1:
    if output.exists():
        _fail("adaptive occurrence output directory must be absent")
    output.mkdir(mode=0o700, parents=False)
    rows: list[tuple[str, int, str]] = []
    directory_fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for role in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES:
            raw = fixed_point.artifact_bytes_by_role[role]
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
                        _fail("adaptive output role write made no progress")
                    view = view[written:]
                os.fsync(fd)
            finally:
                os.close(fd)
            row_stat = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
            if not stat.S_ISREG(row_stat.st_mode) or row_stat.st_size != len(raw):
                _fail("adaptive output role readback changed")
            rows.append((role, len(raw), hashlib.sha256(raw).hexdigest()))
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return AdaptiveOutputCommitV1(
        occurrence_id,
        fixed_point.result_id,
        str(output.resolve()),
        tuple(rows),
    )


@dataclass(frozen=True, slots=True)
class AdaptiveOccurrenceActualAccountingV1:
    native_occurrence: native_v1.AdaptiveOccurrenceNativeAccountingV1 = field(
        repr=False, compare=False
    )
    measurement: AdaptiveSharedMeasurementV1
    fixed_point: fixed_v1.OutputBytesFixedPointResultV1 = field(
        repr=False, compare=False
    )
    output_commit: AdaptiveOutputCommitV1
    receipt_set: AdaptiveSharedReceiptSetV1 = field(repr=False)
    aggregations: tuple[AdaptivePathAggregationV1, ...] = field(repr=False)
    work_vector: WorkVectorV1 = field(repr=False)
    comparison_vector: ComparisonVectorV1 = field(repr=False)
    projection_proof: ActualProjectionProofV1 = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.native_occurrence)
            is not native_v1.AdaptiveOccurrenceNativeAccountingV1
            or self.measurement.occurrence_id != self.native_occurrence.occurrence_id
            or self.receipt_set.occurrence_id != self.native_occurrence.occurrence_id
            or len(self.aggregations) != EXPECTED_REQUIRED_PATH_COUNT
            or len(self.work_vector.records) != EXPECTED_REQUIRED_PATH_COUNT
            or self.work_vector.route_kind
            is not _route_kind(self.native_occurrence.result_outcome)
            or self.comparison_vector.work_vector_id != self.work_vector.work_vector_id
            or self.projection_proof.work_vector_id != self.work_vector.work_vector_id
            or self.projection_proof.projection_term_count
            != EXPECTED_OPERATIONAL_PATH_COUNT
            or self.work_vector.values["io.output_bytes"]
            != self.fixed_point.output_bytes
            or self.output_commit.fixed_point_result_id != self.fixed_point.result_id
        ):
            _fail("adaptive occurrence actual-accounting bundle is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_adaptive_occurrence_accounting.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.native_occurrence.occurrence_id,
            "adaptive_native_occurrence_id": self.native_occurrence.occurrence_id,
            "shared_measurement_id": self.measurement.measurement_id,
            "shared_resource_receipt_set_id": self.receipt_set.receipt_set_id,
            "shared_resource_receipt_ids": [
                row.receipt_id for row in self.receipt_set.receipts
            ],
            "path_aggregation_ids": [row.aggregation_id for row in self.aggregations],
            "work_vector_id": self.work_vector.work_vector_id,
            "comparison_vector_id": self.comparison_vector.comparison_vector_id,
            "actual_projection_proof_id": self.projection_proof.actual_projection_proof_id,
            "output_bytes_fixed_point_result_id": self.fixed_point.result_id,
            "output_commit_id": self.output_commit.output_commit_id,
            "route_kind": self.work_vector.route_kind.value,
            "counter_record_count": len(self.work_vector.records),
            "operational_projection_term_count": self.projection_proof.projection_term_count,
            "shared_resource_receipts_complete": True,
            "formal_work_vector_issued": True,
            "formal_comparison_vector_issued": True,
            "independent_bundle_verification_present": False,
            "counter_completeness_gate_status": "NOT_RUN",
            "official_execution_allowed": False,
        }

    @property
    def occurrence_accounting_id(self) -> str:
        return content_id(OCCURRENCE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_accounting_id": self.occurrence_accounting_id}


@dataclass(frozen=True, slots=True)
class AdaptiveCampaignActualAccountingV1:
    native_campaign: native_v1.AdaptiveCampaignNativeAccountingResultV1 = field(
        repr=False, compare=False
    )
    occurrences: tuple[AdaptiveOccurrenceActualAccountingV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.native_campaign)
            is not native_v1.AdaptiveCampaignNativeAccountingResultV1
            or len(self.occurrences) != 5
            or tuple(row.native_occurrence for row in self.occurrences)
            != self.native_campaign.occurrences
        ):
            _fail("adaptive campaign actual-accounting chain changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_adaptive_campaign_accounting.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "adaptive_native_campaign_id": self.native_campaign.campaign_id,
            "occurrence_accounting_ids": [
                row.occurrence_accounting_id for row in self.occurrences
            ],
            "logical_occurrence_count": len(self.occurrences),
            "route_kind_sequence": [
                row.work_vector.route_kind.value for row in self.occurrences
            ],
            "all_nine_shared_receipt_sets_present": True,
            "formal_work_vectors_issued": True,
            "formal_comparison_vectors_issued": True,
            "independent_complete_bundle_verifier_present": False,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }

    @property
    def campaign_accounting_id(self) -> str:
        return content_id(CAMPAIGN_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_accounting_id": self.campaign_accounting_id}


def verify_adaptive_occurrence_actual_accounting_v1(
    bundle: AdaptiveOccurrenceActualAccountingV1,
) -> AdaptiveOccurrenceActualAccountingV1:
    if type(bundle) is not AdaptiveOccurrenceActualAccountingV1:
        _fail("adaptive occurrence verifier rejects foreign values")
    expected_measurement = _measurement(bundle.native_occurrence)
    profile = _fixed_profile(bundle.native_occurrence, expected_measurement)

    def renderer(candidate: int) -> dict[str, bytes]:
        return dict(
            _render(
                bundle.native_occurrence,
                expected_measurement,
                profile,
                candidate,
            )[1]
        )

    fixed_v1.replay_output_bytes_fixed_point_v1(
        result=bundle.fixed_point,
        renderer=renderer,
    )
    expected, role_bytes = _render(
        bundle.native_occurrence,
        expected_measurement,
        profile,
        bundle.fixed_point.output_bytes,
    )
    registry = registry_v7.official_counter_registry_v7()
    comparison = registry_v7.official_comparison_profile_v7(registry)
    actual = registry_v7.official_actual_projection_profile_v7(registry, comparison)
    registry.validate_vector(expected.work_vector)
    comparison.validate(registry)
    actual.validate(registry, comparison)
    if _project_v7(expected.work_vector, comparison) != expected.comparison_vector:
        _fail("adaptive V7 comparison projection replay changed")
    commit_by_role = {row[0]: row for row in bundle.output_commit.role_rows}
    if (
        expected_measurement != bundle.measurement
        or expected.receipt_set != bundle.receipt_set
        or expected.aggregations != bundle.aggregations
        or expected.work_vector != bundle.work_vector
        or expected.comparison_vector != bundle.comparison_vector
        or expected.projection_proof != bundle.projection_proof
        or profile != bundle.fixed_point.profile
        or dict(role_bytes) != bundle.fixed_point.artifact_bytes_by_role
        or any(
            commit_by_role[role][1:]
            != (len(raw), hashlib.sha256(raw).hexdigest())
            for role, raw in role_bytes.items()
        )
    ):
        _fail("adaptive occurrence artifacts differ from exact replay")
    return bundle


def run_adaptive_campaign_actual_accounting_v1(
    *, output_root: str | Path
) -> AdaptiveCampaignActualAccountingV1:
    root = Path(output_root)
    if root.exists():
        _fail("adaptive campaign output root must be absent")
    root.mkdir(mode=0o700, parents=False)
    native = native_v1.run_adaptive_campaign_native_accounting_v1()
    results: list[AdaptiveOccurrenceActualAccountingV1] = []
    for occurrence in native.occurrences:
        measurement = _measurement(occurrence)
        profile = _fixed_profile(occurrence, measurement)

        def renderer(candidate: int) -> dict[str, bytes]:
            return dict(_render(occurrence, measurement, profile, candidate)[1])

        fixed_point = fixed_v1.solve_output_bytes_fixed_point_v1(
            profile=profile,
            renderer=renderer,
        )
        fixed_v1.replay_output_bytes_fixed_point_v1(
            result=fixed_point,
            renderer=renderer,
        )
        materialized, role_bytes = _render(
            occurrence,
            measurement,
            profile,
            fixed_point.output_bytes,
        )
        if dict(role_bytes) != fixed_point.artifact_bytes_by_role:
            _fail("adaptive final render differs from fixed-point bytes")
        commit = _commit(
            occurrence.occurrence_id,
            fixed_point,
            root / f"{occurrence.occurrence_index:04d}-{occurrence.occurrence_role}",
        )
        result = AdaptiveOccurrenceActualAccountingV1(
            occurrence,
            measurement,
            fixed_point,
            commit,
            materialized.receipt_set,
            materialized.aggregations,
            materialized.work_vector,
            materialized.comparison_vector,
            materialized.projection_proof,
        )
        results.append(verify_adaptive_occurrence_actual_accounting_v1(result))
    return AdaptiveCampaignActualAccountingV1(native, tuple(results))


__all__ = (
    "AdaptiveCampaignActualAccountingV1",
    "AdaptiveOccurrenceActualAccountingV1",
    "AdaptiveOutputCommitV1",
    "AdaptivePathAggregationV1",
    "AdaptiveSharedMeasurementV1",
    "AdaptiveSharedReceiptSetV1",
    "AdaptiveSharedReceiptV1",
    "ConstructionK7AdaptiveCampaignActualAccountingV1Error",
    "LOCAL_DOMAINS",
    "run_adaptive_campaign_actual_accounting_v1",
    "verify_adaptive_occurrence_actual_accounting_v1",
)
