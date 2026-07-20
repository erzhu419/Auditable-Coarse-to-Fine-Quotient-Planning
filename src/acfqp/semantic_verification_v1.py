"""Fail-closed semantic verification core for the partial Phase-3E FQ7 profile.

Typed attestations are outputs of semantic replay, not substitutes for it.  The
core implemented here deliberately covers only authorities that already have a
replayable V1 implementation:

* native ``WorkVectorV1`` materialization against the official counter registry;
* exact actual-work projection from that native vector;
* safe-chain Phase-3D preselection causal/frontier replay and complete local
  cardinality projection without ground transitions;
* route-upper arithmetic/cap replay gated by an upstream cardinality authority;
* authority-gated marginal route selection;
* scoped Phase-3D safe-chain local-worker and sound-post-audit runtime replay
  without a second host solver run;
* trusted in-process ground-fallback result/work/outcome replay without a
  second host solver run;
* forbidden-access protocol replay; and
* terminal class/code validation against semantically replayed evidence.

The remaining FQ7 roles are registered so that their schema and outcome
vocabularies cannot drift, but they fail closed with ``NOT_IMPLEMENTED``.  In
particular, a well-formed attestation carrying a plausible result string is not
accepted as evidence for one of those roles.

``CARDINALITY_EVIDENCE`` is implemented only for two registered safe-chain
profiles: direct fallback and the Phase-3D local preselection projection.  Both
handlers reload the verified frozen Phase-3C parent bundle and recompute the
complete source/bound/evidence chain without ground transitions.  Generic
member lists remain non-authoritative: a source hash or an enumerated witness
cannot establish that it is a complete projection of the frozen RAPM/action
catalogue.

The ground-fallback authority is deliberately scoped to the V0 in-process
trusted executor.  It is not an isolated-worker attestation or portable proof.
This remains a partial verification profile and must not be used to claim the
full FQ7 or Phase-3E official gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from acfqp.accounting_v1 import (
    ComparisonVectorV1,
    CounterRecordV1,
    CounterRegistryV1,
    LaneEnum,
    NativeZeroAttestationV1,
    ReconciliationProofV1,
    SHARED_AXES,
    WorkVectorV1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualWorkScope,
    official_actual_projection_profile_v1,
    verify_actual_projection_v1,
)
from acfqp.access_protocol_v1 import (
    AccessEventLogV1,
    AccessOperation,
    AccessProtocolV1Error,
    AccessProtocolViolation,
    ForbiddenAccessViolationV1,
    PRESELECTION_READ_OPERATIONS,
    ProtocolSequenceProfileV1,
    RouteDecisionFreezeAttestationV1,
    local_execution_stages_v1,
    replay_access_protocol,
)
from acfqp.marginal_accounting_v1 import (
    AggregatedMarginalWorkV1,
    MarginalAccountingV1Error,
    verify_marginal_work_aggregate_v1,
)
from acfqp.native_recorder_v1 import RecordedWorkV1, verify_recorded_work_v1
from acfqp.phase3e_ids import (
    TYPED_VERIFICATION_ATTESTATION_DOMAIN,
    content_id,
    parse_content_id,
)
from acfqp.route_upper_formula_v1 import (
    RouteUpperDerivationProofV1,
    RouteUpperFormulaV1,
    official_route_upper_formula_v1,
    verify_route_upper_derivation_v1,
)
from acfqp.routing_v1 import (
    CardinalityEvidenceV1,
    CausalEvidenceV1,
    CausalOutcome,
    DecisionPointV1,
    FrontierSnapshotV1,
    MarginalRouteDecisionV1,
    RouteComparison,
    RouteDecisionContextV1,
    RouteCapProfileV1,
    RouteKind,
    RouteSelection,
    RouteUpperBoundEnvelopeV1,
    TerminalArtifactV1,
    TerminalClass,
    TerminalCode,
    TypedNotApplicable,
    TypedVerificationAttestationV1,
    TransactionV1,
    verify_unique_attestation_roles,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "phase3e_partial_semantic_verification_v1"


class SemanticVerificationV1Error(ValueError):
    """Semantic replay, evidence binding, or attestation validation failed."""


class SemanticVerifierNotImplementedError(SemanticVerificationV1Error):
    """A registered FQ7 role has no authoritative semantic replay yet."""

    outcome = "NOT_IMPLEMENTED"

    def __init__(self, role: str) -> None:
        super().__init__(
            f"semantic verifier for {role!r} is NOT_IMPLEMENTED in the partial FQ7 profile"
        )
        self.role = role


class SemanticRole(str, Enum):
    EXACT_CACHED_INFEASIBILITY = "EXACT_CACHED_INFEASIBILITY"
    ABSTRACT_AUDIT = "ABSTRACT_AUDIT"
    CAUSAL_SEARCH = "CAUSAL_SEARCH"
    CARDINALITY_EVIDENCE = "CARDINALITY_EVIDENCE"
    ROUTE_UPPER = "ROUTE_UPPER"
    ROUTE_DECISION = "ROUTE_DECISION"
    LOCAL_SOLVER_RESULT = "LOCAL_SOLVER_RESULT"
    POST_AUDIT = "POST_AUDIT"
    GROUND_FALLBACK = "GROUND_FALLBACK"
    WORK_VECTOR = "WORK_VECTOR"
    ACTUAL_PROJECTION = "ACTUAL_PROJECTION"
    TERMINAL_CLASSIFICATION = "TERMINAL_CLASSIFICATION"
    PROTOCOL_ACCESS = "PROTOCOL_ACCESS"


def _fixed_identity(namespace: str, label: str) -> str:
    """Return a stable, domain-separated identity for a verifier/profile name."""

    return hashlib.sha256(
        namespace.encode("utf-8") + b"\x00" + label.encode("utf-8")
    ).hexdigest()


VERIFICATION_PROFILE_ID = _fixed_identity(
    "acfqp:semantic-verification-profile-id:v1", PROFILE_KEY
)


@dataclass(frozen=True, slots=True)
class SemanticVerifierSpecV1:
    role: SemanticRole
    artifact_schema_id: str
    outcomes: frozenset[str]
    semantic_verifier_id: str
    verification_profile_id: str
    verification_counter_path: str
    implemented: bool


def _spec(
    role: SemanticRole,
    schema: str,
    outcomes: Sequence[str],
    *,
    implemented: bool,
    verification_counter_path: str = "common.protocol_checks",
) -> SemanticVerifierSpecV1:
    return SemanticVerifierSpecV1(
        role,
        schema,
        frozenset(outcomes),
        _fixed_identity("acfqp:semantic-verifier-id:v1", role.value),
        VERIFICATION_PROFILE_ID,
        verification_counter_path,
        implemented,
    )


_SPECS = (
    _spec(
        SemanticRole.EXACT_CACHED_INFEASIBILITY,
        "ExactCachedInfeasibilityProofV1",
        ("IDENTICAL_MATCH", "NO_MATCH", "INVALID"),
        implemented=False,
    ),
    _spec(
        SemanticRole.ABSTRACT_AUDIT,
        "AbstractPlanAuditV1",
        ("PASS", "FAIL", "INVALID"),
        implemented=False,
    ),
    _spec(
        SemanticRole.CAUSAL_SEARCH,
        "CausalEvidenceV1",
        (
            "FOUND",
            "CAP_EXHAUSTED",
            "NO_SOUND_COVER",
            "LOCAL_CAP_IMPOSSIBLE",
            "INVALID",
        ),
        # Scoped to the registered safe-chain Phase-3D preselection replay.
        # Other causal profiles remain fail closed in that handler.
        implemented=True,
    ),
    _spec(
        SemanticRole.CARDINALITY_EVIDENCE,
        "CardinalityEvidenceV1",
        ("VALID", "INVALID"),
        # V1 currently implements the registered safe-chain fallback and
        # Phase-3D local preselection extractors.  Other route/domain profiles
        # fail closed in their handlers instead of inheriting this capability.
        implemented=True,
    ),
    _spec(
        SemanticRole.ROUTE_UPPER,
        "RouteUpperBoundEnvelopeV1",
        ("VALID", "INVALID"),
        implemented=True,
    ),
    _spec(
        SemanticRole.ROUTE_DECISION,
        "RouteDecisionV1",
        ("LOCAL", "FALLBACK", "INVALID"),
        # The handler accepts only authority-bearing ROUTE_UPPER results.  A
        # LOCAL result additionally requires CAUSAL_SEARCH=FOUND authority.
        implemented=True,
    ),
    _spec(
        SemanticRole.LOCAL_SOLVER_RESULT,
        "LocalTransactionResultV1",
        (
            "CANDIDATE_FOUND",
            "SEARCH_CAP_EXHAUSTED",
            "NO_FEASIBLE_ASSIGNMENT",
            "INVALID",
        ),
        # Scoped to opaque runtime provenance minted by the existing isolated
        # Phase-3D safe-chain local executor.  Raw transport remains inert.
        implemented=True,
    ),
    _spec(
        SemanticRole.POST_AUDIT,
        "PostAuditCertificateV1",
        ("CERTIFIED", "FAILED", "INVALID"),
        # Scoped to the trusted sound Phase-3D safe-chain post-auditor and the
        # exact local-result authority it consumed.
        implemented=True,
    ),
    _spec(
        SemanticRole.GROUND_FALLBACK,
        "GroundFallbackResultV1",
        (
            "FEASIBLE_CERTIFIED",
            "INFEASIBLE_CERTIFIED",
            "CAP_EXHAUSTED",
            "INVALID",
        ),
        # This accepts only an opaque runtime seal minted by the selected-route
        # trusted executor.  Raw/serialized results still fail closed.
        implemented=True,
    ),
    _spec(
        SemanticRole.WORK_VECTOR,
        "WorkVectorV1",
        ("VALID", "INVALID"),
        implemented=True,
        verification_counter_path="common.integrity_checks",
    ),
    _spec(
        SemanticRole.ACTUAL_PROJECTION,
        "ComparisonVectorV1",
        ("VALID", "INVALID"),
        implemented=True,
    ),
    _spec(
        SemanticRole.TERMINAL_CLASSIFICATION,
        "TerminalArtifactV1",
        (
            TerminalClass.PLAN_CERTIFICATE.value,
            TerminalClass.INFEASIBILITY_CERTIFICATE.value,
            TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE.value,
            "INVALID",
        ),
        implemented=True,
    ),
    _spec(
        SemanticRole.PROTOCOL_ACCESS,
        "ForbiddenAccessViolationV1",
        ("PROTOCOL_FAILURE", "INVALID"),
        implemented=True,
    ),
)

SEMANTIC_VERIFIER_REGISTRY_V1: Mapping[
    SemanticRole, SemanticVerifierSpecV1
] = MappingProxyType({spec.role: spec for spec in _SPECS})


def _role(value: SemanticRole | str) -> SemanticRole:
    try:
        return SemanticRole(value)
    except (TypeError, ValueError) as error:
        raise SemanticVerificationV1Error(f"unknown FQ7 semantic role {value!r}") from error


def semantic_verifier_spec_v1(
    role: SemanticRole | str,
) -> SemanticVerifierSpecV1:
    return SEMANTIC_VERIFIER_REGISTRY_V1[_role(role)]


def require_implemented_role_v1(role: SemanticRole | str) -> SemanticVerifierSpecV1:
    spec = semantic_verifier_spec_v1(role)
    if not spec.implemented:
        raise SemanticVerifierNotImplementedError(spec.role.value)
    return spec


ContentRef = str | TypedNotApplicable


def _content_ref(value: ContentRef, field: str) -> ContentRef:
    if isinstance(value, TypedNotApplicable):
        # Round-trip through the strict loader so a subclass cannot bypass the
        # typed-null field contract.
        return TypedNotApplicable.from_dict(value.to_dict())
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise SemanticVerificationV1Error(
            f"{field} must be a full Phase-3E content ID or typed NOT_APPLICABLE"
        ) from error


def _same_ref(left: ContentRef, right: ContentRef) -> bool:
    if isinstance(left, TypedNotApplicable) or isinstance(right, TypedNotApplicable):
        # Applicability is the identity-bearing fact.  Human-readable reasons
        # can legitimately differ between a terminal and its attestation.
        return isinstance(left, TypedNotApplicable) and isinstance(
            right, TypedNotApplicable
        )
    return left == right


def _load_context(value: RouteDecisionContextV1 | Mapping[str, Any]) -> RouteDecisionContextV1:
    document = value.to_dict() if isinstance(value, RouteDecisionContextV1) else value
    try:
        return RouteDecisionContextV1.from_dict(document)
    except ValueError as error:
        raise SemanticVerificationV1Error(
            f"invalid RouteDecisionContextV1: {error}"
        ) from error


@dataclass(frozen=True, slots=True)
class AttestationContextV1:
    """All query/attempt identity copied into a typed attestation."""

    route_context: RouteDecisionContextV1
    decision_point_id: ContentRef
    transaction_id: ContentRef
    verified_at_protocol_step: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "route_context", _load_context(self.route_context))
        object.__setattr__(
            self,
            "decision_point_id",
            _content_ref(self.decision_point_id, "decision_point_id"),
        )
        object.__setattr__(
            self,
            "transaction_id",
            _content_ref(self.transaction_id, "transaction_id"),
        )
        if (
            isinstance(self.decision_point_id, TypedNotApplicable)
            and not isinstance(self.transaction_id, TypedNotApplicable)
        ):
            raise SemanticVerificationV1Error(
                "an applicable transaction requires an applicable decision point"
            )
        if (
            type(self.verified_at_protocol_step) is not int
            or self.verified_at_protocol_step < 0
        ):
            raise SemanticVerificationV1Error(
                "verified_at_protocol_step must be a nonnegative exact integer"
            )


def _official_registry(
    registry: CounterRegistryV1 | None = None,
) -> CounterRegistryV1:
    expected = official_counter_registry_v1()
    selected = expected if registry is None else registry
    try:
        selected.validate_official_catalogue()
    except ValueError as error:
        raise SemanticVerificationV1Error(
            f"semantic replay requires the official CounterRegistryV1: {error}"
        ) from error
    if selected.registry_id != expected.registry_id:
        raise SemanticVerificationV1Error("counter registry identity drift")
    return selected


def _verification_work_record(
    value: CounterRecordV1 | Mapping[str, Any],
    spec: SemanticVerifierSpecV1,
    registry: CounterRegistryV1,
) -> CounterRecordV1:
    document = value.to_dict() if isinstance(value, CounterRecordV1) else value
    try:
        record = CounterRecordV1.from_dict(document)
        leaf = registry.by_path[record.path]
        record.verify_against(leaf)
    except (KeyError, ValueError) as error:
        raise SemanticVerificationV1Error(
            f"invalid semantic-verification work CounterRecordV1: {error}"
        ) from error
    if record.counter_registry_id != registry.registry_id:
        raise SemanticVerificationV1Error(
            "verification work uses a non-official counter registry"
        )
    if leaf.lane is not LaneEnum.OPERATIONAL:
        raise SemanticVerificationV1Error(
            "semantic-verification work must be in the operational lane"
        )
    if record.path != spec.verification_counter_path:
        raise SemanticVerificationV1Error(
            f"{spec.role.value} verification work must use "
            f"{spec.verification_counter_path!r}"
        )
    if record.value < 1:
        raise SemanticVerificationV1Error(
            "semantic verification must record at least one operational check"
        )
    return record


_VERIFIED_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class SemanticVerificationResultV1:
    """Non-serializable result handle emitted only after semantic replay."""

    artifact: object
    attestation: TypedVerificationAttestationV1
    verification_work_record: CounterRecordV1
    recomputed_evidence_ids: tuple[str, ...]
    binding: AttestationContextV1
    _authority: object

    def __post_init__(self) -> None:
        if self._authority is not _VERIFIED_AUTHORITY:
            raise SemanticVerificationV1Error(
                "semantic verification result was not emitted by an authoritative handler"
            )
        if self.attestation.verification_work_counter_record_id != (
            self.verification_work_record.record_id
        ):
            raise SemanticVerificationV1Error(
                "semantic result/verification-work binding mismatch"
            )
        if tuple(sorted(self.recomputed_evidence_ids)) != self.recomputed_evidence_ids:
            raise SemanticVerificationV1Error(
                "recomputed evidence IDs must be in canonical order"
            )
        if not isinstance(self.binding, AttestationContextV1):
            raise SemanticVerificationV1Error(
                "semantic result must retain its authoritative attestation context"
            )
        context = self.binding.route_context
        expected_context = (
            context.route_decision_context_id,
            context.structural_id,
            context.query_id,
            context.selected_plan_id,
            context.threshold_profile_id,
            context.build_epoch_id,
            context.logical_occurrence_id,
            context.route_attempt_id,
        )
        attested_context = (
            self.attestation.route_decision_context_id,
            self.attestation.structural_id,
            self.attestation.query_id,
            self.attestation.selected_plan_id,
            self.attestation.threshold_profile_id,
            self.attestation.build_epoch_id,
            self.attestation.logical_occurrence_id,
            self.attestation.route_attempt_id,
        )
        if attested_context != expected_context or not _same_ref(
            self.attestation.decision_point_id, self.binding.decision_point_id
        ) or not _same_ref(
            self.attestation.transaction_id, self.binding.transaction_id
        ):
            raise SemanticVerificationV1Error(
                "semantic result/authoritative attestation context mismatch"
            )

    @property
    def role(self) -> SemanticRole:
        return _role(self.attestation.artifact_role)

    @property
    def outcome(self) -> str:
        return self.attestation.verification_result


_PROTOCOL_VERIFIED_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class ProtocolVerificationAttestationV1:
    """Typed attestation for a replayed forbidden-access violation.

    FQ7's original role table did not allocate a serializable role for access
    protocol violations.  This scoped attestation closes that evidence gap
    without pretending that a generic WorkVector proves a protocol failure.
    """

    artifact_id: str
    route_decision_context_id: str
    structural_id: str
    query_id: str
    selected_plan_id: str
    threshold_profile_id: str
    build_epoch_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: ContentRef
    transaction_id: ContentRef
    access_event_log_id: str
    protocol_sequence_profile_id: str
    semantic_verifier_id: str
    verification_profile_id: str
    verification_work_counter_record_id: str
    verified_at_protocol_step: int
    verification_result: str = "PROTOCOL_FAILURE"

    def __post_init__(self) -> None:
        for field in (
            "artifact_id",
            "route_decision_context_id",
            "structural_id",
            "query_id",
            "selected_plan_id",
            "threshold_profile_id",
            "build_epoch_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "access_event_log_id",
            "protocol_sequence_profile_id",
            "semantic_verifier_id",
            "verification_profile_id",
            "verification_work_counter_record_id",
        ):
            try:
                parse_content_id(getattr(self, field))
            except ValueError as error:
                raise SemanticVerificationV1Error(
                    f"{field} must be a full Phase-3E content ID"
                ) from error
        object.__setattr__(
            self,
            "decision_point_id",
            _content_ref(self.decision_point_id, "decision_point_id"),
        )
        object.__setattr__(
            self,
            "transaction_id",
            _content_ref(self.transaction_id, "transaction_id"),
        )
        if self.verification_result != "PROTOCOL_FAILURE":
            raise SemanticVerificationV1Error(
                "protocol verification result must be PROTOCOL_FAILURE"
            )
        if (
            type(self.verified_at_protocol_step) is not int
            or self.verified_at_protocol_step < 0
        ):
            raise SemanticVerificationV1Error(
                "verified_at_protocol_step must be nonnegative"
            )

    def _payload(self) -> dict[str, Any]:
        ref = lambda value: value.to_dict() if isinstance(value, TypedNotApplicable) else value
        return {
            "schema": "acfqp.protocol_verification_attestation.v1",
            "schema_version": SCHEMA_VERSION,
            "artifact_id": self.artifact_id,
            "artifact_schema_id": "ForbiddenAccessViolationV1",
            "artifact_role": SemanticRole.PROTOCOL_ACCESS.value,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "selected_plan_id": self.selected_plan_id,
            "threshold_profile_id": self.threshold_profile_id,
            "BuildEpoch_id": self.build_epoch_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": ref(self.decision_point_id),
            "transaction_id": ref(self.transaction_id),
            "access_event_log_id": self.access_event_log_id,
            "protocol_sequence_profile_id": self.protocol_sequence_profile_id,
            "semantic_verifier_id": self.semantic_verifier_id,
            "verification_profile_id": self.verification_profile_id,
            "verification_result": self.verification_result,
            "verification_work_counter_record_id": (
                self.verification_work_counter_record_id
            ),
            "verified_at_protocol_step": self.verified_at_protocol_step,
        }

    @property
    def verification_attestation_id(self) -> str:
        return content_id(TYPED_VERIFICATION_ATTESTATION_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_attestation_id": self.verification_attestation_id,
        }


@dataclass(frozen=True, slots=True)
class ProtocolVerificationResultV1:
    violation: ForbiddenAccessViolationV1
    attestation: ProtocolVerificationAttestationV1
    verification_work_record: CounterRecordV1
    _authority: object

    def __post_init__(self) -> None:
        if self._authority is not _PROTOCOL_VERIFIED_AUTHORITY:
            raise SemanticVerificationV1Error(
                "protocol verification result was not emitted by replay"
            )
        if self.attestation.artifact_id != self.violation.forbidden_access_violation_id:
            raise SemanticVerificationV1Error(
                "protocol result/violation artifact mismatch"
            )
        if self.attestation.verification_work_counter_record_id != (
            self.verification_work_record.record_id
        ):
            raise SemanticVerificationV1Error(
                "protocol result/verification-work mismatch"
            )

    @property
    def role(self) -> SemanticRole:
        return SemanticRole.PROTOCOL_ACCESS

    @property
    def outcome(self) -> str:
        return "PROTOCOL_FAILURE"


@dataclass(frozen=True, slots=True)
class TerminalRouteEvidenceBundleV1:
    """Runtime-only evidence joining a terminal to the selected runner work.

    The aggregate alone is not authoritative: it must be replayed from the
    native execution and post-result verification suffix.  Likewise, a valid
    access-log hash is insufficient without its decision freeze and the
    authority-bearing route decision supplied in ``evidence_results``.
    """

    execution_work: RecordedWorkV1
    verification_suffix_work: RecordedWorkV1
    aggregate_marginal_work: AggregatedMarginalWorkV1
    access_log: AccessEventLogV1
    freeze_attestation: RouteDecisionFreezeAttestationV1
    protocol_profile: ProtocolSequenceProfileV1

    def __post_init__(self) -> None:
        if not isinstance(self.execution_work, RecordedWorkV1) or not isinstance(
            self.verification_suffix_work, RecordedWorkV1
        ):
            raise SemanticVerificationV1Error(
                "terminal route evidence requires native execution and "
                "verification-suffix work"
            )
        if not isinstance(
            self.aggregate_marginal_work, AggregatedMarginalWorkV1
        ):
            raise SemanticVerificationV1Error(
                "terminal route evidence requires AggregatedMarginalWorkV1"
            )
        if not isinstance(self.access_log, AccessEventLogV1) or not isinstance(
            self.freeze_attestation, RouteDecisionFreezeAttestationV1
        ) or not isinstance(self.protocol_profile, ProtocolSequenceProfileV1):
            raise SemanticVerificationV1Error(
                "terminal route evidence requires typed access/freeze/profile objects"
            )


def _expected_attestation(
    *,
    artifact_id: str,
    spec: SemanticVerifierSpecV1,
    outcome: str,
    binding: AttestationContextV1,
    work: CounterRecordV1,
) -> TypedVerificationAttestationV1:
    if outcome not in spec.outcomes or outcome == "INVALID":
        raise SemanticVerificationV1Error(
            f"{outcome!r} is not a successful recomputed outcome for {spec.role.value}"
        )
    context = binding.route_context
    return TypedVerificationAttestationV1(
        artifact_id=artifact_id,
        artifact_schema_id=spec.artifact_schema_id,
        artifact_role=spec.role.value,
        route_decision_context_id=context.route_decision_context_id,
        structural_id=context.structural_id,
        query_id=context.query_id,
        selected_plan_id=context.selected_plan_id,
        threshold_profile_id=context.threshold_profile_id,
        build_epoch_id=context.build_epoch_id,
        logical_occurrence_id=context.logical_occurrence_id,
        route_attempt_id=context.route_attempt_id,
        decision_point_id=binding.decision_point_id,
        transaction_id=binding.transaction_id,
        semantic_verifier_id=spec.semantic_verifier_id,
        verification_profile_id=spec.verification_profile_id,
        verification_result=outcome,
        verification_work_counter_record_id=work.record_id,
        verified_at_protocol_step=binding.verified_at_protocol_step,
    )


def verify_typed_attestation_v1(
    claimed: TypedVerificationAttestationV1 | Mapping[str, Any],
    *,
    authority_result: "SemanticVerificationResultV1",
    registry: CounterRegistryV1 | None = None,
) -> TypedVerificationAttestationV1:
    """Validate a transported attestation against an authority-bearing result.

    A caller-supplied artifact ID and outcome are not authority.  Requiring the
    non-serializable result handle prevents this transport checker from being
    used to mint an attestation for an artifact that was never replayed.
    """

    result = _require_authoritative_result(authority_result)
    spec = require_implemented_role_v1(result.role)
    trusted_registry = _official_registry(registry)
    work = _verification_work_record(
        result.verification_work_record, spec, trusted_registry
    )
    document = claimed.to_dict() if isinstance(claimed, TypedVerificationAttestationV1) else claimed
    try:
        parsed = TypedVerificationAttestationV1.from_dict(document)
    except ValueError as error:
        raise SemanticVerificationV1Error(f"invalid typed attestation: {error}") from error
    if parsed != result.attestation or (
        parsed.verification_work_counter_record_id != work.record_id
    ):
        raise SemanticVerificationV1Error(
            "typed attestation does not match the authority-bearing semantic result"
        )
    return parsed


def _finish(
    *,
    artifact: object,
    artifact_id: str,
    spec: SemanticVerifierSpecV1,
    outcome: str,
    binding: AttestationContextV1,
    work: CounterRecordV1,
    recomputed_evidence_ids: Sequence[str] = (),
) -> SemanticVerificationResultV1:
    attestation = _expected_attestation(
        artifact_id=artifact_id,
        spec=spec,
        outcome=outcome,
        binding=binding,
        work=work,
    )
    ids = tuple(sorted(recomputed_evidence_ids))
    return SemanticVerificationResultV1(
        artifact,
        attestation,
        work,
        ids,
        binding,
        _VERIFIED_AUTHORITY,
    )


def _verify_work_binding_v1(
    vector: WorkVectorV1,
    binding: AttestationContextV1,
) -> None:
    """Bind native work ownership to the attested route context.

    ``WorkVectorV1.subject_id`` is the native ownership field.  V1 uses a
    transaction subject for local work, a BuildEpoch subject for rebuild work,
    and the route-attempt subject for the remaining attempt-scoped routes.
    Decision/transaction applicability is checked at the same boundary so a
    valid vector from another attempt cannot be re-attested in this context.
    """

    context = binding.route_context
    decision_na = isinstance(binding.decision_point_id, TypedNotApplicable)
    transaction_na = isinstance(binding.transaction_id, TypedNotApplicable)
    if vector.route_kind.value == "LOCAL_ATTEMPT":
        if decision_na or transaction_na:
            raise SemanticVerificationV1Error(
                "local WorkVector requires an applicable decision point and transaction"
            )
        expected_subject = binding.transaction_id
    elif vector.route_kind.value == "DIRECT_FALLBACK":
        if decision_na or not transaction_na:
            raise SemanticVerificationV1Error(
                "fallback WorkVector requires a decision point and no local transaction"
            )
        expected_subject = context.route_attempt_id
    elif vector.route_kind.value == "ABSTRACT_ONLY_CERTIFICATE":
        if not transaction_na:
            raise SemanticVerificationV1Error(
                "abstract/common-prefix WorkVector cannot bind a local transaction"
            )
        expected_subject = context.route_attempt_id
    elif vector.route_kind.value == "REBUILD":
        if not decision_na or not transaction_na:
            raise SemanticVerificationV1Error(
                "rebuild WorkVector cannot bind a query decision or local transaction"
            )
        expected_subject = context.build_epoch_id
    else:  # pragma: no cover - enum exhaustiveness
        raise SemanticVerificationV1Error("unknown WorkVector route kind")
    if vector.subject_id != expected_subject:
        raise SemanticVerificationV1Error(
            "WorkVector subject does not match its attested attempt/transaction/BuildEpoch"
        )


def verify_work_vector_semantics_v1(
    vector: WorkVectorV1 | Mapping[str, Any],
    *,
    binding: AttestationContextV1,
    verification_work_record: CounterRecordV1 | Mapping[str, Any],
    registry: CounterRegistryV1 | None = None,
) -> SemanticVerificationResultV1:
    """Re-materialize a native vector and replay completeness/reconciliation."""

    spec = require_implemented_role_v1(SemanticRole.WORK_VECTOR)
    trusted_registry = _official_registry(registry)
    work = _verification_work_record(
        verification_work_record, spec, trusted_registry
    )
    document = vector.to_dict() if isinstance(vector, WorkVectorV1) else vector
    try:
        parsed = WorkVectorV1.from_dict(document, trusted_registry)
        trusted_registry.validate_vector(parsed)
        _verify_work_binding_v1(parsed, binding)
        native_zero = NativeZeroAttestationV1.derive(parsed, trusted_registry)
        reconciliation = ReconciliationProofV1.derive(parsed, trusted_registry)
    except ValueError as error:
        raise SemanticVerificationV1Error(
            f"WorkVectorV1 semantic replay failed: {error}"
        ) from error
    return _finish(
        artifact=parsed,
        artifact_id=parsed.work_vector_id,
        spec=spec,
        outcome="VALID",
        binding=binding,
        work=work,
        recomputed_evidence_ids=(
            native_zero.native_zero_attestation_id,
            reconciliation.reconciliation_proof_id,
        ),
    )


def verify_actual_projection_semantics_v1(
    *,
    vector: WorkVectorV1 | Mapping[str, Any],
    claimed_comparison: ComparisonVectorV1 | Mapping[str, Any],
    projection_proof: ActualProjectionProofV1 | Mapping[str, Any],
    binding: AttestationContextV1,
    verification_work_record: CounterRecordV1 | Mapping[str, Any],
    registry: CounterRegistryV1 | None = None,
) -> SemanticVerificationResultV1:
    """Recompute the official actual comparison from exact native records."""

    spec = require_implemented_role_v1(SemanticRole.ACTUAL_PROJECTION)
    trusted_registry = _official_registry(registry)
    comparison_profile = official_comparison_profile_v1(trusted_registry)
    actual_profile = official_actual_projection_profile_v1(
        trusted_registry, comparison_profile
    )
    work = _verification_work_record(
        verification_work_record, spec, trusted_registry
    )
    try:
        parsed_vector = WorkVectorV1.from_dict(
            vector.to_dict() if isinstance(vector, WorkVectorV1) else vector,
            trusted_registry,
        )
        _verify_work_binding_v1(parsed_vector, binding)
        parsed_comparison = ComparisonVectorV1.from_dict(
            claimed_comparison.to_dict()
            if isinstance(claimed_comparison, ComparisonVectorV1)
            else claimed_comparison
        )
        parsed_proof = ActualProjectionProofV1.from_dict(
            projection_proof.to_dict()
            if isinstance(projection_proof, ActualProjectionProofV1)
            else projection_proof
        )
        recomputed = verify_actual_projection_v1(
            parsed_proof,
            parsed_vector,
            parsed_comparison,
            trusted_registry,
            comparison_profile,
            actual_profile,
        )
    except ValueError as error:
        raise SemanticVerificationV1Error(
            f"actual-projection semantic replay failed: {error}"
        ) from error
    return _finish(
        artifact=recomputed,
        artifact_id=recomputed.comparison_vector_id,
        spec=spec,
        outcome="VALID",
        binding=binding,
        work=work,
        recomputed_evidence_ids=(parsed_proof.actual_projection_proof_id,),
    )


def verify_ground_fallback_semantics_v1(
    execution: object,
    *,
    cap_profile: object,
    binding: AttestationContextV1,
    verification_work_record: CounterRecordV1 | Mapping[str, Any],
    registry: CounterRegistryV1 | None = None,
) -> SemanticVerificationResultV1:
    """Verify a trusted-executor fallback result without rerunning the solver.

    FQ10 forbids a second full ground-solver replay on the host.  Accordingly,
    this handler accepts only the non-serializable runtime execution seal minted
    after the authority-gated selected route finishes.  It independently
    replays the result schema, cap binding, native WorkVector completeness and
    reconciliation, exact frontier selection/infeasibility conditions, and all
    observable cap/counter invariants.  Raw JSON and unsealed raw-search
    results cannot cross this boundary.

    The runtime seal is a deliberately narrow V0 trust root.  It attests the
    in-process executor's exhaustive-search statement; it is not an isolated
    worker attestation or a portable public-bundle proof, and it does not turn
    on the official Phase-3E gate.
    """

    from acfqp.phase3e_fallback_v1 import (
        GroundFallbackCapProfileV1,
        GroundFallbackExecutionV1,
        GroundFallbackOutcome,
        GroundFallbackResultV1,
        GroundFallbackV1Error,
        verify_trusted_ground_fallback_execution_provenance_v1,
    )

    spec = require_implemented_role_v1(SemanticRole.GROUND_FALLBACK)
    trusted_registry = _official_registry(registry)
    work = _verification_work_record(
        verification_work_record, spec, trusted_registry
    )
    if not isinstance(execution, GroundFallbackExecutionV1):
        raise SemanticVerificationV1Error(
            "GROUND_FALLBACK requires an opaque in-memory trusted execution; "
            "raw result JSON has no authority"
        )
    try:
        delta = verify_trusted_ground_fallback_execution_provenance_v1(execution)
        parsed_result = GroundFallbackResultV1.from_dict(
            execution.result.to_dict()
        )
        parsed_vector = WorkVectorV1.from_dict(
            execution.work_vector.to_dict(), trusted_registry
        )
        parsed_cap = GroundFallbackCapProfileV1.from_dict(
            cap_profile.to_dict()
            if isinstance(cap_profile, GroundFallbackCapProfileV1)
            else cap_profile
        )
        trusted_registry.validate_vector(parsed_vector)
        _verify_work_binding_v1(parsed_vector, binding)
        native_zero = NativeZeroAttestationV1.derive(
            parsed_vector, trusted_registry
        )
        reconciliation = ReconciliationProofV1.derive(
            parsed_vector, trusted_registry
        )
    except (GroundFallbackV1Error, TypeError, ValueError) as error:
        raise SemanticVerificationV1Error(
            f"ground-fallback trusted-execution replay failed: {error}"
        ) from error

    if parsed_result != execution.result or parsed_vector != execution.work_vector:
        raise SemanticVerificationV1Error(
            "ground fallback runtime objects differ from strict schema replay"
        )
    context = binding.route_context
    if isinstance(binding.decision_point_id, TypedNotApplicable) or not isinstance(
        binding.transaction_id, TypedNotApplicable
    ):
        raise SemanticVerificationV1Error(
            "direct fallback requires an applicable decision point and typed-null transaction"
        )
    if (
        parsed_result.route_decision_context_id
        != context.route_decision_context_id
        or parsed_result.decision_point_id != binding.decision_point_id
        or parsed_result.route_attempt_id != context.route_attempt_id
        or parsed_result.query_id != context.query_id
    ):
        raise SemanticVerificationV1Error(
            "ground fallback result uses another route/query/decision context"
        )
    if (
        parsed_result.ground_fallback_cap_profile_id
        != parsed_cap.ground_fallback_cap_profile_id
    ):
        raise SemanticVerificationV1Error(
            "ground fallback result uses another finite cap profile"
        )
    if parsed_result.work_vector_id != parsed_vector.work_vector_id:
        raise SemanticVerificationV1Error(
            "ground fallback result does not bind the replayed native WorkVector"
        )

    values = parsed_vector.values
    cap_limits = {
        "fallback.states_expanded": parsed_cap.max_states_expanded,
        "fallback.actions_evaluated": parsed_cap.max_actions_evaluated,
        "fallback.ground_steps": parsed_cap.max_ground_steps,
        "fallback.outcome_rows": parsed_cap.max_outcome_rows,
        "fallback.bellman_backups": parsed_cap.max_bellman_backups,
        "control.cap_checks": parsed_cap.max_cap_checks,
    }
    exceeded = tuple(
        path for path, maximum in cap_limits.items() if values[path] > maximum
    )
    if exceeded:
        raise SemanticVerificationV1Error(
            "ground fallback actual WorkVector exceeds its finite cap: "
            + ", ".join(exceeded)
        )
    if (
        parsed_result.composed_candidate_count
        > parsed_cap.max_composed_candidates
        or values["fallback.bellman_backups"]
        != parsed_result.composed_candidate_count
    ):
        raise SemanticVerificationV1Error(
            "fallback composed-candidate work is absent, inconsistent, or over cap"
        )
    if (
        values["fallback.ground_steps"]
        > values["fallback.actions_evaluated"]
        or values["fallback.outcome_rows"]
        > values["fallback.ground_steps"]
        * parsed_cap.max_positive_outcomes_per_step
    ):
        raise SemanticVerificationV1Error(
            "fallback action/transition/outcome native counters are inconsistent"
        )

    successful_guards = (
        values["fallback.states_expanded"]
        + values["fallback.actions_evaluated"]
        + values["fallback.ground_steps"]
        + parsed_result.composed_candidate_count
    )
    cap_exhausted = parsed_result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED
    if values["control.cap_checks"] not in (
        successful_guards,
        successful_guards + (1 if cap_exhausted else 0),
    ):
        raise SemanticVerificationV1Error(
            "fallback cap-check count is not derivable from native guarded work"
        )

    # Pareto shape and constrained selection can be replayed from the exact
    # frontier bytes without any kernel call.  Completeness of that frontier is
    # the statement covered by the opaque trusted-executor provenance.
    frontier = parsed_result.frontier
    reward_risk = tuple(
        (point.expected_reward, point.failure_probability) for point in frontier
    )
    if len(set(reward_risk)) != len(reward_risk):
        raise SemanticVerificationV1Error(
            "ground fallback frontier repeats a reward-risk point"
        )
    for index, point in enumerate(frontier):
        if any(
            other_index != index
            and other.expected_reward >= point.expected_reward
            and other.failure_probability <= point.failure_probability
            and (
                other.expected_reward > point.expected_reward
                or other.failure_probability < point.failure_probability
            )
            for other_index, other in enumerate(frontier)
        ):
            raise SemanticVerificationV1Error(
                "ground fallback claimed frontier contains a dominated point"
            )
    feasible = tuple(
        point for point in frontier if point.failure_probability <= delta
    )

    outcome = parsed_result.outcome
    if outcome is GroundFallbackOutcome.FEASIBLE_CERTIFIED:
        if not feasible:
            raise SemanticVerificationV1Error(
                "FEASIBLE_CERTIFIED has no point below the trusted query delta"
            )
        selected = min(
            feasible,
            key=lambda point: (
                -point.expected_reward,
                point.failure_probability,
                point.policy_signature,
            ),
        )
        if (
            selected.policy_signature != parsed_result.selected_policy_signature
            or selected.expected_reward != parsed_result.selected_expected_reward
            or selected.failure_probability
            != parsed_result.selected_failure_probability
        ):
            raise SemanticVerificationV1Error(
                "ground fallback selected point is not the exact constrained optimum"
            )
        expected_successes, expected_failures, expected_rejections = 1, 0, 0
    elif outcome is GroundFallbackOutcome.INFEASIBLE_CERTIFIED:
        if not frontier or feasible:
            raise SemanticVerificationV1Error(
                "INFEASIBLE_CERTIFIED requires a complete nonempty frontier with no feasible point"
            )
        expected_successes, expected_failures, expected_rejections = 1, 0, 0
    else:
        allowed_cap_names = {
            "max_states_expanded",
            "max_actions_evaluated",
            "max_ground_steps",
            "max_outcome_rows",
            "max_bellman_backups",
            "max_composed_candidates",
            "max_cap_checks",
        }
        if parsed_result.cap_exhausted_name not in allowed_cap_names:
            raise SemanticVerificationV1Error(
                "CAP_EXHAUSTED does not name a registered fallback cap"
            )
        expected_successes, expected_failures, expected_rejections = 0, 1, 1

    if (
        values["route.attempts"] != 1
        or values["solver.attempts"] != 1
        or values["route.successes"] != expected_successes
        or values["solver.successes"] != expected_successes
        or values["route.failures"] != expected_failures
        or values["solver.failures"] != expected_failures
        or values["control.cap_rejections"] != expected_rejections
    ):
        raise SemanticVerificationV1Error(
            "ground fallback terminal outcome disagrees with native route/solver/cap counters"
        )

    return _finish(
        artifact=parsed_result,
        artifact_id=parsed_result.ground_fallback_result_id,
        spec=spec,
        outcome=outcome.value,
        binding=binding,
        work=work,
        recomputed_evidence_ids=(
            parsed_vector.work_vector_id,
            parsed_cap.ground_fallback_cap_profile_id,
            native_zero.native_zero_attestation_id,
            reconciliation.reconciliation_proof_id,
        ),
    )


_UPPER_CONTEXT_FIELDS = (
    "preregistration_id",
    "protocol_id",
    "comparison_profile_id",
    "counter_registry_id",
    "structural_id",
    "query_id",
    "selected_plan_id",
    "threshold_profile_id",
    "build_epoch_id",
    "logical_occurrence_id",
    "route_attempt_id",
)


def verify_local_transaction_result_semantics_v1(
    execution: object,
    *,
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    transaction: TransactionV1,
    cap_profile: RouteCapProfileV1,
    binding: AttestationContextV1,
    verification_work_record: CounterRecordV1 | Mapping[str, Any],
    registry: CounterRegistryV1 | None = None,
) -> SemanticVerificationResultV1:
    """Verify the scoped trusted local-worker result without solver replay.

    The opaque runtime seal is the V0 trust root for the fact that the existing
    isolated Phase-3D safe-chain worker produced this exact result.  This
    handler replays strict schemas, context/cap/work binding and native-vector
    integrity, but intentionally does not run the local solver again (FQ10).
    """

    from acfqp.phase3e_local_semantics_v1 import (
        LocalTransactionResultV1,
        Phase3ELocalSemanticV1Error,
        TrustedLocalExecutionV1,
        validate_local_execution_context_v1,
    )

    spec = require_implemented_role_v1(SemanticRole.LOCAL_SOLVER_RESULT)
    trusted_registry = _official_registry(registry)
    work = _verification_work_record(
        verification_work_record, spec, trusted_registry
    )
    if not isinstance(execution, TrustedLocalExecutionV1):
        raise SemanticVerificationV1Error(
            "LOCAL_SOLVER_RESULT requires opaque trusted runtime provenance; "
            "raw LocalTransactionResultV1 bytes have no authority"
        )
    if binding.route_context != context:
        raise SemanticVerificationV1Error(
            "local semantic binding carries another route context"
        )
    if (
        binding.decision_point_id != decision_point.decision_point_id
        or binding.transaction_id != transaction.transaction_id
    ):
        raise SemanticVerificationV1Error(
            "local semantic binding carries another decision or transaction"
        )
    try:
        parsed = LocalTransactionResultV1.from_dict(
            execution.local_result.to_dict()
        )
        parsed_vector = WorkVectorV1.from_dict(
            execution.work_vector.to_dict(), trusted_registry
        )
        validate_local_execution_context_v1(
            execution,
            context=context,
            decision_point=decision_point,
            transaction=transaction,
            cap_profile=cap_profile,
        )
        trusted_registry.validate_vector(parsed_vector)
        _verify_work_binding_v1(parsed_vector, binding)
        native_zero = NativeZeroAttestationV1.derive(
            parsed_vector, trusted_registry
        )
        reconciliation = ReconciliationProofV1.derive(
            parsed_vector, trusted_registry
        )
    except (Phase3ELocalSemanticV1Error, TypeError, ValueError) as error:
        raise SemanticVerificationV1Error(
            f"trusted local-result replay failed: {error}"
        ) from error
    if parsed != execution.local_result or parsed_vector != execution.work_vector:
        raise SemanticVerificationV1Error(
            "local runtime objects differ from strict schema replay"
        )
    values = parsed_vector.values
    limits = dict(cap_profile.limits)
    direct_cap_bindings = {
        "local.causal_candidate_evaluations": "max_causal_candidate_evaluations",
        "local.materialization_ground_steps": "max_materialization_ground_steps",
        "local.materialization_outcome_rows": "max_materialization_positive_outcomes",
        "local.compiler_expanded_forms": "max_expanded_forms",
        "local.compiler_domain_assignments": "max_domain_assignments",
        "local.solver_subset_evaluations": "max_subset_evaluations",
        "local.solver_policy_assignments": "max_policy_assignments",
        "local.solver_frontier_points": "max_root_frontier_points",
        "local.solver_dominance_comparisons": "max_dominance_comparisons",
        "local.solver_affine_term_evaluations": "max_affine_term_evaluations",
        "local.postaudit_ground_steps": "max_postaudit_ground_steps",
        "local.postaudit_outcome_rows": "max_postaudit_positive_outcomes",
    }
    exceeded = tuple(
        path
        for path, cap_name in direct_cap_bindings.items()
        if values[path] > limits[cap_name]
    )
    compiler_input_cap = sum(
        limits[name]
        for name in (
            "max_slice_cells",
            "max_slice_members",
            "max_slice_actions",
            "max_slice_successor_rows",
        )
    )
    if values["local.compiler_input_records"] > compiler_input_cap:
        exceeded += ("local.compiler_input_records",)
    if values["control.cap_checks"] > sum(limits.values()):
        exceeded += ("control.cap_checks",)
    if exceeded:
        raise SemanticVerificationV1Error(
            "local actual WorkVector exceeds the frozen RouteCapProfileV1: "
            + ", ".join(exceeded)
        )
    from acfqp.phase3e_local_semantics_v1 import LocalSolverOutcome

    if parsed.outcome is LocalSolverOutcome.SEARCH_CAP_EXHAUSTED:
        saturation_paths = {
            cap_name: path for path, cap_name in direct_cap_bindings.items()
        }
        saturation_path = saturation_paths.get(parsed.cap_reason)
        if (
            parsed.cap_reason not in limits
            or values["control.cap_rejections"] != 1
            or saturation_path is None
            or values[saturation_path] != limits[parsed.cap_reason]
        ):
            raise SemanticVerificationV1Error(
                "SEARCH_CAP_EXHAUSTED lacks registered native cap-saturation evidence"
            )
    elif values["control.cap_rejections"] != 0:
        raise SemanticVerificationV1Error(
            "a complete local solver result cannot carry cap rejections"
        )
    return _finish(
        artifact=parsed,
        artifact_id=parsed.local_transaction_result_id,
        spec=spec,
        outcome=parsed.outcome.value,
        binding=binding,
        work=work,
        recomputed_evidence_ids=(
            native_zero.native_zero_attestation_id,
            reconciliation.reconciliation_proof_id,
            parsed.runtime_attestation_binding_id,
            parsed.worker_result_binding_id,
        ),
    )


def verify_post_audit_semantics_v1(
    execution: object,
    *,
    local_solver_result: SemanticVerificationResultV1,
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    transaction: TransactionV1,
    cap_profile: RouteCapProfileV1,
    binding: AttestationContextV1,
    verification_work_record: CounterRecordV1 | Mapping[str, Any],
    registry: CounterRegistryV1 | None = None,
) -> SemanticVerificationResultV1:
    """Verify the exact trusted post-audit and its local-result dependency."""

    from acfqp.phase3e_local_semantics_v1 import (
        Phase3ELocalSemanticV1Error,
        PostAuditCertificateV1,
        TrustedLocalExecutionV1,
        validate_local_execution_context_v1,
        verify_trusted_postaudit_runtime_provenance_v1,
    )

    spec = require_implemented_role_v1(SemanticRole.POST_AUDIT)
    trusted_registry = _official_registry(registry)
    work = _verification_work_record(
        verification_work_record, spec, trusted_registry
    )
    if not isinstance(execution, TrustedLocalExecutionV1):
        raise SemanticVerificationV1Error(
            "POST_AUDIT requires opaque trusted runtime provenance; raw bytes have no authority"
        )
    verified_local = require_semantic_verification_result_v1(
        local_solver_result, SemanticRole.LOCAL_SOLVER_RESULT
    )
    if binding.route_context != context or (
        binding.decision_point_id != decision_point.decision_point_id
        or binding.transaction_id != transaction.transaction_id
    ):
        raise SemanticVerificationV1Error(
            "post-audit semantic binding carries another context or transaction"
        )
    try:
        verify_trusted_postaudit_runtime_provenance_v1(execution)
        validate_local_execution_context_v1(
            execution,
            context=context,
            decision_point=decision_point,
            transaction=transaction,
            cap_profile=cap_profile,
        )
        if execution.post_audit is None:
            raise Phase3ELocalSemanticV1Error("trusted execution has no post-audit artifact")
        parsed = PostAuditCertificateV1.from_dict(execution.post_audit.to_dict())
    except (Phase3ELocalSemanticV1Error, TypeError, ValueError) as error:
        raise SemanticVerificationV1Error(
            f"trusted post-audit replay failed: {error}"
        ) from error
    if parsed != execution.post_audit:
        raise SemanticVerificationV1Error(
            "post-audit runtime object differs from strict schema replay"
        )
    if (
        verified_local.artifact != execution.local_result
        or verified_local.attestation.artifact_id
        != parsed.local_transaction_result_id
        or verified_local.binding != binding
        or parsed.route_decision_context_id != context.route_decision_context_id
        or parsed.decision_point_id != decision_point.decision_point_id
        or parsed.transaction_id != transaction.transaction_id
        or parsed.route_attempt_id != context.route_attempt_id
        or parsed.query_id != context.query_id
        or parsed.selected_plan_id != context.selected_plan_id
        or parsed.work_vector_id != execution.work_vector.work_vector_id
    ):
        raise SemanticVerificationV1Error(
            "post-audit/local-result/context identity chain does not match"
        )
    values = execution.work_vector.values
    if (
        parsed.postaudit_ground_steps
        != values["local.postaudit_ground_steps"]
        or parsed.postaudit_positive_outcomes
        != values["local.postaudit_outcome_rows"]
    ):
        raise SemanticVerificationV1Error(
            "post-audit artifact counters differ from the native WorkVector"
        )
    expected_success = parsed.outcome.value == "CERTIFIED"
    if (
        values["route.attempts"] != 1
        or values["route.successes"] != (1 if expected_success else 0)
        or values["route.failures"] != (0 if expected_success else 1)
    ):
        raise SemanticVerificationV1Error(
            "post-audit outcome disagrees with native route completion counters"
        )
    return _finish(
        artifact=parsed,
        artifact_id=parsed.post_audit_certificate_id,
        spec=spec,
        outcome=parsed.outcome.value,
        binding=binding,
        work=work,
        recomputed_evidence_ids=(
            parsed.audit_issue_set_id,
            verified_local.attestation.verification_attestation_id,
        ),
    )


def _load_route_object(value: Any, expected_type: type[Any]) -> Any:
    document = value.to_dict() if isinstance(value, expected_type) else value
    try:
        return expected_type.from_dict(document)
    except ValueError as error:
        raise SemanticVerificationV1Error(
            f"invalid {expected_type.__name__}: {error}"
        ) from error


def _replay_safe_chain_local_preselection_source_v1(
    *,
    source: Any,
    frozen_world: Any,
    context: RouteDecisionContextV1,
    frontier: FrontierSnapshotV1,
    causal: CausalEvidenceV1,
    decision_point: DecisionPointV1,
    transaction: TransactionV1,
    cap_profile: RouteCapProfileV1,
) -> tuple[Any, Any, Any, Any]:
    """Reload and recompute the registered preselection source chain."""

    from acfqp.frozen_phase3c import FrozenPhase3CWorld, load_frozen_phase3c_world
    from acfqp.phase3d import prepare_safe_chain_estimate_context
    from acfqp.phase3e_local_preselection_v1 import (
        SafeChainLocalPreselectionSourceV1,
        derive_safe_chain_local_frontier_and_causal_v1,
        derive_safe_chain_local_preselection_source_v1,
    )

    parsed_source = _load_route_object(
        source, SafeChainLocalPreselectionSourceV1
    )
    if not isinstance(frozen_world, FrozenPhase3CWorld):
        raise SemanticVerificationV1Error(
            "safe-chain local replay requires a loaded FrozenPhase3CWorld parent"
        )
    try:
        # The reload revalidates the manifest, model, BuildEpoch, and frozen
        # action catalogue.  Preparation consumes only RAPM realizations and
        # that frozen catalogue; it performs no kernel step/materialization.
        replayed_world = load_frozen_phase3c_world(frozen_world.source_bundle)
        prepared = prepare_safe_chain_estimate_context(replayed_world)
        replayed_frontier, replayed_causal = (
            derive_safe_chain_local_frontier_and_causal_v1(
                prepared=prepared,
                context=context,
                cap_profile=cap_profile,
                frontier_stage=transaction.transaction_index,
            )
        )
        replayed_source = derive_safe_chain_local_preselection_source_v1(
            prepared=prepared,
            context=context,
            frontier=replayed_frontier,
            causal=replayed_causal,
            decision_point=decision_point,
            transaction=transaction,
            cap_profile=cap_profile,
            frozen_at_protocol_step=parsed_source.frozen_at_protocol_step,
        )
    except (RuntimeError, TypeError, ValueError) as error:
        raise SemanticVerificationV1Error(
            f"safe-chain local preselection replay failed: {error}"
        ) from error
    if frontier != replayed_frontier or causal != replayed_causal:
        raise SemanticVerificationV1Error(
            "frontier/causal evidence differs from frozen-parent replay"
        )
    if parsed_source != replayed_source:
        raise SemanticVerificationV1Error(
            "local preselection source differs from the verified frozen-parent projection"
        )
    return parsed_source, prepared, replayed_frontier, replayed_causal


def verify_safe_chain_local_causal_semantics_v1(
    claimed_causal: CausalEvidenceV1 | Mapping[str, Any],
    *,
    source: Any,
    frozen_world: Any,
    context: RouteDecisionContextV1 | Mapping[str, Any],
    frontier: FrontierSnapshotV1 | Mapping[str, Any],
    decision_point: DecisionPointV1 | Mapping[str, Any],
    transaction: TransactionV1 | Mapping[str, Any],
    cap_profile: RouteCapProfileV1 | Mapping[str, Any],
    binding: AttestationContextV1,
    verification_work_record: CounterRecordV1 | Mapping[str, Any],
    registry: CounterRegistryV1 | None = None,
) -> SemanticVerificationResultV1:
    """Authorize the registered safe-chain ``FOUND`` causal result.

    Negative claims and every unregistered domain/profile fail closed.  The
    route state machine therefore cannot be reopened by supplying a cheap
    local cardinality after a missing, invalid, or negative causal authority.
    """

    from acfqp.phase3e_local_preselection_v1 import (
        SafeChainLocalPreselectionSourceV1,
    )

    spec = require_implemented_role_v1(SemanticRole.CAUSAL_SEARCH)
    trusted_registry = _official_registry(registry)
    work = _verification_work_record(
        verification_work_record, spec, trusted_registry
    )
    parsed_context = _load_context(context)
    parsed_frontier = _load_route_object(frontier, FrontierSnapshotV1)
    parsed_causal = _load_route_object(claimed_causal, CausalEvidenceV1)
    parsed_point = _load_route_object(decision_point, DecisionPointV1)
    parsed_transaction = _load_route_object(transaction, TransactionV1)
    parsed_cap = _load_route_object(cap_profile, RouteCapProfileV1)
    parsed_source = _load_route_object(source, SafeChainLocalPreselectionSourceV1)
    if binding.route_context != parsed_context:
        raise SemanticVerificationV1Error(
            "local causal binding uses another route context"
        )
    if (
        binding.decision_point_id != parsed_point.decision_point_id
        or binding.transaction_id != parsed_transaction.transaction_id
    ):
        raise SemanticVerificationV1Error(
            "local causal binding uses another decision point or transaction"
        )
    if (
        parsed_frontier.route_decision_context_id
        != parsed_context.route_decision_context_id
        or parsed_point.route_decision_context_id
        != parsed_context.route_decision_context_id
        or parsed_point.frontier_snapshot_id
        != parsed_frontier.frontier_snapshot_id
        or parsed_point.causal_evidence_id != parsed_causal.causal_evidence_id
        or parsed_transaction.decision_point_id != parsed_point.decision_point_id
        or parsed_transaction.frontier_snapshot_id
        != parsed_frontier.frontier_snapshot_id
        or parsed_transaction.route_cap_profile_id != parsed_cap.route_cap_profile_id
        or parsed_source.transaction_id != parsed_transaction.transaction_id
    ):
        raise SemanticVerificationV1Error(
            "local causal context/frontier/transaction/cap chain is stale"
        )
    if parsed_source.frozen_at_protocol_step >= binding.verified_at_protocol_step:
        raise SemanticVerificationV1Error(
            "local preselection source was not frozen before semantic verification"
        )
    parsed_source, _prepared, _frontier, replayed_causal = (
        _replay_safe_chain_local_preselection_source_v1(
            source=parsed_source,
            frozen_world=frozen_world,
            context=parsed_context,
            frontier=parsed_frontier,
            causal=parsed_causal,
            decision_point=parsed_point,
            transaction=parsed_transaction,
            cap_profile=parsed_cap,
        )
    )
    if replayed_causal.outcome is not CausalOutcome.FOUND:
        # The registered safe-chain profile has one real FOUND result.  This
        # branch is deliberately explicit so adding another outcome requires
        # a new replay profile rather than inheriting authority accidentally.
        raise SemanticVerificationV1Error(
            "safe-chain causal authority supports only the recomputed FOUND profile"
        )
    return _finish(
        artifact=replayed_causal,
        artifact_id=replayed_causal.causal_evidence_id,
        spec=spec,
        outcome=replayed_causal.outcome.value,
        binding=binding,
        work=work,
        recomputed_evidence_ids=(
            parsed_source.source_artifact_id,
            parsed_source.extraction_profile_id,
            parsed_frontier.frontier_snapshot_id,
            *(artifact_id for _, artifact_id in parsed_source.parent_artifact_ids),
        ),
    )


def verify_safe_chain_local_cardinality_semantics_v1(
    claimed_cardinality: CardinalityEvidenceV1 | Mapping[str, Any],
    *,
    source: Any,
    bound: Any,
    causal_result: SemanticVerificationResultV1,
    frozen_world: Any,
    context: RouteDecisionContextV1 | Mapping[str, Any],
    frontier: FrontierSnapshotV1 | Mapping[str, Any],
    decision_point: DecisionPointV1 | Mapping[str, Any],
    transaction: TransactionV1 | Mapping[str, Any],
    cap_profile: RouteCapProfileV1 | Mapping[str, Any],
    binding: AttestationContextV1,
    verification_work_record: CounterRecordV1 | Mapping[str, Any],
    registry: CounterRegistryV1 | None = None,
) -> SemanticVerificationResultV1:
    """Authorize complete local route cardinalities from frozen parents."""

    from acfqp.phase3e_local_preselection_v1 import (
        SafeChainLocalCardinalityBoundV1,
        SafeChainLocalPreselectionSourceV1,
        build_safe_chain_local_cardinality_evidence_v1,
        derive_safe_chain_local_cardinality_bound_v1,
    )

    spec = require_implemented_role_v1(SemanticRole.CARDINALITY_EVIDENCE)
    trusted_registry = _official_registry(registry)
    work = _verification_work_record(
        verification_work_record, spec, trusted_registry
    )
    parsed_context = _load_context(context)
    parsed_frontier = _load_route_object(frontier, FrontierSnapshotV1)
    parsed_point = _load_route_object(decision_point, DecisionPointV1)
    parsed_transaction = _load_route_object(transaction, TransactionV1)
    parsed_cap = _load_route_object(cap_profile, RouteCapProfileV1)
    parsed_source = _load_route_object(source, SafeChainLocalPreselectionSourceV1)
    parsed_bound = _load_route_object(bound, SafeChainLocalCardinalityBoundV1)
    parsed_claim = _load_route_object(claimed_cardinality, CardinalityEvidenceV1)
    verified_causal = require_semantic_verification_result_v1(
        causal_result, SemanticRole.CAUSAL_SEARCH
    )
    _verify_result_context(verified_causal, binding)
    if (
        verified_causal.outcome != CausalOutcome.FOUND.value
        or not isinstance(verified_causal.artifact, CausalEvidenceV1)
        or verified_causal.attestation.artifact_id
        != verified_causal.artifact.causal_evidence_id
    ):
        raise SemanticVerificationV1Error(
            "local cardinality requires CAUSAL_SEARCH=FOUND authority"
        )
    parsed_causal = verified_causal.artifact
    if binding.route_context != parsed_context:
        raise SemanticVerificationV1Error(
            "local cardinality binding uses another route context"
        )
    if (
        binding.decision_point_id != parsed_point.decision_point_id
        or binding.transaction_id != parsed_transaction.transaction_id
    ):
        raise SemanticVerificationV1Error(
            "local cardinality binding uses another decision point or transaction"
        )
    if (
        parsed_point.causal_evidence_id != parsed_causal.causal_evidence_id
        or parsed_point.frontier_snapshot_id != parsed_frontier.frontier_snapshot_id
        or parsed_transaction.decision_point_id != parsed_point.decision_point_id
        or parsed_transaction.frontier_snapshot_id
        != parsed_frontier.frontier_snapshot_id
        or parsed_transaction.route_cap_profile_id != parsed_cap.route_cap_profile_id
        or parsed_claim.route_kind is not RouteKind.LOCAL_ATTEMPT
        or parsed_claim.route_cap_profile_id != parsed_cap.route_cap_profile_id
        or parsed_claim.frontier_snapshot_id
        != parsed_frontier.frontier_snapshot_id
    ):
        raise SemanticVerificationV1Error(
            "local cardinality evidence uses a stale frontier/transaction/cap"
        )
    if parsed_source.frozen_at_protocol_step >= binding.verified_at_protocol_step:
        raise SemanticVerificationV1Error(
            "local cardinality source was not frozen before semantic verification"
        )
    parsed_source, _prepared, _frontier, _causal = (
        _replay_safe_chain_local_preselection_source_v1(
            source=parsed_source,
            frozen_world=frozen_world,
            context=parsed_context,
            frontier=parsed_frontier,
            causal=parsed_causal,
            decision_point=parsed_point,
            transaction=parsed_transaction,
            cap_profile=parsed_cap,
        )
    )
    try:
        recomputed_bound = derive_safe_chain_local_cardinality_bound_v1(
            source=parsed_source,
            cap_profile=parsed_cap,
            registry=trusted_registry,
        )
        recomputed_cardinality = build_safe_chain_local_cardinality_evidence_v1(
            context=parsed_context,
            decision_point=parsed_point,
            transaction=parsed_transaction,
            cap_profile=parsed_cap,
            bound=recomputed_bound,
        )
    except ValueError as error:
        raise SemanticVerificationV1Error(
            f"safe-chain local cardinality replay failed: {error}"
        ) from error
    if parsed_bound != recomputed_bound:
        raise SemanticVerificationV1Error(
            "local cardinality bound differs from the registered formula"
        )
    if parsed_claim != recomputed_cardinality:
        raise SemanticVerificationV1Error(
            "CardinalityEvidenceV1 differs from authoritative local projection"
        )
    return _finish(
        artifact=recomputed_cardinality,
        artifact_id=recomputed_cardinality.cardinality_evidence_id,
        spec=spec,
        outcome="VALID",
        binding=binding,
        work=work,
        recomputed_evidence_ids=(
            parsed_source.source_artifact_id,
            parsed_source.extraction_profile_id,
            recomputed_bound.local_cardinality_bound_id,
            verified_causal.attestation.verification_attestation_id,
            *(artifact_id for _, artifact_id in parsed_source.parent_artifact_ids),
        ),
    )


def verify_safe_chain_fallback_cardinality_semantics_v1(
    claimed_cardinality: CardinalityEvidenceV1 | Mapping[str, Any],
    *,
    source: Any,
    bound: Any,
    frozen_world: Any,
    context: RouteDecisionContextV1 | Mapping[str, Any],
    decision_point: DecisionPointV1 | Mapping[str, Any],
    cap_profile: Any,
    binding: AttestationContextV1,
    verification_work_record: CounterRecordV1 | Mapping[str, Any],
    registry: CounterRegistryV1 | None = None,
) -> SemanticVerificationResultV1:
    """Authorize one safe-chain direct-fallback cardinality chain.

    The supplied source and bound are merely claims.  The verifier reloads the
    frozen Phase-3C bundle from its source path, replays its manifest/model/
    BuildEpoch/action-catalogue bindings, confirms that the loader performed
    zero ground transition calls, and regenerates source, bound, and generic
    cardinality evidence with the registered fixture-specific integer formula.
    """

    from acfqp.frozen_phase3c import (
        FrozenPhase3CWorld,
        load_frozen_phase3c_world,
    )
    from acfqp.phase3e_fallback_v1 import (
        GroundFallbackCapProfileV1,
        GroundFallbackCardinalityBoundV1,
        SafeChainFallbackCardinalitySourceV1,
        build_ground_fallback_cardinality_evidence_v1,
        derive_safe_chain_fallback_cardinality_bound_v1,
        derive_safe_chain_fallback_cardinality_source_v1,
    )

    spec = require_implemented_role_v1(SemanticRole.CARDINALITY_EVIDENCE)
    trusted_registry = _official_registry(registry)
    work = _verification_work_record(
        verification_work_record, spec, trusted_registry
    )
    parsed_context = _load_context(context)
    if binding.route_context != parsed_context:
        raise SemanticVerificationV1Error(
            "fallback cardinality binding uses another route context"
        )
    parsed_point = _load_route_object(decision_point, DecisionPointV1)
    if (
        parsed_point.route_decision_context_id
        != parsed_context.route_decision_context_id
        or not _same_ref(binding.decision_point_id, parsed_point.decision_point_id)
    ):
        raise SemanticVerificationV1Error(
            "fallback cardinality uses another decision point"
        )
    if not isinstance(binding.transaction_id, TypedNotApplicable):
        raise SemanticVerificationV1Error(
            "direct-fallback cardinality requires typed-null transaction"
        )
    parsed_cap = _load_route_object(cap_profile, GroundFallbackCapProfileV1)
    parsed_source = _load_route_object(
        source, SafeChainFallbackCardinalitySourceV1
    )
    parsed_bound = _load_route_object(bound, GroundFallbackCardinalityBoundV1)
    parsed_claim = _load_route_object(
        claimed_cardinality, CardinalityEvidenceV1
    )
    if (
        parsed_source.route_decision_context_id
        != parsed_context.route_decision_context_id
        or parsed_source.decision_point_id != parsed_point.decision_point_id
        or parsed_bound.route_decision_context_id
        != parsed_context.route_decision_context_id
        or parsed_bound.decision_point_id != parsed_point.decision_point_id
        or parsed_claim.route_decision_context_id
        != parsed_context.route_decision_context_id
    ):
        raise SemanticVerificationV1Error(
            "fallback cardinality source/bound/evidence context mismatch"
        )
    if (
        parsed_source.ground_fallback_cap_profile_id
        != parsed_cap.ground_fallback_cap_profile_id
        or parsed_bound.ground_fallback_cap_profile_id
        != parsed_cap.ground_fallback_cap_profile_id
        or parsed_claim.route_cap_profile_id != parsed_cap.route_cap_profile_id
    ):
        raise SemanticVerificationV1Error(
            "fallback cardinality source/bound/evidence cap mismatch"
        )
    if parsed_claim.route_kind is not RouteKind.DIRECT_FALLBACK:
        raise SemanticVerificationV1Error(
            "safe-chain fallback authority cannot authorize local cardinality"
        )
    if parsed_source.frozen_at_protocol_step >= binding.verified_at_protocol_step:
        raise SemanticVerificationV1Error(
            "fallback cardinality source was not frozen before semantic verification"
        )
    if not isinstance(frozen_world, FrozenPhase3CWorld):
        raise SemanticVerificationV1Error(
            "fallback cardinality requires a loaded FrozenPhase3CWorld parent"
        )
    try:
        # Never trust the caller's in-memory member/count fields.  Reloading
        # the bundle makes deletion+rehash attacks observable through the
        # signed manifest and exact parent topology.
        replayed_world = load_frozen_phase3c_world(frozen_world.source_bundle)
        recomputed_source = derive_safe_chain_fallback_cardinality_source_v1(
            world=replayed_world,
            context=parsed_context,
            decision_point=parsed_point,
            cap_profile=parsed_cap,
            frozen_at_protocol_step=parsed_source.frozen_at_protocol_step,
        )
        recomputed_bound = derive_safe_chain_fallback_cardinality_bound_v1(
            source=recomputed_source,
            cap_profile=parsed_cap,
        )
        recomputed_cardinality = build_ground_fallback_cardinality_evidence_v1(
            context=parsed_context,
            decision_point=parsed_point,
            cap_profile=parsed_cap,
            bound=recomputed_bound,
        )
    except ValueError as error:
        raise SemanticVerificationV1Error(
            f"safe-chain fallback cardinality replay failed: {error}"
        ) from error
    if parsed_source != recomputed_source:
        raise SemanticVerificationV1Error(
            "fallback cardinality source differs from the verified frozen parent extraction"
        )
    if parsed_bound != recomputed_bound:
        raise SemanticVerificationV1Error(
            "fallback cardinality bound differs from the registered formula"
        )
    if parsed_claim != recomputed_cardinality:
        raise SemanticVerificationV1Error(
            "CardinalityEvidenceV1 differs from the authoritative fallback projection"
        )
    parent_ids = tuple(artifact_id for _, artifact_id in parsed_source.parent_artifact_ids)
    return _finish(
        artifact=recomputed_cardinality,
        artifact_id=recomputed_cardinality.cardinality_evidence_id,
        spec=spec,
        outcome="VALID",
        binding=binding,
        work=work,
        recomputed_evidence_ids=(
            parsed_source.source_artifact_id,
            parsed_source.extraction_profile_id,
            parsed_bound.ground_fallback_cardinality_bound_id,
            *parent_ids,
        ),
    )


def verify_route_upper_semantics_v1(
    claimed_upper: RouteUpperBoundEnvelopeV1 | Mapping[str, Any],
    *,
    derivation_proof: RouteUpperDerivationProofV1 | Mapping[str, Any],
    cardinality_result: SemanticVerificationResultV1,
    context: RouteDecisionContextV1 | Mapping[str, Any],
    decision_point: DecisionPointV1 | Mapping[str, Any],
    cap_profile: Any | Mapping[str, Any],
    formula: RouteUpperFormulaV1 | Mapping[str, Any],
    transaction: TransactionV1 | Mapping[str, Any] | None,
    causal: CausalEvidenceV1 | Mapping[str, Any] | None,
    binding: AttestationContextV1,
    verification_work_record: CounterRecordV1 | Mapping[str, Any],
    registry: CounterRegistryV1 | None = None,
) -> SemanticVerificationResultV1:
    """Replay the complete cap/formula/envelope chain.

    The cardinality input must be an authority-bearing semantic result.  A
    transport-valid ``CardinalityEvidenceV1`` or its content hash is never
    accepted directly.  The registered safe-chain fallback handler can mint
    this result after frozen-parent replay; other domain/route profiles remain
    fail-closed until their own source authorities land.
    """

    spec = require_implemented_role_v1(SemanticRole.ROUTE_UPPER)
    trusted_registry = _official_registry(registry)
    comparison_profile = official_comparison_profile_v1(trusted_registry)
    work = _verification_work_record(
        verification_work_record, spec, trusted_registry
    )
    parsed_context = _load_context(context)
    if binding.route_context != parsed_context:
        raise SemanticVerificationV1Error(
            "route-upper attestation context differs from replayed context"
        )
    parsed_point = _load_route_object(decision_point, DecisionPointV1)
    if (
        parsed_point.route_decision_context_id
        != parsed_context.route_decision_context_id
        or not _same_ref(binding.decision_point_id, parsed_point.decision_point_id)
    ):
        raise SemanticVerificationV1Error(
            "route-upper decision point is stale for the attested context"
        )
    parsed_formula = _load_route_object(formula, RouteUpperFormulaV1)
    parsed_upper = _load_route_object(claimed_upper, RouteUpperBoundEnvelopeV1)
    if parsed_upper.route_kind is RouteKind.LOCAL_ATTEMPT:
        parsed_cap = _load_route_object(cap_profile, RouteCapProfileV1)
    else:
        # Import lazily: the fallback module imports the semantic authority
        # layer at its production execution boundary.
        from acfqp.phase3e_fallback_v1 import GroundFallbackCapProfileV1

        parsed_cap = _load_route_object(
            cap_profile, GroundFallbackCapProfileV1
        )
    parsed_proof = _load_route_object(
        derivation_proof, RouteUpperDerivationProofV1
    )
    parsed_transaction = (
        None
        if transaction is None
        else _load_route_object(transaction, TransactionV1)
    )
    parsed_causal = (
        None if causal is None else _load_route_object(causal, CausalEvidenceV1)
    )

    verified_cardinality = require_semantic_verification_result_v1(
        cardinality_result, SemanticRole.CARDINALITY_EVIDENCE
    )
    if verified_cardinality.outcome != "VALID" or not isinstance(
        verified_cardinality.artifact, CardinalityEvidenceV1
    ):
        raise SemanticVerificationV1Error(
            "route upper requires CARDINALITY_EVIDENCE=VALID authority"
        )
    _verify_result_context(verified_cardinality, binding)
    parsed_cardinality = verified_cardinality.artifact
    if (
        verified_cardinality.attestation.artifact_id
        != parsed_cardinality.cardinality_evidence_id
    ):
        raise SemanticVerificationV1Error(
            "cardinality authority does not bind its replayed artifact"
        )

    official_formula = official_route_upper_formula_v1(
        parsed_upper.route_kind,
        registry=trusted_registry,
        profile=comparison_profile,
        cap_profile=parsed_cap,
    )
    if parsed_formula != official_formula:
        raise SemanticVerificationV1Error(
            "route upper uses a non-official route/cap formula"
        )
    try:
        verify_route_upper_derivation_v1(
            parsed_upper,
            parsed_proof,
            context=parsed_context,
            decision_point=parsed_point,
            cardinality=parsed_cardinality,
            cap_profile=parsed_cap,
            registry=trusted_registry,
            profile=comparison_profile,
            formula=parsed_formula,
            transaction=parsed_transaction,
            causal=parsed_causal,
        )
    except ValueError as error:
        raise SemanticVerificationV1Error(
            f"route-upper semantic replay failed: {error}"
        ) from error
    if parsed_upper.route_kind is RouteKind.LOCAL_ATTEMPT:
        if parsed_transaction is None or not _same_ref(
            binding.transaction_id, parsed_transaction.transaction_id
        ):
            raise SemanticVerificationV1Error(
                "local route upper uses another or missing transaction"
            )
    elif not isinstance(binding.transaction_id, TypedNotApplicable):
        raise SemanticVerificationV1Error(
            "direct-fallback upper cannot be attested as local transaction work"
        )
    return _finish(
        artifact=parsed_upper,
        artifact_id=parsed_upper.route_upper_bound_envelope_id,
        spec=spec,
        outcome="VALID",
        binding=binding,
        work=work,
        recomputed_evidence_ids=(
            verified_cardinality.attestation.verification_attestation_id,
            parsed_formula.formula_id,
            parsed_proof.derivation_proof_id,
        ),
    )


def _authority_upper_or_error(
    result: SemanticVerificationResultV1,
    *,
    route_kind: RouteKind,
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    binding: AttestationContextV1,
) -> RouteUpperBoundEnvelopeV1:
    verified = require_semantic_verification_result_v1(
        result, SemanticRole.ROUTE_UPPER
    )
    if verified.outcome != "VALID" or not isinstance(
        verified.artifact, RouteUpperBoundEnvelopeV1
    ):
        raise SemanticVerificationV1Error(
            "route decision requires ROUTE_UPPER=VALID authority"
        )
    if verified.binding.route_context != binding.route_context or not _same_ref(
        verified.binding.decision_point_id, binding.decision_point_id
    ):
        raise SemanticVerificationV1Error(
            "route-upper authority belongs to another context or decision point"
        )
    upper = verified.artifact
    if (
        upper.route_kind is not route_kind
        or upper.route_upper_bound_envelope_id != verified.attestation.artifact_id
        or upper.decision_point_id != decision_point.decision_point_id
    ):
        raise SemanticVerificationV1Error(
            "route-upper authority has the wrong role, route, or decision point"
        )
    for field in _UPPER_CONTEXT_FIELDS:
        if getattr(upper, field) != getattr(context, field):
            raise SemanticVerificationV1Error(
                f"route-upper authority/context mismatch at {field}"
            )
    if route_kind is RouteKind.LOCAL_ATTEMPT and not _same_ref(
        verified.binding.transaction_id, binding.transaction_id
    ):
        raise SemanticVerificationV1Error(
            "local route-upper authority belongs to another transaction"
        )
    if route_kind is RouteKind.DIRECT_FALLBACK and not isinstance(
        verified.binding.transaction_id, TypedNotApplicable
    ):
        raise SemanticVerificationV1Error(
            "fallback route-upper authority must carry typed-null transaction"
        )
    return upper


def _authority_causal_or_none(
    result: SemanticVerificationResultV1 | None,
    *,
    binding: AttestationContextV1,
    decision_point: DecisionPointV1,
) -> CausalEvidenceV1 | None:
    """Return causal evidence only when it came from semantic replay.

    Only the registered safe-chain preselection handler can currently emit
    this authority.  Every other profile returns ``None`` here without ever
    consulting a raw ``local_allowed`` flag.
    """

    if result is None:
        return None
    try:
        verified = require_semantic_verification_result_v1(
            result, SemanticRole.CAUSAL_SEARCH
        )
        _verify_result_context(verified, binding)
    except SemanticVerificationV1Error:
        return None
    if not isinstance(verified.artifact, CausalEvidenceV1):
        return None
    causal = verified.artifact
    if (
        verified.outcome != causal.outcome.value
        or verified.attestation.artifact_id != causal.causal_evidence_id
        or decision_point.causal_evidence_id != causal.causal_evidence_id
        or decision_point.frontier_snapshot_id != causal.frontier_snapshot_id
    ):
        return None
    return causal


def derive_guarded_marginal_route_decision_v1(
    *,
    context: RouteDecisionContextV1 | Mapping[str, Any],
    decision_point: DecisionPointV1 | Mapping[str, Any],
    fallback_upper_result: SemanticVerificationResultV1,
    local_upper_result: SemanticVerificationResultV1 | None,
    causal_result: SemanticVerificationResultV1 | None,
    binding: AttestationContextV1,
) -> MarginalRouteDecisionV1:
    """Construct the only decision admitted by authority-bearing inputs.

    An invalid or stale local-upper result is conservatively converted to
    ``FALLBACK/INVALID_LOCAL_UPPER``.  A missing local upper becomes
    ``FALLBACK/MISSING_LOCAL_UPPER``.  Missing, invalid, or negative causal
    authority forbids LOCAL.  The fallback upper itself is never optional:
    without an authoritative fallback bound there is no safe route decision.
    """

    parsed_context = _load_context(context)
    if binding.route_context != parsed_context:
        raise SemanticVerificationV1Error(
            "route-decision binding uses another route context"
        )
    parsed_point = _load_route_object(decision_point, DecisionPointV1)
    if (
        parsed_point.route_decision_context_id
        != parsed_context.route_decision_context_id
        or not _same_ref(binding.decision_point_id, parsed_point.decision_point_id)
    ):
        raise SemanticVerificationV1Error(
            "route-decision point is stale for the attested context"
        )
    fallback_upper = _authority_upper_or_error(
        fallback_upper_result,
        route_kind=RouteKind.DIRECT_FALLBACK,
        context=parsed_context,
        decision_point=parsed_point,
        binding=binding,
    )

    invalid_local = False
    local_upper: RouteUpperBoundEnvelopeV1 | None = None
    if local_upper_result is not None:
        try:
            local_upper = _authority_upper_or_error(
                local_upper_result,
                route_kind=RouteKind.LOCAL_ATTEMPT,
                context=parsed_context,
                decision_point=parsed_point,
                binding=binding,
            )
        except SemanticVerificationV1Error:
            invalid_local = True

    causal = _authority_causal_or_none(
        causal_result, binding=binding, decision_point=parsed_point
    )
    causal_ref: ContentRef = (
        causal.causal_evidence_id
        if causal is not None
        else TypedNotApplicable("no authoritative causal-search result")
    )
    local_ref: ContentRef = (
        local_upper.route_upper_bound_envelope_id
        if local_upper is not None
        else TypedNotApplicable(
            "local upper missing or rejected by semantic authority"
        )
    )
    if invalid_local:
        return MarginalRouteDecisionV1(
            parsed_point.decision_point_id,
            causal_ref,
            TypedNotApplicable("invalid local upper rejected by authority"),
            fallback_upper.route_upper_bound_envelope_id,
            RouteSelection.FALLBACK,
            RouteComparison.INVALID_LOCAL_UPPER,
            fallback_upper.route_upper_bound_envelope_id,
        )
    if causal is None or causal.local_allowed is not True:
        return MarginalRouteDecisionV1(
            parsed_point.decision_point_id,
            causal_ref,
            local_ref,
            fallback_upper.route_upper_bound_envelope_id,
            RouteSelection.FALLBACK,
            RouteComparison.LOCAL_FORBIDDEN,
            fallback_upper.route_upper_bound_envelope_id,
        )
    return MarginalRouteDecisionV1.select(
        parsed_point,
        fallback_upper,
        causal=causal,
        local_upper=local_upper,
    )


def verify_marginal_route_decision_semantics_v1(
    claimed_decision: MarginalRouteDecisionV1 | Mapping[str, Any],
    *,
    context: RouteDecisionContextV1 | Mapping[str, Any],
    decision_point: DecisionPointV1 | Mapping[str, Any],
    fallback_upper_result: SemanticVerificationResultV1,
    causal_result: SemanticVerificationResultV1 | None,
    local_upper_result: SemanticVerificationResultV1 | None,
    binding: AttestationContextV1,
    verification_work_record: CounterRecordV1 | Mapping[str, Any],
    registry: CounterRegistryV1 | None = None,
) -> SemanticVerificationResultV1:
    """Replay the authority-gated selector and reject a claimed result."""

    spec = require_implemented_role_v1(SemanticRole.ROUTE_DECISION)
    trusted_registry = _official_registry(registry)
    comparison_profile = official_comparison_profile_v1(trusted_registry)
    work = _verification_work_record(
        verification_work_record, spec, trusted_registry
    )
    parsed_context = _load_context(context)
    if binding.route_context != parsed_context:
        raise SemanticVerificationV1Error(
            "route-decision attestation context differs from replayed context"
        )
    if parsed_context.counter_registry_id != trusted_registry.registry_id:
        raise SemanticVerificationV1Error(
            "route context does not bind the official counter registry"
        )
    if parsed_context.comparison_profile_id != comparison_profile.comparison_profile_id:
        raise SemanticVerificationV1Error(
            "route context does not bind the official comparison profile"
        )

    parsed_point = _load_route_object(decision_point, DecisionPointV1)
    parsed_claim = _load_route_object(claimed_decision, MarginalRouteDecisionV1)

    if parsed_point.route_decision_context_id != parsed_context.route_decision_context_id:
        raise SemanticVerificationV1Error("decision point uses another route context")
    if not _same_ref(binding.decision_point_id, parsed_point.decision_point_id):
        raise SemanticVerificationV1Error(
            "attestation decision-point identity does not match replay input"
        )
    try:
        recomputed = derive_guarded_marginal_route_decision_v1(
            context=parsed_context,
            decision_point=parsed_point,
            fallback_upper_result=fallback_upper_result,
            local_upper_result=local_upper_result,
            causal_result=causal_result,
            binding=binding,
        )
    except ValueError as error:
        raise SemanticVerificationV1Error(
            f"route-decision semantic replay failed: {error}"
        ) from error
    if parsed_claim != recomputed:
        raise SemanticVerificationV1Error(
            "claimed marginal route decision differs from recomputed selection"
        )
    return _finish(
        artifact=recomputed,
        artifact_id=recomputed.route_decision_id,
        spec=spec,
        outcome=recomputed.selected_route.value,
        binding=binding,
        work=work,
        recomputed_evidence_ids=tuple(
            sorted(
                result.attestation.verification_attestation_id
                for result in (
                    fallback_upper_result,
                    local_upper_result,
                    causal_result,
                )
                if isinstance(result, SemanticVerificationResultV1)
                and result._authority is _VERIFIED_AUTHORITY
            )
        ),
    )


# A terminal class/code is semantic only when the listed role/outcome evidence
# has itself been replayed.  Hashes or well-formed attestation strings alone are
# intentionally insufficient.
TERMINAL_EVIDENCE_MATRIX_V1: Mapping[
    TerminalCode, tuple[tuple[SemanticRole, str], ...]
] = MappingProxyType(
    {
        TerminalCode.ABSTRACT_CERTIFIED: (
            (SemanticRole.WORK_VECTOR, "VALID"),
            (SemanticRole.ABSTRACT_AUDIT, "PASS"),
        ),
        TerminalCode.LOCAL_GROUND_RECOVERY: (
            (SemanticRole.WORK_VECTOR, "VALID"),
            (SemanticRole.ACTUAL_PROJECTION, "VALID"),
            (SemanticRole.ROUTE_UPPER, "VALID"),
            (SemanticRole.ROUTE_DECISION, "LOCAL"),
            (SemanticRole.LOCAL_SOLVER_RESULT, "CANDIDATE_FOUND"),
            (SemanticRole.POST_AUDIT, "CERTIFIED"),
        ),
        TerminalCode.FULL_GROUND_FALLBACK: (
            (SemanticRole.WORK_VECTOR, "VALID"),
            (SemanticRole.ACTUAL_PROJECTION, "VALID"),
            (SemanticRole.ROUTE_UPPER, "VALID"),
            (SemanticRole.ROUTE_DECISION, "FALLBACK"),
            (SemanticRole.GROUND_FALLBACK, "FEASIBLE_CERTIFIED"),
        ),
        TerminalCode.CACHED_EXACT_INFEASIBLE: (
            (SemanticRole.WORK_VECTOR, "VALID"),
            (SemanticRole.EXACT_CACHED_INFEASIBILITY, "IDENTICAL_MATCH"),
        ),
        TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: (
            (SemanticRole.WORK_VECTOR, "VALID"),
            (SemanticRole.ACTUAL_PROJECTION, "VALID"),
            (SemanticRole.ROUTE_UPPER, "VALID"),
            (SemanticRole.ROUTE_DECISION, "FALLBACK"),
            (SemanticRole.GROUND_FALLBACK, "INFEASIBLE_CERTIFIED"),
        ),
        # Only this noncertificate path is currently classifiable using solely
        # implemented evidence.  The others remain fail-closed below.
        TerminalCode.PROTOCOL_FAILURE: (
            (SemanticRole.WORK_VECTOR, "VALID"),
            (SemanticRole.PROTOCOL_ACCESS, "PROTOCOL_FAILURE"),
        ),
        TerminalCode.INTEGRITY_FAILURE: ((SemanticRole.WORK_VECTOR, "INVALID"),),
        TerminalCode.REBUILD_REQUIRED: (
            (SemanticRole.WORK_VECTOR, "VALID"),
            (SemanticRole.ACTUAL_PROJECTION, "VALID"),
            (SemanticRole.ROUTE_UPPER, "VALID"),
            (SemanticRole.ROUTE_DECISION, "LOCAL"),
            (SemanticRole.LOCAL_SOLVER_RESULT, "CANDIDATE_FOUND"),
            (SemanticRole.POST_AUDIT, "FAILED"),
        ),
        TerminalCode.FALLBACK_CAP_EXHAUSTED: (
            (SemanticRole.WORK_VECTOR, "VALID"),
            (SemanticRole.ACTUAL_PROJECTION, "VALID"),
            (SemanticRole.ROUTE_UPPER, "VALID"),
            (SemanticRole.ROUTE_DECISION, "FALLBACK"),
            (SemanticRole.GROUND_FALLBACK, "CAP_EXHAUSTED"),
        ),
        # No FQ7 budget-replay evidence role exists yet, so the class cannot be
        # semantically certified by this partial profile.
        TerminalCode.ATTEMPT_BUDGET_EXHAUSTED: (),
    }
)


def _require_authoritative_result(
    result: SemanticVerificationResultV1,
) -> SemanticVerificationResultV1:
    if (
        not isinstance(result, SemanticVerificationResultV1)
        or result._authority is not _VERIFIED_AUTHORITY
    ):
        raise SemanticVerificationV1Error(
            "terminal evidence was not produced by semantic replay"
        )
    return result


def require_semantic_verification_result_v1(
    result: SemanticVerificationResultV1,
    role: SemanticRole | str,
) -> SemanticVerificationResultV1:
    """Return an authority-bearing result only when its role is exact."""

    verified = _require_authoritative_result(result)
    expected = _role(role)
    if verified.role is not expected:
        raise SemanticVerificationV1Error(
            f"expected verified {expected.value}, got {verified.role.value}"
        )
    return verified


def require_terminal_classification_result_v1(
    result: SemanticVerificationResultV1,
) -> tuple[TerminalArtifactV1, TypedVerificationAttestationV1]:
    """Extract a terminal only from the terminal semantic authority."""

    verified = require_semantic_verification_result_v1(
        result, SemanticRole.TERMINAL_CLASSIFICATION
    )
    if not isinstance(verified.artifact, TerminalArtifactV1):
        raise SemanticVerificationV1Error(
            "terminal classification result does not carry TerminalArtifactV1"
        )
    terminal = verified.artifact
    if (
        verified.attestation.artifact_id != terminal.terminal_artifact_id
        or verified.outcome != terminal.terminal_class.value
        or verified.recomputed_evidence_ids != terminal.evidence_attestation_ids
    ):
        raise SemanticVerificationV1Error(
            "terminal classification result/attestation/artifact mismatch"
        )
    return terminal, verified.attestation


def verify_forbidden_access_violation_semantics_v1(
    violation: ForbiddenAccessViolationV1 | Mapping[str, Any],
    *,
    access_log: AccessEventLogV1 | Mapping[str, Any],
    profile: ProtocolSequenceProfileV1 | Mapping[str, Any],
    binding: AttestationContextV1,
    verification_work_record: CounterRecordV1 | Mapping[str, Any],
    route_decision_result: SemanticVerificationResultV1 | None = None,
    freeze_attestation: RouteDecisionFreezeAttestationV1 | Mapping[str, Any] | None = None,
    registry: CounterRegistryV1 | None = None,
) -> ProtocolVerificationResultV1:
    """Replay an access log and attest the exact first forbidden event."""

    spec = require_implemented_role_v1(SemanticRole.PROTOCOL_ACCESS)
    trusted_registry = _official_registry(registry)
    work = _verification_work_record(
        verification_work_record, spec, trusted_registry
    )
    try:
        parsed_violation = ForbiddenAccessViolationV1.from_dict(
            violation.to_dict()
            if isinstance(violation, ForbiddenAccessViolationV1)
            else violation
        )
        parsed_log = AccessEventLogV1.from_dict(
            access_log.to_dict()
            if isinstance(access_log, AccessEventLogV1)
            else access_log
        )
        parsed_profile = ProtocolSequenceProfileV1.from_dict(
            profile.to_dict()
            if isinstance(profile, ProtocolSequenceProfileV1)
            else profile
        )
        parsed_freeze = (
            None
            if freeze_attestation is None
            else RouteDecisionFreezeAttestationV1.from_dict(
                freeze_attestation.to_dict()
                if isinstance(
                    freeze_attestation, RouteDecisionFreezeAttestationV1
                )
                else freeze_attestation
            )
        )
    except (AccessProtocolV1Error, ValueError) as error:
        raise SemanticVerificationV1Error(
            f"invalid access-protocol evidence: {error}"
        ) from error
    context = binding.route_context
    if (
        parsed_log.route_attempt_id != context.route_attempt_id
        or parsed_log.decision_point_id != binding.decision_point_id
        or parsed_violation.route_attempt_id != context.route_attempt_id
        or parsed_violation.decision_point_id != binding.decision_point_id
        or parsed_violation.protocol_sequence_profile_id
        != parsed_profile.protocol_sequence_profile_id
    ):
        raise SemanticVerificationV1Error(
            "protocol evidence uses another attempt, decision point, or profile"
        )
    try:
        replay_access_protocol(
            parsed_log,
            parsed_profile,
            decision_result=route_decision_result,
            freeze_attestation=parsed_freeze,
        )
    except AccessProtocolViolation as error:
        recomputed = error.violation
    except AccessProtocolV1Error as error:
        raise SemanticVerificationV1Error(
            f"access-protocol replay failed: {error}"
        ) from error
    else:
        raise SemanticVerificationV1Error(
            "access log does not contain a replayable forbidden access"
        )
    if recomputed != parsed_violation:
        raise SemanticVerificationV1Error(
            "claimed forbidden-access violation differs from replay"
        )
    if binding.verified_at_protocol_step < recomputed.offending_sequence_number:
        raise SemanticVerificationV1Error(
            "protocol verification precedes the offending access"
        )
    attestation = ProtocolVerificationAttestationV1(
        artifact_id=recomputed.forbidden_access_violation_id,
        route_decision_context_id=context.route_decision_context_id,
        structural_id=context.structural_id,
        query_id=context.query_id,
        selected_plan_id=context.selected_plan_id,
        threshold_profile_id=context.threshold_profile_id,
        build_epoch_id=context.build_epoch_id,
        logical_occurrence_id=context.logical_occurrence_id,
        route_attempt_id=context.route_attempt_id,
        decision_point_id=binding.decision_point_id,
        transaction_id=binding.transaction_id,
        access_event_log_id=parsed_log.access_event_log_id,
        protocol_sequence_profile_id=parsed_profile.protocol_sequence_profile_id,
        semantic_verifier_id=spec.semantic_verifier_id,
        verification_profile_id=spec.verification_profile_id,
        verification_work_counter_record_id=work.record_id,
        verified_at_protocol_step=binding.verified_at_protocol_step,
    )
    return ProtocolVerificationResultV1(
        recomputed,
        attestation,
        work,
        _PROTOCOL_VERIFIED_AUTHORITY,
    )


def _verify_result_context(
    result: SemanticVerificationResultV1, binding: AttestationContextV1
) -> None:
    attestation = result.attestation
    context = binding.route_context
    expected = (
        context.route_decision_context_id,
        context.structural_id,
        context.query_id,
        context.selected_plan_id,
        context.threshold_profile_id,
        context.build_epoch_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
    )
    actual = (
        attestation.route_decision_context_id,
        attestation.structural_id,
        attestation.query_id,
        attestation.selected_plan_id,
        attestation.threshold_profile_id,
        attestation.build_epoch_id,
        attestation.logical_occurrence_id,
        attestation.route_attempt_id,
    )
    if actual != expected:
        raise SemanticVerificationV1Error(
            "terminal evidence uses another route/query/build context"
        )
    if not _same_ref(attestation.decision_point_id, binding.decision_point_id):
        raise SemanticVerificationV1Error(
            "terminal evidence uses another decision point"
        )
    if not _same_ref(attestation.transaction_id, binding.transaction_id):
        raise SemanticVerificationV1Error(
            "terminal evidence uses another transaction"
        )


def _verify_protocol_result_context(
    result: ProtocolVerificationResultV1,
    binding: AttestationContextV1,
) -> None:
    if (
        not isinstance(result, ProtocolVerificationResultV1)
        or result._authority is not _PROTOCOL_VERIFIED_AUTHORITY
    ):
        raise SemanticVerificationV1Error(
            "protocol evidence was not produced by access-log replay"
        )
    attestation = result.attestation
    context = binding.route_context
    expected = (
        context.route_decision_context_id,
        context.structural_id,
        context.query_id,
        context.selected_plan_id,
        context.threshold_profile_id,
        context.build_epoch_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
    )
    actual = (
        attestation.route_decision_context_id,
        attestation.structural_id,
        attestation.query_id,
        attestation.selected_plan_id,
        attestation.threshold_profile_id,
        attestation.build_epoch_id,
        attestation.logical_occurrence_id,
        attestation.route_attempt_id,
    )
    if actual != expected or not _same_ref(
        attestation.decision_point_id, binding.decision_point_id
    ) or not _same_ref(attestation.transaction_id, binding.transaction_id):
        raise SemanticVerificationV1Error(
            "protocol terminal evidence uses another route/query/build context"
        )


_MARGINAL_ROUTE_TERMINAL_CODES = frozenset(
    {
        TerminalCode.LOCAL_GROUND_RECOVERY,
        TerminalCode.FULL_GROUND_FALLBACK,
        TerminalCode.FULL_GROUND_EXACT_INFEASIBLE,
        TerminalCode.REBUILD_REQUIRED,
        TerminalCode.FALLBACK_CAP_EXHAUSTED,
    }
)

# The integrated Phase-3E runner performs four fixed post-execution checks
# before charging the route-specific semantic verifier records.  A terminal
# must replay this exact suffix rather than accepting any lower-cost native
# vector that happens to form a self-consistent marginal aggregate.
_RUNNER_MARGINAL_BASE_PROTOCOL_CHECKS_V1 = 4


def _single_terminal_result(
    by_role: Mapping[
        SemanticRole,
        list[SemanticVerificationResultV1 | ProtocolVerificationResultV1],
    ],
    role: SemanticRole,
) -> SemanticVerificationResultV1:
    values = by_role.get(role, ())
    if len(values) != 1 or not isinstance(values[0], SemanticVerificationResultV1):
        raise SemanticVerificationV1Error(
            f"terminal route chain requires exactly one {role.value} authority"
        )
    return values[0]


def _verify_marginal_terminal_route_chain_v1(
    terminal: TerminalArtifactV1,
    *,
    route_evidence: TerminalRouteEvidenceBundleV1 | None,
    by_role: Mapping[
        SemanticRole,
        list[SemanticVerificationResultV1 | ProtocolVerificationResultV1],
    ],
    binding: AttestationContextV1,
    registry: CounterRegistryV1,
) -> None:
    """Bind a route terminal to decision, work, upper, and access replay."""

    if not isinstance(route_evidence, TerminalRouteEvidenceBundleV1):
        raise SemanticVerificationV1Error(
            f"terminal {terminal.terminal_code.value} requires complete typed "
            "runner route evidence"
        )
    decision_result = _single_terminal_result(
        by_role, SemanticRole.ROUTE_DECISION
    )
    upper_result = _single_terminal_result(by_role, SemanticRole.ROUTE_UPPER)
    work_result = _single_terminal_result(by_role, SemanticRole.WORK_VECTOR)
    actual_result = _single_terminal_result(
        by_role, SemanticRole.ACTUAL_PROJECTION
    )
    if not isinstance(decision_result.artifact, MarginalRouteDecisionV1) or not isinstance(
        upper_result.artifact, RouteUpperBoundEnvelopeV1
    ) or not isinstance(work_result.artifact, WorkVectorV1) or not isinstance(
        actual_result.artifact, ComparisonVectorV1
    ):
        raise SemanticVerificationV1Error(
            "terminal route authorities carry the wrong artifact types"
        )
    decision = decision_result.artifact
    upper = upper_result.artifact
    expected_selection = (
        RouteSelection.LOCAL
        if terminal.terminal_code
        in {TerminalCode.LOCAL_GROUND_RECOVERY, TerminalCode.REBUILD_REQUIRED}
        else RouteSelection.FALLBACK
    )
    expected_kind = (
        RouteKind.LOCAL_ATTEMPT
        if expected_selection is RouteSelection.LOCAL
        else RouteKind.DIRECT_FALLBACK
    )
    if (
        decision.selected_route is not expected_selection
        or decision_result.outcome != expected_selection.value
        or decision.selected_upper_id != upper.route_upper_bound_envelope_id
        or upper.route_kind is not expected_kind
        or upper_result.outcome != "VALID"
        or upper_result.attestation.verification_attestation_id
        not in decision_result.recomputed_evidence_ids
    ):
        raise SemanticVerificationV1Error(
            "terminal route decision and selected upper are not one authority chain"
        )

    evidence = route_evidence
    profile = official_comparison_profile_v1(registry)
    actual_profile = official_actual_projection_profile_v1(registry, profile)
    try:
        verify_recorded_work_v1(
            evidence.execution_work,
            expected_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
            registry=registry,
            comparison_profile=profile,
        )
        verify_recorded_work_v1(
            evidence.verification_suffix_work,
            expected_scope=ActualWorkScope.MARGINAL_ROUTE_VERIFICATION,
            registry=registry,
            comparison_profile=profile,
        )
        aggregate = verify_marginal_work_aggregate_v1(
            evidence.aggregate_marginal_work,
            subject_id=evidence.execution_work.work_vector.subject_id,
            route_kind=evidence.execution_work.work_vector.route_kind,
            execution=(
                evidence.execution_work.work_vector,
                evidence.execution_work.comparison_vector,
                evidence.execution_work.actual_projection_proof,
            ),
            verification_suffix=(
                evidence.verification_suffix_work.work_vector,
                evidence.verification_suffix_work.comparison_vector,
                evidence.verification_suffix_work.actual_projection_proof,
            ),
            registry=registry,
            comparison_profile=profile,
            actual_profile=actual_profile,
        )
    except (MarginalAccountingV1Error, ValueError) as error:
        raise SemanticVerificationV1Error(
            f"terminal marginal source-chain replay failed: {error}"
        ) from error

    route_verification_roles = (
        (
            SemanticRole.LOCAL_SOLVER_RESULT,
            SemanticRole.POST_AUDIT,
        )
        if expected_selection is RouteSelection.LOCAL
        else (SemanticRole.GROUND_FALLBACK,)
    )
    expected_suffix_values = {
        path: 0
        for path in evidence.verification_suffix_work.work_vector.values
    }
    expected_suffix_values["common.protocol_checks"] = (
        _RUNNER_MARGINAL_BASE_PROTOCOL_CHECKS_V1
    )
    for role in route_verification_roles:
        semantic_result = _single_terminal_result(by_role, role)
        record = semantic_result.verification_work_record
        expected_suffix_values[record.path] += record.value
    if dict(evidence.verification_suffix_work.work_vector.values) != (
        expected_suffix_values
    ):
        raise SemanticVerificationV1Error(
            "terminal verification suffix does not equal the runner's four "
            "checks plus exact route-specific semantic verifier work"
        )

    aggregate_work = aggregate.aggregate_work_vector
    aggregate_comparison = aggregate.aggregate_comparison_vector
    aggregate_projection = aggregate.aggregate_projection_proof
    aggregation_proof = aggregate.aggregation_proof
    if (
        aggregate_work.route_kind.value != expected_kind.value
        or work_result.artifact != aggregate_work
        or work_result.attestation.artifact_id != aggregate_work.work_vector_id
        or actual_result.artifact != aggregate_comparison
        or actual_result.attestation.artifact_id
        != aggregate_comparison.comparison_vector_id
        or actual_result.recomputed_evidence_ids
        != (aggregate_projection.actual_projection_proof_id,)
        or terminal.actual_work_vector_id != aggregate_work.work_vector_id
        or terminal.actual_comparison_vector_id
        != aggregate_comparison.comparison_vector_id
        or terminal.actual_projection_proof_id
        != aggregate_projection.actual_projection_proof_id
        or terminal.marginal_work_aggregation_proof_id
        != aggregation_proof.marginal_work_aggregation_proof_id
    ):
        raise SemanticVerificationV1Error(
            "terminal actual work/projection does not bind the runner aggregate"
        )

    upper_values = dict(upper.upper_bounds)
    if tuple(sorted(upper_values)) != SHARED_AXES or any(
        aggregate_comparison.value(axis) > upper_values[axis]
        for axis in SHARED_AXES
    ):
        raise SemanticVerificationV1Error(
            "terminal aggregate violates or cannot replay the selected upper"
        )

    try:
        access_log = AccessEventLogV1.from_dict(evidence.access_log.to_dict())
        freeze = RouteDecisionFreezeAttestationV1.from_dict(
            evidence.freeze_attestation.to_dict()
        )
        protocol_profile = ProtocolSequenceProfileV1.from_dict(
            evidence.protocol_profile.to_dict()
        )
        replay_access_protocol(
            access_log,
            protocol_profile,
            decision_result=decision_result,
            freeze_attestation=freeze,
        )
    except (AccessProtocolViolation, AccessProtocolV1Error, ValueError) as error:
        raise SemanticVerificationV1Error(
            f"terminal successful access-protocol replay failed: {error}"
        ) from error
    if (
        freeze.route_decision_id != decision.route_decision_id
        or freeze.route_decision_verification_attestation_id
        != decision_result.attestation.verification_attestation_id
        or freeze.selected_route is not expected_selection
        or access_log.route_decision_id != decision.route_decision_id
        or access_log.route_decision_freeze_attestation_id
        != freeze.route_decision_freeze_attestation_id
        or terminal.route_decision_freeze_attestation_id
        != freeze.route_decision_freeze_attestation_id
        or terminal.access_event_log_id != access_log.access_event_log_id
        or binding.verified_at_protocol_step < len(access_log.events)
    ):
        raise SemanticVerificationV1Error(
            "terminal route freeze/access identities are stale or spliced"
        )
    prefreeze_events = access_log.events[: freeze.last_preselection_sequence]
    if (
        len(prefreeze_events) != len(PRESELECTION_READ_OPERATIONS)
        or len({row.operation for row in prefreeze_events})
        != len(prefreeze_events)
        or {row.operation for row in prefreeze_events}
        != set(PRESELECTION_READ_OPERATIONS)
    ):
        raise SemanticVerificationV1Error(
            "terminal successful access evidence omits a frozen preselection read"
        )

    events = access_log.events
    if expected_selection is RouteSelection.FALLBACK:
        from acfqp.phase3e_fallback_v1 import GroundFallbackResultV1

        route_result = _single_terminal_result(
            by_role, SemanticRole.GROUND_FALLBACK
        )
        ground = route_result.artifact
        if not isinstance(ground, GroundFallbackResultV1) or (
            ground.work_vector_id
            != evidence.execution_work.work_vector.work_vector_id
            or ground.route_decision_id != decision.route_decision_id
            or ground.selected_upper_id != upper.route_upper_bound_envelope_id
        ):
            raise SemanticVerificationV1Error(
                "fallback semantic result is not bound to selected execution work"
            )
        result_events = tuple(
            row
            for row in events
            if row.operation is AccessOperation.FALLBACK_RESULT_ARTIFACT
        )
        if (
            sum(
                row.operation
                in {
                    AccessOperation.FALLBACK_SOLVER_INVOCATION,
                    AccessOperation.FALLBACK_WORKER_LAUNCH,
                }
                for row in events
            )
            != 1
            or len(result_events) != 1
            or result_events[0].artifact_id != ground.ground_fallback_result_id
            or result_events[0] is not events[-1]
            or sum(
                row.operation is AccessOperation.KERNEL_STEP for row in events
            )
            != evidence.execution_work.work_vector.value(
                "fallback.ground_steps"
            )
            or sum(
                row.operation is AccessOperation.GROUND_OUTCOME_ENUMERATION
                for row in events
            )
            != evidence.execution_work.work_vector.value(
                "fallback.ground_steps"
            )
        ):
            raise SemanticVerificationV1Error(
                "fallback access trace does not bind its semantic result"
            )
    else:
        from acfqp.phase3e_local_semantics_v1 import (
            LocalTransactionResultV1,
            PostAuditCertificateV1,
        )

        local_result = _single_terminal_result(
            by_role, SemanticRole.LOCAL_SOLVER_RESULT
        )
        post_result = _single_terminal_result(by_role, SemanticRole.POST_AUDIT)
        local = local_result.artifact
        post = post_result.artifact
        if not isinstance(local, LocalTransactionResultV1) or not isinstance(
            post, PostAuditCertificateV1
        ) or (
            local.work_vector_id
            != evidence.execution_work.work_vector.work_vector_id
            or local.selected_upper_id != upper.route_upper_bound_envelope_id
            or post.work_vector_id != local.work_vector_id
            or post.local_transaction_result_id
            != local.local_transaction_result_id
        ):
            raise SemanticVerificationV1Error(
                "local semantic/post-audit results do not bind selected execution work"
            )
        capability_events = tuple(
            row
            for row in events
            if row.operation is AccessOperation.LOCAL_CAPABILITY_ARTIFACT
        )
        local_events = tuple(
            row
            for row in events
            if row.operation is AccessOperation.LOCAL_WORKER_RESULT_ARTIFACT
        )
        stitch_events = tuple(
            row
            for row in events
            if row.operation is AccessOperation.LOCAL_STITCH_ARTIFACT
        )
        post_events = tuple(
            row
            for row in events
            if row.operation is AccessOperation.LOCAL_POSTAUDIT_ARTIFACT
        )
        if (
            local_execution_stages_v1(
                events, freeze_after_sequence=freeze.last_preselection_sequence
            )
            != (1, 2, 3, 4, 5)
            or any(
                sum(row.operation is operation for row in events) != 1
                for operation in (
                    AccessOperation.LOCAL_SLICE_MATERIALIZATION,
                    AccessOperation.LOCAL_CAPABILITY_COMPILATION,
                    AccessOperation.LOCAL_WORKER_LAUNCH,
                    AccessOperation.LOCAL_PATCH_STITCH,
                    AccessOperation.LOCAL_POSTAUDIT,
                )
            )
            or len(capability_events) != 1
            or capability_events[0].artifact_id != local.capability_binding_id
            or len(local_events) != 1
            or local_events[0].artifact_id != local.worker_result_binding_id
            or len(stitch_events) != 1
            or stitch_events[0].artifact_id != local.stitched_plan_binding_id
            or len(post_events) != 1
            or post_events[0].artifact_id != post.post_audit_certificate_id
            or post_events[0] is not events[-1]
            or sum(
                row.operation is AccessOperation.KERNEL_STEP for row in events
            )
            != (
                evidence.execution_work.work_vector.value(
                    "local.materialization_ground_steps"
                )
                + evidence.execution_work.work_vector.value(
                    "local.postaudit_ground_steps"
                )
            )
            or sum(
                row.operation is AccessOperation.GROUND_OUTCOME_ENUMERATION
                for row in events
            )
            != (
                evidence.execution_work.work_vector.value(
                    "local.materialization_ground_steps"
                )
                + evidence.execution_work.work_vector.value(
                    "local.postaudit_ground_steps"
                )
            )
        ):
            raise SemanticVerificationV1Error(
                "local access trace is incomplete or does not bind semantic artifacts"
            )


def verify_terminal_classification_semantics_v1(
    terminal: TerminalArtifactV1 | Mapping[str, Any],
    *,
    evidence_results: Sequence[
        SemanticVerificationResultV1 | ProtocolVerificationResultV1
    ],
    binding: AttestationContextV1,
    verification_work_record: CounterRecordV1 | Mapping[str, Any],
    route_evidence: TerminalRouteEvidenceBundleV1 | None = None,
    registry: CounterRegistryV1 | None = None,
) -> SemanticVerificationResultV1:
    """Verify terminal class/code from replayed role evidence, never hash-only IDs."""

    spec = require_implemented_role_v1(SemanticRole.TERMINAL_CLASSIFICATION)
    trusted_registry = _official_registry(registry)
    work = _verification_work_record(
        verification_work_record, spec, trusted_registry
    )
    parsed = _load_route_object(terminal, TerminalArtifactV1)
    context = binding.route_context
    if (
        parsed.route_decision_context_id != context.route_decision_context_id
        or parsed.logical_occurrence_id != context.logical_occurrence_id
        or parsed.route_attempt_id != context.route_attempt_id
        or not _same_ref(parsed.decision_point_id, binding.decision_point_id)
        or not _same_ref(parsed.transaction_id, binding.transaction_id)
    ):
        raise SemanticVerificationV1Error(
            "terminal artifact identity differs from attestation context"
        )

    results = tuple(evidence_results)
    for row in results:
        if isinstance(row, ProtocolVerificationResultV1):
            _verify_protocol_result_context(row, binding)
        else:
            _require_authoritative_result(row)
    attestations = tuple(row.attestation for row in results)
    typed_attestations = tuple(
        row for row in attestations if isinstance(row, TypedVerificationAttestationV1)
    )
    try:
        verify_unique_attestation_roles(typed_attestations)
    except ValueError as error:
        raise SemanticVerificationV1Error(
            f"terminal evidence reuses an artifact across roles: {error}"
        ) from error
    roles_by_artifact: dict[str, SemanticRole] = {}
    for result in results:
        artifact_id = result.attestation.artifact_id
        existing = roles_by_artifact.setdefault(artifact_id, result.role)
        if existing is not result.role:
            raise SemanticVerificationV1Error(
                "terminal evidence reuses one artifact across incompatible roles"
            )
        if isinstance(result, ProtocolVerificationResultV1):
            _verification_work_record(
                result.verification_work_record,
                semantic_verifier_spec_v1(SemanticRole.PROTOCOL_ACCESS),
                trusted_registry,
            )
        else:
            _verify_result_context(result, binding)
            # Recheck the transported attestation against the authority-bearing
            # runtime result; caller-supplied IDs/outcomes are insufficient.
            verify_typed_attestation_v1(
                result.attestation,
                authority_result=result,
                registry=trusted_registry,
            )

    supplied_ids = tuple(sorted(row.verification_attestation_id for row in attestations))
    if supplied_ids != parsed.evidence_attestation_ids:
        raise SemanticVerificationV1Error(
            "terminal evidence IDs are missing, opaque, or not exactly the replayed attestations"
        )
    by_role: dict[
        SemanticRole,
        list[SemanticVerificationResultV1 | ProtocolVerificationResultV1],
    ] = {}
    for result in results:
        by_role.setdefault(result.role, []).append(result)

    requirements = TERMINAL_EVIDENCE_MATRIX_V1[parsed.terminal_code]
    if parsed.terminal_code is TerminalCode.ATTEMPT_BUDGET_EXHAUSTED:
        raise SemanticVerifierNotImplementedError("TRUSTED_BUDGET_REPLAY")
    for role, required_outcome in requirements:
        role_spec = semantic_verifier_spec_v1(role)
        if not role_spec.implemented or required_outcome == "INVALID":
            raise SemanticVerifierNotImplementedError(role.value)
        matches = [row for row in by_role.get(role, ()) if row.outcome == required_outcome]
        if len(matches) != 1:
            raise SemanticVerificationV1Error(
                f"terminal {parsed.terminal_code.value} requires exactly one "
                f"semantically verified {role.value}={required_outcome} evidence"
            )
    required_roles = {role for role, _ in requirements}
    if set(by_role) != required_roles or any(
        len(rows) != 1 for rows in by_role.values()
    ):
        raise SemanticVerificationV1Error(
            "terminal evidence roles must exactly match its class/code contract"
        )
    work_vectors = by_role.get(SemanticRole.WORK_VECTOR, ())
    if len(work_vectors) != 1:
        raise SemanticVerificationV1Error(
            "terminal classification requires exactly one replayed WorkVector"
        )
    if work_vectors[0].attestation.artifact_id != parsed.actual_work_vector_id:
        raise SemanticVerificationV1Error(
            "terminal actual_work_vector_id differs from replayed WorkVector evidence"
        )

    route_refs = (
        parsed.actual_comparison_vector_id,
        parsed.actual_projection_proof_id,
        parsed.marginal_work_aggregation_proof_id,
        parsed.route_decision_freeze_attestation_id,
        parsed.access_event_log_id,
    )
    if parsed.terminal_code in _MARGINAL_ROUTE_TERMINAL_CODES:
        if any(isinstance(row, TypedNotApplicable) for row in route_refs):
            raise SemanticVerificationV1Error(
                "marginal route terminal omits required typed route evidence refs"
            )
        _verify_marginal_terminal_route_chain_v1(
            parsed,
            route_evidence=route_evidence,
            by_role=by_role,
            binding=binding,
            registry=trusted_registry,
        )
    elif route_evidence is not None or any(
        not isinstance(row, TypedNotApplicable) for row in route_refs
    ):
        raise SemanticVerificationV1Error(
            "non-route terminal cannot claim marginal runner evidence"
        )

    return _finish(
        artifact=parsed,
        artifact_id=parsed.terminal_artifact_id,
        spec=spec,
        outcome=parsed.terminal_class.value,
        binding=binding,
        work=work,
        recomputed_evidence_ids=supplied_ids,
    )


def reject_unimplemented_semantic_claim_v1(
    role: SemanticRole | str, *, claimed_outcome: str
) -> None:
    """Fail closed even when an unimplemented role carries a legal outcome string."""

    spec = semantic_verifier_spec_v1(role)
    if claimed_outcome not in spec.outcomes:
        raise SemanticVerificationV1Error(
            f"invalid claimed outcome {claimed_outcome!r} for {spec.role.value}"
        )
    if not spec.implemented:
        raise SemanticVerifierNotImplementedError(spec.role.value)
    raise SemanticVerificationV1Error(
        f"{spec.role.value} is implemented; call its semantic replay handler"
    )


__all__ = [
    "AttestationContextV1",
    "PROFILE_KEY",
    "ProtocolVerificationAttestationV1",
    "ProtocolVerificationResultV1",
    "SCHEMA_VERSION",
    "SEMANTIC_VERIFIER_REGISTRY_V1",
    "SemanticRole",
    "SemanticVerificationResultV1",
    "SemanticVerificationV1Error",
    "SemanticVerifierNotImplementedError",
    "SemanticVerifierSpecV1",
    "TERMINAL_EVIDENCE_MATRIX_V1",
    "TerminalRouteEvidenceBundleV1",
    "VERIFICATION_PROFILE_ID",
    "derive_guarded_marginal_route_decision_v1",
    "reject_unimplemented_semantic_claim_v1",
    "require_semantic_verification_result_v1",
    "require_terminal_classification_result_v1",
    "require_implemented_role_v1",
    "semantic_verifier_spec_v1",
    "verify_actual_projection_semantics_v1",
    "verify_forbidden_access_violation_semantics_v1",
    "verify_ground_fallback_semantics_v1",
    "verify_local_transaction_result_semantics_v1",
    "verify_marginal_route_decision_semantics_v1",
    "verify_post_audit_semantics_v1",
    "verify_route_upper_semantics_v1",
    "verify_safe_chain_fallback_cardinality_semantics_v1",
    "verify_safe_chain_local_cardinality_semantics_v1",
    "verify_safe_chain_local_causal_semantics_v1",
    "verify_terminal_classification_semantics_v1",
    "verify_typed_attestation_v1",
    "verify_work_vector_semantics_v1",
]
