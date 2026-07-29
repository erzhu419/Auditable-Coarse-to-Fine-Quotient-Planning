"""Project V0-072 confidence snapshots into robust interval-simplex rows.

This module is the narrow bridge between observation/confidence and planning.
It consumes one exact V2 confidence snapshot plus public state/action
semantics.  It does not call a kernel, enumerate exact support, or accept
caller-supplied probabilities, rewards, destinations, or cardinalities.

Every frozen support event becomes exactly one planner mass.  The unique
confidence ``OTHER`` event becomes one row-bound adversarial destination.
Novel validation descriptors remain inside that aggregate event until a
subsequent confidence epoch explicitly promotes them into frozen support.

The original disjoint development synthetic profile remains unchanged.
Registered target projection has a separate rank-cap-6 schema and accepts
only an internally minted target-confidence authority bound to the exact
remote-main anchor and an independent fresh-stream replay attestation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import partial_support_confidence_v2 as confidence
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import v072_cold_h2_closure_v1 as cold
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import v072_synthetic_row_observation_adapter_v1 as synthetic
import acfqp.transfer_guided_acquisition_preregistration_v1 as prereg


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_confidence_interval_simplex_row_projection_v0"
ROLE = synthetic.ROLE
REGISTERED_TARGET_PROJECTION_STATUS = (
    "ENABLED_ONLY_BY_EXACT_ANCHOR_AND_INDEPENDENT_TRANSCRIPT_REPLAY"
)
DEVELOPMENT_RANK_PROFILE = "DEVELOPMENT_K4_RANK_CAP_4_NONMIGRATABLE"
PRODUCTION_RANK_PROFILE = "PRODUCTION_G2048_RANK_CAP_6_REGISTERED"
REGISTERED_TARGET_CONFIDENCE_AUTHORITY_ENABLED = True


class V072ConfidenceRowProjectionInvariantViolation(ValueError):
    """A row semantic, destination, confidence event, or projection is invalid."""


class RegisteredTargetConfidenceProjectionLockedV1(RuntimeError):
    """Registered target projection has no final execution authority."""


DOMAIN_TAGS = {
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
    "registered_event": (
        "acfqp:v072-registered-confidence-event-interval:v1"
    ),
    "registered_authority": (
        "acfqp:v072-registered-confidence-projection-authority:v1"
    ),
    "registered_projection": (
        "acfqp:v072-registered-confidence-interval-row-projection:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-072 confidence projection domains must be unique")


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V072ConfidenceRowProjectionInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072ConfidenceRowProjectionInvariantViolation(
            f"{field_name} must be one full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V072ConfidenceRowProjectionInvariantViolation(
            "projection arithmetic must use exact Fraction"
        )
    return {"numerator": value.numerator, "denominator": value.denominator}


def _action(value: Any) -> tuple[int, int, int]:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(item) is not int for item in value)
    ):
        raise V072ConfidenceRowProjectionInvariantViolation(
            "public action must be one exact integer triple"
        )
    return value


@dataclass(frozen=True, slots=True)
class PublicStateActionRowBindingV1:
    """Development public row semantics; reward is derived, never supplied."""

    preregistration_id: str
    context_id: str
    arm: str
    physical_row_id: str
    confidence_row_binding_id: str
    state_ranks: tuple[int, ...]
    remaining_horizon: int
    action: tuple[int, int, int]
    rank_cap: int = 4
    query_horizon: int = 2
    rank_profile: str = DEVELOPMENT_RANK_PROFILE
    role: str = ROLE
    registered_target_evidence: bool = False
    _state_id: str = field(init=False, repr=False)
    _action_id: str = field(init=False, repr=False)
    _row_binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.preregistration_id, "public-row preregistration"),
            (self.context_id, "public-row context"),
            (self.physical_row_id, "public physical row"),
            (self.confidence_row_binding_id, "confidence row binding"),
        ):
            _cid(value, label)
        action = _action(self.action)
        first, second, survivor = action
        if (
            self.arm not in prereg.ARM_ORDER
            or type(self.state_ranks) is not tuple
            or not self.state_ranks
            or any(
                type(rank) is not int or not 0 <= rank <= self.rank_cap
                for rank in self.state_ranks
            )
            or self.remaining_horizon not in (1, 2)
            or self.rank_cap != 4
            or self.query_horizon != 2
            or self.rank_profile != DEVELOPMENT_RANK_PROFILE
            or min(first, second, survivor) < 0
            or max(first, second, survivor) >= len(self.state_ranks)
            or first == second
            or survivor not in (first, second)
            or self.state_ranks[first] <= 0
            or self.state_ranks[first] != self.state_ranks[second]
            or self.role != ROLE
            or self.registered_target_evidence is not False
        ):
            raise V072ConfidenceRowProjectionInvariantViolation(
                "public development row semantics are invalid"
            )
        object.__setattr__(
            self,
            "_state_id",
            _content_id("state", self._state_payload()),
        )
        object.__setattr__(
            self,
            "_action_id",
            _content_id("action", self._action_payload()),
        )
        object.__setattr__(
            self,
            "_row_binding_id",
            _content_id("row_binding", self._payload()),
        )

    def _state_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_projection_public_state.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "state_ranks": list(self.state_ranks),
            "remaining_horizon": self.remaining_horizon,
            "role": ROLE,
        }

    @property
    def state_id(self) -> str:
        return self._state_id

    @property
    def merge_rank(self) -> int:
        return self.state_ranks[self.action[0]]

    @property
    def exact_row_reward(self) -> Fraction:
        return (
            Fraction(
                2 ** (self.merge_rank + 1),
                2 ** (self.rank_cap + 1),
            )
            / self.query_horizon
        )

    def _action_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_projection_public_action.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "state_id": self.state_id,
            "remaining_horizon": self.remaining_horizon,
            "action": list(self.action),
            "merge_rank": self.merge_rank,
            "exact_row_reward": _fdoc(self.exact_row_reward),
            "role": ROLE,
        }

    @property
    def action_id(self) -> str:
        return self._action_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_projection_public_row_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": self.preregistration_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "physical_row_id": self.physical_row_id,
            "confidence_row_binding_id": self.confidence_row_binding_id,
            "state_id": self.state_id,
            "remaining_horizon": self.remaining_horizon,
            "action_id": self.action_id,
            "rank_cap": self.rank_cap,
            "query_horizon": self.query_horizon,
            "rank_profile": self.rank_profile,
            "exact_row_reward": _fdoc(self.exact_row_reward),
            "role": ROLE,
            "registered_target_evidence": False,
        }

    @property
    def row_binding_id(self) -> str:
        return self._row_binding_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "state": {**self._state_payload(), "state_id": self.state_id},
            "action": {**self._action_payload(), "action_id": self.action_id},
            "row_binding_id": self.row_binding_id,
        }


def development_synthetic_projection_row_binding_v1(
    acquisition: synthetic.DevelopmentSyntheticRowAcquisitionV2,
    *,
    remaining_horizon: int | None = None,
) -> PublicStateActionRowBindingV1:
    """Mechanically derive the public row binding from a synthetic acquisition."""

    if type(acquisition) is not synthetic.DevelopmentSyntheticRowAcquisitionV2:
        raise V072ConfidenceRowProjectionInvariantViolation(
            "synthetic row binding requires an exact acquisition artifact"
        )
    row = acquisition.row
    horizon = (
        row.remaining_horizon
        if remaining_horizon is None
        else remaining_horizon
    )
    if horizon != row.remaining_horizon:
        raise V072ConfidenceRowProjectionInvariantViolation(
            "synthetic acquisition horizon cannot be caller-overridden"
        )
    return PublicStateActionRowBindingV1(
        preregistration_id=acquisition.confidence_row_binding.preregistration_id,
        context_id=row.context_id,
        arm=acquisition.arm,
        physical_row_id=row.physical_row_id,
        confidence_row_binding_id=(
            acquisition.confidence_row_binding.row_binding_id
        ),
        state_ranks=row.state_ranks,
        remaining_horizon=row.remaining_horizon,
        action=row.action,
    )


def _descriptor_semantics(
    descriptor: confidence.OpaqueOutcomeDescriptorV2,
    row_binding: PublicStateActionRowBindingV1,
) -> tuple[
    robust.DestinationCategory,
    str | None,
    str,
    Mapping[str, Any],
]:
    if type(descriptor) is not confidence.OpaqueOutcomeDescriptorV2:
        raise V072ConfidenceRowProjectionInvariantViolation(
            "destination derivation requires an exact frozen descriptor"
        )
    document = descriptor.document
    if not isinstance(document, Mapping):
        raise V072ConfidenceRowProjectionInvariantViolation(
            "descriptor document is not an object"
        )
    next_state = document.get("next_state")
    if not isinstance(next_state, Mapping):
        raise V072ConfidenceRowProjectionInvariantViolation(
            "descriptor lacks public next-state semantics"
        )
    ranks = next_state.get("ranks")
    next_failure = next_state.get("failure")
    failure = document.get("failure")
    terminal = document.get("terminal")
    reward = document.get("realized_row_reward")
    if (
        type(ranks) not in (tuple, list)
        or len(ranks) != len(row_binding.state_ranks)
        or any(
            type(rank) is not int or not 0 <= rank <= row_binding.rank_cap
            for rank in ranks
        )
        or type(next_failure) is not bool
        or type(failure) is not bool
        or failure != next_failure
        or type(terminal) is not bool
        or type(reward) is not Fraction
        or reward != row_binding.exact_row_reward
        or (
            "descriptor_id" in document
            and document["descriptor_id"] != descriptor.descriptor_id
        )
    ):
        raise V072ConfidenceRowProjectionInvariantViolation(
            "descriptor state/reward/failure semantics are inconsistent"
        )
    if row_binding.remaining_horizon == 2:
        if terminal != failure:
            raise V072ConfidenceRowProjectionInvariantViolation(
                "H2 root outcome terminal/failure semantics changed"
            )
    elif terminal is not True:
        raise V072ConfidenceRowProjectionInvariantViolation(
            "H1 outcome must terminate after the transition"
        )
    if failure:
        category = robust.DestinationCategory.FAILURE
    elif row_binding.remaining_horizon == 1:
        category = robust.DestinationCategory.SUCCESS_TERMINAL
    else:
        category = robust.DestinationCategory.ACTIVE_STATE
    state_document = {
        "schema": "acfqp.v072_projection_successor_state.v1",
        "schema_version": SCHEMA_VERSION,
        "context_id": row_binding.context_id,
        "ranks": list(ranks),
        "failure": failure,
        "remaining_horizon": row_binding.remaining_horizon - 1,
        "source_descriptor_id": descriptor.descriptor_id,
        "role": ROLE,
    }
    semantic_state_id = _content_id("successor_state", state_document)
    state_id = (
        semantic_state_id
        if category is robust.DestinationCategory.ACTIVE_STATE
        else None
    )
    return category, state_id, semantic_state_id, document


@dataclass(frozen=True, slots=True)
class ObservedDestinationBindingV1:
    row_binding_id: str
    descriptor: confidence.OpaqueOutcomeDescriptorV2
    category: robust.DestinationCategory
    state_id: str | None
    semantic_successor_state_id: str
    _destination_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.row_binding_id, "destination row binding")
        _cid(
            self.semantic_successor_state_id,
            "semantic successor state",
        )
        if (
            type(self.descriptor) is not confidence.OpaqueOutcomeDescriptorV2
            or type(self.category) is not robust.DestinationCategory
            or self.category is robust.DestinationCategory.OTHER
        ):
            raise V072ConfidenceRowProjectionInvariantViolation(
                "observed destination binding is malformed"
            )
        if self.category is robust.DestinationCategory.ACTIVE_STATE:
            if self.state_id is None:
                raise V072ConfidenceRowProjectionInvariantViolation(
                    "active destination requires state identity"
                )
            _cid(self.state_id, "active destination state")
        elif self.state_id is not None:
            raise V072ConfidenceRowProjectionInvariantViolation(
                "terminal/failure destination cannot expose active state"
            )
        object.__setattr__(
            self,
            "_destination_id",
            _content_id("destination", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_projection_observed_destination.v1",
            "schema_version": SCHEMA_VERSION,
            "row_binding_id": self.row_binding_id,
            "descriptor_id": self.descriptor.descriptor_id,
            "descriptor_binding_id": self.descriptor.binding_id,
            "category": self.category.value,
            "state_id": self.state_id,
            "semantic_successor_state_id": (
                self.semantic_successor_state_id
            ),
        }

    @property
    def destination_id(self) -> str:
        return self._destination_id

    def registered_destination(self) -> robust.RegisteredDestinationV1:
        return robust.RegisteredDestinationV1(
            self.destination_id,
            self.category,
            self.state_id,
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "descriptor": self.descriptor.to_document(),
            "destination_id": self.destination_id,
        }


@dataclass(frozen=True, slots=True)
class AdversarialOtherDestinationBindingV1:
    context_id: str
    row_binding_id: str
    state_id: str
    action_id: str
    remaining_horizon: int
    category: robust.DestinationCategory = robust.DestinationCategory.OTHER
    failure_value: Fraction = Fraction(1)
    continuation_reward_lower: Fraction = Fraction(0)
    _destination_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.context_id, "OTHER context"),
            (self.row_binding_id, "OTHER row binding"),
            (self.state_id, "OTHER source state"),
            (self.action_id, "OTHER source action"),
        ):
            _cid(value, label)
        if (
            self.remaining_horizon not in (1, 2)
            or self.category is not robust.DestinationCategory.OTHER
            or self.failure_value != 1
            or self.continuation_reward_lower != 0
        ):
            raise V072ConfidenceRowProjectionInvariantViolation(
                "OTHER is not the row-bound adversarial destination"
            )
        object.__setattr__(
            self,
            "_destination_id",
            _content_id("other", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_projection_adversarial_other_destination.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "row_binding_id": self.row_binding_id,
            "state_id": self.state_id,
            "action_id": self.action_id,
            "remaining_horizon": self.remaining_horizon,
            "category": self.category.value,
            "joint_unknown_event_count": 1,
            "failure_value": _fdoc(self.failure_value),
            "continuation_reward_lower": _fdoc(
                self.continuation_reward_lower
            ),
        }

    @property
    def destination_id(self) -> str:
        return self._destination_id

    def registered_destination(self) -> robust.RegisteredDestinationV1:
        return robust.RegisteredDestinationV1(
            self.destination_id,
            robust.DestinationCategory.OTHER,
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "destination_id": self.destination_id}


@dataclass(frozen=True, slots=True)
class ConfidenceEventDestinationProjectionV1:
    event_interval_id: str
    event_ordinal: int
    event_kind: confidence.PartialSupportEventKindV2
    event_key: str
    destination_id: str
    lower_probability: Fraction
    upper_probability: Fraction
    descriptor_id: str | None
    _event_projection_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.event_interval_id, "projected event interval")
        _cid(self.destination_id, "projected destination")
        if self.descriptor_id is not None:
            _cid(self.descriptor_id, "projected descriptor")
        if (
            type(self.event_ordinal) is not int
            or self.event_ordinal < 0
            or type(self.event_kind) is not confidence.PartialSupportEventKindV2
            or type(self.event_key) is not str
            or not self.event_key
            or type(self.lower_probability) is not Fraction
            or type(self.upper_probability) is not Fraction
            or not 0 <= self.lower_probability <= self.upper_probability <= 1
            or (
                self.event_kind is confidence.PartialSupportEventKindV2.OTHER
                and (
                    self.event_key != confidence.OTHER_EVENT_KEY
                    or self.descriptor_id is not None
                )
            )
            or (
                self.event_kind is confidence.PartialSupportEventKindV2.SUPPORT
                and self.descriptor_id != self.event_key
            )
        ):
            raise V072ConfidenceRowProjectionInvariantViolation(
                "confidence event/destination projection is malformed"
            )
        object.__setattr__(
            self,
            "_event_projection_id",
            _content_id("event_projection", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_confidence_event_destination_projection.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "event_interval_id": self.event_interval_id,
            "event_ordinal": self.event_ordinal,
            "event_kind": self.event_kind.value,
            "event_key": self.event_key,
            "destination_id": self.destination_id,
            "lower_probability": _fdoc(self.lower_probability),
            "upper_probability": _fdoc(self.upper_probability),
            "descriptor_id": self.descriptor_id,
        }

    @property
    def event_projection_id(self) -> str:
        return self._event_projection_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "event_projection_id": self.event_projection_id,
        }


@dataclass(frozen=True, slots=True)
class ConfidenceIntervalSimplexRowProjectionV1:
    confidence_snapshot: confidence.PartialSupportConfidenceSnapshotV2
    row_binding: PublicStateActionRowBindingV1
    observed_destinations: tuple[ObservedDestinationBindingV1, ...]
    other_destination: AdversarialOtherDestinationBindingV1
    event_projections: tuple[ConfidenceEventDestinationProjectionV1, ...]
    interval_row: robust.IntervalSimplexRowV1
    exact_row_reward: Fraction
    validation_novel_descriptor_ids: tuple[str, ...]
    novel_descriptors_aggregated_only_in_other: bool = True
    _projection_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _validate_projection(self)
        object.__setattr__(
            self,
            "_projection_id",
            _content_id("projection", self._payload()),
        )

    @property
    def registered_destinations(
        self,
    ) -> tuple[robust.RegisteredDestinationV1, ...]:
        values = tuple(
            item.registered_destination()
            for item in self.observed_destinations
        ) + (self.other_destination.registered_destination(),)
        return tuple(sorted(values, key=lambda item: item.destination_id))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_confidence_interval_simplex_row_projection.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": self.row_binding.preregistration_id,
            "confidence_snapshot_id": self.confidence_snapshot.snapshot_id,
            "row_binding_id": self.row_binding.row_binding_id,
            "observed_destination_ids": [
                item.destination_id for item in self.observed_destinations
            ],
            "other_destination_id": (
                self.other_destination.destination_id
            ),
            "event_projection_ids": [
                item.event_projection_id for item in self.event_projections
            ],
            "interval_row_id": self.interval_row.row_id,
            "exact_row_reward": _fdoc(self.exact_row_reward),
            "validation_novel_descriptor_ids": list(
                self.validation_novel_descriptor_ids
            ),
            "novel_descriptors_aggregated_only_in_other": True,
            "registered_target_evidence": False,
        }

    @property
    def projection_id(self) -> str:
        return self._projection_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_binding": self.row_binding.to_document(),
            "observed_destinations": [
                item.to_document() for item in self.observed_destinations
            ],
            "other_destination": self.other_destination.to_document(),
            "event_projections": [
                item.to_document() for item in self.event_projections
            ],
            "interval_row": self.interval_row.to_document(),
            "registered_destinations": [
                item.to_document() for item in self.registered_destinations
            ],
            "projection_id": self.projection_id,
        }


def _expected_components(
    snapshot: confidence.PartialSupportConfidenceSnapshotV2,
    row_binding: PublicStateActionRowBindingV1,
) -> tuple[
    tuple[ObservedDestinationBindingV1, ...],
    AdversarialOtherDestinationBindingV1,
    tuple[ConfidenceEventDestinationProjectionV1, ...],
    robust.IntervalSimplexRowV1,
]:
    epoch = snapshot.support_epoch
    if type(epoch) not in (
        confidence.InitialSupportEpochV2,
        confidence.PromotedSupportEpochV2,
    ):
        raise V072ConfidenceRowProjectionInvariantViolation(
            "projection requires one exact concrete V2 support epoch"
        )
    confidence_row = epoch.row_binding
    if (
        row_binding.preregistration_id != confidence_row.preregistration_id
        or row_binding.context_id != confidence_row.context_id
        or row_binding.arm != confidence_row.arm
        or row_binding.physical_row_id != confidence_row.physical_row_id
        or row_binding.confidence_row_binding_id
        != confidence_row.row_binding_id
    ):
        raise V072ConfidenceRowProjectionInvariantViolation(
            "confidence snapshot and public row binding do not match"
        )
    support = epoch.support_descriptors
    support_events = snapshot.event_intervals[:-1]
    other_event = snapshot.event_intervals[-1]
    if (
        tuple(item.descriptor_id for item in support)
        != tuple(item.event_key for item in support_events)
        or other_event.event_kind
        is not confidence.PartialSupportEventKindV2.OTHER
        or other_event.event_key != confidence.OTHER_EVENT_KEY
    ):
        raise V072ConfidenceRowProjectionInvariantViolation(
            "snapshot support/event order or unique OTHER changed"
        )
    destinations: list[ObservedDestinationBindingV1] = []
    for descriptor in support:
        category, state_id, semantic_state_id, _ = _descriptor_semantics(
            descriptor, row_binding
        )
        destinations.append(
            ObservedDestinationBindingV1(
                row_binding.row_binding_id,
                descriptor,
                category,
                state_id,
                semantic_state_id,
            )
        )
    other = AdversarialOtherDestinationBindingV1(
        row_binding.context_id,
        row_binding.row_binding_id,
        row_binding.state_id,
        row_binding.action_id,
        row_binding.remaining_horizon,
    )
    event_projections: list[ConfidenceEventDestinationProjectionV1] = []
    masses: list[robust.IntervalDestinationMassV1] = []
    for event, destination in zip(support_events, destinations):
        event_projections.append(
            ConfidenceEventDestinationProjectionV1(
                event.event_interval_id,
                event.event_ordinal,
                event.event_kind,
                event.event_key,
                destination.destination_id,
                event.lower_probability,
                event.upper_probability,
                destination.descriptor.descriptor_id,
            )
        )
        masses.append(
            robust.IntervalDestinationMassV1(
                destination.destination_id,
                event.lower_probability,
                event.upper_probability,
            )
        )
    event_projections.append(
        ConfidenceEventDestinationProjectionV1(
            other_event.event_interval_id,
            other_event.event_ordinal,
            other_event.event_kind,
            other_event.event_key,
            other.destination_id,
            other_event.lower_probability,
            other_event.upper_probability,
            None,
        )
    )
    masses.append(
        robust.IntervalDestinationMassV1(
            other.destination_id,
            other_event.lower_probability,
            other_event.upper_probability,
        )
    )
    row = robust.IntervalSimplexRowV1(
        row_binding.state_id,
        row_binding.remaining_horizon,
        row_binding.action_id,
        row_binding.exact_row_reward,
        row_binding.exact_row_reward,
        other.destination_id,
        tuple(sorted(masses, key=lambda item: item.destination_id)),
    )
    return tuple(destinations), other, tuple(event_projections), row


def _validate_projection(
    projection: ConfidenceIntervalSimplexRowProjectionV1,
) -> None:
    if (
        type(projection.confidence_snapshot)
        is not confidence.PartialSupportConfidenceSnapshotV2
        or type(projection.row_binding) is not PublicStateActionRowBindingV1
        or type(projection.observed_destinations) is not tuple
        or any(
            type(item) is not ObservedDestinationBindingV1
            for item in projection.observed_destinations
        )
        or type(projection.other_destination)
        is not AdversarialOtherDestinationBindingV1
        or type(projection.event_projections) is not tuple
        or any(
            type(item) is not ConfidenceEventDestinationProjectionV1
            for item in projection.event_projections
        )
        or type(projection.interval_row) is not robust.IntervalSimplexRowV1
        or type(projection.exact_row_reward) is not Fraction
        or type(projection.validation_novel_descriptor_ids) is not tuple
        or projection.validation_novel_descriptor_ids
        != tuple(
            sorted(
                projection.confidence_snapshot.novel_descriptor_ids
            )
        )
        or projection.novel_descriptors_aggregated_only_in_other is not True
    ):
        raise V072ConfidenceRowProjectionInvariantViolation(
            "confidence row projection concrete schema is invalid"
        )
    expected = _expected_components(
        projection.confidence_snapshot, projection.row_binding
    )
    if (
        projection.observed_destinations != expected[0]
        or projection.other_destination != expected[1]
        or projection.event_projections != expected[2]
        or projection.interval_row != expected[3]
        or projection.exact_row_reward
        != projection.row_binding.exact_row_reward
        or set(projection.validation_novel_descriptor_ids)
        & {
            item.descriptor.descriptor_id
            for item in projection.observed_destinations
        }
    ):
        raise V072ConfidenceRowProjectionInvariantViolation(
            "destination, mass, reward, OTHER, or novelty projection changed"
        )


def project_confidence_snapshot_to_interval_row_v1(
    snapshot: confidence.PartialSupportConfidenceSnapshotV2,
    row_binding: PublicStateActionRowBindingV1,
) -> ConfidenceIntervalSimplexRowProjectionV1:
    """Mechanically project one exact snapshot; no caller endpoints accepted."""

    if (
        type(snapshot) is not confidence.PartialSupportConfidenceSnapshotV2
        or type(row_binding) is not PublicStateActionRowBindingV1
    ):
        raise V072ConfidenceRowProjectionInvariantViolation(
            "projection requires exact V2 snapshot and public row binding"
        )
    destinations, other, events, row = _expected_components(
        snapshot, row_binding
    )
    return ConfidenceIntervalSimplexRowProjectionV1(
        snapshot,
        row_binding,
        destinations,
        other,
        events,
        row,
        row_binding.exact_row_reward,
        tuple(sorted(snapshot.novel_descriptor_ids)),
    )


class RegisteredConfidenceEventKindV1(str, Enum):
    SUPPORT = "SUPPORT"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class RegisteredConfidenceEventIntervalV1:
    """One interval emitted by the future registered confidence authority."""

    confidence_event_id: str
    event_ordinal: int
    event_kind: RegisteredConfidenceEventKindV1
    descriptor_record_id: str | None
    lower_probability: Fraction
    upper_probability: Fraction
    _event_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.confidence_event_id, "registered confidence event")
        if self.descriptor_record_id is not None:
            _cid(
                self.descriptor_record_id,
                "registered support descriptor",
            )
        if (
            type(self.event_ordinal) is not int
            or self.event_ordinal < 0
            or type(self.event_kind) is not RegisteredConfidenceEventKindV1
            or type(self.lower_probability) is not Fraction
            or type(self.upper_probability) is not Fraction
            or not (
                0
                <= self.lower_probability
                <= self.upper_probability
                <= 1
            )
            or (
                self.event_kind
                is RegisteredConfidenceEventKindV1.SUPPORT
                and self.descriptor_record_id is None
            )
            or (
                self.event_kind is RegisteredConfidenceEventKindV1.OTHER
                and self.descriptor_record_id is not None
            )
        ):
            raise V072ConfidenceRowProjectionInvariantViolation(
                "registered confidence event interval is malformed"
            )
        object.__setattr__(
            self,
            "_event_id",
            _content_id("registered_event", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_confidence_event_interval.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "confidence_event_id": self.confidence_event_id,
            "event_ordinal": self.event_ordinal,
            "event_kind": self.event_kind.value,
            "descriptor_record_id": self.descriptor_record_id,
            "lower_probability": _fdoc(self.lower_probability),
            "upper_probability": _fdoc(self.upper_probability),
        }

    @property
    def event_id(self) -> str:
        return self._event_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "event_id": self.event_id}


_REGISTERED_TARGET_CONFIDENCE_AUTHORITY_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredTargetConfidenceProjectionAuthorityV1:
    """Exact independent-replay output; direct construction is disabled."""

    _minting_capability: object
    anchor_id: str
    final_preregistration_id: str
    row_evidence: cold.ColdRowEvidenceV1
    event_intervals: tuple[RegisteredConfidenceEventIntervalV1, ...]
    discovery_transcript_id: str
    validation_transcript_id: str
    validation_prefix_id: str
    confidence_verification_id: str
    selected_checkpoint_draw_count: int
    _authority_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.anchor_id, "registered confidence anchor"),
            (
                self.final_preregistration_id,
                "registered confidence final preregistration",
            ),
            (
                self.discovery_transcript_id,
                "registered discovery transcript",
            ),
            (
                self.validation_transcript_id,
                "registered validation transcript",
            ),
            (
                self.validation_prefix_id,
                "registered validation prefix",
            ),
            (
                self.confidence_verification_id,
                "registered confidence verification",
            ),
        ):
            _cid(value, label)
        if (
            self._minting_capability
            is not _REGISTERED_TARGET_CONFIDENCE_AUTHORITY_SENTINEL
            or REGISTERED_TARGET_CONFIDENCE_AUTHORITY_ENABLED is not True
            or type(self.row_evidence) is not cold.ColdRowEvidenceV1
            or type(self.event_intervals) is not tuple
            or len(self.event_intervals)
            != len(self.row_evidence.discovery_support) + 1
            or any(
                type(item) is not RegisteredConfidenceEventIntervalV1
                for item in self.event_intervals
            )
            or tuple(
                item.event_ordinal for item in self.event_intervals
            )
            != tuple(range(len(self.event_intervals)))
            or tuple(
                item.descriptor_record_id
                for item in self.event_intervals[:-1]
            )
            != tuple(
                item.descriptor_record_id
                for item in self.row_evidence.discovery_support
            )
            or any(
                item.event_kind
                is not RegisteredConfidenceEventKindV1.SUPPORT
                for item in self.event_intervals[:-1]
            )
            or self.event_intervals[-1].event_kind
            is not RegisteredConfidenceEventKindV1.OTHER
            or sum(
                item.lower_probability for item in self.event_intervals
            )
            > 1
            or sum(
                item.upper_probability for item in self.event_intervals
            )
            < 1
            or type(self.selected_checkpoint_draw_count) is not int
            or self.selected_checkpoint_draw_count
            not in (2_048, 4_096, 8_192, 16_384)
        ):
            raise V072ConfidenceRowProjectionInvariantViolation(
                "registered confidence authority is unminted, incomplete, "
                "or inconsistent with its exact row evidence"
            )
        object.__setattr__(
            self,
            "_authority_id",
            _content_id("registered_authority", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_confidence_projection_authority.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "anchor_id": self.anchor_id,
            "final_preregistration_id": self.final_preregistration_id,
            "row_evidence_id": self.row_evidence.row_evidence_id,
            "event_ids": [item.event_id for item in self.event_intervals],
            "discovery_transcript_id": self.discovery_transcript_id,
            "validation_transcript_id": self.validation_transcript_id,
            "validation_prefix_id": self.validation_prefix_id,
            "confidence_verification_id": (
                self.confidence_verification_id
            ),
            "selected_checkpoint_draw_count": (
                self.selected_checkpoint_draw_count
            ),
            "rank_cap": prereg.RANK_CAP,
            "registered_target_evidence": True,
            "caller_supplied_intervals_allowed": False,
        }

    @property
    def authority_id(self) -> str:
        return self._authority_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "event_intervals": [
                item.to_document() for item in self.event_intervals
            ],
            "authority_id": self.authority_id,
        }


def mint_registered_target_confidence_projection_authority_v1(
    *,
    replay_attestation: Any,
    row_evidence: cold.ColdRowEvidenceV1,
    event_intervals: tuple[RegisteredConfidenceEventIntervalV1, ...],
) -> RegisteredTargetConfidenceProjectionAuthorityV1:
    """Mint only from the private, exact independent replay attestation."""

    # Local imports prevent module cycles while preserving exact concrete
    # type checks.  Both accepted attestations have private verifier-only
    # mints; the matched-direct type is intentionally not an adaptive type.
    from acfqp import (
        v072_registered_target_confidence_independent_verifier_v1
        as independent,
    )
    from acfqp import (
        v072_registered_matched_direct_complete_inventory_v1
        as matched_direct,
    )

    if (
        type(replay_attestation)
        not in (
            independent
            .RegisteredTargetConfidenceIndependentReplayAttestationV1,
            matched_direct
            .RegisteredMatchedDirectConfidenceReplayAttestationV1,
        )
        or type(row_evidence) is not cold.ColdRowEvidenceV1
        or type(event_intervals) is not tuple
        or any(
            type(item) is not RegisteredConfidenceEventIntervalV1
            for item in event_intervals
        )
        or replay_attestation.row_evidence_id
        != row_evidence.row_evidence_id
        or replay_attestation.support_epoch_id
        != row_evidence.support_epoch_id
        or replay_attestation.support_descriptor_record_ids
        != tuple(
            item.descriptor_record_id
            for item in row_evidence.discovery_support
        )
        or replay_attestation.validation_novel_descriptor_record_ids
        != tuple(
            item.descriptor_record_id
            for item in row_evidence.validation_novel
        )
        or replay_attestation.event_ids
        != tuple(item.event_id for item in event_intervals)
        or replay_attestation.event_success_counts
        == ()
        or replay_attestation.event_probability_intervals
        != tuple(
            (item.lower_probability, item.upper_probability)
            for item in event_intervals
        )
        or replay_attestation.selected_checkpoint_draw_count
        != sum(replay_attestation.event_success_counts)
        or replay_attestation.replayed_draw_calls
        not in (
            replay_attestation.selected_checkpoint_draw_count,
            replay_attestation.selected_checkpoint_draw_count
            + prereg.INITIAL_DISCOVERY_DRAWS_PER_PHYSICAL_ROW,
        )
    ):
        raise RegisteredTargetConfidenceProjectionLockedV1(
            "registered confidence authority requires one exact independent "
            "fresh-stream replay attestation"
        )
    return RegisteredTargetConfidenceProjectionAuthorityV1(
        _REGISTERED_TARGET_CONFIDENCE_AUTHORITY_SENTINEL,
        replay_attestation.anchor_id,
        replay_attestation.final_preregistration_id,
        row_evidence,
        event_intervals,
        replay_attestation.discovery_transcript_id,
        replay_attestation.transcript_id,
        replay_attestation.validation_prefix_id,
        replay_attestation.attestation_id,
        replay_attestation.selected_checkpoint_draw_count,
    )


_REGISTERED_PROJECTION_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredConfidenceIntervalSimplexRowProjectionV1:
    """Rank-cap-6 row projection mechanically derived from one authority."""

    _minting_capability: object
    confidence_authority: RegisteredTargetConfidenceProjectionAuthorityV1
    interval_row: robust.IntervalSimplexRowV1
    destinations: tuple[robust.RegisteredDestinationV1, ...]
    exact_row_reward: Fraction
    _projection_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._minting_capability
            is not _REGISTERED_PROJECTION_MINTING_SENTINEL
            or type(self.confidence_authority)
            is not RegisteredTargetConfidenceProjectionAuthorityV1
            or type(self.interval_row) is not robust.IntervalSimplexRowV1
            or type(self.destinations) is not tuple
            or not self.destinations
            or any(
                type(item) is not robust.RegisteredDestinationV1
                for item in self.destinations
            )
            or tuple(item.destination_id for item in self.destinations)
            != tuple(
                sorted({item.destination_id for item in self.destinations})
            )
            or {
                item.destination_id for item in self.destinations
            }
            != {
                item.destination_id for item in self.interval_row.masses
            }
            or sum(
                item.category is robust.DestinationCategory.OTHER
                for item in self.destinations
            )
            != 1
            or type(self.exact_row_reward) is not Fraction
            or self.interval_row.reward_lower != self.exact_row_reward
            or self.interval_row.reward_upper != self.exact_row_reward
        ):
            raise V072ConfidenceRowProjectionInvariantViolation(
                "registered row projection is incomplete or not mechanical"
            )
        (
            expected_row,
            expected_destinations,
            expected_reward,
        ) = project_registered_interval_events_core_v1(
            row_evidence=self.confidence_authority.row_evidence,
            event_intervals=self.confidence_authority.event_intervals,
        )
        if (
            self.exact_row_reward != expected_reward
            or self.destinations != expected_destinations
            or self.interval_row != expected_row
        ):
            raise V072ConfidenceRowProjectionInvariantViolation(
                "registered projection changed an authority interval, "
                "destination, row/action identity, OTHER, or exact reward"
            )
        object.__setattr__(
            self,
            "_projection_id",
            _content_id("registered_projection", self._payload()),
        )

    @property
    def row_evidence(self) -> cold.ColdRowEvidenceV1:
        return self.confidence_authority.row_evidence

    @property
    def context_id(self) -> str:
        return self.row_evidence.context_id

    @property
    def row_evidence_id(self) -> str:
        return self.row_evidence.row_evidence_id

    @property
    def physical_evidence_id(self) -> str:
        return self.row_evidence.physical_evidence_id

    @property
    def support_epoch_id(self) -> str:
        return self.row_evidence.support_epoch_id

    @property
    def confidence_snapshot_id(self) -> str:
        return self.row_evidence.confidence_snapshot_id

    @property
    def row_replay_verification_id(self) -> str:
        return self.row_evidence.row_replay_verification_id

    @property
    def discovery_transcript_id(self) -> str:
        return self.confidence_authority.discovery_transcript_id

    @property
    def validation_transcript_id(self) -> str:
        return self.confidence_authority.validation_transcript_id

    @property
    def validation_prefix_id(self) -> str:
        return self.confidence_authority.validation_prefix_id

    @property
    def selected_checkpoint_draw_count(self) -> int:
        return (
            self.confidence_authority.selected_checkpoint_draw_count
        )

    @property
    def state_semantic_id(self) -> str:
        return self.row_evidence.state.semantic_state_id

    @property
    def remaining_horizon(self) -> int:
        return self.row_evidence.remaining_horizon

    @property
    def action_semantic_id(self) -> str:
        return self.row_evidence.action.semantic_action_id

    @property
    def discovery_support_descriptor_ids(self) -> tuple[str, ...]:
        return tuple(
            item.descriptor_record_id
            for item in self.row_evidence.discovery_support
        )

    @property
    def validation_novel_descriptor_ids(self) -> tuple[str, ...]:
        return tuple(
            item.descriptor_record_id
            for item in self.row_evidence.validation_novel
        )

    @property
    def rank_cap(self) -> int:
        return prereg.RANK_CAP

    @property
    def rank_profile(self) -> str:
        return PRODUCTION_RANK_PROFILE

    @property
    def registered_target_evidence(self) -> bool:
        return True

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_confidence_interval_"
                "simplex_row_projection.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "confidence_authority_id": (
                self.confidence_authority.authority_id
            ),
            "row_evidence_id": self.row_evidence_id,
            "interval_row_id": self.interval_row.row_id,
            "destination_entry_ids": [
                item.registry_entry_id for item in self.destinations
            ],
            "exact_row_reward": _fdoc(self.exact_row_reward),
            "rank_cap": prereg.RANK_CAP,
            "rank_profile": PRODUCTION_RANK_PROFILE,
            "registered_target_evidence": True,
            "source_prior_quantities_used": False,
        }

    @property
    def projection_id(self) -> str:
        return self._projection_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "confidence_authority": (
                self.confidence_authority.to_document()
            ),
            "interval_row": self.interval_row.to_document(),
            "destinations": [
                item.to_document() for item in self.destinations
            ],
            "projection_id": self.projection_id,
        }


def _registered_exact_row_reward(
    row: cold.ColdRowEvidenceV1,
) -> Fraction:
    state_document = dict(row.state.document)
    action_document = dict(row.action.document)
    ranks = state_document.get("ranks")
    action = action_document.get("action")
    if (
        type(ranks) is not list
        or any(
            type(rank) is not int or not 0 <= rank <= prereg.RANK_CAP
            for rank in ranks
        )
        or type(action) is not list
        or len(action) != 3
        or any(type(item) is not int for item in action)
    ):
        raise V072ConfidenceRowProjectionInvariantViolation(
            "registered row lacks exact public rank/action semantics"
        )
    first, second, survivor = action
    if (
        min(first, second, survivor) < 0
        or max(first, second, survivor) >= len(ranks)
        or first == second
        or survivor not in (first, second)
        or ranks[first] <= 0
        or ranks[first] != ranks[second]
    ):
        raise V072ConfidenceRowProjectionInvariantViolation(
            "registered row action is not one legal equal-rank merge"
        )
    return (
        Fraction(
            2 ** (ranks[first] + 1),
            2 ** (prereg.RANK_CAP + 1),
        )
        / prereg.HORIZON
    )


def project_registered_interval_events_core_v1(
    *,
    row_evidence: cold.ColdRowEvidenceV1,
    event_intervals: tuple[RegisteredConfidenceEventIntervalV1, ...],
) -> tuple[
    robust.IntervalSimplexRowV1,
    tuple[robust.RegisteredDestinationV1, ...],
    Fraction,
]:
    """Pure deterministic projection core with no anchor or target access."""

    if (
        type(row_evidence) is not cold.ColdRowEvidenceV1
        or type(event_intervals) is not tuple
        or len(event_intervals)
        != len(row_evidence.discovery_support) + 1
        or any(
            type(item) is not RegisteredConfidenceEventIntervalV1
            for item in event_intervals
        )
        or tuple(
            item.descriptor_record_id for item in event_intervals[:-1]
        )
        != tuple(
            item.descriptor_record_id
            for item in row_evidence.discovery_support
        )
        or any(
            item.event_kind
            is not RegisteredConfidenceEventKindV1.SUPPORT
            for item in event_intervals[:-1]
        )
        or event_intervals[-1].event_kind
        is not RegisteredConfidenceEventKindV1.OTHER
        or sum(item.lower_probability for item in event_intervals) > 1
        or sum(item.upper_probability for item in event_intervals) < 1
    ):
        raise V072ConfidenceRowProjectionInvariantViolation(
            "projection core requires one complete support-plus-OTHER "
            "interval inventory"
        )
    from acfqp import v072_cold_h2_model_builders_v1 as cold_builder

    reward = _registered_exact_row_reward(row_evidence)
    destinations = tuple(
        sorted(
            (
                *(
                    cold_builder.destination_for_descriptor_v1(
                        row_evidence, descriptor
                    )
                    for descriptor in row_evidence.discovery_support
                ),
                cold_builder.other_destination_for_row_v1(
                    row_evidence
                ),
            ),
            key=lambda item: item.destination_id,
        )
    )
    destination_by_descriptor = {
        descriptor.descriptor_record_id:
            cold_builder.destination_for_descriptor_v1(
                row_evidence, descriptor
            )
        for descriptor in row_evidence.discovery_support
    }
    other = cold_builder.other_destination_for_row_v1(row_evidence)
    masses = tuple(
        sorted(
            (
                robust.IntervalDestinationMassV1(
                    (
                        other.destination_id
                        if event.event_kind
                        is RegisteredConfidenceEventKindV1.OTHER
                        else destination_by_descriptor[
                            event.descriptor_record_id
                        ].destination_id
                    ),
                    event.lower_probability,
                    event.upper_probability,
                )
                for event in event_intervals
            ),
            key=lambda item: item.destination_id,
        )
    )
    interval_row = robust.IntervalSimplexRowV1(
        cold_builder.ground_state_id_v1(
            row_evidence.context_id,
            row_evidence.state,
            row_evidence.remaining_horizon,
        ),
        row_evidence.remaining_horizon,
        cold_builder.ground_action_id_v1(
            row_evidence.context_id,
            row_evidence.state,
            row_evidence.remaining_horizon,
            row_evidence.action,
        ),
        reward,
        reward,
        other.destination_id,
        masses,
    )
    return interval_row, destinations, reward


def project_registered_target_confidence_row_v1(
    *,
    anchor: final_authority.V072RemoteMainAnchorV1,
    confidence_authority: RegisteredTargetConfidenceProjectionAuthorityV1,
) -> RegisteredConfidenceIntervalSimplexRowProjectionV1:
    """Project only an internally minted registered confidence authority."""

    if (
        type(anchor) is not final_authority.V072RemoteMainAnchorV1
        or anchor.target_execution_allowed is not True
        or type(confidence_authority)
        is not RegisteredTargetConfidenceProjectionAuthorityV1
        or confidence_authority.anchor_id != anchor.anchor_id
        or confidence_authority.final_preregistration_id
        != anchor.claim.final_preregistration_id
    ):
        raise RegisteredTargetConfidenceProjectionLockedV1(
            "registered projection requires the exact minted remote-main "
            "anchor and matching target-confidence authority"
        )
    interval_row, destinations, reward = (
        project_registered_interval_events_core_v1(
            row_evidence=confidence_authority.row_evidence,
            event_intervals=confidence_authority.event_intervals,
        )
    )
    return RegisteredConfidenceIntervalSimplexRowProjectionV1(
        _REGISTERED_PROJECTION_MINTING_SENTINEL,
        confidence_authority,
        interval_row,
        destinations,
        reward,
    )


__all__ = [
    "AdversarialOtherDestinationBindingV1",
    "ConfidenceEventDestinationProjectionV1",
    "ConfidenceIntervalSimplexRowProjectionV1",
    "DEVELOPMENT_RANK_PROFILE",
    "ObservedDestinationBindingV1",
    "PROFILE_KEY",
    "PRODUCTION_RANK_PROFILE",
    "PROPOSED_CONTRACT_VERSION",
    "PublicStateActionRowBindingV1",
    "REGISTERED_TARGET_CONFIDENCE_AUTHORITY_ENABLED",
    "REGISTERED_TARGET_PROJECTION_STATUS",
    "RegisteredConfidenceEventIntervalV1",
    "RegisteredConfidenceEventKindV1",
    "RegisteredConfidenceIntervalSimplexRowProjectionV1",
    "RegisteredTargetConfidenceProjectionAuthorityV1",
    "RegisteredTargetConfidenceProjectionLockedV1",
    "SCHEMA_VERSION",
    "V072ConfidenceRowProjectionInvariantViolation",
    "development_synthetic_projection_row_binding_v1",
    "project_confidence_snapshot_to_interval_row_v1",
    "project_registered_interval_events_core_v1",
    "project_registered_target_confidence_row_v1",
    "mint_registered_target_confidence_projection_authority_v1",
]
