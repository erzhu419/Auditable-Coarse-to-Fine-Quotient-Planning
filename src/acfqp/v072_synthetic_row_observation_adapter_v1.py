"""Development-only V0-072 adapter for row-bound observation transcripts.

This adapter is a dry-run control, not a registered held-out target sampler.
It exposes one finite K4 graph-transition row with an exact counter-based
synthetic law.  Every random word is reproducible from an arm-free seed
identity, while observations, work, and confidence artifacts remain
arm-specific.

The adapter exercises the full acquisition mechanics:

* 64 proposal-only discovery draws;
* fresh validation prefixes at 2,048/4,096/8,192/16,384;
* immutable incremental prefix extension; and
* support promotion from *all* parent-validation novel descriptors, with no
  new discovery and a fresh 2,048-draw epoch.

The registered-target entry point remains locked because the current V0-072
preregistration is explicitly nonauthorizing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import partial_support_confidence_v2 as confidence
from acfqp import row_bound_observation_core_v2 as core
import acfqp.transfer_guided_acquisition_preregistration_v1 as prereg


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_development_synthetic_row_observation_adapter_v0"
ROLE = core.DEVELOPMENT_ROLE
REGISTERED_TARGET_TAPE_STATUS = "LOCKED_NONAUTHORIZING_DRAFT"

_UINT64_MASK = (1 << 64) - 1
_SPLITMIX_GAMMA = 0x9E3779B97F4A7C15
_ACTION = (0, 1, 0)
_ROOT_RANKS = (1, 1, 2, 0)
_MERGED_RANKS = (2, 0, 2, 0)
_SPAWN_VERTICES = (1, 3)
_REWARD = Fraction(1, 16)


class SyntheticRowObservationV2InvariantViolation(ValueError):
    """A synthetic row, raw replay, acquisition, or lock is invalid."""


class RegisteredTargetRowAcquisitionLockedV2(RuntimeError):
    """The final target manifest/anchor does not yet authorize target draws."""


DOMAIN_TAGS = {
    "anchor": "acfqp:v072-development-row-adapter-anchor:v1",
    "backend": "acfqp:v072-development-row-adapter-backend:v1",
    "context": "acfqp:v072-development-row-adapter-context:v1",
    "row": "acfqp:v072-development-row-adapter-physical-row:v1",
    "arm_free_row": "acfqp:v072-development-row-adapter-arm-free-row:v1",
    "support_chain": (
        "acfqp:v072-development-row-adapter-support-chain:v1"
    ),
    "support_semantics": (
        "acfqp:v072-development-row-adapter-arm-free-support-semantics:v1"
    ),
    "source_stream": (
        "acfqp:v072-development-row-adapter-source-stream:v1"
    ),
    "descriptor": (
        "acfqp:v072-development-row-adapter-semantic-descriptor:v1"
    ),
    "raw_digest": "acfqp:v072-development-row-adapter-raw-digest:v1",
    "commitment": "acfqp:v072-development-row-adapter-commitment:v1",
    "source_observation": (
        "acfqp:v072-development-row-adapter-source-observation:v1"
    ),
    "acquisition": "acfqp:v072-development-row-acquisition:v1",
    "promotion": "acfqp:v072-development-row-promotion:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("synthetic row-adapter domains must be unique")


def _content_id(
    role: str,
    payload: Mapping[str, Any],
    *,
    raw_suffix: bytes = b"",
) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise SyntheticRowObservationV2InvariantViolation(str(error)) from error
    encoded = domain + b"\x00" + body
    if raw_suffix:
        encoded += b"\x00" + raw_suffix
    return hashlib.sha256(encoded).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise SyntheticRowObservationV2InvariantViolation(
            f"{field_name} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _splitmix64(value: int) -> int:
    word = value & _UINT64_MASK
    word = (word ^ (word >> 30)) * 0xBF58476D1CE4E5B9
    word &= _UINT64_MASK
    word = (word ^ (word >> 27)) * 0x94D049BB133111EB
    word &= _UINT64_MASK
    return (word ^ (word >> 31)) & _UINT64_MASK


def _preregistration_id() -> str:
    return prereg.DRAFT_PREREGISTRATION_ID


def _anchor_id() -> str:
    return _content_id(
        "anchor",
        {
            "schema": "acfqp.v072_development_row_adapter_anchor.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "nonce": "v072-development-row-adapter-control-anchor-v1",
            "role": ROLE,
            "registered_target_evidence": False,
        },
    )


def _backend_domain_id() -> str:
    return _content_id(
        "backend",
        {
            "schema": "acfqp.v072_development_row_adapter_backend.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "law": (
                "K4_UNIFORM_TWO_EMPTY_VERTEX_SPAWN_"
                "RANK2_IFF_ARM_FREE_UINT64_BITS_1_TO_8_ARE_ZERO"
            ),
            "randomness": "SPLITMIX64_COUNTER_REPLAY_DEVELOPMENT_ONLY",
            "formal_exact_iid_claimed": False,
            "role": ROLE,
        },
    )


def _context_id() -> str:
    return _content_id(
        "context",
        {
            "schema": "acfqp.v072_development_row_adapter_context.v1",
            "schema_version": SCHEMA_VERSION,
            "topology": {
                "vertex_count": 4,
                "edges": [
                    [0, 1],
                    [0, 2],
                    [0, 3],
                    [1, 2],
                    [1, 3],
                    [2, 3],
                ],
            },
            "root_ranks": list(_ROOT_RANKS),
            "rank_cap": 4,
            "horizon": 2,
            "role": ROLE,
        },
    )


@dataclass(frozen=True, slots=True)
class DevelopmentSyntheticPhysicalRowV2:
    context_id: str = field(default_factory=_context_id)
    remaining_horizon: int = 2
    state_ranks: tuple[int, ...] = _ROOT_RANKS
    action: tuple[int, int, int] = _ACTION
    role: str = ROLE
    _arm_free_row_id: str = field(init=False, repr=False)
    _physical_row_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            _cid(self.context_id, "synthetic row context") != _context_id()
            or self.remaining_horizon != 2
            or self.state_ranks != _ROOT_RANKS
            or self.action != _ACTION
            or self.role != ROLE
        ):
            raise SyntheticRowObservationV2InvariantViolation(
                "development synthetic physical row changed"
            )
        arm_free_payload = {
            "schema": "acfqp.v072_development_row_adapter_arm_free_row.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "remaining_horizon": self.remaining_horizon,
            "state_ranks": list(self.state_ranks),
            "action": list(self.action),
            "role": ROLE,
        }
        object.__setattr__(
            self,
            "_arm_free_row_id",
            _content_id("arm_free_row", arm_free_payload),
        )
        object.__setattr__(
            self,
            "_physical_row_id",
            _content_id(
                "row",
                {
                    "schema": (
                        "acfqp.v072_development_row_adapter_physical_row.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "arm_free_row_id": self._arm_free_row_id,
                    "ground_row_semantics": (
                        "STATE_ACTION_REMAINING_HORIZON"
                    ),
                    "role": ROLE,
                },
            ),
        )

    @property
    def arm_free_row_id(self) -> str:
        return self._arm_free_row_id

    @property
    def physical_row_id(self) -> str:
        return self._physical_row_id

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_development_row_adapter_physical_row.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "remaining_horizon": self.remaining_horizon,
            "state_ranks": list(self.state_ranks),
            "action": list(self.action),
            "arm_free_row_id": self.arm_free_row_id,
            "physical_row_id": self.physical_row_id,
            "role": ROLE,
            "registered_target_evidence": False,
        }


def _arm_free_support_semantics_id(
    row: DevelopmentSyntheticPhysicalRowV2,
    *,
    epoch_index: int,
    parent_semantics_id: str | None,
    support_descriptor_ids: tuple[str, ...],
) -> str:
    if parent_semantics_id is not None:
        _cid(parent_semantics_id, "parent arm-free support semantics")
    if (
        tuple(sorted(set(support_descriptor_ids)))
        != support_descriptor_ids
    ):
        raise SyntheticRowObservationV2InvariantViolation(
            "arm-free support descriptors must be sorted and unique"
        )
    for descriptor_id in support_descriptor_ids:
        _cid(descriptor_id, "arm-free support descriptor")
    return _content_id(
        "support_semantics",
        {
            "schema": (
                "acfqp.v072_development_row_adapter_arm_free_"
                "support_semantics.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "anchor_id": _anchor_id(),
            "context_id": row.context_id,
            "arm_free_row_id": row.arm_free_row_id,
            "confidence_epoch_index": epoch_index,
            "parent_arm_free_support_semantics_id": parent_semantics_id,
            "support_descriptor_ids": list(support_descriptor_ids),
            "arm_serialized": False,
            "role": ROLE,
        },
    )


def _support_chain_id(
    row: DevelopmentSyntheticPhysicalRowV2,
    *,
    arm: str,
    epoch_index: int,
    arm_free_support_semantics_id: str,
    parent_evidence_id: str | None,
) -> str:
    _cid(
        arm_free_support_semantics_id,
        "support-chain arm-free semantics",
    )
    if parent_evidence_id is not None:
        _cid(parent_evidence_id, "support-chain parent evidence")
    return _content_id(
        "support_chain",
        {
            "schema": "acfqp.v072_development_row_adapter_support_chain.v1",
            "schema_version": SCHEMA_VERSION,
            "anchor_id": _anchor_id(),
            "context_id": row.context_id,
            "arm_free_row_id": row.arm_free_row_id,
            "arm": arm,
            "confidence_epoch_index": epoch_index,
            "arm_free_support_semantics_id": (
                arm_free_support_semantics_id
            ),
            "parent_evidence_id": parent_evidence_id,
            "role": ROLE,
        },
    )


def _seed_material(
    row: DevelopmentSyntheticPhysicalRowV2,
    *,
    lane: confidence.ConfidenceObservationLaneV2,
    confidence_epoch_index: int,
    arm_free_support_semantics_id: str,
) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (
                ("anchor_id", _anchor_id()),
                ("backend_domain_id", _backend_domain_id()),
                ("context_id", row.context_id),
                ("arm_free_row_id", row.arm_free_row_id),
                (
                    "arm_free_support_semantics_id",
                    arm_free_support_semantics_id,
                ),
                ("lane", lane.value),
                ("confidence_epoch_index", str(confidence_epoch_index)),
                ("seed_nonce", "v072-development-row-adapter-seed-v1"),
            )
        )
    )


def _source_stream_id(
    seed_material: tuple[tuple[str, str], ...],
    arm: str,
) -> str:
    return _content_id(
        "source_stream",
        {
            "schema": "acfqp.v072_development_row_adapter_source_stream.v1",
            "schema_version": SCHEMA_VERSION,
            "seed_material": [
                {"key": key, "value": value}
                for key, value in seed_material
            ],
            "arm": arm,
            "role": ROLE,
        },
    )


def _stream_identity(
    row: DevelopmentSyntheticPhysicalRowV2,
    *,
    arm: str,
    lane: confidence.ConfidenceObservationLaneV2,
    confidence_epoch_index: int,
    support_epoch_chain_id: str,
    arm_free_support_semantics_id: str,
) -> core.RowObservationStreamIdentityV2:
    material = _seed_material(
        row,
        lane=lane,
        confidence_epoch_index=confidence_epoch_index,
        arm_free_support_semantics_id=arm_free_support_semantics_id,
    )
    return core.RowObservationStreamIdentityV2(
        preregistration_id=_preregistration_id(),
        backend_domain_id=_backend_domain_id(),
        context_id=row.context_id,
        arm=arm,
        physical_row_id=row.physical_row_id,
        arm_free_row_id=row.arm_free_row_id,
        support_epoch_chain_id=support_epoch_chain_id,
        arm_free_support_semantics_id=arm_free_support_semantics_id,
        lane=lane,
        confidence_epoch_index=confidence_epoch_index,
        seed_material=material,
        source_stream_id=_source_stream_id(material, arm),
        evidence_class=core.RowObservationEvidenceClassV2.DEVELOPMENT_SYNTHETIC,
        role=ROLE,
        registered_target_evidence=False,
    )


def _seed(stream: core.RowObservationStreamIdentityV2) -> int:
    return int.from_bytes(
        hashlib.sha256(
            b"acfqp:v072-development-row-adapter-seed:v1\x00"
            + canonical_json_bytes(
                [
                    {"key": key, "value": value}
                    for key, value in stream.seed_material
                ]
            )
        ).digest()[:8],
        "big",
    )


def _descriptor_document(
    word: int,
) -> tuple[str, dict[str, Any]]:
    vertex = _SPAWN_VERTICES[word & 1]
    spawn_rank = 2 if ((word >> 1) & 0xFF) == 0 else 1
    successor = list(_MERGED_RANKS)
    successor[vertex] = spawn_rank
    document = {
        "schema": (
            "acfqp.v072_development_synthetic_semantic_transition_"
            "descriptor.v1"
        ),
        "schema_version": SCHEMA_VERSION,
        "next_state": {
            "ranks": successor,
            "failure": False,
        },
        "realized_row_reward": _fdoc(_REWARD),
        "failure": False,
        "terminal": False,
        "role": ROLE,
        "registered_target_descriptor_authority_compatible": False,
    }
    descriptor_id = _content_id("descriptor", document)
    return descriptor_id, document


def _raw_observation(
    stream: core.RowObservationStreamIdentityV2,
    sequence_index: int,
) -> core.RowBoundRawObservationV2:
    if sequence_index <= 0:
        raise SyntheticRowObservationV2InvariantViolation(
            "synthetic observation index must be positive"
        )
    word = _splitmix64(
        _seed(stream) + _SPLITMIX_GAMMA * sequence_index
    )
    descriptor_id, descriptor_document = _descriptor_document(word)
    digest_payload = {
        "schema": "acfqp.v072_development_row_adapter_raw_digest.v1",
        "schema_version": SCHEMA_VERSION,
        "seed_identity_id": stream.seed_identity_id,
        "sequence_index": sequence_index,
        "outcome_descriptor_id": descriptor_id,
        "role": ROLE,
    }
    raw_digest = _content_id(
        "raw_digest",
        digest_payload,
        raw_suffix=word.to_bytes(8, "big"),
    )
    commitment_payload = {
        "schema": "acfqp.v072_development_row_adapter_commitment.v1",
        "schema_version": SCHEMA_VERSION,
        "source_stream_id": stream.source_stream_id,
        "seed_identity_id": stream.seed_identity_id,
        "sequence_index": sequence_index,
        "raw_digest": raw_digest,
        "role": ROLE,
    }
    commitment_id = _content_id("commitment", commitment_payload)
    source_payload = {
        "schema": (
            "acfqp.v072_development_row_adapter_source_observation.v1"
        ),
        "schema_version": SCHEMA_VERSION,
        "source_stream_id": stream.source_stream_id,
        "seed_identity_id": stream.seed_identity_id,
        "sequence_index": sequence_index,
        "raw_digest": raw_digest,
        "commitment_id": commitment_id,
        "outcome_descriptor_id": descriptor_id,
        "outcome_descriptor": descriptor_document,
        "role": ROLE,
        "registered_target_evidence": False,
    }
    source_observation_id = _content_id(
        "source_observation", source_payload
    )
    source_document = {
        **source_payload,
        "source_observation_id": source_observation_id,
    }
    return core.freeze_source_observation_v2(
        stream_identity=stream,
        sequence_index=sequence_index,
        source_observation_id=source_observation_id,
        source_commitment_id=commitment_id,
        raw_digest=raw_digest,
        outcome_descriptor_id=descriptor_id,
        source_document=source_document,
        outcome_document=descriptor_document,
    )


def _suffix(
    stream: core.RowObservationStreamIdentityV2,
    start: int,
    stop: int,
) -> tuple[core.RowBoundRawObservationV2, ...]:
    if start <= 0 or stop < start:
        raise SyntheticRowObservationV2InvariantViolation(
            "synthetic suffix bounds are invalid"
        )
    return tuple(_raw_observation(stream, index) for index in range(start, stop + 1))


@dataclass(frozen=True, slots=True)
class DevelopmentSyntheticRowAcquisitionV2:
    row: DevelopmentSyntheticPhysicalRowV2
    arm: str
    confidence_row_binding: confidence.ConfidencePhysicalRowBindingV2
    discovery_transcript: core.RowObservationTranscriptV2
    support_epoch: confidence.InitialSupportEpochV2
    validation_history: tuple[core.RowObservationTranscriptV2, ...]
    confidence_snapshot: confidence.PartialSupportConfidenceSnapshotV2
    role: str = ROLE
    _acquisition_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.row) is not DevelopmentSyntheticPhysicalRowV2
            or self.arm not in prereg.ARM_ORDER
            or type(self.confidence_row_binding)
            is not confidence.ConfidencePhysicalRowBindingV2
            or self.confidence_row_binding.context_id != self.row.context_id
            or self.confidence_row_binding.arm != self.arm
            or self.confidence_row_binding.physical_row_id
            != self.row.physical_row_id
            or type(self.discovery_transcript)
            is not core.RowObservationTranscriptV2
            or self.discovery_transcript.stream_identity.lane
            is not confidence.ConfidenceObservationLaneV2.DISCOVERY
            or self.discovery_transcript.selected_checkpoint_draw_count != 64
            or type(self.support_epoch) is not confidence.InitialSupportEpochV2
            or self.support_epoch.row_binding != self.confidence_row_binding
            or type(self.validation_history) is not tuple
            or not self.validation_history
            or any(
                type(item) is not core.RowObservationTranscriptV2
                for item in self.validation_history
            )
            or type(self.confidence_snapshot)
            is not confidence.PartialSupportConfidenceSnapshotV2
            or self.confidence_snapshot.support_epoch != self.support_epoch
            or self.confidence_snapshot.validation_prefix.observations
            != tuple(
                confidence.freeze_confidence_observation_v2(item)
                for item in self.validation_history[-1].observations
            )
            or self.role != ROLE
        ):
            raise SyntheticRowObservationV2InvariantViolation(
                "development row acquisition has inconsistent lineage"
            )
        expected_previous: core.RowObservationTranscriptV2 | None = None
        for transcript in self.validation_history:
            if (
                transcript.stream_identity
                != self.validation_history[0].stream_identity
                or transcript.previous_transcript_id
                != (
                    None
                    if expected_previous is None
                    else expected_previous.transcript_id
                )
                or transcript.previous_draw_count
                != (
                    0
                    if expected_previous is None
                    else expected_previous.selected_checkpoint_draw_count
                )
            ):
                raise SyntheticRowObservationV2InvariantViolation(
                    "validation history is not one immutable growing prefix"
                )
            expected_previous = transcript
        confidence.verify_partial_support_confidence_snapshot_v2(
            self.confidence_snapshot
        )
        object.__setattr__(
            self,
            "_acquisition_id",
            _content_id("acquisition", self._payload()),
        )

    @property
    def validation_transcript(self) -> core.RowObservationTranscriptV2:
        return self.validation_history[-1]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_development_row_acquisition.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": _preregistration_id(),
            "row_id": self.row.physical_row_id,
            "arm": self.arm,
            "confidence_row_binding_id": (
                self.confidence_row_binding.row_binding_id
            ),
            "discovery_transcript_id": (
                self.discovery_transcript.transcript_id
            ),
            "support_epoch_id": self.support_epoch.support_epoch_id,
            "validation_transcript_ids": [
                item.transcript_id for item in self.validation_history
            ],
            "confidence_snapshot_id": self.confidence_snapshot.snapshot_id,
            "selected_checkpoint_draw_count": (
                self.validation_transcript.selected_checkpoint_draw_count
            ),
            "role": ROLE,
            "registered_target_evidence": False,
        }

    @property
    def acquisition_id(self) -> str:
        return self._acquisition_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "acquisition_id": self.acquisition_id}


@dataclass(frozen=True, slots=True)
class DevelopmentSyntheticPromotedRowAcquisitionV2:
    parent_acquisition: DevelopmentSyntheticRowAcquisitionV2
    promoted_support_epoch: confidence.PromotedSupportEpochV2
    fresh_validation_transcript: core.RowObservationTranscriptV2
    confidence_snapshot: confidence.PartialSupportConfidenceSnapshotV2
    fresh_discovery_draw_count: int = 0
    role: str = ROLE
    _promotion_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        parent = self.parent_acquisition
        if (
            type(parent) is not DevelopmentSyntheticRowAcquisitionV2
            or type(self.promoted_support_epoch)
            is not confidence.PromotedSupportEpochV2
            or self.promoted_support_epoch.parent_snapshot
            != parent.confidence_snapshot
            or type(self.fresh_validation_transcript)
            is not core.RowObservationTranscriptV2
            or self.fresh_validation_transcript.stream_identity.lane
            is not confidence.ConfidenceObservationLaneV2.VALIDATION
            or self.fresh_validation_transcript.stream_identity.confidence_epoch_index
            != 2
            or self.fresh_validation_transcript.previous_transcript_id
            is not None
            or self.fresh_validation_transcript.selected_checkpoint_draw_count
            != 2_048
            or set(
                item.sample_id
                for item in self.fresh_validation_transcript.observations
            )
            & set(parent.confidence_snapshot.validation_prefix.sample_ids)
            or type(self.confidence_snapshot)
            is not confidence.PartialSupportConfidenceSnapshotV2
            or self.confidence_snapshot.support_epoch
            != self.promoted_support_epoch
            or self.confidence_snapshot.validation_prefix.observations
            != tuple(
                confidence.freeze_confidence_observation_v2(item)
                for item in self.fresh_validation_transcript.observations
            )
            or self.fresh_discovery_draw_count != 0
            or self.role != ROLE
        ):
            raise SyntheticRowObservationV2InvariantViolation(
                "promoted acquisition reused evidence or changed lineage"
            )
        confidence.verify_partial_support_confidence_snapshot_v2(
            self.confidence_snapshot
        )
        object.__setattr__(
            self,
            "_promotion_id",
            _content_id("promotion", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_development_row_promotion.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "parent_acquisition_id": self.parent_acquisition.acquisition_id,
            "parent_snapshot_id": (
                self.parent_acquisition.confidence_snapshot.snapshot_id
            ),
            "promoted_support_epoch_id": (
                self.promoted_support_epoch.support_epoch_id
            ),
            "fresh_validation_transcript_id": (
                self.fresh_validation_transcript.transcript_id
            ),
            "confidence_snapshot_id": self.confidence_snapshot.snapshot_id,
            "fresh_discovery_draw_count": 0,
            "fresh_validation_draw_count": 2_048,
            "old_probability_samples_reused": False,
            "all_parent_novel_descriptors_promoted": True,
            "role": ROLE,
            "registered_target_evidence": False,
        }

    @property
    def promotion_id(self) -> str:
        return self._promotion_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "promotion_id": self.promotion_id}


def acquire_development_synthetic_initial_row_v2(
    *,
    arm: str = "NO_PRIOR",
    validation_checkpoint: int = 2_048,
) -> DevelopmentSyntheticRowAcquisitionV2:
    """Acquire one cold synthetic row without touching registered target state."""

    if arm not in prereg.ARM_ORDER or validation_checkpoint != 2_048:
        raise SyntheticRowObservationV2InvariantViolation(
            "cold acquisition requires one registered arm and checkpoint 2048"
        )
    row = DevelopmentSyntheticPhysicalRowV2()
    discovery_semantics = _arm_free_support_semantics_id(
        row,
        epoch_index=0,
        parent_semantics_id=None,
        support_descriptor_ids=(),
    )
    discovery_chain = _support_chain_id(
        row,
        arm=arm,
        epoch_index=0,
        arm_free_support_semantics_id=discovery_semantics,
        parent_evidence_id=None,
    )
    discovery_stream = _stream_identity(
        row,
        arm=arm,
        lane=confidence.ConfidenceObservationLaneV2.DISCOVERY,
        confidence_epoch_index=0,
        support_epoch_chain_id=discovery_chain,
        arm_free_support_semantics_id=discovery_semantics,
    )
    discovery = core.build_or_extend_row_observation_transcript_v2(
        stream_identity=discovery_stream,
        selected_checkpoint_draw_count=64,
        new_observations=_suffix(discovery_stream, 1, 64),
    )
    discovered_descriptor_ids = tuple(
        sorted(
            {
                item.outcome_descriptor_id
                for item in discovery.observations
            }
        )
    )
    validation_semantics = _arm_free_support_semantics_id(
        row,
        epoch_index=1,
        parent_semantics_id=discovery_semantics,
        support_descriptor_ids=discovered_descriptor_ids,
    )
    validation_chain = _support_chain_id(
        row,
        arm=arm,
        epoch_index=1,
        arm_free_support_semantics_id=validation_semantics,
        parent_evidence_id=discovery.transcript_id,
    )
    validation_stream = _stream_identity(
        row,
        arm=arm,
        lane=confidence.ConfidenceObservationLaneV2.VALIDATION,
        confidence_epoch_index=1,
        support_epoch_chain_id=validation_chain,
        arm_free_support_semantics_id=validation_semantics,
    )
    row_binding = confidence.ConfidencePhysicalRowBindingV2(
        _preregistration_id(),
        row.context_id,
        arm,
        row.physical_row_id,
    )
    profile = confidence.v0072_partial_support_confidence_profile_v2()
    support_epoch = confidence.freeze_initial_support_epoch_v2(
        row_binding=row_binding,
        purpose=confidence.ConfidenceEpochPurposeV2.INITIAL_SHARED_OR_DIRECT,
        discovery_support_epoch_chain_id=discovery_chain,
        discovery_stream_id=discovery_stream.source_stream_id,
        discovery_observations=discovery.observations,
        validation_support_epoch_chain_id=validation_chain,
        validation_stream_id=validation_stream.source_stream_id,
        profile=profile,
    )
    validation = core.build_or_extend_row_observation_transcript_v2(
        stream_identity=validation_stream,
        selected_checkpoint_draw_count=validation_checkpoint,
        new_observations=_suffix(
            validation_stream, 1, validation_checkpoint
        ),
    )
    snapshot = confidence.build_partial_support_confidence_snapshot_v2(
        support_epoch,
        validation.observations,
        profile,
    )
    return DevelopmentSyntheticRowAcquisitionV2(
        row,
        arm,
        row_binding,
        discovery,
        support_epoch,
        (validation,),
        snapshot,
    )


def extend_development_synthetic_row_prefix_v2(
    acquisition: DevelopmentSyntheticRowAcquisitionV2,
    *,
    validation_checkpoint: int,
) -> DevelopmentSyntheticRowAcquisitionV2:
    """Extend one validation tape; old chunks and observations are reused."""

    if (
        type(acquisition) is not DevelopmentSyntheticRowAcquisitionV2
        or validation_checkpoint not in (4_096, 8_192, 16_384)
        or validation_checkpoint
        <= acquisition.validation_transcript.selected_checkpoint_draw_count
    ):
        raise SyntheticRowObservationV2InvariantViolation(
            "validation extension checkpoint is stale or not preregistered"
        )
    previous = acquisition.validation_transcript
    stream = previous.stream_identity
    validation = core.build_or_extend_row_observation_transcript_v2(
        stream_identity=stream,
        selected_checkpoint_draw_count=validation_checkpoint,
        new_observations=_suffix(
            stream,
            previous.selected_checkpoint_draw_count + 1,
            validation_checkpoint,
        ),
        previous=previous,
    )
    snapshot = confidence.build_partial_support_confidence_snapshot_v2(
        acquisition.support_epoch,
        validation.observations,
        confidence.v0072_partial_support_confidence_profile_v2(),
    )
    return DevelopmentSyntheticRowAcquisitionV2(
        acquisition.row,
        acquisition.arm,
        acquisition.confidence_row_binding,
        acquisition.discovery_transcript,
        acquisition.support_epoch,
        acquisition.validation_history + (validation,),
        snapshot,
    )


def promote_development_synthetic_row_support_v2(
    parent: DevelopmentSyntheticRowAcquisitionV2,
) -> DevelopmentSyntheticPromotedRowAcquisitionV2:
    """Promote all parent novel outcomes and collect fresh epoch-2 validation."""

    if (
        type(parent) is not DevelopmentSyntheticRowAcquisitionV2
        or not parent.confidence_snapshot.novel_descriptors
    ):
        raise SyntheticRowObservationV2InvariantViolation(
            "support promotion requires parent-validation novelty"
        )
    parent_semantics = (
        parent.validation_transcript.stream_identity
        .arm_free_support_semantics_id
    )
    promoted_descriptor_ids = tuple(
        sorted(
            set(parent.support_epoch.support_descriptor_ids)
            | set(parent.confidence_snapshot.novel_descriptor_ids)
        )
    )
    next_semantics = _arm_free_support_semantics_id(
        parent.row,
        epoch_index=2,
        parent_semantics_id=parent_semantics,
        support_descriptor_ids=promoted_descriptor_ids,
    )
    next_chain = _support_chain_id(
        parent.row,
        arm=parent.arm,
        epoch_index=2,
        arm_free_support_semantics_id=next_semantics,
        parent_evidence_id=parent.confidence_snapshot.snapshot_id,
    )
    next_stream = _stream_identity(
        parent.row,
        arm=parent.arm,
        lane=confidence.ConfidenceObservationLaneV2.VALIDATION,
        confidence_epoch_index=2,
        support_epoch_chain_id=next_chain,
        arm_free_support_semantics_id=next_semantics,
    )
    promoted_epoch = confidence.promote_support_epoch_v2(
        parent.confidence_snapshot,
        next_support_epoch_chain_id=next_chain,
        next_validation_stream_id=next_stream.source_stream_id,
    )
    validation = core.build_or_extend_row_observation_transcript_v2(
        stream_identity=next_stream,
        selected_checkpoint_draw_count=2_048,
        new_observations=_suffix(next_stream, 1, 2_048),
    )
    snapshot = confidence.build_partial_support_confidence_snapshot_v2(
        promoted_epoch,
        validation.observations,
        confidence.v0072_partial_support_confidence_profile_v2(),
    )
    return DevelopmentSyntheticPromotedRowAcquisitionV2(
        parent,
        promoted_epoch,
        validation,
        snapshot,
    )


def acquire_registered_target_row_v2(*_args: Any, **_kwargs: Any) -> None:
    """Reject registered target access until a future final anchor authority."""

    raise RegisteredTargetRowAcquisitionLockedV2(
        "registered target row acquisition is locked: "
        f"status={REGISTERED_TARGET_TAPE_STATUS}, "
        f"preregistration_id={prereg.DRAFT_PREREGISTRATION_ID}, "
        "confirmatory_execution_manifest_id=null, "
        "confirmatory_profile_finalized=false, "
        "target_execution_allowed=false"
    )


__all__ = [
    "DevelopmentSyntheticPhysicalRowV2",
    "DevelopmentSyntheticPromotedRowAcquisitionV2",
    "DevelopmentSyntheticRowAcquisitionV2",
    "PROFILE_KEY",
    "REGISTERED_TARGET_TAPE_STATUS",
    "ROLE",
    "RegisteredTargetRowAcquisitionLockedV2",
    "SCHEMA_VERSION",
    "SyntheticRowObservationV2InvariantViolation",
    "acquire_development_synthetic_initial_row_v2",
    "acquire_registered_target_row_v2",
    "extend_development_synthetic_row_prefix_v2",
    "promote_development_synthetic_row_support_v2",
]
