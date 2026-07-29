"""Independent whole-artifact replay for registered incremental epochs.

The verifier consumes an exact prior epoch, an already independently verified
selector closure, and one claimed incremental epoch.  It never invokes the
incremental materializer or any held-out transition stream.  Producer
transcripts are replayed from their frozen observations, confidence counts and
intervals are reconstructed with exact arithmetic, complete history and
latest-row semantics are checked, and the closure/model independent verifiers
are run again before the immutable epoch identity is accepted.

A registration-disjoint verifier at the bottom exercises the same lineage,
history, accounting, and content-identity rules without registered target
access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import public_novel_child_cardinality_authority_v2 as descriptors
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_cold_h2_closure_v1 as cold
from acfqp import (
    v072_cold_h2_closure_independent_verifier_v1 as closure_independent,
)
from acfqp import (
    v072_cold_h2_model_builders_independent_verifier_v1
    as model_independent,
)
from acfqp import v072_confidence_row_projection_v1 as projection
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import v072_heldout_public_graph_adapter_v1 as public_adapter
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import v072_registered_cold_h2_orchestrator_v1 as cold_runtime
from acfqp import (
    v072_registered_incremental_epoch_materializer_v1 as materializer,
)
from acfqp import (
    v072_registered_target_confidence_accumulator_v1 as accumulator,
)
from acfqp import (
    v072_registered_target_confidence_independent_verifier_v1
    as confidence_independent,
)
from acfqp import v072_registered_target_selector_v1 as selector
from acfqp import (
    v072_registered_target_selector_independent_verifier_v1
    as selector_independent,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_registered_incremental_epoch_independent_verifier_v1"

_PRODUCER_DOMAINS = {
    "entry": "acfqp:v072-registered-linear-observation-entry:v1",
    "transcript": "acfqp:v072-registered-linear-row-transcript:v1",
    "acquisition": "acfqp:v072-registered-target-row-acquisition:v1",
}
_REPLAY_DOMAINS = {
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
_VERIFIER_DOMAINS = {
    "access": (
        "acfqp:v072-registered-incremental-epoch-"
        "independent-verifier-access:v1"
    ),
    "attestation": (
        "acfqp:v072-registered-incremental-epoch-"
        "independent-verification:v1"
    ),
    "synthetic_verification": (
        "acfqp:v072-registration-disjoint-incremental-epoch-"
        "independent-verification:v1"
    ),
}


class V072RegisteredIncrementalEpochIndependentVerificationFailure(
    ValueError
):
    """The claimed epoch differs from an independent frozen-artifact replay."""


class RegisteredIncrementalEpochIndependentVerifierLockedV1(RuntimeError):
    """Exact authority/identity inputs were absent before artifact replay."""

    def __init__(
        self,
        message: str,
        *,
        access_audit: "RegisteredIncrementalEpochVerifierAccessAuditV1",
    ) -> None:
        super().__init__(message)
        self.access_audit = access_audit


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            domain.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (TypeError, ValueError) as error:
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            str(error)
        ) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "incremental confidence replay requires exact Fraction values"
        )
    return {"numerator": value.numerator, "denominator": value.denominator}


@dataclass(frozen=True, slots=True)
class RegisteredIncrementalEpochVerifierAccessAuditV1:
    authority_chain_verifications: int = 0
    prior_epoch_replays: int = 0
    selector_closure_replays: int = 0
    producer_artifact_replays: int = 0
    confidence_bundle_replays: int = 0
    history_latest_mapping_replays: int = 0
    closure_independent_replays: int = 0
    model_independent_replays: int = 0
    epoch_identity_replays: int = 0
    observer_stream_opens: int = 0
    observer_draw_calls: int = 0
    evaluation_exact_atom_calls: int = 0

    def __post_init__(self) -> None:
        if any(
            type(getattr(self, name)) is not int
            or getattr(self, name) < 0
            for name in self.__dataclass_fields__
        ):
            raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
                "incremental verifier access counters are malformed"
            )
        if any(
            (
                self.observer_stream_opens,
                self.observer_draw_calls,
                self.evaluation_exact_atom_calls,
            )
        ):
            raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
                "incremental epoch replay attempted target access"
            )

    @property
    def target_access_started(self) -> bool:
        return False

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_incremental_epoch_"
                "independent_verifier_access.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
            },
            "target_access_started": False,
        }

    @property
    def audit_id(self) -> str:
        return _hash(_VERIFIER_DOMAINS["access"], self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "audit_id": self.audit_id}


ZERO_ACCESS_AUDIT = RegisteredIncrementalEpochVerifierAccessAuditV1()


_ATTESTATION_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredIncrementalEpochIndependentAttestationV1:
    _minting_capability: object
    authority_chain_id: str
    anchor_id: str
    occurrence_id: str
    context_id: str
    arm: str
    round_index: int
    predecessor_epoch_id: str
    selector_closure_id: str
    claimed_epoch_id: str
    historical_acquisition_ids: tuple[str, ...]
    active_acquisition_ids: tuple[str, ...]
    closure_id: str
    closure_verification_id: str
    model_pair_id: str
    model_replay_attestation_id: str
    access_audit: RegisteredIncrementalEpochVerifierAccessAuditV1
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.authority_chain_id,
            self.anchor_id,
            self.occurrence_id,
            self.context_id,
            self.predecessor_epoch_id,
            self.selector_closure_id,
            self.claimed_epoch_id,
            *self.historical_acquisition_ids,
            *self.active_acquisition_ids,
            self.closure_id,
            self.closure_verification_id,
            self.model_pair_id,
            self.model_replay_attestation_id,
        ):
            _cid(value, "incremental verification identity")
        if (
            self._minting_capability is not _ATTESTATION_SENTINEL
            or self.arm not in prereg.ARM_ORDER[:-1]
            or self.round_index not in (1, 2)
            or self.historical_acquisition_ids
            != tuple(sorted(set(self.historical_acquisition_ids)))
            or not self.historical_acquisition_ids
            or self.active_acquisition_ids
            != tuple(sorted(set(self.active_acquisition_ids)))
            or not set(self.active_acquisition_ids).issubset(
                self.historical_acquisition_ids
            )
            or type(self.access_audit)
            is not RegisteredIncrementalEpochVerifierAccessAuditV1
            or self.access_audit.target_access_started
        ):
            raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
                "incremental independent attestation is malformed"
            )
        object.__setattr__(
            self,
            "_attestation_id",
            _hash(_VERIFIER_DOMAINS["attestation"], self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_incremental_epoch_"
                "independent_attestation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "round_index": self.round_index,
            "predecessor_epoch_id": self.predecessor_epoch_id,
            "selector_closure_id": self.selector_closure_id,
            "claimed_epoch_id": self.claimed_epoch_id,
            "historical_acquisition_ids": list(
                self.historical_acquisition_ids
            ),
            "active_acquisition_ids": list(self.active_acquisition_ids),
            "closure_id": self.closure_id,
            "closure_verification_id": self.closure_verification_id,
            "model_pair_id": self.model_pair_id,
            "model_replay_attestation_id": (
                self.model_replay_attestation_id
            ),
            "access_audit_id": self.access_audit.audit_id,
            "producer_and_confidence_replayed_from_frozen_bytes": True,
            "full_history_and_latest_row_mapping_replayed": True,
            "closure_and_model_independently_replayed": True,
            "source_prior_used_in_confidence_or_model": False,
            "caller_counts_status_or_rows_accepted": False,
            "observer_stream_opens": 0,
            "observer_draw_calls": 0,
        }

    @property
    def attestation_id(self) -> str:
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}


def _entry_id(
    entry: accumulator.RegisteredLinearObservationEntryV1,
    expected_global_index: int,
) -> str:
    if (
        type(entry) is not accumulator.RegisteredLinearObservationEntryV1
        or entry.global_sequence_index != expected_global_index
        or type(entry.observation)
        is not observer.HeldoutObservedJointTransitionV2
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "producer transcript contains a reordered or foreign entry"
        )
    observation = entry.observation
    result = _hash(
        _PRODUCER_DOMAINS["entry"],
        {
            "schema": (
                "acfqp.v072_registered_linear_observation_entry.v1"
            ),
            "schema_version": accumulator.SCHEMA_VERSION,
            "global_sequence_index": expected_global_index,
            "lane": observation.lane.value,
            "lane_sequence_index": observation.accepted_draw_index,
            "observation_id": observation.observation_id,
            "source_prior_used_in_observation": False,
        },
    )
    if entry.entry_id != result:
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "producer entry content ID does not replay"
        )
    return result


def _transcript_id(
    transcript: accumulator.RegisteredLinearRowTranscriptV1,
) -> str:
    if (
        type(transcript)
        is not accumulator.RegisteredLinearRowTranscriptV1
        or type(transcript.entries) is not tuple
        or not transcript.entries
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "producer transcript has a foreign concrete type"
        )
    entry_ids = tuple(
        _entry_id(
            item,
            transcript.sequence_offset + ordinal,
        )
        for ordinal, item in enumerate(transcript.entries, start=1)
    )
    result = _hash(
        _PRODUCER_DOMAINS["transcript"],
        {
            "schema": "acfqp.v072_registered_linear_row_transcript.v1",
            "schema_version": accumulator.SCHEMA_VERSION,
            "anchor_id": transcript.anchor_id,
            "context_id": transcript.context_id,
            "row_binding_id": transcript.row_binding_id,
            "catalogue_id": transcript.catalogue_id,
            "arm": transcript.arm,
            "action": list(transcript.action),
            "purpose": transcript.purpose.value,
            "checkpoint": transcript.checkpoint,
            "predecessor_transcript_id": (
                transcript.predecessor_transcript_id
            ),
            "sequence_offset": transcript.sequence_offset,
            "entry_ids": list(entry_ids),
            "discovery_work_id": (
                None
                if transcript.discovery_work is None
                else transcript.discovery_work.work_id
            ),
            "validation_work_id": transcript.validation_work.work_id,
            "cumulative_sequence_count": (
                transcript.sequence_offset + len(entry_ids)
            ),
            "append_only": True,
            "replacement_allowed": False,
            "source_prior_used_in_confidence": False,
        },
    )
    if transcript.transcript_id != result:
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "producer transcript content ID does not replay"
        )
    return result


def _acquisition_id(
    acquisition: accumulator.RegisteredTargetRowAcquisitionV1,
) -> str:
    if (
        type(acquisition)
        is not accumulator.RegisteredTargetRowAcquisitionV1
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "history contains a foreign acquisition type"
        )
    transcript_id = _transcript_id(acquisition.transcript)
    result = _hash(
        _PRODUCER_DOMAINS["acquisition"],
        {
            "schema": "acfqp.v072_registered_target_row_acquisition.v1",
            "schema_version": accumulator.SCHEMA_VERSION,
            "proposed_contract_version": (
                accumulator.PROPOSED_CONTRACT_VERSION
            ),
            "profile_key": accumulator.PROFILE_KEY,
            "authority_chain_id": acquisition.authority_chain_id,
            "anchor_id": acquisition.anchor_id,
            "final_preregistration_id": (
                acquisition.final_preregistration_id
            ),
            "context_id": acquisition.context.context_id,
            "catalogue_id": acquisition.catalogue.catalogue_id,
            "row_binding_id": acquisition.row_binding_id,
            "action": list(acquisition.action),
            "arm": acquisition.arm,
            "purpose": acquisition.purpose.value,
            "round_index": acquisition.round_index,
            "checkpoint": acquisition.checkpoint,
            "frontier_id": (
                None
                if acquisition.frontier is None
                else acquisition.frontier.frontier_id
            ),
            "parent_acquisition_id": (
                None
                if acquisition.parent is None
                else acquisition.parent.acquisition_id
            ),
            "discovery_support_epoch_chain_id": (
                None
                if acquisition.discovery_support_epoch_chain is None
                else acquisition.discovery_support_epoch_chain.chain_id
            ),
            "validation_support_epoch_chain_id": (
                acquisition.validation_support_epoch_chain.chain_id
            ),
            "transcript_id": transcript_id,
            "support_descriptor_ids": list(
                acquisition.support_descriptor_ids
            ),
            "validation_novel_descriptor_ids": list(
                acquisition.validation_novel_descriptor_ids
            ),
            "append_only": True,
            "fresh_round_two_frontier": acquisition.round_index == 2,
            "replacement_allowed": False,
            "early_stop_allowed": False,
            "source_prior_used_for_proposal_ordering_only": True,
            "source_prior_used_in_confidence": False,
            "caller_observations_accepted": False,
            "caller_law_or_seed_accepted": False,
        },
    )
    if acquisition.acquisition_id != result:
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "producer acquisition content ID does not replay"
        )
    return result


def _recorded_descriptor_id(
    observation: observer.HeldoutObservedJointTransitionV2,
) -> str:
    return descriptors.RecordedTransitionDescriptorV2(
        observation.next_state,
        observation.realized_row_reward,
        observation.failure,
        observation.terminal,
    ).descriptor_id


def _cold_descriptor(
    observation: observer.HeldoutObservedJointTransitionV2,
    adapter: public_adapter.HeldoutPublicGraphColdClosureAdapterV1,
) -> cold.ColdOutcomeDescriptorV1:
    recorded = descriptors.RecordedTransitionDescriptorV2(
        observation.next_state,
        observation.realized_row_reward,
        observation.failure,
        observation.terminal,
    )
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


def _verify_observation_binding(
    acquisition: accumulator.RegisteredTargetRowAcquisitionV1,
    observation: observer.HeldoutObservedJointTransitionV2,
) -> None:
    expected_chain = (
        acquisition.discovery_support_epoch_chain
        if observation.lane is observer.ObservationLaneV2.DISCOVERY
        else acquisition.validation_support_epoch_chain
    )
    if (
        observation.anchor_id != acquisition.anchor_id
        or observation.context_id != acquisition.context.context_id
        or observation.row_binding_id != acquisition.row_binding_id
        or observation.catalogue_id != acquisition.catalogue.catalogue_id
        or observation.arm != acquisition.arm
        or observation.source_state != acquisition.catalogue.state
        or observation.action != acquisition.action
        or observation.remaining_horizon
        != acquisition.catalogue.remaining_horizon
        or expected_chain is None
        or observation.support_epoch_chain_id != expected_chain.chain_id
        or observation.support_epoch_id != expected_chain.leaf.epoch_id
        or observation.raw_commitment.stream_id != observation.stream_id
        or observation.raw_commitment.lane is not observation.lane
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "embedded producer observation is rebound across row or epoch"
        )


def _replay_confidence_bundle(
    *,
    authority_chain_id: str,
    anchor_id: str,
    final_preregistration_id: str,
    adapter: public_adapter.HeldoutPublicGraphColdClosureAdapterV1,
    acquisition: accumulator.RegisteredTargetRowAcquisitionV1,
    claimed: (
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1
    ),
    parent_replay: (
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1
        | None
    ),
) -> None:
    acquisition_id = _acquisition_id(acquisition)
    if (
        type(claimed)
        is not confidence_independent.RegisteredTargetConfidenceReplayBundleV1
        or claimed.acquisition != acquisition
        or claimed.acquisition_id != acquisition_id
        or acquisition.authority_chain_id != authority_chain_id
        or acquisition.anchor_id != anchor_id
        or acquisition.final_preregistration_id != final_preregistration_id
        or acquisition.context.context_id != adapter.context_id
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "producer/replay pair is substituted or identity-stale"
        )
    transcript = acquisition.transcript
    discovery = tuple(
        item.observation
        for item in transcript.entries
        if item.observation.lane is observer.ObservationLaneV2.DISCOVERY
    )
    validation = tuple(
        item.observation
        for item in transcript.entries
        if item.observation.lane is observer.ObservationLaneV2.VALIDATION
    )
    for observation in (*discovery, *validation):
        _verify_observation_binding(acquisition, observation)
    if (
        len(discovery) != acquisition.purpose.discovery_draw_count
        or len(validation) != acquisition.checkpoint
        or tuple(item.accepted_draw_index for item in discovery)
        != tuple(range(1, len(discovery) + 1))
        or tuple(item.accepted_draw_index for item in validation)
        != tuple(range(1, len(validation) + 1))
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "embedded producer lanes are incomplete or reordered"
        )

    if acquisition.purpose.is_promotion:
        if (
            type(parent_replay)
            is not confidence_independent
            .RegisteredTargetConfidenceReplayBundleV1
            or acquisition.parent != parent_replay.acquisition
            or discovery
            or transcript.predecessor_transcript_id
            != acquisition.parent.transcript.transcript_id
            or transcript.sequence_offset
            != acquisition.parent.transcript.cumulative_sequence_count
        ):
            raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
                "promotion replay does not append to its immediate parent"
            )
        support_descriptors = tuple(
            sorted(
                (
                    *parent_replay.row_evidence.discovery_support,
                    *parent_replay.row_evidence.validation_novel,
                ),
                key=lambda item: item.descriptor_record_id,
            )
        )
        support_ids = tuple(
            sorted(
                item.semantic_descriptor_id
                for item in support_descriptors
            )
        )
        discovery_transcript_id = (
            parent_replay.attestation.discovery_transcript_id
        )
        stream_opens = 1
    else:
        if (
            parent_replay is not None
            or acquisition.parent is not None
            or acquisition.discovery_support_epoch_chain is None
        ):
            raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
                "initial/new-child replay borrowed parent evidence"
            )
        representatives: dict[
            str, observer.HeldoutObservedJointTransitionV2
        ] = {}
        for observation in discovery:
            representatives.setdefault(
                _recorded_descriptor_id(observation),
                observation,
            )
        support_ids = tuple(sorted(representatives))
        support_descriptors = tuple(
            sorted(
                (
                    _cold_descriptor(representatives[item], adapter)
                    for item in support_ids
                ),
                key=lambda item: item.descriptor_record_id,
            )
        )
        discovery_transcript_id = transcript.transcript_id
        stream_opens = 2
    validation_ids = tuple(
        _recorded_descriptor_id(item) for item in validation
    )
    novel_ids = tuple(
        sorted(set(validation_ids) - set(support_ids))
    )
    if (
        acquisition.support_descriptor_ids != support_ids
        or acquisition.validation_novel_descriptor_ids != novel_ids
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "support/validation-novel inventory does not replay"
        )
    novel_representatives: dict[
        str, observer.HeldoutObservedJointTransitionV2
    ] = {}
    for observation in validation:
        descriptor_id = _recorded_descriptor_id(observation)
        if descriptor_id in novel_ids:
            novel_representatives.setdefault(descriptor_id, observation)
    novel_descriptors = tuple(
        sorted(
            (
                _cold_descriptor(novel_representatives[item], adapter)
                for item in novel_ids
            ),
            key=lambda item: item.descriptor_record_id,
        )
    )
    counts_by_semantic, intervals_by_semantic = (
        confidence_independent
        .replay_registered_confidence_count_intervals_core_v1(
            support_descriptor_ids=support_ids,
            validation_descriptor_ids=validation_ids,
            checkpoint=acquisition.checkpoint,
        )
    )
    validation_prefix_id = _hash(
        _REPLAY_DOMAINS["validation_prefix"],
        {
            "schema": (
                "acfqp.v072_registered_validation_prefix_replay.v1"
            ),
            "schema_version": confidence_independent.SCHEMA_VERSION,
            "acquisition_id": acquisition_id,
            "checkpoint": acquisition.checkpoint,
            "observation_ids": [
                item.observation_id for item in validation
            ],
            "descriptor_ids": list(validation_ids),
            "order_preserved": True,
        },
    )
    replay_core_id = _hash(
        _REPLAY_DOMAINS["replay_core"],
        {
            "schema": "acfqp.v072_registered_row_replay_core.v1",
            "schema_version": confidence_independent.SCHEMA_VERSION,
            "acquisition_id": acquisition_id,
            "transcript_id": transcript.transcript_id,
            "support_epoch_chain_id": (
                acquisition.validation_support_epoch_chain.chain_id
            ),
            "support_descriptor_ids": list(support_ids),
            "validation_novel_descriptor_ids": list(novel_ids),
            "validation_prefix_id": validation_prefix_id,
            "discovery_work_id": (
                None
                if transcript.discovery_work is None
                else transcript.discovery_work.work_id
            ),
            "validation_work_id": transcript.validation_work.work_id,
            "linear_replay_once_per_stream": True,
        },
    )
    confidence_snapshot_id = _hash(
        _REPLAY_DOMAINS["confidence_snapshot"],
        {
            "schema": (
                "acfqp.v072_registered_confidence_snapshot_replay.v1"
            ),
            "schema_version": confidence_independent.SCHEMA_VERSION,
            "replay_core_id": replay_core_id,
            "checkpoint": acquisition.checkpoint,
            "support_descriptor_ids": list(support_ids),
            "event_counts": list(counts_by_semantic),
            "event_checkpoints": [
                item[2] for item in intervals_by_semantic
            ],
            "row_epoch_beta": _fdoc(prereg.ROW_EPOCH_BETA),
            "source_prior_used_in_confidence": False,
        },
    )
    all_observations = (*discovery, *validation)
    physical_evidence_id = _hash(
        _REPLAY_DOMAINS["physical"],
        {
            "schema": (
                "acfqp.v072_registered_row_physical_evidence.v1"
            ),
            "schema_version": confidence_independent.SCHEMA_VERSION,
            "anchor_id": anchor_id,
            "acquisition_id": acquisition_id,
            "observation_ids": [
                item.observation_id for item in all_observations
            ],
            "raw_commitment_ids": [
                item.raw_commitment.commitment_id
                for item in all_observations
            ],
            "discovery_work_id": (
                None
                if transcript.discovery_work is None
                else transcript.discovery_work.work_id
            ),
            "validation_work_id": transcript.validation_work.work_id,
            "route_independent": True,
        },
    )
    cold_catalogue = adapter.adapt_public_legal_action_catalogue_v1(
        acquisition.catalogue
    )
    matching_actions = tuple(
        item
        for item in cold_catalogue.actions
        if item.semantic_action_id == acquisition.row_binding_id
    )
    if len(matching_actions) != 1:
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "producer row does not map to one cold semantic action"
        )
    purpose = (
        cold.ColdRowAcquisitionPurposeV1.INCREMENTAL_PROMOTION
        if acquisition.purpose.is_promotion
        else (
            cold.ColdRowAcquisitionPurposeV1.INCREMENTAL_NEW_CHILD
            if acquisition.purpose.is_new_child
            else cold.ColdRowAcquisitionPurposeV1.COLD_INITIAL
        )
    )
    native_work = cold.ColdRowNativeWorkV1(
        purpose,
        len(discovery),
        len(validation),
        (
            0
            if transcript.discovery_work is None
            else transcript.discovery_work.random_word_calls
        ),
        transcript.validation_work.random_word_calls,
        (
            0
            if transcript.discovery_work is None
            else transcript.discovery_work.rejection_count
        ),
        transcript.validation_work.rejection_count,
    )
    expected_row = cold.ColdRowEvidenceV1(
        acquisition.context.context_id,
        cold_catalogue.state,
        acquisition.catalogue.remaining_horizon,
        matching_actions[0],
        support_descriptors,
        novel_descriptors,
        acquisition.validation_support_epoch_chain.leaf.epoch_id,
        confidence_snapshot_id,
        replay_core_id,
        physical_evidence_id,
        native_work,
    )
    if expected_row.to_document() != claimed.row_evidence.to_document():
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "confidence row evidence differs from frozen transcript replay"
        )
    interval_by_semantic = {
        descriptor_id: (
            counts_by_semantic[index],
            intervals_by_semantic[index],
        )
        for index, descriptor_id in enumerate(support_ids)
    }
    expected_events = []
    ordered_counts = []
    ordered_intervals = []
    for ordinal, descriptor in enumerate(support_descriptors):
        count, (lower, upper, checkpoint) = interval_by_semantic[
            descriptor.semantic_descriptor_id
        ]
        confidence_event_id = _hash(
            _REPLAY_DOMAINS["confidence_event"],
            {
                "schema": (
                    "acfqp.v072_registered_confidence_event_replay.v1"
                ),
                "schema_version": confidence_independent.SCHEMA_VERSION,
                "confidence_snapshot_id": confidence_snapshot_id,
                "event_ordinal": ordinal,
                "event_kind": "SUPPORT",
                "semantic_descriptor_id": (
                    descriptor.semantic_descriptor_id
                ),
                "descriptor_record_id": descriptor.descriptor_record_id,
                "success_count": count,
                "checkpoint": checkpoint,
            },
        )
        expected_events.append(
            projection.RegisteredConfidenceEventIntervalV1(
                confidence_event_id,
                ordinal,
                projection.RegisteredConfidenceEventKindV1.SUPPORT,
                descriptor.descriptor_record_id,
                lower,
                upper,
            )
        )
        ordered_counts.append(count)
        ordered_intervals.append((lower, upper))
    other_count = counts_by_semantic[-1]
    other_lower, other_upper, other_checkpoint = intervals_by_semantic[-1]
    other_ordinal = len(support_descriptors)
    other_confidence_event_id = _hash(
        _REPLAY_DOMAINS["confidence_event"],
        {
            "schema": (
                "acfqp.v072_registered_confidence_event_replay.v1"
            ),
            "schema_version": confidence_independent.SCHEMA_VERSION,
            "confidence_snapshot_id": confidence_snapshot_id,
            "event_ordinal": other_ordinal,
            "event_kind": "OTHER",
            "semantic_descriptor_id": None,
            "descriptor_record_id": None,
            "success_count": other_count,
            "checkpoint": other_checkpoint,
        },
    )
    expected_events.append(
        projection.RegisteredConfidenceEventIntervalV1(
            other_confidence_event_id,
            other_ordinal,
            projection.RegisteredConfidenceEventKindV1.OTHER,
            None,
            other_lower,
            other_upper,
        )
    )
    ordered_counts.append(other_count)
    ordered_intervals.append((other_lower, other_upper))
    expected_event_tuple = tuple(expected_events)
    if tuple(
        item.to_document() for item in expected_event_tuple
    ) != tuple(item.to_document() for item in claimed.event_intervals):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "confidence interval used counts not present in transcript"
        )
    attestation_payload = {
        "schema": (
            "acfqp.v072_registered_target_confidence_"
            "independent_replay_attestation.v1"
        ),
        "schema_version": confidence_independent.SCHEMA_VERSION,
        "proposed_contract_version": (
            confidence_independent.PROPOSED_CONTRACT_VERSION
        ),
        "profile_key": confidence_independent.PROFILE_KEY,
        "authority_chain_id": authority_chain_id,
        "anchor_id": anchor_id,
        "final_preregistration_id": final_preregistration_id,
        "acquisition_id": acquisition_id,
        "transcript_id": transcript.transcript_id,
        "discovery_transcript_id": discovery_transcript_id,
        "validation_prefix_id": validation_prefix_id,
        "row_evidence_id": expected_row.row_evidence_id,
        "support_epoch_id": expected_row.support_epoch_id,
        "support_semantic_descriptor_ids": list(support_ids),
        "support_descriptor_record_ids": [
            item.descriptor_record_id for item in support_descriptors
        ],
        "validation_novel_descriptor_record_ids": [
            item.descriptor_record_id for item in novel_descriptors
        ],
        "event_ids": [
            item.event_id for item in expected_event_tuple
        ],
        "event_success_counts": ordered_counts,
        "event_probability_intervals": [
            {"lower": _fdoc(lower), "upper": _fdoc(upper)}
            for lower, upper in ordered_intervals
        ],
        "selected_checkpoint_draw_count": acquisition.checkpoint,
        "replayed_stream_opens": stream_opens,
        "replayed_draw_calls": len(all_observations),
        "linear_replay_once_per_stream": True,
        "event_counts_recomputed": True,
        "interval_projection_recomputed": True,
        "content_ids_recomputed": True,
        "source_prior_used_for_ordering_only": True,
        "source_prior_used_in_confidence": False,
        "caller_observations_or_counts_accepted": False,
    }
    attestation_id = _hash(
        _REPLAY_DOMAINS["attestation"],
        attestation_payload,
    )
    if claimed.attestation.to_document() != {
        **attestation_payload,
        "attestation_id": attestation_id,
    }:
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "confidence attestation does not replay from transcript"
        )
    authority_payload = {
        "schema": (
            "acfqp.v072_registered_confidence_projection_authority.v1"
        ),
        "schema_version": projection.SCHEMA_VERSION,
        "anchor_id": anchor_id,
        "final_preregistration_id": final_preregistration_id,
        "row_evidence_id": expected_row.row_evidence_id,
        "event_ids": [item.event_id for item in expected_event_tuple],
        "discovery_transcript_id": discovery_transcript_id,
        "validation_transcript_id": transcript.transcript_id,
        "validation_prefix_id": validation_prefix_id,
        "confidence_verification_id": attestation_id,
        "selected_checkpoint_draw_count": acquisition.checkpoint,
        "rank_cap": prereg.RANK_CAP,
        "registered_target_evidence": True,
        "caller_supplied_intervals_allowed": False,
    }
    authority_id = _hash(
        projection.DOMAIN_TAGS["registered_authority"],
        authority_payload,
    )
    authority = claimed.confidence_authority
    if (
        authority.to_document()
        != {
            **authority_payload,
            "event_intervals": [
                item.to_document() for item in expected_event_tuple
            ],
            "authority_id": authority_id,
        }
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "confidence authority differs or contains source quantities"
        )
    bundle_payload = {
        "schema": (
            "acfqp.v072_registered_target_confidence_replay_bundle.v1"
        ),
        "schema_version": confidence_independent.SCHEMA_VERSION,
        "acquisition_id": acquisition_id,
        "attestation_id": attestation_id,
        "row_evidence_id": expected_row.row_evidence_id,
        "event_ids": [item.event_id for item in expected_event_tuple],
        "confidence_authority_id": authority_id,
    }
    if claimed.bundle_id != _hash(
        _REPLAY_DOMAINS["bundle"],
        bundle_payload,
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "confidence replay bundle ID does not replay"
        )


def _latest_pairs(
    acquisitions: tuple[
        accumulator.RegisteredTargetRowAcquisitionV1, ...
    ],
    replays: tuple[
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
        ...,
    ],
) -> tuple[
    tuple[
        accumulator.RegisteredTargetRowAcquisitionV1,
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
    ],
    ...,
]:
    if (
        type(acquisitions) is not tuple
        or not acquisitions
        or type(replays) is not tuple
        or len(acquisitions) != len(replays)
        or tuple(item.acquisition_id for item in acquisitions)
        != tuple(sorted({item.acquisition_id for item in acquisitions}))
        or any(
            replay.acquisition != acquisition
            for acquisition, replay in zip(
                acquisitions,
                replays,
                strict=True,
            )
        )
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "acquisition/replay history is dropped, reordered, or substituted"
        )
    latest: dict[
        str,
        tuple[
            accumulator.RegisteredTargetRowAcquisitionV1,
            confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
        ],
    ] = {}
    for acquisition, replay in zip(
        acquisitions,
        replays,
        strict=True,
    ):
        previous = latest.get(acquisition.row_binding_id)
        if (
            previous is not None
            and previous[0].round_index == acquisition.round_index
        ):
            raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
                "one physical row has two versions in the same round"
            )
        if (
            previous is None
            or previous[0].round_index < acquisition.round_index
        ):
            latest[acquisition.row_binding_id] = (acquisition, replay)
    return tuple(
        sorted(latest.values(), key=lambda item: item[0].row_binding_id)
    )


def _incremental_epoch_payload(
    value: materializer.RegisteredIncrementalH2ModelEpochV1,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_registered_incremental_h2_model_epoch.v1",
        "schema_version": materializer.SCHEMA_VERSION,
        "proposed_contract_version": (
            materializer.PROPOSED_CONTRACT_VERSION
        ),
        "profile_key": materializer.PROFILE_KEY,
        "authority_chain_id": value.authority_chain_id,
        "anchor_id": value.anchor_id,
        "occurrence_id": value.occurrence_plan.occurrence_id,
        "context_id": value.context.context_id,
        "arm": value.occurrence_plan.template.arm,
        "round_index": value.round_index,
        "predecessor_epoch_id": value.predecessor_epoch_id,
        "predecessor_acquisition_ids": list(
            value.predecessor_acquisition_ids
        ),
        "predecessor_frontier_id": value.predecessor_frontier_id,
        "selector_closure_id": value.selector_closure.closure_id,
        "frontier_id": value.frontier.frontier_id,
        "acquisition_history_ids": [
            item.acquisition_id for item in value.acquisition_history
        ],
        "confidence_replay_history_ids": [
            item.bundle_id for item in value.confidence_replay_history
        ],
        "new_acquisition_ids": [
            item.acquisition_id for item in value.new_acquisitions
        ],
        "new_confidence_replay_ids": [
            item.bundle_id for item in value.new_confidence_replays
        ],
        "active_confidence_replay_ids": [
            item.bundle_id for item in value.active_confidence_replays
        ],
        "closure_id": value.closure_bundle.closure_id,
        "closure_verification_id": (
            value.closure_verification.verification_id
        ),
        "projection_ids": [
            item.projection_id for item in value.row_projections
        ],
        "model_pair_id": value.model_pair.model_pair_id,
        "model_replay_attestation_id": (
            value.model_replay_attestation.attestation_id
        ),
        "access_audit_id": value.access_audit.audit_id,
        "all_historical_evidence_retained": True,
        "active_closure_latest_physical_row_only": True,
        "immutable": True,
        "caller_rows_status_counts_or_callbacks_accepted": False,
    }


def _replay_prior_epoch_id(
    prior: materializer.PriorRegisteredModelEpochV1,
) -> str:
    if type(prior) is cold_runtime.RegisteredColdH2ModelEpochV1:
        payload = {
            "schema": "acfqp.v072_registered_cold_h2_model_epoch.v1",
            "schema_version": cold_runtime.SCHEMA_VERSION,
            "proposed_contract_version": (
                cold_runtime.PROPOSED_CONTRACT_VERSION
            ),
            "profile_key": cold_runtime.PROFILE_KEY,
            "authority_chain_id": prior.authority_chain_id,
            "anchor_id": prior.anchor_id,
            "occurrence_id": prior.occurrence_plan.occurrence_id,
            "context_id": prior.context.context_id,
            "arm": prior.occurrence_plan.template.arm,
            "adapter_id": prior.adapter.adapter_id,
            "acquisition_ids": [
                item.acquisition_id for item in prior.acquisitions
            ],
            "confidence_replay_bundle_ids": [
                item.bundle_id for item in prior.confidence_replays
            ],
            "closure_id": prior.closure_bundle.closure_id,
            "closure_verification_id": (
                prior.closure_verification.verification_id
            ),
            "projection_ids": [
                item.projection_id for item in prior.row_projections
            ],
            "model_pair_id": prior.model_pair.model_pair_id,
            "model_replay_attestation_id": (
                prior.model_replay_attestation.attestation_id
            ),
            "access_audit_id": prior.access_audit.audit_id,
            "complete_discovery_closed_h2_inventory": True,
            "source_prior_used_in_confidence_or_model": False,
            "caller_evidence_accepted": False,
        }
        result = _hash(cold_runtime.DOMAIN_TAGS["epoch"], payload)
    elif type(prior) is materializer.RegisteredIncrementalH2ModelEpochV1:
        result = _hash(
            materializer.DOMAIN_TAGS["epoch"],
            _incremental_epoch_payload(prior),
        )
    else:
        raise RegisteredIncrementalEpochIndependentVerifierLockedV1(
            "independent replay requires one exact prior epoch",
            access_audit=ZERO_ACCESS_AUDIT,
        )
    if prior.epoch_id != result:
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "prior immutable epoch ID does not replay"
        )
    return result


def _selector_closure_id(
    value: selector.RegisteredSelectorClosureV1,
) -> str:
    if (
        type(value) is not selector.RegisteredSelectorClosureV1
        or type(value.independent_attestation)
        is not selector_independent.RegisteredSelectorIndependentAttestationV1
        or value.claim.claim_id
        != value.independent_attestation.claim_id
        or value.selection_authority is None
        or value.frontier is None
        or value.frontier.selection_authority
        != value.selection_authority
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "selector closure lacks exact independent replay authority"
        )
    expected = _hash(
        selector.DOMAIN_TAGS["closure"],
        {
            "schema": "acfqp.v072_registered_selector_closure.v1",
            "schema_version": selector.SCHEMA_VERSION,
            "claim_id": value.claim.claim_id,
            "attestation_id": (
                value.independent_attestation.attestation_id
            ),
            "selection_authority_id": (
                value.selection_authority.selection_authority_id
            ),
            "frontier_id": value.frontier.frontier_id,
            "outcome": value.claim.decision.outcome.value,
        },
    )
    attestation = value.independent_attestation
    candidate = value.claim.selected_candidate
    if (
        value.closure_id != expected
        or value.claim.decision.outcome
        is not selector.RegisteredSelectorOutcomeV1.SELECTED
        or candidate is None
        or attestation.outcome
        is not selector.RegisteredSelectorOutcomeV1.SELECTED
        or attestation.selected_candidate_id != candidate.candidate_id
        or attestation.supporting_acquisition_ids
        != value.claim.supporting_acquisition_ids
        or attestation.promotion_row_binding_id
        != candidate.promotion_row_binding_id
        or attestation.new_child_row_binding_ids
        != tuple(item.row_binding_id for item in candidate.new_child_rows)
        or attestation.selected_row_binding_ids
        != candidate.selected_row_binding_ids
        or value.frontier.selected_row_binding_ids
        != candidate.selected_row_binding_ids
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "selector closure/candidate inventory does not independently bind"
        )
    return expected


def _prior_parts(
    prior: materializer.PriorRegisteredModelEpochV1,
) -> tuple[
    int,
    tuple[accumulator.RegisteredTargetRowAcquisitionV1, ...],
    tuple[
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
        ...,
    ],
    tuple[
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
        ...,
    ],
    accumulator.RegisteredAcquisitionFrontierV1 | None,
    tuple[str, ...],
]:
    if type(prior) is cold_runtime.RegisteredColdH2ModelEpochV1:
        active = tuple(item[1] for item in _latest_pairs(
            prior.acquisitions,
            prior.confidence_replays,
        ))
        return (
            0,
            prior.acquisitions,
            prior.confidence_replays,
            active,
            None,
            (),
        )
    if type(prior) is materializer.RegisteredIncrementalH2ModelEpochV1:
        active = tuple(item[1] for item in _latest_pairs(
            prior.acquisition_history,
            prior.confidence_replay_history,
        ))
        if prior.active_confidence_replays != active:
            raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
                "prior epoch latest-row mapping does not replay"
            )
        return (
            prior.round_index,
            prior.acquisition_history,
            prior.confidence_replay_history,
            active,
            prior.frontier,
            prior.selector_closure.claim.supporting_acquisition_ids,
        )
    raise RegisteredIncrementalEpochIndependentVerifierLockedV1(
        "independent replay requires one exact prior epoch",
        access_audit=ZERO_ACCESS_AUDIT,
    )


def verify_registered_incremental_h2_model_epoch_independently_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    context: prereg.HeldoutPublicGraphContextV2,
    prior_epoch: materializer.PriorRegisteredModelEpochV1,
    selector_closure: selector.RegisteredSelectorClosureV1,
    claimed: materializer.RegisteredIncrementalH2ModelEpochV1,
) -> RegisteredIncrementalEpochIndependentAttestationV1:
    """Replay one complete incremental epoch without target or materializer."""

    if (
        type(authority_chain)
        is not consumer.RegisteredCampaignAuthorityChainV1
        or type(anchor) is not final_authority.V072RemoteMainAnchorV1
        or authority_chain.remote_main_anchor is not anchor
        or type(occurrence_plan)
        is not consumer.RegisteredOccurrenceExecutionPlanV1
        or occurrence_plan.chain_id != authority_chain.chain_id
        or type(context) is not prereg.HeldoutPublicGraphContextV2
        or context not in prereg.registered_heldout_public_contexts_v2()
        or occurrence_plan.template.context_id != context.context_id
        or type(prior_epoch)
        not in (
            cold_runtime.RegisteredColdH2ModelEpochV1,
            materializer.RegisteredIncrementalH2ModelEpochV1,
        )
        or type(selector_closure)
        is not selector.RegisteredSelectorClosureV1
        or type(claimed)
        is not materializer.RegisteredIncrementalH2ModelEpochV1
    ):
        raise RegisteredIncrementalEpochIndependentVerifierLockedV1(
            "incremental replay requires exact chain-bound typed artifacts",
            access_audit=ZERO_ACCESS_AUDIT,
        )
    try:
        (
            _source_id,
            _manifest_id,
            final_preregistration_id,
            anchor_id,
            _semantic_id,
        ) = consumer.verify_registered_campaign_authority_chain_v1(
            authority_chain
        )
    except (
        consumer.RegisteredCampaignAuthorityGateLockedV1,
        ValueError,
    ) as error:
        raise RegisteredIncrementalEpochIndependentVerifierLockedV1(
            "incremental replay authority chain is stale",
            access_audit=ZERO_ACCESS_AUDIT,
        ) from error
    prior_epoch_id = _replay_prior_epoch_id(prior_epoch)
    selector_closure_id = _selector_closure_id(selector_closure)
    (
        prior_round,
        prior_acquisitions,
        prior_replays,
        prior_active_replays,
        prior_frontier,
        prior_selector_support,
    ) = _prior_parts(prior_epoch)
    candidate = selector_closure.claim.selected_candidate
    assert candidate is not None and selector_closure.frontier is not None
    expected_round = prior_round + 1
    prior_ids = tuple(
        item.acquisition_id for item in prior_acquisitions
    )
    prior_active_by_id = {
        item.acquisition_id: item
        for item in prior_active_replays
    }
    parent = {
        item.acquisition_id: item for item in prior_acquisitions
    }.get(candidate.parent_acquisition_id)
    if (
        prior_round not in (0, 1)
        or prior_epoch.authority_chain_id != authority_chain.chain_id
        or prior_epoch.anchor_id != anchor_id
        or prior_epoch.occurrence_plan != occurrence_plan
        or prior_epoch.context != context
        or selector_closure.claim.authority_chain_id
        != authority_chain.chain_id
        or selector_closure.claim.anchor_id != anchor_id
        or selector_closure.claim.occurrence_id
        != occurrence_plan.occurrence_id
        or selector_closure.claim.context_id != context.context_id
        or selector_closure.claim.arm != occurrence_plan.template.arm
        or selector_closure.claim.round_index != expected_round
        or selector_closure.claim.supporting_acquisition_ids != prior_ids
        or selector_closure.frontier.supporting_acquisition_ids
        != prior_ids
        or selector_closure.claim.predecessor_frontier_id
        != (None if prior_frontier is None else prior_frontier.frontier_id)
        or (
            prior_round == 1
            and not set(prior_selector_support)
            < set(selector_closure.claim.supporting_acquisition_ids)
        )
        or parent is None
        or parent.acquisition_id not in prior_active_by_id
        or parent.round_index != prior_round
        or parent.row_binding_id != candidate.promotion_row_binding_id
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "round/epoch/frontier/promotion lineage does not replay"
        )
    if (
        claimed.authority_chain_id != authority_chain.chain_id
        or claimed.anchor_id != anchor_id
        or claimed.occurrence_plan != occurrence_plan
        or claimed.context != context
        or claimed.round_index != expected_round
        or claimed.predecessor_epoch_id != prior_epoch_id
        or claimed.predecessor_acquisition_ids != prior_ids
        or claimed.predecessor_frontier_id
        != (None if prior_frontier is None else prior_frontier.frontier_id)
        or claimed.selector_closure != selector_closure
        or claimed.selector_closure.closure_id != selector_closure_id
        or claimed.adapter != prior_epoch.adapter
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "claimed incremental epoch is rebound or stale"
        )

    expected_new_row_ids = (
        candidate.promotion_row_binding_id,
        *(item.row_binding_id for item in candidate.new_child_rows),
    )
    if (
        candidate.selected_row_binding_ids
        != tuple(sorted(expected_new_row_ids))
        or selector_closure.frontier.selected_row_binding_ids
        != candidate.selected_row_binding_ids
        or set(item.row_binding_id for item in candidate.new_child_rows)
        & {item.acquisition.row_binding_id for item in prior_active_replays}
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "selected child inventory is incomplete or replaces an active row"
        )
    if (
        type(claimed.new_acquisitions) is not tuple
        or type(claimed.new_confidence_replays) is not tuple
        or len(claimed.new_acquisitions)
        != len(claimed.new_confidence_replays)
        or not claimed.new_acquisitions
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "new producer/replay inventory is missing or reordered"
        )
    new_pairs = tuple(
        zip(
            claimed.new_acquisitions,
            claimed.new_confidence_replays,
            strict=True,
        )
    )
    if (
        tuple(item[0].acquisition_id for item in new_pairs)
        != tuple(
            sorted({item[0].acquisition_id for item in new_pairs})
        )
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "new producer/replay inventory is missing or reordered"
        )
    promotions = tuple(
        item
        for item in new_pairs
        if item[0].purpose.is_promotion
    )
    new_children = tuple(
        item
        for item in new_pairs
        if item[0].purpose.is_new_child
    )
    child_by_row = {item[0].row_binding_id: item for item in new_children}
    spec_by_row = {
        item.row_binding_id: item for item in candidate.new_child_rows
    }
    promotion_purpose = {
        1: (
            accumulator.RegisteredTargetAcquisitionPurposeV1
            .INCREMENTAL_PROMOTION_ROUND_1
        ),
        2: (
            accumulator.RegisteredTargetAcquisitionPurposeV1
            .INCREMENTAL_PROMOTION_ROUND_2
        ),
    }[expected_round]
    child_purpose = {
        1: (
            accumulator.RegisteredTargetAcquisitionPurposeV1
            .INCREMENTAL_NEW_CHILD_ROUND_1
        ),
        2: (
            accumulator.RegisteredTargetAcquisitionPurposeV1
            .INCREMENTAL_NEW_CHILD_ROUND_2
        ),
    }[expected_round]
    if (
        len(promotions) != 1
        or promotions[0][0].parent != parent
        or promotions[0][0].row_binding_id
        != candidate.promotion_row_binding_id
        or promotions[0][0].catalogue != parent.catalogue
        or promotions[0][0].action != parent.action
        or promotions[0][0].purpose is not promotion_purpose
        or promotions[0][0].frontier != selector_closure.frontier
        or set(child_by_row) != set(spec_by_row)
        or any(
            acquisition.catalogue != spec_by_row[row_id].catalogue
            or acquisition.action != spec_by_row[row_id].action
            or acquisition.purpose is not child_purpose
            or acquisition.parent is not None
            or acquisition.frontier != selector_closure.frontier
            for row_id, (acquisition, _replay) in child_by_row.items()
        )
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "selected promotion or complete child inventory was not executed"
        )
    expected_history_pairs = tuple(
        sorted(
            (
                *zip(prior_acquisitions, prior_replays, strict=True),
                *new_pairs,
            ),
            key=lambda item: item[0].acquisition_id,
        )
    )
    if (
        claimed.acquisition_history
        != tuple(item[0] for item in expected_history_pairs)
        or claimed.confidence_replay_history
        != tuple(item[1] for item in expected_history_pairs)
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "history dropped, reordered, or replaced prior evidence"
        )
    latest_pairs = _latest_pairs(
        claimed.acquisition_history,
        claimed.confidence_replay_history,
    )
    expected_active = tuple(item[1] for item in latest_pairs)
    if claimed.active_confidence_replays != expected_active:
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "active closure does not use exactly the latest physical rows"
        )

    replay_by_acquisition: dict[
        str,
        confidence_independent.RegisteredTargetConfidenceReplayBundleV1,
    ] = {}
    ordered_history = tuple(
        sorted(
            expected_history_pairs,
            key=lambda item: (
                item[0].round_index,
                item[0].acquisition_id,
            ),
        )
    )
    for acquisition, replay in ordered_history:
        parent_replay = (
            None
            if acquisition.parent is None
            else replay_by_acquisition.get(
                acquisition.parent.acquisition_id
            )
        )
        _replay_confidence_bundle(
            authority_chain_id=authority_chain.chain_id,
            anchor_id=anchor_id,
            final_preregistration_id=final_preregistration_id,
            adapter=claimed.adapter,
            acquisition=acquisition,
            claimed=replay,
            parent_replay=parent_replay,
        )
        replay_by_acquisition[acquisition.acquisition_id] = replay

    authoritative_rows = tuple(
        item.row_evidence for item in expected_active
    )
    replayed_closure_attestation = (
        closure_independent.verify_v072_cold_h2_closure_independently_v1(
            public_graph=claimed.adapter,
            authoritative_row_evidence=authoritative_rows,
            claimed=claimed.closure_bundle,
        )
    )
    if (
        replayed_closure_attestation.to_document()
        != claimed.closure_verification.to_document()
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "closure independent attestation does not replay"
        )
    replayed_model_attestation = (
        model_independent
        .verify_registered_cold_h2_model_pair_independently_v1(
            anchor,
            authority_chain.remote_main_anchor_attestation,
            claimed.model_pair,
        )
    )
    if (
        replayed_model_attestation.to_document()
        != claimed.model_replay_attestation.to_document()
        or claimed.model_pair.closure_bundle != claimed.closure_bundle
        or tuple(
            sorted(item.row_evidence_id for item in claimed.row_projections)
        )
        != tuple(
            sorted(item.row_evidence.row_evidence_id
                   for item in expected_active)
        )
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "model/projection independent replay differs"
        )
    new_draws = sum(
        len(item.transcript.entries) for item in claimed.new_acquisitions
    )
    expected_access = (
        materializer.RegisteredIncrementalEpochAccessAuditV1(
            authority_chain_verifications=1,
            prior_epoch_checks=1,
            selector_closure_checks=1,
            acquisition_calls=len(claimed.new_acquisitions),
            independent_confidence_replay_calls=(
                len(claimed.new_confidence_replays)
            ),
            producer_stream_opens=sum(
                1 + int(item.transcript.discovery_work is not None)
                for item in claimed.new_acquisitions
            ),
            producer_draw_calls=new_draws,
            replay_stream_opens=sum(
                1 + int(item.transcript.discovery_work is not None)
                for item in claimed.new_acquisitions
            ),
            replay_draw_calls=new_draws,
            unique_online_sample_evidence_draws=new_draws,
            total_observer_draw_calls=2 * new_draws,
            historical_acquisition_count=(
                len(claimed.acquisition_history)
            ),
            active_physical_row_count=len(expected_active),
            superseded_historical_version_count=(
                len(claimed.acquisition_history) - len(expected_active)
            ),
            closure_builds=1,
            closure_independent_verifications=1,
            projection_calls=len(expected_active),
            model_pair_builds=1,
            model_pair_independent_verifications=1,
        )
    )
    if claimed.access_audit != expected_access:
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "draw/history accounting trusts a caller count or omits work"
        )
    expected_epoch_id = _hash(
        materializer.DOMAIN_TAGS["epoch"],
        _incremental_epoch_payload(claimed),
    )
    if claimed.epoch_id != expected_epoch_id:
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "immutable incremental epoch ID does not replay"
        )
    verifier_access = RegisteredIncrementalEpochVerifierAccessAuditV1(
        authority_chain_verifications=1,
        prior_epoch_replays=1,
        selector_closure_replays=1,
        producer_artifact_replays=len(ordered_history),
        confidence_bundle_replays=len(ordered_history),
        history_latest_mapping_replays=1,
        closure_independent_replays=1,
        model_independent_replays=1,
        epoch_identity_replays=1,
    )
    return RegisteredIncrementalEpochIndependentAttestationV1(
        _ATTESTATION_SENTINEL,
        authority_chain.chain_id,
        anchor_id,
        occurrence_plan.occurrence_id,
        context.context_id,
        occurrence_plan.template.arm,
        expected_round,
        prior_epoch_id,
        selector_closure_id,
        expected_epoch_id,
        tuple(
            item.acquisition_id for item in claimed.acquisition_history
        ),
        tuple(sorted(
            item.acquisition.acquisition_id for item in expected_active
        )),
        claimed.closure_bundle.closure_id,
        claimed.closure_verification.verification_id,
        claimed.model_pair.model_pair_id,
        claimed.model_replay_attestation.attestation_id,
        verifier_access,
    )


@dataclass(frozen=True, slots=True)
class RegistrationDisjointIncrementalEpochVerificationV1:
    prior_epoch_id: str
    selector_closure_id: str
    claimed_epoch_id: str
    round_index: int
    historical_acquisition_ids: tuple[str, ...]
    active_acquisition_ids: tuple[str, ...]
    producer_draws: int
    independent_replay_draws: int
    registered_target_accesses: int = 0
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.prior_epoch_id,
            self.selector_closure_id,
            self.claimed_epoch_id,
            *self.historical_acquisition_ids,
            *self.active_acquisition_ids,
        ):
            _cid(value, "synthetic verification identity")
        if (
            self.round_index not in (1, 2)
            or self.historical_acquisition_ids
            != tuple(sorted(set(self.historical_acquisition_ids)))
            or self.active_acquisition_ids
            != tuple(sorted(set(self.active_acquisition_ids)))
            or not set(self.active_acquisition_ids).issubset(
                self.historical_acquisition_ids
            )
            or self.producer_draws < 0
            or self.independent_replay_draws != self.producer_draws
            or self.registered_target_accesses != 0
        ):
            raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
                "synthetic independent verification is malformed"
            )
        object.__setattr__(
            self,
            "_verification_id",
            _hash(
                _VERIFIER_DOMAINS["synthetic_verification"],
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_incremental_epoch_"
                "independent_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "prior_epoch_id": self.prior_epoch_id,
            "selector_closure_id": self.selector_closure_id,
            "claimed_epoch_id": self.claimed_epoch_id,
            "round_index": self.round_index,
            "historical_acquisition_ids": list(
                self.historical_acquisition_ids
            ),
            "active_acquisition_ids": list(
                self.active_acquisition_ids
            ),
            "producer_draws": self.producer_draws,
            "independent_replay_draws": self.independent_replay_draws,
            "registered_target_accesses": 0,
            "source_prior_used_in_confidence": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id


def _synthetic_acquisition_payload(
    *,
    row_binding_id: str,
    round_index: int,
    kind: materializer.RegistrationDisjointAcquisitionKindV1,
    parent_acquisition_id: str | None,
    frontier_id: str | None,
    producer_draws: int,
) -> dict[str, Any]:
    return {
        "schema": (
            "acfqp.v072_registration_disjoint_incremental_acquisition.v1"
        ),
        "schema_version": materializer.SCHEMA_VERSION,
        "row_binding_id": row_binding_id,
        "round_index": round_index,
        "kind": kind.value,
        "parent_acquisition_id": parent_acquisition_id,
        "frontier_id": frontier_id,
        "producer_draws": producer_draws,
        "caller_observations_or_counts_accepted": False,
    }


def _synthetic_acquisition_ids(
    item: materializer.RegistrationDisjointIncrementalAcquisitionV1,
) -> tuple[str, str]:
    if (
        type(item)
        is not materializer.RegistrationDisjointIncrementalAcquisitionV1
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "synthetic history contains a foreign acquisition"
        )
    acquisition_id = _hash(
        materializer.DOMAIN_TAGS["synthetic_acquisition"],
        _synthetic_acquisition_payload(
            row_binding_id=item.row_binding_id,
            round_index=item.round_index,
            kind=item.kind,
            parent_acquisition_id=item.parent_acquisition_id,
            frontier_id=item.frontier_id,
            producer_draws=item.producer_draws,
        ),
    )
    replay_id = _hash(
        materializer.DOMAIN_TAGS["synthetic_replay"],
        {
            "schema": (
                "acfqp.v072_registration_disjoint_incremental_replay.v1"
            ),
            "schema_version": materializer.SCHEMA_VERSION,
            "acquisition_id": acquisition_id,
            "producer_draws": item.producer_draws,
            "independent_replay_draws": item.producer_draws,
            "source_prior_used_in_confidence": False,
            "registered_target_accesses": 0,
        },
    )
    if item.acquisition_id != acquisition_id or item.replay_id != replay_id:
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "synthetic producer/replay identity or confidence origin changed"
        )
    return acquisition_id, replay_id


def _synthetic_epoch_ids(
    value: materializer.RegistrationDisjointIncrementalEpochV1,
) -> tuple[str, str, str, str, str]:
    closure_id = _hash(
        materializer.DOMAIN_TAGS["synthetic_closure"],
        {
            "schema": (
                "acfqp.v072_registration_disjoint_incremental_"
                "active_closure.v1"
            ),
            "schema_version": materializer.SCHEMA_VERSION,
            "active_acquisition_ids": list(value.active_acquisition_ids),
            "latest_physical_row_only": True,
            "history_retained_elsewhere": True,
        },
    )
    closure_verification_id = _hash(
        materializer.DOMAIN_TAGS["synthetic_closure_verification"],
        {
            "schema": (
                "acfqp.v072_registration_disjoint_incremental_"
                "active_closure_verification.v1"
            ),
            "schema_version": materializer.SCHEMA_VERSION,
            "closure_id": closure_id,
            "verification_result": "VALID_COMPLETE_ACTIVE_CLOSURE",
        },
    )
    model_id = _hash(
        materializer.DOMAIN_TAGS["synthetic_model"],
        {
            "schema": (
                "acfqp.v072_registration_disjoint_incremental_"
                "model_pair.v1"
            ),
            "schema_version": materializer.SCHEMA_VERSION,
            "closure_id": closure_id,
            "closure_verification_id": closure_verification_id,
            "direct_and_quotient_built": True,
        },
    )
    model_verification_id = _hash(
        materializer.DOMAIN_TAGS["synthetic_model_verification"],
        {
            "schema": (
                "acfqp.v072_registration_disjoint_incremental_"
                "model_verification.v1"
            ),
            "schema_version": materializer.SCHEMA_VERSION,
            "model_pair_id": model_id,
            "verification_result": "VALID",
        },
    )
    epoch_payload = {
        "schema": (
            "acfqp.v072_registration_disjoint_incremental_epoch.v1"
        ),
        "schema_version": materializer.SCHEMA_VERSION,
        "round_index": value.round_index,
        "predecessor_epoch_id": value.predecessor_epoch_id,
        "predecessor_frontier_id": value.predecessor_frontier_id,
        "frontier_id": value.frontier_id,
        "selector_supporting_acquisition_ids": list(
            value.selector_supporting_acquisition_ids
        ),
        "acquisition_history_ids": [
            item.acquisition_id for item in value.acquisition_history
        ],
        "replay_history_ids": [
            item.replay_id for item in value.acquisition_history
        ],
        "active_acquisition_ids": list(value.active_acquisition_ids),
        "new_acquisition_ids": list(value.new_acquisition_ids),
        "closure_id": closure_id,
        "closure_verification_id": closure_verification_id,
        "model_pair_id": model_id,
        "model_verification_id": model_verification_id,
        "work_id": None if value.work is None else value.work.work_id,
        "immutable": True,
        "registered_target_accesses": 0,
    }
    epoch_id = _hash(
        materializer.DOMAIN_TAGS["synthetic_epoch"],
        epoch_payload,
    )
    return (
        closure_id,
        closure_verification_id,
        model_id,
        model_verification_id,
        epoch_id,
    )


def _verify_synthetic_epoch_self(
    value: materializer.RegistrationDisjointIncrementalEpochV1,
) -> None:
    if (
        type(value)
        is not materializer.RegistrationDisjointIncrementalEpochV1
        or type(value.acquisition_history) is not tuple
        or not value.acquisition_history
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "synthetic epoch has a foreign type or empty history"
        )
    for item in value.acquisition_history:
        _synthetic_acquisition_ids(item)
    history_ids = tuple(
        item.acquisition_id for item in value.acquisition_history
    )
    if history_ids != tuple(sorted(set(history_ids))):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "synthetic acquisition history was reordered or duplicated"
        )
    by_row: dict[
        str, materializer.RegistrationDisjointIncrementalAcquisitionV1
    ] = {}
    for item in value.acquisition_history:
        previous = by_row.get(item.row_binding_id)
        if previous is not None and previous.round_index == item.round_index:
            raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
                "synthetic history contains same-round replacement"
            )
        if previous is None or previous.round_index < item.round_index:
            by_row[item.row_binding_id] = item
    expected_active = tuple(
        sorted(item.acquisition_id for item in by_row.values())
    )
    (
        closure_id,
        closure_verification_id,
        model_id,
        model_verification_id,
        epoch_id,
    ) = _synthetic_epoch_ids(value)
    if (
        value.active_acquisition_ids != expected_active
        or value.closure_id != closure_id
        or value.closure_verification_id != closure_verification_id
        or value.model_pair_id != model_id
        or value.model_verification_id != model_verification_id
        or value.epoch_id != epoch_id
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "synthetic closure/model/epoch identity does not replay"
        )


def verify_registration_disjoint_incremental_epoch_independently_v1(
    *,
    prior_epoch: materializer.RegistrationDisjointIncrementalEpochV1,
    selector_closure: materializer.RegistrationDisjointSelectorClosureV1,
    claimed: materializer.RegistrationDisjointIncrementalEpochV1,
) -> RegistrationDisjointIncrementalEpochVerificationV1:
    """Target-free positive control for whole incremental epoch replay."""

    if (
        type(prior_epoch)
        is not materializer.RegistrationDisjointIncrementalEpochV1
        or type(selector_closure)
        is not materializer.RegistrationDisjointSelectorClosureV1
        or type(claimed)
        is not materializer.RegistrationDisjointIncrementalEpochV1
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "synthetic verifier requires exact typed artifacts"
        )
    _verify_synthetic_epoch_self(prior_epoch)
    _verify_synthetic_epoch_self(claimed)
    prior_ids = tuple(
        item.acquisition_id for item in prior_epoch.acquisition_history
    )
    if (
        prior_epoch.round_index not in (0, 1)
        or selector_closure.round_index != prior_epoch.round_index + 1
        or selector_closure.prior_epoch_id != prior_epoch.epoch_id
        or selector_closure.predecessor_frontier_id
        != prior_epoch.frontier_id
        or selector_closure.supporting_acquisition_ids != prior_ids
        or claimed.round_index != selector_closure.round_index
        or claimed.predecessor_epoch_id != prior_epoch.epoch_id
        or claimed.predecessor_frontier_id
        != selector_closure.predecessor_frontier_id
        or claimed.frontier_id != selector_closure.frontier_id
        or claimed.selector_supporting_acquisition_ids != prior_ids
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "synthetic round/epoch/frontier lineage is stale"
        )
    by_id = {
        item.acquisition_id: item
        for item in prior_epoch.acquisition_history
    }
    parent = by_id.get(
        selector_closure.promotion_parent_acquisition_id
    )
    if (
        parent is None
        or parent.acquisition_id not in prior_epoch.active_acquisition_ids
        or parent.row_binding_id
        != selector_closure.promotion_row_binding_id
        or parent.round_index != prior_epoch.round_index
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "synthetic round-two parent is stale or superseded"
        )
    active_rows = {
        by_id[item].row_binding_id
        for item in prior_epoch.active_acquisition_ids
    }
    if set(selector_closure.new_child_row_binding_ids) & active_rows:
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "synthetic child inventory replaces an active row"
        )
    promotion_draws = prereg.PROMOTION_VALIDATION_DRAWS_PER_ROUND
    child_draws = (
        prereg.NEW_CHILD_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
        + prereg.NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW
    )
    expected_specs = (
        (
            selector_closure.promotion_row_binding_id,
            materializer.RegistrationDisjointAcquisitionKindV1.PROMOTION,
            parent.acquisition_id,
            promotion_draws,
        ),
        *(
            (
                row_id,
                materializer.RegistrationDisjointAcquisitionKindV1.NEW_CHILD,
                None,
                child_draws,
            )
            for row_id in selector_closure.new_child_row_binding_ids
        ),
    )
    expected_new_ids = []
    expected_replay_ids = []
    for row_id, kind, parent_id, draws in expected_specs:
        acquisition_id = _hash(
            materializer.DOMAIN_TAGS["synthetic_acquisition"],
            _synthetic_acquisition_payload(
                row_binding_id=row_id,
                round_index=selector_closure.round_index,
                kind=kind,
                parent_acquisition_id=parent_id,
                frontier_id=selector_closure.frontier_id,
                producer_draws=draws,
            ),
        )
        replay_id = _hash(
            materializer.DOMAIN_TAGS["synthetic_replay"],
            {
                "schema": (
                    "acfqp.v072_registration_disjoint_"
                    "incremental_replay.v1"
                ),
                "schema_version": materializer.SCHEMA_VERSION,
                "acquisition_id": acquisition_id,
                "producer_draws": draws,
                "independent_replay_draws": draws,
                "source_prior_used_in_confidence": False,
                "registered_target_accesses": 0,
            },
        )
        expected_new_ids.append(acquisition_id)
        expected_replay_ids.append(replay_id)
    expected_new_tuple = tuple(sorted(expected_new_ids))
    claimed_new = tuple(
        item
        for item in claimed.acquisition_history
        if item.acquisition_id in claimed.new_acquisition_ids
    )
    if (
        claimed.new_acquisition_ids != expected_new_tuple
        or tuple(sorted(item.acquisition_id for item in claimed_new))
        != expected_new_tuple
        or {
            item.replay_id for item in claimed_new
        } != set(expected_replay_ids)
        or tuple(
            item.acquisition_id for item in claimed.acquisition_history
        )
        != tuple(
            sorted(
                (
                    *prior_ids,
                    *expected_new_tuple,
                )
            )
        )
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "synthetic history dropped/reordered a selected child or replay"
        )
    producer_draws = promotion_draws + (
        child_draws * len(selector_closure.new_child_row_binding_ids)
    )
    work = claimed.work
    if (
        type(work)
        is not materializer.RegistrationDisjointIncrementalWorkV1
        or work.acquisition_calls != len(expected_specs)
        or work.independent_replay_calls != len(expected_specs)
        or work.promotion_count != 1
        or work.new_child_count
        != len(selector_closure.new_child_row_binding_ids)
        or work.producer_draws != producer_draws
        or work.independent_replay_draws != producer_draws
        or work.total_observer_draws != 2 * producer_draws
        or work.historical_acquisition_count
        != len(claimed.acquisition_history)
        or work.active_physical_row_count
        != len(claimed.active_acquisition_ids)
        or work.superseded_historical_version_count
        != (
            len(claimed.acquisition_history)
            - len(claimed.active_acquisition_ids)
        )
        or work.registered_target_accesses != 0
        or work.caller_rows_status_counts_callbacks != 0
    ):
        raise V072RegisteredIncrementalEpochIndependentVerificationFailure(
            "synthetic work trusts a caller count or omits replay work"
        )
    return RegistrationDisjointIncrementalEpochVerificationV1(
        prior_epoch.epoch_id,
        selector_closure.closure_id,
        claimed.epoch_id,
        claimed.round_index,
        tuple(
            item.acquisition_id for item in claimed.acquisition_history
        ),
        claimed.active_acquisition_ids,
        producer_draws,
        producer_draws,
    )


__all__ = [
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "RegisteredIncrementalEpochIndependentAttestationV1",
    "RegisteredIncrementalEpochIndependentVerifierLockedV1",
    "RegisteredIncrementalEpochVerifierAccessAuditV1",
    "RegistrationDisjointIncrementalEpochVerificationV1",
    "SCHEMA_VERSION",
    "V072RegisteredIncrementalEpochIndependentVerificationFailure",
    "ZERO_ACCESS_AUDIT",
    "verify_registered_incremental_h2_model_epoch_independently_v1",
    "verify_registration_disjoint_incremental_epoch_independently_v1",
]
