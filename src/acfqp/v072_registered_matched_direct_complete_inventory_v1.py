"""Complete matched-direct H=2 row inventory and prefix accumulator.

The production authority is deliberately separate from the adaptive
confidence accumulator.  It owns every observer stream, derives the complete
root-plus-discovery-child row inventory internally, and keeps one mutable
validation stream per physical row.  The registered checkpoints
``2048 -> 4096 -> 8192 -> 16384`` are therefore suffix appends to one stream,
never four redraws.

Every acquisition stream has a separate fresh-stream replay instance.  Replay
draws are evaluation work and never reduce or replace acquisition work.  The
module accepts no caller observations, transition law, probability, outcome,
row inventory, row count, confidence interval, or terminal result.

The real production entry points remain anchor-first.  A small
registration-disjoint core exercises inventory, prefix, and accounting
mathematics while the remote-main anchor is unavailable; its artifacts are
explicitly non-target evidence.
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
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import public_novel_child_cardinality_authority_v2 as descriptors
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_cold_h2_closure_independent_verifier_v1 as closure_verify
from acfqp import v072_cold_h2_closure_v1 as cold
from acfqp import v072_cold_h2_model_builders_v1 as cold_builder
from acfqp import v072_confidence_row_projection_v1 as projection
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import v072_heldout_public_graph_adapter_v1 as public_adapter
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import v072_registered_matched_direct_runtime_v1 as runtime


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_registered_matched_direct_complete_inventory_v1"
ARM = runtime.ARM
DISCOVERY_DRAWS_PER_ROW = prereg.INITIAL_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
CHECKPOINTS = prereg.DIRECT_VALIDATION_CHECKPOINTS
CRN_DRAW_DISCOUNT = 0
REGISTERED_COMPLETE_INVENTORY_STATUS = (
    "IMPLEMENTED_ANCHOR_FIRST_SEPARATE_ACQUISITION_AND_REPLAY_LANES"
)


class V072RegisteredMatchedDirectInventoryViolation(ValueError):
    """An authority, inventory, prefix, confidence, or work invariant failed."""


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectInventoryAccessAuditV1:
    authority_chain_verifications: int = 0
    public_inventory_calls: int = 0
    acquisition_stream_opens: int = 0
    acquisition_draw_calls: int = 0
    replay_stream_opens: int = 0
    replay_draw_calls: int = 0

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value < 0
            for value in (
                self.authority_chain_verifications,
                self.public_inventory_calls,
                self.acquisition_stream_opens,
                self.acquisition_draw_calls,
                self.replay_stream_opens,
                self.replay_draw_calls,
            )
        ):
            raise V072RegisteredMatchedDirectInventoryViolation(
                "matched-direct access counters are malformed"
            )

    @property
    def observer_or_target_access_started(self) -> bool:
        return any(
            (
                self.public_inventory_calls,
                self.acquisition_stream_opens,
                self.acquisition_draw_calls,
                self.replay_stream_opens,
                self.replay_draw_calls,
            )
        )


ZERO_TARGET_ACCESS_AUDIT = RegisteredMatchedDirectInventoryAccessAuditV1()


class RegisteredMatchedDirectInventoryGateLockedV1(RuntimeError):
    """The exact production authority chain or occurrence binding is absent."""

    def __init__(
        self,
        message: str,
        *,
        access_audit: RegisteredMatchedDirectInventoryAccessAuditV1,
    ) -> None:
        super().__init__(message)
        self.access_audit = access_audit


DOMAIN_TAGS = {
    "discovery_prefix": (
        "acfqp:v072-registered-matched-direct-discovery-prefix:v1"
    ),
    "validation_prefix": (
        "acfqp:v072-registered-matched-direct-validation-prefix:v1"
    ),
    "transcript": (
        "acfqp:v072-registered-matched-direct-row-transcript:v1"
    ),
    "replay_core": (
        "acfqp:v072-registered-matched-direct-row-replay-core:v1"
    ),
    "physical": (
        "acfqp:v072-registered-matched-direct-row-physical-evidence:v1"
    ),
    "confidence_snapshot": (
        "acfqp:v072-registered-matched-direct-confidence-snapshot:v1"
    ),
    "confidence_event": (
        "acfqp:v072-registered-matched-direct-confidence-event:v1"
    ),
    "confidence_attestation": (
        "acfqp:v072-registered-matched-direct-confidence-attestation:v1"
    ),
    "row_prefix": (
        "acfqp:v072-registered-matched-direct-row-checkpoint-prefix:v1"
    ),
    "work": "acfqp:v072-registered-matched-direct-checkpoint-work:v1",
    "global_other": (
        "acfqp:v072-registered-matched-direct-global-other:v1"
    ),
    "snapshot": (
        "acfqp:v072-registered-matched-direct-cold-snapshot:v1"
    ),
    "model_attestation": (
        "acfqp:v072-registered-matched-direct-model-attestation:v1"
    ),
    "checkpoint": (
        "acfqp:v072-registered-matched-direct-complete-inventory-checkpoint:v1"
    ),
    "run": "acfqp:v072-registered-matched-direct-complete-inventory-run:v1",
    "disjoint_stream": (
        "acfqp:v072-registration-disjoint-matched-direct-stream:v1"
    ),
    "disjoint_prefix": (
        "acfqp:v072-registration-disjoint-matched-direct-prefix:v1"
    ),
    "disjoint_checkpoint": (
        "acfqp:v072-registration-disjoint-matched-direct-checkpoint:v1"
    ),
    "disjoint_run": (
        "acfqp:v072-registration-disjoint-matched-direct-run:v1"
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
        raise V072RegisteredMatchedDirectInventoryViolation(str(error)) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072RegisteredMatchedDirectInventoryViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V072RegisteredMatchedDirectInventoryViolation(
            "matched-direct arithmetic must use exact Fraction"
        )
    return {"numerator": value.numerator, "denominator": value.denominator}


def _recorded_descriptor(
    item: observer.HeldoutObservedJointTransitionV2,
) -> descriptors.RecordedTransitionDescriptorV2:
    if type(item) is not observer.HeldoutObservedJointTransitionV2:
        raise V072RegisteredMatchedDirectInventoryViolation(
            "row transcript contains a foreign observation type"
        )
    return descriptors.RecordedTransitionDescriptorV2(
        item.next_state,
        item.realized_row_reward,
        item.failure,
        item.terminal,
    )


def _observation_tuple_equal(
    left: observer.HeldoutObservedJointTransitionV2,
    right: observer.HeldoutObservedJointTransitionV2,
) -> bool:
    return (
        type(left) is observer.HeldoutObservedJointTransitionV2
        and type(right) is observer.HeldoutObservedJointTransitionV2
        and left.to_document() == right.to_document()
    )


def _verify_gate_without_observer_access(
    *,
    authority_chain: Any,
    anchor: Any,
    occurrence_plan: Any,
    context: Any,
) -> tuple[
    consumer.RegisteredCampaignAuthorityChainV1,
    final_authority.V072RemoteMainAnchorV1,
    runtime.RegisteredMatchedDirectOccurrencePlanV1,
    prereg.HeldoutPublicGraphContextV2,
]:
    if (
        type(authority_chain)
        is not consumer.RegisteredCampaignAuthorityChainV1
        or type(anchor) is not final_authority.V072RemoteMainAnchorV1
        or authority_chain.remote_main_anchor is not anchor
        or type(occurrence_plan)
        is not runtime.RegisteredMatchedDirectOccurrencePlanV1
        or type(context) is not prereg.HeldoutPublicGraphContextV2
    ):
        raise RegisteredMatchedDirectInventoryGateLockedV1(
            "matched-direct inventory requires exact chain/anchor/plan/context "
            "types",
            access_audit=ZERO_TARGET_ACCESS_AUDIT,
        )
    try:
        (
            _source_id,
            _manifest_id,
            final_id,
            anchor_id,
            _anchor_attestation_id,
        ) = consumer.verify_registered_campaign_authority_chain_v1(
            authority_chain
        )
    except (
        consumer.RegisteredCampaignAuthorityGateLockedV1,
        ValueError,
    ) as error:
        raise RegisteredMatchedDirectInventoryGateLockedV1(
            "matched-direct authority chain is stale or rebound",
            access_audit=ZERO_TARGET_ACCESS_AUDIT,
        ) from error
    if (
        context not in prereg.registered_heldout_public_contexts_v2()
        or occurrence_plan.anchor_id != anchor_id
        or occurrence_plan.anchor_id != anchor.anchor_id
        or occurrence_plan.context_id != context.context_id
        or occurrence_plan.context_key != context.context_key
        or occurrence_plan.arm != ARM
        or occurrence_plan.maximum_checkpoint != CHECKPOINTS[-1]
        or occurrence_plan.replacement_allowed is not False
        or occurrence_plan.early_skip_allowed is not False
        or anchor.claim.final_preregistration_id != final_id
    ):
        raise RegisteredMatchedDirectInventoryGateLockedV1(
            "matched-direct occurrence identity is stale or rebound",
            access_audit=RegisteredMatchedDirectInventoryAccessAuditV1(
                authority_chain_verifications=1
            ),
        )
    return authority_chain, anchor, occurrence_plan, context


def _confidence_counts_and_intervals(
    *,
    support_descriptor_ids: tuple[str, ...],
    validation_descriptor_ids: tuple[str, ...],
    checkpoint: int,
) -> tuple[
    tuple[int, ...],
    tuple[tuple[Fraction, Fraction, Mapping[str, Any]], ...],
]:
    if (
        checkpoint not in CHECKPOINTS
        or support_descriptor_ids
        != tuple(sorted(set(support_descriptor_ids)))
        or not 1
        <= len(support_descriptor_ids)
        <= observer.MAX_FROZEN_SUPPORT_MEMBERS_PER_ROW_V2
        or type(validation_descriptor_ids) is not tuple
        or len(validation_descriptor_ids) != checkpoint
    ):
        raise V072RegisteredMatchedDirectInventoryViolation(
            "direct confidence input is outside the registered schedule"
        )
    counts = {item: 0 for item in support_descriptor_ids}
    other_count = 0
    for descriptor_id in validation_descriptor_ids:
        _cid(descriptor_id, "validation descriptor")
        if descriptor_id in counts:
            counts[descriptor_id] += 1
        else:
            other_count += 1
    values = tuple(counts[item] for item in support_descriptor_ids) + (
        other_count,
    )
    profile = SequentialBernoulliProfileV1(
        confidence_alpha=prereg.ROW_EPOCH_BETA / len(values),
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
        for count in values
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
        sum(values) != checkpoint
        or sum(lower for lower, _upper, _doc in intervals) > 1
        or sum(upper for _lower, upper, _doc in intervals) < 1
    ):
        raise V072RegisteredMatchedDirectInventoryViolation(
            "direct confidence events do not form an interval simplex"
        )
    return values, intervals


_CONFIDENCE_ATTESTATION_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectConfidenceReplayAttestationV1:
    """Private fresh-stream replay accepted by the projection authority."""

    _minting_capability: object
    authority_chain_id: str
    anchor_id: str
    final_preregistration_id: str
    occurrence_plan_id: str
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
    event_probability_intervals: tuple[tuple[Fraction, Fraction], ...]
    selected_checkpoint_draw_count: int
    replayed_stream_opens: int
    replayed_draw_calls: int
    replay_execution_lane: str = "EVALUATION_DETERMINISTIC_FRESH_STREAM_REPLAY"
    crn_draw_discount: int = 0
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.authority_chain_id,
            self.anchor_id,
            self.final_preregistration_id,
            self.occurrence_plan_id,
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
            _cid(value, "direct confidence replay identity")
        if (
            self._minting_capability is not _CONFIDENCE_ATTESTATION_SENTINEL
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
            or len(self.event_probability_intervals) != len(self.event_ids)
            or sum(self.event_success_counts)
            != self.selected_checkpoint_draw_count
            or self.selected_checkpoint_draw_count not in CHECKPOINTS
            or any(
                type(count) is not int or count < 0
                for count in self.event_success_counts
            )
            or any(
                type(lower) is not Fraction
                or type(upper) is not Fraction
                or not 0 <= lower <= upper <= 1
                for lower, upper in self.event_probability_intervals
            )
            or sum(
                lower for lower, _upper in self.event_probability_intervals
            )
            > 1
            or sum(
                upper for _lower, upper in self.event_probability_intervals
            )
            < 1
            or self.replayed_stream_opens != 2
            or self.replayed_draw_calls
            != DISCOVERY_DRAWS_PER_ROW + self.selected_checkpoint_draw_count
            or self.replay_execution_lane
            != "EVALUATION_DETERMINISTIC_FRESH_STREAM_REPLAY"
            or self.crn_draw_discount != 0
        ):
            raise V072RegisteredMatchedDirectInventoryViolation(
                "direct confidence replay attestation is malformed"
            )
        object.__setattr__(
            self,
            "_attestation_id",
            _content_id("confidence_attestation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_matched_direct_confidence_"
                "replay_attestation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "final_preregistration_id": self.final_preregistration_id,
            "occurrence_plan_id": self.occurrence_plan_id,
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
            "replay_execution_lane": self.replay_execution_lane,
            "crn_draw_discount": 0,
            "fresh_stream_replay": True,
            "caller_observations_or_counts_accepted": False,
        }

    @property
    def attestation_id(self) -> str:
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectRowCheckpointPrefixV1:
    row_binding_id: str
    catalogue_id: str
    remaining_horizon: int
    checkpoint: int
    acquisition_discovery_stream_id: str
    acquisition_validation_stream_id: str
    replay_discovery_stream_id: str
    replay_validation_stream_id: str
    previous_prefix_id: str | None
    discovery_transcript_id: str
    validation_prefix_id: str
    acquisition_validation_observation_ids: tuple[str, ...]
    replay_validation_observation_ids: tuple[str, ...]
    _prefix_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.row_binding_id,
            self.catalogue_id,
            self.acquisition_discovery_stream_id,
            self.acquisition_validation_stream_id,
            self.replay_discovery_stream_id,
            self.replay_validation_stream_id,
            self.discovery_transcript_id,
            self.validation_prefix_id,
            *self.acquisition_validation_observation_ids,
            *self.replay_validation_observation_ids,
        ):
            _cid(value, "direct row-prefix identity")
        if self.previous_prefix_id is not None:
            _cid(self.previous_prefix_id, "direct previous row prefix")
        if (
            self.remaining_horizon not in (1, prereg.HORIZON)
            or self.checkpoint not in CHECKPOINTS
            or len(self.acquisition_validation_observation_ids)
            != self.checkpoint
            or self.acquisition_validation_observation_ids
            != self.replay_validation_observation_ids
            or self.acquisition_discovery_stream_id
            != self.replay_discovery_stream_id
            or self.acquisition_validation_stream_id
            != self.replay_validation_stream_id
            or (
                self.checkpoint == CHECKPOINTS[0]
                and self.previous_prefix_id is not None
            )
            or (
                self.checkpoint != CHECKPOINTS[0]
                and self.previous_prefix_id is None
            )
        ):
            raise V072RegisteredMatchedDirectInventoryViolation(
                "direct row checkpoint is replaced, redrawn, or incomplete"
            )
        object.__setattr__(
            self,
            "_prefix_id",
            _content_id("row_prefix", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_matched_direct_row_checkpoint_prefix.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "row_binding_id": self.row_binding_id,
            "catalogue_id": self.catalogue_id,
            "remaining_horizon": self.remaining_horizon,
            "checkpoint": self.checkpoint,
            "acquisition_discovery_stream_id": (
                self.acquisition_discovery_stream_id
            ),
            "acquisition_validation_stream_id": (
                self.acquisition_validation_stream_id
            ),
            "replay_discovery_stream_id": self.replay_discovery_stream_id,
            "replay_validation_stream_id": self.replay_validation_stream_id,
            "previous_prefix_id": self.previous_prefix_id,
            "discovery_transcript_id": self.discovery_transcript_id,
            "validation_prefix_id": self.validation_prefix_id,
            "acquisition_validation_observation_ids": list(
                self.acquisition_validation_observation_ids
            ),
            "replay_validation_observation_ids": list(
                self.replay_validation_observation_ids
            ),
            "append_only_same_stream": True,
            "replacement_allowed": False,
            "redraw_of_old_prefix": False,
        }

    @property
    def prefix_id(self) -> str:
        return self._prefix_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "prefix_id": self.prefix_id}


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectCheckpointWorkV1:
    checkpoint: int
    previous_checkpoint: int
    row_count: int
    acquisition_discovery_draws_cumulative: int
    acquisition_validation_draws_new: int
    acquisition_validation_draws_cumulative: int
    acquisition_sample_total: int
    replay_discovery_draws_cumulative: int
    replay_validation_draws_new: int
    replay_validation_draws_cumulative: int
    deterministic_verifier_replay_total: int
    acquisition_stream_opens_cumulative: int
    replay_stream_opens_cumulative: int
    crn_draw_discount: int = 0
    _work_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        expected_previous = (
            0
            if self.checkpoint == CHECKPOINTS[0]
            else CHECKPOINTS[CHECKPOINTS.index(self.checkpoint) - 1]
        )
        discovery = self.row_count * DISCOVERY_DRAWS_PER_ROW
        new_validation = self.row_count * (
            self.checkpoint - expected_previous
        )
        cumulative_validation = self.row_count * self.checkpoint
        cumulative_total = discovery + cumulative_validation
        if (
            self.checkpoint not in CHECKPOINTS
            or self.previous_checkpoint != expected_previous
            or type(self.row_count) is not int
            or self.row_count <= 0
            or self.acquisition_discovery_draws_cumulative != discovery
            or self.acquisition_validation_draws_new != new_validation
            or self.acquisition_validation_draws_cumulative
            != cumulative_validation
            or self.acquisition_sample_total != cumulative_total
            or self.replay_discovery_draws_cumulative != discovery
            or self.replay_validation_draws_new != new_validation
            or self.replay_validation_draws_cumulative
            != cumulative_validation
            or self.deterministic_verifier_replay_total != cumulative_total
            or self.acquisition_stream_opens_cumulative != 2 * self.row_count
            or self.replay_stream_opens_cumulative != 2 * self.row_count
            or self.crn_draw_discount != 0
        ):
            raise V072RegisteredMatchedDirectInventoryViolation(
                "matched-direct work summed checkpoints or mixed replay work"
            )
        object.__setattr__(
            self,
            "_work_id",
            _content_id("work", self._payload()),
        )

    @property
    def acquisition_discovery_draws_new(self) -> int:
        return (
            self.acquisition_discovery_draws_cumulative
            if self.previous_checkpoint == 0
            else 0
        )

    @property
    def replay_discovery_draws_new(self) -> int:
        return (
            self.replay_discovery_draws_cumulative
            if self.previous_checkpoint == 0
            else 0
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_matched_direct_checkpoint_work.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "checkpoint": self.checkpoint,
            "previous_checkpoint": self.previous_checkpoint,
            "row_count": self.row_count,
            "acquisition_discovery_draws_cumulative": (
                self.acquisition_discovery_draws_cumulative
            ),
            "acquisition_discovery_draws_new": (
                self.acquisition_discovery_draws_new
            ),
            "acquisition_validation_draws_new": (
                self.acquisition_validation_draws_new
            ),
            "acquisition_validation_draws_cumulative": (
                self.acquisition_validation_draws_cumulative
            ),
            "acquisition_sample_total": self.acquisition_sample_total,
            "replay_discovery_draws_cumulative": (
                self.replay_discovery_draws_cumulative
            ),
            "replay_discovery_draws_new": (
                self.replay_discovery_draws_new
            ),
            "replay_validation_draws_new": (
                self.replay_validation_draws_new
            ),
            "replay_validation_draws_cumulative": (
                self.replay_validation_draws_cumulative
            ),
            "deterministic_verifier_replay_total": (
                self.deterministic_verifier_replay_total
            ),
            "acquisition_stream_opens_cumulative": (
                self.acquisition_stream_opens_cumulative
            ),
            "replay_stream_opens_cumulative": (
                self.replay_stream_opens_cumulative
            ),
            "acquisition_and_replay_lanes_separate": True,
            "checkpoint_work_is_cumulative_not_checkpoint_sum": True,
            "crn_draw_discount": 0,
        }

    @property
    def work_id(self) -> str:
        return self._work_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


def _registered_global_other(
    context_id: str,
) -> robust.RegisteredDestinationV1:
    _cid(context_id, "direct global OTHER context")
    return robust.RegisteredDestinationV1(
        _content_id(
            "global_other",
            {
                "schema": (
                    "acfqp.v072_registered_matched_direct_global_other.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "context_id": context_id,
                "failure_value": 1,
                "continuation_reward_lower": _fdoc(Fraction(0)),
            },
        ),
        robust.DestinationCategory.OTHER,
    )


def _producer_direct_model(
    closure_bundle: cold.V072ColdH2ClosureBundleV1,
    row_projections: tuple[
        projection.RegisteredConfidenceIntervalSimplexRowProjectionV1,
        ...,
    ],
) -> tuple[
    robust.PartialSupportIntervalModelV1,
    tuple[tuple[str, str, str], ...],
]:
    """Materialize the direct planner view without a quotient or prior."""

    catalogues = (
        closure_bundle.root_catalogue,
        *closure_bundle.child_catalogues,
    )
    state_ids = {
        catalogue.state.semantic_state_id:
            cold_builder.ground_state_id_v1(
                closure_bundle.context_id,
                catalogue.state,
                catalogue.remaining_horizon,
            )
        for catalogue in catalogues
    }
    planner_catalogues = tuple(
        robust.StateActionCatalogueV1(
            state_ids[catalogue.state.semantic_state_id],
            state_ids[catalogue.state.semantic_state_id],
            tuple(
                sorted(
                    (
                        robust.CatalogueActionV1(action_id, action_id)
                        for action in catalogue.actions
                        for action_id in (
                            cold_builder.ground_action_id_v1(
                                closure_bundle.context_id,
                                catalogue.state,
                                catalogue.remaining_horizon,
                                action,
                            ),
                        )
                    ),
                    key=lambda item: item.action_id,
                )
            ),
        )
        for catalogue in catalogues
    )
    global_other = _registered_global_other(closure_bundle.context_id)
    non_other_by_id: dict[str, robust.RegisteredDestinationV1] = {}
    planner_rows: list[robust.IntervalSimplexRowV1] = []
    mappings: list[tuple[str, str, str]] = []
    for item in row_projections:
        source_row = item.interval_row
        source_destination_by_id = {
            destination.destination_id: destination
            for destination in item.destinations
        }
        source_other = source_destination_by_id[
            source_row.other_destination_id
        ]
        if source_other.category is not robust.DestinationCategory.OTHER:
            raise V072RegisteredMatchedDirectInventoryViolation(
                "direct source row OTHER is not adversarial"
            )
        for destination in item.destinations:
            if destination.category is robust.DestinationCategory.OTHER:
                continue
            existing = non_other_by_id.setdefault(
                destination.destination_id,
                destination,
            )
            if existing != destination:
                raise V072RegisteredMatchedDirectInventoryViolation(
                    "direct destination ID has conflicting semantics"
                )
        collapsed_other = robust.IntervalDestinationMassV1(
            global_other.destination_id,
            source_row.other_mass.lower,
            source_row.other_mass.upper,
        )
        planner_row = robust.IntervalSimplexRowV1(
            source_row.state_id,
            source_row.remaining_horizon,
            source_row.action_id,
            source_row.reward_lower,
            source_row.reward_upper,
            global_other.destination_id,
            tuple(
                sorted(
                    (
                        *(
                            mass
                            for mass in source_row.masses
                            if mass.destination_id
                            != source_row.other_destination_id
                        ),
                        collapsed_other,
                    ),
                    key=lambda mass: mass.destination_id,
                )
            ),
        )
        planner_rows.append(planner_row)
        mappings.append(
            (
                source_row.row_id,
                source_row.other_destination_id,
                planner_row.row_id,
            )
        )
    model = robust.build_partial_support_model_v1(
        context_id=closure_bundle.context_id,
        root_state_id=state_ids[
            closure_bundle.root_state.semantic_state_id
        ],
        catalogues=planner_catalogues,
        destinations=(
            *non_other_by_id.values(),
            global_other,
        ),
        rows=planner_rows,
    )
    return model, tuple(sorted(mappings))


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectColdSnapshotV1:
    closure_bundle: cold.V072ColdH2ClosureBundleV1
    row_projections: tuple[
        projection.RegisteredConfidenceIntervalSimplexRowProjectionV1,
        ...,
    ]
    planner_model: robust.PartialSupportIntervalModelV1
    collapse_mappings: tuple[tuple[str, str, str], ...]
    threshold_profile: robust.RobustThresholdProfileV1
    _snapshot_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.closure_bundle) is not cold.V072ColdH2ClosureBundleV1
            or self.closure_bundle.arm != ARM
            or type(self.row_projections) is not tuple
            or not self.row_projections
            or any(
                type(item)
                is not (
                    projection
                    .RegisteredConfidenceIntervalSimplexRowProjectionV1
                )
                for item in self.row_projections
            )
            or tuple(
                item.projection_id for item in self.row_projections
            )
            != tuple(
                sorted(
                    {
                        item.projection_id
                        for item in self.row_projections
                    }
                )
            )
            or {
                item.row_evidence_id for item in self.row_projections
            }
            != {
                item.row_evidence_id
                for item in self.closure_bundle.all_rows
            }
            or type(self.planner_model)
            is not robust.PartialSupportIntervalModelV1
            or self.planner_model.context_id
            != self.closure_bundle.context_id
            or self.planner_model.concretizer_entries
            or type(self.collapse_mappings) is not tuple
            or self.collapse_mappings
            != tuple(sorted(set(self.collapse_mappings)))
            or len(self.collapse_mappings) != len(self.row_projections)
            or type(self.threshold_profile)
            is not robust.RobustThresholdProfileV1
            or self.threshold_profile.context_id
            != self.closure_bundle.context_id
            or self.threshold_profile.risk_tolerance != Fraction(1, 20)
            or self.threshold_profile.reward_ceiling != Fraction(3, 64)
        ):
            raise V072RegisteredMatchedDirectInventoryViolation(
                "matched-direct cold snapshot contains stale or quotient evidence"
            )
        object.__setattr__(
            self,
            "_snapshot_id",
            _content_id("snapshot", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_matched_direct_cold_snapshot.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": self.closure_bundle.context_id,
            "closure_id": self.closure_bundle.closure_id,
            "projection_ids": [
                item.projection_id for item in self.row_projections
            ],
            "planner_model_id": self.planner_model.model_id,
            "collapse_mappings": [
                list(item) for item in self.collapse_mappings
            ],
            "threshold_profile_id": (
                self.threshold_profile.threshold_profile_id
            ),
            "ground_direct_only": True,
            "quotient_model_builds": 0,
            "source_prior_reads": 0,
            "kernel_calls": 0,
        }

    @property
    def snapshot_id(self) -> str:
        return self._snapshot_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "planner_model": self.planner_model.to_document(),
            "threshold_profile": self.threshold_profile.to_document(),
            "snapshot_id": self.snapshot_id,
        }


def build_registered_matched_direct_cold_snapshot_v1(
    *,
    closure_bundle: cold.V072ColdH2ClosureBundleV1,
    row_projections: tuple[
        projection.RegisteredConfidenceIntervalSimplexRowProjectionV1,
        ...,
    ],
) -> RegisteredMatchedDirectColdSnapshotV1:
    projections = tuple(
        sorted(row_projections, key=lambda item: item.projection_id)
    )
    model, mappings = _producer_direct_model(
        closure_bundle,
        projections,
    )
    threshold = robust.RobustThresholdProfileV1(
        closure_bundle.context_id,
        Fraction(1, 20),
        Fraction(3, 64),
    )
    return RegisteredMatchedDirectColdSnapshotV1(
        closure_bundle,
        projections,
        model,
        mappings,
        threshold,
    )


_MODEL_ATTESTATION_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectModelIndependentAttestationV1:
    _minting_capability: object
    snapshot_id: str
    closure_id: str
    planner_model_id: str
    projection_ids: tuple[str, ...]
    row_ids: tuple[str, ...]
    collapse_mappings: tuple[tuple[str, str, str], ...]
    independent_replay_work_events: int
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.snapshot_id,
            self.closure_id,
            self.planner_model_id,
            *self.projection_ids,
            *self.row_ids,
            *(value for item in self.collapse_mappings for value in item),
        ):
            _cid(value, "direct model attestation identity")
        if (
            self._minting_capability is not _MODEL_ATTESTATION_SENTINEL
            or self.projection_ids
            != tuple(sorted(set(self.projection_ids)))
            or self.row_ids != tuple(sorted(set(self.row_ids)))
            or self.collapse_mappings
            != tuple(sorted(set(self.collapse_mappings)))
            or len(self.projection_ids) != len(self.row_ids)
            or len(self.collapse_mappings) != len(self.row_ids)
            or self.independent_replay_work_events
            != len(self.row_ids)
        ):
            raise V072RegisteredMatchedDirectInventoryViolation(
                "direct model independent attestation is malformed"
            )
        object.__setattr__(
            self,
            "_attestation_id",
            _content_id("model_attestation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_matched_direct_model_"
                "independent_attestation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id,
            "closure_id": self.closure_id,
            "planner_model_id": self.planner_model_id,
            "projection_ids": list(self.projection_ids),
            "row_ids": list(self.row_ids),
            "collapse_mappings": [
                list(item) for item in self.collapse_mappings
            ],
            "independent_replay_work_events": (
                self.independent_replay_work_events
            ),
            "execution_lane": "EVALUATION_INDEPENDENT_MODEL_REPLAY",
            "producer_builder_called": False,
            "quotient_model_built": False,
            "kernel_calls": 0,
            "source_prior_reads": 0,
        }

    @property
    def attestation_id(self) -> str:
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}


def _independent_direct_model_replay(
    snapshot: RegisteredMatchedDirectColdSnapshotV1,
) -> tuple[
    robust.PartialSupportIntervalModelV1,
    tuple[tuple[str, str, str], ...],
]:
    """Duplicate direct materialization without calling the producer builder."""

    closure_bundle = snapshot.closure_bundle
    catalogues = (
        closure_bundle.root_catalogue,
        *closure_bundle.child_catalogues,
    )
    state_ids: dict[str, str] = {}
    planner_catalogues: list[robust.StateActionCatalogueV1] = []
    for catalogue in catalogues:
        state_id = cold_builder.ground_state_id_v1(
            closure_bundle.context_id,
            catalogue.state,
            catalogue.remaining_horizon,
        )
        state_ids[catalogue.state.semantic_state_id] = state_id
        actions = []
        for action in catalogue.actions:
            action_id = cold_builder.ground_action_id_v1(
                closure_bundle.context_id,
                catalogue.state,
                catalogue.remaining_horizon,
                action,
            )
            actions.append(robust.CatalogueActionV1(action_id, action_id))
        planner_catalogues.append(
            robust.StateActionCatalogueV1(
                state_id,
                state_id,
                tuple(sorted(actions, key=lambda item: item.action_id)),
            )
        )
    global_other = _registered_global_other(closure_bundle.context_id)
    destinations: dict[str, robust.RegisteredDestinationV1] = {}
    rows: list[robust.IntervalSimplexRowV1] = []
    mappings: list[tuple[str, str, str]] = []
    for item in snapshot.row_projections:
        source = item.interval_row
        for destination in item.destinations:
            if destination.category is robust.DestinationCategory.OTHER:
                continue
            prior = destinations.setdefault(
                destination.destination_id,
                destination,
            )
            if prior != destination:
                raise V072RegisteredMatchedDirectInventoryViolation(
                    "independent direct destination replay conflicts"
                )
        other_mass = robust.IntervalDestinationMassV1(
            global_other.destination_id,
            source.other_mass.lower,
            source.other_mass.upper,
        )
        replayed = robust.IntervalSimplexRowV1(
            source.state_id,
            source.remaining_horizon,
            source.action_id,
            source.reward_lower,
            source.reward_upper,
            global_other.destination_id,
            tuple(
                sorted(
                    (
                        *(
                            mass
                            for mass in source.masses
                            if mass.destination_id
                            != source.other_destination_id
                        ),
                        other_mass,
                    ),
                    key=lambda mass: mass.destination_id,
                )
            ),
        )
        rows.append(replayed)
        mappings.append(
            (source.row_id, source.other_destination_id, replayed.row_id)
        )
    model = robust.PartialSupportIntervalModelV1(
        closure_bundle.context_id,
        state_ids[closure_bundle.root_state.semantic_state_id],
        tuple(sorted(planner_catalogues, key=lambda item: item.state_id)),
        tuple(
            sorted(
                (*destinations.values(), global_other),
                key=lambda item: item.destination_id,
            )
        ),
        tuple(sorted(rows, key=lambda item: item.row_id)),
        (),
    )
    return model, tuple(sorted(mappings))


def verify_registered_matched_direct_cold_snapshot_independently_v1(
    *,
    snapshot: RegisteredMatchedDirectColdSnapshotV1,
) -> RegisteredMatchedDirectModelIndependentAttestationV1:
    if type(snapshot) is not RegisteredMatchedDirectColdSnapshotV1:
        raise V072RegisteredMatchedDirectInventoryViolation(
            "direct model verifier requires the exact snapshot type"
        )
    replayed, mappings = _independent_direct_model_replay(snapshot)
    if (
        replayed.to_document() != snapshot.planner_model.to_document()
        or mappings != snapshot.collapse_mappings
    ):
        raise V072RegisteredMatchedDirectInventoryViolation(
            "direct model differs from independent complete replay"
        )
    return RegisteredMatchedDirectModelIndependentAttestationV1(
        _MODEL_ATTESTATION_SENTINEL,
        snapshot.snapshot_id,
        snapshot.closure_bundle.closure_id,
        replayed.model_id,
        tuple(item.projection_id for item in snapshot.row_projections),
        tuple(item.row_id for item in replayed.rows),
        mappings,
        len(replayed.rows),
    )


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectCompleteInventoryCheckpointV1:
    authority_chain_id: str
    anchor_id: str
    final_preregistration_id: str
    occurrence_plan_id: str
    context_id: str
    checkpoint: int
    previous_checkpoint_id: str | None
    stable_row_binding_ids: tuple[str, ...]
    row_prefixes: tuple[RegisteredMatchedDirectRowCheckpointPrefixV1, ...]
    row_evidence: tuple[cold.ColdRowEvidenceV1, ...]
    confidence_attestations: tuple[
        RegisteredMatchedDirectConfidenceReplayAttestationV1, ...
    ]
    row_projections: tuple[
        projection.RegisteredConfidenceIntervalSimplexRowProjectionV1,
        ...,
    ]
    closure_bundle: cold.V072ColdH2ClosureBundleV1
    closure_verification: (
        closure_verify.V072ColdH2IndependentVerificationV1
    )
    direct_snapshot: RegisteredMatchedDirectColdSnapshotV1
    model_attestation: (
        RegisteredMatchedDirectModelIndependentAttestationV1
    )
    work: RegisteredMatchedDirectCheckpointWorkV1
    inventory_replacement_allowed: bool = False
    inventory_skip_allowed: bool = False
    _checkpoint_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.authority_chain_id,
            self.anchor_id,
            self.final_preregistration_id,
            self.occurrence_plan_id,
            self.context_id,
            *self.stable_row_binding_ids,
        ):
            _cid(value, "direct checkpoint identity")
        if self.previous_checkpoint_id is not None:
            _cid(self.previous_checkpoint_id, "direct prior checkpoint")
        row_count = len(self.stable_row_binding_ids)
        if (
            self.checkpoint not in CHECKPOINTS
            or self.stable_row_binding_ids
            != tuple(sorted(set(self.stable_row_binding_ids)))
            or row_count <= 0
            or type(self.row_prefixes) is not tuple
            or len(self.row_prefixes) != row_count
            or any(
                type(item)
                is not RegisteredMatchedDirectRowCheckpointPrefixV1
                for item in self.row_prefixes
            )
            or tuple(
                item.row_binding_id for item in self.row_prefixes
            )
            != self.stable_row_binding_ids
            or any(
                item.checkpoint != self.checkpoint
                for item in self.row_prefixes
            )
            or type(self.row_evidence) is not tuple
            or len(self.row_evidence) != row_count
            or any(
                type(item) is not cold.ColdRowEvidenceV1
                for item in self.row_evidence
            )
            or tuple(
                item.row_evidence_id for item in self.row_evidence
            )
            != tuple(
                sorted(
                    {
                        item.row_evidence_id for item in self.row_evidence
                    }
                )
            )
            or any(
                item.native_work.acquisition_purpose
                is not cold.ColdRowAcquisitionPurposeV1
                .MATCHED_DIRECT_CHECKPOINT
                or item.native_work.validation_draws != self.checkpoint
                for item in self.row_evidence
            )
            or type(self.confidence_attestations) is not tuple
            or len(self.confidence_attestations) != row_count
            or any(
                type(item)
                is not RegisteredMatchedDirectConfidenceReplayAttestationV1
                or item.selected_checkpoint_draw_count != self.checkpoint
                for item in self.confidence_attestations
            )
            or type(self.row_projections) is not tuple
            or len(self.row_projections) != row_count
            or any(
                type(item)
                is not (
                    projection
                    .RegisteredConfidenceIntervalSimplexRowProjectionV1
                )
                for item in self.row_projections
            )
            or {
                item.row_evidence_id for item in self.row_projections
            }
            != {item.row_evidence_id for item in self.row_evidence}
            or any(
                item.selected_checkpoint_draw_count != self.checkpoint
                for item in self.row_projections
            )
            or {
                item.row_evidence_id
                for item in self.confidence_attestations
            }
            != {item.row_evidence_id for item in self.row_evidence}
            or type(self.closure_bundle)
            is not cold.V072ColdH2ClosureBundleV1
            or self.closure_bundle.context_id != self.context_id
            or self.closure_bundle.arm != ARM
            or {
                item.row_evidence_id
                for item in self.closure_bundle.all_rows
            }
            != {item.row_evidence_id for item in self.row_evidence}
            or self.closure_bundle.counters.total_action_row_count != row_count
            or self.closure_bundle.counters
            .matched_direct_checkpoint_row_count
            != row_count
            or self.closure_bundle.counters.validation_draws
            != row_count * self.checkpoint
            or type(self.closure_verification)
            is not closure_verify.V072ColdH2IndependentVerificationV1
            or self.closure_verification.closure_id
            != self.closure_bundle.closure_id
            or type(self.direct_snapshot)
            is not RegisteredMatchedDirectColdSnapshotV1
            or self.direct_snapshot.closure_bundle != self.closure_bundle
            or type(self.model_attestation)
            is not RegisteredMatchedDirectModelIndependentAttestationV1
            or self.model_attestation.snapshot_id
            != self.direct_snapshot.snapshot_id
            or self.model_attestation.planner_model_id
            != self.direct_snapshot.planner_model.model_id
            or type(self.work)
            is not RegisteredMatchedDirectCheckpointWorkV1
            or self.work.checkpoint != self.checkpoint
            or self.work.row_count != row_count
            or self.inventory_replacement_allowed is not False
            or self.inventory_skip_allowed is not False
            or (
                self.checkpoint == CHECKPOINTS[0]
                and self.previous_checkpoint_id is not None
            )
            or (
                self.checkpoint != CHECKPOINTS[0]
                and self.previous_checkpoint_id is None
            )
        ):
            raise V072RegisteredMatchedDirectInventoryViolation(
                "complete direct checkpoint is partial, stale, or replaced"
            )
        object.__setattr__(
            self,
            "_checkpoint_id",
            _content_id("checkpoint", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_matched_direct_complete_"
                "inventory_checkpoint.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "final_preregistration_id": self.final_preregistration_id,
            "occurrence_plan_id": self.occurrence_plan_id,
            "context_id": self.context_id,
            "arm": ARM,
            "checkpoint": self.checkpoint,
            "previous_checkpoint_id": self.previous_checkpoint_id,
            "stable_row_binding_ids": list(self.stable_row_binding_ids),
            "row_prefix_ids": [
                item.prefix_id for item in self.row_prefixes
            ],
            "row_evidence_ids": [
                item.row_evidence_id for item in self.row_evidence
            ],
            "confidence_attestation_ids": [
                item.attestation_id
                for item in self.confidence_attestations
            ],
            "row_projection_ids": [
                item.projection_id for item in self.row_projections
            ],
            "closure_id": self.closure_bundle.closure_id,
            "closure_verification_id": (
                self.closure_verification.verification_id
            ),
            "direct_snapshot_id": self.direct_snapshot.snapshot_id,
            "model_attestation_id": self.model_attestation.attestation_id,
            "work_id": self.work.work_id,
            "complete_root_plus_reachable_h1_inventory": True,
            "append_only_same_stream_prefix": True,
            "inventory_replacement_allowed": False,
            "inventory_skip_allowed": False,
            "source_prior_reads": 0,
            "evaluation_only_exact_atoms_calls": 0,
            "crn_draw_discount": 0,
        }

    @property
    def checkpoint_id(self) -> str:
        return self._checkpoint_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_prefixes": [
                item.to_document() for item in self.row_prefixes
            ],
            "row_evidence": [
                item.to_document() for item in self.row_evidence
            ],
            "confidence_attestations": [
                item.to_document()
                for item in self.confidence_attestations
            ],
            "row_projections": [
                item.to_document() for item in self.row_projections
            ],
            "closure_bundle": self.closure_bundle.to_document(),
            "closure_verification": (
                self.closure_verification.to_document()
            ),
            "direct_snapshot": self.direct_snapshot.to_document(),
            "model_attestation": self.model_attestation.to_document(),
            "work": self.work.to_document(),
            "checkpoint_id": self.checkpoint_id,
        }


class _RegisteredMatchedDirectRowStreamState:
    __slots__ = (
        "catalogue",
        "action",
        "row_binding",
        "discovery_chain",
        "validation_chain",
        "acquisition_discovery",
        "replay_discovery",
        "acquisition_discovery_work",
        "replay_discovery_work",
        "acquisition_validation_stream",
        "replay_validation_stream",
        "acquisition_validation",
        "replay_validation",
        "previous_prefix",
    )

    def __init__(
        self,
        *,
        anchor: final_authority.V072RemoteMainAnchorV1,
        context: prereg.HeldoutPublicGraphContextV2,
        catalogue: observer.HeldoutLegalActionCatalogueV2,
        action: tuple[int, int, int],
    ) -> None:
        self.catalogue = catalogue
        self.action = action
        self.row_binding = observer.observation_row_binding_v2(
            context,
            catalogue,
            action,
        )
        discovery_epoch = observer.support_epoch_identity_v2(
            context,
            self.row_binding,
            ARM,
            0,
        )
        self.discovery_chain = observer.support_epoch_chain_v2(
            context,
            self.row_binding,
            ARM,
            (discovery_epoch,),
        )
        acquisition_discovery_stream = (
            observer.open_heldout_target_transition_stream_v2(
                anchor,
                context,
                catalogue,
                action,
                ARM,
                observer.ObservationLaneV2.DISCOVERY,
                self.discovery_chain,
            )
        )
        replay_discovery_stream = (
            observer.open_heldout_target_transition_stream_v2(
                anchor,
                context,
                catalogue,
                action,
                ARM,
                observer.ObservationLaneV2.DISCOVERY,
                self.discovery_chain,
            )
        )
        self.acquisition_discovery = tuple(
            acquisition_discovery_stream.draw()
            for _ in range(DISCOVERY_DRAWS_PER_ROW)
        )
        self.replay_discovery = tuple(
            replay_discovery_stream.draw()
            for _ in range(DISCOVERY_DRAWS_PER_ROW)
        )
        self.acquisition_discovery_work = (
            acquisition_discovery_stream.work_snapshot()
        )
        self.replay_discovery_work = (
            replay_discovery_stream.work_snapshot()
        )
        if any(
            not _observation_tuple_equal(left, right)
            for left, right in zip(
                self.acquisition_discovery,
                self.replay_discovery,
                strict=True,
            )
        ):
            raise V072RegisteredMatchedDirectInventoryViolation(
                "fresh discovery replay differs from acquisition"
            )
        support_ids = tuple(
            sorted(
                {
                    _recorded_descriptor(item).descriptor_id
                    for item in self.replay_discovery
                }
            )
        )
        validation_epoch = observer.support_epoch_identity_v2(
            context,
            self.row_binding,
            ARM,
            1,
            support_ids,
            discovery_epoch,
        )
        self.validation_chain = observer.support_epoch_chain_v2(
            context,
            self.row_binding,
            ARM,
            (discovery_epoch, validation_epoch),
        )
        self.acquisition_validation_stream = (
            observer.open_heldout_target_transition_stream_v2(
                anchor,
                context,
                catalogue,
                action,
                ARM,
                observer.ObservationLaneV2.VALIDATION,
                self.validation_chain,
            )
        )
        self.replay_validation_stream = (
            observer.open_heldout_target_transition_stream_v2(
                anchor,
                context,
                catalogue,
                action,
                ARM,
                observer.ObservationLaneV2.VALIDATION,
                self.validation_chain,
            )
        )
        self.acquisition_validation: list[
            observer.HeldoutObservedJointTransitionV2
        ] = []
        self.replay_validation: list[
            observer.HeldoutObservedJointTransitionV2
        ] = []
        self.previous_prefix: (
            RegisteredMatchedDirectRowCheckpointPrefixV1 | None
        ) = None


_ACCUMULATOR_SENTINEL = object()


class RegisteredMatchedDirectCompleteInventoryAccumulatorV1:
    """Mutable owner of one complete set of persistent target streams."""

    __slots__ = (
        "_minting_capability",
        "authority_chain",
        "anchor",
        "occurrence_plan",
        "context",
        "public_graph",
        "root_catalogue",
        "child_catalogues",
        "_rows",
        "_last_checkpoint_artifact",
    )

    def __init__(
        self,
        minting_capability: object,
        authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
        anchor: final_authority.V072RemoteMainAnchorV1,
        occurrence_plan: runtime.RegisteredMatchedDirectOccurrencePlanV1,
        context: prereg.HeldoutPublicGraphContextV2,
    ) -> None:
        if minting_capability is not _ACCUMULATOR_SENTINEL:
            raise V072RegisteredMatchedDirectInventoryViolation(
                "matched-direct accumulator cannot be caller-constructed"
            )
        self._minting_capability = minting_capability
        self.authority_chain = authority_chain
        self.anchor = anchor
        self.occurrence_plan = occurrence_plan
        self.context = context
        self.public_graph = (
            public_adapter.HeldoutPublicGraphColdClosureAdapterV1(context)
        )
        root_state = observer.root_state_v2(context)
        self.root_catalogue = observer.legal_action_catalogue_v2(
            context,
            root_state,
            prereg.HORIZON,
        )
        root_rows = [
            _RegisteredMatchedDirectRowStreamState(
                anchor=anchor,
                context=context,
                catalogue=self.root_catalogue,
                action=action,
            )
            for action in self.root_catalogue.actions
        ]
        child_states_by_id: dict[
            str, observer.HeldoutSymbolicGraphStateV2
        ] = {}
        for row in root_rows:
            for item in row.replay_discovery:
                if item.failure or item.terminal:
                    continue
                existing = child_states_by_id.setdefault(
                    item.next_state.state_id,
                    item.next_state,
                )
                if existing != item.next_state:
                    raise V072RegisteredMatchedDirectInventoryViolation(
                        "one discovered child state ID has conflicting bytes"
                    )
        self.child_catalogues = tuple(
            sorted(
                (
                    observer.legal_action_catalogue_v2(
                        context,
                        state,
                        1,
                    )
                    for state in child_states_by_id.values()
                ),
                key=lambda item: item.catalogue_id,
            )
        )
        child_rows = [
            _RegisteredMatchedDirectRowStreamState(
                anchor=anchor,
                context=context,
                catalogue=catalogue,
                action=action,
            )
            for catalogue in self.child_catalogues
            for action in catalogue.actions
        ]
        rows = tuple(
            sorted(
                (*root_rows, *child_rows),
                key=lambda item: item.row_binding.row_binding_id,
            )
        )
        if (
            not rows
            or len(
                {
                    item.row_binding.row_binding_id for item in rows
                }
            )
            != len(rows)
            or len(rows)
            > context.maximum_physical_rows_per_confidence_epoch
        ):
            raise V072RegisteredMatchedDirectInventoryViolation(
                "internally derived complete direct inventory violates its cap"
            )
        self._rows = rows
        self._last_checkpoint_artifact: (
            RegisteredMatchedDirectCompleteInventoryCheckpointV1 | None
        ) = None

    @property
    def stable_row_binding_ids(self) -> tuple[str, ...]:
        return tuple(
            item.row_binding.row_binding_id for item in self._rows
        )

    @property
    def row_count(self) -> int:
        return len(self._rows)

    @property
    def current_checkpoint(self) -> int:
        if self._last_checkpoint_artifact is None:
            return 0
        return self._last_checkpoint_artifact.checkpoint

    @property
    def access_audit(self) -> RegisteredMatchedDirectInventoryAccessAuditV1:
        validation_draws = self.row_count * self.current_checkpoint
        discovery_draws = self.row_count * DISCOVERY_DRAWS_PER_ROW
        return RegisteredMatchedDirectInventoryAccessAuditV1(
            authority_chain_verifications=1,
            public_inventory_calls=2 + len(self.child_catalogues),
            acquisition_stream_opens=2 * self.row_count,
            acquisition_draw_calls=discovery_draws + validation_draws,
            replay_stream_opens=2 * self.row_count,
            replay_draw_calls=discovery_draws + validation_draws,
        )


def open_registered_matched_direct_complete_inventory_accumulator_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    occurrence_plan: runtime.RegisteredMatchedDirectOccurrencePlanV1,
    context: prereg.HeldoutPublicGraphContextV2,
) -> RegisteredMatchedDirectCompleteInventoryAccumulatorV1:
    chain, canonical_anchor, plan, canonical_context = (
        _verify_gate_without_observer_access(
            authority_chain=authority_chain,
            anchor=anchor,
            occurrence_plan=occurrence_plan,
            context=context,
        )
    )
    return RegisteredMatchedDirectCompleteInventoryAccumulatorV1(
        _ACCUMULATOR_SENTINEL,
        chain,
        canonical_anchor,
        plan,
        canonical_context,
    )


def _cold_descriptor(
    item: observer.HeldoutObservedJointTransitionV2,
    adapter: public_adapter.HeldoutPublicGraphColdClosureAdapterV1,
) -> cold.ColdOutcomeDescriptorV1:
    recorded = _recorded_descriptor(item)
    successor = (
        None
        if item.failure or item.terminal
        else adapter.adapt_public_state_v1(
            item.next_state,
            item.remaining_horizon - 1,
        )
    )
    return cold.ColdOutcomeDescriptorV1(
        recorded.descriptor_id,
        failure=item.failure,
        terminal=item.terminal,
        successor_state=successor,
        document=recorded.to_document(),
    )


def _materialize_row_checkpoint(
    *,
    accumulator: RegisteredMatchedDirectCompleteInventoryAccumulatorV1,
    row: _RegisteredMatchedDirectRowStreamState,
    checkpoint: int,
) -> tuple[
    RegisteredMatchedDirectRowCheckpointPrefixV1,
    cold.ColdRowEvidenceV1,
    RegisteredMatchedDirectConfidenceReplayAttestationV1,
    projection.RegisteredConfidenceIntervalSimplexRowProjectionV1,
]:
    acquisition_validation = tuple(row.acquisition_validation)
    replay_validation = tuple(row.replay_validation)
    if (
        len(acquisition_validation) != checkpoint
        or len(replay_validation) != checkpoint
        or tuple(
            item.accepted_draw_index for item in acquisition_validation
        )
        != tuple(range(1, checkpoint + 1))
        or tuple(
            item.accepted_draw_index for item in replay_validation
        )
        != tuple(range(1, checkpoint + 1))
        or any(
            not _observation_tuple_equal(left, right)
            for left, right in zip(
                acquisition_validation,
                replay_validation,
                strict=True,
            )
        )
    ):
        raise V072RegisteredMatchedDirectInventoryViolation(
            "validation checkpoint is not one identical append-only prefix"
        )
    support_ids = tuple(
        sorted(
            {
                _recorded_descriptor(item).descriptor_id
                for item in row.replay_discovery
            }
        )
    )
    validation_ids = tuple(
        _recorded_descriptor(item).descriptor_id
        for item in replay_validation
    )
    novel_ids = tuple(
        sorted(set(validation_ids) - set(support_ids))
    )
    discovery_transcript_id = _content_id(
        "discovery_prefix",
        {
            "schema": (
                "acfqp.v072_registered_matched_direct_discovery_prefix.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "authority_chain_id": accumulator.authority_chain.chain_id,
            "occurrence_plan_id": accumulator.occurrence_plan.plan_id,
            "row_binding_id": row.row_binding.row_binding_id,
            "stream_id": row.acquisition_discovery[0].stream_id,
            "observation_ids": [
                item.observation_id
                for item in row.acquisition_discovery
            ],
            "raw_commitment_ids": [
                item.raw_commitment.commitment_id
                for item in row.acquisition_discovery
            ],
            "stream_work_id": row.acquisition_discovery_work.work_id,
            "draw_count": DISCOVERY_DRAWS_PER_ROW,
            "acquisition_lane": True,
        },
    )
    validation_prefix_id = _content_id(
        "validation_prefix",
        {
            "schema": (
                "acfqp.v072_registered_matched_direct_validation_prefix.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "authority_chain_id": accumulator.authority_chain.chain_id,
            "occurrence_plan_id": accumulator.occurrence_plan.plan_id,
            "row_binding_id": row.row_binding.row_binding_id,
            "stream_id": replay_validation[0].stream_id,
            "checkpoint": checkpoint,
            "observation_ids": [
                item.observation_id for item in replay_validation
            ],
            "descriptor_ids": list(validation_ids),
            "stream_work_id": (
                row.replay_validation_stream.work_snapshot().work_id
            ),
            "execution_lane": "EVALUATION_DETERMINISTIC_FRESH_STREAM_REPLAY",
            "order_preserved": True,
        },
    )
    transcript_id = _content_id(
        "transcript",
        {
            "schema": (
                "acfqp.v072_registered_matched_direct_row_transcript.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "authority_chain_id": accumulator.authority_chain.chain_id,
            "occurrence_plan_id": accumulator.occurrence_plan.plan_id,
            "row_binding_id": row.row_binding.row_binding_id,
            "discovery_transcript_id": discovery_transcript_id,
            "validation_stream_id": acquisition_validation[0].stream_id,
            "validation_observation_ids": [
                item.observation_id
                for item in acquisition_validation
            ],
            "validation_stream_work_id": (
                row.acquisition_validation_stream.work_snapshot().work_id
            ),
            "checkpoint": checkpoint,
            "append_only": True,
            "redrawn_prefix": False,
        },
    )
    replay_core_id = _content_id(
        "replay_core",
        {
            "schema": (
                "acfqp.v072_registered_matched_direct_row_replay_core.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "transcript_id": transcript_id,
            "discovery_transcript_id": discovery_transcript_id,
            "validation_prefix_id": validation_prefix_id,
            "support_epoch_chain_id": row.validation_chain.chain_id,
            "support_descriptor_ids": list(support_ids),
            "validation_novel_descriptor_ids": list(novel_ids),
            "acquisition_discovery_work_id": (
                row.acquisition_discovery_work.work_id
            ),
            "acquisition_validation_work_id": (
                row.acquisition_validation_stream.work_snapshot().work_id
            ),
            "replay_discovery_work_id": row.replay_discovery_work.work_id,
            "replay_validation_work_id": (
                row.replay_validation_stream.work_snapshot().work_id
            ),
            "fresh_stream_replay": True,
        },
    )
    adapter = accumulator.public_graph
    cold_catalogue = adapter.adapt_public_legal_action_catalogue_v1(
        row.catalogue
    )
    matching_actions = tuple(
        action
        for action in cold_catalogue.actions
        if action.semantic_action_id == row.row_binding.row_binding_id
    )
    if len(matching_actions) != 1:
        raise V072RegisteredMatchedDirectInventoryViolation(
            "public row does not map to one cold action"
        )
    support_representative: dict[
        str, observer.HeldoutObservedJointTransitionV2
    ] = {}
    for item in row.replay_discovery:
        support_representative.setdefault(
            _recorded_descriptor(item).descriptor_id,
            item,
        )
    support_descriptors = tuple(
        sorted(
            (
                _cold_descriptor(
                    support_representative[descriptor_id],
                    adapter,
                )
                for descriptor_id in support_ids
            ),
            key=lambda item: item.descriptor_record_id,
        )
    )
    novel_representative: dict[
        str, observer.HeldoutObservedJointTransitionV2
    ] = {}
    for item in replay_validation:
        descriptor_id = _recorded_descriptor(item).descriptor_id
        if descriptor_id in novel_ids:
            novel_representative.setdefault(descriptor_id, item)
    novel_descriptors = tuple(
        sorted(
            (
                _cold_descriptor(
                    novel_representative[descriptor_id],
                    adapter,
                )
                for descriptor_id in novel_ids
            ),
            key=lambda item: item.descriptor_record_id,
        )
    )
    event_counts, semantic_intervals = _confidence_counts_and_intervals(
        support_descriptor_ids=support_ids,
        validation_descriptor_ids=validation_ids,
        checkpoint=checkpoint,
    )
    by_semantic = {
        descriptor_id: (
            event_counts[index],
            semantic_intervals[index],
        )
        for index, descriptor_id in enumerate(support_ids)
    }
    confidence_snapshot_id = _content_id(
        "confidence_snapshot",
        {
            "schema": (
                "acfqp.v072_registered_matched_direct_confidence_snapshot.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "replay_core_id": replay_core_id,
            "checkpoint": checkpoint,
            "support_descriptor_ids": list(support_ids),
            "event_success_counts": list(event_counts),
            "event_checkpoints": [
                item[2] for item in semantic_intervals
            ],
            "row_epoch_beta": _fdoc(prereg.ROW_EPOCH_BETA),
            "source_prior_used_in_confidence": False,
        },
    )
    physical_evidence_id = _content_id(
        "physical",
        {
            "schema": (
                "acfqp.v072_registered_matched_direct_row_"
                "physical_evidence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "anchor_id": accumulator.anchor.anchor_id,
            "occurrence_plan_id": accumulator.occurrence_plan.plan_id,
            "row_binding_id": row.row_binding.row_binding_id,
            "checkpoint": checkpoint,
            "acquisition_observation_ids": [
                item.observation_id
                for item in (
                    *row.acquisition_discovery,
                    *acquisition_validation,
                )
            ],
            "acquisition_raw_commitment_ids": [
                item.raw_commitment.commitment_id
                for item in (
                    *row.acquisition_discovery,
                    *acquisition_validation,
                )
            ],
            "acquisition_discovery_work_id": (
                row.acquisition_discovery_work.work_id
            ),
            "acquisition_validation_work_id": (
                row.acquisition_validation_stream.work_snapshot().work_id
            ),
            "route": ARM,
            "replay_work_charged_separately": True,
        },
    )
    native_work = cold.ColdRowNativeWorkV1(
        acquisition_purpose=(
            cold.ColdRowAcquisitionPurposeV1.MATCHED_DIRECT_CHECKPOINT
        ),
        discovery_draws=DISCOVERY_DRAWS_PER_ROW,
        validation_draws=checkpoint,
        discovery_random_word_calls=(
            row.acquisition_discovery_work.random_word_calls
        ),
        validation_random_word_calls=(
            row.acquisition_validation_stream.work_snapshot()
            .random_word_calls
        ),
        discovery_rejections=(
            row.acquisition_discovery_work.rejection_count
        ),
        validation_rejections=(
            row.acquisition_validation_stream.work_snapshot()
            .rejection_count
        ),
    )
    row_evidence = cold.ColdRowEvidenceV1(
        accumulator.context.context_id,
        cold_catalogue.state,
        row.catalogue.remaining_horizon,
        matching_actions[0],
        support_descriptors,
        novel_descriptors,
        row.validation_chain.leaf.epoch_id,
        confidence_snapshot_id,
        replay_core_id,
        physical_evidence_id,
        native_work,
    )
    intervals_by_semantic = {
        descriptor_id: by_semantic[descriptor_id][1]
        for descriptor_id in support_ids
    }
    counts_by_semantic = {
        descriptor_id: by_semantic[descriptor_id][0]
        for descriptor_id in support_ids
    }
    event_intervals: list[
        projection.RegisteredConfidenceEventIntervalV1
    ] = []
    ordered_counts: list[int] = []
    ordered_intervals: list[tuple[Fraction, Fraction]] = []
    for ordinal, descriptor in enumerate(support_descriptors):
        count = counts_by_semantic[descriptor.semantic_descriptor_id]
        lower, upper, checkpoint_document = intervals_by_semantic[
            descriptor.semantic_descriptor_id
        ]
        confidence_event_id = _content_id(
            "confidence_event",
            {
                "schema": (
                    "acfqp.v072_registered_matched_direct_"
                    "confidence_event.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "confidence_snapshot_id": confidence_snapshot_id,
                "event_ordinal": ordinal,
                "event_kind": "SUPPORT",
                "semantic_descriptor_id": (
                    descriptor.semantic_descriptor_id
                ),
                "descriptor_record_id": (
                    descriptor.descriptor_record_id
                ),
                "success_count": count,
                "checkpoint": checkpoint_document,
            },
        )
        event_intervals.append(
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
    other_count = event_counts[-1]
    other_lower, other_upper, other_checkpoint = semantic_intervals[-1]
    other_ordinal = len(support_descriptors)
    other_event_id = _content_id(
        "confidence_event",
        {
            "schema": (
                "acfqp.v072_registered_matched_direct_confidence_event.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "confidence_snapshot_id": confidence_snapshot_id,
            "event_ordinal": other_ordinal,
            "event_kind": "OTHER",
            "semantic_descriptor_id": None,
            "descriptor_record_id": None,
            "success_count": other_count,
            "checkpoint": other_checkpoint,
        },
    )
    event_intervals.append(
        projection.RegisteredConfidenceEventIntervalV1(
            other_event_id,
            other_ordinal,
            projection.RegisteredConfidenceEventKindV1.OTHER,
            None,
            other_lower,
            other_upper,
        )
    )
    ordered_counts.append(other_count)
    ordered_intervals.append((other_lower, other_upper))
    event_interval_tuple = tuple(event_intervals)
    attestation = RegisteredMatchedDirectConfidenceReplayAttestationV1(
        _CONFIDENCE_ATTESTATION_SENTINEL,
        accumulator.authority_chain.chain_id,
        accumulator.anchor.anchor_id,
        accumulator.anchor.claim.final_preregistration_id,
        accumulator.occurrence_plan.plan_id,
        transcript_id,
        discovery_transcript_id,
        validation_prefix_id,
        row_evidence.row_evidence_id,
        row.validation_chain.leaf.epoch_id,
        support_ids,
        tuple(
            item.descriptor_record_id for item in support_descriptors
        ),
        tuple(
            item.descriptor_record_id for item in novel_descriptors
        ),
        tuple(item.event_id for item in event_interval_tuple),
        tuple(ordered_counts),
        tuple(ordered_intervals),
        checkpoint,
        2,
        DISCOVERY_DRAWS_PER_ROW + checkpoint,
    )
    confidence_authority = (
        projection.mint_registered_target_confidence_projection_authority_v1(
            replay_attestation=attestation,
            row_evidence=row_evidence,
            event_intervals=event_interval_tuple,
        )
    )
    row_projection = projection.project_registered_target_confidence_row_v1(
        anchor=accumulator.anchor,
        confidence_authority=confidence_authority,
    )
    prefix = RegisteredMatchedDirectRowCheckpointPrefixV1(
        row.row_binding.row_binding_id,
        row.catalogue.catalogue_id,
        row.catalogue.remaining_horizon,
        checkpoint,
        row.acquisition_discovery[0].stream_id,
        acquisition_validation[0].stream_id,
        row.replay_discovery[0].stream_id,
        replay_validation[0].stream_id,
        (
            None
            if row.previous_prefix is None
            else row.previous_prefix.prefix_id
        ),
        discovery_transcript_id,
        validation_prefix_id,
        tuple(item.observation_id for item in acquisition_validation),
        tuple(item.observation_id for item in replay_validation),
    )
    return prefix, row_evidence, attestation, row_projection


def acquire_registered_matched_direct_complete_inventory_checkpoint_v1(
    *,
    accumulator: RegisteredMatchedDirectCompleteInventoryAccumulatorV1,
    checkpoint: int,
) -> RegisteredMatchedDirectCompleteInventoryCheckpointV1:
    """Append exactly the next suffix on every row and freeze one checkpoint."""

    if (
        type(accumulator)
        is not RegisteredMatchedDirectCompleteInventoryAccumulatorV1
        or accumulator._minting_capability is not _ACCUMULATOR_SENTINEL
        or checkpoint not in CHECKPOINTS
    ):
        raise V072RegisteredMatchedDirectInventoryViolation(
            "direct checkpoint requires the exact internally minted accumulator"
        )
    next_index = (
        0
        if accumulator.current_checkpoint == 0
        else CHECKPOINTS.index(accumulator.current_checkpoint) + 1
    )
    if next_index >= len(CHECKPOINTS) or checkpoint != CHECKPOINTS[next_index]:
        raise V072RegisteredMatchedDirectInventoryViolation(
            "direct checkpoints must be acquired synchronously without skip"
        )
    previous_checkpoint = accumulator.current_checkpoint
    delta = checkpoint - previous_checkpoint
    for row in accumulator._rows:
        new_acquisition = tuple(
            row.acquisition_validation_stream.draw()
            for _ in range(delta)
        )
        new_replay = tuple(
            row.replay_validation_stream.draw()
            for _ in range(delta)
        )
        if any(
            not _observation_tuple_equal(left, right)
            for left, right in zip(
                new_acquisition,
                new_replay,
                strict=True,
            )
        ):
            raise V072RegisteredMatchedDirectInventoryViolation(
                "fresh validation suffix replay differs"
            )
        row.acquisition_validation.extend(new_acquisition)
        row.replay_validation.extend(new_replay)
    materialized = tuple(
        _materialize_row_checkpoint(
            accumulator=accumulator,
            row=row,
            checkpoint=checkpoint,
        )
        for row in accumulator._rows
    )
    prefixes = tuple(item[0] for item in materialized)
    row_evidence = tuple(
        sorted(
            (item[1] for item in materialized),
            key=lambda item: item.row_evidence_id,
        )
    )
    confidence_attestations = tuple(
        sorted(
            (item[2] for item in materialized),
            key=lambda item: item.row_evidence_id,
        )
    )
    row_projections = tuple(
        sorted(
            (item[3] for item in materialized),
            key=lambda item: item.projection_id,
        )
    )
    cap_registry = cold.registered_confirmatory_cold_h2_cap_registry_v1()
    cap_evidence = cap_registry.evidence_for_context(
        accumulator.context.context_id
    )
    closure_bundle = cold.freeze_v072_cold_h2_closure_v1(
        public_graph=accumulator.public_graph,
        row_evidence=row_evidence,
        logical_occurrence_id=accumulator.occurrence_plan.plan_id,
        arm=ARM,
        cap_evidence=cap_evidence,
    )
    closure_verification = (
        closure_verify.verify_v072_cold_h2_closure_independently_v1(
            public_graph=accumulator.public_graph,
            authoritative_row_evidence=row_evidence,
            claimed=closure_bundle,
        )
    )
    direct_snapshot = build_registered_matched_direct_cold_snapshot_v1(
        closure_bundle=closure_bundle,
        row_projections=row_projections,
    )
    model_attestation = (
        verify_registered_matched_direct_cold_snapshot_independently_v1(
            snapshot=direct_snapshot
        )
    )
    row_count = accumulator.row_count
    work = RegisteredMatchedDirectCheckpointWorkV1(
        checkpoint,
        previous_checkpoint,
        row_count,
        row_count * DISCOVERY_DRAWS_PER_ROW,
        row_count * delta,
        row_count * checkpoint,
        row_count * (DISCOVERY_DRAWS_PER_ROW + checkpoint),
        row_count * DISCOVERY_DRAWS_PER_ROW,
        row_count * delta,
        row_count * checkpoint,
        row_count * (DISCOVERY_DRAWS_PER_ROW + checkpoint),
        2 * row_count,
        2 * row_count,
    )
    artifact = RegisteredMatchedDirectCompleteInventoryCheckpointV1(
        accumulator.authority_chain.chain_id,
        accumulator.anchor.anchor_id,
        accumulator.anchor.claim.final_preregistration_id,
        accumulator.occurrence_plan.plan_id,
        accumulator.context.context_id,
        checkpoint,
        (
            None
            if accumulator._last_checkpoint_artifact is None
            else accumulator._last_checkpoint_artifact.checkpoint_id
        ),
        accumulator.stable_row_binding_ids,
        prefixes,
        row_evidence,
        confidence_attestations,
        row_projections,
        closure_bundle,
        closure_verification,
        direct_snapshot,
        model_attestation,
        work,
    )
    for row, prefix in zip(
        accumulator._rows,
        prefixes,
        strict=True,
    ):
        row.previous_prefix = prefix
    accumulator._last_checkpoint_artifact = artifact
    return artifact


def verify_registered_matched_direct_complete_inventory_checkpoint_v1(
    *,
    checkpoint_artifact: (
        RegisteredMatchedDirectCompleteInventoryCheckpointV1
    ),
) -> RegisteredMatchedDirectCompleteInventoryCheckpointV1:
    """Replay all deterministic closure/model obligations without target access."""

    if (
        type(checkpoint_artifact)
        is not RegisteredMatchedDirectCompleteInventoryCheckpointV1
    ):
        raise V072RegisteredMatchedDirectInventoryViolation(
            "direct checkpoint verifier requires the exact artifact type"
        )
    context = next(
        (
            item
            for item in prereg.registered_heldout_public_contexts_v2()
            if item.context_id == checkpoint_artifact.context_id
        ),
        None,
    )
    if type(context) is not prereg.HeldoutPublicGraphContextV2:
        raise V072RegisteredMatchedDirectInventoryViolation(
            "direct checkpoint context is outside the registry"
        )
    graph = public_adapter.HeldoutPublicGraphColdClosureAdapterV1(context)
    replayed_closure = (
        closure_verify.verify_v072_cold_h2_closure_independently_v1(
            public_graph=graph,
            authoritative_row_evidence=checkpoint_artifact.row_evidence,
            claimed=checkpoint_artifact.closure_bundle,
        )
    )
    replayed_model = (
        verify_registered_matched_direct_cold_snapshot_independently_v1(
            snapshot=checkpoint_artifact.direct_snapshot
        )
    )
    if (
        replayed_closure != checkpoint_artifact.closure_verification
        or replayed_model != checkpoint_artifact.model_attestation
    ):
        raise V072RegisteredMatchedDirectInventoryViolation(
            "direct checkpoint deterministic verifier replay differs"
        )
    return checkpoint_artifact


@dataclass(frozen=True, slots=True)
class RegisteredMatchedDirectCompleteInventoryRunV1:
    occurrence_plan_id: str
    checkpoints: tuple[
        RegisteredMatchedDirectCompleteInventoryCheckpointV1, ...
    ]
    final_acquisition_sample_total: int
    final_deterministic_verifier_replay_total: int
    _run_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.occurrence_plan_id, "direct inventory run occurrence")
        if (
            type(self.checkpoints) is not tuple
            or len(self.checkpoints) != len(CHECKPOINTS)
            or tuple(item.checkpoint for item in self.checkpoints)
            != CHECKPOINTS
            or any(
                type(item)
                is not RegisteredMatchedDirectCompleteInventoryCheckpointV1
                or item.occurrence_plan_id != self.occurrence_plan_id
                for item in self.checkpoints
            )
            or any(
                current.previous_checkpoint_id != previous.checkpoint_id
                or current.stable_row_binding_ids
                != previous.stable_row_binding_ids
                or tuple(
                    item.previous_prefix_id
                    for item in current.row_prefixes
                )
                != tuple(
                    item.prefix_id for item in previous.row_prefixes
                )
                or any(
                    current_prefix
                    .acquisition_validation_observation_ids[
                        : previous.checkpoint
                    ]
                    != previous_prefix
                    .acquisition_validation_observation_ids
                    or current_prefix
                    .replay_validation_observation_ids[
                        : previous.checkpoint
                    ]
                    != previous_prefix
                    .replay_validation_observation_ids
                    for previous_prefix, current_prefix in zip(
                        previous.row_prefixes,
                        current.row_prefixes,
                        strict=True,
                    )
                )
                for previous, current in zip(
                    self.checkpoints[:-1],
                    self.checkpoints[1:],
                    strict=True,
                )
            )
            or self.final_acquisition_sample_total
            != self.checkpoints[-1].work.acquisition_sample_total
            or self.final_deterministic_verifier_replay_total
            != (
                self.checkpoints[-1]
                .work.deterministic_verifier_replay_total
            )
        ):
            raise V072RegisteredMatchedDirectInventoryViolation(
                "direct run skipped, replaced, or summed checkpoint prefixes"
            )
        object.__setattr__(
            self,
            "_run_id",
            _content_id("run", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_matched_direct_complete_"
                "inventory_run.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_plan_id": self.occurrence_plan_id,
            "checkpoint_ids": [
                item.checkpoint_id for item in self.checkpoints
            ],
            "checkpoint_order": list(CHECKPOINTS),
            "final_acquisition_sample_total": (
                self.final_acquisition_sample_total
            ),
            "final_deterministic_verifier_replay_total": (
                self.final_deterministic_verifier_replay_total
            ),
            "checkpoint_totals_summed": False,
            "crn_draw_discount": 0,
        }

    @property
    def run_id(self) -> str:
        return self._run_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "checkpoints": [
                item.to_document() for item in self.checkpoints
            ],
            "run_id": self.run_id,
        }


def run_registered_matched_direct_complete_inventory_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    occurrence_plan: runtime.RegisteredMatchedDirectOccurrencePlanV1,
    context: prereg.HeldoutPublicGraphContextV2,
) -> RegisteredMatchedDirectCompleteInventoryRunV1:
    accumulator = (
        open_registered_matched_direct_complete_inventory_accumulator_v1(
            authority_chain=authority_chain,
            anchor=anchor,
            occurrence_plan=occurrence_plan,
            context=context,
        )
    )
    artifacts = tuple(
        acquire_registered_matched_direct_complete_inventory_checkpoint_v1(
            accumulator=accumulator,
            checkpoint=checkpoint,
        )
        for checkpoint in CHECKPOINTS
    )
    return RegisteredMatchedDirectCompleteInventoryRunV1(
        occurrence_plan.plan_id,
        artifacts,
        artifacts[-1].work.acquisition_sample_total,
        artifacts[-1].work.deterministic_verifier_replay_total,
    )


@dataclass(frozen=True, slots=True)
class RegistrationDisjointMatchedDirectPrefixV1:
    row_binding_id: str
    validation_stream_id: str
    checkpoint: int
    appended_start_index: int
    appended_end_index: int
    previous_prefix_id: str | None
    cumulative_prefix_digest: str
    _prefix_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.row_binding_id,
            self.validation_stream_id,
            self.cumulative_prefix_digest,
        ):
            _cid(value, "registration-disjoint prefix identity")
        if self.previous_prefix_id is not None:
            _cid(self.previous_prefix_id, "disjoint prior prefix")
        previous_checkpoint = (
            0
            if self.checkpoint == CHECKPOINTS[0]
            else CHECKPOINTS[CHECKPOINTS.index(self.checkpoint) - 1]
        )
        if (
            self.checkpoint not in CHECKPOINTS
            or self.appended_start_index != previous_checkpoint + 1
            or self.appended_end_index != self.checkpoint
            or (
                previous_checkpoint == 0
                and self.previous_prefix_id is not None
            )
            or (
                previous_checkpoint > 0
                and self.previous_prefix_id is None
            )
        ):
            raise V072RegisteredMatchedDirectInventoryViolation(
                "registration-disjoint prefix skipped or redrew samples"
            )
        object.__setattr__(
            self,
            "_prefix_id",
            _content_id("disjoint_prefix", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_matched_direct_prefix.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "row_binding_id": self.row_binding_id,
            "validation_stream_id": self.validation_stream_id,
            "checkpoint": self.checkpoint,
            "appended_start_index": self.appended_start_index,
            "appended_end_index": self.appended_end_index,
            "previous_prefix_id": self.previous_prefix_id,
            "cumulative_prefix_digest": self.cumulative_prefix_digest,
            "same_stream_suffix_append": True,
            "registered_target_evidence": False,
        }

    @property
    def prefix_id(self) -> str:
        return self._prefix_id


@dataclass(frozen=True, slots=True)
class RegistrationDisjointMatchedDirectCheckpointV1:
    checkpoint: int
    stable_row_binding_ids: tuple[str, ...]
    prefixes: tuple[RegistrationDisjointMatchedDirectPrefixV1, ...]
    work: RegisteredMatchedDirectCheckpointWorkV1
    _checkpoint_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self.checkpoint not in CHECKPOINTS
            or self.stable_row_binding_ids
            != tuple(sorted(set(self.stable_row_binding_ids)))
            or type(self.prefixes) is not tuple
            or tuple(item.row_binding_id for item in self.prefixes)
            != self.stable_row_binding_ids
            or any(
                type(item)
                is not RegistrationDisjointMatchedDirectPrefixV1
                or item.checkpoint != self.checkpoint
                for item in self.prefixes
            )
            or type(self.work)
            is not RegisteredMatchedDirectCheckpointWorkV1
            or self.work.checkpoint != self.checkpoint
            or self.work.row_count != len(self.stable_row_binding_ids)
        ):
            raise V072RegisteredMatchedDirectInventoryViolation(
                "registration-disjoint checkpoint inventory is incomplete"
            )
        object.__setattr__(
            self,
            "_checkpoint_id",
            _content_id("disjoint_checkpoint", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_matched_direct_"
                "checkpoint.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "checkpoint": self.checkpoint,
            "stable_row_binding_ids": list(self.stable_row_binding_ids),
            "prefix_ids": [item.prefix_id for item in self.prefixes],
            "work_id": self.work.work_id,
            "registered_target_evidence": False,
        }

    @property
    def checkpoint_id(self) -> str:
        return self._checkpoint_id


@dataclass(frozen=True, slots=True)
class RegistrationDisjointMatchedDirectRunV1:
    checkpoints: tuple[
        RegistrationDisjointMatchedDirectCheckpointV1, ...
    ]
    final_acquisition_sample_total: int
    sum_of_checkpoint_totals_charged: bool = False
    crn_draw_discount: int = 0
    _run_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.checkpoints) is not tuple
            or tuple(item.checkpoint for item in self.checkpoints)
            != CHECKPOINTS
            or any(
                type(item)
                is not RegistrationDisjointMatchedDirectCheckpointV1
                for item in self.checkpoints
            )
            or any(
                current.stable_row_binding_ids
                != previous.stable_row_binding_ids
                or tuple(
                    item.previous_prefix_id for item in current.prefixes
                )
                != tuple(
                    item.prefix_id for item in previous.prefixes
                )
                or tuple(
                    item.validation_stream_id for item in current.prefixes
                )
                != tuple(
                    item.validation_stream_id for item in previous.prefixes
                )
                for previous, current in zip(
                    self.checkpoints[:-1],
                    self.checkpoints[1:],
                    strict=True,
                )
            )
            or self.final_acquisition_sample_total
            != self.checkpoints[-1].work.acquisition_sample_total
            or self.sum_of_checkpoint_totals_charged is not False
            or self.crn_draw_discount != 0
        ):
            raise V072RegisteredMatchedDirectInventoryViolation(
                "registration-disjoint run redrew or summed checkpoint work"
            )
        object.__setattr__(
            self,
            "_run_id",
            _content_id("disjoint_run", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_matched_direct_run.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "checkpoint_ids": [
                item.checkpoint_id for item in self.checkpoints
            ],
            "final_acquisition_sample_total": (
                self.final_acquisition_sample_total
            ),
            "sum_of_checkpoint_totals_charged": False,
            "crn_draw_discount": 0,
            "registered_target_evidence": False,
        }

    @property
    def run_id(self) -> str:
        return self._run_id


def run_registration_disjoint_complete_inventory_schedule_v1(
) -> RegistrationDisjointMatchedDirectRunV1:
    """Exercise the exact prefix/work mathematics without target authority."""

    # The row inventory is derived internally from a frozen synthetic public
    # root/child action shape.  No caller supplies row IDs or row counts.
    semantic_rows = (
        ("ROOT", "ACTION_A"),
        ("ROOT", "ACTION_B"),
        ("CHILD_1", "ACTION_A"),
        ("CHILD_1", "ACTION_B"),
        ("CHILD_2", "ACTION_A"),
    )
    row_ids = tuple(
        sorted(
            _content_id(
                "disjoint_stream",
                {
                    "schema": (
                        "acfqp.v072_registration_disjoint_matched_direct_"
                        "row.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "state_key": state,
                    "action_key": action,
                    "registered_target_evidence": False,
                },
            )
            for state, action in semantic_rows
        )
    )
    stream_by_row = {
        row_id: _content_id(
            "disjoint_stream",
            {
                "schema": (
                    "acfqp.v072_registration_disjoint_matched_direct_"
                    "validation_stream.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "row_binding_id": row_id,
                "lane": "VALIDATION",
                "registered_target_evidence": False,
            },
        )
        for row_id in row_ids
    }
    prior: dict[str, RegistrationDisjointMatchedDirectPrefixV1] = {}
    checkpoint_artifacts = []
    previous_checkpoint = 0
    for checkpoint in CHECKPOINTS:
        prefixes = []
        for row_id in row_ids:
            parent = prior.get(row_id)
            digest = _content_id(
                "disjoint_prefix",
                {
                    "schema": (
                        "acfqp.v072_registration_disjoint_matched_direct_"
                        "cumulative_token_digest.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "row_binding_id": row_id,
                    "validation_stream_id": stream_by_row[row_id],
                    "parent_digest": (
                        None
                        if parent is None
                        else parent.cumulative_prefix_digest
                    ),
                    "appended_indices": {
                        "start": previous_checkpoint + 1,
                        "end": checkpoint,
                    },
                    "deterministic_token_rule": (
                        "SHA256_STREAM_ID_AND_ACCEPTED_DRAW_INDEX"
                    ),
                },
            )
            prefix = RegistrationDisjointMatchedDirectPrefixV1(
                row_id,
                stream_by_row[row_id],
                checkpoint,
                previous_checkpoint + 1,
                checkpoint,
                None if parent is None else parent.prefix_id,
                digest,
            )
            prefixes.append(prefix)
            prior[row_id] = prefix
        row_count = len(row_ids)
        work = RegisteredMatchedDirectCheckpointWorkV1(
            checkpoint,
            previous_checkpoint,
            row_count,
            row_count * DISCOVERY_DRAWS_PER_ROW,
            row_count * (checkpoint - previous_checkpoint),
            row_count * checkpoint,
            row_count * (DISCOVERY_DRAWS_PER_ROW + checkpoint),
            row_count * DISCOVERY_DRAWS_PER_ROW,
            row_count * (checkpoint - previous_checkpoint),
            row_count * checkpoint,
            row_count * (DISCOVERY_DRAWS_PER_ROW + checkpoint),
            2 * row_count,
            2 * row_count,
        )
        checkpoint_artifacts.append(
            RegistrationDisjointMatchedDirectCheckpointV1(
                checkpoint,
                row_ids,
                tuple(prefixes),
                work,
            )
        )
        previous_checkpoint = checkpoint
    artifacts = tuple(checkpoint_artifacts)
    return RegistrationDisjointMatchedDirectRunV1(
        artifacts,
        artifacts[-1].work.acquisition_sample_total,
    )


__all__ = [
    "ARM",
    "CHECKPOINTS",
    "CRN_DRAW_DISCOUNT",
    "DISCOVERY_DRAWS_PER_ROW",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_COMPLETE_INVENTORY_STATUS",
    "RegisteredMatchedDirectCheckpointWorkV1",
    "RegisteredMatchedDirectColdSnapshotV1",
    "RegisteredMatchedDirectCompleteInventoryAccumulatorV1",
    "RegisteredMatchedDirectCompleteInventoryCheckpointV1",
    "RegisteredMatchedDirectCompleteInventoryRunV1",
    "RegisteredMatchedDirectConfidenceReplayAttestationV1",
    "RegisteredMatchedDirectInventoryAccessAuditV1",
    "RegisteredMatchedDirectInventoryGateLockedV1",
    "RegisteredMatchedDirectModelIndependentAttestationV1",
    "RegisteredMatchedDirectRowCheckpointPrefixV1",
    "RegistrationDisjointMatchedDirectCheckpointV1",
    "RegistrationDisjointMatchedDirectPrefixV1",
    "RegistrationDisjointMatchedDirectRunV1",
    "SCHEMA_VERSION",
    "V072RegisteredMatchedDirectInventoryViolation",
    "ZERO_TARGET_ACCESS_AUDIT",
    "acquire_registered_matched_direct_complete_inventory_checkpoint_v1",
    "build_registered_matched_direct_cold_snapshot_v1",
    "open_registered_matched_direct_complete_inventory_accumulator_v1",
    "run_registered_matched_direct_complete_inventory_v1",
    "run_registration_disjoint_complete_inventory_schedule_v1",
    "verify_registered_matched_direct_cold_snapshot_independently_v1",
    "verify_registered_matched_direct_complete_inventory_checkpoint_v1",
]
