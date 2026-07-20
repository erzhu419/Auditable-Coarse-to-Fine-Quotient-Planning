"""Sound full-plan audits for policies proposed on a nominal quotient."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Hashable, Iterable

from acfqp.abstraction.partition import Partition
from acfqp.abstraction.quotient import ExactRealizationEnvelope

from .common import (
    as_fraction,
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
class AuditIssue:
    code: str
    cell: Hashable
    remaining: int
    detail: str


@dataclass(frozen=True)
class CellPolicyBound:
    cell: Hashable
    remaining: int
    reward_lower: Fraction
    failure_upper: Fraction


@dataclass(frozen=True)
class AbstractPolicyAudit:
    unrestricted_reward_upper: Fraction
    lifted_reward_lower: Fraction | None
    lifted_failure_upper: Fraction | None
    regret_upper: Fraction | None
    regret_tolerance: Fraction
    risk_tolerance: Fraction
    certified: bool
    issues: tuple[AuditIssue, ...]
    reachable_bounds: tuple[CellPolicyBound, ...]

    @property
    def safe(self) -> bool:
        return (
            self.lifted_failure_upper is not None
            and self.lifted_failure_upper <= self.risk_tolerance
        )


def unrestricted_upper_envelope(
    kernel: Any,
    query: Any,
    partition: Partition,
) -> dict[tuple[int, Hashable], Fraction]:
    """Compute normative ``U_all`` using every ground action."""

    horizon = query_horizon(kernel, query)
    weights = reward_weights(query)
    goal = getattr(query, "goal", None)
    upper: dict[tuple[int, Hashable], Fraction] = {
        (0, cell): Fraction(0) for cell in partition.cell_ids
    }
    for remaining in range(1, horizon + 1):
        for cell in partition.cell_ids:
            candidates: list[Fraction] = []
            for state in partition.members(cell):
                if is_stopped(kernel, state, goal):
                    candidates.append(Fraction(0))
                    continue
                actions = tuple(kernel.actions(state))
                if not actions:
                    candidates.append(Fraction(0))
                    continue
                for action in actions:
                    value = Fraction(0)
                    for outcome in iter_outcomes(kernel, state, action):
                        probability = as_fraction(outcome.probability)
                        branch = outcome_reward(outcome, weights)
                        stopped = outcome.failure or outcome.terminal or is_stopped(
                            kernel, outcome.next_state, goal
                        )
                        if not stopped:
                            successor = partition.cell_of(outcome.next_state)
                            branch += upper[(remaining - 1, successor)]
                        value += probability * branch
                    candidates.append(value)
            upper[(remaining, cell)] = max(candidates) if candidates else Fraction(0)
    return upper


def audit_abstract_policy(
    kernel: Any,
    query: Any,
    envelope: ExactRealizationEnvelope,
    policy: FiniteHorizonPolicy[Any, Any],
    *,
    regret_tolerance: Fraction = Fraction(1, 20),
    goal_cells: Iterable[Hashable] = (),
    unrestricted_reward_upper: Fraction | int | None = None,
) -> AbstractPolicyAudit:
    """Audit a complete lifted policy against unrestricted ground behaviour.

    The nominal model is deliberately absent from this function.  The lower
    reward and upper failure recursions use only exact ground realizations,
    while ``U_all`` considers every ground action, including those omitted by
    the semantic-action concretizer.
    """

    validate_query(kernel, query)
    partition = envelope.partition
    if envelope.horizon != int(kernel.horizon):
        raise ValueError("envelope and kernel horizons disagree")
    horizon = query_horizon(kernel, query)
    weights = reward_weights(query)
    goals = set(goal_cells)
    issues: list[AuditIssue] = []
    issue_keys: set[tuple[str, Hashable, int]] = set()
    memo: dict[tuple[int, Hashable], tuple[Fraction, Fraction] | None] = {}

    def record(code: str, cell: Hashable, remaining: int, detail: str) -> None:
        key = (code, cell, remaining)
        if key not in issue_keys:
            issue_keys.add(key)
            issues.append(AuditIssue(code, cell, remaining, detail))

    def bounds(cell: Hashable, remaining: int) -> tuple[Fraction, Fraction] | None:
        key = (remaining, cell)
        if key in memo:
            return memo[key]
        members = partition.members(cell)
        if remaining <= 0 or cell in goals or all(kernel.is_terminal(state) for state in members):
            memo[key] = (Fraction(0), Fraction(0))
            return memo[key]
        try:
            action = policy.action(cell, remaining)
        except KeyError:
            record("POLICY_UNDEFINED", cell, remaining, "no semantic action for reachable pair")
            memo[key] = None
            return None
        try:
            realizations = envelope.realizations(cell, action)
        except KeyError:
            record(
                "ACTION_UNAVAILABLE",
                cell,
                remaining,
                f"semantic action {action!r} lacks a common exact realization",
            )
            memo[key] = None
            return None

        reward_values: list[Fraction] = []
        failure_values: list[Fraction] = []
        active_states = {realization.state for realization in realizations}
        for state in members:
            if kernel.is_terminal(state):
                reward_values.append(Fraction(0))
                failure_values.append(Fraction(0))
            elif state not in active_states:
                record(
                    "REALIZATION_MISSING",
                    cell,
                    remaining,
                    f"no exact realization for nonterminal state {state!r}",
                )
                memo[key] = None
                return None
        for realization in realizations:
            reward = realization.reward(weights)
            failure = realization.failure_probability
            for successor, probability in realization.successor_probabilities:
                continuation = bounds(successor, remaining - 1)
                if continuation is None:
                    memo[key] = None
                    return None
                reward += probability * continuation[0]
                failure += probability * continuation[1]
            reward_values.append(reward)
            failure_values.append(failure)
        if not reward_values:
            record("REALIZATION_MISSING", cell, remaining, "cell has no auditable realization")
            memo[key] = None
            return None
        memo[key] = (min(reward_values), max(failure_values))
        return memo[key]

    if unrestricted_reward_upper is None:
        upper = unrestricted_upper_envelope(kernel, query, partition)
        root_upper = Fraction(0)
    else:
        if isinstance(unrestricted_reward_upper, bool) or not isinstance(
            unrestricted_reward_upper, (int, Fraction)
        ):
            raise TypeError(
                "unrestricted_reward_upper must be an exact int or Fraction"
            )
        root_upper = Fraction(unrestricted_reward_upper)
        if root_upper < 0:
            raise ValueError("unrestricted_reward_upper must be nonnegative")
        upper = None
    root_lower = Fraction(0)
    root_failure = Fraction(0)
    complete = True
    for probability, state in query_initial_distribution(kernel, query):
        cell = partition.cell_of(state)
        if upper is not None:
            root_upper += probability * upper[(horizon, cell)]
        result = bounds(cell, horizon)
        if result is None:
            complete = False
        else:
            root_lower += probability * result[0]
            root_failure += probability * result[1]

    if complete and root_upper < root_lower:
        raise ValueError(
            "unrestricted_reward_upper is below the audited policy reward lower bound"
        )
    tolerance = as_fraction(regret_tolerance)
    risk_tolerance = as_fraction(query.delta)
    regret = root_upper - root_lower if complete else None
    certified = bool(
        complete
        and regret is not None
        and regret <= tolerance
        and root_failure <= risk_tolerance
    )
    reachable = tuple(
        CellPolicyBound(cell, remaining, result[0], result[1])
        for (remaining, cell), result in sorted(
            memo.items(), key=lambda item: (-item[0][0], repr(item[0][1]))
        )
        if result is not None
    )
    issues.sort(key=lambda issue: (-issue.remaining, repr(issue.cell), issue.code))
    return AbstractPolicyAudit(
        unrestricted_reward_upper=root_upper,
        lifted_reward_lower=root_lower if complete else None,
        lifted_failure_upper=root_failure if complete else None,
        regret_upper=regret,
        regret_tolerance=tolerance,
        risk_tolerance=risk_tolerance,
        certified=certified,
        issues=tuple(issues),
        reachable_bounds=reachable,
    )
