"""Pure source-log relational coordinate synthesis over finite graphs.

This module is deliberately independent of every domain kernel, target,
query, planner, and certificate implementation.  Its public producer consumes
one anonymous, content-addressed source observation log.  It closes a small
typed incidence grammar, semantically deduplicates the complete depth-two
program set, and exhausts every state/action integer-coordinate pair.

The selected proposal contains only two coordinate ASTs and a generic
anonymous support-key schema.  It contains no source transition rows,
probabilities, rewards, policy, decision, target identity, or query identity.
The source dynamics are used only to rank proposals by their exact sound
alias width; they are not copied into the proposal.

The registered synthetic positive-control helper uses three non-isomorphic
four-vertex geometries (path, star, and paw) and implements its tiny graph
merge process locally.  It is test-fixture acquisition code, not an input to
the synthesis API.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from fractions import Fraction
import functools
import hashlib
from itertools import product
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "relational_graph_coordinate_core_v1"
MAX_PROGRAM_DEPTH = 2
REGISTERED_HORIZON = 2
REGISTERED_RANK_CAP = 6
REGISTERED_LOW_RANK_PROBABILITY = Fraction(99, 100)

DOMAIN_TAGS = {
    "topology": "acfqp:relational-graph-topology:v1",
    "state": "acfqp:relational-graph-state-view:v1",
    "action": "acfqp:relational-graph-action-view:v1",
    "outcome": "acfqp:relational-graph-outcome-view:v1",
    "row": "acfqp:relational-graph-observed-row:v1",
    "log": "acfqp:relational-graph-source-log:v1",
    "program": "acfqp:relational-graph-program:v1",
    "registry": "acfqp:relational-graph-program-registry:v1",
    "schema": "acfqp:relational-graph-support-key-schema:v1",
    "proposal": "acfqp:relational-graph-coordinate-proposal:v1",
    "metrics": "acfqp:relational-graph-synthesis-metrics:v1",
}


class RelationalGraphCoreInvariantViolation(ValueError):
    """A graph, log, program, proposal, or verification invariant failed."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise RelationalGraphCoreInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise RelationalGraphCoreInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _exact_tuple(value: Any, item_type: type, field: str) -> tuple[Any, ...]:
    if type(value) is not tuple or any(type(item) is not item_type for item in value):
        raise RelationalGraphCoreInvariantViolation(
            f"{field} rejects nested runtime substitutions"
        )
    return value


def _runtime_shape(claimed: Any, expected: Any, path: str) -> None:
    if type(claimed) is not type(expected):
        raise RelationalGraphCoreInvariantViolation(
            f"{path} contains a nested runtime substitution"
        )
    if type(expected) is tuple:
        if len(claimed) != len(expected):
            raise RelationalGraphCoreInvariantViolation(f"{path} length changed")
        for index, (left, right) in enumerate(zip(claimed, expected)):
            _runtime_shape(left, right, f"{path}[{index}]")
        return
    if is_dataclass(expected):
        for field in fields(type(expected)):
            _runtime_shape(
                object.__getattribute__(claimed, field.name),
                object.__getattribute__(expected, field.name),
                f"{path}.{field.name}",
            )


@dataclass(frozen=True, slots=True)
class GraphTopologyV1:
    """A canonically encoded finite simple undirected graph."""

    vertex_count: int
    edges: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        if type(self.vertex_count) is not int or self.vertex_count <= 1:
            raise RelationalGraphCoreInvariantViolation(
                "graph vertex_count must be an integer greater than one"
            )
        if (
            type(self.edges) is not tuple
            or not self.edges
            or any(
                type(edge) is not tuple
                or len(edge) != 2
                or any(type(vertex) is not int for vertex in edge)
                or not 0 <= edge[0] < edge[1] < self.vertex_count
                for edge in self.edges
            )
            or self.edges != tuple(sorted(set(self.edges)))
        ):
            raise RelationalGraphCoreInvariantViolation(
                "graph edges must be unique canonical undirected pairs"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.graph_topology.v1",
            "schema_version": SCHEMA_VERSION,
            "vertex_count": self.vertex_count,
            "edges": [list(edge) for edge in self.edges],
        }

    @property
    def topology_id(self) -> str:
        return _content_id("topology", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "topology_id": self.topology_id}

    def neighbors(self, vertex: int) -> frozenset[int]:
        if type(vertex) is not int or not 0 <= vertex < self.vertex_count:
            raise RelationalGraphCoreInvariantViolation(
                "neighbor lookup vertex is outside the graph"
            )
        return frozenset(
            second if first == vertex else first
            for first, second in self.edges
            if first == vertex or second == vertex
        )


@dataclass(frozen=True, slots=True)
class GraphStateViewV1:
    topology_id: str
    ranks: tuple[int, ...]
    failure: bool
    remaining_horizon: int

    def __post_init__(self) -> None:
        _cid(self.topology_id, "state topology")
        if (
            type(self.ranks) is not tuple
            or len(self.ranks) <= 1
            or any(
                type(rank) is not int or not 0 <= rank <= REGISTERED_RANK_CAP
                for rank in self.ranks
            )
            or type(self.failure) is not bool
            or type(self.remaining_horizon) is not int
            or not 0 <= self.remaining_horizon <= REGISTERED_HORIZON
        ):
            raise RelationalGraphCoreInvariantViolation(
                "graph state view is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.graph_state_view.v1",
            "schema_version": SCHEMA_VERSION,
            "topology_id": self.topology_id,
            "ranks": list(self.ranks),
            "failure": self.failure,
            "remaining_horizon": self.remaining_horizon,
        }

    @property
    def state_id(self) -> str:
        return _content_id("state", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "state_id": self.state_id}


@dataclass(frozen=True, slots=True)
class GraphActionViewV1:
    state_id: str
    first: int
    second: int
    survivor: int

    def __post_init__(self) -> None:
        _cid(self.state_id, "action state")
        if (
            type(self.first) is not int
            or type(self.second) is not int
            or type(self.survivor) is not int
            or not 0 <= self.first < self.second
            or self.survivor not in (self.first, self.second)
        ):
            raise RelationalGraphCoreInvariantViolation(
                "graph action view is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.graph_action_view.v1",
            "schema_version": SCHEMA_VERSION,
            "state_id": self.state_id,
            "pair": [self.first, self.second],
            "survivor": self.survivor,
        }

    @property
    def action_id(self) -> str:
        return _content_id("action", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "action_id": self.action_id}


@dataclass(frozen=True, slots=True)
class GraphOutcomeViewV1:
    next_state: GraphStateViewV1
    probability: Fraction
    normalized_reward: Fraction
    failure: bool
    terminal: bool

    def __post_init__(self) -> None:
        if (
            type(self.next_state) is not GraphStateViewV1
            or type(self.probability) is not Fraction
            or not 0 < self.probability <= 1
            or type(self.normalized_reward) is not Fraction
            or not 0 <= self.normalized_reward <= 1
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
            or self.failure != self.next_state.failure
            or (self.failure and not self.terminal)
        ):
            raise RelationalGraphCoreInvariantViolation(
                "graph outcome view is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.graph_outcome_view.v1",
            "schema_version": SCHEMA_VERSION,
            "next_state": self.next_state.to_document(),
            "probability": _fdoc(self.probability),
            "normalized_reward": _fdoc(self.normalized_reward),
            "failure": self.failure,
            "terminal": self.terminal,
        }

    @property
    def outcome_id(self) -> str:
        return _content_id("outcome", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "outcome_id": self.outcome_id}


@dataclass(frozen=True, slots=True)
class GraphObservedRowV1:
    state: GraphStateViewV1
    action: GraphActionViewV1
    legal_actions: tuple[GraphActionViewV1, ...]
    outcomes: tuple[GraphOutcomeViewV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.state) is not GraphStateViewV1
            or type(self.action) is not GraphActionViewV1
        ):
            raise RelationalGraphCoreInvariantViolation(
                "observed row rejects substituted views"
            )
        _exact_tuple(
            self.legal_actions,
            GraphActionViewV1,
            "observed row legal actions",
        )
        _exact_tuple(self.outcomes, GraphOutcomeViewV1, "observed row outcomes")
        if (
            self.state.failure
            or self.state.remaining_horizon <= 0
            or self.action.state_id != self.state.state_id
            or self.action not in self.legal_actions
            or tuple(
                (item.first, item.second, item.survivor)
                for item in self.legal_actions
            )
            != tuple(
                sorted(
                    {
                        (item.first, item.second, item.survivor)
                        for item in self.legal_actions
                    }
                )
            )
            or not self.outcomes
            or sum(
                (item.probability for item in self.outcomes),
                Fraction(0),
            )
            != 1
            or any(
                item.next_state.topology_id != self.state.topology_id
                or item.next_state.remaining_horizon
                != self.state.remaining_horizon - 1
                for item in self.outcomes
            )
        ):
            raise RelationalGraphCoreInvariantViolation(
                "observed row state/action/outcome binding is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.graph_observed_row.v1",
            "schema_version": SCHEMA_VERSION,
            "state": self.state.to_document(),
            "action": self.action.to_document(),
            "legal_actions": [item.to_document() for item in self.legal_actions],
            "outcomes": [item.to_document() for item in self.outcomes],
        }

    @property
    def row_id(self) -> str:
        return _content_id("row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "row_id": self.row_id}


def _legal_action_tuples(
    topology: GraphTopologyV1,
    ranks: tuple[int, ...],
) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (first, second, survivor)
        for first, second in topology.edges
        if ranks[first] > 0 and ranks[first] == ranks[second]
        for survivor in (first, second)
    )


def _legal_action_views(
    topology: GraphTopologyV1,
    state: GraphStateViewV1,
) -> tuple[GraphActionViewV1, ...]:
    return tuple(
        GraphActionViewV1(state.state_id, first, second, survivor)
        for first, second, survivor in _legal_action_tuples(topology, state.ranks)
    )


@dataclass(frozen=True, slots=True)
class AnonymousGraphSourceLogV1:
    topologies: tuple[GraphTopologyV1, ...]
    rows: tuple[GraphObservedRowV1, ...]
    completeness_kind: str = "all_actions_and_active_successor_closure_v1"

    def __post_init__(self) -> None:
        _exact_tuple(self.topologies, GraphTopologyV1, "source topologies")
        _exact_tuple(self.rows, GraphObservedRowV1, "source rows")
        if (
            not self.topologies
            or tuple(item.topology_id for item in self.topologies)
            != tuple(sorted({item.topology_id for item in self.topologies}))
            or not self.rows
            or tuple(item.row_id for item in self.rows)
            != tuple(sorted({item.row_id for item in self.rows}))
            or self.completeness_kind
            != "all_actions_and_active_successor_closure_v1"
        ):
            raise RelationalGraphCoreInvariantViolation(
                "source log ordering, uniqueness, or completeness label changed"
            )
        topology_by_id = {item.topology_id: item for item in self.topologies}
        rows_by_state: dict[str, list[GraphObservedRowV1]] = defaultdict(list)
        state_by_id: dict[str, GraphStateViewV1] = {}
        for row in self.rows:
            topology = topology_by_id.get(row.state.topology_id)
            if (
                topology is None
                or len(row.state.ranks) != topology.vertex_count
                or (row.action.first, row.action.second) not in topology.edges
                or row.state.ranks[row.action.first] == 0
                or row.state.ranks[row.action.first]
                != row.state.ranks[row.action.second]
                or row.legal_actions != _legal_action_views(topology, row.state)
            ):
                raise RelationalGraphCoreInvariantViolation(
                    "source row is not legal under its topology"
                )
            rows_by_state[row.state.state_id].append(row)
            state_by_id[row.state.state_id] = row.state
        for state_id, state_rows in rows_by_state.items():
            legal = state_rows[0].legal_actions
            if (
                any(item.state != state_by_id[state_id] for item in state_rows)
                or any(item.legal_actions != legal for item in state_rows)
                or {
                    item.action.action_id for item in state_rows
                }
                != {item.action_id for item in legal}
                or len(state_rows) != len(legal)
            ):
                raise RelationalGraphCoreInvariantViolation(
                    "source log omits or duplicates a legal state/action row"
                )
        required_successors = {
            outcome.next_state.state_id
            for row in self.rows
            for outcome in row.outcomes
            if not outcome.failure
            and outcome.next_state.remaining_horizon > 0
        }
        if not required_successors.issubset(rows_by_state):
            raise RelationalGraphCoreInvariantViolation(
                "source log omits an active successor state closure"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.anonymous_graph_source_log.v1",
            "schema_version": SCHEMA_VERSION,
            "topologies": [item.to_document() for item in self.topologies],
            "rows": [item.to_document() for item in self.rows],
            "completeness_kind": self.completeness_kind,
        }

    @property
    def source_log_id(self) -> str:
        return _content_id("log", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "source_log_id": self.source_log_id}


class GraphProgramType(str, Enum):
    CELL_SET = "CELL_SET"
    ACTION_SET = "ACTION_SET"
    CELL = "CELL"
    INTEGER = "INTEGER"
    SIGNATURE = "SIGNATURE"


class GraphProgramContext(str, Enum):
    STATE = "STATE"
    STATE_ACTION = "STATE_ACTION"


_PRIMITIVES: dict[
    str,
    tuple[GraphProgramType, GraphProgramContext],
] = {
    "all_cells": (GraphProgramType.CELL_SET, GraphProgramContext.STATE),
    "occupied_cells": (GraphProgramType.CELL_SET, GraphProgramContext.STATE),
    "legal_actions": (GraphProgramType.ACTION_SET, GraphProgramContext.STATE),
    "survivor_cell": (GraphProgramType.CELL, GraphProgramContext.STATE_ACTION),
    "pair_cells": (GraphProgramType.CELL_SET, GraphProgramContext.STATE_ACTION),
    "rank_degree_signature": (
        GraphProgramType.SIGNATURE,
        GraphProgramContext.STATE,
    ),
}

_OPERATORS: dict[str, tuple[tuple[GraphProgramType, ...], GraphProgramType]] = {
    "cardinality_cells": ((GraphProgramType.CELL_SET,), GraphProgramType.INTEGER),
    "cardinality_actions": (
        (GraphProgramType.ACTION_SET,),
        GraphProgramType.INTEGER,
    ),
    "adjacent_filter": (
        (GraphProgramType.CELL, GraphProgramType.CELL_SET),
        GraphProgramType.CELL_SET,
    ),
    "set_difference": (
        (GraphProgramType.CELL_SET, GraphProgramType.CELL_SET),
        GraphProgramType.CELL_SET,
    ),
}

_OPERATION_ORDER = tuple(_PRIMITIVES) + tuple(_OPERATORS)


@dataclass(frozen=True, slots=True)
class GraphCoordinateProgramV1:
    operation: str
    result_type: GraphProgramType
    context: GraphProgramContext
    arguments: tuple["GraphCoordinateProgramV1", ...] = ()

    def __post_init__(self) -> None:
        if type(self.operation) is not str:
            raise RelationalGraphCoreInvariantViolation(
                "program operation must be a string"
            )
        _exact_tuple(
            self.arguments,
            GraphCoordinateProgramV1,
            "program arguments",
        )
        primitive = _PRIMITIVES.get(self.operation)
        if primitive is not None:
            if self.arguments or primitive != (self.result_type, self.context):
                raise RelationalGraphCoreInvariantViolation(
                    "program primitive type/context mismatch"
                )
            return
        operator = _OPERATORS.get(self.operation)
        if operator is None:
            raise RelationalGraphCoreInvariantViolation(
                "program operation is unregistered"
            )
        argument_types, result_type = operator
        expected_context = (
            GraphProgramContext.STATE_ACTION
            if any(
                item.context is GraphProgramContext.STATE_ACTION
                for item in self.arguments
            )
            else GraphProgramContext.STATE
        )
        if (
            tuple(item.result_type for item in self.arguments) != argument_types
            or self.result_type is not result_type
            or self.context is not expected_context
            or self.depth > MAX_PROGRAM_DEPTH
        ):
            raise RelationalGraphCoreInvariantViolation(
                "program operator type/context/depth mismatch"
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
            "schema": "acfqp.graph_coordinate_program.v1",
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


def _primitive(operation: str) -> GraphCoordinateProgramV1:
    result_type, context = _PRIMITIVES[operation]
    return GraphCoordinateProgramV1(operation, result_type, context)


def _operator(
    operation: str,
    arguments: tuple[GraphCoordinateProgramV1, ...],
) -> GraphCoordinateProgramV1:
    context = (
        GraphProgramContext.STATE_ACTION
        if any(
            item.context is GraphProgramContext.STATE_ACTION
            for item in arguments
        )
        else GraphProgramContext.STATE
    )
    return GraphCoordinateProgramV1(
        operation,
        _OPERATORS[operation][1],
        context,
        arguments,
    )


def _program_order_key(program: GraphCoordinateProgramV1) -> tuple[Any, ...]:
    return (
        program.node_count,
        program.depth,
        _OPERATION_ORDER.index(program.operation),
        program.rendered,
        program.program_id,
    )


@dataclass(frozen=True, slots=True)
class _EvaluationCovariate:
    topology: GraphTopologyV1
    state: GraphStateViewV1
    action: GraphActionViewV1 | None
    legal_actions: tuple[GraphActionViewV1, ...]


def _evaluate_program(
    program: GraphCoordinateProgramV1,
    covariate: _EvaluationCovariate,
) -> (
    frozenset[int]
    | tuple[GraphActionViewV1, ...]
    | tuple[tuple[int, int], ...]
    | int
):
    operation = program.operation
    if operation == "all_cells":
        return frozenset(range(covariate.topology.vertex_count))
    if operation == "occupied_cells":
        return frozenset(
            index for index, rank in enumerate(covariate.state.ranks) if rank > 0
        )
    if operation == "legal_actions":
        return covariate.legal_actions
    if operation == "survivor_cell":
        if covariate.action is None:
            raise RelationalGraphCoreInvariantViolation(
                "action-context program lacks an action"
            )
        return covariate.action.survivor
    if operation == "pair_cells":
        if covariate.action is None:
            raise RelationalGraphCoreInvariantViolation(
                "action-context program lacks an action"
            )
        return frozenset(
            (covariate.action.first, covariate.action.second)
        )
    if operation == "rank_degree_signature":
        positive_ranks = tuple(
            rank for rank in covariate.state.ranks if rank > 0
        )
        if not positive_ranks:
            return ()
        minimum = min(positive_ranks)
        return tuple(
            sorted(
                (
                    rank - minimum,
                    len(covariate.topology.neighbors(vertex)),
                )
                for vertex, rank in enumerate(covariate.state.ranks)
                if rank > 0
            )
        )
    values = tuple(
        _evaluate_program(argument, covariate)
        for argument in program.arguments
    )
    if operation == "cardinality_cells":
        if type(values[0]) is not frozenset:
            raise RelationalGraphCoreInvariantViolation(
                "cardinality_cells received a non-cell-set"
            )
        return len(values[0])
    if operation == "cardinality_actions":
        if type(values[0]) is not tuple:
            raise RelationalGraphCoreInvariantViolation(
                "cardinality_actions received a non-action-set"
            )
        return len(values[0])
    if operation == "adjacent_filter":
        vertex, cells = values
        if type(vertex) is not int or type(cells) is not frozenset:
            raise RelationalGraphCoreInvariantViolation(
                "adjacent_filter argument runtime types changed"
            )
        return covariate.topology.neighbors(vertex) & cells
    if operation == "set_difference":
        first, second = values
        if type(first) is not frozenset or type(second) is not frozenset:
            raise RelationalGraphCoreInvariantViolation(
                "set_difference argument runtime types changed"
            )
        return first - second
    raise RelationalGraphCoreInvariantViolation(
        "program evaluator reached an unregistered operation"
    )


def _value_key(
    result_type: GraphProgramType,
    value: Any,
) -> tuple[str, Any]:
    if result_type is GraphProgramType.INTEGER and type(value) is int:
        return ("INTEGER", value)
    if (
        result_type is GraphProgramType.CELL_SET
        and type(value) is frozenset
    ):
        return ("CELL_SET", tuple(sorted(value)))
    if (
        result_type is GraphProgramType.ACTION_SET
        and type(value) is tuple
        and all(
        type(item) is GraphActionViewV1 for item in value
        )
    ):
        return ("ACTION_SET", tuple(item.action_id for item in value))
    if (
        result_type is GraphProgramType.CELL
        and type(value) is int
    ):
        return ("CELL", value)
    if (
        result_type is GraphProgramType.SIGNATURE
        and type(value) is tuple
        and all(
            type(item) is tuple
            and len(item) == 2
            and all(type(component) is int for component in item)
            for item in value
        )
    ):
        return ("SIGNATURE", value)
    raise RelationalGraphCoreInvariantViolation(
        "program evaluator produced an unregistered value"
    )


def evaluate_state_coordinate_v1(
    program: GraphCoordinateProgramV1,
    topology: GraphTopologyV1,
    state: GraphStateViewV1,
) -> tuple[str, Any]:
    """Evaluate one registered state AST and return a canonical tagged value."""

    if (
        type(program) is not GraphCoordinateProgramV1
        or type(topology) is not GraphTopologyV1
        or type(state) is not GraphStateViewV1
        or program.context is not GraphProgramContext.STATE
        or state.topology_id != topology.topology_id
        or len(state.ranks) != topology.vertex_count
    ):
        raise RelationalGraphCoreInvariantViolation(
            "state coordinate evaluator binding or runtime type changed"
        )
    legal_actions = (
        _legal_action_views(topology, state)
        if not state.failure
        else ()
    )
    value = _evaluate_program(
        program,
        _EvaluationCovariate(
            topology,
            state,
            None,
            legal_actions,
        ),
    )
    return _value_key(program.result_type, value)


def evaluate_action_coordinate_v1(
    program: GraphCoordinateProgramV1,
    topology: GraphTopologyV1,
    state: GraphStateViewV1,
    action: GraphActionViewV1,
    legal_actions: tuple[GraphActionViewV1, ...],
) -> tuple[str, Any]:
    """Evaluate one registered action AST and return a canonical tagged value."""

    if (
        type(program) is not GraphCoordinateProgramV1
        or type(topology) is not GraphTopologyV1
        or type(state) is not GraphStateViewV1
        or type(action) is not GraphActionViewV1
        or program.context is not GraphProgramContext.STATE_ACTION
        or state.topology_id != topology.topology_id
        or len(state.ranks) != topology.vertex_count
    ):
        raise RelationalGraphCoreInvariantViolation(
            "action coordinate evaluator binding or runtime type changed"
        )
    _exact_tuple(
        legal_actions,
        GraphActionViewV1,
        "action coordinate legal actions",
    )
    expected_legal = (
        _legal_action_views(topology, state)
        if not state.failure
        else ()
    )
    if (
        legal_actions != expected_legal
        or action not in legal_actions
        or action.state_id != state.state_id
    ):
        raise RelationalGraphCoreInvariantViolation(
            "action coordinate evaluator received a stale/illegal catalogue"
        )
    value = _evaluate_program(
        program,
        _EvaluationCovariate(
            topology,
            state,
            action,
            legal_actions,
        ),
    )
    return _value_key(program.result_type, value)


def _syntactic_program_closure() -> tuple[GraphCoordinateProgramV1, ...]:
    programs = [_primitive(operation) for operation in _PRIMITIVES]
    by_id = {item.program_id: item for item in programs}
    for target_depth in range(1, MAX_PROGRAM_DEPTH + 1):
        prior = tuple(by_id.values())
        by_type: dict[
            GraphProgramType,
            tuple[GraphCoordinateProgramV1, ...],
        ] = {
            result_type: tuple(
                item for item in prior if item.result_type is result_type
            )
            for result_type in GraphProgramType
        }
        generated: list[GraphCoordinateProgramV1] = []
        for operation, (argument_types, _) in _OPERATORS.items():
            for arguments in product(
                *(by_type[item] for item in argument_types)
            ):
                if 1 + max(item.depth for item in arguments) != target_depth:
                    continue
                generated.append(_operator(operation, tuple(arguments)))
        for program in sorted(generated, key=_program_order_key):
            by_id.setdefault(program.program_id, program)
    return tuple(sorted(by_id.values(), key=_program_order_key))


def _topology_lookup(
    source_log: AnonymousGraphSourceLogV1,
) -> dict[str, GraphTopologyV1]:
    return {item.topology_id: item for item in source_log.topologies}


def _state_covariates(
    source_log: AnonymousGraphSourceLogV1,
) -> tuple[_EvaluationCovariate, ...]:
    topology_by_id = _topology_lookup(source_log)
    states: dict[str, GraphStateViewV1] = {}
    for row in source_log.rows:
        states[row.state.state_id] = row.state
        for outcome in row.outcomes:
            states[outcome.next_state.state_id] = outcome.next_state
    return tuple(
        _EvaluationCovariate(
            topology_by_id[state.topology_id],
            state,
            None,
            _legal_action_views(topology_by_id[state.topology_id], state)
            if not state.failure
            else (),
        )
        for state in sorted(states.values(), key=lambda item: item.state_id)
    )


def _action_covariates(
    source_log: AnonymousGraphSourceLogV1,
) -> tuple[_EvaluationCovariate, ...]:
    topology_by_id = _topology_lookup(source_log)
    return tuple(
        _EvaluationCovariate(
            topology_by_id[row.state.topology_id],
            row.state,
            row.action,
            row.legal_actions,
        )
        for row in source_log.rows
    )


@dataclass(frozen=True, slots=True)
class GraphProgramRegistryV1:
    source_log_id: str
    programs: tuple[GraphCoordinateProgramV1, ...]
    syntactic_program_count: int
    semantic_program_count_by_depth: tuple[int, ...]
    grammar_operations: tuple[str, ...] = _OPERATION_ORDER
    max_depth: int = MAX_PROGRAM_DEPTH

    def __post_init__(self) -> None:
        _cid(self.source_log_id, "program registry source log")
        _exact_tuple(
            self.programs,
            GraphCoordinateProgramV1,
            "program registry programs",
        )
        if (
            not self.programs
            or tuple(item.program_id for item in self.programs)
            != tuple(sorted({item.program_id for item in self.programs}))
            or type(self.syntactic_program_count) is not int
            or self.syntactic_program_count < len(self.programs)
            or type(self.semantic_program_count_by_depth) is not tuple
            or len(self.semantic_program_count_by_depth)
            != MAX_PROGRAM_DEPTH + 1
            or any(
                type(item) is not int or item < 0
                for item in self.semantic_program_count_by_depth
            )
            or sum(self.semantic_program_count_by_depth) != len(self.programs)
            or self.grammar_operations != _OPERATION_ORDER
            or self.max_depth != MAX_PROGRAM_DEPTH
        ):
            raise RelationalGraphCoreInvariantViolation(
                "program registry coverage or ordering changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.graph_program_registry.v1",
            "schema_version": SCHEMA_VERSION,
            "source_log_id": self.source_log_id,
            "programs": [item.to_document() for item in self.programs],
            "syntactic_program_count": self.syntactic_program_count,
            "semantic_program_count_by_depth": list(
                self.semantic_program_count_by_depth
            ),
            "grammar_operations": list(self.grammar_operations),
            "max_depth": self.max_depth,
        }

    @property
    def registry_id(self) -> str:
        return _content_id("registry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registry_id": self.registry_id}


def generate_relational_graph_program_registry_v1(
    source_log: AnonymousGraphSourceLogV1,
) -> GraphProgramRegistryV1:
    if type(source_log) is not AnonymousGraphSourceLogV1:
        raise RelationalGraphCoreInvariantViolation(
            "program closure requires the exact source-log type"
        )
    syntactic = _syntactic_program_closure()
    state_covariates = _state_covariates(source_log)
    action_covariates = _action_covariates(source_log)
    representatives: dict[
        tuple[Any, ...],
        GraphCoordinateProgramV1,
    ] = {}
    for program in syntactic:
        covariates = (
            state_covariates
            if program.context is GraphProgramContext.STATE
            else action_covariates
        )
        signature = (
            program.result_type.value,
            program.context.value,
            tuple(
                _value_key(
                    program.result_type,
                    _evaluate_program(program, item),
                )
                for item in covariates
            ),
        )
        prior = representatives.get(signature)
        if prior is None or _program_order_key(program) < _program_order_key(prior):
            representatives[signature] = program
    programs = tuple(
        sorted(
            representatives.values(),
            key=lambda item: item.program_id,
        )
    )
    counts = tuple(
        sum(item.depth == depth for item in programs)
        for depth in range(MAX_PROGRAM_DEPTH + 1)
    )
    return GraphProgramRegistryV1(
        source_log.source_log_id,
        programs,
        len(syntactic),
        counts,
    )


def _state_program_value(
    program: GraphCoordinateProgramV1,
    topology: GraphTopologyV1,
    state: GraphStateViewV1,
) -> int:
    legal = (
        _legal_action_views(topology, state)
        if not state.failure
        else ()
    )
    value = _evaluate_program(
        program,
        _EvaluationCovariate(topology, state, None, legal),
    )
    if type(value) is not int:
        raise RelationalGraphCoreInvariantViolation(
            "state coordinate is not integer-valued"
        )
    return value


def _action_program_value(
    program: GraphCoordinateProgramV1,
    topology: GraphTopologyV1,
    row: GraphObservedRowV1,
) -> int:
    value = _evaluate_program(
        program,
        _EvaluationCovariate(
            topology,
            row.state,
            row.action,
            row.legal_actions,
        ),
    )
    if type(value) is not int:
        raise RelationalGraphCoreInvariantViolation(
            "action coordinate is not integer-valued"
        )
    return value


@dataclass(frozen=True, slots=True)
class _CandidateSummary:
    state_program: GraphCoordinateProgramV1
    action_program: GraphCoordinateProgramV1
    ground_state_count: int
    ground_row_count: int
    abstract_state_count: int
    abstract_support_count: int
    alias_pair_count: int
    availability_variant_count: int
    transition_alias_width: Fraction
    reward_alias_width: Fraction
    sound_alias_width: Fraction
    admissible: bool

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


def _candidate_summary(
    source_log: AnonymousGraphSourceLogV1,
    state_program: GraphCoordinateProgramV1,
    action_program: GraphCoordinateProgramV1,
) -> _CandidateSummary:
    topology_by_id = _topology_lookup(source_log)
    state_values: dict[str, int] = {}
    ground_states: dict[str, GraphStateViewV1] = {}
    for row in source_log.rows:
        ground_states[row.state.state_id] = row.state
        state_values.setdefault(
            row.state.state_id,
            _state_program_value(
                state_program,
                topology_by_id[row.state.topology_id],
                row.state,
            ),
        )
        for outcome in row.outcomes:
            ground_states[outcome.next_state.state_id] = outcome.next_state
            state_values.setdefault(
                outcome.next_state.state_id,
                _state_program_value(
                    state_program,
                    topology_by_id[outcome.next_state.topology_id],
                    outcome.next_state,
                ),
            )

    grouped: dict[
        tuple[int, int, int],
        list[GraphObservedRowV1],
    ] = defaultdict(list)
    action_values_by_state: dict[str, set[int]] = defaultdict(set)
    abstract_state_members: dict[tuple[int, int], set[str]] = defaultdict(set)
    for row in source_log.rows:
        topology = topology_by_id[row.state.topology_id]
        state_value = state_values[row.state.state_id]
        action_value = _action_program_value(
            action_program,
            topology,
            row,
        )
        grouped[
            (row.state.remaining_horizon, state_value, action_value)
        ].append(row)
        action_values_by_state[row.state.state_id].add(action_value)
        abstract_state_members[
            (row.state.remaining_horizon, state_value)
        ].add(row.state.state_id)

    availability_by_abstract_state: dict[
        tuple[int, int],
        set[tuple[int, ...]],
    ] = defaultdict(set)
    for abstract_state, members in abstract_state_members.items():
        for state_id in members:
            availability_by_abstract_state[abstract_state].add(
                tuple(sorted(action_values_by_state[state_id]))
            )
    availability_variants = sum(
        len(items) - 1
        for items in availability_by_abstract_state.values()
        if len(items) > 1
    )

    transition_width = Fraction(0)
    reward_width = Fraction(0)
    alias_pairs = 0
    for rows in grouped.values():
        alias_pairs += len(rows) * (len(rows) - 1) // 2
        distributions: list[dict[tuple[Any, ...], Fraction]] = []
        rewards: list[Fraction] = []
        destinations: set[tuple[Any, ...]] = set()
        for row in rows:
            distribution: dict[tuple[Any, ...], Fraction] = defaultdict(Fraction)
            expected_reward = Fraction(0)
            for outcome in row.outcomes:
                if outcome.failure:
                    destination: tuple[Any, ...] = ("FAILURE",)
                elif outcome.next_state.remaining_horizon == 0:
                    destination = ("SAFE_TERMINAL",)
                else:
                    destination = (
                        "ACTIVE",
                        outcome.next_state.remaining_horizon,
                        state_values[outcome.next_state.state_id],
                    )
                distribution[destination] += outcome.probability
                expected_reward += (
                    outcome.probability * outcome.normalized_reward
                )
                destinations.add(destination)
            distributions.append(distribution)
            rewards.append(expected_reward)
        for destination in destinations:
            values = [
                item.get(destination, Fraction(0))
                for item in distributions
            ]
            transition_width = max(
                transition_width,
                max(values) - min(values),
            )
        reward_width = max(reward_width, max(rewards) - min(rewards))

    row_state_ids = {item.state.state_id for item in source_log.rows}
    state_coordinate_values = {
        state_values[state_id] for state_id in row_state_ids
    }
    action_coordinate_values = {
        _action_program_value(
            action_program,
            topology_by_id[row.state.topology_id],
            row,
        )
        for row in source_log.rows
    }
    abstract_state_count = len(abstract_state_members)
    abstract_support_count = len(grouped)
    admissible = (
        1 < len(state_coordinate_values) < len(row_state_ids)
        and 1 < len(action_coordinate_values) < len(source_log.rows)
        and abstract_state_count < len(row_state_ids)
        and abstract_support_count < len(source_log.rows)
    )
    return _CandidateSummary(
        state_program,
        action_program,
        len(row_state_ids),
        len(source_log.rows),
        abstract_state_count,
        abstract_support_count,
        alias_pairs,
        availability_variants,
        transition_width,
        reward_width,
        max(transition_width, reward_width),
        admissible,
    )


@dataclass(frozen=True, slots=True)
class GraphAnonymousSupportKeySchemaV1:
    fields: tuple[str, ...] = (
        "remaining_horizon",
        "state_coordinate_value",
        "action_coordinate_value",
    )
    destination_key_fields: tuple[str, ...] = (
        "status",
        "remaining_horizon",
        "state_coordinate_value",
    )
    target_instantiation_required: bool = True

    def __post_init__(self) -> None:
        if (
            self.fields
            != (
                "remaining_horizon",
                "state_coordinate_value",
                "action_coordinate_value",
            )
            or self.destination_key_fields
            != (
                "status",
                "remaining_horizon",
                "state_coordinate_value",
            )
            or self.target_instantiation_required is not True
        ):
            raise RelationalGraphCoreInvariantViolation(
                "anonymous support-key schema changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.graph_anonymous_support_key_schema.v1",
            "schema_version": SCHEMA_VERSION,
            "fields": list(self.fields),
            "destination_key_fields": list(self.destination_key_fields),
            "target_instantiation_required": self.target_instantiation_required,
        }

    @property
    def support_schema_id(self) -> str:
        return _content_id("schema", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "support_schema_id": self.support_schema_id,
        }


@dataclass(frozen=True, slots=True)
class RelationalGraphCoordinateProposalV1:
    source_log_id: str
    program_registry_id: str
    state_program: GraphCoordinateProgramV1
    action_program: GraphCoordinateProgramV1
    support_key_schema: GraphAnonymousSupportKeySchemaV1
    grammar_profile_key: str = PROFILE_KEY
    candidate_universe: str = "complete_integer_state_x_action_pairs_v1"
    selection_rule: str = (
        "min_sound_alias_width_then_supports_states_complexity_lexical_v1"
    )
    source_dynamics_included: bool = False
    source_decisions_included: bool = False
    target_identity_included: bool = False
    query_identity_included: bool = False

    def __post_init__(self) -> None:
        _cid(self.source_log_id, "proposal source log")
        _cid(self.program_registry_id, "proposal program registry")
        if (
            type(self.state_program) is not GraphCoordinateProgramV1
            or type(self.action_program) is not GraphCoordinateProgramV1
            or type(self.support_key_schema)
            is not GraphAnonymousSupportKeySchemaV1
            or self.state_program.result_type is not GraphProgramType.INTEGER
            or self.state_program.context is not GraphProgramContext.STATE
            or self.action_program.result_type is not GraphProgramType.INTEGER
            or self.action_program.context
            is not GraphProgramContext.STATE_ACTION
            or self.grammar_profile_key != PROFILE_KEY
            or self.candidate_universe
            != "complete_integer_state_x_action_pairs_v1"
            or self.selection_rule
            != "min_sound_alias_width_then_supports_states_complexity_lexical_v1"
            or self.source_dynamics_included is not False
            or self.source_decisions_included is not False
            or self.target_identity_included is not False
            or self.query_identity_included is not False
        ):
            raise RelationalGraphCoreInvariantViolation(
                "coordinate proposal type or authority boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.relational_graph_coordinate_proposal.v1",
            "schema_version": SCHEMA_VERSION,
            "source_log_id": self.source_log_id,
            "program_registry_id": self.program_registry_id,
            "state_program": self.state_program.to_document(),
            "action_program": self.action_program.to_document(),
            "support_key_schema": self.support_key_schema.to_document(),
            "grammar_profile_key": self.grammar_profile_key,
            "candidate_universe": self.candidate_universe,
            "selection_rule": self.selection_rule,
            "source_dynamics_included": self.source_dynamics_included,
            "source_decisions_included": self.source_decisions_included,
            "target_identity_included": self.target_identity_included,
            "query_identity_included": self.query_identity_included,
        }

    @property
    def proposal_id(self) -> str:
        return _content_id("proposal", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proposal_id": self.proposal_id}


@dataclass(frozen=True, slots=True)
class RelationalGraphSynthesisMetricsV1:
    source_log_id: str
    proposal_id: str
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
    alias_pair_count: int
    availability_variant_count: int
    transition_alias_width: Fraction
    reward_alias_width: Fraction
    sound_alias_width: Fraction
    selected_state_program: str
    selected_action_program: str

    def __post_init__(self) -> None:
        _cid(self.source_log_id, "metrics source log")
        _cid(self.proposal_id, "metrics proposal")
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
            self.alias_pair_count,
            self.availability_variant_count,
        )
        if (
            any(type(item) is not int or item < 0 for item in integer_fields)
            or type(self.semantic_program_count_by_depth) is not tuple
            or any(
                type(item) is not int or item < 0
                for item in self.semantic_program_count_by_depth
            )
            or any(
                type(item) is not Fraction or not 0 <= item <= 1
                for item in (
                    self.transition_alias_width,
                    self.reward_alias_width,
                    self.sound_alias_width,
                )
            )
            or self.sound_alias_width
            != max(self.transition_alias_width, self.reward_alias_width)
            or type(self.selected_state_program) is not str
            or type(self.selected_action_program) is not str
            or not self.selected_state_program
            or not self.selected_action_program
        ):
            raise RelationalGraphCoreInvariantViolation(
                "synthesis metrics are invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.relational_graph_synthesis_metrics.v1",
            "schema_version": SCHEMA_VERSION,
            "source_log_id": self.source_log_id,
            "proposal_id": self.proposal_id,
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
            "alias_pair_count": self.alias_pair_count,
            "availability_variant_count": self.availability_variant_count,
            "transition_alias_width": _fdoc(self.transition_alias_width),
            "reward_alias_width": _fdoc(self.reward_alias_width),
            "sound_alias_width": _fdoc(self.sound_alias_width),
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
    registry: GraphProgramRegistryV1
    candidates: tuple[_CandidateSummary, ...]
    selected: _CandidateSummary
    proposal: RelationalGraphCoordinateProposalV1


def _run_synthesis(
    source_log: AnonymousGraphSourceLogV1,
) -> _Synthesis:
    registry = generate_relational_graph_program_registry_v1(source_log)
    state_programs = tuple(
        item
        for item in registry.programs
        if item.result_type is GraphProgramType.INTEGER
        and item.context is GraphProgramContext.STATE
    )
    action_programs = tuple(
        item
        for item in registry.programs
        if item.result_type is GraphProgramType.INTEGER
        and item.context is GraphProgramContext.STATE_ACTION
    )
    candidates = tuple(
        _candidate_summary(source_log, state_program, action_program)
        for state_program in state_programs
        for action_program in action_programs
    )
    admissible = tuple(item for item in candidates if item.admissible)
    if not admissible:
        raise RelationalGraphCoreInvariantViolation(
            "complete source-only candidate search found no compressive pair"
        )
    selected = min(admissible, key=lambda item: item.selection_key)
    proposal = RelationalGraphCoordinateProposalV1(
        source_log.source_log_id,
        registry.registry_id,
        selected.state_program,
        selected.action_program,
        GraphAnonymousSupportKeySchemaV1(),
    )
    return _Synthesis(registry, candidates, selected, proposal)


def synthesize_relational_graph_proposal_v1(
    source_log: AnonymousGraphSourceLogV1,
) -> RelationalGraphCoordinateProposalV1:
    """Return a source-only AST/support-schema proposal.

    This is the sole public construction API.  Its only input is the exact
    anonymous source-log artifact.
    """

    if type(source_log) is not AnonymousGraphSourceLogV1:
        raise RelationalGraphCoreInvariantViolation(
            "relational graph producer requires the exact source-log type"
        )
    return _run_synthesis(source_log).proposal


def relational_graph_synthesis_metrics_v1(
    source_log: AnonymousGraphSourceLogV1,
    proposal: RelationalGraphCoordinateProposalV1,
) -> RelationalGraphSynthesisMetricsV1:
    if (
        type(source_log) is not AnonymousGraphSourceLogV1
        or type(proposal) is not RelationalGraphCoordinateProposalV1
    ):
        raise RelationalGraphCoreInvariantViolation(
            "metrics require exact source-log and proposal types"
        )
    synthesis = _run_synthesis(source_log)
    if proposal.to_document() != synthesis.proposal.to_document():
        raise RelationalGraphCoreInvariantViolation(
            "metrics reject a noncanonical proposal"
        )
    selected = synthesis.selected
    state_count = sum(
        item.result_type is GraphProgramType.INTEGER
        and item.context is GraphProgramContext.STATE
        for item in synthesis.registry.programs
    )
    action_count = sum(
        item.result_type is GraphProgramType.INTEGER
        and item.context is GraphProgramContext.STATE_ACTION
        for item in synthesis.registry.programs
    )
    return RelationalGraphSynthesisMetricsV1(
        source_log.source_log_id,
        proposal.proposal_id,
        synthesis.registry.syntactic_program_count,
        synthesis.registry.semantic_program_count_by_depth,
        state_count,
        action_count,
        len(synthesis.candidates),
        sum(item.admissible for item in synthesis.candidates),
        selected.ground_state_count,
        selected.ground_row_count,
        selected.abstract_state_count,
        selected.abstract_support_count,
        selected.alias_pair_count,
        selected.availability_variant_count,
        selected.transition_alias_width,
        selected.reward_alias_width,
        selected.sound_alias_width,
        selected.state_program.rendered,
        selected.action_program.rendered,
    )


def verify_relational_graph_proposal_v1(
    source_log: AnonymousGraphSourceLogV1,
    claimed: RelationalGraphCoordinateProposalV1,
) -> bool:
    if (
        type(source_log) is not AnonymousGraphSourceLogV1
        or type(claimed) is not RelationalGraphCoordinateProposalV1
    ):
        raise RelationalGraphCoreInvariantViolation(
            "proposal verifier rejects runtime substitutions"
        )
    expected = _run_synthesis(source_log).proposal
    _runtime_shape(claimed, expected, "relational graph proposal")
    if claimed.to_document() != expected.to_document():
        raise RelationalGraphCoreInvariantViolation(
            "proposal differs from complete source-only replay"
        )
    return True


def _registered_source_topologies() -> tuple[GraphTopologyV1, ...]:
    rows = (
        GraphTopologyV1(4, ((0, 1), (1, 2), (2, 3))),  # P4
        GraphTopologyV1(4, ((0, 1), (0, 2), (0, 3))),  # K1,3
        GraphTopologyV1(4, ((0, 1), (0, 2), (1, 2), (2, 3))),  # paw
    )
    return tuple(sorted(rows, key=lambda item: item.topology_id))


def _fixture_step(
    topology: GraphTopologyV1,
    state: GraphStateViewV1,
    action: GraphActionViewV1,
) -> tuple[GraphOutcomeViewV1, ...]:
    rank = state.ranks[action.first]
    merged = list(state.ranks)
    merged[action.first] = 0
    merged[action.second] = 0
    merged[action.survivor] = min(rank + 1, REGISTERED_RANK_CAP)
    empty_cells = tuple(
        index for index, value in enumerate(merged) if value == 0
    )
    outcomes: list[GraphOutcomeViewV1] = []
    for cell in empty_cells:
        for spawn_rank, rank_probability in (
            (1, REGISTERED_LOW_RANK_PROBABILITY),
            (2, 1 - REGISTERED_LOW_RANK_PROBABILITY),
        ):
            board = merged.copy()
            board[cell] = spawn_rank
            ranks = tuple(board)
            failure = not _legal_action_tuples(topology, ranks)
            next_state = GraphStateViewV1(
                topology.topology_id,
                ranks,
                failure,
                state.remaining_horizon - 1,
            )
            outcomes.append(
                GraphOutcomeViewV1(
                    next_state,
                    rank_probability / len(empty_cells),
                    Fraction(
                        2 ** (rank + 1),
                        2 ** (REGISTERED_RANK_CAP + 1),
                    ),
                    failure,
                    failure,
                )
            )
    return tuple(outcomes)


def _fixture_row(
    topology: GraphTopologyV1,
    state: GraphStateViewV1,
    action: GraphActionViewV1,
) -> GraphObservedRowV1:
    return GraphObservedRowV1(
        state,
        action,
        _legal_action_views(topology, state),
        _fixture_step(topology, state, action),
    )


@functools.lru_cache(maxsize=1)
def build_registered_multigeometry_source_log_v1() -> AnonymousGraphSourceLogV1:
    """Build the P4/star/paw complete-H2 synthetic source fixture."""

    rows: dict[str, GraphObservedRowV1] = {}
    topologies = _registered_source_topologies()
    for topology in topologies:
        roots: dict[tuple[int, ...], GraphStateViewV1] = {}
        for first, second in topology.edges:
            for anchor in range(topology.vertex_count):
                if anchor in (first, second):
                    continue
                board = [0] * topology.vertex_count
                board[first] = 1
                board[second] = 1
                board[anchor] = 2
                state = GraphStateViewV1(
                    topology.topology_id,
                    tuple(board),
                    False,
                    REGISTERED_HORIZON,
                )
                roots[state.ranks] = state
        active_successors: dict[str, GraphStateViewV1] = {}
        for state in roots.values():
            for action in _legal_action_views(topology, state):
                row = _fixture_row(topology, state, action)
                rows[row.row_id] = row
                for outcome in row.outcomes:
                    if (
                        not outcome.failure
                        and outcome.next_state.remaining_horizon > 0
                    ):
                        active_successors[
                            outcome.next_state.state_id
                        ] = outcome.next_state
        for state in active_successors.values():
            for action in _legal_action_views(topology, state):
                row = _fixture_row(topology, state, action)
                rows[row.row_id] = row
    return AnonymousGraphSourceLogV1(
        topologies,
        tuple(sorted(rows.values(), key=lambda item: item.row_id)),
    )


__all__ = [
    "AnonymousGraphSourceLogV1",
    "GraphActionViewV1",
    "GraphAnonymousSupportKeySchemaV1",
    "GraphCoordinateProgramV1",
    "GraphObservedRowV1",
    "GraphOutcomeViewV1",
    "GraphProgramContext",
    "GraphProgramRegistryV1",
    "GraphProgramType",
    "GraphStateViewV1",
    "GraphTopologyV1",
    "RelationalGraphCoordinateProposalV1",
    "RelationalGraphCoreInvariantViolation",
    "RelationalGraphSynthesisMetricsV1",
    "build_registered_multigeometry_source_log_v1",
    "evaluate_action_coordinate_v1",
    "evaluate_state_coordinate_v1",
    "generate_relational_graph_program_registry_v1",
    "relational_graph_synthesis_metrics_v1",
    "synthesize_relational_graph_proposal_v1",
    "verify_relational_graph_proposal_v1",
]
