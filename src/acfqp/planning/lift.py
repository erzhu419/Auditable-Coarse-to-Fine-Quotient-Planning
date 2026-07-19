"""Exact ground evaluation of semantic policies with fixed concretizers.

The semantic selector remains deterministic.  Any randomness in this module
belongs to the frozen action-realisation mechanism supplied by the semantic
adapter and is integrated into the transition kernel before policy
evaluation.  A stochastic concretizer is therefore never materialised as a
randomized ground policy or replaced by one representative primitive action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import TYPE_CHECKING, Any, Hashable, Mapping

from acfqp.core import Outcome

from .common import (
    as_fraction,
    is_stopped,
    iter_outcomes,
    query_horizon,
    query_initial_distribution,
    validate_query,
)
from .ground import PolicyEvaluation, evaluate_ground_policy
from .policy import FiniteHorizonPolicy

if TYPE_CHECKING:
    from acfqp.abstraction.partition import Partition


ActionDistribution = tuple[tuple[Fraction, Hashable], ...]


def _canonical_reward_features(outcome: Any) -> tuple[tuple[str, Fraction], ...]:
    raw = getattr(outcome, "reward_features", ())
    items = raw.items() if isinstance(raw, Mapping) else raw
    features: dict[str, Fraction] = {}
    for raw_name, raw_value in items:
        name = str(raw_name)
        if name in features:
            raise ValueError(f"duplicate reward feature in outcome: {name!r}")
        features[name] = as_fraction(raw_value)
    return tuple(sorted(features.items()))


@dataclass
class SemanticKernelView:
    """A finite-kernel view whose actions are semantic action labels.

    ``adapter.labels`` defines which deterministic semantic decisions are
    available.  ``adapter.concretize`` defines an exact, fixed distribution
    over legal primitive actions.  Distributions are normalized, duplicate
    primitive actions are coalesced, and the first normalized result is cached
    for the lifetime of this view.
    """

    ground_kernel: Any
    semantic_adapter: Any
    _distribution_cache: dict[tuple[Hashable, Hashable], ActionDistribution] = field(
        default_factory=dict,
        init=False,
        repr=False,
        compare=False,
    )
    _outcome_cache: dict[tuple[Hashable, Hashable], tuple[Outcome[Any], ...]] = field(
        default_factory=dict,
        init=False,
        repr=False,
        compare=False,
    )

    def __getattr__(self, name: str) -> Any:
        """Delegate optional registry and goal APIs to the ground kernel."""

        return getattr(self.ground_kernel, name)

    @property
    def horizon(self) -> int:
        return int(self.ground_kernel.horizon)

    def initial_distribution(self) -> tuple[tuple[Fraction, Hashable], ...]:
        return tuple(self.ground_kernel.initial_distribution())

    def is_terminal(self, state: Hashable) -> bool:
        return bool(self.ground_kernel.is_terminal(state))

    def actions(self, state: Hashable) -> tuple[Hashable, ...]:
        labels = tuple(self.semantic_adapter.labels(self.ground_kernel, state))
        try:
            unique_count = len(set(labels))
        except TypeError as error:
            raise TypeError("semantic action labels must be hashable") from error
        if unique_count != len(labels):
            raise ValueError(f"semantic adapter emitted duplicate labels at state {state!r}")
        return labels

    def concretizer_distribution(
        self,
        state: Hashable,
        semantic_action: Hashable,
    ) -> ActionDistribution:
        """Return the cached exact distribution over distinct primitive actions."""

        key = (state, semantic_action)
        cached = self._distribution_cache.get(key)
        if cached is not None:
            return cached
        if semantic_action not in self.actions(state):
            raise ValueError(
                f"semantic action {semantic_action!r} is unavailable at state {state!r}"
            )

        raw_distribution = tuple(
            self.semantic_adapter.concretize(
                self.ground_kernel,
                state,
                semantic_action,
            )
        )
        if not raw_distribution:
            raise ValueError(
                f"concretizer has empty support at state={state!r}, "
                f"action={semantic_action!r}"
            )
        available = set(self.ground_kernel.actions(state))
        coalesced: dict[Hashable, Fraction] = {}
        for raw_probability, ground_action in raw_distribution:
            probability = as_fraction(raw_probability)
            if probability <= 0:
                raise ValueError("concretizer probabilities must be positive")
            if ground_action not in available:
                raise ValueError(
                    f"concretizer selected unavailable ground action {ground_action!r}"
                )
            coalesced[ground_action] = (
                coalesced.get(ground_action, Fraction(0)) + probability
            )
        if sum(coalesced.values(), Fraction(0)) != 1:
            raise ValueError("concretizer probabilities must sum to one")
        normalized = tuple(
            sorted(
                ((probability, action) for action, probability in coalesced.items()),
                key=lambda item: repr(item[1]),
            )
        )
        self._distribution_cache[key] = normalized
        return normalized

    # The shorter name is useful to callers treating the view itself as an
    # action-realisation system.
    concretize = concretizer_distribution

    def step(
        self,
        state: Hashable,
        semantic_action: Hashable,
    ) -> tuple[Outcome[Any], ...]:
        """Integrate the fixed concretizer and coalesce identical outcome atoms."""

        key = (state, semantic_action)
        cached = self._outcome_cache.get(key)
        if cached is not None:
            return cached

        masses: dict[
            tuple[Hashable, tuple[tuple[str, Fraction], ...], bool, bool],
            Fraction,
        ] = {}
        for action_probability, ground_action in self.concretizer_distribution(
            state, semantic_action
        ):
            for outcome in iter_outcomes(self.ground_kernel, state, ground_action):
                atom = (
                    outcome.next_state,
                    _canonical_reward_features(outcome),
                    bool(outcome.failure),
                    bool(outcome.terminal),
                )
                masses[atom] = masses.get(atom, Fraction(0)) + (
                    action_probability * as_fraction(outcome.probability)
                )

        coalesced = tuple(
            Outcome(
                probability=probability,
                next_state=atom[0],
                reward_features=atom[1],
                failure=atom[2],
                terminal=atom[3],
            )
            for atom, probability in sorted(
                masses.items(),
                key=lambda item: (
                    repr(item[0][0]),
                    repr(item[0][1]),
                    item[0][2],
                    item[0][3],
                ),
            )
        )
        if sum((outcome.probability for outcome in coalesced), Fraction(0)) != 1:
            raise AssertionError("semantic transition probability mass must equal one")
        self._outcome_cache[key] = coalesced
        return coalesced


@dataclass(frozen=True)
class SemanticPolicyLift:
    """Exact realization of an abstract selector on its reachable ground graph."""

    abstract_policy: FiniteHorizonPolicy[Any, Any]
    lifted_semantic_policy: FiniteHorizonPolicy[Any, Any]
    evaluation: PolicyEvaluation
    deterministic_ground_policy: FiniteHorizonPolicy[Any, Any] | None

    @property
    def has_deterministic_ground_materialization(self) -> bool:
        return self.deterministic_ground_policy is not None


def _semantic_view(kernel: Any, semantic_adapter: Any) -> SemanticKernelView:
    if isinstance(kernel, SemanticKernelView):
        if semantic_adapter is not None and semantic_adapter is not kernel.semantic_adapter:
            raise ValueError(
                "a SemanticKernelView cannot be combined with a different adapter"
            )
        return kernel
    if semantic_adapter is None:
        raise TypeError("semantic_adapter is required for a ground kernel")
    return SemanticKernelView(kernel, semantic_adapter)


def lift_semantic_policy_decisions(
    kernel: Any,
    query: Any,
    partition: Partition,
    abstract_policy: FiniteHorizonPolicy[Any, Any],
    semantic_adapter: Any | None = None,
) -> FiniteHorizonPolicy[Any, Any]:
    """Expand abstract decisions to every reachable ground state-time pair."""

    view = _semantic_view(kernel, semantic_adapter)
    validate_query(view, query)
    horizon = query_horizon(view, query)
    goal = getattr(query, "goal", None)
    pending = [
        (horizon, state)
        for probability, state in query_initial_distribution(view, query)
        if probability > 0
    ]
    visited: set[tuple[int, Hashable]] = set()
    decisions: dict[tuple[int, Hashable], Hashable] = {}

    while pending:
        remaining, state = pending.pop()
        marker = (remaining, state)
        if marker in visited:
            continue
        visited.add(marker)
        if remaining <= 0 or is_stopped(view, state, goal):
            continue
        labels = view.actions(state)
        if not labels:
            if tuple(view.ground_kernel.actions(state)):
                raise ValueError(
                    f"semantic adapter exposes no action at active state {state!r}"
                )
            continue
        cell = partition.cell_of(state)
        semantic_action = abstract_policy.action(cell, remaining)
        if semantic_action not in labels:
            raise ValueError(
                f"abstract policy chose unavailable semantic action "
                f"{semantic_action!r} at state {state!r}"
            )
        # Normalize and freeze the concretizer even when this is the last stage.
        view.concretizer_distribution(state, semantic_action)
        decisions[marker] = semantic_action

        if remaining <= 1:
            continue
        for outcome in view.step(state, semantic_action):
            if outcome.failure or outcome.terminal:
                continue
            if is_stopped(view, outcome.next_state, goal):
                continue
            pending.append((remaining - 1, outcome.next_state))

    return FiniteHorizonPolicy.from_mapping(decisions)


def _materialize_deterministic_ground_policy(
    view: SemanticKernelView,
    semantic_policy: FiniteHorizonPolicy[Any, Any],
) -> FiniteHorizonPolicy[Any, Any] | None:
    decisions: dict[tuple[int, Hashable], Hashable] = {}
    for decision in semantic_policy.decisions:
        distribution = view.concretizer_distribution(decision.state, decision.action)
        if len(distribution) != 1 or distribution[0][0] != 1:
            return None
        decisions[(decision.remaining, decision.state)] = distribution[0][1]
    return FiniteHorizonPolicy.from_mapping(decisions)


def evaluate_semantic_policy(
    kernel: Any,
    query: Any,
    partition: Partition,
    abstract_policy: FiniteHorizonPolicy[Any, Any],
    semantic_adapter: Any | None = None,
) -> PolicyEvaluation:
    """Evaluate a semantic selector exactly on the ground state space."""

    view = _semantic_view(kernel, semantic_adapter)
    lifted = lift_semantic_policy_decisions(
        view,
        query,
        partition,
        abstract_policy,
    )
    return evaluate_ground_policy(view, query, lifted)


def lift_semantic_policy(
    kernel: Any,
    query: Any,
    partition: Partition,
    abstract_policy: FiniteHorizonPolicy[Any, Any],
    semantic_adapter: Any | None = None,
) -> SemanticPolicyLift:
    """Lift, evaluate, and optionally materialize a semantic policy exactly."""

    view = _semantic_view(kernel, semantic_adapter)
    lifted = lift_semantic_policy_decisions(
        view,
        query,
        partition,
        abstract_policy,
    )
    evaluation = evaluate_ground_policy(view, query, lifted)
    deterministic = _materialize_deterministic_ground_policy(view, lifted)
    return SemanticPolicyLift(
        abstract_policy=abstract_policy,
        lifted_semantic_policy=lifted,
        evaluation=evaluation,
        deterministic_ground_policy=deterministic,
    )
