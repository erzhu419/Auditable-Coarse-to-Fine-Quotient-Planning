"""Canonical Layered Matching Buffer (LMB) kernel and instance generator."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import random
from typing import Mapping

from acfqp.core import Outcome


class LMBStatus(str, Enum):
    ACTIVE = "active"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, order=True, slots=True)
class LMBState:
    """Removed-tile bit mask, per-type buffer counts, and terminal status."""

    removed_mask: int
    buffer: tuple[int, ...]
    status: LMBStatus = LMBStatus.ACTIVE


@dataclass(frozen=True, order=True, slots=True)
class LMBAction:
    tile: int


@dataclass(frozen=True, slots=True)
class LMBGenerationEvidence:
    """Private construction evidence; planners receive only the kernel."""

    seed: int
    target_sequence: tuple[int, ...]
    layers: tuple[int, ...]
    verified: bool


@dataclass(frozen=True, slots=True)
class LMBKernel:
    """A fully observed deterministic matching-buffer instance."""

    tile_types: tuple[int, ...]
    blockers: tuple[frozenset[int], ...]
    type_count: int
    capacity: int
    max_layers: int

    def __post_init__(self) -> None:
        tile_count = len(self.tile_types)
        if tile_count == 0 or tile_count % 3:
            raise ValueError("LMB tile count must be a positive multiple of three")
        if len(self.blockers) != tile_count:
            raise ValueError("one blocker set is required per tile")
        if self.type_count <= 0:
            raise ValueError("type_count must be positive")
        if self.capacity < 0:
            raise ValueError("capacity must be nonnegative")
        if self.max_layers <= 0:
            raise ValueError("max_layers must be positive")
        if any(tile_type < 0 or tile_type >= self.type_count for tile_type in self.tile_types):
            raise ValueError("tile type lies outside [0, type_count)")
        all_tiles = set(range(tile_count))
        for tile, blocker_set in enumerate(self.blockers):
            if tile in blocker_set or not blocker_set <= all_tiles:
                raise ValueError("blocker sets must contain valid other tile IDs")
        self._validate_dag_depth()

    @property
    def tile_count(self) -> int:
        return len(self.tile_types)

    @property
    def horizon(self) -> int:
        return self.tile_count

    @property
    def registered_reward_features(self) -> tuple[str, ...]:
        return ("match", "terminal_clear")

    @property
    def registered_goals(self) -> tuple[str, ...]:
        return ("default",)

    def reward_upper_bound(
        self,
        horizon: int,
        raw_weights: Mapping[str, Fraction],
        goal: str,
    ) -> Fraction:
        if goal not in self.registered_goals:
            raise ValueError(f"unregistered goal: {goal!r}")
        match_weight = Fraction(raw_weights.get("match", 0))
        clear_weight = Fraction(raw_weights.get("terminal_clear", 0))
        if match_weight < 0 or clear_weight < 0:
            raise ValueError("registered reward weights must be nonnegative")
        # Queries may start from any registered reachable state, including a
        # buffer with several counts already at two and a nearly empty board.
        # Therefore one match per remaining step and a clear on any positive
        # horizon are the safe reusable-model bounds.  The total number of
        # triples can never exceed N/3.
        match_count = min(self.tile_count // 3, horizon)
        clear_available = horizon > 0
        return (
            match_weight * match_count
            + clear_weight * self.clear_bonus * int(clear_available)
        )

    @property
    def clear_bonus(self) -> Fraction:
        return Fraction(self.tile_count, 3)

    def _validate_dag_depth(self) -> None:
        visiting: set[int] = set()
        depth_cache: dict[int, int] = {}

        def depth(tile: int) -> int:
            if tile in visiting:
                raise ValueError("blocker graph must be acyclic")
            if tile in depth_cache:
                return depth_cache[tile]
            visiting.add(tile)
            value = 1 + max((depth(blocker) for blocker in self.blockers[tile]), default=-1)
            visiting.remove(tile)
            depth_cache[tile] = value
            return value

        actual_layers = max(depth(tile) for tile in range(self.tile_count)) + 1
        if actual_layers > self.max_layers:
            raise ValueError(
                f"blocker graph uses {actual_layers} layers, exceeding {self.max_layers}"
            )

    def initial_distribution(self) -> tuple[tuple[Fraction, LMBState], ...]:
        return ((Fraction(1), LMBState(0, (0,) * self.type_count)),)

    def _validate_state(self, state: LMBState) -> None:
        if state.removed_mask < 0 or state.removed_mask >> self.tile_count:
            raise ValueError("removed-mask contains nonexistent tiles")
        if len(state.buffer) != self.type_count or any(count < 0 or count >= 3 for count in state.buffer):
            raise ValueError("buffer must contain per-type counts in {0,1,2}")

    def actions(self, state: LMBState) -> tuple[LMBAction, ...]:
        self._validate_state(state)
        if state.status is not LMBStatus.ACTIVE:
            return ()
        result: list[LMBAction] = []
        for tile, blocker_set in enumerate(self.blockers):
            if state.removed_mask & (1 << tile):
                continue
            if all(state.removed_mask & (1 << blocker) for blocker in blocker_set):
                result.append(LMBAction(tile))
        return tuple(result)

    def step(self, state: LMBState, action: LMBAction) -> tuple[Outcome[LMBState], ...]:
        self._validate_state(state)
        if action not in self.actions(state):
            raise ValueError("action is not eligible in this LMB state")

        removed_mask = state.removed_mask | (1 << action.tile)
        tile_type = self.tile_types[action.tile]
        buffer = list(state.buffer)
        buffer[tile_type] += 1
        matched = buffer[tile_type] == 3
        if matched:
            buffer[tile_type] = 0

        occupancy = sum(buffer)
        board_empty = removed_mask == (1 << self.tile_count) - 1
        if occupancy > self.capacity:
            status = LMBStatus.FAILURE
        elif board_empty:
            status = LMBStatus.SUCCESS
        else:
            status = LMBStatus.ACTIVE

        features: list[tuple[str, Fraction]] = []
        if matched:
            features.append(("match", Fraction(1)))
        if status is LMBStatus.SUCCESS:
            features.append(("terminal_clear", self.clear_bonus))
        failed = status is LMBStatus.FAILURE
        return (
            Outcome(
                Fraction(1),
                LMBState(removed_mask, tuple(buffer), status),
                tuple(features),
                failure=failed,
                terminal=status is not LMBStatus.ACTIVE,
            ),
        )

    def is_terminal(self, state: LMBState) -> bool:
        self._validate_state(state)
        return state.status is not LMBStatus.ACTIVE


def _randomized_target_types(
    counts: tuple[int, ...], capacity: int, rng: random.Random
) -> tuple[int, ...] | None:
    """Randomized backtracking under authoritative buffer semantics."""

    type_count = len(counts)

    def search(
        remaining: tuple[int, ...], buffer: tuple[int, ...], prefix: tuple[int, ...]
    ) -> tuple[int, ...] | None:
        if not any(remaining):
            return prefix if not any(buffer) else None

        candidates = [tile_type for tile_type, count in enumerate(remaining) if count]
        rng.shuffle(candidates)
        for tile_type in candidates:
            next_remaining = list(remaining)
            next_remaining[tile_type] -= 1
            next_buffer = list(buffer)
            next_buffer[tile_type] += 1
            if next_buffer[tile_type] == 3:
                next_buffer[tile_type] = 0
            if sum(next_buffer) > capacity:
                continue
            # Necessary and sufficient here: each buffered partial triple can
            # still be completed by the remaining copies of its type.
            if any(
                (next_buffer[t] + next_remaining[t]) % 3
                for t in range(type_count)
            ):
                continue
            result = search(
                tuple(next_remaining), tuple(next_buffer), prefix + (tile_type,)
            )
            if result is not None:
                return result
        return None

    return search(counts, (0,) * type_count, ())


def generate_solvable_lmb(
    *,
    tile_count: int,
    type_count: int,
    capacity: int,
    max_layers: int,
    seed: int,
) -> tuple[LMBKernel, LMBGenerationEvidence]:
    """Generate a reverse-constructed, authoritatively verified LMB instance.

    Each used type occurs a positive multiple of three.  Tile IDs are shuffled
    independently of target position, and the returned kernel carries no
    target sequence, so the construction witness is not leaked to a planner.
    """

    if tile_count <= 0 or tile_count % 3:
        raise ValueError("tile_count must be a positive multiple of three")
    if type_count <= 0 or type_count > tile_count // 3:
        raise ValueError("type_count must lie in [1, tile_count / 3]")
    if capacity < 0 or max_layers <= 0:
        raise ValueError("capacity must be nonnegative and max_layers positive")

    rng = random.Random(seed)
    triple_groups = tile_count // 3
    group_counts = [1] * type_count
    for _ in range(triple_groups - type_count):
        group_counts[rng.randrange(type_count)] += 1
    counts = tuple(3 * groups for groups in group_counts)

    target_types = _randomized_target_types(counts, capacity, rng)
    if target_types is None:
        raise ValueError("no capacity-feasible target sequence exists")

    target_sequence_list = list(range(tile_count))
    rng.shuffle(target_sequence_list)
    target_sequence = tuple(target_sequence_list)

    layers_by_position: list[int] = []
    blockers_by_position: list[frozenset[int]] = []
    for position in range(tile_count):
        largest_layer = min(max_layers - 1, position)
        layer = rng.randrange(largest_layer + 1) if largest_layer else 0
        shallower = [
            prior
            for prior in range(position)
            if layers_by_position[prior] < layer
        ]
        if layer > 0 and not shallower:
            layer = 0
        if layer == 0:
            blocker_set: frozenset[int] = frozenset()
        else:
            blocker_count = min(len(shallower), rng.choice((1, 2)))
            blocker_set = frozenset(rng.sample(shallower, blocker_count))
        layers_by_position.append(layer)
        blockers_by_position.append(blocker_set)

    tile_types_by_id = [0] * tile_count
    blockers_by_id: list[frozenset[int]] = [frozenset() for _ in range(tile_count)]
    layers_by_id = [0] * tile_count
    for position, tile_id in enumerate(target_sequence):
        tile_types_by_id[tile_id] = target_types[position]
        blockers_by_id[tile_id] = frozenset(
            target_sequence[blocker_position]
            for blocker_position in blockers_by_position[position]
        )
        layers_by_id[tile_id] = layers_by_position[position]

    kernel = LMBKernel(
        tile_types=tuple(tile_types_by_id),
        blockers=tuple(blockers_by_id),
        type_count=type_count,
        capacity=capacity,
        max_layers=max_layers,
    )

    state = kernel.initial_distribution()[0][1]
    verified = True
    try:
        for tile in target_sequence:
            action = LMBAction(tile)
            if action not in kernel.actions(state):
                verified = False
                break
            state = kernel.step(state, action)[0].next_state
            if state.status is LMBStatus.FAILURE:
                verified = False
                break
        verified = verified and state.status is LMBStatus.SUCCESS and not any(state.buffer)
    except (AssertionError, ValueError):
        verified = False
    if not verified:
        raise AssertionError("reverse-constructed target failed authoritative simulation")

    return kernel, LMBGenerationEvidence(seed, target_sequence, tuple(layers_by_id), True)
