"""Nominal quotient construction and independent exact realization envelopes."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Callable, Hashable, Iterable, Mapping

from .partition import Partition


ActionLabeler = Callable[[Hashable, Hashable], Hashable]
Concretizer = Callable[[Hashable, Hashable], Iterable[tuple[Fraction, Hashable]]]
SemanticActionProvider = Callable[[Hashable], Iterable[Hashable]]


def _as_fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, float):
        return Fraction(str(value))
    return Fraction(value)


def _deterministic_order(values: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(sorted(values, key=repr))


def _iter_outcomes(kernel: Any, state: Hashable, action: Hashable) -> tuple[Any, ...]:
    raw = kernel.step(state, action)
    outcomes = (raw,) if hasattr(raw, "probability") else tuple(raw)
    if not outcomes:
        raise ValueError(f"action {action!r} at state {state!r} has no outcomes")
    probabilities = tuple(_as_fraction(outcome.probability) for outcome in outcomes)
    if sum(probabilities, Fraction(0)) != 1 or any(value < 0 for value in probabilities):
        raise ValueError("outcome probabilities must be non-negative and sum to one")
    return outcomes


def identity_action_label(_state: Hashable, action: Hashable) -> Hashable:
    return action


@dataclass(frozen=True)
class GroundRealization:
    """Exact one-step behaviour of one ground state under a semantic action."""

    state: Hashable
    reward_features: tuple[tuple[str, Fraction], ...]
    successor_probabilities: tuple[tuple[Hashable, Fraction], ...]
    failure_probability: Fraction
    termination_probability: Fraction

    def reward(self, weights: Mapping[str, Fraction]) -> Fraction:
        return sum(
            (weights.get(name, Fraction(0)) * value for name, value in self.reward_features),
            Fraction(0),
        )


@dataclass(frozen=True)
class EnvelopeEntry:
    cell: Hashable
    action: Hashable
    realizations: tuple[GroundRealization, ...]


@dataclass(frozen=True)
class ExactRealizationEnvelope:
    """All correlated ground realizations; no nominal averaging is performed."""

    partition: Partition
    horizon: int
    entries: tuple[EnvelopeEntry, ...]
    action_labeler: ActionLabeler | None = field(compare=False, repr=False)
    semantic_action_provider: SemanticActionProvider = field(compare=False, repr=False)
    concretizer: Concretizer = field(compare=False, repr=False)

    def actions(self, cell: Hashable) -> tuple[Hashable, ...]:
        return _deterministic_order(entry.action for entry in self.entries if entry.cell == cell)

    def realizations(self, cell: Hashable, action: Hashable) -> tuple[GroundRealization, ...]:
        for entry in self.entries:
            if entry.cell == cell and entry.action == action:
                return entry.realizations
        raise KeyError(f"no exact realization envelope for cell={cell!r}, action={action!r}")


@dataclass(frozen=True)
class NominalActionModel:
    """Arithmetic-average model used only to propose and rank policies."""

    reward_features: tuple[tuple[str, Fraction], ...]
    successor_probabilities: tuple[tuple[Hashable, Fraction], ...]
    failure_probability: Fraction
    termination_probability: Fraction
    realization_count: int

    def reward(self, weights: Mapping[str, Fraction]) -> Fraction:
        return sum(
            (weights.get(name, Fraction(0)) * value for name, value in self.reward_features),
            Fraction(0),
        )


@dataclass(frozen=True)
class NominalEntry:
    cell: Hashable
    action: Hashable
    model: NominalActionModel


@dataclass(frozen=True)
class NominalQuotient:
    partition: Partition
    horizon: int
    entries: tuple[NominalEntry, ...]

    @property
    def cells(self) -> tuple[Hashable, ...]:
        return self.partition.cell_ids

    def actions(self, cell: Hashable) -> tuple[Hashable, ...]:
        return _deterministic_order(entry.action for entry in self.entries if entry.cell == cell)

    def transition(self, cell: Hashable, action: Hashable) -> NominalActionModel:
        for entry in self.entries:
            if entry.cell == cell and entry.action == action:
                return entry.model
        raise KeyError(f"no nominal transition for cell={cell!r}, action={action!r}")


@dataclass(frozen=True)
class QuotientModels:
    """Reusable abstract planning model (RAPM).

    The proposal model and the certificate envelope deliberately travel
    together, while remaining distinct typed objects so nominal quantities
    cannot accidentally be used as audit bounds.
    """

    nominal: NominalQuotient
    envelope: ExactRealizationEnvelope


# The specifications use both the expanded name and the short form.  Keeping
# these aliases avoids introducing a second wrapper type with identical
# semantics.
ReusableAbstractPlanningModel = QuotientModels
RAPM = QuotientModels


def _default_concretizer(
    kernel: Any,
    labeler: ActionLabeler,
) -> Concretizer:
    def concretize(state: Hashable, semantic_action: Hashable) -> tuple[tuple[Fraction, Hashable], ...]:
        matches = tuple(
            action
            for action in kernel.actions(state)
            if labeler(state, action) == semantic_action
        )
        if not matches:
            return ()
        probability = Fraction(1, len(matches))
        return tuple((probability, action) for action in _deterministic_order(matches))

    return concretize


def _normalise_concretizer(
    kernel: Any,
    state: Hashable,
    semantic_action: Hashable,
    labeler: ActionLabeler | None,
    concretizer: Concretizer,
) -> tuple[tuple[Fraction, Hashable], ...]:
    raw = tuple(concretizer(state, semantic_action))
    if not raw:
        raise ValueError(
            f"concretizer has empty support at state={state!r}, action={semantic_action!r}"
        )
    distribution = tuple((_as_fraction(probability), action) for probability, action in raw)
    if any(probability < 0 for probability, _ in distribution):
        raise ValueError("concretizer probabilities must be non-negative")
    if sum((probability for probability, _ in distribution), Fraction(0)) != 1:
        raise ValueError("concretizer probabilities must sum to one")
    available = set(kernel.actions(state))
    for _, action in distribution:
        if action not in available:
            raise ValueError(f"concretizer selected unavailable ground action {action!r}")
        if labeler is not None and labeler(state, action) != semantic_action:
            raise ValueError("concretizer action does not map to the requested semantic action")
    return distribution


def _available_semantic_actions(
    kernel: Any,
    states: tuple[Hashable, ...],
    provider: SemanticActionProvider,
) -> tuple[Hashable, ...]:
    active = tuple(state for state in states if not kernel.is_terminal(state))
    if not active:
        return ()
    common: set[Hashable] | None = None
    for state in active:
        labels = set(provider(state))
        common = labels if common is None else common & labels
    return _deterministic_order(common or ())


def _validate_failure_cell_isolation(
    kernel: Any,
    states: tuple[Hashable, ...],
    partition: Partition,
) -> None:
    """Reject a partition that aliases an explicit failure target.

    Failure is an absorbing semantic event in the audit contract.  Discovering
    its target states from the public transition interface keeps the quotient
    builder domain-agnostic while ensuring a failure state cannot share a cell
    with an ordinary state.
    """

    failure_targets: set[Hashable] = set()
    for state in states:
        if kernel.is_terminal(state):
            continue
        for action in kernel.actions(state):
            for outcome in _iter_outcomes(kernel, state, action):
                if outcome.failure:
                    failure_targets.add(outcome.next_state)
    unknown = failure_targets - set(states)
    if unknown:
        raise ValueError(f"failure targets are absent from the registered state set: {unknown!r}")
    for failure_state in failure_targets:
        cell = partition.cell_of(failure_state)
        nonfailure_members = set(partition.members(cell)) - failure_targets
        if nonfailure_members:
            raise ValueError(
                "failure state must be isolated from non-failure states; "
                f"cell={cell!r}, failure_state={failure_state!r}, "
                f"nonfailure_members={nonfailure_members!r}"
            )


def _realization(
    kernel: Any,
    partition: Partition,
    state: Hashable,
    semantic_action: Hashable,
    labeler: ActionLabeler | None,
    concretizer: Concretizer,
) -> GroundRealization:
    feature_totals: dict[str, Fraction] = {}
    successor_totals: dict[Hashable, Fraction] = {}
    failure_probability = Fraction(0)
    termination_probability = Fraction(0)
    ground_distribution = _normalise_concretizer(
        kernel, state, semantic_action, labeler, concretizer
    )
    for ground_probability, action in ground_distribution:
        for outcome in _iter_outcomes(kernel, state, action):
            probability = ground_probability * _as_fraction(outcome.probability)
            raw_features = outcome.reward_features
            feature_items = raw_features.items() if isinstance(raw_features, Mapping) else raw_features
            for name, value in feature_items:
                key = str(name)
                feature_totals[key] = feature_totals.get(key, Fraction(0)) + probability * _as_fraction(value)
            stopped = bool(outcome.failure or outcome.terminal or kernel.is_terminal(outcome.next_state))
            if outcome.failure:
                failure_probability += probability
            if stopped:
                termination_probability += probability
            else:
                successor = partition.cell_of(outcome.next_state)
                successor_totals[successor] = successor_totals.get(successor, Fraction(0)) + probability
    if sum(successor_totals.values(), termination_probability) != 1:
        raise AssertionError("realization continuation and termination mass must sum to one")
    return GroundRealization(
        state=state,
        reward_features=tuple(sorted(feature_totals.items())),
        successor_probabilities=tuple(sorted(successor_totals.items(), key=lambda item: repr(item[0]))),
        failure_probability=failure_probability,
        termination_probability=termination_probability,
    )


def build_exact_realization_envelope(
    kernel: Any,
    states: Iterable[Hashable],
    partition: Partition,
    *,
    action_labeler: ActionLabeler | None = None,
    concretizer: Concretizer | None = None,
    semantic_adapter: Any | None = None,
) -> ExactRealizationEnvelope:
    """Build the certificate object without computing nominal averages."""

    registered = set(partition.states)
    requested_states = tuple(states)
    requested = set(requested_states)
    if requested != registered:
        missing = requested - registered
        extra = registered - requested
        raise ValueError(f"partition/state mismatch; missing={missing!r}, extra={extra!r}")
    _validate_failure_cell_isolation(kernel, requested_states, partition)
    if semantic_adapter is not None:
        if action_labeler is not None or concretizer is not None:
            raise ValueError(
                "semantic_adapter cannot be combined with explicit action_labeler/concretizer"
            )

        def provider(state: Hashable) -> Iterable[Hashable]:
            return semantic_adapter.labels(kernel, state)

        def adapter_concretizer(
            state: Hashable, semantic_action: Hashable
        ) -> Iterable[tuple[Fraction, Hashable]]:
            return semantic_adapter.concretize(kernel, state, semantic_action)

        labeler: ActionLabeler | None = None
        fixed_concretizer = adapter_concretizer
    else:
        labeler = action_labeler or identity_action_label

        def provider(state: Hashable) -> Iterable[Hashable]:
            return (labeler(state, action) for action in kernel.actions(state))

        fixed_concretizer = concretizer or _default_concretizer(kernel, labeler)
    entries: list[EnvelopeEntry] = []
    for cell in partition.cell_ids:
        members = partition.members(cell)
        active_members = tuple(state for state in members if not kernel.is_terminal(state))
        for semantic_action in _available_semantic_actions(kernel, members, provider):
            realizations = tuple(
                _realization(
                    kernel,
                    partition,
                    state,
                    semantic_action,
                    labeler,
                    fixed_concretizer,
                )
                for state in active_members
            )
            entries.append(EnvelopeEntry(cell, semantic_action, realizations))
    entries.sort(key=lambda entry: (repr(entry.cell), repr(entry.action)))
    return ExactRealizationEnvelope(
        partition=partition,
        horizon=int(kernel.horizon),
        entries=tuple(entries),
        action_labeler=labeler,
        semantic_action_provider=provider,
        concretizer=fixed_concretizer,
    )


def build_nominal_quotient(envelope: ExactRealizationEnvelope) -> NominalQuotient:
    """Average an exact envelope into a policy-proposal model."""

    nominal_entries: list[NominalEntry] = []
    for entry in envelope.entries:
        if not entry.realizations:
            continue
        count = len(entry.realizations)
        feature_names = sorted(
            {name for realization in entry.realizations for name, _ in realization.reward_features}
        )
        successor_cells = _deterministic_order(
            cell
            for realization in entry.realizations
            for cell, _ in realization.successor_probabilities
        )
        successor_cells = tuple(dict.fromkeys(successor_cells))
        reward_features = tuple(
            (
                name,
                sum(
                    (dict(realization.reward_features).get(name, Fraction(0)) for realization in entry.realizations),
                    Fraction(0),
                )
                / count,
            )
            for name in feature_names
        )
        successor_probabilities = tuple(
            (
                cell,
                sum(
                    (
                        dict(realization.successor_probabilities).get(cell, Fraction(0))
                        for realization in entry.realizations
                    ),
                    Fraction(0),
                )
                / count,
            )
            for cell in successor_cells
        )
        successor_probabilities = tuple(
            (cell, probability)
            for cell, probability in successor_probabilities
            if probability > 0
        )
        nominal_entries.append(
            NominalEntry(
                cell=entry.cell,
                action=entry.action,
                model=NominalActionModel(
                    reward_features=reward_features,
                    successor_probabilities=successor_probabilities,
                    failure_probability=sum(
                        (realization.failure_probability for realization in entry.realizations),
                        Fraction(0),
                    )
                    / count,
                    termination_probability=sum(
                        (realization.termination_probability for realization in entry.realizations),
                        Fraction(0),
                    )
                    / count,
                    realization_count=count,
                ),
            )
        )
    nominal_entries.sort(key=lambda entry: (repr(entry.cell), repr(entry.action)))
    return NominalQuotient(envelope.partition, envelope.horizon, tuple(nominal_entries))


def build_quotient_models(
    kernel: Any,
    states: Iterable[Hashable],
    partition: Partition,
    *,
    action_labeler: ActionLabeler | None = None,
    concretizer: Concretizer | None = None,
    semantic_adapter: Any | None = None,
) -> QuotientModels:
    envelope = build_exact_realization_envelope(
        kernel,
        states,
        partition,
        action_labeler=action_labeler,
        concretizer=concretizer,
        semantic_adapter=semantic_adapter,
    )
    return QuotientModels(build_nominal_quotient(envelope), envelope)
