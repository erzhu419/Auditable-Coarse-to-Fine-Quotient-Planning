"""Exact LMB quotient synthesis from generated typed coordinate programs.

This V1 vertical slice receives only an authoritative :class:`LMBKernel` and
frozen :class:`SuiteBuildCoverage`.  It constructs a preregistered typed DSL
from raw structural primitives, deterministically instantiates its registered
production templates into scalar expression ASTs, exhaustively audits every coordinate-subset
candidate against the exact one-step kernel, and publishes a RAPM only for an
exact state-action homomorphism.

Query specifications, rewards chosen by a query, values, policies, J0,
behavioural targets, and human-selected feature subsets are deliberately not
construction inputs.  The result proves program generation inside one fixed
DSL; it does not prove unknown-semantic invention, neural learning, partial
dynamics, sample efficiency, scale, or cross-domain generalisation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from functools import lru_cache
import hashlib
import inspect
from itertools import combinations
from typing import Any, Iterable, Mapping

from acfqp.abstraction.partition import Partition
from acfqp.abstraction.quotient import QuotientModels, build_quotient_models
from acfqp.artifacts import object_id
from acfqp.build_coverage import SuiteBuildCoverage
import acfqp.direct_feature_synthesis as _direct
from acfqp.domains.matching_buffer import LMBAction, LMBKernel, LMBState, LMBStatus
from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.portable import PortableBuildResult


EXPRESSION_SCHEMA = "acfqp.generated_coordinate_expression@v1"
REGISTRY_SCHEMA = "acfqp.generated_coordinate_dsl_registry@v1"
SPEC_SCHEMA = "acfqp.generated_coordinate_synthesis_spec@v1"
TREE_SCHEMA = "acfqp.generated_coordinate_predicate_tree@v1"
TRACE_SCHEMA = "acfqp.generated_coordinate_candidate_trace@v1"
CERTIFICATE_SCHEMA = "acfqp.generated_coordinate_certificate@v1"

EXPRESSION_DOMAIN = "acfqp:generated-coordinate-expression:v1"
REGISTRY_DOMAIN = "acfqp:generated-coordinate-dsl-registry:v1"
SPEC_DOMAIN = "acfqp:generated-coordinate-synthesis-spec:v1"
STRUCTURAL_DOMAIN = "acfqp:generated-coordinate-lmb-structural:v1"
COVERAGE_DOMAIN = "acfqp:generated-coordinate-coverage:v1"
CELL_DOMAIN = "acfqp:generated-coordinate-cell:v1"
PARTITION_DOMAIN = "acfqp:generated-coordinate-partition:v1"
ATOM_DOMAIN = "acfqp:generated-coordinate-atom:v1"
TREE_DOMAIN = "acfqp:generated-coordinate-tree:v1"
LABEL_DOMAIN = "acfqp:generated-coordinate-action-label:v1"
WITNESS_DOMAIN = "acfqp:generated-coordinate-witness:v1"
CANDIDATE_DOMAIN = "acfqp:generated-coordinate-candidate:v1"
TRACE_DOMAIN = "acfqp:generated-coordinate-trace:v1"
CERTIFICATE_DOMAIN = "acfqp:generated-coordinate-certificate:v1"

DSL_PROFILE = "lmb_structural_typed_expression_dsl_v1"
CONTROL_PROFILE = "lmb_state_only_typed_expression_control_v1"
ENUMERATION_RULE = (
    "preregistered_typed_production_template_instantiation_then_canonical_ast_id_dedup_v1"
)
SELECTION_RULE = (
    "minimum_state_program_count_then_action_program_count_then_split_count_"
    "then_generated_ast_size_depth_registered_operator_order_then_ids_then_partition_id_v1"
)
THRESHOLD_RULE = "adjacent_distinct_generated_value_midpoints_v1"
PRODUCTION_CANDIDATE_CAP = 4096
MAX_AST_DEPTH = 3
MAX_STATE_PROGRAMS = 8
MAX_ACTION_PROGRAMS = 4

ALLOWED_CHANNELS = (
    "authoritative_exact_one_step_kernel",
    "frozen_build_coverage",
    "preregistered_raw_structural_primitives",
    "preregistered_typed_expression_productions",
)
FORBIDDEN_CHANNELS = (
    "BehavioralActionSignature",
    "J0",
    "Q_values",
    "QuerySpec",
    "behavioural_quotient_target",
    "heldout_data",
    "human_selected_feature_subset",
    "policy",
    "reward_weights",
    "value_function",
)
CLAIM_KIND = "EXACT_HOMOMORPHISM_FROM_FIXED_TYPED_DSL_PROGRAM_GENERATION"
CLAIM_SCOPE = (
    "generated compositional coordinate programs inside a fixed typed DSL and "
    "direct exact-kernel homomorphism audit; no unknown-semantic invention, "
    "neural learning, partial dynamics, sample-efficiency, scale, query/value/"
    "policy dependence, or cross-domain generalisation claim"
)

# These constants are filled from independently reviewed source snapshots.
# They are intentionally literals, rather than values computed at import time.
EVALUATOR_IMPLEMENTATION_SHA256 = (
    "6f2c561fb4c771f1d67196eab8cd1e00806f552b3065d8d822835937dc68c286"
)
ENUMERATOR_IMPLEMENTATION_SHA256 = (
    "fb7113a7146665036657bc85945394a7de9a91b4cb9a54dfc26413636e8bc350"
)
COMPILER_IMPLEMENTATION_SHA256 = (
    "a10eb19da10adc11a03a46cdfec50c0b85cc6e6fcb0397b0d14ec665a6d0a45b"
)
AUDIT_IMPLEMENTATION_SHA256 = (
    "d2fa3b1987b95d82827062ef898214792b9cf0ffdf734d409c010b98b9aac67a"
)


class GeneratedCoordinateInvariantViolation(ValueError):
    """The generated-coordinate authority chain or exact audit is malformed."""


class GeneratedCoordinateStatus(str, Enum):
    EXACT_GENERATED_HOMOMORPHISM = "EXACT_GENERATED_HOMOMORPHISM"
    NO_EXACT_GENERATED_HOMOMORPHISM = "NO_EXACT_GENERATED_HOMOMORPHISM"
    CANDIDATE_CAP_EXHAUSTED = "CANDIDATE_CAP_EXHAUSTED"


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


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _exact(document: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(document) is not dict or set(document) != keys:
        raise GeneratedCoordinateInvariantViolation(
            f"{label} must contain exactly {tuple(sorted(keys))!r}"
        )
    return document


def _text(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise GeneratedCoordinateInvariantViolation(f"{label} must be nonempty text")
    return value


def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise GeneratedCoordinateInvariantViolation(
            f"{label} must be an integer >= {minimum}"
        )
    return value


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise GeneratedCoordinateInvariantViolation(
            f"{label} must be a full lowercase SHA-256"
        )
    return value


def _fraction_doc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fraction(value: Any, label: str) -> Fraction:
    record = _exact(value, {"numerator", "denominator"}, label)
    numerator = record["numerator"]
    denominator = record["denominator"]
    if type(numerator) is not int or type(denominator) is not int or denominator <= 0:
        raise GeneratedCoordinateInvariantViolation(f"{label} is not an exact rational")
    result = Fraction(numerator, denominator)
    if _fraction_doc(result) != record:
        raise GeneratedCoordinateInvariantViolation(f"{label} must be reduced")
    return result


_PRIMITIVE_SIGNATURES: dict[
    str, tuple[ExpressionType, ExpressionContext, bool]
] = {
    "legal_actions": (ExpressionType.ACTION_SET, ExpressionContext.STATE, False),
    "remaining_tiles": (ExpressionType.TILE_SET, ExpressionContext.STATE, False),
    "buffer_counts": (ExpressionType.INT_VECTOR, ExpressionContext.STATE, False),
    "buffer_capacity": (ExpressionType.INTEGER, ExpressionContext.STATE, False),
    "selected_tile_type": (
        ExpressionType.TILE_TYPE,
        ExpressionContext.STATE_ACTION,
        False,
    ),
    "integer_literal": (ExpressionType.INTEGER, ExpressionContext.STATE, True),
}

_OPERATOR_SIGNATURES: dict[
    str, tuple[tuple[ExpressionType, ...], ExpressionType]
] = {
    "cardinality": ((ExpressionType.ACTION_SET,), ExpressionType.INTEGER),
    "cardinality_tiles": ((ExpressionType.TILE_SET,), ExpressionType.INTEGER),
    "sum_vector": ((ExpressionType.INT_VECTOR,), ExpressionType.INTEGER),
    "max_vector": ((ExpressionType.INT_VECTOR,), ExpressionType.INTEGER),
    "count_equal": (
        (ExpressionType.INT_VECTOR, ExpressionType.INTEGER),
        ExpressionType.INTEGER,
    ),
    "subtract": (
        (ExpressionType.INTEGER, ExpressionType.INTEGER),
        ExpressionType.INTEGER,
    ),
    "buffer_at_type": (
        (ExpressionType.INT_VECTOR, ExpressionType.TILE_TYPE),
        ExpressionType.INTEGER,
    ),
    "equals": (
        (ExpressionType.INTEGER, ExpressionType.INTEGER),
        ExpressionType.BOOLEAN,
    ),
}


_OPERATION_ORDER = tuple(_PRIMITIVE_SIGNATURES) + tuple(_OPERATOR_SIGNATURES)


@dataclass(frozen=True, slots=True)
class GeneratedExpressionV1:
    operation: str
    result_type: ExpressionType
    context: ExpressionContext
    arguments: tuple["GeneratedExpressionV1", ...] = ()
    literal: int | None = None
    schema: str = EXPRESSION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != EXPRESSION_SCHEMA:
            raise GeneratedCoordinateInvariantViolation("expression schema substitution")
        if type(self.operation) is not str:
            raise GeneratedCoordinateInvariantViolation("expression operation must be text")
        if type(self.result_type) is not ExpressionType:
            raise GeneratedCoordinateInvariantViolation("expression result type substitution")
        if type(self.context) is not ExpressionContext:
            raise GeneratedCoordinateInvariantViolation("expression context substitution")
        if type(self.arguments) is not tuple or any(
            type(argument) is not GeneratedExpressionV1 for argument in self.arguments
        ):
            raise GeneratedCoordinateInvariantViolation(
                "expression arguments require exact GeneratedExpressionV1 tuples"
            )
        if self.operation in _PRIMITIVE_SIGNATURES:
            expected_type, expected_context, needs_literal = _PRIMITIVE_SIGNATURES[
                self.operation
            ]
            if self.arguments:
                raise GeneratedCoordinateInvariantViolation("primitive expression has arguments")
            if self.result_type is not expected_type or self.context is not expected_context:
                raise GeneratedCoordinateInvariantViolation("primitive type/context substitution")
            if needs_literal != (self.literal is not None):
                raise GeneratedCoordinateInvariantViolation("primitive literal contract mismatch")
            if self.literal is not None and type(self.literal) is not int:
                raise GeneratedCoordinateInvariantViolation("literal must be exact integer")
            return
        if self.operation not in _OPERATOR_SIGNATURES:
            raise GeneratedCoordinateInvariantViolation("unknown expression operation")
        if self.literal is not None:
            raise GeneratedCoordinateInvariantViolation("operator cannot carry a literal")
        argument_types, result_type = _OPERATOR_SIGNATURES[self.operation]
        if tuple(argument.result_type for argument in self.arguments) != argument_types:
            raise GeneratedCoordinateInvariantViolation("operator argument type mismatch")
        if self.result_type is not result_type:
            raise GeneratedCoordinateInvariantViolation("operator result type mismatch")
        expected_context = (
            ExpressionContext.STATE_ACTION
            if any(
                argument.context is ExpressionContext.STATE_ACTION
                for argument in self.arguments
            )
            else ExpressionContext.STATE
        )
        if self.context is not expected_context:
            raise GeneratedCoordinateInvariantViolation("operator context mismatch")

    @property
    def depth(self) -> int:
        return 0 if not self.arguments else 1 + max(arg.depth for arg in self.arguments)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "operation": self.operation,
            "result_type": self.result_type.value,
            "context": self.context.value,
            "arguments": [argument.to_document() for argument in self.arguments],
            "literal": self.literal,
        }

    @property
    def expression_id(self) -> str:
        return _cached_expression_id(self)

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "expression_id": self.expression_id}

    @classmethod
    def from_document(cls, document: Any) -> "GeneratedExpressionV1":
        record = _exact(
            document,
            {
                "schema",
                "operation",
                "result_type",
                "context",
                "arguments",
                "literal",
                "expression_id",
            },
            "generated expression",
        )
        if type(record["arguments"]) is not list:
            raise GeneratedCoordinateInvariantViolation("expression arguments must be a list")
        try:
            result_type = ExpressionType(record["result_type"])
            context = ExpressionContext(record["context"])
        except (TypeError, ValueError) as error:
            raise GeneratedCoordinateInvariantViolation(
                "expression enum value is invalid"
            ) from error
        result = cls(
            record["operation"],
            result_type,
            context,
            tuple(cls.from_document(item) for item in record["arguments"]),
            record["literal"],
            record["schema"],
        )
        if record["expression_id"] != result.expression_id or record != result.to_document():
            raise GeneratedCoordinateInvariantViolation(
                "expression ID/document is noncanonical"
            )
        return result


@lru_cache(maxsize=None)
def _cached_expression_id(expression: GeneratedExpressionV1) -> str:
    return _content_id(EXPRESSION_DOMAIN, expression._payload())


def _ast_selection_key(expression: GeneratedExpressionV1) -> tuple[Any, ...]:
    node_count = 1 + sum(_ast_selection_key(arg)[0] for arg in expression.arguments)
    return (
        node_count,
        expression.depth,
        _OPERATION_ORDER.index(expression.operation),
        tuple(_ast_selection_key(arg) for arg in expression.arguments),
        -1 if expression.literal is None else expression.literal,
        expression.expression_id,
    )


def _primitive(operation: str, literal: int | None = None) -> GeneratedExpressionV1:
    result_type, context, _ = _PRIMITIVE_SIGNATURES[operation]
    return GeneratedExpressionV1(operation, result_type, context, (), literal)


def _operator(
    operation: str, arguments: tuple[GeneratedExpressionV1, ...]
) -> GeneratedExpressionV1:
    _, result_type = _OPERATOR_SIGNATURES[operation]
    context = (
        ExpressionContext.STATE_ACTION
        if any(argument.context is ExpressionContext.STATE_ACTION for argument in arguments)
        else ExpressionContext.STATE
    )
    return GeneratedExpressionV1(operation, result_type, context, arguments)


def _eval_expression(
    expression: GeneratedExpressionV1,
    kernel: LMBKernel,
    state: LMBState,
    action: LMBAction | None,
) -> Any:
    """Authoritative evaluator for the preregistered typed expression DSL."""

    operation = expression.operation
    if operation == "legal_actions":
        return tuple(kernel.actions(state))
    if operation == "remaining_tiles":
        return tuple(
            tile
            for tile in range(kernel.tile_count)
            if not state.removed_mask & (1 << tile)
        )
    if operation == "buffer_counts":
        return state.buffer
    if operation == "buffer_capacity":
        return kernel.capacity
    if operation == "selected_tile_type":
        if type(action) is not LMBAction:
            raise GeneratedCoordinateInvariantViolation(
                "state-action expression requires an exact LMBAction"
            )
        return kernel.tile_types[action.tile]
    if operation == "integer_literal":
        return expression.literal
    values = tuple(
        _eval_expression(argument, kernel, state, action)
        for argument in expression.arguments
    )
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
    raise GeneratedCoordinateInvariantViolation("unreachable evaluator operation")


def _enumerate_programs(
    profile: str,
) -> tuple[tuple[GeneratedExpressionV1, ...], tuple[GeneratedExpressionV1, ...]]:
    """Instantiate preregistered typed production templates from raw primitives."""

    if profile not in {DSL_PROFILE, CONTROL_PROFILE}:
        raise GeneratedCoordinateInvariantViolation("unregistered DSL profile")
    legal = _primitive("legal_actions")
    remaining = _primitive("remaining_tiles")
    buffer = _primitive("buffer_counts")
    capacity = _primitive("buffer_capacity")
    selected_type = _primitive("selected_tile_type")
    constants = tuple(_primitive("integer_literal", value) for value in (0, 1, 2))

    state_programs = (
        _operator("cardinality", (legal,)),
        _operator("cardinality_tiles", (remaining,)),
        _operator("sum_vector", (buffer,)),
        _operator("max_vector", (buffer,)),
        *tuple(_operator("count_equal", (buffer, value)) for value in constants),
        _operator("subtract", (capacity, _operator("sum_vector", (buffer,)))),
    )
    buffer_at_selected_type = _operator("buffer_at_type", (buffer, selected_type))
    action_programs = (
        buffer_at_selected_type,
        *tuple(
            _operator("equals", (buffer_at_selected_type, value))
            for value in constants
        ),
    )
    if profile == CONTROL_PROFILE:
        action_programs = ()

    def canonical(
        values: tuple[GeneratedExpressionV1, ...], cap: int
    ) -> tuple[GeneratedExpressionV1, ...]:
        by_id = {value.expression_id: value for value in values}
        ordered = tuple(by_id[key] for key in sorted(by_id))
        if len(ordered) > cap:
            raise GeneratedCoordinateInvariantViolation("generated program cap exceeded")
        if any(value.depth > MAX_AST_DEPTH for value in ordered):
            raise GeneratedCoordinateInvariantViolation("generated AST depth cap exceeded")
        return ordered

    return canonical(state_programs, MAX_STATE_PROGRAMS), canonical(
        action_programs, MAX_ACTION_PROGRAMS
    )


def _implementation_digest(functions: tuple[Any, ...]) -> str:
    return hashlib.sha256(
        "\n\x00\n".join(inspect.getsource(function) for function in functions).encode(
            "utf-8"
        )
    ).hexdigest()


def _validate_implementation_authority() -> None:
    checks = (
        ("evaluator", (_eval_expression,), EVALUATOR_IMPLEMENTATION_SHA256),
        ("enumerator", (_primitive, _operator, _enumerate_programs), ENUMERATOR_IMPLEMENTATION_SHA256),
        ("compiler", (_base_partition, _compile_partition), COMPILER_IMPLEMENTATION_SHA256),
        (
            "audit",
            (_audit_candidate, _candidate_selection_key, _ast_selection_key, _direct._ground_signature, _direct._outcomes),
            AUDIT_IMPLEMENTATION_SHA256,
        ),
    )
    for label, functions, expected in checks:
        if _implementation_digest(functions) != expected:
            raise GeneratedCoordinateInvariantViolation(
                f"runtime {label} implementation differs from frozen authority"
            )


@dataclass(frozen=True, slots=True)
class GeneratedDSLRegistryV1:
    profile: str
    state_programs: tuple[GeneratedExpressionV1, ...]
    action_programs: tuple[GeneratedExpressionV1, ...]
    evaluator_implementation_sha256: str = EVALUATOR_IMPLEMENTATION_SHA256
    enumerator_implementation_sha256: str = ENUMERATOR_IMPLEMENTATION_SHA256
    compiler_implementation_sha256: str = COMPILER_IMPLEMENTATION_SHA256
    audit_implementation_sha256: str = AUDIT_IMPLEMENTATION_SHA256
    schema: str = REGISTRY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != REGISTRY_SCHEMA or self.profile not in {
            DSL_PROFILE,
            CONTROL_PROFILE,
        }:
            raise GeneratedCoordinateInvariantViolation("DSL registry profile/schema substitution")
        if type(self.state_programs) is not tuple or type(self.action_programs) is not tuple:
            raise GeneratedCoordinateInvariantViolation("DSL program registries require tuples")
        if any(type(value) is not GeneratedExpressionV1 for value in self.state_programs + self.action_programs):
            raise GeneratedCoordinateInvariantViolation("DSL program type substitution")
        if tuple(sorted(self.state_programs, key=lambda item: item.expression_id)) != self.state_programs:
            raise GeneratedCoordinateInvariantViolation("state programs are not canonically ordered")
        if tuple(sorted(self.action_programs, key=lambda item: item.expression_id)) != self.action_programs:
            raise GeneratedCoordinateInvariantViolation("action programs are not canonically ordered")
        if len({item.expression_id for item in self.state_programs}) != len(self.state_programs):
            raise GeneratedCoordinateInvariantViolation("duplicate state program")
        if len({item.expression_id for item in self.action_programs}) != len(self.action_programs):
            raise GeneratedCoordinateInvariantViolation("duplicate action program")
        if any(item.context is not ExpressionContext.STATE for item in self.state_programs):
            raise GeneratedCoordinateInvariantViolation("state registry contains action-dependent program")
        if any(item.context is not ExpressionContext.STATE_ACTION for item in self.action_programs):
            raise GeneratedCoordinateInvariantViolation("action registry lacks action dependence")
        for field in (
            "evaluator_implementation_sha256",
            "enumerator_implementation_sha256",
            "compiler_implementation_sha256",
            "audit_implementation_sha256",
        ):
            _sha(getattr(self, field), field)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "profile": self.profile,
            "state_programs": [item.to_document() for item in self.state_programs],
            "action_programs": [item.to_document() for item in self.action_programs],
            "max_ast_depth": MAX_AST_DEPTH,
            "max_state_programs": MAX_STATE_PROGRAMS,
            "max_action_programs": MAX_ACTION_PROGRAMS,
            "enumeration_rule": ENUMERATION_RULE,
            "evaluator_implementation_sha256": self.evaluator_implementation_sha256,
            "enumerator_implementation_sha256": self.enumerator_implementation_sha256,
            "compiler_implementation_sha256": self.compiler_implementation_sha256,
            "audit_implementation_sha256": self.audit_implementation_sha256,
        }

    @property
    def registry_id(self) -> str:
        return _content_id(REGISTRY_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registry_id": self.registry_id}

    @classmethod
    def from_document(cls, document: Any) -> "GeneratedDSLRegistryV1":
        keys = {
            "schema", "profile", "state_programs", "action_programs",
            "max_ast_depth", "max_state_programs", "max_action_programs",
            "enumeration_rule", "evaluator_implementation_sha256",
            "enumerator_implementation_sha256", "compiler_implementation_sha256",
            "audit_implementation_sha256", "registry_id",
        }
        record = _exact(document, keys, "generated DSL registry")
        if type(record["state_programs"]) is not list or type(record["action_programs"]) is not list:
            raise GeneratedCoordinateInvariantViolation("registry program fields must be lists")
        if (
            record["max_ast_depth"] != MAX_AST_DEPTH
            or record["max_state_programs"] != MAX_STATE_PROGRAMS
            or record["max_action_programs"] != MAX_ACTION_PROGRAMS
            or record["enumeration_rule"] != ENUMERATION_RULE
        ):
            raise GeneratedCoordinateInvariantViolation("DSL cap/enumeration substitution")
        result = cls(
            record["profile"],
            tuple(GeneratedExpressionV1.from_document(item) for item in record["state_programs"]),
            tuple(GeneratedExpressionV1.from_document(item) for item in record["action_programs"]),
            record["evaluator_implementation_sha256"],
            record["enumerator_implementation_sha256"],
            record["compiler_implementation_sha256"],
            record["audit_implementation_sha256"],
            record["schema"],
        )
        if record["registry_id"] != result.registry_id or record != result.to_document():
            raise GeneratedCoordinateInvariantViolation("registry ID/document is noncanonical")
        return result


def generated_dsl_registry_v1(profile: str = DSL_PROFILE) -> GeneratedDSLRegistryV1:
    state_programs, action_programs = _enumerate_programs(profile)
    return GeneratedDSLRegistryV1(profile, state_programs, action_programs)


def _structural_payload(kernel: LMBKernel) -> dict[str, Any]:
    return {
        "tile_types": list(kernel.tile_types),
        "blockers": [sorted(value) for value in kernel.blockers],
        "type_count": kernel.type_count,
        "capacity": kernel.capacity,
        "max_layers": kernel.max_layers,
        "reward_features": list(kernel.registered_reward_features),
        "goals": list(kernel.registered_goals),
    }


def _structural_id(kernel: LMBKernel) -> str:
    return _content_id(STRUCTURAL_DOMAIN, _structural_payload(kernel))


def _coverage_payload(coverage: SuiteBuildCoverage[LMBState]) -> dict[str, Any]:
    return {
        "mode": coverage.mode,
        "declared_support_set_sha256": coverage.declared_support_set_sha256,
        "declared_support_state_ids": list(coverage.declared_support_state_ids),
        "covered_state_ids": list(coverage.covered_state_ids),
        "exact_state_cap": coverage.exact_state_cap,
        "admissible_query_support_rule": coverage.admissible_query_support_rule,
        "reuse_outside_coverage_forbidden": coverage.reuse_outside_coverage_forbidden,
    }


def _coverage_id(coverage: SuiteBuildCoverage[LMBState]) -> str:
    return _content_id(COVERAGE_DOMAIN, _coverage_payload(coverage))


@dataclass(frozen=True, slots=True)
class GeneratedSynthesisSpecV1:
    structural_id: str
    coverage_id: str
    registry_id: str
    profile: str
    candidate_cap: int
    allowed_information_channels: tuple[str, ...] = ALLOWED_CHANNELS
    forbidden_information_channels: tuple[str, ...] = FORBIDDEN_CHANNELS
    selection_rule: str = SELECTION_RULE
    threshold_rule: str = THRESHOLD_RULE
    schema: str = SPEC_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != SPEC_SCHEMA or self.profile not in {DSL_PROFILE, CONTROL_PROFILE}:
            raise GeneratedCoordinateInvariantViolation("synthesis spec schema/profile substitution")
        for value, label in (
            (self.structural_id, "structural ID"),
            (self.coverage_id, "coverage ID"),
            (self.registry_id, "registry ID"),
        ):
            _sha(value, label)
        _integer(self.candidate_cap, "candidate cap", 1)
        if self.allowed_information_channels != ALLOWED_CHANNELS:
            raise GeneratedCoordinateInvariantViolation("allowed-channel substitution")
        if self.forbidden_information_channels != FORBIDDEN_CHANNELS:
            raise GeneratedCoordinateInvariantViolation("forbidden-channel substitution")
        if self.selection_rule != SELECTION_RULE or self.threshold_rule != THRESHOLD_RULE:
            raise GeneratedCoordinateInvariantViolation("selection/threshold rule substitution")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "structural_id": self.structural_id,
            "coverage_id": self.coverage_id,
            "registry_id": self.registry_id,
            "profile": self.profile,
            "candidate_cap": self.candidate_cap,
            "allowed_information_channels": list(self.allowed_information_channels),
            "forbidden_information_channels": list(self.forbidden_information_channels),
            "selection_rule": self.selection_rule,
            "threshold_rule": self.threshold_rule,
        }

    @property
    def spec_id(self) -> str:
        return _content_id(SPEC_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "spec_id": self.spec_id}


@dataclass(frozen=True, slots=True)
class GeneratedPredicateAtomV1:
    expression_id: str
    threshold: Fraction

    def __post_init__(self) -> None:
        _sha(self.expression_id, "predicate expression ID")
        if type(self.threshold) is not Fraction:
            raise GeneratedCoordinateInvariantViolation("predicate threshold must be Fraction")

    def _payload(self) -> dict[str, Any]:
        return {
            "expression_id": self.expression_id,
            "operator": "<=",
            "threshold": _fraction_doc(self.threshold),
        }

    @property
    def atom_id(self) -> str:
        return _content_id(ATOM_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atom_id": self.atom_id}


@dataclass(frozen=True, slots=True)
class GeneratedPredicateSplitV1:
    sequence: int
    parent_cell_id: str
    atom: GeneratedPredicateAtomV1
    true_child_cell_id: str
    false_child_cell_id: str
    true_member_count: int
    false_member_count: int

    def __post_init__(self) -> None:
        _integer(self.sequence, "split sequence", 1)
        if type(self.atom) is not GeneratedPredicateAtomV1:
            raise GeneratedCoordinateInvariantViolation("split atom type substitution")
        for value, label in (
            (self.parent_cell_id, "parent cell"),
            (self.true_child_cell_id, "true child"),
            (self.false_child_cell_id, "false child"),
        ):
            _sha(value, label)
        _integer(self.true_member_count, "true member count", 1)
        _integer(self.false_member_count, "false member count", 1)

    def to_document(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "parent_cell_id": self.parent_cell_id,
            "atom": self.atom.to_document(),
            "true_child_cell_id": self.true_child_cell_id,
            "false_child_cell_id": self.false_child_cell_id,
            "true_member_count": self.true_member_count,
            "false_member_count": self.false_member_count,
        }


@dataclass(frozen=True, slots=True)
class GeneratedPredicateTreeV1:
    selected_state_program_ids: tuple[str, ...]
    generated_atoms: tuple[GeneratedPredicateAtomV1, ...]
    splits: tuple[GeneratedPredicateSplitV1, ...]
    partition_id: str
    cell_count: int
    active_cell_count: int
    schema: str = TREE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != TREE_SCHEMA:
            raise GeneratedCoordinateInvariantViolation("tree schema substitution")
        if type(self.selected_state_program_ids) is not tuple or tuple(sorted(self.selected_state_program_ids)) != self.selected_state_program_ids:
            raise GeneratedCoordinateInvariantViolation("tree program IDs are not sorted tuples")
        if any(type(value) is not str for value in self.selected_state_program_ids):
            raise GeneratedCoordinateInvariantViolation("tree program ID type substitution")
        if type(self.generated_atoms) is not tuple or any(type(value) is not GeneratedPredicateAtomV1 for value in self.generated_atoms):
            raise GeneratedCoordinateInvariantViolation("tree atom type substitution")
        if type(self.splits) is not tuple or any(type(value) is not GeneratedPredicateSplitV1 for value in self.splits):
            raise GeneratedCoordinateInvariantViolation("tree split type substitution")
        if tuple(item.sequence for item in self.splits) != tuple(range(1, len(self.splits) + 1)):
            raise GeneratedCoordinateInvariantViolation("tree split sequence is not contiguous")
        _sha(self.partition_id, "tree partition ID")
        _integer(self.cell_count, "tree cell count", 1)
        _integer(self.active_cell_count, "tree active cell count", 1)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "selected_state_program_ids": list(self.selected_state_program_ids),
            "generated_atoms": [item.to_document() for item in self.generated_atoms],
            "splits": [item.to_document() for item in self.splits],
            "partition_id": self.partition_id,
            "cell_count": self.cell_count,
            "active_cell_count": self.active_cell_count,
        }

    @property
    def tree_id(self) -> str:
        return _content_id(TREE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "tree_id": self.tree_id}


def _partition_payload(partition: Partition) -> dict[str, Any]:
    blocks = [
        sorted(object_id(state, "state") for state in partition.members(cell))
        for cell in partition.cell_ids
    ]
    return {"blocks": sorted(blocks)}


def _partition_id(partition: Partition) -> str:
    return _content_id(PARTITION_DOMAIN, _partition_payload(partition))


def _base_partition(states: tuple[LMBState, ...]) -> Partition:
    mapping: dict[LMBState, str] = {}
    for state in states:
        kind = state.status.value
        mapping[state] = _content_id(CELL_DOMAIN, {"base_kind": kind})
    return Partition.from_mapping(mapping)


def _compile_partition(
    states: tuple[LMBState, ...],
    rows: Mapping[LMBState, Mapping[str, Fraction]],
    selected_program_ids: tuple[str, ...],
) -> tuple[GeneratedPredicateTreeV1, Partition]:
    partition = _base_partition(states)
    atoms: list[GeneratedPredicateAtomV1] = []
    for expression_id in selected_program_ids:
        values = sorted({row[expression_id] for row in rows.values()})
        atoms.extend(
            GeneratedPredicateAtomV1(expression_id, (left + right) / 2)
            for left, right in zip(values, values[1:])
        )
    splits: list[GeneratedPredicateSplitV1] = []
    for atom in atoms:
        active_cells = tuple(
            cell
            for cell in partition.cell_ids
            if all(state.status is LMBStatus.ACTIVE for state in partition.members(cell))
        )
        for cell in active_cells:
            members = partition.members(cell)
            true_states = tuple(
                state
                for state in members
                if rows[state][atom.expression_id] <= atom.threshold
            )
            true_set = set(true_states)
            false_states = tuple(state for state in members if state not in true_set)
            if not true_states or not false_states:
                continue
            true_cell = _content_id(
                CELL_DOMAIN,
                {"parent": str(cell), "atom_id": atom.atom_id, "branch": "true"},
            )
            false_cell = _content_id(
                CELL_DOMAIN,
                {"parent": str(cell), "atom_id": atom.atom_id, "branch": "false"},
            )
            partition = partition.replace_cell(
                cell, false_states, true_states, false_cell, true_cell
            )
            splits.append(
                GeneratedPredicateSplitV1(
                    len(splits) + 1,
                    str(cell),
                    atom,
                    true_cell,
                    false_cell,
                    len(true_states),
                    len(false_states),
                )
            )
    active_cell_count = sum(
        all(state.status is LMBStatus.ACTIVE for state in partition.members(cell))
        for cell in partition.cell_ids
    )
    tree = GeneratedPredicateTreeV1(
        selected_program_ids,
        tuple(atoms),
        tuple(splits),
        _partition_id(partition),
        len(partition.cell_ids),
        active_cell_count,
    )
    return tree, partition


@dataclass(frozen=True, order=True, slots=True)
class GeneratedActionLabelV1:
    values: tuple[tuple[str, Fraction], ...]

    def __post_init__(self) -> None:
        if type(self.values) is not tuple or any(
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) is not Fraction
            for item in self.values
        ):
            raise GeneratedCoordinateInvariantViolation("action label value type substitution")
        if tuple(sorted(self.values)) != self.values or len({key for key, _ in self.values}) != len(self.values):
            raise GeneratedCoordinateInvariantViolation("action label values are not canonical")
        for expression_id, _ in self.values:
            _sha(expression_id, "action-label expression ID")

    def _payload(self) -> dict[str, Any]:
        return {
            "values": [
                {"expression_id": expression_id, "value": _fraction_doc(value)}
                for expression_id, value in self.values
            ]
        }

    @property
    def label_id(self) -> str:
        return _content_id(LABEL_DOMAIN, self._payload())


@dataclass(frozen=True, slots=True)
class GeneratedActionSemanticAdapterV1:
    selected_programs: tuple[GeneratedExpressionV1, ...]

    def __post_init__(self) -> None:
        if type(self.selected_programs) is not tuple or any(
            type(item) is not GeneratedExpressionV1 for item in self.selected_programs
        ):
            raise GeneratedCoordinateInvariantViolation("adapter program type substitution")
        if tuple(sorted(self.selected_programs, key=lambda item: item.expression_id)) != self.selected_programs:
            raise GeneratedCoordinateInvariantViolation("adapter programs are not canonical")
        if any(item.context is not ExpressionContext.STATE_ACTION for item in self.selected_programs):
            raise GeneratedCoordinateInvariantViolation("adapter contains state-only action program")

    @property
    def selected_program_ids(self) -> tuple[str, ...]:
        return tuple(item.expression_id for item in self.selected_programs)

    def label(
        self, kernel: LMBKernel, state: LMBState, action: LMBAction
    ) -> GeneratedActionLabelV1:
        return GeneratedActionLabelV1(
            tuple(
                (item.expression_id, Fraction(_eval_expression(item, kernel, state, action)))
                for item in self.selected_programs
            )
        )

    def labels(
        self, kernel: LMBKernel, state: LMBState
    ) -> tuple[GeneratedActionLabelV1, ...]:
        return tuple(
            sorted({self.label(kernel, state, action) for action in kernel.actions(state)})
        )

    def concretize(
        self,
        kernel: LMBKernel,
        state: LMBState,
        label: GeneratedActionLabelV1,
    ) -> tuple[tuple[Fraction, LMBAction], ...]:
        actions = tuple(
            sorted(
                action
                for action in kernel.actions(state)
                if self.label(kernel, state, action) == label
            )
        )
        if not actions:
            raise GeneratedCoordinateInvariantViolation("semantic label is unavailable")
        probability = Fraction(1, len(actions))
        return tuple((probability, action) for action in actions)


@dataclass(frozen=True, slots=True)
class GeneratedWitnessV1:
    witness_kind: str
    partition_id: str
    selected_state_program_ids: tuple[str, ...]
    selected_action_program_ids: tuple[str, ...]
    state_ids: tuple[str, ...]
    action_ids: tuple[str, ...]
    label_ids: tuple[str, ...]
    signature_ids: tuple[str, ...]
    detail: str

    def __post_init__(self) -> None:
        if self.witness_kind not in {
            "LABEL_SET_MISMATCH",
            "WITHIN_STATE_ACTION_ALIAS",
            "CROSS_STATE_LABEL_DYNAMICS_MISMATCH",
            "CANDIDATE_CAP_INSUFFICIENT",
        }:
            raise GeneratedCoordinateInvariantViolation("unknown witness kind")
        _sha(self.partition_id, "witness partition ID")
        for field in (
            "selected_state_program_ids", "selected_action_program_ids", "state_ids",
            "action_ids", "label_ids", "signature_ids",
        ):
            values = getattr(self, field)
            if type(values) is not tuple or any(type(value) is not str for value in values):
                raise GeneratedCoordinateInvariantViolation(f"witness {field} type substitution")
        _text(self.detail, "witness detail")

    def _payload(self) -> dict[str, Any]:
        return {
            "witness_kind": self.witness_kind,
            "partition_id": self.partition_id,
            "selected_state_program_ids": list(self.selected_state_program_ids),
            "selected_action_program_ids": list(self.selected_action_program_ids),
            "state_ids": list(self.state_ids),
            "action_ids": list(self.action_ids),
            "label_ids": list(self.label_ids),
            "signature_ids": list(self.signature_ids),
            "detail": self.detail,
        }

    @property
    def witness_id(self) -> str:
        return _content_id(WITNESS_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "witness_id": self.witness_id}


def _witness(
    kind: str,
    partition: Partition,
    state_ids: tuple[str, ...],
    action_ids: tuple[str, ...],
    states: Iterable[LMBState],
    actions: Iterable[LMBAction],
    labels: Iterable[GeneratedActionLabelV1],
    signatures: Iterable[Any],
    detail: str,
) -> GeneratedWitnessV1:
    return GeneratedWitnessV1(
        kind,
        _partition_id(partition),
        state_ids,
        action_ids,
        tuple(object_id(state, "state") for state in states),
        tuple(object_id(action, "ground-action-source") for action in actions),
        tuple(label.label_id for label in labels),
        tuple(signature.signature_id for signature in signatures),
        detail,
    )


def _audit_candidate(
    kernel: LMBKernel,
    partition: Partition,
    state_program_ids: tuple[str, ...],
    action_programs: tuple[GeneratedExpressionV1, ...],
    signature_cache: Mapping[tuple[LMBState, LMBAction], Any],
) -> tuple[int | None, GeneratedWitnessV1 | None]:
    adapter = GeneratedActionSemanticAdapterV1(action_programs)
    action_program_ids = adapter.selected_program_ids
    entry_count = 0
    for cell in partition.cell_ids:
        active = tuple(
            state for state in partition.members(cell) if state.status is LMBStatus.ACTIVE
        )
        if not active:
            continue
        label_sets = {state: adapter.labels(kernel, state) for state in active}
        reference_state = active[0]
        for state in active[1:]:
            if label_sets[state] != label_sets[reference_state]:
                labels = tuple(
                    sorted(set(label_sets[state]) ^ set(label_sets[reference_state]))
                )
                return None, _witness(
                    "LABEL_SET_MISMATCH", partition, state_program_ids,
                    action_program_ids, (reference_state, state), (), labels, (),
                    "one state cell exposes different generated semantic-label sets",
                )
        reference_signatures: dict[GeneratedActionLabelV1, Any] = {}
        for state in active:
            for label in label_sets[state]:
                actions = tuple(
                    action
                    for action in kernel.actions(state)
                    if adapter.label(kernel, state, action) == label
                )
                signatures = tuple(
                    signature_cache[(state, action)]
                    for action in actions
                )
                if len(set(signatures)) != 1:
                    mismatch_index = next(
                        index
                        for index in range(1, len(signatures))
                        if signatures[index] != signatures[0]
                    )
                    return None, _witness(
                        "WITHIN_STATE_ACTION_ALIAS", partition, state_program_ids,
                        action_program_ids, (state,),
                        (actions[0], actions[mismatch_index]), (label,),
                        (signatures[0], signatures[mismatch_index]),
                        "generated label aliased ground actions before raw-signature equality",
                    )
                signature = signatures[0]
                if state is reference_state:
                    reference_signatures[label] = signature
                elif signature != reference_signatures[label]:
                    return None, _witness(
                        "CROSS_STATE_LABEL_DYNAMICS_MISMATCH", partition,
                        state_program_ids, action_program_ids,
                        (reference_state, state), (), (label,),
                        (reference_signatures[label], signature),
                        "same generated cell/label has different one-step signatures",
                    )
        entry_count += len(label_sets[reference_state])
    return entry_count, None


@dataclass(frozen=True, slots=True)
class GeneratedCandidateV1:
    selected_state_program_ids: tuple[str, ...]
    selected_action_program_ids: tuple[str, ...]
    predicate_tree_id: str
    partition_id: str
    cell_count: int
    active_cell_count: int
    split_count: int
    abstract_entry_count: int | None
    exact_homomorphism: bool
    witness_id: str | None

    def __post_init__(self) -> None:
        if type(self.selected_state_program_ids) is not tuple or type(self.selected_action_program_ids) is not tuple:
            raise GeneratedCoordinateInvariantViolation("candidate program IDs require tuples")
        if tuple(sorted(self.selected_state_program_ids)) != self.selected_state_program_ids or tuple(sorted(self.selected_action_program_ids)) != self.selected_action_program_ids:
            raise GeneratedCoordinateInvariantViolation("candidate program IDs are not sorted")
        for value in self.selected_state_program_ids + self.selected_action_program_ids:
            _sha(value, "candidate program ID")
        _sha(self.predicate_tree_id, "candidate tree ID")
        _sha(self.partition_id, "candidate partition ID")
        _integer(self.cell_count, "candidate cell count", 1)
        _integer(self.active_cell_count, "candidate active cell count", 1)
        _integer(self.split_count, "candidate split count", 0)
        if self.abstract_entry_count is not None:
            _integer(self.abstract_entry_count, "abstract entry count", 1)
        if type(self.exact_homomorphism) is not bool:
            raise GeneratedCoordinateInvariantViolation("candidate exact flag substitution")
        if self.witness_id is not None:
            _sha(self.witness_id, "candidate witness ID")
        if self.exact_homomorphism != (self.witness_id is None) or self.exact_homomorphism != (self.abstract_entry_count is not None):
            raise GeneratedCoordinateInvariantViolation("candidate exact/witness relation invalid")

    def _payload(self) -> dict[str, Any]:
        return {
            "selected_state_program_ids": list(self.selected_state_program_ids),
            "selected_action_program_ids": list(self.selected_action_program_ids),
            "predicate_tree_id": self.predicate_tree_id,
            "partition_id": self.partition_id,
            "cell_count": self.cell_count,
            "active_cell_count": self.active_cell_count,
            "split_count": self.split_count,
            "abstract_entry_count": self.abstract_entry_count,
            "exact_homomorphism": self.exact_homomorphism,
            "witness_id": self.witness_id,
        }

    @property
    def candidate_id(self) -> str:
        return _content_id(CANDIDATE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "candidate_id": self.candidate_id}


@dataclass(frozen=True, slots=True)
class GeneratedCandidateTraceV1:
    spec_id: str
    registry_id: str
    required_candidate_count: int
    evaluated_candidate_count: int
    candidates: tuple[GeneratedCandidateV1, ...]
    witnesses: tuple[GeneratedWitnessV1, ...]
    selected_candidate_id: str | None
    status: GeneratedCoordinateStatus
    schema: str = TRACE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != TRACE_SCHEMA or type(self.status) is not GeneratedCoordinateStatus:
            raise GeneratedCoordinateInvariantViolation("trace schema/status substitution")
        _sha(self.spec_id, "trace spec ID")
        _sha(self.registry_id, "trace registry ID")
        _integer(self.required_candidate_count, "required candidate count", 1)
        _integer(self.evaluated_candidate_count, "evaluated candidate count", 0)
        if type(self.candidates) is not tuple or any(type(item) is not GeneratedCandidateV1 for item in self.candidates):
            raise GeneratedCoordinateInvariantViolation("trace candidate type substitution")
        if type(self.witnesses) is not tuple or any(type(item) is not GeneratedWitnessV1 for item in self.witnesses):
            raise GeneratedCoordinateInvariantViolation("trace witness type substitution")
        if self.evaluated_candidate_count != len(self.candidates):
            raise GeneratedCoordinateInvariantViolation("trace candidate count mismatch")
        if self.status is GeneratedCoordinateStatus.CANDIDATE_CAP_EXHAUSTED:
            if self.candidates or self.selected_candidate_id is not None:
                raise GeneratedCoordinateInvariantViolation("cap trace evaluated/published candidate")
        else:
            if self.required_candidate_count != self.evaluated_candidate_count:
                raise GeneratedCoordinateInvariantViolation("complete trace was truncated")
        if self.selected_candidate_id is not None:
            _sha(self.selected_candidate_id, "selected candidate ID")
            selected = [item for item in self.candidates if item.candidate_id == self.selected_candidate_id]
            if len(selected) != 1 or not selected[0].exact_homomorphism:
                raise GeneratedCoordinateInvariantViolation("selected candidate is not exact/unique")
        if self.status is GeneratedCoordinateStatus.EXACT_GENERATED_HOMOMORPHISM and self.selected_candidate_id is None:
            raise GeneratedCoordinateInvariantViolation("exact trace has no selected candidate")
        if self.status is GeneratedCoordinateStatus.NO_EXACT_GENERATED_HOMOMORPHISM and any(item.exact_homomorphism for item in self.candidates):
            raise GeneratedCoordinateInvariantViolation("negative trace contains exact candidate")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "spec_id": self.spec_id,
            "registry_id": self.registry_id,
            "required_candidate_count": self.required_candidate_count,
            "evaluated_candidate_count": self.evaluated_candidate_count,
            "candidates": [item.to_document() for item in self.candidates],
            "witnesses": [item.to_document() for item in self.witnesses],
            "selected_candidate_id": self.selected_candidate_id,
            "status": self.status.value,
        }

    @property
    def trace_id(self) -> str:
        return _content_id(TRACE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "trace_id": self.trace_id}


@dataclass(frozen=True, slots=True)
class GeneratedCoordinateCertificateV1:
    structural_id: str
    coverage_id: str
    registry_id: str
    spec_id: str
    trace_id: str
    selected_candidate_id: str
    predicate_tree_id: str
    partition_id: str
    portable_model_id: str
    selected_state_program_ids: tuple[str, ...]
    selected_action_program_ids: tuple[str, ...]
    selected_state_program_asts: tuple[GeneratedExpressionV1, ...]
    selected_action_program_asts: tuple[GeneratedExpressionV1, ...]
    ground_state_count: int
    active_ground_state_count: int
    quotient_cell_count: int
    active_quotient_cell_count: int
    abstract_entry_count: int
    complete_candidate_trace: bool = True
    exact_point_envelope: bool = True
    claim_kind: str = CLAIM_KIND
    claim_scope: str = CLAIM_SCOPE
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    workload_economics_gate: str = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    counter_completeness_gate: str = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    sample_efficiency_gate: str = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
    schema: str = CERTIFICATE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != CERTIFICATE_SCHEMA or self.claim_kind != CLAIM_KIND or self.claim_scope != CLAIM_SCOPE:
            raise GeneratedCoordinateInvariantViolation("certificate schema/claim substitution")
        for field in (
            "structural_id", "coverage_id", "registry_id", "spec_id", "trace_id",
            "selected_candidate_id", "predicate_tree_id", "partition_id",
        ):
            _sha(getattr(self, field), f"certificate {field}")
        _text(self.portable_model_id, "portable model ID")
        if type(self.selected_state_program_ids) is not tuple or type(self.selected_action_program_ids) is not tuple:
            raise GeneratedCoordinateInvariantViolation("certificate program IDs require tuples")
        if type(self.selected_state_program_asts) is not tuple or type(self.selected_action_program_asts) is not tuple:
            raise GeneratedCoordinateInvariantViolation("certificate ASTs require tuples")
        if any(type(item) is not GeneratedExpressionV1 for item in self.selected_state_program_asts + self.selected_action_program_asts):
            raise GeneratedCoordinateInvariantViolation("certificate AST type substitution")
        if tuple(item.expression_id for item in self.selected_state_program_asts) != self.selected_state_program_ids or tuple(item.expression_id for item in self.selected_action_program_asts) != self.selected_action_program_ids:
            raise GeneratedCoordinateInvariantViolation("certificate AST/ID mismatch")
        for field in (
            "ground_state_count", "active_ground_state_count", "quotient_cell_count",
            "active_quotient_cell_count", "abstract_entry_count",
        ):
            _integer(getattr(self, field), field, 1)
        if self.complete_candidate_trace is not True or self.exact_point_envelope is not True:
            raise GeneratedCoordinateInvariantViolation("certificate exactness/completeness substitution")
        if self.official_execution_allowed is not False or self.official_scalar_cost is not None or self.official_N_break_even is not None:
            raise GeneratedCoordinateInvariantViolation("certificate official-Gate substitution")
        if (
            self.workload_economics_gate != "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
            or self.counter_completeness_gate != "COUNTER_COMPLETENESS_GATE_NOT_RUN"
            or self.sample_efficiency_gate != "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
        ):
            raise GeneratedCoordinateInvariantViolation("certificate Gate substitution")

    def _payload(self) -> dict[str, Any]:
        return {
            field: (
                list(value)
                if field in {"selected_state_program_ids", "selected_action_program_ids"}
                else [item.to_document() for item in value]
                if field in {"selected_state_program_asts", "selected_action_program_asts"}
                else value
            )
            for field, value in (
                (name, getattr(self, name))
                for name in self.__dataclass_fields__
            )
        }

    @property
    def certificate_id(self) -> str:
        return _content_id(CERTIFICATE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "certificate_id": self.certificate_id}


@dataclass(frozen=True, slots=True)
class GeneratedCoordinateSynthesisResultV1:
    status: GeneratedCoordinateStatus
    registry: GeneratedDSLRegistryV1
    spec: GeneratedSynthesisSpecV1
    trace: GeneratedCandidateTraceV1
    predicate_tree: GeneratedPredicateTreeV1 | None
    partition: Partition | None
    semantic_adapter: GeneratedActionSemanticAdapterV1 | None
    quotient_models: QuotientModels | None
    portable_build: PortableBuildResult | None
    certificate: GeneratedCoordinateCertificateV1 | None

    def __post_init__(self) -> None:
        exact = (
            (self.status, GeneratedCoordinateStatus, "status"),
            (self.registry, GeneratedDSLRegistryV1, "registry"),
            (self.spec, GeneratedSynthesisSpecV1, "spec"),
            (self.trace, GeneratedCandidateTraceV1, "trace"),
        )
        for value, expected, label in exact:
            if type(value) is not expected:
                raise GeneratedCoordinateInvariantViolation(
                    f"result {label} must have exact type {expected.__name__}"
                )
        optional = (
            (self.predicate_tree, GeneratedPredicateTreeV1, "predicate_tree"),
            (self.partition, Partition, "partition"),
            (self.semantic_adapter, GeneratedActionSemanticAdapterV1, "semantic_adapter"),
            (self.quotient_models, QuotientModels, "quotient_models"),
            (self.portable_build, PortableBuildResult, "portable_build"),
            (self.certificate, GeneratedCoordinateCertificateV1, "certificate"),
        )
        for value, expected, label in optional:
            if value is not None and type(value) is not expected:
                raise GeneratedCoordinateInvariantViolation(
                    f"result {label} must have exact type {expected.__name__}"
                )
        published = tuple(value for value, _, _ in optional)
        if self.status is GeneratedCoordinateStatus.EXACT_GENERATED_HOMOMORPHISM:
            if any(value is None for value in published):
                raise GeneratedCoordinateInvariantViolation("exact result is incomplete")
        elif any(value is not None for value in published):
            raise GeneratedCoordinateInvariantViolation("negative result published a model")
        if (
            self.spec.registry_id != self.registry.registry_id
            or self.trace.registry_id != self.registry.registry_id
            or self.trace.spec_id != self.spec.spec_id
            or self.trace.status is not self.status
        ):
            raise GeneratedCoordinateInvariantViolation("result authority-chain mismatch")
        if self.certificate is not None:
            certificate = self.certificate
            if (
                certificate.registry_id != self.registry.registry_id
                or certificate.spec_id != self.spec.spec_id
                or certificate.trace_id != self.trace.trace_id
                or certificate.predicate_tree_id != self.predicate_tree.tree_id
                or certificate.partition_id != _partition_id(self.partition)
                or certificate.portable_model_id != self.portable_build.model.model_id
            ):
                raise GeneratedCoordinateInvariantViolation("certificate authority-chain mismatch")


def _subsets(values: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    return tuple(
        subset
        for size in range(len(values) + 1)
        for subset in combinations(values, size)
    )


def _states(coverage: SuiteBuildCoverage[LMBState]) -> tuple[LMBState, ...]:
    return tuple(sorted(coverage.covered_states, key=repr))


def _state_rows(
    kernel: LMBKernel,
    states: tuple[LMBState, ...],
    programs: tuple[GeneratedExpressionV1, ...],
) -> dict[LMBState, dict[str, Fraction]]:
    return {
        state: {
            program.expression_id: Fraction(
                _eval_expression(program, kernel, state, None)
            )
            for program in programs
        }
        for state in states
        if state.status is LMBStatus.ACTIVE
    }


def _singleton(models: QuotientModels) -> bool:
    return all(
        len(
            {
                (
                    realization.reward_features,
                    realization.successor_probabilities,
                    realization.failure_probability,
                    realization.termination_probability,
                )
                for realization in entry.realizations
            }
        )
        == 1
        for entry in models.envelope.entries
    )


def _candidate_selection_key(
    candidate: GeneratedCandidateV1,
    state_by_id: Mapping[str, GeneratedExpressionV1],
    action_by_id: Mapping[str, GeneratedExpressionV1],
) -> tuple[Any, ...]:
    return (
        len(candidate.selected_state_program_ids),
        len(candidate.selected_action_program_ids),
        candidate.split_count,
        tuple(_ast_selection_key(state_by_id[value]) for value in candidate.selected_state_program_ids),
        tuple(_ast_selection_key(action_by_id[value]) for value in candidate.selected_action_program_ids),
        candidate.selected_state_program_ids,
        candidate.selected_action_program_ids,
        candidate.partition_id,
    )


def _synthesize(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    registry: GeneratedDSLRegistryV1,
    candidate_cap: int,
) -> GeneratedCoordinateSynthesisResultV1:
    if type(kernel) is not LMBKernel or type(coverage) is not SuiteBuildCoverage:
        raise GeneratedCoordinateInvariantViolation(
            "generated synthesis requires exact LMBKernel and SuiteBuildCoverage types"
        )
    if type(registry) is not GeneratedDSLRegistryV1:
        raise GeneratedCoordinateInvariantViolation("generated DSL registry type substitution")
    _validate_implementation_authority()
    canonical_registry = generated_dsl_registry_v1(registry.profile)
    if registry.to_document() != canonical_registry.to_document():
        raise GeneratedCoordinateInvariantViolation("generated DSL registry is noncanonical")
    states = _states(coverage)
    if not states or any(type(state) is not LMBState for state in states):
        raise GeneratedCoordinateInvariantViolation("coverage contains invalid LMB states")
    spec = GeneratedSynthesisSpecV1(
        _structural_id(kernel),
        _coverage_id(coverage),
        registry.registry_id,
        registry.profile,
        candidate_cap,
    )
    rows = _state_rows(kernel, states, registry.state_programs)
    state_ids = tuple(item.expression_id for item in registry.state_programs)
    action_ids = tuple(item.expression_id for item in registry.action_programs)
    state_by_id = {item.expression_id: item for item in registry.state_programs}
    action_by_id = {item.expression_id: item for item in registry.action_programs}
    state_subsets = _subsets(state_ids)
    action_subsets = _subsets(action_ids)
    required = len(state_subsets) * len(action_subsets)
    if required > candidate_cap:
        not_evaluated = _content_id(PARTITION_DOMAIN, {"kind": "NOT_EVALUATED_CAP"})
        witness = GeneratedWitnessV1(
            "CANDIDATE_CAP_INSUFFICIENT", not_evaluated, (), (), (), (), (), (),
            f"required={required};cap={candidate_cap}",
        )
        trace = GeneratedCandidateTraceV1(
            spec.spec_id, registry.registry_id, required, 0, (), (witness,), None,
            GeneratedCoordinateStatus.CANDIDATE_CAP_EXHAUSTED,
        )
        return GeneratedCoordinateSynthesisResultV1(
            GeneratedCoordinateStatus.CANDIDATE_CAP_EXHAUSTED,
            registry, spec, trace, None, None, None, None, None, None,
        )

    candidates: list[GeneratedCandidateV1] = []
    witnesses: dict[str, GeneratedWitnessV1] = {}
    exact_candidates: list[GeneratedCandidateV1] = []
    runtime: dict[
        str, tuple[GeneratedPredicateTreeV1, Partition, GeneratedActionSemanticAdapterV1]
    ] = {}
    for state_subset in state_subsets:
        tree, partition = _compile_partition(states, rows, state_subset)
        signature_cache = {
            (state, action): _direct._ground_signature(
                kernel, partition, state, action
            )
            for state in states
            if state.status is LMBStatus.ACTIVE
            for action in kernel.actions(state)
        }
        for action_subset in action_subsets:
            action_programs = tuple(action_by_id[value] for value in action_subset)
            entry_count, witness = _audit_candidate(
                kernel, partition, state_subset, action_programs, signature_cache
            )
            if witness is not None:
                witnesses[witness.witness_id] = witness
            candidate = GeneratedCandidateV1(
                state_subset, action_subset, tree.tree_id, tree.partition_id,
                tree.cell_count, tree.active_cell_count, len(tree.splits), entry_count,
                witness is None, None if witness is None else witness.witness_id,
            )
            candidates.append(candidate)
            if witness is None:
                exact_candidates.append(candidate)
                runtime[candidate.candidate_id] = (
                    tree, partition, GeneratedActionSemanticAdapterV1(action_programs)
                )

    witness_tuple = tuple(sorted(witnesses.values(), key=lambda item: item.witness_id))
    if not exact_candidates:
        trace = GeneratedCandidateTraceV1(
            spec.spec_id, registry.registry_id, required, len(candidates),
            tuple(candidates), witness_tuple, None,
            GeneratedCoordinateStatus.NO_EXACT_GENERATED_HOMOMORPHISM,
        )
        return GeneratedCoordinateSynthesisResultV1(
            GeneratedCoordinateStatus.NO_EXACT_GENERATED_HOMOMORPHISM,
            registry, spec, trace, None, None, None, None, None, None,
        )

    selected = min(
        exact_candidates,
        key=lambda item: _candidate_selection_key(item, state_by_id, action_by_id),
    )
    tree, partition, adapter = runtime[selected.candidate_id]
    trace = GeneratedCandidateTraceV1(
        spec.spec_id, registry.registry_id, required, len(candidates),
        tuple(candidates), witness_tuple, selected.candidate_id,
        GeneratedCoordinateStatus.EXACT_GENERATED_HOMOMORPHISM,
    )
    models = build_quotient_models(kernel, states, partition, semantic_adapter=adapter)
    if not _singleton(models):
        raise GeneratedCoordinateInvariantViolation(
            "exact audit produced a non-singleton realization envelope"
        )
    portable = _direct._portable(kernel, coverage, models)
    certificate = GeneratedCoordinateCertificateV1(
        spec.structural_id,
        spec.coverage_id,
        registry.registry_id,
        spec.spec_id,
        trace.trace_id,
        selected.candidate_id,
        tree.tree_id,
        tree.partition_id,
        portable.model.model_id,
        selected.selected_state_program_ids,
        selected.selected_action_program_ids,
        tuple(state_by_id[value] for value in selected.selected_state_program_ids),
        tuple(action_by_id[value] for value in selected.selected_action_program_ids),
        len(states),
        sum(state.status is LMBStatus.ACTIVE for state in states),
        len(partition.cell_ids),
        tree.active_cell_count,
        len(models.envelope.entries),
    )
    return GeneratedCoordinateSynthesisResultV1(
        GeneratedCoordinateStatus.EXACT_GENERATED_HOMOMORPHISM,
        registry, spec, trace, tree, partition, adapter, models, portable, certificate,
    )


def synthesize_generated_lmb_homomorphism_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
) -> GeneratedCoordinateSynthesisResultV1:
    """Production API: exhaustive generated-program synthesis in the fixed DSL."""

    if type(kernel) is not LMBKernel or type(coverage) is not SuiteBuildCoverage:
        raise GeneratedCoordinateInvariantViolation(
            "production API requires exact LMBKernel and SuiteBuildCoverage types"
        )
    return _synthesize(
        kernel,
        coverage,
        generated_dsl_registry_v1(),
        PRODUCTION_CANDIDATE_CAP,
    )


def run_generated_lmb_control_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    *,
    control: str,
) -> GeneratedCoordinateSynthesisResultV1:
    """Non-production cap and no-action controls; never a production authority."""

    if type(kernel) is not LMBKernel or type(coverage) is not SuiteBuildCoverage:
        raise GeneratedCoordinateInvariantViolation(
            "control API requires exact LMBKernel and SuiteBuildCoverage types"
        )
    if control == "candidate_cap_one":
        return _synthesize(kernel, coverage, generated_dsl_registry_v1(), 1)
    if control == "state_only_no_action_programs":
        return _synthesize(
            kernel,
            coverage,
            generated_dsl_registry_v1(CONTROL_PROFILE),
            PRODUCTION_CANDIDATE_CAP,
        )
    raise GeneratedCoordinateInvariantViolation("unknown generated-coordinate control")


def verify_generated_lmb_homomorphism_v1(
    kernel: LMBKernel,
    coverage: SuiteBuildCoverage[LMBState],
    result: GeneratedCoordinateSynthesisResultV1,
) -> tuple[str, ...]:
    """Independent rebuild verifier; no nested result assertion is trusted."""

    if type(kernel) is not LMBKernel or type(coverage) is not SuiteBuildCoverage:
        raise GeneratedCoordinateInvariantViolation(
            "verifier requires exact LMBKernel and SuiteBuildCoverage types"
        )
    if type(result) is not GeneratedCoordinateSynthesisResultV1:
        raise GeneratedCoordinateInvariantViolation("verifier rejects duck result types")
    if result.registry.profile != DSL_PROFILE or result.spec.candidate_cap != PRODUCTION_CANDIDATE_CAP:
        raise GeneratedCoordinateInvariantViolation("production verifier rejects control provenance")
    _validate_implementation_authority()
    expected = synthesize_generated_lmb_homomorphism_v1(kernel, coverage)
    failures: list[str] = []
    comparisons = (
        ("STATUS_MISMATCH", result.status, expected.status),
        ("REGISTRY_MISMATCH", result.registry.to_document(), expected.registry.to_document()),
        ("SPEC_MISMATCH", result.spec.to_document(), expected.spec.to_document()),
        ("TRACE_MISMATCH", result.trace.to_document(), expected.trace.to_document()),
        (
            "TREE_MISMATCH",
            None if result.predicate_tree is None else result.predicate_tree.to_document(),
            None if expected.predicate_tree is None else expected.predicate_tree.to_document(),
        ),
        ("PARTITION_MISMATCH", result.partition, expected.partition),
        ("ACTION_LABEL_PROGRAM_MISMATCH", result.semantic_adapter, expected.semantic_adapter),
        ("QUOTIENT_MODEL_MISMATCH", result.quotient_models, expected.quotient_models),
        (
            "PORTABLE_MODEL_MISMATCH",
            None if result.portable_build is None else result.portable_build.model.to_dict(),
            None if expected.portable_build is None else expected.portable_build.model.to_dict(),
        ),
        (
            "CERTIFICATE_MISMATCH",
            None if result.certificate is None else result.certificate.to_document(),
            None if expected.certificate is None else expected.certificate.to_document(),
        ),
    )
    for code, actual, rebuilt in comparisons:
        if actual != rebuilt:
            failures.append(code)
    return tuple(failures)
