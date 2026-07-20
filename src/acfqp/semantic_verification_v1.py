"""Fail-closed semantic verification core for the partial Phase-3E FQ7 profile.

Typed attestations are outputs of semantic replay, not substitutes for it.  The
core implemented here deliberately covers only authorities that already have a
replayable V1 implementation:

* native ``WorkVectorV1`` materialization against the official counter registry;
* exact actual-work projection from that native vector;
* forbidden-access protocol replay; and
* terminal class/code validation against semantically replayed evidence.

The remaining FQ7 roles are registered so that their schema and outcome
vocabularies cannot drift, but they fail closed with ``NOT_IMPLEMENTED``.  In
particular, a well-formed attestation carrying a plausible result string is not
accepted as evidence for one of those roles.

This is a partial verification profile.  It does not run, and must not be used
to claim, the full FQ7 or Phase-3E official gate.
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
    WorkVectorV1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    official_actual_projection_profile_v1,
    verify_actual_projection_v1,
)
from acfqp.access_protocol_v1 import (
    AccessEventLogV1,
    AccessProtocolV1Error,
    AccessProtocolViolation,
    ForbiddenAccessViolationV1,
    ProtocolSequenceProfileV1,
    RouteDecisionFreezeAttestationV1,
    replay_access_protocol,
)
from acfqp.phase3e_ids import (
    TYPED_VERIFICATION_ATTESTATION_DOMAIN,
    content_id,
    parse_content_id,
)
from acfqp.routing_v1 import (
    CausalEvidenceV1,
    DecisionPointV1,
    MarginalRouteDecisionV1,
    RouteDecisionContextV1,
    RouteSelection,
    RouteUpperBoundEnvelopeV1,
    TerminalArtifactV1,
    TerminalClass,
    TerminalCode,
    TypedNotApplicable,
    TypedVerificationAttestationV1,
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
        implemented=False,
    ),
    _spec(
        SemanticRole.CARDINALITY_EVIDENCE,
        "CardinalityEvidenceV1",
        ("VALID", "INVALID"),
        implemented=False,
    ),
    _spec(
        SemanticRole.ROUTE_UPPER,
        "RouteUpperBoundEnvelopeV1",
        ("VALID", "INVALID"),
        implemented=False,
    ),
    _spec(
        SemanticRole.ROUTE_DECISION,
        "RouteDecisionV1",
        ("LOCAL", "FALLBACK", "INVALID"),
        # Route selection is not authoritative until both route uppers have
        # themselves been semantically replayed.  The current profile has no
        # implemented ROUTE_UPPER authority, so accepting a merely
        # self-consistent selector object here would create a trust cycle.
        implemented=False,
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
        implemented=False,
    ),
    _spec(
        SemanticRole.POST_AUDIT,
        "PostAuditCertificateV1",
        ("CERTIFIED", "FAILED", "INVALID"),
        implemented=False,
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
        implemented=False,
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


def _load_route_object(value: Any, expected_type: type[Any]) -> Any:
    document = value.to_dict() if isinstance(value, expected_type) else value
    try:
        return expected_type.from_dict(document)
    except ValueError as error:
        raise SemanticVerificationV1Error(
            f"invalid {expected_type.__name__}: {error}"
        ) from error


def verify_marginal_route_decision_semantics_v1(
    claimed_decision: MarginalRouteDecisionV1 | Mapping[str, Any],
    *,
    context: RouteDecisionContextV1 | Mapping[str, Any],
    decision_point: DecisionPointV1 | Mapping[str, Any],
    fallback_upper: RouteUpperBoundEnvelopeV1 | Mapping[str, Any],
    causal: CausalEvidenceV1 | Mapping[str, Any] | None,
    local_upper: RouteUpperBoundEnvelopeV1 | Mapping[str, Any] | None,
    binding: AttestationContextV1,
    verification_work_record: CounterRecordV1 | Mapping[str, Any],
    registry: CounterRegistryV1 | None = None,
) -> SemanticVerificationResultV1:
    """Re-run the marginal selector and reject a claimed route/result string."""

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
    parsed_fallback = _load_route_object(
        fallback_upper, RouteUpperBoundEnvelopeV1
    )
    parsed_causal = (
        None if causal is None else _load_route_object(causal, CausalEvidenceV1)
    )
    parsed_local = (
        None
        if local_upper is None
        else _load_route_object(local_upper, RouteUpperBoundEnvelopeV1)
    )
    parsed_claim = _load_route_object(claimed_decision, MarginalRouteDecisionV1)

    if parsed_point.route_decision_context_id != parsed_context.route_decision_context_id:
        raise SemanticVerificationV1Error("decision point uses another route context")
    if not _same_ref(binding.decision_point_id, parsed_point.decision_point_id):
        raise SemanticVerificationV1Error(
            "attestation decision-point identity does not match replay input"
        )
    for upper in (parsed_fallback,) + (() if parsed_local is None else (parsed_local,)):
        for field in _UPPER_CONTEXT_FIELDS:
            if getattr(upper, field) != getattr(parsed_context, field):
                raise SemanticVerificationV1Error(
                    f"route upper/context mismatch at {field}"
                )
    point_causal = parsed_point.causal_evidence_id
    if parsed_causal is None:
        if not isinstance(point_causal, TypedNotApplicable):
            raise SemanticVerificationV1Error(
                "decision point binds causal evidence that was not supplied"
            )
    else:
        if point_causal != parsed_causal.causal_evidence_id:
            raise SemanticVerificationV1Error(
                "causal evidence does not match the frozen decision point"
            )
        if parsed_point.frontier_snapshot_id != parsed_causal.frontier_snapshot_id:
            raise SemanticVerificationV1Error(
                "causal evidence uses another frontier snapshot"
            )

    try:
        recomputed = MarginalRouteDecisionV1.select(
            parsed_point,
            parsed_fallback,
            causal=parsed_causal,
            local_upper=parsed_local,
        )
    except ValueError as error:
        raise SemanticVerificationV1Error(
            f"route-decision semantic replay failed: {error}"
        ) from error
    if parsed_claim != recomputed:
        raise SemanticVerificationV1Error(
            "claimed marginal route decision differs from recomputed selection"
        )
    if recomputed.selected_route is RouteSelection.LOCAL:
        assert parsed_local is not None  # established by selector
        if not _same_ref(binding.transaction_id, parsed_local.transaction_id):
            raise SemanticVerificationV1Error(
                "local route attestation uses another transaction"
            )
    return _finish(
        artifact=recomputed,
        artifact_id=recomputed.route_decision_id,
        spec=spec,
        outcome=recomputed.selected_route.value,
        binding=binding,
        work=work,
        recomputed_evidence_ids=tuple(
            item
            for item in (
                parsed_fallback.route_upper_bound_envelope_id,
                parsed_local.route_upper_bound_envelope_id
                if parsed_local is not None
                else None,
                parsed_causal.causal_evidence_id if parsed_causal is not None else None,
            )
            if item is not None
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
            (SemanticRole.LOCAL_SOLVER_RESULT, "CANDIDATE_FOUND"),
            (SemanticRole.POST_AUDIT, "CERTIFIED"),
        ),
        TerminalCode.FULL_GROUND_FALLBACK: (
            (SemanticRole.WORK_VECTOR, "VALID"),
            (SemanticRole.GROUND_FALLBACK, "FEASIBLE_CERTIFIED"),
        ),
        TerminalCode.CACHED_EXACT_INFEASIBLE: (
            (SemanticRole.WORK_VECTOR, "VALID"),
            (SemanticRole.EXACT_CACHED_INFEASIBILITY, "IDENTICAL_MATCH"),
        ),
        TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: (
            (SemanticRole.WORK_VECTOR, "VALID"),
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
            (SemanticRole.POST_AUDIT, "FAILED"),
        ),
        TerminalCode.FALLBACK_CAP_EXHAUSTED: (
            (SemanticRole.WORK_VECTOR, "VALID"),
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


def verify_terminal_classification_semantics_v1(
    terminal: TerminalArtifactV1 | Mapping[str, Any],
    *,
    evidence_results: Sequence[
        SemanticVerificationResultV1 | ProtocolVerificationResultV1
    ],
    binding: AttestationContextV1,
    verification_work_record: CounterRecordV1 | Mapping[str, Any],
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
    work_vectors = by_role.get(SemanticRole.WORK_VECTOR, ())
    if len(work_vectors) != 1:
        raise SemanticVerificationV1Error(
            "terminal classification requires exactly one replayed WorkVector"
        )
    if work_vectors[0].attestation.artifact_id != parsed.actual_work_vector_id:
        raise SemanticVerificationV1Error(
            "terminal actual_work_vector_id differs from replayed WorkVector evidence"
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
    "VERIFICATION_PROFILE_ID",
    "reject_unimplemented_semantic_claim_v1",
    "require_semantic_verification_result_v1",
    "require_terminal_classification_result_v1",
    "require_implemented_role_v1",
    "semantic_verifier_spec_v1",
    "verify_actual_projection_semantics_v1",
    "verify_forbidden_access_violation_semantics_v1",
    "verify_marginal_route_decision_semantics_v1",
    "verify_terminal_classification_semantics_v1",
    "verify_typed_attestation_v1",
    "verify_work_vector_semantics_v1",
]
