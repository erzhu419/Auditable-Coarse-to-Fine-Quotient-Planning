"""Domain-neutral H=2 robust planning over honest partial support.

The authority in this module never calls a kernel and has no exact-support
input.  Every transition row is one joint interval simplex with one explicit
``OTHER`` destination.  Robust expectations optimize over that simplex, so
unknown mass is charged exactly once instead of summing marginal upper
bounds.

``OTHER`` has failure value one and reward/continuation lower value zero.
Its optimistic reward continuation is bounded only by the query reward
ceiling.  This keeps the regret comparison sound without pretending that
unobserved support is harmless.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
import hashlib
import itertools
from typing import Any, Iterable, Mapping, Sequence

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.32.0"
PROFILE_KEY = "partial_support_interval_simplex_robust_h2_v0"
HORIZON = 2
NORMALIZED_REGRET_TOLERANCE = Fraction(1, 20)
MAX_POLICY_ASSIGNMENTS = 65_536

DOMAIN_TAGS = {
    "destination": "acfqp:partial-support-destination:v1",
    "catalogue_action": "acfqp:partial-support-catalogue-action:v1",
    "catalogue": "acfqp:partial-support-state-action-catalogue:v1",
    "mass": "acfqp:partial-support-interval-mass:v1",
    "row": "acfqp:partial-support-interval-simplex-row:v1",
    "concretizer": "acfqp:partial-support-distinct-action-concretizer:v1",
    "model": "acfqp:partial-support-interval-simplex-model:v1",
    "threshold": "acfqp:partial-support-robust-threshold:v1",
    "assignment": "acfqp:partial-support-robust-policy-assignment:v1",
    "row_bound": "acfqp:partial-support-robust-row-bound:v1",
    "provenance": "acfqp:partial-support-selected-row-provenance:v1",
    "other_mass": "acfqp:partial-support-other-mass-provenance:v1",
    "counterfactual": "acfqp:partial-support-other-counterfactual:v1",
    "frontier": "acfqp:partial-support-failed-frontier:v1",
    "audit": "acfqp:partial-support-robust-plan-audit:v1",
    "verification": "acfqp:partial-support-robust-audit-verification:v1",
}


class PartialSupportRobustPlannerInvariantViolation(ValueError):
    """The partial-support model, policy, or certificate is malformed."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise PartialSupportRobustPlannerInvariantViolation(str(error)) from error
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise PartialSupportRobustPlannerInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fraction(
    value: Any,
    field: str,
    *,
    lower: Fraction | None = None,
    upper: Fraction | None = None,
) -> Fraction:
    if type(value) is not Fraction:
        raise PartialSupportRobustPlannerInvariantViolation(
            f"{field} must be an exact Fraction"
        )
    if lower is not None and value < lower:
        raise PartialSupportRobustPlannerInvariantViolation(
            f"{field} is below {lower}"
        )
    if upper is not None and value > upper:
        raise PartialSupportRobustPlannerInvariantViolation(
            f"{field} exceeds {upper}"
        )
    return value


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {
        "numerator": exact.numerator,
        "denominator": exact.denominator,
    }


class DestinationCategory(str, Enum):
    ACTIVE_STATE = "ACTIVE_STATE"
    FAILURE = "FAILURE"
    SUCCESS_TERMINAL = "SUCCESS_TERMINAL"
    OTHER = "OTHER"


class RobustSolverKind(str, Enum):
    GROUND_DIRECT = "GROUND_DIRECT"
    QUOTIENT = "QUOTIENT"


class RobustAuditStatus(str, Enum):
    CERTIFIED = "CERTIFIED"
    FAILED_PROOF_FRONTIER = "FAILED_PROOF_FRONTIER"


class PolicyScope(str, Enum):
    GROUND_STATE = "GROUND_STATE"
    QUOTIENT_CELL = "QUOTIENT_CELL"


class SelectedRowCategory(str, Enum):
    ROOT_SELECTED = "ROOT_SELECTED"
    CONTINUATION_SELECTED = "CONTINUATION_SELECTED"
    ROOT_CONCRETIZER_COMPONENT = "ROOT_CONCRETIZER_COMPONENT"
    CONTINUATION_CONCRETIZER_COMPONENT = (
        "CONTINUATION_CONCRETIZER_COMPONENT"
    )


class CounterfactualStatus(str, Enum):
    ORIGINAL_ALREADY_CERTIFIED = "ORIGINAL_ALREADY_CERTIFIED"
    ZERO_OTHER_CERTIFIED = "ZERO_OTHER_CERTIFIED"
    ZERO_OTHER_STILL_FAILED = "ZERO_OTHER_STILL_FAILED"
    ZERO_OTHER_INFEASIBLE_SIMPLEX = "ZERO_OTHER_INFEASIBLE_SIMPLEX"


class FailedFrontierReason(str, Enum):
    RISK = "RISK"
    REGRET = "REGRET"
    RISK_AND_REGRET = "RISK_AND_REGRET"


@dataclass(frozen=True, slots=True)
class RegisteredDestinationV1:
    destination_id: str
    category: DestinationCategory
    state_id: str | None = None

    def __post_init__(self) -> None:
        _cid(self.destination_id, "destination")
        if type(self.category) is not DestinationCategory:
            raise PartialSupportRobustPlannerInvariantViolation(
                "destination category is not registered"
            )
        if self.category is DestinationCategory.ACTIVE_STATE:
            if self.state_id is None:
                raise PartialSupportRobustPlannerInvariantViolation(
                    "active destination requires state_id"
                )
            _cid(self.state_id, "active destination state")
        elif self.state_id is not None:
            raise PartialSupportRobustPlannerInvariantViolation(
                "non-active destination cannot carry state_id"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_destination.v1",
            "schema_version": SCHEMA_VERSION,
            "destination_id": self.destination_id,
            "category": self.category.value,
            "state_id": self.state_id,
        }

    @property
    def registry_entry_id(self) -> str:
        return _content_id("destination", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registry_entry_id": self.registry_entry_id}


@dataclass(frozen=True, slots=True)
class CatalogueActionV1:
    action_id: str
    action_coordinate_key: str

    def __post_init__(self) -> None:
        _cid(self.action_id, "ground action")
        _cid(self.action_coordinate_key, "action coordinate")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_catalogue_action.v1",
            "schema_version": SCHEMA_VERSION,
            "action_id": self.action_id,
            "action_coordinate_key": self.action_coordinate_key,
        }

    @property
    def catalogue_action_id(self) -> str:
        return _content_id("catalogue_action", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "catalogue_action_id": self.catalogue_action_id,
        }


@dataclass(frozen=True, slots=True)
class StateActionCatalogueV1:
    state_id: str
    state_coordinate_key: str
    actions: tuple[CatalogueActionV1, ...]

    def __post_init__(self) -> None:
        _cid(self.state_id, "catalogue state")
        _cid(self.state_coordinate_key, "state coordinate")
        if (
            type(self.actions) is not tuple
            or not self.actions
            or any(type(item) is not CatalogueActionV1 for item in self.actions)
            or tuple(item.action_id for item in self.actions)
            != tuple(sorted({item.action_id for item in self.actions}))
        ):
            raise PartialSupportRobustPlannerInvariantViolation(
                "catalogue actions must be nonempty, distinct, and sorted"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_state_action_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "state_id": self.state_id,
            "state_coordinate_key": self.state_coordinate_key,
            "catalogue_action_ids": [
                item.catalogue_action_id for item in self.actions
            ],
        }

    @property
    def catalogue_id(self) -> str:
        return _content_id("catalogue", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "actions": [item.to_document() for item in self.actions],
            "catalogue_id": self.catalogue_id,
        }


@dataclass(frozen=True, slots=True)
class IntervalDestinationMassV1:
    destination_id: str
    lower: Fraction
    upper: Fraction

    def __post_init__(self) -> None:
        _cid(self.destination_id, "interval destination")
        _fraction(self.lower, "interval lower", lower=Fraction(0), upper=Fraction(1))
        _fraction(self.upper, "interval upper", lower=Fraction(0), upper=Fraction(1))
        if self.lower > self.upper:
            raise PartialSupportRobustPlannerInvariantViolation(
                "interval lower exceeds upper"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_interval_mass.v1",
            "schema_version": SCHEMA_VERSION,
            "destination_id": self.destination_id,
            "lower": _fdoc(self.lower),
            "upper": _fdoc(self.upper),
        }

    @property
    def mass_id(self) -> str:
        return _content_id("mass", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "mass_id": self.mass_id}


def _require_admissible_simplex(
    masses: Sequence[IntervalDestinationMassV1],
    *,
    context: str,
) -> None:
    lower_sum = sum((item.lower for item in masses), Fraction(0))
    upper_sum = sum((item.upper for item in masses), Fraction(0))
    if lower_sum > 1 or upper_sum < 1:
        raise PartialSupportRobustPlannerInvariantViolation(
            f"{context} intervals do not admit a unit simplex"
        )


@dataclass(frozen=True, slots=True)
class IntervalSimplexRowV1:
    state_id: str
    remaining_horizon: int
    action_id: str
    reward_lower: Fraction
    reward_upper: Fraction
    other_destination_id: str
    masses: tuple[IntervalDestinationMassV1, ...]

    def __post_init__(self) -> None:
        _cid(self.state_id, "row state")
        _cid(self.action_id, "row action")
        _cid(self.other_destination_id, "row OTHER destination")
        if type(self.remaining_horizon) is not int or self.remaining_horizon not in (1, 2):
            raise PartialSupportRobustPlannerInvariantViolation(
                "row remaining_horizon must be one or two"
            )
        _fraction(self.reward_lower, "row reward lower", lower=Fraction(0))
        _fraction(self.reward_upper, "row reward upper", lower=Fraction(0))
        if self.reward_lower > self.reward_upper:
            raise PartialSupportRobustPlannerInvariantViolation(
                "row reward lower exceeds upper"
            )
        if (
            type(self.masses) is not tuple
            or not self.masses
            or any(type(item) is not IntervalDestinationMassV1 for item in self.masses)
            or tuple(item.destination_id for item in self.masses)
            != tuple(sorted({item.destination_id for item in self.masses}))
            or sum(
                item.destination_id == self.other_destination_id
                for item in self.masses
            )
            != 1
        ):
            raise PartialSupportRobustPlannerInvariantViolation(
                "row masses must be sorted, distinct, and contain OTHER once"
            )
        _require_admissible_simplex(self.masses, context="row")

    @property
    def row_key(self) -> tuple[str, int, str]:
        return self.state_id, self.remaining_horizon, self.action_id

    @property
    def other_mass(self) -> IntervalDestinationMassV1:
        return next(
            item
            for item in self.masses
            if item.destination_id == self.other_destination_id
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_interval_simplex_row.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "state_id": self.state_id,
            "remaining_horizon": self.remaining_horizon,
            "action_id": self.action_id,
            "reward_lower": _fdoc(self.reward_lower),
            "reward_upper": _fdoc(self.reward_upper),
            "other_destination_id": self.other_destination_id,
            "mass_ids": [item.mass_id for item in self.masses],
        }

    @property
    def row_id(self) -> str:
        return _content_id("row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "masses": [item.to_document() for item in self.masses],
            "row_id": self.row_id,
        }


@dataclass(frozen=True, slots=True)
class DistinctActionConcretizerEntryV1:
    state_coordinate_key: str
    state_id: str
    abstract_action_key: str
    ground_action_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _cid(self.state_coordinate_key, "concretizer state coordinate")
        _cid(self.state_id, "concretizer state")
        _cid(self.abstract_action_key, "concretizer abstract action")
        if (
            type(self.ground_action_ids) is not tuple
            or not self.ground_action_ids
            or self.ground_action_ids
            != tuple(sorted(set(self.ground_action_ids)))
        ):
            raise PartialSupportRobustPlannerInvariantViolation(
                "concretizer support must contain sorted distinct actions"
            )
        for item in self.ground_action_ids:
            _cid(item, "concretizer ground action")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_distinct_action_concretizer.v1",
            "schema_version": SCHEMA_VERSION,
            "state_coordinate_key": self.state_coordinate_key,
            "state_id": self.state_id,
            "abstract_action_key": self.abstract_action_key,
            "ground_action_ids": list(self.ground_action_ids),
            "weights": [
                _fdoc(Fraction(1, len(self.ground_action_ids)))
                for _ in self.ground_action_ids
            ],
        }

    @property
    def concretizer_entry_id(self) -> str:
        return _content_id("concretizer", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "concretizer_entry_id": self.concretizer_entry_id,
        }


@dataclass(frozen=True, slots=True)
class PartialSupportIntervalModelV1:
    context_id: str
    root_state_id: str
    catalogues: tuple[StateActionCatalogueV1, ...]
    destinations: tuple[RegisteredDestinationV1, ...]
    rows: tuple[IntervalSimplexRowV1, ...]
    concretizer_entries: tuple[DistinctActionConcretizerEntryV1, ...] = ()
    horizon: int = HORIZON

    def __post_init__(self) -> None:
        _cid(self.context_id, "model context")
        _cid(self.root_state_id, "model root state")
        if self.horizon != HORIZON:
            raise PartialSupportRobustPlannerInvariantViolation(
                "only the registered H=2 authority is implemented"
            )
        if (
            type(self.catalogues) is not tuple
            or not self.catalogues
            or any(type(item) is not StateActionCatalogueV1 for item in self.catalogues)
            or tuple(item.state_id for item in self.catalogues)
            != tuple(sorted({item.state_id for item in self.catalogues}))
            or self.root_state_id not in {item.state_id for item in self.catalogues}
        ):
            raise PartialSupportRobustPlannerInvariantViolation(
                "model catalogues are incomplete, duplicated, or unsorted"
            )
        if (
            type(self.destinations) is not tuple
            or not self.destinations
            or any(type(item) is not RegisteredDestinationV1 for item in self.destinations)
            or tuple(item.destination_id for item in self.destinations)
            != tuple(sorted({item.destination_id for item in self.destinations}))
            or sum(
                item.category is DestinationCategory.OTHER
                for item in self.destinations
            )
            != 1
        ):
            raise PartialSupportRobustPlannerInvariantViolation(
                "destination registry must be sorted with exactly one OTHER"
            )
        if (
            type(self.rows) is not tuple
            or not self.rows
            or any(type(item) is not IntervalSimplexRowV1 for item in self.rows)
            or tuple(item.row_id for item in self.rows)
            != tuple(sorted({item.row_id for item in self.rows}))
        ):
            raise PartialSupportRobustPlannerInvariantViolation(
                "model rows must be typed, distinct, and row-ID sorted"
            )
        if (
            type(self.concretizer_entries) is not tuple
            or any(
                type(item) is not DistinctActionConcretizerEntryV1
                for item in self.concretizer_entries
            )
            or tuple(item.concretizer_entry_id for item in self.concretizer_entries)
            != tuple(
                sorted(
                    {
                        item.concretizer_entry_id
                        for item in self.concretizer_entries
                    }
                )
            )
        ):
            raise PartialSupportRobustPlannerInvariantViolation(
                "concretizer entries must be distinct and ID sorted"
            )
        self._validate_semantics()

    @property
    def other_destination(self) -> RegisteredDestinationV1:
        return next(
            item
            for item in self.destinations
            if item.category is DestinationCategory.OTHER
        )

    def _validate_semantics(self) -> None:
        catalogue_by_state = {item.state_id: item for item in self.catalogues}
        destination_by_id = {
            item.destination_id: item for item in self.destinations
        }
        other_id = self.other_destination.destination_id
        for destination in self.destinations:
            if (
                destination.category is DestinationCategory.ACTIVE_STATE
                and destination.state_id not in catalogue_by_state
            ):
                raise PartialSupportRobustPlannerInvariantViolation(
                    "active destination state is outside the catalogue registry"
                )
        row_by_key: dict[tuple[str, int, str], IntervalSimplexRowV1] = {}
        for row in self.rows:
            if row.other_destination_id != other_id:
                raise PartialSupportRobustPlannerInvariantViolation(
                    "row OTHER identity differs from the model registry"
                )
            catalogue = catalogue_by_state.get(row.state_id)
            if catalogue is None or row.action_id not in {
                item.action_id for item in catalogue.actions
            }:
                raise PartialSupportRobustPlannerInvariantViolation(
                    "row state/action is outside the observed catalogue"
                )
            if any(item.destination_id not in destination_by_id for item in row.masses):
                raise PartialSupportRobustPlannerInvariantViolation(
                    "row contains an out-of-registry destination"
                )
            if row.row_key in row_by_key:
                raise PartialSupportRobustPlannerInvariantViolation(
                    "duplicate row state/horizon/action key"
                )
            row_by_key[row.row_key] = row

        root_catalogue = catalogue_by_state[self.root_state_id]
        required = {
            (self.root_state_id, HORIZON, action.action_id)
            for action in root_catalogue.actions
        }
        reachable_children: set[str] = set()
        for key in required:
            row = row_by_key.get(key)
            if row is None:
                raise PartialSupportRobustPlannerInvariantViolation(
                    "root observed catalogue is incomplete"
                )
            for mass in row.masses:
                destination = destination_by_id[mass.destination_id]
                if (
                    mass.upper > 0
                    and destination.category is DestinationCategory.ACTIVE_STATE
                ):
                    assert destination.state_id is not None
                    reachable_children.add(destination.state_id)
        for state_id in reachable_children:
            catalogue = catalogue_by_state[state_id]
            required.update(
                (state_id, 1, action.action_id)
                for action in catalogue.actions
            )
        if set(row_by_key) != required:
            raise PartialSupportRobustPlannerInvariantViolation(
                "rows are not the complete reachable observed H2 catalogue"
            )

        action_by_state = {
            item.state_id: {
                action.action_id: action for action in item.actions
            }
            for item in self.catalogues
        }
        seen_concretizer_keys: set[tuple[str, str, str]] = set()
        for entry in self.concretizer_entries:
            catalogue = catalogue_by_state.get(entry.state_id)
            if (
                catalogue is None
                or catalogue.state_coordinate_key
                != entry.state_coordinate_key
            ):
                raise PartialSupportRobustPlannerInvariantViolation(
                    "concretizer state/cell binding is invalid"
                )
            key = (
                entry.state_coordinate_key,
                entry.state_id,
                entry.abstract_action_key,
            )
            if key in seen_concretizer_keys:
                raise PartialSupportRobustPlannerInvariantViolation(
                    "duplicate concretizer semantic key"
                )
            seen_concretizer_keys.add(key)
            for action_id in entry.ground_action_ids:
                action = action_by_state[entry.state_id].get(action_id)
                if (
                    action is None
                    or action.action_coordinate_key
                    != entry.abstract_action_key
                ):
                    raise PartialSupportRobustPlannerInvariantViolation(
                        "concretizer support is not a distinct semantic-action set"
                    )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_interval_simplex_model.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "root_state_id": self.root_state_id,
            "catalogue_ids": [item.catalogue_id for item in self.catalogues],
            "destination_entry_ids": [
                item.registry_entry_id for item in self.destinations
            ],
            "row_ids": [item.row_id for item in self.rows],
            "concretizer_entry_ids": [
                item.concretizer_entry_id for item in self.concretizer_entries
            ],
            "horizon": HORIZON,
        }

    @property
    def model_id(self) -> str:
        return _content_id("model", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "catalogues": [item.to_document() for item in self.catalogues],
            "destinations": [item.to_document() for item in self.destinations],
            "rows": [item.to_document() for item in self.rows],
            "concretizer_entries": [
                item.to_document() for item in self.concretizer_entries
            ],
            "model_id": self.model_id,
        }


def build_partial_support_model_v1(
    *,
    context_id: str,
    root_state_id: str,
    catalogues: Iterable[StateActionCatalogueV1],
    destinations: Iterable[RegisteredDestinationV1],
    rows: Iterable[IntervalSimplexRowV1],
    concretizer_entries: Iterable[DistinctActionConcretizerEntryV1] = (),
) -> PartialSupportIntervalModelV1:
    """Construct the strict kernel-free H2 partial-support model."""

    catalogue_tuple = tuple(sorted(catalogues, key=lambda item: item.state_id))
    destination_tuple = tuple(
        sorted(destinations, key=lambda item: item.destination_id)
    )
    row_tuple = tuple(sorted(rows, key=lambda item: item.row_id))
    concretizer_tuple = tuple(
        sorted(concretizer_entries, key=lambda item: item.concretizer_entry_id)
    )
    return PartialSupportIntervalModelV1(
        context_id,
        root_state_id,
        catalogue_tuple,
        destination_tuple,
        row_tuple,
        concretizer_tuple,
    )


@dataclass(frozen=True, slots=True)
class RobustThresholdProfileV1:
    context_id: str
    risk_tolerance: Fraction
    reward_ceiling: Fraction
    normalized_regret_tolerance: Fraction = NORMALIZED_REGRET_TOLERANCE

    def __post_init__(self) -> None:
        _cid(self.context_id, "threshold context")
        _fraction(
            self.risk_tolerance,
            "risk tolerance",
            lower=Fraction(0),
            upper=Fraction(1),
        )
        if self.risk_tolerance <= 0:
            raise PartialSupportRobustPlannerInvariantViolation(
                "risk tolerance must be positive"
            )
        _fraction(self.reward_ceiling, "reward ceiling", lower=Fraction(0))
        if self.reward_ceiling <= 0:
            raise PartialSupportRobustPlannerInvariantViolation(
                "reward ceiling must be positive"
            )
        if self.normalized_regret_tolerance != NORMALIZED_REGRET_TOLERANCE:
            raise PartialSupportRobustPlannerInvariantViolation(
                "V0 normalized regret tolerance must equal 1/20"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_robust_threshold.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "risk_tolerance": _fdoc(self.risk_tolerance),
            "reward_ceiling": _fdoc(self.reward_ceiling),
            "normalized_regret_tolerance": _fdoc(
                self.normalized_regret_tolerance
            ),
        }

    @property
    def threshold_profile_id(self) -> str:
        return _content_id("threshold", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "threshold_profile_id": self.threshold_profile_id,
        }


@dataclass(frozen=True, slots=True)
class RobustPolicyAssignmentV1:
    scope: PolicyScope
    scope_key: str
    remaining_horizon: int
    selected_action_key: str

    def __post_init__(self) -> None:
        if type(self.scope) is not PolicyScope:
            raise PartialSupportRobustPlannerInvariantViolation(
                "policy assignment scope is invalid"
            )
        _cid(self.scope_key, "policy scope key")
        _cid(self.selected_action_key, "selected action key")
        if type(self.remaining_horizon) is not int or self.remaining_horizon not in (1, 2):
            raise PartialSupportRobustPlannerInvariantViolation(
                "policy assignment horizon must be one or two"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_robust_policy_assignment.v1",
            "schema_version": SCHEMA_VERSION,
            "scope": self.scope.value,
            "scope_key": self.scope_key,
            "remaining_horizon": self.remaining_horizon,
            "selected_action_key": self.selected_action_key,
        }

    @property
    def assignment_id(self) -> str:
        return _content_id("assignment", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "assignment_id": self.assignment_id}


@dataclass(frozen=True, slots=True)
class RobustSelectedRowBoundV1:
    row_id: str
    remaining_horizon: int
    reward_lower: Fraction
    reward_upper: Fraction
    failure_upper: Fraction
    other_mass_lower: Fraction
    other_mass_upper: Fraction
    other_mass_used_for_reward_lower: Fraction
    other_mass_used_for_reward_upper: Fraction
    other_mass_used_for_failure_upper: Fraction

    def __post_init__(self) -> None:
        _cid(self.row_id, "selected row bound")
        if type(self.remaining_horizon) is not int or self.remaining_horizon not in (1, 2):
            raise PartialSupportRobustPlannerInvariantViolation(
                "selected row bound horizon is invalid"
            )
        for value, field in (
            (self.reward_lower, "selected reward lower"),
            (self.reward_upper, "selected reward upper"),
            (self.failure_upper, "selected failure upper"),
            (self.other_mass_lower, "OTHER lower"),
            (self.other_mass_upper, "OTHER upper"),
            (self.other_mass_used_for_reward_lower, "OTHER reward-lower mass"),
            (self.other_mass_used_for_reward_upper, "OTHER reward-upper mass"),
            (self.other_mass_used_for_failure_upper, "OTHER risk mass"),
        ):
            _fraction(value, field, lower=Fraction(0))
        if (
            self.reward_lower > self.reward_upper
            or not 0 <= self.failure_upper <= 1
            or not 0 <= self.other_mass_lower <= self.other_mass_upper <= 1
            or any(
                not self.other_mass_lower <= value <= self.other_mass_upper
                for value in (
                    self.other_mass_used_for_reward_lower,
                    self.other_mass_used_for_reward_upper,
                    self.other_mass_used_for_failure_upper,
                )
            )
        ):
            raise PartialSupportRobustPlannerInvariantViolation(
                "selected row robust bound is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_robust_row_bound.v1",
            "schema_version": SCHEMA_VERSION,
            "row_id": self.row_id,
            "remaining_horizon": self.remaining_horizon,
            "reward_lower": _fdoc(self.reward_lower),
            "reward_upper": _fdoc(self.reward_upper),
            "failure_upper": _fdoc(self.failure_upper),
            "other_mass_lower": _fdoc(self.other_mass_lower),
            "other_mass_upper": _fdoc(self.other_mass_upper),
            "other_mass_used_for_reward_lower": _fdoc(
                self.other_mass_used_for_reward_lower
            ),
            "other_mass_used_for_reward_upper": _fdoc(
                self.other_mass_used_for_reward_upper
            ),
            "other_mass_used_for_failure_upper": _fdoc(
                self.other_mass_used_for_failure_upper
            ),
        }

    @property
    def row_bound_id(self) -> str:
        return _content_id("row_bound", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "row_bound_id": self.row_bound_id}


@dataclass(frozen=True, slots=True)
class SelectedRowProvenanceV1:
    row_id: str
    category: SelectedRowCategory
    policy_scope_key: str
    ground_state_id: str
    ground_action_id: str
    remaining_horizon: int

    def __post_init__(self) -> None:
        for value, field in (
            (self.row_id, "provenance row"),
            (self.policy_scope_key, "provenance policy scope"),
            (self.ground_state_id, "provenance ground state"),
            (self.ground_action_id, "provenance ground action"),
        ):
            _cid(value, field)
        if (
            type(self.category) is not SelectedRowCategory
            or type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, 2)
        ):
            raise PartialSupportRobustPlannerInvariantViolation(
                "selected row provenance is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_selected_row_provenance.v1",
            "schema_version": SCHEMA_VERSION,
            "row_id": self.row_id,
            "category": self.category.value,
            "policy_scope_key": self.policy_scope_key,
            "ground_state_id": self.ground_state_id,
            "ground_action_id": self.ground_action_id,
            "remaining_horizon": self.remaining_horizon,
        }

    @property
    def provenance_id(self) -> str:
        return _content_id("provenance", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "provenance_id": self.provenance_id}


@dataclass(frozen=True, slots=True)
class OtherMassProvenanceV1:
    row_id: str
    remaining_horizon: int
    category: SelectedRowCategory
    other_mass_upper: Fraction
    failure_charge_count: int = 1

    def __post_init__(self) -> None:
        _cid(self.row_id, "OTHER provenance row")
        if (
            type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, 2)
            or type(self.category) is not SelectedRowCategory
            or self.failure_charge_count != 1
        ):
            raise PartialSupportRobustPlannerInvariantViolation(
                "OTHER provenance must charge one row exactly once"
            )
        _fraction(
            self.other_mass_upper,
            "selected OTHER upper",
            lower=Fraction(0),
            upper=Fraction(1),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_other_mass_provenance.v1",
            "schema_version": SCHEMA_VERSION,
            "row_id": self.row_id,
            "remaining_horizon": self.remaining_horizon,
            "category": self.category.value,
            "other_mass_upper": _fdoc(self.other_mass_upper),
            "failure_charge_count": 1,
        }

    @property
    def other_mass_provenance_id(self) -> str:
        return _content_id("other_mass", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "other_mass_provenance_id": self.other_mass_provenance_id,
        }


@dataclass(frozen=True, slots=True)
class OtherOnlyCounterfactualV1:
    status: CounterfactualStatus
    original_certified: bool
    zero_other_certified: bool | None
    changes_failed_to_certified: bool
    zero_other_model_id: str | None
    zero_other_failure_upper: Fraction | None
    zero_other_normalized_regret_upper: Fraction | None
    acquisition_authorized: bool = False

    def __post_init__(self) -> None:
        if type(self.status) is not CounterfactualStatus:
            raise PartialSupportRobustPlannerInvariantViolation(
                "OTHER counterfactual status is invalid"
            )
        if self.zero_other_model_id is not None:
            _cid(self.zero_other_model_id, "zero-OTHER model")
        for value, field in (
            (self.zero_other_failure_upper, "zero-OTHER failure"),
            (self.zero_other_normalized_regret_upper, "zero-OTHER regret"),
        ):
            if value is not None:
                _fraction(value, field, lower=Fraction(0))
        expected_change = (
            not self.original_certified
            and self.zero_other_certified is True
        )
        if (
            type(self.original_certified) is not bool
            or (
                self.zero_other_certified is not None
                and type(self.zero_other_certified) is not bool
            )
            or type(self.changes_failed_to_certified) is not bool
            or self.changes_failed_to_certified is not expected_change
            or self.acquisition_authorized is not False
            or (
                self.status is CounterfactualStatus.ORIGINAL_ALREADY_CERTIFIED
                and (
                    not self.original_certified
                    or self.zero_other_certified is not None
                    or self.zero_other_model_id is not None
                    or self.zero_other_failure_upper is not None
                    or self.zero_other_normalized_regret_upper is not None
                )
            )
            or (
                self.status is CounterfactualStatus.ZERO_OTHER_CERTIFIED
                and (
                    not expected_change
                    or self.zero_other_model_id is None
                    or self.zero_other_failure_upper is None
                    or self.zero_other_normalized_regret_upper is None
                )
            )
            or (
                self.status is CounterfactualStatus.ZERO_OTHER_STILL_FAILED
                and (
                    self.original_certified
                    or self.zero_other_certified is not False
                    or self.zero_other_model_id is None
                    or self.zero_other_failure_upper is None
                    or self.zero_other_normalized_regret_upper is None
                )
            )
            or (
                self.status
                is CounterfactualStatus.ZERO_OTHER_INFEASIBLE_SIMPLEX
                and (
                    self.original_certified
                    or self.zero_other_certified is not None
                    or self.zero_other_model_id is not None
                    or self.zero_other_failure_upper is not None
                    or self.zero_other_normalized_regret_upper is not None
                )
            )
        ):
            raise PartialSupportRobustPlannerInvariantViolation(
                "OTHER-only counterfactual conclusion is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_other_counterfactual.v1",
            "schema_version": SCHEMA_VERSION,
            "status": self.status.value,
            "original_certified": self.original_certified,
            "zero_other_certified": self.zero_other_certified,
            "changes_failed_to_certified": self.changes_failed_to_certified,
            "zero_other_model_id": self.zero_other_model_id,
            "zero_other_failure_upper": (
                None
                if self.zero_other_failure_upper is None
                else _fdoc(self.zero_other_failure_upper)
            ),
            "zero_other_normalized_regret_upper": (
                None
                if self.zero_other_normalized_regret_upper is None
                else _fdoc(self.zero_other_normalized_regret_upper)
            ),
            "acquisition_authorized": False,
        }

    @property
    def counterfactual_id(self) -> str:
        return _content_id("counterfactual", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counterfactual_id": self.counterfactual_id}


@dataclass(frozen=True, slots=True)
class FailedProofFrontierV1:
    reason: FailedFrontierReason
    selected_row_ids: tuple[str, ...]
    other_positive_row_ids: tuple[str, ...]
    other_only_counterfactual_changes: bool

    def __post_init__(self) -> None:
        if type(self.reason) is not FailedFrontierReason:
            raise PartialSupportRobustPlannerInvariantViolation(
                "failed frontier reason is invalid"
            )
        for values, field in (
            (self.selected_row_ids, "frontier selected rows"),
            (self.other_positive_row_ids, "frontier OTHER-positive rows"),
        ):
            if type(values) is not tuple or values != tuple(sorted(set(values))):
                raise PartialSupportRobustPlannerInvariantViolation(
                    f"{field} must be sorted and distinct"
                )
            for item in values:
                _cid(item, field)
        if not set(self.other_positive_row_ids).issubset(
            self.selected_row_ids
        ):
            raise PartialSupportRobustPlannerInvariantViolation(
                "OTHER frontier rows are not selected rows"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_failed_frontier.v1",
            "schema_version": SCHEMA_VERSION,
            "reason": self.reason.value,
            "selected_row_ids": list(self.selected_row_ids),
            "other_positive_row_ids": list(self.other_positive_row_ids),
            "other_only_counterfactual_changes": (
                self.other_only_counterfactual_changes
            ),
        }

    @property
    def frontier_id(self) -> str:
        return _content_id("frontier", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "frontier_id": self.frontier_id}


@dataclass(frozen=True, slots=True)
class RobustPlanAuditV1:
    solver_kind: RobustSolverKind
    model_id: str
    threshold_profile_id: str
    status: RobustAuditStatus
    assignments: tuple[RobustPolicyAssignmentV1, ...]
    selected_row_bounds: tuple[RobustSelectedRowBoundV1, ...]
    selected_row_provenance: tuple[SelectedRowProvenanceV1, ...]
    other_mass_upper_on_selected_policy: tuple[OtherMassProvenanceV1, ...]
    root_reward_lower: Fraction
    unrestricted_reward_upper: Fraction
    root_failure_upper: Fraction
    normalized_regret_upper: Fraction
    counterfactual: OtherOnlyCounterfactualV1
    failed_frontier: FailedProofFrontierV1 | None
    complete_reachable_policy: bool = True
    other_charged_once_per_row: bool = True
    kernel_calls: int = 0

    def __post_init__(self) -> None:
        if (
            type(self.solver_kind) is not RobustSolverKind
            or type(self.status) is not RobustAuditStatus
        ):
            raise PartialSupportRobustPlannerInvariantViolation(
                "robust audit enum changed"
            )
        _cid(self.model_id, "audit model")
        _cid(self.threshold_profile_id, "audit threshold")
        for values, expected_type, field, id_getter in (
            (
                self.assignments,
                RobustPolicyAssignmentV1,
                "assignments",
                lambda item: item.assignment_id,
            ),
            (
                self.selected_row_bounds,
                RobustSelectedRowBoundV1,
                "selected row bounds",
                lambda item: item.row_bound_id,
            ),
            (
                self.selected_row_provenance,
                SelectedRowProvenanceV1,
                "selected row provenance",
                lambda item: item.provenance_id,
            ),
            (
                self.other_mass_upper_on_selected_policy,
                OtherMassProvenanceV1,
                "selected OTHER provenance",
                lambda item: item.other_mass_provenance_id,
            ),
        ):
            if (
                type(values) is not tuple
                or not values
                or any(type(item) is not expected_type for item in values)
                or tuple(id_getter(item) for item in values)
                != tuple(sorted({id_getter(item) for item in values}))
            ):
                raise PartialSupportRobustPlannerInvariantViolation(
                    f"audit {field} must be typed, nonempty, distinct, and sorted"
                )
        for value, field in (
            (self.root_reward_lower, "audit reward lower"),
            (self.unrestricted_reward_upper, "audit unrestricted upper"),
            (self.root_failure_upper, "audit failure upper"),
            (self.normalized_regret_upper, "audit normalized regret"),
        ):
            _fraction(value, field, lower=Fraction(0))
        if (
            self.root_reward_lower > self.unrestricted_reward_upper
            or self.root_failure_upper > 1
            or type(self.counterfactual) is not OtherOnlyCounterfactualV1
            or (
                self.failed_frontier is not None
                and type(self.failed_frontier) is not FailedProofFrontierV1
            )
            or (
                self.status is RobustAuditStatus.CERTIFIED
                and self.failed_frontier is not None
            )
            or (
                self.status is RobustAuditStatus.FAILED_PROOF_FRONTIER
                and self.failed_frontier is None
            )
            or self.complete_reachable_policy is not True
            or self.other_charged_once_per_row is not True
            or self.kernel_calls != 0
        ):
            raise PartialSupportRobustPlannerInvariantViolation(
                "robust audit conclusion or authority boundary is invalid"
            )

    @property
    def certified(self) -> bool:
        return self.status is RobustAuditStatus.CERTIFIED

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_robust_plan_audit.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "solver_kind": self.solver_kind.value,
            "model_id": self.model_id,
            "threshold_profile_id": self.threshold_profile_id,
            "status": self.status.value,
            "assignment_ids": [item.assignment_id for item in self.assignments],
            "selected_row_bound_ids": [
                item.row_bound_id for item in self.selected_row_bounds
            ],
            "selected_row_provenance_ids": [
                item.provenance_id for item in self.selected_row_provenance
            ],
            "other_mass_provenance_ids": [
                item.other_mass_provenance_id
                for item in self.other_mass_upper_on_selected_policy
            ],
            "root_reward_lower": _fdoc(self.root_reward_lower),
            "unrestricted_reward_upper": _fdoc(
                self.unrestricted_reward_upper
            ),
            "root_failure_upper": _fdoc(self.root_failure_upper),
            "normalized_regret_upper": _fdoc(self.normalized_regret_upper),
            "counterfactual_id": self.counterfactual.counterfactual_id,
            "failed_frontier_id": (
                None
                if self.failed_frontier is None
                else self.failed_frontier.frontier_id
            ),
            "complete_reachable_policy": True,
            "other_charged_once_per_row": True,
            "kernel_calls": 0,
        }

    @property
    def audit_id(self) -> str:
        return _content_id("audit", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "assignments": [item.to_document() for item in self.assignments],
            "selected_row_bounds": [
                item.to_document() for item in self.selected_row_bounds
            ],
            "selected_row_provenance": [
                item.to_document() for item in self.selected_row_provenance
            ],
            "other_mass_upper_on_selected_policy": [
                item.to_document()
                for item in self.other_mass_upper_on_selected_policy
            ],
            "counterfactual": self.counterfactual.to_document(),
            "failed_frontier": (
                None
                if self.failed_frontier is None
                else self.failed_frontier.to_document()
            ),
            "audit_id": self.audit_id,
        }


@dataclass(frozen=True, slots=True)
class RobustAuditVerificationV1:
    audit_id: str
    replayed_audit_id: str
    model_id: str
    solver_kind: RobustSolverKind
    valid: bool = True
    same_implementation_semantic_replay: bool = True
    independent_implementation_claimed: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.audit_id, "verified audit"),
            (self.replayed_audit_id, "replayed audit"),
            (self.model_id, "verified model"),
        ):
            _cid(value, field)
        if (
            self.audit_id != self.replayed_audit_id
            or type(self.solver_kind) is not RobustSolverKind
            or self.valid is not True
            or self.same_implementation_semantic_replay is not True
            or self.independent_implementation_claimed is not False
        ):
            raise PartialSupportRobustPlannerInvariantViolation(
                "robust audit replay did not reproduce the claim"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_robust_audit_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "audit_id": self.audit_id,
            "replayed_audit_id": self.replayed_audit_id,
            "model_id": self.model_id,
            "solver_kind": self.solver_kind.value,
            "valid": True,
            "same_implementation_semantic_replay": True,
            "independent_implementation_claimed": False,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


@dataclass(frozen=True, slots=True)
class _ExtremeExpectation:
    value: Fraction
    allocations: Mapping[str, Fraction]


def _extreme_expectation(
    masses: Sequence[IntervalDestinationMassV1],
    values: Mapping[str, Fraction],
    *,
    maximize: bool,
) -> _ExtremeExpectation:
    """Optimize one expectation over one joint interval simplex."""

    if {item.destination_id for item in masses} != set(values):
        raise PartialSupportRobustPlannerInvariantViolation(
            "robust expectation value registry differs from row destinations"
        )
    allocations = {
        item.destination_id: item.lower for item in masses
    }
    residual = Fraction(1) - sum(allocations.values(), Fraction(0))
    ordered = sorted(
        masses,
        key=lambda item: (
            -values[item.destination_id]
            if maximize
            else values[item.destination_id],
            item.destination_id,
        ),
    )
    for item in ordered:
        if residual == 0:
            break
        added = min(residual, item.upper - item.lower)
        allocations[item.destination_id] += added
        residual -= added
    if residual != 0:
        raise PartialSupportRobustPlannerInvariantViolation(
            "joint interval simplex optimizer could not allocate unit mass"
        )
    return _ExtremeExpectation(
        sum(
            allocations[item.destination_id] * values[item.destination_id]
            for item in masses
        ),
        allocations,
    )


@dataclass(frozen=True, slots=True)
class _RowEvaluation:
    bound: RobustSelectedRowBoundV1
    provenance: SelectedRowProvenanceV1


@dataclass(frozen=True, slots=True)
class _StateActionEvaluation:
    reward_lower: Fraction
    reward_upper: Fraction
    failure_upper: Fraction
    rows: tuple[_RowEvaluation, ...]


@dataclass(frozen=True, slots=True)
class _PolicyEvaluation:
    assignments: tuple[RobustPolicyAssignmentV1, ...]
    reward_lower: Fraction
    reward_upper: Fraction
    failure_upper: Fraction
    rows: tuple[_RowEvaluation, ...]

    @property
    def policy_key(self) -> tuple[str, ...]:
        return tuple(item.assignment_id for item in self.assignments)


@dataclass(frozen=True, slots=True)
class _SolvedCore:
    selected: _PolicyEvaluation
    unrestricted_reward_upper: Fraction
    normalized_regret_upper: Fraction
    status: RobustAuditStatus


def _registries(
    model: PartialSupportIntervalModelV1,
) -> tuple[
    dict[str, StateActionCatalogueV1],
    dict[str, RegisteredDestinationV1],
    dict[tuple[str, int, str], IntervalSimplexRowV1],
]:
    return (
        {item.state_id: item for item in model.catalogues},
        {item.destination_id: item for item in model.destinations},
        {item.row_key: item for item in model.rows},
    )


def _reachable_child_states(
    model: PartialSupportIntervalModelV1,
) -> tuple[str, ...]:
    catalogue_by_state, destination_by_id, row_by_key = _registries(model)
    root = catalogue_by_state[model.root_state_id]
    states: set[str] = set()
    for action in root.actions:
        row = row_by_key[(model.root_state_id, 2, action.action_id)]
        for mass in row.masses:
            destination = destination_by_id[mass.destination_id]
            if (
                mass.upper > 0
                and destination.category is DestinationCategory.ACTIVE_STATE
            ):
                assert destination.state_id is not None
                states.add(destination.state_id)
    return tuple(sorted(states))


def _evaluate_ground_row(
    row: IntervalSimplexRowV1,
    *,
    destination_by_id: Mapping[str, RegisteredDestinationV1],
    child_values: Mapping[str, _StateActionEvaluation],
    threshold: RobustThresholdProfileV1,
    category: SelectedRowCategory,
    policy_scope_key: str,
) -> _RowEvaluation:
    risk_values: dict[str, Fraction] = {}
    reward_lower_values: dict[str, Fraction] = {}
    reward_upper_values: dict[str, Fraction] = {}
    for mass in row.masses:
        destination = destination_by_id[mass.destination_id]
        if destination.category in (
            DestinationCategory.FAILURE,
            DestinationCategory.OTHER,
        ):
            risk_values[mass.destination_id] = Fraction(1)
        elif (
            destination.category is DestinationCategory.ACTIVE_STATE
            and row.remaining_horizon > 1
        ):
            assert destination.state_id is not None
            risk_values[mass.destination_id] = child_values[
                destination.state_id
            ].failure_upper
        else:
            risk_values[mass.destination_id] = Fraction(0)

        if (
            destination.category is DestinationCategory.ACTIVE_STATE
            and row.remaining_horizon > 1
        ):
            assert destination.state_id is not None
            reward_lower_values[mass.destination_id] = child_values[
                destination.state_id
            ].reward_lower
            reward_upper_values[mass.destination_id] = child_values[
                destination.state_id
            ].reward_upper
        else:
            reward_lower_values[mass.destination_id] = Fraction(0)
            reward_upper_values[mass.destination_id] = (
                threshold.reward_ceiling
                if (
                    destination.category is DestinationCategory.OTHER
                    and row.remaining_horizon > 1
                )
                else Fraction(0)
            )

    risk = _extreme_expectation(row.masses, risk_values, maximize=True)
    reward_lower = _extreme_expectation(
        row.masses,
        reward_lower_values,
        maximize=False,
    )
    reward_upper = _extreme_expectation(
        row.masses,
        reward_upper_values,
        maximize=True,
    )
    total_lower = row.reward_lower + reward_lower.value
    total_upper = min(
        threshold.reward_ceiling,
        row.reward_upper + reward_upper.value,
    )
    if (
        row.reward_upper > threshold.reward_ceiling
        or total_lower > threshold.reward_ceiling
        or total_lower > total_upper
    ):
        raise PartialSupportRobustPlannerInvariantViolation(
            "row reward interval exceeds the registered reward ceiling"
        )
    other_id = row.other_destination_id
    bound = RobustSelectedRowBoundV1(
        row.row_id,
        row.remaining_horizon,
        total_lower,
        total_upper,
        risk.value,
        row.other_mass.lower,
        row.other_mass.upper,
        reward_lower.allocations[other_id],
        reward_upper.allocations[other_id],
        risk.allocations[other_id],
    )
    provenance = SelectedRowProvenanceV1(
        row.row_id,
        category,
        policy_scope_key,
        row.state_id,
        row.action_id,
        row.remaining_horizon,
    )
    return _RowEvaluation(bound, provenance)


def _average_action_evaluations(
    evaluations: Sequence[_RowEvaluation],
) -> _StateActionEvaluation:
    if not evaluations:
        raise PartialSupportRobustPlannerInvariantViolation(
            "fixed concretizer support is empty"
        )
    denominator = len(evaluations)
    return _StateActionEvaluation(
        sum(
            (item.bound.reward_lower for item in evaluations),
            Fraction(0),
        )
        / denominator,
        sum(
            (item.bound.reward_upper for item in evaluations),
            Fraction(0),
        )
        / denominator,
        sum(
            (item.bound.failure_upper for item in evaluations),
            Fraction(0),
        )
        / denominator,
        tuple(evaluations),
    )


def _direct_policy_evaluations(
    model: PartialSupportIntervalModelV1,
    threshold: RobustThresholdProfileV1,
) -> tuple[_PolicyEvaluation, ...]:
    catalogue_by_state, destination_by_id, row_by_key = _registries(model)
    child_states = _reachable_child_states(model)
    root_catalogue = catalogue_by_state[model.root_state_id]
    child_action_domains = [
        tuple(action.action_id for action in catalogue_by_state[state].actions)
        for state in child_states
    ]
    assignment_count = len(root_catalogue.actions)
    for domain in child_action_domains:
        assignment_count *= len(domain)
    if assignment_count > MAX_POLICY_ASSIGNMENTS:
        raise PartialSupportRobustPlannerInvariantViolation(
            "ground robust policy enumeration exceeds the frozen cap"
        )

    results: list[_PolicyEvaluation] = []
    child_products = (
        itertools.product(*child_action_domains)
        if child_action_domains
        else ((),)
    )
    for child_actions in child_products:
        child_values: dict[str, _StateActionEvaluation] = {}
        child_rows: list[_RowEvaluation] = []
        assignments: list[RobustPolicyAssignmentV1] = []
        for state_id, action_id in zip(child_states, child_actions):
            row = row_by_key[(state_id, 1, action_id)]
            evaluated = _evaluate_ground_row(
                row,
                destination_by_id=destination_by_id,
                child_values={},
                threshold=threshold,
                category=SelectedRowCategory.CONTINUATION_SELECTED,
                policy_scope_key=state_id,
            )
            child_values[state_id] = _StateActionEvaluation(
                evaluated.bound.reward_lower,
                evaluated.bound.reward_upper,
                evaluated.bound.failure_upper,
                (evaluated,),
            )
            child_rows.append(evaluated)
            assignments.append(
                RobustPolicyAssignmentV1(
                    PolicyScope.GROUND_STATE,
                    state_id,
                    1,
                    action_id,
                )
            )
        for root_action in root_catalogue.actions:
            root_row = row_by_key[
                (model.root_state_id, 2, root_action.action_id)
            ]
            root_evaluation = _evaluate_ground_row(
                root_row,
                destination_by_id=destination_by_id,
                child_values=child_values,
                threshold=threshold,
                category=SelectedRowCategory.ROOT_SELECTED,
                policy_scope_key=model.root_state_id,
            )
            root_assignment = RobustPolicyAssignmentV1(
                PolicyScope.GROUND_STATE,
                model.root_state_id,
                2,
                root_action.action_id,
            )
            all_assignments = tuple(
                sorted(
                    (root_assignment, *assignments),
                    key=lambda item: item.assignment_id,
                )
            )
            all_rows = tuple(
                sorted(
                    (root_evaluation, *child_rows),
                    key=lambda item: item.provenance.provenance_id,
                )
            )
            results.append(
                _PolicyEvaluation(
                    all_assignments,
                    root_evaluation.bound.reward_lower,
                    root_evaluation.bound.reward_upper,
                    root_evaluation.bound.failure_upper,
                    all_rows,
                )
            )
    return tuple(results)


def _unrestricted_ground_reward_upper_h2(
    model: PartialSupportIntervalModelV1,
    threshold: RobustThresholdProfileV1,
) -> Fraction:
    """Compute the exact H=2 ground reward upper without policy products.

    The unrestricted comparator maximizes reward upper only.  At H=2 every
    continuation state is visited after the single root transition, and the
    root robust reward-upper functional is monotone in each continuation
    reward upper.  Hence each continuation action can be maximized
    independently before the root actions are compared.  This is exactly the
    same maximum as complete deterministic ground-policy enumeration, without
    its Cartesian assignment count.  Risk-constrained direct planning still
    uses ``_direct_policy_evaluations`` and retains the frozen cap.
    """

    catalogue_by_state, destination_by_id, row_by_key = _registries(model)
    child_values: dict[str, _StateActionEvaluation] = {}
    for state_id in _reachable_child_states(model):
        candidates = tuple(
            _evaluate_ground_row(
                row_by_key[(state_id, 1, action.action_id)],
                destination_by_id=destination_by_id,
                child_values={},
                threshold=threshold,
                category=SelectedRowCategory.CONTINUATION_SELECTED,
                policy_scope_key=state_id,
            )
            for action in catalogue_by_state[state_id].actions
        )
        if not candidates:
            raise PartialSupportRobustPlannerInvariantViolation(
                "reachable child has no unrestricted ground action"
            )
        selected = min(
            candidates,
            key=lambda item: (
                -item.bound.reward_upper,
                item.bound.row_id,
            ),
        )
        child_values[state_id] = _StateActionEvaluation(
            selected.bound.reward_lower,
            selected.bound.reward_upper,
            selected.bound.failure_upper,
            (selected,),
        )

    root = catalogue_by_state[model.root_state_id]
    root_values = tuple(
        _evaluate_ground_row(
            row_by_key[(model.root_state_id, 2, action.action_id)],
            destination_by_id=destination_by_id,
            child_values=child_values,
            threshold=threshold,
            category=SelectedRowCategory.ROOT_SELECTED,
            policy_scope_key=model.root_state_id,
        ).bound.reward_upper
        for action in root.actions
    )
    if not root_values:
        raise PartialSupportRobustPlannerInvariantViolation(
            "root has no unrestricted ground action"
        )
    return max(root_values)


def _concretizer_registry(
    model: PartialSupportIntervalModelV1,
) -> dict[tuple[str, str, str], DistinctActionConcretizerEntryV1]:
    return {
        (
            item.state_coordinate_key,
            item.state_id,
            item.abstract_action_key,
        ): item
        for item in model.concretizer_entries
    }


def _common_abstract_actions(
    model: PartialSupportIntervalModelV1,
    state_ids: Sequence[str],
) -> tuple[str, ...]:
    catalogue_by_state, _, _ = _registries(model)
    entries = _concretizer_registry(model)
    common: set[str] | None = None
    for state_id in state_ids:
        cell = catalogue_by_state[state_id].state_coordinate_key
        available = {
            action_key
            for entry_cell, entry_state, action_key in entries
            if entry_cell == cell and entry_state == state_id
        }
        common = available if common is None else common.intersection(available)
    result = tuple(sorted(common or ()))
    if not result:
        raise PartialSupportRobustPlannerInvariantViolation(
            "quotient cell has no common concretized semantic action"
        )
    return result


def _evaluate_concretized_state_action(
    model: PartialSupportIntervalModelV1,
    threshold: RobustThresholdProfileV1,
    *,
    state_id: str,
    remaining_horizon: int,
    abstract_action_key: str,
    child_values: Mapping[str, _StateActionEvaluation],
    category: SelectedRowCategory,
) -> _StateActionEvaluation:
    catalogue_by_state, destination_by_id, row_by_key = _registries(model)
    cell = catalogue_by_state[state_id].state_coordinate_key
    entry = _concretizer_registry(model).get(
        (cell, state_id, abstract_action_key)
    )
    if entry is None:
        raise PartialSupportRobustPlannerInvariantViolation(
            "selected abstract action has no state concretizer"
        )
    rows = tuple(
        _evaluate_ground_row(
            row_by_key[(state_id, remaining_horizon, action_id)],
            destination_by_id=destination_by_id,
            child_values=child_values,
            threshold=threshold,
            category=category,
            policy_scope_key=cell,
        )
        for action_id in entry.ground_action_ids
    )
    return _average_action_evaluations(rows)


def _quotient_policy_evaluations(
    model: PartialSupportIntervalModelV1,
    threshold: RobustThresholdProfileV1,
) -> tuple[_PolicyEvaluation, ...]:
    catalogue_by_state, _, _ = _registries(model)
    child_states = _reachable_child_states(model)
    child_cells: dict[str, tuple[str, ...]] = {}
    for state_id in child_states:
        cell = catalogue_by_state[state_id].state_coordinate_key
        child_cells.setdefault(cell, ())
        child_cells[cell] = tuple(sorted((*child_cells[cell], state_id)))
    ordered_cells = tuple(sorted(child_cells))
    child_action_domains = [
        _common_abstract_actions(model, child_cells[cell])
        for cell in ordered_cells
    ]
    root_cell = catalogue_by_state[model.root_state_id].state_coordinate_key
    root_actions = _common_abstract_actions(model, (model.root_state_id,))
    assignment_count = len(root_actions)
    for domain in child_action_domains:
        assignment_count *= len(domain)
    if assignment_count > MAX_POLICY_ASSIGNMENTS:
        raise PartialSupportRobustPlannerInvariantViolation(
            "quotient robust policy enumeration exceeds the frozen cap"
        )

    results: list[_PolicyEvaluation] = []
    child_products = (
        itertools.product(*child_action_domains)
        if child_action_domains
        else ((),)
    )
    for selected_child_actions in child_products:
        child_values: dict[str, _StateActionEvaluation] = {}
        child_rows: list[_RowEvaluation] = []
        assignments: list[RobustPolicyAssignmentV1] = []
        for cell, abstract_action in zip(
            ordered_cells,
            selected_child_actions,
        ):
            assignments.append(
                RobustPolicyAssignmentV1(
                    PolicyScope.QUOTIENT_CELL,
                    cell,
                    1,
                    abstract_action,
                )
            )
            for state_id in child_cells[cell]:
                state_value = _evaluate_concretized_state_action(
                    model,
                    threshold,
                    state_id=state_id,
                    remaining_horizon=1,
                    abstract_action_key=abstract_action,
                    child_values={},
                    category=(
                        SelectedRowCategory.CONTINUATION_CONCRETIZER_COMPONENT
                    ),
                )
                child_values[state_id] = state_value
                child_rows.extend(state_value.rows)
        for root_action in root_actions:
            root_value = _evaluate_concretized_state_action(
                model,
                threshold,
                state_id=model.root_state_id,
                remaining_horizon=2,
                abstract_action_key=root_action,
                child_values=child_values,
                category=SelectedRowCategory.ROOT_CONCRETIZER_COMPONENT,
            )
            root_assignment = RobustPolicyAssignmentV1(
                PolicyScope.QUOTIENT_CELL,
                root_cell,
                2,
                root_action,
            )
            results.append(
                _PolicyEvaluation(
                    tuple(
                        sorted(
                            (root_assignment, *assignments),
                            key=lambda item: item.assignment_id,
                        )
                    ),
                    root_value.reward_lower,
                    root_value.reward_upper,
                    root_value.failure_upper,
                    tuple(
                        sorted(
                            (*root_value.rows, *child_rows),
                            key=lambda item: item.provenance.provenance_id,
                        )
                    ),
                )
            )
    return tuple(results)


def _choose_policy(
    evaluations: Sequence[_PolicyEvaluation],
    unrestricted_reward_upper: Fraction,
    threshold: RobustThresholdProfileV1,
) -> _SolvedCore:
    if not evaluations:
        raise PartialSupportRobustPlannerInvariantViolation(
            "robust solver produced no deterministic policies"
        )

    def regret(item: _PolicyEvaluation) -> Fraction:
        return max(
            Fraction(0),
            unrestricted_reward_upper - item.reward_lower,
        ) / threshold.reward_ceiling

    certified = tuple(
        item
        for item in evaluations
        if (
            item.failure_upper <= threshold.risk_tolerance
            and regret(item) <= threshold.normalized_regret_tolerance
        )
    )
    if certified:
        selected = min(
            certified,
            key=lambda item: (
                -item.reward_lower,
                item.failure_upper,
                item.policy_key,
            ),
        )
        status = RobustAuditStatus.CERTIFIED
    else:
        risk_feasible = tuple(
            item
            for item in evaluations
            if item.failure_upper <= threshold.risk_tolerance
        )
        selected = min(
            risk_feasible if risk_feasible else evaluations,
            key=lambda item: (
                regret(item) if risk_feasible else item.failure_upper,
                item.failure_upper,
                -item.reward_lower,
                item.policy_key,
            ),
        )
        status = RobustAuditStatus.FAILED_PROOF_FRONTIER
    return _SolvedCore(
        selected,
        unrestricted_reward_upper,
        regret(selected),
        status,
    )


def _solve_core(
    model: PartialSupportIntervalModelV1,
    threshold: RobustThresholdProfileV1,
    solver_kind: RobustSolverKind,
) -> _SolvedCore:
    if (
        type(model) is not PartialSupportIntervalModelV1
        or type(threshold) is not RobustThresholdProfileV1
        or type(solver_kind) is not RobustSolverKind
        or threshold.context_id != model.context_id
    ):
        raise PartialSupportRobustPlannerInvariantViolation(
            "robust solver inputs or identities do not match"
        )
    if solver_kind is RobustSolverKind.GROUND_DIRECT:
        evaluations = _direct_policy_evaluations(model, threshold)
        unrestricted = max(item.reward_upper for item in evaluations)
    else:
        unrestricted = _unrestricted_ground_reward_upper_h2(
            model,
            threshold,
        )
        evaluations = _quotient_policy_evaluations(model, threshold)
    return _choose_policy(evaluations, unrestricted, threshold)


def _zero_other_model(
    model: PartialSupportIntervalModelV1,
) -> PartialSupportIntervalModelV1:
    other_id = model.other_destination.destination_id
    rows: list[IntervalSimplexRowV1] = []
    for row in model.rows:
        masses = tuple(
            (
                IntervalDestinationMassV1(
                    item.destination_id,
                    Fraction(0),
                    Fraction(0),
                )
                if item.destination_id == other_id
                else item
            )
            for item in row.masses
        )
        rows.append(replace(row, masses=masses))
    return build_partial_support_model_v1(
        context_id=model.context_id,
        root_state_id=model.root_state_id,
        catalogues=model.catalogues,
        destinations=model.destinations,
        rows=rows,
        concretizer_entries=model.concretizer_entries,
    )


def _counterfactual(
    model: PartialSupportIntervalModelV1,
    threshold: RobustThresholdProfileV1,
    solver_kind: RobustSolverKind,
    original: _SolvedCore,
) -> OtherOnlyCounterfactualV1:
    if original.status is RobustAuditStatus.CERTIFIED:
        return OtherOnlyCounterfactualV1(
            CounterfactualStatus.ORIGINAL_ALREADY_CERTIFIED,
            True,
            None,
            False,
            None,
            None,
            None,
        )
    try:
        zero_model = _zero_other_model(model)
    except PartialSupportRobustPlannerInvariantViolation:
        return OtherOnlyCounterfactualV1(
            CounterfactualStatus.ZERO_OTHER_INFEASIBLE_SIMPLEX,
            False,
            None,
            False,
            None,
            None,
            None,
        )
    zero = _solve_core(zero_model, threshold, solver_kind)
    zero_certified = zero.status is RobustAuditStatus.CERTIFIED
    return OtherOnlyCounterfactualV1(
        (
            CounterfactualStatus.ZERO_OTHER_CERTIFIED
            if zero_certified
            else CounterfactualStatus.ZERO_OTHER_STILL_FAILED
        ),
        False,
        zero_certified,
        zero_certified,
        zero_model.model_id,
        zero.selected.failure_upper,
        zero.normalized_regret_upper,
    )


def _make_audit(
    model: PartialSupportIntervalModelV1,
    threshold: RobustThresholdProfileV1,
    solver_kind: RobustSolverKind,
) -> RobustPlanAuditV1:
    core = _solve_core(model, threshold, solver_kind)
    counterfactual = _counterfactual(
        model,
        threshold,
        solver_kind,
        core,
    )
    selected_bounds = tuple(
        sorted(
            (item.bound for item in core.selected.rows),
            key=lambda item: item.row_bound_id,
        )
    )
    provenance = tuple(
        sorted(
            (item.provenance for item in core.selected.rows),
            key=lambda item: item.provenance_id,
        )
    )
    category_by_row = {
        item.row_id: item.category for item in provenance
    }
    other = tuple(
        sorted(
            (
                OtherMassProvenanceV1(
                    item.row_id,
                    item.remaining_horizon,
                    category_by_row[item.row_id],
                    item.other_mass_upper,
                )
                for item in selected_bounds
            ),
            key=lambda item: item.other_mass_provenance_id,
        )
    )
    frontier: FailedProofFrontierV1 | None = None
    if core.status is RobustAuditStatus.FAILED_PROOF_FRONTIER:
        risk_failed = core.selected.failure_upper >= threshold.risk_tolerance
        regret_failed = (
            core.normalized_regret_upper
            > threshold.normalized_regret_tolerance
        )
        reason = (
            FailedFrontierReason.RISK_AND_REGRET
            if risk_failed and regret_failed
            else (
                FailedFrontierReason.RISK
                if risk_failed
                else FailedFrontierReason.REGRET
            )
        )
        frontier = FailedProofFrontierV1(
            reason,
            tuple(sorted(item.row_id for item in selected_bounds)),
            tuple(
                sorted(
                    item.row_id
                    for item in selected_bounds
                    if item.other_mass_upper > 0
                )
            ),
            counterfactual.changes_failed_to_certified,
        )
    return RobustPlanAuditV1(
        solver_kind,
        model.model_id,
        threshold.threshold_profile_id,
        core.status,
        core.selected.assignments,
        selected_bounds,
        provenance,
        other,
        core.selected.reward_lower,
        core.unrestricted_reward_upper,
        core.selected.failure_upper,
        core.normalized_regret_upper,
        counterfactual,
        frontier,
    )


def solve_ground_direct_robust_h2_v1(
    model: PartialSupportIntervalModelV1,
    threshold: RobustThresholdProfileV1,
) -> RobustPlanAuditV1:
    """Enumerate and robustly audit deterministic ground H2 policies."""

    return _make_audit(
        model,
        threshold,
        RobustSolverKind.GROUND_DIRECT,
    )


def solve_quotient_robust_h2_v1(
    model: PartialSupportIntervalModelV1,
    threshold: RobustThresholdProfileV1,
) -> RobustPlanAuditV1:
    """Plan on supplied coordinate cells with fixed distinct concretizers."""

    if not model.concretizer_entries:
        raise PartialSupportRobustPlannerInvariantViolation(
            "quotient robust planning requires frozen concretizer entries"
        )
    return _make_audit(model, threshold, RobustSolverKind.QUOTIENT)


def verify_robust_plan_audit_v1(
    model: PartialSupportIntervalModelV1,
    threshold: RobustThresholdProfileV1,
    claimed: RobustPlanAuditV1,
) -> RobustAuditVerificationV1:
    """Same-implementation semantic replay of the complete robust audit."""

    if type(claimed) is not RobustPlanAuditV1:
        raise PartialSupportRobustPlannerInvariantViolation(
            "claimed robust audit has the wrong type"
        )
    replayed = (
        solve_ground_direct_robust_h2_v1(model, threshold)
        if claimed.solver_kind is RobustSolverKind.GROUND_DIRECT
        else solve_quotient_robust_h2_v1(model, threshold)
    )
    if replayed != claimed or replayed.audit_id != claimed.audit_id:
        raise PartialSupportRobustPlannerInvariantViolation(
            "claimed robust audit differs from complete semantic replay"
        )
    return RobustAuditVerificationV1(
        claimed.audit_id,
        replayed.audit_id,
        model.model_id,
        claimed.solver_kind,
    )


# Public semantic name retained for the confidence-authority integration.
IntervalSimplexDestinationV1 = RegisteredDestinationV1


__all__ = [
    "CONTRACT_VERSION",
    "CounterfactualStatus",
    "DestinationCategory",
    "DistinctActionConcretizerEntryV1",
    "FailedFrontierReason",
    "FailedProofFrontierV1",
    "HORIZON",
    "IntervalDestinationMassV1",
    "IntervalSimplexDestinationV1",
    "IntervalSimplexRowV1",
    "MAX_POLICY_ASSIGNMENTS",
    "NORMALIZED_REGRET_TOLERANCE",
    "OtherMassProvenanceV1",
    "OtherOnlyCounterfactualV1",
    "PROFILE_KEY",
    "PartialSupportIntervalModelV1",
    "PartialSupportRobustPlannerInvariantViolation",
    "PolicyScope",
    "RegisteredDestinationV1",
    "RobustAuditStatus",
    "RobustAuditVerificationV1",
    "RobustPlanAuditV1",
    "RobustPolicyAssignmentV1",
    "RobustSelectedRowBoundV1",
    "RobustSolverKind",
    "RobustThresholdProfileV1",
    "SCHEMA_VERSION",
    "SelectedRowCategory",
    "SelectedRowProvenanceV1",
    "StateActionCatalogueV1",
    "CatalogueActionV1",
    "build_partial_support_model_v1",
    "solve_ground_direct_robust_h2_v1",
    "solve_quotient_robust_h2_v1",
    "verify_robust_plan_audit_v1",
]
