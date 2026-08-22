"""Stochastic fan-out routing with an anonymous action-to-phase relation.

The ground kernel is a branching DAG rather than the stage-local workflow used
by V151--V153.  It exposes neither the anonymous relation nor a planning
shortcut to construction code.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import random

from acfqp.core import Outcome


class RelationFanoutStatus(str, Enum):
    ACTIVE = "active"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, order=True, slots=True)
class RelationFanoutState:
    node: int
    phase: int
    resource: int
    checksum: int
    steps: int
    status: RelationFanoutStatus = RelationFanoutStatus.ACTIVE


@dataclass(frozen=True, order=True, slots=True)
class RelationFanoutAction:
    edge: int


@dataclass(frozen=True, slots=True)
class RelationFanoutRule:
    source: int
    destination: int
    opaque_mode: int
    increment: int
    risk_increment: int
    high_risk_probability: Fraction


@dataclass(frozen=True, slots=True)
class RelationFanoutKernel:
    node_count: int
    modulus: int
    capacity: int
    goal_phase: int
    rules: tuple[RelationFanoutRule, ...]

    @property
    def goal_node(self) -> int:
        return self.node_count - 1

    def initial_distribution(self):
        return ((Fraction(1), RelationFanoutState(0, 0, 0, 0, 0)),)

    def actions(self, state: RelationFanoutState):
        self._validate(state)
        if state.status is not RelationFanoutStatus.ACTIVE:
            return ()
        return tuple(
            RelationFanoutAction(index)
            for index, rule in enumerate(self.rules)
            if rule.source == state.node
        )

    def step(self, state: RelationFanoutState, action: RelationFanoutAction):
        self._validate(state)
        if action not in self.actions(state):
            raise ValueError("relation fan-out action is not legal")
        rule = self.rules[action.edge]
        phase = (state.phase + rule.increment) % self.modulus
        outcomes = []
        for risk_delta, probability in (
            (0, 1 - rule.high_risk_probability),
            (rule.risk_increment, rule.high_risk_probability),
        ):
            resource = state.resource + risk_delta
            if resource > self.capacity:
                status = RelationFanoutStatus.FAILURE
            elif rule.destination == self.goal_node:
                status = (
                    RelationFanoutStatus.SUCCESS
                    if phase == self.goal_phase
                    else RelationFanoutStatus.FAILURE
                )
            else:
                status = RelationFanoutStatus.ACTIVE
            successor = RelationFanoutState(
                rule.destination,
                phase,
                resource,
                state.checksum + rule.increment + 1,
                state.steps + 1,
                status,
            )
            outcomes.append(
                Outcome(
                    probability,
                    successor,
                    (),
                    failure=status is RelationFanoutStatus.FAILURE,
                    terminal=status is not RelationFanoutStatus.ACTIVE,
                )
            )
        return tuple(outcomes)

    def _validate(self, state: RelationFanoutState) -> None:
        if not 0 <= state.node < self.node_count or not 0 <= state.phase < self.modulus:
            raise ValueError("relation fan-out state changed")
        if min(state.resource, state.checksum, state.steps) < 0:
            raise ValueError("relation fan-out counters changed")


def select_seeded_relation_fanout_outcome_v154(
    outcomes, *, seed: int, episode_index: int, decision_index: int
):
    if not outcomes or sum((row.probability for row in outcomes), Fraction()) != 1:
        raise ValueError("relation fan-out distribution changed")
    tape = hashlib.sha256(
        b"acfqp:relation-fanout-outcome:v154\x00"
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
    raise AssertionError("relation fan-out draw escaped unit support")


def generate_stochastic_relation_fanout_routing_v154(*, seed: int):
    rng = random.Random(seed ^ 0x154A61)
    node_count = 5
    mode_tokens = tuple(seed * 40 + value for value in (5, 17, 29, 41))
    probabilities = (Fraction(1, 5), Fraction(2, 5), Fraction(3, 5), Fraction(4, 5))
    rules = []
    robust_old = []
    for node in range(node_count - 1):
        for mode, increment in enumerate((1, 2, 3, 4)):
            destination = min(node_count - 1, node + (2 if mode == 3 else 1))
            if mode == 3 and node in (0, 2):
                robust_old.append(len(rules))
            rules.append(
                RelationFanoutRule(
                    node,
                    destination,
                    mode_tokens[mode],
                    increment,
                    1 + ((seed + node + 2 * mode) % 3),
                    probabilities[(seed + node + mode) % 4],
                )
            )
    order = list(range(len(rules)))
    rng.shuffle(order)
    shuffled = tuple(rules[index] for index in order)
    old_to_new = {old: new for new, old in enumerate(order)}
    robust = tuple(old_to_new[index] for index in robust_old)
    kernel = RelationFanoutKernel(node_count, 19, 24, 8, shuffled)
    state = kernel.initial_distribution()[0][1]
    for key in robust:
        state = max(
            kernel.step(state, RelationFanoutAction(key)),
            key=lambda row: row.next_state.resource,
        ).next_state
    if state.status is not RelationFanoutStatus.SUCCESS:
        raise AssertionError("relation fan-out robust path did not close")
    return kernel, {"seed": seed, "robust_path": robust, "verified": True}


__all__ = (
    "RelationFanoutAction",
    "RelationFanoutState",
    "RelationFanoutStatus",
    "generate_stochastic_relation_fanout_routing_v154",
    "select_seeded_relation_fanout_outcome_v154",
)
