"""Independent verifier for the strict V0-072 matched-direct schedule."""

from __future__ import annotations

from dataclasses import dataclass, fields
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json, parse_content_id
from acfqp import exact_lazy_h2_independent_verifier_v1 as lazy_independent
from acfqp import exact_lazy_h2_robust_planner_v1 as lazy
from acfqp import partial_support_confidence_v2 as confidence
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import row_bound_observation_core_v2 as row_core
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_cold_h2_closure_independent_verifier_v1 as closure_independent
from acfqp import v072_cold_h2_model_builders_independent_verifier_v1 as model_independent
from acfqp import v072_confidence_row_projection_independent_verifier_v1 as projection_independent
from acfqp import v072_matched_direct_ground_baseline_v1 as baseline


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v072_matched_direct_ground_baseline_independent_verifier_v1"
VERIFICATION_DOMAIN = (
    "acfqp:v072-matched-direct-ground-baseline-independent-verification:v1"
)


class V072MatchedDirectIndependentVerificationFailure(ValueError):
    """The claimed schedule differs from independent replay."""


def _fail(message: str) -> None:
    raise V072MatchedDirectIndependentVerificationFailure(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072MatchedDirectIndependentVerificationFailure(
            f"{label} is not one content ID"
        ) from error


INDEPENDENT_DOMAIN_TAGS = {
    "backend": "acfqp:v072-matched-direct-development-backend:v1",
    "context": "acfqp:v072-matched-direct-development-context:v1",
    "state": "acfqp:v072-matched-direct-development-state:v1",
    "action": "acfqp:v072-matched-direct-development-action:v1",
    "row": "acfqp:v072-matched-direct-development-row:v1",
    "support_semantics": (
        "acfqp:v072-matched-direct-development-support-semantics:v1"
    ),
    "support_chain": (
        "acfqp:v072-matched-direct-development-support-chain:v1"
    ),
    "stream": "acfqp:v072-matched-direct-development-stream:v1",
    "descriptor": "acfqp:v072-matched-direct-development-descriptor:v1",
    "raw_digest": "acfqp:v072-matched-direct-development-raw-digest:v1",
    "commitment": "acfqp:v072-matched-direct-development-commitment:v1",
    "source_observation": (
        "acfqp:v072-matched-direct-development-source-observation:v1"
    ),
    "replay": "acfqp:v072-matched-direct-row-replay:v1",
    "acquisition": "acfqp:v072-matched-direct-row-acquisition:v1",
    "checkpoint": "acfqp:v072-matched-direct-checkpoint-evidence:v1",
    "work": "acfqp:v072-matched-direct-checkpoint-work:v1",
    "record": "acfqp:v072-matched-direct-checkpoint-record:v1",
    "run": "acfqp:v072-matched-direct-run:v1",
}


def _hash(
    role: str,
    payload: Mapping[str, Any],
    *,
    raw_suffix: bytes = b"",
) -> str:
    data = (
        INDEPENDENT_DOMAIN_TAGS[role].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    )
    if raw_suffix:
        data += b"\x00" + raw_suffix
    return hashlib.sha256(data).hexdigest()


def _core_hash(role: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        row_core.DOMAIN_TAGS[role].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _fdoc(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _expected_context_id() -> str:
    return _hash(
        "context",
        {
            "schema": "acfqp.v072_matched_direct_development_context.v1",
            "schema_version": baseline.SCHEMA_VERSION,
            "root_ranks": [1, 1, 2, 0],
            "child_ranks": [2, 0, 1, 1],
            "horizon": 2,
            "rank_cap": 4,
            "physical_row_count": 2,
            "registered_target_evidence": False,
        },
    )


def _verify_physical_row(
    row: baseline.DevelopmentMatchedDirectPhysicalRowV1,
) -> None:
    if type(row) is not baseline.DevelopmentMatchedDirectPhysicalRowV1:
        _fail("physical row has a foreign concrete type")
    expected_values = {
        "ROOT": (2, (1, 1, 2, 0), (0, 1, 0), (2, 0, 1, 1)),
        "CHILD": (1, (2, 0, 1, 1), (2, 3, 2), (2, 0, 2, 0)),
    }
    if row.row_key not in expected_values:
        _fail("unknown development physical row")
    horizon, ranks, action, successor = expected_values[row.row_key]
    if (
        row.remaining_horizon != horizon
        or row.state_ranks != ranks
        or row.action != action
        or row.success_next_ranks != successor
        or row.context_id != _expected_context_id()
    ):
        _fail("physical row semantics changed")
    state_id = _hash(
        "state",
        {
            "schema": "acfqp.v072_matched_direct_development_state.v1",
            "schema_version": baseline.SCHEMA_VERSION,
            "context_id": row.context_id,
            "row_key": row.row_key,
            "remaining_horizon": horizon,
            "ranks": list(ranks),
        },
    )
    action_id = _hash(
        "action",
        {
            "schema": "acfqp.v072_matched_direct_development_action.v1",
            "schema_version": baseline.SCHEMA_VERSION,
            "context_id": row.context_id,
            "state_semantic_id": state_id,
            "remaining_horizon": horizon,
            "action": list(action),
        },
    )
    arm_free = _hash(
        "row",
        {
            "schema": "acfqp.v072_matched_direct_arm_free_row.v1",
            "schema_version": baseline.SCHEMA_VERSION,
            "context_id": row.context_id,
            "state_semantic_id": state_id,
            "action_semantic_id": action_id,
            "remaining_horizon": horizon,
        },
    )
    physical = _hash(
        "row",
        {
            "schema": "acfqp.v072_matched_direct_physical_row.v1",
            "schema_version": baseline.SCHEMA_VERSION,
            "arm_free_row_id": arm_free,
            "ground_row_semantics": "STATE_ACTION_REMAINING_HORIZON",
        },
    )
    rank = ranks[action[0]]
    reward = Fraction(2 ** (rank + 1), 2 ** 5) / 2
    payload = {
        "schema": "acfqp.v072_matched_direct_physical_row_record.v1",
        "schema_version": baseline.SCHEMA_VERSION,
        "context_id": row.context_id,
        "row_key": row.row_key,
        "state_semantic_id": state_id,
        "action_semantic_id": action_id,
        "arm_free_row_id": arm_free,
        "physical_row_id": physical,
        "remaining_horizon": horizon,
        "state_ranks": list(ranks),
        "action": list(action),
        "success_next_ranks": list(successor),
        "exact_row_reward": _fdoc(reward),
        "registered_target_evidence": False,
    }
    if (
        row.state_semantic_id != state_id
        or row.action_semantic_id != action_id
        or row.arm_free_row_id != arm_free
        or row.physical_row_id != physical
        or row.exact_row_reward != reward
        or row.row_record_id != _hash("row", payload)
    ):
        _fail("physical row content identity does not replay")


def _expected_descriptor(
    row: baseline.DevelopmentMatchedDirectPhysicalRowV1,
    failure: bool,
) -> tuple[str, dict[str, Any]]:
    terminal = failure or row.remaining_horizon == 1
    ranks = row.state_ranks if failure else row.success_next_ranks
    document = {
        "schema": "acfqp.v072_matched_direct_semantic_transition.v1",
        "schema_version": baseline.SCHEMA_VERSION,
        "context_id": row.context_id,
        "physical_row_id": row.physical_row_id,
        "next_state": {"ranks": list(ranks), "failure": failure},
        "realized_row_reward": _fdoc(row.exact_row_reward),
        "failure": failure,
        "terminal": terminal,
        "registered_target_evidence": False,
    }
    descriptor_id = _hash("descriptor", document)
    document["descriptor_id"] = descriptor_id
    return descriptor_id, document


def _verify_stream(
    stream: row_core.RowObservationStreamIdentityV2,
    row: baseline.DevelopmentMatchedDirectPhysicalRowV1,
    lane: confidence.ConfidenceObservationLaneV2,
    support_ids: tuple[str, ...],
    parent_transcript_id: str | None,
) -> None:
    semantics = _hash(
        "support_semantics",
        {
            "schema": "acfqp.v072_matched_direct_support_semantics.v1",
            "schema_version": baseline.SCHEMA_VERSION,
            "context_id": row.context_id,
            "arm_free_row_id": row.arm_free_row_id,
            "lane": lane.value,
            "support_descriptor_ids": list(support_ids),
            "arm_serialized": False,
        },
    )
    chain = _hash(
        "support_chain",
        {
            "schema": "acfqp.v072_matched_direct_support_chain.v1",
            "schema_version": baseline.SCHEMA_VERSION,
            "context_id": row.context_id,
            "arm": baseline.ARM,
            "physical_row_id": row.physical_row_id,
            "lane": lane.value,
            "support_semantics_id": semantics,
            "parent_transcript_id": parent_transcript_id,
        },
    )
    source_stream = _hash(
        "stream",
        {
            "schema": "acfqp.v072_matched_direct_source_stream.v1",
            "schema_version": baseline.SCHEMA_VERSION,
            "context_id": row.context_id,
            "arm": baseline.ARM,
            "arm_free_row_id": row.arm_free_row_id,
            "lane": lane.value,
            "support_semantics_id": semantics,
        },
    )
    material = tuple(
        sorted(
            (
                ("arm_free_row_id", row.arm_free_row_id),
                ("lane", lane.value),
                ("support_semantics_id", semantics),
            )
        )
    )
    expected = row_core.RowObservationStreamIdentityV2(
        prereg.DRAFT_PREREGISTRATION_ID,
        _hash(
            "backend",
            {
                "schema": "acfqp.v072_matched_direct_development_backend.v1",
                "schema_version": baseline.SCHEMA_VERSION,
                "law": (
                    "COUNTER_PREFIX_FAILURE_RESIDUES_MOD_100_"
                    "DEVELOPMENT_NONCONFIRMATORY"
                ),
                "formal_exact_iid_claimed": False,
                "registered_target_evidence": False,
            },
        ),
        row.context_id,
        baseline.ARM,
        row.physical_row_id,
        row.arm_free_row_id,
        chain,
        semantics,
        lane,
        0 if lane is confidence.ConfidenceObservationLaneV2.DISCOVERY else 1,
        material,
        source_stream,
        row_core.RowObservationEvidenceClassV2.DEVELOPMENT_SYNTHETIC,
        baseline.ROLE,
        False,
    )
    if stream != expected:
        _fail("row stream identity or support chain changed")


def _expected_raw(
    row: baseline.DevelopmentMatchedDirectPhysicalRowV1,
    stream: row_core.RowObservationStreamIdentityV2,
    index: int,
    law: baseline.DevelopmentMatchedDirectLawV1,
) -> row_core.RowBoundRawObservationV2:
    residues = (
        1
        if law
        is baseline.DevelopmentMatchedDirectLawV1.FAILURE_RESIDUE_1_OF_100
        else 3
    )
    failure = (index - 1) % 100 < residues
    descriptor_id, descriptor_document = _expected_descriptor(row, failure)
    raw_payload = {
        "schema": "acfqp.v072_matched_direct_raw_digest.v1",
        "schema_version": baseline.SCHEMA_VERSION,
        "seed_identity_id": stream.seed_identity_id,
        "sequence_index": index,
        "law": law.value,
        "failure": failure,
        "outcome_descriptor_id": descriptor_id,
    }
    raw_digest = _hash(
        "raw_digest",
        raw_payload,
        raw_suffix=residues.to_bytes(1, "big") + index.to_bytes(8, "big"),
    )
    commitment_payload = {
        "schema": "acfqp.v072_matched_direct_commitment.v1",
        "schema_version": baseline.SCHEMA_VERSION,
        "source_stream_id": stream.source_stream_id,
        "seed_identity_id": stream.seed_identity_id,
        "sequence_index": index,
        "raw_digest": raw_digest,
    }
    commitment = _hash("commitment", commitment_payload)
    source_payload = {
        "schema": "acfqp.v072_matched_direct_source_observation.v1",
        "schema_version": baseline.SCHEMA_VERSION,
        "source_stream_id": stream.source_stream_id,
        "seed_identity_id": stream.seed_identity_id,
        "sequence_index": index,
        "law": law.value,
        "raw_digest": raw_digest,
        "commitment_id": commitment,
        "outcome_descriptor_id": descriptor_id,
        "outcome_descriptor": descriptor_document,
        "registered_target_evidence": False,
    }
    source_id = _hash("source_observation", source_payload)
    return row_core.freeze_source_observation_v2(
        stream_identity=stream,
        sequence_index=index,
        source_observation_id=source_id,
        source_commitment_id=commitment,
        raw_digest=raw_digest,
        outcome_descriptor_id=descriptor_id,
        source_document={**source_payload, "source_observation_id": source_id},
        outcome_document=descriptor_document,
    )


def _verify_transcript(
    transcript: row_core.RowObservationTranscriptV2,
    *,
    row: baseline.DevelopmentMatchedDirectPhysicalRowV1,
    law: baseline.DevelopmentMatchedDirectLawV1,
    lane: confidence.ConfidenceObservationLaneV2,
    support_ids: tuple[str, ...],
    parent_transcript_id: str | None,
    previous: row_core.RowObservationTranscriptV2 | None,
) -> None:
    if type(transcript) is not row_core.RowObservationTranscriptV2:
        _fail("transcript has a foreign type")
    _verify_stream(
        transcript.stream_identity,
        row,
        lane,
        support_ids,
        parent_transcript_id,
    )
    prior_id = None if previous is None else previous.transcript_id
    prior_count = 0 if previous is None else previous.selected_checkpoint_draw_count
    if (
        transcript.previous_transcript_id != prior_id
        or transcript.previous_draw_count != prior_count
        or (
            previous is not None
            and transcript.chunks[: len(previous.chunks)] != previous.chunks
        )
    ):
        _fail("transcript reset or dropped its immutable prefix")
    expected_start = 1
    previous_chunk_id = None
    reused_chunk_count = 0 if previous is None else len(previous.chunks)
    for chunk_index, chunk in enumerate(transcript.chunks):
        if (
            type(chunk) is not row_core.RowObservationTranscriptChunkV2
            or chunk.start_sequence_index != expected_start
            or chunk.previous_chunk_id != previous_chunk_id
            or chunk.end_sequence_index
            != chunk.start_sequence_index + len(chunk.observations) - 1
        ):
            _fail("transcript chunk chain is partial or gapped")
        if chunk_index >= reused_chunk_count:
            for observation in chunk.observations:
                expected = _expected_raw(
                    row,
                    transcript.stream_identity,
                    observation.sequence_index,
                    law,
                )
                if (
                    observation != expected
                    or canonical_json_bytes(observation.to_document())
                    != canonical_json_bytes(expected.to_document())
                ):
                    _fail(
                        "raw observation differs from independent law replay"
                    )
        chunk_payload = {
            "schema": "acfqp.v072_row_observation_transcript_chunk.v2",
            "schema_version": row_core.SCHEMA_VERSION,
            "stream_binding_id": transcript.stream_identity.stream_binding_id,
            "start_sequence_index": chunk.start_sequence_index,
            "end_sequence_index": chunk.end_sequence_index,
            "previous_chunk_id": previous_chunk_id,
            "observation_ids": [item.observation_id for item in chunk.observations],
            "source_commitment_ids": [
                item.source_commitment_id for item in chunk.observations
            ],
            "exact_source_documents_embedded": True,
        }
        if chunk.chunk_id != _core_hash("chunk", chunk_payload):
            _fail("transcript chunk content ID does not replay")
        expected_start = chunk.end_sequence_index + 1
        previous_chunk_id = chunk.chunk_id
    count = expected_start - 1
    new_count = count - prior_count
    work_payload = {
        "schema": "acfqp.v072_row_observation_work.v2",
        "schema_version": row_core.SCHEMA_VERSION,
        "stream_binding_id": transcript.stream_identity.stream_binding_id,
        "total_prefix_draws": count,
        "reused_prefix_draws": prior_count,
        "newly_observed_draws": new_count,
        "source_commitments_verified_during_build": new_count,
        "chunks_written_during_build": (
            len(transcript.chunks)
            - (0 if previous is None else len(previous.chunks))
        ),
    }
    work_id = _core_hash("work", work_payload)
    transcript_payload = {
        "schema": "acfqp.v072_row_observation_transcript.v2",
        "schema_version": row_core.SCHEMA_VERSION,
        "proposed_contract_version": row_core.PROPOSED_CONTRACT_VERSION,
        "profile_key": row_core.PROFILE_KEY,
        "stream_binding_id": transcript.stream_identity.stream_binding_id,
        "selected_checkpoint_draw_count": count,
        "chunk_ids": [item.chunk_id for item in transcript.chunks],
        "terminal_chunk_id": transcript.chunks[-1].chunk_id,
        "previous_transcript_id": prior_id,
        "previous_draw_count": prior_count,
        "work_id": work_id,
        "immutable_prefix": True,
    }
    if (
        count != transcript.selected_checkpoint_draw_count
        or transcript.work.to_document() != {**work_payload, "work_id": work_id}
        or transcript.transcript_id
        != _core_hash("transcript", transcript_payload)
    ):
        _fail("transcript draw/work/identity accounting does not replay")


def _verify_acquisition(
    item: baseline.DevelopmentMatchedDirectRowAcquisitionV1,
    *,
    expected_checkpoint: int,
) -> None:
    if (
        type(item) is not baseline.DevelopmentMatchedDirectRowAcquisitionV1
        or item.selected_checkpoint_draw_count != expected_checkpoint
    ):
        _fail("checkpoint row acquisition is missing or asynchronous")
    _verify_physical_row(item.row)
    if item.law not in tuple(baseline.DevelopmentMatchedDirectLawV1):
        _fail("row law is invalid")
    _verify_transcript(
        item.discovery_transcript,
        row=item.row,
        law=item.law,
        lane=confidence.ConfidenceObservationLaneV2.DISCOVERY,
        support_ids=(),
        parent_transcript_id=None,
        previous=None,
    )
    support_ids = tuple(
        sorted(
            {
                observation.outcome_descriptor_id
                for observation in item.discovery_transcript.observations
            }
        )
    )
    previous = None
    for transcript in item.validation_history:
        _verify_transcript(
            transcript,
            row=item.row,
            law=item.law,
            lane=confidence.ConfidenceObservationLaneV2.VALIDATION,
            support_ids=support_ids,
            parent_transcript_id=item.discovery_transcript.transcript_id,
            previous=previous,
        )
        previous = transcript
    expected_history = baseline.CHECKPOINTS[: len(item.validation_history)]
    if tuple(
        member.selected_checkpoint_draw_count
        for member in item.validation_history
    ) != expected_history:
        _fail("row validation history skipped one global checkpoint")
    confidence_verification = confidence.verify_partial_support_confidence_snapshot_v2(
        item.confidence_snapshot
    )
    projection_verification = (
        projection_independent.verify_v072_confidence_row_projection_v1(
            item.source_projection
        )
    )
    final = item.validation_history[-1]
    if (
        item.confidence_verification != confidence_verification
        or item.projection_verification != projection_verification
        or item.confidence_snapshot.validation_prefix.observations
        != tuple(
            confidence.freeze_confidence_observation_v2(observation)
            for observation in final.observations
        )
        or item.source_projection.confidence_snapshot
        != item.confidence_snapshot
    ):
        _fail("confidence/projection result was transplanted")
    replay_payload = {
        "schema": "acfqp.v072_matched_direct_row_replay.v1",
        "schema_version": baseline.SCHEMA_VERSION,
        "profile_key": baseline.PROFILE_KEY,
        "physical_row_id": item.row.physical_row_id,
        "discovery_transcript_id": item.discovery_transcript.transcript_id,
        "validation_transcript_id": final.transcript_id,
        "validation_prefix_id": item.confidence_snapshot.validation_prefix.prefix_id,
        "selected_checkpoint_draw_count": expected_checkpoint,
        "previous_validation_transcript_id": final.previous_transcript_id,
        "newly_observed_validation_draws": final.work.newly_observed_draws,
        "replayed_raw_observation_count": (
            baseline.DISCOVERY_DRAWS_PER_ROW + expected_checkpoint
        ),
        "immutable_prefix_verified": True,
        "exact_development_law_replayed": True,
        "registered_target_evidence": False,
    }
    if (
        item.row_replay.verification_id != _hash("replay", replay_payload)
        or item.row_replay.to_document()
        != {
            **replay_payload,
            "verification_id": _hash("replay", replay_payload),
        }
    ):
        _fail("row replay verification content ID changed")
    acquisition_payload = {
        "schema": "acfqp.v072_matched_direct_row_acquisition.v1",
        "schema_version": baseline.SCHEMA_VERSION,
        "profile_key": baseline.PROFILE_KEY,
        "row_record_id": item.row.row_record_id,
        "law": item.law.value,
        "confidence_row_binding_id": item.confidence_row_binding.row_binding_id,
        "discovery_transcript_id": item.discovery_transcript.transcript_id,
        "support_epoch_id": item.support_epoch.support_epoch_id,
        "validation_transcript_ids": [
            transcript.transcript_id for transcript in item.validation_history
        ],
        "confidence_snapshot_id": item.confidence_snapshot.snapshot_id,
        "confidence_verification_id": item.confidence_verification.verification_id,
        "source_projection_id": item.source_projection.projection_id,
        "projection_verification_id": item.projection_verification.verification_id,
        "row_replay_verification_id": item.row_replay.verification_id,
        "selected_checkpoint_draw_count": expected_checkpoint,
        "registered_target_evidence": False,
    }
    if item.acquisition_id != _hash("acquisition", acquisition_payload):
        _fail("row acquisition content ID does not replay")


def _work_payload(
    value: baseline.MatchedDirectCheckpointWorkV1,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_matched_direct_checkpoint_work.v1",
        "schema_version": baseline.SCHEMA_VERSION,
        "checkpoint": value.checkpoint,
        "physical_row_count": value.physical_row_count,
        "discovery_new_draws": value.discovery_new_draws,
        "validation_new_draws": value.validation_new_draws,
        "accepted_new_draws": value.accepted_new_draws,
        "cumulative_accepted_draws": value.cumulative_accepted_draws,
        "raw_observations_replayed": value.raw_observations_replayed,
        "confidence_verifications": value.confidence_verifications,
        "projection_verifications": value.projection_verifications,
        "direct_model_builds": value.direct_model_builds,
        "direct_model_independent_verifications": (
            value.direct_model_independent_verifications
        ),
        "exact_lazy_ground_planner_calls": value.exact_lazy_ground_planner_calls,
        "independent_lazy_proof_verifications": (
            value.independent_lazy_proof_verifications
        ),
        "quotient_model_builds": value.quotient_model_builds,
        "quotient_planner_calls": value.quotient_planner_calls,
        "source_prior_reads": value.source_prior_reads,
        "selected_row_acquisition_calls": value.selected_row_acquisition_calls,
        "local_promotion_calls": value.local_promotion_calls,
        "fallback_calls": value.fallback_calls,
        "hidden_law_queries": value.hidden_law_queries,
        "exact_ground_evaluator_calls": value.exact_ground_evaluator_calls,
        "crn_cost_discount_draws": value.crn_cost_discount_draws,
    }


@dataclass(frozen=True, slots=True)
class MatchedDirectGroundIndependentVerificationV1:
    run_id: str
    logical_occurrence_id: str
    terminal_class: str
    terminal_code: str
    stopped_checkpoint: int
    checkpoint_record_count: int
    physical_row_count: int
    total_accepted_draws: int
    verified_raw_observation_count: int
    verified_direct_model_count: int
    verified_lazy_proof_count: int
    forbidden_route_invocation_count: int = 0
    exact_evaluator_supplement_count: int = 0
    registered_target_evidence_count: int = 0
    verification_result: str = (
        "VALID_INDEPENDENT_MATCHED_DIRECT_SYNCHRONOUS_SCHEDULE"
    )

    def __post_init__(self) -> None:
        _cid(self.run_id, "verified run")
        _cid(self.logical_occurrence_id, "verified occurrence")
        if (
            self.stopped_checkpoint not in baseline.CHECKPOINTS
            or self.checkpoint_record_count <= 0
            or self.physical_row_count <= 1
            or self.total_accepted_draws <= 0
            or self.verified_raw_observation_count
            < self.total_accepted_draws
            or self.verified_direct_model_count
            != self.checkpoint_record_count
            or self.verified_lazy_proof_count
            != self.checkpoint_record_count
            or self.forbidden_route_invocation_count != 0
            or self.exact_evaluator_supplement_count != 0
            or self.registered_target_evidence_count != 0
        ):
            _fail("independent matched-direct result is malformed")

    @property
    def verification_id(self) -> str:
        payload = {
            "schema": (
                "acfqp.v072_matched_direct_ground_independent_"
                "verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "run_id": self.run_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "terminal_class": self.terminal_class,
            "terminal_code": self.terminal_code,
            "stopped_checkpoint": self.stopped_checkpoint,
            "checkpoint_record_count": self.checkpoint_record_count,
            "physical_row_count": self.physical_row_count,
            "total_accepted_draws": self.total_accepted_draws,
            "verified_raw_observation_count": (
                self.verified_raw_observation_count
            ),
            "verified_direct_model_count": self.verified_direct_model_count,
            "verified_lazy_proof_count": self.verified_lazy_proof_count,
            "forbidden_route_invocation_count": 0,
            "exact_evaluator_supplement_count": 0,
            "registered_target_evidence_count": 0,
            "verification_result": self.verification_result,
        }
        return hashlib.sha256(
            VERIFICATION_DOMAIN.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(payload)
        ).hexdigest()


def _verify_matched_direct_ground_run_independently_impl_v1(
    claimed: baseline.MatchedDirectGroundRunV1,
) -> MatchedDirectGroundIndependentVerificationV1:
    if type(claimed) is not baseline.MatchedDirectGroundRunV1:
        _fail("verifier requires the exact matched-direct run type")
    _cid(claimed.logical_occurrence_id, "claimed occurrence")
    checkpoints = tuple(
        record.evidence.checkpoint for record in claimed.checkpoint_records
    )
    if checkpoints != baseline.CHECKPOINTS[: len(checkpoints)]:
        _fail("checkpoint schedule is partial, reordered, or skipped")
    expected_rows = ("CHILD", "ROOT")
    prior = None
    verified_raw = 0
    for ordinal, record in enumerate(claimed.checkpoint_records):
        if type(record) is not baseline.MatchedDirectCheckpointRecordV1:
            _fail("checkpoint record has a foreign type")
        evidence = record.evidence
        checkpoint = checkpoints[ordinal]
        if (
            type(evidence) is not baseline.MatchedDirectCheckpointEvidenceV1
            or evidence.checkpoint != checkpoint
            or evidence.closure_bundle.arm != baseline.ARM
            or evidence.closure_bundle.consumer_profile.consumer_routes
            != ("DIRECT",)
            or tuple(item.row.row_key for item in evidence.acquisitions)
            != expected_rows
        ):
            _fail("checkpoint inventory is not the full fixed direct arm")
        for acquisition in evidence.acquisitions:
            _verify_acquisition(
                acquisition, expected_checkpoint=checkpoint
            )
            if acquisition.law is not claimed.law:
                _fail("row law was transplanted across the run")
            verified_raw += (
                baseline.DISCOVERY_DRAWS_PER_ROW + checkpoint
            )
        if prior is not None:
            prior_by_id = {
                item.row.physical_row_id: item
                for item in prior.evidence.acquisitions
            }
            for current in evidence.acquisitions:
                old = prior_by_id[current.row.physical_row_id]
                if (
                    current.discovery_transcript != old.discovery_transcript
                    or current.support_epoch != old.support_epoch
                    or current.validation_history[:-1]
                    != old.validation_history
                    or current.validation_history[-1].previous_transcript_id
                    != old.validation_history[-1].transcript_id
                ):
                    _fail("row reset/drop attack changed a checkpoint prefix")
        prior = record
        closure_independent.verify_v072_cold_h2_closure_independently_v1(
            public_graph=baseline._DevelopmentPublicGraphV1(),
            authoritative_row_evidence=evidence.closure_bundle.all_rows,
            claimed=evidence.closure_bundle,
        )
        checkpoint_payload = {
            "schema": "acfqp.v072_matched_direct_checkpoint_evidence.v1",
            "schema_version": baseline.SCHEMA_VERSION,
            "profile_key": baseline.PROFILE_KEY,
            "arm": baseline.ARM,
            "checkpoint": checkpoint,
            "closure_id": evidence.closure_bundle.closure_id,
            "acquisition_ids": [
                item.acquisition_id for item in evidence.acquisitions
            ],
            "bound_projection_ids": [
                item.projection_binding_id for item in evidence.bound_projections
            ],
            "physical_row_ids": [
                item.row.physical_row_id for item in evidence.acquisitions
            ],
            "all_rows_checkpoint_complete": True,
            "consumer_routes": ["DIRECT"],
        }
        if evidence.checkpoint_evidence_id != _hash(
            "checkpoint", checkpoint_payload
        ):
            _fail("checkpoint evidence identity does not replay")
        model_verification = (
            model_independent
            .verify_v072_cold_h2_ground_direct_snapshot_independently_v1(
                record.direct_snapshot
            )
        )
        if model_verification != record.model_verification:
            _fail("direct model snapshot or collapse proof was transplanted")
        if (
            record.planner_result.status
            is not lazy.ExactLazyH2SolveStatus.SOLVED
        ):
            if record.proof_verification is not None:
                _fail("resource-exhausted solve cannot carry a proof")
        else:
            proof = lazy_independent.verify_exact_lazy_h2_solve_result_v1(
                record.direct_snapshot.planner_model,
                record.direct_snapshot.threshold_profile,
                record.planner_result,
            )
            if proof != record.proof_verification:
                _fail("lazy result differs from independent proof replay")
        previous_checkpoint = 0 if ordinal == 0 else checkpoints[ordinal - 1]
        expected_discovery = (
            len(evidence.acquisitions) * baseline.DISCOVERY_DRAWS_PER_ROW
            if ordinal == 0
            else 0
        )
        expected_validation = len(evidence.acquisitions) * (
            checkpoint - previous_checkpoint
        )
        work = record.work
        if (
            work.discovery_new_draws != expected_discovery
            or work.validation_new_draws != expected_validation
            or work.accepted_new_draws
            != expected_discovery + expected_validation
            or work.cumulative_accepted_draws
            != len(evidence.acquisitions)
            * (baseline.DISCOVERY_DRAWS_PER_ROW + checkpoint)
            or work.raw_observations_replayed
            != work.cumulative_accepted_draws
            or work.confidence_verifications != len(evidence.acquisitions)
            or work.projection_verifications != len(evidence.acquisitions)
            or work.work_id != _hash("work", _work_payload(work))
            or any(
                getattr(work, name) != 0
                for name in (
                    "quotient_model_builds",
                    "quotient_planner_calls",
                    "source_prior_reads",
                    "selected_row_acquisition_calls",
                    "local_promotion_calls",
                    "fallback_calls",
                    "hidden_law_queries",
                    "exact_ground_evaluator_calls",
                    "crn_cost_discount_draws",
                )
            )
        ):
            _fail("checkpoint work is incomplete or uses a forbidden route")
        audit = record.planner_result.audit
        record_payload = {
            "schema": "acfqp.v072_matched_direct_checkpoint_record.v1",
            "schema_version": baseline.SCHEMA_VERSION,
            "profile_key": baseline.PROFILE_KEY,
            "checkpoint_evidence_id": evidence.checkpoint_evidence_id,
            "direct_snapshot_id": record.direct_snapshot.snapshot_id,
            "model_verification_id": record.model_verification.verification_id,
            "planner_status": record.planner_result.status.value,
            "audit_id": None if audit is None else audit.audit_id,
            "original_proof_id": (
                None
                if record.planner_result.trace is None
                else record.planner_result.trace.original_proof.proof_id
            ),
            "proof_verification_id": (
                None
                if record.proof_verification is None
                else record.proof_verification.verification_id
            ),
            "resource_exhaustion": (
                None
                if record.planner_result.exhaustion is None
                else {
                    "phase": record.planner_result.exhaustion.phase.value,
                    "code": record.planner_result.exhaustion.code.value,
                    "observed": record.planner_result.exhaustion.observed,
                    "limit": record.planner_result.exhaustion.limit,
                }
            ),
            "status": record.status.value,
            "work_id": work.work_id,
        }
        if record.record_id != _hash("record", record_payload):
            _fail("checkpoint record identity does not replay")

    certified_indices = tuple(
        index
        for index, record in enumerate(claimed.checkpoint_records)
        if record.status
        is baseline.MatchedDirectCheckpointStatusV1.CERTIFIED
    )
    exhausted_indices = tuple(
        index
        for index, record in enumerate(claimed.checkpoint_records)
        if record.status
        is baseline.MatchedDirectCheckpointStatusV1.SOLVER_RESOURCE_EXHAUSTED
    )
    if certified_indices:
        expected_class = (
            baseline.MatchedDirectTerminalClassV1.PLAN_CERTIFICATE
        )
        expected_code = (
            baseline.MatchedDirectTerminalCodeV1
            .MATCHED_DIRECT_GROUND_CERTIFIED
        )
        if certified_indices != (len(claimed.checkpoint_records) - 1,):
            _fail("run continued after or stopped before its first certificate")
    elif exhausted_indices:
        expected_class = (
            baseline.MatchedDirectTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE
        )
        expected_code = (
            baseline.MatchedDirectTerminalCodeV1
            .EXACT_LAZY_RESOURCE_EXHAUSTED
        )
        if exhausted_indices != (len(claimed.checkpoint_records) - 1,):
            _fail("resource exhaustion did not close immediately")
    else:
        expected_class = (
            baseline.MatchedDirectTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE
        )
        expected_code = (
            baseline.MatchedDirectTerminalCodeV1
            .MAXIMUM_DIRECT_CHECKPOINT_EXHAUSTED
        )
        if checkpoints[-1] != baseline.CHECKPOINTS[-1]:
            _fail("noncertificate run stopped before the final checkpoint")
    total = len(claimed.checkpoint_records[0].evidence.acquisitions) * (
        baseline.DISCOVERY_DRAWS_PER_ROW + checkpoints[-1]
    )
    if (
        claimed.terminal_class is not expected_class
        or claimed.terminal_code is not expected_code
        or claimed.stopped_checkpoint != checkpoints[-1]
        or claimed.total_accepted_draws != total
        or claimed.total_random_word_calls != total
        or any(
            getattr(claimed, name) != 0
            for name in (
                "crn_cost_discount_draws",
                "source_prior_reads",
                "quotient_planner_calls",
                "local_promotion_calls",
                "fallback_calls",
                "hidden_law_queries",
                "exact_ground_evaluator_calls",
                "registered_target_evidence_count",
            )
        )
    ):
        _fail("terminal class or aggregate work was forged")
    run_payload = {
        "schema": "acfqp.v072_matched_direct_ground_run.v1",
        "schema_version": baseline.SCHEMA_VERSION,
        "proposed_contract_version": baseline.PROPOSED_CONTRACT_VERSION,
        "profile_key": baseline.PROFILE_KEY,
        "logical_occurrence_id": claimed.logical_occurrence_id,
        "arm": baseline.ARM,
        "law": claimed.law.value,
        "checkpoint_record_ids": [
            item.record_id for item in claimed.checkpoint_records
        ],
        "terminal_class": claimed.terminal_class.value,
        "terminal_code": claimed.terminal_code.value,
        "stopped_checkpoint": claimed.stopped_checkpoint,
        "total_accepted_draws": claimed.total_accepted_draws,
        "total_random_word_calls": claimed.total_random_word_calls,
        "physical_row_count": claimed.physical_row_count,
        "crn_cost_discount_draws": 0,
        "source_prior_reads": 0,
        "quotient_planner_calls": 0,
        "local_promotion_calls": 0,
        "fallback_calls": 0,
        "hidden_law_queries": 0,
        "exact_ground_evaluator_calls": 0,
        "registered_target_evidence_count": 0,
    }
    if claimed.run_id != _hash("run", run_payload):
        _fail("run content identity does not replay")
    return MatchedDirectGroundIndependentVerificationV1(
        claimed.run_id,
        claimed.logical_occurrence_id,
        claimed.terminal_class.value,
        claimed.terminal_code.value,
        claimed.stopped_checkpoint,
        len(claimed.checkpoint_records),
        claimed.physical_row_count,
        claimed.total_accepted_draws,
        verified_raw,
        len(claimed.checkpoint_records),
        len(claimed.checkpoint_records),
    )


def verify_matched_direct_ground_run_independently_v1(
    claimed: baseline.MatchedDirectGroundRunV1,
) -> MatchedDirectGroundIndependentVerificationV1:
    """Normalize every nested semantic-verifier rejection into this domain."""

    try:
        return _verify_matched_direct_ground_run_independently_impl_v1(
            claimed
        )
    except V072MatchedDirectIndependentVerificationFailure:
        raise
    except (ValueError, TypeError, KeyError, AssertionError) as error:
        raise V072MatchedDirectIndependentVerificationFailure(
            f"nested matched-direct semantic replay rejected the run: {error}"
        ) from error


__all__ = [
    "MatchedDirectGroundIndependentVerificationV1",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "V072MatchedDirectIndependentVerificationFailure",
    "verify_matched_direct_ground_run_independently_v1",
]
