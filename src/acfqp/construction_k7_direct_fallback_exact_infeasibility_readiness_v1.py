"""Fail-closed readiness authority for a K7 exact-infeasible fallback path.

Contract 2.0.39 asks whether the current direct-ground fallback can already
close a *production-native* K7 occurrence as
``INFEASIBILITY_CERTIFICATE/FULL_GROUND_EXACT_INFEASIBLE``.  It cannot.  The
current code has three useful but non-interchangeable objects:

* an independently replayable durable exact-infeasibility proof;
* a legacy ``GroundFallbackExecutionV1`` with a 42-leaf V1 WorkVector; and
* a source/AST catalogue locating the fallback and terminal boundaries.

None of those objects emits the route-specific 202 ``CounterRecordV1`` rows,
the nine shared-resource receipts, or the terminal/occurrence chain required
by the Contract-2.0.33 all-path profile.  This module records that fact as a
typed, independently reproducible blocker.  It deliberately has no READY
outcome and no API capable of minting a WorkVector, ComparisonVector, terminal
artifact, or logical-occurrence closure.

The assessment parses already-produced fallback output but never calls the
ground solver.  Durable-proof replay is evaluation-lane evidence and is never
charged or presented as operational route work.  ``CAP_EXHAUSTED`` remains a
noncertificate even when all other identities happen to match.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import WorkVectorV1, official_counter_registry_v1
from acfqp import construction_k7_all_path_accounting_profile_v1 as profile_v1
from acfqp import construction_k7_all_path_operation_boundary_manifest_v1 as boundary_v1
from acfqp.phase3e_exact_infeasibility_durable_proof_v1 import (
    DurableExactInfeasibilityIdentityV1,
    DurableProofVerificationOutcomeV1,
    VerifiedDurableExactInfeasibilityHandleV1,
    classify_legacy_ground_fallback_portability_v1,
    verify_phase3e_exact_infeasibility_durable_proof_bytes_v1,
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackExecutionV1,
    GroundFallbackOutcome,
    GroundFallbackResultV1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_DIRECT_FALLBACK_EXACT_INFEASIBILITY_READINESS_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)
from acfqp.routing_v1 import TerminalClass, TerminalCode


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.39"
PROFILE_KEY = "construction_k7_direct_fallback_exact_infeasibility_readiness_v1"

EXPECTED_K7_COUNTER_RECORD_COUNT = 202
EXPECTED_COMPARISON_AXIS_COUNT = 8

COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

_ISSUER = object()


class ConstructionK7DirectFallbackExactInfeasibilityReadinessV1Error(ValueError):
    """The supplied evidence or fail-closed assessment is malformed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7DirectFallbackExactInfeasibilityReadinessV1Error(message)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class DirectFallbackReadinessOutcomeV1(str, Enum):
    BLOCKED = "BLOCKED"


class DirectFallbackBlockerCodeV1(str, Enum):
    DURABLE_PROOF_INVALID = "DURABLE_PROOF_INVALID"
    DURABLE_PROOF_IDENTITY_MISMATCH = "DURABLE_PROOF_IDENTITY_MISMATCH"
    FALLBACK_EXECUTION_ABSENT = "FALLBACK_EXECUTION_ABSENT"
    FALLBACK_QUERY_ID_NOT_IDENTICAL = "FALLBACK_QUERY_ID_NOT_IDENTICAL"
    FALLBACK_OUTCOME_NOT_INFEASIBLE = "FALLBACK_OUTCOME_NOT_INFEASIBLE"
    FALLBACK_CAP_EXHAUSTED_NONCERTIFICATE = "FALLBACK_CAP_EXHAUSTED_NONCERTIFICATE"
    FALLBACK_SEARCH_COMPLETENESS_NOT_DURABLE = (
        "FALLBACK_SEARCH_COMPLETENESS_NOT_DURABLE"
    )
    FALLBACK_V1_WORK_VECTOR_NOT_K7_202_COUNTER_RECORDS = (
        "FALLBACK_V1_WORK_VECTOR_NOT_K7_202_COUNTER_RECORDS"
    )
    ROUTE_DECISION_AND_UPPER_CHAIN_NOT_RETAINED = (
        "ROUTE_DECISION_AND_UPPER_CHAIN_NOT_RETAINED"
    )
    FALLBACK_BOUNDARY_CATALOGUE_ONLY = "FALLBACK_BOUNDARY_CATALOGUE_ONLY"
    COUNTER_RECORD_SET_AUTHORITY_MISSING = "COUNTER_RECORD_SET_AUTHORITY_MISSING"
    SHARED_RESOURCE_RECEIPT_SET_AUTHORITY_MISSING = (
        "SHARED_RESOURCE_RECEIPT_SET_AUTHORITY_MISSING"
    )
    DIRECT_FALLBACK_FORMAL_MATERIALIZER_MISSING = (
        "DIRECT_FALLBACK_FORMAL_MATERIALIZER_MISSING"
    )
    DIRECT_FALLBACK_COMPLETE_BUNDLE_VERIFIER_MISSING = (
        "DIRECT_FALLBACK_COMPLETE_BUNDLE_VERIFIER_MISSING"
    )
    EXACT_INFEASIBILITY_TERMINAL_AUTHORITY_MISSING = (
        "EXACT_INFEASIBILITY_TERMINAL_AUTHORITY_MISSING"
    )
    LOGICAL_OCCURRENCE_CLOSURE_MISSING = "LOGICAL_OCCURRENCE_CLOSURE_MISSING"


class EvidenceRoleStateV1(str, Enum):
    EVALUATION_VERIFIED_IDENTITY_MATCH_NOT_OPERATIONAL = (
        "EVALUATION_VERIFIED_IDENTITY_MATCH_NOT_OPERATIONAL"
    )
    EVALUATION_INVALID_OR_IDENTITY_MISMATCH = (
        "EVALUATION_INVALID_OR_IDENTITY_MISMATCH"
    )
    LEGACY_RESULT_PRESENT_NOT_DURABLE = "LEGACY_RESULT_PRESENT_NOT_DURABLE"
    CAP_EXHAUSTED_NONCERTIFICATE = "CAP_EXHAUSTED_NONCERTIFICATE"
    WRONG_FALLBACK_OUTCOME = "WRONG_FALLBACK_OUTCOME"
    NOT_RETAINED = "NOT_RETAINED"
    ROUTE_SPECIFIC_AUTHORITY_MISSING = "ROUTE_SPECIFIC_AUTHORITY_MISSING"


@dataclass(frozen=True, slots=True, order=True)
class DirectFallbackBlockerV1:
    code: DirectFallbackBlockerCodeV1
    evidence_role: str
    detail: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "code", DirectFallbackBlockerCodeV1(self.code))
        except (TypeError, ValueError) as error:
            raise ConstructionK7DirectFallbackExactInfeasibilityReadinessV1Error(
                "unknown direct-fallback blocker code"
            ) from error
        if not all(type(value) is str and value for value in (self.evidence_role, self.detail)):
            _fail("direct-fallback blocker text must be nonempty")

    def to_document(self) -> dict[str, str]:
        return {
            "code": self.code.value,
            "evidence_role": self.evidence_role,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True, order=True)
class EvidenceRoleDispositionV1:
    role: str
    required_outcome: str
    state: EvidenceRoleStateV1

    def __post_init__(self) -> None:
        if not all(type(value) is str and value for value in (self.role, self.required_outcome)):
            _fail("evidence-role disposition text must be nonempty")
        try:
            object.__setattr__(self, "state", EvidenceRoleStateV1(self.state))
        except (TypeError, ValueError) as error:
            raise ConstructionK7DirectFallbackExactInfeasibilityReadinessV1Error(
                "unknown evidence-role state"
            ) from error

    def to_document(self) -> dict[str, str]:
        return {
            "role": self.role,
            "required_outcome": self.required_outcome,
            "state": self.state.value,
        }


@dataclass(frozen=True, slots=True)
class ConstructionK7DirectFallbackExactInfeasibilityReadinessV1:
    """A source-bound negative result; by construction it cannot be READY."""

    _issuer: object = field(repr=False, compare=False)
    all_path_accounting_profile_id: str
    operation_boundary_manifest_id: str
    operation_boundary_source_archive_id: str
    fallback_boundary_site_id: str
    terminal_boundary_site_id: str
    durable_proof_verification_id: str
    durable_proof_outcome: str
    durable_proof_id: str | None
    exact_infeasibility_identity_id: str | None
    fallback_result_id: str | None
    fallback_work_vector_id: str | None
    fallback_query_id: str | None
    fallback_outcome: str | None
    fallback_v1_counter_record_count: int
    fallback_portability_blocker_id: str | None
    evidence_role_dispositions: tuple[EvidenceRoleDispositionV1, ...]
    blockers: tuple[DirectFallbackBlockerV1, ...]
    outcome: DirectFallbackReadinessOutcomeV1 = DirectFallbackReadinessOutcomeV1.BLOCKED

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("direct-fallback readiness assessment is caller-minted")
        try:
            object.__setattr__(self, "outcome", DirectFallbackReadinessOutcomeV1(self.outcome))
        except (TypeError, ValueError) as error:
            raise ConstructionK7DirectFallbackExactInfeasibilityReadinessV1Error(
                "readiness outcome must remain BLOCKED"
            ) from error
        ids = (
            self.all_path_accounting_profile_id,
            self.operation_boundary_manifest_id,
            self.operation_boundary_source_archive_id,
            self.fallback_boundary_site_id,
            self.terminal_boundary_site_id,
            self.durable_proof_verification_id,
        )
        optional_ids = (
            self.durable_proof_id,
            self.exact_infeasibility_identity_id,
            self.fallback_result_id,
            self.fallback_work_vector_id,
            self.fallback_query_id,
            self.fallback_portability_blocker_id,
        )
        try:
            for value in ids:
                parse_content_id(value)
            for value in optional_ids:
                if value is not None:
                    parse_content_id(value)
            DurableProofVerificationOutcomeV1(self.durable_proof_outcome)
            if self.fallback_outcome is not None:
                GroundFallbackOutcome(self.fallback_outcome)
        except (TypeError, ValueError) as error:
            raise ConstructionK7DirectFallbackExactInfeasibilityReadinessV1Error(
                "readiness assessment contains an invalid identity or outcome"
            ) from error
        if type(self.fallback_v1_counter_record_count) is not int or self.fallback_v1_counter_record_count < 0:
            _fail("legacy fallback record count must be nonnegative")
        if (
            not self.blockers
            or tuple(sorted(self.blockers)) != self.blockers
            or len(set(self.blockers)) != len(self.blockers)
            or tuple(sorted(self.evidence_role_dispositions))
            != self.evidence_role_dispositions
            or len({row.role for row in self.evidence_role_dispositions})
            != len(self.evidence_role_dispositions)
        ):
            _fail("readiness blockers or role dispositions are incomplete/noncanonical")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_direct_fallback_exact_infeasibility_readiness.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "outcome": self.outcome.value,
            "candidate_terminal_scope": "LOGICAL_OCCURRENCE",
            "candidate_terminal_class": TerminalClass.INFEASIBILITY_CERTIFICATE.value,
            "candidate_terminal_code": TerminalCode.FULL_GROUND_EXACT_INFEASIBLE.value,
            "all_path_accounting_profile_id": self.all_path_accounting_profile_id,
            "operation_boundary_manifest_id": self.operation_boundary_manifest_id,
            "operation_boundary_source_archive_id": self.operation_boundary_source_archive_id,
            "fallback_boundary_site_id": self.fallback_boundary_site_id,
            "terminal_boundary_site_id": self.terminal_boundary_site_id,
            "durable_proof_verification_id": self.durable_proof_verification_id,
            "durable_proof_outcome": self.durable_proof_outcome,
            "durable_proof_id": self.durable_proof_id,
            "exact_infeasibility_identity_id": self.exact_infeasibility_identity_id,
            "durable_proof_lane": "EVALUATION",
            "durable_proof_charged_as_operational_route_work": False,
            "fallback_result_id": self.fallback_result_id,
            "fallback_work_vector_id": self.fallback_work_vector_id,
            "fallback_query_id": self.fallback_query_id,
            "fallback_outcome": self.fallback_outcome,
            "fallback_v1_counter_record_count": self.fallback_v1_counter_record_count,
            "fallback_portability_blocker_id": self.fallback_portability_blocker_id,
            "required_k7_counter_record_count": EXPECTED_K7_COUNTER_RECORD_COUNT,
            "required_comparison_axis_count": EXPECTED_COMPARISON_AXIS_COUNT,
            "evidence_role_dispositions": [row.to_document() for row in self.evidence_role_dispositions],
            "blockers": [row.to_document() for row in self.blockers],
            "ground_solver_called_by_assessment": False,
            "operation_boundary_catalogue_executed": False,
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "terminal_artifact_issued": False,
            "logical_occurrence_closure_issued": False,
            "formal_terminal_authorized": False,
            "all_path_native_accounting_complete": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
            "sample_efficiency_gate_status": SAMPLE_EFFICIENCY_GATE_STATUS,
            "central_domain_registration_pending": False,
        }

    @property
    def readiness_id(self) -> str:
        return content_id(
            CONSTRUCTION_K7_DIRECT_FALLBACK_EXACT_INFEASIBILITY_READINESS_V1_DOMAIN,
            self._payload(),
        )

    @property
    def readiness_document_sha256(self) -> str:
        return _sha256(canonical_json_bytes(self._payload()))

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "readiness_id": self.readiness_id,
            "readiness_document_sha256": self.readiness_document_sha256,
        }


def _replay_fallback_execution(
    execution: GroundFallbackExecutionV1,
) -> tuple[GroundFallbackResultV1, WorkVectorV1]:
    if type(execution) is not GroundFallbackExecutionV1:
        _fail("fallback_execution must be the exact GroundFallbackExecutionV1 type")
    try:
        result = GroundFallbackResultV1.from_dict(execution.result.to_dict())
        registry = official_counter_registry_v1()
        work = WorkVectorV1.from_dict(execution.work_vector.to_dict(), registry)
    except (TypeError, ValueError) as error:
        raise ConstructionK7DirectFallbackExactInfeasibilityReadinessV1Error(
            f"legacy fallback execution does not replay: {error}"
        ) from error
    if result.work_vector_id != work.work_vector_id:
        _fail("fallback execution result/work-vector identity crossed")
    return result, work


def assess_construction_k7_direct_fallback_exact_infeasibility_readiness_v1(
    proof_bytes: bytes,
    *,
    fallback_execution: GroundFallbackExecutionV1 | None = None,
    current_identity: DurableExactInfeasibilityIdentityV1 | Mapping[str, Any] | None = None,
    source_archive: Mapping[str, bytes] | None = None,
) -> ConstructionK7DirectFallbackExactInfeasibilityReadinessV1:
    """Assess the real current authorities without executing either route."""

    profile = profile_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    exact_rule = profile.terminal_path_rule_by_code[
        TerminalCode.FULL_GROUND_EXACT_INFEASIBLE
    ]
    if exact_rule.terminal_class is not TerminalClass.INFEASIBILITY_CERTIFICATE:
        _fail("all-path profile no longer maps exact fallback to infeasibility")

    archive = (
        boundary_v1.load_official_operation_boundary_source_archive_v1()
        if source_archive is None
        else source_archive
    )
    boundary_replay = boundary_v1.replay_operation_boundary_source_archive_v1(
        archive, profile=profile
    )
    if boundary_replay.outcome is not boundary_v1.BoundaryReplayOutcomeV1.VERIFIED:
        _fail("operation-boundary source replay is blocked")
    manifest = boundary_replay.manifest
    assert manifest is not None and boundary_replay.source_archive_id is not None
    fallback_site = manifest.by_key["fallback.authorized-ground-search"]
    terminal_site = manifest.by_key[
        "verification.terminal-semantic-attestation-replay"
    ]

    verified: VerifiedDurableExactInfeasibilityHandleV1 = (
        verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
            proof_bytes, current_identity=current_identity
        )
    )
    blockers: list[DirectFallbackBlockerV1] = []
    if verified.result.outcome is DurableProofVerificationOutcomeV1.INVALID:
        blockers.append(
            DirectFallbackBlockerV1(
                DirectFallbackBlockerCodeV1.DURABLE_PROOF_INVALID,
                "EXACT_GROUND_INFEASIBILITY_PROOF",
                verified.result.reason_code,
            )
        )
    elif verified.result.outcome is DurableProofVerificationOutcomeV1.NO_MATCH:
        blockers.append(
            DirectFallbackBlockerV1(
                DirectFallbackBlockerCodeV1.DURABLE_PROOF_IDENTITY_MISMATCH,
                "EXACT_GROUND_INFEASIBILITY_PROOF",
                "proof is semantically valid but its complete identity differs from the current query/build/kernel/threshold",
            )
        )

    result: GroundFallbackResultV1 | None = None
    work: WorkVectorV1 | None = None
    portability_id: str | None = None
    if fallback_execution is None:
        blockers.append(
            DirectFallbackBlockerV1(
                DirectFallbackBlockerCodeV1.FALLBACK_EXECUTION_ABSENT,
                "GROUND_FALLBACK",
                "no already-produced direct-fallback execution was supplied",
            )
        )
        ground_state = EvidenceRoleStateV1.NOT_RETAINED
    else:
        result, work = _replay_fallback_execution(fallback_execution)
        if result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED:
            blockers.append(
                DirectFallbackBlockerV1(
                    DirectFallbackBlockerCodeV1.FALLBACK_CAP_EXHAUSTED_NONCERTIFICATE,
                    "GROUND_FALLBACK",
                    "CAP_EXHAUSTED is incomplete and can only close as a noncertificate",
                )
            )
            ground_state = EvidenceRoleStateV1.CAP_EXHAUSTED_NONCERTIFICATE
        elif result.outcome is not GroundFallbackOutcome.INFEASIBLE_CERTIFIED:
            blockers.append(
                DirectFallbackBlockerV1(
                    DirectFallbackBlockerCodeV1.FALLBACK_OUTCOME_NOT_INFEASIBLE,
                    "GROUND_FALLBACK",
                    "the retained fallback produced a feasible plan rather than an infeasibility result",
                )
            )
            ground_state = EvidenceRoleStateV1.WRONG_FALLBACK_OUTCOME
        else:
            ground_state = EvidenceRoleStateV1.LEGACY_RESULT_PRESENT_NOT_DURABLE
            portability = classify_legacy_ground_fallback_portability_v1(result)
            portability_id = portability.blocker_id
            blockers.append(
                DirectFallbackBlockerV1(
                    DirectFallbackBlockerCodeV1.FALLBACK_SEARCH_COMPLETENESS_NOT_DURABLE,
                    "GROUND_FALLBACK",
                    portability.blocker_code,
                )
            )
        proof_query_id = (
            None if verified.proof_identity is None else verified.proof_identity.query_id
        )
        if proof_query_id is None or result.query_id != proof_query_id:
            blockers.append(
                DirectFallbackBlockerV1(
                    DirectFallbackBlockerCodeV1.FALLBACK_QUERY_ID_NOT_IDENTICAL,
                    "GROUND_FALLBACK",
                    "fallback query identity does not equal the independently replayed durable-proof query identity",
                )
            )
        if len(work.records) != EXPECTED_K7_COUNTER_RECORD_COUNT:
            blockers.append(
                DirectFallbackBlockerV1(
                    DirectFallbackBlockerCodeV1.FALLBACK_V1_WORK_VECTOR_NOT_K7_202_COUNTER_RECORDS,
                    "COUNTER_RECORD_SET",
                    f"legacy fallback retained {len(work.records)} V1 rows, not the 202 production-native K7 CounterRecords",
                )
            )

    blockers.extend(
        (
            DirectFallbackBlockerV1(
                DirectFallbackBlockerCodeV1.ROUTE_DECISION_AND_UPPER_CHAIN_NOT_RETAINED,
                "ROUTE_DECISION/ROUTE_UPPER",
                "this successor has no identity-bound operational route decision and selected upper for the canonical infeasible occurrence",
            ),
            DirectFallbackBlockerV1(
                DirectFallbackBlockerCodeV1.FALLBACK_BOUNDARY_CATALOGUE_ONLY,
                "GROUND_FALLBACK",
                "the exact AST site catalogue records execution_performed=false and accounting_event_emitted=false",
            ),
            DirectFallbackBlockerV1(
                DirectFallbackBlockerCodeV1.COUNTER_RECORD_SET_AUTHORITY_MISSING,
                "COUNTER_RECORD_SET",
                "no direct-fallback owner/common/native-zero 202-row semantic evidence closure exists",
            ),
            DirectFallbackBlockerV1(
                DirectFallbackBlockerCodeV1.SHARED_RESOURCE_RECEIPT_SET_AUTHORITY_MISSING,
                "SHARED_RESOURCE_RECEIPT_SET",
                "the nine shared-resource paths have no direct-fallback receipts through terminal cutoff",
            ),
            DirectFallbackBlockerV1(
                DirectFallbackBlockerCodeV1.DIRECT_FALLBACK_FORMAL_MATERIALIZER_MISSING,
                "WORK_VECTOR/ACTUAL_PROJECTION/DERIVED_RECONCILIATION",
                "no direct-fallback 202 CounterRecord -> WorkVector -> eight-axis ComparisonVector materializer is connected",
            ),
            DirectFallbackBlockerV1(
                DirectFallbackBlockerCodeV1.DIRECT_FALLBACK_COMPLETE_BUNDLE_VERIFIER_MISSING,
                "ACTUAL_PROJECTION",
                "no independent verifier replays the complete direct-fallback operational bundle",
            ),
            DirectFallbackBlockerV1(
                DirectFallbackBlockerCodeV1.EXACT_INFEASIBILITY_TERMINAL_AUTHORITY_MISSING,
                "TERMINAL_CLASSIFICATION/OCCURRENCE_TERMINAL",
                "durable proof and legacy result are not joined to complete native work by a formal terminal authority",
            ),
            DirectFallbackBlockerV1(
                DirectFallbackBlockerCodeV1.LOGICAL_OCCURRENCE_CLOSURE_MISSING,
                "OCCURRENCE_TERMINAL",
                "no closure retains direct-fallback proof/search work in all campaign denominators",
            ),
        )
    )

    states = {
        role.role: EvidenceRoleDispositionV1(
            role.role,
            role.required_outcome,
            (
                ground_state
                if role.role == "GROUND_FALLBACK"
                else EvidenceRoleStateV1.NOT_RETAINED
                if role.role in {"ROUTE_DECISION", "ROUTE_UPPER"}
                else EvidenceRoleStateV1.ROUTE_SPECIFIC_AUTHORITY_MISSING
            ),
        )
        for role in exact_rule.required_evidence_roles
    }
    # The durable proof is useful evaluation evidence but is intentionally not
    # substituted for the profile's operational GROUND_FALLBACK role.
    states["EXACT_GROUND_INFEASIBILITY_PROOF"] = EvidenceRoleDispositionV1(
        "EXACT_GROUND_INFEASIBILITY_PROOF",
        "IDENTICAL_MATCH",
        (
            EvidenceRoleStateV1.EVALUATION_VERIFIED_IDENTITY_MATCH_NOT_OPERATIONAL
            if verified.result.outcome
            is DurableProofVerificationOutcomeV1.IDENTICAL_MATCH
            else EvidenceRoleStateV1.EVALUATION_INVALID_OR_IDENTITY_MISMATCH
        ),
    )

    proof_identity_id = (
        None
        if verified.proof_identity is None
        else verified.proof_identity.exact_infeasibility_identity_id
    )
    return ConstructionK7DirectFallbackExactInfeasibilityReadinessV1(
        _ISSUER,
        profile.profile_id,
        manifest.manifest_id,
        boundary_replay.source_archive_id,
        fallback_site.site_id,
        terminal_site.site_id,
        verified.result.verification_id,
        verified.result.outcome.value,
        verified.result.durable_proof_id,
        proof_identity_id,
        None if result is None else result.ground_fallback_result_id,
        None if work is None else work.work_vector_id,
        None if result is None else result.query_id,
        None if result is None else result.outcome.value,
        0 if work is None else len(work.records),
        portability_id,
        tuple(sorted(states.values())),
        tuple(sorted(set(blockers))),
    )


def verify_construction_k7_direct_fallback_exact_infeasibility_readiness_document_v1(
    document: Mapping[str, Any],
    proof_bytes: bytes,
    *,
    fallback_execution: GroundFallbackExecutionV1 | None = None,
    current_identity: DurableExactInfeasibilityIdentityV1 | Mapping[str, Any] | None = None,
    source_archive: Mapping[str, bytes] | None = None,
) -> ConstructionK7DirectFallbackExactInfeasibilityReadinessV1:
    """Recompute the blocker and reject any edited or overclaiming document."""

    replayed = assess_construction_k7_direct_fallback_exact_infeasibility_readiness_v1(
        proof_bytes,
        fallback_execution=fallback_execution,
        current_identity=current_identity,
        source_archive=source_archive,
    )
    if type(document) is not dict or canonical_json_bytes(document) != canonical_json_bytes(
        replayed.to_document()
    ):
        _fail("direct-fallback readiness document differs from independent replay")
    return replayed


__all__ = [
    "ConstructionK7DirectFallbackExactInfeasibilityReadinessV1",
    "ConstructionK7DirectFallbackExactInfeasibilityReadinessV1Error",
    "DirectFallbackBlockerCodeV1",
    "DirectFallbackBlockerV1",
    "DirectFallbackReadinessOutcomeV1",
    "EvidenceRoleDispositionV1",
    "EvidenceRoleStateV1",
    "assess_construction_k7_direct_fallback_exact_infeasibility_readiness_v1",
    "verify_construction_k7_direct_fallback_exact_infeasibility_readiness_document_v1",
]
