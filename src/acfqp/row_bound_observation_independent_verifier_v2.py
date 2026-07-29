"""Independent replay verifier for the V0-072 row-observation control.

This verifier intentionally does not call the row transcript builder or the
synthetic acquisition adapter.  Content IDs, SplitMix64 words, graph outcomes,
chunk chains, incremental work, and confidence-observation bindings are
recomputed here from duplicated normative formulas.

The verifier accepts only the exact development-control artifact types.  It
cannot authorize or verify registered target observations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import partial_support_confidence_v2 as confidence
from acfqp import row_bound_observation_core_v2 as core
from acfqp import v072_synthetic_row_observation_adapter_v1 as adapter
import acfqp.transfer_guided_acquisition_preregistration_v1 as prereg


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v072_row_observation_independent_verifier_v0"
ROLE = core.DEVELOPMENT_ROLE

_UINT64_MASK = (1 << 64) - 1
_SPLITMIX_GAMMA = 0x9E3779B97F4A7C15
_ROOT_RANKS = (1, 1, 2, 0)
_MERGED_RANKS = (2, 0, 2, 0)
_SPAWN_VERTICES = (1, 3)
_REWARD = Fraction(1, 16)


class RowObservationIndependentVerificationV2Failure(ValueError):
    """The supplied transcript cannot be independently replayed."""


CORE_DOMAINS = {
    "seed": "acfqp:v072-row-observation-seed-identity:v2",
    "stream": "acfqp:v072-row-observation-stream-identity:v2",
    "sample": "acfqp:v072-row-observation-sample:v2",
    "observation": "acfqp:v072-row-bound-source-observation:v2",
    "chunk": "acfqp:v072-row-observation-transcript-chunk:v2",
    "transcript": "acfqp:v072-row-observation-transcript:v2",
    "work": "acfqp:v072-row-observation-work:v2",
}
ADAPTER_DOMAINS = {
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
CONFIDENCE_DOMAINS = {
    "descriptor": "acfqp:v072-confidence-outcome-descriptor:v2",
    "observation": "acfqp:v072-confidence-observation:v2",
    "row": "acfqp:v072-confidence-physical-row-binding:v2",
}
VERIFICATION_DOMAIN = "acfqp:v072-row-observation-independent-verification:v1"


def _hash(
    domain: str,
    payload: Mapping[str, Any] | list[Any],
    *,
    raw_suffix: bytes = b"",
) -> str:
    try:
        body = canonical_json_bytes(payload)
    except (TypeError, ValueError) as error:
        raise RowObservationIndependentVerificationV2Failure(
            str(error)
        ) from error
    encoded = domain.encode("utf-8") + b"\x00" + body
    if raw_suffix:
        encoded += b"\x00" + raw_suffix
    return hashlib.sha256(encoded).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise RowObservationIndependentVerificationV2Failure(
            f"{field_name} is not one full content ID"
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
    return (
        prereg.freeze_transfer_guided_acquisition_preregistration_v1()
        .preregistration_id
    )


def _expected_anchor_id() -> str:
    return _hash(
        ADAPTER_DOMAINS["anchor"],
        {
            "schema": "acfqp.v072_development_row_adapter_anchor.v1",
            "schema_version": adapter.SCHEMA_VERSION,
            "profile_key": adapter.PROFILE_KEY,
            "nonce": "v072-development-row-adapter-control-anchor-v1",
            "role": ROLE,
            "registered_target_evidence": False,
        },
    )


def _expected_backend_id() -> str:
    return _hash(
        ADAPTER_DOMAINS["backend"],
        {
            "schema": "acfqp.v072_development_row_adapter_backend.v1",
            "schema_version": adapter.SCHEMA_VERSION,
            "profile_key": adapter.PROFILE_KEY,
            "law": (
                "K4_UNIFORM_TWO_EMPTY_VERTEX_SPAWN_"
                "RANK2_IFF_ARM_FREE_UINT64_BITS_1_TO_8_ARE_ZERO"
            ),
            "randomness": "SPLITMIX64_COUNTER_REPLAY_DEVELOPMENT_ONLY",
            "formal_exact_iid_claimed": False,
            "role": ROLE,
        },
    )


def _expected_context_id() -> str:
    return _hash(
        ADAPTER_DOMAINS["context"],
        {
            "schema": "acfqp.v072_development_row_adapter_context.v1",
            "schema_version": adapter.SCHEMA_VERSION,
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


def _verify_row(row: adapter.DevelopmentSyntheticPhysicalRowV2) -> None:
    if type(row) is not adapter.DevelopmentSyntheticPhysicalRowV2:
        raise RowObservationIndependentVerificationV2Failure(
            "row has a noncanonical concrete type"
        )
    context_id = _expected_context_id()
    arm_free_id = _hash(
        ADAPTER_DOMAINS["arm_free_row"],
        {
            "schema": "acfqp.v072_development_row_adapter_arm_free_row.v1",
            "schema_version": adapter.SCHEMA_VERSION,
            "context_id": context_id,
            "remaining_horizon": 2,
            "state_ranks": list(_ROOT_RANKS),
            "action": [0, 1, 0],
            "role": ROLE,
        },
    )
    physical_id = _hash(
        ADAPTER_DOMAINS["row"],
        {
            "schema": "acfqp.v072_development_row_adapter_physical_row.v1",
            "schema_version": adapter.SCHEMA_VERSION,
            "arm_free_row_id": arm_free_id,
            "ground_row_semantics": "STATE_ACTION_REMAINING_HORIZON",
            "role": ROLE,
        },
    )
    if (
        row.context_id != context_id
        or row.remaining_horizon != 2
        or row.state_ranks != _ROOT_RANKS
        or row.action != (0, 1, 0)
        or row.arm_free_row_id != arm_free_id
        or row.physical_row_id != physical_id
        or row.role != ROLE
    ):
        raise RowObservationIndependentVerificationV2Failure(
            "synthetic physical-row identity changed"
        )


def _expected_support_chain_id(
    row: adapter.DevelopmentSyntheticPhysicalRowV2,
    arm: str,
    epoch_index: int,
    arm_free_support_semantics_id: str,
    parent_evidence_id: str | None,
) -> str:
    return _hash(
        ADAPTER_DOMAINS["support_chain"],
        {
            "schema": "acfqp.v072_development_row_adapter_support_chain.v1",
            "schema_version": adapter.SCHEMA_VERSION,
            "anchor_id": _expected_anchor_id(),
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


def _expected_support_semantics_id(
    row: adapter.DevelopmentSyntheticPhysicalRowV2,
    epoch_index: int,
    parent_semantics_id: str | None,
    support_descriptor_ids: tuple[str, ...],
) -> str:
    return _hash(
        ADAPTER_DOMAINS["support_semantics"],
        {
            "schema": (
                "acfqp.v072_development_row_adapter_arm_free_"
                "support_semantics.v1"
            ),
            "schema_version": adapter.SCHEMA_VERSION,
            "anchor_id": _expected_anchor_id(),
            "context_id": row.context_id,
            "arm_free_row_id": row.arm_free_row_id,
            "confidence_epoch_index": epoch_index,
            "parent_arm_free_support_semantics_id": parent_semantics_id,
            "support_descriptor_ids": list(support_descriptor_ids),
            "arm_serialized": False,
            "role": ROLE,
        },
    )


def _expected_seed_material(
    row: adapter.DevelopmentSyntheticPhysicalRowV2,
    lane: confidence.ConfidenceObservationLaneV2,
    epoch_index: int,
    arm_free_support_semantics_id: str,
) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (
                ("anchor_id", _expected_anchor_id()),
                ("backend_domain_id", _expected_backend_id()),
                ("context_id", row.context_id),
                ("arm_free_row_id", row.arm_free_row_id),
                (
                    "arm_free_support_semantics_id",
                    arm_free_support_semantics_id,
                ),
                ("lane", lane.value),
                ("confidence_epoch_index", str(epoch_index)),
                ("seed_nonce", "v072-development-row-adapter-seed-v1"),
            )
        )
    )


def _seed_payload(stream: core.RowObservationStreamIdentityV2) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_row_observation_seed_identity.v2",
        "schema_version": core.SCHEMA_VERSION,
        "backend_domain_id": stream.backend_domain_id,
        "context_id": stream.context_id,
        "arm_free_row_id": stream.arm_free_row_id,
        "arm_free_support_semantics_id": (
            stream.arm_free_support_semantics_id
        ),
        "lane": stream.lane.value,
        "confidence_epoch_index": stream.confidence_epoch_index,
        "seed_material": [
            {"key": key, "value": value}
            for key, value in stream.seed_material
        ],
        "arm_serialized": False,
    }


def _verify_stream(
    stream: core.RowObservationStreamIdentityV2,
    row: adapter.DevelopmentSyntheticPhysicalRowV2,
    *,
    arm: str,
    lane: confidence.ConfidenceObservationLaneV2,
    epoch_index: int,
    support_chain_id: str,
    arm_free_support_semantics_id: str,
) -> None:
    if type(stream) is not core.RowObservationStreamIdentityV2:
        raise RowObservationIndependentVerificationV2Failure(
            "stream has a noncanonical concrete type"
        )
    material = _expected_seed_material(
        row, lane, epoch_index, arm_free_support_semantics_id
    )
    seed_id = _hash(CORE_DOMAINS["seed"], _seed_payload(stream))
    source_stream_id = _hash(
        ADAPTER_DOMAINS["source_stream"],
        {
            "schema": "acfqp.v072_development_row_adapter_source_stream.v1",
            "schema_version": adapter.SCHEMA_VERSION,
            "seed_material": [
                {"key": key, "value": value} for key, value in material
            ],
            "arm": arm,
            "role": ROLE,
        },
    )
    payload = {
        "schema": "acfqp.v072_row_observation_stream_identity.v2",
        "schema_version": core.SCHEMA_VERSION,
        "proposed_contract_version": core.PROPOSED_CONTRACT_VERSION,
        "profile_key": core.PROFILE_KEY,
        "preregistration_id": _preregistration_id(),
        "backend_domain_id": _expected_backend_id(),
        "context_id": row.context_id,
        "arm": arm,
        "physical_row_id": row.physical_row_id,
        "arm_free_row_id": row.arm_free_row_id,
        "support_epoch_chain_id": support_chain_id,
        "arm_free_support_semantics_id": arm_free_support_semantics_id,
        "lane": lane.value,
        "confidence_epoch_index": epoch_index,
        "seed_identity_id": seed_id,
        "source_stream_id": source_stream_id,
        "evidence_class": "DEVELOPMENT_SYNTHETIC",
        "role": ROLE,
        "registered_target_evidence": False,
    }
    expected_binding = _hash(CORE_DOMAINS["stream"], payload)
    if (
        stream.preregistration_id != _preregistration_id()
        or stream.backend_domain_id != _expected_backend_id()
        or stream.context_id != row.context_id
        or stream.arm != arm
        or stream.physical_row_id != row.physical_row_id
        or stream.arm_free_row_id != row.arm_free_row_id
        or stream.support_epoch_chain_id != support_chain_id
        or stream.arm_free_support_semantics_id
        != arm_free_support_semantics_id
        or stream.lane is not lane
        or stream.confidence_epoch_index != epoch_index
        or stream.seed_material != material
        or stream.seed_identity_id != seed_id
        or stream.source_stream_id != source_stream_id
        or stream.evidence_class.value != "DEVELOPMENT_SYNTHETIC"
        or stream.role != ROLE
        or stream.registered_target_evidence is not False
        or stream.stream_binding_id != expected_binding
    ):
        raise RowObservationIndependentVerificationV2Failure(
            "stream/seed identity differs from independent reconstruction"
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


def _expected_descriptor(word: int) -> tuple[str, dict[str, Any]]:
    vertex = _SPAWN_VERTICES[word & 1]
    rank = 2 if ((word >> 1) & 0xFF) == 0 else 1
    successor = list(_MERGED_RANKS)
    successor[vertex] = rank
    document = {
        "schema": (
            "acfqp.v072_development_synthetic_semantic_transition_"
            "descriptor.v1"
        ),
        "schema_version": adapter.SCHEMA_VERSION,
        "next_state": {"ranks": successor, "failure": False},
        "realized_row_reward": _fdoc(_REWARD),
        "failure": False,
        "terminal": False,
        "role": ROLE,
        "registered_target_descriptor_authority_compatible": False,
    }
    return _hash(ADAPTER_DOMAINS["descriptor"], document), document


def _verify_observation(
    observation: core.RowBoundRawObservationV2,
    stream: core.RowObservationStreamIdentityV2,
    sequence_index: int,
) -> None:
    if type(observation) is not core.RowBoundRawObservationV2:
        raise RowObservationIndependentVerificationV2Failure(
            "transcript contains a noncanonical observation type"
        )
    word = _splitmix64(
        _seed(stream) + _SPLITMIX_GAMMA * sequence_index
    )
    descriptor_id, descriptor_document = _expected_descriptor(word)
    digest_payload = {
        "schema": "acfqp.v072_development_row_adapter_raw_digest.v1",
        "schema_version": adapter.SCHEMA_VERSION,
        "seed_identity_id": stream.seed_identity_id,
        "sequence_index": sequence_index,
        "outcome_descriptor_id": descriptor_id,
        "role": ROLE,
    }
    raw_digest = _hash(
        ADAPTER_DOMAINS["raw_digest"],
        digest_payload,
        raw_suffix=word.to_bytes(8, "big"),
    )
    commitment_payload = {
        "schema": "acfqp.v072_development_row_adapter_commitment.v1",
        "schema_version": adapter.SCHEMA_VERSION,
        "source_stream_id": stream.source_stream_id,
        "seed_identity_id": stream.seed_identity_id,
        "sequence_index": sequence_index,
        "raw_digest": raw_digest,
        "role": ROLE,
    }
    commitment_id = _hash(
        ADAPTER_DOMAINS["commitment"], commitment_payload
    )
    source_payload = {
        "schema": (
            "acfqp.v072_development_row_adapter_source_observation.v1"
        ),
        "schema_version": adapter.SCHEMA_VERSION,
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
    source_observation_id = _hash(
        ADAPTER_DOMAINS["source_observation"], source_payload
    )
    source_document = {
        **source_payload,
        "source_observation_id": source_observation_id,
    }
    sample_payload = {
        "schema": "acfqp.v072_row_observation_sample.v2",
        "schema_version": core.SCHEMA_VERSION,
        "stream_binding_id": stream.stream_binding_id,
        "source_observation_id": source_observation_id,
        "source_commitment_id": commitment_id,
        "sequence_index": sequence_index,
    }
    sample_id = _hash(CORE_DOMAINS["sample"], sample_payload)
    observation_payload = {
        "schema": "acfqp.v072_row_bound_source_observation.v2",
        "schema_version": core.SCHEMA_VERSION,
        "stream_binding_id": stream.stream_binding_id,
        "preregistration_id": stream.preregistration_id,
        "context_id": stream.context_id,
        "arm": stream.arm,
        "physical_row_id": stream.physical_row_id,
        "support_epoch_chain_id": stream.support_epoch_chain_id,
        "stream_id": stream.source_stream_id,
        "lane": stream.lane.value,
        "sequence_index": sequence_index,
        "sample_id": sample_id,
        "source_observation_id": source_observation_id,
        "source_commitment_id": commitment_id,
        "raw_digest": raw_digest,
        "outcome_descriptor_id": descriptor_id,
        "source_document": source_document,
        "outcome_document": descriptor_document,
    }
    observation_id = _hash(
        CORE_DOMAINS["observation"], observation_payload
    )
    try:
        decoded_source = loads_canonical_json(
            observation.source_document_bytes
        )
        decoded_outcome = loads_canonical_json(
            observation.outcome_document_bytes
        )
    except (TypeError, ValueError) as error:
        raise RowObservationIndependentVerificationV2Failure(
            f"embedded source bytes are invalid: {error}"
        ) from error
    if (
        observation.stream_binding_id != stream.stream_binding_id
        or observation.preregistration_id != stream.preregistration_id
        or observation.context_id != stream.context_id
        or observation.arm != stream.arm
        or observation.physical_row_id != stream.physical_row_id
        or observation.support_epoch_chain_id
        != stream.support_epoch_chain_id
        or observation.stream_id != stream.source_stream_id
        or observation.lane is not stream.lane
        or observation.sequence_index != sequence_index
        or observation.source_observation_id != source_observation_id
        or observation.source_commitment_id != commitment_id
        or observation.raw_digest != raw_digest
        or observation.outcome_descriptor_id != descriptor_id
        or observation.source_document_bytes
        != canonical_json_bytes(source_document)
        or observation.outcome_document_bytes
        != canonical_json_bytes(descriptor_document)
        or observation.sample_id != sample_id
        or observation.observation_id != observation_id
    ):
        raise RowObservationIndependentVerificationV2Failure(
            "raw observation differs from independent SplitMix replay"
        )


def _verify_transcript(
    transcript: core.RowObservationTranscriptV2,
    *,
    row: adapter.DevelopmentSyntheticPhysicalRowV2,
    arm: str,
    lane: confidence.ConfidenceObservationLaneV2,
    epoch_index: int,
    support_chain_id: str,
    arm_free_support_semantics_id: str,
    previous: core.RowObservationTranscriptV2 | None,
) -> tuple[int, int]:
    if type(transcript) is not core.RowObservationTranscriptV2:
        raise RowObservationIndependentVerificationV2Failure(
            "transcript has a noncanonical concrete type"
        )
    stream = transcript.stream_identity
    _verify_stream(
        stream,
        row,
        arm=arm,
        lane=lane,
        epoch_index=epoch_index,
        support_chain_id=support_chain_id,
        arm_free_support_semantics_id=arm_free_support_semantics_id,
    )
    expected_previous_id = None if previous is None else previous.transcript_id
    expected_previous_count = (
        0 if previous is None else previous.selected_checkpoint_draw_count
    )
    if (
        transcript.previous_transcript_id != expected_previous_id
        or transcript.previous_draw_count != expected_previous_count
        or (
            previous is not None
            and transcript.chunks[: len(previous.chunks)] != previous.chunks
        )
    ):
        raise RowObservationIndependentVerificationV2Failure(
            "transcript did not preserve its immutable prefix"
        )
    expected_start = 1
    prior_chunk_id: str | None = None
    replayed = 0
    for chunk in transcript.chunks:
        if type(chunk) is not core.RowObservationTranscriptChunkV2:
            raise RowObservationIndependentVerificationV2Failure(
                "transcript chunk has a noncanonical concrete type"
            )
        if (
            chunk.stream_binding_id != stream.stream_binding_id
            or chunk.start_sequence_index != expected_start
            or chunk.previous_chunk_id != prior_chunk_id
            or chunk.end_sequence_index
            != chunk.start_sequence_index + len(chunk.observations) - 1
            or not 1 <= len(chunk.observations) <= core.CHUNK_DRAW_CAP
        ):
            raise RowObservationIndependentVerificationV2Failure(
                "chunk chain is gapped or transplanted"
            )
        for observation in chunk.observations:
            _verify_observation(
                observation, stream, observation.sequence_index
            )
            replayed += 1
        chunk_payload = {
            "schema": "acfqp.v072_row_observation_transcript_chunk.v2",
            "schema_version": core.SCHEMA_VERSION,
            "stream_binding_id": stream.stream_binding_id,
            "start_sequence_index": chunk.start_sequence_index,
            "end_sequence_index": chunk.end_sequence_index,
            "previous_chunk_id": prior_chunk_id,
            "observation_ids": [
                item.observation_id for item in chunk.observations
            ],
            "source_commitment_ids": [
                item.source_commitment_id for item in chunk.observations
            ],
            "exact_source_documents_embedded": True,
        }
        expected_chunk_id = _hash(CORE_DOMAINS["chunk"], chunk_payload)
        if chunk.chunk_id != expected_chunk_id:
            raise RowObservationIndependentVerificationV2Failure(
                "chunk content ID does not replay"
            )
        prior_chunk_id = expected_chunk_id
        expected_start = chunk.end_sequence_index + 1
    if replayed != transcript.selected_checkpoint_draw_count:
        raise RowObservationIndependentVerificationV2Failure(
            "transcript replay count differs from checkpoint"
        )
    new_draws = replayed - expected_previous_count
    expected_new_chunks = len(transcript.chunks) - (
        0 if previous is None else len(previous.chunks)
    )
    work_payload = {
        "schema": "acfqp.v072_row_observation_work.v2",
        "schema_version": core.SCHEMA_VERSION,
        "stream_binding_id": stream.stream_binding_id,
        "total_prefix_draws": replayed,
        "reused_prefix_draws": expected_previous_count,
        "newly_observed_draws": new_draws,
        "source_commitments_verified_during_build": new_draws,
        "chunks_written_during_build": expected_new_chunks,
    }
    expected_work_id = _hash(CORE_DOMAINS["work"], work_payload)
    if (
        transcript.work.to_document()
        != {**work_payload, "work_id": expected_work_id}
    ):
        raise RowObservationIndependentVerificationV2Failure(
            "incremental transcript work does not reconcile"
        )
    transcript_payload = {
        "schema": "acfqp.v072_row_observation_transcript.v2",
        "schema_version": core.SCHEMA_VERSION,
        "proposed_contract_version": core.PROPOSED_CONTRACT_VERSION,
        "profile_key": core.PROFILE_KEY,
        "stream_binding_id": stream.stream_binding_id,
        "selected_checkpoint_draw_count": replayed,
        "chunk_ids": [item.chunk_id for item in transcript.chunks],
        "terminal_chunk_id": transcript.chunks[-1].chunk_id,
        "previous_transcript_id": expected_previous_id,
        "previous_draw_count": expected_previous_count,
        "work_id": expected_work_id,
        "immutable_prefix": True,
    }
    expected_transcript_id = _hash(
        CORE_DOMAINS["transcript"], transcript_payload
    )
    if transcript.transcript_id != expected_transcript_id:
        raise RowObservationIndependentVerificationV2Failure(
            "transcript manifest content ID does not replay"
        )
    return replayed, len(transcript.chunks)


def _confidence_observation_id(
    observation: core.RowBoundRawObservationV2,
) -> str:
    descriptor_document = loads_canonical_json(
        observation.outcome_document_bytes
    )
    descriptor_binding_payload = {
        "schema": "acfqp.v072_outcome_descriptor.v2",
        "schema_version": confidence.SCHEMA_VERSION,
        "descriptor_id": observation.outcome_descriptor_id,
        "document": descriptor_document,
    }
    descriptor_binding_id = _hash(
        CONFIDENCE_DOMAINS["descriptor"], descriptor_binding_payload
    )
    payload = {
        "schema": "acfqp.v072_confidence_observation.v2",
        "schema_version": confidence.SCHEMA_VERSION,
        "preregistration_id": observation.preregistration_id,
        "context_id": observation.context_id,
        "arm": observation.arm,
        "physical_row_id": observation.physical_row_id,
        "support_epoch_chain_id": observation.support_epoch_chain_id,
        "stream_id": observation.stream_id,
        "lane": observation.lane.value,
        "sequence_index": observation.sequence_index,
        "sample_id": observation.sample_id,
        "outcome": {
            "descriptor_id": observation.outcome_descriptor_id,
            "binding_id": descriptor_binding_id,
            "document": descriptor_document,
        },
    }
    return _hash(CONFIDENCE_DOMAINS["observation"], payload)


def _verify_confidence_binding(
    raw: tuple[core.RowBoundRawObservationV2, ...],
    frozen: tuple[confidence.OpaqueConfidenceObservationV2, ...],
) -> None:
    if (
        len(raw) != len(frozen)
        or tuple(_confidence_observation_id(item) for item in raw)
        != tuple(item.observation_id for item in frozen)
        or tuple(item.sample_id for item in raw)
        != tuple(item.sample_id for item in frozen)
        or tuple(item.outcome_descriptor_id for item in raw)
        != tuple(item.outcome_descriptor_id for item in frozen)
    ):
        raise RowObservationIndependentVerificationV2Failure(
            "confidence transcript is not the frozen raw transcript"
        )


def _verify_row_binding(
    binding: confidence.ConfidencePhysicalRowBindingV2,
    row: adapter.DevelopmentSyntheticPhysicalRowV2,
    arm: str,
) -> None:
    payload = {
        "schema": "acfqp.v072_confidence_physical_row_binding.v2",
        "schema_version": confidence.SCHEMA_VERSION,
        "preregistration_id": _preregistration_id(),
        "context_id": row.context_id,
        "arm": arm,
        "physical_row_id": row.physical_row_id,
    }
    expected = _hash(CONFIDENCE_DOMAINS["row"], payload)
    if (
        type(binding) is not confidence.ConfidencePhysicalRowBindingV2
        or binding.preregistration_id != _preregistration_id()
        or binding.context_id != row.context_id
        or binding.arm != arm
        or binding.physical_row_id != row.physical_row_id
        or binding.row_binding_id != expected
    ):
        raise RowObservationIndependentVerificationV2Failure(
            "confidence physical-row binding differs from raw row"
        )


@dataclass(frozen=True, slots=True)
class IndependentRowObservationVerificationV2:
    artifact_id: str
    artifact_kind: str
    replayed_raw_observations: int
    replayed_chunks: int
    final_confidence_snapshot_id: str
    final_checkpoint_draw_count: int
    incremental_new_draws: int
    registered_target_draws: int = 0
    verification_result: str = (
        "VALID_INDEPENDENT_EXACT_DEVELOPMENT_ROW_TRANSCRIPT_REPLAY"
    )
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.artifact_id, "verified artifact")
        _cid(self.final_confidence_snapshot_id, "verified confidence snapshot")
        if (
            self.artifact_kind not in ("INITIAL_OR_EXTENDED", "PROMOTION")
            or self.replayed_raw_observations <= 0
            or self.replayed_chunks <= 0
            or self.final_checkpoint_draw_count <= 0
            or self.incremental_new_draws <= 0
            or self.registered_target_draws != 0
            or self.verification_result
            != "VALID_INDEPENDENT_EXACT_DEVELOPMENT_ROW_TRANSCRIPT_REPLAY"
        ):
            raise RowObservationIndependentVerificationV2Failure(
                "independent verification result is malformed"
            )
        object.__setattr__(
            self,
            "_verification_id",
            _hash(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_row_observation_independent_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "artifact_id": self.artifact_id,
            "artifact_kind": self.artifact_kind,
            "replayed_raw_observations": self.replayed_raw_observations,
            "replayed_chunks": self.replayed_chunks,
            "final_confidence_snapshot_id": (
                self.final_confidence_snapshot_id
            ),
            "final_checkpoint_draw_count": (
                self.final_checkpoint_draw_count
            ),
            "incremental_new_draws": self.incremental_new_draws,
            "registered_target_draws": 0,
            "verification_result": self.verification_result,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_development_synthetic_row_acquisition_v2(
    artifact: adapter.DevelopmentSyntheticRowAcquisitionV2,
) -> IndependentRowObservationVerificationV2:
    """Replay an initial or extended checkpoint without production builders."""

    if type(artifact) is not adapter.DevelopmentSyntheticRowAcquisitionV2:
        raise RowObservationIndependentVerificationV2Failure(
            "verification requires an exact development acquisition artifact"
        )
    _verify_row(artifact.row)
    _verify_row_binding(
        artifact.confidence_row_binding, artifact.row, artifact.arm
    )
    discovery_semantics = _expected_support_semantics_id(
        artifact.row, 0, None, ()
    )
    discovery_chain = _expected_support_chain_id(
        artifact.row,
        artifact.arm,
        0,
        discovery_semantics,
        None,
    )
    discovery_draws, discovery_chunks = _verify_transcript(
        artifact.discovery_transcript,
        row=artifact.row,
        arm=artifact.arm,
        lane=confidence.ConfidenceObservationLaneV2.DISCOVERY,
        epoch_index=0,
        support_chain_id=discovery_chain,
        arm_free_support_semantics_id=discovery_semantics,
        previous=None,
    )
    discovered_descriptor_ids = tuple(
        sorted(
            {
                item.outcome_descriptor_id
                for item in artifact.discovery_transcript.observations
            }
        )
    )
    validation_semantics = _expected_support_semantics_id(
        artifact.row,
        1,
        discovery_semantics,
        discovered_descriptor_ids,
    )
    validation_chain = _expected_support_chain_id(
        artifact.row,
        artifact.arm,
        1,
        validation_semantics,
        artifact.discovery_transcript.transcript_id,
    )
    previous: core.RowObservationTranscriptV2 | None = None
    validation_replays = 0
    validation_chunks = 0
    for transcript in artifact.validation_history:
        replayed, chunks = _verify_transcript(
            transcript,
            row=artifact.row,
            arm=artifact.arm,
            lane=confidence.ConfidenceObservationLaneV2.VALIDATION,
            epoch_index=1,
            support_chain_id=validation_chain,
            arm_free_support_semantics_id=validation_semantics,
            previous=previous,
        )
        validation_replays += (
            replayed
            if previous is None
            else replayed - previous.selected_checkpoint_draw_count
        )
        validation_chunks += (
            chunks if previous is None else chunks - len(previous.chunks)
        )
        previous = transcript
    if previous is None:
        raise RowObservationIndependentVerificationV2Failure(
            "validation history is empty"
        )
    epoch = artifact.support_epoch
    if (
        type(epoch) is not confidence.InitialSupportEpochV2
        or epoch.row_binding != artifact.confidence_row_binding
        or epoch.support_epoch_chain_id != validation_chain
        or epoch.validation_stream_id
        != previous.stream_identity.source_stream_id
        or epoch.discovery_evidence.discovery_support_epoch_chain_id
        != discovery_chain
        or epoch.discovery_evidence.discovery_stream_id
        != artifact.discovery_transcript.stream_identity.source_stream_id
    ):
        raise RowObservationIndependentVerificationV2Failure(
            "initial confidence epoch does not bind both raw lanes"
        )
    _verify_confidence_binding(
        artifact.discovery_transcript.observations,
        epoch.discovery_evidence.observations,
    )
    _verify_confidence_binding(
        previous.observations,
        artifact.confidence_snapshot.validation_prefix.observations,
    )
    confidence.verify_partial_support_confidence_snapshot_v2(
        artifact.confidence_snapshot
    )
    expected_payload = {
        "schema": "acfqp.v072_development_row_acquisition.v1",
        "schema_version": adapter.SCHEMA_VERSION,
        "proposed_contract_version": adapter.PROPOSED_CONTRACT_VERSION,
        "profile_key": adapter.PROFILE_KEY,
        "preregistration_id": _preregistration_id(),
        "row_id": artifact.row.physical_row_id,
        "arm": artifact.arm,
        "confidence_row_binding_id": (
            artifact.confidence_row_binding.row_binding_id
        ),
        "discovery_transcript_id": (
            artifact.discovery_transcript.transcript_id
        ),
        "support_epoch_id": epoch.support_epoch_id,
        "validation_transcript_ids": [
            item.transcript_id for item in artifact.validation_history
        ],
        "confidence_snapshot_id": artifact.confidence_snapshot.snapshot_id,
        "selected_checkpoint_draw_count": (
            previous.selected_checkpoint_draw_count
        ),
        "role": ROLE,
        "registered_target_evidence": False,
    }
    expected_artifact_id = _hash(
        ADAPTER_DOMAINS["acquisition"], expected_payload
    )
    if artifact.acquisition_id != expected_artifact_id:
        raise RowObservationIndependentVerificationV2Failure(
            "acquisition artifact content ID does not replay"
        )
    return IndependentRowObservationVerificationV2(
        artifact.acquisition_id,
        "INITIAL_OR_EXTENDED",
        discovery_draws + validation_replays,
        discovery_chunks + validation_chunks,
        artifact.confidence_snapshot.snapshot_id,
        previous.selected_checkpoint_draw_count,
        previous.work.newly_observed_draws,
    )


def verify_development_synthetic_row_promotion_v2(
    artifact: adapter.DevelopmentSyntheticPromotedRowAcquisitionV2,
) -> IndependentRowObservationVerificationV2:
    """Replay promotion, including parent novelty and fresh-evidence quarantine."""

    if type(artifact) is not adapter.DevelopmentSyntheticPromotedRowAcquisitionV2:
        raise RowObservationIndependentVerificationV2Failure(
            "verification requires an exact promoted acquisition artifact"
        )
    parent_verification = verify_development_synthetic_row_acquisition_v2(
        artifact.parent_acquisition
    )
    parent = artifact.parent_acquisition
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
    next_semantics = _expected_support_semantics_id(
        parent.row,
        2,
        parent_semantics,
        promoted_descriptor_ids,
    )
    next_chain = _expected_support_chain_id(
        parent.row,
        parent.arm,
        2,
        next_semantics,
        parent.confidence_snapshot.snapshot_id,
    )
    replayed, chunks = _verify_transcript(
        artifact.fresh_validation_transcript,
        row=parent.row,
        arm=parent.arm,
        lane=confidence.ConfidenceObservationLaneV2.VALIDATION,
        epoch_index=2,
        support_chain_id=next_chain,
        arm_free_support_semantics_id=next_semantics,
        previous=None,
    )
    epoch = artifact.promoted_support_epoch
    expected_support = tuple(
        sorted(
            set(parent.support_epoch.support_descriptor_ids)
            | set(parent.confidence_snapshot.novel_descriptor_ids)
        )
    )
    if (
        type(epoch) is not confidence.PromotedSupportEpochV2
        or epoch.parent_snapshot != parent.confidence_snapshot
        or epoch.epoch_index != 2
        or epoch.support_epoch_chain_id != next_chain
        or epoch.validation_stream_id
        != artifact.fresh_validation_transcript.stream_identity.source_stream_id
        or tuple(sorted(epoch.support_descriptor_ids)) != expected_support
        or not parent.confidence_snapshot.novel_descriptor_ids
        or epoch.promotion_evidence.fresh_discovery_draw_count != 0
        or set(epoch.excluded_probability_sample_ids)
        & set(
            item.sample_id
            for item in artifact.fresh_validation_transcript.observations
        )
        or artifact.fresh_discovery_draw_count != 0
    ):
        raise RowObservationIndependentVerificationV2Failure(
            "promotion omitted novelty, reused samples, or changed epoch"
        )
    _verify_confidence_binding(
        artifact.fresh_validation_transcript.observations,
        artifact.confidence_snapshot.validation_prefix.observations,
    )
    confidence.verify_partial_support_confidence_snapshot_v2(
        artifact.confidence_snapshot
    )
    expected_payload = {
        "schema": "acfqp.v072_development_row_promotion.v1",
        "schema_version": adapter.SCHEMA_VERSION,
        "profile_key": adapter.PROFILE_KEY,
        "parent_acquisition_id": parent.acquisition_id,
        "parent_snapshot_id": parent.confidence_snapshot.snapshot_id,
        "promoted_support_epoch_id": epoch.support_epoch_id,
        "fresh_validation_transcript_id": (
            artifact.fresh_validation_transcript.transcript_id
        ),
        "confidence_snapshot_id": artifact.confidence_snapshot.snapshot_id,
        "fresh_discovery_draw_count": 0,
        "fresh_validation_draw_count": 2_048,
        "old_probability_samples_reused": False,
        "all_parent_novel_descriptors_promoted": True,
        "role": ROLE,
        "registered_target_evidence": False,
    }
    expected_promotion_id = _hash(
        ADAPTER_DOMAINS["promotion"], expected_payload
    )
    if artifact.promotion_id != expected_promotion_id:
        raise RowObservationIndependentVerificationV2Failure(
            "promotion artifact content ID does not replay"
        )
    return IndependentRowObservationVerificationV2(
        artifact.promotion_id,
        "PROMOTION",
        parent_verification.replayed_raw_observations + replayed,
        parent_verification.replayed_chunks + chunks,
        artifact.confidence_snapshot.snapshot_id,
        replayed,
        replayed,
    )


__all__ = [
    "IndependentRowObservationVerificationV2",
    "PROFILE_KEY",
    "RowObservationIndependentVerificationV2Failure",
    "SCHEMA_VERSION",
    "verify_development_synthetic_row_acquisition_v2",
    "verify_development_synthetic_row_promotion_v2",
]
