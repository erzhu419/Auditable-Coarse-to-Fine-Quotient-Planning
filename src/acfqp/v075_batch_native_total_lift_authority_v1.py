"""Batch-native V0-075 model/policy/envelope and total-lift authority.

The operational binding in this module accepts exactly one canonical
``V075BatchNativeBackendResultV1`` and the already emitted learned-support
planner result.  It never recompiles statistical rows, never reruns a planner,
and never expands a batch into per-draw capabilities.

The independent construction verifier can privately replay the signed batches
and reconstruct the exact H=2 transition closure.  It implements the total
lift row by row:

* exact environment failures remain environment failures;
* an exact nonfailure outcome present in the selected statistical row support
  follows the selected continuation (or safely reaches H=0);
* every exact nonfailure outcome absent from that *selected ground row* enters
  one absorbing policy-abort failure with zero continuation reward.

This includes H=1 statistical ``OTHER`` outcomes.  Consequently an aggregate
support row cannot silently treat an unmodelled terminal success as safe.

The construction multistage E2E and attack gate has passed.  Production exact
replay now yields a domain-separated candidate and an independently recomputed
typed result, but neither is a campaign certificate.  Production execution
remains locked until the registered occurrence worker consumes this authority
and campaign reconciliation independently closes the resulting occurrence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Iterable, Mapping

from acfqp.h2_graph_transition_engine_v1 import H2GraphKernelV1
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_batch_native_statistical_backend_v1 as batch_backend
from acfqp import v075_batched_observer_authority_v1 as batched
from acfqp import v075_learned_support_quotient_planners_v1 as planners
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import (
    v075_private_environment_generation_profile_v1 as private_generation,
)
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_route_native_backend_core_v1 as route_backend
from acfqp import v075_total_lift_authority_v1 as exact_authority


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.41.0"
PROFILE_KEY = "v075_batch_native_total_lift_authority_v1"

PRODUCTION_TOTAL_LIFT_EXECUTION_ALLOWED = False
PER_DRAW_CAPABILITY_EXPANSION_ALLOWED = False
CANONICAL_BACKEND_RECOMPUTATION_IN_OPERATIONAL_BRIDGE = False
CANONICAL_PLANNER_RECOMPUTATION_IN_OPERATIONAL_BRIDGE = False

POLICY_ABORT_RULE = planners.POLICY_ABORT_RULE
CONSTRUCTION_E2E_GATE_STATUS = "PASSED"
PRODUCTION_WORKER_INTEGRATION_BLOCKER = (
    "BATCH_NATIVE_TOTAL_LIFT_PRODUCTION_WORKER_INTEGRATION_NOT_RUN"
)
PRODUCTION_RECONCILIATION_INTEGRATION_BLOCKER = (
    "BATCH_NATIVE_TOTAL_LIFT_PRODUCTION_RECONCILIATION_INTEGRATION_NOT_RUN"
)

REQUIRED_LIFECYCLE_PHASE_ORDER = (
    "DISCOVERY_BATCH",
    "SUPPORT_FREEZE",
    "VALIDATION_BATCH",
)

REQUIRED_LIFECYCLE_CLOSURE_FIELDS = (
    "occurrence_id",
    "context_id",
    "arm",
    "target_tape_namespace_id",
    "session_public_id",
    "observer_open_binding_id",
    "lifecycle_transcript_id",
    "lifecycle_phase_order",
    "batch_ids",
    "request_ids",
    "stream_ids",
    "sequence_verification_ids",
    "public_verification_ids",
    "private_replay_verification_ids",
    "aggregate_support_evidence_ids",
    "support_freeze_event_ids",
    "accepted_draw_count",
    "accepted_draw_cap",
    "route_cap_profile_id",
    "per_draw_capability_count",
    "underlying_session_closure_id",
    "underlying_session_closure_verification_id",
    "terminal_code",
    "observer_signature_hex",
)

DOMAIN_TAGS = {
    "observed_row": (
        "acfqp:v075-batch-native-total-lift-observed-row:v1"
    ),
    "model": "acfqp:v075-batch-native-total-lift-model-binding:v1",
    "selected_row_support": (
        "acfqp:v075-batch-native-total-lift-selected-row-support:v1"
    ),
    "policy": "acfqp:v075-batch-native-total-lift-policy-binding:v1",
    "envelope": "acfqp:v075-batch-native-total-lift-envelope-binding:v1",
    "lineage": "acfqp:v075-batch-native-total-lift-lineage:v1",
    "exact_replay": (
        "acfqp:v075-batch-native-total-lift-construction-exact-replay:v1"
    ),
    "production_exact_replay": (
        "acfqp:v075-batch-native-total-lift-production-exact-replay:v1"
    ),
    "partition": (
        "acfqp:v075-batch-native-total-lift-branch-partition:v1"
    ),
    "candidate": (
        "acfqp:v075-batch-native-total-lift-construction-candidate:v1"
    ),
    "verification": (
        "acfqp:v075-batch-native-total-lift-construction-verification:v1"
    ),
    "production_candidate": (
        "acfqp:v075-batch-native-total-lift-production-candidate:v1"
    ),
    "production_result": (
        "acfqp:v075-batch-native-total-lift-production-result:v1"
    ),
    "readiness": (
        "acfqp:v075-batch-native-total-lift-production-readiness:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("batch-native total-lift content domains overlap")


class V075BatchNativeTotalLiftInvariantViolation(ValueError):
    """A batch, row, policy, envelope, exact replay, or identity was invalid."""


def _fail(message: str) -> None:
    raise V075BatchNativeTotalLiftInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        raw = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise V075BatchNativeTotalLiftInvariantViolation(str(error)) from error
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + raw
    ).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075BatchNativeTotalLiftInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("batch-native total-lift arithmetic must be exact")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _action(value: Any, field_name: str) -> tuple[int, int, int]:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(item) is not int for item in value)
        or value[0] >= value[1]
        or value[2] not in value[:2]
    ):
        _fail(f"{field_name} is not one canonical ground action triple")
    return value


def _backend_counter(
    result: batch_backend.V075BatchNativeBackendResultV1,
    path: str,
) -> int:
    matches = tuple(item.value for item in result.work.counters if item.path == path)
    if len(matches) != 1:
        _fail(f"batch-native work lacks exactly one {path} counter")
    return matches[0]


@dataclass(frozen=True, slots=True)
class V075BatchObservedRowBindingV1:
    backend_result_id: str
    statistical_row: route_backend.V075StatisticalRowV1
    row_binding: graph.V075ObservationRowBindingV1
    discovery_batch_ids: tuple[str, ...]
    validation_batch_ids: tuple[str, ...]
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.backend_result_id, "observed row backend result")
        if (
            type(self.statistical_row)
            is not route_backend.V075StatisticalRowV1
            or type(self.row_binding) is not graph.V075ObservationRowBindingV1
            or self.row_binding.row_binding_id
            != self.statistical_row.row_binding_id
            or self.row_binding.state_id
            != self.statistical_row.source_state_id
            or self.row_binding.remaining_horizon
            != self.statistical_row.remaining_horizon
            or self.row_binding.action != self.statistical_row.action
            or self.discovery_batch_ids
            != self.statistical_row.discovery_capability_ids
            or self.validation_batch_ids
            != self.statistical_row.validation_capability_ids
            or not self.discovery_batch_ids
            or not self.validation_batch_ids
            or self.discovery_batch_ids
            != tuple(sorted(set(self.discovery_batch_ids)))
            or self.validation_batch_ids
            != tuple(sorted(set(self.validation_batch_ids)))
            or set(self.discovery_batch_ids) & set(self.validation_batch_ids)
        ):
            _fail("batch observed-row binding is stale or per-draw adapted")
        object.__setattr__(
            self,
            "_binding_id",
            _hash("observed_row", self._payload()),
        )

    @property
    def row_id(self) -> str:
        return self.statistical_row.row_id

    @property
    def action(self) -> tuple[int, int, int]:
        return self.statistical_row.action

    @property
    def modeled_outcome_keys(
        self,
    ) -> tuple[tuple[str, bool, bool], ...]:
        return tuple(
            sorted(
                (
                    item.next_state_id,
                    item.failure,
                    item.terminal,
                )
                for item in self.statistical_row.support
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_batch_native_total_lift_observed_row.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "backend_result_id": self.backend_result_id,
            "statistical_row_id": self.statistical_row.row_id,
            "row_binding_id": self.row_binding.row_binding_id,
            "source_state_id": self.row_binding.state_id,
            "remaining_horizon": self.row_binding.remaining_horizon,
            "action": list(self.action),
            "discovery_batch_ids": list(self.discovery_batch_ids),
            "validation_batch_ids": list(self.validation_batch_ids),
            "modeled_outcome_keys": [
                {
                    "next_state_id": state_id,
                    "failure": failure,
                    "terminal": terminal,
                }
                for state_id, failure, terminal in self.modeled_outcome_keys
            ],
            "aggregate_batch_native": True,
            "per_draw_capability_expansion": False,
        }

    @property
    def binding_id(self) -> str:
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class V075BatchNativeModelBindingV1:
    backend_result: batch_backend.V075BatchNativeBackendResultV1
    learned_graph: planners.V075LearnedSupportGraphV1
    rows: tuple[V075BatchObservedRowBindingV1, ...]
    accepted_draw_count: int
    selected_accepted_draw_count: int
    _model_binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.backend_result)
            is not batch_backend.V075BatchNativeBackendResultV1
            or type(self.learned_graph) is not planners.V075LearnedSupportGraphV1
            or self.learned_graph.backend_result
            != self.backend_result.route_native_result
            or type(self.rows) is not tuple
            or not self.rows
            or any(
                type(item) is not V075BatchObservedRowBindingV1
                or item.backend_result_id != self.backend_result.result_id
                for item in self.rows
            )
            or tuple(item.row_id for item in self.rows)
            != tuple(
                sorted(
                    item.row_id
                    for item in self.backend_result.route_native_result.model.rows
                )
            )
            or type(self.accepted_draw_count) is not int
            or type(self.selected_accepted_draw_count) is not int
            or not 0 < self.selected_accepted_draw_count <= self.accepted_draw_count
        ):
            _fail("batch-native total-lift model binding is inconsistent")
        batch_by_id = {
            item.batch_id: item for item in self.backend_result.request.batches
        }
        expected_total = sum(
            item.request.accepted_draw_count for item in batch_by_id.values()
        )
        expected_selected = sum(
            batch_by_id[item].request.accepted_draw_count
            for item in self.backend_result.selected_batch_ids
        )
        cap = self.backend_result.request.cap_profile
        route = self.backend_result.request.route
        route_cap = (
            cap.maximum_incremental_draws_per_adaptive_arm
            if route.value == "ADAPTIVE_QUOTIENT"
            else sum(
                item.request.accepted_draw_cap
                for item in self.backend_result.request.batches
            )
        )
        row_batch_ids = {
            batch_id
            for row in self.rows
            for batch_id in (
                *row.discovery_batch_ids,
                *row.validation_batch_ids,
            )
        }
        if (
            expected_total != self.accepted_draw_count
            or expected_selected != self.selected_accepted_draw_count
            or self.accepted_draw_count
            != _backend_counter(
                self.backend_result,
                "common.accepted_draws_consumed",
            )
            or self.accepted_draw_count > route_cap
            or row_batch_ids != set(self.backend_result.selected_batch_ids)
            or _backend_counter(
                self.backend_result,
                "common.per_draw_capabilities_materialized",
            )
            != 0
        ):
            _fail("batch-native accepted-draw work/cap binding changed")
        object.__setattr__(
            self,
            "_model_binding_id",
            _hash("model", self._payload()),
        )

    @property
    def context(self):
        return self.backend_result.request.context

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_batch_native_total_lift_model_binding.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "backend_result_id": self.backend_result.result_id,
            "route_native_result_id": (
                self.backend_result.route_native_result.result_id
            ),
            "statistical_model_id": (
                self.backend_result.route_native_result.model.model_id
            ),
            "learned_support_graph_id": self.learned_graph.graph_id,
            "observed_row_binding_ids": [
                item.binding_id for item in self.rows
            ],
            "accepted_draw_count": self.accepted_draw_count,
            "selected_accepted_draw_count": (
                self.selected_accepted_draw_count
            ),
            "superseded_batch_ids": list(
                self.backend_result.superseded_batch_ids
            ),
            "aggregate_support_evidence_ids": list(
                self.backend_result.aggregate_support_evidence_ids
            ),
            "canonical_backend_recomputed": False,
            "per_draw_capability_expansion": False,
        }

    @property
    def model_binding_id(self) -> str:
        return self._model_binding_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "rows": [item.to_document() for item in self.rows],
            "model_binding_id": self.model_binding_id,
        }


@dataclass(frozen=True, slots=True)
class V075BatchSelectedRowSupportV1:
    model_binding_id: str
    source_state_id: str
    remaining_horizon: int
    ground_action: tuple[int, int, int]
    statistical_row_id: str
    modeled_outcome_keys: tuple[tuple[str, bool, bool], ...]
    _support_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.model_binding_id, "selected row support model")
        _cid(self.source_state_id, "selected row support source state")
        _cid(self.statistical_row_id, "selected statistical row")
        _action(self.ground_action, "selected row support action")
        if (
            self.remaining_horizon not in (1, 2)
            or type(self.modeled_outcome_keys) is not tuple
            or not self.modeled_outcome_keys
            or self.modeled_outcome_keys
            != tuple(sorted(set(self.modeled_outcome_keys)))
            or any(
                type(item) is not tuple
                or len(item) != 3
                or type(item[0]) is not str
                or type(item[1]) is not bool
                or type(item[2]) is not bool
                for item in self.modeled_outcome_keys
            )
        ):
            _fail("selected row-specific modeled support is malformed")
        for state_id, _failure, _terminal in self.modeled_outcome_keys:
            _cid(state_id, "selected modeled successor")
        object.__setattr__(
            self,
            "_support_id",
            _hash("selected_row_support", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_batch_native_total_lift_selected_row_support.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "model_binding_id": self.model_binding_id,
            "source_state_id": self.source_state_id,
            "remaining_horizon": self.remaining_horizon,
            "ground_action": list(self.ground_action),
            "statistical_row_id": self.statistical_row_id,
            "modeled_outcome_keys": [
                {
                    "next_state_id": state_id,
                    "failure": failure,
                    "terminal": terminal,
                }
                for state_id, failure, terminal in self.modeled_outcome_keys
            ],
            "support_is_selected_ground_row_specific": True,
            "unmodeled_exact_nonfailure_behavior": (
                "ABSORBING_POLICY_ABORT_FAILURE"
            ),
        }

    @property
    def support_id(self) -> str:
        return self._support_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "support_id": self.support_id}


@dataclass(frozen=True, slots=True)
class V075BatchNativePolicyBindingV1:
    model: V075BatchNativeModelBindingV1
    planner_result: planners.V075SupportPlannerResultV1
    selected_row_supports: tuple[V075BatchSelectedRowSupportV1, ...]
    _policy_binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.model) is not V075BatchNativeModelBindingV1
            or type(self.planner_result) is not planners.V075SupportPlannerResultV1
            or self.planner_result.graph != self.model.learned_graph
            or not self.planner_result.ready_for_exact_total_lift
            or type(self.planner_result.policy)
            is not planners.V075DeterministicH2PolicyV1
            or type(self.planner_result.envelope)
            is not planners.V075RobustH2EnvelopeV1
            or type(self.selected_row_supports) is not tuple
            or not self.selected_row_supports
            or any(
                type(item) is not V075BatchSelectedRowSupportV1
                or item.model_binding_id != self.model.model_binding_id
                for item in self.selected_row_supports
            )
        ):
            _fail("batch-native selected policy is not an exact planner output")
        policy = self.planner_result.policy
        selected_pairs = {
            (choice.state_id, decision.remaining_horizon, action, row_id)
            for decision in policy.decisions
            for choice in decision.state_choices
            for action, row_id in zip(
                choice.ground_actions,
                choice.row_ids,
                strict=True,
            )
        }
        supports = {
            (
                item.source_state_id,
                item.remaining_horizon,
                item.ground_action,
                item.statistical_row_id,
            )
            for item in self.selected_row_supports
        }
        if (
            supports != selected_pairs
            or len(supports) != len(self.selected_row_supports)
            or self.selected_row_supports
            != tuple(
                sorted(
                    self.selected_row_supports,
                    key=lambda item: (
                        -item.remaining_horizon,
                        item.source_state_id,
                        item.ground_action,
                    ),
                )
            )
        ):
            _fail("planner action/row mapping is incomplete or transplanted")
        root_state_id = graph.root_catalogue_v1(
            self.model.context
        ).state.state_id
        root_supports = tuple(
            item
            for item in self.selected_row_supports
            if item.remaining_horizon == 2
            and item.source_state_id == root_state_id
        )
        if not root_supports:
            _fail("selected policy lacks the actual root-state decision")
        child_choice_states = {
            choice.state_id
            for decision in policy.decisions
            if decision.remaining_horizon == 1
            for choice in decision.state_choices
        }
        modeled_root_children = {
            state_id
            for item in root_supports
            for state_id, failure, terminal in item.modeled_outcome_keys
            if not failure and not terminal
        }
        if not modeled_root_children <= child_choice_states:
            _fail("modeled selected root support lacks child decisions")
        object.__setattr__(
            self,
            "_policy_binding_id",
            _hash("policy", self._payload()),
        )

    @property
    def policy(self) -> planners.V075DeterministicH2PolicyV1:
        assert self.planner_result.policy is not None
        return self.planner_result.policy

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_batch_native_total_lift_policy_binding.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "model_binding_id": self.model.model_binding_id,
            "planner_result_id": self.planner_result.result_id,
            "learned_policy_id": self.policy.policy_id,
            "route": self.policy.route.value,
            "selected_row_support_ids": [
                item.support_id for item in self.selected_row_supports
            ],
            "deterministic_semantic_selector": True,
            "fixed_distinct_action_concretizer": True,
            "policy_randomization": False,
            "canonical_planner_recomputed": False,
        }

    @property
    def policy_binding_id(self) -> str:
        return self._policy_binding_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "selected_row_supports": [
                item.to_document() for item in self.selected_row_supports
            ],
            "policy_binding_id": self.policy_binding_id,
        }


@dataclass(frozen=True, slots=True)
class V075BatchNativeEnvelopeBindingV1:
    policy: V075BatchNativePolicyBindingV1
    learned_envelope: planners.V075RobustH2EnvelopeV1
    _envelope_binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.policy) is not V075BatchNativePolicyBindingV1
            or type(self.learned_envelope) is not planners.V075RobustH2EnvelopeV1
            or self.policy.planner_result.envelope != self.learned_envelope
            or self.learned_envelope.policy != self.policy.policy
        ):
            _fail("batch-native operational envelope was transplanted")
        object.__setattr__(
            self,
            "_envelope_binding_id",
            _hash("envelope", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        item = self.learned_envelope
        return {
            "schema": (
                "acfqp.v075_batch_native_total_lift_envelope_binding.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "policy_binding_id": self.policy.policy_binding_id,
            "learned_envelope_id": item.envelope_id,
            "selected_reward_lower": _fdoc(item.selected_reward_lower),
            "selected_reward_upper": _fdoc(item.selected_reward_upper),
            "unrestricted_reward_upper": _fdoc(
                item.unrestricted_reward_upper
            ),
            "selected_failure_upper": _fdoc(
                item.selected_failure_upper
            ),
            "normalized_regret_upper": _fdoc(
                item.normalized_regret_upper
            ),
            "familywise_confidence_error_upper": _fdoc(
                item.familywise_confidence_error_upper
            ),
            "exact_atom_access": False,
        }

    @property
    def envelope_binding_id(self) -> str:
        return self._envelope_binding_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "envelope_binding_id": self.envelope_binding_id,
        }


@dataclass(frozen=True, slots=True)
class V075BatchNativeLineageBindingV1:
    envelope: V075BatchNativeEnvelopeBindingV1
    sealed_lifecycle: lifecycle.V075SealedMultistageOccurrenceLifecycleV1
    private_replays: tuple[
        batched.V075BatchedObservationPrivateReplayVerificationV1,
        ...,
    ]
    _lineage_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.envelope) is not V075BatchNativeEnvelopeBindingV1
            or type(self.sealed_lifecycle)
            is not lifecycle.V075SealedMultistageOccurrenceLifecycleV1
            or type(self.private_replays) is not tuple
            or any(
                type(item)
                is not batched.V075BatchedObservationPrivateReplayVerificationV1
                for item in self.private_replays
            )
            or self.private_replays
            != tuple(sorted(self.private_replays, key=lambda item: item.batch_id))
        ):
            _fail("batch-native private replay lineage is untyped")
        request = self.envelope.policy.model.backend_result.request
        result = self.envelope.policy.model.backend_result
        sealed = self.sealed_lifecycle
        closure = sealed.closure
        batch_by_id = {item.batch_id: item for item in request.batches}
        replay_by_batch = {item.batch_id: item for item in self.private_replays}
        if (
            len(replay_by_batch) != len(self.private_replays)
            or set(replay_by_batch) != set(batch_by_id)
        ):
            _fail("private replay registry does not cover every signed batch")
        for batch_id, batch in batch_by_id.items():
            replay = replay_by_batch[batch_id]
            if (
                replay.request_id != batch.request.request_id
                or replay.observer_open_binding_id
                != batch.request.observer_open_binding.binding_id
                or replay.authority_scope is not batch.request.authority_scope
                or replay.replayed_draw_count
                != batch.request.accepted_draw_count
            ):
                _fail("private replay attestation was batch-transplanted")
        independently_verified = (
            lifecycle.verify_v075_multistage_occurrence_closure_v1(
                closure=closure,
                batches=sealed.batches,
                public_verifications=sealed.public_verifications,
                sequence_verifications=sealed.sequence_verifications,
                private_replay_verifications=(
                    sealed.private_replay_verifications
                ),
                aggregate_support_evidence=(
                    sealed.aggregate_support_evidence
                ),
                underlying_closure=sealed.underlying_closure,
                underlying_closure_verification=(
                    sealed.underlying_closure_verification
                ),
                observer_open_binding=(
                    sealed.underlying_closure.authority_binding
                ),
            )
        )
        request_public = {
            item.batch_id: item for item in request.public_verifications
        }
        sealed_public = {
            item.batch_id: item for item in sealed.public_verifications
        }
        request_sequences = {
            item.stream_id: item for item in request.sequence_verifications
        }
        sealed_sequences = {
            item.stream_id: item for item in sealed.sequence_verifications
        }
        expected_scope = (
            lifecycle.V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY
            if request.authority_scope
            is batched.V075BatchAuthorityScopeV1.CONSTRUCTION_ONLY
            else lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION
        )
        if (
            independently_verified != sealed.verification
            or closure.terminal_code
            is not (
                lifecycle.V075LifecycleTerminalCodeV1
                .COMPLETE_REGISTERED_CHECKPOINT_CLOSED
            )
            or closure.scope is not expected_scope
            or closure.occurrence_id != request.occurrence_id
            or closure.context_id != request.context.context_id
            or closure.arm != request.arm.value
            or closure.target_tape_namespace_id
            != request.namespace.target_tape_namespace_id
            or closure.route_cap_profile_id
            != request.cap_profile.cap_profile_id
            or closure.session_public_id
            != request.batches[0].request.session_public_id
            or closure.observer_open_binding_id
            != request.batches[0].request.observer_open_binding.binding_id
            or set(closure.batch_ids) != set(batch_by_id)
            or {
                item.request.request_id: item.batch_id
                for item in request.batches
            }
            != {
                item.request.request_id: item.batch_id
                for item in sealed.batches
            }
            or request_public != sealed_public
            or request_sequences != sealed_sequences
            or self.private_replays
            != sealed.private_replay_verifications
            or set(closure.aggregate_support_evidence_ids)
            != set(result.aggregate_support_evidence_ids)
            or closure.accepted_draw_count
            != self.envelope.policy.model.accepted_draw_count
            or closure.accepted_draw_count
            != sum(
                item.request.accepted_draw_count
                for item in request.batches
            )
            or sealed.underlying_closure.entries
            or sealed.underlying_closure.closure_id
            != closure.underlying_session_closure_id
            or sealed.underlying_closure_verification.verification_id
            != closure.underlying_closure_verification_id
        ):
            _fail(
                "multistage occurrence closure does not exactly bind the "
                "batch-native request and all replay authorities"
            )
        object.__setattr__(
            self,
            "_lineage_id",
            _hash("lineage", self._payload()),
        )

    @property
    def model(self) -> V075BatchNativeModelBindingV1:
        return self.envelope.policy.model

    def _payload(self) -> dict[str, Any]:
        result = self.model.backend_result
        request = result.request
        return {
            "schema": "acfqp.v075_batch_native_total_lift_lineage.v1",
            "schema_version": SCHEMA_VERSION,
            "envelope_binding_id": self.envelope.envelope_binding_id,
            "backend_result_id": result.result_id,
            "occurrence_id": request.occurrence_id,
            "context_id": request.context.context_id,
            "arm": request.arm.value,
            "session_public_id": (
                request.batches[0].request.session_public_id
            ),
            "observer_open_binding_id": (
                request.batches[0].request.observer_open_binding.binding_id
            ),
            "batch_ids": [item.batch_id for item in request.batches],
            "public_verification_ids": [
                item.verification_id for item in request.public_verifications
            ],
            "sequence_verification_ids": [
                item.verification_id for item in request.sequence_verifications
            ],
            "private_replay_verification_ids": [
                item.verification_id for item in self.private_replays
            ],
            "aggregate_support_evidence_ids": list(
                result.aggregate_support_evidence_ids
            ),
            "accepted_draw_count": self.model.accepted_draw_count,
            "per_draw_capability_count": 0,
            "multistage_occurrence_closure_id": (
                self.sealed_lifecycle.closure.closure_id
            ),
            "multistage_occurrence_closure_verification_id": (
                self.sealed_lifecycle.verification.verification_id
            ),
            "lifecycle_transcript_id": (
                self.sealed_lifecycle.closure.lifecycle_transcript_id
            ),
            "underlying_empty_observer_closure_id": (
                self.sealed_lifecycle.underlying_closure.closure_id
            ),
            "underlying_empty_observer_closure_verification_id": (
                self.sealed_lifecycle.underlying_closure_verification
                .verification_id
            ),
            "production_lineage_complete": (
                self.sealed_lifecycle.closure.scope
                is lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION
            ),
        }

    @property
    def lineage_id(self) -> str:
        return self._lineage_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "lineage_id": self.lineage_id}


def freeze_v075_batch_native_total_lift_lineage_v1(
    *,
    backend_result: batch_backend.V075BatchNativeBackendResultV1,
    planner_result: planners.V075SupportPlannerResultV1,
    sealed_lifecycle: lifecycle.V075SealedMultistageOccurrenceLifecycleV1,
) -> V075BatchNativeLineageBindingV1:
    """Bind existing native outputs without re-running either compiler."""

    if (
        type(backend_result)
        is not batch_backend.V075BatchNativeBackendResultV1
        or type(planner_result) is not planners.V075SupportPlannerResultV1
        or type(sealed_lifecycle)
        is not lifecycle.V075SealedMultistageOccurrenceLifecycleV1
    ):
        _fail("batch-native total-lift bridge rejects duck-typed inputs")
    node_by_row_id = {
        row.row_id: node
        for node in planner_result.graph.nodes
        for row in node.rows
    }
    rows = []
    for row in sorted(
        backend_result.route_native_result.model.rows,
        key=lambda item: item.row_id,
    ):
        node = node_by_row_id.get(row.row_id)
        if node is None:
            _fail("learned graph omits one backend statistical row")
        binding = graph.observation_row_binding_v1(
            node.catalogue.context,
            node.catalogue,
            row.action,
        )
        rows.append(
            V075BatchObservedRowBindingV1(
                backend_result.result_id,
                row,
                binding,
                row.discovery_capability_ids,
                row.validation_capability_ids,
            )
        )
    batch_by_id = {
        item.batch_id: item for item in backend_result.request.batches
    }
    model = V075BatchNativeModelBindingV1(
        backend_result,
        planner_result.graph,
        tuple(rows),
        sum(
            item.request.accepted_draw_count
            for item in backend_result.request.batches
        ),
        sum(
            batch_by_id[item].request.accepted_draw_count
            for item in backend_result.selected_batch_ids
        ),
    )
    row_by_id = {item.row_id: item for item in model.rows}
    if planner_result.policy is None or planner_result.envelope is None:
        _fail("planner emitted no candidate policy/envelope")
    supports = []
    for decision in planner_result.policy.decisions:
        for choice in decision.state_choices:
            for action, row_id in zip(
                choice.ground_actions,
                choice.row_ids,
                strict=True,
            ):
                observed = row_by_id.get(row_id)
                if (
                    observed is None
                    or observed.row_binding.state_id != choice.state_id
                    or observed.row_binding.remaining_horizon
                    != decision.remaining_horizon
                    or observed.action != action
                ):
                    _fail("selected action-to-row binding is stale")
                supports.append(
                    V075BatchSelectedRowSupportV1(
                        model.model_binding_id,
                        choice.state_id,
                        decision.remaining_horizon,
                        action,
                        row_id,
                        observed.modeled_outcome_keys,
                    )
                )
    policy = V075BatchNativePolicyBindingV1(
        model,
        planner_result,
        tuple(
            sorted(
                supports,
                key=lambda item: (
                    -item.remaining_horizon,
                    item.source_state_id,
                    item.ground_action,
                ),
            )
        ),
    )
    envelope = V075BatchNativeEnvelopeBindingV1(
        policy,
        planner_result.envelope,
    )
    return V075BatchNativeLineageBindingV1(
        envelope,
        sealed_lifecycle,
        sealed_lifecycle.private_replay_verifications,
    )


_EXACT_REPLAY_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchNativeConstructionExactReplayV1:
    _issuer: object = field(repr=False, compare=False)
    lineage_id: str
    rows: tuple[exact_authority.V075ExactReplayRowV1, ...] = field(
        repr=False
    )
    private_replay_verification_ids: tuple[str, ...]
    _replay_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.lineage_id, "construction exact replay lineage")
        if (
            self._issuer is not _EXACT_REPLAY_ISSUER
            or type(self.rows) is not tuple
            or not self.rows
            or any(
                type(item) is not exact_authority.V075ExactReplayRowV1
                for item in self.rows
            )
            or tuple(item.row_id for item in self.rows)
            != tuple(sorted({item.row_id for item in self.rows}))
            or self.private_replay_verification_ids
            != tuple(sorted(set(self.private_replay_verification_ids)))
            or not self.private_replay_verification_ids
        ):
            _fail("construction exact replay was caller-minted or incomplete")
        object.__setattr__(
            self,
            "_replay_id",
            _hash("exact_replay", self._payload()),
        )

    @property
    def exact_atom_count(self) -> int:
        return sum(len(item.atoms) for item in self.rows)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_batch_native_total_lift_"
                "construction_exact_replay.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "lineage_id": self.lineage_id,
            "private_replay_verification_ids": list(
                self.private_replay_verification_ids
            ),
            "exact_row_ids": [item.row_id for item in self.rows],
            "exact_atom_count": self.exact_atom_count,
            "scope": "CONSTRUCTION_ONLY",
            "execution_lane": "STANDALONE_EVALUATION_ONLY",
            "private_material_serialized": False,
            "exact_atom_payload_serialized": False,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def replay_id(self) -> str:
        return self._replay_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "replay_id": self.replay_id}


def mint_v075_batch_native_construction_exact_replay_v1(
    *,
    lineage: V075BatchNativeLineageBindingV1,
    authority: observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1,
    private_environment: (
        batched.V075ConstructionBatchReplayEnvironmentFixtureV1
    ),
) -> V075BatchNativeConstructionExactReplayV1:
    """Private construction replay; never serializes a law or exact atom."""

    if (
        type(lineage) is not V075BatchNativeLineageBindingV1
        or type(authority)
        is not observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1
        or type(private_environment)
        is not batched.V075ConstructionBatchReplayEnvironmentFixtureV1
        or authority.namespace != lineage.model.backend_result.request.namespace
        or private_environment.namespace != authority.namespace
    ):
        _fail("construction exact replay authority/environment is transplanted")
    replay_by_batch = {
        item.batch_id: item for item in lineage.private_replays
    }
    recomputed = []
    for item in lineage.model.backend_result.request.batches:
        verified = (
            batched
            .verify_v075_construction_batched_observation_private_replay_v1(
                claimed=item,
                authority=authority,
                private_environment=private_environment,
            )
        )
        if verified != replay_by_batch.get(item.batch_id):
            _fail("construction private replay differs from bound attestation")
        recomputed.append(verified)
    context = lineage.model.context
    law = private_environment.private_environment[
        context.replicate_ordinal
    ]
    kernel = H2GraphKernelV1(
        context.topology,
        context.rank_cap,
        context.horizon,
        law,
    )
    try:
        rows = exact_authority._reconstruct_full_h2_exact_rows(
            context=context,
            kernel=kernel,
        )
    except exact_authority.V075ExactReplayMintViolation as error:
        _fail(str(error))
    return V075BatchNativeConstructionExactReplayV1(
        _EXACT_REPLAY_ISSUER,
        lineage.lineage_id,
        rows,
        tuple(sorted(item.verification_id for item in recomputed)),
    )


_PRODUCTION_EXACT_REPLAY_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchNativeProductionExactReplayV1:
    """Private replay mint bound to the exact production authorization types.

    This is an evaluation boundary, not a plan certificate.  Its exact rows
    are retained only in memory and omitted from the public document.
    """

    _issuer: object = field(repr=False, compare=False)
    lineage_id: str
    rows: tuple[exact_authority.V075ExactReplayRowV1, ...] = field(
        repr=False
    )
    private_replay_verification_ids: tuple[str, ...]
    observer_open_authorization_id: str
    multistage_closure_id: str
    underlying_closure_verification_id: str
    _replay_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.lineage_id, "production exact replay lineage"),
            (
                self.observer_open_authorization_id,
                "production observer-open authorization",
            ),
            (self.multistage_closure_id, "production multistage closure"),
            (
                self.underlying_closure_verification_id,
                "production underlying closure verification",
            ),
        ):
            _cid(value, label)
        if (
            self._issuer is not _PRODUCTION_EXACT_REPLAY_ISSUER
            or type(self.rows) is not tuple
            or not self.rows
            or any(
                type(item) is not exact_authority.V075ExactReplayRowV1
                for item in self.rows
            )
            or tuple(item.row_id for item in self.rows)
            != tuple(sorted({item.row_id for item in self.rows}))
            or self.private_replay_verification_ids
            != tuple(sorted(set(self.private_replay_verification_ids)))
            or not self.private_replay_verification_ids
        ):
            _fail("production exact replay was caller-minted or incomplete")
        object.__setattr__(
            self,
            "_replay_id",
            _hash("production_exact_replay", self._payload()),
        )

    @property
    def exact_atom_count(self) -> int:
        return sum(len(item.atoms) for item in self.rows)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_batch_native_total_lift_"
                "production_exact_replay.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "lineage_id": self.lineage_id,
            "observer_open_authorization_id": (
                self.observer_open_authorization_id
            ),
            "multistage_closure_id": self.multistage_closure_id,
            "underlying_closure_verification_id": (
                self.underlying_closure_verification_id
            ),
            "private_replay_verification_ids": list(
                self.private_replay_verification_ids
            ),
            "exact_row_ids": [item.row_id for item in self.rows],
            "exact_atom_count": self.exact_atom_count,
            "scope": "PRODUCTION_INDEPENDENT_REPLAY",
            "execution_lane": "STANDALONE_EVALUATION_ONLY",
            "private_material_serialized": False,
            "exact_atom_payload_serialized": False,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def replay_id(self) -> str:
        return self._replay_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "replay_id": self.replay_id}


def mint_v075_batch_native_production_exact_replay_v1(
    *,
    lineage: V075BatchNativeLineageBindingV1,
    authority: Any,
    private_salt: bytes,
    private_environment: private_generation.V075PrivateGeneratedEnvironmentV1,
) -> V075BatchNativeProductionExactReplayV1:
    """Mint only from reveal-attested authorization and generated laws."""

    from acfqp import v075_preopen_target_authorization_v1 as preopen

    if (
        type(lineage) is not V075BatchNativeLineageBindingV1
        or type(authority) is not preopen.V075ObserverOpenAuthorizationV1
        or type(private_salt) is not bytes
        or type(private_environment)
        is not private_generation.V075PrivateGeneratedEnvironmentV1
        or lineage.sealed_lifecycle.closure.scope
        is not lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION
        or private_environment.family
        != lineage.model.backend_result.request.namespace.family
    ):
        _fail(
            "production exact replay requires exact reveal-attested "
            "authorization, generated environment, and production lifecycle"
        )
    namespace = lineage.model.backend_result.request.namespace
    replay_by_batch = {
        item.batch_id: item for item in lineage.private_replays
    }
    recomputed = []
    for item in lineage.model.backend_result.request.batches:
        verified = (
            batched.verify_v075_production_batched_observation_private_replay_v1(
                claimed=item,
                authority=authority,
                namespace=namespace,
                private_salt=private_salt,
                private_environment=private_environment,
            )
        )
        if verified != replay_by_batch.get(item.batch_id):
            _fail("production private replay differs from bound attestation")
        recomputed.append(verified)
    sealed = lineage.sealed_lifecycle
    underlying = observer.verify_private_observer_journal_closure_v1(
        closure=sealed.underlying_closure,
        authority=authority,
        namespace=namespace,
        private_salt=private_salt,
        private_environment=(
            private_environment.secret_laws_for_commitment()
        ),
    )
    if underlying != sealed.underlying_closure_verification:
        _fail("production underlying empty closure replay changed")
    context = lineage.model.context
    law = private_environment.laws[
        context.replicate_ordinal
    ].as_secret_law()
    kernel = H2GraphKernelV1(
        context.topology,
        context.rank_cap,
        context.horizon,
        law,
    )
    try:
        rows = exact_authority._reconstruct_full_h2_exact_rows(
            context=context,
            kernel=kernel,
        )
    except exact_authority.V075ExactReplayMintViolation as error:
        _fail(str(error))
    return V075BatchNativeProductionExactReplayV1(
        _PRODUCTION_EXACT_REPLAY_ISSUER,
        lineage.lineage_id,
        rows,
        tuple(sorted(item.verification_id for item in recomputed)),
        authority.authorization_id,
        sealed.closure.closure_id,
        underlying.verification_id,
    )


@dataclass(frozen=True, slots=True)
class V075BatchLiftBranchPartitionV1:
    source_state_id: str
    remaining_horizon: int
    ground_action: tuple[int, int, int]
    statistical_row_id: str
    exact_row_id: str
    execution_weight: Fraction
    exact_atom_probability_items: tuple[tuple[str, Fraction], ...]
    environment_failure_atom_ids: tuple[str, ...]
    modeled_atom_ids: tuple[str, ...]
    policy_abort_atom_ids: tuple[str, ...]
    _partition_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.source_state_id, "partition source state"),
            (self.statistical_row_id, "partition statistical row"),
            (self.exact_row_id, "partition exact row"),
        ):
            _cid(value, label)
        _action(self.ground_action, "partition action")
        all_ids = tuple(item[0] for item in self.exact_atom_probability_items)
        partitions = (
            self.environment_failure_atom_ids,
            self.modeled_atom_ids,
            self.policy_abort_atom_ids,
        )
        if (
            self.remaining_horizon not in (1, 2)
            or type(self.execution_weight) is not Fraction
            or not 0 < self.execution_weight <= 1
            or type(self.exact_atom_probability_items) is not tuple
            or not self.exact_atom_probability_items
            or all_ids != tuple(sorted(set(all_ids)))
            or any(
                type(probability) is not Fraction
                or probability <= 0
                for _atom_id, probability
                in self.exact_atom_probability_items
            )
            or sum(
                (
                    probability
                    for _atom_id, probability
                    in self.exact_atom_probability_items
                ),
                Fraction(0),
            )
            != 1
            or any(values != tuple(sorted(set(values))) for values in partitions)
            or set().union(*(set(values) for values in partitions))
            != set(all_ids)
            or sum(len(values) for values in partitions) != len(all_ids)
        ):
            _fail("exact row branch partition is not disjoint and exhaustive")
        object.__setattr__(
            self,
            "_partition_id",
            _hash("partition", self._payload()),
        )

    def probability_of(self, atom_ids: tuple[str, ...]) -> Fraction:
        probabilities = dict(self.exact_atom_probability_items)
        return sum((probabilities[item] for item in atom_ids), Fraction(0))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_batch_native_total_lift_branch_partition.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "source_state_id": self.source_state_id,
            "remaining_horizon": self.remaining_horizon,
            "ground_action": list(self.ground_action),
            "statistical_row_id": self.statistical_row_id,
            "exact_row_id": self.exact_row_id,
            "execution_weight": _fdoc(self.execution_weight),
            "exact_atom_probability_items": [
                {
                    "exact_atom_id": atom_id,
                    "probability": _fdoc(probability),
                }
                for atom_id, probability
                in self.exact_atom_probability_items
            ],
            "environment_failure_atom_ids": list(
                self.environment_failure_atom_ids
            ),
            "modeled_atom_ids": list(self.modeled_atom_ids),
            "policy_abort_atom_ids": list(self.policy_abort_atom_ids),
            "environment_failure_probability": _fdoc(
                self.probability_of(self.environment_failure_atom_ids)
            ),
            "modeled_probability": _fdoc(
                self.probability_of(self.modeled_atom_ids)
            ),
            "policy_abort_probability": _fdoc(
                self.probability_of(self.policy_abort_atom_ids)
            ),
            "disjoint_exhaustive_partition": True,
        }

    @property
    def partition_id(self) -> str:
        return self._partition_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "partition_id": self.partition_id}


@dataclass(frozen=True, slots=True)
class _GroundPointV1:
    reward: Fraction
    failure: Fraction
    policy_signature: tuple[
        tuple[str, int, tuple[int, int, int]],
        ...,
    ]


def _pareto_ground(
    points: Iterable[_GroundPointV1],
) -> tuple[_GroundPointV1, ...]:
    by_metric: dict[tuple[Fraction, Fraction], _GroundPointV1] = {}
    for point in points:
        key = (point.reward, point.failure)
        prior = by_metric.get(key)
        if prior is None or point.policy_signature < prior.policy_signature:
            by_metric[key] = point
    unique = tuple(by_metric.values())
    retained = tuple(
        point
        for point in unique
        if not any(
            other.reward >= point.reward
            and other.failure <= point.failure
            and (
                other.reward > point.reward
                or other.failure < point.failure
            )
            for other in unique
        )
    )
    return tuple(
        sorted(
            retained,
            key=lambda item: (
                item.failure,
                -item.reward,
                item.policy_signature,
            ),
        )
    )


def _exact_rows_by_key(
    rows: tuple[exact_authority.V075ExactReplayRowV1, ...],
) -> dict[
    tuple[str, int, tuple[int, int, int]],
    exact_authority.V075ExactReplayRowV1,
]:
    result = {
        (
            item.row_binding.state_id,
            item.row_binding.remaining_horizon,
            item.row_binding.action,
        ): item
        for item in rows
    }
    if len(result) != len(rows):
        _fail("exact replay contains duplicate state-time-action rows")
    return result


def _exact_row(
    rows: Mapping[
        tuple[str, int, tuple[int, int, int]],
        exact_authority.V075ExactReplayRowV1,
    ],
    state_id: str,
    remaining_horizon: int,
    action: tuple[int, int, int],
) -> exact_authority.V075ExactReplayRowV1:
    item = rows.get((state_id, remaining_horizon, action))
    if item is None:
        _fail("exact replay lacks one selected state-time-action row")
    return item


def _exact_ground_optimum(
    *,
    context: Any,
    rows: tuple[exact_authority.V075ExactReplayRowV1, ...],
    risk_tolerance: Fraction,
) -> _GroundPointV1 | None:
    by_key = _exact_rows_by_key(rows)
    root = graph.root_catalogue_v1(context)
    candidates = []
    for root_action in root.actions:
        root_row = _exact_row(
            by_key,
            root.state.state_id,
            2,
            root_action,
        )
        active: dict[str, tuple[Any, Fraction]] = {}
        for atom in root_row.atoms:
            if atom.atom.failure:
                continue
            if atom.atom.terminal:
                _fail("exact H=2 root has terminal nonfailure mass")
            state = atom.next_state
            previous = active.get(state.state_id)
            active[state.state_id] = (
                state,
                atom.atom.probability
                + (Fraction(0) if previous is None else previous[1]),
            )
        frontier = (
            _GroundPointV1(
                root_row.reward,
                root_row.failure_probability,
                ((root.state.state_id, 2, root_action),),
            ),
        )
        for state_id in sorted(active):
            state, branch_probability = active[state_id]
            actions = graph.legal_action_triples_v1(
                context,
                state.ranks,
                state.failure,
            )
            options = tuple(
                _GroundPointV1(
                    branch_probability
                    * _exact_row(by_key, state_id, 1, action).reward,
                    branch_probability
                    * _exact_row(
                        by_key,
                        state_id,
                        1,
                        action,
                    ).failure_probability,
                    ((state_id, 1, action),),
                )
                for action in actions
            )
            frontier = _pareto_ground(
                _GroundPointV1(
                    prior.reward + option.reward,
                    prior.failure + option.failure,
                    prior.policy_signature + option.policy_signature,
                )
                for prior in frontier
                for option in options
            )
        candidates.extend(frontier)
    feasible = tuple(
        item for item in candidates if item.failure <= risk_tolerance
    )
    if not feasible:
        return None
    # Exact deterministic tie break: reward, then risk, then the complete
    # lexicographic state-time-action-triple signature.
    return min(
        feasible,
        key=lambda item: (
            -item.reward,
            item.failure,
            item.policy_signature,
        ),
    )


def _partition_exact_row_atoms(
    *,
    exact_row: exact_authority.V075ExactReplayRowV1,
    modeled_outcome_keys: tuple[tuple[str, bool, bool], ...],
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    dict[str, tuple[Any, Fraction]],
]:
    """Apply the normative environment/modeled/abort partition to one row."""

    if (
        type(exact_row) is not exact_authority.V075ExactReplayRowV1
        or type(modeled_outcome_keys) is not tuple
        or modeled_outcome_keys
        != tuple(sorted(set(modeled_outcome_keys)))
    ):
        _fail("exact row partition inputs are untyped or noncanonical")
    modeled_keys = set(modeled_outcome_keys)
    environment_ids = []
    modeled_ids = []
    abort_ids = []
    recurse: dict[str, tuple[Any, Fraction]] = {}
    for atom in exact_row.atoms:
        key = (
            atom.next_state_id,
            atom.atom.failure,
            atom.atom.terminal,
        )
        if atom.atom.failure:
            environment_ids.append(atom.atom_id)
        elif key not in modeled_keys:
            abort_ids.append(atom.atom_id)
        else:
            modeled_ids.append(atom.atom_id)
            if exact_row.row_binding.remaining_horizon == 2:
                if atom.atom.terminal:
                    _fail("modeled H=2 nonfailure unexpectedly terminates")
                prior = recurse.get(atom.next_state_id)
                recurse[atom.next_state_id] = (
                    atom.next_state,
                    atom.atom.probability
                    + (Fraction(0) if prior is None else prior[1]),
                )
            elif not atom.atom.terminal:
                _fail("modeled H=1 outcome did not terminate")
    return (
        tuple(sorted(environment_ids)),
        tuple(sorted(modeled_ids)),
        tuple(sorted(abort_ids)),
        recurse,
    )


class V075BatchTotalLiftConstructionStatusV1(str, Enum):
    EXACT_POSITIVE_CONSTRUCTION_CONTROL = (
        "EXACT_POSITIVE_CONSTRUCTION_CONTROL"
    )
    EXACT_POLICY_RISK_FAILURE = "EXACT_POLICY_RISK_FAILURE"
    EXACT_POLICY_REGRET_FAILURE = "EXACT_POLICY_REGRET_FAILURE"
    EXACT_GROUND_QUERY_INFEASIBLE = "EXACT_GROUND_QUERY_INFEASIBLE"
    STATISTICAL_ENVELOPE_MISS = "STATISTICAL_ENVELOPE_MISS"


class V075BatchTotalLiftProductionStatusV1(str, Enum):
    EXACT_POSITIVE_PRODUCTION_CANDIDATE = (
        "EXACT_POSITIVE_PRODUCTION_CANDIDATE"
    )
    EXACT_POLICY_RISK_FAILURE = "EXACT_POLICY_RISK_FAILURE"
    EXACT_POLICY_REGRET_FAILURE = "EXACT_POLICY_REGRET_FAILURE"
    EXACT_GROUND_QUERY_INFEASIBLE = "EXACT_GROUND_QUERY_INFEASIBLE"
    STATISTICAL_ENVELOPE_MISS = "STATISTICAL_ENVELOPE_MISS"


class _V075BatchTotalLiftExactOutcomeV1(str, Enum):
    EXACT_POSITIVE = "EXACT_POSITIVE"
    EXACT_POLICY_RISK_FAILURE = "EXACT_POLICY_RISK_FAILURE"
    EXACT_POLICY_REGRET_FAILURE = "EXACT_POLICY_REGRET_FAILURE"
    EXACT_GROUND_QUERY_INFEASIBLE = "EXACT_GROUND_QUERY_INFEASIBLE"
    STATISTICAL_ENVELOPE_MISS = "STATISTICAL_ENVELOPE_MISS"


_CANDIDATE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchNativeConstructionTotalLiftCandidateV1:
    _issuer: object = field(repr=False, compare=False)
    lineage_id: str
    exact_replay_id: str
    status: V075BatchTotalLiftConstructionStatusV1
    selected_expected_reward: Fraction
    environment_failure_probability: Fraction
    policy_abort_failure_probability: Fraction
    selected_failure_probability: Fraction
    optimal_expected_reward: Fraction | None
    optimal_failure_probability: Fraction | None
    exact_normalized_regret: Fraction | None
    optimal_policy_signature: tuple[
        tuple[str, int, tuple[int, int, int]],
        ...,
    ]
    envelope_miss_axes: tuple[str, ...]
    partitions: tuple[V075BatchLiftBranchPartitionV1, ...]
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.lineage_id, "candidate lineage")
        _cid(self.exact_replay_id, "candidate exact replay")
        if (
            self._issuer is not _CANDIDATE_ISSUER
            or type(self.status) is not V075BatchTotalLiftConstructionStatusV1
            or any(
                type(item) is not Fraction
                for item in (
                    self.selected_expected_reward,
                    self.environment_failure_probability,
                    self.policy_abort_failure_probability,
                    self.selected_failure_probability,
                )
            )
            or self.selected_expected_reward < 0
            or self.selected_failure_probability
            != (
                self.environment_failure_probability
                + self.policy_abort_failure_probability
            )
            or not 0 <= self.selected_failure_probability <= 1
            or type(self.optimal_policy_signature) is not tuple
            or type(self.envelope_miss_axes) is not tuple
            or self.envelope_miss_axes
            != tuple(sorted(set(self.envelope_miss_axes)))
            or type(self.partitions) is not tuple
            or not self.partitions
            or any(
                type(item) is not V075BatchLiftBranchPartitionV1
                for item in self.partitions
            )
        ):
            _fail("batch-native construction candidate is malformed")
        optional = (
            self.optimal_expected_reward,
            self.optimal_failure_probability,
            self.exact_normalized_regret,
        )
        if any(item is None for item in optional) and not all(
            item is None for item in optional
        ):
            _fail("ground optimum fields are only partially present")
        if self.optimal_expected_reward is None:
            if self.optimal_policy_signature:
                _fail("infeasible ground query cannot carry a policy")
        else:
            assert self.optimal_failure_probability is not None
            assert self.exact_normalized_regret is not None
            if (
                type(self.optimal_expected_reward) is not Fraction
                or type(self.optimal_failure_probability) is not Fraction
                or type(self.exact_normalized_regret) is not Fraction
                or not self.optimal_policy_signature
            ):
                _fail("exact ground optimum is malformed")
        object.__setattr__(
            self,
            "_candidate_id",
            _hash("candidate", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_batch_native_total_lift_"
                "construction_candidate.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "lineage_id": self.lineage_id,
            "exact_replay_id": self.exact_replay_id,
            "status": self.status.value,
            "selected_expected_reward": _fdoc(
                self.selected_expected_reward
            ),
            "environment_failure_probability": _fdoc(
                self.environment_failure_probability
            ),
            "policy_abort_failure_probability": _fdoc(
                self.policy_abort_failure_probability
            ),
            "selected_failure_probability": _fdoc(
                self.selected_failure_probability
            ),
            "optimal_expected_reward": (
                None
                if self.optimal_expected_reward is None
                else _fdoc(self.optimal_expected_reward)
            ),
            "optimal_failure_probability": (
                None
                if self.optimal_failure_probability is None
                else _fdoc(self.optimal_failure_probability)
            ),
            "exact_normalized_regret": (
                None
                if self.exact_normalized_regret is None
                else _fdoc(self.exact_normalized_regret)
            ),
            "optimal_policy_signature": [
                {
                    "state_id": state_id,
                    "remaining_horizon": horizon,
                    "ground_action": list(action),
                }
                for state_id, horizon, action
                in self.optimal_policy_signature
            ],
            "envelope_miss_axes": list(self.envelope_miss_axes),
            "branch_partition_ids": [
                item.partition_id for item in self.partitions
            ],
            "h1_other_is_policy_abort": True,
            "exact_environment_failure_preserved": True,
            "construction_control_only": True,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def candidate_id(self) -> str:
        return self._candidate_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "partitions": [item.to_document() for item in self.partitions],
            "candidate_id": self.candidate_id,
        }


@dataclass(frozen=True, slots=True)
class _V075BatchNativeTotalLiftMetricsV1:
    outcome: _V075BatchTotalLiftExactOutcomeV1
    selected_expected_reward: Fraction
    environment_failure_probability: Fraction
    policy_abort_failure_probability: Fraction
    selected_failure_probability: Fraction
    optimal_expected_reward: Fraction | None
    optimal_failure_probability: Fraction | None
    exact_normalized_regret: Fraction | None
    optimal_policy_signature: tuple[
        tuple[str, int, tuple[int, int, int]],
        ...,
    ]
    envelope_miss_axes: tuple[str, ...]
    partitions: tuple[V075BatchLiftBranchPartitionV1, ...]


def _derive_total_lift_metrics(
    *,
    lineage: V075BatchNativeLineageBindingV1,
    exact_rows_input: tuple[exact_authority.V075ExactReplayRowV1, ...],
) -> _V075BatchNativeTotalLiftMetricsV1:
    if (
        type(lineage) is not V075BatchNativeLineageBindingV1
        or type(exact_rows_input) is not tuple
        or not exact_rows_input
        or any(
            type(item) is not exact_authority.V075ExactReplayRowV1
            for item in exact_rows_input
        )
    ):
        _fail("batch-native exact lift inputs are untyped or incomplete")
    policy_binding = lineage.envelope.policy
    policy = policy_binding.policy
    model = policy_binding.model
    exact_rows = _exact_rows_by_key(exact_rows_input)
    observed_by_id = {item.row_id: item for item in model.rows}
    support_by_key = {
        (
            item.source_state_id,
            item.remaining_horizon,
            item.ground_action,
            item.statistical_row_id,
        ): item
        for item in policy_binding.selected_row_supports
    }
    choice_by_state_horizon: dict[
        tuple[str, int],
        planners.V075PolicyStateChoiceV1,
    ] = {}
    for decision in policy.decisions:
        for choice in decision.state_choices:
            key = (choice.state_id, decision.remaining_horizon)
            if key in choice_by_state_horizon:
                _fail("selected policy repeats one state-time decision")
            choice_by_state_horizon[key] = choice
    root = graph.root_catalogue_v1(model.context)
    root_choice = choice_by_state_horizon.get((root.state.state_id, 2))
    if root_choice is None:
        _fail("selected policy lacks the actual root decision")
    selected_reward = Fraction(0)
    environment_failure = Fraction(0)
    policy_abort = Fraction(0)
    partitions: list[V075BatchLiftBranchPartitionV1] = []

    def evaluate_row(
        *,
        source_state_id: str,
        remaining_horizon: int,
        action: tuple[int, int, int],
        statistical_row_id: str,
        execution_weight: Fraction,
    ) -> tuple[
        exact_authority.V075ExactReplayRowV1,
        dict[str, tuple[Any, Fraction]],
    ]:
        nonlocal selected_reward, environment_failure, policy_abort
        observed = observed_by_id.get(statistical_row_id)
        support = support_by_key.get(
            (
                source_state_id,
                remaining_horizon,
                action,
                statistical_row_id,
            )
        )
        if (
            observed is None
            or support is None
            or observed.action != action
            or observed.row_binding.state_id != source_state_id
            or observed.row_binding.remaining_horizon != remaining_horizon
        ):
            _fail("selected row support does not match its ground action")
        exact_row = _exact_row(
            exact_rows,
            source_state_id,
            remaining_horizon,
            action,
        )
        selected_reward += execution_weight * exact_row.reward
        (
            environment_ids,
            modeled_ids,
            abort_ids,
            recurse,
        ) = _partition_exact_row_atoms(
            exact_row=exact_row,
            modeled_outcome_keys=support.modeled_outcome_keys,
        )
        atom_probability = {
            item.atom_id: item.atom.probability for item in exact_row.atoms
        }
        environment_failure += execution_weight * sum(
            (atom_probability[item] for item in environment_ids),
            Fraction(0),
        )
        policy_abort += execution_weight * sum(
            (atom_probability[item] for item in abort_ids),
            Fraction(0),
        )
        partitions.append(
            V075BatchLiftBranchPartitionV1(
                source_state_id,
                remaining_horizon,
                action,
                statistical_row_id,
                exact_row.row_id,
                execution_weight,
                tuple(
                    (item.atom_id, item.atom.probability)
                    for item in exact_row.atoms
                ),
                tuple(sorted(environment_ids)),
                tuple(sorted(modeled_ids)),
                tuple(sorted(abort_ids)),
            )
        )
        return exact_row, recurse

    for root_action, root_row_id, root_weight in zip(
        root_choice.ground_actions,
        root_choice.row_ids,
        root_choice.uniform_weights,
        strict=True,
    ):
        _root_row, recurse = evaluate_row(
            source_state_id=root.state.state_id,
            remaining_horizon=2,
            action=root_action,
            statistical_row_id=root_row_id,
            execution_weight=root_weight,
        )
        for child_state_id in sorted(recurse):
            _child_state, branch_probability = recurse[child_state_id]
            child_choice = choice_by_state_horizon.get((child_state_id, 1))
            if child_choice is None:
                _fail("modeled selected root child lacks its policy decision")
            for child_action, child_row_id, child_weight in zip(
                child_choice.ground_actions,
                child_choice.row_ids,
                child_choice.uniform_weights,
                strict=True,
            ):
                evaluate_row(
                    source_state_id=child_state_id,
                    remaining_horizon=1,
                    action=child_action,
                    statistical_row_id=child_row_id,
                    execution_weight=(
                        root_weight
                        * branch_probability
                        * child_weight
                    ),
                )
    selected_failure = environment_failure + policy_abort
    thresholds = model.backend_result.request.threshold_profile
    optimum = _exact_ground_optimum(
        context=model.context,
        rows=exact_rows_input,
        risk_tolerance=thresholds.risk_tolerance,
    )
    if optimum is None:
        optimal_reward = None
        optimal_failure = None
        normalized_regret = None
        optimal_signature = ()
    else:
        optimal_reward = optimum.reward
        optimal_failure = optimum.failure
        normalized_regret = (
            optimal_reward - selected_reward
        ) / thresholds.reward_ceiling
        optimal_signature = optimum.policy_signature
    envelope = lineage.envelope.learned_envelope
    misses = []
    if selected_reward < envelope.selected_reward_lower:
        misses.append("SELECTED_REWARD_LOWER")
    if selected_reward > envelope.selected_reward_upper:
        misses.append("SELECTED_REWARD_UPPER")
    if selected_reward > envelope.unrestricted_reward_upper:
        misses.append("UNRESTRICTED_REWARD_UPPER")
    if selected_failure > envelope.selected_failure_upper:
        misses.append("SELECTED_FAILURE_UPPER")
    if (
        normalized_regret is not None
        and normalized_regret > envelope.normalized_regret_upper
    ):
        misses.append("NORMALIZED_REGRET_UPPER")
    if misses:
        outcome = (
            _V075BatchTotalLiftExactOutcomeV1.STATISTICAL_ENVELOPE_MISS
        )
    elif optimum is None:
        outcome = (
            _V075BatchTotalLiftExactOutcomeV1
            .EXACT_GROUND_QUERY_INFEASIBLE
        )
    elif selected_failure > thresholds.risk_tolerance:
        outcome = (
            _V075BatchTotalLiftExactOutcomeV1.EXACT_POLICY_RISK_FAILURE
        )
    elif (
        normalized_regret is None
        or normalized_regret > thresholds.normalized_regret_tolerance
    ):
        outcome = (
            _V075BatchTotalLiftExactOutcomeV1.EXACT_POLICY_REGRET_FAILURE
        )
    else:
        outcome = _V075BatchTotalLiftExactOutcomeV1.EXACT_POSITIVE
    return _V075BatchNativeTotalLiftMetricsV1(
        outcome,
        selected_reward,
        environment_failure,
        policy_abort,
        selected_failure,
        optimal_reward,
        optimal_failure,
        normalized_regret,
        optimal_signature,
        tuple(sorted(misses)),
        tuple(
            sorted(
                partitions,
                key=lambda item: (
                    -item.remaining_horizon,
                    item.source_state_id,
                    item.ground_action,
                ),
            )
        ),
    )


def _derive_candidate(
    *,
    lineage: V075BatchNativeLineageBindingV1,
    exact_replay: V075BatchNativeConstructionExactReplayV1,
) -> V075BatchNativeConstructionTotalLiftCandidateV1:
    if (
        type(lineage) is not V075BatchNativeLineageBindingV1
        or type(exact_replay)
        is not V075BatchNativeConstructionExactReplayV1
        or exact_replay.lineage_id != lineage.lineage_id
        or lineage.sealed_lifecycle.closure.scope
        is not lifecycle.V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY
        or lineage.model.backend_result.request.authority_scope
        is not batched.V075BatchAuthorityScopeV1.CONSTRUCTION_ONLY
    ):
        _fail(
            "construction candidate requires exact construction lineage "
            "and replay types"
        )
    metrics = _derive_total_lift_metrics(
        lineage=lineage,
        exact_rows_input=exact_replay.rows,
    )
    status = {
        _V075BatchTotalLiftExactOutcomeV1.EXACT_POSITIVE: (
            V075BatchTotalLiftConstructionStatusV1
            .EXACT_POSITIVE_CONSTRUCTION_CONTROL
        ),
        _V075BatchTotalLiftExactOutcomeV1.EXACT_POLICY_RISK_FAILURE: (
            V075BatchTotalLiftConstructionStatusV1
            .EXACT_POLICY_RISK_FAILURE
        ),
        _V075BatchTotalLiftExactOutcomeV1.EXACT_POLICY_REGRET_FAILURE: (
            V075BatchTotalLiftConstructionStatusV1
            .EXACT_POLICY_REGRET_FAILURE
        ),
        _V075BatchTotalLiftExactOutcomeV1.EXACT_GROUND_QUERY_INFEASIBLE: (
            V075BatchTotalLiftConstructionStatusV1
            .EXACT_GROUND_QUERY_INFEASIBLE
        ),
        _V075BatchTotalLiftExactOutcomeV1.STATISTICAL_ENVELOPE_MISS: (
            V075BatchTotalLiftConstructionStatusV1
            .STATISTICAL_ENVELOPE_MISS
        ),
    }[metrics.outcome]
    return V075BatchNativeConstructionTotalLiftCandidateV1(
        _CANDIDATE_ISSUER,
        lineage.lineage_id,
        exact_replay.replay_id,
        status,
        metrics.selected_expected_reward,
        metrics.environment_failure_probability,
        metrics.policy_abort_failure_probability,
        metrics.selected_failure_probability,
        metrics.optimal_expected_reward,
        metrics.optimal_failure_probability,
        metrics.exact_normalized_regret,
        metrics.optimal_policy_signature,
        metrics.envelope_miss_axes,
        metrics.partitions,
    )


_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchNativeConstructionTotalLiftVerificationV1:
    _issuer: object = field(repr=False, compare=False)
    candidate: V075BatchNativeConstructionTotalLiftCandidateV1
    independently_recomputed_candidate_id: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(
            self.independently_recomputed_candidate_id,
            "recomputed construction candidate",
        )
        if (
            self._issuer is not _VERIFICATION_ISSUER
            or type(self.candidate)
            is not V075BatchNativeConstructionTotalLiftCandidateV1
            or self.independently_recomputed_candidate_id
            != self.candidate.candidate_id
        ):
            _fail("construction total-lift verification was caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_batch_native_total_lift_"
                "construction_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "candidate_id": self.candidate.candidate_id,
            "independently_recomputed_candidate_id": (
                self.independently_recomputed_candidate_id
            ),
            "verification_result": "EXACT_RECOMPUTATION_MATCH",
            "canonical_backend_recomputed": False,
            "canonical_planner_recomputed": False,
            "construction_control_only": True,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def evaluate_v075_batch_native_construction_total_lift_v1(
    *,
    lineage: V075BatchNativeLineageBindingV1,
    exact_replay: V075BatchNativeConstructionExactReplayV1,
) -> V075BatchNativeConstructionTotalLiftVerificationV1:
    candidate = _derive_candidate(
        lineage=lineage,
        exact_replay=exact_replay,
    )
    return V075BatchNativeConstructionTotalLiftVerificationV1(
        _VERIFICATION_ISSUER,
        candidate,
        candidate.candidate_id,
    )


def verify_v075_batch_native_construction_total_lift_candidate_v1(
    *,
    lineage: V075BatchNativeLineageBindingV1,
    exact_replay: V075BatchNativeConstructionExactReplayV1,
    claimed: V075BatchNativeConstructionTotalLiftCandidateV1,
) -> V075BatchNativeConstructionTotalLiftVerificationV1:
    if (
        type(claimed)
        is not V075BatchNativeConstructionTotalLiftCandidateV1
    ):
        _fail("independent verifier rejects duck-typed candidates")
    expected = _derive_candidate(
        lineage=lineage,
        exact_replay=exact_replay,
    )
    if claimed != expected or claimed.candidate_id != expected.candidate_id:
        _fail("batch-native total-lift candidate differs from recomputation")
    return V075BatchNativeConstructionTotalLiftVerificationV1(
        _VERIFICATION_ISSUER,
        expected,
        expected.candidate_id,
    )


_PRODUCTION_CANDIDATE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchNativeProductionTotalLiftCandidateV1:
    """Private production replay result, not a campaign certificate."""

    _issuer: object = field(repr=False, compare=False)
    lineage_id: str
    exact_replay_id: str
    observer_open_authorization_id: str
    multistage_closure_id: str
    underlying_closure_verification_id: str
    status: V075BatchTotalLiftProductionStatusV1
    selected_expected_reward: Fraction
    environment_failure_probability: Fraction
    policy_abort_failure_probability: Fraction
    selected_failure_probability: Fraction
    optimal_expected_reward: Fraction | None
    optimal_failure_probability: Fraction | None
    exact_normalized_regret: Fraction | None
    optimal_policy_signature: tuple[
        tuple[str, int, tuple[int, int, int]],
        ...,
    ]
    envelope_miss_axes: tuple[str, ...]
    partitions: tuple[V075BatchLiftBranchPartitionV1, ...] = field(
        repr=False
    )
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.lineage_id, "production candidate lineage"),
            (self.exact_replay_id, "production candidate exact replay"),
            (
                self.observer_open_authorization_id,
                "production candidate observer-open authorization",
            ),
            (
                self.multistage_closure_id,
                "production candidate multistage closure",
            ),
            (
                self.underlying_closure_verification_id,
                "production candidate underlying closure verification",
            ),
        ):
            _cid(value, label)
        if (
            self._issuer is not _PRODUCTION_CANDIDATE_ISSUER
            or type(self.status)
            is not V075BatchTotalLiftProductionStatusV1
            or any(
                type(item) is not Fraction
                for item in (
                    self.selected_expected_reward,
                    self.environment_failure_probability,
                    self.policy_abort_failure_probability,
                    self.selected_failure_probability,
                )
            )
            or self.selected_expected_reward < 0
            or self.selected_failure_probability
            != (
                self.environment_failure_probability
                + self.policy_abort_failure_probability
            )
            or not 0 <= self.selected_failure_probability <= 1
            or type(self.optimal_policy_signature) is not tuple
            or type(self.envelope_miss_axes) is not tuple
            or self.envelope_miss_axes
            != tuple(sorted(set(self.envelope_miss_axes)))
            or type(self.partitions) is not tuple
            or not self.partitions
            or any(
                type(item) is not V075BatchLiftBranchPartitionV1
                for item in self.partitions
            )
        ):
            _fail("batch-native production candidate is malformed")
        optional = (
            self.optimal_expected_reward,
            self.optimal_failure_probability,
            self.exact_normalized_regret,
        )
        if any(item is None for item in optional) and not all(
            item is None for item in optional
        ):
            _fail("production ground optimum fields are partially present")
        if self.optimal_expected_reward is None:
            if self.optimal_policy_signature:
                _fail("infeasible production query cannot carry a policy")
        else:
            assert self.optimal_failure_probability is not None
            assert self.exact_normalized_regret is not None
            if (
                type(self.optimal_expected_reward) is not Fraction
                or type(self.optimal_failure_probability) is not Fraction
                or type(self.exact_normalized_regret) is not Fraction
                or not self.optimal_policy_signature
            ):
                _fail("production exact ground optimum is malformed")
        object.__setattr__(
            self,
            "_candidate_id",
            _hash("production_candidate", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_batch_native_total_lift_"
                "production_candidate.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "lineage_id": self.lineage_id,
            "exact_replay_id": self.exact_replay_id,
            "observer_open_authorization_id": (
                self.observer_open_authorization_id
            ),
            "multistage_closure_id": self.multistage_closure_id,
            "underlying_closure_verification_id": (
                self.underlying_closure_verification_id
            ),
            "status": self.status.value,
            "selected_expected_reward": _fdoc(
                self.selected_expected_reward
            ),
            "environment_failure_probability": _fdoc(
                self.environment_failure_probability
            ),
            "policy_abort_failure_probability": _fdoc(
                self.policy_abort_failure_probability
            ),
            "selected_failure_probability": _fdoc(
                self.selected_failure_probability
            ),
            "optimal_expected_reward": (
                None
                if self.optimal_expected_reward is None
                else _fdoc(self.optimal_expected_reward)
            ),
            "optimal_failure_probability": (
                None
                if self.optimal_failure_probability is None
                else _fdoc(self.optimal_failure_probability)
            ),
            "exact_normalized_regret": (
                None
                if self.exact_normalized_regret is None
                else _fdoc(self.exact_normalized_regret)
            ),
            "optimal_policy_signature": [
                {
                    "state_id": state_id,
                    "remaining_horizon": horizon,
                    "ground_action": list(action),
                }
                for state_id, horizon, action
                in self.optimal_policy_signature
            ],
            "envelope_miss_axes": list(self.envelope_miss_axes),
            "branch_partition_ids": [
                item.partition_id for item in self.partitions
            ],
            "scope": "PRODUCTION_INDEPENDENT_REPLAY",
            "h1_other_is_policy_abort": True,
            "exact_environment_failure_preserved": True,
            "row_specific_partition_semantics": True,
            "exact_atom_payload_serialized": False,
            "production_candidate_only": True,
            "production_worker_integration_complete": False,
            "campaign_reconciliation_complete": False,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def candidate_id(self) -> str:
        return self._candidate_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "candidate_id": self.candidate_id}


def _require_production_exact_lift_inputs(
    *,
    lineage: V075BatchNativeLineageBindingV1,
    exact_replay: V075BatchNativeProductionExactReplayV1,
) -> None:
    if (
        type(lineage) is not V075BatchNativeLineageBindingV1
        or type(exact_replay)
        is not V075BatchNativeProductionExactReplayV1
        or exact_replay.lineage_id != lineage.lineage_id
    ):
        _fail(
            "production total lift requires exact production lineage and "
            "replay types"
        )
    sealed = lineage.sealed_lifecycle
    request = lineage.model.backend_result.request
    binding = request.batches[0].request.observer_open_binding
    expected_private_replays = tuple(
        sorted(item.verification_id for item in lineage.private_replays)
    )
    if (
        sealed.closure.scope
        is not lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION
        or request.authority_scope
        is not batched.V075BatchAuthorityScopeV1.PRODUCTION_OPEN
        or binding.scope
        is not observer.V075ObserverOpenAuthorityScopeV1.PRODUCTION_OPEN
        or not binding.independent_final_authority_verified
        or not binding.observer_open_authorized
        or exact_replay.observer_open_authorization_id
        != binding.upstream_authority_id
        or exact_replay.multistage_closure_id
        != sealed.closure.closure_id
        or exact_replay.underlying_closure_verification_id
        != sealed.underlying_closure_verification.verification_id
        or exact_replay.private_replay_verification_ids
        != expected_private_replays
    ):
        _fail(
            "production replay was transplanted across authorization, "
            "lifecycle, closure, or private replay lineage"
        )


def _derive_production_candidate(
    *,
    lineage: V075BatchNativeLineageBindingV1,
    exact_replay: V075BatchNativeProductionExactReplayV1,
) -> V075BatchNativeProductionTotalLiftCandidateV1:
    _require_production_exact_lift_inputs(
        lineage=lineage,
        exact_replay=exact_replay,
    )
    metrics = _derive_total_lift_metrics(
        lineage=lineage,
        exact_rows_input=exact_replay.rows,
    )
    status = {
        _V075BatchTotalLiftExactOutcomeV1.EXACT_POSITIVE: (
            V075BatchTotalLiftProductionStatusV1
            .EXACT_POSITIVE_PRODUCTION_CANDIDATE
        ),
        _V075BatchTotalLiftExactOutcomeV1.EXACT_POLICY_RISK_FAILURE: (
            V075BatchTotalLiftProductionStatusV1.EXACT_POLICY_RISK_FAILURE
        ),
        _V075BatchTotalLiftExactOutcomeV1.EXACT_POLICY_REGRET_FAILURE: (
            V075BatchTotalLiftProductionStatusV1
            .EXACT_POLICY_REGRET_FAILURE
        ),
        _V075BatchTotalLiftExactOutcomeV1.EXACT_GROUND_QUERY_INFEASIBLE: (
            V075BatchTotalLiftProductionStatusV1
            .EXACT_GROUND_QUERY_INFEASIBLE
        ),
        _V075BatchTotalLiftExactOutcomeV1.STATISTICAL_ENVELOPE_MISS: (
            V075BatchTotalLiftProductionStatusV1
            .STATISTICAL_ENVELOPE_MISS
        ),
    }[metrics.outcome]
    return V075BatchNativeProductionTotalLiftCandidateV1(
        _PRODUCTION_CANDIDATE_ISSUER,
        lineage.lineage_id,
        exact_replay.replay_id,
        exact_replay.observer_open_authorization_id,
        exact_replay.multistage_closure_id,
        exact_replay.underlying_closure_verification_id,
        status,
        metrics.selected_expected_reward,
        metrics.environment_failure_probability,
        metrics.policy_abort_failure_probability,
        metrics.selected_failure_probability,
        metrics.optimal_expected_reward,
        metrics.optimal_failure_probability,
        metrics.exact_normalized_regret,
        metrics.optimal_policy_signature,
        metrics.envelope_miss_axes,
        metrics.partitions,
    )


_PRODUCTION_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchNativeProductionTotalLiftResultV1:
    _issuer: object = field(repr=False, compare=False)
    candidate: V075BatchNativeProductionTotalLiftCandidateV1
    independently_recomputed_candidate_id: str
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(
            self.independently_recomputed_candidate_id,
            "recomputed production total-lift candidate",
        )
        if (
            self._issuer is not _PRODUCTION_RESULT_ISSUER
            or type(self.candidate)
            is not V075BatchNativeProductionTotalLiftCandidateV1
            or self.independently_recomputed_candidate_id
            != self.candidate.candidate_id
        ):
            _fail("production total-lift result was caller-minted")
        object.__setattr__(
            self,
            "_result_id",
            _hash("production_result", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_batch_native_total_lift_production_result.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "candidate_id": self.candidate.candidate_id,
            "candidate_status": self.candidate.status.value,
            "independently_recomputed_candidate_id": (
                self.independently_recomputed_candidate_id
            ),
            "verification_result": "EXACT_RECOMPUTATION_MATCH",
            "scope": "PRODUCTION_INDEPENDENT_REPLAY",
            "canonical_backend_recomputed": False,
            "canonical_planner_recomputed": False,
            "production_worker_result_id": None,
            "campaign_reconciliation_result_id": None,
            "production_worker_integration_complete": False,
            "campaign_reconciliation_complete": False,
            "production_total_lift_execution_allowed": False,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "candidate": self.candidate.to_document(),
            "result_id": self.result_id,
        }


def evaluate_v075_batch_native_production_total_lift_v1(
    *,
    lineage: V075BatchNativeLineageBindingV1,
    exact_replay: V075BatchNativeProductionExactReplayV1,
) -> V075BatchNativeProductionTotalLiftCandidateV1:
    """Issue one production-scope candidate; never an official endpoint."""

    return _derive_production_candidate(
        lineage=lineage,
        exact_replay=exact_replay,
    )


def _verify_exact_production_candidate_match(
    *,
    claimed: V075BatchNativeProductionTotalLiftCandidateV1,
    expected: V075BatchNativeProductionTotalLiftCandidateV1,
) -> V075BatchNativeProductionTotalLiftResultV1:
    if (
        type(claimed)
        is not V075BatchNativeProductionTotalLiftCandidateV1
        or type(expected)
        is not V075BatchNativeProductionTotalLiftCandidateV1
    ):
        _fail("production verifier rejects cross-scope or duck candidates")
    if claimed != expected or claimed.candidate_id != expected.candidate_id:
        _fail("production total-lift candidate differs from recomputation")
    return V075BatchNativeProductionTotalLiftResultV1(
        _PRODUCTION_RESULT_ISSUER,
        expected,
        expected.candidate_id,
    )


def verify_v075_batch_native_production_total_lift_candidate_v1(
    *,
    lineage: V075BatchNativeLineageBindingV1,
    exact_replay: V075BatchNativeProductionExactReplayV1,
    claimed: V075BatchNativeProductionTotalLiftCandidateV1,
) -> V075BatchNativeProductionTotalLiftResultV1:
    """Independently recompute every row-specific exact branch partition."""

    if (
        type(claimed)
        is not V075BatchNativeProductionTotalLiftCandidateV1
    ):
        _fail("production verifier rejects cross-scope or duck candidates")
    expected = _derive_production_candidate(
        lineage=lineage,
        exact_replay=exact_replay,
    )
    return _verify_exact_production_candidate_match(
        claimed=claimed,
        expected=expected,
    )


_READINESS_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchNativeTotalLiftProductionReadinessV1:
    _issuer: object = field(repr=False, compare=False)
    blockers: tuple[str, ...]
    required_lifecycle_closure_fields: tuple[str, ...]
    _readiness_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _READINESS_ISSUER
            or self.blockers != tuple(sorted(set(self.blockers)))
            or not self.blockers
            or self.required_lifecycle_closure_fields
            != REQUIRED_LIFECYCLE_CLOSURE_FIELDS
        ):
            _fail("batch-native production readiness is malformed")
        object.__setattr__(
            self,
            "_readiness_id",
            _hash("readiness", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_batch_native_total_lift_"
                "production_readiness.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "blockers": list(self.blockers),
            "required_lifecycle_phase_order": list(
                REQUIRED_LIFECYCLE_PHASE_ORDER
            ),
            "required_lifecycle_closure_fields": list(
                self.required_lifecycle_closure_fields
            ),
            "construction_multistage_e2e_gate_status": (
                CONSTRUCTION_E2E_GATE_STATUS
            ),
            "production_exact_replay_candidate_result_implemented": True,
            "production_worker_integration_complete": False,
            "campaign_reconciliation_complete": False,
            "legacy_single_lane_ipc_sufficient": False,
            "underlying_observer_journal_must_be_empty": True,
            "retrospective_support_freeze_allowed": False,
            "production_total_lift_execution_allowed": False,
            "official_execution_allowed": False,
        }

    @property
    def readiness_id(self) -> str:
        return self._readiness_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "readiness_id": self.readiness_id}


def assess_v075_batch_native_total_lift_production_readiness_v1(
) -> V075BatchNativeTotalLiftProductionReadinessV1:
    return V075BatchNativeTotalLiftProductionReadinessV1(
        _READINESS_ISSUER,
        tuple(
            sorted(
                (
                    PRODUCTION_RECONCILIATION_INTEGRATION_BLOCKER,
                    PRODUCTION_WORKER_INTEGRATION_BLOCKER,
                )
            )
        ),
        REQUIRED_LIFECYCLE_CLOSURE_FIELDS,
    )


__all__ = [
    "CANONICAL_BACKEND_RECOMPUTATION_IN_OPERATIONAL_BRIDGE",
    "CANONICAL_PLANNER_RECOMPUTATION_IN_OPERATIONAL_BRIDGE",
    "CONSTRUCTION_E2E_GATE_STATUS",
    "DOMAIN_TAGS",
    "PER_DRAW_CAPABILITY_EXPANSION_ALLOWED",
    "POLICY_ABORT_RULE",
    "PRODUCTION_RECONCILIATION_INTEGRATION_BLOCKER",
    "PRODUCTION_TOTAL_LIFT_EXECUTION_ALLOWED",
    "PRODUCTION_WORKER_INTEGRATION_BLOCKER",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUIRED_LIFECYCLE_CLOSURE_FIELDS",
    "REQUIRED_LIFECYCLE_PHASE_ORDER",
    "SCHEMA_VERSION",
    "V075BatchLiftBranchPartitionV1",
    "V075BatchNativeConstructionExactReplayV1",
    "V075BatchNativeConstructionTotalLiftCandidateV1",
    "V075BatchNativeConstructionTotalLiftVerificationV1",
    "V075BatchNativeEnvelopeBindingV1",
    "V075BatchNativeLineageBindingV1",
    "V075BatchNativeModelBindingV1",
    "V075BatchNativePolicyBindingV1",
    "V075BatchNativeProductionExactReplayV1",
    "V075BatchNativeProductionTotalLiftCandidateV1",
    "V075BatchNativeProductionTotalLiftResultV1",
    "V075BatchNativeTotalLiftInvariantViolation",
    "V075BatchNativeTotalLiftProductionReadinessV1",
    "V075BatchObservedRowBindingV1",
    "V075BatchSelectedRowSupportV1",
    "V075BatchTotalLiftConstructionStatusV1",
    "V075BatchTotalLiftProductionStatusV1",
    "assess_v075_batch_native_total_lift_production_readiness_v1",
    "evaluate_v075_batch_native_construction_total_lift_v1",
    "evaluate_v075_batch_native_production_total_lift_v1",
    "freeze_v075_batch_native_total_lift_lineage_v1",
    "mint_v075_batch_native_construction_exact_replay_v1",
    "mint_v075_batch_native_production_exact_replay_v1",
    "verify_v075_batch_native_construction_total_lift_candidate_v1",
    "verify_v075_batch_native_production_total_lift_candidate_v1",
]
