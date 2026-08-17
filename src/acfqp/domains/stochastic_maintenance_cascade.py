"""Ground-distinct maintenance domain sharing no named abstraction with V51.

The kernel models a maintenance cascade with repair/spare/hazard semantics.
Its anonymous transition law is intentionally eligible for discovery as an
isomorph of the previously compiled factor-composed program, but neither the
kernel nor its raw adapter publishes that correspondence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import random

from acfqp.core import Outcome


class MaintenanceCascadeStatus(str, Enum):
    ACTIVE = "active"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, order=True, slots=True)
class MaintenanceCascadeState:
    zone: int
    repaired_units: int
    spare_units: int
    latent_load: int
    hazard: int
    elapsed: int
    status: MaintenanceCascadeStatus = MaintenanceCascadeStatus.ACTIVE


@dataclass(frozen=True, order=True, slots=True)
class MaintenanceCascadeAction:
    task: int


@dataclass(frozen=True, slots=True)
class MaintenanceCascadeRule:
    source_zone: int
    destination_zone: int
    repair_increment: int
    spare_increment: int
    hazard_increment: int
    high_hazard_probability: Fraction


@dataclass(frozen=True, slots=True)
class MaintenanceCascadeGenerationEvidence:
    seed: int
    robust_task_path: tuple[int, ...]
    verified: bool


@dataclass(frozen=True, slots=True)
class MaintenanceCascadeKernel:
    zone_count: int
    hazard_capacity: int
    repair_target: int
    rules: tuple[MaintenanceCascadeRule, ...]

    def __post_init__(self) -> None:
        if self.zone_count < 5 or self.hazard_capacity <= 0 or self.repair_target <= 0:
            raise ValueError("maintenance cascade dimensions changed")
        if not self.rules:
            raise ValueError("maintenance cascade rule inventory changed")
        for rule in self.rules:
            if not 0 <= rule.source_zone < rule.destination_zone < self.zone_count:
                raise ValueError("maintenance rule must advance the zone DAG")
            if min(
                rule.repair_increment,
                rule.spare_increment,
                rule.hazard_increment,
            ) <= 0:
                raise ValueError("maintenance increments changed")
            if not 0 < rule.high_hazard_probability < 1:
                raise ValueError("maintenance probability changed")
        for zone in range(self.zone_count - 1):
            if not any(rule.source_zone == zone for rule in self.rules):
                raise ValueError("each nonterminal zone needs a task")

    @property
    def goal_zone(self) -> int:
        return self.zone_count - 1

    def initial_distribution(self):
        return (
            (
                Fraction(1),
                MaintenanceCascadeState(0, 0, 0, 0, 0, 0),
            ),
        )

    def actions(self, state: MaintenanceCascadeState):
        self._validate_state(state)
        if state.status is not MaintenanceCascadeStatus.ACTIVE:
            return ()
        return tuple(
            MaintenanceCascadeAction(index)
            for index, rule in enumerate(self.rules)
            if rule.source_zone == state.zone
        )

    def step(self, state: MaintenanceCascadeState, action: MaintenanceCascadeAction):
        self._validate_state(state)
        if action not in self.actions(state):
            raise ValueError("maintenance action is not legal")
        rule = self.rules[action.task]
        repaired = (
            state.repaired_units + rule.repair_increment + rule.spare_increment
        )
        spare = state.spare_units + rule.spare_increment
        outcomes = []
        for increment, probability in (
            (0, 1 - rule.high_hazard_probability),
            (rule.hazard_increment, rule.high_hazard_probability),
        ):
            hazard = state.hazard + increment
            if hazard > self.hazard_capacity:
                status = MaintenanceCascadeStatus.FAILURE
            elif rule.destination_zone == self.goal_zone:
                status = (
                    MaintenanceCascadeStatus.SUCCESS
                    if repaired == self.repair_target
                    else MaintenanceCascadeStatus.FAILURE
                )
            else:
                status = MaintenanceCascadeStatus.ACTIVE
            successor = MaintenanceCascadeState(
                rule.destination_zone,
                repaired,
                spare,
                state.latent_load + rule.repair_increment,
                hazard,
                state.elapsed + rule.hazard_increment,
                status,
            )
            outcomes.append(
                Outcome(
                    probability,
                    successor,
                    (),
                    failure=status is MaintenanceCascadeStatus.FAILURE,
                    terminal=status is not MaintenanceCascadeStatus.ACTIVE,
                )
            )
        return tuple(outcomes)

    def _validate_state(self, state: MaintenanceCascadeState) -> None:
        if not 0 <= state.zone < self.zone_count:
            raise ValueError("maintenance zone changed")
        if min(
            state.repaired_units,
            state.spare_units,
            state.latent_load,
            state.hazard,
            state.elapsed,
        ) < 0:
            raise ValueError("maintenance counters changed")


def select_seeded_maintenance_cascade_outcome_v1(
    outcomes: tuple[Outcome[MaintenanceCascadeState], ...],
    *,
    seed: int,
    episode_index: int,
    decision_index: int,
):
    if not outcomes or sum((row.probability for row in outcomes), Fraction()) != 1:
        raise ValueError("maintenance outcome distribution changed")
    tape = hashlib.sha256(
        b"acfqp:maintenance-cascade-outcome:v1\x00"
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
    raise AssertionError("maintenance draw escaped a unit distribution")


def generate_stochastic_maintenance_cascade(
    *,
    zone_count: int,
    seed: int,
    repair_base: int = 2,
):
    if zone_count < 5 or repair_base < 2:
        raise ValueError("maintenance generator dimensions changed")
    rng = random.Random(seed ^ 0x52CADA)
    probabilities = (Fraction(1, 5), Fraction(2, 5), Fraction(3, 5))
    repairs = [repair_base + rng.randrange(3) for _ in range(zone_count - 1)]
    spares = [1 for _ in range(zone_count - 1)]
    hazards = [1 + rng.randrange(2) for _ in range(zone_count - 1)]
    target = sum(a + b for a, b in zip(repairs, spares, strict=True))
    capacity = sum(hazards) + 1
    rules = []
    path_old_indices = []
    for zone in range(zone_count - 1):
        path_old_indices.append(len(rules))
        rules.append(
            MaintenanceCascadeRule(
                zone,
                zone + 1,
                repairs[zone],
                spares[zone],
                hazards[zone],
                probabilities[(seed + zone) % len(probabilities)],
            )
        )
        if zone + 2 < zone_count:
            shortcut_repair = repairs[zone] + repairs[zone + 1]
            if (seed + zone) % 2:
                shortcut_repair += 1
            rules.append(
                MaintenanceCascadeRule(
                    zone,
                    zone + 2,
                    shortcut_repair,
                    1,
                    hazards[zone] + hazards[zone + 1] + 1,
                    probabilities[(seed + zone + 2) % len(probabilities)],
                )
            )
    order = list(range(len(rules)))
    rng.shuffle(order)
    shuffled = tuple(rules[index] for index in order)
    old_to_new = {old: new for new, old in enumerate(order)}
    robust_path = tuple(old_to_new[index] for index in path_old_indices)
    kernel = MaintenanceCascadeKernel(zone_count, capacity, target, shuffled)
    state = kernel.initial_distribution()[0][1]
    for rule_index in robust_path:
        outcomes = kernel.step(state, MaintenanceCascadeAction(rule_index))
        state = max(outcomes, key=lambda row: row.next_state.hazard).next_state
    if state.status is not MaintenanceCascadeStatus.SUCCESS:
        raise AssertionError("generated maintenance robust path is not successful")
    return kernel, MaintenanceCascadeGenerationEvidence(seed, robust_path, True)


__all__ = (
    "MaintenanceCascadeAction",
    "MaintenanceCascadeGenerationEvidence",
    "MaintenanceCascadeKernel",
    "MaintenanceCascadeRule",
    "MaintenanceCascadeState",
    "MaintenanceCascadeStatus",
    "generate_stochastic_maintenance_cascade",
    "select_seeded_maintenance_cascade_outcome_v1",
)
