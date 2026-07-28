"""Independent replay for portable relational source proposals.

This verifier intentionally does not import the producer, any domain adapter,
any campaign, or any ground kernel.  Its inputs are two canonical serialized
mappings: an anonymous exact source log and the exported relational skeleton.
It independently parses and hashes every nested object, reconstructs the
depth-two grammar, semantically deduplicates it, exhausts the coordinate
search, and checks the selected programs byte-for-byte.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
import hashlib
from itertools import product
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "portable_relational_skeleton_v1"
MAX_PROGRAM_DEPTH = 2
MAX_HORIZON = 2
SUCCESS_STATUS = "INDEPENDENT_PORTABLE_RELATIONAL_SOURCE_VERIFIED"

DOMAIN_TAGS = {
    "schema": "acfqp:portable-relational-role-schema:v1",
    "action": "acfqp:portable-relational-action-slot:v1",
    "state": "acfqp:portable-relational-state-ir:v1",
    "outcome": "acfqp:portable-relational-outcome-ir:v1",
    "row": "acfqp:portable-relational-observed-row:v1",
    "log": "acfqp:portable-relational-anonymous-log:v1",
    "program": "acfqp:portable-relational-program:v1",
    "support_schema": "acfqp:portable-relational-support-schema:v1",
    "proposal": "acfqp:portable-relational-skeleton:v1",
    "verification": (
        "acfqp:portable-relational-independent-source-verification:v1"
    ),
}

_PRIMITIVES: dict[str, tuple[str, str]] = {
    "all_resources": ("RESOURCE_SET", "STATE"),
    "active_resources": ("RESOURCE_SET", "STATE"),
    "legal_actions": ("ACTION_SET", "STATE"),
    "action_anchor": ("ANCHOR", "STATE_ACTION"),
    "active_attribute_degree_signature": ("SIGNATURE", "STATE"),
}
_OPERATORS: dict[str, tuple[tuple[str, ...], str]] = {
    "cardinality_resources": (("RESOURCE_SET",), "INTEGER"),
    "cardinality_actions": (("ACTION_SET",), "INTEGER"),
    "linked_filter": (("ANCHOR", "RESOURCE_SET"), "RESOURCE_SET"),
    "set_difference": (
        ("RESOURCE_SET", "RESOURCE_SET"),
        "RESOURCE_SET",
    ),
}
_OPERATION_ORDER = tuple(_PRIMITIVES) + tuple(_OPERATORS)

_ROLE_SCHEMA_KEYS = {
    "schema",
    "schema_version",
    "roles",
    "max_program_depth",
    "role_schema_id",
}
_ACTION_KEYS = {
    "schema",
    "schema_version",
    "opaque_action_key",
    "anchor",
    "action_slot_id",
}
_STATE_KEYS = {
    "schema",
    "schema_version",
    "structural_context_id",
    "remaining_horizon",
    "resource_attributes",
    "active_resources",
    "linked_pairs",
    "legal_actions",
    "terminal_kind",
    "state_ir_id",
}
_OUTCOME_KEYS = {
    "schema",
    "schema_version",
    "next_state",
    "probability",
    "normalized_reward",
    "failure",
    "terminal",
    "outcome_ir_id",
}
_ROW_KEYS = {
    "schema",
    "schema_version",
    "state",
    "action",
    "outcomes",
    "observed_row_id",
}
_LOG_KEYS = {
    "schema",
    "schema_version",
    "role_schema",
    "rows",
    "observation_log_id",
}
_PROGRAM_KEYS = {
    "schema",
    "schema_version",
    "operation",
    "result_type",
    "context",
    "arguments",
    "program_id",
}
_SUPPORT_SCHEMA_KEYS = {
    "schema",
    "schema_version",
    "fields",
    "destination_fields",
    "support_schema_id",
}
_SKELETON_KEYS = {
    "schema",
    "schema_version",
    "profile_key",
    "role_schema_id",
    "source_observation_log_id",
    "state_program",
    "action_program",
    "support_schema",
    "skeleton_id",
}


class PortableRelationalIndependentVerificationFailure(ValueError):
    """The serialized source/proposal chain failed independent replay."""


def _mapping(
    value: Any,
    keys: set[str],
    field: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise PortableRelationalIndependentVerificationFailure(
            f"{field} is not a canonical closed mapping"
        )
    return value


def _list(value: Any, field: str) -> list[Any]:
    if type(value) is not list:
        raise PortableRelationalIndependentVerificationFailure(
            f"{field} must be a canonical list"
        )
    return value


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role].encode("utf-8")
    except (KeyError, TypeError, ValueError) as error:
        raise PortableRelationalIndependentVerificationFailure(
            str(error)
        ) from error
    return hashlib.sha256(domain + b"\x00" + encoded).hexdigest()


def _claimed_id(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise PortableRelationalIndependentVerificationFailure(
            f"{field} is not a full content ID"
        ) from error


def _check_id(
    role: str,
    payload: Mapping[str, Any],
    claimed: Any,
    field: str,
) -> str:
    identifier = _claimed_id(claimed, field)
    if identifier != _content_id(role, payload):
        raise PortableRelationalIndependentVerificationFailure(
            f"{field} content ID mismatch"
        )
    return identifier


def _integer(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise PortableRelationalIndependentVerificationFailure(
            f"{field} must be an integer >= {minimum}"
        )
    return value


def _fraction(value: Any, field: str) -> Fraction:
    document = _mapping(
        value,
        {"numerator", "denominator"},
        field,
    )
    numerator = document["numerator"]
    denominator = document["denominator"]
    if (
        type(numerator) is not int
        or type(denominator) is not int
        or denominator <= 0
    ):
        raise PortableRelationalIndependentVerificationFailure(
            f"{field} is not an exact rational"
        )
    result = Fraction(numerator, denominator)
    if (
        result.numerator != numerator
        or result.denominator != denominator
    ):
        raise PortableRelationalIndependentVerificationFailure(
            f"{field} rational is not reduced"
        )
    return result


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {
        "numerator": exact.numerator,
        "denominator": exact.denominator,
    }


def _schema_header(
    document: Mapping[str, Any],
    expected_schema: str,
    field: str,
) -> None:
    if (
        type(document["schema"]) is not str
        or document["schema"] != expected_schema
        or type(document["schema_version"]) is not str
        or document["schema_version"] != SCHEMA_VERSION
    ):
        raise PortableRelationalIndependentVerificationFailure(
            f"{field} schema changed"
        )


@dataclass(frozen=True, slots=True)
class _Action:
    key: str
    anchor: int
    identifier: str
    document: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _State:
    structural_context_id: str
    remaining_horizon: int
    resource_attributes: tuple[int, ...]
    active_resources: tuple[int, ...]
    linked_pairs: tuple[tuple[int, int], ...]
    legal_actions: tuple[_Action, ...]
    terminal_kind: str
    identifier: str
    document: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _Outcome:
    next_state: _State
    probability: Fraction
    normalized_reward: Fraction
    failure: bool
    terminal: bool
    identifier: str
    document: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _Row:
    state: _State
    action: _Action
    outcomes: tuple[_Outcome, ...]
    identifier: str
    document: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _Log:
    role_schema_id: str
    rows: tuple[_Row, ...]
    identifier: str
    document: dict[str, Any]


def _parse_role_schema(value: Any) -> tuple[str, dict[str, Any]]:
    document = _mapping(value, _ROLE_SCHEMA_KEYS, "role schema")
    _schema_header(
        document,
        "acfqp.portable_relational_role_schema.v1",
        "role schema",
    )
    roles = _mapping(
        document["roles"],
        {
            "legal_actions",
            "active_resources",
            "all_resources",
            "action_anchor",
            "linked",
            "resource_attribute",
        },
        "role schema roles",
    )
    if (
        roles
        != {
            "legal_actions": "legal_actions",
            "active_resources": "active_resources",
            "all_resources": "all_resources",
            "action_anchor": "action_anchor",
            "linked": "linked",
            "resource_attribute": "resource_attribute",
        }
        or document["max_program_depth"] != MAX_PROGRAM_DEPTH
        or type(document["max_program_depth"]) is not int
    ):
        raise PortableRelationalIndependentVerificationFailure(
            "role schema semantics changed"
        )
    payload = {
        key: document[key]
        for key in document
        if key != "role_schema_id"
    }
    identifier = _check_id(
        "schema",
        payload,
        document["role_schema_id"],
        "role schema",
    )
    return identifier, document


def _parse_action(value: Any) -> _Action:
    document = _mapping(value, _ACTION_KEYS, "action slot")
    _schema_header(
        document,
        "acfqp.portable_relational_action_slot.v1",
        "action slot",
    )
    key = document["opaque_action_key"]
    anchor = document["anchor"]
    if type(key) is not str or not key:
        raise PortableRelationalIndependentVerificationFailure(
            "action slot key is invalid"
        )
    _integer(anchor, "action anchor")
    payload = {
        item: document[item]
        for item in document
        if item != "action_slot_id"
    }
    identifier = _check_id(
        "action",
        payload,
        document["action_slot_id"],
        "action slot",
    )
    return _Action(key, anchor, identifier, document)


def _parse_state(value: Any) -> _State:
    document = _mapping(value, _STATE_KEYS, "state IR")
    _schema_header(
        document,
        "acfqp.portable_relational_state_ir.v1",
        "state IR",
    )
    structural_context_id = _claimed_id(
        document["structural_context_id"],
        "state structural context",
    )
    remaining_horizon = _integer(
        document["remaining_horizon"],
        "state remaining horizon",
    )
    if remaining_horizon > MAX_HORIZON:
        raise PortableRelationalIndependentVerificationFailure(
            "state remaining horizon exceeds the registered cap"
        )
    raw_attributes = _list(
        document["resource_attributes"],
        "state resource attributes",
    )
    if not raw_attributes or any(type(item) is not int for item in raw_attributes):
        raise PortableRelationalIndependentVerificationFailure(
            "state resource attributes are invalid"
        )
    resource_attributes = tuple(raw_attributes)
    raw_active = _list(
        document["active_resources"],
        "state active resources",
    )
    if (
        any(type(item) is not int for item in raw_active)
        or raw_active != sorted(set(raw_active))
        or any(
            not 0 <= item < len(resource_attributes)
            for item in raw_active
        )
    ):
        raise PortableRelationalIndependentVerificationFailure(
            "state active resources are invalid"
        )
    active_resources = tuple(raw_active)
    raw_linked = _list(document["linked_pairs"], "state linked pairs")
    linked_pairs: list[tuple[int, int]] = []
    for item in raw_linked:
        pair = _list(item, "state linked pair")
        if (
            len(pair) != 2
            or any(type(endpoint) is not int for endpoint in pair)
            or any(
                not 0 <= endpoint < len(resource_attributes)
                for endpoint in pair
            )
        ):
            raise PortableRelationalIndependentVerificationFailure(
                "state linked pair is invalid"
            )
        linked_pairs.append((pair[0], pair[1]))
    if linked_pairs != sorted(set(linked_pairs)):
        raise PortableRelationalIndependentVerificationFailure(
            "state linked pairs are not canonical"
        )
    actions = tuple(
        _parse_action(item)
        for item in _list(document["legal_actions"], "state legal actions")
    )
    if (
        tuple(item.identifier for item in actions)
        != tuple(sorted({item.identifier for item in actions}))
        or len({item.key for item in actions}) != len(actions)
        or any(item.anchor not in active_resources for item in actions)
    ):
        raise PortableRelationalIndependentVerificationFailure(
            "state legal actions are invalid"
        )
    terminal_kind = document["terminal_kind"]
    if (
        type(terminal_kind) is not str
        or terminal_kind
        not in {
            "ACTIVE",
            "FAILURE",
            "SUCCESS",
            "HORIZON_TERMINAL",
        }
        or (terminal_kind != "ACTIVE" and actions)
        or (
            terminal_kind == "ACTIVE"
            and (remaining_horizon == 0 or not actions)
        )
    ):
        raise PortableRelationalIndependentVerificationFailure(
            "state terminal semantics are invalid"
        )
    payload = {
        item: document[item]
        for item in document
        if item != "state_ir_id"
    }
    identifier = _check_id(
        "state",
        payload,
        document["state_ir_id"],
        "state IR",
    )
    return _State(
        structural_context_id,
        remaining_horizon,
        resource_attributes,
        active_resources,
        tuple(linked_pairs),
        actions,
        terminal_kind,
        identifier,
        document,
    )


def _parse_outcome(value: Any) -> _Outcome:
    document = _mapping(value, _OUTCOME_KEYS, "outcome IR")
    _schema_header(
        document,
        "acfqp.portable_relational_outcome_ir.v1",
        "outcome IR",
    )
    next_state = _parse_state(document["next_state"])
    probability = _fraction(document["probability"], "outcome probability")
    normalized_reward = _fraction(
        document["normalized_reward"],
        "outcome normalized reward",
    )
    failure = document["failure"]
    terminal = document["terminal"]
    if (
        not 0 < probability <= 1
        or not 0 <= normalized_reward <= 1
        or type(failure) is not bool
        or type(terminal) is not bool
        or failure != (next_state.terminal_kind == "FAILURE")
        or terminal != (next_state.terminal_kind != "ACTIVE")
    ):
        raise PortableRelationalIndependentVerificationFailure(
            "outcome semantics are invalid"
        )
    payload = {
        item: document[item]
        for item in document
        if item != "outcome_ir_id"
    }
    identifier = _check_id(
        "outcome",
        payload,
        document["outcome_ir_id"],
        "outcome IR",
    )
    return _Outcome(
        next_state,
        probability,
        normalized_reward,
        failure,
        terminal,
        identifier,
        document,
    )


def _parse_row(value: Any) -> _Row:
    document = _mapping(value, _ROW_KEYS, "observed row")
    _schema_header(
        document,
        "acfqp.portable_relational_observed_row.v1",
        "observed row",
    )
    state = _parse_state(document["state"])
    action = _parse_action(document["action"])
    outcomes = tuple(
        _parse_outcome(item)
        for item in _list(document["outcomes"], "row outcomes")
    )
    legal = {
        item.identifier: item
        for item in state.legal_actions
    }
    if (
        action.identifier not in legal
        or legal[action.identifier] != action
        or state.terminal_kind != "ACTIVE"
        or state.remaining_horizon <= 0
        or not outcomes
        or tuple(item.identifier for item in outcomes)
        != tuple(sorted({item.identifier for item in outcomes}))
        or sum(
            (item.probability for item in outcomes),
            Fraction(0),
        )
        != 1
        or any(
            item.next_state.structural_context_id
            != state.structural_context_id
            or item.next_state.remaining_horizon
            != state.remaining_horizon - 1
            for item in outcomes
        )
    ):
        raise PortableRelationalIndependentVerificationFailure(
            "observed row semantics are invalid"
        )
    payload = {
        item: document[item]
        for item in document
        if item != "observed_row_id"
    }
    identifier = _check_id(
        "row",
        payload,
        document["observed_row_id"],
        "observed row",
    )
    return _Row(state, action, outcomes, identifier, document)


def _parse_log(value: Any) -> _Log:
    document = _mapping(value, _LOG_KEYS, "source log")
    _schema_header(
        document,
        "acfqp.portable_relational_anonymous_log.v1",
        "source log",
    )
    role_schema_id, _ = _parse_role_schema(document["role_schema"])
    rows = tuple(
        _parse_row(item)
        for item in _list(document["rows"], "source rows")
    )
    if (
        not rows
        or tuple(item.identifier for item in rows)
        != tuple(sorted({item.identifier for item in rows}))
    ):
        raise PortableRelationalIndependentVerificationFailure(
            "source rows are not canonical"
        )
    rows_by_state: dict[str, list[_Row]] = defaultdict(list)
    for row in rows:
        rows_by_state[row.state.identifier].append(row)
    for state_rows in rows_by_state.values():
        expected = tuple(
            item.identifier
            for item in state_rows[0].state.legal_actions
        )
        claimed = tuple(
            sorted(item.action.identifier for item in state_rows)
        )
        if claimed != expected:
            raise PortableRelationalIndependentVerificationFailure(
                "source rows do not completely cover declared actions"
            )
    payload = {
        item: document[item]
        for item in document
        if item != "observation_log_id"
    }
    identifier = _check_id(
        "log",
        payload,
        document["observation_log_id"],
        "source log",
    )
    return _Log(role_schema_id, rows, identifier, document)


@dataclass(frozen=True, slots=True)
class _Program:
    operation: str
    result_type: str
    context: str
    arguments: tuple["_Program", ...] = ()

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

    def payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_relational_program.v1",
            "schema_version": SCHEMA_VERSION,
            "operation": self.operation,
            "result_type": self.result_type,
            "context": self.context,
            "arguments": [item.document() for item in self.arguments],
        }

    @property
    def identifier(self) -> str:
        return _content_id("program", self.payload())

    def document(self) -> dict[str, Any]:
        return {**self.payload(), "program_id": self.identifier}


def _program_order_key(program: _Program) -> tuple[Any, ...]:
    return (
        program.node_count,
        program.depth,
        _OPERATION_ORDER.index(program.operation),
        program.rendered,
        program.identifier,
    )


def _primitive(operation: str) -> _Program:
    result_type, context = _PRIMITIVES[operation]
    return _Program(operation, result_type, context)


def _operator(
    operation: str,
    arguments: tuple[_Program, ...],
) -> _Program:
    argument_types, result_type = _OPERATORS[operation]
    if tuple(item.result_type for item in arguments) != argument_types:
        raise PortableRelationalIndependentVerificationFailure(
            "internal grammar operator type mismatch"
        )
    context = (
        "STATE_ACTION"
        if any(item.context == "STATE_ACTION" for item in arguments)
        else "STATE"
    )
    candidate = _Program(operation, result_type, context, arguments)
    if candidate.depth > MAX_PROGRAM_DEPTH:
        raise PortableRelationalIndependentVerificationFailure(
            "internal grammar exceeded the registered depth"
        )
    return candidate


def _parse_program(value: Any) -> _Program:
    document = _mapping(value, _PROGRAM_KEYS, "program")
    _schema_header(
        document,
        "acfqp.portable_relational_program.v1",
        "program",
    )
    operation = document["operation"]
    result_type = document["result_type"]
    context = document["context"]
    if (
        type(operation) is not str
        or type(result_type) is not str
        or type(context) is not str
    ):
        raise PortableRelationalIndependentVerificationFailure(
            "program runtime types changed"
        )
    arguments = tuple(
        _parse_program(item)
        for item in _list(document["arguments"], "program arguments")
    )
    if operation in _PRIMITIVES:
        expected_type, expected_context = _PRIMITIVES[operation]
        candidate = _Program(operation, expected_type, expected_context)
        if arguments:
            raise PortableRelationalIndependentVerificationFailure(
                "primitive program has arguments"
            )
    elif operation in _OPERATORS:
        candidate = _operator(operation, arguments)
    else:
        raise PortableRelationalIndependentVerificationFailure(
            "program operation is unregistered"
        )
    if (
        candidate.result_type != result_type
        or candidate.context != context
        or candidate.document() != document
    ):
        raise PortableRelationalIndependentVerificationFailure(
            "program AST or content ID mismatch"
        )
    return candidate


def _syntactic_closure() -> tuple[_Program, ...]:
    known = {
        item.identifier: item
        for item in (_primitive(name) for name in _PRIMITIVES)
    }
    for target_depth in range(1, MAX_PROGRAM_DEPTH + 1):
        prior = tuple(known.values())
        by_type: dict[str, tuple[_Program, ...]] = {}
        for result_type in {
            "RESOURCE_SET",
            "ACTION_SET",
            "ANCHOR",
            "INTEGER",
            "SIGNATURE",
        }:
            by_type[result_type] = tuple(
                item
                for item in prior
                if item.result_type == result_type
            )
        for operation, (argument_types, _) in _OPERATORS.items():
            domains = tuple(by_type[item] for item in argument_types)
            for arguments in product(*domains):
                candidate = _operator(operation, tuple(arguments))
                if candidate.depth == target_depth:
                    known[candidate.identifier] = candidate
    result = tuple(sorted(known.values(), key=_program_order_key))
    if len(result) != 86:
        raise PortableRelationalIndependentVerificationFailure(
            "independent syntactic closure cardinality changed"
        )
    return result


def _linked_resources(state: _State, anchor: int) -> frozenset[int]:
    return frozenset(
        resource
        for relation_anchor, resource in state.linked_pairs
        if relation_anchor == anchor
    )


def _evaluate(
    program: _Program,
    state: _State,
    action: _Action | None,
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
            raise PortableRelationalIndependentVerificationFailure(
                "action program lacks an action"
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
    values = tuple(
        _evaluate(item, state, action)
        for item in program.arguments
    )
    if operation == "cardinality_resources":
        if type(values[0]) is not frozenset:
            raise PortableRelationalIndependentVerificationFailure(
                "resource cardinality runtime type changed"
            )
        return len(values[0])
    if operation == "cardinality_actions":
        if type(values[0]) is not tuple:
            raise PortableRelationalIndependentVerificationFailure(
                "action cardinality runtime type changed"
            )
        return len(values[0])
    if operation == "linked_filter":
        anchor, resources = values
        if type(anchor) is not int or type(resources) is not frozenset:
            raise PortableRelationalIndependentVerificationFailure(
                "linked filter runtime types changed"
            )
        return _linked_resources(state, anchor) & resources
    if operation == "set_difference":
        left, right = values
        if type(left) is not frozenset or type(right) is not frozenset:
            raise PortableRelationalIndependentVerificationFailure(
                "set difference runtime types changed"
            )
        return left - right
    raise PortableRelationalIndependentVerificationFailure(
        "independent evaluator reached an unregistered operation"
    )


def _tagged(
    program: _Program,
    state: _State,
    action: _Action | None = None,
) -> tuple[str, Any]:
    value = _evaluate(program, state, action)
    if program.result_type == "INTEGER" and type(value) is int:
        return ("INTEGER", value)
    if program.result_type == "SIGNATURE" and type(value) is tuple:
        return ("SIGNATURE", value)
    if program.result_type == "RESOURCE_SET" and type(value) is frozenset:
        return ("RESOURCE_SET", tuple(sorted(value)))
    if program.result_type == "ACTION_SET" and type(value) is tuple:
        return ("ACTION_SET", tuple(item.identifier for item in value))
    if program.result_type == "ANCHOR" and type(value) is int:
        return ("ANCHOR", value)
    raise PortableRelationalIndependentVerificationFailure(
        "independent evaluator produced an invalid value"
    )


def _semantic_signature(
    program: _Program,
    log: _Log,
) -> tuple[Any, ...]:
    states: dict[str, _State] = {}
    for row in log.rows:
        states[row.state.identifier] = row.state
        for outcome in row.outcomes:
            states[outcome.next_state.identifier] = outcome.next_state
    if program.context == "STATE":
        return tuple(
            (
                identifier,
                _tagged(program, state),
            )
            for identifier, state in sorted(states.items())
        )
    return tuple(
        (
            row.identifier,
            _tagged(program, row.state, row.action),
        )
        for row in log.rows
    )


def _semantic_registry(
    log: _Log,
) -> tuple[tuple[_Program, ...], tuple[int, ...]]:
    retained: list[_Program] = []
    seen: set[tuple[Any, ...]] = set()
    for program in _syntactic_closure():
        signature = (
            program.context,
            program.result_type,
            _semantic_signature(program, log),
        )
        if signature not in seen:
            seen.add(signature)
            retained.append(program)
    programs = tuple(sorted(retained, key=_program_order_key))
    depth_counts = tuple(
        sum(item.depth == depth for item in programs)
        for depth in range(MAX_PROGRAM_DEPTH + 1)
    )
    return programs, depth_counts


def _integer_state(program: _Program, state: _State) -> int:
    tagged = _tagged(program, state)
    if tagged[0] != "INTEGER" or type(tagged[1]) is not int:
        raise PortableRelationalIndependentVerificationFailure(
            "state candidate is not integer"
        )
    return tagged[1]


def _integer_action(program: _Program, row: _Row) -> int:
    tagged = _tagged(program, row.state, row.action)
    if tagged[0] != "INTEGER" or type(tagged[1]) is not int:
        raise PortableRelationalIndependentVerificationFailure(
            "action candidate is not integer"
        )
    return tagged[1]


@dataclass(frozen=True, slots=True)
class _Candidate:
    state_program: _Program
    action_program: _Program
    ground_state_count: int
    ground_row_count: int
    abstract_state_count: int
    abstract_support_count: int
    transition_alias_width: Fraction
    reward_alias_width: Fraction
    admissible: bool

    @property
    def selection_key(self) -> tuple[Any, ...]:
        return (
            max(
                self.transition_alias_width,
                self.reward_alias_width,
            ),
            self.abstract_support_count,
            self.abstract_state_count,
            (
                self.state_program.node_count
                + self.action_program.node_count
            ),
            max(
                self.state_program.depth,
                self.action_program.depth,
            ),
            self.state_program.rendered,
            self.action_program.rendered,
            self.state_program.identifier,
            self.action_program.identifier,
        )


def _candidate(
    log: _Log,
    state_program: _Program,
    action_program: _Program,
) -> _Candidate:
    states: dict[str, _State] = {}
    for row in log.rows:
        states[row.state.identifier] = row.state
        for outcome in row.outcomes:
            states[outcome.next_state.identifier] = outcome.next_state
    state_values = {
        identifier: _integer_state(state_program, state)
        for identifier, state in states.items()
    }
    grouped: dict[tuple[int, int, int], list[_Row]] = defaultdict(list)
    row_state_ids: set[str] = set()
    action_values: set[int] = set()
    for row in log.rows:
        row_state_ids.add(row.state.identifier)
        action_value = _integer_action(action_program, row)
        action_values.add(action_value)
        grouped[
            (
                row.state.remaining_horizon,
                state_values[row.state.identifier],
                action_value,
            )
        ].append(row)
    transition_width = Fraction(0)
    reward_width = Fraction(0)
    labels_by_state: dict[str, set[int]] = defaultdict(set)
    for row in log.rows:
        labels_by_state[row.state.identifier].add(
            _integer_action(action_program, row)
        )
    availability: dict[
        tuple[int, int],
        set[tuple[int, ...]],
    ] = defaultdict(set)
    for state_id in row_state_ids:
        state = states[state_id]
        availability[
            (
                state.remaining_horizon,
                state_values[state_id],
            )
        ].add(tuple(sorted(labels_by_state[state_id])))
    if any(len(variants) != 1 for variants in availability.values()):
        transition_width = Fraction(1)
    for rows in grouped.values():
        distributions: list[
            dict[tuple[Any, ...], Fraction]
        ] = []
        rewards: list[Fraction] = []
        destinations: set[tuple[Any, ...]] = set()
        for row in rows:
            distribution: dict[
                tuple[Any, ...],
                Fraction,
            ] = defaultdict(Fraction)
            reward = Fraction(0)
            for outcome in row.outcomes:
                next_state = outcome.next_state
                destination = (
                    next_state.terminal_kind,
                    next_state.remaining_horizon,
                    (
                        None
                        if next_state.terminal_kind != "ACTIVE"
                        else state_values[next_state.identifier]
                    ),
                )
                distribution[destination] += outcome.probability
                reward += (
                    outcome.probability
                    * outcome.normalized_reward
                )
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
        state_values[state_id]
        for state_id in row_state_ids
    }
    abstract_states = {
        (
            row.state.remaining_horizon,
            state_values[row.state.identifier],
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


def _canonical_selection(
    log: _Log,
) -> tuple[
    _Candidate,
    tuple[int, ...],
    int,
    int,
]:
    registry, depth_counts = _semantic_registry(log)
    state_programs = tuple(
        item
        for item in registry
        if item.context == "STATE"
        and item.result_type == "INTEGER"
    )
    action_programs = tuple(
        item
        for item in registry
        if item.context == "STATE_ACTION"
        and item.result_type == "INTEGER"
    )
    candidates = tuple(
        _candidate(log, state_program, action_program)
        for state_program in state_programs
        for action_program in action_programs
    )
    admissible = tuple(item for item in candidates if item.admissible)
    if not admissible:
        raise PortableRelationalIndependentVerificationFailure(
            "independent source search found no compressive pair"
        )
    return (
        min(admissible, key=lambda item: item.selection_key),
        depth_counts,
        len(candidates),
        len(admissible),
    )


def _parse_support_schema(value: Any) -> tuple[str, dict[str, Any]]:
    document = _mapping(
        value,
        _SUPPORT_SCHEMA_KEYS,
        "support schema",
    )
    _schema_header(
        document,
        "acfqp.portable_relational_support_schema.v1",
        "support schema",
    )
    if (
        document["fields"]
        != [
            "remaining_horizon",
            "state_coordinate",
            "action_coordinate",
        ]
        or type(document["fields"]) is not list
        or document["destination_fields"]
        != [
            "terminal_kind",
            "remaining_horizon",
            "state_coordinate",
        ]
        or type(document["destination_fields"]) is not list
    ):
        raise PortableRelationalIndependentVerificationFailure(
            "support schema semantics changed"
        )
    payload = {
        item: document[item]
        for item in document
        if item != "support_schema_id"
    }
    identifier = _check_id(
        "support_schema",
        payload,
        document["support_schema_id"],
        "support schema",
    )
    return identifier, document


@dataclass(frozen=True, slots=True)
class IndependentPortableRelationalVerificationV1:
    source_observation_log_id: str
    skeleton_id: str
    syntactic_program_count: int
    semantic_program_count_by_depth: tuple[int, ...]
    evaluated_candidate_count: int
    admissible_candidate_count: int
    selected_state_program: str
    selected_action_program: str
    status: str = SUCCESS_STATUS
    independent_implementation: bool = True
    producer_imported: bool = False

    def __post_init__(self) -> None:
        _claimed_id(self.source_observation_log_id, "verification source log")
        _claimed_id(self.skeleton_id, "verification skeleton")
        if (
            type(self.syntactic_program_count) is not int
            or self.syntactic_program_count != 86
            or type(self.semantic_program_count_by_depth) is not tuple
            or len(self.semantic_program_count_by_depth) != 3
            or any(
                type(item) is not int or item < 0
                for item in self.semantic_program_count_by_depth
            )
            or type(self.evaluated_candidate_count) is not int
            or self.evaluated_candidate_count <= 0
            or type(self.admissible_candidate_count) is not int
            or not 0 < self.admissible_candidate_count <= (
                self.evaluated_candidate_count
            )
            or type(self.selected_state_program) is not str
            or not self.selected_state_program
            or type(self.selected_action_program) is not str
            or not self.selected_action_program
            or self.status != SUCCESS_STATUS
            or self.independent_implementation is not True
            or self.producer_imported is not False
        ):
            raise PortableRelationalIndependentVerificationFailure(
                "independent verification result is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.portable_relational_independent_source_"
                "verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "source_observation_log_id": self.source_observation_log_id,
            "skeleton_id": self.skeleton_id,
            "syntactic_program_count": self.syntactic_program_count,
            "semantic_program_count_by_depth": list(
                self.semantic_program_count_by_depth
            ),
            "evaluated_candidate_count": self.evaluated_candidate_count,
            "admissible_candidate_count": self.admissible_candidate_count,
            "selected_state_program": self.selected_state_program,
            "selected_action_program": self.selected_action_program,
            "status": self.status,
            "independent_implementation": self.independent_implementation,
            "producer_imported": self.producer_imported,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_id": self.verification_id,
        }


def verify_portable_relational_source_documents_v1(
    source_log_document: Mapping[str, Any],
    skeleton_document: Mapping[str, Any],
) -> IndependentPortableRelationalVerificationV1:
    """Independently replay one serialized source-log/proposal chain."""

    source_log = _parse_log(source_log_document)
    skeleton = _mapping(
        skeleton_document,
        _SKELETON_KEYS,
        "relational skeleton",
    )
    _schema_header(
        skeleton,
        "acfqp.portable_relational_skeleton.v1",
        "relational skeleton",
    )
    if (
        type(skeleton["profile_key"]) is not str
        or skeleton["profile_key"] != PROFILE_KEY
        or skeleton["role_schema_id"] != source_log.role_schema_id
        or skeleton["source_observation_log_id"] != source_log.identifier
    ):
        raise PortableRelationalIndependentVerificationFailure(
            "relational skeleton provenance mismatch"
        )
    state_program = _parse_program(skeleton["state_program"])
    action_program = _parse_program(skeleton["action_program"])
    if (
        state_program.context != "STATE"
        or state_program.result_type != "INTEGER"
        or action_program.context != "STATE_ACTION"
        or action_program.result_type != "INTEGER"
    ):
        raise PortableRelationalIndependentVerificationFailure(
            "relational skeleton coordinate types changed"
        )
    _parse_support_schema(skeleton["support_schema"])
    skeleton_payload = {
        item: skeleton[item]
        for item in skeleton
        if item != "skeleton_id"
    }
    skeleton_id = _check_id(
        "proposal",
        skeleton_payload,
        skeleton["skeleton_id"],
        "relational skeleton",
    )
    selected, depth_counts, candidate_count, admissible_count = (
        _canonical_selection(source_log)
    )
    if (
        state_program.document()
        != selected.state_program.document()
        or action_program.document()
        != selected.action_program.document()
    ):
        raise PortableRelationalIndependentVerificationFailure(
            "relational skeleton is not the exact selected coordinate pair"
        )
    return IndependentPortableRelationalVerificationV1(
        source_log.identifier,
        skeleton_id,
        86,
        depth_counts,
        candidate_count,
        admissible_count,
        selected.state_program.rendered,
        selected.action_program.rendered,
    )


__all__ = [
    "IndependentPortableRelationalVerificationV1",
    "PortableRelationalIndependentVerificationFailure",
    "SUCCESS_STATUS",
    "verify_portable_relational_source_documents_v1",
]
