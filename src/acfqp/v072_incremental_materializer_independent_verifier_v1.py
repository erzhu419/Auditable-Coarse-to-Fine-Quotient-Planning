"""Independent verifier for V0-072 acquisition/rebuild handoffs.

No materializer execution, stream-construction, cardinality-construction, or
model-rebuild helper is called.  The verifier replays public development
semantics, raw random words, content IDs, row unions, native counters, and
noncertificate status from literals.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from .phase3e_ids import canonical_json_bytes, parse_content_id
from . import target_preauthorization_selector_v2 as selector
from . import transfer_guided_acquisition_preregistration_v1 as prereg
from . import v072_incremental_materializer_v1 as materializer_types


SCHEMA_VERSION = "1.0.0"
VERIFICATION_PROFILE = (
    "v072_incremental_materializer_independent_verifier_v1"
)

PARENT_DRAWS = 2_048
DISCOVERY_DRAWS = 64
VALIDATION_DRAWS = 8_192
CHILD_DRAWS = 8_256
MAX_ROWS = 19
MAX_DRAWS = 160_960
PENDING = "PENDING_MODEL_REBUILD_NONCERTIFICATE"

DOMAINS = {
    "context": "acfqp:v072-development-multirow-public-context:v1",
    "state": "acfqp:v072-development-multirow-public-state:v1",
    "row": "acfqp:v072-development-multirow-public-row:v1",
    "descriptor": "acfqp:v072-development-multirow-novel-descriptor:v1",
    "parent": "acfqp:v072-development-multirow-parent-evidence:v1",
    "upstream_row": (
        "acfqp:v072-development-multirow-upstream-row-transcript:v1"
    ),
    "upstream_observation": (
        "acfqp:v072-development-multirow-upstream-novel-observation:v1"
    ),
    "parent_model": (
        "acfqp:v072-development-multirow-parent-model-snapshot:v1"
    ),
    "closure": "acfqp:v072-development-multirow-current-closure:v1",
    "cardinality": (
        "acfqp:v072-development-multirow-cardinality-evidence:v1"
    ),
    "cardinality_authority": (
        "acfqp:v072-development-multirow-cardinality-authority:v1"
    ),
    "freeze": "acfqp:v072-incremental-authorization-freeze:v1",
    "request": "acfqp:v072-incremental-materialization-request:v1",
    "transaction": "acfqp:v072-incremental-transaction:v1",
    "epoch": "acfqp:v072-incremental-build-epoch:v1",
    "stream": "acfqp:v072-development-multirow-raw-stream:v1",
    "raw_commitment": (
        "acfqp:v072-development-multirow-raw-commitment:v1"
    ),
    "raw_range": (
        "acfqp:v072-development-multirow-raw-commitment-range:v1"
    ),
    "row_evidence": (
        "acfqp:v072-development-multirow-materialized-row-evidence:v1"
    ),
    "counters": "acfqp:v072-incremental-native-counters:v1",
    "physical_set": (
        "acfqp:v072-development-multirow-physical-row-set:v1"
    ),
    "handoff": "acfqp:v072-incremental-model-rebuild-handoff:v1",
    "run": "acfqp:v072-development-multirow-acquisition-run:v1",
    "attestation": (
        "acfqp:v072-incremental-materializer-independent-attestation:v1"
    ),
}


class IndependentIncrementalMaterializerVerificationFailure(ValueError):
    """The claimed handoff differs from independent replay."""


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAINS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise IndependentIncrementalMaterializerVerificationFailure(
            f"independent content replay failed: {error}"
        ) from error


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise IndependentIncrementalMaterializerVerificationFailure(
            f"{field} is not a content ID"
        ) from error


def _context_id() -> str:
    payload = {
        "schema": "acfqp.v072_development_multirow_public_context.v1",
        "schema_version": "1.0.0",
        "context_key": "development_multirow_path4_v1",
        "vertex_count": 4,
        "edges": [[0, 1], [1, 2], [2, 3]],
        "rank_cap": 4,
        "horizon": 2,
        "registered_target_context": False,
    }
    result = _hash("context", payload)
    if result in {
        item.context_id
        for item in prereg.registered_heldout_public_contexts_v2()
    }:
        raise IndependentIncrementalMaterializerVerificationFailure(
            "development context aliases a registered held-out context"
        )
    return result


def _state_id(state: Any) -> str:
    if (
        type(state) is not materializer_types.DevelopmentPublicStateV1
        or state.context_id != _context_id()
        or len(state.ranks) != 4
        or any(
            type(rank) is not int or not 0 <= rank <= 4
            for rank in state.ranks
        )
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "development state differs from public schema"
        )
    return _hash(
        "state",
        {
            "schema": "acfqp.v072_development_multirow_public_state.v1",
            "context_id": state.context_id,
            "ranks": list(state.ranks),
        },
    )


def _legal_actions(state: Any) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        sorted(
            {
                (left, right, survivor)
        for left, right in ((0, 1), (1, 2), (2, 3))
                if state.ranks[left] > 0
                and state.ranks[left] == state.ranks[right]
                for survivor in (left, right)
            }
        )
    )


def _row_id(row: Any) -> str:
    if (
        type(row) is not materializer_types.DevelopmentPhysicalRowV1
        or row.action not in _legal_actions(row.state)
        or row.remaining_horizon not in (1, 2)
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "development physical row is not publicly legal"
        )
    state_id = _state_id(row.state)
    return _hash(
        "row",
        {
            "schema": "acfqp.v072_development_multirow_public_row.v1",
            "schema_version": "1.0.0",
            "context_id": row.context_id,
            "state_id": state_id,
            "state_ranks": list(row.state.ranks),
            "action": list(row.action),
            "remaining_horizon": row.remaining_horizon,
        },
    )


def _descriptor_id(value: Any) -> str:
    state_id = _state_id(value.successor_state)
    for observation_id in value.observation_ids:
        _cid(observation_id, "descriptor observation")
    if (
        tuple(value.observation_ids)
        != tuple(sorted(set(value.observation_ids)))
        or not _legal_actions(value.successor_state)
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "novel descriptor evidence is malformed"
        )
    return _hash(
        "descriptor",
        {
            "schema": (
                "acfqp.v072_development_multirow_novel_descriptor.v1"
            ),
            "successor_state_id": state_id,
            "successor_ranks": list(value.successor_state.ranks),
            "observation_ids": list(value.observation_ids),
        },
    )


def _closure_id(closure: Any) -> str:
    row_ids = tuple(_row_id(item) for item in closure.rows)
    if row_ids != tuple(sorted(set(row_ids))):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "closure rows are not distinct and sorted"
        )
    return _hash(
        "closure",
        {
            "schema": "acfqp.v072_development_multirow_current_closure.v1",
            "context_id": closure.context_id,
            "model_id": closure.model_id,
            "physical_row_ids": list(row_ids),
        },
    )


def _upstream_row_id(value: Any) -> str:
    if (
        type(value)
        is not materializer_types.DevelopmentUpstreamRowTranscriptV1
        or value.physical_row.remaining_horizon != 2
        or value.semantic_role not in (
            "PROMOTED_PARENT_ROOT_ROW",
            "AUXILIARY_ROOT_ROW",
        )
        or value.discovery_draws != DISCOVERY_DRAWS
        or value.validation_draws != PARENT_DRAWS
        or value.arm not in selector.ADAPTIVE_ARMS
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "upstream root-row transcript has invalid metadata"
        )
    discovery_digest, discovery_counts = _upstream_raw_summary(
        value.discovery_seed_id,
        "UPSTREAM_DISCOVERY",
        value.law_key.value,
        DISCOVERY_DRAWS,
        value.semantic_role,
    )
    validation_digest, validation_counts = _upstream_raw_summary(
        value.validation_seed_id,
        "UPSTREAM_VALIDATION",
        value.law_key.value,
        PARENT_DRAWS,
        value.semantic_role,
    )
    if (
        discovery_digest != value.discovery_raw_digest
        or validation_digest != value.validation_raw_digest
        or discovery_counts != value.discovery_bucket_counts
        or validation_counts != value.validation_bucket_counts
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "upstream root-row raw transcript does not replay"
        )
    discovery_stream_id = _upstream_stream_id(
        value,
        lane="UPSTREAM_DISCOVERY",
        draws=DISCOVERY_DRAWS,
        seed_id=value.discovery_seed_id,
        raw_digest=discovery_digest,
    )
    validation_stream_id = _upstream_stream_id(
        value,
        lane="UPSTREAM_VALIDATION",
        draws=PARENT_DRAWS,
        seed_id=value.validation_seed_id,
        raw_digest=validation_digest,
    )
    discovery_range = _verify_upstream_range(
        value,
        lane="UPSTREAM_DISCOVERY",
        draws=DISCOVERY_DRAWS,
        stream_id=discovery_stream_id,
    )
    validation_range = _verify_upstream_range(
        value,
        lane="UPSTREAM_VALIDATION",
        draws=PARENT_DRAWS,
        stream_id=validation_stream_id,
    )
    return _hash(
        "upstream_row",
        {
            "schema": (
                "acfqp.v072_development_multirow_upstream_row_transcript.v1"
            ),
            "schema_version": "1.0.0",
            "law_key": value.law_key.value,
            "arm": value.arm,
            "physical_row_id": _row_id(value.physical_row),
            "semantic_role": value.semantic_role,
            "discovery_seed_id": value.discovery_seed_id,
            "validation_seed_id": value.validation_seed_id,
            "discovery_crn_pairing_group_seed_id":
                value.discovery_seed_id,
            "validation_crn_pairing_group_seed_id":
                value.validation_seed_id,
            "discovery_raw_digest": discovery_digest,
            "validation_raw_digest": validation_digest,
            "discovery_bucket_counts": list(discovery_counts),
            "validation_bucket_counts": list(validation_counts),
            "discovery_draws": DISCOVERY_DRAWS,
            "validation_draws": PARENT_DRAWS,
            "discovery_stream_id": discovery_stream_id,
            "validation_stream_id": validation_stream_id,
            "discovery_raw_commitment_range_proof_id":
                discovery_range,
            "validation_raw_commitment_range_proof_id":
                validation_range,
            "created_before_current_authorization": True,
            "target_endpoint_calls": 0,
            "hidden_law_queries": 0,
        },
    )


def _parent_id(parent: Any) -> str:
    epoch = parent.epoch
    descriptor_ids = tuple(
        _descriptor_id(item) for item in parent.novel_descriptors
    )
    if descriptor_ids != tuple(sorted(set(descriptor_ids))):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "parent novel descriptors are not canonical"
        )
    upstream_ids = tuple(
        _upstream_row_id(item) for item in parent.upstream_root_rows
    )
    if (
        upstream_ids != tuple(sorted(set(upstream_ids)))
        or parent.parent_physical_row_id
        not in {
            _row_id(item.physical_row)
            for item in parent.upstream_root_rows
        }
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "parent upstream row inventory is stale"
        )
    observation_ids: list[str] = []
    observation_raw_commitment_ids: list[str] = []
    if parent.epoch.round_index == 1:
        if (
            len(parent.upstream_novel_observations)
            != len(parent.novel_descriptors)
        ):
            raise IndependentIncrementalMaterializerVerificationFailure(
                "round-one upstream novelty inventory is incomplete"
            )
        for observation in parent.upstream_novel_observations:
            transcript = observation.transcript
            if (
                transcript.semantic_role
                != "PROMOTED_PARENT_ROOT_ROW"
                or observation.bucket not in (1, 2)
                or (
                    _upstream_word(
                        transcript.validation_seed_id,
                        "UPSTREAM_VALIDATION",
                        transcript.law_key.value,
                        observation.accepted_draw_index,
                        transcript.semantic_role,
                    )
                    & 3
                )
                != observation.bucket
            ):
                raise IndependentIncrementalMaterializerVerificationFailure(
                    "upstream novel observation semantics do not replay"
                )
            stream_id = _upstream_stream_id(
                transcript,
                lane="UPSTREAM_VALIDATION",
                draws=PARENT_DRAWS,
                seed_id=transcript.validation_seed_id,
                raw_digest=transcript.validation_raw_digest,
            )
            raw_commitment_id = _upstream_commitment_id(
                transcript,
                lane="UPSTREAM_VALIDATION",
                stream_id=stream_id,
                index=observation.accepted_draw_index,
            )
            observation_id = _hash(
                "upstream_observation",
                {
                    "schema": (
                        "acfqp.v072_development_multirow_"
                        "upstream_novel_observation.v1"
                    ),
                    "schema_version": "1.0.0",
                    "upstream_row_evidence_id": (
                        _upstream_row_id(transcript)
                    ),
                    "validation_stream_id": stream_id,
                    "accepted_draw_index": (
                        observation.accepted_draw_index
                    ),
                    "raw_commitment_id": raw_commitment_id,
                    "bucket": observation.bucket,
                    "successor_state_id": (
                        _state_id(observation.successor_state)
                    ),
                    "successor_ranks": list(
                        observation.successor_state.ranks
                    ),
                    "failure": False,
                    "terminal": False,
                    "bucket_to_public_semantics_frozen": True,
                },
            )
            observation_ids.append(observation_id)
            observation_raw_commitment_ids.append(raw_commitment_id)
        if (
            {
                _state_id(item.successor_state)
                for item in parent.upstream_novel_observations
            }
            != {
                _state_id(item.successor_state)
                for item in parent.novel_descriptors
            }
            or set(observation_raw_commitment_ids)
            != {
                observation_id
                for descriptor in parent.novel_descriptors
                for observation_id in descriptor.observation_ids
            }
        ):
            raise IndependentIncrementalMaterializerVerificationFailure(
                "upstream novelty does not induce the claimed descriptors"
            )
    elif parent.upstream_novel_observations:
        raise IndependentIncrementalMaterializerVerificationFailure(
            "round two cannot invent upstream novelty observations"
        )
    return _hash(
        "parent",
        {
            "schema": "acfqp.v072_development_multirow_parent_evidence.v1",
            "logical_occurrence_id": epoch.logical_occurrence_id,
            "context_id": epoch.context_id,
            "model_id": epoch.model_id,
            "audit_id": epoch.audit_id,
            "frontier_id": epoch.frontier_id,
            "threshold_profile_id": epoch.threshold_profile_id,
            "selected_policy_id": epoch.selected_policy_id,
            "parent_physical_row_id": parent.parent_physical_row_id,
            "support_epoch_id": parent.support_epoch_id,
            "selected_candidate_id": parent.selected_candidate_id,
            "selected_planner_row_id": parent.selected_planner_row_id,
            "old_support_descriptor_ids":
                list(parent.old_support_descriptor_ids),
            "novel_descriptor_ids": list(descriptor_ids),
            "upstream_root_row_evidence_ids": list(upstream_ids),
            "upstream_novel_observation_ids": sorted(observation_ids),
            "evidence_role": "DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY",
        },
    )


def _replay_cardinality(
    request: Any,
    previous_handoff: (
        materializer_types.IncrementalModelRebuildHandoffV1 | None
    ) = None,
    previous_handoff_id: str | None = None,
) -> tuple[str, tuple[Any, ...]]:
    evidence = request.cardinality_authority.evidence
    parent = request.parent_evidence
    closure = request.current_closure
    induced_by_id: dict[str, Any] = {}
    for descriptor in parent.novel_descriptors:
        for action in _legal_actions(descriptor.successor_state):
            candidate = materializer_types.DevelopmentPhysicalRowV1(
                descriptor.successor_state,
                action,
            )
            induced_by_id[_row_id(candidate)] = candidate
    induced = tuple(induced_by_id[key] for key in sorted(induced_by_id))
    present_ids = {_row_id(item) for item in closure.rows}
    present = tuple(item for item in induced if _row_id(item) in present_ids)
    acquire = tuple(
        item for item in induced if _row_id(item) not in present_ids
    )
    if evidence.round_index == 1:
        if (
            evidence.previous_evidence_id is not None
            or previous_handoff is not None
        ):
            raise IndependentIncrementalMaterializerVerificationFailure(
                "round-one cardinality has a predecessor"
            )
        previous_id = None
        cumulative = acquire
    elif evidence.round_index == 2:
        if (
            type(previous_handoff)
            is not materializer_types.IncrementalModelRebuildHandoffV1
            or previous_handoff_id is None
            or request.previous_handoff_id != previous_handoff_id
            or previous_handoff.request.parent_epoch.round_index != 1
        ):
            raise IndependentIncrementalMaterializerVerificationFailure(
                "round-two cardinality lacks its exact first handoff"
            )
        previous = (
            previous_handoff.request.cardinality_authority.evidence
        )
        previous_id = previous.evidence_id
        previous_rows = {
            _row_id(item): item for item in previous.cumulative_rows
        }
        if (
            evidence.previous_evidence_id != previous_id
            or not set(previous_rows).issubset(present_ids)
            or set(previous_rows)
            & {_row_id(item) for item in acquire}
        ):
            raise IndependentIncrementalMaterializerVerificationFailure(
                "round-two cardinality resets or reacquires prior rows"
            )
        cumulative_by_id = {
            **previous_rows,
            **{_row_id(item): item for item in acquire},
        }
        cumulative = tuple(
            cumulative_by_id[key] for key in sorted(cumulative_by_id)
        )
    else:
        raise IndependentIncrementalMaterializerVerificationFailure(
            "cardinality round index is invalid"
        )
    round_upper = PARENT_DRAWS + CHILD_DRAWS * len(acquire)
    cumulative_upper = (
        PARENT_DRAWS * evidence.round_index
        + CHILD_DRAWS * len(cumulative)
    )
    payload = {
        "schema": (
            "acfqp.v072_development_multirow_cardinality_evidence.v1"
        ),
        "parent_evidence_id": _parent_id(parent),
        "logical_occurrence_id": evidence.logical_occurrence_id,
        "context_id": evidence.context_id,
        "model_id": evidence.model_id,
        "audit_id": evidence.audit_id,
        "frontier_id": evidence.frontier_id,
        "threshold_profile_id": evidence.threshold_profile_id,
        "selected_candidate_id": evidence.selected_candidate_id,
        "selected_planner_row_id": evidence.selected_planner_row_id,
        "support_epoch_id": evidence.support_epoch_id,
        "current_closure_id": _closure_id(closure),
        "round_index": evidence.round_index,
        "previous_evidence_id": previous_id,
        "induced_row_ids": [_row_id(item) for item in induced],
        "already_present_row_ids": [_row_id(item) for item in present],
        "rows_to_acquire_ids": [_row_id(item) for item in acquire],
        "cumulative_row_ids": [_row_id(item) for item in cumulative],
        "exact_round_draw_upper": round_upper,
        "cumulative_draw_upper": cumulative_upper,
        "formula": "2048*r+8256*cardinality(distinct_union)",
        "caller_supplied_mapping": False,
        "caller_supplied_count": False,
    }
    evidence_id = _hash("cardinality", payload)
    if (
        evidence_id != evidence.evidence_id
        or tuple(_row_id(item) for item in evidence.induced_rows)
        != tuple(_row_id(item) for item in induced)
        or tuple(_row_id(item) for item in evidence.rows_to_acquire)
        != tuple(_row_id(item) for item in acquire)
        or evidence.exact_round_draw_upper != round_upper
        or evidence.cumulative_draw_upper != cumulative_upper
        or len(cumulative) > MAX_ROWS
        or cumulative_upper > MAX_DRAWS
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "evidence-first cardinality differs from public replay"
        )
    gain = request.cardinality_authority.selector_gain
    if (
        gain.cardinality_evidence_id != evidence_id
        or gain.exact_draw_upper != round_upper
        or gain.model_id != evidence.model_id
        or gain.audit_id != evidence.audit_id
        or gain.frontier_id != evidence.frontier_id
        or gain.candidate_id != evidence.selected_candidate_id
        or gain.planner_row_id != evidence.selected_planner_row_id
        or not gain.eligible
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "selector gain did not consume replayed cardinality"
        )
    authority_id = _hash(
        "cardinality_authority",
        {
            "schema": (
                "acfqp.v072_development_multirow_cardinality_authority.v1"
            ),
            "evidence_id": evidence_id,
            "selector_counterfactual_id": gain.counterfactual_id,
            "positive_gain_required": True,
            "development_only": True,
        },
    )
    if authority_id != request.cardinality_authority.authority_id:
        raise IndependentIncrementalMaterializerVerificationFailure(
            "cardinality authority ID differs"
        )
    return authority_id, acquire


def _request_id(
    request: Any,
    previous_handoff: (
        materializer_types.IncrementalModelRebuildHandoffV1 | None
    ) = None,
    previous_handoff_id: str | None = None,
) -> str:
    if type(request) is not materializer_types.IncrementalMaterializationRequestV1:
        raise IndependentIncrementalMaterializerVerificationFailure(
            "request does not have exact type"
        )
    authority_id, _acquire = _replay_cardinality(
        request,
        previous_handoff,
        previous_handoff_id,
    )
    epoch = request.parent_epoch
    access = request.preauthorization_access
    auth = request.authorization
    evidence = request.cardinality_authority.evidence
    upstream_ids = tuple(
        _upstream_row_id(item)
        for item in request.parent_evidence.upstream_root_rows
    )
    expected_parent_model = _hash(
        "parent_model",
        {
            "schema": (
                "acfqp.v072_development_multirow_parent_model_snapshot.v1"
            ),
            "schema_version": "1.0.0",
            "context_id": epoch.context_id,
            "law_key": request.parent_evidence.upstream_root_rows[0]
                .law_key.value,
            "upstream_root_row_evidence_ids": list(upstream_ids),
            "physical_row_ids": [
                _row_id(item.physical_row)
                for item in request.parent_evidence.upstream_root_rows
            ],
            "actual_transcript_bound": True,
        },
    )
    if (
        epoch.context_id != _context_id()
        or (
            epoch.round_index == 1
            and epoch.model_id != expected_parent_model
        )
        or (
            epoch.round_index == 2
            and (
                type(previous_handoff)
                is not materializer_types
                .IncrementalModelRebuildHandoffV1
                or previous_handoff_id is None
                or request.previous_handoff_id
                != previous_handoff_id
                or epoch.model_id
                == previous_handoff.request.parent_epoch.model_id
            )
        )
        or epoch.closure_id != _closure_id(request.current_closure)
        or request.parent_evidence.epoch != epoch
        or access.registry_id
        != request.cardinality_authority.selector_gain.registry_id
        or auth.registry_id != access.registry_id
        or access.model_id != epoch.model_id
        or auth.model_id != epoch.model_id
        or access.audit_id != epoch.audit_id
        or auth.audit_id != epoch.audit_id
        or access.frontier_id != epoch.frontier_id
        or auth.frontier_id != epoch.frontier_id
        or access.access_log_id != auth.access_log_id
        or auth.selected_exact_draw_upper
        != evidence.exact_round_draw_upper
        or auth.cumulative_new_child_actions_after_selection
        != len(evidence.cumulative_rows)
        or auth.cumulative_draw_upper_after_selection
        != evidence.cumulative_draw_upper
        or auth.authorization_sequence
        != 2 * epoch.round_index - 1
        or auth.target_access_sequence_minimum
        != 2 * epoch.round_index
        or auth.round_index != epoch.round_index
        or access.round_index != epoch.round_index
        or auth.arm.value != epoch.arm
        or tuple(item.path for item in access.native_zero_counters)
        != selector.REQUIRED_NATIVE_ZERO_PATHS
        or any(
            item.value != 0 or item.observed is not True
            for item in access.native_zero_counters
        )
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "parent/authorization/pre-freeze zero chain differs"
        )
    freeze_id = _hash(
        "freeze",
        {
            "schema": "acfqp.v072_incremental_authorization_freeze.v1",
            "cardinality_authority_id": authority_id,
            "cardinality_evidence_id": evidence.evidence_id,
            "access_log_id": access.access_log_id,
            "authorization_id": auth.authorization_id,
            "native_zero_counter_ids": sorted(
                item.counter_id for item in access.native_zero_counters
            ),
            "round_index": epoch.round_index,
            "authorization_sequence": 2 * epoch.round_index - 1,
            "first_execution_sequence": 2 * epoch.round_index,
            "observer_and_materializer_counters_zero": True,
        },
    )
    if freeze_id != request.authorization_freeze_id:
        raise IndependentIncrementalMaterializerVerificationFailure(
            "authorization freeze differs from native-zero replay"
        )
    result = _hash(
        "request",
        {
            "schema": "acfqp.v072_incremental_materialization_request.v1",
            "logical_occurrence_id": epoch.logical_occurrence_id,
            "context_id": epoch.context_id,
            "round_index": epoch.round_index,
            "parent_closure_id": epoch.closure_id,
            "parent_model_id": epoch.model_id,
            "parent_audit_id": epoch.audit_id,
            "parent_frontier_id": epoch.frontier_id,
            "parent_selected_plan_id": epoch.selected_plan_id,
            "parent_selected_policy_id": epoch.selected_policy_id,
            "parent_build_epoch_id": epoch.build_epoch_id,
            "parent_evidence_id": _parent_id(request.parent_evidence),
            "cardinality_authority_id": authority_id,
            "authorization_freeze_id": freeze_id,
            "previous_handoff_id": request.previous_handoff_id,
        },
    )
    if result != request.request_id:
        raise IndependentIncrementalMaterializerVerificationFailure(
            "request content identity differs"
        )
    return result


def _raw_summary(
    seed_id: str,
    lane: str,
    law_key: str,
    draws: int,
    round_index: int = 1,
) -> tuple[str, tuple[int, int, int, int]]:
    digest = hashlib.sha256()
    counts = [0, 0, 0, 0]
    for index in range(draws):
        value = int.from_bytes(
            hashlib.sha256(
                b"acfqp:v072-development-multirow-word:v1\x00"
                + bytes.fromhex(seed_id)
                + b"\x00"
                + lane.encode("ascii")
                + b"\x00"
                + law_key.encode("ascii")
                + b"\x00"
                + index.to_bytes(8, "big")
            ).digest()[:8],
            "big",
        )
        if law_key == "HASH_BUCKET_LAW_A":
            if lane == "PARENT_FRESH_VALIDATION":
                value = (value & ~3) | (index & 1)
            else:
                value &= ~3
        elif (
            round_index == 2
            and lane == "PARENT_FRESH_VALIDATION"
        ):
            value = (value & ~3) | (index & 1)
        elif lane != "PARENT_FRESH_VALIDATION":
            value &= ~3
        digest.update(value.to_bytes(8, "big"))
        counts[value & 3] += 1
    return digest.hexdigest(), tuple(counts)  # type: ignore[return-value]


def _upstream_word(
    seed_id: str,
    lane: str,
    law_key: str,
    index: int,
    semantic_role: str,
) -> int:
    value = int.from_bytes(
        hashlib.sha256(
            b"acfqp:v072-development-multirow-upstream-word:v1\x00"
            + bytes.fromhex(seed_id)
            + b"\x00"
            + lane.encode("ascii")
            + b"\x00"
            + law_key.encode("ascii")
            + b"\x00"
            + index.to_bytes(8, "big")
        ).digest()[:8],
        "big",
    )
    if semantic_role == "PROMOTED_PARENT_ROOT_ROW":
        if lane == "UPSTREAM_DISCOVERY":
            return value & ~3
        return (value & ~3) | (index % 3)
    if (
        law_key == "HASH_BUCKET_LAW_B"
        and lane == "UPSTREAM_VALIDATION"
    ):
        return value
    return (value & ~3) | (index & 1)


def _upstream_raw_summary(
    seed_id: str,
    lane: str,
    law_key: str,
    draws: int,
    semantic_role: str,
) -> tuple[str, tuple[int, int, int, int]]:
    digest = hashlib.sha256()
    counts = [0, 0, 0, 0]
    for index in range(draws):
        value = _upstream_word(
            seed_id,
            lane,
            law_key,
            index,
            semantic_role,
        )
        digest.update(value.to_bytes(8, "big"))
        counts[value & 3] += 1
    return digest.hexdigest(), tuple(counts)  # type: ignore[return-value]


def _upstream_stream_id(
    transcript: Any,
    *,
    lane: str,
    draws: int,
    seed_id: str,
    raw_digest: str,
) -> str:
    return _hash(
        "stream",
        {
            "schema": (
                "acfqp.v072_development_multirow_upstream_raw_stream.v1"
            ),
            "schema_version": "1.0.0",
            "law_key": transcript.law_key.value,
            "arm": transcript.arm,
            "context_id": transcript.physical_row.context_id,
            "physical_row_id": _row_id(transcript.physical_row),
            "semantic_role": transcript.semantic_role,
            "lane": lane,
            "draw_count": draws,
            "seed_id": seed_id,
            "crn_pairing_group_seed_id": seed_id,
            "raw_word_digest": raw_digest,
            "created_before_current_authorization": True,
            "incremental_suffix_counter": False,
        },
    )


def _upstream_commitment_id(
    transcript: Any,
    *,
    lane: str,
    stream_id: str,
    index: int,
) -> str:
    seed_id = (
        transcript.discovery_seed_id
        if lane == "UPSTREAM_DISCOVERY"
        else transcript.validation_seed_id
    )
    word = _upstream_word(
        seed_id,
        lane,
        transcript.law_key.value,
        index,
        transcript.semantic_role,
    )
    return _hash(
        "raw_commitment",
        {
            "schema": (
                "acfqp.v072_development_multirow_raw_commitment.v1"
            ),
            "schema_version": "1.0.0",
            "stream_id": stream_id,
            "accepted_draw_index": index,
            "word_u64_hex": f"{word:016x}",
            "accepted_exactly_once": True,
        },
    )


def _verify_upstream_range(
    transcript: Any,
    *,
    lane: str,
    draws: int,
    stream_id: str,
    claimed: Any | None = None,
) -> str:
    if claimed is not None and (
        type(claimed) is not materializer_types.RawCommitmentRangeProofV1
        or claimed.stream_id != stream_id
        or claimed.draw_count != draws
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "upstream raw commitment range is missing or transplanted"
        )
    digest = hashlib.sha256()
    seen: set[str] = set()
    first = ""
    last = ""
    for index in range(draws):
        item = _upstream_commitment_id(
            transcript,
            lane=lane,
            stream_id=stream_id,
            index=index,
        )
        if index == 0:
            first = item
        last = item
        digest.update(bytes.fromhex(item))
        seen.add(item)
    payload = {
        "schema": (
            "acfqp.v072_development_multirow_raw_commitment_range.v1"
        ),
        "schema_version": "1.0.0",
        "stream_id": stream_id,
        "accepted_draw_index_range": {"first": 0, "last": draws - 1},
        "draw_count": draws,
        "first_commitment_id": first,
        "last_commitment_id": last,
        "ordered_commitment_digest": digest.hexdigest(),
        "unique_commitment_count": len(seen),
        "complete_contiguous_range": True,
    }
    range_proof_id = _hash("raw_range", payload)
    if claimed is not None and (
        claimed.first_commitment_id != first
        or claimed.last_commitment_id != last
        or claimed.ordered_commitment_digest != digest.hexdigest()
        or claimed.unique_commitment_count != draws
        or claimed.range_proof_id != range_proof_id
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "upstream raw commitment range does not replay"
        )
    return range_proof_id


def _stream_id(
    stream: Any,
    *,
    lane: str,
    draws: int,
    transaction_id: str,
    build_epoch_id: str,
    physical_row_id: str,
    parent_stream_id: str | None,
) -> str:
    if (
        type(stream)
        is not materializer_types.DevelopmentRawObservationStreamV1
        or stream.lane.value != lane
        or stream.draw_count != draws
        or stream.transaction_id != transaction_id
        or stream.build_epoch_id != build_epoch_id
        or stream.physical_row_id != physical_row_id
        or stream.parent_stream_id != parent_stream_id
        or stream.arm not in selector.ADAPTIVE_ARMS
        or stream.seed_id != stream.crn_pairing_group_seed_id
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "raw stream lane/count/lineage differs"
        )
    digest, counts = _raw_summary(
        stream.seed_id,
        lane,
        stream.law_key.value,
        draws,
        stream.round_index,
    )
    if digest != stream.raw_word_digest or counts != stream.outcome_bucket_counts:
        raise IndependentIncrementalMaterializerVerificationFailure(
            "raw word tape differs from independent replay"
        )
    payload = {
        "schema": "acfqp.v072_development_multirow_raw_stream.v1",
        "schema_version": "1.0.0",
        "law_key": stream.law_key.value,
        "arm": stream.arm,
        "logical_occurrence_id": stream.logical_occurrence_id,
        "transaction_id": transaction_id,
        "build_epoch_id": build_epoch_id,
        "context_id": stream.context_id,
        "round_index": stream.round_index,
        "physical_row_id": physical_row_id,
        "parent_stream_id": parent_stream_id,
        "lane": lane,
        "draw_count": draws,
        "seed_id": stream.seed_id,
        "crn_pairing_group_seed_id":
            stream.crn_pairing_group_seed_id,
        "raw_word_digest": digest,
        "outcome_bucket_counts": list(counts),
        "target_endpoint_calls": 0,
        "hidden_law_queries": 0,
    }
    result = _hash("stream", payload)
    if result != stream.stream_id:
        raise IndependentIncrementalMaterializerVerificationFailure(
            "stream content ID differs"
        )
    return result


def _raw_commitment_id(stream: Any, index: int) -> str:
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
            word = (word & ~3) | (index & 1)
        else:
            word &= ~3
    elif (
        stream.round_index == 2
        and stream.lane.value == "PARENT_FRESH_VALIDATION"
    ):
        word = (word & ~3) | (index & 1)
    elif stream.lane.value != "PARENT_FRESH_VALIDATION":
        word &= ~3
    return _hash(
        "raw_commitment",
        {
            "schema": (
                "acfqp.v072_development_multirow_raw_commitment.v1"
            ),
            "schema_version": "1.0.0",
            "stream_id": stream.stream_id,
            "accepted_draw_index": index,
            "word_u64_hex": f"{word:016x}",
            "accepted_exactly_once": True,
        },
    )


def _verify_raw_range(stream: Any, claimed: Any) -> str:
    if (
        type(claimed) is not materializer_types.RawCommitmentRangeProofV1
        or claimed.stream_id != stream.stream_id
        or claimed.draw_count != stream.draw_count
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "raw commitment range is missing or transplanted"
        )
    digest = hashlib.sha256()
    seen: set[str] = set()
    first = ""
    last = ""
    for index in range(stream.draw_count):
        commitment_id = _raw_commitment_id(stream, index)
        if index == 0:
            first = commitment_id
        last = commitment_id
        seen.add(commitment_id)
        digest.update(bytes.fromhex(commitment_id))
    payload = {
        "schema": (
            "acfqp.v072_development_multirow_raw_commitment_range.v1"
        ),
        "schema_version": "1.0.0",
        "stream_id": stream.stream_id,
        "accepted_draw_index_range": {
            "first": 0,
            "last": stream.draw_count - 1,
        },
        "draw_count": stream.draw_count,
        "first_commitment_id": first,
        "last_commitment_id": last,
        "ordered_commitment_digest": digest.hexdigest(),
        "unique_commitment_count": len(seen),
        "complete_contiguous_range": True,
    }
    if (
        claimed.first_commitment_id != first
        or claimed.last_commitment_id != last
        or claimed.ordered_commitment_digest != digest.hexdigest()
        or claimed.unique_commitment_count != stream.draw_count
        or claimed.range_proof_id != _hash("raw_range", payload)
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "raw commitment range/cardinality does not replay"
        )
    return claimed.range_proof_id


@dataclass(frozen=True, slots=True)
class IndependentIncrementalMaterializerAttestationV1:
    run_id: str
    handoff_id: str
    law_key: str
    context_id: str
    logical_occurrence_id: str
    transaction_id: str
    build_epoch_id: str
    acquired_child_row_count: int
    exact_draw_count: int
    status: str
    round_index: int = 1
    previous_handoff_id: str | None = None

    def __post_init__(self) -> None:
        for value in (
            self.run_id,
            self.handoff_id,
            self.context_id,
            self.logical_occurrence_id,
            self.transaction_id,
            self.build_epoch_id,
        ):
            _cid(value, "attestation identity")
        if self.previous_handoff_id is not None:
            _cid(self.previous_handoff_id, "attestation predecessor")
        expected_draws = (
            PARENT_DRAWS
            + CHILD_DRAWS * self.acquired_child_row_count
        )
        if (
            self.law_key not in ("HASH_BUCKET_LAW_A", "HASH_BUCKET_LAW_B")
            or self.round_index not in (1, 2)
            or (self.round_index == 1)
            != (self.previous_handoff_id is None)
            or not 0 <= self.acquired_child_row_count <= MAX_ROWS
            or self.exact_draw_count != expected_draws
            or self.status != PENDING
        ):
            raise IndependentIncrementalMaterializerVerificationFailure(
                "attestation claim is malformed"
            )

    @property
    def attestation_id(self) -> str:
        return _hash(
            "attestation",
            {
                "schema": (
                    "acfqp.v072_incremental_materializer_independent_attestation.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "verification_profile": VERIFICATION_PROFILE,
                "run_id": self.run_id,
                "handoff_id": self.handoff_id,
                "law_key": self.law_key,
                "context_id": self.context_id,
                "logical_occurrence_id": self.logical_occurrence_id,
                "transaction_id": self.transaction_id,
                "build_epoch_id": self.build_epoch_id,
                "acquired_child_row_count":
                    self.acquired_child_row_count,
                "exact_draw_count": self.exact_draw_count,
                "round_index": self.round_index,
                "previous_handoff_id": self.previous_handoff_id,
                "status": self.status,
                "production_execution_helpers_called": [],
            },
        )


def _verify_incremental_materializer_v1(
    claimed: (
        materializer_types.DevelopmentAcquisitionControlRunV1
        | materializer_types.IncrementalModelRebuildHandoffV1
    ),
    *,
    previous_handoff: (
        materializer_types.IncrementalModelRebuildHandoffV1 | None
    ) = None,
    control_handoff_role: bool = False,
) -> IndependentIncrementalMaterializerAttestationV1:
    """Replay one acquisition/handoff without executing production."""

    if type(claimed) is materializer_types.DevelopmentAcquisitionControlRunV1:
        if control_handoff_role:
            raise IndependentIncrementalMaterializerVerificationFailure(
                "control-role handoff replay cannot accept a control wrapper"
            )
        handoff = claimed.handoff
        law_key = claimed.law_key
        control_run = True
        claimed_run_id = claimed.run_id
        if previous_handoff is not None:
            raise IndependentIncrementalMaterializerVerificationFailure(
                "round-one control cannot bind a prior handoff"
            )
    elif type(claimed) is materializer_types.IncrementalModelRebuildHandoffV1:
        handoff = claimed
        law_key = claimed.law_key
        control_run = control_handoff_role
        claimed_run_id = None
        if control_handoff_role and previous_handoff is not None:
            raise IndependentIncrementalMaterializerVerificationFailure(
                "round-one control handoff cannot bind a prior handoff"
            )
    else:
        raise IndependentIncrementalMaterializerVerificationFailure(
            "claimed run/handoff does not have exact type"
        )
    request = handoff.request
    round_index = request.parent_epoch.round_index
    previous_handoff_id = None
    if previous_handoff is not None:
        previous_handoff_id = (
            verify_incremental_materializer_handoff_v1(
                previous_handoff
            ).handoff_id
        )
    request_id = _request_id(
        request,
        previous_handoff,
        previous_handoff_id,
    )
    transaction_id = _hash(
        "transaction",
        {
            "schema": "acfqp.v072_incremental_transaction.v1",
            "request_id": request_id,
            "authorization_id": request.authorization.authorization_id,
            "round_index": round_index,
            "transaction_index": round_index,
        },
    )
    build_epoch_id = _hash(
        "epoch",
        {
            "schema": "acfqp.v072_incremental_build_epoch.v1",
            "parent_build_epoch_id":
                request.parent_epoch.build_epoch_id,
            "parent_model_id": request.parent_epoch.model_id,
            "transaction_id": transaction_id,
            "round_index": round_index,
        },
    )
    if (
        handoff.transaction_id != transaction_id
        or handoff.build_epoch_id != build_epoch_id
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "transaction/build epoch differs from preexecution identities"
        )
    _stream_id(
        handoff.parent_validation_stream,
        lane="PARENT_FRESH_VALIDATION",
        draws=PARENT_DRAWS,
        transaction_id=transaction_id,
        build_epoch_id=build_epoch_id,
        physical_row_id=request.parent_evidence.parent_physical_row_id,
        parent_stream_id=None,
    )
    all_streams = [handoff.parent_validation_stream]
    expected_rows = request.cardinality_authority.evidence.rows_to_acquire
    if tuple(
        _row_id(item.physical_row) for item in handoff.child_rows
    ) != tuple(_row_id(item) for item in expected_rows):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "materialized rows differ from frozen absent-row list"
        )
    row_evidence_ids: list[str] = []
    for item in handoff.child_rows:
        all_streams.extend(
            (item.discovery_stream, item.validation_stream)
        )
        row_id = _row_id(item.physical_row)
        discovery_id = _stream_id(
            item.discovery_stream,
            lane="CHILD_FRESH_DISCOVERY",
            draws=DISCOVERY_DRAWS,
            transaction_id=transaction_id,
            build_epoch_id=build_epoch_id,
            physical_row_id=row_id,
            parent_stream_id=None,
        )
        validation_id = _stream_id(
            item.validation_stream,
            lane="CHILD_FRESH_VALIDATION",
            draws=VALIDATION_DRAWS,
            transaction_id=transaction_id,
            build_epoch_id=build_epoch_id,
            physical_row_id=row_id,
            parent_stream_id=discovery_id,
        )
        evidence_id = _hash(
            "row_evidence",
            {
                "schema": (
                    "acfqp.v072_development_multirow_materialized_row_evidence.v1"
                ),
                "physical_row_id": row_id,
                "discovery_stream_id": discovery_id,
                "validation_stream_id": validation_id,
                "discovery_draws": DISCOVERY_DRAWS,
                "validation_draws": VALIDATION_DRAWS,
            },
        )
        if evidence_id != item.row_evidence_id:
            raise IndependentIncrementalMaterializerVerificationFailure(
                "row evidence ID differs from independent stream replay"
            )
        row_evidence_ids.append(evidence_id)
    range_by_stream = {
        item.stream_id: item for item in handoff.raw_commitment_ranges
    }
    if (
        len(range_by_stream) != len(handoff.raw_commitment_ranges)
        or set(range_by_stream)
        != {item.stream_id for item in all_streams}
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "raw commitment range inventory is incomplete"
        )
    raw_range_ids = [
        _verify_raw_range(stream, range_by_stream[stream.stream_id])
        for stream in sorted(all_streams, key=lambda item: item.stream_id)
    ]
    prior_ranges = tuple(
        sorted(
            handoff.prior_cold_raw_commitment_ranges,
            key=lambda item: item.stream_id,
        )
    )
    prior_by_stream = {item.stream_id: item for item in prior_ranges}
    expected_prior_stream_ids: set[str] = set()
    verified_prior_range_ids: dict[str, str] = {}
    for transcript in request.parent_evidence.upstream_root_rows:
        for lane, draws, seed_id, raw_digest in (
            (
                "UPSTREAM_DISCOVERY",
                DISCOVERY_DRAWS,
                transcript.discovery_seed_id,
                transcript.discovery_raw_digest,
            ),
            (
                "UPSTREAM_VALIDATION",
                PARENT_DRAWS,
                transcript.validation_seed_id,
                transcript.validation_raw_digest,
            ),
        ):
            stream_id = _upstream_stream_id(
                transcript,
                lane=lane,
                draws=draws,
                seed_id=seed_id,
                raw_digest=raw_digest,
            )
            expected_prior_stream_ids.add(stream_id)
            claimed_range = prior_by_stream.get(stream_id)
            verified_prior_range_ids[stream_id] = (
                _verify_upstream_range(
                    transcript,
                    lane=lane,
                    draws=draws,
                    stream_id=stream_id,
                    claimed=claimed_range,
                )
            )
    prior_range_ids = [
        verified_prior_range_ids[item.stream_id]
        for item in prior_ranges
    ]
    if (
        len(prior_by_stream) != len(prior_ranges)
        or set(prior_by_stream) != expected_prior_stream_ids
        or {
            item.stream_id for item in prior_ranges
        }
        & {item.stream_id for item in all_streams}
        or sum(item.draw_count for item in prior_ranges)
        != len(request.parent_evidence.upstream_root_rows)
        * (DISCOVERY_DRAWS + PARENT_DRAWS)
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "prior-cold and incremental raw ledgers overlap or omit work"
        )
    n = len(expected_rows)
    exact_draws = PARENT_DRAWS + CHILD_DRAWS * n
    counters_payload = {
        "schema": "acfqp.v072_incremental_native_counters.v1",
        "round_index": round_index,
        "acquired_child_rows": n,
        "parent_discovery_draws": 0,
        "parent_validation_draws": PARENT_DRAWS,
        "child_discovery_draws": DISCOVERY_DRAWS * n,
        "child_validation_draws": VALIDATION_DRAWS * n,
        "observer_calls": 1 + 2 * n,
        "random_word_calls": exact_draws,
        "accepted_draws": exact_draws,
        "materializer_calls": 1,
        "target_endpoint_calls": 0,
        "hidden_law_queries": 0,
    }
    if (
        handoff.counters._payload() != counters_payload
        or handoff.counters.counter_id != _hash("counters", counters_payload)
        or exact_draws
        != request.cardinality_authority.evidence.exact_round_draw_upper
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "native work counters differ from exact formula"
        )
    union = tuple(
        sorted(
            {
                *request.parent_epoch.physical_row_ids,
                *(_row_id(item) for item in expected_rows),
            }
        )
    )
    if len(set(_row_id(item) for item in expected_rows)) != n:
        raise IndependentIncrementalMaterializerVerificationFailure(
            "a child row is duplicated or double charged"
        )
    row_set_id = _hash(
        "physical_set",
        {
            "schema": (
                "acfqp.v072_development_multirow_physical_row_set.v1"
            ),
            "context_id": request.parent_epoch.context_id,
            "physical_row_ids": list(union),
        },
    )
    if (
        handoff.resulting_physical_row_ids != union
        or handoff.resulting_physical_row_set_id != row_set_id
        or handoff.status != PENDING
        or any(
            value is not None
            for value in (
                handoff.model_id,
                handoff.selected_policy_id,
                handoff.audit_id,
                handoff.frontier_id,
            )
        )
    ):
        raise IndependentIncrementalMaterializerVerificationFailure(
            "handoff invents model/planner/audit or has wrong row union"
        )
    handoff_payload = {
        "schema": "acfqp.v072_incremental_model_rebuild_handoff.v1",
        "schema_version": "1.0.0",
        "law_key": handoff.law_key.value,
        "request_id": request_id,
        "authorization_freeze_id": request.authorization_freeze_id,
        "transaction_id": transaction_id,
        "build_epoch_id": build_epoch_id,
        "round_index": round_index,
        "parent_validation_stream_id":
            handoff.parent_validation_stream.stream_id,
        "child_row_evidence_ids": row_evidence_ids,
        "raw_commitment_range_proof_ids": raw_range_ids,
        "prior_cold_raw_commitment_range_proof_ids":
            prior_range_ids,
        "prior_cold_draws": sum(
            item.draw_count for item in prior_ranges
        ),
        "incremental_suffix_draws": exact_draws,
        "prior_cold_work_double_charged": False,
        "counter_id": handoff.counters.counter_id,
        "resulting_physical_row_ids": list(union),
        "resulting_physical_row_set_id": row_set_id,
        "status": PENDING,
        "model": {"kind": "PENDING_STANDARD_MODEL_REBUILD"},
        "selected_policy": {"kind": "NOT_AVAILABLE"},
        "audit": {"kind": "NOT_RUN"},
        "frontier": {"kind": "NOT_AVAILABLE"},
        "certificate_authority": False,
    }
    handoff_id = _hash("handoff", handoff_payload)
    if handoff_id != handoff.handoff_id:
        raise IndependentIncrementalMaterializerVerificationFailure(
            "handoff content ID differs"
        )
    run_payload = (
        {
            "schema": (
                "acfqp.v072_development_multirow_acquisition_run.v1"
            ),
            "schema_version": "1.0.0",
            "law_key": law_key.value,
            "arm": handoff.request.parent_epoch.arm,
            "handoff_id": handoff_id,
            "status": PENDING,
            "registered_target_evidence": False,
            "certificate_authority": False,
            "caller_supplied_result": False,
        }
        if control_run
        else {
            "schema": (
                "acfqp.v072_independently_verified_"
                "incremental_handoff_run.v1"
            ),
            "schema_version": "1.0.0",
            "law_key": law_key.value,
            "arm": handoff.request.parent_epoch.arm,
            "handoff_id": handoff_id,
            "round_index": round_index,
            "previous_handoff_id": request.previous_handoff_id,
            "status": PENDING,
            "certificate_authority": False,
        }
    )
    run_id = _hash("run", run_payload)
    if claimed_run_id is not None and run_id != claimed_run_id:
        raise IndependentIncrementalMaterializerVerificationFailure(
            "run content ID differs"
        )
    return IndependentIncrementalMaterializerAttestationV1(
        run_id,
        handoff_id,
        law_key.value,
        request.parent_epoch.context_id,
        request.parent_epoch.logical_occurrence_id,
        transaction_id,
        build_epoch_id,
        n,
        exact_draws,
        PENDING,
        round_index,
        request.previous_handoff_id,
    )


def verify_development_incremental_materializer_control_v1(
    claimed: (
        materializer_types.DevelopmentAcquisitionControlRunV1
        | materializer_types.IncrementalModelRebuildHandoffV1
    ),
    *,
    previous_handoff: (
        materializer_types.IncrementalModelRebuildHandoffV1 | None
    ) = None,
) -> IndependentIncrementalMaterializerAttestationV1:
    """Replay the complete acquisition/control wrapper or generic handoff."""

    return _verify_incremental_materializer_v1(
        claimed,
        previous_handoff=previous_handoff,
    )


def verify_development_control_handoff_role_v1(
    claimed: materializer_types.IncrementalModelRebuildHandoffV1,
) -> IndependentIncrementalMaterializerAttestationV1:
    """Derive the round-one control-role ID directly from its handoff.

    This entry point exists for higher-level independent verifiers.  It avoids
    constructing the production ``DevelopmentAcquisitionControlRunV1`` merely
    to select the control-role content domain.
    """

    if type(claimed) is not materializer_types.IncrementalModelRebuildHandoffV1:
        raise IndependentIncrementalMaterializerVerificationFailure(
            "control-role replay requires one exact materializer handoff"
        )
    return _verify_incremental_materializer_v1(
        claimed,
        control_handoff_role=True,
    )


def verify_incremental_materializer_handoff_v1(
    claimed: materializer_types.IncrementalModelRebuildHandoffV1,
    *,
    previous_handoff: (
        materializer_types.IncrementalModelRebuildHandoffV1 | None
    ) = None,
) -> IndependentIncrementalMaterializerAttestationV1:
    """Independently replay either exact incremental transaction."""

    return verify_development_incremental_materializer_control_v1(
        claimed,
        previous_handoff=previous_handoff,
    )


__all__ = [
    "IndependentIncrementalMaterializerAttestationV1",
    "IndependentIncrementalMaterializerVerificationFailure",
    "SCHEMA_VERSION",
    "VERIFICATION_PROFILE",
    "verify_development_control_handoff_role_v1",
    "verify_development_incremental_materializer_control_v1",
    "verify_incremental_materializer_handoff_v1",
]
