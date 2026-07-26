"""Observation-only compositional coordinate-program closure for LMB.

This module advances the V0-045 control by generating the coordinate catalogue
bottom-up from the frozen primitive/operator vocabulary instead of accepting a
handwritten list of coordinate programs.  Its production producer still has
exactly three inputs: a preregistered observation log, its deterministic
semantics profile, and the matching observation authority.

The positive claim is deliberately narrow.  The procedure automatically
composes and semantically deduplicates programs *within* a frozen,
human-specified typed vocabulary, then derives an observation-consistent
partial RAPM.  It does not invent primitives or operators, symbolize raw
sensory input, learn unobserved dynamics, establish statistical or held-out
generalization, certify a plan, or claim sample savings.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from fractions import Fraction
import hashlib
import inspect
from itertools import combinations, product
from typing import Any, Mapping

import acfqp.observed_typed_coordinate_synthesis_v1 as fixed_dsl
from acfqp.observation_partial_rapm_v1 import (
    CanonicalGroundActionV1,
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
    TypedActionAtomKind,
    build_observation_partial_rapm_from_typed_values_v2,
    validate_preregistered_observation_source_graph_v1,
    verify_observation_partial_rapm_from_typed_values_v2,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "lmb_observed_program_closure_partial_rapm_v0"
SUCCESS_STATUS = "OBSERVATION_CONSISTENT_PROGRAM_CLOSURE_PARTIAL_RAPM"
DSL_PROFILE = "lmb_structural_typed_expression_program_closure_depth2_v1"
MAX_EXPRESSION_DEPTH = 2
BASE_EXPRESSION_COUNT = 8
DEPTH_ONE_RAW_COUNT = 41
DEPTH_ONE_NEW_SIGNATURE_COUNT = 13
DEPTH_TWO_RAW_COUNT = 429
DEPTH_TWO_NEW_SIGNATURE_COUNT = 194
SEMANTIC_REPRESENTATIVE_COUNT = 215
STATE_COORDINATE_REPRESENTATIVE_COUNT = 174
ACTION_COORDINATE_REPRESENTATIVE_COUNT = 37
REQUIRED_CANDIDATE_COUNT = (
    (STATE_COORDINATE_REPRESENTATIVE_COUNT + 1)
    * (ACTION_COORDINATE_REPRESENTATIVE_COUNT + 1)
)
PRODUCTION_CANDIDATE_CAP = REQUIRED_CANDIDATE_COUNT
REQUIRED_ADMISSIBLE_CANDIDATE_COUNT = 1384
REQUIRED_SELECTED_CANDIDATE_INDEX = 4013

CURRENT_AUTHORITY_ID = fixed_dsl.CURRENT_AUTHORITY_ID
CURRENT_STRUCTURAL_ID = fixed_dsl.CURRENT_STRUCTURAL_ID

SELECTION_RULE = (
    "max_point_rows_then_max_observed_alias_pairs_then_min_partial_rows_then_"
    "min_entries_cells_programs_ast_complexity_ids_partition_candidate_id_v1"
)
THRESHOLD_RULE = "adjacent_distinct_exact_value_midpoints_v1"
SEMANTIC_DEDUP_RULE = (
    "exact_result_type_context_and_full_source_covariate_signature_keep_"
    "minimum_ast_complexity_v1"
)
OBSERVED_SIGNATURE_RULE = (
    "reward_vector_failure_terminal_and_projected_joint_successor_v1"
)
CANDIDATE_SHAPE = (
    "cartesian_optional_single_state_coordinate_by_optional_single_"
    "state_action_coordinate_state_outer_action_inner_v1"
)
EXPECTED_PRIMITIVE_VOCABULARY = (
    ("legal_actions", "ACTION_SET", "STATE", False),
    ("remaining_tiles", "TILE_SET", "STATE", False),
    ("buffer_counts", "INT_VECTOR", "STATE", False),
    ("buffer_capacity", "INTEGER", "STATE", False),
    ("selected_tile_type", "TILE_TYPE", "STATE_ACTION", False),
    ("integer_literal", "INTEGER", "STATE", True),
)
EXPECTED_OPERATOR_VOCABULARY = (
    ("cardinality", ("ACTION_SET",), "INTEGER"),
    ("cardinality_tiles", ("TILE_SET",), "INTEGER"),
    ("sum_vector", ("INT_VECTOR",), "INTEGER"),
    ("max_vector", ("INT_VECTOR",), "INTEGER"),
    ("count_equal", ("INT_VECTOR", "INTEGER"), "INTEGER"),
    ("subtract", ("INTEGER", "INTEGER"), "INTEGER"),
    ("buffer_at_type", ("INT_VECTOR", "TILE_TYPE"), "INTEGER"),
    ("equals", ("INTEGER", "INTEGER"), "BOOLEAN"),
)

# These literal pins are filled after the implementation is frozen.  The
# retained V0-045 authority is independently checked as well.
PROGRAM_CLOSURE_IMPLEMENTATION_SHA256 = (
    "c17ee3b4501beb859b2fca1a9b07968f32e7f653c6897679581766cca91d1e8f"
)
CANDIDATE_AUDIT_IMPLEMENTATION_SHA256 = (
    "7a011aa2c35910196e277f281c2d2063ef60c4cb7e067e1b66b9493bd68ccf39"
)

DOMAIN_TAGS = {
    "semantic_signature": "acfqp:observed-program-semantic-signature:v1",
    "representative": "acfqp:observed-program-semantic-representative:v1",
    "depth": "acfqp:observed-program-closure-depth-summary:v1",
    "registry": "acfqp:observed-program-closure-registry:v1",
    "spec": "acfqp:observed-program-closure-synthesis-spec:v1",
    "cell": "acfqp:observed-program-closure-cell:v1",
    "partition": "acfqp:observed-program-closure-partition:v1",
    "action_partition": "acfqp:observed-program-closure-action-partition:v1",
    "signature": "acfqp:observed-program-closure-ground-signature:v1",
    "entry": "acfqp:observed-program-closure-entry-evidence:v1",
    "candidate": "acfqp:observed-program-closure-candidate-summary:v1",
    "selected": "acfqp:observed-program-closure-selected-evidence:v1",
    "trace": "acfqp:observed-program-closure-candidate-trace:v1",
    "predicate_atom": "acfqp:observed-program-closure-predicate-atom:v1",
    "predicate_tree": "acfqp:observed-program-closure-predicate-tree:v1",
    "telemetry": "acfqp:observed-program-closure-telemetry:v1",
    "certificate": "acfqp:observed-program-closure-certificate:v1",
    "result": "acfqp:observed-program-closure-result:v1",
    "control": "acfqp:observed-program-closure-cap-control:v1",
}


class ObservedProgramClosureInvariantViolation(ValueError):
    """The closed program-generation or replay authority is inconsistent."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role]
    except (KeyError, TypeError, ValueError) as error:
        raise ObservedProgramClosureInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ObservedProgramClosureInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _exact_tuple(value: Any, item_type: type, field: str) -> tuple[Any, ...]:
    if type(value) is not tuple or any(type(item) is not item_type for item in value):
        raise ObservedProgramClosureInvariantViolation(
            f"{field} rejects nested substitutions before canonical access"
        )
    return value


def _sorted_unique_ids(value: Any, field: str) -> tuple[str, ...]:
    if type(value) is not tuple or any(type(item) is not str for item in value):
        raise ObservedProgramClosureInvariantViolation(f"{field} must be an exact tuple")
    for item in value:
        _cid(item, field)
    if value != tuple(sorted(set(value))):
        raise ObservedProgramClosureInvariantViolation(
            f"{field} must be unique and ID-sorted"
        )
    return value


def _fraction_document(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


ExpressionType = fixed_dsl.ExpressionType
ExpressionContext = fixed_dsl.ExpressionContext
ObservedGeneratedExpressionV1 = fixed_dsl.ObservedGeneratedExpressionV1
ObservedStructuralPrimitiveRegistryBindingV1 = (
    fixed_dsl.ObservedStructuralPrimitiveRegistryBindingV1
)
CandidateEntryClass = fixed_dsl.CandidateEntryClass


def _validate_retained_vocabulary() -> None:
    primitive = tuple(
        (
            operation,
            result_type.value,
            context.value,
            requires_literal,
        )
        for operation, (
            result_type,
            context,
            requires_literal,
        ) in fixed_dsl._PRIMITIVE_SIGNATURES.items()
    )
    operator = tuple(
        (
            operation,
            tuple(item.value for item in argument_types),
            result_type.value,
        )
        for operation, (
            argument_types,
            result_type,
        ) in fixed_dsl._OPERATOR_SIGNATURES.items()
    )
    if (
        primitive != EXPECTED_PRIMITIVE_VOCABULARY
        or operator != EXPECTED_OPERATOR_VOCABULARY
        or fixed_dsl._OPERATION_ORDER
        != tuple(item[0] for item in EXPECTED_PRIMITIVE_VOCABULARY)
        + tuple(item[0] for item in EXPECTED_OPERATOR_VOCABULARY)
    ):
        raise ObservedProgramClosureInvariantViolation(
            "retained human primitive/operator vocabulary changed"
        )


def _base_programs() -> tuple[ObservedGeneratedExpressionV1, ...]:
    expressions = (
        *(fixed_dsl._primitive(operation) for operation in (
            "legal_actions",
            "remaining_tiles",
            "buffer_counts",
            "buffer_capacity",
            "selected_tile_type",
        )),
        *(fixed_dsl._primitive("integer_literal", value) for value in (0, 1, 2)),
    )
    return tuple(sorted(expressions, key=fixed_dsl._ast_complexity))


def _normalized_semantic_value(
    expression: ObservedGeneratedExpressionV1,
    value: Any,
) -> dict[str, Any]:
    result_type = expression.result_type
    if result_type is ExpressionType.ACTION_SET:
        if type(value) is not tuple or any(
            type(item) is not CanonicalGroundActionV1 for item in value
        ):
            raise ObservedProgramClosureInvariantViolation(
                "ACTION_SET evaluator value substitution"
            )
        return {
            "kind": result_type.value,
            "value": sorted({item.action_id for item in value}),
        }
    if result_type in (ExpressionType.TILE_SET, ExpressionType.INT_VECTOR):
        if type(value) is not tuple or any(type(item) is not int for item in value):
            raise ObservedProgramClosureInvariantViolation(
                f"{result_type.value} evaluator value substitution"
            )
        return {"kind": result_type.value, "value": list(value)}
    if result_type in (ExpressionType.INTEGER, ExpressionType.TILE_TYPE):
        if type(value) is not int:
            raise ObservedProgramClosureInvariantViolation(
                f"{result_type.value} evaluator value substitution"
            )
        return {"kind": result_type.value, "value": value}
    if result_type is ExpressionType.BOOLEAN:
        if type(value) is not bool:
            raise ObservedProgramClosureInvariantViolation(
                "BOOLEAN evaluator value substitution"
            )
        return {"kind": result_type.value, "value": value}
    raise ObservedProgramClosureInvariantViolation("unknown expression result type")


def _semantic_signature_payload(
    expression: ObservedGeneratedExpressionV1,
    observation_log: ObservationLogManifestV1,
    structural: ObservedStructuralPrimitiveRegistryBindingV1,
) -> dict[str, Any]:
    catalogue_by_state = {
        item.state_id: item for item in observation_log.action_catalogues
    }
    state_by_id = {item.state_id: item for item in observation_log.states}
    states = tuple(sorted(observation_log.states, key=lambda item: item.state_id))
    actions = tuple(
        sorted(
            (
                action
                for catalogue in observation_log.action_catalogues
                for action in catalogue.actions
            ),
            key=lambda item: item.ground_row_id,
        )
    )
    if expression.context is ExpressionContext.STATE:
        covariates = tuple(item.state_id for item in states)
        values = tuple(
            fixed_dsl._eval_expression(
                expression,
                state,
                catalogue_by_state[state.state_id],
                None,
                structural,
            )
            for state in states
        )
    else:
        covariates = tuple(item.ground_row_id for item in actions)
        values = tuple(
            fixed_dsl._eval_expression(
                expression,
                state_by_id[action.state_id],
                catalogue_by_state[action.state_id],
                action,
                structural,
            )
            for action in actions
        )
    return {
        "schema": "acfqp.observed_program_semantic_signature.v1",
        "observation_log_id": observation_log.log_id,
        "result_type": expression.result_type.value,
        "context": expression.context.value,
        "covariate_ids": list(covariates),
        "typed_values": [
            _normalized_semantic_value(expression, value) for value in values
        ],
    }


def _generate_program_closure(
    observation_log: ObservationLogManifestV1,
    structural: ObservedStructuralPrimitiveRegistryBindingV1,
) -> tuple[
    tuple["ProgramClosureDepthSummaryV1", ...],
    tuple["ProgramSemanticRepresentativeV1", ...],
]:
    retained: dict[str, tuple[ObservedGeneratedExpressionV1, dict[str, Any]]] = {}
    depth_summaries: list[ProgramClosureDepthSummaryV1] = []

    bases = _base_programs()
    for expression in bases:
        payload = _semantic_signature_payload(expression, observation_log, structural)
        signature_id = _content_id("semantic_signature", payload)
        prior = retained.get(signature_id)
        if prior is None or fixed_dsl._ast_complexity(expression) < fixed_dsl._ast_complexity(prior[0]):
            retained[signature_id] = (expression, payload)
    depth_summaries.append(
        ProgramClosureDepthSummaryV1(0, len(bases), len(retained), len(retained))
    )

    for depth in range(1, MAX_EXPRESSION_DEPTH + 1):
        available = tuple(item[0] for item in retained.values())
        by_type = {
            expression_type: tuple(
                expression
                for expression in available
                if expression.result_type is expression_type
            )
            for expression_type in ExpressionType
        }
        generated: dict[str, ObservedGeneratedExpressionV1] = {}
        for operation, (argument_types, _) in fixed_dsl._OPERATOR_SIGNATURES.items():
            for arguments in product(*(by_type[item] for item in argument_types)):
                expression = fixed_dsl._operator(operation, arguments)
                if expression.depth == depth:
                    generated[expression.expression_id] = expression
        raw = tuple(sorted(generated.values(), key=fixed_dsl._ast_complexity))
        before = len(retained)
        for expression in raw:
            payload = _semantic_signature_payload(
                expression, observation_log, structural
            )
            signature_id = _content_id("semantic_signature", payload)
            prior = retained.get(signature_id)
            if prior is None or fixed_dsl._ast_complexity(expression) < fixed_dsl._ast_complexity(prior[0]):
                retained[signature_id] = (expression, payload)
        depth_summaries.append(
            ProgramClosureDepthSummaryV1(
                depth, len(raw), len(retained) - before, len(retained)
            )
        )

    representatives = tuple(
        sorted(
            (
                ProgramSemanticRepresentativeV1(expression, signature_id)
                for signature_id, (expression, _) in retained.items()
            ),
            key=lambda item: item.expression.expression_id,
        )
    )
    return tuple(depth_summaries), representatives


@dataclass(frozen=True, slots=True)
class ProgramClosureDepthSummaryV1:
    depth: int
    raw_syntactic_expression_count: int
    new_semantic_signature_count: int
    cumulative_semantic_representative_count: int

    def __post_init__(self) -> None:
        if (
            type(self.depth) is not int
            or not 0 <= self.depth <= MAX_EXPRESSION_DEPTH
            or any(
                type(value) is not int or value < 0
                for value in (
                    self.raw_syntactic_expression_count,
                    self.new_semantic_signature_count,
                    self.cumulative_semantic_representative_count,
                )
            )
        ):
            raise ObservedProgramClosureInvariantViolation(
                "closure depth summary substitution"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observed_program_closure_depth_summary.v1",
            "depth": self.depth,
            "raw_syntactic_expression_count": self.raw_syntactic_expression_count,
            "new_semantic_signature_count": self.new_semantic_signature_count,
            "cumulative_semantic_representative_count": self.cumulative_semantic_representative_count,
        }

    @property
    def summary_id(self) -> str:
        return _content_id("depth", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "summary_id": self.summary_id}


@dataclass(frozen=True, slots=True)
class ProgramSemanticRepresentativeV1:
    expression: ObservedGeneratedExpressionV1
    semantic_signature_id: str

    def __post_init__(self) -> None:
        if type(self.expression) is not ObservedGeneratedExpressionV1:
            raise ObservedProgramClosureInvariantViolation(
                "semantic representative rejects duck expressions"
            )
        _cid(self.semantic_signature_id, "semantic signature")
        if not 0 <= self.expression.depth <= MAX_EXPRESSION_DEPTH:
            raise ObservedProgramClosureInvariantViolation(
                "semantic representative exceeds closure depth"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observed_program_semantic_representative.v1",
            "expression": self.expression.to_document(),
            "semantic_signature_id": self.semantic_signature_id,
            "retention_rule": "minimum_ast_complexity_then_expression_id_v1",
        }

    @property
    def representative_id(self) -> str:
        return _content_id("representative", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "representative_id": self.representative_id}


@dataclass(frozen=True, slots=True)
class ObservedProgramClosureRegistryV1:
    observation_log_id: str
    structural_binding_id: str
    depth_summaries: tuple[ProgramClosureDepthSummaryV1, ...]
    semantic_representatives: tuple[ProgramSemanticRepresentativeV1, ...]
    state_coordinate_expression_ids: tuple[str, ...]
    action_coordinate_expression_ids: tuple[str, ...]
    profile: str = DSL_PROFILE
    max_depth: int = MAX_EXPRESSION_DEPTH
    semantic_dedup_rule: str = SEMANTIC_DEDUP_RULE
    frozen_primitive_operator_vocabulary: bool = True
    program_closure_implementation_sha256: str = PROGRAM_CLOSURE_IMPLEMENTATION_SHA256
    retained_v0045_evaluator_sha256: str = fixed_dsl.OBSERVATION_EVALUATOR_SHA256

    def __post_init__(self) -> None:
        _cid(self.observation_log_id, "program registry observation log")
        _cid(self.structural_binding_id, "program registry structural binding")
        _exact_tuple(
            self.depth_summaries,
            ProgramClosureDepthSummaryV1,
            "program closure depth summaries",
        )
        _exact_tuple(
            self.semantic_representatives,
            ProgramSemanticRepresentativeV1,
            "program semantic representatives",
        )
        if tuple(item.depth for item in self.depth_summaries) != (0, 1, 2):
            raise ObservedProgramClosureInvariantViolation(
                "program closure depth coverage changed"
            )
        expected_counts = (
            (8, 8, 8),
            (41, 13, 21),
            (429, 194, 215),
        )
        actual_counts = tuple(
            (
                item.raw_syntactic_expression_count,
                item.new_semantic_signature_count,
                item.cumulative_semantic_representative_count,
            )
            for item in self.depth_summaries
        )
        if actual_counts != expected_counts:
            raise ObservedProgramClosureInvariantViolation(
                "program closure count contract changed"
            )
        if (
            len(self.semantic_representatives) != SEMANTIC_REPRESENTATIVE_COUNT
            or tuple(item.expression.expression_id for item in self.semantic_representatives)
            != tuple(
                sorted(
                    {
                        item.expression.expression_id
                        for item in self.semantic_representatives
                    }
                )
            )
            or len(
                {item.semantic_signature_id for item in self.semantic_representatives}
            )
            != SEMANTIC_REPRESENTATIVE_COUNT
        ):
            raise ObservedProgramClosureInvariantViolation(
                "semantic representative coverage/order changed"
            )
        _sorted_unique_ids(
            self.state_coordinate_expression_ids, "state coordinate representatives"
        )
        _sorted_unique_ids(
            self.action_coordinate_expression_ids, "action coordinate representatives"
        )
        if (
            len(self.state_coordinate_expression_ids)
            != STATE_COORDINATE_REPRESENTATIVE_COUNT
            or len(self.action_coordinate_expression_ids)
            != ACTION_COORDINATE_REPRESENTATIVE_COUNT
        ):
            raise ObservedProgramClosureInvariantViolation(
                "scalar coordinate representative counts changed"
            )
        expression_by_id = {
            item.expression.expression_id: item.expression
            for item in self.semantic_representatives
        }
        expected_state_ids = tuple(
            sorted(
                expression_id
                for expression_id, expression in expression_by_id.items()
                if expression.context is ExpressionContext.STATE
                and expression.result_type
                in (ExpressionType.INTEGER, ExpressionType.BOOLEAN)
            )
        )
        expected_action_ids = tuple(
            sorted(
                expression_id
                for expression_id, expression in expression_by_id.items()
                if expression.context is ExpressionContext.STATE_ACTION
                and expression.result_type
                in (ExpressionType.INTEGER, ExpressionType.BOOLEAN)
            )
        )
        if (
            self.state_coordinate_expression_ids != expected_state_ids
            or self.action_coordinate_expression_ids != expected_action_ids
        ):
            raise ObservedProgramClosureInvariantViolation(
                "coordinate registry is not the complete scalar representative projection"
            )
        for expression_id in self.state_coordinate_expression_ids:
            expression = expression_by_id[expression_id]
            if (
                expression.context is not ExpressionContext.STATE
                or expression.result_type
                not in (ExpressionType.INTEGER, ExpressionType.BOOLEAN)
            ):
                raise ObservedProgramClosureInvariantViolation(
                    "state coordinate registry type/context mismatch"
                )
        for expression_id in self.action_coordinate_expression_ids:
            expression = expression_by_id[expression_id]
            if (
                expression.context is not ExpressionContext.STATE_ACTION
                or expression.result_type
                not in (ExpressionType.INTEGER, ExpressionType.BOOLEAN)
            ):
                raise ObservedProgramClosureInvariantViolation(
                    "action coordinate registry type/context mismatch"
                )
        if (
            self.profile != DSL_PROFILE
            or self.max_depth != MAX_EXPRESSION_DEPTH
            or self.semantic_dedup_rule != SEMANTIC_DEDUP_RULE
            or self.frozen_primitive_operator_vocabulary is not True
            or self.program_closure_implementation_sha256
            != PROGRAM_CLOSURE_IMPLEMENTATION_SHA256
            or self.retained_v0045_evaluator_sha256
            != fixed_dsl.OBSERVATION_EVALUATOR_SHA256
        ):
            raise ObservedProgramClosureInvariantViolation(
                "program closure authority contract substitution"
            )
        _cid(
            self.program_closure_implementation_sha256,
            "program closure implementation digest",
        )
        _cid(
            self.retained_v0045_evaluator_sha256,
            "retained V0-045 evaluator digest",
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observed_program_closure_registry.v1",
            "schema_version": SCHEMA_VERSION,
            "profile": self.profile,
            "observation_log_id": self.observation_log_id,
            "structural_binding_id": self.structural_binding_id,
            "max_depth": self.max_depth,
            "semantic_dedup_rule": self.semantic_dedup_rule,
            "frozen_primitive_operator_vocabulary": self.frozen_primitive_operator_vocabulary,
            "depth_summaries": [item.to_document() for item in self.depth_summaries],
            "semantic_representatives": [
                item.to_document() for item in self.semantic_representatives
            ],
            "state_coordinate_expression_ids": list(
                self.state_coordinate_expression_ids
            ),
            "action_coordinate_expression_ids": list(
                self.action_coordinate_expression_ids
            ),
            "program_closure_implementation_sha256": self.program_closure_implementation_sha256,
            "retained_v0045_evaluator_sha256": self.retained_v0045_evaluator_sha256,
        }

    @property
    def registry_id(self) -> str:
        return _content_id("registry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registry_id": self.registry_id}


def _build_registry(
    observation_log: ObservationLogManifestV1,
    structural: ObservedStructuralPrimitiveRegistryBindingV1,
) -> ObservedProgramClosureRegistryV1:
    depth_summaries, representatives = _generate_program_closure(
        observation_log, structural
    )
    state_ids = tuple(
        sorted(
            item.expression.expression_id
            for item in representatives
            if item.expression.context is ExpressionContext.STATE
            and item.expression.result_type
            in (ExpressionType.INTEGER, ExpressionType.BOOLEAN)
        )
    )
    action_ids = tuple(
        sorted(
            item.expression.expression_id
            for item in representatives
            if item.expression.context is ExpressionContext.STATE_ACTION
            and item.expression.result_type
            in (ExpressionType.INTEGER, ExpressionType.BOOLEAN)
        )
    )
    return ObservedProgramClosureRegistryV1(
        observation_log.log_id,
        structural.binding_id,
        depth_summaries,
        representatives,
        state_ids,
        action_ids,
    )


def _build_value_table(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    structural: ObservedStructuralPrimitiveRegistryBindingV1,
    registry: ObservedProgramClosureRegistryV1,
) -> FrozenTypedCoordinateValueTableV2:
    expression_by_id = {
        item.expression.expression_id: item.expression
        for item in registry.semantic_representatives
    }
    catalogue_by_state = {
        item.state_id: item for item in observation_log.action_catalogues
    }
    state_by_id = {item.state_id: item for item in observation_log.states}
    state_rows = []
    action_rows = []
    for state in sorted(observation_log.states, key=lambda item: item.state_id):
        catalogue = catalogue_by_state[state.state_id]
        values = []
        for expression_id in registry.state_coordinate_expression_ids:
            expression = expression_by_id[expression_id]
            raw = fixed_dsl._eval_expression(
                expression, state, catalogue, None, structural
            )
            # The V0-042 PartialCell compiler has an exact-integer state
            # coordinate contract.  Boolean state programs are deterministically
            # lowered to 0/1 while their dedup signature remains BOOLEAN-tagged.
            values.append(int(raw) if type(raw) is bool else raw)
        state_rows.append(
            FrozenStateCoordinateValuesV2(state.state_id, tuple(values))
        )
    for catalogue in observation_log.action_catalogues:
        state = state_by_id[catalogue.state_id]
        for action in catalogue.actions:
            action_rows.append(
                FrozenActionCoordinateValuesV2(
                    action.ground_row_id,
                    state.state_id,
                    action.action_id,
                    tuple(
                        fixed_dsl._eval_expression(
                            expression_by_id[expression_id],
                            state,
                            catalogue,
                            action,
                            structural,
                        )
                        for expression_id in registry.action_coordinate_expression_ids
                    ),
                )
            )
    return FrozenTypedCoordinateValueTableV2(
        observation_log.log_id,
        semantics_profile.profile_id,
        observation_authority.authority_id,
        structural.binding_id,
        registry.registry_id,
        registry.state_coordinate_expression_ids,
        registry.action_coordinate_expression_ids,
        tuple(sorted(state_rows, key=lambda item: item.state_id)),
        tuple(sorted(action_rows, key=lambda item: item.ground_row_id)),
    )


@dataclass(frozen=True, slots=True)
class ObservedProgramClosureSynthesisSpecV1:
    observation_authority_id: str
    observation_log_id: str
    structural_binding_id: str
    program_registry_id: str
    required_candidate_count: int = REQUIRED_CANDIDATE_COUNT
    candidate_cap: int = PRODUCTION_CANDIDATE_CAP
    required_admissible_candidate_count: int = REQUIRED_ADMISSIBLE_CANDIDATE_COUNT
    candidate_shape: str = CANDIDATE_SHAPE
    selection_rule: str = SELECTION_RULE
    threshold_rule: str = THRESHOLD_RULE
    observed_signature_rule: str = OBSERVED_SIGNATURE_RULE
    candidate_audit_implementation_sha256: str = CANDIDATE_AUDIT_IMPLEMENTATION_SHA256
    query_inputs: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.observation_authority_id, "synthesis authority"),
            (self.observation_log_id, "synthesis observation log"),
            (self.structural_binding_id, "synthesis structural binding"),
            (self.program_registry_id, "synthesis program registry"),
        ):
            _cid(value, field)
        _cid(
            self.candidate_audit_implementation_sha256,
            "candidate audit implementation digest",
        )
        if (
            self.required_candidate_count != REQUIRED_CANDIDATE_COUNT
            or self.candidate_cap != PRODUCTION_CANDIDATE_CAP
            or self.required_admissible_candidate_count
            != REQUIRED_ADMISSIBLE_CANDIDATE_COUNT
            or self.candidate_shape != CANDIDATE_SHAPE
            or self.selection_rule != SELECTION_RULE
            or self.threshold_rule != THRESHOLD_RULE
            or self.observed_signature_rule != OBSERVED_SIGNATURE_RULE
            or self.candidate_audit_implementation_sha256
            != CANDIDATE_AUDIT_IMPLEMENTATION_SHA256
            or self.query_inputs != 0
        ):
            raise ObservedProgramClosureInvariantViolation(
                "program closure synthesis spec substitution"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observed_program_closure_synthesis_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            **{field: getattr(self, field) for field in self.__dataclass_fields__},
        }

    @property
    def spec_id(self) -> str:
        return _content_id("spec", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "spec_id": self.spec_id}


@dataclass(frozen=True, slots=True)
class ProgramClosureEntryEvidenceV1:
    source_cell_id: str
    action_label: tuple[bool, ...]
    support_ground_row_ids: tuple[str, ...]
    observed_ground_row_ids: tuple[str, ...]
    missing_ground_row_ids: tuple[str, ...]
    distinct_observed_signature_ids: tuple[str, ...]
    classification: CandidateEntryClass

    def __post_init__(self) -> None:
        _cid(self.source_cell_id, "entry source cell")
        if (
            type(self.action_label) is not tuple
            or not self.action_label
            or any(type(value) is not bool for value in self.action_label)
        ):
            raise ObservedProgramClosureInvariantViolation(
                "entry action label must be nonempty exact booleans"
            )
        for values, field in (
            (self.support_ground_row_ids, "entry support rows"),
            (self.observed_ground_row_ids, "entry observed rows"),
            (self.missing_ground_row_ids, "entry missing rows"),
            (self.distinct_observed_signature_ids, "entry signatures"),
        ):
            _sorted_unique_ids(values, field)
        if (
            not self.support_ground_row_ids
            or set(self.observed_ground_row_ids)
            & set(self.missing_ground_row_ids)
            or tuple(
                sorted(
                    (*self.observed_ground_row_ids, *self.missing_ground_row_ids)
                )
            )
            != self.support_ground_row_ids
        ):
            raise ObservedProgramClosureInvariantViolation(
                "entry observed/missing rows do not partition support"
            )
        expected = (
            CandidateEntryClass.OBSERVED_CONTRADICTION
            if len(self.distinct_observed_signature_ids) > 1
            else CandidateEntryClass.UNOBSERVED_UNKNOWN
            if not self.observed_ground_row_ids
            else CandidateEntryClass.PARTIAL_UNKNOWN
            if self.missing_ground_row_ids
            else CandidateEntryClass.POINT_IDENTIFIED
        )
        if type(self.classification) is not CandidateEntryClass or self.classification is not expected:
            raise ObservedProgramClosureInvariantViolation(
                "entry evidence classification mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observed_program_closure_entry_evidence.v1",
            "source_cell_id": self.source_cell_id,
            "action_label": list(self.action_label),
            "support_ground_row_ids": list(self.support_ground_row_ids),
            "observed_ground_row_ids": list(self.observed_ground_row_ids),
            "missing_ground_row_ids": list(self.missing_ground_row_ids),
            "distinct_observed_signature_ids": list(
                self.distinct_observed_signature_ids
            ),
            "classification": self.classification.value,
        }

    @property
    def entry_id(self) -> str:
        return _content_id("entry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "entry_id": self.entry_id}


@dataclass(frozen=True, slots=True)
class ProgramClosureCandidateSummaryV1:
    candidate_index: int
    state_expression_id: str | None
    action_expression_id: str | None
    action_atom_ids: tuple[str, ...]
    partition_id: str
    action_partition_id: str
    point_identified_registered_rows: int
    observed_equal_alias_pair_count: int
    partial_unknown_registered_rows: int
    abstract_entry_count: int
    active_cell_count: int
    total_cell_count: int
    separated_null_conflict_pair_count: int
    nontrivial_point_entry_count: int
    availability_violation_count: int
    contradiction_entry_count: int
    rejection_codes: tuple[str, ...]
    admissible: bool

    def __post_init__(self) -> None:
        if (
            type(self.candidate_index) is not int
            or not 1 <= self.candidate_index <= REQUIRED_CANDIDATE_COUNT
        ):
            raise ObservedProgramClosureInvariantViolation(
                "candidate index out of range"
            )
        for value, field in (
            (self.state_expression_id, "candidate state expression"),
            (self.action_expression_id, "candidate action expression"),
        ):
            if value is not None:
                _cid(value, field)
        _sorted_unique_ids(self.action_atom_ids, "candidate action atom IDs")
        _cid(self.partition_id, "candidate partition")
        _cid(self.action_partition_id, "candidate action partition")
        for field in (
            "point_identified_registered_rows",
            "observed_equal_alias_pair_count",
            "partial_unknown_registered_rows",
            "abstract_entry_count",
            "active_cell_count",
            "total_cell_count",
            "separated_null_conflict_pair_count",
            "nontrivial_point_entry_count",
            "availability_violation_count",
            "contradiction_entry_count",
        ):
            if type(getattr(self, field)) is not int or getattr(self, field) < 0:
                raise ObservedProgramClosureInvariantViolation(
                    f"{field} must be a nonnegative exact integer"
                )
        if (
            type(self.rejection_codes) is not tuple
            or self.rejection_codes != tuple(sorted(set(self.rejection_codes)))
            or any(type(item) is not str or not item for item in self.rejection_codes)
            or type(self.admissible) is not bool
            or self.admissible != (not self.rejection_codes)
        ):
            raise ObservedProgramClosureInvariantViolation(
                "candidate rejection/admissibility substitution"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observed_program_closure_candidate_summary.v1",
            **{field: getattr(self, field) for field in self.__dataclass_fields__},
            "action_atom_ids": list(self.action_atom_ids),
            "rejection_codes": list(self.rejection_codes),
            "missing_rows_used_as_equality_mismatch_or_negative_evidence": 0,
        }

    @property
    def candidate_id(self) -> str:
        return _content_id("candidate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "candidate_id": self.candidate_id}


@dataclass(frozen=True, slots=True)
class ProgramClosureSelectedEvidenceV1:
    candidate_id: str
    entry_evidence: tuple[ProgramClosureEntryEvidenceV1, ...]

    def __post_init__(self) -> None:
        _cid(self.candidate_id, "selected candidate")
        _exact_tuple(
            self.entry_evidence,
            ProgramClosureEntryEvidenceV1,
            "selected candidate entry evidence",
        )
        if tuple(item.entry_id for item in self.entry_evidence) != tuple(
            sorted({item.entry_id for item in self.entry_evidence})
        ):
            raise ObservedProgramClosureInvariantViolation(
                "selected entry evidence must be unique and ID-sorted"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observed_program_closure_selected_evidence.v1",
            "candidate_id": self.candidate_id,
            "entry_evidence": [item.to_document() for item in self.entry_evidence],
        }

    @property
    def selected_evidence_id(self) -> str:
        return _content_id("selected", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "selected_evidence_id": self.selected_evidence_id}


def _candidate_partition(
    observation_log: ObservationLogManifestV1,
    state_expression_id: str | None,
    value_table: FrozenTypedCoordinateValueTableV2,
) -> tuple[
    str,
    tuple[tuple[str, str, tuple[int, ...], tuple[str, ...]], ...],
    dict[str, str],
]:
    indexes = (
        ()
        if state_expression_id is None
        else (value_table.state_expression_ids.index(state_expression_id),)
    )
    value_by_state = {
        row.state_id: tuple(row.values[index] for index in indexes)
        for row in value_table.state_rows
    }
    groups: dict[tuple[str, tuple[int, ...]], list[str]] = {}
    for state in observation_log.states:
        values = (
            value_by_state[state.state_id]
            if state.planning_kind is PlanningKind.ACTIVE
            else ()
        )
        if any(type(value) is not int for value in values):
            raise ObservedProgramClosureInvariantViolation(
                "candidate state coordinate did not lower to exact integer"
            )
        groups.setdefault((state.planning_kind.value, values), []).append(
            state.state_id
        )
    cells = []
    for (kind, values), members in groups.items():
        payload = {
            "planning_kind": kind,
            "coordinate_values": list(values),
            "member_state_ids": sorted(members),
        }
        cells.append(
            (
                _content_id("cell", payload),
                kind,
                values,
                tuple(sorted(members)),
            )
        )
    cells.sort(key=lambda item: item[0])
    partition_payload = {
        "cells": [
            {
                "cell_id": cell_id,
                "planning_kind": kind,
                "coordinate_values": list(values),
                "member_state_ids": list(members),
            }
            for cell_id, kind, values, members in cells
        ]
    }
    partition_id = _content_id("partition", partition_payload)
    return (
        partition_id,
        tuple(cells),
        {
            state_id: cell_id
            for cell_id, _, _, members in cells
            for state_id in members
        },
    )


def _compile_action_atoms(
    action_expression_id: str | None,
    value_table: FrozenTypedCoordinateValueTableV2,
) -> tuple[FrozenTypedActionCoordinateAtomV2, ...]:
    if action_expression_id is None:
        return (
            FrozenTypedActionCoordinateAtomV2(
                TypedActionAtomKind.UNIVERSAL_TRUE, None, None
            ),
        )
    index = value_table.action_expression_ids.index(action_expression_id)
    values = tuple(row.values[index] for row in value_table.action_rows)
    runtime_types = {type(value) for value in values}
    atoms: list[FrozenTypedActionCoordinateAtomV2] = []
    if runtime_types == {bool}:
        atoms.append(
            FrozenTypedActionCoordinateAtomV2(
                TypedActionAtomKind.BOOLEAN_IDENTITY,
                action_expression_id,
                None,
            )
        )
    elif runtime_types == {int}:
        distinct = tuple(sorted(set(values)))
        atoms.extend(
            FrozenTypedActionCoordinateAtomV2(
                TypedActionAtomKind.INTEGER_LEQ,
                action_expression_id,
                Fraction(left + right, 2),
            )
            for left, right in zip(distinct, distinct[1:])
        )
    else:
        raise ObservedProgramClosureInvariantViolation(
            "action coordinate violates scalar type"
        )
    return tuple(sorted(atoms, key=lambda item: item.atom_id))


def _action_labels(
    action_expression_id: str | None,
    atoms: tuple[FrozenTypedActionCoordinateAtomV2, ...],
    value_table: FrozenTypedCoordinateValueTableV2,
) -> dict[str, tuple[bool, ...]]:
    if action_expression_id is not None and not atoms:
        return {row.ground_row_id: (True,) for row in value_table.action_rows}
    labels: dict[str, tuple[bool, ...]] = {}
    for row in value_table.action_rows:
        values = []
        for atom in atoms:
            if atom.kind is TypedActionAtomKind.UNIVERSAL_TRUE:
                values.append(True)
                continue
            index = value_table.action_expression_ids.index(
                atom.source_expression_id
            )
            raw = row.values[index]
            if atom.kind is TypedActionAtomKind.BOOLEAN_IDENTITY:
                if type(raw) is not bool:
                    raise ObservedProgramClosureInvariantViolation(
                        "boolean action atom received nonboolean value"
                    )
                values.append(raw)
            else:
                if type(raw) is not int:
                    raise ObservedProgramClosureInvariantViolation(
                        "integer action atom received noninteger value"
                    )
                values.append(Fraction(raw) <= atom.threshold)
        labels[row.ground_row_id] = tuple(values)
    return labels


def _action_partition_id(labels: Mapping[str, tuple[bool, ...]]) -> str:
    groups: dict[tuple[bool, ...], list[str]] = {}
    for ground_row_id, label in labels.items():
        groups.setdefault(label, []).append(ground_row_id)
    return _content_id(
        "action_partition",
        {
            "classes": [
                {"label": list(label), "ground_row_ids": sorted(rows)}
                for label, rows in sorted(groups.items())
            ]
        },
    )


def _ground_signature_id(
    observation: Any,
    cell_by_state: dict[str, str],
    reward_names: tuple[str, ...],
) -> str:
    rewards = dict(observation.reward_features)
    if observation.terminal:
        outcome = "TERMINAL_FAILURE" if observation.failure else "TERMINAL_SUCCESS"
        destination = None
    else:
        outcome = "CONTINUATION"
        destination = (
            cell_by_state[observation.successor.reference]
            if observation.successor.kind is SuccessorKind.REGISTERED_STATE
            else "EXTERNAL_STATE"
        )
    return _content_id(
        "signature",
        {
            "reward_features": [
                {
                    "name": name,
                    "value": _fraction_document(
                        rewards.get(name, Fraction(0))
                    ),
                }
                for name in reward_names
            ],
            "failure": observation.failure,
            "terminal": observation.terminal,
            "outcome": outcome,
            "destination": destination,
        },
    )


def _entry_key_by_row(
    observation_log: ObservationLogManifestV1,
    cell_by_state: dict[str, str],
    labels: Mapping[str, tuple[bool, ...]],
) -> dict[str, tuple[str, tuple[bool, ...]]]:
    return {
        action.ground_row_id: (
            cell_by_state[action.state_id],
            labels[action.ground_row_id],
        )
        for catalogue in observation_log.action_catalogues
        for action in catalogue.actions
    }


def _null_conflict_pairs(
    observation_log: ObservationLogManifestV1,
    value_table: FrozenTypedCoordinateValueTableV2,
    reward_names: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    _, _, cell_by_state = _candidate_partition(
        observation_log, None, value_table
    )
    atoms = _compile_action_atoms(None, value_table)
    labels = _action_labels(None, atoms, value_table)
    key_by_row = _entry_key_by_row(observation_log, cell_by_state, labels)
    signatures = {
        item.ground_row_id: _ground_signature_id(
            item, cell_by_state, reward_names
        )
        for item in observation_log.observations
    }
    return tuple(
        (left, right)
        for left, right in combinations(sorted(signatures), 2)
        if key_by_row[left] == key_by_row[right]
        and signatures[left] != signatures[right]
    )


def _audit_candidate(
    candidate_index: int,
    state_expression_id: str | None,
    action_expression_id: str | None,
    observation_log: ObservationLogManifestV1,
    value_table: FrozenTypedCoordinateValueTableV2,
    reward_names: tuple[str, ...],
    null_conflicts: tuple[tuple[str, str], ...],
    state_cache: Mapping[
        str | None,
        tuple[
            str,
            tuple[tuple[str, str, tuple[int, ...], tuple[str, ...]], ...],
            dict[str, str],
            dict[str, str],
        ],
    ],
    action_cache: Mapping[
        str | None,
        tuple[
            tuple[FrozenTypedActionCoordinateAtomV2, ...],
            dict[str, tuple[bool, ...]],
            str,
        ],
    ],
    *,
    include_evidence: bool,
) -> tuple[ProgramClosureCandidateSummaryV1, tuple[ProgramClosureEntryEvidenceV1, ...]]:
    del reward_names
    partition_id, cells, cell_by_state, signature_by_row = state_cache[
        state_expression_id
    ]
    atoms, labels, action_partition_id = action_cache[action_expression_id]
    key_by_row = _entry_key_by_row(observation_log, cell_by_state, labels)
    catalogue_by_state = {
        item.state_id: item for item in observation_log.action_catalogues
    }
    availability_violations = 0
    for _, kind, _, members in cells:
        if kind != PlanningKind.ACTIVE.value:
            continue
        label_sets = {
            tuple(
                sorted(
                    {
                        labels[action.ground_row_id]
                        for action in catalogue_by_state[state_id].actions
                    }
                )
            )
            for state_id in members
        }
        if len(label_sets) != 1:
            availability_violations += 1
    observation_by_row = {
        item.ground_row_id: item for item in observation_log.observations
    }
    rows_by_entry: dict[tuple[str, tuple[bool, ...]], list[str]] = {}
    for row_id, key in key_by_row.items():
        rows_by_entry.setdefault(key, []).append(row_id)
    evidence: list[ProgramClosureEntryEvidenceV1] = []
    point_rows = 0
    partial_rows = 0
    equal_pairs = 0
    contradictions = 0
    nontrivial_points = 0
    for (cell_id, label), support in rows_by_entry.items():
        support_tuple = tuple(sorted(support))
        observed = tuple(
            sorted(set(support_tuple) & set(observation_by_row))
        )
        missing = tuple(
            sorted(set(support_tuple) - set(observation_by_row))
        )
        signatures = tuple(
            sorted({signature_by_row[row_id] for row_id in observed})
        )
        classification = (
            CandidateEntryClass.OBSERVED_CONTRADICTION
            if len(signatures) > 1
            else CandidateEntryClass.UNOBSERVED_UNKNOWN
            if not observed
            else CandidateEntryClass.PARTIAL_UNKNOWN
            if missing
            else CandidateEntryClass.POINT_IDENTIFIED
        )
        if include_evidence:
            evidence.append(
                ProgramClosureEntryEvidenceV1(
                    cell_id,
                    label,
                    support_tuple,
                    observed,
                    missing,
                    signatures,
                    classification,
                )
            )
        signature_counts: dict[str, int] = {}
        for row_id in observed:
            signature_counts[signature_by_row[row_id]] = (
                signature_counts.get(signature_by_row[row_id], 0) + 1
            )
        equal_pairs += sum(
            count * (count - 1) // 2 for count in signature_counts.values()
        )
        if classification is CandidateEntryClass.POINT_IDENTIFIED:
            point_rows += len(support_tuple)
            if len(support_tuple) >= 2:
                nontrivial_points += 1
        elif classification is CandidateEntryClass.PARTIAL_UNKNOWN:
            partial_rows += len(support_tuple)
        elif classification is CandidateEntryClass.OBSERVED_CONTRADICTION:
            contradictions += 1
    separated = sum(
        key_by_row[left] != key_by_row[right]
        for left, right in null_conflicts
    )
    active_cells = sum(
        kind == PlanningKind.ACTIVE.value for _, kind, _, _ in cells
    )
    rejection_codes = []
    if action_expression_id is not None and not atoms:
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
    total_ground_rows = len(value_table.action_rows)
    if len(cells) >= len(observation_log.states) or len(rows_by_entry) >= total_ground_rows:
        rejection_codes.append("NO_STRICT_STATE_ACTION_COMPRESSION")
    rejection_tuple = tuple(sorted(set(rejection_codes)))
    summary = ProgramClosureCandidateSummaryV1(
        candidate_index,
        state_expression_id,
        action_expression_id,
        tuple(item.atom_id for item in atoms),
        partition_id,
        action_partition_id,
        point_rows,
        equal_pairs,
        partial_rows,
        len(rows_by_entry),
        active_cells,
        len(cells),
        separated,
        nontrivial_points,
        availability_violations,
        contradictions,
        rejection_tuple,
        not rejection_tuple,
    )
    return summary, tuple(sorted(evidence, key=lambda item: item.entry_id))


def _candidate_selection_key(
    candidate: ProgramClosureCandidateSummaryV1,
    expression_by_id: Mapping[str, ObservedGeneratedExpressionV1],
) -> tuple[Any, ...]:
    selected = tuple(
        expression_by_id[item]
        for item in (
            candidate.state_expression_id,
            candidate.action_expression_id,
        )
        if item is not None
    )
    return (
        -candidate.point_identified_registered_rows,
        -candidate.observed_equal_alias_pair_count,
        candidate.partial_unknown_registered_rows,
        candidate.abstract_entry_count,
        candidate.active_cell_count,
        candidate.total_cell_count,
        int(candidate.state_expression_id is not None),
        int(candidate.action_expression_id is not None),
        sum(item.node_count for item in selected),
        max((item.depth for item in selected), default=0),
        tuple(fixed_dsl._ast_complexity(item) for item in selected),
        () if candidate.state_expression_id is None else (candidate.state_expression_id,),
        () if candidate.action_expression_id is None else (candidate.action_expression_id,),
        candidate.partition_id,
        candidate.action_partition_id,
        candidate.candidate_id,
    )


@dataclass(frozen=True, slots=True)
class ObservedProgramClosureCandidateTraceV1:
    synthesis_spec_id: str
    value_table_id: str
    required_candidate_count: int
    evaluated_candidate_count: int
    admissible_candidate_count: int
    candidates: tuple[ProgramClosureCandidateSummaryV1, ...]
    selected_candidate_id: str
    selected_evidence: ProgramClosureSelectedEvidenceV1
    null_candidate_id: str
    production_cap_exhausted: bool = False

    def __post_init__(self) -> None:
        _cid(self.synthesis_spec_id, "candidate trace synthesis spec")
        _cid(self.value_table_id, "candidate trace value table")
        if (
            self.required_candidate_count != REQUIRED_CANDIDATE_COUNT
            or self.evaluated_candidate_count != REQUIRED_CANDIDATE_COUNT
            or self.admissible_candidate_count
            != REQUIRED_ADMISSIBLE_CANDIDATE_COUNT
            or self.production_cap_exhausted is not False
        ):
            raise ObservedProgramClosureInvariantViolation(
                "candidate trace coverage/count substitution"
            )
        _exact_tuple(
            self.candidates,
            ProgramClosureCandidateSummaryV1,
            "candidate summaries",
        )
        if (
            len(self.candidates) != REQUIRED_CANDIDATE_COUNT
            or tuple(item.candidate_index for item in self.candidates)
            != tuple(range(1, REQUIRED_CANDIDATE_COUNT + 1))
            or len({item.candidate_id for item in self.candidates})
            != REQUIRED_CANDIDATE_COUNT
        ):
            raise ObservedProgramClosureInvariantViolation(
                "candidate trace sequence/uniqueness mismatch"
            )
        _cid(self.selected_candidate_id, "candidate trace selected candidate")
        _cid(self.null_candidate_id, "candidate trace null candidate")
        if type(self.selected_evidence) is not ProgramClosureSelectedEvidenceV1:
            raise ObservedProgramClosureInvariantViolation(
                "candidate trace rejects duck selected evidence"
            )
        if (
            self.selected_candidate_id
            not in {item.candidate_id for item in self.candidates}
            or self.selected_evidence.candidate_id != self.selected_candidate_id
            or self.null_candidate_id != self.candidates[0].candidate_id
            or self.candidates[0].state_expression_id is not None
            or self.candidates[0].action_expression_id is not None
        ):
            raise ObservedProgramClosureInvariantViolation(
                "candidate trace selected/null binding mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observed_program_closure_candidate_trace.v1",
            "schema_version": SCHEMA_VERSION,
            "synthesis_spec_id": self.synthesis_spec_id,
            "value_table_id": self.value_table_id,
            "required_candidate_count": self.required_candidate_count,
            "evaluated_candidate_count": self.evaluated_candidate_count,
            "admissible_candidate_count": self.admissible_candidate_count,
            "candidates": [item.to_document() for item in self.candidates],
            "selected_candidate_id": self.selected_candidate_id,
            "selected_evidence": self.selected_evidence.to_document(),
            "null_candidate_id": self.null_candidate_id,
            "production_cap_exhausted": self.production_cap_exhausted,
        }

    @property
    def trace_id(self) -> str:
        return _content_id("trace", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "trace_id": self.trace_id}


def _compile_candidate_trace(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    registry: ObservedProgramClosureRegistryV1,
    value_table: FrozenTypedCoordinateValueTableV2,
    spec: ObservedProgramClosureSynthesisSpecV1,
) -> tuple[
    ObservedProgramClosureCandidateTraceV1,
    ProgramClosureCandidateSummaryV1,
]:
    if spec.required_candidate_count > spec.candidate_cap:
        raise ObservedProgramClosureInvariantViolation("CANDIDATE_CAP_EXHAUSTED")
    reward_names = tuple(
        item.name for item in semantics_profile.reward_feature_caps
    )
    null_conflicts = _null_conflict_pairs(
        observation_log, value_table, reward_names
    )
    if not null_conflicts:
        raise ObservedProgramClosureInvariantViolation(
            "INSUFFICIENT_OBSERVED_DISTINCTIONS"
        )
    state_choices: tuple[str | None, ...] = (
        None,
        *registry.state_coordinate_expression_ids,
    )
    action_choices: tuple[str | None, ...] = (
        None,
        *registry.action_coordinate_expression_ids,
    )
    state_cache = {}
    for state_expression_id in state_choices:
        partition_id, cells, cell_by_state = _candidate_partition(
            observation_log, state_expression_id, value_table
        )
        signature_by_row = {
            item.ground_row_id: _ground_signature_id(
                item, cell_by_state, reward_names
            )
            for item in observation_log.observations
        }
        state_cache[state_expression_id] = (
            partition_id,
            cells,
            cell_by_state,
            signature_by_row,
        )
    action_cache = {}
    for action_expression_id in action_choices:
        atoms = _compile_action_atoms(action_expression_id, value_table)
        labels = _action_labels(
            action_expression_id, atoms, value_table
        )
        action_cache[action_expression_id] = (
            atoms,
            labels,
            _action_partition_id(labels),
        )
    summaries = []
    candidate_index = 0
    for state_expression_id in state_choices:
        for action_expression_id in action_choices:
            candidate_index += 1
            summary, _ = _audit_candidate(
                candidate_index,
                state_expression_id,
                action_expression_id,
                observation_log,
                value_table,
                reward_names,
                null_conflicts,
                state_cache,
                action_cache,
                include_evidence=False,
            )
            summaries.append(summary)
    candidates = tuple(summaries)
    admissible = tuple(item for item in candidates if item.admissible)
    if not admissible:
        raise ObservedProgramClosureInvariantViolation(
            "NO_OBSERVATION_CONSISTENT_PROGRAM_CANDIDATE"
        )
    expression_by_id = {
        item.expression.expression_id: item.expression
        for item in registry.semantic_representatives
    }
    selected = min(
        admissible,
        key=lambda item: _candidate_selection_key(item, expression_by_id),
    )
    replayed, evidence = _audit_candidate(
        selected.candidate_index,
        selected.state_expression_id,
        selected.action_expression_id,
        observation_log,
        value_table,
        reward_names,
        null_conflicts,
        state_cache,
        action_cache,
        include_evidence=True,
    )
    if replayed != selected:
        raise ObservedProgramClosureInvariantViolation(
            "selected candidate evidence replay mismatch"
        )
    selected_evidence = ProgramClosureSelectedEvidenceV1(
        selected.candidate_id, evidence
    )
    trace = ObservedProgramClosureCandidateTraceV1(
        spec.spec_id,
        value_table.value_table_id,
        REQUIRED_CANDIDATE_COUNT,
        len(candidates),
        len(admissible),
        candidates,
        selected.candidate_id,
        selected_evidence,
        candidates[0].candidate_id,
    )
    return trace, selected


@dataclass(frozen=True, slots=True)
class ProgramClosurePredicateAtomV1:
    expression_id: str
    threshold: Fraction

    def __post_init__(self) -> None:
        _cid(self.expression_id, "predicate expression")
        if type(self.threshold) not in (int, Fraction):
            raise ObservedProgramClosureInvariantViolation(
                "predicate threshold must be exact"
            )
        object.__setattr__(self, "threshold", Fraction(self.threshold))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observed_program_closure_predicate_atom.v1",
            "expression_id": self.expression_id,
            "operator": "<=",
            "threshold": _fraction_document(self.threshold),
        }

    @property
    def atom_id(self) -> str:
        return _content_id("predicate_atom", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atom_id": self.atom_id}


@dataclass(frozen=True, slots=True)
class ProgramClosurePredicateTreeV1:
    selected_candidate_id: str
    partition_id: str
    state_atoms: tuple[ProgramClosurePredicateAtomV1, ...]
    action_atom_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _cid(self.selected_candidate_id, "predicate tree candidate")
        _cid(self.partition_id, "predicate tree partition")
        _exact_tuple(
            self.state_atoms,
            ProgramClosurePredicateAtomV1,
            "predicate tree state atoms",
        )
        if tuple(item.atom_id for item in self.state_atoms) != tuple(
            sorted({item.atom_id for item in self.state_atoms})
        ):
            raise ObservedProgramClosureInvariantViolation(
                "predicate state atoms must be unique and ID-sorted"
            )
        _sorted_unique_ids(self.action_atom_ids, "predicate action atom IDs")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observed_program_closure_predicate_tree.v1",
            "selected_candidate_id": self.selected_candidate_id,
            "partition_id": self.partition_id,
            "state_atoms": [item.to_document() for item in self.state_atoms],
            "action_atom_ids": list(self.action_atom_ids),
            "threshold_rule": THRESHOLD_RULE,
        }

    @property
    def tree_id(self) -> str:
        return _content_id("predicate_tree", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "tree_id": self.tree_id}


def _predicate_tree(
    observation_log: ObservationLogManifestV1,
    selected: ProgramClosureCandidateSummaryV1,
    value_table: FrozenTypedCoordinateValueTableV2,
) -> ProgramClosurePredicateTreeV1:
    atoms = []
    if selected.state_expression_id is not None:
        active_ids = {
            item.state_id
            for item in observation_log.states
            if item.planning_kind is PlanningKind.ACTIVE
        }
        index = value_table.state_expression_ids.index(
            selected.state_expression_id
        )
        distinct = tuple(
            sorted(
                {
                    row.values[index]
                    for row in value_table.state_rows
                    if row.state_id in active_ids
                }
            )
        )
        atoms.extend(
            ProgramClosurePredicateAtomV1(
                selected.state_expression_id, Fraction(left + right, 2)
            )
            for left, right in zip(distinct, distinct[1:])
        )
    return ProgramClosurePredicateTreeV1(
        selected.candidate_id,
        selected.partition_id,
        tuple(sorted(atoms, key=lambda item: item.atom_id)),
        selected.action_atom_ids,
    )


@dataclass(frozen=True, slots=True)
class ObservedProgramClosureTelemetryV1:
    registered_state_count: int
    registered_ground_row_count: int
    distinct_observed_row_count: int
    missing_ground_row_count: int
    base_expression_count: int
    depth_one_raw_expression_count: int
    depth_two_raw_expression_count: int
    semantic_representative_count: int
    state_coordinate_representative_count: int
    action_coordinate_representative_count: int
    evaluated_candidate_count: int
    admissible_candidate_count: int
    selected_candidate_index: int
    selected_point_rows: int
    selected_observed_equal_alias_pairs: int
    selected_partial_rows: int
    selected_entry_count: int
    selected_active_cell_count: int
    selected_total_cell_count: int
    selected_separated_null_conflict_pairs: int
    selected_nontrivial_point_entries: int
    selected_availability_violations: int
    selected_contradictions: int
    selected_unknown_fraction_multiset: tuple[Fraction, ...]
    new_environment_interactions_during_synthesis: int = 0
    new_generative_oracle_samples_during_synthesis: int = 0
    new_exact_kernel_queries_during_synthesis: int = 0
    new_synthetic_model_rollouts_during_synthesis: int = 0
    query_inputs_during_synthesis: int = 0

    def __post_init__(self) -> None:
        for field in self.__dataclass_fields__:
            if field == "selected_unknown_fraction_multiset":
                continue
            if type(getattr(self, field)) is not int or getattr(self, field) < 0:
                raise ObservedProgramClosureInvariantViolation(
                    "telemetry counters must be nonnegative exact integers"
                )
        if (
            type(self.selected_unknown_fraction_multiset) is not tuple
            or any(
                type(value) not in (int, Fraction)
                for value in self.selected_unknown_fraction_multiset
            )
        ):
            raise ObservedProgramClosureInvariantViolation(
                "unknown-fraction telemetry substitution"
            )
        normalized = tuple(
            sorted(Fraction(value) for value in self.selected_unknown_fraction_multiset)
        )
        if any(not 0 <= value <= 1 for value in normalized):
            raise ObservedProgramClosureInvariantViolation(
                "unknown fraction outside [0,1]"
            )
        object.__setattr__(
            self, "selected_unknown_fraction_multiset", normalized
        )
        if any(
            getattr(self, field) != 0
            for field in (
                "new_environment_interactions_during_synthesis",
                "new_generative_oracle_samples_during_synthesis",
                "new_exact_kernel_queries_during_synthesis",
                "new_synthetic_model_rollouts_during_synthesis",
                "query_inputs_during_synthesis",
            )
        ):
            raise ObservedProgramClosureInvariantViolation(
                "synthesis used a forbidden acquisition/query channel"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observed_program_closure_telemetry.v1",
            **{
                field: getattr(self, field)
                for field in self.__dataclass_fields__
                if field != "selected_unknown_fraction_multiset"
            },
            "selected_unknown_fraction_multiset": [
                _fraction_document(value)
                for value in self.selected_unknown_fraction_multiset
            ],
            "held_out_gate_status": "NOT_RUN",
            "statistical_generalization_gate_status": "NOT_RUN",
            "sample_efficiency_gate_status": "NOT_RUN",
        }

    @property
    def telemetry_id(self) -> str:
        return _content_id("telemetry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "telemetry_id": self.telemetry_id}


def _telemetry(
    observation_log: ObservationLogManifestV1,
    registry: ObservedProgramClosureRegistryV1,
    trace: ObservedProgramClosureCandidateTraceV1,
    selected: ProgramClosureCandidateSummaryV1,
) -> ObservedProgramClosureTelemetryV1:
    unknown = tuple(
        Fraction(
            len(entry.missing_ground_row_ids),
            len(entry.support_ground_row_ids),
        )
        for entry in trace.selected_evidence.entry_evidence
    )
    return ObservedProgramClosureTelemetryV1(
        len(observation_log.states),
        sum(len(item.actions) for item in observation_log.action_catalogues),
        len(observation_log.observations),
        sum(len(item.actions) for item in observation_log.action_catalogues)
        - len(observation_log.observations),
        registry.depth_summaries[0].raw_syntactic_expression_count,
        registry.depth_summaries[1].raw_syntactic_expression_count,
        registry.depth_summaries[2].raw_syntactic_expression_count,
        len(registry.semantic_representatives),
        len(registry.state_coordinate_expression_ids),
        len(registry.action_coordinate_expression_ids),
        trace.evaluated_candidate_count,
        trace.admissible_candidate_count,
        selected.candidate_index,
        selected.point_identified_registered_rows,
        selected.observed_equal_alias_pair_count,
        selected.partial_unknown_registered_rows,
        selected.abstract_entry_count,
        selected.active_cell_count,
        selected.total_cell_count,
        selected.separated_null_conflict_pair_count,
        selected.nontrivial_point_entry_count,
        selected.availability_violation_count,
        selected.contradiction_entry_count,
        unknown,
    )


@dataclass(frozen=True, slots=True)
class ObservedProgramClosureCertificateV1:
    observation_authority_id: str
    acquisition_manifest_id: str
    observation_log_id: str
    semantics_profile_id: str
    evidence_ledger_id: str
    structural_binding_id: str
    program_registry_id: str
    value_table_id: str
    synthesis_spec_id: str
    candidate_trace_id: str
    selected_candidate_id: str
    selected_evidence_id: str
    predicate_tree_id: str
    coordinate_proposal_id: str
    partial_model_id: str
    partial_build_result_id: str
    telemetry_id: str
    evaluated_candidate_count: int = REQUIRED_CANDIDATE_COUNT
    status: str = SUCCESS_STATUS
    claim_kind: str = (
        "OBSERVATION_CONSISTENT_QUERY_NEUTRAL_AUTOMATIC_COMPOSITIONAL_"
        "PROGRAM_PARTIAL_RAPM"
    )
    automatic_compositional_program_generation_claimed: bool = True
    frozen_human_primitive_operator_vocabulary: bool = True
    primitive_invention_claimed: bool = False
    operator_invention_claimed: bool = False
    raw_symbolization_claimed: bool = False
    learned_dynamics_claimed: bool = False
    statistical_generalization_claimed: bool = False
    held_out_generalization_claimed: bool = False
    exact_quotient_claimed: bool = False
    plan_certificate_claimed: bool = False
    sample_efficiency_claimed: bool = False

    def __post_init__(self) -> None:
        for field in tuple(self.__dataclass_fields__)[:17]:
            _cid(getattr(self, field), field)
        if (
            self.evaluated_candidate_count != REQUIRED_CANDIDATE_COUNT
            or self.status != SUCCESS_STATUS
            or self.claim_kind
            != "OBSERVATION_CONSISTENT_QUERY_NEUTRAL_AUTOMATIC_COMPOSITIONAL_PROGRAM_PARTIAL_RAPM"
            or self.automatic_compositional_program_generation_claimed is not True
            or self.frozen_human_primitive_operator_vocabulary is not True
        ):
            raise ObservedProgramClosureInvariantViolation(
                "certificate status/count/positive claim substitution"
            )
        if any(
            getattr(self, field) is not False
            for field in (
                "primitive_invention_claimed",
                "operator_invention_claimed",
                "raw_symbolization_claimed",
                "learned_dynamics_claimed",
                "statistical_generalization_claimed",
                "held_out_generalization_claimed",
                "exact_quotient_claimed",
                "plan_certificate_claimed",
                "sample_efficiency_claimed",
            )
        ):
            raise ObservedProgramClosureInvariantViolation(
                "certificate crosses its explicit claim boundary"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observed_program_closure_certificate.v1",
            "schema_version": SCHEMA_VERSION,
            **{field: getattr(self, field) for field in self.__dataclass_fields__},
        }

    @property
    def certificate_id(self) -> str:
        return _content_id("certificate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "certificate_id": self.certificate_id}


@dataclass(frozen=True, slots=True)
class ObservedProgramClosureResultV1:
    structural_binding: ObservedStructuralPrimitiveRegistryBindingV1
    program_registry: ObservedProgramClosureRegistryV1
    value_table: FrozenTypedCoordinateValueTableV2
    synthesis_spec: ObservedProgramClosureSynthesisSpecV1
    candidate_trace: ObservedProgramClosureCandidateTraceV1
    selected_candidate: ProgramClosureCandidateSummaryV1
    predicate_tree: ProgramClosurePredicateTreeV1
    coordinate_proposal: FrozenTypedCoordinateProposalV2
    partial_build_result: ObservationPartialRAPMBuildV1
    telemetry: ObservedProgramClosureTelemetryV1
    certificate: ObservedProgramClosureCertificateV1
    status: str = SUCCESS_STATUS

    def __post_init__(self) -> None:
        expected_types = (
            (self.structural_binding, ObservedStructuralPrimitiveRegistryBindingV1),
            (self.program_registry, ObservedProgramClosureRegistryV1),
            (self.value_table, FrozenTypedCoordinateValueTableV2),
            (self.synthesis_spec, ObservedProgramClosureSynthesisSpecV1),
            (self.candidate_trace, ObservedProgramClosureCandidateTraceV1),
            (self.selected_candidate, ProgramClosureCandidateSummaryV1),
            (self.predicate_tree, ProgramClosurePredicateTreeV1),
            (self.coordinate_proposal, FrozenTypedCoordinateProposalV2),
            (self.partial_build_result, ObservationPartialRAPMBuildV1),
            (self.telemetry, ObservedProgramClosureTelemetryV1),
            (self.certificate, ObservedProgramClosureCertificateV1),
        )
        if any(type(value) is not expected for value, expected in expected_types):
            raise ObservedProgramClosureInvariantViolation(
                "result rejects nested substitutions before canonical access"
            )
        if (
            self.status != SUCCESS_STATUS
            or self.program_registry.observation_log_id
            != self.value_table.observation_log_id
            or self.program_registry.structural_binding_id
            != self.structural_binding.binding_id
            or self.value_table.structural_binding_id
            != self.structural_binding.binding_id
            or self.value_table.dsl_registry_id
            != self.program_registry.registry_id
            or self.synthesis_spec.observation_log_id
            != self.value_table.observation_log_id
            or self.synthesis_spec.structural_binding_id
            != self.structural_binding.binding_id
            or self.synthesis_spec.program_registry_id
            != self.program_registry.registry_id
            or self.candidate_trace.synthesis_spec_id
            != self.synthesis_spec.spec_id
            or self.candidate_trace.value_table_id
            != self.value_table.value_table_id
            or self.candidate_trace.selected_candidate_id
            != self.selected_candidate.candidate_id
            or self.predicate_tree.selected_candidate_id
            != self.selected_candidate.candidate_id
            or self.predicate_tree.partition_id
            != self.selected_candidate.partition_id
            or self.coordinate_proposal.selected_candidate_id
            != self.selected_candidate.candidate_id
            or self.coordinate_proposal.candidate_trace_id
            != self.candidate_trace.trace_id
            or self.coordinate_proposal.dsl_registry_id
            != self.program_registry.registry_id
            or self.coordinate_proposal.structural_binding_id
            != self.structural_binding.binding_id
            or self.coordinate_proposal.value_table_id
            != self.value_table.value_table_id
            or self.coordinate_proposal.synthesis_spec_id
            != self.synthesis_spec.spec_id
            or self.partial_build_result.coordinate_proposal_id
            != self.coordinate_proposal.proposal_id
            or self.certificate.structural_binding_id
            != self.structural_binding.binding_id
            or self.certificate.program_registry_id
            != self.program_registry.registry_id
            or self.certificate.value_table_id
            != self.value_table.value_table_id
            or self.certificate.synthesis_spec_id
            != self.synthesis_spec.spec_id
            or self.certificate.candidate_trace_id
            != self.candidate_trace.trace_id
            or self.certificate.selected_candidate_id
            != self.selected_candidate.candidate_id
            or self.certificate.selected_evidence_id
            != self.candidate_trace.selected_evidence.selected_evidence_id
            or self.certificate.predicate_tree_id != self.predicate_tree.tree_id
            or self.certificate.coordinate_proposal_id
            != self.coordinate_proposal.proposal_id
            or self.certificate.partial_model_id
            != self.partial_build_result.model.model_id
            or self.certificate.partial_build_result_id
            != self.partial_build_result.result_id
            or self.certificate.telemetry_id != self.telemetry.telemetry_id
        ):
            raise ObservedProgramClosureInvariantViolation(
                "result artifact identity chain mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observed_program_closure_result.v1",
            "schema_version": SCHEMA_VERSION,
            "status": self.status,
            "structural_binding": self.structural_binding.to_document(),
            "program_registry": self.program_registry.to_document(),
            "value_table": self.value_table.to_document(),
            "synthesis_spec": self.synthesis_spec.to_document(),
            "candidate_trace": self.candidate_trace.to_document(),
            "selected_candidate": self.selected_candidate.to_document(),
            "predicate_tree": self.predicate_tree.to_document(),
            "coordinate_proposal": self.coordinate_proposal.to_document(),
            "partial_build_result": self.partial_build_result.to_document(),
            "telemetry": self.telemetry.to_document(),
            "certificate": self.certificate.to_document(),
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _implementation_digest(functions: tuple[Any, ...]) -> str:
    return hashlib.sha256(
        "\n\x00\n".join(
            inspect.getsource(function) for function in functions
        ).encode("utf-8")
    ).hexdigest()


def _validate_implementation_authority() -> None:
    fixed_dsl._validate_implementation_authority()
    _validate_retained_vocabulary()
    checks = (
        (
            "program closure",
            (
                _validate_retained_vocabulary,
                _base_programs,
                _normalized_semantic_value,
                _semantic_signature_payload,
                _generate_program_closure,
                _build_registry,
                _build_value_table,
            ),
            PROGRAM_CLOSURE_IMPLEMENTATION_SHA256,
        ),
        (
            "candidate audit",
            (
                _candidate_partition,
                _compile_action_atoms,
                _action_labels,
                _action_partition_id,
                _ground_signature_id,
                _entry_key_by_row,
                _null_conflict_pairs,
                _audit_candidate,
                _candidate_selection_key,
                _compile_candidate_trace,
                _predicate_tree,
            ),
            CANDIDATE_AUDIT_IMPLEMENTATION_SHA256,
        ),
    )
    for label, functions, expected in checks:
        if _implementation_digest(functions) != expected:
            raise ObservedProgramClosureInvariantViolation(
                f"runtime {label} implementation differs from frozen authority"
            )


def synthesize_observed_lmb_program_closure_partial_rapm_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
) -> ObservedProgramClosureResultV1:
    """Generate depth-two typed programs and derive the selected partial RAPM."""
    if type(observation_log) is not ObservationLogManifestV1:
        raise ObservedProgramClosureInvariantViolation(
            "synthesizer rejects duck observation logs"
        )
    if type(semantics_profile) is not DeterministicObservationProfileV1:
        raise ObservedProgramClosureInvariantViolation(
            "synthesizer rejects duck semantics profiles"
        )
    if type(observation_authority) is not PreregisteredObservationAuthorityV1:
        raise ObservedProgramClosureInvariantViolation(
            "synthesizer rejects duck observation authorities"
        )
    _validate_implementation_authority()
    try:
        validate_preregistered_observation_source_graph_v1(
            observation_log, semantics_profile, observation_authority
        )
    except ObservationPartialRAPMInvariantViolation as error:
        raise ObservedProgramClosureInvariantViolation(str(error)) from error
    row_count = sum(
        len(item.actions) for item in observation_log.action_catalogues
    )
    if (
        len(observation_log.states),
        row_count,
        len(observation_log.observations),
    ) != (8, 11, 7):
        raise ObservedProgramClosureInvariantViolation(
            "production source graph is not the frozen 8/11/7 control"
        )
    structural = fixed_dsl._structural_binding(
        observation_authority, observation_log
    )
    registry = _build_registry(observation_log, structural)
    table = _build_value_table(
        observation_log,
        semantics_profile,
        observation_authority,
        structural,
        registry,
    )
    spec = ObservedProgramClosureSynthesisSpecV1(
        observation_authority.authority_id,
        observation_log.log_id,
        structural.binding_id,
        registry.registry_id,
    )
    trace, selected = _compile_candidate_trace(
        observation_log, semantics_profile, registry, table, spec
    )
    if (
        selected.candidate_index != REQUIRED_SELECTED_CANDIDATE_INDEX
        or (
            selected.point_identified_registered_rows,
            selected.observed_equal_alias_pair_count,
            selected.partial_unknown_registered_rows,
            selected.abstract_entry_count,
            selected.active_cell_count,
            selected.total_cell_count,
            selected.separated_null_conflict_pair_count,
            selected.nontrivial_point_entry_count,
            selected.availability_violation_count,
            selected.contradiction_entry_count,
        )
        != (7, 3, 0, 5, 4, 6, 18, 3, 0, 0)
    ):
        raise ObservedProgramClosureInvariantViolation(
            "frozen source selected-candidate control changed"
        )
    expression_by_id = {
        item.expression.expression_id: item.expression
        for item in registry.semantic_representatives
    }
    selected_state = expression_by_id[selected.state_expression_id]
    selected_action = expression_by_id[selected.action_expression_id]
    if (
        selected_state.operation != "cardinality"
        or selected_action.operation != "buffer_at_type"
    ):
        raise ObservedProgramClosureInvariantViolation(
            "selected automatic coordinate programs changed"
        )
    tree = _predicate_tree(observation_log, selected, table)
    atoms = _compile_action_atoms(selected.action_expression_id, table)
    if not atoms:
        raise ObservedProgramClosureInvariantViolation(
            "selected candidate lacks compiled action atoms"
        )
    proposal = FrozenTypedCoordinateProposalV2(
        (selected.state_expression_id,),
        (selected.action_expression_id,),
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
    build = build_observation_partial_rapm_from_typed_values_v2(
        observation_log,
        proposal,
        table,
        semantics_profile,
        observation_authority,
    )
    if verify_observation_partial_rapm_from_typed_values_v2(
        observation_log,
        proposal,
        table,
        semantics_profile,
        observation_authority,
        build,
    ):
        raise ObservedProgramClosureInvariantViolation(
            "typed V0-042 builder replay mismatch"
        )
    telemetry = _telemetry(observation_log, registry, trace, selected)
    certificate = ObservedProgramClosureCertificateV1(
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
        trace.selected_evidence.selected_evidence_id,
        tree.tree_id,
        proposal.proposal_id,
        build.model.model_id,
        build.result_id,
        telemetry.telemetry_id,
    )
    return ObservedProgramClosureResultV1(
        structural,
        registry,
        table,
        spec,
        trace,
        selected,
        tree,
        proposal,
        build,
        telemetry,
        certificate,
    )


@dataclass(frozen=True, slots=True)
class ObservedProgramClosureCapControlOutcomeV1:
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
        _cid(self.observation_log_id, "cap-control observation log")
        if (
            type(self.candidate_cap) is not int
            or not 1 <= self.candidate_cap < PRODUCTION_CANDIDATE_CAP
            or self.required_candidate_count != REQUIRED_CANDIDATE_COUNT
            or self.evaluated_candidate_count != 0
            or self.status != "CANDIDATE_CAP_EXHAUSTED"
            or self.production_certificate_published is not False
            or self.model_id is not None
            or self.certificate_id is not None
        ):
            raise ObservedProgramClosureInvariantViolation(
                "cap-control outcome overclaims production work"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observed_program_closure_cap_control.v1",
            **{field: getattr(self, field) for field in self.__dataclass_fields__},
        }

    @property
    def outcome_id(self) -> str:
        return _content_id("control", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "outcome_id": self.outcome_id}


def synthesize_observed_lmb_program_closure_cap_control_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    *,
    candidate_cap: int,
) -> ObservedProgramClosureCapControlOutcomeV1:
    """Separately named negative control; it cannot publish a model."""
    if type(observation_log) is not ObservationLogManifestV1:
        raise ObservedProgramClosureInvariantViolation(
            "cap control rejects duck observation logs"
        )
    if type(semantics_profile) is not DeterministicObservationProfileV1:
        raise ObservedProgramClosureInvariantViolation(
            "cap control rejects duck semantics profiles"
        )
    if type(observation_authority) is not PreregisteredObservationAuthorityV1:
        raise ObservedProgramClosureInvariantViolation(
            "cap control rejects duck observation authorities"
        )
    _validate_implementation_authority()
    try:
        validate_preregistered_observation_source_graph_v1(
            observation_log, semantics_profile, observation_authority
        )
    except ObservationPartialRAPMInvariantViolation as error:
        raise ObservedProgramClosureInvariantViolation(str(error)) from error
    return ObservedProgramClosureCapControlOutcomeV1(
        observation_authority.authority_id,
        observation_log.log_id,
        candidate_cap,
    )


def _validate_claimed_runtime_shape(
    claimed: Any,
    expected: Any,
    path: str,
) -> None:
    if type(claimed) is not type(expected):
        raise ObservedProgramClosureInvariantViolation(
            f"{path} contains a nested runtime-type substitution"
        )
    if type(expected) is tuple:
        if len(claimed) != len(expected):
            raise ObservedProgramClosureInvariantViolation(
                f"{path} tuple shape differs from retained replay"
            )
        for index, (claimed_item, expected_item) in enumerate(
            zip(claimed, expected)
        ):
            _validate_claimed_runtime_shape(
                claimed_item, expected_item, f"{path}[{index}]"
            )
        return
    if is_dataclass(expected):
        for field in fields(type(expected)):
            _validate_claimed_runtime_shape(
                object.__getattribute__(claimed, field.name),
                object.__getattribute__(expected, field.name),
                f"{path}.{field.name}",
            )


def verify_observed_lmb_program_closure_partial_rapm_v1(
    observation_log: ObservationLogManifestV1,
    semantics_profile: DeterministicObservationProfileV1,
    observation_authority: PreregisteredObservationAuthorityV1,
    claimed_result: ObservedProgramClosureResultV1,
) -> tuple[str, ...]:
    """Replay program closure, all 6,650 candidates, selection, and model."""
    if type(claimed_result) is not ObservedProgramClosureResultV1:
        raise ObservedProgramClosureInvariantViolation(
            "verifier rejects duck result artifacts"
        )
    expected = synthesize_observed_lmb_program_closure_partial_rapm_v1(
        observation_log, semantics_profile, observation_authority
    )
    _validate_claimed_runtime_shape(claimed_result, expected, "claimed result")
    failures = []
    if (
        claimed_result.program_registry.registry_id
        != expected.program_registry.registry_id
    ):
        failures.append("PROGRAM_CLOSURE_RECONSTRUCTION_MISMATCH")
    if (
        claimed_result.candidate_trace.trace_id
        != expected.candidate_trace.trace_id
    ):
        failures.append("CANDIDATE_TRACE_RECONSTRUCTION_MISMATCH")
    if (
        claimed_result.coordinate_proposal.proposal_id
        != expected.coordinate_proposal.proposal_id
    ):
        failures.append("COORDINATE_PROPOSAL_RECONSTRUCTION_MISMATCH")
    if (
        claimed_result.partial_build_result.model.model_id
        != expected.partial_build_result.model.model_id
    ):
        failures.append("PARTIAL_MODEL_RECONSTRUCTION_MISMATCH")
    if claimed_result.to_document() != expected.to_document():
        failures.append("RESULT_RECONSTRUCTION_MISMATCH")
    return tuple(failures)


__all__ = [
    "ACTION_COORDINATE_REPRESENTATIVE_COUNT",
    "BASE_EXPRESSION_COUNT",
    "MAX_EXPRESSION_DEPTH",
    "ObservedProgramClosureCandidateTraceV1",
    "ObservedProgramClosureCapControlOutcomeV1",
    "ObservedProgramClosureCertificateV1",
    "ObservedProgramClosureInvariantViolation",
    "ObservedProgramClosureRegistryV1",
    "ObservedProgramClosureResultV1",
    "ObservedProgramClosureSynthesisSpecV1",
    "ObservedProgramClosureTelemetryV1",
    "PRODUCTION_CANDIDATE_CAP",
    "ProgramClosureCandidateSummaryV1",
    "ProgramClosureDepthSummaryV1",
    "ProgramClosureEntryEvidenceV1",
    "ProgramClosurePredicateAtomV1",
    "ProgramClosurePredicateTreeV1",
    "ProgramClosureSelectedEvidenceV1",
    "ProgramSemanticRepresentativeV1",
    "REQUIRED_ADMISSIBLE_CANDIDATE_COUNT",
    "REQUIRED_CANDIDATE_COUNT",
    "REQUIRED_SELECTED_CANDIDATE_INDEX",
    "SEMANTIC_REPRESENTATIVE_COUNT",
    "STATE_COORDINATE_REPRESENTATIVE_COUNT",
    "SUCCESS_STATUS",
    "synthesize_observed_lmb_program_closure_cap_control_v1",
    "synthesize_observed_lmb_program_closure_partial_rapm_v1",
    "verify_observed_lmb_program_closure_partial_rapm_v1",
]
