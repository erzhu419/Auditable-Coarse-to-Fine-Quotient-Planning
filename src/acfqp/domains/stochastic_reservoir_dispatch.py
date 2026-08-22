"""Finite stochastic reservoir-dispatch domain for the sixth-family campaign."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import random

from acfqp.core import Outcome


class ReservoirDispatchStatus(str, Enum):
    ACTIVE = "active"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, order=True, slots=True)
class ReservoirDispatchState:
    basin: int
    delivered: int
    reserve: int
    salinity: int
    stress: int
    elapsed: int
    status: ReservoirDispatchStatus = ReservoirDispatchStatus.ACTIVE


@dataclass(frozen=True, order=True, slots=True)
class ReservoirDispatchAction:
    conduit: int


@dataclass(frozen=True, slots=True)
class ReservoirDispatchConduit:
    source: int
    destination: int
    delivery_increment: int
    reserve_increment: int
    salinity_scale: int
    stress_increment: int
    high_stress_probability: Fraction


@dataclass(frozen=True, slots=True)
class ReservoirDispatchGenerationEvidence:
    seed: int
    robust_conduit_path: tuple[int, ...]
    verified: bool


@dataclass(frozen=True, slots=True)
class ReservoirDispatchKernel:
    basin_count: int
    stress_capacity: int
    delivery_target: int
    salinity_target: int
    salinity_modulus: int
    step_limit: int
    conduits: tuple[ReservoirDispatchConduit, ...]

    def __post_init__(self) -> None:
        if self.basin_count < 5 or self.salinity_modulus < 7:
            raise ValueError("reservoir-dispatch dimensions changed")
        if (
            self.stress_capacity <= 0
            or self.delivery_target <= 0
            or self.step_limit < self.basin_count - 1
            or not 0 <= self.salinity_target < self.salinity_modulus
            or not self.conduits
        ):
            raise ValueError("reservoir-dispatch bounds changed")
        for conduit in self.conduits:
            if not 0 <= conduit.source < conduit.destination < self.basin_count:
                raise ValueError("reservoir conduit must advance through its DAG")
            if conduit.destination - conduit.source not in {1, 2}:
                raise ValueError("reservoir conduit advance support changed")
            if min(
                conduit.delivery_increment,
                conduit.reserve_increment,
                conduit.salinity_scale,
                conduit.stress_increment,
            ) <= 0:
                raise ValueError("reservoir conduit descriptor changed")
            if not 0 < conduit.high_stress_probability < 1:
                raise ValueError("reservoir conduit probability changed")
        for basin in range(self.basin_count - 1):
            if not any(row.source == basin for row in self.conduits):
                raise ValueError("each nonterminal reservoir basin needs a conduit")

    @property
    def goal_basin(self) -> int:
        return self.basin_count - 1

    def initial_distribution(self):
        return (
            (
                Fraction(1),
                ReservoirDispatchState(0, 0, 0, 0, 0, 0),
            ),
        )

    def actions(self, state: ReservoirDispatchState):
        self._validate_state(state)
        if state.status is not ReservoirDispatchStatus.ACTIVE:
            return ()
        return tuple(
            ReservoirDispatchAction(index)
            for index, conduit in enumerate(self.conduits)
            if conduit.source == state.basin
        )

    def step(self, state: ReservoirDispatchState, action: ReservoirDispatchAction):
        self._validate_state(state)
        if action not in self.actions(state):
            raise ValueError("reservoir-dispatch action is not legal")
        conduit = self.conduits[action.conduit]
        delivered = (
            state.delivered
            + conduit.delivery_increment
            + conduit.reserve_increment
        )
        reserve = state.reserve + conduit.reserve_increment
        salinity = (
            state.salinity
            + state.delivered * conduit.salinity_scale
            + conduit.delivery_increment
        ) % self.salinity_modulus
        elapsed = state.elapsed + 1
        outcomes = []
        for stress_delta, probability in (
            (0, 1 - conduit.high_stress_probability),
            (conduit.stress_increment, conduit.high_stress_probability),
        ):
            stress = state.stress + stress_delta
            if stress > self.stress_capacity or elapsed > self.step_limit:
                status = ReservoirDispatchStatus.FAILURE
            elif conduit.destination == self.goal_basin:
                status = (
                    ReservoirDispatchStatus.SUCCESS
                    if delivered == self.delivery_target
                    and salinity == self.salinity_target
                    else ReservoirDispatchStatus.FAILURE
                )
            else:
                status = ReservoirDispatchStatus.ACTIVE
            successor = ReservoirDispatchState(
                conduit.destination,
                delivered,
                reserve,
                salinity,
                stress,
                elapsed,
                status,
            )
            outcomes.append(
                Outcome(
                    probability,
                    successor,
                    (),
                    failure=status is ReservoirDispatchStatus.FAILURE,
                    terminal=status is not ReservoirDispatchStatus.ACTIVE,
                )
            )
        return tuple(outcomes)

    def _validate_state(self, state: ReservoirDispatchState) -> None:
        if not 0 <= state.basin < self.basin_count:
            raise ValueError("reservoir basin changed")
        if min(
            state.delivered,
            state.reserve,
            state.stress,
            state.elapsed,
        ) < 0:
            raise ValueError("reservoir counter changed")
        if not 0 <= state.salinity < self.salinity_modulus:
            raise ValueError("reservoir salinity changed")


def select_seeded_reservoir_dispatch_outcome_v1(
    outcomes: tuple[Outcome[ReservoirDispatchState], ...],
    *,
    seed: int,
    episode_index: int,
    decision_index: int,
):
    if not outcomes or sum((row.probability for row in outcomes), Fraction()) != 1:
        raise ValueError("reservoir-dispatch outcome distribution changed")
    tape = hashlib.sha256(
        b"acfqp:stochastic-reservoir-dispatch-outcome:v1\x00"
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
    raise AssertionError("reservoir-dispatch draw escaped unit support")


def generate_stochastic_reservoir_dispatch(
    *, basin_count: int, seed: int
) -> tuple[ReservoirDispatchKernel, ReservoirDispatchGenerationEvidence]:
    if basin_count < 5:
        raise ValueError("reservoir-dispatch generator dimensions changed")
    rng = random.Random(seed ^ 0x171A61)
    probabilities = (Fraction(1, 5), Fraction(2, 5), Fraction(3, 5))
    deliveries = [2 + rng.randrange(4) for _ in range(basin_count - 1)]
    reserves = [1 + rng.randrange(2) for _ in range(basin_count - 1)]
    salinity_scales = [2 + rng.randrange(5) for _ in range(basin_count - 1)]
    stresses = [1 + rng.randrange(3) for _ in range(basin_count - 1)]
    conduits = []
    robust_old_indices = []
    for basin in range(basin_count - 1):
        robust_old_indices.append(len(conduits))
        conduits.append(
            ReservoirDispatchConduit(
                basin,
                basin + 1,
                deliveries[basin],
                reserves[basin],
                salinity_scales[basin],
                stresses[basin],
                probabilities[(seed + basin) % len(probabilities)],
            )
        )
        if basin + 2 < basin_count:
            conduits.append(
                ReservoirDispatchConduit(
                    basin,
                    basin + 2,
                    deliveries[basin] + deliveries[basin + 1] + 1,
                    reserves[basin] + reserves[basin + 1],
                    salinity_scales[basin] + 1,
                    stresses[basin] + stresses[basin + 1] + 1,
                    probabilities[(seed + basin + 1) % len(probabilities)],
                )
            )
    order = list(range(len(conduits)))
    rng.shuffle(order)
    shuffled = tuple(conduits[index] for index in order)
    old_to_new = {old: new for new, old in enumerate(order)}
    robust_path = tuple(old_to_new[index] for index in robust_old_indices)
    modulus = 19 + 2 * (seed % 4)
    target = sum(a + b for a, b in zip(deliveries, reserves, strict=True))
    salinity = delivered = 0
    for delivery, reserve, scale in zip(
        deliveries, reserves, salinity_scales, strict=True
    ):
        salinity = (salinity + delivered * scale + delivery) % modulus
        delivered += delivery + reserve
    kernel = ReservoirDispatchKernel(
        basin_count=basin_count,
        stress_capacity=sum(stresses) + 2,
        delivery_target=target,
        salinity_target=salinity,
        salinity_modulus=modulus,
        step_limit=basin_count + 2,
        conduits=shuffled,
    )
    state = kernel.initial_distribution()[0][1]
    for conduit_index in robust_path:
        outcomes = kernel.step(state, ReservoirDispatchAction(conduit_index))
        state = max(outcomes, key=lambda row: row.next_state.stress).next_state
    if state.status is not ReservoirDispatchStatus.SUCCESS:
        raise AssertionError("generated reservoir robust path changed")
    return kernel, ReservoirDispatchGenerationEvidence(seed, robust_path, True)


__all__ = (
    "ReservoirDispatchAction",
    "ReservoirDispatchConduit",
    "ReservoirDispatchGenerationEvidence",
    "ReservoirDispatchKernel",
    "ReservoirDispatchState",
    "ReservoirDispatchStatus",
    "generate_stochastic_reservoir_dispatch",
    "select_seeded_reservoir_dispatch_outcome_v1",
)
