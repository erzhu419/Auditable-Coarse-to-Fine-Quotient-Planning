"""Kernel-free bridge from observed graph rows to robust H=2 models.

The bridge consumes only public symbolic catalogues, immutable split-support
rows, and portable relational coordinates.  It builds two views over exactly
the same interval-simplex rows:

* a direct view whose state/action coordinates are their ground identities;
* a quotient view whose coordinates come from the frozen relational profile
  and whose semantic actions use a uniform distinct-action concretizer.

Every discovery-known joint outcome retains its own destination identity.
There is exactly one context-wide ``OTHER`` destination.  No exact support,
probability, hidden-law, or evaluation-only authority is imported or called.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Iterable, Mapping

import acfqp.observation_support_graph_acquisition_v1 as acquisition
import acfqp.observation_support_relational_adapter_v1 as relational
import acfqp.partial_support_confidence_v1 as confidence
import acfqp.partial_support_robust_planner_v1 as robust
import acfqp.transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.32.0"
PROFILE_KEY = "observation_support_graph_model_bridge_v0"
REGISTERED_REWARD_CEILING = Fraction(3, 64)
OTHER_ESCAPE_BEHAVIOR = "ABSORBING_POLICY_ABORT_FAILURE"

DOMAIN_TAGS = {
    "action": "acfqp:observation-support-ground-action-binding:v1",
    "coordinate": "acfqp:observation-support-relational-coordinate:v1",
    "destination": "acfqp:observation-support-outcome-destination:v1",
    "other": "acfqp:observation-support-global-other-destination:v1",
    "other_escape": (
        "acfqp:observation-support-other-outcome-escape-handler:v1"
    ),
    "event_destination": (
        "acfqp:observation-support-event-destination-projection:v1"
    ),
    "row_projection": "acfqp:observation-support-row-model-projection:v1",
    "bridge": "acfqp:observation-support-graph-model-bridge:v1",
    "verification": "acfqp:observation-support-graph-model-replay:v1",
}


class ObservationSupportGraphModelInvariantViolation(ValueError):
    """A catalogue, observed row, coordinate, or model binding is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        tag = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise ObservationSupportGraphModelInvariantViolation(str(error)) from error
    return hashlib.sha256(tag + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ObservationSupportGraphModelInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise ObservationSupportGraphModelInvariantViolation(
            "reward/probability must be an exact Fraction"
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
        raise ObservationSupportGraphModelInvariantViolation(
            "ground action must be an exact integer triple"
        )
    return value


def _coordinate_document(value: Any) -> Any:
    """Convert a portable tagged coordinate to strict canonical JSON."""

    if value is None or type(value) in {str, bool, int}:
        return value
    if type(value) is Fraction:
        return _fdoc(value)
    if type(value) is tuple:
        return [_coordinate_document(item) for item in value]
    raise ObservationSupportGraphModelInvariantViolation(
        "portable coordinate contains an unsupported value"
    )


class RelationalCoordinateRole(str, Enum):
    STATE = "STATE"
    ACTION = "ACTION"
    SUPPORT = "SUPPORT"


@dataclass(frozen=True, slots=True)
class GraphGroundActionBindingV1:
    context_id: str
    catalogue_id: str
    state_id: str
    remaining_horizon: int
    action: tuple[int, int, int]

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "action context"),
            (self.catalogue_id, "action catalogue"),
            (self.state_id, "action state"),
        ):
            _cid(value, field)
        if (
            type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, 2)
        ):
            raise ObservationSupportGraphModelInvariantViolation(
                "action horizon is outside H=2"
            )
        _action(self.action)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_ground_action_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "catalogue_id": self.catalogue_id,
            "state_id": self.state_id,
            "remaining_horizon": self.remaining_horizon,
            "action": list(self.action),
        }

    @property
    def action_id(self) -> str:
        return _content_id("action", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "action_id": self.action_id}


@dataclass(frozen=True, slots=True)
class GraphRelationalCoordinateBindingV1:
    context_id: str
    coordinate_profile_id: str
    remaining_horizon: int
    role: RelationalCoordinateRole
    coordinate: tuple[Any, ...]

    def __post_init__(self) -> None:
        _cid(self.context_id, "coordinate context")
        _cid(self.coordinate_profile_id, "coordinate profile")
        if (
            type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, 2)
            or type(self.role) is not RelationalCoordinateRole
            or type(self.coordinate) is not tuple
            or not self.coordinate
        ):
            raise ObservationSupportGraphModelInvariantViolation(
                "relational coordinate binding is malformed"
            )
        _coordinate_document(self.coordinate)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_relational_coordinate.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "coordinate_profile_id": self.coordinate_profile_id,
            "remaining_horizon": self.remaining_horizon,
            "role": self.role.value,
            "coordinate": _coordinate_document(self.coordinate),
        }

    @property
    def coordinate_id(self) -> str:
        return _content_id("coordinate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "coordinate_id": self.coordinate_id}


def _destination_category(
    descriptor: acquisition.GraphObservedOutcomeDescriptorV1,
) -> robust.DestinationCategory:
    if descriptor.failure:
        return robust.DestinationCategory.FAILURE
    if descriptor.terminal:
        return robust.DestinationCategory.SUCCESS_TERMINAL
    return robust.DestinationCategory.ACTIVE_STATE


@dataclass(frozen=True, slots=True)
class GraphObservedDestinationBindingV1:
    descriptor: acquisition.GraphObservedOutcomeDescriptorV1

    def __post_init__(self) -> None:
        if type(self.descriptor) is not acquisition.GraphObservedOutcomeDescriptorV1:
            raise ObservationSupportGraphModelInvariantViolation(
                "destination requires one canonical observed outcome"
            )

    @property
    def category(self) -> robust.DestinationCategory:
        return _destination_category(self.descriptor)

    @property
    def state_id(self) -> str | None:
        return (
            self.descriptor.next_state.state_id
            if self.category is robust.DestinationCategory.ACTIVE_STATE
            else None
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_outcome_destination.v1",
            "schema_version": SCHEMA_VERSION,
            "outcome_id": self.descriptor.outcome_id,
            "category": self.category.value,
            "state_id": self.state_id,
        }

    @property
    def destination_id(self) -> str:
        return _content_id("destination", self._payload())

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


def global_other_destination_id_v1(context_id: str) -> str:
    _cid(context_id, "OTHER context")
    return _content_id(
        "other",
        {
            "schema": "acfqp.observation_support_global_other_destination.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": context_id,
            "joint_unknown_event_count": 1,
            "failure_value": 1,
            "continuation_reward_lower": _fdoc(Fraction(0)),
        },
    )


@dataclass(frozen=True, slots=True)
class GraphOtherOutcomeEscapeHandlerV1:
    """Registered deployment behavior for an outcome outside frozen support."""

    context_id: str
    other_destination_id: str
    event_key: str = confidence.OTHER_EVENT_KEY
    behavior: str = OTHER_ESCAPE_BEHAVIOR
    failure_value: Fraction = Fraction(1)
    continuation_reward_lower: Fraction = Fraction(0)
    requires_ground_action: bool = False

    def __post_init__(self) -> None:
        _cid(self.context_id, "OTHER escape context")
        _cid(self.other_destination_id, "OTHER escape destination")
        if (
            self.other_destination_id
            != global_other_destination_id_v1(self.context_id)
            or self.event_key != confidence.OTHER_EVENT_KEY
            or self.behavior != OTHER_ESCAPE_BEHAVIOR
            or self.failure_value != 1
            or self.continuation_reward_lower != 0
            or self.requires_ground_action is not False
        ):
            raise ObservationSupportGraphModelInvariantViolation(
                "OTHER escape handler is not the registered absorbing abort"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.observation_support_other_outcome_escape_handler.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "other_destination_id": self.other_destination_id,
            "event_key": self.event_key,
            "behavior": self.behavior,
            "failure_value": _fdoc(self.failure_value),
            "continuation_reward_lower": _fdoc(
                self.continuation_reward_lower
            ),
            "requires_ground_action": False,
        }

    @property
    def handler_id(self) -> str:
        return _content_id("other_escape", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "handler_id": self.handler_id}


@dataclass(frozen=True, slots=True)
class GraphEventDestinationProjectionV1:
    """One exact confidence-event to planner-destination projection."""

    event_interval_id: str
    event_key: str
    destination_id: str
    is_other: bool

    def __post_init__(self) -> None:
        _cid(self.event_interval_id, "confidence event interval")
        _cid(self.destination_id, "event destination")
        if (
            type(self.event_key) is not str
            or not self.event_key
            or type(self.is_other) is not bool
            or (self.is_other and self.event_key != confidence.OTHER_EVENT_KEY)
            or (
                not self.is_other
                and _cid(self.event_key, "discovery-known event")
                != self.event_key
            )
        ):
            raise ObservationSupportGraphModelInvariantViolation(
                "event/destination projection is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.observation_support_event_destination_projection.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "event_interval_id": self.event_interval_id,
            "event_key": self.event_key,
            "destination_id": self.destination_id,
            "is_other": self.is_other,
        }

    @property
    def event_destination_projection_id(self) -> str:
        return _content_id("event_destination", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "event_destination_projection_id": (
                self.event_destination_projection_id
            ),
        }


@dataclass(frozen=True, slots=True)
class GraphRowModelProjectionV1:
    partial_row_id: str
    confidence_authority_id: str
    support_epoch_id: str
    action_id: str
    relational_support_coordinate_id: str
    event_destination_projections: tuple[
        GraphEventDestinationProjectionV1, ...
    ]
    planner_row: robust.IntervalSimplexRowV1

    def __post_init__(self) -> None:
        for value, field in (
            (self.partial_row_id, "partial row"),
            (self.confidence_authority_id, "confidence authority"),
            (self.support_epoch_id, "support epoch"),
            (self.action_id, "row action"),
            (
                self.relational_support_coordinate_id,
                "relational support coordinate",
            ),
        ):
            _cid(value, field)
        if (
            type(self.event_destination_projections) is not tuple
            or not self.event_destination_projections
            or any(
                type(item) is not GraphEventDestinationProjectionV1
                for item in self.event_destination_projections
            )
            or tuple(
                item.event_destination_projection_id
                for item in self.event_destination_projections
            )
            != tuple(
                sorted(
                    {
                        item.event_destination_projection_id
                        for item in self.event_destination_projections
                    }
                )
            )
            or len(
                {
                    item.event_interval_id
                    for item in self.event_destination_projections
                }
            )
            != len(self.event_destination_projections)
            or len(
                {
                    item.destination_id
                    for item in self.event_destination_projections
                }
            )
            != len(self.event_destination_projections)
            or sum(
                item.is_other
                for item in self.event_destination_projections
            )
            != 1
            or type(self.planner_row) is not robust.IntervalSimplexRowV1
            or self.planner_row.action_id != self.action_id
            or {
                item.destination_id
                for item in self.event_destination_projections
            }
            != {
                item.destination_id for item in self.planner_row.masses
            }
            or next(
                item.destination_id
                for item in self.event_destination_projections
                if item.is_other
            )
            != self.planner_row.other_destination_id
        ):
            raise ObservationSupportGraphModelInvariantViolation(
                "row projection is duplicated or inconsistent"
            )

    @property
    def known_destination_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                item.destination_id
                for item in self.event_destination_projections
                if not item.is_other
            )
        )

    @property
    def event_interval_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                item.event_interval_id
                for item in self.event_destination_projections
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_row_model_projection.v1",
            "schema_version": SCHEMA_VERSION,
            "partial_row_id": self.partial_row_id,
            "confidence_authority_id": self.confidence_authority_id,
            "support_epoch_id": self.support_epoch_id,
            "action_id": self.action_id,
            "relational_support_coordinate_id": (
                self.relational_support_coordinate_id
            ),
            "event_destination_projection_ids": [
                item.event_destination_projection_id
                for item in self.event_destination_projections
            ],
            "planner_row_id": self.planner_row.row_id,
        }

    @property
    def projection_id(self) -> str:
        return _content_id("row_projection", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "event_destination_projections": [
                item.to_document()
                for item in self.event_destination_projections
            ],
            "planner_row": self.planner_row.to_document(),
            "projection_id": self.projection_id,
        }


@dataclass(frozen=True, slots=True)
class ObservationSupportGraphModelBridgeV1:
    context_id: str
    root_catalogue_id: str
    coordinate_profile_id: str
    public_catalogue_ids: tuple[str, ...]
    source_partial_row_ids: tuple[str, ...]
    action_bindings: tuple[GraphGroundActionBindingV1, ...]
    coordinate_bindings: tuple[GraphRelationalCoordinateBindingV1, ...]
    destination_bindings: tuple[GraphObservedDestinationBindingV1, ...]
    row_projections: tuple[GraphRowModelProjectionV1, ...]
    other_destination_id: str
    direct_model: robust.PartialSupportIntervalModelV1
    quotient_model: robust.PartialSupportIntervalModelV1
    reward_ceiling: Fraction = REGISTERED_REWARD_CEILING
    operational_exact_support_queries: int = 0
    operational_exact_probability_queries: int = 0
    other_escape_handler: GraphOtherOutcomeEscapeHandlerV1 = field(
        init=False
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "other_escape_handler",
            GraphOtherOutcomeEscapeHandlerV1(
                self.context_id,
                self.other_destination_id,
            ),
        )
        for value, field in (
            (self.context_id, "bridge context"),
            (self.root_catalogue_id, "root public catalogue"),
            (self.coordinate_profile_id, "coordinate profile"),
            (self.other_destination_id, "global OTHER destination"),
        ):
            _cid(value, field)
        typed_sequences = (
            (self.action_bindings, GraphGroundActionBindingV1, "action_id"),
            (
                self.coordinate_bindings,
                GraphRelationalCoordinateBindingV1,
                "coordinate_id",
            ),
            (
                self.destination_bindings,
                GraphObservedDestinationBindingV1,
                "destination_id",
            ),
            (self.row_projections, GraphRowModelProjectionV1, "projection_id"),
        )
        for values, concrete_type, identity_field in typed_sequences:
            if (
                type(values) is not tuple
                or any(type(item) is not concrete_type for item in values)
                or tuple(getattr(item, identity_field) for item in values)
                != tuple(
                    sorted(
                        {
                            getattr(item, identity_field)
                            for item in values
                        }
                    )
                )
            ):
                raise ObservationSupportGraphModelInvariantViolation(
                    "bridge registries must be typed, unique, and ID sorted"
                )
        if (
            self.public_catalogue_ids
            != tuple(sorted(set(self.public_catalogue_ids)))
            or self.root_catalogue_id not in self.public_catalogue_ids
            or self.source_partial_row_ids
            != tuple(sorted(set(self.source_partial_row_ids)))
            or type(self.direct_model) is not robust.PartialSupportIntervalModelV1
            or type(self.quotient_model)
            is not robust.PartialSupportIntervalModelV1
            or self.direct_model.context_id != self.context_id
            or self.quotient_model.context_id != self.context_id
            or self.direct_model.root_state_id
            != self.quotient_model.root_state_id
            or self.direct_model.rows != self.quotient_model.rows
            or self.direct_model.destinations != self.quotient_model.destinations
            or self.direct_model.concretizer_entries
            or not self.quotient_model.concretizer_entries
            or self.reward_ceiling != REGISTERED_REWARD_CEILING
            or self.operational_exact_support_queries != 0
            or self.operational_exact_probability_queries != 0
            or type(self.other_escape_handler)
            is not GraphOtherOutcomeEscapeHandlerV1
            or self.other_escape_handler.context_id != self.context_id
            or self.other_escape_handler.other_destination_id
            != self.other_destination_id
            or global_other_destination_id_v1(self.context_id)
            != self.other_destination_id
            or tuple(
                sorted(item.partial_row_id for item in self.row_projections)
            )
            != self.source_partial_row_ids
            or {
                item.planner_row.row_id for item in self.row_projections
            }
            != {item.row_id for item in self.direct_model.rows}
        ):
            raise ObservationSupportGraphModelInvariantViolation(
                "direct/quotient model bridge semantics changed"
            )
        for value in (
            *self.public_catalogue_ids,
            *self.source_partial_row_ids,
        ):
            _cid(value, "bridge source identity")
        direct_catalogues = {
            item.state_id: item for item in self.direct_model.catalogues
        }
        quotient_catalogues = {
            item.state_id: item for item in self.quotient_model.catalogues
        }
        if set(direct_catalogues) != set(quotient_catalogues):
            raise ObservationSupportGraphModelInvariantViolation(
                "direct and quotient state registries differ"
            )
        for state_id, direct in direct_catalogues.items():
            quotient = quotient_catalogues[state_id]
            if (
                direct.state_coordinate_key != state_id
                or tuple(item.action_id for item in direct.actions)
                != tuple(item.action_id for item in quotient.actions)
                or any(
                    item.action_coordinate_key != item.action_id
                    for item in direct.actions
                )
            ):
                raise ObservationSupportGraphModelInvariantViolation(
                    "direct profile is not exact ground identity"
                )
        expected_action_ids = {
            action.action_id
            for catalogue in self.direct_model.catalogues
            for action in catalogue.actions
        }
        if (
            {item.action_id for item in self.action_bindings}
            != expected_action_ids
            or any(
                item.context_id != self.context_id
                or item.catalogue_id not in self.public_catalogue_ids
                for item in self.action_bindings
            )
            or {
                item.destination_id for item in self.destination_bindings
            }
            != {
                item.destination_id
                for item in self.direct_model.destinations
                if item.category is not robust.DestinationCategory.OTHER
            }
            or any(
                item.context_id != self.context_id
                or item.coordinate_profile_id != self.coordinate_profile_id
                for item in self.coordinate_bindings
            )
        ):
            raise ObservationSupportGraphModelInvariantViolation(
                "bridge action, coordinate, or destination registry is stale"
            )
        expected_coordinate_ids = {
            item.state_coordinate_key
            for item in self.quotient_model.catalogues
        } | {
            action.action_coordinate_key
            for item in self.quotient_model.catalogues
            for action in item.actions
        } | {
            item.relational_support_coordinate_id
            for item in self.row_projections
        }
        if {
            item.coordinate_id for item in self.coordinate_bindings
        } != expected_coordinate_ids:
            raise ObservationSupportGraphModelInvariantViolation(
                "relational coordinate provenance is incomplete or extraneous"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_graph_model_bridge.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "root_catalogue_id": self.root_catalogue_id,
            "coordinate_profile_id": self.coordinate_profile_id,
            "public_catalogue_ids": list(self.public_catalogue_ids),
            "source_partial_row_ids": list(self.source_partial_row_ids),
            "action_binding_ids": [
                item.action_id for item in self.action_bindings
            ],
            "coordinate_binding_ids": [
                item.coordinate_id for item in self.coordinate_bindings
            ],
            "destination_binding_ids": [
                item.destination_id for item in self.destination_bindings
            ],
            "row_projection_ids": [
                item.projection_id for item in self.row_projections
            ],
            "other_destination_id": self.other_destination_id,
            "direct_model_id": self.direct_model.model_id,
            "quotient_model_id": self.quotient_model.model_id,
            "reward_ceiling": _fdoc(self.reward_ceiling),
            "operational_exact_support_queries": 0,
            "operational_exact_probability_queries": 0,
            "other_escape_handler_id": (
                self.other_escape_handler.handler_id
            ),
        }

    @property
    def bridge_id(self) -> str:
        return _content_id("bridge", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "action_bindings": [
                item.to_document() for item in self.action_bindings
            ],
            "coordinate_bindings": [
                item.to_document() for item in self.coordinate_bindings
            ],
            "destination_bindings": [
                item.to_document() for item in self.destination_bindings
            ],
            "row_projections": [
                item.to_document() for item in self.row_projections
            ],
            "other_escape_handler": (
                self.other_escape_handler.to_document()
            ),
            "direct_model": self.direct_model.to_document(),
            "quotient_model": self.quotient_model.to_document(),
            "bridge_id": self.bridge_id,
        }


def _canonical_public_catalogues(
    context: observer.PublicGraphContextV1,
    root_catalogue: observer.LegalActionCatalogueV1,
    catalogues: Iterable[observer.LegalActionCatalogueV1],
) -> tuple[observer.LegalActionCatalogueV1, ...]:
    if (
        type(context) is not observer.PublicGraphContextV1
        or context not in observer.registered_public_graph_contexts_v1()
        or type(root_catalogue) is not observer.LegalActionCatalogueV1
        or root_catalogue.context_id != context.context_id
        or root_catalogue.state != observer.root_state_v1(context)
        or root_catalogue.remaining_horizon != 2
    ):
        raise ObservationSupportGraphModelInvariantViolation(
            "root public context/catalogue is not registered"
        )
    values = tuple(catalogues)
    if root_catalogue not in values:
        values = (root_catalogue, *values)
    by_state: dict[str, observer.LegalActionCatalogueV1] = {}
    for catalogue in values:
        if (
            type(catalogue) is not observer.LegalActionCatalogueV1
            or catalogue.context_id != context.context_id
            or catalogue
            != observer.legal_action_catalogue_v1(
                context,
                catalogue.state,
                catalogue.remaining_horizon,
            )
            or catalogue.state.state_id in by_state
        ):
            raise ObservationSupportGraphModelInvariantViolation(
                "public catalogue set is foreign, noncanonical, or duplicated"
            )
        by_state[catalogue.state.state_id] = catalogue
    return tuple(sorted(by_state.values(), key=lambda item: item.state.state_id))


def _validated_rows(
    context: observer.PublicGraphContextV1,
    catalogues: tuple[observer.LegalActionCatalogueV1, ...],
    rows: Iterable[acquisition.GraphPartialSupportRowV1],
) -> tuple[acquisition.GraphPartialSupportRowV1, ...]:
    values = tuple(rows)
    if (
        not values
        or any(type(item) is not acquisition.GraphPartialSupportRowV1 for item in values)
        or tuple(sorted(item.partial_row_id for item in values))
        != tuple(sorted({item.partial_row_id for item in values}))
    ):
        raise ObservationSupportGraphModelInvariantViolation(
            "partial-support rows are empty, duplicated, or untyped"
        )
    catalogue_by_id = {item.catalogue_id: item for item in catalogues}
    row_by_key: dict[tuple[str, tuple[int, int, int]], acquisition.GraphPartialSupportRowV1] = {}
    for row in values:
        catalogue = catalogue_by_id.get(row.binding.catalogue_id)
        key = (row.binding.catalogue_id, row.binding.action)
        if (
            row.binding.context_id != context.context_id
            or catalogue is None
            or row.binding.state_id != catalogue.state.state_id
            or row.binding.remaining_horizon != catalogue.remaining_horizon
            or row.binding.action not in catalogue.actions
            or key in row_by_key
        ):
            raise ObservationSupportGraphModelInvariantViolation(
                "partial-support row is foreign or has a stale binding"
            )
        confidence.verify_partial_support_confidence_v1(
            row.confidence_authority
        )
        known_events = row.confidence_authority.event_intervals[:-1]
        if (
            tuple(item.event_key for item in known_events)
            != tuple(item.outcome_id for item in row.support_descriptors)
            or row.confidence_authority.event_intervals[-1]
            != row.other_interval
        ):
            raise ObservationSupportGraphModelInvariantViolation(
                "row support and confidence events do not match exactly"
            )
        for descriptor in row.support_descriptors:
            if len(descriptor.next_state.ranks) != context.topology.vertex_count:
                raise ObservationSupportGraphModelInvariantViolation(
                    "observed successor is outside the public graph"
                )
            if row.binding.remaining_horizon == 2:
                if descriptor.failure != descriptor.terminal:
                    raise ObservationSupportGraphModelInvariantViolation(
                        "root observed terminal semantics changed"
                    )
            elif not descriptor.terminal:
                raise ObservationSupportGraphModelInvariantViolation(
                    "H1 observed outcome is not terminal"
                )
        row_by_key[key] = row
    required = {
        (catalogue.catalogue_id, action)
        for catalogue in catalogues
        for action in catalogue.actions
    }
    if set(row_by_key) != required:
        raise ObservationSupportGraphModelInvariantViolation(
            "observed rows do not cover every public catalogue action"
        )
    root = next(item for item in catalogues if item.remaining_horizon == 2)
    expected_children = {
        descriptor.next_state.state_id
        for action in root.actions
        for descriptor in row_by_key[
            (root.catalogue_id, action)
        ].support_descriptors
        if not descriptor.failure
    }
    actual_children = {
        item.state.state_id for item in catalogues if item is not root
    }
    if (
        expected_children != actual_children
        or any(item.remaining_horizon != 1 for item in catalogues if item is not root)
    ):
        raise ObservationSupportGraphModelInvariantViolation(
            "catalogues are not exactly root plus discovery-known safe children"
        )
    return tuple(sorted(values, key=lambda item: item.partial_row_id))


def build_observation_support_graph_models_v1(
    *,
    context: observer.PublicGraphContextV1,
    root_catalogue: observer.LegalActionCatalogueV1,
    catalogues: Iterable[observer.LegalActionCatalogueV1],
    partial_rows: Iterable[acquisition.GraphPartialSupportRowV1],
    coordinate_profile: (
        relational.ObservationSupportCoordinateProfileV1 | None
    ) = None,
    reward_ceiling: Fraction = REGISTERED_REWARD_CEILING,
) -> ObservationSupportGraphModelBridgeV1:
    """Project immutable observed rows into direct and relational models."""

    profile = (
        relational.base_coordinate_profile_v1()
        if coordinate_profile is None
        else coordinate_profile
    )
    if (
        type(profile) is not relational.ObservationSupportCoordinateProfileV1
        or reward_ceiling != REGISTERED_REWARD_CEILING
        or context.reward_ceiling != REGISTERED_REWARD_CEILING
        or context.normalized_regret_tolerance
        != robust.NORMALIZED_REGRET_TOLERANCE
    ):
        raise ObservationSupportGraphModelInvariantViolation(
            "bridge requires the registered coordinate/reward profile"
        )
    public_catalogues = _canonical_public_catalogues(
        context,
        root_catalogue,
        catalogues,
    )
    rows = _validated_rows(context, public_catalogues, partial_rows)
    catalogue_by_id = {
        item.catalogue_id: item for item in public_catalogues
    }

    action_bindings: dict[str, GraphGroundActionBindingV1] = {}
    action_by_public_key: dict[
        tuple[str, tuple[int, int, int]], GraphGroundActionBindingV1
    ] = {}
    coordinate_bindings: dict[str, GraphRelationalCoordinateBindingV1] = {}
    state_coordinate_by_state: dict[str, str] = {}
    action_coordinate_by_action_id: dict[str, str] = {}
    support_coordinate_by_action_id: dict[str, str] = {}

    for catalogue in public_catalogues:
        state_ir = relational.relational_state_ir_v1(context, catalogue)
        state_binding = GraphRelationalCoordinateBindingV1(
            context.context_id,
            profile.profile_id,
            catalogue.remaining_horizon,
            RelationalCoordinateRole.STATE,
            relational.state_coordinate_v1(profile, state_ir),
        )
        coordinate_bindings.setdefault(
            state_binding.coordinate_id,
            state_binding,
        )
        state_coordinate_by_state[catalogue.state.state_id] = (
            state_binding.coordinate_id
        )
        for action in catalogue.actions:
            binding = GraphGroundActionBindingV1(
                context.context_id,
                catalogue.catalogue_id,
                catalogue.state.state_id,
                catalogue.remaining_horizon,
                action,
            )
            action_bindings[binding.action_id] = binding
            action_by_public_key[(catalogue.catalogue_id, action)] = binding
            slot = relational.action_slot_v1(context, catalogue, action)
            action_coordinate = GraphRelationalCoordinateBindingV1(
                context.context_id,
                profile.profile_id,
                catalogue.remaining_horizon,
                RelationalCoordinateRole.ACTION,
                relational.action_coordinate_v1(profile, state_ir, slot),
            )
            support_coordinate = GraphRelationalCoordinateBindingV1(
                context.context_id,
                profile.profile_id,
                catalogue.remaining_horizon,
                RelationalCoordinateRole.SUPPORT,
                relational.support_coordinate_v1(
                    profile,
                    context,
                    catalogue,
                    action,
                ),
            )
            for item in (action_coordinate, support_coordinate):
                coordinate_bindings.setdefault(item.coordinate_id, item)
            action_coordinate_by_action_id[binding.action_id] = (
                action_coordinate.coordinate_id
            )
            support_coordinate_by_action_id[binding.action_id] = (
                support_coordinate.coordinate_id
            )

    destination_bindings: dict[str, GraphObservedDestinationBindingV1] = {}
    destination_by_outcome: dict[str, GraphObservedDestinationBindingV1] = {}
    for row in rows:
        for descriptor in row.support_descriptors:
            binding = GraphObservedDestinationBindingV1(descriptor)
            previous = destination_by_outcome.setdefault(
                descriptor.outcome_id,
                binding,
            )
            if previous != binding:
                raise ObservationSupportGraphModelInvariantViolation(
                    "one outcome ID was bound to different destination bytes"
                )
            destination_bindings[binding.destination_id] = binding

    other_id = global_other_destination_id_v1(context.context_id)
    planner_rows: list[robust.IntervalSimplexRowV1] = []
    row_projections: list[GraphRowModelProjectionV1] = []
    for row in rows:
        catalogue = catalogue_by_id[row.binding.catalogue_id]
        action_binding = action_by_public_key[
            (catalogue.catalogue_id, row.binding.action)
        ]
        event_by_key = {
            item.event_key: item
            for item in row.confidence_authority.event_intervals
        }
        masses: list[robust.IntervalDestinationMassV1] = []
        event_destination_projections: list[
            GraphEventDestinationProjectionV1
        ] = []
        rewards = {
            item.realized_row_reward for item in row.support_descriptors
        }
        if len(rewards) != 1:
            raise ObservationSupportGraphModelInvariantViolation(
                "observed row reward is not homogeneous"
            )
        observed_reward = next(iter(rewards))
        if observed_reward > reward_ceiling:
            raise ObservationSupportGraphModelInvariantViolation(
                "observed row reward exceeds the registered query ceiling"
            )
        for descriptor in row.support_descriptors:
            destination = destination_by_outcome[descriptor.outcome_id]
            interval = event_by_key[descriptor.outcome_id]
            masses.append(
                robust.IntervalDestinationMassV1(
                    destination.destination_id,
                    interval.lower_probability,
                    interval.upper_probability,
                )
            )
            event_destination_projections.append(
                GraphEventDestinationProjectionV1(
                    interval.event_interval_id,
                    interval.event_key,
                    destination.destination_id,
                    False,
                )
            )
        masses.append(
            robust.IntervalDestinationMassV1(
                other_id,
                row.other_interval.lower_probability,
                row.other_interval.upper_probability,
            )
        )
        event_destination_projections.append(
            GraphEventDestinationProjectionV1(
                row.other_interval.event_interval_id,
                row.other_interval.event_key,
                other_id,
                True,
            )
        )
        other_upper = row.other_interval.upper_probability
        reward_lower = observed_reward * (1 - other_upper)
        reward_upper = min(
            reward_ceiling,
            observed_reward
            + (reward_ceiling - observed_reward) * other_upper,
        )
        planner_row = robust.IntervalSimplexRowV1(
            catalogue.state.state_id,
            catalogue.remaining_horizon,
            action_binding.action_id,
            reward_lower,
            reward_upper,
            other_id,
            tuple(sorted(masses, key=lambda item: item.destination_id)),
        )
        planner_rows.append(planner_row)
        row_projections.append(
            GraphRowModelProjectionV1(
                row.partial_row_id,
                row.confidence_authority.authority_id,
                row.support_epoch.support_epoch_id,
                action_binding.action_id,
                support_coordinate_by_action_id[action_binding.action_id],
                tuple(
                    sorted(
                        event_destination_projections,
                        key=lambda item: (
                            item.event_destination_projection_id
                        ),
                    )
                ),
                planner_row,
            )
        )

    direct_catalogues: list[robust.StateActionCatalogueV1] = []
    quotient_catalogues: list[robust.StateActionCatalogueV1] = []
    concretizers: list[robust.DistinctActionConcretizerEntryV1] = []
    for catalogue in public_catalogues:
        bindings = tuple(
            sorted(
                (
                    action_by_public_key[(catalogue.catalogue_id, action)]
                    for action in catalogue.actions
                ),
                key=lambda item: item.action_id,
            )
        )
        direct_catalogues.append(
            robust.StateActionCatalogueV1(
                catalogue.state.state_id,
                catalogue.state.state_id,
                tuple(
                    robust.CatalogueActionV1(item.action_id, item.action_id)
                    for item in bindings
                ),
            )
        )
        quotient_actions = tuple(
            robust.CatalogueActionV1(
                item.action_id,
                action_coordinate_by_action_id[item.action_id],
            )
            for item in bindings
        )
        quotient_catalogues.append(
            robust.StateActionCatalogueV1(
                catalogue.state.state_id,
                state_coordinate_by_state[catalogue.state.state_id],
                quotient_actions,
            )
        )
        grouped: dict[str, list[str]] = {}
        for item in quotient_actions:
            grouped.setdefault(item.action_coordinate_key, []).append(
                item.action_id
            )
        concretizers.extend(
            robust.DistinctActionConcretizerEntryV1(
                state_coordinate_by_state[catalogue.state.state_id],
                catalogue.state.state_id,
                abstract_action,
                tuple(sorted(ground_actions)),
            )
            for abstract_action, ground_actions in grouped.items()
        )

    destinations = [
        item.registered_destination()
        for item in destination_bindings.values()
    ]
    destinations.append(
        robust.RegisteredDestinationV1(
            other_id,
            robust.DestinationCategory.OTHER,
        )
    )
    common = {
        "context_id": context.context_id,
        "root_state_id": root_catalogue.state.state_id,
        "destinations": destinations,
        "rows": planner_rows,
    }
    direct_model = robust.build_partial_support_model_v1(
        **common,
        catalogues=direct_catalogues,
    )
    quotient_model = robust.build_partial_support_model_v1(
        **common,
        catalogues=quotient_catalogues,
        concretizer_entries=concretizers,
    )
    return ObservationSupportGraphModelBridgeV1(
        context.context_id,
        root_catalogue.catalogue_id,
        profile.profile_id,
        tuple(sorted(item.catalogue_id for item in public_catalogues)),
        tuple(sorted(item.partial_row_id for item in rows)),
        tuple(sorted(action_bindings.values(), key=lambda item: item.action_id)),
        tuple(
            sorted(
                coordinate_bindings.values(),
                key=lambda item: item.coordinate_id,
            )
        ),
        tuple(
            sorted(
                destination_bindings.values(),
                key=lambda item: item.destination_id,
            )
        ),
        tuple(
            sorted(row_projections, key=lambda item: item.projection_id)
        ),
        other_id,
        direct_model,
        quotient_model,
    )


@dataclass(frozen=True, slots=True)
class ObservationSupportGraphModelReplayV1:
    bridge_id: str
    direct_model_id: str
    quotient_model_id: str
    source_row_count: int
    destination_count: int
    operational_exact_support_queries: int = 0
    operational_exact_probability_queries: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.bridge_id, "verified bridge"),
            (self.direct_model_id, "verified direct model"),
            (self.quotient_model_id, "verified quotient model"),
        ):
            _cid(value, field)
        if (
            type(self.source_row_count) is not int
            or self.source_row_count <= 0
            or type(self.destination_count) is not int
            or self.destination_count <= 1
            or self.operational_exact_support_queries != 0
            or self.operational_exact_probability_queries != 0
        ):
            raise ObservationSupportGraphModelInvariantViolation(
                "bridge replay accounting is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_graph_model_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "bridge_id": self.bridge_id,
            "direct_model_id": self.direct_model_id,
            "quotient_model_id": self.quotient_model_id,
            "source_row_count": self.source_row_count,
            "destination_count": self.destination_count,
            "operational_exact_support_queries": 0,
            "operational_exact_probability_queries": 0,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_observation_support_graph_models_v1(
    *,
    context: observer.PublicGraphContextV1,
    root_catalogue: observer.LegalActionCatalogueV1,
    catalogues: Iterable[observer.LegalActionCatalogueV1],
    partial_rows: Iterable[acquisition.GraphPartialSupportRowV1],
    bridge: ObservationSupportGraphModelBridgeV1,
    coordinate_profile: (
        relational.ObservationSupportCoordinateProfileV1 | None
    ) = None,
) -> ObservationSupportGraphModelReplayV1:
    """Rebuild every projection and require byte-for-byte content identity."""

    if type(bridge) is not ObservationSupportGraphModelBridgeV1:
        raise ObservationSupportGraphModelInvariantViolation(
            "replay requires one concrete model bridge"
        )
    rebuilt = build_observation_support_graph_models_v1(
        context=context,
        root_catalogue=root_catalogue,
        catalogues=catalogues,
        partial_rows=partial_rows,
        coordinate_profile=coordinate_profile,
        reward_ceiling=bridge.reward_ceiling,
    )
    if rebuilt != bridge or rebuilt.to_document() != bridge.to_document():
        raise ObservationSupportGraphModelInvariantViolation(
            "model bridge differs from exact reconstruction"
        )
    return ObservationSupportGraphModelReplayV1(
        bridge.bridge_id,
        bridge.direct_model.model_id,
        bridge.quotient_model.model_id,
        len(bridge.source_partial_row_ids),
        len(bridge.direct_model.destinations),
    )


__all__ = [
    "CONTRACT_VERSION",
    "GraphEventDestinationProjectionV1",
    "GraphGroundActionBindingV1",
    "GraphObservedDestinationBindingV1",
    "GraphOtherOutcomeEscapeHandlerV1",
    "GraphRelationalCoordinateBindingV1",
    "GraphRowModelProjectionV1",
    "ObservationSupportGraphModelBridgeV1",
    "ObservationSupportGraphModelInvariantViolation",
    "ObservationSupportGraphModelReplayV1",
    "OTHER_ESCAPE_BEHAVIOR",
    "PROFILE_KEY",
    "REGISTERED_REWARD_CEILING",
    "RelationalCoordinateRole",
    "SCHEMA_VERSION",
    "build_observation_support_graph_models_v1",
    "global_other_destination_id_v1",
    "verify_observation_support_graph_models_v1",
]
