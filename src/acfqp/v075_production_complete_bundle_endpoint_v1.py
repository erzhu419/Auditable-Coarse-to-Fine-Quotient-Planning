"""Production complete-bundle scientific endpoint for V0-075.

This endpoint consumes one exact production campaign reconciliation and
independently replays that reconciliation before deriving any scientific
claim.  A PASS requires all fifteen retained occurrences to be exact-valid
plan certificates and, separately in each registered context, requires
SOURCE online accepted draws to be lower than NO_PRIOR and no greater than
MATCHED_DIRECT_GROUND.

A complete, semantically valid contrary campaign is a scientific FAIL.
Protocol or integrity failure invalidates the endpoint and cannot be
relabelled as a scientific result.  The endpoint neither opens the target nor
accepts private target material, caller totals, caller verdicts, scalar costs,
or break-even claims.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_production_campaign_reconciliation_v1 as reconciliation
from acfqp import v075_production_occurrence_authority_v1 as occurrence
from acfqp import v075_production_occurrence_plan_v1 as occurrence_plan
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.42.0"
PROFILE_KEY = "v075_production_complete_bundle_endpoint_v1"

PRODUCTION_COMPLETE_BUNDLE_PROTOCOL_STATUS = "READY"
PRODUCTION_ENDPOINT_VERIFICATION_ALLOWED = True
TARGET_EXECUTION_OPENED = False
PRIVATE_TARGET_INPUTS_ACCEPTED = False
CALLER_VERDICTS_ACCEPTED = False
CALLER_TOTALS_ACCEPTED = False

OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
WORKLOAD_ECONOMICS_GATE_STATUS = "NOT_RUN"
COUNTER_COMPLETENESS_GATE_STATUS = "NOT_RUN"

DOMAIN_TAGS = {
    "occurrence_evidence": (
        "acfqp:v075-production-endpoint-occurrence-evidence:v1"
    ),
    "context_evidence": (
        "acfqp:v075-production-endpoint-context-evidence:v1"
    ),
    "endpoint_verification": (
        "acfqp:v075-production-complete-bundle-endpoint-verification:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 production endpoint domains overlap")


class V075ProductionCompleteBundleEndpointInvariantViolation(ValueError):
    """The reconciliation or derived endpoint evidence was not exact."""


class V075ProductionCompleteBundleProtocolOrIntegrityFailure(RuntimeError):
    """Protocol/integrity failure invalidated the scientific endpoint."""

    def __init__(self, invalidating_occurrence_ids: tuple[str, ...]) -> None:
        self.invalidating_occurrence_ids = invalidating_occurrence_ids
        super().__init__(
            "protocol or integrity failure invalidated the production "
            "complete-bundle endpoint"
        )


class V075ProductionScientificEndpointVerdictV1(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


def _fail(message: str) -> None:
    raise V075ProductionCompleteBundleEndpointInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075ProductionCompleteBundleEndpointInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ProductionCompleteBundleEndpointInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


_OCCURRENCE_EVIDENCE_ISSUER = object()
_CONTEXT_EVIDENCE_ISSUER = object()
_ENDPOINT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ProductionEndpointOccurrenceEvidenceV1:
    """One endpoint-visible occurrence with exact terminal and native draws."""

    _issuer: object = field(repr=False, compare=False)
    reconciled_occurrence: (
        reconciliation.V075ProductionReconciledOccurrenceV1
    ) = field(repr=False)
    _evidence_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        item = self.reconciled_occurrence
        if (
            self._issuer is not _OCCURRENCE_EVIDENCE_ISSUER
            or type(item)
            is not reconciliation.V075ProductionReconciledOccurrenceV1
            or item.entry.arm is not item.result.plan_entry.arm
            or item.verification.result_id != item.result.result_id
            or item.verification.occurrence_id != item.entry.occurrence_id
            or item.verification.plan_entry_id != item.entry.entry_id
            or item.verification.terminal_class
            is not item.result.terminal_class
            or item.verification.terminal_code is not item.result.terminal_code
            or type(item.verification.accepted_draw_count) is not int
            or item.verification.accepted_draw_count < 0
        ):
            _fail("endpoint occurrence evidence is foreign or inconsistent")
        object.__setattr__(
            self,
            "_evidence_id",
            _hash("occurrence_evidence", self._payload()),
        )

    @property
    def evidence_id(self) -> str:
        return self._evidence_id

    @property
    def entry(self) -> occurrence_plan.V075ProductionOccurrencePlanEntryV1:
        return self.reconciled_occurrence.entry

    @property
    def arm(self) -> worker.V075WorkerArmV1:
        return self.entry.arm

    @property
    def terminal_class(
        self,
    ) -> occurrence.V075ProductionOccurrenceTerminalClassV1:
        return self.reconciled_occurrence.verification.terminal_class

    @property
    def terminal_code(
        self,
    ) -> occurrence.V075ProductionOccurrenceTerminalCodeV1:
        return self.reconciled_occurrence.verification.terminal_code

    @property
    def accepted_draw_count(self) -> int:
        return self.reconciled_occurrence.verification.accepted_draw_count

    @property
    def exact_valid_plan_certificate(self) -> bool:
        return (
            self.terminal_class
            is occurrence.V075ProductionOccurrenceTerminalClassV1
            .PLAN_CERTIFICATE
            and self.terminal_code
            is occurrence.V075ProductionOccurrenceTerminalCodeV1
            .EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE
        )

    def _payload(self) -> dict[str, Any]:
        item = self.reconciled_occurrence
        return {
            "schema": (
                "acfqp.v075_production_endpoint_occurrence_evidence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_record_id": item.record_id,
            "result_id": item.verification.result_id,
            "verification_id": item.verification.verification_id,
            "occurrence_id": item.verification.occurrence_id,
            "plan_entry_id": item.entry.entry_id,
            "context_id": item.entry.context_id,
            "context_ordinal": item.entry.context_ordinal,
            "arm": item.entry.arm.value,
            "arm_ordinal": item.entry.arm_ordinal,
            "scientific_ordinal": item.entry.scientific_ordinal,
            "transport_ordinal": item.entry.transport_ordinal,
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "accepted_draw_count": self.accepted_draw_count,
            "exact_valid_plan_certificate": (
                self.exact_valid_plan_certificate
            ),
            "retained": True,
            "production_evidence": True,
            "caller_terminal_accepted": False,
            "caller_draw_total_accepted": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "reconciled_occurrence": (
                self.reconciled_occurrence.to_document()
            ),
            "evidence_id": self.evidence_id,
        }


@dataclass(frozen=True, slots=True)
class V075ProductionContextEndpointEvidenceV1:
    """All five immutable arms and exact draw comparisons for one context."""

    _issuer: object = field(repr=False, compare=False)
    context_id: str
    context_ordinal: int
    occurrences: tuple[V075ProductionEndpointOccurrenceEvidenceV1, ...]
    _context_evidence_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.context_id, "endpoint context")
        if (
            self._issuer is not _CONTEXT_EVIDENCE_ISSUER
            or type(self.context_ordinal) is not int
            or self.context_ordinal
            not in range(occurrence_plan.EXPECTED_CONTEXT_COUNT)
            or type(self.occurrences) is not tuple
            or len(self.occurrences)
            != occurrence_plan.EXPECTED_ARM_COUNT
            or any(
                type(item)
                is not V075ProductionEndpointOccurrenceEvidenceV1
                for item in self.occurrences
            )
            or tuple(item.arm for item in self.occurrences)
            != occurrence_plan.REGISTERED_ARM_ORDER
            or any(
                item.entry.context_id != self.context_id
                or item.entry.context_ordinal != self.context_ordinal
                for item in self.occurrences
            )
            or tuple(
                item.entry.arm_ordinal for item in self.occurrences
            )
            != tuple(range(occurrence_plan.EXPECTED_ARM_COUNT))
            or len({item.evidence_id for item in self.occurrences})
            != occurrence_plan.EXPECTED_ARM_COUNT
        ):
            _fail("context endpoint evidence is incomplete or reordered")
        object.__setattr__(
            self,
            "_context_evidence_id",
            _hash("context_evidence", self._payload()),
        )

    @property
    def context_evidence_id(self) -> str:
        return self._context_evidence_id

    def _arm_evidence(
        self,
        arm: worker.V075WorkerArmV1,
    ) -> V075ProductionEndpointOccurrenceEvidenceV1:
        matches = tuple(item for item in self.occurrences if item.arm is arm)
        if len(matches) != 1:  # pragma: no cover - constructor proves this
            _fail("context lacks one exact arm")
        return matches[0]

    @property
    def source_online_accepted_draws(self) -> int:
        return self._arm_evidence(
            worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
        ).accepted_draw_count

    @property
    def no_prior_online_accepted_draws(self) -> int:
        return self._arm_evidence(
            worker.V075WorkerArmV1.NO_PRIOR
        ).accepted_draw_count

    @property
    def matched_direct_online_accepted_draws(self) -> int:
        return self._arm_evidence(
            worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
        ).accepted_draw_count

    @property
    def exact_valid_plan_certificate_count(self) -> int:
        return sum(
            item.exact_valid_plan_certificate for item in self.occurrences
        )

    @property
    def source_strictly_better_than_no_prior(self) -> bool:
        return (
            self.source_online_accepted_draws
            < self.no_prior_online_accepted_draws
        )

    @property
    def source_noninferior_to_matched_direct(self) -> bool:
        return (
            self.source_online_accepted_draws
            <= self.matched_direct_online_accepted_draws
        )

    @property
    def context_pass(self) -> bool:
        return (
            self.exact_valid_plan_certificate_count
            == occurrence_plan.EXPECTED_ARM_COUNT
            and self.source_strictly_better_than_no_prior
            and self.source_noninferior_to_matched_direct
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_context_endpoint_evidence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "context_ordinal": self.context_ordinal,
            "occurrence_evidence_ids": [
                item.evidence_id for item in self.occurrences
            ],
            "occurrence_record_ids": [
                item.reconciled_occurrence.record_id
                for item in self.occurrences
            ],
            "arm_order": [item.arm.value for item in self.occurrences],
            "online_accepted_draws_by_arm": {
                item.arm.value: item.accepted_draw_count
                for item in self.occurrences
            },
            "source_online_accepted_draws": (
                self.source_online_accepted_draws
            ),
            "no_prior_online_accepted_draws": (
                self.no_prior_online_accepted_draws
            ),
            "matched_direct_online_accepted_draws": (
                self.matched_direct_online_accepted_draws
            ),
            "exact_valid_plan_certificate_count": (
                self.exact_valid_plan_certificate_count
            ),
            "source_strictly_better_than_no_prior": (
                self.source_strictly_better_than_no_prior
            ),
            "source_noninferior_to_matched_direct": (
                self.source_noninferior_to_matched_direct
            ),
            "context_pass": self.context_pass,
            "all_five_occurrences_retained": True,
            "production_evidence": True,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrences": [
                item.to_document() for item in self.occurrences
            ],
            "context_evidence_id": self.context_evidence_id,
        }


@dataclass(frozen=True, slots=True)
class V075ProductionCompleteBundleEndpointVerificationV1:
    """Replay-derived scientific endpoint over one complete production bundle."""

    _issuer: object = field(repr=False, compare=False)
    reconciliation: reconciliation.V075ProductionCampaignReconciliationV1 = (
        field(repr=False)
    )
    reconciliation_verification: (
        reconciliation.V075ProductionCampaignReconciliationVerificationV1
    )
    context_evidence: tuple[V075ProductionContextEndpointEvidenceV1, ...]
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        expected_record_ids = tuple(
            item.record_id for item in self.reconciliation.occurrences
        )
        expected_context_ids = tuple(self.reconciliation.plan.context_ids)
        if (
            self._issuer is not _ENDPOINT_ISSUER
            or type(self.reconciliation)
            is not reconciliation.V075ProductionCampaignReconciliationV1
            or type(self.reconciliation_verification)
            is not reconciliation
            .V075ProductionCampaignReconciliationVerificationV1
            or self.reconciliation_verification.reconciliation_id
            != self.reconciliation.reconciliation_id
            or self.reconciliation_verification.replayed_reconciliation_id
            != self.reconciliation.reconciliation_id
            or self.reconciliation_verification.plan_id
            != self.reconciliation.plan.plan_id
            or self.reconciliation_verification.plan_verification_id
            != self.reconciliation.plan_verification.verification_id
            or self.reconciliation_verification
            .source_offline_accounting_id
            != self.reconciliation.source_offline_accounting.accounting_id
            or self.reconciliation_verification.occurrence_record_ids
            != expected_record_ids
            or self.reconciliation_verification.denominator
            != occurrence_plan.EXPECTED_OCCURRENCE_COUNT
            or self.reconciliation_verification.plan_certificate_count
            != self.reconciliation.plan_certificate_count
            or self.reconciliation_verification
            .infeasibility_certificate_count
            != self.reconciliation.infeasibility_certificate_count
            or self.reconciliation_verification.noncertificate_count
            != self.reconciliation.noncertificate_count
            or self.reconciliation_verification.campaign_validity
            is not reconciliation.V075ProductionCampaignValidityV1.VALID
            or type(self.context_evidence) is not tuple
            or len(self.context_evidence)
            != occurrence_plan.EXPECTED_CONTEXT_COUNT
            or any(
                type(item)
                is not V075ProductionContextEndpointEvidenceV1
                for item in self.context_evidence
            )
            or tuple(
                item.context_ordinal for item in self.context_evidence
            )
            != tuple(range(occurrence_plan.EXPECTED_CONTEXT_COUNT))
            or tuple(item.context_id for item in self.context_evidence)
            != expected_context_ids
            or tuple(
                evidence.reconciled_occurrence.record_id
                for context in self.context_evidence
                for evidence in context.occurrences
            )
            != expected_record_ids
        ):
            _fail("production endpoint is partial, reordered, or transplanted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("endpoint_verification", self._payload()),
        )

    @property
    def verification_id(self) -> str:
        return self._verification_id

    @property
    def plan_certificate_count(self) -> int:
        return self.reconciliation_verification.plan_certificate_count

    @property
    def infeasibility_certificate_count(self) -> int:
        return self.reconciliation_verification.infeasibility_certificate_count

    @property
    def noncertificate_count(self) -> int:
        return self.reconciliation_verification.noncertificate_count

    @property
    def verdict(self) -> V075ProductionScientificEndpointVerdictV1:
        if (
            self.plan_certificate_count
            == occurrence_plan.EXPECTED_OCCURRENCE_COUNT
            and self.infeasibility_certificate_count == 0
            and self.noncertificate_count == 0
            and all(item.context_pass for item in self.context_evidence)
        ):
            return V075ProductionScientificEndpointVerdictV1.PASS
        return V075ProductionScientificEndpointVerdictV1.FAIL

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_complete_bundle_endpoint_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "reconciliation_id": self.reconciliation.reconciliation_id,
            "reconciliation_verification_id": (
                self.reconciliation_verification.verification_id
            ),
            "plan_id": self.reconciliation.plan.plan_id,
            "plan_verification_id": (
                self.reconciliation.plan_verification.verification_id
            ),
            "remote_main_anchor_id": (
                self.reconciliation.plan.remote_main_anchor_id
            ),
            "final_preregistration_id": (
                self.reconciliation.plan.final_preregistration_id
            ),
            "target_tape_namespace_id": (
                self.reconciliation.plan.target_tape_namespace_id
            ),
            "public_family_generation_id": (
                self.reconciliation.plan.public_family_generation_id
            ),
            "context_evidence_ids": [
                item.context_evidence_id for item in self.context_evidence
            ],
            "logical_occurrence_denominator": (
                occurrence_plan.EXPECTED_OCCURRENCE_COUNT
            ),
            "plan_certificate_count": self.plan_certificate_count,
            "infeasibility_certificate_count": (
                self.infeasibility_certificate_count
            ),
            "noncertificate_count": self.noncertificate_count,
            "campaign_validity": (
                self.reconciliation_verification.campaign_validity.value
            ),
            "invalidating_occurrence_ids": [],
            "scientific_verdict": self.verdict.value,
            "pass_requires_all_exact_valid_plan_certificates": True,
            "pass_requires_contextwise_source_strictly_better_than_no_prior": (
                True
            ),
            "pass_requires_contextwise_source_noninferior_to_matched_direct": (
                True
            ),
            "complete_valid_contrary_result_is_scientific_fail": True,
            "protocol_or_integrity_is_not_scientific_fail": True,
            "all_occurrences_retained": True,
            "independent_reconciliation_replay": True,
            "caller_verdict_accepted": False,
            "caller_totals_accepted": False,
            "target_execution_opened_by_endpoint": False,
            "private_target_inputs_accepted": False,
            "official_execution_allowed": OFFICIAL_EXECUTION_ALLOWED,
            "official_scalar_cost": OFFICIAL_SCALAR_COST,
            "official_N_break_even": OFFICIAL_N_BREAK_EVEN,
            "workload_economics_gate_status": (
                WORKLOAD_ECONOMICS_GATE_STATUS
            ),
            "counter_completeness_gate_status": (
                COUNTER_COMPLETENESS_GATE_STATUS
            ),
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "reconciliation": self.reconciliation.to_document(),
            "reconciliation_verification": (
                self.reconciliation_verification.to_document()
            ),
            "context_evidence": [
                item.to_document() for item in self.context_evidence
            ],
            "verification_id": self.verification_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def verify_v075_production_complete_bundle_endpoint_v1(
    *,
    repository_root: str | Path,
    namespace: public.V075PublicTargetTapeNamespaceV1,
    claimed: reconciliation.V075ProductionCampaignReconciliationV1,
) -> V075ProductionCompleteBundleEndpointVerificationV1:
    """Independently replay one exact reconciliation and derive its endpoint."""

    if (
        type(namespace) is not public.V075PublicTargetTapeNamespaceV1
        or type(claimed)
        is not reconciliation.V075ProductionCampaignReconciliationV1
    ):
        _fail(
            "production endpoint requires one exact public namespace and "
            "one exact production reconciliation"
        )
    try:
        verified = (
            reconciliation
            .verify_v075_production_campaign_reconciliation_v1(
                repository_root=repository_root,
                namespace=namespace,
                claimed=claimed,
            )
        )
    except Exception as error:
        if isinstance(
            error,
            V075ProductionCompleteBundleEndpointInvariantViolation,
        ):
            raise
        raise V075ProductionCompleteBundleEndpointInvariantViolation(
            f"production reconciliation replay failed: {error}"
        ) from error
    if (
        type(verified)
        is not reconciliation
        .V075ProductionCampaignReconciliationVerificationV1
        or verified.reconciliation_id != claimed.reconciliation_id
        or verified.replayed_reconciliation_id != claimed.reconciliation_id
        or verified.occurrence_record_ids
        != tuple(item.record_id for item in claimed.occurrences)
        or verified.denominator
        != occurrence_plan.EXPECTED_OCCURRENCE_COUNT
        or verified.plan_certificate_count != claimed.plan_certificate_count
        or verified.infeasibility_certificate_count
        != claimed.infeasibility_certificate_count
        or verified.noncertificate_count != claimed.noncertificate_count
    ):
        _fail("reconciliation verifier returned partial or foreign evidence")

    invalidating = claimed.invalidating_occurrence_ids
    if (
        verified.campaign_validity
        is not reconciliation.V075ProductionCampaignValidityV1.VALID
        or invalidating
    ):
        raise V075ProductionCompleteBundleProtocolOrIntegrityFailure(
            invalidating
        )

    occurrence_evidence = tuple(
        V075ProductionEndpointOccurrenceEvidenceV1(
            _OCCURRENCE_EVIDENCE_ISSUER,
            item,
        )
        for item in claimed.occurrences
    )
    contexts = tuple(
        V075ProductionContextEndpointEvidenceV1(
            _CONTEXT_EVIDENCE_ISSUER,
            claimed.plan.context_ids[context_ordinal],
            context_ordinal,
            tuple(
                item
                for item in occurrence_evidence
                if item.entry.context_ordinal == context_ordinal
            ),
        )
        for context_ordinal in range(
            occurrence_plan.EXPECTED_CONTEXT_COUNT
        )
    )
    return V075ProductionCompleteBundleEndpointVerificationV1(
        _ENDPOINT_ISSUER,
        claimed,
        verified,
        contexts,
    )


__all__ = [
    "CALLER_TOTALS_ACCEPTED",
    "CALLER_VERDICTS_ACCEPTED",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "DOMAIN_TAGS",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "PRIVATE_TARGET_INPUTS_ACCEPTED",
    "PRODUCTION_COMPLETE_BUNDLE_PROTOCOL_STATUS",
    "PRODUCTION_ENDPOINT_VERIFICATION_ALLOWED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "TARGET_EXECUTION_OPENED",
    "V075ProductionCompleteBundleEndpointInvariantViolation",
    "V075ProductionCompleteBundleEndpointVerificationV1",
    "V075ProductionCompleteBundleProtocolOrIntegrityFailure",
    "V075ProductionContextEndpointEvidenceV1",
    "V075ProductionEndpointOccurrenceEvidenceV1",
    "V075ProductionScientificEndpointVerdictV1",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "verify_v075_production_complete_bundle_endpoint_v1",
]
