"""Exact lazy H=2 robust planning without Cartesian policy materialization.

This module is a drop-in *semantic* alternative to the V0 partial-support
planner.  It deliberately reuses the V0 model, threshold, policy, row-bound,
and audit objects, so a solved audit has exactly the same bytes and content ID
as exhaustive V0 enumeration.

The search is root-conditioned.  For each root action it expands only
continuation decision units that can affect that root row.  Remaining units
are completed with the assignment that minimizes the frozen policy-key
tie-break.  Exact ``Fraction`` completion rectangles provide an optimistic
reward lower bound and an optimistic failure lower bound; branches that
cannot beat the current complete policy are pruned.  The trace and resource
outcome are intentionally outside ``RobustPlanAuditV1``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Mapping, Sequence

import acfqp.partial_support_robust_planner_v1 as robust
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "exact_lazy_h2_robust_branch_and_bound_v0"

DOMAIN_TAGS = {
    "complete_witness": "acfqp:exact-lazy-h2-complete-node-witness:v1",
    "pruned_witness": "acfqp:exact-lazy-h2-pruned-node-witness:v1",
    "search_proof": "acfqp:exact-lazy-h2-search-proof:v1",
}


class ExactLazyH2InvariantViolation(ValueError):
    """The lazy-search request or an internal exactness invariant is invalid."""


class ExactLazyH2SolveStatus(str, Enum):
    SOLVED = "SOLVED"
    EXACT_DP_RESOURCE_EXHAUSTED = "EXACT_DP_RESOURCE_EXHAUSTED"


class ExactLazyH2ResourceCode(str, Enum):
    MAX_BRANCH_NODES = "MAX_BRANCH_NODES"
    MAX_COMPLETE_POLICIES = "MAX_COMPLETE_POLICIES"
    MAX_ROOT_BOUND_EVALUATIONS = "MAX_ROOT_BOUND_EVALUATIONS"


class ExactLazyH2SearchPhase(str, Enum):
    ORIGINAL = "ORIGINAL"
    ZERO_OTHER_COUNTERFACTUAL = "ZERO_OTHER_COUNTERFACTUAL"


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise ExactLazyH2InvariantViolation(str(error)) from error
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ExactLazyH2InvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise ExactLazyH2InvariantViolation(
            "proof arithmetic must use exact Fraction values"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _id_tuple(
    values: tuple[str, ...],
    field: str,
    *,
    sorted_distinct: bool = False,
) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise ExactLazyH2InvariantViolation(f"{field} must be a tuple")
    for value in values:
        _cid(value, field)
    if len(values) != len(set(values)):
        raise ExactLazyH2InvariantViolation(f"{field} contains duplicates")
    if sorted_distinct and values != tuple(sorted(values)):
        raise ExactLazyH2InvariantViolation(f"{field} must be sorted")
    return values


@dataclass(frozen=True, slots=True)
class ExactLazyH2CompleteNodeWitnessV1:
    """One explicitly evaluated terminal leaf in a root-conditioned tree."""

    root_assignment_id: str
    relevant_scope_keys: tuple[str, ...]
    selected_assignment_ids: tuple[str, ...]
    irrelevant_assignment_ids: tuple[str, ...]
    policy_key: tuple[str, ...]
    reward_lower: Fraction
    reward_upper: Fraction
    failure_upper: Fraction

    def __post_init__(self) -> None:
        _cid(self.root_assignment_id, "complete witness root assignment")
        _id_tuple(
            self.relevant_scope_keys,
            "complete witness relevant scopes",
        )
        _id_tuple(
            self.selected_assignment_ids,
            "complete witness selected assignments",
        )
        _id_tuple(
            self.irrelevant_assignment_ids,
            "complete witness irrelevant assignments",
            sorted_distinct=True,
        )
        _id_tuple(
            self.policy_key,
            "complete witness policy key",
            sorted_distinct=True,
        )
        if len(self.selected_assignment_ids) != len(
            self.relevant_scope_keys
        ):
            raise ExactLazyH2InvariantViolation(
                "complete witness does not assign every relevant scope"
            )
        for value in (
            self.reward_lower,
            self.reward_upper,
            self.failure_upper,
        ):
            if type(value) is not Fraction or value < 0:
                raise ExactLazyH2InvariantViolation(
                    "complete witness bounds must be nonnegative Fractions"
                )
        if self.reward_lower > self.reward_upper or self.failure_upper > 1:
            raise ExactLazyH2InvariantViolation(
                "complete witness exact bounds are inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.exact_lazy_h2_complete_node_witness.v1",
            "schema_version": SCHEMA_VERSION,
            "root_assignment_id": self.root_assignment_id,
            "relevant_scope_keys": list(self.relevant_scope_keys),
            "selected_assignment_ids": list(self.selected_assignment_ids),
            "irrelevant_assignment_ids": list(
                self.irrelevant_assignment_ids
            ),
            "policy_key": list(self.policy_key),
            "reward_lower": _fdoc(self.reward_lower),
            "reward_upper": _fdoc(self.reward_upper),
            "failure_upper": _fdoc(self.failure_upper),
        }

    @property
    def witness_id(self) -> str:
        return _content_id("complete_witness", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "witness_id": self.witness_id}


@dataclass(frozen=True, slots=True)
class ExactLazyH2PrunedNodeWitnessV1:
    """One omitted subtree and its exact optimistic completion rectangle."""

    root_assignment_id: str
    relevant_scope_keys: tuple[str, ...]
    selected_assignment_ids: tuple[str, ...]
    irrelevant_assignment_ids: tuple[str, ...]
    reward_lower_upper_bound: Fraction
    failure_lower_bound: Fraction
    minimum_policy_key: tuple[str, ...]
    dominating_policy_key: tuple[str, ...]
    dominating_reward_lower: Fraction
    dominating_failure_upper: Fraction

    def __post_init__(self) -> None:
        _cid(self.root_assignment_id, "pruned witness root assignment")
        _id_tuple(
            self.relevant_scope_keys,
            "pruned witness relevant scopes",
        )
        _id_tuple(
            self.selected_assignment_ids,
            "pruned witness selected assignments",
        )
        _id_tuple(
            self.irrelevant_assignment_ids,
            "pruned witness irrelevant assignments",
            sorted_distinct=True,
        )
        _id_tuple(
            self.minimum_policy_key,
            "pruned witness minimum policy key",
            sorted_distinct=True,
        )
        _id_tuple(
            self.dominating_policy_key,
            "pruned witness dominating policy key",
            sorted_distinct=True,
        )
        if len(self.selected_assignment_ids) > len(
            self.relevant_scope_keys
        ):
            raise ExactLazyH2InvariantViolation(
                "pruned witness prefix exceeds its relevant scope domain"
            )
        for value in (
            self.reward_lower_upper_bound,
            self.failure_lower_bound,
            self.dominating_reward_lower,
            self.dominating_failure_upper,
        ):
            if type(value) is not Fraction or value < 0:
                raise ExactLazyH2InvariantViolation(
                    "pruned witness bounds must be nonnegative Fractions"
                )
        if (
            self.failure_lower_bound > 1
            or self.dominating_failure_upper > 1
        ):
            raise ExactLazyH2InvariantViolation(
                "pruned witness failure values exceed one"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.exact_lazy_h2_pruned_node_witness.v1",
            "schema_version": SCHEMA_VERSION,
            "root_assignment_id": self.root_assignment_id,
            "relevant_scope_keys": list(self.relevant_scope_keys),
            "selected_assignment_ids": list(self.selected_assignment_ids),
            "irrelevant_assignment_ids": list(
                self.irrelevant_assignment_ids
            ),
            "reward_lower_upper_bound": _fdoc(
                self.reward_lower_upper_bound
            ),
            "failure_lower_bound": _fdoc(self.failure_lower_bound),
            "minimum_policy_key": list(self.minimum_policy_key),
            "dominating_policy_key": list(self.dominating_policy_key),
            "dominating_reward_lower": _fdoc(
                self.dominating_reward_lower
            ),
            "dominating_failure_upper": _fdoc(
                self.dominating_failure_upper
            ),
        }

    @property
    def witness_id(self) -> str:
        return _content_id("pruned_witness", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "witness_id": self.witness_id}


@dataclass(frozen=True, slots=True)
class ExactLazyH2SearchProofV1:
    """Content-addressed prefix cover for one exact lazy search phase."""

    phase: ExactLazyH2SearchPhase
    solver_kind: robust.RobustSolverKind
    model_id: str
    threshold_profile_id: str
    root_assignment_ids: tuple[str, ...]
    selected_policy_key: tuple[str, ...]
    selected_reward_lower: Fraction
    selected_reward_upper: Fraction
    selected_failure_upper: Fraction
    unrestricted_reward_upper: Fraction
    complete_nodes: tuple[ExactLazyH2CompleteNodeWitnessV1, ...]
    pruned_nodes: tuple[ExactLazyH2PrunedNodeWitnessV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.phase) is not ExactLazyH2SearchPhase
            or type(self.solver_kind) is not robust.RobustSolverKind
        ):
            raise ExactLazyH2InvariantViolation(
                "search proof enums are invalid"
            )
        _cid(self.model_id, "search proof model")
        _cid(self.threshold_profile_id, "search proof threshold")
        _id_tuple(
            self.root_assignment_ids,
            "search proof root assignments",
            sorted_distinct=True,
        )
        _id_tuple(
            self.selected_policy_key,
            "search proof selected policy",
            sorted_distinct=True,
        )
        for values, expected_type, field in (
            (
                self.complete_nodes,
                ExactLazyH2CompleteNodeWitnessV1,
                "complete nodes",
            ),
            (
                self.pruned_nodes,
                ExactLazyH2PrunedNodeWitnessV1,
                "pruned nodes",
            ),
        ):
            if (
                type(values) is not tuple
                or any(type(item) is not expected_type for item in values)
                or tuple(item.witness_id for item in values)
                != tuple(sorted({item.witness_id for item in values}))
            ):
                raise ExactLazyH2InvariantViolation(
                    f"search proof {field} must be distinct and ID sorted"
                )
        if not self.complete_nodes:
            raise ExactLazyH2InvariantViolation(
                "search proof requires at least one complete policy"
            )
        for value in (
            self.selected_reward_lower,
            self.selected_reward_upper,
            self.selected_failure_upper,
            self.unrestricted_reward_upper,
        ):
            if type(value) is not Fraction or value < 0:
                raise ExactLazyH2InvariantViolation(
                    "search proof values must be nonnegative Fractions"
                )
        if (
            self.selected_reward_lower > self.selected_reward_upper
            or self.selected_failure_upper > 1
        ):
            raise ExactLazyH2InvariantViolation(
                "search proof selected bounds are inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.exact_lazy_h2_search_proof.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "phase": self.phase.value,
            "solver_kind": self.solver_kind.value,
            "model_id": self.model_id,
            "threshold_profile_id": self.threshold_profile_id,
            "root_assignment_ids": list(self.root_assignment_ids),
            "selected_policy_key": list(self.selected_policy_key),
            "selected_reward_lower": _fdoc(self.selected_reward_lower),
            "selected_reward_upper": _fdoc(self.selected_reward_upper),
            "selected_failure_upper": _fdoc(self.selected_failure_upper),
            "unrestricted_reward_upper": _fdoc(
                self.unrestricted_reward_upper
            ),
            "complete_node_ids": [
                item.witness_id for item in self.complete_nodes
            ],
            "pruned_node_ids": [
                item.witness_id for item in self.pruned_nodes
            ],
        }

    @property
    def proof_id(self) -> str:
        return _content_id("search_proof", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "complete_nodes": [
                item.to_document() for item in self.complete_nodes
            ],
            "pruned_nodes": [
                item.to_document() for item in self.pruned_nodes
            ],
            "proof_id": self.proof_id,
        }


@dataclass(frozen=True, slots=True)
class ExactLazyH2ResourceLimitsV1:
    """Hard exact-search limits; exhaustion never returns an approximate audit."""

    max_branch_nodes: int = 10_000_000
    max_complete_policies: int = 1_000_000
    max_root_bound_evaluations: int = 10_000_000

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value <= 0
            for value in (
                self.max_branch_nodes,
                self.max_complete_policies,
                self.max_root_bound_evaluations,
            )
        ):
            raise ExactLazyH2InvariantViolation(
                "exact lazy H2 resource limits must be positive integers"
            )


@dataclass(frozen=True, slots=True)
class ExactLazyH2SearchCountersV1:
    branch_nodes: int
    complete_policies: int
    root_bound_evaluations: int
    pruned_branches: int
    root_actions_considered: int
    relevant_decision_units: int
    irrelevant_decision_units: int

    def __post_init__(self) -> None:
        values = (
            self.branch_nodes,
            self.complete_policies,
            self.root_bound_evaluations,
            self.pruned_branches,
            self.root_actions_considered,
            self.relevant_decision_units,
            self.irrelevant_decision_units,
        )
        if any(type(value) is not int or value < 0 for value in values):
            raise ExactLazyH2InvariantViolation(
                "exact lazy H2 counters must be nonnegative integers"
            )


@dataclass(frozen=True, slots=True)
class ExactLazyH2SearchTraceV1:
    """Diagnostic proof trace that is not referenced by the V0 audit payload."""

    solver_kind: robust.RobustSolverKind
    original: ExactLazyH2SearchCountersV1
    zero_other_counterfactual: ExactLazyH2SearchCountersV1 | None
    original_proof: ExactLazyH2SearchProofV1
    zero_other_counterfactual_proof: ExactLazyH2SearchProofV1 | None
    exact_fraction_semantics: bool = True
    enters_robust_audit_payload: bool = False
    independent_prune_witness_verifier_implemented: bool = True

    def __post_init__(self) -> None:
        if (
            type(self.solver_kind) is not robust.RobustSolverKind
            or type(self.original) is not ExactLazyH2SearchCountersV1
            or (
                self.zero_other_counterfactual is not None
                and type(self.zero_other_counterfactual)
                is not ExactLazyH2SearchCountersV1
            )
            or type(self.original_proof) is not ExactLazyH2SearchProofV1
            or (
                self.zero_other_counterfactual_proof is not None
                and type(self.zero_other_counterfactual_proof)
                is not ExactLazyH2SearchProofV1
            )
            or self.original_proof.phase
            is not ExactLazyH2SearchPhase.ORIGINAL
            or self.original_proof.solver_kind is not self.solver_kind
            or (
                (self.zero_other_counterfactual is None)
                != (self.zero_other_counterfactual_proof is None)
            )
            or (
                self.zero_other_counterfactual_proof is not None
                and (
                    self.zero_other_counterfactual_proof.phase
                    is not ExactLazyH2SearchPhase.ZERO_OTHER_COUNTERFACTUAL
                    or self.zero_other_counterfactual_proof.solver_kind
                    is not self.solver_kind
                )
            )
            or self.exact_fraction_semantics is not True
            or self.enters_robust_audit_payload is not False
            or self.independent_prune_witness_verifier_implemented is not True
        ):
            raise ExactLazyH2InvariantViolation(
                "exact lazy H2 trace crosses the frozen audit boundary"
            )


@dataclass(frozen=True, slots=True)
class ExactLazyH2ResourceExhaustionV1:
    phase: ExactLazyH2SearchPhase
    code: ExactLazyH2ResourceCode
    observed: int
    limit: int
    counters: ExactLazyH2SearchCountersV1
    terminal_code: str = "EXACT_DP_RESOURCE_EXHAUSTED"
    approximate_audit_emitted: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.phase) is not ExactLazyH2SearchPhase
            or type(self.code) is not ExactLazyH2ResourceCode
            or type(self.observed) is not int
            or type(self.limit) is not int
            or self.observed <= self.limit
            or self.limit <= 0
            or type(self.counters) is not ExactLazyH2SearchCountersV1
            or self.terminal_code != "EXACT_DP_RESOURCE_EXHAUSTED"
            or self.approximate_audit_emitted is not False
        ):
            raise ExactLazyH2InvariantViolation(
                "typed exact-search exhaustion is inconsistent"
            )


@dataclass(frozen=True, slots=True)
class ExactLazyH2SolveResultV1:
    status: ExactLazyH2SolveStatus
    solver_kind: robust.RobustSolverKind
    audit: robust.RobustPlanAuditV1 | None
    trace: ExactLazyH2SearchTraceV1 | None
    exhaustion: ExactLazyH2ResourceExhaustionV1 | None

    def __post_init__(self) -> None:
        solved = self.status is ExactLazyH2SolveStatus.SOLVED
        if (
            type(self.status) is not ExactLazyH2SolveStatus
            or type(self.solver_kind) is not robust.RobustSolverKind
            or (
                solved
                and (
                    type(self.audit) is not robust.RobustPlanAuditV1
                    or type(self.trace) is not ExactLazyH2SearchTraceV1
                    or self.exhaustion is not None
                    or self.audit.solver_kind is not self.solver_kind
                )
            )
            or (
                not solved
                and (
                    self.audit is not None
                    or self.trace is not None
                    or type(self.exhaustion)
                    is not ExactLazyH2ResourceExhaustionV1
                )
            )
        ):
            raise ExactLazyH2InvariantViolation(
                "exact lazy H2 result status and payload disagree"
            )


@dataclass(slots=True)
class _MutableCounters:
    branch_nodes: int = 0
    complete_policies: int = 0
    root_bound_evaluations: int = 0
    pruned_branches: int = 0
    root_actions_considered: int = 0
    relevant_decision_units: int = 0
    irrelevant_decision_units: int = 0

    def freeze(self) -> ExactLazyH2SearchCountersV1:
        return ExactLazyH2SearchCountersV1(
            self.branch_nodes,
            self.complete_policies,
            self.root_bound_evaluations,
            self.pruned_branches,
            self.root_actions_considered,
            self.relevant_decision_units,
            self.irrelevant_decision_units,
        )


class _ResourceReached(RuntimeError):
    def __init__(
        self,
        code: ExactLazyH2ResourceCode,
        observed: int,
        limit: int,
        counters: _MutableCounters,
    ) -> None:
        super().__init__(code.value)
        self.code = code
        self.observed = observed
        self.limit = limit
        self.counters = counters.freeze()


@dataclass(frozen=True, slots=True)
class _DecisionChoice:
    action_key: str
    assignment: robust.RobustPolicyAssignmentV1
    state_values: Mapping[str, robust._StateActionEvaluation]
    rows: tuple[robust._RowEvaluation, ...]


@dataclass(frozen=True, slots=True)
class _DecisionUnit:
    scope_key: str
    state_ids: tuple[str, ...]
    choices: tuple[_DecisionChoice, ...]

    @property
    def lexicographic_default(self) -> _DecisionChoice:
        return min(
            self.choices,
            key=lambda item: item.assignment.assignment_id,
        )


@dataclass(frozen=True, slots=True)
class _RootChoice:
    action_key: str
    assignment: robust.RobustPolicyAssignmentV1
    relevant_state_ids: frozenset[str]


@dataclass(frozen=True, slots=True)
class _RawCompleteWitness:
    root: _RootChoice
    relevant_scope_keys: tuple[str, ...]
    selected: tuple[_DecisionChoice, ...]
    irrelevant: tuple[_DecisionChoice, ...]
    evaluation: robust._PolicyEvaluation


@dataclass(frozen=True, slots=True)
class _RawPrunedWitness:
    root: _RootChoice
    relevant_scope_keys: tuple[str, ...]
    selected: tuple[_DecisionChoice, ...]
    irrelevant: tuple[_DecisionChoice, ...]
    reward_lower_upper_bound: Fraction
    failure_lower_bound: Fraction
    minimum_policy_key: tuple[str, ...]


def _validate_inputs(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
) -> None:
    if (
        type(model) is not robust.PartialSupportIntervalModelV1
        or type(threshold) is not robust.RobustThresholdProfileV1
        or type(solver_kind) is not robust.RobustSolverKind
        or threshold.context_id != model.context_id
    ):
        raise ExactLazyH2InvariantViolation(
            "exact lazy H2 inputs or identities do not match"
        )
    if (
        solver_kind is robust.RobustSolverKind.QUOTIENT
        and not model.concretizer_entries
    ):
        raise ExactLazyH2InvariantViolation(
            "quotient exact lazy H2 planning requires concretizer entries"
        )


def _direct_units(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
) -> tuple[_DecisionUnit, ...]:
    catalogue_by_state, destination_by_id, row_by_key = robust._registries(model)
    units: list[_DecisionUnit] = []
    for state_id in robust._reachable_child_states(model):
        choices: list[_DecisionChoice] = []
        for action in catalogue_by_state[state_id].actions:
            row = row_by_key[(state_id, 1, action.action_id)]
            evaluated = robust._evaluate_ground_row(
                row,
                destination_by_id=destination_by_id,
                child_values={},
                threshold=threshold,
                category=robust.SelectedRowCategory.CONTINUATION_SELECTED,
                policy_scope_key=state_id,
            )
            value = robust._StateActionEvaluation(
                evaluated.bound.reward_lower,
                evaluated.bound.reward_upper,
                evaluated.bound.failure_upper,
                (evaluated,),
            )
            choices.append(
                _DecisionChoice(
                    action.action_id,
                    robust.RobustPolicyAssignmentV1(
                        robust.PolicyScope.GROUND_STATE,
                        state_id,
                        1,
                        action.action_id,
                    ),
                    {state_id: value},
                    (evaluated,),
                )
            )
        units.append(
            _DecisionUnit(
                state_id,
                (state_id,),
                tuple(choices),
            )
        )
    return tuple(units)


def _quotient_units(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
) -> tuple[_DecisionUnit, ...]:
    catalogue_by_state, _, _ = robust._registries(model)
    child_cells: dict[str, tuple[str, ...]] = {}
    for state_id in robust._reachable_child_states(model):
        cell = catalogue_by_state[state_id].state_coordinate_key
        child_cells[cell] = tuple(
            sorted((*child_cells.get(cell, ()), state_id))
        )

    units: list[_DecisionUnit] = []
    for cell in sorted(child_cells):
        state_ids = child_cells[cell]
        choices: list[_DecisionChoice] = []
        for action_key in robust._common_abstract_actions(model, state_ids):
            values: dict[str, robust._StateActionEvaluation] = {}
            rows: list[robust._RowEvaluation] = []
            for state_id in state_ids:
                value = robust._evaluate_concretized_state_action(
                    model,
                    threshold,
                    state_id=state_id,
                    remaining_horizon=1,
                    abstract_action_key=action_key,
                    child_values={},
                    category=(
                        robust.SelectedRowCategory
                        .CONTINUATION_CONCRETIZER_COMPONENT
                    ),
                )
                values[state_id] = value
                rows.extend(value.rows)
            choices.append(
                _DecisionChoice(
                    action_key,
                    robust.RobustPolicyAssignmentV1(
                        robust.PolicyScope.QUOTIENT_CELL,
                        cell,
                        1,
                        action_key,
                    ),
                    values,
                    tuple(rows),
                )
            )
        units.append(_DecisionUnit(cell, state_ids, tuple(choices)))
    return tuple(units)


def _root_choices(
    model: robust.PartialSupportIntervalModelV1,
    solver_kind: robust.RobustSolverKind,
) -> tuple[_RootChoice, ...]:
    catalogue_by_state, destination_by_id, row_by_key = robust._registries(model)
    root_catalogue = catalogue_by_state[model.root_state_id]
    root_cell = root_catalogue.state_coordinate_key
    concretizers = robust._concretizer_registry(model)

    if solver_kind is robust.RobustSolverKind.GROUND_DIRECT:
        raw = tuple(
            (
                action.action_id,
                (row_by_key[(model.root_state_id, 2, action.action_id)],),
            )
            for action in root_catalogue.actions
        )
        scope = robust.PolicyScope.GROUND_STATE
        scope_key = model.root_state_id
    else:
        raw_items: list[
            tuple[str, tuple[robust.IntervalSimplexRowV1, ...]]
        ] = []
        for action_key in robust._common_abstract_actions(
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
                        row_by_key[
                            (model.root_state_id, 2, ground_action_id)
                        ]
                        for ground_action_id in entry.ground_action_ids
                    ),
                )
            )
        raw = tuple(raw_items)
        scope = robust.PolicyScope.QUOTIENT_CELL
        scope_key = root_cell

    output: list[_RootChoice] = []
    for action_key, rows in raw:
        relevant: set[str] = set()
        for row in rows:
            for mass in row.masses:
                destination = destination_by_id[mass.destination_id]
                if (
                    mass.upper > 0
                    and destination.category
                    is robust.DestinationCategory.ACTIVE_STATE
                ):
                    assert destination.state_id is not None
                    relevant.add(destination.state_id)
        output.append(
            _RootChoice(
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
    root: _RootChoice,
    child_values: Mapping[str, robust._StateActionEvaluation],
) -> robust._StateActionEvaluation:
    if solver_kind is robust.RobustSolverKind.GROUND_DIRECT:
        _, destination_by_id, row_by_key = robust._registries(model)
        evaluated = robust._evaluate_ground_row(
            row_by_key[(model.root_state_id, 2, root.action_key)],
            destination_by_id=destination_by_id,
            child_values=child_values,
            threshold=threshold,
            category=robust.SelectedRowCategory.ROOT_SELECTED,
            policy_scope_key=model.root_state_id,
        )
        return robust._StateActionEvaluation(
            evaluated.bound.reward_lower,
            evaluated.bound.reward_upper,
            evaluated.bound.failure_upper,
            (evaluated,),
        )
    return robust._evaluate_concretized_state_action(
        model,
        threshold,
        state_id=model.root_state_id,
        remaining_horizon=2,
        abstract_action_key=root.action_key,
        child_values=child_values,
        category=robust.SelectedRowCategory.ROOT_CONCRETIZER_COMPONENT,
    )


def _policy_order_key(
    item: robust._PolicyEvaluation,
    unrestricted_reward_upper: Fraction,
    threshold: robust.RobustThresholdProfileV1,
) -> tuple[object, ...]:
    regret = max(
        Fraction(0),
        unrestricted_reward_upper - item.reward_lower,
    ) / threshold.reward_ceiling
    if (
        item.failure_upper <= threshold.risk_tolerance
        and regret <= threshold.normalized_regret_tolerance
    ):
        return (0, -item.reward_lower, item.failure_upper, item.policy_key)
    if item.failure_upper <= threshold.risk_tolerance:
        return (
            1,
            regret,
            item.failure_upper,
            -item.reward_lower,
            item.policy_key,
        )
    return (
        2,
        item.failure_upper,
        item.failure_upper,
        -item.reward_lower,
        item.policy_key,
    )


def _minimum_completion_policy_key(
    root: _RootChoice,
    fixed: Sequence[_DecisionChoice],
    unresolved: Sequence[_DecisionUnit],
    irrelevant: Sequence[_DecisionChoice],
) -> tuple[str, ...]:
    assignments = (
        root.assignment,
        *(item.assignment for item in fixed),
        *(item.lexicographic_default.assignment for item in unresolved),
        *(item.assignment for item in irrelevant),
    )
    return tuple(sorted(item.assignment_id for item in assignments))


def _can_prune(
    incumbent: robust._PolicyEvaluation | None,
    *,
    reward_lower_upper_bound: Fraction,
    failure_lower_bound: Fraction,
    minimum_policy_key: tuple[str, ...],
    unrestricted_reward_upper: Fraction,
    threshold: robust.RobustThresholdProfileV1,
) -> bool:
    if incumbent is None:
        return False
    incumbent_key = _policy_order_key(
        incumbent,
        unrestricted_reward_upper,
        threshold,
    )
    category = int(incumbent_key[0])
    optimistic_regret = max(
        Fraction(0),
        unrestricted_reward_upper - reward_lower_upper_bound,
    ) / threshold.reward_ceiling
    possible_risk = failure_lower_bound <= threshold.risk_tolerance
    possible_certificate = (
        possible_risk
        and optimistic_regret <= threshold.normalized_regret_tolerance
    )

    if category == 0:
        if not possible_certificate:
            return True
        if incumbent.reward_lower != reward_lower_upper_bound:
            return incumbent.reward_lower > reward_lower_upper_bound
        if incumbent.failure_upper != failure_lower_bound:
            return incumbent.failure_upper < failure_lower_bound
        return incumbent.policy_key <= minimum_policy_key

    if category == 1:
        if possible_certificate:
            return False
        if not possible_risk:
            return True
        if incumbent.reward_lower != reward_lower_upper_bound:
            return incumbent.reward_lower > reward_lower_upper_bound
        if incumbent.failure_upper != failure_lower_bound:
            return incumbent.failure_upper < failure_lower_bound
        return incumbent.policy_key <= minimum_policy_key

    if possible_risk:
        return False
    if incumbent.failure_upper != failure_lower_bound:
        return incumbent.failure_upper < failure_lower_bound
    if incumbent.reward_lower != reward_lower_upper_bound:
        return incumbent.reward_lower > reward_lower_upper_bound
    return incumbent.policy_key <= minimum_policy_key


def _optimistic_child_values(
    relevant_units: Sequence[_DecisionUnit],
    selected: Sequence[_DecisionChoice],
    unresolved: Sequence[_DecisionUnit],
    irrelevant: Sequence[_DecisionChoice],
) -> dict[str, robust._StateActionEvaluation]:
    values: dict[str, robust._StateActionEvaluation] = {}
    for choice in (*selected, *irrelevant):
        values.update(choice.state_values)
    for unit in unresolved:
        for state_id in unit.state_ids:
            candidates = tuple(
                choice.state_values[state_id] for choice in unit.choices
            )
            reward_lower = max(item.reward_lower for item in candidates)
            reward_upper = max(
                reward_lower,
                max(item.reward_upper for item in candidates),
            )
            failure_upper = min(item.failure_upper for item in candidates)
            values[state_id] = robust._StateActionEvaluation(
                reward_lower,
                reward_upper,
                failure_upper,
                (),
            )
    expected = {
        state_id
        for unit in relevant_units
        for state_id in unit.state_ids
    } | {
        state_id for choice in irrelevant for state_id in choice.state_values
    }
    if set(values) != expected:
        raise ExactLazyH2InvariantViolation(
            "optimistic child completion is incomplete"
        )
    return values


def _complete_policy(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
    root: _RootChoice,
    choices: Sequence[_DecisionChoice],
) -> robust._PolicyEvaluation:
    child_values: dict[str, robust._StateActionEvaluation] = {}
    child_rows: list[robust._RowEvaluation] = []
    for choice in choices:
        child_values.update(choice.state_values)
        child_rows.extend(choice.rows)
    root_value = _evaluate_root(
        model,
        threshold,
        solver_kind,
        root,
        child_values,
    )
    assignments = tuple(
        sorted(
            (root.assignment, *(item.assignment for item in choices)),
            key=lambda item: item.assignment_id,
        )
    )
    rows = tuple(
        sorted(
            (*root_value.rows, *child_rows),
            key=lambda item: item.provenance.provenance_id,
        )
    )
    return robust._PolicyEvaluation(
        assignments,
        root_value.reward_lower,
        root_value.reward_upper,
        root_value.failure_upper,
        rows,
    )


def _freeze_search_proof(
    *,
    phase: ExactLazyH2SearchPhase,
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
    roots: Sequence[_RootChoice],
    selected: robust._PolicyEvaluation,
    unrestricted_reward_upper: Fraction,
    raw_complete: Sequence[_RawCompleteWitness],
    raw_pruned: Sequence[_RawPrunedWitness],
) -> ExactLazyH2SearchProofV1:
    complete = tuple(
        sorted(
            (
                ExactLazyH2CompleteNodeWitnessV1(
                    item.root.assignment.assignment_id,
                    item.relevant_scope_keys,
                    tuple(
                        choice.assignment.assignment_id
                        for choice in item.selected
                    ),
                    tuple(
                        sorted(
                            choice.assignment.assignment_id
                            for choice in item.irrelevant
                        )
                    ),
                    item.evaluation.policy_key,
                    item.evaluation.reward_lower,
                    item.evaluation.reward_upper,
                    item.evaluation.failure_upper,
                )
                for item in raw_complete
            ),
            key=lambda item: item.witness_id,
        )
    )
    pruned = tuple(
        sorted(
            (
                ExactLazyH2PrunedNodeWitnessV1(
                    item.root.assignment.assignment_id,
                    item.relevant_scope_keys,
                    tuple(
                        choice.assignment.assignment_id
                        for choice in item.selected
                    ),
                    tuple(
                        sorted(
                            choice.assignment.assignment_id
                            for choice in item.irrelevant
                        )
                    ),
                    item.reward_lower_upper_bound,
                    item.failure_lower_bound,
                    item.minimum_policy_key,
                    selected.policy_key,
                    selected.reward_lower,
                    selected.failure_upper,
                )
                for item in raw_pruned
            ),
            key=lambda item: item.witness_id,
        )
    )
    return ExactLazyH2SearchProofV1(
        phase,
        solver_kind,
        model.model_id,
        threshold.threshold_profile_id,
        tuple(
            sorted(root.assignment.assignment_id for root in roots)
        ),
        selected.policy_key,
        selected.reward_lower,
        selected.reward_upper,
        selected.failure_upper,
        unrestricted_reward_upper,
        complete,
        pruned,
    )


def _solve_core_lazy(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
    limits: ExactLazyH2ResourceLimitsV1,
    *,
    phase: ExactLazyH2SearchPhase,
) -> tuple[
    robust._SolvedCore,
    ExactLazyH2SearchCountersV1,
    ExactLazyH2SearchProofV1,
]:
    _validate_inputs(model, threshold, solver_kind)
    units = (
        _direct_units(model, threshold)
        if solver_kind is robust.RobustSolverKind.GROUND_DIRECT
        else _quotient_units(model, threshold)
    )
    roots = _root_choices(model, solver_kind)
    unrestricted = robust._unrestricted_ground_reward_upper_h2(
        model,
        threshold,
    )
    counters = _MutableCounters()
    incumbent: robust._PolicyEvaluation | None = None
    raw_complete: list[_RawCompleteWitness] = []
    raw_pruned: list[_RawPrunedWitness] = []

    def bump(
        field: str,
        code: ExactLazyH2ResourceCode,
        limit: int,
    ) -> None:
        value = getattr(counters, field) + 1
        setattr(counters, field, value)
        if value > limit:
            raise _ResourceReached(code, value, limit, counters)

    for root in roots:
        counters.root_actions_considered += 1
        relevant_units = tuple(
            unit
            for unit in units
            if root.relevant_state_ids.intersection(unit.state_ids)
        )
        irrelevant_choices = tuple(
            unit.lexicographic_default
            for unit in units
            if not root.relevant_state_ids.intersection(unit.state_ids)
        )
        counters.relevant_decision_units += len(relevant_units)
        counters.irrelevant_decision_units += len(irrelevant_choices)

        # High reward / low failure choices tend to establish a strong exact
        # incumbent early.  This changes traversal only, never semantics.
        ordered_units = tuple(
            sorted(
                relevant_units,
                key=lambda unit: (-len(unit.state_ids), unit.scope_key),
            )
        )
        ordered_choices = {
            unit.scope_key: tuple(
                sorted(
                    unit.choices,
                    key=lambda choice: (
                        -sum(
                            (
                                value.reward_lower
                                for value in choice.state_values.values()
                            ),
                            Fraction(0),
                        ),
                        sum(
                            (
                                value.failure_upper
                                for value in choice.state_values.values()
                            ),
                            Fraction(0),
                        ),
                        choice.assignment.assignment_id,
                    ),
                )
            )
            for unit in ordered_units
        }
        relevant_scope_keys = tuple(
            unit.scope_key for unit in ordered_units
        )

        def visit(
            index: int,
            selected: tuple[_DecisionChoice, ...],
        ) -> None:
            nonlocal incumbent
            bump(
                "branch_nodes",
                ExactLazyH2ResourceCode.MAX_BRANCH_NODES,
                limits.max_branch_nodes,
            )
            unresolved = ordered_units[index:]
            optimistic_values = _optimistic_child_values(
                ordered_units,
                selected,
                unresolved,
                irrelevant_choices,
            )
            bump(
                "root_bound_evaluations",
                ExactLazyH2ResourceCode.MAX_ROOT_BOUND_EVALUATIONS,
                limits.max_root_bound_evaluations,
            )
            optimistic_root = _evaluate_root(
                model,
                threshold,
                solver_kind,
                root,
                optimistic_values,
            )
            minimum_policy_key = _minimum_completion_policy_key(
                root,
                selected,
                unresolved,
                irrelevant_choices,
            )
            if _can_prune(
                incumbent,
                reward_lower_upper_bound=optimistic_root.reward_lower,
                failure_lower_bound=optimistic_root.failure_upper,
                minimum_policy_key=minimum_policy_key,
                unrestricted_reward_upper=unrestricted,
                threshold=threshold,
            ):
                counters.pruned_branches += 1
                raw_pruned.append(
                    _RawPrunedWitness(
                        root,
                        relevant_scope_keys,
                        selected,
                        irrelevant_choices,
                        optimistic_root.reward_lower,
                        optimistic_root.failure_upper,
                        minimum_policy_key,
                    )
                )
                return

            if index == len(ordered_units):
                bump(
                    "complete_policies",
                    ExactLazyH2ResourceCode.MAX_COMPLETE_POLICIES,
                    limits.max_complete_policies,
                )
                candidate = _complete_policy(
                    model,
                    threshold,
                    solver_kind,
                    root,
                    (*selected, *irrelevant_choices),
                )
                raw_complete.append(
                    _RawCompleteWitness(
                        root,
                        relevant_scope_keys,
                        selected,
                        irrelevant_choices,
                        candidate,
                    )
                )
                if (
                    incumbent is None
                    or _policy_order_key(candidate, unrestricted, threshold)
                    < _policy_order_key(incumbent, unrestricted, threshold)
                ):
                    incumbent = candidate
                return

            unit = ordered_units[index]
            for choice in ordered_choices[unit.scope_key]:
                visit(index + 1, (*selected, choice))

        visit(0, ())

    if incumbent is None:
        raise ExactLazyH2InvariantViolation(
            "exact lazy H2 search produced no complete deterministic policy"
        )
    selected_key = _policy_order_key(incumbent, unrestricted, threshold)
    core = robust._SolvedCore(
        incumbent,
        unrestricted,
        max(Fraction(0), unrestricted - incumbent.reward_lower)
        / threshold.reward_ceiling,
        (
            robust.RobustAuditStatus.CERTIFIED
            if int(selected_key[0]) == 0
            else robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
        ),
    )
    proof = _freeze_search_proof(
        phase=phase,
        model=model,
        threshold=threshold,
        solver_kind=solver_kind,
        roots=roots,
        selected=incumbent,
        unrestricted_reward_upper=unrestricted,
        raw_complete=raw_complete,
        raw_pruned=raw_pruned,
    )
    return core, counters.freeze(), proof


def _counterfactual_and_trace(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
    original: robust._SolvedCore,
    limits: ExactLazyH2ResourceLimitsV1,
) -> tuple[
    robust.OtherOnlyCounterfactualV1,
    ExactLazyH2SearchCountersV1 | None,
    ExactLazyH2SearchProofV1 | None,
]:
    if original.status is robust.RobustAuditStatus.CERTIFIED:
        return (
            robust.OtherOnlyCounterfactualV1(
                robust.CounterfactualStatus.ORIGINAL_ALREADY_CERTIFIED,
                True,
                None,
                False,
                None,
                None,
                None,
            ),
            None,
            None,
        )
    try:
        zero_model = robust._zero_other_model(model)
    except robust.PartialSupportRobustPlannerInvariantViolation:
        return (
            robust.OtherOnlyCounterfactualV1(
                robust.CounterfactualStatus.ZERO_OTHER_INFEASIBLE_SIMPLEX,
                False,
                None,
                False,
                None,
                None,
                None,
            ),
            None,
            None,
        )
    zero, counters, proof = _solve_core_lazy(
        zero_model,
        threshold,
        solver_kind,
        limits,
        phase=ExactLazyH2SearchPhase.ZERO_OTHER_COUNTERFACTUAL,
    )
    certified = zero.status is robust.RobustAuditStatus.CERTIFIED
    return (
        robust.OtherOnlyCounterfactualV1(
            (
                robust.CounterfactualStatus.ZERO_OTHER_CERTIFIED
                if certified
                else robust.CounterfactualStatus.ZERO_OTHER_STILL_FAILED
            ),
            False,
            certified,
            certified,
            zero_model.model_id,
            zero.selected.failure_upper,
            zero.normalized_regret_upper,
        ),
        counters,
        proof,
    )


def _audit_from_core(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
    core: robust._SolvedCore,
    counterfactual: robust.OtherOnlyCounterfactualV1,
) -> robust.RobustPlanAuditV1:
    selected_bounds = tuple(
        sorted(
            (item.bound for item in core.selected.rows),
            key=lambda item: item.row_bound_id,
        )
    )
    provenance = tuple(
        sorted(
            (item.provenance for item in core.selected.rows),
            key=lambda item: item.provenance_id,
        )
    )
    category_by_row = {
        item.row_id: item.category for item in provenance
    }
    other = tuple(
        sorted(
            (
                robust.OtherMassProvenanceV1(
                    item.row_id,
                    item.remaining_horizon,
                    category_by_row[item.row_id],
                    item.other_mass_upper,
                )
                for item in selected_bounds
            ),
            key=lambda item: item.other_mass_provenance_id,
        )
    )
    frontier: robust.FailedProofFrontierV1 | None = None
    if core.status is robust.RobustAuditStatus.FAILED_PROOF_FRONTIER:
        risk_failed = core.selected.failure_upper >= threshold.risk_tolerance
        regret_failed = (
            core.normalized_regret_upper
            > threshold.normalized_regret_tolerance
        )
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
            tuple(sorted(item.row_id for item in selected_bounds)),
            tuple(
                sorted(
                    item.row_id
                    for item in selected_bounds
                    if item.other_mass_upper > 0
                )
            ),
            counterfactual.changes_failed_to_certified,
        )
    return robust.RobustPlanAuditV1(
        solver_kind,
        model.model_id,
        threshold.threshold_profile_id,
        core.status,
        core.selected.assignments,
        selected_bounds,
        provenance,
        other,
        core.selected.reward_lower,
        core.unrestricted_reward_upper,
        core.selected.failure_upper,
        core.normalized_regret_upper,
        counterfactual,
        frontier,
    )


def solve_exact_lazy_robust_h2_v1(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
    *,
    limits: ExactLazyH2ResourceLimitsV1 = ExactLazyH2ResourceLimitsV1(),
) -> ExactLazyH2SolveResultV1:
    """Return an exact byte-compatible audit or typed resource exhaustion."""

    if type(limits) is not ExactLazyH2ResourceLimitsV1:
        raise ExactLazyH2InvariantViolation(
            "exact lazy H2 limits have the wrong type"
        )
    _validate_inputs(model, threshold, solver_kind)
    try:
        core, original_counters, original_proof = _solve_core_lazy(
            model,
            threshold,
            solver_kind,
            limits,
            phase=ExactLazyH2SearchPhase.ORIGINAL,
        )
    except _ResourceReached as error:
        return ExactLazyH2SolveResultV1(
            ExactLazyH2SolveStatus.EXACT_DP_RESOURCE_EXHAUSTED,
            solver_kind,
            None,
            None,
            ExactLazyH2ResourceExhaustionV1(
                ExactLazyH2SearchPhase.ORIGINAL,
                error.code,
                error.observed,
                error.limit,
                error.counters,
            ),
        )
    try:
        counterfactual, zero_counters, zero_proof = (
            _counterfactual_and_trace(
                model,
                threshold,
                solver_kind,
                core,
                limits,
            )
        )
    except _ResourceReached as error:
        return ExactLazyH2SolveResultV1(
            ExactLazyH2SolveStatus.EXACT_DP_RESOURCE_EXHAUSTED,
            solver_kind,
            None,
            None,
            ExactLazyH2ResourceExhaustionV1(
                ExactLazyH2SearchPhase.ZERO_OTHER_COUNTERFACTUAL,
                error.code,
                error.observed,
                error.limit,
                error.counters,
            ),
        )
    audit = _audit_from_core(
        model,
        threshold,
        solver_kind,
        core,
        counterfactual,
    )
    return ExactLazyH2SolveResultV1(
        ExactLazyH2SolveStatus.SOLVED,
        solver_kind,
        audit,
        ExactLazyH2SearchTraceV1(
            solver_kind,
            original_counters,
            zero_counters,
            original_proof,
            zero_proof,
        ),
        None,
    )


def solve_exact_lazy_ground_direct_h2_v1(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    *,
    limits: ExactLazyH2ResourceLimitsV1 = ExactLazyH2ResourceLimitsV1(),
) -> ExactLazyH2SolveResultV1:
    return solve_exact_lazy_robust_h2_v1(
        model,
        threshold,
        robust.RobustSolverKind.GROUND_DIRECT,
        limits=limits,
    )


def solve_exact_lazy_quotient_h2_v1(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    *,
    limits: ExactLazyH2ResourceLimitsV1 = ExactLazyH2ResourceLimitsV1(),
) -> ExactLazyH2SolveResultV1:
    return solve_exact_lazy_robust_h2_v1(
        model,
        threshold,
        robust.RobustSolverKind.QUOTIENT,
        limits=limits,
    )


__all__ = [
    "ExactLazyH2CompleteNodeWitnessV1",
    "ExactLazyH2InvariantViolation",
    "ExactLazyH2PrunedNodeWitnessV1",
    "ExactLazyH2ResourceCode",
    "ExactLazyH2ResourceExhaustionV1",
    "ExactLazyH2ResourceLimitsV1",
    "ExactLazyH2SearchCountersV1",
    "ExactLazyH2SearchPhase",
    "ExactLazyH2SearchProofV1",
    "ExactLazyH2SearchTraceV1",
    "ExactLazyH2SolveResultV1",
    "ExactLazyH2SolveStatus",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "solve_exact_lazy_ground_direct_h2_v1",
    "solve_exact_lazy_quotient_h2_v1",
    "solve_exact_lazy_robust_h2_v1",
]
