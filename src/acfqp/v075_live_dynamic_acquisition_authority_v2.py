"""Exact construction authorities for live V0-075 child acquisition and promotion.

This module is deliberately downstream of an exact
``V075LiveIncrementalModelEpochV2``.  It performs no observer or kernel access.
It has two responsibilities:

* derive every active child exposed by the root numerical rows, reconstruct
  each child's complete public action catalogue, and freeze an all-or-none
  registry of D64 discovery intents plus their V8192 validation templates; and
* when a live proof failed, deterministically select at most one fully
  materialized frontier row for the next registered +2048 validation prefix.

The artifacts are semantic inputs for the observer-signed controller.  They do
not execute a draw.  A validation template is intentionally not executable
until a later observer-signed complete-support freeze provides its exact
epoch-1 stream and support-freeze ID.

All results remain construction-only.  In particular, a numerical candidate is
an early-stop decision awaiting independent total lift, never a plan
certificate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_live_incremental_model_authority_v2 as live_model
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.60.0"
PROFILE_KEY = "v075_live_dynamic_acquisition_authority_v2"
MAX_CANONICAL_INPUT_BYTES = 64 * 1024 * 1024

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
OBSERVER_ACCESS_ALLOWED = False
KERNEL_ACCESS_ALLOWED = False
WORKER_LAUNCH_ALLOWED = False

CHILD_DISCOVERY_DRAWS = 64
CHILD_VALIDATION_DRAWS = 8_192
PROMOTION_DRAWS = 2_048
MAXIMUM_NEW_CHILD_ACTION_ROWS = 19
MAXIMUM_PROMOTION_ROUNDS = 2
ROOT_VALIDATION_BASE_DRAWS = 2_048
CHILD_VALIDATION_BASE_DRAWS = 8_192

TERMINAL_SCOPE = "CONSTRUCTION_INTERMEDIATE_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
PRODUCTION_BLOCKER = (
    "live dynamic acquisition is construction-only; controller semantic-role "
    "adaptation, process isolation, byte-gated observer execution, final "
    "lineage reconciliation, and independent total lift remain required"
)

LIVE_DYNAMIC_CHILD_SEMANTIC_ROLE = (
    "LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT"
)
LIVE_DYNAMIC_CHILD_SEMANTIC_SCHEMA = (
    "acfqp.v075_live_dynamic_child_acquisition_intent.v2"
)
LIVE_DYNAMIC_CHILD_VALIDATION_TEMPLATE_SCHEMA = (
    "acfqp.v075_live_dynamic_child_validation_intent_template.v2"
)
LIVE_PROMOTION_SEMANTIC_ROLE = "LIVE_PROMOTION_AUTHORIZATION"
LIVE_PROMOTION_SEMANTIC_SCHEMA = (
    "acfqp.v075_live_promotion_authorization.v2"
)

PROMOTION_SELECTION_RULE = (
    "MAX_INTERVAL_WIDTH_SUM_THEN_MAX_OTHER_UPPER_THEN_MIN_ROW_ID"
)

DOMAIN_TAGS = {
    "child_edge": "acfqp:v075-live-dynamic-child-causal-edge:v2",
    "child_state": "acfqp:v075-live-dynamic-child-state:v2",
    "child_discovery_intent": (
        "acfqp:v075-live-dynamic-child-discovery-intent:v2"
    ),
    "child_validation_template": (
        "acfqp:v075-live-dynamic-child-validation-template:v2"
    ),
    "child_closure": "acfqp:v075-live-dynamic-child-closure:v2",
    "child_verification": (
        "acfqp:v075-live-dynamic-child-closure-verification:v2"
    ),
    "child_executed_row": (
        "acfqp:v075-live-dynamic-child-executed-row:v2"
    ),
    "child_execution_ledger": (
        "acfqp:v075-live-dynamic-child-execution-ledger:v2"
    ),
    "child_execution_verification": (
        "acfqp:v075-live-dynamic-child-execution-verification:v2"
    ),
    "child_replanning_barrier": (
        "acfqp:v075-live-dynamic-child-replanning-barrier:v2"
    ),
    "child_replanning_verification": (
        "acfqp:v075-live-dynamic-child-replanning-barrier-verification:v2"
    ),
    "promotion_intent": "acfqp:v075-live-promotion-intent:v2",
    "promotion_decision": "acfqp:v075-live-promotion-decision:v2",
    "promotion_verification": (
        "acfqp:v075-live-promotion-decision-verification:v2"
    ),
    "promotion_replanning_barrier": (
        "acfqp:v075-live-promotion-replanning-barrier:v2"
    ),
    "promotion_replanning_verification": (
        "acfqp:v075-live-promotion-replanning-barrier-verification:v2"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 live dynamic authority domains overlap")

_CAPS = worker.V075WorkerCapProfileV1()
if (
    _CAPS.new_child_discovery_draws_per_row != CHILD_DISCOVERY_DRAWS
    or _CAPS.new_child_validation_draws_per_row != CHILD_VALIDATION_DRAWS
    or _CAPS.promotion_validation_draws_per_round != PROMOTION_DRAWS
    or _CAPS.maximum_new_child_action_rows
    != MAXIMUM_NEW_CHILD_ACTION_ROWS
    or _CAPS.maximum_adaptive_rounds != MAXIMUM_PROMOTION_ROUNDS
    or _CAPS.initial_validation_draws_per_row
    != ROOT_VALIDATION_BASE_DRAWS
):
    raise RuntimeError("V0-075 live dynamic constants drifted from cap profile")


class V075LiveDynamicAcquisitionV2InvariantViolation(ValueError):
    """A model epoch, child closure, promotion, or identity chain was invalid."""


class V075LiveDynamicAcquisitionProductionV2NotReady(RuntimeError):
    """Production use remains structurally locked."""


def _fail(message: str) -> NoReturn:
    raise V075LiveDynamicAcquisitionV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075LiveDynamicAcquisitionV2InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075LiveDynamicAcquisitionV2InvariantViolation(
            str(error)
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
        raise V075LiveDynamicAcquisitionV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return document


def _replay_epoch(
    value: live_model.V075LiveIncrementalModelEpochV2,
) -> live_model.V075LiveIncrementalModelEpochV2:
    if type(value) is not live_model.V075LiveIncrementalModelEpochV2:
        _fail("live dynamic authority requires one exact model epoch")
    try:
        replayed = live_model.replay_v075_live_incremental_model_epoch_v2(
            value
        )
    except Exception as error:
        if type(error) is V075LiveDynamicAcquisitionV2InvariantViolation:
            raise
        raise V075LiveDynamicAcquisitionV2InvariantViolation(
            "live incremental model epoch exact replay failed"
        ) from error
    if (
        replayed.model_epoch_id != value.model_epoch_id
        or replayed.canonical_bytes != value.canonical_bytes
    ):
        _fail("live model epoch differs from exact replay")
    return replayed


def _operational_epoch(
    value: live_model.V075LiveIncrementalModelEpochV2,
) -> live_model.V075LiveIncrementalModelEpochV2:
    """Validate construction provenance without portable planner replay."""

    try:
        return live_model._validate_operational_parent(value)  # noqa: SLF001
    except Exception as error:
        if type(error) is V075LiveDynamicAcquisitionV2InvariantViolation:
            raise
        raise V075LiveDynamicAcquisitionV2InvariantViolation(
            "live model epoch lacks immutable same-process provenance"
        ) from error


def _replay_namespace(
    value: namespace_v2.V075PublicTargetTapeNamespaceV2,
    *,
    epoch: live_model.V075LiveIncrementalModelEpochV2,
) -> namespace_v2.V075PublicTargetTapeNamespaceV2:
    if (
        type(value) is not namespace_v2.V075PublicTargetTapeNamespaceV2
        or graph.validate_v075_public_graph_namespace_v2(value) is not value
        or value.target_tape_namespace_id
        != epoch.occurrence_identity.target_tape_namespace_id
        or epoch.occurrence_identity.context_id != epoch.context_id
        or epoch.occurrence_identity.arm is not epoch.arm
    ):
        _fail("live dynamic namespace or occurrence identity was transplanted")
    contexts = tuple(
        item
        for item in value.family.replicate_contexts
        if item.context_id == epoch.context_id
    )
    if (
        len(contexts) != 1
        or contexts[0].to_document() != epoch.model.context.to_document()
    ):
        _fail("live dynamic model context differs from exact namespace")
    return value


def _bootstrap_stream(
    *,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    row_binding: graph.V075ObservationRowBindingV1,
    arm: worker.V075WorkerArmV1,
) -> graph.V075TransitionStreamIdentityV1:
    try:
        bootstrap = graph.derive_shared_support_epoch_v1(
            namespace=namespace,
            row_binding=row_binding,
            epoch_index=0,
            evidence=(),
        )
        chain = graph.freeze_shared_support_chain_v1(
            namespace=namespace,
            row_binding=row_binding,
            epochs=(bootstrap,),
        )
        pairing = graph.freeze_five_arm_pairing_authority_v1(
            namespace=namespace,
            row_binding=row_binding,
            support_chain=chain,
        )
        return graph.derive_transition_stream_identity_v1(
            pairing_authority=pairing,
            arm=arm.value,
        )
    except graph.V075PublicGraphSemanticsInvariantViolation as error:
        raise V075LiveDynamicAcquisitionV2InvariantViolation(
            "dynamic-child bootstrap stream derivation failed"
        ) from error


def _row_source(
    epoch: live_model.V075LiveIncrementalModelEpochV2,
    row_binding_id: str,
) -> live_model.V075LiveModelRowSourceBindingV2:
    try:
        source = epoch.row_source_for_binding_v2(row_binding_id)
    except Exception as error:
        raise V075LiveDynamicAcquisitionV2InvariantViolation(
            "live model row lacks exact row-source evidence"
        ) from error
    if (
        type(source) is not live_model.V075LiveModelRowSourceBindingV2
        or source.row_binding_id != row_binding_id
    ):
        _fail("live model row-source evidence is foreign")
    return source


def _validation_stream(
    *,
    epoch: live_model.V075LiveIncrementalModelEpochV2,
    source: live_model.V075LiveModelRowSourceBindingV2,
) -> graph.V075TransitionStreamIdentityV1:
    if not source.validation_append_receipt_ids:
        _fail("promotion source has no validation append")
    streams: dict[str, graph.V075TransitionStreamIdentityV1] = {}
    for receipt_id in source.validation_append_receipt_ids:
        try:
            append = epoch.controlled_append_by_receipt_id_v2(receipt_id)
        except Exception as error:
            raise V075LiveDynamicAcquisitionV2InvariantViolation(
                "promotion validation append replay failed"
            ) from error
        stream = append.batch.request.stream_identity
        if (
            append.receipt.receipt_id != receipt_id
            or stream.row_binding_id != source.row_binding_id
            or stream.lane is not graph.V075ObservationLaneV1.VALIDATION
            or stream.observer_epoch_index != 1
            or append.batch.request.accepted_draw_cap
            != source.validation_draw_cap
        ):
            _fail("promotion row-source validation stream changed")
        streams[stream.stream_id] = stream
    if (
        len(streams) != 1
        or next(iter(streams)) != source.validation_stream_id
    ):
        _fail("promotion row-source uses multiple validation streams")
    return next(iter(streams.values()))


class V075LiveDynamicChildClosureStatusV2(str, Enum):
    AUTHORIZED = "DYNAMIC_CHILD_BASE_ACQUISITION_AUTHORIZED"
    CANDIDATE_EARLY_STOP = "CANDIDATE_EARLY_STOP"
    ALREADY_COMPLETE = "DYNAMIC_CHILD_CLOSURE_ALREADY_COMPLETE"
    CHILD_ACTION_ROW_CAP_EXCEEDED = "CHILD_ACTION_ROW_CAP_EXCEEDED"


class V075LiveDynamicChildIntentStageV2(str, Enum):
    CHILD_DISCOVERY = "CHILD_DISCOVERY"
    CHILD_VALIDATION = "CHILD_VALIDATION"


_CHILD_EDGE_ISSUER = object()
_CHILD_STATE_ISSUER = object()
_CHILD_DISCOVERY_ISSUER = object()
_CHILD_VALIDATION_TEMPLATE_ISSUER = object()
_CHILD_CLOSURE_FROM_REPLAYED_EPOCH_ISSUER = object()
_CHILD_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075LiveDynamicChildCausalEdgeV2:
    """One exact root-row evidence edge to an active child."""

    _issuer: object = field(repr=False, compare=False)
    child_state_id: str
    parent_numerical_row_id: str
    parent_row_binding_id: str
    support_descriptor_id: str
    row_source_binding_id: str
    support_freeze_id: str
    _edge_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.child_state_id, "live child state"),
            (self.parent_numerical_row_id, "live child parent row"),
            (self.parent_row_binding_id, "live child parent binding"),
            (self.support_descriptor_id, "live child descriptor"),
            (self.row_source_binding_id, "live child row source"),
            (self.support_freeze_id, "live child support freeze"),
        ):
            _cid(value, label)
        if self._issuer is not _CHILD_EDGE_ISSUER:
            _fail("live dynamic child causal edge is caller-minted")
        object.__setattr__(
            self,
            "_edge_id",
            _hash("child_edge", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_dynamic_child_causal_edge.v2",
            "schema_version": SCHEMA_VERSION,
            "child_state_id": self.child_state_id,
            "parent_numerical_row_id": self.parent_numerical_row_id,
            "parent_row_binding_id": self.parent_row_binding_id,
            "support_descriptor_id": self.support_descriptor_id,
            "row_source_binding_id": self.row_source_binding_id,
            "support_freeze_id": self.support_freeze_id,
            "root_descriptor_edge": True,
            "other_event_instantiated": False,
        }

    @property
    def edge_id(self) -> str:
        return self._edge_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "edge_id": self.edge_id}


@dataclass(frozen=True, slots=True)
class V075LiveDynamicChildStateV2:
    """One deduplicated active child with its complete public action domain."""

    _issuer: object = field(repr=False, compare=False)
    state: graph.V075SymbolicGraphStateV1
    catalogue: graph.V075LegalActionCatalogueV1
    row_bindings: tuple[graph.V075ObservationRowBindingV1, ...]
    causal_edges: tuple[V075LiveDynamicChildCausalEdgeV2, ...]
    modeled_row_binding_ids: tuple[str, ...]
    unresolved_row_binding_ids: tuple[str, ...]
    _child_binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.state) is not graph.V075SymbolicGraphStateV1:
            _fail("live dynamic child state is not one exact public state")
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
                            expected_state.context,
                            expected_catalogue,
                            action,
                        )
                        for action in expected_catalogue.actions
                    ),
                    key=lambda item: item.row_binding_id,
                )
            )
        except graph.V075PublicGraphSemanticsInvariantViolation as error:
            raise V075LiveDynamicAcquisitionV2InvariantViolation(
                "live dynamic child public catalogue replay failed"
            ) from error
        if (
            self._issuer is not _CHILD_STATE_ISSUER
            or self.state.failure
            or expected_state.to_document() != self.state.to_document()
            or type(self.catalogue) is not graph.V075LegalActionCatalogueV1
            or expected_catalogue.to_document() != self.catalogue.to_document()
            or self.row_bindings != expected_rows
            or type(self.causal_edges) is not tuple
            or not self.causal_edges
            or self.causal_edges
            != tuple(sorted(self.causal_edges, key=lambda item: item.edge_id))
            or len({item.edge_id for item in self.causal_edges})
            != len(self.causal_edges)
            or any(
                type(item) is not V075LiveDynamicChildCausalEdgeV2
                or item.child_state_id != self.state.state_id
                for item in self.causal_edges
            )
        ):
            _fail("live dynamic child state or causal edge registry changed")
        all_rows = tuple(item.row_binding_id for item in expected_rows)
        for values, label in (
            (self.modeled_row_binding_ids, "modeled live child row"),
            (self.unresolved_row_binding_ids, "unresolved live child row"),
        ):
            if (
                type(values) is not tuple
                or values != tuple(sorted(set(values)))
            ):
                _fail(f"{label} registry is reordered or duplicated")
            for value in values:
                _cid(value, label)
        if (
            set(self.modeled_row_binding_ids)
            & set(self.unresolved_row_binding_ids)
            or tuple(
                sorted(
                    (
                        *self.modeled_row_binding_ids,
                        *self.unresolved_row_binding_ids,
                    )
                )
            )
            != all_rows
        ):
            _fail("live child modeled/unresolved partition is incomplete")
        object.__setattr__(
            self,
            "_child_binding_id",
            _hash("child_state", self._payload()),
        )

    @property
    def child_binding_id(self) -> str:
        return self._child_binding_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_dynamic_child_state.v2",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.state.context_id,
            "child_state_id": self.state.state_id,
            "child_ranks": list(self.state.ranks),
            "catalogue_id": self.catalogue.catalogue_id,
            "complete_action_row_binding_ids": [
                item.row_binding_id for item in self.row_bindings
            ],
            "causal_edge_ids": [item.edge_id for item in self.causal_edges],
            "modeled_row_binding_ids": list(self.modeled_row_binding_ids),
            "unresolved_row_binding_ids": list(
                self.unresolved_row_binding_ids
            ),
            "active_nonfailure_nonterminal_child": True,
            "complete_public_action_catalogue": True,
            "child_state_deduplicated_across_root_rows": True,
            "other_event_instantiated": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "state": self.state.to_document(),
            "catalogue": self.catalogue.to_document(),
            "row_bindings": [item.to_document() for item in self.row_bindings],
            "causal_edges": [
                item.to_document() for item in self.causal_edges
            ],
            "child_binding_id": self.child_binding_id,
        }


@dataclass(frozen=True, slots=True)
class V075LiveDynamicChildDiscoveryIntentV2:
    """One exact D64 observer-ready child discovery intent."""

    _issuer: object = field(repr=False, compare=False)
    source_model_epoch_id: str
    source_numerical_model_id: str
    source_proof_id: str
    source_frontier_id: str | None
    source_head_id: str
    occurrence_id: str
    context_id: str
    arm: worker.V075WorkerArmV1
    child_binding_id: str
    child_state_id: str
    catalogue_id: str
    row_binding: graph.V075ObservationRowBindingV1
    stream_identity: graph.V075TransitionStreamIdentityV1
    ordinal: int
    _intent_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.source_model_epoch_id, "child intent model epoch"),
            (self.source_numerical_model_id, "child intent model"),
            (self.source_proof_id, "child intent proof"),
            (self.source_head_id, "child intent head"),
            (self.occurrence_id, "child intent occurrence"),
            (self.context_id, "child intent context"),
            (self.child_binding_id, "child intent binding"),
            (self.child_state_id, "child intent state"),
            (self.catalogue_id, "child intent catalogue"),
        ):
            _cid(value, label)
        if self.source_frontier_id is not None:
            _cid(self.source_frontier_id, "child intent frontier")
        if (
            self._issuer is not _CHILD_DISCOVERY_ISSUER
            or type(self.arm) is not worker.V075WorkerArmV1
            or type(self.row_binding)
            is not graph.V075ObservationRowBindingV1
            or type(self.stream_identity)
            is not graph.V075TransitionStreamIdentityV1
            or self.row_binding.context_id != self.context_id
            or self.row_binding.state_id != self.child_state_id
            or self.row_binding.catalogue_id != self.catalogue_id
            or self.stream_identity.row_binding != self.row_binding
            or self.stream_identity.arm != self.arm.value
            or self.stream_identity.lane
            is not graph.V075ObservationLaneV1.DISCOVERY
            or self.stream_identity.observer_epoch_index != 0
            or type(self.ordinal) is not int
            or self.ordinal < 0
        ):
            _fail("live child discovery intent is malformed or caller-minted")
        object.__setattr__(
            self,
            "_intent_id",
            _hash("child_discovery_intent", self._payload()),
        )

    @property
    def intent_id(self) -> str:
        return self._intent_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LIVE_DYNAMIC_CHILD_SEMANTIC_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "semantic_role": LIVE_DYNAMIC_CHILD_SEMANTIC_ROLE,
            "stage": V075LiveDynamicChildIntentStageV2.CHILD_DISCOVERY.value,
            "round_index": 0,
            "source_model_epoch_id": self.source_model_epoch_id,
            "source_numerical_model_id": self.source_numerical_model_id,
            "source_proof_id": self.source_proof_id,
            "source_frontier_id": self.source_frontier_id,
            "source_head_id": self.source_head_id,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "arm": self.arm.value,
            "child_binding_id": self.child_binding_id,
            "child_state_id": self.child_state_id,
            "catalogue_id": self.catalogue_id,
            "row_binding_id": self.row_binding.row_binding_id,
            "stream_id": self.stream_identity.stream_id,
            "support_freeze_id": None,
            "accepted_draw_start": 1,
            "accepted_draw_count": CHILD_DISCOVERY_DRAWS,
            "accepted_draw_end": CHILD_DISCOVERY_DRAWS,
            "accepted_draw_cap": CHILD_DISCOVERY_DRAWS,
            "ordinal": self.ordinal,
            "observer_execution_ready": True,
            "base_child_acquisition_consumes_promotion_round": False,
            "official_execution_allowed": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_binding": self.row_binding.to_document(),
            "stream_identity": self.stream_identity.to_document(),
            "intent_id": self.intent_id,
        }


@dataclass(frozen=True, slots=True)
class V075LiveDynamicChildValidationIntentTemplateV2:
    """Exact V8192 requirement awaiting a signed complete-support freeze."""

    _issuer: object = field(repr=False, compare=False)
    discovery_intent: V075LiveDynamicChildDiscoveryIntentV2 = field(
        repr=False
    )
    _template_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _CHILD_VALIDATION_TEMPLATE_ISSUER
            or type(self.discovery_intent)
            is not V075LiveDynamicChildDiscoveryIntentV2
        ):
            _fail("live child validation template is caller-minted")
        object.__setattr__(
            self,
            "_template_id",
            _hash("child_validation_template", self._payload()),
        )

    @property
    def template_id(self) -> str:
        return self._template_id

    @property
    def row_binding_id(self) -> str:
        return self.discovery_intent.row_binding.row_binding_id

    def _payload(self) -> dict[str, Any]:
        discovery = self.discovery_intent
        return {
            "schema": LIVE_DYNAMIC_CHILD_VALIDATION_TEMPLATE_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "semantic_role": LIVE_DYNAMIC_CHILD_SEMANTIC_ROLE,
            "stage": V075LiveDynamicChildIntentStageV2.CHILD_VALIDATION.value,
            "round_index": 0,
            "source_model_epoch_id": discovery.source_model_epoch_id,
            "source_proof_id": discovery.source_proof_id,
            "source_head_id": discovery.source_head_id,
            "occurrence_id": discovery.occurrence_id,
            "context_id": discovery.context_id,
            "arm": discovery.arm.value,
            "child_binding_id": discovery.child_binding_id,
            "child_state_id": discovery.child_state_id,
            "catalogue_id": discovery.catalogue_id,
            "row_binding_id": self.row_binding_id,
            "dependency_discovery_intent_id": discovery.intent_id,
            "stream_id": None,
            "support_freeze_id": None,
            "accepted_draw_start": 1,
            "accepted_draw_count": CHILD_VALIDATION_DRAWS,
            "accepted_draw_end": CHILD_VALIDATION_DRAWS,
            "accepted_draw_cap": (
                CHILD_VALIDATION_DRAWS
                + MAXIMUM_PROMOTION_ROUNDS * PROMOTION_DRAWS
            ),
            "observer_execution_ready": False,
            "observer_signed_complete_support_required": True,
            "validation_stream_must_be_derived_from_support_freeze": True,
            "base_child_acquisition_consumes_promotion_round": False,
            "official_execution_allowed": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "template_id": self.template_id,
        }


@dataclass(frozen=True, slots=True)
class V075LiveDynamicChildClosureV2:
    """All-or-none live child closure derived from every root descriptor."""

    _issuer: object = field(repr=False, compare=False)
    source_epoch: live_model.V075LiveIncrementalModelEpochV2 = field(
        repr=False
    )
    child_states: tuple[V075LiveDynamicChildStateV2, ...]
    discovery_intents: tuple[V075LiveDynamicChildDiscoveryIntentV2, ...]
    validation_templates: tuple[
        V075LiveDynamicChildValidationIntentTemplateV2,
        ...,
    ]
    status: V075LiveDynamicChildClosureStatusV2
    existing_child_action_row_count: int
    unresolved_child_action_row_count: int
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        epoch = self.source_epoch
        if (
            self._issuer is not _CHILD_CLOSURE_FROM_REPLAYED_EPOCH_ISSUER
            or type(epoch) is not live_model.V075LiveIncrementalModelEpochV2
            or type(self.status) is not V075LiveDynamicChildClosureStatusV2
            or type(self.child_states) is not tuple
            or self.child_states
            != tuple(
                sorted(
                    self.child_states,
                    key=lambda item: item.state.state_id,
                )
            )
            or any(
                type(item) is not V075LiveDynamicChildStateV2
                for item in self.child_states
            )
            or type(self.discovery_intents) is not tuple
            or self.discovery_intents
            != tuple(
                sorted(self.discovery_intents, key=lambda item: item.ordinal)
            )
            or tuple(item.ordinal for item in self.discovery_intents)
            != tuple(range(len(self.discovery_intents)))
            or type(self.validation_templates) is not tuple
            or len(self.validation_templates) != len(self.discovery_intents)
            or any(
                type(item)
                is not V075LiveDynamicChildValidationIntentTemplateV2
                for item in self.validation_templates
            )
            or tuple(
                item.discovery_intent.intent_id
                for item in self.validation_templates
            )
            != tuple(item.intent_id for item in self.discovery_intents)
            or type(self.existing_child_action_row_count) is not int
            or self.existing_child_action_row_count < 0
            or type(self.unresolved_child_action_row_count) is not int
            or self.unresolved_child_action_row_count < 0
        ):
            _fail("live dynamic child closure is malformed")
        unresolved = tuple(
            sorted(
                row_id
                for child in self.child_states
                for row_id in child.unresolved_row_binding_ids
            )
        )
        modeled = tuple(
            sorted(
                row_id
                for child in self.child_states
                for row_id in child.modeled_row_binding_ids
            )
        )
        if (
            len(set(unresolved)) != len(unresolved)
            or self.existing_child_action_row_count != len(modeled)
            or self.unresolved_child_action_row_count != len(unresolved)
        ):
            _fail("live dynamic child row accounting changed")
        authorized = (
            self.status is V075LiveDynamicChildClosureStatusV2.AUTHORIZED
        )
        candidate = (
            epoch.proof.outcome
            is planning_v2.V075NumericalOutcomeV2.CANDIDATE
        )
        candidate_stop = (
            self.status
            is V075LiveDynamicChildClosureStatusV2.CANDIDATE_EARLY_STOP
        )
        frontier = epoch.proof.failed_frontier
        if candidate_stop != candidate:
            _fail("child candidate early-stop differs from source proof")
        if authorized:
            row_owners = {
                row.row_binding_id: child
                for child in self.child_states
                for row in child.row_bindings
            }
            if (
                candidate
                or frontier is None
                or len(self.discovery_intents) != len(unresolved)
                or tuple(
                    sorted(
                        item.row_binding.row_binding_id
                        for item in self.discovery_intents
                    )
                )
                != unresolved
                or len(modeled) + len(unresolved)
                > MAXIMUM_NEW_CHILD_ACTION_ROWS
                or any(
                    (
                        item.source_model_epoch_id != epoch.model_epoch_id
                        or item.source_numerical_model_id
                        != epoch.model.model_id
                        or item.source_proof_id != epoch.proof.proof_id
                        or item.source_frontier_id != frontier.frontier_id
                        or item.source_head_id != epoch.head_id
                        or item.occurrence_id
                        != epoch.occurrence_identity.occurrence_id
                        or item.context_id != epoch.context_id
                        or item.arm is not epoch.arm
                        or item.row_binding.row_binding_id
                        not in row_owners
                        or item.child_binding_id
                        != row_owners[
                            item.row_binding.row_binding_id
                        ].child_binding_id
                    )
                    for item in self.discovery_intents
                )
            ):
                _fail("authorized child acquisition is partial or over cap")
        elif self.discovery_intents or self.validation_templates:
            _fail("non-authorized child closure emitted executable work")
        if (
            self.status
            is V075LiveDynamicChildClosureStatusV2.ALREADY_COMPLETE
        ) != (not candidate and not unresolved):
            _fail("child complete status differs from exact row closure")
        if (
            self.status
            is (
                V075LiveDynamicChildClosureStatusV2
                .CHILD_ACTION_ROW_CAP_EXCEEDED
            )
        ) != (
            not candidate
            and bool(unresolved)
            and len(modeled) + len(unresolved)
            > MAXIMUM_NEW_CHILD_ACTION_ROWS
        ):
            _fail("child cap status differs from exact row count")
        if authorized != (
            not candidate
            and bool(unresolved)
            and len(modeled) + len(unresolved)
            <= MAXIMUM_NEW_CHILD_ACTION_ROWS
        ):
            _fail("child authorization differs from failed-frontier row count")
        if (frontier is None) != candidate:
            _fail("child source frontier nullability differs from proof outcome")
        if epoch.proof.model.model_id != epoch.model.model_id:
            _fail("child closure epoch proof/model identity changed")
        object.__setattr__(
            self,
            "_closure_id",
            _hash("child_closure", self._payload()),
        )

    @property
    def closure_id(self) -> str:
        return self._closure_id

    def _payload(self) -> dict[str, Any]:
        epoch = self.source_epoch
        frontier = epoch.proof.failed_frontier
        return {
            "schema": "acfqp.v075_live_dynamic_child_closure.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "status": self.status.value,
            "source_model_epoch_id": epoch.model_epoch_id,
            "source_numerical_model_id": epoch.model.model_id,
            "source_proof_id": epoch.proof.proof_id,
            "source_frontier_id": (
                None if frontier is None else frontier.frontier_id
            ),
            "source_head_id": epoch.head_id,
            "occurrence_id": epoch.occurrence_identity.occurrence_id,
            "context_id": epoch.context_id,
            "arm": epoch.arm.value,
            "child_binding_ids": [
                item.child_binding_id for item in self.child_states
            ],
            "discovery_intent_ids": [
                item.intent_id for item in self.discovery_intents
            ],
            "validation_template_ids": [
                item.template_id for item in self.validation_templates
            ],
            "existing_child_action_row_count": (
                self.existing_child_action_row_count
            ),
            "unresolved_child_action_row_count": (
                self.unresolved_child_action_row_count
            ),
            "maximum_new_child_action_rows": MAXIMUM_NEW_CHILD_ACTION_ROWS,
            "all_root_support_descriptors_examined": not (
                self.status
                is V075LiveDynamicChildClosureStatusV2.CANDIDATE_EARLY_STOP
            ),
            "other_event_instantiated": False,
            "active_children_deduplicated": not (
                self.status
                is V075LiveDynamicChildClosureStatusV2.CANDIDATE_EARLY_STOP
            ),
            "complete_child_catalogues": not (
                self.status
                is V075LiveDynamicChildClosureStatusV2.CANDIDATE_EARLY_STOP
            ),
            "all_or_none_child_base_authorization": True,
            "candidate_early_stop_before_ground_recovery": (
                self.status
                is V075LiveDynamicChildClosureStatusV2.CANDIDATE_EARLY_STOP
            ),
            "child_base_consumes_promotion_rounds": 0,
            "observer_calls": 0,
            "kernel_calls": 0,
            "official_execution_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "child_states": [item.to_document() for item in self.child_states],
            "discovery_intents": [
                item.to_document() for item in self.discovery_intents
            ],
            "validation_templates": [
                item.to_document() for item in self.validation_templates
            ],
            "closure_id": self.closure_id,
        }


@dataclass(frozen=True, slots=True)
class V075LiveDynamicChildClosureVerificationV2:
    """Verifier-issued semantic ID for signed-controller references."""

    _issuer: object = field(repr=False, compare=False)
    closure_id: str
    source_model_epoch_id: str
    source_proof_id: str
    source_head_id: str
    status: V075LiveDynamicChildClosureStatusV2
    discovery_intent_ids: tuple[str, ...]
    validation_template_ids: tuple[str, ...]
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.closure_id, "child closure verification closure"),
            (self.source_model_epoch_id, "child closure verification epoch"),
            (self.source_proof_id, "child closure verification proof"),
            (self.source_head_id, "child closure verification head"),
            *(
                (value, "child closure verification member")
                for value in (
                    *self.discovery_intent_ids,
                    *self.validation_template_ids,
                )
            ),
        ):
            _cid(value, label)
        if (
            self._issuer is not _CHILD_VERIFICATION_ISSUER
            or type(self.status) is not V075LiveDynamicChildClosureStatusV2
            or self.discovery_intent_ids
            != tuple(dict.fromkeys(self.discovery_intent_ids))
            or self.validation_template_ids
            != tuple(dict.fromkeys(self.validation_template_ids))
            or len(self.discovery_intent_ids)
            != len(self.validation_template_ids)
        ):
            _fail("live child closure verification is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("child_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_live_dynamic_child_closure_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "closure_id": self.closure_id,
            "source_model_epoch_id": self.source_model_epoch_id,
            "source_proof_id": self.source_proof_id,
            "source_head_id": self.source_head_id,
            "status": self.status.value,
            "discovery_intent_ids": list(self.discovery_intent_ids),
            "validation_template_ids": list(self.validation_template_ids),
            "semantic_replay_complete": True,
            "observer_execution_performed": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _derive_child_states(
    epoch: live_model.V075LiveIncrementalModelEpochV2,
) -> tuple[V075LiveDynamicChildStateV2, ...]:
    modeled_row_ids = {
        row.row_binding_id
        for row in epoch.model.rows
        if row.remaining_horizon == 1
    }
    causes: dict[
        str,
        tuple[
            graph.V075SymbolicGraphStateV1,
            dict[str, V075LiveDynamicChildCausalEdgeV2],
        ],
    ] = {}
    for row in epoch.model.rows:
        if row.remaining_horizon != 2:
            continue
        source = _row_source(epoch, row.row_binding_id)
        if source.numerical_row_id != row.row_id:
            _fail("root row-source numerical row identity changed")
        for descriptor in row.support:
            if descriptor.failure or descriptor.terminal:
                continue
            try:
                state = graph.V075SymbolicGraphStateV1(
                    epoch.model.context,
                    descriptor.next_ranks,
                    False,
                )
            except graph.V075PublicGraphSemanticsInvariantViolation as error:
                raise V075LiveDynamicAcquisitionV2InvariantViolation(
                    "root support descriptor child is structurally invalid"
                ) from error
            if state.state_id != descriptor.next_state_id:
                _fail("root support descriptor child identity changed")
            edge = V075LiveDynamicChildCausalEdgeV2(
                _CHILD_EDGE_ISSUER,
                state.state_id,
                row.row_id,
                row.row_binding_id,
                descriptor.descriptor_id,
                source.binding_id,
                source.support_freeze_id,
            )
            if state.state_id not in causes:
                causes[state.state_id] = (state, {})
            causes[state.state_id][1][edge.edge_id] = edge

    children = []
    for state_id in sorted(causes):
        state, edges = causes[state_id]
        try:
            catalogue = graph.V075LegalActionCatalogueV1(
                state.context,
                state,
                1,
                graph.legal_action_triples_v1(
                    state.context,
                    state.ranks,
                    state.failure,
                ),
            )
            rows = tuple(
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
            )
        except graph.V075PublicGraphSemanticsInvariantViolation as error:
            raise V075LiveDynamicAcquisitionV2InvariantViolation(
                "complete live child catalogue construction failed"
            ) from error
        row_ids = tuple(item.row_binding_id for item in rows)
        children.append(
            V075LiveDynamicChildStateV2(
                _CHILD_STATE_ISSUER,
                state,
                catalogue,
                rows,
                tuple(edges[key] for key in sorted(edges)),
                tuple(item for item in row_ids if item in modeled_row_ids),
                tuple(item for item in row_ids if item not in modeled_row_ids),
            )
        )
    return tuple(children)


def _assert_exact_root_stage_epoch(
    epoch: live_model.V075LiveIncrementalModelEpochV2,
) -> None:
    """Reject any post-child or post-promotion epoch at the closure entrance."""

    root = graph.root_catalogue_v1(epoch.model.context)
    expected_rows = tuple(
        sorted(
            graph.observation_row_binding_v1(
                epoch.model.context,
                root,
                action,
            ).row_binding_id
            for action in root.actions
        )
    )
    actual_rows = tuple(
        sorted(item.row_binding_id for item in epoch.model.rows)
    )
    root_role = (
        control.V075ControlledBatchSemanticAuthorityRoleV2
        .INITIAL_SCHEDULE_ROW_INTENT
    )
    root_schema = (
        control.V075ControlledBatchSemanticAuthoritySchemaV2
        .INITIAL_SCHEDULE_ROW_INTENT
    )
    if (
        epoch.epoch_index != 1
        or epoch.parent_epoch is not None
        or actual_rows != expected_rows
        or any(item.remaining_horizon != 2 for item in epoch.model.rows)
        or epoch.changed_row_binding_ids != expected_rows
        or epoch.reused_row_binding_ids
        or len(epoch.support_freezes) != len(expected_rows)
        or any(
            append.intent.semantic_authority.role is not root_role
            or append.intent.semantic_authority.schema is not root_schema
            or append.intent.semantic_authority.stage
            not in {
                control.V075ControlledBatchStageV2.ROOT_DISCOVERY,
                control.V075ControlledBatchStageV2.ROOT_VALIDATION,
            }
            or append.intent.semantic_authority.round_index != 0
            for append in epoch.controlled_appends
        )
    ):
        _fail(
            "child closure requires the exact complete root-stage epoch "
            "before any child acquisition or promotion"
        )


def _freeze_v075_live_dynamic_child_closure_from_exact_epoch_v2(
    *,
    epoch: live_model.V075LiveIncrementalModelEpochV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
) -> V075LiveDynamicChildClosureV2:
    """Derive a closure from an epoch already owned by one exact boundary."""

    _assert_exact_root_stage_epoch(epoch)
    namespace = _replay_namespace(namespace, epoch=epoch)
    if epoch.proof.outcome is planning_v2.V075NumericalOutcomeV2.CANDIDATE:
        return V075LiveDynamicChildClosureV2(
            _CHILD_CLOSURE_FROM_REPLAYED_EPOCH_ISSUER,
            epoch,
            (),
            (),
            (),
            V075LiveDynamicChildClosureStatusV2.CANDIDATE_EARLY_STOP,
            0,
            0,
        )
    children = _derive_child_states(epoch)
    modeled = tuple(
        sorted(
            row_id
            for child in children
            for row_id in child.modeled_row_binding_ids
        )
    )
    unresolved = tuple(
        sorted(
            (
                (child, row)
                for child in children
                for row in child.row_bindings
                if row.row_binding_id in child.unresolved_row_binding_ids
            ),
            key=lambda item: item[1].row_binding_id,
        )
    )
    if not unresolved:
        status = V075LiveDynamicChildClosureStatusV2.ALREADY_COMPLETE
        discoveries: tuple[V075LiveDynamicChildDiscoveryIntentV2, ...] = ()
        validations: tuple[
            V075LiveDynamicChildValidationIntentTemplateV2,
            ...,
        ] = ()
    elif len(modeled) + len(unresolved) > MAXIMUM_NEW_CHILD_ACTION_ROWS:
        status = (
            V075LiveDynamicChildClosureStatusV2
            .CHILD_ACTION_ROW_CAP_EXCEEDED
        )
        discoveries = ()
        validations = ()
    else:
        status = V075LiveDynamicChildClosureStatusV2.AUTHORIZED
        frontier = epoch.proof.failed_frontier
        discoveries = tuple(
            V075LiveDynamicChildDiscoveryIntentV2(
                _CHILD_DISCOVERY_ISSUER,
                epoch.model_epoch_id,
                epoch.model.model_id,
                epoch.proof.proof_id,
                None if frontier is None else frontier.frontier_id,
                epoch.head_id,
                epoch.occurrence_identity.occurrence_id,
                epoch.context_id,
                epoch.arm,
                child.child_binding_id,
                child.state.state_id,
                child.catalogue.catalogue_id,
                row,
                _bootstrap_stream(
                    namespace=namespace,
                    row_binding=row,
                    arm=epoch.arm,
                ),
                ordinal,
            )
            for ordinal, (child, row) in enumerate(unresolved)
        )
        validations = tuple(
            V075LiveDynamicChildValidationIntentTemplateV2(
                _CHILD_VALIDATION_TEMPLATE_ISSUER,
                discovery,
            )
            for discovery in discoveries
        )
    return V075LiveDynamicChildClosureV2(
        _CHILD_CLOSURE_FROM_REPLAYED_EPOCH_ISSUER,
        epoch,
        children,
        discoveries,
        validations,
        status,
        len(modeled),
        len(unresolved),
    )


def freeze_v075_live_dynamic_child_closure_v2(
    *,
    source_epoch: live_model.V075LiveIncrementalModelEpochV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
) -> V075LiveDynamicChildClosureV2:
    """Construction factory; portable replay remains in the byte verifier."""

    return _freeze_v075_live_dynamic_child_closure_from_exact_epoch_v2(
        epoch=_operational_epoch(source_epoch),
        namespace=namespace,
    )


def verify_v075_live_dynamic_child_closure_bytes_v2(
    *,
    source_epoch: live_model.V075LiveIncrementalModelEpochV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    claimed_bytes: bytes,
) -> tuple[
    V075LiveDynamicChildClosureV2,
    V075LiveDynamicChildClosureVerificationV2,
]:
    """Exact typed/byte replay; never reopens an observer or resigns evidence."""

    document = _strict_document(claimed_bytes, "live dynamic child closure")
    expected = _freeze_v075_live_dynamic_child_closure_from_exact_epoch_v2(
        epoch=_replay_epoch(source_epoch),
        namespace=namespace,
    )
    if (
        set(document) != set(expected.to_document())
        or claimed_bytes != expected.canonical_bytes
    ):
        _fail("live dynamic child closure differs from exact replay")
    epoch = expected.source_epoch
    verification = V075LiveDynamicChildClosureVerificationV2(
        _CHILD_VERIFICATION_ISSUER,
        expected.closure_id,
        epoch.model_epoch_id,
        epoch.proof.proof_id,
        epoch.head_id,
        expected.status,
        tuple(item.intent_id for item in expected.discovery_intents),
        tuple(item.template_id for item in expected.validation_templates),
    )
    return expected, verification


_CHILD_EXECUTED_ROW_ISSUER = object()
_CHILD_EXECUTION_LEDGER_ISSUER = object()
_CHILD_EXECUTION_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075LiveDynamicChildExecutedRowV2:
    """One exact D64/support-freeze/V8192 execution chain."""

    _issuer: object = field(repr=False, compare=False)
    child_binding_id: str
    row_binding_id: str
    discovery_artifact_id: str
    discovery_append_receipt_id: str
    discovery_batch_id: str
    support_freeze_id: str
    validation_artifact_id: str
    validation_append_receipt_id: str
    validation_batch_id: str
    _executed_row_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.child_binding_id, "executed child binding"),
            (self.row_binding_id, "executed child row"),
            (self.discovery_artifact_id, "executed discovery artifact"),
            (
                self.discovery_append_receipt_id,
                "executed discovery receipt",
            ),
            (self.discovery_batch_id, "executed discovery batch"),
            (self.support_freeze_id, "executed support freeze"),
            (self.validation_artifact_id, "executed validation artifact"),
            (
                self.validation_append_receipt_id,
                "executed validation receipt",
            ),
            (self.validation_batch_id, "executed validation batch"),
        ):
            _cid(value, label)
        if self._issuer is not _CHILD_EXECUTED_ROW_ISSUER:
            _fail("live child executed-row evidence is caller-minted")
        object.__setattr__(
            self,
            "_executed_row_id",
            _hash("child_executed_row", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_dynamic_child_executed_row.v2",
            "schema_version": SCHEMA_VERSION,
            "child_binding_id": self.child_binding_id,
            "row_binding_id": self.row_binding_id,
            "discovery_semantic_artifact_id": self.discovery_artifact_id,
            "discovery_append_receipt_id": (
                self.discovery_append_receipt_id
            ),
            "discovery_batch_id": self.discovery_batch_id,
            "support_freeze_id": self.support_freeze_id,
            "validation_semantic_artifact_id": self.validation_artifact_id,
            "validation_append_receipt_id": (
                self.validation_append_receipt_id
            ),
            "validation_batch_id": self.validation_batch_id,
            "discovery_draw_count": CHILD_DISCOVERY_DRAWS,
            "validation_draw_count": CHILD_VALIDATION_DRAWS,
            "executed_exactly_once": True,
        }

    @property
    def executed_row_id(self) -> str:
        return self._executed_row_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "executed_row_id": self.executed_row_id}


@dataclass(frozen=True, slots=True)
class V075LiveDynamicChildExecutionLedgerV2:
    """Barrier proving every globally authorized child row executed once."""

    _issuer: object = field(repr=False, compare=False)
    closure_id: str
    closure_verification_id: str
    source_model_epoch_id: str
    source_head_id: str
    resulting_head_id: str
    open_prefix_verification_id: str
    executed_rows: tuple[V075LiveDynamicChildExecutedRowV2, ...]
    _ledger_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.closure_id, "child execution closure"),
            (
                self.closure_verification_id,
                "child execution closure verification",
            ),
            (self.source_model_epoch_id, "child execution source epoch"),
            (self.source_head_id, "child execution source head"),
            (self.resulting_head_id, "child execution resulting head"),
            (
                self.open_prefix_verification_id,
                "child execution prefix verification",
            ),
        ):
            _cid(value, label)
        if (
            self._issuer is not _CHILD_EXECUTION_LEDGER_ISSUER
            or self.source_head_id == self.resulting_head_id
            or type(self.executed_rows) is not tuple
            or not self.executed_rows
            or any(
                type(item) is not V075LiveDynamicChildExecutedRowV2
                for item in self.executed_rows
            )
            or self.executed_rows
            != tuple(
                sorted(
                    self.executed_rows,
                    key=lambda item: item.row_binding_id,
                )
            )
            or len({item.row_binding_id for item in self.executed_rows})
            != len(self.executed_rows)
        ):
            _fail("live child execution ledger is malformed")
        object.__setattr__(
            self,
            "_ledger_id",
            _hash("child_execution_ledger", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_dynamic_child_execution_ledger.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "closure_id": self.closure_id,
            "closure_verification_id": self.closure_verification_id,
            "source_model_epoch_id": self.source_model_epoch_id,
            "source_head_id": self.source_head_id,
            "resulting_head_id": self.resulting_head_id,
            "open_prefix_verification_id": (
                self.open_prefix_verification_id
            ),
            "executed_row_ids": [
                item.executed_row_id for item in self.executed_rows
            ],
            "authorized_row_count": len(self.executed_rows),
            "discovery_append_count": len(self.executed_rows),
            "support_freeze_count": len(self.executed_rows),
            "validation_append_count": len(self.executed_rows),
            "all_authorized_intents_executed_exactly_once": True,
            "replanning_barrier_satisfied": True,
            "observer_calls": 0,
            "kernel_calls": 0,
            "official_execution_allowed": False,
        }

    @property
    def ledger_id(self) -> str:
        return self._ledger_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "executed_rows": [
                item.to_document() for item in self.executed_rows
            ],
            "ledger_id": self.ledger_id,
        }


@dataclass(frozen=True, slots=True)
class V075LiveDynamicChildExecutionVerificationV2:
    _issuer: object = field(repr=False, compare=False)
    ledger_id: str
    closure_id: str
    resulting_head_id: str
    executed_row_ids: tuple[str, ...]
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.ledger_id, "child execution ledger verification"),
            (self.closure_id, "child execution closure verification"),
            (self.resulting_head_id, "child execution head verification"),
            *(
                (value, "child execution row verification")
                for value in self.executed_row_ids
            ),
        ):
            _cid(value, label)
        if (
            self._issuer is not _CHILD_EXECUTION_VERIFICATION_ISSUER
            or type(self.executed_row_ids) is not tuple
            or not self.executed_row_ids
            or len(set(self.executed_row_ids))
            != len(self.executed_row_ids)
        ):
            _fail("live child execution verification is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("child_execution_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_live_dynamic_child_execution_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "ledger_id": self.ledger_id,
            "closure_id": self.closure_id,
            "resulting_head_id": self.resulting_head_id,
            "executed_row_ids": list(self.executed_row_ids),
            "semantic_replay_complete": True,
            "replanning_barrier_satisfied": True,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _exact_child_closure_verification(
    closure: V075LiveDynamicChildClosureV2,
) -> V075LiveDynamicChildClosureVerificationV2:
    epoch = closure.source_epoch
    return V075LiveDynamicChildClosureVerificationV2(
        _CHILD_VERIFICATION_ISSUER,
        closure.closure_id,
        epoch.model_epoch_id,
        epoch.proof.proof_id,
        epoch.head_id,
        closure.status,
        tuple(item.intent_id for item in closure.discovery_intents),
        tuple(item.template_id for item in closure.validation_templates),
    )


def _exact_child_execution_verification(
    ledger: V075LiveDynamicChildExecutionLedgerV2,
) -> V075LiveDynamicChildExecutionVerificationV2:
    return V075LiveDynamicChildExecutionVerificationV2(
        _CHILD_EXECUTION_VERIFICATION_ISSUER,
        ledger.ledger_id,
        ledger.closure_id,
        ledger.resulting_head_id,
        tuple(item.executed_row_id for item in ledger.executed_rows),
    )


def _freeze_v075_live_dynamic_child_execution_ledger_v2(
    *,
    closure: V075LiveDynamicChildClosureV2,
    closure_verification: V075LiveDynamicChildClosureVerificationV2,
    open_prefix_verification: (
        control.V075OpenControlledBatchPrefixVerificationV2
    ),
    portable_replay: bool,
) -> V075LiveDynamicChildExecutionLedgerV2:
    """Verify the global all-or-none child acquisition barrier."""

    if (
        type(closure) is not V075LiveDynamicChildClosureV2
        or closure.status
        is not V075LiveDynamicChildClosureStatusV2.AUTHORIZED
        or not closure.discovery_intents
    ):
        _fail("child execution ledger requires an authorized global closure")
    namespace = closure.discovery_intents[0].stream_identity.namespace
    exact_epoch = (
        _replay_epoch(closure.source_epoch)
        if portable_replay
        else _operational_epoch(closure.source_epoch)
    )
    exact_closure = (
        _freeze_v075_live_dynamic_child_closure_from_exact_epoch_v2(
            epoch=exact_epoch,
            namespace=namespace,
        )
    )
    if (
        exact_closure.closure_id != closure.closure_id
        or exact_closure.canonical_bytes != closure.canonical_bytes
    ):
        _fail("child execution ledger closure differs from exact replay")
    exact_verification = _exact_child_closure_verification(exact_closure)
    if (
        type(closure_verification)
        is not V075LiveDynamicChildClosureVerificationV2
        or closure_verification.verification_id
        != exact_verification.verification_id
        or closure_verification.to_document()
        != exact_verification.to_document()
    ):
        _fail("child execution ledger closure verification is foreign")
    if (
        type(open_prefix_verification)
        is not control.V075OpenControlledBatchPrefixVerificationV2
    ):
        _fail("child execution ledger requires one exact open prefix")
    try:
        prefix = (
            control.verify_v075_open_controlled_batch_prefix_v2(
                heads=open_prefix_verification.heads,
                appends=open_prefix_verification.appends,
                support_freezes=open_prefix_verification.support_freezes,
            )
            if portable_replay
            else control.validate_v075_trusted_owned_open_prefix_v2(
                claimed=open_prefix_verification,
                occurrence_identity=exact_epoch.occurrence_identity,
            )
        )
    except Exception as error:
        raise V075LiveDynamicAcquisitionV2InvariantViolation(
            "child execution open-prefix exact replay failed"
        ) from error
    if (
        prefix.verification_id != open_prefix_verification.verification_id
        or prefix.to_document() != open_prefix_verification.to_document()
    ):
        _fail("child execution open-prefix verification changed")
    source = exact_closure.source_epoch.open_prefix_verification
    if (
        prefix.occurrence_id
        != exact_closure.source_epoch.occurrence_identity.occurrence_id
        or prefix.zero_head_id != source.zero_head_id
        or prefix.head_ids[: len(source.head_ids)] != source.head_ids
        or prefix.receipt_ids[: len(source.receipt_ids)]
        != source.receipt_ids
        or prefix.support_freeze_ids[: len(source.support_freeze_ids)]
        != source.support_freeze_ids
    ):
        _fail("child execution prefix is not an exact source-head extension")
    new_appends = prefix.appends[len(source.appends) :]
    new_freezes = prefix.support_freezes[len(source.support_freezes) :]
    expected_count = len(exact_closure.discovery_intents)
    if (
        len(new_appends) != 2 * expected_count
        or len(new_freezes) != expected_count
    ):
        _fail("child execution prefix is partial or contains extra work")
    appends_by_artifact: dict[str, control.V075ControlledBatchAppendV2] = {}
    for append in new_appends:
        artifact_id = append.intent.semantic_authority.semantic_artifact_id
        if artifact_id in appends_by_artifact:
            _fail("child execution repeated one semantic artifact")
        appends_by_artifact[artifact_id] = append
    expected_artifacts = {
        item.intent_id for item in exact_closure.discovery_intents
    } | {
        item.template_id for item in exact_closure.validation_templates
    }
    if set(appends_by_artifact) != expected_artifacts:
        _fail("child execution semantic artifact set is incomplete")
    freezes_by_row = {item.row_binding_id: item for item in new_freezes}
    if len(freezes_by_row) != expected_count:
        _fail("child execution support freeze set is incomplete")
    templates = {
        item.row_binding_id: item
        for item in exact_closure.validation_templates
    }
    role = (
        control.V075ControlledBatchSemanticAuthorityRoleV2
        .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
    )
    schema = (
        control.V075ControlledBatchSemanticAuthoritySchemaV2
        .LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT
    )
    executed = []
    for discovery in exact_closure.discovery_intents:
        row_id = discovery.row_binding.row_binding_id
        template = templates[row_id]
        discovery_append = appends_by_artifact[discovery.intent_id]
        validation_append = appends_by_artifact[template.template_id]
        support = freezes_by_row.get(row_id)
        discovery_intent = discovery_append.intent
        validation_intent = validation_append.intent
        if (
            support is None
            or discovery_intent.semantic_authority.role is not role
            or discovery_intent.semantic_authority.schema is not schema
            or discovery_intent.semantic_authority.semantic_verification_id
            != exact_verification.verification_id
            or discovery_intent.semantic_authority.stage
            is not control.V075ControlledBatchStageV2.CHILD_DISCOVERY
            or discovery_intent.semantic_authority.round_index != 0
            or discovery_intent.semantic_authority.support_freeze_id
            is not None
            or discovery_intent.stream_identity
            != discovery.stream_identity
            or discovery_intent.accepted_draw_start != 1
            or discovery_intent.accepted_draw_count
            != CHILD_DISCOVERY_DRAWS
            or discovery_intent.accepted_draw_cap
            != CHILD_DISCOVERY_DRAWS
            or support.discovery_append.receipt.receipt_id
            != discovery_append.receipt.receipt_id
            or validation_intent.semantic_authority.role is not role
            or validation_intent.semantic_authority.schema is not schema
            or validation_intent.semantic_authority.semantic_verification_id
            != exact_verification.verification_id
            or validation_intent.semantic_authority.stage
            is not control.V075ControlledBatchStageV2.CHILD_VALIDATION
            or validation_intent.semantic_authority.round_index != 0
            or validation_intent.semantic_authority.support_freeze_id
            != support.freeze_id
            or validation_intent.stream_identity
            != control.derive_v075_controlled_validation_stream_v2(
                support_freeze=support
            )
            or validation_intent.accepted_draw_start != 1
            or validation_intent.accepted_draw_count
            != CHILD_VALIDATION_DRAWS
            or validation_intent.accepted_draw_cap
            != (
                CHILD_VALIDATION_DRAWS
                + MAXIMUM_PROMOTION_ROUNDS * PROMOTION_DRAWS
            )
        ):
            _fail("child execution row differs from exact D64/V8192 intent")
        child = next(
            item
            for item in exact_closure.child_states
            if row_id
            in {row.row_binding_id for row in item.row_bindings}
        )
        executed.append(
            V075LiveDynamicChildExecutedRowV2(
                _CHILD_EXECUTED_ROW_ISSUER,
                child.child_binding_id,
                row_id,
                discovery.intent_id,
                discovery_append.receipt.receipt_id,
                discovery_append.batch.batch_id,
                support.freeze_id,
                template.template_id,
                validation_append.receipt.receipt_id,
                validation_append.batch.batch_id,
            )
        )
    return V075LiveDynamicChildExecutionLedgerV2(
        _CHILD_EXECUTION_LEDGER_ISSUER,
        exact_closure.closure_id,
        exact_verification.verification_id,
        exact_closure.source_epoch.model_epoch_id,
        exact_closure.source_epoch.head_id,
        prefix.current_head_id,
        prefix.verification_id,
        tuple(sorted(executed, key=lambda item: item.row_binding_id)),
    )


def freeze_v075_live_dynamic_child_execution_ledger_v2(
    *,
    closure: V075LiveDynamicChildClosureV2,
    closure_verification: V075LiveDynamicChildClosureVerificationV2,
    open_prefix_verification: (
        control.V075OpenControlledBatchPrefixVerificationV2
    ),
) -> V075LiveDynamicChildExecutionLedgerV2:
    """Construction factory using immutable same-process provenance."""

    return _freeze_v075_live_dynamic_child_execution_ledger_v2(
        closure=closure,
        closure_verification=closure_verification,
        open_prefix_verification=open_prefix_verification,
        portable_replay=False,
    )


def verify_v075_live_dynamic_child_execution_ledger_bytes_v2(
    *,
    closure: V075LiveDynamicChildClosureV2,
    closure_verification: V075LiveDynamicChildClosureVerificationV2,
    open_prefix_verification: (
        control.V075OpenControlledBatchPrefixVerificationV2
    ),
    claimed_bytes: bytes,
) -> tuple[
    V075LiveDynamicChildExecutionLedgerV2,
    V075LiveDynamicChildExecutionVerificationV2,
]:
    document = _strict_document(claimed_bytes, "child execution ledger")
    expected = _freeze_v075_live_dynamic_child_execution_ledger_v2(
        closure=closure,
        closure_verification=closure_verification,
        open_prefix_verification=open_prefix_verification,
        portable_replay=True,
    )
    if (
        set(document) != set(expected.to_document())
        or claimed_bytes != expected.canonical_bytes
    ):
        _fail("child execution ledger differs from exact replay")
    verification = _exact_child_execution_verification(expected)
    return expected, verification


_CHILD_REPLANNING_BARRIER_ISSUER = object()
_CHILD_REPLANNING_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075LiveDynamicChildReplanningBarrierV2:
    """Typed all-or-none transition from one failed epoch to its child model."""

    _issuer: object = field(repr=False, compare=False)
    closure_id: str
    closure_verification_id: str
    execution_ledger_id: str
    execution_verification_id: str
    source_model_epoch_id: str
    source_head_id: str
    resulting_model_epoch_id: str
    resulting_head_id: str
    resulting_open_prefix_verification_id: str
    resulting_numerical_model_id: str
    resulting_proof_id: str
    resulting_outcome: planning_v2.V075NumericalOutcomeV2
    authorized_row_binding_ids: tuple[str, ...]
    source_row_binding_ids: tuple[str, ...]
    _barrier_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.closure_id, "child barrier closure"),
            (
                self.closure_verification_id,
                "child barrier closure verification",
            ),
            (self.execution_ledger_id, "child barrier execution ledger"),
            (
                self.execution_verification_id,
                "child barrier execution verification",
            ),
            (self.source_model_epoch_id, "child barrier source epoch"),
            (self.source_head_id, "child barrier source head"),
            (
                self.resulting_model_epoch_id,
                "child barrier resulting epoch",
            ),
            (self.resulting_head_id, "child barrier resulting head"),
            (
                self.resulting_open_prefix_verification_id,
                "child barrier resulting open prefix",
            ),
            (
                self.resulting_numerical_model_id,
                "child barrier resulting model",
            ),
            (self.resulting_proof_id, "child barrier resulting proof"),
            *(
                (value, "child barrier row")
                for value in (
                    *self.authorized_row_binding_ids,
                    *self.source_row_binding_ids,
                )
            ),
        ):
            _cid(value, label)
        if (
            self._issuer is not _CHILD_REPLANNING_BARRIER_ISSUER
            or self.source_model_epoch_id == self.resulting_model_epoch_id
            or self.source_head_id == self.resulting_head_id
            or type(self.resulting_outcome)
            is not planning_v2.V075NumericalOutcomeV2
            or type(self.authorized_row_binding_ids) is not tuple
            or not self.authorized_row_binding_ids
            or self.authorized_row_binding_ids
            != tuple(sorted(set(self.authorized_row_binding_ids)))
            or type(self.source_row_binding_ids) is not tuple
            or not self.source_row_binding_ids
            or self.source_row_binding_ids
            != tuple(sorted(set(self.source_row_binding_ids)))
            or set(self.authorized_row_binding_ids)
            & set(self.source_row_binding_ids)
        ):
            _fail("live child replanning barrier is malformed")
        object.__setattr__(
            self,
            "_barrier_id",
            _hash("child_replanning_barrier", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_live_dynamic_child_replanning_barrier.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "closure_id": self.closure_id,
            "closure_verification_id": self.closure_verification_id,
            "execution_ledger_id": self.execution_ledger_id,
            "execution_verification_id": self.execution_verification_id,
            "source_model_epoch_id": self.source_model_epoch_id,
            "source_head_id": self.source_head_id,
            "resulting_model_epoch_id": self.resulting_model_epoch_id,
            "resulting_head_id": self.resulting_head_id,
            "resulting_open_prefix_verification_id": (
                self.resulting_open_prefix_verification_id
            ),
            "resulting_numerical_model_id": (
                self.resulting_numerical_model_id
            ),
            "resulting_proof_id": self.resulting_proof_id,
            "resulting_outcome": self.resulting_outcome.value,
            "authorized_row_binding_ids": list(
                self.authorized_row_binding_ids
            ),
            "source_row_binding_ids": list(self.source_row_binding_ids),
            "changed_row_binding_ids": list(
                self.authorized_row_binding_ids
            ),
            "reused_row_binding_ids": list(self.source_row_binding_ids),
            "all_authorized_rows_added_exactly_once": True,
            "no_extra_or_missing_modeled_row": True,
            "source_rows_reused_byte_identically": True,
            "parent_epoch_and_signed_prefix_exactly_bound": True,
            "replanning_allowed": True,
            "observer_calls": 0,
            "kernel_calls": 0,
            "official_execution_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def barrier_id(self) -> str:
        return self._barrier_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "barrier_id": self.barrier_id}


@dataclass(frozen=True, slots=True)
class V075LiveDynamicChildReplanningBarrierVerificationV2:
    """Verifier identity required before consuming the resulting proof."""

    _issuer: object = field(repr=False, compare=False)
    barrier_id: str
    closure_id: str
    execution_ledger_id: str
    source_model_epoch_id: str
    resulting_model_epoch_id: str
    resulting_proof_id: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.barrier_id, "child barrier verification barrier"),
            (self.closure_id, "child barrier verification closure"),
            (
                self.execution_ledger_id,
                "child barrier verification execution ledger",
            ),
            (
                self.source_model_epoch_id,
                "child barrier verification source epoch",
            ),
            (
                self.resulting_model_epoch_id,
                "child barrier verification resulting epoch",
            ),
            (
                self.resulting_proof_id,
                "child barrier verification resulting proof",
            ),
        ):
            _cid(value, label)
        if self._issuer is not _CHILD_REPLANNING_VERIFICATION_ISSUER:
            _fail("live child replanning barrier verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("child_replanning_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_live_dynamic_child_replanning_barrier_"
                "verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "barrier_id": self.barrier_id,
            "closure_id": self.closure_id,
            "execution_ledger_id": self.execution_ledger_id,
            "source_model_epoch_id": self.source_model_epoch_id,
            "resulting_model_epoch_id": self.resulting_model_epoch_id,
            "resulting_proof_id": self.resulting_proof_id,
            "semantic_replay_complete": True,
            "replanning_allowed": True,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _exact_child_replanning_barrier_verification(
    barrier: V075LiveDynamicChildReplanningBarrierV2,
) -> V075LiveDynamicChildReplanningBarrierVerificationV2:
    return V075LiveDynamicChildReplanningBarrierVerificationV2(
        _CHILD_REPLANNING_VERIFICATION_ISSUER,
        barrier.barrier_id,
        barrier.closure_id,
        barrier.execution_ledger_id,
        barrier.source_model_epoch_id,
        barrier.resulting_model_epoch_id,
        barrier.resulting_proof_id,
    )


def _freeze_v075_live_dynamic_child_replanning_barrier_v2(
    *,
    closure: V075LiveDynamicChildClosureV2,
    closure_verification: V075LiveDynamicChildClosureVerificationV2,
    execution_ledger: V075LiveDynamicChildExecutionLedgerV2,
    execution_verification: V075LiveDynamicChildExecutionVerificationV2,
    resulting_epoch: live_model.V075LiveIncrementalModelEpochV2,
    portable_replay: bool,
) -> V075LiveDynamicChildReplanningBarrierV2:
    """Authorize replanning only after the exact global child closure."""

    if (
        type(closure) is not V075LiveDynamicChildClosureV2
        or closure.status
        is not V075LiveDynamicChildClosureStatusV2.AUTHORIZED
        or not closure.discovery_intents
    ):
        _fail("child replanning barrier requires one authorized closure")
    namespace = closure.discovery_intents[0].stream_identity.namespace
    source_epoch = (
        _replay_epoch(closure.source_epoch)
        if portable_replay
        else _operational_epoch(closure.source_epoch)
    )
    exact_closure = (
        _freeze_v075_live_dynamic_child_closure_from_exact_epoch_v2(
            epoch=source_epoch,
            namespace=namespace,
        )
    )
    if (
        exact_closure.closure_id != closure.closure_id
        or exact_closure.canonical_bytes != closure.canonical_bytes
    ):
        _fail("child replanning barrier closure differs from exact replay")
    exact_closure_verification = _exact_child_closure_verification(
        exact_closure
    )
    if (
        type(closure_verification)
        is not V075LiveDynamicChildClosureVerificationV2
        or closure_verification.verification_id
        != exact_closure_verification.verification_id
        or closure_verification.to_document()
        != exact_closure_verification.to_document()
    ):
        _fail("child replanning barrier closure verification is foreign")

    result = (
        _replay_epoch(resulting_epoch)
        if portable_replay
        else _operational_epoch(resulting_epoch)
    )
    source = exact_closure.source_epoch
    parent = result.parent_epoch
    if not portable_replay and type(parent) is (
        live_model.V075LiveIncrementalModelEpochV2
    ):
        parent = _operational_epoch(parent)
    if (
        type(parent) is not live_model.V075LiveIncrementalModelEpochV2
        or parent.model_epoch_id != source.model_epoch_id
        or parent.canonical_bytes != source.canonical_bytes
        or (not portable_replay and parent is not source)
        or result.epoch_index != source.epoch_index + 1
        or result.occurrence_identity != source.occurrence_identity
        or result.context_id != source.context_id
        or result.arm is not source.arm
        or result.route is not source.route
    ):
        _fail("child replanning result is not the exact source child epoch")

    exact_ledger = _freeze_v075_live_dynamic_child_execution_ledger_v2(
        closure=exact_closure,
        closure_verification=exact_closure_verification,
        open_prefix_verification=result.open_prefix_verification,
        portable_replay=portable_replay,
    )
    if (
        type(execution_ledger) is not V075LiveDynamicChildExecutionLedgerV2
        or execution_ledger.ledger_id != exact_ledger.ledger_id
        or execution_ledger.canonical_bytes != exact_ledger.canonical_bytes
    ):
        _fail("child replanning execution ledger differs from exact replay")
    exact_execution_verification = _exact_child_execution_verification(
        exact_ledger
    )
    if (
        type(execution_verification)
        is not V075LiveDynamicChildExecutionVerificationV2
        or execution_verification.verification_id
        != exact_execution_verification.verification_id
        or execution_verification.to_document()
        != exact_execution_verification.to_document()
    ):
        _fail("child replanning execution verification is foreign")

    authorized_rows = tuple(
        sorted(
            item.row_binding.row_binding_id
            for item in exact_closure.discovery_intents
        )
    )
    source_rows = tuple(
        sorted(item.row_binding_id for item in source.row_sources)
    )
    result_rows = tuple(
        sorted(item.row_binding_id for item in result.row_sources)
    )
    if (
        exact_ledger.source_head_id != source.head_id
        or exact_ledger.resulting_head_id != result.head_id
        or exact_ledger.open_prefix_verification_id
        != result.open_prefix_verification.verification_id
        or result.changed_row_binding_ids != authorized_rows
        or result.reused_row_binding_ids != source_rows
        or result_rows != tuple(sorted((*source_rows, *authorized_rows)))
        or len(result_rows) != len(set(result_rows))
    ):
        _fail(
            "child replanning result is partial, has extra rows, or changed "
            "one source row"
        )
    return V075LiveDynamicChildReplanningBarrierV2(
        _CHILD_REPLANNING_BARRIER_ISSUER,
        exact_closure.closure_id,
        exact_closure_verification.verification_id,
        exact_ledger.ledger_id,
        exact_execution_verification.verification_id,
        source.model_epoch_id,
        source.head_id,
        result.model_epoch_id,
        result.head_id,
        result.open_prefix_verification.verification_id,
        result.model.model_id,
        result.proof.proof_id,
        result.proof.outcome,
        authorized_rows,
        source_rows,
    )


def freeze_v075_live_dynamic_child_replanning_barrier_v2(
    *,
    closure: V075LiveDynamicChildClosureV2,
    closure_verification: V075LiveDynamicChildClosureVerificationV2,
    execution_ledger: V075LiveDynamicChildExecutionLedgerV2,
    execution_verification: V075LiveDynamicChildExecutionVerificationV2,
    resulting_epoch: live_model.V075LiveIncrementalModelEpochV2,
) -> V075LiveDynamicChildReplanningBarrierV2:
    """Construction barrier using immutable same-process provenance."""

    return _freeze_v075_live_dynamic_child_replanning_barrier_v2(
        closure=closure,
        closure_verification=closure_verification,
        execution_ledger=execution_ledger,
        execution_verification=execution_verification,
        resulting_epoch=resulting_epoch,
        portable_replay=False,
    )


def verify_v075_live_dynamic_child_replanning_barrier_bytes_v2(
    *,
    closure: V075LiveDynamicChildClosureV2,
    closure_verification: V075LiveDynamicChildClosureVerificationV2,
    execution_ledger: V075LiveDynamicChildExecutionLedgerV2,
    execution_verification: V075LiveDynamicChildExecutionVerificationV2,
    resulting_epoch: live_model.V075LiveIncrementalModelEpochV2,
    claimed_bytes: bytes,
) -> tuple[
    V075LiveDynamicChildReplanningBarrierV2,
    V075LiveDynamicChildReplanningBarrierVerificationV2,
]:
    """Replay the complete global closure and resulting model transition."""

    document = _strict_document(claimed_bytes, "child replanning barrier")
    expected = _freeze_v075_live_dynamic_child_replanning_barrier_v2(
        closure=closure,
        closure_verification=closure_verification,
        execution_ledger=execution_ledger,
        execution_verification=execution_verification,
        resulting_epoch=resulting_epoch,
        portable_replay=True,
    )
    if (
        set(document) != set(expected.to_document())
        or claimed_bytes != expected.canonical_bytes
    ):
        _fail("child replanning barrier differs from exact replay")
    return expected, _exact_child_replanning_barrier_verification(expected)


class V075LivePromotionDecisionStatusV2(str, Enum):
    AUTHORIZED = "PROMOTION_AUTHORIZED"
    CANDIDATE_EARLY_STOP = "CANDIDATE_EARLY_STOP"
    NO_ELIGIBLE_FRONTIER_ROW = "NO_ELIGIBLE_FRONTIER_ROW"


_PROMOTION_INTENT_ISSUER = object()
_PROMOTION_DECISION_FROM_REPLAYED_EPOCH_ISSUER = object()
_PROMOTION_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075LivePromotionIntentV2:
    """One exact +2048 extension of an existing epoch-1 validation stream."""

    _issuer: object = field(repr=False, compare=False)
    source_model_epoch_id: str
    source_numerical_model_id: str
    source_proof_id: str
    source_frontier_id: str
    source_head_id: str
    occurrence_id: str
    context_id: str
    arm: worker.V075WorkerArmV1
    round_index: int
    previous_decision_id: str | None
    numerical_row_id: str
    row_binding_id: str
    row_source_binding_id: str
    stage: str
    support_freeze_id: str
    stream_identity: graph.V075TransitionStreamIdentityV1
    accepted_draw_start: int
    accepted_draw_count: int
    accepted_draw_cap: int
    _intent_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.source_model_epoch_id, "promotion source epoch"),
            (self.source_numerical_model_id, "promotion source model"),
            (self.source_proof_id, "promotion source proof"),
            (self.source_frontier_id, "promotion source frontier"),
            (self.source_head_id, "promotion source head"),
            (self.occurrence_id, "promotion occurrence"),
            (self.context_id, "promotion context"),
            (self.numerical_row_id, "promotion numerical row"),
            (self.row_binding_id, "promotion row binding"),
            (self.row_source_binding_id, "promotion row source"),
            (self.support_freeze_id, "promotion support freeze"),
        ):
            _cid(value, label)
        if self.previous_decision_id is not None:
            _cid(self.previous_decision_id, "promotion previous decision")
        if (
            self._issuer is not _PROMOTION_INTENT_ISSUER
            or type(self.arm) is not worker.V075WorkerArmV1
            or self.round_index not in (1, 2)
            or self.stage not in {"ROOT_VALIDATION", "CHILD_VALIDATION"}
            or type(self.stream_identity)
            is not graph.V075TransitionStreamIdentityV1
            or self.stream_identity.context_id != self.context_id
            or self.stream_identity.row_binding_id != self.row_binding_id
            or self.stream_identity.arm != self.arm.value
            or self.stream_identity.lane
            is not graph.V075ObservationLaneV1.VALIDATION
            or self.stream_identity.observer_epoch_index != 1
            or type(self.accepted_draw_start) is not int
            or self.accepted_draw_start <= 1
            or self.accepted_draw_count != PROMOTION_DRAWS
            or type(self.accepted_draw_cap) is not int
            or self.accepted_draw_end > self.accepted_draw_cap
            or (self.round_index == 1) != (self.previous_decision_id is None)
        ):
            _fail("live promotion intent is malformed or caller-minted")
        object.__setattr__(
            self,
            "_intent_id",
            _hash("promotion_intent", self._payload()),
        )

    @property
    def accepted_draw_end(self) -> int:
        return self.accepted_draw_start + self.accepted_draw_count - 1

    @property
    def intent_id(self) -> str:
        return self._intent_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LIVE_PROMOTION_SEMANTIC_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "semantic_role": LIVE_PROMOTION_SEMANTIC_ROLE,
            "stage": self.stage,
            "round_index": self.round_index,
            "source_model_epoch_id": self.source_model_epoch_id,
            "source_numerical_model_id": self.source_numerical_model_id,
            "source_proof_id": self.source_proof_id,
            "source_frontier_id": self.source_frontier_id,
            "source_head_id": self.source_head_id,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "arm": self.arm.value,
            "previous_promotion_decision_id": self.previous_decision_id,
            "numerical_row_id": self.numerical_row_id,
            "row_binding_id": self.row_binding_id,
            "row_source_binding_id": self.row_source_binding_id,
            "support_freeze_id": self.support_freeze_id,
            "stream_id": self.stream_identity.stream_id,
            "observer_epoch_index": 1,
            "accepted_draw_start": self.accepted_draw_start,
            "accepted_draw_count": self.accepted_draw_count,
            "accepted_draw_end": self.accepted_draw_end,
            "accepted_draw_cap": self.accepted_draw_cap,
            "selection_rule": PROMOTION_SELECTION_RULE,
            "support_epoch_immutable": True,
            "other_event_remains_other": True,
            "observer_execution_ready": True,
            "official_execution_allowed": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "stream_identity": self.stream_identity.to_document(),
            "intent_id": self.intent_id,
        }


@dataclass(frozen=True, slots=True)
class V075LivePromotionDecisionV2:
    """Typed authorization, early stop, or empty eligible frontier."""

    _issuer: object = field(repr=False, compare=False)
    source_epoch: live_model.V075LiveIncrementalModelEpochV2 = field(
        repr=False
    )
    child_closure_id: str
    child_closure_verification_id: str
    child_execution_ledger_id: str | None
    child_execution_verification_id: str | None
    child_replanning_barrier_id: str | None
    child_replanning_barrier_verification_id: str | None
    round_index: int
    previous_decision: "V075LivePromotionDecisionV2 | None" = field(
        repr=False
    )
    previous_replanning_barrier_id: str | None
    status: V075LivePromotionDecisionStatusV2
    intent: V075LivePromotionIntentV2 | None
    eligible_row_ids: tuple[str, ...]
    _decision_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        epoch = self.source_epoch
        if (
            self._issuer
            is not _PROMOTION_DECISION_FROM_REPLAYED_EPOCH_ISSUER
            or type(epoch) is not live_model.V075LiveIncrementalModelEpochV2
            or self.round_index not in (1, 2)
            or type(self.status) is not V075LivePromotionDecisionStatusV2
            or type(self.eligible_row_ids) is not tuple
            or self.eligible_row_ids
            != tuple(sorted(set(self.eligible_row_ids)))
        ):
            _fail("live promotion decision is malformed")
        for value in self.eligible_row_ids:
            _cid(value, "promotion eligible row")
        _cid(self.child_closure_id, "promotion child closure")
        _cid(
            self.child_closure_verification_id,
            "promotion child closure verification",
        )
        child_execution_ids = (
            self.child_execution_ledger_id,
            self.child_execution_verification_id,
            self.child_replanning_barrier_id,
            self.child_replanning_barrier_verification_id,
        )
        if any(value is None for value in child_execution_ids) != all(
            value is None for value in child_execution_ids
        ):
            _fail("promotion child execution provenance is partial")
        for value in child_execution_ids:
            if value is not None:
                _cid(value, "promotion child execution provenance")
        if self.previous_replanning_barrier_id is not None:
            _cid(
                self.previous_replanning_barrier_id,
                "promotion previous replanning barrier",
            )
        authorized = self.status is V075LivePromotionDecisionStatusV2.AUTHORIZED
        if authorized != (
            type(self.intent) is V075LivePromotionIntentV2
            and bool(self.eligible_row_ids)
        ):
            _fail("promotion authorization status differs from its intent")
        if authorized and (
            self.intent is None
            or self.intent.round_index != self.round_index
            or self.intent.source_model_epoch_id != epoch.model_epoch_id
            or self.intent.source_proof_id != epoch.proof.proof_id
            or self.intent.source_head_id != epoch.head_id
            or self.intent.numerical_row_id not in self.eligible_row_ids
        ):
            _fail("promotion intent differs from exact source epoch")
        candidate = (
            epoch.proof.outcome is planning_v2.V075NumericalOutcomeV2.CANDIDATE
        )
        if (
            self.status
            is V075LivePromotionDecisionStatusV2.CANDIDATE_EARLY_STOP
        ) != candidate:
            _fail("promotion early-stop status differs from numerical proof")
        if candidate and (self.intent is not None or self.eligible_row_ids):
            _fail("candidate early stop emitted promotion work")
        if (
            self.status
            is V075LivePromotionDecisionStatusV2.NO_ELIGIBLE_FRONTIER_ROW
        ) and (self.intent is not None or self.eligible_row_ids):
            _fail("empty promotion frontier emitted promotion work")
        if self.round_index == 1:
            if (
                self.previous_decision is not None
                or self.previous_replanning_barrier_id is not None
            ):
                _fail("promotion round one cannot cite a previous decision")
        elif (
            type(self.previous_decision) is not V075LivePromotionDecisionV2
            or self.previous_decision.round_index != 1
            or self.previous_decision.status
            is not V075LivePromotionDecisionStatusV2.AUTHORIZED
            or self.previous_replanning_barrier_id is None
        ):
            _fail(
                "promotion round two lacks one authorized round-one parent "
                "and replanning barrier"
            )
        if self.round_index == 2 and (
            self.previous_decision is None
            or self.child_closure_id
            != self.previous_decision.child_closure_id
            or self.child_closure_verification_id
            != self.previous_decision.child_closure_verification_id
            or self.child_execution_ledger_id
            != self.previous_decision.child_execution_ledger_id
            or self.child_execution_verification_id
            != self.previous_decision.child_execution_verification_id
            or self.child_replanning_barrier_id
            != self.previous_decision.child_replanning_barrier_id
            or self.child_replanning_barrier_verification_id
            != (
                self.previous_decision
                .child_replanning_barrier_verification_id
            )
        ):
            _fail("promotion round two changed child predecessor provenance")
        object.__setattr__(
            self,
            "_decision_id",
            _hash("promotion_decision", self._payload()),
        )

    @property
    def decision_id(self) -> str:
        return self._decision_id

    def _payload(self) -> dict[str, Any]:
        epoch = self.source_epoch
        return {
            "schema": "acfqp.v075_live_promotion_decision.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "status": self.status.value,
            "round_index": self.round_index,
            "child_closure_id": self.child_closure_id,
            "child_closure_verification_id": (
                self.child_closure_verification_id
            ),
            "child_execution_ledger_id": self.child_execution_ledger_id,
            "child_execution_verification_id": (
                self.child_execution_verification_id
            ),
            "child_replanning_barrier_id": (
                self.child_replanning_barrier_id
            ),
            "child_replanning_barrier_verification_id": (
                self.child_replanning_barrier_verification_id
            ),
            "previous_promotion_decision_id": (
                None
                if self.previous_decision is None
                else self.previous_decision.decision_id
            ),
            "previous_promotion_replanning_barrier_id": (
                self.previous_replanning_barrier_id
            ),
            "source_model_epoch_id": epoch.model_epoch_id,
            "source_numerical_model_id": epoch.model.model_id,
            "source_proof_id": epoch.proof.proof_id,
            "source_frontier_id": (
                None
                if epoch.proof.failed_frontier is None
                else epoch.proof.failed_frontier.frontier_id
            ),
            "source_head_id": epoch.head_id,
            "occurrence_id": epoch.occurrence_identity.occurrence_id,
            "context_id": epoch.context_id,
            "arm": epoch.arm.value,
            "eligible_numerical_row_ids": list(self.eligible_row_ids),
            "selected_intent_id": (
                None if self.intent is None else self.intent.intent_id
            ),
            "selection_rule": PROMOTION_SELECTION_RULE,
            "maximum_promotion_rounds": MAXIMUM_PROMOTION_ROUNDS,
            "candidate_is_early_stop": True,
            "observer_calls": 0,
            "kernel_calls": 0,
            "official_execution_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "intent": None if self.intent is None else self.intent.to_document(),
            "decision_id": self.decision_id,
        }


@dataclass(frozen=True, slots=True)
class V075LivePromotionDecisionVerificationV2:
    """Verifier-issued semantic identity for one live promotion decision."""

    _issuer: object = field(repr=False, compare=False)
    decision_id: str
    source_model_epoch_id: str
    source_proof_id: str
    source_head_id: str
    round_index: int
    status: V075LivePromotionDecisionStatusV2
    intent_id: str | None
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.decision_id, "promotion verification decision"),
            (self.source_model_epoch_id, "promotion verification epoch"),
            (self.source_proof_id, "promotion verification proof"),
            (self.source_head_id, "promotion verification head"),
        ):
            _cid(value, label)
        if self.intent_id is not None:
            _cid(self.intent_id, "promotion verification intent")
        if (
            self._issuer is not _PROMOTION_VERIFICATION_ISSUER
            or self.round_index not in (1, 2)
            or type(self.status) is not V075LivePromotionDecisionStatusV2
            or (
                self.status is V075LivePromotionDecisionStatusV2.AUTHORIZED
            )
            != (self.intent_id is not None)
        ):
            _fail("promotion decision verification is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("promotion_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_promotion_decision_verification.v2",
            "schema_version": SCHEMA_VERSION,
            "decision_id": self.decision_id,
            "source_model_epoch_id": self.source_model_epoch_id,
            "source_proof_id": self.source_proof_id,
            "source_head_id": self.source_head_id,
            "round_index": self.round_index,
            "status": self.status.value,
            "intent_id": self.intent_id,
            "semantic_replay_complete": True,
            "observer_execution_performed": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _exact_promotion_decision_verification(
    decision: V075LivePromotionDecisionV2,
) -> V075LivePromotionDecisionVerificationV2:
    epoch = decision.source_epoch
    return V075LivePromotionDecisionVerificationV2(
        _PROMOTION_VERIFICATION_ISSUER,
        decision.decision_id,
        epoch.model_epoch_id,
        epoch.proof.proof_id,
        epoch.head_id,
        decision.round_index,
        decision.status,
        None if decision.intent is None else decision.intent.intent_id,
    )


_PROMOTION_REPLANNING_BARRIER_ISSUER = object()
_PROMOTION_REPLANNING_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075LivePromotionReplanningBarrierV2:
    """Typed one-append transition required before consuming a new proof."""

    _issuer: object = field(repr=False, compare=False)
    decision_id: str
    decision_verification_id: str
    intent_id: str
    round_index: int
    previous_replanning_barrier_id: str | None
    source_model_epoch_id: str
    source_head_id: str
    resulting_model_epoch_id: str
    resulting_head_id: str
    resulting_open_prefix_verification_id: str
    resulting_numerical_model_id: str
    resulting_proof_id: str
    resulting_outcome: planning_v2.V075NumericalOutcomeV2
    row_binding_id: str
    append_receipt_id: str
    append_batch_id: str
    reused_row_binding_ids: tuple[str, ...]
    _barrier_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.decision_id, "promotion barrier decision"),
            (
                self.decision_verification_id,
                "promotion barrier decision verification",
            ),
            (self.intent_id, "promotion barrier intent"),
            (self.source_model_epoch_id, "promotion barrier source epoch"),
            (self.source_head_id, "promotion barrier source head"),
            (
                self.resulting_model_epoch_id,
                "promotion barrier resulting epoch",
            ),
            (self.resulting_head_id, "promotion barrier resulting head"),
            (
                self.resulting_open_prefix_verification_id,
                "promotion barrier resulting prefix",
            ),
            (
                self.resulting_numerical_model_id,
                "promotion barrier resulting model",
            ),
            (self.resulting_proof_id, "promotion barrier resulting proof"),
            (self.row_binding_id, "promotion barrier changed row"),
            (self.append_receipt_id, "promotion barrier append receipt"),
            (self.append_batch_id, "promotion barrier append batch"),
            *(
                (value, "promotion barrier reused row")
                for value in self.reused_row_binding_ids
            ),
        ):
            _cid(value, label)
        if self.previous_replanning_barrier_id is not None:
            _cid(
                self.previous_replanning_barrier_id,
                "promotion barrier previous barrier",
            )
        if (
            self._issuer is not _PROMOTION_REPLANNING_BARRIER_ISSUER
            or self.round_index not in (1, 2)
            or (self.round_index == 1)
            != (self.previous_replanning_barrier_id is None)
            or self.source_model_epoch_id == self.resulting_model_epoch_id
            or self.source_head_id == self.resulting_head_id
            or type(self.resulting_outcome)
            is not planning_v2.V075NumericalOutcomeV2
            or type(self.reused_row_binding_ids) is not tuple
            or self.reused_row_binding_ids
            != tuple(sorted(set(self.reused_row_binding_ids)))
            or self.row_binding_id in self.reused_row_binding_ids
        ):
            _fail("live promotion replanning barrier is malformed")
        object.__setattr__(
            self,
            "_barrier_id",
            _hash("promotion_replanning_barrier", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_promotion_replanning_barrier.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "decision_id": self.decision_id,
            "decision_verification_id": self.decision_verification_id,
            "intent_id": self.intent_id,
            "round_index": self.round_index,
            "previous_replanning_barrier_id": (
                self.previous_replanning_barrier_id
            ),
            "source_model_epoch_id": self.source_model_epoch_id,
            "source_head_id": self.source_head_id,
            "resulting_model_epoch_id": self.resulting_model_epoch_id,
            "resulting_head_id": self.resulting_head_id,
            "resulting_open_prefix_verification_id": (
                self.resulting_open_prefix_verification_id
            ),
            "resulting_numerical_model_id": (
                self.resulting_numerical_model_id
            ),
            "resulting_proof_id": self.resulting_proof_id,
            "resulting_outcome": self.resulting_outcome.value,
            "changed_row_binding_ids": [self.row_binding_id],
            "reused_row_binding_ids": list(self.reused_row_binding_ids),
            "append_receipt_id": self.append_receipt_id,
            "append_batch_id": self.append_batch_id,
            "exactly_one_promotion_append": True,
            "semantic_role_schema_and_verification_exactly_bound": True,
            "parent_epoch_and_signed_prefix_exactly_bound": True,
            "proof_consumption_allowed": True,
            "observer_calls": 0,
            "kernel_calls": 0,
            "official_execution_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def barrier_id(self) -> str:
        return self._barrier_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "barrier_id": self.barrier_id}


@dataclass(frozen=True, slots=True)
class V075LivePromotionReplanningBarrierVerificationV2:
    _issuer: object = field(repr=False, compare=False)
    barrier_id: str
    decision_id: str
    intent_id: str
    source_model_epoch_id: str
    resulting_model_epoch_id: str
    resulting_proof_id: str
    round_index: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.barrier_id, "promotion barrier verification barrier"),
            (self.decision_id, "promotion barrier verification decision"),
            (self.intent_id, "promotion barrier verification intent"),
            (
                self.source_model_epoch_id,
                "promotion barrier verification source epoch",
            ),
            (
                self.resulting_model_epoch_id,
                "promotion barrier verification resulting epoch",
            ),
            (
                self.resulting_proof_id,
                "promotion barrier verification resulting proof",
            ),
        ):
            _cid(value, label)
        if (
            self._issuer is not _PROMOTION_REPLANNING_VERIFICATION_ISSUER
            or self.round_index not in (1, 2)
        ):
            _fail(
                "live promotion replanning barrier verification is malformed"
            )
        object.__setattr__(
            self,
            "_verification_id",
            _hash("promotion_replanning_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_live_promotion_replanning_barrier_"
                "verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "barrier_id": self.barrier_id,
            "decision_id": self.decision_id,
            "intent_id": self.intent_id,
            "source_model_epoch_id": self.source_model_epoch_id,
            "resulting_model_epoch_id": self.resulting_model_epoch_id,
            "resulting_proof_id": self.resulting_proof_id,
            "round_index": self.round_index,
            "semantic_replay_complete": True,
            "proof_consumption_allowed": True,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _exact_promotion_replanning_barrier_verification(
    barrier: V075LivePromotionReplanningBarrierV2,
) -> V075LivePromotionReplanningBarrierVerificationV2:
    return V075LivePromotionReplanningBarrierVerificationV2(
        _PROMOTION_REPLANNING_VERIFICATION_ISSUER,
        barrier.barrier_id,
        barrier.decision_id,
        barrier.intent_id,
        barrier.source_model_epoch_id,
        barrier.resulting_model_epoch_id,
        barrier.resulting_proof_id,
        barrier.round_index,
    )


def _promotion_predecessor_ids(
    *,
    source_epoch: live_model.V075LiveIncrementalModelEpochV2,
    child_closure: V075LiveDynamicChildClosureV2,
    child_closure_verification: V075LiveDynamicChildClosureVerificationV2,
    child_execution_ledger: V075LiveDynamicChildExecutionLedgerV2 | None,
    child_execution_verification: (
        V075LiveDynamicChildExecutionVerificationV2 | None
    ),
    child_replanning_barrier: (
        V075LiveDynamicChildReplanningBarrierV2 | None
    ),
    child_replanning_barrier_verification: (
        V075LiveDynamicChildReplanningBarrierVerificationV2 | None
    ),
    portable_replay: bool,
) -> tuple[str, str, str | None, str | None, str | None, str | None]:
    """Prove the sole legal child-stage predecessor for promotion round one."""

    if type(child_closure) is not V075LiveDynamicChildClosureV2:
        _fail("promotion lacks one exact child closure predecessor")
    root_epoch = (
        _replay_epoch(child_closure.source_epoch)
        if portable_replay
        else _operational_epoch(child_closure.source_epoch)
    )
    if not root_epoch.controlled_appends:
        _fail("promotion child predecessor lacks its root namespace")
    namespace = (
        root_epoch.controlled_appends[0]
        .batch.request.stream_identity.namespace
    )
    exact_closure = (
        _freeze_v075_live_dynamic_child_closure_from_exact_epoch_v2(
            epoch=root_epoch,
            namespace=namespace,
        )
    )
    if (
        child_closure.closure_id != exact_closure.closure_id
        or child_closure.canonical_bytes != exact_closure.canonical_bytes
    ):
        _fail("promotion child closure differs from exact root-stage replay")
    exact_closure_verification = _exact_child_closure_verification(
        exact_closure
    )
    if (
        type(child_closure_verification)
        is not V075LiveDynamicChildClosureVerificationV2
        or child_closure_verification.verification_id
        != exact_closure_verification.verification_id
        or child_closure_verification.to_document()
        != exact_closure_verification.to_document()
    ):
        _fail("promotion child closure verification is foreign")
    execution_items = (
        child_execution_ledger,
        child_execution_verification,
        child_replanning_barrier,
        child_replanning_barrier_verification,
    )
    if exact_closure.status is (
        V075LiveDynamicChildClosureStatusV2.ALREADY_COMPLETE
    ):
        exact_source = (
            _replay_epoch(source_epoch)
            if portable_replay
            else _operational_epoch(source_epoch)
        )
        if (
            any(item is not None for item in execution_items)
            or exact_source.model_epoch_id != root_epoch.model_epoch_id
            or exact_source.canonical_bytes != root_epoch.canonical_bytes
            or (not portable_replay and exact_source is not root_epoch)
        ):
            _fail(
                "already-complete child predecessor changed source or "
                "claimed execution work"
            )
        return (
            exact_closure.closure_id,
            exact_closure_verification.verification_id,
            None,
            None,
            None,
            None,
        )
    if exact_closure.status is not (
        V075LiveDynamicChildClosureStatusV2.AUTHORIZED
    ) or any(item is None for item in execution_items):
        _fail(
            "candidate, capped, or incomplete child closure cannot "
            "authorize promotion"
        )
    assert child_execution_ledger is not None
    assert child_execution_verification is not None
    assert child_replanning_barrier is not None
    assert child_replanning_barrier_verification is not None
    exact_barrier = _freeze_v075_live_dynamic_child_replanning_barrier_v2(
        closure=exact_closure,
        closure_verification=exact_closure_verification,
        execution_ledger=child_execution_ledger,
        execution_verification=child_execution_verification,
        resulting_epoch=source_epoch,
        portable_replay=portable_replay,
    )
    exact_barrier_verification = (
        _exact_child_replanning_barrier_verification(exact_barrier)
    )
    if (
        child_replanning_barrier.barrier_id != exact_barrier.barrier_id
        or child_replanning_barrier.canonical_bytes
        != exact_barrier.canonical_bytes
        or child_replanning_barrier_verification.verification_id
        != exact_barrier_verification.verification_id
        or child_replanning_barrier_verification.to_document()
        != exact_barrier_verification.to_document()
    ):
        _fail("promotion child replanning barrier is stale or foreign")
    return (
        exact_closure.closure_id,
        exact_closure_verification.verification_id,
        child_execution_ledger.ledger_id,
        child_execution_verification.verification_id,
        exact_barrier.barrier_id,
        exact_barrier_verification.verification_id,
    )


def _exact_promotion_semantic_append(
    *,
    decision: V075LivePromotionDecisionV2,
    decision_verification: V075LivePromotionDecisionVerificationV2,
    append: control.V075ControlledBatchAppendV2,
) -> None:
    intent = decision.intent
    if intent is None:
        _fail("promotion semantic append requires one authorized intent")
    semantic = append.intent.semantic_authority
    expected_stage = (
        control.V075ControlledBatchStageV2.ROOT_VALIDATION
        if intent.stage == "ROOT_VALIDATION"
        else control.V075ControlledBatchStageV2.CHILD_VALIDATION
    )
    request = append.batch.request
    if (
        semantic.role
        is not (
            control.V075ControlledBatchSemanticAuthorityRoleV2
            .LIVE_PROMOTION_AUTHORIZATION
        )
        or semantic.schema
        is not (
            control.V075ControlledBatchSemanticAuthoritySchemaV2
            .LIVE_PROMOTION_AUTHORIZATION
        )
        or semantic.semantic_artifact_id != intent.intent_id
        or semantic.semantic_verification_id
        != decision_verification.verification_id
        or semantic.stage is not expected_stage
        or semantic.round_index != decision.round_index
        or semantic.support_freeze_id != intent.support_freeze_id
        or request.stream_identity != intent.stream_identity
        or request.accepted_draw_start != intent.accepted_draw_start
        or request.accepted_draw_count != intent.accepted_draw_count
        or request.accepted_draw_cap != intent.accepted_draw_cap
    ):
        _fail(
            "promotion append role, schema, verification, stage, round, "
            "support, stream, prefix, or cap differs from authorization"
        )


def _round_one_is_fresh(
    epoch: live_model.V075LiveIncrementalModelEpochV2,
) -> None:
    for row in epoch.model.rows:
        expected = (
            ROOT_VALIDATION_BASE_DRAWS
            if row.remaining_horizon == 2
            else CHILD_VALIDATION_BASE_DRAWS
        )
        if row.validation_draw_count != expected:
            _fail("promotion round one source already contains a promotion")


def _validate_promotion_replanning_transition(
    *,
    decision: V075LivePromotionDecisionV2,
    decision_verification: V075LivePromotionDecisionVerificationV2,
    result: live_model.V075LiveIncrementalModelEpochV2,
    portable_replay: bool,
) -> tuple[control.V075ControlledBatchAppendV2, tuple[str, ...]]:
    intent = decision.intent
    source = decision.source_epoch
    parent = result.parent_epoch
    if not portable_replay and type(parent) is (
        live_model.V075LiveIncrementalModelEpochV2
    ):
        parent = _operational_epoch(parent)
    if (
        decision.status is not V075LivePromotionDecisionStatusV2.AUTHORIZED
        or intent is None
        or type(parent) is not live_model.V075LiveIncrementalModelEpochV2
        or parent.model_epoch_id != source.model_epoch_id
        or parent.canonical_bytes != source.canonical_bytes
        or (not portable_replay and parent is not source)
        or result.epoch_index != source.epoch_index + 1
        or result.occurrence_identity != source.occurrence_identity
        or result.context_id != source.context_id
        or result.arm is not source.arm
        or result.route is not source.route
        or result.head_id == source.head_id
        or result.support_freeze_ids != source.support_freeze_ids
    ):
        _fail("promotion result is not the exact source child epoch")
    new_receipts = result.append_receipt_ids[len(source.append_receipt_ids) :]
    if (
        result.append_receipt_ids[: len(source.append_receipt_ids)]
        != source.append_receipt_ids
        or len(new_receipts) != 1
    ):
        _fail("promotion result contains partial or extra append work")
    append = result.controlled_append_by_receipt_id_v2(new_receipts[0])
    _exact_promotion_semantic_append(
        decision=decision,
        decision_verification=decision_verification,
        append=append,
    )
    parent_source = _row_source(source, intent.row_binding_id)
    current_source = _row_source(result, intent.row_binding_id)
    parent_stream = _validation_stream(epoch=source, source=parent_source)
    current_stream = _validation_stream(epoch=result, source=current_source)
    new_row_receipts = tuple(
        item
        for item in current_source.validation_append_receipt_ids
        if item not in set(parent_source.validation_append_receipt_ids)
    )
    source_rows = tuple(
        sorted(item.row_binding_id for item in source.row_sources)
    )
    result_rows = tuple(
        sorted(item.row_binding_id for item in result.row_sources)
    )
    reused = tuple(
        item for item in source_rows if item != intent.row_binding_id
    )
    if (
        current_source.support_freeze_id != parent_source.support_freeze_id
        or current_source.support_freeze_id != intent.support_freeze_id
        or current_source.validation_stream_id
        != parent_source.validation_stream_id
        or current_stream != parent_stream
        or current_stream != intent.stream_identity
        or current_source.validation_draw_cap
        != parent_source.validation_draw_cap
        or current_source.validation_prefix_end != intent.accepted_draw_end
        or parent_source.validation_prefix_end
        != intent.accepted_draw_start - 1
        or new_row_receipts != (append.receipt.receipt_id,)
        or result.changed_row_binding_ids != (intent.row_binding_id,)
        or result.reused_row_binding_ids != reused
        or result_rows != source_rows
    ):
        _fail(
            "promotion row source, changed/reused rows, or prefix extension "
            "is stale, partial, or changed"
        )
    return append, reused


def _construct_promotion_replanning_barrier(
    *,
    decision: V075LivePromotionDecisionV2,
    decision_verification: V075LivePromotionDecisionVerificationV2,
    result: live_model.V075LiveIncrementalModelEpochV2,
    append: control.V075ControlledBatchAppendV2,
    reused_row_binding_ids: tuple[str, ...],
) -> V075LivePromotionReplanningBarrierV2:
    intent = decision.intent
    if intent is None:  # pragma: no cover - checked by transition validator
        _fail("promotion barrier lacks one exact intent")
    return V075LivePromotionReplanningBarrierV2(
        _PROMOTION_REPLANNING_BARRIER_ISSUER,
        decision.decision_id,
        decision_verification.verification_id,
        intent.intent_id,
        decision.round_index,
        decision.previous_replanning_barrier_id,
        decision.source_epoch.model_epoch_id,
        decision.source_epoch.head_id,
        result.model_epoch_id,
        result.head_id,
        result.open_prefix_verification.verification_id,
        result.model.model_id,
        result.proof.proof_id,
        result.proof.outcome,
        intent.row_binding_id,
        append.receipt.receipt_id,
        append.batch.batch_id,
        reused_row_binding_ids,
    )


def _verify_round_two_parent(
    *,
    epoch: live_model.V075LiveIncrementalModelEpochV2,
    previous: V075LivePromotionDecisionV2,
    previous_barrier: V075LivePromotionReplanningBarrierV2,
    portable_replay: bool,
) -> None:
    if previous.intent is None:
        _fail("round-two parent lacks an exact promotion intent")
    decision_verification = _exact_promotion_decision_verification(previous)
    append, reused = _validate_promotion_replanning_transition(
        decision=previous,
        decision_verification=decision_verification,
        result=epoch,
        portable_replay=portable_replay,
    )
    expected = _construct_promotion_replanning_barrier(
        decision=previous,
        decision_verification=decision_verification,
        result=epoch,
        append=append,
        reused_row_binding_ids=reused,
    )
    if (
        type(previous_barrier) is not V075LivePromotionReplanningBarrierV2
        or previous_barrier.barrier_id != expected.barrier_id
        or previous_barrier.canonical_bytes != expected.canonical_bytes
    ):
        _fail("round-two lineage lacks the exact round-one proof barrier")


def _eligible_promotion_rows(
    epoch: live_model.V075LiveIncrementalModelEpochV2,
) -> tuple[
    tuple[
        planning_v2.V075FrontierObligationV2,
        planning_v2.V075NumericalRowV2,
        live_model.V075LiveModelRowSourceBindingV2,
        graph.V075TransitionStreamIdentityV1,
    ],
    ...,
]:
    proof = epoch.proof
    if (
        proof.outcome is not planning_v2.V075NumericalOutcomeV2.FAILED_FRONTIER
        or proof.failed_frontier is None
    ):
        _fail("promotion eligibility requires one exact failed proof frontier")
    rows = {item.row_id: item for item in epoch.model.rows}
    eligible = []
    for obligation in proof.failed_frontier.obligations:
        row = rows.get(obligation.row_id)
        if (
            row is None
            or obligation.unmaterialized_successor_ids
            or obligation.next_registered_checkpoint is None
        ):
            continue
        source = _row_source(epoch, row.row_binding_id)
        stream = _validation_stream(epoch=epoch, source=source)
        if (
            source.numerical_row_id != row.row_id
            or source.validation_prefix_end != row.validation_draw_count
            or obligation.current_validation_draw_count
            != row.validation_draw_count
            or obligation.next_registered_checkpoint
            - obligation.current_validation_draw_count
            != PROMOTION_DRAWS
            or obligation.next_registered_checkpoint
            > source.validation_draw_cap
            or source.support_freeze_id not in epoch.support_freeze_ids
        ):
            _fail("failed frontier and live row-source checkpoint disagree")
        eligible.append((obligation, row, source, stream))
    return tuple(
        sorted(
            eligible,
            key=lambda item: (
                -item[0].interval_width_sum,
                -item[0].other_upper,
                item[0].row_id,
            ),
        )
    )


def _freeze_promotion_from_replayed_epoch(
    *,
    epoch: live_model.V075LiveIncrementalModelEpochV2,
    round_index: int,
    previous_decision: V075LivePromotionDecisionV2 | None,
    previous_replanning_barrier: V075LivePromotionReplanningBarrierV2 | None,
    predecessor_ids: tuple[
        str,
        str,
        str | None,
        str | None,
        str | None,
        str | None,
    ],
    portable_replay: bool,
) -> V075LivePromotionDecisionV2:
    """Construct from an epoch already owned by the exact replay boundary."""

    if round_index == 1:
        if (
            previous_decision is not None
            or previous_replanning_barrier is not None
        ):
            _fail("promotion round one rejects previous lineage")
        _round_one_is_fresh(epoch)
    else:
        if (
            type(previous_decision) is not V075LivePromotionDecisionV2
            or previous_decision.round_index != 1
            or previous_decision.status
            is not V075LivePromotionDecisionStatusV2.AUTHORIZED
            or type(previous_replanning_barrier)
            is not V075LivePromotionReplanningBarrierV2
        ):
            _fail(
                "promotion round two requires one authorized round-one "
                "decision and replanning barrier"
            )
        _verify_round_two_parent(
            epoch=epoch,
            previous=previous_decision,
            previous_barrier=previous_replanning_barrier,
            portable_replay=portable_replay,
        )
    proof = epoch.proof
    if proof.outcome is planning_v2.V075NumericalOutcomeV2.CANDIDATE:
        return V075LivePromotionDecisionV2(
            _PROMOTION_DECISION_FROM_REPLAYED_EPOCH_ISSUER,
            epoch,
            *predecessor_ids,
            round_index,
            previous_decision,
            (
                None
                if previous_replanning_barrier is None
                else previous_replanning_barrier.barrier_id
            ),
            V075LivePromotionDecisionStatusV2.CANDIDATE_EARLY_STOP,
            None,
            (),
        )
    eligible = _eligible_promotion_rows(epoch)
    if not eligible:
        return V075LivePromotionDecisionV2(
            _PROMOTION_DECISION_FROM_REPLAYED_EPOCH_ISSUER,
            epoch,
            *predecessor_ids,
            round_index,
            previous_decision,
            (
                None
                if previous_replanning_barrier is None
                else previous_replanning_barrier.barrier_id
            ),
            V075LivePromotionDecisionStatusV2.NO_ELIGIBLE_FRONTIER_ROW,
            None,
            (),
        )
    obligation, row, source, stream = eligible[0]
    assert obligation.next_registered_checkpoint is not None
    stage = (
        "ROOT_VALIDATION"
        if row.remaining_horizon == 2
        else "CHILD_VALIDATION"
    )
    intent = V075LivePromotionIntentV2(
        _PROMOTION_INTENT_ISSUER,
        epoch.model_epoch_id,
        epoch.model.model_id,
        proof.proof_id,
        proof.failed_frontier.frontier_id,  # type: ignore[union-attr]
        epoch.head_id,
        epoch.occurrence_identity.occurrence_id,
        epoch.context_id,
        epoch.arm,
        round_index,
        (
            None
            if previous_decision is None
            else previous_decision.decision_id
        ),
        row.row_id,
        row.row_binding_id,
        source.binding_id,
        stage,
        source.support_freeze_id,
        stream,
        obligation.current_validation_draw_count + 1,
        PROMOTION_DRAWS,
        source.validation_draw_cap,
    )
    return V075LivePromotionDecisionV2(
        _PROMOTION_DECISION_FROM_REPLAYED_EPOCH_ISSUER,
        epoch,
        *predecessor_ids,
        round_index,
        previous_decision,
        (
            None
            if previous_replanning_barrier is None
            else previous_replanning_barrier.barrier_id
        ),
        V075LivePromotionDecisionStatusV2.AUTHORIZED,
        intent,
        tuple(sorted(item[0].row_id for item in eligible)),
    )


def _freeze_v075_live_promotion_decision_v2(
    *,
    source_epoch: live_model.V075LiveIncrementalModelEpochV2,
    round_index: int,
    child_closure: V075LiveDynamicChildClosureV2,
    child_closure_verification: V075LiveDynamicChildClosureVerificationV2,
    child_execution_ledger: V075LiveDynamicChildExecutionLedgerV2 | None,
    child_execution_verification: (
        V075LiveDynamicChildExecutionVerificationV2 | None
    ),
    child_replanning_barrier: (
        V075LiveDynamicChildReplanningBarrierV2 | None
    ),
    child_replanning_barrier_verification: (
        V075LiveDynamicChildReplanningBarrierVerificationV2 | None
    ),
    previous_decision: V075LivePromotionDecisionV2 | None = None,
    previous_replanning_barrier: (
        V075LivePromotionReplanningBarrierV2 | None
    ) = None,
    portable_replay: bool,
) -> V075LivePromotionDecisionV2:
    """Replay once, then freeze one deterministic promotion decision."""

    if type(round_index) is not int or round_index not in (1, 2):
        _fail("promotion round index exceeds the preregistered two-round cap")
    epoch = (
        _replay_epoch(source_epoch)
        if portable_replay
        else _operational_epoch(source_epoch)
    )
    exact_previous = previous_decision
    predecessor_source = epoch
    if round_index == 2:
        parent = epoch.parent_epoch
        if type(parent) is not live_model.V075LiveIncrementalModelEpochV2:
            _fail("promotion round two requires one exact parent epoch")
        parent = (
            _replay_epoch(parent)
            if portable_replay
            else _operational_epoch(parent)
        )
        predecessor_source = parent
    predecessor_ids = _promotion_predecessor_ids(
        source_epoch=predecessor_source,
        child_closure=child_closure,
        child_closure_verification=child_closure_verification,
        child_execution_ledger=child_execution_ledger,
        child_execution_verification=child_execution_verification,
        child_replanning_barrier=child_replanning_barrier,
        child_replanning_barrier_verification=(
            child_replanning_barrier_verification
        ),
        portable_replay=portable_replay,
    )
    if round_index == 2:
        expected_previous = _freeze_promotion_from_replayed_epoch(
            epoch=parent,
            round_index=1,
            previous_decision=None,
            previous_replanning_barrier=None,
            predecessor_ids=predecessor_ids,
            portable_replay=portable_replay,
        )
        if (
            type(previous_decision) is not V075LivePromotionDecisionV2
            or previous_decision.decision_id
            != expected_previous.decision_id
            or previous_decision.canonical_bytes
            != expected_previous.canonical_bytes
        ):
            _fail("promotion round-two parent decision is stale or foreign")
        exact_previous = expected_previous
    return _freeze_promotion_from_replayed_epoch(
        epoch=epoch,
        round_index=round_index,
        previous_decision=exact_previous,
        previous_replanning_barrier=previous_replanning_barrier,
        predecessor_ids=predecessor_ids,
        portable_replay=portable_replay,
    )


def freeze_v075_live_promotion_decision_v2(
    *,
    source_epoch: live_model.V075LiveIncrementalModelEpochV2,
    round_index: int,
    child_closure: V075LiveDynamicChildClosureV2,
    child_closure_verification: V075LiveDynamicChildClosureVerificationV2,
    child_execution_ledger: V075LiveDynamicChildExecutionLedgerV2 | None,
    child_execution_verification: (
        V075LiveDynamicChildExecutionVerificationV2 | None
    ),
    child_replanning_barrier: (
        V075LiveDynamicChildReplanningBarrierV2 | None
    ),
    child_replanning_barrier_verification: (
        V075LiveDynamicChildReplanningBarrierVerificationV2 | None
    ),
    previous_decision: V075LivePromotionDecisionV2 | None = None,
    previous_replanning_barrier: (
        V075LivePromotionReplanningBarrierV2 | None
    ) = None,
) -> V075LivePromotionDecisionV2:
    """Construction decision using immutable same-process provenance."""

    return _freeze_v075_live_promotion_decision_v2(
        source_epoch=source_epoch,
        round_index=round_index,
        child_closure=child_closure,
        child_closure_verification=child_closure_verification,
        child_execution_ledger=child_execution_ledger,
        child_execution_verification=child_execution_verification,
        child_replanning_barrier=child_replanning_barrier,
        child_replanning_barrier_verification=(
            child_replanning_barrier_verification
        ),
        previous_decision=previous_decision,
        previous_replanning_barrier=previous_replanning_barrier,
        portable_replay=False,
    )


def _freeze_v075_live_promotion_replanning_barrier_v2(
    *,
    decision: V075LivePromotionDecisionV2,
    decision_verification: V075LivePromotionDecisionVerificationV2,
    resulting_epoch: live_model.V075LiveIncrementalModelEpochV2,
    child_closure: V075LiveDynamicChildClosureV2,
    child_closure_verification: V075LiveDynamicChildClosureVerificationV2,
    child_execution_ledger: V075LiveDynamicChildExecutionLedgerV2 | None,
    child_execution_verification: (
        V075LiveDynamicChildExecutionVerificationV2 | None
    ),
    child_replanning_barrier: (
        V075LiveDynamicChildReplanningBarrierV2 | None
    ),
    child_replanning_barrier_verification: (
        V075LiveDynamicChildReplanningBarrierVerificationV2 | None
    ),
    previous_replanning_barrier: (
        V075LivePromotionReplanningBarrierV2 | None
    ) = None,
    portable_replay: bool,
) -> V075LivePromotionReplanningBarrierV2:
    """Bind one exact semantic promotion append to its recomputed proof."""

    if (
        type(decision) is not V075LivePromotionDecisionV2
        or decision.status
        is not V075LivePromotionDecisionStatusV2.AUTHORIZED
        or decision.intent is None
    ):
        _fail("promotion replanning barrier requires one authorized decision")
    exact_decision = _freeze_v075_live_promotion_decision_v2(
        source_epoch=decision.source_epoch,
        round_index=decision.round_index,
        child_closure=child_closure,
        child_closure_verification=child_closure_verification,
        child_execution_ledger=child_execution_ledger,
        child_execution_verification=child_execution_verification,
        child_replanning_barrier=child_replanning_barrier,
        child_replanning_barrier_verification=(
            child_replanning_barrier_verification
        ),
        previous_decision=decision.previous_decision,
        previous_replanning_barrier=previous_replanning_barrier,
        portable_replay=portable_replay,
    )
    if (
        exact_decision.decision_id != decision.decision_id
        or exact_decision.canonical_bytes != decision.canonical_bytes
    ):
        _fail("promotion replanning decision differs from exact replay")
    exact_verification = _exact_promotion_decision_verification(
        exact_decision
    )
    if (
        type(decision_verification)
        is not V075LivePromotionDecisionVerificationV2
        or decision_verification.verification_id
        != exact_verification.verification_id
        or decision_verification.to_document()
        != exact_verification.to_document()
    ):
        _fail("promotion replanning decision verification is foreign")
    result = (
        _replay_epoch(resulting_epoch)
        if portable_replay
        else _operational_epoch(resulting_epoch)
    )
    append, reused = _validate_promotion_replanning_transition(
        decision=exact_decision,
        decision_verification=exact_verification,
        result=result,
        portable_replay=portable_replay,
    )
    return _construct_promotion_replanning_barrier(
        decision=exact_decision,
        decision_verification=exact_verification,
        result=result,
        append=append,
        reused_row_binding_ids=reused,
    )


def freeze_v075_live_promotion_replanning_barrier_v2(
    *,
    decision: V075LivePromotionDecisionV2,
    decision_verification: V075LivePromotionDecisionVerificationV2,
    resulting_epoch: live_model.V075LiveIncrementalModelEpochV2,
    child_closure: V075LiveDynamicChildClosureV2,
    child_closure_verification: V075LiveDynamicChildClosureVerificationV2,
    child_execution_ledger: V075LiveDynamicChildExecutionLedgerV2 | None,
    child_execution_verification: (
        V075LiveDynamicChildExecutionVerificationV2 | None
    ),
    child_replanning_barrier: (
        V075LiveDynamicChildReplanningBarrierV2 | None
    ),
    child_replanning_barrier_verification: (
        V075LiveDynamicChildReplanningBarrierVerificationV2 | None
    ),
    previous_replanning_barrier: (
        V075LivePromotionReplanningBarrierV2 | None
    ) = None,
) -> V075LivePromotionReplanningBarrierV2:
    """Construction barrier using immutable same-process provenance."""

    return _freeze_v075_live_promotion_replanning_barrier_v2(
        decision=decision,
        decision_verification=decision_verification,
        resulting_epoch=resulting_epoch,
        child_closure=child_closure,
        child_closure_verification=child_closure_verification,
        child_execution_ledger=child_execution_ledger,
        child_execution_verification=child_execution_verification,
        child_replanning_barrier=child_replanning_barrier,
        child_replanning_barrier_verification=(
            child_replanning_barrier_verification
        ),
        previous_replanning_barrier=previous_replanning_barrier,
        portable_replay=False,
    )


def verify_v075_live_promotion_replanning_barrier_bytes_v2(
    *,
    decision: V075LivePromotionDecisionV2,
    decision_verification: V075LivePromotionDecisionVerificationV2,
    resulting_epoch: live_model.V075LiveIncrementalModelEpochV2,
    child_closure: V075LiveDynamicChildClosureV2,
    child_closure_verification: V075LiveDynamicChildClosureVerificationV2,
    child_execution_ledger: V075LiveDynamicChildExecutionLedgerV2 | None,
    child_execution_verification: (
        V075LiveDynamicChildExecutionVerificationV2 | None
    ),
    child_replanning_barrier: (
        V075LiveDynamicChildReplanningBarrierV2 | None
    ),
    child_replanning_barrier_verification: (
        V075LiveDynamicChildReplanningBarrierVerificationV2 | None
    ),
    claimed_bytes: bytes,
    previous_replanning_barrier: (
        V075LivePromotionReplanningBarrierV2 | None
    ) = None,
) -> tuple[
    V075LivePromotionReplanningBarrierV2,
    V075LivePromotionReplanningBarrierVerificationV2,
]:
    """Replay decision, semantic append, model delta, and resulting proof."""

    document = _strict_document(
        claimed_bytes,
        "promotion replanning barrier",
    )
    expected = _freeze_v075_live_promotion_replanning_barrier_v2(
        decision=decision,
        decision_verification=decision_verification,
        resulting_epoch=resulting_epoch,
        child_closure=child_closure,
        child_closure_verification=child_closure_verification,
        child_execution_ledger=child_execution_ledger,
        child_execution_verification=child_execution_verification,
        child_replanning_barrier=child_replanning_barrier,
        child_replanning_barrier_verification=(
            child_replanning_barrier_verification
        ),
        previous_replanning_barrier=previous_replanning_barrier,
        portable_replay=True,
    )
    if (
        set(document) != set(expected.to_document())
        or claimed_bytes != expected.canonical_bytes
    ):
        _fail("promotion replanning barrier differs from exact replay")
    return (
        expected,
        _exact_promotion_replanning_barrier_verification(expected),
    )


def verify_v075_live_promotion_decision_bytes_v2(
    *,
    source_epoch: live_model.V075LiveIncrementalModelEpochV2,
    round_index: int,
    child_closure: V075LiveDynamicChildClosureV2,
    child_closure_verification: V075LiveDynamicChildClosureVerificationV2,
    child_execution_ledger: V075LiveDynamicChildExecutionLedgerV2 | None,
    child_execution_verification: (
        V075LiveDynamicChildExecutionVerificationV2 | None
    ),
    child_replanning_barrier: (
        V075LiveDynamicChildReplanningBarrierV2 | None
    ),
    child_replanning_barrier_verification: (
        V075LiveDynamicChildReplanningBarrierVerificationV2 | None
    ),
    previous_decision: V075LivePromotionDecisionV2 | None,
    claimed_bytes: bytes,
    previous_replanning_barrier: (
        V075LivePromotionReplanningBarrierV2 | None
    ) = None,
) -> tuple[
    V075LivePromotionDecisionV2,
    V075LivePromotionDecisionVerificationV2,
]:
    """Rebuild the source epoch, selection, intent, and canonical bytes."""

    document = _strict_document(claimed_bytes, "live promotion decision")
    expected = _freeze_v075_live_promotion_decision_v2(
        source_epoch=source_epoch,
        round_index=round_index,
        child_closure=child_closure,
        child_closure_verification=child_closure_verification,
        child_execution_ledger=child_execution_ledger,
        child_execution_verification=child_execution_verification,
        child_replanning_barrier=child_replanning_barrier,
        child_replanning_barrier_verification=(
            child_replanning_barrier_verification
        ),
        previous_decision=previous_decision,
        previous_replanning_barrier=previous_replanning_barrier,
        portable_replay=True,
    )
    if (
        set(document) != set(expected.to_document())
        or claimed_bytes != expected.canonical_bytes
    ):
        _fail("live promotion decision differs from exact replay")
    verification = _exact_promotion_decision_verification(expected)
    return expected, verification


def open_v075_production_live_dynamic_acquisition_authority_v2(
    **_unused: Any,
) -> NoReturn:
    """Remain structurally locked regardless of monkeypatched constants."""

    raise V075LiveDynamicAcquisitionProductionV2NotReady(
        PRODUCTION_BLOCKER
    )


__all__ = [
    "CHILD_DISCOVERY_DRAWS",
    "CHILD_VALIDATION_DRAWS",
    "DOMAIN_TAGS",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "KERNEL_ACCESS_ALLOWED",
    "LIVE_DYNAMIC_CHILD_SEMANTIC_ROLE",
    "LIVE_DYNAMIC_CHILD_SEMANTIC_SCHEMA",
    "LIVE_DYNAMIC_CHILD_VALIDATION_TEMPLATE_SCHEMA",
    "LIVE_PROMOTION_SEMANTIC_ROLE",
    "LIVE_PROMOTION_SEMANTIC_SCHEMA",
    "MAXIMUM_NEW_CHILD_ACTION_ROWS",
    "MAXIMUM_PROMOTION_ROUNDS",
    "OBSERVER_ACCESS_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PROFILE_KEY",
    "PRODUCTION_AUTHORIZING",
    "PRODUCTION_BLOCKER",
    "PROMOTION_DRAWS",
    "PROMOTION_SELECTION_RULE",
    "PROPOSED_CONTRACT_VERSION",
    "ROOT_VALIDATION_BASE_DRAWS",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "TERMINAL_CLASS",
    "TERMINAL_SCOPE",
    "V075LiveDynamicAcquisitionProductionV2NotReady",
    "V075LiveDynamicAcquisitionV2InvariantViolation",
    "V075LiveDynamicChildCausalEdgeV2",
    "V075LiveDynamicChildClosureStatusV2",
    "V075LiveDynamicChildClosureV2",
    "V075LiveDynamicChildClosureVerificationV2",
    "V075LiveDynamicChildDiscoveryIntentV2",
    "V075LiveDynamicChildExecutedRowV2",
    "V075LiveDynamicChildExecutionLedgerV2",
    "V075LiveDynamicChildExecutionVerificationV2",
    "V075LiveDynamicChildIntentStageV2",
    "V075LiveDynamicChildReplanningBarrierV2",
    "V075LiveDynamicChildReplanningBarrierVerificationV2",
    "V075LiveDynamicChildStateV2",
    "V075LiveDynamicChildValidationIntentTemplateV2",
    "V075LivePromotionDecisionStatusV2",
    "V075LivePromotionDecisionV2",
    "V075LivePromotionDecisionVerificationV2",
    "V075LivePromotionIntentV2",
    "V075LivePromotionReplanningBarrierV2",
    "V075LivePromotionReplanningBarrierVerificationV2",
    "freeze_v075_live_dynamic_child_closure_v2",
    "freeze_v075_live_dynamic_child_execution_ledger_v2",
    "freeze_v075_live_dynamic_child_replanning_barrier_v2",
    "freeze_v075_live_promotion_decision_v2",
    "freeze_v075_live_promotion_replanning_barrier_v2",
    "open_v075_production_live_dynamic_acquisition_authority_v2",
    "verify_v075_live_dynamic_child_closure_bytes_v2",
    "verify_v075_live_dynamic_child_execution_ledger_bytes_v2",
    "verify_v075_live_dynamic_child_replanning_barrier_bytes_v2",
    "verify_v075_live_promotion_decision_bytes_v2",
    "verify_v075_live_promotion_replanning_barrier_bytes_v2",
]
