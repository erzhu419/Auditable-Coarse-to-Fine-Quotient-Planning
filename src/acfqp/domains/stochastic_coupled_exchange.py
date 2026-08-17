"""Higher-order partial/stochastic coupled-exchange kernel.

The ground kernel exposes no abstraction.  Each action simultaneously advances
an exchange stage, changes two anonymous inventories, and yields a two-point
risk support.  The primary inventory update composes two action increments,
so its exact transition requires a depth-two integer expression.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import random

from acfqp.core import Outcome


class CoupledExchangeStatus(str, Enum):
    ACTIVE = "active"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, order=True, slots=True)
class CoupledExchangeState:
    stage: int
    primary: int
    secondary: int
    bonus: int
    risk: int
    steps: int
    status: CoupledExchangeStatus = CoupledExchangeStatus.ACTIVE


@dataclass(frozen=True, order=True, slots=True)
class CoupledExchangeAction:
    exchange: int


@dataclass(frozen=True, slots=True)
class CoupledExchangeRule:
    source_stage: int
    destination_stage: int
    primary_increment: int
    secondary_increment: int
    risk_increment: int
    high_risk_probability: Fraction


@dataclass(frozen=True, slots=True)
class CoupledExchangeGenerationEvidence:
    seed: int
    robust_exchange_path: tuple[int, ...]
    verified: bool


@dataclass(frozen=True, slots=True)
class CoupledExchangeKernel:
    stage_count: int
    risk_capacity: int
    target_primary: int
    rules: tuple[CoupledExchangeRule, ...]

    def __post_init__(self) -> None:
        if self.stage_count < 5 or self.risk_capacity <= 0 or self.target_primary <= 0:
            raise ValueError("coupled exchange dimensions changed")
        if not self.rules:
            raise ValueError("coupled exchange rule inventory changed")
        for rule in self.rules:
            if not 0 <= rule.source_stage < rule.destination_stage < self.stage_count:
                raise ValueError("coupled exchange rule must advance the stage DAG")
            if min(
                rule.primary_increment,
                rule.secondary_increment,
                rule.risk_increment,
            ) <= 0:
                raise ValueError("coupled exchange increments changed")
            if not 0 < rule.high_risk_probability < 1:
                raise ValueError("coupled exchange probability changed")
        for stage in range(self.stage_count - 1):
            if not any(rule.source_stage == stage for rule in self.rules):
                raise ValueError("each nonterminal exchange stage needs a rule")

    @property
    def goal_stage(self) -> int:
        return self.stage_count - 1

    def initial_distribution(self) -> tuple[tuple[Fraction, CoupledExchangeState], ...]:
        return ((Fraction(1), CoupledExchangeState(0, 0, 0, 0, 0, 0)),)

    def actions(self, state: CoupledExchangeState) -> tuple[CoupledExchangeAction, ...]:
        self._validate_state(state)
        if state.status is not CoupledExchangeStatus.ACTIVE:
            return ()
        return tuple(
            CoupledExchangeAction(index)
            for index, rule in enumerate(self.rules)
            if rule.source_stage == state.stage
        )

    def step(
        self,
        state: CoupledExchangeState,
        action: CoupledExchangeAction,
    ) -> tuple[Outcome[CoupledExchangeState], ...]:
        self._validate_state(state)
        if action not in self.actions(state):
            raise ValueError("coupled exchange action is not legal")
        rule = self.rules[action.exchange]
        primary = (
            state.primary + rule.primary_increment + rule.secondary_increment
        )
        secondary = state.secondary + rule.secondary_increment
        outcomes = []
        for increment, probability in (
            (0, 1 - rule.high_risk_probability),
            (rule.risk_increment, rule.high_risk_probability),
        ):
            risk = state.risk + increment
            if risk > self.risk_capacity:
                status = CoupledExchangeStatus.FAILURE
            elif rule.destination_stage == self.goal_stage:
                status = (
                    CoupledExchangeStatus.SUCCESS
                    if primary == self.target_primary
                    else CoupledExchangeStatus.FAILURE
                )
            else:
                status = CoupledExchangeStatus.ACTIVE
            successor = CoupledExchangeState(
                rule.destination_stage,
                primary,
                secondary,
                state.bonus + rule.primary_increment,
                risk,
                state.steps + rule.risk_increment,
                status,
            )
            outcomes.append(
                Outcome(
                    probability,
                    successor,
                    (),
                    failure=status is CoupledExchangeStatus.FAILURE,
                    terminal=status is not CoupledExchangeStatus.ACTIVE,
                )
            )
        return tuple(outcomes)

    def _validate_state(self, state: CoupledExchangeState) -> None:
        if not 0 <= state.stage < self.stage_count:
            raise ValueError("coupled exchange stage changed")
        if min(state.primary, state.secondary, state.bonus, state.risk, state.steps) < 0:
            raise ValueError("coupled exchange counters changed")


def select_seeded_coupled_exchange_outcome_v1(
    outcomes: tuple[Outcome[CoupledExchangeState], ...],
    *,
    seed: int,
    episode_index: int,
    decision_index: int,
) -> tuple[Outcome[CoupledExchangeState], str]:
    if not outcomes or sum((row.probability for row in outcomes), Fraction()) != 1:
        raise ValueError("coupled exchange outcome distribution changed")
    tape = hashlib.sha256(
        b"acfqp:coupled-exchange-outcome:v1\x00"
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
    raise AssertionError("coupled exchange draw escaped a unit distribution")


def generate_stochastic_coupled_exchange(
    *,
    stage_count: int,
    seed: int,
    primary_base: int = 2,
) -> tuple[CoupledExchangeKernel, CoupledExchangeGenerationEvidence]:
    if stage_count < 5 or primary_base < 2:
        raise ValueError("coupled exchange generator dimensions changed")
    rng = random.Random(seed)
    probabilities = (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4))
    primary = [primary_base + rng.randrange(3) for _ in range(stage_count - 1)]
    # A constant unit secondary increment leaves a generic depth-two target:
    # primary' = primary + action.primary_increment + action.secondary_increment.
    # The intermediate primary + action.primary residual is one everywhere,
    # so a bounded MDL/residual search can retain it without a domain pattern.
    secondary = [1 for _ in range(stage_count - 1)]
    risks = [1 + rng.randrange(2) for _ in range(stage_count - 1)]
    target = sum(a + b for a, b in zip(primary, secondary, strict=True))
    capacity = sum(risks) + 1
    rules: list[CoupledExchangeRule] = []
    path_old_indices = []
    for stage in range(stage_count - 1):
        path_old_indices.append(len(rules))
        rules.append(
            CoupledExchangeRule(
                stage,
                stage + 1,
                primary[stage],
                secondary[stage],
                risks[stage],
                probabilities[(seed + stage) % len(probabilities)],
            )
        )
        if stage + 2 < stage_count:
            shortcut_primary = primary[stage] + primary[stage + 1]
            # Keep the anonymous secondary-increment field constant across the
            # catalogue.  Its unary relation class is therefore unique, which
            # bounds witness-blind layout matching without naming the field.
            shortcut_secondary = 1
            if (seed + stage) % 2:
                shortcut_primary += 1
            rules.append(
                CoupledExchangeRule(
                    stage,
                    stage + 2,
                    shortcut_primary,
                    shortcut_secondary,
                    risks[stage] + risks[stage + 1] + 1,
                    probabilities[(seed + stage + 1) % len(probabilities)],
                )
            )
    order = list(range(len(rules)))
    rng.shuffle(order)
    shuffled = tuple(rules[index] for index in order)
    old_to_new = {old: new for new, old in enumerate(order)}
    robust_path = tuple(old_to_new[index] for index in path_old_indices)
    kernel = CoupledExchangeKernel(stage_count, capacity, target, shuffled)
    state = kernel.initial_distribution()[0][1]
    for rule_index in robust_path:
        outcomes = kernel.step(state, CoupledExchangeAction(rule_index))
        state = max(outcomes, key=lambda row: row.next_state.risk).next_state
    if state.status is not CoupledExchangeStatus.SUCCESS:
        raise AssertionError("generated coupled exchange robust path is not successful")
    return kernel, CoupledExchangeGenerationEvidence(seed, robust_path, True)


__all__ = (
    "CoupledExchangeAction",
    "CoupledExchangeGenerationEvidence",
    "CoupledExchangeKernel",
    "CoupledExchangeRule",
    "CoupledExchangeState",
    "CoupledExchangeStatus",
    "generate_stochastic_coupled_exchange",
    "select_seeded_coupled_exchange_outcome_v1",
)
