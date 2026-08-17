"""Finite stochastic modular-routing kernel for compositional synthesis.

The kernel combines a deterministic action-conditioned modular relation with a
two-point stochastic resource support.  It exposes no abstract model or
planning shortcut; construction adapters may erase all names below.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import random

from acfqp.core import Outcome


class StochasticModularStatus(str, Enum):
    ACTIVE = "active"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, order=True, slots=True)
class StochasticModularState:
    node: int
    phase: int
    resource: int
    steps: int
    status: StochasticModularStatus = StochasticModularStatus.ACTIVE


@dataclass(frozen=True, order=True, slots=True)
class StochasticModularAction:
    edge: int


@dataclass(frozen=True, slots=True)
class StochasticModularEdge:
    source: int
    destination: int
    mode: int
    magnitude: int
    cost_class: int
    high_cost_probability: Fraction


@dataclass(frozen=True, slots=True)
class StochasticModularGenerationEvidence:
    seed: int
    robust_path: tuple[int, ...]
    verified: bool


@dataclass(frozen=True, slots=True)
class StochasticModularKernel:
    node_count: int
    modulus: int
    capacity: int
    step_limit: int
    goal_phase: int
    mode_deltas: tuple[int, ...]
    edges: tuple[StochasticModularEdge, ...]

    def __post_init__(self) -> None:
        if self.node_count < 4 or self.modulus < 3:
            raise ValueError("stochastic modular graph specification changed")
        if self.capacity <= 0 or self.step_limit < self.node_count - 1:
            raise ValueError("stochastic modular resource bound changed")
        if not 0 <= self.goal_phase < self.modulus:
            raise ValueError("stochastic modular goal phase changed")
        if not self.mode_deltas or any(
            not 0 < value < self.modulus for value in self.mode_deltas
        ):
            raise ValueError("stochastic modular mode table changed")
        if not self.edges:
            raise ValueError("stochastic modular graph is empty")
        for edge in self.edges:
            if not 0 <= edge.source < edge.destination < self.node_count:
                raise ValueError("stochastic modular edge must advance through the DAG")
            if not 0 <= edge.mode < len(self.mode_deltas):
                raise ValueError("stochastic modular edge mode changed")
            if edge.magnitude <= 0 or edge.cost_class < 0:
                raise ValueError("stochastic modular cost descriptor changed")
            if not 0 < edge.high_cost_probability < 1:
                raise ValueError("stochastic modular probability changed")
        for node in range(self.node_count - 1):
            if not any(edge.source == node for edge in self.edges):
                raise ValueError("every nonterminal node needs an outgoing edge")

    @property
    def goal_node(self) -> int:
        return self.node_count - 1

    def initial_distribution(
        self,
    ) -> tuple[tuple[Fraction, StochasticModularState], ...]:
        return ((Fraction(1), StochasticModularState(0, 0, 0, 0)),)

    def actions(
        self, state: StochasticModularState
    ) -> tuple[StochasticModularAction, ...]:
        self._validate_state(state)
        if state.status is not StochasticModularStatus.ACTIVE:
            return ()
        return tuple(
            StochasticModularAction(index)
            for index, edge in enumerate(self.edges)
            if edge.source == state.node
        )

    def step(
        self,
        state: StochasticModularState,
        action: StochasticModularAction,
    ) -> tuple[Outcome[StochasticModularState], ...]:
        self._validate_state(state)
        if action not in self.actions(state):
            raise ValueError("stochastic modular action is not legal")
        edge = self.edges[action.edge]
        phase = (state.phase + self.mode_deltas[edge.mode]) % self.modulus
        steps = state.steps + 1
        outcomes = []
        for delta, probability in (
            (0, 1 - edge.high_cost_probability),
            (edge.magnitude, edge.high_cost_probability),
        ):
            resource = state.resource + delta
            if resource > self.capacity or steps > self.step_limit:
                status = StochasticModularStatus.FAILURE
            elif edge.destination == self.goal_node:
                status = (
                    StochasticModularStatus.SUCCESS
                    if phase == self.goal_phase
                    else StochasticModularStatus.FAILURE
                )
            else:
                status = StochasticModularStatus.ACTIVE
            successor = StochasticModularState(
                edge.destination,
                phase,
                resource,
                steps,
                status,
            )
            outcomes.append(
                Outcome(
                    probability,
                    successor,
                    (),
                    failure=status is StochasticModularStatus.FAILURE,
                    terminal=status is not StochasticModularStatus.ACTIVE,
                )
            )
        return tuple(outcomes)

    def _validate_state(self, state: StochasticModularState) -> None:
        if not 0 <= state.node < self.node_count:
            raise ValueError("stochastic modular node changed")
        if not 0 <= state.phase < self.modulus:
            raise ValueError("stochastic modular phase changed")
        if state.resource < 0 or state.steps < 0:
            raise ValueError("stochastic modular counters changed")


def select_seeded_stochastic_modular_outcome_v1(
    outcomes: tuple[Outcome[StochasticModularState], ...],
    *,
    seed: int,
    episode_index: int,
    decision_index: int,
) -> tuple[Outcome[StochasticModularState], str]:
    if not outcomes or sum((row.probability for row in outcomes), Fraction()) != 1:
        raise ValueError("stochastic modular outcome distribution changed")
    tape = hashlib.sha256(
        b"acfqp:stochastic-modular-outcome:v1\x00"
        + str(seed).encode("ascii")
        + b"\x00"
        + str(episode_index).encode("ascii")
        + b"\x00"
        + str(decision_index).encode("ascii")
    ).digest()
    draw = Fraction(int.from_bytes(tape, "big"), 1 << (8 * len(tape)))
    cumulative = Fraction()
    for outcome in outcomes:
        cumulative += outcome.probability
        if draw < cumulative:
            return outcome, tape.hex()
    raise AssertionError("stochastic modular draw escaped a unit distribution")


def generate_stochastic_modular_routing(
    *,
    node_count: int,
    modulus: int,
    capacity: int,
    step_limit: int,
    mode_deltas: tuple[int, ...],
    seed: int,
    require_last_mode: bool = False,
) -> tuple[StochasticModularKernel, StochasticModularGenerationEvidence]:
    if (
        node_count < 4
        or modulus < 3
        or capacity < node_count - 1
        or step_limit < node_count - 1
        or not mode_deltas
        or any(not 0 < value < modulus for value in mode_deltas)
    ):
        raise ValueError("infeasible stochastic modular generator specification")
    rng = random.Random(seed)
    probabilities = (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4))
    path_modes = [rng.randrange(len(mode_deltas)) for _ in range(node_count - 1)]
    if require_last_mode:
        path_modes[0] = len(mode_deltas) - 1
    goal_phase = sum(mode_deltas[index] for index in path_modes) % modulus
    edges: list[StochasticModularEdge] = []
    path_old_indices = []
    for node in range(node_count - 1):
        cost_class = (seed + node) % 3
        magnitude = 1 + cost_class
        path_old_indices.append(len(edges))
        edges.append(
            StochasticModularEdge(
                node,
                node + 1,
                path_modes[node],
                magnitude,
                cost_class,
                probabilities[cost_class],
            )
        )
        if node + 2 < node_count:
            alternate_class = (cost_class + 1) % 3
            alternate_mode = (
                path_modes[node] + 1 + rng.randrange(len(mode_deltas))
            ) % len(mode_deltas)
            edges.append(
                StochasticModularEdge(
                    node,
                    node + 2,
                    alternate_mode,
                    2 + alternate_class,
                    alternate_class,
                    probabilities[alternate_class],
                )
            )
    order = list(range(len(edges)))
    rng.shuffle(order)
    shuffled = tuple(edges[index] for index in order)
    old_to_new = {old: new for new, old in enumerate(order)}
    robust_path = tuple(old_to_new[index] for index in path_old_indices)
    kernel = StochasticModularKernel(
        node_count=node_count,
        modulus=modulus,
        capacity=capacity,
        step_limit=step_limit,
        goal_phase=goal_phase,
        mode_deltas=mode_deltas,
        edges=shuffled,
    )
    state = kernel.initial_distribution()[0][1]
    for edge_index in robust_path:
        outcomes = kernel.step(state, StochasticModularAction(edge_index))
        state = max(outcomes, key=lambda row: row.next_state.resource).next_state
    if state.status is not StochasticModularStatus.SUCCESS:
        raise AssertionError("generated stochastic modular robust path is not successful")
    return kernel, StochasticModularGenerationEvidence(seed, robust_path, True)


__all__ = (
    "StochasticModularAction",
    "StochasticModularEdge",
    "StochasticModularGenerationEvidence",
    "StochasticModularKernel",
    "StochasticModularState",
    "StochasticModularStatus",
    "generate_stochastic_modular_routing",
    "select_seeded_stochastic_modular_outcome_v1",
)
