"""Adaptive-world-model operation families for construction accounting V7.

V6 remains immutable.  V7 preserves every V6 leaf document and adds only the
native event families used by the observation-driven W5/K6 campaign.  The new
leaves distinguish already-paid model construction from certificate-triggered
local refinement while projecting both onto the same shared resource axes.

This module freezes the catalogue and projections.  It does not by itself
issue events, receipts, WorkVectors, a Counter Completeness result, scalar
economics, or official execution authority.
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
    RouteKindEnum,
    WorkVectorV1,
    official_shared_axes_v1,
)
from acfqp import construction_accounting_registry_v6 as v6
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V7_DOMAIN,
    CONSTRUCTION_COMPARISON_PROFILE_V7_DOMAIN,
    CONSTRUCTION_COUNTER_REGISTRY_V7_DOMAIN,
    CONSTRUCTION_STAGE_PROFILE_V7_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "7.0.0"
COUNTER_REGISTRY_KEY = "acfqp_counter_registry_v7"
STAGE_PROFILE_KEY = "construction_stage_exclusivity_v7"
COMPARISON_PROFILE_KEY = "comparison_profile_shared_resources_v7"
ACTUAL_PROJECTION_PROFILE_KEY = "actual_projection_construction_v7"

EXPECTED_V6_LEAF_COUNT = v6.EXPECTED_V6_LEAF_COUNT
EXPECTED_V6_OPERATIONAL_LEAF_COUNT = v6.EXPECTED_V6_OPERATIONAL_LEAF_COUNT
EXPECTED_V6_REQUIRED_LEAF_COUNT = v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
EXPECTED_V7_ADDITION_COUNT = 19
EXPECTED_V7_OPERATIONAL_ADDITION_COUNT = 17
EXPECTED_V7_LEAF_COUNT = 228
EXPECTED_V7_OPERATIONAL_LEAF_COUNT = 199
EXPECTED_V7_REQUIRED_LEAF_COUNT = 221
EXPECTED_V7_STAGE_COUNT = v6.EXPECTED_V6_STAGE_COUNT

ConstructionStageKindV7 = v6.ConstructionStageKindV6

_OBSERVER = "transition_tuple_observer_v1"
_ACQUISITION = "observation_support_graph_acquisition_v1"
_MODEL = "observation_support_graph_model_v1"
_PROGRAM = "construction_k7_observed_capability_program_synthesis_v1"
_CATALOGUE = "construction_k7_heldout_reusable_model_catalogue_v1"
_PROMOTION = "construction_k7_observation_driven_world_model_synthesis_v1"
_REFINEMENT = "observation_support_coordinate_refinement_v1"


class ConstructionAccountingRegistryV7Error(ValueError):
    """The V7 adaptive catalogue or projection changed."""


def _operational(
    path: str,
    semantics_id: str,
    owner: str,
    unit: str,
    scope: str,
    axis: str = NONKERNEL_COMPUTE_EVENTS,
) -> CounterSemanticsV1:
    return CounterSemanticsV1(
        path,
        semantics_id,
        owner,
        unit,
        LaneEnum.OPERATIONAL,
        scope,
        ReducerEnum.SUM,
        axis,
        True,
    )


def _diagnostic(
    path: str,
    semantics_id: str,
    owner: str,
    unit: str,
    scope: str,
) -> CounterSemanticsV1:
    return CounterSemanticsV1(
        path,
        semantics_id,
        owner,
        unit,
        LaneEnum.DIAGNOSTIC,
        scope,
        ReducerEnum.SUM,
        None,
        True,
    )


def _v7_additions() -> tuple[CounterSemanticsV1, ...]:
    common_scope = "adaptive_world_model_common_prefix_or_abstract_certificate"
    local_scope = "adaptive_world_model_local_refinement"
    rows = (
        _operational(
            "common.model_acquisition_ground_draws",
            "adaptive-model-ground-draw-v7-common",
            _OBSERVER,
            "ground_draws",
            common_scope,
            KERNEL_TRANSITION_CALLS,
        ),
        _operational(
            "common.model_acquisition_random_word_calls",
            "adaptive-model-random-word-v7-common",
            _OBSERVER,
            "random_word_calls",
            common_scope,
        ),
        _diagnostic(
            "common.model_acquisition_rejections",
            "adaptive-model-random-rejection-v7-common",
            _OBSERVER,
            "rejections",
            common_scope,
        ),
        _operational(
            "common.model_outcome_projections",
            "adaptive-model-outcome-projection-v7-common",
            _ACQUISITION,
            "outcome_projections",
            common_scope,
        ),
        _operational(
            "common.model_support_confidence_builds",
            "adaptive-model-support-confidence-build-v7-common",
            _ACQUISITION,
            "confidence_builds",
            common_scope,
        ),
        _operational(
            "common.model_bridge_rows_built",
            "adaptive-model-bridge-row-build-v7-common",
            _MODEL,
            "model_rows",
            common_scope,
        ),
        _operational(
            "common.constructor_program_candidate_evaluations",
            "adaptive-constructor-program-candidate-eval-v7",
            _PROGRAM,
            "candidate_evaluations",
            common_scope,
        ),
        _operational(
            "common.model_catalogue_selection_evaluations",
            "adaptive-model-catalogue-selection-v7",
            _CATALOGUE,
            "selection_evaluations",
            common_scope,
        ),
        _operational(
            "local.model_acquisition_ground_draws",
            "adaptive-model-ground-draw-v7-local",
            _OBSERVER,
            "ground_draws",
            local_scope,
            KERNEL_TRANSITION_CALLS,
        ),
        _operational(
            "local.model_acquisition_random_word_calls",
            "adaptive-model-random-word-v7-local",
            _OBSERVER,
            "random_word_calls",
            local_scope,
        ),
        _diagnostic(
            "local.model_acquisition_rejections",
            "adaptive-model-random-rejection-v7-local",
            _OBSERVER,
            "rejections",
            local_scope,
        ),
        _operational(
            "local.model_outcome_projections",
            "adaptive-model-outcome-projection-v7-local",
            _ACQUISITION,
            "outcome_projections",
            local_scope,
        ),
        _operational(
            "local.model_support_confidence_builds",
            "adaptive-model-support-confidence-build-v7-local",
            _ACQUISITION,
            "confidence_builds",
            local_scope,
        ),
        _operational(
            "local.model_bridge_rows_built",
            "adaptive-model-bridge-row-build-v7-local",
            _MODEL,
            "model_rows",
            local_scope,
        ),
        _operational(
            "local.model_catalogue_promotion_events",
            "adaptive-model-catalogue-promotion-v7",
            _PROMOTION,
            "promotion_events",
            local_scope,
        ),
        _operational(
            "local.model_coordinate_candidate_evaluations",
            "adaptive-coordinate-candidate-evaluation-v7",
            _REFINEMENT,
            "candidate_evaluations",
            local_scope,
        ),
        _operational(
            "local.model_coordinate_candidate_rows_built",
            "adaptive-coordinate-candidate-row-build-v7",
            _REFINEMENT,
            "model_rows",
            local_scope,
        ),
        _operational(
            "local.model_coordinate_candidate_bellman_backups",
            "adaptive-coordinate-candidate-bellman-backup-v7",
            _REFINEMENT,
            "backups",
            local_scope,
        ),
        _operational(
            "local.model_coordinate_candidate_audit_obligations",
            "adaptive-coordinate-candidate-audit-obligation-v7",
            _REFINEMENT,
            "obligations",
            local_scope,
        ),
    )
    result = tuple(sorted(rows, key=lambda row: row.path))
    if (
        len(result) != EXPECTED_V7_ADDITION_COUNT
        or len({row.path for row in result}) != len(result)
        or sum(row.lane is LaneEnum.OPERATIONAL for row in result)
        != EXPECTED_V7_OPERATIONAL_ADDITION_COUNT
    ):
        raise ConstructionAccountingRegistryV7Error("V7 addition catalogue changed")
    return result


@dataclass(frozen=True, slots=True)
class CounterRegistryV7:
    registry_key: str
    schema_version: str
    v6_registry_id: str
    leaves: tuple[CounterSemanticsV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.v6_registry_id)
        if (
            self.registry_key != COUNTER_REGISTRY_KEY
            or self.schema_version != SCHEMA_VERSION
            or tuple(sorted(self.leaves, key=lambda row: row.path)) != self.leaves
            or len({row.path for row in self.leaves}) != len(self.leaves)
        ):
            raise ConstructionAccountingRegistryV7Error("V7 registry shape changed")

    @property
    def by_path(self) -> dict[str, CounterSemanticsV1]:
        return {row.path: row for row in self.leaves}

    @property
    def operational_leaves(self) -> tuple[CounterSemanticsV1, ...]:
        return tuple(row for row in self.leaves if row.lane is LaneEnum.OPERATIONAL)

    @property
    def required_paths(self) -> tuple[str, ...]:
        return tuple(row.path for row in self.leaves if row.required)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.counter_registry.v7",
            "schema_version": self.schema_version,
            "counter_registry_key": self.registry_key,
            "v6_registry_id": self.v6_registry_id,
            "leaves": [row.to_dict() for row in self.leaves],
            "v6_leaf_documents_preserved_exactly": True,
            "adaptive_addition_count": EXPECTED_V7_ADDITION_COUNT,
            "common_and_local_acquisition_provenance_separated": True,
            "shared_comparison_axes_unchanged": True,
            "runtime_operation_emitters_installed": False,
            "operation_family_completeness_claimed": False,
            "counter_completeness_gate_passed": False,
            "workload_economics_gate_passed": False,
            "official_execution_allowed": False,
        }

    @property
    def registry_id(self) -> str:
        return content_id(CONSTRUCTION_COUNTER_REGISTRY_V7_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counter_registry_id": self.registry_id}

    def validate_official_catalogue(self) -> None:
        if self != _expected_registry_v7():
            raise ConstructionAccountingRegistryV7Error("official V7 registry changed")

    def validate_vector(self, vector: WorkVectorV1) -> None:
        self.validate_official_catalogue()
        if (
            type(vector) is not WorkVectorV1
            or vector.counter_registry_id != self.registry_id
            or tuple(sorted(vector.records, key=lambda row: row.path)) != vector.records
            or len({row.path for row in vector.records}) != len(vector.records)
        ):
            raise ConstructionAccountingRegistryV7Error("V7 WorkVector shape changed")
        for row in vector.records:
            leaf = self.by_path.get(row.path)
            if leaf is None or row.counter_registry_id != self.registry_id:
                raise ConstructionAccountingRegistryV7Error("V7 WorkVector crossed its registry")
            row.verify_against(leaf)
        values = vector.values
        if set(self.required_paths) - set(values):
            raise ConstructionAccountingRegistryV7Error("V7 WorkVector omits required records")
        for total, successes, failures in (
            ("route.attempts", "route.successes", "route.failures"),
            ("solver.attempts", "solver.successes", "solver.failures"),
        ):
            if total in values and values[total] != values[successes] + values[failures]:
                raise ConstructionAccountingRegistryV7Error(f"V7 reconciliation failed for {total}")
        if "process.exit_successes" in values and values["process.launches"] != (
            values["process.exit_successes"] + values["process.exit_failures"]
        ):
            raise ConstructionAccountingRegistryV7Error("V7 process reconciliation failed")
        if any(
            values.get(path, 0) > values["io.output_bytes"]
            for path in ("epoch.serialized_bytes", "model.serialized_bytes", "capability.serialized_bytes")
        ) or values.get("branch.evaluations", 0):
            raise ConstructionAccountingRegistryV7Error("V7 derived work was double charged")
        if vector.route_kind is RouteKindEnum.LOCAL_ATTEMPT:
            forbidden = ("fallback.", "rebuild.")
        elif vector.route_kind is RouteKindEnum.DIRECT_FALLBACK:
            forbidden = ("local.", "rebuild.")
        elif vector.route_kind in {
            RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        }:
            forbidden = ("local.", "fallback.", "rebuild.")
        elif vector.route_kind is RouteKindEnum.REBUILD:
            forbidden = ("common.", "local.", "fallback.", "control.")
        else:  # pragma: no cover
            raise ConstructionAccountingRegistryV7Error("unknown V7 route kind")
        nonzero = tuple(
            path
            for path, value in values.items()
            if value and any(path.startswith(prefix) for prefix in forbidden)
        )
        if nonzero:
            raise ConstructionAccountingRegistryV7Error(
                f"V7 route-family exclusivity failed: {nonzero!r}"
            )


def _expected_registry_v7() -> CounterRegistryV7:
    base = v6.official_counter_registry_v6()
    base.validate_official_catalogue()
    additions = _v7_additions()
    if (
        len(base.leaves) != EXPECTED_V6_LEAF_COUNT
        or len(base.operational_leaves) != EXPECTED_V6_OPERATIONAL_LEAF_COUNT
        or len(base.required_paths) != EXPECTED_V6_REQUIRED_LEAF_COUNT
        or set(base.by_path) & {row.path for row in additions}
    ):
        raise ConstructionAccountingRegistryV7Error("V6 prefix changed before V7")
    return CounterRegistryV7(
        COUNTER_REGISTRY_KEY,
        SCHEMA_VERSION,
        base.registry_id,
        tuple(sorted((*base.leaves, *additions), key=lambda row: row.path)),
    )


def official_counter_registry_v7() -> CounterRegistryV7:
    result = _expected_registry_v7()
    if (
        len(result.leaves) != EXPECTED_V7_LEAF_COUNT
        or len(result.operational_leaves) != EXPECTED_V7_OPERATIONAL_LEAF_COUNT
        or len(result.required_paths) != EXPECTED_V7_REQUIRED_LEAF_COUNT
    ):
        raise ConstructionAccountingRegistryV7Error("V7 registry cardinality changed")
    return result


_ADDITION_STAGE = {
    "common.model_catalogue_selection_evaluations": ConstructionStageKindV7.PREOPEN_COMMON_PREFIX,
    "common.model_acquisition_ground_draws": ConstructionStageKindV7.INITIAL_ACQUISITION,
    "common.model_acquisition_random_word_calls": ConstructionStageKindV7.INITIAL_ACQUISITION,
    "common.model_acquisition_rejections": ConstructionStageKindV7.INITIAL_ACQUISITION,
    "common.model_outcome_projections": ConstructionStageKindV7.INITIAL_ACQUISITION,
    "common.model_support_confidence_builds": ConstructionStageKindV7.INITIAL_ACQUISITION,
    "common.model_bridge_rows_built": ConstructionStageKindV7.INITIAL_MODEL_BUILD,
    "common.constructor_program_candidate_evaluations": ConstructionStageKindV7.INITIAL_MODEL_BUILD,
    "local.model_acquisition_ground_draws": ConstructionStageKindV7.OPEN_INCREMENTAL_ACQUISITION,
    "local.model_acquisition_random_word_calls": ConstructionStageKindV7.OPEN_INCREMENTAL_ACQUISITION,
    "local.model_acquisition_rejections": ConstructionStageKindV7.OPEN_INCREMENTAL_ACQUISITION,
    "local.model_outcome_projections": ConstructionStageKindV7.OPEN_INCREMENTAL_ACQUISITION,
    "local.model_support_confidence_builds": ConstructionStageKindV7.OPEN_INCREMENTAL_ACQUISITION,
    "local.model_bridge_rows_built": ConstructionStageKindV7.OPEN_CHECKPOINT_REPLANNING,
    "local.model_catalogue_promotion_events": ConstructionStageKindV7.CLOSED_RECONCILIATION_AND_TERMINALIZATION,
    "local.model_coordinate_candidate_evaluations": ConstructionStageKindV7.OPEN_CHECKPOINT_REPLANNING,
    "local.model_coordinate_candidate_rows_built": ConstructionStageKindV7.OPEN_CHECKPOINT_REPLANNING,
    "local.model_coordinate_candidate_bellman_backups": ConstructionStageKindV7.OPEN_CHECKPOINT_REPLANNING,
    "local.model_coordinate_candidate_audit_obligations": ConstructionStageKindV7.OPEN_CHECKPOINT_REPLANNING,
}


@dataclass(frozen=True, slots=True)
class StageProfileV7:
    counter_registry_id: str
    v6_stage_profile_id: str
    rules: tuple[v6.StageRuleV6, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        parse_content_id(self.v6_stage_profile_id)
        if (
            len(self.rules) != EXPECTED_V7_STAGE_COUNT
            or tuple(sorted(self.rules, key=lambda row: row.stage_kind.value)) != self.rules
            or {row.stage_kind for row in self.rules} != set(ConstructionStageKindV7)
        ):
            raise ConstructionAccountingRegistryV7Error("V7 stage profile changed")

    @property
    def by_stage(self) -> dict[ConstructionStageKindV7, v6.StageRuleV6]:
        return {row.stage_kind: row for row in self.rules}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_stage_profile.v7",
            "schema_version": SCHEMA_VERSION,
            "profile_key": STAGE_PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "v6_stage_profile_id": self.v6_stage_profile_id,
            "rules": [row.to_document() for row in self.rules],
            "v6_stage_ownership_preserved_exactly": True,
            "adaptive_additions_routed_exactly_once": True,
            "runtime_stage_attribution_verified": False,
        }

    @property
    def stage_profile_id(self) -> str:
        return content_id(CONSTRUCTION_STAGE_PROFILE_V7_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "stage_profile_id": self.stage_profile_id}

    def validate(self, registry: CounterRegistryV7) -> None:
        expected = _expected_stage_rules_v7(registry)
        base = v6.official_stage_profile_v6()
        if (
            self.counter_registry_id != registry.registry_id
            or self.v6_stage_profile_id != base.stage_profile_id
            or self.rules != expected
        ):
            raise ConstructionAccountingRegistryV7Error("V7 stage binding changed")


def _expected_stage_rules_v7(registry: CounterRegistryV7) -> tuple[v6.StageRuleV6, ...]:
    base = v6.official_stage_profile_v6()
    rules = tuple(
        sorted(
            (
                v6.StageRuleV6(
                    row.stage_kind,
                    tuple(
                        sorted(
                            set(row.allowed_nonzero_paths)
                            | {path for path, stage in _ADDITION_STAGE.items() if stage is row.stage_kind}
                        )
                    ),
                )
                for row in base.rules
            ),
            key=lambda row: row.stage_kind.value,
        )
    )
    if set(_ADDITION_STAGE) != {row.path for row in _v7_additions()} or any(
        not set(row.allowed_nonzero_paths) <= set(registry.required_paths) for row in rules
    ):
        raise ConstructionAccountingRegistryV7Error("V7 stage ownership is incomplete")
    return rules


def official_stage_profile_v7(registry: CounterRegistryV7 | None = None) -> StageProfileV7:
    selected = registry or official_counter_registry_v7()
    base = v6.official_stage_profile_v6()
    result = StageProfileV7(
        selected.registry_id, base.stage_profile_id, _expected_stage_rules_v7(selected)
    )
    result.validate(selected)
    return result


@dataclass(frozen=True, slots=True)
class ComparisonProfileV7:
    counter_registry_id: str
    axes: tuple[ComparisonAxisV1, ...]
    terms: tuple[ProjectionTermV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        if tuple(row.name for row in self.axes) != SHARED_AXES:
            raise ConstructionAccountingRegistryV7Error("V7 comparison axes changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.comparison_profile.v7",
            "schema_version": SCHEMA_VERSION,
            "profile_key": COMPARISON_PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "axes": [row.to_dict() for row in self.axes],
            "terms": [row.to_dict() for row in self.terms],
            "scalar_cost_defined": False,
        }

    @property
    def comparison_profile_id(self) -> str:
        return content_id(CONSTRUCTION_COMPARISON_PROFILE_V7_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "comparison_profile_id": self.comparison_profile_id}

    def validate(self, registry: CounterRegistryV7) -> None:
        expected = tuple(
            ProjectionTermV1(
                row.path, row.comparison_axis, 1, row.lane, row.semantics_id, row.reducer
            )
            for row in registry.operational_leaves
        )
        if (
            self.counter_registry_id != registry.registry_id
            or self.axes != official_shared_axes_v1()
            or self.terms != expected
            or len({row.source_leaf for row in self.terms}) != len(self.terms)
        ):
            raise ConstructionAccountingRegistryV7Error("V7 comparison profile changed")


def official_comparison_profile_v7(
    registry: CounterRegistryV7 | None = None,
) -> ComparisonProfileV7:
    selected = registry or official_counter_registry_v7()
    result = ComparisonProfileV7(
        selected.registry_id,
        official_shared_axes_v1(),
        tuple(
            ProjectionTermV1(
                row.path, row.comparison_axis, 1, row.lane, row.semantics_id, row.reducer
            )
            for row in selected.operational_leaves
        ),
    )
    result.validate(selected)
    return result


@dataclass(frozen=True, slots=True)
class ActualProjectionProfileV7:
    counter_registry_id: str
    comparison_profile_id: str
    terms: tuple[ProjectionTermV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        parse_content_id(self.comparison_profile_id)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.actual_projection_profile.v7",
            "schema_version": SCHEMA_VERSION,
            "profile_key": ACTUAL_PROJECTION_PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "terms": [row.to_dict() for row in self.terms],
            "caller_supplied_actual_comparison_allowed": False,
        }

    @property
    def actual_projection_profile_id(self) -> str:
        return content_id(CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V7_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "actual_projection_profile_id": self.actual_projection_profile_id}

    def validate(self, registry: CounterRegistryV7, comparison: ComparisonProfileV7) -> None:
        comparison.validate(registry)
        if (
            self.counter_registry_id != registry.registry_id
            or self.comparison_profile_id != comparison.comparison_profile_id
            or self.terms != comparison.terms
        ):
            raise ConstructionAccountingRegistryV7Error("V7 projection profile changed")


def official_actual_projection_profile_v7(
    registry: CounterRegistryV7 | None = None,
    comparison: ComparisonProfileV7 | None = None,
) -> ActualProjectionProfileV7:
    selected = registry or official_counter_registry_v7()
    selected_comparison = comparison or official_comparison_profile_v7(selected)
    result = ActualProjectionProfileV7(
        selected.registry_id,
        selected_comparison.comparison_profile_id,
        selected_comparison.terms,
    )
    result.validate(selected, selected_comparison)
    return result


def freeze_construction_accounting_registry_v7() -> dict[str, Any]:
    registry = official_counter_registry_v7()
    stage = official_stage_profile_v7(registry)
    comparison = official_comparison_profile_v7(registry)
    actual = official_actual_projection_profile_v7(registry, comparison)
    return {
        "counter_registry": registry.to_document(),
        "stage_profile": stage.to_document(),
        "comparison_profile": comparison.to_document(),
        "actual_projection_profile": actual.to_document(),
    }


__all__ = (
    "ACTUAL_PROJECTION_PROFILE_KEY",
    "COMPARISON_PROFILE_KEY",
    "COUNTER_REGISTRY_KEY",
    "ConstructionAccountingRegistryV7Error",
    "ConstructionStageKindV7",
    "EXPECTED_V7_ADDITION_COUNT",
    "EXPECTED_V7_LEAF_COUNT",
    "EXPECTED_V7_OPERATIONAL_ADDITION_COUNT",
    "EXPECTED_V7_OPERATIONAL_LEAF_COUNT",
    "EXPECTED_V7_REQUIRED_LEAF_COUNT",
    "SCHEMA_VERSION",
    "STAGE_PROFILE_KEY",
    "freeze_construction_accounting_registry_v7",
    "official_actual_projection_profile_v7",
    "official_comparison_profile_v7",
    "official_counter_registry_v7",
    "official_stage_profile_v7",
)
