"""Auditable Phase-3E route-state-machine candidate.

Unlike the low-level mechanics in :mod:`acfqp.dynamic_router`, this module only
accepts a complete hash-chained envelope as route evidence.  Every event binds a
single query/plan/epoch/occurrence/attempt context, references independently
verified artifacts, carries exact charged work, and follows a replayed transition
table.  The protocol remains non-official while Phase-3E normative decisions are
unresolved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from acfqp.artifacts import object_id
from acfqp.phase3e_accounting import ECONOMICS_NOT_RUN, ROUTING_MECHANICS_ONLY
from acfqp.route_comparison import (
    DIRECT_FALLBACK,
    LOCAL_ATTEMPT,
    ComparisonVector,
    RouteUpperBoundCandidate,
    compare_route_upper_bounds,
)
from acfqp.work_accounting import (
    EQUAL,
    INCOMPARABLE,
    LEFT_DOMINATES,
    RIGHT_DOMINATES,
    CounterRegistry,
    CounterValidationError,
    WorkVector,
    sum_work_vectors,
)


START = "START"
INTEGRITY_VERIFIED = "INTEGRITY_VERIFIED"
COMPATIBILITY_VERIFIED = "COMPATIBILITY_VERIFIED"
CACHE_CHECKED = "CACHE_CHECKED"
ABSTRACT_FAILED = "ABSTRACT_FAILED"
ROUTE_ESTIMATION_REQUIRED = "ROUTE_ESTIMATION_REQUIRED"
LOCAL_EXECUTION_REQUIRED = "LOCAL_EXECUTION_REQUIRED"
FALLBACK_EXECUTION_REQUIRED = "FALLBACK_EXECUTION_REQUIRED"
NEXT_LOCAL_TRANSACTION_REQUIRED = "NEXT_LOCAL_TRANSACTION_REQUIRED"

PROTOCOL_FAILURE_ATTEMPT_TERMINAL = "PROTOCOL_FAILURE_ATTEMPT_TERMINAL"
REBUILD_REQUIRED_ATTEMPT_TERMINAL = "REBUILD_REQUIRED_ATTEMPT_TERMINAL"
ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL = "ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL"
LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL = (
    "LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL"
)
FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL = (
    "FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL"
)
INFEASIBLE_QUERY_ATTEMPT_TERMINAL = "INFEASIBLE_QUERY_ATTEMPT_TERMINAL"
FALLBACK_CAP_EXHAUSTED_ATTEMPT_TERMINAL = (
    "FALLBACK_CAP_EXHAUSTED_NO_CERTIFICATE_ATTEMPT_TERMINAL"
)

INTEGRITY = "INTEGRITY"
COMPATIBILITY = "COMPATIBILITY"
CACHE_PROOF = "CACHE_PROOF"
ABSTRACT_AUDIT = "ABSTRACT_AUDIT"
CAUSAL_SEARCH = "CAUSAL_SEARCH"
ROUTE_SELECTION = "ROUTE_SELECTION"
LOCAL_RESULT = "LOCAL_RESULT"
FALLBACK_RESULT = "FALLBACK_RESULT"

PASS = "PASS"
FAIL = "FAIL"
MATCH = "MATCH"
MISMATCH = "MISMATCH"
MISS = "MISS"
FOUND = "FOUND"
CAP_EXHAUSTED = "CAP_EXHAUSTED"
NO_SOUND_COVER = "NO_SOUND_COVER"
LOCAL_CAP_IMPOSSIBLE = "LOCAL_CAP_IMPOSSIBLE"
SELECT_LOCAL = "SELECT_LOCAL"
SELECT_FALLBACK_NO_LOCAL = "SELECT_FALLBACK_NO_LOCAL"
SELECT_FALLBACK_DOMINATES = "SELECT_FALLBACK_DOMINATES"
SELECT_FALLBACK_EQUAL = "SELECT_FALLBACK_EQUAL"
SELECT_FALLBACK_INCOMPARABLE = "SELECT_FALLBACK_INCOMPARABLE"
CERTIFIED = "CERTIFIED"
FAILED_DEEPER_BUDGET_REMAINS = "FAILED_DEEPER_BUDGET_REMAINS"
FAILED_DEEPER_BUDGET_EXHAUSTED = "FAILED_DEEPER_BUDGET_EXHAUSTED"
FAILED_NO_SOUND_FRONTIER = "FAILED_NO_SOUND_FRONTIER"
CERTIFIED_FEASIBLE = "CERTIFIED_FEASIBLE"
CERTIFIED_INFEASIBLE = "CERTIFIED_INFEASIBLE"
INCOMPLETE_DUE_TO_CAP = "INCOMPLETE_DUE_TO_CAP"

_TERMINAL_STATES = frozenset(
    {
        PROTOCOL_FAILURE_ATTEMPT_TERMINAL,
        REBUILD_REQUIRED_ATTEMPT_TERMINAL,
        ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL,
        LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL,
        FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL,
        INFEASIBLE_QUERY_ATTEMPT_TERMINAL,
        FALLBACK_CAP_EXHAUSTED_ATTEMPT_TERMINAL,
    }
)
_OUTCOMES = {
    INTEGRITY: frozenset({PASS, FAIL}),
    COMPATIBILITY: frozenset({MATCH, MISMATCH}),
    CACHE_PROOF: frozenset({MATCH, MISS}),
    ABSTRACT_AUDIT: frozenset({PASS, FAIL}),
    CAUSAL_SEARCH: frozenset(
        {FOUND, CAP_EXHAUSTED, NO_SOUND_COVER, LOCAL_CAP_IMPOSSIBLE}
    ),
    ROUTE_SELECTION: frozenset(
        {
            SELECT_LOCAL,
            SELECT_FALLBACK_NO_LOCAL,
            SELECT_FALLBACK_DOMINATES,
            SELECT_FALLBACK_EQUAL,
            SELECT_FALLBACK_INCOMPARABLE,
        }
    ),
    LOCAL_RESULT: frozenset(
        {
            CERTIFIED,
            FAILED_DEEPER_BUDGET_REMAINS,
            FAILED_DEEPER_BUDGET_EXHAUSTED,
            FAILED_NO_SOUND_FRONTIER,
        }
    ),
    FALLBACK_RESULT: frozenset(
        {CERTIFIED_FEASIBLE, CERTIFIED_INFEASIBLE, INCOMPLETE_DUE_TO_CAP}
    ),
}
_REQUIRED_ARTIFACT_ROLES = {
    (INTEGRITY, PASS): frozenset({"integrity_attestation"}),
    (INTEGRITY, FAIL): frozenset({"integrity_failure_attestation"}),
    (COMPATIBILITY, MATCH): frozenset({"compatibility_attestation"}),
    (COMPATIBILITY, MISMATCH): frozenset({"compatibility_mismatch_attestation"}),
    (CACHE_PROOF, MATCH): frozenset(
        {"exact_infeasibility_proof", "proof_verification"}
    ),
    (CACHE_PROOF, MISS): frozenset({"cache_proof_check"}),
    (ABSTRACT_AUDIT, PASS): frozenset(
        {"abstract_audit", "policy_graph", "threshold_profile"}
    ),
    (ABSTRACT_AUDIT, FAIL): frozenset(
        {"abstract_audit", "failed_proof_graph", "threshold_profile"}
    ),
    (CAUSAL_SEARCH, FOUND): frozenset(
        {"causal_certificate", "local_authorization"}
    ),
    (CAUSAL_SEARCH, CAP_EXHAUSTED): frozenset({"causal_cap_attestation"}),
    (CAUSAL_SEARCH, NO_SOUND_COVER): frozenset({"causal_exhaustion_attestation"}),
    (CAUSAL_SEARCH, LOCAL_CAP_IMPOSSIBLE): frozenset(
        {"local_cap_impossibility_attestation"}
    ),
    (ROUTE_SELECTION, SELECT_LOCAL): frozenset(
        {"comparison_profile", "local_upper_bound", "fallback_upper_bound"}
    ),
    (ROUTE_SELECTION, SELECT_FALLBACK_NO_LOCAL): frozenset(
        {"comparison_profile", "fallback_upper_bound"}
    ),
    (ROUTE_SELECTION, SELECT_FALLBACK_DOMINATES): frozenset(
        {"comparison_profile", "local_upper_bound", "fallback_upper_bound"}
    ),
    (ROUTE_SELECTION, SELECT_FALLBACK_EQUAL): frozenset(
        {"comparison_profile", "local_upper_bound", "fallback_upper_bound"}
    ),
    (ROUTE_SELECTION, SELECT_FALLBACK_INCOMPARABLE): frozenset(
        {"comparison_profile", "local_upper_bound", "fallback_upper_bound"}
    ),
    (LOCAL_RESULT, CERTIFIED): frozenset(
        {"local_result", "post_audit_certificate", "actual_work"}
    ),
    (LOCAL_RESULT, FAILED_DEEPER_BUDGET_REMAINS): frozenset(
        {"local_result", "post_audit_failure", "actual_work"}
    ),
    (LOCAL_RESULT, FAILED_DEEPER_BUDGET_EXHAUSTED): frozenset(
        {"local_result", "post_audit_failure", "actual_work"}
    ),
    (LOCAL_RESULT, FAILED_NO_SOUND_FRONTIER): frozenset(
        {"local_result", "post_audit_failure", "actual_work"}
    ),
    (FALLBACK_RESULT, CERTIFIED_FEASIBLE): frozenset(
        {"fallback_result", "ground_certificate", "actual_work"}
    ),
    (FALLBACK_RESULT, CERTIFIED_INFEASIBLE): frozenset(
        {"fallback_result", "exact_infeasibility_proof", "actual_work"}
    ),
    (FALLBACK_RESULT, INCOMPLETE_DUE_TO_CAP): frozenset(
        {"fallback_cap_attestation", "fallback_result", "actual_work"}
    ),
}


class AuditableRouterError(ValueError):
    """The route trace, evidence, transition, or accounting is invalid."""


def _identifier(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise AuditableRouterError(f"{field} must be nonempty")
    return value


@dataclass(frozen=True, slots=True)
class RouteDecisionContext:
    preregistration_skeleton_id: str
    protocol_candidate_id: str
    comparison_profile_candidate_id: str
    counter_registry_id: str
    structural_id: str
    query_id: str
    plan_id: str
    threshold_profile_id: str
    epoch_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    campaign_retry_policy: None = None
    official: bool = False

    def __post_init__(self) -> None:
        for field in (
            "preregistration_skeleton_id",
            "protocol_candidate_id",
            "comparison_profile_candidate_id",
            "counter_registry_id",
            "structural_id",
            "query_id",
            "plan_id",
            "threshold_profile_id",
            "epoch_id",
            "logical_occurrence_id",
            "route_attempt_id",
        ):
            _identifier(getattr(self, field), field=field)
        if self.campaign_retry_policy is not None:
            raise AuditableRouterError("campaign rebuild/retry policy is unresolved")
        if self.official:
            raise AuditableRouterError("preconstruction route context cannot be official")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_decision_context.phase3e_candidate.v1",
            "preregistration_skeleton_id": self.preregistration_skeleton_id,
            "protocol_candidate_id": self.protocol_candidate_id,
            "comparison_profile_candidate_id": self.comparison_profile_candidate_id,
            "counter_registry_id": self.counter_registry_id,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "plan_id": self.plan_id,
            "threshold_profile_id": self.threshold_profile_id,
            "epoch_id": self.epoch_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "campaign_retry_policy": None,
            "official": False,
        }

    @property
    def context_id(self) -> str:
        return object_id(self._payload(), "route-decision-context")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "context_id": self.context_id}


def evidence_work_subject(
    context_id: str, role: str, transaction_id: str | None
) -> str:
    suffix = transaction_id if transaction_id is not None else "none"
    return f"{context_id}:{role.lower()}:{suffix}"


def _comparison_vector_from_dict(document: Mapping[str, Any]) -> ComparisonVector:
    expected = {
        "schema",
        "profile_id",
        "context_id",
        "route_candidate",
        "values",
        "official",
        "vector_id",
    }
    if set(document) != expected:
        raise AuditableRouterError("actual comparison-vector field set mismatch")
    if (
        document["schema"] != "acfqp.route_comparison_vector_candidate.v1"
        or document["official"] is not False
    ):
        raise AuditableRouterError("actual comparison-vector metadata mismatch")
    rows = document["values"]
    if not isinstance(rows, list):
        raise AuditableRouterError("actual comparison values must be a list")
    values = []
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {"axis", "value"}:
            raise AuditableRouterError("actual comparison row is malformed")
        values.append((row["axis"], row["value"]))
    vector = ComparisonVector(
        document["profile_id"],
        document["context_id"],
        document["route_candidate"],
        tuple(values),
    )
    if document["vector_id"] != vector.vector_id:
        raise AuditableRouterError("actual comparison-vector content ID mismatch")
    return vector


@dataclass(frozen=True, slots=True)
class TransitionEvidence:
    context_id: str
    role: str
    outcome: str
    artifact_refs: tuple[tuple[str, str], ...]
    work_delta: WorkVector
    transaction_id: str | None = None
    local_bound_id: str | None = None
    fallback_bound_id: str | None = None
    actual_comparison: ComparisonVector | None = None

    def __post_init__(self) -> None:
        _identifier(self.context_id, field="evidence context_id")
        if self.role not in _OUTCOMES or self.outcome not in _OUTCOMES[self.role]:
            raise AuditableRouterError("unknown evidence role/outcome")
        if tuple(sorted(self.artifact_refs)) != self.artifact_refs:
            raise AuditableRouterError("artifact references must be sorted")
        roles = set()
        for artifact_role, artifact_id in self.artifact_refs:
            _identifier(artifact_role, field="artifact role")
            _identifier(artifact_id, field="artifact ID")
            if artifact_role in roles:
                raise AuditableRouterError("evidence repeats an artifact role")
            roles.add(artifact_role)
        required = _REQUIRED_ARTIFACT_ROLES[(self.role, self.outcome)]
        if not required.issubset(roles):
            raise AuditableRouterError(
                f"evidence misses required artifact roles: {sorted(required - roles)!r}"
            )
        if self.transaction_id is not None:
            _identifier(self.transaction_id, field="transaction_id")
        expected_subject = evidence_work_subject(
            self.context_id, self.role, self.transaction_id
        )
        if self.work_delta.subject_id != expected_subject:
            raise AuditableRouterError("work delta is not bound to this evidence")
        if self.role == ROUTE_SELECTION:
            _identifier(self.fallback_bound_id, field="fallback_bound_id")
            if self.outcome == SELECT_FALLBACK_NO_LOCAL:
                if self.local_bound_id is not None:
                    raise AuditableRouterError("no-local selection carries a local bound")
            else:
                _identifier(self.local_bound_id, field="local_bound_id")
        elif self.local_bound_id is not None or self.fallback_bound_id is not None:
            raise AuditableRouterError("only route selection may carry upper-bound IDs")
        if self.role in {LOCAL_RESULT, FALLBACK_RESULT}:
            if self.actual_comparison is None:
                raise AuditableRouterError("execution result lacks actual comparison work")
            expected_route = LOCAL_ATTEMPT if self.role == LOCAL_RESULT else DIRECT_FALLBACK
            if (
                self.actual_comparison.context_id != self.context_id
                or self.actual_comparison.route_candidate != expected_route
            ):
                raise AuditableRouterError("actual comparison work binding mismatch")
        elif self.actual_comparison is not None:
            raise AuditableRouterError("non-execution evidence carries actual work")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_transition_evidence.phase3e_candidate.v1",
            "context_id": self.context_id,
            "role": self.role,
            "outcome": self.outcome,
            "artifact_refs": [
                {"role": role, "artifact_id": artifact_id}
                for role, artifact_id in self.artifact_refs
            ],
            "work_delta": self.work_delta.to_dict(),
            "transaction_id": self.transaction_id,
            "local_bound_id": self.local_bound_id,
            "fallback_bound_id": self.fallback_bound_id,
            "actual_comparison": (
                self.actual_comparison.to_dict()
                if self.actual_comparison is not None
                else None
            ),
            "official": False,
        }

    @property
    def evidence_id(self) -> str:
        return object_id(self._payload(), "route-transition-evidence")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "evidence_id": self.evidence_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "TransitionEvidence":
        expected = {
            "schema",
            "context_id",
            "role",
            "outcome",
            "artifact_refs",
            "work_delta",
            "transaction_id",
            "local_bound_id",
            "fallback_bound_id",
            "actual_comparison",
            "official",
            "evidence_id",
        }
        if set(document) != expected:
            raise AuditableRouterError("transition evidence field set mismatch")
        if (
            document["schema"]
            != "acfqp.route_transition_evidence.phase3e_candidate.v1"
            or document["official"] is not False
        ):
            raise AuditableRouterError("transition evidence metadata mismatch")
        raw_refs = document["artifact_refs"]
        work_doc = document["work_delta"]
        if not isinstance(raw_refs, list) or not isinstance(work_doc, Mapping):
            raise AuditableRouterError("transition evidence nested data is malformed")
        refs = []
        for row in raw_refs:
            if not isinstance(row, Mapping) or set(row) != {"role", "artifact_id"}:
                raise AuditableRouterError("artifact reference is malformed")
            refs.append((row["role"], row["artifact_id"]))
        actual_doc = document["actual_comparison"]
        if actual_doc is not None and not isinstance(actual_doc, Mapping):
            raise AuditableRouterError("actual comparison document is malformed")
        evidence = cls(
            context_id=document["context_id"],
            role=document["role"],
            outcome=document["outcome"],
            artifact_refs=tuple(refs),
            work_delta=WorkVector.from_dict(work_doc),
            transaction_id=document["transaction_id"],
            local_bound_id=document["local_bound_id"],
            fallback_bound_id=document["fallback_bound_id"],
            actual_comparison=(
                _comparison_vector_from_dict(actual_doc)
                if actual_doc is not None
                else None
            ),
        )
        if document["evidence_id"] != evidence.evidence_id:
            raise AuditableRouterError("transition evidence content ID mismatch")
        return evidence


def make_route_selection_evidence(
    *,
    context: RouteDecisionContext,
    work_delta: WorkVector,
    fallback_bound: RouteUpperBoundCandidate,
    local_bound: RouteUpperBoundCandidate | None,
    transaction_id: str,
) -> TransitionEvidence:
    if (
        fallback_bound.context_id != context.context_id
        or fallback_bound.profile_id != context.comparison_profile_candidate_id
        or fallback_bound.route_candidate != DIRECT_FALLBACK
    ):
        raise AuditableRouterError("fallback bound is not bound to the route context")
    refs = {
        "comparison_profile": context.comparison_profile_candidate_id,
        "fallback_upper_bound": fallback_bound.bound_id,
    }
    if local_bound is None:
        outcome = SELECT_FALLBACK_NO_LOCAL
        local_bound_id = None
    else:
        if (
            local_bound.context_id != context.context_id
            or local_bound.profile_id != context.comparison_profile_candidate_id
            or local_bound.route_candidate != LOCAL_ATTEMPT
        ):
            raise AuditableRouterError("local bound is not bound to the route context")
        refs["local_upper_bound"] = local_bound.bound_id
        relation = compare_route_upper_bounds(local_bound, fallback_bound)
        outcomes = {
            LEFT_DOMINATES: SELECT_LOCAL,
            RIGHT_DOMINATES: SELECT_FALLBACK_DOMINATES,
            EQUAL: SELECT_FALLBACK_EQUAL,
            INCOMPARABLE: SELECT_FALLBACK_INCOMPARABLE,
        }
        outcome = outcomes[relation]
        local_bound_id = local_bound.bound_id
    return TransitionEvidence(
        context_id=context.context_id,
        role=ROUTE_SELECTION,
        outcome=outcome,
        artifact_refs=tuple(sorted(refs.items())),
        work_delta=work_delta,
        transaction_id=transaction_id,
        local_bound_id=local_bound_id,
        fallback_bound_id=fallback_bound.bound_id,
    )


def _next_state(state: str, evidence: TransitionEvidence) -> str:
    key = (state, evidence.role, evidence.outcome)
    table = {
        (START, INTEGRITY, PASS): INTEGRITY_VERIFIED,
        (START, INTEGRITY, FAIL): PROTOCOL_FAILURE_ATTEMPT_TERMINAL,
        (INTEGRITY_VERIFIED, COMPATIBILITY, MATCH): COMPATIBILITY_VERIFIED,
        (INTEGRITY_VERIFIED, COMPATIBILITY, MISMATCH): (
            REBUILD_REQUIRED_ATTEMPT_TERMINAL
        ),
        (COMPATIBILITY_VERIFIED, CACHE_PROOF, MATCH): (
            INFEASIBLE_QUERY_ATTEMPT_TERMINAL
        ),
        (COMPATIBILITY_VERIFIED, CACHE_PROOF, MISS): CACHE_CHECKED,
        (CACHE_CHECKED, ABSTRACT_AUDIT, PASS): ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL,
        (CACHE_CHECKED, ABSTRACT_AUDIT, FAIL): ABSTRACT_FAILED,
        (ABSTRACT_FAILED, CAUSAL_SEARCH, FOUND): ROUTE_ESTIMATION_REQUIRED,
        (ABSTRACT_FAILED, CAUSAL_SEARCH, CAP_EXHAUSTED): ROUTE_ESTIMATION_REQUIRED,
        (ABSTRACT_FAILED, CAUSAL_SEARCH, NO_SOUND_COVER): ROUTE_ESTIMATION_REQUIRED,
        (ABSTRACT_FAILED, CAUSAL_SEARCH, LOCAL_CAP_IMPOSSIBLE): (
            ROUTE_ESTIMATION_REQUIRED
        ),
        (NEXT_LOCAL_TRANSACTION_REQUIRED, CAUSAL_SEARCH, FOUND): (
            ROUTE_ESTIMATION_REQUIRED
        ),
        (NEXT_LOCAL_TRANSACTION_REQUIRED, CAUSAL_SEARCH, CAP_EXHAUSTED): (
            ROUTE_ESTIMATION_REQUIRED
        ),
        (NEXT_LOCAL_TRANSACTION_REQUIRED, CAUSAL_SEARCH, NO_SOUND_COVER): (
            ROUTE_ESTIMATION_REQUIRED
        ),
        (NEXT_LOCAL_TRANSACTION_REQUIRED, CAUSAL_SEARCH, LOCAL_CAP_IMPOSSIBLE): (
            ROUTE_ESTIMATION_REQUIRED
        ),
        (ROUTE_ESTIMATION_REQUIRED, ROUTE_SELECTION, SELECT_LOCAL): (
            LOCAL_EXECUTION_REQUIRED
        ),
        (ROUTE_ESTIMATION_REQUIRED, ROUTE_SELECTION, SELECT_FALLBACK_NO_LOCAL): (
            FALLBACK_EXECUTION_REQUIRED
        ),
        (ROUTE_ESTIMATION_REQUIRED, ROUTE_SELECTION, SELECT_FALLBACK_DOMINATES): (
            FALLBACK_EXECUTION_REQUIRED
        ),
        (ROUTE_ESTIMATION_REQUIRED, ROUTE_SELECTION, SELECT_FALLBACK_EQUAL): (
            FALLBACK_EXECUTION_REQUIRED
        ),
        (
            ROUTE_ESTIMATION_REQUIRED,
            ROUTE_SELECTION,
            SELECT_FALLBACK_INCOMPARABLE,
        ): FALLBACK_EXECUTION_REQUIRED,
        (LOCAL_EXECUTION_REQUIRED, LOCAL_RESULT, CERTIFIED): (
            LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL
        ),
        (
            LOCAL_EXECUTION_REQUIRED,
            LOCAL_RESULT,
            FAILED_DEEPER_BUDGET_REMAINS,
        ): NEXT_LOCAL_TRANSACTION_REQUIRED,
        (
            LOCAL_EXECUTION_REQUIRED,
            LOCAL_RESULT,
            FAILED_DEEPER_BUDGET_EXHAUSTED,
        ): FALLBACK_EXECUTION_REQUIRED,
        (LOCAL_EXECUTION_REQUIRED, LOCAL_RESULT, FAILED_NO_SOUND_FRONTIER): (
            FALLBACK_EXECUTION_REQUIRED
        ),
        (FALLBACK_EXECUTION_REQUIRED, FALLBACK_RESULT, CERTIFIED_FEASIBLE): (
            FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL
        ),
        (FALLBACK_EXECUTION_REQUIRED, FALLBACK_RESULT, CERTIFIED_INFEASIBLE): (
            INFEASIBLE_QUERY_ATTEMPT_TERMINAL
        ),
        (FALLBACK_EXECUTION_REQUIRED, FALLBACK_RESULT, INCOMPLETE_DUE_TO_CAP): (
            FALLBACK_CAP_EXHAUSTED_ATTEMPT_TERMINAL
        ),
    }
    try:
        return table[key]
    except KeyError as error:
        raise AuditableRouterError(
            f"illegal route transition: state={state}, role={evidence.role}, "
            f"outcome={evidence.outcome}"
        ) from error


def _actual_within_bound(
    actual: ComparisonVector, bound: RouteUpperBoundCandidate
) -> None:
    if (
        actual.context_id != bound.context_id
        or actual.profile_id != bound.profile_id
        or actual.route_candidate != bound.route_candidate
    ):
        raise AuditableRouterError("actual comparison work and upper bound differ")
    actual_values = dict(actual.values)
    upper_values = dict(bound.vector.values)
    if set(actual_values) != set(upper_values):
        raise AuditableRouterError("actual comparison work uses different axes")
    exceeded = tuple(
        axis for axis in actual_values if actual_values[axis] > upper_values[axis]
    )
    if exceeded:
        raise AuditableRouterError(
            f"actual comparison work exceeds selected upper bound: {exceeded!r}"
        )


@dataclass(frozen=True, slots=True)
class RouteTraceEvent:
    context_id: str
    sequence: int
    state_before: str
    state_after: str
    evidence: TransitionEvidence
    prev_event_id: str | None

    def __post_init__(self) -> None:
        _identifier(self.context_id, field="event context_id")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int):
            raise AuditableRouterError("event sequence must be an integer")
        if self.sequence < 0:
            raise AuditableRouterError("event sequence must be nonnegative")
        _identifier(self.state_before, field="state_before")
        _identifier(self.state_after, field="state_after")
        if self.evidence.context_id != self.context_id:
            raise AuditableRouterError("event/evidence context mismatch")
        if self.prev_event_id is not None:
            _identifier(self.prev_event_id, field="prev_event_id")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.auditable_route_event.phase3e_candidate.v1",
            "context_id": self.context_id,
            "sequence": self.sequence,
            "state_before": self.state_before,
            "state_after": self.state_after,
            "evidence": self.evidence.to_dict(),
            "prev_event_id": self.prev_event_id,
            "official": False,
        }

    @property
    def event_id(self) -> str:
        return object_id(self._payload(), "auditable-route-event")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "event_id": self.event_id}


def _validate_selection(
    evidence: TransitionEvidence,
    bounds: Mapping[str, RouteUpperBoundCandidate],
) -> RouteUpperBoundCandidate:
    fallback = bounds.get(evidence.fallback_bound_id or "")
    if fallback is None or fallback.route_candidate != DIRECT_FALLBACK:
        raise AuditableRouterError("fallback upper bound is absent or invalid")
    if evidence.local_bound_id is None:
        if evidence.outcome != SELECT_FALLBACK_NO_LOCAL:
            raise AuditableRouterError("selection outcome omits a required local bound")
        return fallback
    local = bounds.get(evidence.local_bound_id)
    if local is None or local.route_candidate != LOCAL_ATTEMPT:
        raise AuditableRouterError("local upper bound is absent or invalid")
    relation = compare_route_upper_bounds(local, fallback)
    expected = {
        LEFT_DOMINATES: SELECT_LOCAL,
        RIGHT_DOMINATES: SELECT_FALLBACK_DOMINATES,
        EQUAL: SELECT_FALLBACK_EQUAL,
        INCOMPARABLE: SELECT_FALLBACK_INCOMPARABLE,
    }[relation]
    if evidence.outcome != expected:
        raise AuditableRouterError("route-selection outcome disagrees with exact comparison")
    return local if evidence.outcome == SELECT_LOCAL else fallback


def replay_route_events(
    *,
    context: RouteDecisionContext,
    events: Sequence[RouteTraceEvent],
    registry: CounterRegistry,
    bounds: Mapping[str, RouteUpperBoundCandidate],
    verified_artifact_ids: Iterable[str],
    require_terminal: bool,
) -> tuple[str, WorkVector]:
    if not events:
        raise AuditableRouterError("auditable route trace cannot be empty")
    if context.counter_registry_id != registry.registry_id:
        raise AuditableRouterError("route context uses a different counter registry")
    verified = set(verified_artifact_ids)
    state = START
    selected_bound: RouteUpperBoundCandidate | None = None
    for index, event in enumerate(events):
        if event.context_id != context.context_id:
            raise AuditableRouterError("route event binds a different context")
        if event.sequence != index:
            raise AuditableRouterError("route event sequence is not contiguous")
        expected_prev = events[index - 1].event_id if index else None
        if event.prev_event_id != expected_prev:
            raise AuditableRouterError("route event hash chain is broken")
        if event.state_before != state:
            raise AuditableRouterError("route event state_before disagrees with replay")
        if state in _TERMINAL_STATES:
            raise AuditableRouterError("route trace continues after a terminal state")
        try:
            registry.validate_vector(event.evidence.work_delta)
        except CounterValidationError as error:
            raise AuditableRouterError(str(error)) from error
        missing_refs = {
            artifact_id
            for _, artifact_id in event.evidence.artifact_refs
            if artifact_id not in verified
        }
        if missing_refs:
            raise AuditableRouterError(
                f"route evidence references unverified artifacts: {sorted(missing_refs)!r}"
            )
        if event.evidence.role == ROUTE_SELECTION:
            selected_bound = _validate_selection(event.evidence, bounds)
            if selected_bound.context_id != context.context_id:
                raise AuditableRouterError("selected upper bound uses a different context")
            if selected_bound.profile_id != context.comparison_profile_candidate_id:
                raise AuditableRouterError("selected upper bound uses a different profile")
        elif event.evidence.role in {LOCAL_RESULT, FALLBACK_RESULT}:
            if selected_bound is None:
                raise AuditableRouterError("execution result has no selected upper bound")
            expected_route = (
                LOCAL_ATTEMPT
                if event.evidence.role == LOCAL_RESULT
                else DIRECT_FALLBACK
            )
            if selected_bound.route_candidate != expected_route:
                raise AuditableRouterError("execution result does not match selected route")
            assert event.evidence.actual_comparison is not None
            _actual_within_bound(event.evidence.actual_comparison, selected_bound)
        next_state = _next_state(state, event.evidence)
        if event.state_after != next_state:
            raise AuditableRouterError("route event state_after disagrees with replay")
        state = next_state
        if state == NEXT_LOCAL_TRANSACTION_REQUIRED:
            selected_bound = None
        elif state == FALLBACK_EXECUTION_REQUIRED and event.evidence.role == LOCAL_RESULT:
            selected_bound = None
    if require_terminal and state not in _TERMINAL_STATES:
        raise AuditableRouterError("complete route envelope ends on a nonterminal prefix")
    return state, sum_work_vectors(
        (event.evidence.work_delta for event in events),
        subject_id=f"route-attempt:{context.route_attempt_id}",
    )


def append_route_event(
    *,
    context: RouteDecisionContext,
    events: Sequence[RouteTraceEvent],
    evidence: TransitionEvidence,
    registry: CounterRegistry,
    bounds: Mapping[str, RouteUpperBoundCandidate],
    verified_artifact_ids: Iterable[str],
) -> RouteTraceEvent:
    if events:
        state, _ = replay_route_events(
            context=context,
            events=events,
            registry=registry,
            bounds=bounds,
            verified_artifact_ids=verified_artifact_ids,
            require_terminal=False,
        )
        if state in _TERMINAL_STATES:
            raise AuditableRouterError("cannot append after terminal state")
        prev_event_id = events[-1].event_id
    else:
        state = START
        prev_event_id = None
    state_after = _next_state(state, evidence)
    event = RouteTraceEvent(
        context.context_id,
        len(events),
        state,
        state_after,
        evidence,
        prev_event_id,
    )
    replay_route_events(
        context=context,
        events=tuple(events) + (event,),
        registry=registry,
        bounds=bounds,
        verified_artifact_ids=verified_artifact_ids,
        require_terminal=False,
    )
    return event


@dataclass(frozen=True, slots=True)
class RouteTraceEnvelope:
    context_id: str
    events: tuple[RouteTraceEvent, ...]
    final_state: str
    accumulated_work: WorkVector
    complete: bool
    campaign_retry_policy: None = None
    official: bool = False

    def __post_init__(self) -> None:
        _identifier(self.context_id, field="envelope context_id")
        if not self.events:
            raise AuditableRouterError("route envelope cannot be empty")
        _identifier(self.final_state, field="envelope final_state")
        if not isinstance(self.complete, bool):
            raise AuditableRouterError("route envelope complete flag must be boolean")
        if self.campaign_retry_policy is not None:
            raise AuditableRouterError("campaign retry policy remains unresolved")
        if self.official:
            raise AuditableRouterError("preconstruction route envelope cannot be official")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_trace_envelope.phase3e_candidate.v1",
            "context_id": self.context_id,
            "event_count": len(self.events),
            "head_event_id": self.events[0].event_id,
            "tail_event_id": self.events[-1].event_id,
            "events": [event.to_dict() for event in self.events],
            "final_state": self.final_state,
            "accumulated_work": self.accumulated_work.to_dict(),
            "complete": self.complete,
            "campaign_retry_policy": None,
            "official": False,
            "routing_protocol_status": ROUTING_MECHANICS_ONLY,
            "economics_gate_status": ECONOMICS_NOT_RUN,
        }

    @property
    def envelope_id(self) -> str:
        return object_id(self._payload(), "route-trace-envelope")

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "envelope_id": self.envelope_id}


def build_route_envelope(
    *,
    context: RouteDecisionContext,
    events: Sequence[RouteTraceEvent],
    registry: CounterRegistry,
    bounds: Mapping[str, RouteUpperBoundCandidate],
    verified_artifact_ids: Iterable[str],
    complete: bool,
) -> RouteTraceEnvelope:
    state, accumulated = replay_route_events(
        context=context,
        events=events,
        registry=registry,
        bounds=bounds,
        verified_artifact_ids=verified_artifact_ids,
        require_terminal=complete,
    )
    return RouteTraceEnvelope(
        context.context_id,
        tuple(events),
        state,
        accumulated,
        complete,
    )


def verify_route_envelope(
    *,
    envelope: RouteTraceEnvelope,
    context: RouteDecisionContext,
    registry: CounterRegistry,
    bounds: Mapping[str, RouteUpperBoundCandidate],
    verified_artifact_ids: Iterable[str],
) -> None:
    if envelope.context_id != context.context_id:
        raise AuditableRouterError("route envelope binds a different context")
    state, accumulated = replay_route_events(
        context=context,
        events=envelope.events,
        registry=registry,
        bounds=bounds,
        verified_artifact_ids=verified_artifact_ids,
        require_terminal=envelope.complete,
    )
    if state != envelope.final_state:
        raise AuditableRouterError("route envelope final state mismatch")
    if accumulated != envelope.accumulated_work:
        raise AuditableRouterError("route envelope accumulated WorkVector mismatch")
    if envelope.complete is not True:
        raise AuditableRouterError("incomplete route prefix is not a route certificate")
    expected = RouteTraceEnvelope(
        envelope.context_id,
        envelope.events,
        state,
        accumulated,
        True,
    )
    if envelope.envelope_id != expected.envelope_id:
        raise AuditableRouterError("route envelope content ID mismatch")


__all__ = [
    "ABSTRACT_AUDIT",
    "ABSTRACT_CERTIFIED_ATTEMPT_TERMINAL",
    "ABSTRACT_FAILED",
    "AuditableRouterError",
    "CACHE_PROOF",
    "CAP_EXHAUSTED",
    "CAUSAL_SEARCH",
    "CERTIFIED",
    "CERTIFIED_FEASIBLE",
    "CERTIFIED_INFEASIBLE",
    "COMPATIBILITY",
    "FAIL",
    "FAILED_DEEPER_BUDGET_EXHAUSTED",
    "FAILED_DEEPER_BUDGET_REMAINS",
    "FAILED_NO_SOUND_FRONTIER",
    "FALLBACK_CAP_EXHAUSTED_ATTEMPT_TERMINAL",
    "FALLBACK_EXECUTION_REQUIRED",
    "FALLBACK_RESULT",
    "FOUND",
    "FULL_GROUND_FALLBACK_ATTEMPT_TERMINAL",
    "INCOMPLETE_DUE_TO_CAP",
    "INFEASIBLE_QUERY_ATTEMPT_TERMINAL",
    "INTEGRITY",
    "LOCAL_CAP_IMPOSSIBLE",
    "LOCAL_EXECUTION_REQUIRED",
    "LOCAL_GROUND_RECOVERY_ATTEMPT_TERMINAL",
    "LOCAL_RESULT",
    "MATCH",
    "MISMATCH",
    "MISS",
    "NEXT_LOCAL_TRANSACTION_REQUIRED",
    "NO_SOUND_COVER",
    "PASS",
    "PROTOCOL_FAILURE_ATTEMPT_TERMINAL",
    "REBUILD_REQUIRED_ATTEMPT_TERMINAL",
    "ROUTE_SELECTION",
    "RouteDecisionContext",
    "RouteTraceEnvelope",
    "RouteTraceEvent",
    "SELECT_FALLBACK_DOMINATES",
    "SELECT_FALLBACK_EQUAL",
    "SELECT_FALLBACK_INCOMPARABLE",
    "SELECT_FALLBACK_NO_LOCAL",
    "SELECT_LOCAL",
    "START",
    "TransitionEvidence",
    "append_route_event",
    "build_route_envelope",
    "evidence_work_subject",
    "make_route_selection_evidence",
    "replay_route_events",
    "verify_route_envelope",
]
