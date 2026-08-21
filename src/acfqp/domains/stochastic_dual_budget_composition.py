"""Source-unseen stochastic composition with a higher-order residual.

The productive and reserve counters have additive action-conditioned updates,
while the checksum couples the prior reserve with an action multiplier.  The
raw construction pipeline must therefore retain a useful partial factor model
without pretending that the higher-order checksum residual was synthesized.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import random

from acfqp.core import Outcome


class DualBudgetStatus(str, Enum):
    ACTIVE = "active"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, order=True, slots=True)
class DualBudgetState:
    stage: int
    primary: int
    reserve: int
    hazard: int
    checksum: int
    status: DualBudgetStatus = DualBudgetStatus.ACTIVE


@dataclass(frozen=True, order=True, slots=True)
class DualBudgetAction:
    rule: int


@dataclass(frozen=True, slots=True)
class DualBudgetRule:
    source_stage: int
    destination_stage: int
    primary_increment: int
    reserve_increment: int
    hazard_increment: int
    checksum_multiplier: int
    high_hazard_probability: Fraction


@dataclass(frozen=True, slots=True)
class DualBudgetGenerationEvidence:
    seed: int
    robust_rule_path: tuple[int, ...]
    verified: bool


@dataclass(frozen=True, slots=True)
class DualBudgetKernel:
    stage_count: int
    hazard_capacity: int
    target_primary: int
    target_reserve: int
    checksum_modulus: int
    rules: tuple[DualBudgetRule, ...]

    def __post_init__(self) -> None:
        if self.stage_count < 5 or self.checksum_modulus < 7:
            raise ValueError("dual-budget dimensions changed")
        if (
            self.hazard_capacity <= 0
            or self.target_primary <= 0
            or self.target_reserve <= 0
            or not self.rules
        ):
            raise ValueError("dual-budget bound changed")
        for rule in self.rules:
            if not (
                0
                <= rule.source_stage
                < rule.destination_stage
                < self.stage_count
            ):
                raise ValueError("dual-budget rule must advance through its DAG")
            if rule.destination_stage - rule.source_stage not in {1, 2}:
                raise ValueError("dual-budget advance support changed")
            if (
                rule.primary_increment <= 0
                or rule.reserve_increment <= 0
                or rule.hazard_increment <= 0
                or rule.checksum_multiplier <= 0
            ):
                raise ValueError("dual-budget increment changed")
            if not 0 < rule.high_hazard_probability < 1:
                raise ValueError("dual-budget probability changed")
        for stage in range(self.stage_count - 1):
            if not any(rule.source_stage == stage for rule in self.rules):
                raise ValueError("each active dual-budget stage requires a rule")

    @property
    def goal_stage(self) -> int:
        return self.stage_count - 1

    def initial_distribution(self) -> tuple[tuple[Fraction, DualBudgetState], ...]:
        return ((Fraction(1), DualBudgetState(0, 0, 0, 0, 0)),)

    def actions(self, state: DualBudgetState) -> tuple[DualBudgetAction, ...]:
        self._validate_state(state)
        if state.status is not DualBudgetStatus.ACTIVE:
            return ()
        return tuple(
            DualBudgetAction(index)
            for index, rule in enumerate(self.rules)
            if rule.source_stage == state.stage
        )

    def step(
        self, state: DualBudgetState, action: DualBudgetAction
    ) -> tuple[Outcome[DualBudgetState], ...]:
        self._validate_state(state)
        if action not in self.actions(state):
            raise ValueError("dual-budget action is not legal")
        rule = self.rules[action.rule]
        primary = state.primary + rule.primary_increment
        reserve = state.reserve + rule.reserve_increment
        checksum = (
            state.checksum
            + state.reserve
            + rule.primary_increment * rule.checksum_multiplier
        ) % self.checksum_modulus
        outcomes = []
        for hazard_delta, probability in (
            (0, 1 - rule.high_hazard_probability),
            (rule.hazard_increment, rule.high_hazard_probability),
        ):
            hazard = state.hazard + hazard_delta
            if hazard > self.hazard_capacity:
                status = DualBudgetStatus.FAILURE
            elif rule.destination_stage == self.goal_stage:
                status = (
                    DualBudgetStatus.SUCCESS
                    if primary == self.target_primary
                    and reserve == self.target_reserve
                    else DualBudgetStatus.FAILURE
                )
            else:
                status = DualBudgetStatus.ACTIVE
            outcomes.append(
                Outcome(
                    probability,
                    DualBudgetState(
                        rule.destination_stage,
                        primary,
                        reserve,
                        hazard,
                        checksum,
                        status,
                    ),
                    (),
                    failure=status is DualBudgetStatus.FAILURE,
                    terminal=status is not DualBudgetStatus.ACTIVE,
                )
            )
        return tuple(outcomes)

    def _validate_state(self, state: DualBudgetState) -> None:
        if not 0 <= state.stage < self.stage_count:
            raise ValueError("dual-budget stage changed")
        if min(state.primary, state.reserve, state.hazard) < 0:
            raise ValueError("dual-budget counter changed")
        if not 0 <= state.checksum < self.checksum_modulus:
            raise ValueError("dual-budget checksum changed")


def select_seeded_dual_budget_outcome_v1(
    outcomes: tuple[Outcome[DualBudgetState], ...],
    *,
    seed: int,
    episode_index: int,
    decision_index: int,
) -> tuple[Outcome[DualBudgetState], str]:
    if not outcomes or sum((row.probability for row in outcomes), Fraction()) != 1:
        raise ValueError("dual-budget outcome distribution changed")
    tape = hashlib.sha256(
        b"acfqp:dual-budget-outcome:v1\x00"
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
    raise AssertionError("dual-budget draw escaped a unit distribution")


def generate_stochastic_dual_budget_composition(
    *, stage_count: int, seed: int
) -> tuple[DualBudgetKernel, DualBudgetGenerationEvidence]:
    if stage_count < 5:
        raise ValueError("dual-budget generator dimensions changed")
    rng = random.Random(seed)
    probabilities = (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4))
    primary_path = [2 + rng.randrange(3) for _ in range(stage_count - 1)]
    reserve_path = [1 + rng.randrange(3) for _ in range(stage_count - 1)]
    hazard_path = [1 + rng.randrange(2) for _ in range(stage_count - 1)]
    rules: list[DualBudgetRule] = []
    path_old_indices = []
    for stage in range(stage_count - 1):
        path_old_indices.append(len(rules))
        rules.append(
            DualBudgetRule(
                stage,
                stage + 1,
                primary_path[stage],
                reserve_path[stage],
                hazard_path[stage],
                12 + (seed + stage) % 5,
                probabilities[(seed + stage) % len(probabilities)],
            )
        )
        if stage + 2 < stage_count:
            rules.append(
                DualBudgetRule(
                    stage,
                    stage + 2,
                    primary_path[stage]
                    + primary_path[stage + 1]
                    + ((seed + stage) % 2),
                    reserve_path[stage]
                    + reserve_path[stage + 1]
                    + ((seed + stage + 1) % 2),
                    hazard_path[stage] + 1,
                    13 + (seed + stage) % 4,
                    probabilities[(seed + stage + 1) % len(probabilities)],
                )
            )
    order = list(range(len(rules)))
    rng.shuffle(order)
    shuffled = tuple(rules[index] for index in order)
    old_to_new = {old: new for new, old in enumerate(order)}
    robust_path = tuple(old_to_new[index] for index in path_old_indices)
    kernel = DualBudgetKernel(
        stage_count=stage_count,
        hazard_capacity=sum(hazard_path) + 1,
        target_primary=sum(primary_path),
        target_reserve=sum(reserve_path),
        checksum_modulus=11 + 2 * (seed % 3),
        rules=shuffled,
    )
    state = kernel.initial_distribution()[0][1]
    for rule_index in robust_path:
        outcomes = kernel.step(state, DualBudgetAction(rule_index))
        state = max(outcomes, key=lambda row: row.next_state.hazard).next_state
    if state.status is not DualBudgetStatus.SUCCESS:
        raise AssertionError("generated dual-budget robust path changed")
    return kernel, DualBudgetGenerationEvidence(seed, robust_path, True)


__all__ = (
    "DualBudgetAction",
    "DualBudgetGenerationEvidence",
    "DualBudgetKernel",
    "DualBudgetRule",
    "DualBudgetState",
    "DualBudgetStatus",
    "generate_stochastic_dual_budget_composition",
    "select_seeded_dual_budget_outcome_v1",
)
