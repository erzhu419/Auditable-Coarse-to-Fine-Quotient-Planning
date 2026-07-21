"""Bounded, non-official rebuild/retry orchestration for one occurrence.

The lower-level :mod:`acfqp.campaign_v1` contracts already define the
authoritative FQ8/FQ9 identities.  This module adds only the missing execution
order: inspect one verified attempt terminal, invoke one preregistered rebuild
recipe exactly when it is both required and allowed, create a new BuildEpoch,
run one retry, and close the same logical-occurrence denominator.

Every supplied work reference is an exact ``RecordedWorkV1`` replay.  Rebuild
work is kept in its own native ``REBUILD`` vector and is never folded into an
attempt vector.  This slice is intentionally non-official: the in-process
callback boundary and global hash/I/O instrumentation are not yet independently
attested, so economics and counter-completeness gates remain locked.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    ReducerEnum,
    RouteKindEnum,
    SHARED_AXES,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.campaign_v1 import (
    COUNTER_COMPLETENESS_GATE_NOT_RUN,
    SCALAR_GATE_NOT_RUN,
    WORKLOAD_ECONOMICS_GATE_NOT_RUN,
    AttemptClosureRecordV1,
    CampaignOccurrenceClosureV1,
    LogicalOccurrenceV1,
    RebuildEventV1,
    RebuildPolicyV1,
    RouteAttemptV1,
    require_campaign_occurrence_closure_authority_v1,
)
from acfqp.native_recorder_v1 import (
    NativeRecorderV1Error,
    RecordedWorkV1,
    verify_recorded_work_v1,
)
from acfqp.phase3e_ids import (
    BOUNDED_REBUILD_OCCURRENCE_WORK_SUM_DOMAIN,
    Phase3EIdentityError,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.routing_v1 import SCHEMA_VERSION, TerminalCode
from acfqp.semantic_verification_v1 import (
    SemanticVerificationResultV1,
    SemanticVerificationV1Error,
    require_terminal_classification_result_v1,
)


BOUNDED_REBUILD_RUNNER_STATUS = "NONOFFICIAL_BOUNDED_REBUILD_RETRY_EXECUTED"
BOUNDED_REBUILD_RUNNER_BLOCKERS = (
    "REBUILD_REQUIRED_SOURCE_TERMINAL_PRODUCER_NOT_INTEGRATED",
    "REBUILD_CALLBACK_PROCESS_ISOLATION_NOT_ATTESTED",
    "REBUILD_CALLBACK_NATIVE_INSTRUMENTATION_NOT_INDEPENDENTLY_ATTESTED",
    "ALL_PATH_HASH_IO_AND_RUNTIME_INSTRUMENTATION_NOT_COMPLETE",
    "INDEPENDENT_COMPLETE_BUNDLE_VERIFIER_NOT_IMPLEMENTED",
)


class Phase3EBoundedRebuildRunnerV1Error(ValueError):
    """A retry was unauthorized, stale, foreign, or not exactly accounted."""


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise Phase3EBoundedRebuildRunnerV1Error(
            f"{field} must be a full Phase-3E content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class AttemptExecutionReceiptV1:
    """Live terminal authority plus every exact native work reference."""

    terminal_result: SemanticVerificationResultV1
    work: tuple[RecordedWorkV1, ...]

    def __post_init__(self) -> None:
        if type(self.terminal_result) is not SemanticVerificationResultV1:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "attempt receipt requires a live semantic terminal result"
            )
        if type(self.work) is not tuple or not self.work:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "attempt receipt requires nonempty exact work references"
            )
        if any(type(row) is not RecordedWorkV1 for row in self.work):
            raise Phase3EBoundedRebuildRunnerV1Error(
                "attempt work references must be exact RecordedWorkV1 values"
            )


@dataclass(frozen=True, slots=True)
class RebuildInvocationV1:
    """Frozen arguments passed to the registered rebuild recipe."""

    occurrence: LogicalOccurrenceV1
    policy: RebuildPolicyV1
    source_attempt: RouteAttemptV1
    source_terminal_result: SemanticVerificationResultV1
    rebuild_recipe_id: str

    def __post_init__(self) -> None:
        _cid(self.rebuild_recipe_id, "rebuild_recipe_id")
        if self.occurrence.rebuild_policy_id != self.policy.rebuild_policy_id:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "rebuild invocation uses another policy"
            )
        if self.policy.rebuild_recipe_id != self.rebuild_recipe_id:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "rebuild invocation does not bind the registered recipe"
            )
        if self.source_attempt.logical_occurrence_id != (
            self.occurrence.logical_occurrence_id
        ):
            raise Phase3EBoundedRebuildRunnerV1Error(
                "rebuild invocation source belongs to another occurrence"
            )


@dataclass(frozen=True, slots=True)
class RebuildExecutionReceiptV1:
    """A newly built epoch and its separate exact native rebuild work."""

    new_build_epoch_id: str
    work: RecordedWorkV1

    def __post_init__(self) -> None:
        _cid(self.new_build_epoch_id, "new_build_epoch_id")
        if type(self.work) is not RecordedWorkV1:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "rebuild receipt requires exact RecordedWorkV1 work"
            )


class RebuildCallbackV1(Protocol):
    def __call__(self, invocation: RebuildInvocationV1) -> RebuildExecutionReceiptV1:
        ...


class RetryCallbackV1(Protocol):
    def __call__(self, attempt: RouteAttemptV1) -> AttemptExecutionReceiptV1:
        ...


@dataclass(frozen=True, slots=True)
class RegisteredRebuildCallbackV1:
    """In-process callback explicitly bound to a preregistered recipe ID."""

    rebuild_recipe_id: str
    callback: RebuildCallbackV1

    def __post_init__(self) -> None:
        _cid(self.rebuild_recipe_id, "rebuild_recipe_id")
        if not callable(self.callback):
            raise Phase3EBoundedRebuildRunnerV1Error(
                "registered rebuild callback is not callable"
            )


@dataclass(frozen=True, slots=True)
class BoundedRebuildWorkComponentV1:
    sequence_index: int
    component_kind: str
    route_attempt_index: int
    work_vector_id: str
    comparison_vector_id: str
    route_kind: RouteKindEnum
    work_scope: ActualWorkScope

    def __post_init__(self) -> None:
        if type(self.sequence_index) is not int or self.sequence_index <= 0:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "work-component sequence index must be positive"
            )
        if self.component_kind not in {"ATTEMPT", "REBUILD"}:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "work-component kind must be ATTEMPT or REBUILD"
            )
        if self.route_attempt_index not in {1, 2}:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "work-component attempt index must be 1 or 2"
            )
        _cid(self.work_vector_id, "work_vector_id")
        _cid(self.comparison_vector_id, "comparison_vector_id")
        try:
            object.__setattr__(self, "route_kind", RouteKindEnum(self.route_kind))
            object.__setattr__(self, "work_scope", ActualWorkScope(self.work_scope))
        except (TypeError, ValueError) as error:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "work component has an invalid route kind or scope"
            ) from error
        is_rebuild_route = self.route_kind is RouteKindEnum.REBUILD
        is_rebuild_scope = self.work_scope is ActualWorkScope.REBUILD_EXECUTION
        if (
            self.component_kind == "REBUILD"
            and not (is_rebuild_route and is_rebuild_scope)
        ) or (
            self.component_kind == "ATTEMPT"
            and (is_rebuild_route or is_rebuild_scope)
        ):
            raise Phase3EBoundedRebuildRunnerV1Error(
                "rebuild component kind, route kind, and work scope disagree"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_index": self.sequence_index,
            "component_kind": self.component_kind,
            "route_attempt_index": self.route_attempt_index,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "route_kind": self.route_kind.value,
            "work_scope": self.work_scope.value,
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "BoundedRebuildWorkComponentV1":
        try:
            require_exact_fields(
                document,
                {
                    "sequence_index",
                    "component_kind",
                    "route_attempt_index",
                    "work_vector_id",
                    "comparison_vector_id",
                    "route_kind",
                    "work_scope",
                },
                context="bounded rebuild work component",
            )
        except (Phase3EIdentityError, ValueError) as error:
            raise Phase3EBoundedRebuildRunnerV1Error(str(error)) from error
        return cls(
            document["sequence_index"],
            document["component_kind"],
            document["route_attempt_index"],
            document["work_vector_id"],
            document["comparison_vector_id"],
            document["route_kind"],
            document["work_scope"],
        )


@dataclass(frozen=True, slots=True)
class BoundedRebuildOccurrenceWorkSumV1:
    """Reducer-aware total retaining attempt/rebuild provenance separately."""

    logical_occurrence_id: str
    components: tuple[BoundedRebuildWorkComponentV1, ...]
    aggregate_values: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        _cid(self.logical_occurrence_id, "logical_occurrence_id")
        if not self.components:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "bounded occurrence work sum cannot be empty"
            )
        if tuple(row.sequence_index for row in self.components) != tuple(
            range(1, len(self.components) + 1)
        ):
            raise Phase3EBoundedRebuildRunnerV1Error(
                "work components must have continuous execution sequence"
            )
        ids = tuple(row.work_vector_id for row in self.components)
        if len(set(ids)) != len(ids):
            raise Phase3EBoundedRebuildRunnerV1Error(
                "occurrence work sum repeats a WorkVector"
            )
        if tuple(axis for axis, _ in self.aggregate_values) != SHARED_AXES:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "occurrence work sum must contain exact shared axes"
            )
        for _, value in self.aggregate_values:
            if type(value) is not int or value < 0:
                raise Phase3EBoundedRebuildRunnerV1Error(
                    "occurrence aggregate values must be nonnegative integers"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.bounded_rebuild_occurrence_work_sum.v1",
            "schema_version": SCHEMA_VERSION,
            "logical_occurrence_id": self.logical_occurrence_id,
            "components": [row.to_dict() for row in self.components],
            "aggregate_values": [
                {"axis": axis, "value": value}
                for axis, value in self.aggregate_values
            ],
        }

    @property
    def bounded_rebuild_occurrence_work_sum_id(self) -> str:
        return content_id(
            BOUNDED_REBUILD_OCCURRENCE_WORK_SUM_DOMAIN, self._payload()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "bounded_rebuild_occurrence_work_sum_id": (
                self.bounded_rebuild_occurrence_work_sum_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "BoundedRebuildOccurrenceWorkSumV1":
        expected = {
            "schema",
            "schema_version",
            "logical_occurrence_id",
            "components",
            "aggregate_values",
            "bounded_rebuild_occurrence_work_sum_id",
        }
        try:
            require_exact_fields(
                document, expected, context="bounded rebuild occurrence work sum"
            )
        except (Phase3EIdentityError, ValueError) as error:
            raise Phase3EBoundedRebuildRunnerV1Error(str(error)) from error
        if (
            document["schema"]
            != "acfqp.bounded_rebuild_occurrence_work_sum.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["components"]) is not list
            or type(document["aggregate_values"]) is not list
        ):
            raise Phase3EBoundedRebuildRunnerV1Error(
                "bounded occurrence-work-sum schema mismatch"
            )
        try:
            values_list: list[tuple[str, int]] = []
            for row in document["aggregate_values"]:
                require_exact_fields(
                    row,
                    {"axis", "value"},
                    context="bounded occurrence aggregate axis",
                )
                values_list.append((row["axis"], row["value"]))
            values = tuple(values_list)
        except (KeyError, TypeError, Phase3EIdentityError, ValueError) as error:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "invalid occurrence aggregate axis row"
            ) from error
        result = cls(
            document["logical_occurrence_id"],
            tuple(
                BoundedRebuildWorkComponentV1.from_dict(row)
                for row in document["components"]
            ),
            values,
        )
        if document["bounded_rebuild_occurrence_work_sum_id"] != (
            result.bounded_rebuild_occurrence_work_sum_id
        ):
            raise Phase3EBoundedRebuildRunnerV1Error(
                "bounded occurrence-work-sum content ID mismatch"
            )
        return result


@dataclass(frozen=True, slots=True)
class BoundedRebuildOccurrenceRunV1:
    occurrence: LogicalOccurrenceV1
    policy: RebuildPolicyV1
    attempts: tuple[RouteAttemptV1, ...]
    attempt_receipts: tuple[AttemptExecutionReceiptV1, ...]
    rebuild_receipt: RebuildExecutionReceiptV1 | None
    rebuild_event: RebuildEventV1 | None
    occurrence_work_sum: BoundedRebuildOccurrenceWorkSumV1
    closure: CampaignOccurrenceClosureV1
    status: str = BOUNDED_REBUILD_RUNNER_STATUS
    blockers: tuple[str, ...] = BOUNDED_REBUILD_RUNNER_BLOCKERS
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    workload_economics_gate_status: str = WORKLOAD_ECONOMICS_GATE_NOT_RUN
    counter_completeness_gate_status: str = COUNTER_COMPLETENESS_GATE_NOT_RUN
    scalar_gate_status: str = SCALAR_GATE_NOT_RUN

    def __post_init__(self) -> None:
        try:
            require_campaign_occurrence_closure_authority_v1(self.closure)
        except ValueError as error:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "bounded runner closure lacks retained campaign authority"
            ) from error
        if len(self.attempts) != len(self.attempt_receipts) or len(
            self.attempts
        ) not in {1, 2}:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "bounded run has misaligned attempt receipts"
            )
        retry = len(self.attempts) == 2
        if retry != (self.rebuild_receipt is not None) or retry != (
            self.rebuild_event is not None
        ):
            raise Phase3EBoundedRebuildRunnerV1Error(
                "bounded retry must retain one rebuild receipt and event"
            )
        if self.closure.logical_occurrence_id != self.occurrence.logical_occurrence_id:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "bounded closure belongs to another occurrence"
            )
        if self.closure.occurrence_work_sum_id != (
            self.occurrence_work_sum.bounded_rebuild_occurrence_work_sum_id
        ):
            raise Phase3EBoundedRebuildRunnerV1Error(
                "campaign closure omits the exact bounded occurrence work sum"
            )
        if (
            self.status != BOUNDED_REBUILD_RUNNER_STATUS
            or self.blockers != BOUNDED_REBUILD_RUNNER_BLOCKERS
            or self.official_execution_allowed is not False
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.workload_economics_gate_status
            != WORKLOAD_ECONOMICS_GATE_NOT_RUN
            or self.counter_completeness_gate_status
            != COUNTER_COMPLETENESS_GATE_NOT_RUN
            or self.scalar_gate_status != SCALAR_GATE_NOT_RUN
        ):
            raise Phase3EBoundedRebuildRunnerV1Error(
                "bounded rebuild runner cannot hide its non-official gate blockers"
            )


def _validate_attempt_receipt(
    occurrence: LogicalOccurrenceV1,
    attempt: RouteAttemptV1,
    receipt: AttemptExecutionReceiptV1,
    *,
    profile: ComparisonProfileV1,
) -> tuple[tuple[RecordedWorkV1, ...], tuple[str, ...]]:
    registry = official_counter_registry_v1()
    try:
        terminal, _ = require_terminal_classification_result_v1(
            receipt.terminal_result
        )
    except SemanticVerificationV1Error as error:
        raise Phase3EBoundedRebuildRunnerV1Error(
            "attempt terminal lacks live classification authority"
        ) from error
    ordered = tuple(sorted(receipt.work, key=lambda row: row.work_vector.work_vector_id))
    ids = tuple(row.work_vector.work_vector_id for row in ordered)
    if len(set(ids)) != len(ids):
        raise Phase3EBoundedRebuildRunnerV1Error(
            "attempt receipt repeats a native WorkVector"
        )
    for row in ordered:
        try:
            verify_recorded_work_v1(
                row,
                expected_scope=row.actual_projection_proof.work_scope,
                registry=registry,
                comparison_profile=profile,
            )
        except NativeRecorderV1Error as error:
            raise Phase3EBoundedRebuildRunnerV1Error(
                f"attempt native work does not replay: {error}"
            ) from error
        if row.work_vector.route_kind is RouteKindEnum.REBUILD:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "rebuild work must remain separate from attempt work"
            )
    if terminal.actual_work_vector_id not in ids:
        raise Phase3EBoundedRebuildRunnerV1Error(
            "attempt receipt omitted the terminal actual WorkVector"
        )
    # Reuse the campaign authority's full occurrence/query/attempt/epoch check
    # before any rebuild callback can run.
    try:
        AttemptClosureRecordV1.bind(
            occurrence, attempt, receipt.terminal_result, ids
        )
    except ValueError as error:
        raise Phase3EBoundedRebuildRunnerV1Error(
            f"attempt receipt is foreign or stale: {error}"
        ) from error
    return ordered, ids


def _validate_rebuild_receipt(
    receipt: RebuildExecutionReceiptV1,
    *,
    source_attempt: RouteAttemptV1,
    profile: ComparisonProfileV1,
) -> RecordedWorkV1:
    if receipt.new_build_epoch_id == source_attempt.build_epoch_id:
        raise Phase3EBoundedRebuildRunnerV1Error(
            "rebuild callback returned the stale BuildEpoch"
        )
    registry = official_counter_registry_v1()
    try:
        verified = verify_recorded_work_v1(
            receipt.work,
            expected_scope=ActualWorkScope.REBUILD_EXECUTION,
            registry=registry,
            comparison_profile=profile,
        )
    except NativeRecorderV1Error as error:
        raise Phase3EBoundedRebuildRunnerV1Error(
            f"rebuild native work does not replay: {error}"
        ) from error
    vector = verified.work_vector
    if (
        vector.route_kind is not RouteKindEnum.REBUILD
        or vector.subject_id != receipt.new_build_epoch_id
    ):
        raise Phase3EBoundedRebuildRunnerV1Error(
            "rebuild work does not bind the new BuildEpoch"
        )
    values = vector.values
    if (
        not any(value for path, value in values.items() if path.startswith("rebuild."))
        or values["io.output_bytes"] <= 0
    ):
        raise Phase3EBoundedRebuildRunnerV1Error(
            "rebuild work must charge native rebuild work and new-epoch output"
        )
    return verified


def _derive_occurrence_sum(
    occurrence: LogicalOccurrenceV1,
    attempt_rows: Sequence[Sequence[RecordedWorkV1]],
    rebuild: RecordedWorkV1 | None,
    profile: ComparisonProfileV1,
) -> BoundedRebuildOccurrenceWorkSumV1:
    ordered: list[tuple[str, int, RecordedWorkV1]] = []
    ordered.extend(("ATTEMPT", 1, row) for row in attempt_rows[0])
    if rebuild is not None:
        ordered.append(("REBUILD", 1, rebuild))
    if len(attempt_rows) == 2:
        ordered.extend(("ATTEMPT", 2, row) for row in attempt_rows[1])
    components = tuple(
        BoundedRebuildWorkComponentV1(
            index,
            kind,
            attempt_index,
            row.work_vector.work_vector_id,
            row.comparison_vector.comparison_vector_id,
            row.work_vector.route_kind,
            row.actual_projection_proof.work_scope,
        )
        for index, (kind, attempt_index, row) in enumerate(ordered, 1)
    )
    reducers = {axis.name: axis.reducer for axis in profile.axes}
    totals = {axis: 0 for axis in SHARED_AXES}
    for _, _, row in ordered:
        vector_rows = row.comparison_vector.values
        values = dict(vector_rows)
        if tuple(axis for axis, _ in vector_rows) != SHARED_AXES:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "comparison vector does not contain exact shared axes"
            )
        for axis in SHARED_AXES:
            if reducers[axis] is ReducerEnum.SUM:
                totals[axis] += values[axis]
            else:
                totals[axis] = max(totals[axis], values[axis])
    return BoundedRebuildOccurrenceWorkSumV1(
        occurrence.logical_occurrence_id,
        components,
        tuple((axis, totals[axis]) for axis in SHARED_AXES),
    )


def run_bounded_rebuild_retry_v1(
    occurrence: LogicalOccurrenceV1,
    policy: RebuildPolicyV1,
    initial_terminal_result: SemanticVerificationResultV1,
    initial_attempt_work: Sequence[RecordedWorkV1],
    *,
    rebuild_callback: RegisteredRebuildCallbackV1 | None = None,
    retry_callback: RetryCallbackV1 | None = None,
) -> BoundedRebuildOccurrenceRunV1:
    """Run at most one rebuild and one retry for one logical occurrence.

    Disabled policies and exhausted retry budgets close ``REBUILD_REQUIRED``
    honestly as a noncertificate.  Foreign/stale authorities, callback recipe
    substitution, malformed native work, and callback failures raise before a
    false closure or certificate can be emitted.
    """

    if type(occurrence) is not LogicalOccurrenceV1 or type(policy) is not RebuildPolicyV1:
        raise Phase3EBoundedRebuildRunnerV1Error(
            "bounded rebuild runner requires exact campaign contracts"
        )
    if occurrence.rebuild_policy_id != policy.rebuild_policy_id:
        raise Phase3EBoundedRebuildRunnerV1Error(
            "logical occurrence uses another rebuild policy"
        )
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    first = RouteAttemptV1.initial(occurrence)
    first_receipt = AttemptExecutionReceiptV1(
        initial_terminal_result, tuple(initial_attempt_work)
    )
    first_work, first_ids = _validate_attempt_receipt(
        occurrence, first, first_receipt, profile=profile
    )
    first_terminal, _ = require_terminal_classification_result_v1(
        first_receipt.terminal_result
    )

    attempts: tuple[RouteAttemptV1, ...] = (first,)
    receipts: tuple[AttemptExecutionReceiptV1, ...] = (first_receipt,)
    terminal_results: tuple[SemanticVerificationResultV1, ...] = (
        first_receipt.terminal_result,
    )
    attempt_ids: tuple[tuple[str, ...], ...] = (first_ids,)
    attempt_work: tuple[tuple[RecordedWorkV1, ...], ...] = (first_work,)
    rebuild_receipt: RebuildExecutionReceiptV1 | None = None
    rebuild_event: RebuildEventV1 | None = None
    rebuild_work: RecordedWorkV1 | None = None

    retry_allowed = policy.can_retry(route_attempt_count=1, rebuild_count=0)
    if first_terminal.terminal_code is TerminalCode.REBUILD_REQUIRED and retry_allowed:
        if rebuild_callback is None or retry_callback is None:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "allowed REBUILD_REQUIRED terminal needs registered rebuild and retry callbacks"
            )
        if type(rebuild_callback) is not RegisteredRebuildCallbackV1:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "rebuild callback lacks preregistered recipe binding"
            )
        if rebuild_callback.rebuild_recipe_id != policy.rebuild_recipe_id:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "rebuild callback uses a foreign recipe"
            )
        invocation = RebuildInvocationV1(
            occurrence,
            policy,
            first,
            first_receipt.terminal_result,
            rebuild_callback.rebuild_recipe_id,
        )
        produced = rebuild_callback.callback(invocation)
        if type(produced) is not RebuildExecutionReceiptV1:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "rebuild callback returned the wrong receipt type"
            )
        rebuild_receipt = produced
        rebuild_work = _validate_rebuild_receipt(
            produced, source_attempt=first, profile=profile
        )
        try:
            second = RouteAttemptV1.retry(
                occurrence,
                policy,
                first,
                first_receipt.terminal_result,
                produced.new_build_epoch_id,
            )
            rebuild_event = RebuildEventV1.authorize(
                occurrence,
                policy,
                first,
                first_receipt.terminal_result,
                second,
                rebuild_work.work_vector.work_vector_id,
            )
        except ValueError as error:
            raise Phase3EBoundedRebuildRunnerV1Error(
                f"rebuild retry authorization failed: {error}"
            ) from error
        if not callable(retry_callback):
            raise Phase3EBoundedRebuildRunnerV1Error(
                "retry callback is not callable"
            )
        second_receipt = retry_callback(second)
        if type(second_receipt) is not AttemptExecutionReceiptV1:
            raise Phase3EBoundedRebuildRunnerV1Error(
                "retry callback returned the wrong receipt type"
            )
        second_work, second_ids = _validate_attempt_receipt(
            occurrence, second, second_receipt, profile=profile
        )
        all_ids = set(first_ids)
        if rebuild_work.work_vector.work_vector_id in all_ids or any(
            value in all_ids for value in second_ids
        ):
            raise Phase3EBoundedRebuildRunnerV1Error(
                "retry/rebuild reused work from the first attempt"
            )
        attempts = (first, second)
        receipts = (first_receipt, second_receipt)
        terminal_results = (
            first_receipt.terminal_result,
            second_receipt.terminal_result,
        )
        attempt_ids = (first_ids, second_ids)
        attempt_work = (first_work, second_work)

    occurrence_sum = _derive_occurrence_sum(
        occurrence, attempt_work, rebuild_work, profile
    )
    try:
        closure = CampaignOccurrenceClosureV1.close(
            occurrence,
            policy,
            attempts,
            terminal_results,
            attempt_ids,
            occurrence_sum.bounded_rebuild_occurrence_work_sum_id,
            rebuild_events=(() if rebuild_event is None else (rebuild_event,)),
        )
    except ValueError as error:
        raise Phase3EBoundedRebuildRunnerV1Error(
            f"campaign occurrence closure failed: {error}"
        ) from error
    return BoundedRebuildOccurrenceRunV1(
        occurrence,
        policy,
        attempts,
        receipts,
        rebuild_receipt,
        rebuild_event,
        occurrence_sum,
        closure,
    )


__all__ = [
    "AttemptExecutionReceiptV1",
    "BOUNDED_REBUILD_RUNNER_BLOCKERS",
    "BOUNDED_REBUILD_RUNNER_STATUS",
    "BoundedRebuildOccurrenceRunV1",
    "BoundedRebuildOccurrenceWorkSumV1",
    "BoundedRebuildWorkComponentV1",
    "Phase3EBoundedRebuildRunnerV1Error",
    "RebuildExecutionReceiptV1",
    "RebuildInvocationV1",
    "RegisteredRebuildCallbackV1",
    "run_bounded_rebuild_retry_v1",
]
