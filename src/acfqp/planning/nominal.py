"""Policy proposal on the reusable nominal quotient model."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Any, Hashable, Iterable

from acfqp.abstraction.quotient import NominalQuotient

from .common import as_fraction, reward_weights
from .ground import ParetoPoint, pareto_prune, select_constrained
from .policy import FiniteHorizonPolicy


@dataclass(frozen=True)
class NominalParetoResult:
    frontier: tuple[ParetoPoint, ...]
    selected: ParetoPoint | None
    composed_candidate_count: int

    @property
    def feasible(self) -> bool:
        return self.selected is not None


def solve_nominal_pareto(
    model: NominalQuotient,
    query: Any,
    *,
    goal_cells: Iterable[Hashable] = (),
) -> NominalParetoResult:
    """Plan exactly in the point model; the result still requires an audit.

    As in the J0 oracle, the recursion uses an exact occupancy distribution and
    jointly chooses actions for its support.  This preserves one deterministic
    decision at a shared downstream ``(cell, remaining)`` pair when abstract
    stochastic paths merge.
    """

    horizon = int(query.horizon)
    if horizon < 0 or horizon > model.horizon:
        raise ValueError("query horizon lies outside the nominal model horizon")
    weights = reward_weights(query)
    goals = set(goal_cells)
    Distribution = tuple[tuple[Hashable, Fraction], ...]
    memo: dict[tuple[int, Distribution], tuple[ParetoPoint, ...]] = {}
    candidate_count = 0
    zero = ParetoPoint(Fraction(0), Fraction(0), FiniteHorizonPolicy(()))

    def canonical_distribution(
        masses: dict[Hashable, Fraction],
    ) -> Distribution:
        return tuple(
            sorted(
                ((cell, mass) for cell, mass in masses.items() if mass > 0),
                key=lambda item: repr(item[0]),
            )
        )

    def frontier_for(
        distribution: Distribution,
        remaining: int,
    ) -> tuple[ParetoPoint, ...]:
        nonlocal candidate_count
        key = (remaining, distribution)
        if key in memo:
            return memo[key]
        if remaining <= 0 or not distribution:
            memo[key] = (zero,)
            return memo[key]

        cell_mass = dict(distribution)
        decision_cells: list[Hashable] = []
        action_sets: list[tuple[Hashable, ...]] = []
        for cell, mass in distribution:
            if mass <= 0 or cell in goals:
                continue
            actions = model.actions(cell)
            if actions:
                decision_cells.append(cell)
                action_sets.append(actions)
        if not decision_cells:
            memo[key] = (zero,)
            return memo[key]

        candidates: list[ParetoPoint] = []
        for chosen_actions in product(*action_sets):
            immediate_reward = Fraction(0)
            immediate_failure = Fraction(0)
            successor_mass: dict[Hashable, Fraction] = {}
            current_decisions: list[tuple[tuple[int, Hashable], Hashable]] = []
            for cell, action in zip(decision_cells, chosen_actions):
                mass = cell_mass[cell]
                transition = model.transition(cell, action)
                current_decisions.append(((remaining, cell), action))
                immediate_reward += mass * transition.reward(weights)
                immediate_failure += mass * transition.failure_probability
                for successor, probability in transition.successor_probabilities:
                    successor_mass[successor] = (
                        successor_mass.get(successor, Fraction(0))
                        + mass * probability
                    )

            continuation_frontier = frontier_for(
                canonical_distribution(successor_mass), remaining - 1
            )
            for continuation in continuation_frontier:
                candidate_count += 1
                mapping = continuation.policy.as_dict()
                conflict = False
                for decision_key, action in current_decisions:
                    incumbent = mapping.get(decision_key)
                    if incumbent is not None and incumbent != action:
                        conflict = True
                        break
                    mapping[decision_key] = action
                if conflict:
                    continue
                policy = FiniteHorizonPolicy.from_mapping(mapping)
                candidates.append(
                    ParetoPoint(
                        immediate_reward + continuation.expected_reward,
                        immediate_failure + continuation.failure_probability,
                        policy,
                    )
                )
        memo[key] = pareto_prune(candidates)
        return memo[key]

    initial_mass: dict[Hashable, Fraction] = {}
    for probability, state in query.initial_distribution:
        cell = model.partition.cell_of(state)
        initial_mass[cell] = initial_mass.get(cell, Fraction(0)) + as_fraction(probability)
    if not initial_mass:
        raise ValueError("query initial distribution must not be empty")
    if sum(initial_mass.values(), Fraction(0)) != 1:
        raise ValueError("query initial probabilities must sum to one")
    frontier = frontier_for(canonical_distribution(initial_mass), horizon)
    return NominalParetoResult(
        frontier=frontier,
        selected=select_constrained(frontier, as_fraction(query.delta)),
        composed_candidate_count=candidate_count,
    )
