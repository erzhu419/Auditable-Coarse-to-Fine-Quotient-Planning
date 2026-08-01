"""Additive v4 registry correcting live construction-operation ownership.

The v3 registry is immutable.  Operation-site audit of the K7 construction
path found eight additional native leaves: four operations belong to model
build stages rather than acquisition stages, and four operations belong to
the closed private replay.  This successor preserves every v3 leaf and its
metadata exactly and appends only those audited leaves.

The historical v3 acquisition leaves remain registered because they are
valid for architectures that perform projection and prior binding while the
observer is acquiring.  A runtime that performs those operations during
model build records native zero for the acquisition leaves and charges the
new build leaves.

This module freezes schemas and profiles only.  It issues no live work
records or scientific claims.
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
from acfqp import construction_accounting_registry_v3 as v3
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V4_DOMAIN,
    CONSTRUCTION_COMPARISON_PROFILE_V4_DOMAIN,
    CONSTRUCTION_COUNTER_REGISTRY_V4_DOMAIN,
    CONSTRUCTION_STAGE_PROFILE_V4_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "4.0.0"
COUNTER_REGISTRY_KEY = "acfqp_counter_registry_v4"
STAGE_PROFILE_KEY = "construction_stage_exclusivity_v4"
COMPARISON_PROFILE_KEY = "comparison_profile_shared_resources_v4"
ACTUAL_PROJECTION_PROFILE_KEY = "actual_projection_construction_v4"

EXPECTED_V3_LEAF_COUNT = 116
EXPECTED_V3_OPERATIONAL_LEAF_COUNT = 99
EXPECTED_V3_REQUIRED_LEAF_COUNT = 109
EXPECTED_V4_ADDITION_COUNT = 8
EXPECTED_V4_OPERATIONAL_ADDITION_COUNT = 7
EXPECTED_V4_LEAF_COUNT = 124
EXPECTED_V4_OPERATIONAL_LEAF_COUNT = 106
EXPECTED_V4_REQUIRED_LEAF_COUNT = 117
EXPECTED_V4_STAGE_COUNT = 10


class ConstructionAccountingRegistryV4Error(ValueError):
    """The additive v4 registry or one of its profiles is invalid."""


# The stage vocabulary is unchanged.  Aliasing it makes the exact stage
# identity explicit and prevents a second enum from silently diverging.
ConstructionStageKindV4 = v3.ConstructionStageKindV3


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


def _v4_additions() -> tuple[CounterSemanticsV1, ...]:
    initial_scope = "construction_occurrence_initial_build_epoch"
    checkpoint_scope = (
        "construction_occurrence_open_checkpoint_replanning"
    )
    closure_scope = (
        "construction_occurrence_closed_reconciliation_and_terminalization"
    )
    rows = (
        _operational(
            "build.initial_outcome_projections",
            "v075-outcome-projection-v4-initial-build",
            "v075_batch_native_planning_backend_v2",
            "outcome_projections",
            initial_scope,
        ),
        _operational(
            "build.initial_proposal_entries_bound",
            "v075-proposal-entry-binding-v4-initial-build",
            "v075_source_prior_adapter_v1",
            "proposal_entries",
            initial_scope,
        ),
        _operational(
            "build.open_checkpoint_outcome_projections",
            "v075-outcome-projection-v4-open-checkpoint",
            "v075_batch_native_planning_backend_v2",
            "outcome_projections",
            checkpoint_scope,
        ),
        _operational(
            "build.open_checkpoint_proposal_entries_bound",
            "v075-proposal-entry-binding-v4-open-checkpoint",
            "v075_source_prior_adapter_v1",
            "proposal_entries",
            checkpoint_scope,
        ),
        _operational(
            "closure.reconciliation_private_replay_ground_steps",
            "v075-private-replay-ground-step-v4-closed-reconciliation",
            "v075_private_observer_boundary_v2",
            "ground_steps",
            closure_scope,
            KERNEL_TRANSITION_CALLS,
        ),
        _operational(
            "closure.reconciliation_private_replay_random_word_calls",
            "v075-private-replay-random-word-call-v4-closed-reconciliation",
            "v075_private_observer_boundary_v2",
            "random_word_calls",
            closure_scope,
        ),
        _diagnostic(
            "closure.reconciliation_private_replay_rejections",
            "v075-private-replay-rejection-v4-closed-reconciliation",
            "v075_private_observer_boundary_v2",
            "rejections",
            closure_scope,
        ),
        _operational(
            "closure.reconciliation_private_replay_outcome_aggregate_rows",
            "v075-private-replay-outcome-aggregate-row-v4-closed-reconciliation",
            "v075_private_observer_boundary_v2",
            "aggregate_rows",
            closure_scope,
        ),
    )
    return tuple(sorted(rows, key=lambda row: row.path))


@dataclass(frozen=True, slots=True)
class CounterRegistryV4:
    registry_key: str
    schema_version: str
    v3_registry_id: str
    leaves: tuple[CounterSemanticsV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.v3_registry_id)
        if (
            self.registry_key != COUNTER_REGISTRY_KEY
            or self.schema_version != SCHEMA_VERSION
            or tuple(sorted(self.leaves, key=lambda row: row.path))
            != self.leaves
            or len({row.path for row in self.leaves}) != len(self.leaves)
        ):
            raise ConstructionAccountingRegistryV4Error(
                "v4 counter registry shape changed"
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
            "schema": "acfqp.counter_registry.v4",
            "schema_version": self.schema_version,
            "counter_registry_key": self.registry_key,
            "v3_registry_id": self.v3_registry_id,
            "leaves": [row.to_dict() for row in self.leaves],
            "v3_prefix_preserved_exactly": True,
            "v3_acquisition_paths_remain_valid_and_registered": True,
            "native_zero_required_when_registered_path_did_not_execute": True,
        }

    @property
    def registry_id(self) -> str:
        return content_id(
            CONSTRUCTION_COUNTER_REGISTRY_V4_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counter_registry_id": self.registry_id}

    def validate_official_catalogue(self) -> None:
        if self != _expected_registry_v4():
            raise ConstructionAccountingRegistryV4Error(
                "official v4 counter catalogue changed"
            )


def _expected_registry_v4() -> CounterRegistryV4:
    base = v3.official_counter_registry_v3()
    base.validate_official_catalogue()
    additions = _v4_additions()
    if (
        len(base.leaves) != EXPECTED_V3_LEAF_COUNT
        or len(base.operational_leaves)
        != EXPECTED_V3_OPERATIONAL_LEAF_COUNT
        or len(base.required_paths) != EXPECTED_V3_REQUIRED_LEAF_COUNT
        or len(additions) != EXPECTED_V4_ADDITION_COUNT
        or sum(
            row.lane is LaneEnum.OPERATIONAL for row in additions
        )
        != EXPECTED_V4_OPERATIONAL_ADDITION_COUNT
        or set(base.by_path) & {row.path for row in additions}
    ):
        raise ConstructionAccountingRegistryV4Error(
            "v3 prefix or v4 additive catalogue changed"
        )
    return CounterRegistryV4(
        COUNTER_REGISTRY_KEY,
        SCHEMA_VERSION,
        base.registry_id,
        tuple(sorted((*base.leaves, *additions), key=lambda row: row.path)),
    )


def official_counter_registry_v4() -> CounterRegistryV4:
    result = _expected_registry_v4()
    if (
        len(result.leaves) != EXPECTED_V4_LEAF_COUNT
        or len(result.operational_leaves)
        != EXPECTED_V4_OPERATIONAL_LEAF_COUNT
        or len(result.required_paths) != EXPECTED_V4_REQUIRED_LEAF_COUNT
    ):
        raise ConstructionAccountingRegistryV4Error(
            "v4 registry cardinality changed"
        )
    return result


_ADDITION_STAGE = {
    "build.initial_outcome_projections": (
        ConstructionStageKindV4.INITIAL_MODEL_BUILD
    ),
    "build.initial_proposal_entries_bound": (
        ConstructionStageKindV4.INITIAL_MODEL_BUILD
    ),
    "build.open_checkpoint_outcome_projections": (
        ConstructionStageKindV4.OPEN_CHECKPOINT_REPLANNING
    ),
    "build.open_checkpoint_proposal_entries_bound": (
        ConstructionStageKindV4.OPEN_CHECKPOINT_REPLANNING
    ),
    "closure.reconciliation_private_replay_ground_steps": (
        ConstructionStageKindV4
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    ),
    "closure.reconciliation_private_replay_random_word_calls": (
        ConstructionStageKindV4
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    ),
    "closure.reconciliation_private_replay_rejections": (
        ConstructionStageKindV4
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    ),
    "closure.reconciliation_private_replay_outcome_aggregate_rows": (
        ConstructionStageKindV4
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    ),
}


@dataclass(frozen=True, slots=True)
class StageRuleV4:
    stage_kind: ConstructionStageKindV4
    allowed_nonzero_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        try:
            selected = ConstructionStageKindV4(self.stage_kind)
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingRegistryV4Error(
                f"unknown construction stage {self.stage_kind!r}"
            ) from error
        object.__setattr__(self, "stage_kind", selected)
        if (
            tuple(sorted(self.allowed_nonzero_paths))
            != self.allowed_nonzero_paths
            or len(set(self.allowed_nonzero_paths))
            != len(self.allowed_nonzero_paths)
        ):
            raise ConstructionAccountingRegistryV4Error(
                "v4 stage paths must be unique and sorted"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "stage_kind": self.stage_kind.value,
            "allowed_nonzero_paths": list(self.allowed_nonzero_paths),
        }


def _expected_stage_rules_v4(
    registry: CounterRegistryV4,
) -> tuple[StageRuleV4, ...]:
    base_registry = v3.official_counter_registry_v3()
    base_profile = v3.official_stage_profile_v3(base_registry)
    additions_by_stage = {
        kind: {
            path for path, selected in _ADDITION_STAGE.items()
            if selected is kind
        }
        for kind in ConstructionStageKindV4
    }
    rules = tuple(
        StageRuleV4(
            row.stage_kind,
            tuple(sorted(
                set(row.allowed_nonzero_paths)
                | additions_by_stage[row.stage_kind]
            )),
        )
        for row in base_profile.rules
    )
    if set(_ADDITION_STAGE) != {
        row.path for row in _v4_additions()
    }:
        raise ConstructionAccountingRegistryV4Error(
            "v4 stage ownership does not cover each addition exactly once"
        )
    if any(
        not set(row.allowed_nonzero_paths) <= set(registry.required_paths)
        for row in rules
    ):
        raise ConstructionAccountingRegistryV4Error(
            "v4 stage rule references an unknown path"
        )
    return rules


@dataclass(frozen=True, slots=True)
class StageProfileV4:
    counter_registry_id: str
    v3_stage_profile_id: str
    rules: tuple[StageRuleV4, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        parse_content_id(self.v3_stage_profile_id)
        if (
            len(self.rules) != EXPECTED_V4_STAGE_COUNT
            or tuple(sorted(
                self.rules, key=lambda row: row.stage_kind.value
            )) != self.rules
            or {row.stage_kind for row in self.rules}
            != set(ConstructionStageKindV4)
        ):
            raise ConstructionAccountingRegistryV4Error(
                "v4 stage profile must cover each stage exactly once"
            )

    @property
    def by_stage(self) -> dict[ConstructionStageKindV4, StageRuleV4]:
        return {row.stage_kind: row for row in self.rules}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_stage_profile.v4",
            "schema_version": SCHEMA_VERSION,
            "profile_key": STAGE_PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "v3_stage_profile_id": self.v3_stage_profile_id,
            "rules": [row.to_document() for row in self.rules],
            "v3_stage_ownership_preserved_exactly": True,
            "build_projection_and_prior_binding_owned_by_build_stages": True,
            "closed_private_replay_owned_by_closed_reconciliation": True,
            "v3_acquisition_paths_remain_valid_and_registered": True,
        }

    @property
    def stage_profile_id(self) -> str:
        return content_id(
            CONSTRUCTION_STAGE_PROFILE_V4_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "stage_profile_id": self.stage_profile_id}

    def validate(self, registry: CounterRegistryV4) -> None:
        registry.validate_official_catalogue()
        base = v3.official_stage_profile_v3()
        if (
            self.counter_registry_id != registry.registry_id
            or self.v3_stage_profile_id != base.stage_profile_id
            or self.rules != _expected_stage_rules_v4(registry)
        ):
            raise ConstructionAccountingRegistryV4Error(
                "official v4 stage profile changed"
            )


def official_stage_profile_v4(
    registry: CounterRegistryV4 | None = None,
) -> StageProfileV4:
    selected = registry or official_counter_registry_v4()
    base = v3.official_stage_profile_v3()
    result = StageProfileV4(
        selected.registry_id,
        base.stage_profile_id,
        _expected_stage_rules_v4(selected),
    )
    result.validate(selected)
    return result


@dataclass(frozen=True, slots=True)
class ComparisonProfileV4:
    counter_registry_id: str
    axes: tuple[ComparisonAxisV1, ...]
    terms: tuple[ProjectionTermV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        if tuple(row.name for row in self.axes) != SHARED_AXES:
            raise ConstructionAccountingRegistryV4Error(
                "v4 comparison axes changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.comparison_profile.v4",
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
            CONSTRUCTION_COMPARISON_PROFILE_V4_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "comparison_profile_id": self.comparison_profile_id,
        }

    def validate(self, registry: CounterRegistryV4) -> None:
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
            raise ConstructionAccountingRegistryV4Error(
                "official v4 comparison profile changed"
            )


def official_comparison_profile_v4(
    registry: CounterRegistryV4 | None = None,
) -> ComparisonProfileV4:
    selected = registry or official_counter_registry_v4()
    result = ComparisonProfileV4(
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
class ActualProjectionProfileV4:
    counter_registry_id: str
    comparison_profile_id: str
    terms: tuple[ProjectionTermV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        parse_content_id(self.comparison_profile_id)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.actual_projection_profile.v4",
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
            CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V4_DOMAIN,
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
        registry: CounterRegistryV4,
        comparison: ComparisonProfileV4,
    ) -> None:
        comparison.validate(registry)
        if (
            self.counter_registry_id != registry.registry_id
            or self.comparison_profile_id
            != comparison.comparison_profile_id
            or self.terms != comparison.terms
        ):
            raise ConstructionAccountingRegistryV4Error(
                "official v4 actual-projection profile changed"
            )


def official_actual_projection_profile_v4(
    registry: CounterRegistryV4 | None = None,
    comparison: ComparisonProfileV4 | None = None,
) -> ActualProjectionProfileV4:
    selected = registry or official_counter_registry_v4()
    selected_comparison = (
        comparison or official_comparison_profile_v4(selected)
    )
    result = ActualProjectionProfileV4(
        selected.registry_id,
        selected_comparison.comparison_profile_id,
        selected_comparison.terms,
    )
    result.validate(selected, selected_comparison)
    return result


def freeze_construction_accounting_registry_v4() -> dict[str, Any]:
    """Return fresh canonical documents without issuing work evidence."""

    registry = official_counter_registry_v4()
    stage = official_stage_profile_v4(registry)
    comparison = official_comparison_profile_v4(registry)
    actual = official_actual_projection_profile_v4(
        registry, comparison
    )
    return {
        "counter_registry": registry.to_document(),
        "stage_profile": stage.to_document(),
        "comparison_profile": comparison.to_document(),
        "actual_projection_profile": actual.to_document(),
    }
