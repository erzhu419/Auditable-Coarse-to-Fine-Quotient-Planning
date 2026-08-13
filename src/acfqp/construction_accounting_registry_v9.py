"""Additive accounting leaves for synthesized-model construction and replay.

V8 accounts target execution, abstract planning, fallback, and independent
ground replay.  It does not have native semantics for the operations used to
propose and prove the observation-derived 2048 expression model.  V9 adds
those operation families without relabelling any V8 leaf.

The scalar target-probability interface is deliberately charged as a
registered non-kernel computation event: it returns one dynamics label and is
not a state-action transition evaluation.  Sample labels remain separately
reportable; they are never silently converted into ground-transition calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Any

from acfqp import construction_accounting_registry_v8 as v8
from acfqp.accounting_v1 import (
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
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V9_DOMAIN,
    CONSTRUCTION_COMPARISON_PROFILE_V9_DOMAIN,
    CONSTRUCTION_COUNTER_REGISTRY_V9_DOMAIN,
    CONSTRUCTION_STAGE_PROFILE_V9_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "9.0.0"
COUNTER_REGISTRY_KEY = "acfqp_counter_registry_v9"
STAGE_PROFILE_KEY = "construction_stage_exclusivity_v9"
COMPARISON_PROFILE_KEY = "comparison_profile_shared_resources_v9"
ACTUAL_PROJECTION_PROFILE_KEY = "actual_projection_construction_v9"

EXPECTED_V8_LEAF_COUNT = v8.EXPECTED_V8_LEAF_COUNT
EXPECTED_V8_OPERATIONAL_LEAF_COUNT = v8.EXPECTED_V8_OPERATIONAL_LEAF_COUNT
EXPECTED_V8_REQUIRED_LEAF_COUNT = v8.EXPECTED_V8_REQUIRED_LEAF_COUNT
EXPECTED_V9_OPERATIONAL_ADDITION_COUNT = 8
EXPECTED_V9_EVALUATION_ADDITION_COUNT = 8
EXPECTED_V9_ADDITION_COUNT = 16
EXPECTED_V9_LEAF_COUNT = 269
EXPECTED_V9_OPERATIONAL_LEAF_COUNT = 213
EXPECTED_V9_REQUIRED_LEAF_COUNT = 262


class ConstructionAccountingRegistryV9Error(ValueError):
    """The V9 model-synthesis accounting contract changed."""


class ModelSynthesisStageKindV9(str, Enum):
    ACQUISITION_AND_SELECTION = "MODEL_SYNTHESIS_ACQUISITION_AND_SELECTION"
    PROOF_AND_FREEZE = "MODEL_SYNTHESIS_PROOF_AND_FREEZE"
    STANDALONE_EVALUATION = "MODEL_SYNTHESIS_STANDALONE_EVALUATION"


def _leaf(
    path: str,
    semantics_id: str,
    owner: str,
    unit: str,
    lane: LaneEnum,
    scope: str,
) -> CounterSemanticsV1:
    return CounterSemanticsV1(
        path,
        semantics_id,
        owner,
        unit,
        lane,
        scope,
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS if lane is LaneEnum.OPERATIONAL else None,
        True,
    )


_OPERATIONAL_FAMILIES = (
    (
        "model.active_query_partition_evaluations",
        "standard-2048-active-query-partition-evaluation-v9",
        "partition_evaluations",
    ),
    (
        "model.candidate_label_consistency_checks",
        "standard-2048-candidate-label-consistency-check-v9",
        "consistency_checks",
    ),
    (
        "model.exact_program_proof_rows_evaluated",
        "standard-2048-expression-proof-row-evaluation-v9",
        "proof_rows",
    ),
    (
        "model.expression_candidates_materialized",
        "standard-2048-expression-candidate-materialization-v9",
        "candidates",
    ),
    (
        "model.structural_context_rows_frozen",
        "standard-2048-structural-context-freeze-v9",
        "context_rows",
    ),
    (
        "model.structural_expression_value_evaluations",
        "standard-2048-structural-expression-value-evaluation-v9",
        "expression_value_evaluations",
    ),
    (
        "model.target_probability_labels_acquired",
        "standard-2048-target-probability-label-query-v9",
        "scalar_probability_labels",
    ),
    (
        "model.world_model_freezes",
        "standard-2048-expression-world-model-freeze-v9",
        "world_models",
    ),
)


def _v9_additions() -> tuple[CounterSemanticsV1, ...]:
    operational = tuple(
        _leaf(
            path,
            semantics,
            "standard_2048_observation_expression_synthesizer_v24",
            unit,
            LaneEnum.OPERATIONAL,
            "registered_model_synthesis_occurrence",
        )
        for path, semantics, unit in _OPERATIONAL_FAMILIES
    )
    evaluation = tuple(
        _leaf(
            "evaluation." + path.removeprefix("model."),
            semantics.replace("-v9", "-independent-replay-v9"),
            "standard_2048_model_synthesis_independent_verifier_v24",
            unit,
            LaneEnum.EVALUATION,
            "standalone_model_synthesis_replay",
        )
        for path, semantics, unit in _OPERATIONAL_FAMILIES
    )
    result = tuple(sorted((*operational, *evaluation), key=lambda row: row.path))
    if (
        len(result) != EXPECTED_V9_ADDITION_COUNT
        or len({row.path for row in result}) != len(result)
        or sum(row.lane is LaneEnum.OPERATIONAL for row in result)
        != EXPECTED_V9_OPERATIONAL_ADDITION_COUNT
        or sum(row.lane is LaneEnum.EVALUATION for row in result)
        != EXPECTED_V9_EVALUATION_ADDITION_COUNT
    ):
        raise ConstructionAccountingRegistryV9Error("V9 addition catalogue changed")
    return result


@dataclass(frozen=True, slots=True)
class CounterRegistryV9:
    registry_key: str
    schema_version: str
    v8_registry_id: str
    leaves: tuple[CounterSemanticsV1, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.v8_registry_id)
        if (
            self.registry_key != COUNTER_REGISTRY_KEY
            or self.schema_version != SCHEMA_VERSION
            or tuple(sorted(self.leaves, key=lambda row: row.path)) != self.leaves
            or len({row.path for row in self.leaves}) != len(self.leaves)
        ):
            raise ConstructionAccountingRegistryV9Error("V9 registry shape changed")

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
            "schema": "acfqp.counter_registry.v9",
            "schema_version": self.schema_version,
            "counter_registry_key": self.registry_key,
            "v8_registry_id": self.v8_registry_id,
            "leaves": [row.to_dict() for row in self.leaves],
            "v8_leaf_documents_preserved_exactly": True,
            "model_synthesis_native_operation_families_registered": True,
            "scalar_probability_label_query_is_ground_transition_call": False,
            "scalar_probability_label_query_maps_to_nonkernel_compute_event": True,
            "sample_label_count_remains_separately_reportable": True,
            "evaluation_leaves_have_no_comparison_projection": True,
            "shared_comparison_axes_unchanged": True,
            "runtime_operation_emitters_installed": False,
            "counter_completeness_gate_passed": False,
            "workload_economics_gate_passed": False,
            "official_execution_allowed": False,
        }

    @property
    def registry_id(self) -> str:
        return _counter_registry_id(self)

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counter_registry_id": self.registry_id}

    def validate_official_catalogue(self) -> None:
        if self != _expected_registry_v9():
            raise ConstructionAccountingRegistryV9Error("official V9 registry changed")

    def validate_vector(self, vector: WorkVectorV1) -> None:
        self.validate_official_catalogue()
        if (
            type(vector) is not WorkVectorV1
            or vector.counter_registry_id != self.registry_id
            or tuple(sorted(vector.records, key=lambda row: row.path)) != vector.records
            or len({row.path for row in vector.records}) != len(vector.records)
        ):
            raise ConstructionAccountingRegistryV9Error("V9 WorkVector shape changed")
        for record in vector.records:
            leaf = self.by_path.get(record.path)
            if leaf is None or record.counter_registry_id != self.registry_id:
                raise ConstructionAccountingRegistryV9Error("V9 WorkVector crossed registry")
            record.verify_against(leaf)
        values = vector.values
        if set(self.required_paths) - set(values):
            raise ConstructionAccountingRegistryV9Error("V9 WorkVector omits records")
        for total, successes, failures in (
            ("route.attempts", "route.successes", "route.failures"),
            ("solver.attempts", "solver.successes", "solver.failures"),
        ):
            if total in values and values[total] != values[successes] + values[failures]:
                raise ConstructionAccountingRegistryV9Error("V9 reconciliation failed")
        if "process.exit_successes" in values and values["process.launches"] != (
            values["process.exit_successes"] + values["process.exit_failures"]
        ):
            raise ConstructionAccountingRegistryV9Error("V9 process reconciliation failed")
        if any(
            values.get(path, 0) > values["io.output_bytes"]
            for path in (
                "epoch.serialized_bytes",
                "model.serialized_bytes",
                "capability.serialized_bytes",
            )
        ) or values.get("branch.evaluations", 0):
            raise ConstructionAccountingRegistryV9Error("V9 derived work double charged")
        if vector.route_kind is RouteKindEnum.LOCAL_ATTEMPT:
            forbidden = ("fallback.", "rebuild.")
        elif vector.route_kind is RouteKindEnum.DIRECT_FALLBACK:
            forbidden = ("local.", "rebuild.", "model.")
        elif vector.route_kind in {
            RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        }:
            forbidden = ("local.", "fallback.", "rebuild.")
        elif vector.route_kind is RouteKindEnum.REBUILD:
            forbidden = ("common.", "local.", "fallback.", "control.", "model.")
        else:  # pragma: no cover
            raise ConstructionAccountingRegistryV9Error("unknown V9 route kind")
        if any(
            value and any(path.startswith(prefix) for prefix in forbidden)
            for path, value in values.items()
        ):
            raise ConstructionAccountingRegistryV9Error("V9 route-family exclusivity failed")


@lru_cache(maxsize=1)
def _expected_registry_v9() -> CounterRegistryV9:
    base = v8.official_counter_registry_v8()
    base.validate_official_catalogue()
    additions = _v9_additions()
    if (
        len(base.leaves) != EXPECTED_V8_LEAF_COUNT
        or len(base.operational_leaves) != EXPECTED_V8_OPERATIONAL_LEAF_COUNT
        or len(base.required_paths) != EXPECTED_V8_REQUIRED_LEAF_COUNT
        or set(base.by_path) & {row.path for row in additions}
    ):
        raise ConstructionAccountingRegistryV9Error("V8 prefix changed before V9")
    return CounterRegistryV9(
        COUNTER_REGISTRY_KEY,
        SCHEMA_VERSION,
        base.registry_id,
        tuple(sorted((*base.leaves, *additions), key=lambda row: row.path)),
    )


@lru_cache(maxsize=1)
def _counter_registry_id(registry: CounterRegistryV9) -> str:
    return content_id(CONSTRUCTION_COUNTER_REGISTRY_V9_DOMAIN, registry._payload())


@lru_cache(maxsize=1)
def official_counter_registry_v9() -> CounterRegistryV9:
    result = _expected_registry_v9()
    if (
        len(result.leaves) != EXPECTED_V9_LEAF_COUNT
        or len(result.operational_leaves) != EXPECTED_V9_OPERATIONAL_LEAF_COUNT
        or len(result.required_paths) != EXPECTED_V9_REQUIRED_LEAF_COUNT
    ):
        raise ConstructionAccountingRegistryV9Error("V9 registry cardinality changed")
    return result


@dataclass(frozen=True, slots=True)
class ModelSynthesisStageRuleV9:
    stage_kind: ModelSynthesisStageKindV9
    allowed_nonzero_paths: tuple[str, ...]

    def to_document(self) -> dict[str, Any]:
        return {
            "stage_kind": self.stage_kind.value,
            "allowed_nonzero_paths": list(self.allowed_nonzero_paths),
        }


def _model_stage_rules() -> tuple[ModelSynthesisStageRuleV9, ...]:
    acquisition = tuple(
        sorted(
            path
            for path, _, _ in _OPERATIONAL_FAMILIES
            if path
            not in {
                "model.exact_program_proof_rows_evaluated",
                "model.world_model_freezes",
            }
        )
    )
    proof = (
        "model.exact_program_proof_rows_evaluated",
        "model.world_model_freezes",
    )
    evaluation = tuple(sorted("evaluation." + path.removeprefix("model.") for path, _, _ in _OPERATIONAL_FAMILIES))
    return (
        ModelSynthesisStageRuleV9(ModelSynthesisStageKindV9.ACQUISITION_AND_SELECTION, acquisition),
        ModelSynthesisStageRuleV9(ModelSynthesisStageKindV9.PROOF_AND_FREEZE, proof),
        ModelSynthesisStageRuleV9(ModelSynthesisStageKindV9.STANDALONE_EVALUATION, evaluation),
    )


@dataclass(frozen=True, slots=True)
class StageProfileV9:
    counter_registry_id: str
    v8_stage_profile_id: str
    v8_rules: tuple[Any, ...]
    model_synthesis_rules: tuple[ModelSynthesisStageRuleV9, ...]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_stage_profile.v9",
            "schema_version": SCHEMA_VERSION,
            "profile_key": STAGE_PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "v8_stage_profile_id": self.v8_stage_profile_id,
            "v8_construction_rules": [row.to_document() for row in self.v8_rules],
            "model_synthesis_rules": [row.to_document() for row in self.model_synthesis_rules],
            "model_synthesis_and_route_execution_are_distinct_stages": True,
            "standalone_evaluation_is_nonoperational": True,
            "runtime_stage_attribution_verified": False,
        }

    @property
    def stage_profile_id(self) -> str:
        return _stage_profile_id(self)

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "stage_profile_id": self.stage_profile_id}

    def validate(self, registry: CounterRegistryV9) -> None:
        base = v8.official_stage_profile_v8()
        if (
            self.counter_registry_id != registry.registry_id
            or self.v8_stage_profile_id != base.stage_profile_id
            or self.v8_rules != base.v7_rules
            or self.model_synthesis_rules != _model_stage_rules()
        ):
            raise ConstructionAccountingRegistryV9Error("V9 stage binding changed")


@lru_cache(maxsize=2)
def official_stage_profile_v9(registry: CounterRegistryV9 | None = None) -> StageProfileV9:
    selected = registry or official_counter_registry_v9()
    base = v8.official_stage_profile_v8()
    result = StageProfileV9(
        selected.registry_id,
        base.stage_profile_id,
        base.v7_rules,
        _model_stage_rules(),
    )
    result.validate(selected)
    return result


@lru_cache(maxsize=1)
def _stage_profile_id(profile: StageProfileV9) -> str:
    return content_id(CONSTRUCTION_STAGE_PROFILE_V9_DOMAIN, profile._payload())


@dataclass(frozen=True, slots=True)
class ComparisonProfileV9:
    counter_registry_id: str
    axes: tuple[ComparisonAxisV1, ...]
    terms: tuple[ProjectionTermV1, ...]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.comparison_profile.v9",
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
        return _comparison_profile_id(self)

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "comparison_profile_id": self.comparison_profile_id}

    def validate(self, registry: CounterRegistryV9) -> None:
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
            raise ConstructionAccountingRegistryV9Error("V9 comparison profile changed")


@lru_cache(maxsize=2)
def official_comparison_profile_v9(registry: CounterRegistryV9 | None = None) -> ComparisonProfileV9:
    selected = registry or official_counter_registry_v9()
    result = ComparisonProfileV9(
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


@lru_cache(maxsize=1)
def _comparison_profile_id(profile: ComparisonProfileV9) -> str:
    return content_id(CONSTRUCTION_COMPARISON_PROFILE_V9_DOMAIN, profile._payload())


@dataclass(frozen=True, slots=True)
class ActualProjectionProfileV9:
    counter_registry_id: str
    comparison_profile_id: str
    terms: tuple[ProjectionTermV1, ...]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.actual_projection_profile.v9",
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
        return _actual_projection_profile_id(self)

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "actual_projection_profile_id": self.actual_projection_profile_id}

    def validate(self, registry: CounterRegistryV9, comparison: ComparisonProfileV9) -> None:
        comparison.validate(registry)
        if (
            self.counter_registry_id != registry.registry_id
            or self.comparison_profile_id != comparison.comparison_profile_id
            or self.terms != comparison.terms
        ):
            raise ConstructionAccountingRegistryV9Error("V9 projection profile changed")


@lru_cache(maxsize=4)
def official_actual_projection_profile_v9(
    registry: CounterRegistryV9 | None = None,
    comparison: ComparisonProfileV9 | None = None,
) -> ActualProjectionProfileV9:
    selected = registry or official_counter_registry_v9()
    selected_comparison = comparison or official_comparison_profile_v9(selected)
    result = ActualProjectionProfileV9(
        selected.registry_id,
        selected_comparison.comparison_profile_id,
        selected_comparison.terms,
    )
    result.validate(selected, selected_comparison)
    return result


@lru_cache(maxsize=1)
def _actual_projection_profile_id(profile: ActualProjectionProfileV9) -> str:
    return content_id(
        CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V9_DOMAIN,
        profile._payload(),
    )


def freeze_construction_accounting_registry_v9() -> dict[str, Any]:
    registry = official_counter_registry_v9()
    stage = official_stage_profile_v9(registry)
    comparison = official_comparison_profile_v9(registry)
    actual = official_actual_projection_profile_v9(registry, comparison)
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
    "ConstructionAccountingRegistryV9Error",
    "EXPECTED_V9_ADDITION_COUNT",
    "EXPECTED_V9_EVALUATION_ADDITION_COUNT",
    "EXPECTED_V9_LEAF_COUNT",
    "EXPECTED_V9_OPERATIONAL_ADDITION_COUNT",
    "EXPECTED_V9_OPERATIONAL_LEAF_COUNT",
    "EXPECTED_V9_REQUIRED_LEAF_COUNT",
    "ModelSynthesisStageKindV9",
    "SCHEMA_VERSION",
    "STAGE_PROFILE_KEY",
    "freeze_construction_accounting_registry_v9",
    "official_actual_projection_profile_v9",
    "official_comparison_profile_v9",
    "official_counter_registry_v9",
    "official_stage_profile_v9",
)
