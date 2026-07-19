"""Exact tiny-instance ground planning under a chance constraint.

The oracle jointly chooses one action for every state carrying probability at
the current stage.  Recursing on that exact successor occupancy distribution
preserves deterministic-Markov consistency when stochastic paths merge.  A
state-local Pareto recursion is not sufficient for this purpose: pruning a
locally dominated subpolicy can remove a globally useful policy when another
branch shares some of its downstream decisions.

Frontier growth is exponential in the worst case, so this remains a J0 oracle
for finite fixtures rather than a large-scale planner.  No sampling,
relaxation, or silent policy cap is used.  A brute-force policy enumerator
remains available solely for microscopic cross-checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Any, Hashable, Iterator, Mapping

from .common import (
    as_fraction,
    deterministic_order,
    is_stopped,
    iter_outcomes,
    outcome_reward,
    query_horizon,
    query_initial_distribution,
    reward_weights,
    validate_query,
)
from .policy import FiniteHorizonPolicy


@dataclass(frozen=True)
class PolicyEvaluation:
    expected_reward: Fraction
    failure_probability: Fraction


@dataclass(frozen=True)
class ParetoPoint:
    expected_reward: Fraction
    failure_probability: Fraction
    policy: FiniteHorizonPolicy[Any, Any]


@dataclass(frozen=True)
class GroundParetoResult:
    frontier: tuple[ParetoPoint, ...]
    selected: ParetoPoint | None
    composed_candidate_count: int

    @property
    def feasible(self) -> bool:
        return self.selected is not None

    @property
    def evaluated_policy_count(self) -> int:
        """Backward-compatible name for the exact candidate-work counter."""

        return self.composed_candidate_count


def reachable_decision_pairs(kernel: Any, query: Any) -> tuple[tuple[int, Hashable], ...]:
    """Return all state/horizon pairs reachable under any ground action."""

    horizon = query_horizon(kernel, query)
    goal = getattr(query, "goal", None)
    initial = query_initial_distribution(kernel, query)
    pending = [(horizon, state) for probability, state in initial if probability > 0]
    visited: set[tuple[int, Hashable]] = set()
    decision_pairs: set[tuple[int, Hashable]] = set()

    while pending:
        remaining, state = pending.pop()
        marker = (remaining, state)
        if marker in visited:
            continue
        visited.add(marker)
        if remaining <= 0 or is_stopped(kernel, state, goal):
            continue
        actions = deterministic_order(kernel.actions(state))
        if not actions:
            continue
        decision_pairs.add(marker)
        if remaining == 1:
            continue
        for action in actions:
            for outcome in iter_outcomes(kernel, state, action):
                if outcome.failure or outcome.terminal:
                    continue
                if is_stopped(kernel, outcome.next_state, goal):
                    continue
                pending.append((remaining - 1, outcome.next_state))

    return tuple(sorted(decision_pairs, key=lambda item: (-item[0], repr(item[1]))))


def enumerate_deterministic_policies(
    kernel: Any,
    query: Any,
) -> Iterator[FiniteHorizonPolicy[Any, Any]]:
    decision_pairs = reachable_decision_pairs(kernel, query)
    action_sets = [deterministic_order(kernel.actions(state)) for _, state in decision_pairs]
    if any(not actions for actions in action_sets):
        return
    if not decision_pairs:
        yield FiniteHorizonPolicy(())
        return
    for actions in product(*action_sets):
        yield FiniteHorizonPolicy.from_mapping(
            {decision_pair: action for decision_pair, action in zip(decision_pairs, actions)}
        )


def evaluate_ground_policy(
    kernel: Any,
    query: Any,
    policy: FiniteHorizonPolicy[Any, Any],
) -> PolicyEvaluation:
    """Evaluate reward and one-time absorbing-failure probability exactly."""

    validate_query(kernel, query)
    weights = reward_weights(query)
    goal = getattr(query, "goal", None)
    horizon = query_horizon(kernel, query)
    memo: dict[tuple[int, Hashable], PolicyEvaluation] = {}

    def evaluate_state(state: Hashable, remaining: int) -> PolicyEvaluation:
        key = (remaining, state)
        if key in memo:
            return memo[key]
        if remaining <= 0 or is_stopped(kernel, state, goal):
            result = PolicyEvaluation(Fraction(0), Fraction(0))
            memo[key] = result
            return result
        actions = tuple(kernel.actions(state))
        if not actions:
            result = PolicyEvaluation(Fraction(0), Fraction(0))
            memo[key] = result
            return result
        action = policy.action(state, remaining)
        if action not in actions:
            raise ValueError(f"policy chose unavailable action {action!r} at state {state!r}")

        reward = Fraction(0)
        failure = Fraction(0)
        for outcome in iter_outcomes(kernel, state, action):
            probability = as_fraction(outcome.probability)
            branch_reward = outcome_reward(outcome, weights)
            branch_failure = Fraction(1) if outcome.failure else Fraction(0)
            stopped = outcome.failure or outcome.terminal or is_stopped(
                kernel, outcome.next_state, goal
            )
            if not stopped:
                continuation = evaluate_state(outcome.next_state, remaining - 1)
                branch_reward += continuation.expected_reward
                branch_failure = continuation.failure_probability
            reward += probability * branch_reward
            failure += probability * branch_failure
        result = PolicyEvaluation(reward, failure)
        memo[key] = result
        return result

    expected_reward = Fraction(0)
    failure_probability = Fraction(0)
    for probability, state in query_initial_distribution(kernel, query):
        value = evaluate_state(state, horizon)
        expected_reward += probability * value.expected_reward
        failure_probability += probability * value.failure_probability
    return PolicyEvaluation(expected_reward, failure_probability)


def pareto_prune(points: list[ParetoPoint]) -> tuple[ParetoPoint, ...]:
    """Keep reward-maximising/risk-minimising nondominated points."""

    unique: dict[tuple[Fraction, Fraction], ParetoPoint] = {}
    for point in points:
        key = (point.expected_reward, point.failure_probability)
        incumbent = unique.get(key)
        if incumbent is None or point.policy.signature() < incumbent.policy.signature():
            unique[key] = point

    candidates = list(unique.values())
    frontier: list[ParetoPoint] = []
    for point in candidates:
        dominated = any(
            other is not point
            and other.expected_reward >= point.expected_reward
            and other.failure_probability <= point.failure_probability
            and (
                other.expected_reward > point.expected_reward
                or other.failure_probability < point.failure_probability
            )
            for other in candidates
        )
        if not dominated:
            frontier.append(point)
    frontier.sort(
        key=lambda point: (
            point.failure_probability,
            -point.expected_reward,
            point.policy.signature(),
        )
    )
    return tuple(frontier)


def select_constrained(
    frontier: tuple[ParetoPoint, ...],
    delta: Fraction,
) -> ParetoPoint | None:
    feasible = [point for point in frontier if point.failure_probability <= delta]
    if not feasible:
        return None
    return min(
        feasible,
        key=lambda point: (
            -point.expected_reward,
            point.failure_probability,
            point.policy.signature(),
        ),
    )


def solve_ground_pareto(
    kernel: Any,
    query: Any,
    required_decisions: Mapping[tuple[int, Hashable], Hashable] | None = None,
) -> GroundParetoResult:
    """Solve J0 exactly over deterministic finite-horizon Markov policies.

    The recursion state is the exact sub-probability distribution over active
    states at one remaining horizon.  Actions are selected jointly for its
    support, after which all stochastic successors are coalesced before the
    next recursive call.  This enumerates only decisions reachable under the
    current policy prefix while enforcing a single decision at every shared
    ``(state, remaining)`` pair.
    """

    validate_query(kernel, query)
    weights = reward_weights(query)
    goal = getattr(query, "goal", None)
    horizon = query_horizon(kernel, query)
    requirements = dict(required_decisions or {})
    if requirements:
        reachable_pairs = set(reachable_decision_pairs(kernel, query))
        for decision, required_action in requirements.items():
            if (
                not isinstance(decision, tuple)
                or len(decision) != 2
                or not isinstance(decision[0], int)
            ):
                raise ValueError(
                    "required decision keys must be (positive remaining, state) pairs"
                )
            remaining, state = decision
            if remaining <= 0 or remaining > horizon:
                raise ValueError(
                    f"required decision remaining horizon {remaining!r} lies outside "
                    f"[1, {horizon}]"
                )
            if decision not in reachable_pairs:
                raise ValueError(
                    f"required decision {decision!r} is not reachable under any ground action"
                )
            if required_action not in tuple(kernel.actions(state)):
                raise ValueError(
                    f"required action {required_action!r} is unavailable at state {state!r}"
                )
    Distribution = tuple[tuple[Hashable, Fraction], ...]
    memo: dict[tuple[int, Distribution], tuple[ParetoPoint, ...]] = {}
    composed_candidates = 0

    zero = ParetoPoint(Fraction(0), Fraction(0), FiniteHorizonPolicy(()))

    def canonical_distribution(
        masses: dict[Hashable, Fraction],
    ) -> Distribution:
        return tuple(
            sorted(
                (
                    (state, mass)
                    for state, mass in masses.items()
                    if mass > 0
                ),
                key=lambda item: repr(item[0]),
            )
        )

    def occupancy_frontier(
        distribution: Distribution,
        remaining: int,
    ) -> tuple[ParetoPoint, ...]:
        nonlocal composed_candidates
        key = (remaining, distribution)
        if key in memo:
            return memo[key]
        if remaining <= 0 or not distribution:
            memo[key] = (zero,)
            return memo[key]

        decision_states: list[Hashable] = []
        action_sets: list[tuple[Hashable, ...]] = []
        state_mass = dict(distribution)
        for state, mass in distribution:
            if mass <= 0 or is_stopped(kernel, state, goal):
                continue
            actions = deterministic_order(kernel.actions(state))
            decision_key = (remaining, state)
            if decision_key in requirements:
                actions = (requirements[decision_key],)
            if actions:
                decision_states.append(state)
                action_sets.append(actions)
        if not decision_states:
            memo[key] = (zero,)
            return memo[key]

        # At the final decision stage there is no successor policy to couple.
        # Compose one state's exact action frontier at a time and Pareto-prune
        # after every state.  This is equivalent to the full Cartesian product
        # but avoids enumerating 2^|support| combinations for symmetric
        # distribution-valued queries such as the safe-chain D4 orbit.
        if remaining == 1:
            partial_frontier: tuple[ParetoPoint, ...] = (zero,)
            for state, actions in zip(decision_states, action_sets):
                mass = state_mass[state]
                extended: list[ParetoPoint] = []
                for partial in partial_frontier:
                    for action in actions:
                        composed_candidates += 1
                        immediate_reward = Fraction(0)
                        immediate_failure = Fraction(0)
                        for outcome in iter_outcomes(kernel, state, action):
                            probability = mass * as_fraction(outcome.probability)
                            immediate_reward += probability * outcome_reward(
                                outcome, weights
                            )
                            if outcome.failure:
                                immediate_failure += probability
                        mapping = partial.policy.as_dict()
                        mapping[(remaining, state)] = action
                        extended.append(
                            ParetoPoint(
                                partial.expected_reward + immediate_reward,
                                partial.failure_probability + immediate_failure,
                                FiniteHorizonPolicy.from_mapping(mapping),
                            )
                        )
                partial_frontier = pareto_prune(extended)
            memo[key] = partial_frontier
            return memo[key]

        candidates: list[ParetoPoint] = []
        for chosen_actions in product(*action_sets):
            immediate_reward = Fraction(0)
            immediate_failure = Fraction(0)
            successor_mass: dict[Hashable, Fraction] = {}
            current_decisions: list[
                tuple[tuple[int, Hashable], Hashable]
            ] = []
            for state, action in zip(decision_states, chosen_actions):
                mass = state_mass[state]
                current_decisions.append(((remaining, state), action))
                for outcome in iter_outcomes(kernel, state, action):
                    probability = mass * as_fraction(outcome.probability)
                    immediate_reward += probability * outcome_reward(outcome, weights)
                    if outcome.failure:
                        immediate_failure += probability
                        continue
                    stopped = outcome.terminal or is_stopped(
                        kernel, outcome.next_state, goal
                    )
                    if not stopped:
                        successor_mass[outcome.next_state] = (
                            successor_mass.get(outcome.next_state, Fraction(0))
                            + probability
                        )

            successor_distribution = canonical_distribution(successor_mass)
            continuation_frontier = occupancy_frontier(
                successor_distribution, remaining - 1
            )
            for continuation in continuation_frontier:
                composed_candidates += 1
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
                combined_policy = FiniteHorizonPolicy.from_mapping(mapping)
                candidates.append(
                    ParetoPoint(
                        immediate_reward + continuation.expected_reward,
                        immediate_failure + continuation.failure_probability,
                        combined_policy,
                    )
                )
        memo[key] = pareto_prune(candidates)
        return memo[key]

    initial_mass: dict[Hashable, Fraction] = {}
    for probability, state in query_initial_distribution(kernel, query):
        initial_mass[state] = initial_mass.get(state, Fraction(0)) + probability
    frontier = occupancy_frontier(canonical_distribution(initial_mass), horizon)
    delta = as_fraction(getattr(query, "delta"))
    return GroundParetoResult(
        frontier=frontier,
        selected=select_constrained(frontier, delta),
        composed_candidate_count=composed_candidates,
    )


def solve_ground_action_frontier(
    kernel: Any,
    query: Any,
    *,
    state: Hashable,
    remaining: int,
    action: Hashable,
) -> GroundParetoResult:
    """Solve the exact ground frontier with one state-time action forced.

    The requirement constrains the deterministic Markov decision whenever the
    pair is reached; it does not alter the initial distribution or force the
    state itself to be visited.  Structurally unreachable pairs and illegal
    actions are rejected instead of returning a vacuous frontier.
    """

    return solve_ground_pareto(
        kernel,
        query,
        required_decisions={(remaining, state): action},
    )
