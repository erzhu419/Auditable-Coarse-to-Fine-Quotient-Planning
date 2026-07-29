"""Standalone exact lift evaluation and exact fallback for V0-068.

This module is deliberately downstream of the operational robust audit.  It
is the only V0-068 consumer (besides the explicit fallback authority) that
imports the hidden-law evaluators from :mod:`transition_tuple_observer_v1`.

The lift evaluator first freezes and semantically replays the supplied robust
audit without making an exact-law call.  Only then does it resolve the policy
through the model bridge:

* direct assignments select one bound ground action;
* quotient assignments select one semantic action and use the frozen uniform
  distribution over *distinct* ground actions in its concretizer.

The resulting H=2 policy is evaluated recursively with exact Fractions.  A
separate complete ground search supplies the deterministic constrained
comparator.  Both are evaluation-only work and can never strengthen or alter
the already frozen operational certificate.

The fallback wrapper has a separate ``FALLBACK_EXACT`` logical lane.  Its cap
outcome is explicitly a non-certificate and is never mapped to infeasibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Mapping

import acfqp.observation_support_graph_acquisition_v1 as acquisition
import acfqp.observation_support_graph_model_v1 as graph_model
import acfqp.partial_support_robust_planner_v1 as robust
import acfqp.transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.32.0"
PROFILE_KEY = "observation_support_exact_evaluation_v0"
EVALUATION_ONLY = "EVALUATION_ONLY"
FALLBACK_EXACT = "FALLBACK_EXACT"
DEFAULT_FALLBACK_EXACT_ROW_CAP = 65_536
UNSEEN_OUTCOME_POLICY_SEMANTICS = graph_model.OTHER_ESCAPE_BEHAVIOR
FALLBACK_CAP_SEMANTICS = "POSTHOC_COMPLETE_SEARCH_WORK_CLASSIFICATION"


DOMAIN_TAGS = {
    "decision": "acfqp:observation-support-exact-lift-decision:v1",
    "policy": "acfqp:observation-support-exact-lift-policy:v1",
    "counters": "acfqp:observation-support-exact-evaluation-counters:v1",
    "evaluation": "acfqp:observation-support-exact-lift-evaluation:v1",
    "verification": (
        "acfqp:observation-support-exact-lift-evaluation-verification:v1"
    ),
    "fallback_cap": "acfqp:observation-support-exact-fallback-cap:v1",
    "fallback_counters": (
        "acfqp:observation-support-exact-fallback-counters:v1"
    ),
    "fallback": "acfqp:observation-support-exact-fallback-result:v1",
}


class ObservationSupportExactEvaluationInvariantViolation(ValueError):
    """An evaluation/fallback identity, policy lift, or result is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise ObservationSupportExactEvaluationInvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ObservationSupportExactEvaluationInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise ObservationSupportExactEvaluationInvariantViolation(
            "exact probability/reward must be a Fraction"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _registered_context(
    context: observer.PublicGraphContextV1,
) -> observer.PublicGraphContextV1:
    if (
        type(context) is not observer.PublicGraphContextV1
        or context not in observer.registered_public_graph_contexts_v1()
    ):
        raise ObservationSupportExactEvaluationInvariantViolation(
            "exact authority requires one registered public graph context"
        )
    return context


@dataclass(frozen=True, slots=True)
class ExactLiftDecisionV1:
    """One reachable state-time decision after exact policy lifting."""

    context_id: str
    bridge_id: str
    model_id: str
    audit_id: str
    state_id: str
    catalogue_id: str
    remaining_horizon: int
    policy_scope: robust.PolicyScope
    policy_scope_key: str
    selected_action_key: str
    ground_action_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "decision context"),
            (self.bridge_id, "decision bridge"),
            (self.model_id, "decision model"),
            (self.audit_id, "decision audit"),
            (self.state_id, "decision state"),
            (self.catalogue_id, "decision catalogue"),
            (self.policy_scope_key, "decision policy scope"),
            (self.selected_action_key, "decision selected action"),
        ):
            _cid(value, field)
        if (
            type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, 2)
            or type(self.policy_scope) is not robust.PolicyScope
            or type(self.ground_action_ids) is not tuple
            or not self.ground_action_ids
            or self.ground_action_ids
            != tuple(sorted(set(self.ground_action_ids)))
            or (
                self.policy_scope is robust.PolicyScope.GROUND_STATE
                and (
                    self.policy_scope_key != self.state_id
                    or len(self.ground_action_ids) != 1
                    or self.selected_action_key != self.ground_action_ids[0]
                )
            )
        ):
            raise ObservationSupportExactEvaluationInvariantViolation(
                "exact lift decision is malformed"
            )
        for action_id in self.ground_action_ids:
            _cid(action_id, "decision ground action")

    @property
    def uniform_ground_action_weight(self) -> Fraction:
        return Fraction(1, len(self.ground_action_ids))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_exact_lift_decision.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "bridge_id": self.bridge_id,
            "model_id": self.model_id,
            "audit_id": self.audit_id,
            "state_id": self.state_id,
            "catalogue_id": self.catalogue_id,
            "remaining_horizon": self.remaining_horizon,
            "policy_scope": self.policy_scope.value,
            "policy_scope_key": self.policy_scope_key,
            "selected_action_key": self.selected_action_key,
            "ground_action_ids": list(self.ground_action_ids),
            "uniform_ground_action_weight": _fdoc(
                self.uniform_ground_action_weight
            ),
            "distinct_action_uniform_concretizer": True,
        }

    @property
    def decision_id(self) -> str:
        return _content_id("decision", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "decision_id": self.decision_id}


def _lifted_policy_id(
    *,
    context_id: str,
    bridge_id: str,
    model_id: str,
    audit_id: str,
    decisions: tuple[ExactLiftDecisionV1, ...],
) -> str:
    return _content_id(
        "policy",
        {
            "schema": "acfqp.observation_support_exact_lift_policy.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": context_id,
            "bridge_id": bridge_id,
            "model_id": model_id,
            "audit_id": audit_id,
            "decision_ids": [item.decision_id for item in decisions],
            "horizon": 2,
        },
    )


@dataclass(frozen=True, slots=True)
class ExactLiftEvaluationCountersV1:
    lift_exact_atom_calls: int
    lift_exact_atoms_enumerated: int
    lift_state_time_nodes: int
    comparator_complete_ground_search_calls: int
    comparator_exact_state_action_rows: int
    total_evaluation_exact_row_calls: int
    operational_exact_atom_calls: int = 0
    execution_lane: str = EVALUATION_ONLY

    def __post_init__(self) -> None:
        if (
            type(self.lift_exact_atom_calls) is not int
            or self.lift_exact_atom_calls <= 0
            or type(self.lift_exact_atoms_enumerated) is not int
            or self.lift_exact_atoms_enumerated < self.lift_exact_atom_calls
            or type(self.lift_state_time_nodes) is not int
            or self.lift_state_time_nodes <= 0
            or self.comparator_complete_ground_search_calls != 1
            or type(self.comparator_exact_state_action_rows) is not int
            or self.comparator_exact_state_action_rows <= 0
            or self.total_evaluation_exact_row_calls
            != (
                self.lift_exact_atom_calls
                + self.comparator_exact_state_action_rows
            )
            or self.operational_exact_atom_calls != 0
            or self.execution_lane != EVALUATION_ONLY
        ):
            raise ObservationSupportExactEvaluationInvariantViolation(
                "exact lift evaluation counters do not reconcile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.observation_support_exact_evaluation_counters.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "lift_exact_atom_calls": self.lift_exact_atom_calls,
            "lift_exact_atoms_enumerated": (
                self.lift_exact_atoms_enumerated
            ),
            "lift_state_time_nodes": self.lift_state_time_nodes,
            "comparator_complete_ground_search_calls": 1,
            "comparator_exact_state_action_rows": (
                self.comparator_exact_state_action_rows
            ),
            "total_evaluation_exact_row_calls": (
                self.total_evaluation_exact_row_calls
            ),
            "operational_exact_atom_calls": 0,
            "execution_lane": self.execution_lane,
        }

    @property
    def counters_id(self) -> str:
        return _content_id("counters", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counters_id": self.counters_id}


@dataclass(frozen=True, slots=True)
class ObservationSupportExactLiftEvaluationV1:
    context_id: str
    bridge_id: str
    model_id: str
    audit_id: str
    threshold_profile_id: str
    solver_kind: robust.RobustSolverKind
    lifted_policy_id: str
    decisions: tuple[ExactLiftDecisionV1, ...]
    exact_failure_probability: Fraction
    exact_normalized_reward: Fraction
    exact_comparator: observer.EvaluationExactGroundSearchV1
    exact_normalized_regret: Fraction
    audit_failure_bound: Fraction
    audit_reward_lower: Fraction
    audit_unrestricted_reward_upper: Fraction
    audit_normalized_regret_upper: Fraction
    counters: ExactLiftEvaluationCountersV1
    prerequisite_operational_freeze_id: str | None = None
    audit_bounds_cover_exact_lift: bool = True
    public_risk_check_passed: bool = True
    public_regret_check_passed: bool = True
    audit_certified_before_evaluation: bool = True
    audit_frozen_before_first_exact_call: bool = True
    may_influence_operational_certificate: bool = False
    repairs_conditional_prng_certificate: bool = False
    unseen_outcome_policy_semantics: str = (
        UNSEEN_OUTCOME_POLICY_SEMANTICS
    )
    execution_lane: str = EVALUATION_ONLY

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "evaluation context"),
            (self.bridge_id, "evaluation bridge"),
            (self.model_id, "evaluation model"),
            (self.audit_id, "evaluation audit"),
            (self.threshold_profile_id, "evaluation threshold"),
            (self.lifted_policy_id, "lifted policy"),
        ):
            _cid(value, field)
        if self.prerequisite_operational_freeze_id is not None:
            _cid(
                self.prerequisite_operational_freeze_id,
                "evaluation prerequisite operational freeze",
            )
        if (
            type(self.solver_kind) is not robust.RobustSolverKind
            or type(self.decisions) is not tuple
            or not self.decisions
            or any(type(item) is not ExactLiftDecisionV1 for item in self.decisions)
            or tuple(item.decision_id for item in self.decisions)
            != tuple(sorted({item.decision_id for item in self.decisions}))
            or any(
                item.context_id != self.context_id
                or item.bridge_id != self.bridge_id
                or item.model_id != self.model_id
                or item.audit_id != self.audit_id
                for item in self.decisions
            )
            or _lifted_policy_id(
                context_id=self.context_id,
                bridge_id=self.bridge_id,
                model_id=self.model_id,
                audit_id=self.audit_id,
                decisions=self.decisions,
            )
            != self.lifted_policy_id
            or type(self.exact_failure_probability) is not Fraction
            or not 0 <= self.exact_failure_probability <= 1
            or type(self.exact_normalized_reward) is not Fraction
            or self.exact_normalized_reward < 0
            or type(self.exact_comparator)
            is not observer.EvaluationExactGroundSearchV1
            or self.exact_comparator.context_id != self.context_id
            or type(self.exact_normalized_regret) is not Fraction
            or self.exact_normalized_regret
            != (
                self.exact_comparator.root_normalized_reward
                - self.exact_normalized_reward
            )
            or self.exact_normalized_regret < 0
            or any(
                type(value) is not Fraction
                for value in (
                    self.audit_failure_bound,
                    self.audit_reward_lower,
                    self.audit_unrestricted_reward_upper,
                    self.audit_normalized_regret_upper,
                )
            )
            or not (
                self.exact_failure_probability <= self.audit_failure_bound
                and self.audit_reward_lower
                <= self.exact_normalized_reward
                <= self.audit_unrestricted_reward_upper
                and self.exact_normalized_regret
                <= self.audit_normalized_regret_upper
            )
            or type(self.counters) is not ExactLiftEvaluationCountersV1
            or self.counters.lift_state_time_nodes != len(self.decisions)
            or self.counters.comparator_exact_state_action_rows
            != self.exact_comparator.evaluated_state_action_rows
            or self.audit_bounds_cover_exact_lift is not True
            or self.public_risk_check_passed is not True
            or self.public_regret_check_passed is not True
            or self.audit_certified_before_evaluation is not True
            or self.audit_frozen_before_first_exact_call is not True
            or self.may_influence_operational_certificate is not False
            or self.repairs_conditional_prng_certificate is not False
            or self.unseen_outcome_policy_semantics
            != UNSEEN_OUTCOME_POLICY_SEMANTICS
            or self.execution_lane != EVALUATION_ONLY
        ):
            raise ObservationSupportExactEvaluationInvariantViolation(
                "exact lift evaluation claim or authority boundary is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_exact_lift_evaluation.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "bridge_id": self.bridge_id,
            "model_id": self.model_id,
            "audit_id": self.audit_id,
            "threshold_profile_id": self.threshold_profile_id,
            "solver_kind": self.solver_kind.value,
            "lifted_policy_id": self.lifted_policy_id,
            "decision_ids": [item.decision_id for item in self.decisions],
            "exact_failure_probability": _fdoc(
                self.exact_failure_probability
            ),
            "exact_normalized_reward": _fdoc(
                self.exact_normalized_reward
            ),
            "exact_comparator_search_id": self.exact_comparator.search_id,
            "exact_normalized_regret": _fdoc(self.exact_normalized_regret),
            "audit_failure_bound": _fdoc(self.audit_failure_bound),
            "audit_reward_lower": _fdoc(self.audit_reward_lower),
            "audit_unrestricted_reward_upper": _fdoc(
                self.audit_unrestricted_reward_upper
            ),
            "audit_normalized_regret_upper": _fdoc(
                self.audit_normalized_regret_upper
            ),
            "counters_id": self.counters.counters_id,
            "prerequisite_operational_freeze": (
                {"kind": "STANDALONE_UNBOUND"}
                if self.prerequisite_operational_freeze_id is None
                else {
                    "kind": "BOUND_PREDECESSOR",
                    "operational_freeze_id": (
                        self.prerequisite_operational_freeze_id
                    ),
                }
            ),
            "audit_bounds_cover_exact_lift": True,
            "public_risk_check_passed": True,
            "public_regret_check_passed": True,
            "audit_certified_before_evaluation": True,
            "audit_frozen_before_first_exact_call": True,
            "may_influence_operational_certificate": False,
            "repairs_conditional_prng_certificate": False,
            "unseen_outcome_policy_semantics": (
                self.unseen_outcome_policy_semantics
            ),
            "execution_lane": self.execution_lane,
        }

    @property
    def evaluation_id(self) -> str:
        return _content_id("evaluation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "decisions": [item.to_document() for item in self.decisions],
            "exact_comparator": self.exact_comparator.to_document(),
            "counters": self.counters.to_document(),
            "evaluation_id": self.evaluation_id,
        }


def _frozen_audit_inputs(
    context: observer.PublicGraphContextV1,
    bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    audit: robust.RobustPlanAuditV1,
) -> tuple[
    robust.PartialSupportIntervalModelV1,
    robust.RobustThresholdProfileV1,
]:
    registered = _registered_context(context)
    if (
        type(bridge) is not graph_model.ObservationSupportGraphModelBridgeV1
        or bridge.context_id != registered.context_id
        or type(bridge.other_escape_handler)
        is not graph_model.GraphOtherOutcomeEscapeHandlerV1
        or bridge.other_escape_handler.behavior
        != UNSEEN_OUTCOME_POLICY_SEMANTICS
        or bridge.other_escape_handler.other_destination_id
        != bridge.other_destination_id
        or type(audit) is not robust.RobustPlanAuditV1
    ):
        raise ObservationSupportExactEvaluationInvariantViolation(
            "context, bridge, and frozen audit identities do not match"
        )
    model = (
        bridge.direct_model
        if audit.solver_kind is robust.RobustSolverKind.GROUND_DIRECT
        else bridge.quotient_model
    )
    threshold = robust.RobustThresholdProfileV1(
        registered.context_id,
        registered.risk_tolerance,
        bridge.reward_ceiling,
        registered.normalized_regret_tolerance,
    )
    if (
        audit.model_id != model.model_id
        or audit.threshold_profile_id != threshold.threshold_profile_id
        or audit.status is not robust.RobustAuditStatus.CERTIFIED
    ):
        raise ObservationSupportExactEvaluationInvariantViolation(
            "exact evaluation requires the matching certified frozen audit"
        )
    try:
        robust.verify_robust_plan_audit_v1(model, threshold, audit)
    except robust.PartialSupportRobustPlannerInvariantViolation as error:
        raise ObservationSupportExactEvaluationInvariantViolation(
            "frozen robust audit failed semantic replay"
        ) from error
    return model, threshold


def _policy_assignment_registry(
    audit: robust.RobustPlanAuditV1,
) -> dict[tuple[robust.PolicyScope, str, int], robust.RobustPolicyAssignmentV1]:
    registry: dict[
        tuple[robust.PolicyScope, str, int],
        robust.RobustPolicyAssignmentV1,
    ] = {}
    for assignment in audit.assignments:
        key = (
            assignment.scope,
            assignment.scope_key,
            assignment.remaining_horizon,
        )
        if key in registry:
            raise ObservationSupportExactEvaluationInvariantViolation(
                "frozen audit contains duplicate semantic policy assignments"
            )
        registry[key] = assignment
    return registry


def evaluate_observation_support_exact_lift_v1(
    context: observer.PublicGraphContextV1,
    bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    audit: robust.RobustPlanAuditV1,
    *,
    prerequisite_operational_freeze_id: str | None = None,
) -> ObservationSupportExactLiftEvaluationV1:
    """Exactly evaluate a certified policy after its audit is frozen."""

    if prerequisite_operational_freeze_id is not None:
        _cid(
            prerequisite_operational_freeze_id,
            "evaluation prerequisite operational freeze",
        )
    model, threshold = _frozen_audit_inputs(context, bridge, audit)

    # Everything above this line is kernel-free and freezes the complete
    # operational input identity before the first hidden-law query below.
    frozen_audit_id = audit.audit_id
    frozen_bridge_id = bridge.bridge_id
    frozen_model_id = model.model_id

    assignments = _policy_assignment_registry(audit)
    binding_by_action_id = {
        item.action_id: item for item in bridge.action_bindings
    }
    catalogue_by_state = {
        item.state_id: item for item in model.catalogues
    }
    concretizer_by_key = {
        (
            item.state_coordinate_key,
            item.state_id,
            item.abstract_action_key,
        ): item
        for item in model.concretizer_entries
    }
    known_outcome_ids_by_action_id = {
        item.action_id: frozenset(
            projection.event_key
            for projection in item.event_destination_projections
            if not projection.is_other
        )
        for item in bridge.row_projections
    }

    decisions: dict[tuple[str, int], ExactLiftDecisionV1] = {}
    values: dict[tuple[str, int], tuple[Fraction, Fraction]] = {}
    lift_exact_atom_calls = 0
    lift_exact_atoms_enumerated = 0

    def decision_for(
        state: observer.SymbolicGraphStateV1,
        remaining_horizon: int,
    ) -> tuple[
        ExactLiftDecisionV1,
        tuple[graph_model.GraphGroundActionBindingV1, ...],
        observer.LegalActionCatalogueV1,
    ]:
        model_catalogue = catalogue_by_state.get(state.state_id)
        if model_catalogue is None:
            raise ObservationSupportExactEvaluationInvariantViolation(
                "exact lift lacks a reachable ground-state catalogue"
            )
        public_catalogue = observer.legal_action_catalogue_v1(
            context,
            state,
            remaining_horizon,
        )
        if public_catalogue.catalogue_id not in bridge.public_catalogue_ids:
            raise ObservationSupportExactEvaluationInvariantViolation(
                "exact lift reached an unbound public catalogue"
            )
        if audit.solver_kind is robust.RobustSolverKind.GROUND_DIRECT:
            scope = robust.PolicyScope.GROUND_STATE
            scope_key = state.state_id
            assignment = assignments.get(
                (scope, scope_key, remaining_horizon)
            )
            if assignment is None:
                raise ObservationSupportExactEvaluationInvariantViolation(
                    "exact lift lacks a reachable direct policy assignment"
                )
            ground_action_ids = (assignment.selected_action_key,)
        else:
            scope = robust.PolicyScope.QUOTIENT_CELL
            scope_key = model_catalogue.state_coordinate_key
            assignment = assignments.get(
                (scope, scope_key, remaining_horizon)
            )
            if assignment is None:
                raise ObservationSupportExactEvaluationInvariantViolation(
                    "exact lift lacks a reachable quotient policy assignment"
                )
            entry = concretizer_by_key.get(
                (
                    scope_key,
                    state.state_id,
                    assignment.selected_action_key,
                )
            )
            if entry is None:
                raise ObservationSupportExactEvaluationInvariantViolation(
                    "exact lift lacks the frozen ground concretizer"
                )
            ground_action_ids = entry.ground_action_ids

        ground_bindings: list[graph_model.GraphGroundActionBindingV1] = []
        for action_id in ground_action_ids:
            binding = binding_by_action_id.get(action_id)
            if (
                binding is None
                or binding.context_id != context.context_id
                or binding.state_id != state.state_id
                or binding.remaining_horizon != remaining_horizon
                or binding.catalogue_id != public_catalogue.catalogue_id
                or binding.action not in public_catalogue.actions
            ):
                raise ObservationSupportExactEvaluationInvariantViolation(
                    "lifted action is stale, foreign, or illegal"
                )
            ground_bindings.append(binding)
        decision = ExactLiftDecisionV1(
            context.context_id,
            frozen_bridge_id,
            frozen_model_id,
            frozen_audit_id,
            state.state_id,
            public_catalogue.catalogue_id,
            remaining_horizon,
            scope,
            scope_key,
            assignment.selected_action_key,
            tuple(sorted(ground_action_ids)),
        )
        return decision, tuple(ground_bindings), public_catalogue

    def solve(
        state: observer.SymbolicGraphStateV1,
        remaining_horizon: int,
    ) -> tuple[Fraction, Fraction]:
        nonlocal lift_exact_atom_calls, lift_exact_atoms_enumerated
        key = (state.state_id, remaining_horizon)
        if key in values:
            return values[key]
        decision, bindings, public_catalogue = decision_for(
            state,
            remaining_horizon,
        )
        decisions[key] = decision
        action_weight = Fraction(1, len(bindings))
        risk = Fraction(0)
        reward = Fraction(0)
        for binding in bindings:
            atoms = observer.evaluation_exact_atoms_v1(
                context,
                public_catalogue,
                binding.action,
            )
            lift_exact_atom_calls += 1
            lift_exact_atoms_enumerated += len(atoms)
            immediate_rewards = {
                item.realized_row_reward for item in atoms
            }
            if len(immediate_rewards) != 1:
                raise ObservationSupportExactEvaluationInvariantViolation(
                    "exact evaluation row reward became stochastic"
                )
            action_risk = Fraction(0)
            action_future_reward = Fraction(0)
            known_outcome_ids = known_outcome_ids_by_action_id.get(
                binding.action_id
            )
            if known_outcome_ids is None:
                raise ObservationSupportExactEvaluationInvariantViolation(
                    "exact lift lacks the selected row's support projection"
                )
            for atom in atoms:
                descriptor = acquisition.GraphObservedOutcomeDescriptorV1(
                    atom.next_state,
                    atom.realized_row_reward,
                    atom.failure,
                    atom.terminal,
                )
                if descriptor.outcome_id not in known_outcome_ids:
                    # The deployed partial-support policy maps the single
                    # adversarial OTHER event to an explicit absorbing abort.
                    action_risk += atom.probability
                elif atom.failure:
                    action_risk += atom.probability
                elif remaining_horizon > 1:
                    child_risk, child_reward = solve(
                        atom.next_state,
                        remaining_horizon - 1,
                    )
                    action_risk += atom.probability * child_risk
                    action_future_reward += atom.probability * child_reward
            risk += action_weight * action_risk
            reward += action_weight * (
                next(iter(immediate_rewards)) + action_future_reward
            )
        values[key] = (risk, reward)
        return values[key]

    exact_failure, exact_reward = solve(
        observer.root_state_v1(context),
        2,
    )
    decision_tuple = tuple(
        sorted(decisions.values(), key=lambda item: item.decision_id)
    )

    # The comparator is a second, independently identified evaluation-only
    # authority call.  It is not visible to the operational planner/audit.
    comparator = observer.evaluation_exact_ground_search_v1(context)
    exact_regret = comparator.root_normalized_reward - exact_reward
    bounds_cover = (
        exact_failure <= audit.root_failure_upper
        and audit.root_reward_lower
        <= exact_reward
        <= audit.unrestricted_reward_upper
        and exact_regret <= audit.normalized_regret_upper
    )
    risk_passed = exact_failure <= context.risk_tolerance
    regret_passed = (
        Fraction(0)
        <= exact_regret
        <= context.normalized_regret_tolerance
    )
    if not bounds_cover:
        raise ObservationSupportExactEvaluationInvariantViolation(
            "robust audit bounds do not contain the exact lifted policy"
        )
    if not risk_passed or not regret_passed:
        raise ObservationSupportExactEvaluationInvariantViolation(
            "exact lifted policy fails the public risk/regret query"
        )

    counters = ExactLiftEvaluationCountersV1(
        lift_exact_atom_calls,
        lift_exact_atoms_enumerated,
        len(decision_tuple),
        1,
        comparator.evaluated_state_action_rows,
        lift_exact_atom_calls + comparator.evaluated_state_action_rows,
    )
    policy_id = _lifted_policy_id(
        context_id=context.context_id,
        bridge_id=frozen_bridge_id,
        model_id=frozen_model_id,
        audit_id=frozen_audit_id,
        decisions=decision_tuple,
    )
    return ObservationSupportExactLiftEvaluationV1(
        context.context_id,
        frozen_bridge_id,
        frozen_model_id,
        frozen_audit_id,
        threshold.threshold_profile_id,
        audit.solver_kind,
        policy_id,
        decision_tuple,
        exact_failure,
        exact_reward,
        comparator,
        exact_regret,
        audit.root_failure_upper,
        audit.root_reward_lower,
        audit.unrestricted_reward_upper,
        audit.normalized_regret_upper,
        counters,
        prerequisite_operational_freeze_id,
    )


@dataclass(frozen=True, slots=True)
class ObservationSupportExactLiftVerificationV1:
    context_id: str
    bridge_id: str
    audit_id: str
    claimed_evaluation_id: str
    replayed_evaluation_id: str
    replay_evaluation_exact_row_calls: int
    valid: bool = True
    execution_lane: str = EVALUATION_ONLY

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "verification context"),
            (self.bridge_id, "verification bridge"),
            (self.audit_id, "verification audit"),
            (self.claimed_evaluation_id, "claimed evaluation"),
            (self.replayed_evaluation_id, "replayed evaluation"),
        ):
            _cid(value, field)
        if (
            self.claimed_evaluation_id != self.replayed_evaluation_id
            or type(self.replay_evaluation_exact_row_calls) is not int
            or self.replay_evaluation_exact_row_calls <= 0
            or self.valid is not True
            or self.execution_lane != EVALUATION_ONLY
        ):
            raise ObservationSupportExactEvaluationInvariantViolation(
                "exact lift verification is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.observation_support_exact_lift_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "bridge_id": self.bridge_id,
            "audit_id": self.audit_id,
            "claimed_evaluation_id": self.claimed_evaluation_id,
            "replayed_evaluation_id": self.replayed_evaluation_id,
            "replay_evaluation_exact_row_calls": (
                self.replay_evaluation_exact_row_calls
            ),
            "valid": True,
            "execution_lane": self.execution_lane,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_observation_support_exact_lift_v1(
    context: observer.PublicGraphContextV1,
    bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    audit: robust.RobustPlanAuditV1,
    claimed: ObservationSupportExactLiftEvaluationV1,
) -> ObservationSupportExactLiftVerificationV1:
    """Replay the standalone exact lift and reject any changed byte/identity."""

    if type(claimed) is not ObservationSupportExactLiftEvaluationV1:
        raise ObservationSupportExactEvaluationInvariantViolation(
            "claimed exact lift evaluation has the wrong type"
        )
    replayed = evaluate_observation_support_exact_lift_v1(
        context,
        bridge,
        audit,
        prerequisite_operational_freeze_id=(
            claimed.prerequisite_operational_freeze_id
        ),
    )
    if (
        replayed != claimed
        or replayed.to_document() != claimed.to_document()
        or replayed.evaluation_id != claimed.evaluation_id
    ):
        raise ObservationSupportExactEvaluationInvariantViolation(
            "claimed exact lift evaluation differs from exact replay"
        )
    return ObservationSupportExactLiftVerificationV1(
        context.context_id,
        bridge.bridge_id,
        audit.audit_id,
        claimed.evaluation_id,
        replayed.evaluation_id,
        replayed.counters.total_evaluation_exact_row_calls,
    )


class ExactFallbackOutcome(str, Enum):
    FEASIBLE_PLAN_CERTIFIED = "FEASIBLE_PLAN_CERTIFIED"
    CAP_EXHAUSTED_NONCERTIFICATE = "CAP_EXHAUSTED_NONCERTIFICATE"


@dataclass(frozen=True, slots=True)
class ExactFallbackCapV1:
    context_id: str
    max_exact_state_action_rows: int

    def __post_init__(self) -> None:
        _cid(self.context_id, "fallback cap context")
        if (
            type(self.max_exact_state_action_rows) is not int
            or self.max_exact_state_action_rows <= 0
        ):
            raise ObservationSupportExactEvaluationInvariantViolation(
                "fallback exact row cap must be a positive integer"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_exact_fallback_cap.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "max_exact_state_action_rows": (
                self.max_exact_state_action_rows
            ),
        }

    @property
    def cap_id(self) -> str:
        return _content_id("fallback_cap", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cap_id": self.cap_id}


@dataclass(frozen=True, slots=True)
class ExactFallbackCountersV1:
    complete_exact_ground_search_calls: int
    exact_state_action_rows: int
    inferred_exact_atom_calls: int
    cap_checks: int
    cap_rejections: int
    acquisition_transition_calls: int = 0
    logical_lane: str = FALLBACK_EXACT

    def __post_init__(self) -> None:
        if (
            self.complete_exact_ground_search_calls != 1
            or type(self.exact_state_action_rows) is not int
            or self.exact_state_action_rows <= 0
            or self.inferred_exact_atom_calls
            != self.exact_state_action_rows
            or self.cap_checks != 1
            or self.cap_rejections not in (0, 1)
            or self.acquisition_transition_calls != 0
            or self.logical_lane != FALLBACK_EXACT
        ):
            raise ObservationSupportExactEvaluationInvariantViolation(
                "exact fallback counters do not reconcile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_exact_fallback_counters.v1",
            "schema_version": SCHEMA_VERSION,
            "complete_exact_ground_search_calls": 1,
            "exact_state_action_rows": self.exact_state_action_rows,
            "inferred_exact_atom_calls": self.inferred_exact_atom_calls,
            "cap_checks": 1,
            "cap_rejections": self.cap_rejections,
            "acquisition_transition_calls": 0,
            "logical_lane": self.logical_lane,
        }

    @property
    def counters_id(self) -> str:
        return _content_id("fallback_counters", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counters_id": self.counters_id}


@dataclass(frozen=True, slots=True)
class ObservationSupportExactFallbackResultV1:
    context_id: str
    cap: ExactFallbackCapV1
    search: observer.EvaluationExactGroundSearchV1
    outcome: ExactFallbackOutcome
    counters: ExactFallbackCountersV1
    feasible_plan_certified: bool
    prerequisite_operational_freeze_id: str | None = None
    infeasibility_certified: bool = False
    interruptible_hard_cap_claimed: bool = False
    cap_semantics: str = FALLBACK_CAP_SEMANTICS
    logical_lane: str = FALLBACK_EXACT

    def __post_init__(self) -> None:
        _cid(self.context_id, "fallback context")
        if self.prerequisite_operational_freeze_id is not None:
            _cid(
                self.prerequisite_operational_freeze_id,
                "fallback prerequisite operational freeze",
            )
        expected_outcome = (
            ExactFallbackOutcome.CAP_EXHAUSTED_NONCERTIFICATE
            if (
                type(self.search)
                is observer.EvaluationExactGroundSearchV1
                and type(self.cap) is ExactFallbackCapV1
                and self.search.evaluated_state_action_rows
                > self.cap.max_exact_state_action_rows
            )
            else ExactFallbackOutcome.FEASIBLE_PLAN_CERTIFIED
        )
        if (
            type(self.cap) is not ExactFallbackCapV1
            or self.cap.context_id != self.context_id
            or type(self.search) is not observer.EvaluationExactGroundSearchV1
            or self.search.context_id != self.context_id
            or type(self.outcome) is not ExactFallbackOutcome
            or type(self.counters) is not ExactFallbackCountersV1
            or self.counters.exact_state_action_rows
            != self.search.evaluated_state_action_rows
            or self.counters.cap_rejections
            != (
                1
                if self.search.evaluated_state_action_rows
                > self.cap.max_exact_state_action_rows
                else 0
            )
            or self.outcome is not expected_outcome
            or self.feasible_plan_certified
            != (
                self.outcome
                is ExactFallbackOutcome.FEASIBLE_PLAN_CERTIFIED
            )
            or self.infeasibility_certified is not False
            or self.interruptible_hard_cap_claimed is not False
            or self.cap_semantics != FALLBACK_CAP_SEMANTICS
            or self.logical_lane != FALLBACK_EXACT
        ):
            raise ObservationSupportExactEvaluationInvariantViolation(
                "exact fallback result or classification is invalid"
            )

    @property
    def cap_exhausted(self) -> bool:
        return (
            self.outcome
            is ExactFallbackOutcome.CAP_EXHAUSTED_NONCERTIFICATE
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_exact_fallback_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "cap_id": self.cap.cap_id,
            "search_id": self.search.search_id,
            "outcome": self.outcome.value,
            "counters_id": self.counters.counters_id,
            "feasible_plan_certified": self.feasible_plan_certified,
            "prerequisite_operational_freeze": (
                {"kind": "STANDALONE_UNBOUND"}
                if self.prerequisite_operational_freeze_id is None
                else {
                    "kind": "BOUND_PREDECESSOR",
                    "operational_freeze_id": (
                        self.prerequisite_operational_freeze_id
                    ),
                }
            ),
            "infeasibility_certified": False,
            "interruptible_hard_cap_claimed": False,
            "cap_semantics": self.cap_semantics,
            "logical_lane": self.logical_lane,
        }

    @property
    def fallback_result_id(self) -> str:
        return _content_id("fallback", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "cap": self.cap.to_document(),
            "search": self.search.to_document(),
            "counters": self.counters.to_document(),
            "fallback_result_id": self.fallback_result_id,
        }


def run_observation_support_exact_fallback_v1(
    context: observer.PublicGraphContextV1,
    *,
    max_exact_state_action_rows: int = DEFAULT_FALLBACK_EXACT_ROW_CAP,
    prerequisite_operational_freeze_id: str | None = None,
) -> ObservationSupportExactFallbackResultV1:
    """Run the complete exact fallback in its own charged logical lane.

    The current exact-search authority is complete rather than interruptible.
    The cap is therefore checked against the fully charged realized search
    work.  Exceeding it closes this fallback attempt as a non-certificate;
    the complete result is retained for provenance but is not reclassified as
    either feasibility or infeasibility evidence.
    """

    registered = _registered_context(context)
    if prerequisite_operational_freeze_id is not None:
        _cid(
            prerequisite_operational_freeze_id,
            "fallback prerequisite operational freeze",
        )
    cap = ExactFallbackCapV1(
        registered.context_id,
        max_exact_state_action_rows,
    )
    search = observer.evaluation_exact_ground_search_v1(registered)
    rejected = (
        search.evaluated_state_action_rows
        > cap.max_exact_state_action_rows
    )
    outcome = (
        ExactFallbackOutcome.CAP_EXHAUSTED_NONCERTIFICATE
        if rejected
        else ExactFallbackOutcome.FEASIBLE_PLAN_CERTIFIED
    )
    counters = ExactFallbackCountersV1(
        1,
        search.evaluated_state_action_rows,
        search.evaluated_state_action_rows,
        1,
        int(rejected),
    )
    return ObservationSupportExactFallbackResultV1(
        registered.context_id,
        cap,
        search,
        outcome,
        counters,
        not rejected,
        prerequisite_operational_freeze_id,
    )


__all__ = [
    "CONTRACT_VERSION",
    "DEFAULT_FALLBACK_EXACT_ROW_CAP",
    "EVALUATION_ONLY",
    "ExactFallbackCapV1",
    "ExactFallbackCountersV1",
    "ExactFallbackOutcome",
    "ExactLiftDecisionV1",
    "ExactLiftEvaluationCountersV1",
    "FALLBACK_CAP_SEMANTICS",
    "FALLBACK_EXACT",
    "ObservationSupportExactEvaluationInvariantViolation",
    "ObservationSupportExactFallbackResultV1",
    "ObservationSupportExactLiftEvaluationV1",
    "ObservationSupportExactLiftVerificationV1",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "UNSEEN_OUTCOME_POLICY_SEMANTICS",
    "evaluate_observation_support_exact_lift_v1",
    "run_observation_support_exact_fallback_v1",
    "verify_observation_support_exact_lift_v1",
]
