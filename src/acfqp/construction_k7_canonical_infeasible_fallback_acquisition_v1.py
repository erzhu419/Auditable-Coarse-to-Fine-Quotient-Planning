"""Source-bound acquisition for the canonical exact-infeasible fallback.

Contract 2.0.42 is deliberately narrower than a formal K7 terminal.  It
freezes a direct-fallback upper and route-decision candidate from a durable
canonical G2048 H=1 witness, executes the raw in-process ground fallback once,
and records the exact source values that execution currently exposes.

The legacy fallback solver still emits the 42-row V1 WorkVector.  This module
never changes those records' registry ID and never presents them as V6
``CounterRecordV1`` rows.  Instead it emits fresh, source-bound acquisition
evidence for the seven direct-fallback native paths whose operation streams
are retained by that solver and six route/solver reconciliation values.  The
178 stage-forbidden paths are only zero *candidates*: without a production V6
recorder or complete side-effect monitor they remain unresolved.  The nine
shared-resource paths and two process-exit reconciliation paths are likewise
explicit blockers.

Consequently the exact partition is ``178 + 7 + 6 + 11 = 202`` and all 202
paths remain formally blocked; thirteen exact source values are retained for
the next authority.  No production WorkVector, ComparisonVector, terminal,
occurrence closure, Gate, scalar, or break-even claim is issued.  The existing
Contract-2.0.29 materializer is
also intentionally not called: it is specialized to an
``ABSTRACT_FAILED_PREFIX`` with 114 profile-native zeros, whereas this route
segment is ``DIRECT_FALLBACK`` with 178 stage-forbidden paths.

All domains are centrally registered and role-separated.  This closes only
the identity namespace; it does not promote the raw acquisition into an
official bundle.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import (
    RouteKindEnum,
    WorkVectorV1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_all_path_accounting_profile_v1 as all_path_v1
from acfqp.core import QuerySpec
from acfqp.domains.g2048 import (
    G2048Action,
    G2048Kernel,
    G2048State,
    G2048Status,
)
from acfqp.phase3e_exact_infeasibility_durable_proof_v1 import (
    DurableExactInfeasibilityIdentityV1,
    DurableProofVerificationOutcomeV1,
    issue_phase3e_exact_infeasibility_durable_proof_v1,
    verify_phase3e_exact_infeasibility_durable_proof_bytes_v1,
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackCardinalityBoundV1,
    GroundFallbackExecutionV1,
    GroundFallbackOutcome,
    GroundFallbackResultV1,
    build_ground_fallback_cardinality_evidence_v1,
    run_ground_fallback_search_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_ACQUISITION_V1_DOMAIN,
    CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_CARDINALITY_SOURCE_V1_DOMAIN,
    CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_CURRENT_IDENTITY_V1_DOMAIN,
    CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_PATH_EVIDENCE_V1_DOMAIN,
    CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_PREEXECUTION_V1_DOMAIN,
    CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_SUPPORT_V1_DOMAIN,
    CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_TRANSITION_TRACE_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)
from acfqp.route_upper_formula_v1 import (
    RouteUpperFormulaV1,
    RouteUpperDerivationProofV1,
    derive_route_upper_v1,
    official_route_upper_formula_v1,
)
from acfqp.routing_v1 import (
    CardinalityEvidenceV1,
    DecisionPointV1,
    MarginalRouteDecisionV1,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    RouteUpperBoundEnvelopeV1,
    TypedNotApplicable,
)
from acfqp.routing_v1 import TerminalCode


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.42"
PROFILE_KEY = "construction_k7_canonical_infeasible_fallback_acquisition_v1"

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

EXPECTED_REQUIRED_PATH_COUNT = registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
EXPECTED_STAGE_ZERO_COUNT = 178
EXPECTED_NATIVE_EVENT_COUNT = 7
EXPECTED_EXACT_DERIVED_COUNT = 6
EXPECTED_UNRESOLVED_COUNT = 11
EXPECTED_SHARED_RESOURCE_BLOCKER_COUNT = 9
EXPECTED_EXACT_SOURCE_VALUE_COUNT = 13
EXPECTED_FORMALLY_RESOLVED_PATH_COUNT = 0

_PREEXECUTION_DOMAIN = (
    CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_PREEXECUTION_V1_DOMAIN
)
_CURRENT_IDENTITY_DOMAIN = (
    CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_CURRENT_IDENTITY_V1_DOMAIN
)
_CARDINALITY_SOURCE_DOMAIN = (
    CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_CARDINALITY_SOURCE_V1_DOMAIN
)
_TRACE_DOMAIN = (
    CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_TRANSITION_TRACE_V1_DOMAIN
)
_PATH_EVIDENCE_DOMAIN = (
    CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_PATH_EVIDENCE_V1_DOMAIN
)
_ACQUISITION_DOMAIN = (
    CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_ACQUISITION_V1_DOMAIN
)
_SUPPORT_DOMAIN = CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_SUPPORT_V1_DOMAIN
REGISTERED_DOMAINS = frozenset(
    {
        _PREEXECUTION_DOMAIN,
        _CURRENT_IDENTITY_DOMAIN,
        _CARDINALITY_SOURCE_DOMAIN,
        _TRACE_DOMAIN,
        _PATH_EVIDENCE_DOMAIN,
        _ACQUISITION_DOMAIN,
        _SUPPORT_DOMAIN,
    }
)

_PREEXECUTION_ISSUER = object()
_CURRENT_IDENTITY_ISSUER = object()
_PATH_ISSUER = object()
_ACQUISITION_ISSUER = object()

_EXPECTED_RAW_SOLVER_CALLABLE = run_ground_fallback_search_v1
_EXPECTED_KERNEL_STEP_CALLABLE = G2048Kernel.step
_EXPECTED_KERNEL_ACTIONS_CALLABLE = G2048Kernel.actions
_EXPECTED_KERNEL_INITIAL_DISTRIBUTION_CALLABLE = G2048Kernel.initial_distribution


class ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error(ValueError):
    """The source proof, live execution, or residual partition is invalid."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _local_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in REGISTERED_DOMAINS:
        _fail("fallback acquisition used an unknown registered content domain")
    return content_id(domain, dict(payload))


def _support_id(label: str, payload: Any) -> str:
    return _local_id(
        _SUPPORT_DOMAIN,
        {
            "schema": "acfqp.construction_k7_canonical_infeasible_fallback_support.v1",
            "label": label,
            "payload": payload,
        },
    )


def _require_unsubstituted_raw_callables() -> None:
    """Reject monkeypatched raw execution before it can cause a side effect."""

    if (
        run_ground_fallback_search_v1 is not _EXPECTED_RAW_SOLVER_CALLABLE
        or G2048Kernel.step is not _EXPECTED_KERNEL_STEP_CALLABLE
        or G2048Kernel.actions is not _EXPECTED_KERNEL_ACTIONS_CALLABLE
        or G2048Kernel.initial_distribution
        is not _EXPECTED_KERNEL_INITIAL_DISTRIBUTION_CALLABLE
    ):
        _fail("raw fallback or live-kernel callable substitution detected")


class FallbackPathDispositionV1(str, Enum):
    STAGE_FORBIDDEN_ZERO_CANDIDATE_UNRESOLVED = (
        "STAGE_FORBIDDEN_ZERO_CANDIDATE_UNRESOLVED"
    )
    SOURCE_BOUND_LEGACY_NATIVE_VALUE_CANDIDATE = (
        "SOURCE_BOUND_LEGACY_NATIVE_VALUE_CANDIDATE"
    )
    SOURCE_BOUND_LEGACY_RECONCILIATION_VALUE_CANDIDATE = (
        "SOURCE_BOUND_LEGACY_RECONCILIATION_VALUE_CANDIDATE"
    )
    UNRESOLVED_SHARED_RESOURCE_RECEIPT = (
        "UNRESOLVED_SHARED_RESOURCE_RECEIPT"
    )
    UNRESOLVED_PROCESS_DERIVED_PROOF = (
        "UNRESOLVED_PROCESS_DERIVED_PROOF"
    )


_NATIVE_EVENT_PATHS = (
    "control.cap_checks",
    "control.cap_rejections",
    "fallback.actions_evaluated",
    "fallback.bellman_backups",
    "fallback.ground_steps",
    "fallback.outcome_rows",
    "fallback.states_expanded",
)

_EXACT_DERIVED_PATHS = (
    "route.attempts",
    "route.failures",
    "route.successes",
    "solver.attempts",
    "solver.failures",
    "solver.successes",
)

_SHARED_RESOURCE_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)

_UNRESOLVED_PROCESS_DERIVED_PATHS = (
    "process.exit_failures",
    "process.exit_successes",
)


def _occurrence_stage_plan_status(
    terminal_code: TerminalCode,
) -> list[dict[str, str]]:
    """Expose the full FQ9 occurrence gap around this raw route segment."""

    profile = all_path_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    rule = profile.terminal_path_rule_by_code[terminal_code]
    rows: list[dict[str, str]] = []
    for entry in rule.stage_plan:
        if entry.stage_kind is registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK:
            status = "RAW_SOURCE_SEGMENT_ONLY_PRODUCTION_STAGE_MISSING"
        elif entry.disposition is all_path_v1.StageDispositionV1.FORBIDDEN:
            status = "PROFILE_FORBIDDEN_NOT_EXECUTED"
        elif entry.disposition in {
            all_path_v1.StageDispositionV1.REQUIRED_ONCE,
            all_path_v1.StageDispositionV1.REQUIRED_AT_LEAST_ONCE,
        }:
            status = "REQUIRED_OCCURRENCE_STAGE_MISSING"
        else:
            status = "OPTIONAL_OCCURRENCE_STAGE_NOT_EVIDENCED"
        rows.append(
            {
                "stage_kind": entry.stage_kind.value,
                "profile_disposition": entry.disposition.value,
                "acquisition_status": status,
            }
        )
    return rows


@dataclass(frozen=True, slots=True)
class CanonicalFallbackPathEvidenceV1:
    """One V6 path disposition; never a V6 CounterRecord."""

    _issuer: InitVar[object]
    acquisition_context_id: str
    path: str
    semantics_id: str
    owner: str
    unit: str
    lane: str
    scope: str
    reducer: str
    comparison_axis: str | None
    disposition: FallbackPathDispositionV1
    value: int | None
    source_ids: tuple[str, ...]
    formula: str | None
    blocker: str | None
    _evidence_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PATH_ISSUER:
            _fail("fallback path evidence is caller-minted")
        _cid(self.acquisition_context_id, "fallback acquisition context")
        for source_id in self.source_ids:
            _cid(source_id, "fallback path source")
        try:
            disposition = FallbackPathDispositionV1(self.disposition)
        except (TypeError, ValueError) as error:
            raise ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error(
                "fallback path disposition is invalid"
            ) from error
        object.__setattr__(self, "disposition", disposition)
        registry = registry_v6.official_counter_registry_v6()
        leaf = registry.by_path.get(self.path)
        if (
            leaf is None
            or not leaf.required
            or (
                self.semantics_id,
                self.owner,
                self.unit,
                self.lane,
                self.scope,
                self.reducer,
                self.comparison_axis,
            )
            != (
                leaf.semantics_id,
                leaf.owner,
                leaf.unit,
                leaf.lane.value,
                leaf.scope,
                leaf.reducer.value,
                leaf.comparison_axis,
            )
            or type(self.source_ids) is not tuple
            or len(set(self.source_ids)) != len(self.source_ids)
        ):
            _fail("fallback path evidence differs from its exact V6 leaf")
        if not self.blocker:
            _fail("every fallback path remains formal-blocked and needs a blocker")
        if (
            disposition
            is FallbackPathDispositionV1.STAGE_FORBIDDEN_ZERO_CANDIDATE_UNRESOLVED
        ):
            if self.value is not None or len(self.source_ids) != 2 or self.formula is not None:
                _fail("stage-forbidden zero candidate overclaims a native-zero value")
        elif (
            disposition
            is FallbackPathDispositionV1.SOURCE_BOUND_LEGACY_NATIVE_VALUE_CANDIDATE
        ):
            if (
                type(self.value) is not int
                or self.value < 0
                or len(self.source_ids) != 3
                or self.formula is not None
            ):
                _fail("legacy native candidate lacks one exact source value")
        elif (
            disposition
            is FallbackPathDispositionV1.SOURCE_BOUND_LEGACY_RECONCILIATION_VALUE_CANDIDATE
        ):
            if (
                type(self.value) is not int
                or self.value < 0
                or len(self.source_ids) != 2
                or not self.formula
            ):
                _fail("legacy reconciliation candidate lacks its exact source formula")
        elif self.value is not None or self.formula is not None or self.source_ids:
            _fail("unresolved receipt/reconciliation path contains source evidence")
        object.__setattr__(
            self,
            "_evidence_id",
            _local_id(_PATH_EVIDENCE_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_canonical_infeasible_fallback_path_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "acquisition_context_id": self.acquisition_context_id,
            "path": self.path,
            "semantics_id": self.semantics_id,
            "owner": self.owner,
            "unit": self.unit,
            "lane": self.lane,
            "scope": self.scope,
            "reducer": self.reducer,
            "comparison_axis": self.comparison_axis,
            "disposition": self.disposition.value,
            "value": self.value,
            "source_ids": list(self.source_ids),
            "formula": self.formula,
            "blocker": self.blocker,
            "source_v1_record_relabelled_as_v6": False,
            "source_v1_zero_record_used_as_native_zero": False,
            "v6_counter_record_issued": False,
            "missing_event_inferred_zero": False,
            "exact_source_value_available": self.value is not None,
            "formal_path_resolved": False,
            "formal_materialization_eligible": False,
            "central_domain_registration_pending": False,
        }

    @property
    def evidence_id(self) -> str:
        if _local_id(_PATH_EVIDENCE_DOMAIN, self._payload()) != self._evidence_id:
            _fail("fallback path evidence changed after issuance")
        return self._evidence_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "fallback_path_evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class CanonicalFallbackCurrentIdentityV1:
    """Issuer-owned current identity built from source plus the live kernel.

    A bare :class:`DurableExactInfeasibilityIdentityV1` is intentionally not
    accepted by the acquisition API: a caller could otherwise copy the
    claimant proof's own identity and turn verification into a self-match.
    """

    _issuer: InitVar[object]
    identity: DurableExactInfeasibilityIdentityV1
    current_source_proof_sha256: str
    live_initial_law_id: str
    live_transition_law_id: str
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CURRENT_IDENTITY_ISSUER:
            _fail("current canonical fallback identity is caller-minted")
        if type(self.identity) is not DurableExactInfeasibilityIdentityV1:
            _fail("current canonical fallback identity lacks a typed identity")
        DurableExactInfeasibilityIdentityV1.from_dict(self.identity.to_dict())
        for value, label in (
            (self.identity.exact_infeasibility_identity_id, "current identity"),
            (self.live_initial_law_id, "live initial law"),
            (self.live_transition_law_id, "live transition law"),
        ):
            _cid(value, label)
        if (
            type(self.current_source_proof_sha256) is not str
            or len(self.current_source_proof_sha256) != 64
            or any(
                char not in "0123456789abcdef"
                for char in self.current_source_proof_sha256
            )
        ):
            _fail("current source proof digest is invalid")
        object.__setattr__(
            self,
            "_attestation_id",
            _local_id(_CURRENT_IDENTITY_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_canonical_infeasible_fallback_current_identity.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "identity": self.identity.to_dict(),
            "current_source_proof_sha256": self.current_source_proof_sha256,
            "live_initial_law_id": self.live_initial_law_id,
            "live_transition_law_id": self.live_transition_law_id,
            "current_identity_source_supplied_separately_from_claimant": True,
            "claimant_identity_used_as_current_by_default": False,
            "live_kernel_and_query_replayed": True,
            "explicit_current_identity_components_required": [
                "BuildEpoch_id",
                "threshold_profile_id",
                "reward_profile_id",
                "policy_class_id",
                "complete_search_profile_id",
            ],
            "build_lane": "EVALUATION",
            "charged_as_operational_route_work": False,
            "central_domain_registration_pending": False,
            "production_authority": False,
        }

    @property
    def attestation_id(self) -> str:
        if (
            _local_id(_CURRENT_IDENTITY_DOMAIN, self._payload())
            != self._attestation_id
        ):
            _fail("current canonical fallback identity changed after issuance")
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "current_identity_attestation_id": self.attestation_id,
        }


@dataclass(frozen=True, slots=True)
class CanonicalDirectFallbackPreexecutionCandidateV1:
    """Proof-derived raw-slice upper and frozen FALLBACK decision candidate."""

    _issuer: InitVar[object]
    durable_proof_id: str
    current_identity: CanonicalFallbackCurrentIdentityV1
    cardinality_source_id: str
    route_context: RouteDecisionContextV1
    decision_point: DecisionPointV1
    cap_profile: GroundFallbackCapProfileV1
    cardinality_bound: GroundFallbackCardinalityBoundV1
    cardinality: CardinalityEvidenceV1
    formula: RouteUpperFormulaV1
    upper: RouteUpperBoundEnvelopeV1
    upper_proof: RouteUpperDerivationProofV1
    decision: MarginalRouteDecisionV1
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PREEXECUTION_ISSUER:
            _fail("direct-fallback preexecution candidate is caller-minted")
        if type(self.current_identity) is not CanonicalFallbackCurrentIdentityV1:
            _fail("preexecution candidate lacks an issuer-owned current identity")
        current = self.current_identity.identity
        for value, label in (
            (self.durable_proof_id, "durable proof"),
            (
                self.current_identity.attestation_id,
                "current exact-infeasibility identity",
            ),
            (self.cardinality_source_id, "fallback cardinality source"),
        ):
            _cid(value, label)
        registry = official_counter_registry_v1()
        comparison = official_comparison_profile_v1(registry)
        try:
            context = RouteDecisionContextV1.from_dict(self.route_context.to_dict())
            point = DecisionPointV1.from_dict(self.decision_point.to_dict())
            cap = GroundFallbackCapProfileV1.from_dict(self.cap_profile.to_dict())
            bound = GroundFallbackCardinalityBoundV1.from_dict(
                self.cardinality_bound.to_dict()
            )
            cardinality = CardinalityEvidenceV1.from_dict(self.cardinality.to_dict())
            expected_formula = official_route_upper_formula_v1(
                RouteKind.DIRECT_FALLBACK,
                registry=registry,
                profile=comparison,
                cap_profile=cap,
            )
            expected_upper, expected_proof = derive_route_upper_v1(
                context=context,
                decision_point=point,
                cardinality=cardinality,
                cap_profile=cap,
                registry=registry,
                profile=comparison,
                formula=expected_formula,
            )
            expected_decision = MarginalRouteDecisionV1.select(
                point, expected_upper, causal=None, local_upper=None
            )
        except (TypeError, ValueError) as error:
            raise ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error(
                f"direct-fallback preexecution chain failed replay: {error}"
            ) from error
        if (
            self.route_context != context
            or self.decision_point != point
            or self.cap_profile != cap
            or self.cardinality_bound != bound
            or self.cardinality != cardinality
            or self.formula != expected_formula
            or self.upper != expected_upper
            or self.upper_proof != expected_proof
            or self.decision != expected_decision
            or self.cardinality_source_id not in bound.source_artifact_ids
            or bound.ground_fallback_cardinality_bound_id
            not in cardinality.source_artifact_ids
            or self.decision.selected_route is not RouteSelection.FALLBACK
            or self.decision.selected_upper_id
            != self.upper.route_upper_bound_envelope_id
            or context.structural_id != current.structural_id
            or context.query_id != current.query_id
            or context.build_epoch_id != current.build_epoch_id
            or context.threshold_profile_id
            != current.threshold_profile_id
        ):
            _fail("direct-fallback preexecution chain differs from exact replay")
        object.__setattr__(
            self,
            "_candidate_id",
            _local_id(_PREEXECUTION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_canonical_infeasible_fallback_preexecution.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "durable_proof_id": self.durable_proof_id,
            "current_identity_attestation": self.current_identity.to_document(),
            "cardinality_source_id": self.cardinality_source_id,
            "route_context": self.route_context.to_dict(),
            "decision_point": self.decision_point.to_dict(),
            "cap_profile": self.cap_profile.to_dict(),
            "cardinality_bound": self.cardinality_bound.to_dict(),
            "cardinality": self.cardinality.to_dict(),
            "route_upper_formula": self.formula.to_dict(),
            "route_upper": self.upper.to_dict(),
            "route_upper_derivation_proof": self.upper_proof.to_dict(),
            "route_decision": self.decision.to_dict(),
            "current_identity_attestation_id": self.current_identity.attestation_id,
            "current_identity_supplied_separately": True,
            "claimant_self_match_used": False,
            "cardinality_source_replayed_from_durable_h1_action_closure": True,
            "route_upper_arithmetic_replayed": True,
            "route_decision_frozen_before_kernel_access": True,
            "selected_route": RouteSelection.FALLBACK.value,
            "scope": "RAW_IN_PROCESS_MARGINAL_SEGMENT",
            "production_route_authority": False,
            "production_authorized": False,
            "existing_contract_1_semantic_registry_extended": False,
            "central_domain_registration_pending": False,
            "official_execution_allowed": False,
        }

    @property
    def candidate_id(self) -> str:
        if _local_id(_PREEXECUTION_DOMAIN, self._payload()) != self._candidate_id:
            _fail("direct-fallback preexecution candidate changed after issuance")
        return self._candidate_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "direct_fallback_preexecution_candidate_id": self.candidate_id,
        }


@dataclass(frozen=True, slots=True)
class CanonicalInfeasibleFallbackAcquisitionV1:
    """The exact 202-path source-value/residual partition after a raw run."""

    _issuer: InitVar[object]
    proof_bytes_sha256: str
    preexecution: CanonicalDirectFallbackPreexecutionCandidateV1
    transition_trace_id: str
    execution: GroundFallbackExecutionV1 = field(repr=False, compare=False)
    path_evidence: tuple[CanonicalFallbackPathEvidenceV1, ...]
    acquisition_outcome: str
    _acquisition_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ACQUISITION_ISSUER
            or type(self.preexecution)
            is not CanonicalDirectFallbackPreexecutionCandidateV1
            or type(self.execution) is not GroundFallbackExecutionV1
            or type(self.path_evidence) is not tuple
        ):
            _fail("canonical fallback acquisition is caller-minted")
        _cid(self.transition_trace_id, "transition trace")
        if (
            type(self.proof_bytes_sha256) is not str
            or len(self.proof_bytes_sha256) != 64
            or any(char not in "0123456789abcdef" for char in self.proof_bytes_sha256)
        ):
            _fail("proof byte digest is invalid")
        result = self.execution.result
        work = self.execution.work_vector
        expected_outcome = (
            "EXACT_INFEASIBILITY_RAW_SOURCE_VALUES_ACQUIRED"
            if result.outcome is GroundFallbackOutcome.INFEASIBLE_CERTIFIED
            else "CAP_EXHAUSTED_NONCERTIFICATE_ACQUISITION"
            if result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED
            else "WRONG_FALLBACK_OUTCOME_BLOCKED"
        )
        if (
            self.acquisition_outcome != expected_outcome
            or result.route_decision_context_id
            != self.preexecution.route_context.route_decision_context_id
            or result.decision_point_id
            != self.preexecution.decision_point.decision_point_id
            or result.route_decision_id != self.preexecution.decision.route_decision_id
            or result.selected_upper_id
            != self.preexecution.upper.route_upper_bound_envelope_id
            or result.route_attempt_id
            != self.preexecution.route_context.route_attempt_id
            or work.route_kind is not RouteKindEnum.DIRECT_FALLBACK
            or result.work_vector_id != work.work_vector_id
            or self.execution.trusted_provenance is not None
            or len(work.records) != 42
            or len(self.path_evidence) != EXPECTED_REQUIRED_PATH_COUNT
            or tuple(row.path for row in self.path_evidence)
            != tuple(sorted(row.path for row in self.path_evidence))
            or len({row.path for row in self.path_evidence})
            != EXPECTED_REQUIRED_PATH_COUNT
        ):
            _fail("canonical fallback execution or 202-path partition crossed identities")
        counts = {kind: 0 for kind in FallbackPathDispositionV1}
        for row in self.path_evidence:
            counts[row.disposition] += 1
        if (
            counts[
                FallbackPathDispositionV1.STAGE_FORBIDDEN_ZERO_CANDIDATE_UNRESOLVED
            ]
            != EXPECTED_STAGE_ZERO_COUNT
            or counts[
                FallbackPathDispositionV1.SOURCE_BOUND_LEGACY_NATIVE_VALUE_CANDIDATE
            ]
            != EXPECTED_NATIVE_EVENT_COUNT
            or counts[
                FallbackPathDispositionV1.SOURCE_BOUND_LEGACY_RECONCILIATION_VALUE_CANDIDATE
            ]
            != EXPECTED_EXACT_DERIVED_COUNT
            or counts[
                FallbackPathDispositionV1.UNRESOLVED_SHARED_RESOURCE_RECEIPT
            ]
            != EXPECTED_SHARED_RESOURCE_BLOCKER_COUNT
            or counts[
                FallbackPathDispositionV1.UNRESOLVED_PROCESS_DERIVED_PROOF
            ]
            != len(_UNRESOLVED_PROCESS_DERIVED_PATHS)
        ):
            _fail("canonical fallback 178+7+6+11 partition changed")
        object.__setattr__(
            self,
            "_acquisition_id",
            _local_id(_ACQUISITION_DOMAIN, self._payload()),
        )

    @property
    def by_path(self) -> dict[str, CanonicalFallbackPathEvidenceV1]:
        return {row.path: row for row in self.path_evidence}

    def _payload(self) -> dict[str, Any]:
        result = self.execution.result
        work = self.execution.work_vector
        target_terminal_code = (
            TerminalCode.FULL_GROUND_EXACT_INFEASIBLE
            if result.outcome is GroundFallbackOutcome.INFEASIBLE_CERTIFIED
            else TerminalCode.FALLBACK_CAP_EXHAUSTED
        )
        counts = {kind.value: 0 for kind in FallbackPathDispositionV1}
        for row in self.path_evidence:
            counts[row.disposition.value] += 1
        return {
            "schema": "acfqp.construction_k7_canonical_infeasible_fallback_acquisition.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "proof_bytes_sha256": self.proof_bytes_sha256,
            "durable_proof_lane": "EVALUATION",
            "durable_proof_charged_as_operational_route_work": False,
            "preexecution_candidate": self.preexecution.to_document(),
            "current_identity_attestation_id": (
                self.preexecution.current_identity.attestation_id
            ),
            "current_identity_build_lane": "EVALUATION",
            "claimant_self_match_used": False,
            "transition_trace_id": self.transition_trace_id,
            "ground_fallback_result": result.to_dict(),
            "source_v1_work_vector": work.to_dict(),
            "source_v1_counter_record_count": len(work.records),
            "source_v1_counter_records_relabelled_as_v6": False,
            "acquisition_outcome": self.acquisition_outcome,
            "raw_marginal_segment": True,
            "raw_in_process_search": True,
            "ground_fallback_trusted_provenance_present": False,
            "trusted_provenance": None,
            "production_executor_used": False,
            "production_authorized": False,
            "production_chain_closed": False,
            "external_side_effect_monitor_connected": False,
            "external_side_effect_freedom_claimed": False,
            "raw_infeasibility_source_values_acquired": (
                result.outcome is GroundFallbackOutcome.INFEASIBLE_CERTIFIED
            ),
            "operational_infeasibility_terminal_authorized": False,
            "cap_exhausted_is_infeasibility": False,
            "required_v6_path_count": len(self.path_evidence),
            "path_disposition_counts": [
                {"disposition": kind.value, "count": counts[kind.value]}
                for kind in FallbackPathDispositionV1
            ],
            "path_evidence": [row.to_document() for row in self.path_evidence],
            "exact_source_value_path_count": EXPECTED_EXACT_SOURCE_VALUE_COUNT,
            "formal_resolved_path_count": EXPECTED_FORMALLY_RESOLVED_PATH_COUNT,
            "formal_blocked_path_count": EXPECTED_REQUIRED_PATH_COUNT,
            "all_202_paths_formal_blocked": True,
            "zero_candidates_not_counted_as_resolved": True,
            "unresolved_source_value_path_count": (
                EXPECTED_EXACT_SOURCE_VALUE_COUNT
            ),
            "unresolved_no_value_path_count": (
                EXPECTED_STAGE_ZERO_COUNT + EXPECTED_UNRESOLVED_COUNT
            ),
            "unresolved_shared_resource_paths": list(_SHARED_RESOURCE_PATHS),
            "unresolved_process_derived_paths": list(
                _UNRESOLVED_PROCESS_DERIVED_PATHS
            ),
            "fq9_target_terminal_code": target_terminal_code.value,
            "fq9_occurrence_stage_plan": _occurrence_stage_plan_status(
                target_terminal_code
            ),
            "preceding_required_occurrence_stages_missing": [
                "FAILED_ABSTRACT_PREFIX",
                "INITIAL_ACQUISITION",
                "INITIAL_MODEL_BUILD",
                "PREOPEN_COMMON_PREFIX",
            ],
            "production_direct_fallback_stage_missing": True,
            "following_required_occurrence_stages_missing": [
                "CLOSED_RECONCILIATION_AND_TERMINALIZATION"
            ],
            "complete_occurrence_stage_plan_satisfied": False,
            "v6_counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "formal_materializer_v1_called": False,
            "formal_materializer_v1_compatible": False,
            "formal_materializer_v1_expected_profile_native_zeros": 114,
            "direct_fallback_stage_zero_candidate_count": (
                EXPECTED_STAGE_ZERO_COUNT
            ),
            "route_generic_materializer_v2_required": True,
            "contract_local_source_gaps_narrowed": [
                "DURABLE_PROOF_TO_RAW_TRACE_IDENTITY_LINK_ACQUIRED_NOT_PRODUCTION_AUTHORITY",
                "RAW_ROUTE_DECISION_AND_UPPER_CANDIDATE_RETAINED_NOT_SEMANTIC_AUTHORITY",
            ],
            "readiness_blockers_remaining": [
                "SEMANTIC_ROLE_REGISTRATION_PENDING",
                "COUNTER_RECORD_SET_AUTHORITY_MISSING_ALL_202_PATHS",
                "DIRECT_FALLBACK_COMPLETE_BUNDLE_VERIFIER_MISSING",
                "DIRECT_FALLBACK_FORMAL_MATERIALIZER_MISSING",
                "EXACT_INFEASIBILITY_TERMINAL_AUTHORITY_MISSING",
                "FALLBACK_BOUNDARY_CATALOGUE_ONLY_PRODUCTION_SITE_NOT_EXECUTED",
                "FALLBACK_V1_WORK_VECTOR_NOT_K7_202_COUNTER_RECORDS",
                "LOGICAL_OCCURRENCE_CLOSURE_MISSING",
                "SHARED_RESOURCE_RECEIPT_SET_AUTHORITY_MISSING_9_PATHS",
            ],
            "terminal_artifact_issued": False,
            "logical_occurrence_closure_issued": False,
            "complete_bundle_verifier_issued": False,
            "central_domain_registration_pending": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "counter_completeness_gate_status": (
                COUNTER_COMPLETENESS_GATE_STATUS
            ),
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
            "sample_efficiency_gate_status": SAMPLE_EFFICIENCY_GATE_STATUS,
        }

    @property
    def acquisition_id(self) -> str:
        if _local_id(_ACQUISITION_DOMAIN, self._payload()) != self._acquisition_id:
            _fail("canonical fallback acquisition changed after issuance")
        return self._acquisition_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "canonical_infeasible_fallback_acquisition_id": self.acquisition_id,
        }


class _TracingKernel:
    """Retain every actual post-selection ground transition exactly once."""

    def __init__(self, inner: G2048Kernel) -> None:
        self.inner = inner
        self.rows: list[dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def step(self, state: G2048State, action: G2048Action) -> Any:
        outcomes = self.inner.step(state, action)
        self.rows.append(_trace_row(state, action, outcomes))
        return outcomes


def _state_document(state: G2048State) -> dict[str, Any]:
    return {"board": list(state.board), "status": state.status.value}


def _trace_row(state: G2048State, action: G2048Action, outcomes: Any) -> dict[str, Any]:
    rows = []
    for outcome in outcomes:
        features = dict(outcome.reward_features)
        if set(features) != {"merge"}:
            _fail("live canonical fallback emitted a noncanonical reward feature")
        rows.append(
            {
                "probability": outcome.probability,
                "next_state": _state_document(outcome.next_state),
                "reward": features["merge"],
                "failure": outcome.failure,
                "terminal": outcome.terminal,
            }
        )
    rows.sort(key=canonical_json_bytes)
    return {
        "state": _state_document(state),
        "action": {
            "first": action.first,
            "second": action.second,
            "survivor": action.survivor,
        },
        "outcomes": rows,
    }


def _expected_trace(proof: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    catalogue = {
        row["state_id"]: row["state"] for row in proof["kernel_profile"]["state_catalogue"]
    }
    result = []
    for row in proof["kernel_profile"]["transition_rows"]:
        outcomes = [
            {
                "probability": outcome["probability"],
                "next_state": catalogue[outcome["next_state_id"]],
                "reward": outcome["reward"],
                "failure": outcome["failure"],
                "terminal": outcome["terminal"],
            }
            for outcome in row["outcomes"]
        ]
        outcomes.sort(key=canonical_json_bytes)
        result.append(
            {
                "state": catalogue[row["state_id"]],
                "action": row["action"],
                "outcomes": outcomes,
            }
        )
    result.sort(key=canonical_json_bytes)
    return tuple(result)


def _canonical_query(kernel: G2048Kernel) -> QuerySpec[G2048State]:
    return QuerySpec(
        kernel.initial_distribution(),
        1,
        (("merge", Fraction(1)),),
        "default",
        Fraction(1, 20),
        Fraction(1),
        "g2048.canonical.merge_le_1_per_step.total_le_h.v1",
    )


def _verify_initial_law(query: QuerySpec[G2048State], proof: Mapping[str, Any]) -> None:
    actual = tuple(
        sorted(
            (
                {"probability": probability, "state": _state_document(state)}
                for probability, state in query.initial_distribution
            ),
            key=canonical_json_bytes,
        )
    )
    expected = tuple(
        sorted(
            (
                {"probability": row["probability"], "state": row["state"]}
                for row in proof["query_profile"]["initial_distribution"]
            ),
            key=canonical_json_bytes,
        )
    )
    query_profile = proof["query_profile"]
    threshold_profile = proof["threshold_profile"]
    reward_profile = proof["reward_profile"]
    actual_rewards = [
        {"feature": feature, "coefficient": coefficient}
        for feature, coefficient in query.reward_weights
    ]
    if (
        actual != expected
        or query.horizon != query_profile["horizon"]
        or query.goal != query_profile["goal"]
        or query.delta != threshold_profile["delta"]
        or actual_rewards != reward_profile["reward_weights"]
        or query.normalizer != reward_profile["normalizer"]
        or query.normalizer_proof_id != reward_profile["normalizer_proof_id"]
    ):
        _fail("live canonical query semantics differ from durable proof")


def build_current_canonical_fallback_identity_v1(
    phase05_bundle_root: str | Path,
    *,
    build_epoch_id: str | None = None,
    threshold_profile_id: str | None = None,
    reward_profile_id: str | None = None,
    policy_class_id: str | None = None,
    complete_search_profile_id: str | None = None,
) -> CanonicalFallbackCurrentIdentityV1:
    """Build a current source/live-kernel identity independently of a claim.

    The current root is supplied separately from the proof under assessment.
    Its bundle integrity, exact projection, and live kernel transition law are
    replayed before its typed identity is returned.  A claimant proof is never
    allowed to nominate itself as the current identity.
    """

    _require_unsubstituted_raw_callables()
    explicit_components = {
        "BuildEpoch_id": _cid(build_epoch_id, "explicit current BuildEpoch"),
        "threshold_profile_id": _cid(
            threshold_profile_id, "explicit current threshold profile"
        ),
        "reward_profile_id": _cid(
            reward_profile_id, "explicit current reward profile"
        ),
        "policy_class_id": _cid(
            policy_class_id, "explicit current policy class"
        ),
        "complete_search_profile_id": _cid(
            complete_search_profile_id, "explicit current search profile"
        ),
    }
    current_raw = issue_phase3e_exact_infeasibility_durable_proof_v1(
        Path(phase05_bundle_root)
    )
    try:
        current_document = loads_canonical_json(current_raw)
        if type(current_document) is not dict:
            raise ValueError("current identity projection is not an object")
        identity = DurableExactInfeasibilityIdentityV1.from_dict(
            current_document["identity"]
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error(
            "current canonical source identity failed typed replay"
        ) from error
    verified = verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
        current_raw,
        current_identity=identity,
    )
    if verified.result.outcome is not DurableProofVerificationOutcomeV1.IDENTICAL_MATCH:
        _fail("fresh current canonical source failed its integrity/semantic replay")
    actual_components = {
        "BuildEpoch_id": identity.build_epoch_id,
        "threshold_profile_id": identity.threshold_profile_id,
        "reward_profile_id": identity.reward_profile_id,
        "policy_class_id": identity.policy_class_id,
        "complete_search_profile_id": identity.complete_search_profile_id,
    }
    if explicit_components != actual_components:
        _fail("explicit current identity components differ from current source")
    kernel = G2048Kernel(2)
    query = _canonical_query(kernel)
    _verify_initial_law(query, current_document)
    live_initial_law = tuple(
        sorted(
            (
                {"probability": probability, "state": _state_document(state)}
                for probability, state in query.initial_distribution
            ),
            key=canonical_json_bytes,
        )
    )
    actual_rows: list[dict[str, Any]] = []
    catalogue = {
        row["state_id"]: row["state"]
        for row in current_document["kernel_profile"]["state_catalogue"]
    }
    for row in current_document["kernel_profile"]["transition_rows"]:
        state_document = catalogue[row["state_id"]]
        state = G2048State(
            tuple(state_document["board"]),
            G2048Status(state_document["status"]),
        )
        action = G2048Action(
            row["action"]["first"],
            row["action"]["second"],
            row["action"]["survivor"],
        )
        actual_rows.append(_trace_row(state, action, kernel.step(state, action)))
    live_transition_rows = tuple(sorted(actual_rows, key=canonical_json_bytes))
    if live_transition_rows != _expected_trace(current_document):
        _fail("current live kernel differs from the current source identity")
    return CanonicalFallbackCurrentIdentityV1(
        _CURRENT_IDENTITY_ISSUER,
        identity,
        hashlib.sha256(current_raw).hexdigest(),
        _support_id("current-live-initial-law", list(live_initial_law)),
        _support_id("current-live-transition-law", list(live_transition_rows)),
    )


def _typed_current_identity(
    value: object | None,
) -> CanonicalFallbackCurrentIdentityV1:
    if value is None:
        _fail("fresh current identity is required; claimant self-match is forbidden")
    if type(value) is not CanonicalFallbackCurrentIdentityV1:
        _fail(
            "claimant self-match is forbidden; current identity requires an "
            "issuer-owned live/source attestation"
        )
    _cid(value.attestation_id, "current identity attestation")
    DurableExactInfeasibilityIdentityV1.from_dict(value.identity.to_dict())
    return value


def _proof_document(
    proof_bytes: bytes,
    *,
    current_identity: object | None,
) -> tuple[dict[str, Any], Any, CanonicalFallbackCurrentIdentityV1]:
    if type(proof_bytes) is not bytes or not proof_bytes:
        _fail("durable proof bytes are missing")
    current = _typed_current_identity(current_identity)
    verified = verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
        proof_bytes,
        current_identity=current.identity,
    )
    if verified.result.outcome is DurableProofVerificationOutcomeV1.NO_MATCH:
        _fail("durable proof does not match the fresh current live/build identity")
    if verified.result.outcome is not DurableProofVerificationOutcomeV1.IDENTICAL_MATCH:
        _fail("durable exact-infeasibility proof failed independent replay")
    try:
        document = loads_canonical_json(proof_bytes)
    except (TypeError, ValueError) as error:
        raise ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error(
            "durable proof bytes are noncanonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != proof_bytes:
        _fail("durable proof bytes are noncanonical")
    if (
        document.get("claim", {}).get("outcome") != "INFEASIBLE_CERTIFIED"
        or document.get("claim", {}).get("search_complete") is not True
        or document.get("claim", {}).get("cap_exhausted") is not False
        or document.get("complete_search_profile", {}).get("algorithm")
        != "complete_h1_deterministic_markov_enumeration"
    ):
        _fail("durable proof is not the canonical complete H1 infeasibility witness")
    if verified.proof_identity != current.identity:
        _fail("durable verifier returned IDENTICAL_MATCH for another current identity")
    return document, verified, current


def _exact_cardinalities(proof: Mapping[str, Any]) -> dict[str, int]:
    profile = proof["complete_search_profile"]
    initial = proof["query_profile"]["initial_distribution"]
    state_count = len(initial)
    transition_count = profile["transition_count"]
    outcome_count = profile["positive_outcome_count"]
    if (
        state_count != 8
        or transition_count != 16
        or outcome_count != 96
        or any(row.get("remaining") != 1 for row in proof["kernel_profile"]["transition_rows"])
    ):
        _fail("canonical H1 cardinality source changed")
    # In the registered H1 occupancy-frontier solver each state/action row
    # incurs one state expansion per initial state, one action evaluation,
    # one transition, and one candidate composition.  Each expansion and each
    # of those three action operations performs one finite-cap guard.
    return {
        "common.protocol_checks": 5,
        "fallback.actions_evaluated": transition_count,
        "fallback.bellman_backups": transition_count,
        "fallback.composed_candidates": transition_count,
        "fallback.ground_steps": transition_count,
        "fallback.outcome_rows": outcome_count,
        "fallback.states_expanded": state_count,
        "control.cap_checks": state_count + 3 * transition_count,
        "control.cap_rejections": 0,
    }


def _default_cap(cardinalities: Mapping[str, int]) -> GroundFallbackCapProfileV1:
    return GroundFallbackCapProfileV1(
        max_states_expanded=cardinalities["fallback.states_expanded"],
        max_actions_evaluated=cardinalities["fallback.actions_evaluated"],
        max_ground_steps=cardinalities["fallback.ground_steps"],
        max_outcome_rows=cardinalities["fallback.outcome_rows"],
        max_bellman_backups=cardinalities["fallback.bellman_backups"],
        max_composed_candidates=cardinalities["fallback.composed_candidates"],
        max_cap_checks=cardinalities["control.cap_checks"],
        max_positive_outcomes_per_step=6,
    )


def _preexecution_candidate(
    proof: Mapping[str, Any],
    *,
    current_identity: CanonicalFallbackCurrentIdentityV1,
    cap_profile: GroundFallbackCapProfileV1 | None,
) -> CanonicalDirectFallbackPreexecutionCandidateV1:
    identity = proof["identity"]
    proof_id = proof["durable_exact_infeasibility_proof_id"]
    exact = _exact_cardinalities(proof)
    cap = cap_profile or _default_cap(exact)
    GroundFallbackCapProfileV1.from_dict(cap.to_dict())
    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    cap_id = cap.ground_fallback_cap_profile_id
    occurrence_id = _support_id(
        "logical-occurrence",
        {"durable_proof_id": proof_id, "ground_fallback_cap_profile_id": cap_id},
    )
    attempt_id = _support_id(
        "route-attempt",
        {"logical_occurrence_id": occurrence_id, "attempt_index": 1},
    )
    context = RouteDecisionContextV1(
        _support_id("preregistration", {"durable_proof_id": proof_id}),
        _support_id("protocol", {"contract": PROPOSED_CONTRACT_VERSION}),
        comparison.comparison_profile_id,
        registry.registry_id,
        identity["structural_id"],
        identity["query_id"],
        _support_id(
            "selected-plan",
            {
                "kind": "CANONICAL_PHASE05_MANDATORY_DIRECT_FALLBACK",
                "durable_proof_id": proof_id,
            },
        ),
        identity["threshold_profile_id"],
        identity["BuildEpoch_id"],
        occurrence_id,
        attempt_id,
    )
    point = DecisionPointV1(
        context.route_decision_context_id,
        TypedNotApplicable("direct fallback has no local transaction"),
        TypedNotApplicable("direct fallback has no local frontier"),
        TypedNotApplicable("direct fallback has no causal search"),
        _support_id(
            "common-prefix-work-root",
            {
                "logical_occurrence_id": occurrence_id,
                "scope": "OUTSIDE_THIS_MARGINAL_ACQUISITION",
            },
        ),
    )
    cardinality_source_payload = {
        "schema": "acfqp.construction_k7_canonical_infeasible_fallback_cardinality_source.v1",
        "schema_version": SCHEMA_VERSION,
        "durable_proof_id": proof_id,
        "RouteDecisionContext_id": context.route_decision_context_id,
        "decision_point_id": point.decision_point_id,
        "ground_fallback_cap_profile_id": cap_id,
        "formula": "H1: states=initial states; actions=transitions; outcomes=sum rows; candidates=transitions; cap_checks=states+3*transitions",
        "exact_cardinalities": [
            {"name": name, "value": value} for name, value in sorted(exact.items())
        ],
        "measured_before_execution": True,
        "depends_on_actual_route_work": False,
        "central_domain_registration_pending": False,
    }
    cardinality_source_id = _local_id(
        _CARDINALITY_SOURCE_DOMAIN, cardinality_source_payload
    )
    bound = GroundFallbackCardinalityBoundV1(
        context.route_decision_context_id,
        point.decision_point_id,
        cap_id,
        tuple((name, exact[name]) for name in (
            "common.protocol_checks",
            "fallback.actions_evaluated",
            "fallback.bellman_backups",
            "fallback.composed_candidates",
            "fallback.ground_steps",
            "fallback.outcome_rows",
            "fallback.states_expanded",
            "control.cap_checks",
        )),
        (cardinality_source_id,),
    )
    cardinality = build_ground_fallback_cardinality_evidence_v1(
        context=context,
        decision_point=point,
        cap_profile=cap,
        bound=bound,
    )
    formula = official_route_upper_formula_v1(
        RouteKind.DIRECT_FALLBACK,
        registry=registry,
        profile=comparison,
        cap_profile=cap,
    )
    upper, upper_proof = derive_route_upper_v1(
        context=context,
        decision_point=point,
        cardinality=cardinality,
        cap_profile=cap,
        registry=registry,
        profile=comparison,
        formula=formula,
    )
    decision = MarginalRouteDecisionV1.select(
        point, upper, causal=None, local_upper=None
    )
    return CanonicalDirectFallbackPreexecutionCandidateV1(
        _PREEXECUTION_ISSUER,
        proof_id,
        current_identity,
        cardinality_source_id,
        context,
        point,
        cap,
        bound,
        cardinality,
        formula,
        upper,
        upper_proof,
        decision,
    )


def replay_canonical_direct_fallback_preexecution_candidate_v1(
    proof_bytes: bytes,
    *,
    current_identity: CanonicalFallbackCurrentIdentityV1 | None = None,
    cap_profile: GroundFallbackCapProfileV1 | None = None,
) -> CanonicalDirectFallbackPreexecutionCandidateV1:
    """Independently reissue the canonical pre-execution authority.

    This is the narrow evaluation-lane replay boundary for downstream
    construction artifacts that need the typed pre-execution decision but
    must not trust a supplied candidate object's type or self-reported
    content ID.  The durable proof and the separately issued current identity
    are both replayed before a new issuer-owned candidate is returned.  No
    fallback transition is executed here.
    """

    _require_unsubstituted_raw_callables()
    proof, _verified, current = _proof_document(
        proof_bytes,
        current_identity=current_identity,
    )
    return _preexecution_candidate(
        proof,
        current_identity=current,
        cap_profile=cap_profile,
    )


def _verify_live_execution(
    *,
    execution: GroundFallbackExecutionV1,
    trace_rows: tuple[dict[str, Any], ...],
    proof: Mapping[str, Any],
    preexecution: CanonicalDirectFallbackPreexecutionCandidateV1,
) -> str:
    registry = official_counter_registry_v1()
    try:
        result = GroundFallbackResultV1.from_dict(execution.result.to_dict())
        work = WorkVectorV1.from_dict(execution.work_vector.to_dict(), registry)
    except (TypeError, ValueError) as error:
        raise ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error(
            f"real fallback execution failed exact V1 replay: {error}"
        ) from error
    expected_trace = _expected_trace(proof)
    actual_trace = tuple(sorted(trace_rows, key=canonical_json_bytes))
    expected_trace_keys = [canonical_json_bytes(row) for row in expected_trace]
    actual_trace_keys = [canonical_json_bytes(row) for row in actual_trace]
    trace_is_subset = all(
        actual_trace_keys.count(key) <= expected_trace_keys.count(key)
        for key in set(actual_trace_keys)
    )
    trace_payload = {
        "schema": "acfqp.construction_k7_canonical_infeasible_fallback_transition_trace.v1",
        "schema_version": SCHEMA_VERSION,
        "durable_proof_id": preexecution.durable_proof_id,
        "route_decision_id": preexecution.decision.route_decision_id,
        "selected_upper_id": preexecution.upper.route_upper_bound_envelope_id,
        "ground_fallback_result_id": result.ground_fallback_result_id,
        "ordered_transition_rows": list(actual_trace),
        "matches_complete_durable_transition_rows": actual_trace == expected_trace,
        "is_duplicate_safe_subset_of_durable_transition_rows": trace_is_subset,
        "central_domain_registration_pending": False,
    }
    trace_id = _local_id(_TRACE_DOMAIN, trace_payload)
    actual = work.values
    leaf_upper = dict(preexecution.upper_proof.leaf_upper_bounds)
    if (
        result != execution.result
        or work != execution.work_vector
        or result.query_id != proof["identity"]["query_id"]
        or result.ground_fallback_cap_profile_id
        != preexecution.cap_profile.ground_fallback_cap_profile_id
        or not trace_is_subset
        or actual["fallback.ground_steps"] != len(actual_trace)
        or actual["fallback.outcome_rows"]
        != sum(len(row["outcomes"]) for row in actual_trace)
        or any(
            actual[path] > leaf_upper[path]
            for path in _NATIVE_EVENT_PATHS
        )
    ):
        _fail("real fallback result/work/trace differs from its frozen exact source")
    if result.outcome is GroundFallbackOutcome.INFEASIBLE_CERTIFIED:
        exact = _exact_cardinalities(proof)
        actual_frontier = tuple(
            sorted(
                (
                    point.expected_reward,
                    point.failure_probability,
                )
                for point in result.frontier
            )
        )
        expected_frontier = tuple(
            sorted(
                (
                    row["expected_reward"],
                    row["failure_probability"],
                )
                for row in proof["claimed_frontier"]
            )
        )
        if (
            actual_trace != expected_trace
            or len(actual_trace_keys) != len(set(actual_trace_keys))
            or result.search_complete is not True
            or result.cap_exhausted_name is not None
            or result.selected_policy_signature
            or result.selected_failure_probability is not None
            or result.selected_expected_reward is not None
            or result.composed_candidate_count
            != exact["fallback.composed_candidates"]
            or actual_frontier != expected_frontier
            or any(actual[path] != exact[path] for path in _NATIVE_EVENT_PATHS)
        ):
            _fail("INFEASIBLE_CERTIFIED execution is not the exact complete H1 search")
    elif result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED:
        if (
            result.search_complete is not False
            or result.frontier
            or result.selected_policy_signature
            or execution.selected_policy is not None
        ):
            _fail("CAP_EXHAUSTED execution leaked a certificate or policy")
    else:
        _fail("canonical infeasible fallback unexpectedly produced a feasible policy")
    return trace_id


def _path_partition(
    *,
    preexecution: CanonicalDirectFallbackPreexecutionCandidateV1,
    execution: GroundFallbackExecutionV1,
    transition_trace_id: str,
) -> tuple[CanonicalFallbackPathEvidenceV1, ...]:
    v1 = official_counter_registry_v1()
    v6 = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(v6)
    allowed = set(
        stage.by_stage[
            registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK
        ].allowed_nonzero_paths
    )
    forbidden = set(v6.required_paths) - allowed
    if (
        len(forbidden) != EXPECTED_STAGE_ZERO_COUNT
        or allowed
        != set(_NATIVE_EVENT_PATHS)
        | set(_EXACT_DERIVED_PATHS)
        | set(_SHARED_RESOURCE_PATHS)
        | set(_UNRESOLVED_PROCESS_DERIVED_PATHS)
    ):
        _fail("V6 direct-fallback stage partition changed")
    v1_by_path = {row.path: row for row in execution.work_vector.records}
    values = execution.work_vector.values
    result = execution.result
    success = int(result.outcome is not GroundFallbackOutcome.CAP_EXHAUSTED)
    failure = 1 - success
    derived = {
        "route.attempts": 1,
        "route.successes": success,
        "route.failures": failure,
        "solver.attempts": 1,
        "solver.successes": success,
        "solver.failures": failure,
    }
    formulas = {
        "route.attempts": "one selected direct-fallback invocation",
        "route.successes": "1 iff selected fallback search completed without cap exhaustion",
        "route.failures": "route.attempts - route.successes",
        "solver.attempts": "one real ground fallback solver invocation",
        "solver.successes": "1 iff exhaustive solver completed without cap exhaustion",
        "solver.failures": "solver.attempts - solver.successes",
    }
    context_id = _support_id(
        "path-acquisition-context",
        {
            "preexecution_candidate_id": preexecution.candidate_id,
            "ground_fallback_result_id": result.ground_fallback_result_id,
            "source_v1_work_vector_id": execution.work_vector.work_vector_id,
            "transition_trace_id": transition_trace_id,
        },
    )
    rows: list[CanonicalFallbackPathEvidenceV1] = []
    for path in v6.required_paths:
        leaf = v6.by_path[path]
        if path in forbidden:
            disposition = (
                FallbackPathDispositionV1.STAGE_FORBIDDEN_ZERO_CANDIDATE_UNRESOLVED
            )
            value: int | None = None
            sources = (
                preexecution.decision.route_decision_id,
                stage.stage_profile_id,
            )
            formula = None
            blocker = (
                "STAGE_PROFILE_ZERO_CANDIDATE_REQUIRES_PRODUCTION_V6_NATIVE_ZERO_ATTESTATION_AND_COMPLETE_SIDE_EFFECT_MONITOR"
            )
        elif path in _NATIVE_EVENT_PATHS:
            source = v1_by_path[path]
            v1_leaf = v1.by_path[path]
            if v1_leaf.to_dict() != leaf.to_dict():
                _fail("V1/V6 preserved native-event leaf metadata changed")
            disposition = (
                FallbackPathDispositionV1.SOURCE_BOUND_LEGACY_NATIVE_VALUE_CANDIDATE
            )
            value = values[path]
            sources = (
                source.record_id,
                execution.work_vector.work_vector_id,
                transition_trace_id,
            )
            formula = None
            blocker = (
                "EXACT_LEGACY_SOURCE_VALUE_REQUIRES_PRODUCTION_V6_RECORDER_AND_FRESH_COUNTER_RECORD_AUTHORITY"
            )
        elif path in _EXACT_DERIVED_PATHS:
            disposition = (
                FallbackPathDispositionV1.SOURCE_BOUND_LEGACY_RECONCILIATION_VALUE_CANDIDATE
            )
            value = derived[path]
            sources = (
                result.ground_fallback_result_id,
                execution.work_vector.work_vector_id,
            )
            formula = formulas[path]
            blocker = (
                "EXACT_LEGACY_RECONCILIATION_VALUE_REQUIRES_PRODUCTION_DERIVED_AUTHORITY_AND_V6_DEPENDENCIES"
            )
        elif path in _SHARED_RESOURCE_PATHS:
            disposition = (
                FallbackPathDispositionV1.UNRESOLVED_SHARED_RESOURCE_RECEIPT
            )
            value = None
            sources = ()
            formula = None
            blocker = (
                "DIRECT_FALLBACK_SHARED_RESOURCE_RECEIPT_NOT_CONNECTED; "
                "legacy V1 zero is not a V6 native-zero or measurement receipt"
            )
        else:
            assert path in _UNRESOLVED_PROCESS_DERIVED_PATHS
            disposition = (
                FallbackPathDispositionV1.UNRESOLVED_PROCESS_DERIVED_PROOF
            )
            value = None
            sources = ()
            formula = None
            blocker = (
                "PROCESS_EXIT_RECONCILIATION_REQUIRES_PROCESS_LAUNCH_RECEIPT"
            )
        rows.append(
            CanonicalFallbackPathEvidenceV1(
                _PATH_ISSUER,
                context_id,
                path,
                leaf.semantics_id,
                leaf.owner,
                leaf.unit,
                leaf.lane.value,
                leaf.scope,
                leaf.reducer.value,
                leaf.comparison_axis,
                disposition,
                value,
                sources,
                formula,
                blocker,
            )
        )
    return tuple(rows)


def acquire_canonical_infeasible_direct_fallback_v1(
    proof_bytes: bytes,
    *,
    current_identity: CanonicalFallbackCurrentIdentityV1 | None = None,
    cap_profile: GroundFallbackCapProfileV1 | None = None,
) -> CanonicalInfeasibleFallbackAcquisitionV1:
    """Freeze a raw fallback decision, execute it, and partition 202 paths."""

    _require_unsubstituted_raw_callables()
    proof, _verified, current = _proof_document(
        proof_bytes,
        current_identity=current_identity,
    )
    preexecution = _preexecution_candidate(
        proof,
        current_identity=current,
        cap_profile=cap_profile,
    )
    if preexecution.decision.selected_route is not RouteSelection.FALLBACK:
        _fail("preexecution candidate did not freeze the fallback route")

    raw_kernel = G2048Kernel(2)
    query = _canonical_query(raw_kernel)
    _verify_initial_law(query, proof)
    traced_kernel = _TracingKernel(raw_kernel)
    # This is the only ground transition boundary in the producer.  It occurs
    # strictly after ``preexecution.candidate_id`` and the route decision have
    # been frozen above.
    _ = preexecution.candidate_id
    execution = run_ground_fallback_search_v1(
        traced_kernel,
        query,
        route_decision_context_id=(
            preexecution.route_context.route_decision_context_id
        ),
        decision_point_id=preexecution.decision_point.decision_point_id,
        route_decision_id=preexecution.decision.route_decision_id,
        selected_upper_id=preexecution.upper.route_upper_bound_envelope_id,
        route_attempt_id=preexecution.route_context.route_attempt_id,
        query_id=proof["identity"]["query_id"],
        cap_profile=preexecution.cap_profile,
        registry=official_counter_registry_v1(),
        recorder_id="canonical-infeasible-fallback-source-v1",
    )
    trace_rows = tuple(traced_kernel.rows)
    trace_id = _verify_live_execution(
        execution=execution,
        trace_rows=trace_rows,
        proof=proof,
        preexecution=preexecution,
    )
    paths = _path_partition(
        preexecution=preexecution,
        execution=execution,
        transition_trace_id=trace_id,
    )
    outcome = (
        "EXACT_INFEASIBILITY_RAW_SOURCE_VALUES_ACQUIRED"
        if execution.result.outcome is GroundFallbackOutcome.INFEASIBLE_CERTIFIED
        else "CAP_EXHAUSTED_NONCERTIFICATE_ACQUISITION"
        if execution.result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED
        else "WRONG_FALLBACK_OUTCOME_BLOCKED"
    )
    return CanonicalInfeasibleFallbackAcquisitionV1(
        _ACQUISITION_ISSUER,
        hashlib.sha256(proof_bytes).hexdigest(),
        preexecution,
        trace_id,
        execution,
        paths,
        outcome,
    )


def verify_canonical_infeasible_direct_fallback_acquisition_bytes_v1(
    *,
    raw: bytes,
    proof_bytes: bytes,
    current_identity: CanonicalFallbackCurrentIdentityV1 | None = None,
    cap_profile: GroundFallbackCapProfileV1 | None = None,
) -> CanonicalInfeasibleFallbackAcquisitionV1:
    """Evaluation-lane full replay; no replay work is operationally charged."""

    if type(raw) is not bytes or not raw:
        _fail("fallback acquisition bytes are missing")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error(
            "fallback acquisition bytes are noncanonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("fallback acquisition bytes are noncanonical")
    replayed = acquire_canonical_infeasible_direct_fallback_v1(
        proof_bytes,
        current_identity=current_identity,
        cap_profile=cap_profile,
    )
    if document != replayed.to_document():
        _fail("fallback acquisition bytes differ from independent full replay")
    return replayed


__all__ = (
    "CanonicalDirectFallbackPreexecutionCandidateV1",
    "CanonicalFallbackCurrentIdentityV1",
    "CanonicalFallbackPathEvidenceV1",
    "CanonicalInfeasibleFallbackAcquisitionV1",
    "ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error",
    "EXPECTED_EXACT_DERIVED_COUNT",
    "EXPECTED_EXACT_SOURCE_VALUE_COUNT",
    "EXPECTED_FORMALLY_RESOLVED_PATH_COUNT",
    "EXPECTED_NATIVE_EVENT_COUNT",
    "EXPECTED_REQUIRED_PATH_COUNT",
    "EXPECTED_SHARED_RESOURCE_BLOCKER_COUNT",
    "EXPECTED_STAGE_ZERO_COUNT",
    "EXPECTED_UNRESOLVED_COUNT",
    "FallbackPathDispositionV1",
    "REGISTERED_DOMAINS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "acquire_canonical_infeasible_direct_fallback_v1",
    "build_current_canonical_fallback_identity_v1",
    "replay_canonical_direct_fallback_preexecution_candidate_v1",
    "verify_canonical_infeasible_direct_fallback_acquisition_bytes_v1",
)
