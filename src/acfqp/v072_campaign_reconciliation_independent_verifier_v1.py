"""Independent replay verifier for the V0-072 campaign work ledger.

The verifier never calls a reconciliation adapter.  It replays source
authorities, accepted-draw commitment ranges, native work, access ordering,
terminal classification, denominator membership, and every reconciliation
content ID from duplicated normative formulas.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import row_bound_observation_core_v2 as row_core
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_campaign_reconciliation_authority_v1 as claimed_types
from acfqp import v072_development_complete_adaptive_run_v1 as complete
from acfqp import (
    v072_development_complete_adaptive_run_independent_verifier_v1
    as complete_verifier,
)
from acfqp import v072_incremental_materializer_v1 as materializer
from acfqp import v072_matched_direct_ground_baseline_v1 as matched
from acfqp import (
    v072_matched_direct_ground_baseline_independent_verifier_v1
    as matched_verifier,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v072_campaign_reconciliation_independent_verifier_v1"
VERIFICATION_DOMAIN = (
    "acfqp:v072-campaign-reconciliation-independent-verification:v1"
)

DOMAINS = {
    "row_series": "acfqp:v072-reconciliation-row-core-series:v1",
    "crn_group": "acfqp:v072-reconciliation-crn-pairing-group:v1",
    "range": "acfqp:v072-reconciliation-accepted-draw-range:v1",
    "work": "acfqp:v072-reconciliation-operational-work:v1",
    "access": "acfqp:v072-reconciliation-access-order:v1",
    "occurrence": "acfqp:v072-reconciliation-occurrence:v1",
    "campaign": "acfqp:v072-reconciliation-campaign-ledger:v1",
    "context_binding": (
        "acfqp:v072-reconciliation-development-context-binding:v1"
    ),
}
MATERIALIZER_DOMAINS = {
    "stream": "acfqp:v072-development-multirow-raw-stream:v1",
    "raw_commitment": (
        "acfqp:v072-development-multirow-raw-commitment:v1"
    ),
    "raw_range": (
        "acfqp:v072-development-multirow-raw-commitment-range:v1"
    ),
}


class IndependentCampaignReconciliationVerificationFailure(ValueError):
    """The ledger differs from independent source/work replay."""


def _fail(message: str) -> None:
    raise IndependentCampaignReconciliationVerificationFailure(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            domain.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (TypeError, ValueError) as error:
        raise IndependentCampaignReconciliationVerificationFailure(
            f"content replay failed: {error}"
        ) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise IndependentCampaignReconciliationVerificationFailure(
            f"{label} is not one content ID"
        ) from error


def _ordered_digest(values: Iterable[str]) -> tuple[str, str, str, int]:
    digest = hashlib.sha256()
    seen: set[str] = set()
    first = ""
    last = ""
    count = 0
    for value in values:
        _cid(value, "accepted draw commitment")
        if count == 0:
            first = value
        last = value
        digest.update(bytes.fromhex(value))
        seen.add(value)
        count += 1
    if count <= 0 or len(seen) != count:
        _fail("accepted draw range is empty or internally reused")
    return first, last, digest.hexdigest(), count


def _crn_group(seed_identity_id: str, first: int, last: int) -> str:
    _cid(seed_identity_id, "arm-free CRN seed identity")
    return _hash(
        DOMAINS["crn_group"],
        {
            "schema": "acfqp.v072_reconciliation_crn_pairing_group.v1",
            "schema_version": claimed_types.SCHEMA_VERSION,
            "arm_free_stream_identity_id": seed_identity_id,
            "accepted_draw_index_range": {
                "first": first,
                "last": last,
            },
            "arm_serialized": False,
            "cost_discount_allowed": False,
        },
    )


def _suffix_word(stream: Any, index: int) -> int:
    word = int.from_bytes(
        hashlib.sha256(
            b"acfqp:v072-development-multirow-word:v1\x00"
            + bytes.fromhex(stream.seed_id)
            + b"\x00"
            + stream.lane.value.encode("ascii")
            + b"\x00"
            + stream.law_key.value.encode("ascii")
            + b"\x00"
            + index.to_bytes(8, "big")
        ).digest()[:8],
        "big",
    )
    if stream.law_key.value == "HASH_BUCKET_LAW_A":
        if stream.lane.value == "PARENT_FRESH_VALIDATION":
            return (word & ~3) | (index & 1)
        return word & ~3
    if (
        stream.round_index == 2
        and stream.lane.value == "PARENT_FRESH_VALIDATION"
    ):
        return (word & ~3) | (index & 1)
    if stream.lane.value != "PARENT_FRESH_VALIDATION":
        return word & ~3
    return word


def _independent_suffix_stream_id(stream: Any) -> str:
    if type(stream) is not materializer.DevelopmentRawObservationStreamV1:
        _fail("incremental suffix stream has a foreign type")
    digest = hashlib.sha256()
    counts = [0, 0, 0, 0]
    for index in range(stream.draw_count):
        word = _suffix_word(stream, index)
        digest.update(word.to_bytes(8, "big"))
        counts[word & 3] += 1
    raw_digest = digest.hexdigest()
    if (
        raw_digest != stream.raw_word_digest
        or tuple(counts) != stream.outcome_bucket_counts
        or stream.seed_id != stream.crn_pairing_group_seed_id
    ):
        _fail("incremental suffix raw words do not independently replay")
    return _hash(
        MATERIALIZER_DOMAINS["stream"],
        {
            "schema": "acfqp.v072_development_multirow_raw_stream.v1",
            "schema_version": "1.0.0",
            "law_key": stream.law_key.value,
            "arm": stream.arm,
            "logical_occurrence_id": stream.logical_occurrence_id,
            "transaction_id": stream.transaction_id,
            "build_epoch_id": stream.build_epoch_id,
            "context_id": stream.context_id,
            "round_index": stream.round_index,
            "physical_row_id": stream.physical_row_id,
            "parent_stream_id": stream.parent_stream_id,
            "lane": stream.lane.value,
            "draw_count": stream.draw_count,
            "seed_id": stream.seed_id,
            "crn_pairing_group_seed_id":
                stream.crn_pairing_group_seed_id,
            "raw_word_digest": raw_digest,
            "outcome_bucket_counts": counts,
            "target_endpoint_calls": 0,
            "hidden_law_queries": 0,
        },
    )


def _independent_suffix_commitment_id(
    stream: Any,
    stream_id: str,
    index: int,
) -> str:
    return _hash(
        MATERIALIZER_DOMAINS["raw_commitment"],
        {
            "schema": (
                "acfqp.v072_development_multirow_raw_commitment.v1"
            ),
            "schema_version": "1.0.0",
            "stream_id": stream_id,
            "accepted_draw_index": index,
            "word_u64_hex": f"{_suffix_word(stream, index):016x}",
            "accepted_exactly_once": True,
        },
    )


def _upstream_word(transcript: Any, lane: Any, index: int) -> int:
    seed_id = (
        transcript.discovery_seed_id
        if lane is materializer.UpstreamAcquisitionLaneV1.DISCOVERY
        else transcript.validation_seed_id
    )
    word = int.from_bytes(
        hashlib.sha256(
            b"acfqp:v072-development-multirow-upstream-word:v1\x00"
            + bytes.fromhex(seed_id)
            + b"\x00"
            + lane.value.encode("ascii")
            + b"\x00"
            + transcript.law_key.value.encode("ascii")
            + b"\x00"
            + index.to_bytes(8, "big")
        ).digest()[:8],
        "big",
    )
    if transcript.semantic_role == "PROMOTED_PARENT_ROOT_ROW":
        if lane is materializer.UpstreamAcquisitionLaneV1.DISCOVERY:
            return word & ~3
        return (word & ~3) | (index % 3)
    if (
        transcript.law_key.value == "HASH_BUCKET_LAW_B"
        and lane is materializer.UpstreamAcquisitionLaneV1.VALIDATION
    ):
        return word
    return (word & ~3) | (index & 1)


def _independent_upstream_stream_id(transcript: Any, lane: Any) -> str:
    if (
        type(transcript)
        is not materializer.DevelopmentUpstreamRowTranscriptV1
        or type(lane) is not materializer.UpstreamAcquisitionLaneV1
    ):
        _fail("prior-cold stream has a foreign type")
    seed_id = (
        transcript.discovery_seed_id
        if lane is materializer.UpstreamAcquisitionLaneV1.DISCOVERY
        else transcript.validation_seed_id
    )
    draws = (
        transcript.discovery_draws
        if lane is materializer.UpstreamAcquisitionLaneV1.DISCOVERY
        else transcript.validation_draws
    )
    expected_digest = (
        transcript.discovery_raw_digest
        if lane is materializer.UpstreamAcquisitionLaneV1.DISCOVERY
        else transcript.validation_raw_digest
    )
    digest = hashlib.sha256()
    counts = [0, 0, 0, 0]
    for index in range(draws):
        word = _upstream_word(transcript, lane, index)
        digest.update(word.to_bytes(8, "big"))
        counts[word & 3] += 1
    expected_counts = (
        transcript.discovery_bucket_counts
        if lane is materializer.UpstreamAcquisitionLaneV1.DISCOVERY
        else transcript.validation_bucket_counts
    )
    if (
        digest.hexdigest() != expected_digest
        or tuple(counts) != expected_counts
    ):
        _fail("prior-cold raw words do not independently replay")
    return _hash(
        MATERIALIZER_DOMAINS["stream"],
        {
            "schema": (
                "acfqp.v072_development_multirow_upstream_raw_stream.v1"
            ),
            "schema_version": "1.0.0",
            "law_key": transcript.law_key.value,
            "arm": transcript.arm,
            "context_id": transcript.physical_row.context_id,
            "physical_row_id": transcript.physical_row.physical_row_id,
            "semantic_role": transcript.semantic_role,
            "lane": lane.value,
            "draw_count": draws,
            "seed_id": seed_id,
            "crn_pairing_group_seed_id": seed_id,
            "raw_word_digest": expected_digest,
            "created_before_current_authorization": True,
            "incremental_suffix_counter": False,
        },
    )


def _independent_upstream_commitment_id(
    transcript: Any,
    lane: Any,
    stream_id: str,
    index: int,
) -> str:
    return _hash(
        MATERIALIZER_DOMAINS["raw_commitment"],
        {
            "schema": (
                "acfqp.v072_development_multirow_raw_commitment.v1"
            ),
            "schema_version": "1.0.0",
            "stream_id": stream_id,
            "accepted_draw_index": index,
            "word_u64_hex": (
                f"{_upstream_word(transcript, lane, index):016x}"
            ),
            "accepted_exactly_once": True,
        },
    )


def _verify_content_ids(
    occurrence: claimed_types.ReconciledOperationalOccurrenceV1,
) -> None:
    for draw_range in occurrence.draw_ranges:
        payload = draw_range.to_document()
        range_id = payload.pop("range_id")
        if range_id != _hash(DOMAINS["range"], payload):
            _fail("accepted-draw range content ID differs")
    work_payload = occurrence.work.to_document()
    work_id = work_payload.pop("work_id")
    if work_id != _hash(DOMAINS["work"], work_payload):
        _fail("operational work content ID differs")
    for access_order in (
        occurrence.access_order,
        *occurrence.additional_access_orders,
    ):
        access_payload = access_order.to_document()
        access_id = access_payload.pop("access_order_id")
        if access_id != _hash(DOMAINS["access"], access_payload):
            _fail("access-order content ID differs")
    occurrence_document = occurrence.to_document()
    occurrence_id = occurrence_document.pop("occurrence_record_id")
    occurrence_document.pop("draw_ranges")
    occurrence_document.pop("work")
    occurrence_document.pop("access_order")
    occurrence_document.pop("additional_access_orders")
    if occurrence_id != _hash(DOMAINS["occurrence"], occurrence_document):
        _fail("occurrence content ID differs")


def _resident_sources(
    occurrence: claimed_types.ReconciledOperationalOccurrenceV1,
) -> tuple[row_core.RowObservationTranscriptV2, ...]:
    source = occurrence._source_object
    if occurrence.source_kind is (
        claimed_types.ReconciliationSourceKindV1.ROW_CORE_RESIDENT
    ):
        if type(source) is not claimed_types.RowCoreObservationSeriesV1:
            _fail("row-core occurrence has a foreign source")
        values = (source.discovery_transcript, *source.validation_history)
    else:
        if type(source) is not matched.MatchedDirectGroundRunV1:
            _fail("matched-direct occurrence has a foreign source")
        matched_verifier.verify_matched_direct_ground_run_independently_v1(
            source
        )
        values = tuple(
            transcript
            for acquisition in (
                source.checkpoint_records[-1].evidence.acquisitions
            )
            for transcript in (
                acquisition.discovery_transcript,
                *acquisition.validation_history,
            )
        )
    if any(
        type(item) is not row_core.RowObservationTranscriptV2
        for item in values
    ):
        _fail("resident transcript source has a foreign type")
    return values


def _verify_resident_occurrence(
    occurrence: claimed_types.ReconciledOperationalOccurrenceV1,
) -> tuple[set[str], dict[str, int]]:
    source = occurrence._source_object
    transcripts = _resident_sources(occurrence)
    by_id = {item.transcript_id: item for item in transcripts}
    if len(by_id) != len(transcripts):
        _fail("resident source repeats one transcript artifact")
    seen: set[str] = set()
    stages: dict[str, int] = {}
    if (
        occurrence.source_kind
        is claimed_types.ReconciliationSourceKindV1.ROW_CORE_RESIDENT
    ):
        series_values = (source,)
        extension_stage = (
            claimed_types.DrawStageV1.ROW_CORE_VALIDATION_EXTENSION
        )
    else:
        series_values = tuple(
            claimed_types.RowCoreObservationSeriesV1(
                acquisition.discovery_transcript,
                acquisition.validation_history,
            )
            for acquisition in (
                source.checkpoint_records[-1].evidence.acquisitions
            )
        )
        extension_stage = (
            claimed_types.DrawStageV1.DIRECT_VALIDATION_EXTENSION
        )
    expected_keys: set[tuple[str, int, int, str]] = set()
    for series in series_values:
        expected_keys.add(
            (
                series.discovery_transcript.transcript_id,
                1,
                64,
                claimed_types.DrawStageV1.COLD_DISCOVERY.value,
            )
        )
        previous = 0
        for ordinal, transcript in enumerate(series.validation_history):
            expected_keys.add(
                (
                    transcript.transcript_id,
                    previous + 1,
                    transcript.selected_checkpoint_draw_count,
                    (
                        claimed_types.DrawStageV1.COLD_VALIDATION
                        if ordinal == 0
                        else extension_stage
                    ).value,
                )
            )
            previous = transcript.selected_checkpoint_draw_count
    actual_keys = {
        (
            item.source_artifact_id,
            item.first_accepted_draw_index,
            item.last_accepted_draw_index,
            item.stage.value,
        )
        for item in occurrence.draw_ranges
    }
    if actual_keys != expected_keys:
        _fail("resident range inventory omits or invents a transcript prefix")
    for draw_range in occurrence.draw_ranges:
        transcript = by_id.get(draw_range.source_artifact_id)
        if (
            transcript is None
            or draw_range.commitment_scheme
            is not (
                claimed_types.CommitmentSchemeV1
                .RESIDENT_ARM_BOUND_SOURCE_COMMITMENT
            )
            or draw_range.stream_id
            != transcript.stream_identity.source_stream_id
            or draw_range.arm != transcript.stream_identity.arm
            or draw_range.context_id != transcript.stream_identity.context_id
        ):
            _fail("resident range is not bound to its exact transcript")
        start = draw_range.first_accepted_draw_index
        stop = draw_range.last_accepted_draw_index
        observations = transcript.observations[start - 1 : stop]
        commitments = tuple(
            item.source_commitment_id for item in observations
        )
        first, last, digest, count = _ordered_digest(commitments)
        expected_crn = _crn_group(
            transcript.stream_identity.seed_identity_id,
            start,
            stop,
        )
        if (
            start <= 0
            or count != draw_range.draw_count
            or first != draw_range.first_commitment_id
            or last != draw_range.last_commitment_id
            or digest != draw_range.ordered_commitment_digest
            or expected_crn != draw_range.crn_pairing_group_id
            or seen.intersection(commitments)
        ):
            _fail("resident commitments or CRN identity do not replay")
        seen.update(commitments)
        stages[draw_range.stage.value] = (
            stages.get(draw_range.stage.value, 0) + count
        )
    if (
        occurrence.source_kind
        is claimed_types.ReconciliationSourceKindV1.ROW_CORE_RESIDENT
    ):
        series_payload = {
            "schema": "acfqp.v072_reconciliation_row_core_series.v1",
            "schema_version": claimed_types.SCHEMA_VERSION,
            "context_id": source.context_id,
            "arm": source.arm,
            "physical_row_id": source.physical_row_id,
            "discovery_transcript_id": (
                source.discovery_transcript.transcript_id
            ),
            "validation_transcript_ids": [
                item.transcript_id for item in source.validation_history
            ],
            "observation_only": True,
            "registered_target_evidence": False,
        }
        if (
            type(source) is not claimed_types.RowCoreObservationSeriesV1
            or source.series_id
            != _hash(DOMAINS["row_series"], series_payload)
            or occurrence.source_artifact_id != source.series_id
            or occurrence.logical_occurrence_id
            != source.logical_occurrence_id
            or occurrence.terminal_class
            is not (
                claimed_types.ReconciliationTerminalClassV1
                .ATTEMPT_CLOSURE_NONCERTIFICATE
            )
            or occurrence.terminal_code
            is not (
                claimed_types.ReconciliationTerminalCodeV1
                .OBSERVATION_ONLY_NONCERTIFICATE
            )
        ):
            _fail("row-core source identity or terminal differs")
    else:
        if occurrence.source_artifact_id != source.run_id:
            _fail("matched-direct source identity differs")
        expected_terminal = (
            claimed_types.ReconciliationTerminalClassV1.PLAN_CERTIFICATE
            if source.certified
            else (
                claimed_types.ReconciliationTerminalClassV1
                .ATTEMPT_CLOSURE_NONCERTIFICATE
            )
        )
        if occurrence.terminal_class is not expected_terminal:
            _fail("matched-direct terminal class differs")
    return seen, stages


def _incremental_commitments(
    occurrence: claimed_types.ReconciledOperationalOccurrenceV1,
) -> tuple[set[str], dict[str, int]]:
    run = occurrence._source_object
    if type(run) is materializer.DevelopmentAcquisitionControlRunV1:
        handoffs = (run.handoff,)
        complete_source = False
    elif type(run) is complete.DevelopmentCompleteAdaptivePlanningRunV1:
        complete_verifier.verify_development_complete_adaptive_run_v1(run)
        handoffs = run.handoffs
        complete_source = True
    else:
        _fail("incremental occurrence has a foreign source")
    first_handoff = handoffs[0]
    suffix_values = tuple(
        stream
        for handoff in handoffs
        for stream in (
            handoff.parent_validation_stream,
        *(
            stream
            for child in handoff.child_rows
            for stream in (
                child.discovery_stream,
                child.validation_stream,
            )
        ),
        )
    )
    suffix_streams = {
        _independent_suffix_stream_id(stream): stream
        for stream in suffix_values
    }
    upstream_streams = {
        _independent_upstream_stream_id(transcript, lane): (
            transcript,
            lane,
        )
        for transcript in (
            first_handoff.request.parent_evidence.upstream_root_rows
        )
        for lane in (
            materializer.UpstreamAcquisitionLaneV1.DISCOVERY,
            materializer.UpstreamAcquisitionLaneV1.VALIDATION,
        )
    }
    if {
        item.stream_id for item in occurrence.draw_ranges
    } != {*suffix_streams, *upstream_streams}:
        _fail("compressed range inventory omits or invents one raw stream")
    proof_by_stream = {
        item.stream_id: item
        for handoff in handoffs
        for item in handoff.raw_commitment_ranges
    }
    seen: set[str] = set()
    stages: dict[str, int] = {}
    for draw_range in occurrence.draw_ranges:
        stream = suffix_streams.get(draw_range.stream_id)
        upstream = upstream_streams.get(draw_range.stream_id)
        if (stream is None) == (upstream is None):
            _fail("compressed range has zero or multiple source streams")
        if stream is not None:
            if stream.arm != occurrence.arm:
                _fail("incremental suffix stream is transplanted across arms")
            commitments = tuple(
                _independent_suffix_commitment_id(
                    stream,
                    draw_range.stream_id,
                    index,
                )
                for index in range(stream.draw_count)
            )
            seed_id = stream.crn_pairing_group_seed_id
            expected_stage = {
                materializer.AcquisitionLaneV1.PARENT_FRESH_VALIDATION: (
                    claimed_types.DrawStageV1
                    .INCREMENTAL_PARENT_VALIDATION
                ),
                materializer.AcquisitionLaneV1.CHILD_FRESH_DISCOVERY: (
                    claimed_types.DrawStageV1
                    .INCREMENTAL_CHILD_DISCOVERY
                ),
                materializer.AcquisitionLaneV1.CHILD_FRESH_VALIDATION: (
                    claimed_types.DrawStageV1
                    .INCREMENTAL_CHILD_VALIDATION
                ),
            }[stream.lane]
            expected_round = stream.round_index
            expected_physical_row = stream.physical_row_id
        else:
            transcript, lane = upstream  # type: ignore[misc]
            if transcript.arm != occurrence.arm:
                _fail("prior-cold stream is transplanted across arms")
            commitments = tuple(
                _independent_upstream_commitment_id(
                    transcript,
                    lane,
                    draw_range.stream_id,
                    index,
                )
                for index in range(draw_range.draw_count)
            )
            seed_id = (
                transcript.discovery_seed_id
                if lane
                is materializer.UpstreamAcquisitionLaneV1.DISCOVERY
                else transcript.validation_seed_id
            )
            expected_stage = (
                claimed_types.DrawStageV1.COLD_DISCOVERY
                if lane
                is materializer.UpstreamAcquisitionLaneV1.DISCOVERY
                else claimed_types.DrawStageV1.COLD_VALIDATION
            )
            expected_round = 0
            expected_physical_row = (
                transcript.physical_row.physical_row_id
            )
        first, last, digest, count = _ordered_digest(commitments)
        expected_proof_id = _hash(
            MATERIALIZER_DOMAINS["raw_range"],
            {
                "schema": (
                    "acfqp.v072_development_multirow_"
                    "raw_commitment_range.v1"
                ),
                "schema_version": "1.0.0",
                "stream_id": draw_range.stream_id,
                "accepted_draw_index_range": {
                    "first": 0,
                    "last": count - 1,
                },
                "draw_count": count,
                "first_commitment_id": first,
                "last_commitment_id": last,
                "ordered_commitment_digest": digest,
                "unique_commitment_count": count,
                "complete_contiguous_range": True,
            },
        )
        proof = (
            proof_by_stream.get(draw_range.stream_id)
            if stream is not None
            else None
        )
        if (
            (stream is not None and proof is None)
            or draw_range.commitment_scheme
            is not claimed_types.CommitmentSchemeV1.COMPRESSED_STREAM_INDEX_WORD
            or (
                proof is not None
                and (
                    proof.range_proof_id != expected_proof_id
                    or proof.draw_count != count
                    or proof.first_commitment_id != first
                    or proof.last_commitment_id != last
                    or proof.ordered_commitment_digest != digest
                )
            )
            or draw_range.source_range_proof_id != expected_proof_id
            or draw_range.source_artifact_id != expected_proof_id
            or draw_range.round_index != expected_round
            or draw_range.stage is not expected_stage
            or draw_range.physical_row_id != expected_physical_row
            or draw_range.first_accepted_draw_index != 0
            or draw_range.last_accepted_draw_index != count - 1
            or draw_range.draw_count != count
            or draw_range.first_commitment_id != first
            or draw_range.last_commitment_id != last
            or draw_range.ordered_commitment_digest != digest
            or draw_range.crn_pairing_group_id
            != _crn_group(seed_id, 0, count - 1)
            or seen.intersection(commitments)
        ):
            _fail("compressed commitments or CRN identity do not replay")
        seen.update(commitments)
        stages[draw_range.stage.value] = (
            stages.get(draw_range.stage.value, 0) + count
        )
    if (
        occurrence.logical_occurrence_id
        != first_handoff.request.parent_epoch.logical_occurrence_id
        or occurrence.arm != first_handoff.request.parent_epoch.arm
    ):
        _fail("incremental source identity or derived terminal differs")
    if complete_source:
        expected_code = {
            (
                complete.DevelopmentCompleteAdaptiveTerminalCodeV1
                .PLAN_CERTIFIED_AFTER_FIRST_INCREMENTAL_REBUILD
            ): (
                claimed_types.ReconciliationTerminalCodeV1
                .PLAN_CERTIFIED_AFTER_FIRST_INCREMENTAL_REBUILD
            ),
            (
                complete.DevelopmentCompleteAdaptiveTerminalCodeV1
                .PLAN_CERTIFIED_AFTER_SECOND_INCREMENTAL_REBUILD
            ): (
                claimed_types.ReconciliationTerminalCodeV1
                .PLAN_CERTIFIED_AFTER_SECOND_INCREMENTAL_REBUILD
            ),
        }.get(run.terminal_code)
        if (
            occurrence.source_artifact_id != run.run_id
            or occurrence.context_id != run.context_id
            or occurrence.terminal_class
            is not (
                claimed_types.ReconciliationTerminalClassV1
                .PLAN_CERTIFICATE
            )
            or expected_code is None
            or occurrence.terminal_code is not expected_code
        ):
            _fail("complete adaptive terminal or source identity differs")
    elif (
        occurrence.source_artifact_id != run.run_id
        or occurrence.terminal_class
        is not (
            claimed_types.ReconciliationTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE
        )
        or occurrence.terminal_code
        is not (
            claimed_types.ReconciliationTerminalCodeV1
            .INCREMENTAL_PENDING_MODEL_REBUILD_NONCERTIFICATE
        )
    ):
        _fail("pending incremental terminal or source identity differs")
    return seen, stages


def _verify_work(
    occurrence: claimed_types.ReconciledOperationalOccurrenceV1,
    commitment_count: int,
    stages: Mapping[str, int],
) -> None:
    work = occurrence.work
    stage_to_leaf = {
        claimed_types.DrawStageV1.COLD_DISCOVERY.value:
            work.cold_discovery_draws,
        claimed_types.DrawStageV1.COLD_VALIDATION.value:
            work.cold_validation_draws,
        claimed_types.DrawStageV1.ROW_CORE_VALIDATION_EXTENSION.value:
            work.row_core_validation_extension_draws,
        claimed_types.DrawStageV1.DIRECT_VALIDATION_EXTENSION.value:
            work.direct_extension_draws,
        claimed_types.DrawStageV1.INCREMENTAL_PARENT_VALIDATION.value:
            work.incremental_parent_validation_draws,
        claimed_types.DrawStageV1.INCREMENTAL_CHILD_DISCOVERY.value:
            work.incremental_child_discovery_draws,
        claimed_types.DrawStageV1.INCREMENTAL_CHILD_VALIDATION.value:
            work.incremental_child_validation_draws,
    }
    if (
        work.accepted_draws != commitment_count
        or work.random_word_calls != commitment_count
        or work.resident_commitment_count
        + work.compressed_commitment_count
        != commitment_count
        or any(
            stage_to_leaf[stage.value] != stages.get(stage.value, 0)
            for stage in claimed_types.DrawStageV1
        )
        or work.failed_certificate_attempts
        != (
            work.failed_direct_checkpoint_attempts
            + work.failed_parent_certificate_attempts
            + work.failed_incremental_postbuild_audits
        )
        or work.terminal_artifact_count != 1
        or work.crn_cost_discount_draws != 0
        or work.caller_supplied_counts is not False
    ):
        _fail("native work differs from independently replayed ranges")
    source = occurrence._source_object
    if occurrence.source_kind is (
        claimed_types.ReconciliationSourceKindV1.ROW_CORE_RESIDENT
    ):
        if any(
            (
                work.direct_checkpoint_attempts,
                work.failed_direct_checkpoint_attempts,
                work.failed_parent_certificate_attempts,
                work.failed_incremental_postbuild_audits,
                work.failed_certificate_attempts,
                work.direct_model_builds,
                work.direct_model_independent_verifications,
                work.direct_solver_calls,
                work.direct_proof_verifications,
                work.incremental_materializer_calls,
                work.incremental_observer_calls,
                work.incremental_postbuild_model_builds,
                (
                    work
                    .incremental_postbuild_model_independent_verifications
                ),
                work.incremental_postbuild_solver_calls,
                work.incremental_postbuild_proof_verifications,
                work.incremental_postbuild_audits,
                work.preauthorization_public_metadata_reads,
                work.preauthorization_counterfactual_evaluations,
                work.preauthorization_source_consensus_lookups,
                work.native_zero_counter_count,
            )
        ):
            _fail("row-only source contains invented planning/access work")
    elif occurrence.source_kind is (
        claimed_types.ReconciliationSourceKindV1.MATCHED_DIRECT_RUN
    ):
        attempts = len(source.checkpoint_records)
        failed = sum(
            item.status
            is matched.MatchedDirectCheckpointStatusV1.NOT_CERTIFIED
            for item in source.checkpoint_records
        )
        if (
            work.direct_checkpoint_attempts,
            work.failed_direct_checkpoint_attempts,
            work.direct_model_builds,
            work.direct_model_independent_verifications,
            work.direct_solver_calls,
            work.direct_proof_verifications,
        ) != (attempts, failed, attempts, attempts, attempts, attempts):
            _fail("matched-direct failed/build/solve/proof work differs")
        if any(
            (
                work.failed_parent_certificate_attempts,
                work.failed_incremental_postbuild_audits,
                work.incremental_materializer_calls,
                work.incremental_observer_calls,
                work.incremental_postbuild_model_builds,
                (
                    work
                    .incremental_postbuild_model_independent_verifications
                ),
                work.incremental_postbuild_solver_calls,
                work.incremental_postbuild_proof_verifications,
                work.incremental_postbuild_audits,
                work.preauthorization_public_metadata_reads,
                work.preauthorization_counterfactual_evaluations,
                work.preauthorization_source_consensus_lookups,
                work.native_zero_counter_count,
            )
        ):
            _fail("matched-direct source contains incremental/access work")
    elif occurrence.source_kind is (
        claimed_types.ReconciliationSourceKindV1.INCREMENTAL_COMPRESSED
    ):
        counters = source.handoff.counters
        access = source.handoff.request.preauthorization_access
        if (
            work.failed_parent_certificate_attempts != 1
            or work.failed_incremental_postbuild_audits != 0
            or work.incremental_postbuild_model_builds != 0
            or (
                work.incremental_postbuild_model_independent_verifications
                != 0
            )
            or work.incremental_postbuild_solver_calls != 0
            or work.incremental_postbuild_proof_verifications != 0
            or work.incremental_postbuild_audits != 0
            or work.incremental_materializer_calls
            != counters.materializer_calls
            or work.incremental_observer_calls != counters.observer_calls
            or work.preauthorization_public_metadata_reads
            != access.public_catalogue_metadata_reads
            or work.preauthorization_counterfactual_evaluations
            != access.exact_counterfactual_evaluations
            or work.preauthorization_source_consensus_lookups
            != access.source_consensus_lookups
            or work.native_zero_counter_count
            != len(access.native_zero_counters)
            or any(
                (
                    work.direct_checkpoint_attempts,
                    work.failed_direct_checkpoint_attempts,
                    work.direct_model_builds,
                    work.direct_model_independent_verifications,
                    work.direct_solver_calls,
                    work.direct_proof_verifications,
                )
            )
        ):
            _fail("incremental failure/access/execution work differs")
    elif occurrence.source_kind is (
        claimed_types.ReconciliationSourceKindV1
        .COMPLETE_ADAPTIVE_PLANNING_COMPRESSED
    ):
        if type(source) is not (
            complete.DevelopmentCompleteAdaptivePlanningRunV1
        ):
            _fail("complete adaptive work has a foreign source")
        counters = tuple(item.counters for item in source.handoffs)
        accesses = tuple(
            item.request.preauthorization_access
            for item in source.handoffs
        )
        postbuild_count = len(source.postbuild_results)
        failed_postbuilds = sum(
            not item.certified for item in source.postbuild_results
        )
        if (
            work.accepted_draws != source.total_accepted_draws
            or work.failed_parent_certificate_attempts != 1
            or work.failed_incremental_postbuild_audits
            != failed_postbuilds
            or work.incremental_materializer_calls
            != sum(item.materializer_calls for item in counters)
            or work.incremental_observer_calls
            != sum(item.observer_calls for item in counters)
            or (
                work.incremental_postbuild_model_builds,
                (
                    work
                    .incremental_postbuild_model_independent_verifications
                ),
                work.incremental_postbuild_solver_calls,
                work.incremental_postbuild_proof_verifications,
                work.incremental_postbuild_audits,
            )
            != (postbuild_count,) * 5
            or work.preauthorization_public_metadata_reads
            != sum(
                item.public_catalogue_metadata_reads for item in accesses
            )
            or work.preauthorization_counterfactual_evaluations
            != sum(
                item.exact_counterfactual_evaluations for item in accesses
            )
            or work.preauthorization_source_consensus_lookups
            != sum(item.source_consensus_lookups for item in accesses)
            or work.native_zero_counter_count
            != sum(len(item.native_zero_counters) for item in accesses)
            or any(
                (
                    work.direct_checkpoint_attempts,
                    work.failed_direct_checkpoint_attempts,
                    work.direct_model_builds,
                    work.direct_model_independent_verifications,
                    work.direct_solver_calls,
                    work.direct_proof_verifications,
                )
            )
        ):
            _fail("complete adaptive failed/build/solve/access work differs")
    else:  # pragma: no cover
        _fail("unknown reconciliation source kind")


def _verify_access(
    occurrence: claimed_types.ReconciledOperationalOccurrenceV1,
) -> None:
    compressed_kinds = (
        claimed_types.ReconciliationSourceKindV1.INCREMENTAL_COMPRESSED,
        (
            claimed_types.ReconciliationSourceKindV1
            .COMPLETE_ADAPTIVE_PLANNING_COMPRESSED
        ),
    )
    if occurrence.source_kind not in compressed_kinds:
        access = occurrence.access_order
        if (
            access.kind is not claimed_types.AccessOrderKindV1.NOT_APPLICABLE
            or access.source_artifact_id != occurrence.source_artifact_id
            or access.authorization_frozen_before_execution
            or access.native_zero_counter_ids
            or access.native_zero_paths
            or access.native_zero_values
            or occurrence.additional_access_orders
        ):
            _fail("nonincremental access order contains invented work")
        return
    source = occurrence._source_object
    handoffs = (
        (source.handoff,)
        if occurrence.source_kind
        is claimed_types.ReconciliationSourceKindV1.INCREMENTAL_COMPRESSED
        else source.handoffs
    )
    claimed_accesses = (
        occurrence.access_order,
        *occurrence.additional_access_orders,
    )
    if len(claimed_accesses) != len(handoffs):
        _fail("incremental access-order count differs from physical rounds")
    for access, handoff in zip(
        claimed_accesses,
        handoffs,
        strict=True,
    ):
        request = handoff.request
        source_access = request.preauthorization_access
        authorization = request.authorization
        if (
            access.kind
            is not claimed_types.AccessOrderKindV1.PREAUTHORIZED_INCREMENTAL
            or access.source_artifact_id != occurrence.source_artifact_id
            or access.access_log_id != source_access.access_log_id
            or access.authorization_id != authorization.authorization_id
            or access.authorization_freeze_id
            != request.authorization_freeze_id
            or access.round_index != request.parent_epoch.round_index
            or access.authorization_sequence
            != authorization.authorization_sequence
            or access.first_execution_sequence
            != authorization.target_access_sequence_minimum
            or access.native_zero_counter_ids
            != tuple(
                item.counter_id for item in source_access.native_zero_counters
            )
            or access.native_zero_paths
            != tuple(
                item.path for item in source_access.native_zero_counters
            )
            or access.native_zero_values
            != tuple(
                item.value for item in source_access.native_zero_counters
            )
            or not access.authorization_frozen_before_execution
        ):
            _fail("incremental preauthorization order/native zero differs")


@dataclass(frozen=True, slots=True)
class IndependentCampaignReconciliationAttestationV1:
    ledger_id: str
    logical_occurrence_denominator: int
    plan_certificate_count: int
    noncertificate_count: int
    accepted_draw_commitment_count: int
    random_word_call_count: int
    crn_pairing_group_count: int
    crn_cost_discount_draws: int
    verification_profile: str = PROFILE_KEY

    @property
    def attestation_id(self) -> str:
        return _hash(
            VERIFICATION_DOMAIN,
            {
                "schema": (
                    "acfqp.v072_campaign_reconciliation_"
                    "independent_attestation.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "verification_profile": self.verification_profile,
                "ledger_id": self.ledger_id,
                "logical_occurrence_denominator": (
                    self.logical_occurrence_denominator
                ),
                "plan_certificate_count": self.plan_certificate_count,
                "noncertificate_count": self.noncertificate_count,
                "accepted_draw_commitment_count": (
                    self.accepted_draw_commitment_count
                ),
                "random_word_call_count": self.random_word_call_count,
                "crn_pairing_group_count": self.crn_pairing_group_count,
                "crn_cost_discount_draws": self.crn_cost_discount_draws,
                "verification_result": "PASS",
            },
        )


def _verify_campaign_impl(
    claimed: claimed_types.CampaignReconciliationLedgerV1,
) -> IndependentCampaignReconciliationAttestationV1:
    if type(claimed) is not claimed_types.CampaignReconciliationLedgerV1:
        _fail("campaign ledger has a foreign concrete type")
    binding = claimed.development_context_binding
    if binding is not None:
        if type(binding) is not (
            claimed_types.DevelopmentSharedExperimentalContextBindingV1
        ):
            _fail("development context binding has a foreign type")
        base = {
            "schema": (
                "acfqp.v072_reconciliation_development_context_binding.v1"
            ),
            "schema_version": claimed_types.SCHEMA_VERSION,
            "mechanics_context_key": (
                "V072_DEVELOPMENT_P4_FIVE_ARM_MECHANICS_V1"
            ),
            "arm_native_context_bindings": [
                {"arm": arm, "native_context_id": context_id}
                for arm, context_id in binding.arm_native_context_bindings
            ],
            "scientific_matched_pair": False,
            "matched_endpoint_authority": False,
            "registered_target_evidence": False,
        }
        mechanics_context_id = _hash(
            DOMAINS["context_binding"],
            {**base, "identity_role": "MECHANICS_CONTEXT"},
        )
        binding_id = _hash(
            DOMAINS["context_binding"],
            {
                **base,
                "mechanics_context_id": mechanics_context_id,
                "identity_role": "NATIVE_CONTEXT_BINDING",
            },
        )
        if (
            binding.mechanics_context_key
            != "V072_DEVELOPMENT_P4_FIVE_ARM_MECHANICS_V1"
            or tuple(arm for arm, _ in binding.arm_native_context_bindings)
            != prereg.ARM_ORDER
            or binding.mechanics_context_id != mechanics_context_id
            or binding.binding_id != binding_id
            or binding.scientific_matched_pair
            or binding.matched_endpoint_authority
            or binding.registered_target_evidence
        ):
            _fail("development mechanics-only context binding differs")
    occurrence_ids = tuple(
        item.occurrence_record_id for item in claimed.occurrences
    )
    if (
        len(
            {
                (item.logical_occurrence_id, item.arm)
                for item in claimed.occurrences
            }
        )
        != len(claimed.occurrences)
    ):
        _fail("campaign occurrence inventory is noncanonical")
    if claimed.order_profile is (
        claimed_types.CampaignOrderProfileV1.DEVELOPMENT_CONTENT_ID
    ):
        if (
            occurrence_ids != tuple(sorted(set(occurrence_ids)))
            or binding is not None
        ):
            _fail("development content-ID campaign order differs")
    elif claimed.order_profile is (
        claimed_types.CampaignOrderProfileV1
        .CONTEXT_MAJOR_FROZEN_ARM_ORDER
    ):
        registered_contexts = tuple(
            item.context_id
            for item in prereg.registered_heldout_public_contexts_v2()
        )
        native_binding = (
            {}
            if binding is None
            else dict(binding.arm_native_context_bindings)
        )
        if binding is not None and any(
            native_binding.get(item.arm) != item.context_id
            for item in claimed.occurrences
        ):
            _fail("mechanics binding differs from native occurrence context")
        effective_contexts = tuple(
            (
                item.context_id
                if binding is None
                else binding.mechanics_context_id
            )
            for item in claimed.occurrences
        )
        present_contexts = {
            *effective_contexts
        }
        unknown_contexts = tuple(
            sorted(present_contexts - set(registered_contexts))
        )
        context_order = {
            value: index
            for index, value in enumerate(
                (*registered_contexts, *unknown_contexts)
            )
        }
        arm_order = {
            value: index for index, value in enumerate(prereg.ARM_ORDER)
        }
        pairs = tuple(
            (effective_context, item.arm)
            for effective_context, item in zip(
                effective_contexts, claimed.occurrences
            )
        )
        if (
            any(arm not in arm_order for _, arm in pairs)
            or pairs
            != tuple(
                sorted(
                    pairs,
                    key=lambda item: (
                        context_order[item[0]],
                        arm_order[item[1]],
                    ),
                )
            )
            or any(
                {
                    arm
                    for context_id, arm in pairs
                    if context_id == current_context
                }
                != set(prereg.ARM_ORDER)
                for current_context in present_contexts
            )
        ):
            _fail("context-major frozen five-arm order differs")
        registered_pairs = tuple(
            pair for pair in pairs if pair[0] in set(registered_contexts)
        )
        if registered_pairs and (
            len(registered_pairs) != prereg.CONFIRMATORY_OCCURRENCE_COUNT
            or {context_id for context_id, _ in registered_pairs}
            != set(registered_contexts)
        ):
            _fail("registered campaign is not exact 15-occurrence shape")
    else:
        _fail("campaign order profile is unknown")
    global_commitments: set[str] = set()
    crn_groups: dict[str, list[tuple[str, int, set[str]]]] = {}
    for occurrence in claimed.occurrences:
        if type(occurrence) is not (
            claimed_types.ReconciledOperationalOccurrenceV1
        ):
            _fail("campaign contains a foreign occurrence type")
        _verify_content_ids(occurrence)
        if occurrence.source_kind in (
            claimed_types.ReconciliationSourceKindV1
            .INCREMENTAL_COMPRESSED,
            (
                claimed_types.ReconciliationSourceKindV1
                .COMPLETE_ADAPTIVE_PLANNING_COMPRESSED
            ),
        ):
            commitments, stages = _incremental_commitments(occurrence)
        else:
            commitments, stages = _verify_resident_occurrence(occurrence)
        if global_commitments.intersection(commitments):
            _fail("one accepted draw commitment is reused across occurrences")
        global_commitments.update(commitments)
        _verify_work(occurrence, len(commitments), stages)
        _verify_access(occurrence)
        if (
            not occurrence.denominator_included
            or not occurrence.terminal_derived_from_source
            or occurrence.caller_supplied_terminal_outcome
            or occurrence.crn_cost_discount_draws != 0
        ):
            _fail("terminal/denominator/discount claim is not authoritative")
        for draw_range in occurrence.draw_ranges:
            range_commitments = {
                value
                for value in commitments
                if value
                in {
                    draw_range.first_commitment_id,
                    draw_range.last_commitment_id,
                }
            }
            # Full group disjointness is already established by global
            # commitment replay.  This record retains arm/count invariants.
            crn_groups.setdefault(
                draw_range.crn_pairing_group_id, []
            ).append(
                (
                    occurrence.arm,
                    draw_range.draw_count,
                    range_commitments,
                )
            )
    for members in crn_groups.values():
        if (
            len({arm for arm, _, _ in members}) != len(members)
            or len({count for _, count, _ in members}) != 1
        ):
            _fail("CRN group repeats an arm or has unequal draw counts")
    denominator = len(claimed.occurrences)
    plan = sum(
        item.terminal_class
        is claimed_types.ReconciliationTerminalClassV1.PLAN_CERTIFICATE
        for item in claimed.occurrences
    )
    noncertificate = denominator - plan
    total_draws = sum(
        item.work.accepted_draws for item in claimed.occurrences
    )
    if (
        claimed.logical_occurrence_denominator != denominator
        or claimed.plan_certificate_count != plan
        or claimed.noncertificate_count != noncertificate
        or claimed.total_accepted_draws != total_draws
        or claimed.total_random_word_calls != total_draws
        or len(global_commitments) != total_draws
        or claimed.total_resident_commitments
        + claimed.total_compressed_commitments
        != total_draws
        or claimed.total_terminal_artifacts != denominator
        or claimed.crn_pairing_group_count != len(crn_groups)
        or claimed.crn_cost_discount_draws != 0
        or claimed.registered_target_evidence_count != 0
    ):
        _fail("campaign totals, denominator, or terminal counts differ")
    ledger_document = claimed.to_document()
    ledger_id = ledger_document.pop("ledger_id")
    ledger_document.pop("occurrences")
    ledger_document.pop("development_context_binding")
    if ledger_id != _hash(DOMAINS["campaign"], ledger_document):
        _fail("campaign ledger content ID differs")
    return IndependentCampaignReconciliationAttestationV1(
        ledger_id,
        denominator,
        plan,
        noncertificate,
        total_draws,
        total_draws,
        len(crn_groups),
        0,
    )


def verify_campaign_reconciliation_independently_v1(
    claimed: claimed_types.CampaignReconciliationLedgerV1,
) -> IndependentCampaignReconciliationAttestationV1:
    """Normalize every nested replay rejection into this verifier domain."""

    try:
        return _verify_campaign_impl(claimed)
    except IndependentCampaignReconciliationVerificationFailure:
        raise
    except (ValueError, TypeError, KeyError, AssertionError) as error:
        raise IndependentCampaignReconciliationVerificationFailure(
            f"nested campaign reconciliation replay failed: {error}"
        ) from error


__all__ = [
    "IndependentCampaignReconciliationAttestationV1",
    "IndependentCampaignReconciliationVerificationFailure",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "verify_campaign_reconciliation_independently_v1",
]
