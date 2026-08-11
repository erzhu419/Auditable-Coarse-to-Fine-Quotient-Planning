"""Owner-bound stage accounting for fresh held-out abstract reuse.

The query-neutral W5 overlay already exists before this occurrence starts.
The only substantive route work is one robust H=2 quotient-planner call.  Two
inactive-by-default hooks in the planner expose its audit obligation and each
robust Bellman row backup to this recorder.  No source reconstruction,
observer, exact evaluator, ground solver, or same-implementation verifier is
run in the operational window.

The nine shared-resource paths remain explicit zero placeholders here.  They
are replaced by complete-window receipts in the occurrence-accounting slice;
they are never summed with these placeholders.
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
from acfqp import construction_k7_heldout_checkpoint_recertification_v1 as source_v1
from acfqp import construction_k7_heldout_overlay_abstract_reuse_v1 as reuse_v1
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp.accounting_v1 import ReducerEnum
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_OPERATION_BOUNDARY_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_OPERATION_MANIFEST_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_STAGE_ACCOUNTING_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_STAGE_PROFILE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.122"
PROFILE_KEY = "construction_k7_heldout_abstract_stage_accounting_v1"
RECORDER_ID = "construction-k7-heldout-abstract-stage-accounting-v1"

STAGE_PROFILE_DOMAIN = CONSTRUCTION_K7_HELDOUT_ABSTRACT_STAGE_PROFILE_V1_DOMAIN
BOUNDARY_DOMAIN = CONSTRUCTION_K7_HELDOUT_ABSTRACT_OPERATION_BOUNDARY_V1_DOMAIN
MANIFEST_DOMAIN = CONSTRUCTION_K7_HELDOUT_ABSTRACT_OPERATION_MANIFEST_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_HELDOUT_ABSTRACT_STAGE_ACCOUNTING_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {STAGE_PROFILE_DOMAIN, BOUNDARY_DOMAIN, MANIFEST_DOMAIN, RESULT_DOMAIN}
)
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("held-out abstract stage-accounting domains are not central")

_S = registry_v6.ConstructionStageKindV6
CANONICAL_STAGE_PLAN_V1 = (
    _S.PREOPEN_COMMON_PREFIX,
    _S.INITIAL_ACQUISITION,
    _S.INITIAL_MODEL_BUILD,
    _S.OPEN_CHECKPOINT_REPLANNING,
    _S.CLOSED_RECONCILIATION_AND_TERMINALIZATION,
)
ABSTRACT_OPERATION_PATHS = (
    "common.abstract_audit_obligations",
    "common.abstract_bellman_backups",
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
    "typed-heldout-source-identity-graph",
    "v6-registry-and-heldout-stage-profile",
    "two-owner-operation-manifest",
    "fresh-query-model-threshold-binding",
    "five-stage-event-replay",
    "route-reconciliation",
)
EXPECTED_PROTOCOL_OBLIGATIONS = (
    "single-owner-accounting-scope",
    "query-neutral-overlay-present-before-planning",
    "one-fresh-quotient-planner-call",
    "no-operational-source-or-audit-replay",
    "no-ground-observer-or-exact-evaluator",
    "abstract-route-family-exclusivity",
)
_PROCESS_LOCK = threading.Lock()


class ConstructionK7HeldoutAbstractStageAccountingV1Error(RuntimeError):
    """The held-out stage profile, owner event, or replay changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutAbstractStageAccountingV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutAbstractStageAccountingV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _stage(value: Any) -> registry_v6.ConstructionStageKindV6:
    try:
        return registry_v6.ConstructionStageKindV6(getattr(value, "value", value))
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutAbstractStageAccountingV1Error(
            f"unknown held-out accounting stage {value!r}"
        ) from error


def _live_stage(value: Any) -> registry_v3.ConstructionStageKindV3:
    return registry_v3.ConstructionStageKindV3(_stage(value).value)


def _expected_stage_rules() -> tuple[registry_v6.StageRuleV6, ...]:
    base = registry_v6.official_stage_profile_v6()
    result = []
    for row in base.rules:
        additions = (
            ABSTRACT_OPERATION_PATHS
            if row.stage_kind is _S.OPEN_CHECKPOINT_REPLANNING
            else ()
        )
        result.append(
            registry_v6.StageRuleV6(
                row.stage_kind,
                tuple(sorted(set(row.allowed_nonzero_paths) | set(additions))),
            )
        )
    return tuple(sorted(result, key=lambda row: row.stage_kind.value))


@dataclass(frozen=True, slots=True)
class HeldoutAbstractStageProfileV1:
    counter_registry_id: str
    v6_stage_profile_id: str
    rules: tuple[registry_v6.StageRuleV6, ...]

    def __post_init__(self) -> None:
        _cid(self.counter_registry_id, "held-out stage counter registry")
        _cid(self.v6_stage_profile_id, "held-out predecessor stage profile")
        if self.rules != _expected_stage_rules():
            _fail("held-out abstract stage rules changed")

    @property
    def by_stage(self) -> dict[Any, registry_v6.StageRuleV6]:
        return {row.stage_kind: row for row in self.rules}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_stage_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "v6_stage_profile_id": self.v6_stage_profile_id,
            "rules": [row.to_document() for row in self.rules],
            "v6_stage_ownership_preserved_exactly": True,
            "abstract_audit_and_bellman_paths_added_only_to_open_checkpoint": True,
            "runtime_owner_match_verified": False,
            "runtime_stage_attribution_verified": False,
        }

    @property
    def stage_profile_id(self) -> str:
        return content_id(STAGE_PROFILE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "stage_profile_id": self.stage_profile_id}

    def validate(self, registry: registry_v6.CounterRegistryV6) -> None:
        registry.validate_official_catalogue()
        base = registry_v6.official_stage_profile_v6(registry)
        if (
            self.counter_registry_id != registry.registry_id
            or self.v6_stage_profile_id != base.stage_profile_id
            or self.rules != _expected_stage_rules()
        ):
            _fail("held-out stage profile binding changed")


def official_heldout_abstract_stage_profile_v1(
    registry: registry_v6.CounterRegistryV6 | None = None,
) -> HeldoutAbstractStageProfileV1:
    selected = registry or registry_v6.official_counter_registry_v6()
    base = registry_v6.official_stage_profile_v6(selected)
    result = HeldoutAbstractStageProfileV1(
        selected.registry_id,
        base.stage_profile_id,
        _expected_stage_rules(),
    )
    result.validate(selected)
    return result


@dataclass(frozen=True, slots=True)
class HeldoutAbstractOperationBoundaryV1:
    boundary_key: str
    dispatch_key: str
    target_path: str
    registered_owner: str
    operation_source_module: str
    operation_source_symbol: str
    count_rule: str

    def __post_init__(self) -> None:
        if any(
            type(value) is not str or not value
            for value in (
                self.boundary_key,
                self.dispatch_key,
                self.target_path,
                self.registered_owner,
                self.operation_source_module,
                self.operation_source_symbol,
                self.count_rule,
            )
        ):
            _fail("held-out operation boundary is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_operation_boundary.v1",
            "schema_version": SCHEMA_VERSION,
            "boundary_key": self.boundary_key,
            "dispatch_key": self.dispatch_key,
            "stage": _S.OPEN_CHECKPOINT_REPLANNING.value,
            "target_path": self.target_path,
            "registered_owner": self.registered_owner,
            "reducer": ReducerEnum.SUM.value,
            "operation_source_module": self.operation_source_module,
            "operation_source_symbol": self.operation_source_symbol,
            "count_rule": self.count_rule,
            "inactive_without_exact_accounting_scope": True,
        }

    @property
    def boundary_id(self) -> str:
        return content_id(BOUNDARY_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "boundary_id": self.boundary_id}


_EXPECTED_BOUNDARIES = (
    HeldoutAbstractOperationBoundaryV1(
        "heldout.robust.audit-obligation",
        "partial-support.robust-audit-obligation",
        "common.abstract_audit_obligations",
        "abstract_auditor",
        "acfqp.partial_support_robust_planner_v1",
        "_make_audit",
        "one event for the complete robust audit obligation",
    ),
    HeldoutAbstractOperationBoundaryV1(
        "heldout.robust.bellman-backup",
        "partial-support.robust-bellman-backup",
        "common.abstract_bellman_backups",
        "abstract_planner",
        "acfqp.partial_support_robust_planner_v1",
        "_evaluate_ground_row",
        "one event for each robust state-action row backup",
    ),
)


@dataclass(frozen=True, slots=True)
class HeldoutAbstractOperationManifestV1:
    counter_registry_id: str
    stage_profile_id: str
    boundaries: tuple[HeldoutAbstractOperationBoundaryV1, ...]

    def __post_init__(self) -> None:
        _cid(self.counter_registry_id, "manifest counter registry")
        _cid(self.stage_profile_id, "manifest stage profile")
        if self.boundaries != _EXPECTED_BOUNDARIES:
            _fail("held-out operation boundary inventory changed")

    @property
    def by_dispatch(self) -> dict[str, HeldoutAbstractOperationBoundaryV1]:
        return {row.dispatch_key: row for row in self.boundaries}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_operation_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "boundaries": [row.to_document() for row in self.boundaries],
            "owner_boundary_count": len(self.boundaries),
            "source_hooks_inactive_by_default": True,
            "runtime_evidence_issued": False,
        }

    @property
    def manifest_id(self) -> str:
        return content_id(MANIFEST_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}

    def validate(
        self,
        registry: registry_v6.CounterRegistryV6,
        stage_profile: HeldoutAbstractStageProfileV1,
    ) -> None:
        stage_profile.validate(registry)
        allowed = set(
            stage_profile.by_stage[_S.OPEN_CHECKPOINT_REPLANNING]
            .allowed_nonzero_paths
        )
        if (
            self.counter_registry_id != registry.registry_id
            or self.stage_profile_id != stage_profile.stage_profile_id
            or self.boundaries != _EXPECTED_BOUNDARIES
            or len(self.by_dispatch) != len(self.boundaries)
        ):
            _fail("held-out operation manifest identity changed")
        for row in self.boundaries:
            leaf = registry.by_path.get(row.target_path)
            if (
                leaf is None
                or leaf.owner != row.registered_owner
                or leaf.reducer is not ReducerEnum.SUM
                or row.target_path not in allowed
            ):
                _fail("held-out operation boundary differs from V6 semantics")


def official_heldout_abstract_operation_manifest_v1(
    registry: registry_v6.CounterRegistryV6 | None = None,
    stage_profile: HeldoutAbstractStageProfileV1 | None = None,
) -> HeldoutAbstractOperationManifestV1:
    selected = registry or registry_v6.official_counter_registry_v6()
    selected_stage = stage_profile or official_heldout_abstract_stage_profile_v1(
        selected
    )
    result = HeldoutAbstractOperationManifestV1(
        selected.registry_id,
        selected_stage.stage_profile_id,
        _EXPECTED_BOUNDARIES,
    )
    result.validate(selected, selected_stage)
    return result


def _owner_binding(module_name: str, symbol: str) -> tuple[Any, Any]:
    try:
        module = importlib.import_module(module_name)
        function = getattr(module, symbol)
    except (AttributeError, ImportError) as error:
        raise ConstructionK7HeldoutAbstractStageAccountingV1Error(
            f"cannot bind held-out operation owner {module_name}.{symbol}"
        ) from error
    code = getattr(function, "__code__", None)
    if code is None:
        _fail("held-out operation owner has no Python code object")
    return module.__dict__, code


class _HeldoutStageHookV1:
    def __init__(
        self,
        *,
        active: live_v3.ConstructionActiveStageV3,
        manifest: HeldoutAbstractOperationManifestV1,
    ) -> None:
        self._owner_thread = threading.get_ident()
        self._active = active
        self._by_dispatch = manifest.by_dispatch
        self._owners = {
            row.boundary_key: _owner_binding(
                row.operation_source_module, row.operation_source_symbol
            )
            for row in manifest.boundaries
        }
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
            _fail("held-out planner operation escaped its owner-bound stage")
        row = self._by_dispatch.get(dispatch_key)
        if row is None:
            _fail(f"unregistered held-out planner operation {dispatch_key!r}")
        expected_globals, expected_code = self._owners[row.boundary_key]
        if (
            caller_module != row.operation_source_module
            or caller_globals is not expected_globals
            or caller_code is not expected_code
        ):
            _fail("held-out planner event caller differs from its frozen owner")
        self._pending[row.boundary_key] = self._pending.get(row.boundary_key, 0) + 1

    def flush(self) -> None:
        by_key = {row.boundary_key: row for row in self._by_dispatch.values()}
        for key in sorted(self._pending):
            row = by_key[key]
            self._active.add(
                row.target_path,
                self._pending[key],
                operation_site_id=row.boundary_id,
            )
        self._pending.clear()


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
            _fail("held-out planner business-hash meter binding changed")


@dataclass(frozen=True, slots=True)
class HeldoutAbstractStageAccountingResultV1:
    reuse_result: reuse_v1.HeldoutOverlayAbstractReuseResultV1 = field(
        repr=False, compare=False
    )
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    operation_manifest_id: str
    lifecycle_id: str
    business_hash_invocations: int
    integrity_obligations: tuple[str, ...]
    protocol_obligations: tuple[str, ...]
    recorded_stages: tuple[live_v3.RecordedStageWorkV3, ...]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.reuse_result) is not reuse_v1.HeldoutOverlayAbstractReuseResultV1:
            _fail("held-out stage accounting requires one exact reuse result")
        for value, label in (
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.comparison_profile_id, "comparison profile"),
            (self.actual_projection_profile_id, "actual projection profile"),
            (self.operation_manifest_id, "operation manifest"),
            (self.lifecycle_id, "accounting lifecycle"),
        ):
            _cid(value, label)
        if (
            type(self.recorded_stages) is not tuple
            or len(self.recorded_stages) != EXPECTED_STAGE_COUNT
            or tuple(_stage(row.stage_start.stage_kind) for row in self.recorded_stages)
            != CANONICAL_STAGE_PLAN_V1
            or any(
                row.work_vector.subject_id != self.reuse_result.query.logical_occurrence_id
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
            _fail("held-out stage-accounting chain is malformed")
        values = self.recorded_stages[3].work_vector.values
        if (
            values["common.abstract_audit_obligations"] != 1
            or values["common.abstract_bellman_backups"] <= 0
            or len(self.recorded_stages[3].operation_events) != 2
            or self.recorded_stages[4].work_vector.values["route.successes"] != 1
            or self.recorded_stages[4].work_vector.values["route.attempts"] != 1
            or self.recorded_stages[4].work_vector.values["route.failures"] != 0
        ):
            _fail("held-out abstract planner or route reconciliation was not observed")
        object.__setattr__(self, "_result_id", content_id(RESULT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        planner = self.recorded_stages[3]
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_stage_accounting.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "heldout_abstract_reuse_result_id": self.reuse_result.result_id,
            "logical_occurrence_id": self.reuse_result.query.logical_occurrence_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "operation_manifest_id": self.operation_manifest_id,
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
            "abstract_audit_obligations": (
                planner.work_vector.values["common.abstract_audit_obligations"]
            ),
            "abstract_bellman_backups": (
                planner.work_vector.values["common.abstract_bellman_backups"]
            ),
            "fresh_planner_called_exactly_once": True,
            "source_model_or_audit_replayed_operationally": False,
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
            _fail("held-out stage-accounting result changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "recorded_stages": [row.to_document() for row in self.recorded_stages],
            "heldout_abstract_stage_accounting_id": self.result_id,
        }


def _record_heldout_abstract_query_v1(
    source: source_v1.HeldoutCheckpointRecertificationResultV1,
    query: reuse_v1.HeldoutOverlayQueryV1,
    expected_result: reuse_v1.HeldoutOverlayAbstractReuseResultV1 | None,
) -> HeldoutAbstractStageAccountingResultV1:
    if (
        type(source) is not source_v1.HeldoutCheckpointRecertificationResultV1
        or type(query) is not reuse_v1.HeldoutOverlayQueryV1
        or query.source_result_id != source.result_id
        or query.source_overlay_id != source.final_overlay.overlay_id
        or query.context_id != source.context.context_id
        or query.quotient_model_id
        != source.final_overlay.bridge.quotient_model.model_id
        or query.threshold_profile_id != source.threshold.threshold_profile_id
    ):
        _fail("held-out stage-accounting source/query identity graph changed")
    query.query_id
    if expected_result is not None:
        if (
            type(expected_result)
            is not reuse_v1.HeldoutOverlayAbstractReuseResultV1
            or expected_result.source is not source
            or expected_result.query != query
            or expected_result.plan.query != query
            or expected_result.plan.audit.model_id != query.quotient_model_id
        ):
            _fail("held-out stage-accounting frozen result changed")
        expected_result.result_id
        expected_result.plan.plan_id
    if not _PROCESS_LOCK.acquire(blocking=False):
        _fail("another held-out stage-accounting scope is active")
    token = None
    try:
        if owned_v1._ACTIVE_RUNTIME.get() is not None:  # noqa: SLF001
            _fail("another owner-bound accounting runtime is active")
        registry = registry_v6.official_counter_registry_v6()
        stage_profile = official_heldout_abstract_stage_profile_v1(registry)
        comparison = registry_v6.official_comparison_profile_v6(registry)
        actual = registry_v6.official_actual_projection_profile_v6(
            registry, comparison
        )
        manifest = official_heldout_abstract_operation_manifest_v1(
            registry, stage_profile
        )
        lifecycle = live_v3.open_construction_accounting_lifecycle_v3(
            subject_id=query.logical_occurrence_id,
            recorder_id=RECORDER_ID,
            stage_plan=tuple(_live_stage(item) for item in CANONICAL_STAGE_PLAN_V1),
            registry=registry,
            stage_profile=stage_profile,
            comparison_profile=comparison,
            actual_projection_profile=actual,
        )
        rows: list[live_v3.RecordedStageWorkV3] = []
        outputs = (
            (query.query_id,),
            (source.final_overlay.overlay_id,),
            (source.final_overlay.bridge.quotient_model.model_id,),
        )
        for stage, output_ids in zip(CANONICAL_STAGE_PLAN_V1[:3], outputs):
            active = lifecycle.begin_stage(_live_stage(stage))
            rows.append(active.complete(output_artifact_ids=output_ids))

        active = lifecycle.begin_stage(_live_stage(CANONICAL_STAGE_PLAN_V1[3]))
        hook = _HeldoutStageHookV1(active=active, manifest=manifest)
        token = owned_v1._ACTIVE_RUNTIME.set(hook)  # noqa: SLF001
        meter = _BusinessHashMeterV1()
        try:
            with meter:
                operational_audit = robust.solve_quotient_robust_h2_v1(
                    source.final_overlay.bridge.quotient_model,
                    source.threshold,
                )
        finally:
            owned_v1._ACTIVE_RUNTIME.reset(token)  # noqa: SLF001
            token = None
        if expected_result is None:
            result = reuse_v1.complete_heldout_overlay_abstract_reuse_v1(
                source, query, operational_audit
            )
        else:
            result = expected_result
            if (
                operational_audit != result.plan.audit
                or operational_audit.audit_id != result.plan.audit.audit_id
            ):
                _fail("owner-accounted quotient planner changed the frozen plan")
        hook.flush()
        rows.append(
            active.complete(
                output_artifact_ids=(operational_audit.audit_id, result.plan.plan_id)
            )
        )

        active = lifecycle.begin_stage(_live_stage(CANONICAL_STAGE_PLAN_V1[4]))
        active.add(
            "route.successes",
            1,
            operation_site_id=content_id(
                RESULT_DOMAIN,
                {
                    "role": "heldout-abstract-route-success",
                    "heldout_abstract_reuse_result_id": result.result_id,
                    "audit_id": operational_audit.audit_id,
                },
            ),
        )
        rows.append(active.complete(output_artifact_ids=(result.result_id,)))
        recorded = lifecycle.finish()
        if tuple(rows) != recorded:
            _fail("held-out accounting lifecycle replay changed")
        issued = HeldoutAbstractStageAccountingResultV1(
            result,
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
        return verify_heldout_abstract_stage_accounting_v1(issued)
    finally:
        if token is not None:
            owned_v1._ACTIVE_RUNTIME.reset(token)  # noqa: SLF001
        _PROCESS_LOCK.release()


def record_heldout_abstract_route_v1(
    result: reuse_v1.HeldoutOverlayAbstractReuseResultV1,
) -> HeldoutAbstractStageAccountingResultV1:
    """Replay and account an already frozen held-out plan."""

    if type(result) is not reuse_v1.HeldoutOverlayAbstractReuseResultV1:
        _fail("held-out stage accounting rejects a foreign result")
    return _record_heldout_abstract_query_v1(result.source, result.query, result)


def run_and_record_heldout_abstract_route_v1(
    source: source_v1.HeldoutCheckpointRecertificationResultV1,
    query: reuse_v1.HeldoutOverlayQueryV1,
) -> HeldoutAbstractStageAccountingResultV1:
    """Execute and account exactly one planner call for a frozen query."""

    return _record_heldout_abstract_query_v1(source, query, None)


def verify_heldout_abstract_stage_accounting_v1(
    result: HeldoutAbstractStageAccountingResultV1,
) -> HeldoutAbstractStageAccountingResultV1:
    if type(result) is not HeldoutAbstractStageAccountingResultV1:
        _fail("held-out stage-accounting verifier rejects foreign values")
    registry = registry_v6.official_counter_registry_v6()
    stage_profile = official_heldout_abstract_stage_profile_v1(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(registry, comparison)
    manifest = official_heldout_abstract_operation_manifest_v1(
        registry, stage_profile
    )
    result.reuse_result.result_id
    if (
        result.counter_registry_id != registry.registry_id
        or result.stage_profile_id != stage_profile.stage_profile_id
        or result.comparison_profile_id != comparison.comparison_profile_id
        or result.actual_projection_profile_id != actual.actual_projection_profile_id
        or result.operation_manifest_id != manifest.manifest_id
        or tuple(_stage(row.stage_start.stage_kind) for row in result.recorded_stages)
        != CANONICAL_STAGE_PLAN_V1
    ):
        _fail("held-out stage-accounting authority binding changed")
    for row in result.recorded_stages:
        live_v3.verify_recorded_stage_work_v3(
            row, registry, stage_profile, comparison, actual
        )
    result.__post_init__()
    return result


__all__ = (
    "ABSTRACT_OPERATION_PATHS",
    "CANONICAL_STAGE_PLAN_V1",
    "ConstructionK7HeldoutAbstractStageAccountingV1Error",
    "HeldoutAbstractOperationManifestV1",
    "HeldoutAbstractStageAccountingResultV1",
    "HeldoutAbstractStageProfileV1",
    "LOCAL_DOMAINS",
    "SHARED_PLACEHOLDER_PATHS",
    "official_heldout_abstract_operation_manifest_v1",
    "official_heldout_abstract_stage_profile_v1",
    "record_heldout_abstract_route_v1",
    "run_and_record_heldout_abstract_route_v1",
    "verify_heldout_abstract_stage_accounting_v1",
)
