"""Shared contracts for finite, exactly enumerable decision processes.

V0 keeps the physical kernel separate from query-specific rewards and goals.  A
kernel therefore exposes named additive reward features rather than one fixed
scalar reward.  Probabilities and built-in benchmark reward features are
``Fraction`` objects so that probability-mass and oracle checks do not depend
on floating-point tolerances.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Generic, Hashable, Mapping, Protocol, TypeVar, runtime_checkable


StateT = TypeVar("StateT", bound=Hashable)
ActionT = TypeVar("ActionT", bound=Hashable)


def _as_fraction(value: Fraction | int | float | str) -> Fraction:
    """Convert a public numeric input without preserving binary-float noise."""

    if isinstance(value, Fraction):
        return value
    if isinstance(value, float):
        return Fraction(str(value))
    return Fraction(value)


@dataclass(frozen=True, slots=True)
class Outcome(Generic[StateT]):
    """One atom of an exact transition distribution.

    ``failure`` is the one-time transition cost for entering the absorbing
    failure set.  It is false on already-terminal states because terminal
    states have no actions and hence emit no further outcomes.
    """

    probability: Fraction
    next_state: StateT
    reward_features: tuple[tuple[str, Fraction], ...] = ()
    failure: bool = False
    terminal: bool = False

    def __post_init__(self) -> None:
        probability = _as_fraction(self.probability)
        if probability <= 0 or probability > 1:
            raise ValueError("outcome probability must lie in (0, 1]")
        object.__setattr__(self, "probability", probability)

        names: set[str] = set()
        canonical_features: list[tuple[str, Fraction]] = []
        for name, value in self.reward_features:
            if not name:
                raise ValueError("reward-feature names must be nonempty")
            if name in names:
                raise ValueError(f"duplicate reward feature: {name}")
            names.add(name)
            canonical_features.append((name, _as_fraction(value)))
        object.__setattr__(self, "reward_features", tuple(canonical_features))

    def feature(self, name: str, default: Fraction = Fraction(0)) -> Fraction:
        """Return one named additive feature."""

        for feature_name, value in self.reward_features:
            if feature_name == name:
                return value
        return default


@runtime_checkable
class FiniteKernel(Protocol[StateT, ActionT]):
    """Protocol implemented by every exact finite V0 benchmark."""

    @property
    def horizon(self) -> int:
        """Largest supported finite planning horizon."""

    @property
    def registered_reward_features(self) -> tuple[str, ...]:
        """Reward-feature names accepted by a production query."""

    @property
    def registered_goals(self) -> tuple[str, ...]:
        """Goal identifiers accepted without rebuilding the kernel/model."""

    def reward_upper_bound(
        self,
        horizon: int,
        raw_weights: Mapping[str, Fraction],
        goal: str,
    ) -> Fraction:
        """Prove an upper bound on raw total return for query validation."""

    def initial_distribution(self) -> tuple[tuple[Fraction, StateT], ...]:
        """Return an ordered, normalized exact initial-state distribution."""

    def actions(self, state: StateT) -> tuple[ActionT, ...]:
        """Return only valid actions, in canonical deterministic order."""

    def step(self, state: StateT, action: ActionT) -> tuple[Outcome[StateT], ...]:
        """Return an ordered exact distribution whose mass is one."""

    def is_terminal(self, state: StateT) -> bool:
        """Whether ``state`` belongs to an absorbing terminal set."""


@dataclass(frozen=True, slots=True)
class QuerySpec(Generic[StateT]):
    """A per-query request over a reusable physical/abstract model.

    The distribution and reward basis are tuples (rather than dictionaries) so
    a query remains immutable, hashable, serializable, and deterministically
    ordered. ``reward_weights`` are expressed in raw feature units;
    ``normalizer`` is a proved positive upper bound on raw total return, and
    planning evaluates the coefficients divided by that bound.  The proof ID
    names the deterministic validation rule used to establish that bound.
    """

    initial_distribution: tuple[tuple[Fraction, StateT], ...]
    horizon: int
    reward_weights: tuple[tuple[str, Fraction], ...]
    goal: str
    delta: Fraction
    normalizer: Fraction = Fraction(1)
    normalizer_proof_id: str = "kernel.reward_upper_bound.v1"

    def __post_init__(self) -> None:
        if self.horizon < 0:
            raise ValueError("query horizon must be nonnegative")

        normalized_initial: list[tuple[Fraction, StateT]] = []
        initial_mass = Fraction(0)
        seen_states: set[StateT] = set()
        for probability, state in self.initial_distribution:
            p = _as_fraction(probability)
            if p <= 0:
                raise ValueError("initial-state probabilities must be positive")
            if state in seen_states:
                raise ValueError("initial distribution contains a duplicate state")
            seen_states.add(state)
            normalized_initial.append((p, state))
            initial_mass += p
        if initial_mass != 1:
            raise ValueError(f"initial distribution must have mass one, got {initial_mass}")
        object.__setattr__(self, "initial_distribution", tuple(normalized_initial))

        names: set[str] = set()
        weights: list[tuple[str, Fraction]] = []
        for name, weight in self.reward_weights:
            if not name or name in names:
                raise ValueError("reward-weight names must be nonempty and unique")
            names.add(name)
            weights.append((name, _as_fraction(weight)))
        object.__setattr__(self, "reward_weights", tuple(weights))

        delta = _as_fraction(self.delta)
        if delta not in {Fraction(0), Fraction(1, 20), Fraction(1, 10)}:
            raise ValueError("V0 delta must be one of 0, 0.05, or 0.10")
        object.__setattr__(self, "delta", delta)

        normalizer = _as_fraction(self.normalizer)
        if normalizer <= 0:
            raise ValueError("reward normalizer must be positive")
        object.__setattr__(self, "normalizer", normalizer)
        if (
            not isinstance(self.normalizer_proof_id, str)
            or not self.normalizer_proof_id.strip()
        ):
            raise ValueError("normalizer proof ID must be a nonempty string")

    @property
    def normalizer_value(self) -> Fraction:
        """Normative API name for the proved raw-return upper bound."""

        return self.normalizer

    @classmethod
    def from_state(
        cls,
        state: StateT,
        *,
        horizon: int,
        reward_weights: tuple[tuple[str, Fraction], ...] = (),
        goal: str = "default",
        delta: Fraction = Fraction(1, 20),
        normalizer: Fraction = Fraction(1),
        normalizer_proof_id: str = "kernel.reward_upper_bound.v1",
    ) -> "QuerySpec[StateT]":
        """Construct the common degenerate-initial-state query."""

        return cls(
            ((Fraction(1), state),),
            horizon,
            reward_weights,
            goal,
            delta,
            normalizer,
            normalizer_proof_id,
        )
