"""Finite stochastic packet-batching kernel with a nonlinear parity residual."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import random

from acfqp.core import Outcome


class PacketBatchingStatus(str, Enum):
    ACTIVE = "active"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, order=True, slots=True)
class PacketBatchingState:
    station: int
    packets: int
    delay: int
    parity: int
    steps: int
    status: PacketBatchingStatus = PacketBatchingStatus.ACTIVE


@dataclass(frozen=True, order=True, slots=True)
class PacketBatchingAction:
    route: int


@dataclass(frozen=True, slots=True)
class PacketBatchingRoute:
    source: int
    destination: int
    packet_increment: int
    delay_increment: int
    parity_scale: int
    cost_class: int
    high_delay_probability: Fraction


@dataclass(frozen=True, slots=True)
class PacketBatchingGenerationEvidence:
    seed: int
    robust_route_path: tuple[int, ...]
    verified: bool


@dataclass(frozen=True, slots=True)
class PacketBatchingKernel:
    station_count: int
    delay_capacity: int
    target_packets: int
    target_parity: int
    parity_modulus: int
    step_limit: int
    routes: tuple[PacketBatchingRoute, ...]

    def __post_init__(self) -> None:
        if self.station_count < 5 or self.parity_modulus < 5:
            raise ValueError("packet-batching dimensions changed")
        if (
            self.delay_capacity <= 0
            or self.target_packets <= 0
            or self.step_limit < self.station_count - 1
            or not 0 <= self.target_parity < self.parity_modulus
            or not self.routes
        ):
            raise ValueError("packet-batching bounds changed")
        for route in self.routes:
            if not 0 <= route.source < route.destination < self.station_count:
                raise ValueError("packet-batching route must advance through its DAG")
            if route.destination - route.source not in {1, 2}:
                raise ValueError("packet-batching advance support changed")
            if min(
                route.packet_increment,
                route.delay_increment,
                route.parity_scale,
            ) <= 0:
                raise ValueError("packet-batching descriptor changed")
            if not 0 < route.high_delay_probability < 1:
                raise ValueError("packet-batching probability changed")
        for station in range(self.station_count - 1):
            if not any(route.source == station for route in self.routes):
                raise ValueError("each packet-batching station requires a route")

    @property
    def goal_station(self) -> int:
        return self.station_count - 1

    def initial_distribution(self) -> tuple[tuple[Fraction, PacketBatchingState], ...]:
        return ((Fraction(1), PacketBatchingState(0, 0, 0, 0, 0)),)

    def actions(self, state: PacketBatchingState) -> tuple[PacketBatchingAction, ...]:
        self._validate_state(state)
        if state.status is not PacketBatchingStatus.ACTIVE:
            return ()
        return tuple(
            PacketBatchingAction(index)
            for index, route in enumerate(self.routes)
            if route.source == state.station
        )

    def step(
        self, state: PacketBatchingState, action: PacketBatchingAction
    ) -> tuple[Outcome[PacketBatchingState], ...]:
        self._validate_state(state)
        if action not in self.actions(state):
            raise ValueError("packet-batching action is not legal")
        route = self.routes[action.route]
        packets = state.packets + route.packet_increment
        parity = (
            state.parity
            + state.packets * route.parity_scale
            + route.packet_increment
        ) % self.parity_modulus
        steps = state.steps + 1
        outcomes = []
        for delay_delta, probability in (
            (0, 1 - route.high_delay_probability),
            (route.delay_increment, route.high_delay_probability),
        ):
            delay = state.delay + delay_delta
            if delay > self.delay_capacity or steps > self.step_limit:
                status = PacketBatchingStatus.FAILURE
            elif route.destination == self.goal_station:
                status = (
                    PacketBatchingStatus.SUCCESS
                    if packets == self.target_packets and parity == self.target_parity
                    else PacketBatchingStatus.FAILURE
                )
            else:
                status = PacketBatchingStatus.ACTIVE
            successor = PacketBatchingState(
                route.destination, packets, delay, parity, steps, status
            )
            outcomes.append(
                Outcome(
                    probability,
                    successor,
                    (),
                    failure=status is PacketBatchingStatus.FAILURE,
                    terminal=status is not PacketBatchingStatus.ACTIVE,
                )
            )
        return tuple(outcomes)

    def _validate_state(self, state: PacketBatchingState) -> None:
        if not 0 <= state.station < self.station_count:
            raise ValueError("packet-batching station changed")
        if min(state.packets, state.delay, state.steps) < 0:
            raise ValueError("packet-batching counter changed")
        if not 0 <= state.parity < self.parity_modulus:
            raise ValueError("packet-batching parity changed")


def select_seeded_packet_batching_outcome_v1(
    outcomes: tuple[Outcome[PacketBatchingState], ...],
    *,
    seed: int,
    episode_index: int,
    decision_index: int,
) -> tuple[Outcome[PacketBatchingState], str]:
    if not outcomes or sum((row.probability for row in outcomes), Fraction()) != 1:
        raise ValueError("packet-batching outcome distribution changed")
    tape = hashlib.sha256(
        b"acfqp:stochastic-packet-batching-outcome:v1\x00"
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
    raise AssertionError("packet-batching draw escaped a unit distribution")


def generate_stochastic_packet_batching(
    *, station_count: int, seed: int
) -> tuple[PacketBatchingKernel, PacketBatchingGenerationEvidence]:
    if station_count < 5:
        raise ValueError("packet-batching generator dimensions changed")
    rng = random.Random(seed)
    probabilities = (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4))
    packet_path = [1 + rng.randrange(4) for _ in range(station_count - 1)]
    delay_path = [1 + rng.randrange(3) for _ in range(station_count - 1)]
    parity_path = [2 + rng.randrange(5) for _ in range(station_count - 1)]
    routes: list[PacketBatchingRoute] = []
    path_old_indices = []
    for station in range(station_count - 1):
        path_old_indices.append(len(routes))
        routes.append(
            PacketBatchingRoute(
                station,
                station + 1,
                packet_path[station],
                delay_path[station],
                parity_path[station],
                (seed + station) % 3,
                probabilities[(seed + station) % len(probabilities)],
            )
        )
        if station + 2 < station_count:
            routes.append(
                PacketBatchingRoute(
                    station,
                    station + 2,
                    packet_path[station]
                    + packet_path[station + 1]
                    + 1
                    + ((seed + station) % 2),
                    delay_path[station] + 1,
                    parity_path[station] + 1,
                    (seed + station + 1) % 3,
                    probabilities[(seed + station + 1) % len(probabilities)],
                )
            )
    order = list(range(len(routes)))
    rng.shuffle(order)
    shuffled = tuple(routes[index] for index in order)
    old_to_new = {old: new for new, old in enumerate(order)}
    robust_path = tuple(old_to_new[index] for index in path_old_indices)
    parity_modulus = 17 + 2 * (seed % 3)
    target_packets = sum(packet_path)
    parity = packets = 0
    for packet_increment, parity_scale in zip(packet_path, parity_path):
        parity = (parity + packets * parity_scale + packet_increment) % parity_modulus
        packets += packet_increment
    kernel = PacketBatchingKernel(
        station_count=station_count,
        delay_capacity=sum(delay_path) + 2,
        target_packets=target_packets,
        target_parity=parity,
        parity_modulus=parity_modulus,
        step_limit=station_count + 2,
        routes=shuffled,
    )
    state = kernel.initial_distribution()[0][1]
    for route_index in robust_path:
        outcomes = kernel.step(state, PacketBatchingAction(route_index))
        state = max(outcomes, key=lambda row: row.next_state.delay).next_state
    if state.status is not PacketBatchingStatus.SUCCESS:
        raise AssertionError("generated packet-batching robust path changed")
    return kernel, PacketBatchingGenerationEvidence(seed, robust_path, True)


__all__ = (
    "PacketBatchingAction",
    "PacketBatchingGenerationEvidence",
    "PacketBatchingKernel",
    "PacketBatchingRoute",
    "PacketBatchingState",
    "PacketBatchingStatus",
    "generate_stochastic_packet_batching",
    "select_seeded_packet_batching_outcome_v1",
)
