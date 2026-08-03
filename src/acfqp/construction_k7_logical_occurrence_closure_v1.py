"""Construction-only K7 logical-occurrence closure successor.

This module closes exactly one registered K7 logical occurrence after the
production complete-bundle verifier has independently replayed the full
semantic, accounting, source-cap, and attempt-terminal chain.  It is a
non-retroactive successor: neither :mod:`acfqp.campaign_v1` nor the historical
semantic-verification authority is widened.

The only accepted case is the current initial route attempt under the
canonical non-retryable ``RebuildPolicyV1``.  Its complete 202-record
``WorkVector`` is retained as one occurrence component, without rewriting,
coalescing, or silently dropping provenance.  The resulting occurrence is a
covered denominator entry but is *not* certificate-covered.

This construction does not issue a campaign closure, unlock either official
Gate, or define scalar economics.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import (
    SHARED_AXES,
    ComparisonVectorV1,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp import campaign_v1
from acfqp import (
    construction_k7_production_complete_bundle_independent_verifier_v1
    as complete_verifier_v1,
)
from acfqp import v075_k7_root_cap_accounted_sealed_ipc_v1 as route_ipc_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_LOGICAL_OCCURRENCE_CLOSURE_AUTHORITY_V1_DOMAIN,
    CONSTRUCTION_K7_LOGICAL_OCCURRENCE_CLOSURE_BUNDLE_V1_DOMAIN,
    CONSTRUCTION_K7_LOGICAL_OCCURRENCE_CLOSURE_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_LOGICAL_OCCURRENCE_WORK_SUM_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.32"
PROFILE_KEY = "construction_k7_logical_occurrence_closure_v1"

EXPECTED_COUNTER_RECORD_COUNT = 202
EXPECTED_ROUTE_ATTEMPT_COUNT = 1
EXPECTED_REBUILD_COUNT = 0

SOURCE_TERMINAL_SCOPE = "ROUTE_ATTEMPT"
TERMINAL_SCOPE = "LOGICAL_OCCURRENCE"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = "ATTEMPT_BUDGET_EXHAUSTED"
SOURCE_CAUSE = "CHILD_ACTION_ROW_CAP_EXCEEDED"

WORKLOAD_ECONOMICS_GATE_NOT_RUN = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
COUNTER_COMPLETENESS_GATE_NOT_RUN = "COUNTER_COMPLETENESS_GATE_NOT_RUN"

K7_OCCURRENCE_WORK_SUM_V1_DOMAIN = (
    CONSTRUCTION_K7_LOGICAL_OCCURRENCE_WORK_SUM_V1_DOMAIN
)
K7_LOGICAL_OCCURRENCE_CLOSURE_AUTHORITY_V1_DOMAIN = (
    CONSTRUCTION_K7_LOGICAL_OCCURRENCE_CLOSURE_AUTHORITY_V1_DOMAIN
)
K7_LOGICAL_OCCURRENCE_CLOSURE_BUNDLE_V1_DOMAIN = (
    CONSTRUCTION_K7_LOGICAL_OCCURRENCE_CLOSURE_BUNDLE_V1_DOMAIN
)
K7_LOGICAL_OCCURRENCE_CLOSURE_VERIFICATION_V1_DOMAIN = (
    CONSTRUCTION_K7_LOGICAL_OCCURRENCE_CLOSURE_VERIFICATION_V1_DOMAIN
)

LOCAL_DOMAINS = frozenset(
    {
        K7_OCCURRENCE_WORK_SUM_V1_DOMAIN,
        K7_LOGICAL_OCCURRENCE_CLOSURE_AUTHORITY_V1_DOMAIN,
        K7_LOGICAL_OCCURRENCE_CLOSURE_BUNDLE_V1_DOMAIN,
        K7_LOGICAL_OCCURRENCE_CLOSURE_VERIFICATION_V1_DOMAIN,
    }
)
if len(LOCAL_DOMAINS) != 4:  # pragma: no cover
    raise RuntimeError("K7 occurrence-closure domains must be unique")
if not LOCAL_DOMAINS.issubset(PHASE3E_DOMAIN_TAGS):  # pragma: no cover
    raise RuntimeError("K7 occurrence-closure domains must be centrally registered")

_WORK_SUM_ISSUER = object()
_CLOSURE_ISSUER = object()
_BUNDLE_ISSUER = object()
_VERIFICATION_ISSUER = object()


class ConstructionK7LogicalOccurrenceClosureV1Error(ValueError):
    """The complete work, route identity, policy, or closure did not replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LogicalOccurrenceClosureV1Error(message)


def _local_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAINS:
        _fail("occurrence closure used an unknown local domain")
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7LogicalOccurrenceClosureV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _canonical_object(raw: Any, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} bytes are missing")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7LogicalOccurrenceClosureV1Error(
            f"{label} bytes are noncanonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} bytes are noncanonical")
    return document


def _canonical_disabled_rebuild_policy(
    policy: campaign_v1.RebuildPolicyV1,
) -> campaign_v1.RebuildPolicyV1:
    expected = campaign_v1.RebuildPolicyV1()
    if (
        type(policy) is not campaign_v1.RebuildPolicyV1
        or policy.to_dict() != expected.to_dict()
        or policy.rebuild_allowed is not False
        or policy.max_rebuild_attempts != 0
        or policy.can_retry(route_attempt_count=1, rebuild_count=0)
    ):
        _fail("K7 root-cap occurrence requires the canonical non-retryable policy")
    return expected


def _route_from_replay_inputs(
    closure_replay_inputs: Mapping[str, Any],
) -> route_ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1:
    if type(closure_replay_inputs) is not dict:
        _fail("closure replay inputs must be one exact mapping")
    roots = closure_replay_inputs.get("replay_roots")
    if type(roots) is not dict:
        _fail("closure replay inputs lack full replay roots")
    request_replay = roots.get("request_replay")
    route = getattr(getattr(request_replay, "request", None), "route_identity", None)
    if type(route) is not route_ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1:
        _fail("closure replay inputs lack the exact request route identity")
    # This re-runs the route object's complete internal identity graph check.
    route.to_document()
    return route


def _terminal_document_join(
    *,
    verification: complete_verifier_v1.K7ProductionCompleteBundleVerificationV1,
    terminal_accounting_bundle_raw: bytes,
    route: route_ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1,
    policy: campaign_v1.RebuildPolicyV1,
) -> dict[str, Any]:
    if type(verification) is not (
        complete_verifier_v1.K7ProductionCompleteBundleVerificationV1
    ):
        _fail("logical occurrence closure requires the independent verifier authority")
    if type(route) is not (
        route_ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1
    ):
        _fail("logical occurrence closure requires the exact request route identity")
    # Re-evaluate the frozen verification identity before consuming its typed
    # work/comparison views.
    verification.verification_id
    document = _canonical_object(
        terminal_accounting_bundle_raw,
        "terminal accounting bundle",
    )
    if (
        hashlib.sha256(terminal_accounting_bundle_raw).hexdigest()
        != verification.terminal_bundle_sha256
        or len(terminal_accounting_bundle_raw)
        != verification.terminal_bundle_byte_count
        or document.get("root_cap_terminal_accounting_bundle_id")
        != verification.terminal_accounting_bundle_id
    ):
        _fail("terminal bytes do not match the independently verified bundle")

    formal = document.get("formal_accounting_materialization_bundle")
    cap = document.get("root_cap_exhaustion_evidence")
    terminal = document.get("attempt_budget_terminal_authority")
    if not all(type(value) is dict for value in (formal, cap, terminal)):
        _fail("terminal bundle omitted complete formal, cap, or terminal evidence")
    assert isinstance(formal, dict)
    assert isinstance(cap, dict)
    assert isinstance(terminal, dict)

    work = verification.verified_work_vector
    comparison = verification.verified_comparison_vector
    attestation = verification.attestation
    logical = route.logical_occurrence
    attempt = route.route_attempt
    context = route.route_context
    decision = route.decision_point
    transaction = route.transaction
    counter_ids = tuple(row.record_id for row in work.records)
    if (
        route.logical_occurrence.rebuild_policy_id != policy.rebuild_policy_id
        or cap.get("rebuild_policy_id") != policy.rebuild_policy_id
        or attempt.route_attempt_index != 1
        or attempt.logical_occurrence_id != logical.logical_occurrence_id
        or attempt.build_epoch_id != logical.initial_build_epoch_id
        or logical.logical_occurrence_id != attestation.logical_occurrence_id
        or attempt.route_attempt_id != attestation.route_attempt_id
        or context.route_decision_context_id
        != attestation.route_decision_context_id
        or decision.decision_point_id != attestation.decision_point_id
        or transaction.transaction_id != attestation.transaction_id
        or logical.structural_id != attestation.structural_id
        or logical.query_id != attestation.query_id
        or logical.selected_plan_id != attestation.selected_plan_id
        or logical.threshold_profile_id != attestation.threshold_profile_id
        or attempt.build_epoch_id != attestation.build_epoch_id
        or document.get("terminal_scope") != SOURCE_TERMINAL_SCOPE
        or document.get("terminal_class") != TERMINAL_CLASS
        or document.get("terminal_code") != TERMINAL_CODE
        or document.get("specific_cause") != SOURCE_CAUSE
        or document.get("terminal_is_infeasibility_certificate") is not False
        or document.get("plan_certificate") is not False
        or document.get("infeasibility_certificate") is not False
        or document.get("logical_occurrence_closed") is not False
        or formal.get("formal_accounting_materialization_bundle_id")
        != verification.formal_materialization_bundle_id
        or formal.get("work_vector") != work.to_dict()
        or formal.get("comparison_vector") != comparison.to_dict()
        or formal.get("counter_record_ids") != list(counter_ids)
        or formal.get("actual_projection_proof", {}).get(
            "formal_actual_projection_proof_id"
        )
        != verification.formal_actual_projection_proof_id
        or cap.get("root_cap_exhaustion_evidence_id")
        != verification.root_cap_exhaustion_evidence_id
        or cap.get("logical_occurrence_id") != logical.logical_occurrence_id
        or cap.get("route_attempt_id") != attempt.route_attempt_id
        or cap.get("decision_point_id") != decision.decision_point_id
        or cap.get("transaction_id") != transaction.transaction_id
        or cap.get("rebuild_allowed") is not False
        or terminal.get("attempt_budget_terminal_authority_id")
        != verification.attempt_budget_terminal_authority_id
        or terminal.get("logical_occurrence_id") != logical.logical_occurrence_id
        or terminal.get("route_attempt_id") != attempt.route_attempt_id
        or terminal.get("actual_work_vector_id") != work.work_vector_id
        or terminal.get("actual_comparison_vector_id")
        != comparison.comparison_vector_id
        or terminal.get("counter_record_ids") != list(counter_ids)
        or (
            terminal.get("route_attempt_count"),
            terminal.get("route_success_count"),
            terminal.get("route_failure_count"),
        )
        != (1, 0, 1)
        or terminal.get("terminal_class") != TERMINAL_CLASS
        or terminal.get("terminal_code") != TERMINAL_CODE
        or terminal.get("terminal_is_infeasibility_certificate") is not False
        or terminal.get("logical_occurrence_closed") is not False
        or len(counter_ids) != EXPECTED_COUNTER_RECORD_COUNT
        or counter_ids != verification.counter_record_ids
        or work.subject_id != logical.logical_occurrence_id
        or work.route_kind is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
        or comparison.subject_id != logical.logical_occurrence_id
        or comparison.route_kind is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
        or comparison.work_vector_id != work.work_vector_id
        or (
            work.values.get("route.attempts"),
            work.values.get("route.successes"),
            work.values.get("route.failures"),
        )
        != (1, 0, 1)
    ):
        _fail("verified terminal, complete work, route, or policy identities crossed")
    return document


@dataclass(frozen=True, slots=True)
class K7OccurrenceWorkSumV1:
    """One-component, reducer-exact occurrence total retaining all provenance."""

    _issuer: InitVar[object]
    production_complete_bundle_verification_id: str
    terminal_accounting_bundle_id: str
    logical_occurrence_id: str
    route_identity_id: str
    route_decision_context_id: str
    route_attempt_id: str
    decision_point_id: str
    transaction_id: str
    counter_registry_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    formal_actual_projection_proof_id: str
    work_vector: WorkVectorV1 = field(repr=False, compare=False)
    comparison_vector: ComparisonVectorV1 = field(repr=False, compare=False)
    counter_record_ids: tuple[str, ...]
    evaluation_verification_work_counter_record_id: str
    aggregate_values: tuple[tuple[str, int], ...]
    _work_sum_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _WORK_SUM_ISSUER
            or type(self.work_vector) is not WorkVectorV1
            or type(self.comparison_vector) is not ComparisonVectorV1
        ):
            _fail("K7 occurrence work sum is caller-minted")
        for value, label in (
            (self.production_complete_bundle_verification_id, "complete verification"),
            (self.terminal_accounting_bundle_id, "terminal accounting bundle"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.route_identity_id, "route identity"),
            (self.route_decision_context_id, "route decision context"),
            (self.route_attempt_id, "route attempt"),
            (self.decision_point_id, "decision point"),
            (self.transaction_id, "transaction"),
            (self.counter_registry_id, "counter registry"),
            (self.comparison_profile_id, "comparison profile"),
            (self.actual_projection_profile_id, "actual projection profile"),
            (self.formal_actual_projection_proof_id, "projection proof"),
            *((value, "counter record") for value in self.counter_record_ids),
            (
                self.evaluation_verification_work_counter_record_id,
                "evaluation verification work",
            ),
        ):
            _cid(value, label)
        if (
            type(self.counter_record_ids) is not tuple
            or len(self.counter_record_ids) != EXPECTED_COUNTER_RECORD_COUNT
            or len(set(self.counter_record_ids)) != len(self.counter_record_ids)
            or tuple(row.record_id for row in self.work_vector.records)
            != self.counter_record_ids
            or self.work_vector.counter_registry_id != self.counter_registry_id
            or self.work_vector.subject_id != self.logical_occurrence_id
            or self.work_vector.route_kind is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
            or self.comparison_vector.comparison_profile_id
            != self.comparison_profile_id
            or self.comparison_vector.work_vector_id
            != self.work_vector.work_vector_id
            or self.comparison_vector.subject_id != self.logical_occurrence_id
            or self.comparison_vector.route_kind
            is not RouteKindEnum.ABSTRACT_FAILED_PREFIX
            or tuple(self.comparison_vector.values) != self.aggregate_values
            or tuple(axis for axis, _ in self.aggregate_values) != SHARED_AXES
        ):
            _fail("occurrence work sum dropped, rewrote, or crossed actual work")
        object.__setattr__(
            self,
            "_work_sum_id",
            _local_id(K7_OCCURRENCE_WORK_SUM_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_logical_occurrence_work_sum.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "production_complete_bundle_verification_id": (
                self.production_complete_bundle_verification_id
            ),
            "root_cap_terminal_accounting_bundle_id": (
                self.terminal_accounting_bundle_id
            ),
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_identity_id": self.route_identity_id,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "route_attempt_ids": [self.route_attempt_id],
            "decision_point_id": self.decision_point_id,
            "transaction_ids": [self.transaction_id],
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "formal_actual_projection_proof_id": (
                self.formal_actual_projection_proof_id
            ),
            "attempt_work_vector_ids": [self.work_vector.work_vector_id],
            "attempt_comparison_vector_ids": [
                self.comparison_vector.comparison_vector_id
            ],
            "rebuild_event_ids": [],
            "rebuild_work_vector_ids": [],
            "counter_record_count": len(self.counter_record_ids),
            "counter_record_ids": list(self.counter_record_ids),
            "aggregate_values": [
                {"axis": axis, "value": value}
                for axis, value in self.aggregate_values
            ],
            "component_count": 1,
            "attempt_work_component_count": 1,
            "rebuild_work_component_count": 0,
            "all_202_counter_records_preserved": True,
            "counter_record_order_preserved": True,
            "counter_record_provenance_preserved": True,
            "counter_values_rewritten": False,
            "work_components_coalesced": False,
            "unreferenced_operational_work_allowed": False,
            "single_component_reducer_exact": True,
            "evaluation_verification_work_counter_record_id": (
                self.evaluation_verification_work_counter_record_id
            ),
            "evaluation_work_excluded_from_operational_sum": True,
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def occurrence_work_sum_id(self) -> str:
        expected = _local_id(K7_OCCURRENCE_WORK_SUM_V1_DOMAIN, self._payload())
        if expected != self._work_sum_id:
            _fail("K7 occurrence work sum changed after issuance")
        return self._work_sum_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "logical_occurrence_work_sum_id": self.occurrence_work_sum_id,
        }


@dataclass(frozen=True, slots=True)
class K7LogicalOccurrenceClosureV1:
    """Typed final closure for one non-retryable, noncertificate occurrence."""

    _issuer: InitVar[object]
    complete_verification_id: str
    complete_verification_attestation_id: str
    terminal_accounting_bundle_id: str
    attempt_terminal_authority_id: str
    logical_occurrence_id: str
    rebuild_policy_id: str
    route_identity_id: str
    route_attempt_id: str
    build_epoch_id: str
    occurrence_work_sum_id: str
    work_vector_id: str
    comparison_vector_id: str
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CLOSURE_ISSUER:
            _fail("K7 logical occurrence closure is caller-minted")
        for value, label in (
            (self.complete_verification_id, "complete verification"),
            (
                self.complete_verification_attestation_id,
                "complete verification attestation",
            ),
            (self.terminal_accounting_bundle_id, "terminal accounting bundle"),
            (self.attempt_terminal_authority_id, "attempt terminal authority"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.rebuild_policy_id, "rebuild policy"),
            (self.route_identity_id, "route identity"),
            (self.route_attempt_id, "route attempt"),
            (self.build_epoch_id, "BuildEpoch"),
            (self.occurrence_work_sum_id, "occurrence work sum"),
            (self.work_vector_id, "work vector"),
            (self.comparison_vector_id, "comparison vector"),
        ):
            _cid(value, label)
        object.__setattr__(
            self,
            "_closure_id",
            _local_id(
                K7_LOGICAL_OCCURRENCE_CLOSURE_AUTHORITY_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_logical_occurrence_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "source_terminal_scope": SOURCE_TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "specific_cause": SOURCE_CAUSE,
            "production_complete_bundle_verification_id": (
                self.complete_verification_id
            ),
            "production_complete_bundle_verification_attestation_id": (
                self.complete_verification_attestation_id
            ),
            "root_cap_terminal_accounting_bundle_id": (
                self.terminal_accounting_bundle_id
            ),
            "attempt_budget_terminal_authority_id": (
                self.attempt_terminal_authority_id
            ),
            "logical_occurrence_id": self.logical_occurrence_id,
            "rebuild_policy_id": self.rebuild_policy_id,
            "route_identity_id": self.route_identity_id,
            "route_attempts": [
                {
                    "route_attempt_index": 1,
                    "route_attempt_id": self.route_attempt_id,
                    "BuildEpoch_id": self.build_epoch_id,
                    "terminal_class": TERMINAL_CLASS,
                    "terminal_code": TERMINAL_CODE,
                    "terminal_actual_work_vector_id": self.work_vector_id,
                    "terminal_actual_comparison_vector_id": (
                        self.comparison_vector_id
                    ),
                }
            ],
            "rebuild_event_ids": [],
            "rebuild_work_vector_ids": [],
            "logical_occurrence_work_sum_id": self.occurrence_work_sum_id,
            "logical_occurrence_count": 1,
            "route_attempt_count": EXPECTED_ROUTE_ATTEMPT_COUNT,
            "route_success_count": 0,
            "route_failure_count": 1,
            "rebuild_count": EXPECTED_REBUILD_COUNT,
            "plan_certificate_count": 0,
            "infeasibility_certificate_count": 0,
            "noncertificate_count": 1,
            "closure_denominator_included": True,
            "certification_denominator_included": True,
            "economics_denominator_included": True,
            "closure_denominator_count": 1,
            "certification_coverage_denominator_count": 1,
            "economics_cost_denominator_count": 1,
            "certificate_covered": False,
            "rebuild_allowed": False,
            "retry_possible": False,
            "logical_occurrence_closed": True,
            "terminal_is_infeasibility_certificate": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "hidden_or_unreferenced_work_accepted": False,
            "campaign_closure_issued": False,
            "official_execution_allowed": False,
            "counter_completeness_gate": COUNTER_COMPLETENESS_GATE_NOT_RUN,
            "workload_economics_gate": WORKLOAD_ECONOMICS_GATE_NOT_RUN,
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def closure_id(self) -> str:
        expected = _local_id(
            K7_LOGICAL_OCCURRENCE_CLOSURE_AUTHORITY_V1_DOMAIN,
            self._payload(),
        )
        if expected != self._closure_id:
            _fail("K7 logical occurrence closure changed after issuance")
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "logical_occurrence_closure_id": self.closure_id,
        }


@dataclass(frozen=True, slots=True)
class K7LogicalOccurrenceClosureBundleV1:
    """Portable exact-root bundle for the occurrence-level successor."""

    _issuer: InitVar[object]
    complete_verification: (
        complete_verifier_v1.K7ProductionCompleteBundleVerificationV1
    ) = field(repr=False, compare=False)
    terminal_accounting_document: Mapping[str, Any] = field(
        repr=False,
        compare=False,
    )
    route_identity: route_ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1 = (
        field(repr=False, compare=False)
    )
    rebuild_policy: campaign_v1.RebuildPolicyV1 = field(repr=False)
    occurrence_work_sum: K7OccurrenceWorkSumV1
    occurrence_closure: K7LogicalOccurrenceClosureV1
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BUNDLE_ISSUER
            or type(self.complete_verification) is not (
                complete_verifier_v1.K7ProductionCompleteBundleVerificationV1
            )
            or type(self.terminal_accounting_document) is not dict
            or type(self.route_identity)
            is not route_ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1
            or type(self.rebuild_policy) is not campaign_v1.RebuildPolicyV1
            or type(self.occurrence_work_sum) is not K7OccurrenceWorkSumV1
            or type(self.occurrence_closure) is not K7LogicalOccurrenceClosureV1
        ):
            _fail("K7 occurrence closure bundle is caller-minted")
        if (
            self.complete_verification.verification_id
            != self.occurrence_closure.complete_verification_id
            or self.complete_verification.terminal_accounting_bundle_id
            != self.occurrence_work_sum.terminal_accounting_bundle_id
            or self.terminal_accounting_document.get(
                "root_cap_terminal_accounting_bundle_id"
            )
            != self.complete_verification.terminal_accounting_bundle_id
            or self.route_identity.logical_occurrence.logical_occurrence_id
            != self.occurrence_closure.logical_occurrence_id
            or self.rebuild_policy.rebuild_policy_id
            != self.occurrence_closure.rebuild_policy_id
            or self.occurrence_work_sum.occurrence_work_sum_id
            != self.occurrence_closure.occurrence_work_sum_id
        ):
            _fail("K7 occurrence closure bundle identities crossed")
        object.__setattr__(
            self,
            "_bundle_id",
            _local_id(
                K7_LOGICAL_OCCURRENCE_CLOSURE_BUNDLE_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_logical_occurrence_closure_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "production_complete_bundle_verification": (
                self.complete_verification.to_document()
            ),
            "root_cap_terminal_accounting_bundle": dict(
                self.terminal_accounting_document
            ),
            "request_route_identity": self.route_identity.to_document(),
            "rebuild_policy": self.rebuild_policy.to_dict(),
            "logical_occurrence_work_sum": self.occurrence_work_sum.to_document(),
            "logical_occurrence_closure": self.occurrence_closure.to_document(),
            "complete_bundle_reverified_before_closure": True,
            "complete_terminal_bytes_embedded": True,
            "complete_route_identity_embedded": True,
            "complete_202_record_provenance_retained": True,
            "arbitrary_or_retryable_rebuild_policy_accepted": False,
            "attempt_transplant_accepted": False,
            "hidden_work_accepted": False,
            "cap_exhaustion_mapped_to_infeasibility": False,
            "denominator_deletion_accepted": False,
            "campaign_closure_issued": False,
            "official_execution_allowed": False,
            "counter_completeness_gate": COUNTER_COMPLETENESS_GATE_NOT_RUN,
            "workload_economics_gate": WORKLOAD_ECONOMICS_GATE_NOT_RUN,
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def bundle_id(self) -> str:
        expected = _local_id(
            K7_LOGICAL_OCCURRENCE_CLOSURE_BUNDLE_V1_DOMAIN,
            self._payload(),
        )
        if expected != self._bundle_id:
            _fail("K7 logical occurrence closure bundle changed after issuance")
        return self._bundle_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "logical_occurrence_closure_bundle_id": self.bundle_id,
        }


@dataclass(frozen=True, slots=True)
class K7LogicalOccurrenceClosureVerificationV1:
    """Fresh full-root verification result for a portable occurrence closure."""

    _issuer: InitVar[object]
    verified_bundle: K7LogicalOccurrenceClosureBundleV1 = field(
        repr=False,
        compare=False,
    )
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _VERIFICATION_ISSUER
            or type(self.verified_bundle) is not K7LogicalOccurrenceClosureBundleV1
        ):
            _fail("K7 logical occurrence closure verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _local_id(
                K7_LOGICAL_OCCURRENCE_CLOSURE_VERIFICATION_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        bundle = self.verified_bundle
        closure = bundle.occurrence_closure
        work_sum = bundle.occurrence_work_sum
        return {
            "schema": "acfqp.construction_k7_logical_occurrence_closure_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_closure_bundle_id": bundle.bundle_id,
            "logical_occurrence_closure_id": closure.closure_id,
            "logical_occurrence_work_sum_id": work_sum.occurrence_work_sum_id,
            "production_complete_bundle_verification_id": (
                bundle.complete_verification.verification_id
            ),
            "root_cap_terminal_accounting_bundle_id": (
                bundle.complete_verification.terminal_accounting_bundle_id
            ),
            "logical_occurrence_id": closure.logical_occurrence_id,
            "route_attempt_id": closure.route_attempt_id,
            "actual_work_vector_id": work_sum.work_vector.work_vector_id,
            "actual_comparison_vector_id": (
                work_sum.comparison_vector.comparison_vector_id
            ),
            "counter_record_count": len(work_sum.counter_record_ids),
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "route_attempt_count": 1,
            "rebuild_count": 0,
            "logical_occurrence_count": 1,
            "certificate_covered": False,
            "all_202_records_and_provenance_replayed": True,
            "nonretryable_policy_replayed": True,
            "attempt_identity_replayed": True,
            "three_denominators_replayed": True,
            "infeasibility_certificate": False,
            "campaign_closure_issued": False,
            "official_execution_allowed": False,
            "counter_completeness_gate": COUNTER_COMPLETENESS_GATE_NOT_RUN,
            "workload_economics_gate": WORKLOAD_ECONOMICS_GATE_NOT_RUN,
        }

    @property
    def verification_id(self) -> str:
        expected = _local_id(
            K7_LOGICAL_OCCURRENCE_CLOSURE_VERIFICATION_V1_DOMAIN,
            self._payload(),
        )
        if expected != self._verification_id:
            _fail("K7 logical occurrence closure verification changed")
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "logical_occurrence_closure_verification_id": self.verification_id,
        }


def issue_k7_logical_occurrence_closure_bundle_v1(
    *,
    complete_bundle_verification: (
        complete_verifier_v1.K7ProductionCompleteBundleVerificationV1
    ),
    terminal_accounting_bundle_raw: bytes,
    request_route_identity: (
        route_ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1
    ),
    rebuild_policy: campaign_v1.RebuildPolicyV1,
) -> K7LogicalOccurrenceClosureBundleV1:
    """Close one exact, non-retryable K7 occurrence from verified roots."""

    policy = _canonical_disabled_rebuild_policy(rebuild_policy)
    terminal_document = _terminal_document_join(
        verification=complete_bundle_verification,
        terminal_accounting_bundle_raw=terminal_accounting_bundle_raw,
        route=request_route_identity,
        policy=policy,
    )
    verification = complete_bundle_verification
    route = request_route_identity
    logical = route.logical_occurrence
    attempt = route.route_attempt
    work = verification.verified_work_vector
    comparison = verification.verified_comparison_vector
    work_sum = K7OccurrenceWorkSumV1(
        _WORK_SUM_ISSUER,
        verification.verification_id,
        verification.terminal_accounting_bundle_id,
        logical.logical_occurrence_id,
        route.route_identity_id,
        route.route_context.route_decision_context_id,
        attempt.route_attempt_id,
        route.decision_point.decision_point_id,
        route.transaction.transaction_id,
        work.counter_registry_id,
        comparison.comparison_profile_id,
        route.profile.actual_projection_profile_id,
        verification.formal_actual_projection_proof_id,
        work,
        comparison,
        verification.counter_record_ids,
        verification.verification_work_record.record_id,
        comparison.values,
    )
    closure = K7LogicalOccurrenceClosureV1(
        _CLOSURE_ISSUER,
        verification.verification_id,
        verification.attestation.attestation_id,
        verification.terminal_accounting_bundle_id,
        verification.attempt_budget_terminal_authority_id,
        logical.logical_occurrence_id,
        policy.rebuild_policy_id,
        route.route_identity_id,
        attempt.route_attempt_id,
        attempt.build_epoch_id,
        work_sum.occurrence_work_sum_id,
        work.work_vector_id,
        comparison.comparison_vector_id,
    )
    return K7LogicalOccurrenceClosureBundleV1(
        _BUNDLE_ISSUER,
        verification,
        terminal_document,
        route,
        policy,
        work_sum,
        closure,
    )


def verify_k7_logical_occurrence_closure_claim_bytes_v1(
    *,
    raw: bytes,
    complete_bundle_verification: (
        complete_verifier_v1.K7ProductionCompleteBundleVerificationV1
    ),
    terminal_accounting_bundle_raw: bytes,
    request_route_identity: (
        route_ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1
    ),
    rebuild_policy: campaign_v1.RebuildPolicyV1,
) -> K7LogicalOccurrenceClosureVerificationV1:
    """Verify closure bytes against an already independent typed authority.

    The complete verification object is not an ID-only shortcut: it can only
    be minted by the independent full-root verifier, and the exact terminal
    bytes must still match its digest, byte count, typed views, and artifact
    identities.  The full portable entrypoint below first recreates that
    authority from all roots, then delegates here.
    """

    claimed = _canonical_object(raw, "logical occurrence closure bundle")
    expected = issue_k7_logical_occurrence_closure_bundle_v1(
        complete_bundle_verification=complete_bundle_verification,
        terminal_accounting_bundle_raw=terminal_accounting_bundle_raw,
        request_route_identity=request_route_identity,
        rebuild_policy=rebuild_policy,
    )
    if claimed != expected.to_document():
        _fail("portable logical occurrence closure differs from verified roots")
    return K7LogicalOccurrenceClosureVerificationV1(
        _VERIFICATION_ISSUER,
        expected,
    )


def verify_k7_logical_occurrence_closure_bundle_bytes_v1(
    *,
    raw: bytes,
    complete_bundle_verification_raw: bytes,
    semantic_closure_raw: bytes,
    formal_materialization_raw: bytes,
    terminal_accounting_bundle_raw: bytes,
    closure_replay_inputs: Mapping[str, Any],
) -> K7LogicalOccurrenceClosureVerificationV1:
    """Freshly replay a portable occurrence closure from all production roots."""

    try:
        complete_verification = (
            complete_verifier_v1
            .verify_k7_production_complete_bundle_verification_bytes_v1(
                raw=complete_bundle_verification_raw,
                semantic_closure_raw=semantic_closure_raw,
                formal_materialization_raw=formal_materialization_raw,
                terminal_accounting_bundle_raw=terminal_accounting_bundle_raw,
                closure_replay_inputs=closure_replay_inputs,
            )
        )
    except Exception as error:
        raise ConstructionK7LogicalOccurrenceClosureV1Error(
            "production complete bundle failed independent replay"
        ) from error
    route = _route_from_replay_inputs(closure_replay_inputs)
    return verify_k7_logical_occurrence_closure_claim_bytes_v1(
        raw=raw,
        complete_bundle_verification=complete_verification,
        terminal_accounting_bundle_raw=terminal_accounting_bundle_raw,
        request_route_identity=route,
        rebuild_policy=campaign_v1.RebuildPolicyV1(),
    )


__all__ = (
    "COUNTER_COMPLETENESS_GATE_NOT_RUN",
    "ConstructionK7LogicalOccurrenceClosureV1Error",
    "EXPECTED_COUNTER_RECORD_COUNT",
    "K7_LOGICAL_OCCURRENCE_CLOSURE_AUTHORITY_V1_DOMAIN",
    "K7_LOGICAL_OCCURRENCE_CLOSURE_BUNDLE_V1_DOMAIN",
    "K7_LOGICAL_OCCURRENCE_CLOSURE_VERIFICATION_V1_DOMAIN",
    "K7_OCCURRENCE_WORK_SUM_V1_DOMAIN",
    "K7LogicalOccurrenceClosureBundleV1",
    "K7LogicalOccurrenceClosureV1",
    "K7LogicalOccurrenceClosureVerificationV1",
    "K7OccurrenceWorkSumV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SOURCE_CAUSE",
    "TERMINAL_CLASS",
    "TERMINAL_CODE",
    "TERMINAL_SCOPE",
    "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
    "issue_k7_logical_occurrence_closure_bundle_v1",
    "verify_k7_logical_occurrence_closure_bundle_bytes_v1",
    "verify_k7_logical_occurrence_closure_claim_bytes_v1",
)
