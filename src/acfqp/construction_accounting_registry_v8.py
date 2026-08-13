"""V8 accounting leaves for target execution and independent exact replay.

V8 is additive over V7.  It closes two gaps exposed by the standard-2048
campaign: the actual online target transition was not a canonical cost leaf,
and the matched exact replay had no typed evaluation-lane operation family.
No outcome, WorkVector, Counter Completeness, scalar, or official authority is
issued by this registry module alone.
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
from acfqp import construction_accounting_registry_v7 as v7
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V8_DOMAIN,
    CONSTRUCTION_COMPARISON_PROFILE_V8_DOMAIN,
    CONSTRUCTION_COUNTER_REGISTRY_V8_DOMAIN,
    CONSTRUCTION_STAGE_PROFILE_V8_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "8.0.0"
COUNTER_REGISTRY_KEY = "acfqp_counter_registry_v8"
STAGE_PROFILE_KEY = "construction_stage_exclusivity_v8"
COMPARISON_PROFILE_KEY = "comparison_profile_shared_resources_v8"
ACTUAL_PROJECTION_PROFILE_KEY = "actual_projection_construction_v8"

EXPECTED_V7_LEAF_COUNT = v7.EXPECTED_V7_LEAF_COUNT
EXPECTED_V7_OPERATIONAL_LEAF_COUNT = v7.EXPECTED_V7_OPERATIONAL_LEAF_COUNT
EXPECTED_V7_REQUIRED_LEAF_COUNT = v7.EXPECTED_V7_REQUIRED_LEAF_COUNT
EXPECTED_V8_ADDITION_COUNT = 14
EXPECTED_V8_OPERATIONAL_ADDITION_COUNT = 4
EXPECTED_V8_EVALUATION_ADDITION_COUNT = 6
EXPECTED_V8_DIAGNOSTIC_ADDITION_COUNT = 4
EXPECTED_V8_LEAF_COUNT = 242
EXPECTED_V8_OPERATIONAL_LEAF_COUNT = 203
EXPECTED_V8_REQUIRED_LEAF_COUNT = 235


class ConstructionAccountingRegistryV8Error(ValueError):
    """The additive V8 catalogue, projection, or lane boundary changed."""


def _leaf(
    path: str,
    semantics_id: str,
    owner: str,
    unit: str,
    lane: LaneEnum,
    scope: str,
    axis: str | None,
) -> CounterSemanticsV1:
    return CounterSemanticsV1(
        path,
        semantics_id,
        owner,
        unit,
        lane,
        scope,
        ReducerEnum.SUM,
        axis,
        True,
    )


def _v8_additions() -> tuple[CounterSemanticsV1, ...]:
    rows = (
        _leaf(
            "common.abstract_subproof_cache_lookups",
            "abstract-subproof-cache-lookup-v8",
            "standard_2048_factored_bellman_v12",
            "lookups",
            LaneEnum.OPERATIONAL,
            "logical_occurrence_abstract_certificate",
            NONKERNEL_COMPUTE_EVENTS,
        ),
        _leaf(
            "common.abstract_subproof_cache_hits",
            "abstract-subproof-cache-hit-v8",
            "standard_2048_factored_bellman_v12",
            "hits",
            LaneEnum.DIAGNOSTIC,
            "logical_occurrence_abstract_certificate",
            None,
        ),
        _leaf(
            "common.abstract_subproof_cache_misses",
            "abstract-subproof-cache-miss-v8",
            "standard_2048_factored_bellman_v12",
            "misses",
            LaneEnum.DIAGNOSTIC,
            "logical_occurrence_abstract_certificate",
            None,
        ),
        _leaf(
            "target.execution_ground_steps",
            "target-ground-transition-call-v8",
            "standard_2048_target_executor_v12",
            "calls",
            LaneEnum.OPERATIONAL,
            "logical_occurrence_target_execution",
            KERNEL_TRANSITION_CALLS,
        ),
        _leaf(
            "target.execution_outcome_rows",
            "target-outcome-row-enumeration-v8",
            "standard_2048_target_executor_v12",
            "rows",
            LaneEnum.OPERATIONAL,
            "logical_occurrence_target_execution",
            NONKERNEL_COMPUTE_EVENTS,
        ),
        _leaf(
            "target.transition_observations",
            "target-transition-observation-v8",
            "standard_2048_target_executor_v12",
            "observations",
            LaneEnum.OPERATIONAL,
            "logical_occurrence_target_execution",
            NONKERNEL_COMPUTE_EVENTS,
        ),
        _leaf(
            "evaluation.exact_states_expanded",
            "evaluation-exact-state-stage-expand-v8",
            "standard_2048_independent_exact_replay_v12",
            "state_stage_subproblems",
            LaneEnum.EVALUATION,
            "standalone_evaluation_replay",
            None,
        ),
        _leaf(
            "evaluation.exact_actions_evaluated",
            "evaluation-exact-action-stage-eval-v8",
            "standard_2048_independent_exact_replay_v12",
            "evaluations",
            LaneEnum.EVALUATION,
            "standalone_evaluation_replay",
            None,
        ),
        _leaf(
            "evaluation.exact_ground_steps",
            "evaluation-ground-transition-call-v8",
            "standard_2048_independent_exact_replay_v12",
            "calls",
            LaneEnum.EVALUATION,
            "standalone_evaluation_replay",
            None,
        ),
        _leaf(
            "evaluation.exact_outcome_rows",
            "evaluation-ground-outcome-row-v8",
            "standard_2048_independent_exact_replay_v12",
            "rows",
            LaneEnum.EVALUATION,
            "standalone_evaluation_replay",
            None,
        ),
        _leaf(
            "evaluation.exact_bellman_backups",
            "evaluation-exact-bellman-backup-v8",
            "standard_2048_independent_exact_replay_v12",
            "backups",
            LaneEnum.EVALUATION,
            "standalone_evaluation_replay",
            None,
        ),
        _leaf(
            "evaluation.exact_subproof_cache_lookups",
            "evaluation-exact-cache-lookup-v8",
            "standard_2048_independent_exact_replay_v12",
            "lookups",
            LaneEnum.EVALUATION,
            "standalone_evaluation_replay",
            None,
        ),
        _leaf(
            "evaluation.exact_subproof_cache_hits",
            "evaluation-exact-cache-hit-v8",
            "standard_2048_independent_exact_replay_v12",
            "hits",
            LaneEnum.DIAGNOSTIC,
            "standalone_evaluation_replay",
            None,
        ),
        _leaf(
            "evaluation.exact_subproof_cache_misses",
            "evaluation-exact-cache-miss-v8",
            "standard_2048_independent_exact_replay_v12",
            "misses",
            LaneEnum.DIAGNOSTIC,
            "standalone_evaluation_replay",
            None,
        ),
    )
    result = tuple(sorted(rows, key=lambda row: row.path))
    counts = {
        lane: sum(row.lane is lane for row in result)
        for lane in (LaneEnum.OPERATIONAL, LaneEnum.EVALUATION, LaneEnum.DIAGNOSTIC)
    }
    if (
        len(result) != EXPECTED_V8_ADDITION_COUNT
        or len({row.path for row in result}) != len(result)
        or counts[LaneEnum.OPERATIONAL] != EXPECTED_V8_OPERATIONAL_ADDITION_COUNT
        or counts[LaneEnum.EVALUATION] != EXPECTED_V8_EVALUATION_ADDITION_COUNT
        or counts[LaneEnum.DIAGNOSTIC] != EXPECTED_V8_DIAGNOSTIC_ADDITION_COUNT
    ):
        raise ConstructionAccountingRegistryV8Error("V8 addition catalogue changed")
    return result


@dataclass(frozen=True, slots=True)
class CounterRegistryV8:
    registry_key: str
    schema_version: str
    v7_registry_id: str
    leaves: tuple[CounterSemanticsV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.v7_registry_id)
        if (
            self.registry_key != COUNTER_REGISTRY_KEY
            or self.schema_version != SCHEMA_VERSION
            or tuple(sorted(self.leaves, key=lambda row: row.path)) != self.leaves
            or len({row.path for row in self.leaves}) != len(self.leaves)
        ):
            raise ConstructionAccountingRegistryV8Error("V8 registry shape changed")

    @property
    def by_path(self) -> dict[str, CounterSemanticsV1]:
        return {row.path: row for row in self.leaves}

    @property
    def operational_leaves(self) -> tuple[CounterSemanticsV1, ...]:
        return tuple(row for row in self.leaves if row.lane is LaneEnum.OPERATIONAL)

    @property
    def evaluation_leaves(self) -> tuple[CounterSemanticsV1, ...]:
        return tuple(row for row in self.leaves if row.lane is LaneEnum.EVALUATION)

    @property
    def required_paths(self) -> tuple[str, ...]:
        return tuple(row.path for row in self.leaves if row.required)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.counter_registry.v8",
            "schema_version": self.schema_version,
            "counter_registry_key": self.registry_key,
            "v7_registry_id": self.v7_registry_id,
            "leaves": [row.to_dict() for row in self.leaves],
            "v7_leaf_documents_preserved_exactly": True,
            "target_execution_is_operational": True,
            "evaluation_replay_is_nonoperational": True,
            "evaluation_leaves_have_no_comparison_projection": True,
            "shared_comparison_axes_unchanged": True,
            "runtime_operation_emitters_installed": False,
            "counter_completeness_gate_passed": False,
            "workload_economics_gate_passed": False,
            "official_execution_allowed": False,
        }

    @property
    def registry_id(self) -> str:
        return content_id(CONSTRUCTION_COUNTER_REGISTRY_V8_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counter_registry_id": self.registry_id}

    def validate_official_catalogue(self) -> None:
        if self != _expected_registry_v8():
            raise ConstructionAccountingRegistryV8Error("official V8 registry changed")

    def validate_vector(self, vector: WorkVectorV1) -> None:
        self.validate_official_catalogue()
        if (
            type(vector) is not WorkVectorV1
            or vector.counter_registry_id != self.registry_id
            or tuple(sorted(vector.records, key=lambda row: row.path)) != vector.records
            or len({row.path for row in vector.records}) != len(vector.records)
        ):
            raise ConstructionAccountingRegistryV8Error("V8 WorkVector shape changed")
        for row in vector.records:
            leaf = self.by_path.get(row.path)
            if leaf is None or row.counter_registry_id != self.registry_id:
                raise ConstructionAccountingRegistryV8Error("V8 WorkVector crossed its registry")
            row.verify_against(leaf)
        values = vector.values
        if set(self.required_paths) - set(values):
            raise ConstructionAccountingRegistryV8Error("V8 WorkVector omits required records")
        for total, successes, failures in (
            ("route.attempts", "route.successes", "route.failures"),
            ("solver.attempts", "solver.successes", "solver.failures"),
        ):
            if total in values and values[total] != values[successes] + values[failures]:
                raise ConstructionAccountingRegistryV8Error(f"V8 reconciliation failed for {total}")
        if "process.exit_successes" in values and values["process.launches"] != (
            values["process.exit_successes"] + values["process.exit_failures"]
        ):
            raise ConstructionAccountingRegistryV8Error("V8 process reconciliation failed")
        if any(
            values.get(path, 0) > values["io.output_bytes"]
            for path in (
                "epoch.serialized_bytes",
                "model.serialized_bytes",
                "capability.serialized_bytes",
            )
        ) or values.get("branch.evaluations", 0):
            raise ConstructionAccountingRegistryV8Error("V8 derived work was double charged")
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
            raise ConstructionAccountingRegistryV8Error("unknown V8 route kind")
        nonzero = tuple(
            path
            for path, value in values.items()
            if value and any(path.startswith(prefix) for prefix in forbidden)
        )
        if nonzero:
            raise ConstructionAccountingRegistryV8Error(
                f"V8 route-family exclusivity failed: {nonzero!r}"
            )


def _expected_registry_v8() -> CounterRegistryV8:
    base = v7.official_counter_registry_v7()
    base.validate_official_catalogue()
    additions = _v8_additions()
    if (
        len(base.leaves) != EXPECTED_V7_LEAF_COUNT
        or len(base.operational_leaves) != EXPECTED_V7_OPERATIONAL_LEAF_COUNT
        or len(base.required_paths) != EXPECTED_V7_REQUIRED_LEAF_COUNT
        or set(base.by_path) & {row.path for row in additions}
    ):
        raise ConstructionAccountingRegistryV8Error("V7 prefix changed before V8")
    return CounterRegistryV8(
        COUNTER_REGISTRY_KEY,
        SCHEMA_VERSION,
        base.registry_id,
        tuple(sorted((*base.leaves, *additions), key=lambda row: row.path)),
    )


def official_counter_registry_v8() -> CounterRegistryV8:
    result = _expected_registry_v8()
    if (
        len(result.leaves) != EXPECTED_V8_LEAF_COUNT
        or len(result.operational_leaves) != EXPECTED_V8_OPERATIONAL_LEAF_COUNT
        or len(result.required_paths) != EXPECTED_V8_REQUIRED_LEAF_COUNT
    ):
        raise ConstructionAccountingRegistryV8Error("V8 registry cardinality changed")
    return result


@dataclass(frozen=True, slots=True)
class StageProfileV8:
    counter_registry_id: str
    v7_stage_profile_id: str
    v7_rules: tuple[Any, ...]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_stage_profile.v8",
            "schema_version": SCHEMA_VERSION,
            "profile_key": STAGE_PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "v7_stage_profile_id": self.v7_stage_profile_id,
            "v7_construction_rules": [row.to_document() for row in self.v7_rules],
            "v7_construction_stage_ownership_preserved_exactly": True,
            "target_execution_owned_by_route_execution_not_construction_stage": True,
            "evaluation_replay_owned_by_standalone_verifier": True,
            "runtime_stage_attribution_verified": False,
        }

    @property
    def stage_profile_id(self) -> str:
        return content_id(CONSTRUCTION_STAGE_PROFILE_V8_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "stage_profile_id": self.stage_profile_id}

    def validate(self, registry: CounterRegistryV8) -> None:
        base = v7.official_stage_profile_v7()
        if (
            self.counter_registry_id != registry.registry_id
            or self.v7_stage_profile_id != base.stage_profile_id
            or self.v7_rules != base.rules
        ):
            raise ConstructionAccountingRegistryV8Error("V8 stage binding changed")


def official_stage_profile_v8(
    registry: CounterRegistryV8 | None = None,
) -> StageProfileV8:
    selected = registry or official_counter_registry_v8()
    base = v7.official_stage_profile_v7()
    result = StageProfileV8(selected.registry_id, base.stage_profile_id, base.rules)
    result.validate(selected)
    return result


@dataclass(frozen=True, slots=True)
class ComparisonProfileV8:
    counter_registry_id: str
    axes: tuple[ComparisonAxisV1, ...]
    terms: tuple[ProjectionTermV1, ...]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.comparison_profile.v8",
            "schema_version": SCHEMA_VERSION,
            "profile_key": COMPARISON_PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "axes": [row.to_dict() for row in self.axes],
            "terms": [row.to_dict() for row in self.terms],
            "evaluation_lanes_excluded": True,
            "scalar_cost_defined": False,
        }

    @property
    def comparison_profile_id(self) -> str:
        return content_id(CONSTRUCTION_COMPARISON_PROFILE_V8_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "comparison_profile_id": self.comparison_profile_id}

    def validate(self, registry: CounterRegistryV8) -> None:
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
            or tuple(row.name for row in self.axes) != SHARED_AXES
            or self.terms != expected
            or len({row.source_leaf for row in self.terms}) != len(self.terms)
        ):
            raise ConstructionAccountingRegistryV8Error("V8 comparison profile changed")


def official_comparison_profile_v8(
    registry: CounterRegistryV8 | None = None,
) -> ComparisonProfileV8:
    selected = registry or official_counter_registry_v8()
    result = ComparisonProfileV8(
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
class ActualProjectionProfileV8:
    counter_registry_id: str
    comparison_profile_id: str
    terms: tuple[ProjectionTermV1, ...]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.actual_projection_profile.v8",
            "schema_version": SCHEMA_VERSION,
            "profile_key": ACTUAL_PROJECTION_PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "terms": [row.to_dict() for row in self.terms],
            "evaluation_lanes_excluded": True,
            "caller_supplied_actual_comparison_allowed": False,
        }

    @property
    def actual_projection_profile_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V8_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "actual_projection_profile_id": self.actual_projection_profile_id,
        }

    def validate(
        self, registry: CounterRegistryV8, comparison: ComparisonProfileV8
    ) -> None:
        comparison.validate(registry)
        if (
            self.counter_registry_id != registry.registry_id
            or self.comparison_profile_id != comparison.comparison_profile_id
            or self.terms != comparison.terms
        ):
            raise ConstructionAccountingRegistryV8Error("V8 projection profile changed")


def official_actual_projection_profile_v8(
    registry: CounterRegistryV8 | None = None,
    comparison: ComparisonProfileV8 | None = None,
) -> ActualProjectionProfileV8:
    selected = registry or official_counter_registry_v8()
    selected_comparison = comparison or official_comparison_profile_v8(selected)
    result = ActualProjectionProfileV8(
        selected.registry_id,
        selected_comparison.comparison_profile_id,
        selected_comparison.terms,
    )
    result.validate(selected, selected_comparison)
    return result


def freeze_construction_accounting_registry_v8() -> dict[str, Any]:
    registry = official_counter_registry_v8()
    stage = official_stage_profile_v8(registry)
    comparison = official_comparison_profile_v8(registry)
    actual = official_actual_projection_profile_v8(registry, comparison)
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
    "ConstructionAccountingRegistryV8Error",
    "EXPECTED_V8_ADDITION_COUNT",
    "EXPECTED_V8_EVALUATION_ADDITION_COUNT",
    "EXPECTED_V8_LEAF_COUNT",
    "EXPECTED_V8_OPERATIONAL_ADDITION_COUNT",
    "EXPECTED_V8_OPERATIONAL_LEAF_COUNT",
    "EXPECTED_V8_REQUIRED_LEAF_COUNT",
    "SCHEMA_VERSION",
    "STAGE_PROFILE_KEY",
    "freeze_construction_accounting_registry_v8",
    "official_actual_projection_profile_v8",
    "official_comparison_profile_v8",
    "official_counter_registry_v8",
    "official_stage_profile_v8",
)
