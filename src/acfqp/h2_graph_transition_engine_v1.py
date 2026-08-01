"""Profile-neutral exact H=2 graph transition engine.

This module contains no campaign, anchor, observer, source-prior, or target
identity authority.  It is a pure arithmetic core shared by separately
domain-separated campaign adapters.  In particular, callers must derive and
bind their own tape namespace before passing a seed-domain and pairing-group
identity to :func:`derive_splitmix64_seed_v1`.

The engine preserves the registered graph-merge semantics:

* one adjacent equal-rank pair is merged;
* the survivor is one endpoint of that pair;
* one rank is spawned uniformly over post-merge empty vertices;
* failure is checked after the spawn and before horizon truncation; and
* all probabilities and rewards use exact :class:`fractions.Fraction`.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import math
from typing import Iterable

from acfqp import (
    construction_accounting_owned_runtime_v1 as accounting_runtime,
)
from acfqp.phase3e_ids import parse_content_id
from acfqp.relational_graph_core_v1 import GraphTopologyV1


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "h2_graph_transition_engine_v1"

_UINT64_MODULUS = 1 << 64
_UINT64_MASK = _UINT64_MODULUS - 1
_SPLITMIX_GAMMA = 0x9E3779B97F4A7C15


class H2GraphTransitionInvariantViolation(ValueError):
    """A pure graph state, action, law, seed, or transition is invalid."""


def _cid(value: object, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise H2GraphTransitionInvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        ) from error


def _fraction(value: object, field: str) -> Fraction:
    if type(value) is not Fraction:
        raise H2GraphTransitionInvariantViolation(
            f"{field} must use exact Fraction arithmetic"
        )
    return value


@dataclass(frozen=True, slots=True)
class H2GraphStateV1:
    ranks: tuple[int, ...]
    failure: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.ranks) is not tuple
            or not self.ranks
            or any(type(rank) is not int or rank < 0 for rank in self.ranks)
            or type(self.failure) is not bool
        ):
            raise H2GraphTransitionInvariantViolation(
                "graph state must contain nonnegative integer ranks"
            )


@dataclass(frozen=True, slots=True, order=True)
class H2GraphActionV1:
    first: int
    second: int
    survivor: int

    def __post_init__(self) -> None:
        if (
            type(self.first) is not int
            or type(self.second) is not int
            or type(self.survivor) is not int
            or self.first < 0
            or self.second < 0
            or self.first >= self.second
            or self.survivor not in (self.first, self.second)
        ):
            raise H2GraphTransitionInvariantViolation(
                "graph action must be one ordered edge and endpoint survivor"
            )

    @property
    def triple(self) -> tuple[int, int, int]:
        return (self.first, self.second, self.survivor)


@dataclass(frozen=True, slots=True)
class H2GraphTransitionAtomV1:
    next_state: H2GraphStateV1
    probability: Fraction
    realized_row_reward: Fraction
    failure: bool
    terminal: bool
    spawn_cell: int
    spawn_rank: int

    def __post_init__(self) -> None:
        if (
            type(self.next_state) is not H2GraphStateV1
            or type(self.probability) is not Fraction
            or not 0 < self.probability <= 1
            or type(self.realized_row_reward) is not Fraction
            or not 0 <= self.realized_row_reward <= 1
            or type(self.failure) is not bool
            or self.failure != self.next_state.failure
            or type(self.terminal) is not bool
            or type(self.spawn_cell) is not int
            or self.spawn_cell < 0
            or type(self.spawn_rank) is not int
            or self.spawn_rank <= 0
        ):
            raise H2GraphTransitionInvariantViolation(
                "exact transition atom is malformed"
            )


@dataclass(frozen=True, slots=True)
class H2GraphSampleV1:
    next_state: H2GraphStateV1
    realized_row_reward: Fraction
    failure: bool
    terminal: bool
    spawn_cell: int
    spawn_rank: int
    accepted_draw_index: int
    random_word_start_index: int
    random_words: tuple[int, ...]

    def __post_init__(self) -> None:
        if (
            type(self.next_state) is not H2GraphStateV1
            or type(self.realized_row_reward) is not Fraction
            or type(self.failure) is not bool
            or self.failure != self.next_state.failure
            or type(self.terminal) is not bool
            or type(self.spawn_cell) is not int
            or type(self.spawn_rank) is not int
            or type(self.accepted_draw_index) is not int
            or self.accepted_draw_index <= 0
            or type(self.random_word_start_index) is not int
            or self.random_word_start_index <= 0
            or type(self.random_words) is not tuple
            or not self.random_words
            or any(
                type(word) is not int
                or not 0 <= word < _UINT64_MODULUS
                for word in self.random_words
            )
        ):
            raise H2GraphTransitionInvariantViolation(
                "deterministic graph sample is malformed"
            )

    @property
    def random_word_count(self) -> int:
        return len(self.random_words)

    @property
    def rejection_count(self) -> int:
        return len(self.random_words) - 1


def _canonical_spawn_law(
    value: Iterable[tuple[int, Fraction]],
) -> tuple[tuple[int, Fraction], ...]:
    try:
        law = tuple(value)
    except TypeError as error:
        raise H2GraphTransitionInvariantViolation(
            "spawn law must be one concrete exact sequence"
        ) from error
    if (
        not law
        or tuple(rank for rank, _ in law)
        != tuple(sorted({rank for rank, _ in law}))
        or any(
            type(rank) is not int
            or rank <= 0
            or type(probability) is not Fraction
            or probability <= 0
            for rank, probability in law
        )
        or sum((probability for _, probability in law), Fraction(0)) != 1
    ):
        raise H2GraphTransitionInvariantViolation(
            "spawn law must be sorted, unique, positive, and normalized"
        )
    return law


@dataclass(frozen=True, slots=True)
class H2GraphKernelV1:
    topology: GraphTopologyV1
    rank_cap: int
    horizon: int
    spawn_law: tuple[tuple[int, Fraction], ...]

    def __post_init__(self) -> None:
        if (
            type(self.topology) is not GraphTopologyV1
            or type(self.rank_cap) is not int
            or self.rank_cap <= 0
            or type(self.horizon) is not int
            or self.horizon != 2
        ):
            raise H2GraphTransitionInvariantViolation(
                "H2 graph kernel geometry or cap is invalid"
            )
        canonical = _canonical_spawn_law(self.spawn_law)
        if canonical != self.spawn_law:
            raise H2GraphTransitionInvariantViolation(
                "spawn law is not in canonical tuple form"
            )
        if any(rank > self.rank_cap for rank, _ in canonical):
            raise H2GraphTransitionInvariantViolation(
                "spawn rank exceeds the registered rank cap"
            )

    def validate_state(self, state: H2GraphStateV1) -> H2GraphStateV1:
        if (
            type(state) is not H2GraphStateV1
            or len(state.ranks) != self.topology.vertex_count
            or any(rank > self.rank_cap for rank in state.ranks)
        ):
            raise H2GraphTransitionInvariantViolation(
                "state is outside the graph kernel"
            )
        expected_failure = not self.legal_actions_from_ranks(
            state.ranks,
            failure=False,
        )
        if state.failure != expected_failure:
            raise H2GraphTransitionInvariantViolation(
                "state failure flag disagrees with legal actions"
            )
        return state

    def legal_actions_from_ranks(
        self,
        ranks: tuple[int, ...],
        *,
        failure: bool,
    ) -> tuple[H2GraphActionV1, ...]:
        if (
            type(ranks) is not tuple
            or len(ranks) != self.topology.vertex_count
            or any(
                type(rank) is not int
                or rank < 0
                or rank > self.rank_cap
                for rank in ranks
            )
            or type(failure) is not bool
        ):
            raise H2GraphTransitionInvariantViolation(
                "legal-action query is outside the graph kernel"
            )
        if failure:
            return ()
        return tuple(
            H2GraphActionV1(first, second, survivor)
            for first, second in self.topology.edges
            if ranks[first] > 0 and ranks[first] == ranks[second]
            for survivor in (first, second)
        )

    def legal_actions(
        self,
        state: H2GraphStateV1,
    ) -> tuple[H2GraphActionV1, ...]:
        self.validate_state(state)
        return self.legal_actions_from_ranks(
            state.ranks,
            failure=state.failure,
        )

    def merge(
        self,
        state: H2GraphStateV1,
        action: H2GraphActionV1,
    ) -> tuple[tuple[int, ...], tuple[int, ...], Fraction]:
        canonical_state = self.validate_state(state)
        if (
            type(action) is not H2GraphActionV1
            or action not in self.legal_actions(canonical_state)
        ):
            raise H2GraphTransitionInvariantViolation(
                "transition action is not legal at its source state"
            )
        rank = canonical_state.ranks[action.first]
        board = list(canonical_state.ranks)
        board[action.first] = 0
        board[action.second] = 0
        board[action.survivor] = min(rank + 1, self.rank_cap)
        empty = tuple(index for index, value in enumerate(board) if value == 0)
        if not empty:
            raise H2GraphTransitionInvariantViolation(
                "registered merge produced no spawn location"
            )
        reward = (
            Fraction(2 ** (rank + 1), 2 ** (self.rank_cap + 1))
            / self.horizon
        )
        return tuple(board), empty, reward

    def exact_atoms(
        self,
        state: H2GraphStateV1,
        action: H2GraphActionV1,
        *,
        remaining_horizon: int,
    ) -> tuple[H2GraphTransitionAtomV1, ...]:
        if (
            type(remaining_horizon) is not int
            or remaining_horizon not in (1, self.horizon)
        ):
            raise H2GraphTransitionInvariantViolation(
                "remaining horizon is outside the H=2 kernel"
            )
        board, empty, reward = self.merge(state, action)
        atoms: list[H2GraphTransitionAtomV1] = []
        for cell in empty:
            for rank, rank_probability in self.spawn_law:
                successor = list(board)
                successor[cell] = rank
                successor_ranks = tuple(successor)
                failure = not self.legal_actions_from_ranks(
                    successor_ranks,
                    failure=False,
                )
                next_state = H2GraphStateV1(successor_ranks, failure)
                atoms.append(
                    H2GraphTransitionAtomV1(
                        next_state=next_state,
                        probability=(
                            Fraction(1, len(empty)) * rank_probability
                        ),
                        realized_row_reward=reward,
                        failure=failure,
                        terminal=failure or remaining_horizon == 1,
                        spawn_cell=cell,
                        spawn_rank=rank,
                    )
                )
        if sum((atom.probability for atom in atoms), Fraction(0)) != 1:
            raise RuntimeError("exact H2 graph transition row is not normalized")
        return tuple(atoms)


def _integer_spawn_law(
    law: tuple[tuple[int, Fraction], ...],
) -> tuple[int, tuple[tuple[int, int], ...]]:
    canonical = _canonical_spawn_law(law)
    denominator = 1
    for _, probability in canonical:
        denominator = math.lcm(denominator, probability.denominator)
    integer = tuple(
        (
            rank,
            probability.numerator
            * (denominator // probability.denominator),
        )
        for rank, probability in canonical
    )
    if sum(weight for _, weight in integer) != denominator:
        raise RuntimeError("exact spawn law integerization failed")
    return denominator, integer


def _rank_from_token(
    law: tuple[tuple[int, int], ...],
    token: int,
) -> int:
    cursor = 0
    for rank, weight in law:
        cursor += weight
        if token < cursor:
            return rank
    raise RuntimeError("accepted rank token lies outside the spawn law")


def splitmix64_v1(value: int) -> int:
    if type(value) is not int:
        raise H2GraphTransitionInvariantViolation(
            "SplitMix64 input must be an integer"
        )
    word = value & _UINT64_MASK
    word = (word ^ (word >> 30)) * 0xBF58476D1CE4E5B9
    word &= _UINT64_MASK
    word = (word ^ (word >> 27)) * 0x94D049BB133111EB
    word &= _UINT64_MASK
    return (word ^ (word >> 31)) & _UINT64_MASK


def derive_splitmix64_seed_v1(
    *,
    seed_domain: str,
    pairing_group_id: str,
) -> int:
    if (
        type(seed_domain) is not str
        or not seed_domain
        or seed_domain.strip() != seed_domain
        or "\x00" in seed_domain
    ):
        raise H2GraphTransitionInvariantViolation(
            "seed domain must be one nonempty canonical string"
        )
    group = _cid(pairing_group_id, "pairing group")
    digest = hashlib.sha256(
        seed_domain.encode("utf-8")
        + b"\x00"
        + group.encode("ascii")
    ).digest()
    return int.from_bytes(digest[:8], "big")


def verify_exact_atoms_v1(
    *,
    kernel: H2GraphKernelV1,
    state: H2GraphStateV1,
    action: H2GraphActionV1,
    remaining_horizon: int,
    atoms: tuple[H2GraphTransitionAtomV1, ...],
) -> tuple[H2GraphTransitionAtomV1, ...]:
    """Replay one exact row at a serialization trust boundary.

    Transition atoms deliberately remain lightweight immutable arithmetic
    values.  They are not self-authenticating artifacts.  Any adapter that
    accepts serialized atoms from another process must bind the source row and
    call this verifier instead of trusting caller-provided atom fields.
    """

    if (
        type(atoms) is not tuple
        or any(type(atom) is not H2GraphTransitionAtomV1 for atom in atoms)
    ):
        raise H2GraphTransitionInvariantViolation(
            "serialized exact atoms must be one canonical typed tuple"
        )
    expected = kernel.exact_atoms(
        state,
        action,
        remaining_horizon=remaining_horizon,
    )
    if atoms != expected:
        raise H2GraphTransitionInvariantViolation(
            "serialized exact atoms do not replay from the bound source row"
        )
    return atoms


class DeterministicH2GraphStreamV1:
    """One mutable deterministic tape over an immutable exact graph row."""

    __slots__ = (
        "_accepted_draws",
        "_acceptance_limit",
        "_board",
        "_empty",
        "_integer_law",
        "_kernel",
        "_law_denominator",
        "_outcome_denominator",
        "_random_word_calls",
        "_rejection_count",
        "_remaining_horizon",
        "_reward",
        "_seed",
    )

    def __init__(
        self,
        *,
        kernel: H2GraphKernelV1,
        state: H2GraphStateV1,
        action: H2GraphActionV1,
        remaining_horizon: int,
        seed: int,
    ) -> None:
        if type(kernel) is not H2GraphKernelV1:
            raise H2GraphTransitionInvariantViolation(
                "stream requires one exact H2 graph kernel"
            )
        if type(seed) is not int or not 0 <= seed < _UINT64_MODULUS:
            raise H2GraphTransitionInvariantViolation(
                "stream seed must be one uint64"
            )
        if (
            type(remaining_horizon) is not int
            or remaining_horizon not in (1, kernel.horizon)
        ):
            raise H2GraphTransitionInvariantViolation(
                "stream remaining horizon is invalid"
            )
        board, empty, reward = kernel.merge(state, action)
        accounting_runtime.emit_owned_operation_v1(
            "engine.stream-init.merge",
            amount=1,
        )
        law_denominator, integer_law = _integer_spawn_law(
            kernel.spawn_law
        )
        outcome_denominator = len(empty) * law_denominator
        self._kernel = kernel
        self._remaining_horizon = remaining_horizon
        self._seed = seed
        self._board = board
        self._empty = empty
        self._reward = reward
        self._law_denominator = law_denominator
        self._integer_law = integer_law
        self._outcome_denominator = outcome_denominator
        self._acceptance_limit = (
            _UINT64_MODULUS
            - (_UINT64_MODULUS % outcome_denominator)
        )
        self._accepted_draws = 0
        self._random_word_calls = 0
        self._rejection_count = 0

    @property
    def accepted_draw_count(self) -> int:
        return self._accepted_draws

    @property
    def random_word_calls(self) -> int:
        return self._random_word_calls

    @property
    def rejection_count(self) -> int:
        return self._rejection_count

    def draw(self) -> H2GraphSampleV1:
        start = self._random_word_calls + 1
        words: list[int] = []
        while True:
            word_index = self._random_word_calls + 1
            word = splitmix64_v1(
                self._seed + _SPLITMIX_GAMMA * word_index
            )
            accounting_runtime.emit_owned_operation_v1(
                "engine.draw.random-word",
                amount=1,
            )
            self._random_word_calls += 1
            words.append(word)
            if word >= self._acceptance_limit:
                accounting_runtime.emit_owned_operation_v1(
                    "engine.draw.rejection",
                    amount=1,
                )
                self._rejection_count += 1
                continue
            token = word % self._outcome_denominator
            empty_index = token // self._law_denominator
            rank_token = token % self._law_denominator
            spawn_rank = _rank_from_token(
                self._integer_law,
                rank_token,
            )
            break
        spawn_cell = self._empty[empty_index]
        successor = list(self._board)
        successor[spawn_cell] = spawn_rank
        successor_ranks = tuple(successor)
        failure = not self._kernel.legal_actions_from_ranks(
            successor_ranks,
            failure=False,
        )
        next_state = H2GraphStateV1(successor_ranks, failure)
        self._accepted_draws += 1
        sample = H2GraphSampleV1(
            next_state=next_state,
            realized_row_reward=self._reward,
            failure=failure,
            terminal=failure or self._remaining_horizon == 1,
            spawn_cell=spawn_cell,
            spawn_rank=spawn_rank,
            accepted_draw_index=self._accepted_draws,
            random_word_start_index=start,
            random_words=tuple(words),
        )
        accounting_runtime.emit_owned_operation_v1(
            "engine.draw.ground-sample",
            amount=1,
        )
        return sample


def verify_deterministic_samples_v1(
    *,
    kernel: H2GraphKernelV1,
    state: H2GraphStateV1,
    action: H2GraphActionV1,
    remaining_horizon: int,
    seed: int,
    samples: tuple[H2GraphSampleV1, ...],
) -> tuple[H2GraphSampleV1, ...]:
    """Replay a complete deterministic sample prefix exactly.

    This is the only profile-neutral authority supplied for samples crossing a
    process or artifact boundary.  It verifies the source row, seed, accepted
    draw indices, random-word indices, rejection words, outcomes, and rewards
    by reconstructing the stream from its beginning.
    """

    if (
        type(samples) is not tuple
        or any(type(sample) is not H2GraphSampleV1 for sample in samples)
    ):
        raise H2GraphTransitionInvariantViolation(
            "serialized samples must be one canonical typed tuple"
        )
    stream = DeterministicH2GraphStreamV1(
        kernel=kernel,
        state=state,
        action=action,
        remaining_horizon=remaining_horizon,
        seed=seed,
    )
    expected = tuple(stream.draw() for _ in samples)
    if samples != expected:
        raise H2GraphTransitionInvariantViolation(
            "serialized samples do not replay from the bound row and seed"
        )
    return samples


__all__ = [
    "DeterministicH2GraphStreamV1",
    "H2GraphActionV1",
    "H2GraphKernelV1",
    "H2GraphSampleV1",
    "H2GraphStateV1",
    "H2GraphTransitionAtomV1",
    "H2GraphTransitionInvariantViolation",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "derive_splitmix64_seed_v1",
    "splitmix64_v1",
    "verify_deterministic_samples_v1",
    "verify_exact_atoms_v1",
]
