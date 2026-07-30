"""Deterministic dynamic-child closure intent authority for V0-075 V2.

This construction leaf consumes one exact schedule-bound planning result and
replays its complete repository/profile/slot/schedule/lineage/authority
chain.  It then derives every active non-``OTHER`` child state from signed
aggregate evidence, reconstructs the complete public action catalogue for
each distinct child state, and freezes discovery intents for every unresolved
child action row.

The leaf is intentionally an intent compiler only.  It performs no observer
or kernel access, launches no worker, appends no batch, freezes no support,
invokes no planner, and issues no certificate.  Child closure is a barrier
before adaptive promotion rounds and consumes zero promotion rounds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_batched_observer_authority_v2 as batched_v2
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition_v2
from acfqp import v075_preopen_target_authorization_v2 as preopen_v2
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_schedule_bound_acquisition_lifecycle_v2 as initial_v2
from acfqp import v075_schedule_bound_sound_planning_authority_v2 as bridge_v2


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.51.0"
PROFILE_KEY = "v075_dynamic_child_closure_intent_authority_v2"
MAX_CANONICAL_INPUT_BYTES = 64 * 1024 * 1024

MAXIMUM_DISTINCT_CHILD_ACTION_ROWS = 19
CHILD_DISCOVERY_DRAWS = 64
DISCOVERY_OBSERVER_EPOCH_INDEX = 0
FOLLOW_ON_VALIDATION_EPOCH_INDEX = 1

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
OBSERVER_ACCESS_ALLOWED = False
KERNEL_ACCESS_ALLOWED = False
WORKER_LAUNCH_ALLOWED = False
PROMOTION_ROUND_EXECUTION_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
PRODUCTION_BLOCKER = (
    "dynamic child closure is an unexecuted construction intent; signed "
    "batch execution, support freeze, validation, replanning, total lift, "
    "isolated IPC, and production occurrence authority are not integrated"
)

DOMAIN_TAGS = {
    "causal_edge": "acfqp:v075-dynamic-child-causal-edge:v2",
    "child_state": "acfqp:v075-dynamic-child-state-causal-binding:v2",
    "intent": "acfqp:v075-dynamic-child-discovery-intent:v2",
    "result": "acfqp:v075-dynamic-child-closure-intent-result:v2",
    "verification": (
        "acfqp:v075-dynamic-child-closure-intent-verification:v2"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 dynamic-child intent domains must be unique")


class V075DynamicChildClosureIntentV2InvariantViolation(ValueError):
    """An upstream witness, child closure, catalogue, cap, or byte was bad."""


class V075DynamicChildClosureIntentProductionV2NotReady(RuntimeError):
    """This construction intent cannot authorize production execution."""


def _fail(message: str) -> NoReturn:
    raise V075DynamicChildClosureIntentV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075DynamicChildClosureIntentV2InvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075DynamicChildClosureIntentV2InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _strict_document(raw: bytes, label: str) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > MAX_CANONICAL_INPUT_BYTES
    ):
        _fail(f"{label} bytes are absent or over cap")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075DynamicChildClosureIntentV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return document


class V075DynamicChildClosureIntentStatusV2(str, Enum):
    AUTHORIZED = "CHILD_CLOSURE_DISCOVERY_INTENTS_AUTHORIZED"
    ALREADY_COMPLETE = "CHILD_CLOSURE_ALREADY_COMPLETE"
    CHILD_ACTION_ROW_CAP_EXCEEDED = "CHILD_ACTION_ROW_CAP_EXCEEDED"
    CHILD_ACTION_CATALOGUE_NOT_YET_BOUND = (
        "CHILD_ACTION_CATALOGUE_NOT_YET_BOUND"
    )


_CHILD_STATE_ISSUER = object()
_CAUSAL_EDGE_ISSUER = object()
_INTENT_ISSUER = object()
_RESULT_ISSUER = object()
_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075DynamicChildCausalEdgeV2:
    """One non-flattened parent-evidence-child causal relation."""

    _issuer: object = field(repr=False, compare=False)
    child_state_id: str
    parent_row_binding_id: str
    numerical_row_id: str | None
    support_descriptor_id: str | None
    row_evidence_binding_id: str | None
    support_freeze_id: str | None
    discovery_batch_ids: tuple[str, ...]
    outcome_id: str | None
    _edge_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.child_state_id, "causal edge child"),
            (self.parent_row_binding_id, "causal edge parent row"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _CAUSAL_EDGE_ISSUER
            or type(self.discovery_batch_ids) is not tuple
            or not self.discovery_batch_ids
            or self.discovery_batch_ids
            != tuple(sorted(set(self.discovery_batch_ids)))
        ):
            _fail("dynamic child causal edge is malformed or caller-minted")
        for value in self.discovery_batch_ids:
            _cid(value, "causal edge discovery batch")
        adaptive = self.numerical_row_id is not None
        if adaptive:
            required = (
                self.numerical_row_id,
                self.support_descriptor_id,
                self.row_evidence_binding_id,
                self.support_freeze_id,
            )
            if self.outcome_id is not None or any(
                value is None for value in required
            ):
                _fail("adaptive child causal edge is incomplete")
            for value, label in zip(
                required,
                (
                    "causal edge numerical row",
                    "causal edge support descriptor",
                    "causal edge evidence binding",
                    "causal edge support freeze",
                ),
            ):
                _cid(value, label)
        else:
            if (
                self.support_descriptor_id is not None
                or self.row_evidence_binding_id is not None
                or self.support_freeze_id is not None
                or self.outcome_id is None
                or len(self.discovery_batch_ids) != 1
            ):
                _fail("direct child causal edge is incomplete")
            _cid(self.outcome_id, "causal edge direct outcome")
        object.__setattr__(
            self,
            "_edge_id",
            _hash("causal_edge", self._payload()),
        )

    @property
    def source_kind(self) -> str:
        return (
            "ADAPTIVE_SUPPORT_DESCRIPTOR"
            if self.numerical_row_id is not None
            else "DIRECT_DISCOVERY_OUTCOME"
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_dynamic_child_causal_edge.v2",
            "schema_version": SCHEMA_VERSION,
            "source_kind": self.source_kind,
            "child_state_id": self.child_state_id,
            "parent_row_binding_id": self.parent_row_binding_id,
            "numerical_row_id": self.numerical_row_id,
            "support_descriptor_id": self.support_descriptor_id,
            "row_evidence_binding_id": self.row_evidence_binding_id,
            "support_freeze_id": self.support_freeze_id,
            "discovery_batch_ids": list(self.discovery_batch_ids),
            "outcome_id": self.outcome_id,
            "relation_preserved_without_cartesian_flattening": True,
        }

    @property
    def edge_id(self) -> str:
        return self._edge_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "edge_id": self.edge_id}


@dataclass(frozen=True, slots=True)
class V075DynamicChildStateCausalBindingV2:
    """One deduplicated active child and its complete public action domain."""

    _issuer: object = field(repr=False, compare=False)
    state: graph.V075SymbolicGraphStateV1
    catalogue: graph.V075LegalActionCatalogueV1
    row_bindings: tuple[graph.V075ObservationRowBindingV1, ...]
    causal_edges: tuple[V075DynamicChildCausalEdgeV2, ...]
    already_modeled_action_row_ids: tuple[str, ...]
    unresolved_action_row_ids: tuple[str, ...]
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            expected_state = graph.V075SymbolicGraphStateV1(
                self.state.context,
                self.state.ranks,
                self.state.failure,
            )
            expected_catalogue = graph.V075LegalActionCatalogueV1(
                expected_state.context,
                expected_state,
                1,
                graph.legal_action_triples_v1(
                    expected_state.context,
                    expected_state.ranks,
                    expected_state.failure,
                ),
            )
            expected_rows = tuple(
                sorted(
                    (
                        graph.observation_row_binding_v1(
                            expected_catalogue.context,
                            expected_catalogue,
                            action,
                        )
                        for action in expected_catalogue.actions
                    ),
                    key=lambda item: item.row_binding_id,
                )
            )
        except (
            AttributeError,
            TypeError,
            graph.V075PublicGraphSemanticsInvariantViolation,
        ) as error:
            raise V075DynamicChildClosureIntentV2InvariantViolation(
                "dynamic child state semantic replay failed"
            ) from error
        if (
            self._issuer is not _CHILD_STATE_ISSUER
            or type(self.state) is not graph.V075SymbolicGraphStateV1
            or type(self.catalogue) is not graph.V075LegalActionCatalogueV1
            or self.state.failure
            or self.state.to_document() != expected_state.to_document()
            or self.catalogue.to_document()
            != expected_catalogue.to_document()
            or type(self.row_bindings) is not tuple
            or tuple(item.to_document() for item in self.row_bindings)
            != tuple(item.to_document() for item in expected_rows)
            or tuple(item.row_binding_id for item in self.row_bindings)
            != tuple(item.row_binding_id for item in expected_rows)
        ):
            _fail("dynamic child state catalogue is incomplete or caller-minted")
        if (
            type(self.causal_edges) is not tuple
            or not self.causal_edges
            or any(
                type(item) is not V075DynamicChildCausalEdgeV2
                or item.child_state_id != self.state.state_id
                for item in self.causal_edges
            )
            or self.causal_edges
            != tuple(sorted(self.causal_edges, key=lambda item: item.edge_id))
            or len({item.edge_id for item in self.causal_edges})
            != len(self.causal_edges)
        ):
            _fail("dynamic child causal edge registry is incomplete")
        all_row_ids = tuple(item.row_binding_id for item in self.row_bindings)
        for values, label in (
            (
                self.already_modeled_action_row_ids,
                "already modeled child row",
            ),
            (
                self.unresolved_action_row_ids,
                "unresolved child row",
            ),
        ):
            if (
                type(values) is not tuple
                or values != tuple(sorted(set(values)))
            ):
                _fail(f"{label} registry is duplicated, reordered, or empty")
            for value in values:
                _cid(value, label)
        if (
            set(self.already_modeled_action_row_ids)
            & set(self.unresolved_action_row_ids)
            or tuple(
                sorted(
                    (
                        *self.already_modeled_action_row_ids,
                        *self.unresolved_action_row_ids,
                    )
                )
            )
            != all_row_ids
            or len({item.source_kind for item in self.causal_edges}) != 1
        ):
            _fail("modeled/unresolved child row partition or causal mode changed")
        object.__setattr__(
            self,
            "_binding_id",
            _hash("child_state", self._payload()),
        )

    @property
    def causal_edge_ids(self) -> tuple[str, ...]:
        return tuple(item.edge_id for item in self.causal_edges)

    @property
    def causal_parent_row_binding_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted({item.parent_row_binding_id for item in self.causal_edges})
        )

    @property
    def causal_numerical_row_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    item.numerical_row_id
                    for item in self.causal_edges
                    if item.numerical_row_id is not None
                }
            )
        )

    @property
    def causal_support_descriptor_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    item.support_descriptor_id
                    for item in self.causal_edges
                    if item.support_descriptor_id is not None
                }
            )
        )

    @property
    def causal_discovery_batch_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    batch_id
                    for item in self.causal_edges
                    for batch_id in item.discovery_batch_ids
                }
            )
        )

    @property
    def causal_outcome_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    item.outcome_id
                    for item in self.causal_edges
                    if item.outcome_id is not None
                }
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_dynamic_child_state_causal_binding.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": self.state.context_id,
            "child_state_id": self.state.state_id,
            "child_ranks": list(self.state.ranks),
            "child_remaining_horizon": 1,
            "catalogue_id": self.catalogue.catalogue_id,
            "complete_action_row_ids": [
                item.row_binding_id for item in self.row_bindings
            ],
            "causal_edge_ids": list(self.causal_edge_ids),
            "causal_parent_row_binding_ids": list(
                self.causal_parent_row_binding_ids
            ),
            "causal_numerical_row_ids": list(
                self.causal_numerical_row_ids
            ),
            "causal_support_descriptor_ids": list(
                self.causal_support_descriptor_ids
            ),
            "causal_discovery_batch_ids": list(
                self.causal_discovery_batch_ids
            ),
            "causal_outcome_ids": list(self.causal_outcome_ids),
            "already_modeled_action_row_ids": list(
                self.already_modeled_action_row_ids
            ),
            "unresolved_action_row_ids": list(
                self.unresolved_action_row_ids
            ),
            "active_nonfailure_nonterminal_child": True,
            "complete_public_action_catalogue": True,
            "child_state_deduplicated_across_parents": True,
            "other_instantiated": False,
        }

    @property
    def binding_id(self) -> str:
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "state": self.state.to_document(),
            "catalogue": self.catalogue.to_document(),
            "row_bindings": [
                item.to_document() for item in self.row_bindings
            ],
            "causal_edges": [
                item.to_document() for item in self.causal_edges
            ],
            "binding_id": self.binding_id,
        }


@dataclass(frozen=True, slots=True)
class V075DynamicChildDiscoveryIntentV2:
    """One D64 discovery intent for one unresolved child action row."""

    _issuer: object = field(repr=False, compare=False)
    planning_result_id: str
    acquisition_profile_id: str
    occurrence_slot_id: str
    schedule_id: str
    lineage_id: str
    construction_authority_replay_id: str
    occurrence_id: str
    target_tape_namespace_id: str
    context_id: str
    arm: str
    child_binding_id: str
    child_state_id: str
    catalogue_id: str
    row_binding: graph.V075ObservationRowBindingV1
    causal_parent_row_binding_ids: tuple[str, ...]
    causal_edge_ids: tuple[str, ...]
    ordinal: int
    _intent_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.planning_result_id, "child intent planning result"),
            (self.acquisition_profile_id, "child intent profile"),
            (self.occurrence_slot_id, "child intent slot"),
            (self.schedule_id, "child intent schedule"),
            (self.lineage_id, "child intent lineage"),
            (
                self.construction_authority_replay_id,
                "child intent construction replay",
            ),
            (self.occurrence_id, "child intent occurrence"),
            (self.target_tape_namespace_id, "child intent tape"),
            (self.context_id, "child intent context"),
            (self.child_binding_id, "child intent binding"),
            (self.child_state_id, "child intent child state"),
            (self.catalogue_id, "child intent catalogue"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _INTENT_ISSUER
            or type(self.row_binding)
            is not graph.V075ObservationRowBindingV1
            or self.row_binding.context_id != self.context_id
            or self.row_binding.state_id != self.child_state_id
            or self.row_binding.catalogue_id != self.catalogue_id
            or type(self.ordinal) is not int
            or self.ordinal < 0
            or type(self.arm) is not str
        ):
            _fail("dynamic child discovery intent is malformed or caller-minted")
        for values, label in (
            (self.causal_parent_row_binding_ids, "intent causal parent"),
            (self.causal_edge_ids, "intent causal edge"),
        ):
            if (
                type(values) is not tuple
                or not values
                or values != tuple(sorted(set(values)))
            ):
                _fail(f"{label} registry is empty, duplicated, or reordered")
            for value in values:
                _cid(value, label)
        object.__setattr__(
            self,
            "_intent_id",
            _hash("intent", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_dynamic_child_discovery_intent.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "planning_result_id": self.planning_result_id,
            "acquisition_profile_id": self.acquisition_profile_id,
            "occurrence_slot_id": self.occurrence_slot_id,
            "schedule_id": self.schedule_id,
            "lineage_id": self.lineage_id,
            "construction_authority_replay_id": (
                self.construction_authority_replay_id
            ),
            "occurrence_id": self.occurrence_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "child_binding_id": self.child_binding_id,
            "child_state_id": self.child_state_id,
            "catalogue_id": self.catalogue_id,
            "row_binding_id": self.row_binding.row_binding_id,
            "action": list(self.row_binding.action),
            "ordinal": self.ordinal,
            "lane": "DISCOVERY",
            "observer_epoch_index": DISCOVERY_OBSERVER_EPOCH_INDEX,
            "follow_on_validation_epoch_index": (
                FOLLOW_ON_VALIDATION_EPOCH_INDEX
            ),
            "accepted_draw_start": 1,
            "accepted_draw_count": CHILD_DISCOVERY_DRAWS,
            "accepted_draw_end": CHILD_DISCOVERY_DRAWS,
            "accepted_draw_cap": CHILD_DISCOVERY_DRAWS,
            "causal_parent_row_binding_ids": list(
                self.causal_parent_row_binding_ids
            ),
            "causal_edge_ids": list(self.causal_edge_ids),
            "same_occurrence_and_target_tape": True,
            "child_closure_barrier": True,
            "promotion_round_index": None,
            "promotion_rounds_consumed": 0,
            "observer_executed": False,
            "batch_generated": False,
        }

    @property
    def intent_id(self) -> str:
        return self._intent_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_binding": self.row_binding.to_document(),
            "intent_id": self.intent_id,
        }


@dataclass(frozen=True, slots=True)
class V075DynamicChildClosureIntentResultV2:
    """Complete deterministic child-closure intent or typed noncertificate."""

    _issuer: object = field(repr=False, compare=False)
    planning_result: bridge_v2.V075ScheduleBoundSoundPlanningResultV2 = field(
        repr=False
    )
    child_states: tuple[V075DynamicChildStateCausalBindingV2, ...]
    intents: tuple[V075DynamicChildDiscoveryIntentV2, ...]
    status: V075DynamicChildClosureIntentStatusV2
    missing_authority_fields: tuple[str, ...]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _RESULT_ISSUER
            or type(self.planning_result)
            is not bridge_v2.V075ScheduleBoundSoundPlanningResultV2
            or type(self.status) is not V075DynamicChildClosureIntentStatusV2
            or self.child_states
            != tuple(
                sorted(
                    self.child_states,
                    key=lambda item: item.state.state_id,
                )
            )
            or any(
                type(item) is not V075DynamicChildStateCausalBindingV2
                for item in self.child_states
            )
            or self.intents
            != tuple(sorted(self.intents, key=lambda item: item.ordinal))
            or tuple(item.ordinal for item in self.intents)
            != tuple(range(len(self.intents)))
            or any(
                type(item) is not V075DynamicChildDiscoveryIntentV2
                for item in self.intents
            )
            or type(self.missing_authority_fields) is not tuple
            or self.missing_authority_fields
            != tuple(sorted(set(self.missing_authority_fields)))
        ):
            _fail("dynamic child closure result is malformed or caller-minted")
        unresolved_ids = tuple(
            sorted(
                row_id
                for child in self.child_states
                for row_id in child.unresolved_action_row_ids
            )
        )
        planning = self.planning_result
        try:
            expected_children, expected_missing = _child_state_bindings(
                planning
            )
        except Exception as error:
            if type(error) is V075DynamicChildClosureIntentV2InvariantViolation:
                raise
            raise V075DynamicChildClosureIntentV2InvariantViolation(
                "dynamic child semantic edge replay failed"
            ) from error
        if (
            tuple(item.to_document() for item in self.child_states)
            != tuple(item.to_document() for item in expected_children)
            or self.missing_authority_fields != expected_missing
        ):
            _fail(
                "child catalogue, causal edges, or missing authority differs "
                "from exact planning replay"
            )
        modeled_row_ids = (
            set()
            if planning.compiler_output is None
            else {
                item.row_binding_id
                for item in planning.compiler_output.model.rows
                if item.remaining_horizon == 1
            }
        )
        if (
            len(unresolved_ids) != len(set(unresolved_ids))
            or len({item.state.state_id for item in self.child_states})
            != len(self.child_states)
            or len({item.binding_id for item in self.child_states})
            != len(self.child_states)
        ):
            _fail("child state, binding, or action-row registry is duplicated")
        for child in self.child_states:
            complete = tuple(
                item.row_binding_id for item in child.row_bindings
            )
            expected_already = tuple(
                item for item in complete if item in modeled_row_ids
            )
            expected_unresolved = tuple(
                item for item in complete if item not in modeled_row_ids
            )
            if (
                child.already_modeled_action_row_ids != expected_already
                or child.unresolved_action_row_ids != expected_unresolved
            ):
                _fail(
                    "child modeled/unresolved partition differs from the "
                    "planning model"
                )
        authorized = (
            self.status is V075DynamicChildClosureIntentStatusV2.AUTHORIZED
        )
        cap_exceeded = self.status is (
            V075DynamicChildClosureIntentStatusV2
            .CHILD_ACTION_ROW_CAP_EXCEEDED
        )
        catalogue_missing = self.status is (
            V075DynamicChildClosureIntentStatusV2
            .CHILD_ACTION_CATALOGUE_NOT_YET_BOUND
        )
        if (
            authorized
            and (
                not unresolved_ids
                or len(unresolved_ids) > MAXIMUM_DISTINCT_CHILD_ACTION_ROWS
                or tuple(
                    item.row_binding.row_binding_id for item in self.intents
                )
                != unresolved_ids
                or self.missing_authority_fields
            )
        ):
            _fail("authorized child closure omitted or invented an action row")
        if (
            not authorized
            and self.intents
            or cap_exceeded
            != (len(unresolved_ids) > MAXIMUM_DISTINCT_CHILD_ACTION_ROWS)
            or (
                self.status
                is V075DynamicChildClosureIntentStatusV2.ALREADY_COMPLETE
            )
            != (not unresolved_ids and not self.missing_authority_fields)
            or catalogue_missing != bool(self.missing_authority_fields)
            or (
                catalogue_missing
                and unresolved_ids
            )
        ):
            _fail("child closure status, cap, or missing authority disagrees")
        schedule = planning.initial_lifecycle.schedule
        child_by_unresolved_row = {
            row.row_binding_id: (child, row)
            for child in self.child_states
            for row in child.row_bindings
            if row.row_binding_id in child.unresolved_action_row_ids
        }
        for intent in self.intents:
            expected_pair = child_by_unresolved_row.get(
                intent.row_binding.row_binding_id
            )
            if expected_pair is None:
                _fail("child discovery intent names no unresolved child row")
            expected_child, expected_row = expected_pair
            if (
                intent.planning_result_id != planning.result_id
                or intent.acquisition_profile_id
                != planning.initial_lifecycle.profile.profile_id
                or intent.occurrence_slot_id
                != planning.initial_lifecycle.expected_slot.slot_id
                or intent.schedule_id != schedule.schedule_id
                or intent.lineage_id
                != planning.initial_lifecycle.lineage.lineage_id
                or intent.construction_authority_replay_id
                != planning.initial_lifecycle.authority_replay.replay_id
                or intent.occurrence_id
                != schedule.occurrence.occurrence_id
                or intent.target_tape_namespace_id
                != schedule.occurrence.target_tape_namespace_id
                or intent.context_id != schedule.occurrence.context_id
                or intent.arm != schedule.occurrence.arm.value
                or intent.child_binding_id != expected_child.binding_id
                or intent.child_state_id != expected_child.state.state_id
                or intent.catalogue_id
                != expected_child.catalogue.catalogue_id
                or intent.row_binding != expected_row
                or intent.causal_parent_row_binding_ids
                != expected_child.causal_parent_row_binding_ids
                or intent.causal_edge_ids != expected_child.causal_edge_ids
            ):
                _fail(
                    "child discovery intent crossed an identity or causal "
                    "boundary"
                )
        object.__setattr__(
            self,
            "_result_id",
            _hash("result", self._payload()),
        )

    @property
    def unresolved_action_row_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                row_id
                for child in self.child_states
                for row_id in child.unresolved_action_row_ids
            )
        )

    def _payload(self) -> dict[str, Any]:
        planning = self.planning_result
        schedule = planning.initial_lifecycle.schedule
        direct = schedule.occurrence.arm is acquisition_v2.DIRECT_ARM
        return {
            "schema": (
                "acfqp.v075_dynamic_child_closure_intent_result.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": self.status.value,
            "planning_result_id": planning.result_id,
            "planning_terminal_code": planning.terminal_code.value,
            "acquisition_profile_id": (
                planning.initial_lifecycle.profile.profile_id
            ),
            "occurrence_slot_id": (
                planning.initial_lifecycle.expected_slot.slot_id
            ),
            "schedule_id": schedule.schedule_id,
            "lineage_id": planning.initial_lifecycle.lineage.lineage_id,
            "construction_authority_replay_id": (
                planning.initial_lifecycle.authority_replay.replay_id
            ),
            "occurrence_id": schedule.occurrence.occurrence_id,
            "target_tape_namespace_id": (
                schedule.occurrence.target_tape_namespace_id
            ),
            "context_id": schedule.occurrence.context_id,
            "arm": schedule.occurrence.arm.value,
            "route": (
                planning_v2.V075PlanningRouteV2.MATCHED_DIRECT_GROUND.value
                if direct
                else planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT.value
            ),
            "child_state_binding_ids": [
                item.binding_id for item in self.child_states
            ],
            "distinct_active_child_state_count": len(self.child_states),
            "unresolved_child_action_row_ids": list(
                self.unresolved_action_row_ids
            ),
            "distinct_unresolved_child_action_row_count": len(
                self.unresolved_action_row_ids
            ),
            "maximum_distinct_child_action_rows": (
                MAXIMUM_DISTINCT_CHILD_ACTION_ROWS
            ),
            "intent_ids": [item.intent_id for item in self.intents],
            "discovery_intent_count": len(self.intents),
            "missing_authority_fields": list(
                self.missing_authority_fields
            ),
            "cap_exceeded_without_subset_selection": self.status
            is (
                V075DynamicChildClosureIntentStatusV2
                .CHILD_ACTION_ROW_CAP_EXCEEDED
            ),
            "child_action_catalogues_reconstructed_from_public_graph": (
                not self.missing_authority_fields
            ),
            "caller_provided_candidate_list_used": False,
            "other_instantiated": False,
            "child_states_deduplicated_across_parents": True,
            "cap_counts_distinct_child_action_row_ids": True,
            "child_closure_is_pre_promotion_barrier": True,
            "maximum_adaptive_promotion_rounds": 2,
            "promotion_rounds_consumed": 0,
            "observer_access": False,
            "kernel_access": False,
            "worker_launches": 0,
            "batches_generated": 0,
            "lifecycle_generated": False,
            "planner_invocations": 0,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "planning_result": self.planning_result.to_document(),
            "child_states": [item.to_document() for item in self.child_states],
            "intents": [item.to_document() for item in self.intents],
            "result_id": self.result_id,
        }


@dataclass(frozen=True, slots=True)
class V075DynamicChildClosureIntentVerificationV2:
    _issuer: object = field(repr=False, compare=False)
    result_id: str
    planning_result_id: str
    planning_verification_id: str
    status: V075DynamicChildClosureIntentStatusV2
    child_state_count: int
    unresolved_action_row_count: int
    intent_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.result_id, "verified child closure result"),
            (self.planning_result_id, "verified planning result"),
            (self.planning_verification_id, "verified planning attestation"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _VERIFICATION_ISSUER
            or type(self.status) is not V075DynamicChildClosureIntentStatusV2
            or any(
                type(value) is not int or value < 0
                for value in (
                    self.child_state_count,
                    self.unresolved_action_row_count,
                    self.intent_count,
                )
            )
            or (
                self.status is V075DynamicChildClosureIntentStatusV2.AUTHORIZED
            )
            != (self.intent_count > 0)
        ):
            _fail("dynamic child closure verification is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_dynamic_child_closure_intent_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "result_id": self.result_id,
            "planning_result_id": self.planning_result_id,
            "planning_verification_id": self.planning_verification_id,
            "status": self.status.value,
            "child_state_count": self.child_state_count,
            "unresolved_action_row_count": (
                self.unresolved_action_row_count
            ),
            "intent_count": self.intent_count,
            "repository_schedule_replayed": True,
            "construction_authority_replayed": True,
            "initial_lifecycle_replayed": True,
            "schedule_bound_planning_replayed": True,
            "signed_aggregate_lineage_replayed": True,
            "complete_public_child_catalogues_replayed": self.status
            is not (
                V075DynamicChildClosureIntentStatusV2
                .CHILD_ACTION_CATALOGUE_NOT_YET_BOUND
            ),
            "typed_catalogue_authority_missing_verified": self.status
            is (
                V075DynamicChildClosureIntentStatusV2
                .CHILD_ACTION_CATALOGUE_NOT_YET_BOUND
            ),
            "canonical_result_bytes_replayed": True,
            "observer_access": False,
            "kernel_access": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


@dataclass(slots=True)
class _MutableChildCause:
    state: graph.V075SymbolicGraphStateV1
    edges: dict[str, V075DynamicChildCausalEdgeV2]


def _active_child_causes(
    planning: bridge_v2.V075ScheduleBoundSoundPlanningResultV2,
) -> tuple[_MutableChildCause, ...]:
    """Derive active children from model descriptors or signed root batches."""

    schedule = planning.initial_lifecycle.schedule
    context = next(
        (
            item
            for item in planning.initial_lifecycle.profile.namespace.family
            .replicate_contexts
            if item.context_id == schedule.occurrence.context_id
        ),
        None,
    )
    if context is None:
        _fail("planning occurrence context is absent from its exact profile")
    causes: dict[str, _MutableChildCause] = {}

    if planning.compiler_output is not None:
        evidence_by_row = {
            item.numerical_row_id: item
            for item in planning.compiler_output.evidence_bindings
        }
        for row in planning.compiler_output.model.rows:
            if row.remaining_horizon != 2:
                continue
            evidence = evidence_by_row.get(row.row_id)
            if evidence is None:
                _fail("adaptive model row lacks its discovery evidence binding")
            for descriptor in row.support:
                if descriptor.failure or descriptor.terminal:
                    continue
                try:
                    state = graph.V075SymbolicGraphStateV1(
                        context,
                        descriptor.next_ranks,
                        False,
                    )
                except graph.V075PublicGraphSemanticsInvariantViolation as error:
                    raise V075DynamicChildClosureIntentV2InvariantViolation(
                        "adaptive active child state is structurally invalid"
                    ) from error
                if state.state_id != descriptor.next_state_id:
                    _fail("adaptive support descriptor child identity changed")
                cause = causes.setdefault(
                    state.state_id,
                    _MutableChildCause(
                        state,
                        {},
                    ),
                )
                edge = V075DynamicChildCausalEdgeV2(
                    _CAUSAL_EDGE_ISSUER,
                    state.state_id,
                    row.row_binding_id,
                    row.row_id,
                    descriptor.descriptor_id,
                    evidence.binding_id,
                    evidence.support_freeze_id,
                    evidence.discovery_batch_ids,
                    None,
                )
                cause.edges[edge.edge_id] = edge
    else:
        lineage = planning.initial_lifecycle.lineage
        for batch in lineage.batches:
            row = batch.request.stream_identity.row_binding
            if (
                row.remaining_horizon != 2
                or batch.request.stream_identity.lane.value != "DISCOVERY"
            ):
                continue
            for outcome in batch.outcomes:
                if outcome.failure or outcome.terminal:
                    continue
                try:
                    state = graph.V075SymbolicGraphStateV1(
                        context,
                        outcome.next_ranks,
                        False,
                    )
                except graph.V075PublicGraphSemanticsInvariantViolation as error:
                    raise V075DynamicChildClosureIntentV2InvariantViolation(
                        "direct active child state is structurally invalid"
                    ) from error
                cause = causes.setdefault(
                    state.state_id,
                    _MutableChildCause(
                        state,
                        {},
                    ),
                )
                edge = V075DynamicChildCausalEdgeV2(
                    _CAUSAL_EDGE_ISSUER,
                    state.state_id,
                    row.row_binding_id,
                    None,
                    None,
                    None,
                    None,
                    (batch.batch_id,),
                    outcome.outcome_id,
                )
                cause.edges[edge.edge_id] = edge
    return tuple(causes[key] for key in sorted(causes))


def _complete_child_action_catalogue(
    state: graph.V075SymbolicGraphStateV1,
) -> tuple[
    graph.V075LegalActionCatalogueV1,
    tuple[graph.V075ObservationRowBindingV1, ...],
]:
    """Resolve the separately testable public child-action authority."""

    actions = graph.legal_action_triples_v1(
        state.context,
        state.ranks,
        state.failure,
    )
    catalogue = graph.V075LegalActionCatalogueV1(
        state.context,
        state,
        1,
        actions,
    )
    return (
        catalogue,
        tuple(
            sorted(
                (
                    graph.observation_row_binding_v1(
                        state.context,
                        catalogue,
                        action,
                    )
                    for action in catalogue.actions
                ),
                key=lambda item: item.row_binding_id,
            )
        ),
    )


def _child_state_bindings(
    planning: bridge_v2.V075ScheduleBoundSoundPlanningResultV2,
) -> tuple[
    tuple[V075DynamicChildStateCausalBindingV2, ...],
    tuple[str, ...],
]:
    modeled = (
        set()
        if planning.compiler_output is None
        else {
            item.row_binding_id
            for item in planning.compiler_output.model.rows
            if item.remaining_horizon == 1
        }
    )
    result: list[V075DynamicChildStateCausalBindingV2] = []
    for cause in _active_child_causes(planning):
        state = cause.state
        try:
            catalogue, rows = _complete_child_action_catalogue(state)
        except graph.V075PublicGraphSemanticsInvariantViolation:
            # Missing catalogue authority is a typed construction closure, not
            # permission to authorize the children successfully reconstructed
            # before this one.  The caller therefore receives no partial
            # bindings or intents.
            return (
                (),
                (
                    "complete_public_child_action_catalogue",
                ),
            )
        row_ids = tuple(item.row_binding_id for item in rows)
        already = tuple(item for item in row_ids if item in modeled)
        unresolved = tuple(item for item in row_ids if item not in modeled)
        result.append(
            V075DynamicChildStateCausalBindingV2(
                _CHILD_STATE_ISSUER,
                state,
                catalogue,
                rows,
                tuple(
                    cause.edges[key]
                    for key in sorted(cause.edges)
                ),
                already,
                unresolved,
            )
        )
    return (
        tuple(sorted(result, key=lambda item: item.state.state_id)),
        (),
    )


def _replay_planning(
    *,
    repository_root: str | Path,
    profile: acquisition_v2.V075FiveArmAcquisitionProfileV2,
    expected_slot: acquisition_v2.V075PreregisteredOccurrenceSlotV2,
    schedule: acquisition_v2.V075InitialAcquisitionScheduleV2,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    construction_authority: preopen_v2.V075ObserverOpenAuthorizationV2,
    current_lifecycle: initial_v2.LifecycleWitnessV2,
    initial_lifecycle: (
        initial_v2.V075ScheduleBoundInitialAcquisitionLifecycleV2
    ),
    planning_result: bridge_v2.V075ScheduleBoundSoundPlanningResultV2,
) -> tuple[
    bridge_v2.V075ScheduleBoundSoundPlanningResultV2,
    bridge_v2.V075ScheduleBoundSoundPlanningVerificationV2,
]:
    if type(planning_result) is not (
        bridge_v2.V075ScheduleBoundSoundPlanningResultV2
    ):
        _fail("dynamic child closure requires one exact planning result")
    try:
        return bridge_v2.verify_v075_schedule_bound_sound_planning_result_bytes_v2(
            repository_root=repository_root,
            profile=profile,
            expected_slot=expected_slot,
            schedule=schedule,
            lineage=lineage,
            construction_authority=construction_authority,
            current_lifecycle=current_lifecycle,
            initial_lifecycle=initial_lifecycle,
            claimed_bytes=planning_result.canonical_bytes,
        )
    except Exception as error:
        if type(error) is V075DynamicChildClosureIntentV2InvariantViolation:
            raise
        raise V075DynamicChildClosureIntentV2InvariantViolation(
            "schedule-bound planning and upstream exact replay failed"
        ) from error


def freeze_v075_dynamic_child_closure_intent_authority_v2(
    *,
    repository_root: str | Path,
    profile: acquisition_v2.V075FiveArmAcquisitionProfileV2,
    expected_slot: acquisition_v2.V075PreregisteredOccurrenceSlotV2,
    schedule: acquisition_v2.V075InitialAcquisitionScheduleV2,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    construction_authority: preopen_v2.V075ObserverOpenAuthorizationV2,
    current_lifecycle: initial_v2.LifecycleWitnessV2,
    initial_lifecycle: (
        initial_v2.V075ScheduleBoundInitialAcquisitionLifecycleV2
    ),
    planning_result: bridge_v2.V075ScheduleBoundSoundPlanningResultV2,
) -> V075DynamicChildClosureIntentResultV2:
    """Replay all inputs and freeze, but do not execute, child discovery."""

    planning, _verification = _replay_planning(
        repository_root=repository_root,
        profile=profile,
        expected_slot=expected_slot,
        schedule=schedule,
        lineage=lineage,
        construction_authority=construction_authority,
        current_lifecycle=current_lifecycle,
        initial_lifecycle=initial_lifecycle,
        planning_result=planning_result,
    )
    direct = schedule.occurrence.arm is acquisition_v2.DIRECT_ARM
    if direct:
        if planning.terminal_code is not (
            bridge_v2.V075ScheduleBoundPlanningTerminalCodeV2
            .PLANNING_DEFERRED_AWAITING_CHILD_EXPANSION
        ):
            _fail("direct child closure did not follow typed planning deferral")
    elif planning.terminal_code not in {
        (
            bridge_v2.V075ScheduleBoundPlanningTerminalCodeV2
            .FAILED_FRONTIER_AWAITING_DYNAMIC_ACQUISITION
        ),
        (
            bridge_v2.V075ScheduleBoundPlanningTerminalCodeV2
            .CANDIDATE_AWAITING_INDEPENDENT_TOTAL_LIFT
        ),
    }:
        _fail("adaptive child closure followed an ineligible planning terminal")

    child_states, missing_authority_fields = _child_state_bindings(planning)
    unresolved = tuple(
        (child, row)
        for child in child_states
        for row in child.row_bindings
        if row.row_binding_id in child.unresolved_action_row_ids
    )
    if missing_authority_fields:
        status = (
            V075DynamicChildClosureIntentStatusV2
            .CHILD_ACTION_CATALOGUE_NOT_YET_BOUND
        )
        intents = ()
    elif not unresolved:
        status = V075DynamicChildClosureIntentStatusV2.ALREADY_COMPLETE
        intents: tuple[V075DynamicChildDiscoveryIntentV2, ...] = ()
    elif len(unresolved) > MAXIMUM_DISTINCT_CHILD_ACTION_ROWS:
        status = (
            V075DynamicChildClosureIntentStatusV2
            .CHILD_ACTION_ROW_CAP_EXCEEDED
        )
        intents = ()
    else:
        status = V075DynamicChildClosureIntentStatusV2.AUTHORIZED
        lifecycle = planning.initial_lifecycle
        intents = tuple(
            V075DynamicChildDiscoveryIntentV2(
                _INTENT_ISSUER,
                planning.result_id,
                lifecycle.profile.profile_id,
                lifecycle.expected_slot.slot_id,
                lifecycle.schedule.schedule_id,
                lifecycle.lineage.lineage_id,
                lifecycle.authority_replay.replay_id,
                lifecycle.schedule.occurrence.occurrence_id,
                lifecycle.schedule.occurrence.target_tape_namespace_id,
                lifecycle.schedule.occurrence.context_id,
                lifecycle.schedule.occurrence.arm.value,
                child.binding_id,
                child.state.state_id,
                child.catalogue.catalogue_id,
                row,
                child.causal_parent_row_binding_ids,
                child.causal_edge_ids,
                ordinal,
            )
            for ordinal, (child, row) in enumerate(
                sorted(
                    unresolved,
                    key=lambda item: item[1].row_binding_id,
                )
            )
        )
    return V075DynamicChildClosureIntentResultV2(
        _RESULT_ISSUER,
        planning,
        child_states,
        intents,
        status,
        missing_authority_fields,
    )


def verify_v075_dynamic_child_closure_intent_result_bytes_v2(
    *,
    repository_root: str | Path,
    profile: acquisition_v2.V075FiveArmAcquisitionProfileV2,
    expected_slot: acquisition_v2.V075PreregisteredOccurrenceSlotV2,
    schedule: acquisition_v2.V075InitialAcquisitionScheduleV2,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    construction_authority: preopen_v2.V075ObserverOpenAuthorizationV2,
    current_lifecycle: initial_v2.LifecycleWitnessV2,
    initial_lifecycle: (
        initial_v2.V075ScheduleBoundInitialAcquisitionLifecycleV2
    ),
    planning_result: bridge_v2.V075ScheduleBoundSoundPlanningResultV2,
    claimed_bytes: bytes,
) -> tuple[
    V075DynamicChildClosureIntentResultV2,
    V075DynamicChildClosureIntentVerificationV2,
]:
    """Rebuild the bridge, upstream chain, child closure, intents, and bytes."""

    document = _strict_document(
        claimed_bytes,
        "dynamic child closure intent result",
    )
    replayed_planning, planning_verification = _replay_planning(
        repository_root=repository_root,
        profile=profile,
        expected_slot=expected_slot,
        schedule=schedule,
        lineage=lineage,
        construction_authority=construction_authority,
        current_lifecycle=current_lifecycle,
        initial_lifecycle=initial_lifecycle,
        planning_result=planning_result,
    )
    expected = freeze_v075_dynamic_child_closure_intent_authority_v2(
        repository_root=repository_root,
        profile=profile,
        expected_slot=expected_slot,
        schedule=schedule,
        lineage=lineage,
        construction_authority=construction_authority,
        current_lifecycle=current_lifecycle,
        initial_lifecycle=initial_lifecycle,
        planning_result=replayed_planning,
    )
    if (
        set(document) != set(expected.to_document())
        or claimed_bytes != expected.canonical_bytes
    ):
        _fail("dynamic child closure differs from exact canonical byte replay")
    verification = V075DynamicChildClosureIntentVerificationV2(
        _VERIFICATION_ISSUER,
        expected.result_id,
        replayed_planning.result_id,
        planning_verification.verification_id,
        expected.status,
        len(expected.child_states),
        len(expected.unresolved_action_row_ids),
        len(expected.intents),
    )
    return expected, verification


def open_v075_production_dynamic_child_closure_intent_authority_v2(
    *_args: Any,
    **_kwargs: Any,
) -> NoReturn:
    """Remain structurally locked regardless of monkeypatched flags."""

    raise V075DynamicChildClosureIntentProductionV2NotReady(
        PRODUCTION_BLOCKER
    )


__all__ = [
    "CHILD_DISCOVERY_DRAWS",
    "DISCOVERY_OBSERVER_EPOCH_INDEX",
    "DOMAIN_TAGS",
    "FOLLOW_ON_VALIDATION_EPOCH_INDEX",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "KERNEL_ACCESS_ALLOWED",
    "MAXIMUM_DISTINCT_CHILD_ACTION_ROWS",
    "OBSERVER_ACCESS_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PROFILE_KEY",
    "PRODUCTION_AUTHORIZING",
    "PRODUCTION_BLOCKER",
    "PROMOTION_ROUND_EXECUTION_ALLOWED",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "TERMINAL_CLASS",
    "TERMINAL_SCOPE",
    "V075DynamicChildClosureIntentProductionV2NotReady",
    "V075DynamicChildClosureIntentResultV2",
    "V075DynamicChildClosureIntentStatusV2",
    "V075DynamicChildClosureIntentV2InvariantViolation",
    "V075DynamicChildClosureIntentVerificationV2",
    "V075DynamicChildCausalEdgeV2",
    "V075DynamicChildDiscoveryIntentV2",
    "V075DynamicChildStateCausalBindingV2",
    "WORKER_LAUNCH_ALLOWED",
    "freeze_v075_dynamic_child_closure_intent_authority_v2",
    "open_v075_production_dynamic_child_closure_intent_authority_v2",
    "verify_v075_dynamic_child_closure_intent_result_bytes_v2",
]
