"""Authoritative FQ6 actual-work projection for Phase 3E.

The route-comparison profile describes *which resources are comparable*.
This module adds the separate authority required for actual work:

``CounterRecordV1 -> WorkVectorV1 -> ActualProjectionProfileV1 ->
ComparisonVectorV1``.

Every verification entry point recomputes the comparison vector from the exact
work vector.  A self-consistent comparison-vector document is not evidence by
itself.  Common-prefix work and marginal selected-route work are distinct
scopes: upper compliance is legal only for a marginal vector whose ``common.*``
leaves are native zero.  Failed-local and subsequent fallback work remain
separate vectors; ``OccurrenceWorkSumV1`` retains all input references and
derives a reducer-aware occurrence aggregate (sum for traffic/events, max for
peak capacity).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from acfqp.accounting_v1 import (
    AccountingV1Error,
    ComparisonProfileV1,
    ComparisonVectorV1,
    CounterRegistryV1,
    LaneEnum,
    ProjectionTermV1,
    ReducerEnum,
    RouteKindEnum,
    SHARED_AXES,
    WorkVectorV1,
    derive_comparison_vector_v1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.phase3e_ids import (
    ACTUAL_PROJECTION_PROFILE_DOMAIN,
    ACTUAL_PROJECTION_PROOF_DOMAIN,
    COMPARISON_VECTOR_DOMAIN,
    OCCURRENCE_WORK_SUM_DOMAIN,
    WORK_VECTOR_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.route_upper_formula_v1 import (
    RouteUpperDerivationProofV1,
    RouteUpperFormulaV1,
    verify_route_upper_derivation_v1,
)
from acfqp.routing_v1 import (
    CardinalityEvidenceV1,
    CausalEvidenceV1,
    DecisionPointV1,
    MarginalRouteDecisionV1,
    RouteCapProfileV1,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    RouteUpperBoundEnvelopeV1,
    TransactionV1,
    TypedNotApplicable,
)


SCHEMA_VERSION = "1.0.0"
ACTUAL_PROJECTION_PROFILE_KEY = "actual_projection_profile_v1"
EXACT_OPERATIONAL_MAPPING = "EXACT_OFFICIAL_OPERATIONAL_MAPPING"
SEPARATE_COMMON_PREFIX = "SEPARATE_COMMON_PREFIX_WORK_VECTOR_REQUIRED"
UPPER_BOUND_VIOLATION = "UPPER_BOUND_VIOLATION"
PROTOCOL_FAILURE = "PROTOCOL_FAILURE"
WITHIN_SELECTED_UPPER = "WITHIN_SELECTED_UPPER"


class ActualAccountingV1Error(ValueError):
    """An FQ6 artifact, reference, or projection is not authoritative."""


class ActualAccountingProtocolError(ActualAccountingV1Error):
    """A result violates the actual-work protocol."""

    violation_code = "ACTUAL_ACCOUNTING_PROTOCOL_VIOLATION"
    terminal_code = PROTOCOL_FAILURE

    def __init__(self, message: str, *, violated_axes: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.violated_axes = violated_axes


class UpperBoundViolationError(ActualAccountingProtocolError):
    """Actual selected-route work exceeds its frozen pre-execution upper."""

    violation_code = UPPER_BOUND_VIOLATION
    terminal_code = PROTOCOL_FAILURE


class ActualWorkScope(str, Enum):
    COMMON_PREFIX = "COMMON_PREFIX"
    MARGINAL_ROUTE_EXECUTION = "MARGINAL_ROUTE_EXECUTION"
    MARGINAL_ROUTE_VERIFICATION = "MARGINAL_ROUTE_VERIFICATION"
    MARGINAL_ROUTE_AGGREGATE = "MARGINAL_ROUTE_AGGREGATE"
    REBUILD_EXECUTION = "REBUILD_EXECUTION"
    EVALUATION_REPLAY = "EVALUATION_REPLAY"


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ActualAccountingV1Error(
            f"{field} must be a full Phase-3E content ID"
        ) from error


def _token(value: Any, field: str) -> str:
    if type(value) is not str or not value:
        raise ActualAccountingV1Error(f"{field} must be a nonempty string")
    return value


def _enum(value: Any, enum_type: type[Enum], field: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ActualAccountingV1Error(f"invalid {field}: {value!r}") from error


def _fields(
    document: Mapping[str, Any], expected: set[str], context: str
) -> None:
    try:
        require_exact_fields(document, expected, context=context)
    except ValueError as error:
        raise ActualAccountingV1Error(str(error)) from error


def _central_work_vector_id(vector: WorkVectorV1) -> str:
    expected = content_id(WORK_VECTOR_DOMAIN, vector._payload())
    if vector.work_vector_id != expected:
        raise ActualAccountingV1Error(
            "WorkVectorV1 does not use the registered work-vector domain"
        )
    return expected


def _central_comparison_vector_id(vector: ComparisonVectorV1) -> str:
    expected = content_id(COMPARISON_VECTOR_DOMAIN, vector._payload())
    if vector.comparison_vector_id != expected:
        raise ActualAccountingV1Error(
            "ComparisonVectorV1 does not use the registered comparison-vector domain"
        )
    return expected


@dataclass(frozen=True, slots=True)
class ActualProjectionProfileV1:
    """Frozen operational projection distinct from route-upper formulae."""

    profile_key: str
    schema_version: str
    counter_registry_id: str
    comparison_profile_id: str
    mapping_kind: str
    common_prefix_policy: str
    source_lane: LaneEnum
    terms: tuple[ProjectionTermV1, ...]

    def __post_init__(self) -> None:
        _token(self.profile_key, "profile_key")
        _token(self.schema_version, "schema_version")
        _cid(self.counter_registry_id, "counter_registry_id")
        _cid(self.comparison_profile_id, "comparison_profile_id")
        if self.mapping_kind != EXACT_OPERATIONAL_MAPPING:
            raise ActualAccountingV1Error("actual projection must use the exact mapping")
        if self.common_prefix_policy != SEPARATE_COMMON_PREFIX:
            raise ActualAccountingV1Error(
                "actual projection must keep common-prefix work separate"
            )
        object.__setattr__(
            self, "source_lane", _enum(self.source_lane, LaneEnum, "source_lane")
        )
        if self.source_lane is not LaneEnum.OPERATIONAL:
            raise ActualAccountingV1Error(
                "official actual projection accepts operational work only"
            )
        if tuple(sorted(self.terms, key=lambda term: term.source_leaf)) != self.terms:
            raise ActualAccountingV1Error(
                "actual-projection terms must be source-sorted"
            )
        if len({term.source_leaf for term in self.terms}) != len(self.terms):
            raise ActualAccountingV1Error(
                "actual projection repeats an operational source leaf"
            )

    def validate(
        self,
        registry: CounterRegistryV1,
        comparison_profile: ComparisonProfileV1,
    ) -> None:
        registry.validate_official_catalogue()
        comparison_profile.validate(registry)
        if (
            self.profile_key != ACTUAL_PROJECTION_PROFILE_KEY
            or self.schema_version != SCHEMA_VERSION
        ):
            raise ActualAccountingV1Error("actual-projection profile key/version mismatch")
        if self.counter_registry_id != registry.registry_id:
            raise ActualAccountingV1Error("actual projection registry mismatch")
        if self.comparison_profile_id != comparison_profile.comparison_profile_id:
            raise ActualAccountingV1Error("actual projection comparison-profile mismatch")
        if self.terms != comparison_profile.terms:
            expected = {term.source_leaf for term in comparison_profile.terms}
            actual = {term.source_leaf for term in self.terms}
            unknown = sorted(actual - set(registry.by_path))
            missing = sorted(expected - actual)
            duplicate_metadata = sorted(expected & actual)
            raise ActualAccountingV1Error(
                "actual projection is not the exact official mapping; "
                f"missing={missing!r}, unknown={unknown!r}, "
                f"changed={duplicate_metadata!r}"
            )
        if any(term.source_lane is not LaneEnum.OPERATIONAL for term in self.terms):
            raise ActualAccountingV1Error(
                "evaluation/provenance/diagnostic work entered operational projection"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.actual_projection_profile.v1",
            "schema_version": self.schema_version,
            "profile_key": self.profile_key,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "mapping_kind": self.mapping_kind,
            "common_prefix_policy": self.common_prefix_policy,
            "source_lane": self.source_lane.value,
            "terms": [term.to_dict() for term in self.terms],
        }

    @property
    def actual_projection_profile_id(self) -> str:
        return content_id(ACTUAL_PROJECTION_PROFILE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "actual_projection_profile_id": self.actual_projection_profile_id,
        }

    @classmethod
    def from_dict(
        cls,
        document: Mapping[str, Any],
        registry: CounterRegistryV1,
        comparison_profile: ComparisonProfileV1,
    ) -> "ActualProjectionProfileV1":
        expected = {
            "schema",
            "schema_version",
            "profile_key",
            "counter_registry_id",
            "comparison_profile_id",
            "mapping_kind",
            "common_prefix_policy",
            "source_lane",
            "terms",
            "actual_projection_profile_id",
        }
        _fields(document, expected, "actual-projection profile")
        if (
            document["schema"] != "acfqp.actual_projection_profile.v1"
            or type(document["terms"]) is not list
        ):
            raise ActualAccountingV1Error("actual-projection profile schema mismatch")
        profile = cls(
            document["profile_key"],
            document["schema_version"],
            document["counter_registry_id"],
            document["comparison_profile_id"],
            document["mapping_kind"],
            document["common_prefix_policy"],
            document["source_lane"],
            tuple(ProjectionTermV1.from_dict(row) for row in document["terms"]),
        )
        profile.validate(registry, comparison_profile)
        if document["actual_projection_profile_id"] != profile.actual_projection_profile_id:
            raise ActualAccountingV1Error("actual-projection profile content ID mismatch")
        return profile


def official_actual_projection_profile_v1(
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> ActualProjectionProfileV1:
    registry = registry or official_counter_registry_v1()
    comparison_profile = comparison_profile or official_comparison_profile_v1(registry)
    profile = ActualProjectionProfileV1(
        ACTUAL_PROJECTION_PROFILE_KEY,
        SCHEMA_VERSION,
        registry.registry_id,
        comparison_profile.comparison_profile_id,
        EXACT_OPERATIONAL_MAPPING,
        SEPARATE_COMMON_PREFIX,
        LaneEnum.OPERATIONAL,
        comparison_profile.terms,
    )
    profile.validate(registry, comparison_profile)
    return profile


def _validate_work_scope(
    vector: WorkVectorV1, source_lane: LaneEnum, work_scope: ActualWorkScope
) -> None:
    if source_lane is not LaneEnum.OPERATIONAL:
        raise ActualAccountingV1Error(
            "evaluation/provenance work cannot enter operational actual projection"
        )
    values = vector.values
    if work_scope is ActualWorkScope.EVALUATION_REPLAY:
        raise ActualAccountingV1Error(
            "evaluation replay requires a separate evaluation projection profile"
        )
    if work_scope is ActualWorkScope.COMMON_PREFIX:
        if vector.route_kind not in {
            RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
            RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        }:
            raise ActualAccountingV1Error(
                "common-prefix work must use the non-route-execution vector kind"
            )
        forbidden = ("local.", "fallback.", "rebuild.")
    elif work_scope is ActualWorkScope.MARGINAL_ROUTE_EXECUTION:
        if vector.route_kind not in {
            RouteKindEnum.LOCAL_ATTEMPT,
            RouteKindEnum.DIRECT_FALLBACK,
        }:
            raise ActualAccountingV1Error(
                "marginal work must be a local-attempt or direct-fallback vector"
            )
        # Runtime-CAS resolution is selected-route execution even though its
        # operation families (hash/integrity/protocol) are shared by both
        # routes.  Only the closed factory recorder or its typed two-source
        # merge may carry nonzero ``common.*`` rows in this scope; ordinary
        # route executors remain unable to launder common-prefix work here.
        allowed_shared_recorders = {
            "phase3e-sealed-executor-factory-v1",
            "phase3e-sealed-execution-merge-v1",
            "phase3e-sealed-failed-execution-merge-v1",
        }
        bad_shared = sorted(
            row.path
            for row in vector.records
            if row.path.startswith("common.")
            and row.value
            and row.recorder_id not in allowed_shared_recorders
        )
        if bad_shared:
            raise ActualAccountingV1Error(
                "marginal execution contains forbidden work from unauthorised "
                "shared recorders: "
                f"{bad_shared!r}"
            )
        forbidden = ("rebuild.",)
    elif work_scope is ActualWorkScope.MARGINAL_ROUTE_VERIFICATION:
        if vector.route_kind not in {
            RouteKindEnum.LOCAL_ATTEMPT,
            RouteKindEnum.DIRECT_FALLBACK,
        }:
            raise ActualAccountingV1Error(
                "marginal verification work must retain the selected route kind"
            )
        # Result/cap/projection/terminal checks happen only after the selected
        # route has produced artifacts.  They therefore cannot be charged to
        # the already-frozen common prefix.  Keep them in a separate suffix
        # vector and forbid solver/kernel work in that vector; a later native
        # aggregation proof combines execution and verification before upper
        # compliance is checked.
        forbidden = ("local.", "fallback.", "rebuild.")
    elif work_scope is ActualWorkScope.MARGINAL_ROUTE_AGGREGATE:
        if vector.route_kind not in {
            RouteKindEnum.LOCAL_ATTEMPT,
            RouteKindEnum.DIRECT_FALLBACK,
        }:
            raise ActualAccountingV1Error(
                "marginal aggregate must retain the selected route kind"
            )
        # This scope is emitted only by the native execution+verification
        # aggregation helper.  Route-kind exclusivity still rejects the
        # opposite route family; common.* here is post-freeze verification,
        # never the separately referenced common prefix.
        forbidden = ("rebuild.",)
    elif work_scope is ActualWorkScope.REBUILD_EXECUTION:
        if vector.route_kind is not RouteKindEnum.REBUILD:
            raise ActualAccountingV1Error("rebuild scope requires a rebuild vector")
        forbidden = ("common.", "local.", "fallback.", "control.")
    else:  # pragma: no cover - enum exhaustiveness
        raise ActualAccountingV1Error("unknown actual work scope")
    nonzero = sorted(
        path
        for path, value in values.items()
        if value
        and any(path.startswith(prefix) for prefix in forbidden)
        # FQ11 preserves the causal-search operation family as ``local.*``;
        # FQ2/FQ13 place that estimate-before-execute work in the common
        # prefix.  This one failed-prefix leaf is therefore the registered
        # cross-family exception.  Materialization/compiler/solver/post-audit
        # leaves remain forbidden here.
        and not (
            work_scope is ActualWorkScope.COMMON_PREFIX
            and vector.route_kind is RouteKindEnum.ABSTRACT_FAILED_PREFIX
            and path == "local.causal_candidate_evaluations"
        )
    )
    if nonzero:
        raise ActualAccountingV1Error(
            f"work scope {work_scope.value} contains forbidden work: {nonzero!r}"
        )


@dataclass(frozen=True, slots=True)
class ActualProjectionProofV1:
    actual_projection_profile_id: str
    counter_registry_id: str
    comparison_profile_id: str
    work_vector_id: str
    comparison_vector_id: str
    source_lane: LaneEnum
    work_scope: ActualWorkScope
    projection_term_count: int

    def __post_init__(self) -> None:
        for field in (
            "actual_projection_profile_id",
            "counter_registry_id",
            "comparison_profile_id",
            "work_vector_id",
            "comparison_vector_id",
        ):
            _cid(getattr(self, field), field)
        object.__setattr__(
            self, "source_lane", _enum(self.source_lane, LaneEnum, "source_lane")
        )
        object.__setattr__(
            self, "work_scope", _enum(self.work_scope, ActualWorkScope, "work_scope")
        )
        if type(self.projection_term_count) is not int or self.projection_term_count <= 0:
            raise ActualAccountingV1Error("projection_term_count must be positive")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.actual_projection_proof.v1",
            "schema_version": SCHEMA_VERSION,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "source_lane": self.source_lane.value,
            "work_scope": self.work_scope.value,
            "projection_term_count": self.projection_term_count,
        }

    @property
    def actual_projection_proof_id(self) -> str:
        return content_id(ACTUAL_PROJECTION_PROOF_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "actual_projection_proof_id": self.actual_projection_proof_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "ActualProjectionProofV1":
        expected = {
            "schema",
            "schema_version",
            "actual_projection_profile_id",
            "counter_registry_id",
            "comparison_profile_id",
            "work_vector_id",
            "comparison_vector_id",
            "source_lane",
            "work_scope",
            "projection_term_count",
            "actual_projection_proof_id",
        }
        _fields(document, expected, "actual-projection proof")
        if (
            document["schema"] != "acfqp.actual_projection_proof.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise ActualAccountingV1Error("actual-projection proof schema mismatch")
        proof = cls(
            document["actual_projection_profile_id"],
            document["counter_registry_id"],
            document["comparison_profile_id"],
            document["work_vector_id"],
            document["comparison_vector_id"],
            document["source_lane"],
            document["work_scope"],
            document["projection_term_count"],
        )
        if document["actual_projection_proof_id"] != proof.actual_projection_proof_id:
            raise ActualAccountingV1Error("actual-projection proof content ID mismatch")
        return proof


def derive_actual_projection_v1(
    vector: WorkVectorV1,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
    *,
    source_lane: LaneEnum | str,
    work_scope: ActualWorkScope | str,
) -> tuple[ComparisonVectorV1, ActualProjectionProofV1]:
    """Derive, rather than accept, the actual comparison and proof."""

    lane = _enum(source_lane, LaneEnum, "source_lane")
    scope = _enum(work_scope, ActualWorkScope, "work_scope")
    registry.validate_vector(vector)
    actual_profile.validate(registry, comparison_profile)
    _central_work_vector_id(vector)
    _validate_work_scope(vector, lane, scope)
    comparison = derive_comparison_vector_v1(vector, registry, comparison_profile)
    _central_comparison_vector_id(comparison)
    proof = ActualProjectionProofV1(
        actual_profile.actual_projection_profile_id,
        registry.registry_id,
        comparison_profile.comparison_profile_id,
        vector.work_vector_id,
        comparison.comparison_vector_id,
        lane,
        scope,
        len(actual_profile.terms),
    )
    return comparison, proof


def verify_actual_projection_v1(
    proof: ActualProjectionProofV1,
    vector: WorkVectorV1,
    claimed_comparison: ComparisonVectorV1,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> ComparisonVectorV1:
    """Recompute actual work and reject an independently filled comparison."""

    recomputed, expected_proof = derive_actual_projection_v1(
        vector,
        registry,
        comparison_profile,
        actual_profile,
        source_lane=proof.source_lane,
        work_scope=proof.work_scope,
    )
    if proof != expected_proof:
        raise ActualAccountingV1Error("actual-projection proof does not match recomputation")
    if claimed_comparison != recomputed:
        raise ActualAccountingV1Error(
            "claimed actual comparison does not match exact WorkVector projection"
        )
    if claimed_comparison.work_vector_id != vector.work_vector_id:
        raise ActualAccountingV1Error("actual comparison uses another WorkVector")
    if claimed_comparison.comparison_profile_id != comparison_profile.comparison_profile_id:
        raise ActualAccountingV1Error("actual comparison uses another comparison profile")
    return recomputed


@dataclass(frozen=True, slots=True)
class ActualResultRefsV1:
    actual_work_id: str
    actual_comparison_id: str
    actual_projection_proof_id: str

    def __post_init__(self) -> None:
        _cid(self.actual_work_id, "actual_work_id")
        _cid(self.actual_comparison_id, "actual_comparison_id")
        _cid(self.actual_projection_proof_id, "actual_projection_proof_id")

    def to_dict(self) -> dict[str, str]:
        return {
            "actual_work_id": self.actual_work_id,
            "actual_comparison_id": self.actual_comparison_id,
            "actual_projection_proof_id": self.actual_projection_proof_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "ActualResultRefsV1":
        expected = {
            "actual_work_id",
            "actual_comparison_id",
            "actual_projection_proof_id",
        }
        _fields(document, expected, "actual result references")
        return cls(
            document["actual_work_id"],
            document["actual_comparison_id"],
            document["actual_projection_proof_id"],
        )


def verify_actual_result_refs_v1(
    refs: ActualResultRefsV1,
    proof: ActualProjectionProofV1,
    vector: WorkVectorV1,
    claimed_comparison: ComparisonVectorV1,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> ComparisonVectorV1:
    if refs.actual_work_id != vector.work_vector_id:
        raise ActualAccountingV1Error("result actual_work reference mismatch")
    if refs.actual_comparison_id != claimed_comparison.comparison_vector_id:
        raise ActualAccountingV1Error("result actual_comparison reference mismatch")
    if refs.actual_projection_proof_id != proof.actual_projection_proof_id:
        raise ActualAccountingV1Error("result actual-projection proof reference mismatch")
    return verify_actual_projection_v1(
        proof,
        vector,
        claimed_comparison,
        registry,
        comparison_profile,
        actual_profile,
    )


def _verify_selected_upper_authority_v1(
    *,
    route_decision: MarginalRouteDecisionV1,
    route_context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    selected_upper: RouteUpperBoundEnvelopeV1,
    derivation_proof: RouteUpperDerivationProofV1,
    cardinality: CardinalityEvidenceV1,
    cap_profile: Any,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    formula: RouteUpperFormulaV1,
    transaction: TransactionV1 | None,
    causal: CausalEvidenceV1 | None,
) -> None:
    """Bind an upper to the selected decision and replay its fixed verifier.

    Callers cannot inject a predicate such as ``lambda: True`` and thereby
    bless a self-signed upper.  This module selects the authoritative formula
    verifier and supplies its complete frozen derivation inputs directly.
    """

    if route_decision.decision_point_id != decision_point.decision_point_id:
        raise ActualAccountingProtocolError(
            "route decision does not bind the supplied decision point"
        )
    if decision_point.route_decision_context_id != route_context.route_decision_context_id:
        raise ActualAccountingProtocolError(
            "decision point does not bind the supplied route context"
        )
    if route_decision.selected_upper_id != selected_upper.route_upper_bound_envelope_id:
        raise ActualAccountingProtocolError(
            "actual work does not use the upper selected by the route decision"
        )

    for field in (
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
    ):
        if getattr(selected_upper, field) != getattr(route_context, field):
            raise ActualAccountingProtocolError(
                f"selected upper route-context mismatch: {field}"
            )
    if selected_upper.decision_point_id != decision_point.decision_point_id:
        raise ActualAccountingProtocolError(
            "selected upper belongs to another decision point"
        )

    expected_route = (
        RouteKind.LOCAL_ATTEMPT
        if route_decision.selected_route is RouteSelection.LOCAL
        else RouteKind.DIRECT_FALLBACK
    )
    if selected_upper.route_kind is not expected_route:
        raise ActualAccountingProtocolError(
            "selected upper route kind disagrees with the route decision"
        )
    if expected_route is RouteKind.LOCAL_ATTEMPT:
        if selected_upper.transaction_index != decision_point.transaction_index:
            raise ActualAccountingProtocolError(
                "selected local upper transaction-index mismatch"
            )
        if selected_upper.frontier_snapshot_id != decision_point.frontier_snapshot_id:
            raise ActualAccountingProtocolError(
                "selected local upper frontier mismatch"
            )
        if selected_upper.causal_evidence_id != decision_point.causal_evidence_id:
            raise ActualAccountingProtocolError(
                "selected local upper causal-evidence mismatch"
            )

    proof_bindings = (
        (derivation_proof.route_upper_bound_envelope_id, selected_upper.route_upper_bound_envelope_id, "envelope"),
        (derivation_proof.route_decision_context_id, route_context.route_decision_context_id, "route context"),
        (derivation_proof.decision_point_id, decision_point.decision_point_id, "decision point"),
        (derivation_proof.route_cap_profile_id, selected_upper.route_cap_profile_id, "cap profile"),
        (derivation_proof.cardinality_evidence_id, selected_upper.cardinality_evidence_id, "cardinality evidence"),
        (derivation_proof.counter_registry_id, selected_upper.counter_registry_id, "counter registry"),
        (derivation_proof.comparison_profile_id, selected_upper.comparison_profile_id, "comparison profile"),
        (derivation_proof.formula_id, selected_upper.formula_id, "formula"),
        (derivation_proof.transaction_id, selected_upper.transaction_id, "transaction"),
        (derivation_proof.causal_evidence_id, selected_upper.causal_evidence_id, "causal evidence"),
        (derivation_proof.route_kind, selected_upper.route_kind, "route kind"),
        (derivation_proof.comparison_upper_bounds, selected_upper.upper_bounds, "comparison upper"),
    )
    for actual_binding, expected_binding, label in proof_bindings:
        if actual_binding != expected_binding:
            raise ActualAccountingProtocolError(
                f"upper derivation proof {label} binding mismatch"
            )
    try:
        verify_route_upper_derivation_v1(
            selected_upper,
            derivation_proof,
            context=route_context,
            decision_point=decision_point,
            cardinality=cardinality,
            cap_profile=cap_profile,
            registry=registry,
            profile=comparison_profile,
            formula=formula,
            transaction=transaction,
            causal=causal,
        )
    except ValueError as error:
        raise ActualAccountingProtocolError(
            "trusted route-upper derivation replay failed"
        ) from error


def verify_selected_upper_compliance_v1(
    *,
    selected_upper_id: str,
    selected_upper: RouteUpperBoundEnvelopeV1,
    route_decision: MarginalRouteDecisionV1,
    route_context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    upper_derivation_proof: RouteUpperDerivationProofV1,
    upper_cardinality: CardinalityEvidenceV1,
    upper_cap_profile: Any,
    upper_formula: RouteUpperFormulaV1,
    upper_transaction: TransactionV1 | None,
    upper_causal: CausalEvidenceV1 | None,
    refs: ActualResultRefsV1,
    proof: ActualProjectionProofV1,
    vector: WorkVectorV1,
    claimed_comparison: ComparisonVectorV1,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
) -> str:
    """Verify marginal actual work against the exact selected-route upper."""

    _cid(selected_upper_id, "selected_upper_id")
    if selected_upper_id != selected_upper.route_upper_bound_envelope_id:
        raise ActualAccountingProtocolError("selected upper reference mismatch")
    _verify_selected_upper_authority_v1(
        route_decision=route_decision,
        route_context=route_context,
        decision_point=decision_point,
        selected_upper=selected_upper,
        derivation_proof=upper_derivation_proof,
        cardinality=upper_cardinality,
        cap_profile=upper_cap_profile,
        registry=registry,
        comparison_profile=comparison_profile,
        formula=upper_formula,
        transaction=upper_transaction,
        causal=upper_causal,
    )
    actual = verify_actual_result_refs_v1(
        refs,
        proof,
        vector,
        claimed_comparison,
        registry,
        comparison_profile,
        actual_profile,
    )
    if proof.work_scope is not ActualWorkScope.MARGINAL_ROUTE_EXECUTION:
        raise ActualAccountingProtocolError(
            "common-prefix or rebuild work cannot be checked against a marginal upper"
        )
    if selected_upper.counter_registry_id != registry.registry_id:
        raise ActualAccountingProtocolError("selected upper registry mismatch")
    if selected_upper.comparison_profile_id != comparison_profile.comparison_profile_id:
        raise ActualAccountingProtocolError("selected upper comparison-profile mismatch")
    if selected_upper.route_kind.value != vector.route_kind.value:
        raise ActualAccountingProtocolError("selected upper route-kind mismatch")
    expected_subject = (
        selected_upper.transaction_id
        if selected_upper.route_kind is RouteKind.LOCAL_ATTEMPT
        else route_context.route_attempt_id
    )
    if isinstance(expected_subject, TypedNotApplicable):
        raise ActualAccountingProtocolError(
            "selected local upper has no concrete transaction subject"
        )
    if vector.subject_id != expected_subject:
        raise ActualAccountingProtocolError(
            "actual WorkVector subject does not match the selected route identity"
        )
    upper = dict(selected_upper.upper_bounds)
    if tuple(sorted(upper)) != SHARED_AXES or len(upper) != len(SHARED_AXES):
        raise ActualAccountingProtocolError("selected upper does not contain exact shared axes")
    exceeded = tuple(
        axis for axis in SHARED_AXES if actual.value(axis) > upper[axis]
    )
    if exceeded:
        raise UpperBoundViolationError(
            "actual selected-route work exceeds its frozen upper on "
            + ", ".join(exceeded),
            violated_axes=exceeded,
        )
    return WITHIN_SELECTED_UPPER


def _aggregate_values(
    vectors: Sequence[ComparisonVectorV1], profile: ComparisonProfileV1
) -> tuple[tuple[str, int], ...]:
    if not vectors:
        raise ActualAccountingV1Error("occurrence aggregate cannot be empty")
    reducers = {axis.name: axis.reducer for axis in profile.axes}
    totals = {axis: 0 for axis in SHARED_AXES}
    for vector in vectors:
        if tuple(axis for axis, _ in vector.values) != SHARED_AXES:
            raise ActualAccountingV1Error("comparison vector axis set mismatch")
        for axis, value in vector.values:
            if reducers[axis] is ReducerEnum.SUM:
                totals[axis] += value
            else:
                totals[axis] = max(totals[axis], value)
    return tuple(sorted(totals.items()))


@dataclass(frozen=True, slots=True)
class OccurrenceWorkSumV1:
    """Reducer-aware common-prefix + failed-local + fallback aggregate."""

    logical_occurrence_id: str
    route_decision_context_id: str
    route_attempt_id: str
    decision_point_id: str
    local_transaction_id: str
    counter_registry_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    common_prefix_work_id: str
    common_prefix_comparison_id: str
    local_attempt_work_id: str
    local_attempt_comparison_id: str
    fallback_work_id: str
    fallback_comparison_id: str
    aggregate_values: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        for field in (
            "logical_occurrence_id",
            "route_decision_context_id",
            "route_attempt_id",
            "decision_point_id",
            "local_transaction_id",
            "counter_registry_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "common_prefix_work_id",
            "common_prefix_comparison_id",
            "local_attempt_work_id",
            "local_attempt_comparison_id",
            "fallback_work_id",
            "fallback_comparison_id",
        ):
            _cid(getattr(self, field), field)
        refs = (
            self.common_prefix_work_id,
            self.local_attempt_work_id,
            self.fallback_work_id,
        )
        if len(set(refs)) != len(refs):
            raise ActualAccountingV1Error("occurrence aggregate repeats a WorkVector")
        comparison_refs = (
            self.common_prefix_comparison_id,
            self.local_attempt_comparison_id,
            self.fallback_comparison_id,
        )
        if len(set(comparison_refs)) != len(comparison_refs):
            raise ActualAccountingV1Error("occurrence aggregate repeats a comparison vector")
        if (
            tuple(sorted(self.aggregate_values)) != self.aggregate_values
            or tuple(axis for axis, _ in self.aggregate_values) != SHARED_AXES
        ):
            raise ActualAccountingV1Error(
                "occurrence aggregate must contain exact sorted shared axes"
            )
        for axis, value in self.aggregate_values:
            if type(value) is not int or value < 0:
                raise ActualAccountingV1Error(
                    f"occurrence aggregate {axis} must be a nonnegative integer"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.occurrence_work_sum.v1",
            "schema_version": SCHEMA_VERSION,
            "logical_occurrence_id": self.logical_occurrence_id,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "local_transaction_id": self.local_transaction_id,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "common_prefix_work_id": self.common_prefix_work_id,
            "common_prefix_comparison_id": self.common_prefix_comparison_id,
            "local_attempt_work_id": self.local_attempt_work_id,
            "local_attempt_comparison_id": self.local_attempt_comparison_id,
            "fallback_work_id": self.fallback_work_id,
            "fallback_comparison_id": self.fallback_comparison_id,
            "aggregate_values": [
                {"axis": axis, "value": value}
                for axis, value in self.aggregate_values
            ],
        }

    @property
    def logical_occurrence_work_sum_id(self) -> str:
        return content_id(OCCURRENCE_WORK_SUM_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "logical_occurrence_work_sum_id": self.logical_occurrence_work_sum_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "OccurrenceWorkSumV1":
        expected = {
            "schema",
            "schema_version",
            "logical_occurrence_id",
            "RouteDecisionContext_id",
            "route_attempt_id",
            "decision_point_id",
            "local_transaction_id",
            "counter_registry_id",
            "comparison_profile_id",
            "actual_projection_profile_id",
            "common_prefix_work_id",
            "common_prefix_comparison_id",
            "local_attempt_work_id",
            "local_attempt_comparison_id",
            "fallback_work_id",
            "fallback_comparison_id",
            "aggregate_values",
            "logical_occurrence_work_sum_id",
        }
        _fields(document, expected, "occurrence work sum")
        if (
            document["schema"] != "acfqp.occurrence_work_sum.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["aggregate_values"]) is not list
        ):
            raise ActualAccountingV1Error("occurrence-work-sum schema mismatch")
        values: list[tuple[str, int]] = []
        for row in document["aggregate_values"]:
            _fields(row, {"axis", "value"}, "occurrence aggregate axis")
            values.append((row["axis"], row["value"]))
        result = cls(
            document["logical_occurrence_id"],
            document["RouteDecisionContext_id"],
            document["route_attempt_id"],
            document["decision_point_id"],
            document["local_transaction_id"],
            document["counter_registry_id"],
            document["comparison_profile_id"],
            document["actual_projection_profile_id"],
            document["common_prefix_work_id"],
            document["common_prefix_comparison_id"],
            document["local_attempt_work_id"],
            document["local_attempt_comparison_id"],
            document["fallback_work_id"],
            document["fallback_comparison_id"],
            tuple(values),
        )
        if document["logical_occurrence_work_sum_id"] != result.logical_occurrence_work_sum_id:
            raise ActualAccountingV1Error("occurrence-work-sum content ID mismatch")
        return result


def derive_occurrence_work_sum_v1(
    *,
    logical_occurrence_id: str,
    route_context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    local_transaction: TransactionV1,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
    common_prefix: tuple[
        WorkVectorV1, ComparisonVectorV1, ActualProjectionProofV1
    ],
    local_attempt: tuple[
        WorkVectorV1, ComparisonVectorV1, ActualProjectionProofV1
    ],
    fallback: tuple[
        WorkVectorV1, ComparisonVectorV1, ActualProjectionProofV1
    ],
) -> OccurrenceWorkSumV1:
    _cid(logical_occurrence_id, "logical_occurrence_id")
    if route_context.logical_occurrence_id != logical_occurrence_id:
        raise ActualAccountingV1Error(
            "occurrence aggregate route-context occurrence mismatch"
        )
    if decision_point.route_decision_context_id != route_context.route_decision_context_id:
        raise ActualAccountingV1Error(
            "occurrence aggregate decision-point context mismatch"
        )
    if local_transaction.logical_occurrence_id != logical_occurrence_id:
        raise ActualAccountingV1Error(
            "occurrence aggregate transaction occurrence mismatch"
        )
    if local_transaction.route_attempt_id != route_context.route_attempt_id:
        raise ActualAccountingV1Error(
            "occurrence aggregate transaction route-attempt mismatch"
        )
    if local_transaction.decision_point_id != decision_point.decision_point_id:
        raise ActualAccountingV1Error(
            "occurrence aggregate transaction decision-point mismatch"
        )
    triples = (common_prefix, local_attempt, fallback)
    allowed_scopes = (
        frozenset({ActualWorkScope.COMMON_PREFIX}),
        frozenset(
            {
                ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
                ActualWorkScope.MARGINAL_ROUTE_AGGREGATE,
            }
        ),
        frozenset(
            {
                ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
                ActualWorkScope.MARGINAL_ROUTE_AGGREGATE,
            }
        ),
    )
    for (work, comparison, proof), component_scopes in zip(
        triples, allowed_scopes, strict=True
    ):
        if proof.work_scope not in component_scopes:
            raise ActualAccountingV1Error("occurrence input work-scope mismatch")
        verify_actual_projection_v1(
            proof,
            work,
            comparison,
            registry,
            comparison_profile,
            actual_profile,
        )
    prefix_work, prefix_comparison, _ = common_prefix
    local_work, local_comparison, _ = local_attempt
    fallback_work, fallback_comparison, _ = fallback
    if decision_point.common_prefix_work_id != prefix_work.work_vector_id:
        raise ActualAccountingV1Error(
            "decision point does not reference the supplied common-prefix WorkVector"
        )
    expected_subjects = (
        (
            prefix_work,
            route_context.route_attempt_id,
            "common-prefix route attempt",
        ),
        (local_work, local_transaction.transaction_id, "local transaction"),
        (fallback_work, route_context.route_attempt_id, "fallback route attempt"),
    )
    for work, expected_subject, label in expected_subjects:
        if work.subject_id != expected_subject:
            raise ActualAccountingV1Error(
                f"occurrence {label} WorkVector subject mismatch"
            )
    if local_work.route_kind is not RouteKindEnum.LOCAL_ATTEMPT:
        raise ActualAccountingV1Error("occurrence local input is not a local attempt")
    if fallback_work.route_kind is not RouteKindEnum.DIRECT_FALLBACK:
        raise ActualAccountingV1Error("occurrence fallback input is not direct fallback")
    aggregate = _aggregate_values(
        (prefix_comparison, local_comparison, fallback_comparison),
        comparison_profile,
    )
    return OccurrenceWorkSumV1(
        logical_occurrence_id,
        route_context.route_decision_context_id,
        route_context.route_attempt_id,
        decision_point.decision_point_id,
        local_transaction.transaction_id,
        registry.registry_id,
        comparison_profile.comparison_profile_id,
        actual_profile.actual_projection_profile_id,
        prefix_work.work_vector_id,
        prefix_comparison.comparison_vector_id,
        local_work.work_vector_id,
        local_comparison.comparison_vector_id,
        fallback_work.work_vector_id,
        fallback_comparison.comparison_vector_id,
        aggregate,
    )


def verify_occurrence_work_sum_v1(
    occurrence_sum: OccurrenceWorkSumV1,
    *,
    logical_occurrence_id: str,
    route_context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    local_transaction: TransactionV1,
    registry: CounterRegistryV1,
    comparison_profile: ComparisonProfileV1,
    actual_profile: ActualProjectionProfileV1,
    common_prefix: tuple[
        WorkVectorV1, ComparisonVectorV1, ActualProjectionProofV1
    ],
    local_attempt: tuple[
        WorkVectorV1, ComparisonVectorV1, ActualProjectionProofV1
    ],
    fallback: tuple[
        WorkVectorV1, ComparisonVectorV1, ActualProjectionProofV1
    ],
) -> None:
    expected = derive_occurrence_work_sum_v1(
        logical_occurrence_id=logical_occurrence_id,
        route_context=route_context,
        decision_point=decision_point,
        local_transaction=local_transaction,
        registry=registry,
        comparison_profile=comparison_profile,
        actual_profile=actual_profile,
        common_prefix=common_prefix,
        local_attempt=local_attempt,
        fallback=fallback,
    )
    if occurrence_sum != expected:
        raise ActualAccountingV1Error(
            "occurrence work sum does not match reducer-aware replay"
        )


__all__ = [
    "ACTUAL_PROJECTION_PROFILE_KEY",
    "ActualAccountingProtocolError",
    "ActualAccountingV1Error",
    "ActualProjectionProfileV1",
    "ActualProjectionProofV1",
    "ActualResultRefsV1",
    "ActualWorkScope",
    "OccurrenceWorkSumV1",
    "PROTOCOL_FAILURE",
    "SEPARATE_COMMON_PREFIX",
    "UPPER_BOUND_VIOLATION",
    "UpperBoundViolationError",
    "UpperDerivationVerifierV1",
    "WITHIN_SELECTED_UPPER",
    "derive_actual_projection_v1",
    "derive_occurrence_work_sum_v1",
    "official_actual_projection_profile_v1",
    "verify_actual_projection_v1",
    "verify_actual_result_refs_v1",
    "verify_occurrence_work_sum_v1",
    "verify_selected_upper_compliance_v1",
]
