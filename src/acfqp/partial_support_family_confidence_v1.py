"""Family-level confidence accounting for V0-068 partial-support planning.

The row authority in :mod:`acfqp.partial_support_confidence_v1` spends
``1 / 64000`` for one immutable ``(row, support epoch, authority)``.  This
module freezes the family union bound before execution.  Its positive
certificate always reports the preregistered cap, rather than replacing that
cap by the smaller number of rows that happened to be useful to a selected
plan.

The input boundary is deliberately stronger than a tuple of confidence
authorities.  Every planning consideration is named in a closed manifest and
every unique manifest identity must be accompanied by both its concrete
``GraphPartialSupportRowV1`` and its standalone replay attestation.  Thus a
verifier cannot silently retain only selected rows.  Repeated quotient and
direct considerations of the same physical authority are deduplicated, while
conflicting documents for one identity fail closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Mapping

import acfqp.observation_support_graph_acquisition_v1 as graph_acquisition
import acfqp.partial_support_confidence_v1 as row_confidence
import acfqp.transition_tuple_observer_v1 as transition_observer
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.32.0"
PROFILE_KEY = "partial_support_family_confidence_v0"

MAX_UNIQUE_ROW_EPOCHS = 512
ROW_EPOCH_TAIL_UPPER = Fraction(1, 64_000)
PREREGISTERED_FAMILY_TAIL_UPPER = (
    MAX_UNIQUE_ROW_EPOCHS * ROW_EPOCH_TAIL_UPPER
)
PREREGISTERED_FAMILY_CONFIDENCE_LOWER = (
    1 - PREREGISTERED_FAMILY_TAIL_UPPER
)

FAMILY_ACCOUNTING_RULE = (
    "PREREGISTERED_CAP_TIMES_ROW_EPOCH_TAIL_NOT_REALIZED_SELECTED_COUNT"
)
IDENTITY_RULE = "CONTEXT_ROW_SUPPORT_EPOCH_CONFIDENCE_AUTHORITY"
DEDUPLICATION_RULE = (
    "DIRECT_AND_QUOTIENT_CONSIDERATIONS_SHARE_ONE_PHYSICAL_AUTHORITY_CHARGE"
)
MANIFEST_RULE = (
    "CLOSED_ALL_CONSIDERED_MANIFEST_REQUIRES_ONE_ROW_AND_REPLAY_PER_IDENTITY"
)
REGISTERED_RANDOMNESS_IMPLEMENTATION = (
    transition_observer.REGISTERED_RANDOMNESS_IMPLEMENTATION
)
EXACT_IID_IMPLEMENTATION_CLAIMED = (
    transition_observer.EXACT_IID_IMPLEMENTATION_CLAIMED
)
STATISTICAL_CLAIM_SCOPE = transition_observer.STATISTICAL_CLAIM_SCOPE
FORMAL_EXACT_IID_PLAN_CERTIFICATE = False


DOMAIN_TAGS = {
    "identity": "acfqp:partial-support-family-row-epoch-identity:v1",
    "consideration": "acfqp:partial-support-family-consideration:v1",
    "manifest": "acfqp:partial-support-family-consideration-manifest:v1",
    "row_document": "acfqp:partial-support-family-row-document:v1",
    "replay_document": "acfqp:partial-support-family-replay-document:v1",
    "evidence": "acfqp:partial-support-family-row-epoch-evidence:v1",
    "authority": "acfqp:partial-support-family-confidence-authority:v1",
    "cap": "acfqp:partial-support-family-cap-exhausted:v1",
    "verification": (
        "acfqp:partial-support-family-confidence-verification:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("family-confidence content domains must be unique")


class PartialSupportFamilyConfidenceInvariantViolation(ValueError):
    """A family manifest, evidence set, or confidence claim is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise PartialSupportFamilyConfidenceInvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(domain + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise PartialSupportFamilyConfidenceInvariantViolation(
            f"{field_name} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise PartialSupportFamilyConfidenceInvariantViolation(
            "confidence quantities must be exact Fractions"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


class PlanningConsumerKindV1(str, Enum):
    QUOTIENT = "QUOTIENT"
    DIRECT = "DIRECT"
    PLANNER_AUDIT = "PLANNER_AUDIT"


class PartialSupportFamilyStatusV1(str, Enum):
    CONDITIONAL_STATISTICAL_CERTIFIED = (
        "CONDITIONAL_STATISTICAL_CERTIFIED"
    )
    CAP_EXHAUSTED = "CAP_EXHAUSTED"


@dataclass(frozen=True, slots=True)
class PartialSupportRowEpochIdentityV1:
    """The only identity used by family-level deduplication."""

    context_id: str
    row_id: str
    support_epoch_id: str
    confidence_authority_id: str

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.context_id, "row-epoch context"),
            (self.row_id, "row-epoch row"),
            (self.support_epoch_id, "row-epoch support epoch"),
            (
                self.confidence_authority_id,
                "row-epoch confidence authority",
            ),
        ):
            _cid(value, field_name)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_family_row_epoch_identity.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "identity_rule": IDENTITY_RULE,
            "context_id": self.context_id,
            "row_id": self.row_id,
            "support_epoch_id": self.support_epoch_id,
            "confidence_authority_id": self.confidence_authority_id,
        }

    @property
    def identity_id(self) -> str:
        return _content_id("identity", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "identity_id": self.identity_id}


def graph_row_epoch_identity_v1(
    row: graph_acquisition.GraphPartialSupportRowV1,
) -> PartialSupportRowEpochIdentityV1:
    if type(row) is not graph_acquisition.GraphPartialSupportRowV1:
        raise PartialSupportFamilyConfidenceInvariantViolation(
            "row-epoch identity requires a concrete graph row"
        )
    return PartialSupportRowEpochIdentityV1(
        context_id=row.binding.context_id,
        row_id=row.binding.row_id,
        support_epoch_id=row.support_epoch.support_epoch_id,
        confidence_authority_id=row.confidence_authority.authority_id,
    )


@dataclass(frozen=True, slots=True)
class PlanningRowEpochConsiderationV1:
    """One chronological logical use of a physical row authority."""

    planning_trace_id: str
    sequence_index: int
    logical_consumer_id: str
    consumer_kind: PlanningConsumerKindV1
    row_epoch_identity: PartialSupportRowEpochIdentityV1

    def __post_init__(self) -> None:
        _cid(self.planning_trace_id, "planning trace")
        _cid(self.logical_consumer_id, "logical consumer")
        if (
            type(self.sequence_index) is not int
            or self.sequence_index < 0
            or type(self.consumer_kind) is not PlanningConsumerKindV1
            or type(self.row_epoch_identity)
            is not PartialSupportRowEpochIdentityV1
        ):
            raise PartialSupportFamilyConfidenceInvariantViolation(
                "planning row-epoch consideration is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_family_consideration.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "planning_trace_id": self.planning_trace_id,
            "sequence_index": self.sequence_index,
            "logical_consumer_id": self.logical_consumer_id,
            "consumer_kind": self.consumer_kind.value,
            "row_epoch_identity_id": (
                self.row_epoch_identity.identity_id
            ),
        }

    @property
    def consideration_id(self) -> str:
        return _content_id("consideration", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_epoch_identity": self.row_epoch_identity.to_document(),
            "consideration_id": self.consideration_id,
        }


def bind_planning_row_epoch_consideration_v1(
    *,
    planning_trace_id: str,
    sequence_index: int,
    logical_consumer_id: str,
    consumer_kind: PlanningConsumerKindV1,
    row: graph_acquisition.GraphPartialSupportRowV1,
) -> PlanningRowEpochConsiderationV1:
    return PlanningRowEpochConsiderationV1(
        planning_trace_id=planning_trace_id,
        sequence_index=sequence_index,
        logical_consumer_id=logical_consumer_id,
        consumer_kind=consumer_kind,
        row_epoch_identity=graph_row_epoch_identity_v1(row),
    )


@dataclass(frozen=True, slots=True)
class PlanningRowEpochManifestV1:
    """Closed, chronological list of every row authority examined."""

    planning_trace_id: str
    considerations: tuple[PlanningRowEpochConsiderationV1, ...]
    unique_row_epoch_identities: tuple[
        PartialSupportRowEpochIdentityV1,
        ...,
    ]
    trace_closed: bool = True
    contains_all_considered_rows: bool = True
    manifest_rule: str = MANIFEST_RULE

    def __post_init__(self) -> None:
        _cid(self.planning_trace_id, "planning trace")
        if (
            type(self.considerations) is not tuple
            or not self.considerations
            or any(
                type(item) is not PlanningRowEpochConsiderationV1
                for item in self.considerations
            )
            or tuple(item.sequence_index for item in self.considerations)
            != tuple(range(len(self.considerations)))
            or any(
                item.planning_trace_id != self.planning_trace_id
                for item in self.considerations
            )
            or len(
                {item.consideration_id for item in self.considerations}
            )
            != len(self.considerations)
            or type(self.unique_row_epoch_identities) is not tuple
            or any(
                type(item) is not PartialSupportRowEpochIdentityV1
                for item in self.unique_row_epoch_identities
            )
            or tuple(
                item.identity_id
                for item in self.unique_row_epoch_identities
            )
            != tuple(
                sorted(
                    {
                        item.row_epoch_identity.identity_id
                        for item in self.considerations
                    }
                )
            )
            or self.trace_closed is not True
            or self.contains_all_considered_rows is not True
            or self.manifest_rule != MANIFEST_RULE
        ):
            raise PartialSupportFamilyConfidenceInvariantViolation(
                "planning manifest is not closed, complete, or canonical"
            )

    @property
    def unique_row_epoch_count(self) -> int:
        return len(self.unique_row_epoch_identities)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.partial_support_family_consideration_manifest.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "planning_trace_id": self.planning_trace_id,
            "consideration_ids": [
                item.consideration_id for item in self.considerations
            ],
            "unique_row_epoch_identity_ids": [
                item.identity_id
                for item in self.unique_row_epoch_identities
            ],
            "logical_consideration_count": len(self.considerations),
            "unique_row_epoch_count": self.unique_row_epoch_count,
            "trace_closed": True,
            "contains_all_considered_rows": True,
            "manifest_rule": MANIFEST_RULE,
        }

    @property
    def manifest_id(self) -> str:
        return _content_id("manifest", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "considerations": [
                item.to_document() for item in self.considerations
            ],
            "unique_row_epoch_identities": [
                item.to_document()
                for item in self.unique_row_epoch_identities
            ],
            "manifest_id": self.manifest_id,
        }


def freeze_planning_row_epoch_manifest_v1(
    planning_trace_id: str,
    considerations: tuple[PlanningRowEpochConsiderationV1, ...],
) -> PlanningRowEpochManifestV1:
    if (
        type(considerations) is not tuple
        or any(
            type(item) is not PlanningRowEpochConsiderationV1
            for item in considerations
        )
    ):
        raise PartialSupportFamilyConfidenceInvariantViolation(
            "manifest considerations must be an exact tuple"
        )
    by_identity = {
        item.row_epoch_identity.identity_id: item.row_epoch_identity
        for item in considerations
    }
    return PlanningRowEpochManifestV1(
        planning_trace_id=planning_trace_id,
        considerations=considerations,
        unique_row_epoch_identities=tuple(
            by_identity[key] for key in sorted(by_identity)
        ),
    )


@dataclass(frozen=True, slots=True)
class PartialSupportRowEpochEvidenceV1:
    """Concrete row plus its replay; bare confidence authorities are illegal."""

    row: graph_acquisition.GraphPartialSupportRowV1
    replay: graph_acquisition.GraphPartialSupportReplayVerificationV1
    row_epoch_identity: PartialSupportRowEpochIdentityV1 = field(init=False)
    row_document_id: str = field(init=False)
    replay_document_id: str = field(init=False)
    confidence_verification_id: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.row) is not graph_acquisition.GraphPartialSupportRowV1
            or type(self.replay)
            is not graph_acquisition.GraphPartialSupportReplayVerificationV1
        ):
            raise PartialSupportFamilyConfidenceInvariantViolation(
                "family evidence requires a concrete graph row and replay"
            )
        # The concrete GraphPartialSupportRowV1 constructor has already
        # validated this authority.  Materialize its typed expected
        # verification reference cheaply here; the independent family
        # verifier below performs the full interval/count reconstruction.
        authority = self.row.confidence_authority
        epoch = self.row.support_epoch
        confidence_verification = (
            row_confidence.PartialSupportConfidenceVerificationV1(
                authority_id=authority.authority_id,
                support_epoch_id=epoch.support_epoch_id,
                validation_evidence_id=(
                    authority.validation_evidence.validation_evidence_id
                ),
                joint_simplex_id=authority.joint_simplex.joint_simplex_id,
                event_count=epoch.event_count,
                per_event_alpha=epoch.per_event_alpha,
                row_epoch_beta=epoch.row_epoch_beta,
            )
        )
        expected_replay = (
            graph_acquisition.GraphPartialSupportReplayVerificationV1(
                partial_row_id=self.row.partial_row_id,
                physical_evidence_id=self.row.physical_evidence_id,
                confidence_verification_id=(
                    confidence_verification.verification_id
                ),
                replayed_support_epoch_index=(
                    self.row.support_epoch_index
                ),
                replayed_observer_draws=(
                    self.row.counters.total_observer_draws
                ),
                replayed_random_word_calls=(
                    self.row.counters.total_random_word_calls
                ),
                replayed_rejections=self.row.counters.total_rejections,
            )
        )
        if (
            self.replay != expected_replay
            or self.replay.to_document() != expected_replay.to_document()
        ):
            raise PartialSupportFamilyConfidenceInvariantViolation(
                "row replay does not attest this exact row authority"
            )
        identity = graph_row_epoch_identity_v1(self.row)
        row_document_id = _content_id(
            "row_document",
            {
                "schema": "acfqp.partial_support_family_row_document.v1",
                "schema_version": SCHEMA_VERSION,
                "row": self.row.to_document(),
            },
        )
        replay_document_id = _content_id(
            "replay_document",
            {
                "schema": (
                    "acfqp.partial_support_family_replay_document.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "replay": self.replay.to_document(),
            },
        )
        object.__setattr__(self, "row_epoch_identity", identity)
        object.__setattr__(self, "row_document_id", row_document_id)
        object.__setattr__(self, "replay_document_id", replay_document_id)
        object.__setattr__(
            self,
            "confidence_verification_id",
            confidence_verification.verification_id,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.partial_support_family_row_epoch_evidence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "row_epoch_identity_id": self.row_epoch_identity.identity_id,
            "partial_row_id": self.row.partial_row_id,
            "physical_evidence_id": self.row.physical_evidence_id,
            "row_document_id": self.row_document_id,
            "replay_verification_id": self.replay.verification_id,
            "replay_document_id": self.replay_document_id,
            "confidence_verification_id": (
                self.confidence_verification_id
            ),
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


def bind_partial_support_row_epoch_evidence_v1(
    row: graph_acquisition.GraphPartialSupportRowV1,
    replay: graph_acquisition.GraphPartialSupportReplayVerificationV1,
) -> PartialSupportRowEpochEvidenceV1:
    return PartialSupportRowEpochEvidenceV1(row=row, replay=replay)


def _canonical_evidence(
    evidences: tuple[PartialSupportRowEpochEvidenceV1, ...],
) -> tuple[PartialSupportRowEpochEvidenceV1, ...]:
    if (
        type(evidences) is not tuple
        or any(
            type(item) is not PartialSupportRowEpochEvidenceV1
            for item in evidences
        )
    ):
        raise PartialSupportFamilyConfidenceInvariantViolation(
            "family input forbids bare confidence authorities"
        )
    by_identity: dict[str, PartialSupportRowEpochEvidenceV1] = {}
    for item in evidences:
        expected_identity = graph_row_epoch_identity_v1(item.row)
        expected_row_document_id = _content_id(
            "row_document",
            {
                "schema": "acfqp.partial_support_family_row_document.v1",
                "schema_version": SCHEMA_VERSION,
                "row": item.row.to_document(),
            },
        )
        expected_replay_document_id = _content_id(
            "replay_document",
            {
                "schema": (
                    "acfqp.partial_support_family_replay_document.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "replay": item.replay.to_document(),
            },
        )
        if (
            item.row_epoch_identity != expected_identity
            or item.row_document_id != expected_row_document_id
            or item.replay_document_id != expected_replay_document_id
            or item.replay.partial_row_id != item.row.partial_row_id
            or item.replay.physical_evidence_id
            != item.row.physical_evidence_id
            or item.replay.replayed_support_epoch_index
            != item.row.support_epoch_index
            or item.replay.replayed_observer_draws
            != item.row.counters.total_observer_draws
            or item.replay.replayed_random_word_calls
            != item.row.counters.total_random_word_calls
            or item.replay.replayed_rejections
            != item.row.counters.total_rejections
            or item.replay.confidence_verification_id
            != item.confidence_verification_id
        ):
            raise PartialSupportFamilyConfidenceInvariantViolation(
                "row-epoch evidence changed after construction"
            )
        identity_id = item.row_epoch_identity.identity_id
        previous = by_identity.setdefault(identity_id, item)
        if (
            previous.row_document_id != item.row_document_id
            or previous.replay_document_id != item.replay_document_id
            or previous.evidence_id != item.evidence_id
        ):
            raise PartialSupportFamilyConfidenceInvariantViolation(
                "one row-epoch identity is bound to different documents"
            )
    return tuple(by_identity[key] for key in sorted(by_identity))


@dataclass(frozen=True, slots=True)
class PartialSupportFamilyConfidenceAuthorityV1:
    manifest: PlanningRowEpochManifestV1
    unique_evidences: tuple[PartialSupportRowEpochEvidenceV1, ...]
    family_status: PartialSupportFamilyStatusV1 = (
        PartialSupportFamilyStatusV1.CONDITIONAL_STATISTICAL_CERTIFIED
    )
    maximum_unique_row_epochs: int = MAX_UNIQUE_ROW_EPOCHS
    row_epoch_tail_upper: Fraction = ROW_EPOCH_TAIL_UPPER
    family_tail_upper: Fraction = PREREGISTERED_FAMILY_TAIL_UPPER
    family_confidence_lower: Fraction = (
        PREREGISTERED_FAMILY_CONFIDENCE_LOWER
    )
    certification_allowed: bool = True
    randomness_implementation: str = REGISTERED_RANDOMNESS_IMPLEMENTATION
    exact_iid_implementation_claimed: bool = (
        EXACT_IID_IMPLEMENTATION_CLAIMED
    )
    statistical_claim_scope: str = STATISTICAL_CLAIM_SCOPE
    formal_exact_iid_plan_certificate: bool = (
        FORMAL_EXACT_IID_PLAN_CERTIFICATE
    )

    def __post_init__(self) -> None:
        if (
            type(self.manifest) is not PlanningRowEpochManifestV1
            or type(self.unique_evidences) is not tuple
            or any(
                type(item) is not PartialSupportRowEpochEvidenceV1
                for item in self.unique_evidences
            )
            or tuple(
                item.row_epoch_identity.identity_id
                for item in self.unique_evidences
            )
            != tuple(
                item.identity_id
                for item in self.manifest.unique_row_epoch_identities
            )
            or self.manifest.unique_row_epoch_count
            != len(self.unique_evidences)
            or self.manifest.unique_row_epoch_count
            > MAX_UNIQUE_ROW_EPOCHS
            or self.family_status
            is not (
                PartialSupportFamilyStatusV1
                .CONDITIONAL_STATISTICAL_CERTIFIED
            )
            or self.maximum_unique_row_epochs != MAX_UNIQUE_ROW_EPOCHS
            or self.row_epoch_tail_upper != ROW_EPOCH_TAIL_UPPER
            or self.family_tail_upper
            != PREREGISTERED_FAMILY_TAIL_UPPER
            or self.family_confidence_lower
            != 1 - self.family_tail_upper
            or self.certification_allowed is not True
            or self.randomness_implementation
            != REGISTERED_RANDOMNESS_IMPLEMENTATION
            or self.exact_iid_implementation_claimed is not False
            or self.statistical_claim_scope != STATISTICAL_CLAIM_SCOPE
            or self.formal_exact_iid_plan_certificate is not False
        ):
            raise PartialSupportFamilyConfidenceInvariantViolation(
                "family confidence authority is incomplete or not preregistered"
            )

    @property
    def realized_unique_row_epoch_count(self) -> int:
        return len(self.unique_evidences)

    @property
    def realized_family_tail_diagnostic(self) -> Fraction:
        return (
            self.realized_unique_row_epoch_count
            * self.row_epoch_tail_upper
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.partial_support_family_confidence_authority.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "manifest_id": self.manifest.manifest_id,
            "planning_trace_id": self.manifest.planning_trace_id,
            "unique_row_epoch_identity_ids": [
                item.row_epoch_identity.identity_id
                for item in self.unique_evidences
            ],
            "unique_evidence_ids": [
                item.evidence_id for item in self.unique_evidences
            ],
            "realized_unique_row_epoch_count": (
                self.realized_unique_row_epoch_count
            ),
            "maximum_unique_row_epochs": self.maximum_unique_row_epochs,
            "row_epoch_tail_upper": _fdoc(self.row_epoch_tail_upper),
            "realized_family_tail_diagnostic": _fdoc(
                self.realized_family_tail_diagnostic
            ),
            "family_tail_upper": _fdoc(self.family_tail_upper),
            "family_confidence_lower": _fdoc(
                self.family_confidence_lower
            ),
            "family_status": self.family_status.value,
            "certification_allowed": True,
            "randomness_implementation": self.randomness_implementation,
            "exact_iid_implementation_claimed": False,
            "statistical_claim_scope": self.statistical_claim_scope,
            "formal_exact_iid_plan_certificate": False,
            "family_accounting_rule": FAMILY_ACCOUNTING_RULE,
            "deduplication_rule": DEDUPLICATION_RULE,
            "manifest_rule": MANIFEST_RULE,
        }

    @property
    def authority_id(self) -> str:
        return _content_id("authority", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "authority_id": self.authority_id}


@dataclass(frozen=True, slots=True)
class PartialSupportFamilyCapExhaustedV1:
    """Typed non-certificate closure when the preregistered cap is exceeded."""

    manifest: PlanningRowEpochManifestV1
    family_status: PartialSupportFamilyStatusV1 = (
        PartialSupportFamilyStatusV1.CAP_EXHAUSTED
    )
    maximum_unique_row_epochs: int = MAX_UNIQUE_ROW_EPOCHS
    row_epoch_tail_upper: Fraction = ROW_EPOCH_TAIL_UPPER
    family_tail_upper: Fraction = PREREGISTERED_FAMILY_TAIL_UPPER
    family_confidence_lower: Fraction = (
        PREREGISTERED_FAMILY_CONFIDENCE_LOWER
    )
    certification_allowed: bool = False
    randomness_implementation: str = REGISTERED_RANDOMNESS_IMPLEMENTATION
    exact_iid_implementation_claimed: bool = (
        EXACT_IID_IMPLEMENTATION_CLAIMED
    )
    statistical_claim_scope: str = STATISTICAL_CLAIM_SCOPE
    formal_exact_iid_plan_certificate: bool = (
        FORMAL_EXACT_IID_PLAN_CERTIFICATE
    )

    def __post_init__(self) -> None:
        if (
            type(self.manifest) is not PlanningRowEpochManifestV1
            or self.manifest.unique_row_epoch_count
            <= MAX_UNIQUE_ROW_EPOCHS
            or self.family_status
            is not PartialSupportFamilyStatusV1.CAP_EXHAUSTED
            or self.maximum_unique_row_epochs != MAX_UNIQUE_ROW_EPOCHS
            or self.row_epoch_tail_upper != ROW_EPOCH_TAIL_UPPER
            or self.family_tail_upper
            != PREREGISTERED_FAMILY_TAIL_UPPER
            or self.family_confidence_lower
            != 1 - self.family_tail_upper
            or self.certification_allowed is not False
            or self.randomness_implementation
            != REGISTERED_RANDOMNESS_IMPLEMENTATION
            or self.exact_iid_implementation_claimed is not False
            or self.statistical_claim_scope != STATISTICAL_CLAIM_SCOPE
            or self.formal_exact_iid_plan_certificate is not False
        ):
            raise PartialSupportFamilyConfidenceInvariantViolation(
                "family cap-exhausted closure is not canonical"
            )

    @property
    def realized_unique_row_epoch_count(self) -> int:
        return self.manifest.unique_row_epoch_count

    @property
    def realized_family_tail_diagnostic(self) -> Fraction:
        return (
            self.realized_unique_row_epoch_count
            * self.row_epoch_tail_upper
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_family_cap_exhausted.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "manifest_id": self.manifest.manifest_id,
            "planning_trace_id": self.manifest.planning_trace_id,
            "realized_unique_row_epoch_count": (
                self.realized_unique_row_epoch_count
            ),
            "maximum_unique_row_epochs": self.maximum_unique_row_epochs,
            "row_epoch_tail_upper": _fdoc(self.row_epoch_tail_upper),
            "realized_family_tail_diagnostic": _fdoc(
                self.realized_family_tail_diagnostic
            ),
            "family_tail_upper": _fdoc(self.family_tail_upper),
            "family_confidence_lower": _fdoc(
                self.family_confidence_lower
            ),
            "family_status": self.family_status.value,
            "certification_allowed": False,
            "randomness_implementation": self.randomness_implementation,
            "exact_iid_implementation_claimed": False,
            "statistical_claim_scope": self.statistical_claim_scope,
            "formal_exact_iid_plan_certificate": False,
            "family_accounting_rule": FAMILY_ACCOUNTING_RULE,
            "manifest_rule": MANIFEST_RULE,
        }

    @property
    def closure_id(self) -> str:
        return _content_id("cap", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self.closure_id}


PartialSupportFamilyBuildResultV1 = (
    PartialSupportFamilyConfidenceAuthorityV1
    | PartialSupportFamilyCapExhaustedV1
)


def build_partial_support_family_confidence_v1(
    manifest: PlanningRowEpochManifestV1,
    evidences: tuple[PartialSupportRowEpochEvidenceV1, ...],
) -> PartialSupportFamilyBuildResultV1:
    """Build the family authority, or close with typed ``CAP_EXHAUSTED``."""

    if type(manifest) is not PlanningRowEpochManifestV1:
        raise PartialSupportFamilyConfidenceInvariantViolation(
            "family build requires the closed all-considered manifest"
        )
    if manifest.unique_row_epoch_count > MAX_UNIQUE_ROW_EPOCHS:
        if (
            type(evidences) is not tuple
            or any(
                type(item) is not PartialSupportRowEpochEvidenceV1
                for item in evidences
            )
        ):
            raise PartialSupportFamilyConfidenceInvariantViolation(
                "family input forbids bare confidence authorities"
            )
        return PartialSupportFamilyCapExhaustedV1(manifest=manifest)
    canonical = _canonical_evidence(evidences)
    manifest_ids = tuple(
        item.identity_id for item in manifest.unique_row_epoch_identities
    )
    evidence_ids = tuple(
        item.row_epoch_identity.identity_id for item in canonical
    )
    if evidence_ids != manifest_ids:
        raise PartialSupportFamilyConfidenceInvariantViolation(
            "family evidence omits considered rows or adds unconsidered rows"
        )
    return PartialSupportFamilyConfidenceAuthorityV1(
        manifest=manifest,
        unique_evidences=canonical,
    )


@dataclass(frozen=True, slots=True)
class PartialSupportFamilyConfidenceVerificationV1:
    family_authority_id: str
    manifest_id: str
    planning_trace_id: str
    rebuilt_row_epoch_identity_ids: tuple[str, ...]
    rebuilt_row_authority_ids: tuple[str, ...]
    rebuilt_confidence_verification_ids: tuple[str, ...]
    rebuilt_replay_verification_ids: tuple[str, ...]
    realized_unique_row_epoch_count: int
    maximum_unique_row_epochs: int
    family_tail_upper: Fraction
    family_confidence_lower: Fraction
    randomness_implementation: str = REGISTERED_RANDOMNESS_IMPLEMENTATION
    exact_iid_implementation_claimed: bool = (
        EXACT_IID_IMPLEMENTATION_CLAIMED
    )
    statistical_claim_scope: str = STATISTICAL_CLAIM_SCOPE
    formal_exact_iid_plan_certificate: bool = (
        FORMAL_EXACT_IID_PLAN_CERTIFICATE
    )
    verification_result: str = (
        "VALID_COMPLETE_CONDITIONAL_PARTIAL_SUPPORT_FAMILY_CONFIDENCE"
    )

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.family_authority_id, "family authority"),
            (self.manifest_id, "family manifest"),
            (self.planning_trace_id, "planning trace"),
        ):
            _cid(value, field_name)
        sequences = (
            self.rebuilt_row_epoch_identity_ids,
            self.rebuilt_row_authority_ids,
            self.rebuilt_confidence_verification_ids,
            self.rebuilt_replay_verification_ids,
        )
        if (
            any(type(items) is not tuple for items in sequences)
            or any(
                _cid(item, "rebuilt family evidence") != item
                for items in sequences
                for item in items
            )
            or any(
                len(items) != self.realized_unique_row_epoch_count
                for items in sequences
            )
            or type(self.realized_unique_row_epoch_count) is not int
            or not 1
            <= self.realized_unique_row_epoch_count
            <= MAX_UNIQUE_ROW_EPOCHS
            or self.maximum_unique_row_epochs != MAX_UNIQUE_ROW_EPOCHS
            or self.family_tail_upper
            != PREREGISTERED_FAMILY_TAIL_UPPER
            or self.family_confidence_lower
            != 1 - self.family_tail_upper
            or self.randomness_implementation
            != REGISTERED_RANDOMNESS_IMPLEMENTATION
            or self.exact_iid_implementation_claimed is not False
            or self.statistical_claim_scope != STATISTICAL_CLAIM_SCOPE
            or self.formal_exact_iid_plan_certificate is not False
            or self.verification_result
            != (
                "VALID_COMPLETE_CONDITIONAL_"
                "PARTIAL_SUPPORT_FAMILY_CONFIDENCE"
            )
        ):
            raise PartialSupportFamilyConfidenceInvariantViolation(
                "family confidence verification is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.partial_support_family_confidence_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "family_authority_id": self.family_authority_id,
            "manifest_id": self.manifest_id,
            "planning_trace_id": self.planning_trace_id,
            "rebuilt_row_epoch_identity_ids": list(
                self.rebuilt_row_epoch_identity_ids
            ),
            "rebuilt_row_authority_ids": list(
                self.rebuilt_row_authority_ids
            ),
            "rebuilt_confidence_verification_ids": list(
                self.rebuilt_confidence_verification_ids
            ),
            "rebuilt_replay_verification_ids": list(
                self.rebuilt_replay_verification_ids
            ),
            "realized_unique_row_epoch_count": (
                self.realized_unique_row_epoch_count
            ),
            "maximum_unique_row_epochs": self.maximum_unique_row_epochs,
            "family_tail_upper": _fdoc(self.family_tail_upper),
            "family_confidence_lower": _fdoc(
                self.family_confidence_lower
            ),
            "randomness_implementation": self.randomness_implementation,
            "exact_iid_implementation_claimed": False,
            "statistical_claim_scope": self.statistical_claim_scope,
            "formal_exact_iid_plan_certificate": False,
            "verification_result": self.verification_result,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_partial_support_family_confidence_v1(
    authority: PartialSupportFamilyConfidenceAuthorityV1,
    manifest: PlanningRowEpochManifestV1,
    evidences: tuple[PartialSupportRowEpochEvidenceV1, ...],
) -> PartialSupportFamilyConfidenceVerificationV1:
    """Rebuild every row authority and require the full manifest evidence set."""

    if (
        type(authority)
        is not PartialSupportFamilyConfidenceAuthorityV1
        or type(manifest) is not PlanningRowEpochManifestV1
        or authority.manifest.manifest_id != manifest.manifest_id
        or authority.manifest.to_document() != manifest.to_document()
    ):
        raise PartialSupportFamilyConfidenceInvariantViolation(
            "verification requires the exact certified family and manifest"
        )
    # Re-run every concrete row confidence authority exactly once.  The
    # ordinary builder only needs to check immutable bindings because each
    # concrete row already performed validation at creation.
    canonical_input = _canonical_evidence(evidences)
    fully_rebuilt: list[PartialSupportRowEpochEvidenceV1] = []
    for item in canonical_input:
        confidence_verification = (
            row_confidence.verify_partial_support_confidence_v1(
                item.row.confidence_authority
            )
        )
        if (
            confidence_verification.verification_id
            != item.confidence_verification_id
        ):
            raise PartialSupportFamilyConfidenceInvariantViolation(
                "row confidence authority changed during family replay"
            )
        fully_rebuilt.append(
            PartialSupportRowEpochEvidenceV1(
                row=item.row,
                replay=item.replay,
            )
        )
    fully_rebuilt_evidences = tuple(fully_rebuilt)
    rebuilt = build_partial_support_family_confidence_v1(
        manifest,
        fully_rebuilt_evidences,
    )
    if (
        type(rebuilt) is not PartialSupportFamilyConfidenceAuthorityV1
        or rebuilt != authority
        or rebuilt.to_document() != authority.to_document()
        or rebuilt.authority_id != authority.authority_id
    ):
        raise PartialSupportFamilyConfidenceInvariantViolation(
            "family confidence authority does not survive complete replay"
        )
    return PartialSupportFamilyConfidenceVerificationV1(
        family_authority_id=rebuilt.authority_id,
        manifest_id=manifest.manifest_id,
        planning_trace_id=manifest.planning_trace_id,
        rebuilt_row_epoch_identity_ids=tuple(
            item.row_epoch_identity.identity_id
            for item in rebuilt.unique_evidences
        ),
        rebuilt_row_authority_ids=tuple(
            item.row.confidence_authority.authority_id
            for item in rebuilt.unique_evidences
        ),
        rebuilt_confidence_verification_ids=tuple(
            item.confidence_verification_id
            for item in rebuilt.unique_evidences
        ),
        rebuilt_replay_verification_ids=tuple(
            item.replay.verification_id
            for item in rebuilt.unique_evidences
        ),
        realized_unique_row_epoch_count=(
            rebuilt.realized_unique_row_epoch_count
        ),
        maximum_unique_row_epochs=MAX_UNIQUE_ROW_EPOCHS,
        family_tail_upper=rebuilt.family_tail_upper,
        family_confidence_lower=rebuilt.family_confidence_lower,
        randomness_implementation=rebuilt.randomness_implementation,
        exact_iid_implementation_claimed=False,
        statistical_claim_scope=rebuilt.statistical_claim_scope,
        formal_exact_iid_plan_certificate=False,
    )


__all__ = [
    "CONTRACT_VERSION",
    "DEDUPLICATION_RULE",
    "EXACT_IID_IMPLEMENTATION_CLAIMED",
    "FAMILY_ACCOUNTING_RULE",
    "FORMAL_EXACT_IID_PLAN_CERTIFICATE",
    "IDENTITY_RULE",
    "MANIFEST_RULE",
    "MAX_UNIQUE_ROW_EPOCHS",
    "PROFILE_KEY",
    "PREREGISTERED_FAMILY_CONFIDENCE_LOWER",
    "PREREGISTERED_FAMILY_TAIL_UPPER",
    "REGISTERED_RANDOMNESS_IMPLEMENTATION",
    "PartialSupportFamilyBuildResultV1",
    "PartialSupportFamilyCapExhaustedV1",
    "PartialSupportFamilyConfidenceAuthorityV1",
    "PartialSupportFamilyConfidenceInvariantViolation",
    "PartialSupportFamilyConfidenceVerificationV1",
    "PartialSupportFamilyStatusV1",
    "PartialSupportRowEpochEvidenceV1",
    "PartialSupportRowEpochIdentityV1",
    "PlanningConsumerKindV1",
    "PlanningRowEpochConsiderationV1",
    "PlanningRowEpochManifestV1",
    "ROW_EPOCH_TAIL_UPPER",
    "SCHEMA_VERSION",
    "STATISTICAL_CLAIM_SCOPE",
    "bind_partial_support_row_epoch_evidence_v1",
    "bind_planning_row_epoch_consideration_v1",
    "build_partial_support_family_confidence_v1",
    "freeze_planning_row_epoch_manifest_v1",
    "graph_row_epoch_identity_v1",
    "verify_partial_support_family_confidence_v1",
]
