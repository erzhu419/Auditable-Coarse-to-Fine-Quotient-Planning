"""V0-075 context-major campaign reconciliation foundation.

The scientific schedule is immutable: three public contexts crossed with the
five registered arms, in context-major order.  Scientific ordinal ``i`` maps
to transport ordinal ``i + 1``.  Reconciliation derives every count and
classification from issuer-produced semantic verifications; it accepts no
caller summary, status, validity bit, denominator, or expected identity.

The production occurrence/total-lift adapter does not exist yet.  Production
entry points therefore remain explicitly ``NOT_READY``.  A domain-separated
construction-fixture path exercises the complete reconciliation mechanics
without creating production evidence or opening the held-out observer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_public_source_work_authority_v1 as public_source_work


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_campaign_reconciliation_v1"

ARM_ORDER = public.ARM_ORDER
CONTEXT_COUNT = 3
ARM_COUNT = 5
LOGICAL_OCCURRENCE_DENOMINATOR = 15
SCIENTIFIC_ORDINALS = tuple(range(LOGICAL_OCCURRENCE_DENOMINATOR))
TRANSPORT_ORDINALS = tuple(range(1, LOGICAL_OCCURRENCE_DENOMINATOR + 1))
ORDINAL_MAPPING = "SCIENTIFIC_ZERO_TO_TRANSPORT_ONE_PLUS_ONE_V1"

PRODUCTION_OCCURRENCE_RESULT_PROTOCOL_STATUS = "NOT_READY"
PRODUCTION_TOTAL_LIFT_ADAPTER_IMPLEMENTED = False
PRODUCTION_RECONCILIATION_ALLOWED = False

OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
WORKLOAD_ECONOMICS_GATE_STATUS = "NOT_RUN"
COUNTER_COMPLETENESS_GATE_STATUS = "NOT_RUN"

DOMAIN_TAGS = {
    "plan_entry": "acfqp:v075-scientific-occurrence-plan-entry:v1",
    "plan": "acfqp:v075-scientific-occurrence-plan:v1",
    "fixture_source_work": (
        "acfqp:v075-construction-fixture-source-offline-work:v1"
    ),
    "fixture_source_materialization": (
        "acfqp:v075-construction-fixture-source-materialization:v1"
    ),
    "fixture_source_verification": (
        "acfqp:v075-construction-fixture-source-verification:v1"
    ),
    "fixture_offline_work": (
        "acfqp:v075-construction-fixture-offline-work:v1"
    ),
    "fixture_observer_record": (
        "acfqp:v075-construction-fixture-observer-record:v1"
    ),
    "fixture_observer_journal": (
        "acfqp:v075-construction-fixture-observer-journal:v1"
    ),
    "fixture_transport_manifest": (
        "acfqp:v075-construction-fixture-transport-manifest:v1"
    ),
    "fixture_total_lift": (
        "acfqp:v075-construction-fixture-total-lift:v1"
    ),
    "fixture_online_work": (
        "acfqp:v075-construction-fixture-online-work:v1"
    ),
    "fixture_occurrence_evidence": (
        "acfqp:v075-construction-fixture-occurrence-evidence:v1"
    ),
    "fixture_occurrence_verification": (
        "acfqp:v075-construction-fixture-occurrence-verification:v1"
    ),
    "fixture_reconciled_occurrence": (
        "acfqp:v075-construction-fixture-reconciled-occurrence:v1"
    ),
    "fixture_arm_totals": (
        "acfqp:v075-construction-fixture-arm-totals:v1"
    ),
    "fixture_reconciliation": (
        "acfqp:v075-construction-fixture-campaign-reconciliation:v1"
    ),
    "fixture_reconciliation_verification": (
        "acfqp:v075-construction-fixture-reconciliation-verification:v1"
    ),
    "source_offline_accounting": (
        "acfqp:v075-source-offline-accounting-once:v1"
    ),
    "production_readiness": (
        "acfqp:v075-production-reconciliation-readiness:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 reconciliation content domains must be unique")


class V075CampaignReconciliationInvariantViolation(ValueError):
    """A schedule, identity, work, or classification invariant failed."""


class V075ProductionReconciliationNotReady(RuntimeError):
    """The production total-lift result protocol has not been integrated."""


def _fail(message: str) -> None:
    raise V075CampaignReconciliationInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075CampaignReconciliationInvariantViolation(str(error)) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075CampaignReconciliationInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _token(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\x00" in value
    ):
        _fail(f"{field_name} must be canonical nonempty text")
    return value


def _positive_int(value: Any, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{field_name} must be a positive integer")
    return value


class V075OccurrenceTerminalClassV1(str, Enum):
    PLAN_CERTIFICATE = "PLAN_CERTIFICATE"
    INFEASIBILITY_CERTIFICATE = "INFEASIBILITY_CERTIFICATE"
    ATTEMPT_CLOSURE_NONCERTIFICATE = "ATTEMPT_CLOSURE_NONCERTIFICATE"


class V075OccurrenceTerminalCodeV1(str, Enum):
    EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE = (
        "EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE"
    )
    EXACT_INFEASIBILITY_CERTIFICATE = "EXACT_INFEASIBILITY_CERTIFICATE"
    TOTAL_LIFT_NONCERTIFICATE = "TOTAL_LIFT_NONCERTIFICATE"
    CAP_EXHAUSTED = "CAP_EXHAUSTED"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"


class V075ConstructionTerminalEvidenceKindV1(str, Enum):
    EXACT_VALID_PLAN = "EXACT_VALID_PLAN"
    EXACT_INFEASIBLE = "EXACT_INFEASIBLE"
    TOTAL_LIFT_FAILED = "TOTAL_LIFT_FAILED"
    CAP_EXHAUSTED = "CAP_EXHAUSTED"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"


_TERMINAL_DERIVATION = {
    V075ConstructionTerminalEvidenceKindV1.EXACT_VALID_PLAN: (
        V075OccurrenceTerminalClassV1.PLAN_CERTIFICATE,
        V075OccurrenceTerminalCodeV1.EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE,
        True,
    ),
    V075ConstructionTerminalEvidenceKindV1.EXACT_INFEASIBLE: (
        V075OccurrenceTerminalClassV1.INFEASIBILITY_CERTIFICATE,
        V075OccurrenceTerminalCodeV1.EXACT_INFEASIBILITY_CERTIFICATE,
        False,
    ),
    V075ConstructionTerminalEvidenceKindV1.TOTAL_LIFT_FAILED: (
        V075OccurrenceTerminalClassV1.ATTEMPT_CLOSURE_NONCERTIFICATE,
        V075OccurrenceTerminalCodeV1.TOTAL_LIFT_NONCERTIFICATE,
        False,
    ),
    V075ConstructionTerminalEvidenceKindV1.CAP_EXHAUSTED: (
        V075OccurrenceTerminalClassV1.ATTEMPT_CLOSURE_NONCERTIFICATE,
        V075OccurrenceTerminalCodeV1.CAP_EXHAUSTED,
        False,
    ),
    V075ConstructionTerminalEvidenceKindV1.PROTOCOL_FAILURE: (
        V075OccurrenceTerminalClassV1.ATTEMPT_CLOSURE_NONCERTIFICATE,
        V075OccurrenceTerminalCodeV1.PROTOCOL_FAILURE,
        False,
    ),
    V075ConstructionTerminalEvidenceKindV1.INTEGRITY_FAILURE: (
        V075OccurrenceTerminalClassV1.ATTEMPT_CLOSURE_NONCERTIFICATE,
        V075OccurrenceTerminalCodeV1.INTEGRITY_FAILURE,
        False,
    ),
}


_PLAN_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ScientificOccurrencePlanEntryV1:
    _issuer: object
    context: public.V075PublicReplicateContextV1
    arm: str
    _occurrence_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _PLAN_ISSUER
            or type(self.context) is not public.V075PublicReplicateContextV1
            or self.arm not in ARM_ORDER
        ):
            _fail("scientific occurrence plan entry was not canonically issued")
        object.__setattr__(
            self,
            "_occurrence_id",
            _hash("plan_entry", self._payload()),
        )

    @property
    def context_ordinal(self) -> int:
        return self.context.replicate_ordinal

    @property
    def arm_ordinal(self) -> int:
        return ARM_ORDER.index(self.arm)

    @property
    def scientific_ordinal(self) -> int:
        return self.context_ordinal * ARM_COUNT + self.arm_ordinal

    @property
    def transport_ordinal(self) -> int:
        return self.scientific_ordinal + 1

    @property
    def occurrence_id(self) -> str:
        return self._occurrence_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_scientific_occurrence_plan_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context.context_id,
            "context_key": self.context.context_key,
            "context_ordinal": self.context_ordinal,
            "arm": self.arm,
            "arm_ordinal": self.arm_ordinal,
            "scientific_ordinal": self.scientific_ordinal,
            "transport_ordinal": self.transport_ordinal,
            "ordinal_mapping": ORDINAL_MAPPING,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_id": self.occurrence_id}


@dataclass(frozen=True, slots=True)
class V075ScientificOccurrencePlanV1:
    _issuer: object
    family_generation: public.V075PublicFamilyGenerationV1
    entries: tuple[V075ScientificOccurrencePlanEntryV1, ...]
    _plan_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        expected = tuple(
            V075ScientificOccurrencePlanEntryV1(_PLAN_ISSUER, context, arm)
            for context in self.family_generation.replicate_contexts
            for arm in ARM_ORDER
        )
        if (
            self._issuer is not _PLAN_ISSUER
            or type(self.family_generation)
            is not public.V075PublicFamilyGenerationV1
            or type(self.entries) is not tuple
            or self.entries != expected
            or len(self.entries) != LOGICAL_OCCURRENCE_DENOMINATOR
            or tuple(item.scientific_ordinal for item in self.entries)
            != SCIENTIFIC_ORDINALS
            or tuple(item.transport_ordinal for item in self.entries)
            != TRANSPORT_ORDINALS
            or len({item.occurrence_id for item in self.entries})
            != LOGICAL_OCCURRENCE_DENOMINATOR
        ):
            _fail("scientific occurrence plan is not the frozen 3 x 5 schedule")
        object.__setattr__(self, "_plan_id", _hash("plan", self._payload()))

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_scientific_occurrence_plan.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "family_generation_id": self.family_generation.generation_id,
            "occurrence_ids": [item.occurrence_id for item in self.entries],
            "context_count": CONTEXT_COUNT,
            "arm_count": ARM_COUNT,
            "logical_occurrence_denominator": (
                LOGICAL_OCCURRENCE_DENOMINATOR
            ),
            "schedule_order": "CONTEXT_MAJOR_ARM_MINOR_V1",
            "scientific_ordinals": list(SCIENTIFIC_ORDINALS),
            "transport_ordinals": list(TRANSPORT_ORDINALS),
            "ordinal_mapping": ORDINAL_MAPPING,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "entries": [item.to_document() for item in self.entries],
            "plan_id": self.plan_id,
        }


def freeze_v075_scientific_occurrence_plan_v1(
    family_generation: public.V075PublicFamilyGenerationV1,
) -> V075ScientificOccurrencePlanV1:
    if type(family_generation) is not public.V075PublicFamilyGenerationV1:
        _fail("plan issuer requires the exact public family-generation type")
    entries = tuple(
        V075ScientificOccurrencePlanEntryV1(_PLAN_ISSUER, context, arm)
        for context in family_generation.replicate_contexts
        for arm in ARM_ORDER
    )
    return V075ScientificOccurrencePlanV1(
        _PLAN_ISSUER,
        family_generation,
        entries,
    )


_FIXTURE_ISSUER = object()


_SOURCE_ACCOUNTING_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075SourceOfflineAccountingV1:
    """Exact replay-derived source work, charged once outside online arms."""

    _issuer: object
    source_bundle: public_source_work.V075VerifiedPublicSourceWorkBundleV1
    _accounting_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _SOURCE_ACCOUNTING_ISSUER
            or type(self.source_bundle)
            is not public_source_work.V075VerifiedPublicSourceWorkBundleV1
        ):
            _fail("source offline accounting lacks public replay verification")
        object.__setattr__(
            self,
            "_accounting_id",
            _hash("source_offline_accounting", self._payload()),
        )

    @property
    def accounting_id(self) -> str:
        return self._accounting_id

    @property
    def offline_draw_count(self) -> int:
        return self.source_bundle.offline_draw_count

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_source_offline_accounting_once.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_public_work_bundle_id": self.source_bundle.bundle_id,
            "materialization_id": self.source_bundle.materialization_id,
            "materialization_verification_id": (
                self.source_bundle.verification_id
            ),
            "source_replay_controller_status_id": (
                self.source_bundle.controller_status_id
            ),
            "source_recipe_id": self.source_bundle.source_recipe_id,
            "source_campaign_id": self.source_bundle.source_campaign_id,
            "campaign_counters_id": self.source_bundle.campaign_counters_id,
            "source_offline_draw_count": self.offline_draw_count,
            "source_offline_charge_count": 1,
            "source_offline_in_online_totals": False,
            "comparison_work_vector_materialized": False,
            "counter_completeness_claimed": False,
            "economics_available": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "workload_economics_gate_status": "NOT_RUN",
            "target_execution_allowed": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_public_work_bundle": self.source_bundle.to_document(),
            "accounting_id": self.accounting_id,
        }


def reconcile_v075_source_offline_work_once_v1(
    *,
    source_bundle: public_source_work.V075VerifiedPublicSourceWorkBundleV1,
) -> V075SourceOfflineAccountingV1:
    """Bind the law-free public replay bundle once; accepts no caller total.

    The historical source runtime is intentionally absent from this
    production dependency graph.  Its exact replay and independent
    rematerialization occur in the source-only controller before campaign
    construction.  The public authority independently recomputes the
    materialization, verification, and controller-status identity chain
    before this boundary charges its native sample work exactly once.
    """

    if (
        type(source_bundle)
        is not public_source_work.V075VerifiedPublicSourceWorkBundleV1
    ):
        _fail("source accounting requires an authority-issued public bundle")
    return V075SourceOfflineAccountingV1(
        _SOURCE_ACCOUNTING_ISSUER,
        source_bundle,
    )


@dataclass(frozen=True, slots=True)
class V075ConstructionSourceOfflineWorkFixtureV1:
    _issuer: object
    plan_id: str
    fixture_nonce: str
    offline_draw_count: int
    _fixture_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.plan_id, "fixture source plan")
        _token(self.fixture_nonce, "fixture source nonce")
        _positive_int(self.offline_draw_count, "fixture offline draw count")
        if self._issuer is not _FIXTURE_ISSUER:
            _fail("construction source work was caller-minted")
        object.__setattr__(
            self,
            "_fixture_id",
            _hash("fixture_source_work", self._payload()),
        )

    def _derived_id(self, role: str) -> str:
        return _hash(
            role,
            {
                "source_fixture_id": self.fixture_id,
                "plan_id": self.plan_id,
                "fixture_nonce": self.fixture_nonce,
                "offline_draw_count": self.offline_draw_count,
            },
        )

    @property
    def source_materialization_id(self) -> str:
        return self._derived_id("fixture_source_materialization")

    @property
    def source_verification_id(self) -> str:
        return self._derived_id("fixture_source_verification")

    @property
    def offline_work_id(self) -> str:
        return self._derived_id("fixture_offline_work")

    @property
    def fixture_id(self) -> str:
        return self._fixture_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_source_offline_work_fixture.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "plan_id": self.plan_id,
            "fixture_nonce": self.fixture_nonce,
            "offline_draw_count": self.offline_draw_count,
            "construction_fixture_only": True,
            "production_evidence": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_materialization_id": self.source_materialization_id,
            "source_verification_id": self.source_verification_id,
            "offline_work_id": self.offline_work_id,
            "fixture_id": self.fixture_id,
        }


def issue_v075_construction_source_work_fixture_v1(
    *,
    plan: V075ScientificOccurrencePlanV1,
    fixture_nonce: str,
    offline_draw_count: int,
) -> V075ConstructionSourceOfflineWorkFixtureV1:
    if type(plan) is not V075ScientificOccurrencePlanV1:
        _fail("construction source issuer requires the exact frozen plan")
    return V075ConstructionSourceOfflineWorkFixtureV1(
        _FIXTURE_ISSUER,
        plan.plan_id,
        fixture_nonce,
        offline_draw_count,
    )


@dataclass(frozen=True, slots=True)
class V075ConstructionOccurrenceEvidenceV1:
    _issuer: object
    plan_entry: V075ScientificOccurrencePlanEntryV1
    fixture_nonce: str
    online_draw_count: int
    terminal_evidence_kind: V075ConstructionTerminalEvidenceKindV1
    _evidence_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _FIXTURE_ISSUER
            or type(self.plan_entry)
            is not V075ScientificOccurrencePlanEntryV1
            or type(self.terminal_evidence_kind)
            is not V075ConstructionTerminalEvidenceKindV1
        ):
            _fail("construction occurrence evidence was caller-minted")
        _token(self.fixture_nonce, "fixture occurrence nonce")
        _positive_int(self.online_draw_count, "online draw count")
        object.__setattr__(
            self,
            "_evidence_id",
            _hash("fixture_occurrence_evidence", self._payload()),
        )

    def _derived_id(self, role: str) -> str:
        return _hash(
            role,
            {
                "occurrence_id": self.plan_entry.occurrence_id,
                "scientific_ordinal": self.plan_entry.scientific_ordinal,
                "transport_ordinal": self.plan_entry.transport_ordinal,
                "fixture_nonce": self.fixture_nonce,
                "online_draw_count": self.online_draw_count,
                "terminal_evidence_kind": self.terminal_evidence_kind.value,
            },
        )

    @property
    def observer_record_id(self) -> str:
        return self._derived_id("fixture_observer_record")

    @property
    def observer_journal_id(self) -> str:
        return self._derived_id("fixture_observer_journal")

    @property
    def transport_manifest_id(self) -> str:
        return self._derived_id("fixture_transport_manifest")

    @property
    def total_lift_result_id(self) -> str:
        return self._derived_id("fixture_total_lift")

    @property
    def online_work_id(self) -> str:
        return self._derived_id("fixture_online_work")

    @property
    def evidence_id(self) -> str:
        return self._evidence_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_construction_occurrence_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.plan_entry.occurrence_id,
            "context_id": self.plan_entry.context.context_id,
            "context_ordinal": self.plan_entry.context_ordinal,
            "arm": self.plan_entry.arm,
            "arm_ordinal": self.plan_entry.arm_ordinal,
            "scientific_ordinal": self.plan_entry.scientific_ordinal,
            "transport_ordinal": self.plan_entry.transport_ordinal,
            "fixture_nonce": self.fixture_nonce,
            "online_draw_count": self.online_draw_count,
            "terminal_evidence_kind": self.terminal_evidence_kind.value,
            "construction_fixture_only": True,
            "production_evidence": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "observer_record_id": self.observer_record_id,
            "observer_journal_id": self.observer_journal_id,
            "transport_manifest_id": self.transport_manifest_id,
            "total_lift_result_id": self.total_lift_result_id,
            "online_work_id": self.online_work_id,
            "evidence_id": self.evidence_id,
        }


def issue_v075_construction_occurrence_fixture_v1(
    *,
    plan_entry: V075ScientificOccurrencePlanEntryV1,
    fixture_nonce: str,
    online_draw_count: int,
    terminal_evidence_kind: V075ConstructionTerminalEvidenceKindV1,
) -> V075ConstructionOccurrenceEvidenceV1:
    return V075ConstructionOccurrenceEvidenceV1(
        _FIXTURE_ISSUER,
        plan_entry,
        fixture_nonce,
        online_draw_count,
        terminal_evidence_kind,
    )


_SEMANTIC_VERIFIER_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionOccurrenceSemanticVerificationV1:
    _issuer: object
    evidence: V075ConstructionOccurrenceEvidenceV1
    terminal_class: V075OccurrenceTerminalClassV1
    terminal_code: V075OccurrenceTerminalCodeV1
    exact_valid_total_lift_plan: bool
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _SEMANTIC_VERIFIER_ISSUER
            or type(self.evidence)
            is not V075ConstructionOccurrenceEvidenceV1
            or type(self.terminal_class) is not V075OccurrenceTerminalClassV1
            or type(self.terminal_code) is not V075OccurrenceTerminalCodeV1
            or type(self.exact_valid_total_lift_plan) is not bool
            or (
                self.terminal_class,
                self.terminal_code,
                self.exact_valid_total_lift_plan,
            )
            != _TERMINAL_DERIVATION[self.evidence.terminal_evidence_kind]
        ):
            _fail("occurrence classification was not semantic-verifier derived")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("fixture_occurrence_verification", self._payload()),
        )

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_occurrence_semantic_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "evidence_id": self.evidence.evidence_id,
            "occurrence_id": self.evidence.plan_entry.occurrence_id,
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "exact_valid_total_lift_plan": (
                self.exact_valid_total_lift_plan
            ),
            "classification_recomputed": True,
            "caller_status_accepted": False,
            "caller_validity_accepted": False,
            "construction_fixture_only": True,
            "production_evidence": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "evidence": self.evidence.to_document(),
            "verification_id": self.verification_id,
        }


def verify_v075_construction_occurrence_fixture_v1(
    evidence: V075ConstructionOccurrenceEvidenceV1,
) -> V075ConstructionOccurrenceSemanticVerificationV1:
    if type(evidence) is not V075ConstructionOccurrenceEvidenceV1:
        _fail("semantic verifier requires exact construction evidence")
    terminal_class, terminal_code, exact_valid = _TERMINAL_DERIVATION[
        evidence.terminal_evidence_kind
    ]
    return V075ConstructionOccurrenceSemanticVerificationV1(
        _SEMANTIC_VERIFIER_ISSUER,
        evidence,
        terminal_class,
        terminal_code,
        exact_valid,
    )


@dataclass(frozen=True, slots=True)
class V075ConstructionReconciledOccurrenceV1:
    _issuer: object
    verification: V075ConstructionOccurrenceSemanticVerificationV1
    _record_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _FIXTURE_ISSUER
            or type(self.verification)
            is not V075ConstructionOccurrenceSemanticVerificationV1
            or verify_v075_construction_occurrence_fixture_v1(
                self.verification.evidence
            )
            != self.verification
        ):
            _fail("reconciled occurrence lacks exact semantic verification")
        object.__setattr__(
            self,
            "_record_id",
            _hash("fixture_reconciled_occurrence", self._payload()),
        )

    @property
    def evidence(self) -> V075ConstructionOccurrenceEvidenceV1:
        return self.verification.evidence

    @property
    def plan_entry(self) -> V075ScientificOccurrencePlanEntryV1:
        return self.evidence.plan_entry

    @property
    def record_id(self) -> str:
        return self._record_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_reconciled_occurrence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.plan_entry.occurrence_id,
            "scientific_ordinal": self.plan_entry.scientific_ordinal,
            "transport_ordinal": self.plan_entry.transport_ordinal,
            "context_id": self.plan_entry.context.context_id,
            "context_ordinal": self.plan_entry.context_ordinal,
            "arm": self.plan_entry.arm,
            "arm_ordinal": self.plan_entry.arm_ordinal,
            "verification_id": self.verification.verification_id,
            "observer_record_id": self.evidence.observer_record_id,
            "observer_journal_id": self.evidence.observer_journal_id,
            "transport_manifest_id": self.evidence.transport_manifest_id,
            "total_lift_result_id": self.evidence.total_lift_result_id,
            "online_work_id": self.evidence.online_work_id,
            "online_draw_count": self.evidence.online_draw_count,
            "terminal_class": self.verification.terminal_class.value,
            "terminal_code": self.verification.terminal_code.value,
            "exact_valid_total_lift_plan": (
                self.verification.exact_valid_total_lift_plan
            ),
            "retained": True,
            "construction_fixture_only": True,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification": self.verification.to_document(),
            "record_id": self.record_id,
        }


@dataclass(frozen=True, slots=True)
class V075ConstructionArmOnlineAccountingV1:
    _issuer: object
    arm: str
    occurrences: tuple[V075ConstructionReconciledOccurrenceV1, ...]
    _accounting_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _FIXTURE_ISSUER
            or self.arm not in ARM_ORDER
            or type(self.occurrences) is not tuple
            or len(self.occurrences) != CONTEXT_COUNT
            or any(
                type(item) is not V075ConstructionReconciledOccurrenceV1
                for item in self.occurrences
            )
            or tuple(item.plan_entry.context_ordinal for item in self.occurrences)
            != tuple(range(CONTEXT_COUNT))
            or any(item.plan_entry.arm != self.arm for item in self.occurrences)
            or len({item.evidence.online_work_id for item in self.occurrences})
            != CONTEXT_COUNT
        ):
            _fail("per-arm online accounting is incomplete or reordered")
        object.__setattr__(
            self,
            "_accounting_id",
            _hash("fixture_arm_totals", self._payload()),
        )

    @property
    def online_draw_count(self) -> int:
        return sum(item.evidence.online_draw_count for item in self.occurrences)

    @property
    def accounting_id(self) -> str:
        return self._accounting_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_arm_online_accounting.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "arm": self.arm,
            "occurrence_record_ids": [
                item.record_id for item in self.occurrences
            ],
            "online_work_ids": [
                item.evidence.online_work_id for item in self.occurrences
            ],
            "context_online_draw_counts": [
                item.evidence.online_draw_count for item in self.occurrences
            ],
            "online_draw_count": self.online_draw_count,
            "source_offline_draws_included": False,
            "crn_draw_discount": 0,
            "construction_fixture_only": True,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "accounting_id": self.accounting_id}


@dataclass(frozen=True, slots=True)
class V075ConstructionCampaignReconciliationV1:
    _issuer: object
    plan: V075ScientificOccurrencePlanV1
    source_offline_work: V075ConstructionSourceOfflineWorkFixtureV1
    occurrences: tuple[V075ConstructionReconciledOccurrenceV1, ...]
    arm_online_accounting: tuple[
        V075ConstructionArmOnlineAccountingV1, ...
    ]
    _reconciliation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        expected_arm = tuple(
            V075ConstructionArmOnlineAccountingV1(
                _FIXTURE_ISSUER,
                arm,
                tuple(
                    item
                    for item in self.occurrences
                    if item.plan_entry.arm == arm
                ),
            )
            for arm in ARM_ORDER
        )
        target_role_ids = tuple(
            value
            for item in self.occurrences
            for value in (
                item.verification.verification_id,
                item.evidence.evidence_id,
                item.evidence.observer_record_id,
                item.evidence.observer_journal_id,
                item.evidence.transport_manifest_id,
                item.evidence.total_lift_result_id,
                item.evidence.online_work_id,
                item.record_id,
            )
        )
        source_role_ids = (
            self.source_offline_work.fixture_id,
            self.source_offline_work.source_materialization_id,
            self.source_offline_work.source_verification_id,
            self.source_offline_work.offline_work_id,
        )
        if (
            self._issuer is not _FIXTURE_ISSUER
            or type(self.plan) is not V075ScientificOccurrencePlanV1
            or type(self.source_offline_work)
            is not V075ConstructionSourceOfflineWorkFixtureV1
            or self.source_offline_work.plan_id != self.plan.plan_id
            or type(self.occurrences) is not tuple
            or len(self.occurrences) != LOGICAL_OCCURRENCE_DENOMINATOR
            or any(
                type(item) is not V075ConstructionReconciledOccurrenceV1
                for item in self.occurrences
            )
            or tuple(item.plan_entry for item in self.occurrences)
            != self.plan.entries
            or tuple(
                item.plan_entry.scientific_ordinal
                for item in self.occurrences
            )
            != SCIENTIFIC_ORDINALS
            or tuple(
                item.plan_entry.transport_ordinal for item in self.occurrences
            )
            != TRANSPORT_ORDINALS
            or len(set(target_role_ids)) != len(target_role_ids)
            or len(set(source_role_ids)) != len(source_role_ids)
            or set(target_role_ids) & set(source_role_ids)
            or self.arm_online_accounting != expected_arm
        ):
            _fail(
                "campaign reconciliation omitted, duplicated, reordered, "
                "transplanted, or role-aliased evidence"
            )
        object.__setattr__(
            self,
            "_reconciliation_id",
            _hash("fixture_reconciliation", self._payload()),
        )

    @property
    def reconciliation_id(self) -> str:
        return self._reconciliation_id

    @property
    def plan_certificate_count(self) -> int:
        return sum(
            item.verification.terminal_class
            is V075OccurrenceTerminalClassV1.PLAN_CERTIFICATE
            for item in self.occurrences
        )

    @property
    def infeasibility_certificate_count(self) -> int:
        return sum(
            item.verification.terminal_class
            is V075OccurrenceTerminalClassV1.INFEASIBILITY_CERTIFICATE
            for item in self.occurrences
        )

    @property
    def noncertificate_count(self) -> int:
        return sum(
            item.verification.terminal_class
            is V075OccurrenceTerminalClassV1.ATTEMPT_CLOSURE_NONCERTIFICATE
            for item in self.occurrences
        )

    @property
    def target_online_draw_count(self) -> int:
        return sum(
            item.evidence.online_draw_count for item in self.occurrences
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_campaign_reconciliation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "plan_id": self.plan.plan_id,
            "family_generation_id": (
                self.plan.family_generation.generation_id
            ),
            "source_offline_fixture_id": self.source_offline_work.fixture_id,
            "source_materialization_id": (
                self.source_offline_work.source_materialization_id
            ),
            "source_verification_id": (
                self.source_offline_work.source_verification_id
            ),
            "source_offline_work_id": (
                self.source_offline_work.offline_work_id
            ),
            "source_offline_draw_count": (
                self.source_offline_work.offline_draw_count
            ),
            "source_offline_charge_count": 1,
            "occurrence_record_ids": [
                item.record_id for item in self.occurrences
            ],
            "arm_online_accounting_ids": [
                item.accounting_id for item in self.arm_online_accounting
            ],
            "target_online_draw_count": self.target_online_draw_count,
            "logical_occurrence_denominator": (
                LOGICAL_OCCURRENCE_DENOMINATOR
            ),
            "plan_certificate_count": self.plan_certificate_count,
            "infeasibility_certificate_count": (
                self.infeasibility_certificate_count
            ),
            "noncertificate_count": self.noncertificate_count,
            "all_occurrences_retained": True,
            "context_major_order": True,
            "replacement_allowed": False,
            "early_stop_allowed": False,
            "source_offline_in_online_totals": False,
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
            "plan": self.plan.to_document(),
            "source_offline_work": self.source_offline_work.to_document(),
            "occurrences": [item.to_document() for item in self.occurrences],
            "arm_online_accounting": [
                item.to_document() for item in self.arm_online_accounting
            ],
            "reconciliation_id": self.reconciliation_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def reconcile_v075_construction_fixture_campaign_v1(
    *,
    plan: V075ScientificOccurrencePlanV1,
    source_offline_work: V075ConstructionSourceOfflineWorkFixtureV1,
    occurrence_verifications: Iterable[
        V075ConstructionOccurrenceSemanticVerificationV1
    ],
) -> V075ConstructionCampaignReconciliationV1:
    """Canonicalize arbitrary completion order into the frozen schedule."""

    if type(plan) is not V075ScientificOccurrencePlanV1:
        _fail("construction reconciliation requires the exact frozen plan")
    values = tuple(occurrence_verifications)
    if (
        len(values) != LOGICAL_OCCURRENCE_DENOMINATOR
        or any(
            type(item)
            is not V075ConstructionOccurrenceSemanticVerificationV1
            for item in values
        )
    ):
        _fail("construction reconciliation requires exactly 15 verifications")
    by_ordinal: dict[
        int, V075ConstructionOccurrenceSemanticVerificationV1
    ] = {}
    for item in values:
        replayed = verify_v075_construction_occurrence_fixture_v1(
            item.evidence
        )
        ordinal = item.evidence.plan_entry.scientific_ordinal
        if replayed != item or ordinal in by_ordinal:
            _fail("occurrence verification is forged or duplicated")
        by_ordinal[ordinal] = item
    if tuple(sorted(by_ordinal)) != SCIENTIFIC_ORDINALS:
        _fail("occurrence denominator has an omission or foreign ordinal")
    canonical = tuple(
        V075ConstructionReconciledOccurrenceV1(
            _FIXTURE_ISSUER,
            by_ordinal[index],
        )
        for index in SCIENTIFIC_ORDINALS
    )
    if tuple(item.plan_entry for item in canonical) != plan.entries:
        _fail("occurrence evidence was transplanted across the frozen plan")
    arm_totals = tuple(
        V075ConstructionArmOnlineAccountingV1(
            _FIXTURE_ISSUER,
            arm,
            tuple(item for item in canonical if item.plan_entry.arm == arm),
        )
        for arm in ARM_ORDER
    )
    return V075ConstructionCampaignReconciliationV1(
        _FIXTURE_ISSUER,
        plan,
        source_offline_work,
        canonical,
        arm_totals,
    )


_RECONCILIATION_VERIFIER_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionCampaignReconciliationVerificationV1:
    _issuer: object
    reconciliation_id: str
    replayed_reconciliation_id: str
    plan_id: str
    denominator: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.reconciliation_id, "claimed reconciliation"),
            (self.replayed_reconciliation_id, "replayed reconciliation"),
            (self.plan_id, "verified plan"),
        ):
            _cid(value, field_name)
        if (
            self._issuer is not _RECONCILIATION_VERIFIER_ISSUER
            or self.reconciliation_id != self.replayed_reconciliation_id
            or self.denominator != LOGICAL_OCCURRENCE_DENOMINATOR
        ):
            _fail("reconciliation verification was not independently derived")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("fixture_reconciliation_verification", self._payload()),
        )

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_campaign_reconciliation_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "reconciliation_id": self.reconciliation_id,
            "replayed_reconciliation_id": self.replayed_reconciliation_id,
            "plan_id": self.plan_id,
            "verified_occurrence_denominator": self.denominator,
            "caller_status_accepted": False,
            "caller_validity_accepted": False,
            "construction_fixture_only": True,
            "production_evidence": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_construction_campaign_reconciliation_v1(
    claimed: V075ConstructionCampaignReconciliationV1,
) -> V075ConstructionCampaignReconciliationVerificationV1:
    if type(claimed) is not V075ConstructionCampaignReconciliationV1:
        _fail("reconciliation verifier requires the exact artifact type")
    replayed = reconcile_v075_construction_fixture_campaign_v1(
        plan=claimed.plan,
        source_offline_work=claimed.source_offline_work,
        occurrence_verifications=tuple(
            item.verification for item in claimed.occurrences
        ),
    )
    if (
        replayed.reconciliation_id != claimed.reconciliation_id
        or replayed.canonical_bytes != claimed.canonical_bytes
    ):
        _fail("reconciliation differs from independent semantic replay")
    return V075ConstructionCampaignReconciliationVerificationV1(
        _RECONCILIATION_VERIFIER_ISSUER,
        claimed.reconciliation_id,
        replayed.reconciliation_id,
        claimed.plan.plan_id,
        len(claimed.occurrences),
    )


@dataclass(frozen=True, slots=True)
class V075ProductionReconciliationReadinessV1:
    _issuer: object
    _status_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self._issuer is not _PLAN_ISSUER:
            _fail("production readiness was caller-minted")
        object.__setattr__(
            self,
            "_status_id",
            _hash("production_readiness", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_production_reconciliation_readiness.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "production_occurrence_result_protocol_status": (
                PRODUCTION_OCCURRENCE_RESULT_PROTOCOL_STATUS
            ),
            "source_offline_accounting_once_implemented": True,
            "production_total_lift_adapter_implemented": False,
            "production_reconciliation_allowed": False,
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


def v075_production_reconciliation_readiness_v1(
) -> V075ProductionReconciliationReadinessV1:
    return V075ProductionReconciliationReadinessV1(_PLAN_ISSUER)


def reconcile_v075_campaign_v1() -> None:
    """Fail closed until exact production occurrence authorities exist."""

    raise V075ProductionReconciliationNotReady(
        "V0-075 production occurrence/total-lift protocol is NOT_READY; "
        "construction fixtures are not production evidence"
    )


__all__ = [
    "ARM_ORDER",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "LOGICAL_OCCURRENCE_DENOMINATOR",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "ORDINAL_MAPPING",
    "PROFILE_KEY",
    "PRODUCTION_OCCURRENCE_RESULT_PROTOCOL_STATUS",
    "SCIENTIFIC_ORDINALS",
    "TRANSPORT_ORDINALS",
    "V075CampaignReconciliationInvariantViolation",
    "V075ConstructionCampaignReconciliationV1",
    "V075ConstructionCampaignReconciliationVerificationV1",
    "V075ConstructionOccurrenceEvidenceV1",
    "V075ConstructionOccurrenceSemanticVerificationV1",
    "V075ConstructionSourceOfflineWorkFixtureV1",
    "V075ConstructionTerminalEvidenceKindV1",
    "V075OccurrenceTerminalClassV1",
    "V075OccurrenceTerminalCodeV1",
    "V075ProductionReconciliationNotReady",
    "V075SourceOfflineAccountingV1",
    "freeze_v075_scientific_occurrence_plan_v1",
    "issue_v075_construction_occurrence_fixture_v1",
    "issue_v075_construction_source_work_fixture_v1",
    "reconcile_v075_campaign_v1",
    "reconcile_v075_construction_fixture_campaign_v1",
    "reconcile_v075_source_offline_work_once_v1",
    "v075_production_reconciliation_readiness_v1",
    "verify_v075_construction_campaign_reconciliation_v1",
    "verify_v075_construction_occurrence_fixture_v1",
]
