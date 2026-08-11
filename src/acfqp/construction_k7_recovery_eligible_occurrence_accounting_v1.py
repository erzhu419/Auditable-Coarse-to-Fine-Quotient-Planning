"""Occurrence-wide accounting for the recovery-eligible world-model loop.

Three verified native stage vectors retain operation provenance.  This module
reduces their non-shared leaves, replaces all nine stage placeholders with
supervisor/fixed-point receipts, preserves route-family exclusivity, and emits
three complete CounterRecord -> WorkVector -> ComparisonVector chains.
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
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualWorkScope,
    verify_actual_projection_v1,
)
from acfqp import construction_accounting_live_v3 as live_v3
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_recovery_eligible_stage_accounting_v1 as stage_v1
from acfqp import construction_k7_recovery_eligible_supervised_executor_v1 as executor_v1
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp import construction_shared_resource_receipts_v1 as shared_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OCCURRENCE_ACCOUNTING_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OUTPUT_COMMIT_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OUTPUT_RENDERER_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_PATH_AGGREGATION_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_SET_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.116"
PROFILE_KEY = "construction_k7_recovery_eligible_occurrence_accounting_v1"
PATH_AGGREGATION_DOMAIN = (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_PATH_AGGREGATION_V1_DOMAIN
)
SHARED_RECEIPT_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_V1_DOMAIN
SHARED_RECEIPT_SET_DOMAIN = (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_SET_V1_DOMAIN
)
BUNDLE_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OCCURRENCE_ACCOUNTING_V1_DOMAIN
RENDERER_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OUTPUT_RENDERER_V1_DOMAIN
OUTPUT_COMMIT_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OUTPUT_COMMIT_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {
        PATH_AGGREGATION_DOMAIN,
        SHARED_RECEIPT_DOMAIN,
        SHARED_RECEIPT_SET_DOMAIN,
        BUNDLE_DOMAIN,
        RENDERER_DOMAIN,
        OUTPUT_COMMIT_DOMAIN,
    }
)
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("recovery occurrence-accounting domains are not central")

EXPECTED_STAGE_COUNT = 3
EXPECTED_REQUIRED_PATH_COUNT = registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
EXPECTED_OPERATIONAL_PATH_COUNT = registry_v6.EXPECTED_V6_OPERATIONAL_LEAF_COUNT
EXPECTED_SHARED_PATH_COUNT = 9
EXPECTED_PROJECTION_TERM_COUNT = EXPECTED_OPERATIONAL_PATH_COUNT
SHARED_PATHS = shared_v1.SHARED_RESOURCE_PATHS
PRE_OUTPUT_SHARED_PATHS = tuple(
    path for path in SHARED_PATHS if path != "io.output_bytes"
)
LOCAL_RECOVERY_PATH_PREFIXES = ("local.", "acquisition.", "build.")
DERIVED_RECONCILIATION_PATHS = (
    "process.exit_failures",
    "process.exit_successes",
    "route.attempts",
    "route.failures",
    "route.successes",
    "solver.attempts",
    "solver.failures",
    "solver.successes",
)


class ConstructionK7RecoveryEligibleOccurrenceAccountingV1Error(RuntimeError):
    """A reduction, receipt, fixed point, or output commit failed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RecoveryEligibleOccurrenceAccountingV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligibleOccurrenceAccountingV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


@dataclass(frozen=True, slots=True)
class RecoveryEligibleSharedResourceReceiptV1:
    occurrence_id: str
    supervised_execution_id: str
    shared_measurement_id: str
    path: str
    reducer: ReducerEnum
    value: int
    source_kind: str
    source_evidence_id: str
    stage_placeholder_record_ids: tuple[str, ...]
    output_fixed_point_profile_id: str | None = None

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "receipt occurrence"),
            (self.supervised_execution_id, "receipt execution"),
            (self.shared_measurement_id, "receipt measurement"),
            (self.source_evidence_id, "receipt evidence"),
        ):
            _cid(value, label)
        object.__setattr__(self, "reducer", ReducerEnum(self.reducer))
        _nonnegative(self.value, "shared receipt value")
        if (
            self.path not in SHARED_PATHS
            or self.source_kind
            not in {"TRUSTED_SUPERVISOR_MEASUREMENT", "OUTPUT_FIXED_POINT"}
            or type(self.stage_placeholder_record_ids) is not tuple
            or len(self.stage_placeholder_record_ids) != EXPECTED_STAGE_COUNT
        ):
            _fail("recovery shared receipt structure changed")
        for record_id in self.stage_placeholder_record_ids:
            _cid(record_id, "receipt placeholder")
        is_output = self.path == "io.output_bytes"
        if (
            (self.output_fixed_point_profile_id is not None) != is_output
            or (is_output and self.source_kind != "OUTPUT_FIXED_POINT")
            or (not is_output and self.source_kind != "TRUSTED_SUPERVISOR_MEASUREMENT")
        ):
            _fail("recovery shared receipt source binding changed")
        if self.output_fixed_point_profile_id is not None:
            _cid(self.output_fixed_point_profile_id, "fixed-point profile")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_shared_receipt.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "supervised_execution_id": self.supervised_execution_id,
            "shared_measurement_id": self.shared_measurement_id,
            "path": self.path,
            "reducer": self.reducer.value,
            "value": self.value,
            "source_kind": self.source_kind,
            "source_evidence_id": self.source_evidence_id,
            "stage_placeholder_record_ids": list(self.stage_placeholder_record_ids),
            "output_fixed_point_profile_id": self.output_fixed_point_profile_id,
            "complete_window_closed": True,
            "stage_placeholders_replaced_not_summed": True,
            "official_execution_allowed": False,
        }

    @property
    def receipt_id(self) -> str:
        return content_id(SHARED_RECEIPT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "shared_resource_receipt_id": self.receipt_id}


@dataclass(frozen=True, slots=True)
class RecoveryEligibleSharedResourceReceiptSetV1:
    occurrence_id: str
    supervised_execution_id: str
    shared_measurement_id: str
    receipts: tuple[RecoveryEligibleSharedResourceReceiptV1, ...]

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "receipt-set occurrence"),
            (self.supervised_execution_id, "receipt-set execution"),
            (self.shared_measurement_id, "receipt-set measurement"),
        ):
            _cid(value, label)
        if (
            type(self.receipts) is not tuple
            or tuple(row.path for row in self.receipts) != SHARED_PATHS
            or any(
                type(row) is not RecoveryEligibleSharedResourceReceiptV1
                or row.occurrence_id != self.occurrence_id
                or row.supervised_execution_id != self.supervised_execution_id
                or row.shared_measurement_id != self.shared_measurement_id
                for row in self.receipts
            )
        ):
            _fail("recovery receipt set does not cover nine paths")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_shared_receipt_set.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "supervised_execution_id": self.supervised_execution_id,
            "shared_measurement_id": self.shared_measurement_id,
            "shared_resource_paths": list(SHARED_PATHS),
            "shared_resource_receipt_ids": [row.receipt_id for row in self.receipts],
            "receipt_count": EXPECTED_SHARED_PATH_COUNT,
            "all_nine_shared_paths_semantically_replayed": True,
            "official_execution_allowed": False,
        }

    @property
    def receipt_set_id(self) -> str:
        return content_id(SHARED_RECEIPT_SET_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "shared_resource_receipt_set_id": self.receipt_set_id}


@dataclass(frozen=True, slots=True)
class RecoveryEligiblePathAggregationV1:
    occurrence_id: str
    supervised_execution_id: str
    path: str
    reducer: ReducerEnum
    value: int
    stage_record_ids: tuple[str, ...]
    source_kind: str
    source_evidence_id: str

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "aggregation occurrence")
        _cid(self.supervised_execution_id, "aggregation execution")
        _cid(self.source_evidence_id, "aggregation evidence")
        object.__setattr__(self, "reducer", ReducerEnum(self.reducer))
        _nonnegative(self.value, "aggregation value")
        if (
            type(self.path) is not str
            or not self.path
            or type(self.stage_record_ids) is not tuple
            or len(self.stage_record_ids) != EXPECTED_STAGE_COUNT
            or self.source_kind
            not in {
                "STAGE_SUM",
                "STAGE_MAX",
                "SHARED_RESOURCE_RECEIPT",
                "SEMANTIC_DERIVED_RECONCILIATION",
            }
        ):
            _fail("recovery path aggregation structure changed")
        for record_id in self.stage_record_ids:
            _cid(record_id, "aggregation stage record")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_path_aggregation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "supervised_execution_id": self.supervised_execution_id,
            "path": self.path,
            "reducer": self.reducer.value,
            "value": self.value,
            "stage_record_ids": list(self.stage_record_ids),
            "source_kind": self.source_kind,
            "source_evidence_id": self.source_evidence_id,
            "all_stage_instances_retained": True,
            "shared_stage_placeholders_replaced_not_summed": self.path in SHARED_PATHS,
        }

    @property
    def aggregation_id(self) -> str:
        return content_id(PATH_AGGREGATION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "path_aggregation_id": self.aggregation_id}


def _verified_stage_records(
    execution: executor_v1.SupervisedRecoveryEligibleExecutionV1,
) -> tuple[Any, Any, Any, Any, tuple[live_v3.RecordedStageWorkV3, ...]]:
    execution = executor_v1.require_supervised_recovery_eligible_execution_v1(
        execution
    )
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(registry, comparison)
    rows = execution.recorded_stages
    if tuple(
        registry_v6.ConstructionStageKindV6(row.stage_start.stage_kind.value)
        for row in rows
    ) != stage_v1.CANONICAL_STAGE_PLAN_V1:
        _fail("occurrence aggregation requires three ordered recovery stages")
    for row in rows:
        live_v3.verify_recorded_stage_work_v3(
            row, registry, stage, comparison, actual
        )
    if any(
        row.work_vector.values[path] != 0
        for row in rows
        for path in SHARED_PATHS
    ):
        _fail("recovery stage shared placeholders became nonzero")
    return registry, stage, comparison, actual, rows


def _derived_reconciliation_values(
    execution: executor_v1.SupervisedRecoveryEligibleExecutionV1,
) -> dict[str, int]:
    science = execution.science_summary
    values = {
        "process.exit_failures": 0,
        "process.exit_successes": 1,
        "route.attempts": science["route_attempts"],
        "route.failures": science["route_failures"],
        "route.successes": science["route_successes"],
        "solver.attempts": science["solver_attempts"],
        "solver.failures": science["solver_failures"],
        "solver.successes": science["solver_successes"],
    }
    if (
        values["route.attempts"]
        != values["route.successes"] + values["route.failures"]
        or values["solver.attempts"]
        != values["solver.successes"] + values["solver.failures"]
        or execution.measurement.fixed_values["process.launches"]
        != values["process.exit_successes"] + values["process.exit_failures"]
    ):
        _fail("recovery route/solver/process facts do not reconcile")
    return values


@dataclass(frozen=True, slots=True)
class _MaterializedCandidateV1:
    receipt_set: RecoveryEligibleSharedResourceReceiptSetV1
    aggregations: tuple[RecoveryEligiblePathAggregationV1, ...]
    work_vectors: tuple[WorkVectorV1, ...]
    comparison_vectors: tuple[ComparisonVectorV1, ...]
    projection_proofs: tuple[ActualProjectionProofV1, ...]
    occurrence_comparison_values: tuple[tuple[str, int], ...]


def _materialize_candidate(
    *,
    execution: executor_v1.SupervisedRecoveryEligibleExecutionV1,
    fixed_profile: fixed_v1.OutputBytesFixedPointProfileV1,
    output_candidate: int,
    verified: tuple[Any, Any, Any, Any, tuple[live_v3.RecordedStageWorkV3, ...]],
) -> _MaterializedCandidateV1:
    registry, _stage, comparison, actual, stages = verified
    if fixed_profile.execution_identity_id != execution.execution_id:
        _fail("recovery fixed point crossed supervised execution")
    records_by_path = tuple(
        {record.path: record for record in row.work_vector.records}
        for row in stages
    )
    if any(tuple(sorted(rows)) != registry.required_paths for rows in records_by_path):
        _fail("recovery stage record inventory changed")

    measurement = execution.measurement
    shared_values = dict(measurement.fixed_values)
    shared_values["io.mounted_bytes_peak"] = measurement.mounted_bytes_peak(
        output_candidate
    )
    shared_values["io.output_bytes"] = _nonnegative(
        output_candidate, "output fixed-point candidate"
    )
    receipts = tuple(
        RecoveryEligibleSharedResourceReceiptV1(
            measurement.occurrence_id,
            execution.execution_id,
            measurement.measurement_id,
            path,
            registry.by_path[path].reducer,
            shared_values[path],
            (
                "OUTPUT_FIXED_POINT"
                if path == "io.output_bytes"
                else "TRUSTED_SUPERVISOR_MEASUREMENT"
            ),
            (
                fixed_profile.profile_id
                if path == "io.output_bytes"
                else measurement.measurement_id
            ),
            tuple(rows[path].record_id for rows in records_by_path),
            fixed_profile.profile_id if path == "io.output_bytes" else None,
        )
        for path in SHARED_PATHS
    )
    receipt_set = RecoveryEligibleSharedResourceReceiptSetV1(
        measurement.occurrence_id,
        execution.execution_id,
        measurement.measurement_id,
        receipts,
    )
    receipt_by_path = {row.path: row for row in receipts}
    derived = _derived_reconciliation_values(execution)
    aggregations: list[RecoveryEligiblePathAggregationV1] = []
    aggregate_values: dict[str, int] = {}
    for path in registry.required_paths:
        leaf = registry.by_path[path]
        stage_records = tuple(rows[path] for rows in records_by_path)
        if path in receipt_by_path:
            receipt = receipt_by_path[path]
            value = receipt.value
            source_kind = "SHARED_RESOURCE_RECEIPT"
            source_id = receipt.receipt_id
        elif path in derived:
            value = derived[path]
            source_kind = "SEMANTIC_DERIVED_RECONCILIATION"
            source_id = measurement.operational_trace_id
        elif leaf.reducer is ReducerEnum.SUM:
            value = sum(record.value for record in stage_records)
            source_kind = "STAGE_SUM"
            source_id = execution.execution_id
        else:
            value = max(record.value for record in stage_records)
            source_kind = "STAGE_MAX"
            source_id = execution.execution_id
        aggregation = RecoveryEligiblePathAggregationV1(
            measurement.occurrence_id,
            execution.execution_id,
            path,
            leaf.reducer,
            value,
            tuple(record.record_id for record in stage_records),
            source_kind,
            source_id,
        )
        aggregations.append(aggregation)
        aggregate_values[path] = value
    aggregation_rows = tuple(aggregations)
    if (
        len(aggregation_rows) != EXPECTED_REQUIRED_PATH_COUNT
        or tuple(row.path for row in aggregation_rows) != registry.required_paths
    ):
        _fail("recovery occurrence aggregation is incomplete")

    components = (
        ("SUPERVISED_OCCURRENCE_WRAPPER", RouteKindEnum.ABSTRACT_FAILED_PREFIX),
        ("LOCAL_RECOVERY_AGGREGATE", RouteKindEnum.LOCAL_ATTEMPT),
        ("DIRECT_FALLBACK", RouteKindEnum.DIRECT_FALLBACK),
    )

    def stage_reduce(path: str, indexes: tuple[int, ...]) -> int:
        values = tuple(records_by_path[index][path].value for index in indexes)
        if registry.by_path[path].reducer is ReducerEnum.SUM:
            return sum(values)
        return max(values)

    component_values = {
        name: {path: 0 for path in registry.required_paths}
        for name, _route in components
    }
    for path in registry.required_paths:
        if path.startswith(LOCAL_RECOVERY_PATH_PREFIXES):
            component_values["LOCAL_RECOVERY_AGGREGATE"][path] = aggregate_values[path]
        elif path.startswith(("fallback.", "route.", "solver.")):
            component_values["DIRECT_FALLBACK"][path] = aggregate_values[path]
        elif path.startswith("control."):
            component_values["LOCAL_RECOVERY_AGGREGATE"][path] = stage_reduce(
                path, (0, 1)
            )
            component_values["DIRECT_FALLBACK"][path] = stage_reduce(path, (2,))
        else:
            component_values["SUPERVISED_OCCURRENCE_WRAPPER"][path] = (
                aggregate_values[path]
            )

    work_vectors: list[WorkVectorV1] = []
    comparisons: list[ComparisonVectorV1] = []
    proofs: list[ActualProjectionProofV1] = []
    for component_name, route_kind in components:
        records = tuple(
            CounterRecordV1(
                registry.registry_id,
                aggregation.path,
                component_values[component_name][aggregation.path],
                True,
                content_id(
                    PATH_AGGREGATION_DOMAIN,
                    {
                        "occurrence_path_aggregation_id": aggregation.aggregation_id,
                        "component_name": component_name,
                        "route_kind": route_kind.value,
                        "component_value": component_values[component_name][
                            aggregation.path
                        ],
                    },
                ),
                registry.by_path[aggregation.path].semantics_id,
                registry.by_path[aggregation.path].owner,
                registry.by_path[aggregation.path].unit,
                registry.by_path[aggregation.path].lane,
                registry.by_path[aggregation.path].scope,
                registry.by_path[aggregation.path].reducer,
            )
            for aggregation in aggregation_rows
        )
        vector = WorkVectorV1(
            registry.registry_id,
            measurement.occurrence_id,
            route_kind,
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
            registry.registry_id,
            comparison.comparison_profile_id,
            vector.work_vector_id,
            projected.comparison_vector_id,
            LaneEnum.OPERATIONAL,
            (
                ActualWorkScope.COMMON_PREFIX
                if route_kind is RouteKindEnum.ABSTRACT_FAILED_PREFIX
                else ActualWorkScope.MARGINAL_ROUTE_AGGREGATE
            ),
            len(actual.terms),
        )
        verify_actual_projection_v1(
            proof, vector, projected, registry, comparison, actual
        )
        work_vectors.append(vector)
        comparisons.append(projected)
        proofs.append(proof)

    axis_reducers = {axis.name: axis.reducer for axis in comparison.axes}
    occurrence_axes = tuple(
        (
            axis,
            (
                sum(dict(vector.values)[axis] for vector in comparisons)
                if axis_reducers[axis] is ReducerEnum.SUM
                else max(dict(vector.values)[axis] for vector in comparisons)
            ),
        )
        for axis in SHARED_AXES
    )
    for path, aggregate in aggregate_values.items():
        values = tuple(component_values[name][path] for name, _route in components)
        expected = (
            sum(values)
            if registry.by_path[path].reducer is ReducerEnum.SUM
            else max(values)
        )
        if expected != aggregate:
            _fail(f"recovery component reduction changed for {path}")
    if len(actual.terms) != EXPECTED_PROJECTION_TERM_COUNT:
        _fail("recovery projection does not cover 182 operational leaves")
    return _MaterializedCandidateV1(
        receipt_set,
        aggregation_rows,
        tuple(work_vectors),
        tuple(comparisons),
        tuple(proofs),
        occurrence_axes,
    )


@dataclass(frozen=True, slots=True)
class _RenderedCandidateV1:
    materialized: _MaterializedCandidateV1
    role_bytes: Mapping[str, bytes]


def _static_role_bytes(
    execution: executor_v1.SupervisedRecoveryEligibleExecutionV1,
) -> Mapping[str, bytes]:
    return MappingProxyType(
        {
            "BUSINESS_RESULT": canonical_json_bytes(
                {
                    "artifact_role": "BUSINESS_RESULT",
                    "schema": "acfqp.construction_k7_recovery_eligible_business_result.v1",
                    "schema_version": SCHEMA_VERSION,
                    "profile_key": PROFILE_KEY,
                    "occurrence_id": execution.measurement.occurrence_id,
                    "native_accounting_id": execution.measurement.native_accounting_id,
                    "stage_accounting_result_id": execution.measurement.stage_accounting_result_id,
                    "shared_measurement_id": execution.measurement.measurement_id,
                    "runtime_preparation": execution.preparation.to_document(),
                    "supervised_request": dict(execution.request_document),
                    "shared_measurement": execution.measurement.to_document(),
                    "science_summary": dict(execution.science_summary),
                    "terminal_class": "PLAN_CERTIFICATE",
                    "terminal_code": "FULL_GROUND_FALLBACK",
                    "construction_only": True,
                    "official_execution_allowed": False,
                }
            ),
            "OPERATIONAL_TRACE": execution.trace_raw,
        }
    )


def _render_candidate(
    *,
    execution: executor_v1.SupervisedRecoveryEligibleExecutionV1,
    fixed_profile: fixed_v1.OutputBytesFixedPointProfileV1,
    output_candidate: int,
    verified: tuple[Any, Any, Any, Any, tuple[live_v3.RecordedStageWorkV3, ...]],
    static_role_bytes: Mapping[str, bytes],
) -> _RenderedCandidateV1:
    materialized = _materialize_candidate(
        execution=execution,
        fixed_profile=fixed_profile,
        output_candidate=output_candidate,
        verified=verified,
    )
    wrapper, local, fallback = materialized.work_vectors
    wrapper_comparison, local_comparison, fallback_comparison = (
        materialized.comparison_vectors
    )
    wrapper_proof, local_proof, fallback_proof = materialized.projection_proofs
    roles: dict[str, bytes] = dict(static_role_bytes)
    roles["TERMINAL_ARTIFACT"] = canonical_json_bytes(
        {
            "artifact_role": "TERMINAL_ARTIFACT",
            "schema": "acfqp.construction_k7_recovery_eligible_terminal_artifact.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": wrapper.subject_id,
            "native_accounting_id": execution.measurement.native_accounting_id,
            "direct_ground_fallback_id": execution.science_summary[
                "direct_ground_fallback_id"
            ],
            "component_work_vector_ids": [
                row.work_vector_id for row in materialized.work_vectors
            ],
            "component_comparison_vector_ids": [
                row.comparison_vector_id for row in materialized.comparison_vectors
            ],
            "component_actual_projection_proof_ids": [
                row.actual_projection_proof_id for row in materialized.projection_proofs
            ],
            "io.output_bytes": output_candidate,
            "terminal_scope": "LOGICAL_OCCURRENCE_CONSTRUCTION",
            "terminal_class": "PLAN_CERTIFICATE",
            "terminal_code": "FULL_GROUND_FALLBACK",
            "scientific_plan_certificate_preserved": True,
            "official_certificate_coverage_authority": False,
            "campaign_closure_issued": False,
            "official_execution_allowed": False,
        }
    )
    roles["COUNTER_RECORD_SET"] = canonical_json_bytes(
        {
            "artifact_role": "COUNTER_RECORD_SET",
            "schema": "acfqp.construction_k7_recovery_eligible_counter_record_set.v1",
            "occurrence_id": wrapper.subject_id,
            "io.output_bytes": output_candidate,
            "shared_resource_receipt_set": materialized.receipt_set.to_document(),
            "shared_resource_receipts": [
                row.to_document() for row in materialized.receipt_set.receipts
            ],
            "component_counter_record_count": sum(
                len(row.records) for row in materialized.work_vectors
            ),
            "counter_records_per_component": EXPECTED_REQUIRED_PATH_COUNT,
            "path_aggregations": [
                row.to_document() for row in materialized.aggregations
            ],
            "component_counter_records": [
                {
                    "route_kind": row.route_kind.value,
                    "counter_records": [item.to_dict() for item in row.records],
                }
                for row in materialized.work_vectors
            ],
        }
    )
    roles["WORK_VECTOR"] = canonical_json_bytes(
        {
            "artifact_role": "WORK_VECTOR",
            "schema": "acfqp.construction_k7_recovery_eligible_work_vector_artifact.v1",
            "io.output_bytes": output_candidate,
            "route_family_vectors_remain_separate": True,
            "marginal_route_upper_compliance_authority": False,
            "supervised_wrapper_work_vector": wrapper.to_dict(),
            "local_recovery_work_vector": local.to_dict(),
            "direct_fallback_work_vector": fallback.to_dict(),
        }
    )
    roles["COMPARISON_VECTOR"] = canonical_json_bytes(
        {
            "artifact_role": "COMPARISON_VECTOR",
            "schema": "acfqp.construction_k7_recovery_eligible_comparison_vector_artifact.v1",
            "io.output_bytes": output_candidate,
            "route_choice_authority": False,
            "supervised_wrapper_comparison_vector": wrapper_comparison.to_dict(),
            "local_recovery_comparison_vector": local_comparison.to_dict(),
            "direct_fallback_comparison_vector": fallback_comparison.to_dict(),
            "occurrence_reducer_exact_comparison_values": [
                {"axis": axis, "value": value}
                for axis, value in materialized.occurrence_comparison_values
            ],
        }
    )
    roles["ACTUAL_PROJECTION_PROOF"] = canonical_json_bytes(
        {
            "artifact_role": "ACTUAL_PROJECTION_PROOF",
            "schema": "acfqp.construction_k7_recovery_eligible_projection_artifact.v1",
            "io.output_bytes": output_candidate,
            "supervised_wrapper_actual_projection_proof": wrapper_proof.to_dict(),
            "local_recovery_actual_projection_proof": local_proof.to_dict(),
            "direct_fallback_actual_projection_proof": fallback_proof.to_dict(),
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
            "schema": "acfqp.construction_k7_recovery_eligible_output_manifest.v1",
            "occurrence_id": wrapper.subject_id,
            "output_bytes_fixed_point_profile_id": fixed_profile.profile_id,
            "io.output_bytes": output_candidate,
            "ordered_preceding_roles": preceding,
            "output_manifest_self_extent_excluded_from_preceding_rows": True,
            "required_role_order": list(fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES),
        }
    )
    if tuple(roles) != fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES:
        _fail("recovery rendered role order changed")
    return _RenderedCandidateV1(materialized, MappingProxyType(roles))


@dataclass(frozen=True, slots=True)
class RecoveryEligibleOutputRoleCommitV1:
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
            _fail("recovery output role commit is malformed")
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
class RecoveryEligibleOutputCommitV1:
    occurrence_id: str
    fixed_point_result_id: str
    shared_measurement_id: str
    role_commits: tuple[RecoveryEligibleOutputRoleCommitV1, ...]
    output_bytes: int

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "output occurrence")
        _cid(self.fixed_point_result_id, "output fixed point")
        _cid(self.shared_measurement_id, "output measurement")
        if (
            tuple(row.artifact_role for row in self.role_commits)
            != fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
            or sum(row.byte_count for row in self.role_commits) != self.output_bytes
            or self.output_bytes <= 0
        ):
            _fail("recovery output commit inventory changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_output_commit.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "output_bytes_fixed_point_result_id": self.fixed_point_result_id,
            "shared_measurement_id": self.shared_measurement_id,
            "role_commits": [row.to_document() for row in self.role_commits],
            "io.output_bytes": self.output_bytes,
            "single_write_per_role": True,
            "directory_fsync_completed": True,
            "commit_receipt_is_provenance_not_an_extra_output_role": True,
            "construction_only": True,
            "official_execution_allowed": False,
        }

    @property
    def output_commit_id(self) -> str:
        return content_id(OUTPUT_COMMIT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "output_commit_id": self.output_commit_id}


def _commit_role_bytes(
    *,
    execution: executor_v1.SupervisedRecoveryEligibleExecutionV1,
    fixed_point: fixed_v1.OutputBytesFixedPointResultV1,
    output_directory: Path,
    pending_trace_path: Path,
) -> RecoveryEligibleOutputCommitV1:
    directory = output_directory.resolve(strict=True)
    info = directory.stat()
    if directory.is_symlink() or not directory.is_dir() or stat.S_IMODE(info.st_mode) & 0o077:
        _fail("recovery output directory must be private and real")
    expected_pending = directory / ".OPERATIONAL_TRACE.pending"
    if pending_trace_path != expected_pending:
        _fail("recovery pending trace path changed")
    if tuple(sorted(path.name for path in directory.iterdir())) != (expected_pending.name,):
        _fail("recovery output directory contains unexpected material")
    if (
        pending_trace_path.is_symlink()
        or not pending_trace_path.is_file()
        or pending_trace_path.read_bytes() != execution.trace_raw
    ):
        _fail("recovery pending trace differs from supervised bytes")
    role_bytes = fixed_point.artifact_bytes_by_role
    if role_bytes["OPERATIONAL_TRACE"] != execution.trace_raw:
        _fail("recovery fixed point replaced operational trace")
    commits: list[RecoveryEligibleOutputRoleCommitV1] = []
    for role in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES:
        raw = role_bytes[role]
        target = directory / f"{role}.json"
        if role == "OPERATIONAL_TRACE":
            descriptor = os.open(pending_trace_path, os.O_RDONLY | os.O_CLOEXEC)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.replace(pending_trace_path, target)
        else:
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
                        _fail("recovery output write made no progress")
                    offset += count
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        target_stat = target.stat()
        if (
            target.is_symlink()
            or not target.is_file()
            or target_stat.st_size != len(raw)
            or stat.S_IMODE(target_stat.st_mode) & 0o177
        ):
            _fail("recovery committed role identity changed")
        commits.append(
            RecoveryEligibleOutputRoleCommitV1(
                role,
                target.name,
                len(raw),
                hashlib.sha256(raw).hexdigest(),
            )
        )
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return RecoveryEligibleOutputCommitV1(
        execution.measurement.occurrence_id,
        fixed_point.result_id,
        execution.measurement.measurement_id,
        tuple(commits),
        fixed_point.output_bytes,
    )


@dataclass(frozen=True, slots=True)
class RecoveryEligibleOccurrenceAccountingBundleV1:
    supervised_execution: executor_v1.SupervisedRecoveryEligibleExecutionV1 = field(
        repr=False, compare=False
    )
    fixed_point: fixed_v1.OutputBytesFixedPointResultV1 = field(
        repr=False, compare=False
    )
    output_commit: RecoveryEligibleOutputCommitV1
    receipt_set: RecoveryEligibleSharedResourceReceiptSetV1 = field(
        repr=False, compare=False
    )
    path_aggregations: tuple[RecoveryEligiblePathAggregationV1, ...] = field(
        repr=False
    )
    work_vectors: tuple[WorkVectorV1, ...] = field(repr=False)
    comparison_vectors: tuple[ComparisonVectorV1, ...] = field(repr=False)
    actual_projection_proofs: tuple[ActualProjectionProofV1, ...] = field(repr=False)
    occurrence_comparison_values: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        if (
            type(self.supervised_execution)
            is not executor_v1.SupervisedRecoveryEligibleExecutionV1
            or type(self.fixed_point) is not fixed_v1.OutputBytesFixedPointResultV1
            or type(self.output_commit) is not RecoveryEligibleOutputCommitV1
            or type(self.receipt_set) is not RecoveryEligibleSharedResourceReceiptSetV1
            or len(self.path_aggregations) != EXPECTED_REQUIRED_PATH_COUNT
            or tuple(row.route_kind for row in self.work_vectors)
            != (
                RouteKindEnum.ABSTRACT_FAILED_PREFIX,
                RouteKindEnum.LOCAL_ATTEMPT,
                RouteKindEnum.DIRECT_FALLBACK,
            )
            or any(
                len(row.records) != EXPECTED_REQUIRED_PATH_COUNT
                or row.subject_id != self.supervised_execution.measurement.occurrence_id
                for row in self.work_vectors
            )
            or len(self.comparison_vectors) != 3
            or len(self.actual_projection_proofs) != 3
            or tuple(row.work_vector_id for row in self.comparison_vectors)
            != tuple(row.work_vector_id for row in self.work_vectors)
            or tuple(row.work_vector_id for row in self.actual_projection_proofs)
            != tuple(row.work_vector_id for row in self.work_vectors)
            or self.work_vectors[0].values["io.output_bytes"]
            != self.fixed_point.output_bytes
            or self.work_vectors[0].values["io.mounted_bytes_peak"]
            != self.supervised_execution.measurement.mounted_bytes_peak(
                self.fixed_point.output_bytes
            )
            or tuple(axis for axis, _value in self.occurrence_comparison_values)
            != SHARED_AXES
        ):
            _fail("recovery occurrence accounting bundle is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_occurrence_accounting.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.work_vectors[0].subject_id,
            "native_accounting_id": self.supervised_execution.measurement.native_accounting_id,
            "supervised_execution_id": self.supervised_execution.execution_id,
            "shared_measurement_id": self.supervised_execution.measurement.measurement_id,
            "shared_resource_receipt_set_id": self.receipt_set.receipt_set_id,
            "shared_resource_receipt_ids": [
                row.receipt_id for row in self.receipt_set.receipts
            ],
            "output_bytes_fixed_point_result_id": self.fixed_point.result_id,
            "output_commit_id": self.output_commit.output_commit_id,
            "path_aggregation_ids": [
                row.aggregation_id for row in self.path_aggregations
            ],
            "component_counter_record_ids": [
                [item.record_id for item in row.records] for row in self.work_vectors
            ],
            "component_work_vector_ids": [
                row.work_vector_id for row in self.work_vectors
            ],
            "component_comparison_vector_ids": [
                row.comparison_vector_id for row in self.comparison_vectors
            ],
            "component_actual_projection_proof_ids": [
                row.actual_projection_proof_id for row in self.actual_projection_proofs
            ],
            "occurrence_reducer_exact_comparison_values": [
                {"axis": axis, "value": value}
                for axis, value in self.occurrence_comparison_values
            ],
            "shared_resource_path_count": EXPECTED_SHARED_PATH_COUNT,
            "shared_resource_paths": list(SHARED_PATHS),
            "shared_resource_receipts_complete": True,
            "three_complete_202_counter_record_chains_present": True,
            "route_family_work_vectors_issued": 3,
            "route_family_comparison_vectors_issued": 3,
            "route_family_actual_projection_proofs_issued": 3,
            "all_182_operational_leaves_projected_exactly_once_per_component": True,
            "stage_local_records_retained": (
                EXPECTED_STAGE_COUNT * EXPECTED_REQUIRED_PATH_COUNT
            ),
            "eight_operational_roles_committed_once": True,
            "route_family_exclusivity_preserved": True,
            "occurrence_reducer_exact_comparison_aggregate_present": True,
            "marginal_route_upper_compliance_authority": False,
            "route_choice_authority": False,
            "scientific_terminal_class": "PLAN_CERTIFICATE",
            "scientific_terminal_code": "FULL_GROUND_FALLBACK",
            "official_certificate_coverage_authority": False,
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
        return {
            **self._payload(),
            "occurrence_accounting_bundle_id": self.bundle_id,
        }


def _renderer_components(
    execution: executor_v1.SupervisedRecoveryEligibleExecutionV1,
) -> tuple[
    tuple[Any, Any, Any, Any, tuple[live_v3.RecordedStageWorkV3, ...]],
    fixed_v1.OutputBytesFixedPointProfileV1,
    Mapping[str, bytes],
]:
    verified = _verified_stage_records(execution)
    renderer_id = content_id(
        RENDERER_DOMAIN,
        {
            "supervised_execution_id": execution.execution_id,
            "occurrence_id": execution.measurement.occurrence_id,
            "shared_measurement_id": execution.measurement.measurement_id,
            "operational_trace_id": execution.measurement.operational_trace_id,
            "required_roles": list(fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES),
        },
    )
    profile = fixed_v1.freeze_output_bytes_fixed_point_profile_v1(
        renderer_id=renderer_id,
        execution_identity_id=execution.execution_id,
        max_total_bytes=512 * 1024 * 1024,
        role_byte_caps={
            role: 256 * 1024 * 1024
            for role in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
        },
        max_iterations=32,
    )
    return verified, profile, _static_role_bytes(execution)


def finalize_recovery_eligible_occurrence_accounting_v1(
    *,
    supervised_execution: executor_v1.SupervisedRecoveryEligibleExecutionV1,
    output_directory: str | Path,
    pending_trace_path: str | Path,
) -> RecoveryEligibleOccurrenceAccountingBundleV1:
    execution = executor_v1.require_supervised_recovery_eligible_execution_v1(
        supervised_execution
    )
    verified, profile, static = _renderer_components(execution)

    def renderer(candidate: int) -> dict[str, bytes]:
        return dict(
            _render_candidate(
                execution=execution,
                fixed_profile=profile,
                output_candidate=candidate,
                verified=verified,
                static_role_bytes=static,
            ).role_bytes
        )

    fixed_point = fixed_v1.solve_output_bytes_fixed_point_v1(
        profile=profile, renderer=renderer
    )
    fixed_v1.replay_output_bytes_fixed_point_v1(
        result=fixed_point, renderer=renderer
    )
    final = _render_candidate(
        execution=execution,
        fixed_profile=profile,
        output_candidate=fixed_point.output_bytes,
        verified=verified,
        static_role_bytes=static,
    )
    if dict(final.role_bytes) != fixed_point.artifact_bytes_by_role:
        _fail("recovery final render differs from fixed-point bytes")
    commit = _commit_role_bytes(
        execution=execution,
        fixed_point=fixed_point,
        output_directory=Path(output_directory),
        pending_trace_path=Path(pending_trace_path).resolve(strict=True),
    )
    materialized = final.materialized
    result = RecoveryEligibleOccurrenceAccountingBundleV1(
        execution,
        fixed_point,
        commit,
        materialized.receipt_set,
        materialized.aggregations,
        materialized.work_vectors,
        materialized.comparison_vectors,
        materialized.projection_proofs,
        materialized.occurrence_comparison_values,
    )
    return verify_recovery_eligible_occurrence_accounting_v1(result)


def run_recovery_eligible_occurrence_accounting_v1(
    *,
    repository_root: str | Path,
    runtime_cas_root: str | Path,
    output_directory: str | Path,
    binding_bytes: bytes,
    snapshot_bytes: bytes,
    transition_bytes: bytes,
    logical_occurrence_id: str,
    query_ordinal: int,
    timeout_seconds: int = executor_v1.DEFAULT_TIMEOUT_SECONDS,
) -> RecoveryEligibleOccurrenceAccountingBundleV1:
    output = Path(output_directory)
    if output.exists():
        _fail("recovery output directory must be absent")
    output.mkdir(mode=0o700, parents=False)
    preparation = executor_v1.prepare_recovery_eligible_accounted_runtime_v1(
        repository_root=repository_root,
        runtime_cas_root=runtime_cas_root,
    )
    pending_trace = output.resolve(strict=True) / ".OPERATIONAL_TRACE.pending"
    execution = executor_v1.execute_recovery_eligible_accounted_v1(
        preparation,
        binding_bytes=binding_bytes,
        snapshot_bytes=snapshot_bytes,
        transition_bytes=transition_bytes,
        logical_occurrence_id=logical_occurrence_id,
        query_ordinal=query_ordinal,
        trace_output_path=pending_trace,
        timeout_seconds=timeout_seconds,
    )
    return finalize_recovery_eligible_occurrence_accounting_v1(
        supervised_execution=execution,
        output_directory=output,
        pending_trace_path=pending_trace,
    )


def verify_recovery_eligible_occurrence_accounting_v1(
    bundle: RecoveryEligibleOccurrenceAccountingBundleV1,
) -> RecoveryEligibleOccurrenceAccountingBundleV1:
    if type(bundle) is not RecoveryEligibleOccurrenceAccountingBundleV1:
        _fail("recovery occurrence verifier received a foreign bundle")
    verified, profile, static = _renderer_components(bundle.supervised_execution)
    registry, _stage, comparison, actual, _rows = verified
    if profile != bundle.fixed_point.profile:
        _fail("recovery fixed-point profile changed")

    def renderer(candidate: int) -> dict[str, bytes]:
        return dict(
            _render_candidate(
                execution=bundle.supervised_execution,
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
        execution=bundle.supervised_execution,
        fixed_profile=profile,
        output_candidate=bundle.fixed_point.output_bytes,
        verified=verified,
        static_role_bytes=static,
    ).materialized
    if (
        expected.receipt_set != bundle.receipt_set
        or expected.aggregations != bundle.path_aggregations
        or expected.work_vectors != bundle.work_vectors
        or expected.comparison_vectors != bundle.comparison_vectors
        or expected.projection_proofs != bundle.actual_projection_proofs
        or expected.occurrence_comparison_values != bundle.occurrence_comparison_values
        or any(row.counter_registry_id != registry.registry_id for row in bundle.work_vectors)
        or any(
            row.comparison_profile_id != comparison.comparison_profile_id
            for row in bundle.comparison_vectors
        )
        or any(
            row.actual_projection_profile_id != actual.actual_projection_profile_id
            or row.projection_term_count != EXPECTED_PROJECTION_TERM_COUNT
            for row in bundle.actual_projection_proofs
        )
        or any(
            tuple(item.path for item in row.records) != registry.required_paths
            for row in bundle.work_vectors
        )
        or bundle.output_commit.fixed_point_result_id != bundle.fixed_point.result_id
        or bundle.output_commit.shared_measurement_id
        != bundle.supervised_execution.measurement.measurement_id
    ):
        _fail("recovery accounting artifacts differ from exact replay")
    return bundle


__all__ = (
    "ConstructionK7RecoveryEligibleOccurrenceAccountingV1Error",
    "LOCAL_DOMAINS",
    "RecoveryEligibleOccurrenceAccountingBundleV1",
    "RecoveryEligibleOutputCommitV1",
    "RecoveryEligibleOutputRoleCommitV1",
    "RecoveryEligiblePathAggregationV1",
    "RecoveryEligibleSharedResourceReceiptSetV1",
    "RecoveryEligibleSharedResourceReceiptV1",
    "finalize_recovery_eligible_occurrence_accounting_v1",
    "run_recovery_eligible_occurrence_accounting_v1",
    "verify_recovery_eligible_occurrence_accounting_v1",
)
