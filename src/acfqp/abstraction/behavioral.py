"""Exact model-oracle behavioural state/action minimisation.

This module constructs the coarsest stable partition reached by ordinary
partition refinement when primitive action *names* are irrelevant.  At each
round an action is represented only by its exact expected reward-feature
vector, one-time failure/termination probabilities, and distribution over the
previous round's cells.  A state's controlled behaviour is the set of those
action signatures.  Primitive actions with the same final signature are then
concretized uniformly over their distinct supports.

The construction is an exact-model oracle baseline.  It can discover
behavioural equivalences which are not supplied as a group action, but it is
not a learned abstraction and it does not invent human-readable predicates.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Hashable, Iterable

from .partition import Partition
from .quotient import QuotientModels, build_quotient_models


def _fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, float):
        return Fraction(str(value))
    return Fraction(value)


def _ordered(values: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(sorted(values, key=repr))


def _outcomes(kernel: Any, state: Hashable, action: Hashable) -> tuple[Any, ...]:
    raw = kernel.step(state, action)
    outcomes = (raw,) if hasattr(raw, "probability") else tuple(raw)
    if not outcomes:
        raise ValueError("an exact behavioural action must have an outcome")
    probabilities = tuple(_fraction(outcome.probability) for outcome in outcomes)
    if any(probability <= 0 for probability in probabilities):
        raise ValueError("exact behavioural outcomes must have positive mass")
    if sum(probabilities, Fraction(0)) != 1:
        raise ValueError("exact behavioural outcome mass must equal one")
    return outcomes


@dataclass(frozen=True, order=True, slots=True)
class BehavioralCellId:
    """Canonical integer cell identifier for one refinement result."""

    index: int


@dataclass(frozen=True, slots=True)
class BehavioralActionSignature:
    """One exact action's quotient-relevant controlled behaviour."""

    reward_features: tuple[tuple[str, Fraction], ...]
    failure_probability: Fraction
    termination_probability: Fraction
    successor_probabilities: tuple[tuple[BehavioralCellId, Fraction], ...]


@dataclass(frozen=True, slots=True)
class BehavioralRefinementStep:
    iteration: int
    cell_count: int
    partition_signature: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class BehavioralActionAssignment:
    state: Hashable
    ground_action: Hashable
    semantic_action: BehavioralActionSignature


@dataclass(frozen=True, slots=True)
class BehavioralSemanticAdapter:
    """Frozen exact action-signature system produced by minimisation."""

    assignments: tuple[BehavioralActionAssignment, ...]

    def labels(self, kernel: Any, state: Hashable) -> tuple[BehavioralActionSignature, ...]:
        available = set(kernel.actions(state))
        records = tuple(
            record
            for record in self.assignments
            if record.state == state and record.ground_action in available
        )
        if len(records) != len(available):
            if not available and kernel.is_terminal(state):
                return ()
            raise ValueError("behavioural adapter is incomplete for the supplied kernel/state")
        return _ordered({record.semantic_action for record in records})

    def concretize(
        self,
        kernel: Any,
        state: Hashable,
        label: BehavioralActionSignature,
    ) -> tuple[tuple[Fraction, Hashable], ...]:
        available = set(kernel.actions(state))
        actions = _ordered(
            record.ground_action
            for record in self.assignments
            if record.state == state
            and record.ground_action in available
            and record.semantic_action == label
        )
        if not actions:
            raise ValueError("behavioural semantic action is unavailable at this state")
        probability = Fraction(1, len(actions))
        return tuple((probability, action) for action in actions)

    def features(
        self,
        _kernel: Any,
        _state: Hashable,
    ) -> tuple[tuple[str, Fraction], ...]:
        """The exact oracle adapter does not expose a predicate grammar."""

        return ()


@dataclass(frozen=True, slots=True)
class ExactBehavioralQuotient:
    partition: Partition
    semantic_adapter: BehavioralSemanticAdapter
    refinement_trace: tuple[BehavioralRefinementStep, ...]
    failure_targets: tuple[Hashable, ...]
    quotient_models: QuotientModels

    @property
    def ground_state_count(self) -> int:
        return len(self.partition.states)

    @property
    def cell_count(self) -> int:
        return len(self.partition.cell_ids)


def _failure_targets(kernel: Any, states: tuple[Hashable, ...]) -> tuple[Hashable, ...]:
    registered = set(states)
    targets: set[Hashable] = set()
    for state in states:
        if kernel.is_terminal(state):
            continue
        for action in _ordered(kernel.actions(state)):
            for outcome in _outcomes(kernel, state, action):
                if outcome.failure:
                    targets.add(outcome.next_state)
    missing = targets - registered
    if missing:
        raise ValueError(
            "failure targets are absent from behavioural quotient coverage: "
            f"{_ordered(missing)!r}"
        )
    return _ordered(targets)


def _terminal_kind(
    kernel: Any,
    state: Hashable,
    failures: set[Hashable],
) -> str:
    if not kernel.is_terminal(state):
        return "active"
    return "failure" if state in failures else "terminal"


def _canonical_partition(
    states: tuple[Hashable, ...],
    raw_signatures: dict[Hashable, Hashable],
) -> Partition:
    unique = _ordered(set(raw_signatures.values()))
    identifiers = {
        signature: BehavioralCellId(index)
        for index, signature in enumerate(unique)
    }
    return Partition.from_mapping(
        {state: identifiers[raw_signatures[state]] for state in states}
    )


def _action_signature(
    kernel: Any,
    partition: Partition,
    state: Hashable,
    action: Hashable,
) -> BehavioralActionSignature:
    rewards: dict[str, Fraction] = {}
    successors: dict[BehavioralCellId, Fraction] = {}
    failure = Fraction(0)
    termination = Fraction(0)
    for outcome in _outcomes(kernel, state, action):
        probability = _fraction(outcome.probability)
        raw_features = outcome.reward_features
        items = raw_features.items() if hasattr(raw_features, "items") else raw_features
        for name, value in items:
            key = str(name)
            rewards[key] = rewards.get(key, Fraction(0)) + probability * _fraction(value)
        stopped = bool(
            outcome.failure
            or outcome.terminal
            or kernel.is_terminal(outcome.next_state)
        )
        if outcome.failure:
            failure += probability
        if stopped:
            termination += probability
        else:
            cell = partition.cell_of(outcome.next_state)
            if not isinstance(cell, BehavioralCellId):
                raise TypeError("behavioural refinement requires BehavioralCellId cells")
            successors[cell] = successors.get(cell, Fraction(0)) + probability
    if sum(successors.values(), termination) != 1:
        raise AssertionError("continuation and termination mass must equal one")
    return BehavioralActionSignature(
        tuple(sorted(rewards.items())),
        failure,
        termination,
        tuple(sorted(successors.items(), key=lambda item: item[0].index)),
    )


def _same_blocks(left: Partition, right: Partition) -> bool:
    return left.signature() == right.signature()


def build_exact_behavioral_quotient(
    kernel: Any,
    states: Iterable[Hashable],
    *,
    max_refinement_rounds: int | None = None,
) -> ExactBehavioralQuotient:
    """Construct and independently materialize an exact behavioural quotient.

    The finite refinement is monotone because each active state's next
    signature includes its previous cell.  The default round cap is the number
    of registered states: a stricter cap can be supplied for an explicit
    resource contract, but exhausting it is always an error rather than a
    silently approximate result.
    """

    registered = _ordered(states)
    if not registered or len(set(registered)) != len(registered):
        raise ValueError("behavioural quotient states must be nonempty and unique")
    failures = _failure_targets(kernel, registered)
    failure_set = set(failures)
    initial_raw = {
        state: ("terminal", _terminal_kind(kernel, state, failure_set))
        if kernel.is_terminal(state)
        else ("active",)
        for state in registered
    }
    partition = _canonical_partition(registered, initial_raw)
    trace = [
        BehavioralRefinementStep(0, len(partition.cell_ids), partition.signature())
    ]
    cap = len(registered) if max_refinement_rounds is None else max_refinement_rounds
    if cap <= 0:
        raise ValueError("behavioural refinement round cap must be positive")

    for iteration in range(1, cap + 1):
        raw: dict[Hashable, Hashable] = {}
        for state in registered:
            if kernel.is_terminal(state):
                raw[state] = (
                    "terminal",
                    _terminal_kind(kernel, state, failure_set),
                )
                continue
            action_signatures = {
                _action_signature(kernel, partition, state, action)
                for action in _ordered(kernel.actions(state))
            }
            if not action_signatures:
                raise ValueError(
                    "a nonterminal behavioural state has no primitive action"
                )
            raw[state] = (
                "active",
                partition.cell_of(state),
                _ordered(action_signatures),
            )
        refined = _canonical_partition(registered, raw)
        trace.append(
            BehavioralRefinementStep(
                iteration,
                len(refined.cell_ids),
                refined.signature(),
            )
        )
        if _same_blocks(partition, refined):
            partition = refined
            break
        if len(refined.cell_ids) < len(partition.cell_ids):
            raise AssertionError("behavioural refinement unexpectedly merged cells")
        partition = refined
    else:
        raise RuntimeError("exact behavioural refinement exhausted its round cap")

    assignments = tuple(
        BehavioralActionAssignment(
            state,
            action,
            _action_signature(kernel, partition, state, action),
        )
        for state in registered
        if not kernel.is_terminal(state)
        for action in _ordered(kernel.actions(state))
    )
    adapter = BehavioralSemanticAdapter(assignments)
    models = build_quotient_models(
        kernel,
        registered,
        partition,
        semantic_adapter=adapter,
    )
    for entry in models.envelope.entries:
        behaviours = {
            (
                realization.reward_features,
                realization.failure_probability,
                realization.termination_probability,
                realization.successor_probabilities,
            )
            for realization in entry.realizations
        }
        if len(behaviours) != 1:
            raise AssertionError(
                "stable behavioural quotient produced a non-singleton exact envelope"
            )
    return ExactBehavioralQuotient(
        partition,
        adapter,
        tuple(trace),
        failures,
        models,
    )


__all__ = [
    "BehavioralActionAssignment",
    "BehavioralActionSignature",
    "BehavioralCellId",
    "BehavioralRefinementStep",
    "BehavioralSemanticAdapter",
    "ExactBehavioralQuotient",
    "build_exact_behavioral_quotient",
]
