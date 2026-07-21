"""Fail-closed feasibility audit for a real ground-derived transaction two.

The current H=2 safe-chain profile is a positive local-recovery control.  Its
registered transaction-1 repair exhausts the authorized deterministic policy
space and the ensuing sound ground post-audit certifies the stitched plan.  It
therefore cannot honestly exercise the ``FAILED -> deeper frontier`` edge of
the Phase-3E occurrence state machine.

This module makes that limitation executable instead of manufacturing a
failed certificate.  It consumes the live, production-shaped model-failure
preparation, replays the exact authorized materialization/compiler/solver/
stitch/post-audit calculation in the evaluation lane, and emits a
content-addressed artifact.  The replay does not invoke J0, mint route
semantic authority, call a test-only semantic finisher, or accept any caller-
supplied identity/hash.  It is not operational route work and it does not
close ``PRODUCTION_GROUND_DERIVED_TRANSACTION_TWO``.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import re
from typing import Any, Mapping

from acfqp.general_local_solver import (
    CERTIFIED,
    solve_general_local_recovery,
    validate_general_local_result,
)
from acfqp.local_recovery import PatchedAuditKernelView, audit_hybrid_policy
from acfqp.phase3d import (
    SAFE_CHAIN_SEARCH_LIMITS,
    _execute_safe_chain_local_preparation,
    _general_request,
    _overlay_from_result,
    require_safe_chain_prepared_estimate_context_v1,
    require_verified_model_estimate_binding_v1,
)
from acfqp.phase3e_ids import (
    GROUND_DERIVED_TRANSACTION_TWO_FEASIBILITY_AUDIT_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.phase3e_model_failure_consumer_v1 import (
    PreparedModelFailureConsumerV1,
)
from acfqp.routing_v1 import RouteSelection


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "phase3e_canonical_h2_transaction_two_feasibility_audit_v0"
OUTCOME = "CANONICAL_H2_TRANSACTION_TWO_UNREACHABLE"
REMAINING_OBLIGATION = "PRODUCTION_GROUND_DERIVED_TRANSACTION_TWO"
POST_AUDIT_CERTIFIED_OUTCOME = "CERTIFIED"
_DERIVED_LEGACY_ID = re.compile(
    r"^[a-z][a-z0-9-]*(?::|-)[0-9a-f]{16,64}$"
)

REQUIRED_NEW_FIXTURE_PROPERTIES = (
    "REGISTERED_QUERY_OR_STRUCTURAL_PROFILE_DISTINCT_FROM_CANONICAL_H2_POSITIVE_CONTROL",
    "TRANSACTION_ONE_REAL_LOCAL_CANDIDATE_WITH_SOUND_POSTAUDIT_FAILED",
    "NONEMPTY_EXACT_FAILED_OBLIGATIONS_BOUND_TO_POSTAUDIT_ISSUES",
    "NEW_GROUND_STATE_ACTION_DISTINCTIONS_OUTSIDE_TRANSACTION_ONE_FRONTIER",
    "STRICTLY_DEEPER_CONTENT_ADDRESSED_FRONTIER_AND_FRESH_PRODUCTION_AUTHORITIES",
    "TRANSACTION_TWO_REAL_SELECTED_ROUTE_EXECUTION_AND_TYPED_OCCURRENCE_CLOSURE",
    "BOTH_NATIVE_TRANSACTION_WORKVECTORS_RETAINED_AND_REPLAYABLE",
)


class TransactionTwoFeasibilityV1Error(ValueError):
    """The canonical H2 evaluation or its retained identity chain changed."""


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise TransactionTwoFeasibilityV1Error(
            f"{field_name} must be a full content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class GroundDerivedTransactionTwoFeasibilityAuditV1:
    """Replayable negative result for the canonical H2 transaction-2 edge."""

    model_only_result_id: str
    ground_binding_id: str
    route_decision_context_id: str
    selected_plan_id: str
    first_frontier_snapshot_id: str
    first_causal_evidence_id: str
    first_transaction_id: str
    local_cap_profile_id: str
    capability_id: str
    ground_slice_id: str
    solver_request_id: str
    solver_result_id: str
    threshold_profile_id: str
    risk_tolerance: Fraction
    regret_tolerance: Fraction
    lifted_reward_lower: Fraction
    lifted_failure_upper: Fraction
    regret_upper: Fraction
    first_frontier_obligation_count: int
    materialization_ground_steps: int
    materialization_positive_outcomes: int
    solver_policy_assignments: int
    patched_decision_count: int
    postaudit_ground_steps: int
    postaudit_issue_count: int
    unresolved_ground_distinction_count: int
    profile_key: str = PROFILE_KEY
    selected_route: str = RouteSelection.LOCAL.value
    solver_outcome: str = CERTIFIED
    post_audit_outcome: str = POST_AUDIT_CERTIFIED_OUTCOME
    outcome: str = OUTCOME
    remaining_obligation: str = REMAINING_OBLIGATION
    required_new_fixture_properties: tuple[str, ...] = (
        REQUIRED_NEW_FIXTURE_PROPERTIES
    )
    transaction_two_authorized: bool = False
    production_obligation_closed: bool = False
    evaluation_only: bool = True
    ground_replay_used: bool = True
    j0_used: bool = False
    test_only_semantic_finish_used: bool = False
    caller_supplied_hashes_used: bool = False
    official_execution_allowed: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "model_only_result_id",
            "ground_binding_id",
            "route_decision_context_id",
            "selected_plan_id",
            "first_frontier_snapshot_id",
            "first_causal_evidence_id",
            "first_transaction_id",
            "local_cap_profile_id",
            "threshold_profile_id",
        ):
            _cid(getattr(self, name), name)
        for name in (
            "capability_id",
            "ground_slice_id",
            "solver_request_id",
            "solver_result_id",
        ):
            value = getattr(self, name)
            if type(value) is not str or _DERIVED_LEGACY_ID.fullmatch(value) is None:
                raise TransactionTwoFeasibilityV1Error(
                    f"{name} must be a derived legacy opaque ID"
                )
        for name in (
            "risk_tolerance",
            "regret_tolerance",
            "lifted_reward_lower",
            "lifted_failure_upper",
            "regret_upper",
        ):
            object.__setattr__(self, name, Fraction(getattr(self, name)))
        if (
            self.profile_key != PROFILE_KEY
            or self.selected_route != RouteSelection.LOCAL.value
            or self.solver_outcome != CERTIFIED
            or self.post_audit_outcome != POST_AUDIT_CERTIFIED_OUTCOME
            or self.outcome != OUTCOME
            or self.remaining_obligation != REMAINING_OBLIGATION
            or self.required_new_fixture_properties
            != REQUIRED_NEW_FIXTURE_PROPERTIES
            or self.transaction_two_authorized is not False
            or self.production_obligation_closed is not False
            or self.evaluation_only is not True
            or self.ground_replay_used is not True
            or self.j0_used is not False
            or self.test_only_semantic_finish_used is not False
            or self.caller_supplied_hashes_used is not False
            or self.official_execution_allowed is not False
            or self.schema_version != SCHEMA_VERSION
        ):
            raise TransactionTwoFeasibilityV1Error(
                "transaction-2 feasibility audit overclaims its scope"
            )
        integer_values = (
            self.first_frontier_obligation_count,
            self.materialization_ground_steps,
            self.materialization_positive_outcomes,
            self.solver_policy_assignments,
            self.patched_decision_count,
            self.postaudit_ground_steps,
            self.postaudit_issue_count,
            self.unresolved_ground_distinction_count,
        )
        if any(type(value) is not int or value < 0 for value in integer_values):
            raise TransactionTwoFeasibilityV1Error(
                "transaction-2 feasibility counts must be nonnegative integers"
            )
        # These are the exact registered canonical-H2 ground replay values.  A
        # change must create a new profile/version, not silently unlock tx2.
        if (
            self.risk_tolerance != Fraction(1, 20)
            or self.regret_tolerance != Fraction(1, 20)
            or self.lifted_reward_lower != Fraction(3, 64)
            or self.lifted_failure_upper != Fraction(397, 20000)
            or self.regret_upper != 0
            or self.first_frontier_obligation_count < 1
            or self.materialization_ground_steps != 16
            or self.materialization_positive_outcomes != 64
            or self.solver_policy_assignments != 257
            or self.patched_decision_count != 8
            or self.postaudit_ground_steps != 8
            or self.postaudit_issue_count != 0
            or self.unresolved_ground_distinction_count != 0
            or not self.lifted_failure_upper < self.risk_tolerance
            or not self.regret_upper <= self.regret_tolerance
        ):
            raise TransactionTwoFeasibilityV1Error(
                "canonical H2 local/post-audit golden changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.ground_derived_transaction_two_feasibility_audit.v1",
            "schema_version": self.schema_version,
            "profile_key": self.profile_key,
            "model_only_result_id": self.model_only_result_id,
            "ground_binding_id": self.ground_binding_id,
            "route_decision_context_id": self.route_decision_context_id,
            "selected_plan_id": self.selected_plan_id,
            "first_frontier_snapshot_id": self.first_frontier_snapshot_id,
            "first_causal_evidence_id": self.first_causal_evidence_id,
            "first_transaction_id": self.first_transaction_id,
            "local_cap_profile_id": self.local_cap_profile_id,
            "capability_id": self.capability_id,
            "ground_slice_id": self.ground_slice_id,
            "solver_request_id": self.solver_request_id,
            "solver_result_id": self.solver_result_id,
            "threshold_profile_id": self.threshold_profile_id,
            "risk_tolerance": self.risk_tolerance,
            "regret_tolerance": self.regret_tolerance,
            "lifted_reward_lower": self.lifted_reward_lower,
            "lifted_failure_upper": self.lifted_failure_upper,
            "regret_upper": self.regret_upper,
            "first_frontier_obligation_count": (
                self.first_frontier_obligation_count
            ),
            "materialization_ground_steps": self.materialization_ground_steps,
            "materialization_positive_outcomes": (
                self.materialization_positive_outcomes
            ),
            "solver_policy_assignments": self.solver_policy_assignments,
            "patched_decision_count": self.patched_decision_count,
            "postaudit_ground_steps": self.postaudit_ground_steps,
            "postaudit_issue_count": self.postaudit_issue_count,
            "unresolved_ground_distinction_count": (
                self.unresolved_ground_distinction_count
            ),
            "selected_route": self.selected_route,
            "solver_outcome": self.solver_outcome,
            "post_audit_outcome": self.post_audit_outcome,
            "outcome": self.outcome,
            "remaining_obligation": self.remaining_obligation,
            "required_new_fixture_properties": list(
                self.required_new_fixture_properties
            ),
            "transaction_two_authorized": self.transaction_two_authorized,
            "production_obligation_closed": self.production_obligation_closed,
            "evaluation_only": self.evaluation_only,
            "ground_replay_used": self.ground_replay_used,
            "j0_used": self.j0_used,
            "test_only_semantic_finish_used": (
                self.test_only_semantic_finish_used
            ),
            "caller_supplied_hashes_used": self.caller_supplied_hashes_used,
            "official_execution_allowed": self.official_execution_allowed,
        }

    @property
    def feasibility_audit_id(self) -> str:
        return content_id(
            GROUND_DERIVED_TRANSACTION_TWO_FEASIBILITY_AUDIT_DOMAIN,
            self._payload(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "feasibility_audit_id": self.feasibility_audit_id}

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "GroundDerivedTransactionTwoFeasibilityAuditV1":
        fields = {
            "schema",
            "schema_version",
            "profile_key",
            "model_only_result_id",
            "ground_binding_id",
            "route_decision_context_id",
            "selected_plan_id",
            "first_frontier_snapshot_id",
            "first_causal_evidence_id",
            "first_transaction_id",
            "local_cap_profile_id",
            "capability_id",
            "ground_slice_id",
            "solver_request_id",
            "solver_result_id",
            "threshold_profile_id",
            "risk_tolerance",
            "regret_tolerance",
            "lifted_reward_lower",
            "lifted_failure_upper",
            "regret_upper",
            "first_frontier_obligation_count",
            "materialization_ground_steps",
            "materialization_positive_outcomes",
            "solver_policy_assignments",
            "patched_decision_count",
            "postaudit_ground_steps",
            "postaudit_issue_count",
            "unresolved_ground_distinction_count",
            "selected_route",
            "solver_outcome",
            "post_audit_outcome",
            "outcome",
            "remaining_obligation",
            "required_new_fixture_properties",
            "transaction_two_authorized",
            "production_obligation_closed",
            "evaluation_only",
            "ground_replay_used",
            "j0_used",
            "test_only_semantic_finish_used",
            "caller_supplied_hashes_used",
            "official_execution_allowed",
            "feasibility_audit_id",
        }
        require_exact_fields(
            document, fields, context="transaction-2 feasibility audit"
        )
        if (
            document["schema"]
            != "acfqp.ground_derived_transaction_two_feasibility_audit.v1"
            or type(document["required_new_fixture_properties"]) is not list
        ):
            raise TransactionTwoFeasibilityV1Error(
                "transaction-2 feasibility audit schema mismatch"
            )
        result = cls(
            model_only_result_id=document["model_only_result_id"],
            ground_binding_id=document["ground_binding_id"],
            route_decision_context_id=document["route_decision_context_id"],
            selected_plan_id=document["selected_plan_id"],
            first_frontier_snapshot_id=document["first_frontier_snapshot_id"],
            first_causal_evidence_id=document["first_causal_evidence_id"],
            first_transaction_id=document["first_transaction_id"],
            local_cap_profile_id=document["local_cap_profile_id"],
            capability_id=document["capability_id"],
            ground_slice_id=document["ground_slice_id"],
            solver_request_id=document["solver_request_id"],
            solver_result_id=document["solver_result_id"],
            threshold_profile_id=document["threshold_profile_id"],
            risk_tolerance=document["risk_tolerance"],
            regret_tolerance=document["regret_tolerance"],
            lifted_reward_lower=document["lifted_reward_lower"],
            lifted_failure_upper=document["lifted_failure_upper"],
            regret_upper=document["regret_upper"],
            first_frontier_obligation_count=document[
                "first_frontier_obligation_count"
            ],
            materialization_ground_steps=document[
                "materialization_ground_steps"
            ],
            materialization_positive_outcomes=document[
                "materialization_positive_outcomes"
            ],
            solver_policy_assignments=document["solver_policy_assignments"],
            patched_decision_count=document["patched_decision_count"],
            post_audit_outcome=document["post_audit_outcome"],
            postaudit_ground_steps=document["postaudit_ground_steps"],
            postaudit_issue_count=document["postaudit_issue_count"],
            unresolved_ground_distinction_count=document[
                "unresolved_ground_distinction_count"
            ],
            profile_key=document["profile_key"],
            selected_route=document["selected_route"],
            solver_outcome=document["solver_outcome"],
            outcome=document["outcome"],
            remaining_obligation=document["remaining_obligation"],
            required_new_fixture_properties=tuple(
                document["required_new_fixture_properties"]
            ),
            transaction_two_authorized=document["transaction_two_authorized"],
            production_obligation_closed=document[
                "production_obligation_closed"
            ],
            evaluation_only=document["evaluation_only"],
            ground_replay_used=document["ground_replay_used"],
            j0_used=document["j0_used"],
            test_only_semantic_finish_used=document[
                "test_only_semantic_finish_used"
            ],
            caller_supplied_hashes_used=document[
                "caller_supplied_hashes_used"
            ],
            official_execution_allowed=document["official_execution_allowed"],
            schema_version=document["schema_version"],
        )
        if document["feasibility_audit_id"] != result.feasibility_audit_id:
            raise TransactionTwoFeasibilityV1Error(
                "transaction-2 feasibility audit ID mismatch"
            )
        return result


def audit_canonical_h2_transaction_two_feasibility_v1(
    prepared_consumer: PreparedModelFailureConsumerV1,
) -> GroundDerivedTransactionTwoFeasibilityAuditV1:
    """Replay the canonical H2 local tail and fail closed when it certifies."""

    if type(prepared_consumer) is not PreparedModelFailureConsumerV1:
        raise TransactionTwoFeasibilityV1Error(
            "feasibility audit requires a live prepared model-failure consumer"
        )
    prepared_consumer.validate_before_run()
    if prepared_consumer.selected_route is not RouteSelection.LOCAL:
        raise TransactionTwoFeasibilityV1Error(
            "canonical H2 feasibility audit requires selected LOCAL"
        )
    authorities = prepared_consumer.route_authorities
    prepared_local = require_safe_chain_prepared_estimate_context_v1(
        authorities.prepared_local
    )
    require_verified_model_estimate_binding_v1(prepared_local)
    transaction = authorities.transaction
    if (
        transaction.transaction_index != 1
        or authorities.frontier.frontier_stage != 1
        or transaction.frontier_snapshot_id
        != authorities.frontier.frontier_snapshot_id
        or transaction.route_cap_profile_id
        != authorities.local_bound.route_cap_profile_id
    ):
        raise TransactionTwoFeasibilityV1Error(
            "canonical H2 transaction-1 authority chain is stale"
        )

    # This is an explicit evaluation replay.  It uses the same registered
    # materializer, compiler, finite solver and sound auditor as the selected
    # local route, but never invokes the sealed executor or mints route
    # semantic authority.
    local = _execute_safe_chain_local_preparation(prepared_local)
    request = _general_request(
        occurrence_id=(
            "phase3e-tx2-feasibility:"
            + prepared_consumer.route_authorities.transaction.transaction_id
        ),
        capability=local.capability,
        ground_slice=local.sparse_slice,
        limits=SAFE_CHAIN_SEARCH_LIMITS,
    )
    solver = solve_general_local_recovery(
        local.capability, local.sparse_slice, request
    )
    solver_document = solver.to_dict()
    validate_general_local_result(solver_document)
    if solver_document["status"] != CERTIFIED:
        raise TransactionTwoFeasibilityV1Error(
            "canonical H2 local solver no longer returns its certified candidate"
        )
    overlay = _overlay_from_result(local, solver_document)
    post_kernel = PatchedAuditKernelView(
        local.world.kernel,
        tuple((decision.state, decision.action) for decision in overlay.decisions),
    )
    post = audit_hybrid_policy(
        post_kernel,
        local.query,
        local.world.models.envelope,
        overlay,
        regret_tolerance=prepared_local.pre_audit.regret_tolerance,
        unrestricted_reward_upper=local.unrestricted_reward_upper,
    )
    post_steps = sum(
        row.operation == "step" for row in post_kernel.access_log
    )
    if not post.certified:
        # A future real failure must be registered under a new fixture/profile
        # and enter the production continuation chain.  This negative-control
        # profile must never silently relabel that event as success here.
        raise TransactionTwoFeasibilityV1Error(
            "canonical H2 golden changed: register a new transaction-2 fixture"
        )

    materialization = local.materialization_counts
    counters = solver_document["counters"]
    context = prepared_consumer.prepared.context
    artifact = GroundDerivedTransactionTwoFeasibilityAuditV1(
        model_only_result_id=(
            prepared_consumer.failed_prefix_authority.model_only_result_id
        ),
        ground_binding_id=prepared_consumer.ground_binding_id,
        route_decision_context_id=context.route_decision_context_id,
        selected_plan_id=context.selected_plan_id,
        first_frontier_snapshot_id=authorities.frontier.frontier_snapshot_id,
        first_causal_evidence_id=authorities.causal.causal_evidence_id,
        first_transaction_id=transaction.transaction_id,
        local_cap_profile_id=transaction.route_cap_profile_id,
        capability_id=local.capability["capability_id"],
        ground_slice_id=local.sparse_slice["slice_id"],
        solver_request_id=request["request_id"],
        solver_result_id=solver_document["result_id"],
        threshold_profile_id=context.threshold_profile_id,
        risk_tolerance=post.risk_tolerance,
        regret_tolerance=post.regret_tolerance,
        lifted_reward_lower=post.lifted_reward_lower,
        lifted_failure_upper=post.lifted_failure_upper,
        regret_upper=post.regret_upper,
        first_frontier_obligation_count=len(
            authorities.frontier.failed_obligation_ids
        ),
        materialization_ground_steps=materialization[
            "state_action_steps"
        ],
        materialization_positive_outcomes=materialization[
            "positive_probability_outcomes"
        ],
        solver_policy_assignments=counters["policy_assignments"],
        patched_decision_count=len(overlay.decisions),
        post_audit_outcome=POST_AUDIT_CERTIFIED_OUTCOME,
        postaudit_ground_steps=post_steps,
        postaudit_issue_count=len(post.issues),
        unresolved_ground_distinction_count=len(post.issues),
    )
    # Round-trip before returning so a malformed schema cannot acquire a live
    # negative-control interpretation merely by being locally constructed.
    if GroundDerivedTransactionTwoFeasibilityAuditV1.from_dict(
        artifact.to_dict()
    ) != artifact:
        raise TransactionTwoFeasibilityV1Error(
            "transaction-2 feasibility audit is not replay-stable"
        )
    return artifact


def verify_canonical_h2_transaction_two_feasibility_audit_v1(
    prepared_consumer: PreparedModelFailureConsumerV1,
    claimed: GroundDerivedTransactionTwoFeasibilityAuditV1,
) -> GroundDerivedTransactionTwoFeasibilityAuditV1:
    """Independently rerun the ground evaluation and compare the full artifact."""

    if type(claimed) is not GroundDerivedTransactionTwoFeasibilityAuditV1:
        raise TransactionTwoFeasibilityV1Error(
            "transaction-2 feasibility verifier requires the typed artifact"
        )
    replay = audit_canonical_h2_transaction_two_feasibility_v1(
        prepared_consumer
    )
    if replay != claimed or replay.feasibility_audit_id != claimed.feasibility_audit_id:
        raise TransactionTwoFeasibilityV1Error(
            "transaction-2 feasibility claim differs from ground replay"
        )
    return replay


__all__ = [
    "OUTCOME",
    "POST_AUDIT_CERTIFIED_OUTCOME",
    "PROFILE_KEY",
    "REMAINING_OBLIGATION",
    "REQUIRED_NEW_FIXTURE_PROPERTIES",
    "GroundDerivedTransactionTwoFeasibilityAuditV1",
    "TransactionTwoFeasibilityV1Error",
    "audit_canonical_h2_transaction_two_feasibility_v1",
    "verify_canonical_h2_transaction_two_feasibility_audit_v1",
]
