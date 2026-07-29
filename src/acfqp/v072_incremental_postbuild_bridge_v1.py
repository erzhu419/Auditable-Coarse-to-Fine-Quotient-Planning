"""Exact post-build bridge for V0-072 development incremental acquisition.

The bridge consumes one immutable materializer handoff and derives, without
caller-supplied planner output:

1. a standard ``V072ColdH2ClosureBundleV1`` from the same physical rows and
   raw transcript lineage;
2. verified confidence-row projections at the 2,048 validation checkpoint;
3. the standard direct/quotient model pair and row-bound-OTHER collapse proof;
4. the independent model-pair attestation;
5. one exact-lazy quotient solve plus its independent proof replay.

The terminal status is mechanically copied from the verified planner audit.
This module is development-only and nonconfirmatory.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from .phase3e_ids import canonical_json_bytes, parse_content_id
from . import partial_support_confidence_v2 as confidence
from . import partial_support_robust_planner_v1 as robust
from . import transfer_guided_acquisition_preregistration_v1 as prereg
from . import target_preauthorization_selector_v2 as selector
from . import v072_cold_h2_closure_v1 as closure
from . import v072_cold_h2_model_builders_v1 as models
from . import (
    v072_cold_h2_model_builders_independent_verifier_v1
    as model_independent,
)
from . import v072_exact_lazy_planner_component_v1 as planner_component
from . import v072_confidence_row_projection_v1 as confidence_projection
from . import (
    v072_confidence_row_projection_independent_verifier_v1
    as confidence_projection_independent,
)
from . import v072_incremental_materializer_v1 as materializer
from . import (
    v072_incremental_materializer_independent_verifier_v1
    as materializer_independent,
)
from . import v072_target_selector_component_v1 as selector_component


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_incremental_postbuild_bridge_v1"
CHECKPOINT_DRAWS = 2_048


class V072IncrementalPostbuildBridgeInvariantViolation(ValueError):
    """A handoff, row lineage, model, or verified audit is inconsistent."""


class PostbuildStatusV1(str):
    pass


DOMAIN_TAGS = {
    "topology": "acfqp:v072-incremental-postbuild-topology:v1",
    "action": "acfqp:v072-incremental-postbuild-public-action:v1",
    "descriptor": "acfqp:v072-incremental-postbuild-descriptor:v1",
    "transcript": "acfqp:v072-incremental-postbuild-transcript-binding:v1",
    "prefix": "acfqp:v072-incremental-postbuild-validation-prefix:v1",
    "physical": "acfqp:v072-incremental-postbuild-physical-evidence:v1",
    "support_epoch": "acfqp:v072-incremental-postbuild-support-epoch:v1",
    "confidence": "acfqp:v072-incremental-postbuild-confidence:v1",
    "replay": "acfqp:v072-incremental-postbuild-row-replay:v1",
    "projection": "acfqp:v072-incremental-postbuild-projection:v1",
    "projection_verification": (
        "acfqp:v072-incremental-postbuild-projection-verification:v1"
    ),
    "lineage": "acfqp:v072-incremental-postbuild-row-lineage:v1",
    "selected_policy": (
        "acfqp:v072-incremental-postbuild-selected-policy:v1"
    ),
    "result": "acfqp:v072-incremental-postbuild-result:v1",
    "support_chain": (
        "acfqp:v072-incremental-postbuild-support-chain:v1"
    ),
    "unknown_descriptor": (
        "acfqp:v072-incremental-postbuild-unknown-descriptor:v1"
    ),
    "selected_plan": (
        "acfqp:v072-incremental-postbuild-selected-plan:v1"
    ),
    "confidence_authority": (
        "acfqp:v072-incremental-postbuild-confidence-row-authority:v1"
    ),
    "round_two_preparation": (
        "acfqp:v072-development-round-two-preparation:v1"
    ),
}


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V072IncrementalPostbuildBridgeInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072IncrementalPostbuildBridgeInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _cold_state(
    value: materializer.DevelopmentPublicStateV1,
    *,
    topology_id: str,
) -> closure.ColdPublicStateV1:
    return closure.ColdPublicStateV1(
        value.state_id,
        {
            "schema": (
                "acfqp.v072_incremental_postbuild_public_state.v1"
            ),
            "context_id": value.context_id,
            "topology_id": topology_id,
            "ranks": list(value.ranks),
            "failure": False,
            "registered_target": False,
        },
    )


def _cold_action(
    row: materializer.DevelopmentPhysicalRowV1,
    *,
    topology_id: str,
) -> closure.ColdPublicActionV1:
    semantic_id = _content_id(
        "action",
        {
            "schema": (
                "acfqp.v072_incremental_postbuild_public_action.v1"
            ),
            "context_id": row.context_id,
            "state_id": row.state.state_id,
            "remaining_horizon": row.remaining_horizon,
            "action": list(row.action),
        },
    )
    return closure.ColdPublicActionV1(
        semantic_id,
        {
            "schema": (
                "acfqp.v072_incremental_postbuild_public_action.v1"
            ),
            "context_id": row.context_id,
            "topology_id": topology_id,
            "action": list(row.action),
            "registered_target": False,
        },
    )


def _descriptor(
    *,
    context_id: str,
    label: str,
    successor: closure.ColdPublicStateV1 | None,
) -> closure.ColdOutcomeDescriptorV1:
    semantic_id = _content_id(
        "descriptor",
        {
            "schema": "acfqp.v072_incremental_postbuild_descriptor.v1",
            "context_id": context_id,
            "label": label,
            "successor_state_id": (
                None if successor is None else successor.semantic_state_id
            ),
            "terminal": successor is None,
        },
    )
    return closure.ColdOutcomeDescriptorV1(
        semantic_id,
        failure=False,
        terminal=successor is None,
        successor_state=successor,
        document={
            "schema": (
                "acfqp.v072_incremental_postbuild_outcome_document.v1"
            ),
            "context_id": context_id,
            "semantic_role": label,
            "registered_target": False,
        },
    )


class _DevelopmentColdPublicGraph:
    def __init__(
        self,
        *,
        context_id: str,
        root_state: closure.ColdPublicStateV1,
        actions_by_state: Mapping[
            str, tuple[closure.ColdPublicActionV1, ...]
        ],
        states_by_id: Mapping[str, closure.ColdPublicStateV1],
    ) -> None:
        self.context_id = context_id
        self.horizon = 2
        self._root_state = root_state
        self._actions_by_state = dict(actions_by_state)
        self._states_by_id = dict(states_by_id)

    def root_state_v1(self) -> closure.ColdPublicStateV1:
        return self._root_state

    def canonical_state_v1(
        self,
        state: closure.ColdPublicStateV1,
    ) -> closure.ColdPublicStateV1:
        try:
            return self._states_by_id[state.semantic_state_id]
        except KeyError as error:
            raise V072IncrementalPostbuildBridgeInvariantViolation(
                "cold graph received an unregistered development state"
            ) from error

    def legal_actions_v1(
        self,
        state: closure.ColdPublicStateV1,
        remaining_horizon: int,
    ) -> tuple[closure.ColdPublicActionV1, ...]:
        canonical = self.canonical_state_v1(state)
        expected = (
            2
            if canonical.semantic_state_id
            == self._root_state.semantic_state_id
            else 1
        )
        if remaining_horizon != expected:
            raise V072IncrementalPostbuildBridgeInvariantViolation(
                "cold graph horizon is inconsistent"
            )
        return self._actions_by_state[canonical.semantic_state_id]


def _hash_word(
    *,
    seed_id: str,
    lane: str,
    law_key: str,
    index: int,
) -> int:
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
            return (value & ~3) | (index & 1)
        return value & ~3
    if lane != "PARENT_FRESH_VALIDATION":
        return value & ~3
    return value


def _prefix_counts(
    *,
    seed_id: str,
    lane: str,
    law_key: str,
    draws: int = CHECKPOINT_DRAWS,
) -> tuple[int, int, int, int]:
    counts = [0, 0, 0, 0]
    for index in range(draws):
        counts[
            _hash_word(
                seed_id=seed_id,
                lane=lane,
                law_key=law_key,
                index=index,
            )
            & 3
        ] += 1
    return tuple(counts)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class HandoffRowProjectionLineageV1:
    semantic_physical_row_id: str
    cold_row_evidence_id: str
    cold_physical_evidence_id: str
    discovery_transcript_id: str
    validation_transcript_id: str
    validation_prefix_id: str
    projection_binding_id: str
    source_stream_ids: tuple[str, ...]
    selected_checkpoint_draw_count: int

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.semantic_physical_row_id, "semantic physical row"),
            (self.cold_row_evidence_id, "cold row evidence"),
            (self.cold_physical_evidence_id, "cold physical evidence"),
            (self.discovery_transcript_id, "discovery transcript"),
            (self.validation_transcript_id, "validation transcript"),
            (self.validation_prefix_id, "validation prefix"),
            (self.projection_binding_id, "projection binding"),
        ):
            _cid(value, field_name)
        if (
            type(self.source_stream_ids) is not tuple
            or not self.source_stream_ids
            or self.source_stream_ids
            != tuple(sorted(set(self.source_stream_ids)))
            or self.selected_checkpoint_draw_count
            not in (CHECKPOINT_DRAWS, materializer.CHILD_VALIDATION_DRAWS)
        ):
            raise V072IncrementalPostbuildBridgeInvariantViolation(
                "row projection lineage is incomplete"
            )
        for item in self.source_stream_ids:
            _cid(item, "row source stream")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_incremental_postbuild_row_lineage.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "semantic_physical_row_id": self.semantic_physical_row_id,
            "cold_row_evidence_id": self.cold_row_evidence_id,
            "cold_physical_evidence_id":
                self.cold_physical_evidence_id,
            "discovery_transcript_id": self.discovery_transcript_id,
            "validation_transcript_id": self.validation_transcript_id,
            "validation_prefix_id": self.validation_prefix_id,
            "projection_binding_id": self.projection_binding_id,
            "source_stream_ids": list(self.source_stream_ids),
            "selected_checkpoint_draw_count":
                self.selected_checkpoint_draw_count,
            "same_handoff_physical_lineage": True,
        }

    @property
    def lineage_id(self) -> str:
        return _content_id("lineage", self._payload())


@dataclass(frozen=True, slots=True)
class _RawSource:
    stream_id: str
    draw_count: int
    range_proof_id: str
    current_stream: (
        materializer.DevelopmentRawObservationStreamV1 | None
    ) = None
    upstream_transcript: (
        materializer.DevelopmentUpstreamRowTranscriptV1 | None
    ) = None
    upstream_lane: materializer.UpstreamAcquisitionLaneV1 | None = None

    def __post_init__(self) -> None:
        for value in (self.stream_id, self.range_proof_id):
            _cid(value, "raw source identity")
        if (
            type(self.draw_count) is not int
            or self.draw_count <= 0
            or (self.current_stream is not None)
            == (self.upstream_transcript is not None)
            or (
                self.upstream_transcript is not None
                and type(self.upstream_lane)
                is not materializer.UpstreamAcquisitionLaneV1
            )
            or (
                self.current_stream is not None
                and self.upstream_lane is not None
            )
        ):
            raise V072IncrementalPostbuildBridgeInvariantViolation(
                "raw source lineage is malformed"
            )

    def word(self, index: int) -> int:
        if self.current_stream is not None:
            return materializer.raw_word_u64_v1(
                self.current_stream,
                index,
            )
        assert self.upstream_transcript is not None
        assert self.upstream_lane is not None
        return materializer.upstream_raw_word_u64_v1(
            self.upstream_transcript,
            self.upstream_lane,
            index,
        )

    def commitment_id(self, index: int) -> str:
        if self.current_stream is not None:
            return materializer.raw_commitment_id_v1(
                self.current_stream,
                index,
            )
        assert self.upstream_transcript is not None
        assert self.upstream_lane is not None
        return materializer.upstream_raw_commitment_id_v1(
            self.upstream_transcript,
            self.upstream_lane,
            index,
        )


@dataclass(frozen=True, slots=True)
class _RowBuildInput:
    semantic_row: materializer.DevelopmentPhysicalRowV1
    cold_state: closure.ColdPublicStateV1
    cold_action: closure.ColdPublicActionV1
    descriptors: tuple[closure.ColdOutcomeDescriptorV1, ...]
    discovery_source: _RawSource
    validation_source: _RawSource
    source_stream_ids: tuple[str, ...]
    validation_counts: tuple[int, int, int, int]
    parent_two_supports: bool
    selected_checkpoint_draw_count: int


def _transcript_id(
    *,
    role: str,
    semantic_row_id: str,
    source_id: str,
    raw_digest: str,
    draws: int,
) -> str:
    return _content_id(
        "transcript",
        {
            "schema": (
                "acfqp.v072_incremental_postbuild_transcript_binding.v1"
            ),
            "role": role,
            "semantic_physical_row_id": semantic_row_id,
            "source_id": source_id,
            "raw_digest": raw_digest,
            "draws": draws,
        },
    )


def _build_standard_inputs(
    handoff: materializer.IncrementalModelRebuildHandoffV1,
    prior_handoff: (
        materializer.IncrementalModelRebuildHandoffV1 | None
    ) = None,
) -> tuple[
    _DevelopmentColdPublicGraph,
    tuple[_RowBuildInput, ...],
    str,
]:
    request = handoff.request
    context = materializer.development_public_context_v1()
    if (
        type(handoff)
        is not materializer.IncrementalModelRebuildHandoffV1
        or handoff.status != materializer.PENDING_STATUS
        or request.parent_epoch.context_id != context.context_id
        or request.parent_epoch.round_index not in (1, 2)
        or (
            request.parent_epoch.round_index == 1
            and prior_handoff is not None
        )
        or (
            request.parent_epoch.round_index == 2
            and (
                type(prior_handoff)
                is not materializer.IncrementalModelRebuildHandoffV1
                or request.previous_handoff_id != prior_handoff.handoff_id
                or prior_handoff.request.parent_epoch.round_index != 1
                or prior_handoff.law_key is not handoff.law_key
                or (
                    prior_handoff.request.parent_epoch
                    .logical_occurrence_id
                )
                != request.parent_epoch.logical_occurrence_id
            )
        )
        or tuple(
            sorted(
                {
                    *request.current_closure.physical_row_ids,
                    *(
                        item.physical_row.physical_row_id
                        for item in handoff.child_rows
                    ),
                }
            )
        )
        != handoff.resulting_physical_row_ids
    ):
        raise V072IncrementalPostbuildBridgeInvariantViolation(
            "postbuild input is not one exact incremental handoff chain"
        )
    topology_id = _content_id(
        "topology",
        {
            "schema": "acfqp.v072_incremental_postbuild_topology.v1",
            "context_id": context.context_id,
            "vertex_count": context.vertex_count,
            "edges": [list(edge) for edge in context.edges],
            "rank_cap": context.rank_cap,
        },
    )
    semantic_rows = tuple(
        sorted(
            {
                value.physical_row_id: value
                for value in (
                    *request.current_closure.rows,
                    *(
                        item.physical_row
                        for item in handoff.child_rows
                    ),
                )
            }.values(),
            key=lambda value: value.physical_row_id,
        )
    )
    root_rows = tuple(
        value
        for value in request.current_closure.rows
        if value.remaining_horizon == 2
    )
    if (
        len(root_rows) != 2
        or any(item.remaining_horizon != 2 for item in root_rows)
    ):
        raise V072IncrementalPostbuildBridgeInvariantViolation(
            "parent closure is not one complete P4 root catalogue"
        )
    cold_state_by_semantic: dict[str, closure.ColdPublicStateV1] = {}
    for row in semantic_rows:
        cold_state_by_semantic.setdefault(
            row.state.state_id,
            _cold_state(row.state, topology_id=topology_id),
        )
    promoted_novel_state = materializer.DevelopmentPublicStateV1(
        context.context_id,
        (1, 1, 3, 4),
    )
    cold_state_by_semantic.setdefault(
        promoted_novel_state.state_id,
        _cold_state(promoted_novel_state, topology_id=topology_id),
    )
    root_state = cold_state_by_semantic[root_rows[0].state.state_id]
    child_states = tuple(
        sorted(
            {
                cold_state_by_semantic[item.state.state_id].state_record_id:
                cold_state_by_semantic[item.state.state_id]
                for item in semantic_rows
                if item.remaining_horizon == 1
            }.values(),
            key=lambda value: value.state_record_id,
        )
    )
    expected_child_state_count = (
        2 if request.parent_epoch.round_index == 1 else 3
    )
    if len(child_states) != expected_child_state_count:
        raise V072IncrementalPostbuildBridgeInvariantViolation(
            "development closure has the wrong cumulative child-state count"
        )
    child_descriptors = tuple(
        sorted(
            (
                _descriptor(
                    context_id=context.context_id,
                    label=f"PROMOTED_CHILD_{index}",
                    successor=state,
                )
                for index, state in enumerate(child_states)
            ),
            key=lambda item: item.descriptor_record_id,
        )
    )
    terminal_by_row = {
        item.physical_row.physical_row_id: _descriptor(
            context_id=context.context_id,
            label=f"TERMINAL_CHILD_{item.physical_row.physical_row_id}",
            successor=None,
        )
        for item in (
            *(
                ()
                if prior_handoff is None
                else prior_handoff.child_rows
            ),
            *handoff.child_rows,
        )
    }
    actions_by_state: dict[
        str, tuple[closure.ColdPublicActionV1, ...]
    ] = {}
    for state_id in cold_state_by_semantic:
        rows = tuple(
            row
            for row in semantic_rows
            if row.state.state_id == state_id
        )
        actions_by_state[state_id] = tuple(
            sorted(
                (
                    _cold_action(row, topology_id=topology_id)
                    for row in rows
                ),
                key=lambda item: item.action_record_id,
            )
        )
    graph = _DevelopmentColdPublicGraph(
        context_id=context.context_id,
        root_state=root_state,
        actions_by_state=actions_by_state,
        states_by_id=cold_state_by_semantic,
    )
    upstream_by_row = {
        item.physical_row.physical_row_id: item
        for item in request.parent_evidence.upstream_root_rows
    }
    child_by_row = {
        item.physical_row.physical_row_id: item
        for item in (
            *(
                ()
                if prior_handoff is None
                else prior_handoff.child_rows
            ),
            *handoff.child_rows,
        )
    }
    suffix_range_by_stream = {
        item.stream_id: item
        for source_handoff in (
            *(() if prior_handoff is None else (prior_handoff,)),
            handoff,
        )
        for item in source_handoff.raw_commitment_ranges
    }
    rows: list[_RowBuildInput] = []
    for semantic_row in semantic_rows:
        row_id = semantic_row.physical_row_id
        cold_state = cold_state_by_semantic[semantic_row.state.state_id]
        cold_action = next(
            item
            for item in actions_by_state[semantic_row.state.state_id]
            if list(item.document["action"]) == list(semantic_row.action)
        )
        if row_id in upstream_by_row:
            upstream = upstream_by_row[row_id]
            discovery_source = _RawSource(
                upstream.discovery_stream_id,
                upstream.discovery_draws,
                upstream.discovery_raw_commitment_range.range_proof_id,
                upstream_transcript=upstream,
                upstream_lane=(
                    materializer.UpstreamAcquisitionLaneV1.DISCOVERY
                ),
            )
            if (
                row_id
                == request.parent_evidence.parent_physical_row_id
            ):
                validation = handoff.parent_validation_stream
                validation_source = _RawSource(
                    validation.stream_id,
                    validation.draw_count,
                    suffix_range_by_stream[
                        validation.stream_id
                    ].range_proof_id,
                    current_stream=validation,
                )
                counts = validation.outcome_bucket_counts
                source_ids = tuple(
                    sorted(
                        (
                            upstream.discovery_stream_id,
                            validation.stream_id,
                        )
                    )
                )
                descriptors = child_descriptors
                parent_two = True
            else:
                validation_source = _RawSource(
                    upstream.validation_stream_id,
                    upstream.validation_draws,
                    (
                        upstream.validation_raw_commitment_range
                        .range_proof_id
                    ),
                    upstream_transcript=upstream,
                    upstream_lane=(
                        materializer.UpstreamAcquisitionLaneV1.VALIDATION
                    ),
                )
                counts = upstream.validation_bucket_counts
                source_ids = tuple(
                    sorted(
                        (
                            upstream.discovery_stream_id,
                            upstream.validation_stream_id,
                        )
                    )
                )
                descriptors = child_descriptors
                parent_two = True
            selected_checkpoint = CHECKPOINT_DRAWS
        else:
            child = child_by_row[row_id]
            discovery_source = _RawSource(
                child.discovery_stream.stream_id,
                child.discovery_stream.draw_count,
                suffix_range_by_stream[
                    child.discovery_stream.stream_id
                ].range_proof_id,
                current_stream=child.discovery_stream,
            )
            validation_source = _RawSource(
                child.validation_stream.stream_id,
                child.validation_stream.draw_count,
                suffix_range_by_stream[
                    child.validation_stream.stream_id
                ].range_proof_id,
                current_stream=child.validation_stream,
            )
            counts = child.validation_stream.outcome_bucket_counts
            source_ids = tuple(
                sorted(
                    (
                        child.discovery_stream.stream_id,
                        child.validation_stream.stream_id,
                    )
                )
            )
            descriptors = (terminal_by_row[row_id],)
            parent_two = False
            selected_checkpoint = materializer.CHILD_VALIDATION_DRAWS
        rows.append(
            _RowBuildInput(
                semantic_row,
                cold_state,
                cold_action,
                tuple(
                    sorted(
                        descriptors,
                        key=lambda item: item.descriptor_record_id,
                    )
                ),
                discovery_source,
                validation_source,
                source_ids,
                counts,
                parent_two,
                selected_checkpoint,
            )
        )
    return graph, tuple(rows), topology_id


def _exact_row_reward(
    row: materializer.DevelopmentPhysicalRowV1,
) -> Fraction:
    merge_rank = row.state.ranks[row.action[0]]
    return Fraction(2 ** (merge_rank + 1), 2 ** 5) / 2


def _terminal_ranks(
    row: materializer.DevelopmentPhysicalRowV1,
) -> tuple[int, ...]:
    ranks = list(row.state.ranks)
    left, right, survivor = row.action
    loser = right if survivor == left else left
    ranks[loser] = 0
    ranks[survivor] = min(ranks[survivor] + 1, 4)
    return tuple(ranks)


def _confidence_descriptor(
    *,
    row: materializer.DevelopmentPhysicalRowV1,
    cold_descriptor: closure.ColdOutcomeDescriptorV1,
) -> confidence.OpaqueOutcomeDescriptorV2:
    ranks = (
        tuple(cold_descriptor.successor_state.document["ranks"])
        if cold_descriptor.successor_state is not None
        else _terminal_ranks(row)
    )
    document = {
        "schema": (
            "acfqp.v072_incremental_postbuild_outcome_semantics.v1"
        ),
        "descriptor_id": cold_descriptor.semantic_descriptor_id,
        "next_state": {
            "ranks": list(ranks),
            "failure": cold_descriptor.failure,
        },
        "failure": cold_descriptor.failure,
        "terminal": cold_descriptor.terminal,
        "realized_row_reward": _exact_row_reward(row),
        "registered_target": False,
    }
    return confidence.OpaqueOutcomeDescriptorV2(
        cold_descriptor.semantic_descriptor_id,
        document,
    )


def _unknown_confidence_descriptor(
    *,
    row: materializer.DevelopmentPhysicalRowV1,
    bucket: int,
) -> confidence.OpaqueOutcomeDescriptorV2:
    descriptor_id = _content_id(
        "unknown_descriptor",
        {
            "schema": (
                "acfqp.v072_incremental_postbuild_unknown_descriptor.v1"
            ),
            "semantic_physical_row_id": row.physical_row_id,
            "bucket": bucket,
            "successor_ranks": [1, 1, 3, 4],
            "failure": False,
            "terminal": False,
            "realized_row_reward": _fdoc(_exact_row_reward(row)),
        },
    )
    return confidence.OpaqueOutcomeDescriptorV2(
        descriptor_id,
        {
            "schema": (
                "acfqp.v072_incremental_postbuild_outcome_semantics.v1"
            ),
            "descriptor_id": descriptor_id,
            "next_state": {
                # Buckets 2 and 3 are distinct public outcome descriptors but
                # share one concrete newly reachable state.  Its two legal
                # actions are therefore deduplicated to two physical child
                # rows by the evidence-first cardinality authority.
                "ranks": [1, 1, 3, 4],
                "failure": False,
            },
            "failure": False,
            "terminal": False,
            "realized_row_reward": _exact_row_reward(row),
            "raw_bucket": bucket,
            "registered_target": False,
        },
    )


def _cold_descriptor_from_confidence(
    descriptor: confidence.OpaqueOutcomeDescriptorV2,
    *,
    successor_by_ranks: Mapping[
        tuple[int, ...], closure.ColdPublicStateV1
    ],
) -> closure.ColdOutcomeDescriptorV1:
    document = descriptor.document
    next_state = document["next_state"]
    failure = bool(document["failure"])
    terminal = bool(document["terminal"])
    successor = (
        None
        if failure or terminal
        else successor_by_ranks[tuple(next_state["ranks"])]
    )
    return closure.ColdOutcomeDescriptorV1(
        descriptor.descriptor_id,
        failure=failure,
        terminal=terminal,
        successor_state=successor,
        document=document,
    )


def _confidence_observations(
    *,
    handoff: materializer.IncrementalModelRebuildHandoffV1,
    row: materializer.DevelopmentPhysicalRowV1,
    source: _RawSource,
    lane: confidence.ConfidenceObservationLaneV2,
    support_epoch_chain_id: str,
    known_by_bucket: Mapping[
        int, confidence.OpaqueOutcomeDescriptorV2
    ],
    include_unknown: bool,
) -> tuple[confidence.OpaqueConfidenceObservationV2, ...]:
    unknown = {
        bucket: _unknown_confidence_descriptor(
            row=row,
            bucket=bucket,
        )
        for bucket in range(4)
        if bucket not in known_by_bucket
    }
    output = []
    for index in range(source.draw_count):
        bucket = source.word(index) & 3
        if bucket in known_by_bucket:
            descriptor = known_by_bucket[bucket]
        elif include_unknown:
            descriptor = unknown[bucket]
        else:
            raise V072IncrementalPostbuildBridgeInvariantViolation(
                "known-support lane emitted an unregistered raw bucket"
            )
        output.append(
            confidence.OpaqueConfidenceObservationV2(
                prereg.DRAFT_PREREGISTRATION_ID,
                row.context_id,
                handoff.request.parent_epoch.arm,
                row.physical_row_id,
                support_epoch_chain_id,
                source.stream_id,
                lane,
                index + 1,
                source.commitment_id(index),
                descriptor,
            )
        )
    return tuple(output)


@dataclass(frozen=True, slots=True)
class ProductionConfidenceRowAuthorityV1:
    row_binding: confidence.ConfidencePhysicalRowBindingV2
    support_epoch: (
        confidence.InitialSupportEpochV2
        | confidence.PromotedSupportEpochV2
    )
    snapshot: confidence.PartialSupportConfidenceSnapshotV2
    confidence_verification: (
        confidence.PartialSupportConfidenceVerificationV2
    )
    source_projection: (
        confidence_projection.ConfidenceIntervalSimplexRowProjectionV1
    )
    projection_verification: (
        confidence_projection_independent
        .V072ConfidenceRowProjectionVerificationV1
    )
    discovery_transcript_id: str
    validation_transcript_id: str
    row_replay_verification_id: str
    support_descriptors: tuple[closure.ColdOutcomeDescriptorV1, ...]
    validation_novel: tuple[closure.ColdOutcomeDescriptorV1, ...]
    bucket_descriptor_ids: tuple[tuple[int, str], ...]
    promotion_parent_snapshot: (
        confidence.PartialSupportConfidenceSnapshotV2 | None
    ) = None

    @property
    def authority_id(self) -> str:
        return _content_id(
            "confidence_authority",
            {
                "schema": (
                    "acfqp.v072_incremental_postbuild_"
                    "confidence_row_authority.v1"
                ),
                "row_binding_id": self.row_binding.row_binding_id,
                "support_epoch_id": self.support_epoch.support_epoch_id,
                "confidence_snapshot_id": self.snapshot.snapshot_id,
                "confidence_verification_id":
                    self.confidence_verification.verification_id,
                "source_projection_id":
                    self.source_projection.projection_id,
                "projection_verification_id":
                    self.projection_verification.verification_id,
                "discovery_transcript_id":
                    self.discovery_transcript_id,
                "validation_transcript_id":
                    self.validation_transcript_id,
                "row_replay_verification_id":
                    self.row_replay_verification_id,
                "support_descriptor_record_ids": [
                    value.descriptor_record_id
                    for value in self.support_descriptors
                ],
                "validation_novel_descriptor_record_ids": [
                    value.descriptor_record_id
                    for value in self.validation_novel
                ],
                "bucket_descriptor_ids": [
                    [bucket, descriptor_id]
                    for bucket, descriptor_id
                    in self.bucket_descriptor_ids
                ],
                "promotion_parent_snapshot_id": (
                    None
                    if self.promotion_parent_snapshot is None
                    else self.promotion_parent_snapshot.snapshot_id
                ),
            },
        )


def _build_production_confidence(
    *,
    handoff: materializer.IncrementalModelRebuildHandoffV1,
    item: _RowBuildInput,
    physical_evidence_id: str,
    successor_by_ranks: Mapping[
        tuple[int, ...], closure.ColdPublicStateV1
    ],
    prior_authority: ProductionConfidenceRowAuthorityV1 | None = None,
) -> ProductionConfidenceRowAuthorityV1:
    row = item.semantic_row
    binding = confidence.ConfidencePhysicalRowBindingV2(
        prereg.DRAFT_PREREGISTRATION_ID,
        row.context_id,
        handoff.request.parent_epoch.arm,
        row.physical_row_id,
    )
    initially_known = tuple(
        _confidence_descriptor(row=row, cold_descriptor=value)
        for value in item.descriptors
    )
    discovery_chain = _content_id(
        "support_chain",
        {
            "schema": (
                "acfqp.v072_incremental_postbuild_support_chain.v1"
            ),
            "physical_evidence_id": physical_evidence_id,
            "lane": "DISCOVERY",
            "stream_id": item.discovery_source.stream_id,
        },
    )
    validation_chain = _content_id(
        "support_chain",
        {
            "schema": (
                "acfqp.v072_incremental_postbuild_support_chain.v1"
            ),
            "physical_evidence_id": physical_evidence_id,
            "lane": "VALIDATION",
            "stream_id": item.validation_source.stream_id,
        },
    )
    is_promoted_parent = (
        row.physical_row_id
        == handoff.request.parent_evidence.parent_physical_row_id
    )
    promotion_parent_snapshot = None
    if (
        prior_authority is None
        and is_promoted_parent
        and handoff.request.parent_epoch.round_index == 1
    ):
        old_support_ids = (
            handoff.request.parent_evidence.old_support_descriptor_ids
        )
        if len(old_support_ids) != 1:
            raise V072IncrementalPostbuildBridgeInvariantViolation(
                "round-one promoted parent requires one frozen old support"
            )
        by_successor = {
            tuple(value.document["next_state"]["ranks"]): value
            for value in initially_known
        }
        bucket_one_observation = next(
            value
            for value in (
                handoff.request.parent_evidence
                .upstream_novel_observations
            )
            if value.bucket == 1
        )
        bucket_one_cold = next(
            value
            for value in item.descriptors
            if (
                value.successor_state is not None
                and tuple(value.successor_state.document["ranks"])
                == bucket_one_observation.successor_state.ranks
            )
        )
        old_cold = closure.ColdOutcomeDescriptorV1(
            old_support_ids[0],
            failure=False,
            terminal=False,
            successor_state=bucket_one_cold.successor_state,
            document={
                "schema": (
                    "acfqp.v072_incremental_postbuild_old_support.v1"
                ),
                "semantic_role": (
                    "OLD_ACTIVE_DESCRIPTOR_SHARED_SUCCESSOR_WITH_BUCKET_1"
                ),
            },
        )
        old_descriptor = _confidence_descriptor(
            row=row,
            cold_descriptor=old_cold,
        )
        known_by_bucket = {0: old_descriptor}
        for observation in (
            handoff.request.parent_evidence
            .upstream_novel_observations
        ):
            known_by_bucket[observation.bucket] = by_successor[
                observation.successor_state.ranks
            ]
        if set(known_by_bucket) != {0, 1, 2}:
            raise V072IncrementalPostbuildBridgeInvariantViolation(
                "upstream novelty does not bind buckets 1/2"
            )
        upstream = next(
            value
            for value in (
                handoff.request.parent_evidence.upstream_root_rows
            )
            if value.physical_row.physical_row_id
            == row.physical_row_id
        )
        prior_validation_source = _RawSource(
            upstream.validation_stream_id,
            upstream.validation_draws,
            upstream.validation_raw_commitment_range.range_proof_id,
            upstream_transcript=upstream,
            upstream_lane=(
                materializer.UpstreamAcquisitionLaneV1.VALIDATION
            ),
        )
        prior_discovery_chain = _content_id(
            "support_chain",
            {
                "schema": (
                    "acfqp.v072_incremental_postbuild_support_chain.v1"
                ),
                "physical_evidence_id": physical_evidence_id,
                "lane": "UPSTREAM_DISCOVERY",
                "stream_id": item.discovery_source.stream_id,
            },
        )
        prior_validation_chain = _content_id(
            "support_chain",
            {
                "schema": (
                    "acfqp.v072_incremental_postbuild_support_chain.v1"
                ),
                "physical_evidence_id": physical_evidence_id,
                "lane": "UPSTREAM_VALIDATION",
                "stream_id": prior_validation_source.stream_id,
            },
        )
        prior_discovery = _confidence_observations(
            handoff=handoff,
            row=row,
            source=item.discovery_source,
            lane=confidence.ConfidenceObservationLaneV2.DISCOVERY,
            support_epoch_chain_id=prior_discovery_chain,
            known_by_bucket={0: old_descriptor},
            include_unknown=False,
        )
        prior_epoch = confidence.freeze_initial_support_epoch_v2(
            row_binding=binding,
            purpose=(
                confidence.ConfidenceEpochPurposeV2
                .INITIAL_SHARED_OR_DIRECT
            ),
            discovery_support_epoch_chain_id=prior_discovery_chain,
            discovery_stream_id=item.discovery_source.stream_id,
            discovery_observations=prior_discovery,
            validation_support_epoch_chain_id=prior_validation_chain,
            validation_stream_id=prior_validation_source.stream_id,
        )
        prior_validation = _confidence_observations(
            handoff=handoff,
            row=row,
            source=prior_validation_source,
            lane=confidence.ConfidenceObservationLaneV2.VALIDATION,
            support_epoch_chain_id=prior_validation_chain,
            known_by_bucket=known_by_bucket,
            include_unknown=False,
        )
        promotion_parent_snapshot = (
            confidence.build_partial_support_confidence_snapshot_v2(
                prior_epoch,
                prior_validation,
                confidence.v0072_partial_support_confidence_profile_v2(),
            )
        )
        confidence.verify_partial_support_confidence_snapshot_v2(
            promotion_parent_snapshot
        )
        if {
            value.descriptor_id
            for value in promotion_parent_snapshot.novel_descriptors
        } != {
            known_by_bucket[1].descriptor_id,
            known_by_bucket[2].descriptor_id,
        }:
            raise V072IncrementalPostbuildBridgeInvariantViolation(
                "upstream validation did not produce the two promoted descriptors"
            )
        epoch = confidence.promote_support_epoch_v2(
            promotion_parent_snapshot,
            next_support_epoch_chain_id=validation_chain,
            next_validation_stream_id=item.validation_source.stream_id,
        )
        discovery = prior_discovery
        discovery_transcript_id = item.discovery_source.stream_id
    elif prior_authority is None:
        known_by_bucket = {
            index: value
            for index, value in enumerate(initially_known)
        }
        discovery = _confidence_observations(
            handoff=handoff,
            row=row,
            source=item.discovery_source,
            lane=confidence.ConfidenceObservationLaneV2.DISCOVERY,
            support_epoch_chain_id=discovery_chain,
            known_by_bucket=known_by_bucket,
            include_unknown=False,
        )
        purpose = (
            confidence.ConfidenceEpochPurposeV2.INITIAL_SHARED_OR_DIRECT
            if row.remaining_horizon == 2
            else confidence.ConfidenceEpochPurposeV2.NEW_CHILD
        )
        epoch = confidence.freeze_initial_support_epoch_v2(
            row_binding=binding,
            purpose=purpose,
            discovery_support_epoch_chain_id=discovery_chain,
            discovery_stream_id=item.discovery_source.stream_id,
            discovery_observations=discovery,
            validation_support_epoch_chain_id=validation_chain,
            validation_stream_id=item.validation_source.stream_id,
        )
        discovery_transcript_id = item.discovery_source.stream_id
    else:
        if (
            row.remaining_horizon != 2
            or prior_authority.support_epoch.row_binding != binding
            or not prior_authority.snapshot.novel_descriptors
        ):
            raise V072IncrementalPostbuildBridgeInvariantViolation(
                "round-two promotion lacks the exact failed parent snapshot"
            )
        epoch = confidence.promote_support_epoch_v2(
            prior_authority.snapshot,
            next_support_epoch_chain_id=validation_chain,
            next_validation_stream_id=item.validation_source.stream_id,
        )
        by_id = {
            value.descriptor_id: value
            for value in epoch.support_descriptors
        }
        known_by_bucket = {
            bucket: by_id[descriptor_id]
            for bucket, descriptor_id
            in prior_authority.bucket_descriptor_ids
        }
        for value in prior_authority.snapshot.novel_descriptors:
            bucket = value.document.get("raw_bucket")
            if type(bucket) is not int or bucket not in range(4):
                raise V072IncrementalPostbuildBridgeInvariantViolation(
                    "round-two promoted novelty lacks raw bucket semantics"
                )
            known_by_bucket[bucket] = by_id[value.descriptor_id]
        if {
            value.descriptor_id for value in known_by_bucket.values()
        } != {
            value.descriptor_id for value in epoch.support_descriptors
        }:
            raise V072IncrementalPostbuildBridgeInvariantViolation(
                "round-two bucket map differs from promoted support"
            )
        discovery = ()
        discovery_transcript_id = (
            prior_authority.discovery_transcript_id
        )
        promotion_parent_snapshot = prior_authority.snapshot
    validation = _confidence_observations(
        handoff=handoff,
        row=row,
        source=item.validation_source,
        lane=confidence.ConfidenceObservationLaneV2.VALIDATION,
        support_epoch_chain_id=validation_chain,
        known_by_bucket=known_by_bucket,
        include_unknown=item.parent_two_supports,
    )
    if len(validation) != item.selected_checkpoint_draw_count:
        raise V072IncrementalPostbuildBridgeInvariantViolation(
            "confidence did not consume the full authorized validation stream"
        )
    snapshot = confidence.build_partial_support_confidence_snapshot_v2(
        epoch,
        validation,
        confidence.v0072_partial_support_confidence_profile_v2(),
    )
    confidence_verification = (
        confidence.verify_partial_support_confidence_snapshot_v2(snapshot)
    )
    public_binding = confidence_projection.PublicStateActionRowBindingV1(
        preregistration_id=prereg.DRAFT_PREREGISTRATION_ID,
        context_id=row.context_id,
        arm=handoff.request.parent_epoch.arm,
        physical_row_id=row.physical_row_id,
        confidence_row_binding_id=binding.row_binding_id,
        state_ranks=row.state.ranks,
        remaining_horizon=row.remaining_horizon,
        action=row.action,
    )
    source_projection = (
        confidence_projection
        .project_confidence_snapshot_to_interval_row_v1(
            snapshot,
            public_binding,
        )
    )
    projection_verification = (
        confidence_projection_independent
        .verify_v072_confidence_row_projection_v1(source_projection)
    )
    replay_id = _content_id(
        "replay",
        {
            "schema": (
                "acfqp.v072_incremental_postbuild_row_replay.v1"
            ),
            "physical_evidence_id": physical_evidence_id,
            "discovery_stream_id": discovery_transcript_id,
            "validation_stream_id": item.validation_source.stream_id,
            "discovery_raw_commitment_range_proof_id":
                item.discovery_source.range_proof_id,
            "validation_raw_commitment_range_proof_id":
                item.validation_source.range_proof_id,
            "discovery_observation_ids": [
                value.observation_id for value in discovery
            ],
            "parent_confidence_snapshot_id": (
                None
                if promotion_parent_snapshot is None
                else promotion_parent_snapshot.snapshot_id
            ),
            "promotion_evidence_id": (
                None
                if type(epoch) is confidence.InitialSupportEpochV2
                else epoch.promotion_evidence.evidence_id
            ),
            "validation_prefix_id":
                snapshot.validation_prefix.prefix_id,
            "confidence_verification_id":
                confidence_verification.verification_id,
            "projection_verification_id":
                projection_verification.verification_id,
            "raw_replay_verified": True,
        },
    )
    cold_support = tuple(
        sorted(
            (
                _cold_descriptor_from_confidence(
                    value,
                    successor_by_ranks=successor_by_ranks,
                )
                for value in epoch.support_descriptors
            ),
            key=lambda value: value.descriptor_record_id,
        )
    )
    cold_novel = tuple(
        sorted(
            (
                _cold_descriptor_from_confidence(
                    value,
                    successor_by_ranks=successor_by_ranks,
                )
                for value in snapshot.novel_descriptors
            ),
            key=lambda value: value.descriptor_record_id,
        )
    )
    return ProductionConfidenceRowAuthorityV1(
        binding,
        epoch,
        snapshot,
        confidence_verification,
        source_projection,
        projection_verification,
        discovery_transcript_id,
        item.validation_source.stream_id,
        replay_id,
        cold_support,
        cold_novel,
        tuple(
            sorted(
                (
                    (bucket, value.descriptor_id)
                    for bucket, value in known_by_bucket.items()
                ),
            )
        ),
        promotion_parent_snapshot,
    )


def _build_closure_and_projections(
    handoff: materializer.IncrementalModelRebuildHandoffV1,
    prior_handoff: (
        materializer.IncrementalModelRebuildHandoffV1 | None
    ) = None,
    prior_postbuild: "IncrementalPostbuildResultV1 | None" = None,
) -> tuple[
    closure.V072ColdH2ClosureBundleV1,
    tuple[models.VerifiedColdH2ConfidenceRowProjectionV1, ...],
    tuple[HandoffRowProjectionLineageV1, ...],
    tuple[ProductionConfidenceRowAuthorityV1, ...],
    models.ColdH2PublicRelationalContextV1,
]:
    if (
        handoff.request.parent_epoch.round_index == 1
        and (prior_handoff is not None or prior_postbuild is not None)
    ) or (
        handoff.request.parent_epoch.round_index == 2
        and (
            type(prior_handoff)
            is not materializer.IncrementalModelRebuildHandoffV1
            or type(prior_postbuild) is not IncrementalPostbuildResultV1
            or prior_postbuild.handoff_id != prior_handoff.handoff_id
            or prior_postbuild.audit_status
            is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
        )
    ):
        raise V072IncrementalPostbuildBridgeInvariantViolation(
            "postbuild lineage does not bind the required prior failed result"
        )
    graph, inputs, topology_id = _build_standard_inputs(
        handoff,
        prior_handoff,
    )
    cold_rows: list[closure.ColdRowEvidenceV1] = []
    input_by_semantic_key: dict[tuple[str, int, str], _RowBuildInput] = {}
    authority_by_semantic_key: dict[
        tuple[str, int, str], ProductionConfidenceRowAuthorityV1
    ] = {}
    successor_by_ranks = {
        tuple(value.document["ranks"]): value
        for value in graph._states_by_id.values()
    }
    prior_authority_by_row = (
        {}
        if prior_postbuild is None
        else {
            value.row_binding.physical_row_id: value
            for value in prior_postbuild.confidence_authorities
        }
    )
    for item in inputs:
        semantic_row_id = item.semantic_row.physical_row_id
        physical_id = _content_id(
            "physical",
            {
                "schema": (
                    "acfqp.v072_incremental_postbuild_physical_evidence.v1"
                ),
                "semantic_physical_row_id": semantic_row_id,
                "source_stream_ids": list(item.source_stream_ids),
                "discovery_raw_commitment_range_proof_id":
                    item.discovery_source.range_proof_id,
                "validation_raw_commitment_range_proof_id":
                    item.validation_source.range_proof_id,
                "selected_checkpoint_draw_count":
                    item.selected_checkpoint_draw_count,
            },
        )
        authority = _build_production_confidence(
            handoff=handoff,
            item=item,
            physical_evidence_id=physical_id,
            successor_by_ranks=successor_by_ranks,
            prior_authority=(
                prior_authority_by_row.get(semantic_row_id)
                if (
                    handoff.request.parent_epoch.round_index == 2
                    and semantic_row_id
                    == (
                        handoff.request.parent_evidence
                        .parent_physical_row_id
                    )
                )
                else None
            ),
        )
        if (
            item.validation_source.current_stream is not None
            and item.validation_source.current_stream.lane
            is materializer.AcquisitionLaneV1.PARENT_FRESH_VALIDATION
        ):
            native_work = closure.ColdRowNativeWorkV1(
                acquisition_purpose=(
                    closure.ColdRowAcquisitionPurposeV1
                    .INCREMENTAL_PROMOTION
                ),
                discovery_draws=0,
                validation_draws=CHECKPOINT_DRAWS,
                discovery_random_word_calls=0,
                validation_random_word_calls=CHECKPOINT_DRAWS,
            )
        elif item.semantic_row.remaining_horizon == 1:
            native_work = closure.ColdRowNativeWorkV1(
                acquisition_purpose=(
                    closure.ColdRowAcquisitionPurposeV1
                    .INCREMENTAL_NEW_CHILD
                ),
                discovery_draws=materializer.CHILD_DISCOVERY_DRAWS,
                validation_draws=(
                    materializer.CHILD_VALIDATION_DRAWS
                ),
                discovery_random_word_calls=(
                    materializer.CHILD_DISCOVERY_DRAWS
                ),
                validation_random_word_calls=(
                    materializer.CHILD_VALIDATION_DRAWS
                ),
            )
        else:
            native_work = closure.ColdRowNativeWorkV1()
        row = closure.ColdRowEvidenceV1(
            graph.context_id,
            item.cold_state,
            item.semantic_row.remaining_horizon,
            item.cold_action,
            authority.support_descriptors,
            authority.validation_novel,
            authority.support_epoch.support_epoch_id,
            authority.snapshot.snapshot_id,
            authority.row_replay_verification_id,
            physical_id,
            native_work,
        )
        cold_rows.append(row)
        input_by_semantic_key[row.semantic_key] = item
        authority_by_semantic_key[row.semantic_key] = authority
    cap = closure.development_synthetic_cold_h2_cap_evidence_v1(
        context_id=graph.context_id,
        context_key="v072_incremental_postbuild_path4_control_v1",
        total_physical_row_cap=8,
        development_scope_id=_content_id(
            "topology",
            {
                "schema": (
                    "acfqp.v072_incremental_postbuild_development_scope.v1"
                ),
                "handoff_id": handoff.handoff_id,
            },
        ),
    )
    bundle = closure.freeze_v072_cold_h2_closure_v1(
        public_graph=graph,
        row_evidence=tuple(
            sorted(cold_rows, key=lambda item: item.row_evidence_id)
        ),
        logical_occurrence_id=(
            handoff.request.parent_epoch.logical_occurrence_id
        ),
        arm=handoff.request.parent_epoch.arm,
        cap_evidence=cap,
    )
    projections: list[models.VerifiedColdH2ConfidenceRowProjectionV1] = []
    lineage: list[HandoffRowProjectionLineageV1] = []
    for row in bundle.all_rows:
        item = input_by_semantic_key[row.semantic_key]
        authority = authority_by_semantic_key[row.semantic_key]
        source = authority.source_projection
        destinations = tuple(
            sorted(
                (
                    *(
                        models.destination_for_descriptor_v1(
                            row, descriptor
                        )
                        for descriptor in row.discovery_support
                    ),
                    models.other_destination_for_row_v1(row),
                ),
                key=lambda value: value.destination_id,
            )
        )
        events_by_descriptor = {
            value.event_key: value
            for value in authority.snapshot.event_intervals
            if value.event_kind
            is confidence.PartialSupportEventKindV2.SUPPORT
        }
        if set(events_by_descriptor) != {
            value.semantic_descriptor_id
            for value in row.discovery_support
        }:
            raise V072IncrementalPostbuildBridgeInvariantViolation(
                "production confidence support differs from frozen closure"
            )
        masses = []
        for descriptor in row.discovery_support:
            destination = models.destination_for_descriptor_v1(
                row,
                descriptor,
            )
            event = events_by_descriptor[
                descriptor.semantic_descriptor_id
            ]
            masses.append(
                robust.IntervalDestinationMassV1(
                    destination.destination_id,
                    event.lower_probability,
                    event.upper_probability,
                )
            )
        other_destination = next(
            destination
            for destination in destinations
            if destination.category is robust.DestinationCategory.OTHER
        )
        other_event = authority.snapshot.event_intervals[-1]
        if (
            other_event.event_kind
            is not confidence.PartialSupportEventKindV2.OTHER
        ):
            raise V072IncrementalPostbuildBridgeInvariantViolation(
                "production confidence snapshot lost unique OTHER"
            )
        masses.append(
            robust.IntervalDestinationMassV1(
                other_destination.destination_id,
                other_event.lower_probability,
                other_event.upper_probability,
            )
        )
        interval_row = robust.IntervalSimplexRowV1(
            models.ground_state_id_v1(
                row.context_id,
                row.state,
                row.remaining_horizon,
            ),
            row.remaining_horizon,
            models.ground_action_id_v1(
                row.context_id,
                row.state,
                row.remaining_horizon,
                row.action,
            ),
            source.exact_row_reward,
            source.exact_row_reward,
            other_destination.destination_id,
            tuple(sorted(masses, key=lambda value: value.destination_id)),
        )
        projection = models.VerifiedColdH2ConfidenceRowProjectionV1(
            context_id=row.context_id,
            row_evidence_id=row.row_evidence_id,
            physical_evidence_id=row.physical_evidence_id,
            support_epoch_id=row.support_epoch_id,
            confidence_snapshot_id=row.confidence_snapshot_id,
            row_replay_verification_id=row.row_replay_verification_id,
            discovery_transcript_id=(
                authority.discovery_transcript_id
            ),
            validation_transcript_id=(
                authority.validation_transcript_id
            ),
            validation_prefix_id=(
                authority.snapshot.validation_prefix.prefix_id
            ),
            selected_checkpoint_draw_count=(
                item.selected_checkpoint_draw_count
            ),
            source_projection_id=source.projection_id,
            projection_verification_id=(
                authority.projection_verification.verification_id
            ),
            state_semantic_id=row.state.semantic_state_id,
            remaining_horizon=row.remaining_horizon,
            action_semantic_id=row.action.semantic_action_id,
            discovery_support_descriptor_ids=tuple(
                sorted(
                    descriptor.descriptor_record_id
                    for descriptor in row.discovery_support
                )
            ),
            validation_novel_descriptor_ids=tuple(
                sorted(
                    value.descriptor_record_id
                    for value in row.validation_novel
                )
            ),
            interval_row=interval_row,
            destinations=destinations,
            rank_cap=4,
            rank_profile=models.DEVELOPMENT_RANK_PROFILE,
            evidence_class=(
                models.RowProjectionEvidenceClassV1
                .DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY
            ),
            registered_target_evidence=False,
        )
        projections.append(projection)
        lineage.append(
            HandoffRowProjectionLineageV1(
                item.semantic_row.physical_row_id,
                row.row_evidence_id,
                row.physical_evidence_id,
                authority.discovery_transcript_id,
                authority.validation_transcript_id,
                authority.snapshot.validation_prefix.prefix_id,
                projection.projection_binding_id,
                item.source_stream_ids,
                item.selected_checkpoint_draw_count,
            )
        )
    relational_context = models.ColdH2PublicRelationalContextV1(
        graph.context_id,
        topology_id,
        4,
        materializer.development_public_context_v1().edges,
    )
    return (
        bundle,
        tuple(
            sorted(
                projections,
                key=lambda item: item.projection_binding_id,
            )
        ),
        tuple(sorted(lineage, key=lambda item: item.lineage_id)),
        tuple(
            sorted(
                authority_by_semantic_key.values(),
                key=lambda item: item.authority_id,
            )
        ),
        relational_context,
    )


@dataclass(frozen=True, slots=True)
class IncrementalPostbuildResultV1:
    handoff_id: str
    closure_bundle: closure.V072ColdH2ClosureBundleV1
    row_projections: tuple[
        models.VerifiedColdH2ConfidenceRowProjectionV1, ...
    ]
    row_lineage: tuple[HandoffRowProjectionLineageV1, ...]
    confidence_authorities: tuple[
        ProductionConfidenceRowAuthorityV1, ...
    ]
    model_pair: models.V072ColdH2ModelPairV1
    model_independent_attestation: (
        model_independent.V072ColdH2ModelIndependentVerificationV1
    )
    planner_result: (
        planner_component.V072ExactLazyPlannerComponentResultV1
    )
    selected_policy_id: str
    audit_id: str
    failed_frontier_id: str | None
    audit_status: robust.RobustAuditStatus
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.handoff_id, "postbuild handoff"),
            (self.selected_policy_id, "postbuild selected policy"),
            (self.audit_id, "postbuild audit"),
        ):
            _cid(value, field_name)
        if self.failed_frontier_id is not None:
            _cid(self.failed_frontier_id, "postbuild frontier")
        audit = self.planner_result.solve_result.audit
        if (
            type(self.closure_bundle)
            is not closure.V072ColdH2ClosureBundleV1
            or type(self.row_projections) is not tuple
            or type(self.row_lineage) is not tuple
            or type(self.confidence_authorities) is not tuple
            or len(self.confidence_authorities)
            != len(self.closure_bundle.all_rows)
            or len(
                {
                    value.authority_id
                    for value in self.confidence_authorities
                }
            )
            != len(self.confidence_authorities)
            or type(self.model_pair) is not models.V072ColdH2ModelPairV1
            or type(self.model_independent_attestation)
            is not (
                model_independent
                .V072ColdH2ModelIndependentVerificationV1
            )
            or type(self.planner_result)
            is not (
                planner_component
                .V072ExactLazyPlannerComponentResultV1
            )
            or self.planner_result.independent_verification is None
            or audit is None
            or self.model_pair.closure_bundle != self.closure_bundle
            or self.model_independent_attestation.model_pair_id
            != self.model_pair.model_pair_id
            or self.planner_result.model_id
            != self.model_pair.quotient_planner_projection.planner_model.model_id
            or self.planner_result.threshold_profile_id
            != self.model_pair.threshold_profile.threshold_profile_id
            or self.planner_result.solver_kind
            is not robust.RobustSolverKind.QUOTIENT
            or self.planner_result.independent_verification is None
            or self.audit_id != audit.audit_id
            or self.audit_status is not audit.status
            or self.failed_frontier_id
            != (
                None
                if audit.failed_frontier is None
                else audit.failed_frontier.frontier_id
            )
            or (
                self.audit_status is robust.RobustAuditStatus.CERTIFIED
            )
            != (self.failed_frontier_id is None)
        ):
            raise V072IncrementalPostbuildBridgeInvariantViolation(
                "postbuild result is not one independently verified planner audit"
            )
        object.__setattr__(
            self,
            "_result_id",
            _content_id("result", self._payload()),
        )

    @property
    def certified(self) -> bool:
        return self.audit_status is robust.RobustAuditStatus.CERTIFIED

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_incremental_postbuild_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "handoff_id": self.handoff_id,
            "closure_id": self.closure_bundle.closure_id,
            "row_projection_binding_ids": [
                item.projection_binding_id
                for item in self.row_projections
            ],
            "row_lineage_ids": [
                item.lineage_id for item in self.row_lineage
            ],
            "confidence_authority_ids": [
                item.authority_id
                for item in self.confidence_authorities
            ],
            "model_pair_id": self.model_pair.model_pair_id,
            "direct_model_id": self.model_pair.direct_model.model_id,
            "quotient_model_id": self.model_pair.quotient_model.model_id,
            "quotient_planner_model_id": (
                self.model_pair.quotient_planner_projection
                .planner_model.model_id
            ),
            "quotient_other_collapse_proof_id": (
                self.model_pair.quotient_planner_projection
                .collapse_proof.proof_id
            ),
            "model_independent_attestation_id": (
                self.model_independent_attestation.verification_id
            ),
            "planner_component_result_id": (
                self.planner_result.component_result_id
            ),
            "planner_independent_verification_id": (
                self.planner_result.independent_verification.verification_id
                if self.planner_result.independent_verification is not None
                else None
            ),
            "selected_policy_id": self.selected_policy_id,
            "audit_id": self.audit_id,
            "audit_status": self.audit_status.value,
            "failed_frontier_id": self.failed_frontier_id,
            "caller_supplied_model": False,
            "caller_supplied_audit": False,
            "certificate_authority": self.certified,
            "registered_target_evidence": False,
        }

    @property
    def result_id(self) -> str:
        return self._result_id


def run_incremental_postbuild_bridge_v1(
    *,
    handoff: materializer.IncrementalModelRebuildHandoffV1,
    prior_handoff: (
        materializer.IncrementalModelRebuildHandoffV1 | None
    ) = None,
    prior_postbuild: IncrementalPostbuildResultV1 | None = None,
) -> IncrementalPostbuildResultV1:
    """Build, independently verify, solve, and derive the actual audit."""

    bundle, projections, lineage, authorities, relational_context = (
        _build_closure_and_projections(
            handoff,
            prior_handoff,
            prior_postbuild,
        )
    )
    pair = models.build_v072_cold_h2_models_v1(
        closure_bundle=bundle,
        verified_row_projections=projections,
        relational_context=relational_context,
    )
    model_attestation = (
        model_independent
        .verify_v072_cold_h2_model_pair_independently_v1(pair)
    )
    planner_result = (
        planner_component.solve_and_verify_v072_exact_lazy_h2_v1(
            model=(
                pair.quotient_planner_projection.planner_model
            ),
            threshold=pair.threshold_profile,
            solver_kind=robust.RobustSolverKind.QUOTIENT,
        )
    )
    audit = planner_result.solve_result.audit
    if audit is None:
        raise V072IncrementalPostbuildBridgeInvariantViolation(
            "exact-lazy resource exhaustion cannot authorize another round"
        )
    selected_policy_id = _content_id(
        "selected_policy",
        {
            "schema": (
                "acfqp.v072_incremental_postbuild_selected_policy.v1"
            ),
            "planner_model_id": planner_result.model_id,
            "audit_id": audit.audit_id,
            "assignment_ids": [
                item.assignment_id for item in audit.assignments
            ],
            "independent_verification_id": (
                planner_result.independent_verification.verification_id
                if planner_result.independent_verification is not None
                else None
            ),
        },
    )
    return IncrementalPostbuildResultV1(
        handoff.handoff_id,
        bundle,
        projections,
        lineage,
        authorities,
        pair,
        model_attestation,
        planner_result,
        selected_policy_id,
        audit.audit_id,
        (
            None
            if audit.failed_frontier is None
            else audit.failed_frontier.frontier_id
        ),
        audit.status,
    )


def prepare_actual_development_round_two_selection_v1(
    *,
    first_handoff: materializer.IncrementalModelRebuildHandoffV1,
    failed_postbuild: IncrementalPostbuildResultV1,
    arm: selector.TargetSelectionArmV2 = (
        selector.TargetSelectionArmV2.NO_PRIOR
    ),
    source_prior: selector.VerifiedSourcePriorBindingV2 | None = None,
    ood_abstention: selector.OodPriorTypedAbstentionV2 | None = None,
) -> selector.PreparedTargetSelectionV2:
    """Run the production selector on the actual failed model/frontier."""

    if (
        type(first_handoff)
        is not materializer.IncrementalModelRebuildHandoffV1
        or type(failed_postbuild) is not IncrementalPostbuildResultV1
        or failed_postbuild.handoff_id != first_handoff.handoff_id
        or failed_postbuild.audit_status
        is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
        or failed_postbuild.failed_frontier_id is None
        or type(arm) is not selector.TargetSelectionArmV2
        or arm.value != first_handoff.request.parent_epoch.arm
    ):
        raise V072IncrementalPostbuildBridgeInvariantViolation(
            "round-two selector requires the exact failed round-one chain"
        )
    model = (
        failed_postbuild.model_pair.quotient_planner_projection
        .planner_model
    )
    audit = failed_postbuild.planner_result.solve_result.audit
    if audit is None or audit.failed_frontier is None:
        raise V072IncrementalPostbuildBridgeInvariantViolation(
            "round-two selector lacks an actual failed audit/frontier"
        )
    threshold = failed_postbuild.model_pair.threshold_profile
    parent_authority = next(
        value
        for value in failed_postbuild.confidence_authorities
        if value.row_binding.physical_row_id
        == first_handoff.request.parent_evidence.parent_physical_row_id
    )
    novel_state = materializer.DevelopmentPublicStateV1(
        first_handoff.request.parent_epoch.context_id,
        (1, 1, 3, 4),
    )
    catalogue_state_id = _content_id(
        "topology",
        {
            "schema": (
                "acfqp.v072_incremental_postbuild_round_two_"
                "public_child_state.v1"
            ),
            "context_id": novel_state.context_id,
            "state_id": novel_state.state_id,
            "ranks": list(novel_state.ranks),
            "remaining_horizon": 1,
        },
    )
    catalogue = robust.StateActionCatalogueV1(
        catalogue_state_id,
        _content_id(
            "topology",
            {
                "schema": (
                    "acfqp.v072_incremental_postbuild_round_two_"
                    "state_coordinate.v1"
                ),
                "context_id": novel_state.context_id,
                "ranks": list(novel_state.ranks),
            },
        ),
        tuple(
            sorted(
                (
                    robust.CatalogueActionV1(
                        _content_id(
                            "action",
                            {
                                "schema": (
                                    "acfqp.v072_incremental_postbuild_"
                                    "round_two_public_action.v1"
                                ),
                                "state_id": novel_state.state_id,
                                "action": list(action),
                            },
                        ),
                        _content_id(
                            "action",
                            {
                                "schema": (
                                    "acfqp.v072_incremental_postbuild_"
                                    "round_two_action_coordinate.v1"
                                ),
                                "survivor": action[2],
                            },
                        ),
                    )
                    for action in ((0, 1, 0), (0, 1, 1))
                ),
                key=lambda value: value.action_id,
            )
        ),
    )
    row_by_id = {value.row_id: value for value in model.rows}
    metadata = []
    for planner_row_id in audit.failed_frontier.selected_row_ids:
        planner_row = row_by_id[planner_row_id]
        metadata.append(
            selector.FrontierRowPublicActionMetadataV2(
                planner_row.row_id,
                planner_row.state_id,
                planner_row.action_id,
                planner_row.remaining_horizon,
                (catalogue,)
                if planner_row.remaining_horizon == 2
                else (),
            )
        )
    public_metadata = selector.PublicFrontierActionCatalogueMetadataV2(
        model.model_id,
        audit.audit_id,
        audit.failed_frontier.frontier_id,
        parent_authority.support_epoch.support_epoch_id,
        tuple(sorted(metadata, key=lambda value: value.metadata_id)),
    )
    candidates = tuple(
        sorted(
            (
                selector.TargetAcquisitionCandidateV2(
                    model.model_id,
                    audit.audit_id,
                    audit.failed_frontier.frontier_id,
                    threshold.threshold_profile_id,
                    public_metadata.support_epoch_id,
                    value,
                    selector._portable_feature(
                        model=model,
                        audit=audit,
                        row=row_by_id[value.planner_row_id],
                    ),
                )
                for value in public_metadata.rows
            ),
            key=lambda value: value.candidate_id,
        )
    )
    first_authorization = first_handoff.request.authorization
    registry = selector.TargetCandidateRegistryV2(
        model.model_id,
        audit.audit_id,
        audit.failed_frontier.frontier_id,
        threshold.threshold_profile_id,
        public_metadata.support_epoch_id,
        public_metadata.public_metadata_id,
        2,
        first_authorization.registry_id,
        first_authorization.authorization_id,
        first_authorization
        .cumulative_new_child_actions_after_selection,
        first_authorization.cumulative_draw_upper_after_selection,
        candidates,
    )
    return selector.prepare_target_selection_v2(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
        arm=arm,
        source_prior=source_prior,
        ood_abstention=ood_abstention,
    )


@dataclass(frozen=True, slots=True)
class DevelopmentRoundTwoPreparationV1:
    """Actual failed-proof-to-authorized-round-two derivation."""

    first_materializer_attestation: (
        materializer_independent
        .IndependentIncrementalMaterializerAttestationV1
    )
    selection: selector.PreparedTargetSelectionV2
    selector_verification: (
        selector_component.V072TargetSelectorSemanticVerificationV1
    )
    request: materializer.IncrementalMaterializationRequestV1

    def __post_init__(self) -> None:
        if (
            type(self.first_materializer_attestation)
            is not (
                materializer_independent
                .IndependentIncrementalMaterializerAttestationV1
            )
            or type(self.selection)
            is not selector.PreparedTargetSelectionV2
            or type(self.selector_verification)
            is not (
                selector_component
                .V072TargetSelectorSemanticVerificationV1
            )
            or type(self.request)
            is not materializer.IncrementalMaterializationRequestV1
            or self.request.parent_epoch.round_index != 2
            or self.request.authorization
            != self.selection.authorization
            or self.request.preauthorization_access
            != self.selection.access_log
            or self.selector_verification.prepared_selection_id
            != self.selection.prepared_selection_id
            or (
                self.selector_verification
                .previous_materializer_attestation_id
            )
            != self.first_materializer_attestation.attestation_id
            or (
                self.selector_verification
                .previous_development_authorization_id
            )
            != (
                self.selection.registry.previous_authorization_id
            )
        ):
            raise V072IncrementalPostbuildBridgeInvariantViolation(
                "round-two preparation lacks one verified predecessor chain"
            )

    @property
    def preparation_id(self) -> str:
        return _content_id(
            "round_two_preparation",
            {
                "schema": (
                    "acfqp.v072_development_round_two_preparation.v1"
                ),
                "first_materializer_attestation_id": (
                    self.first_materializer_attestation.attestation_id
                ),
                "prepared_selection_id": (
                    self.selection.prepared_selection_id
                ),
                "selector_verification_id": (
                    self.selector_verification.verification_id
                ),
                "request_id": self.request.request_id,
                "proposal_only_resolution_ids": sorted(
                    item.optimistic_resolution_id
                    for item in self.selection.counterfactuals
                    if item.optimistic_resolution_id is not None
                ),
                "resolution_model_used_for_certificate": False,
                "target_access_performed_before_freeze": False,
            },
        )


def prepare_actual_development_round_two_request_v1(
    *,
    first_handoff: materializer.IncrementalModelRebuildHandoffV1,
    failed_postbuild: IncrementalPostbuildResultV1,
    arm: selector.TargetSelectionArmV2 = (
        selector.TargetSelectionArmV2.NO_PRIOR
    ),
    source_prior: selector.VerifiedSourcePriorBindingV2 | None = None,
    ood_abstention: selector.OodPriorTypedAbstentionV2 | None = None,
) -> DevelopmentRoundTwoPreparationV1:
    """Freeze an actual round-two request from the failed standard audit."""

    control = materializer.DevelopmentAcquisitionControlRunV1(
        first_handoff.law_key,
        first_handoff,
    )
    first_attestation = (
        materializer_independent
        .verify_development_incremental_materializer_control_v1(control)
    )
    selected = prepare_actual_development_round_two_selection_v1(
        first_handoff=first_handoff,
        failed_postbuild=failed_postbuild,
        arm=arm,
        source_prior=source_prior,
        ood_abstention=ood_abstention,
    )
    model = (
        failed_postbuild.model_pair.quotient_planner_projection
        .planner_model
    )
    audit = failed_postbuild.planner_result.solve_result.audit
    if audit is None or audit.failed_frontier is None:
        raise V072IncrementalPostbuildBridgeInvariantViolation(
            "round-two request lacks an actual failed audit"
        )
    selected_planner_row = next(
        value
        for value in model.rows
        if value.row_id
        == selected.authorization.selected_planner_row_id
    )
    if selected_planner_row.remaining_horizon != 2:
        raise V072IncrementalPostbuildBridgeInvariantViolation(
            "actual selector did not choose the novel root row"
        )

    collapse_entry = next(
        value
        for value in (
            failed_postbuild.model_pair.quotient_planner_projection
            .collapse_proof.entries
        )
        if value.planner_row_id == selected_planner_row.row_id
    )
    source_row = next(
        value
        for value in failed_postbuild.model_pair.quotient_model.rows
        if value.row_id == collapse_entry.source_row_id
    )
    projection = next(
        value
        for value in failed_postbuild.row_projections
        if (
            value.interval_row.remaining_horizon == 2
            and value.interval_row.action_id == source_row.action_id
        )
    )
    selected_lineage = next(
        value
        for value in failed_postbuild.row_lineage
        if value.projection_binding_id == projection.projection_binding_id
    )
    parent_physical_row_id = (
        first_handoff.request.parent_evidence.parent_physical_row_id
    )
    if selected_lineage.semantic_physical_row_id != parent_physical_row_id:
        raise V072IncrementalPostbuildBridgeInvariantViolation(
            "selector root does not map to the promoted physical row"
        )
    parent_authority = next(
        value
        for value in failed_postbuild.confidence_authorities
        if value.row_binding.physical_row_id == parent_physical_row_id
    )
    if (
        not parent_authority.snapshot.novel_descriptors
        or len(parent_authority.snapshot.novel_descriptors) != 1
    ):
        raise V072IncrementalPostbuildBridgeInvariantViolation(
            "failed root must expose exactly one actual novel descriptor"
        )
    novel = parent_authority.snapshot.novel_descriptors[0]
    ranks = tuple(novel.document["next_state"]["ranks"])
    novel_observation_ids = tuple(
        sorted(
            {
                observation.sample_id
                for observation in (
                    parent_authority.snapshot.validation_prefix.observations
                )
                if observation.outcome.descriptor_id
                == novel.descriptor_id
            }
        )
    )
    novel_descriptor = materializer.DevelopmentNovelDescriptorV1(
        materializer.DevelopmentPublicStateV1(
            first_handoff.request.parent_epoch.context_id,
            ranks,
        ),
        novel_observation_ids,
    )
    first_request = first_handoff.request
    closure_rows = tuple(
        sorted(
            {
                value.physical_row_id: value
                for value in (
                    *first_request.current_closure.rows,
                    *(
                        item.physical_row
                        for item in first_handoff.child_rows
                    ),
                )
            }.values(),
            key=lambda value: value.physical_row_id,
        )
    )
    closure2 = materializer.DevelopmentCurrentClosureV1(
        first_request.parent_epoch.context_id,
        model.model_id,
        closure_rows,
    )
    epoch2 = materializer.ImmutablePlanningEpochV1(
        first_request.parent_epoch.logical_occurrence_id,
        first_request.parent_epoch.context_id,
        arm.value,
        2,
        closure2.closure_id,
        model.model_id,
        audit.audit_id,
        audit.failed_frontier.frontier_id,
        failed_postbuild.model_pair.threshold_profile.threshold_profile_id,
        failed_postbuild.planner_result.component_result_id,
        failed_postbuild.selected_policy_id,
        first_handoff.build_epoch_id,
        closure2.physical_row_ids,
    )
    parent2 = materializer.DevelopmentParentEvidenceV1(
        epoch2,
        parent_physical_row_id,
        parent_authority.support_epoch.support_epoch_id,
        selected.authorization.selected_candidate_id,
        selected.authorization.selected_planner_row_id,
        tuple(
            sorted(
                value.descriptor_id
                for value in (
                    parent_authority.support_epoch.support_descriptors
                )
            )
        ),
        (novel_descriptor,),
        first_request.parent_evidence.upstream_root_rows,
        (),
    )
    evidence2 = materializer.derive_development_cardinality_evidence_v1(
        parent=parent2,
        current_closure=closure2,
        previous_evidence=(
            first_request.cardinality_authority.evidence
        ),
    )
    selected_counterfactual = next(
        value
        for value in selected.counterfactuals
        if value.candidate_id
        == selected.authorization.selected_candidate_id
    )
    if (
        selected_counterfactual.exact_draw_upper
        != evidence2.exact_round_draw_upper
    ):
        raise V072IncrementalPostbuildBridgeInvariantViolation(
            "selector cost and actual novel-child cardinality differ"
        )
    bound_counterfactual = replace(
        selected_counterfactual,
        cardinality_evidence_id=evidence2.evidence_id,
    )
    authority2 = materializer.DevelopmentCardinalityAuthorityV1(
        evidence2,
        bound_counterfactual,
    )
    request2 = materializer.IncrementalMaterializationRequestV1(
        epoch2,
        parent2,
        closure2,
        authority2,
        selected.access_log,
        selected.authorization,
        first_handoff.handoff_id,
    )
    verification = selector_component.verify_target_selection_semantically_v1(
        model=model,
        audit=audit,
        threshold=failed_postbuild.model_pair.threshold_profile,
        registry=selected.registry,
        arm=arm,
        claimed=selected,
        previous_development_authorization=(
            first_request.authorization
        ),
        previous_materializer_attestation_id=(
            first_attestation.attestation_id
        ),
        source_prior=source_prior,
        ood_abstention=ood_abstention,
    )
    return DevelopmentRoundTwoPreparationV1(
        first_attestation,
        selected,
        verification,
        request2,
    )


__all__ = [
    "CHECKPOINT_DRAWS",
    "HandoffRowProjectionLineageV1",
    "IncrementalPostbuildResultV1",
    "DevelopmentRoundTwoPreparationV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V072IncrementalPostbuildBridgeInvariantViolation",
    "run_incremental_postbuild_bridge_v1",
    "prepare_actual_development_round_two_request_v1",
    "prepare_actual_development_round_two_selection_v1",
]
