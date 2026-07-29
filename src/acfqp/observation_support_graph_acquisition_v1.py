"""Observation-only partial-support graph acquisition for V0-068.

This module joins the narrow transition observer to the split-support
confidence authority.  A row is acquired in two statistically separate
lanes:

1. exactly 64 discovery draws freeze a finite set of stable joint-outcome
   descriptors;
2. a fresh validation stream is extended only through preregistered
   checkpoints and is projected onto that frozen set plus one ``OTHER``.

An outcome descriptor hashes the realized next state, row reward, failure,
and terminal flags.  It never hashes the observation/sample identity, raw
random-word commitment, route, or consumer.  Consequently repeated samples
of the same realized tuple share one outcome identity, while quotient and
direct consumers can share the same route-independent physical prefix.
Logical work charges remain separate content-addressed artifacts.

Novel validation outcomes stay inside ``OTHER`` for the current immutable
epoch.  A second epoch may promote them as proposal-only support members, but
all parent samples are quarantined and the new probability evidence comes
from a fresh observer validation domain.

Neither acquisition nor replay calls an exact atom enumerator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import functools
import hashlib
from typing import Any, Iterable, Mapping

import acfqp.partial_support_confidence_v1 as support_confidence
import acfqp.transition_tuple_observer_v1 as transition_observer
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.32.0"
PROFILE_KEY = "observation_support_graph_acquisition_v0"

DISCOVERY_DRAW_COUNT = 64
VALIDATION_CHECKPOINTS = (2_048, 4_096, 8_192, 16_384)
MAX_SUPPORT_EPOCH_INDEX = 2
ROUTE_INDEPENDENT_SEED_RULE = (
    "CONTEXT_CATALOGUE_ACTION_LANE_SUPPORT_EPOCH_ONLY"
)
LOGICAL_CHARGE_RULE = (
    "SHARED_PHYSICAL_PREFIX_SEPARATE_CONTENT_ADDRESSED_CONSUMER_CHARGES"
)


class ObservationSupportGraphAcquisitionInvariantViolation(ValueError):
    """A row binding, split prefix, epoch lineage, or replay is invalid."""


DOMAIN_TAGS = {
    "outcome": "acfqp:graph-observed-joint-outcome-descriptor:v1",
    "row_binding": "acfqp:graph-observation-support-row-binding:v1",
    "counters": "acfqp:graph-partial-support-acquisition-counters:v1",
    "physical": "acfqp:graph-partial-support-physical-evidence:v1",
    "row": "acfqp:graph-partial-support-row:v1",
    "charge": "acfqp:graph-partial-support-logical-charge:v1",
    "replay": "acfqp:graph-partial-support-row-replay:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("graph partial-support content domains must be unique")


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(domain + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            "probability/reward values must be exact Fractions"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _action(value: Any) -> tuple[int, int, int]:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(item) is not int for item in value)
    ):
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            "ground action must be an exact integer triple"
        )
    return value


def _ids(
    values: Any,
    field: str,
    *,
    sorted_unique: bool = False,
) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            f"{field} must be an exact tuple"
        )
    for value in values:
        _cid(value, field)
    if sorted_unique and values != tuple(sorted(set(values))):
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            f"{field} must be unique and content-ID sorted"
        )
    return values


@dataclass(frozen=True, slots=True)
class GraphObservedOutcomeDescriptorV1:
    """Stable identity of a realized joint tuple, independent of its sample."""

    next_state: transition_observer.SymbolicGraphStateV1
    realized_row_reward: Fraction
    failure: bool
    terminal: bool

    def __post_init__(self) -> None:
        if (
            type(self.next_state)
            is not transition_observer.SymbolicGraphStateV1
            or type(self.realized_row_reward) is not Fraction
            or not 0 <= self.realized_row_reward <= 1
            or type(self.failure) is not bool
            or self.failure != self.next_state.failure
            or type(self.terminal) is not bool
            or (self.failure and not self.terminal)
        ):
            raise ObservationSupportGraphAcquisitionInvariantViolation(
                "observed graph outcome descriptor is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.graph_observed_joint_outcome_descriptor.v1",
            "schema_version": SCHEMA_VERSION,
            "next_state": self.next_state.to_document(),
            "realized_row_reward": _fdoc(self.realized_row_reward),
            "failure": self.failure,
            "terminal": self.terminal,
        }

    @property
    def outcome_id(self) -> str:
        return _content_id("outcome", self._payload())

    @property
    def document(self) -> Mapping[str, Any]:
        return self._payload()

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "outcome_id": self.outcome_id}


def observed_outcome_descriptor_v1(
    observation: transition_observer.ObservedJointTransitionV1,
) -> GraphObservedOutcomeDescriptorV1:
    if (
        type(observation)
        is not transition_observer.ObservedJointTransitionV1
    ):
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            "outcome projection requires one canonical observer tuple"
        )
    return GraphObservedOutcomeDescriptorV1(
        observation.next_state,
        observation.realized_row_reward,
        observation.failure,
        observation.terminal,
    )


@dataclass(frozen=True, slots=True)
class GraphObservationRowBindingV1:
    context_id: str
    catalogue_id: str
    state_id: str
    action: tuple[int, int, int]
    remaining_horizon: int

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "row context"),
            (self.catalogue_id, "row catalogue"),
            (self.state_id, "row state"),
        ):
            _cid(value, field)
        _action(self.action)
        if (
            type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, 2)
        ):
            raise ObservationSupportGraphAcquisitionInvariantViolation(
                "row horizon is outside the registered H=2 profile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.graph_observation_support_row_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "catalogue_id": self.catalogue_id,
            "state_id": self.state_id,
            "action": list(self.action),
            "remaining_horizon": self.remaining_horizon,
        }

    @property
    def row_id(self) -> str:
        return _content_id("row_binding", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "row_id": self.row_id}


def _canonical_row_binding(
    context: transition_observer.PublicGraphContextV1,
    catalogue: transition_observer.LegalActionCatalogueV1,
    action: tuple[int, int, int],
) -> GraphObservationRowBindingV1:
    if (
        type(context) is not transition_observer.PublicGraphContextV1
        or context
        not in transition_observer.registered_public_graph_contexts_v1()
        or type(catalogue)
        is not transition_observer.LegalActionCatalogueV1
        or catalogue.context_id != context.context_id
    ):
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            "graph row binding has a context/catalogue mismatch"
        )
    expected = transition_observer.legal_action_catalogue_v1(
        context,
        catalogue.state,
        catalogue.remaining_horizon,
    )
    if catalogue.to_document() != expected.to_document():
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            "graph row binding received a noncanonical action catalogue"
        )
    selected = _action(action)
    if selected not in catalogue.actions:
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            "graph row action is outside the exact legal catalogue"
        )
    return GraphObservationRowBindingV1(
        context.context_id,
        catalogue.catalogue_id,
        catalogue.state.state_id,
        selected,
        catalogue.remaining_horizon,
    )


@dataclass(frozen=True, slots=True)
class GraphPartialSupportCountersV1:
    support_epoch_index: int
    initial_discovery_draws: int
    prior_validation_draws: int
    current_validation_draws: int
    total_observer_draws: int
    discovery_random_word_calls: int
    discovery_rejections: int
    prior_validation_random_word_calls: int
    prior_validation_rejections: int
    current_validation_random_word_calls: int
    current_validation_rejections: int
    total_random_word_calls: int
    total_rejections: int

    def __post_init__(self) -> None:
        integer_fields = (
            self.support_epoch_index,
            self.initial_discovery_draws,
            self.prior_validation_draws,
            self.current_validation_draws,
            self.total_observer_draws,
            self.discovery_random_word_calls,
            self.discovery_rejections,
            self.prior_validation_random_word_calls,
            self.prior_validation_rejections,
            self.current_validation_random_word_calls,
            self.current_validation_rejections,
            self.total_random_word_calls,
            self.total_rejections,
        )
        if (
            any(type(item) is not int or item < 0 for item in integer_fields)
            or self.support_epoch_index not in (1, 2)
            or self.initial_discovery_draws != DISCOVERY_DRAW_COUNT
            or self.current_validation_draws
            not in VALIDATION_CHECKPOINTS
            or (
                self.support_epoch_index == 1
                and (
                    self.prior_validation_draws
                    or self.prior_validation_random_word_calls
                    or self.prior_validation_rejections
                )
            )
            or (
                self.support_epoch_index == 2
                and self.prior_validation_draws
                not in VALIDATION_CHECKPOINTS
            )
            or self.total_observer_draws
            != (
                self.initial_discovery_draws
                + self.prior_validation_draws
                + self.current_validation_draws
            )
            or self.discovery_random_word_calls
            != self.initial_discovery_draws + self.discovery_rejections
            or self.prior_validation_random_word_calls
            != self.prior_validation_draws
            + self.prior_validation_rejections
            or self.current_validation_random_word_calls
            != self.current_validation_draws
            + self.current_validation_rejections
            or self.total_random_word_calls
            != (
                self.discovery_random_word_calls
                + self.prior_validation_random_word_calls
                + self.current_validation_random_word_calls
            )
            or self.total_rejections
            != (
                self.discovery_rejections
                + self.prior_validation_rejections
                + self.current_validation_rejections
            )
        ):
            raise ObservationSupportGraphAcquisitionInvariantViolation(
                "graph partial-support counters do not reconcile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.graph_partial_support_acquisition_counters.v1",
            "schema_version": SCHEMA_VERSION,
            "support_epoch_index": self.support_epoch_index,
            "initial_discovery_draws": self.initial_discovery_draws,
            "prior_validation_draws": self.prior_validation_draws,
            "current_validation_draws": self.current_validation_draws,
            "total_observer_draws": self.total_observer_draws,
            "discovery_random_word_calls": (
                self.discovery_random_word_calls
            ),
            "discovery_rejections": self.discovery_rejections,
            "prior_validation_random_word_calls": (
                self.prior_validation_random_word_calls
            ),
            "prior_validation_rejections": (
                self.prior_validation_rejections
            ),
            "current_validation_random_word_calls": (
                self.current_validation_random_word_calls
            ),
            "current_validation_rejections": (
                self.current_validation_rejections
            ),
            "total_random_word_calls": self.total_random_word_calls,
            "total_rejections": self.total_rejections,
        }

    @property
    def counters_id(self) -> str:
        return _content_id("counters", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counters_id": self.counters_id}


SupportEpochV1 = (
    support_confidence.FrozenSupportEpochV1
    | support_confidence.PromotedSupportEpochV1
)


def _epoch_index(epoch: SupportEpochV1) -> int:
    if type(epoch) not in (
        support_confidence.FrozenSupportEpochV1,
        support_confidence.PromotedSupportEpochV1,
    ):
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            "partial support row contains a noncanonical epoch"
        )
    return epoch.support_epoch_index


def _descriptor_tuple(
    descriptors: Any,
    field: str,
) -> tuple[GraphObservedOutcomeDescriptorV1, ...]:
    if (
        type(descriptors) is not tuple
        or any(
            type(item) is not GraphObservedOutcomeDescriptorV1
            for item in descriptors
        )
        or tuple(item.outcome_id for item in descriptors)
        != tuple(sorted({item.outcome_id for item in descriptors}))
    ):
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            f"{field} must be unique and outcome-ID sorted"
        )
    return descriptors


def _opaque_matches_descriptor(
    opaque: support_confidence.OpaqueObservedJointOutcomeV1,
    descriptor: GraphObservedOutcomeDescriptorV1,
) -> bool:
    return (
        opaque.outcome_id == descriptor.outcome_id
        and canonical_json_bytes(dict(opaque.document))
        == canonical_json_bytes(dict(descriptor.document))
    )


@dataclass(frozen=True, slots=True)
class GraphPartialSupportRowV1:
    binding: GraphObservationRowBindingV1
    observer_epoch_chain: tuple[
        transition_observer.SupportEpochIdentityV1,
        ...,
    ]
    support_epoch: SupportEpochV1
    confidence_authority: (
        support_confidence.PartialSupportConfidenceAuthorityV1
    )
    support_descriptors: tuple[GraphObservedOutcomeDescriptorV1, ...]
    novel_descriptors: tuple[GraphObservedOutcomeDescriptorV1, ...]
    initial_discovery_observation_ids: tuple[str, ...]
    prior_validation_observation_ids: tuple[str, ...]
    current_validation_observation_ids: tuple[str, ...]
    counters: GraphPartialSupportCountersV1
    other_interval: support_confidence.PartialSupportEventIntervalV1
    parent_row: GraphPartialSupportRowV1 | None = None
    split_support_authority: bool = True
    route_independent_physical_prefix: bool = True
    _physical_evidence_id: str = field(
        init=False,
        repr=False,
        compare=False,
    )
    _partial_row_id: str = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if (
            type(self.binding) is not GraphObservationRowBindingV1
            or type(self.observer_epoch_chain) is not tuple
            or any(
                type(item)
                is not transition_observer.SupportEpochIdentityV1
                for item in self.observer_epoch_chain
            )
            or type(self.confidence_authority)
            is not support_confidence.PartialSupportConfidenceAuthorityV1
            or type(self.counters) is not GraphPartialSupportCountersV1
            or type(self.other_interval)
            is not support_confidence.PartialSupportEventIntervalV1
            or self.split_support_authority is not True
            or self.route_independent_physical_prefix is not True
        ):
            raise ObservationSupportGraphAcquisitionInvariantViolation(
                "graph partial-support row has an invalid concrete schema"
            )
        epoch_index = _epoch_index(self.support_epoch)
        support = _descriptor_tuple(
            self.support_descriptors,
            "support descriptors",
        )
        novel = _descriptor_tuple(
            self.novel_descriptors,
            "novel descriptors",
        )
        discovery_ids = _ids(
            self.initial_discovery_observation_ids,
            "initial discovery observation IDs",
        )
        prior_ids = _ids(
            self.prior_validation_observation_ids,
            "prior validation observation IDs",
        )
        current_ids = _ids(
            self.current_validation_observation_ids,
            "current validation observation IDs",
        )
        if (
            len(discovery_ids) != DISCOVERY_DRAW_COUNT
            or len(set(discovery_ids)) != len(discovery_ids)
            or len(prior_ids) != self.counters.prior_validation_draws
            or len(set(prior_ids)) != len(prior_ids)
            or len(current_ids) != self.counters.current_validation_draws
            or len(set(current_ids)) != len(current_ids)
            or set(discovery_ids) & set(prior_ids)
            or set(discovery_ids) & set(current_ids)
            or set(prior_ids) & set(current_ids)
            or self.counters.support_epoch_index != epoch_index
            or len(self.observer_epoch_chain) != epoch_index + 1
            or tuple(
                item.epoch_index for item in self.observer_epoch_chain
            )
            != tuple(range(epoch_index + 1))
            or any(
                item.context_id != self.binding.context_id
                for item in self.observer_epoch_chain
            )
            or any(
                self.observer_epoch_chain[index].parent_epoch_id
                != self.observer_epoch_chain[index - 1].epoch_id
                for index in range(1, len(self.observer_epoch_chain))
            )
            or self.observer_epoch_chain[0].parent_epoch_id is not None
            or self.support_epoch.row_id != self.binding.row_id
            or self.confidence_authority.support_epoch
            != self.support_epoch
            or self.confidence_authority.validation_evidence.sample_ids
            != current_ids
            or self.other_interval
            != self.confidence_authority.event_intervals[-1]
            or self.other_interval.event_kind
            is not support_confidence.PartialSupportEventKind.OTHER
            or tuple(item.outcome_id for item in support)
            != self.support_epoch.support_outcome_ids
            or tuple(item.outcome_id for item in novel)
            != self.confidence_authority.novel_outcome_ids
            or set(item.outcome_id for item in support)
            & set(item.outcome_id for item in novel)
        ):
            raise ObservationSupportGraphAcquisitionInvariantViolation(
                "graph partial-support row identity or split lineage changed"
            )
        support_by_id = {item.outcome_id: item for item in support}
        if any(
            not _opaque_matches_descriptor(
                opaque,
                support_by_id[opaque.outcome_id],
            )
            for opaque in self.support_epoch.support_outcomes
        ):
            raise ObservationSupportGraphAcquisitionInvariantViolation(
                "support descriptor document differs from confidence authority"
            )
        validation_by_outcome = {
            item.outcome.outcome_id: item.outcome
            for item in self.confidence_authority.validation_evidence.observations
        }
        novel_by_id = {item.outcome_id: item for item in novel}
        if any(
            not _opaque_matches_descriptor(
                validation_by_outcome[outcome_id],
                novel_by_id[outcome_id],
            )
            for outcome_id in self.confidence_authority.novel_outcome_ids
        ):
            raise ObservationSupportGraphAcquisitionInvariantViolation(
                "novel descriptor document differs from validation evidence"
            )
        expected_excluded = set(discovery_ids) | set(prior_ids)
        if (
            set(self.support_epoch.excluded_probability_sample_ids)
            != expected_excluded
        ):
            raise ObservationSupportGraphAcquisitionInvariantViolation(
                "support epoch does not quarantine all proposal-only samples"
            )
        if epoch_index == 1:
            if (
                self.parent_row is not None
                or prior_ids
                or type(self.support_epoch)
                is not support_confidence.FrozenSupportEpochV1
                or self.support_epoch.discovery_evidence.sample_ids
                != discovery_ids
            ):
                raise ObservationSupportGraphAcquisitionInvariantViolation(
                    "initial support row has a parent or changed discovery"
                )
        else:
            if (
                type(self.parent_row) is not GraphPartialSupportRowV1
                or self.parent_row.support_epoch.support_epoch_index
                != epoch_index - 1
                or self.parent_row.partial_row_id
                != self.support_epoch.parent_support_epoch_id
                and self.parent_row.support_epoch.support_epoch_id
                != self.support_epoch.parent_support_epoch_id
                or self.parent_row.binding != self.binding
                or self.parent_row.observer_epoch_chain
                != self.observer_epoch_chain[:-1]
                or prior_ids
                != (
                    self.parent_row.prior_validation_observation_ids
                    + self.parent_row.current_validation_observation_ids
                )
            ):
                raise ObservationSupportGraphAcquisitionInvariantViolation(
                    "promoted support row is not the next immutable epoch"
                )
        object.__setattr__(
            self,
            "_physical_evidence_id",
            _content_id("physical", self._physical_payload()),
        )
        object.__setattr__(
            self,
            "_partial_row_id",
            _content_id("row", self._payload()),
        )

    @property
    def support_epoch_index(self) -> int:
        return self.support_epoch.support_epoch_index

    def _physical_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.graph_partial_support_physical_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "binding_id": self.binding.row_id,
            "observer_epoch_ids": [
                item.epoch_id for item in self.observer_epoch_chain
            ],
            "split_support_epoch_id": self.support_epoch.support_epoch_id,
            "confidence_authority_id": self.confidence_authority.authority_id,
            "initial_discovery_observation_ids": list(
                self.initial_discovery_observation_ids
            ),
            "prior_validation_observation_ids": list(
                self.prior_validation_observation_ids
            ),
            "current_validation_observation_ids": list(
                self.current_validation_observation_ids
            ),
            "counters_id": self.counters.counters_id,
        }

    @property
    def physical_evidence_id(self) -> str:
        return self._physical_evidence_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.graph_partial_support_row.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "binding_id": self.binding.row_id,
            "support_epoch_index": self.support_epoch_index,
            "observer_epoch_ids": [
                item.epoch_id for item in self.observer_epoch_chain
            ],
            "split_support_epoch_id": self.support_epoch.support_epoch_id,
            "confidence_authority_id": self.confidence_authority.authority_id,
            "support_descriptors": [
                item.to_document() for item in self.support_descriptors
            ],
            "novel_descriptors": [
                item.to_document() for item in self.novel_descriptors
            ],
            "other_interval_id": self.other_interval.event_interval_id,
            "other_lower_probability": _fdoc(
                self.other_interval.lower_probability
            ),
            "other_upper_probability": _fdoc(
                self.other_interval.upper_probability
            ),
            "counters_id": self.counters.counters_id,
            "physical_evidence_id": self.physical_evidence_id,
            "parent_row": (
                {"kind": "ROOT"}
                if self.parent_row is None
                else {
                    "kind": "PREDECESSOR",
                    "partial_row_id": self.parent_row.partial_row_id,
                }
            ),
            "split_support_authority": True,
            "route_independent_physical_prefix": True,
            "route_independent_seed_rule": ROUTE_INDEPENDENT_SEED_RULE,
        }

    @property
    def partial_row_id(self) -> str:
        return self._partial_row_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "binding": self.binding.to_document(),
            "support_epoch": self.support_epoch.to_document(),
            "confidence_authority": (
                self.confidence_authority.to_document()
            ),
            "counters": self.counters.to_document(),
            "partial_row_id": self.partial_row_id,
        }


def _split_observation(
    observation: transition_observer.ObservedJointTransitionV1,
    stream_domain_id: str,
    sequence_index: int,
    outcome_cache: dict[
        tuple[str, Fraction, bool, bool],
        tuple[
            GraphObservedOutcomeDescriptorV1,
            support_confidence.OpaqueObservedJointOutcomeV1,
        ],
    ],
) -> tuple[
    support_confidence.SplitSupportObservationV1,
    GraphObservedOutcomeDescriptorV1,
    str,
]:
    key = (
        observation.next_state.state_id,
        observation.realized_row_reward,
        observation.failure,
        observation.terminal,
    )
    cached = outcome_cache.get(key)
    if cached is None:
        descriptor = observed_outcome_descriptor_v1(observation)
        opaque = support_confidence.freeze_observed_joint_outcome_v1(
            descriptor
        )
        outcome_cache[key] = (descriptor, opaque)
    else:
        descriptor, opaque = cached
    observation_id = observation.observation_id
    return (
        support_confidence.SplitSupportObservationV1(
            stream_domain_id=stream_domain_id,
            sample_id=observation_id,
            sequence_index=sequence_index,
            outcome=opaque,
        ),
        descriptor,
        observation_id,
    )


def _representative_descriptors(
    descriptors: Iterable[GraphObservedOutcomeDescriptorV1],
) -> tuple[GraphObservedOutcomeDescriptorV1, ...]:
    by_id: dict[str, GraphObservedOutcomeDescriptorV1] = {}
    for descriptor in descriptors:
        previous = by_id.setdefault(descriptor.outcome_id, descriptor)
        if previous != descriptor:
            raise ObservationSupportGraphAcquisitionInvariantViolation(
                "one outcome ID is bound to two symbolic descriptors"
            )
    return tuple(by_id[key] for key in sorted(by_id))


class _GraphPartialSupportPrefixStreamV1:
    """Mutable physical prefix; snapshots are immutable row artifacts."""

    __slots__ = (
        "_context",
        "_catalogue",
        "_action",
        "_binding",
        "_observer_epochs",
        "_discovery_stream",
        "_validation_stream",
        "_discovery_observer_ids",
        "_discovery_split",
        "_support_descriptors",
        "_validation_observer_ids",
        "_validation_split",
        "_validation_descriptors",
        "_support_epoch",
        "_outcome_projection_cache",
    )

    def __init__(
        self,
        context: transition_observer.PublicGraphContextV1,
        catalogue: transition_observer.LegalActionCatalogueV1,
        action: tuple[int, int, int],
    ) -> None:
        self._binding = _canonical_row_binding(
            context,
            catalogue,
            action,
        )
        self._context = context
        self._catalogue = catalogue
        self._action = action
        self._outcome_projection_cache = {}
        discovery_epoch = transition_observer.support_epoch_identity_v1(
            context,
            0,
        )
        self._discovery_stream = (
            transition_observer.open_target_local_transition_stream_v1(
                context,
                catalogue,
                action,
                transition_observer.ObservationLane.DISCOVERY,
                discovery_epoch,
            )
        )
        discovery_observer_ids: list[str] = []
        discovery_split: list[
            support_confidence.SplitSupportObservationV1
        ] = []
        discovery_descriptors: list[
            GraphObservedOutcomeDescriptorV1
        ] = []
        for index in range(DISCOVERY_DRAW_COUNT):
            observation = self._discovery_stream.draw()
            split, descriptor, observation_id = _split_observation(
                observation,
                self._discovery_stream.stream_id,
                index,
                self._outcome_projection_cache,
            )
            discovery_observer_ids.append(observation_id)
            discovery_split.append(split)
            discovery_descriptors.append(descriptor)
        support_descriptors = _representative_descriptors(
            discovery_descriptors
        )
        validation_epoch = transition_observer.support_epoch_identity_v1(
            context,
            1,
            tuple(item.outcome_id for item in support_descriptors),
            discovery_epoch,
        )
        self._observer_epochs = (
            discovery_epoch,
            validation_epoch,
        )
        self._validation_stream = (
            transition_observer.open_target_local_transition_stream_v1(
                context,
                catalogue,
                action,
                transition_observer.ObservationLane.VALIDATION,
                validation_epoch,
            )
        )
        self._support_epoch = (
            support_confidence.freeze_support_epoch_v1(
                row_id=self._binding.row_id,
                support_epoch_index=1,
                discovery_stream_domain_id=(
                    self._discovery_stream.stream_id
                ),
                validation_stream_domain_id=(
                    self._validation_stream.stream_id
                ),
                discovery_observations=tuple(discovery_split),
            )
        )
        self._discovery_observer_ids = tuple(discovery_observer_ids)
        self._discovery_split = tuple(discovery_split)
        self._support_descriptors = support_descriptors
        self._validation_observer_ids: list[str] = []
        self._validation_split: list[
            support_confidence.SplitSupportObservationV1
        ] = []
        self._validation_descriptors: list[
            GraphObservedOutcomeDescriptorV1
        ] = []

    @property
    def row_id(self) -> str:
        return self._binding.row_id

    @property
    def current_validation_draw_count(self) -> int:
        return len(self._validation_split)

    def extend_validation_to(
        self,
        checkpoint_draw_count: int,
    ) -> GraphPartialSupportRowV1:
        if (
            type(checkpoint_draw_count) is not int
            or checkpoint_draw_count not in VALIDATION_CHECKPOINTS
            or checkpoint_draw_count < len(self._validation_split)
        ):
            raise ObservationSupportGraphAcquisitionInvariantViolation(
                "validation extension violates checkpoints or chronology"
            )
        while len(self._validation_split) < checkpoint_draw_count:
            observation = self._validation_stream.draw()
            split, descriptor, observation_id = _split_observation(
                observation,
                self._validation_stream.stream_id,
                len(self._validation_split),
                self._outcome_projection_cache,
            )
            self._validation_observer_ids.append(observation_id)
            self._validation_split.append(split)
            self._validation_descriptors.append(descriptor)
        authority = (
            support_confidence.build_partial_support_confidence_v1(
                self._support_epoch,
                tuple(self._validation_split),
            )
        )
        support_ids = set(self._support_epoch.support_outcome_ids)
        novel = _representative_descriptors(
            item
            for item in self._validation_descriptors
            if item.outcome_id not in support_ids
        )
        discovery_work = self._discovery_stream.work_snapshot()
        validation_work = self._validation_stream.work_snapshot()
        counters = GraphPartialSupportCountersV1(
            1,
            DISCOVERY_DRAW_COUNT,
            0,
            checkpoint_draw_count,
            DISCOVERY_DRAW_COUNT + checkpoint_draw_count,
            discovery_work.random_word_calls,
            discovery_work.rejection_count,
            0,
            0,
            validation_work.random_word_calls,
            validation_work.rejection_count,
            discovery_work.random_word_calls
            + validation_work.random_word_calls,
            discovery_work.rejection_count
            + validation_work.rejection_count,
        )
        return GraphPartialSupportRowV1(
            self._binding,
            self._observer_epochs,
            self._support_epoch,
            authority,
            self._support_descriptors,
            novel,
            self._discovery_observer_ids,
            (),
            tuple(self._validation_observer_ids),
            counters,
            authority.event_intervals[-1],
        )


def open_graph_partial_support_prefix_v1(
    context: transition_observer.PublicGraphContextV1,
    catalogue: transition_observer.LegalActionCatalogueV1,
    action: tuple[int, int, int],
) -> _GraphPartialSupportPrefixStreamV1:
    return _GraphPartialSupportPrefixStreamV1(
        context,
        catalogue,
        action,
    )


@functools.lru_cache(maxsize=128)
def acquire_graph_partial_support_row_v1(
    context: transition_observer.PublicGraphContextV1,
    catalogue: transition_observer.LegalActionCatalogueV1,
    action: tuple[int, int, int],
    checkpoint_draw_count: int = VALIDATION_CHECKPOINTS[0],
) -> GraphPartialSupportRowV1:
    """Acquire one cached route-independent initial physical prefix."""

    prefix = open_graph_partial_support_prefix_v1(
        context,
        catalogue,
        action,
    )
    return prefix.extend_validation_to(checkpoint_draw_count)


def _promote_graph_partial_support_row_uncached_v1(
    parent_row: GraphPartialSupportRowV1,
    context: transition_observer.PublicGraphContextV1,
    catalogue: transition_observer.LegalActionCatalogueV1,
    action: tuple[int, int, int],
    checkpoint_draw_count: int,
) -> GraphPartialSupportRowV1:
    binding = _canonical_row_binding(context, catalogue, action)
    if (
        type(parent_row) is not GraphPartialSupportRowV1
        or parent_row.support_epoch_index != 1
        or parent_row.binding != binding
        or not parent_row.novel_descriptors
        or checkpoint_draw_count not in VALIDATION_CHECKPOINTS
    ):
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            "epoch-2 promotion requires one matching novel epoch-1 row"
        )
    promoted_support = _representative_descriptors(
        (
            *parent_row.support_descriptors,
            *parent_row.novel_descriptors,
        )
    )
    observer_epoch = transition_observer.support_epoch_identity_v1(
        context,
        2,
        tuple(item.outcome_id for item in promoted_support),
        parent_row.observer_epoch_chain[-1],
    )
    validation_stream = (
        transition_observer.open_target_local_transition_stream_v1(
            context,
            catalogue,
            action,
            transition_observer.ObservationLane.VALIDATION,
            observer_epoch,
        )
    )
    support_epoch = support_confidence.promote_support_epoch_v1(
        parent_row.confidence_authority,
        next_validation_stream_domain_id=validation_stream.stream_id,
    )
    validation_observer_ids: list[str] = []
    validation_split: list[
        support_confidence.SplitSupportObservationV1
    ] = []
    validation_descriptors: list[
        GraphObservedOutcomeDescriptorV1
    ] = []
    outcome_projection_cache: dict[
        tuple[str, Fraction, bool, bool],
        tuple[
            GraphObservedOutcomeDescriptorV1,
            support_confidence.OpaqueObservedJointOutcomeV1,
        ],
    ] = {}
    for index in range(checkpoint_draw_count):
        observation = validation_stream.draw()
        split, descriptor, observation_id = _split_observation(
            observation,
            validation_stream.stream_id,
            index,
            outcome_projection_cache,
        )
        validation_observer_ids.append(observation_id)
        validation_split.append(split)
        validation_descriptors.append(descriptor)
    authority = support_confidence.build_partial_support_confidence_v1(
        support_epoch,
        tuple(validation_split),
    )
    support_ids = set(support_epoch.support_outcome_ids)
    novel = _representative_descriptors(
        item
        for item in validation_descriptors
        if item.outcome_id not in support_ids
    )
    validation_work = validation_stream.work_snapshot()
    parent_counters = parent_row.counters
    prior_validation_draws = (
        parent_counters.prior_validation_draws
        + parent_counters.current_validation_draws
    )
    prior_validation_words = (
        parent_counters.prior_validation_random_word_calls
        + parent_counters.current_validation_random_word_calls
    )
    prior_validation_rejections = (
        parent_counters.prior_validation_rejections
        + parent_counters.current_validation_rejections
    )
    counters = GraphPartialSupportCountersV1(
        2,
        DISCOVERY_DRAW_COUNT,
        prior_validation_draws,
        checkpoint_draw_count,
        DISCOVERY_DRAW_COUNT
        + prior_validation_draws
        + checkpoint_draw_count,
        parent_counters.discovery_random_word_calls,
        parent_counters.discovery_rejections,
        prior_validation_words,
        prior_validation_rejections,
        validation_work.random_word_calls,
        validation_work.rejection_count,
        parent_counters.discovery_random_word_calls
        + prior_validation_words
        + validation_work.random_word_calls,
        parent_counters.discovery_rejections
        + prior_validation_rejections
        + validation_work.rejection_count,
    )
    return GraphPartialSupportRowV1(
        binding,
        (*parent_row.observer_epoch_chain, observer_epoch),
        support_epoch,
        authority,
        promoted_support,
        novel,
        parent_row.initial_discovery_observation_ids,
        (
            parent_row.prior_validation_observation_ids
            + parent_row.current_validation_observation_ids
        ),
        tuple(validation_observer_ids),
        counters,
        authority.event_intervals[-1],
        parent_row,
    )


@functools.lru_cache(maxsize=64)
def promote_graph_partial_support_row_v1(
    parent_row: GraphPartialSupportRowV1,
    context: transition_observer.PublicGraphContextV1,
    catalogue: transition_observer.LegalActionCatalogueV1,
    action: tuple[int, int, int],
    checkpoint_draw_count: int = VALIDATION_CHECKPOINTS[0],
) -> GraphPartialSupportRowV1:
    """Promote parent novel outcomes and acquire a fresh validation prefix."""

    return _promote_graph_partial_support_row_uncached_v1(
        parent_row,
        context,
        catalogue,
        action,
        checkpoint_draw_count,
    )


@dataclass(frozen=True, slots=True)
class GraphPartialSupportLogicalChargeV1:
    logical_consumer_id: str
    partial_row_id: str
    physical_evidence_id: str
    counters: GraphPartialSupportCountersV1
    shared_physical_computation_allowed: bool = True
    logical_charge_rule: str = LOGICAL_CHARGE_RULE

    def __post_init__(self) -> None:
        for value, field in (
            (self.logical_consumer_id, "logical consumer"),
            (self.partial_row_id, "charged partial row"),
            (self.physical_evidence_id, "charged physical evidence"),
        ):
            _cid(value, field)
        if (
            type(self.counters) is not GraphPartialSupportCountersV1
            or self.shared_physical_computation_allowed is not True
            or self.logical_charge_rule != LOGICAL_CHARGE_RULE
        ):
            raise ObservationSupportGraphAcquisitionInvariantViolation(
                "logical partial-support charge is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.graph_partial_support_logical_charge.v1",
            "schema_version": SCHEMA_VERSION,
            "logical_consumer_id": self.logical_consumer_id,
            "partial_row_id": self.partial_row_id,
            "physical_evidence_id": self.physical_evidence_id,
            "counters_id": self.counters.counters_id,
            "shared_physical_computation_allowed": True,
            "logical_charge_rule": self.logical_charge_rule,
        }

    @property
    def charge_id(self) -> str:
        return _content_id("charge", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "counters": self.counters.to_document(),
            "charge_id": self.charge_id,
        }


def charge_graph_partial_support_row_v1(
    row: GraphPartialSupportRowV1,
    logical_consumer_id: str,
) -> GraphPartialSupportLogicalChargeV1:
    if type(row) is not GraphPartialSupportRowV1:
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            "logical charge requires one canonical partial-support row"
        )
    _cid(logical_consumer_id, "logical consumer")
    return GraphPartialSupportLogicalChargeV1(
        logical_consumer_id,
        row.partial_row_id,
        row.physical_evidence_id,
        row.counters,
    )


@dataclass(frozen=True, slots=True)
class GraphPartialSupportReplayVerificationV1:
    partial_row_id: str
    physical_evidence_id: str
    confidence_verification_id: str
    replayed_support_epoch_index: int
    replayed_observer_draws: int
    replayed_random_word_calls: int
    replayed_rejections: int
    exact_atom_enumerator_calls: int = 0
    replay_result: str = "VALID_OBSERVATION_ONLY_PARTIAL_SUPPORT_ROW"

    def __post_init__(self) -> None:
        for value, field in (
            (self.partial_row_id, "replay partial row"),
            (self.physical_evidence_id, "replay physical evidence"),
            (
                self.confidence_verification_id,
                "replay confidence verification",
            ),
        ):
            _cid(value, field)
        if (
            type(self.replayed_support_epoch_index) is not int
            or self.replayed_support_epoch_index not in (1, 2)
            or type(self.replayed_observer_draws) is not int
            or self.replayed_observer_draws <= 0
            or type(self.replayed_random_word_calls) is not int
            or self.replayed_random_word_calls
            < self.replayed_observer_draws
            or type(self.replayed_rejections) is not int
            or self.replayed_rejections < 0
            or self.replayed_random_word_calls
            != self.replayed_observer_draws + self.replayed_rejections
            or self.exact_atom_enumerator_calls != 0
            or self.replay_result
            != "VALID_OBSERVATION_ONLY_PARTIAL_SUPPORT_ROW"
        ):
            raise ObservationSupportGraphAcquisitionInvariantViolation(
                "graph partial-support replay result is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.graph_partial_support_row_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "partial_row_id": self.partial_row_id,
            "physical_evidence_id": self.physical_evidence_id,
            "confidence_verification_id": (
                self.confidence_verification_id
            ),
            "replayed_support_epoch_index": (
                self.replayed_support_epoch_index
            ),
            "replayed_observer_draws": self.replayed_observer_draws,
            "replayed_random_word_calls": (
                self.replayed_random_word_calls
            ),
            "replayed_rejections": self.replayed_rejections,
            "exact_atom_enumerator_calls": 0,
            "replay_result": self.replay_result,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("replay", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_graph_partial_support_row_v1(
    context: transition_observer.PublicGraphContextV1,
    catalogue: transition_observer.LegalActionCatalogueV1,
    action: tuple[int, int, int],
    row: GraphPartialSupportRowV1,
) -> GraphPartialSupportReplayVerificationV1:
    """Regenerate the consumed prefixes and rebuild the confidence authority."""

    if type(row) is not GraphPartialSupportRowV1:
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            "standalone replay requires a concrete graph partial-support row"
        )
    binding = _canonical_row_binding(context, catalogue, action)
    if row.binding != binding:
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            "standalone replay row binding mismatch"
        )
    if row.support_epoch_index == 1:
        prefix = open_graph_partial_support_prefix_v1(
            context,
            catalogue,
            action,
        )
        rebuilt = prefix.extend_validation_to(
            row.counters.current_validation_draws
        )
    else:
        if type(row.parent_row) is not GraphPartialSupportRowV1:
            raise ObservationSupportGraphAcquisitionInvariantViolation(
                "promoted replay is missing its parent row"
            )
        verify_graph_partial_support_row_v1(
            context,
            catalogue,
            action,
            row.parent_row,
        )
        rebuilt = _promote_graph_partial_support_row_uncached_v1(
            row.parent_row,
            context,
            catalogue,
            action,
            row.counters.current_validation_draws,
        )
    if rebuilt != row or rebuilt.to_document() != row.to_document():
        raise ObservationSupportGraphAcquisitionInvariantViolation(
            "graph partial-support row differs from standalone prefix replay"
        )
    confidence_verification = (
        support_confidence.verify_partial_support_confidence_v1(
            row.confidence_authority
        )
    )
    return GraphPartialSupportReplayVerificationV1(
        row.partial_row_id,
        row.physical_evidence_id,
        confidence_verification.verification_id,
        row.support_epoch_index,
        row.counters.total_observer_draws,
        row.counters.total_random_word_calls,
        row.counters.total_rejections,
    )


__all__ = [
    "CONTRACT_VERSION",
    "DISCOVERY_DRAW_COUNT",
    "GraphObservationRowBindingV1",
    "GraphObservedOutcomeDescriptorV1",
    "GraphPartialSupportCountersV1",
    "GraphPartialSupportLogicalChargeV1",
    "GraphPartialSupportReplayVerificationV1",
    "GraphPartialSupportRowV1",
    "LOGICAL_CHARGE_RULE",
    "MAX_SUPPORT_EPOCH_INDEX",
    "ObservationSupportGraphAcquisitionInvariantViolation",
    "PROFILE_KEY",
    "ROUTE_INDEPENDENT_SEED_RULE",
    "SCHEMA_VERSION",
    "VALIDATION_CHECKPOINTS",
    "acquire_graph_partial_support_row_v1",
    "charge_graph_partial_support_row_v1",
    "observed_outcome_descriptor_v1",
    "open_graph_partial_support_prefix_v1",
    "promote_graph_partial_support_row_v1",
    "verify_graph_partial_support_row_v1",
]
