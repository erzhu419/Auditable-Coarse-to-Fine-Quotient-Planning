"""Five-stage operation authority for the query-bound continuation.

This additive manifest reuses the already frozen acquisition/checkpoint owner
sites and adds the exact source-owned counters in the query-bound direct
fallback.  It authorizes stage-local construction evidence only.  In
particular, it does not claim that the nine occurrence-wide shared-resource
paths have been measured or that an occurrence WorkVector is complete.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import v075_k7_causal_promotion_operation_boundary_manifest_v4 as causal_v4
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as root_v3
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_ACCOUNTING_BOUNDARY_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_ACCOUNTING_MANIFEST_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.94"
PROFILE_KEY = "construction_k7_query_bound_accounting_manifest_v1"
BOUNDARY_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_ACCOUNTING_BOUNDARY_V1_DOMAIN
MANIFEST_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_ACCOUNTING_MANIFEST_V1_DOMAIN
LOCAL_DOMAINS = frozenset({BOUNDARY_DOMAIN, MANIFEST_DOMAIN})
if len(LOCAL_DOMAINS) != 2 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("query-bound accounting domains are not central")

_S = registry_v6.ConstructionStageKindV6
OPEN_STAGES = frozenset(
    {_S.OPEN_INCREMENTAL_ACQUISITION, _S.OPEN_CHECKPOINT_REPLANNING}
)
DIRECT_STAGE = _S.DIRECT_FALLBACK
EXPECTED_REUSED_OPEN_BOUNDARY_COUNT = 43
EXPECTED_QUERY_OPEN_BOUNDARY_COUNT = 3
EXPECTED_OPEN_BOUNDARY_COUNT = (
    EXPECTED_REUSED_OPEN_BOUNDARY_COUNT + EXPECTED_QUERY_OPEN_BOUNDARY_COUNT
)
EXPECTED_DIRECT_BOUNDARY_COUNT = 11
EXPECTED_BOUNDARY_COUNT = EXPECTED_OPEN_BOUNDARY_COUNT + EXPECTED_DIRECT_BOUNDARY_COUNT
_ISSUER = object()


class ConstructionK7QueryBoundAccountingManifestV1Error(ValueError):
    """The query-bound operation inventory or one authority changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundAccountingManifestV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundAccountingManifestV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _emittable(classification: Any) -> bool:
    value = getattr(classification, "value", classification)
    return type(value) is str and value.endswith("SCHEMA_ONLY") and "NATIVE_ZERO" not in value


@dataclass(frozen=True, slots=True)
class _DirectSpecV1:
    boundary_key: str
    dispatch_key: str
    target_path: str
    operation_source_symbol: str


@dataclass(frozen=True, slots=True)
class _OpenSpecV1:
    boundary_key: str
    dispatch_key: str
    target_path: str
    operation_source_symbol: str


_QUERY_OPEN_SPECS = (
    _OpenSpecV1(
        "query-replanning.validation-delta-replay",
        "batch-planning.query-delta.freeze",
        "build.open_checkpoint_batch_v2_typed_record_replays",
        "freeze_v075_query_bound_validation_delta_v2",
    ),
    _OpenSpecV1(
        "query-replanning.validation-outcome-projection",
        "batch-planning.query-delta.outcome-project",
        "build.open_checkpoint_outcome_projections",
        "compile_v075_query_bound_validation_overlay_v2",
    ),
    _OpenSpecV1(
        "query-replanning.validation-model-row-build",
        "batch-planning.query-delta.model-row-build",
        "build.open_checkpoint_model_rows_built",
        "compile_v075_query_bound_validation_overlay_v2",
    ),
)


_DIRECT_SPECS = (
    _DirectSpecV1(
        "query-fallback.action-evaluated",
        "query-fallback.action.evaluated",
        "fallback.actions_evaluated",
        "_QueryBoundFallbackLedgerV1.evaluate_action",
    ),
    _DirectSpecV1(
        "query-fallback.bellman-backup",
        "query-fallback.bellman.backup",
        "fallback.bellman_backups",
        "_QueryBoundFallbackLedgerV1.bellman_backup",
    ),
    _DirectSpecV1(
        "query-fallback.cap-check",
        "query-fallback.control.cap-check",
        "control.cap_checks",
        "_QueryBoundFallbackLedgerV1._guard",
    ),
    _DirectSpecV1(
        "query-fallback.cap-rejection",
        "query-fallback.control.cap-rejection",
        "control.cap_rejections",
        "_QueryBoundFallbackLedgerV1._guard",
    ),
    _DirectSpecV1(
        "query-fallback.ground-step",
        "query-fallback.kernel.transition",
        "fallback.ground_steps",
        "_QueryBoundFallbackLedgerV1.ground_step",
    ),
    _DirectSpecV1(
        "query-fallback.outcome-row",
        "query-fallback.outcome.row",
        "fallback.outcome_rows",
        "_QueryBoundFallbackLedgerV1.record_outcomes",
    ),
    _DirectSpecV1(
        "query-fallback.route-failure",
        "query-fallback.route.failure",
        "route.failures",
        "_QueryBoundFallbackLedgerV1.finish_route",
    ),
    _DirectSpecV1(
        "query-fallback.route-success",
        "query-fallback.route.success",
        "route.successes",
        "_QueryBoundFallbackLedgerV1.finish_route",
    ),
    _DirectSpecV1(
        "query-fallback.solver-failure",
        "query-fallback.solver.failure",
        "solver.failures",
        "_QueryBoundFallbackLedgerV1.finish_solver",
    ),
    _DirectSpecV1(
        "query-fallback.solver-success",
        "query-fallback.solver.success",
        "solver.successes",
        "_QueryBoundFallbackLedgerV1.finish_solver",
    ),
    _DirectSpecV1(
        "query-fallback.state-expanded",
        "query-fallback.state.expanded",
        "fallback.states_expanded",
        "_QueryBoundFallbackLedgerV1.expand_state",
    ),
)


@dataclass(frozen=True, slots=True)
class QueryBoundAccountingOperationBoundaryV1:
    _issuer: object = field(repr=False, compare=False)
    predecessor_boundary_id: str | None
    boundary_key: str
    dispatch_key: str
    stage: registry_v6.ConstructionStageKindV6
    classification: root_v3.OperationBoundaryClassificationV3
    target_path: str
    registered_owner: str
    reducer: ReducerEnum
    operation_source_module: str
    operation_source_symbol: str
    count_rule: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("query-bound accounting boundary is caller-minted")
        if self.predecessor_boundary_id is not None:
            _cid(self.predecessor_boundary_id, "predecessor boundary")
        try:
            object.__setattr__(self, "stage", _S(self.stage))
            object.__setattr__(
                self,
                "classification",
                root_v3.OperationBoundaryClassificationV3(self.classification),
            )
            object.__setattr__(self, "reducer", ReducerEnum(self.reducer))
        except (TypeError, ValueError) as error:
            raise ConstructionK7QueryBoundAccountingManifestV1Error(
                "query-bound boundary enum changed"
            ) from error
        if (
            self.stage not in OPEN_STAGES | {DIRECT_STAGE}
            or not _emittable(self.classification)
            or self.reducer is not ReducerEnum.SUM
            or not all(
                type(value) is str and value
                for value in (
                    self.boundary_key,
                    self.dispatch_key,
                    self.target_path,
                    self.registered_owner,
                    self.operation_source_module,
                    self.operation_source_symbol,
                    self.count_rule,
                )
            )
        ):
            _fail("query-bound accounting boundary is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_accounting_boundary.v1",
            "schema_version": SCHEMA_VERSION,
            "predecessor_boundary_id": self.predecessor_boundary_id,
            "boundary_key": self.boundary_key,
            "dispatch_key": self.dispatch_key,
            "stage": self.stage.value,
            "classification": self.classification.value,
            "target_path": self.target_path,
            "registered_owner": self.registered_owner,
            "reducer": self.reducer.value,
            "operation_source_module": self.operation_source_module,
            "operation_source_symbol": self.operation_source_symbol,
            "count_rule": self.count_rule,
            "unit_amount_source_hook": True,
            "stage_local_only": True,
        }

    @property
    def boundary_id(self) -> str:
        return content_id(BOUNDARY_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "boundary_id": self.boundary_id}


@dataclass(frozen=True, slots=True)
class QueryBoundAccountingOperationManifestV1:
    _issuer: object = field(repr=False, compare=False)
    predecessor_manifest_id: str
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    boundaries: tuple[QueryBoundAccountingOperationBoundaryV1, ...]

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("query-bound accounting manifest is caller-minted")
        for value, label in (
            (self.predecessor_manifest_id, "predecessor manifest"),
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.comparison_profile_id, "comparison profile"),
            (self.actual_projection_profile_id, "projection profile"),
        ):
            _cid(value, label)
        if (
            type(self.boundaries) is not tuple
            or len(self.boundaries) != EXPECTED_BOUNDARY_COUNT
            or tuple(sorted(self.boundaries, key=lambda row: row.boundary_key))
            != self.boundaries
            or len({row.boundary_key for row in self.boundaries})
            != len(self.boundaries)
            or len({(row.stage, row.dispatch_key) for row in self.boundaries})
            != len(self.boundaries)
        ):
            _fail("query-bound accounting manifest inventory changed")

    @property
    def by_key(self) -> Mapping[str, QueryBoundAccountingOperationBoundaryV1]:
        return MappingProxyType({row.boundary_key: row for row in self.boundaries})

    def _payload(self) -> dict[str, Any]:
        open_count = sum(row.stage in OPEN_STAGES for row in self.boundaries)
        direct_count = sum(row.stage is DIRECT_STAGE for row in self.boundaries)
        return {
            "schema": "acfqp.construction_k7_query_bound_accounting_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "predecessor_manifest_id": self.predecessor_manifest_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "stage_plan": [
                _S.OPEN_INCREMENTAL_ACQUISITION.value,
                _S.OPEN_CHECKPOINT_REPLANNING.value,
                _S.OPEN_INCREMENTAL_ACQUISITION.value,
                _S.OPEN_CHECKPOINT_REPLANNING.value,
                _S.DIRECT_FALLBACK.value,
            ],
            "boundaries": [row.to_document() for row in self.boundaries],
            "boundary_count": len(self.boundaries),
            "reused_open_boundary_count": EXPECTED_REUSED_OPEN_BOUNDARY_COUNT,
            "query_specific_open_boundary_count": (
                open_count - EXPECTED_REUSED_OPEN_BOUNDARY_COUNT
            ),
            "query_direct_fallback_boundary_count": direct_count,
            "owner_code_identity_checked_when_runtime_activates": True,
            "complete_source_ast_closure_present": False,
            "all_reachable_operation_sites_complete": False,
            "stage_local_counter_chain_authorized": True,
            "shared_resource_receipts_present": False,
            "occurrence_work_vector_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def manifest_id(self) -> str:
        return content_id(MANIFEST_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}

    def validate_official(self) -> None:
        if self != _expected_manifest():
            _fail("official query-bound accounting manifest changed")


def _expected_manifest() -> QueryBoundAccountingOperationManifestV1:
    predecessor = causal_v4.official_k7_causal_promotion_operation_boundary_manifest_v4()
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(registry, comparison)
    rows: list[QueryBoundAccountingOperationBoundaryV1] = []
    for prior in predecessor.boundaries:
        if prior.stage not in OPEN_STAGES or not _emittable(prior.classification):
            continue
        rows.append(
            QueryBoundAccountingOperationBoundaryV1(
                _ISSUER,
                prior.boundary_id,
                prior.boundary_key,
                prior.dispatch_key,
                prior.stage,
                prior.classification,
                prior.target_path,
                prior.registered_owner,
                prior.reducer,
                prior.operation_source_module,
                prior.operation_source_symbol,
                prior.count_rule,
            )
        )
    allowed_open = set(
        stage.by_stage[_S.OPEN_CHECKPOINT_REPLANNING].allowed_nonzero_paths
    )
    for spec in _QUERY_OPEN_SPECS:
        leaf = registry.by_path.get(spec.target_path)
        if (
            leaf is None
            or spec.target_path not in allowed_open
            or leaf.reducer is not ReducerEnum.SUM
        ):
            _fail("query-bound replanning boundary lost its V6 leaf")
        rows.append(
            QueryBoundAccountingOperationBoundaryV1(
                _ISSUER,
                None,
                spec.boundary_key,
                spec.dispatch_key,
                _S.OPEN_CHECKPOINT_REPLANNING,
                root_v3.OperationBoundaryClassificationV3.V6_NATIVE_BOUNDARY_SCHEMA_ONLY,
                spec.target_path,
                leaf.owner,
                leaf.reducer,
                "acfqp.v075_batch_native_planning_backend_v2",
                spec.operation_source_symbol,
                "COUNT_EACH_EXACT_QUERY_DELTA_OPERATION",
            )
        )
    allowed_direct = set(stage.by_stage[DIRECT_STAGE].allowed_nonzero_paths)
    for spec in _DIRECT_SPECS:
        leaf = registry.by_path.get(spec.target_path)
        if (
            leaf is None
            or spec.target_path not in allowed_direct
            or leaf.reducer is not ReducerEnum.SUM
        ):
            _fail("query-bound fallback boundary lost its V6 leaf")
        rows.append(
            QueryBoundAccountingOperationBoundaryV1(
                _ISSUER,
                None,
                spec.boundary_key,
                spec.dispatch_key,
                DIRECT_STAGE,
                root_v3.OperationBoundaryClassificationV3.V6_NATIVE_BOUNDARY_SCHEMA_ONLY,
                spec.target_path,
                leaf.owner,
                leaf.reducer,
                "acfqp.construction_k7_query_bound_direct_ground_fallback_v1",
                spec.operation_source_symbol,
                "COUNT_EACH_EXACT_SOURCE_OWNED_UNIT_OPERATION",
            )
        )
    result = QueryBoundAccountingOperationManifestV1(
        _ISSUER,
        predecessor.manifest_id,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        actual.actual_projection_profile_id,
        tuple(sorted(rows, key=lambda row: row.boundary_key)),
    )
    if (
        sum(row.stage in OPEN_STAGES for row in result.boundaries)
        != EXPECTED_OPEN_BOUNDARY_COUNT
        or sum(row.stage is DIRECT_STAGE for row in result.boundaries)
        != EXPECTED_DIRECT_BOUNDARY_COUNT
    ):
        _fail("query-bound accounting boundary cardinality changed")
    return result


def official_query_bound_accounting_operation_manifest_v1(
) -> QueryBoundAccountingOperationManifestV1:
    result = _expected_manifest()
    result.validate_official()
    return result


__all__ = (
    "ConstructionK7QueryBoundAccountingManifestV1Error",
    "EXPECTED_BOUNDARY_COUNT",
    "EXPECTED_DIRECT_BOUNDARY_COUNT",
    "EXPECTED_OPEN_BOUNDARY_COUNT",
    "EXPECTED_QUERY_OPEN_BOUNDARY_COUNT",
    "EXPECTED_REUSED_OPEN_BOUNDARY_COUNT",
    "LOCAL_DOMAINS",
    "OPEN_STAGES",
    "PROFILE_KEY",
    "QueryBoundAccountingOperationBoundaryV1",
    "QueryBoundAccountingOperationManifestV1",
    "official_query_bound_accounting_operation_manifest_v1",
)
