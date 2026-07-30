"""Additive successor registry for live V0-075 construction accounting.

Contract 1.85 deliberately stopped before live instrumentation.  A source
audit then established that the 69-leaf v2 catalogue cannot cover every
operation executed by the registered construction and future checkpoint
paths.  This module therefore creates an immutable successor instead of
mutating v2.

The v3 catalogue:

* preserves every v2 leaf and its metadata byte-for-byte;
* registers the eleven previously unmapped operational families at each
  stage where they can actually execute;
* distinguishes acquisition/planning while the observer remains open from
  initial build and closed reconciliation;
* partitions all 87 distinct historical custom counter paths into four
  explicit migration dispositions;
* continues to forbid translating historical summary counters into native
  records.

This is still a schema/profile module.  It mints no CounterRecord,
WorkVector, terminal, occurrence closure, campaign result, or certificate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.accounting_v1 import (
    KERNEL_TRANSITION_CALLS,
    NONKERNEL_COMPUTE_EVENTS,
    SHARED_AXES,
    ComparisonAxisV1,
    CounterSemanticsV1,
    LaneEnum,
    ProjectionTermV1,
    ReducerEnum,
    official_shared_axes_v1,
)
from acfqp.construction_accounting_v2 import (
    official_counter_registry_v2,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V3_DOMAIN,
    CONSTRUCTION_COMPARISON_PROFILE_V3_DOMAIN,
    CONSTRUCTION_COUNTER_REGISTRY_V3_DOMAIN,
    CONSTRUCTION_LEGACY_MIGRATION_PROFILE_V3_DOMAIN,
    CONSTRUCTION_STAGE_PROFILE_V3_DOMAIN,
    content_id,
    parse_content_id,
)
from acfqp import v075_batch_native_statistical_backend_v1 as batch_native
from acfqp import v075_integrated_direct_occurrence_pipeline_v1 as direct
from acfqp import v075_learned_support_quotient_planners_v1 as planner
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_route_native_backend_core_v1 as route_core


SCHEMA_VERSION = "3.0.0"
COUNTER_REGISTRY_KEY = "acfqp_counter_registry_v3"
STAGE_PROFILE_KEY = "construction_stage_exclusivity_v3"
COMPARISON_PROFILE_KEY = "comparison_profile_shared_resources_v3"
ACTUAL_PROJECTION_PROFILE_KEY = "actual_projection_construction_v3"
LEGACY_MIGRATION_PROFILE_KEY = "v075_legacy_counter_migration_v3"

EXPECTED_V2_LEAF_COUNT = 69
EXPECTED_V2_OPERATIONAL_LEAF_COUNT = 53
EXPECTED_V2_REQUIRED_LEAF_COUNT = 62
EXPECTED_V3_ADDITION_COUNT = 47
EXPECTED_V3_OPERATIONAL_ADDITION_COUNT = 46
EXPECTED_V3_LEAF_COUNT = 116
EXPECTED_V3_OPERATIONAL_LEAF_COUNT = 99
EXPECTED_V3_REQUIRED_LEAF_COUNT = 109
EXPECTED_V3_STAGE_COUNT = 10
EXPECTED_LEGACY_DISTINCT_PATH_COUNT = 87


class ConstructionAccountingRegistryV3Error(ValueError):
    """A successor-registry or legacy-migration artifact is invalid."""


class ConstructionStageKindV3(str, Enum):
    PREOPEN_COMMON_PREFIX = "PREOPEN_COMMON_PREFIX"
    INITIAL_ACQUISITION = "INITIAL_ACQUISITION"
    INITIAL_MODEL_BUILD = "INITIAL_MODEL_BUILD"
    FAILED_ABSTRACT_PREFIX = "FAILED_ABSTRACT_PREFIX"
    OPEN_INCREMENTAL_ACQUISITION = "OPEN_INCREMENTAL_ACQUISITION"
    OPEN_CHECKPOINT_REPLANNING = "OPEN_CHECKPOINT_REPLANNING"
    CLOSED_RECONCILIATION_AND_TERMINALIZATION = (
        "CLOSED_RECONCILIATION_AND_TERMINALIZATION"
    )
    LOCAL_ATTEMPT = "LOCAL_ATTEMPT"
    DIRECT_FALLBACK = "DIRECT_FALLBACK"
    REBUILD = "REBUILD"


class LegacyMigrationDispositionV3(str, Enum):
    REINSTRUMENT_EXISTING_FAMILY = "REINSTRUMENT_EXISTING_FAMILY"
    DECOMPOSE_AT_NATIVE_SITES = "DECOMPOSE_AT_NATIVE_SITES"
    DERIVE_OR_DIAGNOSE_FROM_PRIMITIVES = (
        "DERIVE_OR_DIAGNOSE_FROM_PRIMITIVES"
    )
    REGISTER_NEW_OPERATIONAL_FAMILY = "REGISTER_NEW_OPERATIONAL_FAMILY"


def _stage(value: Any) -> ConstructionStageKindV3:
    try:
        return ConstructionStageKindV3(value)
    except (TypeError, ValueError) as error:
        raise ConstructionAccountingRegistryV3Error(
            f"unknown construction stage {value!r}"
        ) from error


def _operational(
    path: str,
    semantics_id: str,
    owner: str,
    unit: str,
    scope: str,
    axis: str = NONKERNEL_COMPUTE_EVENTS,
) -> CounterSemanticsV1:
    return CounterSemanticsV1(
        path=path,
        semantics_id=semantics_id,
        owner=owner,
        unit=unit,
        lane=LaneEnum.OPERATIONAL,
        scope=scope,
        reducer=ReducerEnum.SUM,
        comparison_axis=axis,
        required=True,
    )


def _diagnostic(
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
        lane=LaneEnum.DIAGNOSTIC,
        scope=scope,
        reducer=ReducerEnum.SUM,
        comparison_axis=None,
        required=True,
    )


_PLANNING_FAMILY_METADATA = MappingProxyType(
    {
        "confidence_event_evaluations": (
            "v075-confidence-event-evaluation-v3",
            "v075_batch_native_planning_backend_v2",
            "confidence_events",
        ),
        "exact_likelihood_comparisons": (
            "v075-exact-likelihood-comparison-v3",
            "v075_batch_native_planning_backend_v2",
            "likelihood_comparisons",
        ),
        "interval_lp_allocations": (
            "v075-interval-lp-allocation-v3",
            "v075_learned_support_quotient_planners_v1",
            "lp_allocations",
        ),
        "dominance_comparisons": (
            "v075-dominance-comparison-v3",
            "v075_learned_support_quotient_planners_v1",
            "dominance_comparisons",
        ),
        "deterministic_tie_breaks": (
            "v075-deterministic-tie-break-v3",
            "v075_learned_support_quotient_planners_v1",
            "tie_breaks",
        ),
        "quotient_cells_compiled": (
            "v075-quotient-cell-compile-v3",
            "v075_learned_support_quotient_planners_v1",
            "quotient_cells",
        ),
        "semantic_actions_compiled": (
            "v075-semantic-action-compile-v3",
            "v075_learned_support_quotient_planners_v1",
            "semantic_actions",
        ),
        "concretizer_ground_actions_compiled": (
            "v075-concretizer-ground-action-compile-v3",
            "v075_learned_support_quotient_planners_v1",
            "ground_actions",
        ),
    }
)


def _planning_family_leaves(
    *,
    prefix: str,
    semantics_stage: str,
    scope: str,
) -> tuple[CounterSemanticsV1, ...]:
    return tuple(
        _operational(
            f"{prefix}_{family}",
            f"{semantics_id}-{semantics_stage}",
            owner,
            unit,
            scope,
        )
        for family, (
            semantics_id,
            owner,
            unit,
        ) in _PLANNING_FAMILY_METADATA.items()
    )


def _v3_additions() -> tuple[CounterSemanticsV1, ...]:
    initial_acquisition_scope = (
        "construction_occurrence_initial_acquisition_prefix"
    )
    initial_build_scope = "construction_occurrence_initial_build_epoch"
    failed_abstract_scope = (
        "construction_occurrence_failed_abstract_prefix"
    )
    open_acquisition_scope = (
        "construction_occurrence_open_incremental_acquisition"
    )
    open_checkpoint_scope = (
        "construction_occurrence_open_checkpoint_replanning"
    )
    closure_scope = (
        "construction_occurrence_closed_reconciliation_and_terminalization"
    )

    initial_acquisition = (
        _operational(
            "acquisition.initial_outcome_projections",
            "v075-outcome-projection-v3-initial-acquisition",
            "v075_batch_native_planning_backend_v2",
            "outcome_projections",
            initial_acquisition_scope,
        ),
        _operational(
            "acquisition.initial_proposal_entries_bound",
            "v075-proposal-entry-binding-v3-initial-acquisition",
            "v075_source_prior_adapter_v1",
            "proposal_entries",
            initial_acquisition_scope,
        ),
        _operational(
            "acquisition.initial_child_catalogues_built",
            "v075-child-catalogue-build-v3-initial-acquisition",
            "v075_live_dynamic_acquisition_authority_v2",
            "child_catalogues",
            initial_acquisition_scope,
        ),
    )
    initial_build = _planning_family_leaves(
        prefix="build.initial",
        semantics_stage="initial-build",
        scope=initial_build_scope,
    )
    failed_abstract = (
        _operational(
            "audit.failed_child_catalogues_built",
            "v075-child-catalogue-build-v3-failed-abstract-audit",
            "v075_live_dynamic_acquisition_authority_v2",
            "child_catalogues",
            failed_abstract_scope,
        ),
    )
    closure = (
        *_planning_family_leaves(
            prefix="closure.reconciliation",
            semantics_stage="closed-reconciliation",
            scope=closure_scope,
        ),
        _operational(
            "closure.reconciliation_outcome_projections",
            "v075-outcome-projection-v3-closed-reconciliation",
            "v075_batch_native_planning_backend_v2",
            "outcome_projections",
            closure_scope,
        ),
        _operational(
            "closure.reconciliation_proposal_entries_bound",
            "v075-proposal-entry-binding-v3-closed-reconciliation",
            "v075_source_prior_adapter_v1",
            "proposal_entries",
            closure_scope,
        ),
        _operational(
            "closure.reconciliation_child_catalogues_built",
            "v075-child-catalogue-build-v3-closed-reconciliation",
            "v075_live_dynamic_acquisition_authority_v2",
            "child_catalogues",
            closure_scope,
        ),
    )
    open_acquisition = (
        _operational(
            "acquisition.incremental_observer_accepted_draws",
            "v075-observer-accepted-draw-v3-open-incremental",
            "v075_private_observer_boundary_v2",
            "accepted_draws",
            open_acquisition_scope,
            KERNEL_TRANSITION_CALLS,
        ),
        _operational(
            "acquisition.incremental_observer_random_word_calls",
            "v075-observer-random-word-call-v3-open-incremental",
            "v075_private_observer_boundary_v2",
            "random_word_calls",
            open_acquisition_scope,
        ),
        _diagnostic(
            "acquisition.incremental_observer_rejections",
            "v075-observer-rejection-v3-open-incremental",
            "v075_private_observer_boundary_v2",
            "rejections",
            open_acquisition_scope,
        ),
        _operational(
            "acquisition.incremental_outcome_aggregate_rows",
            "v075-outcome-aggregate-row-v3-open-incremental",
            "v075_private_observer_boundary_v2",
            "aggregate_rows",
            open_acquisition_scope,
        ),
        _operational(
            "acquisition.incremental_signed_batches",
            "v075-signed-batch-v3-open-incremental",
            "v075_private_observer_boundary_v2",
            "signed_batches",
            open_acquisition_scope,
        ),
        _operational(
            "acquisition.incremental_support_freezes",
            "v075-support-freeze-v3-open-incremental",
            "v075_observer_signed_batch_control_authority_v2",
            "support_freezes",
            open_acquisition_scope,
        ),
        _operational(
            "acquisition.incremental_outcome_projections",
            "v075-outcome-projection-v3-open-incremental",
            "v075_batch_native_planning_backend_v2",
            "outcome_projections",
            open_acquisition_scope,
        ),
        _operational(
            "acquisition.incremental_proposal_entries_bound",
            "v075-proposal-entry-binding-v3-open-incremental",
            "v075_source_prior_adapter_v1",
            "proposal_entries",
            open_acquisition_scope,
        ),
        _operational(
            "acquisition.incremental_child_catalogues_built",
            "v075-child-catalogue-build-v3-open-incremental",
            "v075_live_dynamic_acquisition_authority_v2",
            "child_catalogues",
            open_acquisition_scope,
        ),
    )
    open_checkpoint_existing = (
        _operational(
            "build.open_checkpoint_interval_log_search_evaluations",
            "v075-interval-log-search-evaluation-v3-open-checkpoint",
            "v075_batch_native_planning_backend_v2",
            "log_search_evaluations",
            open_checkpoint_scope,
        ),
        _operational(
            "build.open_checkpoint_interval_row_evaluations",
            "v075-interval-row-evaluation-v3-open-checkpoint",
            "v075_batch_native_planning_backend_v2",
            "row_behavior_evaluations",
            open_checkpoint_scope,
        ),
        _operational(
            "build.open_checkpoint_model_rows_built",
            "v075-model-row-build-v3-open-checkpoint",
            "v075_live_incremental_model_authority_v2",
            "model_rows",
            open_checkpoint_scope,
        ),
        _operational(
            "build.open_checkpoint_policy_assignments_evaluated",
            "v075-policy-assignment-evaluation-v3-open-checkpoint",
            "v075_batch_native_planning_backend_v2",
            "policy_assignments",
            open_checkpoint_scope,
        ),
        _operational(
            "build.open_checkpoint_semantic_record_replays",
            "v075-semantic-record-replay-v3-open-checkpoint",
            "v075_semantic_replay_instrumentation_v3",
            "record_replays",
            open_checkpoint_scope,
        ),
        _operational(
            "build.open_checkpoint_semantic_role_closures",
            "v075-semantic-role-closure-v3-open-checkpoint",
            "v075_semantic_replay_instrumentation_v3",
            "role_closures",
            open_checkpoint_scope,
        ),
        _operational(
            "build.open_checkpoint_source_units_compiled",
            "v075-row-source-unit-compile-v3-open-checkpoint",
            "v075_live_incremental_model_authority_v2",
            "row_source_units",
            open_checkpoint_scope,
        ),
    )
    open_checkpoint = (
        *open_checkpoint_existing,
        *_planning_family_leaves(
            prefix="build.open_checkpoint",
            semantics_stage="open-checkpoint",
            scope=open_checkpoint_scope,
        ),
    )
    rows = (
        *initial_acquisition,
        *initial_build,
        *failed_abstract,
        *closure,
        *open_acquisition,
        *open_checkpoint,
    )
    return tuple(sorted(rows, key=lambda row: row.path))


@dataclass(frozen=True, slots=True)
class CounterRegistryV3:
    registry_key: str
    schema_version: str
    v2_registry_id: str
    leaves: tuple[CounterSemanticsV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.v2_registry_id)
        if (
            self.registry_key != COUNTER_REGISTRY_KEY
            or self.schema_version != SCHEMA_VERSION
            or tuple(sorted(self.leaves, key=lambda row: row.path))
            != self.leaves
            or len({row.path for row in self.leaves}) != len(self.leaves)
        ):
            raise ConstructionAccountingRegistryV3Error(
                "v3 counter registry shape changed"
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
            "schema": "acfqp.counter_registry.v3",
            "schema_version": self.schema_version,
            "counter_registry_key": self.registry_key,
            "v2_registry_id": self.v2_registry_id,
            "leaves": [row.to_dict() for row in self.leaves],
            "v2_prefix_preserved_exactly": True,
        }

    @property
    def registry_id(self) -> str:
        return content_id(
            CONSTRUCTION_COUNTER_REGISTRY_V3_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counter_registry_id": self.registry_id}

    def validate_official_catalogue(self) -> None:
        expected = _expected_registry_v3()
        if self != expected:
            raise ConstructionAccountingRegistryV3Error(
                "official v3 counter catalogue changed"
            )


def _expected_registry_v3() -> CounterRegistryV3:
    v2 = official_counter_registry_v2()
    v2.validate_official_catalogue()
    additions = _v3_additions()
    if (
        len(v2.leaves) != EXPECTED_V2_LEAF_COUNT
        or len(v2.operational_leaves)
        != EXPECTED_V2_OPERATIONAL_LEAF_COUNT
        or len(v2.required_paths) != EXPECTED_V2_REQUIRED_LEAF_COUNT
        or len(additions) != EXPECTED_V3_ADDITION_COUNT
        or len(
            tuple(
                row
                for row in additions
                if row.lane is LaneEnum.OPERATIONAL
            )
        )
        != EXPECTED_V3_OPERATIONAL_ADDITION_COUNT
        or set(v2.by_path) & {row.path for row in additions}
    ):
        raise ConstructionAccountingRegistryV3Error(
            "v2 prefix or v3 additive catalogue changed"
        )
    return CounterRegistryV3(
        COUNTER_REGISTRY_KEY,
        SCHEMA_VERSION,
        v2.registry_id,
        tuple(sorted((*v2.leaves, *additions), key=lambda row: row.path)),
    )


def official_counter_registry_v3() -> CounterRegistryV3:
    result = _expected_registry_v3()
    if (
        len(result.leaves) != EXPECTED_V3_LEAF_COUNT
        or len(result.operational_leaves)
        != EXPECTED_V3_OPERATIONAL_LEAF_COUNT
        or len(result.required_paths) != EXPECTED_V3_REQUIRED_LEAF_COUNT
    ):
        raise ConstructionAccountingRegistryV3Error(
            "v3 registry cardinality changed"
        )
    return result


_COMMON_RUNTIME_PATHS = frozenset(
    {
        "common.hash_invocations",
        "common.integrity_checks",
        "common.protocol_checks",
        "io.mounted_bytes_peak",
        "io.output_bytes",
        "io.read_bytes",
        "io.staged_bytes",
        "memory.working_bytes_peak",
        "process.exit_failures",
        "process.exit_successes",
        "process.launches",
    }
)
_ROUTE_RECONCILIATION_PATHS = frozenset(
    {
        "route.attempts",
        "route.failures",
        "route.successes",
        "solver.attempts",
        "solver.failures",
        "solver.successes",
    }
)


@dataclass(frozen=True, slots=True)
class StageRuleV3:
    stage_kind: ConstructionStageKindV3
    allowed_nonzero_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        if (
            tuple(sorted(self.allowed_nonzero_paths))
            != self.allowed_nonzero_paths
            or len(set(self.allowed_nonzero_paths))
            != len(self.allowed_nonzero_paths)
        ):
            raise ConstructionAccountingRegistryV3Error(
                "v3 stage paths must be unique and sorted"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "stage_kind": self.stage_kind.value,
            "allowed_nonzero_paths": list(self.allowed_nonzero_paths),
        }


def _paths(
    registry: CounterRegistryV3, *prefixes: str
) -> frozenset[str]:
    return frozenset(
        path
        for path in registry.required_paths
        if any(path.startswith(prefix) for prefix in prefixes)
    )


def _expected_stage_rules_v3(
    registry: CounterRegistryV3,
) -> tuple[StageRuleV3, ...]:
    abstract = frozenset(
        {
            "common.abstract_audit_obligations",
            "common.abstract_bellman_backups",
        }
    )
    rules = {
        ConstructionStageKindV3.PREOPEN_COMMON_PREFIX: (
            _COMMON_RUNTIME_PATHS
        ),
        ConstructionStageKindV3.INITIAL_ACQUISITION: (
            _COMMON_RUNTIME_PATHS
            | _paths(registry, "acquisition.initial_")
        ),
        ConstructionStageKindV3.INITIAL_MODEL_BUILD: (
            _COMMON_RUNTIME_PATHS | _paths(registry, "build.initial_")
        ),
        ConstructionStageKindV3.FAILED_ABSTRACT_PREFIX: (
            _COMMON_RUNTIME_PATHS
            | abstract
            | _paths(registry, "audit.failed_")
        ),
        ConstructionStageKindV3.OPEN_INCREMENTAL_ACQUISITION: (
            _COMMON_RUNTIME_PATHS
            | _paths(registry, "acquisition.incremental_")
        ),
        ConstructionStageKindV3.OPEN_CHECKPOINT_REPLANNING: (
            _COMMON_RUNTIME_PATHS
            | _paths(registry, "build.open_checkpoint_")
        ),
        (
            ConstructionStageKindV3
            .CLOSED_RECONCILIATION_AND_TERMINALIZATION
        ): (
            _COMMON_RUNTIME_PATHS
            | frozenset(
                {
                    "route.attempts",
                    "route.failures",
                    "route.successes",
                }
            )
            | _paths(registry, "closure.reconciliation_")
        ),
        ConstructionStageKindV3.LOCAL_ATTEMPT: (
            _COMMON_RUNTIME_PATHS
            | _ROUTE_RECONCILIATION_PATHS
            | _paths(registry, "local.", "control.")
        ),
        ConstructionStageKindV3.DIRECT_FALLBACK: (
            _COMMON_RUNTIME_PATHS
            | _ROUTE_RECONCILIATION_PATHS
            | _paths(registry, "fallback.", "control.")
        ),
        ConstructionStageKindV3.REBUILD: (
            _COMMON_RUNTIME_PATHS | _paths(registry, "rebuild.")
        ),
    }
    return tuple(
        StageRuleV3(kind, tuple(sorted(paths)))
        for kind, paths in sorted(
            rules.items(), key=lambda item: item[0].value
        )
    )


@dataclass(frozen=True, slots=True)
class StageProfileV3:
    counter_registry_id: str
    rules: tuple[StageRuleV3, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        if (
            len(self.rules) != EXPECTED_V3_STAGE_COUNT
            or tuple(
                sorted(self.rules, key=lambda row: row.stage_kind.value)
            )
            != self.rules
            or {row.stage_kind for row in self.rules}
            != set(ConstructionStageKindV3)
        ):
            raise ConstructionAccountingRegistryV3Error(
                "v3 stage profile must cover each stage exactly once"
            )

    @property
    def by_stage(self) -> dict[ConstructionStageKindV3, StageRuleV3]:
        return {row.stage_kind: row for row in self.rules}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_stage_profile.v3",
            "schema_version": SCHEMA_VERSION,
            "profile_key": STAGE_PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "rules": [row.to_document() for row in self.rules],
            "initial_build_owns_root_epoch_compile_and_plan": True,
            "failed_abstract_prefix_owns_verified_child_audit_only": True,
            "interval_row_path_uses_registered_row_behavior_unit": True,
        }

    @property
    def stage_profile_id(self) -> str:
        return content_id(
            CONSTRUCTION_STAGE_PROFILE_V3_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "stage_profile_id": self.stage_profile_id}

    def validate(self, registry: CounterRegistryV3) -> None:
        registry.validate_official_catalogue()
        if (
            self.counter_registry_id != registry.registry_id
            or self.rules != _expected_stage_rules_v3(registry)
        ):
            raise ConstructionAccountingRegistryV3Error(
                "official v3 stage profile changed"
            )
        known = set(registry.required_paths)
        if any(
            not set(row.allowed_nonzero_paths) <= known
            for row in self.rules
        ):
            raise ConstructionAccountingRegistryV3Error(
                "v3 stage profile references an unknown path"
            )


def official_stage_profile_v3(
    registry: CounterRegistryV3 | None = None,
) -> StageProfileV3:
    selected = registry or official_counter_registry_v3()
    result = StageProfileV3(
        selected.registry_id,
        _expected_stage_rules_v3(selected),
    )
    result.validate(selected)
    return result


@dataclass(frozen=True, slots=True)
class ComparisonProfileV3:
    counter_registry_id: str
    axes: tuple[ComparisonAxisV1, ...]
    terms: tuple[ProjectionTermV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        if tuple(row.name for row in self.axes) != SHARED_AXES:
            raise ConstructionAccountingRegistryV3Error(
                "v3 comparison axes changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.comparison_profile.v3",
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
            CONSTRUCTION_COMPARISON_PROFILE_V3_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "comparison_profile_id": self.comparison_profile_id,
        }

    def validate(self, registry: CounterRegistryV3) -> None:
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
            raise ConstructionAccountingRegistryV3Error(
                "official v3 comparison profile changed"
            )


def official_comparison_profile_v3(
    registry: CounterRegistryV3 | None = None,
) -> ComparisonProfileV3:
    selected = registry or official_counter_registry_v3()
    result = ComparisonProfileV3(
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
class ActualProjectionProfileV3:
    counter_registry_id: str
    comparison_profile_id: str
    terms: tuple[ProjectionTermV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        parse_content_id(self.comparison_profile_id)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.actual_projection_profile.v3",
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
            CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V3_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "actual_projection_profile_id": (
                self.actual_projection_profile_id
            ),
        }

    def validate(
        self,
        registry: CounterRegistryV3,
        comparison: ComparisonProfileV3,
    ) -> None:
        comparison.validate(registry)
        if (
            self.counter_registry_id != registry.registry_id
            or self.comparison_profile_id
            != comparison.comparison_profile_id
            or self.terms != comparison.terms
        ):
            raise ConstructionAccountingRegistryV3Error(
                "official v3 actual-projection profile changed"
            )


def official_actual_projection_profile_v3(
    registry: CounterRegistryV3 | None = None,
    comparison: ComparisonProfileV3 | None = None,
) -> ActualProjectionProfileV3:
    selected = registry or official_counter_registry_v3()
    selected_comparison = (
        comparison or official_comparison_profile_v3(selected)
    )
    result = ActualProjectionProfileV3(
        selected.registry_id,
        selected_comparison.comparison_profile_id,
        selected_comparison.terms,
    )
    result.validate(selected, selected_comparison)
    return result


_REINSTRUMENT_EXISTING = frozenset(
    {
        "common.accepted_draws_consumed",
        "common.interval_row_evaluations",
        "common.log_search_evaluations",
        "common.policy_assignments_evaluated",
        "common.signed_batches_retained",
        "common.statistical_rows_built",
        "support.rows_frozen",
    }
)
_DECOMPOSE_NATIVE = frozenset(
    {
        "common.aggregate_support_evidence_verified",
        "common.capability_attestation_verifications",
        "common.capability_refs_consumed",
        "common.learned_support_graph_checks",
        "common.open_lifecycle_checks",
        "common.pre_sampling_identity_checks",
        "common.public_batch_verifications",
        "common.request_bytes_read",
        "common.request_checks",
        "common.request_reconstructions",
        "common.schedule_checks",
        "common.sequence_verifications",
        "common.total_lift_authority_bindings",
        "integrity.no_persistence_checks",
        "planning.checkpoints_evaluated",
        "source.adapter_payload_reads",
        "source_prior.adapter_reads",
        "source_prior.read_bytes",
    }
)
_NEW_OPERATIONAL = frozenset(
    {
        "adaptive.cells_compiled",
        "adaptive.concretizer_ground_actions",
        "adaptive.semantic_actions_compiled",
        "common.confidence_event_evaluations",
        "common.deterministic_tie_breaks",
        "common.dominance_comparisons",
        "common.exact_likelihood_comparisons",
        "common.interval_lp_allocations",
        "common.outcome_projections",
        "discovery.child_catalogues",
        "source.proposal_entries_bound",
    }
)
_DERIVED_OR_DIAGNOSTIC = frozenset(
    {
        "adaptive.model_builds",
        "adaptive.model_rows",
        "adaptive.no_prior_attempts",
        "adaptive.no_prior_dispatches",
        "adaptive.observation_capabilities",
        "adaptive.ood_abstention_attempts",
        "adaptive.ood_abstention_dispatches",
        "adaptive.planner_calls",
        "adaptive.planner_invocations",
        "adaptive.policy_solver_calls",
        "adaptive.proposal_dispatches",
        "adaptive.quotient_compiler_calls",
        "adaptive.route_attempts",
        "adaptive.route_dispatches",
        "adaptive.source_proposal_attempts",
        "adaptive.source_proposal_dispatches",
        "adaptive.total_lift_evaluations",
        "adaptive.wrong_prior_attempts",
        "adaptive.wrong_prior_dispatches",
        "common.adaptive_cap_charged_incremental_draws",
        "common.capability_records",
        "common.discovery_capabilities_consumed",
        "common.discovery_draws_consumed",
        "common.outcome_aggregates_projected",
        "common.per_draw_capabilities_materialized",
        "common.superseded_validation_draws",
        "common.total_lift_bind_attempts",
        "common.total_lift_candidate_emissions",
        "common.validation_capabilities_consumed",
        "common.validation_draws_consumed",
        "direct.ground_actions_considered",
        "direct.ground_planner_invocations",
        "direct.ground_states_considered",
        "direct.model_rows",
        "direct.observation_capabilities",
        "direct.planner_calls",
        "direct.policy_solver_calls",
        "direct.route_attempts",
        "direct.route_dispatches",
        "direct.total_lift_evaluations",
        "discovery.child_draws",
        "discovery.child_rows",
        "discovery.distinct_nonfailure_child_states",
        "discovery.root_draws",
        "discovery.root_rows",
        "planning.backend_compilations",
        "planning.matched_direct_planner_invocations",
        "planning.ready_checkpoint_count",
        "support.distinct_states_frozen",
        "validation.draws",
        "validation.rows",
    }
)

_EXISTING_TARGETS = MappingProxyType(
    {
        "common.accepted_draws_consumed": (
            "acquisition.initial_observer_accepted_draws",
            "acquisition.incremental_observer_accepted_draws",
        ),
        "common.signed_batches_retained": (
            "acquisition.initial_signed_batches",
            "acquisition.incremental_signed_batches",
        ),
        "support.rows_frozen": (
            "acquisition.initial_support_freezes",
            "acquisition.incremental_support_freezes",
        ),
        "common.log_search_evaluations": (
            "build.initial_interval_log_search_evaluations",
            "build.open_checkpoint_interval_log_search_evaluations",
            "closure.reconciliation_interval_log_search_evaluations",
        ),
        "common.interval_row_evaluations": (
            "build.initial_interval_row_evaluations",
            "build.open_checkpoint_interval_row_evaluations",
            "closure.reconciliation_interval_row_evaluations",
        ),
        "common.statistical_rows_built": (
            "build.initial_model_rows_built",
            "build.open_checkpoint_model_rows_built",
            "closure.reconciliation_model_rows_built",
        ),
        "common.policy_assignments_evaluated": (
            "build.initial_policy_assignments_evaluated",
            "build.open_checkpoint_policy_assignments_evaluated",
            "closure.reconciliation_policy_assignments_evaluated",
        ),
    }
)
_DECOMPOSE_TARGETS = MappingProxyType(
    {
        path: (
            ("io.read_bytes",)
            if "read" in path or "payload" in path
            else (
                ("common.integrity_checks",)
                if (
                    "verified" in path
                    or "verification" in path
                    or "integrity" in path
                    or "attestation" in path
                    or "persistence" in path
                )
                else ("common.protocol_checks",)
            )
        )
        for path in _DECOMPOSE_NATIVE
    }
)
_NEW_TARGETS = MappingProxyType(
    {
        "common.confidence_event_evaluations": (
            "build.initial_confidence_event_evaluations",
            "build.open_checkpoint_confidence_event_evaluations",
            "closure.reconciliation_confidence_event_evaluations",
        ),
        "common.exact_likelihood_comparisons": (
            "build.initial_exact_likelihood_comparisons",
            "build.open_checkpoint_exact_likelihood_comparisons",
            "closure.reconciliation_exact_likelihood_comparisons",
        ),
        "common.interval_lp_allocations": (
            "build.initial_interval_lp_allocations",
            "build.open_checkpoint_interval_lp_allocations",
            "closure.reconciliation_interval_lp_allocations",
        ),
        "common.dominance_comparisons": (
            "build.initial_dominance_comparisons",
            "build.open_checkpoint_dominance_comparisons",
            "closure.reconciliation_dominance_comparisons",
        ),
        "common.deterministic_tie_breaks": (
            "build.initial_deterministic_tie_breaks",
            "build.open_checkpoint_deterministic_tie_breaks",
            "closure.reconciliation_deterministic_tie_breaks",
        ),
        "common.outcome_projections": (
            "acquisition.initial_outcome_projections",
            "acquisition.incremental_outcome_projections",
            "closure.reconciliation_outcome_projections",
        ),
        "source.proposal_entries_bound": (
            "acquisition.initial_proposal_entries_bound",
            "acquisition.incremental_proposal_entries_bound",
            "closure.reconciliation_proposal_entries_bound",
        ),
        "discovery.child_catalogues": (
            "acquisition.initial_child_catalogues_built",
            "acquisition.incremental_child_catalogues_built",
            "audit.failed_child_catalogues_built",
            "closure.reconciliation_child_catalogues_built",
        ),
        "adaptive.cells_compiled": (
            "build.initial_quotient_cells_compiled",
            "build.open_checkpoint_quotient_cells_compiled",
            "closure.reconciliation_quotient_cells_compiled",
        ),
        "adaptive.semantic_actions_compiled": (
            "build.initial_semantic_actions_compiled",
            "build.open_checkpoint_semantic_actions_compiled",
            "closure.reconciliation_semantic_actions_compiled",
        ),
        "adaptive.concretizer_ground_actions": (
            "build.initial_concretizer_ground_actions_compiled",
            "build.open_checkpoint_concretizer_ground_actions_compiled",
            "closure.reconciliation_concretizer_ground_actions_compiled",
        ),
    }
)


def _legacy_catalogues() -> dict[str, tuple[str, ...]]:
    return {
        "V075_BATCH_NATIVE_HISTORICAL_CUSTOM": (
            batch_native.BATCH_NATIVE_COUNTER_PATHS
        ),
        "V075_DIRECT_HISTORICAL_CUSTOM": (
            direct.DIRECT_PIPELINE_COUNTER_PATHS
        ),
        "V075_PLANNER_HISTORICAL_CUSTOM": (
            planner.PLANNER_COUNTER_PATHS
        ),
        "V075_ROUTE_CORE_HISTORICAL_CUSTOM": route_core.COUNTER_PATHS,
        "V075_REGISTERED_WORKER_HISTORICAL_CUSTOM": (
            worker.REGISTERED_COUNTER_PATHS
        ),
    }


@dataclass(frozen=True, slots=True)
class LegacyMigrationRowV3:
    legacy_path: str
    source_catalogues: tuple[str, ...]
    disposition: LegacyMigrationDispositionV3
    target_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "disposition",
            LegacyMigrationDispositionV3(self.disposition),
        )
        if (
            not self.legacy_path
            or tuple(sorted(self.source_catalogues))
            != self.source_catalogues
            or not self.source_catalogues
            or tuple(sorted(self.target_paths)) != self.target_paths
            or len(set(self.target_paths)) != len(self.target_paths)
        ):
            raise ConstructionAccountingRegistryV3Error(
                "legacy migration row is noncanonical"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "legacy_path": self.legacy_path,
            "source_catalogues": list(self.source_catalogues),
            "disposition": self.disposition.value,
            "target_paths": list(self.target_paths),
            "historical_summary_translation_allowed": False,
            "native_operation_site_evidence_required": (
                self.disposition
                is not (
                    LegacyMigrationDispositionV3
                    .DERIVE_OR_DIAGNOSE_FROM_PRIMITIVES
                )
            ),
        }


def _expected_legacy_rows(
    registry: CounterRegistryV3,
) -> tuple[LegacyMigrationRowV3, ...]:
    catalogues = _legacy_catalogues()
    by_path: dict[str, list[str]] = {}
    for family, paths in catalogues.items():
        for path in paths:
            by_path.setdefault(path, []).append(family)
    union = set(by_path)
    partitions = (
        _REINSTRUMENT_EXISTING,
        _DECOMPOSE_NATIVE,
        _DERIVED_OR_DIAGNOSTIC,
        _NEW_OPERATIONAL,
    )
    if (
        len(union) != EXPECTED_LEGACY_DISTINCT_PATH_COUNT
        or any(
            left & right
            for index, left in enumerate(partitions)
            for right in partitions[index + 1 :]
        )
        or set().union(*partitions) != union
    ):
        raise ConstructionAccountingRegistryV3Error(
            "87-path legacy migration partition changed"
        )
    known_targets = set(registry.by_path)
    rows: list[LegacyMigrationRowV3] = []
    for path in sorted(union):
        if path in _REINSTRUMENT_EXISTING:
            disposition = (
                LegacyMigrationDispositionV3
                .REINSTRUMENT_EXISTING_FAMILY
            )
            targets = _EXISTING_TARGETS[path]
        elif path in _DECOMPOSE_NATIVE:
            disposition = (
                LegacyMigrationDispositionV3.DECOMPOSE_AT_NATIVE_SITES
            )
            targets = _DECOMPOSE_TARGETS[path]
        elif path in _NEW_OPERATIONAL:
            disposition = (
                LegacyMigrationDispositionV3
                .REGISTER_NEW_OPERATIONAL_FAMILY
            )
            targets = _NEW_TARGETS[path]
        else:
            disposition = (
                LegacyMigrationDispositionV3
                .DERIVE_OR_DIAGNOSE_FROM_PRIMITIVES
            )
            targets = ()
        if not set(targets) <= known_targets:
            raise ConstructionAccountingRegistryV3Error(
                f"legacy path {path!r} maps outside v3"
            )
        rows.append(
            LegacyMigrationRowV3(
                path,
                tuple(sorted(by_path[path])),
                disposition,
                tuple(sorted(targets)),
            )
        )
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class LegacyMigrationProfileV3:
    counter_registry_id: str
    rows: tuple[LegacyMigrationRowV3, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        if (
            len(self.rows) != EXPECTED_LEGACY_DISTINCT_PATH_COUNT
            or tuple(sorted(self.rows, key=lambda row: row.legacy_path))
            != self.rows
            or len({row.legacy_path for row in self.rows})
            != len(self.rows)
        ):
            raise ConstructionAccountingRegistryV3Error(
                "legacy migration profile is incomplete"
            )

    def _payload(self) -> dict[str, Any]:
        counts = {
            disposition.value: sum(
                row.disposition is disposition for row in self.rows
            )
            for disposition in LegacyMigrationDispositionV3
        }
        return {
            "schema": "acfqp.construction_legacy_counter_migration.v3",
            "schema_version": SCHEMA_VERSION,
            "profile_key": LEGACY_MIGRATION_PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "rows": [row.to_document() for row in self.rows],
            "disposition_counts": counts,
            "legacy_catalogue_entry_count": sum(
                len(paths) for paths in _legacy_catalogues().values()
            ),
            "legacy_distinct_path_count": len(self.rows),
            "legacy_summary_translation_allowed": False,
            "operation_site_instrumentation_complete": False,
            "derived_formula_registry_complete": False,
        }

    @property
    def migration_profile_id(self) -> str:
        return content_id(
            CONSTRUCTION_LEGACY_MIGRATION_PROFILE_V3_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "migration_profile_id": self.migration_profile_id,
        }

    def validate(self, registry: CounterRegistryV3) -> None:
        registry.validate_official_catalogue()
        if (
            self.counter_registry_id != registry.registry_id
            or self.rows != _expected_legacy_rows(registry)
        ):
            raise ConstructionAccountingRegistryV3Error(
                "official legacy migration profile changed"
            )


def official_legacy_migration_profile_v3(
    registry: CounterRegistryV3 | None = None,
) -> LegacyMigrationProfileV3:
    selected = registry or official_counter_registry_v3()
    result = LegacyMigrationProfileV3(
        selected.registry_id,
        _expected_legacy_rows(selected),
    )
    result.validate(selected)
    return result


def freeze_construction_accounting_registry_successor_v3(
) -> dict[str, dict[str, Any]]:
    """Return schema/profile documents without issuing live work evidence."""

    registry = official_counter_registry_v3()
    stage = official_stage_profile_v3(registry)
    comparison = official_comparison_profile_v3(registry)
    actual = official_actual_projection_profile_v3(
        registry, comparison
    )
    migration = official_legacy_migration_profile_v3(registry)
    return {
        "counter_registry": registry.to_document(),
        "stage_profile": stage.to_document(),
        "comparison_profile": comparison.to_document(),
        "actual_projection_profile": actual.to_document(),
        "legacy_migration_profile": migration.to_document(),
    }


__all__ = [
    "ACTUAL_PROJECTION_PROFILE_KEY",
    "COMPARISON_PROFILE_KEY",
    "COUNTER_REGISTRY_KEY",
    "EXPECTED_LEGACY_DISTINCT_PATH_COUNT",
    "EXPECTED_V3_LEAF_COUNT",
    "EXPECTED_V3_OPERATIONAL_LEAF_COUNT",
    "EXPECTED_V3_REQUIRED_LEAF_COUNT",
    "EXPECTED_V3_STAGE_COUNT",
    "LEGACY_MIGRATION_PROFILE_KEY",
    "SCHEMA_VERSION",
    "STAGE_PROFILE_KEY",
    "ActualProjectionProfileV3",
    "ComparisonProfileV3",
    "ConstructionAccountingRegistryV3Error",
    "ConstructionStageKindV3",
    "CounterRegistryV3",
    "LegacyMigrationDispositionV3",
    "LegacyMigrationProfileV3",
    "LegacyMigrationRowV3",
    "StageProfileV3",
    "StageRuleV3",
    "freeze_construction_accounting_registry_successor_v3",
    "official_actual_projection_profile_v3",
    "official_comparison_profile_v3",
    "official_counter_registry_v3",
    "official_legacy_migration_profile_v3",
    "official_stage_profile_v3",
]
