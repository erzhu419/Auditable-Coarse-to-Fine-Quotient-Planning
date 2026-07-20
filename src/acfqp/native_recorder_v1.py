"""Native, explicit-zero Phase-3E work recording.

The recorder is intentionally small and synchronous.  It is the accounting
boundary used by the Contract-1.0 consumer runner: every required registry
leaf is created as an observed native zero when the recorder starts, and only
registered events may mutate it.  Closing a recorder materializes both the
native ``WorkVectorV1`` and the exact operational comparison projection.

This is not a sampler and it does not translate legacy summary counters.
Callers must record work at the operation that incurred it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acfqp.accounting_v1 import (
    AccountingV1Error,
    ComparisonProfileV1,
    ComparisonVectorV1,
    CounterRegistryV1,
    CounterRecordV1,
    LaneEnum,
    NativeZeroAttestationV1,
    ReconciliationProofV1,
    ReducerEnum,
    RouteKindEnum,
    WorkVectorV1,
    explicit_records_v1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualWorkScope,
    derive_actual_projection_v1,
    official_actual_projection_profile_v1,
    verify_actual_projection_v1,
)
from acfqp.phase3e_ids import parse_content_id


RECORDER_ID = "phase3e-native-operation-recorder-v1"


class NativeRecorderV1Error(ValueError):
    """A counter operation is unregistered, ambiguous, or occurs after seal."""


@dataclass(frozen=True, slots=True)
class RecordedWorkV1:
    """Replayable native work and its exact, non-scalar projection."""

    work_vector: WorkVectorV1
    native_zero_attestation: NativeZeroAttestationV1
    reconciliation_proof: ReconciliationProofV1
    comparison_vector: ComparisonVectorV1
    actual_projection_proof: ActualProjectionProofV1


class NativeCounterRecorderV1:
    """Mutable operation recorder with one irreversible ``seal`` boundary.

    Starting the recorder explicitly emits an observed zero for every required
    leaf.  This is different from treating a missing row as zero: the final
    vector contains a native ``CounterRecordV1`` (and recorder provenance) for
    every one of those observations.
    """

    def __init__(
        self,
        *,
        subject_id: str,
        route_kind: RouteKindEnum | str,
        work_scope: ActualWorkScope | str,
        registry: CounterRegistryV1 | None = None,
        comparison_profile: ComparisonProfileV1 | None = None,
        recorder_id: str = RECORDER_ID,
    ) -> None:
        try:
            self.registry = registry or official_counter_registry_v1()
            self.registry.validate_official_catalogue()
            self.comparison_profile = comparison_profile or (
                official_comparison_profile_v1(self.registry)
            )
            self.comparison_profile.validate(self.registry)
            self.subject_id = parse_content_id(subject_id)
            self.route_kind = RouteKindEnum(route_kind)
            self.work_scope = ActualWorkScope(work_scope)
        except (TypeError, ValueError) as error:
            raise NativeRecorderV1Error(str(error)) from error
        if type(recorder_id) is not str or not recorder_id:
            raise NativeRecorderV1Error("recorder_id must be nonempty")
        self.recorder_id = recorder_id
        allowed_scopes = {
            RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE: {
                ActualWorkScope.COMMON_PREFIX
            },
            RouteKindEnum.LOCAL_ATTEMPT: {
                ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
                ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
            },
            RouteKindEnum.DIRECT_FALLBACK: {
                ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
                ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
            },
            RouteKindEnum.REBUILD: {ActualWorkScope.REBUILD_EXECUTION},
        }[self.route_kind]
        if self.work_scope not in allowed_scopes:
            raise NativeRecorderV1Error(
                f"{self.route_kind.value} cannot be recorded as "
                f"{self.work_scope.value}"
            )
        # These are explicit start-of-lane observations, not absent values.
        self._values = {path: 0 for path in self.registry.required_paths}
        self._sealed = False
        self._sealed_work: RecordedWorkV1 | None = None

    @property
    def values(self) -> dict[str, int]:
        return dict(self._values)

    @property
    def sealed_work(self) -> RecordedWorkV1 | None:
        """Return the already materialized bundle without reopening the ledger."""

        return self._sealed_work

    def _leaf(self, path: str):
        if self._sealed:
            raise NativeRecorderV1Error("counter recorder is already sealed")
        try:
            leaf = self.registry.by_path[path]
        except KeyError as error:
            raise NativeRecorderV1Error(
                f"unknown native counter path {path!r}"
            ) from error
        if leaf.lane is not LaneEnum.OPERATIONAL and not leaf.required:
            raise NativeRecorderV1Error(
                f"non-required {leaf.lane.value} counter {path!r} cannot enter "
                "the operational WorkVector"
            )
        if self.work_scope is ActualWorkScope.MARGINAL_ROUTE_VERIFICATION:
            forbidden = ("local.", "fallback.", "rebuild.")
        else:
            forbidden = {
                RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE: (
                    "local.", "fallback.", "rebuild."
                ),
                RouteKindEnum.LOCAL_ATTEMPT: (
                    "common.", "fallback.", "rebuild."
                ),
                RouteKindEnum.DIRECT_FALLBACK: (
                    "common.", "local.", "rebuild."
                ),
                RouteKindEnum.REBUILD: (
                    "common.", "local.", "fallback.", "control."
                ),
            }[self.route_kind]
        if any(path.startswith(prefix) for prefix in forbidden):
            raise NativeRecorderV1Error(
                f"counter {path!r} belongs outside the "
                f"{self.work_scope.value} lane"
            )
        return leaf

    @staticmethod
    def _amount(value: Any, field: str) -> int:
        if type(value) is not int or value < 0:
            raise NativeRecorderV1Error(
                f"{field} must be a nonnegative exact integer"
            )
        return value

    def add(self, path: str, amount: int = 1) -> None:
        """Record additive native work at the operation that incurred it."""

        leaf = self._leaf(path)
        if leaf.reducer is not ReducerEnum.SUM:
            raise NativeRecorderV1Error(
                f"{path!r} is a peak counter; use observe_peak"
            )
        self._values[path] += self._amount(amount, path)

    def observe_peak(self, path: str, value: int) -> None:
        """Record a native capacity observation using the registered max reducer."""

        leaf = self._leaf(path)
        if leaf.reducer is not ReducerEnum.MAX:
            raise NativeRecorderV1Error(
                f"{path!r} is additive; use add"
            )
        self._values[path] = max(
            self._values[path], self._amount(value, path)
        )

    def record_route_completion(self, *, success: bool) -> None:
        if type(success) is not bool:
            raise NativeRecorderV1Error("route success must be boolean")
        self.add("route.attempts")
        self.add("route.successes" if success else "route.failures")

    def record_solver_completion(self, *, success: bool) -> None:
        if type(success) is not bool:
            raise NativeRecorderV1Error("solver success must be boolean")
        self.add("solver.attempts")
        self.add("solver.successes" if success else "solver.failures")

    def record_process_completion(self, *, success: bool) -> None:
        if type(success) is not bool:
            raise NativeRecorderV1Error("process success must be boolean")
        self.add("process.launches")
        self.add(
            "process.exit_successes" if success else "process.exit_failures"
        )

    def charge_verified_record(self, record: Any) -> None:
        """Charge one authoritative operational verification record exactly.

        Semantic handlers return a ``CounterRecordV1``.  Re-reading its value
        is safe only after registry metadata replay; arbitrary dictionaries are
        deliberately not accepted here.
        """

        from acfqp.accounting_v1 import CounterRecordV1

        if not isinstance(record, CounterRecordV1):
            raise NativeRecorderV1Error(
                "verification work must be an exact CounterRecordV1"
            )
        leaf = self._leaf(record.path)
        try:
            if record.counter_registry_id != self.registry.registry_id:
                raise AccountingV1Error("verification record registry mismatch")
            record.verify_against(leaf)
        except AccountingV1Error as error:
            raise NativeRecorderV1Error(str(error)) from error
        if record.lane is not LaneEnum.OPERATIONAL:
            raise NativeRecorderV1Error(
                "evaluation verification cannot enter operational work"
            )
        if leaf.reducer is ReducerEnum.SUM:
            self.add(record.path, record.value)
        else:
            self.observe_peak(record.path, record.value)

    def _materialize(self, values: dict[str, int]) -> RecordedWorkV1:
        """Materialize one exact snapshot using this recorder's provenance."""

        try:
            records = explicit_records_v1(
                self.registry,
                values,
                recorder_id=self.recorder_id,
            )
            vector = self.registry.materialize(
                subject_id=self.subject_id,
                route_kind=self.route_kind,
                records=records,
            )
            actual_profile = official_actual_projection_profile_v1(
                self.registry, self.comparison_profile
            )
            comparison, projection = derive_actual_projection_v1(
                vector,
                self.registry,
                self.comparison_profile,
                actual_profile,
                source_lane=LaneEnum.OPERATIONAL,
                work_scope=self.work_scope,
            )
            return RecordedWorkV1(
                vector,
                NativeZeroAttestationV1.derive(vector, self.registry),
                ReconciliationProofV1.derive(vector, self.registry),
                comparison,
                projection,
            )
        except (AccountingV1Error, ValueError) as error:
            raise NativeRecorderV1Error(str(error)) from error

    def seal(self) -> RecordedWorkV1:
        """Close the recorder and derive all accounting artifacts exactly once."""

        if self._sealed:
            raise NativeRecorderV1Error("counter recorder is already sealed")
        result = self._materialize(dict(self._values))
        self._sealed = True
        self._sealed_work = result
        return result

    def seal_route_failure(self) -> RecordedWorkV1:
        """Seal a single selected-route attempt as failed, idempotently.

        Route closure leaves are derived-only bookkeeping.  A callback may
        record a provisional successful completion and then fail a runner
        protocol check.  Rewriting exactly these three leaves to ``1/0/1``
        records the final attempt outcome without adding a second attempt or
        changing any native operation counter.  A previously sealed snapshot
        is therefore safe to close as failed as well.
        """

        if self.work_scope is not ActualWorkScope.MARGINAL_ROUTE_EXECUTION:
            raise NativeRecorderV1Error(
                "only marginal route execution work has a route-failure closure"
            )
        values = dict(self._values)
        attempts = values["route.attempts"]
        successes = values["route.successes"]
        failures = values["route.failures"]
        if (attempts, successes, failures) not in {
            (0, 0, 0),
            (1, 1, 0),
            (1, 0, 1),
        }:
            raise NativeRecorderV1Error(
                "cannot normalize a multi-attempt or malformed route closure"
            )
        values.update(
            {
                "route.attempts": 1,
                "route.successes": 0,
                "route.failures": 1,
            }
        )
        result = self._materialize(values)
        self._values.update(values)
        self._sealed = True
        self._sealed_work = result
        return result

    def seal_partial(self) -> RecordedWorkV1:
        """Seal the current exact values, returning an existing seal if present.

        This is used only on fail-closed paths to retain verification work
        already incurred before a later exception.  It never adds counters.
        """

        if self._sealed_work is not None:
            return self._sealed_work
        result = self._materialize(dict(self._values))
        self._sealed = True
        self._sealed_work = result
        return result


def derive_failed_recorded_work_v1(
    recorded: RecordedWorkV1,
    *,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> RecordedWorkV1:
    """Normalize an executor-owned route bundle to one failed attempt.

    Every operation record and its recorder provenance is retained byte for
    byte.  Only the three derived route-closure records are replaced.  This is
    intentionally not an aggregation step and cannot double-charge an
    attempt.
    """

    if not isinstance(recorded, RecordedWorkV1):
        raise NativeRecorderV1Error(
            "failed executor-owned work must be an exact RecordedWorkV1"
        )
    registry = registry or official_counter_registry_v1()
    profile = comparison_profile or official_comparison_profile_v1(registry)
    verify_recorded_work_v1(
        recorded,
        expected_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
    )
    values = recorded.work_vector.values
    closure = (
        values["route.attempts"],
        values["route.successes"],
        values["route.failures"],
    )
    if closure not in {(0, 0, 0), (1, 1, 0), (1, 0, 1)}:
        raise NativeRecorderV1Error(
            "cannot normalize a multi-attempt or malformed owned route closure"
        )
    replacements = {
        "route.attempts": 1,
        "route.successes": 0,
        "route.failures": 1,
    }
    rows = tuple(
        CounterRecordV1(
            row.counter_registry_id,
            row.path,
            replacements.get(row.path, row.value),
            row.observed,
            row.recorder_id,
            row.semantics_id,
            row.owner,
            row.unit,
            row.lane,
            row.scope,
            row.reducer,
        )
        for row in recorded.work_vector.records
    )
    try:
        vector = registry.materialize(
            subject_id=recorded.work_vector.subject_id,
            route_kind=recorded.work_vector.route_kind,
            records=rows,
        )
    except AccountingV1Error as error:
        raise NativeRecorderV1Error(str(error)) from error
    return derive_recorded_work_v1(
        vector,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
        registry=registry,
        comparison_profile=profile,
    )


def derive_recorded_work_v1(
    vector: WorkVectorV1,
    *,
    work_scope: ActualWorkScope | str,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> RecordedWorkV1:
    """Derive proofs from an executor's already exact native WorkVector.

    This adapter never fills absent rows and never translates legacy summary
    counters.  It is intended for executors such as the capped ground fallback
    that own their native ledger internally.
    """

    registry = registry or official_counter_registry_v1()
    profile = comparison_profile or official_comparison_profile_v1(registry)
    try:
        registry.validate_vector(vector)
        actual_profile = official_actual_projection_profile_v1(registry, profile)
        comparison, projection = derive_actual_projection_v1(
            vector,
            registry,
            profile,
            actual_profile,
            source_lane=LaneEnum.OPERATIONAL,
            work_scope=work_scope,
        )
        return RecordedWorkV1(
            vector,
            NativeZeroAttestationV1.derive(vector, registry),
            ReconciliationProofV1.derive(vector, registry),
            comparison,
            projection,
        )
    except (AccountingV1Error, ValueError) as error:
        raise NativeRecorderV1Error(str(error)) from error


def verify_recorded_work_v1(
    recorded: RecordedWorkV1,
    *,
    expected_scope: ActualWorkScope | str,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> RecordedWorkV1:
    """Replay every component of a ``RecordedWorkV1`` runtime bundle."""

    if not isinstance(recorded, RecordedWorkV1):
        raise NativeRecorderV1Error("recorded work has the wrong runtime type")
    registry = registry or official_counter_registry_v1()
    profile = comparison_profile or official_comparison_profile_v1(registry)
    try:
        scope = ActualWorkScope(expected_scope)
        actual_profile = official_actual_projection_profile_v1(registry, profile)
        verify_actual_projection_v1(
            recorded.actual_projection_proof,
            recorded.work_vector,
            recorded.comparison_vector,
            registry,
            profile,
            actual_profile,
        )
        if recorded.actual_projection_proof.work_scope is not scope:
            raise AccountingV1Error("recorded work-scope mismatch")
        if recorded.native_zero_attestation != NativeZeroAttestationV1.derive(
            recorded.work_vector, registry
        ):
            raise AccountingV1Error("native-zero attestation does not replay")
        if recorded.reconciliation_proof != ReconciliationProofV1.derive(
            recorded.work_vector, registry
        ):
            raise AccountingV1Error("reconciliation proof does not replay")
    except (AccountingV1Error, TypeError, ValueError) as error:
        raise NativeRecorderV1Error(str(error)) from error
    return recorded


__all__ = [
    "derive_failed_recorded_work_v1",
    "NativeCounterRecorderV1",
    "NativeRecorderV1Error",
    "RECORDER_ID",
    "RecordedWorkV1",
    "derive_recorded_work_v1",
    "verify_recorded_work_v1",
]
