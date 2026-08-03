"""Independent semantic replay for the construction-accounting V6 chain.

The portable counter-record, work-vector and comparison-vector byte shapes are
the shapes already frozen by :mod:`acfqp.accounting_v1`.  Their *semantics* in
this module are not V1 semantics: every record and every projection term is
checked against the exact V6 registry, stage, comparison and actual-projection
profiles.  In particular, no V1 registry materializer, vector validator,
projection helper, or Phase-3E V1 semantic verifier is called.

The verifier starts from a separately supplied tuple of native CounterRecords.
It rebuilds the canonical WorkVector and then recomputes the ComparisonVector
from the official V6 actual-projection terms.  Claimed vectors are comparison
targets only; their records or values are never used as the source of truth.

This is a construction accounting verifier.  It does not authenticate recorder
process provenance, issue a terminal/certificate, or unlock an official Gate.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass
from functools import lru_cache
from types import MappingProxyType
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.accounting_v1 import (
    SHARED_AXES,
    AccountingV1Error,
    ComparisonVectorV1,
    CounterRecordV1,
    LaneEnum,
    ReducerEnum,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "6.0.0"
PROFILE_KEY = "construction_accounting_semantic_verification_v6"
EXPECTED_REQUIRED_RECORD_COUNT = registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
EXPECTED_OPERATIONAL_RECORD_COUNT = (
    registry_v6.EXPECTED_V6_OPERATIONAL_LEAF_COUNT
)
EXPECTED_DIRECT_FALLBACK_ALLOWED_REQUIRED_COUNT = 24
EXPECTED_DIRECT_FALLBACK_FORBIDDEN_REQUIRED_ZERO_COUNT = 178
EXPECTED_DIRECT_FALLBACK_ALLOWED_OPERATIONAL_COUNT = 16
EXPECTED_DIRECT_FALLBACK_FORBIDDEN_OPERATIONAL_ZERO_COUNT = 166


ROUTE_STAGE_KIND_V6: Mapping[
    RouteKindEnum, registry_v6.ConstructionStageKindV6
] = MappingProxyType(
    {
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE: (
            registry_v6.ConstructionStageKindV6.PREOPEN_COMMON_PREFIX
        ),
        RouteKindEnum.ABSTRACT_FAILED_PREFIX: (
            registry_v6.ConstructionStageKindV6.FAILED_ABSTRACT_PREFIX
        ),
        RouteKindEnum.LOCAL_ATTEMPT: (
            registry_v6.ConstructionStageKindV6.LOCAL_ATTEMPT
        ),
        RouteKindEnum.DIRECT_FALLBACK: (
            registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
        ),
        RouteKindEnum.REBUILD: registry_v6.ConstructionStageKindV6.REBUILD,
    }
)


class ConstructionAccountingSemanticVerificationV6Error(ValueError):
    """The V6 native-record, WorkVector, or projection chain is invalid."""


def _fail(message: str) -> NoReturn:
    raise ConstructionAccountingSemanticVerificationV6Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionAccountingSemanticVerificationV6Error(
            f"{label} must be one exact content ID"
        ) from error


def _route_kind(value: RouteKindEnum | str) -> RouteKindEnum:
    try:
        return RouteKindEnum(value)
    except (TypeError, ValueError) as error:
        raise ConstructionAccountingSemanticVerificationV6Error(
            "route kind is not registered"
        ) from error


def _stage_kind(
    value: registry_v6.ConstructionStageKindV6 | str,
) -> registry_v6.ConstructionStageKindV6:
    try:
        return registry_v6.ConstructionStageKindV6(value)
    except (TypeError, ValueError) as error:
        raise ConstructionAccountingSemanticVerificationV6Error(
            "construction stage kind is not registered"
        ) from error


@lru_cache(maxsize=1)
def _official_profiles() -> tuple[
    registry_v6.CounterRegistryV6,
    registry_v6.StageProfileV6,
    registry_v6.ComparisonProfileV6,
    registry_v6.ActualProjectionProfileV6,
]:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(
        registry, comparison
    )
    registry.validate_official_catalogue()
    stage.validate(registry)
    comparison.validate(registry)
    actual.validate(registry, comparison)
    return registry, stage, comparison, actual


def _bind_profile_ids(
    *,
    counter_registry_id: str,
    stage_profile_id: str,
    comparison_profile_id: str,
    actual_projection_profile_id: str,
    registry: registry_v6.CounterRegistryV6,
    stage: registry_v6.StageProfileV6,
    comparison: registry_v6.ComparisonProfileV6,
    actual: registry_v6.ActualProjectionProfileV6,
) -> None:
    supplied = (
        _cid(counter_registry_id, "counter registry"),
        _cid(stage_profile_id, "stage profile"),
        _cid(comparison_profile_id, "comparison profile"),
        _cid(actual_projection_profile_id, "actual projection profile"),
    )
    expected = (
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        actual.actual_projection_profile_id,
    )
    if supplied != expected:
        _fail("V6 registry/stage/comparison/actual profile identity mismatch")


def _parse_record(value: CounterRecordV1 | Mapping[str, Any]) -> CounterRecordV1:
    document = value.to_dict() if type(value) is CounterRecordV1 else value
    if type(document) is not dict:
        _fail("native CounterRecord must be one exact document")
    try:
        # This is strict byte-shape/content-ID parsing only.  V6 metadata and
        # completeness are replayed below against CounterRegistryV6.
        return CounterRecordV1.from_dict(document)
    except (AccountingV1Error, TypeError, ValueError) as error:
        raise ConstructionAccountingSemanticVerificationV6Error(
            f"native CounterRecord failed strict content replay: {error}"
        ) from error


def _canonical_records(
    values: Sequence[CounterRecordV1 | Mapping[str, Any]],
    *,
    registry: registry_v6.CounterRegistryV6,
) -> tuple[CounterRecordV1, ...]:
    if type(values) is not tuple:
        _fail("native CounterRecords must be one retained exact tuple")
    records = tuple(_parse_record(value) for value in values)
    paths = tuple(record.path for record in records)
    path_set = set(paths)
    required = set(registry.required_paths)
    duplicate_paths = sorted(
        path for path in path_set if paths.count(path) != 1
    )
    unknown = sorted(path_set - required)
    missing = sorted(required - path_set)
    if duplicate_paths:
        _fail(f"native CounterRecords repeat paths: {duplicate_paths!r}")
    if unknown:
        _fail(f"native CounterRecords contain unknown/optional paths: {unknown!r}")
    if missing:
        _fail(f"native CounterRecords omit explicit required paths: {missing!r}")
    if (
        len(records) != EXPECTED_REQUIRED_RECORD_COUNT
        or len({record.record_id for record in records}) != len(records)
    ):
        _fail("native CounterRecord cardinality or identity uniqueness changed")

    by_path = registry.by_path
    for record in records:
        leaf = by_path[record.path]
        actual_metadata = (
            record.semantics_id,
            record.owner,
            record.unit,
            record.lane,
            record.scope,
            record.reducer,
        )
        expected_metadata = (
            leaf.semantics_id,
            leaf.owner,
            leaf.unit,
            leaf.lane,
            leaf.scope,
            leaf.reducer,
        )
        if (
            record.counter_registry_id != registry.registry_id
            or record.observed is not True
            or actual_metadata != expected_metadata
        ):
            _fail(
                f"native CounterRecord metadata/observation differs for {record.path!r}"
            )
    return tuple(sorted(records, key=lambda record: record.path))


_RECONCILIATION_GROUPS = (
    ("route.attempts", "route.successes", "route.failures"),
    ("solver.attempts", "solver.successes", "solver.failures"),
    ("process.launches", "process.exit_successes", "process.exit_failures"),
)


def _validate_reconciliation_and_stage(
    vector: WorkVectorV1,
    *,
    registry: registry_v6.CounterRegistryV6,
    stage: registry_v6.StageProfileV6,
    stage_kind: registry_v6.ConstructionStageKindV6,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    values = vector.values
    expected_stage_kind = ROUTE_STAGE_KIND_V6.get(vector.route_kind)
    if expected_stage_kind is None or stage_kind is not expected_stage_kind:
        _fail(
            "route kind and construction stage kind are not an accepted exact pair"
        )
    rule = stage.by_stage[stage_kind]
    allowed = set(rule.allowed_nonzero_paths)
    positive = {path for path, value in values.items() if value > 0}
    forbidden_positive = tuple(sorted(positive - allowed))
    if forbidden_positive:
        _fail(
            "V6 stage-family exclusivity violation: "
            f"{forbidden_positive!r}"
        )

    required = set(registry.required_paths)
    operational = {row.path for row in registry.operational_leaves}
    forbidden_required = tuple(sorted(required - allowed))
    forbidden_operational = tuple(sorted(operational - allowed))
    if any(values[path] != 0 for path in forbidden_required):
        _fail("V6 stage-forbidden required path is not an explicit zero")
    if stage_kind is registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK:
        allowed_required = required & allowed
        allowed_operational = operational & allowed
        if (
            len(allowed_required)
            != EXPECTED_DIRECT_FALLBACK_ALLOWED_REQUIRED_COUNT
            or len(forbidden_required)
            != EXPECTED_DIRECT_FALLBACK_FORBIDDEN_REQUIRED_ZERO_COUNT
            or len(allowed_operational)
            != EXPECTED_DIRECT_FALLBACK_ALLOWED_OPERATIONAL_COUNT
            or len(forbidden_operational)
            != EXPECTED_DIRECT_FALLBACK_FORBIDDEN_OPERATIONAL_ZERO_COUNT
        ):
            _fail("DIRECT_FALLBACK allowed/forbidden V6 cardinalities changed")

    for total, successes, failures in _RECONCILIATION_GROUPS:
        if values[total] != values[successes] + values[failures]:
            _fail(f"V6 reconciliation failed for {total}")
    for path in (
        "capability.serialized_bytes",
        "epoch.serialized_bytes",
        "model.serialized_bytes",
    ):
        if path in values and values[path] > values["io.output_bytes"]:
            _fail(f"{path} exceeds io.output_bytes")
    return forbidden_required, forbidden_operational


def _parse_claimed_work_vector(
    value: WorkVectorV1 | Mapping[str, Any],
) -> WorkVectorV1:
    document = value.to_dict() if type(value) is WorkVectorV1 else value
    expected = {
        "schema",
        "counter_registry_id",
        "subject_id",
        "route_kind",
        "counter_record_ids",
        "records",
        "work_vector_id",
    }
    if (
        type(document) is not dict
        or set(document) != expected
        or document.get("schema") != "acfqp.work_vector.v1"
        or type(document.get("counter_record_ids")) is not list
        or type(document.get("records")) is not list
    ):
        _fail("claimed WorkVector has the wrong portable byte shape")
    try:
        records = tuple(CounterRecordV1.from_dict(row) for row in document["records"])
        parsed = WorkVectorV1(
            document["counter_registry_id"],
            document["subject_id"],
            document["route_kind"],
            records,
        )
    except (AccountingV1Error, TypeError, ValueError) as error:
        raise ConstructionAccountingSemanticVerificationV6Error(
            f"claimed WorkVector failed strict content replay: {error}"
        ) from error
    if (
        document["counter_record_ids"] != [row.record_id for row in records]
        or document["work_vector_id"] != parsed.work_vector_id
    ):
        _fail("claimed WorkVector record list or content identity changed")
    return parsed


def _projection_values(
    vector: WorkVectorV1,
    *,
    registry: registry_v6.CounterRegistryV6,
    comparison: registry_v6.ComparisonProfileV6,
    actual: registry_v6.ActualProjectionProfileV6,
) -> tuple[tuple[str, int], ...]:
    comparison.validate(registry)
    actual.validate(registry, comparison)
    terms = actual.terms
    operational_paths = tuple(row.path for row in registry.operational_leaves)
    if (
        len(terms) != EXPECTED_OPERATIONAL_RECORD_COUNT
        or tuple(term.source_leaf for term in terms) != operational_paths
        or len({term.source_leaf for term in terms}) != len(terms)
        or any(
            term.source_lane is not LaneEnum.OPERATIONAL
            or registry.by_path[term.source_leaf].lane is not LaneEnum.OPERATIONAL
            or term.source_semantics_id
            != registry.by_path[term.source_leaf].semantics_id
            or term.target_axis
            != registry.by_path[term.source_leaf].comparison_axis
            or term.reducer is not registry.by_path[term.source_leaf].reducer
            or term.coefficient != 1
            for term in terms
        )
    ):
        _fail("V6 actual projection is not the exact 182-leaf mapping")
    axis_reducers = {axis.name: axis.reducer for axis in comparison.axes}
    if tuple(axis_reducers) != SHARED_AXES:
        _fail("V6 comparison profile does not contain the exact shared axes")
    projected = {axis: 0 for axis in SHARED_AXES}
    source = vector.values
    for term in terms:
        if axis_reducers[term.target_axis] is not term.reducer:
            _fail("V6 projection term/axis reducer mismatch")
        contribution = source[term.source_leaf] * term.coefficient
        if term.reducer is ReducerEnum.SUM:
            projected[term.target_axis] += contribution
        else:
            projected[term.target_axis] = max(
                projected[term.target_axis], contribution
            )
    return tuple((axis, projected[axis]) for axis in SHARED_AXES)


def _parse_claimed_comparison_vector(
    value: ComparisonVectorV1 | Mapping[str, Any],
) -> ComparisonVectorV1:
    document = value.to_dict() if type(value) is ComparisonVectorV1 else value
    if type(document) is not dict:
        _fail("claimed ComparisonVector must be one exact document")
    try:
        return ComparisonVectorV1.from_dict(document)
    except (AccountingV1Error, TypeError, ValueError) as error:
        raise ConstructionAccountingSemanticVerificationV6Error(
            f"claimed ComparisonVector failed strict content replay: {error}"
        ) from error


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class VerifiedConstructionAccountingSemanticsV6:
    """Retained in-memory result of one exact V6 accounting replay."""

    _issuer: InitVar[object]
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    stage_kind: registry_v6.ConstructionStageKindV6
    work_vector: WorkVectorV1
    comparison_vector: ComparisonVectorV1
    native_zero_paths: tuple[str, ...]
    native_zero_counter_record_ids: tuple[str, ...]
    projected_counter_record_ids: tuple[str, ...]
    forbidden_required_zero_paths: tuple[str, ...]
    forbidden_required_zero_counter_record_ids: tuple[str, ...]
    forbidden_operational_zero_paths: tuple[str, ...]
    forbidden_operational_zero_counter_record_ids: tuple[str, ...]

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _RESULT_ISSUER
            or type(self.work_vector) is not WorkVectorV1
            or type(self.comparison_vector) is not ComparisonVectorV1
        ):
            _fail("V6 semantic-verification result is verifier-owned")
        object.__setattr__(self, "stage_kind", _stage_kind(self.stage_kind))
        for value, label in (
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.comparison_profile_id, "comparison profile"),
            (self.actual_projection_profile_id, "actual projection profile"),
            *((value, "native-zero record") for value in self.native_zero_counter_record_ids),
            *((value, "projected record") for value in self.projected_counter_record_ids),
            *((value, "forbidden required-zero record") for value in self.forbidden_required_zero_counter_record_ids),
            *((value, "forbidden operational-zero record") for value in self.forbidden_operational_zero_counter_record_ids),
        ):
            _cid(value, label)
        if (
            tuple(sorted(self.native_zero_paths)) != self.native_zero_paths
            or len(set(self.native_zero_paths)) != len(self.native_zero_paths)
            or len(self.native_zero_paths)
            != len(self.native_zero_counter_record_ids)
            or len(self.projected_counter_record_ids)
            != EXPECTED_OPERATIONAL_RECORD_COUNT
            or len(set(self.projected_counter_record_ids))
            != len(self.projected_counter_record_ids)
            or tuple(sorted(self.forbidden_required_zero_paths))
            != self.forbidden_required_zero_paths
            or len(self.forbidden_required_zero_paths)
            != len(self.forbidden_required_zero_counter_record_ids)
            or tuple(sorted(self.forbidden_operational_zero_paths))
            != self.forbidden_operational_zero_paths
            or len(self.forbidden_operational_zero_paths)
            != len(self.forbidden_operational_zero_counter_record_ids)
        ):
            _fail("V6 zero/projection evidence cardinality changed")
        if self.stage_kind is registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK:
            if (
                len(self.forbidden_required_zero_paths)
                != EXPECTED_DIRECT_FALLBACK_FORBIDDEN_REQUIRED_ZERO_COUNT
                or len(self.forbidden_operational_zero_paths)
                != EXPECTED_DIRECT_FALLBACK_FORBIDDEN_OPERATIONAL_ZERO_COUNT
            ):
                _fail("DIRECT_FALLBACK forbidden-zero evidence changed")

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_accounting_semantic_verification.v6",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "stage_kind": self.stage_kind.value,
            "work_vector": self.work_vector.to_dict(),
            "comparison_vector": self.comparison_vector.to_dict(),
            "native_zero_paths": list(self.native_zero_paths),
            "native_zero_counter_record_ids": list(
                self.native_zero_counter_record_ids
            ),
            "projected_counter_record_ids": list(
                self.projected_counter_record_ids
            ),
            "forbidden_required_zero_paths": list(
                self.forbidden_required_zero_paths
            ),
            "forbidden_required_zero_counter_record_ids": list(
                self.forbidden_required_zero_counter_record_ids
            ),
            "forbidden_operational_zero_paths": list(
                self.forbidden_operational_zero_paths
            ),
            "forbidden_operational_zero_counter_record_ids": list(
                self.forbidden_operational_zero_counter_record_ids
            ),
            "forbidden_required_zero_count": len(
                self.forbidden_required_zero_paths
            ),
            "forbidden_operational_zero_count": len(
                self.forbidden_operational_zero_paths
            ),
            "counter_record_count": len(self.work_vector.records),
            "operational_projection_term_count": len(
                self.projected_counter_record_ids
            ),
            "work_vector_recomputed_from_native_records": True,
            "comparison_recomputed_from_v6_actual_projection": True,
            "caller_supplied_comparison_used_as_source": False,
            "v1_registry_or_semantic_verifier_used": False,
            "per_record_stage_provenance_claimed": False,
            "recorder_process_provenance_authenticated": False,
            "official_execution_allowed": False,
            "counter_completeness_gate_passed": False,
            "workload_economics_gate_passed": False,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def verify_construction_accounting_semantics_v6(
    *,
    native_counter_records: tuple[CounterRecordV1 | Mapping[str, Any], ...],
    expected_subject_id: str,
    expected_route_kind: RouteKindEnum | str,
    expected_stage_kind: registry_v6.ConstructionStageKindV6 | str,
    counter_registry_id: str,
    stage_profile_id: str,
    comparison_profile_id: str,
    actual_projection_profile_id: str,
    claimed_work_vector: WorkVectorV1 | Mapping[str, Any],
    claimed_comparison_vector: ComparisonVectorV1 | Mapping[str, Any],
) -> VerifiedConstructionAccountingSemanticsV6:
    """Replay the exact V6 record -> WorkVector -> ComparisonVector chain."""

    subject_id = _cid(expected_subject_id, "expected subject")
    route_kind = _route_kind(expected_route_kind)
    stage_kind = _stage_kind(expected_stage_kind)
    registry, stage, comparison, actual = _official_profiles()
    _bind_profile_ids(
        counter_registry_id=counter_registry_id,
        stage_profile_id=stage_profile_id,
        comparison_profile_id=comparison_profile_id,
        actual_projection_profile_id=actual_projection_profile_id,
        registry=registry,
        stage=stage,
        comparison=comparison,
        actual=actual,
    )
    records = _canonical_records(native_counter_records, registry=registry)
    vector = WorkVectorV1(
        registry.registry_id,
        subject_id,
        route_kind,
        records,
    )
    forbidden_required, forbidden_operational = (
        _validate_reconciliation_and_stage(
            vector,
            registry=registry,
            stage=stage,
            stage_kind=stage_kind,
        )
    )

    parsed_work = _parse_claimed_work_vector(claimed_work_vector)
    if parsed_work.to_dict() != vector.to_dict():
        _fail("claimed WorkVector differs from native-record recomputation")

    projected = ComparisonVectorV1(
        comparison.comparison_profile_id,
        vector.work_vector_id,
        vector.subject_id,
        vector.route_kind,
        _projection_values(
            vector,
            registry=registry,
            comparison=comparison,
            actual=actual,
        ),
    )
    parsed_comparison = _parse_claimed_comparison_vector(
        claimed_comparison_vector
    )
    if parsed_comparison.to_dict() != projected.to_dict():
        _fail(
            "claimed ComparisonVector differs from V6 actual-projection recomputation"
        )

    by_path = {record.path: record for record in records}
    zero_paths = tuple(
        record.path for record in records if record.value == 0
    )
    return VerifiedConstructionAccountingSemanticsV6(
        _RESULT_ISSUER,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        actual.actual_projection_profile_id,
        stage_kind,
        vector,
        projected,
        zero_paths,
        tuple(by_path[path].record_id for path in zero_paths),
        tuple(
            by_path[term.source_leaf].record_id for term in actual.terms
        ),
        forbidden_required,
        tuple(by_path[path].record_id for path in forbidden_required),
        forbidden_operational,
        tuple(by_path[path].record_id for path in forbidden_operational),
    )


__all__ = (
    "ConstructionAccountingSemanticVerificationV6Error",
    "EXPECTED_OPERATIONAL_RECORD_COUNT",
    "EXPECTED_REQUIRED_RECORD_COUNT",
    "EXPECTED_DIRECT_FALLBACK_ALLOWED_OPERATIONAL_COUNT",
    "EXPECTED_DIRECT_FALLBACK_ALLOWED_REQUIRED_COUNT",
    "EXPECTED_DIRECT_FALLBACK_FORBIDDEN_OPERATIONAL_ZERO_COUNT",
    "EXPECTED_DIRECT_FALLBACK_FORBIDDEN_REQUIRED_ZERO_COUNT",
    "PROFILE_KEY",
    "ROUTE_STAGE_KIND_V6",
    "SCHEMA_VERSION",
    "VerifiedConstructionAccountingSemanticsV6",
    "verify_construction_accounting_semantics_v6",
)
