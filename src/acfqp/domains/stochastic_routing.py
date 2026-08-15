"""Finite stochastic routing kernel used by the generic world-model campaign.

The kernel exposes ordinary typed states/actions.  The V47 learner receives only
an opaque integer-vector/action-field adapter defined outside this module; it is
never given the source/destination/cost roles below.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import random

from acfqp.core import Outcome


class StochasticRoutingStatus(str, Enum):
    ACTIVE = "active"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, order=True, slots=True)
class StochasticRoutingState:
    node: int
    resource: int
    status: StochasticRoutingStatus = StochasticRoutingStatus.ACTIVE


@dataclass(frozen=True, order=True, slots=True)
class StochasticRoutingAction:
    edge: int


@dataclass(frozen=True, slots=True)
class StochasticRoutingEdge:
    source: int
    destination: int
    cost_class: int
    magnitude: int
    high_cost_probability: Fraction


@dataclass(frozen=True, slots=True)
class StochasticRoutingGenerationEvidence:
    seed: int
    robust_path: tuple[int, ...]
    verified: bool


@dataclass(frozen=True, slots=True)
class StochasticRoutingKernel:
    node_count: int
    capacity: int
    edges: tuple[StochasticRoutingEdge, ...]

    def __post_init__(self) -> None:
        if self.node_count < 3:
            raise ValueError("routing node_count must be at least three")
        if self.capacity <= 0:
            raise ValueError("routing capacity must be positive")
        if not self.edges:
            raise ValueError("routing kernel requires edges")
        for edge in self.edges:
            if not 0 <= edge.source < edge.destination < self.node_count:
                raise ValueError("routing edges must advance through the DAG")
            if edge.cost_class < 0 or edge.magnitude <= 0:
                raise ValueError("routing edge class/magnitude changed")
            if not 0 < edge.high_cost_probability < 1:
                raise ValueError("routing probability must be strictly interior")
        for node in range(self.node_count - 1):
            if not any(edge.source == node for edge in self.edges):
                raise ValueError("every nonterminal routing node needs an outgoing edge")

    @property
    def goal_node(self) -> int:
        return self.node_count - 1

    def initial_distribution(self) -> tuple[tuple[Fraction, StochasticRoutingState], ...]:
        return ((Fraction(1), StochasticRoutingState(0, 0)),)

    def actions(self, state: StochasticRoutingState) -> tuple[StochasticRoutingAction, ...]:
        if state.status is not StochasticRoutingStatus.ACTIVE:
            return ()
        return tuple(
            StochasticRoutingAction(index)
            for index, edge in enumerate(self.edges)
            if edge.source == state.node
        )

    def step(
        self,
        state: StochasticRoutingState,
        action: StochasticRoutingAction,
    ) -> tuple[Outcome[StochasticRoutingState], ...]:
        if action not in self.actions(state):
            raise ValueError("routing action is not legal")
        edge = self.edges[action.edge]
        outcomes = []
        for delta, probability in (
            (0, 1 - edge.high_cost_probability),
            (edge.magnitude, edge.high_cost_probability),
        ):
            resource = state.resource + delta
            status = (
                StochasticRoutingStatus.FAILURE
                if resource > self.capacity
                else StochasticRoutingStatus.SUCCESS
                if edge.destination == self.goal_node
                else StochasticRoutingStatus.ACTIVE
            )
            outcomes.append(
                Outcome(
                    probability,
                    StochasticRoutingState(edge.destination, resource, status),
                    (),
                    failure=status is StochasticRoutingStatus.FAILURE,
                    terminal=status is not StochasticRoutingStatus.ACTIVE,
                )
            )
        return tuple(outcomes)


def select_seeded_routing_outcome_v1(
    outcomes: tuple[Outcome[StochasticRoutingState], ...],
    *,
    seed: int,
    episode_index: int,
    decision_index: int,
) -> tuple[Outcome[StochasticRoutingState], str]:
    if not outcomes or sum((row.probability for row in outcomes), Fraction()) != 1:
        raise ValueError("routing outcome distribution changed")
    tape = hashlib.sha256(
        b"acfqp:stochastic-routing-outcome:v1\x00"
        + str(seed).encode("ascii")
        + b"\x00"
        + str(episode_index).encode("ascii")
        + b"\x00"
        + str(decision_index).encode("ascii")
    ).digest()
    denominator = 1 << (8 * len(tape))
    draw = Fraction(int.from_bytes(tape, "big"), denominator)
    cumulative = Fraction()
    for outcome in outcomes:
        cumulative += outcome.probability
        if draw < cumulative:
            return outcome, tape.hex()
    raise AssertionError("routing seeded draw escaped a unit distribution")


def generate_stochastic_routing(
    *,
    node_count: int,
    capacity: int,
    seed: int,
) -> tuple[StochasticRoutingKernel, StochasticRoutingGenerationEvidence]:
    if node_count < 4 or capacity < node_count // 2:
        raise ValueError("routing generator specification is infeasible")
    rng = random.Random(seed)
    probabilities = (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4))
    edges: list[StochasticRoutingEdge] = []
    robust_path = []
    for node in range(node_count - 1):
        destinations = [node + 1]
        if node + 2 < node_count:
            destinations.append(node + 2)
        for ordinal, destination in enumerate(destinations):
            cost_class = (node + ordinal + seed) % 3
            magnitude = cost_class + 1
            edge = StochasticRoutingEdge(
                node,
                destination,
                cost_class,
                magnitude,
                probabilities[cost_class],
            )
            edges.append(edge)
        robust_path.append(len(edges) - len(destinations))
    # Shuffle edge identities while keeping edge semantics and the graph intact.
    order = list(range(len(edges)))
    rng.shuffle(order)
    shuffled = tuple(edges[index] for index in order)
    old_to_new = {old: new for new, old in enumerate(order)}
    remapped_path = tuple(old_to_new[index] for index in robust_path)
    kernel = StochasticRoutingKernel(node_count, capacity, shuffled)
    return kernel, StochasticRoutingGenerationEvidence(seed, remapped_path, True)


__all__ = (
    "StochasticRoutingAction",
    "StochasticRoutingEdge",
    "StochasticRoutingGenerationEvidence",
    "StochasticRoutingKernel",
    "StochasticRoutingState",
    "StochasticRoutingStatus",
    "generate_stochastic_routing",
    "select_seeded_routing_outcome_v1",
)
