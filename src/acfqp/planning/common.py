"""Shared exact arithmetic and kernel helpers for planning code."""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Hashable, Iterable, Mapping


def as_fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, float):
        return Fraction(str(value))
    return Fraction(value)


def reward_weights(query: Any) -> dict[str, Fraction]:
    """Return query coefficients on the certified normalized-return scale.

    ``QuerySpec.reward_weights`` are coefficients in raw feature units, while
    its proved positive ``normalizer`` bounds total raw return.  Legacy
    query-like test objects without that field use the unit normalizer.
    """

    raw = getattr(query, "reward_weights", ())
    items = raw.items() if isinstance(raw, Mapping) else raw
    normalizer = as_fraction(getattr(query, "normalizer", Fraction(1)))
    if normalizer <= 0:
        raise ValueError("reward normalizer must be positive")
    return {
        str(name): as_fraction(weight) / normalizer
        for name, weight in items
    }


def outcome_reward(outcome: Any, weights: Mapping[str, Fraction]) -> Fraction:
    raw = getattr(outcome, "reward_features", ())
    items = raw.items() if isinstance(raw, Mapping) else raw
    return sum(
        (weights.get(str(name), Fraction(0)) * as_fraction(value) for name, value in items),
        Fraction(0),
    )


def query_initial_distribution(kernel: Any, query: Any) -> tuple[tuple[Fraction, Hashable], ...]:
    raw = getattr(query, "initial_distribution", None)
    if not raw:
        raw = kernel.initial_distribution()
    distribution = tuple((as_fraction(probability), state) for probability, state in raw)
    if not distribution:
        raise ValueError("initial distribution must not be empty")
    if any(probability < 0 for probability, _ in distribution):
        raise ValueError("initial probabilities must be non-negative")
    total = sum((probability for probability, _ in distribution), Fraction(0))
    if total != 1:
        raise ValueError(f"initial probabilities must sum to one, got {total}")
    return distribution


def query_horizon(kernel: Any, query: Any) -> int:
    horizon = int(getattr(query, "horizon"))
    if horizon < 0:
        raise ValueError("query horizon must be non-negative")
    maximum = int(getattr(kernel, "horizon"))
    if horizon > maximum:
        raise ValueError(f"query horizon {horizon} exceeds kernel horizon {maximum}")
    return horizon


def validate_query(kernel: Any, query: Any) -> None:
    """Validate the query fields whose registry is owned by a domain kernel.

    Lightweight test kernels may omit the optional registries. Production V0
    kernels expose them, in which case unknown reward features or goals are
    rejected instead of being silently treated as zero/no-op semantics.
    """

    query_horizon(kernel, query)
    normalizer = as_fraction(getattr(query, "normalizer", Fraction(1)))
    if normalizer <= 0:
        raise ValueError("reward normalizer must be positive")

    raw = getattr(query, "reward_weights", ())
    items = raw.items() if isinstance(raw, Mapping) else raw
    raw_weights = {str(name): as_fraction(weight) for name, weight in items}

    registered_rewards = getattr(kernel, "registered_reward_features", None)
    if registered_rewards is not None:
        allowed = {str(name) for name in registered_rewards}
        requested = set(raw_weights)
        unknown = requested - allowed
        if unknown:
            raise ValueError(f"unregistered reward features: {sorted(unknown)!r}")

    goal = getattr(query, "goal", None)
    registered_goals = getattr(kernel, "registered_goals", None)
    if registered_goals is not None:
        if goal not in set(registered_goals):
            raise ValueError(f"unregistered goal: {goal!r}")

    bounder = getattr(kernel, "reward_upper_bound", None)
    if callable(bounder):
        proved_bound = as_fraction(bounder(query_horizon(kernel, query), raw_weights, goal))
        if proved_bound < 0:
            raise ValueError("proved reward upper bound must be nonnegative")
        if normalizer < proved_bound:
            raise ValueError(
                f"reward normalizer {normalizer} is below proved bound {proved_bound}"
            )


def iter_outcomes(kernel: Any, state: Hashable, action: Hashable) -> tuple[Any, ...]:
    raw = kernel.step(state, action)
    if hasattr(raw, "probability"):
        outcomes = (raw,)
    else:
        outcomes = tuple(raw)
    if not outcomes:
        raise ValueError(f"action {action!r} at state {state!r} has no outcomes")
    probabilities = tuple(as_fraction(outcome.probability) for outcome in outcomes)
    if any(probability < 0 for probability in probabilities):
        raise ValueError("outcome probabilities must be non-negative")
    total = sum(probabilities, Fraction(0))
    if total != 1:
        raise ValueError(
            f"outcome probabilities for state={state!r}, action={action!r} "
            f"must sum to one, got {total}"
        )
    return outcomes


def goal_reached(goal: Any, state: Hashable) -> bool:
    """Interpret the small registered-goal forms used by V0 adapters.

    Domain kernels remain authoritative for structural terminal states.  This
    helper additionally supports callable goals, literal goal states, and
    states exposing an ``is_goal`` method or ``goal`` attribute.
    """

    if goal is None:
        return False
    if callable(goal):
        return bool(goal(state))
    checker = getattr(state, "is_goal", None)
    if callable(checker):
        try:
            return bool(checker(goal))
        except TypeError:
            return bool(checker())
    if hasattr(state, "goal"):
        return getattr(state, "goal") == goal
    return state == goal


def is_stopped(kernel: Any, state: Hashable, goal: Any = None) -> bool:
    if bool(kernel.is_terminal(state)):
        return True
    registered_checker = getattr(kernel, "is_goal", None)
    if callable(registered_checker) and goal is not None:
        try:
            return bool(registered_checker(state, goal))
        except TypeError:
            return bool(registered_checker(goal, state))
    return goal_reached(goal, state)


def deterministic_order(values: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(sorted(values, key=repr))
