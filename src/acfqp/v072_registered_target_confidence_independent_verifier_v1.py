"""Independent target-tape replay for registered V0-072 confidence rows.

This module never calls the acquisition producer or its count core.  It opens
fresh anchor-gated streams, replays each lane linearly once, reconstructs the
support/OTHER Bernoulli intervals with exact arithmetic, adapts public outcome
semantics into cold H=2 row evidence, and mints the only attestation accepted
by the registered confidence-projection authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.sequential_bernoulli_acquisition_v1 import (
    SequentialBernoulliProfileV1,
    build_anytime_bernoulli_checkpoint_v1,
)
from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import partial_support_confidence_v2 as confidence
from acfqp import public_novel_child_cardinality_authority_v2 as descriptors
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_cold_h2_closure_v1 as cold
from acfqp import v072_confidence_row_projection_v1 as projection
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import v072_heldout_public_graph_adapter_v1 as public_adapter
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import (
    v072_registered_target_confidence_accumulator_v1 as accumulator,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_registered_target_confidence_independent_verifier_v1"

_PRODUCER_DOMAINS = {
    "entry": "acfqp:v072-registered-linear-observation-entry:v1",
    "transcript": "acfqp:v072-registered-linear-row-transcript:v1",
    "acquisition": "acfqp:v072-registered-target-row-acquisition:v1",
}
_DOMAINS = {
    "validation_prefix": (
        "acfqp:v072-registered-validation-prefix-replay:v1"
    ),
    "confidence_snapshot": (
        "acfqp:v072-registered-confidence-snapshot-replay:v1"
    ),
    "replay_core": "acfqp:v072-registered-row-replay-core:v1",
    "physical": "acfqp:v072-registered-row-physical-evidence:v1",
    "confidence_event": (
        "acfqp:v072-registered-confidence-event-replay:v1"
    ),
    "attestation": (
        "acfqp:v072-registered-target-confidence-replay-attestation:v1"
    ),
    "bundle": (
        "acfqp:v072-registered-target-confidence-replay-bundle:v1"
    ),
}


class V072RegisteredTargetConfidenceIndependentReplayViolation(ValueError):
    """The authority, transcript, replay, interval, or row binding differs."""


@dataclass(frozen=True, slots=True)
class RegisteredTargetConfidenceReplayAccessAuditV1:
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
            raise V072RegisteredTargetConfidenceIndependentReplayViolation(
                "independent replay audit counters are invalid"
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


ZERO_REPLAY_TARGET_ACCESS_AUDIT = (
    RegisteredTargetConfidenceReplayAccessAuditV1()
)


class RegisteredTargetConfidenceIndependentReplayLockedV1(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        access_audit: RegisteredTargetConfidenceReplayAccessAuditV1,
    ) -> None:
        super().__init__(message)
        self.access_audit = access_audit


def _content_id(
    domain: str,
    payload: Mapping[str, Any],
    *,
    producer: bool = False,
) -> str:
    registry = _PRODUCER_DOMAINS if producer else _DOMAINS
    try:
        encoded = canonical_json_bytes(dict(payload))
        tag = registry[domain].encode("utf-8")
    except (KeyError, TypeError, ValueError) as error:
        raise V072RegisteredTargetConfidenceIndependentReplayViolation(
            str(error)
        ) from error
    return hashlib.sha256(tag + b"\x00" + encoded).hexdigest()


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072RegisteredTargetConfidenceIndependentReplayViolation(
            f"{label} must be one full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V072RegisteredTargetConfidenceIndependentReplayViolation(
            "independent confidence replay requires exact Fraction values"
        )
    return {"numerator": value.numerator, "denominator": value.denominator}


def _recorded_descriptor(
    observation: observer.HeldoutObservedJointTransitionV2,
) -> descriptors.RecordedTransitionDescriptorV2:
    if (
        type(observation)
        is not observer.HeldoutObservedJointTransitionV2
    ):
        raise V072RegisteredTargetConfidenceIndependentReplayViolation(
            "replayed transition has a foreign concrete type"
        )
    return descriptors.RecordedTransitionDescriptorV2(
        observation.next_state,
        observation.realized_row_reward,
        observation.failure,
        observation.terminal,
    )


def _entry_payload(
    global_sequence_index: int,
    observation: observer.HeldoutObservedJointTransitionV2,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_registered_linear_observation_entry.v1",
        "schema_version": SCHEMA_VERSION,
        "global_sequence_index": global_sequence_index,
        "lane": observation.lane.value,
        "lane_sequence_index": observation.accepted_draw_index,
        "observation_id": observation.observation_id,
        "source_prior_used_in_observation": False,
    }


def _transcript_payload(
    value: accumulator.RegisteredLinearRowTranscriptV1,
    entry_ids: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_registered_linear_row_transcript.v1",
        "schema_version": SCHEMA_VERSION,
        "anchor_id": value.anchor_id,
        "context_id": value.context_id,
        "row_binding_id": value.row_binding_id,
        "catalogue_id": value.catalogue_id,
        "arm": value.arm,
        "action": list(value.action),
        "purpose": value.purpose.value,
        "checkpoint": value.checkpoint,
        "predecessor_transcript_id": value.predecessor_transcript_id,
        "sequence_offset": value.sequence_offset,
        "entry_ids": list(entry_ids),
        "discovery_work_id": (
            None
            if value.discovery_work is None
            else value.discovery_work.work_id
        ),
        "validation_work_id": value.validation_work.work_id,
        "cumulative_sequence_count": (
            value.sequence_offset + len(entry_ids)
        ),
        "append_only": True,
        "replacement_allowed": False,
        "source_prior_used_in_confidence": False,
    }


def _acquisition_payload(
    value: accumulator.RegisteredTargetRowAcquisitionV1,
    transcript_id: str,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_registered_target_row_acquisition.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": (
            accumulator.PROPOSED_CONTRACT_VERSION
        ),
        "profile_key": accumulator.PROFILE_KEY,
        "authority_chain_id": value.authority_chain_id,
        "anchor_id": value.anchor_id,
        "final_preregistration_id": value.final_preregistration_id,
        "context_id": value.context.context_id,
        "catalogue_id": value.catalogue.catalogue_id,
        "row_binding_id": value.row_binding_id,
        "action": list(value.action),
        "arm": value.arm,
        "purpose": value.purpose.value,
        "round_index": value.round_index,
        "checkpoint": value.checkpoint,
        "frontier_id": (
            None if value.frontier is None else value.frontier.frontier_id
        ),
        "parent_acquisition_id": (
            None if value.parent is None else value.parent.acquisition_id
        ),
        "discovery_support_epoch_chain_id": (
            None
            if value.discovery_support_epoch_chain is None
            else value.discovery_support_epoch_chain.chain_id
        ),
        "validation_support_epoch_chain_id": (
            value.validation_support_epoch_chain.chain_id
        ),
        "transcript_id": transcript_id,
        "support_descriptor_ids": list(value.support_descriptor_ids),
        "validation_novel_descriptor_ids": list(
            value.validation_novel_descriptor_ids
        ),
        "append_only": True,
        "fresh_round_two_frontier": value.round_index == 2,
        "replacement_allowed": False,
        "early_stop_allowed": False,
        "source_prior_used_for_proposal_ordering_only": True,
        "source_prior_used_in_confidence": False,
        "caller_observations_accepted": False,
        "caller_law_or_seed_accepted": False,
    }


def _preflight(
    *,
    authority_chain: Any,
    anchor: Any,
    acquisition: Any,
    parent_replay: Any,
) -> None:
    """Reject all identity/type/rebinding failures before opening a stream."""

    if (
        type(authority_chain)
        is not consumer.RegisteredCampaignAuthorityChainV1
        or type(anchor) is not final_authority.V072RemoteMainAnchorV1
        or authority_chain.remote_main_anchor is not anchor
        or type(acquisition)
        is not accumulator.RegisteredTargetRowAcquisitionV1
    ):
        raise RegisteredTargetConfidenceIndependentReplayLockedV1(
            "independent replay requires one exact chain/anchor/acquisition",
            access_audit=ZERO_REPLAY_TARGET_ACCESS_AUDIT,
        )
    try:
        (
            _source_recipe_id,
            _manifest_id,
            final_id,
            anchor_id,
            _semantic_attestation_id,
        ) = consumer.verify_registered_campaign_authority_chain_v1(
            authority_chain
        )
    except (
        consumer.RegisteredCampaignAuthorityGateLockedV1,
        ValueError,
    ) as error:
        raise RegisteredTargetConfidenceIndependentReplayLockedV1(
            "independent replay authority chain is stale",
            access_audit=ZERO_REPLAY_TARGET_ACCESS_AUDIT,
        ) from error
    try:
        expected_catalogue = observer.legal_action_catalogue_v2(
            acquisition.context,
            acquisition.catalogue.state,
            acquisition.catalogue.remaining_horizon,
        )
    except (ValueError, TypeError) as error:
        raise RegisteredTargetConfidenceIndependentReplayLockedV1(
            "independent replay catalogue is invalid",
            access_audit=RegisteredTargetConfidenceReplayAccessAuditV1(
                authority_chain_verifications=1
            ),
        ) from error
    transcript = acquisition.transcript
    if (
        acquisition.authority_chain_id != authority_chain.chain_id
        or acquisition.anchor_id != anchor_id
        or acquisition.anchor_id != anchor.anchor_id
        or acquisition.final_preregistration_id != final_id
        or acquisition.context
        not in prereg.registered_heldout_public_contexts_v2()
        or acquisition.catalogue.to_document()
        != expected_catalogue.to_document()
        or acquisition.action not in acquisition.catalogue.actions
        or acquisition.arm not in prereg.ARM_ORDER[:-1]
        or type(transcript)
        is not accumulator.RegisteredLinearRowTranscriptV1
        or type(transcript.entries) is not tuple
    ):
        raise RegisteredTargetConfidenceIndependentReplayLockedV1(
            "independent replay acquisition identity is rebound",
            access_audit=RegisteredTargetConfidenceReplayAccessAuditV1(
                authority_chain_verifications=1
            ),
        )
    recomputed_entry_ids = tuple(
        _content_id(
            "entry",
            _entry_payload(
                transcript.sequence_offset + ordinal,
                item.observation,
            ),
            producer=True,
        )
        for ordinal, item in enumerate(transcript.entries, start=1)
    )
    transcript_id = _content_id(
        "transcript",
        _transcript_payload(transcript, recomputed_entry_ids),
        producer=True,
    )
    acquisition_id = _content_id(
        "acquisition",
        _acquisition_payload(acquisition, transcript_id),
        producer=True,
    )
    if (
        tuple(item.entry_id for item in transcript.entries)
        != recomputed_entry_ids
        or transcript.transcript_id != transcript_id
        or acquisition.acquisition_id != acquisition_id
    ):
        raise RegisteredTargetConfidenceIndependentReplayLockedV1(
            "cached producer content identity fails independent preflight",
            access_audit=RegisteredTargetConfidenceReplayAccessAuditV1(
                authority_chain_verifications=1
            ),
        )
    if acquisition.purpose.is_promotion:
        if (
            type(parent_replay)
            is not RegisteredTargetConfidenceReplayBundleV1
            or type(acquisition.parent)
            is not accumulator.RegisteredTargetRowAcquisitionV1
            or parent_replay.acquisition_id
            != acquisition.parent.acquisition_id
            or parent_replay.anchor_id != anchor.anchor_id
            or parent_replay.authority_chain_id
            != authority_chain.chain_id
            or parent_replay.row_evidence.context_id
            != acquisition.context.context_id
            or parent_replay.row_evidence.action.semantic_action_id
            != acquisition.row_binding_id
        ):
            raise RegisteredTargetConfidenceIndependentReplayLockedV1(
                "promotion lacks the exact independently replayed parent",
                access_audit=RegisteredTargetConfidenceReplayAccessAuditV1(
                    authority_chain_verifications=1
                ),
            )
    elif parent_replay is not None or acquisition.parent is not None:
        raise RegisteredTargetConfidenceIndependentReplayLockedV1(
            "initial/new-child replay cannot borrow a parent transcript",
            access_audit=RegisteredTargetConfidenceReplayAccessAuditV1(
                authority_chain_verifications=1
            ),
        )


def _compare_replayed_transcript(
    acquisition: accumulator.RegisteredTargetRowAcquisitionV1,
    observations: tuple[observer.HeldoutObservedJointTransitionV2, ...],
) -> tuple[str, ...]:
    transcript = acquisition.transcript
    if len(observations) != len(transcript.entries):
        raise V072RegisteredTargetConfidenceIndependentReplayViolation(
            "replayed transcript length differs"
        )
    entry_ids = []
    for ordinal, (expected, claimed) in enumerate(
        zip(observations, transcript.entries),
        start=1,
    ):
        global_index = transcript.sequence_offset + ordinal
        entry_id = _content_id(
            "entry",
            _entry_payload(global_index, expected),
            producer=True,
        )
        if (
            claimed.global_sequence_index != global_index
            or expected.to_document()
            != claimed.observation.to_document()
            or claimed.entry_id != entry_id
        ):
            raise V072RegisteredTargetConfidenceIndependentReplayViolation(
                "linear transcript has a gap, reorder, or changed observation"
            )
        entry_ids.append(entry_id)
    transcript_id = _content_id(
        "transcript",
        _transcript_payload(transcript, tuple(entry_ids)),
        producer=True,
    )
    if transcript_id != transcript.transcript_id:
        raise V072RegisteredTargetConfidenceIndependentReplayViolation(
            "linear transcript content identity differs"
        )
    return tuple(entry_ids)


def _cold_descriptor(
    observation: observer.HeldoutObservedJointTransitionV2,
    adapter: public_adapter.HeldoutPublicGraphColdClosureAdapterV1,
) -> cold.ColdOutcomeDescriptorV1:
    recorded = _recorded_descriptor(observation)
    successor = (
        None
        if observation.failure or observation.terminal
        else adapter.adapt_public_state_v1(
            observation.next_state,
            observation.remaining_horizon - 1,
        )
    )
    return cold.ColdOutcomeDescriptorV1(
        recorded.descriptor_id,
        failure=observation.failure,
        terminal=observation.terminal,
        successor_state=successor,
        document=recorded.to_document(),
    )


def _exact_event_checkpoints(
    support_ids: tuple[str, ...],
    validation_ids: tuple[str, ...],
    checkpoint: int,
) -> tuple[
    tuple[int, ...],
    tuple[tuple[Fraction, Fraction, Mapping[str, Any]], ...],
]:
    counts = {item: 0 for item in support_ids}
    other = 0
    for item in validation_ids:
        if item in counts:
            counts[item] += 1
        else:
            other += 1
    event_counts = tuple(counts[item] for item in support_ids) + (other,)
    profile = SequentialBernoulliProfileV1(
        confidence_alpha=prereg.ROW_EPOCH_BETA / len(event_counts),
        target_half_width=confidence.TARGET_HALF_WIDTH,
        checkpoints=(checkpoint,),
        boundary_grid_bits=confidence.BOUNDARY_GRID_BITS,
    )
    checkpoints = tuple(
        build_anytime_bernoulli_checkpoint_v1(
            checkpoint,
            count,
            profile,
        )
        for count in event_counts
    )
    intervals = tuple(
        (
            item.lower_probability,
            item.upper_probability,
            item.to_document(),
        )
        for item in checkpoints
    )
    if (
        sum(event_counts) != checkpoint
        or sum(item[0] for item in intervals) > 1
        or sum(item[1] for item in intervals) < 1
    ):
        raise V072RegisteredTargetConfidenceIndependentReplayViolation(
            "independently replayed support-plus-OTHER intervals do not "
            "reconcile as an interval simplex"
        )
    return event_counts, intervals


def replay_registered_confidence_count_intervals_core_v1(
    *,
    support_descriptor_ids: tuple[str, ...],
    validation_descriptor_ids: tuple[str, ...],
    checkpoint: int,
) -> tuple[
    tuple[int, ...],
    tuple[tuple[Fraction, Fraction, Mapping[str, Any]], ...],
]:
    """Target-free independent count/interval core for disjoint test data."""

    if (
        type(support_descriptor_ids) is not tuple
        or support_descriptor_ids
        != tuple(sorted(set(support_descriptor_ids)))
        or not 1
        <= len(support_descriptor_ids)
        <= observer.MAX_FROZEN_SUPPORT_MEMBERS_PER_ROW_V2
        or type(validation_descriptor_ids) is not tuple
        or type(checkpoint) is not int
        or checkpoint not in (2_048, 8_192)
        or len(validation_descriptor_ids) != checkpoint
    ):
        raise V072RegisteredTargetConfidenceIndependentReplayViolation(
            "independent count replay input is outside the frozen profile"
        )
    for value in (*support_descriptor_ids, *validation_descriptor_ids):
        _cid(value, "independent count descriptor")
    return _exact_event_checkpoints(
        support_descriptor_ids,
        validation_descriptor_ids,
        checkpoint,
    )


_ATTESTATION_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredTargetConfidenceIndependentReplayAttestationV1:
    _minting_capability: object
    authority_chain_id: str
    anchor_id: str
    final_preregistration_id: str
    acquisition_id: str
    transcript_id: str
    discovery_transcript_id: str
    validation_prefix_id: str
    row_evidence_id: str
    support_epoch_id: str
    support_semantic_descriptor_ids: tuple[str, ...]
    support_descriptor_record_ids: tuple[str, ...]
    validation_novel_descriptor_record_ids: tuple[str, ...]
    event_ids: tuple[str, ...]
    event_success_counts: tuple[int, ...]
    event_probability_intervals: tuple[
        tuple[Fraction, Fraction], ...
    ]
    selected_checkpoint_draw_count: int
    replayed_stream_opens: int
    replayed_draw_calls: int
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.authority_chain_id,
            self.anchor_id,
            self.final_preregistration_id,
            self.acquisition_id,
            self.transcript_id,
            self.discovery_transcript_id,
            self.validation_prefix_id,
            self.row_evidence_id,
            self.support_epoch_id,
            *self.support_semantic_descriptor_ids,
            *self.support_descriptor_record_ids,
            *self.validation_novel_descriptor_record_ids,
            *self.event_ids,
        ):
            _cid(value, "replay attestation identity")
        if (
            self._minting_capability is not _ATTESTATION_MINTING_SENTINEL
            or self.support_semantic_descriptor_ids
            != tuple(sorted(set(self.support_semantic_descriptor_ids)))
            or self.support_descriptor_record_ids
            != tuple(sorted(set(self.support_descriptor_record_ids)))
            or len(self.support_semantic_descriptor_ids)
            != len(self.support_descriptor_record_ids)
            or self.validation_novel_descriptor_record_ids
            != tuple(
                sorted(set(self.validation_novel_descriptor_record_ids))
            )
            or len(self.event_ids)
            != len(self.support_descriptor_record_ids) + 1
            or len(self.event_success_counts) != len(self.event_ids)
            or len(self.event_probability_intervals)
            != len(self.event_ids)
            or any(
                type(item) is not int or item < 0
                for item in self.event_success_counts
            )
            or sum(self.event_success_counts)
            != self.selected_checkpoint_draw_count
            or any(
                type(lower) is not Fraction
                or type(upper) is not Fraction
                or not 0 <= lower <= upper <= 1
                for lower, upper in self.event_probability_intervals
            )
            or sum(
                lower
                for lower, _upper in self.event_probability_intervals
            )
            > 1
            or sum(
                upper
                for _lower, upper in self.event_probability_intervals
            )
            < 1
            or self.selected_checkpoint_draw_count
            not in (2_048, 8_192)
            or self.replayed_stream_opens not in (1, 2)
            or self.replayed_draw_calls
            not in (
                2_048,
                2_112,
                8_256,
            )
        ):
            raise V072RegisteredTargetConfidenceIndependentReplayViolation(
                "independent confidence replay attestation is malformed"
            )
        object.__setattr__(
            self,
            "_attestation_id",
            _content_id("attestation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_target_confidence_"
                "independent_replay_attestation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "final_preregistration_id": self.final_preregistration_id,
            "acquisition_id": self.acquisition_id,
            "transcript_id": self.transcript_id,
            "discovery_transcript_id": self.discovery_transcript_id,
            "validation_prefix_id": self.validation_prefix_id,
            "row_evidence_id": self.row_evidence_id,
            "support_epoch_id": self.support_epoch_id,
            "support_semantic_descriptor_ids": list(
                self.support_semantic_descriptor_ids
            ),
            "support_descriptor_record_ids": list(
                self.support_descriptor_record_ids
            ),
            "validation_novel_descriptor_record_ids": list(
                self.validation_novel_descriptor_record_ids
            ),
            "event_ids": list(self.event_ids),
            "event_success_counts": list(self.event_success_counts),
            "event_probability_intervals": [
                {"lower": _fdoc(lower), "upper": _fdoc(upper)}
                for lower, upper in self.event_probability_intervals
            ],
            "selected_checkpoint_draw_count": (
                self.selected_checkpoint_draw_count
            ),
            "replayed_stream_opens": self.replayed_stream_opens,
            "replayed_draw_calls": self.replayed_draw_calls,
            "linear_replay_once_per_stream": True,
            "event_counts_recomputed": True,
            "interval_projection_recomputed": True,
            "content_ids_recomputed": True,
            "source_prior_used_for_ordering_only": True,
            "source_prior_used_in_confidence": False,
            "caller_observations_or_counts_accepted": False,
        }

    @property
    def attestation_id(self) -> str:
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}


_BUNDLE_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredTargetConfidenceReplayBundleV1:
    _minting_capability: object
    acquisition: accumulator.RegisteredTargetRowAcquisitionV1
    attestation: RegisteredTargetConfidenceIndependentReplayAttestationV1
    row_evidence: cold.ColdRowEvidenceV1
    event_intervals: tuple[
        projection.RegisteredConfidenceEventIntervalV1, ...
    ]
    confidence_authority: (
        projection.RegisteredTargetConfidenceProjectionAuthorityV1
    )
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._minting_capability is not _BUNDLE_MINTING_SENTINEL
            or type(self.acquisition)
            is not accumulator.RegisteredTargetRowAcquisitionV1
            or type(self.attestation)
            is not RegisteredTargetConfidenceIndependentReplayAttestationV1
            or type(self.row_evidence) is not cold.ColdRowEvidenceV1
            or type(self.event_intervals) is not tuple
            or any(
                type(item)
                is not projection.RegisteredConfidenceEventIntervalV1
                for item in self.event_intervals
            )
            or type(self.confidence_authority)
            is not projection.RegisteredTargetConfidenceProjectionAuthorityV1
            or self.attestation.acquisition_id
            != self.acquisition.acquisition_id
            or self.attestation.row_evidence_id
            != self.row_evidence.row_evidence_id
            or self.attestation.event_ids
            != tuple(item.event_id for item in self.event_intervals)
            or self.confidence_authority.row_evidence != self.row_evidence
            or self.confidence_authority.event_intervals
            != self.event_intervals
            or self.confidence_authority.confidence_verification_id
            != self.attestation.attestation_id
        ):
            raise V072RegisteredTargetConfidenceIndependentReplayViolation(
                "registered confidence replay bundle does not reconcile"
            )
        object.__setattr__(
            self,
            "_bundle_id",
            _content_id("bundle", self._payload()),
        )

    @property
    def authority_chain_id(self) -> str:
        return self.attestation.authority_chain_id

    @property
    def anchor_id(self) -> str:
        return self.attestation.anchor_id

    @property
    def acquisition_id(self) -> str:
        return self.acquisition.acquisition_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_target_confidence_replay_bundle.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "acquisition_id": self.acquisition_id,
            "attestation_id": self.attestation.attestation_id,
            "row_evidence_id": self.row_evidence.row_evidence_id,
            "event_ids": [item.event_id for item in self.event_intervals],
            "confidence_authority_id": (
                self.confidence_authority.authority_id
            ),
        }

    @property
    def bundle_id(self) -> str:
        return self._bundle_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "attestation": self.attestation.to_document(),
            "row_evidence": self.row_evidence.to_document(),
            "event_intervals": [
                item.to_document() for item in self.event_intervals
            ],
            "confidence_authority": (
                self.confidence_authority.to_document()
            ),
            "bundle_id": self.bundle_id,
        }


def verify_registered_target_confidence_independently_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    acquisition: accumulator.RegisteredTargetRowAcquisitionV1,
    parent_replay: RegisteredTargetConfidenceReplayBundleV1 | None = None,
) -> RegisteredTargetConfidenceReplayBundleV1:
    """Replay fresh target streams once and mint exact row confidence."""

    _preflight(
        authority_chain=authority_chain,
        anchor=anchor,
        acquisition=acquisition,
        parent_replay=parent_replay,
    )
    context = acquisition.context
    catalogue = acquisition.catalogue
    action = acquisition.action
    arm = acquisition.arm
    row_binding = observer.observation_row_binding_v2(
        context,
        catalogue,
        action,
    )
    discovery_observations: tuple[
        observer.HeldoutObservedJointTransitionV2, ...
    ]
    if acquisition.purpose.is_promotion:
        assert parent_replay is not None
        discovery_observations = ()
        discovery_work = None
        support_ids = tuple(
            sorted(
                {
                    *(
                        item.semantic_descriptor_id
                        for item in parent_replay.row_evidence.discovery_support
                    ),
                    *(
                        item.semantic_descriptor_id
                        for item in parent_replay.row_evidence.validation_novel
                    ),
                }
            )
        )
        parent_chain = acquisition.parent.validation_support_epoch_chain
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
        discovery_transcript_id = (
            parent_replay.attestation.discovery_transcript_id
        )
        stream_opens = 1
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
        if (
            acquisition.discovery_support_epoch_chain is None
            or acquisition.discovery_support_epoch_chain.to_document()
            != discovery_chain.to_document()
        ):
            raise RegisteredTargetConfidenceIndependentReplayLockedV1(
                "discovery support chain differs before observer access",
                access_audit=RegisteredTargetConfidenceReplayAccessAuditV1(
                    authority_chain_verifications=1
                ),
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
            for _ in range(acquisition.purpose.discovery_draw_count)
        )
        discovery_work = discovery_stream.work_snapshot()
        support_ids = tuple(
            sorted(
                {
                    _recorded_descriptor(item).descriptor_id
                    for item in discovery_observations
                }
            )
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
        discovery_transcript_id = acquisition.transcript.transcript_id
        stream_opens = 2
    if (
        validation_chain.to_document()
        != acquisition.validation_support_epoch_chain.to_document()
        or support_ids != acquisition.support_descriptor_ids
    ):
        raise V072RegisteredTargetConfidenceIndependentReplayViolation(
            "independent support replay differs from the validation epoch"
        )
    validation_stream = observer.open_heldout_target_transition_stream_v2(
        anchor,
        context,
        catalogue,
        action,
        arm,
        observer.ObservationLaneV2.VALIDATION,
        validation_chain,
    )
    validation_observations = tuple(
        validation_stream.draw() for _ in range(acquisition.checkpoint)
    )
    validation_work = validation_stream.work_snapshot()
    if (
        discovery_work != acquisition.transcript.discovery_work
        or validation_work != acquisition.transcript.validation_work
    ):
        raise V072RegisteredTargetConfidenceIndependentReplayViolation(
            "replayed native stream work differs"
        )
    all_observations = (
        *discovery_observations,
        *validation_observations,
    )
    _compare_replayed_transcript(acquisition, all_observations)
    validation_ids = tuple(
        _recorded_descriptor(item).descriptor_id
        for item in validation_observations
    )
    novel_ids = tuple(sorted(set(validation_ids) - set(support_ids)))
    if novel_ids != acquisition.validation_novel_descriptor_ids:
        raise V072RegisteredTargetConfidenceIndependentReplayViolation(
            "validation-novel descriptor inventory differs"
        )
    recomputed_acquisition_id = _content_id(
        "acquisition",
        _acquisition_payload(
            acquisition,
            acquisition.transcript.transcript_id,
        ),
        producer=True,
    )
    if recomputed_acquisition_id != acquisition.acquisition_id:
        raise V072RegisteredTargetConfidenceIndependentReplayViolation(
            "acquisition content identity differs after linear replay"
        )

    adapter = public_adapter.HeldoutPublicGraphColdClosureAdapterV1(
        context
    )
    cold_catalogue = adapter.adapt_public_legal_action_catalogue_v1(
        catalogue
    )
    matching_actions = tuple(
        item
        for item in cold_catalogue.actions
        if item.semantic_action_id == row_binding.row_binding_id
    )
    if len(matching_actions) != 1:
        raise V072RegisteredTargetConfidenceIndependentReplayViolation(
            "public action did not map to one cold semantic action"
        )
    if acquisition.purpose.is_promotion:
        assert parent_replay is not None
        support_descriptors = tuple(
            sorted(
                (
                    *parent_replay.row_evidence.discovery_support,
                    *parent_replay.row_evidence.validation_novel,
                ),
                key=lambda item: item.descriptor_record_id,
            )
        )
    else:
        representative_by_id: dict[
            str, observer.HeldoutObservedJointTransitionV2
        ] = {}
        for item in discovery_observations:
            representative_by_id.setdefault(
                _recorded_descriptor(item).descriptor_id,
                item,
            )
        support_descriptors = tuple(
            sorted(
                (
                    _cold_descriptor(
                        representative_by_id[descriptor_id],
                        adapter,
                    )
                    for descriptor_id in support_ids
                ),
                key=lambda item: item.descriptor_record_id,
            )
        )
    novel_representative_by_id: dict[
        str, observer.HeldoutObservedJointTransitionV2
    ] = {}
    for item in validation_observations:
        descriptor_id = _recorded_descriptor(item).descriptor_id
        if descriptor_id in novel_ids:
            novel_representative_by_id.setdefault(descriptor_id, item)
    novel_descriptors = tuple(
        sorted(
            (
                _cold_descriptor(
                    novel_representative_by_id[descriptor_id],
                    adapter,
                )
                for descriptor_id in novel_ids
            ),
            key=lambda item: item.descriptor_record_id,
        )
    )

    event_counts_by_semantic, intervals_by_semantic = (
        _exact_event_checkpoints(
            support_ids,
            validation_ids,
            acquisition.checkpoint,
        )
    )
    interval_by_semantic = {
        descriptor_id: (
            event_counts_by_semantic[ordinal],
            intervals_by_semantic[ordinal],
        )
        for ordinal, descriptor_id in enumerate(support_ids)
    }
    other_count = event_counts_by_semantic[-1]
    other_interval = intervals_by_semantic[-1]
    validation_prefix_id = _content_id(
        "validation_prefix",
        {
            "schema": (
                "acfqp.v072_registered_validation_prefix_replay.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "acquisition_id": acquisition.acquisition_id,
            "checkpoint": acquisition.checkpoint,
            "observation_ids": [
                item.observation_id for item in validation_observations
            ],
            "descriptor_ids": list(validation_ids),
            "order_preserved": True,
        },
    )
    replay_core_id = _content_id(
        "replay_core",
        {
            "schema": "acfqp.v072_registered_row_replay_core.v1",
            "schema_version": SCHEMA_VERSION,
            "acquisition_id": acquisition.acquisition_id,
            "transcript_id": acquisition.transcript.transcript_id,
            "support_epoch_chain_id": validation_chain.chain_id,
            "support_descriptor_ids": list(support_ids),
            "validation_novel_descriptor_ids": list(novel_ids),
            "validation_prefix_id": validation_prefix_id,
            "discovery_work_id": (
                None if discovery_work is None else discovery_work.work_id
            ),
            "validation_work_id": validation_work.work_id,
            "linear_replay_once_per_stream": True,
        },
    )
    confidence_snapshot_id = _content_id(
        "confidence_snapshot",
        {
            "schema": (
                "acfqp.v072_registered_confidence_snapshot_replay.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "replay_core_id": replay_core_id,
            "checkpoint": acquisition.checkpoint,
            "support_descriptor_ids": list(support_ids),
            "event_counts": list(event_counts_by_semantic),
            "event_checkpoints": [
                item[2] for item in intervals_by_semantic
            ],
            "row_epoch_beta": _fdoc(prereg.ROW_EPOCH_BETA),
            "source_prior_used_in_confidence": False,
        },
    )
    physical_evidence_id = _content_id(
        "physical",
        {
            "schema": (
                "acfqp.v072_registered_row_physical_evidence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "anchor_id": anchor.anchor_id,
            "acquisition_id": acquisition.acquisition_id,
            "observation_ids": [
                item.observation_id for item in all_observations
            ],
            "raw_commitment_ids": [
                item.raw_commitment.commitment_id
                for item in all_observations
            ],
            "discovery_work_id": (
                None if discovery_work is None else discovery_work.work_id
            ),
            "validation_work_id": validation_work.work_id,
            "route_independent": True,
        },
    )
    if acquisition.purpose.is_promotion:
        cold_purpose = cold.ColdRowAcquisitionPurposeV1.INCREMENTAL_PROMOTION
    elif acquisition.purpose.is_new_child:
        cold_purpose = cold.ColdRowAcquisitionPurposeV1.INCREMENTAL_NEW_CHILD
    else:
        cold_purpose = cold.ColdRowAcquisitionPurposeV1.COLD_INITIAL
    native_work = cold.ColdRowNativeWorkV1(
        acquisition_purpose=cold_purpose,
        discovery_draws=len(discovery_observations),
        validation_draws=len(validation_observations),
        discovery_random_word_calls=(
            0
            if discovery_work is None
            else discovery_work.random_word_calls
        ),
        validation_random_word_calls=validation_work.random_word_calls,
        discovery_rejections=(
            0 if discovery_work is None else discovery_work.rejection_count
        ),
        validation_rejections=validation_work.rejection_count,
    )
    row_evidence = cold.ColdRowEvidenceV1(
        context.context_id,
        cold_catalogue.state,
        catalogue.remaining_horizon,
        matching_actions[0],
        support_descriptors,
        novel_descriptors,
        validation_chain.leaf.epoch_id,
        confidence_snapshot_id,
        replay_core_id,
        physical_evidence_id,
        native_work,
    )

    event_intervals_list = []
    ordered_counts = []
    ordered_intervals = []
    for ordinal, item in enumerate(support_descriptors):
        count, (lower, upper, checkpoint_document) = (
            interval_by_semantic[item.semantic_descriptor_id]
        )
        confidence_event_id = _content_id(
            "confidence_event",
            {
                "schema": (
                    "acfqp.v072_registered_confidence_event_replay.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "confidence_snapshot_id": confidence_snapshot_id,
                "event_ordinal": ordinal,
                "event_kind": "SUPPORT",
                "semantic_descriptor_id": item.semantic_descriptor_id,
                "descriptor_record_id": item.descriptor_record_id,
                "success_count": count,
                "checkpoint": checkpoint_document,
            },
        )
        event_intervals_list.append(
            projection.RegisteredConfidenceEventIntervalV1(
                confidence_event_id,
                ordinal,
                projection.RegisteredConfidenceEventKindV1.SUPPORT,
                item.descriptor_record_id,
                lower,
                upper,
            )
        )
        ordered_counts.append(count)
        ordered_intervals.append((lower, upper))
    other_ordinal = len(support_descriptors)
    other_confidence_event_id = _content_id(
        "confidence_event",
        {
            "schema": (
                "acfqp.v072_registered_confidence_event_replay.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "confidence_snapshot_id": confidence_snapshot_id,
            "event_ordinal": other_ordinal,
            "event_kind": "OTHER",
            "semantic_descriptor_id": None,
            "descriptor_record_id": None,
            "success_count": other_count,
            "checkpoint": other_interval[2],
        },
    )
    event_intervals_list.append(
        projection.RegisteredConfidenceEventIntervalV1(
            other_confidence_event_id,
            other_ordinal,
            projection.RegisteredConfidenceEventKindV1.OTHER,
            None,
            other_interval[0],
            other_interval[1],
        )
    )
    ordered_counts.append(other_count)
    ordered_intervals.append((other_interval[0], other_interval[1]))
    event_intervals = tuple(event_intervals_list)
    replayed_draw_calls = len(all_observations)
    attestation = (
        RegisteredTargetConfidenceIndependentReplayAttestationV1(
            _ATTESTATION_MINTING_SENTINEL,
            authority_chain.chain_id,
            anchor.anchor_id,
            acquisition.final_preregistration_id,
            acquisition.acquisition_id,
            acquisition.transcript.transcript_id,
            discovery_transcript_id,
            validation_prefix_id,
            row_evidence.row_evidence_id,
            validation_chain.leaf.epoch_id,
            support_ids,
            tuple(
                item.descriptor_record_id for item in support_descriptors
            ),
            tuple(
                item.descriptor_record_id for item in novel_descriptors
            ),
            tuple(item.event_id for item in event_intervals),
            tuple(ordered_counts),
            tuple(ordered_intervals),
            acquisition.checkpoint,
            stream_opens,
            replayed_draw_calls,
        )
    )
    confidence_authority = (
        projection.mint_registered_target_confidence_projection_authority_v1(
            replay_attestation=attestation,
            row_evidence=row_evidence,
            event_intervals=event_intervals,
        )
    )
    return RegisteredTargetConfidenceReplayBundleV1(
        _BUNDLE_MINTING_SENTINEL,
        acquisition,
        attestation,
        row_evidence,
        event_intervals,
        confidence_authority,
    )


__all__ = [
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "RegisteredTargetConfidenceIndependentReplayAttestationV1",
    "RegisteredTargetConfidenceIndependentReplayLockedV1",
    "RegisteredTargetConfidenceReplayAccessAuditV1",
    "RegisteredTargetConfidenceReplayBundleV1",
    "SCHEMA_VERSION",
    "V072RegisteredTargetConfidenceIndependentReplayViolation",
    "ZERO_REPLAY_TARGET_ACCESS_AUDIT",
    "replay_registered_confidence_count_intervals_core_v1",
    "verify_registered_target_confidence_independently_v1",
]
