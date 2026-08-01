"""Additive owner-correct operation families for construction accounting V6.

V5 is immutable.  This successor preserves every V5 leaf document exactly
and adds narrowly scoped operation families whose primitive implementation
site is below the V4/V5 caller that previously exposed only a returned
summary.  It also adds the missing observer, replay, row-source, and exact
planner boundaries required by the batch-native multi-round path.

This module freezes schemas and stage ownership only.  It installs no runtime
emitter, issues no counter record, and makes no all-site, Gate, economics, or
official-execution claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
from acfqp import construction_accounting_registry_v5 as v5
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V6_DOMAIN,
    CONSTRUCTION_COMPARISON_PROFILE_V6_DOMAIN,
    CONSTRUCTION_COUNTER_REGISTRY_V6_DOMAIN,
    CONSTRUCTION_STAGE_PROFILE_V6_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "6.0.0"
COUNTER_REGISTRY_KEY = "acfqp_counter_registry_v6"
STAGE_PROFILE_KEY = "construction_stage_exclusivity_v6"
COMPARISON_PROFILE_KEY = "comparison_profile_shared_resources_v6"
ACTUAL_PROJECTION_PROFILE_KEY = "actual_projection_construction_v6"

EXPECTED_V5_LEAF_COUNT = 151
EXPECTED_V5_OPERATIONAL_LEAF_COUNT = 133
EXPECTED_V5_REQUIRED_LEAF_COUNT = 144
EXPECTED_V6_ADDITION_COUNT = 58
EXPECTED_V6_OPERATIONAL_ADDITION_COUNT = 49
EXPECTED_V6_LEAF_COUNT = 209
EXPECTED_V6_OPERATIONAL_LEAF_COUNT = 182
EXPECTED_V6_REQUIRED_LEAF_COUNT = 202
EXPECTED_V6_STAGE_COUNT = 10

_ENGINE = "h2_graph_transition_engine_v1"
_PRIVATE = "v075_private_observer_boundary_v2"
_LIVE_MODEL = "v075_live_incremental_model_authority_v2"
_PLANNING = "v075_batch_native_planning_backend_v2"
_SEQUENTIAL = "sequential_bernoulli_acquisition_v1"

_INITIAL_ACQUISITION_SCOPE = (
    "construction_occurrence_initial_acquisition_prefix"
)
_OPEN_ACQUISITION_SCOPE = (
    "construction_occurrence_open_incremental_acquisition"
)
_INITIAL_BUILD_SCOPE = "construction_occurrence_initial_build_epoch"
_OPEN_CHECKPOINT_SCOPE = (
    "construction_occurrence_open_checkpoint_replanning"
)
_CLOSED_SCOPE = (
    "construction_occurrence_closed_reconciliation_and_terminalization"
)


class ConstructionAccountingRegistryV6Error(ValueError):
    """The additive V6 registry or one of its profiles is invalid."""


ConstructionStageKindV6 = v5.ConstructionStageKindV5


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


def _observation_additions(
    *,
    prefix: str,
    semantics_stage: str,
    scope: str,
) -> tuple[CounterSemanticsV1, ...]:
    return (
        _operational(
            f"acquisition.{prefix}_engine_ground_draws",
            f"v075-engine-ground-draw-v6-{semantics_stage}",
            _ENGINE,
            "ground_draws",
            scope,
            KERNEL_TRANSITION_CALLS,
        ),
        _operational(
            f"acquisition.{prefix}_engine_random_word_calls",
            f"v075-engine-random-word-call-v6-{semantics_stage}",
            _ENGINE,
            "random_word_calls",
            scope,
        ),
        _diagnostic(
            f"acquisition.{prefix}_engine_rejections",
            f"v075-engine-rejection-v6-{semantics_stage}",
            _ENGINE,
            "rejections",
            scope,
        ),
        _operational(
            f"acquisition.{prefix}_engine_stream_initialization_merges",
            f"v075-engine-stream-init-merge-v6-{semantics_stage}",
            _ENGINE,
            "merge_calls",
            scope,
            KERNEL_TRANSITION_CALLS,
        ),
        _operational(
            f"acquisition.{prefix}_observer_accumulator_updates",
            f"v075-observer-accumulator-update-v6-{semantics_stage}",
            _PRIVATE,
            "accumulator_updates",
            scope,
        ),
        _operational(
            f"acquisition.{prefix}_signed_batches_materialized",
            f"v075-signed-batch-materialize-v6-{semantics_stage}",
            _PRIVATE,
            "signed_batches",
            scope,
        ),
        _operational(
            f"acquisition.{prefix}_signed_batches_committed",
            f"v075-signed-batch-journal-commit-v6-{semantics_stage}",
            _PRIVATE,
            "journal_commits",
            scope,
        ),
    )


def _confidence_and_planner_additions(
    *,
    prefix: str,
    semantics_stage: str,
    scope: str,
    include_row_source_binding: bool,
) -> tuple[CounterSemanticsV1, ...]:
    result = [
        _operational(
            f"{prefix}_sequential_exact_likelihood_comparisons",
            f"v075-sequential-exact-likelihood-comparison-v6-{semantics_stage}",
            _SEQUENTIAL,
            "likelihood_comparisons",
            scope,
        ),
        _operational(
            f"{prefix}_sequential_interval_log_search_evaluations",
            f"v075-sequential-log-search-evaluation-v6-{semantics_stage}",
            _SEQUENTIAL,
            "log_search_evaluations",
            scope,
        ),
        _operational(
            f"{prefix}_confidence_cache_lookups",
            f"v075-confidence-cache-lookup-v6-{semantics_stage}",
            _SEQUENTIAL,
            "cache_lookups",
            scope,
        ),
        _diagnostic(
            f"{prefix}_confidence_cache_hits",
            f"v075-confidence-cache-hit-v6-{semantics_stage}",
            _SEQUENTIAL,
            "cache_hits",
            scope,
        ),
        _diagnostic(
            f"{prefix}_confidence_cache_misses",
            f"v075-confidence-cache-miss-v6-{semantics_stage}",
            _SEQUENTIAL,
            "cache_misses",
            scope,
        ),
        _operational(
            f"{prefix}_batch_v2_replay_checkpoint_evaluations",
            f"v075-batch-v2-replay-checkpoint-evaluation-v6-{semantics_stage}",
            _PLANNING,
            "checkpoint_replays",
            scope,
        ),
        _operational(
            f"{prefix}_batch_v2_replay_interval_reconstructions",
            f"v075-batch-v2-replay-interval-reconstruction-v6-{semantics_stage}",
            _PLANNING,
            "interval_reconstructions",
            scope,
        ),
        _operational(
            f"{prefix}_batch_v2_option_metric_evaluations",
            f"v075-batch-v2-option-metric-evaluation-v6-{semantics_stage}",
            _PLANNING,
            "option_metric_evaluations",
            scope,
        ),
        _operational(
            f"{prefix}_batch_v2_policy_assignment_cap_checks",
            f"v075-batch-v2-policy-assignment-cap-check-v6-{semantics_stage}",
            _PLANNING,
            "cap_checks",
            scope,
        ),
    ]
    if include_row_source_binding:
        result.append(
            _operational(
                f"{prefix}_live_model_row_source_bindings_built",
                f"v075-live-model-row-source-binding-build-v6-{semantics_stage}",
                _LIVE_MODEL,
                "row_source_bindings",
                scope,
            )
        )
    return tuple(result)


_OPEN_BATCH_FAMILIES = (
    ("typed_record_replays", "typed-record-replay", "typed_record_replays"),
    ("row_behaviors_compiled", "row-behavior-compile", "row_behaviors"),
    ("quotient_cells_compiled", "quotient-cell-compile", "quotient_cells"),
    ("semantic_options_compiled", "semantic-option-compile", "semantic_options"),
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
    ("policy_order_comparisons", "policy-order-comparison", "comparisons"),
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


def _open_checkpoint_batch_additions() -> tuple[CounterSemanticsV1, ...]:
    rows = []
    for suffix, semantics, unit in _OPEN_BATCH_FAMILIES:
        live_support = suffix == "support_descriptors_compiled"
        rows.append(
            _operational(
                (
                    "build.open_checkpoint_live_model_"
                    "support_descriptors_compiled"
                    if live_support
                    else f"build.open_checkpoint_batch_v2_{suffix}"
                ),
                (
                    "v075-live-model-support-descriptor-compile-v6-"
                    "open-checkpoint"
                    if live_support
                    else f"v075-batch-v2-{semantics}-v6-open-checkpoint"
                ),
                _LIVE_MODEL if live_support else _PLANNING,
                unit,
                _OPEN_CHECKPOINT_SCOPE,
            )
        )
    rows.append(
        _operational(
            "build.open_checkpoint_live_model_outcome_projections",
            "v075-live-model-outcome-projection-v6-open-checkpoint",
            _LIVE_MODEL,
            "outcome_projections",
            _OPEN_CHECKPOINT_SCOPE,
        )
    )
    return tuple(rows)


def _closed_replay_additions() -> tuple[CounterSemanticsV1, ...]:
    return (
        _operational(
            "closure.reconciliation_engine_ground_draws",
            "v075-engine-ground-draw-v6-closed-private-replay",
            _ENGINE,
            "ground_draws",
            _CLOSED_SCOPE,
            KERNEL_TRANSITION_CALLS,
        ),
        _operational(
            "closure.reconciliation_engine_random_word_calls",
            "v075-engine-random-word-call-v6-closed-private-replay",
            _ENGINE,
            "random_word_calls",
            _CLOSED_SCOPE,
        ),
        _diagnostic(
            "closure.reconciliation_engine_rejections",
            "v075-engine-rejection-v6-closed-private-replay",
            _ENGINE,
            "rejections",
            _CLOSED_SCOPE,
        ),
        _operational(
            "closure.reconciliation_engine_stream_initialization_merges",
            "v075-engine-stream-init-merge-v6-closed-private-replay",
            _ENGINE,
            "merge_calls",
            _CLOSED_SCOPE,
            KERNEL_TRANSITION_CALLS,
        ),
        _operational(
            "closure.reconciliation_private_replay_accumulator_updates",
            "v075-private-replay-accumulator-update-v6-closed-reconciliation",
            _PRIVATE,
            "accumulator_updates",
            _CLOSED_SCOPE,
        ),
    )


def _v6_additions() -> tuple[CounterSemanticsV1, ...]:
    rows = (
        *_observation_additions(
            prefix="initial",
            semantics_stage="initial-acquisition",
            scope=_INITIAL_ACQUISITION_SCOPE,
        ),
        *_observation_additions(
            prefix="incremental",
            semantics_stage="open-incremental-acquisition",
            scope=_OPEN_ACQUISITION_SCOPE,
        ),
        *_confidence_and_planner_additions(
            prefix="build.initial",
            semantics_stage="initial-build",
            scope=_INITIAL_BUILD_SCOPE,
            include_row_source_binding=True,
        ),
        *_open_checkpoint_batch_additions(),
        *_confidence_and_planner_additions(
            prefix="build.open_checkpoint",
            semantics_stage="open-checkpoint",
            scope=_OPEN_CHECKPOINT_SCOPE,
            include_row_source_binding=True,
        ),
        *_closed_replay_additions(),
        *_confidence_and_planner_additions(
            prefix="closure.reconciliation",
            semantics_stage="closed-reconciliation",
            scope=_CLOSED_SCOPE,
            include_row_source_binding=False,
        ),
    )
    result = tuple(sorted(rows, key=lambda row: row.path))
    if (
        len(result) != EXPECTED_V6_ADDITION_COUNT
        or len({row.path for row in result}) != len(result)
        or sum(row.lane is LaneEnum.OPERATIONAL for row in result)
        != EXPECTED_V6_OPERATIONAL_ADDITION_COUNT
    ):
        raise ConstructionAccountingRegistryV6Error(
            "V6 owner-correction additions changed cardinality"
        )
    return result


@dataclass(frozen=True, slots=True)
class CounterRegistryV6:
    registry_key: str
    schema_version: str
    v5_registry_id: str
    leaves: tuple[CounterSemanticsV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.v5_registry_id)
        if (
            self.registry_key != COUNTER_REGISTRY_KEY
            or self.schema_version != SCHEMA_VERSION
            or tuple(sorted(self.leaves, key=lambda row: row.path))
            != self.leaves
            or len({row.path for row in self.leaves}) != len(self.leaves)
        ):
            raise ConstructionAccountingRegistryV6Error(
                "V6 counter registry shape changed"
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
            "schema": "acfqp.counter_registry.v6",
            "schema_version": self.schema_version,
            "counter_registry_key": self.registry_key,
            "v5_registry_id": self.v5_registry_id,
            "leaves": [row.to_dict() for row in self.leaves],
            "v5_leaf_documents_preserved_exactly": True,
            "owner_correction_addition_count": EXPECTED_V6_ADDITION_COUNT,
            "primitive_engine_and_sequential_owners_frozen": True,
            "confidence_cache_lookup_is_operational": True,
            "confidence_cache_hit_miss_are_diagnostic": True,
            "exact_and_log_work_counts_cache_miss_computation_only": True,
            "open_incremental_and_checkpoint_stage_schema_supported": True,
            "legacy_mismatched_paths_deleted_or_relabelled": False,
            "runtime_operation_emitters_installed": False,
            "runtime_owner_match_verified": False,
            "runtime_stage_attribution_verified": False,
            "operation_family_completeness_claimed": False,
            "official_execution_allowed": False,
            "counter_completeness_gate_passed": False,
            "workload_economics_gate_passed": False,
        }

    @property
    def registry_id(self) -> str:
        return content_id(
            CONSTRUCTION_COUNTER_REGISTRY_V6_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counter_registry_id": self.registry_id}

    def validate_official_catalogue(self) -> None:
        if self != _expected_registry_v6():
            raise ConstructionAccountingRegistryV6Error(
                "official V6 counter catalogue changed"
            )


def _expected_registry_v6() -> CounterRegistryV6:
    base = v5.official_counter_registry_v5()
    base.validate_official_catalogue()
    additions = _v6_additions()
    if (
        len(base.leaves) != EXPECTED_V5_LEAF_COUNT
        or len(base.operational_leaves) != EXPECTED_V5_OPERATIONAL_LEAF_COUNT
        or len(base.required_paths) != EXPECTED_V5_REQUIRED_LEAF_COUNT
        or set(base.by_path) & {row.path for row in additions}
        or any(
            not row.required
            or row.reducer is not ReducerEnum.SUM
            or (
                row.lane is LaneEnum.OPERATIONAL
                and row.comparison_axis
                not in {KERNEL_TRANSITION_CALLS, NONKERNEL_COMPUTE_EVENTS}
            )
            or (
                row.lane is LaneEnum.DIAGNOSTIC
                and row.comparison_axis is not None
            )
            for row in additions
        )
    ):
        raise ConstructionAccountingRegistryV6Error(
            "V5 prefix or V6 additive catalogue changed"
        )
    return CounterRegistryV6(
        COUNTER_REGISTRY_KEY,
        SCHEMA_VERSION,
        base.registry_id,
        tuple(sorted((*base.leaves, *additions), key=lambda row: row.path)),
    )


def official_counter_registry_v6() -> CounterRegistryV6:
    result = _expected_registry_v6()
    if (
        len(result.leaves) != EXPECTED_V6_LEAF_COUNT
        or len(result.operational_leaves)
        != EXPECTED_V6_OPERATIONAL_LEAF_COUNT
        or len(result.required_paths) != EXPECTED_V6_REQUIRED_LEAF_COUNT
    ):
        raise ConstructionAccountingRegistryV6Error(
            "V6 registry cardinality changed"
        )
    return result


def _addition_stage_by_path() -> dict[str, ConstructionStageKindV6]:
    result: dict[str, ConstructionStageKindV6] = {}
    for row in _v6_additions():
        if row.path.startswith("acquisition.initial_"):
            stage = ConstructionStageKindV6.INITIAL_ACQUISITION
        elif row.path.startswith("acquisition.incremental_"):
            stage = ConstructionStageKindV6.OPEN_INCREMENTAL_ACQUISITION
        elif row.path.startswith("build.initial_"):
            stage = ConstructionStageKindV6.INITIAL_MODEL_BUILD
        elif row.path.startswith("build.open_checkpoint_"):
            stage = ConstructionStageKindV6.OPEN_CHECKPOINT_REPLANNING
        elif row.path.startswith("closure.reconciliation_"):
            stage = (
                ConstructionStageKindV6
                .CLOSED_RECONCILIATION_AND_TERMINALIZATION
            )
        else:  # pragma: no cover - guarded by the frozen catalogue
            raise ConstructionAccountingRegistryV6Error(
                "V6 addition has no exact stage owner"
            )
        result[row.path] = stage
    return result


@dataclass(frozen=True, slots=True)
class StageRuleV6:
    stage_kind: ConstructionStageKindV6
    allowed_nonzero_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        try:
            selected = ConstructionStageKindV6(self.stage_kind)
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingRegistryV6Error(
                f"unknown construction stage {self.stage_kind!r}"
            ) from error
        object.__setattr__(self, "stage_kind", selected)
        if (
            tuple(sorted(self.allowed_nonzero_paths))
            != self.allowed_nonzero_paths
            or len(set(self.allowed_nonzero_paths))
            != len(self.allowed_nonzero_paths)
        ):
            raise ConstructionAccountingRegistryV6Error(
                "V6 stage paths must be unique and sorted"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "stage_kind": self.stage_kind.value,
            "allowed_nonzero_paths": list(self.allowed_nonzero_paths),
        }


def _expected_stage_rules_v6(
    registry: CounterRegistryV6,
) -> tuple[StageRuleV6, ...]:
    base = v5.official_stage_profile_v5()
    ownership = _addition_stage_by_path()
    rules = tuple(
        sorted(
            (
                StageRuleV6(
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
            ),
            key=lambda row: row.stage_kind.value,
        )
    )
    if set(ownership) != {row.path for row in _v6_additions()} or any(
        not set(row.allowed_nonzero_paths) <= set(registry.required_paths)
        for row in rules
    ):
        raise ConstructionAccountingRegistryV6Error(
            "V6 stage ownership is incomplete"
        )
    return rules


@dataclass(frozen=True, slots=True)
class StageProfileV6:
    counter_registry_id: str
    v5_stage_profile_id: str
    rules: tuple[StageRuleV6, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        parse_content_id(self.v5_stage_profile_id)
        if (
            len(self.rules) != EXPECTED_V6_STAGE_COUNT
            or tuple(sorted(self.rules, key=lambda row: row.stage_kind.value))
            != self.rules
            or {row.stage_kind for row in self.rules}
            != set(ConstructionStageKindV6)
        ):
            raise ConstructionAccountingRegistryV6Error(
                "V6 stage profile must cover each stage exactly once"
            )

    @property
    def by_stage(self) -> dict[ConstructionStageKindV6, StageRuleV6]:
        return {row.stage_kind: row for row in self.rules}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_stage_profile.v6",
            "schema_version": SCHEMA_VERSION,
            "profile_key": STAGE_PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "v5_stage_profile_id": self.v5_stage_profile_id,
            "rules": [row.to_document() for row in self.rules],
            "v5_stage_ownership_preserved_exactly": True,
            "open_incremental_owner_corrections_routed": True,
            "open_checkpoint_owner_corrections_routed": True,
            "runtime_owner_match_verified": False,
            "runtime_stage_attribution_verified": False,
        }

    @property
    def stage_profile_id(self) -> str:
        return content_id(
            CONSTRUCTION_STAGE_PROFILE_V6_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "stage_profile_id": self.stage_profile_id}

    def validate(self, registry: CounterRegistryV6) -> None:
        registry.validate_official_catalogue()
        base = v5.official_stage_profile_v5()
        if (
            self.counter_registry_id != registry.registry_id
            or self.v5_stage_profile_id != base.stage_profile_id
            or self.rules != _expected_stage_rules_v6(registry)
        ):
            raise ConstructionAccountingRegistryV6Error(
                "official V6 stage profile changed"
            )


def official_stage_profile_v6(
    registry: CounterRegistryV6 | None = None,
) -> StageProfileV6:
    selected = registry or official_counter_registry_v6()
    base = v5.official_stage_profile_v5()
    result = StageProfileV6(
        selected.registry_id,
        base.stage_profile_id,
        _expected_stage_rules_v6(selected),
    )
    result.validate(selected)
    return result


@dataclass(frozen=True, slots=True)
class ComparisonProfileV6:
    counter_registry_id: str
    axes: tuple[ComparisonAxisV1, ...]
    terms: tuple[ProjectionTermV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        if tuple(row.name for row in self.axes) != SHARED_AXES:
            raise ConstructionAccountingRegistryV6Error(
                "V6 comparison axes changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.comparison_profile.v6",
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
            CONSTRUCTION_COMPARISON_PROFILE_V6_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "comparison_profile_id": self.comparison_profile_id,
        }

    def validate(self, registry: CounterRegistryV6) -> None:
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
            raise ConstructionAccountingRegistryV6Error(
                "official V6 comparison profile changed"
            )


def official_comparison_profile_v6(
    registry: CounterRegistryV6 | None = None,
) -> ComparisonProfileV6:
    selected = registry or official_counter_registry_v6()
    result = ComparisonProfileV6(
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
class ActualProjectionProfileV6:
    counter_registry_id: str
    comparison_profile_id: str
    terms: tuple[ProjectionTermV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        parse_content_id(self.comparison_profile_id)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.actual_projection_profile.v6",
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
            CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V6_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "actual_projection_profile_id": self.actual_projection_profile_id,
        }

    def validate(
        self,
        registry: CounterRegistryV6,
        comparison: ComparisonProfileV6,
    ) -> None:
        comparison.validate(registry)
        if (
            self.counter_registry_id != registry.registry_id
            or self.comparison_profile_id
            != comparison.comparison_profile_id
            or self.terms != comparison.terms
        ):
            raise ConstructionAccountingRegistryV6Error(
                "official V6 actual-projection profile changed"
            )


def official_actual_projection_profile_v6(
    registry: CounterRegistryV6 | None = None,
    comparison: ComparisonProfileV6 | None = None,
) -> ActualProjectionProfileV6:
    selected = registry or official_counter_registry_v6()
    selected_comparison = comparison or official_comparison_profile_v6(
        selected
    )
    result = ActualProjectionProfileV6(
        selected.registry_id,
        selected_comparison.comparison_profile_id,
        selected_comparison.terms,
    )
    result.validate(selected, selected_comparison)
    return result


def freeze_construction_accounting_registry_v6() -> dict[str, Any]:
    """Return canonical V6 profile documents without issuing evidence."""

    registry = official_counter_registry_v6()
    stage = official_stage_profile_v6(registry)
    comparison = official_comparison_profile_v6(registry)
    actual = official_actual_projection_profile_v6(registry, comparison)
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
    "ConstructionAccountingRegistryV6Error",
    "ConstructionStageKindV6",
    "EXPECTED_V5_LEAF_COUNT",
    "EXPECTED_V5_OPERATIONAL_LEAF_COUNT",
    "EXPECTED_V5_REQUIRED_LEAF_COUNT",
    "EXPECTED_V6_ADDITION_COUNT",
    "EXPECTED_V6_LEAF_COUNT",
    "EXPECTED_V6_OPERATIONAL_ADDITION_COUNT",
    "EXPECTED_V6_OPERATIONAL_LEAF_COUNT",
    "EXPECTED_V6_REQUIRED_LEAF_COUNT",
    "EXPECTED_V6_STAGE_COUNT",
    "SCHEMA_VERSION",
    "STAGE_PROFILE_KEY",
    "freeze_construction_accounting_registry_v6",
    "official_actual_projection_profile_v6",
    "official_comparison_profile_v6",
    "official_counter_registry_v6",
    "official_stage_profile_v6",
]
