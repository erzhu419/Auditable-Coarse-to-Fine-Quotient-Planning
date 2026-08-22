"""A stochastic workflow whose reusable increments require relation lookup."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import random

from acfqp.core import Outcome


class RelationKeyedWorkflowStatus(str, Enum):
    ACTIVE = "active"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, order=True, slots=True)
class RelationKeyedWorkflowState:
    stage: int
    completed: int
    reserve: int
    noise: int
    elapsed: int
    status: RelationKeyedWorkflowStatus = RelationKeyedWorkflowStatus.ACTIVE


@dataclass(frozen=True, order=True, slots=True)
class RelationKeyedWorkflowAction:
    rule: int


@dataclass(frozen=True, slots=True)
class RelationKeyedWorkflowRule:
    source_stage: int
    destination_stage: int
    opaque_mode: int
    mode_increment: int
    high_noise_probability: Fraction


@dataclass(frozen=True, slots=True)
class RelationKeyedWorkflowGenerationEvidence:
    seed: int
    robust_rule_path: tuple[int, ...]
    verified: bool


@dataclass(frozen=True, slots=True)
class RelationKeyedWorkflowKernel:
    stage_count: int
    completion_target: int
    modulus: int
    rules: tuple[RelationKeyedWorkflowRule, ...]

    @property
    def goal_stage(self) -> int:
        return self.stage_count - 1

    def initial_distribution(self):
        return ((Fraction(1), RelationKeyedWorkflowState(0, 0, 0, 0, 0)),)

    def actions(self, state: RelationKeyedWorkflowState):
        if state.status is not RelationKeyedWorkflowStatus.ACTIVE:
            return ()
        return tuple(
            RelationKeyedWorkflowAction(index)
            for index, rule in enumerate(self.rules)
            if rule.source_stage == state.stage
        )

    def step(
        self,
        state: RelationKeyedWorkflowState,
        action: RelationKeyedWorkflowAction,
    ):
        if action not in self.actions(state):
            raise ValueError("relation-keyed workflow action is not legal")
        rule = self.rules[action.rule]
        completed = state.completed + rule.mode_increment
        reserve = state.reserve + rule.mode_increment + 1
        terminal = rule.destination_stage == self.goal_stage
        status = (
            RelationKeyedWorkflowStatus.SUCCESS
            if terminal and completed == self.completion_target
            else RelationKeyedWorkflowStatus.FAILURE
            if terminal
            else RelationKeyedWorkflowStatus.ACTIVE
        )
        result = []
        for noise, probability in (
            (0, 1 - rule.high_noise_probability),
            (1, rule.high_noise_probability),
        ):
            successor = RelationKeyedWorkflowState(
                rule.destination_stage,
                completed,
                reserve,
                (state.noise + noise) % 2,
                state.elapsed + 1,
                status,
            )
            result.append(
                Outcome(
                    probability,
                    successor,
                    (),
                    failure=status is RelationKeyedWorkflowStatus.FAILURE,
                    terminal=status is not RelationKeyedWorkflowStatus.ACTIVE,
                )
            )
        return tuple(result)


def select_seeded_relation_keyed_workflow_outcome_v1(
    outcomes,
    *,
    seed: int,
    episode_index: int,
    decision_index: int,
):
    if not outcomes or sum((row.probability for row in outcomes), Fraction()) != 1:
        raise ValueError("relation-keyed outcome distribution changed")
    tape = hashlib.sha256(
        b"acfqp:relation-keyed-workflow-outcome:v1\x00"
        + str(seed).encode()
        + b"\x00"
        + str(episode_index).encode()
        + b"\x00"
        + str(decision_index).encode()
    ).digest()
    draw = Fraction(int.from_bytes(tape, "big"), 1 << (8 * len(tape)))
    cumulative = Fraction()
    for outcome in outcomes:
        cumulative += outcome.probability
        if draw < cumulative:
            return outcome, tape.hex()
    raise AssertionError("relation-keyed draw escaped unit support")


def generate_stochastic_relation_keyed_workflow(*, stage_count: int, seed: int):
    if stage_count < 5:
        raise ValueError("relation-keyed workflow needs at least five stages")
    rng = random.Random(seed ^ 0x151A91)
    mode_tokens = (seed * 10 + 3, seed * 10 + 7)
    probabilities = (Fraction(1, 5), Fraction(2, 5), Fraction(3, 5))
    rules = []
    robust_old = []
    for stage in range(stage_count - 1):
        for mode, increment in enumerate((1, 2)):
            if mode == 1:
                robust_old.append(len(rules))
            rules.append(
                RelationKeyedWorkflowRule(
                    stage,
                    stage + 1,
                    mode_tokens[mode],
                    increment,
                    probabilities[(seed + stage + mode) % len(probabilities)],
                )
            )
    order = list(range(len(rules)))
    rng.shuffle(order)
    shuffled = tuple(rules[index] for index in order)
    old_to_new = {old: new for new, old in enumerate(order)}
    robust = tuple(old_to_new[index] for index in robust_old)
    kernel = RelationKeyedWorkflowKernel(
        stage_count,
        2 * (stage_count - 1),
        17,
        shuffled,
    )
    state = kernel.initial_distribution()[0][1]
    for key in robust:
        state = kernel.step(state, RelationKeyedWorkflowAction(key))[0].next_state
    if state.status is not RelationKeyedWorkflowStatus.SUCCESS:
        raise AssertionError("relation-keyed robust path did not close")
    return kernel, RelationKeyedWorkflowGenerationEvidence(seed, robust, True)


__all__ = (
    "RelationKeyedWorkflowAction",
    "RelationKeyedWorkflowKernel",
    "RelationKeyedWorkflowState",
    "RelationKeyedWorkflowStatus",
    "generate_stochastic_relation_keyed_workflow",
    "select_seeded_relation_keyed_workflow_outcome_v1",
)
