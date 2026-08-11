"""Three-stage native accounting runtime for the recovery-eligible loop."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import importlib
import sys
import threading
from typing import Any, Iterator, Mapping, NoReturn

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_live_v3 as live_v3
from acfqp import construction_accounting_owned_runtime_v1 as hook_v1
from acfqp import construction_accounting_registry_v3 as registry_v3
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_recovery_eligible_accounting_manifest_v1 as manifest_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_STAGE_ACCOUNTING_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.114"
PROFILE_KEY = "construction_k7_recovery_eligible_stage_accounting_v1"
RECORDER_ID = "construction-k7-recovery-eligible-stage-accounting-v1"
RESULT_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_STAGE_ACCOUNTING_V1_DOMAIN
LOCAL_DOMAINS = frozenset({RESULT_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("recovery-eligible stage-accounting domain is not central")

CANONICAL_STAGE_PLAN_V1 = manifest_v1.CANONICAL_STAGE_PLAN_V1
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
EXPECTED_STAGE_COUNT = 3
EXPECTED_STAGE_LOCAL_RECORD_COUNT = (
    EXPECTED_STAGE_COUNT * registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
)
_PROCESS_LOCK = threading.Lock()


class ConstructionK7RecoveryEligibleStageAccountingV1Error(RuntimeError):
    """The three-stage order, source owner, or native event changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RecoveryEligibleStageAccountingV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligibleStageAccountingV1Error(
            f"{label} must be one content ID"
        ) from error


def _stage(value: Any) -> registry_v6.ConstructionStageKindV6:
    try:
        return registry_v6.ConstructionStageKindV6(getattr(value, "value", value))
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligibleStageAccountingV1Error(
            f"unknown recovery accounting stage {value!r}"
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
        raise ConstructionK7RecoveryEligibleStageAccountingV1Error(
            f"cannot bind recovery operation owner {module_name}.{symbol}"
        ) from error
    function = getattr(selected, "__func__", selected)
    code = getattr(function, "__code__", None)
    if code is None:
        _fail(f"recovery operation owner {module_name}.{symbol} has no code")
    return module.__dict__, code


@dataclass(frozen=True, slots=True)
class RecoveryEligibleStageAccountingResultV1:
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
            (self.occurrence_id, "logical occurrence"),
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.comparison_profile_id, "comparison profile"),
            (self.actual_projection_profile_id, "actual projection profile"),
            (self.boundary_manifest_id, "boundary manifest"),
            (self.lifecycle_id, "accounting lifecycle"),
        ):
            _cid(value, label)
        if (
            type(self.recorded_stages) is not tuple
            or len(self.recorded_stages) != EXPECTED_STAGE_COUNT
            or tuple(_stage(row.stage_start.stage_kind) for row in self.recorded_stages)
            != CANONICAL_STAGE_PLAN_V1
            or type(self.stage_output_bindings) is not tuple
            or len(self.stage_output_bindings) != EXPECTED_STAGE_COUNT
            or any(
                row.work_vector.values[path] != 0
                for row in self.recorded_stages
                for path in SHARED_RESOURCE_PATHS
            )
        ):
            _fail("recovery stage-accounting result changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_stage_accounting.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_id": self.occurrence_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "boundary_manifest_id": self.boundary_manifest_id,
            "lifecycle_id": self.lifecycle_id,
            "stage_plan": [item.value for item in CANONICAL_STAGE_PLAN_V1],
            "stage_work_vector_ids": [
                row.work_vector.work_vector_id for row in self.recorded_stages
            ],
            "stage_comparison_vector_ids": [
                row.comparison_vector.comparison_vector_id
                for row in self.recorded_stages
            ],
            "stage_projection_proof_ids": [
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
            "native_operation_events_owner_bound": True,
            "native_zeroes_explicit": True,
            "nine_shared_resource_paths_are_zero_placeholders": True,
            "shared_resource_receipts_present": False,
            "occurrence_work_vector_issued": False,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        return content_id(RESULT_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "recorded_stages": [row.to_document() for row in self.recorded_stages],
            "recovery_eligible_stage_accounting_id": self.result_id,
        }


class RecoveryEligibleStageAccountingSessionV1:
    def __init__(
        self,
        *,
        occurrence_id: str,
        recorder_id: str,
        registry: registry_v6.CounterRegistryV6,
        stage_profile: Any,
        comparison_profile: Any,
        actual_projection_profile: Any,
        manifest: manifest_v1.RecoveryEligibleAccountingManifestV1,
    ) -> None:
        self._owner_thread = threading.get_ident()
        self._occurrence_id = _cid(occurrence_id, "logical occurrence")
        self._registry = registry
        self._stage_profile = stage_profile
        self._comparison_profile = comparison_profile
        self._actual_profile = actual_projection_profile
        self._manifest = manifest
        self._validate_authorities()
        self._lifecycle = live_v3.open_construction_accounting_lifecycle_v3(
            subject_id=self._occurrence_id,
            recorder_id=recorder_id,
            stage_plan=tuple(_live_stage(row) for row in CANONICAL_STAGE_PLAN_V1),
            registry=registry,
            stage_profile=stage_profile,
            comparison_profile=comparison_profile,
            actual_projection_profile=actual_projection_profile,
        )
        self._active: live_v3.ConstructionActiveStageV3 | None = None
        self._pending: dict[str, int] = {}
        self._outputs: list[tuple[tuple[str, str], ...]] = []
        self._result: RecoveryEligibleStageAccountingResultV1 | None = None
        self._terminal = False
        self._owner_bindings = {
            row.boundary_key: _owner_binding(
                row.operation_source_module, row.operation_source_symbol
            )
            for row in manifest.boundaries
        }
        self._by_dispatch = {
            (row.stage, row.dispatch_key): row for row in manifest.boundaries
        }
        if len(self._by_dispatch) != len(manifest.boundaries):
            _fail("recovery operation dispatch inventory is ambiguous")

    def _validate_authorities(self) -> None:
        self._registry.validate_official_catalogue()
        self._stage_profile.validate(self._registry)
        self._comparison_profile.validate(self._registry)
        self._actual_profile.validate(self._registry, self._comparison_profile)
        self._manifest.validate_official()
        if (
            self._manifest.counter_registry_id != self._registry.registry_id
            or self._manifest.stage_profile_id != self._stage_profile.stage_profile_id
            or self._manifest.comparison_profile_id
            != self._comparison_profile.comparison_profile_id
            or self._manifest.actual_projection_profile_id
            != self._actual_profile.actual_projection_profile_id
        ):
            _fail("recovery accounting authorities crossed")

    def _check_owner(self) -> None:
        if threading.get_ident() != self._owner_thread:
            _fail("recovery accounting session used from another thread")

    @property
    def is_terminal(self) -> bool:
        return self._terminal

    @property
    def active_stage(self) -> registry_v6.ConstructionStageKindV6 | None:
        return None if self._active is None else _stage(self._active.start.stage_kind)

    def enter_stage(self, stage: Any) -> None:
        self._check_owner()
        selected = _stage(stage)
        index = len(self._lifecycle.recorded_stages)
        if (
            self._terminal
            or self._active is not None
            or index >= EXPECTED_STAGE_COUNT
            or selected is not CANONICAL_STAGE_PLAN_V1[index]
        ):
            _fail("recovery accounting stage entry is not legal")
        self._active = self._lifecycle.begin_stage(_live_stage(selected))
        self._pending = {}

    def emit_operation(
        self,
        dispatch_key: Any,
        amount: Any = 1,
        *,
        caller_module: Any,
        caller_globals: Any,
        caller_code: Any,
    ) -> None:
        self._check_owner()
        if (
            self._terminal
            or self._active is None
            or type(dispatch_key) is not str
            or type(amount) is not int
            or amount != 1
        ):
            _fail("recovery operation occurred outside its exact stage")
        boundary = self._by_dispatch.get((self.active_stage, dispatch_key))
        if boundary is None:
            _fail(f"unregistered recovery operation {dispatch_key!r}")
        expected_globals, expected_code = self._owner_bindings[boundary.boundary_key]
        if (
            caller_module != boundary.operation_source_module
            or caller_globals is not expected_globals
            or caller_code is not expected_code
        ):
            _fail("recovery operation caller differs from its registered owner")
        leaf = self._registry.by_path[boundary.target_path]
        if boundary.reducer is not ReducerEnum.SUM or leaf.reducer is not ReducerEnum.SUM:
            _fail("recovery source hooks must be SUM primitives")
        self._pending[boundary.boundary_key] = (
            self._pending.get(boundary.boundary_key, 0) + 1
        )

    def _flush(self) -> None:
        if self._active is None:
            if self._pending:
                _fail("recovery pending operations lack an active stage")
            return
        for key in sorted(self._pending):
            boundary = self._manifest.by_key[key]
            self._active.add(
                boundary.target_path,
                self._pending[key],
                operation_site_id=boundary.boundary_id,
            )
        self._pending = {}

    def exit_stage(self, *, output_bindings: Any) -> None:
        self._check_owner()
        if self._terminal or self._active is None:
            _fail("recovery accounting stage exit is not legal")
        try:
            bindings = tuple(
                sorted(
                    (str(role), _cid(value, f"stage output {role}"))
                    for role, value in output_bindings
                )
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7RecoveryEligibleStageAccountingV1Error(
                "recovery stage outputs are malformed"
            ) from error
        if len({role for role, _value in bindings}) != len(bindings):
            _fail("recovery stage output roles repeat")
        self._flush()
        self._active.complete(output_artifact_ids=tuple(value for _role, value in bindings))
        self._outputs.append(bindings)
        self._active = None

    def complete_occurrence(self) -> RecoveryEligibleStageAccountingResultV1:
        self._check_owner()
        if self._result is not None:
            return self._result
        if self._terminal or self._active is not None:
            _fail("recovery accounting lifecycle cannot complete")
        rows = self._lifecycle.finish()
        if len(rows) != EXPECTED_STAGE_COUNT:
            _fail("recovery accounting lifecycle is incomplete")
        self._result = RecoveryEligibleStageAccountingResultV1(
            self._occurrence_id,
            self._registry.registry_id,
            self._stage_profile.stage_profile_id,
            self._comparison_profile.comparison_profile_id,
            self._actual_profile.actual_projection_profile_id,
            self._manifest.manifest_id,
            self._lifecycle.lifecycle_id,
            rows,
            tuple(self._outputs),
        )
        self._terminal = True
        return self._result

    def abort_occurrence(self, reason: str) -> None:
        self._check_owner()
        if self._terminal:
            return
        if self._active is not None:
            failure_id = content_id(
                RESULT_DOMAIN,
                {
                    "schema": "acfqp.construction_k7_recovery_eligible_stage_abort.v1",
                    "logical_occurrence_id": self._occurrence_id,
                    "stage": self.active_stage.value,
                    "reason": reason if type(reason) is str and reason else "UNSPECIFIED",
                },
            )
            self._flush()
            self._active.abort(failure_evidence_ids=(failure_id,))
            self._active = None
        self._terminal = True


@contextmanager
def activate_recovery_eligible_stage_accounting_v1(
    *,
    occurrence_id: str,
    recorder_id: str = RECORDER_ID,
) -> Iterator[RecoveryEligibleStageAccountingSessionV1]:
    if not _PROCESS_LOCK.acquire(blocking=False):
        _fail("another recovery stage-accounting runtime is active")
    token = None
    session = None
    try:
        if hook_v1._ACTIVE_RUNTIME.get() is not None:  # noqa: SLF001
            _fail("another owned accounting runtime is active")
        registry = registry_v6.official_counter_registry_v6()
        stage = registry_v6.official_stage_profile_v6(registry)
        comparison = registry_v6.official_comparison_profile_v6(registry)
        actual = registry_v6.official_actual_projection_profile_v6(registry, comparison)
        manifest = manifest_v1.official_recovery_eligible_accounting_manifest_v1()
        session = RecoveryEligibleStageAccountingSessionV1(
            occurrence_id=occurrence_id,
            recorder_id=recorder_id,
            registry=registry,
            stage_profile=stage,
            comparison_profile=comparison,
            actual_projection_profile=actual,
            manifest=manifest,
        )
        token = hook_v1._ACTIVE_RUNTIME.set(session)  # noqa: SLF001
        try:
            yield session
        except BaseException as error:
            session.abort_occurrence(type(error).__name__)
            raise
        else:
            if not session.is_terminal:
                session.abort_occurrence("INCOMPLETE_RECOVERY_ACCOUNTING_SCOPE")
                _fail("recovery accounting scope exited before completion")
    finally:
        if token is not None:
            hook_v1._ACTIVE_RUNTIME.reset(token)  # noqa: SLF001
        _PROCESS_LOCK.release()


def verify_recovery_eligible_stage_accounting_v1(
    result: RecoveryEligibleStageAccountingResultV1,
) -> RecoveryEligibleStageAccountingResultV1:
    if type(result) is not RecoveryEligibleStageAccountingResultV1:
        _fail("recovery stage verifier received a foreign result")
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(registry, comparison)
    manifest = manifest_v1.official_recovery_eligible_accounting_manifest_v1()
    if (
        result.counter_registry_id != registry.registry_id
        or result.stage_profile_id != stage.stage_profile_id
        or result.comparison_profile_id != comparison.comparison_profile_id
        or result.actual_projection_profile_id != actual.actual_projection_profile_id
        or result.boundary_manifest_id != manifest.manifest_id
    ):
        _fail("recovery stage result authority changed")
    for row in result.recorded_stages:
        live_v3.verify_recorded_stage_work_v3(row, registry, stage, comparison, actual)
    return result


__all__ = (
    "CANONICAL_STAGE_PLAN_V1",
    "ConstructionK7RecoveryEligibleStageAccountingV1Error",
    "EXPECTED_STAGE_COUNT",
    "EXPECTED_STAGE_LOCAL_RECORD_COUNT",
    "LOCAL_DOMAINS",
    "RecoveryEligibleStageAccountingResultV1",
    "activate_recovery_eligible_stage_accounting_v1",
    "verify_recovery_eligible_stage_accounting_v1",
)
