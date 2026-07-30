"""Construction-stage native accounting schemas.

This module is the additive accounting-v2 schema promised by contract 1.84.
It does not translate legacy V0-075 summary counters and it does not claim
that any production runner is instrumented.  It freezes:

* the immutable 49-leaf Phase-3E v1 catalogue as an exact prefix;
* thirteen construction BUILD/ACQUISITION leaves plus seven distinct
  closed-reconciliation/terminalization leaves;
* stage-specific nonzero exclusivity;
* the unchanged eight shared comparison axes;
* exact native-record -> WorkVector -> ComparisonVector projection.

The mutable recorder is only a mechanism for an owner that is already active
at the beginning of a stage.  A sealed vector must bind a separate,
content-addressed stage-completion attestation; this module does not mint or
verify that semantic authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Iterable, Mapping

from acfqp.accounting_v1 import (
    KERNEL_TRANSITION_CALLS,
    NONKERNEL_COMPUTE_EVENTS,
    OUTPUT_BYTES,
    PEAK_MOUNTED_BYTES,
    PEAK_WORKING_BYTES,
    PROCESS_LAUNCHES,
    READ_BYTES,
    SHARED_AXES,
    STAGED_BYTES,
    ComparisonAxisV1,
    CounterSemanticsV1,
    LaneEnum,
    ProjectionTermV1,
    ReducerEnum,
    official_counter_registry_v1,
    official_shared_axes_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V2_DOMAIN,
    CONSTRUCTION_ACTUAL_PROJECTION_PROOF_V2_DOMAIN,
    CONSTRUCTION_COMPARISON_PROFILE_V2_DOMAIN,
    CONSTRUCTION_COMPARISON_VECTOR_V2_DOMAIN,
    CONSTRUCTION_COUNTER_RECORD_V2_DOMAIN,
    CONSTRUCTION_COUNTER_REGISTRY_V2_DOMAIN,
    CONSTRUCTION_STAGE_PROFILE_V2_DOMAIN,
    CONSTRUCTION_WORK_VECTOR_V2_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "2.0.0"
COUNTER_REGISTRY_KEY = "acfqp_counter_registry_v2"
COMPARISON_PROFILE_KEY = "comparison_profile_shared_resources_v2"
ACTUAL_PROJECTION_PROFILE_KEY = "actual_projection_construction_v2"
STAGE_PROFILE_KEY = "construction_stage_exclusivity_v2"

EXPECTED_BASE_LEAF_COUNT = 49
EXPECTED_BASE_OPERATIONAL_LEAF_COUNT = 34
EXPECTED_V2_LEAF_COUNT = 69
EXPECTED_V2_OPERATIONAL_LEAF_COUNT = 53
EXPECTED_V2_REQUIRED_LEAF_COUNT = 62

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")


class ConstructionAccountingV2Error(ValueError):
    """A v2 construction-accounting artifact is malformed or incomplete."""


class StageKindV2(str, Enum):
    PREOPEN_COMMON_PREFIX = "PREOPEN_COMMON_PREFIX"
    INITIAL_ACQUISITION = "INITIAL_ACQUISITION"
    INITIAL_MODEL_BUILD = "INITIAL_MODEL_BUILD"
    FAILED_ABSTRACT_PREFIX = "FAILED_ABSTRACT_PREFIX"
    CLOSED_RECONCILIATION_AND_TERMINALIZATION = (
        "CLOSED_RECONCILIATION_AND_TERMINALIZATION"
    )
    LOCAL_ATTEMPT = "LOCAL_ATTEMPT"
    DIRECT_FALLBACK = "DIRECT_FALLBACK"
    REBUILD = "REBUILD"


def _identifier(value: Any, field: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ConstructionAccountingV2Error(
            f"{field} must be a canonical identifier"
        )
    return value


def _nonnegative(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ConstructionAccountingV2Error(
            f"{field} must be a nonnegative exact integer"
        )
    return value


def _stage(value: Any) -> StageKindV2:
    try:
        return StageKindV2(value)
    except (TypeError, ValueError) as error:
        raise ConstructionAccountingV2Error(
            f"unknown construction stage: {value!r}"
        ) from error


def _new_operational_leaf(
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


def _new_required_diagnostic_leaf(
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


def _construction_leaves() -> tuple[CounterSemanticsV1, ...]:
    """Return scoped construction additions with non-overlapping semantics."""

    rows = (
        _new_operational_leaf(
            "acquisition.initial_observer_accepted_draws",
            "v075-initial-observer-accepted-draw-v2",
            "v075_private_observer_boundary_v2",
            "accepted_draws",
            "construction_occurrence_initial_acquisition_prefix",
            KERNEL_TRANSITION_CALLS,
        ),
        _new_operational_leaf(
            "acquisition.initial_observer_random_word_calls",
            "v075-initial-observer-random-word-call-v2",
            "v075_private_observer_boundary_v2",
            "random_word_calls",
            "construction_occurrence_initial_acquisition_prefix",
        ),
        _new_required_diagnostic_leaf(
            "acquisition.initial_observer_rejections",
            "v075-initial-observer-rejection-v2",
            "v075_private_observer_boundary_v2",
            "rejections",
            "construction_occurrence_initial_acquisition_prefix",
        ),
        _new_operational_leaf(
            "acquisition.initial_outcome_aggregate_rows",
            "v075-initial-outcome-aggregate-row-materialization-v2",
            "v075_private_observer_boundary_v2",
            "aggregate_rows",
            "construction_occurrence_initial_acquisition_prefix",
        ),
        _new_operational_leaf(
            "acquisition.initial_signed_batches",
            "v075-initial-signed-batch-materialization-v2",
            "v075_private_observer_boundary_v2",
            "signed_batches",
            "construction_occurrence_initial_acquisition_prefix",
        ),
        _new_operational_leaf(
            "acquisition.initial_support_freezes",
            "v075-initial-support-freeze-materialization-v2",
            "v075_observer_signed_batch_control_authority_v2",
            "support_freezes",
            "construction_occurrence_initial_acquisition_prefix",
        ),
        _new_operational_leaf(
            "build.initial_interval_log_search_evaluations",
            "v075-initial-interval-log-search-eval-v2",
            "v075_batch_native_planning_backend_v2",
            "log_search_evaluations",
            "construction_occurrence_initial_build_epoch",
        ),
        _new_operational_leaf(
            "build.initial_interval_row_evaluations",
            "v075-initial-interval-row-eval-v2",
            "v075_batch_native_planning_backend_v2",
            "row_behavior_evaluations",
            "construction_occurrence_initial_build_epoch",
        ),
        _new_operational_leaf(
            "build.initial_model_rows_built",
            "v075-initial-model-row-build-v2",
            "v075_live_incremental_model_authority_v2",
            "model_rows",
            "construction_occurrence_initial_build_epoch",
        ),
        _new_operational_leaf(
            "build.initial_policy_assignments_evaluated",
            "v075-initial-policy-assignment-eval-v2",
            "v075_batch_native_planning_backend_v2",
            "policy_assignments",
            "construction_occurrence_initial_build_epoch",
        ),
        _new_operational_leaf(
            "build.initial_semantic_record_replays",
            "v075-initial-semantic-record-replay-v2",
            "v075_semantic_replay_instrumentation_v2",
            "record_replays",
            "construction_occurrence_initial_build_epoch",
        ),
        _new_operational_leaf(
            "build.initial_semantic_role_closures",
            "v075-initial-semantic-role-closure-v2",
            "v075_semantic_replay_instrumentation_v2",
            "role_closures",
            "construction_occurrence_initial_build_epoch",
        ),
        _new_operational_leaf(
            "build.initial_source_units_compiled",
            "v075-initial-row-source-unit-compile-v2",
            "v075_live_incremental_model_authority_v2",
            "row_source_units",
            "construction_occurrence_initial_build_epoch",
        ),
        _new_operational_leaf(
            "closure.reconciliation_interval_log_search_evaluations",
            "v075-closed-reconciliation-interval-log-search-eval-v2",
            "v075_batch_native_planning_backend_v2",
            "log_search_evaluations",
            "construction_occurrence_closed_reconciliation_and_terminalization",
        ),
        _new_operational_leaf(
            "closure.reconciliation_interval_row_evaluations",
            "v075-closed-reconciliation-interval-row-eval-v2",
            "v075_batch_native_planning_backend_v2",
            "row_behavior_evaluations",
            "construction_occurrence_closed_reconciliation_and_terminalization",
        ),
        _new_operational_leaf(
            "closure.reconciliation_model_rows_built",
            "v075-closed-reconciliation-model-row-build-v2",
            "v075_live_incremental_model_authority_v2",
            "model_rows",
            "construction_occurrence_closed_reconciliation_and_terminalization",
        ),
        _new_operational_leaf(
            "closure.reconciliation_policy_assignments_evaluated",
            "v075-closed-reconciliation-policy-assignment-eval-v2",
            "v075_batch_native_planning_backend_v2",
            "policy_assignments",
            "construction_occurrence_closed_reconciliation_and_terminalization",
        ),
        _new_operational_leaf(
            "closure.reconciliation_semantic_record_replays",
            "v075-closed-reconciliation-semantic-record-replay-v2",
            "v075_semantic_replay_instrumentation_v2",
            "record_replays",
            "construction_occurrence_closed_reconciliation_and_terminalization",
        ),
        _new_operational_leaf(
            "closure.reconciliation_semantic_role_closures",
            "v075-closed-reconciliation-semantic-role-closure-v2",
            "v075_semantic_replay_instrumentation_v2",
            "role_closures",
            "construction_occurrence_closed_reconciliation_and_terminalization",
        ),
        _new_operational_leaf(
            "closure.reconciliation_source_units_compiled",
            "v075-closed-reconciliation-row-source-unit-compile-v2",
            "v075_live_incremental_model_authority_v2",
            "row_source_units",
            "construction_occurrence_closed_reconciliation_and_terminalization",
        ),
    )
    return tuple(sorted(rows, key=lambda row: row.path))


@dataclass(frozen=True, slots=True)
class CounterRegistryV2:
    registry_key: str
    schema_version: str
    base_counter_registry_id: str
    leaves: tuple[CounterSemanticsV1, ...]

    def __post_init__(self) -> None:
        _identifier(self.registry_key, "registry_key")
        _identifier(self.schema_version, "schema_version")
        parse_content_id(self.base_counter_registry_id)
        if (
            not self.leaves
            or tuple(sorted(self.leaves, key=lambda row: row.path))
            != self.leaves
            or len({row.path for row in self.leaves}) != len(self.leaves)
        ):
            raise ConstructionAccountingV2Error(
                "registry leaves must be nonempty, unique, and path-sorted"
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
            "schema": "acfqp.counter_registry.v2",
            "schema_version": self.schema_version,
            "registry_key": self.registry_key,
            "base_counter_registry_id": self.base_counter_registry_id,
            "base_registry_is_immutable_exact_prefix": True,
            "leaves": [row.to_dict() for row in self.leaves],
        }

    @property
    def registry_id(self) -> str:
        return content_id(
            CONSTRUCTION_COUNTER_REGISTRY_V2_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counter_registry_id": self.registry_id}

    def validate_official_catalogue(self) -> None:
        expected = _expected_registry_v2()
        if (
            self.registry_key != expected.registry_key
            or self.schema_version != expected.schema_version
            or self.base_counter_registry_id
            != expected.base_counter_registry_id
            or self.leaves != expected.leaves
        ):
            raise ConstructionAccountingV2Error(
                "official construction counter catalogue changed"
            )

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> "CounterRegistryV2":
        expected = {
            "schema",
            "schema_version",
            "registry_key",
            "base_counter_registry_id",
            "base_registry_is_immutable_exact_prefix",
            "leaves",
            "counter_registry_id",
        }
        if type(document) is not dict or set(document) != expected:
            raise ConstructionAccountingV2Error(
                "counter registry field set mismatch"
            )
        if (
            document["schema"] != "acfqp.counter_registry.v2"
            or document["base_registry_is_immutable_exact_prefix"] is not True
            or type(document["leaves"]) is not list
        ):
            raise ConstructionAccountingV2Error(
                "counter registry schema/prefix marker mismatch"
            )
        result = cls(
            document["registry_key"],
            document["schema_version"],
            document["base_counter_registry_id"],
            tuple(
                CounterSemanticsV1.from_dict(row)
                for row in document["leaves"]
            ),
        )
        result.validate_official_catalogue()
        if document["counter_registry_id"] != result.registry_id:
            raise ConstructionAccountingV2Error(
                "counter registry content ID mismatch"
            )
        return result


def _expected_registry_v2() -> CounterRegistryV2:
    base = official_counter_registry_v1()
    base.validate_official_catalogue()
    if (
        len(base.leaves) != EXPECTED_BASE_LEAF_COUNT
        or len(base.operational_leaves)
        != EXPECTED_BASE_OPERATIONAL_LEAF_COUNT
    ):
        raise ConstructionAccountingV2Error(
            "immutable accounting-v1 prefix changed"
        )
    additions = _construction_leaves()
    if set(base.by_path) & {row.path for row in additions}:
        raise ConstructionAccountingV2Error(
            "construction additions overlap accounting-v1"
        )
    return CounterRegistryV2(
        COUNTER_REGISTRY_KEY,
        SCHEMA_VERSION,
        base.registry_id,
        tuple(sorted((*base.leaves, *additions), key=lambda row: row.path)),
    )


def official_counter_registry_v2() -> CounterRegistryV2:
    result = _expected_registry_v2()
    if (
        len(result.leaves) != EXPECTED_V2_LEAF_COUNT
        or len(result.operational_leaves)
        != EXPECTED_V2_OPERATIONAL_LEAF_COUNT
        or len(result.required_paths) != EXPECTED_V2_REQUIRED_LEAF_COUNT
    ):
        raise ConstructionAccountingV2Error(
            "construction registry cardinality changed"
        )
    result.validate_official_catalogue()
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
class StageRuleV2:
    stage_kind: StageKindV2
    allowed_nonzero_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        if (
            tuple(sorted(self.allowed_nonzero_paths))
            != self.allowed_nonzero_paths
            or len(set(self.allowed_nonzero_paths))
            != len(self.allowed_nonzero_paths)
        ):
            raise ConstructionAccountingV2Error(
                "stage allowed paths must be unique and sorted"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "stage_kind": self.stage_kind.value,
            "allowed_nonzero_paths": list(self.allowed_nonzero_paths),
        }

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> "StageRuleV2":
        if (
            type(document) is not dict
            or set(document)
            != {"stage_kind", "allowed_nonzero_paths"}
            or type(document["allowed_nonzero_paths"]) is not list
        ):
            raise ConstructionAccountingV2Error(
                "stage rule field set mismatch"
            )
        return cls(
            document["stage_kind"],
            tuple(document["allowed_nonzero_paths"]),
        )


def _prefix_paths(
    registry: CounterRegistryV2, *prefixes: str
) -> frozenset[str]:
    return frozenset(
        path
        for path in registry.required_paths
        if any(path.startswith(prefix) for prefix in prefixes)
    )


def _expected_stage_rules(
    registry: CounterRegistryV2,
) -> tuple[StageRuleV2, ...]:
    build_initial = frozenset(
        {
            "build.initial_interval_log_search_evaluations",
            "build.initial_interval_row_evaluations",
            "build.initial_model_rows_built",
            "build.initial_policy_assignments_evaluated",
            "build.initial_semantic_record_replays",
            "build.initial_semantic_role_closures",
            "build.initial_source_units_compiled",
        }
    )
    abstract = frozenset(
        {
            "common.abstract_audit_obligations",
            "common.abstract_bellman_backups",
        }
    )
    rows = {
        StageKindV2.PREOPEN_COMMON_PREFIX: _COMMON_RUNTIME_PATHS,
        StageKindV2.INITIAL_ACQUISITION: (
            _COMMON_RUNTIME_PATHS
            | _prefix_paths(registry, "acquisition.")
        ),
        StageKindV2.INITIAL_MODEL_BUILD: (
            _COMMON_RUNTIME_PATHS | build_initial
        ),
        StageKindV2.FAILED_ABSTRACT_PREFIX: (
            _COMMON_RUNTIME_PATHS | abstract
        ),
        StageKindV2.CLOSED_RECONCILIATION_AND_TERMINALIZATION: (
            _COMMON_RUNTIME_PATHS
            | frozenset(
                {
                    "route.attempts",
                    "route.failures",
                    "route.successes",
                }
            )
            | _prefix_paths(registry, "closure.")
        ),
        StageKindV2.LOCAL_ATTEMPT: (
            _COMMON_RUNTIME_PATHS
            | _ROUTE_RECONCILIATION_PATHS
            | _prefix_paths(registry, "local.", "control.")
        ),
        StageKindV2.DIRECT_FALLBACK: (
            _COMMON_RUNTIME_PATHS
            | _ROUTE_RECONCILIATION_PATHS
            | _prefix_paths(registry, "fallback.", "control.")
        ),
        StageKindV2.REBUILD: (
            _COMMON_RUNTIME_PATHS | _prefix_paths(registry, "rebuild.")
        ),
    }
    return tuple(
        StageRuleV2(stage, tuple(sorted(paths)))
        for stage, paths in sorted(rows.items(), key=lambda item: item[0].value)
    )


@dataclass(frozen=True, slots=True)
class StageProfileV2:
    profile_key: str
    schema_version: str
    counter_registry_id: str
    rules: tuple[StageRuleV2, ...]

    def __post_init__(self) -> None:
        _identifier(self.profile_key, "stage profile key")
        _identifier(self.schema_version, "stage profile schema version")
        parse_content_id(self.counter_registry_id)
        if (
            tuple(sorted(self.rules, key=lambda row: row.stage_kind.value))
            != self.rules
            or len({row.stage_kind for row in self.rules}) != len(self.rules)
            or {row.stage_kind for row in self.rules} != set(StageKindV2)
        ):
            raise ConstructionAccountingV2Error(
                "stage profile must cover each stage exactly once"
            )

    @property
    def by_stage(self) -> dict[StageKindV2, StageRuleV2]:
        return {row.stage_kind: row for row in self.rules}

    def validate(self, registry: CounterRegistryV2) -> None:
        registry.validate_official_catalogue()
        expected = _expected_stage_rules(registry)
        if (
            self.profile_key != STAGE_PROFILE_KEY
            or self.schema_version != SCHEMA_VERSION
            or self.counter_registry_id != registry.registry_id
            or self.rules != expected
        ):
            raise ConstructionAccountingV2Error(
                "official construction stage profile changed"
            )
        known = set(registry.required_paths)
        for rule in self.rules:
            if not set(rule.allowed_nonzero_paths) <= known:
                raise ConstructionAccountingV2Error(
                    "stage profile references unknown/non-required paths"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_stage_profile.v2",
            "schema_version": self.schema_version,
            "profile_key": self.profile_key,
            "counter_registry_id": self.counter_registry_id,
            "rules": [row.to_document() for row in self.rules],
        }

    @property
    def stage_profile_id(self) -> str:
        return content_id(
            CONSTRUCTION_STAGE_PROFILE_V2_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "stage_profile_id": self.stage_profile_id}

    @classmethod
    def from_document(
        cls,
        document: Mapping[str, Any],
        registry: CounterRegistryV2,
    ) -> "StageProfileV2":
        expected = {
            "schema",
            "schema_version",
            "profile_key",
            "counter_registry_id",
            "rules",
            "stage_profile_id",
        }
        if (
            type(document) is not dict
            or set(document) != expected
            or document["schema"]
            != "acfqp.construction_stage_profile.v2"
            or type(document["rules"]) is not list
        ):
            raise ConstructionAccountingV2Error(
                "stage profile field set mismatch"
            )
        result = cls(
            document["profile_key"],
            document["schema_version"],
            document["counter_registry_id"],
            tuple(
                StageRuleV2.from_document(row)
                for row in document["rules"]
            ),
        )
        result.validate(registry)
        if document["stage_profile_id"] != result.stage_profile_id:
            raise ConstructionAccountingV2Error(
                "stage profile content ID mismatch"
            )
        return result


def official_stage_profile_v2(
    registry: CounterRegistryV2 | None = None,
) -> StageProfileV2:
    selected = registry or official_counter_registry_v2()
    result = StageProfileV2(
        STAGE_PROFILE_KEY,
        SCHEMA_VERSION,
        selected.registry_id,
        _expected_stage_rules(selected),
    )
    result.validate(selected)
    return result


@dataclass(frozen=True, slots=True)
class ComparisonProfileV2:
    profile_key: str
    schema_version: str
    counter_registry_id: str
    axes: tuple[ComparisonAxisV1, ...]
    terms: tuple[ProjectionTermV1, ...]

    def __post_init__(self) -> None:
        _identifier(self.profile_key, "comparison profile key")
        _identifier(self.schema_version, "comparison profile version")
        parse_content_id(self.counter_registry_id)
        if (
            tuple(sorted(self.axes, key=lambda row: row.name)) != self.axes
            or len({row.name for row in self.axes}) != len(self.axes)
            or tuple(sorted(self.terms, key=lambda row: row.source_leaf))
            != self.terms
            or len({row.source_leaf for row in self.terms})
            != len(self.terms)
        ):
            raise ConstructionAccountingV2Error(
                "comparison axes/terms must be unique and sorted"
            )

    def validate(self, registry: CounterRegistryV2) -> None:
        registry.validate_official_catalogue()
        if (
            self.profile_key != COMPARISON_PROFILE_KEY
            or self.schema_version != SCHEMA_VERSION
            or self.counter_registry_id != registry.registry_id
            or self.axes != official_shared_axes_v1()
        ):
            raise ConstructionAccountingV2Error(
                "comparison profile identity or axes changed"
            )
        expected = {row.path for row in registry.operational_leaves}
        actual = {row.source_leaf for row in self.terms}
        if actual != expected:
            raise ConstructionAccountingV2Error(
                "comparison projection does not cover each operational leaf"
            )
        by_axis = {row.name: row for row in self.axes}
        for term in self.terms:
            leaf = registry.by_path[term.source_leaf]
            if (
                term.source_lane is not LaneEnum.OPERATIONAL
                or term.source_semantics_id != leaf.semantics_id
                or term.coefficient != 1
                or term.target_axis != leaf.comparison_axis
                or term.reducer is not leaf.reducer
                or by_axis[term.target_axis].reducer is not term.reducer
            ):
                raise ConstructionAccountingV2Error(
                    f"invalid comparison projection for {term.source_leaf}"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.comparison_profile.v2",
            "schema_version": self.schema_version,
            "profile_key": self.profile_key,
            "counter_registry_id": self.counter_registry_id,
            "axes": [row.to_dict() for row in self.axes],
            "terms": [row.to_dict() for row in self.terms],
        }

    @property
    def comparison_profile_id(self) -> str:
        return content_id(
            CONSTRUCTION_COMPARISON_PROFILE_V2_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "comparison_profile_id": self.comparison_profile_id,
        }

    @classmethod
    def from_document(
        cls,
        document: Mapping[str, Any],
        registry: CounterRegistryV2,
    ) -> "ComparisonProfileV2":
        expected = {
            "schema",
            "schema_version",
            "profile_key",
            "counter_registry_id",
            "axes",
            "terms",
            "comparison_profile_id",
        }
        if (
            type(document) is not dict
            or set(document) != expected
            or document["schema"] != "acfqp.comparison_profile.v2"
            or type(document["axes"]) is not list
            or type(document["terms"]) is not list
        ):
            raise ConstructionAccountingV2Error(
                "comparison profile field set mismatch"
            )
        result = cls(
            document["profile_key"],
            document["schema_version"],
            document["counter_registry_id"],
            tuple(
                ComparisonAxisV1.from_dict(row)
                for row in document["axes"]
            ),
            tuple(
                ProjectionTermV1.from_dict(row)
                for row in document["terms"]
            ),
        )
        result.validate(registry)
        if document["comparison_profile_id"] != result.comparison_profile_id:
            raise ConstructionAccountingV2Error(
                "comparison profile content ID mismatch"
            )
        return result


def official_comparison_profile_v2(
    registry: CounterRegistryV2 | None = None,
) -> ComparisonProfileV2:
    selected = registry or official_counter_registry_v2()
    axes = official_shared_axes_v1()
    by_axis = {row.name: row for row in axes}
    terms = tuple(
        ProjectionTermV1(
            source_leaf=leaf.path,
            target_axis=leaf.comparison_axis or "",
            coefficient=1,
            source_lane=leaf.lane,
            source_semantics_id=leaf.semantics_id,
            reducer=by_axis[leaf.comparison_axis or ""].reducer,
        )
        for leaf in selected.operational_leaves
    )
    result = ComparisonProfileV2(
        COMPARISON_PROFILE_KEY,
        SCHEMA_VERSION,
        selected.registry_id,
        axes,
        terms,
    )
    result.validate(selected)
    return result


@dataclass(frozen=True, slots=True)
class ActualProjectionProfileV2:
    profile_key: str
    schema_version: str
    counter_registry_id: str
    comparison_profile_id: str
    terms: tuple[ProjectionTermV1, ...]

    def __post_init__(self) -> None:
        _identifier(self.profile_key, "actual projection profile key")
        _identifier(self.schema_version, "actual projection profile version")
        parse_content_id(self.counter_registry_id)
        parse_content_id(self.comparison_profile_id)
        if (
            tuple(sorted(self.terms, key=lambda row: row.source_leaf))
            != self.terms
            or len({row.source_leaf for row in self.terms})
            != len(self.terms)
        ):
            raise ConstructionAccountingV2Error(
                "actual projection terms must be unique and sorted"
            )

    def validate(
        self,
        registry: CounterRegistryV2,
        comparison: ComparisonProfileV2,
    ) -> None:
        comparison.validate(registry)
        if (
            self.profile_key != ACTUAL_PROJECTION_PROFILE_KEY
            or self.schema_version != SCHEMA_VERSION
            or self.counter_registry_id != registry.registry_id
            or self.comparison_profile_id
            != comparison.comparison_profile_id
            or self.terms != comparison.terms
        ):
            raise ConstructionAccountingV2Error(
                "actual projection profile differs from exact comparison"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.actual_projection_profile.v2",
            "schema_version": self.schema_version,
            "profile_key": self.profile_key,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "terms": [row.to_dict() for row in self.terms],
        }

    @property
    def actual_projection_profile_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V2_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "actual_projection_profile_id": (
                self.actual_projection_profile_id
            ),
        }

    @classmethod
    def from_document(
        cls,
        document: Mapping[str, Any],
        registry: CounterRegistryV2,
        comparison: ComparisonProfileV2,
    ) -> "ActualProjectionProfileV2":
        expected = {
            "schema",
            "schema_version",
            "profile_key",
            "counter_registry_id",
            "comparison_profile_id",
            "terms",
            "actual_projection_profile_id",
        }
        if (
            type(document) is not dict
            or set(document) != expected
            or document["schema"] != "acfqp.actual_projection_profile.v2"
            or type(document["terms"]) is not list
        ):
            raise ConstructionAccountingV2Error(
                "actual projection profile field set mismatch"
            )
        result = cls(
            document["profile_key"],
            document["schema_version"],
            document["counter_registry_id"],
            document["comparison_profile_id"],
            tuple(
                ProjectionTermV1.from_dict(row)
                for row in document["terms"]
            ),
        )
        result.validate(registry, comparison)
        if (
            document["actual_projection_profile_id"]
            != result.actual_projection_profile_id
        ):
            raise ConstructionAccountingV2Error(
                "actual projection profile content ID mismatch"
            )
        return result


def official_actual_projection_profile_v2(
    registry: CounterRegistryV2 | None = None,
    comparison: ComparisonProfileV2 | None = None,
) -> ActualProjectionProfileV2:
    selected_registry = registry or official_counter_registry_v2()
    selected_comparison = comparison or official_comparison_profile_v2(
        selected_registry
    )
    result = ActualProjectionProfileV2(
        ACTUAL_PROJECTION_PROFILE_KEY,
        SCHEMA_VERSION,
        selected_registry.registry_id,
        selected_comparison.comparison_profile_id,
        selected_comparison.terms,
    )
    result.validate(selected_registry, selected_comparison)
    return result


@dataclass(frozen=True, slots=True)
class CounterRecordV2:
    counter_registry_id: str
    subject_id: str
    stage_instance_id: str
    stage_start_attestation_id: str
    stage_kind: StageKindV2
    path: str
    value: int
    observed: bool
    recorder_id: str
    semantics_id: str
    owner: str
    unit: str
    lane: LaneEnum
    scope: str
    reducer: ReducerEnum

    def __post_init__(self) -> None:
        parse_content_id(self.counter_registry_id)
        parse_content_id(self.subject_id)
        parse_content_id(self.stage_instance_id)
        parse_content_id(self.stage_start_attestation_id)
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        _identifier(self.path, "counter path")
        _nonnegative(self.value, self.path)
        if self.observed is not True:
            raise ConstructionAccountingV2Error(
                "missing/unobserved records cannot be native zero"
            )
        _identifier(self.recorder_id, "recorder_id")
        _identifier(self.semantics_id, "semantics_id")
        _identifier(self.owner, "owner")
        _identifier(self.unit, "unit")
        try:
            object.__setattr__(self, "lane", LaneEnum(self.lane))
            object.__setattr__(self, "reducer", ReducerEnum(self.reducer))
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingV2Error(
                "counter lane/reducer is invalid"
            ) from error
        _identifier(self.scope, "scope")

    @classmethod
    def observe(
        cls,
        registry: CounterRegistryV2,
        path: str,
        value: int,
        *,
        subject_id: str,
        stage_instance_id: str,
        stage_start_attestation_id: str,
        stage_kind: StageKindV2 | str,
        recorder_id: str,
    ) -> "CounterRecordV2":
        try:
            leaf = registry.by_path[path]
        except KeyError as error:
            raise ConstructionAccountingV2Error(
                f"unknown v2 counter path {path!r}"
            ) from error
        return cls(
            registry.registry_id,
            parse_content_id(subject_id),
            parse_content_id(stage_instance_id),
            parse_content_id(stage_start_attestation_id),
            _stage(stage_kind),
            path,
            value,
            True,
            recorder_id,
            leaf.semantics_id,
            leaf.owner,
            leaf.unit,
            leaf.lane,
            leaf.scope,
            leaf.reducer,
        )

    def verify_against(self, leaf: CounterSemanticsV1) -> None:
        if (
            self.semantics_id,
            self.owner,
            self.unit,
            self.lane,
            self.scope,
            self.reducer,
        ) != (
            leaf.semantics_id,
            leaf.owner,
            leaf.unit,
            leaf.lane,
            leaf.scope,
            leaf.reducer,
        ):
            raise ConstructionAccountingV2Error(
                f"counter metadata mismatch for {self.path!r}"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.counter_record.v2",
            "counter_registry_id": self.counter_registry_id,
            "subject_id": self.subject_id,
            "stage_instance_id": self.stage_instance_id,
            "stage_start_attestation_id": self.stage_start_attestation_id,
            "stage_kind": self.stage_kind.value,
            "path": self.path,
            "value": self.value,
            "observed": self.observed,
            "recorder_id": self.recorder_id,
            "semantics_id": self.semantics_id,
            "owner": self.owner,
            "unit": self.unit,
            "lane": self.lane.value,
            "scope": self.scope,
            "reducer": self.reducer.value,
        }

    @property
    def record_id(self) -> str:
        return content_id(
            CONSTRUCTION_COUNTER_RECORD_V2_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counter_record_id": self.record_id}

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> "CounterRecordV2":
        expected = {
            "schema",
            "counter_registry_id",
            "subject_id",
            "stage_instance_id",
            "stage_start_attestation_id",
            "stage_kind",
            "path",
            "value",
            "observed",
            "recorder_id",
            "semantics_id",
            "owner",
            "unit",
            "lane",
            "scope",
            "reducer",
            "counter_record_id",
        }
        if (
            type(document) is not dict
            or set(document) != expected
            or document["schema"] != "acfqp.counter_record.v2"
        ):
            raise ConstructionAccountingV2Error(
                "counter record field set mismatch"
            )
        result = cls(
            document["counter_registry_id"],
            document["subject_id"],
            document["stage_instance_id"],
            document["stage_start_attestation_id"],
            document["stage_kind"],
            document["path"],
            document["value"],
            document["observed"],
            document["recorder_id"],
            document["semantics_id"],
            document["owner"],
            document["unit"],
            document["lane"],
            document["scope"],
            document["reducer"],
        )
        if document["counter_record_id"] != result.record_id:
            raise ConstructionAccountingV2Error(
                "counter record content ID mismatch"
            )
        return result


def _validate_reconciliation(values: Mapping[str, int]) -> None:
    for total, success, failure in (
        ("route.attempts", "route.successes", "route.failures"),
        ("solver.attempts", "solver.successes", "solver.failures"),
    ):
        if values[total] != values[success] + values[failure]:
            raise ConstructionAccountingV2Error(
                f"reconciliation failed for {total}"
            )
    if values["process.launches"] != (
        values["process.exit_successes"]
        + values["process.exit_failures"]
    ):
        raise ConstructionAccountingV2Error(
            "process launch/exit reconciliation failed"
        )
    for path in (
        "capability.serialized_bytes",
        "epoch.serialized_bytes",
        "model.serialized_bytes",
    ):
        if path in values and values[path] > values["io.output_bytes"]:
            raise ConstructionAccountingV2Error(
                f"{path} exceeds io.output_bytes"
            )
    if values.get("branch.evaluations", 0):
        raise ConstructionAccountingV2Error(
            "generic branch.evaluations cannot enter native accounting"
        )


@dataclass(frozen=True, slots=True)
class WorkVectorV2:
    counter_registry_id: str
    stage_profile_id: str
    subject_id: str
    stage_instance_id: str
    stage_start_attestation_id: str
    stage_completion_attestation_id: str
    stage_kind: StageKindV2
    records: tuple[CounterRecordV2, ...]

    def __post_init__(self) -> None:
        for value in (
            self.counter_registry_id,
            self.stage_profile_id,
            self.subject_id,
            self.stage_instance_id,
            self.stage_start_attestation_id,
            self.stage_completion_attestation_id,
        ):
            parse_content_id(value)
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        if (
            not self.records
            or tuple(sorted(self.records, key=lambda row: row.path))
            != self.records
            or len({row.path for row in self.records}) != len(self.records)
        ):
            raise ConstructionAccountingV2Error(
                "work-vector records must be nonempty, unique, and sorted"
            )

    @property
    def values(self) -> dict[str, int]:
        return {row.path: row.value for row in self.records}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.work_vector.v2",
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "subject_id": self.subject_id,
            "stage_instance_id": self.stage_instance_id,
            "stage_start_attestation_id": self.stage_start_attestation_id,
            "stage_completion_attestation_id": (
                self.stage_completion_attestation_id
            ),
            "stage_kind": self.stage_kind.value,
            "counter_record_ids": [row.record_id for row in self.records],
        }

    @property
    def work_vector_id(self) -> str:
        return content_id(
            CONSTRUCTION_WORK_VECTOR_V2_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "records": [row.to_document() for row in self.records],
            "work_vector_id": self.work_vector_id,
        }

    @classmethod
    def from_document(
        cls,
        document: Mapping[str, Any],
        registry: CounterRegistryV2,
        stage_profile: StageProfileV2,
    ) -> "WorkVectorV2":
        expected = {
            "schema",
            "counter_registry_id",
            "stage_profile_id",
            "subject_id",
            "stage_instance_id",
            "stage_start_attestation_id",
            "stage_completion_attestation_id",
            "stage_kind",
            "counter_record_ids",
            "records",
            "work_vector_id",
        }
        if (
            type(document) is not dict
            or set(document) != expected
            or document["schema"] != "acfqp.work_vector.v2"
            or type(document["counter_record_ids"]) is not list
            or type(document["records"]) is not list
        ):
            raise ConstructionAccountingV2Error(
                "work vector field set mismatch"
            )
        rows = tuple(
            CounterRecordV2.from_document(row)
            for row in document["records"]
        )
        if document["counter_record_ids"] != [
            row.record_id for row in rows
        ]:
            raise ConstructionAccountingV2Error(
                "work vector record-ID list mismatch"
            )
        result = cls(
            document["counter_registry_id"],
            document["stage_profile_id"],
            document["subject_id"],
            document["stage_instance_id"],
            document["stage_start_attestation_id"],
            document["stage_completion_attestation_id"],
            document["stage_kind"],
            rows,
        )
        validate_work_vector_v2(result, registry, stage_profile)
        if document["work_vector_id"] != result.work_vector_id:
            raise ConstructionAccountingV2Error(
                "work vector content ID mismatch"
            )
        return result


def validate_work_vector_v2(
    vector: WorkVectorV2,
    registry: CounterRegistryV2,
    stage_profile: StageProfileV2,
) -> None:
    registry.validate_official_catalogue()
    stage_profile.validate(registry)
    if (
        vector.counter_registry_id != registry.registry_id
        or vector.stage_profile_id != stage_profile.stage_profile_id
    ):
        raise ConstructionAccountingV2Error(
            "work vector registry/stage-profile identity mismatch"
        )
    by_path = registry.by_path
    for row in vector.records:
        if (
            row.counter_registry_id != registry.registry_id
            or row.subject_id != vector.subject_id
            or row.stage_instance_id != vector.stage_instance_id
            or row.stage_start_attestation_id
            != vector.stage_start_attestation_id
            or row.stage_kind is not vector.stage_kind
            or row.path not in by_path
        ):
            raise ConstructionAccountingV2Error(
                "work vector contains a foreign counter record"
            )
        row.verify_against(by_path[row.path])
    present = {row.path for row in vector.records}
    missing = sorted(set(registry.required_paths) - present)
    if missing:
        raise ConstructionAccountingV2Error(
            f"work vector omits required native records: {missing!r}"
        )
    _validate_reconciliation(vector.values)
    allowed = set(
        stage_profile.by_stage[vector.stage_kind].allowed_nonzero_paths
    )
    forbidden = sorted(
        path
        for path, value in vector.values.items()
        if value and path not in allowed
    )
    if forbidden:
        raise ConstructionAccountingV2Error(
            f"stage-family exclusivity violation: {forbidden!r}"
        )


@dataclass(frozen=True, slots=True)
class ComparisonVectorV2:
    comparison_profile_id: str
    work_vector_id: str
    subject_id: str
    stage_instance_id: str
    stage_kind: StageKindV2
    values: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        for value in (
            self.comparison_profile_id,
            self.work_vector_id,
            self.subject_id,
            self.stage_instance_id,
        ):
            parse_content_id(value)
        object.__setattr__(self, "stage_kind", _stage(self.stage_kind))
        if (
            tuple(sorted(self.values)) != self.values
            or len(dict(self.values)) != len(self.values)
            or tuple(name for name, _value in self.values) != SHARED_AXES
        ):
            raise ConstructionAccountingV2Error(
                "comparison vector must contain the exact eight axes"
            )
        for name, value in self.values:
            _identifier(name, "comparison axis")
            _nonnegative(value, name)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.comparison_vector.v2",
            "comparison_profile_id": self.comparison_profile_id,
            "work_vector_id": self.work_vector_id,
            "subject_id": self.subject_id,
            "stage_instance_id": self.stage_instance_id,
            "stage_kind": self.stage_kind.value,
            "values": [
                {"axis": name, "value": value}
                for name, value in self.values
            ],
        }

    @property
    def comparison_vector_id(self) -> str:
        return content_id(
            CONSTRUCTION_COMPARISON_VECTOR_V2_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "comparison_vector_id": self.comparison_vector_id,
        }


@dataclass(frozen=True, slots=True)
class ActualProjectionProofV2:
    actual_projection_profile_id: str
    work_vector_id: str
    comparison_vector_id: str
    counter_record_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value in (
            self.actual_projection_profile_id,
            self.work_vector_id,
            self.comparison_vector_id,
            *self.counter_record_ids,
        ):
            parse_content_id(value)
        if len(set(self.counter_record_ids)) != len(self.counter_record_ids):
            raise ConstructionAccountingV2Error(
                "projection proof repeats a counter-record ID"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.actual_projection_proof.v2",
            "actual_projection_profile_id": (
                self.actual_projection_profile_id
            ),
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "counter_record_ids": list(self.counter_record_ids),
            "all_operational_leaves_projected_exactly_once": True,
            "nonoperational_leaves_projected": False,
            "scalar_cost_defined": False,
        }

    @property
    def actual_projection_proof_id(self) -> str:
        return content_id(
            CONSTRUCTION_ACTUAL_PROJECTION_PROOF_V2_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "actual_projection_proof_id": self.actual_projection_proof_id,
        }


def derive_actual_projection_v2(
    vector: WorkVectorV2,
    registry: CounterRegistryV2,
    stage_profile: StageProfileV2,
    comparison: ComparisonProfileV2,
    actual_profile: ActualProjectionProfileV2,
) -> tuple[ComparisonVectorV2, ActualProjectionProofV2]:
    validate_work_vector_v2(vector, registry, stage_profile)
    comparison.validate(registry)
    actual_profile.validate(registry, comparison)
    source = vector.values
    values = {row.name: 0 for row in comparison.axes}
    for term in actual_profile.terms:
        contribution = source[term.source_leaf] * term.coefficient
        if term.reducer is ReducerEnum.SUM:
            values[term.target_axis] += contribution
        else:
            values[term.target_axis] = max(
                values[term.target_axis], contribution
            )
    projected = ComparisonVectorV2(
        comparison.comparison_profile_id,
        vector.work_vector_id,
        vector.subject_id,
        vector.stage_instance_id,
        vector.stage_kind,
        tuple(sorted(values.items())),
    )
    proof = ActualProjectionProofV2(
        actual_profile.actual_projection_profile_id,
        vector.work_vector_id,
        projected.comparison_vector_id,
        tuple(row.record_id for row in vector.records),
    )
    return projected, proof


@dataclass(frozen=True, slots=True)
class RecordedStageWorkV2:
    work_vector: WorkVectorV2
    comparison_vector: ComparisonVectorV2
    actual_projection_proof: ActualProjectionProofV2


class ConstructionStageRecorderV2:
    """Explicit-zero recorder that must be opened before the owned stage."""

    def __init__(
        self,
        *,
        subject_id: str,
        stage_instance_id: str,
        stage_start_attestation_id: str,
        stage_kind: StageKindV2 | str,
        recorder_id: str,
        registry: CounterRegistryV2 | None = None,
        stage_profile: StageProfileV2 | None = None,
        comparison_profile: ComparisonProfileV2 | None = None,
        actual_projection_profile: ActualProjectionProfileV2 | None = None,
    ) -> None:
        self.registry = registry or official_counter_registry_v2()
        self.stage_profile = stage_profile or official_stage_profile_v2(
            self.registry
        )
        self.comparison_profile = (
            comparison_profile
            or official_comparison_profile_v2(self.registry)
        )
        self.actual_projection_profile = (
            actual_projection_profile
            or official_actual_projection_profile_v2(
                self.registry, self.comparison_profile
            )
        )
        self.registry.validate_official_catalogue()
        self.stage_profile.validate(self.registry)
        self.comparison_profile.validate(self.registry)
        self.actual_projection_profile.validate(
            self.registry, self.comparison_profile
        )
        self.subject_id = parse_content_id(subject_id)
        self.stage_instance_id = parse_content_id(stage_instance_id)
        self.stage_start_attestation_id = parse_content_id(
            stage_start_attestation_id
        )
        self.stage_kind = _stage(stage_kind)
        self.recorder_id = _identifier(recorder_id, "recorder_id")
        self._values = {path: 0 for path in self.registry.required_paths}
        self._sealed: RecordedStageWorkV2 | None = None

    def _leaf(self, path: str) -> CounterSemanticsV1:
        if self._sealed is not None:
            raise ConstructionAccountingV2Error(
                "construction recorder is already sealed"
            )
        try:
            leaf = self.registry.by_path[path]
        except KeyError as error:
            raise ConstructionAccountingV2Error(
                f"unknown v2 counter path {path!r}"
            ) from error
        if not leaf.required:
            raise ConstructionAccountingV2Error(
                "optional diagnostic records do not enter a stage WorkVector"
            )
        if (
            path
            not in self.stage_profile.by_stage[
                self.stage_kind
            ].allowed_nonzero_paths
        ):
            raise ConstructionAccountingV2Error(
                f"{path!r} is outside {self.stage_kind.value}"
            )
        return leaf

    def add(self, path: str, amount: int = 1) -> None:
        leaf = self._leaf(path)
        if leaf.lane is LaneEnum.DERIVED_ONLY:
            raise ConstructionAccountingV2Error(
                f"{path!r} is reconciled/derived; use set_reconciliation"
            )
        if leaf.reducer is not ReducerEnum.SUM:
            raise ConstructionAccountingV2Error(
                f"{path!r} is a peak; use observe_peak"
            )
        self._values[path] += _nonnegative(amount, path)

    def observe_peak(self, path: str, value: int) -> None:
        leaf = self._leaf(path)
        if leaf.reducer is not ReducerEnum.MAX:
            raise ConstructionAccountingV2Error(
                f"{path!r} is additive; use add"
            )
        self._values[path] = max(
            self._values[path], _nonnegative(value, path)
        )

    def set_reconciliation(
        self,
        *,
        route_successes: int = 0,
        route_failures: int = 0,
        solver_successes: int = 0,
        solver_failures: int = 0,
        process_exit_successes: int = 0,
        process_exit_failures: int = 0,
    ) -> None:
        if self._sealed is not None:
            raise ConstructionAccountingV2Error(
                "construction recorder is already sealed"
            )
        values = {
            "route.successes": _nonnegative(
                route_successes, "route_successes"
            ),
            "route.failures": _nonnegative(
                route_failures, "route_failures"
            ),
            "solver.successes": _nonnegative(
                solver_successes, "solver_successes"
            ),
            "solver.failures": _nonnegative(
                solver_failures, "solver_failures"
            ),
            "process.exit_successes": _nonnegative(
                process_exit_successes, "process_exit_successes"
            ),
            "process.exit_failures": _nonnegative(
                process_exit_failures, "process_exit_failures"
            ),
        }
        values["route.attempts"] = (
            values["route.successes"] + values["route.failures"]
        )
        values["solver.attempts"] = (
            values["solver.successes"] + values["solver.failures"]
        )
        values["process.launches"] = (
            values["process.exit_successes"]
            + values["process.exit_failures"]
        )
        allowed = set(
            self.stage_profile.by_stage[
                self.stage_kind
            ].allowed_nonzero_paths
        )
        forbidden = [
            path for path, value in values.items() if value and path not in allowed
        ]
        if forbidden:
            raise ConstructionAccountingV2Error(
                "reconciliation events are outside the owned stage"
            )
        self._values.update(values)

    def seal(
        self, *, stage_completion_attestation_id: str
    ) -> RecordedStageWorkV2:
        completion = parse_content_id(stage_completion_attestation_id)
        if self._sealed is not None:
            if (
                self._sealed.work_vector.stage_completion_attestation_id
                != completion
            ):
                raise ConstructionAccountingV2Error(
                    "sealed stage cannot be rebound to another completion"
                )
            return self._sealed
        rows = tuple(
            CounterRecordV2.observe(
                self.registry,
                path,
                self._values[path],
                subject_id=self.subject_id,
                stage_instance_id=self.stage_instance_id,
                stage_start_attestation_id=(
                    self.stage_start_attestation_id
                ),
                stage_kind=self.stage_kind,
                recorder_id=self.recorder_id,
            )
            for path in sorted(self.registry.required_paths)
        )
        vector = WorkVectorV2(
            self.registry.registry_id,
            self.stage_profile.stage_profile_id,
            self.subject_id,
            self.stage_instance_id,
            self.stage_start_attestation_id,
            completion,
            self.stage_kind,
            rows,
        )
        projected, proof = derive_actual_projection_v2(
            vector,
            self.registry,
            self.stage_profile,
            self.comparison_profile,
            self.actual_projection_profile,
        )
        self._sealed = RecordedStageWorkV2(vector, projected, proof)
        return self._sealed


def freeze_construction_accounting_schema_v2() -> dict[str, Any]:
    """Return the four exact schema documents without issuing work evidence."""

    registry = official_counter_registry_v2()
    stage = official_stage_profile_v2(registry)
    comparison = official_comparison_profile_v2(registry)
    actual = official_actual_projection_profile_v2(registry, comparison)
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
    "EXPECTED_V2_LEAF_COUNT",
    "EXPECTED_V2_OPERATIONAL_LEAF_COUNT",
    "EXPECTED_V2_REQUIRED_LEAF_COUNT",
    "SCHEMA_VERSION",
    "STAGE_PROFILE_KEY",
    "ActualProjectionProfileV2",
    "ActualProjectionProofV2",
    "ComparisonProfileV2",
    "ComparisonVectorV2",
    "ConstructionAccountingV2Error",
    "ConstructionStageRecorderV2",
    "CounterRecordV2",
    "CounterRegistryV2",
    "RecordedStageWorkV2",
    "StageKindV2",
    "StageProfileV2",
    "StageRuleV2",
    "WorkVectorV2",
    "derive_actual_projection_v2",
    "freeze_construction_accounting_schema_v2",
    "official_actual_projection_profile_v2",
    "official_comparison_profile_v2",
    "official_counter_registry_v2",
    "official_stage_profile_v2",
    "validate_work_vector_v2",
]
