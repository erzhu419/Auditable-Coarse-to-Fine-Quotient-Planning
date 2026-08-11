"""Owner-bound five-stage accounting for one query-local continuation.

The lifecycle records two incremental acquisitions, two checkpoint
replannings, and the exact direct-ground fallback.  Every completed stage is
materialized as V6 CounterRecordV3 -> WorkVectorV3 -> ComparisonVectorV3 plus
its projection proof.  These vectors deliberately retain zero placeholders
for the nine occurrence-wide shared resources; a later trusted supervisor
must replace those placeholders before issuing an occurrence WorkVector.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import importlib
import sys
import threading
from typing import Any, Iterator, Mapping, Sequence

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_live_v3 as live_v3
from acfqp import construction_accounting_owned_runtime_v1 as hook_runtime_v1
from acfqp import construction_accounting_registry_v3 as registry_v3
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_query_bound_accounting_manifest_v1 as manifest_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_STAGE_RUNTIME_RESULT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.95"
PROFILE_KEY = "construction_k7_query_bound_stage_accounting_v1"
RECORDER_ID = "construction-k7-query-bound-stage-accounting-v1"
RESULT_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_STAGE_RUNTIME_RESULT_V1_DOMAIN
LOCAL_DOMAINS = frozenset({RESULT_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("query-bound stage-runtime domain is not central")

_S = registry_v6.ConstructionStageKindV6
CANONICAL_QUERY_BOUND_STAGE_PLAN_V1 = (
    _S.OPEN_INCREMENTAL_ACQUISITION,
    _S.OPEN_CHECKPOINT_REPLANNING,
    _S.OPEN_INCREMENTAL_ACQUISITION,
    _S.OPEN_CHECKPOINT_REPLANNING,
    _S.DIRECT_FALLBACK,
)
EXPECTED_STAGE_COUNT = 5
EXPECTED_STAGE_LOCAL_RECORD_COUNT = (
    EXPECTED_STAGE_COUNT * registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
)
SHARED_RESOURCE_PATHS = (
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
_PROCESS_LOCK = threading.Lock()


class ConstructionK7QueryBoundStageAccountingV1Error(RuntimeError):
    """The owner, stage order, operation, or authority failed closed."""


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundStageAccountingV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _stage(value: Any) -> registry_v6.ConstructionStageKindV6:
    try:
        return registry_v6.ConstructionStageKindV6(
            getattr(value, "value", value)
        )
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundStageAccountingV1Error(
            f"unknown query-bound accounting stage {value!r}"
        ) from error


def _live_stage(
    value: registry_v6.ConstructionStageKindV6,
) -> registry_v3.ConstructionStageKindV3:
    return registry_v3.ConstructionStageKindV3(value.value)


def _owner_binding(module_name: str, symbol: str) -> tuple[Any, Any]:
    try:
        module = importlib.import_module(module_name)
        selected: Any = module
        for component in symbol.split("."):
            selected = getattr(selected, component)
    except (AttributeError, ImportError) as error:
        raise ConstructionK7QueryBoundStageAccountingV1Error(
            f"cannot bind query operation owner {module_name}.{symbol}"
        ) from error
    function = getattr(selected, "__func__", selected)
    code = getattr(function, "__code__", None)
    if code is None:
        raise ConstructionK7QueryBoundStageAccountingV1Error(
            f"query operation owner {module_name}.{symbol} has no code identity"
        )
    return module.__dict__, code


@dataclass(frozen=True, slots=True)
class QueryBoundStageAccountingResultV1:
    occurrence_id: str
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    boundary_manifest_id: str
    lifecycle_id: str
    recorded_stages: tuple[live_v3.RecordedStageWorkV3, ...]
    stage_output_bindings: tuple[tuple[tuple[str, str], ...], ...]

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "query occurrence"),
            (self.counter_registry_id, "query registry"),
            (self.stage_profile_id, "query stage profile"),
            (self.comparison_profile_id, "query comparison profile"),
            (self.actual_projection_profile_id, "query projection profile"),
            (self.boundary_manifest_id, "query boundary manifest"),
            (self.lifecycle_id, "query accounting lifecycle"),
        ):
            _cid(value, label)
        if (
            type(self.recorded_stages) is not tuple
            or len(self.recorded_stages) != EXPECTED_STAGE_COUNT
            or tuple(_stage(row.stage_start.stage_kind) for row in self.recorded_stages)
            != CANONICAL_QUERY_BOUND_STAGE_PLAN_V1
            or type(self.stage_output_bindings) is not tuple
            or len(self.stage_output_bindings) != EXPECTED_STAGE_COUNT
            or any(
                row.work_vector.values[path] != 0
                for row in self.recorded_stages
                for path in SHARED_RESOURCE_PATHS
            )
        ):
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound stage result changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_stage_runtime_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "boundary_manifest_id": self.boundary_manifest_id,
            "lifecycle_id": self.lifecycle_id,
            "stage_plan": [row.value for row in CANONICAL_QUERY_BOUND_STAGE_PLAN_V1],
            "stage_work_vector_ids": [
                row.work_vector.work_vector_id for row in self.recorded_stages
            ],
            "stage_comparison_vector_ids": [
                row.comparison_vector.comparison_vector_id
                for row in self.recorded_stages
            ],
            "stage_actual_projection_proof_ids": [
                row.actual_projection_proof.actual_projection_proof_id
                for row in self.recorded_stages
            ],
            "stage_output_bindings": [
                [
                    {"role": role, "artifact_id": artifact_id}
                    for role, artifact_id in bindings
                ]
                for bindings in self.stage_output_bindings
            ],
            "stage_local_counter_record_count": sum(
                len(row.work_vector.records) for row in self.recorded_stages
            ),
            "expected_stage_local_counter_record_count": (
                EXPECTED_STAGE_LOCAL_RECORD_COUNT
            ),
            "source_hook_calls_aggregated_by_stage_and_operation_site": True,
            "stage_local_counter_chain_present": True,
            "nine_shared_resource_paths_are_zero_placeholders": True,
            "shared_resource_receipts_present": False,
            "all_reachable_operation_sites_complete": False,
            "occurrence_counter_records_issued": False,
            "occurrence_work_vector_issued": False,
            "occurrence_comparison_vector_issued": False,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        return content_id(RESULT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_bound_stage_runtime_result_id": self.result_id}


class QueryBoundStageAccountingSessionV1:
    """One thread-owned exact five-stage query continuation."""

    def __init__(
        self,
        *,
        occurrence_id: str,
        recorder_id: str,
        counter_registry: registry_v6.CounterRegistryV6,
        stage_profile: Any,
        comparison_profile: Any,
        actual_projection_profile: Any,
        boundary_manifest: manifest_v1.QueryBoundAccountingOperationManifestV1,
    ) -> None:
        self._owner_thread = threading.get_ident()
        self._occurrence_id = _cid(occurrence_id, "query occurrence")
        self._registry = counter_registry
        self._stage_profile = stage_profile
        self._comparison_profile = comparison_profile
        self._actual_profile = actual_projection_profile
        self._boundary_manifest = boundary_manifest
        self._validate_authorities()
        self._lifecycle = live_v3.open_construction_accounting_lifecycle_v3(
            subject_id=self._occurrence_id,
            recorder_id=recorder_id,
            stage_plan=tuple(_live_stage(row) for row in CANONICAL_QUERY_BOUND_STAGE_PLAN_V1),
            registry=counter_registry,
            stage_profile=stage_profile,
            comparison_profile=comparison_profile,
            actual_projection_profile=actual_projection_profile,
        )
        self._active: live_v3.ConstructionActiveStageV3 | None = None
        self._pending_counts: dict[str, int] = {}
        self._outputs: list[tuple[tuple[str, str], ...]] = []
        self._terminal = False
        self._result: QueryBoundStageAccountingResultV1 | None = None
        self._owner_bindings = {
            row.boundary_key: _owner_binding(
                row.operation_source_module,
                row.operation_source_symbol,
            )
            for row in boundary_manifest.boundaries
        }
        self._by_stage_dispatch = {
            (row.stage, row.dispatch_key): row
            for row in boundary_manifest.boundaries
        }
        if len(self._by_stage_dispatch) != len(boundary_manifest.boundaries):
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound operation dispatch inventory is ambiguous"
            )

    def _check_thread(self) -> None:
        if threading.get_ident() != self._owner_thread:
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound accounting session used from another thread"
            )

    def _validate_authorities(self) -> None:
        try:
            self._registry.validate_official_catalogue()
            self._stage_profile.validate(self._registry)
            self._comparison_profile.validate(self._registry)
            self._actual_profile.validate(self._registry, self._comparison_profile)
            self._boundary_manifest.validate_official()
        except Exception as error:
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound accounting authority changed"
            ) from error
        if (
            self._boundary_manifest.counter_registry_id != self._registry.registry_id
            or self._boundary_manifest.stage_profile_id
            != self._stage_profile.stage_profile_id
            or self._boundary_manifest.comparison_profile_id
            != self._comparison_profile.comparison_profile_id
            or self._boundary_manifest.actual_projection_profile_id
            != self._actual_profile.actual_projection_profile_id
        ):
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound accounting authority identities crossed"
            )

    @property
    def is_terminal(self) -> bool:
        return self._terminal

    @property
    def active_stage(self) -> registry_v6.ConstructionStageKindV6 | None:
        return None if self._active is None else _stage(self._active.start.stage_kind)

    def enter_stage(self, stage: Any) -> None:
        self._check_thread()
        if self._terminal or self._active is not None:
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound stage entry is not legal"
            )
        index = len(self._lifecycle.recorded_stages)
        selected = _stage(stage)
        if (
            index >= EXPECTED_STAGE_COUNT
            or selected is not CANONICAL_QUERY_BOUND_STAGE_PLAN_V1[index]
        ):
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound stage order changed"
            )
        self._active = self._lifecycle.begin_stage(_live_stage(selected))
        self._pending_counts = {}

    def emit_operation(
        self,
        dispatch_key: Any,
        amount: Any = 1,
        *,
        caller_module: Any,
        caller_globals: Any,
        caller_code: Any,
    ) -> None:
        self._check_thread()
        if self._terminal or self._active is None:
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound operation occurred outside an active stage"
            )
        if type(dispatch_key) is not str or type(amount) is not int or amount != 1:
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound operation dispatch or amount changed"
            )
        boundary = self._by_stage_dispatch.get((self.active_stage, dispatch_key))
        if boundary is None:
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound operation dispatch is absent or belongs to another stage"
            )
        expected_globals, expected_code = self._owner_bindings[boundary.boundary_key]
        if (
            caller_module != boundary.operation_source_module
            or caller_globals is not expected_globals
            or caller_code is not expected_code
        ):
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound operation caller differs from its registered owner"
            )
        leaf = self._registry.by_path[boundary.target_path]
        if boundary.reducer is not ReducerEnum.SUM or leaf.reducer is not ReducerEnum.SUM:
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound source hook may emit only SUM primitives"
            )
        self._pending_counts[boundary.boundary_key] = (
            self._pending_counts.get(boundary.boundary_key, 0) + 1
        )

    def _flush(self) -> None:
        if self._active is None:
            if self._pending_counts:
                raise ConstructionK7QueryBoundStageAccountingV1Error(
                    "query-bound operation totals lack an active stage"
                )
            return
        for boundary_key in sorted(self._pending_counts):
            boundary = self._boundary_manifest.by_key[boundary_key]
            self._active.add(
                boundary.target_path,
                self._pending_counts[boundary_key],
                operation_site_id=boundary.boundary_id,
            )
        self._pending_counts = {}

    def exit_stage(
        self,
        stage: Any | None = None,
        *,
        output_bindings: Any = (),
    ) -> None:
        self._check_thread()
        if self._terminal or self._active is None:
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound stage exit is not legal"
            )
        if stage is not None and _stage(stage) is not self.active_stage:
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound stage exit changed stage"
            )
        try:
            bindings = tuple(
                sorted(
                    (str(role), _cid(artifact_id, f"stage output {role}"))
                    for role, artifact_id in output_bindings
                )
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound stage outputs are malformed"
            ) from error
        if len({role for role, _value in bindings}) != len(bindings):
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound stage output roles repeat"
            )
        self._flush()
        self._active.complete(
            output_artifact_ids=tuple(value for _role, value in bindings)
        )
        self._outputs.append(bindings)
        self._active = None

    def complete_occurrence(self) -> QueryBoundStageAccountingResultV1:
        self._check_thread()
        if self._result is not None:
            return self._result
        if self._terminal or self._active is not None:
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound stage lifecycle cannot complete"
            )
        recorded = self._lifecycle.finish()
        if len(recorded) != EXPECTED_STAGE_COUNT:
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "query-bound stage lifecycle is incomplete"
            )
        result = QueryBoundStageAccountingResultV1(
            self._occurrence_id,
            self._registry.registry_id,
            self._stage_profile.stage_profile_id,
            self._comparison_profile.comparison_profile_id,
            self._actual_profile.actual_projection_profile_id,
            self._boundary_manifest.manifest_id,
            self._lifecycle.lifecycle_id,
            recorded,
            tuple(self._outputs),
        )
        self._result = result
        self._terminal = True
        return result

    def abort_occurrence(self, reason: str) -> None:
        self._check_thread()
        if self._terminal:
            return
        if type(reason) is not str or not reason:
            reason = "UNSPECIFIED_QUERY_BOUND_ACCOUNTING_FAILURE"
        if self._active is not None:
            failure_id = content_id(
                RESULT_DOMAIN,
                {
                    "schema": "acfqp.construction_k7_query_bound_stage_abort.v1",
                    "reason": reason,
                    "occurrence_id": self._occurrence_id,
                    "stage": self.active_stage.value,
                },
            )
            self._flush()
            self._active.abort(failure_evidence_ids=(failure_id,))
            self._active = None
        self._terminal = True


@contextmanager
def activate_query_bound_stage_accounting_v1(
    *,
    occurrence_id: str,
    recorder_id: str = RECORDER_ID,
) -> Iterator[QueryBoundStageAccountingSessionV1]:
    if not _PROCESS_LOCK.acquire(blocking=False):
        raise ConstructionK7QueryBoundStageAccountingV1Error(
            "another query-bound accounting runtime is active"
        )
    token = None
    session = None
    try:
        if hook_runtime_v1._ACTIVE_RUNTIME.get() is not None:  # noqa: SLF001
            raise ConstructionK7QueryBoundStageAccountingV1Error(
                "another owned accounting runtime is active"
            )
        registry = registry_v6.official_counter_registry_v6()
        stage = registry_v6.official_stage_profile_v6(registry)
        comparison = registry_v6.official_comparison_profile_v6(registry)
        actual = registry_v6.official_actual_projection_profile_v6(registry, comparison)
        manifest = manifest_v1.official_query_bound_accounting_operation_manifest_v1()
        session = QueryBoundStageAccountingSessionV1(
            occurrence_id=occurrence_id,
            recorder_id=recorder_id,
            counter_registry=registry,
            stage_profile=stage,
            comparison_profile=comparison,
            actual_projection_profile=actual,
            boundary_manifest=manifest,
        )
        token = hook_runtime_v1._ACTIVE_RUNTIME.set(session)  # noqa: SLF001
        try:
            yield session
        except BaseException as error:
            session.abort_occurrence(type(error).__name__)
            raise
        else:
            if not session.is_terminal:
                session.abort_occurrence("INCOMPLETE_QUERY_BOUND_ACCOUNTING_SCOPE")
                raise ConstructionK7QueryBoundStageAccountingV1Error(
                    "query-bound accounting scope exited before completion"
                )
    finally:
        if token is not None:
            hook_runtime_v1._ACTIVE_RUNTIME.reset(token)  # noqa: SLF001
        _PROCESS_LOCK.release()


def query_bound_stage_accounting_active_v1() -> bool:
    return type(hook_runtime_v1._ACTIVE_RUNTIME.get()) is QueryBoundStageAccountingSessionV1  # noqa: SLF001


__all__ = (
    "CANONICAL_QUERY_BOUND_STAGE_PLAN_V1",
    "ConstructionK7QueryBoundStageAccountingV1Error",
    "EXPECTED_STAGE_COUNT",
    "EXPECTED_STAGE_LOCAL_RECORD_COUNT",
    "LOCAL_DOMAINS",
    "QueryBoundStageAccountingResultV1",
    "QueryBoundStageAccountingSessionV1",
    "SHARED_RESOURCE_PATHS",
    "activate_query_bound_stage_accounting_v1",
    "query_bound_stage_accounting_active_v1",
)
