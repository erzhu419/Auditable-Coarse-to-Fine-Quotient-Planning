"""Additive V5 registry for the currently known K7 owner gaps.

V4 is immutable.  The strict source-owner audit showed that the K7 V2 path
executes batch-native compiler/planner work and a dynamic-child audit that
cannot be charged to similarly named learned-support, semantic-instrumentation
or generic abstract-planner leaves.  This successor preserves every V4 leaf
document exactly and appends 27 owner-specific operational leaves.

This is a schema-only, minimal *known-gap* closure.  It installs no operation
hook, emits no work evidence, and does not claim that hash/check/I/O/process,
peak, formula, terminal, route, occurrence, campaign, or all-path accounting
is complete.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acfqp.accounting_v1 import (
    NONKERNEL_COMPUTE_EVENTS,
    SHARED_AXES,
    ComparisonAxisV1,
    CounterSemanticsV1,
    LaneEnum,
    ProjectionTermV1,
    ReducerEnum,
    official_shared_axes_v1,
)
from acfqp import construction_accounting_registry_v4 as v4
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V5_DOMAIN,
    CONSTRUCTION_COMPARISON_PROFILE_V5_DOMAIN,
    CONSTRUCTION_COUNTER_REGISTRY_V5_DOMAIN,
    CONSTRUCTION_STAGE_PROFILE_V5_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "5.0.0"
COUNTER_REGISTRY_KEY = "acfqp_counter_registry_v5"
STAGE_PROFILE_KEY = "construction_stage_exclusivity_v5"
COMPARISON_PROFILE_KEY = "comparison_profile_shared_resources_v5"
ACTUAL_PROJECTION_PROFILE_KEY = "actual_projection_construction_v5"

EXPECTED_V4_LEAF_COUNT = 124
EXPECTED_V4_OPERATIONAL_LEAF_COUNT = 106
EXPECTED_V4_REQUIRED_LEAF_COUNT = 117
EXPECTED_V5_ADDITION_COUNT = 27
EXPECTED_V5_LEAF_COUNT = 151
EXPECTED_V5_OPERATIONAL_LEAF_COUNT = 133
EXPECTED_V5_REQUIRED_LEAF_COUNT = 144
EXPECTED_V5_STAGE_COUNT = 10


class ConstructionAccountingRegistryV5Error(ValueError):
    """The additive V5 registry or one of its profiles is invalid."""


ConstructionStageKindV5 = v4.ConstructionStageKindV4


def _operational(
    path: str,
    semantics_id: str,
    owner: str,
    unit: str,
    scope: str,
) -> CounterSemanticsV1:
    return CounterSemanticsV1(
        path=path,
        semantics_id=semantics_id,
        owner=owner,
        unit=unit,
        lane=LaneEnum.OPERATIONAL,
        scope=scope,
        reducer=ReducerEnum.SUM,
        comparison_axis=NONKERNEL_COMPUTE_EVENTS,
        required=True,
    )


_BATCH_FAMILIES = (
    (
        "typed_record_replays",
        "typed-record-replay",
        "typed_record_replays",
    ),
    (
        "row_behaviors_compiled",
        "row-behavior-compile",
        "row_behaviors",
    ),
    (
        "quotient_cells_compiled",
        "quotient-cell-compile",
        "quotient_cells",
    ),
    (
        "semantic_options_compiled",
        "semantic-option-compile",
        "semantic_options",
    ),
    (
        "concretizer_ground_actions_bound",
        "concretizer-ground-action-bind",
        "ground_actions",
    ),
    (
        "interval_greedy_allocation_steps",
        "interval-greedy-allocation-step",
        "greedy_allocation_steps",
    ),
    (
        "policy_order_comparisons",
        "policy-order-comparison",
        "comparisons",
    ),
    (
        "frontier_obligations_built",
        "frontier-obligation-build",
        "frontier_obligations",
    ),
    (
        "support_descriptors_compiled",
        "support-descriptor-compile",
        "support_descriptors",
    ),
)


def _batch_additions(
    *,
    path_prefix: str,
    semantics_suffix: str,
    scope: str,
) -> tuple[CounterSemanticsV1, ...]:
    return tuple(
        _operational(
            (
                "build.initial_live_model_support_descriptors_compiled"
                if semantics_suffix == "initial-build"
                and path_suffix == "support_descriptors_compiled"
                else f"{path_prefix}_batch_v2_{path_suffix}"
            ),
            (
                "v075-live-model-support-descriptor-compile-v5-initial-build"
                if semantics_suffix == "initial-build"
                and path_suffix == "support_descriptors_compiled"
                else (
                    f"v075-batch-v2-{semantic_family}-v5-"
                    f"{semantics_suffix}"
                )
            ),
            (
                "v075_live_incremental_model_authority_v2"
                if semantics_suffix == "initial-build"
                and path_suffix == "support_descriptors_compiled"
                else "v075_batch_native_planning_backend_v2"
            ),
            unit,
            scope,
        )
        for path_suffix, semantic_family, unit in _BATCH_FAMILIES
    )


def _v5_additions() -> tuple[CounterSemanticsV1, ...]:
    initial_scope = "construction_occurrence_initial_build_epoch"
    failed_scope = "construction_occurrence_failed_abstract_prefix"
    closed_scope = (
        "construction_occurrence_closed_reconciliation_and_terminalization"
    )
    initial = _batch_additions(
        path_prefix="build.initial",
        semantics_suffix="initial-build",
        scope=initial_scope,
    )
    closed = _batch_additions(
        path_prefix="closure.reconciliation",
        semantics_suffix="closed-reconciliation",
        scope=closed_scope,
    )
    dynamic = (
        _operational(
            "audit.dynamic_root_rows_scanned",
            "v075-dynamic-root-row-scan-v5-failed-abstract-audit",
            "v075_live_dynamic_acquisition_authority_v2",
            "root_rows",
            failed_scope,
        ),
        _operational(
            "audit.dynamic_support_descriptors_scanned",
            "v075-dynamic-support-descriptor-scan-v5-failed-abstract-audit",
            "v075_live_dynamic_acquisition_authority_v2",
            "support_descriptors",
            failed_scope,
        ),
        _operational(
            "audit.dynamic_causal_edges_built",
            "v075-dynamic-causal-edge-build-v5-failed-abstract-audit",
            "v075_live_dynamic_acquisition_authority_v2",
            "causal_edges",
            failed_scope,
        ),
        _operational(
            "audit.dynamic_child_action_rows_built",
            "v075-dynamic-child-action-row-build-v5-failed-abstract-audit",
            "v075_live_dynamic_acquisition_authority_v2",
            "child_action_rows",
            failed_scope,
        ),
        _operational(
            "audit.dynamic_row_cap_checks",
            "v075-dynamic-child-row-cap-check-v5-failed-abstract-audit",
            "v075_live_dynamic_acquisition_authority_v2",
            "cap_checks",
            failed_scope,
        ),
        _operational(
            "audit.dynamic_child_closure_attestations",
            "v075-dynamic-child-closure-attestation-v5-failed-abstract-audit",
            "v075_live_dynamic_acquisition_authority_v2",
            "attestations",
            failed_scope,
        ),
    )
    corrections = (
        _operational(
            "build.initial_live_model_outcome_projections",
            "v075-live-model-outcome-projection-v5-initial-build",
            "v075_live_incremental_model_authority_v2",
            "outcome_projections",
            initial_scope,
        ),
        _operational(
            "closure.reconciliation_batch_v2_model_rows_built",
            "v075-batch-v2-model-row-build-v5-closed-reconciliation",
            "v075_batch_native_planning_backend_v2",
            "model_rows",
            closed_scope,
        ),
        _operational(
            "closure.reconciliation_batch_v2_row_evidence_bindings_built",
            "v075-batch-v2-row-evidence-binding-build-v5-closed-reconciliation",
            "v075_batch_native_planning_backend_v2",
            "row_evidence_bindings",
            closed_scope,
        ),
    )
    result = tuple(sorted((*initial, *closed, *dynamic, *corrections), key=lambda row: row.path))
    if len(result) != EXPECTED_V5_ADDITION_COUNT:
        raise ConstructionAccountingRegistryV5Error(
            "V5 known-owner additions changed cardinality"
        )
    return result


@dataclass(frozen=True, slots=True)
class CounterRegistryV5:
    registry_key: str
    schema_version: str
    v4_registry_id: str
    leaves: tuple[CounterSemanticsV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.v4_registry_id)
        if (
            self.registry_key != COUNTER_REGISTRY_KEY
            or self.schema_version != SCHEMA_VERSION
            or tuple(sorted(self.leaves, key=lambda row: row.path))
            != self.leaves
            or len({row.path for row in self.leaves}) != len(self.leaves)
        ):
            raise ConstructionAccountingRegistryV5Error(
                "V5 counter registry shape changed"
            )

    @property
    def by_path(self) -> dict[str, CounterSemanticsV1]:
        return {row.path: row for row in self.leaves}

    @property
    def operational_leaves(self) -> tuple[CounterSemanticsV1, ...]:
        return tuple(
            row for row in self.leaves if row.lane is LaneEnum.OPERATIONAL
        )

    @property
    def required_paths(self) -> tuple[str, ...]:
        return tuple(row.path for row in self.leaves if row.required)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.counter_registry.v5",
            "schema_version": self.schema_version,
            "counter_registry_key": self.registry_key,
            "v4_registry_id": self.v4_registry_id,
            "leaves": [row.to_dict() for row in self.leaves],
            "v4_prefix_preserved_exactly": True,
            "known_owner_gap_addition_count": EXPECTED_V5_ADDITION_COUNT,
            "greedy_allocation_event_boundary_schema_frozen": True,
            "runtime_greedy_allocation_instrumented": False,
            "support_descriptor_compile_distinct_from_typed_replay": True,
            "v4_owner_mismatch_paths_native_zero_on_registered_k7_path": True,
            "minimal_known_owner_gap_closure_only": True,
            "operation_family_completeness_claimed": False,
            "runtime_owner_match_verified": False,
            "runtime_stage_attribution_verified": False,
            "operation_event_boundary_profile_complete": False,
            "native_zero_required_when_registered_path_did_not_execute": True,
        }

    @property
    def registry_id(self) -> str:
        return content_id(
            CONSTRUCTION_COUNTER_REGISTRY_V5_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counter_registry_id": self.registry_id}

    def validate_official_catalogue(self) -> None:
        if self != _expected_registry_v5():
            raise ConstructionAccountingRegistryV5Error(
                "official V5 counter catalogue changed"
            )


def _expected_registry_v5() -> CounterRegistryV5:
    base = v4.official_counter_registry_v4()
    base.validate_official_catalogue()
    additions = _v5_additions()
    if (
        len(base.leaves) != EXPECTED_V4_LEAF_COUNT
        or len(base.operational_leaves) != EXPECTED_V4_OPERATIONAL_LEAF_COUNT
        or len(base.required_paths) != EXPECTED_V4_REQUIRED_LEAF_COUNT
        or set(base.by_path) & {row.path for row in additions}
        or any(
            row.lane is not LaneEnum.OPERATIONAL
            or row.reducer is not ReducerEnum.SUM
            or row.comparison_axis != NONKERNEL_COMPUTE_EVENTS
            or not row.required
            for row in additions
        )
    ):
        raise ConstructionAccountingRegistryV5Error(
            "V4 prefix or V5 additive catalogue changed"
        )
    return CounterRegistryV5(
        COUNTER_REGISTRY_KEY,
        SCHEMA_VERSION,
        base.registry_id,
        tuple(sorted((*base.leaves, *additions), key=lambda row: row.path)),
    )


def official_counter_registry_v5() -> CounterRegistryV5:
    result = _expected_registry_v5()
    if (
        len(result.leaves) != EXPECTED_V5_LEAF_COUNT
        or len(result.operational_leaves)
        != EXPECTED_V5_OPERATIONAL_LEAF_COUNT
        or len(result.required_paths) != EXPECTED_V5_REQUIRED_LEAF_COUNT
    ):
        raise ConstructionAccountingRegistryV5Error(
            "V5 registry cardinality changed"
        )
    return result


def _addition_stage_by_path() -> dict[str, ConstructionStageKindV5]:
    result: dict[str, ConstructionStageKindV5] = {}
    for row in _v5_additions():
        if row.path.startswith("build.initial"):
            stage = ConstructionStageKindV5.INITIAL_MODEL_BUILD
        elif row.path.startswith("audit.dynamic"):
            stage = ConstructionStageKindV5.FAILED_ABSTRACT_PREFIX
        elif row.path.startswith("closure.reconciliation"):
            stage = (
                ConstructionStageKindV5
                .CLOSED_RECONCILIATION_AND_TERMINALIZATION
            )
        else:  # pragma: no cover - guarded by the frozen catalogue
            raise ConstructionAccountingRegistryV5Error(
                "V5 addition has no exact stage owner"
            )
        result[row.path] = stage
    return result


@dataclass(frozen=True, slots=True)
class StageRuleV5:
    stage_kind: ConstructionStageKindV5
    allowed_nonzero_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        try:
            selected = ConstructionStageKindV5(self.stage_kind)
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingRegistryV5Error(
                f"unknown construction stage {self.stage_kind!r}"
            ) from error
        object.__setattr__(self, "stage_kind", selected)
        if (
            tuple(sorted(self.allowed_nonzero_paths))
            != self.allowed_nonzero_paths
            or len(set(self.allowed_nonzero_paths))
            != len(self.allowed_nonzero_paths)
        ):
            raise ConstructionAccountingRegistryV5Error(
                "V5 stage paths must be unique and sorted"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "stage_kind": self.stage_kind.value,
            "allowed_nonzero_paths": list(self.allowed_nonzero_paths),
        }


def _expected_stage_rules_v5(
    registry: CounterRegistryV5,
) -> tuple[StageRuleV5, ...]:
    base = v4.official_stage_profile_v4()
    ownership = _addition_stage_by_path()
    rules = tuple(
        StageRuleV5(
            row.stage_kind,
            tuple(
                sorted(
                    set(row.allowed_nonzero_paths)
                    | {
                        path
                        for path, stage in ownership.items()
                        if stage is row.stage_kind
                    }
                )
            ),
        )
        for row in base.rules
    )
    if set(ownership) != {row.path for row in _v5_additions()} or any(
        not set(row.allowed_nonzero_paths) <= set(registry.required_paths)
        for row in rules
    ):
        raise ConstructionAccountingRegistryV5Error(
            "V5 stage ownership is incomplete"
        )
    return rules


@dataclass(frozen=True, slots=True)
class StageProfileV5:
    counter_registry_id: str
    v4_stage_profile_id: str
    rules: tuple[StageRuleV5, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        parse_content_id(self.v4_stage_profile_id)
        if (
            len(self.rules) != EXPECTED_V5_STAGE_COUNT
            or tuple(sorted(self.rules, key=lambda row: row.stage_kind.value))
            != self.rules
            or {row.stage_kind for row in self.rules}
            != set(ConstructionStageKindV5)
        ):
            raise ConstructionAccountingRegistryV5Error(
                "V5 stage profile must cover each stage exactly once"
            )

    @property
    def by_stage(self) -> dict[ConstructionStageKindV5, StageRuleV5]:
        return {row.stage_kind: row for row in self.rules}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_stage_profile.v5",
            "schema_version": SCHEMA_VERSION,
            "profile_key": STAGE_PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "v4_stage_profile_id": self.v4_stage_profile_id,
            "rules": [row.to_document() for row in self.rules],
            "v4_stage_ownership_preserved_exactly": True,
            "batch_v2_initial_and_closed_stage_assignment_schema_frozen": True,
            "dynamic_child_failed_prefix_assignment_schema_frozen": True,
            "owner_correction_stage_assignment_schema_frozen": True,
            "runtime_owner_match_verified": False,
            "runtime_stage_attribution_verified": False,
        }

    @property
    def stage_profile_id(self) -> str:
        return content_id(
            CONSTRUCTION_STAGE_PROFILE_V5_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "stage_profile_id": self.stage_profile_id}

    def validate(self, registry: CounterRegistryV5) -> None:
        registry.validate_official_catalogue()
        base = v4.official_stage_profile_v4()
        if (
            self.counter_registry_id != registry.registry_id
            or self.v4_stage_profile_id != base.stage_profile_id
            or self.rules != _expected_stage_rules_v5(registry)
        ):
            raise ConstructionAccountingRegistryV5Error(
                "official V5 stage profile changed"
            )


def official_stage_profile_v5(
    registry: CounterRegistryV5 | None = None,
) -> StageProfileV5:
    selected = registry or official_counter_registry_v5()
    base = v4.official_stage_profile_v4()
    result = StageProfileV5(
        selected.registry_id,
        base.stage_profile_id,
        _expected_stage_rules_v5(selected),
    )
    result.validate(selected)
    return result


@dataclass(frozen=True, slots=True)
class ComparisonProfileV5:
    counter_registry_id: str
    axes: tuple[ComparisonAxisV1, ...]
    terms: tuple[ProjectionTermV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        if tuple(row.name for row in self.axes) != SHARED_AXES:
            raise ConstructionAccountingRegistryV5Error(
                "V5 comparison axes changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.comparison_profile.v5",
            "schema_version": SCHEMA_VERSION,
            "profile_key": COMPARISON_PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "axes": [row.to_dict() for row in self.axes],
            "terms": [row.to_dict() for row in self.terms],
            "scalar_cost_defined": False,
        }

    @property
    def comparison_profile_id(self) -> str:
        return content_id(
            CONSTRUCTION_COMPARISON_PROFILE_V5_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "comparison_profile_id": self.comparison_profile_id,
        }

    def validate(self, registry: CounterRegistryV5) -> None:
        registry.validate_official_catalogue()
        expected = tuple(
            ProjectionTermV1(
                row.path,
                row.comparison_axis,
                1,
                row.lane,
                row.semantics_id,
                row.reducer,
            )
            for row in registry.operational_leaves
        )
        if (
            self.counter_registry_id != registry.registry_id
            or self.axes != official_shared_axes_v1()
            or self.terms != expected
            or len({row.source_leaf for row in self.terms})
            != len(self.terms)
        ):
            raise ConstructionAccountingRegistryV5Error(
                "official V5 comparison profile changed"
            )


def official_comparison_profile_v5(
    registry: CounterRegistryV5 | None = None,
) -> ComparisonProfileV5:
    selected = registry or official_counter_registry_v5()
    result = ComparisonProfileV5(
        selected.registry_id,
        official_shared_axes_v1(),
        tuple(
            ProjectionTermV1(
                row.path,
                row.comparison_axis,
                1,
                row.lane,
                row.semantics_id,
                row.reducer,
            )
            for row in selected.operational_leaves
        ),
    )
    result.validate(selected)
    return result


@dataclass(frozen=True, slots=True)
class ActualProjectionProfileV5:
    counter_registry_id: str
    comparison_profile_id: str
    terms: tuple[ProjectionTermV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        parse_content_id(self.comparison_profile_id)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.actual_projection_profile.v5",
            "schema_version": SCHEMA_VERSION,
            "profile_key": ACTUAL_PROJECTION_PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "terms": [row.to_dict() for row in self.terms],
            "caller_supplied_actual_comparison_allowed": False,
        }

    @property
    def actual_projection_profile_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V5_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "actual_projection_profile_id": self.actual_projection_profile_id,
        }

    def validate(
        self,
        registry: CounterRegistryV5,
        comparison: ComparisonProfileV5,
    ) -> None:
        comparison.validate(registry)
        if (
            self.counter_registry_id != registry.registry_id
            or self.comparison_profile_id
            != comparison.comparison_profile_id
            or self.terms != comparison.terms
        ):
            raise ConstructionAccountingRegistryV5Error(
                "official V5 actual-projection profile changed"
            )


def official_actual_projection_profile_v5(
    registry: CounterRegistryV5 | None = None,
    comparison: ComparisonProfileV5 | None = None,
) -> ActualProjectionProfileV5:
    selected = registry or official_counter_registry_v5()
    selected_comparison = comparison or official_comparison_profile_v5(
        selected
    )
    result = ActualProjectionProfileV5(
        selected.registry_id,
        selected_comparison.comparison_profile_id,
        selected_comparison.terms,
    )
    result.validate(selected, selected_comparison)
    return result


def freeze_construction_accounting_registry_v5() -> dict[str, Any]:
    """Return canonical V5 profile documents without issuing evidence."""

    registry = official_counter_registry_v5()
    stage = official_stage_profile_v5(registry)
    comparison = official_comparison_profile_v5(registry)
    actual = official_actual_projection_profile_v5(registry, comparison)
    return {
        "counter_registry": registry.to_document(),
        "stage_profile": stage.to_document(),
        "comparison_profile": comparison.to_document(),
        "actual_projection_profile": actual.to_document(),
    }


__all__ = [
    "ACTUAL_PROJECTION_PROFILE_KEY",
    "COMPARISON_PROFILE_KEY",
    "COUNTER_REGISTRY_KEY",
    "ConstructionAccountingRegistryV5Error",
    "ConstructionStageKindV5",
    "EXPECTED_V4_LEAF_COUNT",
    "EXPECTED_V4_OPERATIONAL_LEAF_COUNT",
    "EXPECTED_V4_REQUIRED_LEAF_COUNT",
    "EXPECTED_V5_ADDITION_COUNT",
    "EXPECTED_V5_LEAF_COUNT",
    "EXPECTED_V5_OPERATIONAL_LEAF_COUNT",
    "EXPECTED_V5_REQUIRED_LEAF_COUNT",
    "EXPECTED_V5_STAGE_COUNT",
    "SCHEMA_VERSION",
    "STAGE_PROFILE_KEY",
    "freeze_construction_accounting_registry_v5",
    "official_actual_projection_profile_v5",
    "official_comparison_profile_v5",
    "official_counter_registry_v5",
    "official_stage_profile_v5",
]
