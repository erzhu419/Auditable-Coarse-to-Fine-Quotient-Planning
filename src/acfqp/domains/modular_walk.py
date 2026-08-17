"""Finite modular-walk kernel for template-free world-model synthesis.

The environment exposes ordinary typed states and actions.  Construction K7
adapters deliberately erase the names below before synthesis; this module does
not provide an abstract model or a planning shortcut.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import random

from acfqp.core import Outcome


class ModularWalkStatus(str, Enum):
    ACTIVE = "active"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, order=True, slots=True)
class ModularWalkState:
    node: int
    residue: int
    steps: int
    status: ModularWalkStatus = ModularWalkStatus.ACTIVE


@dataclass(frozen=True, order=True, slots=True)
class ModularWalkAction:
    edge: int


@dataclass(frozen=True, slots=True)
class ModularWalkEdge:
    source: int
    destination: int
    mode: int


@dataclass(frozen=True, slots=True)
class ModularWalkGenerationEvidence:
    seed: int
    successful_path: tuple[int, ...]
    verified: bool


@dataclass(frozen=True, slots=True)
class ModularWalkKernel:
    node_count: int
    modulus: int
    step_limit: int
    goal_residue: int
    mode_deltas: tuple[int, ...]
    edges: tuple[ModularWalkEdge, ...]

    def __post_init__(self) -> None:
        if self.node_count < 4:
            raise ValueError("modular walk needs at least four nodes")
        if self.modulus < 3:
            raise ValueError("modulus must be at least three")
        if self.step_limit < self.node_count - 1:
            raise ValueError("step limit cannot exclude every monotone path")
        if not 0 <= self.goal_residue < self.modulus:
            raise ValueError("goal residue lies outside the modulus")
        if not self.mode_deltas:
            raise ValueError("at least one modular mode is required")
        if any(not 0 < value < self.modulus for value in self.mode_deltas):
            raise ValueError("mode deltas must be strictly inside the modulus")
        if not self.edges:
            raise ValueError("modular walk requires edges")
        for edge in self.edges:
            if not 0 <= edge.source < edge.destination < self.node_count:
                raise ValueError("modular edges must advance through the DAG")
            if not 0 <= edge.mode < len(self.mode_deltas):
                raise ValueError("edge mode lies outside the delta table")
        for node in range(self.node_count - 1):
            if not any(edge.source == node for edge in self.edges):
                raise ValueError("every nonterminal node needs an outgoing edge")

    @property
    def goal_node(self) -> int:
        return self.node_count - 1

    def initial_distribution(self) -> tuple[tuple[Fraction, ModularWalkState], ...]:
        return ((Fraction(1), ModularWalkState(0, 0, 0)),)

    def actions(self, state: ModularWalkState) -> tuple[ModularWalkAction, ...]:
        self._validate_state(state)
        if state.status is not ModularWalkStatus.ACTIVE:
            return ()
        return tuple(
            ModularWalkAction(index)
            for index, edge in enumerate(self.edges)
            if edge.source == state.node
        )

    def step(
        self,
        state: ModularWalkState,
        action: ModularWalkAction,
    ) -> tuple[Outcome[ModularWalkState], ...]:
        self._validate_state(state)
        if action not in self.actions(state):
            raise ValueError("modular action is not legal")
        edge = self.edges[action.edge]
        residue = (state.residue + self.mode_deltas[edge.mode]) % self.modulus
        steps = state.steps + 1
        if steps > self.step_limit:
            status = ModularWalkStatus.FAILURE
        elif edge.destination == self.goal_node:
            status = (
                ModularWalkStatus.SUCCESS
                if residue == self.goal_residue
                else ModularWalkStatus.FAILURE
            )
        else:
            status = ModularWalkStatus.ACTIVE
        successor = ModularWalkState(edge.destination, residue, steps, status)
        return (
            Outcome(
                Fraction(1),
                successor,
                (),
                failure=status is ModularWalkStatus.FAILURE,
                terminal=status is not ModularWalkStatus.ACTIVE,
            ),
        )

    def _validate_state(self, state: ModularWalkState) -> None:
        if not 0 <= state.node < self.node_count:
            raise ValueError("modular node lies outside the graph")
        if not 0 <= state.residue < self.modulus:
            raise ValueError("modular residue lies outside the modulus")
        if state.steps < 0:
            raise ValueError("modular step count must be nonnegative")


def generate_modular_walk(
    *,
    node_count: int,
    modulus: int,
    step_limit: int,
    mode_deltas: tuple[int, ...],
    seed: int,
    require_last_mode: bool = False,
) -> tuple[ModularWalkKernel, ModularWalkGenerationEvidence]:
    """Generate a monotone graph with a privately verified successful path.

    ``require_last_mode`` is used only by the held-out generator to ensure that
    its successful path contains a mode absent from source observations.  The
    returned kernel does not reveal the successful path.
    """

    if node_count < 4 or modulus < 3 or step_limit < node_count - 1:
        raise ValueError("infeasible modular-walk specification")
    if not mode_deltas or any(not 0 < value < modulus for value in mode_deltas):
        raise ValueError("invalid modular mode deltas")
    rng = random.Random(seed)

    path_modes = [rng.randrange(len(mode_deltas)) for _ in range(node_count - 1)]
    if require_last_mode:
        path_modes[0] = len(mode_deltas) - 1
    goal_residue = sum(mode_deltas[index] for index in path_modes) % modulus

    edges: list[ModularWalkEdge] = [
        ModularWalkEdge(node, node + 1, path_modes[node])
        for node in range(node_count - 1)
    ]
    for node in range(node_count - 2):
        mode = (path_modes[node] + 1 + rng.randrange(len(mode_deltas))) % len(
            mode_deltas
        )
        edges.append(ModularWalkEdge(node, node + 2, mode))

    order = list(range(len(edges)))
    rng.shuffle(order)
    shuffled = tuple(edges[index] for index in order)
    original_to_new = {old: new for new, old in enumerate(order)}
    successful_path = tuple(original_to_new[node] for node in range(node_count - 1))
    kernel = ModularWalkKernel(
        node_count=node_count,
        modulus=modulus,
        step_limit=step_limit,
        goal_residue=goal_residue,
        mode_deltas=mode_deltas,
        edges=shuffled,
    )

    state = kernel.initial_distribution()[0][1]
    for edge_index in successful_path:
        state = kernel.step(state, ModularWalkAction(edge_index))[0].next_state
    if state.status is not ModularWalkStatus.SUCCESS:
        raise AssertionError("generated modular path did not reach its goal")
    return kernel, ModularWalkGenerationEvidence(seed, successful_path, True)


__all__ = (
    "ModularWalkAction",
    "ModularWalkEdge",
    "ModularWalkGenerationEvidence",
    "ModularWalkKernel",
    "ModularWalkState",
    "ModularWalkStatus",
    "generate_modular_walk",
)
