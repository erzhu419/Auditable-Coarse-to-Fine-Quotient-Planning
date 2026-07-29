"""Split-support confidence authority for partial joint rows (V0-068).

Discovery and validation are deliberately different statistical roles.
Discovery freezes a finite set of named joint outcomes ``S``.  A fresh,
independent validation stream is then projected onto ``S`` plus exactly one
``OTHER`` event.  Every validation draw contributes to exactly one category.

For ``m = |S| + 1`` categories, each Bernoulli event receives
``alpha = (1 / 64000) / m``.  The per-event intervals reuse the exact
uniform-beta likelihood-mixture Ville confidence sequence implemented by
``sequential_bernoulli_acquisition_v1``.  Their Cartesian product is
intersected with the exact probability simplex.  A union bound therefore
gives row-epoch simultaneous coverage at least ``1 - 1/64000`` at every
registered, data-dependent checkpoint.

Outcomes discovered during validation are reported as novel identities but
remain inside the one ``OTHER`` coordinate for that immutable support epoch.
They may propose the next support epoch, but their old samples are explicitly
proposal-only and can never be reused as probability evidence in the new
epoch.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Mapping, Protocol, runtime_checkable

from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp.sequential_bernoulli_acquisition_v1 import (
    AnytimeBernoulliCheckpointV1,
    SequentialBernoulliProfileV1,
    build_anytime_bernoulli_checkpoint_v1,
)


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.32.0"
PROFILE_KEY = "split_support_confidence_v0"

ROW_EPOCH_BETA = Fraction(1, 64_000)
MAX_DISCOVERED_ATOMS = 16
MAX_EVENT_COUNT = MAX_DISCOVERED_ATOMS + 1
OTHER_EVENT_KEY = "OTHER"
DEFAULT_CHECKPOINTS = (
    64,
    128,
    256,
    512,
    1_024,
    2_048,
    4_096,
    8_192,
    16_384,
)
DEFAULT_TARGET_HALF_WIDTH = Fraction(1, 64)
DEFAULT_BOUNDARY_GRID_BITS = 16

CONFIDENCE_ACCOUNTING = (
    "BONFERRONI_OVER_FROZEN_SUPPORT_PLUS_ONE_OTHER_WITH_PER_EVENT_VILLE_CS"
)
SUPPORT_FREEZE_RULE = "DISCOVERY_OR_PRIOR_VALIDATION_PROPOSAL_BEFORE_VALIDATION"
OTHER_ACCOUNTING_RULE = "ONE_AND_ONLY_ONE_OTHER_SIMPLEX_COORDINATE"
PROMOTION_RULE = (
    "PRIOR_VALIDATION_NOVEL_OUTCOMES_PROPOSE_SUPPORT_ONLY_FRESH_VALIDATION_REQUIRED"
)


DOMAIN_TAGS = {
    "outcome_binding": "acfqp:opaque-observed-joint-outcome-binding:v1",
    "observation": "acfqp:split-support-observation:v1",
    "discovery": "acfqp:split-support-discovery-evidence:v1",
    "support_epoch": "acfqp:frozen-split-support-epoch:v1",
    "validation": "acfqp:split-support-validation-evidence:v1",
    "promotion": "acfqp:split-support-promotion-evidence:v1",
    "promoted_epoch": "acfqp:promoted-split-support-epoch:v1",
    "profile": "acfqp:partial-support-confidence-profile:v1",
    "event_interval": "acfqp:partial-support-event-interval:v1",
    "simplex": "acfqp:partial-support-joint-simplex:v1",
    "authority": "acfqp:partial-support-confidence-authority:v1",
    "verification": "acfqp:partial-support-confidence-verification:v1",
}


class PartialSupportConfidenceInvariantViolation(ValueError):
    """A support split, sample lineage, interval, or simplex is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        tag = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise PartialSupportConfidenceInvariantViolation(str(error)) from error
    return hashlib.sha256(tag + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise PartialSupportConfidenceInvariantViolation(
            f"{field_name} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise PartialSupportConfidenceInvariantViolation(
            "probability values must be exact Fractions"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


@runtime_checkable
class ObservedJointOutcomeProtocol(Protocol):
    """Small observer boundary: an opaque identity and a canonical document."""

    @property
    def outcome_id(self) -> str: ...

    @property
    def document(self) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True, init=False)
class OpaqueObservedJointOutcomeV1:
    """Immutable canonical copy of an observer-owned joint outcome."""

    outcome_id: str
    _document_bytes: bytes = field(repr=False)
    _document_object: dict[str, Any] = field(repr=False, compare=False)
    _outcome_binding_id: str = field(init=False, repr=False)

    def __init__(
        self,
        outcome_id: str,
        document: Mapping[str, Any],
    ) -> None:
        _cid(outcome_id, "outcome")
        if not isinstance(document, Mapping):
            raise PartialSupportConfidenceInvariantViolation(
                "opaque outcome document must be a mapping"
            )
        try:
            encoded = canonical_json_bytes(dict(document))
        except (TypeError, ValueError) as error:
            raise PartialSupportConfidenceInvariantViolation(
                f"opaque outcome document is not canonical: {error}"
            ) from error
        decoded = loads_canonical_json(encoded)
        if type(decoded) is not dict:
            raise PartialSupportConfidenceInvariantViolation(
                "stored opaque outcome document is not an object"
            )
        object.__setattr__(self, "outcome_id", outcome_id)
        object.__setattr__(self, "_document_bytes", encoded)
        object.__setattr__(self, "_document_object", decoded)
        object.__setattr__(
            self,
            "_outcome_binding_id",
            _content_id(
                "outcome_binding",
                {
                    "schema": (
                        "acfqp.opaque_observed_joint_outcome_binding.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "outcome_id": outcome_id,
                    "document": decoded,
                },
            ),
        )

    @property
    def document(self) -> Mapping[str, Any]:
        return copy.deepcopy(self._document_object)

    @property
    def outcome_binding_id(self) -> str:
        return self._outcome_binding_id

    def _trusted_to_document(self) -> dict[str, Any]:
        """Internal immutable-use view; callers must never mutate it."""

        return {
            "outcome_id": self.outcome_id,
            "outcome_binding_id": self.outcome_binding_id,
            "document": self._document_object,
        }

    def to_document(self) -> dict[str, Any]:
        return copy.deepcopy(self._trusted_to_document())


def freeze_observed_joint_outcome_v1(
    value: ObservedJointOutcomeProtocol | OpaqueObservedJointOutcomeV1,
) -> OpaqueObservedJointOutcomeV1:
    """Copy an observer outcome across the opaque protocol boundary."""

    if type(value) is OpaqueObservedJointOutcomeV1:
        return value
    if not isinstance(value, ObservedJointOutcomeProtocol):
        raise PartialSupportConfidenceInvariantViolation(
            "joint outcome does not implement outcome_id + document"
        )
    return OpaqueObservedJointOutcomeV1(value.outcome_id, value.document)


@dataclass(frozen=True, slots=True)
class SplitSupportObservationV1:
    """One globally identified draw in one discovery or validation stream."""

    stream_domain_id: str
    sample_id: str
    sequence_index: int
    outcome: OpaqueObservedJointOutcomeV1
    _observation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.stream_domain_id, "stream domain")
        _cid(self.sample_id, "sample")
        if (
            type(self.sequence_index) is not int
            or self.sequence_index < 0
            or type(self.outcome) is not OpaqueObservedJointOutcomeV1
        ):
            raise PartialSupportConfidenceInvariantViolation(
                "split-support observation is malformed"
            )
        object.__setattr__(
            self,
            "_observation_id",
            _content_id("observation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.split_support_observation.v1",
            "schema_version": SCHEMA_VERSION,
            "stream_domain_id": self.stream_domain_id,
            "sample_id": self.sample_id,
            "sequence_index": self.sequence_index,
            "outcome": self.outcome._trusted_to_document(),
        }

    @property
    def observation_id(self) -> str:
        return self._observation_id

    def to_document(self) -> dict[str, Any]:
        return copy.deepcopy(
            {**self._payload(), "observation_id": self.observation_id}
        )


def _validate_observation_stream(
    observations: tuple[SplitSupportObservationV1, ...],
    stream_domain_id: str,
    *,
    allow_empty: bool = False,
) -> None:
    _cid(stream_domain_id, "stream domain")
    if (
        type(observations) is not tuple
        or (not observations and not allow_empty)
        or any(type(item) is not SplitSupportObservationV1 for item in observations)
        or tuple(item.sequence_index for item in observations)
        != tuple(range(len(observations)))
        or any(item.stream_domain_id != stream_domain_id for item in observations)
        or len({item.sample_id for item in observations}) != len(observations)
    ):
        raise PartialSupportConfidenceInvariantViolation(
            "observation stream is not contiguous, unique, and domain-bound"
        )
    documents: dict[str, bytes] = {}
    for observation in observations:
        outcome = observation.outcome
        previous = documents.setdefault(outcome.outcome_id, outcome._document_bytes)
        if previous != outcome._document_bytes:
            raise PartialSupportConfidenceInvariantViolation(
                "one outcome ID is bound to different opaque documents"
            )


def _representative_outcomes(
    observations: tuple[SplitSupportObservationV1, ...],
) -> tuple[OpaqueObservedJointOutcomeV1, ...]:
    by_id: dict[str, OpaqueObservedJointOutcomeV1] = {}
    for observation in observations:
        current = observation.outcome
        previous = by_id.setdefault(current.outcome_id, current)
        if previous._document_bytes != current._document_bytes:
            raise PartialSupportConfidenceInvariantViolation(
                "one outcome ID is bound to different opaque documents"
            )
    return tuple(by_id[key] for key in sorted(by_id))


@dataclass(frozen=True, slots=True)
class DiscoverySupportEvidenceV1:
    """Independent observations used only to freeze support, never intervals."""

    row_id: str
    support_epoch_index: int
    discovery_stream_domain_id: str
    observations: tuple[SplitSupportObservationV1, ...]
    discovered_support_outcomes: tuple[OpaqueObservedJointOutcomeV1, ...]
    support_selection_only: bool = True
    probability_evidence_draw_count: int = 0
    _discovery_evidence_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.row_id, "row")
        _validate_observation_stream(
            self.observations,
            self.discovery_stream_domain_id,
        )
        expected = _representative_outcomes(self.observations)
        if (
            type(self.support_epoch_index) is not int
            or self.support_epoch_index < 1
            or type(self.discovered_support_outcomes) is not tuple
            or any(
                type(item) is not OpaqueObservedJointOutcomeV1
                for item in self.discovered_support_outcomes
            )
            or self.discovered_support_outcomes != expected
            or len(expected) > MAX_DISCOVERED_ATOMS
            or self.support_selection_only is not True
            or self.probability_evidence_draw_count != 0
        ):
            raise PartialSupportConfidenceInvariantViolation(
                "discovery support evidence is not a bounded proposal-only freeze"
            )
        object.__setattr__(
            self,
            "_discovery_evidence_id",
            _content_id("discovery", self._payload()),
        )

    @property
    def sample_ids(self) -> tuple[str, ...]:
        return tuple(item.sample_id for item in self.observations)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.split_support_discovery_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "row_id": self.row_id,
            "support_epoch_index": self.support_epoch_index,
            "discovery_stream_domain_id": self.discovery_stream_domain_id,
            "observation_ids": [
                item.observation_id for item in self.observations
            ],
            "discovered_support": [
                item.to_document() for item in self.discovered_support_outcomes
            ],
            "support_selection_only": True,
            "probability_evidence_draw_count": 0,
        }

    @property
    def discovery_evidence_id(self) -> str:
        return self._discovery_evidence_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "discovery_evidence_id": self.discovery_evidence_id}


@dataclass(frozen=True, slots=True)
class FrozenSupportEpochV1:
    """Immutable initial support selected before its validation stream."""

    row_id: str
    support_epoch_index: int
    discovery_evidence: DiscoverySupportEvidenceV1
    validation_stream_domain_id: str
    support_outcomes: tuple[OpaqueObservedJointOutcomeV1, ...]
    event_count: int
    per_event_alpha: Fraction
    row_epoch_beta: Fraction = ROW_EPOCH_BETA
    support_freeze_rule: str = SUPPORT_FREEZE_RULE
    _support_epoch_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.row_id, "row")
        _cid(self.validation_stream_domain_id, "validation stream domain")
        if type(self.discovery_evidence) is not DiscoverySupportEvidenceV1:
            raise PartialSupportConfidenceInvariantViolation(
                "initial support epoch has invalid discovery evidence"
            )
        expected_support = self.discovery_evidence.discovered_support_outcomes
        expected_count = len(expected_support) + 1
        if (
            self.discovery_evidence.row_id != self.row_id
            or self.discovery_evidence.support_epoch_index
            != self.support_epoch_index
            or self.discovery_evidence.discovery_stream_domain_id
            == self.validation_stream_domain_id
            or self.support_outcomes != expected_support
            or self.event_count != expected_count
            or not 1 <= self.event_count <= MAX_EVENT_COUNT
            or type(self.per_event_alpha) is not Fraction
            or self.per_event_alpha != ROW_EPOCH_BETA / expected_count
            or self.row_epoch_beta != ROW_EPOCH_BETA
            or self.support_freeze_rule != SUPPORT_FREEZE_RULE
        ):
            raise PartialSupportConfidenceInvariantViolation(
                "initial support epoch is changed, stale, or not split-sample"
            )
        object.__setattr__(
            self,
            "_support_epoch_id",
            _content_id("support_epoch", self._payload()),
        )

    @property
    def support_outcome_ids(self) -> tuple[str, ...]:
        return tuple(item.outcome_id for item in self.support_outcomes)

    @property
    def excluded_probability_sample_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.discovery_evidence.sample_ids))

    @property
    def forbidden_validation_stream_domain_ids(self) -> tuple[str, ...]:
        return (self.discovery_evidence.discovery_stream_domain_id,)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_split_support_epoch.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "row_id": self.row_id,
            "support_epoch_index": self.support_epoch_index,
            "discovery_evidence_id": self.discovery_evidence.discovery_evidence_id,
            "validation_stream_domain_id": self.validation_stream_domain_id,
            "support": [item.to_document() for item in self.support_outcomes],
            "event_count": self.event_count,
            "row_epoch_beta": _fdoc(self.row_epoch_beta),
            "per_event_alpha": _fdoc(self.per_event_alpha),
            "excluded_probability_sample_ids": list(
                self.excluded_probability_sample_ids
            ),
            "forbidden_validation_stream_domain_ids": list(
                self.forbidden_validation_stream_domain_ids
            ),
            "support_freeze_rule": self.support_freeze_rule,
        }

    @property
    def support_epoch_id(self) -> str:
        return self._support_epoch_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "support_epoch_id": self.support_epoch_id}


def freeze_support_epoch_v1(
    *,
    row_id: str,
    support_epoch_index: int,
    discovery_stream_domain_id: str,
    validation_stream_domain_id: str,
    discovery_observations: tuple[SplitSupportObservationV1, ...],
) -> FrozenSupportEpochV1:
    """Freeze ``S`` from discovery before any validation draw is admitted."""

    support = _representative_outcomes(discovery_observations)
    discovery = DiscoverySupportEvidenceV1(
        row_id=row_id,
        support_epoch_index=support_epoch_index,
        discovery_stream_domain_id=discovery_stream_domain_id,
        observations=discovery_observations,
        discovered_support_outcomes=support,
    )
    event_count = len(support) + 1
    return FrozenSupportEpochV1(
        row_id=row_id,
        support_epoch_index=support_epoch_index,
        discovery_evidence=discovery,
        validation_stream_domain_id=validation_stream_domain_id,
        support_outcomes=support,
        event_count=event_count,
        per_event_alpha=ROW_EPOCH_BETA / event_count,
    )


@dataclass(frozen=True, slots=True)
class ValidationEvidenceV1:
    """One fresh ordinal transcript bound to exactly one support epoch."""

    row_id: str
    support_epoch_id: str
    validation_stream_domain_id: str
    selected_checkpoint_draw_count: int
    observations: tuple[SplitSupportObservationV1, ...]
    _validation_evidence_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.row_id, "row")
        _cid(self.support_epoch_id, "support epoch")
        _validate_observation_stream(
            self.observations,
            self.validation_stream_domain_id,
        )
        if (
            type(self.selected_checkpoint_draw_count) is not int
            or self.selected_checkpoint_draw_count <= 0
            or self.selected_checkpoint_draw_count != len(self.observations)
        ):
            raise PartialSupportConfidenceInvariantViolation(
                "validation evidence is not one complete selected checkpoint"
            )
        object.__setattr__(
            self,
            "_validation_evidence_id",
            _content_id("validation", self._payload()),
        )

    @property
    def sample_ids(self) -> tuple[str, ...]:
        return tuple(item.sample_id for item in self.observations)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.split_support_validation_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "row_id": self.row_id,
            "support_epoch_id": self.support_epoch_id,
            "validation_stream_domain_id": self.validation_stream_domain_id,
            "selected_checkpoint_draw_count": (
                self.selected_checkpoint_draw_count
            ),
            "observation_ids": [
                item.observation_id for item in self.observations
            ],
        }

    @property
    def validation_evidence_id(self) -> str:
        return self._validation_evidence_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "validation_evidence_id": self.validation_evidence_id,
        }


@dataclass(frozen=True, slots=True)
class PromotionSupportEvidenceV1:
    """Prior validation outcomes used as support proposals, never as counts."""

    parent_support_epoch_id: str
    parent_support_epoch_index: int
    parent_validation_evidence: ValidationEvidenceV1
    parent_support_outcomes: tuple[OpaqueObservedJointOutcomeV1, ...]
    parent_excluded_probability_sample_ids: tuple[str, ...]
    parent_forbidden_validation_stream_domain_ids: tuple[str, ...]
    parent_novel_outcome_ids: tuple[str, ...]
    novel_proposal_observations: tuple[SplitSupportObservationV1, ...]
    proposed_support_outcomes: tuple[OpaqueObservedJointOutcomeV1, ...]
    excluded_probability_sample_ids: tuple[str, ...]
    forbidden_validation_stream_domain_ids: tuple[str, ...]
    proposal_only: bool = True
    probability_evidence_draw_count: int = 0
    _promotion_evidence_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.parent_support_epoch_id, "parent support epoch")
        if (
            type(self.parent_support_epoch_index) is not int
            or self.parent_support_epoch_index < 1
            or type(self.parent_validation_evidence) is not ValidationEvidenceV1
            or self.parent_validation_evidence.support_epoch_id
            != self.parent_support_epoch_id
            or type(self.parent_support_outcomes) is not tuple
            or type(self.parent_novel_outcome_ids) is not tuple
            or type(self.novel_proposal_observations) is not tuple
            or not self.novel_proposal_observations
            or any(
                type(item) is not OpaqueObservedJointOutcomeV1
                for item in self.parent_support_outcomes
            )
            or any(
                type(item) is not SplitSupportObservationV1
                for item in self.novel_proposal_observations
            )
            or self.proposal_only is not True
            or self.probability_evidence_draw_count != 0
        ):
            raise PartialSupportConfidenceInvariantViolation(
                "promotion evidence is not proposal-only parent validation"
            )

        for item in self.parent_excluded_probability_sample_ids:
            _cid(item, "parent excluded sample")
        for item in self.parent_forbidden_validation_stream_domain_ids:
            _cid(item, "parent forbidden stream domain")
        validation_by_sample = {
            item.sample_id: item
            for item in self.parent_validation_evidence.observations
        }
        proposal_ids = {
            item.outcome.outcome_id for item in self.novel_proposal_observations
        }
        parent_support_ids = {
            item.outcome_id for item in self.parent_support_outcomes
        }
        expected_novel_ids = tuple(
            sorted(
                {
                    item.outcome.outcome_id
                    for item in self.parent_validation_evidence.observations
                    if item.outcome.outcome_id not in parent_support_ids
                }
            )
        )
        if (
            any(
                validation_by_sample.get(item.sample_id) != item
                for item in self.novel_proposal_observations
            )
            or proposal_ids.intersection(parent_support_ids)
            or not proposal_ids.issubset(set(self.parent_novel_outcome_ids))
            or self.parent_novel_outcome_ids != expected_novel_ids
            or tuple(sorted(set(self.parent_excluded_probability_sample_ids)))
            != self.parent_excluded_probability_sample_ids
            or tuple(
                sorted(set(self.parent_forbidden_validation_stream_domain_ids))
            )
            != self.parent_forbidden_validation_stream_domain_ids
        ):
            raise PartialSupportConfidenceInvariantViolation(
                "promotion observations are not novel members of parent validation"
            )

        by_id = {item.outcome_id: item for item in self.parent_support_outcomes}
        for observation in self.novel_proposal_observations:
            by_id.setdefault(observation.outcome.outcome_id, observation.outcome)
        expected_support = tuple(by_id[key] for key in sorted(by_id))
        expected_excluded = tuple(
            sorted(
                set(self.parent_excluded_probability_sample_ids)
                | set(self.parent_validation_evidence.sample_ids)
            )
        )
        expected_forbidden = tuple(
            sorted(
                set(self.parent_forbidden_validation_stream_domain_ids)
                | {
                    self.parent_validation_evidence.validation_stream_domain_id
                }
            )
        )
        if (
            self.proposed_support_outcomes != expected_support
            or len(expected_support) > MAX_DISCOVERED_ATOMS
            or expected_excluded != self.excluded_probability_sample_ids
            or expected_forbidden != self.forbidden_validation_stream_domain_ids
            or tuple(sorted(set(self.excluded_probability_sample_ids)))
            != self.excluded_probability_sample_ids
            or tuple(sorted(set(self.forbidden_validation_stream_domain_ids)))
            != self.forbidden_validation_stream_domain_ids
        ):
            raise PartialSupportConfidenceInvariantViolation(
                "promoted support or no-reuse lineage is incomplete"
            )
        object.__setattr__(
            self,
            "_promotion_evidence_id",
            _content_id("promotion", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.split_support_promotion_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "parent_support_epoch_id": self.parent_support_epoch_id,
            "parent_support_epoch_index": self.parent_support_epoch_index,
            "parent_validation_evidence_id": (
                self.parent_validation_evidence.validation_evidence_id
            ),
            "parent_support": [
                item.to_document() for item in self.parent_support_outcomes
            ],
            "parent_excluded_probability_sample_ids": list(
                self.parent_excluded_probability_sample_ids
            ),
            "parent_forbidden_validation_stream_domain_ids": list(
                self.parent_forbidden_validation_stream_domain_ids
            ),
            "parent_novel_outcome_ids": list(self.parent_novel_outcome_ids),
            "novel_proposal_observation_ids": [
                item.observation_id for item in self.novel_proposal_observations
            ],
            "proposed_support": [
                item.to_document() for item in self.proposed_support_outcomes
            ],
            "excluded_probability_sample_ids": list(
                self.excluded_probability_sample_ids
            ),
            "forbidden_validation_stream_domain_ids": list(
                self.forbidden_validation_stream_domain_ids
            ),
            "proposal_only": True,
            "probability_evidence_draw_count": 0,
            "promotion_rule": PROMOTION_RULE,
        }

    @property
    def promotion_evidence_id(self) -> str:
        return self._promotion_evidence_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "promotion_evidence_id": self.promotion_evidence_id,
        }


@dataclass(frozen=True, slots=True)
class PromotedSupportEpochV1:
    """A new immutable support epoch proposed by prior novel observations."""

    row_id: str
    support_epoch_index: int
    parent_support_epoch_id: str
    promotion_evidence: PromotionSupportEvidenceV1
    validation_stream_domain_id: str
    support_outcomes: tuple[OpaqueObservedJointOutcomeV1, ...]
    event_count: int
    per_event_alpha: Fraction
    row_epoch_beta: Fraction = ROW_EPOCH_BETA
    promotion_rule: str = PROMOTION_RULE
    _support_epoch_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.row_id, "row")
        _cid(self.parent_support_epoch_id, "parent support epoch")
        _cid(self.validation_stream_domain_id, "validation stream domain")
        if type(self.promotion_evidence) is not PromotionSupportEvidenceV1:
            raise PartialSupportConfidenceInvariantViolation(
                "promoted support epoch has invalid promotion evidence"
            )
        expected_support = self.promotion_evidence.proposed_support_outcomes
        expected_count = len(expected_support) + 1
        if (
            self.promotion_evidence.parent_support_epoch_id
            != self.parent_support_epoch_id
            or self.promotion_evidence.parent_validation_evidence.row_id
            != self.row_id
            or type(self.support_epoch_index) is not int
            or self.support_epoch_index
            != self.promotion_evidence.parent_support_epoch_index + 1
            or self.validation_stream_domain_id
            in self.promotion_evidence.forbidden_validation_stream_domain_ids
            or self.support_outcomes != expected_support
            or self.event_count != expected_count
            or not 1 <= self.event_count <= MAX_EVENT_COUNT
            or self.per_event_alpha != ROW_EPOCH_BETA / expected_count
            or self.row_epoch_beta != ROW_EPOCH_BETA
            or self.promotion_rule != PROMOTION_RULE
        ):
            raise PartialSupportConfidenceInvariantViolation(
                "promoted support epoch is stale, changed, or reuses a stream"
            )
        object.__setattr__(
            self,
            "_support_epoch_id",
            _content_id("promoted_epoch", self._payload()),
        )

    @property
    def support_outcome_ids(self) -> tuple[str, ...]:
        return tuple(item.outcome_id for item in self.support_outcomes)

    @property
    def excluded_probability_sample_ids(self) -> tuple[str, ...]:
        return self.promotion_evidence.excluded_probability_sample_ids

    @property
    def forbidden_validation_stream_domain_ids(self) -> tuple[str, ...]:
        return self.promotion_evidence.forbidden_validation_stream_domain_ids

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.promoted_split_support_epoch.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "row_id": self.row_id,
            "support_epoch_index": self.support_epoch_index,
            "parent_support_epoch_id": self.parent_support_epoch_id,
            "promotion_evidence_id": self.promotion_evidence.promotion_evidence_id,
            "validation_stream_domain_id": self.validation_stream_domain_id,
            "support": [item.to_document() for item in self.support_outcomes],
            "event_count": self.event_count,
            "row_epoch_beta": _fdoc(self.row_epoch_beta),
            "per_event_alpha": _fdoc(self.per_event_alpha),
            "excluded_probability_sample_ids": list(
                self.excluded_probability_sample_ids
            ),
            "forbidden_validation_stream_domain_ids": list(
                self.forbidden_validation_stream_domain_ids
            ),
            "promotion_rule": self.promotion_rule,
        }

    @property
    def support_epoch_id(self) -> str:
        return self._support_epoch_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "support_epoch_id": self.support_epoch_id}


SupportEpochV1 = FrozenSupportEpochV1 | PromotedSupportEpochV1


def _require_support_epoch(value: Any) -> SupportEpochV1:
    if type(value) not in (FrozenSupportEpochV1, PromotedSupportEpochV1):
        raise PartialSupportConfidenceInvariantViolation(
            "support epoch has an unsupported concrete type"
        )
    return value


@dataclass(frozen=True, slots=True)
class PartialSupportConfidenceProfileV1:
    """Registered row-level allocation and upstream Ville-CS parameters."""

    row_epoch_beta: Fraction = ROW_EPOCH_BETA
    maximum_discovered_atoms: int = MAX_DISCOVERED_ATOMS
    checkpoints: tuple[int, ...] = DEFAULT_CHECKPOINTS
    target_half_width: Fraction = DEFAULT_TARGET_HALF_WIDTH
    boundary_grid_bits: int = DEFAULT_BOUNDARY_GRID_BITS
    confidence_accounting: str = CONFIDENCE_ACCOUNTING
    other_accounting_rule: str = OTHER_ACCOUNTING_RULE
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self.row_epoch_beta != ROW_EPOCH_BETA
            or self.maximum_discovered_atoms != MAX_DISCOVERED_ATOMS
            or self.checkpoints != DEFAULT_CHECKPOINTS
            or self.target_half_width != DEFAULT_TARGET_HALF_WIDTH
            or self.boundary_grid_bits != DEFAULT_BOUNDARY_GRID_BITS
            or self.confidence_accounting != CONFIDENCE_ACCOUNTING
            or self.other_accounting_rule != OTHER_ACCOUNTING_RULE
        ):
            raise PartialSupportConfidenceInvariantViolation(
                "partial-support confidence profile is not preregistered"
            )
        object.__setattr__(
            self,
            "_profile_id",
            _content_id("profile", self._payload()),
        )

    def sequential_profile(
        self,
        event_count: int,
    ) -> SequentialBernoulliProfileV1:
        if type(event_count) is not int or not 1 <= event_count <= MAX_EVENT_COUNT:
            raise PartialSupportConfidenceInvariantViolation(
                "event count is outside the preregistered support cap"
            )
        return SequentialBernoulliProfileV1(
            confidence_alpha=self.row_epoch_beta / event_count,
            target_half_width=self.target_half_width,
            checkpoints=self.checkpoints,
            boundary_grid_bits=self.boundary_grid_bits,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_confidence_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "row_epoch_beta": _fdoc(self.row_epoch_beta),
            "maximum_discovered_atoms": self.maximum_discovered_atoms,
            "maximum_event_count": MAX_EVENT_COUNT,
            "checkpoints": list(self.checkpoints),
            "target_half_width": _fdoc(self.target_half_width),
            "boundary_grid_bits": self.boundary_grid_bits,
            "confidence_accounting": self.confidence_accounting,
            "other_accounting_rule": self.other_accounting_rule,
        }

    @property
    def profile_id(self) -> str:
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


def v0068_partial_support_confidence_profile_v1(
) -> PartialSupportConfidenceProfileV1:
    return PartialSupportConfidenceProfileV1()


class PartialSupportEventKind(str, Enum):
    DISCOVERED = "DISCOVERED"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class PartialSupportEventIntervalV1:
    support_epoch_id: str
    validation_evidence_id: str
    sequential_profile_id: str
    event_ordinal: int
    event_kind: PartialSupportEventKind
    event_key: str
    success_count: int
    checkpoint: AnytimeBernoulliCheckpointV1
    _event_interval_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.support_epoch_id, "support epoch"),
            (self.validation_evidence_id, "validation evidence"),
            (self.sequential_profile_id, "sequential profile"),
        ):
            _cid(value, field_name)
        if (
            type(self.event_ordinal) is not int
            or self.event_ordinal < 0
            or type(self.event_kind) is not PartialSupportEventKind
            or type(self.event_key) is not str
            or not self.event_key
            or (
                self.event_kind is PartialSupportEventKind.DISCOVERED
                and _cid(self.event_key, "discovered event") != self.event_key
            )
            or (
                self.event_kind is PartialSupportEventKind.OTHER
                and self.event_key != OTHER_EVENT_KEY
            )
            or type(self.success_count) is not int
            or self.success_count < 0
            or type(self.checkpoint) is not AnytimeBernoulliCheckpointV1
            or self.checkpoint.success_count != self.success_count
        ):
            raise PartialSupportConfidenceInvariantViolation(
                "partial-support event interval is inconsistent"
            )
        object.__setattr__(
            self,
            "_event_interval_id",
            _content_id("event_interval", self._payload()),
        )

    @property
    def lower_probability(self) -> Fraction:
        return self.checkpoint.lower_probability

    @property
    def upper_probability(self) -> Fraction:
        return self.checkpoint.upper_probability

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_event_interval.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "support_epoch_id": self.support_epoch_id,
            "validation_evidence_id": self.validation_evidence_id,
            "sequential_profile_id": self.sequential_profile_id,
            "event_ordinal": self.event_ordinal,
            "event_kind": self.event_kind.value,
            "event_key": self.event_key,
            "success_count": self.success_count,
            "checkpoint": self.checkpoint.to_document(),
        }

    @property
    def event_interval_id(self) -> str:
        return self._event_interval_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "event_interval_id": self.event_interval_id}


@dataclass(frozen=True, slots=True)
class PartialSupportJointSimplexV1:
    """Exact interval box intersected with ``sum(p_i) = 1``."""

    support_epoch_id: str
    validation_evidence_id: str
    event_interval_ids: tuple[str, ...]
    lower_probabilities: tuple[Fraction, ...]
    upper_probabilities: tuple[Fraction, ...]
    other_coordinate_ordinal: int
    other_coordinate_count: int = 1
    simplex_total: Fraction = Fraction(1)
    other_accounting_rule: str = OTHER_ACCOUNTING_RULE
    _joint_simplex_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.support_epoch_id, "support epoch")
        _cid(self.validation_evidence_id, "validation evidence")
        count = len(self.event_interval_ids)
        if (
            type(self.event_interval_ids) is not tuple
            or not self.event_interval_ids
            or any(
                _cid(item, "event interval") != item
                for item in self.event_interval_ids
            )
            or len(set(self.event_interval_ids)) != count
            or type(self.lower_probabilities) is not tuple
            or type(self.upper_probabilities) is not tuple
            or len(self.lower_probabilities) != count
            or len(self.upper_probabilities) != count
            or any(type(item) is not Fraction for item in self.lower_probabilities)
            or any(type(item) is not Fraction for item in self.upper_probabilities)
            or any(
                not 0 <= lower <= upper <= 1
                for lower, upper in zip(
                    self.lower_probabilities,
                    self.upper_probabilities,
                )
            )
            or sum(self.lower_probabilities, Fraction(0)) > 1
            or sum(self.upper_probabilities, Fraction(0)) < 1
            or self.other_coordinate_ordinal != count - 1
            or self.other_coordinate_count != 1
            or self.simplex_total != 1
            or self.other_accounting_rule != OTHER_ACCOUNTING_RULE
        ):
            raise PartialSupportConfidenceInvariantViolation(
                "joint interval simplex is infeasible or duplicates OTHER"
            )
        object.__setattr__(
            self,
            "_joint_simplex_id",
            _content_id("simplex", self._payload()),
        )

    @property
    def other_lower_probability(self) -> Fraction:
        return self.lower_probabilities[self.other_coordinate_ordinal]

    @property
    def other_upper_probability(self) -> Fraction:
        return self.upper_probabilities[self.other_coordinate_ordinal]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_joint_simplex.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "support_epoch_id": self.support_epoch_id,
            "validation_evidence_id": self.validation_evidence_id,
            "coordinates": [
                {
                    "event_interval_id": event_id,
                    "lower_probability": _fdoc(lower),
                    "upper_probability": _fdoc(upper),
                }
                for event_id, lower, upper in zip(
                    self.event_interval_ids,
                    self.lower_probabilities,
                    self.upper_probabilities,
                )
            ],
            "simplex_total": _fdoc(self.simplex_total),
            "other_coordinate_ordinal": self.other_coordinate_ordinal,
            "other_coordinate_count": 1,
            "other_accounting_rule": self.other_accounting_rule,
        }

    @property
    def joint_simplex_id(self) -> str:
        return self._joint_simplex_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "joint_simplex_id": self.joint_simplex_id}


@dataclass(frozen=True, slots=True)
class PartialSupportConfidenceAuthorityV1:
    support_epoch: SupportEpochV1
    confidence_profile: PartialSupportConfidenceProfileV1
    validation_evidence: ValidationEvidenceV1
    sequential_profile: SequentialBernoulliProfileV1
    event_intervals: tuple[PartialSupportEventIntervalV1, ...]
    joint_simplex: PartialSupportJointSimplexV1
    novel_outcome_ids: tuple[str, ...]
    row_simultaneous_miscoverage_upper: Fraction = ROW_EPOCH_BETA
    other_event_count: int = 1
    _authority_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _validate_authority_v1(self)
        object.__setattr__(
            self,
            "_authority_id",
            _content_id("authority", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        epoch = _require_support_epoch(self.support_epoch)
        return {
            "schema": "acfqp.partial_support_confidence_authority.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "support_epoch_id": epoch.support_epoch_id,
            "confidence_profile_id": self.confidence_profile.profile_id,
            "validation_evidence_id": (
                self.validation_evidence.validation_evidence_id
            ),
            "sequential_profile_id": self.sequential_profile.profile_id,
            "event_interval_ids": [
                item.event_interval_id for item in self.event_intervals
            ],
            "joint_simplex_id": self.joint_simplex.joint_simplex_id,
            "novel_outcome_ids": list(self.novel_outcome_ids),
            "row_simultaneous_miscoverage_upper": _fdoc(
                self.row_simultaneous_miscoverage_upper
            ),
            "other_event_count": self.other_event_count,
            "confidence_accounting": CONFIDENCE_ACCOUNTING,
            "support_is_immutable_for_this_authority": True,
        }

    @property
    def authority_id(self) -> str:
        return self._authority_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "authority_id": self.authority_id}


def _validate_epoch_and_validation(
    epoch: SupportEpochV1,
    evidence: ValidationEvidenceV1,
    profile: PartialSupportConfidenceProfileV1,
) -> None:
    epoch = _require_support_epoch(epoch)
    if (
        type(evidence) is not ValidationEvidenceV1
        or type(profile) is not PartialSupportConfidenceProfileV1
        or evidence.row_id != epoch.row_id
        or evidence.support_epoch_id != epoch.support_epoch_id
        or evidence.validation_stream_domain_id
        != epoch.validation_stream_domain_id
        or evidence.validation_stream_domain_id
        in epoch.forbidden_validation_stream_domain_ids
        or set(evidence.sample_ids).intersection(
            epoch.excluded_probability_sample_ids
        )
        or evidence.selected_checkpoint_draw_count not in profile.checkpoints
        or epoch.row_epoch_beta != profile.row_epoch_beta
        or epoch.event_count != len(epoch.support_outcomes) + 1
        or epoch.per_event_alpha
        != profile.row_epoch_beta / epoch.event_count
    ):
        raise PartialSupportConfidenceInvariantViolation(
            "validation is reused, stale, or not bound to its frozen support"
        )

    support_documents = {
        item.outcome_id: item._document_bytes for item in epoch.support_outcomes
    }
    for observation in evidence.observations:
        expected = support_documents.get(observation.outcome.outcome_id)
        if expected is not None and expected != observation.outcome._document_bytes:
            raise PartialSupportConfidenceInvariantViolation(
                "validation changed an existing support outcome document"
            )


def _expected_event_counts(
    epoch: SupportEpochV1,
    evidence: ValidationEvidenceV1,
) -> tuple[tuple[int, ...], tuple[str, ...]]:
    support_ids = epoch.support_outcome_ids
    support_set = set(support_ids)
    counts = {item: 0 for item in support_ids}
    other_count = 0
    novel: set[str] = set()
    for observation in evidence.observations:
        outcome_id = observation.outcome.outcome_id
        if outcome_id in support_set:
            counts[outcome_id] += 1
        else:
            other_count += 1
            novel.add(outcome_id)
    return (
        tuple(counts[item] for item in support_ids) + (other_count,),
        tuple(sorted(novel)),
    )


def _build_event_intervals(
    epoch: SupportEpochV1,
    evidence: ValidationEvidenceV1,
    sequential_profile: SequentialBernoulliProfileV1,
) -> tuple[PartialSupportEventIntervalV1, ...]:
    counts, _ = _expected_event_counts(epoch, evidence)
    keys = epoch.support_outcome_ids + (OTHER_EVENT_KEY,)
    return tuple(
        PartialSupportEventIntervalV1(
            support_epoch_id=epoch.support_epoch_id,
            validation_evidence_id=evidence.validation_evidence_id,
            sequential_profile_id=sequential_profile.profile_id,
            event_ordinal=ordinal,
            event_kind=(
                PartialSupportEventKind.OTHER
                if ordinal == len(keys) - 1
                else PartialSupportEventKind.DISCOVERED
            ),
            event_key=key,
            success_count=counts[ordinal],
            checkpoint=build_anytime_bernoulli_checkpoint_v1(
                evidence.selected_checkpoint_draw_count,
                counts[ordinal],
                sequential_profile,
            ),
        )
        for ordinal, key in enumerate(keys)
    )


def _build_joint_simplex(
    epoch: SupportEpochV1,
    evidence: ValidationEvidenceV1,
    events: tuple[PartialSupportEventIntervalV1, ...],
) -> PartialSupportJointSimplexV1:
    return PartialSupportJointSimplexV1(
        support_epoch_id=epoch.support_epoch_id,
        validation_evidence_id=evidence.validation_evidence_id,
        event_interval_ids=tuple(item.event_interval_id for item in events),
        lower_probabilities=tuple(item.lower_probability for item in events),
        upper_probabilities=tuple(item.upper_probability for item in events),
        other_coordinate_ordinal=len(events) - 1,
    )


def _validate_authority_v1(
    authority: PartialSupportConfidenceAuthorityV1,
) -> None:
    epoch = _require_support_epoch(authority.support_epoch)
    if (
        type(authority.confidence_profile)
        is not PartialSupportConfidenceProfileV1
        or type(authority.validation_evidence) is not ValidationEvidenceV1
        or type(authority.sequential_profile) is not SequentialBernoulliProfileV1
        or type(authority.event_intervals) is not tuple
        or type(authority.joint_simplex) is not PartialSupportJointSimplexV1
        or type(authority.novel_outcome_ids) is not tuple
        or authority.row_simultaneous_miscoverage_upper != ROW_EPOCH_BETA
        or authority.other_event_count != 1
    ):
        raise PartialSupportConfidenceInvariantViolation(
            "partial-support authority has an invalid concrete schema"
        )
    _validate_epoch_and_validation(
        epoch,
        authority.validation_evidence,
        authority.confidence_profile,
    )
    expected_profile = authority.confidence_profile.sequential_profile(
        epoch.event_count
    )
    expected_events = _build_event_intervals(
        epoch,
        authority.validation_evidence,
        expected_profile,
    )
    _, expected_novel = _expected_event_counts(
        epoch,
        authority.validation_evidence,
    )
    if (
        authority.sequential_profile != expected_profile
        or authority.sequential_profile.confidence_alpha
        != epoch.per_event_alpha
        or len(authority.event_intervals) != epoch.event_count
        or authority.event_intervals != expected_events
        or sum(
            (item.success_count for item in authority.event_intervals),
            0,
        )
        != authority.validation_evidence.selected_checkpoint_draw_count
        or tuple(
            item.event_kind for item in authority.event_intervals
        ).count(PartialSupportEventKind.OTHER)
        != 1
        or authority.event_intervals[-1].event_key != OTHER_EVENT_KEY
        or authority.novel_outcome_ids != expected_novel
        or epoch.event_count * authority.sequential_profile.confidence_alpha
        != ROW_EPOCH_BETA
    ):
        raise PartialSupportConfidenceInvariantViolation(
            "event intervals, alpha allocation, or OTHER collapse was transplanted"
        )
    expected_simplex = _build_joint_simplex(
        epoch,
        authority.validation_evidence,
        expected_events,
    )
    if authority.joint_simplex != expected_simplex:
        raise PartialSupportConfidenceInvariantViolation(
            "joint simplex does not exactly bind the event intervals"
        )


def build_partial_support_confidence_v1(
    support_epoch: SupportEpochV1,
    validation_observations: tuple[SplitSupportObservationV1, ...],
    confidence_profile: PartialSupportConfidenceProfileV1 | None = None,
) -> PartialSupportConfidenceAuthorityV1:
    """Build the exact joint interval-simplex authority at one checkpoint."""

    epoch = _require_support_epoch(support_epoch)
    profile = (
        v0068_partial_support_confidence_profile_v1()
        if confidence_profile is None
        else confidence_profile
    )
    if type(profile) is not PartialSupportConfidenceProfileV1:
        raise PartialSupportConfidenceInvariantViolation(
            "confidence profile has an unsupported concrete type"
        )
    evidence = ValidationEvidenceV1(
        row_id=epoch.row_id,
        support_epoch_id=epoch.support_epoch_id,
        validation_stream_domain_id=epoch.validation_stream_domain_id,
        selected_checkpoint_draw_count=len(validation_observations),
        observations=validation_observations,
    )
    _validate_epoch_and_validation(epoch, evidence, profile)
    sequential_profile = profile.sequential_profile(epoch.event_count)
    events = _build_event_intervals(epoch, evidence, sequential_profile)
    _, novel = _expected_event_counts(epoch, evidence)
    return PartialSupportConfidenceAuthorityV1(
        support_epoch=epoch,
        confidence_profile=profile,
        validation_evidence=evidence,
        sequential_profile=sequential_profile,
        event_intervals=events,
        joint_simplex=_build_joint_simplex(epoch, evidence, events),
        novel_outcome_ids=novel,
    )


def promote_support_epoch_v1(
    parent_authority: PartialSupportConfidenceAuthorityV1,
    *,
    next_validation_stream_domain_id: str,
    novel_proposal_observations: (
        tuple[SplitSupportObservationV1, ...] | None
    ) = None,
) -> PromotedSupportEpochV1:
    """Promote prior novel identities, while quarantining every old sample."""

    if type(parent_authority) is not PartialSupportConfidenceAuthorityV1:
        raise PartialSupportConfidenceInvariantViolation(
            "promotion requires a verified concrete parent authority"
        )
    verify_partial_support_confidence_v1(parent_authority)
    parent_epoch = _require_support_epoch(parent_authority.support_epoch)
    novel_set = set(parent_authority.novel_outcome_ids)
    proposals = (
        tuple(
            item
            for item in parent_authority.validation_evidence.observations
            if item.outcome.outcome_id in novel_set
        )
        if novel_proposal_observations is None
        else novel_proposal_observations
    )
    by_id = {item.outcome_id: item for item in parent_epoch.support_outcomes}
    for observation in proposals:
        by_id.setdefault(observation.outcome.outcome_id, observation.outcome)
    proposed_support = tuple(by_id[key] for key in sorted(by_id))
    excluded_samples = tuple(
        sorted(
            set(parent_epoch.excluded_probability_sample_ids)
            | set(parent_authority.validation_evidence.sample_ids)
        )
    )
    forbidden_domains = tuple(
        sorted(
            set(parent_epoch.forbidden_validation_stream_domain_ids)
            | {
                parent_authority.validation_evidence.validation_stream_domain_id
            }
        )
    )
    promotion = PromotionSupportEvidenceV1(
        parent_support_epoch_id=parent_epoch.support_epoch_id,
        parent_support_epoch_index=parent_epoch.support_epoch_index,
        parent_validation_evidence=parent_authority.validation_evidence,
        parent_support_outcomes=parent_epoch.support_outcomes,
        parent_excluded_probability_sample_ids=(
            parent_epoch.excluded_probability_sample_ids
        ),
        parent_forbidden_validation_stream_domain_ids=(
            parent_epoch.forbidden_validation_stream_domain_ids
        ),
        parent_novel_outcome_ids=parent_authority.novel_outcome_ids,
        novel_proposal_observations=proposals,
        proposed_support_outcomes=proposed_support,
        excluded_probability_sample_ids=excluded_samples,
        forbidden_validation_stream_domain_ids=forbidden_domains,
    )
    event_count = len(proposed_support) + 1
    return PromotedSupportEpochV1(
        row_id=parent_epoch.row_id,
        support_epoch_index=parent_epoch.support_epoch_index + 1,
        parent_support_epoch_id=parent_epoch.support_epoch_id,
        promotion_evidence=promotion,
        validation_stream_domain_id=next_validation_stream_domain_id,
        support_outcomes=proposed_support,
        event_count=event_count,
        per_event_alpha=ROW_EPOCH_BETA / event_count,
    )


@dataclass(frozen=True, slots=True)
class PartialSupportConfidenceVerificationV1:
    authority_id: str
    support_epoch_id: str
    validation_evidence_id: str
    joint_simplex_id: str
    event_count: int
    per_event_alpha: Fraction
    row_epoch_beta: Fraction
    verification_result: str = "VALID_EXACT_SPLIT_SUPPORT_CONFIDENCE"

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.authority_id, "authority"),
            (self.support_epoch_id, "support epoch"),
            (self.validation_evidence_id, "validation evidence"),
            (self.joint_simplex_id, "joint simplex"),
        ):
            _cid(value, field_name)
        if (
            type(self.event_count) is not int
            or not 1 <= self.event_count <= MAX_EVENT_COUNT
            or type(self.per_event_alpha) is not Fraction
            or self.per_event_alpha != ROW_EPOCH_BETA / self.event_count
            or self.row_epoch_beta != ROW_EPOCH_BETA
            or self.verification_result
            != "VALID_EXACT_SPLIT_SUPPORT_CONFIDENCE"
        ):
            raise PartialSupportConfidenceInvariantViolation(
                "partial-support verification is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_confidence_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "authority_id": self.authority_id,
            "support_epoch_id": self.support_epoch_id,
            "validation_evidence_id": self.validation_evidence_id,
            "joint_simplex_id": self.joint_simplex_id,
            "event_count": self.event_count,
            "per_event_alpha": _fdoc(self.per_event_alpha),
            "row_epoch_beta": _fdoc(self.row_epoch_beta),
            "verification_result": self.verification_result,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_partial_support_confidence_v1(
    authority: PartialSupportConfidenceAuthorityV1,
) -> PartialSupportConfidenceVerificationV1:
    """Rebuild every count, interval, identity binding, and simplex coordinate."""

    if type(authority) is not PartialSupportConfidenceAuthorityV1:
        raise PartialSupportConfidenceInvariantViolation(
            "verification requires a concrete authority"
        )
    _validate_authority_v1(authority)
    rebuilt = build_partial_support_confidence_v1(
        authority.support_epoch,
        authority.validation_evidence.observations,
        authority.confidence_profile,
    )
    if rebuilt != authority or rebuilt.authority_id != authority.authority_id:
        raise PartialSupportConfidenceInvariantViolation(
            "partial-support authority does not survive exact replay"
        )
    epoch = _require_support_epoch(authority.support_epoch)
    return PartialSupportConfidenceVerificationV1(
        authority_id=authority.authority_id,
        support_epoch_id=epoch.support_epoch_id,
        validation_evidence_id=authority.validation_evidence.validation_evidence_id,
        joint_simplex_id=authority.joint_simplex.joint_simplex_id,
        event_count=epoch.event_count,
        per_event_alpha=epoch.per_event_alpha,
        row_epoch_beta=epoch.row_epoch_beta,
    )
