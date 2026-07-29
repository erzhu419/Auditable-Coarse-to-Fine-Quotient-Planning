"""Independent proof replay for the exact lazy H=2 robust planner.

The verifier never calls the production lazy solver or any of its private
traversal helpers.  It reconstructs the finite decision domains and the joint
interval-simplex Bellman arithmetic from the public model objects.  A
content-addressed prefix cover proves that every root-conditioned policy
extension was either evaluated completely or was soundly dominated by the
final selected policy.

Models inside the legacy Cartesian cap receive an additional byte-for-byte
comparison against the public exhaustive V0 authority.  Larger models are
accepted only after complete prefix-cover replay.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib
from typing import Any, Mapping, Sequence

import acfqp.exact_lazy_h2_robust_planner_v1 as lazy
import acfqp.partial_support_robust_planner_v1 as robust
from acfqp.phase3e_ids import canonical_json_bytes


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "exact_lazy_h2_independent_prefix_cover_verifier_v0"
DOMAIN_TAG = "acfqp:exact-lazy-h2-independent-verification:v1"


class ExactLazyH2IndependentVerificationError(ValueError):
    """The claimed lazy result is malformed or its proof does not close."""


def _content_id(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        DOMAIN_TAG.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _fdoc(value: Fraction) -> dict[str, int]:
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


@dataclass(frozen=True, slots=True)
class ExactLazyH2IndependentVerificationV1:
    model_id: str
    threshold_profile_id: str
    audit_id: str
    original_proof_id: str
    zero_other_proof_id: str | None
    solver_kind: robust.RobustSolverKind
    verified_branch_nodes: int
    verified_complete_nodes: int
    verified_pruned_nodes: int
    legacy_exhaustive_bytes_compared: bool
    complete_prefix_cover_verified: bool = True
    exact_fraction_replay_verified: bool = True
    selected_audit_rebuilt_independently: bool = True
    production_lazy_solver_called: bool = False
    independent_implementation_claimed: bool = True

    def __post_init__(self) -> None:
        if (
            type(self.solver_kind) is not robust.RobustSolverKind
            or any(
                type(value) is not str or len(value) != 64
                for value in (
                    self.model_id,
                    self.threshold_profile_id,
                    self.audit_id,
                    self.original_proof_id,
                )
            )
            or (
                self.zero_other_proof_id is not None
                and (
                    type(self.zero_other_proof_id) is not str
                    or len(self.zero_other_proof_id) != 64
                )
            )
            or any(
                type(value) is not int or value < 0
                for value in (
                    self.verified_branch_nodes,
                    self.verified_complete_nodes,
                    self.verified_pruned_nodes,
                )
            )
            or type(self.legacy_exhaustive_bytes_compared) is not bool
            or self.complete_prefix_cover_verified is not True
            or self.exact_fraction_replay_verified is not True
            or self.selected_audit_rebuilt_independently is not True
            or self.production_lazy_solver_called is not False
            or self.independent_implementation_claimed is not True
        ):
            raise ExactLazyH2IndependentVerificationError(
                "independent verification result is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.exact_lazy_h2_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "model_id": self.model_id,
            "threshold_profile_id": self.threshold_profile_id,
            "audit_id": self.audit_id,
            "original_proof_id": self.original_proof_id,
            "zero_other_proof_id": self.zero_other_proof_id,
            "solver_kind": self.solver_kind.value,
            "verified_branch_nodes": self.verified_branch_nodes,
            "verified_complete_nodes": self.verified_complete_nodes,
            "verified_pruned_nodes": self.verified_pruned_nodes,
            "legacy_exhaustive_bytes_compared": (
                self.legacy_exhaustive_bytes_compared
            ),
            "complete_prefix_cover_verified": True,
            "exact_fraction_replay_verified": True,
            "selected_audit_rebuilt_independently": True,
            "production_lazy_solver_called": False,
            "independent_implementation_claimed": True,
        }

    @property
    def verification_id(self) -> str:
        return _content_id(self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_id": self.verification_id,
        }


@dataclass(frozen=True, slots=True)
class _RowEvaluation:
    bound: robust.RobustSelectedRowBoundV1
    provenance: robust.SelectedRowProvenanceV1


@dataclass(frozen=True, slots=True)
class _Value:
    reward_lower: Fraction
    reward_upper: Fraction
    failure_upper: Fraction
    rows: tuple[_RowEvaluation, ...]


@dataclass(frozen=True, slots=True)
class _Policy:
    assignments: tuple[robust.RobustPolicyAssignmentV1, ...]
    reward_lower: Fraction
    reward_upper: Fraction
    failure_upper: Fraction
    rows: tuple[_RowEvaluation, ...]

    @property
    def policy_key(self) -> tuple[str, ...]:
        return tuple(item.assignment_id for item in self.assignments)


@dataclass(frozen=True, slots=True)
class _PolicyOrderSummary:
    reward_lower: Fraction
    reward_upper: Fraction
    failure_upper: Fraction
    policy_key: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _Choice:
    assignment: robust.RobustPolicyAssignmentV1
    values: Mapping[str, _Value]
    rows: tuple[_RowEvaluation, ...]


@dataclass(frozen=True, slots=True)
class _Unit:
    scope_key: str
    state_ids: tuple[str, ...]
    choices: tuple[_Choice, ...]

    @property
    def default(self) -> _Choice:
        return min(self.choices, key=lambda item: item.assignment.assignment_id)


@dataclass(frozen=True, slots=True)
class _Root:
    action_key: str
    assignment: robust.RobustPolicyAssignmentV1
    relevant_state_ids: frozenset[str]


@dataclass(frozen=True, slots=True)
class _ProofReplay:
    selected: _Policy
    unrestricted_reward_upper: Fraction
    status: robust.RobustAuditStatus
    branch_nodes: int
    complete_nodes: int
    pruned_nodes: int


def _fail(message: str) -> None:
    raise ExactLazyH2IndependentVerificationError(message)


def _registries(
    model: robust.PartialSupportIntervalModelV1,
) -> tuple[
    dict[str, robust.StateActionCatalogueV1],
    dict[str, robust.RegisteredDestinationV1],
    dict[tuple[str, int, str], robust.IntervalSimplexRowV1],
    dict[
        tuple[str, str, str],
        robust.DistinctActionConcretizerEntryV1,
    ],
]:
    return (
        {item.state_id: item for item in model.catalogues},
        {item.destination_id: item for item in model.destinations},
        {item.row_key: item for item in model.rows},
        {
            (
                item.state_coordinate_key,
                item.state_id,
                item.abstract_action_key,
            ): item
            for item in model.concretizer_entries
        },
    )


def _reachable_children(
    model: robust.PartialSupportIntervalModelV1,
) -> tuple[str, ...]:
    catalogues, destinations, rows, _ = _registries(model)
    output: set[str] = set()
    for action in catalogues[model.root_state_id].actions:
        row = rows[(model.root_state_id, 2, action.action_id)]
        for mass in row.masses:
            destination = destinations[mass.destination_id]
            if (
                mass.upper > 0
                and destination.category
                is robust.DestinationCategory.ACTIVE_STATE
            ):
                assert destination.state_id is not None
                output.add(destination.state_id)
    return tuple(sorted(output))


def _extreme_expectation(
    masses: Sequence[robust.IntervalDestinationMassV1],
    values: Mapping[str, Fraction],
    *,
    maximize: bool,
) -> tuple[Fraction, dict[str, Fraction]]:
    if {item.destination_id for item in masses} != set(values):
        _fail("row value registry does not equal the interval simplex")
    allocations = {
        item.destination_id: item.lower for item in masses
    }
    residual = Fraction(1) - sum(allocations.values(), Fraction(0))
    ordered = sorted(
        masses,
        key=lambda item: (
            -values[item.destination_id]
            if maximize
            else values[item.destination_id],
            item.destination_id,
        ),
    )
    for item in ordered:
        if residual == 0:
            break
        addition = min(residual, item.upper - item.lower)
        allocations[item.destination_id] += addition
        residual -= addition
    if residual != 0:
        _fail("independent simplex replay could not allocate unit mass")
    return (
        sum(
            allocations[item.destination_id] * values[item.destination_id]
            for item in masses
        ),
        allocations,
    )


def _evaluate_row(
    row: robust.IntervalSimplexRowV1,
    *,
    destinations: Mapping[str, robust.RegisteredDestinationV1],
    child_values: Mapping[str, _Value],
    threshold: robust.RobustThresholdProfileV1,
    category: robust.SelectedRowCategory,
    policy_scope_key: str,
) -> _RowEvaluation:
    risk_values: dict[str, Fraction] = {}
    lower_values: dict[str, Fraction] = {}
    upper_values: dict[str, Fraction] = {}
    for mass in row.masses:
        destination = destinations[mass.destination_id]
        active = (
            destination.category
            is robust.DestinationCategory.ACTIVE_STATE
            and row.remaining_horizon > 1
        )
        if destination.category in (
            robust.DestinationCategory.FAILURE,
            robust.DestinationCategory.OTHER,
        ):
            risk_values[mass.destination_id] = Fraction(1)
        elif active:
            assert destination.state_id is not None
            risk_values[mass.destination_id] = child_values[
                destination.state_id
            ].failure_upper
        else:
            risk_values[mass.destination_id] = Fraction(0)
        if active:
            assert destination.state_id is not None
            lower_values[mass.destination_id] = child_values[
                destination.state_id
            ].reward_lower
            upper_values[mass.destination_id] = child_values[
                destination.state_id
            ].reward_upper
        else:
            lower_values[mass.destination_id] = Fraction(0)
            upper_values[mass.destination_id] = (
                threshold.reward_ceiling
                if (
                    destination.category
                    is robust.DestinationCategory.OTHER
                    and row.remaining_horizon > 1
                )
                else Fraction(0)
            )
    risk, risk_allocations = _extreme_expectation(
        row.masses,
        risk_values,
        maximize=True,
    )
    lower, lower_allocations = _extreme_expectation(
        row.masses,
        lower_values,
        maximize=False,
    )
    upper, upper_allocations = _extreme_expectation(
        row.masses,
        upper_values,
        maximize=True,
    )
    total_lower = row.reward_lower + lower
    total_upper = min(
        threshold.reward_ceiling,
        row.reward_upper + upper,
    )
    if (
        row.reward_upper > threshold.reward_ceiling
        or total_lower > threshold.reward_ceiling
        or total_lower > total_upper
    ):
        _fail("independent row replay exceeds the reward ceiling")
    other = row.other_destination_id
    return _RowEvaluation(
        robust.RobustSelectedRowBoundV1(
            row.row_id,
            row.remaining_horizon,
            total_lower,
            total_upper,
            risk,
            row.other_mass.lower,
            row.other_mass.upper,
            lower_allocations[other],
            upper_allocations[other],
            risk_allocations[other],
        ),
        robust.SelectedRowProvenanceV1(
            row.row_id,
            category,
            policy_scope_key,
            row.state_id,
            row.action_id,
            row.remaining_horizon,
        ),
    )


def _average(rows: Sequence[_RowEvaluation]) -> _Value:
    if not rows:
        _fail("concretizer support is empty")
    denominator = len(rows)
    return _Value(
        sum((item.bound.reward_lower for item in rows), Fraction(0))
        / denominator,
        sum((item.bound.reward_upper for item in rows), Fraction(0))
        / denominator,
        sum((item.bound.failure_upper for item in rows), Fraction(0))
        / denominator,
        tuple(rows),
    )


def _common_actions(
    model: robust.PartialSupportIntervalModelV1,
    state_ids: Sequence[str],
) -> tuple[str, ...]:
    catalogues, _, _, concretizers = _registries(model)
    common: set[str] | None = None
    for state_id in state_ids:
        cell = catalogues[state_id].state_coordinate_key
        available = {
            action_key
            for entry_cell, entry_state, action_key in concretizers
            if entry_cell == cell and entry_state == state_id
        }
        common = (
            available if common is None else common.intersection(available)
        )
    result = tuple(sorted(common or ()))
    if not result:
        _fail("quotient cell has no common semantic action")
    return result


def _evaluate_concretized(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    *,
    state_id: str,
    remaining_horizon: int,
    action_key: str,
    child_values: Mapping[str, _Value],
    category: robust.SelectedRowCategory,
) -> _Value:
    catalogues, destinations, rows, concretizers = _registries(model)
    cell = catalogues[state_id].state_coordinate_key
    entry = concretizers.get((cell, state_id, action_key))
    if entry is None:
        _fail("semantic action lacks a concretizer")
    evaluated = tuple(
        _evaluate_row(
            rows[(state_id, remaining_horizon, action_id)],
            destinations=destinations,
            child_values=child_values,
            threshold=threshold,
            category=category,
            policy_scope_key=cell,
        )
        for action_id in entry.ground_action_ids
    )
    return _average(evaluated)


def _decision_units(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
) -> tuple[_Unit, ...]:
    catalogues, destinations, rows, _ = _registries(model)
    child_states = _reachable_children(model)
    if solver_kind is robust.RobustSolverKind.GROUND_DIRECT:
        output: list[_Unit] = []
        for state_id in child_states:
            choices: list[_Choice] = []
            for action in catalogues[state_id].actions:
                row = _evaluate_row(
                    rows[(state_id, 1, action.action_id)],
                    destinations=destinations,
                    child_values={},
                    threshold=threshold,
                    category=robust.SelectedRowCategory.CONTINUATION_SELECTED,
                    policy_scope_key=state_id,
                )
                choices.append(
                    _Choice(
                        robust.RobustPolicyAssignmentV1(
                            robust.PolicyScope.GROUND_STATE,
                            state_id,
                            1,
                            action.action_id,
                        ),
                        {
                            state_id: _Value(
                                row.bound.reward_lower,
                                row.bound.reward_upper,
                                row.bound.failure_upper,
                                (row,),
                            )
                        },
                        (row,),
                    )
                )
            output.append(_Unit(state_id, (state_id,), tuple(choices)))
        return tuple(output)

    cells: dict[str, list[str]] = {}
    for state_id in child_states:
        cells.setdefault(
            catalogues[state_id].state_coordinate_key,
            [],
        ).append(state_id)
    quotient_output: list[_Unit] = []
    for cell in sorted(cells):
        states = tuple(sorted(cells[cell]))
        choices = []
        for action_key in _common_actions(model, states):
            values: dict[str, _Value] = {}
            selected_rows: list[_RowEvaluation] = []
            for state_id in states:
                value = _evaluate_concretized(
                    model,
                    threshold,
                    state_id=state_id,
                    remaining_horizon=1,
                    action_key=action_key,
                    child_values={},
                    category=(
                        robust.SelectedRowCategory
                        .CONTINUATION_CONCRETIZER_COMPONENT
                    ),
                )
                values[state_id] = value
                selected_rows.extend(value.rows)
            choices.append(
                _Choice(
                    robust.RobustPolicyAssignmentV1(
                        robust.PolicyScope.QUOTIENT_CELL,
                        cell,
                        1,
                        action_key,
                    ),
                    values,
                    tuple(selected_rows),
                )
            )
        quotient_output.append(_Unit(cell, states, tuple(choices)))
    return tuple(quotient_output)


def _roots(
    model: robust.PartialSupportIntervalModelV1,
    solver_kind: robust.RobustSolverKind,
) -> tuple[_Root, ...]:
    catalogues, destinations, rows, concretizers = _registries(model)
    root_catalogue = catalogues[model.root_state_id]
    root_cell = root_catalogue.state_coordinate_key
    if solver_kind is robust.RobustSolverKind.GROUND_DIRECT:
        raw = tuple(
            (
                action.action_id,
                (rows[(model.root_state_id, 2, action.action_id)],),
            )
            for action in root_catalogue.actions
        )
        scope = robust.PolicyScope.GROUND_STATE
        scope_key = model.root_state_id
    else:
        raw_items = []
        for action_key in _common_actions(
            model,
            (model.root_state_id,),
        ):
            entry = concretizers[
                (root_cell, model.root_state_id, action_key)
            ]
            raw_items.append(
                (
                    action_key,
                    tuple(
                        rows[(model.root_state_id, 2, action_id)]
                        for action_id in entry.ground_action_ids
                    ),
                )
            )
        raw = tuple(raw_items)
        scope = robust.PolicyScope.QUOTIENT_CELL
        scope_key = root_cell
    output = []
    for action_key, root_rows in raw:
        relevant: set[str] = set()
        for row in root_rows:
            for mass in row.masses:
                destination = destinations[mass.destination_id]
                if (
                    mass.upper > 0
                    and destination.category
                    is robust.DestinationCategory.ACTIVE_STATE
                ):
                    assert destination.state_id is not None
                    relevant.add(destination.state_id)
        output.append(
            _Root(
                action_key,
                robust.RobustPolicyAssignmentV1(
                    scope,
                    scope_key,
                    2,
                    action_key,
                ),
                frozenset(relevant),
            )
        )
    return tuple(output)


def _evaluate_root(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
    root: _Root,
    child_values: Mapping[str, _Value],
) -> _Value:
    catalogues, destinations, rows, _ = _registries(model)
    if solver_kind is robust.RobustSolverKind.GROUND_DIRECT:
        item = _evaluate_row(
            rows[(model.root_state_id, 2, root.action_key)],
            destinations=destinations,
            child_values=child_values,
            threshold=threshold,
            category=robust.SelectedRowCategory.ROOT_SELECTED,
            policy_scope_key=model.root_state_id,
        )
        return _Value(
            item.bound.reward_lower,
            item.bound.reward_upper,
            item.bound.failure_upper,
            (item,),
        )
    return _evaluate_concretized(
        model,
        threshold,
        state_id=model.root_state_id,
        remaining_horizon=2,
        action_key=root.action_key,
        child_values=child_values,
        category=robust.SelectedRowCategory.ROOT_CONCRETIZER_COMPONENT,
    )


def _complete_policy(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
    root: _Root,
    choices: Sequence[_Choice],
) -> _Policy:
    child_values: dict[str, _Value] = {}
    child_rows: list[_RowEvaluation] = []
    for choice in choices:
        child_values.update(choice.values)
        child_rows.extend(choice.rows)
    root_value = _evaluate_root(
        model,
        threshold,
        solver_kind,
        root,
        child_values,
    )
    return _Policy(
        tuple(
            sorted(
                (root.assignment, *(item.assignment for item in choices)),
                key=lambda item: item.assignment_id,
            )
        ),
        root_value.reward_lower,
        root_value.reward_upper,
        root_value.failure_upper,
        tuple(
            sorted(
                (*root_value.rows, *child_rows),
                key=lambda item: item.provenance.provenance_id,
            )
        ),
    )


def _optimistic_values(
    relevant: Sequence[_Unit],
    selected: Sequence[_Choice],
    unresolved: Sequence[_Unit],
    irrelevant: Sequence[_Choice],
) -> dict[str, _Value]:
    values: dict[str, _Value] = {}
    for choice in (*selected, *irrelevant):
        values.update(choice.values)
    for unit in unresolved:
        for state_id in unit.state_ids:
            candidates = tuple(
                choice.values[state_id] for choice in unit.choices
            )
            lower = max(item.reward_lower for item in candidates)
            values[state_id] = _Value(
                lower,
                max(
                    lower,
                    max(item.reward_upper for item in candidates),
                ),
                min(item.failure_upper for item in candidates),
                (),
            )
    expected = {
        state_id
        for unit in relevant
        for state_id in unit.state_ids
    } | {
        state_id
        for choice in irrelevant
        for state_id in choice.values
    }
    if set(values) != expected:
        _fail("optimistic child rectangle is incomplete")
    return values


def _unrestricted_reward_upper(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
) -> Fraction:
    catalogues, destinations, rows, _ = _registries(model)
    child_values: dict[str, _Value] = {}
    for state_id in _reachable_children(model):
        candidates = tuple(
            _evaluate_row(
                rows[(state_id, 1, action.action_id)],
                destinations=destinations,
                child_values={},
                threshold=threshold,
                category=robust.SelectedRowCategory.CONTINUATION_SELECTED,
                policy_scope_key=state_id,
            )
            for action in catalogues[state_id].actions
        )
        chosen = min(
            candidates,
            key=lambda item: (-item.bound.reward_upper, item.bound.row_id),
        )
        child_values[state_id] = _Value(
            chosen.bound.reward_lower,
            chosen.bound.reward_upper,
            chosen.bound.failure_upper,
            (chosen,),
        )
    return max(
        _evaluate_row(
            rows[(model.root_state_id, 2, action.action_id)],
            destinations=destinations,
            child_values=child_values,
            threshold=threshold,
            category=robust.SelectedRowCategory.ROOT_SELECTED,
            policy_scope_key=model.root_state_id,
        ).bound.reward_upper
        for action in catalogues[model.root_state_id].actions
    )


def _order_key(
    policy: _Policy | _PolicyOrderSummary,
    unrestricted: Fraction,
    threshold: robust.RobustThresholdProfileV1,
) -> tuple[object, ...]:
    regret = max(Fraction(0), unrestricted - policy.reward_lower) / (
        threshold.reward_ceiling
    )
    if (
        policy.failure_upper <= threshold.risk_tolerance
        and regret <= threshold.normalized_regret_tolerance
    ):
        return (
            0,
            -policy.reward_lower,
            policy.failure_upper,
            policy.policy_key,
        )
    if policy.failure_upper <= threshold.risk_tolerance:
        return (
            1,
            regret,
            policy.failure_upper,
            -policy.reward_lower,
            policy.policy_key,
        )
    return (
        2,
        policy.failure_upper,
        policy.failure_upper,
        -policy.reward_lower,
        policy.policy_key,
    )


def _can_prune(
    selected: _Policy | _PolicyOrderSummary,
    *,
    reward_lower_upper_bound: Fraction,
    failure_lower_bound: Fraction,
    minimum_policy_key: tuple[str, ...],
    unrestricted: Fraction,
    threshold: robust.RobustThresholdProfileV1,
) -> bool:
    selected_key = _order_key(selected, unrestricted, threshold)
    category = int(selected_key[0])
    optimistic_regret = max(
        Fraction(0),
        unrestricted - reward_lower_upper_bound,
    ) / threshold.reward_ceiling
    possible_risk = failure_lower_bound <= threshold.risk_tolerance
    possible_certificate = (
        possible_risk
        and optimistic_regret <= threshold.normalized_regret_tolerance
    )
    if category == 0:
        if not possible_certificate:
            return True
        if selected.reward_lower != reward_lower_upper_bound:
            return selected.reward_lower > reward_lower_upper_bound
        if selected.failure_upper != failure_lower_bound:
            return selected.failure_upper < failure_lower_bound
        return selected.policy_key <= minimum_policy_key
    if category == 1:
        if possible_certificate:
            return False
        if not possible_risk:
            return True
        if selected.reward_lower != reward_lower_upper_bound:
            return selected.reward_lower > reward_lower_upper_bound
        if selected.failure_upper != failure_lower_bound:
            return selected.failure_upper < failure_lower_bound
        return selected.policy_key <= minimum_policy_key
    if possible_risk:
        return False
    if selected.failure_upper != failure_lower_bound:
        return selected.failure_upper < failure_lower_bound
    if selected.reward_lower != reward_lower_upper_bound:
        return selected.reward_lower > reward_lower_upper_bound
    return selected.policy_key <= minimum_policy_key


def _minimum_policy_key(
    root: _Root,
    selected: Sequence[_Choice],
    unresolved: Sequence[_Unit],
    irrelevant: Sequence[_Choice],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            (
                root.assignment.assignment_id,
                *(item.assignment.assignment_id for item in selected),
                *(item.default.assignment.assignment_id for item in unresolved),
                *(item.assignment.assignment_id for item in irrelevant),
            )
        )
    )


def _verify_search_proof(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
    proof: lazy.ExactLazyH2SearchProofV1,
    counters: lazy.ExactLazyH2SearchCountersV1,
    *,
    phase: lazy.ExactLazyH2SearchPhase,
) -> _ProofReplay:
    if (
        type(proof) is not lazy.ExactLazyH2SearchProofV1
        or type(counters) is not lazy.ExactLazyH2SearchCountersV1
        or proof.phase is not phase
        or proof.solver_kind is not solver_kind
        or proof.model_id != model.model_id
        or proof.threshold_profile_id != threshold.threshold_profile_id
    ):
        _fail("search proof identity chain does not match the replay input")
    units = _decision_units(model, threshold, solver_kind)
    roots = _roots(model, solver_kind)
    root_by_assignment = {
        item.assignment.assignment_id: item for item in roots
    }
    if proof.root_assignment_ids != tuple(sorted(root_by_assignment)):
        _fail("search proof root domain is incomplete")
    unrestricted = _unrestricted_reward_upper(model, threshold)
    if proof.unrestricted_reward_upper != unrestricted:
        _fail("search proof changed the unrestricted exact reward upper")

    complete_by_root: dict[
        str, list[lazy.ExactLazyH2CompleteNodeWitnessV1]
    ] = {item: [] for item in root_by_assignment}
    pruned_by_root: dict[
        str, list[lazy.ExactLazyH2PrunedNodeWitnessV1]
    ] = {item: [] for item in root_by_assignment}
    for witness in proof.complete_nodes:
        if witness.root_assignment_id not in complete_by_root:
            _fail("complete witness names an unknown root assignment")
        complete_by_root[witness.root_assignment_id].append(witness)
    for witness in proof.pruned_nodes:
        if witness.root_assignment_id not in pruned_by_root:
            _fail("pruned witness names an unknown root assignment")
        pruned_by_root[witness.root_assignment_id].append(witness)

    all_complete: list[_Policy] = []
    branch_nodes = 0
    relevant_count = 0
    irrelevant_count = 0
    selected_proxy = _PolicyOrderSummary(
        proof.selected_reward_lower,
        proof.selected_reward_upper,
        proof.selected_failure_upper,
        proof.selected_policy_key,
    )

    for root_id, root in root_by_assignment.items():
        relevant = tuple(
            sorted(
                (
                    unit
                    for unit in units
                    if root.relevant_state_ids.intersection(unit.state_ids)
                ),
                key=lambda unit: (-len(unit.state_ids), unit.scope_key),
            )
        )
        irrelevant = tuple(
            unit.default
            for unit in units
            if not root.relevant_state_ids.intersection(unit.state_ids)
        )
        scopes = tuple(item.scope_key for item in relevant)
        irrelevant_ids = tuple(
            sorted(item.assignment.assignment_id for item in irrelevant)
        )
        domains = tuple(
            {
                choice.assignment.assignment_id: choice
                for choice in unit.choices
            }
            for unit in relevant
        )
        relevant_count += len(relevant)
        irrelevant_count += len(irrelevant)
        terminals: dict[
            tuple[str, ...],
            lazy.ExactLazyH2CompleteNodeWitnessV1
            | lazy.ExactLazyH2PrunedNodeWitnessV1,
        ] = {}
        for witness in (
            *complete_by_root[root_id],
            *pruned_by_root[root_id],
        ):
            if (
                witness.relevant_scope_keys != scopes
                or witness.irrelevant_assignment_ids != irrelevant_ids
            ):
                _fail("witness domain metadata differs from the model")
            path = witness.selected_assignment_ids
            if len(path) > len(domains):
                _fail("witness path exceeds the root-conditioned domain")
            if any(
                assignment_id not in domains[index]
                for index, assignment_id in enumerate(path)
            ):
                _fail("witness path selects an unavailable action")
            if path in terminals:
                _fail("proof contains duplicate terminal prefixes")
            terminals[path] = witness

        trie: dict[Any, Any] = {}
        marker = object()
        for path, witness in terminals.items():
            node = trie
            for assignment_id in path:
                if marker in node:
                    _fail("terminal proof prefixes overlap")
                node = node.setdefault(assignment_id, {})
            if node:
                _fail("terminal proof prefixes overlap")
            node[marker] = witness

        def validate_node(
            node: dict[Any, Any],
            depth: int,
            selected_choices: tuple[_Choice, ...],
        ) -> None:
            nonlocal branch_nodes
            branch_nodes += 1
            if marker in node:
                if len(node) != 1:
                    _fail("terminal witness has descendants")
                witness = node[marker]
                if type(witness) is lazy.ExactLazyH2CompleteNodeWitnessV1:
                    if depth != len(relevant):
                        _fail("complete witness occurs before a complete policy")
                    policy = _complete_policy(
                        model,
                        threshold,
                        solver_kind,
                        root,
                        (*selected_choices, *irrelevant),
                    )
                    if (
                        witness.policy_key != policy.policy_key
                        or witness.reward_lower != policy.reward_lower
                        or witness.reward_upper != policy.reward_upper
                        or witness.failure_upper != policy.failure_upper
                    ):
                        _fail("complete-node exact evaluation was forged")
                    all_complete.append(policy)
                    return
                if type(witness) is not lazy.ExactLazyH2PrunedNodeWitnessV1:
                    _fail("terminal witness has an unknown type")
                unresolved = relevant[depth:]
                optimistic = _evaluate_root(
                    model,
                    threshold,
                    solver_kind,
                    root,
                    _optimistic_values(
                        relevant,
                        selected_choices,
                        unresolved,
                        irrelevant,
                    ),
                )
                minimum_key = _minimum_policy_key(
                    root,
                    selected_choices,
                    unresolved,
                    irrelevant,
                )
                if (
                    witness.reward_lower_upper_bound
                    != optimistic.reward_lower
                    or witness.failure_lower_bound
                    != optimistic.failure_upper
                    or witness.minimum_policy_key != minimum_key
                    or witness.dominating_policy_key
                    != proof.selected_policy_key
                    or witness.dominating_reward_lower
                    != proof.selected_reward_lower
                    or witness.dominating_failure_upper
                    != proof.selected_failure_upper
                ):
                    _fail("pruned-node completion rectangle was forged")
                if not _can_prune(
                    selected_proxy,
                    reward_lower_upper_bound=optimistic.reward_lower,
                    failure_lower_bound=optimistic.failure_upper,
                    minimum_policy_key=minimum_key,
                    unrestricted=unrestricted,
                    threshold=threshold,
                ):
                    _fail("claimed final policy does not dominate a pruned branch")
                return
            if depth == len(relevant):
                _fail("proof leaves a complete policy unclassified")
            if set(node) != set(domains[depth]):
                _fail("proof prefix does not cover every action extension")
            for assignment_id, choice in domains[depth].items():
                validate_node(
                    node[assignment_id],
                    depth + 1,
                    (*selected_choices, choice),
                )

        validate_node(trie, 0, ())

    selected_matches = tuple(
        policy
        for policy in all_complete
        if (
            policy.policy_key == proof.selected_policy_key
            and policy.reward_lower == proof.selected_reward_lower
            and policy.reward_upper == proof.selected_reward_upper
            and policy.failure_upper == proof.selected_failure_upper
        )
    )
    if len(selected_matches) != 1:
        _fail("selected policy is not one unique complete-node witness")
    selected = selected_matches[0]
    if any(
        _order_key(selected, unrestricted, threshold)
        > _order_key(candidate, unrestricted, threshold)
        for candidate in all_complete
    ):
        _fail("a completed witness ranks ahead of the selected policy")
    selected_category = int(_order_key(selected, unrestricted, threshold)[0])
    status = (
        robust.RobustAuditStatus.CERTIFIED
        if selected_category == 0
        else robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
    )
    expected_counters = (
        branch_nodes,
        len(proof.complete_nodes),
        branch_nodes,
        len(proof.pruned_nodes),
        len(roots),
        relevant_count,
        irrelevant_count,
    )
    actual_counters = (
        counters.branch_nodes,
        counters.complete_policies,
        counters.root_bound_evaluations,
        counters.pruned_branches,
        counters.root_actions_considered,
        counters.relevant_decision_units,
        counters.irrelevant_decision_units,
    )
    if actual_counters != expected_counters:
        _fail("search counters do not reconcile with the prefix-cover proof")
    return _ProofReplay(
        selected,
        unrestricted,
        status,
        branch_nodes,
        len(proof.complete_nodes),
        len(proof.pruned_nodes),
    )


def _zero_other_model(
    model: robust.PartialSupportIntervalModelV1,
) -> robust.PartialSupportIntervalModelV1:
    other_id = model.other_destination.destination_id
    rows = tuple(
        replace(
            row,
            masses=tuple(
                (
                    robust.IntervalDestinationMassV1(
                        mass.destination_id,
                        Fraction(0),
                        Fraction(0),
                    )
                    if mass.destination_id == other_id
                    else mass
                )
                for mass in row.masses
            ),
        )
        for row in model.rows
    )
    return robust.build_partial_support_model_v1(
        context_id=model.context_id,
        root_state_id=model.root_state_id,
        catalogues=model.catalogues,
        destinations=model.destinations,
        rows=rows,
        concretizer_entries=model.concretizer_entries,
    )


def _build_audit(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
    original: _ProofReplay,
    counterfactual: robust.OtherOnlyCounterfactualV1,
) -> robust.RobustPlanAuditV1:
    bounds = tuple(
        sorted(
            (item.bound for item in original.selected.rows),
            key=lambda item: item.row_bound_id,
        )
    )
    provenance = tuple(
        sorted(
            (item.provenance for item in original.selected.rows),
            key=lambda item: item.provenance_id,
        )
    )
    category_by_row = {item.row_id: item.category for item in provenance}
    other = tuple(
        sorted(
            (
                robust.OtherMassProvenanceV1(
                    item.row_id,
                    item.remaining_horizon,
                    category_by_row[item.row_id],
                    item.other_mass_upper,
                )
                for item in bounds
            ),
            key=lambda item: item.other_mass_provenance_id,
        )
    )
    regret = max(
        Fraction(0),
        original.unrestricted_reward_upper
        - original.selected.reward_lower,
    ) / threshold.reward_ceiling
    frontier = None
    if original.status is robust.RobustAuditStatus.FAILED_PROOF_FRONTIER:
        risk_failed = (
            original.selected.failure_upper >= threshold.risk_tolerance
        )
        regret_failed = regret > threshold.normalized_regret_tolerance
        reason = (
            robust.FailedFrontierReason.RISK_AND_REGRET
            if risk_failed and regret_failed
            else (
                robust.FailedFrontierReason.RISK
                if risk_failed
                else robust.FailedFrontierReason.REGRET
            )
        )
        frontier = robust.FailedProofFrontierV1(
            reason,
            tuple(sorted(item.row_id for item in bounds)),
            tuple(
                sorted(
                    item.row_id
                    for item in bounds
                    if item.other_mass_upper > 0
                )
            ),
            counterfactual.changes_failed_to_certified,
        )
    return robust.RobustPlanAuditV1(
        solver_kind,
        model.model_id,
        threshold.threshold_profile_id,
        original.status,
        original.selected.assignments,
        bounds,
        provenance,
        other,
        original.selected.reward_lower,
        original.unrestricted_reward_upper,
        original.selected.failure_upper,
        regret,
        counterfactual,
        frontier,
    )


def _legacy_assignment_count(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
) -> int:
    units = _decision_units(model, threshold, solver_kind)
    total = len(_roots(model, solver_kind))
    for unit in units:
        total *= len(unit.choices)
    return total


def verify_exact_lazy_h2_solve_result_v1(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    claimed: lazy.ExactLazyH2SolveResultV1,
) -> ExactLazyH2IndependentVerificationV1:
    """Independently replay a solved lazy result and its complete proof cover."""

    if (
        type(model) is not robust.PartialSupportIntervalModelV1
        or type(threshold) is not robust.RobustThresholdProfileV1
        or type(claimed) is not lazy.ExactLazyH2SolveResultV1
        or claimed.status is not lazy.ExactLazyH2SolveStatus.SOLVED
        or type(claimed.audit) is not robust.RobustPlanAuditV1
        or type(claimed.trace) is not lazy.ExactLazyH2SearchTraceV1
        or claimed.exhaustion is not None
        or threshold.context_id != model.context_id
        or claimed.audit.model_id != model.model_id
        or claimed.audit.threshold_profile_id
        != threshold.threshold_profile_id
        or claimed.audit.solver_kind is not claimed.solver_kind
        or claimed.trace.solver_kind is not claimed.solver_kind
        or claimed.trace.independent_prune_witness_verifier_implemented
        is not True
    ):
        _fail("claimed lazy result or identity chain is invalid")

    original = _verify_search_proof(
        model,
        threshold,
        claimed.solver_kind,
        claimed.trace.original_proof,
        claimed.trace.original,
        phase=lazy.ExactLazyH2SearchPhase.ORIGINAL,
    )
    zero_proof_id = None
    zero_replay = None
    if original.status is robust.RobustAuditStatus.CERTIFIED:
        if (
            claimed.trace.zero_other_counterfactual is not None
            or claimed.trace.zero_other_counterfactual_proof is not None
        ):
            _fail("certified original search must not carry a zero-OTHER proof")
        counterfactual = robust.OtherOnlyCounterfactualV1(
            robust.CounterfactualStatus.ORIGINAL_ALREADY_CERTIFIED,
            True,
            None,
            False,
            None,
            None,
            None,
        )
    else:
        try:
            zero_model = _zero_other_model(model)
        except robust.PartialSupportRobustPlannerInvariantViolation:
            if (
                claimed.trace.zero_other_counterfactual is not None
                or claimed.trace.zero_other_counterfactual_proof is not None
            ):
                _fail("infeasible zero-OTHER simplex cannot carry a proof")
            counterfactual = robust.OtherOnlyCounterfactualV1(
                robust.CounterfactualStatus.ZERO_OTHER_INFEASIBLE_SIMPLEX,
                False,
                None,
                False,
                None,
                None,
                None,
            )
        else:
            if (
                claimed.trace.zero_other_counterfactual is None
                or claimed.trace.zero_other_counterfactual_proof is None
            ):
                _fail("valid zero-OTHER model requires an independent proof")
            zero_replay = _verify_search_proof(
                zero_model,
                threshold,
                claimed.solver_kind,
                claimed.trace.zero_other_counterfactual_proof,
                claimed.trace.zero_other_counterfactual,
                phase=(
                    lazy.ExactLazyH2SearchPhase.ZERO_OTHER_COUNTERFACTUAL
                ),
            )
            zero_proof_id = (
                claimed.trace.zero_other_counterfactual_proof.proof_id
            )
            certified = (
                zero_replay.status is robust.RobustAuditStatus.CERTIFIED
            )
            zero_regret = max(
                Fraction(0),
                zero_replay.unrestricted_reward_upper
                - zero_replay.selected.reward_lower,
            ) / threshold.reward_ceiling
            counterfactual = robust.OtherOnlyCounterfactualV1(
                (
                    robust.CounterfactualStatus.ZERO_OTHER_CERTIFIED
                    if certified
                    else robust.CounterfactualStatus.ZERO_OTHER_STILL_FAILED
                ),
                False,
                certified,
                certified,
                zero_model.model_id,
                zero_replay.selected.failure_upper,
                zero_regret,
            )

    rebuilt = _build_audit(
        model,
        threshold,
        claimed.solver_kind,
        original,
        counterfactual,
    )
    if (
        rebuilt != claimed.audit
        or rebuilt.audit_id != claimed.audit.audit_id
        or canonical_json_bytes(rebuilt.to_document())
        != canonical_json_bytes(claimed.audit.to_document())
    ):
        _fail("claimed RobustPlanAuditV1 differs from independent rebuild")

    legacy_compared = (
        _legacy_assignment_count(
            model,
            threshold,
            claimed.solver_kind,
        )
        <= robust.MAX_POLICY_ASSIGNMENTS
    )
    if legacy_compared:
        legacy = (
            robust.solve_ground_direct_robust_h2_v1(model, threshold)
            if claimed.solver_kind
            is robust.RobustSolverKind.GROUND_DIRECT
            else robust.solve_quotient_robust_h2_v1(model, threshold)
        )
        if canonical_json_bytes(legacy.to_document()) != (
            canonical_json_bytes(claimed.audit.to_document())
        ):
            _fail("lazy audit differs from exhaustive legacy canonical bytes")

    zero_branch_nodes = 0 if zero_replay is None else zero_replay.branch_nodes
    zero_complete = 0 if zero_replay is None else zero_replay.complete_nodes
    zero_pruned = 0 if zero_replay is None else zero_replay.pruned_nodes
    return ExactLazyH2IndependentVerificationV1(
        model.model_id,
        threshold.threshold_profile_id,
        claimed.audit.audit_id,
        claimed.trace.original_proof.proof_id,
        zero_proof_id,
        claimed.solver_kind,
        original.branch_nodes + zero_branch_nodes,
        original.complete_nodes + zero_complete,
        original.pruned_nodes + zero_pruned,
        legacy_compared,
    )


__all__ = [
    "ExactLazyH2IndependentVerificationError",
    "ExactLazyH2IndependentVerificationV1",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "verify_exact_lazy_h2_solve_result_v1",
]
