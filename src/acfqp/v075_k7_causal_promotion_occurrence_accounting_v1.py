"""Owner-correct occurrence accounting for the K7 causal-promotion run.

The business occurrence runs once in a fresh sealed worker.  Its trusted
supervisor owns process, byte-traffic, peak, named-obligation, and hash-window
evidence.  This module replaces the twelve stage-local zero placeholders for
the nine occurrence-wide shared paths, reduces every other V6 path over all
twelve verified stages, solves the exact eight-role output-byte fixed point,
commits those eight roles once, and issues the formal
CounterRecord -> WorkVector -> ComparisonVector chain.

The result remains a construction-only noncertificate.  It joins the sealed
worker's exact registered-budget replay to the complete actual vector and
therefore emits one attempt-scoped ``ATTEMPT_BUDGET_EXHAUSTED`` typed terminal.
It does not implement the generic trusted-budget authority, close the logical
occurrence, run either official Gate, or set an official scalar.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
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
from acfqp.phase3e_ids import (
    V075_K7_CAUSAL_PROMOTION_OCCURRENCE_ACCOUNTING_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_OUTPUT_COMMIT_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_OUTPUT_RENDERER_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_PATH_AGGREGATION_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)
from acfqp import construction_accounting_live_v3 as live_v3
from acfqp import construction_accounting_owned_runtime_v2 as owned_v2
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp import construction_shared_resource_receipts_v1 as shared_v1
from acfqp import v075_k7_causal_promotion_accounted_executor_v1 as executor_v1
from acfqp import v075_k7_causal_promotion_terminal_authority_v1 as terminal_v1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.79"
PROFILE_KEY = "v075_k7_causal_promotion_occurrence_accounting_v1"

PATH_AGGREGATION_DOMAIN = (
    V075_K7_CAUSAL_PROMOTION_PATH_AGGREGATION_V1_DOMAIN
)
BUNDLE_DOMAIN = V075_K7_CAUSAL_PROMOTION_OCCURRENCE_ACCOUNTING_V1_DOMAIN
RENDERER_DOMAIN = V075_K7_CAUSAL_PROMOTION_OUTPUT_RENDERER_V1_DOMAIN
OUTPUT_COMMIT_DOMAIN = V075_K7_CAUSAL_PROMOTION_OUTPUT_COMMIT_V1_DOMAIN

EXPECTED_STAGE_COUNT = 12
EXPECTED_REQUIRED_PATH_COUNT = registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
EXPECTED_OPERATIONAL_PATH_COUNT = registry_v6.EXPECTED_V6_OPERATIONAL_LEAF_COUNT
EXPECTED_SHARED_PATH_COUNT = 9
EXPECTED_PROJECTION_TERM_COUNT = EXPECTED_OPERATIONAL_PATH_COUNT
SHARED_PATHS = shared_v1.SHARED_RESOURCE_PATHS
PRE_OUTPUT_SHARED_PATHS = tuple(
    path for path in SHARED_PATHS if path != "io.output_bytes"
)

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
SOURCE_KINDS = frozenset(
    {
        "STAGE_SUM",
        "STAGE_MAX",
        "SHARED_MEASUREMENT",
        "OUTPUT_FIXED_POINT",
        "SEMANTIC_DERIVED_RECONCILIATION",
    }
)


class V075K7CausalPromotionOccurrenceAccountingV1Error(RuntimeError):
    """One supervisor measurement, reduction, render, or commit failed."""


def _fail(message: str) -> NoReturn:
    raise V075K7CausalPromotionOccurrenceAccountingV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075K7CausalPromotionOccurrenceAccountingV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _domain_id(domain: str, payload: Mapping[str, Any]) -> str:
    return content_id(domain, dict(payload))


@dataclass(frozen=True, slots=True)
class OccurrencePathAggregationV1:
    occurrence_id: str
    supervised_execution_id: str
    path: str
    reducer: ReducerEnum
    value: int
    stage_record_ids: tuple[str, ...]
    source_kind: str
    source_evidence_id: str
    output_fixed_point_profile_id: str | None = None
    output_candidate: int | None = None

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "path aggregation occurrence")
        _cid(self.supervised_execution_id, "path aggregation execution")
        _cid(self.source_evidence_id, "path aggregation source evidence")
        try:
            object.__setattr__(self, "reducer", ReducerEnum(self.reducer))
        except (TypeError, ValueError) as error:
            raise V075K7CausalPromotionOccurrenceAccountingV1Error(
                "path aggregation reducer is invalid"
            ) from error
        _nonnegative(self.value, "path aggregation value")
        if (
            type(self.path) is not str
            or not self.path
            or type(self.stage_record_ids) is not tuple
            or len(self.stage_record_ids) != EXPECTED_STAGE_COUNT
            or type(self.source_kind) is not str
            or self.source_kind not in SOURCE_KINDS
        ):
            _fail("path aggregation structure changed")
        for record_id in self.stage_record_ids:
            _cid(record_id, "path aggregation stage record")
        is_output = self.path == "io.output_bytes"
        if (
            (self.output_fixed_point_profile_id is not None) != is_output
            or (self.output_candidate is not None) != is_output
            or (is_output and self.source_kind != "OUTPUT_FIXED_POINT")
        ):
            _fail("path aggregation fixed-point binding changed")
        if self.output_fixed_point_profile_id is not None:
            _cid(self.output_fixed_point_profile_id, "path aggregation profile")
            if self.output_candidate != self.value:
                _fail("output aggregation candidate/value differ")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_causal_promotion_path_aggregation.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "supervised_execution_id": self.supervised_execution_id,
            "path": self.path,
            "reducer": self.reducer.value,
            "value": self.value,
            "stage_record_ids": list(self.stage_record_ids),
            "source_kind": self.source_kind,
            "source_evidence_id": self.source_evidence_id,
            "output_fixed_point_profile_id": self.output_fixed_point_profile_id,
            "output_candidate": self.output_candidate,
            "all_stage_instances_retained": True,
            "shared_stage_placeholders_replaced_not_summed": (
                self.path in SHARED_PATHS
            ),
        }

    @property
    def aggregation_id(self) -> str:
        return _domain_id(PATH_AGGREGATION_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "path_aggregation_id": self.aggregation_id}


def _verified_stage_records(
    execution: executor_v1.SupervisedCausalPromotionExecutionV1,
) -> tuple[Any, Any, Any, Any, tuple[live_v3.RecordedStageWorkV3, ...]]:
    if type(execution) is not executor_v1.SupervisedCausalPromotionExecutionV1:
        _fail("occurrence accounting requires one exact supervised execution")
    if execution.execution_id != execution.measurement.measurement_id:
        _fail("supervised execution identity changed before aggregation")
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(
        registry,
        comparison,
    )
    rows = execution.recorded_stages
    if (
        len(rows) != EXPECTED_STAGE_COUNT
        or tuple(
            registry_v6.ConstructionStageKindV6(
                row.stage_start.stage_kind.value
            )
            for row in rows
        )
        != owned_v2.CANONICAL_CAUSAL_PROMOTION_STAGE_PLAN_V2
    ):
        _fail("occurrence aggregation requires exactly twelve ordered stages")
    for row in rows:
        live_v3.verify_recorded_stage_work_v3(
            row,
            registry,
            stage,
            comparison,
            actual,
        )
    if any(
        row.work_vector.values[path] != 0
        for row in rows
        for path in SHARED_PATHS
    ):
        _fail("stage-local shared placeholders became nonzero")
    return registry, stage, comparison, actual, rows


def _derived_reconciliation_values(
    execution: executor_v1.SupervisedCausalPromotionExecutionV1,
) -> dict[str, int]:
    science = execution.science_summary
    result = {
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
        result["route.attempts"]
        != result["route.successes"] + result["route.failures"]
        or result["solver.attempts"]
        != result["solver.successes"] + result["solver.failures"]
        or execution.measurement.fixed_values["process.launches"]
        != result["process.exit_successes"] + result["process.exit_failures"]
    ):
        _fail("supervised route/solver/process facts do not reconcile")
    return result


def _aggregation_value_and_source(
    *,
    execution: executor_v1.SupervisedCausalPromotionExecutionV1,
    path: str,
    reducer: ReducerEnum,
    stage_records: tuple[CounterRecordV1, ...],
    fixed_profile: fixed_v1.OutputBytesFixedPointProfileV1,
    output_candidate: int,
) -> tuple[int, str, str]:
    measurement = execution.measurement
    if path == "io.output_bytes":
        return (
            _nonnegative(output_candidate, "output fixed-point candidate"),
            "OUTPUT_FIXED_POINT",
            fixed_profile.profile_id,
        )
    if path == "io.mounted_bytes_peak":
        return (
            measurement.mounted_bytes_peak(output_candidate),
            "SHARED_MEASUREMENT",
            measurement.measurement_id,
        )
    if path in measurement.fixed_values:
        return (
            measurement.fixed_values[path],
            "SHARED_MEASUREMENT",
            measurement.measurement_id,
        )
    derived = _derived_reconciliation_values(execution)
    if path in derived:
        return (
            derived[path],
            "SEMANTIC_DERIVED_RECONCILIATION",
            measurement.operational_trace_id,
        )
    if reducer is ReducerEnum.SUM:
        return (
            sum(record.value for record in stage_records),
            "STAGE_SUM",
            execution.execution_id,
        )
    return (
        max(record.value for record in stage_records),
        "STAGE_MAX",
        execution.execution_id,
    )


def _build_aggregations(
    *,
    execution: executor_v1.SupervisedCausalPromotionExecutionV1,
    fixed_profile: fixed_v1.OutputBytesFixedPointProfileV1,
    output_candidate: int,
    verified: tuple[
        Any,
        Any,
        Any,
        Any,
        tuple[live_v3.RecordedStageWorkV3, ...],
    ],
) -> tuple[OccurrencePathAggregationV1, ...]:
    registry, _stage, _comparison, _actual, stages = verified
    if fixed_profile.execution_identity_id != execution.execution_id:
        _fail("output fixed-point profile crossed the supervised execution")
    records_by_path = tuple(
        {record.path: record for record in row.work_vector.records}
        for row in stages
    )
    if any(tuple(sorted(rows)) != registry.required_paths for rows in records_by_path):
        _fail("stage work-vector path inventory changed during aggregation")
    result: list[OccurrencePathAggregationV1] = []
    for path in registry.required_paths:
        leaf = registry.by_path[path]
        stage_records = tuple(rows[path] for rows in records_by_path)
        value, source_kind, source_evidence_id = _aggregation_value_and_source(
            execution=execution,
            path=path,
            reducer=leaf.reducer,
            stage_records=stage_records,
            fixed_profile=fixed_profile,
            output_candidate=output_candidate,
        )
        result.append(
            OccurrencePathAggregationV1(
                execution.measurement.occurrence_id,
                execution.execution_id,
                path,
                leaf.reducer,
                value,
                tuple(record.record_id for record in stage_records),
                source_kind,
                source_evidence_id,
                fixed_profile.profile_id if path == "io.output_bytes" else None,
                value if path == "io.output_bytes" else None,
            )
        )
    rows = tuple(result)
    if (
        len(rows) != EXPECTED_REQUIRED_PATH_COUNT
        or tuple(row.path for row in rows) != registry.required_paths
    ):
        _fail("occurrence path aggregation is incomplete or reordered")
    return rows


@dataclass(frozen=True, slots=True)
class _CandidateInvariantRowsV1:
    execution_id: str
    fixed_profile_id: str
    aggregations: tuple[OccurrencePathAggregationV1, ...]
    records: tuple[CounterRecordV1, ...]


def _candidate_invariant_rows(
    *,
    execution: executor_v1.SupervisedCausalPromotionExecutionV1,
    fixed_profile: fixed_v1.OutputBytesFixedPointProfileV1,
    verified: tuple[
        Any,
        Any,
        Any,
        Any,
        tuple[live_v3.RecordedStageWorkV3, ...],
    ],
) -> _CandidateInvariantRowsV1:
    registry = verified[0]
    aggregations = _build_aggregations(
        execution=execution,
        fixed_profile=fixed_profile,
        output_candidate=0,
        verified=verified,
    )
    records = tuple(
        CounterRecordV1(
            registry.registry_id,
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
        for row in aggregations
    )
    return _CandidateInvariantRowsV1(
        execution.execution_id,
        fixed_profile.profile_id,
        aggregations,
        records,
    )


def _materialize_candidate(
    *,
    execution: executor_v1.SupervisedCausalPromotionExecutionV1,
    fixed_profile: fixed_v1.OutputBytesFixedPointProfileV1,
    output_candidate: int,
    verified: tuple[
        Any,
        Any,
        Any,
        Any,
        tuple[live_v3.RecordedStageWorkV3, ...],
    ],
    invariant_rows: _CandidateInvariantRowsV1,
) -> tuple[
    tuple[OccurrencePathAggregationV1, ...],
    WorkVectorV1,
    ComparisonVectorV1,
    ActualProjectionProofV1,
]:
    registry, _stage, comparison, actual, _stages = verified
    if (
        invariant_rows.execution_id != execution.execution_id
        or invariant_rows.fixed_profile_id != fixed_profile.profile_id
    ):
        _fail("candidate-invariant rows crossed execution identities")
    aggregations_list = list(invariant_rows.aggregations)
    records_list = list(invariant_rows.records)
    for path in ("io.mounted_bytes_peak", "io.output_bytes"):
        index = registry.required_paths.index(path)
        prior = aggregations_list[index]
        value, source_kind, source_id = _aggregation_value_and_source(
            execution=execution,
            path=path,
            reducer=registry.by_path[path].reducer,
            stage_records=tuple(
                row.work_vector.records[index]
                for row in execution.recorded_stages
            ),
            fixed_profile=fixed_profile,
            output_candidate=output_candidate,
        )
        changed = replace(
            prior,
            value=value,
            source_kind=source_kind,
            source_evidence_id=source_id,
            output_candidate=value if path == "io.output_bytes" else None,
        )
        leaf = registry.by_path[path]
        aggregations_list[index] = changed
        records_list[index] = CounterRecordV1(
            registry.registry_id,
            path,
            value,
            True,
            changed.aggregation_id,
            leaf.semantics_id,
            leaf.owner,
            leaf.unit,
            leaf.lane,
            leaf.scope,
            leaf.reducer,
        )
    aggregations = tuple(aggregations_list)
    records = tuple(records_list)
    vector = WorkVectorV1(
        registry.registry_id,
        execution.measurement.occurrence_id,
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        records,
    )
    values = vector.values
    for record in records:
        record.verify_against(registry.by_path[record.path])
    if (
        tuple(record.path for record in records) != registry.required_paths
        or len(records) != EXPECTED_REQUIRED_PATH_COUNT
        or values["route.attempts"]
        != values["route.successes"] + values["route.failures"]
        or values["solver.attempts"]
        != values["solver.successes"] + values["solver.failures"]
        or values["process.launches"]
        != values["process.exit_successes"] + values["process.exit_failures"]
    ):
        _fail("occurrence WorkVector is incomplete or unreconciled")
    forbidden = tuple(
        path
        for path, value in values.items()
        if value
        and (
            path.startswith("fallback.")
            or path.startswith("rebuild.")
            or path.startswith("local.")
        )
    )
    if forbidden:
        _fail(f"failed-prefix vector contains forbidden route work: {forbidden!r}")
    axes = {axis: 0 for axis in SHARED_AXES}
    for term in actual.terms:
        contribution = values[term.source_leaf] * term.coefficient
        if term.reducer is ReducerEnum.SUM:
            axes[term.target_axis] += contribution
        else:
            axes[term.target_axis] = max(
                axes[term.target_axis],
                contribution,
            )
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
        ActualWorkScope.COMMON_PREFIX,
        len(actual.terms),
    )
    if len(actual.terms) != EXPECTED_PROJECTION_TERM_COUNT:
        _fail("occurrence projection does not cover 182 operational leaves")
    return aggregations, vector, projected, proof


@dataclass(frozen=True, slots=True)
class _RenderedCandidateV1:
    aggregations: tuple[OccurrencePathAggregationV1, ...]
    work_vector: WorkVectorV1
    comparison_vector: ComparisonVectorV1
    projection_proof: ActualProjectionProofV1
    role_bytes: Mapping[str, bytes]


def _candidate_independent_role_bytes(
    execution: executor_v1.SupervisedCausalPromotionExecutionV1,
) -> Mapping[str, bytes]:
    science = execution.science_summary
    return MappingProxyType(
        {
            "BUSINESS_RESULT": canonical_json_bytes(
                {
                    "artifact_role": "BUSINESS_RESULT",
                    "schema": "acfqp.v075_k7_causal_promotion_business_result.v2",
                    "schema_version": "2.0.0",
                    "profile_key": PROFILE_KEY,
                    "occurrence_id": execution.measurement.occurrence_id,
                    "accounted_occurrence_id": (
                        execution.measurement.accounted_occurrence_id
                    ),
                    "owned_accounting_result_id": (
                        execution.measurement.owned_accounting_result_id
                    ),
                    "budget_closure_id": science["budget_closure_id"],
                    "shared_measurement_id": execution.measurement.measurement_id,
                    "runtime_preparation": execution.preparation.to_document(),
                    "supervised_request": dict(execution.request_document),
                    "shared_measurement": execution.measurement.to_document(),
                    "terminal_target_class": (
                        "ATTEMPT_CLOSURE_NONCERTIFICATE"
                    ),
                    "terminal_target_code": "ATTEMPT_BUDGET_EXHAUSTED",
                    "construction_only": True,
                    "official_execution_allowed": False,
                }
            ),
            "OPERATIONAL_TRACE": execution.trace_raw,
        }
    )


def _render_candidate(
    *,
    execution: executor_v1.SupervisedCausalPromotionExecutionV1,
    fixed_profile: fixed_v1.OutputBytesFixedPointProfileV1,
    output_candidate: int,
    verified: tuple[
        Any,
        Any,
        Any,
        Any,
        tuple[live_v3.RecordedStageWorkV3, ...],
    ],
    static_role_bytes: Mapping[str, bytes],
    invariant_rows: _CandidateInvariantRowsV1,
) -> _RenderedCandidateV1:
    aggregations, vector, comparison, proof = _materialize_candidate(
        execution=execution,
        fixed_profile=fixed_profile,
        output_candidate=output_candidate,
        verified=verified,
        invariant_rows=invariant_rows,
    )
    if (
        tuple(static_role_bytes) != ("BUSINESS_RESULT", "OPERATIONAL_TRACE")
        or any(type(raw) is not bytes or not raw for raw in static_role_bytes.values())
    ):
        _fail("candidate-independent role cache is malformed")
    role_bytes: dict[str, bytes] = dict(static_role_bytes)
    terminal = terminal_v1.issue_v075_k7_causal_promotion_budget_terminal_v1(
        budget_replay_attestation=(
            execution.trace_document["budget_replay_attestation"]
        ),
        occurrence_id=vector.subject_id,
        accounted_occurrence_id=execution.measurement.accounted_occurrence_id,
        supervised_execution_id=execution.execution_id,
        work_vector_id=vector.work_vector_id,
        comparison_vector_id=comparison.comparison_vector_id,
        projection_proof_id=proof.actual_projection_proof_id,
    )
    role_bytes["TERMINAL_ARTIFACT"] = canonical_json_bytes(
        terminal.to_role_document(output_bytes=output_candidate)
    )
    role_bytes["COUNTER_RECORD_SET"] = canonical_json_bytes(
        {
            "artifact_role": "COUNTER_RECORD_SET",
            "schema": "acfqp.v075_k7_causal_promotion_counter_record_set.v1",
            "occurrence_id": vector.subject_id,
            "io.output_bytes": output_candidate,
            "counter_record_count": len(vector.records),
            "path_aggregations": [row.to_document() for row in aggregations],
            "counter_records": [row.to_dict() for row in vector.records],
        }
    )
    role_bytes["WORK_VECTOR"] = canonical_json_bytes(
        {
            "artifact_role": "WORK_VECTOR",
            "schema": "acfqp.v075_k7_causal_promotion_work_vector_artifact.v1",
            "io.output_bytes": output_candidate,
            "work_vector": vector.to_dict(),
        }
    )
    role_bytes["COMPARISON_VECTOR"] = canonical_json_bytes(
        {
            "artifact_role": "COMPARISON_VECTOR",
            "schema": (
                "acfqp.v075_k7_causal_promotion_comparison_vector_artifact.v1"
            ),
            "io.output_bytes": output_candidate,
            "comparison_vector": comparison.to_dict(),
        }
    )
    role_bytes["ACTUAL_PROJECTION_PROOF"] = canonical_json_bytes(
        {
            "artifact_role": "ACTUAL_PROJECTION_PROOF",
            "schema": "acfqp.v075_k7_causal_promotion_projection_artifact.v1",
            "io.output_bytes": output_candidate,
            "actual_projection_proof": proof.to_dict(),
        }
    )
    preceding = [
        {
            "artifact_role": role,
            "byte_count": len(raw),
            "bytes_sha256": hashlib.sha256(raw).hexdigest(),
        }
        for role, raw in role_bytes.items()
    ]
    role_bytes["OUTPUT_MANIFEST"] = canonical_json_bytes(
        {
            "artifact_role": "OUTPUT_MANIFEST",
            "schema": "acfqp.v075_k7_causal_promotion_output_manifest.v1",
            "occurrence_id": vector.subject_id,
            "output_bytes_fixed_point_profile_id": fixed_profile.profile_id,
            "io.output_bytes": output_candidate,
            "ordered_preceding_roles": preceding,
            "output_manifest_self_extent_excluded_from_preceding_rows": True,
            "required_role_order": list(
                fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
            ),
        }
    )
    if tuple(role_bytes) != fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES:
        _fail("rendered causal-promotion role order changed")
    return _RenderedCandidateV1(
        aggregations,
        vector,
        comparison,
        proof,
        MappingProxyType(role_bytes),
    )


@dataclass(frozen=True, slots=True)
class OutputRoleCommitV1:
    artifact_role: str
    filename: str
    byte_count: int
    bytes_sha256: str

    def __post_init__(self) -> None:
        if (
            self.artifact_role
            not in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
            or self.filename != f"{self.artifact_role}.json"
            or type(self.byte_count) is not int
            or self.byte_count <= 0
        ):
            _fail("output role commit is malformed")
        _cid(self.bytes_sha256, "output role SHA-256")

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
class CausalPromotionOutputCommitV1:
    occurrence_id: str
    fixed_point_result_id: str
    shared_measurement_id: str
    role_commits: tuple[OutputRoleCommitV1, ...]
    output_bytes: int

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "output commit occurrence")
        _cid(self.fixed_point_result_id, "output commit fixed point")
        _cid(self.shared_measurement_id, "output commit measurement")
        if (
            type(self.role_commits) is not tuple
            or tuple(row.artifact_role for row in self.role_commits)
            != fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
            or sum(row.byte_count for row in self.role_commits) != self.output_bytes
            or self.output_bytes <= 0
        ):
            _fail("output commit role inventory or byte total changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_causal_promotion_output_commit.v1",
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
        return _domain_id(OUTPUT_COMMIT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "output_commit_id": self.output_commit_id}


def _commit_role_bytes(
    *,
    execution: executor_v1.SupervisedCausalPromotionExecutionV1,
    fixed_point: fixed_v1.OutputBytesFixedPointResultV1,
    output_directory: Path,
    pending_trace_path: Path,
) -> CausalPromotionOutputCommitV1:
    directory = output_directory.resolve(strict=True)
    info = directory.stat()
    if (
        directory.is_symlink()
        or not directory.is_dir()
        or stat.S_IMODE(info.st_mode) & 0o077
    ):
        _fail("output directory must be one private real directory")
    expected_pending = directory / ".OPERATIONAL_TRACE.pending"
    if pending_trace_path != expected_pending:
        _fail("operational trace pending path changed")
    existing = tuple(sorted(path.name for path in directory.iterdir()))
    if existing != (expected_pending.name,):
        _fail("output directory contains material outside the pending trace")
    if (
        pending_trace_path.is_symlink()
        or not pending_trace_path.is_file()
        or pending_trace_path.read_bytes() != execution.trace_raw
    ):
        _fail("pending operational trace differs from supervised bytes")
    role_bytes = fixed_point.artifact_bytes_by_role
    if role_bytes["OPERATIONAL_TRACE"] != execution.trace_raw:
        _fail("fixed point replaced the worker operational trace")

    commits: list[OutputRoleCommitV1] = []
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
                written = 0
                while written < len(raw):
                    count = os.write(descriptor, raw[written:])
                    if count <= 0:
                        _fail("output role write made no progress")
                    written += count
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
            _fail("committed output role identity or mode changed")
        commits.append(
            OutputRoleCommitV1(
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
    if tuple(sorted(path.name for path in directory.iterdir())) != tuple(
        sorted(f"{role}.json" for role in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES)
    ):
        _fail("committed output directory role set changed")
    return CausalPromotionOutputCommitV1(
        execution.measurement.occurrence_id,
        fixed_point.result_id,
        execution.measurement.measurement_id,
        tuple(commits),
        fixed_point.output_bytes,
    )


@dataclass(frozen=True, slots=True)
class CausalPromotionOccurrenceAccountingBundleV1:
    supervised_execution: executor_v1.SupervisedCausalPromotionExecutionV1 = field(
        repr=False,
        compare=False,
    )
    fixed_point: fixed_v1.OutputBytesFixedPointResultV1 = field(
        repr=False,
        compare=False,
    )
    output_commit: CausalPromotionOutputCommitV1
    path_aggregations: tuple[OccurrencePathAggregationV1, ...] = field(repr=False)
    work_vector: WorkVectorV1 = field(repr=False)
    comparison_vector: ComparisonVectorV1 = field(repr=False)
    actual_projection_proof: ActualProjectionProofV1 = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.supervised_execution)
            is not executor_v1.SupervisedCausalPromotionExecutionV1
            or type(self.fixed_point) is not fixed_v1.OutputBytesFixedPointResultV1
            or type(self.output_commit) is not CausalPromotionOutputCommitV1
            or len(self.path_aggregations) != EXPECTED_REQUIRED_PATH_COUNT
            or len(self.work_vector.records) != EXPECTED_REQUIRED_PATH_COUNT
            or self.work_vector.subject_id
            != self.supervised_execution.measurement.occurrence_id
            or self.work_vector.values["io.output_bytes"]
            != self.fixed_point.output_bytes
            or self.work_vector.values["io.mounted_bytes_peak"]
            != self.supervised_execution.measurement.mounted_bytes_peak(
                self.fixed_point.output_bytes
            )
            or self.output_commit.output_bytes != self.fixed_point.output_bytes
            or self.comparison_vector.work_vector_id
            != self.work_vector.work_vector_id
            or self.actual_projection_proof.work_vector_id
            != self.work_vector.work_vector_id
            or self.actual_projection_proof.comparison_vector_id
            != self.comparison_vector.comparison_vector_id
        ):
            _fail("causal-promotion accounting bundle is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_causal_promotion_occurrence_accounting.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.work_vector.subject_id,
            "accounted_occurrence_id": (
                self.supervised_execution.measurement.accounted_occurrence_id
            ),
            "supervised_execution_id": self.supervised_execution.execution_id,
            "shared_measurement_id": (
                self.supervised_execution.measurement.measurement_id
            ),
            "output_bytes_fixed_point_result_id": self.fixed_point.result_id,
            "output_commit_id": self.output_commit.output_commit_id,
            "path_aggregation_ids": [
                row.aggregation_id for row in self.path_aggregations
            ],
            "counter_record_ids": [row.record_id for row in self.work_vector.records],
            "work_vector_id": self.work_vector.work_vector_id,
            "comparison_vector_id": self.comparison_vector.comparison_vector_id,
            "actual_projection_proof_id": (
                self.actual_projection_proof.actual_projection_proof_id
            ),
            "shared_resource_path_count": EXPECTED_SHARED_PATH_COUNT,
            "shared_resource_paths": list(SHARED_PATHS),
            "shared_resource_measurement_complete": True,
            "complete_202_counter_record_chain_present": True,
            "occurrence_work_vector_issued": True,
            "comparison_vector_issued": True,
            "actual_projection_proof_issued": True,
            "all_182_operational_leaves_projected_exactly_once": True,
            "stage_local_records_retained": (
                EXPECTED_STAGE_COUNT * EXPECTED_REQUIRED_PATH_COUNT
            ),
            "eight_operational_roles_committed_once": True,
            "terminal_candidate_rendered": False,
            "semantic_terminal_artifact_issued": True,
            "semantic_terminal_scope": "ROUTE_ATTEMPT",
            "semantic_terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "semantic_terminal_code": "ATTEMPT_BUDGET_EXHAUSTED",
            "generic_trusted_budget_replay_v1_implemented": False,
            "logical_occurrence_closed": False,
            "campaign_closure_issued": False,
            "counter_completeness_gate_status": (
                "COUNTER_COMPLETENESS_GATE_NOT_RUN"
            ),
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }

    @property
    def bundle_id(self) -> str:
        return _domain_id(BUNDLE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_accounting_bundle_id": self.bundle_id}


def _renderer_components(
    execution: executor_v1.SupervisedCausalPromotionExecutionV1,
) -> tuple[
    tuple[Any, Any, Any, Any, tuple[live_v3.RecordedStageWorkV3, ...]],
    fixed_v1.OutputBytesFixedPointProfileV1,
    Mapping[str, bytes],
    _CandidateInvariantRowsV1,
]:
    verified = _verified_stage_records(execution)
    renderer_id = _domain_id(
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
        max_total_bytes=256 * 1024 * 1024,
        role_byte_caps={
            role: 128 * 1024 * 1024
            for role in fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
        },
        max_iterations=32,
    )
    static = _candidate_independent_role_bytes(execution)
    invariant = _candidate_invariant_rows(
        execution=execution,
        fixed_profile=profile,
        verified=verified,
    )
    return verified, profile, static, invariant


def finalize_v075_causal_promotion_occurrence_accounting_v1(
    *,
    supervised_execution: executor_v1.SupervisedCausalPromotionExecutionV1,
    output_directory: str | Path,
    pending_trace_path: str | Path,
) -> CausalPromotionOccurrenceAccountingBundleV1:
    """Solve, commit, and issue the formal occurrence accounting chain."""

    verified, profile, static, invariant = _renderer_components(
        supervised_execution
    )

    def renderer(candidate: int) -> dict[str, bytes]:
        return dict(
            _render_candidate(
                execution=supervised_execution,
                fixed_profile=profile,
                output_candidate=candidate,
                verified=verified,
                static_role_bytes=static,
                invariant_rows=invariant,
            ).role_bytes
        )

    fixed_point = fixed_v1.solve_output_bytes_fixed_point_v1(
        profile=profile,
        renderer=renderer,
    )
    fixed_v1.replay_output_bytes_fixed_point_v1(
        result=fixed_point,
        renderer=renderer,
    )
    final = _render_candidate(
        execution=supervised_execution,
        fixed_profile=profile,
        output_candidate=fixed_point.output_bytes,
        verified=verified,
        static_role_bytes=static,
        invariant_rows=invariant,
    )
    if dict(final.role_bytes) != fixed_point.artifact_bytes_by_role:
        _fail("final materialization differs from fixed-point bytes")
    commit = _commit_role_bytes(
        execution=supervised_execution,
        fixed_point=fixed_point,
        output_directory=Path(output_directory),
        pending_trace_path=Path(pending_trace_path).resolve(strict=True),
    )
    result = CausalPromotionOccurrenceAccountingBundleV1(
        supervised_execution,
        fixed_point,
        commit,
        final.aggregations,
        final.work_vector,
        final.comparison_vector,
        final.projection_proof,
    )
    return verify_v075_causal_promotion_occurrence_accounting_v1(result)


def run_v075_causal_promotion_occurrence_accounting_v1(
    *,
    repository_root: str | Path,
    runtime_cas_root: str | Path,
    output_directory: str | Path,
    construction_fixture_marker: str = "nonfresh-k7-causal-promotion",
    timeout_seconds: int = executor_v1.DEFAULT_TIMEOUT_SECONDS,
) -> CausalPromotionOccurrenceAccountingBundleV1:
    """Prepare outside the cutoff, then run and account one occurrence."""

    output = Path(output_directory)
    if output.exists():
        _fail("output directory must be absent before construction")
    output.mkdir(mode=0o700, parents=False)
    preparation = executor_v1.prepare_v075_k7_causal_promotion_accounted_runtime_v1(
        repository_root=repository_root,
        runtime_cas_root=runtime_cas_root,
    )
    pending_trace = output.resolve(strict=True) / ".OPERATIONAL_TRACE.pending"
    execution = executor_v1.execute_v075_k7_causal_promotion_accounted_v1(
        preparation,
        trace_output_path=pending_trace,
        construction_fixture_marker=construction_fixture_marker,
        timeout_seconds=timeout_seconds,
    )
    return finalize_v075_causal_promotion_occurrence_accounting_v1(
        supervised_execution=execution,
        output_directory=output,
        pending_trace_path=pending_trace,
    )


def verify_v075_causal_promotion_occurrence_accounting_v1(
    bundle: CausalPromotionOccurrenceAccountingBundleV1,
) -> CausalPromotionOccurrenceAccountingBundleV1:
    """Replay the stage reduction, fixed point, and exact V6 projection."""

    if type(bundle) is not CausalPromotionOccurrenceAccountingBundleV1:
        _fail("occurrence accounting verifier received a foreign bundle")
    verified, profile, static, invariant = _renderer_components(
        bundle.supervised_execution
    )
    registry, _stage, comparison, actual, _rows = verified
    if profile != bundle.fixed_point.profile:
        _fail("accounting bundle fixed-point profile changed")

    def renderer(candidate: int) -> dict[str, bytes]:
        return dict(
            _render_candidate(
                execution=bundle.supervised_execution,
                fixed_profile=profile,
                output_candidate=candidate,
                verified=verified,
                static_role_bytes=static,
                invariant_rows=invariant,
            ).role_bytes
        )

    fixed_v1.replay_output_bytes_fixed_point_v1(
        result=bundle.fixed_point,
        renderer=renderer,
    )
    expected = _render_candidate(
        execution=bundle.supervised_execution,
        fixed_profile=profile,
        output_candidate=bundle.fixed_point.output_bytes,
        verified=verified,
        static_role_bytes=static,
        invariant_rows=invariant,
    )
    expected_commit = tuple(
        OutputRoleCommitV1(
            role,
            f"{role}.json",
            len(raw),
            hashlib.sha256(raw).hexdigest(),
        )
        for role, raw in expected.role_bytes.items()
    )
    if (
        expected.aggregations != bundle.path_aggregations
        or expected.work_vector != bundle.work_vector
        or expected.comparison_vector != bundle.comparison_vector
        or expected.projection_proof != bundle.actual_projection_proof
        or dict(expected.role_bytes) != bundle.fixed_point.artifact_bytes_by_role
        or expected_commit != bundle.output_commit.role_commits
        or bundle.output_commit.fixed_point_result_id != bundle.fixed_point.result_id
        or bundle.output_commit.shared_measurement_id
        != bundle.supervised_execution.measurement.measurement_id
        or bundle.work_vector.counter_registry_id != registry.registry_id
        or bundle.comparison_vector.comparison_profile_id
        != comparison.comparison_profile_id
        or bundle.actual_projection_proof.actual_projection_profile_id
        != actual.actual_projection_profile_id
        or bundle.actual_projection_proof.projection_term_count
        != EXPECTED_PROJECTION_TERM_COUNT
        or tuple(row.path for row in bundle.work_vector.records)
        != registry.required_paths
    ):
        _fail("occurrence accounting artifacts differ from exact replay")
    return bundle


__all__ = (
    "BUNDLE_DOMAIN",
    "CausalPromotionOccurrenceAccountingBundleV1",
    "CausalPromotionOutputCommitV1",
    "EXPECTED_REQUIRED_PATH_COUNT",
    "EXPECTED_SHARED_PATH_COUNT",
    "OccurrencePathAggregationV1",
    "OUTPUT_COMMIT_DOMAIN",
    "PATH_AGGREGATION_DOMAIN",
    "PRE_OUTPUT_SHARED_PATHS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "RENDERER_DOMAIN",
    "SCHEMA_VERSION",
    "SHARED_PATHS",
    "V075K7CausalPromotionOccurrenceAccountingV1Error",
    "finalize_v075_causal_promotion_occurrence_accounting_v1",
    "run_v075_causal_promotion_occurrence_accounting_v1",
    "verify_v075_causal_promotion_occurrence_accounting_v1",
)
