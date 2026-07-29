"""Independent verifier for V0-072 confidence-to-row projections.

The verifier duplicates all projection formulas and content domains.  It does
not invoke the production projector, row/destination derivation helpers, or
any transition kernel.  The V2 confidence snapshot is first independently
verified, after which destination categories, exact event intervals, the
single adversarial OTHER mass, robust planner IDs, and projection identity are
recomputed from frozen bytes.
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
from acfqp import partial_support_confidence_v2 as confidence
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import v072_confidence_row_projection_v1 as projection
import acfqp.transfer_guided_acquisition_preregistration_v1 as prereg


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v072_confidence_row_projection_independent_verifier_v0"
ROLE = (
    "DEVELOPMENT_SYNTHETIC_DRY_RUN_NOT_REGISTERED_TARGET_TAPE"
)

PROJECTION_DOMAINS = {
    "state": "acfqp:v072-projection-public-state:v1",
    "action": "acfqp:v072-projection-public-action:v1",
    "row_binding": "acfqp:v072-projection-public-row-binding:v1",
    "successor_state": "acfqp:v072-projection-successor-state:v1",
    "destination": "acfqp:v072-projection-observed-destination:v1",
    "other": "acfqp:v072-projection-adversarial-other-destination:v1",
    "event_projection": (
        "acfqp:v072-confidence-event-destination-projection:v1"
    ),
    "projection": "acfqp:v072-confidence-interval-row-projection:v1",
}
CONFIDENCE_DOMAINS = {
    "row": "acfqp:v072-confidence-physical-row-binding:v2",
    "profile": "acfqp:v072-partial-support-confidence-profile:v2",
    "row_epoch": "acfqp:v072-row-confidence-epoch-authority:v2",
    "snapshot": "acfqp:v072-partial-support-confidence-snapshot:v2",
}
ROBUST_DOMAINS = {
    "destination": "acfqp:partial-support-destination:v1",
    "mass": "acfqp:partial-support-interval-mass:v1",
    "row": "acfqp:partial-support-interval-simplex-row:v1",
}
VERIFICATION_DOMAIN = (
    "acfqp:v072-confidence-row-projection-independent-verification:v1"
)


class V072ConfidenceRowProjectionIndependentVerificationFailure(ValueError):
    """The projection differs from an independent exact reconstruction."""


def _hash(
    domain: str,
    payload: Mapping[str, Any],
) -> str:
    try:
        body = canonical_json_bytes(dict(payload))
    except (TypeError, ValueError) as error:
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            str(error)
        ) from error
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + body
    ).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            f"{field_name} must be one full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _verify_row_binding(
    binding: projection.PublicStateActionRowBindingV1,
) -> tuple[str, str, str, Fraction]:
    if type(binding) is not projection.PublicStateActionRowBindingV1:
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "public row binding has a noncanonical concrete type"
        )
    if (
        binding.arm not in prereg.ARM_ORDER
        or type(binding.state_ranks) is not tuple
        or not binding.state_ranks
        or binding.remaining_horizon not in (1, 2)
        or binding.rank_cap != 4
        or binding.query_horizon != 2
        or binding.rank_profile != projection.DEVELOPMENT_RANK_PROFILE
        or binding.role != ROLE
        or binding.registered_target_evidence is not False
    ):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "public row binding leaves the development profile"
        )
    first, second, survivor = binding.action
    if (
        min(first, second, survivor) < 0
        or max(first, second, survivor) >= len(binding.state_ranks)
        or first == second
        or survivor not in (first, second)
        or binding.state_ranks[first] <= 0
        or binding.state_ranks[first] != binding.state_ranks[second]
    ):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "public action is not an equal-rank survivor merge"
        )
    state_payload = {
        "schema": "acfqp.v072_projection_public_state.v1",
        "schema_version": projection.SCHEMA_VERSION,
        "context_id": binding.context_id,
        "state_ranks": list(binding.state_ranks),
        "remaining_horizon": binding.remaining_horizon,
        "role": ROLE,
    }
    state_id = _hash(PROJECTION_DOMAINS["state"], state_payload)
    merge_rank = binding.state_ranks[first]
    reward = (
        Fraction(2 ** (merge_rank + 1), 2 ** (binding.rank_cap + 1))
        / binding.query_horizon
    )
    action_payload = {
        "schema": "acfqp.v072_projection_public_action.v1",
        "schema_version": projection.SCHEMA_VERSION,
        "context_id": binding.context_id,
        "state_id": state_id,
        "remaining_horizon": binding.remaining_horizon,
        "action": list(binding.action),
        "merge_rank": merge_rank,
        "exact_row_reward": _fdoc(reward),
        "role": ROLE,
    }
    action_id = _hash(PROJECTION_DOMAINS["action"], action_payload)
    row_payload = {
        "schema": "acfqp.v072_projection_public_row_binding.v1",
        "schema_version": projection.SCHEMA_VERSION,
        "proposed_contract_version": projection.PROPOSED_CONTRACT_VERSION,
        "profile_key": projection.PROFILE_KEY,
        "preregistration_id": binding.preregistration_id,
        "context_id": binding.context_id,
        "arm": binding.arm,
        "physical_row_id": binding.physical_row_id,
        "confidence_row_binding_id": binding.confidence_row_binding_id,
        "state_id": state_id,
        "remaining_horizon": binding.remaining_horizon,
        "action_id": action_id,
        "rank_cap": 4,
        "query_horizon": 2,
        "rank_profile": projection.DEVELOPMENT_RANK_PROFILE,
        "exact_row_reward": _fdoc(reward),
        "role": ROLE,
        "registered_target_evidence": False,
    }
    row_binding_id = _hash(
        PROJECTION_DOMAINS["row_binding"], row_payload
    )
    if (
        binding.state_id != state_id
        or binding.action_id != action_id
        or binding.row_binding_id != row_binding_id
        or binding.exact_row_reward != reward
    ):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "public state/action/reward/row IDs do not replay"
        )
    return state_id, action_id, row_binding_id, reward


def _descriptor_expected(
    descriptor: confidence.OpaqueOutcomeDescriptorV2,
    binding: projection.PublicStateActionRowBindingV1,
    row_binding_id: str,
) -> tuple[
    robust.DestinationCategory,
    str | None,
    str,
    str,
    dict[str, Any],
]:
    if type(descriptor) is not confidence.OpaqueOutcomeDescriptorV2:
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "support descriptor has a noncanonical type"
        )
    document = descriptor.document
    next_state = document.get("next_state")
    if not isinstance(next_state, Mapping):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "support descriptor lacks next-state semantics"
        )
    ranks = next_state.get("ranks")
    next_failure = next_state.get("failure")
    failure = document.get("failure")
    terminal = document.get("terminal")
    reward = document.get("realized_row_reward")
    if (
        type(ranks) not in (tuple, list)
        or len(ranks) != len(binding.state_ranks)
        or any(
            type(rank) is not int or not 0 <= rank <= binding.rank_cap
            for rank in ranks
        )
        or type(next_failure) is not bool
        or type(failure) is not bool
        or failure != next_failure
        or type(terminal) is not bool
        or reward != binding.exact_row_reward
        or (
            "descriptor_id" in document
            and document["descriptor_id"] != descriptor.descriptor_id
        )
    ):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "support descriptor semantics are inconsistent"
        )
    if binding.remaining_horizon == 2:
        if terminal != failure:
            raise V072ConfidenceRowProjectionIndependentVerificationFailure(
                "H2 terminal/failure semantics changed"
            )
    elif terminal is not True:
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "H1 successor must terminate"
        )
    if failure:
        category = robust.DestinationCategory.FAILURE
    elif binding.remaining_horizon == 1:
        category = robust.DestinationCategory.SUCCESS_TERMINAL
    else:
        category = robust.DestinationCategory.ACTIVE_STATE
    state_payload = {
        "schema": "acfqp.v072_projection_successor_state.v1",
        "schema_version": projection.SCHEMA_VERSION,
        "context_id": binding.context_id,
        "ranks": list(ranks),
        "failure": failure,
        "remaining_horizon": binding.remaining_horizon - 1,
        "source_descriptor_id": descriptor.descriptor_id,
        "role": ROLE,
    }
    semantic_state_id = _hash(
        PROJECTION_DOMAINS["successor_state"], state_payload
    )
    state_id = (
        semantic_state_id
        if category is robust.DestinationCategory.ACTIVE_STATE
        else None
    )
    destination_payload = {
        "schema": "acfqp.v072_projection_observed_destination.v1",
        "schema_version": projection.SCHEMA_VERSION,
        "row_binding_id": row_binding_id,
        "descriptor_id": descriptor.descriptor_id,
        "descriptor_binding_id": descriptor.binding_id,
        "category": category.value,
        "state_id": state_id,
        "semantic_successor_state_id": semantic_state_id,
    }
    destination_id = _hash(
        PROJECTION_DOMAINS["destination"], destination_payload
    )
    return (
        category,
        state_id,
        semantic_state_id,
        destination_id,
        destination_payload,
    )


def _other_expected(
    binding: projection.PublicStateActionRowBindingV1,
    state_id: str,
    action_id: str,
    row_binding_id: str,
) -> tuple[str, dict[str, Any]]:
    payload = {
        "schema": (
            "acfqp.v072_projection_adversarial_other_destination.v1"
        ),
        "schema_version": projection.SCHEMA_VERSION,
        "context_id": binding.context_id,
        "row_binding_id": row_binding_id,
        "state_id": state_id,
        "action_id": action_id,
        "remaining_horizon": binding.remaining_horizon,
        "category": robust.DestinationCategory.OTHER.value,
        "joint_unknown_event_count": 1,
        "failure_value": _fdoc(Fraction(1)),
        "continuation_reward_lower": _fdoc(Fraction(0)),
    }
    return _hash(PROJECTION_DOMAINS["other"], payload), payload


def _mass_expected(
    destination_id: str,
    lower: Fraction,
    upper: Fraction,
) -> tuple[str, dict[str, Any]]:
    payload = {
        "schema": "acfqp.partial_support_interval_mass.v1",
        "schema_version": robust.SCHEMA_VERSION,
        "destination_id": destination_id,
        "lower": _fdoc(lower),
        "upper": _fdoc(upper),
    }
    return _hash(ROBUST_DOMAINS["mass"], payload), payload


def _registered_destination_expected(
    destination_id: str,
    category: robust.DestinationCategory,
    state_id: str | None,
) -> tuple[str, dict[str, Any]]:
    payload = {
        "schema": "acfqp.partial_support_destination.v1",
        "schema_version": robust.SCHEMA_VERSION,
        "destination_id": destination_id,
        "category": category.value,
        "state_id": state_id,
    }
    return _hash(ROBUST_DOMAINS["destination"], payload), payload


def _verify_observation_prefix(
    observations: tuple[confidence.OpaqueConfidenceObservationV2, ...],
    *,
    row: confidence.ConfidencePhysicalRowBindingV2,
    support_chain_id: str,
    stream_id: str,
    lane: confidence.ConfidenceObservationLaneV2,
) -> None:
    if (
        type(observations) is not tuple
        or not observations
        or any(
            type(item) is not confidence.OpaqueConfidenceObservationV2
            for item in observations
        )
        or tuple(item.sequence_index for item in observations)
        != tuple(range(1, len(observations) + 1))
        or len({item.sample_id for item in observations})
        != len(observations)
        or any(
            item.preregistration_id != row.preregistration_id
            or item.context_id != row.context_id
            or item.arm != row.arm
            or item.physical_row_id != row.physical_row_id
            or item.support_epoch_chain_id != support_chain_id
            or item.stream_id != stream_id
            or item.lane is not lane
            for item in observations
        )
    ):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "confidence observation prefix is gapped or transplanted"
        )


def _representative_descriptors(
    observations: tuple[confidence.OpaqueConfidenceObservationV2, ...],
) -> tuple[confidence.OpaqueOutcomeDescriptorV2, ...]:
    by_id: dict[str, confidence.OpaqueOutcomeDescriptorV2] = {}
    for observation in observations:
        prior = by_id.setdefault(
            observation.outcome.descriptor_id, observation.outcome
        )
        if prior.to_document() != observation.outcome.to_document():
            raise V072ConfidenceRowProjectionIndependentVerificationFailure(
                "one descriptor ID changed document"
            )
    return tuple(by_id[key] for key in sorted(by_id))


def _environment_free_confidence_replay(
    snapshot: confidence.PartialSupportConfidenceSnapshotV2,
) -> None:
    """Replay confidence math without rebuilding the hidden-law preregistration."""

    if type(snapshot) is not confidence.PartialSupportConfidenceSnapshotV2:
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "confidence snapshot has a noncanonical concrete type"
        )
    epoch = snapshot.support_epoch
    if type(epoch) is confidence.InitialSupportEpochV2:
        discovery = epoch.discovery_evidence
        _verify_observation_prefix(
            discovery.observations,
            row=epoch.row_binding,
            support_chain_id=discovery.discovery_support_epoch_chain_id,
            stream_id=discovery.discovery_stream_id,
            lane=confidence.ConfidenceObservationLaneV2.DISCOVERY,
        )
        expected_support = _representative_descriptors(
            discovery.observations
        )
        if (
            epoch.epoch_index != 1
            or epoch.support_descriptors != expected_support
            or discovery.proposed_support != expected_support
            or epoch.excluded_probability_sample_ids
            != tuple(
                sorted(item.sample_id for item in discovery.observations)
            )
            or epoch.forbidden_validation_stream_ids
            != (discovery.discovery_stream_id,)
            or discovery.probability_evidence_draw_count != 0
        ):
            raise V072ConfidenceRowProjectionIndependentVerificationFailure(
                "initial confidence support lineage does not replay"
            )
    elif type(epoch) is confidence.PromotedSupportEpochV2:
        _environment_free_confidence_replay(epoch.parent_snapshot)
        parent = epoch.parent_snapshot
        parent_epoch = parent.support_epoch
        expected_novel = tuple(
            sorted(parent.novel_descriptor_ids)
        )
        by_id = {
            item.descriptor_id: item
            for item in parent_epoch.support_descriptors
        }
        for item in parent.novel_descriptors:
            by_id[item.descriptor_id] = item
        expected_support = tuple(by_id[key] for key in sorted(by_id))
        expected_excluded = tuple(
            sorted(
                set(parent_epoch.excluded_probability_sample_ids)
                | set(parent.validation_prefix.sample_ids)
            )
        )
        expected_forbidden = tuple(
            sorted(
                set(parent_epoch.forbidden_validation_stream_ids)
                | {parent_epoch.validation_stream_id}
            )
        )
        if (
            epoch.epoch_index != parent_epoch.epoch_index + 1
            or not expected_novel
            or epoch.support_descriptors != expected_support
            or epoch.excluded_probability_sample_ids != expected_excluded
            or epoch.forbidden_validation_stream_ids != expected_forbidden
            or epoch.promotion_evidence.parent_snapshot_id
            != parent.snapshot_id
            or epoch.promotion_evidence.parent_novel_descriptor_ids
            != expected_novel
            or epoch.promotion_evidence.promoted_support_descriptor_ids
            != tuple(item.descriptor_id for item in expected_support)
            or epoch.promotion_evidence.fresh_discovery_draw_count != 0
        ):
            raise V072ConfidenceRowProjectionIndependentVerificationFailure(
                "promoted confidence support lineage does not replay"
            )
    else:
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "confidence support epoch has an unknown type"
        )
    row = epoch.row_binding
    row_payload = {
        "schema": "acfqp.v072_confidence_physical_row_binding.v2",
        "schema_version": confidence.SCHEMA_VERSION,
        "preregistration_id": row.preregistration_id,
        "context_id": row.context_id,
        "arm": row.arm,
        "physical_row_id": row.physical_row_id,
    }
    if row.row_binding_id != _hash(CONFIDENCE_DOMAINS["row"], row_payload):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "confidence row binding ID does not replay"
        )
    prefix = snapshot.validation_prefix
    _verify_observation_prefix(
        prefix.observations,
        row=row,
        support_chain_id=epoch.support_epoch_chain_id,
        stream_id=epoch.validation_stream_id,
        lane=confidence.ConfidenceObservationLaneV2.VALIDATION,
    )
    if (
        prefix.row_binding_id != row.row_binding_id
        or prefix.support_epoch_id != epoch.support_epoch_id
        or prefix.support_epoch_chain_id != epoch.support_epoch_chain_id
        or prefix.validation_stream_id != epoch.validation_stream_id
        or prefix.selected_checkpoint_draw_count != len(prefix.observations)
        or set(prefix.sample_ids)
        & set(epoch.excluded_probability_sample_ids)
        or prefix.validation_stream_id
        in epoch.forbidden_validation_stream_ids
    ):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "confidence validation prefix is stale or reused"
        )
    expected_prefix = confidence.ValidationPrefixV2(
        prefix.row_binding_id,
        prefix.support_epoch_id,
        prefix.support_epoch_chain_id,
        prefix.validation_stream_id,
        len(prefix.observations),
        prefix.observations,
    )
    if prefix.prefix_id != expected_prefix.prefix_id:
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "confidence validation prefix ID does not replay"
        )
    profile_document = snapshot.profile.to_document()
    profile_id = profile_document.pop("profile_id")
    if (
        snapshot.profile.preregistration_id != row.preregistration_id
        or snapshot.profile.row_epoch_beta != confidence.ROW_EPOCH_BETA
        or snapshot.profile.maximum_support_descriptors
        != confidence.MAX_SUPPORT_DESCRIPTORS
        or snapshot.profile.cold_checkpoints != confidence.COLD_CHECKPOINTS
        or snapshot.profile.direct_checkpoints
        != confidence.DIRECT_CHECKPOINTS
        or snapshot.profile.new_child_checkpoints
        != confidence.NEW_CHILD_CHECKPOINTS
        or snapshot.profile.promotion_checkpoints
        != confidence.PROMOTION_CHECKPOINTS
        or snapshot.profile.target_half_width
        != confidence.TARGET_HALF_WIDTH
        or snapshot.profile.boundary_grid_bits
        != confidence.BOUNDARY_GRID_BITS
        or profile_id
        != _hash(CONFIDENCE_DOMAINS["profile"], profile_document)
    ):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "confidence profile ID/preregistration does not replay"
        )
    support_ids = tuple(
        item.descriptor_id for item in epoch.support_descriptors
    )
    counts = {key: 0 for key in support_ids}
    novel: dict[str, confidence.OpaqueOutcomeDescriptorV2] = {}
    other_count = 0
    for observation in prefix.observations:
        key = observation.outcome.descriptor_id
        if key in counts:
            counts[key] += 1
        else:
            other_count += 1
            prior = novel.setdefault(key, observation.outcome)
            if prior.to_document() != observation.outcome.to_document():
                raise V072ConfidenceRowProjectionIndependentVerificationFailure(
                    "novel confidence descriptor changed document"
                )
    count_values = tuple(counts[key] for key in support_ids) + (
        other_count,
    )
    keys = support_ids + (confidence.OTHER_EVENT_KEY,)
    checkpoints = {
        confidence.ConfidenceEpochPurposeV2.INITIAL_SHARED_OR_DIRECT: (
            confidence.DIRECT_CHECKPOINTS
        ),
        confidence.ConfidenceEpochPurposeV2.NEW_CHILD: (
            confidence.NEW_CHILD_CHECKPOINTS
        ),
        confidence.ConfidenceEpochPurposeV2.PROMOTION: (
            confidence.PROMOTION_CHECKPOINTS
        ),
    }.get(epoch.purpose)
    if (
        checkpoints is None
        or prefix.selected_checkpoint_draw_count not in checkpoints
    ):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "confidence checkpoint/purpose is not preregistered"
        )
    sequential = SequentialBernoulliProfileV1(
        confidence_alpha=confidence.ROW_EPOCH_BETA / len(keys),
        target_half_width=confidence.TARGET_HALF_WIDTH,
        checkpoints=checkpoints,
        boundary_grid_bits=confidence.BOUNDARY_GRID_BITS,
    )
    expected_events = tuple(
        confidence.PartialSupportEventIntervalV2(
            epoch.support_epoch_id,
            prefix.prefix_id,
            sequential.profile_id,
            ordinal,
            (
                confidence.PartialSupportEventKindV2.OTHER
                if ordinal == len(keys) - 1
                else confidence.PartialSupportEventKindV2.SUPPORT
            ),
            key,
            count_values[ordinal],
            build_anytime_bernoulli_checkpoint_v1(
                len(prefix.observations),
                count_values[ordinal],
                sequential,
            ),
        )
        for ordinal, key in enumerate(keys)
    )
    simplex = confidence.PartialSupportJointSimplexV2(
        epoch.support_epoch_id,
        prefix.prefix_id,
        tuple(item.event_interval_id for item in expected_events),
        tuple(item.lower_probability for item in expected_events),
        tuple(item.upper_probability for item in expected_events),
        len(expected_events) - 1,
    )
    expected_novel_descriptors = tuple(
        novel[key] for key in sorted(novel)
    )
    row_epoch_payload = {
        "schema": "acfqp.v072_row_confidence_epoch_authority.v2",
        "schema_version": confidence.SCHEMA_VERSION,
        "preregistration_id": snapshot.profile.preregistration_id,
        "profile_id": snapshot.profile.profile_id,
        "row_binding_id": row.row_binding_id,
        "support_epoch_id": epoch.support_epoch_id,
        "support_epoch_chain_id": epoch.support_epoch_chain_id,
        "epoch_index": epoch.epoch_index,
        "purpose": epoch.purpose.value,
        "row_epoch_beta": _fdoc(confidence.ROW_EPOCH_BETA),
        "checkpoint_snapshots_share_this_authority": True,
    }
    row_epoch_id = _hash(
        CONFIDENCE_DOMAINS["row_epoch"], row_epoch_payload
    )
    if (
        snapshot.sequential_profile != sequential
        or snapshot.event_intervals != expected_events
        or snapshot.joint_simplex != simplex
        or snapshot.novel_descriptors != expected_novel_descriptors
        or snapshot.row_confidence_epoch_id != row_epoch_id
        or snapshot.row_epoch_beta != confidence.ROW_EPOCH_BETA
        or snapshot.per_event_alpha
        != confidence.ROW_EPOCH_BETA / len(keys)
        or sum(count_values) != len(prefix.observations)
    ):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "confidence counts/intervals/simplex/novelty do not replay"
        )
    snapshot_document = snapshot.to_document()
    snapshot_id = snapshot_document.pop("snapshot_id")
    if snapshot_id != _hash(
        CONFIDENCE_DOMAINS["snapshot"], snapshot_document
    ):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "confidence snapshot content ID does not replay"
        )


@dataclass(frozen=True, slots=True)
class V072ConfidenceRowProjectionVerificationV1:
    projection_id: str
    confidence_snapshot_id: str
    row_binding_id: str
    interval_row_id: str
    support_mass_count: int
    other_mass_count: int
    exact_row_reward: Fraction
    registered_target_evidence_count: int = 0
    verification_result: str = (
        "VALID_INDEPENDENT_EXACT_CONFIDENCE_INTERVAL_ROW_PROJECTION"
    )
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.projection_id, "verified projection"),
            (self.confidence_snapshot_id, "verified confidence snapshot"),
            (self.row_binding_id, "verified public row"),
            (self.interval_row_id, "verified interval row"),
        ):
            _cid(value, label)
        if (
            self.support_mass_count <= 0
            or self.other_mass_count != 1
            or type(self.exact_row_reward) is not Fraction
            or self.registered_target_evidence_count != 0
            or self.verification_result
            != "VALID_INDEPENDENT_EXACT_CONFIDENCE_INTERVAL_ROW_PROJECTION"
        ):
            raise V072ConfidenceRowProjectionIndependentVerificationFailure(
                "projection verification result is malformed"
            )
        object.__setattr__(
            self,
            "_verification_id",
            _hash(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_confidence_row_projection_independent_"
                "verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "projection_id": self.projection_id,
            "confidence_snapshot_id": self.confidence_snapshot_id,
            "row_binding_id": self.row_binding_id,
            "interval_row_id": self.interval_row_id,
            "support_mass_count": self.support_mass_count,
            "other_mass_count": 1,
            "exact_row_reward": _fdoc(self.exact_row_reward),
            "registered_target_evidence_count": 0,
            "verification_result": self.verification_result,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v072_confidence_row_projection_v1(
    artifact: projection.ConfidenceIntervalSimplexRowProjectionV1,
) -> V072ConfidenceRowProjectionVerificationV1:
    """Recompute the complete projection without production derivation calls."""

    if type(artifact) is not projection.ConfidenceIntervalSimplexRowProjectionV1:
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "verification requires the exact projection artifact type"
        )
    snapshot = artifact.confidence_snapshot
    if type(snapshot) is not confidence.PartialSupportConfidenceSnapshotV2:
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "projection confidence snapshot has a foreign type"
        )
    _environment_free_confidence_replay(snapshot)
    binding = artifact.row_binding
    state_id, action_id, row_binding_id, reward = _verify_row_binding(
        binding
    )
    confidence_row = snapshot.support_epoch.row_binding
    if (
        confidence_row.preregistration_id != binding.preregistration_id
        or confidence_row.context_id != binding.context_id
        or confidence_row.arm != binding.arm
        or confidence_row.physical_row_id != binding.physical_row_id
        or confidence_row.row_binding_id != binding.confidence_row_binding_id
    ):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "confidence snapshot was transplanted across public rows"
        )
    support = snapshot.support_epoch.support_descriptors
    support_events = snapshot.event_intervals[:-1]
    other_event = snapshot.event_intervals[-1]
    if (
        tuple(item.descriptor_id for item in support)
        != tuple(item.event_key for item in support_events)
        or other_event.event_kind
        is not confidence.PartialSupportEventKindV2.OTHER
        or other_event.event_key != confidence.OTHER_EVENT_KEY
        or len(artifact.observed_destinations) != len(support)
        or len(artifact.event_projections) != len(snapshot.event_intervals)
    ):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "support/event/OTHER cardinality or order changed"
        )
    destination_ids: list[str] = []
    categories: list[robust.DestinationCategory] = []
    state_ids: list[str | None] = []
    destination_payloads: list[dict[str, Any]] = []
    for descriptor, actual in zip(
        support, artifact.observed_destinations
    ):
        expected = _descriptor_expected(
            descriptor, binding, row_binding_id
        )
        category, target_state, semantic_state, destination_id, payload = (
            expected
        )
        if (
            type(actual) is not projection.ObservedDestinationBindingV1
            or actual.row_binding_id != row_binding_id
            or actual.descriptor != descriptor
            or actual.category is not category
            or actual.state_id != target_state
            or actual.semantic_successor_state_id != semantic_state
            or actual.destination_id != destination_id
        ):
            raise V072ConfidenceRowProjectionIndependentVerificationFailure(
                "observed destination does not replay from descriptor bytes"
            )
        destination_ids.append(destination_id)
        categories.append(category)
        state_ids.append(target_state)
        destination_payloads.append(payload)
    other_id, other_payload = _other_expected(
        binding, state_id, action_id, row_binding_id
    )
    other = artifact.other_destination
    if (
        type(other)
        is not projection.AdversarialOtherDestinationBindingV1
        or other.context_id != binding.context_id
        or other.row_binding_id != row_binding_id
        or other.state_id != state_id
        or other.action_id != action_id
        or other.remaining_horizon != binding.remaining_horizon
        or other.category is not robust.DestinationCategory.OTHER
        or other.failure_value != 1
        or other.continuation_reward_lower != 0
        or other.destination_id != other_id
    ):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "OTHER is not the unique row-bound adversarial destination"
        )
    expected_event_projection_ids: list[str] = []
    expected_masses: list[tuple[str, Fraction, Fraction, str]] = []
    for ordinal, event in enumerate(snapshot.event_intervals):
        is_other = ordinal == len(support_events)
        destination_id = (
            other_id if is_other else destination_ids[ordinal]
        )
        descriptor_id = (
            None if is_other else support[ordinal].descriptor_id
        )
        event_payload = {
            "schema": (
                "acfqp.v072_confidence_event_destination_projection.v1"
            ),
            "schema_version": projection.SCHEMA_VERSION,
            "event_interval_id": event.event_interval_id,
            "event_ordinal": event.event_ordinal,
            "event_kind": event.event_kind.value,
            "event_key": event.event_key,
            "destination_id": destination_id,
            "lower_probability": _fdoc(event.lower_probability),
            "upper_probability": _fdoc(event.upper_probability),
            "descriptor_id": descriptor_id,
        }
        event_projection_id = _hash(
            PROJECTION_DOMAINS["event_projection"], event_payload
        )
        actual_event = artifact.event_projections[ordinal]
        if (
            type(actual_event)
            is not projection.ConfidenceEventDestinationProjectionV1
            or actual_event.event_interval_id != event.event_interval_id
            or actual_event.event_ordinal != event.event_ordinal
            or actual_event.event_kind is not event.event_kind
            or actual_event.event_key != event.event_key
            or actual_event.destination_id != destination_id
            or actual_event.lower_probability != event.lower_probability
            or actual_event.upper_probability != event.upper_probability
            or actual_event.descriptor_id != descriptor_id
            or actual_event.event_projection_id != event_projection_id
        ):
            raise V072ConfidenceRowProjectionIndependentVerificationFailure(
                "confidence event mass was reordered, duplicated, or changed"
            )
        mass_id, _ = _mass_expected(
            destination_id,
            event.lower_probability,
            event.upper_probability,
        )
        expected_event_projection_ids.append(event_projection_id)
        expected_masses.append(
            (
                destination_id,
                event.lower_probability,
                event.upper_probability,
                mass_id,
            )
        )
    expected_masses.sort(key=lambda item: item[0])
    row = artifact.interval_row
    if (
        type(row) is not robust.IntervalSimplexRowV1
        or row.state_id != state_id
        or row.remaining_horizon != binding.remaining_horizon
        or row.action_id != action_id
        or row.reward_lower != reward
        or row.reward_upper != reward
        or row.other_destination_id != other_id
        or len(row.masses) != len(expected_masses)
    ):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "robust interval row identity/reward/OTHER changed"
        )
    for actual_mass, expected_mass in zip(row.masses, expected_masses):
        if (
            type(actual_mass) is not robust.IntervalDestinationMassV1
            or actual_mass.destination_id != expected_mass[0]
            or actual_mass.lower != expected_mass[1]
            or actual_mass.upper != expected_mass[2]
            or actual_mass.mass_id != expected_mass[3]
        ):
            raise V072ConfidenceRowProjectionIndependentVerificationFailure(
                "robust mass differs from exact confidence interval"
            )
    lower_sum = sum(
        (item[1] for item in expected_masses), Fraction(0)
    )
    upper_sum = sum(
        (item[2] for item in expected_masses), Fraction(0)
    )
    if lower_sum > 1 or upper_sum < 1:
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "projected intervals no longer admit the snapshot joint simplex"
        )
    row_payload = {
        "schema": "acfqp.partial_support_interval_simplex_row.v1",
        "schema_version": robust.SCHEMA_VERSION,
        "contract_version": robust.CONTRACT_VERSION,
        "profile_key": robust.PROFILE_KEY,
        "state_id": state_id,
        "remaining_horizon": binding.remaining_horizon,
        "action_id": action_id,
        "reward_lower": _fdoc(reward),
        "reward_upper": _fdoc(reward),
        "other_destination_id": other_id,
        "mass_ids": [item[3] for item in expected_masses],
    }
    interval_row_id = _hash(ROBUST_DOMAINS["row"], row_payload)
    if row.row_id != interval_row_id:
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "robust interval row content ID does not replay"
        )
    novel_ids = tuple(sorted(snapshot.novel_descriptor_ids))
    if (
        artifact.exact_row_reward != reward
        or artifact.validation_novel_descriptor_ids != novel_ids
        or artifact.novel_descriptors_aggregated_only_in_other is not True
        or set(novel_ids) & set(destination_ids)
        or set(novel_ids) & {
            item.descriptor.descriptor_id
            for item in artifact.observed_destinations
        }
    ):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "validation novelty escaped OTHER before promotion"
        )
    actual_registered = artifact.registered_destinations
    expected_registry: list[
        tuple[str, robust.DestinationCategory, str | None, str]
    ] = []
    for destination_id, category, target_state in zip(
        destination_ids, categories, state_ids
    ):
        registry_id, _ = _registered_destination_expected(
            destination_id, category, target_state
        )
        expected_registry.append(
            (destination_id, category, target_state, registry_id)
        )
    other_registry_id, _ = _registered_destination_expected(
        other_id, robust.DestinationCategory.OTHER, None
    )
    expected_registry.append(
        (
            other_id,
            robust.DestinationCategory.OTHER,
            None,
            other_registry_id,
        )
    )
    expected_registry.sort(key=lambda item: item[0])
    if len(actual_registered) != len(expected_registry):
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "destination registry omitted or duplicated an entry"
        )
    for actual, expected in zip(actual_registered, expected_registry):
        if (
            type(actual) is not robust.RegisteredDestinationV1
            or actual.destination_id != expected[0]
            or actual.category is not expected[1]
            or actual.state_id != expected[2]
            or actual.registry_entry_id != expected[3]
        ):
            raise V072ConfidenceRowProjectionIndependentVerificationFailure(
                "destination registry entry does not replay"
            )
    projection_payload = {
        "schema": (
            "acfqp.v072_confidence_interval_simplex_row_projection.v1"
        ),
        "schema_version": projection.SCHEMA_VERSION,
        "proposed_contract_version": projection.PROPOSED_CONTRACT_VERSION,
        "profile_key": projection.PROFILE_KEY,
        "preregistration_id": binding.preregistration_id,
        "confidence_snapshot_id": snapshot.snapshot_id,
        "row_binding_id": row_binding_id,
        "observed_destination_ids": destination_ids,
        "other_destination_id": other_id,
        "event_projection_ids": expected_event_projection_ids,
        "interval_row_id": interval_row_id,
        "exact_row_reward": _fdoc(reward),
        "validation_novel_descriptor_ids": list(novel_ids),
        "novel_descriptors_aggregated_only_in_other": True,
        "registered_target_evidence": False,
    }
    projection_id = _hash(
        PROJECTION_DOMAINS["projection"], projection_payload
    )
    if artifact.projection_id != projection_id:
        raise V072ConfidenceRowProjectionIndependentVerificationFailure(
            "projection content ID does not replay"
        )
    return V072ConfidenceRowProjectionVerificationV1(
        projection_id,
        snapshot.snapshot_id,
        row_binding_id,
        interval_row_id,
        len(support),
        1,
        reward,
    )


__all__ = [
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "V072ConfidenceRowProjectionIndependentVerificationFailure",
    "V072ConfidenceRowProjectionVerificationV1",
    "verify_v072_confidence_row_projection_v1",
]
