"""Owner-bound operation catalogue for the recovery-eligible H=2 loop.

The established query-bound catalogue describes two local transactions.  This
additive profile keeps its audited acquisition/replanning owner sites, changes
only the direct-fallback owner to the recovery-eligible runner, and freezes the
actual three-stage path used here.  It authorizes native stage evidence, not
the nine occurrence-wide shared-resource receipts or an official Gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_query_bound_accounting_manifest_v1 as prior_v1
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as root_v3
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_ACCOUNTING_BOUNDARY_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_ACCOUNTING_MANIFEST_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.114"
PROFILE_KEY = "construction_k7_recovery_eligible_accounting_manifest_v1"
BOUNDARY_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_ACCOUNTING_BOUNDARY_V1_DOMAIN
MANIFEST_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_ACCOUNTING_MANIFEST_V1_DOMAIN
LOCAL_DOMAINS = frozenset({BOUNDARY_DOMAIN, MANIFEST_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("recovery-eligible accounting domains are not central")

_S = registry_v6.ConstructionStageKindV6
OPEN_ACQUISITION = _S.OPEN_INCREMENTAL_ACQUISITION
OPEN_REPLANNING = _S.OPEN_CHECKPOINT_REPLANNING
DIRECT_FALLBACK = _S.DIRECT_FALLBACK
CANONICAL_STAGE_PLAN_V1 = (
    OPEN_ACQUISITION,
    OPEN_REPLANNING,
    DIRECT_FALLBACK,
)
_ISSUER = object()


class ConstructionK7RecoveryEligibleAccountingManifestV1Error(ValueError):
    """The operation source, owner, path, or stage changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RecoveryEligibleAccountingManifestV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligibleAccountingManifestV1Error(
            f"{label} must be one content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class RecoveryEligibleAccountingBoundaryV1:
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
            _fail("recovery accounting boundary is caller-minted")
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
            raise ConstructionK7RecoveryEligibleAccountingManifestV1Error(
                "recovery accounting boundary enum changed"
            ) from error
        if (
            self.stage not in set(CANONICAL_STAGE_PLAN_V1)
            or self.reducer is not ReducerEnum.SUM
            or not self.classification.value.endswith("SCHEMA_ONLY")
            or "NATIVE_ZERO" in self.classification.value
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
            _fail("recovery accounting boundary is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_accounting_boundary.v1",
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
class _DirectSpecV1:
    boundary_key: str
    dispatch_key: str
    target_path: str
    operation_source_symbol: str


_DIRECT_SPECS = (
    _DirectSpecV1(
        "recovery-fallback-action-evaluated",
        "query-fallback.action.evaluated",
        "fallback.actions_evaluated",
        "_FallbackLedger.evaluate_action",
    ),
    _DirectSpecV1(
        "recovery-fallback-bellman-backup",
        "query-fallback.bellman.backup",
        "fallback.bellman_backups",
        "_FallbackLedger.bellman_backup",
    ),
    _DirectSpecV1(
        "recovery-fallback-cap-check",
        "query-fallback.control.cap-check",
        "control.cap_checks",
        "_FallbackLedger._guard",
    ),
    _DirectSpecV1(
        "recovery-fallback-cap-rejection",
        "query-fallback.control.cap-rejection",
        "control.cap_rejections",
        "_FallbackLedger._guard",
    ),
    _DirectSpecV1(
        "recovery-fallback-ground-step",
        "query-fallback.kernel.transition",
        "fallback.ground_steps",
        "_FallbackLedger.ground_step",
    ),
    _DirectSpecV1(
        "recovery-fallback-outcome-row",
        "query-fallback.outcome.row",
        "fallback.outcome_rows",
        "_FallbackLedger.record_outcomes",
    ),
    _DirectSpecV1(
        "recovery-fallback-state-expanded",
        "query-fallback.state.expanded",
        "fallback.states_expanded",
        "_FallbackLedger.expand_state",
    ),
)


@dataclass(frozen=True, slots=True)
class RecoveryEligibleAccountingManifestV1:
    _issuer: object = field(repr=False, compare=False)
    predecessor_manifest_id: str
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    boundaries: tuple[RecoveryEligibleAccountingBoundaryV1, ...]

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("recovery accounting manifest is caller-minted")
        for value, label in (
            (self.predecessor_manifest_id, "predecessor manifest"),
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.comparison_profile_id, "comparison profile"),
            (self.actual_projection_profile_id, "projection profile"),
        ):
            _cid(value, label)
        if (
            not self.boundaries
            or tuple(sorted(self.boundaries, key=lambda row: row.boundary_key))
            != self.boundaries
            or len({row.boundary_key for row in self.boundaries})
            != len(self.boundaries)
            or len({(row.stage, row.dispatch_key) for row in self.boundaries})
            != len(self.boundaries)
        ):
            _fail("recovery accounting manifest inventory changed")

    @property
    def by_key(self) -> Mapping[str, RecoveryEligibleAccountingBoundaryV1]:
        return MappingProxyType({row.boundary_key: row for row in self.boundaries})

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_accounting_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "predecessor_manifest_id": self.predecessor_manifest_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "stage_plan": [item.value for item in CANONICAL_STAGE_PLAN_V1],
            "boundaries": [row.to_document() for row in self.boundaries],
            "boundary_count": len(self.boundaries),
            "open_boundary_count": sum(
                row.stage in {OPEN_ACQUISITION, OPEN_REPLANNING}
                for row in self.boundaries
            ),
            "direct_fallback_boundary_count": sum(
                row.stage is DIRECT_FALLBACK for row in self.boundaries
            ),
            "fallback_route_solver_reconciliation_semantically_derived": True,
            "owner_code_identity_checked_when_runtime_activates": True,
            "native_stage_counter_chain_authorized": True,
            "nine_shared_resource_receipts_present": False,
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
            _fail("official recovery accounting manifest changed")


def _expected_manifest() -> RecoveryEligibleAccountingManifestV1:
    prior = prior_v1.official_query_bound_accounting_operation_manifest_v1()
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(registry, comparison)
    rows = [
        RecoveryEligibleAccountingBoundaryV1(
            _ISSUER,
            item.boundary_id,
            item.boundary_key,
            item.dispatch_key,
            item.stage,
            item.classification,
            item.target_path,
            item.registered_owner,
            item.reducer,
            item.operation_source_module,
            item.operation_source_symbol,
            item.count_rule,
        )
        for item in prior.boundaries
        if item.stage in {OPEN_ACQUISITION, OPEN_REPLANNING}
    ]
    allowed = set(stage.by_stage[DIRECT_FALLBACK].allowed_nonzero_paths)
    for spec in _DIRECT_SPECS:
        leaf = registry.by_path.get(spec.target_path)
        if (
            leaf is None
            or spec.target_path not in allowed
            or leaf.reducer is not ReducerEnum.SUM
        ):
            _fail("recovery fallback boundary lost its V6 leaf")
        rows.append(
            RecoveryEligibleAccountingBoundaryV1(
                _ISSUER,
                None,
                spec.boundary_key,
                spec.dispatch_key,
                DIRECT_FALLBACK,
                root_v3.OperationBoundaryClassificationV3.V6_NATIVE_BOUNDARY_SCHEMA_ONLY,
                spec.target_path,
                leaf.owner,
                leaf.reducer,
                "acfqp.construction_k7_recovery_eligible_direct_ground_fallback_v1",
                spec.operation_source_symbol,
                "COUNT_EACH_EXACT_SOURCE_OWNED_UNIT_OPERATION",
            )
        )
    result = RecoveryEligibleAccountingManifestV1(
        _ISSUER,
        prior.manifest_id,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        actual.actual_projection_profile_id,
        tuple(sorted(rows, key=lambda row: row.boundary_key)),
    )
    if (
        len(result.boundaries) != 53
        or result._payload()["open_boundary_count"] != 46
        or result._payload()["direct_fallback_boundary_count"] != 7
    ):
        _fail("recovery accounting boundary cardinality changed")
    return result


def official_recovery_eligible_accounting_manifest_v1(
) -> RecoveryEligibleAccountingManifestV1:
    result = _expected_manifest()
    result.validate_official()
    return result


__all__ = (
    "CANONICAL_STAGE_PLAN_V1",
    "ConstructionK7RecoveryEligibleAccountingManifestV1Error",
    "LOCAL_DOMAINS",
    "RecoveryEligibleAccountingBoundaryV1",
    "RecoveryEligibleAccountingManifestV1",
    "official_recovery_eligible_accounting_manifest_v1",
)
