"""Finite-horizon deterministic policy objects.

Policies are query results, not part of the reusable quotient model.  A
decision is indexed by both the current state (ground or abstract) and the
remaining horizon, so the representation supports non-stationary policies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Hashable, Iterable, Mapping, TypeVar


StateT = TypeVar("StateT", bound=Hashable)
ActionT = TypeVar("ActionT", bound=Hashable)


@dataclass(frozen=True)
class PolicyDecision(Generic[StateT, ActionT]):
    remaining: int
    state: StateT
    action: ActionT

    def __post_init__(self) -> None:
        if self.remaining <= 0:
            raise ValueError("policy decisions require a positive remaining horizon")


@dataclass(frozen=True)
class FiniteHorizonPolicy(Generic[StateT, ActionT]):
    """An immutable deterministic Markov policy for a finite horizon."""

    decisions: tuple[PolicyDecision[StateT, ActionT], ...]

    def __post_init__(self) -> None:
        seen: set[tuple[int, StateT]] = set()
        for decision in self.decisions:
            key = (decision.remaining, decision.state)
            if key in seen:
                raise ValueError(f"duplicate policy decision for {key!r}")
            seen.add(key)

    @classmethod
    def from_mapping(
        cls,
        mapping: Mapping[tuple[int, StateT], ActionT]
        | Iterable[tuple[tuple[int, StateT], ActionT]],
    ) -> "FiniteHorizonPolicy[StateT, ActionT]":
        items = mapping.items() if isinstance(mapping, Mapping) else mapping
        decisions = [
            PolicyDecision(remaining=key[0], state=key[1], action=action)
            for key, action in items
        ]
        decisions.sort(key=lambda item: (-item.remaining, repr(item.state), repr(item.action)))
        return cls(tuple(decisions))

    def action(self, state: StateT, remaining: int) -> ActionT:
        for decision in self.decisions:
            if decision.remaining == remaining and decision.state == state:
                return decision.action
        raise KeyError(f"policy has no decision for state={state!r}, remaining={remaining}")

    def contains(self, state: StateT, remaining: int) -> bool:
        try:
            self.action(state, remaining)
        except KeyError:
            return False
        return True

    def as_dict(self) -> dict[tuple[int, StateT], ActionT]:
        return {
            (decision.remaining, decision.state): decision.action
            for decision in self.decisions
        }

    def signature(self) -> tuple[tuple[int, str, str], ...]:
        """Stable ordering key used for deterministic tie breaking."""

        return tuple(
            (decision.remaining, repr(decision.state), repr(decision.action))
            for decision in self.decisions
        )


EMPTY_POLICY: FiniteHorizonPolicy[Hashable, Hashable] = FiniteHorizonPolicy(())
