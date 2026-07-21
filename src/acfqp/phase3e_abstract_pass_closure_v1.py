"""Strict, non-official closure of a model-only abstract PASS.

This module connects the model-only RAPM audit to the existing semantic
terminal and campaign machinery.  It deliberately does *not* run a planner,
load a ground model, bind a ground namespace, or execute a route.

The mathematical plan certificate can be closed only when the caller retains
both the authority-bearing ``ABSTRACT_AUDIT=PASS`` result and the fresh
executor's opaque ``ModelOnlyQueryExecutionV1``.  Bare ``RecordedWorkV1`` and
serialized execution artifacts are never accepted as authority.  The sealed
work is replayed through the official registry and projection profile; zeros
are accepted only as explicit observed native records.  This slice does not
claim that every model-only operation is already wired to that recorder, so
all official execution/economics gates remain locked.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Mapping

from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    CounterRecordV1,
    CounterRegistryV1,
    LaneEnum,
    RouteKindEnum,
    SHARED_AXES,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProfileV1,
    ActualWorkScope,
    official_actual_projection_profile_v1,
)
from acfqp.campaign_v1 import (
    COUNTER_COMPLETENESS_GATE_NOT_RUN,
    WORKLOAD_ECONOMICS_GATE_NOT_RUN,
    CampaignOccurrenceClosureV1,
    CampaignV1Error,
    require_campaign_occurrence_closure_authority_v1,
)
from acfqp.native_recorder_v1 import RecordedWorkV1, verify_recorded_work_v1
from acfqp.phase3e_ids import (
    ABSTRACT_ONLY_OCCURRENCE_WORK_SUM_DOMAIN,
    MODEL_ONLY_OPERATIONAL_EXECUTION_DOMAIN,
    MODEL_ONLY_OPERATIONAL_REQUEST_DOMAIN,
    Phase3EIdentityError,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.phase3e_model_only_v1 import (
    ModelOnlyOutcome,
    Phase3EModelOnlyResultV1,
)
from acfqp.phase3e_model_only_executor_v1 import (
    ModelOnlyQueryExecutionV1,
    Phase3EModelOnlyExecutorV1Error,
    verify_model_only_query_execution_v1,
)
from acfqp.phase3e_rapm_consumer_v1 import RAPMSourceLeaseV1
from acfqp.routing_v1 import (
    TerminalArtifactV1,
    TerminalClass,
    TerminalCode,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    AttestationContextV1,
    SemanticRole,
    SemanticVerificationResultV1,
    SemanticVerificationV1Error,
    require_semantic_verification_result_v1,
    require_terminal_classification_result_v1,
    verify_terminal_classification_semantics_v1,
    verify_typed_attestation_v1,
    verify_work_vector_semantics_v1,
)


SCHEMA_VERSION = "1.0.0"
ABSTRACT_ONLY_OCCURRENCE_WORK_SUM_SCHEMA = (
    "acfqp.abstract_only_occurrence_work_sum.v1"
)
MODEL_ONLY_NATIVE_RECORDER_ID = "phase3e-model-only-native-recorder-v1"
MODEL_ONLY_PASS_ACCOUNTING_STATUS = (
    "PROVISIONAL_NATIVE_REPLAY_COUNTER_COMPLETENESS_GATE_NOT_RUN"
)
MODEL_ONLY_PASS_EXECUTION_SCOPE = "MODEL_ONLY_PASS_CLOSURE"

_REQUIRED_POSITIVE_MODEL_ONLY_COUNTERS = (
    "common.abstract_bellman_backups",
    "common.abstract_audit_obligations",
    "common.integrity_checks",
    "common.protocol_checks",
    "common.hash_invocations",
    "io.read_bytes",
)


class Phase3EAbstractPassClosureV1Error(ValueError):
    """A model-only PASS, authority, accounting, or campaign binding failed."""


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise Phase3EAbstractPassClosureV1Error(
            f"{field} must be a full Phase-3E content ID"
        ) from error


def _axis_values(value: Any) -> tuple[tuple[str, int], ...]:
    rows = tuple(value)
    if tuple(axis for axis, _ in rows) != SHARED_AXES:
        raise Phase3EAbstractPassClosureV1Error(
            "abstract-only occurrence sum must contain exact shared axes"
        )
    for axis, amount in rows:
        if type(axis) is not str or type(amount) is not int or amount < 0:
            raise Phase3EAbstractPassClosureV1Error(
                "abstract-only occurrence values must be nonnegative integers"
            )
    return rows


@dataclass(frozen=True, slots=True)
class ModelOnlyOperationalRequestV1:
    """Pre-execution identity for the narrowly scoped PASS closure run."""

    source_lease_id: str
    query_key: str
    legacy_portable_rapm_id: str
    legacy_portable_query_id: str
    kernel_sha256: str
    regret_tolerance: Fraction
    execution_scope: str = MODEL_ONLY_PASS_EXECUTION_SCOPE
    official_execution_allowed: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _cid(self.source_lease_id, "source_lease_id")
        _cid(self.kernel_sha256, "kernel_sha256")
        for field in (
            "query_key",
            "legacy_portable_rapm_id",
            "legacy_portable_query_id",
        ):
            if type(getattr(self, field)) is not str or not getattr(self, field):
                raise Phase3EAbstractPassClosureV1Error(
                    f"{field} must be a nonempty string"
                )
        object.__setattr__(self, "regret_tolerance", Fraction(self.regret_tolerance))
        if self.regret_tolerance < 0:
            raise Phase3EAbstractPassClosureV1Error(
                "model-only request regret tolerance must be nonnegative"
            )
        if (
            self.execution_scope != MODEL_ONLY_PASS_EXECUTION_SCOPE
            or self.official_execution_allowed is not False
            or self.schema_version != SCHEMA_VERSION
        ):
            raise Phase3EAbstractPassClosureV1Error(
                "model-only operational request exceeded PASS-only scope"
            )

    @classmethod
    def from_source_lease(
        cls,
        lease: RAPMSourceLeaseV1,
        *,
        regret_tolerance: Fraction | int,
    ) -> "ModelOnlyOperationalRequestV1":
        if type(lease) is not RAPMSourceLeaseV1:
            raise Phase3EAbstractPassClosureV1Error(
                "model-only request requires a retained RAPM source lease"
            )
        parsed = RAPMSourceLeaseV1.from_dict(lease.to_dict())
        return cls(
            parsed.source_lease_id,
            parsed.query_key,
            parsed.legacy_portable_rapm_id,
            parsed.legacy_portable_query_id,
            parsed.kernel_sha256,
            Fraction(regret_tolerance),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.model_only_operational_request.v1",
            "schema_version": self.schema_version,
            "source_lease_id": self.source_lease_id,
            "query_key": self.query_key,
            "legacy_portable_rapm_id": self.legacy_portable_rapm_id,
            "legacy_portable_query_id": self.legacy_portable_query_id,
            "kernel_sha256": self.kernel_sha256,
            "regret_tolerance": self.regret_tolerance,
            "execution_scope": self.execution_scope,
            "official_execution_allowed": False,
        }

    @property
    def model_only_operational_request_id(self) -> str:
        return content_id(MODEL_ONLY_OPERATIONAL_REQUEST_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "model_only_operational_request_id": (
                self.model_only_operational_request_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "ModelOnlyOperationalRequestV1":
        expected = {
            "schema",
            "schema_version",
            "source_lease_id",
            "query_key",
            "legacy_portable_rapm_id",
            "legacy_portable_query_id",
            "kernel_sha256",
            "regret_tolerance",
            "execution_scope",
            "official_execution_allowed",
            "model_only_operational_request_id",
        }
        try:
            require_exact_fields(
                document, expected, context="ModelOnlyOperationalRequestV1"
            )
        except (Phase3EIdentityError, TypeError) as error:
            raise Phase3EAbstractPassClosureV1Error(str(error)) from error
        if document["schema"] != "acfqp.model_only_operational_request.v1":
            raise Phase3EAbstractPassClosureV1Error(
                "model-only operational request schema mismatch"
            )
        result = cls(
            document["source_lease_id"],
            document["query_key"],
            document["legacy_portable_rapm_id"],
            document["legacy_portable_query_id"],
            document["kernel_sha256"],
            document["regret_tolerance"],
            document["execution_scope"],
            document["official_execution_allowed"],
            document["schema_version"],
        )
        if document["model_only_operational_request_id"] != (
            result.model_only_operational_request_id
        ):
            raise Phase3EAbstractPassClosureV1Error(
                "model-only operational request ID mismatch"
            )
        return result


@dataclass(frozen=True, slots=True)
class ModelOnlyOperationalExecutionArtifactV1:
    """Serializable projection of the opaque PASS execution authority."""

    request_id: str
    source_lease_id: str
    model_only_result_id: str
    selected_plan_id: str
    route_decision_context_id: str
    route_attempt_id: str
    work_vector_id: str
    comparison_vector_id: str
    actual_projection_proof_id: str
    native_zero_attestation_id: str
    reconciliation_proof_id: str
    execution_scope: str = MODEL_ONLY_PASS_EXECUTION_SCOPE
    official_execution_allowed: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in (
            "request_id",
            "source_lease_id",
            "model_only_result_id",
            "selected_plan_id",
            "route_decision_context_id",
            "route_attempt_id",
            "work_vector_id",
            "comparison_vector_id",
            "actual_projection_proof_id",
            "native_zero_attestation_id",
            "reconciliation_proof_id",
        ):
            _cid(getattr(self, field), field)
        if (
            self.execution_scope != MODEL_ONLY_PASS_EXECUTION_SCOPE
            or self.official_execution_allowed is not False
            or self.schema_version != SCHEMA_VERSION
        ):
            raise Phase3EAbstractPassClosureV1Error(
                "model-only execution artifact exceeded PASS-only scope"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.model_only_operational_execution.v1",
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "source_lease_id": self.source_lease_id,
            "model_only_result_id": self.model_only_result_id,
            "selected_plan_id": self.selected_plan_id,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "route_attempt_id": self.route_attempt_id,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "actual_projection_proof_id": self.actual_projection_proof_id,
            "native_zero_attestation_id": self.native_zero_attestation_id,
            "reconciliation_proof_id": self.reconciliation_proof_id,
            "execution_scope": self.execution_scope,
            "official_execution_allowed": False,
        }

    @property
    def model_only_operational_execution_id(self) -> str:
        return content_id(MODEL_ONLY_OPERATIONAL_EXECUTION_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "model_only_operational_execution_id": (
                self.model_only_operational_execution_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "ModelOnlyOperationalExecutionArtifactV1":
        expected = {
            "schema",
            "schema_version",
            "request_id",
            "source_lease_id",
            "model_only_result_id",
            "selected_plan_id",
            "RouteDecisionContext_id",
            "route_attempt_id",
            "work_vector_id",
            "comparison_vector_id",
            "actual_projection_proof_id",
            "native_zero_attestation_id",
            "reconciliation_proof_id",
            "execution_scope",
            "official_execution_allowed",
            "model_only_operational_execution_id",
        }
        try:
            require_exact_fields(
                document,
                expected,
                context="ModelOnlyOperationalExecutionArtifactV1",
            )
        except (Phase3EIdentityError, TypeError) as error:
            raise Phase3EAbstractPassClosureV1Error(str(error)) from error
        if document["schema"] != "acfqp.model_only_operational_execution.v1":
            raise Phase3EAbstractPassClosureV1Error(
                "model-only operational execution schema mismatch"
            )
        result = cls(
            document["request_id"],
            document["source_lease_id"],
            document["model_only_result_id"],
            document["selected_plan_id"],
            document["RouteDecisionContext_id"],
            document["route_attempt_id"],
            document["work_vector_id"],
            document["comparison_vector_id"],
            document["actual_projection_proof_id"],
            document["native_zero_attestation_id"],
            document["reconciliation_proof_id"],
            document["execution_scope"],
            document["official_execution_allowed"],
            document["schema_version"],
        )
        if document["model_only_operational_execution_id"] != (
            result.model_only_operational_execution_id
        ):
            raise Phase3EAbstractPassClosureV1Error(
                "model-only operational execution ID mismatch"
            )
        return result


_MODEL_ONLY_OPERATIONAL_EXECUTION_AUTHORITY = object()


class _LegacyBareWorkPassAuthorityV1:
    """Removed construction seam retained only to reject legacy fabrication."""

    __slots__ = ("_request", "_result", "_recorded_work", "_artifact", "_authority")

    def __init__(
        self,
        request: ModelOnlyOperationalRequestV1,
        result: Phase3EModelOnlyResultV1,
        recorded_work: RecordedWorkV1,
        artifact: ModelOnlyOperationalExecutionArtifactV1,
        authority: object,
    ) -> None:
        if authority is not _MODEL_ONLY_OPERATIONAL_EXECUTION_AUTHORITY:
            raise Phase3EAbstractPassClosureV1Error(
                "model-only execution was not minted by the trusted PASS factory"
            )
        object.__setattr__(self, "_request", request)
        object.__setattr__(self, "_result", result)
        object.__setattr__(self, "_recorded_work", recorded_work)
        object.__setattr__(self, "_artifact", artifact)
        object.__setattr__(self, "_authority", authority)

    def __setattr__(self, _name: str, _value: object) -> None:
        raise AttributeError("legacy bare-work PASS authority is immutable")

    @property
    def request(self) -> ModelOnlyOperationalRequestV1:
        return self._request

    @property
    def result(self) -> Phase3EModelOnlyResultV1:
        return self._result

    @property
    def recorded_work(self) -> RecordedWorkV1:
        return self._recorded_work

    @property
    def artifact(self) -> ModelOnlyOperationalExecutionArtifactV1:
        return self._artifact


@dataclass(frozen=True, slots=True)
class AbstractOnlyOccurrenceWorkSumV1:
    """Reducer-exact one-component occurrence total for an abstract PASS.

    Unlike the older local+fallback occurrence schema, an abstract-only
    certificate has no decision point and no transaction.  Its one comparison
    vector is therefore already the reducer-aware occurrence total.
    """

    logical_occurrence_id: str
    route_decision_context_id: str
    route_attempt_id: str
    counter_registry_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    work_vector_id: str
    comparison_vector_id: str
    actual_projection_proof_id: str
    native_zero_attestation_id: str
    reconciliation_proof_id: str
    aggregate_values: tuple[tuple[str, int], ...]
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    workload_economics_gate: str = WORKLOAD_ECONOMICS_GATE_NOT_RUN
    counter_completeness_gate: str = COUNTER_COMPLETENESS_GATE_NOT_RUN

    def __post_init__(self) -> None:
        for field in (
            "logical_occurrence_id",
            "route_decision_context_id",
            "route_attempt_id",
            "counter_registry_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "work_vector_id",
            "comparison_vector_id",
            "actual_projection_proof_id",
            "native_zero_attestation_id",
            "reconciliation_proof_id",
        ):
            _cid(getattr(self, field), field)
        object.__setattr__(self, "aggregate_values", _axis_values(self.aggregate_values))
        if self.official_execution_allowed is not False:
            raise Phase3EAbstractPassClosureV1Error(
                "model-only PASS must not unlock official execution"
            )
        if self.official_scalar_cost is not None or self.official_N_break_even is not None:
            raise Phase3EAbstractPassClosureV1Error(
                "model-only PASS cannot invent scalar economics"
            )
        if (
            self.workload_economics_gate != WORKLOAD_ECONOMICS_GATE_NOT_RUN
            or self.counter_completeness_gate != COUNTER_COMPLETENESS_GATE_NOT_RUN
        ):
            raise Phase3EAbstractPassClosureV1Error(
                "model-only PASS cannot change locked Phase-3E gates"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ABSTRACT_ONLY_OCCURRENCE_WORK_SUM_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "logical_occurrence_id": self.logical_occurrence_id,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "route_attempt_id": self.route_attempt_id,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "actual_projection_proof_id": self.actual_projection_proof_id,
            "native_zero_attestation_id": self.native_zero_attestation_id,
            "reconciliation_proof_id": self.reconciliation_proof_id,
            "aggregate_values": [
                {"axis": axis, "value": value}
                for axis, value in self.aggregate_values
            ],
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "workload_economics_gate": WORKLOAD_ECONOMICS_GATE_NOT_RUN,
            "counter_completeness_gate": COUNTER_COMPLETENESS_GATE_NOT_RUN,
        }

    @property
    def abstract_only_occurrence_work_sum_id(self) -> str:
        return content_id(ABSTRACT_ONLY_OCCURRENCE_WORK_SUM_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "abstract_only_occurrence_work_sum_id": (
                self.abstract_only_occurrence_work_sum_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "AbstractOnlyOccurrenceWorkSumV1":
        expected = {
            "schema",
            "schema_version",
            "logical_occurrence_id",
            "RouteDecisionContext_id",
            "route_attempt_id",
            "counter_registry_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "work_vector_id",
            "comparison_vector_id",
            "actual_projection_proof_id",
            "native_zero_attestation_id",
            "reconciliation_proof_id",
            "aggregate_values",
            "official_execution_allowed",
            "official_scalar_cost",
            "official_N_break_even",
            "workload_economics_gate",
            "counter_completeness_gate",
            "abstract_only_occurrence_work_sum_id",
        }
        try:
            require_exact_fields(
                document, expected, context="AbstractOnlyOccurrenceWorkSumV1"
            )
        except Phase3EIdentityError as error:
            raise Phase3EAbstractPassClosureV1Error(str(error)) from error
        if (
            document["schema"] != ABSTRACT_ONLY_OCCURRENCE_WORK_SUM_SCHEMA
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["aggregate_values"]) is not list
        ):
            raise Phase3EAbstractPassClosureV1Error(
                "abstract-only occurrence-work-sum schema mismatch"
            )
        values: list[tuple[str, int]] = []
        for row in document["aggregate_values"]:
            try:
                require_exact_fields(
                    row, {"axis", "value"}, context="abstract-only aggregate axis"
                )
            except Phase3EIdentityError as error:
                raise Phase3EAbstractPassClosureV1Error(str(error)) from error
            values.append((row["axis"], row["value"]))
        result = cls(
            document["logical_occurrence_id"],
            document["RouteDecisionContext_id"],
            document["route_attempt_id"],
            document["counter_registry_id"],
            document["comparison_profile_id"],
            document["actual_projection_profile_id"],
            document["work_vector_id"],
            document["comparison_vector_id"],
            document["actual_projection_proof_id"],
            document["native_zero_attestation_id"],
            document["reconciliation_proof_id"],
            tuple(values),
            document["official_execution_allowed"],
            document["official_scalar_cost"],
            document["official_N_break_even"],
            document["workload_economics_gate"],
            document["counter_completeness_gate"],
        )
        if (
            document["abstract_only_occurrence_work_sum_id"]
            != result.abstract_only_occurrence_work_sum_id
        ):
            raise Phase3EAbstractPassClosureV1Error(
                "abstract-only occurrence-work-sum content ID mismatch"
            )
        return result


def derive_abstract_only_occurrence_work_sum_v1(
    model_only_result: Phase3EModelOnlyResultV1,
    recorded_work: RecordedWorkV1,
    *,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> AbstractOnlyOccurrenceWorkSumV1:
    try:
        replayed = verify_recorded_work_v1(
            recorded_work,
            expected_scope=ActualWorkScope.COMMON_PREFIX,
            registry=registry,
            comparison_profile=comparison_profile,
        )
    except ValueError as error:
        raise Phase3EAbstractPassClosureV1Error(
            f"model-only native work does not replay: {error}"
        ) from error
    vector = replayed.work_vector
    context = model_only_result.route_context
    if (
        vector.route_kind is not RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
        or vector.subject_id != context.route_attempt_id
        or vector.counter_registry_id != context.counter_registry_id
        or replayed.comparison_vector.comparison_profile_id
        != context.comparison_profile_id
        or replayed.actual_projection_proof.actual_projection_profile_id
        != actual_profile.actual_projection_profile_id
    ):
        raise Phase3EAbstractPassClosureV1Error(
            "model-only native work belongs to another route/context/profile"
        )
    if any(
        record.recorder_id != MODEL_ONLY_NATIVE_RECORDER_ID
        for record in vector.records
    ):
        raise Phase3EAbstractPassClosureV1Error(
            "model-only work was not emitted by the registered model-only recorder"
        )
    missing = tuple(
        path
        for path in _REQUIRED_POSITIVE_MODEL_ONLY_COUNTERS
        if vector.value(path) <= 0
    )
    if missing:
        raise Phase3EAbstractPassClosureV1Error(
            "model-only work omits required observed operations: " + ", ".join(missing)
        )
    return AbstractOnlyOccurrenceWorkSumV1(
        model_only_result.logical_occurrence.logical_occurrence_id,
        context.route_decision_context_id,
        context.route_attempt_id,
        registry.registry_id,
        comparison_profile.comparison_profile_id,
        actual_profile.actual_projection_profile_id,
        vector.work_vector_id,
        replayed.comparison_vector.comparison_vector_id,
        replayed.actual_projection_proof.actual_projection_proof_id,
        replayed.native_zero_attestation.native_zero_attestation_id,
        replayed.reconciliation_proof.reconciliation_proof_id,
        replayed.comparison_vector.values,
    )


def _expected_model_only_execution_artifact_v1(
    request: ModelOnlyOperationalRequestV1,
    result: Phase3EModelOnlyResultV1,
    recorded_work: RecordedWorkV1,
) -> ModelOnlyOperationalExecutionArtifactV1:
    return ModelOnlyOperationalExecutionArtifactV1(
        request.model_only_operational_request_id,
        request.source_lease_id,
        result.result_id,
        result.selected_plan.selected_contingent_plan_id,
        result.route_context.route_decision_context_id,
        result.route_attempt.route_attempt_id,
        recorded_work.work_vector.work_vector_id,
        recorded_work.comparison_vector.comparison_vector_id,
        recorded_work.actual_projection_proof.actual_projection_proof_id,
        recorded_work.native_zero_attestation.native_zero_attestation_id,
        recorded_work.reconciliation_proof.reconciliation_proof_id,
    )


def _validate_model_only_request_result_v1(
    request: ModelOnlyOperationalRequestV1,
    result: Phase3EModelOnlyResultV1,
) -> None:
    if type(request) is not ModelOnlyOperationalRequestV1 or type(
        result
    ) is not Phase3EModelOnlyResultV1:
        raise Phase3EAbstractPassClosureV1Error(
            "model-only execution requires exact request/result runtime types"
        )
    replayed_request = ModelOnlyOperationalRequestV1.from_dict(request.to_dict())
    lease = RAPMSourceLeaseV1.from_dict(result.source_lease.to_dict())
    if (
        replayed_request.source_lease_id != lease.source_lease_id
        or replayed_request.query_key != lease.query_key
        or replayed_request.legacy_portable_rapm_id
        != lease.legacy_portable_rapm_id
        or replayed_request.legacy_portable_query_id
        != lease.legacy_portable_query_id
        or replayed_request.kernel_sha256 != lease.kernel_sha256
        or replayed_request.regret_tolerance != result.audit.regret_tolerance
    ):
        raise Phase3EAbstractPassClosureV1Error(
            "model-only operational request/result/source identity mismatch"
        )
    if (
        result.outcome is not ModelOnlyOutcome.PASS
        or result.ground_binding_required
    ):
        raise Phase3EAbstractPassClosureV1Error(
            "MODEL_ONLY_PASS_CLOSURE cannot authorize failed-prefix work"
        )


def _seal_model_only_operational_execution_v1(
    request: ModelOnlyOperationalRequestV1,
    result: Phase3EModelOnlyResultV1,
    recorded_work: RecordedWorkV1,
    *,
    registry: CounterRegistryV1 | None = None,
) -> _LegacyBareWorkPassAuthorityV1:
    """Trusted-factory seam used until the model-only runner owns recording.

    This helper is intentionally private.  Public closure consumes only its
    opaque result.  The production runner must eventually call this at the end
    of one recorder-owned PASS execution; it must never be used for H2 FAIL
    prefix work.
    """

    _validate_model_only_request_result_v1(request, result)
    trusted_registry = registry or official_counter_registry_v1()
    comparison_profile = official_comparison_profile_v1(trusted_registry)
    actual_profile = official_actual_projection_profile_v1(
        trusted_registry, comparison_profile
    )
    # Replays all native/projection identities and the registered recorder.
    derive_abstract_only_occurrence_work_sum_v1(
        result,
        recorded_work,
        registry=trusted_registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    artifact = _expected_model_only_execution_artifact_v1(
        request, result, recorded_work
    )
    return _LegacyBareWorkPassAuthorityV1(
        request,
        result,
        recorded_work,
        artifact,
        _MODEL_ONLY_OPERATIONAL_EXECUTION_AUTHORITY,
    )


def verify_model_only_operational_execution_v1(
    execution: ModelOnlyQueryExecutionV1,
    *,
    registry: CounterRegistryV1 | None = None,
) -> ModelOnlyQueryExecutionV1:
    """Require the executor-owned PASS seal without planning or ground access."""

    try:
        retained = verify_model_only_query_execution_v1(execution)
    except (Phase3EModelOnlyExecutorV1Error, TypeError, ValueError) as error:
        raise Phase3EAbstractPassClosureV1Error(
            f"abstract PASS requires executor-owned execution authority: {error}"
        ) from error
    result = retained.model_only_result
    if (
        result.outcome is not ModelOnlyOutcome.PASS
        or result.ground_binding_required
        or retained.recorded_work.work_vector.route_kind
        is not RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
    ):
        raise Phase3EAbstractPassClosureV1Error(
            "abstract PASS closure rejects failed-prefix execution authority"
        )
    trusted_registry = registry or official_counter_registry_v1()
    comparison_profile = official_comparison_profile_v1(trusted_registry)
    actual_profile = official_actual_projection_profile_v1(
        trusted_registry, comparison_profile
    )
    derive_abstract_only_occurrence_work_sum_v1(
        result,
        retained.recorded_work,
        registry=trusted_registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )
    return retained


@dataclass(frozen=True, slots=True)
class ModelOnlyAbstractPassClosureV1:
    """Runtime authority bundle for a non-official abstract certificate closure."""

    operational_execution: ModelOnlyQueryExecutionV1
    audit_result: SemanticVerificationResultV1
    work_result: SemanticVerificationResultV1
    terminal_result: SemanticVerificationResultV1
    occurrence_work_sum: AbstractOnlyOccurrenceWorkSumV1
    campaign_closure: CampaignOccurrenceClosureV1
    accounting_status: str = MODEL_ONLY_PASS_ACCOUNTING_STATUS
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None

    def __post_init__(self) -> None:
        execution = verify_model_only_operational_execution_v1(
            self.operational_execution
        )
        try:
            campaign_closure = (
                require_campaign_occurrence_closure_authority_v1(
                    self.campaign_closure
                )
            )
            audit = require_semantic_verification_result_v1(
                self.audit_result, SemanticRole.ABSTRACT_AUDIT
            )
            work = require_semantic_verification_result_v1(
                self.work_result, SemanticRole.WORK_VECTOR
            )
            terminal, _ = require_terminal_classification_result_v1(
                self.terminal_result
            )
        except (CampaignV1Error, SemanticVerificationV1Error) as error:
            raise Phase3EAbstractPassClosureV1Error(str(error)) from error
        if audit.outcome != "PASS" or work.outcome != "VALID":
            raise Phase3EAbstractPassClosureV1Error(
                "abstract closure requires ABSTRACT_AUDIT=PASS and WORK_VECTOR=VALID"
            )
        if (
            terminal.terminal_class is not TerminalClass.PLAN_CERTIFICATE
            or terminal.terminal_code is not TerminalCode.ABSTRACT_CERTIFIED
            or terminal.actual_work_vector_id
            != execution.recorded_work.work_vector.work_vector_id
            or self.occurrence_work_sum.work_vector_id
            != terminal.actual_work_vector_id
            or campaign_closure.final_terminal_artifact_id
            != terminal.terminal_artifact_id
            or campaign_closure.occurrence_work_sum_id
            != self.occurrence_work_sum.abstract_only_occurrence_work_sum_id
        ):
            raise Phase3EAbstractPassClosureV1Error(
                "abstract terminal/accounting/campaign closure chain is inconsistent"
            )
        if (
            self.accounting_status != MODEL_ONLY_PASS_ACCOUNTING_STATUS
            or self.official_execution_allowed is not False
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
        ):
            raise Phase3EAbstractPassClosureV1Error(
                "abstract PASS closure cannot claim official economics"
            )

    @property
    def terminal_artifact(self) -> TerminalArtifactV1:
        terminal, _ = require_terminal_classification_result_v1(
            self.terminal_result
        )
        return terminal

    @property
    def model_only_result(self) -> Phase3EModelOnlyResultV1:
        return self.operational_execution.model_only_result

    @property
    def recorded_work(self) -> RecordedWorkV1:
        return self.operational_execution.recorded_work


def close_model_only_abstract_pass_v1(
    operational_execution: ModelOnlyQueryExecutionV1,
    abstract_audit_authority: SemanticVerificationResultV1,
    *,
    work_verification_record: CounterRecordV1 | Mapping[str, Any],
    terminal_verification_record: CounterRecordV1 | Mapping[str, Any],
    registry: CounterRegistryV1 | None = None,
    ground_binding: object | None = None,
    ground_executor: object | None = None,
) -> ModelOnlyAbstractPassClosureV1:
    """Close one retained abstract PASS without planning or ground access.

    ``ground_binding`` and ``ground_executor`` are rejection-only parameters:
    they make accidental coupling at this boundary explicit and fail closed.
    """

    if ground_binding is not None or ground_executor is not None:
        raise Phase3EAbstractPassClosureV1Error(
            "abstract PASS closure forbids ground binding and route executors"
        )
    execution = verify_model_only_operational_execution_v1(
        operational_execution, registry=registry
    )
    model_only_result = execution.model_only_result
    recorded_work = execution.recorded_work
    try:
        audit_result = require_semantic_verification_result_v1(
            abstract_audit_authority, SemanticRole.ABSTRACT_AUDIT
        )
        verify_typed_attestation_v1(
            audit_result.attestation, authority_result=audit_result, registry=registry
        )
    except (SemanticVerificationV1Error, TypeError, ValueError) as error:
        raise Phase3EAbstractPassClosureV1Error(
            f"abstract PASS lacks retained semantic authority: {error}"
        ) from error
    if (
        audit_result.outcome != "PASS"
        or audit_result.artifact != model_only_result.audit
        or audit_result.attestation.artifact_id != model_only_result.audit.audit_id
        or audit_result.binding.route_context != model_only_result.route_context
        or not isinstance(audit_result.binding.decision_point_id, TypedNotApplicable)
        or not isinstance(audit_result.binding.transaction_id, TypedNotApplicable)
        or model_only_result.result_id not in audit_result.recomputed_evidence_ids
    ):
        raise Phase3EAbstractPassClosureV1Error(
            "abstract audit authority uses another result, outcome, or route context"
        )

    trusted_registry = registry or official_counter_registry_v1()
    trusted_registry.validate_official_catalogue()
    comparison_profile = official_comparison_profile_v1(trusted_registry)
    actual_profile = official_actual_projection_profile_v1(
        trusted_registry, comparison_profile
    )
    if (
        model_only_result.route_context.counter_registry_id
        != trusted_registry.registry_id
        or model_only_result.route_context.comparison_profile_id
        != comparison_profile.comparison_profile_id
    ):
        raise Phase3EAbstractPassClosureV1Error(
            "model-only result uses another counter/comparison profile"
        )
    occurrence_sum = derive_abstract_only_occurrence_work_sum_v1(
        model_only_result,
        recorded_work,
        registry=trusted_registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
    )

    # Terminal replay is standalone evaluation work.  The exact typed-null
    # references are retained from the abstract audit authority.
    terminal_binding = AttestationContextV1(
        model_only_result.route_context,
        audit_result.binding.decision_point_id,
        audit_result.binding.transaction_id,
        audit_result.binding.verified_at_protocol_step + 1,
        LaneEnum.EVALUATION,
    )
    try:
        work_result = verify_work_vector_semantics_v1(
            recorded_work.work_vector,
            binding=terminal_binding,
            verification_work_record=work_verification_record,
            registry=trusted_registry,
        )
        evidence_ids = tuple(
            sorted(
                (
                    audit_result.attestation.verification_attestation_id,
                    work_result.attestation.verification_attestation_id,
                )
            )
        )
        terminal = TerminalArtifactV1(
            "ROUTE_ATTEMPT",
            TerminalClass.PLAN_CERTIFICATE,
            TerminalCode.ABSTRACT_CERTIFIED,
            model_only_result.route_context.route_decision_context_id,
            model_only_result.logical_occurrence.logical_occurrence_id,
            model_only_result.route_attempt.route_attempt_id,
            terminal_binding.decision_point_id,
            terminal_binding.transaction_id,
            recorded_work.work_vector.work_vector_id,
            evidence_ids,
        )
        terminal_result = verify_terminal_classification_semantics_v1(
            terminal,
            evidence_results=(work_result, audit_result),
            binding=terminal_binding,
            verification_work_record=terminal_verification_record,
            registry=trusted_registry,
        )
        campaign_closure = CampaignOccurrenceClosureV1.close(
            model_only_result.logical_occurrence,
            model_only_result.rebuild_policy,
            (model_only_result.route_attempt,),
            (terminal_result,),
            ((recorded_work.work_vector.work_vector_id,),),
            occurrence_sum.abstract_only_occurrence_work_sum_id,
        )
    except (SemanticVerificationV1Error, ValueError) as error:
        raise Phase3EAbstractPassClosureV1Error(
            f"abstract terminal/campaign semantic closure failed: {error}"
        ) from error

    return ModelOnlyAbstractPassClosureV1(
        execution,
        audit_result,
        work_result,
        terminal_result,
        occurrence_sum,
        campaign_closure,
    )


__all__ = [
    "ABSTRACT_ONLY_OCCURRENCE_WORK_SUM_SCHEMA",
    "AbstractOnlyOccurrenceWorkSumV1",
    "MODEL_ONLY_NATIVE_RECORDER_ID",
    "MODEL_ONLY_PASS_ACCOUNTING_STATUS",
    "ModelOnlyAbstractPassClosureV1",
    "Phase3EAbstractPassClosureV1Error",
    "close_model_only_abstract_pass_v1",
    "derive_abstract_only_occurrence_work_sum_v1",
    "verify_model_only_operational_execution_v1",
]
