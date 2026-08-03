"""Atomic V6 materialization of one fully replayed K7 semantic closure.

The module consumes only the portable 202-path semantic closure plus the full
roots required by that closure's independent verifier.  It emits the existing
``accounting_v1`` record/vector types, but deliberately does *not* call the V1
registry's ``materialize`` or ``validate_vector`` methods: their catalogue is
not the V6 catalogue.  Every registry, reconciliation and projection check is
replayed here against the exact V6 profiles.

This is an accounting artifact, not an official execution, terminal,
certificate, economics or scalar-cost authority.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import (
    SHARED_AXES,
    ComparisonVectorV1,
    CounterRecordV1,
    LaneEnum,
    ReducerEnum,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_semantic_evidence_closure_v1 as closure_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_FORMAL_ACCOUNTING_MATERIALIZATION_BUNDLE_V1_DOMAIN,
    CONSTRUCTION_K7_FORMAL_ACTUAL_PROJECTION_PROOF_V6_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.29"
PROFILE_KEY = "construction_k7_formal_accounting_materializer_v1"
EXPECTED_COUNTER_RECORD_COUNT = registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
EXPECTED_PROJECTION_TERM_COUNT = registry_v6.EXPECTED_V6_OPERATIONAL_LEAF_COUNT
EXPECTED_PROFILE_NATIVE_ZERO_COUNT = 114

ACTUAL_PROJECTION_PROOF_V6_DOMAIN = (
    CONSTRUCTION_K7_FORMAL_ACTUAL_PROJECTION_PROOF_V6_DOMAIN
)
MATERIALIZATION_BUNDLE_V1_DOMAIN = (
    CONSTRUCTION_K7_FORMAL_ACCOUNTING_MATERIALIZATION_BUNDLE_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset(
    {ACTUAL_PROJECTION_PROOF_V6_DOMAIN, MATERIALIZATION_BUNDLE_V1_DOMAIN}
)
if len(LOCAL_DOMAINS) != 2 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("formal materializer domains are not central and unique")

_PROOF_ISSUER = object()
_BUNDLE_ISSUER = object()


class ConstructionK7FormalAccountingMaterializerV1Error(ValueError):
    """The semantic closure or one formal accounting artifact failed replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FormalAccountingMaterializerV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7FormalAccountingMaterializerV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _fields(document: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(document) is not dict or set(document) != expected:
        _fail(f"{label} field set changed")
    return document


def _canonical_document(raw: Any, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} bytes are missing")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7FormalAccountingMaterializerV1Error(
            f"{label} bytes are noncanonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} bytes are noncanonical")
    return document


@dataclass(frozen=True, slots=True)
class K7FormalActualProjectionProofV6:
    _issuer: InitVar[object]
    semantic_evidence_closure_id: str
    semantic_evidence_closure_context_id: str
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    work_vector_id: str
    comparison_vector_id: str
    counter_record_ids: tuple[str, ...]
    projected_source_paths: tuple[str, ...]
    projected_counter_record_ids: tuple[str, ...]
    profile_native_zero_counter_record_ids: tuple[str, ...]
    projection_term_count: int
    _proof_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROOF_ISSUER:
            _fail("V6 actual-projection proof is caller-minted")
        for value, label in (
            (self.semantic_evidence_closure_id, "semantic closure"),
            (self.semantic_evidence_closure_context_id, "semantic closure context"),
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.comparison_profile_id, "comparison profile"),
            (self.actual_projection_profile_id, "actual projection profile"),
            (self.work_vector_id, "work vector"),
            (self.comparison_vector_id, "comparison vector"),
            *((value, "counter record") for value in self.counter_record_ids),
            *((value, "projected counter record") for value in self.projected_counter_record_ids),
            *((value, "native-zero counter record") for value in self.profile_native_zero_counter_record_ids),
        ):
            _cid(value, label)
        if (
            type(self.counter_record_ids) is not tuple
            or len(self.counter_record_ids) != EXPECTED_COUNTER_RECORD_COUNT
            or len(set(self.counter_record_ids)) != len(self.counter_record_ids)
            or type(self.projected_source_paths) is not tuple
            or len(self.projected_source_paths) != EXPECTED_PROJECTION_TERM_COUNT
            or len(set(self.projected_source_paths)) != len(self.projected_source_paths)
            or type(self.projected_counter_record_ids) is not tuple
            or len(self.projected_counter_record_ids) != EXPECTED_PROJECTION_TERM_COUNT
            or len(set(self.projected_counter_record_ids))
            != len(self.projected_counter_record_ids)
            or type(self.profile_native_zero_counter_record_ids) is not tuple
            or len(self.profile_native_zero_counter_record_ids)
            != EXPECTED_PROFILE_NATIVE_ZERO_COUNT
            or len(set(self.profile_native_zero_counter_record_ids))
            != len(self.profile_native_zero_counter_record_ids)
            or type(self.projection_term_count) is not int
            or self.projection_term_count != EXPECTED_PROJECTION_TERM_COUNT
            or not set(self.projected_counter_record_ids)
            <= set(self.counter_record_ids)
            or not set(self.profile_native_zero_counter_record_ids)
            <= set(self.counter_record_ids)
        ):
            _fail("V6 actual-projection proof cardinality or identity set changed")
        object.__setattr__(
            self,
            "_proof_id",
            content_id(ACTUAL_PROJECTION_PROOF_V6_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_formal_actual_projection_proof.v6",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "semantic_evidence_closure_id": self.semantic_evidence_closure_id,
            "semantic_evidence_closure_context_id": (
                self.semantic_evidence_closure_context_id
            ),
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "counter_record_ids": list(self.counter_record_ids),
            "projected_source_paths": list(self.projected_source_paths),
            "projected_counter_record_ids": list(
                self.projected_counter_record_ids
            ),
            "profile_native_zero_counter_record_ids": list(
                self.profile_native_zero_counter_record_ids
            ),
            "projection_term_count": self.projection_term_count,
            "all_182_operational_leaves_projected_exactly_once": True,
            "nonoperational_leaves_projected": False,
            "profile_native_zero_recorders_explicit": True,
            "eight_axis_sum_max_replayed": True,
            "caller_supplied_actual_comparison_accepted": False,
            "scalar_cost_defined": False,
            "official_execution_allowed": False,
        }

    @property
    def proof_id(self) -> str:
        if content_id(ACTUAL_PROJECTION_PROOF_V6_DOMAIN, self._payload()) != self._proof_id:
            _fail("V6 actual-projection proof changed after issuance")
        return self._proof_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "formal_actual_projection_proof_id": self.proof_id}

    @classmethod
    def _from_document(cls, document: Any) -> "K7FormalActualProjectionProofV6":
        fields = {
            "schema", "schema_version", "proposed_contract_version", "profile_key",
            "semantic_evidence_closure_id", "semantic_evidence_closure_context_id",
            "counter_registry_id", "stage_profile_id", "comparison_profile_id",
            "actual_projection_profile_id", "work_vector_id", "comparison_vector_id",
            "counter_record_ids", "projected_source_paths",
            "projected_counter_record_ids", "profile_native_zero_counter_record_ids",
            "projection_term_count", "all_182_operational_leaves_projected_exactly_once",
            "nonoperational_leaves_projected", "profile_native_zero_recorders_explicit",
            "eight_axis_sum_max_replayed", "caller_supplied_actual_comparison_accepted",
            "scalar_cost_defined", "official_execution_allowed",
            "formal_actual_projection_proof_id",
        }
        row = _fields(document, fields, "V6 actual-projection proof")
        if (
            row["schema"]
            != "acfqp.construction_k7_formal_actual_projection_proof.v6"
            or row["schema_version"] != SCHEMA_VERSION
            or row["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
            or row["profile_key"] != PROFILE_KEY
            or row["all_182_operational_leaves_projected_exactly_once"] is not True
            or row["nonoperational_leaves_projected"] is not False
            or row["profile_native_zero_recorders_explicit"] is not True
            or row["eight_axis_sum_max_replayed"] is not True
            or row["caller_supplied_actual_comparison_accepted"] is not False
            or row["scalar_cost_defined"] is not False
            or row["official_execution_allowed"] is not False
            or any(
                type(row[name]) is not list
                for name in (
                    "counter_record_ids",
                    "projected_source_paths",
                    "projected_counter_record_ids",
                    "profile_native_zero_counter_record_ids",
                )
            )
        ):
            _fail("V6 actual-projection proof locks or list fields changed")
        proof = cls(
            _PROOF_ISSUER,
            row["semantic_evidence_closure_id"],
            row["semantic_evidence_closure_context_id"],
            row["counter_registry_id"],
            row["stage_profile_id"],
            row["comparison_profile_id"],
            row["actual_projection_profile_id"],
            row["work_vector_id"],
            row["comparison_vector_id"],
            tuple(row["counter_record_ids"]),
            tuple(row["projected_source_paths"]),
            tuple(row["projected_counter_record_ids"]),
            tuple(row["profile_native_zero_counter_record_ids"]),
            row["projection_term_count"],
        )
        if row["formal_actual_projection_proof_id"] != proof.proof_id:
            _fail("V6 actual-projection proof content identity changed")
        return proof


@dataclass(frozen=True, slots=True)
class K7FormalAccountingMaterializationBundleV1:
    _issuer: InitVar[object]
    semantic_evidence_closure_id: str
    semantic_evidence_closure_context_id: str
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    work_vector: WorkVectorV1
    comparison_vector: ComparisonVectorV1
    actual_projection_proof: K7FormalActualProjectionProofV6
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BUNDLE_ISSUER
            or type(self.work_vector) is not WorkVectorV1
            or type(self.comparison_vector) is not ComparisonVectorV1
            or type(self.actual_projection_proof)
            is not K7FormalActualProjectionProofV6
        ):
            _fail("formal accounting bundle is caller-minted")
        for value, label in (
            (self.semantic_evidence_closure_id, "semantic closure"),
            (self.semantic_evidence_closure_context_id, "semantic closure context"),
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.comparison_profile_id, "comparison profile"),
            (self.actual_projection_profile_id, "actual projection profile"),
        ):
            _cid(value, label)
        if (
            len(self.work_vector.records) != EXPECTED_COUNTER_RECORD_COUNT
            or self.work_vector.route_kind is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
            or self.comparison_vector.work_vector_id
            != self.work_vector.work_vector_id
            or self.actual_projection_proof.work_vector_id
            != self.work_vector.work_vector_id
            or self.actual_projection_proof.comparison_vector_id
            != self.comparison_vector.comparison_vector_id
        ):
            _fail("formal accounting bundle contains crossed vector identities")
        object.__setattr__(
            self,
            "_bundle_id",
            content_id(MATERIALIZATION_BUNDLE_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_formal_accounting_materialization_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "semantic_evidence_closure_id": self.semantic_evidence_closure_id,
            "semantic_evidence_closure_context_id": (
                self.semantic_evidence_closure_context_id
            ),
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "route_kind": RouteKindEnum.ABSTRACT_FAILED_PREFIX.value,
            "counter_record_count": len(self.work_vector.records),
            "counter_record_ids": [row.record_id for row in self.work_vector.records],
            "work_vector": self.work_vector.to_dict(),
            "comparison_vector": self.comparison_vector.to_dict(),
            "actual_projection_proof": self.actual_projection_proof.to_document(),
            "semantic_closure_replayed_from_full_roots": True,
            "v1_registry_validator_used": False,
            "formal_accounting_materialized": True,
            "terminal_artifact_issued": False,
            "certificate_issued": False,
            "official_execution_allowed": False,
            "counter_completeness_gate_passed": False,
            "workload_economics_gate_passed": False,
            "scalar_cost_defined": False,
        }

    @property
    def bundle_id(self) -> str:
        if content_id(MATERIALIZATION_BUNDLE_V1_DOMAIN, self._payload()) != self._bundle_id:
            _fail("formal accounting bundle changed after issuance")
        return self._bundle_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "formal_accounting_materialization_bundle_id": self.bundle_id}


def _official_profiles() -> tuple[Any, Any, Any, Any]:
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


def _replay_semantic_closure(
    *, semantic_closure_raw: Any, closure_replay_inputs: Mapping[str, Any]
) -> closure_v1.K7SemanticEvidenceClosureV1:
    if type(closure_replay_inputs) is not dict:
        _fail("semantic closure replay inputs must be one exact mapping")
    try:
        result = closure_v1.verify_k7_semantic_evidence_closure_bytes_v1(
            raw=semantic_closure_raw,
            **closure_replay_inputs,
        )
    except Exception as error:
        raise ConstructionK7FormalAccountingMaterializerV1Error(
            "202-path semantic closure failed independent full-root replay"
        ) from error
    if (
        type(result) is not closure_v1.K7SemanticEvidenceClosureV1
        or len(result.resolutions) != EXPECTED_COUNTER_RECORD_COUNT
        or result.to_document().get("next_atomic_materialization_authorized")
        is not True
        or result.to_document().get("semantic_replay_complete") is not True
    ):
        _fail("semantic closure is not the complete materialization prerequisite")
    return result


def _records_from_closure(
    semantic_closure: closure_v1.K7SemanticEvidenceClosureV1,
    registry: registry_v6.CounterRegistryV6,
) -> tuple[CounterRecordV1, ...]:
    rows = []
    for resolution in semantic_closure.resolutions:
        leaf = registry.by_path.get(resolution.path)
        if leaf is None:
            _fail("semantic closure contains an unknown V6 path")
        rows.append(
            CounterRecordV1(
                registry.registry_id,
                resolution.path,
                resolution.value,
                True,
                resolution.recorder_authority_id,
                leaf.semantics_id,
                leaf.owner,
                leaf.unit,
                leaf.lane,
                leaf.scope,
                leaf.reducer,
            )
        )
    return tuple(rows)


_RECONCILIATION_GROUPS = (
    ("route.attempts", "route.successes", "route.failures"),
    ("solver.attempts", "solver.successes", "solver.failures"),
    ("process.launches", "process.exit_successes", "process.exit_failures"),
)


def _verify_v6_work_vector(
    *,
    vector: Any,
    semantic_closure: closure_v1.K7SemanticEvidenceClosureV1,
    registry: registry_v6.CounterRegistryV6,
    stage: registry_v6.StageProfileV6,
) -> None:
    if type(vector) is not WorkVectorV1:
        _fail("materialized work vector has a foreign type")
    required = registry.required_paths
    records = vector.records
    if (
        vector.counter_registry_id != registry.registry_id
        or semantic_closure.context.counter_registry_id != registry.registry_id
        or semantic_closure.context.stage_profile_id != stage.stage_profile_id
        or vector.subject_id != semantic_closure.context.logical_occurrence_id
        or vector.route_kind is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
        or type(records) is not tuple
        or len(records) != EXPECTED_COUNTER_RECORD_COUNT
        or tuple(row.path for row in records) != required
        or len({row.path for row in records}) != len(records)
        or len({row.record_id for row in records}) != len(records)
    ):
        _fail("V6 work vector does not contain each required path exactly once")
    resolutions = semantic_closure.by_path
    profile_zero_ids: list[str] = []
    for record in records:
        if type(record) is not CounterRecordV1:
            _fail("V6 work vector contains a foreign counter record")
        leaf = registry.by_path.get(record.path)
        resolution = resolutions.get(record.path)
        if (
            leaf is None
            or resolution is None
            or record.counter_registry_id != registry.registry_id
            or record.value != resolution.value
            or record.observed is not True
            or record.recorder_id != resolution.recorder_authority_id
            or (
                record.semantics_id,
                record.owner,
                record.unit,
                record.lane,
                record.scope,
                record.reducer,
            )
            != (
                leaf.semantics_id,
                leaf.owner,
                leaf.unit,
                leaf.lane,
                leaf.scope,
                leaf.reducer,
            )
        ):
            _fail("counter value, recorder, observation or V6 metadata changed")
        if (
            resolution.kind
            is closure_v1.SemanticResolutionKindV1.PROFILE_NATIVE_ZERO
        ):
            if record.value != 0:
                _fail("profile-native zero materialized a nonzero value")
            profile_zero_ids.append(record.record_id)
    if (
        len(profile_zero_ids) != EXPECTED_PROFILE_NATIVE_ZERO_COUNT
        or len(set(profile_zero_ids)) != len(profile_zero_ids)
    ):
        _fail("profile-native zero records lack explicit path recorders")

    values = vector.values
    for total, successes, failures in _RECONCILIATION_GROUPS:
        if values[total] != values[successes] + values[failures]:
            _fail(f"V6 reconciliation failed for {total}")
    if (
        (values["route.attempts"], values["route.successes"], values["route.failures"])
        != (1, 0, 1)
        or (
            values["solver.attempts"],
            values["solver.successes"],
            values["solver.failures"],
        )
        != (0, 0, 0)
    ):
        _fail("registered abstract-failed-prefix route/solver outcome changed")
    derived_paths = {
        "route.attempts", "route.successes", "route.failures",
        "solver.attempts", "solver.successes", "solver.failures",
        "process.exit_successes", "process.exit_failures",
    }
    if any(
        resolutions[path].kind
        is not closure_v1.SemanticResolutionKindV1.DERIVED_RECONCILIATION
        for path in derived_paths
    ):
        _fail("route/solver/process reconciliation lacks derived proof authority")
    forbidden_nonzero = tuple(
        path
        for path, value in values.items()
        if value
        and path.startswith(("local.", "fallback.", "rebuild."))
        and path != "local.causal_candidate_evaluations"
    )
    if forbidden_nonzero:
        _fail("abstract failed prefix contains selected-route execution work")


def _projection_values(
    *,
    vector: WorkVectorV1,
    registry: registry_v6.CounterRegistryV6,
    comparison: registry_v6.ComparisonProfileV6,
    actual: registry_v6.ActualProjectionProfileV6,
) -> tuple[tuple[str, int], ...]:
    comparison.validate(registry)
    actual.validate(registry, comparison)
    terms = actual.terms
    operational_paths = tuple(row.path for row in registry.operational_leaves)
    if (
        len(terms) != EXPECTED_PROJECTION_TERM_COUNT
        or tuple(row.source_leaf for row in terms) != operational_paths
        or len({row.source_leaf for row in terms}) != len(terms)
        or any(
            registry.by_path[row.source_leaf].lane is not LaneEnum.OPERATIONAL
            or row.source_lane is not LaneEnum.OPERATIONAL
            or row.coefficient != 1
            or row.source_semantics_id
            != registry.by_path[row.source_leaf].semantics_id
            or row.target_axis
            != registry.by_path[row.source_leaf].comparison_axis
            or row.reducer != registry.by_path[row.source_leaf].reducer
            for row in terms
        )
        or any(
            row.lane is not LaneEnum.OPERATIONAL
            and row.path in {term.source_leaf for term in terms}
            for row in registry.leaves
        )
    ):
        _fail("V6 projection does not map 182 operational leaves exactly once")
    axis_reducers = {row.name: row.reducer for row in comparison.axes}
    if tuple(axis_reducers) != SHARED_AXES:
        _fail("V6 comparison profile does not contain the exact eight axes")
    values = {axis: 0 for axis in SHARED_AXES}
    source = vector.values
    for term in terms:
        if axis_reducers[term.target_axis] is not term.reducer:
            _fail("V6 term reducer differs from its target-axis reducer")
        contribution = source[term.source_leaf] * term.coefficient
        if term.reducer is ReducerEnum.SUM:
            values[term.target_axis] += contribution
        else:
            values[term.target_axis] = max(values[term.target_axis], contribution)
    return tuple((axis, values[axis]) for axis in SHARED_AXES)


def _expected_projection_proof(
    *,
    semantic_closure: closure_v1.K7SemanticEvidenceClosureV1,
    vector: WorkVectorV1,
    comparison_vector: ComparisonVectorV1,
    registry: registry_v6.CounterRegistryV6,
    stage: registry_v6.StageProfileV6,
    comparison: registry_v6.ComparisonProfileV6,
    actual: registry_v6.ActualProjectionProfileV6,
) -> K7FormalActualProjectionProofV6:
    by_path = {row.path: row for row in vector.records}
    native_zero_paths = tuple(
        row.path
        for row in semantic_closure.resolutions
        if row.kind is closure_v1.SemanticResolutionKindV1.PROFILE_NATIVE_ZERO
    )
    return K7FormalActualProjectionProofV6(
        _PROOF_ISSUER,
        semantic_closure.closure_id,
        semantic_closure.context.context_id,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        actual.actual_projection_profile_id,
        vector.work_vector_id,
        comparison_vector.comparison_vector_id,
        tuple(row.record_id for row in vector.records),
        tuple(row.source_leaf for row in actual.terms),
        tuple(by_path[row.source_leaf].record_id for row in actual.terms),
        tuple(by_path[path].record_id for path in native_zero_paths),
        len(actual.terms),
    )


def _verify_bundle_against_closure(
    bundle: Any,
    semantic_closure: closure_v1.K7SemanticEvidenceClosureV1,
) -> None:
    if type(bundle) is not K7FormalAccountingMaterializationBundleV1:
        _fail("formal accounting verifier received a foreign bundle")
    registry, stage, comparison, actual = _official_profiles()
    vector = bundle.work_vector
    _verify_v6_work_vector(
        vector=vector,
        semantic_closure=semantic_closure,
        registry=registry,
        stage=stage,
    )
    expected_values = _projection_values(
        vector=vector,
        registry=registry,
        comparison=comparison,
        actual=actual,
    )
    expected_comparison = ComparisonVectorV1(
        comparison.comparison_profile_id,
        vector.work_vector_id,
        vector.subject_id,
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        expected_values,
    )
    expected_proof = _expected_projection_proof(
        semantic_closure=semantic_closure,
        vector=vector,
        comparison_vector=expected_comparison,
        registry=registry,
        stage=stage,
        comparison=comparison,
        actual=actual,
    )
    if (
        bundle.semantic_evidence_closure_id != semantic_closure.closure_id
        or bundle.semantic_evidence_closure_context_id
        != semantic_closure.context.context_id
        or bundle.counter_registry_id != registry.registry_id
        or bundle.stage_profile_id != stage.stage_profile_id
        or bundle.comparison_profile_id != comparison.comparison_profile_id
        or bundle.actual_projection_profile_id
        != actual.actual_projection_profile_id
        or bundle.comparison_vector.to_dict() != expected_comparison.to_dict()
        or bundle.actual_projection_proof.to_document()
        != expected_proof.to_document()
        or bundle.comparison_vector.subject_id != vector.subject_id
        or bundle.comparison_vector.route_kind
        is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
    ):
        _fail("actual comparison, projection proof or identity reference mismatch")


def _materialize_verified_closure(
    semantic_closure: closure_v1.K7SemanticEvidenceClosureV1,
) -> K7FormalAccountingMaterializationBundleV1:
    registry, stage, comparison, actual = _official_profiles()
    records = _records_from_closure(semantic_closure, registry)
    vector = WorkVectorV1(
        registry.registry_id,
        semantic_closure.context.logical_occurrence_id,
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        records,
    )
    _verify_v6_work_vector(
        vector=vector,
        semantic_closure=semantic_closure,
        registry=registry,
        stage=stage,
    )
    comparison_vector = ComparisonVectorV1(
        comparison.comparison_profile_id,
        vector.work_vector_id,
        vector.subject_id,
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        _projection_values(
            vector=vector,
            registry=registry,
            comparison=comparison,
            actual=actual,
        ),
    )
    proof = _expected_projection_proof(
        semantic_closure=semantic_closure,
        vector=vector,
        comparison_vector=comparison_vector,
        registry=registry,
        stage=stage,
        comparison=comparison,
        actual=actual,
    )
    result = K7FormalAccountingMaterializationBundleV1(
        _BUNDLE_ISSUER,
        semantic_closure.closure_id,
        semantic_closure.context.context_id,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        actual.actual_projection_profile_id,
        vector,
        comparison_vector,
        proof,
    )
    _verify_bundle_against_closure(result, semantic_closure)
    return result


_WORK_VECTOR_FIELDS = {
    "schema", "counter_registry_id", "subject_id", "route_kind",
    "counter_record_ids", "records", "work_vector_id",
}


def _parse_work_vector(document: Any) -> WorkVectorV1:
    row = _fields(document, _WORK_VECTOR_FIELDS, "portable work vector")
    if (
        row["schema"] != "acfqp.work_vector.v1"
        or type(row["records"]) is not list
        or type(row["counter_record_ids"]) is not list
    ):
        _fail("portable work-vector schema or record lists changed")
    try:
        records = tuple(CounterRecordV1.from_dict(item) for item in row["records"])
        vector = WorkVectorV1(
            row["counter_registry_id"],
            row["subject_id"],
            row["route_kind"],
            records,
        )
    except Exception as error:
        raise ConstructionK7FormalAccountingMaterializerV1Error(
            "portable counter record or work vector failed content replay"
        ) from error
    if (
        row["counter_record_ids"] != [record.record_id for record in records]
        or row["work_vector_id"] != vector.work_vector_id
    ):
        _fail("portable work-vector record or vector identity changed")
    return vector


_BUNDLE_FIELDS = {
    "schema", "schema_version", "proposed_contract_version", "profile_key",
    "semantic_evidence_closure_id", "semantic_evidence_closure_context_id",
    "counter_registry_id", "stage_profile_id", "comparison_profile_id",
    "actual_projection_profile_id", "route_kind", "counter_record_count",
    "counter_record_ids", "work_vector", "comparison_vector",
    "actual_projection_proof", "semantic_closure_replayed_from_full_roots",
    "v1_registry_validator_used", "formal_accounting_materialized",
    "terminal_artifact_issued", "certificate_issued", "official_execution_allowed",
    "counter_completeness_gate_passed", "workload_economics_gate_passed",
    "scalar_cost_defined", "formal_accounting_materialization_bundle_id",
}


def _parse_bundle_document(
    document: Any,
) -> K7FormalAccountingMaterializationBundleV1:
    row = _fields(document, _BUNDLE_FIELDS, "formal accounting bundle")
    if (
        row["schema"]
        != "acfqp.construction_k7_formal_accounting_materialization_bundle.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or row["profile_key"] != PROFILE_KEY
        or row["route_kind"] != RouteKindEnum.ABSTRACT_FAILED_PREFIX.value
        or row["counter_record_count"] != EXPECTED_COUNTER_RECORD_COUNT
        or type(row["counter_record_ids"]) is not list
        or row["semantic_closure_replayed_from_full_roots"] is not True
        or row["v1_registry_validator_used"] is not False
        or row["formal_accounting_materialized"] is not True
        or any(
            row[name] is not False
            for name in (
                "terminal_artifact_issued",
                "certificate_issued",
                "official_execution_allowed",
                "counter_completeness_gate_passed",
                "workload_economics_gate_passed",
                "scalar_cost_defined",
            )
        )
    ):
        _fail("formal accounting bundle schema, counts or Gate locks changed")
    vector = _parse_work_vector(row["work_vector"])
    try:
        comparison = ComparisonVectorV1.from_dict(row["comparison_vector"])
    except Exception as error:
        raise ConstructionK7FormalAccountingMaterializerV1Error(
            "portable comparison vector failed content replay"
        ) from error
    proof = K7FormalActualProjectionProofV6._from_document(
        row["actual_projection_proof"]
    )
    result = K7FormalAccountingMaterializationBundleV1(
        _BUNDLE_ISSUER,
        row["semantic_evidence_closure_id"],
        row["semantic_evidence_closure_context_id"],
        row["counter_registry_id"],
        row["stage_profile_id"],
        row["comparison_profile_id"],
        row["actual_projection_profile_id"],
        vector,
        comparison,
        proof,
    )
    if (
        row["counter_record_ids"] != [item.record_id for item in vector.records]
        or row["formal_accounting_materialization_bundle_id"] != result.bundle_id
        or row != result.to_document()
    ):
        _fail("portable formal accounting bundle content identity changed")
    return result


def materialize_k7_formal_accounting_v1(
    *,
    semantic_closure_raw: bytes,
    closure_replay_inputs: Mapping[str, Any],
) -> K7FormalAccountingMaterializationBundleV1:
    """Replay the full semantic roots once and atomically materialize V6."""

    semantic_closure = _replay_semantic_closure(
        semantic_closure_raw=semantic_closure_raw,
        closure_replay_inputs=closure_replay_inputs,
    )
    return _materialize_verified_closure(semantic_closure)


def verify_k7_formal_accounting_materialization_bytes_v1(
    *,
    raw: bytes,
    semantic_closure_raw: bytes,
    closure_replay_inputs: Mapping[str, Any],
) -> K7FormalAccountingMaterializationBundleV1:
    """Replay portable bytes and recompute every V6 value from full roots."""

    document = _canonical_document(raw, "formal accounting materialization")
    claimed_id = document.get("formal_accounting_materialization_bundle_id")
    payload = dict(document)
    payload.pop("formal_accounting_materialization_bundle_id", None)
    if (
        type(claimed_id) is not str
        or content_id(MATERIALIZATION_BUNDLE_V1_DOMAIN, payload) != claimed_id
    ):
        _fail("formal accounting materialization content identity changed")
    claimed = _parse_bundle_document(document)
    semantic_closure = _replay_semantic_closure(
        semantic_closure_raw=semantic_closure_raw,
        closure_replay_inputs=closure_replay_inputs,
    )
    _verify_bundle_against_closure(claimed, semantic_closure)
    return claimed


__all__ = (
    "ACTUAL_PROJECTION_PROOF_V6_DOMAIN",
    "ConstructionK7FormalAccountingMaterializerV1Error",
    "EXPECTED_COUNTER_RECORD_COUNT",
    "EXPECTED_PROFILE_NATIVE_ZERO_COUNT",
    "EXPECTED_PROJECTION_TERM_COUNT",
    "K7FormalAccountingMaterializationBundleV1",
    "K7FormalActualProjectionProofV6",
    "MATERIALIZATION_BUNDLE_V1_DOMAIN",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "materialize_k7_formal_accounting_v1",
    "verify_k7_formal_accounting_materialization_bytes_v1",
)
