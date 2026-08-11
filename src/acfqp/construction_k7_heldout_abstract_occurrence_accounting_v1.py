"""Formal occurrence accounting for fresh held-out abstract reuse.

The input is one already-issued held-out overlay-reuse result.  The only
operational planner replay is performed by the owner-bound stage recorder.
This module closes that same-process measurement window, replaces all nine
shared-resource stage placeholders, and emits one complete
CounterRecord -> WorkVector -> ComparisonVector chain for an
``ABSTRACT_ONLY_CERTIFICATE`` route.  The independent portable replay stays
outside the operational lane.

This remains a construction-only occurrence artifact.  It does not close a
campaign, run either economics gate, or authorize official execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import resource
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
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualWorkScope,
    verify_actual_projection_v1,
)
from acfqp import construction_accounting_live_v3 as live_v3
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_heldout_overlay_abstract_reuse_v1 as reuse_v1
from acfqp import construction_k7_heldout_abstract_stage_accounting_v1 as stage_v1
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp import construction_shared_resource_receipts_v1 as shared_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_OCCURRENCE_ACCOUNTING_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_OUTPUT_COMMIT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_OUTPUT_RENDERER_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_PATH_AGGREGATION_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_SHARED_MEASUREMENT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_SHARED_RECEIPT_SET_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_SHARED_RECEIPT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.123"
PROFILE_KEY = "construction_k7_heldout_abstract_occurrence_accounting_v1"
MEASUREMENT_DOMAIN = CONSTRUCTION_K7_HELDOUT_ABSTRACT_SHARED_MEASUREMENT_V1_DOMAIN
RECEIPT_DOMAIN = CONSTRUCTION_K7_HELDOUT_ABSTRACT_SHARED_RECEIPT_V1_DOMAIN
RECEIPT_SET_DOMAIN = (
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_SHARED_RECEIPT_SET_V1_DOMAIN
)
AGGREGATION_DOMAIN = CONSTRUCTION_K7_HELDOUT_ABSTRACT_PATH_AGGREGATION_V1_DOMAIN
BUNDLE_DOMAIN = CONSTRUCTION_K7_HELDOUT_ABSTRACT_OCCURRENCE_ACCOUNTING_V1_DOMAIN
RENDERER_DOMAIN = CONSTRUCTION_K7_HELDOUT_ABSTRACT_OUTPUT_RENDERER_V1_DOMAIN
OUTPUT_COMMIT_DOMAIN = CONSTRUCTION_K7_HELDOUT_ABSTRACT_OUTPUT_COMMIT_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {
        MEASUREMENT_DOMAIN,
        RECEIPT_DOMAIN,
        RECEIPT_SET_DOMAIN,
        AGGREGATION_DOMAIN,
        BUNDLE_DOMAIN,
        RENDERER_DOMAIN,
        OUTPUT_COMMIT_DOMAIN,
    }
)
if len(LOCAL_DOMAINS) != 7 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("held-out occurrence-accounting domains are not central")

SHARED_PATHS = shared_v1.SHARED_RESOURCE_PATHS
EXPECTED_STAGE_COUNT = stage_v1.EXPECTED_STAGE_COUNT
EXPECTED_REQUIRED_PATH_COUNT = registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
EXPECTED_OPERATIONAL_PATH_COUNT = registry_v6.EXPECTED_V6_OPERATIONAL_LEAF_COUNT
EXPECTED_SHARED_PATH_COUNT = len(SHARED_PATHS)


class ConstructionK7HeldoutAbstractOccurrenceAccountingV1Error(RuntimeError):
    """The shared measurement, reduction, fixed point, or commit failed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutAbstractOccurrenceAccountingV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutAbstractOccurrenceAccountingV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _peak_working_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports KiB; the project runtime is Linux-only.  Treat the
    # process-wide high-water mark as a conservative same-process upper bound.
    return max(1, int(value) * 1024)


@dataclass(frozen=True, slots=True)
class HeldoutAbstractSharedMeasurementV1:
    occurrence_id: str
    reuse_result_id: str
    stage_accounting_id: str
    input_bytes_sha256: str
    read_bytes: int
    business_hash_invocations: int
    integrity_checks: int
    protocol_checks: int
    pre_output_mounted_bytes: int
    pre_output_working_bytes_peak: int

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "measurement occurrence"),
            (self.reuse_result_id, "measurement result"),
            (self.stage_accounting_id, "measurement stage accounting"),
            (self.input_bytes_sha256, "measurement input digest"),
        ):
            _cid(value, label)
        for value, label in (
            (self.read_bytes, "read bytes"),
            (self.business_hash_invocations, "business hash invocations"),
            (self.integrity_checks, "integrity checks"),
            (self.protocol_checks, "protocol checks"),
            (self.pre_output_mounted_bytes, "pre-output mounted bytes"),
            (self.pre_output_working_bytes_peak, "pre-output working bytes"),
        ):
            _nonnegative(value, label)
        if (
            self.read_bytes <= 0
            or self.business_hash_invocations <= 0
            or self.integrity_checks <= 0
            or self.protocol_checks <= 0
            or self.pre_output_mounted_bytes != self.read_bytes
            or self.pre_output_working_bytes_peak <= 0
        ):
            _fail("held-out complete-window measurement is not substantive")

    def mounted_bytes_peak(self, output_bytes: int) -> int:
        return self.pre_output_mounted_bytes + _nonnegative(
            output_bytes, "mounted output candidate"
        )

    def working_bytes_peak(self, output_bytes: int) -> int:
        return max(
            self.pre_output_working_bytes_peak,
            self.mounted_bytes_peak(output_bytes),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_shared_measurement.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "heldout_abstract_reuse_result_id": self.reuse_result_id,
            "heldout_abstract_stage_accounting_id": self.stage_accounting_id,
            "input_bytes_sha256": self.input_bytes_sha256,
            "io.read_bytes": self.read_bytes,
            "common.hash_invocations": self.business_hash_invocations,
            "common.integrity_checks": self.integrity_checks,
            "common.protocol_checks": self.protocol_checks,
            "pre_output_mounted_bytes": self.pre_output_mounted_bytes,
            "pre_output_working_bytes_peak": self.pre_output_working_bytes_peak,
            "io.staged_bytes": 0,
            "process.launches": 0,
            "same_process_no_staging": True,
            "route_input_envelope_only": True,
            "source_observation_archive_not_read": True,
            "business_hashes_exclude_accounting_serialization": True,
            "independent_portable_replay_in_operational_window": False,
            "complete_window_closed": True,
            "official_execution_allowed": False,
        }

    @property
    def measurement_id(self) -> str:
        return content_id(MEASUREMENT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "shared_measurement_id": self.measurement_id}


@dataclass(frozen=True, slots=True)
class HeldoutAbstractSharedReceiptV1:
    occurrence_id: str
    measurement_id: str
    path: str
    reducer: ReducerEnum
    value: int
    source_evidence_id: str
    stage_placeholder_record_ids: tuple[str, ...]
    fixed_point_profile_id: str | None = None

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "receipt occurrence")
        _cid(self.measurement_id, "receipt measurement")
        _cid(self.source_evidence_id, "receipt source")
        object.__setattr__(self, "reducer", ReducerEnum(self.reducer))
        _nonnegative(self.value, "receipt value")
        if (
            self.path not in SHARED_PATHS
            or type(self.stage_placeholder_record_ids) is not tuple
            or len(self.stage_placeholder_record_ids) != EXPECTED_STAGE_COUNT
        ):
            _fail("held-out shared receipt shape changed")
        for value in self.stage_placeholder_record_ids:
            _cid(value, "stage placeholder record")
        is_output = self.path == "io.output_bytes"
        if (self.fixed_point_profile_id is not None) != is_output:
            _fail("output receipt fixed-point binding changed")
        if self.fixed_point_profile_id is not None:
            _cid(self.fixed_point_profile_id, "receipt fixed-point profile")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_shared_receipt.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "shared_measurement_id": self.measurement_id,
            "path": self.path,
            "reducer": self.reducer.value,
            "value": self.value,
            "source_kind": (
                "OUTPUT_FIXED_POINT"
                if self.path == "io.output_bytes"
                else "COMPLETE_WINDOW_MEASUREMENT"
            ),
            "source_evidence_id": self.source_evidence_id,
            "stage_placeholder_record_ids": list(self.stage_placeholder_record_ids),
            "output_fixed_point_profile_id": self.fixed_point_profile_id,
            "stage_placeholders_replaced_not_summed": True,
            "official_execution_allowed": False,
        }

    @property
    def receipt_id(self) -> str:
        return content_id(RECEIPT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "shared_resource_receipt_id": self.receipt_id}


@dataclass(frozen=True, slots=True)
class HeldoutAbstractSharedReceiptSetV1:
    occurrence_id: str
    measurement_id: str
    receipts: tuple[HeldoutAbstractSharedReceiptV1, ...]

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "receipt-set occurrence")
        _cid(self.measurement_id, "receipt-set measurement")
        if (
            tuple(row.path for row in self.receipts) != SHARED_PATHS
            or any(
                type(row) is not HeldoutAbstractSharedReceiptV1
                or row.occurrence_id != self.occurrence_id
                or row.measurement_id != self.measurement_id
                for row in self.receipts
            )
        ):
            _fail("held-out receipt set does not cover the exact nine paths")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_shared_receipt_set.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "shared_measurement_id": self.measurement_id,
            "shared_resource_paths": list(SHARED_PATHS),
            "shared_resource_receipt_ids": [row.receipt_id for row in self.receipts],
            "receipt_count": EXPECTED_SHARED_PATH_COUNT,
            "all_nine_shared_paths_complete": True,
            "official_execution_allowed": False,
        }

    @property
    def receipt_set_id(self) -> str:
        return content_id(RECEIPT_SET_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "shared_resource_receipt_set_id": self.receipt_set_id}


@dataclass(frozen=True, slots=True)
class HeldoutAbstractPathAggregationV1:
    occurrence_id: str
    path: str
    reducer: ReducerEnum
    value: int
    stage_record_ids: tuple[str, ...]
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
            or len(self.stage_record_ids) != EXPECTED_STAGE_COUNT
            or self.source_kind not in {"STAGE_SUM", "STAGE_MAX", "SHARED_RECEIPT"}
        ):
            _fail("held-out path aggregation shape changed")
        for value in self.stage_record_ids:
            _cid(value, "aggregation stage record")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_path_aggregation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "path": self.path,
            "reducer": self.reducer.value,
            "value": self.value,
            "stage_record_ids": list(self.stage_record_ids),
            "source_kind": self.source_kind,
            "source_evidence_id": self.source_evidence_id,
            "shared_stage_placeholders_replaced_not_summed": self.path in SHARED_PATHS,
        }

    @property
    def aggregation_id(self) -> str:
        return content_id(AGGREGATION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "path_aggregation_id": self.aggregation_id}


@dataclass(frozen=True, slots=True)
class _MaterializedCandidateV1:
    receipt_set: HeldoutAbstractSharedReceiptSetV1
    aggregations: tuple[HeldoutAbstractPathAggregationV1, ...]
    work_vector: WorkVectorV1
    comparison_vector: ComparisonVectorV1
    projection_proof: ActualProjectionProofV1


def _verified_stage_chain(
    stage: stage_v1.HeldoutAbstractStageAccountingResultV1,
) -> tuple[Any, Any, Any, tuple[live_v3.RecordedStageWorkV3, ...]]:
    stage_v1.verify_heldout_abstract_stage_accounting_v1(stage)
    registry = registry_v6.official_counter_registry_v6()
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(registry, comparison)
    rows = stage.recorded_stages
    if (
        len(rows) != EXPECTED_STAGE_COUNT
        or any(row.work_vector.values[path] != 0 for row in rows for path in SHARED_PATHS)
    ):
        _fail("held-out stage chain no longer has nine explicit placeholders")
    return registry, comparison, actual, rows


def _shared_values(
    measurement: HeldoutAbstractSharedMeasurementV1,
    output_candidate: int,
) -> dict[str, int]:
    return {
        "common.hash_invocations": measurement.business_hash_invocations,
        "common.integrity_checks": measurement.integrity_checks,
        "common.protocol_checks": measurement.protocol_checks,
        "io.mounted_bytes_peak": measurement.mounted_bytes_peak(output_candidate),
        "io.output_bytes": _nonnegative(output_candidate, "output candidate"),
        "io.read_bytes": measurement.read_bytes,
        "io.staged_bytes": 0,
        "memory.working_bytes_peak": measurement.working_bytes_peak(output_candidate),
        "process.launches": 0,
    }


def _materialize_candidate(
    *,
    stage: stage_v1.HeldoutAbstractStageAccountingResultV1,
    measurement: HeldoutAbstractSharedMeasurementV1,
    fixed_profile: fixed_v1.OutputBytesFixedPointProfileV1,
    output_candidate: int,
    verified: tuple[Any, Any, Any, tuple[live_v3.RecordedStageWorkV3, ...]],
) -> _MaterializedCandidateV1:
    registry, comparison, actual, stages = verified
    occurrence_id = stage.reuse_result.query.logical_occurrence_id
    stage_id = stage.result_id
    measurement_id = measurement.measurement_id
    fixed_profile_id = fixed_profile.profile_id
    if (
        fixed_profile.execution_identity_id != stage_id
        or measurement.occurrence_id != occurrence_id
        or measurement.stage_accounting_id != stage_id
    ):
        _fail("held-out fixed point crossed its occurrence or stage authority")
    records_by_path = tuple(
        {record.path: record for record in row.work_vector.records} for row in stages
    )
    if any(tuple(sorted(rows)) != registry.required_paths for rows in records_by_path):
        _fail("held-out stage record inventory changed")
    shared_values = _shared_values(measurement, output_candidate)
    receipts = tuple(
        HeldoutAbstractSharedReceiptV1(
            occurrence_id,
            measurement_id,
            path,
            registry.by_path[path].reducer,
            shared_values[path],
            fixed_profile_id if path == "io.output_bytes" else measurement_id,
            tuple(rows[path].record_id for rows in records_by_path),
            fixed_profile_id if path == "io.output_bytes" else None,
        )
        for path in SHARED_PATHS
    )
    receipt_set = HeldoutAbstractSharedReceiptSetV1(
        occurrence_id, measurement_id, receipts
    )
    receipt_by_path = {row.path: row for row in receipts}
    aggregations: list[HeldoutAbstractPathAggregationV1] = []
    for path in registry.required_paths:
        leaf = registry.by_path[path]
        stage_records = tuple(rows[path] for rows in records_by_path)
        if path in receipt_by_path:
            receipt = receipt_by_path[path]
            value = receipt.value
            kind = "SHARED_RECEIPT"
            source_id = receipt.receipt_id
        elif leaf.reducer is ReducerEnum.SUM:
            value = sum(row.value for row in stage_records)
            kind = "STAGE_SUM"
            source_id = stage_id
        else:
            value = max(row.value for row in stage_records)
            kind = "STAGE_MAX"
            source_id = stage_id
        aggregations.append(
            HeldoutAbstractPathAggregationV1(
                occurrence_id,
                path,
                leaf.reducer,
                value,
                tuple(row.record_id for row in stage_records),
                kind,
                source_id,
            )
        )
    aggregation_rows = tuple(aggregations)
    if (
        len(aggregation_rows) != EXPECTED_REQUIRED_PATH_COUNT
        or tuple(row.path for row in aggregation_rows) != registry.required_paths
    ):
        _fail("held-out occurrence path aggregation is incomplete")
    registry_id = registry.registry_id
    records = tuple(
        CounterRecordV1(
            registry_id,
            row.path,
            row.value,
            True,
            row.aggregation_id,
            registry.by_path[row.path].semantics_id,
            registry.by_path[row.path].owner,
            registry.by_path[row.path].unit,
            registry.by_path[row.path].lane,
            registry.by_path[row.path].scope,
            registry.by_path[row.path].reducer,
        )
        for row in aggregation_rows
    )
    vector = WorkVectorV1(
        registry_id,
        occurrence_id,
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        records,
    )
    registry.validate_vector(vector)
    axes = {axis: 0 for axis in SHARED_AXES}
    for term in actual.terms:
        contribution = vector.values[term.source_leaf] * term.coefficient
        if term.reducer is ReducerEnum.SUM:
            axes[term.target_axis] += contribution
        else:
            axes[term.target_axis] = max(axes[term.target_axis], contribution)
    projected = ComparisonVectorV1(
        comparison.comparison_profile_id,
        vector.work_vector_id,
        vector.subject_id,
        vector.route_kind,
        tuple(sorted(axes.items())),
    )
    proof = ActualProjectionProofV1(
        actual.actual_projection_profile_id,
        registry_id,
        comparison.comparison_profile_id,
        vector.work_vector_id,
        projected.comparison_vector_id,
        LaneEnum.OPERATIONAL,
        ActualWorkScope.COMMON_PREFIX,
        len(actual.terms),
    )
    if (
        len(records) != EXPECTED_REQUIRED_PATH_COUNT
        or proof.projection_term_count != EXPECTED_OPERATIONAL_PATH_COUNT
        or any(
            value != 0
            for path, value in vector.values.items()
            if path.startswith(("local.", "fallback.", "rebuild."))
        )
    ):
        _fail("held-out abstract-only WorkVector changed route family")
    return _MaterializedCandidateV1(
        receipt_set,
        aggregation_rows,
        vector,
        projected,
        proof,
    )


@dataclass(frozen=True, slots=True)
class _RenderedCandidateV1:
    materialized: _MaterializedCandidateV1
    role_bytes: Mapping[str, bytes]


def _static_role_bytes(
    stage: stage_v1.HeldoutAbstractStageAccountingResultV1,
) -> Mapping[str, bytes]:
    result = stage.reuse_result
    return MappingProxyType(
        {
            "BUSINESS_RESULT": canonical_json_bytes(
                {
                    "artifact_role": "BUSINESS_RESULT",
                    "schema": "acfqp.construction_k7_heldout_abstract_business_result.v1",
                    "schema_version": SCHEMA_VERSION,
                    "profile_key": PROFILE_KEY,
                    "occurrence_id": result.query.logical_occurrence_id,
                    "heldout_abstract_reuse_result_id": result.result_id,
                    "source_result_id": result.source.result_id,
                    "source_overlay_id": result.source.final_overlay.overlay_id,
                    "quotient_model_id": (
                        result.source.final_overlay.bridge.quotient_model.model_id
                    ),
                    "fresh_query_id": result.query.query_id,
                    "fresh_abstract_plan_id": result.plan.plan_id,
                    "fresh_robust_audit_id": result.plan.audit.audit_id,
                    "route_kind": RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE.value,
                    "fresh_ground_or_observer_event_count": 0,
                    "construction_only": True,
                    "official_execution_allowed": False,
                }
            ),
            "OPERATIONAL_TRACE": canonical_json_bytes(
                {
                    "artifact_role": "OPERATIONAL_TRACE",
                    "schema": "acfqp.construction_k7_heldout_abstract_operational_trace.v1",
                    "schema_version": SCHEMA_VERSION,
                    "profile_key": PROFILE_KEY,
                    "heldout_abstract_stage_accounting": stage.to_document(),
                    "independent_evaluation_replay_included": False,
                }
            ),
        }
    )


def _render_candidate(
    *,
    stage: stage_v1.HeldoutAbstractStageAccountingResultV1,
    measurement: HeldoutAbstractSharedMeasurementV1,
    fixed_profile: fixed_v1.OutputBytesFixedPointProfileV1,
    output_candidate: int,
    verified: tuple[Any, Any, Any, tuple[live_v3.RecordedStageWorkV3, ...]],
    static_role_bytes: Mapping[str, bytes],
) -> _RenderedCandidateV1:
    materialized = _materialize_candidate(
        stage=stage,
        measurement=measurement,
        fixed_profile=fixed_profile,
        output_candidate=output_candidate,
        verified=verified,
    )
    vector = materialized.work_vector
    comparison = materialized.comparison_vector
    proof = materialized.projection_proof
    roles: dict[str, bytes] = dict(static_role_bytes)
    roles["TERMINAL_ARTIFACT"] = canonical_json_bytes(
        {
            "artifact_role": "TERMINAL_ARTIFACT",
            "schema": "acfqp.construction_k7_heldout_abstract_terminal_artifact.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": vector.subject_id,
            "work_vector_id": vector.work_vector_id,
            "comparison_vector_id": comparison.comparison_vector_id,
            "actual_projection_proof_id": proof.actual_projection_proof_id,
            "io.output_bytes": output_candidate,
            "terminal_scope": "LOGICAL_OCCURRENCE_CONSTRUCTION",
            "terminal_class": "PLAN_CERTIFICATE",
            "terminal_code": "ABSTRACT_CERTIFIED",
            "fresh_abstract_plan_certified": True,
            "local_recovery_executed": False,
            "direct_ground_fallback_executed": False,
            "campaign_closure_issued": False,
            "official_certificate_coverage_authority": False,
            "official_execution_allowed": False,
        }
    )
    roles["COUNTER_RECORD_SET"] = canonical_json_bytes(
        {
            "artifact_role": "COUNTER_RECORD_SET",
            "schema": "acfqp.construction_k7_heldout_abstract_counter_record_set.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": vector.subject_id,
            "io.output_bytes": output_candidate,
            "shared_measurement": measurement.to_document(),
            "shared_resource_receipt_set": materialized.receipt_set.to_document(),
            "shared_resource_receipts": [
                row.to_document() for row in materialized.receipt_set.receipts
            ],
            "path_aggregations": [row.to_document() for row in materialized.aggregations],
            "counter_record_count": len(vector.records),
            "counter_records": [row.to_dict() for row in vector.records],
        }
    )
    roles["WORK_VECTOR"] = canonical_json_bytes(
        {
            "artifact_role": "WORK_VECTOR",
            "schema": "acfqp.construction_k7_heldout_abstract_work_vector_artifact.v1",
            "io.output_bytes": output_candidate,
            "route_kind": RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE.value,
            "local_fallback_rebuild_native_zero": True,
            "work_vector": vector.to_dict(),
        }
    )
    roles["COMPARISON_VECTOR"] = canonical_json_bytes(
        {
            "artifact_role": "COMPARISON_VECTOR",
            "schema": "acfqp.construction_k7_heldout_abstract_comparison_vector_artifact.v1",
            "io.output_bytes": output_candidate,
            "route_choice_authority": False,
            "comparison_vector": comparison.to_dict(),
        }
    )
    roles["ACTUAL_PROJECTION_PROOF"] = canonical_json_bytes(
        {
            "artifact_role": "ACTUAL_PROJECTION_PROOF",
            "schema": "acfqp.construction_k7_heldout_abstract_projection_artifact.v1",
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
            "schema": "acfqp.construction_k7_heldout_abstract_output_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": vector.subject_id,
            "output_bytes_fixed_point_profile_id": fixed_profile.profile_id,
            "io.output_bytes": output_candidate,
            "ordered_preceding_roles": preceding,
            "required_role_order": list(fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES),
            "output_manifest_self_extent_excluded_from_preceding_rows": True,
        }
    )
    if tuple(roles) != fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES:
        _fail("held-out output role order changed")
    return _RenderedCandidateV1(materialized, MappingProxyType(roles))


@dataclass(frozen=True, slots=True)
class HeldoutAbstractOutputRoleCommitV1:
    artifact_role: str
    filename: str
    byte_count: int
    bytes_sha256: str

    def __post_init__(self) -> None:
        if (
            self.artifact_role not in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
            or self.filename != f"{self.artifact_role}.json"
            or type(self.byte_count) is not int
            or self.byte_count <= 0
        ):
            _fail("held-out output role commit is malformed")
        _cid(self.bytes_sha256, "output role digest")

    def to_document(self) -> dict[str, Any]:
        return {
            "artifact_role": self.artifact_role,
            "filename": self.filename,
            "byte_count": self.byte_count,
            "bytes_sha256": self.bytes_sha256,
            "regular_file": True,
            "file_fsync_completed": True,
        }


@dataclass(frozen=True, slots=True)
class HeldoutAbstractOutputCommitV1:
    occurrence_id: str
    fixed_point_result_id: str
    measurement_id: str
    role_commits: tuple[HeldoutAbstractOutputRoleCommitV1, ...]
    output_bytes: int

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "output occurrence")
        _cid(self.fixed_point_result_id, "output fixed point")
        _cid(self.measurement_id, "output measurement")
        if (
            tuple(row.artifact_role for row in self.role_commits)
            != fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
            or sum(row.byte_count for row in self.role_commits) != self.output_bytes
            or self.output_bytes <= 0
        ):
            _fail("held-out output commit inventory changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_output_commit.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "output_bytes_fixed_point_result_id": self.fixed_point_result_id,
            "shared_measurement_id": self.measurement_id,
            "role_commits": [row.to_document() for row in self.role_commits],
            "io.output_bytes": self.output_bytes,
            "directory_fsync_completed": True,
            "single_write_per_role": True,
            "official_execution_allowed": False,
        }

    @property
    def output_commit_id(self) -> str:
        return content_id(OUTPUT_COMMIT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "output_commit_id": self.output_commit_id}


def _commit_role_bytes(
    *,
    occurrence_id: str,
    measurement_id: str,
    fixed_point: fixed_v1.OutputBytesFixedPointResultV1,
    output_directory: Path,
) -> HeldoutAbstractOutputCommitV1:
    directory = output_directory.resolve(strict=True)
    info = directory.stat()
    if directory.is_symlink() or not directory.is_dir() or stat.S_IMODE(info.st_mode) & 0o077:
        _fail("held-out output directory must be private and real")
    if any(directory.iterdir()):
        _fail("held-out output directory must be empty")
    commits: list[HeldoutAbstractOutputRoleCommitV1] = []
    for role in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES:
        raw = fixed_point.artifact_bytes_by_role[role]
        target = directory / f"{role}.json"
        descriptor = os.open(
            target,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
            0o600,
        )
        try:
            offset = 0
            while offset < len(raw):
                count = os.write(descriptor, raw[offset:])
                if count <= 0:
                    _fail("held-out output write made no progress")
                offset += count
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        info = target.stat()
        if (
            target.is_symlink()
            or not target.is_file()
            or info.st_size != len(raw)
            or stat.S_IMODE(info.st_mode) & 0o177
        ):
            _fail("held-out output role identity changed")
        commits.append(
            HeldoutAbstractOutputRoleCommitV1(
                role,
                target.name,
                len(raw),
                hashlib.sha256(raw).hexdigest(),
            )
        )
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return HeldoutAbstractOutputCommitV1(
        occurrence_id,
        fixed_point.result_id,
        measurement_id,
        tuple(commits),
        fixed_point.output_bytes,
    )


@dataclass(frozen=True, slots=True)
class HeldoutAbstractOccurrenceAccountingBundleV1:
    reuse_result: reuse_v1.HeldoutOverlayAbstractReuseResultV1 = field(
        repr=False, compare=False
    )
    stage_accounting: stage_v1.HeldoutAbstractStageAccountingResultV1 = field(
        repr=False, compare=False
    )
    measurement: HeldoutAbstractSharedMeasurementV1
    fixed_point: fixed_v1.OutputBytesFixedPointResultV1 = field(
        repr=False, compare=False
    )
    output_commit: HeldoutAbstractOutputCommitV1
    receipt_set: HeldoutAbstractSharedReceiptSetV1 = field(repr=False)
    path_aggregations: tuple[HeldoutAbstractPathAggregationV1, ...] = field(repr=False)
    work_vector: WorkVectorV1 = field(repr=False)
    comparison_vector: ComparisonVectorV1 = field(repr=False)
    actual_projection_proof: ActualProjectionProofV1 = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.reuse_result) is not reuse_v1.HeldoutOverlayAbstractReuseResultV1
            or type(self.stage_accounting)
            is not stage_v1.HeldoutAbstractStageAccountingResultV1
            or self.stage_accounting.reuse_result != self.reuse_result
            or self.measurement.reuse_result_id != self.reuse_result.result_id
            or self.receipt_set.measurement_id != self.measurement.measurement_id
            or len(self.path_aggregations) != EXPECTED_REQUIRED_PATH_COUNT
            or self.work_vector.route_kind is not RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
            or len(self.work_vector.records) != EXPECTED_REQUIRED_PATH_COUNT
            or self.comparison_vector.work_vector_id != self.work_vector.work_vector_id
            or self.actual_projection_proof.work_vector_id != self.work_vector.work_vector_id
            or self.actual_projection_proof.projection_term_count
            != EXPECTED_OPERATIONAL_PATH_COUNT
            or self.work_vector.values["io.output_bytes"] != self.fixed_point.output_bytes
            or self.output_commit.output_bytes != self.fixed_point.output_bytes
        ):
            _fail("held-out occurrence accounting bundle is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_occurrence_accounting.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.work_vector.subject_id,
            "heldout_abstract_reuse_result_id": self.reuse_result.result_id,
            "heldout_abstract_stage_accounting_id": self.stage_accounting.result_id,
            "shared_measurement_id": self.measurement.measurement_id,
            "shared_resource_receipt_set_id": self.receipt_set.receipt_set_id,
            "shared_resource_receipt_ids": [row.receipt_id for row in self.receipt_set.receipts],
            "path_aggregation_ids": [row.aggregation_id for row in self.path_aggregations],
            "counter_record_ids": [row.record_id for row in self.work_vector.records],
            "work_vector_id": self.work_vector.work_vector_id,
            "comparison_vector_id": self.comparison_vector.comparison_vector_id,
            "actual_projection_proof_id": self.actual_projection_proof.actual_projection_proof_id,
            "output_bytes_fixed_point_result_id": self.fixed_point.result_id,
            "output_commit_id": self.output_commit.output_commit_id,
            "shared_resource_path_count": EXPECTED_SHARED_PATH_COUNT,
            "complete_202_counter_record_chain_present": True,
            "all_182_operational_leaves_projected_exactly_once": True,
            "route_kind": RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE.value,
            "terminal_class": "PLAN_CERTIFICATE",
            "terminal_code": "ABSTRACT_CERTIFIED",
            "fresh_ground_or_observer_event_count": 0,
            "local_fallback_rebuild_native_zero": True,
            "eight_operational_roles_committed_once": True,
            "logical_occurrence_campaign_closed": False,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }

    @property
    def bundle_id(self) -> str:
        return content_id(BUNDLE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_accounting_bundle_id": self.bundle_id}


def _renderer_components(
    stage: stage_v1.HeldoutAbstractStageAccountingResultV1,
    measurement: HeldoutAbstractSharedMeasurementV1,
) -> tuple[
    tuple[Any, Any, Any, tuple[live_v3.RecordedStageWorkV3, ...]],
    fixed_v1.OutputBytesFixedPointProfileV1,
    Mapping[str, bytes],
]:
    verified = _verified_stage_chain(stage)
    renderer_id = content_id(
        RENDERER_DOMAIN,
        {
            "heldout_abstract_stage_accounting_id": stage.result_id,
            "shared_measurement_id": measurement.measurement_id,
            "required_roles": list(fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES),
        },
    )
    profile = fixed_v1.freeze_output_bytes_fixed_point_profile_v1(
        renderer_id=renderer_id,
        execution_identity_id=stage.result_id,
        max_total_bytes=512 * 1024 * 1024,
        role_byte_caps={
            role: 256 * 1024 * 1024
            for role in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
        },
        max_iterations=32,
    )
    return verified, profile, _static_role_bytes(stage)


def _operational_input_document(
    result: reuse_v1.HeldoutOverlayAbstractReuseResultV1,
) -> dict[str, Any]:
    """Return exactly the model/query envelope consumed by this occurrence.

    The historical observation archive remains reachable through the source
    result ID, but a directly certified fresh query does not reread it.  This
    avoids charging or serializing unrelated source evidence as route input.
    """

    return {
        "schema": "acfqp.construction_k7_heldout_abstract_route_input.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "heldout_abstract_reuse_result_id": result.result_id,
        "source_result_id": result.source.result_id,
        "source_overlay_id": result.source.final_overlay.overlay_id,
        "query": result.query.to_document(),
        "plan": result.plan.to_document(),
        "quotient_model": (
            result.source.final_overlay.bridge.quotient_model.to_document()
        ),
        "threshold": result.source.threshold.to_document(),
        "source_observation_archive_embedded": False,
        "new_ground_or_observer_input_present": False,
    }


def _run_heldout_abstract_occurrence_from_stage_v1(
    result: reuse_v1.HeldoutOverlayAbstractReuseResultV1,
    stage: stage_v1.HeldoutAbstractStageAccountingResultV1,
    *,
    output_directory: str | Path,
    replay_before_return: bool,
) -> HeldoutAbstractOccurrenceAccountingBundleV1:
    if (
        type(result) is not reuse_v1.HeldoutOverlayAbstractReuseResultV1
        or type(stage) is not stage_v1.HeldoutAbstractStageAccountingResultV1
        or stage.reuse_result is not result
    ):
        _fail("held-out occurrence accounting requires one exact accounted result")
    stage_v1.verify_heldout_abstract_stage_accounting_v1(stage)
    output = Path(output_directory)
    if output.exists():
        _fail("held-out output directory must be absent")
    input_raw = canonical_json_bytes(_operational_input_document(result))
    parsed_input = loads_canonical_json(input_raw)
    if canonical_json_bytes(parsed_input) != input_raw:
        _fail("held-out input bytes failed canonical readback")
    measurement = HeldoutAbstractSharedMeasurementV1(
        result.query.logical_occurrence_id,
        result.result_id,
        stage.result_id,
        hashlib.sha256(input_raw).hexdigest(),
        len(input_raw),
        stage.business_hash_invocations,
        len(stage.integrity_obligations),
        len(stage.protocol_obligations),
        len(input_raw),
        _peak_working_bytes(),
    )
    verified, profile, static = _renderer_components(stage, measurement)

    def renderer(candidate: int) -> dict[str, bytes]:
        return dict(
            _render_candidate(
                stage=stage,
                measurement=measurement,
                fixed_profile=profile,
                output_candidate=candidate,
                verified=verified,
                static_role_bytes=static,
            ).role_bytes
        )

    fixed_point = fixed_v1.solve_output_bytes_fixed_point_v1(
        profile=profile, renderer=renderer
    )
    fixed_v1.replay_output_bytes_fixed_point_v1(result=fixed_point, renderer=renderer)
    final = _render_candidate(
        stage=stage,
        measurement=measurement,
        fixed_profile=profile,
        output_candidate=fixed_point.output_bytes,
        verified=verified,
        static_role_bytes=static,
    )
    registry, comparison, actual, _rows = verified
    verify_actual_projection_v1(
        final.materialized.projection_proof,
        final.materialized.work_vector,
        final.materialized.comparison_vector,
        registry,
        comparison,
        actual,
    )
    if dict(final.role_bytes) != fixed_point.artifact_bytes_by_role:
        _fail("held-out final render differs from fixed-point bytes")
    output.mkdir(mode=0o700, parents=False)
    commit = _commit_role_bytes(
        occurrence_id=result.query.logical_occurrence_id,
        measurement_id=measurement.measurement_id,
        fixed_point=fixed_point,
        output_directory=output,
    )
    materialized = final.materialized
    bundle = HeldoutAbstractOccurrenceAccountingBundleV1(
        result,
        stage,
        measurement,
        fixed_point,
        commit,
        materialized.receipt_set,
        materialized.aggregations,
        materialized.work_vector,
        materialized.comparison_vector,
        materialized.projection_proof,
    )
    return (
        verify_heldout_abstract_occurrence_accounting_v1(bundle)
        if replay_before_return
        else bundle
    )


def run_heldout_abstract_occurrence_accounting_v1(
    result: reuse_v1.HeldoutOverlayAbstractReuseResultV1,
    *,
    output_directory: str | Path,
) -> HeldoutAbstractOccurrenceAccountingBundleV1:
    """Replay a frozen plan once inside the owner-accounted route window."""

    if type(result) is not reuse_v1.HeldoutOverlayAbstractReuseResultV1:
        _fail("held-out occurrence accounting requires one exact typed result")
    if Path(output_directory).exists():
        _fail("held-out output directory must be absent")
    stage = stage_v1.record_heldout_abstract_route_v1(result)
    return _run_heldout_abstract_occurrence_from_stage_v1(
        result,
        stage,
        output_directory=output_directory,
        replay_before_return=True,
    )


def run_preaccounted_heldout_abstract_occurrence_v1(
    stage: stage_v1.HeldoutAbstractStageAccountingResultV1,
    *,
    output_directory: str | Path,
) -> HeldoutAbstractOccurrenceAccountingBundleV1:
    """Materialize receipts without executing a second planner call."""

    if type(stage) is not stage_v1.HeldoutAbstractStageAccountingResultV1:
        _fail("preaccounted held-out occurrence requires one exact stage result")
    return _run_heldout_abstract_occurrence_from_stage_v1(
        stage.reuse_result,
        stage,
        output_directory=output_directory,
        replay_before_return=False,
    )


def verify_heldout_abstract_occurrence_accounting_v1(
    bundle: HeldoutAbstractOccurrenceAccountingBundleV1,
) -> HeldoutAbstractOccurrenceAccountingBundleV1:
    if type(bundle) is not HeldoutAbstractOccurrenceAccountingBundleV1:
        _fail("held-out occurrence verifier rejects foreign values")
    bundle.reuse_result.result_id
    stage_v1.verify_heldout_abstract_stage_accounting_v1(bundle.stage_accounting)
    verified, profile, static = _renderer_components(
        bundle.stage_accounting, bundle.measurement
    )
    if profile != bundle.fixed_point.profile:
        _fail("held-out fixed-point profile changed")

    def renderer(candidate: int) -> dict[str, bytes]:
        return dict(
            _render_candidate(
                stage=bundle.stage_accounting,
                measurement=bundle.measurement,
                fixed_profile=profile,
                output_candidate=candidate,
                verified=verified,
                static_role_bytes=static,
            ).role_bytes
        )

    fixed_v1.replay_output_bytes_fixed_point_v1(
        result=bundle.fixed_point, renderer=renderer
    )
    expected = _render_candidate(
        stage=bundle.stage_accounting,
        measurement=bundle.measurement,
        fixed_profile=profile,
        output_candidate=bundle.fixed_point.output_bytes,
        verified=verified,
        static_role_bytes=static,
    ).materialized
    registry, comparison, actual, _rows = verified
    verify_actual_projection_v1(
        expected.projection_proof,
        expected.work_vector,
        expected.comparison_vector,
        registry,
        comparison,
        actual,
    )
    if (
        expected.receipt_set != bundle.receipt_set
        or expected.aggregations != bundle.path_aggregations
        or expected.work_vector != bundle.work_vector
        or expected.comparison_vector != bundle.comparison_vector
        or expected.projection_proof != bundle.actual_projection_proof
        or bundle.output_commit.fixed_point_result_id != bundle.fixed_point.result_id
        or bundle.output_commit.measurement_id != bundle.measurement.measurement_id
    ):
        _fail("held-out occurrence artifacts differ from exact replay")
    return bundle


__all__ = (
    "ConstructionK7HeldoutAbstractOccurrenceAccountingV1Error",
    "LOCAL_DOMAINS",
    "HeldoutAbstractOccurrenceAccountingBundleV1",
    "HeldoutAbstractOutputCommitV1",
    "HeldoutAbstractOutputRoleCommitV1",
    "HeldoutAbstractPathAggregationV1",
    "HeldoutAbstractSharedMeasurementV1",
    "HeldoutAbstractSharedReceiptSetV1",
    "HeldoutAbstractSharedReceiptV1",
    "run_heldout_abstract_occurrence_accounting_v1",
    "run_preaccounted_heldout_abstract_occurrence_v1",
    "verify_heldout_abstract_occurrence_accounting_v1",
)
