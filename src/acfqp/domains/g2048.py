"""Canonical explicit-merge Generalized-2048 kernel."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from itertools import combinations, product
from typing import ClassVar, Iterable, Mapping

from acfqp.core import Outcome, QuerySpec


class G2048Status(str, Enum):
    ACTIVE = "active"
    FAILURE = "failure"


@dataclass(frozen=True, order=True, slots=True)
class G2048State:
    """A row-major board plus its absorbing-status bit."""

    board: tuple[int, ...]
    status: G2048Status = G2048Status.ACTIVE


@dataclass(frozen=True, order=True, slots=True)
class G2048Action:
    """Merge an unordered adjacent pair and retain the tile at ``survivor``."""

    first: int
    second: int
    survivor: int

    def __post_init__(self) -> None:
        if self.first >= self.second:
            raise ValueError("action pair must be stored in increasing cell order")
        if self.survivor not in (self.first, self.second):
            raise ValueError("survivor must be one of the merged cells")


class D4Transform(str, Enum):
    """The fixed, deterministic square-dihedral transform order."""

    IDENTITY = "identity"
    ROTATE_90 = "rotate_90"
    ROTATE_180 = "rotate_180"
    ROTATE_270 = "rotate_270"
    REFLECT = "reflect"
    REFLECT_ROTATE_90 = "reflect_rotate_90"
    REFLECT_ROTATE_180 = "reflect_rotate_180"
    REFLECT_ROTATE_270 = "reflect_rotate_270"


D4_ELEMENTS: tuple[D4Transform, ...] = tuple(D4Transform)


def _transform_parameters(transform: D4Transform) -> tuple[bool, int]:
    selected = D4Transform(transform)
    return {
        D4Transform.IDENTITY: (False, 0),
        D4Transform.ROTATE_90: (False, 1),
        D4Transform.ROTATE_180: (False, 2),
        D4Transform.ROTATE_270: (False, 3),
        D4Transform.REFLECT: (True, 0),
        D4Transform.REFLECT_ROTATE_90: (True, 1),
        D4Transform.REFLECT_ROTATE_180: (True, 2),
        D4Transform.REFLECT_ROTATE_270: (True, 3),
    }[selected]


def transform_cell(cell: int, size: int, transform: D4Transform) -> int:
    """Map one row-major cell under a D4 element.

    Reflected elements apply a left-right reflection first and then the named
    clockwise rotation.  This convention fixes composition and serialized
    transform IDs without affecting the represented group action.
    """

    if size < 2:
        raise ValueError("D4 transforms require a square of size at least two")
    if cell < 0 or cell >= size * size:
        raise ValueError("cell lies outside the square")
    reflected, rotations = _transform_parameters(transform)
    row, column = divmod(cell, size)
    if reflected:
        column = size - 1 - column
    for _ in range(rotations):
        row, column = column, size - 1 - row
    return row * size + column


def transform_board(
    board: tuple[int, ...], size: int, transform: D4Transform
) -> tuple[int, ...]:
    """Transform a row-major square board without changing tile ranks."""

    if len(board) != size * size:
        raise ValueError("board length does not match square size")
    transformed = [0] * len(board)
    for source, rank in enumerate(board):
        transformed[transform_cell(source, size, transform)] = rank
    return tuple(transformed)


def transform_state(
    state: G2048State, transform: D4Transform, size: int = 2
) -> G2048State:
    """Apply a D4 element to a state, preserving its absorbing status."""

    return G2048State(transform_board(state.board, size, transform), state.status)


def transform_action(
    action: G2048Action, transform: D4Transform, size: int = 2
) -> G2048Action:
    """Apply the same D4 element to pair endpoints and the survivor cell."""

    first_image = transform_cell(action.first, size, transform)
    second_image = transform_cell(action.second, size, transform)
    survivor_image = transform_cell(action.survivor, size, transform)
    first, second = sorted((first_image, second_image))
    return G2048Action(first, second, survivor_image)


def transform_outcome(
    outcome: Outcome[G2048State], transform: D4Transform, size: int = 2
) -> Outcome[G2048State]:
    """Transport one exact kernel outcome through a board automorphism."""

    return Outcome(
        outcome.probability,
        transform_state(outcome.next_state, transform, size),
        outcome.reward_features,
        failure=outcome.failure,
        terminal=outcome.terminal,
    )


def compose_d4(
    left: D4Transform, right: D4Transform
) -> D4Transform:
    """Return ``left`` after ``right`` under the fixed transform convention."""

    target = tuple(
        transform_cell(transform_cell(cell, 3, right), 3, left)
        for cell in range(9)
    )
    for candidate in D4_ELEMENTS:
        if tuple(transform_cell(cell, 3, candidate) for cell in range(9)) == target:
            return candidate
    raise AssertionError("D4 composition left the registered group")


def inverse_d4(transform: D4Transform) -> D4Transform:
    """Return the unique inverse D4 element."""

    selected = D4Transform(transform)
    for candidate in D4_ELEMENTS:
        if (
            compose_d4(candidate, selected) is D4Transform.IDENTITY
            and compose_d4(selected, candidate) is D4Transform.IDENTITY
        ):
            return candidate
    raise AssertionError("D4 element has no inverse")


def orbit(state: G2048State, size: int = 2) -> tuple[G2048State, ...]:
    """Return unique D4 images in canonical state order.

    Images are first enumerated in ``D4_ELEMENTS`` order and deduplicated by
    insertion order; only that ordered sequence is then canonically sorted.
    No set iteration determines artifact order.
    """

    images: list[G2048State] = []
    seen: set[G2048State] = set()
    for transform in D4_ELEMENTS:
        image = transform_state(state, transform, size)
        if image not in seen:
            seen.add(image)
            images.append(image)
    return tuple(sorted(images, key=lambda image: (image.board, image.status.value)))


def stabilizer(
    state: G2048State, size: int = 2
) -> tuple[D4Transform, ...]:
    """Return the state stabilizer in the fixed D4 element order."""

    return tuple(
        transform
        for transform in D4_ELEMENTS
        if transform_state(state, transform, size) == state
    )


def canonicalize_state(
    state: G2048State, size: int = 2
) -> tuple[G2048State, D4Transform]:
    """Return the canonical orbit representative and a transform reaching it."""

    indexed = tuple(
        (transform_state(state, transform, size), index, transform)
        for index, transform in enumerate(D4_ELEMENTS)
    )
    representative, _, transform = min(
        indexed,
        key=lambda item: (item[0].board, item[0].status.value, item[1]),
    )
    return representative, transform


def canonicalize_state_action(
    state: G2048State,
    action: G2048Action,
    size: int = 2,
) -> tuple[G2048State, G2048Action, D4Transform]:
    """Canonicalize a state-action pair, resolving state stabilizers by action."""

    candidates = tuple(
        (
            transform_state(state, transform, size),
            transform_action(action, transform, size),
            index,
            transform,
        )
        for index, transform in enumerate(D4_ELEMENTS)
    )
    canonical_state, canonical_action, _, transform = min(
        candidates,
        key=lambda item: (
            item[0].board,
            item[0].status.value,
            item[1].first,
            item[1].second,
            item[1].survivor,
            item[2],
        ),
    )
    return canonical_state, canonical_action, transform


# Explicit aliases make the symmetry scope clear at call sites while retaining
# the compact stable helper names requested by fixture runners.
d4_orbit = orbit
d4_stabilizer = stabilizer
canonicalize_d4_state = canonicalize_state
canonicalize_d4_state_action = canonicalize_state_action


@dataclass(frozen=True, slots=True)
class G2048Kernel:
    """Finite exact G2048-Select dynamics.

    The two normative configurations are selected by ``size``.  Spawn
    probabilities are represented exactly as decimal rationals.
    """

    size: int = 2

    def __post_init__(self) -> None:
        if self.size not in (2, 3):
            raise ValueError("V0 G2048 size must be 2 or 3")

    @property
    def rank_cap(self) -> int:
        return 6 if self.size == 2 else 8

    @property
    def horizon(self) -> int:
        return 6 if self.size == 2 else 8

    @property
    def registered_reward_features(self) -> tuple[str, ...]:
        return ("merge",)

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
        coefficient = Fraction(raw_weights.get("merge", 0))
        if coefficient < 0:
            raise ValueError("registered reward weights must be nonnegative")
        return horizon * coefficient

    @property
    def spawn_distribution(self) -> tuple[tuple[int, Fraction], ...]:
        if self.size == 2:
            return ((1, Fraction(9, 10)), (2, Fraction(1, 10)))
        return (
            (1, Fraction(4, 5)),
            (2, Fraction(3, 20)),
            (3, Fraction(1, 20)),
        )

    @property
    def cell_count(self) -> int:
        return self.size * self.size

    def _adjacent(self, first: int, second: int) -> bool:
        row_a, col_a = divmod(first, self.size)
        row_b, col_b = divmod(second, self.size)
        return abs(row_a - row_b) + abs(col_a - col_b) == 1

    def _validate_state(self, state: G2048State) -> None:
        if len(state.board) != self.cell_count:
            raise ValueError("board size does not match kernel size")
        if any(rank < 0 or rank > self.rank_cap for rank in state.board):
            raise ValueError("board contains a rank outside [0, R]")

    def initial_distribution(self) -> tuple[tuple[Fraction, G2048State], ...]:
        """Conditional law after resampling two-tile boards with no merge."""

        candidates: list[tuple[Fraction, G2048State]] = []
        for first, second in combinations(range(self.cell_count), 2):
            cell_probability = Fraction(1, self.cell_count * (self.cell_count - 1) // 2)
            for (rank_a, p_a), (rank_b, p_b) in product(
                self.spawn_distribution, repeat=2
            ):
                board = [0] * self.cell_count
                board[first] = rank_a
                board[second] = rank_b
                state = G2048State(tuple(board))
                if self.actions(state):
                    candidates.append((cell_probability * p_a * p_b, state))

        accepted_mass = sum((p for p, _ in candidates), Fraction(0))
        if accepted_mass == 0:  # defensive: impossible for the normative grids
            raise RuntimeError("initial-state rejection sampler has zero acceptance mass")
        normalized = tuple((p / accepted_mass, state) for p, state in candidates)
        if sum((p for p, _ in normalized), Fraction(0)) != 1:
            raise AssertionError("internal error: initial distribution is not normalized")
        return normalized

    def actions(self, state: G2048State) -> tuple[G2048Action, ...]:
        self._validate_state(state)
        if state.status is not G2048Status.ACTIVE:
            return ()
        result: list[G2048Action] = []
        for first, second in combinations(range(self.cell_count), 2):
            if not self._adjacent(first, second):
                continue
            rank = state.board[first]
            if rank != 0 and rank == state.board[second]:
                result.append(G2048Action(first, second, first))
                result.append(G2048Action(first, second, second))
        return tuple(result)

    def step(
        self, state: G2048State, action: G2048Action
    ) -> tuple[Outcome[G2048State], ...]:
        self._validate_state(state)
        if action not in self.actions(state):
            raise ValueError("action is not legal in this G2048 state")

        rank = state.board[action.first]
        board_after_merge = list(state.board)
        board_after_merge[action.first] = 0
        board_after_merge[action.second] = 0
        board_after_merge[action.survivor] = min(rank + 1, self.rank_cap)
        empty_cells = tuple(i for i, value in enumerate(board_after_merge) if value == 0)
        if not empty_cells:  # merging two cells always creates an empty cell
            raise AssertionError("G2048 merge unexpectedly left no empty cell")

        reward = Fraction(2 ** (rank + 1), 2 ** (self.rank_cap + 1))
        outcomes: list[Outcome[G2048State]] = []
        cell_probability = Fraction(1, len(empty_cells))
        for cell in empty_cells:
            for spawn_rank, rank_probability in self.spawn_distribution:
                next_board = board_after_merge.copy()
                next_board[cell] = spawn_rank
                provisional = G2048State(tuple(next_board))
                failed = not self.actions(provisional)
                next_state = G2048State(
                    provisional.board,
                    G2048Status.FAILURE if failed else G2048Status.ACTIVE,
                )
                outcomes.append(
                    Outcome(
                        cell_probability * rank_probability,
                        next_state,
                        (("merge", reward),),
                        failure=failed,
                        terminal=failed,
                    )
                )

        if sum((outcome.probability for outcome in outcomes), Fraction(0)) != 1:
            raise AssertionError("internal error: G2048 outcome mass is not one")
        return tuple(outcomes)

    def is_terminal(self, state: G2048State) -> bool:
        self._validate_state(state)
        return state.status is G2048Status.FAILURE


SAFE_CHAIN_STRUCTURAL_KEY = "g2048_select_safe_chain_2x2_v0"
SAFE_CHAIN_QUERY_NAME = "safe_chain_d4_uniform_h2"
SAFE_CHAIN_BASE_STATE = G2048State((1, 1, 2, 0))


@dataclass(frozen=True, slots=True)
class G2048SafeChainKernel(G2048Kernel):
    """The separately keyed feasible 2x2 safe-chain dynamics.

    Its default initial distribution is only a named query-fixture default;
    ``structural_key()`` deliberately excludes it, the query horizon, reward
    coefficients, and risk threshold.
    """

    size: int = 2

    fixture_key: ClassVar[str] = SAFE_CHAIN_STRUCTURAL_KEY
    display_name: ClassVar[str] = "G2048-Select Safe-Chain 2×2"
    evaluation_role: ClassVar[str] = (
        "nontrivial_safe_planning_and_quotient_certificate"
    )

    def __post_init__(self) -> None:
        if self.size != 2:
            raise ValueError("the V0 safe-chain fixture is fixed to a 2x2 board")

    @property
    def spawn_distribution(self) -> tuple[tuple[int, Fraction], ...]:
        return ((1, Fraction(99, 100)), (2, Fraction(1, 100)))

    def structural_key(self) -> dict[str, object]:
        """Return every transition-semantic field and no query-owned field."""

        return {
            "fixture_key": self.fixture_key,
            "board_size": self.size,
            "rank_cap": self.rank_cap,
            "horizon_max": self.horizon,
            "adjacency": "orthogonal",
            "action": "one_adjacent_equal_pair_with_chosen_survivor",
            "merge_rank": "min(j+1,rank_cap)",
            "merge_count_per_step": 1,
            "spawn_timing": "after_merge",
            "spawn_count": 1,
            "spawn_distribution": self.spawn_distribution,
            "spawn_position": "uniform_over_empty_cells",
            "failure_rule": "absorbing_if_no_legal_merge_after_spawn",
            "failure_before_horizon_truncation": True,
        }

    def canonical_query_distribution(
        self, name: str = SAFE_CHAIN_QUERY_NAME
    ) -> tuple[tuple[Fraction, G2048State], ...]:
        """Return the registered query-owned uniform D4 orbit law."""

        if name not in {SAFE_CHAIN_QUERY_NAME, self.fixture_key, "canonical"}:
            raise ValueError(f"unknown safe-chain query distribution: {name!r}")
        states = orbit(SAFE_CHAIN_BASE_STATE, self.size)
        if len(states) != 8:
            raise AssertionError("safe-chain base board must have an eight-state D4 orbit")
        return tuple((Fraction(1, 8), state) for state in states)

    def validate_query_distribution(
        self, distribution: Iterable[tuple[Fraction, G2048State]]
    ) -> None:
        """Validate exact mass, unique states, and structural compatibility."""

        records = tuple((Fraction(probability), state) for probability, state in distribution)
        if not records:
            raise ValueError("query distribution must not be empty")
        if any(probability <= 0 for probability, _ in records):
            raise ValueError("query probabilities must be positive")
        if sum((probability for probability, _ in records), Fraction(0)) != 1:
            raise ValueError("query distribution mass must be one")
        states = [state for _, state in records]
        if len(states) != len(set(states)):
            raise ValueError("query distribution contains a duplicate state")
        for state in states:
            self._validate_state(state)

    def initial_distribution(self) -> tuple[tuple[Fraction, G2048State], ...]:
        """Return the named default used when a generic caller omits ``rho0``."""

        return self.canonical_query_distribution()


def safe_chain_kernel() -> G2048SafeChainKernel:
    """Construct the frozen safe-chain structural kernel."""

    return G2048SafeChainKernel()


def safe_chain_query(
    kernel: G2048SafeChainKernel | None = None,
    *,
    initial_distribution: Iterable[tuple[Fraction, G2048State]] | None = None,
) -> QuerySpec[G2048State]:
    """Construct the canonical query with query-owned, canonically ordered rho0."""

    selected_kernel = safe_chain_kernel() if kernel is None else kernel
    if not isinstance(selected_kernel, G2048SafeChainKernel):
        raise TypeError("safe_chain_query requires G2048SafeChainKernel")
    raw_distribution = (
        selected_kernel.canonical_query_distribution()
        if initial_distribution is None
        else tuple(initial_distribution)
    )
    selected_kernel.validate_query_distribution(raw_distribution)
    distribution = tuple(
        sorted(
            ((Fraction(probability), state) for probability, state in raw_distribution),
            key=lambda item: (item[1].board, item[1].status.value),
        )
    )
    return QuerySpec(
        initial_distribution=distribution,
        horizon=2,
        reward_weights=(("merge", Fraction(1)),),
        goal="default",
        delta=Fraction(1, 20),
        normalizer=Fraction(2),
        normalizer_proof_id="g2048.canonical.merge_le_1_per_step.total_le_h.v1",
    )


def safe_chain_fixture() -> tuple[G2048SafeChainKernel, QuerySpec[G2048State]]:
    """Return the frozen structural kernel and its separate canonical query."""

    kernel = safe_chain_kernel()
    return kernel, safe_chain_query(kernel)
