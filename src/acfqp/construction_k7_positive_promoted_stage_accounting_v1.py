"""Owner-bound V6 stage accounting for one fresh promoted abstract plan.

The promoted RAPM is an already-existing, query-neutral model.  This module
therefore records explicit-zero preopen/acquisition/build stages, executes the
fresh H=2 planner exactly once in ``OPEN_CHECKPOINT_REPLANNING``, and closes
one successful abstract route in the reconciliation stage.  Planner events
come only from the registered owner hooks already present in the V2 planner.

Shared process/I/O/hash predicates are deliberately left as stage-local zero
placeholders.  A later occurrence materializer replaces, rather than sums,
those nine paths with complete-window receipts.  This slice issues no
terminal, campaign, scientific, official, scalar, or economics authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import importlib
import threading
from typing import Any, NoReturn

from acfqp import construction_accounting_live_v3 as live_v3
from acfqp import construction_accounting_owned_runtime_v1 as owned_v1
from acfqp import construction_accounting_registry_v3 as registry_v3
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_positive_promoted_overlay_v1 as positive_v1
from acfqp import v075_k7_causal_promotion_operation_boundary_manifest_v4 as boundary_v4
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_POSITIVE_PROMOTED_STAGE_ACCOUNTING_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.117"
PROFILE_KEY = "construction_k7_positive_promoted_stage_accounting_v1"
RECORDER_ID = "construction-k7-positive-promoted-stage-accounting-v1"
RESULT_DOMAIN = CONSTRUCTION_K7_POSITIVE_PROMOTED_STAGE_ACCOUNTING_V1_DOMAIN
LOCAL_DOMAINS = frozenset({RESULT_DOMAIN})
if LOCAL_DOMAINS - PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("positive promoted stage-accounting domain is not central")

_S = registry_v6.ConstructionStageKindV6
CANONICAL_STAGE_PLAN_V1 = (
    _S.PREOPEN_COMMON_PREFIX,
    _S.INITIAL_ACQUISITION,
    _S.INITIAL_MODEL_BUILD,
    _S.OPEN_CHECKPOINT_REPLANNING,
    _S.CLOSED_RECONCILIATION_AND_TERMINALIZATION,
)
SHARED_PLACEHOLDER_PATHS = (
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
EXPECTED_STAGE_COUNT = len(CANONICAL_STAGE_PLAN_V1)
EXPECTED_STAGE_LOCAL_RECORD_COUNT = (
    EXPECTED_STAGE_COUNT * registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
)
EXPECTED_INTEGRITY_OBLIGATIONS = (
    "typed-positive-input-identity-graph",
    "v6-profile-chain",
    "open-boundary-manifest",
    "operational-plan-byte-identity",
    "five-stage-event-replay",
    "route-reconciliation",
)
EXPECTED_PROTOCOL_OBLIGATIONS = (
    "single-owner-accounting-scope",
    "promoted-model-reuse-before-planning",
    "one-fresh-planner-call",
    "no-operational-exact-lift-replay",
    "abstract-route-family-exclusivity",
)
_PROCESS_LOCK = threading.Lock()


class ConstructionK7PositivePromotedStageAccountingV1Error(RuntimeError):
    """The positive route, owner binding, stage order, or event replay changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PositivePromotedStageAccountingV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7PositivePromotedStageAccountingV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _stage(value: Any) -> registry_v6.ConstructionStageKindV6:
    try:
        return registry_v6.ConstructionStageKindV6(getattr(value, "value", value))
    except (TypeError, ValueError) as error:
        raise ConstructionK7PositivePromotedStageAccountingV1Error(
            f"unknown positive accounting stage {value!r}"
        ) from error


def _live_stage(value: Any) -> registry_v3.ConstructionStageKindV3:
    return registry_v3.ConstructionStageKindV3(_stage(value).value)


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
        raise ConstructionK7PositivePromotedStageAccountingV1Error(
            f"cannot bind positive operation owner {module_name}.{symbol}"
        ) from error
    function = getattr(selected, "__func__", selected)
    code = getattr(function, "__code__", None)
    if code is None:
        _fail(f"positive operation owner {module_name}.{symbol} has no code")
    return module.__dict__, code


class _BusinessHashMeterV1:
    def __init__(self) -> None:
        self.count = 0
        self._original: Any = None
        self._installed: Any = None

    def __enter__(self) -> "_BusinessHashMeterV1":
        self._original = hashlib.sha256

        def metered(*args: Any, **kwargs: Any) -> Any:
            self.count += 1
            return self._original(*args, **kwargs)

        self._installed = metered
        hashlib.sha256 = metered  # type: ignore[assignment]
        return self

    def __exit__(self, _kind: object, _value: object, _traceback: object) -> None:
        changed = hashlib.sha256 is not self._installed
        hashlib.sha256 = self._original  # type: ignore[assignment]
        if changed:
            _fail("positive planner business-hash meter binding changed")


class _PositiveStageHookV1:
    """Minimal owner-checked adapter consumed by ``emit_owned_operation_v1``."""

    def __init__(
        self,
        *,
        active: live_v3.ConstructionActiveStageV3,
        manifest: boundary_v4.K7CausalPromotionOperationBoundaryManifestV4,
    ) -> None:
        self._owner_thread = threading.get_ident()
        self._active = active
        self._stage = _stage(active.start.stage_kind)
        rows = tuple(
            row
            for row in manifest.boundaries
            if _emittable(row) and _stage(row.stage) is self._stage
        )
        self._by_dispatch: dict[str, Any] = {}
        self._owners: dict[str, tuple[Any, Any]] = {}
        for row in rows:
            if row.dispatch_key in self._by_dispatch:
                _fail("positive stage dispatch inventory is ambiguous")
            self._by_dispatch[row.dispatch_key] = row
            self._owners[row.boundary_key] = _owner_binding(
                row.operation_source_module,
                row.operation_source_symbol,
            )
        self._pending: dict[str, int] = {}

    def emit_operation(
        self,
        dispatch_key: Any,
        amount: Any = 1,
        *,
        caller_module: Any,
        caller_globals: Any,
        caller_code: Any,
    ) -> None:
        if (
            threading.get_ident() != self._owner_thread
            or type(dispatch_key) is not str
            or type(amount) is not int
            or amount != 1
        ):
            _fail("positive planner operation escaped its owner-bound stage")
        row = self._by_dispatch.get(dispatch_key)
        if row is None:
            _fail(f"unregistered positive planner operation {dispatch_key!r}")
        expected_globals, expected_code = self._owners[row.boundary_key]
        if (
            caller_module != row.operation_source_module
            or caller_globals is not expected_globals
            or caller_code is not expected_code
        ):
            _fail("positive planner operation caller differs from its owner")
        self._pending[row.boundary_key] = self._pending.get(row.boundary_key, 0) + 1

    def flush(self) -> None:
        for key in sorted(self._pending):
            row = next(
                item for item in self._by_dispatch.values()
                if item.boundary_key == key
            )
            self._active.add(
                row.target_path,
                self._pending[key],
                operation_site_id=row.boundary_id,
            )
        self._pending.clear()


@dataclass(frozen=True, slots=True)
class PositivePromotedStageAccountingResultV1:
    positive_result: positive_v1.PositivePromotedOverlayResultV1 = field(
        repr=False, compare=False
    )
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    boundary_manifest_id: str
    lifecycle_id: str
    business_hash_invocations: int
    integrity_obligations: tuple[str, ...]
    protocol_obligations: tuple[str, ...]
    recorded_stages: tuple[live_v3.RecordedStageWorkV3, ...]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.positive_result) is not positive_v1.PositivePromotedOverlayResultV1:
            _fail("positive stage accounting requires one exact result")
        for value, label in (
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.comparison_profile_id, "comparison profile"),
            (self.actual_projection_profile_id, "actual projection profile"),
            (self.boundary_manifest_id, "operation boundary manifest"),
            (self.lifecycle_id, "accounting lifecycle"),
        ):
            _cid(value, label)
        if (
            type(self.recorded_stages) is not tuple
            or len(self.recorded_stages) != EXPECTED_STAGE_COUNT
            or tuple(_stage(row.stage_start.stage_kind) for row in self.recorded_stages)
            != CANONICAL_STAGE_PLAN_V1
            or any(
                row.work_vector.subject_id
                != self.positive_result.query.logical_occurrence_id
                for row in self.recorded_stages
            )
            or any(
                row.work_vector.values[path] != 0
                for row in self.recorded_stages
                for path in SHARED_PLACEHOLDER_PATHS
            )
            or type(self.business_hash_invocations) is not int
            or self.business_hash_invocations <= 0
            or self.integrity_obligations != EXPECTED_INTEGRITY_OBLIGATIONS
            or self.protocol_obligations != EXPECTED_PROTOCOL_OBLIGATIONS
        ):
            _fail("positive stage-accounting chain is malformed")
        values = self.recorded_stages[3].work_vector.values
        if (
            not self.recorded_stages[3].operation_events
            or not any(
                value > 0
                for path, value in values.items()
                if path.startswith("build.open_checkpoint_")
            )
            or self.recorded_stages[4].work_vector.values["route.successes"] != 1
            or self.recorded_stages[4].work_vector.values["route.attempts"] != 1
            or self.recorded_stages[4].work_vector.values["route.failures"] != 0
        ):
            _fail("positive abstract planning or route reconciliation was not observed")
        object.__setattr__(self, "_result_id", content_id(RESULT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        planner = self.recorded_stages[3]
        return {
            "schema": "acfqp.construction_k7_positive_promoted_stage_accounting.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "positive_promoted_overlay_result_id": self.positive_result.result_id,
            "logical_occurrence_id": self.positive_result.query.logical_occurrence_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "operation_boundary_manifest_id": self.boundary_manifest_id,
            "accounting_lifecycle_id": self.lifecycle_id,
            "business_hash_invocations": self.business_hash_invocations,
            "named_integrity_obligations": list(self.integrity_obligations),
            "named_protocol_obligations": list(self.protocol_obligations),
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
            "stage_local_counter_record_count": EXPECTED_STAGE_LOCAL_RECORD_COUNT,
            "fresh_planner_operation_event_count": len(planner.operation_events),
            "fresh_policy_assignments_evaluated": (
                self.positive_result.plan.proof.policy_assignments_evaluated
            ),
            "fresh_planner_called_exactly_once": True,
            "promoted_model_reused_without_rebuild": True,
            "fresh_ground_or_observer_event_count": 0,
            "local_fallback_rebuild_native_zero": True,
            "nine_shared_paths_are_stage_placeholders": True,
            "shared_resource_receipts_issued": False,
            "occurrence_work_vector_issued": False,
            "terminal_artifact_issued": False,
            "campaign_occurrence_closed": False,
            "scientific_endpoint_credit_allowed": False,
            "official_execution_allowed": False,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
        }

    @property
    def result_id(self) -> str:
        current = content_id(RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("positive stage-accounting result changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "recorded_stages": [row.to_document() for row in self.recorded_stages],
            "positive_promoted_stage_accounting_id": self.result_id,
        }


def record_positive_promoted_abstract_route_v1(
    result: positive_v1.PositivePromotedOverlayResultV1,
) -> PositivePromotedStageAccountingResultV1:
    if type(result) is not positive_v1.PositivePromotedOverlayResultV1:
        _fail("positive stage accounting rejects a foreign result")
    # The producer-free verifier is the independent evaluation boundary.
    # Operational accounting consumes the already-issued typed authority and
    # checks its live identity graph; it must not replay the full producer.
    result.result_id
    result.epoch.epoch_id
    result.query.query_id
    result.plan.plan_id
    result.exact_lift.binding_id
    if (
        result.query.epoch != result.epoch
        or result.plan.query != result.query
        or result.exact_lift.plan != result.plan
    ):
        _fail("positive stage-accounting input identity graph changed")
    verified = result
    if not _PROCESS_LOCK.acquire(blocking=False):
        _fail("another positive stage-accounting scope is active")
    token = None
    try:
        if owned_v1._ACTIVE_RUNTIME.get() is not None:  # noqa: SLF001
            _fail("another owner-bound accounting runtime is active")
        registry = registry_v6.official_counter_registry_v6()
        stage_profile = registry_v6.official_stage_profile_v6(registry)
        comparison = registry_v6.official_comparison_profile_v6(registry)
        actual = registry_v6.official_actual_projection_profile_v6(
            registry, comparison
        )
        manifest = boundary_v4.official_k7_causal_promotion_operation_boundary_manifest_v4()
        manifest.validate_official()
        lifecycle = live_v3.open_construction_accounting_lifecycle_v3(
            subject_id=verified.query.logical_occurrence_id,
            recorder_id=RECORDER_ID,
            stage_plan=tuple(_live_stage(item) for item in CANONICAL_STAGE_PLAN_V1),
            registry=registry,
            stage_profile=stage_profile,
            comparison_profile=comparison,
            actual_projection_profile=actual,
        )
        rows: list[live_v3.RecordedStageWorkV3] = []
        outputs = (
            (verified.query.query_id,),
            (verified.epoch.epoch_id,),
            (verified.epoch.model.model_id,),
        )
        for stage, output_ids in zip(CANONICAL_STAGE_PLAN_V1[:3], outputs):
            active = lifecycle.begin_stage(_live_stage(stage))
            rows.append(active.complete(output_artifact_ids=output_ids))

        active = lifecycle.begin_stage(_live_stage(CANONICAL_STAGE_PLAN_V1[3]))
        hook = _PositiveStageHookV1(active=active, manifest=manifest)
        token = owned_v1._ACTIVE_RUNTIME.set(hook)  # noqa: SLF001
        meter = _BusinessHashMeterV1()
        try:
            with meter:
                operational_plan = positive_v1.plan_positive_promoted_overlay_query_v1(
                    verified.query
                )
        finally:
            owned_v1._ACTIVE_RUNTIME.reset(token)  # noqa: SLF001
            token = None
        if (
            operational_plan.proof != verified.plan.proof
            or operational_plan.plan_id != verified.plan.plan_id
        ):
            _fail("owner-accounted fresh planner replay changed its exact plan")
        hook.flush()
        rows.append(
            active.complete(
                output_artifact_ids=(
                    operational_plan.proof.proof_id,
                    operational_plan.plan_id,
                )
            )
        )

        active = lifecycle.begin_stage(_live_stage(CANONICAL_STAGE_PLAN_V1[4]))
        active.add(
            "route.successes",
            1,
            operation_site_id=content_id(
                RESULT_DOMAIN,
                {
                    "role": "positive-abstract-route-success",
                    "positive_promoted_overlay_result_id": verified.result_id,
                    "fresh_numerical_proof_id": verified.plan.proof.proof_id,
                },
            ),
        )
        rows.append(
            active.complete(output_artifact_ids=(verified.exact_lift.binding_id,))
        )
        recorded = lifecycle.finish()
        if tuple(rows) != recorded:
            _fail("positive accounting lifecycle replay changed")
        issued = PositivePromotedStageAccountingResultV1(
            verified,
            registry.registry_id,
            stage_profile.stage_profile_id,
            comparison.comparison_profile_id,
            actual.actual_projection_profile_id,
            manifest.manifest_id,
            lifecycle.lifecycle_id,
            meter.count,
            EXPECTED_INTEGRITY_OBLIGATIONS,
            EXPECTED_PROTOCOL_OBLIGATIONS,
            recorded,
        )
        return verify_positive_promoted_stage_accounting_v1(issued)
    finally:
        if token is not None:
            owned_v1._ACTIVE_RUNTIME.reset(token)  # noqa: SLF001
        _PROCESS_LOCK.release()


def verify_positive_promoted_stage_accounting_v1(
    result: PositivePromotedStageAccountingResultV1,
) -> PositivePromotedStageAccountingResultV1:
    if type(result) is not PositivePromotedStageAccountingResultV1:
        _fail("positive stage-accounting verifier rejects foreign values")
    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(registry, comparison)
    manifest = boundary_v4.official_k7_causal_promotion_operation_boundary_manifest_v4()
    manifest.validate_official()
    result.positive_result.result_id
    if (
        result.counter_registry_id != registry.registry_id
        or result.stage_profile_id != stage_profile.stage_profile_id
        or result.comparison_profile_id != comparison.comparison_profile_id
        or result.actual_projection_profile_id != actual.actual_projection_profile_id
        or result.boundary_manifest_id != manifest.manifest_id
        or tuple(_stage(row.stage_start.stage_kind) for row in result.recorded_stages)
        != CANONICAL_STAGE_PLAN_V1
    ):
        _fail("positive stage-accounting authority binding changed")
    for row in result.recorded_stages:
        live_v3.verify_recorded_stage_work_v3(
            row,
            registry,
            stage_profile,
            comparison,
            actual,
        )
    result.__post_init__()
    return result


__all__ = (
    "CANONICAL_STAGE_PLAN_V1",
    "ConstructionK7PositivePromotedStageAccountingV1Error",
    "LOCAL_DOMAINS",
    "PositivePromotedStageAccountingResultV1",
    "record_positive_promoted_abstract_route_v1",
    "verify_positive_promoted_stage_accounting_v1",
)
