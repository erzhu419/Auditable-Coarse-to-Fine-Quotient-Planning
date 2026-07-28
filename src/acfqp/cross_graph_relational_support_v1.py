"""Registered cross-geometry graph-merge foundation for V0-065.

This module owns only the physical graph family, exact source acquisition,
target catalogues, and cold exact H2 controls.  Coordinate synthesis and the
partial/statistical RAPM live above this boundary.  In particular, none of
the transition, motif, or catalogue functions branches on a graph identity:
all behavior is induced by the registered edge set.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import functools
import hashlib
import inspect
from itertools import permutations
from typing import Any, Mapping

from acfqp.core import Outcome, QuerySpec
from acfqp.domains.g2048 import G2048Action, G2048State, G2048Status
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.planning.ground import reachable_decision_pairs, solve_ground_pareto
from acfqp.relational_graph_core_v1 import (
    AnonymousGraphSourceLogV1,
    GraphActionViewV1,
    GraphObservedRowV1,
    GraphOutcomeViewV1,
    GraphStateViewV1,
    GraphTopologyV1,
)


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.29.0"
PROFILE_KEY = "observation_driven_cross_geometry_relational_rapm_v0"

VERTEX_COUNT = 4
HORIZON = 2
RISK_TOLERANCE = Fraction(1, 20)
LOW_RANK_PROBABILITY = Fraction(99, 100)
RANK_CAP = 6
REWARD_NORMALIZER = Fraction(HORIZON)

# Filled after the foundation implementation is frozen.  The observed digest
# covers an explicit authority list, so later higher-layer classes can be
# added without silently changing the physical-kernel identity.
FOUNDATION_IMPLEMENTATION_SHA256 = (
    "6be5d16937c46ca4acc326e0b8150755546b52faf9118bd2bfd3620c7788aedb"
)


DOMAIN_TAGS = {
    "structural": "acfqp:cross-graph-structural:v1",
    "context": "acfqp:cross-graph-context:v1",
    "nonisomorphism": "acfqp:cross-graph-nonisomorphism:v1",
    "family": "acfqp:cross-graph-family:v1",
    "source_bundle": "acfqp:cross-graph-source-observation-bundle:v1",
    "catalogue": "acfqp:cross-graph-state-catalogue:v1",
    "sample": "acfqp:cross-graph-merge-sample:v1",
    "query": "acfqp:cross-graph-cold-h2-query:v1",
    "cold_control": "acfqp:cross-graph-cold-h2-control:v1",
}


class CrossGraphInvariantViolation(ValueError):
    """A graph, context, transition, observation, or control is inconsistent."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise CrossGraphInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise CrossGraphInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


class CrossGraphSplit(str, Enum):
    SOURCE = "SOURCE"
    TARGET = "TARGET"


GRAPH_SPECS: tuple[tuple[str, tuple[tuple[int, int], ...]], ...] = (
    ("p4", ((0, 1), (1, 2), (2, 3))),
    ("star", ((0, 1), (0, 2), (0, 3))),
    ("paw", ((0, 1), (0, 2), (1, 2), (2, 3))),
    ("c4", ((0, 1), (0, 2), (1, 3), (2, 3))),
    ("diamond", ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3))),
    (
        "k4",
        ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)),
    ),
)
GRAPH_BY_KEY = {
    key: GraphTopologyV1(VERTEX_COUNT, edges) for key, edges in GRAPH_SPECS
}

SOURCE_CONTEXT_SPECS = (
    ("cross_source_p4_r1_v0", "p4", 1),
    ("cross_source_star_r2_v0", "star", 2),
    ("cross_source_paw_r3_v0", "paw", 3),
)
TARGET_CONTEXT_SPECS = (
    ("cross_target_c4_r2_v0", "c4", 2),
    ("cross_target_diamond_r3_v0", "diamond", 3),
    ("cross_target_k4_r4_v0", "k4", 4),
)


@dataclass(frozen=True, slots=True)
class CrossGraphStructuralContextV1:
    """One registered rank-relative process on one literal graph topology."""

    context_key: str
    split: CrossGraphSplit
    graph_key: str
    topology: GraphTopologyV1
    low_rank: int
    low_rank_probability: Fraction = LOW_RANK_PROBABILITY
    rank_cap: int = RANK_CAP
    horizon: int = HORIZON
    risk_tolerance: Fraction = RISK_TOLERANCE

    def __post_init__(self) -> None:
        expected_specs = (
            SOURCE_CONTEXT_SPECS
            if self.split is CrossGraphSplit.SOURCE
            else TARGET_CONTEXT_SPECS
        )
        if (
            type(self.context_key) is not str
            or type(self.graph_key) is not str
            or type(self.topology) is not GraphTopologyV1
            or (self.context_key, self.graph_key, self.low_rank)
            not in expected_specs
            or self.topology != GRAPH_BY_KEY.get(self.graph_key)
            or type(self.low_rank) is not int
            or not 1 <= self.low_rank < self.rank_cap
            or self.low_rank_probability != LOW_RANK_PROBABILITY
            or self.rank_cap != RANK_CAP
            or self.horizon != HORIZON
            or self.risk_tolerance != RISK_TOLERANCE
            or self.high_rank > self.rank_cap
        ):
            raise CrossGraphInvariantViolation(
                "cross-graph context is outside the registered family"
            )

    @property
    def high_rank(self) -> int:
        return self.low_rank + 1

    def _structural_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_graph_structural.v1",
            "schema_version": SCHEMA_VERSION,
            "topology": self.topology.to_document(),
            "rank_cap": self.rank_cap,
            "spawn_support": [self.low_rank, self.high_rank],
            "spawn_probabilities": [
                _fdoc(self.low_rank_probability),
                _fdoc(1 - self.low_rank_probability),
            ],
            "merge_semantics": "selected_equal_edge_single_survivor",
            "merge_rank": "min(rank_plus_one,rank_cap)",
            "spawn_timing": "after_every_valid_merge",
            "spawn_position": "uniform_over_postmerge_empty_vertices",
            "failure_rule": "postspawn_no_legal_equal_edge_merge",
            "failure_before_horizon_truncation": True,
            "foundation_implementation_sha256": (
                FOUNDATION_IMPLEMENTATION_SHA256
            ),
        }

    @property
    def structural_id(self) -> str:
        return _content_id("structural", self._structural_payload())

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_graph_structural_context.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_key": self.context_key,
            "split": self.split.value,
            "graph_key": self.graph_key,
            "structural_id": self.structural_id,
            "horizon": self.horizon,
            "risk_tolerance": _fdoc(self.risk_tolerance),
        }

    @property
    def context_id(self) -> str:
        return _content_id("context", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


def registered_cross_graph_contexts_v1(
    split: CrossGraphSplit | None = None,
) -> tuple[CrossGraphStructuralContextV1, ...]:
    rows = tuple(
        CrossGraphStructuralContextV1(
            context_key,
            CrossGraphSplit.SOURCE,
            graph_key,
            GRAPH_BY_KEY[graph_key],
            low_rank,
        )
        for context_key, graph_key, low_rank in SOURCE_CONTEXT_SPECS
    ) + tuple(
        CrossGraphStructuralContextV1(
            context_key,
            CrossGraphSplit.TARGET,
            graph_key,
            GRAPH_BY_KEY[graph_key],
            low_rank,
        )
        for context_key, graph_key, low_rank in TARGET_CONTEXT_SPECS
    )
    return rows if split is None else tuple(item for item in rows if item.split is split)


def _degree_sequence(topology: GraphTopologyV1) -> tuple[int, ...]:
    return tuple(
        sorted(
            (len(topology.neighbors(vertex)) for vertex in range(VERTEX_COUNT)),
            reverse=True,
        )
    )


def _isomorphism_mappings(
    left: GraphTopologyV1,
    right: GraphTopologyV1,
) -> tuple[tuple[int, ...], ...]:
    """Exhaust all vertex bijections; four vertices means exactly 24 checks."""

    if left.vertex_count != right.vertex_count:
        return ()
    right_edges = set(right.edges)
    matches: list[tuple[int, ...]] = []
    for mapping in permutations(range(left.vertex_count)):
        image = {
            tuple(sorted((mapping[first], mapping[second])))
            for first, second in left.edges
        }
        if image == right_edges:
            matches.append(mapping)
    return tuple(matches)


@dataclass(frozen=True, slots=True)
class GraphNonisomorphismWitnessV1:
    source_graph_id: str
    target_graph_id: str
    source_edge_count: int
    target_edge_count: int
    source_degree_sequence: tuple[int, ...]
    target_degree_sequence: tuple[int, ...]
    tested_bijection_count: int
    isomorphism_mapping_count: int

    def __post_init__(self) -> None:
        _cid(self.source_graph_id, "nonisomorphism source graph")
        _cid(self.target_graph_id, "nonisomorphism target graph")
        if (
            any(
                type(value) is not int or value < 0
                for value in (
                    self.source_edge_count,
                    self.target_edge_count,
                    self.tested_bijection_count,
                    self.isomorphism_mapping_count,
                )
            )
            or type(self.source_degree_sequence) is not tuple
            or type(self.target_degree_sequence) is not tuple
            or self.tested_bijection_count != 24
            or self.isomorphism_mapping_count != 0
        ):
            raise CrossGraphInvariantViolation(
                "source-target nonisomorphism witness is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_graph_nonisomorphism_witness.v1",
            "schema_version": SCHEMA_VERSION,
            "source_graph_id": self.source_graph_id,
            "target_graph_id": self.target_graph_id,
            "source_edge_count": self.source_edge_count,
            "target_edge_count": self.target_edge_count,
            "source_degree_sequence": list(self.source_degree_sequence),
            "target_degree_sequence": list(self.target_degree_sequence),
            "tested_bijection_count": self.tested_bijection_count,
            "isomorphism_mapping_count": self.isomorphism_mapping_count,
        }

    @property
    def witness_id(self) -> str:
        return _content_id("nonisomorphism", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "witness_id": self.witness_id}


def _nonisomorphism_witness(
    source: GraphTopologyV1,
    target: GraphTopologyV1,
) -> GraphNonisomorphismWitnessV1:
    mappings = _isomorphism_mappings(source, target)
    if mappings:
        raise CrossGraphInvariantViolation(
            "registered source and target graphs are isomorphic"
        )
    return GraphNonisomorphismWitnessV1(
        source.topology_id,
        target.topology_id,
        len(source.edges),
        len(target.edges),
        _degree_sequence(source),
        _degree_sequence(target),
        24,
        0,
    )


@dataclass(frozen=True, slots=True)
class CrossGraphFamilyV1:
    source_contexts: tuple[CrossGraphStructuralContextV1, ...]
    target_contexts: tuple[CrossGraphStructuralContextV1, ...]
    nonisomorphism_witnesses: tuple[GraphNonisomorphismWitnessV1, ...]
    source_target_graph_nonisomorphic: bool = True
    official_execution_allowed: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.source_contexts) is not tuple
            or type(self.target_contexts) is not tuple
            or type(self.nonisomorphism_witnesses) is not tuple
            or any(
                type(item) is not CrossGraphStructuralContextV1
                for item in self.source_contexts + self.target_contexts
            )
            or any(
                type(item) is not GraphNonisomorphismWitnessV1
                for item in self.nonisomorphism_witnesses
            )
            or self.source_contexts
            != registered_cross_graph_contexts_v1(CrossGraphSplit.SOURCE)
            or self.target_contexts
            != registered_cross_graph_contexts_v1(CrossGraphSplit.TARGET)
            or len(self.nonisomorphism_witnesses) != 9
            or tuple(item.witness_id for item in self.nonisomorphism_witnesses)
            != tuple(
                sorted(
                    {item.witness_id for item in self.nonisomorphism_witnesses}
                )
            )
            or self.source_target_graph_nonisomorphic is not True
            or self.official_execution_allowed is not False
        ):
            raise CrossGraphInvariantViolation(
                "cross-graph family registry is inconsistent"
            )
        source_ids = {item.structural_id for item in self.source_contexts}
        target_ids = {item.structural_id for item in self.target_contexts}
        if not source_ids.isdisjoint(target_ids):
            raise CrossGraphInvariantViolation(
                "source and target structural identities overlap"
            )
        expected_pairs = {
            (source.topology.topology_id, target.topology.topology_id)
            for source in self.source_contexts
            for target in self.target_contexts
        }
        if {
            (item.source_graph_id, item.target_graph_id)
            for item in self.nonisomorphism_witnesses
        } != expected_pairs:
            raise CrossGraphInvariantViolation(
                "nonisomorphism witnesses do not cover the source-target product"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_graph_family.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_contexts": [
                item.to_document() for item in self.source_contexts
            ],
            "target_contexts": [
                item.to_document() for item in self.target_contexts
            ],
            "nonisomorphism_witnesses": [
                item.to_document() for item in self.nonisomorphism_witnesses
            ],
            "source_target_graph_nonisomorphic": (
                self.source_target_graph_nonisomorphic
            ),
            "official_execution_allowed": self.official_execution_allowed,
        }

    @property
    def family_id(self) -> str:
        return _content_id("family", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "family_id": self.family_id}


@functools.lru_cache(maxsize=1)
def registered_cross_graph_family_v1() -> CrossGraphFamilyV1:
    source = registered_cross_graph_contexts_v1(CrossGraphSplit.SOURCE)
    target = registered_cross_graph_contexts_v1(CrossGraphSplit.TARGET)
    witnesses = tuple(
        sorted(
            (
                _nonisomorphism_witness(left.topology, right.topology)
                for left in source
                for right in target
            ),
            key=lambda item: item.witness_id,
        )
    )
    return CrossGraphFamilyV1(source, target, witnesses)


@dataclass(frozen=True, slots=True)
class GraphMergeSampleV1:
    next_state: G2048State
    normalized_reward: Fraction
    failure: bool
    terminal: bool
    structural_atom_index: int

    def __post_init__(self) -> None:
        if (
            type(self.next_state) is not G2048State
            or type(self.normalized_reward) is not Fraction
            or not 0 <= self.normalized_reward <= 1
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
            or self.failure != (
                self.next_state.status is G2048Status.FAILURE
            )
            or self.terminal != self.failure
            or type(self.structural_atom_index) is not int
            or self.structural_atom_index < 0
        ):
            raise CrossGraphInvariantViolation("graph merge sample is invalid")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.graph_merge_sample.v1",
            "schema_version": SCHEMA_VERSION,
            "next_state": {
                "board": list(self.next_state.board),
                "status": self.next_state.status.value,
            },
            "normalized_reward": _fdoc(self.normalized_reward),
            "failure": self.failure,
            "terminal": self.terminal,
            "structural_atom_index": self.structural_atom_index,
            "exact_probability_exposed": False,
        }

    @property
    def sample_id(self) -> str:
        return _content_id("sample", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "sample_id": self.sample_id}


@dataclass(frozen=True, slots=True)
class GraphMergeKernelV1:
    """Exact and generative rank-relative merge process on a registered graph."""

    context: CrossGraphStructuralContextV1

    def __post_init__(self) -> None:
        if (
            type(self.context) is not CrossGraphStructuralContextV1
            or self.context not in registered_cross_graph_contexts_v1()
        ):
            raise CrossGraphInvariantViolation(
                "graph merge kernel requires a registered context"
            )

    @property
    def horizon(self) -> int:
        return self.context.horizon

    @property
    def rank_cap(self) -> int:
        return self.context.rank_cap

    @property
    def cell_count(self) -> int:
        return self.context.topology.vertex_count

    @property
    def registered_reward_features(self) -> tuple[str, ...]:
        return ("merge",)

    @property
    def registered_goals(self) -> tuple[str, ...]:
        return ("default",)

    @property
    def spawn_distribution(self) -> tuple[tuple[int, Fraction], ...]:
        return (
            (self.context.low_rank, self.context.low_rank_probability),
            (self.context.high_rank, 1 - self.context.low_rank_probability),
        )

    def reward_upper_bound(
        self,
        horizon: int,
        raw_weights: Mapping[str, Fraction],
        goal: str,
    ) -> Fraction:
        if goal != "default" or not 0 <= horizon <= self.horizon:
            raise ValueError("unregistered graph-merge goal or horizon")
        coefficient = Fraction(raw_weights.get("merge", 0))
        if coefficient < 0:
            raise ValueError("registered reward weights must be nonnegative")
        return horizon * coefficient

    def _validate_state(self, state: G2048State) -> None:
        if (
            type(state) is not G2048State
            or len(state.board) != self.cell_count
            or any(
                type(rank) is not int or not 0 <= rank <= self.rank_cap
                for rank in state.board
            )
        ):
            raise ValueError("state is outside this graph-merge process")

    def initial_distribution(self) -> tuple[tuple[Fraction, G2048State], ...]:
        roots = motif_states_v1(self.context)
        mass = Fraction(1, len(roots))
        return tuple((mass, state) for state in roots)

    def actions(self, state: G2048State) -> tuple[G2048Action, ...]:
        self._validate_state(state)
        if state.status is not G2048Status.ACTIVE:
            return ()
        return tuple(
            G2048Action(first, second, survivor)
            for first, second in self.context.topology.edges
            if state.board[first] > 0
            and state.board[first] == state.board[second]
            for survivor in (first, second)
        )

    def _merged_board(
        self,
        state: G2048State,
        action: G2048Action,
    ) -> tuple[list[int], int, tuple[int, ...], Fraction]:
        self._validate_state(state)
        if action not in self.actions(state):
            raise ValueError("action is not legal in this graph-merge state")
        rank = state.board[action.first]
        board = list(state.board)
        board[action.first] = 0
        board[action.second] = 0
        board[action.survivor] = min(rank + 1, self.rank_cap)
        empty_cells = tuple(
            index for index, value in enumerate(board) if value == 0
        )
        if not empty_cells:
            raise AssertionError("a merge must create an empty vertex")
        reward = Fraction(2 ** (rank + 1), 2 ** (self.rank_cap + 1))
        return board, rank, empty_cells, reward

    def step(
        self,
        state: G2048State,
        action: G2048Action,
    ) -> tuple[Outcome[G2048State], ...]:
        board, _, empty_cells, reward = self._merged_board(state, action)
        cell_probability = Fraction(1, len(empty_cells))
        outcomes: list[Outcome[G2048State]] = []
        for cell in empty_cells:
            for spawn_rank, rank_probability in self.spawn_distribution:
                next_board = board.copy()
                next_board[cell] = spawn_rank
                provisional = G2048State(tuple(next_board))
                failed = not self.actions(provisional)
                next_state = G2048State(
                    provisional.board,
                    (
                        G2048Status.FAILURE
                        if failed
                        else G2048Status.ACTIVE
                    ),
                )
                outcomes.append(
                    Outcome(
                        cell_probability * rank_probability,
                        next_state,
                        (("merge", reward),),
                        failure=failed,
                        terminal=failed,
                    )
                )
        if sum(
            (item.probability for item in outcomes),
            Fraction(0),
        ) != 1:
            raise AssertionError("graph-merge outcome mass is not one")
        return tuple(outcomes)

    def sample(
        self,
        state: G2048State,
        action: G2048Action,
        uniform: Fraction,
    ) -> GraphMergeSampleV1:
        """Return one generative atom without exposing its exact probability."""

        if type(uniform) is not Fraction or not 0 <= uniform < 1:
            raise ValueError("sample uniform must be an exact value in [0,1)")
        board, _, empty_cells, reward = self._merged_board(state, action)
        scaled = uniform * len(empty_cells)
        cell_ordinal = scaled.numerator // scaled.denominator
        rank_uniform = scaled - cell_ordinal
        low = rank_uniform < self.context.low_rank_probability
        rank_ordinal = 0 if low else 1
        spawn_rank = (
            self.context.low_rank if low else self.context.high_rank
        )
        next_board = board.copy()
        next_board[empty_cells[cell_ordinal]] = spawn_rank
        provisional = G2048State(tuple(next_board))
        failed = not self.actions(provisional)
        return GraphMergeSampleV1(
            G2048State(
                provisional.board,
                (
                    G2048Status.FAILURE
                    if failed
                    else G2048Status.ACTIVE
                ),
            ),
            reward / REWARD_NORMALIZER,
            failed,
            failed,
            2 * cell_ordinal + rank_ordinal,
        )

    def sample_transition(
        self,
        state: G2048State,
        action: G2048Action,
        uniform: Fraction,
    ) -> GraphMergeSampleV1:
        return self.sample(state, action, uniform)

    def sample_structural_atom_index(
        self,
        empty_cell_count: int,
        uniform_uint256: int,
    ) -> int:
        if (
            type(empty_cell_count) is not int
            or empty_cell_count <= 0
            or type(uniform_uint256) is not int
            or not 0 <= uniform_uint256 < 1 << 256
        ):
            raise ValueError("structural sampler input is invalid")
        scaled = uniform_uint256 * empty_cell_count
        cell_ordinal, rank_remainder = divmod(scaled, 1 << 256)
        low = (
            rank_remainder
            * self.context.low_rank_probability.denominator
            < self.context.low_rank_probability.numerator * (1 << 256)
        )
        return 2 * cell_ordinal + (0 if low else 1)

    def is_terminal(self, state: G2048State) -> bool:
        self._validate_state(state)
        return state.status is G2048Status.FAILURE


def motif_states_v1(
    context: CrossGraphStructuralContextV1,
) -> tuple[G2048State, ...]:
    """Enumerate every edge plus every third-vertex anchor without graph cases."""

    if type(context) is not CrossGraphStructuralContextV1:
        raise CrossGraphInvariantViolation(
            "motif enumeration requires a registered context"
        )
    states: set[G2048State] = set()
    for first, second in context.topology.edges:
        for anchor in range(context.topology.vertex_count):
            if anchor in (first, second):
                continue
            board = [0] * context.topology.vertex_count
            board[first] = context.low_rank
            board[second] = context.low_rank
            board[anchor] = context.high_rank
            states.add(G2048State(tuple(board)))
    return tuple(
        sorted(states, key=lambda item: (item.board, item.status.value))
    )


def _state_view(
    context: CrossGraphStructuralContextV1,
    state: G2048State,
    remaining_horizon: int,
) -> GraphStateViewV1:
    return GraphStateViewV1(
        context.topology.topology_id,
        state.board,
        state.status is G2048Status.FAILURE,
        remaining_horizon,
    )


def _action_view(
    state: GraphStateViewV1,
    action: G2048Action,
) -> GraphActionViewV1:
    return GraphActionViewV1(
        state.state_id,
        action.first,
        action.second,
        action.survivor,
    )


def _ground_action(action: GraphActionViewV1) -> G2048Action:
    return G2048Action(action.first, action.second, action.survivor)


def _observed_row(
    context: CrossGraphStructuralContextV1,
    kernel: GraphMergeKernelV1,
    state: G2048State,
    action: G2048Action,
    remaining_horizon: int,
) -> GraphObservedRowV1:
    raw_state = _state_view(context, state, remaining_horizon)
    legal = tuple(
        _action_view(raw_state, item) for item in kernel.actions(state)
    )
    outcomes = tuple(
        GraphOutcomeViewV1(
            _state_view(
                context,
                outcome.next_state,
                remaining_horizon - 1,
            ),
            outcome.probability,
            outcome.feature("merge") / REWARD_NORMALIZER,
            outcome.failure,
            outcome.terminal,
        )
        for outcome in kernel.step(state, action)
    )
    return GraphObservedRowV1(
        raw_state,
        _action_view(raw_state, action),
        legal,
        outcomes,
    )


def _complete_h2_rows(
    context: CrossGraphStructuralContextV1,
) -> tuple[GraphObservedRowV1, ...]:
    kernel = GraphMergeKernelV1(context)
    rows: dict[str, GraphObservedRowV1] = {}
    active_successors: dict[G2048State, None] = {}
    for state in motif_states_v1(context):
        for action in kernel.actions(state):
            row = _observed_row(
                context,
                kernel,
                state,
                action,
                HORIZON,
            )
            rows[row.row_id] = row
            for outcome in row.outcomes:
                if not outcome.failure and not outcome.terminal:
                    active_successors[
                        G2048State(
                            outcome.next_state.ranks,
                            G2048Status.ACTIVE,
                        )
                    ] = None
    for state in sorted(
        active_successors,
        key=lambda item: (item.board, item.status.value),
    ):
        for action in kernel.actions(state):
            row = _observed_row(context, kernel, state, action, 1)
            rows[row.row_id] = row
    return tuple(sorted(rows.values(), key=lambda item: item.row_id))


@dataclass(frozen=True, slots=True)
class CrossGraphSourceObservationBundleV1:
    family_id: str
    contexts: tuple[CrossGraphStructuralContextV1, ...]
    observation_log: AnonymousGraphSourceLogV1
    row_counts_by_context: tuple[tuple[str, int], ...]
    query_inputs_used: int = 0
    target_inputs_used: int = 0
    graph_group_prior_used: bool = False
    graph_identity_branches_used: bool = False

    def __post_init__(self) -> None:
        _cid(self.family_id, "source bundle family")
        if (
            type(self.contexts) is not tuple
            or any(
                type(item) is not CrossGraphStructuralContextV1
                for item in self.contexts
            )
            or type(self.observation_log) is not AnonymousGraphSourceLogV1
            or self.contexts
            != registered_cross_graph_contexts_v1(CrossGraphSplit.SOURCE)
            or self.family_id != registered_cross_graph_family_v1().family_id
            or type(self.row_counts_by_context) is not tuple
            or self.query_inputs_used != 0
            or self.target_inputs_used != 0
            or self.graph_group_prior_used is not False
            or self.graph_identity_branches_used is not False
        ):
            raise CrossGraphInvariantViolation(
                "source observation bundle binding changed"
            )
        expected_rows: dict[str, GraphObservedRowV1] = {}
        expected_counts: list[tuple[str, int]] = []
        for context in self.contexts:
            rows = _complete_h2_rows(context)
            expected_counts.append((context.context_id, len(rows)))
            expected_rows.update((item.row_id, item) for item in rows)
        expected_log = AnonymousGraphSourceLogV1(
            tuple(
                sorted(
                    (item.topology for item in self.contexts),
                    key=lambda item: item.topology_id,
                )
            ),
            tuple(sorted(expected_rows.values(), key=lambda item: item.row_id)),
        )
        if (
            self.row_counts_by_context != tuple(expected_counts)
            or self.observation_log.to_document()
            != expected_log.to_document()
        ):
            raise CrossGraphInvariantViolation(
                "source log is incomplete or differs from exact H2 replay"
            )

    @property
    def ground_row_count(self) -> int:
        return len(self.observation_log.rows)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_graph_source_observation_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "family_id": self.family_id,
            "contexts": [item.to_document() for item in self.contexts],
            "observation_log": self.observation_log.to_document(),
            "row_counts_by_context": [
                {"context_id": context_id, "row_count": count}
                for context_id, count in self.row_counts_by_context
            ],
            "query_inputs_used": self.query_inputs_used,
            "target_inputs_used": self.target_inputs_used,
            "graph_group_prior_used": self.graph_group_prior_used,
            "graph_identity_branches_used": (
                self.graph_identity_branches_used
            ),
        }

    @property
    def bundle_id(self) -> str:
        return _content_id("source_bundle", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "bundle_id": self.bundle_id}


@functools.lru_cache(maxsize=1)
def acquire_cross_graph_source_observations_v1(
) -> CrossGraphSourceObservationBundleV1:
    family = registered_cross_graph_family_v1()
    rows: dict[str, GraphObservedRowV1] = {}
    counts: list[tuple[str, int]] = []
    for context in family.source_contexts:
        context_rows = _complete_h2_rows(context)
        counts.append((context.context_id, len(context_rows)))
        rows.update((item.row_id, item) for item in context_rows)
    log = AnonymousGraphSourceLogV1(
        tuple(
            sorted(
                (item.topology for item in family.source_contexts),
                key=lambda item: item.topology_id,
            )
        ),
        tuple(sorted(rows.values(), key=lambda item: item.row_id)),
    )
    return CrossGraphSourceObservationBundleV1(
        family.family_id,
        family.source_contexts,
        log,
        tuple(counts),
    )


@dataclass(frozen=True, slots=True)
class CrossGraphStateCatalogueV1:
    context_id: str
    state: GraphStateViewV1
    legal_actions: tuple[GraphActionViewV1, ...]

    def __post_init__(self) -> None:
        _cid(self.context_id, "state catalogue context")
        if (
            type(self.state) is not GraphStateViewV1
            or type(self.legal_actions) is not tuple
            or any(
                type(item) is not GraphActionViewV1
                for item in self.legal_actions
            )
            or self.state.failure
            or self.state.remaining_horizon not in (1, HORIZON)
            or any(
                item.state_id != self.state.state_id
                for item in self.legal_actions
            )
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
        ):
            raise CrossGraphInvariantViolation("state catalogue is invalid")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_graph_state_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "state": self.state.to_document(),
            "legal_actions": [
                item.to_document() for item in self.legal_actions
            ],
        }

    @property
    def catalogue_id(self) -> str:
        return _content_id("catalogue", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "catalogue_id": self.catalogue_id}


def _catalogue(
    context: CrossGraphStructuralContextV1,
    kernel: GraphMergeKernelV1,
    state: G2048State,
    remaining_horizon: int,
) -> CrossGraphStateCatalogueV1:
    raw_state = _state_view(context, state, remaining_horizon)
    return CrossGraphStateCatalogueV1(
        context.context_id,
        raw_state,
        tuple(
            _action_view(raw_state, action)
            for action in kernel.actions(state)
        ),
    )


def target_root_catalogues_v1(
    context: CrossGraphStructuralContextV1,
) -> tuple[CrossGraphStateCatalogueV1, ...]:
    if (
        type(context) is not CrossGraphStructuralContextV1
        or context.split is not CrossGraphSplit.TARGET
    ):
        raise CrossGraphInvariantViolation(
            "target root catalogues require a registered target context"
        )
    kernel = GraphMergeKernelV1(context)
    return tuple(
        sorted(
            (
                _catalogue(context, kernel, state, HORIZON)
                for state in motif_states_v1(context)
            ),
            key=lambda item: item.catalogue_id,
        )
    )


def continuation_catalogues_from_states_v1(
    context: CrossGraphStructuralContextV1,
    states: tuple[G2048State, ...],
) -> tuple[CrossGraphStateCatalogueV1, ...]:
    if (
        type(context) is not CrossGraphStructuralContextV1
        or context.split is not CrossGraphSplit.TARGET
        or type(states) is not tuple
        or any(type(item) is not G2048State for item in states)
    ):
        raise CrossGraphInvariantViolation(
            "target continuation catalogue input is invalid"
        )
    kernel = GraphMergeKernelV1(context)
    unique = {
        state
        for state in states
        if state.status is G2048Status.ACTIVE and kernel.actions(state)
    }
    return tuple(
        sorted(
            (
                _catalogue(context, kernel, state, 1)
                for state in unique
            ),
            key=lambda item: item.catalogue_id,
        )
    )


def target_continuation_catalogues_v1(
    context: CrossGraphStructuralContextV1,
) -> tuple[CrossGraphStateCatalogueV1, ...]:
    """Exact structural-support helper for acquisition and standalone replay."""

    if (
        type(context) is not CrossGraphStructuralContextV1
        or context.split is not CrossGraphSplit.TARGET
    ):
        raise CrossGraphInvariantViolation(
            "target continuation catalogues require a registered target context"
        )
    kernel = GraphMergeKernelV1(context)
    successors = tuple(
        outcome.next_state
        for root in motif_states_v1(context)
        for action in kernel.actions(root)
        for outcome in kernel.step(root, action)
        if not outcome.failure and not outcome.terminal
    )
    return continuation_catalogues_from_states_v1(context, successors)


def _cold_query_payload(
    context: CrossGraphStructuralContextV1,
    root_ordinal: int,
    state: G2048State,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.cross_graph_cold_h2_query.v1",
        "schema_version": SCHEMA_VERSION,
        "context_id": context.context_id,
        "structural_id": context.structural_id,
        "root_ordinal": root_ordinal,
        "initial_board": list(state.board),
        "horizon": HORIZON,
        "delta": _fdoc(RISK_TOLERANCE),
        "reward_weights": [{"name": "merge", "weight": _fdoc(Fraction(1))}],
        "normalizer": _fdoc(REWARD_NORMALIZER),
        "policy_class": "deterministic_finite_horizon_markov_v1",
    }


@dataclass(frozen=True, slots=True)
class ColdExactH2ControlV1:
    context_id: str
    structural_id: str
    query_id: str
    root_ordinal: int
    initial_board: tuple[int, ...]
    reachable_state_count: int
    reachable_state_action_row_count: int
    composed_candidate_count: int
    minimum_failure_probability: Fraction
    selected_failure_probability: Fraction | None
    selected_normalized_reward: Fraction | None
    feasible: bool
    exact_ground_oracle_used: bool = True
    model_reuse_count: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "cold control context"),
            (self.structural_id, "cold control structural"),
            (self.query_id, "cold control query"),
        ):
            _cid(value, field)
        if (
            type(self.root_ordinal) is not int
            or self.root_ordinal < 0
            or type(self.initial_board) is not tuple
            or len(self.initial_board) != VERTEX_COUNT
            or any(
                type(value) is not int or value < 0
                for value in (
                    self.reachable_state_count,
                    self.reachable_state_action_row_count,
                    self.composed_candidate_count,
                )
            )
            or type(self.minimum_failure_probability) is not Fraction
            or not 0 <= self.minimum_failure_probability <= 1
            or type(self.feasible) is not bool
            or self.feasible
            != (self.selected_failure_probability is not None)
            or (
                self.selected_failure_probability is None
                and self.selected_normalized_reward is not None
            )
            or (
                self.selected_failure_probability is not None
                and (
                    type(self.selected_failure_probability) is not Fraction
                    or not 0
                    <= self.selected_failure_probability
                    <= RISK_TOLERANCE
                    or type(self.selected_normalized_reward) is not Fraction
                    or self.selected_normalized_reward < 0
                )
            )
            or self.exact_ground_oracle_used is not True
            or self.model_reuse_count != 0
        ):
            raise CrossGraphInvariantViolation("cold exact H2 control is invalid")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_graph_cold_exact_h2_control.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "root_ordinal": self.root_ordinal,
            "initial_board": list(self.initial_board),
            "reachable_state_count": self.reachable_state_count,
            "reachable_state_action_row_count": (
                self.reachable_state_action_row_count
            ),
            "composed_candidate_count": self.composed_candidate_count,
            "minimum_failure_probability": _fdoc(
                self.minimum_failure_probability
            ),
            "selected_failure_probability": (
                None
                if self.selected_failure_probability is None
                else _fdoc(self.selected_failure_probability)
            ),
            "selected_normalized_reward": (
                None
                if self.selected_normalized_reward is None
                else _fdoc(self.selected_normalized_reward)
            ),
            "feasible": self.feasible,
            "exact_ground_oracle_used": self.exact_ground_oracle_used,
            "model_reuse_count": self.model_reuse_count,
        }

    @property
    def control_id(self) -> str:
        return _content_id("cold_control", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "control_id": self.control_id}


def cold_exact_h2_oracle_v1(
    context: CrossGraphStructuralContextV1,
    root_ordinal: int = 0,
) -> ColdExactH2ControlV1:
    if (
        type(context) is not CrossGraphStructuralContextV1
        or context.split is not CrossGraphSplit.TARGET
    ):
        raise CrossGraphInvariantViolation(
            "cold H2 control requires a registered target context"
        )
    roots = motif_states_v1(context)
    if (
        type(root_ordinal) is not int
        or not 0 <= root_ordinal < len(roots)
    ):
        raise CrossGraphInvariantViolation(
            "cold H2 root ordinal is outside the motif family"
        )
    state = roots[root_ordinal]
    kernel = GraphMergeKernelV1(context)
    query_payload = _cold_query_payload(context, root_ordinal, state)
    query_id = _content_id("query", query_payload)
    query = QuerySpec.from_state(
        state,
        horizon=HORIZON,
        reward_weights=(("merge", Fraction(1)),),
        goal="default",
        delta=RISK_TOLERANCE,
        normalizer=REWARD_NORMALIZER,
        normalizer_proof_id="graph_merge_horizon_reward_upper_v1",
    )
    result = solve_ground_pareto(kernel, query)
    if not result.frontier:
        raise AssertionError("exact H2 oracle returned an empty frontier")
    minimum_failure = min(
        item.failure_probability for item in result.frontier
    )
    pairs = reachable_decision_pairs(kernel, query)
    selected = result.selected
    return ColdExactH2ControlV1(
        context.context_id,
        context.structural_id,
        query_id,
        root_ordinal,
        state.board,
        len(pairs),
        sum(len(kernel.actions(pair_state)) for _, pair_state in pairs),
        result.composed_candidate_count,
        minimum_failure,
        (
            None
            if selected is None
            else selected.failure_probability
        ),
        (
            None
            if selected is None
            else selected.expected_reward
        ),
        selected is not None,
    )


def cold_exact_h2_family_v1(
    context: CrossGraphStructuralContextV1,
) -> tuple[ColdExactH2ControlV1, ...]:
    return tuple(
        cold_exact_h2_oracle_v1(context, ordinal)
        for ordinal in range(len(motif_states_v1(context)))
    )


def _foundation_authority_items_v1() -> tuple[Any, ...]:
    return (
        CrossGraphStructuralContextV1,
        GraphMergeSampleV1,
        GraphMergeKernelV1,
        motif_states_v1,
        _state_view,
        _action_view,
        _observed_row,
        _complete_h2_rows,
        target_root_catalogues_v1,
        continuation_catalogues_from_states_v1,
        target_continuation_catalogues_v1,
        cold_exact_h2_oracle_v1,
    )


def _observed_foundation_implementation_sha256_v1() -> str:
    source = "\n\n".join(
        inspect.getsource(item) for item in _foundation_authority_items_v1()
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def validate_cross_graph_foundation_authority_v1() -> None:
    if (
        _observed_foundation_implementation_sha256_v1()
        != FOUNDATION_IMPLEMENTATION_SHA256
    ):
        raise CrossGraphInvariantViolation(
            "cross-graph physical foundation differs from frozen authority"
        )


__all__ = [
    "CONTRACT_VERSION",
    "FOUNDATION_IMPLEMENTATION_SHA256",
    "HORIZON",
    "LOW_RANK_PROBABILITY",
    "PROFILE_KEY",
    "RANK_CAP",
    "RISK_TOLERANCE",
    "ColdExactH2ControlV1",
    "CrossGraphFamilyV1",
    "CrossGraphInvariantViolation",
    "CrossGraphSourceObservationBundleV1",
    "CrossGraphSplit",
    "CrossGraphStateCatalogueV1",
    "CrossGraphStructuralContextV1",
    "GraphMergeKernelV1",
    "GraphMergeSampleV1",
    "GraphNonisomorphismWitnessV1",
    "acquire_cross_graph_source_observations_v1",
    "cold_exact_h2_family_v1",
    "cold_exact_h2_oracle_v1",
    "continuation_catalogues_from_states_v1",
    "motif_states_v1",
    "registered_cross_graph_contexts_v1",
    "registered_cross_graph_family_v1",
    "target_continuation_catalogues_v1",
    "target_root_catalogues_v1",
    "validate_cross_graph_foundation_authority_v1",
]
