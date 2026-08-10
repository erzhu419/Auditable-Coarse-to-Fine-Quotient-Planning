"""Owner-bound accounting runtime for the causal-promotion occurrence.

The V1 runtime is intentionally fixed to the historical five-stage root-cap
negative control.  This additive successor keeps the already-installed source
hooks, but binds them to the V6 registry, the causal-promotion V4 operation
manifest, and a preregistered sequence containing the two repeatable open
stage kinds.

Each completed stage is materialized through ``construction_accounting_live_v3``
as exact CounterRecords, WorkVector, ComparisonVector, and projection proof.
Those are stage-local construction artifacts only; this module does not yet
aggregate them into the single occurrence WorkVector required by K7.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import importlib
import sys
import threading
from typing import Any, Iterator, Mapping, Sequence

from acfqp.accounting_v1 import ReducerEnum
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import construction_accounting_live_v3 as live_v3
from acfqp import construction_accounting_owned_runtime_v1 as hook_runtime_v1
from acfqp import construction_accounting_registry_v3 as registry_v3
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import v075_k7_causal_promotion_operation_boundary_manifest_v4 as manifest_v4


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.77"
PROFILE_KEY = "construction_accounting_owned_runtime_v2"
RECORDER_ID = "v075-k7-causal-promotion-owned-runtime-v2"
RUNTIME_RESULT_DOMAIN = "acfqp:v075-k7-causal-promotion-owned-runtime-result:v2"

_S = registry_v6.ConstructionStageKindV6
CANONICAL_CAUSAL_PROMOTION_STAGE_PLAN_V2 = (
    _S.PREOPEN_COMMON_PREFIX,
    _S.INITIAL_ACQUISITION,
    _S.INITIAL_MODEL_BUILD,
    _S.FAILED_ABSTRACT_PREFIX,
    _S.OPEN_INCREMENTAL_ACQUISITION,
    _S.OPEN_CHECKPOINT_REPLANNING,
    _S.OPEN_CHECKPOINT_REPLANNING,
    _S.OPEN_INCREMENTAL_ACQUISITION,
    _S.OPEN_CHECKPOINT_REPLANNING,
    _S.OPEN_INCREMENTAL_ACQUISITION,
    _S.OPEN_CHECKPOINT_REPLANNING,
    _S.CLOSED_RECONCILIATION_AND_TERMINALIZATION,
)
EXPECTED_STAGE_INSTANCE_COUNT = 12
EXPECTED_OPEN_INCREMENTAL_INSTANCE_COUNT = 3
EXPECTED_OPEN_CHECKPOINT_INSTANCE_COUNT = 4
_PROCESS_LOCK = threading.Lock()


class OwnedConstructionAccountingRuntimeV2Error(RuntimeError):
    """The owner, stage, operation, or lifecycle binding failed closed."""


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise OwnedConstructionAccountingRuntimeV2Error(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _stage(value: Any) -> registry_v6.ConstructionStageKindV6:
    try:
        return registry_v6.ConstructionStageKindV6(
            getattr(value, "value", value)
        )
    except (TypeError, ValueError) as error:
        raise OwnedConstructionAccountingRuntimeV2Error(
            f"unknown V6 construction stage {value!r}"
        ) from error


def _live_stage(
    value: registry_v6.ConstructionStageKindV6,
) -> registry_v3.ConstructionStageKindV3:
    return registry_v3.ConstructionStageKindV3(value.value)


def _emittable(boundary: Any) -> bool:
    value = getattr(getattr(boundary, "classification", None), "value", "")
    return value.endswith("SCHEMA_ONLY") and "NATIVE_ZERO" not in value


def _owner_binding(module_name: str, symbol: str) -> tuple[Any, Any]:
    try:
        module = importlib.import_module(module_name)
        selected: Any = module
        for component in symbol.split("."):
            selected = getattr(selected, component)
    except (AttributeError, ImportError) as error:
        raise OwnedConstructionAccountingRuntimeV2Error(
            f"cannot bind owner {module_name}.{symbol}"
        ) from error
    function = getattr(selected, "__func__", selected)
    code = getattr(function, "__code__", None)
    if code is None:
        raise OwnedConstructionAccountingRuntimeV2Error(
            f"owner {module_name}.{symbol} has no Python code identity"
        )
    return module.__dict__, code


@dataclass(frozen=True, slots=True)
class OwnedCausalPromotionAccountingResultV2:
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
            (self.occurrence_id, "owned runtime occurrence"),
            (self.counter_registry_id, "owned runtime registry"),
            (self.stage_profile_id, "owned runtime stage profile"),
            (self.comparison_profile_id, "owned runtime comparison profile"),
            (
                self.actual_projection_profile_id,
                "owned runtime actual projection profile",
            ),
            (self.boundary_manifest_id, "owned runtime boundary manifest"),
            (self.lifecycle_id, "owned runtime lifecycle"),
        ):
            _cid(value, label)
        if (
            type(self.recorded_stages) is not tuple
            or len(self.recorded_stages) != EXPECTED_STAGE_INSTANCE_COUNT
            or type(self.stage_output_bindings) is not tuple
            or len(self.stage_output_bindings) != len(self.recorded_stages)
            or tuple(
                _stage(row.stage_start.stage_kind)
                for row in self.recorded_stages
            )
            != CANONICAL_CAUSAL_PROMOTION_STAGE_PLAN_V2
        ):
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned causal-promotion stage result changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_causal_promotion_owned_runtime_result.v2",
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
            "stage_plan": [
                item.value for item in CANONICAL_CAUSAL_PROMOTION_STAGE_PLAN_V2
            ],
            "stage_work_vector_ids": [
                item.work_vector.work_vector_id for item in self.recorded_stages
            ],
            "stage_comparison_vector_ids": [
                item.comparison_vector.comparison_vector_id
                for item in self.recorded_stages
            ],
            "stage_actual_projection_proof_ids": [
                item.actual_projection_proof.actual_projection_proof_id
                for item in self.recorded_stages
            ],
            "stage_output_bindings": [
                [
                    {"role": role, "artifact_id": artifact_id}
                    for role, artifact_id in rows
                ]
                for rows in self.stage_output_bindings
            ],
            "stage_local_counter_record_count": sum(
                len(item.work_vector.records) for item in self.recorded_stages
            ),
            "source_hook_calls_aggregated_by_stage_and_operation_site": True,
            "aggregate_counts_are_exact_integers": True,
            "per_primitive_event_objects_required": False,
            "stage_local_vectors_only": True,
            "occurrence_work_vector_issued": False,
            "all_site_completeness_claimed": False,
            "shared_resource_fixed_point_complete": False,
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        return hashlib.sha256(
            RUNTIME_RESULT_DOMAIN.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(self._payload())
        ).hexdigest()

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "owned_runtime_result_id": self.result_id}


class OwnedConstructionAccountingSessionV2:
    """One thread-owned, exact 12-instance causal-promotion lifecycle."""

    def __init__(
        self,
        *,
        occurrence_id: str,
        recorder_id: str,
        counter_registry: registry_v6.CounterRegistryV6,
        stage_profile: Any,
        comparison_profile: Any,
        actual_projection_profile: Any,
        boundary_profile: (
            manifest_v4.K7CausalPromotionOperationBoundaryManifestV4
        ),
    ) -> None:
        self._owner_thread = threading.get_ident()
        self._occurrence_id = _cid(occurrence_id, "occurrence")
        self._registry = counter_registry
        self._stage_profile = stage_profile
        self._comparison_profile = comparison_profile
        self._actual_profile = actual_projection_profile
        self._boundary_profile = boundary_profile
        self._validate_authorities()
        plan = tuple(
            _live_stage(item)
            for item in CANONICAL_CAUSAL_PROMOTION_STAGE_PLAN_V2
        )
        self._lifecycle = live_v3.open_construction_accounting_lifecycle_v3(
            subject_id=self._occurrence_id,
            recorder_id=recorder_id,
            stage_plan=plan,
            registry=counter_registry,
            stage_profile=stage_profile,
            comparison_profile=comparison_profile,
            actual_projection_profile=actual_projection_profile,
        )
        self._active: live_v3.ConstructionActiveStageV3 | None = None
        self._pending_counts: dict[str, int] = {}
        self._outputs: list[tuple[tuple[str, str], ...]] = []
        self._terminal = False
        self._result: OwnedCausalPromotionAccountingResultV2 | None = None
        self._owner_bindings = {
            row.boundary_key: _owner_binding(
                row.operation_source_module, row.operation_source_symbol
            )
            for row in boundary_profile.boundaries
            if _emittable(row)
        }
        self._emittable_by_stage_dispatch = {
            (row.stage, row.dispatch_key): row
            for row in boundary_profile.boundaries
            if _emittable(row)
        }
        if len(self._emittable_by_stage_dispatch) != len(
            self._owner_bindings
        ):
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned operation stage/dispatch index is ambiguous"
            )

    def _check_thread(self) -> None:
        if threading.get_ident() != self._owner_thread:
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned causal-promotion runtime used from another thread"
            )

    def _validate_authorities(self) -> None:
        try:
            self._registry.validate_official_catalogue()
            self._stage_profile.validate(self._registry)
            self._comparison_profile.validate(self._registry)
            self._actual_profile.validate(
                self._registry, self._comparison_profile
            )
            self._boundary_profile.validate_official()
        except Exception as error:
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned causal-promotion accounting authorities changed"
            ) from error
        if (
            self._boundary_profile.counter_registry_id
            != self._registry.registry_id
            or self._boundary_profile.stage_profile_id
            != self._stage_profile.stage_profile_id
            or self._boundary_profile.comparison_profile_id
            != self._comparison_profile.comparison_profile_id
            or self._boundary_profile.actual_projection_profile_id
            != self._actual_profile.actual_projection_profile_id
        ):
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned causal-promotion authority identities crossed"
            )

    @property
    def is_terminal(self) -> bool:
        return self._terminal

    @property
    def active_stage(self) -> registry_v6.ConstructionStageKindV6 | None:
        return (
            None
            if self._active is None
            else _stage(self._active.start.stage_kind)
        )

    def enter_stage(self, stage: Any) -> None:
        self._check_thread()
        if self._terminal or self._active is not None:
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned causal-promotion stage entry is not legal"
            )
        index = len(self._lifecycle.recorded_stages)
        selected = _stage(stage)
        if (
            index >= len(CANONICAL_CAUSAL_PROMOTION_STAGE_PLAN_V2)
            or selected is not CANONICAL_CAUSAL_PROMOTION_STAGE_PLAN_V2[index]
        ):
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned causal-promotion stage order changed"
            )
        self._active = self._lifecycle.begin_stage(_live_stage(selected))
        self._pending_counts = {}

    def _flush_pending_counts(self) -> None:
        if self._active is None:
            if self._pending_counts:
                raise OwnedConstructionAccountingRuntimeV2Error(
                    "owned operation totals exist without an active stage"
                )
            return
        for boundary_key in sorted(self._pending_counts):
            amount = self._pending_counts[boundary_key]
            if amount <= 0:
                raise OwnedConstructionAccountingRuntimeV2Error(
                    "owned operation aggregate is not positive"
                )
            boundary = self._boundary_profile.by_key[boundary_key]
            self._active.add(
                boundary.target_path,
                amount,
                operation_site_id=boundary.boundary_id,
            )
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
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned operation occurred outside an active stage"
            )
        if type(dispatch_key) is not str or type(amount) is not int or amount != 1:
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned operation dispatch or primitive amount changed"
            )
        current = self.active_stage
        boundary = self._emittable_by_stage_dispatch.get(
            (current, dispatch_key)
        )
        if boundary is None:
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned operation dispatch is absent or ambiguous"
            )
        expected_globals, expected_code = self._owner_bindings[
            boundary.boundary_key
        ]
        if (
            caller_module != boundary.operation_source_module
            or caller_globals is not expected_globals
            or caller_code is not expected_code
        ):
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned operation caller differs from its registered owner"
            )
        leaf = self._registry.by_path[boundary.target_path]
        if (
            boundary.reducer is not ReducerEnum.SUM
            or leaf.reducer is not ReducerEnum.SUM
        ):
            raise OwnedConstructionAccountingRuntimeV2Error(
                "source hooks may emit only registered SUM primitives"
            )
        self._pending_counts[boundary.boundary_key] = (
            self._pending_counts.get(boundary.boundary_key, 0) + 1
        )

    def exit_stage(
        self,
        stage: Any | None = None,
        *,
        output_bindings: Any = (),
    ) -> None:
        self._check_thread()
        if self._terminal or self._active is None:
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned causal-promotion stage exit is not legal"
            )
        if stage is not None and _stage(stage) is not self.active_stage:
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned causal-promotion stage exit changed stage"
            )
        try:
            bindings = tuple(
                sorted(
                    (str(role), _cid(artifact_id, f"stage output {role}"))
                    for role, artifact_id in output_bindings
                )
            )
        except (TypeError, ValueError) as error:
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned stage output bindings are malformed"
            ) from error
        if len({role for role, _value in bindings}) != len(bindings):
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned stage output roles repeat"
            )
        self._flush_pending_counts()
        self._active.complete(
            output_artifact_ids=tuple(value for _role, value in bindings)
        )
        self._outputs.append(bindings)
        self._active = None

    def complete_occurrence(self) -> OwnedCausalPromotionAccountingResultV2:
        self._check_thread()
        if self._result is not None:
            return self._result
        if self._terminal or self._active is not None:
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned causal-promotion occurrence cannot complete"
            )
        recorded = self._lifecycle.finish()
        if len(recorded) != EXPECTED_STAGE_INSTANCE_COUNT:
            raise OwnedConstructionAccountingRuntimeV2Error(
                "owned causal-promotion lifecycle is incomplete"
            )
        result = OwnedCausalPromotionAccountingResultV2(
            self._occurrence_id,
            self._registry.registry_id,
            self._stage_profile.stage_profile_id,
            self._comparison_profile.comparison_profile_id,
            self._actual_profile.actual_projection_profile_id,
            self._boundary_profile.manifest_id,
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
            reason = "UNSPECIFIED_CAUSAL_PROMOTION_RUNTIME_FAILURE"
        if self._active is not None:
            failure_id = hashlib.sha256(
                b"acfqp:causal-promotion-owned-runtime-failure:v2\x00"
                + reason.encode("utf-8", errors="replace")
            ).hexdigest()
            self._flush_pending_counts()
            self._active.abort(failure_evidence_ids=(failure_id,))
            self._active = None
        self._terminal = True


@contextmanager
def activate_owned_causal_promotion_accounting_v2(
    *,
    occurrence_id: str,
    recorder_id: str = RECORDER_ID,
) -> Iterator[OwnedConstructionAccountingSessionV2]:
    """Bind existing owner-local source hooks to the 12-instance V2 plan."""

    if not _PROCESS_LOCK.acquire(blocking=False):
        raise OwnedConstructionAccountingRuntimeV2Error(
            "another owned causal-promotion accounting run is active"
        )
    token = None
    session = None
    try:
        if hook_runtime_v1._ACTIVE_RUNTIME.get() is not None:  # noqa: SLF001
            raise OwnedConstructionAccountingRuntimeV2Error(
                "an existing owned accounting runtime is active"
            )
        registry = registry_v6.official_counter_registry_v6()
        stage = registry_v6.official_stage_profile_v6(registry)
        comparison = registry_v6.official_comparison_profile_v6(registry)
        actual = registry_v6.official_actual_projection_profile_v6(
            registry, comparison
        )
        boundary = (
            manifest_v4
            .official_k7_causal_promotion_operation_boundary_manifest_v4()
        )
        session = OwnedConstructionAccountingSessionV2(
            occurrence_id=occurrence_id,
            recorder_id=recorder_id,
            counter_registry=registry,
            stage_profile=stage,
            comparison_profile=comparison,
            actual_projection_profile=actual,
            boundary_profile=boundary,
        )
        token = hook_runtime_v1._ACTIVE_RUNTIME.set(session)  # noqa: SLF001
        try:
            yield session
        except BaseException as error:
            session.abort_occurrence(type(error).__name__)
            raise
        else:
            if not session.is_terminal:
                session.abort_occurrence("INCOMPLETE_CAUSAL_PROMOTION_SCOPE")
                raise OwnedConstructionAccountingRuntimeV2Error(
                    "owned causal-promotion scope exited without completion"
                )
    finally:
        if token is not None:
            hook_runtime_v1._ACTIVE_RUNTIME.reset(token)  # noqa: SLF001
        _PROCESS_LOCK.release()


def enter_owned_causal_promotion_stage_v2(stage: Any) -> None:
    session = hook_runtime_v1._ACTIVE_RUNTIME.get()  # noqa: SLF001
    if session is not None:
        if type(session) is not OwnedConstructionAccountingSessionV2:
            raise OwnedConstructionAccountingRuntimeV2Error(
                "active runtime is not the causal-promotion successor"
            )
        session.enter_stage(stage)


def exit_owned_causal_promotion_stage_v2(
    stage: Any | None = None,
    *,
    output_bindings: Sequence[tuple[str, str]] = (),
) -> None:
    session = hook_runtime_v1._ACTIVE_RUNTIME.get()  # noqa: SLF001
    if session is not None:
        if type(session) is not OwnedConstructionAccountingSessionV2:
            raise OwnedConstructionAccountingRuntimeV2Error(
                "active runtime is not the causal-promotion successor"
            )
        session.exit_stage(stage, output_bindings=output_bindings)


def complete_owned_causal_promotion_occurrence_v2(
) -> OwnedCausalPromotionAccountingResultV2 | None:
    session = hook_runtime_v1._ACTIVE_RUNTIME.get()  # noqa: SLF001
    if session is None:
        return None
    if type(session) is not OwnedConstructionAccountingSessionV2:
        raise OwnedConstructionAccountingRuntimeV2Error(
            "active runtime is not the causal-promotion successor"
        )
    return session.complete_occurrence()


def owned_causal_promotion_accounting_active_v2() -> bool:
    return type(hook_runtime_v1._ACTIVE_RUNTIME.get()) is (  # noqa: SLF001
        OwnedConstructionAccountingSessionV2
    )


__all__ = (
    "CANONICAL_CAUSAL_PROMOTION_STAGE_PLAN_V2",
    "EXPECTED_OPEN_CHECKPOINT_INSTANCE_COUNT",
    "EXPECTED_OPEN_INCREMENTAL_INSTANCE_COUNT",
    "EXPECTED_STAGE_INSTANCE_COUNT",
    "OwnedCausalPromotionAccountingResultV2",
    "OwnedConstructionAccountingRuntimeV2Error",
    "activate_owned_causal_promotion_accounting_v2",
    "complete_owned_causal_promotion_occurrence_v2",
    "enter_owned_causal_promotion_stage_v2",
    "exit_owned_causal_promotion_stage_v2",
    "owned_causal_promotion_accounting_active_v2",
)
