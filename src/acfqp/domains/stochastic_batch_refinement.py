"""Fresh finite stochastic batch-refinement ground kernel for V54.

The kernel exposes only typed ground states and actions.  Its generation
evidence is deliberately separate so the registered constructor can remain
witness blind.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import random

from acfqp.core import Outcome


class BatchRefinementStatus(str, Enum):
    ACTIVE = "active"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, order=True, slots=True)
class BatchRefinementState:
    stage: int
    units: int
    risk: int
    checksum: int
    status: BatchRefinementStatus = BatchRefinementStatus.ACTIVE


@dataclass(frozen=True, order=True, slots=True)
class BatchRefinementAction:
    rule: int


@dataclass(frozen=True, slots=True)
class BatchRefinementRule:
    source_stage: int
    destination_stage: int
    anonymous_advance_class: int
    unit_increment: int
    risk_increment: int
    high_risk_probability: Fraction


@dataclass(frozen=True, slots=True)
class BatchRefinementGenerationEvidence:
    seed: int
    robust_rule_path: tuple[int, ...]
    verified: bool


@dataclass(frozen=True, slots=True)
class BatchRefinementKernel:
    stage_count: int
    risk_capacity: int
    target_units: int
    checksum_modulus: int
    rules: tuple[BatchRefinementRule, ...]

    def __post_init__(self) -> None:
        if self.stage_count < 5 or self.checksum_modulus < 7:
            raise ValueError("batch-refinement dimensions changed")
        if self.risk_capacity <= 0 or self.target_units <= 0 or not self.rules:
            raise ValueError("batch-refinement bound changed")
        for rule in self.rules:
            if not 0 <= rule.source_stage < rule.destination_stage < self.stage_count:
                raise ValueError("batch-refinement rule must advance through its DAG")
            if rule.destination_stage - rule.source_stage not in {1, 2}:
                raise ValueError("batch-refinement advance support changed")
            if rule.unit_increment <= 0 or rule.risk_increment <= 0:
                raise ValueError("batch-refinement increment changed")
            if not 0 < rule.high_risk_probability < 1:
                raise ValueError("batch-refinement probability changed")
        for stage in range(self.stage_count - 1):
            if not any(rule.source_stage == stage for rule in self.rules):
                raise ValueError("each active batch stage requires a rule")

    @property
    def goal_stage(self) -> int:
        return self.stage_count - 1

    def initial_distribution(self) -> tuple[tuple[Fraction, BatchRefinementState], ...]:
        return ((Fraction(1), BatchRefinementState(0, 0, 0, 0)),)

    def actions(self, state: BatchRefinementState) -> tuple[BatchRefinementAction, ...]:
        self._validate_state(state)
        if state.status is not BatchRefinementStatus.ACTIVE:
            return ()
        return tuple(
            BatchRefinementAction(index)
            for index, rule in enumerate(self.rules)
            if rule.source_stage == state.stage
        )

    def step(
        self, state: BatchRefinementState, action: BatchRefinementAction
    ) -> tuple[Outcome[BatchRefinementState], ...]:
        self._validate_state(state)
        if action not in self.actions(state):
            raise ValueError("batch-refinement action is not legal")
        rule = self.rules[action.rule]
        units = state.units + rule.unit_increment
        checksum = (state.checksum + rule.unit_increment) % self.checksum_modulus
        outcomes = []
        for risk_delta, probability in (
            (0, 1 - rule.high_risk_probability),
            (rule.risk_increment, rule.high_risk_probability),
        ):
            risk = state.risk + risk_delta
            if risk > self.risk_capacity:
                status = BatchRefinementStatus.FAILURE
            elif rule.destination_stage == self.goal_stage:
                status = (
                    BatchRefinementStatus.SUCCESS
                    if units == self.target_units
                    else BatchRefinementStatus.FAILURE
                )
            else:
                status = BatchRefinementStatus.ACTIVE
            outcomes.append(
                Outcome(
                    probability,
                    BatchRefinementState(
                        rule.destination_stage, units, risk, checksum, status
                    ),
                    (),
                    failure=status is BatchRefinementStatus.FAILURE,
                    terminal=status is not BatchRefinementStatus.ACTIVE,
                )
            )
        return tuple(outcomes)

    def _validate_state(self, state: BatchRefinementState) -> None:
        if not 0 <= state.stage < self.stage_count:
            raise ValueError("batch-refinement stage changed")
        if state.units < 0 or state.risk < 0:
            raise ValueError("batch-refinement counter changed")
        if not 0 <= state.checksum < self.checksum_modulus:
            raise ValueError("batch-refinement checksum changed")


def select_seeded_batch_refinement_outcome_v1(
    outcomes: tuple[Outcome[BatchRefinementState], ...],
    *,
    seed: int,
    episode_index: int,
    decision_index: int,
) -> tuple[Outcome[BatchRefinementState], str]:
    if not outcomes or sum((row.probability for row in outcomes), Fraction()) != 1:
        raise ValueError("batch-refinement outcome distribution changed")
    tape = hashlib.sha256(
        b"acfqp:batch-refinement-outcome:v1\x00"
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
    raise AssertionError("batch-refinement draw escaped a unit distribution")


def generate_stochastic_batch_refinement(
    *, stage_count: int, unit_base: int, seed: int
) -> tuple[BatchRefinementKernel, BatchRefinementGenerationEvidence]:
    if stage_count < 5 or unit_base < 2:
        raise ValueError("batch-refinement generator specification changed")
    rng = random.Random(seed)
    probabilities = (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4))
    advance_tokens = {1: 17 + 6 * (seed % 5), 2: 43 + 6 * (seed % 5)}
    primary_units = [unit_base + rng.randrange(3) for _ in range(stage_count - 1)]
    primary_risks = [1 + rng.randrange(3) for _ in range(stage_count - 1)]
    rules: list[BatchRefinementRule] = []
    robust_path = []
    for stage in range(stage_count - 1):
        robust_path.append(len(rules))
        rules.append(
            BatchRefinementRule(
                stage,
                stage + 1,
                advance_tokens[1],
                primary_units[stage],
                primary_risks[stage],
                probabilities[(seed + stage) % len(probabilities)],
            )
        )
        if stage + 2 < stage_count:
            skipped_units = primary_units[stage] + primary_units[stage + 1] + 1
            rules.append(
                BatchRefinementRule(
                    stage,
                    stage + 2,
                    advance_tokens[2],
                    skipped_units,
                    primary_risks[stage] + 1,
                    probabilities[(seed + stage + 1) % len(probabilities)],
                )
            )
    kernel = BatchRefinementKernel(
        stage_count=stage_count,
        risk_capacity=sum(primary_risks) + 1,
        target_units=sum(primary_units),
        checksum_modulus=11 + 2 * (seed % 3),
        rules=tuple(rules),
    )
    state = kernel.initial_distribution()[0][1]
    for rule_index in robust_path:
        outcomes = kernel.step(state, BatchRefinementAction(rule_index))
        state = max(outcomes, key=lambda row: row.next_state.risk).next_state
    if state.status is not BatchRefinementStatus.SUCCESS:
        raise AssertionError("batch-refinement robust witness changed")
    return kernel, BatchRefinementGenerationEvidence(seed, tuple(robust_path), True)


__all__ = (
    "BatchRefinementAction",
    "BatchRefinementGenerationEvidence",
    "BatchRefinementKernel",
    "BatchRefinementRule",
    "BatchRefinementState",
    "BatchRefinementStatus",
    "generate_stochastic_batch_refinement",
    "select_seeded_batch_refinement_outcome_v1",
)
