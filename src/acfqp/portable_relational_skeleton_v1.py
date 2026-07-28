"""Domain-neutral relational program-shape synthesis.

The module deliberately knows nothing about graph merge, G2048, matching
buffers, tiles, vertices, target queries, planners, or kernels.  Domain
adapters compile observations into the typed roles below:

``legal_actions``
    the complete action catalogue visible at one observed state;
``active_resources``
    the resources currently active in that state;
``action_anchor``
    the relational focus of one action; and
``linked``
    a preregistered anchor-to-resource relation.

The source-only producer closes the complete depth-two grammar, semantically
deduplicates it on an anonymous exact observation log, exhausts every
compressive integer state/action pair, and exports only the selected operator
trees plus a support-key schema.  Source transition rows and the complete
program registry are not transported.

Target refinement is a separate operation.  It regenerates a fresh registry
from the frozen grammar and the currently authorized target slice.  Its API
does not accept a source registry, source candidate ranking, target kernel, or
query.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from itertools import product
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "portable_relational_skeleton_v1"
MAX_PROGRAM_DEPTH = 2
MAX_HORIZON = 2

DOMAIN_TAGS = {
    "schema": "acfqp:portable-relational-role-schema:v1",
    "action": "acfqp:portable-relational-action-slot:v1",
    "state": "acfqp:portable-relational-state-ir:v1",
    "outcome": "acfqp:portable-relational-outcome-ir:v1",
    "row": "acfqp:portable-relational-observed-row:v1",
    "log": "acfqp:portable-relational-anonymous-log:v1",
    "program": "acfqp:portable-relational-program:v1",
    "registry": "acfqp:portable-relational-program-registry:v1",
    "support_schema": "acfqp:portable-relational-support-schema:v1",
    "proposal": "acfqp:portable-relational-skeleton:v1",
    "metrics": "acfqp:portable-relational-synthesis-metrics:v1",
    "failed_proof": "acfqp:portable-relational-failed-proof-ref:v1",
    "target_generation": "acfqp:portable-relational-target-generation:v1",
}


class PortableRelationalInvariantViolation(ValueError):
    """A typed IR, grammar, proposal, or replay invariant failed."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise PortableRelationalInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise PortableRelationalInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _exact_tuple(
    value: Any,
    item_type: type,
    field: str,
) -> tuple[Any, ...]:
    if type(value) is not tuple or any(type(item) is not item_type for item in value):
        raise PortableRelationalInvariantViolation(
            f"{field} rejects nested runtime substitutions"
        )
    return value


@dataclass(frozen=True, slots=True)
class PortableRelationalRoleSchemaV1:
    """The only ontology visible to the generic producer."""

    legal_action_role: str = "legal_actions"
    active_resource_role: str = "active_resources"
    all_resource_role: str = "all_resources"
    action_anchor_role: str = "action_anchor"
    linked_relation_role: str = "linked"
    resource_attribute_role: str = "resource_attribute"
    max_program_depth: int = MAX_PROGRAM_DEPTH

    def __post_init__(self) -> None:
        if (
            type(self.legal_action_role) is not str
            or type(self.active_resource_role) is not str
            or type(self.all_resource_role) is not str
            or type(self.action_anchor_role) is not str
            or type(self.linked_relation_role) is not str
            or type(self.resource_attribute_role) is not str
            or type(self.max_program_depth) is not int
            or
            self.legal_action_role != "legal_actions"
            or self.active_resource_role != "active_resources"
            or self.all_resource_role != "all_resources"
            or self.action_anchor_role != "action_anchor"
            or self.linked_relation_role != "linked"
            or self.resource_attribute_role != "resource_attribute"
            or self.max_program_depth != MAX_PROGRAM_DEPTH
        ):
            raise PortableRelationalInvariantViolation(
                "portable relational role schema changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_relational_role_schema.v1",
            "schema_version": SCHEMA_VERSION,
            "roles": {
                "legal_actions": self.legal_action_role,
                "active_resources": self.active_resource_role,
                "all_resources": self.all_resource_role,
                "action_anchor": self.action_anchor_role,
                "linked": self.linked_relation_role,
                "resource_attribute": self.resource_attribute_role,
            },
            "max_program_depth": self.max_program_depth,
        }

    @property
    def role_schema_id(self) -> str:
        return _content_id("schema", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "role_schema_id": self.role_schema_id}


@dataclass(frozen=True, slots=True)
class RelationalActionSlotV1:
    """One opaque action and its adapter-declared relational anchor."""

    opaque_action_key: str
    anchor: int

    def __post_init__(self) -> None:
        if (
            type(self.opaque_action_key) is not str
            or not self.opaque_action_key
            or type(self.anchor) is not int
            or self.anchor < 0
        ):
            raise PortableRelationalInvariantViolation(
                "relational action slot is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_relational_action_slot.v1",
            "schema_version": SCHEMA_VERSION,
            "opaque_action_key": self.opaque_action_key,
            "anchor": self.anchor,
        }

    @property
    def action_slot_id(self) -> str:
        return _content_id("action", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "action_slot_id": self.action_slot_id}


@dataclass(frozen=True, slots=True)
class RelationalStateIRV1:
    """Lossless data-only covariates used by portable programs."""

    structural_context_id: str
    remaining_horizon: int
    resource_attributes: tuple[int, ...]
    active_resources: tuple[int, ...]
    linked_pairs: tuple[tuple[int, int], ...]
    legal_actions: tuple[RelationalActionSlotV1, ...]
    terminal_kind: str = "ACTIVE"

    def __post_init__(self) -> None:
        _cid(self.structural_context_id, "relational state structural context")
        if (
            type(self.remaining_horizon) is not int
            or not 0 <= self.remaining_horizon <= MAX_HORIZON
            or type(self.resource_attributes) is not tuple
            or not self.resource_attributes
            or any(type(item) is not int for item in self.resource_attributes)
            or type(self.active_resources) is not tuple
            or self.active_resources
            != tuple(sorted(set(self.active_resources)))
            or any(
                type(item) is not int
                or not 0 <= item < len(self.resource_attributes)
                for item in self.active_resources
            )
            or type(self.linked_pairs) is not tuple
            or self.linked_pairs != tuple(sorted(set(self.linked_pairs)))
            or any(
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not int
                or not 0 <= item[0] < len(self.resource_attributes)
                or type(item[1]) is not int
                or not 0 <= item[1] < len(self.resource_attributes)
                for item in self.linked_pairs
            )
            or type(self.legal_actions) is not tuple
            or any(
                type(item) is not RelationalActionSlotV1
                for item in self.legal_actions
            )
            or tuple(item.action_slot_id for item in self.legal_actions)
            != tuple(
                sorted(
                    {item.action_slot_id for item in self.legal_actions}
                )
            )
            or len(
                {item.opaque_action_key for item in self.legal_actions}
            )
            != len(self.legal_actions)
            or any(
                item.anchor not in self.active_resources
                for item in self.legal_actions
            )
            or self.terminal_kind not in (
                "ACTIVE",
                "FAILURE",
                "SUCCESS",
                "HORIZON_TERMINAL",
            )
            or (
                self.terminal_kind != "ACTIVE"
                and self.legal_actions
            )
            or (
                self.terminal_kind == "ACTIVE"
                and (
                    self.remaining_horizon == 0
                    or not self.legal_actions
                )
            )
        ):
            raise PortableRelationalInvariantViolation(
                "portable relational state IR is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_relational_state_ir.v1",
            "schema_version": SCHEMA_VERSION,
            "structural_context_id": self.structural_context_id,
            "remaining_horizon": self.remaining_horizon,
            "resource_attributes": list(self.resource_attributes),
            "active_resources": list(self.active_resources),
            "linked_pairs": [list(item) for item in self.linked_pairs],
            "legal_actions": [
                item.to_document() for item in self.legal_actions
            ],
            "terminal_kind": self.terminal_kind,
        }

    @property
    def state_ir_id(self) -> str:
        return _content_id("state", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "state_ir_id": self.state_ir_id}


@dataclass(frozen=True, slots=True)
class RelationalOutcomeIRV1:
    next_state: RelationalStateIRV1
    probability: Fraction
    normalized_reward: Fraction
    failure: bool
    terminal: bool

    def __post_init__(self) -> None:
        if (
            type(self.next_state) is not RelationalStateIRV1
            or type(self.probability) is not Fraction
            or not 0 < self.probability <= 1
            or type(self.normalized_reward) is not Fraction
            or not 0 <= self.normalized_reward <= 1
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
            or self.failure != (
                self.next_state.terminal_kind == "FAILURE"
            )
            or (
                self.terminal
                != (self.next_state.terminal_kind != "ACTIVE")
            )
        ):
            raise PortableRelationalInvariantViolation(
                "portable relational outcome IR is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_relational_outcome_ir.v1",
            "schema_version": SCHEMA_VERSION,
            "next_state": self.next_state.to_document(),
            "probability": _fdoc(self.probability),
            "normalized_reward": _fdoc(self.normalized_reward),
            "failure": self.failure,
            "terminal": self.terminal,
        }

    @property
    def outcome_ir_id(self) -> str:
        return _content_id("outcome", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "outcome_ir_id": self.outcome_ir_id}


@dataclass(frozen=True, slots=True)
class RelationalObservedRowV1:
    state: RelationalStateIRV1
    action: RelationalActionSlotV1
    outcomes: tuple[RelationalOutcomeIRV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.state) is not RelationalStateIRV1
            or type(self.action) is not RelationalActionSlotV1
            or self.action not in self.state.legal_actions
            or self.state.terminal_kind != "ACTIVE"
            or self.state.remaining_horizon <= 0
            or type(self.outcomes) is not tuple
            or not self.outcomes
            or any(
                type(item) is not RelationalOutcomeIRV1
                or item.next_state.structural_context_id
                != self.state.structural_context_id
                or item.next_state.remaining_horizon
                != self.state.remaining_horizon - 1
                for item in self.outcomes
            )
            or sum(
                (item.probability for item in self.outcomes),
                Fraction(0),
            )
            != 1
            or tuple(item.outcome_ir_id for item in self.outcomes)
            != tuple(
                sorted(
                    {item.outcome_ir_id for item in self.outcomes}
                )
            )
        ):
            raise PortableRelationalInvariantViolation(
                "portable relational observed row is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_relational_observed_row.v1",
            "schema_version": SCHEMA_VERSION,
            "state": self.state.to_document(),
            "action": self.action.to_document(),
            "outcomes": [item.to_document() for item in self.outcomes],
        }

    @property
    def observed_row_id(self) -> str:
        return _content_id("row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "observed_row_id": self.observed_row_id}


@dataclass(frozen=True, slots=True)
class AnonymousRelationalObservationLogV1:
    role_schema: PortableRelationalRoleSchemaV1
    rows: tuple[RelationalObservedRowV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.role_schema) is not PortableRelationalRoleSchemaV1
            or type(self.rows) is not tuple
            or not self.rows
            or any(type(item) is not RelationalObservedRowV1 for item in self.rows)
            or tuple(item.observed_row_id for item in self.rows)
            != tuple(sorted({item.observed_row_id for item in self.rows}))
        ):
            raise PortableRelationalInvariantViolation(
                "anonymous relational observation log is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_relational_anonymous_log.v1",
            "schema_version": SCHEMA_VERSION,
            "role_schema": self.role_schema.to_document(),
            "rows": [item.to_document() for item in self.rows],
        }

    @property
    def observation_log_id(self) -> str:
        return _content_id("log", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "observation_log_id": self.observation_log_id,
        }


def _validate_complete_source_action_coverage(
    log: AnonymousRelationalObservationLogV1,
) -> None:
    """Require one and only one exact row for every declared source action."""

    rows_by_state: dict[
        str,
        list[RelationalObservedRowV1],
    ] = defaultdict(list)
    for row in log.rows:
        rows_by_state[row.state.state_ir_id].append(row)
    for rows in rows_by_state.values():
        state = rows[0].state
        claimed = tuple(
            sorted(item.action.action_slot_id for item in rows)
        )
        expected = tuple(
            item.action_slot_id for item in state.legal_actions
        )
        if claimed != expected:
            raise PortableRelationalInvariantViolation(
                "source synthesis requires complete exact action-row coverage"
            )


class RelationalProgramContext(str, Enum):
    STATE = "STATE"
    STATE_ACTION = "STATE_ACTION"


class RelationalProgramType(str, Enum):
    RESOURCE_SET = "RESOURCE_SET"
    ACTION_SET = "ACTION_SET"
    ANCHOR = "ANCHOR"
    INTEGER = "INTEGER"
    SIGNATURE = "SIGNATURE"


_PRIMITIVES: dict[
    str,
    tuple[RelationalProgramType, RelationalProgramContext],
] = {
    "all_resources": (
        RelationalProgramType.RESOURCE_SET,
        RelationalProgramContext.STATE,
    ),
    "active_resources": (
        RelationalProgramType.RESOURCE_SET,
        RelationalProgramContext.STATE,
    ),
    "legal_actions": (
        RelationalProgramType.ACTION_SET,
        RelationalProgramContext.STATE,
    ),
    "action_anchor": (
        RelationalProgramType.ANCHOR,
        RelationalProgramContext.STATE_ACTION,
    ),
    "active_attribute_degree_signature": (
        RelationalProgramType.SIGNATURE,
        RelationalProgramContext.STATE,
    ),
}

_OPERATORS: dict[
    str,
    tuple[tuple[RelationalProgramType, ...], RelationalProgramType],
] = {
    "cardinality_resources": (
        (RelationalProgramType.RESOURCE_SET,),
        RelationalProgramType.INTEGER,
    ),
    "cardinality_actions": (
        (RelationalProgramType.ACTION_SET,),
        RelationalProgramType.INTEGER,
    ),
    "linked_filter": (
        (
            RelationalProgramType.ANCHOR,
            RelationalProgramType.RESOURCE_SET,
        ),
        RelationalProgramType.RESOURCE_SET,
    ),
    "set_difference": (
        (
            RelationalProgramType.RESOURCE_SET,
            RelationalProgramType.RESOURCE_SET,
        ),
        RelationalProgramType.RESOURCE_SET,
    ),
}

_OPERATION_ORDER = tuple(_PRIMITIVES) + tuple(_OPERATORS)


@dataclass(frozen=True, slots=True)
class PortableRelationalProgramV1:
    operation: str
    result_type: RelationalProgramType
    context: RelationalProgramContext
    arguments: tuple["PortableRelationalProgramV1", ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.operation) is not str
            or type(self.result_type) is not RelationalProgramType
            or type(self.context) is not RelationalProgramContext
        ):
            raise PortableRelationalInvariantViolation(
                "portable program rejects runtime type substitutions"
            )
        _exact_tuple(
            self.arguments,
            PortableRelationalProgramV1,
            "portable program arguments",
        )
        primitive = _PRIMITIVES.get(self.operation)
        if primitive is not None:
            if self.arguments or primitive != (self.result_type, self.context):
                raise PortableRelationalInvariantViolation(
                    "portable primitive type/context mismatch"
                )
            return
        operator = _OPERATORS.get(self.operation)
        if operator is None:
            raise PortableRelationalInvariantViolation(
                "portable program operation is unregistered"
            )
        expected_context = (
            RelationalProgramContext.STATE_ACTION
            if any(
                item.context is RelationalProgramContext.STATE_ACTION
                for item in self.arguments
            )
            else RelationalProgramContext.STATE
        )
        if (
            tuple(item.result_type for item in self.arguments)
            != operator[0]
            or self.result_type is not operator[1]
            or self.context is not expected_context
            or self.depth > MAX_PROGRAM_DEPTH
        ):
            raise PortableRelationalInvariantViolation(
                "portable operator type/context/depth mismatch"
            )

    @property
    def depth(self) -> int:
        return (
            0
            if not self.arguments
            else 1 + max(item.depth for item in self.arguments)
        )

    @property
    def node_count(self) -> int:
        return 1 + sum(item.node_count for item in self.arguments)

    @property
    def rendered(self) -> str:
        if not self.arguments:
            return self.operation
        return (
            f"{self.operation}("
            + ",".join(item.rendered for item in self.arguments)
            + ")"
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_relational_program.v1",
            "schema_version": SCHEMA_VERSION,
            "operation": self.operation,
            "result_type": self.result_type.value,
            "context": self.context.value,
            "arguments": [item.to_document() for item in self.arguments],
        }

    @property
    def program_id(self) -> str:
        return _content_id("program", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "program_id": self.program_id}


def _program_order_key(
    program: PortableRelationalProgramV1,
) -> tuple[Any, ...]:
    return (
        program.node_count,
        program.depth,
        _OPERATION_ORDER.index(program.operation),
        program.rendered,
        program.program_id,
    )


def _primitive(operation: str) -> PortableRelationalProgramV1:
    result_type, context = _PRIMITIVES[operation]
    return PortableRelationalProgramV1(
        operation,
        result_type,
        context,
    )


def _operator(
    operation: str,
    arguments: tuple[PortableRelationalProgramV1, ...],
) -> PortableRelationalProgramV1:
    context = (
        RelationalProgramContext.STATE_ACTION
        if any(
            item.context is RelationalProgramContext.STATE_ACTION
            for item in arguments
        )
        else RelationalProgramContext.STATE
    )
    return PortableRelationalProgramV1(
        operation,
        _OPERATORS[operation][1],
        context,
        arguments,
    )


def syntactic_portable_program_closure_v1(
) -> tuple[PortableRelationalProgramV1, ...]:
    """Return the complete registered grammar closure through depth two."""

    known = {
        item.program_id: item
        for item in (_primitive(name) for name in _PRIMITIVES)
    }
    for target_depth in range(1, MAX_PROGRAM_DEPTH + 1):
        prior = tuple(known.values())
        by_type: dict[
            RelationalProgramType,
            tuple[PortableRelationalProgramV1, ...],
        ] = {}
        for result_type in RelationalProgramType:
            by_type[result_type] = tuple(
                item for item in prior if item.result_type is result_type
            )
        generated: list[PortableRelationalProgramV1] = []
        for operation, (argument_types, _) in _OPERATORS.items():
            domains = tuple(by_type[item] for item in argument_types)
            for arguments in product(*domains):
                candidate = _operator(operation, tuple(arguments))
                if candidate.depth == target_depth:
                    generated.append(candidate)
        for item in generated:
            known[item.program_id] = item
    return tuple(sorted(known.values(), key=_program_order_key))


def _linked_resources(
    state: RelationalStateIRV1,
    anchor: int,
) -> frozenset[int]:
    return frozenset(
        resource
        for relation_anchor, resource in state.linked_pairs
        if relation_anchor == anchor
    )


def _evaluate(
    program: PortableRelationalProgramV1,
    state: RelationalStateIRV1,
    action: RelationalActionSlotV1 | None,
) -> Any:
    operation = program.operation
    if operation == "all_resources":
        return frozenset(range(len(state.resource_attributes)))
    if operation == "active_resources":
        return frozenset(state.active_resources)
    if operation == "legal_actions":
        return state.legal_actions
    if operation == "action_anchor":
        if action is None:
            raise PortableRelationalInvariantViolation(
                "action-context program lacks an action"
            )
        return action.anchor
    if operation == "active_attribute_degree_signature":
        if not state.active_resources:
            return ()
        active_attributes = tuple(
            state.resource_attributes[item]
            for item in state.active_resources
        )
        minimum = min(active_attributes)
        return tuple(
            sorted(
                (
                    state.resource_attributes[resource] - minimum,
                    sum(
                        relation_resource in state.active_resources
                        for relation_anchor, relation_resource
                        in state.linked_pairs
                        if relation_anchor == resource
                    ),
                )
                for resource in state.active_resources
            )
        )
    values = tuple(_evaluate(item, state, action) for item in program.arguments)
    if operation == "cardinality_resources":
        if type(values[0]) is not frozenset:
            raise PortableRelationalInvariantViolation(
                "resource cardinality received a non-resource set"
            )
        return len(values[0])
    if operation == "cardinality_actions":
        if type(values[0]) is not tuple:
            raise PortableRelationalInvariantViolation(
                "action cardinality received a non-action set"
            )
        return len(values[0])
    if operation == "linked_filter":
        anchor, resources = values
        if type(anchor) is not int or type(resources) is not frozenset:
            raise PortableRelationalInvariantViolation(
                "linked_filter runtime types changed"
            )
        return _linked_resources(state, anchor) & resources
    if operation == "set_difference":
        left, right = values
        if type(left) is not frozenset or type(right) is not frozenset:
            raise PortableRelationalInvariantViolation(
                "set_difference runtime types changed"
            )
        return left - right
    raise PortableRelationalInvariantViolation(
        "portable evaluator reached an unregistered operation"
    )


def evaluate_portable_state_program_v1(
    program: PortableRelationalProgramV1,
    state: RelationalStateIRV1,
) -> tuple[str, Any]:
    if (
        type(program) is not PortableRelationalProgramV1
        or type(state) is not RelationalStateIRV1
        or program.context is not RelationalProgramContext.STATE
    ):
        raise PortableRelationalInvariantViolation(
            "portable state-program binding is invalid"
        )
    value = _evaluate(program, state, None)
    if program.result_type is RelationalProgramType.INTEGER and type(value) is int:
        return ("INTEGER", value)
    if (
        program.result_type is RelationalProgramType.SIGNATURE
        and type(value) is tuple
    ):
        return ("SIGNATURE", value)
    if (
        program.result_type is RelationalProgramType.RESOURCE_SET
        and type(value) is frozenset
    ):
        return ("RESOURCE_SET", tuple(sorted(value)))
    if (
        program.result_type is RelationalProgramType.ACTION_SET
        and type(value) is tuple
    ):
        return (
            "ACTION_SET",
            tuple(item.action_slot_id for item in value),
        )
    raise PortableRelationalInvariantViolation(
        "portable state program produced an invalid value"
    )


def evaluate_portable_action_program_v1(
    program: PortableRelationalProgramV1,
    state: RelationalStateIRV1,
    action: RelationalActionSlotV1,
) -> tuple[str, Any]:
    if (
        type(program) is not PortableRelationalProgramV1
        or type(state) is not RelationalStateIRV1
        or type(action) is not RelationalActionSlotV1
        or program.context is not RelationalProgramContext.STATE_ACTION
        or action not in state.legal_actions
    ):
        raise PortableRelationalInvariantViolation(
            "portable action-program binding is invalid"
        )
    value = _evaluate(program, state, action)
    if program.result_type is RelationalProgramType.INTEGER and type(value) is int:
        return ("INTEGER", value)
    if (
        program.result_type is RelationalProgramType.RESOURCE_SET
        and type(value) is frozenset
    ):
        return ("RESOURCE_SET", tuple(sorted(value)))
    if program.result_type is RelationalProgramType.ANCHOR and type(value) is int:
        return ("ANCHOR", value)
    raise PortableRelationalInvariantViolation(
        "portable action program produced an invalid value"
    )


def _semantic_signature(
    program: PortableRelationalProgramV1,
    log: AnonymousRelationalObservationLogV1,
) -> tuple[Any, ...]:
    states: dict[str, RelationalStateIRV1] = {}
    for row in log.rows:
        states[row.state.state_ir_id] = row.state
        for outcome in row.outcomes:
            states[outcome.next_state.state_ir_id] = outcome.next_state
    if program.context is RelationalProgramContext.STATE:
        return tuple(
            (
                state_id,
                evaluate_portable_state_program_v1(program, state),
            )
            for state_id, state in sorted(states.items())
        )
    return tuple(
        (
            row.observed_row_id,
            evaluate_portable_action_program_v1(
                program,
                row.state,
                row.action,
            ),
        )
        for row in log.rows
    )


@dataclass(frozen=True, slots=True)
class PortableRelationalProgramRegistryV1:
    role_schema_id: str
    observation_log_id: str
    syntactic_program_count: int
    programs: tuple[PortableRelationalProgramV1, ...]
    semantic_program_count_by_depth: tuple[int, ...]

    def __post_init__(self) -> None:
        _cid(self.role_schema_id, "registry role schema")
        _cid(self.observation_log_id, "registry observation log")
        if (
            self.role_schema_id
            != PortableRelationalRoleSchemaV1().role_schema_id
            or
            type(self.syntactic_program_count) is not int
            or self.syntactic_program_count <= 0
            or type(self.programs) is not tuple
            or not self.programs
            or any(
                type(item) is not PortableRelationalProgramV1
                for item in self.programs
            )
            or tuple(item.program_id for item in self.programs)
            != tuple(sorted(
                {item.program_id for item in self.programs},
                key=lambda item: next(
                    _program_order_key(program)
                    for program in self.programs
                    if program.program_id == item
                ),
            ))
            or type(self.semantic_program_count_by_depth) is not tuple
            or len(self.semantic_program_count_by_depth)
            != MAX_PROGRAM_DEPTH + 1
            or sum(self.semantic_program_count_by_depth)
            != len(self.programs)
        ):
            raise PortableRelationalInvariantViolation(
                "portable program registry is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_relational_program_registry.v1",
            "schema_version": SCHEMA_VERSION,
            "role_schema_id": self.role_schema_id,
            "observation_log_id": self.observation_log_id,
            "syntactic_program_count": self.syntactic_program_count,
            "programs": [item.to_document() for item in self.programs],
            "semantic_program_count_by_depth": list(
                self.semantic_program_count_by_depth
            ),
        }

    @property
    def registry_id(self) -> str:
        return _content_id("registry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registry_id": self.registry_id}


def generate_portable_relational_program_registry_v1(
    log: AnonymousRelationalObservationLogV1,
) -> PortableRelationalProgramRegistryV1:
    if type(log) is not AnonymousRelationalObservationLogV1:
        raise PortableRelationalInvariantViolation(
            "portable closure requires the exact anonymous log type"
        )
    syntactic = syntactic_portable_program_closure_v1()
    retained: list[PortableRelationalProgramV1] = []
    seen: dict[tuple[Any, ...], PortableRelationalProgramV1] = {}
    for program in syntactic:
        signature = (
            program.context.value,
            program.result_type.value,
            _semantic_signature(program, log),
        )
        if signature not in seen:
            seen[signature] = program
            retained.append(program)
    retained_tuple = tuple(sorted(retained, key=_program_order_key))
    depth_counts = tuple(
        sum(item.depth == depth for item in retained_tuple)
        for depth in range(MAX_PROGRAM_DEPTH + 1)
    )
    return PortableRelationalProgramRegistryV1(
        log.role_schema.role_schema_id,
        log.observation_log_id,
        len(syntactic),
        retained_tuple,
        depth_counts,
    )


@dataclass(frozen=True, slots=True)
class PortableRelationalSupportSchemaV1:
    fields: tuple[str, ...] = (
        "remaining_horizon",
        "state_coordinate",
        "action_coordinate",
    )
    destination_fields: tuple[str, ...] = (
        "terminal_kind",
        "remaining_horizon",
        "state_coordinate",
    )

    def __post_init__(self) -> None:
        if (
            type(self.fields) is not tuple
            or type(self.destination_fields) is not tuple
            or
            self.fields
            != (
                "remaining_horizon",
                "state_coordinate",
                "action_coordinate",
            )
            or self.destination_fields
            != (
                "terminal_kind",
                "remaining_horizon",
                "state_coordinate",
            )
        ):
            raise PortableRelationalInvariantViolation(
                "portable support schema changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_relational_support_schema.v1",
            "schema_version": SCHEMA_VERSION,
            "fields": list(self.fields),
            "destination_fields": list(self.destination_fields),
        }

    @property
    def support_schema_id(self) -> str:
        return _content_id("support_schema", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "support_schema_id": self.support_schema_id,
        }


@dataclass(frozen=True, slots=True)
class PortableRelationalSkeletonV1:
    role_schema_id: str
    source_observation_log_id: str
    state_program: PortableRelationalProgramV1
    action_program: PortableRelationalProgramV1
    support_schema: PortableRelationalSupportSchemaV1

    def __post_init__(self) -> None:
        _cid(self.role_schema_id, "skeleton role schema")
        _cid(self.source_observation_log_id, "skeleton source log")
        if (
            type(self.state_program) is not PortableRelationalProgramV1
            or self.state_program.context is not RelationalProgramContext.STATE
            or self.state_program.result_type is not RelationalProgramType.INTEGER
            or type(self.action_program) is not PortableRelationalProgramV1
            or self.action_program.context
            is not RelationalProgramContext.STATE_ACTION
            or self.action_program.result_type
            is not RelationalProgramType.INTEGER
            or type(self.support_schema) is not PortableRelationalSupportSchemaV1
            or self.role_schema_id
            != PortableRelationalRoleSchemaV1().role_schema_id
        ):
            raise PortableRelationalInvariantViolation(
                "portable relational skeleton crosses its source-only boundary"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_relational_skeleton.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "role_schema_id": self.role_schema_id,
            "source_observation_log_id": self.source_observation_log_id,
            "state_program": self.state_program.to_document(),
            "action_program": self.action_program.to_document(),
            "support_schema": self.support_schema.to_document(),
        }

    @property
    def skeleton_id(self) -> str:
        return _content_id("proposal", self._payload())

    @property
    def proposal_id(self) -> str:
        return self.skeleton_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "skeleton_id": self.skeleton_id}


@dataclass(frozen=True, slots=True)
class _Candidate:
    state_program: PortableRelationalProgramV1
    action_program: PortableRelationalProgramV1
    ground_state_count: int
    ground_row_count: int
    abstract_state_count: int
    abstract_support_count: int
    transition_alias_width: Fraction
    reward_alias_width: Fraction
    admissible: bool

    @property
    def sound_alias_width(self) -> Fraction:
        return max(self.transition_alias_width, self.reward_alias_width)

    @property
    def selection_key(self) -> tuple[Any, ...]:
        return (
            self.sound_alias_width,
            self.abstract_support_count,
            self.abstract_state_count,
            self.state_program.node_count + self.action_program.node_count,
            max(self.state_program.depth, self.action_program.depth),
            self.state_program.rendered,
            self.action_program.rendered,
            self.state_program.program_id,
            self.action_program.program_id,
        )


def _integer_state_value(
    program: PortableRelationalProgramV1,
    state: RelationalStateIRV1,
) -> int:
    tagged = evaluate_portable_state_program_v1(program, state)
    if tagged[0] != "INTEGER" or type(tagged[1]) is not int:
        raise PortableRelationalInvariantViolation(
            "candidate state coordinate is not integer"
        )
    return tagged[1]


def _integer_action_value(
    program: PortableRelationalProgramV1,
    row: RelationalObservedRowV1,
) -> int:
    tagged = evaluate_portable_action_program_v1(
        program,
        row.state,
        row.action,
    )
    if tagged[0] != "INTEGER" or type(tagged[1]) is not int:
        raise PortableRelationalInvariantViolation(
            "candidate action coordinate is not integer"
        )
    return tagged[1]


def _candidate(
    log: AnonymousRelationalObservationLogV1,
    state_program: PortableRelationalProgramV1,
    action_program: PortableRelationalProgramV1,
) -> _Candidate:
    states: dict[str, RelationalStateIRV1] = {}
    for row in log.rows:
        states[row.state.state_ir_id] = row.state
        for outcome in row.outcomes:
            states[outcome.next_state.state_ir_id] = outcome.next_state
    state_values = {
        state_id: _integer_state_value(state_program, state)
        for state_id, state in states.items()
    }
    grouped: dict[
        tuple[int, int, int],
        list[RelationalObservedRowV1],
    ] = defaultdict(list)
    row_state_ids: set[str] = set()
    action_values: set[int] = set()
    for row in log.rows:
        row_state_ids.add(row.state.state_ir_id)
        action_value = _integer_action_value(action_program, row)
        action_values.add(action_value)
        grouped[
            (
                row.state.remaining_horizon,
                state_values[row.state.state_ir_id],
                action_value,
            )
        ].append(row)
    transition_width = Fraction(0)
    reward_width = Fraction(0)
    availability_by_state_cell: dict[
        tuple[int, int],
        set[tuple[int, ...]],
    ] = defaultdict(set)
    labels_by_state: dict[str, set[int]] = defaultdict(set)
    for row in log.rows:
        labels_by_state[row.state.state_ir_id].add(
            _integer_action_value(action_program, row)
        )
    for state_id in row_state_ids:
        state = states[state_id]
        availability_by_state_cell[
            (
                state.remaining_horizon,
                state_values[state_id],
            )
        ].add(tuple(sorted(labels_by_state[state_id])))
    if any(
        len(variants) != 1
        for variants in availability_by_state_cell.values()
    ):
        transition_width = Fraction(1)
    for rows in grouped.values():
        distributions: list[dict[tuple[Any, ...], Fraction]] = []
        rewards: list[Fraction] = []
        destinations: set[tuple[Any, ...]] = set()
        for row in rows:
            distribution: dict[tuple[Any, ...], Fraction] = defaultdict(Fraction)
            reward = Fraction(0)
            for outcome in row.outcomes:
                next_state = outcome.next_state
                destination = (
                    next_state.terminal_kind,
                    next_state.remaining_horizon,
                    (
                        None
                        if next_state.terminal_kind != "ACTIVE"
                        else state_values[next_state.state_ir_id]
                    ),
                )
                distribution[destination] += outcome.probability
                reward += outcome.probability * outcome.normalized_reward
                destinations.add(destination)
            distributions.append(distribution)
            rewards.append(reward)
        for destination in destinations:
            values = [
                item.get(destination, Fraction(0))
                for item in distributions
            ]
            transition_width = max(
                transition_width,
                max(values) - min(values),
            )
        reward_width = max(
            reward_width,
            max(rewards) - min(rewards),
        )
    row_state_values = {
        state_values[state_id] for state_id in row_state_ids
    }
    abstract_states = {
        (
            row.state.remaining_horizon,
            state_values[row.state.state_ir_id],
        )
        for row in log.rows
    }
    admissible = (
        1 < len(row_state_values) < len(row_state_ids)
        and 1 < len(action_values) < len(log.rows)
        and len(abstract_states) < len(row_state_ids)
        and len(grouped) < len(log.rows)
    )
    return _Candidate(
        state_program,
        action_program,
        len(row_state_ids),
        len(log.rows),
        len(abstract_states),
        len(grouped),
        transition_width,
        reward_width,
        admissible,
    )


@dataclass(frozen=True, slots=True)
class PortableRelationalSynthesisMetricsV1:
    source_observation_log_id: str
    skeleton_id: str
    syntactic_program_count: int
    semantic_program_count_by_depth: tuple[int, ...]
    state_integer_program_count: int
    action_integer_program_count: int
    evaluated_candidate_count: int
    admissible_candidate_count: int
    ground_state_count: int
    ground_row_count: int
    abstract_state_count: int
    abstract_support_count: int
    transition_alias_width: Fraction
    reward_alias_width: Fraction
    selected_state_program: str
    selected_action_program: str

    def __post_init__(self) -> None:
        _cid(self.source_observation_log_id, "metrics source log")
        _cid(self.skeleton_id, "metrics skeleton")
        integer_fields = (
            self.syntactic_program_count,
            self.state_integer_program_count,
            self.action_integer_program_count,
            self.evaluated_candidate_count,
            self.admissible_candidate_count,
            self.ground_state_count,
            self.ground_row_count,
            self.abstract_state_count,
            self.abstract_support_count,
        )
        if (
            any(type(item) is not int or item < 0 for item in integer_fields)
            or self.syntactic_program_count <= 0
            or self.state_integer_program_count <= 0
            or self.action_integer_program_count <= 0
            or self.evaluated_candidate_count
            != (
                self.state_integer_program_count
                * self.action_integer_program_count
            )
            or not 0 < self.admissible_candidate_count <= (
                self.evaluated_candidate_count
            )
            or not 0 < self.abstract_state_count < self.ground_state_count
            or not 0 < self.abstract_support_count < self.ground_row_count
            or type(self.semantic_program_count_by_depth) is not tuple
            or len(self.semantic_program_count_by_depth)
            != MAX_PROGRAM_DEPTH + 1
            or any(
                type(item) is not int or item < 0
                for item in self.semantic_program_count_by_depth
            )
            or type(self.transition_alias_width) is not Fraction
            or not 0 <= self.transition_alias_width <= 1
            or type(self.reward_alias_width) is not Fraction
            or not 0 <= self.reward_alias_width <= 1
            or type(self.selected_state_program) is not str
            or not self.selected_state_program
            or type(self.selected_action_program) is not str
            or not self.selected_action_program
        ):
            raise PortableRelationalInvariantViolation(
                "portable synthesis metrics are invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_relational_synthesis_metrics.v1",
            "schema_version": SCHEMA_VERSION,
            "source_observation_log_id": self.source_observation_log_id,
            "skeleton_id": self.skeleton_id,
            "syntactic_program_count": self.syntactic_program_count,
            "semantic_program_count_by_depth": list(
                self.semantic_program_count_by_depth
            ),
            "state_integer_program_count": self.state_integer_program_count,
            "action_integer_program_count": self.action_integer_program_count,
            "evaluated_candidate_count": self.evaluated_candidate_count,
            "admissible_candidate_count": self.admissible_candidate_count,
            "ground_state_count": self.ground_state_count,
            "ground_row_count": self.ground_row_count,
            "abstract_state_count": self.abstract_state_count,
            "abstract_support_count": self.abstract_support_count,
            "transition_alias_width": _fdoc(self.transition_alias_width),
            "reward_alias_width": _fdoc(self.reward_alias_width),
            "sound_alias_width": _fdoc(
                max(self.transition_alias_width, self.reward_alias_width)
            ),
            "selected_state_program": self.selected_state_program,
            "selected_action_program": self.selected_action_program,
        }

    @property
    def metrics_id(self) -> str:
        return _content_id("metrics", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "metrics_id": self.metrics_id}


@dataclass(frozen=True, slots=True)
class _Synthesis:
    registry: PortableRelationalProgramRegistryV1
    candidates: tuple[_Candidate, ...]
    selected: _Candidate
    skeleton: PortableRelationalSkeletonV1


def _synthesis(
    log: AnonymousRelationalObservationLogV1,
) -> _Synthesis:
    _validate_complete_source_action_coverage(log)
    registry = generate_portable_relational_program_registry_v1(log)
    state_programs = tuple(
        item
        for item in registry.programs
        if item.context is RelationalProgramContext.STATE
        and item.result_type is RelationalProgramType.INTEGER
    )
    action_programs = tuple(
        item
        for item in registry.programs
        if item.context is RelationalProgramContext.STATE_ACTION
        and item.result_type is RelationalProgramType.INTEGER
    )
    candidates = tuple(
        _candidate(log, state_program, action_program)
        for state_program in state_programs
        for action_program in action_programs
    )
    admissible = tuple(item for item in candidates if item.admissible)
    if not admissible:
        raise PortableRelationalInvariantViolation(
            "portable source search found no compressive coordinate pair"
        )
    selected = min(admissible, key=lambda item: item.selection_key)
    skeleton = PortableRelationalSkeletonV1(
        log.role_schema.role_schema_id,
        log.observation_log_id,
        selected.state_program,
        selected.action_program,
        PortableRelationalSupportSchemaV1(),
    )
    return _Synthesis(registry, candidates, selected, skeleton)


def synthesize_portable_relational_skeleton_v1(
    source_log: AnonymousRelationalObservationLogV1,
) -> PortableRelationalSkeletonV1:
    """The sole source producer; its only input is an anonymous exact log."""

    if type(source_log) is not AnonymousRelationalObservationLogV1:
        raise PortableRelationalInvariantViolation(
            "portable producer requires the exact anonymous-log type"
        )
    return _synthesis(source_log).skeleton


def portable_relational_synthesis_metrics_v1(
    source_log: AnonymousRelationalObservationLogV1,
    skeleton: PortableRelationalSkeletonV1,
) -> PortableRelationalSynthesisMetricsV1:
    if (
        type(source_log) is not AnonymousRelationalObservationLogV1
        or type(skeleton) is not PortableRelationalSkeletonV1
    ):
        raise PortableRelationalInvariantViolation(
            "portable metrics reject runtime substitutions"
        )
    replay = _synthesis(source_log)
    if replay.skeleton.to_document() != skeleton.to_document():
        raise PortableRelationalInvariantViolation(
            "portable metrics reject a noncanonical skeleton"
        )
    selected = replay.selected
    return PortableRelationalSynthesisMetricsV1(
        source_log.observation_log_id,
        skeleton.skeleton_id,
        replay.registry.syntactic_program_count,
        replay.registry.semantic_program_count_by_depth,
        sum(
            item.context is RelationalProgramContext.STATE
            and item.result_type is RelationalProgramType.INTEGER
            for item in replay.registry.programs
        ),
        sum(
            item.context is RelationalProgramContext.STATE_ACTION
            and item.result_type is RelationalProgramType.INTEGER
            for item in replay.registry.programs
        ),
        len(replay.candidates),
        sum(item.admissible for item in replay.candidates),
        selected.ground_state_count,
        selected.ground_row_count,
        selected.abstract_state_count,
        selected.abstract_support_count,
        selected.transition_alias_width,
        selected.reward_alias_width,
        selected.state_program.rendered,
        selected.action_program.rendered,
    )


def verify_portable_relational_skeleton_v1(
    source_log: AnonymousRelationalObservationLogV1,
    claimed: PortableRelationalSkeletonV1,
) -> bool:
    if (
        type(source_log) is not AnonymousRelationalObservationLogV1
        or type(claimed) is not PortableRelationalSkeletonV1
    ):
        raise PortableRelationalInvariantViolation(
            "portable skeleton verifier rejects runtime substitutions"
        )
    expected = _synthesis(source_log).skeleton
    if expected.to_document() != claimed.to_document():
        raise PortableRelationalInvariantViolation(
            "portable skeleton failed complete source replay"
        )
    return True


@dataclass(frozen=True, slots=True)
class FailedRelationalProofRefV1:
    target_context_id: str
    model_epoch_id: str
    failed_audit_id: str
    reason: str

    def __post_init__(self) -> None:
        for value, field in (
            (self.target_context_id, "failed proof target context"),
            (self.model_epoch_id, "failed proof model epoch"),
            (self.failed_audit_id, "failed proof audit"),
        ):
            _cid(value, field)
        if type(self.reason) is not str or self.reason not in (
            "ALIAS_WIDTH",
            "ACTION_AVAILABILITY",
            "RISK_OR_REGRET",
        ):
            raise PortableRelationalInvariantViolation(
                "target program generation lacks a registered failed proof"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_relational_failed_proof_ref.v1",
            "schema_version": SCHEMA_VERSION,
            "target_context_id": self.target_context_id,
            "model_epoch_id": self.model_epoch_id,
            "failed_audit_id": self.failed_audit_id,
            "reason": self.reason,
        }

    @property
    def failed_proof_ref_id(self) -> str:
        return _content_id("failed_proof", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "failed_proof_ref_id": self.failed_proof_ref_id,
        }


@dataclass(frozen=True, slots=True)
class TargetRelationalProgramGenerationV1:
    skeleton_id: str
    target_observation_log_id: str
    failed_proof_ref_id: str
    registry: PortableRelationalProgramRegistryV1
    generated_program_ids: tuple[str, ...]
    source_registry_access_count: int = 0
    source_candidate_metric_access_count: int = 0
    primitive_invention_count: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.skeleton_id, "target generation skeleton"),
            (self.target_observation_log_id, "target generation log"),
            (self.failed_proof_ref_id, "target generation failed proof"),
        ):
            _cid(value, field)
        if (
            type(self.registry) is not PortableRelationalProgramRegistryV1
            or self.registry.observation_log_id
            != self.target_observation_log_id
            or self.registry.role_schema_id
            != PortableRelationalRoleSchemaV1().role_schema_id
            or type(self.generated_program_ids) is not tuple
            or self.generated_program_ids
            != tuple(sorted(set(self.generated_program_ids)))
            or set(self.generated_program_ids)
            != {item.program_id for item in self.registry.programs}
            or self.source_registry_access_count != 0
            or self.source_candidate_metric_access_count != 0
            or self.primitive_invention_count != 0
        ):
            raise PortableRelationalInvariantViolation(
                "target program generation crossed its authority boundary"
            )

    @property
    def target_program_generation_count(self) -> int:
        return self.registry.syntactic_program_count

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_relational_target_generation.v1",
            "schema_version": SCHEMA_VERSION,
            "skeleton_id": self.skeleton_id,
            "target_observation_log_id": self.target_observation_log_id,
            "failed_proof_ref_id": self.failed_proof_ref_id,
            "registry": self.registry.to_document(),
            "generated_program_ids": list(self.generated_program_ids),
            "target_program_generation_count": (
                self.target_program_generation_count
            ),
            "source_registry_access_count": self.source_registry_access_count,
            "source_candidate_metric_access_count": (
                self.source_candidate_metric_access_count
            ),
            "primitive_invention_count": self.primitive_invention_count,
        }

    @property
    def generation_id(self) -> str:
        return _content_id("target_generation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "generation_id": self.generation_id}


def generate_target_relational_programs_v1(
    skeleton: PortableRelationalSkeletonV1,
    failed_proof: FailedRelationalProofRefV1,
    authorized_target_log: AnonymousRelationalObservationLogV1,
) -> TargetRelationalProgramGenerationV1:
    """Fresh target closure; no source registry can be supplied."""

    if (
        type(skeleton) is not PortableRelationalSkeletonV1
        or type(failed_proof) is not FailedRelationalProofRefV1
        or type(authorized_target_log)
        is not AnonymousRelationalObservationLogV1
        or skeleton.role_schema_id
        != authorized_target_log.role_schema.role_schema_id
        or skeleton.source_observation_log_id
        == authorized_target_log.observation_log_id
        or {
            row.state.structural_context_id
            for row in authorized_target_log.rows
        }
        != {failed_proof.target_context_id}
    ):
        raise PortableRelationalInvariantViolation(
            "target program generation binding is invalid"
        )
    registry = generate_portable_relational_program_registry_v1(
        authorized_target_log
    )
    return TargetRelationalProgramGenerationV1(
        skeleton.skeleton_id,
        authorized_target_log.observation_log_id,
        failed_proof.failed_proof_ref_id,
        registry,
        tuple(sorted(item.program_id for item in registry.programs)),
    )


__all__ = [
    "AnonymousRelationalObservationLogV1",
    "FailedRelationalProofRefV1",
    "MAX_PROGRAM_DEPTH",
    "PROFILE_KEY",
    "PortableRelationalInvariantViolation",
    "PortableRelationalProgramRegistryV1",
    "PortableRelationalProgramV1",
    "PortableRelationalRoleSchemaV1",
    "PortableRelationalSkeletonV1",
    "PortableRelationalSupportSchemaV1",
    "PortableRelationalSynthesisMetricsV1",
    "RelationalActionSlotV1",
    "RelationalObservedRowV1",
    "RelationalOutcomeIRV1",
    "RelationalProgramContext",
    "RelationalProgramType",
    "RelationalStateIRV1",
    "TargetRelationalProgramGenerationV1",
    "evaluate_portable_action_program_v1",
    "evaluate_portable_state_program_v1",
    "generate_portable_relational_program_registry_v1",
    "generate_target_relational_programs_v1",
    "portable_relational_synthesis_metrics_v1",
    "synthesize_portable_relational_skeleton_v1",
    "syntactic_portable_program_closure_v1",
    "verify_portable_relational_skeleton_v1",
]
