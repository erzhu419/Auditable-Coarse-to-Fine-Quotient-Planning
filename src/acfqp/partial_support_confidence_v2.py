"""V0-072 split-support confidence with exact, replayable lineage.

This module is deliberately isolated from the V0-068 confidence artifacts.
It reuses only the exact ``SequentialBernoulliProfileV1`` and uniform-beta
Ville confidence-sequence mathematics.  Every schema, content domain, support
epoch, observation, and authority in this file is V2-specific, so no V1
content ID can silently acquire a new meaning.

The observation boundary is generic.  A domain-separated synthetic control
can implement :class:`ConfidenceObservationProtocolV2` without opening the
registered held-out target tape.  Registered target observations remain
subject to their separate execution-anchor gate.
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
import acfqp.transfer_guided_acquisition_preregistration_v1 as prereg


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_partial_support_confidence_v2"

ROW_EPOCH_BETA = Fraction(1, 300_000)
MAX_SUPPORT_DESCRIPTORS = 16
OTHER_EVENT_KEY = "OTHER"
TARGET_HALF_WIDTH = Fraction(1, 64)
BOUNDARY_GRID_BITS = 16

COLD_CHECKPOINTS = (2_048,)
DIRECT_CHECKPOINTS = (2_048, 4_096, 8_192, 16_384)
NEW_CHILD_CHECKPOINTS = (8_192,)
PROMOTION_CHECKPOINTS = (2_048,)

MAX_ARM_ROW_EPOCH_AUTHORITIES = 480
ARM_COUNT = 5
MAX_CAMPAIGN_ROW_EPOCH_AUTHORITIES = 2_400
CAMPAIGN_JOINT_TAIL_UPPER = Fraction(1, 125)
CAMPAIGN_CONFIDENCE_LOWER = Fraction(124, 125)

CONFIDENCE_ACCOUNTING = (
    "BONFERRONI_OVER_FROZEN_SUPPORT_PLUS_EXACTLY_ONE_OTHER_"
    "WITH_PER_EVENT_TIME_UNIFORM_VILLE_CS"
)
PROMOTION_RULE = (
    "PARENT_SUPPORT_UNION_ALL_PARENT_VALIDATION_NOVEL_DESCRIPTORS_"
    "NO_FRESH_DISCOVERY_AND_FRESH_VALIDATION_ONLY"
)
CAMPAIGN_PROOF_RULE = "FINITE_UNION_BOUND_NO_INDEPENDENCE_REQUIRED"


class PartialSupportConfidenceV2InvariantViolation(ValueError):
    """A V2 identity, transcript, interval, or confidence claim is invalid."""


DOMAIN_TAGS = {
    "descriptor": "acfqp:v072-confidence-outcome-descriptor:v2",
    "observation": "acfqp:v072-confidence-observation:v2",
    "row": "acfqp:v072-confidence-physical-row-binding:v2",
    "profile": "acfqp:v072-partial-support-confidence-profile:v2",
    "discovery": "acfqp:v072-support-discovery-evidence:v2",
    "initial_epoch": "acfqp:v072-initial-support-confidence-epoch:v2",
    "promotion": "acfqp:v072-support-promotion-evidence:v2",
    "promoted_epoch": "acfqp:v072-promoted-support-confidence-epoch:v2",
    "validation_prefix": "acfqp:v072-validation-prefix:v2",
    "row_epoch": "acfqp:v072-row-confidence-epoch-authority:v2",
    "event": "acfqp:v072-partial-support-event-interval:v2",
    "simplex": "acfqp:v072-partial-support-joint-simplex:v2",
    "snapshot": "acfqp:v072-partial-support-confidence-snapshot:v2",
    "verification": "acfqp:v072-confidence-snapshot-verification:v2",
    "snapshot_series": "acfqp:v072-confidence-checkpoint-series:v2",
    "allocation": "acfqp:v072-campaign-confidence-allocation:v2",
    "allocation_verification": (
        "acfqp:v072-campaign-confidence-allocation-verification:v2"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-072 confidence content domains must be unique")


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        tag = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise PartialSupportConfidenceV2InvariantViolation(str(error)) from error
    return hashlib.sha256(tag + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise PartialSupportConfidenceV2InvariantViolation(
            f"{field_name} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise PartialSupportConfidenceV2InvariantViolation(
            "confidence arithmetic must use exact Fraction"
        )
    return {"numerator": value.numerator, "denominator": value.denominator}


def _preregistration_id() -> str:
    # Confidence/model construction must not rebuild the hidden environment
    # manifest merely to validate the nonauthorizing development identity.
    # The preregistration authority independently guards this literal against
    # its canonical frozen document.
    return prereg.DRAFT_PREREGISTRATION_ID


class ConfidenceObservationLaneV2(str, Enum):
    DISCOVERY = "DISCOVERY"
    VALIDATION = "VALIDATION"


class ConfidenceEpochPurposeV2(str, Enum):
    INITIAL_SHARED_OR_DIRECT = "INITIAL_SHARED_OR_DIRECT"
    NEW_CHILD = "NEW_CHILD"
    PROMOTION = "PROMOTION"


@runtime_checkable
class ConfidenceObservationProtocolV2(Protocol):
    """Generic immutable observation boundary used by synthetic controls."""

    @property
    def preregistration_id(self) -> str: ...

    @property
    def context_id(self) -> str: ...

    @property
    def arm(self) -> str: ...

    @property
    def physical_row_id(self) -> str: ...

    @property
    def support_epoch_chain_id(self) -> str: ...

    @property
    def stream_id(self) -> str: ...

    @property
    def lane(self) -> ConfidenceObservationLaneV2: ...

    @property
    def sequence_index(self) -> int: ...

    @property
    def sample_id(self) -> str: ...

    @property
    def outcome_descriptor_id(self) -> str: ...

    @property
    def outcome_document(self) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True, init=False)
class OpaqueOutcomeDescriptorV2:
    descriptor_id: str
    _document_bytes: bytes = field(repr=False)
    _document_object: dict[str, Any] = field(repr=False, compare=False)
    _binding_id: str = field(init=False, repr=False)

    def __init__(self, descriptor_id: str, document: Mapping[str, Any]) -> None:
        _cid(descriptor_id, "outcome descriptor")
        if not isinstance(document, Mapping):
            raise PartialSupportConfidenceV2InvariantViolation(
                "outcome descriptor document must be a mapping"
            )
        try:
            encoded = canonical_json_bytes(dict(document))
            decoded = loads_canonical_json(encoded)
        except (TypeError, ValueError) as error:
            raise PartialSupportConfidenceV2InvariantViolation(
                f"outcome descriptor document is not canonical: {error}"
            ) from error
        if type(decoded) is not dict:
            raise PartialSupportConfidenceV2InvariantViolation(
                "outcome descriptor document must decode to an object"
            )
        object.__setattr__(self, "descriptor_id", descriptor_id)
        object.__setattr__(self, "_document_bytes", encoded)
        object.__setattr__(self, "_document_object", decoded)
        object.__setattr__(
            self,
            "_binding_id",
            _content_id(
                "descriptor",
                {
                    "schema": "acfqp.v072_outcome_descriptor.v2",
                    "schema_version": SCHEMA_VERSION,
                    "descriptor_id": descriptor_id,
                    "document": decoded,
                },
            ),
        )

    @property
    def binding_id(self) -> str:
        return self._binding_id

    @property
    def document(self) -> Mapping[str, Any]:
        return copy.deepcopy(self._document_object)

    def _trusted_document(self) -> dict[str, Any]:
        return {
            "descriptor_id": self.descriptor_id,
            "binding_id": self.binding_id,
            "document": self._document_object,
        }

    def to_document(self) -> dict[str, Any]:
        return copy.deepcopy(self._trusted_document())


@dataclass(frozen=True, slots=True)
class OpaqueConfidenceObservationV2:
    preregistration_id: str
    context_id: str
    arm: str
    physical_row_id: str
    support_epoch_chain_id: str
    stream_id: str
    lane: ConfidenceObservationLaneV2
    sequence_index: int
    sample_id: str
    outcome: OpaqueOutcomeDescriptorV2
    _observation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.preregistration_id, "observation preregistration"),
            (self.context_id, "observation context"),
            (self.physical_row_id, "observation physical row"),
            (self.support_epoch_chain_id, "observation support epoch chain"),
            (self.stream_id, "observation stream"),
            (self.sample_id, "observation sample"),
        ):
            _cid(value, label)
        if (
            type(self.arm) is not str
            or not self.arm
            or type(self.lane) is not ConfidenceObservationLaneV2
            or type(self.sequence_index) is not int
            or self.sequence_index <= 0
            or type(self.outcome) is not OpaqueOutcomeDescriptorV2
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "confidence observation is malformed"
            )
        object.__setattr__(
            self,
            "_observation_id",
            _content_id("observation", self._payload()),
        )

    @property
    def outcome_descriptor_id(self) -> str:
        return self.outcome.descriptor_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_confidence_observation.v2",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "physical_row_id": self.physical_row_id,
            "support_epoch_chain_id": self.support_epoch_chain_id,
            "stream_id": self.stream_id,
            "lane": self.lane.value,
            "sequence_index": self.sequence_index,
            "sample_id": self.sample_id,
            "outcome": self.outcome._trusted_document(),
        }

    @property
    def observation_id(self) -> str:
        return self._observation_id

    def to_document(self) -> dict[str, Any]:
        return copy.deepcopy({**self._payload(), "observation_id": self.observation_id})


def freeze_confidence_observation_v2(
    observation: ConfidenceObservationProtocolV2 | OpaqueConfidenceObservationV2,
) -> OpaqueConfidenceObservationV2:
    """Copy one protocol observation into the isolated V2 content domain."""

    if type(observation) is OpaqueConfidenceObservationV2:
        return observation
    if not isinstance(observation, ConfidenceObservationProtocolV2):
        raise PartialSupportConfidenceV2InvariantViolation(
            "observation does not implement the V2 confidence protocol"
        )
    return OpaqueConfidenceObservationV2(
        preregistration_id=observation.preregistration_id,
        context_id=observation.context_id,
        arm=observation.arm,
        physical_row_id=observation.physical_row_id,
        support_epoch_chain_id=observation.support_epoch_chain_id,
        stream_id=observation.stream_id,
        lane=observation.lane,
        sequence_index=observation.sequence_index,
        sample_id=observation.sample_id,
        outcome=OpaqueOutcomeDescriptorV2(
            observation.outcome_descriptor_id,
            observation.outcome_document,
        ),
    )


@dataclass(frozen=True, slots=True)
class ConfidencePhysicalRowBindingV2:
    preregistration_id: str
    context_id: str
    arm: str
    physical_row_id: str
    _row_binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.preregistration_id, "row preregistration"),
            (self.context_id, "row context"),
            (self.physical_row_id, "physical row"),
        ):
            _cid(value, label)
        if (
            self.preregistration_id != _preregistration_id()
            or type(self.arm) is not str
            or self.arm not in prereg.ARM_ORDER
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "row binding is outside the frozen V0-072 preregistration"
            )
        object.__setattr__(
            self,
            "_row_binding_id",
            _content_id("row", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_confidence_physical_row_binding.v2",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "physical_row_id": self.physical_row_id,
        }

    @property
    def row_binding_id(self) -> str:
        return self._row_binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "row_binding_id": self.row_binding_id}


@dataclass(frozen=True, slots=True)
class PartialSupportConfidenceProfileV2:
    preregistration_id: str
    row_epoch_beta: Fraction = ROW_EPOCH_BETA
    maximum_support_descriptors: int = MAX_SUPPORT_DESCRIPTORS
    cold_checkpoints: tuple[int, ...] = COLD_CHECKPOINTS
    direct_checkpoints: tuple[int, ...] = DIRECT_CHECKPOINTS
    new_child_checkpoints: tuple[int, ...] = NEW_CHILD_CHECKPOINTS
    promotion_checkpoints: tuple[int, ...] = PROMOTION_CHECKPOINTS
    target_half_width: Fraction = TARGET_HALF_WIDTH
    boundary_grid_bits: int = BOUNDARY_GRID_BITS
    confidence_accounting: str = CONFIDENCE_ACCOUNTING
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            _cid(self.preregistration_id, "confidence preregistration")
            != _preregistration_id()
            or self.row_epoch_beta != ROW_EPOCH_BETA
            or self.maximum_support_descriptors != MAX_SUPPORT_DESCRIPTORS
            or self.cold_checkpoints != COLD_CHECKPOINTS
            or self.direct_checkpoints != DIRECT_CHECKPOINTS
            or self.new_child_checkpoints != NEW_CHILD_CHECKPOINTS
            or self.promotion_checkpoints != PROMOTION_CHECKPOINTS
            or self.target_half_width != TARGET_HALF_WIDTH
            or self.boundary_grid_bits != BOUNDARY_GRID_BITS
            or self.confidence_accounting != CONFIDENCE_ACCOUNTING
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "V0-072 confidence profile differs from preregistration"
            )
        object.__setattr__(
            self,
            "_profile_id",
            _content_id("profile", self._payload()),
        )

    def checkpoints_for(
        self, purpose: ConfidenceEpochPurposeV2
    ) -> tuple[int, ...]:
        if purpose is ConfidenceEpochPurposeV2.INITIAL_SHARED_OR_DIRECT:
            return self.direct_checkpoints
        if purpose is ConfidenceEpochPurposeV2.NEW_CHILD:
            return self.new_child_checkpoints
        if purpose is ConfidenceEpochPurposeV2.PROMOTION:
            return self.promotion_checkpoints
        raise PartialSupportConfidenceV2InvariantViolation(
            "confidence epoch purpose is unsupported"
        )

    def sequential_profile(
        self,
        event_count: int,
        purpose: ConfidenceEpochPurposeV2,
    ) -> SequentialBernoulliProfileV1:
        if (
            type(event_count) is not int
            or not 1 <= event_count <= MAX_SUPPORT_DESCRIPTORS + 1
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "event count exceeds support plus one OTHER"
            )
        return SequentialBernoulliProfileV1(
            confidence_alpha=self.row_epoch_beta / event_count,
            target_half_width=self.target_half_width,
            checkpoints=self.checkpoints_for(purpose),
            boundary_grid_bits=self.boundary_grid_bits,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_partial_support_confidence_profile.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": self.preregistration_id,
            "row_epoch_beta": _fdoc(self.row_epoch_beta),
            "maximum_support_descriptors": self.maximum_support_descriptors,
            "maximum_event_count": self.maximum_support_descriptors + 1,
            "cold_checkpoints": list(self.cold_checkpoints),
            "direct_checkpoints": list(self.direct_checkpoints),
            "new_child_checkpoints": list(self.new_child_checkpoints),
            "promotion_checkpoints": list(self.promotion_checkpoints),
            "target_half_width": _fdoc(self.target_half_width),
            "boundary_grid_bits": self.boundary_grid_bits,
            "confidence_accounting": self.confidence_accounting,
            "checkpoint_alpha_spending": False,
        }

    @property
    def profile_id(self) -> str:
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


def v0072_partial_support_confidence_profile_v2(
) -> PartialSupportConfidenceProfileV2:
    return PartialSupportConfidenceProfileV2(_preregistration_id())


def _freeze_observations(
    observations: tuple[
        ConfidenceObservationProtocolV2 | OpaqueConfidenceObservationV2, ...
    ],
) -> tuple[OpaqueConfidenceObservationV2, ...]:
    if type(observations) is not tuple:
        raise PartialSupportConfidenceV2InvariantViolation(
            "observation transcript must be a tuple"
        )
    return tuple(freeze_confidence_observation_v2(item) for item in observations)


def _validate_bound_prefix(
    observations: tuple[OpaqueConfidenceObservationV2, ...],
    row_binding: ConfidencePhysicalRowBindingV2,
    *,
    support_epoch_chain_id: str,
    stream_id: str,
    lane: ConfidenceObservationLaneV2,
) -> None:
    _cid(support_epoch_chain_id, "support epoch chain")
    _cid(stream_id, "observation stream")
    if (
        not observations
        or any(type(item) is not OpaqueConfidenceObservationV2 for item in observations)
        or tuple(item.sequence_index for item in observations)
        != tuple(range(1, len(observations) + 1))
        or len({item.sample_id for item in observations}) != len(observations)
        or any(
            item.preregistration_id != row_binding.preregistration_id
            or item.context_id != row_binding.context_id
            or item.arm != row_binding.arm
            or item.physical_row_id != row_binding.physical_row_id
            or item.support_epoch_chain_id != support_epoch_chain_id
            or item.stream_id != stream_id
            or item.lane is not lane
            for item in observations
        )
    ):
        raise PartialSupportConfidenceV2InvariantViolation(
            "observation prefix has a gap, reorder, duplicate, or identity transplant"
        )
    descriptor_documents: dict[str, bytes] = {}
    for item in observations:
        previous = descriptor_documents.setdefault(
            item.outcome.descriptor_id,
            item.outcome._document_bytes,
        )
        if previous != item.outcome._document_bytes:
            raise PartialSupportConfidenceV2InvariantViolation(
                "one descriptor ID is bound to different documents"
            )


def _representative_descriptors(
    observations: tuple[OpaqueConfidenceObservationV2, ...],
) -> tuple[OpaqueOutcomeDescriptorV2, ...]:
    by_id: dict[str, OpaqueOutcomeDescriptorV2] = {}
    for item in observations:
        prior = by_id.setdefault(item.outcome.descriptor_id, item.outcome)
        if prior._document_bytes != item.outcome._document_bytes:
            raise PartialSupportConfidenceV2InvariantViolation(
                "one descriptor ID is bound to different documents"
            )
    return tuple(by_id[key] for key in sorted(by_id))


@dataclass(frozen=True, slots=True)
class DiscoveryProposalEvidenceV2:
    row_binding: ConfidencePhysicalRowBindingV2
    discovery_support_epoch_chain_id: str
    discovery_stream_id: str
    observations: tuple[OpaqueConfidenceObservationV2, ...]
    proposed_support: tuple[OpaqueOutcomeDescriptorV2, ...]
    support_selection_only: bool = True
    probability_evidence_draw_count: int = 0
    _evidence_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.row_binding) is not ConfidencePhysicalRowBindingV2:
            raise PartialSupportConfidenceV2InvariantViolation(
                "discovery requires a concrete physical-row binding"
            )
        _validate_bound_prefix(
            self.observations,
            self.row_binding,
            support_epoch_chain_id=self.discovery_support_epoch_chain_id,
            stream_id=self.discovery_stream_id,
            lane=ConfidenceObservationLaneV2.DISCOVERY,
        )
        expected = _representative_descriptors(self.observations)
        if (
            self.proposed_support != expected
            or not 1 <= len(expected) <= MAX_SUPPORT_DESCRIPTORS
            or self.support_selection_only is not True
            or self.probability_evidence_draw_count != 0
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "discovery must be bounded proposal-only support evidence"
            )
        object.__setattr__(
            self,
            "_evidence_id",
            _content_id("discovery", self._payload()),
        )

    @property
    def sample_ids(self) -> tuple[str, ...]:
        return tuple(item.sample_id for item in self.observations)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_support_discovery_evidence.v2",
            "schema_version": SCHEMA_VERSION,
            "row_binding_id": self.row_binding.row_binding_id,
            "discovery_support_epoch_chain_id": (
                self.discovery_support_epoch_chain_id
            ),
            "discovery_stream_id": self.discovery_stream_id,
            "observation_ids": [item.observation_id for item in self.observations],
            "proposed_support": [item.to_document() for item in self.proposed_support],
            "support_selection_only": True,
            "probability_evidence_draw_count": 0,
        }

    @property
    def evidence_id(self) -> str:
        return self._evidence_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class InitialSupportEpochV2:
    row_binding: ConfidencePhysicalRowBindingV2
    profile_id: str
    epoch_index: int
    purpose: ConfidenceEpochPurposeV2
    support_epoch_chain_id: str
    validation_stream_id: str
    discovery_evidence: DiscoveryProposalEvidenceV2
    support_descriptors: tuple[OpaqueOutcomeDescriptorV2, ...]
    excluded_probability_sample_ids: tuple[str, ...]
    forbidden_validation_stream_ids: tuple[str, ...]
    _support_epoch_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.row_binding) is not ConfidencePhysicalRowBindingV2
            or _cid(self.profile_id, "confidence profile") != (
                v0072_partial_support_confidence_profile_v2().profile_id
            )
            or self.epoch_index != 1
            or self.purpose not in (
                ConfidenceEpochPurposeV2.INITIAL_SHARED_OR_DIRECT,
                ConfidenceEpochPurposeV2.NEW_CHILD,
            )
            or type(self.discovery_evidence) is not DiscoveryProposalEvidenceV2
            or self.discovery_evidence.row_binding != self.row_binding
            or self.support_descriptors != self.discovery_evidence.proposed_support
            or self.excluded_probability_sample_ids
            != tuple(sorted(self.discovery_evidence.sample_ids))
            or self.forbidden_validation_stream_ids
            != (self.discovery_evidence.discovery_stream_id,)
            or self.validation_stream_id in self.forbidden_validation_stream_ids
            or self.support_epoch_chain_id
            == self.discovery_evidence.discovery_support_epoch_chain_id
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "initial support epoch is stale, reused, or not preregistered"
            )
        _cid(self.support_epoch_chain_id, "initial validation support chain")
        _cid(self.validation_stream_id, "initial validation stream")
        object.__setattr__(
            self,
            "_support_epoch_id",
            _content_id("initial_epoch", self._payload()),
        )

    @property
    def support_descriptor_ids(self) -> tuple[str, ...]:
        return tuple(item.descriptor_id for item in self.support_descriptors)

    @property
    def event_count(self) -> int:
        return len(self.support_descriptors) + 1

    @property
    def support_epoch_id(self) -> str:
        return self._support_epoch_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_initial_support_confidence_epoch.v2",
            "schema_version": SCHEMA_VERSION,
            "row_binding_id": self.row_binding.row_binding_id,
            "profile_id": self.profile_id,
            "epoch_index": self.epoch_index,
            "purpose": self.purpose.value,
            "support_epoch_chain_id": self.support_epoch_chain_id,
            "validation_stream_id": self.validation_stream_id,
            "discovery_evidence_id": self.discovery_evidence.evidence_id,
            "support": [item.to_document() for item in self.support_descriptors],
            "event_count": self.event_count,
            "other_event_count": 1,
            "excluded_probability_sample_ids": list(
                self.excluded_probability_sample_ids
            ),
            "forbidden_validation_stream_ids": list(
                self.forbidden_validation_stream_ids
            ),
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "support_epoch_id": self.support_epoch_id}


def freeze_initial_support_epoch_v2(
    *,
    row_binding: ConfidencePhysicalRowBindingV2,
    purpose: ConfidenceEpochPurposeV2,
    discovery_support_epoch_chain_id: str,
    discovery_stream_id: str,
    discovery_observations: tuple[
        ConfidenceObservationProtocolV2 | OpaqueConfidenceObservationV2, ...
    ],
    validation_support_epoch_chain_id: str,
    validation_stream_id: str,
    profile: PartialSupportConfidenceProfileV2 | None = None,
) -> InitialSupportEpochV2:
    canonical_profile = (
        v0072_partial_support_confidence_profile_v2()
        if profile is None
        else profile
    )
    if type(canonical_profile) is not PartialSupportConfidenceProfileV2:
        raise PartialSupportConfidenceV2InvariantViolation(
            "initial support requires the concrete V2 profile"
        )
    observations = _freeze_observations(discovery_observations)
    discovery = DiscoveryProposalEvidenceV2(
        row_binding,
        discovery_support_epoch_chain_id,
        discovery_stream_id,
        observations,
        _representative_descriptors(observations),
    )
    return InitialSupportEpochV2(
        row_binding=row_binding,
        profile_id=canonical_profile.profile_id,
        epoch_index=1,
        purpose=purpose,
        support_epoch_chain_id=validation_support_epoch_chain_id,
        validation_stream_id=validation_stream_id,
        discovery_evidence=discovery,
        support_descriptors=discovery.proposed_support,
        excluded_probability_sample_ids=tuple(sorted(discovery.sample_ids)),
        forbidden_validation_stream_ids=(discovery_stream_id,),
    )


@dataclass(frozen=True, slots=True)
class ValidationPrefixV2:
    row_binding_id: str
    support_epoch_id: str
    support_epoch_chain_id: str
    validation_stream_id: str
    selected_checkpoint_draw_count: int
    observations: tuple[OpaqueConfidenceObservationV2, ...]
    _prefix_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.row_binding_id, "validation row binding"),
            (self.support_epoch_id, "validation support epoch"),
            (self.support_epoch_chain_id, "validation support chain"),
            (self.validation_stream_id, "validation stream"),
        ):
            _cid(value, label)
        if (
            type(self.selected_checkpoint_draw_count) is not int
            or self.selected_checkpoint_draw_count <= 0
            or self.selected_checkpoint_draw_count != len(self.observations)
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "validation prefix is not one complete checkpoint"
            )
        object.__setattr__(
            self,
            "_prefix_id",
            _content_id("validation_prefix", self._payload()),
        )

    @property
    def sample_ids(self) -> tuple[str, ...]:
        return tuple(item.sample_id for item in self.observations)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_validation_prefix.v2",
            "schema_version": SCHEMA_VERSION,
            "row_binding_id": self.row_binding_id,
            "support_epoch_id": self.support_epoch_id,
            "support_epoch_chain_id": self.support_epoch_chain_id,
            "validation_stream_id": self.validation_stream_id,
            "selected_checkpoint_draw_count": self.selected_checkpoint_draw_count,
            "observation_ids": [item.observation_id for item in self.observations],
            "immutable_prefix": True,
        }

    @property
    def prefix_id(self) -> str:
        return self._prefix_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "prefix_id": self.prefix_id}


class PartialSupportEventKindV2(str, Enum):
    SUPPORT = "SUPPORT"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class PartialSupportEventIntervalV2:
    support_epoch_id: str
    validation_prefix_id: str
    sequential_profile_id: str
    event_ordinal: int
    event_kind: PartialSupportEventKindV2
    event_key: str
    success_count: int
    checkpoint: AnytimeBernoulliCheckpointV1
    _event_interval_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.support_epoch_id, "event support epoch"),
            (self.validation_prefix_id, "event validation prefix"),
            (self.sequential_profile_id, "event sequential profile"),
        ):
            _cid(value, label)
        if (
            type(self.event_ordinal) is not int
            or self.event_ordinal < 0
            or type(self.event_kind) is not PartialSupportEventKindV2
            or type(self.event_key) is not str
            or not self.event_key
            or (
                self.event_kind is PartialSupportEventKindV2.SUPPORT
                and _cid(self.event_key, "support event key") != self.event_key
            )
            or (
                self.event_kind is PartialSupportEventKindV2.OTHER
                and self.event_key != OTHER_EVENT_KEY
            )
            or type(self.success_count) is not int
            or self.success_count < 0
            or type(self.checkpoint) is not AnytimeBernoulliCheckpointV1
            or self.checkpoint.success_count != self.success_count
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "event interval is malformed or does not bind its checkpoint"
            )
        object.__setattr__(
            self,
            "_event_interval_id",
            _content_id("event", self._payload()),
        )

    @property
    def lower_probability(self) -> Fraction:
        return self.checkpoint.lower_probability

    @property
    def upper_probability(self) -> Fraction:
        return self.checkpoint.upper_probability

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_partial_support_event_interval.v2",
            "schema_version": SCHEMA_VERSION,
            "support_epoch_id": self.support_epoch_id,
            "validation_prefix_id": self.validation_prefix_id,
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
class PartialSupportJointSimplexV2:
    support_epoch_id: str
    validation_prefix_id: str
    event_interval_ids: tuple[str, ...]
    lower_probabilities: tuple[Fraction, ...]
    upper_probabilities: tuple[Fraction, ...]
    other_coordinate_ordinal: int
    other_coordinate_count: int = 1
    simplex_total: Fraction = Fraction(1)
    _simplex_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.support_epoch_id, "simplex support epoch")
        _cid(self.validation_prefix_id, "simplex validation prefix")
        count = len(self.event_interval_ids)
        if (
            count <= 0
            or any(_cid(item, "simplex event") != item for item in self.event_interval_ids)
            or len(set(self.event_interval_ids)) != count
            or len(self.lower_probabilities) != count
            or len(self.upper_probabilities) != count
            or any(type(item) is not Fraction for item in self.lower_probabilities)
            or any(type(item) is not Fraction for item in self.upper_probabilities)
            or any(
                not 0 <= lower <= upper <= 1
                for lower, upper in zip(
                    self.lower_probabilities, self.upper_probabilities
                )
            )
            or sum(self.lower_probabilities, Fraction()) > 1
            or sum(self.upper_probabilities, Fraction()) < 1
            or self.other_coordinate_ordinal != count - 1
            or self.other_coordinate_count != 1
            or self.simplex_total != 1
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "joint simplex is infeasible, tampered, or lacks exactly one OTHER"
            )
        object.__setattr__(
            self,
            "_simplex_id",
            _content_id("simplex", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_partial_support_joint_simplex.v2",
            "schema_version": SCHEMA_VERSION,
            "support_epoch_id": self.support_epoch_id,
            "validation_prefix_id": self.validation_prefix_id,
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
            "other_coordinate_ordinal": self.other_coordinate_ordinal,
            "other_coordinate_count": 1,
            "simplex_total": _fdoc(self.simplex_total),
        }

    @property
    def simplex_id(self) -> str:
        return self._simplex_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "simplex_id": self.simplex_id}


@dataclass(frozen=True, slots=True)
class PromotionEvidenceV2:
    parent_snapshot_id: str
    parent_support_epoch_id: str
    parent_validation_prefix_id: str
    parent_support_descriptor_ids: tuple[str, ...]
    parent_novel_descriptor_ids: tuple[str, ...]
    promoted_support_descriptor_ids: tuple[str, ...]
    excluded_probability_sample_ids: tuple[str, ...]
    forbidden_validation_stream_ids: tuple[str, ...]
    fresh_discovery_draw_count: int = 0
    promotion_rule: str = PROMOTION_RULE
    _evidence_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.parent_snapshot_id, "promotion parent snapshot"),
            (self.parent_support_epoch_id, "promotion parent support epoch"),
            (self.parent_validation_prefix_id, "promotion parent prefix"),
        ):
            _cid(value, label)
        for sequence, label in (
            (self.parent_support_descriptor_ids, "parent support descriptors"),
            (self.parent_novel_descriptor_ids, "parent novel descriptors"),
            (self.promoted_support_descriptor_ids, "promoted support descriptors"),
            (self.excluded_probability_sample_ids, "excluded samples"),
            (self.forbidden_validation_stream_ids, "forbidden streams"),
        ):
            if tuple(sorted(set(sequence))) != sequence:
                raise PartialSupportConfidenceV2InvariantViolation(
                    f"{label} must be content-ID sorted and unique"
                )
            for value in sequence:
                _cid(value, label)
        expected = tuple(
            sorted(
                set(self.parent_support_descriptor_ids)
                | set(self.parent_novel_descriptor_ids)
            )
        )
        if (
            not self.parent_novel_descriptor_ids
            or self.promoted_support_descriptor_ids != expected
            or len(expected) > MAX_SUPPORT_DESCRIPTORS
            or self.fresh_discovery_draw_count != 0
            or self.promotion_rule != PROMOTION_RULE
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "promotion omitted a novel descriptor or performed fresh discovery"
            )
        object.__setattr__(
            self,
            "_evidence_id",
            _content_id("promotion", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_support_promotion_evidence.v2",
            "schema_version": SCHEMA_VERSION,
            "parent_snapshot_id": self.parent_snapshot_id,
            "parent_support_epoch_id": self.parent_support_epoch_id,
            "parent_validation_prefix_id": self.parent_validation_prefix_id,
            "parent_support_descriptor_ids": list(self.parent_support_descriptor_ids),
            "parent_novel_descriptor_ids": list(self.parent_novel_descriptor_ids),
            "promoted_support_descriptor_ids": list(
                self.promoted_support_descriptor_ids
            ),
            "excluded_probability_sample_ids": list(
                self.excluded_probability_sample_ids
            ),
            "forbidden_validation_stream_ids": list(
                self.forbidden_validation_stream_ids
            ),
            "fresh_discovery_draw_count": 0,
            "promotion_rule": self.promotion_rule,
        }

    @property
    def evidence_id(self) -> str:
        return self._evidence_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class PromotedSupportEpochV2:
    row_binding: ConfidencePhysicalRowBindingV2
    profile_id: str
    epoch_index: int
    purpose: ConfidenceEpochPurposeV2
    support_epoch_chain_id: str
    validation_stream_id: str
    parent_snapshot: "PartialSupportConfidenceSnapshotV2"
    promotion_evidence: PromotionEvidenceV2
    support_descriptors: tuple[OpaqueOutcomeDescriptorV2, ...]
    excluded_probability_sample_ids: tuple[str, ...]
    forbidden_validation_stream_ids: tuple[str, ...]
    _support_epoch_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        parent = self.parent_snapshot
        if type(parent) is not PartialSupportConfidenceSnapshotV2:
            raise PartialSupportConfidenceV2InvariantViolation(
                "promotion requires a concrete parent confidence snapshot"
            )
        parent_epoch = _require_support_epoch(parent.support_epoch)
        by_id = {
            item.descriptor_id: item for item in parent_epoch.support_descriptors
        }
        for item in parent.novel_descriptors:
            by_id[item.descriptor_id] = item
        expected_support = tuple(by_id[key] for key in sorted(by_id))
        expected_excluded = tuple(
            sorted(
                set(parent_epoch.excluded_probability_sample_ids)
                | set(parent.validation_prefix.sample_ids)
            )
        )
        expected_forbidden = tuple(
            sorted(
                set(parent_epoch.forbidden_validation_stream_ids)
                | {parent_epoch.validation_stream_id}
            )
        )
        if (
            self.row_binding != parent_epoch.row_binding
            or self.profile_id != parent_epoch.profile_id
            or self.epoch_index != parent_epoch.epoch_index + 1
            or self.purpose is not ConfidenceEpochPurposeV2.PROMOTION
            or self.support_epoch_chain_id == parent_epoch.support_epoch_chain_id
            or self.validation_stream_id in expected_forbidden
            or self.support_descriptors != expected_support
            or self.excluded_probability_sample_ids != expected_excluded
            or self.forbidden_validation_stream_ids != expected_forbidden
            or self.promotion_evidence.parent_snapshot_id != parent.snapshot_id
            or self.promotion_evidence.parent_support_epoch_id
            != parent_epoch.support_epoch_id
            or self.promotion_evidence.parent_validation_prefix_id
            != parent.validation_prefix.prefix_id
            or self.promotion_evidence.parent_support_descriptor_ids
            != tuple(sorted(parent_epoch.support_descriptor_ids))
            or self.promotion_evidence.parent_novel_descriptor_ids
            != tuple(sorted(parent.novel_descriptor_ids))
            or self.promotion_evidence.promoted_support_descriptor_ids
            != tuple(item.descriptor_id for item in expected_support)
            or self.promotion_evidence.excluded_probability_sample_ids
            != expected_excluded
            or self.promotion_evidence.forbidden_validation_stream_ids
            != expected_forbidden
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "promoted epoch lineage is partial, stale, or reuses old evidence"
            )
        _cid(self.support_epoch_chain_id, "promoted support chain")
        _cid(self.validation_stream_id, "promoted validation stream")
        object.__setattr__(
            self,
            "_support_epoch_id",
            _content_id("promoted_epoch", self._payload()),
        )

    @property
    def support_descriptor_ids(self) -> tuple[str, ...]:
        return tuple(item.descriptor_id for item in self.support_descriptors)

    @property
    def event_count(self) -> int:
        return len(self.support_descriptors) + 1

    @property
    def support_epoch_id(self) -> str:
        return self._support_epoch_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_promoted_support_confidence_epoch.v2",
            "schema_version": SCHEMA_VERSION,
            "row_binding_id": self.row_binding.row_binding_id,
            "profile_id": self.profile_id,
            "epoch_index": self.epoch_index,
            "purpose": self.purpose.value,
            "support_epoch_chain_id": self.support_epoch_chain_id,
            "validation_stream_id": self.validation_stream_id,
            "parent_snapshot_id": self.parent_snapshot.snapshot_id,
            "promotion_evidence_id": self.promotion_evidence.evidence_id,
            "support": [item.to_document() for item in self.support_descriptors],
            "event_count": self.event_count,
            "other_event_count": 1,
            "excluded_probability_sample_ids": list(
                self.excluded_probability_sample_ids
            ),
            "forbidden_validation_stream_ids": list(
                self.forbidden_validation_stream_ids
            ),
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "support_epoch_id": self.support_epoch_id}


SupportEpochV2 = InitialSupportEpochV2 | PromotedSupportEpochV2


def _require_support_epoch(value: Any) -> SupportEpochV2:
    if type(value) not in (InitialSupportEpochV2, PromotedSupportEpochV2):
        raise PartialSupportConfidenceV2InvariantViolation(
            "support epoch has an unsupported concrete V2 type"
        )
    return value


def _validate_epoch_and_prefix(
    epoch: SupportEpochV2,
    prefix: ValidationPrefixV2,
    profile: PartialSupportConfidenceProfileV2,
) -> None:
    epoch = _require_support_epoch(epoch)
    if (
        type(prefix) is not ValidationPrefixV2
        or type(profile) is not PartialSupportConfidenceProfileV2
        or epoch.profile_id != profile.profile_id
        or prefix.row_binding_id != epoch.row_binding.row_binding_id
        or prefix.support_epoch_id != epoch.support_epoch_id
        or prefix.support_epoch_chain_id != epoch.support_epoch_chain_id
        or prefix.validation_stream_id != epoch.validation_stream_id
        or prefix.validation_stream_id in epoch.forbidden_validation_stream_ids
        or set(prefix.sample_ids).intersection(
            epoch.excluded_probability_sample_ids
        )
        or prefix.selected_checkpoint_draw_count
        not in profile.checkpoints_for(epoch.purpose)
        or not 1 <= len(epoch.support_descriptors) <= MAX_SUPPORT_DESCRIPTORS
    ):
        raise PartialSupportConfidenceV2InvariantViolation(
            "validation prefix is stale, reused, or outside its registered checkpoint"
        )
    _validate_bound_prefix(
        prefix.observations,
        epoch.row_binding,
        support_epoch_chain_id=epoch.support_epoch_chain_id,
        stream_id=epoch.validation_stream_id,
        lane=ConfidenceObservationLaneV2.VALIDATION,
    )
    known_documents = {
        item.descriptor_id: item._document_bytes
        for item in epoch.support_descriptors
    }
    for observation in prefix.observations:
        expected = known_documents.get(observation.outcome.descriptor_id)
        if expected is not None and expected != observation.outcome._document_bytes:
            raise PartialSupportConfidenceV2InvariantViolation(
                "validation changed a frozen support descriptor document"
            )


def _counts_and_novel(
    epoch: SupportEpochV2,
    observations: tuple[OpaqueConfidenceObservationV2, ...],
) -> tuple[tuple[int, ...], tuple[OpaqueOutcomeDescriptorV2, ...]]:
    support_ids = epoch.support_descriptor_ids
    support_set = set(support_ids)
    counts = {key: 0 for key in support_ids}
    novel_by_id: dict[str, OpaqueOutcomeDescriptorV2] = {}
    other = 0
    for observation in observations:
        key = observation.outcome.descriptor_id
        if key in support_set:
            counts[key] += 1
        else:
            other += 1
            prior = novel_by_id.setdefault(key, observation.outcome)
            if prior._document_bytes != observation.outcome._document_bytes:
                raise PartialSupportConfidenceV2InvariantViolation(
                    "novel descriptor changed within validation"
                )
    return (
        tuple(counts[key] for key in support_ids) + (other,),
        tuple(novel_by_id[key] for key in sorted(novel_by_id)),
    )


def _expected_events(
    epoch: SupportEpochV2,
    prefix: ValidationPrefixV2,
    sequential_profile: SequentialBernoulliProfileV1,
) -> tuple[PartialSupportEventIntervalV2, ...]:
    counts, _ = _counts_and_novel(epoch, prefix.observations)
    keys = epoch.support_descriptor_ids + (OTHER_EVENT_KEY,)
    return tuple(
        PartialSupportEventIntervalV2(
            support_epoch_id=epoch.support_epoch_id,
            validation_prefix_id=prefix.prefix_id,
            sequential_profile_id=sequential_profile.profile_id,
            event_ordinal=ordinal,
            event_kind=(
                PartialSupportEventKindV2.OTHER
                if ordinal == len(keys) - 1
                else PartialSupportEventKindV2.SUPPORT
            ),
            event_key=key,
            success_count=counts[ordinal],
            checkpoint=build_anytime_bernoulli_checkpoint_v1(
                prefix.selected_checkpoint_draw_count,
                counts[ordinal],
                sequential_profile,
            ),
        )
        for ordinal, key in enumerate(keys)
    )


def _expected_simplex(
    epoch: SupportEpochV2,
    prefix: ValidationPrefixV2,
    events: tuple[PartialSupportEventIntervalV2, ...],
) -> PartialSupportJointSimplexV2:
    return PartialSupportJointSimplexV2(
        support_epoch_id=epoch.support_epoch_id,
        validation_prefix_id=prefix.prefix_id,
        event_interval_ids=tuple(item.event_interval_id for item in events),
        lower_probabilities=tuple(item.lower_probability for item in events),
        upper_probabilities=tuple(item.upper_probability for item in events),
        other_coordinate_ordinal=len(events) - 1,
    )


def _row_confidence_epoch_id(
    epoch: SupportEpochV2,
    profile: PartialSupportConfidenceProfileV2,
) -> str:
    return _content_id(
        "row_epoch",
        {
            "schema": "acfqp.v072_row_confidence_epoch_authority.v2",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": profile.preregistration_id,
            "profile_id": profile.profile_id,
            "row_binding_id": epoch.row_binding.row_binding_id,
            "support_epoch_id": epoch.support_epoch_id,
            "support_epoch_chain_id": epoch.support_epoch_chain_id,
            "epoch_index": epoch.epoch_index,
            "purpose": epoch.purpose.value,
            "row_epoch_beta": _fdoc(profile.row_epoch_beta),
            "checkpoint_snapshots_share_this_authority": True,
        },
    )


@dataclass(frozen=True, slots=True)
class PartialSupportConfidenceSnapshotV2:
    support_epoch: SupportEpochV2
    profile: PartialSupportConfidenceProfileV2
    validation_prefix: ValidationPrefixV2
    sequential_profile: SequentialBernoulliProfileV1
    event_intervals: tuple[PartialSupportEventIntervalV2, ...]
    joint_simplex: PartialSupportJointSimplexV2
    novel_descriptors: tuple[OpaqueOutcomeDescriptorV2, ...]
    row_confidence_epoch_id: str
    row_epoch_beta: Fraction = ROW_EPOCH_BETA
    per_event_alpha: Fraction = Fraction(0)
    other_event_count: int = 1
    checkpoint_consumes_additional_row_epoch_authority: bool = False
    _snapshot_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _validate_snapshot_structure(self)
        object.__setattr__(
            self,
            "_snapshot_id",
            _content_id("snapshot", self._payload()),
        )

    @property
    def novel_descriptor_ids(self) -> tuple[str, ...]:
        return tuple(item.descriptor_id for item in self.novel_descriptors)

    @property
    def selected_checkpoint_draw_count(self) -> int:
        return self.validation_prefix.selected_checkpoint_draw_count

    @property
    def snapshot_id(self) -> str:
        return self._snapshot_id

    def _payload(self) -> dict[str, Any]:
        epoch = _require_support_epoch(self.support_epoch)
        return {
            "schema": "acfqp.v072_partial_support_confidence_snapshot.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": self.profile.preregistration_id,
            "profile_id": self.profile.profile_id,
            "row_binding_id": epoch.row_binding.row_binding_id,
            "support_epoch_id": epoch.support_epoch_id,
            "support_epoch_chain_id": epoch.support_epoch_chain_id,
            "row_confidence_epoch_id": self.row_confidence_epoch_id,
            "validation_prefix_id": self.validation_prefix.prefix_id,
            "selected_checkpoint_draw_count": self.selected_checkpoint_draw_count,
            "sequential_profile_id": self.sequential_profile.profile_id,
            "event_interval_ids": [
                item.event_interval_id for item in self.event_intervals
            ],
            "joint_simplex_id": self.joint_simplex.simplex_id,
            "novel_descriptors": [
                item.to_document() for item in self.novel_descriptors
            ],
            "row_epoch_beta": _fdoc(self.row_epoch_beta),
            "per_event_alpha": _fdoc(self.per_event_alpha),
            "other_event_count": 1,
            "checkpoint_consumes_additional_row_epoch_authority": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "snapshot_id": self.snapshot_id}


def _validate_snapshot_structure(
    snapshot: PartialSupportConfidenceSnapshotV2,
) -> None:
    epoch = _require_support_epoch(snapshot.support_epoch)
    if (
        type(snapshot.profile) is not PartialSupportConfidenceProfileV2
        or type(snapshot.validation_prefix) is not ValidationPrefixV2
        or type(snapshot.sequential_profile) is not SequentialBernoulliProfileV1
        or type(snapshot.event_intervals) is not tuple
        or any(
            type(item) is not PartialSupportEventIntervalV2
            for item in snapshot.event_intervals
        )
        or type(snapshot.joint_simplex) is not PartialSupportJointSimplexV2
        or type(snapshot.novel_descriptors) is not tuple
        or any(
            type(item) is not OpaqueOutcomeDescriptorV2
            for item in snapshot.novel_descriptors
        )
        or snapshot.row_epoch_beta != ROW_EPOCH_BETA
        or snapshot.other_event_count != 1
        or snapshot.checkpoint_consumes_additional_row_epoch_authority is not False
    ):
        raise PartialSupportConfidenceV2InvariantViolation(
            "confidence snapshot concrete schema is invalid"
        )
    _validate_epoch_and_prefix(epoch, snapshot.validation_prefix, snapshot.profile)
    expected_sequential = snapshot.profile.sequential_profile(
        epoch.event_count, epoch.purpose
    )
    expected_events = _expected_events(
        epoch, snapshot.validation_prefix, expected_sequential
    )
    _, expected_novel = _counts_and_novel(
        epoch, snapshot.validation_prefix.observations
    )
    expected_alpha = ROW_EPOCH_BETA / epoch.event_count
    expected_epoch_id = _row_confidence_epoch_id(epoch, snapshot.profile)
    if (
        snapshot.sequential_profile != expected_sequential
        or snapshot.per_event_alpha != expected_alpha
        or snapshot.sequential_profile.confidence_alpha != expected_alpha
        or snapshot.event_intervals != expected_events
        or len(snapshot.event_intervals) != epoch.event_count
        or sum(item.success_count for item in snapshot.event_intervals)
        != snapshot.selected_checkpoint_draw_count
        or sum(
            item.event_kind is PartialSupportEventKindV2.OTHER
            for item in snapshot.event_intervals
        )
        != 1
        or snapshot.event_intervals[-1].event_key != OTHER_EVENT_KEY
        or snapshot.novel_descriptors != expected_novel
        or snapshot.row_confidence_epoch_id != expected_epoch_id
        or epoch.event_count * snapshot.per_event_alpha != ROW_EPOCH_BETA
        or snapshot.joint_simplex
        != _expected_simplex(epoch, snapshot.validation_prefix, expected_events)
    ):
        raise PartialSupportConfidenceV2InvariantViolation(
            "counts, alpha, OTHER, novel set, or exact simplex was transplanted"
        )


def build_partial_support_confidence_snapshot_v2(
    support_epoch: SupportEpochV2,
    validation_observations: tuple[
        ConfidenceObservationProtocolV2 | OpaqueConfidenceObservationV2, ...
    ],
    profile: PartialSupportConfidenceProfileV2 | None = None,
) -> PartialSupportConfidenceSnapshotV2:
    epoch = _require_support_epoch(support_epoch)
    canonical_profile = (
        v0072_partial_support_confidence_profile_v2()
        if profile is None
        else profile
    )
    if type(canonical_profile) is not PartialSupportConfidenceProfileV2:
        raise PartialSupportConfidenceV2InvariantViolation(
            "snapshot requires the concrete V2 confidence profile"
        )
    observations = _freeze_observations(validation_observations)
    prefix = ValidationPrefixV2(
        row_binding_id=epoch.row_binding.row_binding_id,
        support_epoch_id=epoch.support_epoch_id,
        support_epoch_chain_id=epoch.support_epoch_chain_id,
        validation_stream_id=epoch.validation_stream_id,
        selected_checkpoint_draw_count=len(observations),
        observations=observations,
    )
    _validate_epoch_and_prefix(epoch, prefix, canonical_profile)
    sequential = canonical_profile.sequential_profile(
        epoch.event_count, epoch.purpose
    )
    events = _expected_events(epoch, prefix, sequential)
    _, novel = _counts_and_novel(epoch, observations)
    return PartialSupportConfidenceSnapshotV2(
        support_epoch=epoch,
        profile=canonical_profile,
        validation_prefix=prefix,
        sequential_profile=sequential,
        event_intervals=events,
        joint_simplex=_expected_simplex(epoch, prefix, events),
        novel_descriptors=novel,
        row_confidence_epoch_id=_row_confidence_epoch_id(
            epoch, canonical_profile
        ),
        per_event_alpha=ROW_EPOCH_BETA / epoch.event_count,
    )


def promote_support_epoch_v2(
    parent_snapshot: PartialSupportConfidenceSnapshotV2,
    *,
    next_support_epoch_chain_id: str,
    next_validation_stream_id: str,
) -> PromotedSupportEpochV2:
    """Promote *all* novel descriptors and quarantine all prior samples."""

    verify_partial_support_confidence_snapshot_v2(parent_snapshot)
    parent_epoch = _require_support_epoch(parent_snapshot.support_epoch)
    if not parent_snapshot.novel_descriptors:
        raise PartialSupportConfidenceV2InvariantViolation(
            "promotion requires at least one parent novel descriptor"
        )
    by_id = {
        item.descriptor_id: item for item in parent_epoch.support_descriptors
    }
    for item in parent_snapshot.novel_descriptors:
        by_id[item.descriptor_id] = item
    support = tuple(by_id[key] for key in sorted(by_id))
    excluded = tuple(
        sorted(
            set(parent_epoch.excluded_probability_sample_ids)
            | set(parent_snapshot.validation_prefix.sample_ids)
        )
    )
    forbidden = tuple(
        sorted(
            set(parent_epoch.forbidden_validation_stream_ids)
            | {parent_epoch.validation_stream_id}
        )
    )
    evidence = PromotionEvidenceV2(
        parent_snapshot_id=parent_snapshot.snapshot_id,
        parent_support_epoch_id=parent_epoch.support_epoch_id,
        parent_validation_prefix_id=parent_snapshot.validation_prefix.prefix_id,
        parent_support_descriptor_ids=tuple(
            sorted(parent_epoch.support_descriptor_ids)
        ),
        parent_novel_descriptor_ids=tuple(
            sorted(parent_snapshot.novel_descriptor_ids)
        ),
        promoted_support_descriptor_ids=tuple(
            item.descriptor_id for item in support
        ),
        excluded_probability_sample_ids=excluded,
        forbidden_validation_stream_ids=forbidden,
    )
    return PromotedSupportEpochV2(
        row_binding=parent_epoch.row_binding,
        profile_id=parent_epoch.profile_id,
        epoch_index=parent_epoch.epoch_index + 1,
        purpose=ConfidenceEpochPurposeV2.PROMOTION,
        support_epoch_chain_id=next_support_epoch_chain_id,
        validation_stream_id=next_validation_stream_id,
        parent_snapshot=parent_snapshot,
        promotion_evidence=evidence,
        support_descriptors=support,
        excluded_probability_sample_ids=excluded,
        forbidden_validation_stream_ids=forbidden,
    )


@dataclass(frozen=True, slots=True)
class PartialSupportConfidenceVerificationV2:
    snapshot_id: str
    row_confidence_epoch_id: str
    support_epoch_id: str
    validation_prefix_id: str
    joint_simplex_id: str
    selected_checkpoint_draw_count: int
    event_count: int
    per_event_alpha: Fraction
    row_epoch_beta: Fraction
    verification_result: str = (
        "VALID_INDEPENDENT_EXACT_V072_SPLIT_SUPPORT_CONFIDENCE"
    )

    def __post_init__(self) -> None:
        for value, label in (
            (self.snapshot_id, "verified snapshot"),
            (self.row_confidence_epoch_id, "verified row epoch"),
            (self.support_epoch_id, "verified support epoch"),
            (self.validation_prefix_id, "verified validation prefix"),
            (self.joint_simplex_id, "verified simplex"),
        ):
            _cid(value, label)
        if (
            self.selected_checkpoint_draw_count <= 0
            or not 2 <= self.event_count <= MAX_SUPPORT_DESCRIPTORS + 1
            or self.per_event_alpha != ROW_EPOCH_BETA / self.event_count
            or self.row_epoch_beta != ROW_EPOCH_BETA
            or self.verification_result
            != "VALID_INDEPENDENT_EXACT_V072_SPLIT_SUPPORT_CONFIDENCE"
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "confidence verification artifact is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_confidence_snapshot_verification.v2",
            "schema_version": SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id,
            "row_confidence_epoch_id": self.row_confidence_epoch_id,
            "support_epoch_id": self.support_epoch_id,
            "validation_prefix_id": self.validation_prefix_id,
            "joint_simplex_id": self.joint_simplex_id,
            "selected_checkpoint_draw_count": self.selected_checkpoint_draw_count,
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


def _independently_verify_epoch_lineage(epoch: SupportEpochV2) -> None:
    """Replay epoch lineage without invoking either public builder."""

    if type(epoch) is InitialSupportEpochV2:
        discovery = epoch.discovery_evidence
        _validate_bound_prefix(
            discovery.observations,
            epoch.row_binding,
            support_epoch_chain_id=discovery.discovery_support_epoch_chain_id,
            stream_id=discovery.discovery_stream_id,
            lane=ConfidenceObservationLaneV2.DISCOVERY,
        )
        expected_support = _representative_descriptors(discovery.observations)
        if (
            discovery.proposed_support != expected_support
            or epoch.support_descriptors != expected_support
            or epoch.excluded_probability_sample_ids
            != tuple(sorted(item.sample_id for item in discovery.observations))
            or epoch.forbidden_validation_stream_ids
            != (discovery.discovery_stream_id,)
            or discovery.probability_evidence_draw_count != 0
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "independent replay rejected initial discovery lineage"
            )
        return
    if type(epoch) is not PromotedSupportEpochV2:
        raise PartialSupportConfidenceV2InvariantViolation(
            "independent replay rejects an unknown support epoch"
        )
    parent = epoch.parent_snapshot
    verify_partial_support_confidence_snapshot_v2(parent)
    parent_epoch = _require_support_epoch(parent.support_epoch)
    expected_novel_ids = tuple(
        sorted(
            {
                item.outcome.descriptor_id
                for item in parent.validation_prefix.observations
                if item.outcome.descriptor_id
                not in set(parent_epoch.support_descriptor_ids)
            }
        )
    )
    by_id = {
        item.descriptor_id: item for item in parent_epoch.support_descriptors
    }
    for item in parent.novel_descriptors:
        by_id[item.descriptor_id] = item
    expected_support = tuple(by_id[key] for key in sorted(by_id))
    expected_excluded = tuple(
        sorted(
            set(parent_epoch.excluded_probability_sample_ids)
            | set(parent.validation_prefix.sample_ids)
        )
    )
    expected_forbidden = tuple(
        sorted(
            set(parent_epoch.forbidden_validation_stream_ids)
            | {parent_epoch.validation_stream_id}
        )
    )
    if (
        parent.novel_descriptor_ids != expected_novel_ids
        or not expected_novel_ids
        or epoch.support_descriptors != expected_support
        or epoch.excluded_probability_sample_ids != expected_excluded
        or epoch.forbidden_validation_stream_ids != expected_forbidden
        or epoch.promotion_evidence.parent_novel_descriptor_ids
        != expected_novel_ids
        or epoch.promotion_evidence.promoted_support_descriptor_ids
        != tuple(item.descriptor_id for item in expected_support)
        or epoch.promotion_evidence.fresh_discovery_draw_count != 0
    ):
        raise PartialSupportConfidenceV2InvariantViolation(
            "independent replay rejected promoted support lineage"
        )


def verify_partial_support_confidence_snapshot_v2(
    snapshot: PartialSupportConfidenceSnapshotV2,
) -> PartialSupportConfidenceVerificationV2:
    """Independently replay counts, intervals, simplex, prefix, and lineage.

    This function intentionally does not call
    :func:`build_partial_support_confidence_snapshot_v2`.
    """

    if type(snapshot) is not PartialSupportConfidenceSnapshotV2:
        raise PartialSupportConfidenceV2InvariantViolation(
            "verification requires a concrete V2 snapshot"
        )
    epoch = _require_support_epoch(snapshot.support_epoch)
    _independently_verify_epoch_lineage(epoch)
    _validate_epoch_and_prefix(epoch, snapshot.validation_prefix, snapshot.profile)

    expected_counts, expected_novel = _counts_and_novel(
        epoch, snapshot.validation_prefix.observations
    )
    expected_sequential = snapshot.profile.sequential_profile(
        epoch.event_count, epoch.purpose
    )
    keys = epoch.support_descriptor_ids + (OTHER_EVENT_KEY,)
    rebuilt_events: list[PartialSupportEventIntervalV2] = []
    for ordinal, (key, count) in enumerate(zip(keys, expected_counts)):
        checkpoint = build_anytime_bernoulli_checkpoint_v1(
            snapshot.selected_checkpoint_draw_count,
            count,
            expected_sequential,
        )
        rebuilt_events.append(
            PartialSupportEventIntervalV2(
                support_epoch_id=epoch.support_epoch_id,
                validation_prefix_id=snapshot.validation_prefix.prefix_id,
                sequential_profile_id=expected_sequential.profile_id,
                event_ordinal=ordinal,
                event_kind=(
                    PartialSupportEventKindV2.OTHER
                    if ordinal == len(keys) - 1
                    else PartialSupportEventKindV2.SUPPORT
                ),
                event_key=key,
                success_count=count,
                checkpoint=checkpoint,
            )
        )
    events = tuple(rebuilt_events)
    lower = tuple(item.lower_probability for item in events)
    upper = tuple(item.upper_probability for item in events)
    rebuilt_simplex = PartialSupportJointSimplexV2(
        support_epoch_id=epoch.support_epoch_id,
        validation_prefix_id=snapshot.validation_prefix.prefix_id,
        event_interval_ids=tuple(item.event_interval_id for item in events),
        lower_probabilities=lower,
        upper_probabilities=upper,
        other_coordinate_ordinal=len(events) - 1,
    )
    expected_row_epoch_id = _row_confidence_epoch_id(epoch, snapshot.profile)
    expected_alpha = ROW_EPOCH_BETA / epoch.event_count
    if (
        snapshot.profile.preregistration_id != _preregistration_id()
        or snapshot.row_epoch_beta != ROW_EPOCH_BETA
        or snapshot.per_event_alpha != expected_alpha
        or snapshot.sequential_profile != expected_sequential
        or snapshot.event_intervals != events
        or snapshot.joint_simplex != rebuilt_simplex
        or snapshot.novel_descriptors != expected_novel
        or snapshot.row_confidence_epoch_id != expected_row_epoch_id
        or sum(expected_counts) != snapshot.selected_checkpoint_draw_count
        or len(events) != len(epoch.support_descriptors) + 1
        or events[-1].event_kind is not PartialSupportEventKindV2.OTHER
        or any(
            item.event_kind is PartialSupportEventKindV2.OTHER
            for item in events[:-1]
        )
    ):
        raise PartialSupportConfidenceV2InvariantViolation(
            "independent confidence replay differs from the supplied snapshot"
        )
    expected_snapshot_id = _content_id("snapshot", snapshot._payload())
    if snapshot.snapshot_id != expected_snapshot_id:
        raise PartialSupportConfidenceV2InvariantViolation(
            "snapshot content ID does not recompute"
        )
    return PartialSupportConfidenceVerificationV2(
        snapshot_id=snapshot.snapshot_id,
        row_confidence_epoch_id=snapshot.row_confidence_epoch_id,
        support_epoch_id=epoch.support_epoch_id,
        validation_prefix_id=snapshot.validation_prefix.prefix_id,
        joint_simplex_id=snapshot.joint_simplex.simplex_id,
        selected_checkpoint_draw_count=snapshot.selected_checkpoint_draw_count,
        event_count=epoch.event_count,
        per_event_alpha=expected_alpha,
        row_epoch_beta=ROW_EPOCH_BETA,
    )


@dataclass(frozen=True, slots=True)
class RowConfidenceCheckpointSeriesV2:
    snapshots: tuple[PartialSupportConfidenceSnapshotV2, ...]
    row_epoch_authorities_consumed: int = 1
    checkpoint_alpha_spending: bool = False
    _series_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.snapshots) is not tuple
            or not self.snapshots
            or any(
                type(item) is not PartialSupportConfidenceSnapshotV2
                for item in self.snapshots
            )
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "checkpoint series requires concrete snapshots"
            )
        for snapshot in self.snapshots:
            verify_partial_support_confidence_snapshot_v2(snapshot)
        first = self.snapshots[0]
        checkpoints = tuple(
            item.selected_checkpoint_draw_count for item in self.snapshots
        )
        if (
            checkpoints != tuple(sorted(set(checkpoints)))
            or any(
                item.row_confidence_epoch_id != first.row_confidence_epoch_id
                for item in self.snapshots
            )
            or any(
                later.validation_prefix.observations[: len(earlier.validation_prefix.observations)]
                != earlier.validation_prefix.observations
                for earlier, later in zip(self.snapshots, self.snapshots[1:])
            )
            or self.row_epoch_authorities_consumed != 1
            or self.checkpoint_alpha_spending is not False
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "checkpoint snapshots are not immutable prefixes of one row epoch"
            )
        object.__setattr__(
            self,
            "_series_id",
            _content_id("snapshot_series", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_confidence_checkpoint_series.v2",
            "schema_version": SCHEMA_VERSION,
            "row_confidence_epoch_id": (
                self.snapshots[0].row_confidence_epoch_id
            ),
            "snapshot_ids": [item.snapshot_id for item in self.snapshots],
            "checkpoint_draw_counts": [
                item.selected_checkpoint_draw_count for item in self.snapshots
            ],
            "row_epoch_authorities_consumed": 1,
            "checkpoint_alpha_spending": False,
            "time_uniform_single_alpha": True,
        }

    @property
    def series_id(self) -> str:
        return self._series_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "series_id": self.series_id}


@dataclass(frozen=True, slots=True)
class V072CampaignConfidenceAllocationV2:
    preregistration_id: str
    arm_count: int = ARM_COUNT
    maximum_row_epoch_authorities_per_arm: int = (
        MAX_ARM_ROW_EPOCH_AUTHORITIES
    )
    maximum_campaign_row_epoch_authorities: int = (
        MAX_CAMPAIGN_ROW_EPOCH_AUTHORITIES
    )
    row_epoch_beta: Fraction = ROW_EPOCH_BETA
    campaign_joint_tail_upper: Fraction = CAMPAIGN_JOINT_TAIL_UPPER
    campaign_confidence_lower: Fraction = CAMPAIGN_CONFIDENCE_LOWER
    proof_rule: str = CAMPAIGN_PROOF_RULE
    cross_arm_independence_required: bool = False
    _allocation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            _cid(self.preregistration_id, "allocation preregistration")
            != _preregistration_id()
            or self.arm_count != len(prereg.ARM_ORDER)
            or self.arm_count != ARM_COUNT
            or self.maximum_row_epoch_authorities_per_arm
            != MAX_ARM_ROW_EPOCH_AUTHORITIES
            or self.maximum_campaign_row_epoch_authorities
            != self.arm_count * self.maximum_row_epoch_authorities_per_arm
            or self.maximum_campaign_row_epoch_authorities
            != MAX_CAMPAIGN_ROW_EPOCH_AUTHORITIES
            or self.row_epoch_beta != ROW_EPOCH_BETA
            or self.campaign_joint_tail_upper
            != self.maximum_campaign_row_epoch_authorities * self.row_epoch_beta
            or self.campaign_joint_tail_upper != CAMPAIGN_JOINT_TAIL_UPPER
            or self.campaign_confidence_lower
            != 1 - self.campaign_joint_tail_upper
            or self.campaign_confidence_lower != CAMPAIGN_CONFIDENCE_LOWER
            or self.proof_rule != CAMPAIGN_PROOF_RULE
            or self.cross_arm_independence_required is not False
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "campaign confidence allocation does not prove the frozen union bound"
            )
        object.__setattr__(
            self,
            "_allocation_id",
            _content_id("allocation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_campaign_confidence_allocation.v2",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "arm_count": self.arm_count,
            "maximum_row_epoch_authorities_per_arm": (
                self.maximum_row_epoch_authorities_per_arm
            ),
            "maximum_campaign_row_epoch_authorities": (
                self.maximum_campaign_row_epoch_authorities
            ),
            "row_epoch_beta": _fdoc(self.row_epoch_beta),
            "campaign_joint_tail_upper": _fdoc(
                self.campaign_joint_tail_upper
            ),
            "campaign_confidence_lower": _fdoc(
                self.campaign_confidence_lower
            ),
            "proof_rule": self.proof_rule,
            "cross_arm_independence_required": False,
        }

    @property
    def allocation_id(self) -> str:
        return self._allocation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "allocation_id": self.allocation_id}


def v0072_campaign_confidence_allocation_v2(
) -> V072CampaignConfidenceAllocationV2:
    return V072CampaignConfidenceAllocationV2(_preregistration_id())


@dataclass(frozen=True, slots=True)
class V072CampaignConfidenceAllocationVerificationV2:
    allocation_id: str
    maximum_campaign_row_epoch_authorities: int
    campaign_joint_tail_upper: Fraction
    campaign_confidence_lower: Fraction
    verification_result: str = (
        "VALID_FINITE_UNION_BOUND_WITHOUT_INDEPENDENCE"
    )

    def __post_init__(self) -> None:
        _cid(self.allocation_id, "verified allocation")
        if (
            self.maximum_campaign_row_epoch_authorities
            != MAX_CAMPAIGN_ROW_EPOCH_AUTHORITIES
            or self.campaign_joint_tail_upper != CAMPAIGN_JOINT_TAIL_UPPER
            or self.campaign_confidence_lower != CAMPAIGN_CONFIDENCE_LOWER
            or self.verification_result
            != "VALID_FINITE_UNION_BOUND_WITHOUT_INDEPENDENCE"
        ):
            raise PartialSupportConfidenceV2InvariantViolation(
                "campaign allocation verification changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_campaign_confidence_allocation_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "allocation_id": self.allocation_id,
            "maximum_campaign_row_epoch_authorities": (
                self.maximum_campaign_row_epoch_authorities
            ),
            "campaign_joint_tail_upper": _fdoc(
                self.campaign_joint_tail_upper
            ),
            "campaign_confidence_lower": _fdoc(
                self.campaign_confidence_lower
            ),
            "verification_result": self.verification_result,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("allocation_verification", self._payload())


def verify_v0072_campaign_confidence_allocation_v2(
    allocation: V072CampaignConfidenceAllocationV2,
) -> V072CampaignConfidenceAllocationVerificationV2:
    if type(allocation) is not V072CampaignConfidenceAllocationV2:
        raise PartialSupportConfidenceV2InvariantViolation(
            "allocation verifier requires a concrete V2 artifact"
        )
    expected = v0072_campaign_confidence_allocation_v2()
    if allocation != expected or allocation.allocation_id != expected.allocation_id:
        raise PartialSupportConfidenceV2InvariantViolation(
            "campaign allocation does not survive independent reconstruction"
        )
    return V072CampaignConfidenceAllocationVerificationV2(
        allocation_id=allocation.allocation_id,
        maximum_campaign_row_epoch_authorities=(
            allocation.maximum_campaign_row_epoch_authorities
        ),
        campaign_joint_tail_upper=allocation.campaign_joint_tail_upper,
        campaign_confidence_lower=allocation.campaign_confidence_lower,
    )


__all__ = [
    "ARM_COUNT",
    "BOUNDARY_GRID_BITS",
    "CAMPAIGN_CONFIDENCE_LOWER",
    "CAMPAIGN_JOINT_TAIL_UPPER",
    "COLD_CHECKPOINTS",
    "ConfidenceEpochPurposeV2",
    "ConfidenceObservationLaneV2",
    "ConfidenceObservationProtocolV2",
    "ConfidencePhysicalRowBindingV2",
    "DIRECT_CHECKPOINTS",
    "DiscoveryProposalEvidenceV2",
    "InitialSupportEpochV2",
    "MAX_ARM_ROW_EPOCH_AUTHORITIES",
    "MAX_CAMPAIGN_ROW_EPOCH_AUTHORITIES",
    "MAX_SUPPORT_DESCRIPTORS",
    "NEW_CHILD_CHECKPOINTS",
    "OTHER_EVENT_KEY",
    "OpaqueConfidenceObservationV2",
    "OpaqueOutcomeDescriptorV2",
    "PROMOTION_CHECKPOINTS",
    "PartialSupportConfidenceProfileV2",
    "PartialSupportConfidenceSnapshotV2",
    "PartialSupportConfidenceV2InvariantViolation",
    "PartialSupportConfidenceVerificationV2",
    "PartialSupportEventIntervalV2",
    "PartialSupportEventKindV2",
    "PartialSupportJointSimplexV2",
    "PromotedSupportEpochV2",
    "PromotionEvidenceV2",
    "ROW_EPOCH_BETA",
    "RowConfidenceCheckpointSeriesV2",
    "SupportEpochV2",
    "V072CampaignConfidenceAllocationV2",
    "V072CampaignConfidenceAllocationVerificationV2",
    "ValidationPrefixV2",
    "build_partial_support_confidence_snapshot_v2",
    "freeze_confidence_observation_v2",
    "freeze_initial_support_epoch_v2",
    "promote_support_epoch_v2",
    "v0072_campaign_confidence_allocation_v2",
    "v0072_partial_support_confidence_profile_v2",
    "verify_partial_support_confidence_snapshot_v2",
    "verify_v0072_campaign_confidence_allocation_v2",
]
