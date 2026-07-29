"""V0-075 complete-bundle endpoint derivation.

Endpoint status is recomputed from the exact fifteen-occurrence
reconciliation.  A scientific PASS requires, in every public context:

* all five occurrences are exact-valid total-lift plan certificates;
* SOURCE_CONSENSUS_PRIOR uses fewer online draws than NO_PRIOR; and
* SOURCE_CONSENSUS_PRIOR uses no more draws than MATCHED_DIRECT_GROUND.

A complete, integrity-valid contrary result is a scientific FAIL.  Protocol
or integrity failure invalidates the endpoint instead of being reported as a
scientific result.  The production bundle adapter remains ``NOT_READY``;
domain-separated construction fixtures test these mechanics only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_campaign_reconciliation_v1 as reconciliation
from acfqp import v075_public_campaign_authority_v1 as public


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_complete_bundle_endpoint_verifier_v1"

PRODUCTION_COMPLETE_BUNDLE_PROTOCOL_STATUS = "NOT_READY"
PRODUCTION_ENDPOINT_VERIFICATION_ALLOWED = False

OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
WORKLOAD_ECONOMICS_GATE_STATUS = "NOT_RUN"
COUNTER_COMPLETENESS_GATE_STATUS = "NOT_RUN"

DOMAIN_TAGS = {
    "fixture_bundle": (
        "acfqp:v075-construction-fixture-complete-bundle:v1"
    ),
    "fixture_context_endpoint": (
        "acfqp:v075-construction-fixture-context-endpoint:v1"
    ),
    "fixture_endpoint_verification": (
        "acfqp:v075-construction-fixture-endpoint-verification:v1"
    ),
    "production_readiness": (
        "acfqp:v075-production-complete-bundle-endpoint-readiness:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 endpoint content domains must be unique")


class V075CompleteBundleEndpointInvariantViolation(ValueError):
    """The complete bundle is foreign, partial, forged, or semantically stale."""


class V075CompleteBundleProtocolOrIntegrityFailure(RuntimeError):
    """A protocol/integrity event invalidated the scientific endpoint."""


class V075ProductionCompleteBundleEndpointNotReady(RuntimeError):
    """The exact production occurrence bundle type has not been integrated."""


class V075ScientificEndpointVerdictV1(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


def _fail(message: str) -> None:
    raise V075CompleteBundleEndpointInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075CompleteBundleEndpointInvariantViolation(str(error)) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075CompleteBundleEndpointInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


_BUNDLE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionCompleteBundleV1:
    _issuer: object
    reconciliation: (
        reconciliation.V075ConstructionCampaignReconciliationV1
    )
    reconciliation_verification: (
        reconciliation
        .V075ConstructionCampaignReconciliationVerificationV1
    )
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _BUNDLE_ISSUER
            or type(self.reconciliation)
            is not reconciliation.V075ConstructionCampaignReconciliationV1
            or type(self.reconciliation_verification)
            is not reconciliation
            .V075ConstructionCampaignReconciliationVerificationV1
            or self.reconciliation_verification.reconciliation_id
            != self.reconciliation.reconciliation_id
            or self.reconciliation_verification.plan_id
            != self.reconciliation.plan.plan_id
            or self.reconciliation_verification.denominator
            != reconciliation.LOGICAL_OCCURRENCE_DENOMINATOR
        ):
            _fail("construction complete bundle was not internally minted")
        object.__setattr__(
            self,
            "_bundle_id",
            _hash("fixture_bundle", self._payload()),
        )

    @property
    def bundle_id(self) -> str:
        return self._bundle_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_construction_complete_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "reconciliation_id": self.reconciliation.reconciliation_id,
            "reconciliation_verification_id": (
                self.reconciliation_verification.verification_id
            ),
            "plan_id": self.reconciliation.plan.plan_id,
            "logical_occurrence_denominator": (
                reconciliation.LOGICAL_OCCURRENCE_DENOMINATOR
            ),
            "all_occurrences_retained": True,
            "construction_fixture_only": True,
            "production_evidence": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "reconciliation": self.reconciliation.to_document(),
            "reconciliation_verification": (
                self.reconciliation_verification.to_document()
            ),
            "bundle_id": self.bundle_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def mint_v075_construction_complete_bundle_v1(
    claimed: reconciliation.V075ConstructionCampaignReconciliationV1,
) -> V075ConstructionCompleteBundleV1:
    if (
        type(claimed)
        is not reconciliation.V075ConstructionCampaignReconciliationV1
    ):
        _fail("bundle minting requires the exact reconciliation type")
    attestation = (
        reconciliation.verify_v075_construction_campaign_reconciliation_v1(
            claimed
        )
    )
    return V075ConstructionCompleteBundleV1(
        _BUNDLE_ISSUER,
        claimed,
        attestation,
    )


_CONTEXT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionContextEndpointV1:
    _issuer: object
    context_id: str
    context_ordinal: int
    occurrence_record_ids: tuple[str, ...]
    source_online_draws: int
    no_prior_online_draws: int
    matched_direct_online_draws: int
    exact_valid_plan_certificate_count: int
    source_strictly_better_than_no_prior: bool
    source_noninferior_to_matched_direct: bool
    _context_endpoint_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.context_id, "context endpoint context")
        for value in self.occurrence_record_ids:
            _cid(value, "context endpoint occurrence")
        expected_strict = self.source_online_draws < self.no_prior_online_draws
        expected_direct = (
            self.source_online_draws <= self.matched_direct_online_draws
        )
        if (
            self._issuer is not _CONTEXT_ISSUER
            or type(self.context_ordinal) is not int
            or self.context_ordinal not in range(reconciliation.CONTEXT_COUNT)
            or type(self.occurrence_record_ids) is not tuple
            or len(self.occurrence_record_ids) != reconciliation.ARM_COUNT
            or len(set(self.occurrence_record_ids))
            != reconciliation.ARM_COUNT
            or any(
                type(value) is not int or value <= 0
                for value in (
                    self.source_online_draws,
                    self.no_prior_online_draws,
                    self.matched_direct_online_draws,
                )
            )
            or type(self.exact_valid_plan_certificate_count) is not int
            or self.exact_valid_plan_certificate_count
            not in range(reconciliation.ARM_COUNT + 1)
            or type(self.source_strictly_better_than_no_prior) is not bool
            or type(self.source_noninferior_to_matched_direct) is not bool
            or self.source_strictly_better_than_no_prior != expected_strict
            or self.source_noninferior_to_matched_direct != expected_direct
        ):
            _fail("context endpoint was not exactly derived")
        object.__setattr__(
            self,
            "_context_endpoint_id",
            _hash("fixture_context_endpoint", self._payload()),
        )

    @property
    def context_endpoint_id(self) -> str:
        return self._context_endpoint_id

    @property
    def context_pass(self) -> bool:
        return (
            self.exact_valid_plan_certificate_count
            == reconciliation.ARM_COUNT
            and self.source_strictly_better_than_no_prior
            and self.source_noninferior_to_matched_direct
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_construction_context_endpoint.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "context_ordinal": self.context_ordinal,
            "occurrence_record_ids": list(self.occurrence_record_ids),
            "source_online_draws": self.source_online_draws,
            "no_prior_online_draws": self.no_prior_online_draws,
            "matched_direct_online_draws": self.matched_direct_online_draws,
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
            "construction_fixture_only": True,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "context_endpoint_id": self.context_endpoint_id,
        }


_ENDPOINT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionCompleteBundleEndpointVerificationV1:
    _issuer: object
    bundle_id: str
    reconciliation_id: str
    context_endpoints: tuple[V075ConstructionContextEndpointV1, ...]
    plan_certificate_count: int
    infeasibility_certificate_count: int
    noncertificate_count: int
    verdict: V075ScientificEndpointVerdictV1
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.bundle_id, "endpoint bundle")
        _cid(self.reconciliation_id, "endpoint reconciliation")
        expected_verdict = (
            V075ScientificEndpointVerdictV1.PASS
            if (
                self.plan_certificate_count
                == reconciliation.LOGICAL_OCCURRENCE_DENOMINATOR
                and self.infeasibility_certificate_count == 0
                and self.noncertificate_count == 0
                and all(item.context_pass for item in self.context_endpoints)
            )
            else V075ScientificEndpointVerdictV1.FAIL
        )
        if (
            self._issuer is not _ENDPOINT_ISSUER
            or type(self.context_endpoints) is not tuple
            or len(self.context_endpoints) != reconciliation.CONTEXT_COUNT
            or any(
                type(item) is not V075ConstructionContextEndpointV1
                for item in self.context_endpoints
            )
            or tuple(item.context_ordinal for item in self.context_endpoints)
            != tuple(range(reconciliation.CONTEXT_COUNT))
            or any(
                type(value) is not int or value < 0
                for value in (
                    self.plan_certificate_count,
                    self.infeasibility_certificate_count,
                    self.noncertificate_count,
                )
            )
            or (
                self.plan_certificate_count
                + self.infeasibility_certificate_count
                + self.noncertificate_count
                != reconciliation.LOGICAL_OCCURRENCE_DENOMINATOR
            )
            or type(self.verdict) is not V075ScientificEndpointVerdictV1
            or self.verdict is not expected_verdict
        ):
            _fail("endpoint verdict/counts were not independently derived")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("fixture_endpoint_verification", self._payload()),
        )

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_complete_bundle_endpoint_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "bundle_id": self.bundle_id,
            "reconciliation_id": self.reconciliation_id,
            "context_endpoint_ids": [
                item.context_endpoint_id for item in self.context_endpoints
            ],
            "plan_certificate_count": self.plan_certificate_count,
            "infeasibility_certificate_count": (
                self.infeasibility_certificate_count
            ),
            "noncertificate_count": self.noncertificate_count,
            "logical_occurrence_denominator": (
                reconciliation.LOGICAL_OCCURRENCE_DENOMINATOR
            ),
            "verdict": self.verdict.value,
            "scientific_pass_rule": (
                "ALL_15_EXACT_VALID_PLAN_CERTIFICATES_AND_"
                "PER_CONTEXT_SOURCE_LT_NO_PRIOR_AND_SOURCE_LE_MATCHED_DIRECT"
            ),
            "caller_status_accepted": False,
            "caller_validity_accepted": False,
            "caller_expected_identity_accepted": False,
            "official_execution_allowed": OFFICIAL_EXECUTION_ALLOWED,
            "official_scalar_cost": OFFICIAL_SCALAR_COST,
            "official_N_break_even": OFFICIAL_N_BREAK_EVEN,
            "workload_economics_gate_status": (
                WORKLOAD_ECONOMICS_GATE_STATUS
            ),
            "counter_completeness_gate_status": (
                COUNTER_COMPLETENESS_GATE_STATUS
            ),
            "construction_fixture_only": True,
            "production_evidence": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "context_endpoints": [
                item.to_document() for item in self.context_endpoints
            ],
            "verification_id": self.verification_id,
        }


def _derive_context_endpoint_v1(
    *,
    context: public.V075PublicReplicateContextV1,
    occurrences: tuple[
        reconciliation.V075ConstructionReconciledOccurrenceV1, ...
    ],
) -> V075ConstructionContextEndpointV1:
    expected = tuple(
        item
        for item in occurrences
        if item.plan_entry.context_ordinal == context.replicate_ordinal
    )
    if (
        len(expected) != reconciliation.ARM_COUNT
        or tuple(item.plan_entry.arm for item in expected)
        != reconciliation.ARM_ORDER
        or any(item.plan_entry.context.context_id != context.context_id for item in expected)
    ):
        _fail("context endpoint input is incomplete or not context-major")
    by_arm = {item.plan_entry.arm: item for item in expected}
    exact_count = sum(
        item.verification.exact_valid_total_lift_plan
        and item.verification.terminal_class
        is reconciliation.V075OccurrenceTerminalClassV1.PLAN_CERTIFICATE
        and item.verification.terminal_code
        is reconciliation.V075OccurrenceTerminalCodeV1
        .EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE
        for item in expected
    )
    source = by_arm["SOURCE_CONSENSUS_PRIOR"].evidence.online_draw_count
    no_prior = by_arm["NO_PRIOR"].evidence.online_draw_count
    direct = by_arm["MATCHED_DIRECT_GROUND"].evidence.online_draw_count
    return V075ConstructionContextEndpointV1(
        _CONTEXT_ISSUER,
        context.context_id,
        context.replicate_ordinal,
        tuple(item.record_id for item in expected),
        source,
        no_prior,
        direct,
        exact_count,
        source < no_prior,
        source <= direct,
    )


def verify_v075_construction_complete_bundle_endpoint_v1(
    bundle: V075ConstructionCompleteBundleV1,
) -> V075ConstructionCompleteBundleEndpointVerificationV1:
    """Replay the bundle and derive PASS/FAIL without caller assertions."""

    if type(bundle) is not V075ConstructionCompleteBundleV1:
        _fail("endpoint verifier requires the exact internally minted bundle")
    replayed_attestation = (
        reconciliation.verify_v075_construction_campaign_reconciliation_v1(
            bundle.reconciliation
        )
    )
    if replayed_attestation != bundle.reconciliation_verification:
        _fail("complete bundle reconciliation attestation is stale")
    reminted = V075ConstructionCompleteBundleV1(
        _BUNDLE_ISSUER,
        bundle.reconciliation,
        replayed_attestation,
    )
    if (
        reminted.bundle_id != bundle.bundle_id
        or reminted.canonical_bytes != bundle.canonical_bytes
    ):
        _fail("complete bundle differs from exact replay")

    claimed = bundle.reconciliation
    expected_plan = reconciliation.freeze_v075_scientific_occurrence_plan_v1(
        public.V075PublicFamilyGenerationV1()
    )
    if (
        claimed.plan.plan_id != expected_plan.plan_id
        or claimed.plan.to_document() != expected_plan.to_document()
    ):
        _fail("complete bundle uses a foreign scientific plan")

    invalid_codes = {
        reconciliation.V075OccurrenceTerminalCodeV1.PROTOCOL_FAILURE,
        reconciliation.V075OccurrenceTerminalCodeV1.INTEGRITY_FAILURE,
    }
    if any(
        item.verification.terminal_code in invalid_codes
        for item in claimed.occurrences
    ):
        raise V075CompleteBundleProtocolOrIntegrityFailure(
            "protocol/integrity failure invalidates the V0-075 endpoint"
        )

    contexts = tuple(
        _derive_context_endpoint_v1(
            context=context,
            occurrences=claimed.occurrences,
        )
        for context in claimed.plan.family_generation.replicate_contexts
    )
    verdict = (
        V075ScientificEndpointVerdictV1.PASS
        if (
            claimed.plan_certificate_count
            == reconciliation.LOGICAL_OCCURRENCE_DENOMINATOR
            and claimed.infeasibility_certificate_count == 0
            and claimed.noncertificate_count == 0
            and all(item.context_pass for item in contexts)
        )
        else V075ScientificEndpointVerdictV1.FAIL
    )
    return V075ConstructionCompleteBundleEndpointVerificationV1(
        _ENDPOINT_ISSUER,
        bundle.bundle_id,
        claimed.reconciliation_id,
        contexts,
        claimed.plan_certificate_count,
        claimed.infeasibility_certificate_count,
        claimed.noncertificate_count,
        verdict,
    )


@dataclass(frozen=True, slots=True)
class V075ProductionCompleteBundleEndpointReadinessV1:
    _issuer: object
    _status_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self._issuer is not _BUNDLE_ISSUER:
            _fail("production endpoint readiness was caller-minted")
        object.__setattr__(
            self,
            "_status_id",
            _hash("production_readiness", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_complete_bundle_endpoint_readiness.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "production_complete_bundle_protocol_status": (
                PRODUCTION_COMPLETE_BUNDLE_PROTOCOL_STATUS
            ),
            "production_endpoint_verification_allowed": False,
            "construction_fixture_accepted_as_production": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "workload_economics_gate_status": "NOT_RUN",
            "counter_completeness_gate_status": "NOT_RUN",
        }

    @property
    def status_id(self) -> str:
        return self._status_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "status_id": self.status_id}


def v075_production_complete_bundle_endpoint_readiness_v1(
) -> V075ProductionCompleteBundleEndpointReadinessV1:
    return V075ProductionCompleteBundleEndpointReadinessV1(_BUNDLE_ISSUER)


def verify_v075_complete_bundle_endpoint_v1() -> None:
    """Fail closed until exact production bundle authorities are available."""

    raise V075ProductionCompleteBundleEndpointNotReady(
        "V0-075 production complete-bundle protocol is NOT_READY; "
        "construction fixtures are not production evidence"
    )


__all__ = [
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "PRODUCTION_COMPLETE_BUNDLE_PROTOCOL_STATUS",
    "V075CompleteBundleEndpointInvariantViolation",
    "V075CompleteBundleProtocolOrIntegrityFailure",
    "V075ConstructionCompleteBundleEndpointVerificationV1",
    "V075ConstructionCompleteBundleV1",
    "V075ProductionCompleteBundleEndpointNotReady",
    "V075ScientificEndpointVerdictV1",
    "mint_v075_construction_complete_bundle_v1",
    "v075_production_complete_bundle_endpoint_readiness_v1",
    "verify_v075_complete_bundle_endpoint_v1",
    "verify_v075_construction_complete_bundle_endpoint_v1",
]
