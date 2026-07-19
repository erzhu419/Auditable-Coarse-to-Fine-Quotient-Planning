"""Exact state-time orbit quotients with auditable semantic action lifts.

The implementation is group-generic but is intended for the frozen D4 action
registered by :mod:`acfqp.domains.g2048`.  A quotient state is an orbit at one
remaining horizon; horizons are never merged.  At a representative state,
primitive actions are quotiented by the representative stabilizer.  At a
ground state, a semantic action is concretized uniformly over *distinct*
inverse images through every transporter to the representative.

For an exact automorphism this construction has zero realization-envelope
width.  The high-level API builds the quotient, validates that claim, solves
the exact constrained abstract frontier, evaluates its stochastic ground lift,
and compares it with the unrestricted deterministic J0 oracle.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
from itertools import product
from typing import Callable, Generic, Hashable, Iterable, Mapping, TypeVar

from acfqp.planning.common import (
    as_fraction,
    is_stopped,
    iter_outcomes,
    query_horizon,
    query_initial_distribution,
    reward_weights,
    validate_query,
)
from acfqp.planning.ground import (
    GroundParetoResult,
    ParetoPoint,
    PolicyEvaluation,
    pareto_prune,
    select_constrained,
    solve_ground_pareto,
)
from acfqp.planning.policy import FiniteHorizonPolicy


StateT = TypeVar("StateT", bound=Hashable)
ActionT = TypeVar("ActionT", bound=Hashable)
ElementT = TypeVar("ElementT", bound=Hashable)


EXACT_D4_QUOTIENT_INVARIANT_VIOLATION = (
    "EXACT_D4_QUOTIENT_INVARIANT_VIOLATION"
)


class ExactD4QuotientInvariantViolation(ValueError):
    """A baseline-validation failure that must not trigger CEGAR or fallback."""

    status = EXACT_D4_QUOTIENT_INVARIANT_VIOLATION

    def __init__(self, failures: Iterable[str]):
        self.failures = tuple(str(failure) for failure in failures)
        detail = "; ".join(self.failures) or "unspecified exact-D4 invariant failure"
        super().__init__(f"{self.status}: {detail}")


def _default_key(value: Hashable) -> str:
    return repr(value)


@dataclass(frozen=True)
class FiniteGroupAction(Generic[StateT, ActionT, ElementT]):
    """Small callable contract separating the quotient from a domain module."""

    elements: tuple[ElementT, ...]
    transform_state: Callable[[ElementT, StateT], StateT]
    transform_action: Callable[[ElementT, ActionT], ActionT]
    inverse: Callable[[ElementT], ElementT]
    state_key: Callable[[StateT], str] = _default_key
    action_key: Callable[[ActionT], str] = _default_key

    def __post_init__(self) -> None:
        if not self.elements:
            raise ValueError("finite group action requires at least one element")
        if len(set(self.elements)) != len(self.elements):
            raise ValueError("finite group element registry contains duplicates")

    def state_orbit(self, state: StateT) -> tuple[StateT, ...]:
        images = {self.transform_state(element, state) for element in self.elements}
        return tuple(sorted(images, key=lambda item: (self.state_key(item), repr(item))))

    def representative(self, state: StateT) -> StateT:
        return self.state_orbit(state)[0]

    def stabilizer(self, state: StateT) -> tuple[ElementT, ...]:
        return tuple(
            element
            for element in self.elements
            if self.transform_state(element, state) == state
        )

    def transporters(self, state: StateT, target: StateT) -> tuple[ElementT, ...]:
        return tuple(
            element
            for element in self.elements
            if self.transform_state(element, state) == target
        )


class OrbitCellKind(str, Enum):
    ACTIVE = "active_orbit"
    TERMINAL = "terminal_orbit"
    FAILURE = "absorbing_failure"


@dataclass(frozen=True, slots=True)
class StateTimeOrbitId:
    remaining: int
    kind: OrbitCellKind
    representative_key: str


@dataclass(frozen=True)
class StateTimeOrbit(Generic[StateT, ElementT]):
    cell_id: StateTimeOrbitId
    representative: StateT | None
    members: tuple[StateT, ...]
    stabilizer: tuple[ElementT, ...]
    terminal: bool
    failure: bool


@dataclass(frozen=True, slots=True)
class StateTimeAssignment(Generic[StateT]):
    remaining: int
    state: StateT
    cell_id: StateTimeOrbitId


@dataclass(frozen=True, slots=True)
class StabilizerActionOrbitLabel:
    """Stable semantic label determined at one canonical state representative."""

    representative_state_key: str
    action_keys: tuple[str, ...]


@dataclass(frozen=True)
class StabilizerActionOrbit(Generic[StateT, ActionT, ElementT]):
    cell_id: StateTimeOrbitId
    label: StabilizerActionOrbitLabel
    representative_state: StateT
    representative_actions: tuple[ActionT, ...]
    canonical_action: ActionT
    stabilizer: tuple[ElementT, ...]


@dataclass(frozen=True)
class InverseActionConcretization(Generic[StateT, ActionT, ElementT]):
    """The exact ``K_x`` distribution for one state and semantic action."""

    cell_id: StateTimeOrbitId
    state: StateT
    label: StabilizerActionOrbitLabel
    transporters_to_representative: tuple[ElementT, ...]
    action_distribution: tuple[tuple[Fraction, ActionT], ...]


@dataclass(frozen=True)
class OrbitRealization(Generic[StateT]):
    cell_id: StateTimeOrbitId
    state: StateT
    label: StabilizerActionOrbitLabel
    reward_features: tuple[tuple[str, Fraction], ...]
    successor_probabilities: tuple[tuple[StateTimeOrbitId, Fraction], ...]
    failure_probability: Fraction
    termination_probability: Fraction


@dataclass(frozen=True)
class ExactOrbitTransition:
    cell_id: StateTimeOrbitId
    label: StabilizerActionOrbitLabel
    reward_features: tuple[tuple[str, Fraction], ...]
    successor_probabilities: tuple[tuple[StateTimeOrbitId, Fraction], ...]
    failure_probability: Fraction
    termination_probability: Fraction

    def reward(self, weights: Mapping[str, Fraction]) -> Fraction:
        return sum(
            (weights.get(name, Fraction(0)) * value for name, value in self.reward_features),
            Fraction(0),
        )


@dataclass(frozen=True)
class OrbitEnvelopeWidth:
    cell_id: StateTimeOrbitId
    label: StabilizerActionOrbitLabel
    reward_feature_widths: tuple[tuple[str, Fraction], ...]
    failure_width: Fraction
    termination_width: Fraction
    successor_total_variation_width: Fraction

    @property
    def zero(self) -> bool:
        return (
            all(width == 0 for _, width in self.reward_feature_widths)
            and self.failure_width == 0
            and self.termination_width == 0
            and self.successor_total_variation_width == 0
        )


@dataclass(frozen=True)
class OrbitAutomorphismCheck(Generic[StateT, ActionT, ElementT]):
    remaining: int
    state: StateT
    action: ActionT
    element: ElementT
    transformed_state: StateT
    transformed_action: ActionT
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class OrbitStateAutomorphismCheck(Generic[StateT, ElementT]):
    remaining: int
    state: StateT
    element: ElementT
    transformed_state: StateT
    terminal_semantics_preserved: bool
    failure_semantics_preserved: bool
    legal_action_set_preserved: bool
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class CanonicalizerChoiceCheck(Generic[StateT]):
    cell_id: StateTimeOrbitId
    label: StabilizerActionOrbitLabel
    alternative_representative: StateT
    transporter_choices_checked: int
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class StateTimeD4Quotient(Generic[StateT, ActionT, ElementT]):
    """Pure-data exact quotient suitable for canonical artifact serialization."""

    horizon: int
    state_time_orbits: tuple[StateTimeOrbit[StateT, ElementT], ...]
    assignments: tuple[StateTimeAssignment[StateT], ...]
    action_orbits: tuple[StabilizerActionOrbit[StateT, ActionT, ElementT], ...]
    concretizations: tuple[InverseActionConcretization[StateT, ActionT, ElementT], ...]
    realizations: tuple[OrbitRealization[StateT], ...]
    transitions: tuple[ExactOrbitTransition, ...]
    envelope_widths: tuple[OrbitEnvelopeWidth, ...]
    state_automorphism_checks: tuple[OrbitStateAutomorphismCheck[StateT, ElementT], ...]
    automorphism_checks: tuple[OrbitAutomorphismCheck[StateT, ActionT, ElementT], ...]
    canonicalizer_choice_checks: tuple[CanonicalizerChoiceCheck[StateT], ...]

    def cell_of(self, state: StateT, remaining: int) -> StateTimeOrbitId:
        for assignment in self.assignments:
            if assignment.remaining == remaining and assignment.state == state:
                return assignment.cell_id
        raise KeyError(f"state-time pair is absent from D4 quotient: {(state, remaining)!r}")

    def orbit(self, cell_id: StateTimeOrbitId) -> StateTimeOrbit[StateT, ElementT]:
        for orbit in self.state_time_orbits:
            if orbit.cell_id == cell_id:
                return orbit
        raise KeyError(f"unknown state-time orbit: {cell_id!r}")

    def labels(self, cell_id: StateTimeOrbitId) -> tuple[StabilizerActionOrbitLabel, ...]:
        return tuple(
            action_orbit.label
            for action_orbit in self.action_orbits
            if action_orbit.cell_id == cell_id
        )

    def transition(
        self, cell_id: StateTimeOrbitId, label: StabilizerActionOrbitLabel
    ) -> ExactOrbitTransition:
        for transition in self.transitions:
            if transition.cell_id == cell_id and transition.label == label:
                return transition
        raise KeyError(f"unknown D4 quotient transition: {(cell_id, label)!r}")

    def concretize(
        self,
        state: StateT,
        remaining: int,
        label: StabilizerActionOrbitLabel,
    ) -> tuple[tuple[Fraction, ActionT], ...]:
        cell_id = self.cell_of(state, remaining)
        for record in self.concretizations:
            if record.cell_id == cell_id and record.state == state and record.label == label:
                return record.action_distribution
        raise KeyError(f"semantic action is unavailable at state-time pair: {(state, remaining)!r}")


@dataclass(frozen=True)
class D4QuotientValidation:
    representative_independent: bool
    zero_width_exact_model: bool
    automorphism_exact: bool
    automorphism_check_count: int
    canonicalizer_choice_independent: bool
    distinct_uniform_concretizer: bool
    horizons_separated: bool
    failure_cells_unified: bool
    terminal_nonterminal_separated: bool
    failures: tuple[str, ...]
    envelope_widths: tuple[OrbitEnvelopeWidth, ...]

    @property
    def exact(self) -> bool:
        return not self.failures


@dataclass(frozen=True)
class LiftedOrbitDecision(Generic[StateT, ActionT]):
    cell_id: StateTimeOrbitId
    state: StateT
    label: StabilizerActionOrbitLabel
    action_distribution: tuple[tuple[Fraction, ActionT], ...]


@dataclass(frozen=True)
class LiftedOrbitPolicy(Generic[StateT, ActionT]):
    abstract_policy: FiniteHorizonPolicy[StateTimeOrbitId, StabilizerActionOrbitLabel]
    decisions: tuple[LiftedOrbitDecision[StateT, ActionT], ...]


@dataclass(frozen=True, slots=True)
class D4CompressionCounts:
    ground_state_time_count: int
    quotient_state_time_count: int
    ground_legal_action_count: int
    semantic_action_orbit_count: int
    distinct_concretizer_support_count: int
    state_compression_ratio: Fraction
    action_compression_ratio: Fraction

    @property
    def strict_state_compression(self) -> bool:
        return self.ground_state_time_count > self.quotient_state_time_count

    @property
    def strict_action_compression(self) -> bool:
        return self.ground_legal_action_count > self.semantic_action_orbit_count


@dataclass(frozen=True)
class StateTimeValueCheck(Generic[StateT]):
    cell_id: StateTimeOrbitId
    state: StateT
    abstract_feasible: bool
    ground_feasible: bool
    abstract_value: Fraction | None
    abstract_risk: Fraction | None
    lifted_value: Fraction | None
    lifted_risk: Fraction | None
    ground_value: Fraction | None
    ground_risk: Fraction | None
    abstract_frontier_signature: tuple[tuple[Fraction, Fraction], ...]
    ground_frontier_signature: tuple[tuple[Fraction, Fraction], ...]
    frontier_exact: bool
    abstract_unconstrained_value: Fraction
    lifted_unconstrained_value: Fraction
    ground_unconstrained_value: Fraction
    unconstrained_value_exact: bool
    constrained_result_exact: bool
    exact_match: bool


@dataclass(frozen=True)
class ExactD4QuotientReport(Generic[StateT, ActionT, ElementT]):
    """High-level exact baseline result consumed by tests and artifact runners."""

    quotient: StateTimeD4Quotient[StateT, ActionT, ElementT]
    validation: D4QuotientValidation
    abstract_frontier: tuple[ParetoPoint, ...]
    abstract_selected_policy: FiniteHorizonPolicy[
        StateTimeOrbitId, StabilizerActionOrbitLabel
    ] | None
    abstract_value: Fraction | None
    abstract_risk: Fraction | None
    lifted_ground_policy: LiftedOrbitPolicy[StateT, ActionT] | None
    lifted_value: Fraction | None
    lifted_risk: Fraction | None
    ground_frontier: tuple[ParetoPoint, ...]
    ground_selected_policy: FiniteHorizonPolicy[StateT, ActionT] | None
    ground_value: Fraction | None
    ground_risk: Fraction | None
    delta_action: Fraction | None
    compression: D4CompressionCounts
    state_time_value_checks: tuple[StateTimeValueCheck[StateT], ...]
    all_state_time_values_exact: bool
    abstract_composed_candidate_count: int
    ground_composed_candidate_count: int

    @property
    def state_time_orbits(self) -> tuple[StateTimeOrbit[StateT, ElementT], ...]:
        return self.quotient.state_time_orbits

    @property
    def action_orbits(self) -> tuple[StabilizerActionOrbit[StateT, ActionT, ElementT], ...]:
        return self.quotient.action_orbits

    @property
    def concretizations(
        self,
    ) -> tuple[InverseActionConcretization[StateT, ActionT, ElementT], ...]:
        return self.quotient.concretizations

    @property
    def envelope_widths(self) -> tuple[OrbitEnvelopeWidth, ...]:
        return self.validation.envelope_widths


@dataclass(frozen=True)
class _AbstractSolveResult:
    frontier: tuple[ParetoPoint, ...]
    selected: ParetoPoint | None
    composed_candidate_count: int


def _cell_sort_key(cell_id: StateTimeOrbitId) -> tuple[int, str, str]:
    return (-cell_id.remaining, cell_id.kind.value, cell_id.representative_key)


def _unique_by_key(
    values: Iterable[ActionT], key: Callable[[ActionT], str]
) -> tuple[ActionT, ...]:
    result: dict[str, ActionT] = {}
    for value in values:
        identifier = key(value)
        incumbent = result.get(identifier)
        if incumbent is not None and incumbent != value:
            raise ValueError(f"canonical action key collision: {identifier!r}")
        result[identifier] = value
    return tuple(result[identifier] for identifier in sorted(result))


def _enumerate_orbit_closed_state_time_pairs(
    kernel: object,
    query: object,
    group: FiniteGroupAction[StateT, ActionT, ElementT],
    *,
    is_failure: Callable[[StateT], bool] | None,
    state_time_cap: int,
) -> tuple[tuple[tuple[int, StateT], ...], frozenset[tuple[int, StateT]]]:
    horizon = query_horizon(kernel, query)
    pending: list[tuple[int, StateT]] = []
    seen: set[tuple[int, StateT]] = set()
    failure_pairs: set[tuple[int, StateT]] = set()

    def enqueue_orbit(state: StateT, remaining: int, failure: bool = False) -> None:
        orbit = group.state_orbit(state)
        for image in orbit:
            pair = (remaining, image)
            if failure or (is_failure is not None and is_failure(image)):
                failure_pairs.add(pair)
            if pair not in seen:
                if len(seen) >= state_time_cap:
                    raise RuntimeError("D4 state-time orbit closure exceeded its cap")
                seen.add(pair)
                pending.append(pair)

    for probability, state in query_initial_distribution(kernel, query):
        if probability > 0:
            enqueue_orbit(state, horizon)

    goal = getattr(query, "goal", None)
    while pending:
        pending.sort(key=lambda pair: (-pair[0], group.state_key(pair[1]), repr(pair[1])))
        remaining, state = pending.pop(0)
        if remaining <= 0 or is_stopped(kernel, state, goal):
            continue
        actions = tuple(kernel.actions(state))
        if not actions:
            raise ValueError("active state in D4 closure has no legal primitive action")
        for action in actions:
            for outcome in iter_outcomes(kernel, state, action):
                enqueue_orbit(
                    outcome.next_state,
                    remaining - 1,
                    failure=bool(outcome.failure),
                )
    ordered = tuple(
        sorted(seen, key=lambda pair: (-pair[0], group.state_key(pair[1]), repr(pair[1])))
    )
    return ordered, frozenset(failure_pairs)


def _build_orbits(
    kernel: object,
    query: object,
    group: FiniteGroupAction[StateT, ActionT, ElementT],
    pairs: tuple[tuple[int, StateT], ...],
    failure_pairs: frozenset[tuple[int, StateT]],
) -> tuple[
    tuple[StateTimeOrbit[StateT, ElementT], ...],
    tuple[StateTimeAssignment[StateT], ...],
]:
    goal = getattr(query, "goal", None)
    groups: dict[tuple[int, str, str], list[StateT]] = {}
    representatives: dict[tuple[int, str, str], StateT | None] = {}
    for remaining, state in pairs:
        if (remaining, state) in failure_pairs:
            key = (remaining, OrbitCellKind.FAILURE.value, "F")
            representative = None
        else:
            representative = group.representative(state)
            representative_key = group.state_key(representative)
            key = (remaining, "orbit", representative_key)
            incumbent = representatives.get(key)
            if incumbent is not None and incumbent != representative:
                raise ValueError(
                    f"canonical state key collision: {representative_key!r}"
                )
        groups.setdefault(key, []).append(state)
        representatives[key] = representative

    orbits: list[StateTimeOrbit[StateT, ElementT]] = []
    assignments: list[StateTimeAssignment[StateT]] = []
    seen_cell_ids: set[StateTimeOrbitId] = set()
    for key in sorted(groups, key=lambda item: (-item[0], item[1], item[2])):
        remaining, marker, representative_key = key
        members = tuple(
            sorted(set(groups[key]), key=lambda state: (group.state_key(state), repr(state)))
        )
        stopped = tuple(
            remaining == 0 or is_stopped(kernel, state, goal) for state in members
        )
        failure = marker == OrbitCellKind.FAILURE.value
        if failure:
            if not all(stopped):
                raise ValueError("absorbing failure cell contains a nonterminal state")
            kind = OrbitCellKind.FAILURE
            representative = None
            stabilizer: tuple[ElementT, ...] = ()
            representative_key = "F"
        else:
            if len(set(stopped)) != 1:
                raise ValueError("D4 orbit mixes terminal and nonterminal states")
            kind = OrbitCellKind.TERMINAL if stopped[0] else OrbitCellKind.ACTIVE
            representative = representatives[key]
            if representative is None:  # pragma: no cover - type narrowing
                raise AssertionError("ordinary D4 orbit lacks a representative")
            stabilizer = group.stabilizer(representative)
        cell_id = StateTimeOrbitId(remaining, kind, representative_key)
        if cell_id in seen_cell_ids:
            raise ValueError(f"canonical state key collision for orbit cell {cell_id!r}")
        seen_cell_ids.add(cell_id)
        orbit = StateTimeOrbit(
            cell_id,
            representative,
            members,
            stabilizer,
            terminal=all(stopped),
            failure=failure,
        )
        orbits.append(orbit)
        assignments.extend(
            StateTimeAssignment(remaining, state, cell_id) for state in members
        )
    orbits.sort(key=lambda orbit: _cell_sort_key(orbit.cell_id))
    assignments.sort(
        key=lambda item: (-item.remaining, group.state_key(item.state), repr(item.state))
    )
    return tuple(orbits), tuple(assignments)


def _build_action_orbits_and_concretizations(
    kernel: object,
    group: FiniteGroupAction[StateT, ActionT, ElementT],
    orbits: tuple[StateTimeOrbit[StateT, ElementT], ...],
) -> tuple[
    tuple[StabilizerActionOrbit[StateT, ActionT, ElementT], ...],
    tuple[InverseActionConcretization[StateT, ActionT, ElementT], ...],
]:
    action_orbits: list[StabilizerActionOrbit[StateT, ActionT, ElementT]] = []
    concretizations: list[InverseActionConcretization[StateT, ActionT, ElementT]] = []
    for orbit in orbits:
        if orbit.cell_id.remaining <= 0 or orbit.terminal:
            continue
        representative = orbit.representative
        if representative is None:  # pragma: no cover - failure cells are terminal
            raise AssertionError("active orbit lacks a representative")
        legal = _unique_by_key(kernel.actions(representative), group.action_key)
        if not legal:
            raise ValueError("active D4 representative has no primitive actions")
        legal_set = set(legal)
        unseen = set(legal)
        while unseen:
            seed = min(unseen, key=lambda action: (group.action_key(action), repr(action)))
            images = _unique_by_key(
                (group.transform_action(element, seed) for element in orbit.stabilizer),
                group.action_key,
            )
            if not set(images) <= legal_set:
                raise ValueError("state stabilizer does not preserve legal primitive actions")
            unseen -= set(images)
            label = StabilizerActionOrbitLabel(
                group.state_key(representative),
                tuple(group.action_key(action) for action in images),
            )
            action_orbit = StabilizerActionOrbit(
                orbit.cell_id,
                label,
                representative,
                images,
                images[0],
                orbit.stabilizer,
            )
            action_orbits.append(action_orbit)

            for state in orbit.members:
                transporters = group.transporters(state, representative)
                if not transporters:
                    raise ValueError("D4 orbit member has no transporter to its representative")
                inverse_actions = _unique_by_key(
                    (
                        group.transform_action(group.inverse(element), images[0])
                        for element in transporters
                    ),
                    group.action_key,
                )
                state_legal = set(kernel.actions(state))
                if not inverse_actions or not set(inverse_actions) <= state_legal:
                    raise ValueError("inverse-action concretizer emitted an illegal action")
                probability = Fraction(1, len(inverse_actions))
                concretizations.append(
                    InverseActionConcretization(
                        orbit.cell_id,
                        state,
                        label,
                        transporters,
                        tuple((probability, action) for action in inverse_actions),
                    )
                )
    action_orbits.sort(
        key=lambda item: (_cell_sort_key(item.cell_id), item.label.action_keys)
    )
    concretizations.sort(
        key=lambda item: (
            _cell_sort_key(item.cell_id),
            group.state_key(item.state),
            item.label.action_keys,
        )
    )
    return tuple(action_orbits), tuple(concretizations)


def _realize(
    kernel: object,
    query: object,
    quotient_assignments: tuple[StateTimeAssignment[StateT], ...],
    concretization: InverseActionConcretization[StateT, ActionT, ElementT],
) -> OrbitRealization[StateT]:
    feature_totals: dict[str, Fraction] = {}
    successor_totals: dict[StateTimeOrbitId, Fraction] = {}
    failure_probability = Fraction(0)
    termination_probability = Fraction(0)
    goal = getattr(query, "goal", None)
    next_remaining = concretization.cell_id.remaining - 1
    assignment_map = {
        (assignment.remaining, assignment.state): assignment.cell_id
        for assignment in quotient_assignments
    }
    for action_probability, action in concretization.action_distribution:
        for outcome in iter_outcomes(kernel, concretization.state, action):
            probability = action_probability * as_fraction(outcome.probability)
            raw_features = outcome.reward_features
            items = raw_features.items() if isinstance(raw_features, Mapping) else raw_features
            for name, value in items:
                feature_totals[str(name)] = (
                    feature_totals.get(str(name), Fraction(0))
                    + probability * as_fraction(value)
                )
            if outcome.failure:
                failure_probability += probability
            stopped = bool(
                outcome.failure
                or outcome.terminal
                or is_stopped(kernel, outcome.next_state, goal)
            )
            if stopped:
                termination_probability += probability
            try:
                successor = assignment_map[(next_remaining, outcome.next_state)]
            except KeyError as error:  # pragma: no cover - closure invariant
                raise AssertionError("D4 quotient is not closed under its kernel") from error
            successor_totals[successor] = (
                successor_totals.get(successor, Fraction(0)) + probability
            )
    if sum(successor_totals.values(), Fraction(0)) != 1:
        raise AssertionError("D4 realization successor mass differs from one")
    return OrbitRealization(
        concretization.cell_id,
        concretization.state,
        concretization.label,
        tuple(sorted(feature_totals.items())),
        tuple(sorted(successor_totals.items(), key=lambda item: _cell_sort_key(item[0]))),
        failure_probability,
        termination_probability,
    )


def _total_variation(
    left: Mapping[StateTimeOrbitId, Fraction],
    right: Mapping[StateTimeOrbitId, Fraction],
) -> Fraction:
    support = set(left) | set(right)
    return sum(
        (abs(left.get(cell, Fraction(0)) - right.get(cell, Fraction(0))) for cell in support),
        Fraction(0),
    ) / 2


def _build_transitions_and_widths(
    kernel: object,
    query: object,
    assignments: tuple[StateTimeAssignment[StateT], ...],
    action_orbits: tuple[StabilizerActionOrbit[StateT, ActionT, ElementT], ...],
    concretizations: tuple[InverseActionConcretization[StateT, ActionT, ElementT], ...],
) -> tuple[
    tuple[OrbitRealization[StateT], ...],
    tuple[ExactOrbitTransition, ...],
    tuple[OrbitEnvelopeWidth, ...],
]:
    realizations = tuple(
        _realize(kernel, query, assignments, concretization)
        for concretization in concretizations
    )
    transitions: list[ExactOrbitTransition] = []
    widths: list[OrbitEnvelopeWidth] = []
    for action_orbit in action_orbits:
        group_realizations = tuple(
            realization
            for realization in realizations
            if realization.cell_id == action_orbit.cell_id
            and realization.label == action_orbit.label
        )
        if not group_realizations:
            raise AssertionError("D4 action orbit lacks ground realizations")
        feature_names = sorted(
            {
                name
                for realization in group_realizations
                for name, _ in realization.reward_features
            }
        )
        reward_widths = []
        for name in feature_names:
            values = [dict(realization.reward_features).get(name, Fraction(0)) for realization in group_realizations]
            reward_widths.append((name, max(values) - min(values)))
        failure_values = [realization.failure_probability for realization in group_realizations]
        termination_values = [realization.termination_probability for realization in group_realizations]
        tv_width = max(
            (
                _total_variation(
                    dict(left.successor_probabilities),
                    dict(right.successor_probabilities),
                )
                for left in group_realizations
                for right in group_realizations
            ),
            default=Fraction(0),
        )
        widths.append(
            OrbitEnvelopeWidth(
                action_orbit.cell_id,
                action_orbit.label,
                tuple(reward_widths),
                max(failure_values) - min(failure_values),
                max(termination_values) - min(termination_values),
                tv_width,
            )
        )
        representative_realization = next(
            realization
            for realization in group_realizations
            if realization.state == action_orbit.representative_state
        )
        transitions.append(
            ExactOrbitTransition(
                action_orbit.cell_id,
                action_orbit.label,
                representative_realization.reward_features,
                representative_realization.successor_probabilities,
                representative_realization.failure_probability,
                representative_realization.termination_probability,
            )
        )
    transitions.sort(key=lambda item: (_cell_sort_key(item.cell_id), item.label.action_keys))
    widths.sort(key=lambda item: (_cell_sort_key(item.cell_id), item.label.action_keys))
    return realizations, tuple(transitions), tuple(widths)


def _outcome_measure(
    kernel: object,
    state: StateT,
    action: ActionT,
    *,
    group: FiniteGroupAction[StateT, ActionT, ElementT] | None = None,
    element: ElementT | None = None,
) -> dict[tuple[StateT, tuple[tuple[str, Fraction], ...], bool, bool], Fraction]:
    measure: dict[
        tuple[StateT, tuple[tuple[str, Fraction], ...], bool, bool], Fraction
    ] = {}
    for outcome in iter_outcomes(kernel, state, action):
        next_state = outcome.next_state
        if group is not None:
            if element is None:  # pragma: no cover - internal contract
                raise AssertionError("transformed outcome measure lacks a group element")
            next_state = group.transform_state(element, next_state)
        features = tuple(
            sorted((str(name), as_fraction(value)) for name, value in outcome.reward_features)
        )
        key = (next_state, features, bool(outcome.failure), bool(outcome.terminal))
        measure[key] = measure.get(key, Fraction(0)) + as_fraction(outcome.probability)
    return measure


def _build_automorphism_checks(
    kernel: object,
    query: object,
    group: FiniteGroupAction[StateT, ActionT, ElementT],
    assignments: tuple[StateTimeAssignment[StateT], ...],
) -> tuple[OrbitAutomorphismCheck[StateT, ActionT, ElementT], ...]:
    assignment_map = {
        (assignment.remaining, assignment.state): assignment.cell_id
        for assignment in assignments
    }
    goal = getattr(query, "goal", None)
    checks: list[OrbitAutomorphismCheck[StateT, ActionT, ElementT]] = []
    for assignment in assignments:
        remaining = assignment.remaining
        state = assignment.state
        if remaining <= 0 or is_stopped(kernel, state, goal):
            continue
        for action in kernel.actions(state):
            transported_measure = None
            for element in group.elements:
                transformed_state = group.transform_state(element, state)
                transformed_action = group.transform_action(element, action)
                detail = ""
                passed = True
                if assignment_map.get((remaining, transformed_state)) != assignment.cell_id:
                    passed = False
                    detail = "transformed state left its state-time orbit"
                elif transformed_action not in set(kernel.actions(transformed_state)):
                    passed = False
                    detail = "transformed primitive action is illegal"
                else:
                    transported_measure = _outcome_measure(
                        kernel,
                        state,
                        action,
                        group=group,
                        element=element,
                    )
                    direct_measure = _outcome_measure(
                        kernel, transformed_state, transformed_action
                    )
                    if transported_measure != direct_measure:
                        passed = False
                        detail = "exact reward/failure/transition measure is not equivariant"
                checks.append(
                    OrbitAutomorphismCheck(
                        remaining,
                        state,
                        action,
                        element,
                        transformed_state,
                        transformed_action,
                        passed,
                        detail,
                    )
                )
    return tuple(checks)


def _build_state_automorphism_checks(
    kernel: object,
    query: object,
    group: FiniteGroupAction[StateT, ActionT, ElementT],
    orbits: tuple[StateTimeOrbit[StateT, ElementT], ...],
    assignments: tuple[StateTimeAssignment[StateT], ...],
) -> tuple[OrbitStateAutomorphismCheck[StateT, ElementT], ...]:
    assignment_map = {
        (assignment.remaining, assignment.state): assignment.cell_id
        for assignment in assignments
    }
    orbit_map = {orbit.cell_id: orbit for orbit in orbits}
    goal = getattr(query, "goal", None)
    checks: list[OrbitStateAutomorphismCheck[StateT, ElementT]] = []
    for assignment in assignments:
        source_orbit = orbit_map[assignment.cell_id]
        source_actions = set(kernel.actions(assignment.state))
        source_stopped = assignment.remaining == 0 or is_stopped(
            kernel, assignment.state, goal
        )
        source_terminal = assignment.remaining == 0 or bool(
            kernel.is_terminal(assignment.state)
        )
        for element in group.elements:
            transformed_state = group.transform_state(element, assignment.state)
            transformed_cell = assignment_map.get(
                (assignment.remaining, transformed_state)
            )
            target_orbit = orbit_map.get(transformed_cell)
            terminal_preserved = (
                (
                    assignment.remaining == 0
                    or bool(kernel.is_terminal(transformed_state))
                )
                == source_terminal
                and (
                    assignment.remaining == 0
                    or is_stopped(kernel, transformed_state, goal)
                )
                == source_stopped
            )
            failure_preserved = bool(
                target_orbit is not None
                and target_orbit.failure == source_orbit.failure
            )
            transformed_actions = {
                group.transform_action(element, action) for action in source_actions
            }
            legal_action_set_preserved = transformed_actions == set(
                kernel.actions(transformed_state)
            )
            same_cell = transformed_cell == assignment.cell_id
            passed = (
                same_cell
                and terminal_preserved
                and failure_preserved
                and legal_action_set_preserved
            )
            detail_parts = []
            if not same_cell:
                detail_parts.append("state orbit")
            if not terminal_preserved:
                detail_parts.append("terminal/goal semantics")
            if not failure_preserved:
                detail_parts.append("failure semantics")
            if not legal_action_set_preserved:
                detail_parts.append("legal action-set equality")
            checks.append(
                OrbitStateAutomorphismCheck(
                    assignment.remaining,
                    assignment.state,
                    element,
                    transformed_state,
                    terminal_preserved,
                    failure_preserved,
                    legal_action_set_preserved,
                    passed,
                    "equivariance failed for " + ", ".join(detail_parts)
                    if detail_parts
                    else "",
                )
            )
    return tuple(checks)


def _build_canonicalizer_choice_checks(
    group: FiniteGroupAction[StateT, ActionT, ElementT],
    orbits: tuple[StateTimeOrbit[StateT, ElementT], ...],
    action_orbits: tuple[StabilizerActionOrbit[StateT, ActionT, ElementT], ...],
    concretizations: tuple[InverseActionConcretization[StateT, ActionT, ElementT], ...],
) -> tuple[CanonicalizerChoiceCheck[StateT], ...]:
    concretization_map = {
        (record.cell_id, record.state, record.label): record.action_distribution
        for record in concretizations
    }
    checks: list[CanonicalizerChoiceCheck[StateT]] = []
    orbit_map = {orbit.cell_id: orbit for orbit in orbits}
    for action_orbit in action_orbits:
        orbit = orbit_map[action_orbit.cell_id]
        canonical_representative = action_orbit.representative_state
        canonical_action = action_orbit.canonical_action
        for alternative in orbit.members:
            representative_transports = group.transporters(
                canonical_representative, alternative
            )
            passed = bool(representative_transports)
            detail = "" if passed else "no transporter to alternative representative"
            choices_checked = 0
            for representative_transport in representative_transports:
                alternative_action = group.transform_action(
                    representative_transport, canonical_action
                )
                alternative_stabilizer_orbit = set(
                    group.transform_action(element, alternative_action)
                    for element in group.stabilizer(alternative)
                )
                transported_action_orbit = set(
                    group.transform_action(representative_transport, action)
                    for action in action_orbit.representative_actions
                )
                if alternative_stabilizer_orbit != transported_action_orbit:
                    passed = False
                    detail = "alternative representative changes the stabilizer action orbit"
                    break
                for state in orbit.members:
                    choices_checked += 1
                    alternative_transporters = group.transporters(state, alternative)
                    if not alternative_transporters:
                        passed = False
                        detail = "orbit member has no transporter to alternative representative"
                        break
                    inverse_actions = _unique_by_key(
                        (
                            group.transform_action(
                                group.inverse(element), alternative_action
                            )
                            for element in alternative_transporters
                        ),
                        group.action_key,
                    )
                    if not inverse_actions:  # pragma: no cover - follows transporter check
                        passed = False
                        detail = "alternative representative produced an empty K_x"
                        break
                    probability = Fraction(1, len(inverse_actions))
                    alternative_distribution = tuple(
                        (probability, action) for action in inverse_actions
                    )
                    if alternative_distribution != concretization_map[
                        (action_orbit.cell_id, state, action_orbit.label)
                    ]:
                        passed = False
                        detail = "alternative representative changes distinct inverse-action K_x"
                        break
                if not passed:
                    break
            checks.append(
                CanonicalizerChoiceCheck(
                    action_orbit.cell_id,
                    action_orbit.label,
                    alternative,
                    choices_checked,
                    passed,
                    detail,
                )
            )
    return tuple(checks)


def build_state_time_d4_quotient(
    kernel: object,
    query: object,
    group: FiniteGroupAction[StateT, ActionT, ElementT],
    *,
    is_failure: Callable[[StateT], bool] | None = None,
    state_time_cap: int = 50_000,
) -> StateTimeD4Quotient[StateT, ActionT, ElementT]:
    """Build the exact-data state-time quotient and all ``K_x`` records."""

    validate_query(kernel, query)
    pairs, failure_pairs = _enumerate_orbit_closed_state_time_pairs(
        kernel,
        query,
        group,
        is_failure=is_failure,
        state_time_cap=state_time_cap,
    )
    orbits, assignments = _build_orbits(kernel, query, group, pairs, failure_pairs)
    action_orbits, concretizations = _build_action_orbits_and_concretizations(
        kernel, group, orbits
    )
    realizations, transitions, widths = _build_transitions_and_widths(
        kernel, query, assignments, action_orbits, concretizations
    )
    state_automorphism_checks = _build_state_automorphism_checks(
        kernel, query, group, orbits, assignments
    )
    automorphism_checks = _build_automorphism_checks(
        kernel, query, group, assignments
    )
    canonicalizer_checks = _build_canonicalizer_choice_checks(
        group, orbits, action_orbits, concretizations
    )
    return StateTimeD4Quotient(
        query_horizon(kernel, query),
        orbits,
        assignments,
        action_orbits,
        concretizations,
        realizations,
        transitions,
        widths,
        state_automorphism_checks,
        automorphism_checks,
        canonicalizer_checks,
    )


def validate_d4_quotient(
    quotient: StateTimeD4Quotient[StateT, ActionT, ElementT],
) -> D4QuotientValidation:
    """Validate representative independence and structural quotient invariants."""

    failures: list[str] = []
    horizons_separated = all(
        all(assignment.remaining == orbit.cell_id.remaining for assignment in quotient.assignments if assignment.cell_id == orbit.cell_id)
        for orbit in quotient.state_time_orbits
    )
    if not horizons_separated:
        failures.append("a D4 state-time cell mixes remaining horizons")

    failure_by_horizon: dict[int, int] = {}
    failure_cells_unified = True
    for orbit in quotient.state_time_orbits:
        if orbit.failure:
            failure_by_horizon[orbit.cell_id.remaining] = failure_by_horizon.get(orbit.cell_id.remaining, 0) + 1
            if not orbit.terminal or orbit.cell_id.kind is not OrbitCellKind.FAILURE:
                failure_cells_unified = False
    if any(count != 1 for count in failure_by_horizon.values()):
        failure_cells_unified = False
    if not failure_cells_unified:
        failures.append("absorbing failure targets are not unified into one F_h cell")

    terminal_nonterminal_separated = all(
        orbit.failure
        or orbit.cell_id.kind
        is (OrbitCellKind.TERMINAL if orbit.terminal else OrbitCellKind.ACTIVE)
        for orbit in quotient.state_time_orbits
    )
    if not terminal_nonterminal_separated:
        failures.append("terminal and nonterminal states share a D4 orbit cell")

    failed_state_automorphisms = tuple(
        check for check in quotient.state_automorphism_checks if not check.passed
    )
    if failed_state_automorphisms:
        failures.extend(
            f"D4 state automorphism failure at h={check.remaining}, "
            f"state={check.state!r}, element={check.element!r}: {check.detail}"
            for check in failed_state_automorphisms
        )
    failed_automorphisms = tuple(
        check for check in quotient.automorphism_checks if not check.passed
    )
    automorphism_exact = not failed_state_automorphisms and not failed_automorphisms
    if failed_automorphisms:
        failures.extend(
            f"D4 automorphism failure at h={check.remaining}, "
            f"state={check.state!r}, action={check.action!r}, "
            f"element={check.element!r}: {check.detail}"
            for check in failed_automorphisms
        )

    failed_canonicalizers = tuple(
        check for check in quotient.canonicalizer_choice_checks if not check.passed
    )
    canonicalizer_independent = not failed_canonicalizers
    if failed_canonicalizers:
        failures.extend(
            f"canonicalizer-choice failure at {check.cell_id!r}: {check.detail}"
            for check in failed_canonicalizers
        )

    distinct_uniform = True
    for record in quotient.concretizations:
        actions = tuple(action for _, action in record.action_distribution)
        probabilities = tuple(probability for probability, _ in record.action_distribution)
        expected = Fraction(1, len(actions)) if actions else Fraction(0)
        if (
            not actions
            or len(set(actions)) != len(actions)
            or any(probability != expected for probability in probabilities)
            or sum(probabilities, Fraction(0)) != 1
        ):
            distinct_uniform = False
            failures.append(
                f"K_x is not uniform over distinct inverse actions at "
                f"{record.cell_id!r}, state={record.state!r}"
            )

    nonzero = tuple(width for width in quotient.envelope_widths if not width.zero)
    representative_independent = not nonzero
    zero_width = not nonzero
    if nonzero:
        failures.extend(
            f"nonzero representative envelope width at {width.cell_id!r}, {width.label!r}"
            for width in nonzero
        )
    return D4QuotientValidation(
        representative_independent,
        zero_width,
        automorphism_exact,
        len(quotient.state_automorphism_checks) + len(quotient.automorphism_checks),
        canonicalizer_independent,
        distinct_uniform,
        horizons_separated,
        failure_cells_unified,
        terminal_nonterminal_separated,
        tuple(failures),
        quotient.envelope_widths,
    )


def _solve_abstract_frontier(
    quotient: StateTimeD4Quotient[StateT, ActionT, ElementT],
    query: object,
) -> _AbstractSolveResult:
    weights = reward_weights(query)
    Distribution = tuple[tuple[StateTimeOrbitId, Fraction], ...]
    memo: dict[Distribution, tuple[ParetoPoint, ...]] = {}
    composed_candidates = 0
    zero = ParetoPoint(Fraction(0), Fraction(0), FiniteHorizonPolicy(()))

    def canonical_distribution(
        masses: Mapping[StateTimeOrbitId, Fraction],
    ) -> Distribution:
        return tuple(
            sorted(
                ((cell, mass) for cell, mass in masses.items() if mass > 0),
                key=lambda item: _cell_sort_key(item[0]),
            )
        )

    def frontier(distribution: Distribution) -> tuple[ParetoPoint, ...]:
        nonlocal composed_candidates
        if distribution in memo:
            return memo[distribution]
        decision_cells = [
            cell
            for cell, mass in distribution
            if mass > 0 and quotient.labels(cell)
        ]
        if not decision_cells:
            memo[distribution] = (zero,)
            return memo[distribution]
        mass_by_cell = dict(distribution)
        candidates: list[ParetoPoint] = []
        for labels in product(*(quotient.labels(cell) for cell in decision_cells)):
            immediate_reward = Fraction(0)
            immediate_failure = Fraction(0)
            successor_mass: dict[StateTimeOrbitId, Fraction] = {}
            current_decisions: list[
                tuple[tuple[int, StateTimeOrbitId], StabilizerActionOrbitLabel]
            ] = []
            for cell, label in zip(decision_cells, labels):
                mass = mass_by_cell[cell]
                transition = quotient.transition(cell, label)
                immediate_reward += mass * transition.reward(weights)
                immediate_failure += mass * transition.failure_probability
                current_decisions.append(((cell.remaining, cell), label))
                for successor, probability in transition.successor_probabilities:
                    successor_mass[successor] = (
                        successor_mass.get(successor, Fraction(0)) + mass * probability
                    )
            for continuation in frontier(canonical_distribution(successor_mass)):
                composed_candidates += 1
                mapping = continuation.policy.as_dict()
                for decision_key, label in current_decisions:
                    incumbent = mapping.get(decision_key)
                    if incumbent is not None and incumbent != label:  # pragma: no cover
                        raise AssertionError("abstract policy has a state-time action conflict")
                    mapping[decision_key] = label
                candidates.append(
                    ParetoPoint(
                        immediate_reward + continuation.expected_reward,
                        immediate_failure + continuation.failure_probability,
                        FiniteHorizonPolicy.from_mapping(mapping),
                    )
                )
        memo[distribution] = pareto_prune(candidates)
        return memo[distribution]

    initial_mass: dict[StateTimeOrbitId, Fraction] = {}
    initial_horizon = int(getattr(query, "horizon"))
    for probability, state in getattr(query, "initial_distribution"):
        cell = quotient.cell_of(state, initial_horizon)
        initial_mass[cell] = initial_mass.get(cell, Fraction(0)) + as_fraction(probability)
    result_frontier = frontier(canonical_distribution(initial_mass))
    selected = select_constrained(result_frontier, as_fraction(getattr(query, "delta")))
    return _AbstractSolveResult(result_frontier, selected, composed_candidates)


def evaluate_lifted_d4_policy(
    kernel: object,
    query: object,
    quotient: StateTimeD4Quotient[StateT, ActionT, ElementT],
    policy: FiniteHorizonPolicy[StateTimeOrbitId, StabilizerActionOrbitLabel],
) -> PolicyEvaluation:
    """Exactly evaluate the stochastic ground policy induced by all ``K_x``."""

    validate_query(kernel, query)
    weights = reward_weights(query)
    goal = getattr(query, "goal", None)
    memo: dict[tuple[int, StateT], PolicyEvaluation] = {}

    def evaluate(state: StateT, remaining: int) -> PolicyEvaluation:
        key = (remaining, state)
        if key in memo:
            return memo[key]
        if remaining <= 0 or is_stopped(kernel, state, goal):
            result = PolicyEvaluation(Fraction(0), Fraction(0))
            memo[key] = result
            return result
        cell = quotient.cell_of(state, remaining)
        label = policy.action(cell, remaining)
        reward = Fraction(0)
        failure = Fraction(0)
        for action_probability, action in quotient.concretize(state, remaining, label):
            for outcome in iter_outcomes(kernel, state, action):
                probability = action_probability * as_fraction(outcome.probability)
                branch_reward = sum(
                    (
                        weights.get(str(name), Fraction(0)) * as_fraction(value)
                        for name, value in outcome.reward_features
                    ),
                    Fraction(0),
                )
                branch_failure = Fraction(1) if outcome.failure else Fraction(0)
                stopped = bool(
                    outcome.failure
                    or outcome.terminal
                    or is_stopped(kernel, outcome.next_state, goal)
                )
                if not stopped:
                    continuation = evaluate(outcome.next_state, remaining - 1)
                    branch_reward += continuation.expected_reward
                    branch_failure = continuation.failure_probability
                reward += probability * branch_reward
                failure += probability * branch_failure
        result = PolicyEvaluation(reward, failure)
        memo[key] = result
        return result

    root_reward = Fraction(0)
    root_failure = Fraction(0)
    initial_horizon = query_horizon(kernel, query)
    for probability, state in query_initial_distribution(kernel, query):
        result = evaluate(state, initial_horizon)
        root_reward += probability * result.expected_reward
        root_failure += probability * result.failure_probability
    return PolicyEvaluation(root_reward, root_failure)


def _materialize_lifted_policy(
    quotient: StateTimeD4Quotient[StateT, ActionT, ElementT],
    policy: FiniteHorizonPolicy[StateTimeOrbitId, StabilizerActionOrbitLabel],
) -> LiftedOrbitPolicy[StateT, ActionT]:
    decisions = []
    for concretization in quotient.concretizations:
        try:
            selected = policy.action(
                concretization.cell_id, concretization.cell_id.remaining
            )
        except KeyError:
            continue
        if selected == concretization.label:
            decisions.append(
                LiftedOrbitDecision(
                    concretization.cell_id,
                    concretization.state,
                    concretization.label,
                    concretization.action_distribution,
                )
            )
    return LiftedOrbitPolicy(policy, tuple(decisions))


def _compression_counts(
    kernel: object,
    query: object,
    quotient: StateTimeD4Quotient[StateT, ActionT, ElementT],
) -> D4CompressionCounts:
    goal = getattr(query, "goal", None)
    ground_action_count = sum(
        len(tuple(kernel.actions(assignment.state)))
        for assignment in quotient.assignments
        if assignment.remaining > 0
        and not is_stopped(kernel, assignment.state, goal)
    )
    semantic_count = len(quotient.action_orbits)
    ground_state_count = len(quotient.assignments)
    quotient_state_count = len(quotient.state_time_orbits)
    return D4CompressionCounts(
        ground_state_time_count=ground_state_count,
        quotient_state_time_count=quotient_state_count,
        ground_legal_action_count=ground_action_count,
        semantic_action_orbit_count=semantic_count,
        distinct_concretizer_support_count=sum(
            len(record.action_distribution) for record in quotient.concretizations
        ),
        state_compression_ratio=Fraction(ground_state_count, quotient_state_count),
        action_compression_ratio=(
            Fraction(ground_action_count, semantic_count)
            if semantic_count
            else Fraction(1)
        ),
    )


def _state_time_value_checks(
    kernel: object,
    query: object,
    quotient: StateTimeD4Quotient[StateT, ActionT, ElementT],
) -> tuple[StateTimeValueCheck[StateT], ...]:
    """Compare exact point-query values at every represented ``(x,h)`` pair."""

    abstract_cache: dict[StateTimeOrbitId, _AbstractSolveResult] = {}
    checks: list[StateTimeValueCheck[StateT]] = []
    for assignment in quotient.assignments:
        point_query = replace(
            query,
            initial_distribution=((Fraction(1), assignment.state),),
            horizon=assignment.remaining,
        )
        abstract = abstract_cache.get(assignment.cell_id)
        if abstract is None:
            abstract = _solve_abstract_frontier(quotient, point_query)
            abstract_cache[assignment.cell_id] = abstract
        ground = solve_ground_pareto(kernel, point_query)
        abstract_selected = abstract.selected
        ground_selected = ground.selected
        if abstract_selected is None:
            abstract_value = None
            abstract_risk = None
            lifted_value = None
            lifted_risk = None
        else:
            abstract_value = abstract_selected.expected_reward
            abstract_risk = abstract_selected.failure_probability
            lifted = evaluate_lifted_d4_policy(
                kernel, point_query, quotient, abstract_selected.policy
            )
            lifted_value = lifted.expected_reward
            lifted_risk = lifted.failure_probability
        if ground_selected is None:
            ground_value = None
            ground_risk = None
        else:
            ground_value = ground_selected.expected_reward
            ground_risk = ground_selected.failure_probability
        abstract_signature = tuple(
            sorted(
                {
                    (point.expected_reward, point.failure_probability)
                    for point in abstract.frontier
                }
            )
        )
        ground_signature = tuple(
            sorted(
                {
                    (point.expected_reward, point.failure_probability)
                    for point in ground.frontier
                }
            )
        )
        frontier_exact = abstract_signature == ground_signature
        abstract_reward_optimal = min(
            abstract.frontier,
            key=lambda point: (
                -point.expected_reward,
                point.failure_probability,
                point.policy.signature(),
            ),
        )
        ground_reward_optimal = min(
            ground.frontier,
            key=lambda point: (
                -point.expected_reward,
                point.failure_probability,
                point.policy.signature(),
            ),
        )
        lifted_reward_optimal = evaluate_lifted_d4_policy(
            kernel, point_query, quotient, abstract_reward_optimal.policy
        )
        abstract_unconstrained_value = abstract_reward_optimal.expected_reward
        lifted_unconstrained_value = lifted_reward_optimal.expected_reward
        ground_unconstrained_value = ground_reward_optimal.expected_reward
        unconstrained_value_exact = (
            abstract_unconstrained_value
            == lifted_unconstrained_value
            == ground_unconstrained_value
        )
        constrained_result_exact = (
            (abstract_selected is None) == (ground_selected is None)
            and (abstract_value, abstract_risk) == (lifted_value, lifted_risk)
            and (abstract_value, abstract_risk) == (ground_value, ground_risk)
        )
        exact_match = (
            constrained_result_exact
            and frontier_exact
            and unconstrained_value_exact
        )
        checks.append(
            StateTimeValueCheck(
                assignment.cell_id,
                assignment.state,
                abstract_selected is not None,
                ground_selected is not None,
                abstract_value,
                abstract_risk,
                lifted_value,
                lifted_risk,
                ground_value,
                ground_risk,
                abstract_signature,
                ground_signature,
                frontier_exact,
                abstract_unconstrained_value,
                lifted_unconstrained_value,
                ground_unconstrained_value,
                unconstrained_value_exact,
                constrained_result_exact,
                exact_match,
            )
        )
    return tuple(checks)


def solve_exact_d4_quotient(
    kernel: object,
    query: object,
    quotient: StateTimeD4Quotient[StateT, ActionT, ElementT],
    *,
    ground_result: GroundParetoResult | None = None,
) -> ExactD4QuotientReport[StateT, ActionT, ElementT]:
    """Solve, lift and compare a previously built exact D4 quotient."""

    validation = validate_d4_quotient(quotient)
    if not validation.exact:
        raise ExactD4QuotientInvariantViolation(validation.failures)
    abstract = _solve_abstract_frontier(quotient, query)
    ground = ground_result or solve_ground_pareto(kernel, query)
    if abstract.selected is None:
        abstract_policy = None
        abstract_value = None
        abstract_risk = None
        lifted_policy = None
        lifted_value = None
        lifted_risk = None
    else:
        abstract_policy = abstract.selected.policy
        abstract_value = abstract.selected.expected_reward
        abstract_risk = abstract.selected.failure_probability
        lifted_policy = _materialize_lifted_policy(quotient, abstract_policy)
        lifted = evaluate_lifted_d4_policy(kernel, query, quotient, abstract_policy)
        lifted_value = lifted.expected_reward
        lifted_risk = lifted.failure_probability
        if (lifted_value, lifted_risk) != (abstract_value, abstract_risk):
            raise AssertionError("exact D4 abstract value/risk differs from its ground lift")

    if ground.selected is None:
        ground_policy = None
        ground_value = None
        ground_risk = None
    else:
        ground_policy = ground.selected.policy
        ground_value = ground.selected.expected_reward
        ground_risk = ground.selected.failure_probability
    delta_action = (
        ground_value - lifted_value
        if ground_value is not None and lifted_value is not None
        else None
    )
    compression = _compression_counts(kernel, query, quotient)
    state_time_checks = _state_time_value_checks(kernel, query, quotient)
    return ExactD4QuotientReport(
        quotient=quotient,
        validation=validation,
        abstract_frontier=abstract.frontier,
        abstract_selected_policy=abstract_policy,
        abstract_value=abstract_value,
        abstract_risk=abstract_risk,
        lifted_ground_policy=lifted_policy,
        lifted_value=lifted_value,
        lifted_risk=lifted_risk,
        ground_frontier=ground.frontier,
        ground_selected_policy=ground_policy,
        ground_value=ground_value,
        ground_risk=ground_risk,
        delta_action=delta_action,
        compression=compression,
        state_time_value_checks=state_time_checks,
        all_state_time_values_exact=all(
            check.exact_match for check in state_time_checks
        ),
        abstract_composed_candidate_count=abstract.composed_candidate_count,
        ground_composed_candidate_count=ground.composed_candidate_count,
    )


def build_validate_solve_d4(
    kernel: object,
    query: object,
    group: FiniteGroupAction[StateT, ActionT, ElementT],
    *,
    is_failure: Callable[[StateT], bool] | None = None,
    state_time_cap: int = 50_000,
) -> ExactD4QuotientReport[StateT, ActionT, ElementT]:
    """One-call exact D4 build/validate/solve/lift/J0 baseline API."""

    quotient = build_state_time_d4_quotient(
        kernel,
        query,
        group,
        is_failure=is_failure,
        state_time_cap=state_time_cap,
    )
    return solve_exact_d4_quotient(kernel, query, quotient)
