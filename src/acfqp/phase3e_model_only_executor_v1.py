"""Fresh-process, native-accounted producer for a model-only RAPM query.

This is a deliberately non-official bridge between the pure serialized RAPM
consumer and the later PASS/FAIL consumers.  The portable planner and sound
audit run once in a fresh ``python -I`` process.  The host validates the
transport, selected-plan and campaign bindings without invoking the planner,
then materializes an explicit-zero ``WorkVectorV1`` and its exact comparison
projection.  PASS and FAIL are distinct typed executions: PASS uses
``ABSTRACT_ONLY_CERTIFICATE`` while FAIL is retained as an
``ABSTRACT_FAILED_PREFIX`` / ``COMMON_PREFIX`` input to later routing.

V1 does not claim a sealed OS namespace, a preregistered runtime-tree cap, full
content-ID hash instrumentation, or native counters for every abstract
candidate/dominance operation.  Those omissions are embedded in the result;
official execution and both Phase-3E gates remain locked.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Mapping
import weakref

from acfqp.accounting_v1 import (
    ComparisonVectorV1,
    NativeZeroAttestationV1,
    ReconciliationProofV1,
    RouteKindEnum,
    WorkVectorV1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualWorkScope,
    official_actual_projection_profile_v1,
)
from acfqp.campaign_v1 import (
    COUNTER_COMPLETENESS_GATE_NOT_RUN,
    WORKLOAD_ECONOMICS_GATE_NOT_RUN,
    LogicalOccurrenceV1,
    RebuildPolicyV1,
    RouteAttemptV1,
)
from acfqp.native_recorder_v1 import (
    NativeCounterRecorderV1,
    RecordedWorkV1,
    verify_recorded_work_v1,
)
from acfqp.phase3e_ids import (
    MODEL_ONLY_ORCHESTRATION_BINDING_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
)
from acfqp.phase3e_model_only_v1 import (
    ModelOnlyOutcome,
    ModelOnlyPhase3EIdentitiesV1,
    Phase3EModelOnlyResultV1,
    _campaign_bindings_v1,
    derive_model_only_phase3e_identities_v1,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    ModelOnlyRAPMSourceV1,
    RAPMSourceLeaseV1,
    SelectedContingentPlanV1,
    _mint_model_only_source_from_loader_sealed_transport_v1,
    require_model_only_source_authority_v1,
)
from acfqp.portable import PortableQuery, PortableRAPM, fraction_to_json
from acfqp.portable_sound_audit_v1 import (
    AbstractPlanAuditV1,
    PortableSoundBellmanProofV1,
)
from acfqp.routing_v1 import RouteDecisionContextV1


SCHEMA_VERSION = "1.0.0"
REQUEST_SCHEMA = "acfqp.phase3e_model_only_execution_request.v1"
EVENT_TRACE_SCHEMA = "acfqp.phase3e_model_only_native_event_trace.v1"
WORKER_OUTPUT_SCHEMA = "acfqp.phase3e_model_only_worker_output.v1"
EXECUTION_SCHEMA = "acfqp.phase3e_model_only_operational_execution.v1"
ISOLATION_PROFILE_ID = "fresh_python_I_process_import_denylist_v1"
COUNTER_COVERAGE_STATUS = "PARTIAL_NATIVE_COUNTER_COVERAGE_NONOFFICIAL_V1"
RUNTIME_ENTRYPOINT = "acfqp/phase3e_model_only_runtime_v1.py"
# Contracted recorder identity consumed by phase3e_abstract_pass_closure_v1.
# Kept literal here so the fresh planner runtime does not import terminal or
# semantic-verifier machinery merely to name its accounting provenance.
MODEL_ONLY_NATIVE_RECORDER_ID = "phase3e-model-only-native-recorder-v1"
_REQUIRED_POSITIVE_MODEL_ONLY_COUNTERS = (
    "common.abstract_bellman_backups",
    "common.abstract_audit_obligations",
    "common.integrity_checks",
    "common.protocol_checks",
    "common.hash_invocations",
    "io.read_bytes",
)

COUNTER_COVERAGE_BLOCKERS = (
    "ABSTRACT_CANDIDATE_AND_DOMINANCE_FAMILIES_NOT_REGISTERED",
    "CONTENT_ID_HASH_INVOCATIONS_NOT_GLOBALLY_HOOKED",
    "RUNTIME_TREE_AND_RESOURCE_CAP_NOT_SEALED",
    "WORKER_EVENT_TRACE_HAS_NO_SEALED_ATTESTATION",
    "WORKER_RESULT_REQUIRES_EXTERNAL_SEMANTIC_AUDIT_AUTHORITY",
    "VISIBLE_RUNTIME_MOUNT_AND_IMPORT_BYTES_NOT_FULLY_ACCOUNTED",
)

_TRACE_PATHS = frozenset(
    {
        "common.abstract_bellman_backups",
        "common.abstract_audit_obligations",
        "common.integrity_checks",
        "common.protocol_checks",
        "common.hash_invocations",
    }
)


class Phase3EModelOnlyExecutorV1Error(ValueError):
    """The process, transport, source binding, or accounting failed closed."""


@dataclass(frozen=True, slots=True)
class ModelOnlyProcessFailureEvidenceV1:
    request_id: str
    returncode: int | None
    staged_bytes: int
    output_bytes_observed: int
    stdout: str
    stderr: str
    failure_kind: str
    official_execution_allowed: bool = False

    def __post_init__(self) -> None:
        parse_content_id(self.request_id)
        if self.returncode is not None and type(self.returncode) is not int:
            raise Phase3EModelOnlyExecutorV1Error("returncode must be int or null")
        for name in ("staged_bytes", "output_bytes_observed"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise Phase3EModelOnlyExecutorV1Error(f"{name} must be nonnegative")
        if type(self.failure_kind) is not str or not self.failure_kind:
            raise Phase3EModelOnlyExecutorV1Error("failure_kind must be nonempty")
        if self.official_execution_allowed is not False:
            raise Phase3EModelOnlyExecutorV1Error("failure cannot unlock execution")


class ModelOnlyProcessFailedV1(Phase3EModelOnlyExecutorV1Error):
    def __init__(self, evidence: ModelOnlyProcessFailureEvidenceV1) -> None:
        self.evidence = evidence
        super().__init__(
            f"model-only worker failed closed: {evidence.failure_kind}; "
            f"rc={evidence.returncode}"
        )


class ModelOnlyNoncertificateOutcomeV1(Phase3EModelOnlyExecutorV1Error):
    """Compatibility wrapper observed a sound, honestly accounted FAIL."""

    def __init__(
        self,
        *,
        request_id: str,
        worker_output_id: str,
        result: Phase3EModelOnlyResultV1,
        event_trace: "ModelOnlyNativeEventTraceV1",
        execution: "ModelOnlyQueryExecutionV1",
    ) -> None:
        self.request_id = request_id
        self.worker_output_id = worker_output_id
        self.result = result
        self.event_trace = event_trace
        self.execution = execution
        self.recorded_work = execution.recorded_work
        super().__init__(
            "model-only audit returned an accounted ABSTRACT_FAILED_PREFIX; "
            "the PASS-only compatibility API cannot return it as a certificate"
        )


def _artifact_id(role: str, payload: Mapping[str, Any]) -> str:
    return content_id(
        MODEL_ONLY_ORCHESTRATION_BINDING_DOMAIN,
        {
            "schema": "acfqp.phase3e_model_only_execution_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "role": role,
            "payload": dict(payload),
        },
    )


def _plain_canonical_document(raw: bytes) -> Mapping[str, Any]:
    # First pass rejects whitespace, duplicate keys, non-reduced rationals and
    # other alternate encodings.  A plain second pass preserves rational JSON
    # records for the portable V1 parsers.
    loads_canonical_json(raw)
    value = json.loads(raw.decode("utf-8"))
    if type(value) is not dict:
        raise Phase3EModelOnlyExecutorV1Error("canonical document root must be object")
    return value


@dataclass(frozen=True, slots=True)
class ModelOnlyExecutionRequestV1:
    source_lease: RAPMSourceLeaseV1
    portable_rapm_base64: str
    portable_query_base64: str
    regret_tolerance: Fraction

    def __post_init__(self) -> None:
        if type(self.source_lease) is not RAPMSourceLeaseV1:
            raise Phase3EModelOnlyExecutorV1Error("request requires exact source lease")
        for name in ("portable_rapm_base64", "portable_query_base64"):
            value = getattr(self, name)
            if type(value) is not str or not value:
                raise Phase3EModelOnlyExecutorV1Error(f"{name} must be nonempty")
            try:
                base64.b64decode(value, validate=True)
            except ValueError as error:
                raise Phase3EModelOnlyExecutorV1Error(
                    f"{name} is not canonical base64"
                ) from error
        if type(self.regret_tolerance) is not Fraction or self.regret_tolerance < 0:
            raise Phase3EModelOnlyExecutorV1Error(
                "request regret_tolerance must be nonnegative exact Fraction"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": REQUEST_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "source_lease": self.source_lease.to_dict(),
            "portable_rapm_base64": self.portable_rapm_base64,
            "portable_query_base64": self.portable_query_base64,
            "regret_tolerance": fraction_to_json(self.regret_tolerance),
        }

    @property
    def request_id(self) -> str:
        return _artifact_id("model_only_execution_request", self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "request_id": self.request_id}


def parse_model_only_execution_request_v1(
    document: Mapping[str, Any],
) -> ModelOnlyExecutionRequestV1:
    require_exact_fields(
        document,
        {
            "schema",
            "schema_version",
            "source_lease",
            "portable_rapm_base64",
            "portable_query_base64",
            "regret_tolerance",
            "request_id",
        },
        context="ModelOnlyExecutionRequestV1",
    )
    if (
        document["schema"] != REQUEST_SCHEMA
        or document["schema_version"] != SCHEMA_VERSION
    ):
        raise Phase3EModelOnlyExecutorV1Error("execution request schema mismatch")
    tolerance = document["regret_tolerance"]
    if type(tolerance) is dict:
        from acfqp.portable import fraction_from_json

        tolerance = fraction_from_json(tolerance, field="request regret_tolerance")
    request = ModelOnlyExecutionRequestV1(
        RAPMSourceLeaseV1.from_dict(document["source_lease"]),
        document["portable_rapm_base64"],
        document["portable_query_base64"],
        tolerance,
    )
    if document["request_id"] != request.request_id:
        raise Phase3EModelOnlyExecutorV1Error("execution request ID mismatch")
    return request


def model_only_execution_request_v1(
    source: ModelOnlyRAPMSourceV1,
    *,
    regret_tolerance: Fraction | int = Fraction(1, 20),
) -> ModelOnlyExecutionRequestV1:
    try:
        require_model_only_source_authority_v1(source)
    except ValueError as error:
        raise Phase3EModelOnlyExecutorV1Error(
            f"executor input lacks live source authority: {error}"
        ) from error
    if isinstance(regret_tolerance, bool) or not isinstance(
        regret_tolerance, (int, Fraction)
    ):
        raise Phase3EModelOnlyExecutorV1Error(
            "regret_tolerance must be an exact int or Fraction"
        )
    tolerance = Fraction(regret_tolerance)
    if tolerance < 0:
        raise Phase3EModelOnlyExecutorV1Error(
            "regret_tolerance must be nonnegative"
        )
    model_bytes = bytes(source.portable_rapm_source_bytes)
    query_bytes = bytes(source.portable_query_source_bytes)
    if (
        hashlib.sha256(model_bytes).hexdigest()
        != source.lease.portable_rapm_sha256
        or hashlib.sha256(query_bytes).hexdigest()
        != source.lease.portable_query_sha256
    ):
        raise Phase3EModelOnlyExecutorV1Error(
            "retained model/query bytes no longer match the verified source lease"
        )
    return ModelOnlyExecutionRequestV1(
        source.lease,
        base64.b64encode(model_bytes).decode("ascii"),
        base64.b64encode(query_bytes).decode("ascii"),
        tolerance,
    )


def reconstruct_model_only_source_from_request_v1(
    request: ModelOnlyExecutionRequestV1,
) -> ModelOnlyRAPMSourceV1:
    if type(request) is not ModelOnlyExecutionRequestV1:
        raise Phase3EModelOnlyExecutorV1Error("invalid execution request runtime type")
    model_bytes = base64.b64decode(request.portable_rapm_base64, validate=True)
    query_bytes = base64.b64decode(request.portable_query_base64, validate=True)
    if (
        hashlib.sha256(model_bytes).hexdigest()
        != request.source_lease.portable_rapm_sha256
        or hashlib.sha256(query_bytes).hexdigest()
        != request.source_lease.portable_query_sha256
    ):
        raise Phase3EModelOnlyExecutorV1Error("request source-byte digest mismatch")
    try:
        model_document = json.loads(model_bytes.decode("utf-8"))
        query_document = json.loads(query_bytes.decode("utf-8"))
        model = PortableRAPM.from_dict(model_document)
        query = PortableQuery.from_dict(query_document, model)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise Phase3EModelOnlyExecutorV1Error(
            f"request portable source is invalid: {error}"
        ) from error
    # This is the isolated runtime's equivalent of the manifest loader: the
    # request parser has replayed the content ID, and the exact transported
    # bytes have been checked against the loader-minted lease.  Mint a new
    # process-local authority; never deserialize one from the lease itself.
    return _mint_model_only_source_from_loader_sealed_transport_v1(
        lease=request.source_lease,
        model=model,
        query=query,
        portable_rapm_source_bytes=model_bytes,
        portable_query_source_bytes=query_bytes,
    )


@dataclass(frozen=True, slots=True)
class ModelOnlyNativeEventV1:
    sequence: int
    path: str
    amount: int

    def __post_init__(self) -> None:
        if type(self.sequence) is not int or self.sequence <= 0:
            raise Phase3EModelOnlyExecutorV1Error("event sequence must be positive")
        if self.path not in _TRACE_PATHS:
            raise Phase3EModelOnlyExecutorV1Error("event trace contains unknown path")
        if type(self.amount) is not int or self.amount <= 0:
            raise Phase3EModelOnlyExecutorV1Error("event amount must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {"sequence": self.sequence, "path": self.path, "amount": self.amount}


@dataclass(frozen=True, slots=True)
class ModelOnlyNativeEventTraceV1:
    events: tuple[ModelOnlyNativeEventV1, ...]

    def __post_init__(self) -> None:
        if not self.events:
            raise Phase3EModelOnlyExecutorV1Error("native event trace cannot be empty")
        if tuple(event.sequence for event in self.events) != tuple(
            range(1, len(self.events) + 1)
        ):
            raise Phase3EModelOnlyExecutorV1Error(
                "native event trace sequence must be contiguous"
            )

    @classmethod
    def from_events(
        cls, events: Iterable[tuple[str, int]]
    ) -> "ModelOnlyNativeEventTraceV1":
        return cls(
            tuple(
                ModelOnlyNativeEventV1(index, path, amount)
                for index, (path, amount) in enumerate(events, start=1)
            )
        )

    @property
    def totals(self) -> dict[str, int]:
        result = {path: 0 for path in _TRACE_PATHS}
        for event in self.events:
            result[event.path] += event.amount
        return result

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": EVENT_TRACE_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "events": [event.to_dict() for event in self.events],
        }

    @property
    def event_trace_id(self) -> str:
        return _artifact_id("model_only_native_event_trace", self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "event_trace_id": self.event_trace_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "ModelOnlyNativeEventTraceV1":
        require_exact_fields(
            document,
            {"schema", "schema_version", "events", "event_trace_id"},
            context="ModelOnlyNativeEventTraceV1",
        )
        if (
            document["schema"] != EVENT_TRACE_SCHEMA
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["events"]) is not list
        ):
            raise Phase3EModelOnlyExecutorV1Error("native event trace schema mismatch")
        rows: list[ModelOnlyNativeEventV1] = []
        for row in document["events"]:
            require_exact_fields(
                row, {"sequence", "path", "amount"}, context="native event"
            )
            rows.append(ModelOnlyNativeEventV1(row["sequence"], row["path"], row["amount"]))
        result = cls(tuple(rows))
        if document["event_trace_id"] != result.event_trace_id:
            raise Phase3EModelOnlyExecutorV1Error("native event trace ID mismatch")
        return result


def worker_output_document_v1(
    *,
    request: ModelOnlyExecutionRequestV1,
    result: Phase3EModelOnlyResultV1,
    event_trace: ModelOnlyNativeEventTraceV1,
    peak_working_bytes: int,
    forbidden_imports: tuple[str, ...],
) -> dict[str, Any]:
    if type(peak_working_bytes) is not int or peak_working_bytes <= 0:
        raise Phase3EModelOnlyExecutorV1Error("worker peak bytes must be positive")
    payload = {
        "schema": WORKER_OUTPUT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "request_id": request.request_id,
        "model_only_result": result.to_dict(),
        "native_event_trace": event_trace.to_dict(),
        "peak_working_bytes": peak_working_bytes,
        "forbidden_imports": list(forbidden_imports),
    }
    return {**payload, "worker_output_id": _artifact_id("model_only_worker_output", payload)}


def _parse_result_without_planner_v1(
    document: Mapping[str, Any], source: ModelOnlyRAPMSourceV1
) -> Phase3EModelOnlyResultV1:
    try:
        require_model_only_source_authority_v1(source)
    except ValueError as error:
        raise Phase3EModelOnlyExecutorV1Error(
            f"worker-result replay lacks live source authority: {error}"
        ) from error
    require_exact_fields(
        document,
        {
            "schema", "schema_version", "source_lease", "identities",
            "selected_plan", "sound_proof", "audit", "outcome",
            "ground_binding_required", "rebuild_policy", "logical_occurrence",
            "route_attempt", "route_context", "result_id",
        },
        context="worker model-only result",
    )
    lease = RAPMSourceLeaseV1.from_dict(document["source_lease"])
    if lease != source.lease:
        raise Phase3EModelOnlyExecutorV1Error("worker result/source lease mismatch")
    identities = ModelOnlyPhase3EIdentitiesV1.from_dict(document["identities"])
    selected = SelectedContingentPlanV1.from_dict(document["selected_plan"], source=source)
    proof = PortableSoundBellmanProofV1.from_dict(document["sound_proof"])
    audit = AbstractPlanAuditV1.from_dict(document["audit"])
    result = Phase3EModelOnlyResultV1(
        lease,
        identities,
        selected,
        proof,
        audit,
        ModelOnlyOutcome(document["outcome"]),
        document["ground_binding_required"],
        RebuildPolicyV1.from_dict(document["rebuild_policy"]),
        LogicalOccurrenceV1.from_dict(document["logical_occurrence"]),
        RouteAttemptV1.from_dict(document["route_attempt"]),
        RouteDecisionContextV1.from_dict(document["route_context"]),
    )
    expected_identities = derive_model_only_phase3e_identities_v1(source)
    expected_campaign = _campaign_bindings_v1(
        source=source,
        identities=expected_identities,
        selected_plan=selected,
        regret_tolerance=audit.regret_tolerance,
    )
    if identities != expected_identities or (
        result.rebuild_policy,
        result.logical_occurrence,
        result.route_attempt,
        result.route_context,
    ) != expected_campaign:
        raise Phase3EModelOnlyExecutorV1Error(
            "worker result differs from source/frozen-plan campaign derivation"
        )
    if document["result_id"] != result.result_id:
        raise Phase3EModelOnlyExecutorV1Error("worker model-only result ID mismatch")
    return result


def _parse_worker_output_v1(
    document: Mapping[str, Any],
    *,
    request: ModelOnlyExecutionRequestV1,
    source: ModelOnlyRAPMSourceV1,
) -> tuple[str, Phase3EModelOnlyResultV1, ModelOnlyNativeEventTraceV1, int]:
    require_exact_fields(
        document,
        {
            "schema", "schema_version", "request_id", "model_only_result",
            "native_event_trace", "peak_working_bytes", "forbidden_imports",
            "worker_output_id",
        },
        context="model-only worker output",
    )
    payload = dict(document)
    claimed = payload.pop("worker_output_id")
    if (
        document["schema"] != WORKER_OUTPUT_SCHEMA
        or document["schema_version"] != SCHEMA_VERSION
        or document["request_id"] != request.request_id
        or document["forbidden_imports"] != []
        or claimed != _artifact_id("model_only_worker_output", payload)
    ):
        raise Phase3EModelOnlyExecutorV1Error("worker output binding mismatch")
    peak = document["peak_working_bytes"]
    if type(peak) is not int or peak <= 0:
        raise Phase3EModelOnlyExecutorV1Error("worker peak bytes are invalid")
    trace = ModelOnlyNativeEventTraceV1.from_dict(document["native_event_trace"])
    result = _parse_result_without_planner_v1(document["model_only_result"], source)
    return claimed, result, trace, peak


def _recorded_work_from_dict_v1(document: Mapping[str, Any]) -> RecordedWorkV1:
    require_exact_fields(
        document,
        {
            "work_vector", "native_zero_attestation", "reconciliation_proof",
            "comparison_vector", "actual_projection_proof",
        },
        context="model-only recorded work",
    )
    registry = official_counter_registry_v1()
    work = RecordedWorkV1(
        WorkVectorV1.from_dict(document["work_vector"], registry),
        NativeZeroAttestationV1.from_dict(document["native_zero_attestation"]),
        ReconciliationProofV1.from_dict(document["reconciliation_proof"]),
        ComparisonVectorV1.from_dict(document["comparison_vector"]),
        ActualProjectionProofV1.from_dict(document["actual_projection_proof"]),
    )
    return verify_recorded_work_v1(
        work,
        expected_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=official_comparison_profile_v1(registry),
    )


def _recorded_work_to_dict_v1(work: RecordedWorkV1) -> dict[str, Any]:
    return {
        "work_vector": work.work_vector.to_dict(),
        "native_zero_attestation": work.native_zero_attestation.to_dict(),
        "reconciliation_proof": work.reconciliation_proof.to_dict(),
        "comparison_vector": work.comparison_vector.to_dict(),
        "actual_projection_proof": work.actual_projection_proof.to_dict(),
    }


@dataclass(frozen=True, slots=True)
class ModelOnlyQueryExecutionArtifactV1:
    """Serializable PASS/FAIL projection; transport is never live authority."""

    request_id: str
    worker_output_id: str
    model_only_result: Phase3EModelOnlyResultV1
    native_event_trace: ModelOnlyNativeEventTraceV1
    recorded_work: RecordedWorkV1
    isolation_profile_id: str = ISOLATION_PROFILE_ID
    counter_coverage_status: str = COUNTER_COVERAGE_STATUS
    counter_coverage_blockers: tuple[str, ...] = COUNTER_COVERAGE_BLOCKERS
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    workload_economics_gate: str = WORKLOAD_ECONOMICS_GATE_NOT_RUN
    counter_completeness_gate: str = COUNTER_COMPLETENESS_GATE_NOT_RUN

    def __post_init__(self) -> None:
        parse_content_id(self.request_id)
        parse_content_id(self.worker_output_id)
        expected_route_kind = (
            RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
            if self.model_only_result.outcome is ModelOnlyOutcome.PASS
            else RouteKindEnum.ABSTRACT_FAILED_PREFIX
        )
        if (
            self.recorded_work.work_vector.subject_id
            != self.model_only_result.route_attempt.route_attempt_id
            or self.recorded_work.work_vector.route_kind
            is not expected_route_kind
        ):
            raise Phase3EModelOnlyExecutorV1Error("recorded work/result binding mismatch")
        if (
            self.isolation_profile_id != ISOLATION_PROFILE_ID
            or self.counter_coverage_status != COUNTER_COVERAGE_STATUS
            or self.counter_coverage_blockers != COUNTER_COVERAGE_BLOCKERS
            or self.official_execution_allowed is not False
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.workload_economics_gate != WORKLOAD_ECONOMICS_GATE_NOT_RUN
            or self.counter_completeness_gate != COUNTER_COMPLETENESS_GATE_NOT_RUN
        ):
            raise Phase3EModelOnlyExecutorV1Error("non-official lock fields changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": EXECUTION_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "request_id": self.request_id,
            "worker_output_id": self.worker_output_id,
            "model_only_result": self.model_only_result.to_dict(),
            "native_event_trace": self.native_event_trace.to_dict(),
            "recorded_work": _recorded_work_to_dict_v1(self.recorded_work),
            "isolation_profile_id": self.isolation_profile_id,
            "counter_coverage_status": self.counter_coverage_status,
            "counter_coverage_blockers": list(self.counter_coverage_blockers),
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "workload_economics_gate": WORKLOAD_ECONOMICS_GATE_NOT_RUN,
            "counter_completeness_gate": COUNTER_COMPLETENESS_GATE_NOT_RUN,
        }

    @property
    def operational_execution_id(self) -> str:
        return _artifact_id("model_only_operational_execution", self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "operational_execution_id": self.operational_execution_id}

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any], *, source: ModelOnlyRAPMSourceV1
    ) -> "ModelOnlyQueryExecutionArtifactV1":
        try:
            require_model_only_source_authority_v1(source)
        except ValueError as error:
            raise Phase3EModelOnlyExecutorV1Error(
                f"execution replay lacks live source authority: {error}"
            ) from error
        expected = {
            "schema", "schema_version", "request_id", "worker_output_id",
            "model_only_result", "native_event_trace", "recorded_work",
            "isolation_profile_id", "counter_coverage_status",
            "counter_coverage_blockers", "official_execution_allowed",
            "official_scalar_cost", "official_N_break_even",
            "workload_economics_gate", "counter_completeness_gate",
            "operational_execution_id",
        }
        require_exact_fields(
            document, expected, context="ModelOnlyQueryExecutionArtifactV1"
        )
        if (
            document["schema"] != EXECUTION_SCHEMA
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["counter_coverage_blockers"]) is not list
        ):
            raise Phase3EModelOnlyExecutorV1Error("operational execution schema mismatch")
        result = cls(
            document["request_id"],
            document["worker_output_id"],
            _parse_result_without_planner_v1(document["model_only_result"], source),
            ModelOnlyNativeEventTraceV1.from_dict(document["native_event_trace"]),
            _recorded_work_from_dict_v1(document["recorded_work"]),
            document["isolation_profile_id"],
            document["counter_coverage_status"],
            tuple(document["counter_coverage_blockers"]),
            document["official_execution_allowed"],
            document["official_scalar_cost"],
            document["official_N_break_even"],
            document["workload_economics_gate"],
            document["counter_completeness_gate"],
        )
        if document["operational_execution_id"] != result.operational_execution_id:
            raise Phase3EModelOnlyExecutorV1Error("operational execution ID mismatch")
        return result


_MODEL_ONLY_QUERY_EXECUTION_AUTHORITY = object()
_LIVE_QUERY_EXECUTIONS: dict[
    int, tuple[weakref.ReferenceType["ModelOnlyQueryExecutionV1"], object]
] = {}


class ModelOnlyQueryExecutionV1:
    """Opaque runtime authority over one fresh-process PASS or FAIL execution."""

    __slots__ = ("_artifact", "_authority", "_instance_token", "__weakref__")

    def __init__(
        self,
        artifact: ModelOnlyQueryExecutionArtifactV1,
        authority: object,
    ) -> None:
        if authority is not _MODEL_ONLY_QUERY_EXECUTION_AUTHORITY:
            raise Phase3EModelOnlyExecutorV1Error(
                "model-only query execution was not minted by the fresh executor"
            )
        token = object()
        object.__setattr__(self, "_artifact", artifact)
        object.__setattr__(self, "_authority", authority)
        object.__setattr__(self, "_instance_token", token)
        identity = id(self)

        def discard(reference: weakref.ReferenceType[ModelOnlyQueryExecutionV1]) -> None:
            current = _LIVE_QUERY_EXECUTIONS.get(identity)
            if current is not None and current[0] is reference:
                _LIVE_QUERY_EXECUTIONS.pop(identity, None)

        reference = weakref.ref(self, discard)
        _LIVE_QUERY_EXECUTIONS[identity] = (reference, token)

    def __setattr__(self, _name: str, _value: object) -> None:
        raise AttributeError("ModelOnlyQueryExecutionV1 is immutable")

    @property
    def artifact(self) -> ModelOnlyQueryExecutionArtifactV1:
        return self._artifact

    @property
    def request_id(self) -> str:
        return self._artifact.request_id

    @property
    def worker_output_id(self) -> str:
        return self._artifact.worker_output_id

    @property
    def model_only_result(self) -> Phase3EModelOnlyResultV1:
        return self._artifact.model_only_result

    @property
    def native_event_trace(self) -> ModelOnlyNativeEventTraceV1:
        return self._artifact.native_event_trace

    @property
    def recorded_work(self) -> RecordedWorkV1:
        return self._artifact.recorded_work

    @property
    def isolation_profile_id(self) -> str:
        return self._artifact.isolation_profile_id

    @property
    def counter_coverage_status(self) -> str:
        return self._artifact.counter_coverage_status

    @property
    def counter_coverage_blockers(self) -> tuple[str, ...]:
        return self._artifact.counter_coverage_blockers

    @property
    def official_execution_allowed(self) -> bool:
        return self._artifact.official_execution_allowed

    @property
    def official_scalar_cost(self) -> None:
        return self._artifact.official_scalar_cost

    @property
    def official_N_break_even(self) -> None:
        return self._artifact.official_N_break_even

    @property
    def operational_execution_id(self) -> str:
        return self._artifact.operational_execution_id

    def to_dict(self) -> dict[str, Any]:
        """Return transport bytes; round-tripping them does not mint authority."""

        return self._artifact.to_dict()


def require_model_only_query_execution_authority_v1(
    execution: object,
) -> ModelOnlyQueryExecutionV1:
    """Require an exact executor-minted live query execution."""

    if type(execution) is not ModelOnlyQueryExecutionV1:
        raise Phase3EModelOnlyExecutorV1Error(
            "a retained executor-minted ModelOnlyQueryExecutionV1 authority is required"
        )
    live = _LIVE_QUERY_EXECUTIONS.get(id(execution))
    if (
        live is None
        or live[0]() is not execution
        or live[1] is not execution._instance_token
        or execution._authority is not _MODEL_ONLY_QUERY_EXECUTION_AUTHORITY
    ):
        raise Phase3EModelOnlyExecutorV1Error(
            "a retained executor-minted ModelOnlyQueryExecutionV1 authority is required"
        )
    # Replay all transport-level frozen-dataclass invariants without acquiring
    # source or invoking a planner.  A forged wrapper cannot change its member.
    execution.artifact.__post_init__()
    return execution


def _verify_model_only_query_execution_artifact_members_v1(
    artifact: ModelOnlyQueryExecutionArtifactV1,
) -> ModelOnlyQueryExecutionArtifactV1:
    """Replay artifact members without minting process-local authority."""

    if type(artifact) is not ModelOnlyQueryExecutionArtifactV1:
        raise Phase3EModelOnlyExecutorV1Error(
            "model-only query replay requires the exact transport artifact type"
        )
    artifact.__post_init__()
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    actual_profile = official_actual_projection_profile_v1(registry, comparison)
    try:
        work = verify_recorded_work_v1(
            artifact.recorded_work,
            expected_scope=ActualWorkScope.COMMON_PREFIX,
            registry=registry,
            comparison_profile=comparison,
        )
    except ValueError as error:
        raise Phase3EModelOnlyExecutorV1Error(
            f"model-only query work does not replay: {error}"
        ) from error
    result = artifact.model_only_result
    expected_kind = (
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
        if result.outcome is ModelOnlyOutcome.PASS
        else RouteKindEnum.ABSTRACT_FAILED_PREFIX
    )
    if (
        work.work_vector.route_kind is not expected_kind
        or work.work_vector.subject_id != result.route_attempt.route_attempt_id
        or work.work_vector.counter_registry_id != result.route_context.counter_registry_id
        or work.comparison_vector.comparison_profile_id
        != result.route_context.comparison_profile_id
        or work.actual_projection_proof.actual_projection_profile_id
        != actual_profile.actual_projection_profile_id
        or any(
            record.recorder_id != MODEL_ONLY_NATIVE_RECORDER_ID
            for record in work.work_vector.records
        )
    ):
        raise Phase3EModelOnlyExecutorV1Error(
            "model-only query work belongs to another outcome, context, or recorder"
        )
    missing = tuple(
        path
        for path in _REQUIRED_POSITIVE_MODEL_ONLY_COUNTERS
        if work.work_vector.value(path) <= 0
    )
    if missing:
        raise Phase3EModelOnlyExecutorV1Error(
            "model-only query work omits observed operations: " + ", ".join(missing)
        )
    trace_values = dict(artifact.native_event_trace.totals)
    if any(
        work.work_vector.value(path) < amount
        for path, amount in trace_values.items()
    ):
        raise Phase3EModelOnlyExecutorV1Error(
            "model-only recorded work is smaller than the retained worker trace"
        )
    return artifact


def verify_model_only_query_execution_artifact_v1(
    artifact: ModelOnlyQueryExecutionArtifactV1 | Mapping[str, Any],
    *,
    request: ModelOnlyExecutionRequestV1 | Mapping[str, Any],
    source: ModelOnlyRAPMSourceV1 | None = None,
) -> ModelOnlyQueryExecutionArtifactV1:
    """Purely replay one transported model-only execution artifact.

    The request carries the exact RAPM/query bytes required for no-replanning
    Bellman-proof replay.  When ``source`` is supplied it must be a live source
    minted by the complete Phase-3C bundle loader and its retained bytes must
    match the request byte-for-byte.  Without ``source`` this function proves
    only transport self-consistency; a bundle verifier must supply the parent
    authority before making a source-provenance claim.  This function never
    mints :class:`ModelOnlyQueryExecutionV1` authority and never calls the
    portable planner or any ground/local solver.
    """

    try:
        parsed_request = (
            request
            if type(request) is ModelOnlyExecutionRequestV1
            else parse_model_only_execution_request_v1(request)
        )
        if type(parsed_request) is not ModelOnlyExecutionRequestV1:
            raise Phase3EModelOnlyExecutorV1Error(
                "model-only request has the wrong runtime type"
            )
        if source is None:
            replay_source = reconstruct_model_only_source_from_request_v1(
                parsed_request
            )
        else:
            require_model_only_source_authority_v1(source)
            request_model_bytes = base64.b64decode(
                parsed_request.portable_rapm_base64, validate=True
            )
            request_query_bytes = base64.b64decode(
                parsed_request.portable_query_base64, validate=True
            )
            if (
                source.lease != parsed_request.source_lease
                or source.portable_rapm_source_bytes != request_model_bytes
                or source.portable_query_source_bytes != request_query_bytes
            ):
                raise Phase3EModelOnlyExecutorV1Error(
                    "verified Phase3C parent source differs from the execution request"
                )
            replay_source = source
        document = (
            artifact.to_dict()
            if type(artifact) is ModelOnlyQueryExecutionArtifactV1
            else artifact
        )
        parsed = ModelOnlyQueryExecutionArtifactV1.from_dict(
            document, source=replay_source
        )
    except (TypeError, ValueError) as error:
        if isinstance(error, Phase3EModelOnlyExecutorV1Error):
            raise
        raise Phase3EModelOnlyExecutorV1Error(
            f"model-only execution artifact replay failed: {error}"
        ) from error
    if parsed.request_id != parsed_request.request_id or (
        parsed.model_only_result.source_lease != parsed_request.source_lease
    ):
        raise Phase3EModelOnlyExecutorV1Error(
            "model-only execution artifact belongs to another request/source lease"
        )
    verified = _verify_model_only_query_execution_artifact_members_v1(parsed)
    replayed_worker_output = worker_output_document_v1(
        request=parsed_request,
        result=verified.model_only_result,
        event_trace=verified.native_event_trace,
        peak_working_bytes=verified.recorded_work.work_vector.value(
            "memory.working_bytes_peak"
        ),
        forbidden_imports=(),
    )
    if replayed_worker_output["worker_output_id"] != verified.worker_output_id:
        raise Phase3EModelOnlyExecutorV1Error(
            "model-only execution artifact does not bind a replayable worker output"
        )
    return verified


def verify_model_only_failed_prefix_artifact_v1(
    artifact: ModelOnlyQueryExecutionArtifactV1 | Mapping[str, Any],
    *,
    request: ModelOnlyExecutionRequestV1 | Mapping[str, Any],
    source: ModelOnlyRAPMSourceV1 | None = None,
) -> ModelOnlyQueryExecutionArtifactV1:
    """Purely replay an H2 ``ABSTRACT_FAILED_PREFIX`` transport artifact."""

    parsed = verify_model_only_query_execution_artifact_v1(
        artifact, request=request, source=source
    )
    if (
        parsed.model_only_result.outcome is not ModelOnlyOutcome.FAIL
        or not parsed.model_only_result.ground_binding_required
        or parsed.recorded_work.work_vector.route_kind
        is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
    ):
        raise Phase3EModelOnlyExecutorV1Error(
            "failed-prefix artifact replay requires ABSTRACT_FAILED_PREFIX"
        )
    return parsed


def verify_model_only_query_execution_v1(
    execution: object,
) -> ModelOnlyQueryExecutionV1:
    """Replay the complete retained execution/work/profile binding.

    This is an authority verifier, not a transport parser.  It returns the
    exact live object, whose ``request_id``, ``model_only_result``,
    ``recorded_work`` and ``native_event_trace`` properties are the frozen
    request/result/work/trace binding consumed by later stages.
    """

    retained = require_model_only_query_execution_authority_v1(execution)
    _verify_model_only_query_execution_artifact_members_v1(retained.artifact)
    return retained


def verify_model_only_failed_prefix_execution_v1(
    execution: object,
) -> ModelOnlyQueryExecutionV1:
    """Require one exact H2-style failed audit and its COMMON_PREFIX work."""

    retained = verify_model_only_query_execution_v1(execution)
    if (
        retained.model_only_result.outcome is not ModelOnlyOutcome.FAIL
        or not retained.model_only_result.ground_binding_required
        or retained.recorded_work.work_vector.route_kind
        is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
    ):
        raise Phase3EModelOnlyExecutorV1Error(
            "failed-prefix consumer requires an ABSTRACT_FAILED_PREFIX authority"
        )
    return retained


def _mint_model_only_query_execution_v1(
    artifact: ModelOnlyQueryExecutionArtifactV1,
) -> ModelOnlyQueryExecutionV1:
    return ModelOnlyQueryExecutionV1(
        artifact, _MODEL_ONLY_QUERY_EXECUTION_AUTHORITY
    )


def execute_model_only_query_v1(
    source: ModelOnlyRAPMSourceV1,
    *,
    regret_tolerance: Fraction | int = Fraction(1, 20),
    timeout_seconds: int = 120,
    runtime_source_root: str | Path | None = None,
) -> ModelOnlyQueryExecutionV1:
    """Run one query once and retain an honestly typed PASS/FAIL execution."""

    try:
        require_model_only_source_authority_v1(source)
    except ValueError as error:
        raise Phase3EModelOnlyExecutorV1Error(
            f"execution requires live source authority: {error}"
        ) from error
    if type(timeout_seconds) is not int or timeout_seconds <= 0:
        raise Phase3EModelOnlyExecutorV1Error("timeout_seconds must be positive")
    request = model_only_execution_request_v1(
        source, regret_tolerance=regret_tolerance
    )
    request_raw = canonical_json_bytes(request.to_dict())
    runtime_root = (
        Path(runtime_source_root).resolve()
        if runtime_source_root is not None
        else Path(__file__).resolve().parents[1]
    )
    entrypoint = runtime_root / RUNTIME_ENTRYPOINT
    if not entrypoint.is_file():
        raise Phase3EModelOnlyExecutorV1Error("model-only runtime entrypoint missing")

    with tempfile.TemporaryDirectory(prefix="acfqp-model-only-") as temporary:
        root = Path(temporary)
        request_path = root / "request.json"
        output_path = root / "output.json"
        request_path.write_bytes(request_raw)
        try:
            process = subprocess.run(
                (
                    sys.executable,
                    "-I",
                    "-B",
                    str(entrypoint),
                    "--runtime-source",
                    str(runtime_root),
                    "--request",
                    str(request_path),
                    "--output",
                    str(output_path),
                ),
                cwd=root,
                env={
                    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                    "LANG": "C.UTF-8",
                    "PYTHONHASHSEED": "0",
                },
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except Exception as error:
            evidence = ModelOnlyProcessFailureEvidenceV1(
                request.request_id,
                None,
                len(request_raw),
                output_path.stat().st_size if output_path.exists() else 0,
                "",
                repr(error),
                "PROCESS_LAUNCH_OR_TIMEOUT",
            )
            raise ModelOnlyProcessFailedV1(evidence) from error
        output_raw = output_path.read_bytes() if output_path.exists() else b""
        if process.returncode != 0 or process.stdout or process.stderr or not output_raw:
            raise ModelOnlyProcessFailedV1(
                ModelOnlyProcessFailureEvidenceV1(
                    request.request_id,
                    process.returncode,
                    len(request_raw),
                    len(output_raw),
                    process.stdout,
                    process.stderr,
                    "NONZERO_OR_NOISY_OR_MISSING_OUTPUT",
                )
            )
        try:
            output_document = _plain_canonical_document(output_raw)
            output_id, result, trace, peak = _parse_worker_output_v1(
                output_document, request=request, source=source
            )
        except Exception as error:
            raise ModelOnlyProcessFailedV1(
                ModelOnlyProcessFailureEvidenceV1(
                    request.request_id,
                    process.returncode,
                    len(request_raw),
                    len(output_raw),
                    process.stdout,
                    f"invalid worker output: {error}",
                    "INVALID_OUTPUT",
                )
            ) from error

    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    route_kind = (
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
        if result.outcome is ModelOnlyOutcome.PASS
        else RouteKindEnum.ABSTRACT_FAILED_PREFIX
    )
    recorder = NativeCounterRecorderV1(
        subject_id=result.route_attempt.route_attempt_id,
        route_kind=route_kind,
        work_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=comparison,
        recorder_id=MODEL_ONLY_NATIVE_RECORDER_ID,
    )
    for path, amount in trace.totals.items():
        if amount:
            recorder.add(path, amount)
    # Exact supervisor operations, charged after the fresh-process trace.
    recorder.add("common.integrity_checks", 6)
    recorder.add("common.protocol_checks", 5)
    recorder.add("common.hash_invocations", 2)
    recorder.add("io.read_bytes", len(request_raw) + len(output_raw))
    recorder.add("io.staged_bytes", len(request_raw))
    recorder.add("io.output_bytes", len(output_raw))
    recorder.observe_peak("memory.working_bytes_peak", peak)
    recorder.record_process_completion(success=True)
    recorder.record_solver_completion(success=True)
    recorder.record_route_completion(success=True)
    work = recorder.seal()
    verify_recorded_work_v1(
        work,
        expected_scope=ActualWorkScope.COMMON_PREFIX,
        registry=registry,
        comparison_profile=comparison,
    )
    return _mint_model_only_query_execution_v1(
        ModelOnlyQueryExecutionArtifactV1(
            request.request_id,
            output_id,
            result,
            trace,
            work,
        )
    )


def execute_model_only_abstract_pass_v1(
    source: ModelOnlyRAPMSourceV1,
    *,
    regret_tolerance: Fraction | int = Fraction(1, 20),
    timeout_seconds: int = 120,
    runtime_source_root: str | Path | None = None,
) -> ModelOnlyQueryExecutionV1:
    """Compatibility PASS-only wrapper over :func:`execute_model_only_query_v1`.

    FAIL remains available on ``error.execution`` with its complete
    ``ABSTRACT_FAILED_PREFIX`` work; it is never returned as a PASS authority.
    """

    execution = execute_model_only_query_v1(
        source,
        regret_tolerance=regret_tolerance,
        timeout_seconds=timeout_seconds,
        runtime_source_root=runtime_source_root,
    )
    if execution.model_only_result.outcome is not ModelOnlyOutcome.PASS:
        raise ModelOnlyNoncertificateOutcomeV1(
            request_id=execution.request_id,
            worker_output_id=execution.worker_output_id,
            result=execution.model_only_result,
            event_trace=execution.native_event_trace,
            execution=execution,
        )
    return execution


__all__ = [
    "COUNTER_COVERAGE_BLOCKERS",
    "COUNTER_COVERAGE_STATUS",
    "EXECUTION_SCHEMA",
    "ISOLATION_PROFILE_ID",
    "ModelOnlyExecutionRequestV1",
    "ModelOnlyNativeEventTraceV1",
    "ModelOnlyNoncertificateOutcomeV1",
    "ModelOnlyQueryExecutionArtifactV1",
    "ModelOnlyQueryExecutionV1",
    "ModelOnlyProcessFailedV1",
    "ModelOnlyProcessFailureEvidenceV1",
    "Phase3EModelOnlyExecutorV1Error",
    "execute_model_only_abstract_pass_v1",
    "execute_model_only_query_v1",
    "model_only_execution_request_v1",
    "parse_model_only_execution_request_v1",
    "reconstruct_model_only_source_from_request_v1",
    "require_model_only_query_execution_authority_v1",
    "verify_model_only_failed_prefix_artifact_v1",
    "verify_model_only_failed_prefix_execution_v1",
    "verify_model_only_query_execution_artifact_v1",
    "verify_model_only_query_execution_v1",
    "worker_output_document_v1",
]
