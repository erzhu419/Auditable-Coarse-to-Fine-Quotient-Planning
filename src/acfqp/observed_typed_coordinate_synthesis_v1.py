"""Observation-only synthesis of a reusable typed partial RAPM.

The production surface consumes exactly the three allowlisted V0-042 source
authorities.  It has no kernel, query, planner, value, policy, J0, target
signature, callback, or caller-selected coordinate channel.  Missing rows are
preserved as unknown ambiguity; only logged rows contribute congruence evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import inspect
from itertools import combinations
from typing import Any, Mapping

from acfqp.observation_partial_rapm_v1 import (
    AmbiguityRowStatus,
    CanonicalGroundActionV1,
    CanonicalStateObservationV1,
    DeterministicObservationProfileV1,
    FrozenActionCoordinateValuesV2,
    FrozenStateCoordinateValuesV2,
    FrozenTypedActionCoordinateAtomV2,
    FrozenTypedCoordinateProposalV2,
    FrozenTypedCoordinateValueTableV2,
    ObservationLogManifestV1,
    ObservationPartialRAPMBuildV1,
    ObservationPartialRAPMInvariantViolation,
    PlanningKind,
    PreregisteredObservationAuthorityV1,
    SuccessorKind,
    TrustedCompleteActionCatalogueV1,
    TypedActionAtomKind,
    build_observation_partial_rapm_from_typed_values_v2,
    validate_preregistered_observation_source_graph_v1,
    verify_observation_partial_rapm_from_typed_values_v2,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "lmb_query_free_observed_typed_coordinate_synthesis_v0"
SUCCESS_STATUS = "OBSERVATION_CONSISTENT_TYPED_PARTIAL_RAPM"
PRODUCTION_CANDIDATE_CAP = 4096
STATE_PROGRAM_COUNT = 8
ACTION_PROGRAM_COUNT = 4
REQUIRED_CANDIDATE_COUNT = 2**STATE_PROGRAM_COUNT * 2**ACTION_PROGRAM_COUNT
DSL_PROFILE = "lmb_structural_typed_expression_dsl_v1"
EXPRESSION_SCHEMA = "acfqp.generated_coordinate_expression@v1"
EXPRESSION_DOMAIN = "acfqp:generated-coordinate-expression:v1"

CURRENT_AUTHORITY_ID = "5aac3e8f1e7b8b2af4cafe50a8b54c25c21008d2b9fccd4aaaeebc3ab79df825"
CURRENT_STRUCTURAL_ID = "eb4d4562d979fe6312fe8c7876176b6a8c6e99ee859e5da67e53ea2fac7a76e8"

DOMAIN_TAGS = {
    "structural": "acfqp:observed-structural-primitive-binding:v1",
    "registry": "acfqp:observed-dsl-registry-binding:v1",
    "spec": "acfqp:observed-coordinate-synthesis-spec:v1",
    "cell": "acfqp:observed-candidate-cell:v1",
    "partition": "acfqp:observed-candidate-partition:v1",
    "action_partition": "acfqp:observed-candidate-action-partition:v1",
    "candidate": "acfqp:observed-coordinate-candidate:v1",
    "trace": "acfqp:observed-coordinate-candidate-trace:v1",
    "entry": "acfqp:observed-entry-evidence:v1",
    "signature": "acfqp:observed-ground-signature:v1",
    "atom": "acfqp:observed-coordinate-predicate-atom:v1",
    "tree": "acfqp:observed-coordinate-predicate-tree:v1",
    "telemetry": "acfqp:observation-synthesis-telemetry:v1",
    "certificate": "acfqp:observed-typed-partial-rapm-certificate:v1",
    "result": "acfqp:observed-typed-partial-rapm-result:v1",
    "control": "acfqp:observed-synthesis-cap-control-outcome:v1",
}

SELECTION_RULE = (
    "max_point_rows_then_max_observed_alias_pairs_then_min_partial_rows_then_"
    "min_entries_cells_programs_ast_complexity_ids_partition_candidate_id_v1"
)
THRESHOLD_RULE = "adjacent_distinct_exact_value_midpoints_v1"
OBSERVED_SIGNATURE_RULE = (
    "reward_vector_failure_terminal_and_projected_joint_successor_v1"
)
# Independently reviewed literal hashes of the exact function groups checked by
# ``_validate_implementation_authority``.  They are not computed at import time.
IMPLEMENTATION_CONTRACT_SHA256 = "d3d853e4b19f43157c1e7d46114b8b0d78cf902e4915d3cea14d5451303bba5e"
OBSERVATION_EVALUATOR_SHA256 = "b514b09b4ee2d1b41d761e99b0b771e535afe820b9a7876836c129c2058c3f3b"
OBSERVATION_COMPILER_SHA256 = "08ac74c1235478159617f476f79a144a917026e918da8f4f1106019dabce0822"
OBSERVATION_SELECTOR_SHA256 = "ddf6b186fb405de3a815913f2f18f22d76b7daa4d798a748035be757d7e4cdca"


class ObservedTypedCoordinateInvariantViolation(ValueError):
    """The closed synthesis authority or deterministic replay is inconsistent."""


class ExpressionType(str, Enum):
    ACTION_SET = "ACTION_SET"
    TILE_SET = "TILE_SET"
    INT_VECTOR = "INT_VECTOR"
    TILE_TYPE = "TILE_TYPE"
    INTEGER = "INTEGER"
    BOOLEAN = "BOOLEAN"


class ExpressionContext(str, Enum):
    STATE = "STATE"
    STATE_ACTION = "STATE_ACTION"


class CandidateEntryClass(str, Enum):
    POINT_IDENTIFIED = "POINT_IDENTIFIED"
    PARTIAL_UNKNOWN = "PARTIAL_UNKNOWN"
    UNOBSERVED_UNKNOWN = "UNOBSERVED_UNKNOWN"
    OBSERVED_CONTRADICTION = "OBSERVED_CONTRADICTION"


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role]
    except (KeyError, TypeError, ValueError) as error:
        raise ObservedTypedCoordinateInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ObservedTypedCoordinateInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _exact_tuple(value: Any, item_type: type, field: str) -> tuple[Any, ...]:
    if type(value) is not tuple or any(type(item) is not item_type for item in value):
        raise ObservedTypedCoordinateInvariantViolation(
            f"{field} rejects nested substitutions before canonical access"
        )
    return value


def _fraction_document(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


_PRIMITIVE_SIGNATURES: dict[str, tuple[ExpressionType, ExpressionContext, bool]] = {
    "legal_actions": (ExpressionType.ACTION_SET, ExpressionContext.STATE, False),
    "remaining_tiles": (ExpressionType.TILE_SET, ExpressionContext.STATE, False),
    "buffer_counts": (ExpressionType.INT_VECTOR, ExpressionContext.STATE, False),
    "buffer_capacity": (ExpressionType.INTEGER, ExpressionContext.STATE, False),
    "selected_tile_type": (ExpressionType.TILE_TYPE, ExpressionContext.STATE_ACTION, False),
    "integer_literal": (ExpressionType.INTEGER, ExpressionContext.STATE, True),
}
_OPERATOR_SIGNATURES: dict[str, tuple[tuple[ExpressionType, ...], ExpressionType]] = {
    "cardinality": ((ExpressionType.ACTION_SET,), ExpressionType.INTEGER),
    "cardinality_tiles": ((ExpressionType.TILE_SET,), ExpressionType.INTEGER),
    "sum_vector": ((ExpressionType.INT_VECTOR,), ExpressionType.INTEGER),
    "max_vector": ((ExpressionType.INT_VECTOR,), ExpressionType.INTEGER),
    "count_equal": ((ExpressionType.INT_VECTOR, ExpressionType.INTEGER), ExpressionType.INTEGER),
    "subtract": ((ExpressionType.INTEGER, ExpressionType.INTEGER), ExpressionType.INTEGER),
    "buffer_at_type": ((ExpressionType.INT_VECTOR, ExpressionType.TILE_TYPE), ExpressionType.INTEGER),
    "equals": ((ExpressionType.INTEGER, ExpressionType.INTEGER), ExpressionType.BOOLEAN),
}
_OPERATION_ORDER = tuple(_PRIMITIVE_SIGNATURES) + tuple(_OPERATOR_SIGNATURES)


@dataclass(frozen=True, slots=True)
class ObservedGeneratedExpressionV1:
    operation: str
    result_type: ExpressionType
    context: ExpressionContext
    arguments: tuple["ObservedGeneratedExpressionV1", ...] = ()
    literal: int | None = None
    schema: str = EXPRESSION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != EXPRESSION_SCHEMA or type(self.operation) is not str:
            raise ObservedTypedCoordinateInvariantViolation("expression schema/operation substitution")
        if type(self.result_type) is not ExpressionType or type(self.context) is not ExpressionContext:
            raise ObservedTypedCoordinateInvariantViolation("expression type/context substitution")
        _exact_tuple(self.arguments, ObservedGeneratedExpressionV1, "expression arguments")
        if self.operation in _PRIMITIVE_SIGNATURES:
            result_type, context, requires_literal = _PRIMITIVE_SIGNATURES[self.operation]
            if self.arguments or self.result_type is not result_type or self.context is not context:
                raise ObservedTypedCoordinateInvariantViolation("primitive expression contract mismatch")
            if requires_literal != (self.literal is not None):
                raise ObservedTypedCoordinateInvariantViolation("primitive literal contract mismatch")
            if self.literal is not None and type(self.literal) is not int:
                raise ObservedTypedCoordinateInvariantViolation("integer literal substitution")
            return
        signature = _OPERATOR_SIGNATURES.get(self.operation)
        if signature is None or self.literal is not None:
            raise ObservedTypedCoordinateInvariantViolation("operator expression contract mismatch")
        argument_types, result_type = signature
        if tuple(item.result_type for item in self.arguments) != argument_types:
            raise ObservedTypedCoordinateInvariantViolation("operator argument type mismatch")
        expected_context = (
            ExpressionContext.STATE_ACTION
            if any(item.context is ExpressionContext.STATE_ACTION for item in self.arguments)
            else ExpressionContext.STATE
        )
        if self.result_type is not result_type or self.context is not expected_context:
            raise ObservedTypedCoordinateInvariantViolation("operator result/context mismatch")

    @property
    def node_count(self) -> int:
        return 1 + sum(item.node_count for item in self.arguments)

    @property
    def depth(self) -> int:
        return 0 if not self.arguments else 1 + max(item.depth for item in self.arguments)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "operation": self.operation,
            "result_type": self.result_type.value,
            "context": self.context.value,
            "arguments": [item.to_document() for item in self.arguments],
            "literal": self.literal,
        }

    @property
    def expression_id(self) -> str:
        return hashlib.sha256(
            EXPRESSION_DOMAIN.encode("utf-8") + b"\x00" + canonical_json_bytes(self._payload())
        ).hexdigest()

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "expression_id": self.expression_id}


def _primitive(operation: str, literal: int | None = None) -> ObservedGeneratedExpressionV1:
    result_type, context, _ = _PRIMITIVE_SIGNATURES[operation]
    return ObservedGeneratedExpressionV1(operation, result_type, context, (), literal)


def _operator(
    operation: str, arguments: tuple[ObservedGeneratedExpressionV1, ...]
) -> ObservedGeneratedExpressionV1:
    result_type = _OPERATOR_SIGNATURES[operation][1]
    context = (
        ExpressionContext.STATE_ACTION
        if any(item.context is ExpressionContext.STATE_ACTION for item in arguments)
        else ExpressionContext.STATE
    )
    return ObservedGeneratedExpressionV1(operation, result_type, context, arguments)


def _enumerate_programs() -> tuple[
    tuple[ObservedGeneratedExpressionV1, ...], tuple[ObservedGeneratedExpressionV1, ...]
]:
    legal = _primitive("legal_actions")
    remaining = _primitive("remaining_tiles")
    buffer = _primitive("buffer_counts")
    capacity = _primitive("buffer_capacity")
    selected = _primitive("selected_tile_type")
    literals = tuple(_primitive("integer_literal", value) for value in (0, 1, 2))
    state = (
        _operator("cardinality", (legal,)),
        _operator("cardinality_tiles", (remaining,)),
        _operator("sum_vector", (buffer,)),
        _operator("max_vector", (buffer,)),
        *tuple(_operator("count_equal", (buffer, value)) for value in literals),
        _operator("subtract", (capacity, _operator("sum_vector", (buffer,)))),
    )
    selected_value = _operator("buffer_at_type", (buffer, selected))
    action = (
        selected_value,
        *tuple(_operator("equals", (selected_value, value)) for value in literals),
    )
    state = tuple(sorted(state, key=lambda item: item.expression_id))
    action = tuple(sorted(action, key=lambda item: item.expression_id))
    if len(state) != STATE_PROGRAM_COUNT or len(action) != ACTION_PROGRAM_COUNT:
        raise ObservedTypedCoordinateInvariantViolation("fixed DSL registry cardinality changed")
    return state, action


@dataclass(frozen=True, slots=True)
class ObservedStructuralPrimitiveRegistryBindingV1:
    observation_authority_id: str
    structural_id: str
    tile_count: int
    tile_type_count: int
    buffer_capacity: int
    implementation_contract_sha256: str = IMPLEMENTATION_CONTRACT_SHA256

    def __post_init__(self) -> None:
        _cid(self.observation_authority_id, "structural binding authority")
        _cid(self.structural_id, "structural binding structural_id")
        if (self.observation_authority_id, self.structural_id) != (
            CURRENT_AUTHORITY_ID, CURRENT_STRUCTURAL_ID
        ):
            raise ObservedTypedCoordinateInvariantViolation("unknown authority/structural binding pair")
        if (self.tile_count, self.tile_type_count, self.buffer_capacity) != (6, 2, 3):
            raise ObservedTypedCoordinateInvariantViolation("structural primitive substitution")
        _cid(self.implementation_contract_sha256, "implementation contract digest")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observed_structural_primitive_registry_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "observation_authority_id": self.observation_authority_id,
            "structural_id": self.structural_id,
            "tile_count": self.tile_count,
            "tile_type_count": self.tile_type_count,
            "buffer_capacity": self.buffer_capacity,
            "implementation_contract_sha256": self.implementation_contract_sha256,
        }

    @property
    def binding_id(self) -> str:
        return _content_id("structural", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class ObservedDSLRegistryBindingV1:
    state_programs: tuple[ObservedGeneratedExpressionV1, ...]
    action_programs: tuple[ObservedGeneratedExpressionV1, ...]
    profile: str = DSL_PROFILE
    evaluator_implementation_sha256: str = OBSERVATION_EVALUATOR_SHA256
    selector_implementation_sha256: str = OBSERVATION_SELECTOR_SHA256
    compiler_implementation_sha256: str = OBSERVATION_COMPILER_SHA256

    def __post_init__(self) -> None:
        _exact_tuple(self.state_programs, ObservedGeneratedExpressionV1, "state program registry")
        _exact_tuple(self.action_programs, ObservedGeneratedExpressionV1, "action program registry")
        expected_state, expected_action = _enumerate_programs()
        if self.state_programs != expected_state or self.action_programs != expected_action:
            raise ObservedTypedCoordinateInvariantViolation("fixed DSL registry substitution")
        if self.profile != DSL_PROFILE:
            raise ObservedTypedCoordinateInvariantViolation("DSL profile substitution")
        _cid(self.evaluator_implementation_sha256, "observation evaluator digest")
        _cid(self.selector_implementation_sha256, "observation selector digest")
        _cid(self.compiler_implementation_sha256, "observation compiler digest")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observed_dsl_registry_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "profile": self.profile,
            "state_programs": [item.to_document() for item in self.state_programs],
            "action_programs": [item.to_document() for item in self.action_programs],
            "evaluator_implementation_sha256": self.evaluator_implementation_sha256,
            "selector_implementation_sha256": self.selector_implementation_sha256,
            "compiler_implementation_sha256": self.compiler_implementation_sha256,
        }

    @property
    def registry_id(self) -> str:
        return _content_id("registry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registry_id": self.registry_id}


def _eval_expression(
    expression: ObservedGeneratedExpressionV1,
    state: CanonicalStateObservationV1,
    catalogue: TrustedCompleteActionCatalogueV1,
    action: CanonicalGroundActionV1 | None,
    structural: ObservedStructuralPrimitiveRegistryBindingV1,
) -> Any:
    operation = expression.operation
    if operation == "legal_actions":
        return catalogue.actions
    if operation == "remaining_tiles":
        return tuple(
            tile for tile in range(structural.tile_count)
            if not state.removed_mask & (1 << tile)
        )
    if operation == "buffer_counts":
        return state.buffer_counts
    if operation == "buffer_capacity":
        return structural.buffer_capacity
    if operation == "selected_tile_type":
        if type(action) is not CanonicalGroundActionV1:
            raise ObservedTypedCoordinateInvariantViolation("state-action expression lacks exact action")
        return action.selected_type
    if operation == "integer_literal":
        return expression.literal
    values = tuple(_eval_expression(item, state, catalogue, action, structural) for item in expression.arguments)
    if operation in {"cardinality", "cardinality_tiles"}:
        return len(values[0])
    if operation == "sum_vector":
        return sum(values[0])
    if operation == "max_vector":
        return max(values[0], default=0)
    if operation == "count_equal":
        return sum(item == values[1] for item in values[0])
    if operation == "subtract":
        return values[0] - values[1]
    if operation == "buffer_at_type":
        return values[0][values[1]]
    if operation == "equals":
        return values[0] == values[1]
    raise ObservedTypedCoordinateInvariantViolation("unreachable fixed DSL operation")


@dataclass(frozen=True, slots=True)
class ObservedSynthesisSpecV1:
    observation_authority_id: str
    structural_binding_id: str
    dsl_registry_id: str
    required_candidate_count: int = REQUIRED_CANDIDATE_COUNT
    candidate_cap: int = PRODUCTION_CANDIDATE_CAP
    selection_rule: str = SELECTION_RULE
    threshold_rule: str = THRESHOLD_RULE
    observed_signature_rule: str = OBSERVED_SIGNATURE_RULE
    query_inputs: int = 0

    def __post_init__(self) -> None:
        for value, field in ((self.observation_authority_id, "authority"), (self.structural_binding_id, "structural binding"), (self.dsl_registry_id, "DSL registry")):
            _cid(value, field)
        if self.required_candidate_count != REQUIRED_CANDIDATE_COUNT or self.candidate_cap != PRODUCTION_CANDIDATE_CAP:
            raise ObservedTypedCoordinateInvariantViolation("production candidate cap/count substitution")
        if self.selection_rule != SELECTION_RULE or self.threshold_rule != THRESHOLD_RULE or self.observed_signature_rule != OBSERVED_SIGNATURE_RULE or self.query_inputs != 0:
            raise ObservedTypedCoordinateInvariantViolation("synthesis information/selection contract substitution")

    def _payload(self) -> dict[str, Any]:
        return {"schema": "acfqp.observed_coordinate_synthesis_spec.v1", "schema_version": SCHEMA_VERSION, "profile_key": PROFILE_KEY, "observation_authority_id": self.observation_authority_id, "structural_binding_id": self.structural_binding_id, "dsl_registry_id": self.dsl_registry_id, "required_candidate_count": self.required_candidate_count, "candidate_cap": self.candidate_cap, "selection_rule": self.selection_rule, "threshold_rule": self.threshold_rule, "observed_signature_rule": self.observed_signature_rule, "query_inputs": self.query_inputs}

    @property
    def spec_id(self) -> str:
        return _content_id("spec", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "spec_id": self.spec_id}

@dataclass(frozen=True, slots=True)
class ObservedEntryEvidenceV1:
    source_cell_id: str
    action_label: tuple[bool, ...]
    support_ground_row_ids: tuple[str, ...]
    observed_ground_row_ids: tuple[str, ...]
    missing_ground_row_ids: tuple[str, ...]
    distinct_observed_signature_ids: tuple[str, ...]
    classification: CandidateEntryClass

    def __post_init__(self) -> None:
        _cid(self.source_cell_id, "entry source cell")
        if type(self.action_label) is not tuple or not self.action_label or any(
            type(value) is not bool for value in self.action_label
        ):
            raise ObservedTypedCoordinateInvariantViolation("entry action label must be nonempty booleans")
        for values, field in (
            (self.support_ground_row_ids, "entry support rows"),
            (self.observed_ground_row_ids, "entry observed rows"),
            (self.missing_ground_row_ids, "entry missing rows"),
            (self.distinct_observed_signature_ids, "entry observed signatures"),
        ):
            if type(values) is not tuple or any(type(item) is not str for item in values):
                raise ObservedTypedCoordinateInvariantViolation(f"{field} must be an exact tuple")
            for item in values:
                _cid(item, field)
            if values != tuple(sorted(set(values))):
                raise ObservedTypedCoordinateInvariantViolation(f"{field} must be unique and sorted")
        if not self.support_ground_row_ids or set(self.observed_ground_row_ids) & set(self.missing_ground_row_ids) or tuple(sorted((*self.observed_ground_row_ids, *self.missing_ground_row_ids))) != self.support_ground_row_ids:
            raise ObservedTypedCoordinateInvariantViolation("entry observed/missing rows do not partition support")
        if type(self.classification) is not CandidateEntryClass:
            raise ObservedTypedCoordinateInvariantViolation("entry classification substitution")
        expected = (
            CandidateEntryClass.OBSERVED_CONTRADICTION
            if len(self.distinct_observed_signature_ids) > 1
            else CandidateEntryClass.UNOBSERVED_UNKNOWN
            if not self.observed_ground_row_ids
            else CandidateEntryClass.PARTIAL_UNKNOWN
            if self.missing_ground_row_ids
            else CandidateEntryClass.POINT_IDENTIFIED
        )
        if self.classification is not expected:
            raise ObservedTypedCoordinateInvariantViolation("entry evidence classification mismatch")

    def _payload(self) -> dict[str, Any]:
        return {"schema": "acfqp.observed_entry_evidence.v1", "source_cell_id": self.source_cell_id, "action_label": list(self.action_label), "support_ground_row_ids": list(self.support_ground_row_ids), "observed_ground_row_ids": list(self.observed_ground_row_ids), "missing_ground_row_ids": list(self.missing_ground_row_ids), "distinct_observed_signature_ids": list(self.distinct_observed_signature_ids), "classification": self.classification.value}

    @property
    def entry_id(self) -> str:
        return _content_id("entry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "entry_id": self.entry_id}


@dataclass(frozen=True, slots=True)
class ObservedCandidateV1:
    candidate_index: int
    state_mask: int
    action_mask: int
    state_expression_ids: tuple[str, ...]
    action_expression_ids: tuple[str, ...]
    action_atom_ids: tuple[str, ...]
    partition_id: str
    active_cell_count: int
    total_cell_count: int
    abstract_entry_count: int
    action_partition_id: str
    point_identified_registered_rows: int
    observed_equal_alias_pair_count: int
    partial_unknown_registered_rows: int
    separated_null_conflict_pair_count: int
    nontrivial_point_entry_count: int
    availability_violation_count: int
    contradiction_entry_count: int
    entry_evidence: tuple[ObservedEntryEvidenceV1, ...]
    rejection_codes: tuple[str, ...]
    admissible: bool

    def __post_init__(self) -> None:
        if type(self.candidate_index) is not int or not 1 <= self.candidate_index <= REQUIRED_CANDIDATE_COUNT:
            raise ObservedTypedCoordinateInvariantViolation("candidate index out of range")
        if type(self.state_mask) is not int or not 0 <= self.state_mask < 2**STATE_PROGRAM_COUNT or type(self.action_mask) is not int or not 0 <= self.action_mask < 2**ACTION_PROGRAM_COUNT:
            raise ObservedTypedCoordinateInvariantViolation("candidate mask out of range")
        for values, field in ((self.state_expression_ids, "candidate state IDs"), (self.action_expression_ids, "candidate action IDs"), (self.action_atom_ids, "candidate action atom IDs")):
            if type(values) is not tuple or values != tuple(sorted(set(values))):
                raise ObservedTypedCoordinateInvariantViolation(f"{field} must be unique and sorted")
            for item in values:
                _cid(item, field)
        _cid(self.partition_id, "candidate partition")
        _cid(self.action_partition_id, "candidate action partition")
        for field in ("active_cell_count", "total_cell_count", "abstract_entry_count", "point_identified_registered_rows", "observed_equal_alias_pair_count", "partial_unknown_registered_rows", "separated_null_conflict_pair_count", "nontrivial_point_entry_count", "availability_violation_count", "contradiction_entry_count"):
            if type(getattr(self, field)) is not int or getattr(self, field) < 0:
                raise ObservedTypedCoordinateInvariantViolation(f"{field} must be nonnegative")
        _exact_tuple(self.entry_evidence, ObservedEntryEvidenceV1, "candidate entry evidence")
        if tuple(item.entry_id for item in self.entry_evidence) != tuple(sorted({item.entry_id for item in self.entry_evidence})):
            raise ObservedTypedCoordinateInvariantViolation("candidate entry evidence must be unique and sorted")
        if type(self.rejection_codes) is not tuple or self.rejection_codes != tuple(sorted(set(self.rejection_codes))) or any(type(item) is not str or not item for item in self.rejection_codes):
            raise ObservedTypedCoordinateInvariantViolation("candidate rejection codes must be unique sorted text")
        if type(self.admissible) is not bool or self.admissible != (not self.rejection_codes):
            raise ObservedTypedCoordinateInvariantViolation("candidate admissibility/rejection mismatch")

    def _payload(self) -> dict[str, Any]:
        return {"schema": "acfqp.observed_coordinate_candidate.v1", "candidate_index": self.candidate_index, "state_mask": self.state_mask, "action_mask": self.action_mask, "state_expression_ids": list(self.state_expression_ids), "action_expression_ids": list(self.action_expression_ids), "action_atom_ids": list(self.action_atom_ids), "partition_id": self.partition_id, "action_partition_id": self.action_partition_id, "active_cell_count": self.active_cell_count, "total_cell_count": self.total_cell_count, "abstract_entry_count": self.abstract_entry_count, "point_identified_registered_rows": self.point_identified_registered_rows, "observed_equal_alias_pair_count": self.observed_equal_alias_pair_count, "partial_unknown_registered_rows": self.partial_unknown_registered_rows, "separated_null_conflict_pair_count": self.separated_null_conflict_pair_count, "nontrivial_point_entry_count": self.nontrivial_point_entry_count, "availability_violation_count": self.availability_violation_count, "contradiction_entry_count": self.contradiction_entry_count, "entry_evidence": [item.to_document() for item in self.entry_evidence], "rejection_codes": list(self.rejection_codes), "admissible": self.admissible, "missing_rows_used_as_equality_mismatch_or_negative_evidence": 0}

    @property
    def candidate_id(self) -> str:
        return _content_id("candidate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "candidate_id": self.candidate_id}


def _structural_binding(authority: PreregisteredObservationAuthorityV1, log: ObservationLogManifestV1) -> ObservedStructuralPrimitiveRegistryBindingV1:
    return ObservedStructuralPrimitiveRegistryBindingV1(authority.authority_id, log.structural_id, 6, 2, 3)


def _dsl_registry() -> ObservedDSLRegistryBindingV1:
    state, action = _enumerate_programs()
    return ObservedDSLRegistryBindingV1(state, action)


def _build_value_table(
    log: ObservationLogManifestV1,
    profile: DeterministicObservationProfileV1,
    authority: PreregisteredObservationAuthorityV1,
    structural: ObservedStructuralPrimitiveRegistryBindingV1,
    registry: ObservedDSLRegistryBindingV1,
) -> FrozenTypedCoordinateValueTableV2:
    catalogue_by_state = {item.state_id: item for item in log.action_catalogues}
    if set(catalogue_by_state) != {item.state_id for item in log.states}:
        raise ObservedTypedCoordinateInvariantViolation("complete state/catalogue binding changed")
    state_rows: list[FrozenStateCoordinateValuesV2] = []
    action_rows: list[FrozenActionCoordinateValuesV2] = []
    for state in log.states:
        if (
            len(state.buffer_counts) != structural.tile_type_count
            or any(value not in (0, 1, 2) for value in state.buffer_counts)
            or state.removed_mask >> structural.tile_count
        ):
            raise ObservedTypedCoordinateInvariantViolation("state exceeds closed structural primitive scope")
        catalogue = catalogue_by_state[state.state_id]
        state_rows.append(FrozenStateCoordinateValuesV2(state.state_id, tuple(_eval_expression(expression, state, catalogue, None, structural) for expression in registry.state_programs)))
        for action in catalogue.actions:
            if not 0 <= action.selected_type < structural.tile_type_count:
                raise ObservedTypedCoordinateInvariantViolation("action selected type exceeds structural scope")
            action_rows.append(FrozenActionCoordinateValuesV2(action.ground_row_id, state.state_id, action.action_id, tuple(_eval_expression(expression, state, catalogue, action, structural) for expression in registry.action_programs)))
    return FrozenTypedCoordinateValueTableV2(
        log.log_id,
        profile.profile_id,
        authority.authority_id,
        structural.binding_id,
        registry.registry_id,
        tuple(item.expression_id for item in registry.state_programs),
        tuple(item.expression_id for item in registry.action_programs),
        tuple(sorted(state_rows, key=lambda item: item.state_id)),
        tuple(sorted(action_rows, key=lambda item: item.ground_row_id)),
    )


def _selected_ids(programs: tuple[ObservedGeneratedExpressionV1, ...], mask: int) -> tuple[str, ...]:
    return tuple(item.expression_id for index, item in enumerate(programs) if mask & (1 << index))


def _compile_action_atoms(
    expression_ids: tuple[str, ...], table: FrozenTypedCoordinateValueTableV2
):
    if not expression_ids:
        return (FrozenTypedActionCoordinateAtomV2(TypedActionAtomKind.UNIVERSAL_TRUE, None, None),)
    atoms = []
    for expression_id in expression_ids:
        index = table.action_expression_ids.index(expression_id)
        values = tuple(row.values[index] for row in table.action_rows)
        runtime_types = {type(value) for value in values}
        if runtime_types == {bool}:
            atoms.append(FrozenTypedActionCoordinateAtomV2(TypedActionAtomKind.BOOLEAN_IDENTITY, expression_id, None))
        elif runtime_types == {int}:
            distinct = tuple(sorted(set(values)))
            atoms.extend(FrozenTypedActionCoordinateAtomV2(TypedActionAtomKind.INTEGER_LEQ, expression_id, Fraction(left + right, 2)) for left, right in zip(distinct, distinct[1:]))
        else:
            raise ObservedTypedCoordinateInvariantViolation("action program violates fixed scalar type")
    return tuple(sorted(atoms, key=lambda item: item.atom_id))


def _action_labels(expression_ids: tuple[str, ...], atoms, table: FrozenTypedCoordinateValueTableV2) -> dict[str, tuple[bool, ...]]:
    if expression_ids and not atoms:
        return {row.ground_row_id: (True,) for row in table.action_rows}
    labels = {}
    for row in table.action_rows:
        values = []
        for atom in atoms:
            if atom.kind.value == "UNIVERSAL_TRUE":
                values.append(True)
            else:
                index = table.action_expression_ids.index(atom.source_expression_id)
                raw = row.values[index]
                values.append(raw if atom.kind.value == "BOOLEAN_IDENTITY" else Fraction(raw) <= atom.threshold)
        labels[row.ground_row_id] = tuple(values)
    return labels


def _action_partition_id(labels: Mapping[str, tuple[bool, ...]]) -> str:
    groups: dict[tuple[bool, ...], list[str]] = {}
    for ground_row_id, label in labels.items():
        groups.setdefault(label, []).append(ground_row_id)
    payload = {
        "classes": [
            {"label": list(label), "ground_row_ids": sorted(rows)}
            for label, rows in sorted(groups.items())
        ]
    }
    return _content_id("action_partition", payload)


def _candidate_partition(log: ObservationLogManifestV1, selected_state_ids: tuple[str, ...], table: FrozenTypedCoordinateValueTableV2):
    indexes = tuple(table.state_expression_ids.index(item) for item in selected_state_ids)
    value_by_state = {row.state_id: tuple(row.values[index] for index in indexes) for row in table.state_rows}
    groups: dict[tuple[str, tuple[int, ...]], list[str]] = {}
    for state in log.states:
        values = value_by_state[state.state_id] if state.planning_kind is PlanningKind.ACTIVE else ()
        groups.setdefault((state.planning_kind.value, values), []).append(state.state_id)
    cells = []
    for (kind, values), members in groups.items():
        payload = {"planning_kind": kind, "coordinate_values": list(values), "member_state_ids": sorted(members)}
        cells.append((_content_id("cell", payload), kind, values, tuple(sorted(members))))
    cells.sort(key=lambda item: item[0])
    partition_payload = {"cells": [{"cell_id": cell_id, "planning_kind": kind, "coordinate_values": list(values), "member_state_ids": list(members)} for cell_id, kind, values, members in cells]}
    partition_id = _content_id("partition", partition_payload)
    return partition_id, tuple(cells), {state_id: cell_id for cell_id, _, _, members in cells for state_id in members}


def _signature_id(observation, cell_by_state: dict[str, str], reward_names: tuple[str, ...]) -> str:
    rewards = dict(observation.reward_features)
    if observation.terminal:
        outcome = "TERMINAL_FAILURE" if observation.failure else "TERMINAL_SUCCESS"
        destination = None
    else:
        outcome = "CONTINUATION"
        destination = cell_by_state[observation.successor.reference] if observation.successor.kind is SuccessorKind.REGISTERED_STATE else "EXTERNAL_STATE"
    payload = {"reward_features": [{"name": name, "value": _fraction_document(rewards.get(name, Fraction(0)))} for name in reward_names], "failure": observation.failure, "terminal": observation.terminal, "outcome": outcome, "destination": destination}
    return _content_id("signature", payload)


def _entry_key_by_row(log, cells, cell_by_state, labels):
    action_by_row = {action.ground_row_id: action for catalogue in log.action_catalogues for action in catalogue.actions}
    return {row_id: (cell_by_state[action.state_id], labels[row_id]) for row_id, action in action_by_row.items()}


def _null_conflict_pairs(log, table, reward_names):
    _, cells, cell_by_state = _candidate_partition(log, (), table)
    labels = _action_labels((), _compile_action_atoms((), table), table)
    key_by_row = _entry_key_by_row(log, cells, cell_by_state, labels)
    signature_by_row = {item.ground_row_id: _signature_id(item, cell_by_state, reward_names) for item in log.observations}
    conflicts = []
    for left, right in combinations(sorted(signature_by_row), 2):
        if key_by_row[left] == key_by_row[right] and signature_by_row[left] != signature_by_row[right]:
            conflicts.append((left, right))
    return tuple(conflicts)

def _audit_candidate(
    candidate_index: int,
    state_mask: int,
    action_mask: int,
    log: ObservationLogManifestV1,
    profile: DeterministicObservationProfileV1,
    registry: ObservedDSLRegistryBindingV1,
    table: FrozenTypedCoordinateValueTableV2,
    null_conflicts: tuple[tuple[str, str], ...],
) -> ObservedCandidateV1:
    state_ids = _selected_ids(registry.state_programs, state_mask)
    action_ids = _selected_ids(registry.action_programs, action_mask)
    atoms = _compile_action_atoms(action_ids, table)
    labels = _action_labels(action_ids, atoms, table)
    partition_id, cells, cell_by_state = _candidate_partition(log, state_ids, table)
    key_by_row = _entry_key_by_row(log, cells, cell_by_state, labels)
    action_by_row = {action.ground_row_id: action for catalogue in log.action_catalogues for action in catalogue.actions}
    catalogue_by_state = {item.state_id: item for item in log.action_catalogues}
    availability_violations = 0
    for _, kind, _, members in cells:
        if kind != PlanningKind.ACTIVE.value:
            continue
        label_sets = {
            tuple(sorted({labels[action.ground_row_id] for action in catalogue_by_state[state_id].actions}))
            for state_id in members
        }
        if len(label_sets) != 1:
            availability_violations += 1
    reward_names = tuple(item.name for item in profile.reward_feature_caps)
    observation_by_row = {item.ground_row_id: item for item in log.observations}
    signature_by_row = {row_id: _signature_id(item, cell_by_state, reward_names) for row_id, item in observation_by_row.items()}
    rows_by_entry: dict[tuple[str, tuple[bool, ...]], list[str]] = {}
    for row_id, key in key_by_row.items():
        rows_by_entry.setdefault(key, []).append(row_id)
    evidence: list[ObservedEntryEvidenceV1] = []
    point_rows = 0
    partial_rows = 0
    equal_pairs = 0
    contradictions = 0
    nontrivial_points = 0
    for (cell_id, label), support in rows_by_entry.items():
        support_tuple = tuple(sorted(support))
        observed = tuple(sorted(set(support_tuple) & set(observation_by_row)))
        missing = tuple(sorted(set(support_tuple) - set(observation_by_row)))
        signatures = tuple(sorted({signature_by_row[row_id] for row_id in observed}))
        classification = (
            CandidateEntryClass.OBSERVED_CONTRADICTION
            if len(signatures) > 1
            else CandidateEntryClass.UNOBSERVED_UNKNOWN
            if not observed
            else CandidateEntryClass.PARTIAL_UNKNOWN
            if missing
            else CandidateEntryClass.POINT_IDENTIFIED
        )
        evidence.append(ObservedEntryEvidenceV1(cell_id, label, support_tuple, observed, missing, signatures, classification))
        signature_counts: dict[str, int] = {}
        for row_id in observed:
            signature_counts[signature_by_row[row_id]] = signature_counts.get(signature_by_row[row_id], 0) + 1
        equal_pairs += sum(count * (count - 1) // 2 for count in signature_counts.values())
        if classification is CandidateEntryClass.POINT_IDENTIFIED:
            point_rows += len(support_tuple)
            if len(support_tuple) >= 2:
                nontrivial_points += 1
        elif classification is CandidateEntryClass.PARTIAL_UNKNOWN:
            partial_rows += len(support_tuple)
        elif classification is CandidateEntryClass.OBSERVED_CONTRADICTION:
            contradictions += 1
    evidence_tuple = tuple(sorted(evidence, key=lambda item: item.entry_id))
    separated = sum(key_by_row[left] != key_by_row[right] for left, right in null_conflicts)
    active_cells = sum(kind == PlanningKind.ACTIVE.value for _, kind, _, _ in cells)
    rejection_codes = []
    if action_ids and not atoms:
        rejection_codes.append("NONSEPARATING_SELECTED_ACTION_PROGRAM")
    if availability_violations:
        rejection_codes.append("SEMANTIC_LABEL_AVAILABILITY_VIOLATION")
    if contradictions:
        rejection_codes.append("OBSERVED_CONTRADICTION")
    if equal_pairs == 0:
        rejection_codes.append("NO_NONTRIVIAL_OBSERVED_EQUALITY_WITNESS")
    if separated == 0:
        rejection_codes.append("NO_NULL_CONFLICT_SEPARATION")
    if nontrivial_points == 0:
        rejection_codes.append("NO_NONTRIVIAL_POINT_IDENTIFIED_ENTRY")
    if len(cells) >= len(log.states) or len(evidence_tuple) >= len(action_by_row):
        rejection_codes.append("NO_STRICT_STATE_ACTION_COMPRESSION")
    rejection_tuple = tuple(sorted(set(rejection_codes)))
    return ObservedCandidateV1(
        candidate_index=candidate_index,
        state_mask=state_mask,
        action_mask=action_mask,
        state_expression_ids=state_ids,
        action_expression_ids=action_ids,
        action_atom_ids=tuple(item.atom_id for item in atoms),
        partition_id=partition_id,
        active_cell_count=active_cells,
        total_cell_count=len(cells),
        abstract_entry_count=len(evidence_tuple),
        action_partition_id=_action_partition_id(labels),
        point_identified_registered_rows=point_rows,
        observed_equal_alias_pair_count=equal_pairs,
        partial_unknown_registered_rows=partial_rows,
        separated_null_conflict_pair_count=separated,
        nontrivial_point_entry_count=nontrivial_points,
        availability_violation_count=availability_violations,
        contradiction_entry_count=contradictions,
        entry_evidence=evidence_tuple,
        rejection_codes=rejection_tuple,
        admissible=not rejection_tuple,
    )


def _ast_complexity(program: ObservedGeneratedExpressionV1) -> tuple[Any, ...]:
    return (program.node_count, program.depth, _OPERATION_ORDER.index(program.operation), tuple(_ast_complexity(item) for item in program.arguments), -1 if program.literal is None else program.literal, program.expression_id)


def _candidate_selection_key(candidate: ObservedCandidateV1, registry: ObservedDSLRegistryBindingV1) -> tuple[Any, ...]:
    programs_by_id = {item.expression_id: item for item in (*registry.state_programs, *registry.action_programs)}
    selected = tuple(programs_by_id[item] for item in (*candidate.state_expression_ids, *candidate.action_expression_ids))
    return (
        -candidate.point_identified_registered_rows,
        -candidate.observed_equal_alias_pair_count,
        candidate.partial_unknown_registered_rows,
        candidate.abstract_entry_count,
        candidate.active_cell_count,
        candidate.total_cell_count,
        len(candidate.state_expression_ids),
        len(candidate.action_expression_ids),
        sum(item.node_count for item in selected),
        max((item.depth for item in selected), default=0),
        tuple(_ast_complexity(item) for item in selected),
        candidate.state_expression_ids,
        candidate.action_expression_ids,
        candidate.partition_id,
        candidate.action_partition_id,
        candidate.candidate_id,
    )


@dataclass(frozen=True, slots=True)
class ObservedCandidateTraceV1:
    synthesis_spec_id: str
    value_table_id: str
    required_candidate_count: int
    evaluated_candidate_count: int
    candidates: tuple[ObservedCandidateV1, ...]
    selected_candidate_id: str
    null_candidate_id: str
    production_cap_exhausted: bool = False

    def __post_init__(self) -> None:
        _cid(self.synthesis_spec_id, "trace synthesis spec")
        _cid(self.value_table_id, "trace value table")
        if self.required_candidate_count != REQUIRED_CANDIDATE_COUNT or self.evaluated_candidate_count != REQUIRED_CANDIDATE_COUNT or self.production_cap_exhausted is not False:
            raise ObservedTypedCoordinateInvariantViolation("production trace did not evaluate exactly 4096 candidates")
        _exact_tuple(self.candidates, ObservedCandidateV1, "candidate trace")
        if len(self.candidates) != REQUIRED_CANDIDATE_COUNT or tuple(item.candidate_index for item in self.candidates) != tuple(range(1, REQUIRED_CANDIDATE_COUNT + 1)):
            raise ObservedTypedCoordinateInvariantViolation("candidate trace sequence/coverage mismatch")
        ids = tuple(item.candidate_id for item in self.candidates)
        if len(set(ids)) != len(ids):
            raise ObservedTypedCoordinateInvariantViolation("duplicate candidate artifact")
        _cid(self.selected_candidate_id, "selected candidate")
        _cid(self.null_candidate_id, "null candidate")
        if self.selected_candidate_id not in ids or self.null_candidate_id != self.candidates[0].candidate_id or self.candidates[0].state_mask != 0 or self.candidates[0].action_mask != 0:
            raise ObservedTypedCoordinateInvariantViolation("trace selected/null candidate binding mismatch")

    def _payload(self) -> dict[str, Any]:
        return {"schema": "acfqp.observed_coordinate_candidate_trace.v1", "schema_version": SCHEMA_VERSION, "synthesis_spec_id": self.synthesis_spec_id, "value_table_id": self.value_table_id, "required_candidate_count": self.required_candidate_count, "evaluated_candidate_count": self.evaluated_candidate_count, "candidates": [item.to_document() for item in self.candidates], "selected_candidate_id": self.selected_candidate_id, "null_candidate_id": self.null_candidate_id, "production_cap_exhausted": self.production_cap_exhausted}

    @property
    def trace_id(self) -> str:
        return _content_id("trace", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "trace_id": self.trace_id}


@dataclass(frozen=True, slots=True)
class ObservedPredicateAtomV1:
    expression_id: str
    threshold: Fraction

    def __post_init__(self) -> None:
        _cid(self.expression_id, "predicate expression")
        if type(self.threshold) not in (int, Fraction):
            raise ObservedTypedCoordinateInvariantViolation("predicate threshold must be exact")
        object.__setattr__(self, "threshold", Fraction(self.threshold))

    def _payload(self) -> dict[str, Any]:
        return {"schema": "acfqp.observed_coordinate_predicate_atom.v1", "expression_id": self.expression_id, "operator": "<=", "threshold": _fraction_document(self.threshold)}

    @property
    def atom_id(self) -> str:
        return _content_id("atom", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atom_id": self.atom_id}


@dataclass(frozen=True, slots=True)
class ObservedPredicateTreeV1:
    selected_candidate_id: str
    partition_id: str
    state_atoms: tuple[ObservedPredicateAtomV1, ...]
    action_atom_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _cid(self.selected_candidate_id, "predicate tree candidate")
        _cid(self.partition_id, "predicate tree partition")
        _exact_tuple(self.state_atoms, ObservedPredicateAtomV1, "predicate tree state atoms")
        if tuple(item.atom_id for item in self.state_atoms) != tuple(sorted({item.atom_id for item in self.state_atoms})):
            raise ObservedTypedCoordinateInvariantViolation("predicate state atoms must be unique sorted")
        if type(self.action_atom_ids) is not tuple or self.action_atom_ids != tuple(sorted(set(self.action_atom_ids))):
            raise ObservedTypedCoordinateInvariantViolation("predicate action atom IDs must be unique sorted")
        for item in self.action_atom_ids:
            _cid(item, "predicate action atom")

    def _payload(self) -> dict[str, Any]:
        return {"schema": "acfqp.observed_coordinate_predicate_tree.v1", "selected_candidate_id": self.selected_candidate_id, "partition_id": self.partition_id, "state_atoms": [item.to_document() for item in self.state_atoms], "action_atom_ids": list(self.action_atom_ids), "threshold_rule": THRESHOLD_RULE}

    @property
    def tree_id(self) -> str:
        return _content_id("tree", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "tree_id": self.tree_id}


def _predicate_tree(log: ObservationLogManifestV1, selected: ObservedCandidateV1, table: FrozenTypedCoordinateValueTableV2) -> ObservedPredicateTreeV1:
    atoms = []
    active_ids = {item.state_id for item in log.states if item.planning_kind is PlanningKind.ACTIVE}
    for expression_id in selected.state_expression_ids:
        index = table.state_expression_ids.index(expression_id)
        distinct = tuple(sorted({row.values[index] for row in table.state_rows if row.state_id in active_ids}))
        atoms.extend(ObservedPredicateAtomV1(expression_id, Fraction(left + right, 2)) for left, right in zip(distinct, distinct[1:]))
    return ObservedPredicateTreeV1(selected.candidate_id, selected.partition_id, tuple(sorted(atoms, key=lambda item: item.atom_id)), selected.action_atom_ids)


def _compile_trace(log, profile, registry, table, spec):
    if spec.required_candidate_count > spec.candidate_cap:
        raise ObservedTypedCoordinateInvariantViolation("CANDIDATE_CAP_EXHAUSTED")
    reward_names = tuple(item.name for item in profile.reward_feature_caps)
    null_conflicts = _null_conflict_pairs(log, table, reward_names)
    if not null_conflicts:
        raise ObservedTypedCoordinateInvariantViolation("INSUFFICIENT_OBSERVED_DISTINCTIONS")
    candidates = []
    index = 0
    for state_mask in range(2**STATE_PROGRAM_COUNT):
        for action_mask in range(2**ACTION_PROGRAM_COUNT):
            index += 1
            candidates.append(_audit_candidate(index, state_mask, action_mask, log, profile, registry, table, null_conflicts))
    candidates_tuple = tuple(candidates)
    admissible = tuple(item for item in candidates_tuple if item.admissible)
    if not admissible:
        raise ObservedTypedCoordinateInvariantViolation("NO_OBSERVATION_CONSISTENT_TYPED_CANDIDATE")
    selected = min(admissible, key=lambda item: _candidate_selection_key(item, registry))
    trace = ObservedCandidateTraceV1(spec.spec_id, table.value_table_id, REQUIRED_CANDIDATE_COUNT, len(candidates_tuple), candidates_tuple, selected.candidate_id, candidates_tuple[0].candidate_id)
    return trace, selected

@dataclass(frozen=True, slots=True)
class ObservationSynthesisTelemetryV1:
    registered_state_count: int
    registered_ground_row_count: int
    distinct_observed_row_count: int
    missing_ground_row_count: int
    state_expression_evaluations: int
    action_expression_evaluations: int
    evaluated_candidate_count: int
    complete_catalogue_label_set_comparisons: int
    observed_signature_comparisons: int
    missing_rows_status_inspections: int
    predicate_atom_count: int
    selected_point_rows: int
    selected_partial_rows: int
    selected_entry_count: int
    selected_active_cell_count: int
    selected_total_cell_count: int
    selected_unknown_fraction_multiset: tuple[Fraction, ...]
    new_environment_interactions_during_synthesis: int = 0
    new_generative_oracle_samples_during_synthesis: int = 0
    new_exact_kernel_queries_during_synthesis: int = 0
    new_synthetic_model_rollouts_during_synthesis: int = 0
    query_inputs_during_synthesis: int = 0

    def __post_init__(self) -> None:
        integer_fields = tuple(field for field in self.__dataclass_fields__ if field != "selected_unknown_fraction_multiset")
        if any(type(getattr(self, field)) is not int or getattr(self, field) < 0 for field in integer_fields):
            raise ObservedTypedCoordinateInvariantViolation("telemetry counters must be nonnegative exact integers")
        if type(self.selected_unknown_fraction_multiset) is not tuple or any(type(value) not in (int, Fraction) for value in self.selected_unknown_fraction_multiset):
            raise ObservedTypedCoordinateInvariantViolation("unknown-fraction telemetry must be exact")
        normalized = tuple(sorted(Fraction(value) for value in self.selected_unknown_fraction_multiset))
        if any(not 0 <= value <= 1 for value in normalized):
            raise ObservedTypedCoordinateInvariantViolation("unknown fraction outside [0,1]")
        object.__setattr__(self, "selected_unknown_fraction_multiset", normalized)
        if any(getattr(self, field) != 0 for field in ("new_environment_interactions_during_synthesis", "new_generative_oracle_samples_during_synthesis", "new_exact_kernel_queries_during_synthesis", "new_synthetic_model_rollouts_during_synthesis", "query_inputs_during_synthesis")):
            raise ObservedTypedCoordinateInvariantViolation("synthesis used a forbidden acquisition/query channel")

    def _payload(self) -> dict[str, Any]:
        return {"schema": "acfqp.observation_synthesis_telemetry.v1", **{field: getattr(self, field) for field in self.__dataclass_fields__ if field != "selected_unknown_fraction_multiset"}, "selected_unknown_fraction_multiset": [_fraction_document(value) for value in self.selected_unknown_fraction_multiset], "sample_efficiency_gate_status": "NOT_RUN", "sample_efficiency_gate_blocks_mainline": False}

    @property
    def telemetry_id(self) -> str:
        return _content_id("telemetry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "telemetry_id": self.telemetry_id}


@dataclass(frozen=True, slots=True)
class ObservedTypedPartialRAPMCertificateV1:
    observation_authority_id: str
    acquisition_manifest_id: str
    observation_log_id: str
    semantics_profile_id: str
    evidence_ledger_id: str
    structural_binding_id: str
    dsl_registry_id: str
    value_table_id: str
    synthesis_spec_id: str
    candidate_trace_id: str
    selected_candidate_id: str
    predicate_tree_id: str
    coordinate_proposal_id: str
    partial_model_id: str
    partial_build_result_id: str
    telemetry_id: str
    evaluated_candidate_count: int = REQUIRED_CANDIDATE_COUNT
    status: str = SUCCESS_STATUS
    claim_kind: str = "OBSERVATION_CONSISTENT_QUERY_NEUTRAL_TYPED_PARTIAL_RAPM"
    transport_authority_claimed: bool = False
    observer_honesty_claimed: bool = False
    exact_quotient_claimed: bool = False
    plan_certificate_claimed: bool = False
    sample_efficiency_claimed: bool = False

    def __post_init__(self) -> None:
        for field in tuple(self.__dataclass_fields__)[:16]:
            _cid(getattr(self, field), field)
        if self.evaluated_candidate_count != REQUIRED_CANDIDATE_COUNT or self.status != SUCCESS_STATUS or self.claim_kind != "OBSERVATION_CONSISTENT_QUERY_NEUTRAL_TYPED_PARTIAL_RAPM":
            raise ObservedTypedCoordinateInvariantViolation("certificate status/count/claim substitution")
        if any(getattr(self, field) is not False for field in ("transport_authority_claimed", "observer_honesty_claimed", "exact_quotient_claimed", "plan_certificate_claimed", "sample_efficiency_claimed")):
            raise ObservedTypedCoordinateInvariantViolation("certificate crosses its explicit claim boundary")

    def _payload(self) -> dict[str, Any]:
        return {"schema": "acfqp.observed_typed_partial_rapm_certificate.v1", "schema_version": SCHEMA_VERSION, **{field: getattr(self, field) for field in self.__dataclass_fields__}}

    @property
    def certificate_id(self) -> str:
        return _content_id("certificate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "certificate_id": self.certificate_id}


@dataclass(frozen=True, slots=True)
class ObservedTypedPartialRAPMResultV1:
    structural_binding: ObservedStructuralPrimitiveRegistryBindingV1
    dsl_registry: ObservedDSLRegistryBindingV1
    value_table: FrozenTypedCoordinateValueTableV2
    synthesis_spec: ObservedSynthesisSpecV1
    candidate_trace: ObservedCandidateTraceV1
    selected_candidate: ObservedCandidateV1
    predicate_tree: ObservedPredicateTreeV1
    coordinate_proposal: FrozenTypedCoordinateProposalV2
    partial_build_result: ObservationPartialRAPMBuildV1
    telemetry: ObservationSynthesisTelemetryV1
    certificate: ObservedTypedPartialRAPMCertificateV1
    status: str = SUCCESS_STATUS

    def __post_init__(self) -> None:
        expected_types = (
            (self.structural_binding, ObservedStructuralPrimitiveRegistryBindingV1),
            (self.dsl_registry, ObservedDSLRegistryBindingV1),
            (self.value_table, FrozenTypedCoordinateValueTableV2),
            (self.synthesis_spec, ObservedSynthesisSpecV1),
            (self.candidate_trace, ObservedCandidateTraceV1),
            (self.selected_candidate, ObservedCandidateV1),
            (self.predicate_tree, ObservedPredicateTreeV1),
            (self.coordinate_proposal, FrozenTypedCoordinateProposalV2),
            (self.partial_build_result, ObservationPartialRAPMBuildV1),
            (self.telemetry, ObservationSynthesisTelemetryV1),
            (self.certificate, ObservedTypedPartialRAPMCertificateV1),
        )
        if any(type(value) is not expected for value, expected in expected_types):
            raise ObservedTypedCoordinateInvariantViolation("result rejects nested substitutions before canonical access")
        if self.status != SUCCESS_STATUS or self.candidate_trace.selected_candidate_id != self.selected_candidate.candidate_id or self.coordinate_proposal.selected_candidate_id != self.selected_candidate.candidate_id or self.coordinate_proposal.candidate_trace_id != self.candidate_trace.trace_id or self.partial_build_result.coordinate_proposal_id != self.coordinate_proposal.proposal_id or self.certificate.selected_candidate_id != self.selected_candidate.candidate_id or self.certificate.partial_model_id != self.partial_build_result.model.model_id:
            raise ObservedTypedCoordinateInvariantViolation("result artifact identity chain mismatch")

    def _payload(self) -> dict[str, Any]:
        return {"schema": "acfqp.observed_typed_partial_rapm_result.v1", "schema_version": SCHEMA_VERSION, "status": self.status, "structural_binding": self.structural_binding.to_document(), "dsl_registry": self.dsl_registry.to_document(), "value_table": self.value_table.to_document(), "synthesis_spec": self.synthesis_spec.to_document(), "candidate_trace": self.candidate_trace.to_document(), "selected_candidate": self.selected_candidate.to_document(), "predicate_tree": self.predicate_tree.to_document(), "coordinate_proposal": self.coordinate_proposal.to_document(), "partial_build_result": self.partial_build_result.to_document(), "telemetry": self.telemetry.to_document(), "certificate": self.certificate.to_document()}

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _telemetry(log, table, trace, selected, tree):
    label_comparisons = 0
    signature_comparisons = 0
    for candidate in trace.candidates:
        _, cells, _ = _candidate_partition(log, candidate.state_expression_ids, table)
        label_comparisons += sum(max(len(members) - 1, 0) for _, kind, _, members in cells if kind == PlanningKind.ACTIVE.value)
        signature_comparisons += sum(len(entry.observed_ground_row_ids) * (len(entry.observed_ground_row_ids) - 1) // 2 for entry in candidate.entry_evidence)
    unknown = tuple(Fraction(len(entry.missing_ground_row_ids), len(entry.support_ground_row_ids)) for entry in selected.entry_evidence)
    return ObservationSynthesisTelemetryV1(
        len(log.states),
        len(table.action_rows),
        len(log.observations),
        len(table.action_rows) - len(log.observations),
        len(log.states) * len(table.state_expression_ids),
        len(table.action_rows) * len(table.action_expression_ids),
        len(trace.candidates),
        label_comparisons,
        signature_comparisons,
        (len(table.action_rows) - len(log.observations)) * len(trace.candidates),
        len(tree.state_atoms) + len(tree.action_atom_ids),
        selected.point_identified_registered_rows,
        selected.partial_unknown_registered_rows,
        selected.abstract_entry_count,
        selected.active_cell_count,
        selected.total_cell_count,
        unknown,
    )


def _implementation_digest(functions: tuple[Any, ...]) -> str:
    return hashlib.sha256(
        "\n\x00\n".join(inspect.getsource(function) for function in functions).encode(
            "utf-8"
        )
    ).hexdigest()


def _validate_implementation_authority() -> None:
    checks = (
        (
            "registry",
            (_primitive, _operator, _enumerate_programs, _structural_binding, _dsl_registry),
            IMPLEMENTATION_CONTRACT_SHA256,
        ),
        (
            "evaluator",
            (_eval_expression, _build_value_table),
            OBSERVATION_EVALUATOR_SHA256,
        ),
        (
            "compiler",
            (
                _compile_action_atoms,
                _action_labels,
                _action_partition_id,
                _candidate_partition,
                _predicate_tree,
            ),
            OBSERVATION_COMPILER_SHA256,
        ),
        (
            "selector",
            (
                _signature_id,
                _entry_key_by_row,
                _null_conflict_pairs,
                _audit_candidate,
                _ast_complexity,
                _candidate_selection_key,
                _compile_trace,
            ),
            OBSERVATION_SELECTOR_SHA256,
        ),
    )
    for label, functions, expected in checks:
        if _implementation_digest(functions) != expected:
            raise ObservedTypedCoordinateInvariantViolation(
                f"runtime {label} implementation differs from frozen authority"
            )


def synthesize_observed_lmb_partial_rapm_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
) -> ObservedTypedPartialRAPMResultV1:
    """Evaluate all 4096 fixed-DSL subsets from exactly three source inputs."""
    if type(observation_log) is not ObservationLogManifestV1:
        raise ObservedTypedCoordinateInvariantViolation("synthesizer rejects duck observation logs")
    if type(semantics_profile) is not DeterministicObservationProfileV1:
        raise ObservedTypedCoordinateInvariantViolation("synthesizer rejects duck semantics profiles")
    if type(observation_authority) is not PreregisteredObservationAuthorityV1:
        raise ObservedTypedCoordinateInvariantViolation("synthesizer rejects duck observation authorities")
    _validate_implementation_authority()
    try:
        validate_preregistered_observation_source_graph_v1(observation_log, semantics_profile, observation_authority)
    except ObservationPartialRAPMInvariantViolation as error:
        raise ObservedTypedCoordinateInvariantViolation(str(error)) from error
    row_count = sum(len(item.actions) for item in observation_log.action_catalogues)
    if (len(observation_log.states), row_count, len(observation_log.observations)) != (8, 11, 7):
        raise ObservedTypedCoordinateInvariantViolation("production source graph is not the frozen 8/11/7 control")
    structural = _structural_binding(observation_authority, observation_log)
    registry = _dsl_registry()
    table = _build_value_table(observation_log, semantics_profile, observation_authority, structural, registry)
    spec = ObservedSynthesisSpecV1(observation_authority.authority_id, structural.binding_id, registry.registry_id)
    trace, selected = _compile_trace(observation_log, semantics_profile, registry, table, spec)
    tree = _predicate_tree(observation_log, selected, table)
    atoms = _compile_action_atoms(selected.action_expression_ids, table)
    if not atoms:
        raise ObservedTypedCoordinateInvariantViolation("selected candidate lacks compiled action atoms")
    proposal = FrozenTypedCoordinateProposalV2(
        selected.state_expression_ids,
        selected.action_expression_ids,
        atoms,
        registry.registry_id,
        structural.binding_id,
        table.value_table_id,
        spec.spec_id,
        selected.candidate_id,
        trace.trace_id,
        observation_log.log_id,
        semantics_profile.profile_id,
        observation_authority.authority_id,
        observation_authority.acquisition_manifest.manifest_id,
    )
    build = build_observation_partial_rapm_from_typed_values_v2(observation_log, proposal, table, semantics_profile, observation_authority)
    if verify_observation_partial_rapm_from_typed_values_v2(observation_log, proposal, table, semantics_profile, observation_authority, build):
        raise ObservedTypedCoordinateInvariantViolation("typed V0-042 builder replay mismatch")
    telemetry = _telemetry(observation_log, table, trace, selected, tree)
    certificate = ObservedTypedPartialRAPMCertificateV1(
        observation_authority.authority_id,
        observation_authority.acquisition_manifest.manifest_id,
        observation_log.log_id,
        semantics_profile.profile_id,
        observation_log.evidence_ledger.ledger_id,
        structural.binding_id,
        registry.registry_id,
        table.value_table_id,
        spec.spec_id,
        trace.trace_id,
        selected.candidate_id,
        tree.tree_id,
        proposal.proposal_id,
        build.model.model_id,
        build.result_id,
        telemetry.telemetry_id,
    )
    return ObservedTypedPartialRAPMResultV1(structural, registry, table, spec, trace, selected, tree, proposal, build, telemetry, certificate)

@dataclass(frozen=True, slots=True)
class ObservedSynthesisCapControlOutcomeV1:
    observation_authority_id: str
    observation_log_id: str
    candidate_cap: int
    required_candidate_count: int = REQUIRED_CANDIDATE_COUNT
    evaluated_candidate_count: int = 0
    status: str = "CANDIDATE_CAP_EXHAUSTED"
    production_certificate_published: bool = False
    model_id: None = None
    certificate_id: None = None

    def __post_init__(self) -> None:
        _cid(self.observation_authority_id, "cap-control authority")
        _cid(self.observation_log_id, "cap-control log")
        if type(self.candidate_cap) is not int or not 1 <= self.candidate_cap < PRODUCTION_CANDIDATE_CAP:
            raise ObservedTypedCoordinateInvariantViolation("cap-control cap must be below 4096")
        if self.required_candidate_count != REQUIRED_CANDIDATE_COUNT or self.evaluated_candidate_count != 0 or self.status != "CANDIDATE_CAP_EXHAUSTED" or self.production_certificate_published is not False or self.model_id is not None or self.certificate_id is not None:
            raise ObservedTypedCoordinateInvariantViolation("cap-control outcome overclaims production work")

    def _payload(self) -> dict[str, Any]:
        return {"schema": "acfqp.observed_synthesis_cap_control_outcome.v1", "observation_authority_id": self.observation_authority_id, "observation_log_id": self.observation_log_id, "candidate_cap": self.candidate_cap, "required_candidate_count": self.required_candidate_count, "evaluated_candidate_count": self.evaluated_candidate_count, "status": self.status, "production_certificate_published": self.production_certificate_published, "model_id": self.model_id, "certificate_id": self.certificate_id}

    @property
    def outcome_id(self) -> str:
        return _content_id("control", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "outcome_id": self.outcome_id}


def synthesize_observed_lmb_partial_rapm_cap_control_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    *,
    candidate_cap: int,
) -> ObservedSynthesisCapControlOutcomeV1:
    """Separately named nonproduction control; it cannot publish a model."""
    if type(observation_log) is not ObservationLogManifestV1:
        raise ObservedTypedCoordinateInvariantViolation("cap control rejects duck logs")
    if type(semantics_profile) is not DeterministicObservationProfileV1:
        raise ObservedTypedCoordinateInvariantViolation("cap control rejects duck profiles")
    if type(observation_authority) is not PreregisteredObservationAuthorityV1:
        raise ObservedTypedCoordinateInvariantViolation("cap control rejects duck authorities")
    _validate_implementation_authority()
    try:
        validate_preregistered_observation_source_graph_v1(
            observation_log, semantics_profile, observation_authority
        )
    except ObservationPartialRAPMInvariantViolation as error:
        raise ObservedTypedCoordinateInvariantViolation(str(error)) from error
    return ObservedSynthesisCapControlOutcomeV1(
        observation_authority.authority_id,
        observation_log.log_id,
        candidate_cap,
    )



def verify_observed_lmb_partial_rapm_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    claimed_result: ObservedTypedPartialRAPMResultV1,
) -> tuple[str, ...]:
    """Retained-runtime replay of source, all candidates, selection, and model."""
    if type(claimed_result) is not ObservedTypedPartialRAPMResultV1:
        raise ObservedTypedCoordinateInvariantViolation("verifier rejects duck result artifacts")
    expected = synthesize_observed_lmb_partial_rapm_v1(observation_log, semantics_profile, observation_authority)
    _validate_claimed_runtime_shape_v1(claimed_result, expected, "claimed result")
    failures = []
    if claimed_result.candidate_trace.trace_id != expected.candidate_trace.trace_id:
        failures.append("CANDIDATE_TRACE_RECONSTRUCTION_MISMATCH")
    if claimed_result.coordinate_proposal.proposal_id != expected.coordinate_proposal.proposal_id:
        failures.append("COORDINATE_PROPOSAL_RECONSTRUCTION_MISMATCH")
    if claimed_result.partial_build_result.model.model_id != expected.partial_build_result.model.model_id:
        failures.append("PARTIAL_MODEL_RECONSTRUCTION_MISMATCH")
    if claimed_result.to_document() != expected.to_document():
        failures.append("RESULT_RECONSTRUCTION_MISMATCH")
    return tuple(failures)


def _validate_claimed_runtime_shape_v1(
    claimed: Any,
    expected: Any,
    path: str,
) -> None:
    """Compare recursive runtime types without touching derived properties."""

    if type(claimed) is not type(expected):
        raise ObservedTypedCoordinateInvariantViolation(
            f"{path} contains a nested runtime-type substitution"
        )
    if type(expected) is tuple:
        if len(claimed) != len(expected):
            raise ObservedTypedCoordinateInvariantViolation(
                f"{path} tuple shape differs from retained replay"
            )
        for index, (claimed_item, expected_item) in enumerate(zip(claimed, expected)):
            _validate_claimed_runtime_shape_v1(
                claimed_item, expected_item, f"{path}[{index}]"
            )
        return
    if is_dataclass(expected):
        for field in fields(type(expected)):
            _validate_claimed_runtime_shape_v1(
                object.__getattribute__(claimed, field.name),
                object.__getattribute__(expected, field.name),
                f"{path}.{field.name}",
            )


__all__ = [
    "ACTION_PROGRAM_COUNT",
    "CandidateEntryClass",
    "ObservedCandidateTraceV1",
    "ObservedCandidateV1",
    "ObservedDSLRegistryBindingV1",
    "ObservedEntryEvidenceV1",
    "ObservedGeneratedExpressionV1",
    "ObservedPredicateAtomV1",
    "ObservedPredicateTreeV1",
    "ObservedStructuralPrimitiveRegistryBindingV1",
    "ObservedSynthesisCapControlOutcomeV1",
    "ObservedSynthesisSpecV1",
    "ObservedTypedCoordinateInvariantViolation",
    "ObservedTypedPartialRAPMCertificateV1",
    "ObservedTypedPartialRAPMResultV1",
    "ObservationSynthesisTelemetryV1",
    "PRODUCTION_CANDIDATE_CAP",
    "REQUIRED_CANDIDATE_COUNT",
    "STATE_PROGRAM_COUNT",
    "SUCCESS_STATUS",
    "synthesize_observed_lmb_partial_rapm_cap_control_v1",
    "synthesize_observed_lmb_partial_rapm_v1",
    "verify_observed_lmb_partial_rapm_v1",
]
