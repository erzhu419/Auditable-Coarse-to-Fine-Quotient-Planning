"""Exact, deterministic finite-horizon reachable-state enumeration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Generic

from .core import ActionT, FiniteKernel, Outcome, StateT


class EnumerationStatus(str, Enum):
    EXACT = "EXACT"
    STATE_CAP_EXCEEDED = "STATE_CAP_EXCEEDED"


class EvaluationTier(str, Enum):
    EXACT_SOUND = "EXACT_SOUND"
    STRESS_ONLY = "STRESS_ONLY"


@dataclass(frozen=True, slots=True)
class TransitionRecord(Generic[StateT, ActionT]):
    depth: int
    state: StateT
    action: ActionT
    outcomes: tuple[Outcome[StateT], ...]


@dataclass(frozen=True, slots=True)
class EnumerationResult(Generic[StateT, ActionT]):
    status: EnumerationStatus
    evaluation_tier: EvaluationTier
    complete: bool
    horizon: int
    states: tuple[StateT, ...]
    layers: tuple[tuple[StateT, ...], ...]
    transitions: tuple[TransitionRecord[StateT, ActionT], ...]
    state_count_lower_bound: int

    @property
    def state_count(self) -> int:
        """Stored unique states (exact iff ``complete`` is true)."""

        return len(self.states)


def _ordered(values: set[StateT]) -> tuple[StateT, ...]:
    return tuple(sorted(values, key=lambda value: (type(value).__qualname__, repr(value))))


def _validate_distribution(
    distribution: tuple[tuple[Fraction, StateT], ...], *, name: str
) -> tuple[tuple[Fraction, StateT], ...]:
    if not distribution:
        raise ValueError(f"{name} distribution must not be empty")
    total = Fraction(0)
    seen: set[StateT] = set()
    for probability, state in distribution:
        if not isinstance(probability, Fraction):
            probability = Fraction(str(probability))
        if probability <= 0:
            raise ValueError(f"{name} probabilities must be positive")
        if state in seen:
            raise ValueError(f"{name} distribution contains a duplicate state")
        seen.add(state)
        total += probability
    if total != 1:
        raise ValueError(f"{name} distribution mass must be one, got {total}")
    return distribution


def enumerate_reachable(
    kernel: FiniteKernel[StateT, ActionT],
    *,
    initial_distribution: tuple[tuple[Fraction, StateT], ...] | None = None,
    horizon: int | None = None,
    state_cap: int = 50_000,
) -> EnumerationResult[StateT, ActionT]:
    """Enumerate every positive-probability state reachable through ``horizon``.

    On the first would-be state beyond ``state_cap``, the function returns an
    explicitly incomplete ``STRESS_ONLY`` result and a lower bound of
    ``state_cap + 1``.  It never labels a capped prefix as exact-sound.
    """

    if state_cap <= 0:
        raise ValueError("state_cap must be positive")
    selected_horizon = kernel.horizon if horizon is None else horizon
    if selected_horizon < 0 or selected_horizon > kernel.horizon:
        raise ValueError("enumeration horizon must lie in [0, kernel.horizon]")

    initial = _validate_distribution(
        kernel.initial_distribution() if initial_distribution is None else initial_distribution,
        name="initial",
    )
    initial_states = _ordered({state for probability, state in initial if probability > 0})
    if len(initial_states) > state_cap:
        return EnumerationResult(
            EnumerationStatus.STATE_CAP_EXCEEDED,
            EvaluationTier.STRESS_ONLY,
            False,
            selected_horizon,
            initial_states[:state_cap],
            (initial_states[:state_cap],),
            (),
            state_cap + 1,
        )

    seen: set[StateT] = set(initial_states)
    ordered_seen: list[StateT] = list(initial_states)
    layers: list[tuple[StateT, ...]] = [initial_states]
    transitions: list[TransitionRecord[StateT, ActionT]] = []

    for depth in range(selected_horizon):
        next_layer: set[StateT] = set()
        for state in layers[-1]:
            if kernel.is_terminal(state):
                continue
            actions = tuple(sorted(kernel.actions(state), key=repr))
            for action in actions:
                outcomes = kernel.step(state, action)
                if not outcomes:
                    raise ValueError("a valid action must have at least one outcome")
                mass = sum((outcome.probability for outcome in outcomes), Fraction(0))
                if mass != 1:
                    raise ValueError(
                        f"transition mass at depth {depth} for {action!r} is {mass}, not one"
                    )
                transitions.append(TransitionRecord(depth, state, action, outcomes))
                for outcome in outcomes:
                    next_state = outcome.next_state
                    next_layer.add(next_state)
                    if next_state not in seen:
                        if len(seen) == state_cap:
                            return EnumerationResult(
                                EnumerationStatus.STATE_CAP_EXCEEDED,
                                EvaluationTier.STRESS_ONLY,
                                False,
                                selected_horizon,
                                tuple(ordered_seen),
                                tuple(layers),
                                tuple(transitions),
                                state_cap + 1,
                            )
                        seen.add(next_state)
                        ordered_seen.append(next_state)
        layers.append(_ordered(next_layer))

    return EnumerationResult(
        EnumerationStatus.EXACT,
        EvaluationTier.EXACT_SOUND,
        True,
        selected_horizon,
        tuple(ordered_seen),
        tuple(layers),
        tuple(transitions),
        len(ordered_seen),
    )
