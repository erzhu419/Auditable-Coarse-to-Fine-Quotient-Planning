"""Executable, law-free route-native common core for V0-075.

This module is the deepest backend stage that can currently be executed from
the canonical occurrence-worker request alone.  It performs:

* strict request/capability reconstruction through the registered worker;
* five-arm route and proposal separation;
* SOURCE forward-midrank and registered WRONG reverse-midrank binding;
* exact discovery/validation separation;
* exact-grid time-uniform Bernoulli confidence calculations;
* V0-075-domain statistical row/model artifacts;
* route-native work accounting; and
* deterministic policy/envelope/total-lift *candidate-input* blockers.

The last three artifacts are deliberately nonauthorizing.  A worker
capability projection carries row/stream IDs but not the complete typed public
support-chain and catalogue graph required by
``v075_total_lift_authority_v1``.  Moreover, no V0-075 quotient compiler or
matched-direct robust solver binding is frozen yet.  This core therefore does
not invent those bindings, import a V0-072 target authority, or claim a plan
certificate.

No target observer, kernel, transition law, reveal, salt, signer, callback,
cache, or resume surface is accepted here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp.sequential_bernoulli_acquisition_v1 import (
    METHOD_ID as EXACT_BERNOULLI_METHOD_ID,
    SequentialBernoulliProfileV1,
    build_anytime_bernoulli_checkpoint_v1,
)
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp import v075_public_graph_semantics_v1 as public_graph
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_route_native_backend_common_core_v1"
PRODUCTION_BACKEND_READY = False

ROW_EPOCH_BETA = Fraction(1, 300_000)
TARGET_HALF_WIDTH = Fraction(1, 64)
BOUNDARY_GRID_BITS = 16
MAX_SUPPORT_OUTCOMES = 16

SOURCE_FORWARD_MIDRANK = (
    Fraction(1, 6),
    Fraction(19, 36),
    Fraction(1),
)
REGISTERED_WRONG_REVERSED_MIDRANK = tuple(
    reversed(SOURCE_FORWARD_MIDRANK)
)

DOMAIN_TAGS = {
    "schedule": "acfqp:v075-route-native-schedule:v1",
    "schedule_semantics": "acfqp:v075-route-native-schedule-semantics:v1",
    "proposal": "acfqp:v075-route-native-proposal-basis:v1",
    "outcome": "acfqp:v075-route-native-outcome-descriptor:v1",
    "interval": "acfqp:v075-route-native-event-interval:v1",
    "row": "acfqp:v075-route-native-statistical-row:v1",
    "model": "acfqp:v075-route-native-statistical-model:v1",
    "policy": "acfqp:v075-route-native-policy-candidate:v1",
    "envelope": "acfqp:v075-route-native-envelope-candidate:v1",
    "total_lift_input": (
        "acfqp:v075-route-native-total-lift-candidate-input:v1"
    ),
    "counter": "acfqp:v075-route-native-backend-counter:v1",
    "work": "acfqp:v075-route-native-backend-work:v1",
    "result": "acfqp:v075-route-native-backend-result:v1",
}

if (
    len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values()))
    or any(not value.startswith("acfqp:v075-") for value in DOMAIN_TAGS.values())
):
    raise RuntimeError("V0-075 route-native backend domains must be unique")


class V075RouteNativeBackendInvariantViolation(ValueError):
    """A capability, schedule, model, proposal, or work invariant failed."""


def _fail(message: str) -> None:
    raise V075RouteNativeBackendInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075RouteNativeBackendInvariantViolation(str(error)) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075RouteNativeBackendInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("backend arithmetic must use exact Fraction")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _strict_load(raw: bytes, *, field_name: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{field_name} must be nonempty canonical bytes")
    try:
        document = loads_canonical_json(raw)
        if type(document) is not dict or canonical_json_bytes(document) != raw:
            _fail(f"{field_name} is not one canonical object")
        return document
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075RouteNativeBackendInvariantViolation(
            f"{field_name} is invalid: {error}"
        ) from error


class V075BackendScheduleStatusV1(str, Enum):
    COMPLETE_REGISTERED_CHECKPOINT = "COMPLETE_REGISTERED_CHECKPOINT"
    PREFIX_BEFORE_REGISTERED_CHECKPOINT = (
        "PREFIX_BEFORE_REGISTERED_CHECKPOINT"
    )
    INVALID_OR_OVER_CAP = "INVALID_OR_OVER_CAP"


class V075BackendCandidateStatusV1(str, Enum):
    NOT_READY_NO_VALIDATION = "NOT_READY_NO_VALIDATION"
    NOT_READY_INCOMPLETE_ACTION_CATALOGUE = (
        "NOT_READY_INCOMPLETE_ACTION_CATALOGUE"
    )
    NOT_READY_TYPED_SUPPORT_GRAPH_BINDER = (
        "NOT_READY_TYPED_SUPPORT_GRAPH_BINDER"
    )
    NOT_READY_V075_QUOTIENT_COMPILER = (
        "NOT_READY_V075_QUOTIENT_COMPILER"
    )
    NOT_READY_V075_DIRECT_ROBUST_SOLVER = (
        "NOT_READY_V075_DIRECT_ROBUST_SOLVER"
    )


def _schedule_profile_payload(
    route: worker.V075WorkerRouteV1,
    caps: worker.V075WorkerCapProfileV1,
) -> dict[str, Any]:
    adaptive = route is worker.V075WorkerRouteV1.ADAPTIVE_QUOTIENT
    return {
        "schema": "acfqp.v075_route_native_schedule_semantics.v1",
        "schema_version": SCHEMA_VERSION,
        "route": route.value,
        "discovery_checkpoints": [
            caps.initial_discovery_draws_per_row
        ],
        "validation_checkpoints": (
            [caps.initial_validation_draws_per_row]
            if adaptive
            else list(caps.direct_validation_checkpoints)
        ),
        "maximum_adaptive_rounds": (
            caps.maximum_adaptive_rounds if adaptive else 0
        ),
        "maximum_incremental_draws": (
            caps.maximum_incremental_draws_per_adaptive_arm
            if adaptive
            else 0
        ),
        "new_child_discovery_draws_per_row": (
            caps.new_child_discovery_draws_per_row if adaptive else 0
        ),
        "new_child_validation_draws_per_row": (
            caps.new_child_validation_draws_per_row if adaptive else 0
        ),
        "checkpoint_alpha_spending": False,
    }


@dataclass(frozen=True, slots=True)
class V075RouteScheduleV1:
    request_id: str
    arm: worker.V075WorkerArmV1
    route: worker.V075WorkerRouteV1
    discovery_stream_counts: tuple[tuple[str, int], ...]
    validation_stream_counts: tuple[tuple[str, int], ...]
    status: V075BackendScheduleStatusV1
    cap_profile_id: str

    def __post_init__(self) -> None:
        _cid(self.request_id, "route schedule request")
        _cid(self.cap_profile_id, "route schedule cap profile")
        if (
            type(self.arm) is not worker.V075WorkerArmV1
            or type(self.route) is not worker.V075WorkerRouteV1
            or type(self.status) is not V075BackendScheduleStatusV1
            or type(self.discovery_stream_counts) is not tuple
            or type(self.validation_stream_counts) is not tuple
        ):
            _fail("route schedule is malformed")
        for values in (
            self.discovery_stream_counts,
            self.validation_stream_counts,
        ):
            if (
                values != tuple(sorted(values))
                or any(
                    type(stream_id) is not str
                    or type(count) is not int
                    or count <= 0
                    for stream_id, count in values
                )
            ):
                _fail("route schedule stream counts are noncanonical")
            for stream_id, _count in values:
                _cid(stream_id, "route schedule stream")
        if (
            self.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
        ) != (
            self.route is worker.V075WorkerRouteV1.MATCHED_DIRECT_GROUND
        ):
            _fail("route schedule arm and route disagree")

    @property
    def schedule_semantics_id(self) -> str:
        return _hash(
            "schedule_semantics",
            _schedule_profile_payload(
                self.route,
                worker.V075WorkerCapProfileV1(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_route_native_schedule.v1",
            "schema_version": SCHEMA_VERSION,
            "request_id": self.request_id,
            "arm": self.arm.value,
            "route": self.route.value,
            "schedule_semantics_id": self.schedule_semantics_id,
            "discovery_stream_counts": [
                {"stream_id": stream_id, "draw_count": count}
                for stream_id, count in self.discovery_stream_counts
            ],
            "validation_stream_counts": [
                {"stream_id": stream_id, "draw_count": count}
                for stream_id, count in self.validation_stream_counts
            ],
            "status": self.status.value,
            "cap_profile_id": self.cap_profile_id,
            "common_random_numbers_reduce_charged_work": False,
        }

    @property
    def schedule_id(self) -> str:
        return _hash("schedule", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "schedule_id": self.schedule_id}


@dataclass(frozen=True, slots=True)
class V075ProposalBasisV1:
    request_id: str
    arm: worker.V075WorkerArmV1
    semantics: worker.V075WorkerProposalSemanticsV1
    exact_midrank_vector: tuple[Fraction, ...]
    source_transport_id: str | None
    target_feature_binding_available: bool = False

    def __post_init__(self) -> None:
        _cid(self.request_id, "proposal request")
        if (
            type(self.arm) is not worker.V075WorkerArmV1
            or type(self.semantics)
            is not worker.V075WorkerProposalSemanticsV1
            or type(self.exact_midrank_vector) is not tuple
            or any(type(item) is not Fraction for item in self.exact_midrank_vector)
            or self.target_feature_binding_available is not False
        ):
            _fail("proposal basis is malformed")
        expected: tuple[Fraction, ...]
        if self.arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR:
            expected = SOURCE_FORWARD_MIDRANK
            if self.source_transport_id is None:
                _fail("SOURCE proposal lacks verified transport")
            _cid(self.source_transport_id, "SOURCE proposal transport")
        elif self.arm is worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR:
            expected = REGISTERED_WRONG_REVERSED_MIDRANK
            if self.source_transport_id is not None:
                _fail("WRONG proposal illegally consumed source payload")
        else:
            expected = ()
            if self.source_transport_id is not None:
                _fail("non-SOURCE proposal illegally consumed source payload")
        if self.exact_midrank_vector != expected:
            _fail("proposal midrank vector changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_route_native_proposal_basis.v1",
            "schema_version": SCHEMA_VERSION,
            "request_id": self.request_id,
            "arm": self.arm.value,
            "proposal_semantics": self.semantics.value,
            "exact_midrank_vector": [
                _fdoc(item) for item in self.exact_midrank_vector
            ],
            "source_transport_id": self.source_transport_id,
            "source_payload_consumed": (
                self.arm
                is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
            ),
            "neutral_schedule": self.arm
            in {
                worker.V075WorkerArmV1.NO_PRIOR,
                worker.V075WorkerArmV1.OOD_ABSTENTION,
            },
            "ood_abstains_exactly_to_no_prior": (
                self.arm is worker.V075WorkerArmV1.OOD_ABSTENTION
            ),
            "target_feature_binding_available": False,
            "proposal_applied_to_target_rows": False,
            "may_certify": False,
        }

    @property
    def proposal_id(self) -> str:
        return _hash("proposal", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proposal_id": self.proposal_id}


@dataclass(frozen=True, slots=True)
class V075OutcomeDescriptorV1:
    context_id: str
    next_state_id: str
    next_ranks: tuple[int, ...]
    failure: bool
    terminal: bool
    realized_row_reward: Fraction

    def __post_init__(self) -> None:
        _cid(self.context_id, "outcome context")
        _cid(self.next_state_id, "outcome next state")
        if (
            type(self.next_ranks) is not tuple
            or not self.next_ranks
            or any(type(item) is not int or not 0 <= item <= 6
                   for item in self.next_ranks)
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
            or (self.failure and not self.terminal)
            or type(self.realized_row_reward) is not Fraction
            or self.realized_row_reward < 0
        ):
            _fail("outcome descriptor is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_route_native_outcome_descriptor.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "next_state_id": self.next_state_id,
            "next_ranks": list(self.next_ranks),
            "failure": self.failure,
            "terminal": self.terminal,
            "realized_row_reward": _fdoc(self.realized_row_reward),
            "spawn_identity_discarded_after_state_projection": True,
        }

    @property
    def descriptor_id(self) -> str:
        return _hash("outcome", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "descriptor_id": self.descriptor_id}


@dataclass(frozen=True, slots=True)
class V075EventIntervalV1:
    event_key: str
    descriptor: V075OutcomeDescriptorV1 | None
    draw_count: int
    success_count: int
    empirical_probability: Fraction
    lower_probability: Fraction
    upper_probability: Fraction
    exact_likelihood_comparisons: int
    log_search_evaluations: int

    def __post_init__(self) -> None:
        if self.event_key == "OTHER":
            if self.descriptor is not None:
                _fail("OTHER interval cannot carry a descriptor")
        elif (
            type(self.descriptor) is not V075OutcomeDescriptorV1
            or self.event_key != self.descriptor.descriptor_id
        ):
            _fail("event interval descriptor binding changed")
        if (
            type(self.draw_count) is not int
            or self.draw_count <= 0
            or type(self.success_count) is not int
            or not 0 <= self.success_count <= self.draw_count
            or self.empirical_probability
            != Fraction(self.success_count, self.draw_count)
            or not 0 <= self.lower_probability <= self.empirical_probability
            or not self.empirical_probability <= self.upper_probability <= 1
            or type(self.exact_likelihood_comparisons) is not int
            or self.exact_likelihood_comparisons < 0
            or type(self.log_search_evaluations) is not int
            or self.log_search_evaluations < 0
        ):
            _fail("event confidence interval is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_route_native_event_interval.v1",
            "schema_version": SCHEMA_VERSION,
            "event_key": self.event_key,
            "descriptor_id": (
                None if self.descriptor is None else self.descriptor.descriptor_id
            ),
            "draw_count": self.draw_count,
            "success_count": self.success_count,
            "empirical_probability": _fdoc(self.empirical_probability),
            "lower_probability": _fdoc(self.lower_probability),
            "upper_probability": _fdoc(self.upper_probability),
            "exact_likelihood_comparisons": (
                self.exact_likelihood_comparisons
            ),
            "log_search_evaluations": self.log_search_evaluations,
            "method_id": EXACT_BERNOULLI_METHOD_ID,
        }

    @property
    def interval_id(self) -> str:
        return _hash("interval", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "interval_id": self.interval_id}


@dataclass(frozen=True, slots=True)
class V075StatisticalRowV1:
    context_id: str
    row_binding_id: str
    source_state_id: str
    remaining_horizon: int
    action: tuple[int, int, int]
    discovery_capability_ids: tuple[str, ...]
    validation_capability_ids: tuple[str, ...]
    support: tuple[V075OutcomeDescriptorV1, ...]
    intervals: tuple[V075EventIntervalV1, ...]
    validation_epoch_index: int | None
    blocker: str | None

    def __post_init__(self) -> None:
        for value, name in (
            (self.context_id, "statistical row context"),
            (self.row_binding_id, "statistical row binding"),
            (self.source_state_id, "statistical row source state"),
        ):
            _cid(value, name)
        if (
            self.remaining_horizon not in (1, 2)
            or type(self.action) is not tuple
            or len(self.action) != 3
            or any(type(item) is not int for item in self.action)
            or self.action[0] >= self.action[1]
            or self.action[2] not in self.action[:2]
            or type(self.discovery_capability_ids) is not tuple
            or type(self.validation_capability_ids) is not tuple
            or type(self.support) is not tuple
            or type(self.intervals) is not tuple
        ):
            _fail("statistical row is malformed")
        for item in (
            *self.discovery_capability_ids,
            *self.validation_capability_ids,
        ):
            _cid(item, "statistical row capability")
        if (
            len(set(self.discovery_capability_ids))
            != len(self.discovery_capability_ids)
            or len(set(self.validation_capability_ids))
            != len(self.validation_capability_ids)
            or tuple(item.descriptor_id for item in self.support)
            != tuple(sorted({item.descriptor_id for item in self.support}))
            or len(self.support) > MAX_SUPPORT_OUTCOMES
        ):
            _fail("statistical row support or capabilities are noncanonical")
        if self.validation_capability_ids:
            if (
                type(self.validation_epoch_index) is not int
                or self.validation_epoch_index <= 0
                or len(self.intervals) != len(self.support) + 1
                or tuple(item.event_key for item in self.intervals)
                != tuple(item.descriptor_id for item in self.support)
                + ("OTHER",)
            ):
                _fail("validated statistical row lacks support-plus-OTHER")
        elif (
            self.validation_epoch_index is not None
            or self.intervals
            or self.blocker != "VALIDATION_CAPABILITIES_NOT_AVAILABLE"
        ):
            _fail("discovery-only row must remain nonstatistical")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_route_native_statistical_row.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "row_binding_id": self.row_binding_id,
            "source_state_id": self.source_state_id,
            "remaining_horizon": self.remaining_horizon,
            "action": list(self.action),
            "discovery_capability_ids": list(
                self.discovery_capability_ids
            ),
            "validation_capability_ids": list(
                self.validation_capability_ids
            ),
            "support_descriptor_ids": [
                item.descriptor_id for item in self.support
            ],
            "interval_ids": [item.interval_id for item in self.intervals],
            "validation_epoch_index": self.validation_epoch_index,
            "blocker": self.blocker,
            "support_from_complete_signed_discovery_prefix": True,
            "validation_counts_exclude_discovery": True,
            "one_other_event": bool(self.intervals),
            "typed_public_support_graph_replayed": False,
        }

    @property
    def row_id(self) -> str:
        return _hash("row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "support": [item.to_document() for item in self.support],
            "intervals": [item.to_document() for item in self.intervals],
            "row_id": self.row_id,
        }


@dataclass(frozen=True, slots=True)
class V075StatisticalModelV1:
    request_id: str
    occurrence_id: str
    arm: worker.V075WorkerArmV1
    proposal_id: str
    schedule_id: str
    rows: tuple[V075StatisticalRowV1, ...]
    root_catalogue_complete: bool
    modeled_child_catalogues_complete: bool
    unresolved_source_state_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, name in (
            (self.request_id, "model request"),
            (self.occurrence_id, "model occurrence"),
            (self.proposal_id, "model proposal"),
            (self.schedule_id, "model schedule"),
        ):
            _cid(value, name)
        if (
            type(self.arm) is not worker.V075WorkerArmV1
            or type(self.rows) is not tuple
            or not self.rows
            or tuple(item.row_id for item in self.rows)
            != tuple(sorted({item.row_id for item in self.rows}))
            or type(self.root_catalogue_complete) is not bool
            or type(self.modeled_child_catalogues_complete) is not bool
            or self.unresolved_source_state_ids
            != tuple(sorted(set(self.unresolved_source_state_ids)))
        ):
            _fail("statistical model is malformed")
        for value in self.unresolved_source_state_ids:
            _cid(value, "unresolved source state")

    @property
    def has_validation(self) -> bool:
        return all(item.validation_capability_ids for item in self.rows)

    @property
    def action_catalogues_complete(self) -> bool:
        return (
            self.root_catalogue_complete
            and self.modeled_child_catalogues_complete
            and not self.unresolved_source_state_ids
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_route_native_statistical_model.v1",
            "schema_version": SCHEMA_VERSION,
            "request_id": self.request_id,
            "occurrence_id": self.occurrence_id,
            "arm": self.arm.value,
            "proposal_id": self.proposal_id,
            "schedule_id": self.schedule_id,
            "row_ids": [item.row_id for item in self.rows],
            "root_catalogue_complete": self.root_catalogue_complete,
            "modeled_child_catalogues_complete": (
                self.modeled_child_catalogues_complete
            ),
            "unresolved_source_state_ids": list(
                self.unresolved_source_state_ids
            ),
            "has_validation": self.has_validation,
            "action_catalogues_complete": self.action_catalogues_complete,
            "transition_law_access": False,
            "exact_atoms_in_model": False,
            "typed_public_support_graph_replayed": False,
            "may_certify": False,
        }

    @property
    def model_id(self) -> str:
        return _hash("model", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "rows": [item.to_document() for item in self.rows],
            "model_id": self.model_id,
        }


def _candidate_status(
    model: V075StatisticalModelV1,
    arm: worker.V075WorkerArmV1,
) -> V075BackendCandidateStatusV1:
    if not model.has_validation:
        return V075BackendCandidateStatusV1.NOT_READY_NO_VALIDATION
    if not model.action_catalogues_complete:
        return (
            V075BackendCandidateStatusV1
            .NOT_READY_INCOMPLETE_ACTION_CATALOGUE
        )
    # Even a complete ID-level inventory lacks the typed support-chain graph
    # stripped by the process-safe capability projection.
    if any(
        not row.to_document()["typed_public_support_graph_replayed"]
        for row in model.rows
    ):
        return (
            V075BackendCandidateStatusV1
            .NOT_READY_TYPED_SUPPORT_GRAPH_BINDER
        )
    if arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND:
        return (
            V075BackendCandidateStatusV1
            .NOT_READY_V075_DIRECT_ROBUST_SOLVER
        )
    return (
        V075BackendCandidateStatusV1
        .NOT_READY_V075_QUOTIENT_COMPILER
    )


@dataclass(frozen=True, slots=True)
class V075PolicyCandidateV1:
    model_id: str
    arm: worker.V075WorkerArmV1
    status: V075BackendCandidateStatusV1
    candidate_root_row_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _cid(self.model_id, "policy candidate model")
        if (
            type(self.arm) is not worker.V075WorkerArmV1
            or type(self.status) is not V075BackendCandidateStatusV1
            or self.candidate_root_row_ids
            != tuple(sorted(set(self.candidate_root_row_ids)))
        ):
            _fail("policy candidate is malformed")
        for item in self.candidate_root_row_ids:
            _cid(item, "policy candidate root row")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_route_native_policy_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "model_id": self.model_id,
            "arm": self.arm.value,
            "status": self.status.value,
            "candidate_root_row_ids": list(self.candidate_root_row_ids),
            "selected_root_row_id": None,
            "selected_child_decisions": [],
            "deterministic_policy_selected": False,
            "may_certify": False,
        }

    @property
    def policy_candidate_id(self) -> str:
        return _hash("policy", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "policy_candidate_id": self.policy_candidate_id,
        }


@dataclass(frozen=True, slots=True)
class V075EnvelopeCandidateV1:
    model_id: str
    policy_candidate_id: str
    status: V075BackendCandidateStatusV1

    def __post_init__(self) -> None:
        _cid(self.model_id, "envelope model")
        _cid(self.policy_candidate_id, "envelope policy candidate")
        if type(self.status) is not V075BackendCandidateStatusV1:
            _fail("envelope status is not typed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_route_native_envelope_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "model_id": self.model_id,
            "policy_candidate_id": self.policy_candidate_id,
            "status": self.status.value,
            "selected_reward_lower": None,
            "unrestricted_reward_upper": None,
            "selected_failure_upper": None,
            "normalized_regret_upper": None,
            "statistical_envelope_ready": False,
            "may_certify": False,
        }

    @property
    def envelope_candidate_id(self) -> str:
        return _hash("envelope", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "envelope_candidate_id": self.envelope_candidate_id,
        }


@dataclass(frozen=True, slots=True)
class V075TotalLiftCandidateInputV1:
    occurrence_id: str
    model_id: str
    policy_candidate_id: str
    envelope_candidate_id: str
    status: V075BackendCandidateStatusV1
    observed_row_ids: tuple[str, ...]
    capability_ref_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, name in (
            (self.occurrence_id, "total-lift occurrence"),
            (self.model_id, "total-lift model candidate"),
            (self.policy_candidate_id, "total-lift policy candidate"),
            (self.envelope_candidate_id, "total-lift envelope candidate"),
        ):
            _cid(value, name)
        if (
            type(self.status) is not V075BackendCandidateStatusV1
            or self.observed_row_ids
            != tuple(sorted(set(self.observed_row_ids)))
            or len(set(self.capability_ref_ids))
            != len(self.capability_ref_ids)
        ):
            _fail("total-lift candidate input is malformed")
        for item in (*self.observed_row_ids, *self.capability_ref_ids):
            _cid(item, "total-lift candidate input member")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_route_native_total_lift_candidate_input.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "model_id": self.model_id,
            "policy_candidate_id": self.policy_candidate_id,
            "envelope_candidate_id": self.envelope_candidate_id,
            "status": self.status.value,
            "observed_row_ids": list(self.observed_row_ids),
            "capability_ref_ids": list(self.capability_ref_ids),
            "typed_occurrence_binding_required": True,
            "typed_row_and_catalogue_graph_required": True,
            "typed_signed_capability_objects_required": True,
            "ready_for_total_lift_evaluation": False,
            "exact_atom_access": False,
        }

    @property
    def total_lift_input_id(self) -> str:
        return _hash("total_lift_input", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "total_lift_input_id": self.total_lift_input_id,
        }


COUNTER_PATHS = (
    "common.request_reconstructions",
    "common.capability_refs_consumed",
    "common.discovery_capabilities_consumed",
    "common.validation_capabilities_consumed",
    "common.outcome_projections",
    "common.schedule_checks",
    "common.confidence_event_evaluations",
    "common.exact_likelihood_comparisons",
    "common.log_search_evaluations",
    "common.statistical_rows_built",
    "source.adapter_payload_reads",
    "source.proposal_entries_bound",
    "adaptive.route_attempts",
    "adaptive.source_proposal_attempts",
    "adaptive.no_prior_attempts",
    "adaptive.wrong_prior_attempts",
    "adaptive.ood_abstention_attempts",
    "direct.route_attempts",
    "adaptive.model_rows",
    "direct.model_rows",
    "adaptive.policy_solver_calls",
    "direct.policy_solver_calls",
    "common.total_lift_bind_attempts",
)


@dataclass(frozen=True, slots=True)
class V075BackendCounterV1:
    path: str
    value: int
    observed: bool = True

    def __post_init__(self) -> None:
        if (
            self.path not in COUNTER_PATHS
            or type(self.value) is not int
            or self.value < 0
            or self.observed is not True
        ):
            _fail("backend counter is unknown or malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_route_native_backend_counter.v1",
            "schema_version": SCHEMA_VERSION,
            "path": self.path,
            "value": self.value,
            "observed": True,
            "lane": "OPERATIONAL_CONSTRUCTION",
        }

    @property
    def counter_id(self) -> str:
        return _hash("counter", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counter_id": self.counter_id}


@dataclass(frozen=True, slots=True)
class V075BackendWorkV1:
    request_id: str
    arm: worker.V075WorkerArmV1
    counters: tuple[V075BackendCounterV1, ...]

    def __post_init__(self) -> None:
        _cid(self.request_id, "backend work request")
        if (
            type(self.arm) is not worker.V075WorkerArmV1
            or type(self.counters) is not tuple
            or tuple(item.path for item in self.counters) != COUNTER_PATHS
        ):
            _fail("backend work counters are incomplete or reordered")
        values = {item.path: item.value for item in self.counters}
        adaptive = self.arm is not worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
        expected_arms = tuple(
            int(self.arm is item) for item in tuple(worker.V075WorkerArmV1)[:4]
        )
        if (
            values["adaptive.route_attempts"] != int(adaptive)
            or values["direct.route_attempts"] != int(not adaptive)
            or (
                values["adaptive.source_proposal_attempts"],
                values["adaptive.no_prior_attempts"],
                values["adaptive.wrong_prior_attempts"],
                values["adaptive.ood_abstention_attempts"],
            )
            != expected_arms
            or (
                adaptive
                and (
                    values["direct.model_rows"] != 0
                    or values["direct.policy_solver_calls"] != 0
                )
            )
            or (
                not adaptive
                and (
                    values["adaptive.model_rows"] != 0
                    or values["adaptive.policy_solver_calls"] != 0
                )
            )
        ):
            _fail("backend route-native work lanes are mixed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_route_native_backend_work.v1",
            "schema_version": SCHEMA_VERSION,
            "request_id": self.request_id,
            "arm": self.arm.value,
            "counter_ids": [item.counter_id for item in self.counters],
            "required_counter_paths": list(COUNTER_PATHS),
            "native_zeros_complete": True,
            "route_lanes_disjoint": True,
        }

    @property
    def work_id(self) -> str:
        return _hash("work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "counters": [item.to_document() for item in self.counters],
            "work_id": self.work_id,
        }


@dataclass(frozen=True, slots=True)
class V075RouteNativeBackendResultV1:
    request_id: str
    occurrence_id: str
    arm: worker.V075WorkerArmV1
    schedule: V075RouteScheduleV1
    proposal: V075ProposalBasisV1
    model: V075StatisticalModelV1
    policy: V075PolicyCandidateV1
    envelope: V075EnvelopeCandidateV1
    total_lift_input: V075TotalLiftCandidateInputV1
    work: V075BackendWorkV1

    def __post_init__(self) -> None:
        for value, name in (
            (self.request_id, "backend result request"),
            (self.occurrence_id, "backend result occurrence"),
        ):
            _cid(value, name)
        if (
            type(self.arm) is not worker.V075WorkerArmV1
            or self.schedule.request_id != self.request_id
            or self.proposal.request_id != self.request_id
            or self.model.request_id != self.request_id
            or self.model.occurrence_id != self.occurrence_id
            or self.model.arm is not self.arm
            or self.policy.model_id != self.model.model_id
            or self.envelope.model_id != self.model.model_id
            or self.envelope.policy_candidate_id
            != self.policy.policy_candidate_id
            or self.total_lift_input.model_id != self.model.model_id
            or self.total_lift_input.policy_candidate_id
            != self.policy.policy_candidate_id
            or self.total_lift_input.envelope_candidate_id
            != self.envelope.envelope_candidate_id
            or self.work.request_id != self.request_id
            or self.work.arm is not self.arm
        ):
            _fail("backend result identity graph is inconsistent")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_route_native_backend_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "request_id": self.request_id,
            "occurrence_id": self.occurrence_id,
            "arm": self.arm.value,
            "schedule_id": self.schedule.schedule_id,
            "proposal_id": self.proposal.proposal_id,
            "model_id": self.model.model_id,
            "policy_candidate_id": self.policy.policy_candidate_id,
            "envelope_candidate_id": self.envelope.envelope_candidate_id,
            "total_lift_input_id": (
                self.total_lift_input.total_lift_input_id
            ),
            "work_id": self.work.work_id,
            "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "terminal_code": "ROUTE_BACKEND_BINDINGS_NOT_READY",
            "production_backend_ready": False,
            "target_accessed": False,
            "scientific_result": False,
        }

    @property
    def result_id(self) -> str:
        return _hash("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "schedule": self.schedule.to_document(),
            "proposal": self.proposal.to_document(),
            "model": self.model.to_document(),
            "policy": self.policy.to_document(),
            "envelope": self.envelope.to_document(),
            "total_lift_input": self.total_lift_input.to_document(),
            "work": self.work.to_document(),
            "result_id": self.result_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _capability_documents(
    request: Mapping[str, Any],
) -> tuple[tuple[str, dict[str, Any]], ...]:
    result: list[tuple[str, dict[str, Any]]] = []
    for ref in request["capability_refs"]:
        try:
            raw = bytes.fromhex(ref["capability_bytes_hex"])
        except (TypeError, ValueError) as error:
            raise V075RouteNativeBackendInvariantViolation(
                "capability bytes are not hexadecimal"
            ) from error
        document = _strict_load(raw, field_name="signed capability")
        if document["capability_id"] != ref["capability_id"]:
            _fail("capability projection differs from worker verification")
        result.append((ref["ref_id"], document))
    return tuple(result)


def _registered_context(
    context_id: str,
) -> public_authority.V075PublicReplicateContextV1:
    _cid(context_id, "backend context")
    matches = tuple(
        item
        for item in (
            public_authority.freeze_v075_public_family_generation_v1()
            .replicate_contexts
        )
        if item.context_id == context_id
    )
    if len(matches) != 1:
        _fail("backend context is not one registered public context")
    return matches[0]


def _outcome(
    context: public_authority.V075PublicReplicateContextV1,
    capability: Mapping[str, Any],
) -> V075OutcomeDescriptorV1:
    try:
        state = public_graph.V075SymbolicGraphStateV1(
            context,
            tuple(capability["next_ranks"]),
            capability["failure"],
        )
    except public_graph.V075PublicGraphSemanticsInvariantViolation as error:
        raise V075RouteNativeBackendInvariantViolation(str(error)) from error
    return V075OutcomeDescriptorV1(
        context.context_id,
        state.state_id,
        state.ranks,
        capability["failure"],
        capability["terminal"],
        capability["realized_row_reward"],
    )


def _proposal(
    request: Mapping[str, Any],
    arm: worker.V075WorkerArmV1,
    registration: worker.V075WorkerArmRegistrationV1,
) -> V075ProposalBasisV1:
    transport = request["source_prior_transport"]
    vector: tuple[Fraction, ...]
    transport_id: str | None
    if arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR:
        if type(transport) is not dict:
            _fail("SOURCE backend lacks verified source transport")
        adapter = _strict_load(
            bytes.fromhex(transport["adapter_bytes_hex"]),
            field_name="source-prior adapter",
        )
        try:
            entries = adapter["catalogue"]["entries"]
            vector = tuple(
                item["exact_mean_midrank"] for item in entries
            )
        except (KeyError, TypeError) as error:
            raise V075RouteNativeBackendInvariantViolation(
                "SOURCE adapter catalogue is malformed"
            ) from error
        transport_id = transport["transport_id"]
    elif arm is worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR:
        if transport is not None:
            _fail("WRONG backend must not receive source transport")
        vector = REGISTERED_WRONG_REVERSED_MIDRANK
        transport_id = None
    else:
        if transport is not None:
            _fail("non-SOURCE backend must not receive source transport")
        vector = ()
        transport_id = None
    return V075ProposalBasisV1(
        request["request_id"],
        arm,
        registration.proposal_semantics,
        vector,
        transport_id,
    )


def _schedule(
    request: Mapping[str, Any],
    arm: worker.V075WorkerArmV1,
    route: worker.V075WorkerRouteV1,
    capabilities: tuple[tuple[str, dict[str, Any]], ...],
) -> V075RouteScheduleV1:
    counts: dict[tuple[str, str], int] = {}
    for _ref_id, item in capabilities:
        key = (item["lane"], item["stream_id"])
        counts[key] = counts.get(key, 0) + 1
    discovery = tuple(
        sorted(
            (stream, count)
            for (lane, stream), count in counts.items()
            if lane == "DISCOVERY"
        )
    )
    validation = tuple(
        sorted(
            (stream, count)
            for (lane, stream), count in counts.items()
            if lane == "VALIDATION"
        )
    )
    caps = worker.V075WorkerCapProfileV1()
    discovery_allowed = {
        caps.initial_discovery_draws_per_row,
        caps.new_child_discovery_draws_per_row,
    }
    validation_allowed = (
        {
            caps.initial_validation_draws_per_row,
            caps.new_child_validation_draws_per_row,
            caps.promotion_validation_draws_per_round,
        }
        if route is worker.V075WorkerRouteV1.ADAPTIVE_QUOTIENT
        else set(caps.direct_validation_checkpoints)
    )
    complete = (
        bool(discovery)
        and bool(validation)
        and all(count in discovery_allowed for _, count in discovery)
        and all(count in validation_allowed for _, count in validation)
    )
    maximum = (
        caps.maximum_incremental_draws_per_adaptive_arm
        if route is worker.V075WorkerRouteV1.ADAPTIVE_QUOTIENT
        else caps.direct_validation_checkpoints[-1]
        * max(1, len(validation))
        + caps.initial_discovery_draws_per_row
        * max(1, len(discovery))
    )
    total = sum(count for _, count in (*discovery, *validation))
    status = (
        V075BackendScheduleStatusV1.INVALID_OR_OVER_CAP
        if total > maximum
        else (
            V075BackendScheduleStatusV1.COMPLETE_REGISTERED_CHECKPOINT
            if complete
            else V075BackendScheduleStatusV1.PREFIX_BEFORE_REGISTERED_CHECKPOINT
        )
    )
    return V075RouteScheduleV1(
        request["request_id"],
        arm,
        route,
        discovery,
        validation,
        status,
        request["cap_profile_id"],
    )


def _intervals(
    *,
    support: tuple[V075OutcomeDescriptorV1, ...],
    validation: tuple[tuple[str, dict[str, Any]], ...],
    context: public_authority.V075PublicReplicateContextV1,
    checkpoints: tuple[int, ...],
) -> tuple[V075EventIntervalV1, ...]:
    by_id = {item.descriptor_id: item for item in support}
    counts = {item.descriptor_id: 0 for item in support}
    other = 0
    for _ref_id, capability in validation:
        descriptor = _outcome(context, capability)
        if descriptor.descriptor_id in counts:
            counts[descriptor.descriptor_id] += 1
        else:
            other += 1
    draw_count = len(validation)
    event_count = len(support) + 1
    profile = SequentialBernoulliProfileV1(
        confidence_alpha=ROW_EPOCH_BETA / event_count,
        target_half_width=TARGET_HALF_WIDTH,
        checkpoints=checkpoints,
        boundary_grid_bits=BOUNDARY_GRID_BITS,
    )
    result: list[V075EventIntervalV1] = []
    for event_key, count in (
        *((item.descriptor_id, counts[item.descriptor_id]) for item in support),
        ("OTHER", other),
    ):
        checkpoint = build_anytime_bernoulli_checkpoint_v1(
            draw_count,
            count,
            profile,
        )
        result.append(
            V075EventIntervalV1(
                event_key,
                None if event_key == "OTHER" else by_id[event_key],
                draw_count,
                count,
                checkpoint.empirical_probability,
                checkpoint.lower_probability,
                checkpoint.upper_probability,
                checkpoint.exact_likelihood_comparisons,
                checkpoint.log_search_evaluations,
            )
        )
    return tuple(result)


def _rows(
    request: Mapping[str, Any],
    capabilities: tuple[tuple[str, dict[str, Any]], ...],
    context: public_authority.V075PublicReplicateContextV1,
    route: worker.V075WorkerRouteV1,
) -> tuple[V075StatisticalRowV1, ...]:
    grouped: dict[
        str,
        dict[str, list[tuple[str, dict[str, Any]]]],
    ] = {}
    for ref_id, capability in capabilities:
        grouped.setdefault(
            capability["row_binding_id"],
            {"DISCOVERY": [], "VALIDATION": []},
        )[capability["lane"]].append((ref_id, capability))
    rows: list[V075StatisticalRowV1] = []
    caps = worker.V075WorkerCapProfileV1()
    checkpoints = (
        (
            caps.initial_validation_draws_per_row,
            caps.new_child_validation_draws_per_row,
        )
        if route is worker.V075WorkerRouteV1.ADAPTIVE_QUOTIENT
        else caps.direct_validation_checkpoints
    )
    for row_binding_id in sorted(grouped):
        lanes = grouped[row_binding_id]
        all_items = lanes["DISCOVERY"] + lanes["VALIDATION"]
        first = all_items[0][1]
        if any(
            (
                item["context_id"],
                item["source_state_id"],
                item["remaining_horizon"],
                tuple(item["action"]),
            )
            != (
                first["context_id"],
                first["source_state_id"],
                first["remaining_horizon"],
                tuple(first["action"]),
            )
            for _ref_id, item in all_items
        ):
            _fail("row capabilities disagree on public row semantics")
        discovery = tuple(
            sorted(
                lanes["DISCOVERY"],
                key=lambda item: (
                    item[1]["observer_epoch_index"],
                    item[1]["stream_id"],
                    item[1]["accepted_draw_index"],
                ),
            )
        )
        validation_all = tuple(
            sorted(
                lanes["VALIDATION"],
                key=lambda item: (
                    item[1]["observer_epoch_index"],
                    item[1]["stream_id"],
                    item[1]["accepted_draw_index"],
                ),
            )
        )
        support_by_id: dict[str, V075OutcomeDescriptorV1] = {}
        for _ref_id, item in discovery:
            descriptor = _outcome(context, item)
            support_by_id[descriptor.descriptor_id] = descriptor
        if len(support_by_id) > MAX_SUPPORT_OUTCOMES:
            _fail("discovery support exceeds the registered cap")
        support = tuple(
            support_by_id[key] for key in sorted(support_by_id)
        )
        validation_epoch: int | None = None
        selected_validation: tuple[
            tuple[str, dict[str, Any]], ...
        ] = ()
        if validation_all:
            validation_epoch = max(
                item["observer_epoch_index"]
                for _ref_id, item in validation_all
            )
            selected_validation = tuple(
                item
                for item in validation_all
                if item[1]["observer_epoch_index"] == validation_epoch
            )
            stream_ids = {
                item["stream_id"] for _ref_id, item in selected_validation
            }
            if len(stream_ids) != 1:
                _fail("one row/epoch has multiple validation streams")
            if not support:
                _fail("validation cannot precede signed discovery support")
        rows.append(
            V075StatisticalRowV1(
                context.context_id,
                row_binding_id,
                first["source_state_id"],
                first["remaining_horizon"],
                tuple(first["action"]),
                tuple(ref_id for ref_id, _item in discovery),
                tuple(ref_id for ref_id, _item in selected_validation),
                support,
                (
                    ()
                    if not selected_validation
                    else _intervals(
                        support=support,
                        validation=selected_validation,
                        context=context,
                        checkpoints=checkpoints,
                    )
                ),
                validation_epoch,
                (
                    "VALIDATION_CAPABILITIES_NOT_AVAILABLE"
                    if not selected_validation
                    else "TYPED_SUPPORT_GRAPH_REPLAY_NOT_AVAILABLE"
                ),
            )
        )
    return tuple(sorted(rows, key=lambda item: item.row_id))


def _catalogue_completeness(
    context: public_authority.V075PublicReplicateContextV1,
    rows: tuple[V075StatisticalRowV1, ...],
) -> tuple[bool, bool, tuple[str, ...]]:
    known_states = {
        public_graph.root_catalogue_v1(context).state.state_id:
        public_graph.root_catalogue_v1(context).state
    }
    for row in rows:
        for descriptor in row.support:
            try:
                state = public_graph.V075SymbolicGraphStateV1(
                    context,
                    descriptor.next_ranks,
                    descriptor.failure,
                )
            except public_graph.V075PublicGraphSemanticsInvariantViolation:
                continue
            known_states[state.state_id] = state
    rows_by_state: dict[str, set[tuple[int, int, int]]] = {}
    for row in rows:
        if row.validation_capability_ids:
            rows_by_state.setdefault(row.source_state_id, set()).add(row.action)
    unresolved = tuple(
        sorted(
            {
                row.source_state_id
                for row in rows
                if row.source_state_id not in known_states
            }
        )
    )
    root = public_graph.root_catalogue_v1(context)
    root_complete = rows_by_state.get(root.state.state_id, set()) == set(
        root.actions
    )
    child_state_ids = {
        descriptor.next_state_id
        for row in rows
        if row.remaining_horizon == 2
        for descriptor in row.support
        if not descriptor.terminal and not descriptor.failure
    }
    child_complete = True
    for state_id in child_state_ids:
        state = known_states.get(state_id)
        if state is None:
            child_complete = False
            continue
        catalogue = public_graph.V075LegalActionCatalogueV1(
            context,
            state,
            1,
            public_graph.legal_action_triples_v1(
                context,
                state.ranks,
                state.failure,
            ),
        )
        if rows_by_state.get(state_id, set()) != set(catalogue.actions):
            child_complete = False
    return root_complete, child_complete, unresolved


def _work(
    request: Mapping[str, Any],
    arm: worker.V075WorkerArmV1,
    capabilities: tuple[tuple[str, dict[str, Any]], ...],
    rows: tuple[V075StatisticalRowV1, ...],
) -> V075BackendWorkV1:
    discovery = sum(
        item["lane"] == "DISCOVERY" for _ref_id, item in capabilities
    )
    validation = len(capabilities) - discovery
    intervals = tuple(
        interval for row in rows for interval in row.intervals
    )
    adaptive = arm is not worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    values = {
        "common.request_reconstructions": 1,
        "common.capability_refs_consumed": len(capabilities),
        "common.discovery_capabilities_consumed": discovery,
        "common.validation_capabilities_consumed": validation,
        "common.outcome_projections": len(capabilities),
        "common.schedule_checks": 1,
        "common.confidence_event_evaluations": len(intervals),
        "common.exact_likelihood_comparisons": sum(
            item.exact_likelihood_comparisons for item in intervals
        ),
        "common.log_search_evaluations": sum(
            item.log_search_evaluations for item in intervals
        ),
        "common.statistical_rows_built": len(rows),
        "source.adapter_payload_reads": int(
            arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
        ),
        "source.proposal_entries_bound": (
            3 if arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR else 0
        ),
        "adaptive.route_attempts": int(adaptive),
        "adaptive.source_proposal_attempts": int(
            arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
        ),
        "adaptive.no_prior_attempts": int(
            arm is worker.V075WorkerArmV1.NO_PRIOR
        ),
        "adaptive.wrong_prior_attempts": int(
            arm is worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR
        ),
        "adaptive.ood_abstention_attempts": int(
            arm is worker.V075WorkerArmV1.OOD_ABSTENTION
        ),
        "direct.route_attempts": int(not adaptive),
        "adaptive.model_rows": len(rows) if adaptive else 0,
        "direct.model_rows": len(rows) if not adaptive else 0,
        "adaptive.policy_solver_calls": 0,
        "direct.policy_solver_calls": 0,
        "common.total_lift_bind_attempts": 0,
    }
    return V075BackendWorkV1(
        request["request_id"],
        arm,
        tuple(
            V075BackendCounterV1(path, values[path])
            for path in COUNTER_PATHS
        ),
    )


def execute_v075_route_native_backend_core_v1(
    request_bytes: bytes,
) -> V075RouteNativeBackendResultV1:
    """Execute the law-free statistical common core on canonical bytes."""

    try:
        request = worker.load_v075_registered_occurrence_worker_request_v1(
            request_bytes
        )
    except worker.V075RegisteredOccurrenceWorkerInvariantViolation as error:
        raise V075RouteNativeBackendInvariantViolation(str(error)) from error
    arm = worker.V075WorkerArmV1(request["arm"])
    route = worker.V075WorkerRouteV1(request["route"])
    registry = worker.freeze_v075_worker_registry_draft_v1()
    registration = registry.require_arm(arm)
    capabilities = _capability_documents(request)
    context = _registered_context(request["context_id"])
    proposal = _proposal(request, arm, registration)
    schedule = _schedule(request, arm, route, capabilities)
    rows = _rows(request, capabilities, context, route)
    root_complete, child_complete, unresolved = _catalogue_completeness(
        context,
        rows,
    )
    model = V075StatisticalModelV1(
        request["request_id"],
        request["occurrence_id"],
        arm,
        proposal.proposal_id,
        schedule.schedule_id,
        rows,
        root_complete,
        child_complete,
        unresolved,
    )
    status = _candidate_status(model, arm)
    root_state_id = public_graph.root_catalogue_v1(context).state.state_id
    policy = V075PolicyCandidateV1(
        model.model_id,
        arm,
        status,
        tuple(
            sorted(
                row.row_id
                for row in rows
                if row.source_state_id == root_state_id
            )
        ),
    )
    envelope = V075EnvelopeCandidateV1(
        model.model_id,
        policy.policy_candidate_id,
        status,
    )
    total_lift_input = V075TotalLiftCandidateInputV1(
        request["occurrence_id"],
        model.model_id,
        policy.policy_candidate_id,
        envelope.envelope_candidate_id,
        status,
        tuple(row.row_id for row in rows),
        tuple(request["capability_ref_ids"]),
    )
    return V075RouteNativeBackendResultV1(
        request["request_id"],
        request["occurrence_id"],
        arm,
        schedule,
        proposal,
        model,
        policy,
        envelope,
        total_lift_input,
        _work(request, arm, capabilities, rows),
    )


def verify_v075_route_native_backend_result_v1(
    *,
    request_bytes: bytes,
    claimed_bytes: bytes,
) -> V075RouteNativeBackendResultV1:
    """Recompute the complete construction result from canonical input."""

    expected = execute_v075_route_native_backend_core_v1(request_bytes)
    if type(claimed_bytes) is not bytes or claimed_bytes != expected.canonical_bytes:
        _fail("route-native backend result differs from recomputation")
    return expected


__all__ = [
    "BOUNDARY_GRID_BITS",
    "COUNTER_PATHS",
    "DOMAIN_TAGS",
    "MAX_SUPPORT_OUTCOMES",
    "PROFILE_KEY",
    "PRODUCTION_BACKEND_READY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_WRONG_REVERSED_MIDRANK",
    "ROW_EPOCH_BETA",
    "SCHEMA_VERSION",
    "SOURCE_FORWARD_MIDRANK",
    "TARGET_HALF_WIDTH",
    "V075BackendCandidateStatusV1",
    "V075BackendCounterV1",
    "V075BackendScheduleStatusV1",
    "V075BackendWorkV1",
    "V075EnvelopeCandidateV1",
    "V075EventIntervalV1",
    "V075OutcomeDescriptorV1",
    "V075PolicyCandidateV1",
    "V075ProposalBasisV1",
    "V075RouteNativeBackendInvariantViolation",
    "V075RouteNativeBackendResultV1",
    "V075RouteScheduleV1",
    "V075StatisticalModelV1",
    "V075StatisticalRowV1",
    "V075TotalLiftCandidateInputV1",
    "execute_v075_route_native_backend_core_v1",
    "verify_v075_route_native_backend_result_v1",
]
