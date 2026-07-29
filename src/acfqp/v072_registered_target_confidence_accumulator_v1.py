"""Anchor-gated registered row acquisition and confidence-count core.

The production entry point owns the observer.  It accepts no observation,
law, seed, random word, count, interval, source prior, status, or terminal
argument.  Invalid authority/context/frontier identities fail before a target
stream is opened.  The output is an append-only linear transcript; a separate
independent verifier replays it and is the only authority allowed to mint a
registered confidence projection authority.

The count-to-interval core is deterministic and target-free.  It can be
tested with registration-disjoint synthetic descriptor identities without
opening the registered held-out family.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.sequential_bernoulli_acquisition_v1 import (
    AnytimeBernoulliCheckpointV1,
    SequentialBernoulliProfileV1,
    build_anytime_bernoulli_checkpoint_v1,
)
from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import partial_support_confidence_v2 as confidence
from acfqp import public_novel_child_cardinality_authority_v2 as descriptors
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import v072_registered_campaign_consumer_v1 as consumer


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_registered_target_confidence_accumulator_v1"
REGISTERED_OBSERVATIONS_GENERATED_PRE_ANCHOR = 0
REGISTERED_INCREMENTAL_FRONTIER_SELECTION_AUTHORITY_STATUS = (
    "ENABLED_ONLY_BY_INDEPENDENT_FAILED_PROOF_SELECTOR_REPLAY"
)

DOMAIN_TAGS = {
    "selection": (
        "acfqp:v072-registered-acquisition-selection-authority:v1"
    ),
    "frontier": "acfqp:v072-registered-acquisition-frontier:v1",
    "entry": "acfqp:v072-registered-linear-observation-entry:v1",
    "transcript": "acfqp:v072-registered-linear-row-transcript:v1",
    "acquisition": "acfqp:v072-registered-target-row-acquisition:v1",
    "core_event": "acfqp:v072-registered-confidence-core-event:v1",
    "core": "acfqp:v072-registered-confidence-count-core:v1",
    "sequence": "acfqp:v072-registered-confidence-sequence:v1",
}


class V072RegisteredTargetConfidenceAccumulatorViolation(ValueError):
    """A production identity, transcript, frontier, or count core is invalid."""


@dataclass(frozen=True, slots=True)
class RegisteredTargetAcquisitionAccessAuditV1:
    authority_chain_verifications: int = 0
    observer_stream_opens: int = 0
    observer_draw_calls: int = 0
    accepted_observations: int = 0

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value < 0
            for value in (
                self.authority_chain_verifications,
                self.observer_stream_opens,
                self.observer_draw_calls,
                self.accepted_observations,
            )
        ):
            raise V072RegisteredTargetConfidenceAccumulatorViolation(
                "registered acquisition audit counters are invalid"
            )

    @property
    def target_access_started(self) -> bool:
        return any(
            (
                self.observer_stream_opens,
                self.observer_draw_calls,
                self.accepted_observations,
            )
        )


ZERO_TARGET_ACCESS_AUDIT = RegisteredTargetAcquisitionAccessAuditV1()


class RegisteredTargetAcquisitionGateLockedV1(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        access_audit: RegisteredTargetAcquisitionAccessAuditV1,
    ) -> None:
        super().__init__(message)
        self.access_audit = access_audit


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V072RegisteredTargetConfidenceAccumulatorViolation(
            str(error)
        ) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072RegisteredTargetConfidenceAccumulatorViolation(
            f"{label} must be one full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V072RegisteredTargetConfidenceAccumulatorViolation(
            "registered confidence arithmetic must use exact Fraction"
        )
    return {"numerator": value.numerator, "denominator": value.denominator}


class RegisteredTargetAcquisitionPurposeV1(str, Enum):
    COLD_INITIAL = "COLD_INITIAL"
    INCREMENTAL_NEW_CHILD_ROUND_1 = "INCREMENTAL_NEW_CHILD_ROUND_1"
    INCREMENTAL_NEW_CHILD_ROUND_2 = "INCREMENTAL_NEW_CHILD_ROUND_2"
    INCREMENTAL_PROMOTION_ROUND_1 = "INCREMENTAL_PROMOTION_ROUND_1"
    INCREMENTAL_PROMOTION_ROUND_2 = "INCREMENTAL_PROMOTION_ROUND_2"

    @property
    def round_index(self) -> int:
        return {
            self.COLD_INITIAL: 0,
            self.INCREMENTAL_NEW_CHILD_ROUND_1: 1,
            self.INCREMENTAL_NEW_CHILD_ROUND_2: 2,
            self.INCREMENTAL_PROMOTION_ROUND_1: 1,
            self.INCREMENTAL_PROMOTION_ROUND_2: 2,
        }[self]

    @property
    def discovery_draw_count(self) -> int:
        return (
            0
            if self in (
                self.INCREMENTAL_PROMOTION_ROUND_1,
                self.INCREMENTAL_PROMOTION_ROUND_2,
            )
            else prereg.INITIAL_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
        )

    @property
    def required_checkpoint(self) -> int:
        return (
            prereg.NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW
            if self in (
                self.INCREMENTAL_NEW_CHILD_ROUND_1,
                self.INCREMENTAL_NEW_CHILD_ROUND_2,
            )
            else prereg.INITIAL_VALIDATION_DRAWS_PER_PHYSICAL_ROW
        )

    @property
    def is_promotion(self) -> bool:
        return self in (
            self.INCREMENTAL_PROMOTION_ROUND_1,
            self.INCREMENTAL_PROMOTION_ROUND_2,
        )

    @property
    def is_new_child(self) -> bool:
        return self in (
            self.INCREMENTAL_NEW_CHILD_ROUND_1,
            self.INCREMENTAL_NEW_CHILD_ROUND_2,
        )


_SELECTION_AUTHORITY_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredAcquisitionSelectionAuthorityV1:
    """Exact independently replayed selector output; never caller-minted."""

    _minting_capability: object
    authority_chain_id: str
    anchor_id: str
    context_id: str
    arm: str
    round_index: int
    predecessor_frontier_id: str | None
    occurrence_id: str
    failed_audit_id: str
    model_pair_id: str
    model_replay_attestation_id: str
    candidate_inventory_id: str
    proposal_order_id: str
    selected_candidate_id: str
    supporting_acquisition_ids: tuple[str, ...]
    supporting_row_binding_ids: tuple[str, ...]
    promotion_row_binding_id: str
    new_child_row_binding_ids: tuple[str, ...]
    selected_row_binding_ids: tuple[str, ...]
    selected_draw_upper: int
    cumulative_draw_upper: int
    causal_evidence_id: str
    _selection_authority_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.authority_chain_id, "selection authority chain"),
            (self.anchor_id, "selection anchor"),
            (self.context_id, "selection context"),
            (self.occurrence_id, "selection occurrence"),
            (self.failed_audit_id, "selection failed audit"),
            (self.model_pair_id, "selection model pair"),
            (
                self.model_replay_attestation_id,
                "selection model replay attestation",
            ),
            (self.candidate_inventory_id, "selection candidate inventory"),
            (self.proposal_order_id, "selection proposal order"),
            (self.selected_candidate_id, "selection candidate"),
            (
                self.promotion_row_binding_id,
                "selection promotion row",
            ),
            (self.causal_evidence_id, "selection causal evidence"),
        ):
            _cid(value, label)
        if self.predecessor_frontier_id is not None:
            _cid(
                self.predecessor_frontier_id,
                "selection predecessor frontier",
            )
        if (
            self._minting_capability
            is not _SELECTION_AUTHORITY_MINTING_SENTINEL
            or self.arm not in prereg.ARM_ORDER[:-1]
            or self.round_index not in (1, 2)
            or (
                self.round_index == 1
                and self.predecessor_frontier_id is not None
            )
            or (
                self.round_index == 2
                and self.predecessor_frontier_id is None
            )
            or self.supporting_acquisition_ids
            != tuple(sorted(set(self.supporting_acquisition_ids)))
            or not self.supporting_acquisition_ids
            or self.supporting_row_binding_ids
            != tuple(sorted(set(self.supporting_row_binding_ids)))
            or not self.supporting_row_binding_ids
            or self.new_child_row_binding_ids
            != tuple(sorted(set(self.new_child_row_binding_ids)))
            or self.selected_row_binding_ids
            != tuple(sorted(set(self.selected_row_binding_ids)))
            or not self.selected_row_binding_ids
            or self.promotion_row_binding_id
            not in self.supporting_row_binding_ids
            or set(self.new_child_row_binding_ids)
            & set(self.supporting_row_binding_ids)
            or self.selected_row_binding_ids
            != tuple(
                sorted(
                    (
                        self.promotion_row_binding_id,
                        *self.new_child_row_binding_ids,
                    )
                )
            )
            or type(self.selected_draw_upper) is not int
            or self.selected_draw_upper
            != (
                prereg.PROMOTION_VALIDATION_DRAWS_PER_ROUND
                + (
                    prereg.NEW_CHILD_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
                    + prereg.NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW
                )
                * len(self.new_child_row_binding_ids)
            )
            or type(self.cumulative_draw_upper) is not int
            or not (
                self.selected_draw_upper
                <= self.cumulative_draw_upper
                <= prereg.MAX_TWO_ROUND_INCREMENTAL_DRAW_CAP_PER_ARM
            )
            or (
                self.round_index == 1
                and self.cumulative_draw_upper != self.selected_draw_upper
            )
            or (
                self.round_index == 2
                and self.cumulative_draw_upper
                <= self.selected_draw_upper
            )
        ):
            raise V072RegisteredTargetConfidenceAccumulatorViolation(
                "registered selector/causal authority is absent or malformed"
            )
        for value in (
            *self.supporting_acquisition_ids,
            *self.supporting_row_binding_ids,
            *self.new_child_row_binding_ids,
            *self.selected_row_binding_ids,
        ):
            _cid(value, "selection member")
        object.__setattr__(
            self,
            "_selection_authority_id",
            _content_id("selection", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_acquisition_selection_authority.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "round_index": self.round_index,
            "predecessor_frontier_id": self.predecessor_frontier_id,
            "occurrence_id": self.occurrence_id,
            "failed_audit_id": self.failed_audit_id,
            "model_pair_id": self.model_pair_id,
            "model_replay_attestation_id": (
                self.model_replay_attestation_id
            ),
            "candidate_inventory_id": self.candidate_inventory_id,
            "proposal_order_id": self.proposal_order_id,
            "selected_candidate_id": self.selected_candidate_id,
            "supporting_acquisition_ids": list(
                self.supporting_acquisition_ids
            ),
            "supporting_row_binding_ids": list(
                self.supporting_row_binding_ids
            ),
            "selected_row_binding_ids": list(
                self.selected_row_binding_ids
            ),
            "promotion_row_binding_id": self.promotion_row_binding_id,
            "new_child_row_binding_ids": list(
                self.new_child_row_binding_ids
            ),
            "selected_draw_upper": self.selected_draw_upper,
            "cumulative_draw_upper": self.cumulative_draw_upper,
            "causal_evidence_id": self.causal_evidence_id,
            "source_prior_used_for_ordering_only": True,
            "source_prior_used_in_causal_evidence": False,
            "source_prior_used_in_confidence": False,
            "source_quantities_serialized_in_authority": False,
            "caller_content_ids_can_authorize": False,
        }

    @property
    def selection_authority_id(self) -> str:
        return self._selection_authority_id


_FRONTIER_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredAcquisitionFrontierV1:
    """Evidence-bound authorization frontier; never a source-prior object."""

    _minting_capability: object
    selection_authority: RegisteredAcquisitionSelectionAuthorityV1
    _frontier_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._minting_capability is not _FRONTIER_MINTING_SENTINEL
            or type(self.selection_authority)
            is not RegisteredAcquisitionSelectionAuthorityV1
        ):
            raise V072RegisteredTargetConfidenceAccumulatorViolation(
                "registered acquisition frontier is stale or incomplete"
            )
        object.__setattr__(
            self,
            "_frontier_id",
            _content_id("frontier", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_acquisition_frontier.v1",
            "schema_version": SCHEMA_VERSION,
            "selection_authority_id": (
                self.selection_authority.selection_authority_id
            ),
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "round_index": self.round_index,
            "predecessor_frontier_id": self.predecessor_frontier_id,
            "supporting_acquisition_ids": list(
                self.supporting_acquisition_ids
            ),
            "supporting_row_binding_ids": list(
                self.supporting_row_binding_ids
            ),
            "selected_row_binding_ids": list(
                self.selected_row_binding_ids
            ),
            "causal_evidence_id": self.causal_evidence_id,
            "fresh_round_two_frontier": self.round_index == 2,
            "replacement_allowed": False,
            "early_stop_allowed": False,
            "source_prior_used_for_ordering_only": True,
            "source_prior_used_in_confidence": False,
        }

    @property
    def authority_chain_id(self) -> str:
        return self.selection_authority.authority_chain_id

    @property
    def anchor_id(self) -> str:
        return self.selection_authority.anchor_id

    @property
    def context_id(self) -> str:
        return self.selection_authority.context_id

    @property
    def arm(self) -> str:
        return self.selection_authority.arm

    @property
    def round_index(self) -> int:
        return self.selection_authority.round_index

    @property
    def predecessor_frontier_id(self) -> str | None:
        return self.selection_authority.predecessor_frontier_id

    @property
    def supporting_acquisition_ids(self) -> tuple[str, ...]:
        return self.selection_authority.supporting_acquisition_ids

    @property
    def supporting_row_binding_ids(self) -> tuple[str, ...]:
        return self.selection_authority.supporting_row_binding_ids

    @property
    def selected_row_binding_ids(self) -> tuple[str, ...]:
        return self.selection_authority.selected_row_binding_ids

    @property
    def promotion_row_binding_id(self) -> str:
        return self.selection_authority.promotion_row_binding_id

    @property
    def new_child_row_binding_ids(self) -> tuple[str, ...]:
        return self.selection_authority.new_child_row_binding_ids

    @property
    def cumulative_draw_upper(self) -> int:
        return self.selection_authority.cumulative_draw_upper

    @property
    def causal_evidence_id(self) -> str:
        return self.selection_authority.causal_evidence_id

    @property
    def frontier_id(self) -> str:
        return self._frontier_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "frontier_id": self.frontier_id}


@dataclass(frozen=True, slots=True)
class RegisteredLinearObservationEntryV1:
    global_sequence_index: int
    observation: observer.HeldoutObservedJointTransitionV2
    _entry_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.global_sequence_index) is not int
            or self.global_sequence_index <= 0
            or type(self.observation)
            is not observer.HeldoutObservedJointTransitionV2
        ):
            raise V072RegisteredTargetConfidenceAccumulatorViolation(
                "registered linear observation entry is malformed"
            )
        object.__setattr__(
            self,
            "_entry_id",
            _content_id("entry", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_linear_observation_entry.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "global_sequence_index": self.global_sequence_index,
            "lane": self.observation.lane.value,
            "lane_sequence_index": (
                self.observation.accepted_draw_index
            ),
            "observation_id": self.observation.observation_id,
            "source_prior_used_in_observation": False,
        }

    @property
    def entry_id(self) -> str:
        return self._entry_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "observation": self.observation.to_document(),
            "entry_id": self.entry_id,
        }


@dataclass(frozen=True, slots=True)
class RegisteredLinearRowTranscriptV1:
    anchor_id: str
    context_id: str
    row_binding_id: str
    catalogue_id: str
    arm: str
    action: tuple[int, int, int]
    purpose: RegisteredTargetAcquisitionPurposeV1
    checkpoint: int
    predecessor_transcript_id: str | None
    sequence_offset: int
    entries: tuple[RegisteredLinearObservationEntryV1, ...]
    discovery_work: observer.HeldoutTransitionStreamWorkV2 | None
    validation_work: observer.HeldoutTransitionStreamWorkV2
    _transcript_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.anchor_id, "transcript anchor"),
            (self.context_id, "transcript context"),
            (self.row_binding_id, "transcript row"),
            (self.catalogue_id, "transcript catalogue"),
        ):
            _cid(value, label)
        if self.predecessor_transcript_id is not None:
            _cid(
                self.predecessor_transcript_id,
                "transcript predecessor",
            )
        if (
            self.arm not in prereg.ARM_ORDER[:-1]
            or type(self.action) is not tuple
            or len(self.action) != 3
            or any(type(item) is not int for item in self.action)
            or type(self.purpose)
            is not RegisteredTargetAcquisitionPurposeV1
            or self.checkpoint != self.purpose.required_checkpoint
            or type(self.sequence_offset) is not int
            or self.sequence_offset < 0
            or type(self.entries) is not tuple
            or not self.entries
            or any(
                type(item) is not RegisteredLinearObservationEntryV1
                for item in self.entries
            )
            or tuple(
                item.global_sequence_index for item in self.entries
            )
            != tuple(
                range(
                    self.sequence_offset + 1,
                    self.sequence_offset + len(self.entries) + 1,
                )
            )
            or type(self.validation_work)
            is not observer.HeldoutTransitionStreamWorkV2
        ):
            raise V072RegisteredTargetConfidenceAccumulatorViolation(
                "registered transcript has a gap, reorder, or stale profile"
            )
        discovery = tuple(
            item.observation
            for item in self.entries
            if item.observation.lane is observer.ObservationLaneV2.DISCOVERY
        )
        validation = tuple(
            item.observation
            for item in self.entries
            if item.observation.lane is observer.ObservationLaneV2.VALIDATION
        )
        expected_discovery = self.purpose.discovery_draw_count
        if (
            len(discovery) != expected_discovery
            or len(validation) != self.checkpoint
            or self.entries
            != tuple(
                RegisteredLinearObservationEntryV1(
                    self.sequence_offset + index,
                    observation,
                )
                for index, observation in enumerate(
                    (*discovery, *validation),
                    start=1,
                )
            )
            or tuple(
                item.accepted_draw_index for item in discovery
            )
            != tuple(range(1, len(discovery) + 1))
            or tuple(
                item.accepted_draw_index for item in validation
            )
            != tuple(range(1, len(validation) + 1))
            or any(
                item.anchor_id != self.anchor_id
                or item.context_id != self.context_id
                or item.row_binding_id != self.row_binding_id
                or item.catalogue_id != self.catalogue_id
                or item.arm != self.arm
                or item.action != self.action
                for item in (*discovery, *validation)
            )
            or (
                expected_discovery == 0
                and self.discovery_work is not None
            )
            or (
                expected_discovery > 0
                and (
                    type(self.discovery_work)
                    is not observer.HeldoutTransitionStreamWorkV2
                    or self.discovery_work.accepted_draws
                    != expected_discovery
                )
            )
            or self.validation_work.accepted_draws != self.checkpoint
            or self.validation_work.stream_id
            != validation[0].stream_id
            or (
                discovery
                and self.discovery_work is not None
                and self.discovery_work.stream_id
                != discovery[0].stream_id
            )
            or (
                self.purpose.is_promotion
                and (
                    self.predecessor_transcript_id is None
                    or self.sequence_offset <= 0
                )
            )
            or (
                not self.purpose.is_promotion
                and (
                    self.predecessor_transcript_id is not None
                    or self.sequence_offset != 0
                )
            )
        ):
            raise V072RegisteredTargetConfidenceAccumulatorViolation(
                "registered transcript lane/count/work identities differ"
            )
        object.__setattr__(
            self,
            "_transcript_id",
            _content_id("transcript", self._payload()),
        )

    @property
    def cumulative_sequence_count(self) -> int:
        return self.sequence_offset + len(self.entries)

    @property
    def discovery_observations(
        self,
    ) -> tuple[observer.HeldoutObservedJointTransitionV2, ...]:
        return tuple(
            item.observation
            for item in self.entries
            if item.observation.lane is observer.ObservationLaneV2.DISCOVERY
        )

    @property
    def validation_observations(
        self,
    ) -> tuple[observer.HeldoutObservedJointTransitionV2, ...]:
        return tuple(
            item.observation
            for item in self.entries
            if item.observation.lane is observer.ObservationLaneV2.VALIDATION
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_linear_row_transcript.v1",
            "schema_version": SCHEMA_VERSION,
            "anchor_id": self.anchor_id,
            "context_id": self.context_id,
            "row_binding_id": self.row_binding_id,
            "catalogue_id": self.catalogue_id,
            "arm": self.arm,
            "action": list(self.action),
            "purpose": self.purpose.value,
            "checkpoint": self.checkpoint,
            "predecessor_transcript_id": self.predecessor_transcript_id,
            "sequence_offset": self.sequence_offset,
            "entry_ids": [item.entry_id for item in self.entries],
            "discovery_work_id": (
                None
                if self.discovery_work is None
                else self.discovery_work.work_id
            ),
            "validation_work_id": self.validation_work.work_id,
            "cumulative_sequence_count": self.cumulative_sequence_count,
            "append_only": True,
            "replacement_allowed": False,
            "source_prior_used_in_confidence": False,
        }

    @property
    def transcript_id(self) -> str:
        return self._transcript_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "entries": [item.to_document() for item in self.entries],
            "discovery_work": (
                None
                if self.discovery_work is None
                else self.discovery_work.to_document()
            ),
            "validation_work": self.validation_work.to_document(),
            "transcript_id": self.transcript_id,
        }


def _descriptor_id(
    observation: observer.HeldoutObservedJointTransitionV2,
) -> str:
    return descriptors.RecordedTransitionDescriptorV2(
        observation.next_state,
        observation.realized_row_reward,
        observation.failure,
        observation.terminal,
    ).descriptor_id


_ACQUISITION_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredTargetRowAcquisitionV1:
    _minting_capability: object
    authority_chain_id: str
    anchor_id: str
    final_preregistration_id: str
    context: prereg.HeldoutPublicGraphContextV2
    catalogue: observer.HeldoutLegalActionCatalogueV2
    action: tuple[int, int, int]
    arm: str
    purpose: RegisteredTargetAcquisitionPurposeV1
    checkpoint: int
    frontier: RegisteredAcquisitionFrontierV1 | None
    parent: "RegisteredTargetRowAcquisitionV1 | None"
    discovery_support_epoch_chain: (
        observer.HeldoutSupportEpochChainV2 | None
    )
    validation_support_epoch_chain: observer.HeldoutSupportEpochChainV2
    transcript: RegisteredLinearRowTranscriptV1
    support_descriptor_ids: tuple[str, ...]
    validation_novel_descriptor_ids: tuple[str, ...]
    _acquisition_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.authority_chain_id, "acquisition authority chain"),
            (self.anchor_id, "acquisition anchor"),
            (
                self.final_preregistration_id,
                "acquisition final preregistration",
            ),
        ):
            _cid(value, label)
        if (
            self._minting_capability is not _ACQUISITION_MINTING_SENTINEL
            or type(self.context)
            is not prereg.HeldoutPublicGraphContextV2
            or self.context
            not in prereg.registered_heldout_public_contexts_v2()
            or type(self.catalogue)
            is not observer.HeldoutLegalActionCatalogueV2
            or self.catalogue.context_id != self.context.context_id
            or self.action not in self.catalogue.actions
            or self.arm not in prereg.ARM_ORDER[:-1]
            or type(self.purpose)
            is not RegisteredTargetAcquisitionPurposeV1
            or self.checkpoint != self.purpose.required_checkpoint
            or type(self.validation_support_epoch_chain)
            is not observer.HeldoutSupportEpochChainV2
            or type(self.transcript) is not RegisteredLinearRowTranscriptV1
            or self.transcript.anchor_id != self.anchor_id
            or self.transcript.context_id != self.context.context_id
            or self.transcript.catalogue_id != self.catalogue.catalogue_id
            or self.transcript.action != self.action
            or self.transcript.arm != self.arm
            or self.transcript.purpose is not self.purpose
            or self.transcript.checkpoint != self.checkpoint
        ):
            raise V072RegisteredTargetConfidenceAccumulatorViolation(
                "registered row acquisition is unminted or identity-stale"
            )
        if self.purpose.is_promotion:
            if (
                type(self.parent) is not RegisteredTargetRowAcquisitionV1
                or self.parent.anchor_id != self.anchor_id
                or self.parent.context.context_id != self.context.context_id
                or self.parent.catalogue.catalogue_id
                != self.catalogue.catalogue_id
                or self.parent.action != self.action
                or self.parent.arm != self.arm
                or self.parent.purpose.round_index
                != self.purpose.round_index - 1
                or self.discovery_support_epoch_chain is not None
                or self.transcript.predecessor_transcript_id
                != self.parent.transcript.transcript_id
                or self.transcript.sequence_offset
                != self.parent.transcript.cumulative_sequence_count
            ):
                raise V072RegisteredTargetConfidenceAccumulatorViolation(
                    "promotion did not append to the immediate same-row parent"
                )
            expected_support = tuple(
                sorted(
                    set(self.parent.support_descriptor_ids)
                    | set(self.parent.validation_novel_descriptor_ids)
                )
            )
        else:
            if (
                self.parent is not None
                or type(self.discovery_support_epoch_chain)
                is not observer.HeldoutSupportEpochChainV2
            ):
                raise V072RegisteredTargetConfidenceAccumulatorViolation(
                    "initial/new-child acquisition has a parent or no discovery"
                )
            expected_support = tuple(
                sorted(
                    {
                        _descriptor_id(item)
                        for item in self.transcript.discovery_observations
                    }
                )
            )
        validation_ids = tuple(
            _descriptor_id(item)
            for item in self.transcript.validation_observations
        )
        expected_novel = tuple(
            sorted(set(validation_ids) - set(expected_support))
        )
        if (
            not expected_support
            or len(expected_support)
            > observer.MAX_FROZEN_SUPPORT_MEMBERS_PER_ROW_V2
            or self.support_descriptor_ids != expected_support
            or self.validation_novel_descriptor_ids != expected_novel
            or self.validation_support_epoch_chain.leaf
            .frozen_support_member_ids
            != expected_support
            or self.validation_support_epoch_chain.chain_id
            != self.transcript.validation_observations[
                0
            ].support_epoch_chain_id
            or (
                self.purpose.round_index == 0
                and self.frontier is not None
            )
            or (
                self.purpose.round_index > 0
                and (
                    type(self.frontier)
                    is not RegisteredAcquisitionFrontierV1
                    or self.frontier.anchor_id != self.anchor_id
                    or self.frontier.context_id != self.context.context_id
                    or self.frontier.arm != self.arm
                    or self.frontier.round_index
                    != self.purpose.round_index
                    or self.transcript.row_binding_id
                    not in self.frontier.selected_row_binding_ids
                    or (
                        self.purpose.is_promotion
                        and self.transcript.row_binding_id
                        not in self.frontier.supporting_row_binding_ids
                    )
                    or (
                        self.purpose.is_new_child
                        and self.transcript.row_binding_id
                        in self.frontier.supporting_row_binding_ids
                    )
                )
            )
        ):
            raise V072RegisteredTargetConfidenceAccumulatorViolation(
                "acquisition support/novel/frontier lineage changed"
            )
        object.__setattr__(
            self,
            "_acquisition_id",
            _content_id("acquisition", self._payload()),
        )

    @property
    def round_index(self) -> int:
        return self.purpose.round_index

    @property
    def row_binding_id(self) -> str:
        return self.transcript.row_binding_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_target_row_acquisition.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "final_preregistration_id": self.final_preregistration_id,
            "context_id": self.context.context_id,
            "catalogue_id": self.catalogue.catalogue_id,
            "row_binding_id": self.row_binding_id,
            "action": list(self.action),
            "arm": self.arm,
            "purpose": self.purpose.value,
            "round_index": self.round_index,
            "checkpoint": self.checkpoint,
            "frontier_id": (
                None if self.frontier is None else self.frontier.frontier_id
            ),
            "parent_acquisition_id": (
                None if self.parent is None else self.parent.acquisition_id
            ),
            "discovery_support_epoch_chain_id": (
                None
                if self.discovery_support_epoch_chain is None
                else self.discovery_support_epoch_chain.chain_id
            ),
            "validation_support_epoch_chain_id": (
                self.validation_support_epoch_chain.chain_id
            ),
            "transcript_id": self.transcript.transcript_id,
            "support_descriptor_ids": list(self.support_descriptor_ids),
            "validation_novel_descriptor_ids": list(
                self.validation_novel_descriptor_ids
            ),
            "append_only": True,
            "fresh_round_two_frontier": self.round_index == 2,
            "replacement_allowed": False,
            "early_stop_allowed": False,
            "source_prior_used_for_proposal_ordering_only": True,
            "source_prior_used_in_confidence": False,
            "caller_observations_accepted": False,
            "caller_law_or_seed_accepted": False,
        }

    @property
    def acquisition_id(self) -> str:
        return self._acquisition_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "frontier": (
                None if self.frontier is None else self.frontier.to_document()
            ),
            "discovery_support_epoch_chain": (
                None
                if self.discovery_support_epoch_chain is None
                else self.discovery_support_epoch_chain.to_document()
            ),
            "validation_support_epoch_chain": (
                self.validation_support_epoch_chain.to_document()
            ),
            "transcript": self.transcript.to_document(),
            "acquisition_id": self.acquisition_id,
        }


def freeze_registered_acquisition_frontier_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    selection_authority: RegisteredAcquisitionSelectionAuthorityV1,
    predecessor: RegisteredAcquisitionFrontierV1 | None,
    supporting_acquisitions: tuple[RegisteredTargetRowAcquisitionV1, ...],
) -> RegisteredAcquisitionFrontierV1:
    """Bind an exact selector authority; arbitrary row/causal IDs are rejected."""

    _verify_authority_gate(authority_chain, anchor)
    if (
        type(selection_authority)
        is not RegisteredAcquisitionSelectionAuthorityV1
        or selection_authority.authority_chain_id
        != authority_chain.chain_id
        or selection_authority.anchor_id != anchor.anchor_id
        or type(supporting_acquisitions) is not tuple
        or not supporting_acquisitions
        or any(
            type(item) is not RegisteredTargetRowAcquisitionV1
            or item.authority_chain_id != authority_chain.chain_id
            or item.anchor_id != anchor.anchor_id
            or item.context.context_id
            != selection_authority.context_id
            or item.arm != selection_authority.arm
            for item in supporting_acquisitions
        )
    ):
        raise RegisteredTargetAcquisitionGateLockedV1(
            "frontier inputs are foreign or rebound",
            access_audit=RegisteredTargetAcquisitionAccessAuditV1(
                authority_chain_verifications=1
            ),
        )
    supporting_ids = tuple(
        sorted({item.acquisition_id for item in supporting_acquisitions})
    )
    supporting_rows = tuple(
        sorted({item.row_binding_id for item in supporting_acquisitions})
    )
    if (
        supporting_ids
        != selection_authority.supporting_acquisition_ids
        or supporting_rows
        != selection_authority.supporting_row_binding_ids
    ):
        raise V072RegisteredTargetConfidenceAccumulatorViolation(
            "selection authority is not derived from actual acquisitions"
        )
    if selection_authority.round_index == 1:
        if predecessor is not None:
            raise V072RegisteredTargetConfidenceAccumulatorViolation(
                "round-1 frontier cannot have a predecessor"
            )
    else:
        if (
            type(predecessor) is not RegisteredAcquisitionFrontierV1
            or predecessor.round_index != 1
            or predecessor.authority_chain_id != authority_chain.chain_id
            or predecessor.anchor_id != anchor.anchor_id
            or predecessor.context_id
            != selection_authority.context_id
            or predecessor.arm != selection_authority.arm
            or selection_authority.predecessor_frontier_id
            != predecessor.frontier_id
            or not set(predecessor.supporting_acquisition_ids)
            < set(supporting_ids)
            or not set(predecessor.supporting_row_binding_ids)
            <= set(supporting_rows)
        ):
            raise V072RegisteredTargetConfidenceAccumulatorViolation(
                "round-2 frontier is not a fresh strict extension"
            )
    return RegisteredAcquisitionFrontierV1(
        _FRONTIER_MINTING_SENTINEL,
        selection_authority,
    )


def mint_registered_acquisition_selection_authority_v1(
    *,
    selector_attestation: Any,
    supporting_acquisitions: tuple[RegisteredTargetRowAcquisitionV1, ...],
) -> RegisteredAcquisitionSelectionAuthorityV1:
    """Mint only from the private independent selector replay attestation."""

    from acfqp import (
        v072_registered_target_selector_independent_verifier_v1
        as independent,
    )

    if (
        type(selector_attestation)
        is not independent.RegisteredSelectorIndependentAttestationV1
        or selector_attestation.selected_candidate_id is None
        or selector_attestation.promotion_row_binding_id is None
        or type(supporting_acquisitions) is not tuple
        or not supporting_acquisitions
        or any(
            type(item) is not RegisteredTargetRowAcquisitionV1
            for item in supporting_acquisitions
        )
    ):
        raise RegisteredTargetAcquisitionGateLockedV1(
            "selection authority requires one exact independent replay",
            access_audit=ZERO_TARGET_ACCESS_AUDIT,
        )
    supporting_ids = tuple(
        sorted({item.acquisition_id for item in supporting_acquisitions})
    )
    supporting_rows = tuple(
        sorted({item.row_binding_id for item in supporting_acquisitions})
    )
    if (
        supporting_ids
        != selector_attestation.supporting_acquisition_ids
        or supporting_rows
        != selector_attestation.supporting_row_binding_ids
        or selector_attestation.selected_row_binding_ids
        != tuple(
            sorted(
                (
                    selector_attestation.promotion_row_binding_id,
                    *selector_attestation.new_child_row_binding_ids,
                )
            )
        )
    ):
        raise RegisteredTargetAcquisitionGateLockedV1(
            "selector replay is rebound to a different acquisition inventory",
            access_audit=ZERO_TARGET_ACCESS_AUDIT,
        )
    return RegisteredAcquisitionSelectionAuthorityV1(
        _SELECTION_AUTHORITY_MINTING_SENTINEL,
        selector_attestation.authority_chain_id,
        selector_attestation.anchor_id,
        selector_attestation.context_id,
        selector_attestation.arm,
        selector_attestation.round_index,
        selector_attestation.predecessor_frontier_id,
        selector_attestation.occurrence_id,
        selector_attestation.failed_audit_id,
        selector_attestation.model_pair_id,
        selector_attestation.model_replay_attestation_id,
        selector_attestation.candidate_inventory_id,
        selector_attestation.proposal_order_id,
        selector_attestation.selected_candidate_id,
        supporting_ids,
        supporting_rows,
        selector_attestation.promotion_row_binding_id,
        selector_attestation.new_child_row_binding_ids,
        selector_attestation.selected_row_binding_ids,
        selector_attestation.selected_draw_upper,
        selector_attestation.cumulative_draw_upper,
        selector_attestation.causal_evidence_id,
    )


def _verify_authority_gate(
    authority_chain: Any,
    anchor: Any,
) -> None:
    if (
        type(authority_chain)
        is not consumer.RegisteredCampaignAuthorityChainV1
        or type(anchor) is not final_authority.V072RemoteMainAnchorV1
        or authority_chain.remote_main_anchor is not anchor
    ):
        raise RegisteredTargetAcquisitionGateLockedV1(
            "registered acquisition requires the exact chain-bound anchor",
            access_audit=ZERO_TARGET_ACCESS_AUDIT,
        )
    try:
        consumer.verify_registered_campaign_authority_chain_v1(
            authority_chain
        )
    except (
        consumer.RegisteredCampaignAuthorityGateLockedV1,
        ValueError,
    ) as error:
        raise RegisteredTargetAcquisitionGateLockedV1(
            "registered acquisition authority chain is stale or rebound",
            access_audit=ZERO_TARGET_ACCESS_AUDIT,
        ) from error


def _validate_preobserver_request(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    context: Any,
    catalogue: Any,
    action: Any,
    arm: Any,
    purpose: Any,
    checkpoint: Any,
    frontier: Any,
    parent: Any,
) -> None:
    _verify_authority_gate(authority_chain, anchor)
    if (
        type(context) is not prereg.HeldoutPublicGraphContextV2
        or context not in prereg.registered_heldout_public_contexts_v2()
        or type(catalogue)
        is not observer.HeldoutLegalActionCatalogueV2
        or catalogue.context_id != context.context_id
        or catalogue.state.failure
        or type(action) is not tuple
        or action not in catalogue.actions
        or arm not in prereg.ARM_ORDER[:-1]
        or type(purpose) is not RegisteredTargetAcquisitionPurposeV1
        or checkpoint != purpose.required_checkpoint
    ):
        raise RegisteredTargetAcquisitionGateLockedV1(
            "registered row request is malformed before observer access",
            access_audit=RegisteredTargetAcquisitionAccessAuditV1(
                authority_chain_verifications=1
            ),
        )
    try:
        expected_catalogue = observer.legal_action_catalogue_v2(
            context,
            catalogue.state,
            catalogue.remaining_horizon,
        )
    except (
        observer.HeldoutGraphTransitionObserverV2InvariantViolation,
        ValueError,
    ) as error:
        raise RegisteredTargetAcquisitionGateLockedV1(
            "registered catalogue is invalid before observer access",
            access_audit=RegisteredTargetAcquisitionAccessAuditV1(
                authority_chain_verifications=1
            ),
        ) from error
    if catalogue.to_document() != expected_catalogue.to_document():
        raise RegisteredTargetAcquisitionGateLockedV1(
            "registered catalogue is incomplete before observer access",
            access_audit=RegisteredTargetAcquisitionAccessAuditV1(
                authority_chain_verifications=1
            ),
        )
    if purpose.round_index == 0:
        valid_lineage = frontier is None and parent is None
    elif purpose.is_promotion:
        valid_lineage = (
            type(frontier) is RegisteredAcquisitionFrontierV1
            and type(parent) is RegisteredTargetRowAcquisitionV1
            and parent.authority_chain_id == authority_chain.chain_id
            and parent.anchor_id == anchor.anchor_id
            and parent.context.context_id == context.context_id
            and parent.catalogue.catalogue_id == catalogue.catalogue_id
            and parent.action == action
            and parent.arm == arm
            and parent.round_index == purpose.round_index - 1
            and parent.acquisition_id
            in frontier.supporting_acquisition_ids
        )
    else:
        valid_lineage = (
            type(frontier) is RegisteredAcquisitionFrontierV1
            and parent is None
        )
    if (
        not valid_lineage
        or (
            type(frontier) is RegisteredAcquisitionFrontierV1
            and (
                frontier.authority_chain_id != authority_chain.chain_id
                or frontier.anchor_id != anchor.anchor_id
                or frontier.context_id != context.context_id
                or frontier.arm != arm
                or frontier.round_index != purpose.round_index
            )
        )
    ):
        raise RegisteredTargetAcquisitionGateLockedV1(
            "registered frontier/parent chain is stale or rebound",
            access_audit=RegisteredTargetAcquisitionAccessAuditV1(
                authority_chain_verifications=1
            ),
        )


def acquire_registered_target_row_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    context: prereg.HeldoutPublicGraphContextV2,
    catalogue: observer.HeldoutLegalActionCatalogueV2,
    action: tuple[int, int, int],
    arm: str,
    purpose: RegisteredTargetAcquisitionPurposeV1,
    checkpoint: int,
    frontier: RegisteredAcquisitionFrontierV1 | None = None,
    parent: RegisteredTargetRowAcquisitionV1 | None = None,
) -> RegisteredTargetRowAcquisitionV1:
    """Own both observer lanes; caller cannot inject samples or counts."""

    _validate_preobserver_request(
        authority_chain=authority_chain,
        anchor=anchor,
        context=context,
        catalogue=catalogue,
        action=action,
        arm=arm,
        purpose=purpose,
        checkpoint=checkpoint,
        frontier=frontier,
        parent=parent,
    )
    row_binding = observer.observation_row_binding_v2(
        context,
        catalogue,
        action,
    )
    if (
        type(frontier) is RegisteredAcquisitionFrontierV1
        and row_binding.row_binding_id
        not in frontier.selected_row_binding_ids
    ):
        raise RegisteredTargetAcquisitionGateLockedV1(
            "requested row is outside the frozen frontier",
            access_audit=RegisteredTargetAcquisitionAccessAuditV1(
                authority_chain_verifications=1
            ),
        )
    if purpose.is_new_child and frontier is not None:
        # A selected new-child row cannot replace an already acquired row.
        if (
            row_binding.row_binding_id
            in frontier.supporting_row_binding_ids
        ):
            raise RegisteredTargetAcquisitionGateLockedV1(
                "new-child acquisition attempts row replacement",
                access_audit=RegisteredTargetAcquisitionAccessAuditV1(
                    authority_chain_verifications=1
                ),
            )
    if (
        purpose.is_promotion
        and frontier is not None
        and row_binding.row_binding_id
        not in frontier.supporting_row_binding_ids
    ):
        raise RegisteredTargetAcquisitionGateLockedV1(
            "promotion row is absent from the acquired support frontier",
            access_audit=RegisteredTargetAcquisitionAccessAuditV1(
                authority_chain_verifications=1
            ),
        )
    discovery_chain: observer.HeldoutSupportEpochChainV2 | None
    discovery_work: observer.HeldoutTransitionStreamWorkV2 | None
    discovery_observations: tuple[
        observer.HeldoutObservedJointTransitionV2, ...
    ]
    if purpose.is_promotion:
        assert parent is not None
        discovery_chain = None
        discovery_work = None
        discovery_observations = ()
        support_ids = tuple(
            sorted(
                set(parent.support_descriptor_ids)
                | set(parent.validation_novel_descriptor_ids)
            )
        )
        parent_chain = parent.validation_support_epoch_chain
        validation_epoch = observer.support_epoch_identity_v2(
            context,
            row_binding,
            arm,
            parent_chain.leaf.epoch_index + 1,
            support_ids,
            parent_chain.leaf,
        )
        validation_chain = observer.support_epoch_chain_v2(
            context,
            row_binding,
            arm,
            (*parent_chain.epochs, validation_epoch),
        )
        sequence_offset = parent.transcript.cumulative_sequence_count
        predecessor_transcript_id = parent.transcript.transcript_id
    else:
        discovery_epoch = observer.support_epoch_identity_v2(
            context,
            row_binding,
            arm,
            0,
        )
        discovery_chain = observer.support_epoch_chain_v2(
            context,
            row_binding,
            arm,
            (discovery_epoch,),
        )
        discovery_stream = (
            observer.open_heldout_target_transition_stream_v2(
                anchor,
                context,
                catalogue,
                action,
                arm,
                observer.ObservationLaneV2.DISCOVERY,
                discovery_chain,
            )
        )
        discovery_observations = tuple(
            discovery_stream.draw()
            for _ in range(purpose.discovery_draw_count)
        )
        discovery_work = discovery_stream.work_snapshot()
        support_ids = tuple(
            sorted({_descriptor_id(item) for item in discovery_observations})
        )
        validation_epoch = observer.support_epoch_identity_v2(
            context,
            row_binding,
            arm,
            1,
            support_ids,
            discovery_epoch,
        )
        validation_chain = observer.support_epoch_chain_v2(
            context,
            row_binding,
            arm,
            (discovery_epoch, validation_epoch),
        )
        sequence_offset = 0
        predecessor_transcript_id = None
    validation_stream = (
        observer.open_heldout_target_transition_stream_v2(
            anchor,
            context,
            catalogue,
            action,
            arm,
            observer.ObservationLaneV2.VALIDATION,
            validation_chain,
        )
    )
    validation_observations = tuple(
        validation_stream.draw() for _ in range(checkpoint)
    )
    validation_work = validation_stream.work_snapshot()
    observations = (*discovery_observations, *validation_observations)
    entries = tuple(
        RegisteredLinearObservationEntryV1(
            sequence_offset + index,
            observation,
        )
        for index, observation in enumerate(observations, start=1)
    )
    transcript = RegisteredLinearRowTranscriptV1(
        anchor.anchor_id,
        context.context_id,
        row_binding.row_binding_id,
        catalogue.catalogue_id,
        arm,
        action,
        purpose,
        checkpoint,
        predecessor_transcript_id,
        sequence_offset,
        entries,
        discovery_work,
        validation_work,
    )
    validation_ids = tuple(
        _descriptor_id(item) for item in validation_observations
    )
    novel_ids = tuple(sorted(set(validation_ids) - set(support_ids)))
    return RegisteredTargetRowAcquisitionV1(
        _ACQUISITION_MINTING_SENTINEL,
        authority_chain.chain_id,
        anchor.anchor_id,
        anchor.claim.final_preregistration_id,
        context,
        catalogue,
        action,
        arm,
        purpose,
        checkpoint,
        frontier,
        parent,
        discovery_chain,
        validation_chain,
        transcript,
        support_ids,
        novel_ids,
    )


@dataclass(frozen=True, slots=True)
class RegisteredConfidenceCoreEventV1:
    event_ordinal: int
    descriptor_id: str | None
    success_count: int
    checkpoint: Any
    _event_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.descriptor_id is not None:
            _cid(self.descriptor_id, "core support descriptor")
        if (
            type(self.event_ordinal) is not int
            or self.event_ordinal < 0
            or type(self.success_count) is not int
            or self.success_count < 0
            or type(self.checkpoint)
            is not AnytimeBernoulliCheckpointV1
            or self.checkpoint.success_count != self.success_count
        ):
            raise V072RegisteredTargetConfidenceAccumulatorViolation(
                "registered confidence core event is malformed"
            )
        object.__setattr__(
            self,
            "_event_id",
            _content_id("core_event", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_confidence_core_event.v1",
            "schema_version": SCHEMA_VERSION,
            "event_ordinal": self.event_ordinal,
            "event_kind": (
                "OTHER" if self.descriptor_id is None else "SUPPORT"
            ),
            "descriptor_id": self.descriptor_id,
            "success_count": self.success_count,
            "checkpoint": self.checkpoint.to_document(),
        }

    @property
    def event_id(self) -> str:
        return self._event_id


@dataclass(frozen=True, slots=True)
class RegisteredConfidenceCountCoreV1:
    purpose: RegisteredTargetAcquisitionPurposeV1
    support_descriptor_ids: tuple[str, ...]
    validation_sequence_digest: str
    checkpoint: int
    events: tuple[RegisteredConfidenceCoreEventV1, ...]
    _core_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(
            self.validation_sequence_digest,
            "confidence validation sequence",
        )
        if (
            type(self.purpose)
            is not RegisteredTargetAcquisitionPurposeV1
            or self.checkpoint != self.purpose.required_checkpoint
            or self.support_descriptor_ids
            != tuple(sorted(set(self.support_descriptor_ids)))
            or not self.support_descriptor_ids
            or type(self.events) is not tuple
            or len(self.events) != len(self.support_descriptor_ids) + 1
            or tuple(item.event_ordinal for item in self.events)
            != tuple(range(len(self.events)))
            or tuple(item.descriptor_id for item in self.events[:-1])
            != self.support_descriptor_ids
            or self.events[-1].descriptor_id is not None
            or sum(item.success_count for item in self.events)
            != self.checkpoint
            or sum(
                item.checkpoint.lower_probability for item in self.events
            )
            > 1
            or sum(
                item.checkpoint.upper_probability for item in self.events
            )
            < 1
        ):
            raise V072RegisteredTargetConfidenceAccumulatorViolation(
                "registered confidence core does not reconcile"
            )
        object.__setattr__(
            self,
            "_core_id",
            _content_id("core", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_confidence_count_core.v1",
            "schema_version": SCHEMA_VERSION,
            "purpose": self.purpose.value,
            "support_descriptor_ids": list(self.support_descriptor_ids),
            "validation_sequence_digest": self.validation_sequence_digest,
            "checkpoint": self.checkpoint,
            "event_ids": [item.event_id for item in self.events],
            "row_epoch_beta": _fdoc(prereg.ROW_EPOCH_BETA),
            "source_prior_used_in_confidence": False,
            "target_local_counts_only": True,
        }

    @property
    def core_id(self) -> str:
        return self._core_id


def derive_registered_confidence_count_core_v1(
    *,
    purpose: RegisteredTargetAcquisitionPurposeV1,
    support_descriptor_ids: tuple[str, ...],
    validation_descriptor_ids: tuple[str, ...],
    checkpoint: int,
) -> RegisteredConfidenceCountCoreV1:
    """Pure count/interval replay; no context, anchor, observer, or prior."""

    if (
        type(purpose) is not RegisteredTargetAcquisitionPurposeV1
        or checkpoint != purpose.required_checkpoint
        or support_descriptor_ids
        != tuple(sorted(set(support_descriptor_ids)))
        or not 1
        <= len(support_descriptor_ids)
        <= observer.MAX_FROZEN_SUPPORT_MEMBERS_PER_ROW_V2
        or type(validation_descriptor_ids) is not tuple
        or len(validation_descriptor_ids) != checkpoint
    ):
        raise V072RegisteredTargetConfidenceAccumulatorViolation(
            "confidence core input is outside the frozen profile"
        )
    for value in (*support_descriptor_ids, *validation_descriptor_ids):
        _cid(value, "confidence descriptor")
    counts = {value: 0 for value in support_descriptor_ids}
    other = 0
    for value in validation_descriptor_ids:
        if value in counts:
            counts[value] += 1
        else:
            other += 1
    event_count = len(support_descriptor_ids) + 1
    profile = SequentialBernoulliProfileV1(
        confidence_alpha=prereg.ROW_EPOCH_BETA / event_count,
        target_half_width=confidence.TARGET_HALF_WIDTH,
        checkpoints=(checkpoint,),
        boundary_grid_bits=confidence.BOUNDARY_GRID_BITS,
    )
    values = tuple(counts[item] for item in support_descriptor_ids) + (
        other,
    )
    events = tuple(
        RegisteredConfidenceCoreEventV1(
            ordinal,
            (
                support_descriptor_ids[ordinal]
                if ordinal < len(support_descriptor_ids)
                else None
            ),
            count,
            build_anytime_bernoulli_checkpoint_v1(
                checkpoint,
                count,
                profile,
            ),
        )
        for ordinal, count in enumerate(values)
    )
    sequence_id = _content_id(
        "sequence",
        {
            "schema": (
                "acfqp.v072_registered_confidence_validation_sequence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "descriptor_ids": list(validation_descriptor_ids),
            "order_preserved": True,
        },
    )
    return RegisteredConfidenceCountCoreV1(
        purpose,
        support_descriptor_ids,
        sequence_id,
        checkpoint,
        events,
    )


__all__ = [
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_INCREMENTAL_FRONTIER_SELECTION_AUTHORITY_STATUS",
    "REGISTERED_OBSERVATIONS_GENERATED_PRE_ANCHOR",
    "RegisteredAcquisitionFrontierV1",
    "RegisteredAcquisitionSelectionAuthorityV1",
    "RegisteredConfidenceCoreEventV1",
    "RegisteredConfidenceCountCoreV1",
    "RegisteredLinearObservationEntryV1",
    "RegisteredLinearRowTranscriptV1",
    "RegisteredTargetAcquisitionAccessAuditV1",
    "RegisteredTargetAcquisitionGateLockedV1",
    "RegisteredTargetAcquisitionPurposeV1",
    "RegisteredTargetRowAcquisitionV1",
    "SCHEMA_VERSION",
    "V072RegisteredTargetConfidenceAccumulatorViolation",
    "ZERO_TARGET_ACCESS_AUDIT",
    "acquire_registered_target_row_v1",
    "derive_registered_confidence_count_core_v1",
    "freeze_registered_acquisition_frontier_v1",
    "mint_registered_acquisition_selection_authority_v1",
]
